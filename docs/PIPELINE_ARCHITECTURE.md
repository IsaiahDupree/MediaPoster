# MediaPoster Pipeline Architecture

## Overview

This document describes the complete video processing pipeline from ingestion to social media publishing.

---

## ✅ Safari Automation Uses the SAME Pipeline

The `SafariEventListener` uses the same `VideoReadyPipeline` that handles all video processing:

```python
# services/safari_event_listener.py line 70-72
@property
def pipeline(self):
    from services.video_ready_pipeline import VideoReadyPipeline
    self._pipeline = VideoReadyPipeline()
```

This means Safari-automated videos go through the exact same AI analysis and publishing flow as manually uploaded videos.

---

## 📊 Complete Pipeline Map

| Pipeline | Purpose | Frontend API | EventBus Topic |
|----------|---------|--------------|----------------|
| **VideoReadyPipeline** | Safari/Sora video → AI analysis → DB → Blotato | ❌ (WebSocket only) | `VIDEO_READY`, `PUBLISH_REQUESTED` |
| **IngestionAnalysisIntegrator** | Content ingestion → AI analysis | `/ingestion/*` | `CONTENT_INGESTED` |
| **PublishIntegrator** (ARCH-003) | Analysis → Blotato publishing | ❌ (EventBus only) | `PUBLISH_REQUESTED` |
| **BlotatoService** | Upload to Blotato → Social media | `/schedule/publish-now` | `publish.completed` |
| **ContentAnalysisOrchestrator** | Transcription + Vision + Psychology | `/content/analyze` | `ANALYSIS_COMPLETED` |
| **VideoAnalysisPipeline** | Whisper + Frame analysis | `/video-pipeline/execute` | N/A |
| **MasterOrchestrator** | Coordinates all subsystems | `/orchestrator/*` | All topics |

---

## 🔗 Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    VIDEO INGESTION SOURCES                       │
├─────────────────────────────────────────────────────────────────┤
│  Safari Automation        iPhone Import         API Upload       │
│  (WebSocket:7071)         (/ingestion/scan)    (/upload)        │
└────────┬────────────────────────┬───────────────────┬───────────┘
         │                        │                   │
         ▼                        ▼                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VideoReadyPipeline                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Ingest to DB │→ │ AI Analysis  │→ │ Save Analysis│           │
│  │(original_    │  │ (GPT-4o +    │  │(analyzed_    │           │
│  │ videos)      │  │  Whisper)    │  │ videos)      │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
└────────────────────────────┬────────────────────────────────────┘
                             │ EventBus: PUBLISH_REQUESTED
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PublishIntegrator (ARCH-003)                  │
│  - Extracts AI-generated titles/descriptions                    │
│  - Platform-specific formatting                                  │
│  - Account selection                                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BlotatoService                                │
│  - Upload video to Blotato cloud                                 │
│  - Send to YouTube (228), TikTok (710), Instagram (807)         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🖥️ Frontend-Accessible Endpoints

| Feature | Endpoint | Method |
|---------|----------|--------|
| **Schedule Post** | `/schedule/create` | POST |
| **Publish Now** | `/schedule/publish-now` | POST |
| **Publishing Queue** | `/publishing-queue/queue` | GET |
| **Add to Queue** | `/publishing-queue/add` | POST |
| **Ingestion Status** | `/ingestion/status` | GET |
| **Start Ingestion** | `/ingestion/start` | POST |
| **Scan Files** | `/ingestion/scan` | POST |
| **Sora Generate** | `/sora-automation/generate` | POST |
| **Sora Pipeline** | `/sora-automation/pipeline/full` | POST |
| **Content Analysis** | `/content/analyze` | POST |
| **Video Pipeline** | `/video-pipeline/execute` | POST |

---

## 📁 Key Files

### Core Pipeline
- `services/video_ready_pipeline.py` - Main video processing pipeline
- `services/publish_integrator.py` - ARCH-003: Analysis → Publishing bridge
- `services/blotato_service.py` - Blotato API integration
- `services/master_orchestrator.py` - Coordinates all subsystems

### Safari Automation
- `services/safari_event_listener.py` - WebSocket listener for Safari events
- `automation/safari_sora_scraper.py` - Sora video scraping
- `automation/sora_full_automation.py` - Full Sora automation

### Analysis
- `services/content_analysis_orchestrator.py` - Multi-step analysis
- `services/video_pipeline.py` - Whisper + Frame analysis
- `services/ingestion_analysis_integrator.py` - Auto-analyze on ingest

### EventBus Topics
- `services/event_bus/topics.py` - All event topic definitions

---

## 🔄 Video Processing Flow

### 1. Safari Browser Automation Flow
```
Safari detects video ready (WebSocket:7071)
    ↓
SafariEventListener receives event
    ↓
VideoReadyPipeline.process_video_ready()
    ↓
Step 0: Ingest to DB (original_videos table)
    ↓
Step 1: AI Analysis (GPT-4o + Whisper)
    - Transcription
    - Platform-specific captions (YouTube, TikTok, Instagram)
    - Virality scoring
    - Hashtag generation
    ↓
Step 2: Save Analysis (analyzed_videos table)
    ↓
Step 3: Publish via EventBus → PublishIntegrator → Blotato
```

### 2. Manual Upload Flow
```
User uploads via /upload endpoint
    ↓
IngestionAnalysisIntegrator
    ↓
VideoReadyPipeline (same as above)
```

### 3. iPhone Import Flow
```
/ingestion/scan scans iPhone import folder
    ↓
IngestionAnalysisIntegrator
    ↓
VideoReadyPipeline (same as above)
```

---

## 🗄️ Database Tables

| Table | Purpose |
|-------|---------|
| `original_videos` | Raw video metadata and file paths |
| `analyzed_videos` | AI analysis results (titles, captions, scores) |
| `scheduled_posts` | Posts scheduled for publishing |
| `weekly_plan_slots` | Weekly content planning slots |
| `platform_accounts` | Connected social media accounts |
| `safari_videos` | Safari automation video tracking |
| `sora_video_pipeline` | Sora generation pipeline state |

---

## 🧪 Testing

### Test Video Pipeline
```bash
python scripts/test_video_pipeline.py           # Test with smallest video
python scripts/test_video_pipeline.py --list    # List available videos
python scripts/test_video_pipeline.py --all     # Process all videos
python scripts/test_video_pipeline.py --publish # Actually publish
```

### Health Check
```bash
python scripts/health_check.py
```

### Database Audit
```bash
python scripts/db_audit.py
```

---

## 📡 EventBus Topics

| Topic | When Published |
|-------|----------------|
| `VIDEO_READY` | Video is ready for processing |
| `CONTENT_INGESTED` | Content file ingested to DB |
| `CONTENT_ANALYSIS_COMPLETED` | AI analysis finished |
| `PUBLISH_REQUESTED` | Request to publish content |
| `publish.completed` | Publishing finished successfully |

---

## 🔧 Platform Account IDs (Blotato)

| Platform | Account ID | Username |
|----------|------------|----------|
| YouTube | 228 | UCnDBsELI2OlaEl5yxA77HNA |
| TikTok | 710 | isaiah_dupree |
| Instagram | 807 | the_isaiah_dupree |
| Threads | 173 | the_isaiah_dupree_ |

---

## 📋 Summary

The MediaPoster pipeline is unified:
1. **All video sources** (Safari, iPhone, API) use the same `VideoReadyPipeline`
2. **Same AI analysis** (GPT-4o + Whisper) for all videos
3. **Same database** (original_videos → analyzed_videos)
4. **Same publishing** (EventBus → PublishIntegrator → Blotato)

This ensures consistent behavior regardless of how content enters the system.
