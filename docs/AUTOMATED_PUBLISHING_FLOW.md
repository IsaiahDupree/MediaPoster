# Automated Social Media Publishing Flow

## Overview

The MediaPoster backend includes an automated **Post Scheduler** that runs as a background worker, checking for scheduled posts and publishing them automatically without any frontend interaction required.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    BACKEND POST SCHEDULER FLOW                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Every 60 seconds, the scheduler checks for due posts:                  │
│                                                                         │
│  1. CHECK FOR DUE POSTS                                                │
│     └─ Query DB: scheduled_at <= NOW() AND status = 'scheduled'        │
│                                                                         │
│  2. FOR EACH DUE POST → BackgroundPublisher.publish()                  │
│     │                                                                   │
│     ├─ Step 1: VERIFY MEDIA                                            │
│     │   └─ Check file exists, get file path, duration                  │
│     │                                                                   │
│     ├─ Step 2: VERIFY ANALYSIS                                         │
│     │   └─ Get captions, hashtags, platform content                    │
│     │                                                                   │
│     ├─ Step 3: VERIFY ACCOUNT                                          │
│     │   └─ Confirm Blotato account ID is valid                         │
│     │                                                                   │
│     ├─ Step 4: UPLOAD TO CLOUD (Google Drive)                          │
│     │   └─ Stage video file for Blotato access                         │
│     │                                                                   │
│     ├─ Step 5: UPLOAD TO BLOTATO                                       │
│     │   └─ POST to Blotato API → Get blotato_media_id                  │
│     │                                                                   │
│     ├─ Step 6: PUBLISH TO PLATFORM                                     │
│     │   └─ POST to Blotato publish → Get post_submission_id            │
│     │   └─ ✅ Blotato 201 response                                     │
│     │                                                                   │
│     ├─ Step 7: POLL FOR URL (30 attempts × 5 sec = 2.5 min)           │
│     │   └─ GET /posts/status/{submission_id}                           │
│     │   └─ Wait for status: 'published' + publicUrl                    │
│     │   └─ ✅ Platform URL obtained (e.g., Instagram reel URL)         │
│     │                                                                   │
│     └─ Step 8: STORE RECORD                                            │
│         └─ Update scheduled_posts: status='posted', platform_url=URL   │
│         └─ Create posted_content record for analytics                  │
│                                                                         │
│  3. MARK COMPLETE OR RETRY                                             │
│     └─ Success: status = 'posted'                                      │
│     └─ Failure: retry_count++, schedule next retry (max 3 retries)     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. PostScheduler (`Backend/services/post_scheduler.py`)
- Background worker that runs every 60 seconds
- Queries database for due posts
- Manages retry logic (max 3 retries with exponential backoff)
- Auto-starts when backend starts

### 2. BackgroundPublisher (`Backend/services/background_publisher.py`)
- Encapsulates the full verified publish flow
- Same process as manual frontend publishing
- Includes verification steps before publishing

### 3. PublishService (`Backend/services/publish_service.py`)
- Handles cloud storage upload (Google Drive or Supabase)
- Manages Blotato API interactions
- Polls for platform URLs after publishing

## Starting the Scheduler

The scheduler automatically starts when the backend starts:

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
python main.py
```

You'll see in the console:
```
✓ Post Scheduler started (checking every 60s)
============================================================
[Scheduler] 🕐 Check #1 at 2025-12-22 16:56:00 UTC
[Scheduler] 📊 Due now: 5 | Upcoming: 10
[Scheduler] 🚀 Processing 5 due posts...
```

## Checking Scheduler Status

### API Endpoint
```bash
curl http://localhost:5555/api/schedule/scheduler/status
```

Response:
```json
{
  "is_running": true,
  "check_interval_seconds": 60,
  "max_retries": 3,
  "blotato_configured": true,
  "status_counts": {
    "posted": 15,
    "scheduled": 5
  },
  "upcoming_posts": 5,
  "due_now": 0,
  "recent_failures_24h": 0
}
```

## Frontend Console Logging

The schedule page (`/schedule`) shows comprehensive logging every 10 seconds:

```
======================================================================
[Scheduler] 🕐 12/22/2025, 11:52:11 AM (America/New_York)
======================================================================
[Scheduler] 📊 Summary:
   Total scheduled: 39
   Due NOW (past scheduled time): 24
   Upcoming: 15

[Scheduler] ⚠️ POSTS DUE FOR PUBLISHING:
   🔴 Video Title... | instagram | Overdue by 3 min

[Scheduler] ⏳ NEXT UP (with countdown):
   🟢 Next Video     | instagram  | 11:57:56 AM | T-5m 45s

[Scheduler] 📈 Stats: 10 posted, 0 failed
======================================================================
```

## Supported Platforms

Via Blotato API:
- Instagram (Reels, Posts)
- TikTok
- YouTube
- Twitter/X
- Facebook
- LinkedIn
- Threads
- Pinterest
- Bluesky

## File Format Requirements

**Supported:** MOV, MP4 (video files)  
**Not Supported:** HEIC, JPG, PNG (image files) - Blotato returns 500 error

## Database Tables

### scheduled_posts
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| content_id | UUID | Reference to videos table |
| title | TEXT | Post title |
| caption | TEXT | Post caption/description |
| hashtags | JSONB | Array of hashtags |
| platform | TEXT | Target platform |
| account_id | TEXT | Blotato account ID |
| scheduled_at | TIMESTAMP | When to publish |
| status | TEXT | scheduled/posted/failed |
| platform_url | TEXT | Published post URL |
| retry_count | INT | Number of retry attempts |

### posted_content
Tracks published content for analytics after successful posting.

## Error Handling

### Retry Logic
- Max retries: 3
- Retry delay: 5 minutes × retry count (exponential backoff)
- After max retries: status = 'failed'

### Common Errors
1. **NULL content_id** - Post has no media attached
2. **HEIC format** - Image files not supported
3. **Analysis missing** - Media not analyzed yet
4. **Invalid account** - Blotato account not found

## Environment Variables Required

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
BLOTATO_API_KEY=your_blotato_api_key
GOOGLE_DRIVE_CREDENTIALS=path/to/credentials.json
```

## Verification Flow

Before publishing, the scheduler verifies:
1. ✅ Media file exists and is accessible
2. ✅ Analysis data available (captions, hashtags)
3. ✅ Blotato account is valid and connected
4. ✅ Platform is supported

Only after all verifications pass does the actual publish begin.

---

*Last Updated: December 22, 2025*
