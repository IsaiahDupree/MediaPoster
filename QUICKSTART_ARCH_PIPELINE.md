# Quick Start: System Architecture Integration

**Last Updated:** January 29, 2026
**Status:** ✅ Production Ready

This guide shows you how to use the newly implemented System Architecture Integration (ARCH-001 to ARCH-008) to run complete end-to-end content pipelines.

---

## What You Can Do Now

With the System Architecture Integration complete, you can:

1. **Generate multi-part AI videos** with Sora (1-3 parts automatically stitched)
2. **Analyze content** with AI-powered insights (hooks, viral score, hashtags)
3. **Publish to 22 accounts** across 9 platforms (TikTok, Instagram, YouTube, etc.)
4. **Schedule tweets** every 2 hours with awareness-based content
5. **Track offer traffic** from social posts to conversion
6. **Get AI optimization suggestions** based on performance data

All of this happens **automatically** through a single API call or Python function.

---

## Prerequisites

### 1. Start the Backend

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload
```

### 2. Verify System is Ready

```bash
python scripts/verify_arch_implementation.py
```

You should see:
```
🎉 All verifications passed!
✅ System Architecture Integration is fully operational
```

---

## Method 1: Using the REST API

### Start a Pipeline

```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "AI automation revolutionizing content creation",
    "num_parts": 3,
    "character": "@isaiahdupree",
    "publish_platforms": ["tiktok", "instagram", "youtube"],
    "schedule_tweets": true,
    "tweets_per_day": 12,
    "offer_url": "https://blotato.com/offers/ai-automation"
  }'
```

**Response:**
```json
{
  "success": true,
  "pipeline_id": "pipeline-a7f3c2d1",
  "status": "initializing",
  "message": "Pipeline started: AI automation revolutionizing content creation"
}
```

### Check Pipeline Status

```bash
curl http://localhost:5555/api/orchestrator/pipeline/pipeline-a7f3c2d1
```

**Response:**
```json
{
  "success": true,
  "pipeline_id": "pipeline-a7f3c2d1",
  "status": "publishing",
  "current_step": "publishing",
  "started_at": "2026-01-29T00:00:00Z",
  "outputs": {
    "sora": {
      "stitched_video": "/output/sora_pipeline/multipart_a7f3c2d1_final.mp4",
      "analysis": {
        "detected_hook": "AI is changing everything",
        "viral_score": 82,
        "hashtags": ["AI", "automation"]
      }
    },
    "publish_jobs": [
      {"platform": "tiktok", "status": "completed"},
      {"platform": "instagram", "status": "completed"},
      {"platform": "youtube", "status": "uploading"}
    ]
  }
}
```

### List All Pipelines

```bash
curl http://localhost:5555/api/orchestrator/pipelines?limit=10
```

### Get Analytics for a Pipeline

```bash
curl http://localhost:5555/api/orchestrator/pipeline/pipeline-a7f3c2d1/analytics
```

### Get Traffic Report

```bash
curl http://localhost:5555/api/orchestrator/pipeline/pipeline-a7f3c2d1/traffic
```

---

## Method 2: Using Python

### Start a Pipeline Programmatically

```python
import asyncio
from services.master_orchestrator import MasterOrchestrator, PipelineConfig

async def run_pipeline():
    # Get orchestrator instance
    orchestrator = MasterOrchestrator.get_instance()

    # Start orchestrator
    await orchestrator.start()

    # Create pipeline config
    config = PipelineConfig(
        theme="AI automation revolutionizing content creation",
        num_parts=3,
        character="@isaiahdupree",
        publish_platforms=["tiktok", "instagram", "youtube"],
        schedule_tweets=True,
        tweets_per_day=12,
        offer_url="https://blotato.com/offers/ai-automation"
    )

    # Start pipeline
    pipeline_id = await orchestrator.start_pipeline(config)
    print(f"Pipeline started: {pipeline_id}")

    # Monitor status
    while True:
        status = orchestrator.get_pipeline_status(pipeline_id)
        print(f"Status: {status['status']}")

        if status['status'] in ['completed', 'failed']:
            break

        await asyncio.sleep(10)

    # Cleanup
    await orchestrator.stop()

    return pipeline_id

# Run it
pipeline_id = asyncio.run(run_pipeline())
```

### Alternative: Quick Start Method

```python
import asyncio
from services.master_orchestrator import MasterOrchestrator

async def quick_pipeline():
    orchestrator = MasterOrchestrator.get_instance()
    await orchestrator.start()

    # Simple one-liner
    pipeline_id = await orchestrator.run_full_pipeline(
        theme="AI automation revolutionizing content creation",
        num_parts=3,
        character="@isaiahdupree",
        publish_platforms=["tiktok", "instagram", "youtube"],
        schedule_tweets=True,
        tweets_per_day=12,
        offer_url="https://blotato.com/offers/ai-automation"
    )

    print(f"Pipeline {pipeline_id} started!")
    await orchestrator.stop()
    return pipeline_id

pipeline_id = asyncio.run(quick_pipeline())
```

---

## What Happens During a Pipeline?

### Step 1: Sora Video Generation (ARCH-002)
- AI generates prompts for 3-part video series
- Each part is generated via Safari automation
- Videos are downloaded and watermarks removed
- Parts are stitched into one final video
- **Duration:** ~10-15 minutes

### Step 2: Content Analysis (ARCH-003)
- AI analyzes the final video
- Extracts hooks, tone, viral score
- Generates titles, descriptions, hashtags
- Creates platform-specific captions
- **Duration:** ~30 seconds

### Step 3: Multi-Platform Publishing (ARCH-003)
- Video uploaded to cloud storage
- Published to TikTok, Instagram, YouTube via Blotato
- Waits for platform URLs
- Duplicate detection prevents re-posting
- **Duration:** ~2-5 minutes per platform

### Step 4: Twitter Campaign (ARCH-004)
- Generates 12 tweets (or custom count)
- Schedules tweets every 2 hours
- Uses 5 awareness stages
- Includes offer URL if provided
- **Duration:** ~1 minute

### Step 5: Offer Tracking (ARCH-005)
- Creates tracked links with UTM parameters
- Registers campaign in database
- Ready to track clicks and conversions
- **Duration:** Instant

### Step 6: Analytics Feedback (ARCH-006)
- Waits 24 hours for data collection
- AI analyzes performance metrics
- Generates optimization suggestions
- Learns from patterns
- **Duration:** Runs asynchronously

**Total Pipeline Time:** ~15-25 minutes (excluding analytics wait)

---

## Advanced Features

### Custom Platform Selection

```python
# Only publish to TikTok and Instagram
pipeline_id = await orchestrator.run_full_pipeline(
    theme="Quick content tip",
    num_parts=1,  # Single video
    publish_platforms=["tiktok", "instagram"],
    schedule_tweets=False  # Skip Twitter campaign
)
```

### Skip Tweet Scheduling

```python
# Generate and publish video only, no tweets
pipeline_id = await orchestrator.run_full_pipeline(
    theme="Product demo",
    num_parts=2,
    schedule_tweets=False
)
```

### Track Offer Performance

```python
# Include offer URL for traffic tracking
pipeline_id = await orchestrator.run_full_pipeline(
    theme="Special offer announcement",
    num_parts=1,
    offer_url="https://mysite.com/offers/special",
    tweets_per_day=24  # Tweet every hour
)
```

### Use Character Presets

```python
# Use specific Sora character
pipeline_id = await orchestrator.run_full_pipeline(
    theme="Tech tutorial",
    character="@isaiahdupree",  # Consistent character across parts
    num_parts=3
)
```

---

## Monitoring & Analytics

### Real-Time Progress

The pipeline emits events you can subscribe to:

```python
from services.event_bus import EventBus, Topics

async def monitor_pipeline(pipeline_id):
    bus = EventBus.get_instance()

    async def on_sora_complete(event):
        if event.payload.get("pipeline_id") == pipeline_id:
            print("✅ Sora generation complete!")

    async def on_publish_complete(event):
        if event.payload.get("pipeline_id") == pipeline_id:
            platform = event.payload.get("platform")
            print(f"✅ Published to {platform}")

    bus.subscribe(Topics.SORA_BATCH_COMPLETED, on_sora_complete)
    bus.subscribe(Topics.PUBLISH_COMPLETED, on_publish_complete)
```

### Get Analytics After 24 Hours

```python
from services.analytics_feedback_loop import AnalyticsFeedbackLoop

async def get_analytics(pipeline_id):
    feedback = AnalyticsFeedbackLoop.get_instance()
    analysis = await feedback.analyze_pipeline_performance(pipeline_id)

    print(f"Performance Rating: {analysis['rating']}")
    print(f"AI Insights: {analysis['insights']}")
    print(f"Suggestions: {analysis['suggestions']}")
```

### Get Traffic Report

```python
from services.offer_traffic_tracker import OfferTrafficTracker

def get_traffic(pipeline_id):
    tracker = OfferTrafficTracker.get_instance()
    report = tracker.get_pipeline_traffic_report(pipeline_id)

    print(f"Total Clicks: {report['total_clicks']}")
    print(f"Conversions: {report['total_conversions']}")
    print(f"Revenue: ${report['total_revenue_usd']}")
    print(f"Conversion Rate: {report['conversion_rate']}%")
```

---

## Troubleshooting

### Pipeline Stuck?

Check the status:
```bash
curl http://localhost:5555/api/orchestrator/pipeline/:id
```

If status is "failed", check the error:
```bash
curl http://localhost:5555/api/orchestrator/pipeline/:id | jq '.error'
```

### View Event History

```bash
curl http://localhost:5555/api/orchestrator/pipeline/:id/events
```

### Database Connection Issues

Verify database is running:
```bash
python scripts/verify_arch_implementation.py
```

Should show all tables created.

### Safari Automation Issues

Make sure Safari is accessible:
```bash
osascript -e 'tell application "Safari" to activate'
```

---

## API Reference

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/orchestrator/pipeline/start` | Start new pipeline |
| GET | `/api/orchestrator/pipeline/:id` | Get status |
| GET | `/api/orchestrator/pipelines` | List pipelines |
| GET | `/api/orchestrator/pipeline/:id/events` | Event history |
| GET | `/api/orchestrator/health` | Health check |

### Analytics Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orchestrator/pipeline/:id/analytics` | AI analytics |
| GET | `/api/orchestrator/analytics/top-themes` | Best themes |
| GET | `/api/orchestrator/analytics/historical` | Past insights |

### Traffic Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orchestrator/pipeline/:id/traffic` | Traffic report |
| GET | `/api/orchestrator/traffic/platform-performance` | By platform |
| GET | `/api/orchestrator/traffic/top-campaigns` | Top campaigns |

---

## Next Steps

1. **Run your first pipeline** using the examples above
2. **Monitor progress** via API or dashboard
3. **Analyze results** after 24 hours
4. **Optimize** based on AI suggestions
5. **Scale up** by running multiple pipelines

---

## Support

- **Documentation:** `docs/ARCH_IMPLEMENTATION_COMPLETE.md`
- **API Spec:** `api/endpoints/orchestrator.py`
- **Tests:** `tests/test_system_architecture_integration.py`
- **Verification:** `scripts/verify_arch_implementation.py`

---

**System Status:** ✅ Production Ready
**Last Verified:** January 29, 2026
**Features Implemented:** ARCH-001 to ARCH-008 (100%)
