# Complete Video Pipeline Guide

## Overview

This document describes the full pipeline for:
1. **Ingesting** videos into the MediaPoster database
2. **Analyzing** videos (transcription + AI content analysis)
3. **Generating** titles and descriptions
4. **Posting** to YouTube, TikTok, and other platforms

---

## Architecture Summary

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   VIDEO FILE    │ ──► │     INGEST      │ ──► │    ANALYZE      │
│  (local/sora)   │     │  /api/media-db  │     │  VideoAnalyzer  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                        ┌─────────────────┐             ▼
                        │    SCHEDULE     │ ◄── ┌─────────────────┐
                        │  PostScheduler  │     │ GENERATE CONTENT│
                        └─────────────────┘     │   AI Titles     │
                                │               └─────────────────┘
                                ▼
                        ┌─────────────────┐
                        │    PUBLISH      │
                        │  Blotato API    │
                        └─────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
               YouTube      TikTok     Instagram
```

---

## Step 1: Ingest Videos

### API Endpoint
```
POST http://localhost:5555/api/media-db/ingest/file?file_path=/path/to/video.mp4
```

### What It Does
- Extracts video metadata (duration, resolution, aspect ratio)
- Creates record in `videos` table
- Prevents duplicates via `source_uri` unique constraint
- Emits `media.ingested` event for downstream processing

### Python Example
```python
import httpx

async def ingest_video(file_path: str) -> dict:
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            "http://localhost:5555/api/media-db/ingest/file",
            params={"file_path": file_path}
        )
        return response.json()
        
# Response: {"status": "ingested", "media_id": "uuid-here"}
# Or: {"status": "exists", "media_id": "uuid-here"} if duplicate
```

### Batch Ingest
```
POST http://localhost:5555/api/media-db/batch/ingest
{
    "directory_path": "/path/to/videos",
    "recursive": false,
    "resume": true
}
```

### Key Files
- `Backend/api/media_processing_db.py` - Ingest endpoints
- `Backend/database/models.py` - Video and VideoAnalysis models

---

## Step 2: Analyze Videos

### API Endpoint
```
POST http://localhost:5555/api/media-db/analyze/{media_id}
```

Or batch analyze:
```
POST http://localhost:5555/api/media-db/batch/analyze
{
    "limit": 50,
    "skip_analyzed": true
}
```

### Analysis Pipeline (4 Steps)

1. **Transcription** (Groq Whisper)
   - Extracts audio from video
   - Transcribes using `whisper-large-v3`
   - Stores transcript, language, word count, segments

2. **Visual Analysis** (GPT-4o Mini)
   - Extracts 5 key frames
   - Analyzes visual content
   - Selects best thumbnail frame

3. **Content Analysis** (GPT-4)
   - Analyzes transcript + visuals
   - Extracts: topics, hooks, tone, pacing
   - Generates: pre_social_score (viral potential)
   - Identifies: pain points, emotional drivers, CTA

4. **AI Title Generation**
   - Generates ~30 char punchy title
   - Stored in `videos.title` column

### What Gets Stored (video_analysis table)
```sql
- transcript          -- Full transcript text
- topics              -- Array of 3-5 main topics
- hooks               -- Array of attention-grabbing phrases
- detected_hook       -- Best single hook
- tone                -- energetic/calm/educational/etc.
- pacing              -- fast/medium/slow
- pre_social_score    -- 0-100 viral potential
- visual_analysis     -- JSONB frame analysis
- pain_points         -- Problems content addresses
- emotional_drivers   -- Emotional triggers
- call_to_action      -- CTA analysis
- pillar_tags         -- Content categorization
- format_tags         -- video type tags
```

### Analysis Validation
Analysis is only marked complete if:
- Transcript > 10 characters
- At least 1 topic identified
- pre_social_score is set

### Key Files
- `Backend/services/video_analyzer.py` - Main orchestrator
- `Backend/services/whisper_transcriber.py` - Transcription
- `Backend/services/content_analyzer.py` - GPT-4 analysis
- `Backend/services/frame_analyzer.py` - Visual analysis
- `Backend/config/model_registry.py` - AI model configuration

---

## Step 3: Generate Titles & Descriptions

### Automatic Title Generation
Titles are generated automatically during analysis (Step 2).

### Manual Title/Description Generation
```python
from services.content_analyzer import ContentAnalyzer

analyzer = ContentAnalyzer()

# Generate from transcript
result = analyzer.analyze_transcript(
    transcript="Your video transcript here...",
    video_metadata={"duration": 60, "title": "Original title"}
)

# Result includes:
# - topics: ["topic1", "topic2"]
# - hooks: ["hook phrase 1", "hook phrase 2"]
# - detected_hook: "best hook"
# - pre_social_score: 85
```

### Caption Generation for Posting
Captions are composed from analysis data:
```python
def build_caption(analysis: dict, hashtags: list = None) -> str:
    hook = analysis.get("detected_hook", "")
    topics = analysis.get("topics", [])
    
    caption = f"{hook}\n\n"
    if hashtags:
        caption += " ".join(f"#{tag}" for tag in hashtags)
    
    return caption[:2200]  # Instagram limit
```

---

## Step 4: Schedule Posts

### Database Table: scheduled_posts
```sql
CREATE TABLE scheduled_posts (
    id UUID PRIMARY KEY,
    clip_id UUID,                    -- Reference to videos.id
    platform TEXT,                   -- 'youtube', 'tiktok', 'instagram'
    platform_account_id TEXT,        -- Blotato account ID
    account_username TEXT,
    scheduled_time TIMESTAMP,
    status TEXT,                     -- 'scheduled', 'publishing', 'posted', 'failed'
    caption TEXT,
    title TEXT,
    hashtags TEXT[],
    platform_post_id TEXT,           -- After posting
    platform_url TEXT,               -- After posting
    published_at TIMESTAMP
);
```

### Schedule via API
```
POST http://localhost:5555/api/schedule/create
{
    "media_id": "uuid-of-video",
    "platform": "youtube",
    "account_id": "228",
    "scheduled_time": "2024-01-15T10:00:00Z",
    "caption": "Check out this video! #content",
    "title": "Amazing Video Title"
}
```

### Key Files
- `Backend/services/post_scheduler.py` - Background scheduler
- `Backend/api/endpoints/schedule.py` - Schedule endpoints

---

## Step 5: Publish to Platforms

### Blotato API Integration
MediaPoster uses Blotato as the unified publishing gateway.

### Publish Flow
```
1. Upload video to cloud storage (Supabase or Google Drive)
2. Send public URL to Blotato /v2/media
3. Blotato returns hosted media URL
4. Submit post via Blotato /v2/posts
5. Poll for platform URL
6. Store in posted_content table
```

### Platform-Specific Settings

**YouTube:**
```python
target_config = {
    "targetType": "youtube",
    "privacyStatus": "public",
    "shouldNotifySubscribers": True,
    "isMadeForKids": False
}
```

**TikTok:**
```python
target_config = {
    "targetType": "tiktok",
    "privacyLevel": "PUBLIC_TO_EVERYONE",
    "disabledComments": False,
    "disabledDuet": False,
    "disabledStitch": False,
    "isAiGenerated": True  # For Sora videos
}
```

**Instagram (Reels):**
```python
target_config = {
    "targetType": "instagram",
    "mediaType": "reel"
}
```

### Account IDs (from Memory)
| Platform | ID | Username |
|----------|-----|----------|
| YouTube | 228 | Isaiah Dupree |
| YouTube | 3370 | lofi_creator |
| TikTok | 710 | @isaiah_dupree |
| TikTok | 243 | @the_isaiah_dupree |
| TikTok | 4508 | @dupree_isaiah |

### Key Files
- `Backend/services/publish_service.py` - Publishing logic
- `Backend/services/background_publisher.py` - Unified publish flow
- `Backend/services/blotato_service.py` - Blotato API wrapper
- `Backend/config/blotato_accounts.py` - Account configuration

---

## Complete Python Script Example

```python
"""
Complete pipeline: Ingest → Analyze → Schedule → Publish
"""
import asyncio
import httpx
from datetime import datetime, timedelta, timezone
from pathlib import Path

API_BASE = "http://localhost:5555"

async def run_pipeline(video_path: str, platform: str = "youtube", account_id: str = "228"):
    async with httpx.AsyncClient(timeout=300) as client:
        
        # Step 1: Ingest
        print(f"[1/4] Ingesting {video_path}...")
        resp = await client.post(
            f"{API_BASE}/api/media-db/ingest/file",
            params={"file_path": video_path}
        )
        result = resp.json()
        media_id = result["media_id"]
        print(f"       Media ID: {media_id}")
        
        # Step 2: Analyze
        print(f"[2/4] Analyzing...")
        resp = await client.post(f"{API_BASE}/api/media-db/analyze/{media_id}")
        analysis = resp.json()
        print(f"       Score: {analysis.get('pre_social_score')}")
        print(f"       Topics: {analysis.get('topics')}")
        
        # Step 3: Get generated title/caption
        print(f"[3/4] Getting content...")
        resp = await client.get(f"{API_BASE}/api/media-db/detail/{media_id}")
        detail = resp.json()
        title = detail.get("title", "Untitled")
        hook = detail.get("detected_hook", "Check this out!")
        
        # Step 4: Schedule post
        print(f"[4/4] Scheduling for {platform}...")
        schedule_time = datetime.now(timezone.utc) + timedelta(minutes=5)
        
        resp = await client.post(
            f"{API_BASE}/api/schedule/create",
            json={
                "media_id": media_id,
                "platform": platform,
                "account_id": account_id,
                "scheduled_time": schedule_time.isoformat(),
                "title": title,
                "caption": f"{hook}\n\n#content #video",
            }
        )
        schedule_result = resp.json()
        print(f"       Scheduled: {schedule_result}")
        
        return {
            "media_id": media_id,
            "title": title,
            "platform": platform,
            "scheduled_time": schedule_time.isoformat()
        }

# Run
if __name__ == "__main__":
    asyncio.run(run_pipeline(
        "/Users/isaiahdupree/Documents/SoraVideos/clean/cleaned_video.mp4",
        platform="youtube",
        account_id="228"
    ))
```

---

## Environment Variables Required

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres

# AI Services
GROQ_API_KEY=gsk_...          # Transcription (Whisper)
OPENAI_API_KEY=sk-...         # Content analysis (GPT-4)

# Publishing
BLOTATO_API_KEY=...           # Social media posting

# Cloud Storage (for publishing)
SUPABASE_URL=https://...
SUPABASE_KEY=...
# OR
GOOGLE_DRIVE_CREDENTIALS=...
```

---

## Starting the Services

### Backend API
```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
python -m uvicorn main:app --host 0.0.0.0 --port 5555 --reload
```

### Post Scheduler (Background)
The scheduler starts automatically with the backend. Check status:
```
GET http://localhost:5555/api/schedule/status
```

### Frontend Dashboard
```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/dashboard
npm run dev
# Runs on http://localhost:5557
```

---

## Troubleshooting

### Analysis Not Working
1. Check Groq API key: `echo $GROQ_API_KEY`
2. Check video has audio: `ffprobe -v error -show_streams video.mp4`
3. Check logs: `tail -f Backend/logs/app.log`

### Scheduling Not Publishing
1. Check Blotato API key configured
2. Check scheduler status: `GET /api/schedule/status`
3. Check for failed posts: `GET /api/schedule/queue`

### Duplicate Detection
Videos are deduplicated by:
- `source_uri` (file path) during ingest
- `media_id + platform + account_id` during publish

---

## API Quick Reference

| Action | Endpoint | Method |
|--------|----------|--------|
| Ingest single | `/api/media-db/ingest/file?file_path=...` | POST |
| Batch ingest | `/api/media-db/batch/ingest` | POST |
| Analyze single | `/api/media-db/analyze/{id}` | POST |
| Batch analyze | `/api/media-db/batch/analyze` | POST |
| Get detail | `/api/media-db/detail/{id}` | GET |
| List all | `/api/media-db/list` | GET |
| Schedule post | `/api/schedule/create` | POST |
| Scheduler status | `/api/schedule/status` | GET |
| Blotato accounts | `/api/blotato/accounts` | GET |
