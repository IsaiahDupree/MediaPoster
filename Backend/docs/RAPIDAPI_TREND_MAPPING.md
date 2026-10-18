# RapidAPI → Trend Analysis Feature Mapping

**Quick Reference:** How each RapidAPI endpoint maps to trend analysis features

## 🎯 Feature → RapidAPI Endpoint Mapping

### Top Trends

**What we need:** Clustered media showing trending formats/patterns

**RapidAPI Endpoints Used:**
1. `POST /v1/search` → Find accounts by keyword
2. `POST /v1/reels` → Get reels from multiple accounts
3. `POST /v1/posts` → Get posts from accounts
4. `GET /v1/media_by_shortcode` → Get detailed metrics

**Data Flow:**
```
Search (keyword) → Accounts → Reels/Posts → Extract:
  - Caption text (for format detection)
  - Hashtags (for clustering)
  - Audio/music_id (for clustering)
  - Engagement metrics (for scoring)
  - Timestamps (for velocity)
```

**Internal Processing:**
- Cluster by: music_id, hashtag sets, caption similarity
- Score by: velocity, acceleration, engagement rate
- AI: Generate trend summary, formats, ideas

---

### Top Music/Sounds

**What we need:** Most used audio tracks with trending metrics

**RapidAPI Endpoints Used:**
1. `POST /v1/reels` → Extract audio metadata

**Data Extraction:**
```json
// From POST /v1/reels response
clips_metadata.music_info.music_asset_info = {
  "audio_id": "id",           // ← Use for grouping
  "title": "Title",            // ← Display
  "display_artist": "Artist",  // ← Display
  "progressive_download_url": "url"  // ← Audio file
}

// Or original sound:
clips_metadata.original_sound_info.audio_asset_info = {
  "progressive_download_url": "url"
}
```

**Internal Processing:**
- Group by `audio_id` or `music_id`
- Count usage across all collected media
- Calculate velocity (new uses in 24h)
- Rank by trending_score

---

### Top Hashtags

**What we need:** Most used hashtags with growth metrics

**RapidAPI Endpoints Used:**
1. `POST /v1/search` → Search for hashtags (returns media_count)
2. `POST /v1/reels` → Extract hashtags from captions
3. `POST /v1/posts` → Extract hashtags from captions

**Data Extraction:**
```json
// From POST /v1/search response
{
  "data": {
    "hashtags": [{
      "name": "fitness",
      "id": "hashtag_id",
      "media_count": 123456  // ← Total posts
    }]
  }
}

// From POST /v1/reels response
{
  "caption": {
    "text": "Check this out #fitness #workout #gym"  // ← Extract hashtags
  }
}
```

**Internal Processing:**
- Extract hashtags from captions (regex: `#\w+`)
- Count frequency across media
- Track usage over time (velocity)
- Rank by trending_score

---

### Top Keywords

**What we need:** Trending keywords extracted from captions/transcripts

**RapidAPI Endpoints Used:**
1. `POST /v1/reels` → Get captions
2. `POST /v1/posts` → Get captions
3. (Optional) Whisper API → Get transcripts

**Data Extraction:**
```json
// From POST /v1/reels response
{
  "caption": {
    "text": "Amazon finds that changed my life! These products are amazing."
  }
}
// Extract keywords: "amazon finds", "products", "amazing"
```

**Internal Processing:**
- Extract keywords using TF-IDF or KeyBERT
- Track frequency and velocity
- Link to accounts using keywords
- Rank by trending_score

---

### Top Accounts per Keyword/Niche

**What we need:** Accounts ranked by niche/keyword association

**RapidAPI Endpoints Used:**
1. `POST /v1/search` → Search accounts by keyword
2. `POST /v1/info` → Get account profile/metrics
3. `POST /v1/reels` → Get account content
4. `POST /v1/posts` → Get account content

**Data Flow:**
```
Search (keyword) → Accounts → Profile → Content → Analyze:
  - Follower count
  - Engagement rate
  - Content type (reels/posts)
  - Top hashtags used
  - Top sounds used
```

**Internal Processing:**
- Calculate engagement_rate = (likes + comments) / followers
- Track content frequency
- Rank by niche/keyword association + engagement

---

### Top Niches

**What we need:** Category-level aggregations

**RapidAPI Endpoints Used:**
- Aggregate from all above endpoints

**Internal Processing:**
- Group accounts/content by category
- Aggregate metrics per niche
- Rank niches by total activity/trends

---

## 📊 Complete Data Collection Strategy

### Discovery Sources

| Source | RapidAPI Endpoint | Frequency | Purpose |
|--------|------------------|-----------|---------|
| **Keyword Search** | `POST /v1/search` | Every 6h | Find accounts by keyword |
| **Account Profiles** | `POST /v1/info` | Daily | Update account metrics |
| **Account Reels** | `POST /v1/reels` | Every 6h | Get latest content + audio |
| **Account Posts** | `POST /v1/posts` | Every 6h | Get latest content |
| **Hashtag Search** | `POST /v1/search` | Daily | Discover hashtags |
| **Media Details** | `GET /v1/media_by_shortcode` | On-demand | Get detailed metrics |

### Collection Schedule

```python
# Every 6 hours
- Discover accounts by keywords (fitness, amazon finds, etc.)
- Get reels from trending accounts
- Extract audio, hashtags, keywords
- Update media_candidates table

# Every 24 hours
- Calculate trend scores
- Cluster into trend groups
- Update trending_sounds, trending_hashtags, trending_keywords
- Generate AI summaries for new trends

# Every hour
- Update velocity metrics
- Refresh top lists
```

---

## 🔧 Implementation Code Examples

### Discover Accounts by Keyword

```python
async def discover_accounts_by_keyword(keyword: str):
    """Find accounts using RapidAPI search"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://instagram-scraper-stable-api.p.rapidapi.com/v1/search",
            headers={
                "X-RapidAPI-Key": RAPIDAPI_KEY,
                "X-RapidAPI-Host": "instagram-scraper-stable-api.p.rapidapi.com",
                "Content-Type": "application/json"
            },
            json={"query": keyword}
        )
        
        data = response.json()
        accounts = data.get("data", {}).get("users", [])
        
        for account in accounts:
            # Get full profile
            profile = await get_profile(account["username"])
            
            # Get their content
            reels = await get_reels(account["username"])
            
            # Store in database
            await store_account_data(account, profile, reels, keyword)
```

### Extract Audio from Reels

```python
async def extract_trending_audio(username: str):
    """Extract audio metadata from user reels"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://instagram-scraper-stable-api.p.rapidapi.com/v1/reels",
            headers={...},
            json={"username_or_id_or_url": username, "count": 50}
        )
        
        data = response.json()
        items = data.get("data", {}).get("items", [])
        
        audio_tracks = {}
        
        for item in items:
            clips = item.get("clips_metadata", {})
            
            # Try music first
            music_info = clips.get("music_info", {})
            if music_info:
                music_asset = music_info.get("music_asset_info", {})
                audio_id = music_asset.get("audio_id")
                
                if audio_id:
                    if audio_id not in audio_tracks:
                        audio_tracks[audio_id] = {
                            "title": music_asset.get("title"),
                            "artist": music_asset.get("display_artist"),
                            "usage_count": 0,
                            "total_views": 0
                        }
                    
                    audio_tracks[audio_id]["usage_count"] += 1
                    audio_tracks[audio_id]["total_views"] += item.get("play_count", 0)
        
        # Store in trending_sounds table
        await store_trending_sounds(audio_tracks)
```

### Extract Hashtags from Captions

```python
import re

def extract_hashtags(caption_text: str) -> List[str]:
    """Extract hashtags from caption"""
    if not caption_text:
        return []
    
    # Find all hashtags
    hashtags = re.findall(r'#(\w+)', caption_text)
    return [tag.lower() for tag in hashtags]

# Usage:
async def process_reel_captions():
    reels = await get_reels("username")
    
    for reel in reels:
        caption = reel.get("caption", {}).get("text", "")
        hashtags = extract_hashtags(caption)
        
        # Update hashtag counts
        for tag in hashtags:
            await increment_hashtag_count(tag, reel)
```

---

## 📈 Trend Score Calculation Example

```python
async def calculate_trend_score(media_id: str):
    """Calculate trend score for a media item"""
    media = await get_media(media_id)
    
    # Get historical views (from previous snapshots)
    views_6h_ago = await get_views_at(media_id, hours_ago=6)
    views_24h_ago = await get_views_at(media_id, hours_ago=24)
    
    current_views = media.play_count
    
    # Calculate velocity
    velocity_6h = current_views - views_6h_ago
    velocity_24h = current_views - views_24h_ago
    
    # Calculate acceleration
    velocity_6h_ago = views_6h_ago - views_30h_ago
    acceleration = velocity_6h - velocity_6h_ago
    
    # Calculate engagement rate
    engagement_rate = (media.like_count + media.comment_count) / max(current_views, 1)
    
    # Calculate trend score
    score = (
        min(1.0, velocity_24h / 100000) * 0.4 +  # Velocity (40%)
        min(1.0, max(0, acceleration / 50000)) * 0.2 +  # Acceleration (20%)
        min(1.0, engagement_rate * 10) * 0.25 +  # Engagement (25%)
        freshness_score(media.taken_at) * 0.1 +  # Freshness (10%)
        diversity_score(media.trend_group_id) * 0.05  # Diversity (5%)
    )
    
    await update_media_score(media_id, score, velocity_24h, acceleration)
```

---

## 🎯 Quick Start: Building the System

### Step 1: Set Up Database
```bash
# Run migration
psql -d your_db -f Backend/database/migrations/instagram_trends_schema.sql
```

### Step 2: Create Collection Service
```python
# Backend/services/trend_discovery/account_discovery.py
from services.instagram.adapters.instagram_stable_adapter import InstagramStableAdapter

adapter = InstagramStableAdapter()

# Discover accounts
accounts = await adapter.search("fitness coach")

# Get their content
for account in accounts:
    reels = await adapter.get_user_reels(account.username)
    # Store in database
```

### Step 3: Schedule Collection Jobs
```python
# Backend/tasks/discover_accounts.py
from celery import Celery

@celery.task
def discover_accounts_job():
    keywords = ["fitness coach", "amazon finds", "copywriter", ...]
    for keyword in keywords:
        discover_accounts_by_keyword(keyword)
```

### Step 4: Calculate Trends
```python
# Backend/tasks/calculate_trends.py
@celery.task
def calculate_trends_job():
    # Calculate scores
    calculate_all_trend_scores()
    
    # Cluster media
    cluster_media_into_trends()
    
    # Generate AI summaries
    generate_trend_summaries()
```

---

## 📚 Full Documentation

- **Complete Spec:** `Backend/docs/INSTAGRAM_TREND_ANALYSIS_SPEC.md`
- **RapidAPI Docs:** `Backend/docs/rapidapi/instagram-scraper-stable-api.md`
- **Audio Guide:** `Backend/docs/RAPIDAPI_AUDIO_EXTRACTION_GUIDE.md`

