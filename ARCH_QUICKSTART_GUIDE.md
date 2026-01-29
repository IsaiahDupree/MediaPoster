# ARCH System Quick Start Guide

**System Architecture Integration - Production Ready**

This guide will help you quickly start using the MediaPoster ARCH system to run fully autonomous content pipelines.

---

## What is ARCH?

ARCH (Architecture Integration) wires together all MediaPoster subsystems into a unified orchestrator:

```
Sora (3-part video) → Stitch → AI Analysis → Publish to 22 accounts → Tweet campaign → Track traffic
```

**One API call = Complete content operation**

---

## Quick Start (30 seconds)

### 1. Start the Backend

```bash
cd Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload
```

### 2. Trigger a Pipeline

```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "The future of AI agents",
    "num_parts": 3,
    "character": "@isaiahdupree",
    "publish_platforms": ["tiktok", "instagram", "youtube"],
    "schedule_tweets": true,
    "tweets_per_day": 12,
    "offer_url": "https://blotato.com/offers/ai-agents"
  }'
```

### 3. Check Status

```bash
# Get pipeline ID from response, then:
curl http://localhost:5555/api/orchestrator/pipeline/{pipeline_id}
```

**Done!** The system will now:
- ✅ Generate 3-part Sora video (8-12 min)
- ✅ Stitch videos together (30-60 sec)
- ✅ Analyze content with AI (10-20 sec)
- ✅ Publish to 22 Blotato accounts (1-2 min)
- ✅ Schedule 12 tweets over 24 hours
- ✅ Track clicks and conversions

---

## Pipeline Configuration

### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `theme` | string | ✅ | - | Video theme/topic |
| `num_parts` | int | ❌ | 3 | Number of video parts (1-5) |
| `character` | string | ❌ | null | Sora @character (e.g., "@isaiahdupree") |
| `publish_platforms` | array | ❌ | ["tiktok", "instagram", "youtube"] | Platforms to publish to |
| `schedule_tweets` | bool | ❌ | true | Schedule Twitter campaign |
| `tweets_per_day` | int | ❌ | 12 | Tweets per day (1-60) |
| `offer_url` | string | ❌ | null | Offer URL for tracking |
| `metadata` | object | ❌ | {} | Custom metadata |

### Example Configurations

#### Minimal (just video)
```json
{
  "theme": "AI productivity hacks",
  "num_parts": 1,
  "schedule_tweets": false
}
```

#### Full Campaign (video + tweets + tracking)
```json
{
  "theme": "Building AI agents that make money",
  "num_parts": 3,
  "character": "@isaiahdupree",
  "publish_platforms": ["tiktok", "instagram", "youtube", "threads"],
  "schedule_tweets": true,
  "tweets_per_day": 12,
  "offer_url": "https://blotato.com/offers/ai-course"
}
```

#### Multi-Product (3 products × 20 tweets = 60/day)
```json
{
  "theme": "Product showcase",
  "tweets_per_day": 60,
  "offer_url": "https://example.com/multi-product"
}
```

---

## API Endpoints

### Core Pipeline

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/orchestrator/pipeline/start` | Start new pipeline |
| GET | `/api/orchestrator/pipeline/:id` | Get pipeline status |
| GET | `/api/orchestrator/pipelines` | List all pipelines |
| GET | `/api/orchestrator/stats` | System stats |
| GET | `/api/orchestrator/health` | Health check |

### Analytics (ARCH-006)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orchestrator/pipeline/:id/analytics` | AI performance insights |
| GET | `/api/analytics/top-themes` | Best performing themes |
| GET | `/api/analytics/historical` | Historical insights |

### Traffic Tracking (ARCH-005)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orchestrator/pipeline/:id/traffic` | Traffic report |
| GET | `/api/traffic/platform-performance` | Platform breakdown |
| GET | `/api/traffic/top-campaigns` | Top campaigns |

---

## Pipeline Status

### Status Values

| Status | Description |
|--------|-------------|
| `initializing` | Pipeline created, starting Sora |
| `generating_video` | Sora generating video parts |
| `analyzing` | AI analyzing content |
| `publishing` | Publishing to platforms |
| `scheduling_tweets` | Scheduling Twitter campaign |
| `completed` | Pipeline finished successfully |
| `failed` | Pipeline encountered error |

### Status Response Example

```json
{
  "pipeline_id": "pipeline-a1b2c3d4",
  "theme": "AI automation",
  "status": "publishing",
  "started_at": "2026-01-29T10:00:00Z",
  "current_step": "publishing",
  "steps_completed": 3,
  "total_steps": 5,
  "outputs": {
    "sora": {
      "stitched_video": "/path/to/video.mp4",
      "analysis": {
        "viral_score": 85,
        "hooks": ["Attention-grabbing hook"],
        "topics": ["AI", "automation", "productivity"],
        "tone": "energetic"
      }
    },
    "publish_jobs": [
      {"platform": "tiktok", "status": "completed"},
      {"platform": "instagram", "status": "in_progress"}
    ]
  }
}
```

---

## Monitoring

### Dashboard

Visit: `http://localhost:5557` (Next.js dashboard)

Features:
- ✅ Real-time pipeline status
- ✅ Progress visualization
- ✅ Video preview
- ✅ Platform publish status
- ✅ Traffic metrics
- ✅ AI insights

### Logs

```bash
# Application logs
tail -f Backend/logs/app.log

# Filter for orchestrator
grep "Master Orchestrator" Backend/logs/app.log

# Filter by pipeline ID
grep "pipeline-a1b2c3d4" Backend/logs/app.log
```

### Database Queries

```sql
-- Active pipelines
SELECT pipeline_id, theme, status, started_at
FROM orchestrator_pipelines
WHERE status NOT IN ('completed', 'failed')
ORDER BY started_at DESC;

-- Pipeline steps
SELECT step_name, status, started_at, completed_at
FROM orchestrator_pipeline_steps
WHERE pipeline_id = 'pipeline-xxx'
ORDER BY step_order;

-- Traffic by platform
SELECT platform, SUM(clicks) as clicks, SUM(conversions) as conversions
FROM offer_traffic_tracking
GROUP BY platform;
```

---

## Common Use Cases

### 1. Daily Content Automation

**Goal:** Generate and publish 1 video daily with tweet campaign

```bash
# Run once per day (can be scheduled with cron)
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "Daily tip: [topic]",
    "num_parts": 1,
    "publish_platforms": ["tiktok", "instagram"],
    "schedule_tweets": true,
    "tweets_per_day": 12
  }'
```

### 2. Product Launch Campaign

**Goal:** Create 3-part video series promoting new product

```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "Introducing [Product Name] - Revolutionary AI Tool",
    "num_parts": 3,
    "character": "@isaiahdupree",
    "publish_platforms": ["tiktok", "instagram", "youtube", "threads", "facebook"],
    "schedule_tweets": true,
    "tweets_per_day": 20,
    "offer_url": "https://example.com/product-launch"
  }'
```

### 3. Content Testing

**Goal:** Test different themes to see what performs best

```bash
# Generate multiple pipelines with different themes
for theme in "AI productivity" "Automation tips" "Tech reviews"; do
  curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
    -H "Content-Type: application/json" \
    -d "{
      \"theme\": \"$theme\",
      \"num_parts\": 1,
      \"schedule_tweets\": false
    }"
  sleep 5
done

# After 24-48 hours, check analytics
curl http://localhost:5555/api/analytics/top-themes
```

### 4. Traffic Optimization

**Goal:** Monitor which platforms drive the most conversions

```bash
# Check platform performance
curl http://localhost:5555/api/traffic/platform-performance?days=30

# Check top campaigns
curl http://localhost:5555/api/traffic/top-campaigns?limit=10&metric=conversions
```

---

## Troubleshooting

### Pipeline Stuck

**Symptom:** Pipeline status not changing

```bash
# 1. Check pipeline status
curl http://localhost:5555/api/orchestrator/pipeline/{id}

# 2. Check event history
curl http://localhost:5555/api/orchestrator/pipeline/{id}/events

# 3. Check logs
grep "{pipeline_id}" Backend/logs/app.log

# 4. Check database
psql -h localhost -p 54322 -U postgres -d postgres
SELECT * FROM orchestrator_pipeline_steps WHERE pipeline_id = '{id}';
```

### Sora Generation Failed

**Common Causes:**
- Safari automation not working
- Not logged into Sora.com
- Download path permissions

**Solutions:**
```bash
# Check Safari automation logs
grep "SoraPipeline" Backend/logs/app.log

# Verify login status (run from Backend/)
python3 -c "
from automation.sora.sora_controller import SoraController
import asyncio
controller = SoraController()
asyncio.run(controller.launch_sora())
asyncio.run(controller.check_login_status())
"
```

### Publishing Failed

**Common Causes:**
- Blotato API credentials invalid
- Platform accounts not connected
- Media file not found

**Solutions:**
```bash
# Check Blotato service logs
grep "BlotatoService" Backend/logs/app.log

# Verify API key
echo $BLOTATO_API_KEY

# Test Blotato connection
curl -X GET http://localhost:5555/api/blotato/accounts \
  -H "Authorization: Bearer $BLOTATO_API_KEY"
```

### Twitter Campaign Not Scheduling

**Common Causes:**
- TwitterCampaignService not started
- EventBus subscription missing
- Blotato Twitter account not connected

**Solutions:**
```bash
# Check if service is running
curl http://localhost:5555/health

# Check database
psql -h localhost -p 54322 -U postgres -d postgres
SELECT * FROM campaign_products;
SELECT * FROM scheduled_tweets WHERE created_at > NOW() - INTERVAL '1 day';
```

---

## Performance Tips

### Optimize Video Generation

1. **Use 1 part for speed:**
   - 1 part = ~3 minutes
   - 3 parts = ~12 minutes

2. **Pre-generate prompts:**
   ```json
   {
     "theme": "Custom theme",
     "num_parts": 3,
     "part_prompts": [
       "Hook: Attention-grabbing opening",
       "Content: Main demonstration",
       "CTA: Call to action"
     ]
   }
   ```

3. **Skip watermark removal:**
   - Saves ~30 seconds per video
   - Set in Sora pipeline config

### Optimize Publishing

1. **Reduce platform count:**
   - Publish to 5-10 platforms instead of 22
   - Focus on high-performing platforms

2. **Batch operations:**
   - Run multiple pipelines with `schedule_tweets: false`
   - Schedule tweets separately in bulk

### Optimize Tweets

1. **Reduce tweet frequency:**
   - 6 tweets/day (4-hour intervals) instead of 12
   - Saves AI costs and API calls

2. **Reuse templates:**
   - Pre-define tweet templates in database
   - Reduce AI generation calls

---

## Advanced Usage

### Custom Event Handlers

Subscribe to pipeline events in your own code:

```python
from services.event_bus import EventBus, Topics

bus = EventBus.get_instance()

async def handle_pipeline_complete(event):
    pipeline_id = event.payload.get("pipeline_id")
    print(f"Pipeline {pipeline_id} completed!")
    # Your custom logic here

bus.subscribe(Topics.ORCHESTRATOR_PIPELINE_COMPLETED, handle_pipeline_complete)
```

### Custom Analytics

Extend analytics with custom metrics:

```python
from services.analytics_feedback_loop import AnalyticsFeedbackLoop

feedback = AnalyticsFeedbackLoop.get_instance()

# Add custom metric
await feedback.record_custom_metric(
    pipeline_id="pipeline-xxx",
    metric_name="brand_mentions",
    metric_value=42
)
```

### Scheduled Pipelines

Use cron to schedule regular pipelines:

```bash
# crontab -e

# Run daily at 9 AM
0 9 * * * curl -X POST http://localhost:5555/api/orchestrator/pipeline/start -H "Content-Type: application/json" -d '{"theme":"Daily AI tip"}'

# Run every 6 hours
0 */6 * * * curl -X POST http://localhost:5555/api/orchestrator/pipeline/start -H "Content-Type: application/json" -d '{"theme":"Tech update"}'
```

---

## Next Steps

### Learn More
- 📖 Read `ARCH_SESSION_SUMMARY_2026_01_29.md` for detailed architecture
- 📊 Check `ARCH_FEATURES_VERIFIED_2026_01_29.md` for implementation details
- 🎨 Explore `ARCH_PIPELINE_DIAGRAM.md` for visual workflow

### Extend the System
- Add custom platforms to `publish_integrator.py`
- Create custom tweet templates in `twitter_campaign_service.py`
- Build custom analytics in `analytics_feedback_loop.py`

### Production Deployment
1. Set up environment variables
2. Configure database connection strings
3. Set up monitoring (logs, health checks)
4. Deploy to cloud (AWS, GCP, Azure)
5. Set up CI/CD pipeline

---

## Support

### Documentation
- `Backend/docs/` - API documentation
- `Backend/services/` - Service source code
- Test files - Usage examples

### Logs
- `Backend/logs/app.log` - Application logs
- `Backend/logs/errors.log` - Error logs

### Database
```bash
# Connect to database
psql -h localhost -p 54322 -U postgres -d postgres

# View tables
\dt

# View pipelines
SELECT * FROM orchestrator_pipelines ORDER BY started_at DESC LIMIT 10;
```

---

**Quick Reference Card**

```
Start Pipeline:  POST /api/orchestrator/pipeline/start
Check Status:    GET  /api/orchestrator/pipeline/:id
List Pipelines:  GET  /api/orchestrator/pipelines
Get Analytics:   GET  /api/orchestrator/pipeline/:id/analytics
Get Traffic:     GET  /api/orchestrator/pipeline/:id/traffic
System Stats:    GET  /api/orchestrator/stats
Health Check:    GET  /api/orchestrator/health
```

**System is ready! Start your first pipeline now! 🚀**
