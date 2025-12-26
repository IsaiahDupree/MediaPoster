# Instagram Trend Analysis System - Complete Specification

**Based on:** Instagram Scraper Stable API (RapidAPI)  
**Provider:** RockSolid APIs (thetechguy32744)  
**API Base:** `https://instagram-scraper-stable-api.p.rapidapi.com`

---

## 🎯 System Overview

This specification maps RapidAPI endpoints to a comprehensive trend analysis system that provides:
- Top trends (formats, templates, patterns)
- Top music/sounds
- Top keywords
- Top accounts per keyword/niche
- Top niches
- Trend velocity and acceleration metrics

---

## 📡 RapidAPI Endpoint Mapping

### Available Endpoints (Verified)

| Endpoint | Method | Purpose | Trend Use Case |
|----------|--------|---------|----------------|
| `POST /v1/info` | POST | User profile | Get account metrics, follower counts |
| `POST /v1/reels` | POST | User reels | Extract audio, engagement metrics |
| `POST /v1/posts` | POST | User posts | Get post engagement, captions |
| `POST /v1/search` | POST | Search users/hashtags | Discover accounts by keyword |
| `GET /v1/reel_by_shortcode` | GET | Reel details | Get specific reel metrics |
| `GET /v1/media_by_shortcode` | GET | Media details | Get post/reel details |

### Missing Endpoints (Need Workarounds)

The API **does not directly provide**:
- ❌ Hashtag media feed (need to use search + manual collection)
- ❌ Location-based feeds (not available)
- ❌ Explore feed (not available)
- ❌ Trending sounds/music list (need to aggregate from reels)

**Solution:** Build our own dataset by sampling and aggregating data from available endpoints.

---

## 🏗️ Architecture: Trend Discovery Pipeline

### Phase 1: Data Collection (RapidAPI → Internal DB)

#### 1.1 Trend Discovery Sources

**A) Keyword → Accounts → Media**
```python
# RapidAPI Endpoint: POST /v1/search
# Use case: Find accounts by keyword
POST /v1/search
{
  "query": "fitness coach"  # or "amazon finds", "copywriter", etc.
}

# Then for each account:
POST /v1/reels
{
  "username_or_id_or_url": "found_username",
  "count": 12
}
```

**B) Hashtag Discovery**
```python
# RapidAPI Endpoint: POST /v1/search
# Search for hashtags
POST /v1/search
{
  "query": "#gym"  # or "gym" (works for hashtags too)
}

# Response includes hashtags with media_count
# Then manually collect media using:
# - Search for accounts using the hashtag
# - Get their reels/posts
```

**C) Audio/Music Discovery**
```python
# RapidAPI Endpoint: POST /v1/reels
# Extract audio from reels
POST /v1/reels
{
  "username_or_id_or_url": "username",
  "count": 50  # Get more reels for better sampling
}

# Extract from response:
# clips_metadata.music_info.music_asset_info.audio_id
# clips_metadata.music_info.music_asset_info.title
# clips_metadata.music_info.music_asset_info.display_artist
```

**D) Account Sampling**
```python
# RapidAPI Endpoint: POST /v1/info
# Get account metrics
POST /v1/info
{
  "username_or_id_or_url": "username"
}

# Then get their content:
POST /v1/reels + POST /v1/posts
```

---

## 📊 Database Schema for Trend Analysis

### Core Tables

```sql
-- Media candidates pool (raw data from RapidAPI)
CREATE TABLE instagram_media_candidates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id TEXT UNIQUE NOT NULL,
    shortcode TEXT UNIQUE,
    media_type TEXT CHECK (media_type IN ('reel', 'post', 'carousel')),
    
    -- Content
    caption_text TEXT,
    hashtags TEXT[],  -- Extracted from caption
    location_name TEXT,
    location_id TEXT,
    
    -- Engagement Metrics
    play_count BIGINT,
    like_count BIGINT,
    comment_count BIGINT,
    share_count BIGINT,  -- May be null
    view_count BIGINT,
    
    -- Audio/Music
    music_id TEXT,
    music_title TEXT,
    music_artist TEXT,
    audio_url TEXT,
    original_sound_id TEXT,
    
    -- Author
    author_id TEXT NOT NULL,
    author_username TEXT,
    author_followers BIGINT,
    
    -- Timestamps
    taken_at TIMESTAMPTZ NOT NULL,
    discovered_at TIMESTAMPTZ DEFAULT now(),
    
    -- Metadata
    thumbnail_url TEXT,
    video_url TEXT,
    permalink TEXT,
    
    -- Trend Analysis Fields
    trend_score NUMERIC(5,2) DEFAULT 0,
    velocity_6h NUMERIC(10,2),  -- Views gained in last 6 hours
    velocity_24h NUMERIC(10,2),  -- Views gained in last 24 hours
    acceleration NUMERIC(10,2),  -- Change in velocity
    engagement_rate NUMERIC(5,4),  -- (likes + comments) / views
    
    -- Clustering
    trend_group_id UUID REFERENCES trend_groups(id),
    cluster_key TEXT,  -- For grouping (music_id, hashtag_set, etc.)
    
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_media_candidates_taken_at ON instagram_media_candidates(taken_at DESC);
CREATE INDEX idx_media_candidates_trend_score ON instagram_media_candidates(trend_score DESC);
CREATE INDEX idx_media_candidates_music_id ON instagram_media_candidates(music_id);
CREATE INDEX idx_media_candidates_hashtags ON instagram_media_candidates USING GIN(hashtags);
CREATE INDEX idx_media_candidates_trend_group ON instagram_media_candidates(trend_group_id);

-- Trend Groups (clustered media)
CREATE TABLE trend_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trend_name TEXT NOT NULL,
    trend_description TEXT,
    
    -- Clustering Keys
    primary_music_id TEXT,
    primary_hashtags TEXT[],
    format_pattern TEXT,  -- e.g., "3-beat caption: heart → broken → cheers"
    visual_template TEXT,  -- Template description
    
    -- Metrics
    total_views BIGINT DEFAULT 0,
    total_posts INTEGER DEFAULT 0,
    total_likes BIGINT DEFAULT 0,
    total_comments BIGINT DEFAULT 0,
    velocity_24h NUMERIC(10,2),
    acceleration NUMERIC(10,2),
    engagement_rate NUMERIC(5,4),
    
    -- Top Examples
    top_example_media_ids UUID[],
    
    -- Regions (if location data available)
    trending_countries TEXT[],
    trending_cities TEXT[],
    
    -- AI-Generated Content
    ai_summary TEXT,  -- "What it is" paragraph
    trend_formats JSONB,  -- ["3 cards, same font/template", ...]
    content_ideas JSONB,  -- ["Idea 1", "Idea 2", ...]
    hook_lines JSONB,  -- ["Hook 1", "Hook 2", ...]
    cta_patterns JSONB,  -- ["Comment bait", "Save prompts", ...]
    associated_sounds JSONB,  -- Top 3-10 sounds in cluster
    
    -- Metadata
    first_seen_at TIMESTAMPTZ,
    peak_at TIMESTAMPTZ,
    status TEXT CHECK (status IN ('rising', 'peak', 'declining', 'dead')),
    
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_trend_groups_velocity ON trend_groups(velocity_24h DESC);
CREATE INDEX idx_trend_groups_status ON trend_groups(status);

-- Top Sounds/Music
CREATE TABLE trending_sounds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    music_id TEXT UNIQUE NOT NULL,
    title TEXT,
    artist TEXT,
    audio_url TEXT,
    
    -- Metrics
    usage_count INTEGER DEFAULT 0,  -- How many posts use this sound
    total_views BIGINT DEFAULT 0,
    total_likes BIGINT DEFAULT 0,
    velocity_24h NUMERIC(10,2),
    trending_score NUMERIC(5,2) DEFAULT 0,
    
    -- Top Media
    top_media_ids UUID[],
    
    -- Regions
    trending_countries TEXT[],
    
    -- Timestamps
    first_seen_at TIMESTAMPTZ,
    peak_at TIMESTAMPTZ,
    last_updated TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_trending_sounds_score ON trending_sounds(trending_score DESC);
CREATE INDEX idx_trending_sounds_velocity ON trending_sounds(velocity_24h DESC);

-- Top Hashtags
CREATE TABLE trending_hashtags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tag TEXT UNIQUE NOT NULL,
    
    -- Metrics
    media_count BIGINT DEFAULT 0,  -- Total posts with this tag
    usage_count_24h INTEGER DEFAULT 0,  -- Posts in last 24h
    velocity_7d NUMERIC(10,2),  -- Growth over 7 days
    trending_score NUMERIC(5,2) DEFAULT 0,
    
    -- Top Media
    top_media_ids UUID[],
    
    -- Categories
    category TEXT,  -- niche/category
    related_tags TEXT[],
    
    -- Timestamps
    first_seen_at TIMESTAMPTZ,
    peak_at TIMESTAMPTZ,
    last_updated TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_trending_hashtags_score ON trending_hashtags(trending_score DESC);
CREATE INDEX idx_trending_hashtags_category ON trending_hashtags(category);

-- Top Keywords (extracted from captions/transcripts)
CREATE TABLE trending_keywords (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keyword TEXT UNIQUE NOT NULL,
    
    -- Metrics
    frequency INTEGER DEFAULT 0,  -- How many posts mention it
    frequency_24h INTEGER DEFAULT 0,
    velocity NUMERIC(10,2),  -- Is usage increasing?
    trending_score NUMERIC(5,2) DEFAULT 0,
    
    -- Top Accounts using this keyword
    top_account_ids TEXT[],
    top_account_usernames TEXT[],
    
    -- Top Media
    top_media_ids UUID[],
    
    -- Related
    related_keywords TEXT[],
    associated_hashtags TEXT[],
    
    -- Timestamps
    first_seen_at TIMESTAMPTZ,
    peak_at TIMESTAMPTZ,
    last_updated TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_trending_keywords_score ON trending_keywords(trending_score DESC);
CREATE INDEX idx_trending_keywords_velocity ON trending_keywords(velocity DESC);

-- Top Accounts by Niche/Keyword
CREATE TABLE top_accounts_by_niche (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id TEXT NOT NULL,
    username TEXT NOT NULL,
    niche TEXT,  -- "fitness", "amazon finds", "copywriter", etc.
    keyword TEXT,  -- Specific keyword they're associated with
    
    -- Metrics
    follower_count BIGINT,
    engagement_rate NUMERIC(5,4),
    avg_views BIGINT,
    avg_likes BIGINT,
    post_frequency NUMERIC(5,2),  -- Posts per week
    
    -- Content Analysis
    primary_content_type TEXT,  -- "reels", "posts", "carousels"
    top_hashtags TEXT[],
    top_sounds TEXT[],
    
    -- Ranking
    niche_rank INTEGER,  -- Rank within this niche
    trending_score NUMERIC(5,2),
    
    -- Timestamps
    discovered_at TIMESTAMPTZ,
    last_updated TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE(account_id, niche, keyword)
);

CREATE INDEX idx_top_accounts_niche ON top_accounts_by_niche(niche, trending_score DESC);
CREATE INDEX idx_top_accounts_keyword ON top_accounts_by_niche(keyword, trending_score DESC);

-- Niches
CREATE TABLE niches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    
    -- Top Metrics
    top_hashtags TEXT[],
    top_sounds TEXT[],
    top_keywords TEXT[],
    top_accounts TEXT[],
    
    -- Trend Metrics
    total_trends INTEGER DEFAULT 0,
    active_trends INTEGER DEFAULT 0,
    avg_engagement_rate NUMERIC(5,4),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

---

## 🔌 Internal API Endpoints (Your Backend)

### Trend Endpoints

```python
# GET /api/trends
# Get list of trending formats/patterns
GET /api/trends?country=US&niche=fitness&time_window=24h&limit=50

Response:
{
  "trends": [
    {
      "trend_id": "uuid",
      "trend_name": "3-Beat Heartbreak Story",
      "summary": "Short description...",
      "formats": ["3 cards, same font/template", "Heart → Broken → Cheers"],
      "content_ideas": ["Idea 1", "Idea 2"],
      "hook_lines": ["Hook 1", "Hook 2"],
      "cta_patterns": ["Comment bait", "Save prompts"],
      "associated_sounds": [
        {"title": "Sound 1", "artist": "Artist 1", "music_id": "id1"}
      ],
      "example_posts": [
        {"media_id": "id", "shortcode": "ABC123", "thumbnail": "url"}
      ],
      "trending_countries": ["US", "UK"],
      "metrics": {
        "total_views": 1000000,
        "total_posts": 500,
        "velocity_24h": 50000,
        "engagement_rate": 0.08
      }
    }
  ],
  "count": 50
}

# GET /api/trends/{trend_id}
# Get detailed trend information
GET /api/trends/{trend_id}

Response:
{
  "trend_id": "uuid",
  "trend_name": "...",
  "trend_description": "Full description...",
  "formats": [...],
  "content_ideas": [...],
  "hook_lines": [...],
  "cta_patterns": [...],
  "associated_sounds": [...],
  "example_posts": [...],
  "trending_countries": [...],
  "metrics": {...},
  "timeline": {
    "first_seen": "2024-01-01T00:00:00Z",
    "peak_at": "2024-01-05T00:00:00Z",
    "status": "rising" | "peak" | "declining"
  }
}
```

### Sounds/Music Endpoints

```python
# GET /api/sounds/top
# Get top trending sounds
GET /api/sounds/top?country=US&niche=fitness&limit=50&time_window=24h

Response:
{
  "sounds": [
    {
      "music_id": "id",
      "title": "Sound Title",
      "artist": "Artist Name",
      "audio_url": "https://...",
      "metrics": {
        "usage_count": 1000,
        "total_views": 5000000,
        "velocity_24h": 50000,
        "trending_score": 8.5
      },
      "top_media": [...],
      "trending_countries": ["US", "UK"]
    }
  ],
  "count": 50
}

# GET /api/sounds/{sound_id}
# Get detailed sound information
GET /api/sounds/{sound_id}

Response:
{
  "music_id": "id",
  "title": "...",
  "artist": "...",
  "audio_url": "...",
  "metrics": {...},
  "top_media": [...],
  "usage_timeline": [...],
  "trending_countries": [...],
  "related_sounds": [...]
}
```

### Hashtag Endpoints

```python
# GET /api/hashtags/top
# Get top trending hashtags
GET /api/hashtags/top?category=fitness&limit=50&time_window=7d

Response:
{
  "hashtags": [
    {
      "tag": "fitness",
      "media_count": 1000000,
      "usage_count_24h": 5000,
      "velocity_7d": 15.5,
      "trending_score": 9.2,
      "category": "fitness",
      "top_media": [...],
      "related_tags": ["workout", "gym", "health"]
    }
  ],
  "count": 50
}

# GET /api/hashtags/{tag}
# Get hashtag details
GET /api/hashtags/fitness

Response:
{
  "tag": "fitness",
  "metrics": {...},
  "top_media": [...],
  "related_tags": [...],
  "trending_accounts": [...],
  "usage_timeline": [...]
}
```

### Keyword Endpoints

```python
# GET /api/keywords/top
# Get top trending keywords
GET /api/keywords/top?limit=50&time_window=24h

Response:
{
  "keywords": [
    {
      "keyword": "amazon finds",
      "frequency": 5000,
      "frequency_24h": 500,
      "velocity": 25.5,
      "trending_score": 8.7,
      "top_accounts": [
        {"username": "account1", "follower_count": 100000}
      ],
      "top_media": [...],
      "related_keywords": ["amazon", "finds", "deals"],
      "associated_hashtags": ["#amazonfinds", "#amazon"]
    }
  ],
  "count": 50
}

# GET /api/keywords/{keyword}
# Get keyword details
GET /api/keywords/amazon%20finds

Response:
{
  "keyword": "amazon finds",
  "metrics": {...},
  "top_accounts": [...],
  "top_media": [...],
  "related_keywords": [...],
  "associated_hashtags": [...],
  "usage_timeline": [...]
}
```

### Account Endpoints

```python
# GET /api/accounts/search
# Search accounts by keyword/niche
GET /api/accounts/search?q=fitness%20coach&niche=fitness&limit=50

Response:
{
  "accounts": [
    {
      "account_id": "id",
      "username": "fitnesscoach",
      "full_name": "Fitness Coach",
      "follower_count": 100000,
      "engagement_rate": 0.08,
      "niche": "fitness",
      "trending_score": 7.5,
      "top_hashtags": ["#fitness", "#workout"],
      "top_sounds": [...]
    }
  ],
  "count": 50
}

# GET /api/accounts/{account_id}
# Get account details
GET /api/accounts/{account_id}

Response:
{
  "account_id": "id",
  "username": "...",
  "profile": {...},
  "metrics": {...},
  "recent_posts": [...],
  "top_hashtags": [...],
  "top_sounds": [...],
  "similar_accounts": [...]
}
```

### Niche Endpoints

```python
# GET /api/niches
# Get all niches with top metrics
GET /api/niches

Response:
{
  "niches": [
    {
      "name": "fitness",
      "description": "...",
      "top_hashtags": [...],
      "top_sounds": [...],
      "top_keywords": [...],
      "top_accounts": [...],
      "metrics": {
        "total_trends": 50,
        "active_trends": 20,
        "avg_engagement_rate": 0.08
      }
    }
  ]
}

# GET /api/niches/{niche}
# Get niche details
GET /api/niches/fitness

Response:
{
  "name": "fitness",
  "description": "...",
  "top_hashtags": [...],
  "top_sounds": [...],
  "top_keywords": [...],
  "top_accounts": [...],
  "active_trends": [...],
  "metrics": {...}
}
```

### Analyzer Endpoints

```python
# POST /api/analyzer/upload
# Upload video for analysis
POST /api/analyzer/upload
Content-Type: multipart/form-data

{
  "file": <video_file>,
  "account_id": "optional"
}

Response:
{
  "job_id": "uuid",
  "status": "queued",
  "estimated_time": 30
}

# GET /api/analyzer/{job_id}
# Get analysis progress and results
GET /api/analyzer/{job_id}

Response:
{
  "job_id": "uuid",
  "status": "processing" | "completed" | "failed",
  "progress": {
    "step": 2,
    "total_steps": 6,
    "current_step": "Analyzing engagement patterns"
  },
  "results": {
    "viral_score": 7.5,
    "fixes": ["Improve hook", "Add trending sound"],
    "suggested_hooks": [...],
    "suggested_hashtags": [...],
    "suggested_sounds": [...],
    "best_time_to_post": "2024-01-15T14:00:00Z"
  }
}
```

### Best Time to Post

```python
# GET /api/best-time-to-post
# Get optimal posting times
GET /api/best-time-to-post?account_id=id&country=US&niche=fitness

Response:
{
  "account_id": "id",
  "optimal_windows": [
    {
      "day": "Monday",
      "time": "14:00",
      "timezone": "America/New_York",
      "score": 9.5,
      "reason": "Peak engagement for fitness content"
    }
  ],
  "avoid_times": [...],
  "timezone": "America/New_York"
}
```

---

## 🔄 Data Collection Workflow

### Step 1: Discovery Jobs (Scheduled)

```python
# Job 1: Keyword-based account discovery
async def discover_accounts_by_keyword(keyword: str):
    # 1. Search for accounts
    response = await rapidapi_client.post("/v1/search", {
        "query": keyword
    })
    
    accounts = response["data"]["users"]
    
    # 2. For each account, get profile
    for account in accounts:
        profile = await rapidapi_client.post("/v1/info", {
            "username_or_id_or_url": account["username"]
        })
        
        # Store in top_accounts_by_niche
        await store_account(account, keyword, profile)
        
        # 3. Get their reels/posts
        reels = await rapidapi_client.post("/v1/reels", {
            "username_or_id_or_url": account["username"],
            "count": 12
        })
        
        # Store media candidates
        await store_media_candidates(reels["data"]["items"])

# Job 2: Hashtag discovery
async def discover_hashtag_content(hashtag: str):
    # 1. Search for hashtag
    response = await rapidapi_client.post("/v1/search", {
        "query": hashtag
    })
    
    hashtag_info = response["data"]["hashtags"][0]  # If found
    
    # 2. Find accounts using this hashtag (via search)
    # Search for accounts, then check their posts for hashtag
    
    # 3. Collect media with this hashtag
    # (Iterate through discovered accounts)

# Job 3: Audio discovery
async def discover_trending_audio():
    # 1. Get reels from trending accounts
    # 2. Extract audio metadata
    # 3. Aggregate by music_id
    # 4. Calculate velocity and trending scores
```

### Step 2: Trend Detection (Scheduled)

```python
# Calculate trend scores
async def calculate_trend_scores():
    # For each media candidate:
    # - Calculate velocity (Δviews over 6h/24h)
    # - Calculate acceleration
    # - Calculate engagement rate
    # - Update trend_score
    
    # Cluster media into trend groups:
    # - Group by music_id
    # - Group by hashtag sets
    # - Group by caption similarity (AI embedding)
    # - Group by visual template (AI embedding)
```

### Step 3: AI Summary Generation (Scheduled)

```python
# Generate trend details using LLM
async def generate_trend_details(trend_group_id: str):
    trend_group = await get_trend_group(trend_group_id)
    example_posts = await get_example_posts(trend_group_id)
    
    # Use LLM to generate:
    prompt = f"""
    Analyze these Instagram posts and create a trend summary:
    Posts: {example_posts}
    
    Generate:
    1. Trend name (short label)
    2. What it is (1 paragraph)
    3. Trend formats (bullets)
    4. Content ideas (3-5)
    5. Hook lines
    6. CTA patterns
    """
    
    result = await llm.generate(prompt)
    
    # Update trend_group with AI-generated content
    await update_trend_group(trend_group_id, result)
```

---

## 📈 Trend Score Calculation

### Formula

```python
def calculate_trend_score(media):
    # Velocity component (40%)
    velocity_score = min(1.0, media.velocity_24h / 100000) * 0.4
    
    # Acceleration component (20%)
    acceleration_score = min(1.0, max(0, media.acceleration / 50000)) * 0.2
    
    # Engagement component (25%)
    engagement_score = min(1.0, media.engagement_rate * 10) * 0.25
    
    # Freshness component (10%)
    hours_old = (now() - media.taken_at).total_seconds() / 3600
    freshness_score = max(0, 1.0 - (hours_old / 168)) * 0.1  # 7 days max
    
    # Creator diversity component (5%)
    # (calculated at trend_group level)
    
    return velocity_score + acceleration_score + engagement_score + freshness_score
```

---

## 🗄️ Implementation Files Structure

```
Backend/
├── services/
│   ├── trend_discovery/
│   │   ├── __init__.py
│   │   ├── account_discovery.py      # Keyword → Accounts
│   │   ├── hashtag_discovery.py      # Hashtag → Media
│   │   ├── audio_discovery.py        # Extract & aggregate audio
│   │   └── media_collector.py        # Collect media candidates
│   ├── trend_analysis/
│   │   ├── __init__.py
│   │   ├── trend_scorer.py           # Calculate trend scores
│   │   ├── trend_clusterer.py         # Cluster media into trends
│   │   ├── velocity_calculator.py     # Calculate velocity/acceleration
│   │   └── ai_summarizer.py           # Generate trend details
│   └── keyword_extraction/
│       ├── __init__.py
│       ├── caption_analyzer.py        # Extract keywords from captions
│       └── transcript_analyzer.py      # Extract from transcripts
├── api/
│   └── endpoints/
│       ├── trends.py                  # GET /api/trends
│       ├── sounds.py                  # GET /api/sounds
│       ├── hashtags.py                # GET /api/hashtags
│       ├── keywords.py                # GET /api/keywords
│       ├── accounts.py                # GET /api/accounts
│       ├── niches.py                  # GET /api/niches
│       └── analyzer.py                # POST /api/analyzer
├── database/
│   └── migrations/
│       └── instagram_trends_schema.sql
└── tasks/
    ├── discover_accounts.py           # Celery task
    ├── discover_hashtags.py           # Celery task
    ├── calculate_trends.py            # Celery task
    └── generate_ai_summaries.py       # Celery task
```

---

## ⚙️ RapidAPI → Internal Endpoint Mapping

| Feature | RapidAPI Endpoint | Internal Endpoint | Data Flow |
|---------|------------------|-------------------|-----------|
| **Top Trends** | `POST /v1/reels` (multiple accounts) | `GET /api/trends` | Aggregate → Cluster → Score → AI Summary |
| **Top Sounds** | `POST /v1/reels` → extract audio | `GET /api/sounds/top` | Extract audio_id → Aggregate → Rank |
| **Top Hashtags** | `POST /v1/search` → `POST /v1/reels` | `GET /api/hashtags/top` | Extract hashtags → Count → Rank |
| **Top Keywords** | `POST /v1/reels` → captions | `GET /api/keywords/top` | Extract keywords → TF-IDF → Rank |
| **Top Accounts** | `POST /v1/search` → `POST /v1/info` | `GET /api/accounts/search` | Search → Profile → Rank by metrics |
| **Top Niches** | Aggregate all above | `GET /api/niches` | Group by category → Aggregate metrics |

---

## 🚀 Implementation Plan

### Phase 1: Data Collection (Week 1-2)
1. ✅ Set up database schema
2. ✅ Create media collector service
3. ✅ Implement account discovery by keyword
4. ✅ Implement hashtag discovery
5. ✅ Implement audio extraction

### Phase 2: Trend Detection (Week 3)
1. ✅ Implement velocity calculator
2. ✅ Implement trend scorer
3. ✅ Implement trend clusterer
4. ✅ Set up scheduled jobs

### Phase 3: AI Integration (Week 4)
1. ✅ Implement AI summarizer
2. ✅ Generate trend details
3. ✅ Extract keywords from captions
4. ✅ Template detection (OCR/vision)

### Phase 4: API Endpoints (Week 5)
1. ✅ Implement all GET endpoints
2. ✅ Add filtering and pagination
3. ✅ Add caching layer
4. ✅ Rate limiting

### Phase 5: Frontend Integration (Week 6)
1. ✅ Connect to API endpoints
2. ✅ Display trends, sounds, hashtags
3. ✅ Implement detail pages
4. ✅ Add search and filters

---

## 📝 Key Implementation Notes

### Rate Limiting Strategy
- **RapidAPI calls:** Batch and cache aggressively
- **Internal API:** Fast responses from cached DB
- **Refresh schedule:** Update trends every 6 hours, sounds/hashtags hourly

### Data Freshness
- **Real-time:** Not possible with scrapers
- **Near real-time:** 6-hour refresh cycle
- **Caching:** 1-hour cache for top lists

### Scalability
- **Database:** Partition by date for media_candidates
- **Jobs:** Use Celery for async processing
- **Caching:** Redis for hot data

---

## 🔗 Related Documentation

- **RapidAPI Docs:** `Backend/docs/rapidapi/instagram-scraper-stable-api.md`
- **Audio Extraction:** `Backend/docs/RAPIDAPI_AUDIO_EXTRACTION_GUIDE.md`
- **Tests:** `Backend/tests/test_instagram_scraper_stable_api.py`

