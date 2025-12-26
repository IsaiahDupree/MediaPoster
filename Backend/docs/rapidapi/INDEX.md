# RapidAPI Documentation Index

## Your Subscriptions Summary

You have **58 API subscriptions** on RapidAPI. This documentation covers all APIs relevant to MediaPoster.

---

## 📂 Documentation Files

| File | Description |
|------|-------------|
| [INDEX.md](./INDEX.md) | This file - master index |
| [ALL_API_LINKS.md](./ALL_API_LINKS.md) | All 58 API links organized by category |
| [api_registry.json](./api_registry.json) | Machine-readable JSON registry |
| [ENDPOINT_REGISTRY.md](./ENDPOINT_REGISTRY.md) | **Verified endpoints from API testing** |
| [PROVIDER_FAILOVER.md](./PROVIDER_FAILOVER.md) | **Failover strategy & Python implementation** |
| [openapi-unified.yaml](./openapi-unified.yaml) | **Unified OpenAPI schema (normalized)** |
| [tiktok-scraper7.md](./tiktok-scraper7.md) | TikTok Scraper7 detailed docs |
| [tiktok-video-feature-summary.md](./tiktok-video-feature-summary.md) | TikTok Feature Summary docs |
| [instagram-scraper-stable-api.md](./instagram-scraper-stable-api.md) | Instagram Scraper Stable API (RockSolid) detailed docs |
| [instagram-looter2.md](./instagram-looter2.md) | Instagram Looter2 detailed docs |
| [instagram-statistics-api.md](./instagram-statistics-api.md) | Instagram Statistics API docs |
| [yt-api.md](./yt-api.md) | YouTube YT-API detailed docs |
| [threads-api.md](./threads-api.md) | Threads API docs |
| [twitter-api.md](./twitter-api.md) | Twitter/X API docs |
| [linkedin-api.md](./linkedin-api.md) | LinkedIn API docs |
| [soundcloud-api.md](./soundcloud-api.md) | SoundCloud API docs |
| [bluesky-api.md](./bluesky-api.md) | **Bluesky API (FREE, no key needed)** |

---

---

## 📚 API Documentation Files

### Working APIs ✅

| Platform | API | Documentation | Status |
|----------|-----|---------------|--------|
| 🎵 TikTok | Scraper7 | [tiktok-scraper7.md](./tiktok-scraper7.md) | ✅ Working |
| 🎵 TikTok | Video Feature Summary | [tiktok-video-feature-summary.md](./tiktok-video-feature-summary.md) | ✅ Working |
| 📸 Instagram | Scraper Stable API | [instagram-scraper-stable-api.md](./instagram-scraper-stable-api.md) | ✅ Working |
| 📸 Instagram | Looter2 | [instagram-looter2.md](./instagram-looter2.md) | ✅ Working |
| 📸 Instagram | Statistics API | [instagram-statistics-api.md](./instagram-statistics-api.md) | ✅ Working |
| ▶️ YouTube | YT-API | [yt-api.md](./yt-api.md) | ✅ Working |

### Requires Subscription ⚠️

| Platform | API | Documentation | Status |
|----------|-----|---------------|--------|
| 🧵 Threads | Threads API | [threads-api.md](./threads-api.md) | ⚠️ Not subscribed |
| 𝕏 Twitter | The Old Bird | [twitter-api.md](./twitter-api.md) | ⚠️ Rate limited |
| 💼 LinkedIn | Scraper API | [linkedin-api.md](./linkedin-api.md) | ⚠️ Rate limited |
| 🎵 SoundCloud | SoundCloud API | [soundcloud-api.md](./soundcloud-api.md) | ⚠️ Not subscribed |

---

## Quick Reference

### API Hosts

```
# TikTok
tiktok-scraper7.p.rapidapi.com
tiktok-video-feature-summary.p.rapidapi.com

# Instagram  
instagram-scraper-stable-api.p.rapidapi.com
instagram-looter2.p.rapidapi.com
instagram-statistics-api.p.rapidapi.com

# YouTube
yt-api.p.rapidapi.com

# Threads
threads-api4.p.rapidapi.com

# Twitter/X
twitter-api45.p.rapidapi.com

# LinkedIn
linkedin-data-scraper.p.rapidapi.com

# SoundCloud
soundcloud-api3.p.rapidapi.com
```

---

## Working Endpoints Summary

### TikTok Scraper7
- ✅ `/user/info` - User profile
- ✅ `/user/posts` - User videos with metrics
- ✅ `/user/followers` - Followers list
- ✅ `/user/following` - Following list

### Instagram Scraper Stable API
- ✅ `POST /v1/info` - User profile
- ✅ `POST /v1/reels` - User reels with audio
- ✅ `GET /v1/reel_by_shortcode` - Reel details
- ✅ `GET /v1/media_by_shortcode` - Media details
- ✅ `POST /v1/posts` - User posts
- ✅ `POST /v1/search` - Search users/hashtags

### Instagram Looter2
- ✅ `/profile` - User profile with 12 recent posts
- ✅ `/post` - Single post by shortcode

### Instagram Statistics
- ✅ `/community` - Profile stats & engagement

### YT-API
- ✅ `/video/info` - Video details
- ✅ `/search` - Search videos
- ✅ `/playlist` - Playlist data
- ✅ `/comments` - Video comments
- ✅ `/trending` - Trending videos

### TikTok Video Feature Summary
- ✅ `/user/info` - User profile
- ✅ `/user/posts` - User videos

---

## Authentication Header

All APIs require these headers:

```
X-RapidAPI-Key: YOUR_API_KEY
X-RapidAPI-Host: {api-host}.p.rapidapi.com
```

Your API key is stored in: `Backend/.env` → `RAPIDAPI_KEY`

---

## Backfill Scripts

| Script | Platform | Location |
|--------|----------|----------|
| TikTok Metrics | TikTok | `scripts/backfill_tiktok_metrics.py` |
| Instagram Metrics | Instagram | `scripts/backfill_instagram_metrics.py` |

### Usage:
```bash
# TikTok
python scripts/backfill_tiktok_metrics.py
python scripts/backfill_tiktok_metrics.py --dry-run

# Instagram
python scripts/backfill_instagram_metrics.py
python scripts/backfill_instagram_metrics.py --dry-run
```

---

## RapidAPI Links

- **Hub**: https://rapidapi.com/hub
- **Your Subscriptions**: https://rapidapi.com/developer/billing/subscriptions-and-usage
- **Documentation**: https://docs.rapidapi.com

---

## Rate Limits (Free Tier)

| API | Monthly Limit |
|-----|---------------|
| TikTok Scraper7 | 100 |
| Instagram Looter2 | 100 |
| Instagram Statistics | 100 |
| YT-API | 100 |
| Threads API | 100 |
| Twitter API | 50 |
| LinkedIn API | 25 |

---

*Last Updated: December 2024*
