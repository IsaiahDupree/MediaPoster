# ARCH Implementation Quick Reference

## Features Implemented

### ARCH-001: Master Orchestrator Service
**File:** `Backend/services/master_orchestrator.py`
**Main Class:** `MasterOrchestrator`
**Key Methods:**
- `start_pipeline(config: PipelineConfig) -> pipeline_id`
- `get_pipeline_status(pipeline_id: str) -> status_dict`
- `list_pipelines(status: str = None, limit: int = 10) -> List[Dict]`
- `_extract_platform_metadata(analysis: Dict) -> Dict[str, Dict]`

**Event Subscriptions:**
- `SORA_BATCH_COMPLETED` → `_handle_sora_batch_completed()`
- `SORA_BATCH_FAILED` → `_handle_sora_batch_failed()`
- `PUBLISH_COMPLETED` → `_handle_publish_completed()`
- `PUBLISH_FAILED` → `_handle_publish_failed()`
- `TWITTER_CAMPAIGN_SCHEDULED` → `_handle_twitter_scheduled()`

**Database Tables:**
- `orchestrator_pipelines` - Pipeline state and config
- `orchestrator_pipeline_steps` - Step-by-step tracking

---

### ARCH-002: 3-Part Sora Batch Coordination
**File:** `Backend/automation/sora/pipeline.py`
**Main Class:** `SoraPipeline`
**Key Method:** `generate_multi_part(theme, num_parts=3, character=None, ...) -> job_dict`

**Workflow:**
1. Generate part prompts via AI (GPT-4o-mini)
2. Generate 3 videos (respects Sora's 3-concurrent limit)
3. Download and clean videos (remove watermarks)
4. Stitch parts together
5. Analyze content for metadata

**EventBus Topics:**
- `SORA_BATCH_REQUESTED` - Incoming request
- `SORA_BATCH_STARTED` - Processing started
- `SORA_BATCH_COMPLETED` - All videos done (emits analysis)
- `SORA_BATCH_FAILED` - Generation failed

**Response Example:**
```json
{
  "id": "pipeline-123",
  "status": "completed",
  "successful_parts": 3,
  "stitched_video": "/path/to/final.mp4",
  "analysis": {
    "detected_hook": "Check this out...",
    "viral_score": 87,
    "hashtags": ["viral", "trending"],
    "title_tiktok": "...",
    "title_instagram": "...",
    "title_youtube": "..."
  }
}
```

---

### ARCH-003: Content Analyzer → Publisher Integration
**Files:**
- `Backend/services/workers/publish_worker.py` (lines 172-210)
- `Backend/services/master_orchestrator.py` (method: `_extract_platform_metadata`)

**Key Feature:** Auto-fill titles, descriptions, hashtags from Sora analysis

**Data Flow:**
```
SORA_BATCH_COMPLETED (with analysis)
    ↓
_extract_platform_metadata() → platform-specific metadata
    ↓
PUBLISH_REQUESTED (with title, description, hashtags, hook)
    ↓
PublishWorker._run_publish_pipeline()
    ↓
Uses analysis to build captions
```

**Example Payload:**
```json
{
  "media_id": "video_123",
  "platform": "tiktok",
  "video_path": "/path/to/video.mp4",
  "analysis": {
    "detected_hook": "Amazing discovery!",
    "viral_score": 82,
    "hashtags": ["amazing", "discovery"]
  },
  "title": "Check out this discovery",
  "description": "You won't believe what happened...",
  "hashtags": ["amazing", "discovery", "fyp"],
  "hook": "Amazing discovery!"
}
```

---

## API Endpoints (ARCH-007)

**File:** `Backend/api/endpoints/orchestrator.py`

### Start Pipeline
```
POST /api/orchestrator/pipeline/start
Content-Type: application/json

{
  "theme": "AI automation",
  "num_parts": 3,
  "character": "@isaiahdupree",
  "publish_platforms": ["tiktok", "instagram", "youtube"],
  "schedule_tweets": true,
  "tweets_per_day": 12,
  "offer_url": "https://example.com/ai"
}
```

Response:
```json
{
  "success": true,
  "pipeline_id": "pipeline-a1b2c3d4",
  "status": "initializing",
  "message": "Pipeline started: AI automation"
}
```

### Get Pipeline Status
```
GET /api/orchestrator/pipeline/pipeline-a1b2c3d4
```

### List Pipelines
```
GET /api/orchestrator/pipelines?status=completed&limit=10
```

### Get Pipeline Events
```
GET /api/orchestrator/pipeline/pipeline-a1b2c3d4/events
```

---

## EventBus Topics

**Core Orchestrator Topics:**
- `orchestrator.pipeline.started`
- `orchestrator.pipeline.completed`

**Sora Topics:**
- `sora.batch.requested`
- `sora.batch.started`
- `sora.batch.progress`
- `sora.batch.completed`
- `sora.batch.failed`

**Publishing Topics:**
- `publish.requested`
- `publish.started`
- `publish.uploading`
- `publish.upload.completed`
- `publish.submitted`
- `publish.polling`
- `publish.completed`
- `publish.failed`

**All topics defined in:** `Backend/services/event_bus/topics.py`

---

## Testing

**Verification Script:**
```bash
cd Backend
python3 tests/verify_arch_implementation.py
```

**Integration Tests:**
```bash
python3 -m pytest tests/integration/test_system_architecture_integration.py -v
```

**Test Files:**
- `tests/integration/test_system_architecture_integration.py`
- `tests/integration/test_arch_pipeline_integration.py`
- `tests/integration/test_arch_complete_integration.py`
- `tests/verify_arch_implementation.py`

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     REST API Request                         │
│         POST /api/orchestrator/pipeline/start                │
└────────────────────────┬────────────────────────────────────┘
                         │
                         v
        ┌────────────────────────────────┐
        │   MasterOrchestrator (ARCH-001)│
        │  - start_pipeline()            │
        │  - event subscriptions         │
        │  - database persistence        │
        └────────────┬───────────────────┘
                     │
                     v
            emit: SORA_BATCH_REQUESTED
                     │
                     v
        ┌────────────────────────────────┐
        │    SoraPipeline (ARCH-002)     │
        │  - generate_multi_part()       │
        │  - 3-part video generation     │
        │  - auto-stitch & analysis      │
        └────────────┬───────────────────┘
                     │
                     v
            emit: SORA_BATCH_COMPLETED
                (with analysis)
                     │
        ┌────────────v───────────────────┐
        │ Extract Platform Metadata      │
        │       (ARCH-003)               │
        │ - Extract titles/descriptions  │
        │ - Platform-specific format     │
        └────────────┬───────────────────┘
                     │
                     v
            emit: PUBLISH_REQUESTED
                (per platform)
                     │
                     v
        ┌────────────────────────────────┐
        │    PublishWorker (ARCH-003)    │
        │  - Uses pre-computed analysis  │
        │  - Upload & submit to platform │
        │  - Poll for URL                │
        └────────────┬───────────────────┘
                     │
                     v
            emit: PUBLISH_COMPLETED
                (per platform)
                     │
                     v
        ┌────────────────────────────────┐
        │  TwitterCampaignService        │
        │  - Schedule 12 tweets/day      │
        │  - 2-hour intervals            │
        │  - Offer URL rotation          │
        └────────────┬───────────────────┘
                     │
                     v
            emit: TWITTER_CAMPAIGN_SCHEDULED
                     │
                     v
        ┌────────────────────────────────┐
        │  Pipeline Complete ✅          │
        │  emit: ORCHESTRATOR_PIPELINE.. │
        │        COMPLETED               │
        └────────────────────────────────┘
```

---

## Common Tasks

### Start a Pipeline Programmatically
```python
from services.master_orchestrator import MasterOrchestrator, PipelineConfig

orchestrator = MasterOrchestrator.get_instance()

config = PipelineConfig(
    theme="AI automation",
    num_parts=3,
    character="isaiahdupree",
    publish_platforms=["tiktok", "instagram"],
    schedule_tweets=True,
    tweets_per_day=12
)

pipeline_id = await orchestrator.start_pipeline(config)
print(f"Pipeline started: {pipeline_id}")
```

### Check Pipeline Status
```python
status = orchestrator.get_pipeline_status(pipeline_id)
print(f"Status: {status['status']}")
print(f"Progress: {status.get('current_step', 'unknown')}")
```

### Listen to Pipeline Events
```python
from services.event_bus import EventBus, Topics

bus = EventBus.get_instance()

async def on_pipeline_complete(event):
    print(f"Pipeline completed: {event.payload}")

bus.subscribe(Topics.ORCHESTRATOR_PIPELINE_COMPLETED, on_pipeline_complete)
```

---

## Troubleshooting

**Pipeline Stuck:**
- Check EventBus event history: `GET /api/orchestrator/pipeline/{id}/events`
- Verify worker processes are running
- Check database for pipeline_steps status

**Analysis Missing:**
- ARCH-003 requires `payload.get("analysis")` to be present
- Fallback: PublishWorker will auto-generate if `auto_generate_metadata=True`

**Publishing Failed:**
- Check Blotato service connectivity
- Verify account_id is valid (22 accounts configured)
- Check for duplicate content (DuplicateDetector enabled)

---

## References

- **PRD:** `Backend/docs/PRD_SYSTEM_ARCHITECTURE_INTEGRATION.md`
- **Summary:** `ARCH_IMPLEMENTATION_SUMMARY.md`
- **Verification:** Run `tests/verify_arch_implementation.py`
- **Feature List:** `feature_list.json` (ARCH-001 through ARCH-008)
