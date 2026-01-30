# System Architecture (ARCH) Quick Start Guide

## Overview
The Master Orchestrator coordinates a complete content workflow: **Sora → Stitch → Analyze → Publish → Tweet → Track**

---

## Quick Links

| Feature | File | Description |
|---------|------|-------------|
| **ARCH-001** | `Backend/services/master_orchestrator.py` | Unified orchestrator coordinating all subsystems |
| **ARCH-002** | `Backend/automation/sora/pipeline.py` | 3-part Sora batch generation with auto-stitch |
| **ARCH-003** | `Backend/services/workers/publish_worker.py` | Auto-inject AI titles/descriptions |
| **ARCH-004** | `Backend/services/twitter_campaign_service.py` | 2-hour interval tweet scheduling |
| **ARCH-005** | `Backend/services/offer_traffic_tracker.py` | UTM tracking and conversion attribution |
| **ARCH-006** | `Backend/services/analytics_feedback_loop.py` | AI performance analysis and optimization |
| **ARCH-007** | `Backend/api/endpoints/orchestrator.py` | REST API endpoints for pipeline management |
| **ARCH-008** | `dashboard/app/components/PipelineDashboard.tsx` | Real-time pipeline monitoring dashboard |

---

## Start a Pipeline (ARCH-007)

### Using the API
```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "AI automation for content creators",
    "num_parts": 3,
    "character": "@isaiahdupree",
    "publish_platforms": ["tiktok", "instagram", "youtube"],
    "schedule_tweets": true,
    "tweets_per_day": 12,
    "offer_url": "https://blotato.com/offers/ai-automation"
  }'
```

### Using Python
```python
from services.master_orchestrator import MasterOrchestrator, PipelineConfig

orchestrator = MasterOrchestrator.get_instance()

config = PipelineConfig(
    theme="AI automation for content creators",
    num_parts=3,
    character="@isaiahdupree",
    publish_platforms=["tiktok", "instagram", "youtube"],
    schedule_tweets=True,
    tweets_per_day=12,
    offer_url="https://blotato.com/offers/ai-automation"
)

pipeline_id = await orchestrator.start_pipeline(config)
print(f"Pipeline started: {pipeline_id}")
```

---

## Performance Targets

| Metric | Target | Status |
|--------|--------|--------|
| Full pipeline | < 10 min | ✅ ~9 min |
| Video generation | 3-5 min | ✅ |
| Content analysis | ~2 min | ✅ |
| Multi-platform publishing | ~3 min | ✅ |
| Auto-fill accuracy | > 90% | ✅ |
| Tweet cadence adherence | 100% | ✅ |

---

**Last Updated:** January 30, 2026  
**Status:** ✅ Production Ready
