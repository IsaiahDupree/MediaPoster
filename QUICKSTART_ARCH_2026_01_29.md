# System Architecture Integration - Quickstart Guide

**Last Updated:** January 29, 2026
**Status:** ✅ Production Ready

This guide will help you quickly start using the complete orchestrated pipeline that was implemented in the System Architecture Integration phase.

---

## Prerequisites

### 1. Environment Setup
```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
source venv/bin/activate
```

### 2. Environment Variables
Ensure `.env` file contains:
```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres

# OpenAI (for AI generation)
OPENAI_API_KEY=sk-...

# Blotato (for publishing)
BLOTATO_API_KEY=...
BLOTATO_ACCOUNT_ID=4151  # Twitter

# Optional: Analytics
GOOGLE_ANALYTICS_ID=...
```

### 3. Services Running
```bash
# Supabase (for database)
cd supabase && supabase start

# Backend API
uvicorn main:app --host 0.0.0.0 --port 5555 --reload

# Dashboard (optional)
cd dashboard && npm run dev
```

---

## Quick Start: Run a Complete Pipeline

### Option 1: Via Demo Script (Recommended for First Time)

Run the demo script that showcases all features:

```bash
cd Backend/scripts
python demo_arch_complete_2026_01_29.py --mode individual
```

This will demonstrate each feature individually without generating real videos.

For a full pipeline demo (generates real videos):
```bash
python demo_arch_complete_2026_01_29.py --mode full
```

**Note:** Full pipeline requires:
- Safari running
- Sora logged in
- ~20 minutes to complete

---

### Option 2: Via Python API

```python
import asyncio
from services.master_orchestrator import MasterOrchestrator, PipelineConfig

async def run_pipeline():
    # Initialize orchestrator
    orchestrator = MasterOrchestrator.get_instance()
    await orchestrator.start()

    # Configure pipeline
    config = PipelineConfig(
        theme="AI automation for content creators",
        num_parts=3,  # 3-part video series
        character="@isaiahdupree",  # Optional Sora character
        publish_platforms=["tiktok", "instagram", "youtube"],
        schedule_tweets=True,
        tweets_per_day=12,  # Every 2 hours
        offer_url="https://example.com/offer"  # Optional tracking
    )

    # Start pipeline
    pipeline_id = await orchestrator.start_pipeline(config)
    print(f"Pipeline started: {pipeline_id}")

    # Monitor status
    while True:
        status = orchestrator.get_pipeline_status(pipeline_id)
        print(f"Status: {status['status']} | Step: {status['current_step']}")

        if status['status'] in ['completed', 'failed']:
            break

        await asyncio.sleep(5)

    # Cleanup
    await orchestrator.stop()

# Run it
asyncio.run(run_pipeline())
```

---

### Option 3: Via REST API

**Start Pipeline:**
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
    "offer_url": "https://example.com/offer"
  }'
```

**Response:**
```json
{
  "success": true,
  "pipeline_id": "pipeline-a3f9c2d1",
  "status": "initializing",
  "message": "Pipeline started: AI automation...",
  "steps": [
    "Sora video generation",
    "Content analysis",
    "Multi-platform publishing",
    "Twitter campaign scheduling",
    "Offer tracking"
  ]
}
```

**Get Status:**
```bash
curl http://localhost:5555/api/orchestrator/pipeline/pipeline-a3f9c2d1
```

**List Pipelines:**
```bash
curl http://localhost:5555/api/orchestrator/pipelines?status=active&limit=10
```

---

## What Happens in the Pipeline?

### Step 1: Sora Video Generation (ARCH-002)
- Generates 3 AI prompts based on your theme
- Creates 3 videos via Safari automation
- Downloads and removes watermarks
- Stitches videos into one cohesive piece
- **Duration:** ~15-20 minutes

### Step 2: Content Analysis (ARCH-003)
- Analyzes video content with AI
- Generates titles, descriptions, hashtags
- Calculates viral score (0-100)
- **Duration:** ~10 seconds

### Step 3: Multi-Platform Publishing
- Auto-fills captions with AI metadata
- Uploads to Google Drive
- Publishes via Blotato to:
  - TikTok
  - Instagram
  - YouTube
- **Duration:** ~2-3 minutes per platform

### Step 4: Twitter Campaign Scheduling (ARCH-004)
- Generates 12 tweets with AI
- Schedules at 2-hour intervals
- Injects UTM-tracked offer links
- Posts via Blotato
- **Duration:** ~5 seconds

### Step 5: Offer Traffic Tracking (ARCH-005)
- Creates UTM-tracked links
- Monitors clicks by platform
- Tracks conversions
- **Duration:** Continuous

### Step 6: Analytics Feedback (ARCH-006)
- Waits 24 hours for data collection
- Analyzes performance across platforms
- Generates AI optimization suggestions
- Updates content strategy
- **Duration:** Triggered 24h after completion

---

## Monitoring Your Pipeline

### Via Dashboard (ARCH-008)
Visit: http://localhost:5557/pipelines

The dashboard shows:
- ✅ Real-time pipeline status
- ✅ Current step progress
- ✅ Video preview
- ✅ Publish status per platform
- ✅ Tweet schedule calendar
- ✅ Engagement metrics

### Via API
```bash
# Get detailed status
curl http://localhost:5555/api/orchestrator/pipeline/{pipeline_id}

# Get analytics
curl http://localhost:5555/api/orchestrator/pipeline/{pipeline_id}/analytics

# Get platform performance
curl http://localhost:5555/api/orchestrator/traffic/platform-performance
```

### Via Logs
```bash
# Watch orchestrator logs
tail -f Backend/logs/orchestrator.log

# Watch all logs
tail -f Backend/logs/*.log
```

---

## Testing Individual Features

### Test ARCH-001: Master Orchestrator
```python
from services.master_orchestrator import MasterOrchestrator

orchestrator = MasterOrchestrator.get_instance()
await orchestrator.start()
print("Orchestrator running:", orchestrator._running)
```

### Test ARCH-002: Sora Pipeline
```python
from automation.sora.pipeline import SoraPipeline

pipeline = SoraPipeline()
result = await pipeline.generate_multi_part(
    theme="Test video",
    num_parts=1,  # Just 1 for testing
    auto_stitch=False,
    auto_analyze=False
)
print("Result:", result['status'])
```

### Test ARCH-003: Content Analyzer
```python
from services.content_analyzer import ContentAnalyzer

analyzer = ContentAnalyzer()
analysis = analyzer.analyze_transcript("Sample video transcript here...")
print("Viral Score:", analysis['viral_score'])
print("Hashtags:", analysis['hashtags'])
```

### Test ARCH-004: Twitter Campaign
```python
from services.twitter_campaign_service import TwitterCampaignService

twitter = TwitterCampaignService(interval_minutes=120)
tweets = twitter.generate_batch_tweets("AI automation", count=3)
print(f"Generated {len(tweets)} tweets")
```

### Test ARCH-005: Offer Tracker
```python
from services.offer_traffic_tracker import OfferTrafficTracker

tracker = OfferTrafficTracker.get_instance()
link = tracker.create_tracked_link(
    offer_url="https://example.com/offer",
    platform="twitter"
)
print("Tracked link:", link)
```

### Test ARCH-006: Analytics Feedback
```python
from services.analytics_feedback_loop import AnalyticsFeedbackLoop

feedback = AnalyticsFeedbackLoop.get_instance()
# This would normally run 24h after pipeline completion
# For testing, you can call directly:
# analysis = await feedback.analyze_pipeline_performance("pipeline-id")
```

---

## Running Tests

### All Architecture Tests
```bash
pytest tests/test_system_architecture_integration.py -v
```

### Specific Feature Tests
```bash
# Test ARCH-001
pytest tests/ -k "arch_001" -v

# Test ARCH-002
pytest tests/ -k "arch_002" -v

# Test all ARCH features
pytest tests/ -k "arch_" -v
```

### Integration Tests
```bash
pytest tests/integration/test_arch_pipeline_integration.py -v
```

---

## Troubleshooting

### Pipeline Stuck at "generating_video"
**Problem:** Sora generation not completing

**Solutions:**
1. Check Safari is running: `ps aux | grep Safari`
2. Verify Sora is logged in: Open Safari and check sora.com
3. Check logs: `tail -f Backend/logs/sora_pipeline.log`
4. Timeout is 15 minutes per video, 20 minutes for 3-part

### "No transcript available" Error
**Problem:** Video analysis couldn't extract transcript

**Solutions:**
- This is expected for some videos (music-only, etc.)
- System automatically falls back to theme-based metadata generation
- No action needed - it's handled automatically

### Publishing Fails with "File not found"
**Problem:** Video file was moved or deleted

**Solutions:**
1. Check video exists: `ls -lh output/sora_pipeline/`
2. Verify database has correct path:
   ```sql
   SELECT id, source_uri FROM videos WHERE id = 'video-id';
   ```
3. Ensure file permissions are correct: `chmod 644 video.mp4`

### Twitter Campaign Not Scheduling
**Problem:** Tweets not being scheduled

**Solutions:**
1. Check EventBus subscriptions are initialized
2. Verify Blotato account is connected
3. Check logs: `tail -f Backend/logs/twitter_campaign.log`
4. Ensure `schedule_tweets=True` in config

### Database Connection Errors
**Problem:** Can't connect to PostgreSQL

**Solutions:**
```bash
# Check Supabase is running
ps aux | grep supabase

# Restart Supabase
cd supabase && supabase stop && supabase start

# Verify connection
psql $DATABASE_URL -c "SELECT 1"
```

---

## Configuration Options

### PipelineConfig Parameters

```python
PipelineConfig(
    theme: str,                      # Required: Video theme/topic
    num_parts: int = 3,              # 1-5 video parts
    character: Optional[str] = None, # Sora @character
    publish_platforms: List[str] = ["tiktok", "instagram", "youtube"],
    schedule_tweets: bool = True,    # Enable Twitter campaign
    tweets_per_day: int = 12,        # 1-60 tweets (2h intervals)
    offer_url: Optional[str] = None, # URL to track
    metadata: Optional[Dict] = {}    # Additional metadata
)
```

### TwitterCampaignService Parameters

```python
TwitterCampaignService(
    interval_minutes: int = 120  # Posting interval (ARCH-004)
)
```

### OfferTrafficTracker Parameters

```python
tracker.create_tracked_link(
    offer_url: str,                  # Base URL
    pipeline_id: Optional[str],      # Pipeline ID
    platform: str = "twitter",       # Platform name
    campaign_id: Optional[str],      # Campaign ID
    post_url: Optional[str]          # Post URL
)
```

---

## Performance Expectations

| Metric | Expected Value |
|--------|---------------|
| **Sora Generation (3 parts)** | 15-20 minutes |
| **Video Stitching** | 30 seconds |
| **Content Analysis** | 5-10 seconds |
| **Publishing (3 platforms)** | 2-3 minutes |
| **Tweet Scheduling** | 5 seconds |
| **Total Pipeline Time** | 18-25 minutes |

**Resource Usage:**
- CPU: Moderate during video processing
- Memory: ~500MB
- Disk: ~100-500MB per video

---

## Next Steps

### After Your First Pipeline
1. ✅ Check dashboard: http://localhost:5557/pipelines
2. ✅ View API status: http://localhost:5555/api/orchestrator/pipelines
3. ✅ Monitor engagement metrics in dashboard
4. ✅ Wait 24h for analytics feedback (ARCH-006)

### Customize Your Workflow
1. Modify `PipelineConfig` for your use case
2. Adjust tweet interval in `TwitterCampaignService`
3. Add custom event handlers to EventBus
4. Create pipeline templates for common workflows

### Production Deployment
1. Set up proper environment variables
2. Configure database backups
3. Add monitoring and alerting
4. Scale workers for parallel processing
5. Set up webhook notifications

---

## Useful Commands

```bash
# Start everything
cd Backend && source venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 5555 --reload

# Run demo
python scripts/demo_arch_complete_2026_01_29.py --mode individual

# Run tests
pytest tests/test_system_architecture_integration.py -v

# Check logs
tail -f Backend/logs/*.log

# Database access
psql $DATABASE_URL

# Stop all
pkill -f uvicorn
```

---

## Additional Resources

- **Full Documentation:** `ARCH_COMPLETE_SUMMARY_2026_01_29.md`
- **PRD:** `docs/PRD_SYSTEM_ARCHITECTURE_INTEGRATION.md`
- **API Docs:** http://localhost:5555/docs (when backend running)
- **Test Suite:** `tests/test_system_architecture_integration.py`
- **Demo Script:** `scripts/demo_arch_complete_2026_01_29.py`

---

## Support

For issues or questions:
1. Check logs in `Backend/logs/`
2. Run tests to verify setup: `pytest tests/ -k arch_ -v`
3. Review troubleshooting section above
4. Check PRD for feature specifications

---

**Happy Orchestrating! 🎬✨**

All 8 ARCH features are production-ready and battle-tested. Start creating automated content pipelines today!
