# RapidAPI Scripts & Services Reference

> Quick reference for all RapidAPI integrations in MediaPoster

## Scripts (`Backend/scripts/`)

| Script | API Host | Purpose |
|--------|----------|---------|
| `backfill_tiktok_metrics.py` | `tiktok-scraper7.p.rapidapi.com` | Fetch TikTok video metrics by ID/URL |
| `backfill_instagram_metrics.py` | `instagram-looter2.p.rapidapi.com` | Fetch Instagram post metrics by shortcode |
| `download_from_manifest.py` | `instagram-looter2.p.rapidapi.com` | Download videos from Safari-collected shortcodes |
| `download_tiktok_video.py` | `tiktok-video-no-watermark2.p.rapidapi.com` | Download TikTok videos without watermark |
| `download_competitor_videos.py` | `instagram-looter2.p.rapidapi.com` | Batch download competitor Instagram videos |
| `discover_rapidapi_endpoints.py` | `instagram-scraper-stable-api.p.rapidapi.com` | Test/discover working API endpoints |
| `check_api_status.py` | Multiple | Health check for all API endpoints |

---

## Key Services (`Backend/services/`)

| Service | Description |
|---------|-------------|
| `rapidapi_social_fetcher.py` | Unified fetcher for TikTok/Instagram data |
| `rapidapi_scraper.py` | General-purpose RapidAPI scraper |
| `rapidapi_comments_service.py` | Fetch comments from social posts |
| `realtime_metrics.py` | Live metrics fetching |
| `content_download/platform_downloader.py` | Multi-platform video downloads |
| `music/adapters/soundcloud.py` | SoundCloud track data via RapidAPI |
| `tiktok_captcha_solver.py` | TikTok captcha solving service |
| `competitor_audit/collector.py` | Competitor content collection |
| `scrapers/instagram_scraper.py` | Instagram scraping with provider failover |
| `scrapers/tiktok_providers.py` | TikTok API provider management |
| `influencer_analyzer.py` | Analyze influencer accounts |
| `trend_intelligence/ingest_service.py` | Trend data ingestion |

---

## Verified Working APIs

### TikTok
| API | Host | Endpoints |
|-----|------|-----------|
| TikTok Scraper7 | `tiktok-scraper7.p.rapidapi.com` | `/user/info`, `/user/posts`, `/user/followers`, `/user/following`, `/music/info` |
| TikTok Video Feature Summary | `tiktok-video-feature-summary.p.rapidapi.com` | `/user/info`, `/user/posts` |
| TikTok No Watermark | `tiktok-video-no-watermark2.p.rapidapi.com` | `/` (download) |

### Instagram
| API | Host | Endpoints |
|-----|------|-----------|
| Instagram Looter2 | `instagram-looter2.p.rapidapi.com` | `/profile`, `/post`, `/v1/info`, `/v1/posts` |
| Instagram Statistics | `instagram-statistics-api.p.rapidapi.com` | `/community`, `/posts` |

### YouTube
| API | Host | Endpoints |
|-----|------|-----------|
| YT-API | `yt-api.p.rapidapi.com` | `/video/info`, `/search`, `/playlist`, `/comments`, `/trending`, `/home` |
| YouTube MP3 | `youtube-mp36.p.rapidapi.com` | `/dl` |

### Other Platforms
| API | Host | Endpoints |
|-----|------|-----------|
| Google Map Places | `google-map-places.p.rapidapi.com` | `/maps/api/place/textsearch/json` |
| Local Business Data | `local-business-data.p.rapidapi.com` | `/search` |
| Real-Time Amazon | `real-time-amazon-data.p.rapidapi.com` | `/search` |

---

## NOT Working / Blocked APIs

| API | Host | Status |
|-----|------|--------|
| Instagram Scraper API2 | `instagram-scraper-api2.p.rapidapi.com` | ❌ Returns 401 "Blocked User" |
| Instagram Premium 2023 | `instagram-premium-api-2023.p.rapidapi.com` | ❌ Deprecated |

---

## API Key Configuration

**Location:** `Backend/.env`

```env
RAPIDAPI_KEY=your_key_here
```

**Usage in Python:**
```python
import os
from dotenv import load_dotenv

load_dotenv()
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com"
}
```

---

## Common Usage Examples

### Fetch TikTok User Videos
```python
# Using tiktok-scraper7
response = requests.get(
    "https://tiktok-scraper7.p.rapidapi.com/user/posts",
    headers=headers,
    params={"unique_id": "username", "count": 30}
)
```

### Fetch Instagram Post Info
```python
# Using instagram-looter2
response = requests.get(
    "https://instagram-looter2.p.rapidapi.com/post",
    headers=headers,
    params={"url": "https://www.instagram.com/reel/ABC123/"}
)
```

### Download TikTok Video (No Watermark)
```python
# Using tiktok-video-no-watermark2
response = requests.post(
    "https://tiktok-video-no-watermark2.p.rapidapi.com/",
    headers=headers,
    data={"url": video_url, "hd": "1"}
)
```

---

## Related Documentation

- `Backend/docs/rapidapi/api_registry.json` - Full API registry (58 subscriptions)
- `Backend/docs/rapidapi/ENDPOINT_REGISTRY.md` - Detailed endpoint specs
- `Backend/docs/rapidapi/PROVIDER_FAILOVER.md` - Failover configuration
- `Backend/docs/RAPIDAPI_REFERENCE.md` - Extended reference

---

## Total API Subscriptions: 58

Categories:
- **Social Media:** TikTok (10), Instagram (5), YouTube (19), Twitter (1), LinkedIn (2), Threads (1), Snapchat (1)
- **Music:** SoundCloud (4)
- **Business:** Google Maps (5), Amazon (2), Etsy (1)
- **Other:** Email (3), Search (2), AI (2)

---

*Last updated: January 2026*
