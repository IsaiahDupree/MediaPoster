# PRD: System Benchmarks & Critical Workflows

**Version:** 1.0  
**Date:** January 20, 2026  
**Status:** Specification Complete  
**Priority:** Critical  
**Estimated Effort:** 3-4 weeks

---

## Executive Summary

This PRD defines the **critical benchmark workflows** that MediaPoster must successfully execute to be considered production-ready. These benchmarks validate end-to-end functionality across content ingestion, AI analysis, automation, multi-platform publishing, and resource management.

---

## Current System Status (As of Jan 20, 2026)

### Infrastructure Health

| Component | Status | Details |
|-----------|--------|---------|
| Backend API | ✅ Running | Port 5555, 832 endpoints |
| Database | ✅ Connected | Supabase operational |
| CPU Monitor | ✅ Active | Auto-sleep enabled (5% threshold, 300s timeout) |
| Sleep Mode | ✅ Awake | Wake triggers functional |
| Blotato Accounts | ✅ Connected | 22 accounts across 9 platforms |

### Media Inventory

| Metric | Value |
|--------|-------|
| External Drive | `/Volumes/My Passport/MediaPoster` |
| Total Files | 11,158 |
| Total Size | 190.27 GB |
| Ingested to DB | 0 (needs ingestion) |
| Analyzed | 0 |

---

## Benchmark 1: Content Ingestion & Safe Data Export

### BM-001: Directory Ingestion Pipeline

**Objective:** Ingest content from a directory, run AI analysis, and export analysis data to a "completed save" location (references only, not media files).

#### Workflow Steps

```
┌─────────────────────────────────────────────────────────────────┐
│  1. SCAN DIRECTORY                                              │
│     /Volumes/My Passport/MediaPoster/workspace1/iphone_import   │
│     → Detect all video/image files                              │
│     → Extract metadata (duration, dimensions, codec, date)      │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. INGEST TO DATABASE                                          │
│     → Create media_items record                                 │
│     → Store source_uri (reference to original file)             │
│     → Hash file for deduplication                               │
│     → NO DUPLICATION of video/image files                       │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  3. AI ANALYSIS                                                 │
│     → Visual analysis (OpenAI Vision API)                       │
│     → Generate titles (5 variations)                            │
│     → Generate descriptions (3 variations)                      │
│     → Hashtag suggestions per platform                          │
│     → Content niche detection                                   │
│     → Quality scoring                                           │
│     → Thumbnail extraction                                      │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  4. EXPORT TO SAFE LOCATION                                     │
│     Target: /Volumes/My Passport/MediaPoster/completed_analysis │
│                                                                   │
│     Export includes:                                              │
│     ├── media_manifest.json (all media references)              │
│     ├── analysis_data/                                          │
│     │   ├── {media_id}_analysis.json                           │
│     │   └── ...                                                 │
│     ├── thumbnails/                                             │
│     │   ├── {media_id}_thumb.jpg                               │
│     │   └── ...                                                 │
│     └── export_metadata.json (export timestamp, counts)         │
│                                                                   │
│     DOES NOT INCLUDE: Video files, image files                   │
│     ONLY: References (source_uri), analysis data, thumbnails    │
└─────────────────────────────────────────────────────────────────┘
```

#### API Endpoints Required

```
POST /api/ingestion/start
  - config: { directory, enable_ai_analysis, export_on_complete }

GET  /api/ingestion/status
  - Returns: { scanned, ingested, analyzing, analyzed, exported }

POST /api/ingestion/export
  - Exports all analysis data to safe location

GET  /api/media-db/stats
  - Returns inventory counts and sizes
```

#### Database Schema for Safe Export

```sql
CREATE TABLE export_manifests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    export_path TEXT NOT NULL,
    export_timestamp TIMESTAMPTZ DEFAULT NOW(),
    total_media_count INTEGER,
    total_analysis_count INTEGER,
    total_thumbnail_count INTEGER,
    export_size_bytes BIGINT,
    status VARCHAR(20) DEFAULT 'pending',
    metadata JSONB
);

CREATE TABLE media_items (
    id UUID PRIMARY KEY,
    source_uri TEXT NOT NULL,              -- Reference to original file
    source_hash VARCHAR(64),               -- SHA256 for deduplication
    file_name TEXT,
    file_size BIGINT,
    duration_seconds FLOAT,
    width INTEGER,
    height INTEGER,
    codec TEXT,
    created_at TIMESTAMPTZ,
    analysis_status VARCHAR(20),
    analysis_data JSONB,                   -- AI analysis results
    thumbnail_path TEXT,                   -- Exported thumbnail location
    -- NO blob storage of actual video/image
);
```

#### Success Criteria

| Metric | Target |
|--------|--------|
| Ingestion rate | > 100 files/minute |
| Analysis rate | > 10 files/minute |
| Export completeness | 100% of analyzed items |
| Data recovery | Full restore from export |

---

## Benchmark 2: Resource Monitoring & Thresholds

### BM-002: CPU/GPU Utilization Management

**Objective:** Monitor and enforce resource limits during backend and frontend operation.

#### Resource Thresholds

| Resource | Idle Threshold | Warning | Critical | Auto-Sleep |
|----------|---------------|---------|----------|------------|
| CPU | < 5% | 70% | 90% | After 5 min idle |
| Memory | < 40% | 80% | 95% | N/A |
| GPU | < 10% | 70% | 95% | N/A |

#### Current Implementation Status

```json
{
  "cpu_monitor": {
    "enabled": true,
    "check_interval": 5,
    "idle_threshold": 5.0,
    "idle_timeout": 300,
    "auto_sleep": true
  },
  "current_metrics": {
    "cpu_percent": 91.6,
    "memory_percent": 83.7,
    "memory_used_mb": 8302
  }
}
```

#### Required Enhancements

```python
# Backend/services/resource_manager.py

class ResourceManager:
    """
    Unified resource monitoring with enforced thresholds.
    """
    
    # Thresholds
    CPU_WARNING = 70.0
    CPU_CRITICAL = 90.0
    MEMORY_WARNING = 80.0
    MEMORY_CRITICAL = 95.0
    GPU_WARNING = 70.0
    GPU_CRITICAL = 95.0
    
    async def check_resources(self) -> ResourceStatus:
        """Check all resources and return status."""
        return ResourceStatus(
            cpu=self._get_cpu_status(),
            memory=self._get_memory_status(),
            gpu=self._get_gpu_status(),
            can_start_heavy_task=self._can_start_heavy_task(),
            throttle_level=self._calculate_throttle()
        )
    
    async def wait_for_resources(self, required: ResourceRequirements) -> bool:
        """Wait until resources are available for a task."""
        pass
    
    def throttle_if_needed(self) -> float:
        """Return delay factor (1.0 = normal, 2.0 = half speed)."""
        pass
```

#### Dashboard Widget

```
┌─────────────────────────────────────────────────────────────────┐
│  System Resources                                    [⟳ Live]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  CPU Usage                                                       │
│  ████████████████████████████████░░░░░░░░  78% ⚠️                │
│  Per Core: [58%][51%][46%][42%][73%][73%][73%][73%][63%]        │
│                                                                   │
│  Memory                                                          │
│  ████████████████████████████████████░░░░  84% ⚠️                │
│  Used: 8.3 GB / 12 GB  •  Available: 4.0 GB                     │
│                                                                   │
│  GPU (Apple M2)                                                  │
│  ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  22% ✅                │
│                                                                   │
│  Auto-Sleep: Enabled  •  Idle: 0s / 300s until sleep            │
│                                                                   │
│  [Pause Tasks] [Force Sleep] [View History]                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Benchmark 3: Automation Status & Media Constraints

### BM-003: Automation Inventory Dashboard

**Objective:** Track all automations, their status, resource needs, and media availability.

#### Automation Registry

```sql
CREATE TABLE automations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    type VARCHAR(50) NOT NULL,  -- 'posting', 'dm_sync', 'engagement', 'scraping'
    platform VARCHAR(20),
    
    -- Status
    status VARCHAR(20) DEFAULT 'inactive',  -- active, paused, error, inactive
    last_run TIMESTAMPTZ,
    next_run TIMESTAMPTZ,
    run_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    last_error TEXT,
    
    -- Schedule
    schedule_cron TEXT,
    schedule_interval_minutes INTEGER,
    
    -- Resource requirements
    requires_safari BOOLEAN DEFAULT false,
    requires_gpu BOOLEAN DEFAULT false,
    estimated_cpu_percent FLOAT,
    estimated_duration_seconds INTEGER,
    
    -- Media requirements
    requires_media BOOLEAN DEFAULT false,
    media_type VARCHAR(20),  -- 'video', 'image', 'any'
    media_per_run INTEGER DEFAULT 1,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE automation_media_usage (
    automation_id UUID REFERENCES automations(id),
    media_consumed_count INTEGER DEFAULT 0,
    media_remaining_count INTEGER,
    days_until_empty FLOAT,
    last_calculated TIMESTAMPTZ DEFAULT NOW()
);
```

#### Automation Status Dashboard

```
┌─────────────────────────────────────────────────────────────────┐
│  Automation Center                              [+ New] [⟳]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Active Automations                                              │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ ✅ TikTok Daily Posts    Active   Next: 2h 15m              ││
│  │    Media: 45 videos remaining (15 days @ 3/day)             ││
│  │    Resources: CPU 15%, Safari ✓                             ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ ✅ Instagram Reels       Active   Next: 4h 30m              ││
│  │    Media: 120 videos remaining (40 days @ 3/day)            ││
│  │    Resources: CPU 10%, Blotato API                          ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ ⚠️  Twitter DM Sync      Active   Last: 30m ago             ││
│  │    Media: N/A (no media required)                           ││
│  │    Resources: Safari ✓  ⚠️ Session expires in 2h            ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ ❌ YouTube Shorts        Error    Last: 2d ago              ││
│  │    Error: "Blotato auth expired"                            ││
│  │    Media: 30 clips ready                                    ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
│  ⚠️ Media Alerts                                                 │
│  • TikTok posts: Only 15 days of content remaining              │
│  • Instagram stories: EMPTY - needs content                     │
│                                                                   │
│  [View All] [Pause All] [Generate Report]                       │
└─────────────────────────────────────────────────────────────────┘
```

#### Media Constraint Tracking

```python
async def check_media_constraints() -> MediaConstraintReport:
    """
    Check all automations for media availability.
    Returns warning if any automation will run out of media.
    """
    report = MediaConstraintReport()
    
    for automation in await get_active_automations():
        if not automation.requires_media:
            continue
        
        available = await count_available_media(
            media_type=automation.media_type,
            platform=automation.platform
        )
        
        daily_consumption = automation.media_per_run * runs_per_day(automation)
        days_remaining = available / daily_consumption if daily_consumption > 0 else float('inf')
        
        if days_remaining < 7:
            report.add_warning(automation, days_remaining, available)
        if days_remaining < 1:
            report.add_critical(automation, days_remaining, available)
    
    return report
```

---

## Benchmark 4: Sora → AI Analysis → Twitter

### BM-004: End-to-End Sora Video Workflow

**Objective:** Generate a video via Sora, analyze it, and post to Twitter.

#### Workflow Sequence

```
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Sora Video Generation (Safari Automation)             │
│                                                                   │
│  Input:                                                          │
│    prompt: "A serene mountain landscape at sunset..."           │
│    duration: 10 seconds                                          │
│    aspect_ratio: "9:16"                                          │
│                                                                   │
│  Process:                                                        │
│    1. Wake system if sleeping                                    │
│    2. Check Safari session (Platform.SORA)                       │
│    3. Navigate to sora.com                                       │
│    4. Enter prompt                                               │
│    5. Select duration/aspect ratio                               │
│    6. Click Generate                                             │
│    7. Poll for completion (5-10 minutes)                         │
│    8. Download video                                             │
│                                                                   │
│  Output: /path/to/sora_video_12345.mp4                          │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2: Watermark Removal (Optional)                           │
│                                                                   │
│  If Sora watermark detected:                                     │
│    → Use SoraWatermarkCleaner                                    │
│    → E2FGVI-HQ inpainting model                                  │
│    → GPU acceleration if available                               │
│                                                                   │
│  Output: /path/to/sora_video_12345_clean.mp4                    │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3: AI Analysis                                            │
│                                                                   │
│  Analysis includes:                                              │
│    → Visual content description                                  │
│    → Suggested titles (5 variations)                             │
│    → Suggested descriptions (3 variations)                       │
│    → Hashtag recommendations                                     │
│    → Best posting time                                           │
│    → Thumbnail extraction                                        │
│                                                                   │
│  Output: analysis_data.json                                      │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4: Post to Twitter                                        │
│                                                                   │
│  Method: Blotato API                                             │
│  Account: @IsaiahDupree7 (ID: 4151)                             │
│                                                                   │
│  Post content:                                                   │
│    text: {selected_title}                                        │
│    media: [video_path]                                           │
│                                                                   │
│  Output: post_id, post_url                                       │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 5: Track & Store                                          │
│                                                                   │
│  Store in database:                                              │
│    → posts table (post_id, platform, account, content)          │
│    → media_items linked to post                                  │
│    → Schedule checkback for metrics (1h, 6h, 24h)               │
│                                                                   │
│  Dashboard update: Refresh posted content page                   │
└─────────────────────────────────────────────────────────────────┘
```

#### API Sequence

```bash
# Step 1: Generate Sora video
POST /api/sora/generate
{
  "prompt": "A serene mountain landscape...",
  "duration": 10,
  "aspect_ratio": "9:16"
}
→ Returns: { "job_id": "sora_123" }

# Step 2: Poll for completion
GET /api/sora/jobs/sora_123
→ Returns: { "status": "completed", "video_path": "..." }

# Step 3: AI Analysis
POST /api/ai/analyze
{
  "media_path": "/path/to/video.mp4",
  "generate_titles": true,
  "generate_descriptions": true
}
→ Returns: { "analysis": {...}, "titles": [...] }

# Step 4: Post to Twitter
POST /api/twitter/post
{
  "account_id": 4151,
  "text": "Amazing sunset views 🌅",
  "media_paths": ["/path/to/video.mp4"]
}
→ Returns: { "post_id": "...", "url": "..." }
```

#### Success Criteria

| Step | Metric | Target |
|------|--------|--------|
| Sora generation | Success rate | > 95% |
| Watermark removal | Quality | No visible artifacts |
| AI analysis | Response time | < 30 seconds |
| Twitter post | Success rate | > 99% |
| End-to-end | Total time | < 15 minutes |

---

## Benchmark 5: DM Sync Automation

### BM-005: Cross-Platform DM Synchronization

**Objective:** Pull DM/message data from Instagram, TikTok, and Twitter and display in frontend.

#### Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  DM SYNC AUTOMATION                                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  TRIGGER: Scheduled (every 30 minutes) or Manual                │
│                                                                   │
│  PLATFORMS:                                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Instagram                                                    ││
│  │   Method: Safari Automation                                  ││
│  │   URL: instagram.com/direct/inbox                           ││
│  │   Accounts: @the_isaiah_dupree, @the_isaiah_dupree_, etc.   ││
│  │   Extract: Sender, message, timestamp, read status          ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ TikTok                                                       ││
│  │   Method: Safari Automation                                  ││
│  │   URL: tiktok.com/messages                                  ││
│  │   Accounts: @isaiah_dupree, @the_isaiah_dupree, etc.        ││
│  │   Extract: Sender, message, timestamp                       ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Twitter/X                                                    ││
│  │   Method: Safari Automation                                  ││
│  │   URL: x.com/messages                                       ││
│  │   Accounts: @IsaiahDupree7                                  ││
│  │   Extract: Sender, message, timestamp                       ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
│  OUTPUT TO DATABASE:                                             │
│    → dm_messages table                                           │
│    → dm_conversations table                                      │
│    → WebSocket push to frontend                                  │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### Frontend: Community Inbox

```
┌─────────────────────────────────────────────────────────────────┐
│  Community Inbox                    [Sync Now] Last: 5 min ago  │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌───────────────────────────────────────────────┐│
│  │ Filters  │  │                                               ││
│  │          │  │  @video_creator (Instagram)           2m ago  ││
│  │ ☑️ All   │  │  "Love your content! Can we collab?"         ││
│  │ ☐ Unread │  │  [Reply] [Mark Read] [AI Suggest]            ││
│  │          │  ├───────────────────────────────────────────────┤│
│  │ Platform │  │  @music_producer (TikTok)            15m ago  ││
│  │ ☑️ IG    │  │  "Check out my new track, would be perfect"  ││
│  │ ☑️ TikTok│  │  [Reply] [Mark Read] [AI Suggest]            ││
│  │ ☑️ Twitter│ ├───────────────────────────────────────────────┤│
│  │          │  │  @brand_manager (Twitter)             1h ago  ││
│  │ Account  │  │  "Interested in a sponsorship deal"          ││
│  │ [All ▼]  │  │  [Reply] [Mark Read] [AI Suggest]            ││
│  └──────────┘  └───────────────────────────────────────────────┘│
│                                                                   │
│  Unread: 12  •  Total: 156  •  AI Replies: 3 pending            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Benchmark 6: Dev Vlog → Viral Clips → YouTube Shorts

### BM-006: Long-Form to Short-Form Pipeline

**Objective:** Create a dev vlog with voice clone, use Opus-style clipping to find viral moments, and post shorts to YouTube.

#### End-to-End Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: Dev Vlog Creation                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  INPUT:                                                          │
│    → Topic: "Building an AI-powered content system"             │
│    → Script: Generated by AI or provided                        │
│    → Screen recordings / B-roll footage                         │
│                                                                   │
│  VOICE CLONING (Modal):                                          │
│    → Use cloned voice profile (Isaiah's voice)                  │
│    → Generate voiceover from script                             │
│    → Output: voiceover.wav                                       │
│                                                                   │
│  VIDEO ASSEMBLY:                                                 │
│    → Combine voiceover + visuals                                │
│    → Add background music (optional)                            │
│    → Export: dev_vlog_full.mp4 (10-15 minutes)                  │
│                                                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: Content Repurposing Engine (Opus-Style)               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  AI CLIP DETECTION:                                              │
│    → Analyze transcript for viral moments                       │
│    → Detect hooks, insights, emotional peaks                    │
│    → Score each potential clip (0-100 virality)                 │
│    → Select top 5-10 clips                                      │
│                                                                   │
│  CLIP PROCESSING:                                                │
│    For each clip:                                                │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │ 1. Extract clip segment (15-60 seconds)                 │  │
│    │ 2. Smart Reframing (16:9 → 9:16)                        │  │
│    │    → Face detection and centering                        │  │
│    │    → Keep speaker in frame                               │  │
│    │ 3. Add Captions                                          │  │
│    │    → Word-by-word animated captions                      │  │
│    │    → Style: Bold, centered, high contrast                │  │
│    │ 4. Add Title Card                                        │  │
│    │    → Top middle position                                 │  │
│    │    → Hook text from AI analysis                          │  │
│    │ 5. Export short                                          │  │
│    └─────────────────────────────────────────────────────────┘  │
│                                                                   │
│  OUTPUT: 5-10 YouTube Shorts ready for upload                   │
│                                                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: Publish to YouTube via Blotato                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  For each short:                                                 │
│    → Upload to YouTube (Account: Isaiah Dupree)                 │
│    → Set as Short (#Shorts in title/description)               │
│    → Add title, description, tags from AI analysis              │
│    → Schedule or publish immediately                            │
│                                                                   │
│  Track:                                                          │
│    → Store post record in database                              │
│    → Link to source long-form video                             │
│    → Schedule metric checkbacks                                 │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

#### Technical Components Required

| Component | Status | Files |
|-----------|--------|-------|
| Voice Cloning | 📋 PRD Ready | `PRD_MODAL_VOICE_CLONING.md` |
| Content Repurposing | 📋 PRD Ready | `PRD_CONTENT_REPURPOSING_ENGINE.md` |
| Face Detection | ⚠️ Partial | FFmpeg + OpenCV |
| Caption Generation | ⚠️ Partial | Whisper + styled overlay |
| Blotato YouTube | ✅ Ready | `api/endpoints/blotato.py` |

#### API Sequence

```bash
# Step 1: Generate voiceover
POST /api/voice/generate
{
  "voice_profile_id": "isaiah_v1",
  "script": "Today we're building...",
  "output_format": "wav"
}

# Step 2: Assemble video
POST /api/video/assemble
{
  "voiceover_path": "/path/to/voiceover.wav",
  "visual_assets": ["/path/to/screenrec.mp4"],
  "output_path": "/path/to/dev_vlog.mp4"
}

# Step 3: Find viral clips
POST /api/repurposing/analyze
{
  "video_path": "/path/to/dev_vlog.mp4",
  "target_clip_count": 5,
  "min_virality_score": 70
}

# Step 4: Generate shorts
POST /api/repurposing/generate-shorts
{
  "video_path": "/path/to/dev_vlog.mp4",
  "clips": [{"start": 120, "end": 150, "score": 85}, ...],
  "add_captions": true,
  "add_title_card": true,
  "face_centering": true,
  "output_aspect_ratio": "9:16"
}

# Step 5: Post to YouTube
POST /api/blotato/publish
{
  "platform": "youtube",
  "account_id": 228,
  "media_paths": ["/path/to/short_1.mp4"],
  "title": "This ONE trick changed everything #Shorts",
  "description": "...",
  "is_short": true
}
```

---

## Implementation Roadmap

### Week 1: Foundation

| Day | Task |
|-----|------|
| 1-2 | Safe Export system for analysis data |
| 3 | Resource Manager with GPU monitoring |
| 4-5 | Automation registry and status API |

### Week 2: Sora & DM Workflows

| Day | Task |
|-----|------|
| 1-2 | Sora → Twitter complete workflow |
| 3-4 | DM sync across platforms |
| 5 | Frontend: Community Inbox |

### Week 3: Content Repurposing

| Day | Task |
|-----|------|
| 1-2 | AI clip detection |
| 3 | Face centering / reframing |
| 4 | Caption generation |
| 5 | Title card overlay |

### Week 4: Integration & Testing

| Day | Task |
|-----|------|
| 1-2 | End-to-end testing all benchmarks |
| 3-4 | Dashboard integration |
| 5 | Documentation and handoff |

---

## Success Criteria Summary

| Benchmark | Description | Target |
|-----------|-------------|--------|
| BM-001 | Directory ingestion + safe export | 100 files/min |
| BM-002 | CPU/GPU stays under thresholds | < 90% sustained |
| BM-003 | Automation status visible | All 20+ automations |
| BM-004 | Sora → Twitter end-to-end | < 15 min total |
| BM-005 | DM sync across 3 platforms | < 5 min sync |
| BM-006 | Dev vlog → 5 shorts → YouTube | < 30 min total |

---

**Document Owner:** Engineering Team  
**Last Updated:** January 20, 2026
