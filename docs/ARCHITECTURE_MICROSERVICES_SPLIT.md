# MediaPoster Microservices Split Architecture

**Created:** 2026-01-31  
**Status:** Proposal / Roadmap  
**Purpose:** Reduce system load by splitting MediaPoster into focused microservices

---

## Overview

The current MediaPoster monolith (~75MB main.py with 600+ service files) handles everything from scheduling to video generation. This proposal outlines how to split it into independent services for better scalability and resource allocation.

---

## 🎯 Core MediaPoster (Keep in main repo)

*The essential posting/scheduling functionality - this is what MediaPoster IS*

```
mediaposter-core/
├── services/
│   ├── post_scheduler.py
│   ├── blotato_service.py
│   ├── blotato_api.py
│   ├── publish_service.py
│   ├── publisher_service.py
│   ├── background_publisher.py
│   ├── multi_platform_publisher.py
│   ├── sleep_mode_service.py
│   ├── smart_scheduler.py
│   └── external_queue_manager.py
├── api/endpoints/
│   ├── external_scheduling.py
│   ├── schedule.py
│   └── posts.py
└── database/ (scheduled_posts, posted_content)
```

**Load:** Low-medium (mostly scheduling logic)

### Implementation Notes
- Keep FastAPI as the main framework
- This becomes the "API Gateway" for all other services
- All external clients (n8n, Shortcuts, etc.) talk to this
- Lightweight - should run on minimal resources
- Blotato integration stays here (it's the posting mechanism)

### Dependencies
- PostgreSQL/Supabase (scheduled_posts, posted_content tables)
- Redis for job queues to other services
- Event bus for async communication

---

## 📹 Media Processing Service (New repo: `mediaposter-media-processor`)

*Heavy CPU/GPU - video analysis, transcription, thumbnails*

```
mediaposter-media-processor/
├── services/
│   ├── video_analyzer.py
│   ├── video_analysis.py
│   ├── batch_video_analyzer.py
│   ├── frame_analyzer.py
│   ├── frame_sampler.py
│   ├── thumbnail_service.py
│   ├── thumbnail_generator.py
│   ├── transcription.py
│   ├── transcription_adapter.py
│   ├── whisper_transcriber.py
│   ├── audio_analyzer.py
│   ├── audio_service.py
│   ├── format_detector.py
│   ├── format_classifier.py
│   └── clip_extraction/
├── api/
│   ├── POST /analyze-video
│   ├── POST /transcribe
│   ├── POST /generate-thumbnail
│   └── POST /extract-clips
└── workers/
    └── celery or rq workers
```

**Load:** 🔴 HEAVY - offload to dedicated server

### Implementation Notes
- **Separate machine with GPU** for Whisper/video processing
- Use Celery or RQ for job queue processing
- Store results in shared Supabase
- Consider Modal.com for serverless GPU processing
- FFmpeg, OpenCV, Whisper are the heavy dependencies

### API Contract
```python
# Request: Analyze video
POST /api/v1/analyze
{
    "video_url": "supabase://bucket/path.mp4",
    "options": {
        "transcribe": true,
        "extract_frames": true,
        "generate_thumbnail": true,
        "detect_format": true
    }
}

# Response
{
    "job_id": "uuid",
    "status": "queued",
    "webhook_url": "https://mediaposter/webhook/analysis-complete"
}
```

### Communication Pattern
1. Core MediaPoster sends job to Redis queue
2. Media Processor picks up job, processes
3. Stores results in Supabase
4. Sends webhook notification OR publishes to event bus
5. Core MediaPoster updates UI/state

---

## 🤖 AI Services (New repo: `mediaposter-ai-services`)

*OpenAI/Groq API calls - rate limited, costly*

```
mediaposter-ai-services/
├── services/
│   ├── ai_client.py
│   ├── ai_content_analyzer.py
│   ├── ai_content_generator.py
│   ├── ai_content_service.py
│   ├── ai_recommendation_service.py
│   ├── ai_thumbnail_selector.py
│   ├── ai_title_generator.py
│   ├── content_generation_pipeline.py
│   ├── awareness_classifier.py
│   ├── fate_scorer.py
│   ├── sentiment_analyzer.py
│   └── vision_analyzer.py
├── api/
│   ├── POST /generate-content
│   ├── POST /analyze-sentiment
│   ├── POST /classify-awareness
│   ├── POST /generate-titles
│   └── POST /select-thumbnail
└── rate_limiting/
    └── token bucket per API key
```

**Load:** 🟡 Medium (API-bound, not CPU-bound)

### Implementation Notes
- Central place for ALL AI API keys
- Rate limiting per provider (OpenAI, Groq, Anthropic)
- Token usage tracking and cost monitoring
- Caching layer for repeated queries
- Could use LiteLLM for provider abstraction

### API Contract
```python
POST /api/v1/generate-titles
{
    "transcript": "...",
    "platform": "tiktok",
    "style": "engaging",
    "count": 5
}

# Response
{
    "titles": [...],
    "tokens_used": 450,
    "model": "gpt-4o-mini",
    "cached": false
}
```

### Cost Tracking
- Track tokens per request
- Daily/monthly budgets per feature
- Automatic fallback to cheaper models when budget exceeded

---

## 🎬 Video Generation Service (New repo: `mediaposter-video-gen`)

*Remotion, Sora, TTS - very heavy*

```
mediaposter-video-gen/
├── services/
│   ├── remotion/
│   ├── sora/
│   ├── sora_video_pipeline.py
│   ├── sora_daily/
│   ├── tts/
│   ├── voice/
│   ├── music/
│   ├── matting/
│   ├── video_renderer/
│   ├── video_generation/
│   ├── visuals/
│   └── character_generator.py
├── api/
│   ├── POST /render-video
│   ├── POST /generate-sora
│   ├── POST /text-to-speech
│   └── POST /clone-voice
└── templates/
    └── remotion compositions
```

**Load:** 🔴 EXTREMELY HEAVY - needs dedicated resources

### Implementation Notes
- **High-memory machine** (32GB+ RAM for Remotion)
- Node.js runtime for Remotion
- Python for Sora/TTS orchestration
- Consider Modal.com or Replicate for serverless
- Long-running jobs (minutes, not seconds)

### Job Queue Pattern
```python
# Jobs can take 2-10 minutes
POST /api/v1/render
{
    "template": "talking_head",
    "script": "...",
    "voice_id": "isaiah_clone",
    "music_id": "upbeat_01"
}

# Immediate response
{
    "job_id": "uuid",
    "estimated_time": 180,  # seconds
    "status_url": "/api/v1/jobs/uuid"
}

# Webhook on completion
POST https://mediaposter/webhook/render-complete
{
    "job_id": "uuid",
    "output_url": "supabase://renders/output.mp4",
    "duration": 145
}
```

---

## 🌐 Safari Automation Service (Existing repo: `Safari Automation`)

*macOS-specific, requires Safari instance*

```
Safari Automation/  # Already exists!
├── services/
│   ├── safari_automation_client.py
│   ├── safari_automation_orchestrator.py
│   ├── safari_event_listener.py
│   ├── safari_queue_manager.py
│   ├── safari_session_service.py
│   └── auto_comment_service.py
├── automation/
│   ├── safari_extension/
│   ├── safari_sora_scraper.py
│   └── applescript handlers
├── docs/
│   ├── selectors/  # Platform selector references
│   └── prds/       # Full control PRDs
└── Must run on Mac with Safari
```

**Load:** 🟡 Medium (browser-bound)

### Implementation Notes
- **Must run on macOS** with Safari
- AppleScript for browser control
- WebSocket connection to Core MediaPoster
- Session management for authenticated actions
- Already being split! Docs moved today.

### Communication Pattern
```python
# Core MediaPoster sends command
{
    "action": "post_to_tiktok",
    "video_path": "/path/to/video.mp4",
    "caption": "...",
    "session_id": "tiktok_isaiah"
}

# Safari Automation executes via AppleScript
# Reports back via WebSocket
{
    "status": "completed",
    "post_url": "https://tiktok.com/@user/video/123"
}
```

---

## 📊 Analytics Service (New repo: `mediaposter-analytics`)

*Data fetching, aggregation, trends*

```
mediaposter-analytics/
├── services/
│   ├── analytics_service.py
│   ├── analytics_aggregator.py
│   ├── social_analytics_service.py
│   ├── multi_platform_analytics_aggregator.py
│   ├── instagram_analytics.py
│   ├── tiktok_analytics_service.py
│   ├── youtube_analytics.py
│   ├── fetch_social_analytics.py
│   ├── realtime_metrics.py
│   ├── metrics_snapshot_service.py
│   ├── trend_intelligence/
│   └── predictive_analytics.py
├── jobs/
│   ├── hourly_metrics_fetch.py
│   ├── daily_aggregation.py
│   └── weekly_reports.py
└── api/
    ├── GET /metrics/{platform}/{account}
    ├── GET /trends
    └── GET /reports
```

**Load:** 🟡 Medium (API-bound)

### Implementation Notes
- Scheduled jobs (cron-based)
- RapidAPI for platform data
- Heavy Supabase writes
- Could run as serverless functions
- Cache layer for dashboard queries

### Scheduled Jobs
```
# Every hour
- Fetch post metrics for recent posts
- Update engagement scores

# Every 6 hours  
- Aggregate daily stats
- Compute trend velocities

# Daily
- Generate performance reports
- Update predictive models
```

---

## 💬 Engagement/CRM Service (New repo: `mediaposter-engagement`)

*DMs, comments, relationships - EverReach integration*

```
mediaposter-engagement/
├── services/
│   ├── inbox/
│   ├── dm_outreach/
│   ├── dm_fetcher_service.py
│   ├── dm_permission_service.py
│   ├── dm_warmth_system.py
│   ├── comment_fetcher_service.py
│   ├── relationship_ai.py
│   ├── relationship_crm.py
│   ├── engagement/
│   └── everreach/
├── api/
│   ├── GET /inbox
│   ├── POST /send-dm
│   ├── GET /relationships
│   └── POST /warm-lead
└── integrations/
    └── everreach_sync.py
```

**Load:** 🟢 Low-medium

### Implementation Notes
- Could be **separate product entirely**
- Integrates with EverReach CRM
- Permission-gated DM sending
- Lead scoring and warmth tracking
- Safari Automation for actual DM sending

---

## 🧪 Template/Experiment System (New repo: `mediaposter-experiments`)

*A/B testing, bandit allocation, leaderboards*

```
mediaposter-experiments/
├── services/
│   ├── template_leaderboard.py
│   ├── template_auto_forker.py
│   ├── template_retiree.py
│   ├── template_library.py
│   ├── bandit_allocator.py
│   ├── ab_testing.py
│   └── experiments_scheduler/
├── api/
│   ├── GET /templates
│   ├── POST /templates
│   ├── GET /allocations
│   └── GET /leaderboard
└── algorithms/
    ├── thompson_sampling.py
    └── ucb.py
```

**Load:** 🟢 Low

### Implementation Notes
- Background processing only
- Periodic recomputation (every 5-15 min)
- Shared database with Core
- Could stay in monolith initially

---

## Summary Table

| Service | Current Load | Split Priority | Communication | Deployment |
|---------|-------------|----------------|---------------|------------|
| **Core MediaPoster** | 🟢 Low | Keep | - | Any server |
| **Media Processor** | 🔴 Heavy | **HIGH** | Redis Queue | GPU server |
| **Video Generation** | 🔴 Extreme | **HIGH** | Redis Queue | High-mem server |
| **AI Services** | 🟡 Medium | Medium | HTTP API | Any server |
| **Safari Automation** | 🟡 Medium | Medium | WebSocket | macOS only |
| **Analytics** | 🟡 Medium | Low | Scheduled Jobs | Serverless |
| **Engagement/CRM** | 🟢 Low | Low | Event Bus | Any server |
| **Experiments** | 🟢 Low | Low | Shared DB | Any server |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    MEDIAPOSTER CORE                         │
│         (Scheduling, Publishing, API Gateway)               │
│              FastAPI @ port 5555                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬─────────────┐
        │ Redis Queue │ HTTP/WS     │ Event Bus   │
        ▼             ▼             ▼             ▼
┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐
│  Media    │  │   Video   │  │    AI     │  │  Safari   │
│ Processor │  │Generation │  │ Services  │  │Automation │
│  (GPU)    │  │  (Sora)   │  │ (OpenAI)  │  │  (macOS)  │
│ :6001     │  │   :6002   │  │   :6003   │  │   :6004   │
└───────────┘  └───────────┘  └───────────┘  └───────────┘
        │             │             │             │
        └─────────────┴─────────────┴─────────────┘
                      │
              ┌───────┴───────┐
              │   Supabase    │
              │   PostgreSQL  │
              │   @ :54322    │
              └───────────────┘
```

---

## Implementation Roadmap

### Phase 1: Extract Heavy Services (Priority: HIGH)
1. **Media Processor** - Move video analysis, transcription to separate service
2. **Video Generation** - Move Remotion/Sora to dedicated high-memory service
3. Set up Redis for job queues
4. Implement webhook callbacks

### Phase 2: Extract API Services (Priority: MEDIUM)
1. **AI Services** - Centralize all LLM calls
2. **Safari Automation** - Already in progress! Complete the split
3. Set up service discovery

### Phase 3: Extract Background Services (Priority: LOW)
1. **Analytics** - Move to scheduled serverless functions
2. **Engagement/CRM** - Consider as separate product
3. **Experiments** - Keep in monolith or extract if needed

---

## Shared Infrastructure

### Redis
```yaml
# docker-compose.yml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
  volumes:
    - redis_data:/data
```

### Service Registry
```python
# services.py
SERVICES = {
    "core": "http://localhost:5555",
    "media_processor": "http://localhost:6001", 
    "video_gen": "http://localhost:6002",
    "ai_services": "http://localhost:6003",
    "safari_automation": "http://localhost:6004",
}
```

### Health Checks
Each service exposes:
- `GET /health` - Basic health
- `GET /health/ready` - Ready to accept work
- `GET /health/live` - Still alive

---

## Benefits of Split

1. **Resource Isolation** - GPU-heavy work doesn't block scheduling
2. **Independent Scaling** - Scale video gen separately from posting
3. **Fault Isolation** - AI service down doesn't stop posts
4. **Deployment Flexibility** - Different machines for different needs
5. **Development Speed** - Smaller, focused codebases
6. **Cost Optimization** - Run GPU services only when needed

---

## Migration Strategy

1. **Strangler Fig Pattern** - Gradually route traffic to new services
2. **Feature Flags** - Toggle between monolith and microservice
3. **Shared Database** - All services use same Supabase initially
4. **Event Sourcing** - Log all state changes for debugging

```python
# In Core MediaPoster
if settings.USE_MEDIA_PROCESSOR_SERVICE:
    result = await media_processor_client.analyze(video_url)
else:
    result = await local_video_analyzer.analyze(video_url)
```
