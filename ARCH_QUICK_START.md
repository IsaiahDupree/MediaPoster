# System Architecture Quick Start Guide

## Overview

The MediaPoster System Architecture (ARCH-001 to ARCH-008) provides a unified, event-driven pipeline for autonomous content creation and publishing.

## Quick API Examples

### 1. Start a Complete Pipeline

**Endpoint:** `POST /api/orchestrator/pipeline/start`

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

### 2. Check Pipeline Status

```bash
curl http://localhost:5555/api/orchestrator/pipeline/pipeline-abc123
```

### 3. List Pipelines

```bash
curl "http://localhost:5555/api/orchestrator/pipelines?status=completed&limit=10"
```

### 4. Cancel Pipeline

```bash
curl -X DELETE http://localhost:5555/api/orchestrator/pipeline/pipeline-abc123
```

## Python SDK Usage

### Start Pipeline Programmatically

```python
from services.master_orchestrator import MasterOrchestrator, PipelineConfig
import asyncio

async def run():
    orchestrator = MasterOrchestrator.get_instance()
    
    config = PipelineConfig(
        theme="AI automation revolutionizing content creation",
        num_parts=3,
        character="@isaiahdupree",
        publish_platforms=["tiktok", "instagram", "youtube"],
        schedule_tweets=True,
        tweets_per_day=12,
        offer_url="https://blotato.com/offers/ai-automation"
    )
    
    pipeline_id = await orchestrator.start_pipeline(config)
    print(f"Pipeline started: {pipeline_id}")
    
    # Check status
    status = orchestrator.get_pipeline_status(pipeline_id)
    print(f"Status: {status['status']}")

asyncio.run(run())
```

## Event Flow

```
Start Pipeline → Sora Generation → Content Analysis → 
Multi-Platform Publishing → Twitter Scheduling → 
Offer Tracking → Analytics & Optimization
```

## Configuration

```python
from services.master_orchestrator import PipelineConfig

config = PipelineConfig(
    theme="content theme",
    num_parts=3,                    # 1-5 parts
    character="@character",         # Sora character
    publish_platforms=["tiktok"],   # Target platforms
    schedule_tweets=True,           # Enable Twitter
    tweets_per_day=12,              # 2-hour intervals
    offer_url="https://example.com/offer",
    max_retries=2                   # Retry failed steps
)
```

## Common Tasks

### Get Pipeline Metrics

```python
from services.master_orchestrator import MasterOrchestrator

orchestrator = MasterOrchestrator.get_instance()
metrics = orchestrator.get_pipeline_metrics()
print(f"Active: {metrics['active_pipelines']}")
print(f"Completed: {metrics['completed_pipelines']}")
```

### Generate Tracked Offer Link

```python
from services.offer_traffic_tracker import OfferTrafficTracker

tracker = OfferTrafficTracker.get_instance()
tracked_url = tracker.create_tracked_link(
    offer_url="https://example.com/offer",
    pipeline_id="pipeline-abc123",
    platform="twitter"
)
print(f"Tracked URL: {tracked_url}")
```

---

**Last Updated:** February 2, 2026
**Version:** 1.0 (Production Ready)
