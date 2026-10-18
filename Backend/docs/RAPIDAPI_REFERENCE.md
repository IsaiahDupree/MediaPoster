# RapidAPI Social Media APIs Reference

## Your Subscriptions (58 total)

Based on your RapidAPI hub, here are the relevant social media APIs for metrics backfill:

---

## 🎵 TikTok APIs

### 1. TikTok Scraper7 (WORKING ✅)
- **Host**: `tiktok-scraper7.p.rapidapi.com`
- **Status**: Tested and working
- **Free Tier**: 100 requests/month

#### Endpoints:
| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/user/info` | GET | Get user profile | `unique_id` (username) |
| `/user/posts` | GET | Get user's videos with metrics | `unique_id` (username) |

#### Response (user/posts):
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "videos": [
      {
        "video_id": "7583730892892392759",
        "title": "Video title",
        "play_count": 93,
        "digg_count": 3,
        "comment_count": 1,
        "share_count": 0,
        "cover": "https://..."
      }
    ]
  }
}
```

### 2. TikTok Video Feature Summary
- **Host**: `tiktok-video-feature-summary.p.rapidapi.com`
- **Endpoints**: `/user/info`, `/video/info`

### 3. TikTok API (by apibox)
- **Host**: `tiktok-api.p.rapidapi.com`
- **Endpoints**: Multiple post/user endpoints

### 4. Tiktok Scraper (by TIKWM) - Rating: 10/10
- **Host**: Various
- **Features**: HD video without watermark, trends, users, posts

---

## 📸 Instagram APIs

### 1. Instagram Looter2 (WORKING ✅)
- **Host**: `instagram-looter2.p.rapidapi.com`
- **Status**: Tested and working
- **Free Tier**: 100 requests/month

#### Endpoints:
| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/profile` | GET | Get user profile with posts | `username` |

#### Response (profile):
```json
{
  "status": true,
  "username": "the_isaiah_dupree",
  "full_name": "Isaiah Dupree",
  "biography": "...",
  "edge_followed_by": { "count": 1234 },
  "edge_follow": { "count": 567 },
  "edge_owner_to_timeline_media": {
    "count": 42,
    "edges": [
      {
        "node": {
          "shortcode": "DOVvhx1AKQr",
          "edge_liked_by": { "count": 54 },
          "edge_media_to_comment": { "count": 3 },
          "video_view_count": 517,
          "is_video": true
        }
      }
    ]
  }
}
```

### 2. Instagram Statistics API (WORKING ✅)
- **Host**: `instagram-statistics-api.p.rapidapi.com`
- **Features**: Demographics, engagement rates, historical data

#### Endpoints:
| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/community` | GET | Get profile stats | `url` (profile URL) |
| `/posts` | GET | Get posts with date range | `url`, `from`, `to` |

### 3. Instagram Scraper API2 (BLOCKED ❌)
- **Host**: `instagram-scraper-api2.p.rapidapi.com`
- **Status**: Returns 401 "Blocked User" - subscription may be inactive

### 4. Instagram Premium API 2023
- **Host**: `instagram-premium-api-2023.p.rapidapi.com`
- **Note**: Deprecated - use Social Media Data API1 instead

### 5. Instagram Scraper (by JoTucker)
- **Host**: Various
- **Rating**: 9.9/10

---

## 🧵 Threads API

### Threads API (by apibox)
- **Host**: `threads-api4.p.rapidapi.com`
- **Status**: Fast and stable
- **Rating**: 9.9/10

#### Endpoints:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/user/info` | GET | Get user profile |
| `/user/posts` | GET | Get user posts |
| `/post/info` | GET | Get single post |

---

## ▶️ YouTube APIs

### 1. YT-API (by ytjar) - Rating: 9.9/10
- **Host**: `yt-api.p.rapidapi.com`
- **Features**: Video data, shorts, channels, search, playlists

#### Endpoints:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/video/info` | GET | Get video details |
| `/channel/info` | GET | Get channel info |
| `/search` | GET | Search videos |

### 2. YouTube v3 (by Glavier)
- **Host**: `youtube-v31.p.rapidapi.com`
- **Standard YouTube Data API wrapper

### 3. YouTube Media Downloader
- **Host**: Various
- **Features**: Download videos, subtitles, comments

---

## 𝕏 Twitter/X APIs

### The Old Bird
- **Host**: `the-old-bird.p.rapidapi.com`
- **Rating**: 9.9/10
- **Features**: Tweet details, followers, followings, search

#### Endpoints:
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/user/info` | GET | Get user profile |
| `/user/tweets` | GET | Get user tweets |
| `/tweet/info` | GET | Get tweet details |

---

## 💼 LinkedIn APIs

### 1. Real-Time LinkedIn Scraper API
- **Host**: `linkedin-data-scraper.p.rapidapi.com`
- **Rating**: 9.9/10
- **Features**: Profile and company data

### 2. Fresh LinkedIn Scraper API
- **Host**: Various
- **Rating**: 9.9/10

---

## 👻 Snapchat API

### Snapchat (by social miner)
- **Host**: Various
- **Rating**: 9.9/10
- **Telegram**: https://t.me/social_miner_news

---

## 🎵 SoundCloud APIs

### 1. SoundCloud API (by Patrick)
- **Host**: Various
- **Rating**: 9.6/10
- **Features**: Search artists, tracks, albums, stream URLs

### 2. SoundCloud Scraper
- **Host**: Various
- **Features**: Albums, playlists, profiles, downloads

---

## Common Headers

All RapidAPI requests require these headers:
```
X-RapidAPI-Key: YOUR_API_KEY
X-RapidAPI-Host: {api-host}.p.rapidapi.com
```

---

## Rate Limits by Tier

| Tier | Monthly Limit | Rate |
|------|---------------|------|
| BASIC (Free) | 50-100 | 1 req/sec |
| PRO | 10,000+ | 5 req/sec |
| ULTRA | 100,000+ | 10 req/sec |
| MEGA | 500,000+ | 20 req/sec |

---

## Backfill Scripts

### TikTok
```bash
python scripts/backfill_tiktok_metrics.py
python scripts/backfill_tiktok_metrics.py --dry-run
```

### Instagram
```bash
python scripts/backfill_instagram_metrics.py
python scripts/backfill_instagram_metrics.py --dry-run
```

### Account Mappings (Instagram)
Edit the `ACCOUNT_MAPPINGS` dict in `backfill_instagram_metrics.py`:
```python
ACCOUNT_MAPPINGS = {
    "670": "the_isaiah_dupree",  # Blotato ID -> Instagram username
}
```

---

## API Usage Tracking

The backend tracks API usage in `Backend/data/api_usage/`:
- `budgets.json` - Monthly limits and current usage
- `usage_records.json` - Individual API call logs

Dashboard: http://localhost:5557/api-usage

---

## Tested & Working Endpoints Summary

| Platform | API | Host | Status |
|----------|-----|------|--------|
| TikTok | Scraper7 | tiktok-scraper7.p.rapidapi.com | ✅ Working |
| Instagram | Looter2 | instagram-looter2.p.rapidapi.com | ✅ Working |
| Instagram | Statistics | instagram-statistics-api.p.rapidapi.com | ✅ Working |
| Instagram | Scraper API2 | instagram-scraper-api2.p.rapidapi.com | ❌ Blocked |

---

## Links

- RapidAPI Hub: https://rapidapi.com/hub
- Your Subscriptions: https://rapidapi.com/developer/billing/subscriptions-and-usage
- API Documentation: https://docs.rapidapi.com

---

*Last Updated: December 2024*
