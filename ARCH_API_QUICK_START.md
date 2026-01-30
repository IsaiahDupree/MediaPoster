# MediaPoster ARCH Features - Quick Start API Guide

**Date:** January 30, 2026
**Status:** ✅ All features implemented and tested

---

## Quick Start

### 1. Start a Content Pipeline

```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "AI automation transforming business",
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
  "message": "Pipeline started: AI automation transforming business",
  "steps": [
    "Sora video generation",
    "Content analysis",
    "Multi-platform publishing",
    "Twitter campaign scheduling",
    "Offer tracking"
  ]
}
```

### 2. Check Pipeline Status

```bash
curl http://localhost:5555/api/orchestrator/pipeline/pipeline-a1b2c3d4
```

**Response:**
```json
{
  "success": true,
  "pipeline_id": "pipeline-a1b2c3d4",
  "theme": "AI automation transforming business",
  "status": "publishing",
  "started_at": "2026-01-30T17:00:00Z",
  "current_step": "publishing",
  "outputs": {
    "sora": {
      "stitched_video": "/videos/multipart_a1b2c3d4_final.mp4",
      "successful_parts": 3,
      "failed_parts": 0,
      "analysis": {
        "title_tiktok": "AI Is Automating Everything (And Here's Why)",
        "title_instagram": "The Automation Revolution Is Here",
        "title_youtube": "How AI Automation Is Transforming Modern Business",
        "description": "Discover how artificial intelligence is revolutionizing business processes...",
        "hashtags": ["#AI", "#automation", "#business", "#technology"],
        "detected_hook": "AI is changing everything..."
      }
    },
    "publish_jobs": [
      {"platform": "tiktok", "status": "completed"},
      {"platform": "instagram", "status": "completed"},
      {"platform": "youtube", "status": "running"},
      {"platform": "threads", "status": "pending"}
    ]
  }
}
```

### 3. List Recent Pipelines

```bash
# Get last 10 pipelines
curl http://localhost:5555/api/orchestrator/pipelines

# Filter by status
curl http://localhost:5555/api/orchestrator/pipelines?status=completed&limit=5
```

**Response:**
```json
{
  "success": true,
  "count": 3,
  "pipelines": [
    {
      "pipeline_id": "pipeline-a1b2c3d4",
      "theme": "AI automation transforming business",
      "status": "completed",
      "started_at": "2026-01-30T17:00:00Z",
      "video_path": "/videos/multipart_a1b2c3d4_final.mp4",
      "published_count": 22,
      "tweets_scheduled": 12
    }
  ]
}
```

### 4. Get Pipeline Event History (Debugging)

```bash
curl http://localhost:5555/api/orchestrator/pipeline/pipeline-a1b2c3d4/events
```

**Response:**
```json
{
  "success": true,
  "pipeline_id": "pipeline-a1b2c3d4",
  "event_count": 45,
  "events": [
    {
      "timestamp": "2026-01-30T17:00:00Z",
      "topic": "orchestrator.pipeline.started",
      "payload": {
        "pipeline_id": "pipeline-a1b2c3d4",
        "theme": "AI automation"
      }
    },
    {
      "timestamp": "2026-01-30T17:01:05Z",
      "topic": "sora.batch.requested",
      "payload": {
        "pipeline_id": "pipeline-a1b2c3d4",
        "num_parts": 3,
        "character": "@isaiahdupree"
      }
    }
  ]
}
```

---

## Request Parameters

### POST /api/orchestrator/pipeline/start

**Required Parameters:**
- `theme` (string) - Video content theme/topic
  - Min length: 1 character
  - Example: "AI automation transforming business"

**Optional Parameters:**
- `num_parts` (integer, default: 3)
  - Video parts to generate (1-5)
  - Recommended: 3 (hook, main content, payoff)
  - Example: 3

- `character` (string, optional)
  - Sora character reference
  - Format: "@charactername" (e.g., "@isaiahdupree")
  - Example: "@isaiahdupree"

- `publish_platforms` (array, default: ["tiktok", "instagram", "youtube"])
  - Platforms to publish to
  - Available: tiktok, instagram, youtube, threads, twitter, pinterest, linkedin, facebook, bluesky, snapchat, tumbleweed
  - Example: ["tiktok", "instagram", "youtube"]

- `schedule_tweets` (boolean, default: true)
  - Whether to schedule Twitter/X posts
  - Example: true

- `tweets_per_day` (integer, default: 12)
  - Number of tweets to schedule
  - Range: 1-60
  - Interval: (24 * 60) / tweets_per_day minutes
  - Example: 12 (= 120-minute = 2-hour intervals)

- `offer_url` (string, optional)
  - URL to track and promote in tweets
  - Must be valid HTTP(S) URL
  - Supports UTM parameters
  - Example: "https://blotato.com/offers/ai-automation"

- `metadata` (object, optional)
  - Additional custom metadata
  - Example: {"campaign_id": "campaign-123", "ab_test": "variant_a"}

---

## Pipeline Statuses

| Status | Description | Duration |
|--------|-------------|----------|
| `initializing` | Setting up pipeline | <1s |
| `generating_video` | Sora video generation in progress | 2-5 min |
| `analyzing` | Content analysis running | 20-30s |
| `publishing` | Multi-platform publishing | 2-5 min |
| `scheduling_tweets` | Twitter campaign scheduling | 10-30s |
| `completed` | Pipeline finished successfully | Total: 5-15 min |
| `failed` | Pipeline encountered error | Variable |
| `partial` | Some steps succeeded, some failed | Variable |

---

## Response Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Pipeline found, status retrieved |
| 400 | Bad request | Invalid pipeline_id format |
| 404 | Not found | Pipeline doesn't exist |
| 500 | Server error | Database connection failed |

---

## Pipeline Data Structure

### Complete Pipeline Response

```json
{
  "pipeline_id": "pipeline-a1b2c3d4",
  "config": {
    "theme": "AI automation",
    "num_parts": 3,
    "character": "@isaiahdupree",
    "publish_platforms": ["tiktok", "instagram", "youtube"],
    "schedule_tweets": true,
    "tweets_per_day": 12,
    "offer_url": "https://blotato.com/offers/ai"
  },
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "theme": "AI automation",
  "status": "completed",
  "started_at": "2026-01-30T17:00:00Z",
  "completed_at": "2026-01-30T17:12:35Z",
  "duration_seconds": 755,
  "current_step": "twitter_campaign",
  "steps_completed": [
    "sora_generation",
    "content_analysis",
    "publishing",
    "twitter_campaign"
  ],
  "outputs": {
    "sora": {
      "stitched_video": "/videos/multipart_a1b2c3d4_final.mp4",
      "successful_parts": 3,
      "failed_parts": 0,
      "analysis": {
        "title_tiktok": "AI Is Automating Everything",
        "title_instagram": "The Automation Revolution",
        "title_youtube": "How AI Automation Transforms Business",
        "description": "Full description text...",
        "hashtags": ["#AI", "#automation", "#business"],
        "detected_hook": "AI is changing everything",
        "viral_score": 8.7,
        "emotional_triggers": ["curiosity", "urgency", "inspiration"],
        "key_moments": [
          {"timestamp": 5, "description": "Hook moment"},
          {"timestamp": 15, "description": "Main content starts"},
          {"timestamp": 45, "description": "Call to action"}
        ]
      }
    },
    "publish_jobs": [
      {
        "platform": "tiktok",
        "status": "completed",
        "post_url": "https://tiktok.com/@blotato/video/1234567890",
        "timestamp": "2026-01-30T17:05:00Z"
      },
      {
        "platform": "instagram",
        "status": "completed",
        "post_url": "https://instagram.com/p/ABC123/",
        "timestamp": "2026-01-30T17:05:15Z"
      },
      {
        "platform": "youtube",
        "status": "completed",
        "post_url": "https://youtube.com/watch?v=dQw4w9WgXcQ",
        "timestamp": "2026-01-30T17:06:00Z"
      }
    ],
    "twitter": {
      "tweets_scheduled": 12,
      "first_tweet": "2026-01-30T19:00:00Z",
      "last_tweet": "2026-01-31T17:00:00Z",
      "tweet_urls": [
        "https://twitter.com/blotato/status/1234567890",
        "https://twitter.com/blotato/status/1234567891"
      ]
    },
    "traffic": {
      "offer_url": "https://blotato.com/offers/ai",
      "tracking_urls": {
        "tiktok": "https://track.blotato.com/?utm_source=tiktok&utm_medium=social&utm_campaign=pipeline-a1b2c3d4",
        "instagram": "https://track.blotato.com/?utm_source=instagram&utm_medium=social&utm_campaign=pipeline-a1b2c3d4",
        "twitter": "https://track.blotato.com/?utm_source=twitter&utm_medium=social&utm_campaign=pipeline-a1b2c3d4"
      }
    }
  }
}
```

---

## Common Examples

### Example 1: Quick Start
```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "How to build a startup",
    "num_parts": 3
  }'
```

### Example 2: Full Production Setup
```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "AI automation transforming content creation",
    "num_parts": 3,
    "character": "@isaiahdupree",
    "publish_platforms": [
      "tiktok", "instagram", "youtube",
      "threads", "twitter", "pinterest",
      "linkedin", "facebook", "bluesky"
    ],
    "schedule_tweets": true,
    "tweets_per_day": 12,
    "offer_url": "https://blotato.com/offers/ai-automation?ref=content",
    "metadata": {
      "campaign_name": "Q1 2026 AI Campaign",
      "ab_test_variant": "dynamic_titles",
      "priority": "high"
    }
  }'
```

### Example 3: Minimal with Offer Tracking
```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "Digital marketing trends 2026",
    "offer_url": "https://blotato.com/free-trial?campaign=marketing"
  }'
```

### Example 4: Check Status in Script
```bash
#!/bin/bash
PIPELINE_ID="pipeline-a1b2c3d4"

while true; do
  STATUS=$(curl -s http://localhost:5555/api/orchestrator/pipeline/$PIPELINE_ID | jq -r '.status')
  echo "Pipeline status: $STATUS"

  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    echo "Pipeline finished with status: $STATUS"
    break
  fi

  sleep 10
done
```

---

## Integration Examples

### Python
```python
import requests

BASE_URL = "http://localhost:5555"

# Start pipeline
response = requests.post(
    f"{BASE_URL}/api/orchestrator/pipeline/start",
    json={
        "theme": "AI automation",
        "num_parts": 3,
        "schedule_tweets": True,
        "tweets_per_day": 12,
        "offer_url": "https://blotato.com/offer"
    }
)

pipeline_id = response.json()["pipeline_id"]
print(f"Pipeline started: {pipeline_id}")

# Check status
status_response = requests.get(f"{BASE_URL}/api/orchestrator/pipeline/{pipeline_id}")
print(f"Status: {status_response.json()['status']}")

# List pipelines
list_response = requests.get(
    f"{BASE_URL}/api/orchestrator/pipelines",
    params={"status": "completed", "limit": 5}
)
pipelines = list_response.json()["pipelines"]
print(f"Found {len(pipelines)} completed pipelines")
```

### JavaScript/Node.js
```javascript
const fetch = require('node-fetch');

const BASE_URL = 'http://localhost:5555';

async function startPipeline() {
  const response = await fetch(
    `${BASE_URL}/api/orchestrator/pipeline/start`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        theme: 'AI automation',
        num_parts: 3,
        schedule_tweets: true,
        tweets_per_day: 12,
        offer_url: 'https://blotato.com/offer'
      })
    }
  );

  const data = await response.json();
  console.log(`Pipeline started: ${data.pipeline_id}`);
  return data.pipeline_id;
}

async function getPipelineStatus(pipelineId) {
  const response = await fetch(`${BASE_URL}/api/orchestrator/pipeline/${pipelineId}`);
  const data = await response.json();
  console.log(`Status: ${data.status}`);
  return data;
}

// Usage
(async () => {
  const id = await startPipeline();
  const status = await getPipelineStatus(id);
})();
```

---

## Troubleshooting

### Pipeline Stuck in "generating_video"
- Check Sora service logs: `Backend/logs/sora_pipeline.log`
- Verify Sora access: Check if Safari automation is running
- Check offer URL is reachable (if provided)

### Platform Publishing Failed
- Check Blotato service logs
- Verify platform credentials are valid
- Check rate limits on social platforms

### Tweets Not Scheduling
- Verify `schedule_tweets: true` in request
- Check `tweets_per_day` value (1-60 range)
- Verify Twitter API credentials

### Analytics Not Appearing
- Wait 5-10 minutes for initial metrics collection
- Check offer_url is provided for tracking
- Verify database connectivity

---

## Performance Tips

1. **Batch Multiple Pipelines**: Use multiple parallel requests
2. **Monitor Status Efficiently**: Poll every 30 seconds instead of every 5
3. **Cache Results**: Store pipeline_id for quick status lookups
4. **Use Webhooks**: (Future feature) Subscribe to completion events instead of polling
5. **Plan Tweets**: Use `tweets_per_day` based on audience timezone

---

## Support & Documentation

- **Full Implementation Report**: `ARCH_SESSION_COMPLETION_REPORT.md`
- **Status Reference**: `ARCH_IMPLEMENTATION_STATUS.md`
- **Feature Details**: `ARCH_IMPLEMENTATION_SUMMARY.md`
- **Verification Tests**: Run `python3 Backend/tests/verify_arch_implementation.py`

---

**Status: ✅ Ready for Production**

*Last Updated: January 30, 2026*
