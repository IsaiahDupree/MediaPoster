# Pub/Sub Architecture: Gaps & Improvement Opportunities

> **Last Updated:** December 24, 2024
> **Coverage:** ~75% of operations emit events (up from ~40%)

## Current State

### ✅ What's Already Using Event Bus

| Component | Topics Used | Status |
|-----------|-------------|--------|
| **PostScheduler** | `scheduler.*`, `schedule.*`, `publish.*` | ✅ Full integration |
| **PublishWorker** | `publish.*` | ✅ Full pipeline |
| **BlotatoService** | `blotato.publish.*`, `blotato.account.*` | ✅ Subscriptions |
| **WorkflowManager** | `*` (all events) | ✅ Tracking |
| **WebSocket** | `*` (broadcasts to frontend) | ✅ Real-time updates |
| **AI Video Generation** | `ai.generation.*` | ✅ Progress tracking |
| **Clip Extraction** | `clip.extraction.*` | ✅ Progress tracking |
| **Media Processing** | `media.ingested`, `media.deleted` | ✅ NEW |
| **Analysis Pipeline** | `analysis.*` (full lifecycle) | ✅ NEW |
| **Schedule CRUD** | `schedule.created/updated/cancelled` | ✅ NEW |
| **Experiments** | `experiment.*` (create/start/complete) | ✅ NEW |
| **Narrative Builder** | `narrative.*` | ✅ NEW |
| **Accounts** | `account.synced` | ✅ NEW |
| **MetricsFetchWorker** | Subscribes to `publish.completed` | ✅ NEW |
| **CleanupWorker** | Subscribes to `media.deleted` | ✅ NEW |

### Existing Topics (from `topics.py`)

```
MEDIA: ingested, updated, deleted, thumbnail.ready
ANALYSIS: requested, started, progress, step.completed, completed, failed
PUBLISH: requested, queued, started, uploading, completed, failed
SCHEDULE: created, updated, cancelled, due
METRICS: fetch.requested, fetch.completed, updated, aggregated
AI_GENERATION: requested, started, progress, completed, failed
CLIP_EXTRACTION: requested, started, progress, completed, failed
```

---

## ✅ Recently Implemented (December 2024)

### 1. **Media Library Operations** ✅ DONE
| Operation | Event | Location |
|-----------|-------|----------|
| Upload video | `MEDIA_INGESTED` | `media_processing_db.py` |
| Delete video | `MEDIA_DELETED` | `media_processing_db.py` |
| CleanupWorker | Subscribes to `media.deleted` | `workers/cleanup_worker.py` |

### 2. **Posted Content Tracking** ✅ DONE
| Operation | Event | Location |
|-----------|-------|----------|
| Content posted | `PUBLISH_COMPLETED` | `blotato_router.py` |
| MetricsFetchWorker | Subscribes to `publish.completed` | `workers/metrics_fetch_worker.py` |

### 3. **Experiments System** ✅ DONE
| Operation | Event | Location |
|-----------|-------|----------|
| Experiment created | `EXPERIMENT_PLAN_RUN` | `experiments.py` |
| Experiment started | `EXPERIMENT_RUN_STARTED` | `experiments.py` |
| Experiment completed | `EXPERIMENT_RUN_COMPLETED` | `experiments.py` |

### 4. **Narrative Builder** ✅ DONE
| Operation | Event | Location |
|-----------|-------|----------|
| Goal created | `NARRATIVE_GOAL_UPDATED` | `narrative_builder.py` |
| Schedule generated | `NARRATIVE_PLAN_GENERATED` | `narrative_builder.py` |

### 5. **Social Accounts** ✅ DONE
| Operation | Event | Location |
|-----------|-------|----------|
| Account connected | `BLOTATO_ACCOUNT_SYNCED` | `accounts.py` |

### 6. **Schedule CRUD** ✅ DONE
| Operation | Event | Location |
|-----------|-------|----------|
| Post scheduled | `SCHEDULE_CREATED` | `schedule.py` |
| Post updated | `SCHEDULE_UPDATED` | `schedule.py` |
| Post cancelled | `SCHEDULE_CANCELLED` | `schedule.py` |

### 7. **Analysis Pipeline** ✅ DONE (Full Lifecycle)
| Operation | Event | Location |
|-----------|-------|----------|
| Analysis requested | `ANALYSIS_REQUESTED` | `media_processing_db.py` |
| Analysis progress | `ANALYSIS_PROGRESS` | `media_processing_db.py` |
| Step events | `TRANSCRIPT_STARTED`, `VISUAL_STARTED`, etc. | `media_processing_db.py` |
| Analysis completed | `ANALYSIS_COMPLETED` | `media_processing_db.py` |
| Analysis failed | `ANALYSIS_FAILED` | `media_processing_db.py` |

### 8. **Frontend WebSocket Hook** ✅ DONE
| Component | Location |
|-----------|----------|
| `useEventBus()` hook | `dashboard/lib/hooks/useEventBus.ts` |
| `usePublishProgress()` | Real-time publish tracking |
| `useAnalysisProgress()` | Real-time analysis tracking |

---

## 🟡 Remaining Gaps (Lower Priority)

| Missing Step | Should Emit |
|--------------|-------------|
| Frame extraction start | `analysis.frames.started` |
| Frame extraction done | `analysis.frames.completed` |
| Music suggestion ready | `analysis.music.ready` |

---

### 7. **Metrics Backfill** (LOW)
**Current:** Manual script execution
**Problem:** No automated metrics refresh

| Operation | Should Emit | Benefit |
|-----------|-------------|---------|
| Backfill started | `metrics.backfill.started` | Track progress |
| Platform metrics fetched | `metrics.platform.fetched` | Update specific post |
| Backfill completed | `metrics.backfill.completed` | Dashboard refresh |

---

## 🔧 Architecture Improvements

### 1. **Add Missing Topic Definitions**

```python
# Add to topics.py

# CONTENT LIFECYCLE
CONTENT_POSTED = "content.posted"
CONTENT_POST_FAILED = "content.post_failed"
CONTENT_METRICS_UPDATED = "content.metrics.updated"

# EXPERIMENTS
EXPERIMENT_CREATED = "experiment.created"
EXPERIMENT_VARIANT_PUBLISHED = "experiment.variant.published"
EXPERIMENT_CONCLUDED = "experiment.concluded"
EXPERIMENT_LEARNING_EXTRACTED = "experiment.learning.extracted"

# NARRATIVE
NARRATIVE_GOAL_CREATED = "narrative.goal.created"
NARRATIVE_PILLAR_ASSIGNED = "narrative.pillar.assigned"
NARRATIVE_SCHEDULE_GENERATED = "narrative.schedule.generated"

# ACCOUNTS
ACCOUNT_CONNECTED = "account.connected"
ACCOUNT_DISCONNECTED = "account.disconnected"
ACCOUNT_AUTH_EXPIRED = "account.auth.expired"
ACCOUNT_SYNCED = "account.synced"

# METRICS
METRICS_BACKFILL_STARTED = "metrics.backfill.started"
METRICS_BACKFILL_COMPLETED = "metrics.backfill.completed"
```

---

### 2. **Create Event-Driven Workers**

| Worker | Subscribes To | Does |
|--------|---------------|------|
| `MetricsFetchWorker` | `content.posted` | Auto-fetch metrics after publish |
| `ExperimentTracker` | `experiment.variant.published` | Track variant performance |
| `AccountSyncWorker` | `account.*` | Sync Blotato accounts |
| `CleanupWorker` | `media.deleted` | Remove orphaned thumbnails/schedules |
| `NarrativeScheduler` | `narrative.schedule.generated` | Create scheduled_posts entries |

---

### 3. **Frontend WebSocket Integration**

Currently the WebSocket bridge exists but frontend doesn't fully use it.

**Add real-time updates for:**
- Schedule page: Post status changes
- Media library: Analysis progress
- Posted content: New posts appearing
- Experiments: Variant results updating

```typescript
// Frontend WebSocket hook
useEffect(() => {
  const ws = new WebSocket(`ws://localhost:5555/ws/events?topics=schedule.*,publish.*`);
  ws.onmessage = (e) => {
    const { event } = JSON.parse(e.data);
    if (event.topic === 'publish.completed') {
      // Refresh schedule or show toast
      toast.success(`Published to ${event.payload.platform}!`);
      refetchSchedule();
    }
  };
}, []);
```

---

### 4. **Event-Driven Caching**

**Problem:** Multiple components fetch same data repeatedly

**Solution:** Cache invalidation via events

```python
# When media is updated
await event_bus.publish(Topics.MEDIA_UPDATED, {"media_id": id})

# Cache subscriber
@event_bus.subscribe(Topics.MEDIA_UPDATED)
async def invalidate_cache(event):
    cache.delete(f"media:{event.payload['media_id']}")
```

---

### 5. **Saga Pattern for Complex Workflows**

**Current:** Publish workflow is linear, failures require manual recovery

**Improvement:** Use saga pattern for rollback

```
publish.requested → upload.started → upload.completed → submit.started → submit.completed
                          ↓                                    ↓
                   upload.failed                         submit.failed
                          ↓                                    ↓
                   (cleanup cloud)                      (cleanup blotato)
```

---

## 📊 Priority Implementation Order

| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| 1 | Media lifecycle events | Low | High - enables auto-analysis |
| 2 | Content posted events | Low | High - enables metrics fetch |
| 3 | Frontend WebSocket hooks | Medium | High - real-time UX |
| 4 | Experiment events | Medium | Medium - better A/B tracking |
| 5 | Account sync events | Low | Medium - better reliability |
| 6 | Metrics backfill worker | Medium | Medium - automated updates |
| 7 | Narrative→Schedule bridge | High | High - content strategy |

---

## Quick Wins (Can Do Now)

### 1. Emit `MEDIA_INGESTED` after upload
```python
# In media_processing_db.py after video insert
await event_bus.publish(Topics.MEDIA_INGESTED, {
    "media_id": str(video.id),
    "filename": video.file_name,
    "source_type": video.source_type
})
```

### 2. Emit `CONTENT_POSTED` after publish
```python
# In blotato_router.py after successful publish
await event_bus.publish("content.posted", {
    "media_id": media_id,
    "platform": platform,
    "platform_url": result.get("url"),
    "account_id": account_id
})
```

### 3. Add metrics fetch trigger
```python
# New worker that subscribes to content.posted
@event_bus.subscribe("content.posted")
async def auto_fetch_metrics(event):
    # Wait 5 minutes then fetch initial metrics
    await asyncio.sleep(300)
    await fetch_platform_metrics(event.payload["platform_url"])
```

---

## Summary

**Current coverage:** ~40% of operations emit events
**Target coverage:** 80%+ for all state-changing operations

**Key benefits of full pub/sub:**
1. **Decoupling** - Services don't need to know about each other
2. **Real-time UI** - WebSocket broadcasts all changes
3. **Audit trail** - All events logged with correlation IDs
4. **Retry/recovery** - Failed events go to DLQ for replay
5. **Extensibility** - Add new features by subscribing to existing events
