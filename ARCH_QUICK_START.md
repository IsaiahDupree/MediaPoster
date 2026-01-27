# System Architecture Integration - Quick Start Guide

**TL;DR:** All ARCH features (ARCH-001 to ARCH-008) are implemented and tested. Here's how to use them.

## 🚀 Run the Full Pipeline (3 Methods)

### Method 1: Python API (Recommended)
```python
from services.master_orchestrator import get_orchestrator

# Initialize
orchestrator = get_orchestrator()
await orchestrator.start()

# Run full pipeline
result = await orchestrator.run_full_pipeline(
    theme="How to build viral AI content",
    num_parts=3,
    platforms=["tiktok", "instagram", "youtube"],
    schedule_tweets=True,
    tweets_per_day=12,
    offer_url="https://your-offer.com"
)

print(f"✅ Pipeline {result['id']} complete!")
```

### Method 2: REST API
```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/run \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "How to build viral AI content",
    "num_parts": 3,
    "publish_platforms": ["tiktok", "instagram"],
    "schedule_tweets": true,
    "tweets_per_day": 12
  }'
```

### Method 3: CLI
```bash
cd Backend
python -m services.master_orchestrator "Your video theme here"
```

---

## ⚙️ Configuration

### Required Environment Variables
```bash
OPENAI_API_KEY=sk-...      # For AI generation
BLOTATO_API_KEY=...        # For publishing
DATABASE_URL=postgresql://...  # For persistence
```

### Optional Settings
```bash
TWITTER_API_KEY=...        # For Twitter posting
GROQ_API_KEY=...          # Cheaper content analysis
REDIS_URL=redis://...      # Distributed EventBus
```

---

## 🧪 Testing

### Run All Tests
```bash
cd Backend
pytest tests/test_system_architecture_integration.py -v
```

### Run Demo
```bash
python demo_system_architecture.py
```

---

## 📊 Check Pipeline Status

### Get Single Pipeline
```python
status = orchestrator.get_pipeline_status(pipeline_id)
print(status)
```

### List All Pipelines
```python
pipelines = orchestrator.list_active_pipelines()
for p in pipelines:
    print(f"{p['id']}: {p['status']} - {p['theme']}")
```

### Get Metrics
```python
metrics = orchestrator.get_pipeline_metrics(days=30)
print(f"Success rate: {metrics['success_rate']}%")
```

---

## 🎯 What Each ARCH Feature Does

| Feature | What It Does |
|---------|-------------|
| **ARCH-001** | Orchestrates entire pipeline (Sora → Analyze → Publish → Tweet) |
| **ARCH-002** | Generates 3-part videos in batch with auto-stitching |
| **ARCH-003** | Auto-fills captions/hashtags from AI analysis |
| **ARCH-004** | Schedules tweets every 2 hours (12/day) |
| **ARCH-005** | Tracks offer clicks and conversions via UTM links |
| **ARCH-006** | Learns from analytics to optimize future content |
| **ARCH-007** | REST API endpoint for pipeline control |
| **ARCH-008** | Dashboard widget showing pipeline progress |

---

## ⏱️ Expected Timing

- **Sora Generation:** 10-15 minutes
- **Publishing:** 2-3 minutes (parallel to 22 accounts)
- **Tweet Scheduling:** 1-2 seconds
- **Total:** ~15-20 minutes end-to-end

---

## 🐛 Troubleshooting

### Pipeline Fails
```python
# Check error
status = orchestrator.get_pipeline_status(pipeline_id)
print(status.get('error'))

# Retry from database
pipeline = orchestrator.load_pipeline_from_db(pipeline_id)
```

### View Failed Events
```python
from services.event_bus import EventBus
bus = EventBus.get_instance()
failed = bus.get_dead_letter_queue(limit=10)
for event, error in failed:
    print(f"Event {event.id}: {error}")
```

### Replay Event
```python
bus.replay_event(event_id)
```

---

## 📁 Key Files

| File | Purpose |
|------|---------|
| `services/master_orchestrator.py` | Main orchestration logic |
| `automation/sora/pipeline.py` | Video generation |
| `services/twitter_campaign_service.py` | Tweet scheduling |
| `services/offer_tracker.py` | Conversion tracking |
| `api/endpoints/orchestrator.py` | REST API |
| `tests/test_system_architecture_integration.py` | Tests (17 passing) |

---

## ✅ Verification Checklist

- [x] All 8 ARCH features implemented
- [x] 17 integration tests passing
- [x] Database schema created
- [x] REST API endpoints working
- [x] Documentation complete
- [x] Demo scripts available
- [x] Ready for production

---

## 📚 Full Documentation

See `ARCH_IMPLEMENTATION_VERIFIED.md` for detailed feature specs and `ARCH_SESSION_SUMMARY.md` for complete architecture overview.

---

**Status:** PRODUCTION READY 🚀
