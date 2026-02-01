# MediaPoster Microservices → Existing Repos Mapping

**Created:** 2026-02-01  
**Status:** Active Planning  
**Purpose:** Map MediaPoster services to existing repos in ~/Documents/Software

---

## Executive Summary

After analyzing the `~/Documents/Software` directory, we found **6 existing repos** that align with the proposed microservices architecture. This means we don't need to create new repos from scratch - we can offload MediaPoster services to mature, existing codebases.

---

## Existing Repos Inventory

| Repo | Path | Status | Tech Stack |
|------|------|--------|------------|
| **Safari Automation** | `/Safari Automation/` | ✅ Active | TypeScript, Safari WebDriver |
| **Local EverReach CRM** | `/Local EverReach CRM/` | ✅ Active | TypeScript, Supabase |
| **Remotion** | `/Remotion/` | ✅ Active | TypeScript, Remotion, Node.js |
| **TTS** | `/TTS/` | ✅ Active | Python, IndexTTS2, ElevenLabs |
| **WaterMarkRemover - BlankLogo** | `/WaterMarkRemover - BlankLogo/` | ✅ Active | TypeScript, RunPod |
| **ai-video-platform** | `/ai-video-platform/` | ⚠️ Reference | Next.js, Remotion |

---

## Detailed Repo → Service Mapping

### 1. 🌐 Safari Automation → Safari Automation Service

**Repo:** `/Users/isaiahdupree/Documents/Software/Safari Automation/`

**Already Contains:**
```
packages/
├── browser/          # Safari WebDriver control
├── crm-core/         # CRM functionality (client, engines, models)
├── instagram-dm/     # Instagram DM automation
├── tiktok-dm/        # TikTok DM automation  
├── twitter-dm/       # Twitter DM automation
├── protocol/         # Communication protocol
├── scheduler/        # Job scheduling
├── selectors/        # DOM selectors registry
├── services/         # Service layer
├── social-cli/       # CLI tools
└── unified-client/   # Unified API client
```

**MediaPoster Services to Move:**
| MediaPoster File | → Safari Automation Package |
|------------------|----------------------------|
| `services/safari_automation_client.py` | `packages/browser/` |
| `services/safari_automation_orchestrator.py` | `packages/services/` |
| `services/safari_event_listener.py` | `packages/browser/` |
| `services/safari_queue_manager.py` | `packages/scheduler/` |
| `services/safari_session_service.py` | `packages/browser/` |
| `services/auto_comment_service.py` | `packages/services/` |
| `automation/safari_*.py` (all) | `python/` |
| `automation/tiktok_*.py` | `packages/tiktok-dm/` |
| `automation/twitter_*.py` | `packages/twitter-dm/` |

**Why This Makes Sense:**
- Safari Automation already has the TypeScript infrastructure
- Platform adapters exist (Instagram, TikTok, Threads, Twitter)
- Selector registry with versioning and fallbacks
- Audit logging built-in
- Monorepo structure with `packages/` ready for code

**Docs Already Moved:** ✅ (moved on 2026-01-31)
- `docs/selectors/` - All platform selector references
- `docs/prds/` - Full control PRDs

---

### 2. 💬 Local EverReach CRM → Engagement/CRM Service

**Repo:** `/Users/isaiahdupree/Documents/Software/Local EverReach CRM/`

**Already Contains:**
```
packages/
├── crm-core/           # Core CRM library
│   └── src/
│       ├── engines/    # Scoring, coaching, copilot
│       ├── models/     # TypeScript types
│       └── client/     # Supabase client
├── crm-server/         # REST API server
└── instagram-dm/       # Instagram DM automation
    └── src/
        ├── automation/ # Safari driver, DM operations
        └── api/        # REST API + client
```

**MediaPoster Services to Move:**
| MediaPoster File | → EverReach CRM Package |
|------------------|-------------------------|
| `services/inbox/` | `packages/crm-core/src/engines/` |
| `services/dm_outreach/` | `packages/instagram-dm/` |
| `services/dm_fetcher_service.py` | `packages/crm-server/` |
| `services/dm_permission_service.py` | `packages/crm-core/` |
| `services/dm_warmth_system.py` | `packages/crm-core/src/engines/` |
| `services/comment_fetcher_service.py` | `packages/crm-server/` |
| `services/relationship_ai.py` | `packages/crm-core/src/engines/` |
| `services/relationship_crm.py` | `packages/crm-core/` |
| `services/relationship_cadence.py` | `packages/crm-core/src/engines/` |
| `services/relationship_fit_signals.py` | `packages/crm-core/src/engines/` |
| `services/relationship_metrics.py` | `packages/crm-core/src/engines/` |
| `services/engagement/` | `packages/crm-core/src/engines/` |
| `services/everreach/` | Root integration |
| `services/lead_discovery_service.py` | `packages/crm-core/` |
| `services/touchpoint_service.py` | `packages/crm-core/` |
| `services/reply_suggestions.py` | `packages/crm-core/src/engines/` |

**Why This Makes Sense:**
- Already has relationship scoring (6R framework)
- DM coaching engine exists
- AI copilot for replies
- Instagram automation already integrated
- Same Supabase backend
- Could become a standalone product

**Current Features in EverReach CRM:**
- `calculateRelationshipScore()` - Score relationships
- `analyzeConversation()` - DM coaching
- `generateReplySuggestions()` - AI copilot
- Pipeline analytics
- Automated outreach scheduling

---

### 3. 🎬 Remotion → Video Generation Service

**Repo:** `/Users/isaiahdupree/Documents/Software/Remotion/`

**Already Contains:**
```
src/
├── compositions/     # 17 video compositions
├── scenes/          # 11 scene components
├── ad-templates/    # 10 ad templates
├── audio/           # 14 audio utilities
├── components/      # 17 UI components
├── animations/      # Animation utilities
├── api/             # 16 API endpoints
├── analytics/       # Render analytics
├── integrations/    # External integrations
├── format/          # Format utilities
├── sfx/             # Sound effects
├── video-toolkit/   # Video utilities
└── Root.tsx         # Main composition (72KB!)
```

**MediaPoster Services to Move:**
| MediaPoster File | → Remotion Location |
|------------------|---------------------|
| `services/remotion/` | `src/` (merge) |
| `services/video_renderer/` | `src/api/` |
| `services/video_generation/` | `src/compositions/` |
| `services/visuals/` | `src/components/` |
| `services/visual_remotion_renderer.py` | `scripts/` |
| `services/visual_poster_service.py` | `src/api/` |
| `services/visual_campaign_service.py` | `src/api/` |
| `services/character_generator.py` | `src/compositions/` |
| `services/broll_video_producer.py` | `src/scenes/` |
| `services/explainer_video/` | `src/compositions/` |
| `services/segment_editor.py` | `src/utils/` |
| `services/segment_engine.py` | `src/utils/` |

**Why This Makes Sense:**
- Already has full Remotion setup with 17 compositions
- Ad templates ready
- API layer exists
- High-memory rendering infrastructure
- Output directory for renders

---

### 4. 🎙️ TTS → Voice/Audio Service (Part of Video Gen)

**Repo:** `/Users/isaiahdupree/Documents/Software/TTS/`

**Already Contains:**
```
├── IndexTTS2/                    # IndexTTS2 model
├── clone_voice_indextts2.py     # Voice cloning
├── clone_voice_elevenlabs.py    # ElevenLabs integration
├── generate_with_emotions_api.py # Emotion control
├── audio_refinement_processor.py # Audio cleanup
├── audio_quality_analyzer.py    # Quality checks
├── process_isolation_with_chunking.py # Voice isolation
├── training_data/               # Voice training data
├── isolated_audio/              # Processed audio
└── test_outputs/                # Generated audio
```

**MediaPoster Services to Move:**
| MediaPoster File | → TTS Location |
|------------------|----------------|
| `services/tts/` | Root (merge) |
| `services/voice/` | `voice_cloning/` (new) |
| `services/voice_cloning_quality_assessor.py` | Root |
| `services/audio_analyzer.py` | Root |
| `services/audio_service.py` | Root |
| `services/transcription.py` | Root |
| `services/transcription_adapter.py` | Root |
| `services/whisper_transcriber.py` | Root |
| `services/music/` | `music/` (new) |
| `services/music_library.py` | `music/` |
| `services/music_matcher.py` | `music/` |
| `services/music_selector.py` | `music/` |

**Why This Makes Sense:**
- Complete TTS infrastructure already
- IndexTTS2 + ElevenLabs integrations
- Voice cloning workflow exists
- Audio processing pipeline
- Python-based (matches MediaPoster)

---

### 5. 📹 WaterMarkRemover - BlankLogo → Media Processing Service

**Repo:** `/Users/isaiahdupree/Documents/Software/WaterMarkRemover - BlankLogo/`

**Already Contains:**
```
├── apps/               # Applications
├── packages/           # Shared packages
├── scripts/            # Processing scripts
├── test-videos/        # Test assets
├── Dockerfile.runpod   # GPU deployment
├── Dockerfile.serverless # Serverless deployment
├── docker-compose.yml  # Local dev
└── render.yaml         # Render.com config
```

**MediaPoster Services to Move:**
| MediaPoster File | → BlankLogo Location |
|------------------|----------------------|
| `services/video_analyzer.py` | `packages/analyzer/` |
| `services/video_analysis.py` | `packages/analyzer/` |
| `services/batch_video_analyzer.py` | `packages/analyzer/` |
| `services/frame_analyzer.py` | `packages/analyzer/` |
| `services/frame_sampler.py` | `packages/analyzer/` |
| `services/thumbnail_service.py` | `packages/thumbnail/` |
| `services/thumbnail_generator.py` | `packages/thumbnail/` |
| `services/format_detector.py` | `packages/detector/` |
| `services/format_classifier.py` | `packages/detector/` |
| `services/clip_extraction/` | `packages/extraction/` |
| `services/clip_extraction_service.py` | `packages/extraction/` |
| `services/matting/` | `packages/matting/` |
| `services/background_removal.py` | `packages/matting/` |
| `services/deduplication_guard.py` | `packages/utils/` |
| `services/duplicate_detector.py` | `packages/utils/` |

**Why This Makes Sense:**
- Already has video processing infrastructure
- RunPod GPU deployment ready
- Docker setup for heavy processing
- Serverless deployment option
- pnpm monorepo structure

---

### 6. 🤖 AI Services → New Package in Existing Repo OR New Repo

**Option A:** Add to Safari Automation as `packages/ai-services/`
**Option B:** Create new repo `mediaposter-ai-services/`

**MediaPoster Services to Move:**
| MediaPoster File | Purpose |
|------------------|---------|
| `services/ai_client.py` | LLM API wrapper |
| `services/ai_content_analyzer.py` | Content analysis |
| `services/ai_content_generator.py` | Content generation |
| `services/ai_content_service.py` | Service layer |
| `services/ai_recommendation_service.py` | Recommendations |
| `services/ai_thumbnail_selector.py` | Thumbnail AI |
| `services/ai_title_generator.py` | Title generation |
| `services/awareness_classifier.py` | Awareness levels |
| `services/fate_scorer.py` | FATE scoring |
| `services/sentiment_analyzer.py` | Sentiment analysis |
| `services/vision_analyzer.py` | Vision API |
| `services/enhanced_vision_analyzer.py` | Enhanced vision |
| `services/content_generation_pipeline.py` | Pipeline |
| `services/ai_providers/` | Provider adapters |

**Recommendation:** Create as `packages/ai-services/` in Safari Automation since it needs to integrate with multiple services.

---

## Updated Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                       MEDIAPOSTER CORE                               │
│              (Scheduling, Publishing, API Gateway)                   │
│                    ~/Software/MediaPoster/                           │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┬──────────────────┐
        │ HTTP/WS           │ Redis Queue       │ Event Bus        │
        ▼                   ▼                   ▼                  ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│    Safari     │  │   Remotion    │  │     TTS       │  │  BlankLogo    │
│  Automation   │  │ Video Render  │  │ Voice/Audio   │  │Media Process  │
│               │  │               │  │               │  │               │
│ ~/Safari      │  │ ~/Remotion/   │  │ ~/TTS/        │  │~/WaterMark..  │
│ Automation/   │  │               │  │               │  │               │
└───────────────┘  └───────────────┘  └───────────────┘  └───────────────┘
        │                   │                   │                  │
        │          ┌────────┴───────────────────┴──────────┐       │
        │          │            Merge into:                 │       │
        │          │    Video Generation Service            │       │
        │          └────────────────────────────────────────┘       │
        │                                                           │
        ▼                                                           │
┌───────────────┐                                                   │
│ EverReach CRM │◄──────────────────────────────────────────────────┘
│               │
│~/Local Ever.. │
│    CRM/       │
└───────────────┘
        │
        └──────────────────────────────────────────────────────────┐
                                                                   │
                              ┌────────────────────────────────────┘
                              ▼
                      ┌───────────────┐
                      │   Supabase    │
                      │  PostgreSQL   │
                      │   @ :54322    │
                      └───────────────┘
```

---

## Service Communication Patterns

| From | To | Method | Why |
|------|-----|--------|-----|
| MediaPoster Core | Safari Automation | WebSocket | Real-time browser control |
| MediaPoster Core | Remotion | HTTP + Redis Queue | Async render jobs |
| MediaPoster Core | TTS | HTTP + Redis Queue | Async audio generation |
| MediaPoster Core | BlankLogo | HTTP + Redis Queue | Async video processing |
| MediaPoster Core | EverReach CRM | Event Bus | Async engagement |
| Safari Automation | EverReach CRM | Direct Import | DM data sync |
| All Services | Supabase | PostgreSQL | Shared database |

---

## Migration Priority Matrix

| Service | Target Repo | Priority | Effort | Impact |
|---------|-------------|----------|--------|--------|
| Safari Automation | Safari Automation | 🟢 HIGH | Medium | High - Browser ops on Mac only |
| Video Rendering | Remotion | 🟢 HIGH | High | High - Heavy resource usage |
| Media Processing | BlankLogo | 🟢 HIGH | High | High - GPU processing |
| Voice/Audio | TTS | 🟡 MEDIUM | Medium | Medium - Specialized |
| CRM/Engagement | EverReach CRM | 🟡 MEDIUM | Medium | Medium - Separate product |
| AI Services | New or Safari Auto | 🟠 LOW | Low | Low - API-bound only |

---

## Step-by-Step Migration Plan

### Phase 1: Safari Automation (Week 1-2)
1. ✅ Move docs/selectors to Safari Automation (DONE)
2. Create `python/` package in Safari Automation
3. Move `automation/safari_*.py` files
4. Set up WebSocket server for MediaPoster communication
5. Update MediaPoster to use Safari Automation API

### Phase 2: Video Generation (Week 3-4)
1. Audit Remotion repo structure
2. Move `services/remotion/` to Remotion repo
3. Move `services/video_generation/` 
4. Create render API endpoint
5. Set up Redis queue for render jobs

### Phase 3: Media Processing (Week 5-6)
1. Create `packages/analyzer/` in BlankLogo
2. Move video analysis services
3. Move thumbnail services
4. Set up Docker for GPU processing
5. Create processing API

### Phase 4: Voice/Audio (Week 7)
1. Move TTS services to TTS repo
2. Move music services
3. Create audio generation API
4. Integrate with Video Generation

### Phase 5: CRM/Engagement (Week 8)
1. Map data models between repos
2. Move relationship services
3. Move DM services
4. Set up event bus integration

---

## Files to Keep in MediaPoster Core

These services stay in MediaPoster as they ARE the core product:

```
services/
├── post_scheduler.py          # Core scheduling
├── blotato_service.py         # Blotato integration
├── blotato_api.py             # Blotato API
├── publish_service.py         # Publishing
├── publisher_service.py       # Publisher
├── background_publisher.py    # Background publishing
├── multi_platform_publisher.py # Multi-platform
├── sleep_mode_service.py      # Sleep/wake
├── smart_scheduler.py         # Smart scheduling
├── external_queue_manager.py  # External API queue
├── wake_triggers.py           # Wake triggers
├── approval_queue.py          # Approval workflow
├── inventory_aware_scheduler.py # Inventory
├── weekly_planner.py          # Weekly planning
├── same_day_adjuster.py       # Same-day adjustments
└── event_bus/                 # Event bus (shared)
```

---

## Shared Infrastructure

All repos should share:

1. **Supabase Database** - Same PostgreSQL instance
2. **Redis** - Job queues and caching
3. **Event Bus** - Cross-service events
4. **Auth** - Shared authentication

### Redis Setup (add to each repo)
```yaml
# docker-compose.yml addition
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
```

### Service Registry
```typescript
// shared/services.ts
export const SERVICES = {
  core: 'http://localhost:5555',
  safari: 'http://localhost:6001',
  remotion: 'http://localhost:6002',
  tts: 'http://localhost:6003',
  blanklogo: 'http://localhost:6004',
  crm: 'http://localhost:6005',
};
```

---

## Benefits of This Approach

1. **No new repos needed** - Use existing, mature codebases
2. **Faster migration** - Infrastructure already exists
3. **Proven patterns** - Each repo has established architecture
4. **Resource isolation** - Heavy services on dedicated machines
5. **Independent scaling** - Scale each service as needed
6. **Team ownership** - Clear repo boundaries
7. **Reduced MediaPoster complexity** - Focus on core scheduling

---

## Next Steps

1. [x] Review this mapping with stakeholders
2. [x] Prioritize Phase 1 (Safari Automation)
3. [x] Create API contracts between services
4. [ ] Set up shared Redis instance
5. [x] Begin incremental migration

---

## NEW: Microservices Created (2026-02-01)

Two new microservices have been extracted and deployed:

### media-pipeline (Port 6004)
**Repository:** https://github.com/IsaiahDupree/media-pipeline
**Local Path:** `/Users/isaiahdupree/Documents/Software/media-pipeline/`
**Total Code:** 12,913 lines moved from MediaPoster

| Endpoint | Implementation | Status |
|----------|---------------|--------|
| `GET /health` | Health check | ✅ Real |
| `POST /api/analyze` | ffprobe video analysis | ✅ Real |
| `POST /api/thumbnail/generate` | ffmpeg frame extraction | ✅ Real |
| `POST /api/format/detect` | FormatDetector (15 types) | ✅ Real |
| `POST /api/clip/extract` | ffmpeg clip extraction | ✅ Real |
| `POST /api/deduplicate/check` | DuplicateDetector | ✅ Real |
| `POST /api/transcribe` | OpenAI Whisper | ✅ Real |

**Services Copied:**
- `frame_analyzer.py`, `frame_analyzer_enhanced.py`, `frame_sampler.py`
- `video_analyzer.py`, `batch_video_analyzer.py`, `video_analysis.py`
- `thumbnail_generator.py`, `thumbnail_service.py`, `ai_thumbnail_selector.py`
- `transcription.py`, `whisper_transcriber.py`, `transcription_adapter.py`
- `broll_detector.py`, `duplicate_detector.py`

### content-intelligence (Port 6006)
**Repository:** https://github.com/IsaiahDupree/content-intelligence
**Local Path:** `/Users/isaiahdupree/Documents/Software/content-intelligence/`
**Total Code:** 7,959 lines moved from MediaPoster

| Endpoint | Implementation | Status |
|----------|---------------|--------|
| `GET /health` | Health check | ✅ Real |
| `POST /api/score/fate` | FATEScorer (F/A/T/E) | ✅ Real |
| `POST /api/classify/awareness` | AwarenessClassifier (5 levels) | ✅ Real |
| `POST /api/analyze/sentiment` | SentimentAnalyzer | ✅ Real |
| `POST /api/generate/title` | Groq/OpenAI AI | ✅ Real |
| `POST /api/generate/caption` | Groq/OpenAI AI | ✅ Real |
| `POST /api/vision/analyze` | VisionAnalyzer (OpenAI Vision) | ✅ Real |

**Services Copied:**
- `fate_scorer.py`, `awareness_classifier.py`, `sentiment_analyzer.py`
- `vision_analyzer_standalone.py`, `ai_content_analyzer.py`
- `ai_title_generator.py`, `ai_content_generator.py`, `hook_generator.py`
- `ai_recommendation_service.py`

---

## Connectivity from MediaPoster

```python
# Backend/services/microservices_client.py
from services.microservices_client import get_microservices_client

client = get_microservices_client()

# Media Pipeline
await client.analyze_video("/path/to/video.mp4")
await client.generate_thumbnails("/path/to/video.mp4", count=5)
await client.detect_format("/path/to/video.mp4", transcript="...")
await client.extract_clip("/path/to/video.mp4", start_time=10, end_time=30)

# Content Intelligence
await client.score_fate("Your content text here...")
await client.classify_awareness("Are you struggling with...")
await client.analyze_sentiment("This is amazing!")
await client.generate_titles("How to grow TikTok", platform="tiktok")
await client.generate_caption("Video about tips", platform="instagram")
```

---

## Updated Service Registry

```python
# Environment variables
MEDIA_PIPELINE_URL=http://localhost:6004
CONTENT_INTEL_URL=http://localhost:6006
SAFARI_URL=http://localhost:6001
REMOTION_URL=http://localhost:6002
```

| Service | Port | Status |
|---------|------|--------|
| MediaPoster Core | 5555 | ✅ Active |
| Safari Automation | 6001 | ⏸️ Optional |
| Remotion | 6002 | ⏸️ Optional |
| **media-pipeline** | 6004 | ✅ **Active** |
| **content-intelligence** | 6006 | ✅ **Active** |

---

## Quick Start Commands

```bash
# Start media-pipeline
cd ~/Documents/Software/media-pipeline
source venv/bin/activate
python app.py

# Start content-intelligence
cd ~/Documents/Software/content-intelligence
source venv/bin/activate
python app.py

# Test connectivity
curl http://localhost:6004/health
curl http://localhost:6006/health
```
