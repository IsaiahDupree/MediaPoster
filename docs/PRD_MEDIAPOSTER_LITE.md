# PRD: MediaPoster Lite

**Owner:** @isaiahdupree | **Date:** 2026-02-19 | **Status:** Approved — Building Now
**Deploy:** Vercel | **DB:** Supabase Cloud

---

## 1. Summary

MediaPoster Lite is a 24/7 cloud-deployed command-and-control layer for video publishing. It runs on Vercel, stores state in Supabase, and exposes a secure REST API + dashboard. Your local machine calls it to queue videos, check rate limits, and report publish results. Lite decides *what/when/where*; local executes *how*.

## 2. Scope

**In:** Queue management, scheduling, rate limiting, pause/resume, platform config, dashboard UI, API key auth, activity log, webhooks, recurring schedules, CLI tool.

**Out:** Video file processing, Safari automation, OpenAI generation, Sora scripts, trend detection, direct Blotato calls, multi-tenancy.

## 3. Architecture

```
Local Machine  ──HTTPS──▶  Vercel (Next.js 14)  ──▶  Supabase Cloud
  • mplite CLI              • /api/queue/*              • publish_queue
  • Publisher daemon        • /api/config/*             • publishing_config
  • MediaPoster Full        • /api/platforms/*          • platforms
  • curl scripts            • /api/status               • daily_counters
                            • Dashboard UI              • activity_log
                                                        • api_keys
```

**Publisher daemon loop:**
1. `GET /api/queue/next?platform=tiktok` → get item
2. `POST /api/queue/:id/claim` → mark "publishing"
3. Local publishes via Blotato
4. `POST /api/queue/:id/complete` or `/fail`

## 4. Tech Stack

Next.js 14 App Router · TypeScript · Tailwind CSS · shadcn/ui · Lucide · Supabase JS · Zod · Recharts · date-fns · Vercel

## 5. Database Schema

### `publishing_config` (single row)
| Column | Type | Default |
|--------|------|---------|
| global_enabled | boolean | true |
| videos_per_day | int | 8 |
| posts_per_day | int | 12 |
| platform_limits | jsonb | {} — e.g. {"tiktok":4,"instagram":3} |
| posting_windows | jsonb | {} — e.g. {"start":"08:00","end":"23:00","tz":"America/New_York"} |
| min_interval_minutes | int | 30 |
| priority_order | jsonb | [] — e.g. ["tiktok","instagram","youtube"] |
| updated_at | timestamptz | now() |
| updated_by | text | "system" |

### `publish_queue`
| Column | Type | Notes |
|--------|------|-------|
| id | uuid PK | gen_random_uuid() |
| title | text | display name |
| video_url | text | NOT NULL — URL ref only, no uploads |
| thumbnail_url | text | optional |
| caption | text | post caption |
| hashtags | jsonb | ["#tag1","#tag2"] |
| platform | text | "tiktok"\|"instagram"\|"youtube"\|"twitter"\|"threads" |
| account_id | text | Blotato account ID |
| account_username | text | display |
| status | text | queued\|scheduled\|publishing\|published\|failed\|paused\|cancelled |
| priority | int | 1 (highest) – 10 (lowest), default 5 |
| scheduled_for | timestamptz | null = next available slot |
| published_at | timestamptz | set on complete |
| platform_post_id | text | returned by Blotato |
| platform_url | text | live URL on platform |
| error_message | text | last failure reason |
| retry_count | int | default 0 |
| max_retries | int | default 3 |
| metadata | jsonb | {"source":"ugc_generator","script_id":"abc"} |
| source | text | "api"\|"dashboard"\|"cli"\|"webhook" |
| created_at / updated_at | timestamptz | |

Indexes: status, platform, (scheduled_for WHERE status IN queued/scheduled), (priority, scheduled_for WHERE active)

### `platforms`
| Column | Type |
|--------|------|
| name | text UNIQUE — "tiktok", "instagram", etc. |
| display_name | text |
| color | text — hex for UI |
| is_enabled | boolean |
| daily_limit | int |
| accounts | jsonb — [{"id":"710","username":"isaiah_dupree","is_active":true}] |
| default_hashtags | jsonb |
| posting_config | jsonb — {"max_caption_length":2200,"supports_thumbnails":true} |

### `daily_counters`
| Column | Type |
|--------|------|
| counter_date | date UNIQUE per platform |
| platform | text |
| count | int |
| last_publish | timestamptz |

### `schedules`
| Column | Type |
|--------|------|
| name, description | text |
| is_active | boolean |
| schedule_type | "one_time"\|"recurring"\|"smart" |
| cron_expression | text — e.g. "0 14 * * 1-5" |
| timezone | text |
| platforms | jsonb |
| template | jsonb — default caption/hashtags/account_id |
| next_run_at, last_run_at | timestamptz |
| run_count | int |

### `activity_log`
| Column | Type |
|--------|------|
| action | text — "queue.add"\|"queue.cancel"\|"config.update"\|"publish.success"\|... |
| entity_type | text — "queue_item"\|"config"\|"platform" |
| entity_id | text |
| details | jsonb |
| source | text — "api"\|"dashboard"\|"cli"\|"webhook"\|"system" |
| ip_address | text |
| created_at | timestamptz |

### `api_keys`
| Column | Type |
|--------|------|
| name | text — "local-machine", "iphone-shortcut" |
| key_hash | text UNIQUE — SHA-256 of actual key |
| prefix | text — "mpl_xxxxxxxx" for identification |
| permissions | jsonb — ["*"] or ["queue.*","config.read"] |
| is_active | boolean |
| last_used, expires_at | timestamptz |

### `webhooks`
| Column | Type |
|--------|------|
| name, url | text |
| events | jsonb — ["publish.success","publish.failed","queue.empty"] |
| secret | text — for HMAC signing |
| is_active | boolean |
| last_fired, fire_count | timestamptz / int |

## 6. API Reference

**Auth:** `Authorization: Bearer mpl_xxx` on all routes except `/api/health` and `/api/webhooks/inbound/*`

**Response envelope:**
```json
{ "success": true, "data": { ... } }
{ "success": false, "error": "code", "message": "Human readable" }
```

### Queue
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/queue | Add video |
| POST | /api/queue/bulk | Bulk add (≤50) |
| GET | /api/queue | List (filters: platform, status, limit, offset, date_from, date_to) |
| GET | /api/queue/stats | Counts by status + platform |
| GET | /api/queue/next?platform= | Next publishable item |
| GET | /api/queue/:id | Get item |
| PATCH | /api/queue/:id | Update fields |
| POST | /api/queue/:id/claim | Mark "publishing" |
| POST | /api/queue/:id/complete | Mark published + platform_url |
| POST | /api/queue/:id/fail | Mark failed + error_message |
| POST | /api/queue/:id/pause | Pause |
| POST | /api/queue/:id/resume | Resume |
| POST | /api/queue/:id/cancel | Cancel |
| POST | /api/queue/:id/retry | Reset failed → queued |
| POST | /api/queue/:id/reschedule | New scheduled_for |
| POST | /api/queue/:id/priority | Change priority 1–10 |
| DELETE | /api/queue/:id | Hard delete |

### Config
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/config | Get config |
| PATCH | /api/config | Update fields |
| POST | /api/config/pause | Pause all |
| POST | /api/config/resume | Resume all |

### Rate Limiting
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/can-publish/:platform | Check limit + window |
| GET | /api/daily-summary | Today's counts per platform |

### Platforms
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/platforms | List all |
| GET | /api/platforms/:name | Get one |
| PATCH | /api/platforms/:name | Update |
| POST | /api/platforms/:name/toggle | Enable/disable |

### Schedules
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | /api/schedules | List / Create |
| GET/PATCH/DELETE | /api/schedules/:id | CRUD |
| POST | /api/schedules/:id/toggle | Enable/disable |
| POST | /api/schedules/:id/trigger | Run now |

### Status & History
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/status | Config + queue stats + daily summary |
| GET | /api/history | Published items |
| GET | /api/activity | Audit log (paginated) |
| GET | /api/health | No auth — health check |

### API Keys
| Method | Path | Description |
|--------|------|-------------|
| GET | /api/keys | List (prefix only, never full key) |
| POST | /api/keys | Generate (returns full key once) |
| DELETE | /api/keys/:id | Revoke |

### Webhooks
| Method | Path | Description |
|--------|------|-------------|
| GET/POST | /api/webhooks | List / Register |
| DELETE | /api/webhooks/:id | Remove |
| POST | /api/webhooks/inbound/blotato | Blotato callbacks (no auth) |
| POST | /api/webhooks/inbound/cron | Vercel cron (secret header) |

## 7. Dashboard Pages

| Route | Page | Key Features |
|-------|------|-------------|
| / | Overview | Stats cards, platform progress bars, next-up list, live activity feed |
| /queue | Queue Manager | Table with filters/bulk actions, add form, realtime updates |
| /queue/:id | Item Detail | Full item view, status history timeline, edit form |
| /calendar | Calendar | Week/month view, drag-to-reschedule, platform color coding |
| /platforms | Platforms | Cards per platform, toggle, accounts list, limit sliders |
| /config | Configuration | Global toggle, daily limits, posting windows, priority order |
| /history | History | Published items with platform links and performance |
| /activity | Activity Log | Paginated audit trail with filters |
| /settings | Settings | API keys table, webhooks table, preferences |

### Realtime
Dashboard uses Supabase Realtime subscriptions:
- `publish_queue` changes → queue table + stats update live
- `activity_log` inserts → activity feed updates live
- `daily_counters` updates → platform bars update live

## 8. CLI Tool (`mplite`)

Single-file Python script, zero external dependencies.

```bash
# Install
curl -o /usr/local/bin/mplite https://mediaposter-lite.vercel.app/cli
chmod +x /usr/local/bin/mplite
mplite init   # prompts for URL + API key

# Queue
mplite queue add --video URL --caption "..." --platform tiktok --account 710 --schedule "2026-02-20 14:00"
mplite queue add --from-file batch.json
mplite queue list [--platform tiktok] [--status queued] [--json]
mplite queue get <id>
mplite queue next --platform tiktok
mplite queue cancel <id>
mplite queue pause <id>
mplite queue resume <id>
mplite queue retry <id>
mplite queue reschedule <id> "2026-02-21 10:00"
mplite queue priority <id> 2

# Publisher lifecycle (called by local publisher daemon)
mplite publish claim <id>
mplite publish complete <id> --url "https://tiktok.com/..." --post-id "123"
mplite publish fail <id> --error "Rate limited by Blotato"

# Config
mplite config show
mplite config set videos-per-day 10
mplite config set platform-limit tiktok 4
mplite config pause
mplite config resume

# Status
mplite status
mplite status --json
mplite can-publish tiktok
mplite daily-summary

# History & Activity
mplite history [--days 7] [--platform tiktok]
mplite activity [--limit 20]
```

## 9. Local Publisher Daemon

```python
#!/usr/bin/env python3
"""Polls MediaPoster Lite and publishes via Blotato."""
import time, requests, os

LITE_URL = os.environ["MPLITE_URL"]
HEADERS = {"Authorization": f"Bearer {os.environ['MPLITE_KEY']}"}
PLATFORMS = ["tiktok", "instagram", "youtube"]

def run():
    while True:
        for platform in PLATFORMS:
            r = requests.get(f"{LITE_URL}/api/can-publish/{platform}", headers=HEADERS)
            if not r.json()["data"]["can_publish"]:
                continue
            r = requests.get(f"{LITE_URL}/api/queue/next?platform={platform}", headers=HEADERS)
            if r.status_code == 404:
                continue
            item = r.json()["data"]
            requests.post(f"{LITE_URL}/api/queue/{item['id']}/claim", headers=HEADERS)
            try:
                # publish via Blotato here
                platform_url = blotato_publish(item)
                requests.post(f"{LITE_URL}/api/queue/{item['id']}/complete",
                    headers=HEADERS, json={"platform_url": platform_url})
            except Exception as e:
                requests.post(f"{LITE_URL}/api/queue/{item['id']}/fail",
                    headers=HEADERS, json={"error_message": str(e)})
        time.sleep(60)
```

## 10. Security

- All API keys stored as SHA-256 hashes only
- Keys prefixed `mpl_` for identification
- Granular permissions: `["*"]` or `["queue.*", "config.read"]`
- Inbound webhooks validated via HMAC-SHA256 signature
- Vercel Edge middleware validates auth before any route handler runs
- Supabase RLS: all tables locked to service role (no public access)
- Rate limiting on API key: 1000 req/min per key

## 11. Success Criteria

- [ ] `mplite queue add` from local machine → item appears in Vercel dashboard in <1s
- [ ] `mplite config pause` → all publishing halted, dashboard shows paused state
- [ ] Publisher daemon polls and publishes without local MediaPoster running
- [ ] Dashboard loads in <2s on mobile
- [ ] Realtime updates work without page refresh
- [ ] API key generation and revocation works end-to-end
- [ ] Vercel deployment succeeds from `git push`
- [ ] All 27 existing MediaPoster Lite integration tests pass

## 12. File Structure

```
mediaposter-lite/
├── app/
│   ├── layout.tsx
│   ├── page.tsx                    # Overview dashboard
│   ├── queue/
│   │   ├── page.tsx                # Queue manager
│   │   └── [id]/page.tsx           # Item detail
│   ├── calendar/page.tsx
│   ├── platforms/page.tsx
│   ├── config/page.tsx
│   ├── history/page.tsx
│   ├── activity/page.tsx
│   └── settings/page.tsx
├── app/api/
│   ├── queue/
│   │   ├── route.ts                # GET list, POST add
│   │   ├── bulk/route.ts
│   │   ├── next/route.ts
│   │   ├── stats/route.ts
│   │   └── [id]/
│   │       ├── route.ts            # GET, PATCH, DELETE
│   │       ├── claim/route.ts
│   │       ├── complete/route.ts
│   │       ├── fail/route.ts
│   │       ├── pause/route.ts
│   │       ├── resume/route.ts
│   │       ├── cancel/route.ts
│   │       ├── retry/route.ts
│   │       ├── reschedule/route.ts
│   │       └── priority/route.ts
│   ├── config/
│   │   ├── route.ts
│   │   ├── pause/route.ts
│   │   └── resume/route.ts
│   ├── can-publish/[platform]/route.ts
│   ├── daily-summary/route.ts
│   ├── platforms/
│   │   ├── route.ts
│   │   └── [name]/
│   │       ├── route.ts
│   │       ├── toggle/route.ts
│   │       └── accounts/route.ts
│   ├── schedules/
│   │   ├── route.ts
│   │   └── [id]/
│   │       ├── route.ts
│   │       ├── toggle/route.ts
│   │       └── trigger/route.ts
│   ├── status/route.ts
│   ├── history/route.ts
│   ├── activity/route.ts
│   ├── health/route.ts
│   ├── keys/
│   │   ├── route.ts
│   │   └── [id]/route.ts
│   └── webhooks/
│       ├── route.ts
│       ├── [id]/route.ts
│       └── inbound/
│           ├── blotato/route.ts
│           └── cron/route.ts
├── components/
│   ├── ui/                         # shadcn/ui components
│   ├── dashboard/
│   │   ├── StatsCards.tsx
│   │   ├── PlatformBars.tsx
│   │   ├── NextUpList.tsx
│   │   └── ActivityFeed.tsx
│   ├── queue/
│   │   ├── QueueTable.tsx
│   │   ├── QueueFilters.tsx
│   │   ├── AddQueueItemForm.tsx
│   │   └── BulkActions.tsx
│   ├── calendar/
│   │   └── PublishCalendar.tsx
│   └── shared/
│       ├── PlatformBadge.tsx
│       ├── StatusBadge.tsx
│       └── Sidebar.tsx
├── lib/
│   ├── supabase.ts                 # Supabase client (server + browser)
│   ├── auth.ts                     # API key validation
│   ├── middleware.ts               # Edge auth middleware
│   └── schemas.ts                  # Zod schemas for all API inputs
├── middleware.ts                   # Vercel Edge middleware
├── public/cli                      # mplite CLI script (served as download)
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql
├── .env.local.example
├── vercel.json
└── package.json
```
