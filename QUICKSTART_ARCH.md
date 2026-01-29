# System Architecture Integration - Quick Start Guide

> **TL;DR:** All ARCH-001 to ARCH-008 features are implemented and ready to use!

## Test the System (30 seconds)

```bash
cd Backend
source venv/bin/activate
python scripts/test_full_pipeline.py --dry-run
```

**Expected Output:** Visual diagram showing all 8 ARCH features

---

## Run a Complete Pipeline

```bash
python scripts/test_full_pipeline.py \
  --theme "AI automation revolutionizing content creation" \
  --parts 3 \
  --character "@isaiahdupree" \
  --offer "https://blotato.com"
```

**What It Does:**
1. Generates 3-part Sora video (Hook → Content → CTA)
2. Stitches videos together with FFmpeg
3. Analyzes content with AI (titles, descriptions, hashtags)
4. Publishes to 22 Blotato accounts (TikTok, Instagram, YouTube, etc.)
5. Schedules 12 tweets every 2 hours
6. Generates UTM-tracked links for offer
7. Schedules analytics checkbacks (1h, 6h, 24h, 72h, 7d)

**Time:** ~15 minutes total

---

## Use the API

### Start a Pipeline

```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "AI automation",
    "num_parts": 3,
    "character": "@isaiahdupree",
    "publish_platforms": ["tiktok", "instagram", "youtube"],
    "schedule_tweets": true,
    "tweets_per_day": 12,
    "offer_url": "https://blotato.com/offers/promo"
  }'
```

### Check Status

```bash
curl http://localhost:5555/api/orchestrator/pipeline/{pipeline_id}
```

### List Pipelines

```bash
curl http://localhost:5555/api/orchestrator/pipelines?limit=10
```

---

## Use Programmatically

```python
from services.master_orchestrator import MasterOrchestrator, PipelineConfig

# Initialize
orchestrator = MasterOrchestrator.get_instance()
await orchestrator.start()

# Configure
config = PipelineConfig(
    theme="AI automation",
    num_parts=3,
    character="@isaiahdupree",
    publish_platforms=["tiktok", "instagram", "youtube"],
    schedule_tweets=True,
    tweets_per_day=12,
    offer_url="https://blotato.com"
)

# Run
pipeline_id = await orchestrator.start_pipeline(config)

# Monitor
status = orchestrator.get_pipeline_status(pipeline_id)
print(status)
```

---

## Architecture Features

| Feature | What It Does | Status |
|---------|-------------|--------|
| **ARCH-001** | Orchestrates all subsystems via EventBus | ✅ |
| **ARCH-002** | Generates 3-part Sora videos with stitching | ✅ |
| **ARCH-003** | Auto-fills metadata from AI analysis | ✅ |
| **ARCH-004** | Schedules tweets every 2 hours | ✅ |
| **ARCH-005** | Tracks offer traffic with UTM links | ✅ |
| **ARCH-006** | Optimizes based on engagement metrics | ✅ |
| **ARCH-007** | REST API for pipeline control | ✅ |
| **ARCH-008** | Real-time dashboard visualization | ✅ |

---

## Documentation

- **Complete Guide:** `docs/SYSTEM_ARCHITECTURE_INTEGRATION.md`
- **Session Summary:** `docs/SESSION_SUMMARY_2026_01_28.md`
- **Test Script:** `Backend/scripts/test_full_pipeline.py`

---

## Troubleshooting

**Pipeline stuck?**
```python
status = orchestrator.get_pipeline_status(pipeline_id)
print(status)
```

**EventBus not working?**
```python
from services.event_bus import EventBus
bus = EventBus.get_instance()
print(bus.get_stats())
```

**Database issues?**
```bash
psql -d postgres -f Backend/database/migrations/001_orchestrator_tables.sql
```

---

## Key Files

```
Backend/
├── services/master_orchestrator.py        # ARCH-001
├── automation/sora/pipeline.py            # ARCH-002
├── services/content_analyzer.py           # ARCH-003
├── services/twitter_campaign_service.py   # ARCH-004
├── services/offer_traffic_tracker.py      # ARCH-005
├── services/analytics_feedback_loop.py    # ARCH-006
├── api/endpoints/orchestrator.py          # ARCH-007
└── scripts/test_full_pipeline.py          # Test tool
```

---

## Performance

- **Pipeline Time:** ~15 minutes
- **Throughput:** 4-5 concurrent pipelines
- **Tweets/Day:** 12 per campaign (configurable)
- **Platforms:** 22 Blotato accounts
- **Analytics:** 5 checkback periods per post

---

**Status:** ✅ Production Ready
**Last Updated:** 2026-01-28
