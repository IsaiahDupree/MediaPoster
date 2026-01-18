# RapidAPI Developer Guide - MediaPoster

> **Complete documentation for implementing and using third-party RapidAPI integrations in the MediaPoster project.**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Authentication](#authentication)
3. [Working APIs by Platform](#working-apis-by-platform)
4. [Service Files & Locations](#service-files--locations)
5. [Scripts & Tools](#scripts--tools)
6. [Code Examples](#code-examples)
7. [Failover Strategy](#failover-strategy)
8. [Rate Limits & Best Practices](#rate-limits--best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

1. RapidAPI account with active subscriptions
2. API key stored in environment

### Setup

```bash
# Add to Backend/.env
RAPIDAPI_KEY=your_api_key_here
```

### Test API Connection

```bash
cd Backend
python scripts/check_api_status.py
```

---

## Authentication

All RapidAPI calls require these headers:

```python
headers = {
    "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
    "X-RapidAPI-Host": "{api-host}.p.rapidapi.com"
}
```

**Key Location:** `Backend/.env` → `RAPIDAPI_KEY`

---

## Working APIs by Platform

### 🎵 TikTok

#### TikTok Scraper7 (PRIMARY ✅)
- **Host:** `tiktok-scraper7.p.rapidapi.com`
- **Docs:** https://rapidapi.com/JoTucker/api/tiktok-scraper7
- **Status:** ✅ Working

| Endpoint | Method | Parameters | Description |
|----------|--------|------------|-------------|
| `/user/info` | GET | `unique_id` | Get user profile |
| `/user/posts` | GET | `unique_id` | Get user videos with metrics |
| `/user/followers` | GET | `unique_id` | Get followers list |
| `/user/following` | GET | `unique_id` | Get following list |
| `/music/info` | GET | `music_id` | Get music/sound info |

**Response Example (user/posts):**
```json
{
  "code": 0,
  "data": {
    "videos": [{
      "video_id": "7123456789",
      "title": "Video title",
      "play_count": 10000,
      "digg_count": 500,
      "comment_count": 50,
      "share_count": 20,
      "cover": "https://..."
    }]
  }
}
```

**Python Usage:**
```python
import httpx
import os

async def get_tiktok_user(username: str):
    headers = {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
        "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com",
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://tiktok-scraper7.p.rapidapi.com/user/info",
            headers=headers,
            params={"unique_id": username}
        )
        return response.json()
```

#### TikTok Video Feature Summary (SECONDARY)
- **Host:** `tiktok-video-feature-summary.p.rapidapi.com`
- **Status:** ✅ Working (limited endpoints)

| Endpoint | Method | Parameters |
|----------|--------|------------|
| `/user/info` | GET | `unique_id` |
| `/user/posts` | GET | `unique_id` |

#### TikTok Video No Watermark
- **Host:** `tiktok-video-no-watermark2.p.rapidapi.com`
- **Status:** ✅ Working

| Endpoint | Method | Parameters | Description |
|----------|--------|------------|-------------|
| `/` | GET | `url` | Download TikTok video without watermark |

---

### 📸 Instagram

#### Instagram Looter2 (PRIMARY ✅)
- **Host:** `instagram-looter2.p.rapidapi.com`
- **Docs:** https://rapidapi.com/irror-systems/api/instagram-looter
- **Status:** ✅ Working

| Endpoint | Method | Parameters | Description |
|----------|--------|------------|-------------|
| `/profile` | GET | `username` | Get profile with 12 recent posts |
| `/post` | GET | `shortcode` | Get single post by shortcode |

**Response Example (profile):**
```json
{
  "status": true,
  "username": "the_isaiah_dupree",
  "full_name": "Isaiah Dupree",
  "biography": "Bio text here",
  "edge_followed_by": { "count": 1000 },
  "edge_follow": { "count": 500 },
  "edge_owner_to_timeline_media": {
    "count": 150,
    "edges": [{
      "node": {
        "shortcode": "ABC123",
        "edge_liked_by": { "count": 100 },
        "edge_media_to_comment": { "count": 10 },
        "video_view_count": 5000
      }
    }]
  }
}
```

**Python Usage:**
```python
async def get_instagram_profile(username: str):
    headers = {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
        "X-RapidAPI-Host": "instagram-looter2.p.rapidapi.com",
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://instagram-looter2.p.rapidapi.com/profile",
            headers=headers,
            params={"username": username}
        )
        return response.json()
```

#### Instagram Scraper Stable API (RECOMMENDED FOR REELS)
- **Host:** `instagram-scraper-stable-api.p.rapidapi.com`
- **Docs:** https://rapidapi.com/thetechguy32744/api/instagram-scraper-stable-api
- **Status:** ✅ Working

| Endpoint | Method | Parameters | Description |
|----------|--------|------------|-------------|
| `/v1/info` | POST | `username_or_id_or_url` | Get user profile |
| `/v1/reels` | POST | `username_or_id_or_url`, `count`, `pagination_token` | Get reels with audio URLs |
| `/v1/reel_by_shortcode` | GET | `shortcode` | Get reel details |
| `/v1/media_by_shortcode` | GET | `shortcode` | Get media by shortcode |
| `/v1/posts` | POST | `username_or_id_or_url`, `count` | Get user posts |
| `/v1/search` | POST | `query` | Search users/hashtags |

**Key Features:**
- Real-time data (no caching)
- Audio URL extraction from reels
- Video download URLs
- Play count for videos
- Pagination support

#### Instagram Statistics API
- **Host:** `instagram-statistics-api.p.rapidapi.com`
- **Status:** ✅ Working

| Endpoint | Method | Parameters | Description |
|----------|--------|------------|-------------|
| `/community` | GET | `url` (profile URL) | Get profile stats & engagement |

**Response Example:**
```json
{
  "data": {
    "followers": 1000,
    "following": 500,
    "postsCount": 150,
    "avgLikes": 100,
    "avgComments": 10,
    "engagementRate": 5.5,
    "qualityScore": 85
  }
}
```

#### ❌ NOT WORKING
- `instagram-scraper-api2.p.rapidapi.com` - Returns 401 "Blocked User"
- `/v1/reels` endpoint on instagram-looter2 - Returns 404

---

### ▶️ YouTube

#### YT-API (PRIMARY ✅)
- **Host:** `yt-api.p.rapidapi.com`
- **Docs:** https://rapidapi.com/ytjar/api/yt-api
- **Status:** ✅ Working

| Endpoint | Method | Parameters | Description |
|----------|--------|------------|-------------|
| `/video/info` | GET | `id` (video ID) | Get video details |
| `/search` | GET | `query` | Search videos |
| `/playlist` | GET | `id` | Get playlist |
| `/comments` | GET | `id` | Get video comments |
| `/trending` | GET | `geo` (optional) | Get trending videos |
| `/home` | GET | - | Get home feed |

**Response Example (video/info):**
```json
{
  "id": "dQw4w9WgXcQ",
  "title": "Video Title",
  "viewCount": 1000000,
  "likeCount": 50000,
  "commentCount": 5000,
  "channelId": "UCxxxxxxx",
  "channelTitle": "Channel Name",
  "publishedAt": "2024-01-01T00:00:00Z"
}
```

#### YouTube MP3 Download
- **Host:** `youtube-mp36.p.rapidapi.com`
- **Status:** ✅ Working

| Endpoint | Method | Parameters | Description |
|----------|--------|------------|-------------|
| `/dl` | GET | `id` (video ID) | Download as MP3 |

---

### 🐦 Twitter/X

#### The Old Bird
- **Host:** `twitter-api45.p.rapidapi.com`
- **Status:** ⚠️ Rate limited on free tier

| Endpoint | Method | Parameters | Status |
|----------|--------|------------|--------|
| `/user.php` | GET | `username` | 403 (requires PRO) |
| `/tweet.php` | GET | `tweet_id` | 429 (rate limited) |
| `/search.php` | GET | `query` | 429 (rate limited) |

**Note:** Requires PRO subscription for reliable access.

---

### 💼 LinkedIn

#### Real-Time LinkedIn Scraper
- **Host:** `linkedin-data-scraper.p.rapidapi.com`
- **Status:** ⚠️ Rate limited

| Endpoint | Method | Parameters |
|----------|--------|------------|
| `/get-profile-data-by-url` | GET | `url` |

---

### 📍 Google Maps & Local Business

#### Google Map Places
- **Host:** `google-map-places.p.rapidapi.com`
- **Status:** ✅ Working

| Endpoint | Method | Parameters |
|----------|--------|------------|
| `/maps/api/place/textsearch/json` | GET | `query` |

#### Local Business Data
- **Host:** `local-business-data.p.rapidapi.com`
- **Status:** ✅ Working

| Endpoint | Method | Parameters |
|----------|--------|------------|
| `/search` | GET | `query`, `location` |

---

### 🛒 Amazon

#### Real-Time Amazon Data
- **Host:** `real-time-amazon-data.p.rapidapi.com`
- **Status:** ✅ Working

| Endpoint | Method | Parameters |
|----------|--------|------------|
| `/search` | GET | `query`, `country` |

---

### 🦋 Bluesky (FREE - No RapidAPI needed)

Bluesky uses a public API that doesn't require a RapidAPI key:

```python
async def get_bluesky_profile(handle: str):
    clean_handle = handle.replace("@", "")
    if not clean_handle.endswith(".bsky.social"):
        clean_handle = f"{clean_handle}.bsky.social"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile",
            params={"actor": clean_handle}
        )
        return response.json()
```

---

## Service Files & Locations

### Core Services

| File | Purpose | Location |
|------|---------|----------|
| `rapidapi_social_fetcher.py` | Unified social media fetcher | `Backend/services/` |
| `rapidapi_scraper.py` | Generic scraper service | `Backend/services/` |
| `rapidapi_comments_service.py` | Comments fetching service | `Backend/services/` |
| `rapidapi_adapter.py` | Instagram adapter | `Backend/services/instagram/adapters/` |

### API Endpoints

| File | Purpose | Location |
|------|---------|----------|
| `rapidapi_metrics.py` | Metrics API endpoints | `Backend/api/` |
| `rapidapi_comments.py` | Comments API endpoints | `Backend/api/endpoints/` |

### Configuration

| File | Purpose | Location |
|------|---------|----------|
| `.env` | API key storage | `Backend/` |
| `api_registry.json` | API registry (58 APIs) | `Backend/docs/rapidapi/` |

---

## Scripts & Tools

### Backfill Scripts

```bash
# Backfill TikTok metrics from API
cd Backend
python scripts/backfill_tiktok_metrics.py
python scripts/backfill_tiktok_metrics.py --dry-run  # Test without updating

# Backfill Instagram metrics from API
python scripts/backfill_instagram_metrics.py
python scripts/backfill_instagram_metrics.py --dry-run
```

### API Status Check

```bash
# Check all API statuses
python scripts/check_api_status.py
```

### Endpoint Discovery

```bash
# Discover available endpoints for an API
python scripts/discover_rapidapi_endpoints.py

# Scrape endpoint documentation
python scripts/scrape_rapidapi_endpoints.py
```

### Testing Scripts

| Script | Purpose |
|--------|---------|
| `test_instagram_looter_music.py` | Test Instagram music extraction |
| `test_rapidapi_integration.py` | Integration tests |
| `test_rapidapi_metrics.py` | Metrics API tests |

---

## Code Examples

### 1. Fetch TikTok User Videos with Metrics

```python
import httpx
import os
from typing import Dict, List

async def fetch_tiktok_videos(username: str) -> List[Dict]:
    """Fetch all videos for a TikTok user with metrics."""
    headers = {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
        "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com",
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://tiktok-scraper7.p.rapidapi.com/user/posts",
            headers=headers,
            params={"unique_id": username}
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("videos", [])
        return []

# Extract metrics from video
def parse_video_metrics(video: Dict) -> Dict:
    stats = video.get("stats", video)
    return {
        "views": stats.get("playCount") or stats.get("play_count") or 0,
        "likes": stats.get("diggCount") or stats.get("digg_count") or 0,
        "comments": stats.get("commentCount") or stats.get("comment_count") or 0,
        "shares": stats.get("shareCount") or stats.get("share_count") or 0,
    }
```

### 2. Fetch Instagram Profile with Posts

```python
async def fetch_instagram_profile(username: str) -> Dict:
    """Fetch Instagram profile with recent posts."""
    headers = {
        "X-RapidAPI-Key": os.getenv("RAPIDAPI_KEY"),
        "X-RapidAPI-Host": "instagram-looter2.p.rapidapi.com",
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://instagram-looter2.p.rapidapi.com/profile",
            headers=headers,
            params={"username": username}
        )
        
        if response.status_code == 200:
            return response.json()
        return {}

def extract_instagram_metrics(profile: Dict) -> Dict:
    """Extract metrics from Instagram profile response."""
    return {
        "followers": profile.get("edge_followed_by", {}).get("count", 0),
        "following": profile.get("edge_follow", {}).get("count", 0),
        "posts_count": profile.get("edge_owner_to_timeline_media", {}).get("count", 0),
    }
```

### 3. Using the Unified Social Fetcher

```python
from services.rapidapi_social_fetcher import (
    get_social_fetcher,
    Platform,
    SocialAccount
)

async def fetch_all_analytics():
    fetcher = get_social_fetcher()
    
    accounts = [
        SocialAccount(Platform.TIKTOK, "isaiah_dupree"),
        SocialAccount(Platform.INSTAGRAM, "the_isaiah_dupree"),
        SocialAccount(Platform.YOUTUBE, "UCnDBsELI2OlaEl5yxA77HNA"),
    ]
    
    results = await fetcher.fetch_all_accounts(accounts)
    
    for analytics in results:
        print(f"{analytics.platform.value}: {analytics.followers_count} followers")
```

### 4. Extract Video ID from URLs

```python
import re
from typing import Optional

def extract_tiktok_video_id(url: str) -> Optional[str]:
    """Extract TikTok video ID from URL."""
    patterns = [
        r'tiktok\.com/.*/video/(\d+)',
        r'tiktok\.com/.*[?&]video_id=(\d+)',
        r'/video/(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def extract_instagram_shortcode(url: str) -> Optional[str]:
    """Extract Instagram shortcode from URL."""
    patterns = [
        r'instagram\.com/(?:reel|p)/([A-Za-z0-9_-]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None
```

---

## Failover Strategy

### Provider Priority

| Platform | Primary | Secondary | Fallback |
|----------|---------|-----------|----------|
| TikTok | tiktok-scraper7 | tiktok-video-feature-summary | - |
| Instagram | instagram-looter2 | instagram-statistics-api | - |
| YouTube | yt-api | - | - |
| Twitter | twitter-api45 | - | - |
| LinkedIn | linkedin-data-scraper | fresh-linkedin-scraper | - |

### Failover Implementation

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

@dataclass
class ProviderConfig:
    name: str
    host: str
    priority: int
    error_count: int = 0
    disabled_until: Optional[datetime] = None

PROVIDERS = {
    "tiktok": [
        ProviderConfig("tiktok-scraper7", "tiktok-scraper7.p.rapidapi.com", 1),
        ProviderConfig("tiktok-feature", "tiktok-video-feature-summary.p.rapidapi.com", 2),
    ],
    "instagram": [
        ProviderConfig("instagram-looter2", "instagram-looter2.p.rapidapi.com", 1),
        ProviderConfig("instagram-stats", "instagram-statistics-api.p.rapidapi.com", 2),
    ],
}

async def call_with_failover(platform: str, endpoint: str, params: Dict):
    """Call API with automatic failover to secondary providers."""
    providers = [p for p in PROVIDERS.get(platform, []) 
                 if not p.disabled_until or p.disabled_until < datetime.now()]
    providers.sort(key=lambda p: p.priority)
    
    for provider in providers:
        try:
            response = await make_api_call(provider.host, endpoint, params)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 429:
                provider.error_count += 1
                if provider.error_count >= 3:
                    provider.disabled_until = datetime.now() + timedelta(minutes=5)
                continue
        except Exception:
            continue
    
    raise Exception(f"All providers failed for {platform}")
```

---

## Rate Limits & Best Practices

### Free Tier Limits

| API | Monthly Requests |
|-----|------------------|
| TikTok Scraper7 | 100 |
| Instagram Looter2 | 100 |
| Instagram Statistics | 100 |
| YT-API | 100 |
| Twitter API | 50 |
| LinkedIn API | 25 |

### Best Practices

1. **Rate Limiting:** Add delays between requests
   ```python
   await asyncio.sleep(1.5)  # 1.5 seconds between calls
   ```

2. **Caching:** Cache responses to minimize API calls
   ```python
   # Use Redis or in-memory cache
   cached = await cache.get(f"profile:{username}")
   if cached:
       return cached
   ```

3. **Batch Operations:** Group by user to minimize calls
   ```python
   # Fetch all videos for a user once, then match locally
   videos = await fetch_user_videos(username)
   video_lookup = {v["video_id"]: v for v in videos}
   ```

4. **Error Handling:** Always handle rate limits gracefully
   ```python
   if response.status_code == 429:
       retry_after = int(response.headers.get("Retry-After", 60))
       await asyncio.sleep(retry_after)
   ```

---

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Invalid API key | Check `RAPIDAPI_KEY` in `.env` |
| 403 Forbidden | Not subscribed | Subscribe to API on RapidAPI |
| 404 Not Found | Endpoint doesn't exist | Use documented endpoints only |
| 429 Too Many Requests | Rate limited | Wait and retry, use failover |
| 500 Server Error | API provider issue | Try secondary provider |

### Debugging

```python
# Enable logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Print full response
response = await client.get(url, headers=headers, params=params)
print(f"Status: {response.status_code}")
print(f"Headers: {response.headers}")
print(f"Body: {response.text[:500]}")
```

### Testing API Connection

```bash
# Quick test with curl
curl -X GET "https://tiktok-scraper7.p.rapidapi.com/user/info?unique_id=tiktok" \
  -H "X-RapidAPI-Key: YOUR_KEY" \
  -H "X-RapidAPI-Host: tiktok-scraper7.p.rapidapi.com"
```

---

## Documentation Files

| File | Description | Location |
|------|-------------|----------|
| `INDEX.md` | Master documentation index | `Backend/docs/rapidapi/` |
| `ALL_API_LINKS.md` | All 58 API links by category | `Backend/docs/rapidapi/` |
| `ENDPOINT_REGISTRY.md` | Verified endpoints | `Backend/docs/rapidapi/` |
| `PROVIDER_FAILOVER.md` | Failover strategy | `Backend/docs/rapidapi/` |
| `api_registry.json` | Machine-readable registry | `Backend/docs/rapidapi/` |
| `tiktok-scraper7.md` | TikTok API docs | `Backend/docs/rapidapi/` |
| `instagram-looter2.md` | Instagram API docs | `Backend/docs/rapidapi/` |
| `instagram-statistics-api.md` | Instagram Stats docs | `Backend/docs/rapidapi/` |
| `yt-api.md` | YouTube API docs | `Backend/docs/rapidapi/` |

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAPIDAPI QUICK REFERENCE                      │
├─────────────────────────────────────────────────────────────────┤
│ TikTok (tiktok-scraper7.p.rapidapi.com)                         │
│   GET /user/info?unique_id={username}                           │
│   GET /user/posts?unique_id={username}                          │
├─────────────────────────────────────────────────────────────────┤
│ Instagram (instagram-looter2.p.rapidapi.com)                    │
│   GET /profile?username={username}                              │
│   GET /post?shortcode={shortcode}                               │
├─────────────────────────────────────────────────────────────────┤
│ YouTube (yt-api.p.rapidapi.com)                                 │
│   GET /video/info?id={video_id}                                 │
│   GET /search?query={query}                                     │
│   GET /trending                                                 │
├─────────────────────────────────────────────────────────────────┤
│ API Key Location: Backend/.env → RAPIDAPI_KEY                   │
│ Backfill Scripts: Backend/scripts/backfill_*.py                 │
│ Service Files: Backend/services/rapidapi_*.py                   │
└─────────────────────────────────────────────────────────────────┘
```

---

*Last Updated: January 2025*
*Total API Subscriptions: 58*
*Verified Working: 12*
