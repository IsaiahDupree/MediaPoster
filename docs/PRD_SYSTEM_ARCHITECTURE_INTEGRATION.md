# PRD: System Architecture Integration

**Version:** 1.0  
**Date:** January 26, 2026  
**Status:** Active  
**Priority:** P0  
**Estimated Effort:** 2-3 weeks

---

## Executive Summary

Wire together existing MediaPoster subsystems into a unified orchestrator that automates the complete workflow:

```
Sora (1 or 3-part) → Stitch → Analyze → Auto-fill Titles/Descriptions → Post via Blotato (all accounts/platforms)
                                                                      ↓
Tweet Subsystem (every 2h) → Track Engagement → Optimize → Drive Traffic to Offers
```

---

## Current System Status

### ✅ Working Components

| Component | Location | Status |
|-----------|----------|--------|
| Sora Safari Automation | `automation/sora_full_automation.py`, `automation/sora/pipeline.py` | ✅ Working |
| Video Stitching (ffmpeg) | `services/ai_video_pipeline/stitcher.py` | ✅ Working |
| Content Analysis (AI) | `services/content_analyzer.py` | ✅ Working |
| Blotato Publishing | `services/publish_service.py`, `services/blotato_service.py` | ✅ Working |
| 22 Blotato Accounts | All platforms configured | ✅ Working |
| Twitter Campaign System | `services/twitter_campaign_service.py` | ✅ Working |
| Engagement Automation | Comments on threads/IG/TikTok/Twitter | ✅ Working |
| Event Bus (Pub/Sub) | `services/event_bus.py` | ✅ Working |
| Sora Worker | `services/workers/sora_worker.py` | ✅ Working |
| Publish Worker | `services/workers/publish_worker.py` | ✅ Working |

### ⚠️ Integration Gaps

| Gap | Current State | Effort |
|-----|---------------|--------|
| 3-Part Sora Orchestration | 60% built | 2 hours |
| Auto-Fill Titles Before Post | 70% built | 1 hour |
| Tweet Subsystem Every 2h | 80% built | 30 min |
| Offer Traffic Tracking | 0% built | 4 hours |
| Closed-Loop Optimization | 40% built | 3 hours |

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MASTER ORCHESTRATOR                          │
│            (coordinates all subsystems via EventBus)            │
└─────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  SORA PIPELINE  │  │  TWEET ENGINE   │  │  ENGAGEMENT     │
│  ───────────────│  │  ───────────────│  │  AUTOMATION     │
│  - Generate 1-3 │  │  - Every 2h     │  │  ───────────────│
│  - Stitch       │  │  - Offer CTAs   │  │  - Comments     │
│  - Analyze      │  │  - Track clicks │  │  - Likes        │
│  - Queue        │  │  - Optimize     │  │  - Follows      │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BLOTATO PUBLISHER                            │
│  - 22 accounts across 10 platforms                              │
│  - Auto titles/descriptions from AI analysis                    │
│  - Duplicate prevention                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ANALYTICS & OPTIMIZATION                     │
│  - Track engagement metrics                                     │
│  - Offer conversion tracking (UTM)                              │
│  - Feed back to AI for content improvement                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Feature Specifications

### ARCH-001: Master Orchestrator Service

**Priority:** P0

Create unified orchestrator that coordinates all subsystems via EventBus.

```python
# Backend/services/master_orchestrator.py
class MasterOrchestrator:
    async def run_full_pipeline(self, config: PipelineConfig):
        # 1. Generate video(s) via Sora
        # 2. Stitch if multi-part
        # 3. Analyze content
        # 4. Auto-fill metadata
        # 5. Publish to all accounts
        # 6. Schedule tweet campaign
        # 7. Track engagement
```

### ARCH-002: 3-Part Sora Batch Coordination

**Priority:** P0

Add `generate_multi_part()` method to SoraPipeline.

```python
async def generate_multi_part(self, prompts: List[str], stitch: bool = True) -> str:
    videos = []
    for i, prompt in enumerate(prompts):
        video = await self.generate_single(prompt)
        videos.append(video)
    
    if stitch:
        return await self.stitcher.stitch(videos)
    return videos
```

### ARCH-003: Content Analyzer → Publisher Integration

**Priority:** P0

Auto-inject AI-generated titles/descriptions into publish payload.

```python
# In PublishWorker
async def prepare_payload(self, video_path: str):
    analysis = await self.content_analyzer.analyze(video_path)
    return {
        "title": analysis.generated_title,
        "description": analysis.generated_description,
        "hashtags": analysis.suggested_hashtags,
        "hooks": analysis.detected_hooks
    }
```

### ARCH-004: Tweet Scheduler 2-Hour Interval

**Priority:** P1

Configure TwitterCampaignScheduler for 2-hour intervals with offer CTAs.

```python
scheduler = TwitterCampaignScheduler(
    interval_minutes=120,
    include_offer_cta=True,
    offer_rotation=["link1", "link2", "link3"]
)
```

### ARCH-005: Offer Traffic Tracking Service

**Priority:** P1

New service for UTM link generation and conversion tracking.

```python
# Backend/services/offer_tracker.py
class OfferTracker:
    async def create_tracked_link(self, offer_url: str, campaign: str) -> str:
        # Generate short link with UTM params
        
    async def track_click(self, link_id: str, metadata: dict):
        # Record click event
        
    async def get_conversion_report(self, campaign: str) -> ConversionReport:
        # Return attribution data
```

**Database Tables:**
- `offer_links` - tracked URLs with UTM params
- `offer_clicks` - click events
- `offer_conversions` - conversion attribution

### ARCH-006: Analytics → AI Feedback Loop

**Priority:** P1

Connect engagement analytics back to ContentIdeator for optimization.

```python
class ContentOptimizer:
    async def learn_from_performance(self, post_id: str):
        metrics = await self.analytics.get_post_metrics(post_id)
        if metrics.engagement_rate > threshold:
            await self.ideator.reinforce_style(post_id)
        else:
            await self.ideator.avoid_style(post_id)
```

### ARCH-007: Unified Pipeline API Endpoint

**Priority:** P1

Single API endpoint to trigger full workflow.

```python
@router.post("/api/pipeline/full")
async def run_full_pipeline(request: PipelineRequest):
    return await orchestrator.run_full_pipeline(
        prompts=request.prompts,
        accounts=request.accounts or "all",
        tweet_interval=request.tweet_interval or 120,
        offer_url=request.offer_url
    )
```

### ARCH-008: Pipeline Dashboard Widget

**Priority:** P2

Frontend widget showing pipeline status and progress.

```tsx
// dashboard/components/PipelineDashboard.tsx
- Current stage indicator
- Video preview
- Account publish status
- Tweet schedule
- Engagement metrics
```

---

## Implementation Plan

### Phase 1: Core Integration (Week 1)
- ARCH-001: Master Orchestrator
- ARCH-002: 3-Part Sora
- ARCH-003: Analyzer → Publisher

### Phase 2: Tweet & Tracking (Week 2)
- ARCH-004: 2-Hour Tweet Scheduler
- ARCH-005: Offer Tracking Service

### Phase 3: Optimization & UI (Week 3)
- ARCH-006: Analytics Feedback Loop
- ARCH-007: Unified API
- ARCH-008: Dashboard Widget

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Full pipeline execution time | < 10 min |
| Auto-fill accuracy | > 90% |
| Tweet cadence adherence | 100% |
| Offer click tracking | 100% attribution |
| Engagement optimization lift | +15% over baseline |

---

## Features Summary

| ID | Name | Priority |
|----|------|----------|
| ARCH-001 | Master Orchestrator Service | P0 |
| ARCH-002 | 3-Part Sora Batch Coordination | P0 |
| ARCH-003 | Content Analyzer → Publisher Integration | P0 |
| ARCH-004 | Tweet Scheduler 2-Hour Interval | P1 |
| ARCH-005 | Offer Traffic Tracking Service | P1 |
| ARCH-006 | Analytics → AI Feedback Loop | P1 |
| ARCH-007 | Unified Pipeline API Endpoint | P1 |
| ARCH-008 | Pipeline Dashboard Widget | P2 |

---

**Document Owner:** Engineering  
**Last Updated:** January 26, 2026
