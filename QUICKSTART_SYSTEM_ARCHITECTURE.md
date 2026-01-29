# MediaPoster System Architecture - Quick Start Guide

**Last Updated:** January 29, 2026
**Status:** ✅ All ARCH-001 to ARCH-008 features operational and verified

This guide will help you quickly get started with the MediaPoster System Architecture (ARCH-001 to ARCH-008).

---

## What is System Architecture Integration?

The MediaPoster System Architecture Integration provides a **fully automated content pipeline** from video generation to multi-platform publishing:

```
Sora (1-3 part) → Stitch → Analyze → Auto-fill → Post to 22 Blotato accounts
                                                          ↓
Tweet every 2h → Track Engagement → Optimize → Drive Offer Traffic
```

### Features Implemented

| Feature | Description | Status |
|---------|-------------|--------|
| **ARCH-001** | Master Orchestrator Service | ✅ Complete |
| **ARCH-002** | 3-Part Sora Batch Coordination | ✅ Complete |
| **ARCH-003** | Content Analyzer → Publisher Integration | ✅ Complete |
| **ARCH-004** | Tweet Scheduler 2-Hour Interval | ✅ Complete |
| **ARCH-005** | Offer Traffic Tracking Service | ✅ Complete |
| **ARCH-006** | Analytics → AI Feedback Loop | ✅ Complete |
| **ARCH-007** | Unified Pipeline API Endpoint | ✅ Complete |
| **ARCH-008** | Pipeline Dashboard Widget | ✅ Complete |

---

## Quick Start in 3 Steps

### 1. Run the Demo Script

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster

# Full demo with dry-run (see what would happen)
python3 Backend/scripts/demo_full_arch_pipeline.py --dry-run

# Run with actual execution (requires Sora access)
python3 Backend/scripts/demo_full_arch_pipeline.py \
  --theme "AI automation revolutionizing content creation" \
  --num-parts 3 \
  --character "@isaiahdupree" \
  --platforms tiktok instagram youtube \
  --tweets-per-day 12 \
  --offer-url "https://blotato.com/offers/ai-automation"
```

### 2. Use the REST API

```bash
# Start the backend server
cd Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload
```

Then call the API:

```bash
# Start a new pipeline
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

# Get pipeline status
curl http://localhost:5555/api/orchestrator/pipeline/{pipeline_id}

# List all pipelines
curl http://localhost:5555/api/orchestrator/pipelines

# Get analytics (after 24h)
curl http://localhost:5555/api/orchestrator/pipeline/{pipeline_id}/analytics

# Get traffic metrics
curl http://localhost:5555/api/orchestrator/pipeline/{pipeline_id}/traffic
```

### 3. Use Python Directly

```python
import asyncio
from services.master_orchestrator import MasterOrchestrator, PipelineConfig

async def main():
    # Get orchestrator instance
    orchestrator = MasterOrchestrator.get_instance()
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

    # Get status
    status = orchestrator.get_pipeline_status(pipeline_id)
    print(f"Status: {status}")

    await orchestrator.stop()

asyncio.run(main())
```

---

## What Happens When You Run a Pipeline?

### Step-by-Step Workflow

1. **ARCH-001: Master Orchestrator** receives your request
   - Creates pipeline record in database
   - Initializes pipeline steps: Sora → Analyze → Publish → Tweet

2. **ARCH-002: Sora Pipeline** generates 3-part video
   - AI generates cohesive prompts for each part
   - Submits to Sora via Safari automation
   - Downloads completed videos
   - Removes watermarks
   - Stitches parts into single video

3. **Content Analysis** analyzes the stitched video
   - Generates platform-specific titles (TikTok, Instagram, YouTube)
   - Creates engaging description
   - Suggests relevant hashtags
   - Identifies hook and CTA

4. **ARCH-003: Publish Integrator** publishes to platforms
   - Auto-fills titles, descriptions, hashtags from AI analysis
   - Publishes to 22 Blotato accounts across platforms
   - Tracks each publish job status

5. **ARCH-004: Twitter Campaign** schedules tweets
   - Generates 12 tweets/day (every 2 hours)
   - Uses 5-stage awareness model (Unaware → Most Aware)
   - Rotates content types (Hook, Authority, Story, Emotional, CTA)

6. **ARCH-005: Offer Traffic Tracker** tracks conversions
   - Generates UTM-tracked links
   - Tracks clicks per platform
   - Monitors conversions and revenue

7. **ARCH-006: Analytics Feedback Loop** optimizes future content
   - Analyzes performance after 24 hours
   - AI identifies what worked and what didn't
   - Generates actionable optimization suggestions
   - Suggests next content ideas

8. **Pipeline Complete!** 🎉
   - Video published to all platforms
   - Tweets scheduled for next 24 hours
   - Traffic tracking active
   - Analytics ready in 24h

---

## Key Endpoints

### Pipeline Management
- `POST /api/orchestrator/pipeline/start` - Start new pipeline
- `GET /api/orchestrator/pipeline/:id` - Get pipeline status
- `GET /api/orchestrator/pipelines` - List all pipelines
- `GET /api/orchestrator/health` - Health check

### Analytics (ARCH-006)
- `GET /api/orchestrator/pipeline/:id/analytics` - Performance analysis
- `GET /api/orchestrator/analytics/top-themes` - Best performing themes
- `GET /api/orchestrator/analytics/historical` - Historical insights

### Traffic Tracking (ARCH-005)
- `GET /api/orchestrator/pipeline/:id/traffic` - Traffic report
- `GET /api/orchestrator/traffic/platform-performance` - Platform metrics
- `GET /api/orchestrator/traffic/top-campaigns` - Top campaigns

---

## Example Output

When you run a pipeline, you'll see real-time event updates:

```
================================================================================
🏗️  SYSTEM ARCHITECTURE INTEGRATION DEMO
================================================================================
Theme: AI automation revolutionizing content creation
Parts: 3
Character: @isaiahdupree
Platforms: tiktok, instagram, youtube
Tweets: 12/day (every 120 min)
Offer: https://blotato.com/offers/ai-automation
================================================================================

10:00:00 | INFO     | 🚀 [PIPELINE STARTED] AI automation revolutionizing content creation
10:00:01 | INFO     | 🎬 [SORA] Starting 3-part generation...
10:08:45 | SUCCESS  | ✅ [SORA] Completed: 3/3 parts
10:08:45 | INFO     |    Video: /output/sora_pipeline/multipart_pipeline-abc123_final.mp4
10:08:46 | INFO     | 📤 [PUBLISH] Requested for tiktok
10:08:47 | INFO     | 📤 [PUBLISH] Requested for instagram
10:08:48 | INFO     | 📤 [PUBLISH] Requested for youtube
10:09:20 | SUCCESS  | ✅ [PUBLISH] Completed for tiktok
10:09:22 | SUCCESS  | ✅ [PUBLISH] Completed for instagram
10:09:25 | SUCCESS  | ✅ [PUBLISH] Completed for youtube
10:09:26 | SUCCESS  | ✅ [TWITTER] Scheduled 12 tweets
10:09:27 | SUCCESS  | 🎉 [PIPELINE COMPLETED] AI automation revolutionizing content creation

================================================================================
📊 PIPELINE RESULTS
================================================================================

Pipeline ID: pipeline-abc123
Status: COMPLETED
Started: 2026-01-29T10:00:00Z
Completed: 2026-01-29T10:09:27Z

🎬 Sora Generation:
   Video: /output/sora_pipeline/multipart_pipeline-abc123_final.mp4
   Title (TikTok): AI Automation Changes Everything 🤖
   Hashtags: ai, automation, contentcreation, viral, fyp

📤 Publishing:
   tiktok: completed
   instagram: completed
   youtube: completed

🐦 Twitter Campaign:
   Tweets scheduled: 12

🔗 Offer Tracking:
   Offer URL: https://blotato.com/offers/ai-automation
   Traffic endpoint: /api/orchestrator/pipeline/pipeline-abc123/traffic

================================================================================
```

---

## Testing

Run integration tests:

```bash
cd Backend
pytest tests/test_system_architecture_integration.py -v
```

Tests verify all ARCH-001 to ARCH-008 features are working correctly.

---

## Troubleshooting

### Pipeline stuck in "generating_video"
- Check Sora Safari automation is running
- Verify Sora is logged in
- Check `Backend/automation/sora/` logs

### Publishing failed
- Verify Blotato API credentials in `.env`
- Check account configuration in `Backend/config/blotato_accounts.py`
- Check platform-specific API limits

### Database errors
- Ensure PostgreSQL is running: `supabase status`
- Run migrations: `supabase db reset` (WARNING: destroys data)
- Check DATABASE_URL in `.env`

### Event bus not working
- Verify EventBus singleton is initialized
- Check event topic subscriptions in logs
- Use `/api/orchestrator/pipeline/:id/events` to debug events

---

## Next Steps

1. **Read Full Documentation:** `ARCH_SYSTEM_COMPLETE.md`
2. **Review Source Code:**
   - `Backend/services/master_orchestrator.py` (ARCH-001)
   - `Backend/automation/sora/pipeline.py` (ARCH-002)
   - `Backend/services/publish_integrator.py` (ARCH-003)
   - `Backend/api/endpoints/orchestrator.py` (ARCH-007)
3. **Run Tests:** `pytest tests/test_system_architecture_integration.py -v`
4. **Build Dashboard:** Integrate ARCH-008 frontend widget

---

## Support

For questions or issues:
1. Check logs in `Backend/logs/`
2. Review event history: `/api/orchestrator/pipeline/:id/events`
3. Check integration tests for examples
4. Review PRD: `docs/PRD_SYSTEM_ARCHITECTURE_INTEGRATION.md`

---

**Status:** ✅ All features operational and tested
**Last Updated:** January 29, 2026
