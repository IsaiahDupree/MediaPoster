# System Architecture Integration Quick Start Guide
**Last Updated:** February 2, 2026

---

## Overview

The System Architecture Integration (ARCH) provides a unified orchestrator for the complete MediaPoster workflow:

```
Sora (1-3 part) → Stitch → Analyze → Auto-fill → Post to Platforms
                                           ↓
                      Tweet every 2h → Track Engagement → Drive Traffic
```

---

## Starting Your First Pipeline

### Option 1: Using the REST API

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

### Option 2: Using Python

```python
from services.master_orchestrator import MasterOrchestrator, PipelineConfig

# Create orchestrator
orchestrator = MasterOrchestrator.get_instance()

# Create configuration
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
```

---

## Monitoring Pipeline Progress

### Check Real-Time Status

```bash
# Get specific pipeline status
curl http://localhost:5555/api/orchestrator/pipeline/{pipeline_id}

# List all recent pipelines
curl http://localhost:5555/api/orchestrator/pipelines?limit=10&status=completed

# Get pipeline events (for debugging)
curl http://localhost:5555/api/orchestrator/pipeline/{pipeline_id}/events
```

### Expected Pipeline Status Progression

1. **initializing** → Preparing pipeline and database records
2. **generating_video** → Sora is creating video parts
3. **analyzing** → Content analyzer extracting metadata
4. **publishing** → Multi-platform publishing in progress
5. **scheduling_tweets** → Twitter campaign being scheduled
6. **completed** → Pipeline done successfully

---

## Configuration Options

### Required Parameters

| Parameter | Type | Example |
|-----------|------|---------|
| `theme` | string | "AI automation revolutionizing content creation" |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `num_parts` | int | 3 | Number of video parts (1-5) |
| `character` | string | null | Sora @character reference |
| `publish_platforms` | array | ["tiktok", "instagram", "youtube"] | Platforms to publish to |
| `schedule_tweets` | boolean | true | Schedule Twitter campaign |
| `tweets_per_day` | int | 12 | Number of tweets per day (1-60) |
| `offer_url` | string | null | Offer URL for traffic tracking |

---

## Pipeline Workflow Details

### Step 1: Sora Video Generation (ARCH-002)
- Generates `num_parts` video segments concurrently (max 2 due to Safari)
- Each part: ~2-4 minutes
- Timeout: 15 minutes per entire batch
- Output: Individual MP4 files

### Step 2: Video Stitching (ARCH-002)
- Concatenates parts using VideoStitcher
- Removes Sora watermarks (optional)
- Timeout: 2 minutes
- Output: Single stitched video MP4

### Step 3: Content Analysis (ARCH-003)
- Analyzes video for:
  - Hook/opening (most impactful moment)
  - Topics and keywords
  - Tone and pacing
  - Pain points addressed
  - Call-to-action effectiveness
  - Viral score prediction
- Timeout: 1 minute
- Output: Analysis JSON object

### Step 4: Publishing (ARCH-003)
- Platform-specific metadata auto-generated:
  - TikTok: Short hook + 7 hashtags
  - Instagram: Long caption + 25 hashtags
  - YouTube: SEO-optimized title + description
- Uploads to Blotato (unified publishing API)
- Timeout: 5 minutes per platform
- Output: Platform URLs for each post

### Step 5: Twitter Campaign (ARCH-004)
- Schedules `tweets_per_day` tweets (default: 12/day)
- Interval: `(24 * 60) / tweets_per_day` minutes (e.g., 120 min for 12/day)
- Rotates offer CTA across variations
- Timeout: 1 minute
- Output: Tweet IDs and schedule

---

## Real-Time Analytics

### Get Performance Analysis (After Publishing)

```bash
# Get AI feedback on pipeline performance
curl http://localhost:5555/api/orchestrator/pipeline/{pipeline_id}/analytics
```

**Response:**
```json
{
  "pipeline_id": "pipeline-abc123",
  "rating": "excellent",
  "engagement_score": 8.5,
  "viral_potential": "high",
  "top_insights": [
    "Hook was highly effective (90% retention)",
    "Pacing matched audience expectations",
    "Call-to-action resonated strongly"
  ],
  "recommendations": [
    "Maintain similar hook style for future videos",
    "Consider longer content on YouTube",
    "Invest more in CTA variations"
  ]
}
```

### Track Offer Traffic

```bash
# Get offer click/conversion metrics
curl http://localhost:5555/api/orchestrator/pipeline/{pipeline_id}/traffic

# Compare platform performance
curl "http://localhost:5555/api/orchestrator/traffic/platform-performance?days=30"

# Find top performing campaigns
curl "http://localhost:5555/api/orchestrator/traffic/top-campaigns?limit=10&metric=conversions"
```

---

## Error Handling & Recovery

### Automatic Retry Logic
- Failed steps automatically retry (up to 2 times by default)
- Timeout triggers retry with same parameters
- After max retries exhausted, pipeline marked as failed

### Manual Pipeline Cancellation

```bash
curl -X DELETE http://localhost:5555/api/orchestrator/pipeline/{pipeline_id}
```

### Troubleshooting

| Status | Issue | Solution |
|--------|-------|----------|
| **stuck in generating_video** | Sora taking too long | Check Sora API status; increase timeout via config |
| **publishing partially failed** | Some platforms succeeded, others failed | Check Blotato logs; platforms can be retried individually |
| **no tweets scheduled** | Twitter service unavailable | Retry manually; check Twitter API credentials |

### Access Event History

```python
from services.event_bus import EventBus

bus = EventBus.get_instance()
events = bus.get_recent_events(correlation_id=pipeline_id, limit=100)

for event in events:
    print(f"{event.timestamp} | {event.topic} | {event.payload}")
```

---

## Advanced Configuration

### Custom Step Timeouts

```python
from services.master_orchestrator import PipelineConfig

config = PipelineConfig(
    theme="...",
    step_timeouts={
        "sora_generation": 1200,    # 20 minutes
        "video_stitching": 180,     # 3 minutes
        "content_analysis": 120,    # 2 minutes
        "publishing": 600,          # 10 minutes
        "twitter_campaign": 120     # 2 minutes
    },
    max_retries=3  # Up to 3 retries per step
)

pipeline_id = await orchestrator.start_pipeline(config)
```

### Custom Publish Platforms

```python
config = PipelineConfig(
    theme="...",
    publish_platforms=["tiktok", "instagram", "youtube", "twitter", "linkedin", "threads"]
)
```

---

## Database Schema

### orchestrator_pipelines table
```sql
CREATE TABLE orchestrator_pipelines (
    pipeline_id VARCHAR PRIMARY KEY,
    theme VARCHAR,
    num_parts INTEGER,
    character VARCHAR,
    publish_platforms TEXT[],
    schedule_tweets BOOLEAN,
    tweets_per_day INTEGER,
    offer_url VARCHAR,
    status VARCHAR,
    correlation_id VARCHAR,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    failed_at TIMESTAMP,
    stitched_video VARCHAR,
    published_count INTEGER,
    tweets_scheduled INTEGER,
    error TEXT,
    metadata JSONB
);
```

### orchestrator_pipeline_steps table
```sql
CREATE TABLE orchestrator_pipeline_steps (
    pipeline_id VARCHAR,
    step_name VARCHAR,
    step_order INTEGER,
    status VARCHAR,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    failed_at TIMESTAMP,
    output JSONB,
    error TEXT,
    PRIMARY KEY (pipeline_id, step_name)
);
```

---

## Key Files & Services

| Component | File | Purpose |
|-----------|------|---------|
| **Master Orchestrator** | `services/master_orchestrator.py` | Core pipeline coordinator |
| **Sora Pipeline** | `automation/sora/pipeline.py` | Multi-part video generation |
| **REST API** | `api/endpoints/orchestrator.py` | Pipeline HTTP endpoints |
| **Sora Worker** | `services/workers/sora_worker.py` | Event-driven Sora handler |
| **Publish Worker** | `services/workers/publish_worker.py` | Event-driven publishing |
| **Content Analyzer** | `services/content_analyzer.py` | AI content analysis |
| **Analytics Feedback** | `services/analytics_feedback_loop.py` | Performance analysis |
| **Offer Tracker** | `services/offer_traffic_tracker.py` | UTM tracking |

---

## Performance Tips

### Optimize for Speed
1. **Reduce num_parts**: 2-part video (8-10 min) vs 3-part (12-15 min)
2. **Skip tweet scheduling**: `schedule_tweets=false` saves 1 minute
3. **Limit platforms**: 2-3 platforms faster than all 8
4. **Pre-generate prompts**: Provide `part_prompts` to skip AI generation step

### Optimize for Quality
1. **Increase num_parts**: More content = better engagement
2. **Enable all platforms**: Reach more audiences
3. **Schedule tweets**: Consistent brand presence
4. **Include offer_url**: Drive measurable conversions

---

## Integration with Other Services

### Event Bus Integration
All pipeline events are published to EventBus topics:
- `orchestrator.pipeline.started` - Pipeline initialized
- `orchestrator.pipeline.completed` - Pipeline finished
- `orchestrator.pipeline.failed` - Pipeline error
- `orchestrator.step.started` - Individual step started
- `orchestrator.step.completed` - Individual step finished

Subscribe to these events for custom handling:
```python
from services.event_bus import EventBus, Topics

bus = EventBus.get_instance()

async def on_pipeline_complete(event):
    print(f"Pipeline {event.payload['pipeline_id']} completed!")

bus.subscribe(Topics.ORCHESTRATOR_PIPELINE_COMPLETED, on_pipeline_complete)
```

---

## Testing

### Run Integration Tests
```bash
cd Backend
python3 -m pytest tests/integration/test_arch_pipeline_integration.py -v
```

### Simulate Pipeline Flow
```bash
# In Python REPL
from services.master_orchestrator import MasterOrchestrator, PipelineConfig
import asyncio

async def test():
    orch = MasterOrchestrator.get_instance()
    config = PipelineConfig(theme="Test theme", num_parts=1)
    pid = await orch.start_pipeline(config)

    # Check status
    import time
    time.sleep(2)
    status = orch.get_pipeline_status(pid)
    print(status)

asyncio.run(test())
```

---

## Support & Debugging

### Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("services.master_orchestrator")
logger.setLevel(logging.DEBUG)
```

### Common Issues

**Q: Pipeline stuck in "generating_video" for 20+ minutes**
A: Check Safari is running and Sora API is accessible. Look at sora_worker logs.

**Q: Some platforms not receiving published videos**
A: Check platform-specific API credentials in Blotato. Verify publish_platforms list.

**Q: Twitter campaign not scheduling**
A: Verify Twitter API access and tweet variation templates are configured.

**Q: No analytics feedback generated**
A: Wait 30 minutes after publishing for metrics to be collected. Must have `schedule_tweets=true` or `offer_url`.

---

## Feature Roadmap

**Completed (ARCH-001 to ARCH-008):**
- ✅ Master Orchestrator Service
- ✅ 3-Part Sora Batch Coordination
- ✅ Content Analyzer → Publisher Integration
- ✅ Tweet Scheduler 2-Hour Interval
- ✅ Offer Traffic Tracking Service
- ✅ Analytics → AI Feedback Loop
- ✅ Unified Pipeline API Endpoint
- ✅ Pipeline Dashboard Widget

**Upcoming:**
- 🔄 Frontend dashboard for pipeline monitoring
- 🔄 Advanced A/B testing with template variations
- 🔄 Content repurposing (long-form to shorts)
- 🔄 Community inbox (unified comments/DMs)

---

## Additional Resources

- **Full ARCH Documentation**: `docs/SESSION_ARCH_VALIDATION_2026_02_02.md`
- **Architecture Overview**: `docs/AGENT_ARCHITECTURE.md`
- **Content Ops PRD**: `Backend/docs/PRD_CONTENT_OPS_CONTROLLER.md`
- **API Reference**: `docs/API_REFERENCE.md`

---

**Happy automating! 🚀**
