# MediaPoster Orchestrator - Quick Start Guide

## Overview
The Master Orchestrator coordinates the complete autonomous content pipeline:
**Sora → Stitch → Analyze → Publish → Tweet → Track → Optimize**

## Basic Usage

### 1. Start a Pipeline via API

```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "How AI is revolutionizing content creation in 2026",
    "num_parts": 3,
    "character": "@isaiahdupree",
    "publish_platforms": ["tiktok", "instagram", "youtube"],
    "schedule_tweets": true,
    "tweets_per_day": 12,
    "offer_url": "https://blotato.com/ai-automation"
  }'
```

**Response:**
```json
{
  "success": true,
  "pipeline_id": "pipeline-abc123",
  "status": "initializing",
  "message": "Pipeline started: How AI is revolutionizing content creation in 2026"
}
```

### 2. Check Pipeline Status

```bash
curl http://localhost:5555/api/orchestrator/pipeline/pipeline-abc123
```

**Response:**
```json
{
  "success": true,
  "pipeline_id": "pipeline-abc123",
  "theme": "How AI is revolutionizing content creation in 2026",
  "status": "generating_video",
  "started_at": "2026-01-29T10:00:00Z",
  "steps_completed": 1,
  "total_steps": 5,
  "video_path": null,
  "published_count": 0,
  "tweets_scheduled": 0
}
```

### 3. Get Analytics (after 24h)

```bash
curl http://localhost:5555/api/orchestrator/pipeline/pipeline-abc123/analytics
```

**Response:**
```json
{
  "success": true,
  "pipeline_id": "pipeline-abc123",
  "rating": "excellent",
  "metrics": {
    "total_views": 125000,
    "avg_engagement_rate": 8.5,
    "total_likes": 10625,
    "platforms": ["tiktok", "instagram", "youtube"]
  },
  "ai_insights": "Strong hook with the 'AI revolution' angle resonated well...",
  "optimization_suggestions": [
    {
      "category": "Content",
      "suggestion": "Continue emphasizing practical AI use cases"
    },
    {
      "category": "Timing",
      "suggestion": "Post between 9-11 AM for maximum engagement"
    }
  ]
}
```

### 4. Get Traffic Report

```bash
curl http://localhost:5555/api/orchestrator/pipeline/pipeline-abc123/traffic
```

**Response:**
```json
{
  "success": true,
  "pipeline_id": "pipeline-abc123",
  "total_clicks": 3420,
  "total_conversions": 87,
  "total_revenue_usd": 4350.00,
  "conversion_rate": 2.54,
  "platforms": ["twitter", "tiktok", "instagram"]
}
```

## Python SDK Usage

### Start Pipeline Programmatically

```python
from services.master_orchestrator import MasterOrchestrator, PipelineConfig

# Get orchestrator instance
orchestrator = MasterOrchestrator.get_instance()

# Configure pipeline
config = PipelineConfig(
    theme="How AI is revolutionizing content creation in 2026",
    num_parts=3,
    character="@isaiahdupree",
    publish_platforms=["tiktok", "instagram", "youtube"],
    schedule_tweets=True,
    tweets_per_day=12,
    offer_url="https://blotato.com/ai-automation"
)

# Start pipeline
pipeline_id = await orchestrator.start_pipeline(config)
print(f"✅ Pipeline started: {pipeline_id}")

# Monitor progress
while True:
    status = orchestrator.get_pipeline_status(pipeline_id)
    print(f"Status: {status['status']} - {status['steps_completed']}/{status['total_steps']} steps")

    if status['status'] in ['completed', 'failed']:
        break

    await asyncio.sleep(60)  # Check every minute

print(f"✅ Pipeline {status['status']}: {status.get('video_path')}")
```

### Get Analytics and Optimize

```python
from services.analytics_feedback_loop import AnalyticsFeedbackLoop

feedback = AnalyticsFeedbackLoop.get_instance()

# Wait 24 hours after pipeline completion, then analyze
analysis = await feedback.analyze_pipeline_performance(pipeline_id)

print(f"Performance Rating: {analysis['rating']}")
print(f"\nAI Insights:\n{analysis['ai_insights']}")
print(f"\nOptimization Suggestions:")
for suggestion in analysis['optimization_suggestions']:
    print(f"  - [{suggestion['category']}] {suggestion['suggestion']}")

# Get top performing themes for future content
top_themes = feedback.get_top_performing_themes(limit=5)
print(f"\n📊 Top Performing Themes:")
for theme in top_themes:
    print(f"  - {theme['theme']}: {theme['avg_engagement_rate']:.1f}% engagement")
```

### Track Offer Performance

```python
from services.offer_traffic_tracker import OfferTrafficTracker

tracker = OfferTrafficTracker.get_instance()

# Get pipeline traffic report
report = tracker.get_pipeline_traffic_report(pipeline_id)
print(f"Clicks: {report['total_clicks']}")
print(f"Conversions: {report['total_conversions']}")
print(f"Revenue: ${report['total_revenue_usd']:.2f}")
print(f"Conversion Rate: {report['conversion_rate']:.2f}%")

# Get platform performance comparison
platforms = tracker.get_platform_performance(days=30)
for platform in platforms:
    print(f"{platform['platform']}: {platform['total_clicks']} clicks, {platform['total_conversions']} conversions")

# Get top campaigns
campaigns = tracker.get_top_performing_campaigns(limit=10, metric="revenue_usd")
for campaign in campaigns:
    print(f"{campaign['offer_name']}: ${campaign['revenue_usd']:.2f} revenue")
```

## Configuration Options

### PipelineConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `theme` | str | **Required** | Video theme/topic |
| `num_parts` | int | 3 | Number of video parts (1-5) |
| `character` | str | None | Sora @character (e.g., @isaiahdupree) |
| `publish_platforms` | List[str] | ["tiktok", "instagram", "youtube"] | Platforms to publish to |
| `schedule_tweets` | bool | True | Whether to schedule Twitter campaign |
| `tweets_per_day` | int | 12 | Tweets per day (1-60) |
| `offer_url` | str | None | Offer URL to track and promote |
| `metadata` | Dict | {} | Additional metadata |

### Supported Platforms
- `tiktok` - TikTok
- `instagram` - Instagram (Feed + Reels)
- `youtube` - YouTube Shorts
- `twitter` - X/Twitter
- `linkedin` - LinkedIn
- `facebook` - Facebook
- `threads` - Threads
- `pinterest` - Pinterest

### Tweet Interval Calculation
- `tweets_per_day=12` → interval = 120 minutes (2 hours)
- `tweets_per_day=24` → interval = 60 minutes (1 hour)
- `tweets_per_day=6` → interval = 240 minutes (4 hours)

Formula: `interval_minutes = 1440 / tweets_per_day`

## Pipeline Lifecycle

### Status Flow
```
initializing
    ↓
generating_video  (Sora 3-part generation)
    ↓
analyzing  (AI content analysis)
    ↓
publishing  (Multi-platform publishing)
    ↓
scheduling_tweets  (Twitter campaign)
    ↓
completed  ✅
```

### Error Handling
If any step fails, status becomes `failed` with error details:

```json
{
  "status": "failed",
  "error": "Failed to generate video part 2: Sora timeout",
  "failed_at": "2026-01-29T10:45:23Z"
}
```

## API Endpoints Reference

### Pipeline Management
- `POST /api/orchestrator/pipeline/start` - Start new pipeline
- `GET /api/orchestrator/pipeline/{id}` - Get status
- `GET /api/orchestrator/pipelines` - List all pipelines
- `GET /api/orchestrator/pipeline/{id}/events` - Get event log
- `GET /api/orchestrator/stats` - Get system stats
- `GET /api/orchestrator/health` - Health check

### Analytics
- `GET /api/orchestrator/pipeline/{id}/analytics` - Get AI analysis
- `GET /api/orchestrator/analytics/top-themes` - Top themes
- `GET /api/orchestrator/analytics/historical` - Historical insights

### Traffic Tracking
- `GET /api/orchestrator/pipeline/{id}/traffic` - Pipeline traffic
- `GET /api/orchestrator/traffic/platform-performance` - Platform comparison
- `GET /api/orchestrator/traffic/top-campaigns` - Top campaigns

## Environment Variables

```bash
# Required
OPENAI_API_KEY=sk-...              # For content analysis and feedback
BLOTATO_API_KEY=...                # For multi-platform publishing

# Optional
DATABASE_URL=postgresql://...      # Database connection
TWITTER_CAMPAIGN_TWEETS_PER_DAY=12 # Tweet frequency
```

## Troubleshooting

### Pipeline Stuck in "generating_video"
- Check Sora account login status
- Verify Safari automation is working
- Check Sora queue status

### No Analytics Available
- Analytics requires 24 hours of data collection
- Ensure posts were successfully published
- Check that performance metrics are being tracked

### Traffic Tracking Not Working
- Verify offer URL is valid
- Check UTM parameters are being added
- Ensure clicks are being logged via EventBus

## Best Practices

1. **Theme Selection:** Use specific, engaging themes (e.g., "How AI automation saves content creators 10 hours/week" vs. "AI is cool")

2. **Multi-part Videos:** Use 3 parts for optimal storytelling (Hook → Value → CTA)

3. **Platform Selection:** Start with top 3 platforms (TikTok, Instagram, YouTube) before expanding

4. **Tweet Frequency:** 12 tweets/day (2-hour intervals) balances visibility and spam prevention

5. **Offer URLs:** Always include tracked offer URLs for conversion attribution

6. **Analytics Review:** Wait 24-48 hours before analyzing performance for accurate metrics

7. **Optimization Loop:** Use AI insights to refine future content themes and formats

## Example Workflows

### Workflow 1: Quick Single-Part Video
```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -d '{"theme": "Quick tip: AI automation hack", "num_parts": 1, "publish_platforms": ["tiktok"]}'
```

### Workflow 2: Full 3-Part Campaign with Tracking
```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -d '{
    "theme": "Complete guide to AI content automation",
    "num_parts": 3,
    "publish_platforms": ["tiktok", "instagram", "youtube"],
    "schedule_tweets": true,
    "tweets_per_day": 12,
    "offer_url": "https://blotato.com/ai-course"
  }'
```

### Workflow 3: Character-Specific Content
```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -d '{
    "theme": "Behind the scenes of my AI workflow",
    "num_parts": 2,
    "character": "@isaiahdupree",
    "publish_platforms": ["tiktok", "instagram", "youtube", "twitter"]
  }'
```

## Performance Expectations

| Metric | Expected Value |
|--------|----------------|
| Pipeline Duration | 20-50 minutes |
| Video Generation | 15-45 minutes |
| Content Analysis | 5-10 seconds |
| Publishing (per platform) | 10-30 seconds |
| Tweet Scheduling | 1-2 seconds |
| Analytics Generation | 10-20 seconds |

## Support

For issues or questions:
1. Check pipeline status via API
2. Review event log: `GET /api/orchestrator/pipeline/{id}/events`
3. Check system health: `GET /api/orchestrator/health`
4. Review error logs in `Backend/logs/`

---

**Last Updated:** January 29, 2026
**Version:** 1.0
**Status:** Production Ready
