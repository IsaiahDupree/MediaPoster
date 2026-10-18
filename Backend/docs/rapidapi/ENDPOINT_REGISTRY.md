# RapidAPI Endpoint Registry (Verified)

## Discovery Method
Endpoints verified by direct API testing with your RapidAPI key on December 20, 2024.

---

## 🎵 TikTok APIs

### TikTok Scraper7 (PRIMARY ✅)
- **Host**: `tiktok-scraper7.p.rapidapi.com`
- **Docs**: https://rapidapi.com/JoTucker/api/tiktok-scraper7
- **Status**: ✅ Working

| Endpoint | Method | Status | Parameters | Description |
|----------|--------|--------|------------|-------------|
| `/user/info` | GET | ✅ | `unique_id` | Get user profile |
| `/user/posts` | GET | ✅ | `unique_id` | Get user videos with metrics |
| `/user/followers` | GET | ✅ | `unique_id` | Get followers list |
| `/user/following` | GET | ✅ | `unique_id` | Get following list |
| `/music/info` | GET | ✅ | `music_id` | Get music/sound info |

**Response Fields (user/posts)**:
```json
{
  "data": {
    "videos": [{
      "video_id": "string",
      "title": "string",
      "play_count": 0,
      "digg_count": 0,
      "comment_count": 0,
      "share_count": 0,
      "cover": "url"
    }]
  }
}
```

---

### TikTok Video Feature Summary
- **Host**: `tiktok-video-feature-summary.p.rapidapi.com`
- **Docs**: https://rapidapi.com/voyagel/api/tiktok-video-feature-summary
- **Status**: ✅ Working (limited)

| Endpoint | Method | Status | Parameters |
|----------|--------|--------|------------|
| `/user/info` | GET | ✅ | `unique_id` |
| `/user/posts` | GET | ✅ | `unique_id` |

---

### TikTok Scraper (TIKWM)
- **Host**: `tiktok-scraper.p.rapidapi.com`
- **Status**: ⚠️ Rate limited (429 errors)
- **Note**: May require higher tier subscription

---

## 📸 Instagram APIs

### Instagram Scraper Stable API (PRIMARY ✅)
- **Host**: `instagram-scraper-stable-api.p.rapidapi.com`
- **Provider**: RockSolid APIs (thetechguy32744)
- **Docs**: https://rapidapi.com/thetechguy32744/api/instagram-scraper-stable-api
- **Status**: ✅ Working
- **Last Verified**: 2024-12-25

| Endpoint | Method | Status | Parameters | Description |
|----------|--------|--------|------------|-------------|
| `/v1/info` | POST | ✅ | `username_or_id_or_url` | Get user profile with followers, bio, etc. |
| `/v1/reels` | POST | ✅ | `username_or_id_or_url`, `count`, `pagination_token` | Get user reels with audio URLs |
| `/v1/reel_by_shortcode` | GET | ✅ | `shortcode` | Get detailed reel data by shortcode |
| `/v1/media_by_shortcode` | GET | ✅ | `shortcode` | Get media (post/reel) by shortcode |
| `/v1/posts` | POST | ✅ | `username_or_id_or_url`, `count`, `pagination_token` | Get user posts (photos/videos/carousels) |
| `/v1/search` | POST | ✅ | `query` | Search for users and hashtags |

**Key Features**:
- Real-time data (no caching)
- Audio URL extraction from reels
- Video download URLs
- Play count for videos
- Pagination support

**Response Example (reels)**:
```json
{
  "data": {
    "items": [{
      "id": "reel_id",
      "code": "shortcode",
      "video_versions": [{"url": "https://..."}],
      "clips_metadata": {
        "music_info": {
          "music_asset_info": {
            "progressive_download_url": "https://audio.mp3"
          }
        }
      },
      "play_count": 12345,
      "like_count": 678
    }]
  }
}
```

### Instagram Looter2 (SECONDARY ✅)
- **Host**: `instagram-looter2.p.rapidapi.com`
- **Docs**: https://rapidapi.com/irror-systems/api/instagram-looter
- **Status**: ✅ Working

| Endpoint | Method | Status | Parameters | Description |
|----------|--------|--------|------------|-------------|
| `/profile` | GET | ✅ | `username` | Get profile with 12 recent posts |

**Response Fields**:
```json
{
  "status": true,
  "username": "string",
  "full_name": "string",
  "biography": "string",
  "edge_followed_by": { "count": 0 },
  "edge_owner_to_timeline_media": {
    "edges": [{
      "node": {
        "shortcode": "string",
        "edge_liked_by": { "count": 0 },
        "edge_media_to_comment": { "count": 0 },
        "video_view_count": 0
      }
    }]
  }
}
```

---

### Instagram Statistics API
- **Host**: `instagram-statistics-api.p.rapidapi.com`
- **Docs**: https://rapidapi.com/starter-llp-starter-llp-default/api/instagram-statistics-api
- **Status**: ✅ Working

| Endpoint | Method | Status | Parameters | Description |
|----------|--------|--------|------------|-------------|
| `/community` | GET | ✅ | `url` (profile URL) | Get profile stats & engagement |

**Response Fields**:
```json
{
  "data": {
    "followers": 0,
    "following": 0,
    "postsCount": 0,
    "avgLikes": 0,
    "avgComments": 0,
    "engagementRate": 0.0,
    "qualityScore": 0
  }
}
```

---

## ▶️ YouTube APIs

### YT-API (PRIMARY ✅)
- **Host**: `yt-api.p.rapidapi.com`
- **Docs**: https://rapidapi.com/ytjar/api/yt-api
- **Status**: ✅ Working (6 endpoints)

| Endpoint | Method | Status | Parameters | Description |
|----------|--------|--------|------------|-------------|
| `/video/info` | GET | ✅ | `id` (video ID) | Get video details |
| `/search` | GET | ✅ | `query` | Search videos |
| `/playlist` | GET | ✅ | `id` | Get playlist |
| `/comments` | GET | ✅ | `id` | Get video comments |
| `/trending` | GET | ✅ | `geo` (optional) | Get trending videos |
| `/home` | GET | ✅ | - | Get home feed |

**Response Fields (video/info)**:
```json
{
  "id": "string",
  "title": "string",
  "viewCount": 0,
  "likeCount": 0,
  "commentCount": 0,
  "channelId": "string",
  "channelTitle": "string",
  "publishedAt": "string"
}
```

---

## 𝕏 Twitter/X APIs

### The Old Bird (Twitter API)
- **Host**: `twitter-api45.p.rapidapi.com`
- **Docs**: https://rapidapi.com/data-hungry-beast/api/the-old-bird
- **Status**: ⚠️ Rate limited on free tier

| Endpoint | Method | Status | Parameters |
|----------|--------|--------|------------|
| `/user.php` | GET | 403 | `username` |
| `/tweet.php` | GET | 429 | `tweet_id` |
| `/search.php` | GET | 429 | `query` |

**Note**: Requires PRO subscription for reliable access.

---

## 🧵 Threads API

### Threads API (apibox)
- **Host**: `threads-api4.p.rapidapi.com`
- **Docs**: https://rapidapi.com/apibox/api/threads-api
- **Status**: ❌ Not subscribed (404 errors)

**Note**: Need to subscribe to this API on RapidAPI.

---

## 💼 LinkedIn APIs

### Real-Time LinkedIn Scraper
- **Host**: `linkedin-data-scraper.p.rapidapi.com`
- **Docs**: https://rapidapi.com/rockapis/api/real-time-linkedin-scraper-api
- **Status**: ⚠️ Rate limited

### Fresh LinkedIn Scraper
- **Host**: `fresh-linkedin-scraper-api.p.rapidapi.com`
- **Docs**: https://rapidapi.com/saleleads/api/fresh-linkedin-scraper-api
- **Status**: ⚠️ Rate limited

---

## 📍 Google Maps APIs

### Google Map Places
- **Host**: `google-map-places.p.rapidapi.com`
- **Status**: ✅ Working

| Endpoint | Method | Status | Parameters |
|----------|--------|--------|------------|
| `/maps/api/place/textsearch/json` | GET | ✅ | `query` |

---

## 🏪 Local Business Data
- **Host**: `local-business-data.p.rapidapi.com`
- **Status**: ✅ Working

| Endpoint | Method | Status | Parameters |
|----------|--------|--------|------------|
| `/search` | GET | ✅ | `query`, `location` |

---

## 🛒 Amazon APIs

### Real-Time Amazon Data
- **Host**: `real-time-amazon-data.p.rapidapi.com`
- **Status**: ✅ Working

| Endpoint | Method | Status | Parameters |
|----------|--------|--------|------------|
| `/search` | GET | ✅ | `query`, `country` |

---

## 🎵 YouTube MP3

### YouTube MP3 (ytjar)
- **Host**: `youtube-mp36.p.rapidapi.com`
- **Status**: ✅ Working

| Endpoint | Method | Status | Parameters |
|----------|--------|--------|------------|
| `/dl` | GET | ✅ | `id` (video ID) |

---

## 🎵 TikTok No Watermark

### TikTok Video No Watermark
- **Host**: `tiktok-video-no-watermark2.p.rapidapi.com`
- **Status**: ✅ Working

| Endpoint | Method | Status | Parameters |
|----------|--------|--------|------------|
| `/` | GET | ✅ | `url` (TikTok video URL) |

---

## 👻 Snapchat

### Snapchat API
- **Host**: `snapchat.p.rapidapi.com`
- **Status**: ⚠️ Rate limited (429)

---

## 🤖 Perplexity AI

### Perplexity API
- **Host**: `perplexity-ai.p.rapidapi.com`
- **Status**: ⚠️ Rate limited (429)

---

## Provider Priority Matrix

| Platform | Primary Provider | Secondary | Fallback |
|----------|-----------------|-----------|----------|
| TikTok | tiktok-scraper7 | tiktok-video-feature-summary | tiktok-no-watermark |
| Instagram | instagram-looter2 | instagram-statistics-api | - |
| YouTube | yt-api | youtube-mp36 | - |
| Twitter | the-old-bird | - | - |
| Threads | threads-api4 | - | - |
| LinkedIn | linkedin-data-scraper | fresh-linkedin-scraper | - |
| Google Maps | google-map-places | local-business-data | - |
| Amazon | real-time-amazon-data | - | - |
| Snapchat | snapchat | - | - |
| AI | perplexity-ai | - | - |

---

## Capability Coverage

| Capability | TikTok | Instagram | YouTube | Twitter | LinkedIn |
|------------|--------|-----------|---------|---------|----------|
| user.profile | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| user.posts | ✅ | ✅ | ✅ | ⚠️ | ⚠️ |
| user.followers | ✅ | ❌ | ❌ | ⚠️ | ⚠️ |
| video.info | ❌ | ❌ | ✅ | ❌ | ❌ |
| video.comments | ❌ | ❌ | ✅ | ❌ | ❌ |
| search | ❌ | ❌ | ✅ | ⚠️ | ⚠️ |
| trending | ❌ | ❌ | ✅ | ❌ | ❌ |
| analytics | ❌ | ✅ | ❌ | ❌ | ❌ |

✅ = Working | ⚠️ = Rate Limited | ❌ = Not Available

---

## Authentication

All APIs require these headers:
```
X-RapidAPI-Key: YOUR_RAPIDAPI_KEY
X-RapidAPI-Host: {host}.p.rapidapi.com
```

---

## Failover Strategy

```python
PROVIDER_PRIORITY = {
    "tiktok": ["tiktok-scraper7", "tiktok-video-feature-summary"],
    "instagram": ["instagram-looter2", "instagram-statistics-api"],
    "youtube": ["yt-api"],
    "twitter": ["twitter-api45"],
    "linkedin": ["linkedin-data-scraper", "fresh-linkedin-scraper-api"],
}

async def call_with_failover(platform: str, endpoint: str, params: dict):
    for provider in PROVIDER_PRIORITY[platform]:
        try:
            response = await call_api(provider, endpoint, params)
            if response.status_code == 200:
                return response.json()
        except Exception:
            continue
    raise Exception(f"All {platform} providers failed")
```

---

*Last Updated: December 20, 2024*
*Discovery Method: Direct API testing with httpx*
