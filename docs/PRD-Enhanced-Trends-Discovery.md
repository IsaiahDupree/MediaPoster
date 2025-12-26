# PRD: Enhanced Trends Discovery System

## Overview

A comprehensive trend discovery and analysis system that identifies what's trending on Instagram by tracking hashtags, keywords, sounds, and content patterns. Uses real-time data from Instagram Scraper Stable API to detect acceleration, not just popularity.

## Core Concept

> **A "trend" isn't just popular. It's popular + accelerating.**

Every trend candidate needs:
- **A trackable unit**: hashtag, sound/audio, or keyword/concept cluster
- **A time window**: last 24h / 72h / 7d
- **A trend score**: velocity + engagement quality + breadth (many creators)

---

## Data Sources

### Instagram Scraper Stable API Endpoints

| Endpoint | Purpose | Data Retrieved |
|----------|---------|----------------|
| `POST /search_ig.php` | Search hashtags & users | Hashtag IDs, names, related terms |
| `GET /hashtag_posts_reels.php` | Posts by hashtag | Media IDs, captions, metrics, timestamps |
| `GET /detailed_media_v2.php` | Detailed media data | play_count, audio metadata, full metrics |
| `GET /reel_detailed.php` | Reel details | Audio ID, music info, engagement |
| `GET /post_comments.php` | Comments | Sentiment, keyword extraction |

---

## System Architecture

### 1. Ingestion Pipeline (Hourly/Daily)

```
┌─────────────────────────────────────────────────────────────────┐
│                    TREND INGESTION PIPELINE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  [Seed Keywords] → Search API → [Hashtag Candidates]            │
│        ↓                              ↓                          │
│  [Niche Config]              [Hashtag Posts/Reels]              │
│        ↓                              ↓                          │
│  [Tracked Hashtags] ←────── [Media Items with Metrics]          │
│                                       ↓                          │
│                              [Detailed Media Data]               │
│                                       ↓                          │
│                              [Audio/Sound Extraction]            │
│                                       ↓                          │
│                              [Keyword Extraction (NLP)]          │
│                                       ↓                          │
│                     ┌─────────────────┴─────────────────┐       │
│                     ↓                 ↓                 ↓       │
│              [Hashtag Trends]  [Sound Trends]  [Keyword Trends] │
│                     ↓                 ↓                 ↓       │
│                     └─────────────────┬─────────────────┘       │
│                                       ↓                          │
│                              [Trend Scoring Engine]              │
│                                       ↓                          │
│                              [AI Trend Brief Generator]          │
│                                       ↓                          │
│                              [Trend Detail Pages]                │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Data Flow

**A) Discover Candidates**
```python
# Seed inputs (configurable per niche)
seed_keywords = ["entrepreneur", "ai tools", "content creator", "viral"]

# Expand via Search API
for keyword in seed_keywords:
    hashtags = search_ig(query=keyword)  # Returns related hashtags
    store_hashtag_candidates(hashtags)
```

**B) Pull Top Posts/Reels Per Hashtag**
```python
for hashtag in tracked_hashtags:
    media = get_hashtag_posts_reels(hashtag_id, pagination_token)
    for item in media:
        store_media_item(
            media_id=item.id,
            caption=item.caption,
            like_count=item.likes,
            comment_count=item.comments,
            timestamp=item.taken_at  # Critical for velocity
        )
```

**C) Enrich Each Media Item**
```python
for media in recent_media:
    details = get_detailed_media_v2(media_id)
    update_media(
        play_count=details.play_count,
        audio_id=details.audio.id,
        audio_title=details.audio.title,
        audio_artist=details.audio.artist
    )
```

---

## Trend Types

### 1. Hashtag Trends

Track per day/hour:
- Number of new reels under that hashtag
- Median plays / play velocity
- Engagement rate: (likes + comments) / plays
- Unique creator count

**Scoring Formula:**
```python
hashtag_score = (
    velocity_of_posts * 0.3 +
    median_play_count * 0.3 +
    unique_creator_count * 0.2 +
    engagement_rate * 0.2
)
```

### 2. Sound/Audio Trends

Group reels by `audio_id`:
- New reels using that audio in last 24-72h
- Median plays + top-decile plays
- Creator diversity (not just one person)

**Scoring Formula:**
```python
sound_score = (
    new_reels_24h * 0.4 +
    median_plays * 0.3 +
    creator_diversity * 0.3
)
```

### 3. Keyword Trends (Emergent)

Instagram doesn't provide keywords directly. Extract from:
- Caption text analysis
- Frequent n-grams (2-5 word phrases)
- Concept clustering (embedding similarity)

**Examples of emergent keywords:**
- "POV: you're the..."
- "3 things I wish I knew"
- "hot take:"
- "nobody talks about this"

**Scoring Formula:**
```python
keyword_score = (
    frequency_in_top_posts * 0.4 +
    engagement_of_posts_with_keyword * 0.3 +
    growth_rate_7d * 0.3
)
```

---

## Database Schema

```sql
-- Tracked hashtags with time series
CREATE TABLE trend_hashtags (
    id UUID PRIMARY KEY,
    hashtag_id TEXT UNIQUE,
    name TEXT NOT NULL,
    niche TEXT,
    
    -- Current metrics
    post_count INTEGER,
    media_count INTEGER,
    
    -- Time series (JSONB for flexibility)
    daily_metrics JSONB,  -- {date: {posts, plays, engagement}}
    
    -- Computed scores
    velocity_24h NUMERIC,
    velocity_7d NUMERIC,
    trend_score NUMERIC,
    
    first_seen_at TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT NOW()
);

-- Tracked sounds/audio
CREATE TABLE trend_sounds (
    id UUID PRIMARY KEY,
    audio_id TEXT UNIQUE,
    title TEXT,
    artist TEXT,
    
    -- Metrics
    usage_count INTEGER,
    daily_usage JSONB,  -- {date: count}
    
    -- Computed
    velocity_24h NUMERIC,
    velocity_7d NUMERIC,
    trend_score NUMERIC,
    
    first_seen_at TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT NOW()
);

-- Extracted keywords from captions
CREATE TABLE trend_keywords (
    id UUID PRIMARY KEY,
    keyword TEXT UNIQUE,
    keyword_type TEXT,  -- 'phrase', 'hook', 'format'
    niche TEXT,
    
    -- Metrics
    occurrence_count INTEGER,
    daily_occurrences JSONB,
    avg_engagement NUMERIC,
    
    -- Computed
    velocity_7d NUMERIC,
    trend_score NUMERIC,
    
    first_seen_at TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT NOW()
);

-- Media items for trend analysis
CREATE TABLE trend_media (
    id UUID PRIMARY KEY,
    media_id TEXT UNIQUE,
    shortcode TEXT,
    
    -- Content
    caption TEXT,
    hashtags TEXT[],
    
    -- Metrics
    play_count INTEGER,
    like_count INTEGER,
    comment_count INTEGER,
    
    -- Audio
    audio_id TEXT,
    audio_title TEXT,
    
    -- Extracted keywords
    extracted_keywords TEXT[],
    
    -- Timestamps
    posted_at TIMESTAMP,
    fetched_at TIMESTAMP DEFAULT NOW()
);

-- Generated trend briefs
CREATE TABLE trend_briefs (
    id UUID PRIMARY KEY,
    trend_type TEXT,  -- 'hashtag', 'sound', 'keyword'
    trend_id TEXT,    -- Reference to the trend
    
    -- AI-generated content
    summary TEXT,
    why_trending TEXT,
    content_ideas JSONB,
    format_tips JSONB,
    suggested_hooks TEXT[],
    
    -- Supporting data
    top_examples JSONB,  -- Top performing media
    regions TEXT[],
    
    generated_at TIMESTAMP DEFAULT NOW()
);
```

---

## Trend Brief Generation

For each trend, generate a structured brief:

### Input Data
```python
trend_input = {
    "trend_type": "hashtag",
    "trend_id": "entrepreneurmindset",
    "top_reels": [
        {"caption": "...", "plays": 1.2M, "likes": 50K},
        # ... more examples
    ],
    "common_patterns": {
        "caption_templates": ["3 things...", "POV:..."],
        "emoji_patterns": ["🔥", "💰", "📈"],
        "hashtag_sets": [["entrepreneur", "business", "success"]]
    },
    "metrics": {
        "velocity_24h": 2.5,  # 2.5x growth
        "avg_plays": 500000,
        "creator_count": 150
    }
}
```

### AI Analysis Output
```json
{
    "summary": "Entrepreneur mindset content is surging with 2.5x growth...",
    "why_trending": "New year motivation combined with...",
    "content_ideas": [
        "Share your morning routine as an entrepreneur",
        "3 books that changed my business mindset",
        "POV: You quit your 9-5 to follow your dreams"
    ],
    "format_tips": [
        "Use talking head with B-roll overlay",
        "3-card text format works best",
        "Hook in first 0.5 seconds"
    ],
    "suggested_hooks": [
        "Nobody talks about this part of entrepreneurship...",
        "3 things I wish I knew before starting...",
        "Hot take: Your 9-5 is not the problem..."
    ],
    "top_sounds": ["audio_123", "audio_456"]
}
```

---

## API Endpoints

```
# Hashtag Trends
GET  /api/trends/hashtags
GET  /api/trends/hashtags/{hashtag_id}
POST /api/trends/hashtags/search?query=entrepreneur

# Sound Trends  
GET  /api/trends/sounds
GET  /api/trends/sounds/{audio_id}

# Keyword Trends
GET  /api/trends/keywords
GET  /api/trends/keywords/{keyword}

# Trend Briefs
GET  /api/trends/briefs
GET  /api/trends/briefs/{trend_id}
POST /api/trends/briefs/generate

# Discovery
POST /api/trends/discover  # Trigger discovery pipeline
GET  /api/trends/discover/status
```

---

## Implementation Phases

### Phase 1: Hashtag Discovery (Day 1)
- [ ] Implement Search API integration (`/search_ig.php`)
- [ ] Store hashtag candidates with metrics
- [ ] Basic velocity calculation
- [ ] Update existing trends API

### Phase 2: Media Enrichment (Day 2)
- [ ] Implement Posts/Reels by hashtag
- [ ] Detailed media data fetching
- [ ] Audio/sound extraction
- [ ] Store time series data

### Phase 3: Keyword Extraction (Day 3)
- [ ] Caption text analysis
- [ ] N-gram extraction
- [ ] Keyword clustering
- [ ] Trend detection for keywords

### Phase 4: Scoring Engine (Day 4)
- [ ] Velocity calculation (24h, 7d)
- [ ] Composite trend scores
- [ ] Ranking algorithms
- [ ] Region detection (if available)

### Phase 5: AI Brief Generation (Day 5)
- [ ] Pattern mining from top content
- [ ] LLM integration for summaries
- [ ] Content idea generation
- [ ] Trend detail page data

---

## Configuration

```python
TREND_CONFIG = {
    "niches": [
        {
            "name": "entrepreneurship",
            "seed_keywords": ["entrepreneur", "business", "startup", "founder"],
            "seed_hashtags": ["entrepreneurmindset", "businessowner"]
        },
        {
            "name": "content_creation", 
            "seed_keywords": ["content creator", "viral", "tiktok tips"],
            "seed_hashtags": ["contentcreator", "viraltips"]
        }
    ],
    "update_frequency_hours": 3,
    "velocity_windows": ["24h", "72h", "7d"],
    "min_posts_for_trend": 50,
    "top_n_for_brief": 20
}
```

---

## Rate Limits & Optimization

- Cache API responses (1-3 hour TTL)
- Batch requests where possible
- Implement request throttling
- Store raw responses for re-processing
- Fallback gracefully when endpoints fail

---

## Success Metrics

1. **Coverage**: Trends detected across niches
2. **Accuracy**: Trends that actually perform
3. **Timeliness**: Detection speed vs. viral peak
4. **Actionability**: Users creating content from briefs
5. **Freshness**: Data recency

---

## Appendix: Keyword Extraction Examples

From caption analysis, detect patterns like:

| Pattern Type | Examples |
|--------------|----------|
| **Hook Phrases** | "Nobody talks about...", "Hot take:", "POV:" |
| **Format Markers** | "3 things I wish...", "Day in the life", "What I eat in a day" |
| **Engagement Bait** | "Save this for later", "Comment 'YES' if you agree" |
| **Trend Indicators** | "This is blowing up", "Going viral", "Trending now" |
