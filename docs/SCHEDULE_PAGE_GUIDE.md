# Schedule Page Developer Guide

## Overview

The Schedule page displays a calendar view of scheduled posts across all platforms. This guide documents the architecture, data flow, and common issues for developers working on scheduling features.

---

## Architecture

### Data Flow

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   Frontend          │     │   Backend API       │     │   Database          │
│   schedule/page.tsx │────▶│   /api/schedule/*   │────▶│   scheduled_posts   │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
         │                           │                           │
         │  fetchSchedule()          │  list_scheduled_posts()   │
         │  GET /api/schedule/list   │  SELECT ... FROM          │
         │  ?limit=500               │  scheduled_posts          │
         │                           │                           │
         ▼                           ▼                           ▼
    Calendar View              JSON Response              SQL Query
```

### Key Files

| File | Purpose |
|------|---------|
| `dashboard/app/(dashboard)/schedule/page.tsx` | Frontend calendar UI |
| `Backend/api/endpoints/schedule.py` | API endpoints for CRUD operations |
| `Backend/scripts/schedule_7_day_posts.py` | Script to bulk schedule posts |
| `Backend/services/narrative_scheduler/` | AI-powered scheduling service |

---

## Database Schema

### `scheduled_posts` Table

```sql
CREATE TABLE scheduled_posts (
    id UUID PRIMARY KEY,
    content_id TEXT,              -- Legacy field
    clip_id UUID,                 -- Video clip reference
    content_variant_id UUID,      -- Content variant reference
    
    -- Post content
    title TEXT NOT NULL,
    caption TEXT,
    hashtags JSONB DEFAULT '[]',
    thumbnail_url TEXT,
    
    -- Platform info
    platform TEXT NOT NULL,       -- 'tiktok', 'instagram', 'youtube', etc.
    account_id TEXT NOT NULL,
    account_username TEXT,
    blotato_account_id TEXT,      -- Blotato service account ID
    
    -- Scheduling
    scheduled_at TIMESTAMPTZ,     -- Legacy field
    scheduled_time TIMESTAMPTZ,   -- Primary scheduling field (used by API)
    
    -- Status tracking
    status TEXT DEFAULT 'pending', -- CRITICAL: Must be 'pending' to show as scheduled
    post_type TEXT DEFAULT 'reel',
    media_type TEXT,              -- 'reel' or 'story' for Instagram
    
    -- Publishing results
    platform_post_id TEXT,
    platform_url TEXT,
    published_at TIMESTAMPTZ,
    error_message TEXT,
    
    -- Metadata
    source TEXT,                  -- 'manual', 'narrative_builder', etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Status Values

### CRITICAL: Status Field Requirements

| Status | Meaning | Shows in Calendar? |
|--------|---------|-------------------|
| `pending` | Awaiting publishing | ✅ YES - Shows as "Scheduled" |
| `scheduled` | ⚠️ LEGACY - DO NOT USE | ❌ NO - Frontend expects 'pending' |
| `publishing` | Currently being published | ⚠️ Shows briefly |
| `posted` | Successfully published | ✅ YES - Shows as "Posted" |
| `published` | Alias for posted | ✅ YES |
| `failed` | Publishing failed | ✅ YES - Shows as "Failed" |

**⚠️ IMPORTANT:** When creating scheduled posts programmatically, always use `status = 'pending'`, NOT `'scheduled'`. The frontend filters on `status === 'pending'` for the "Scheduled" view.

---

## API Endpoints

### GET /api/schedule/list

Lists scheduled posts with optional filters.

**Parameters:**
- `limit` (int, default: 100, max: 500) - Number of posts to return
- `start_date` (string) - Filter by start date (YYYY-MM-DD)
- `end_date` (string) - Filter by end date (YYYY-MM-DD)
- `platform` (string) - Filter by platform
- `status` (string) - Filter by status

**⚠️ IMPORTANT:** Default limit is 100. If you have many posts, future dates may not appear! The frontend uses `limit=500` to ensure all posts are fetched.

**Response:**
```json
{
  "posts": [
    {
      "id": "uuid",
      "content_id": "uuid",
      "media_id": "uuid",
      "title": "Post Title",
      "caption": "Post caption...",
      "platform": "tiktok",
      "account_id": "710",
      "account_username": "isaiah_dupree",
      "scheduled_at": "2026-01-02T09:00:00+00:00",
      "status": "pending",
      "source": "narrative_builder"
    }
  ],
  "total": 100
}
```

### POST /api/schedule/create

Creates a new scheduled post.

**Request Body:**
```json
{
  "content_id": "video-uuid",
  "title": "Post Title",
  "caption": "Post caption with #hashtags",
  "platform": "tiktok",
  "account_id": "710",
  "account_username": "isaiah_dupree",
  "scheduled_at": "2026-01-02T09:00:00Z",
  "post_type": "reel"
}
```

---

## PubSub Events

The schedule system uses the EventBus for real-time updates:

| Topic | When Emitted | Payload |
|-------|--------------|---------|
| `SCHEDULE_CREATED` | New post scheduled | `{post_id, content_id, platform, scheduled_at}` |
| `publish.completed` | Post successfully published | `{post_id, media_id, platform, platform_url}` |
| `publish.failed` | Publishing failed | `{post_id, media_id, platform, error}` |
| `schedule.due` | Post is due for publishing | `{post_id, platform}` |

---

## Deduplication Rules

The scheduling system prevents duplicate content through two checks:

### 1. Same Video to Same Account
- Prevents the exact same video (by `content_id`) from being scheduled to the same Blotato account
- A video CAN be scheduled to multiple different accounts

### 2. Same Transcript to Same Account
- Prevents videos with identical transcripts from being scheduled to the same account
- Uses MD5 hash of transcript for comparison (transcripts > 50 chars)
- This catches cases where the same content exists as multiple video files

**Example:**
```
Video A (transcript: "Hello world...") → Account 710 ✅
Video A (transcript: "Hello world...") → Account 807 ✅ (different account)
Video A (transcript: "Hello world...") → Account 710 ❌ (duplicate - same video)
Video B (transcript: "Hello world...") → Account 710 ❌ (duplicate - same transcript)
```

---

## Common Issues & Solutions

### Issue 1: Future Posts Not Showing in Calendar

**Symptom:** Posts scheduled for future dates don't appear in calendar UI.

**Root Cause:** API default limit is 100, ordered by date ascending. If you have >100 posts, future dates are excluded.

**Solution:** Frontend fetches with `limit=500`:
```typescript
const res = await fetch(`${API_URL}/api/schedule/list?limit=500`);
```

### Issue 2: Posts Created But Not Showing

**Symptom:** Database has posts but they don't appear in "Scheduled" view.

**Root Cause:** Posts created with `status: 'scheduled'` instead of `status: 'pending'`.

**Solution:** Always use `status = 'pending'` when creating posts:
```sql
INSERT INTO scheduled_posts (..., status) VALUES (..., 'pending');
```

**Fix existing posts:**
```sql
UPDATE scheduled_posts SET status = 'pending' WHERE status = 'scheduled';
```

### Issue 3: Timezone Display Issues

**Symptom:** Posts appear on wrong day in calendar.

**Root Cause:** Posts stored in UTC but displayed in local timezone.

**Solution:** Frontend converts UTC to local timezone for display. Ensure `scheduled_time` is stored as proper ISO8601 with timezone.

---

## Creating Scheduled Posts Programmatically

### Using the API

```python
import requests

response = requests.post("http://localhost:5555/api/schedule/create", json={
    "content_id": "video-uuid-here",
    "title": "My Video Title",
    "caption": "Check this out! #viral",
    "platform": "tiktok",
    "account_id": "710",
    "account_username": "isaiah_dupree",
    "scheduled_at": "2026-01-02T09:00:00Z",
    "post_type": "reel"
})
```

### Direct Database Insert

```python
from sqlalchemy import create_engine, text

engine = create_engine("postgresql://postgres:postgres@127.0.0.1:54322/postgres")

with engine.connect() as conn:
    conn.execute(text("""
        INSERT INTO scheduled_posts (
            content_id, title, caption, platform, account_id,
            account_username, scheduled_time, scheduled_at, status
        ) VALUES (
            :content_id, :title, :caption, :platform, :account_id,
            :account_username, :scheduled_time, :scheduled_time, 'pending'
        )
    """), {
        "content_id": "video-uuid",
        "title": "My Video",
        "caption": "Caption here",
        "platform": "tiktok",
        "account_id": "710",
        "account_username": "isaiah_dupree",
        "scheduled_time": "2026-01-02T09:00:00+00:00"
    })
    conn.commit()
```

---

## Blotato Account Mapping

Posts require a Blotato account ID for publishing. See `Backend/config/blotato_accounts.py` for the mapping:

| Platform | Account ID | Username |
|----------|------------|----------|
| TikTok | 710 | @isaiah_dupree |
| Instagram | 807 | @the_isaiah_dupree |
| YouTube | 228 | Isaiah Dupree |
| Threads | 1369 | @dupree_isaiah_ |
| Twitter | 4151 | @soursides_is_sour |

---

## Testing

### Run Schedule API Tests

```bash
cd Backend
python -m pytest tests/test_scheduler_api.py -v
```

### Run Frontend Schedule Tests

```bash
cd dashboard
npm test -- schedule-integration.test.tsx
```

### Manual Testing

1. Create a test post via API
2. Check it appears in calendar at correct date/time
3. Verify status shows as "Scheduled"
4. Trigger publishing and verify status updates

---

## Related Documentation

- `docs/AI_NARRATIVE_SCHEDULING_PRD.md` - AI scheduling system design
- `docs/AUTOMATED_PUBLISHING_FLOW.md` - Publishing pipeline
- `docs/BLOTATO_API_DOCS.md` - Blotato integration

---

*Last updated: January 2026*
