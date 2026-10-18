# Data Hydration Architecture

## Overview

A comprehensive system for efficiently fetching, storing, and serving social media data across all pages with:
- **Single Source of Truth** - All pages pull from centralized database tables
- **Master Refresh** - One button populates everything
- **API Failover** - Multiple providers per platform
- **Efficient Caching** - Minimize redundant API calls

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND PAGES                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │
│  │Analytics │  │Content   │  │Followers │  │ People   │  │ Posted   │     │
│  │Dashboard │  │Perform.  │  │/Top Fans │  │          │  │ Content  │     │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘     │
│       │             │             │             │             │            │
│       └─────────────┴─────────────┴──────┬──────┴─────────────┘            │
│                                          │                                  │
│                                          ▼                                  │
│                              ┌───────────────────┐                         │
│                              │  🔄 RE-FETCH      │                         │
│                              │     BUTTON        │                         │
│                              └─────────┬─────────┘                         │
│                                        │                                    │
└────────────────────────────────────────┼────────────────────────────────────┘
                                         │
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           HYDRATION API                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    POST /api/hydration/refresh         GET /api/hydration/page/{page}      │
│         │                                        │                          │
│         ▼                                        ▼                          │
│    ┌──────────────────────────────────────────────────────────────┐        │
│    │              DATA HYDRATION SERVICE                          │        │
│    │                                                              │        │
│    │   master_refresh()          get_analytics_overview()        │        │
│    │   _refresh_accounts()       get_content_performance()       │        │
│    │   _refresh_posts()          get_top_fans()                  │        │
│    │   _refresh_comments()       get_people()                    │        │
│    │   _refresh_followers()                                      │        │
│    │   _refresh_metrics()                                        │        │
│    └──────────────────────────────────────────────────────────────┘        │
│                       │                                                     │
└───────────────────────┼─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PLATFORM DATA ORCHESTRATOR                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│    ┌─────────────────────────────────────────────────────────────┐         │
│    │                    PROVIDER REGISTRY                         │         │
│    │                                                              │         │
│    │  TikTok:    [scraper7] ──▶ [feature-summary]                │         │
│    │  Instagram: [looter2] ──▶ [statistics]                       │         │
│    │  YouTube:   [Google API]                                     │         │
│    │  Bluesky:   [Public AT Protocol]                            │         │
│    │  Twitter:   [api45]                                          │         │
│    └─────────────────────────────────────────────────────────────┘         │
│                       │                                                     │
│                       ▼                                                     │
│    ┌─────────────────────────────────────────────────────────────┐         │
│    │                    FAILOVER LOGIC                            │         │
│    │                                                              │         │
│    │  1. Check cache (15 min TTL)                                │         │
│    │  2. Try primary provider                                     │         │
│    │  3. On 429/5xx → Try secondary provider                      │         │
│    │  4. On 3+ errors → Disable provider temporarily              │         │
│    │  5. Track rate limits per provider                          │         │
│    └─────────────────────────────────────────────────────────────┘         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATABASE TABLES                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐                        │
│  │ social_media_accounts│  │    posted_content    │                        │
│  │                      │  │                      │                        │
│  │ - id                 │  │ - id                 │                        │
│  │ - platform           │  │ - platform_post_id   │                        │
│  │ - username           │  │ - platform           │                        │
│  │ - followers_count    │  │ - views, likes       │                        │
│  │ - posts_count        │  │ - comments, shares   │                        │
│  │ - total_views        │  │ - engagement_rate    │                        │
│  │ - last_fetched_at    │  │ - analytics_updated  │                        │
│  └──────────────────────┘  └──────────────────────┘                        │
│                                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐                        │
│  │top_engaged_followers │  │   hydration_cache    │                        │
│  │                      │  │                      │                        │
│  │ - follower_id        │  │ - key                │                        │
│  │ - platform           │  │ - value (JSONB)      │                        │
│  │ - username           │  │ - updated_at         │                        │
│  │ - engagement_score   │  │                      │                        │
│  │ - engagement_tier    │  │ Keys:                │                        │
│  │ - comment_count      │  │ - account_totals     │                        │
│  │ - like_count         │  │ - platform_breakdown │                        │
│  │ - rank               │  │ - engagement_stats   │                        │
│  └──────────────────────┘  └──────────────────────┘                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: Master Refresh

When user clicks "Re-Fetch", the following happens in order:

```
1. ACCOUNTS (10-30 sec)
   └── For each active account:
       └── fetch_profile() with failover
       └── Update social_media_accounts

2. POSTS (30-60 sec)
   └── For each account:
       └── fetch_posts() with failover
       └── Upsert into posted_content

3. COMMENTS (30-60 sec)
   └── For recent posts (30 days):
       └── fetch_comments() with failover
       └── Extract commenters

4. FOLLOWERS (1-2 sec)
   └── Save extracted commenters to top_engaged_followers
   └── Recalculate engagement_tier
   └── Update global + platform rankings

5. METRICS (< 1 sec)
   └── Aggregate totals into hydration_cache
   └── Pre-compute platform breakdown
   └── Pre-compute engagement stats
```

---

## API Endpoints

### Hydration Control

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/hydration/status` | GET | Check refresh status, record counts |
| `/api/hydration/refresh` | POST | Master refresh (blocks until done) |
| `/api/hydration/refresh-background` | POST | Start refresh in background |

### Page Data Providers

| Endpoint | Method | Serves Page |
|----------|--------|-------------|
| `/api/hydration/page/analytics` | GET | Analytics Dashboard |
| `/api/hydration/page/content-performance` | GET | Content Performance |
| `/api/hydration/page/followers` | GET | Followers / Top Fans |
| `/api/hydration/page/people` | GET | People |

---

## Frontend Integration

### Before: Direct API Calls (Inefficient)

```tsx
// Each page calls different endpoints
const Analytics = () => {
  fetch('/api/social-accounts/accounts');
  fetch('/api/social-analytics/overview');
  // Multiple API calls, no caching
}

const Followers = () => {
  fetch('/api/social-analytics/followers');
  // Separate call, may duplicate work
}
```

### After: Hydrated Data (Efficient)

```tsx
// Single source of truth
const Analytics = () => {
  const data = await fetch('/api/hydration/page/analytics');
  // Pre-computed, cached, fast
}

const Followers = () => {
  const data = await fetch('/api/hydration/page/followers');
  // Same underlying data, consistent
}

// One refresh button updates everything
const handleRefresh = async () => {
  await fetch('/api/hydration/refresh', { method: 'POST' });
  // All pages now have fresh data
}
```

---

## Provider Failover Details

### Per-Platform Providers

| Platform | Primary | Fallback | Rate Limit |
|----------|---------|----------|------------|
| TikTok | tiktok-scraper7 | tiktok-feature-summary | 500/day |
| Instagram | instagram-looter2 | instagram-statistics | 100/day |
| YouTube | Google API (direct) | - | 10,000/day |
| Bluesky | Public AT Protocol | - | 1,000/day |
| Twitter | twitter-api45 | - | 100/day |

### Failover Triggers

| Error | Action |
|-------|--------|
| 429 Rate Limited | Try next provider |
| 5xx Server Error | Try next provider |
| Timeout | Mark error, try next |
| 3+ Consecutive Errors | Disable provider 15+ min |

---

## Database Schema

### hydration_cache

```sql
CREATE TABLE hydration_cache (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

Cached Keys:
- `account_totals` - Aggregate follower/post/view counts
- `platform_breakdown` - Per-platform stats
- `engagement_stats` - Super fans / active / lurker counts

### top_engaged_followers

```sql
CREATE TABLE top_engaged_followers (
    id SERIAL PRIMARY KEY,
    follower_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    username TEXT NOT NULL,
    display_name TEXT,
    avatar_url TEXT,
    engagement_score FLOAT,
    engagement_tier TEXT,  -- super_fan, active, lurker, inactive
    comment_count INTEGER,
    like_count INTEGER,
    total_interactions INTEGER,
    rank INTEGER,
    platform_rank INTEGER,
    UNIQUE(platform, follower_id)
);
```

---

## Usage Examples

### Trigger Full Refresh

```bash
# Synchronous (wait for completion)
curl -X POST http://localhost:5555/api/hydration/refresh

# Background (returns immediately)
curl -X POST http://localhost:5555/api/hydration/refresh-background

# Selective refresh
curl -X POST http://localhost:5555/api/hydration/refresh \
  -H "Content-Type: application/json" \
  -d '{"domains": ["accounts", "metrics"]}'
```

### Check Status

```bash
curl http://localhost:5555/api/hydration/status
```

Response:
```json
{
  "last_full_refresh": "2024-12-20T22:15:00",
  "accounts_count": 13,
  "posts_count": 20,
  "followers_count": 20,
  "refresh_in_progress": false
}
```

### Get Page Data

```bash
# Analytics page
curl http://localhost:5555/api/hydration/page/analytics

# Followers with filter
curl "http://localhost:5555/api/hydration/page/followers?platform=youtube&tier=super_fan"
```

---

## Files

| File | Purpose |
|------|---------|
| `services/platform_data_orchestrator.py` | API failover + fetching |
| `services/data_hydration_service.py` | Centralized data management |
| `api/endpoints/data_orchestrator.py` | Orchestrator API |
| `api/endpoints/data_hydration.py` | Hydration API |
| `docs/PLATFORM_DATA_ORCHESTRATOR.md` | Orchestrator docs |
| `docs/DATA_HYDRATION_ARCHITECTURE.md` | This document |

---

## Benefits

1. **Efficiency** - One refresh populates all pages
2. **Consistency** - All pages show same data
3. **Resilience** - Failover between API providers
4. **Speed** - Pre-computed aggregates for fast page loads
5. **Observability** - Status endpoint shows refresh progress

---

*Last Updated: December 20, 2024*
