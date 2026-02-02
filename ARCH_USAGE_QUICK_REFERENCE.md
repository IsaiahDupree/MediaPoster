# ARCH Features - Quick Usage Reference
## MediaPoster System Architecture Integration (ARCH-001 to ARCH-008)

---

## Quick Start: Launch a Complete Pipeline

### Using Python (Backend)
```python
from services.master_orchestrator import MasterOrchestrator, PipelineConfig

# Create orchestrator
orchestrator = MasterOrchestrator.get_instance()

# Create pipeline configuration
config = PipelineConfig(
    theme="AI automation revolutionizing content creation",
    num_parts=3,
    character="@isaiahdupree",  # Optional Sora character
    publish_platforms=["tiktok", "instagram", "youtube"],
    schedule_tweets=True,
    tweets_per_day=12,
    offer_url="https://blotato.com/offers/ai-automation"
)

# Start pipeline
pipeline_id = await orchestrator.start_pipeline(config)
print(f"Pipeline started: {pipeline_id}")
```

### Using REST API (HTTP)
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
  "pipeline_id": "pipeline-a1b2c3d4",
  "status": "initializing",
  "message": "Pipeline started: AI automation revolutionizing content creation",
  "steps": [
    "Sora video generation",
    "Content analysis",
    "Multi-platform publishing",
    "Twitter campaign scheduling",
    "Offer tracking"
  ]
}
```

---

## Feature 1: Master Orchestrator (ARCH-001)

### What It Does
Coordinates all subsystems into a unified pipeline workflow.

### Main Methods
```python
# Start a pipeline
pipeline_id = await orchestrator.start_pipeline(config)

# Get pipeline status
status = orchestrator.get_pipeline_status(pipeline_id)

# List all pipelines
pipelines = await orchestrator.list_pipelines(status="completed", limit=10)

# Cancel a running pipeline
cancelled = await orchestrator.cancel_pipeline(pipeline_id)
```

### Pipeline Status Values
- `initializing` - Just created, starting setup
- `generating_video` - Sora generating videos
- `analyzing` - Content analysis in progress
- `publishing` - Publishing to platforms
- `scheduling_tweets` - Tweet scheduling
- `completed` - Pipeline finished successfully
- `failed` - Pipeline encountered an error

---

## Feature 2: 3-Part Sora Batch (ARCH-002)

### What It Does
Generates multi-part AI videos automatically and stitches them together.

### Python Usage
```python
from automation.sora.pipeline import SoraPipeline

pipeline = SoraPipeline()

result = await pipeline.generate_multi_part(
    theme="AI tips for productivity",
    num_parts=3,
    character="@isaiahdupree",
    auto_stitch=True,      # Automatically stitch parts
    auto_analyze=True,     # Automatically analyze
    remove_watermark=True  # Remove Sora watermark
)

print(f"Video: {result['stitched_video']}")
print(f"Viral Score: {result['analysis']['viral_score']}")
```

### Configuration
```python
config = PipelineConfig(
    num_parts=3,  # 1-5 parts supported
    character="@isaiahdupree"  # Optional Sora character
)
```

---

## Feature 3: Content Analyzer → Publisher (ARCH-003)

### What It Does
Automatically extracts AI metadata and injects it into publishing payloads.

### Auto-Filled Metadata
```python
# The orchestrator automatically extracts and injects:
{
    "title": "AI Automation: The Future of Content Creation",
    "description": "Discover how AI is revolutionizing...",
    "hashtags": ["AI", "automation", "contentcreation"],
    "hook": "Most creators don't know this...",
    "cta": "Learn more at [offer_url]",
    "viral_score": 8.5,
    "content_type": "educational",
    "tone": "informative"
}

# These are passed to PublishWorker automatically
```

### Platform Customization
```python
# Auto-filled metadata is optimized per platform:
metadata = {
    "tiktok": {
        "title": "Shorter, punchy title for TikTok",
        "hashtags": ["#AI", "#automation"]
    },
    "youtube": {
        "title": "Full detailed title for YouTube",
        "description": "Extended description with links"
    },
    "instagram": {
        "title": "Visual-focused title",
        "hashtags": ["#ai", "#trends"]
    }
}
```

---

## Feature 4: Tweet Scheduler 2-Hour Interval (ARCH-004)

### What It Does
Schedules tweets at 2-hour intervals (12 tweets/day by default).

### Configuration
```python
config = PipelineConfig(
    schedule_tweets=True,
    tweets_per_day=12,  # Default: 12 tweets spread over 24h
    # This results in one tweet every 2 hours (120 minutes)
)

# Or customize the interval:
# 12 tweets/day = 24h / 12 = 2h per tweet (default)
# 6 tweets/day = 24h / 6 = 4h per tweet
# 24 tweets/day = 24h / 24 = 1h per tweet
```

### Tweet Generation
```python
# Tweets are automatically generated and scheduled
# Includes:
# - Offer URL with UTM parameters
# - Hook and CTA from content analysis
# - Platform-specific adjustments
# - Multi-account rotation
```

---

## Feature 5: Offer Traffic Tracking (ARCH-005)

### What It Does
Tracks clicks and conversions from social posts to offer URLs.

### Python Usage
```python
from services.offer_traffic_tracker import OfferTrafficTracker

tracker = OfferTrafficTracker.get_instance()

# Create a tracked link
tracked_url = tracker.create_tracked_link(
    offer_url="https://example.com/product",
    campaign="ai-automation-jan2026",
    source="mediaposter",      # Traffic source
    medium="social",           # Medium type
    content="v1"              # Optional variant ID
)

# Result: https://example.com/product?utm_campaign=ai-automation-jan2026&utm_source=mediaposter&utm_medium=social&utm_content=v1

# Track a click
await tracker.track_click(
    utm_campaign="ai-automation-jan2026",
    platform="tiktok",
    account_id="807"
)

# Track a conversion
await tracker.track_conversion(
    utm_campaign="ai-automation-jan2026",
    conversion_type="purchase",
    revenue=49.99
)

# Get analytics
stats = tracker.get_campaign_stats("ai-automation-jan2026")
print(f"Clicks: {stats['total_clicks']}")
print(f"Conversions: {stats['conversions']}")
print(f"ROI: {stats['roi']:.0%}")
```

---

## Feature 6: Analytics Feedback Loop (ARCH-006)

### What It Does
Analyzes post performance and generates optimization recommendations.

### Python Usage
```python
from services.analytics_feedback import get_analytics_feedback

feedback = get_analytics_feedback()
await feedback.start()

# Analyze post performance
insights = await feedback.analyze_post_performance(
    post_id="post-123",
    platform="tiktok",
    views=5000,
    likes=250,
    shares=50,
    conversions=5,
    revenue=249.95
)

# Get recommendations
recommendations = feedback.get_recommendations(
    platform="tiktok",
    content_type="hook"
)

for rec in recommendations:
    print(f"{rec.name}: {rec.description}")
    print(f"Confidence: {rec.confidence:.0%}")
```

### Detected Patterns
```
HIGH PERFORMING:
- Hook type: "Problem-focused" (avg viral score: 8.2)
- CTA style: "Limited time offer" (conversion rate: 3.2%)
- Topics: ["AI", "automation"] (engagement rate: 12%)

LOW PERFORMING:
- Hook type: "Generic intro" (avg viral score: 3.5)
- CTA style: "Learn more" (conversion rate: 0.5%)
```

---

## Feature 7: Unified Pipeline API (ARCH-007)

### Endpoints

#### Start Pipeline
```bash
POST /api/orchestrator/pipeline/start
```

#### Get Pipeline Status
```bash
GET /api/orchestrator/pipeline/{pipeline_id}

# Response:
{
  "success": true,
  "pipeline_id": "pipeline-a1b2c3d4",
  "theme": "AI automation",
  "status": "publishing",
  "started_at": "2026-02-02T15:30:00Z",
  "video_path": "/path/to/video.mp4",
  "published_count": 2,
  "tweets_scheduled": 12
}
```

#### List Pipelines
```bash
GET /api/orchestrator/pipelines?status=completed&limit=10

# Filters:
# - status: initializing|generating_video|analyzing|publishing|completed|failed
# - limit: number of results (default 10)
```

#### Cancel Pipeline
```bash
DELETE /api/orchestrator/pipeline/{pipeline_id}
```

#### Get Pipeline Events
```bash
GET /api/orchestrator/pipeline/{pipeline_id}/events

# Returns all EventBus events for this pipeline
```

#### Get Stats
```bash
GET /api/orchestrator/stats

# Response:
{
  "total_pipelines": 42,
  "successful_pipelines": 38,
  "failed_pipelines": 4,
  "success_rate": 0.904,
  "avg_duration_seconds": 1245,
  "total_videos_generated": 42,
  "total_posts_published": 294,
  "total_tweets_scheduled": 504
}
```

---

## Feature 8: Dashboard Widget (ARCH-008)

### Integration in React
```jsx
import PipelineWidget from '@/components/PipelineWidget'

export function Dashboard() {
  return (
    <div>
      <h1>Content Pipeline</h1>
      <PipelineWidget
        pipelineId="pipeline-a1b2c3d4"
        refreshInterval={5000}  // 5 seconds
      />
    </div>
  )
}
```

### What It Shows
- Real-time pipeline status
- Current step indicator
- Video preview thumbnail
- Per-platform publishing status
- Tweet schedule visualization
- Engagement metrics
- Traffic and conversion data

---

## Common Workflows

### Workflow 1: Generate and Publish Content
```python
# 1. Start orchestrator
orchestrator = MasterOrchestrator.get_instance()
await orchestrator.start()

# 2. Create pipeline
config = PipelineConfig(
    theme="Your content theme",
    num_parts=3,
    publish_platforms=["tiktok", "instagram"],
    schedule_tweets=True,
    offer_url="https://example.com/offer"
)

# 3. Start pipeline
pipeline_id = await orchestrator.start_pipeline(config)

# 4. Monitor progress
while True:
    status = orchestrator.get_pipeline_status(pipeline_id)
    print(f"Status: {status['status']}")
    if status['status'] in ['completed', 'failed']:
        break
    await asyncio.sleep(5)

# 5. Check results
print(f"Videos generated: {status.get('video_path')}")
print(f"Posts published: {status.get('published_count')}")
print(f"Tweets scheduled: {status.get('tweets_scheduled')}")
```

### Workflow 2: Track Offer Performance
```python
# Create tracked link
tracker = OfferTrafficTracker.get_instance()
tracked_url = tracker.create_tracked_link(
    offer_url="https://example.com/product",
    campaign="jan2026-promotion"
)

# Include in tweets/posts
# When users click through, traffic is tracked automatically

# Later, check performance
stats = tracker.get_campaign_stats("jan2026-promotion")
print(f"Total clicks: {stats['total_clicks']}")
print(f"Conversions: {stats['conversions']}")
print(f"Conversion rate: {stats['conversion_rate']:.1%}")
```

### Workflow 3: Optimize Content Strategy
```python
# Get feedback on past performance
feedback = get_analytics_feedback()
recommendations = feedback.get_recommendations(
    platform="tiktok",
    content_type="hook"
)

# Next pipeline will incorporate learnings
config = PipelineConfig(
    theme="New theme incorporating learnings",
    num_parts=3,
    # ... other config
)
```

---

## Troubleshooting

### Pipeline Stuck in "generating_video"
- Check if Safari is running
- Check `Backend/logs/errors.log` for Sora API errors
- Verify OpenAI API key is set
- Manual recovery: `DELETE /api/orchestrator/pipeline/{id}`

### No Posts Publishing
- Verify Blotato API key
- Check if accounts are connected
- Verify video path is valid
- Check EventBus subscriptions

### Tweets Not Scheduling
- Verify Twitter/Blotato account
- Check tweet text length (280 chars)
- Verify offer URL format
- Check scheduler is running

### Offer Tracking Not Working
- Verify offer URL is valid
- Check UTM parameters are appended
- Verify database tables exist
- Check EventBus events are logged

---

## Performance Tuning

### Concurrency
```python
# Configure max concurrent Sora generations
from automation.sora.pipeline import SoraPipeline
pipeline = SoraPipeline(max_concurrent=2)  # Default 2
```

### Timeouts
```python
config = PipelineConfig(
    step_timeouts={
        "sora_generation": 900,    # 15 minutes
        "video_stitching": 120,    # 2 minutes
        "content_analysis": 60,    # 1 minute
        "publishing": 300,         # 5 minutes
        "twitter_campaign": 60     # 1 minute
    }
)
```

### Retry Policy
```python
config = PipelineConfig(
    max_retries=2  # Retry failed steps up to 2 times
)
```

---

## Production Deployment Checklist

- [ ] Database tables created (orchestrator_pipelines, etc.)
- [ ] API keys configured (OpenAI, Blotato, etc.)
- [ ] EventBus backend configured (Redis or in-memory)
- [ ] Logging directories writable
- [ ] SSL/TLS certificates in place
- [ ] Rate limiting configured
- [ ] Monitoring dashboards set up
- [ ] Backup strategy in place
- [ ] Load testing completed
- [ ] Error alerting configured

---

## Additional Resources

- **Full Documentation:** `ARCH_SESSION_VERIFICATION_2026_02_02.md`
- **Test Suite:** `Backend/tests/integration/test_arch_pipeline_integration.py`
- **Implementation Files:**
  - Master Orchestrator: `Backend/services/master_orchestrator.py`
  - Sora Pipeline: `Backend/automation/sora/pipeline.py`
  - Offer Tracker: `Backend/services/offer_traffic_tracker.py`
  - Analytics Feedback: `Backend/services/analytics_feedback.py`
  - API Endpoints: `Backend/api/endpoints/orchestrator.py`

---

**Last Updated:** February 2, 2026
**Status:** Production Ready ✅
