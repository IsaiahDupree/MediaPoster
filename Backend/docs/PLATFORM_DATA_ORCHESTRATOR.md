# Platform Data Orchestrator

## Overview

The Platform Data Orchestrator is a unified system for efficiently fetching social media data across all platforms with:

- **Failover** - Automatic switching between API providers when one fails
- **Caching** - In-memory cache with TTL to minimize redundant API calls
- **Batching** - Efficient batch operations for multiple accounts/posts
- **Rate Limiting** - Awareness of API quotas per provider
- **Data Population** - Automatic saving to database tables

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Platform Data Orchestrator                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐    │
│  │ TikTok   │   │Instagram │   │ YouTube  │   │ Bluesky  │    │
│  │ Providers│   │ Providers│   │ Provider │   │ Provider │    │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘    │
│       │              │              │              │           │
│       ▼              ▼              ▼              ▼           │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    Provider Registry                     │  │
│  │  - Priority ordering                                     │  │
│  │  - Error tracking                                        │  │
│  │  - Rate limit tracking                                   │  │
│  │  - Auto-disable on failures                              │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                 │
│                              ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                       Cache Layer                        │  │
│  │  - 15 min TTL                                            │  │
│  │  - Key: platform:datatype:identifier                     │  │
│  └─────────────────────────────────────────────────────────┘  │
│                              │                                 │
│                              ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                   Database Population                    │  │
│  │  - social_media_accounts                                 │  │
│  │  - top_engaged_followers                                 │  │
│  │  - posted_content                                        │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## API Providers by Platform

### TikTok
| Priority | Provider | Rate Limit | Endpoints |
|----------|----------|------------|-----------|
| 1 | tiktok-scraper7 | 500/day | profile, posts, comments |
| 2 | tiktok-feature-summary | 100/day | profile, posts |

### Instagram
| Priority | Provider | Rate Limit | Endpoints |
|----------|----------|------------|-----------|
| 1 | instagram-looter2 | 100/day | profile, posts, media |
| 2 | instagram-statistics | 100/day | profile, posts |

### YouTube
| Priority | Provider | Rate Limit | Endpoints |
|----------|----------|------------|-----------|
| 1 | Google YouTube API | 10,000/day | channels, videos, comments |

### Bluesky
| Priority | Provider | Rate Limit | Endpoints |
|----------|----------|------------|-----------|
| 1 | Public AT Protocol | 1,000/day | profile, feed, posts |

---

## API Endpoints

### GET `/api/orchestrator/status`
Get status of all providers.

**Response:**
```json
{
  "providers": {
    "tiktok": [
      {
        "name": "tiktok-scraper7",
        "priority": 1,
        "calls_today": 45,
        "rate_limit": 500,
        "error_count": 0,
        "disabled": false
      }
    ]
  },
  "cache_size": 12
}
```

### POST `/api/orchestrator/refresh-all`
Refresh data for all connected social accounts.

**Response:**
```json
{
  "success": 10,
  "failed": 2,
  "errors": ["twitter/@user: Rate limited"]
}
```

### POST `/api/orchestrator/populate-engagement`
Fetch comprehensive engagement data for a specific account.

**Request:**
```json
{
  "platform": "youtube",
  "username": "UCnDBsELI2OIaEI5yxA77HNA"
}
```

**Response:**
```json
{
  "profile": {
    "followers": 2810,
    "posts": 641,
    "views": 142062
  },
  "posts_fetched": 30,
  "comments_fetched": 156,
  "followers_updated": 14
}
```

### GET `/api/orchestrator/fetch/profile/{platform}/{username}`
Fetch profile data with failover.

### GET `/api/orchestrator/fetch/posts/{platform}/{username}`
Fetch posts with failover.

### GET `/api/orchestrator/fetch/comments/{platform}/{post_id}`
Fetch comments with failover.

---

## Failover Logic

```
Request → Check Cache
              │
         ┌────┴────┐
         │ Cached? │──Yes──▶ Return cached data
         └────┬────┘
              │ No
              ▼
         Get available providers (sorted by priority)
              │
              ▼
         ┌─────────────────┐
         │ Try Provider #1 │
         └────────┬────────┘
                  │
             ┌────┴────┐
             │ Success │──Yes──▶ Cache + Return
             └────┬────┘
                  │ No (429/5xx/timeout)
                  ▼
         ┌─────────────────┐
         │ Mark error      │
         │ Try Provider #2 │
         └────────┬────────┘
                  │
             ┌────┴────┐
             │ Success │──Yes──▶ Cache + Return
             └────┬────┘
                  │ No
                  ▼
         Return error (all providers failed)
```

---

## Data Flow: populate_engagement_data()

This is the main method for comprehensive data collection:

```
1. Fetch Profile
   └─▶ Update social_media_accounts table

2. Fetch Recent Posts (30)
   └─▶ For each post:
       └─▶ Fetch Comments (50)
           └─▶ Extract commenters
               └─▶ Calculate engagement scores
                   └─▶ Update top_engaged_followers table
```

### Engagement Score Calculation
```python
score = comment_count * 10 + like_count * 2

if score >= 30:
    tier = "super_fan"
elif score >= 15:
    tier = "active"  
elif score >= 5:
    tier = "lurker"
else:
    tier = "inactive"
```

---

## Usage Examples

### Python
```python
from services.platform_data_orchestrator import get_orchestrator, Platform

orchestrator = get_orchestrator()

# Fetch single profile
result = await orchestrator.fetch_profile(Platform.YOUTUBE, "UCnDBsELI2OIaEI5yxA77HNA")
if result.success:
    print(f"Subscribers: {result.data['items'][0]['statistics']['subscriberCount']}")

# Populate all engagement data for an account
results = await orchestrator.populate_engagement_data(Platform.YOUTUBE, "UCnDBsELI2OIaEI5yxA77HNA")
print(f"Fetched {results['comments_fetched']} comments")
print(f"Updated {results['followers_updated']} engaged followers")

# Refresh all accounts
refresh_results = await orchestrator.refresh_all_accounts()
print(f"Success: {refresh_results['success']}, Failed: {refresh_results['failed']}")
```

### cURL
```bash
# Check provider status
curl http://localhost:5555/api/orchestrator/status

# Refresh all accounts
curl -X POST http://localhost:5555/api/orchestrator/refresh-all

# Populate engagement for YouTube
curl -X POST http://localhost:5555/api/orchestrator/populate-engagement \
  -H "Content-Type: application/json" \
  -d '{"platform": "youtube", "username": "UCnDBsELI2OIaEI5yxA77HNA"}'

# Fetch specific profile
curl http://localhost:5555/api/orchestrator/fetch/profile/youtube/UCnDBsELI2OIaEI5yxA77HNA
```

---

## Database Tables Populated

### social_media_accounts
Updated fields:
- `followers_count`
- `following_count`
- `posts_count`
- `total_views`
- `total_likes`
- `bio`
- `profile_pic_url`
- `last_fetched_at`

### top_engaged_followers
Updated fields:
- `follower_id`
- `platform`
- `username`
- `display_name`
- `avatar_url`
- `engagement_score`
- `engagement_tier`
- `comment_count`
- `like_count`
- `total_interactions`
- `last_interaction`

---

## Rate Limit Management

- Each provider tracks `calls_today` vs `rate_limit`
- Counters reset daily
- When rate limit exceeded, provider is skipped (not disabled)
- When errors occur 3+ times, provider is temporarily disabled:
  - 3 errors: disabled for 15 minutes
  - 4 errors: disabled for 20 minutes
  - etc.

---

## Related Files

| File | Purpose |
|------|---------|
| `services/platform_data_orchestrator.py` | Main orchestrator service |
| `api/endpoints/data_orchestrator.py` | REST API endpoints |
| `docs/rapidapi/PROVIDER_FAILOVER.md` | Detailed failover documentation |
| `services/rapidapi_social_fetcher.py` | Legacy fetcher (being replaced) |

---

*Last Updated: December 20, 2024*
