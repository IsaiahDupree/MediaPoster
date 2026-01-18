# Scheduling System - Quick Start Guide

## Overview

This guide explains how to schedule posts in MediaPoster, from content selection to publication tracking.

---

## Directory Structure

```
MediaPoster/
├── Backend/
│   ├── services/
│   │   ├── post_scheduler.py        # Core scheduler - runs every 60s
│   │   ├── publish_service.py       # Blotato publishing logic
│   │   ├── background_publisher.py  # Async publish handler
│   │   └── publisher_service.py     # Publishing orchestration
│   ├── api/endpoints/
│   │   └── schedule.py              # /api/schedule/* endpoints
│   ├── tasks/
│   │   └── scheduled_publishing.py  # Background task definitions
│   └── docs/
│       ├── SCHEDULING_BUGS_ANALYSIS.md
│       └── SCHEDULING_ROBUSTNESS_SUMMARY.md
│
├── dashboard/                       # Next.js Frontend
│   ├── app/(dashboard)/
│   │   └── schedule/
│   │       └── page.tsx             # Schedule page UI
│   ├── lib/services/
│   │   └── schedule-service.ts      # Frontend API client
│   └── __tests__/
│       ├── schedule-edit-modal.test.tsx
│       └── schedule-integration.test.tsx
│
├── e2e/                             # Playwright E2E Tests
│   ├── schedule-data-consistency.spec.ts  # ⭐ NEW - Data flow tests
│   ├── schedule-api-flow.spec.ts          # API integration tests
│   ├── schedule-create-post.spec.ts       # Post creation flow
│   ├── schedule-reliability.spec.ts       # Error handling tests
│   ├── scheduler-workflow.spec.ts         # Full workflow tests
│   └── blotato-scheduler-integration.spec.ts
│
└── docs/
    ├── SCHEDULING_QUICKSTART.md     # ⭐ THIS FILE
    ├── SCHEDULE_PAGE_GUIDE.md       # UI guide
    ├── TWITTER_POSTING_STRATEGY.md  # Rate limits & automation
    └── AI_NARRATIVE_SCHEDULING_PRD.md
```

---

## Scheduling Flow

### Step 1: Content Selection
```
User Action: Click "+" on calendar slot
     │
     ▼
┌─────────────────┐
│  Modal Opens    │
│  Shows clips    │
│  from media DB  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Filter clips:  │
│  • Video/Image  │
│  • Analyzed     │
│  • Curated      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Select clip    │
│  Preview details│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Choose platform │
│ Choose account  │
└────────┬────────┘
         │
         ▼
    [Schedule]
```

### Step 2: Data Flow
```
Frontend                    Backend                     Database
   │                           │                           │
   │  POST /api/schedule/create│                           │
   │ ─────────────────────────▶│                           │
   │                           │                           │
   │                           │  INSERT INTO              │
   │                           │  scheduled_posts          │
   │                           │ ─────────────────────────▶│
   │                           │                           │
   │                           │◀───── Return ID ──────────│
   │                           │                           │
   │◀──── { id, status } ──────│                           │
   │                           │                           │
```

### Step 3: Publishing (Automatic)
```
Post Scheduler (runs every 60s)
         │
         ▼
┌─────────────────────────┐
│ Query: scheduled_posts  │
│ WHERE scheduled_at ≤ NOW│
│ AND status = 'scheduled'│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  For each due post:     │
│  1. Verify media exists │
│  2. Get Blotato account │
│  3. Upload to GDrive    │
│  4. Upload to Blotato   │
│  5. Publish via Blotato │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Update scheduled_posts │
│  • status = 'posted'    │
│  • platform_url = URL   │
│  • platform_post_id     │
│  • published_at = NOW() │
└─────────────────────────┘
```

---

## Key Database Fields

### scheduled_posts Table

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Primary key |
| `clip_id` | UUID | Reference to video/clip |
| `platform` | VARCHAR | tiktok, instagram, youtube, twitter, etc. |
| `status` | VARCHAR | pending → scheduled → publishing → posted/failed |
| `scheduled_at` | TIMESTAMP | When to publish |
| `platform_url` | TEXT | **URL to published post** ⚠️ |
| `platform_post_id` | TEXT | External platform's post ID |
| `published_at` | TIMESTAMP | Actual publish time |
| `error_message` | TEXT | Error details if failed |
| `blotato_account_id` | TEXT | Account used for publishing |

### Common Issues

#### ⚠️ platform_url Not Saved
**Symptom**: Posts show as "posted" but URL is null

**Causes**:
1. Blotato didn't return URL in response
2. Polling for URL timed out
3. Database update failed after publish

**Debug**:
```sql
SELECT id, platform, status, platform_url, platform_post_id, error_message
FROM scheduled_posts 
WHERE status = 'posted' AND platform_url IS NULL
ORDER BY published_at DESC
LIMIT 10;
```

#### ⚠️ clip_id Missing
**Symptom**: Post fails with "Media not found"

**Cause**: Post was created without linking to actual video content

**Debug**:
```sql
SELECT id, title, platform, clip_id, status
FROM scheduled_posts 
WHERE clip_id IS NULL AND status != 'posted'
ORDER BY created_at DESC;
```

---

## API Endpoints

### Schedule Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/schedule/` | GET | List all scheduled posts |
| `/api/schedule/{id}` | GET | Get single post details |
| `/api/schedule/create` | POST | Create new scheduled post |
| `/api/schedule/{id}` | PUT | Update scheduled post |
| `/api/schedule/{id}` | DELETE | Cancel scheduled post |
| `/api/schedule/process-due` | POST | Manually trigger due posts |

### Request Example: Create Post
```json
POST /api/schedule/create
{
  "clip_id": "uuid-of-video",
  "platform": "tiktok",
  "account_id": "710",
  "scheduled_at": "2026-01-06T12:00:00Z",
  "title": "My Post Title",
  "caption": "Post caption here",
  "hashtags": ["#ai", "#automation"]
}
```

### Response Example: Post Created
```json
{
  "id": "new-post-uuid",
  "status": "scheduled",
  "platform": "tiktok",
  "scheduled_at": "2026-01-06T12:00:00Z",
  "clip_id": "uuid-of-video"
}
```

---

## Running Tests

### Data Consistency Tests
```bash
# Run all data consistency tests
npx playwright test schedule-data-consistency.spec.ts

# Run specific test
npx playwright test -g "DC-URL-001"

# Run with UI
npx playwright test schedule-data-consistency.spec.ts --ui
```

### Full Schedule Test Suite
```bash
# All schedule-related tests
npx playwright test schedule-

# With verbose output
npx playwright test schedule- --reporter=list
```

---

## Troubleshooting

### Check Post Status
```bash
# Via API
curl http://localhost:5555/api/schedule/{post_id}

# Via Database
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres \
  -c "SELECT * FROM scheduled_posts WHERE id = '{post_id}';"
```

### Check Scheduler Logs
```bash
tail -f Backend/logs/app.log | grep -i "scheduler\|publish"
```

### Force Process Due Posts
```bash
curl -X POST http://localhost:5555/api/schedule/process-due
```

### View Recent Failures
```sql
SELECT id, platform, title, error_message, last_error, retry_count
FROM scheduled_posts 
WHERE status = 'failed'
ORDER BY updated_at DESC
LIMIT 10;
```

---

## Rate Limits

### Blotato API Limits
| Platform | Limit | Recovery |
|----------|-------|----------|
| Twitter | 30 posts/burst | 15 min cooldown |
| TikTok | ~50 posts/day | Per account |
| Instagram | ~25 posts/day | Per account |
| YouTube | Variable | Per account |

### Recommended Spacing
- **Safe**: 5+ minutes between posts
- **Moderate**: 2-3 minutes between posts
- **Aggressive**: 1 minute (may hit limits)

---

## Files Reference

### Backend
- `Backend/services/post_scheduler.py` - Main scheduler loop
- `Backend/services/publish_service.py` - Blotato integration
- `Backend/services/background_publisher.py` - Async publishing

### Frontend
- `dashboard/app/(dashboard)/schedule/page.tsx` - Schedule UI
- `dashboard/lib/services/schedule-service.ts` - API client

### Tests
- `e2e/schedule-data-consistency.spec.ts` - **Data flow verification**
- `e2e/schedule-api-flow.spec.ts` - API tests
- `e2e/scheduler-workflow.spec.ts` - Full workflow tests

### Documentation
- `docs/SCHEDULING_QUICKSTART.md` - This file
- `docs/TWITTER_POSTING_STRATEGY.md` - Rate limits & automation
- `Backend/docs/SCHEDULING_BUGS_ANALYSIS.md` - Known issues

---

*Last Updated: January 5, 2026*
