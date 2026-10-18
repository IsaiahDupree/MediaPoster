# PRD: Blotato Video Queue & Publishing Controls

**Owner:** @isaiahdupree  
**Date:** 2026-02-17  
**Status:** In Progress  

---

## Problem Statement

The current system can publish content through Blotato to 20+ social accounts across 9 platforms, but lacks:

1. **No unified queue view** — Can't see all scheduled/pending videos across all Blotato accounts in one place.
2. **No runtime publishing rate controls** — `posts_per_day` is hardcoded in various places; can't adjust on the fly.
3. **No per-platform throttling** — Can't say "max 3 TikTok videos/day, 2 Instagram reels/day."
4. **No pause/resume** — Can't halt all publishing without stopping the entire scheduler.
5. **No external server API** — Another server (e.g., Safari Automation, dashboard, or mobile app) can't query or control the publishing pipeline.

## Existing Infrastructure

| Component | File | What it does |
|-----------|------|-------------|
| `BlotatoAPI` | `services/blotato_api.py` | Low-level HTTP client for Blotato v2 API |
| `BlotatoService` | `services/blotato_service.py` | Account registry (20 accounts), event bus publish |
| `PostScheduler` | `services/post_scheduler.py` | Background worker that publishes `scheduled_posts` at their time |
| `AdaptiveScheduler` | `services/adaptive_scheduler_service.py` | AI-driven schedule generation, content scoring, fatigue guard |
| `blotato_router.py` | `api/blotato_router.py` | REST endpoints for direct/bulk/multi-platform publish |
| `post_scheduler_api.py` | `api/endpoints/post_scheduler_api.py` | Start/stop scheduler, view queue, retry/cancel |
| `scheduled_posts` | DB table | Stores scheduled posts with status, platform, time |

## Solution: VideoPublishingController

A new service layer that sits **between** the existing scheduler and Blotato, providing centralized rate control, queue management, and an API callable from any server.

### Architecture

```
External Server (Safari Automation, Dashboard, Mobile)
        │
        ▼  HTTP API
┌──────────────────────────────────┐
│  /api/publishing/*  endpoints    │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│   VideoPublishingController      │  ← NEW: central control plane
│                                  │
│   • Runtime config (DB-backed)   │
│   • Per-platform rate limits     │
│   • Global pause/resume          │
│   • Queue inspection & reorder   │
│   • Daily counters & throttling  │
└──────────────┬───────────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
  PostScheduler   BlotatoService
  (timing)        (delivery)
```

### Data Model

#### Table: `publishing_config`

Stores runtime-adjustable publishing settings (single row, updated in place).

| Column | Type | Default | Description |
|--------|------|---------|-------------|
| `id` | serial PK | — | |
| `global_enabled` | boolean | true | Master on/off switch |
| `global_videos_per_day` | int | 8 | Total videos across all platforms |
| `global_posts_per_day` | int | 12 | Total posts (video + text) |
| `platform_limits` | jsonb | `{}` | Per-platform daily caps, e.g. `{"tiktok": 4, "instagram": 3}` |
| `posting_windows` | jsonb | `{}` | Time windows, e.g. `{"start": "08:00", "end": "23:00", "tz": "America/New_York"}` |
| `min_interval_minutes` | int | 30 | Minimum gap between posts on same platform |
| `priority_order` | jsonb | `[]` | Platform priority for when budget is limited |
| `updated_at` | timestamptz | now() | Last config change |
| `updated_by` | text | 'system' | Who changed it |

#### Table: `video_publish_queue`

Unified view of all videos waiting to be published through Blotato.

| Column | Type | Description |
|--------|------|-------------|
| `id` | uuid PK | |
| `video_id` | text | Reference to source video |
| `title` | text | Display title |
| `video_url` | text | Media URL (Google Drive, local, etc.) |
| `thumbnail_url` | text | Optional thumbnail |
| `caption` | text | Post caption |
| `hashtags` | jsonb | `["#tag1", "#tag2"]` |
| `platform` | text | Target platform |
| `account_id` | text | Blotato account ID |
| `account_username` | text | For display |
| `status` | text | `queued`, `scheduled`, `publishing`, `published`, `failed`, `paused`, `cancelled` |
| `priority` | int | 1 = highest, 10 = lowest |
| `scheduled_for` | timestamptz | When to publish (null = next available slot) |
| `published_at` | timestamptz | When it actually published |
| `blotato_submission_id` | text | Blotato's post submission ID |
| `platform_url` | text | Final URL on the platform |
| `error_message` | text | Last error if failed |
| `retry_count` | int | Default 0 |
| `metadata` | jsonb | Extra data (sora script id, trend, etc.) |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

### API Endpoints (all under `/api/publishing`)

#### Config Management
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/config` | Get current publishing config |
| `PATCH` | `/config` | Update config (videos_per_day, platform limits, windows, etc.) |
| `POST` | `/config/pause` | Pause all publishing globally |
| `POST` | `/config/resume` | Resume publishing |

#### Queue Management
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/queue` | List queue items (filter by platform, status, date range) |
| `GET` | `/queue/stats` | Queue statistics: counts by status, platform, upcoming 24h |
| `POST` | `/queue` | Add a video to the publish queue |
| `POST` | `/queue/bulk` | Add multiple videos at once |
| `PATCH` | `/queue/{id}` | Update queue item (caption, time, priority) |
| `PATCH` | `/queue/{id}/priority` | Change priority (reorder) |
| `POST` | `/queue/{id}/reschedule` | Reschedule to new time |
| `POST` | `/queue/{id}/pause` | Pause a single item |
| `POST` | `/queue/{id}/resume` | Resume a paused item |
| `POST` | `/queue/{id}/cancel` | Cancel and remove from queue |
| `POST` | `/queue/{id}/retry` | Retry a failed item |
| `DELETE` | `/queue/{id}` | Delete from queue |

#### Dashboard / Status
| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/status` | Full publishing status: config, counters, next scheduled |
| `GET` | `/daily-summary` | Today's publishing: posted, remaining budget, by platform |
| `GET` | `/history` | Published history (filter by date, platform) |

### External Server Integration

All endpoints are standard REST, designed to be called from any server:

```bash
# From Safari Automation server or any external service:
curl http://mediaposter:5555/api/publishing/config
curl -X PATCH http://mediaposter:5555/api/publishing/config \
  -H "Content-Type: application/json" \
  -d '{"global_videos_per_day": 6, "platform_limits": {"tiktok": 3, "instagram": 2}}'

curl http://mediaposter:5555/api/publishing/queue?platform=tiktok&status=queued
curl -X POST http://mediaposter:5555/api/publishing/config/pause
```

### Integration Points

1. **PostScheduler** — Before publishing a post, checks `VideoPublishingController.can_publish(platform)` for rate limits and pause state.
2. **BlotatoService** — After successful publish, controller updates queue status and daily counters.
3. **SoraScheduler** — When a Sora video is generated and processed, it gets added to the `video_publish_queue` automatically.
4. **Safari Automation** — Can query and control the queue via API.
5. **Event Bus** — Emits events: `publishing.queued`, `publishing.started`, `publishing.completed`, `publishing.paused`, `publishing.config.updated`.

### Success Criteria

- [ ] Can view all queued videos in one API call
- [ ] Can change videos_per_day at runtime without restart
- [ ] Can set per-platform daily limits
- [ ] Can pause/resume all publishing with one API call
- [ ] Can pause/resume individual queue items
- [ ] All endpoints callable from external servers
- [ ] PostScheduler respects new rate limits
- [ ] Daily counters reset at midnight (configurable timezone)
