# PubSub Architecture Audit Report

> **Generated:** December 24, 2024
> **Scope:** Backend event bus, topics, workers, and subscriptions

---

## Executive Summary

The MediaPoster PubSub architecture has **88 defined topics** but only **~45 are actively used** in production code. This audit identifies gaps, inefficiencies, and opportunities for improvement.

**Overall Health:** 🟡 Good with room for improvement

---

## 1. Topic Usage Analysis

### ✅ Heavily Used Topics (5+ references)

| Topic | Usage Count | Status |
|-------|-------------|--------|
| `publish.completed` | 29 | ✅ Well integrated |
| `scheduler.tick` | 25 | ✅ Core scheduler |
| `publish.failed` | 15 | ✅ Error handling |
| `analysis.requested` | 13 | ✅ Analysis pipeline |
| `schedule.due` | 12 | ✅ Scheduler core |
| `publish.requested` | 12 | ✅ Publishing pipeline |
| `scheduler.started/stopped` | 19 | ✅ Worker lifecycle |
| `publish.started` | 9 | ✅ Progress tracking |
| `media.ingested` | 9 | ✅ Media pipeline |
| `analysis.completed` | 9 | ✅ Analysis pipeline |
| `clip.extraction.requested` | 7 | ✅ Clip pipeline |

### 🟡 Moderately Used Topics (2-4 references)

| Topic | Usage Count | Notes |
|-------|-------------|-------|
| `schedule.created/updated/cancelled` | 11 | Schedule CRUD |
| `metrics.updated` | 4 | Metrics pipeline |
| `analysis.started/failed` | 9 | Analysis lifecycle |
| `worker.started/stopped` | 6 | Worker management |
| `metrics.fetch.*` | 7 | Metrics fetching |
| `media.deleted` | 2 | Cleanup trigger |

### 🔴 Defined But NEVER Used (0 references)

| Topic | Category | Recommendation |
|-------|----------|----------------|
| `ai.generation.failed` | AI Gen | Implement in AI video generation |
| `ai.generation.progress` | AI Gen | Add progress tracking |
| `ai.generation.requested` | AI Gen | Add to generation endpoint |
| `ai.generation.started` | AI Gen | Add to generation worker |
| `metrics.aggregated` | Metrics | Add to aggregation service |
| `notification.created` | Notifications | Create notification worker |
| `notification.sent` | Notifications | Add delivery tracking |
| `publish.queued` | Publishing | Add queue step |
| `publish.retrying` | Publishing | Add retry logic |
| `mp.hydration.*` | Hydration | Not implemented |
| `mp.scheduler.cmd.*` | Scheduler | Use existing schedule.* instead |
| `mp.trends.*` | Trends | Trends feature incomplete |
| `mp.ui.*` | UI | Frontend not consuming |
| `mp.rules.evt.*` | Rules | KB rules incomplete |
| `system.health.check` | System | Add health check events |

---

## 2. Worker Subscription Analysis

### Active Workers & Their Subscriptions

| Worker | Subscribes To | Emits |
|--------|---------------|-------|
| **AnalysisWorker** | `analysis.requested` | `analysis.started/completed/failed`, `transcript.*`, `visual.*` |
| **PublishWorker** | `publish.requested`, `schedule.due` | `publish.*` (full lifecycle) |
| **SchedulerWorker** | `schedule.created/updated/cancelled` | `scheduler.*`, `schedule.due` |
| **MetricsFetchWorker** | `publish.completed` | `metrics.fetch.*`, `metrics.updated` |
| **CleanupWorker** | `media.deleted` | (cleanup actions) |
| **MetricsBackfillWorker** | `metrics.fetch.requested` | `metrics.*` |
| **ExperimentTrackerWorker** | `publish.completed`, `metrics.updated` | `experiment.variant.*` |
| **ClipExtractionWorker** | `clip.extraction.requested` | `clip.extraction.*` |

### ❌ Missing Workers (Topics with no subscribers)

| Topic Pattern | Suggested Worker |
|---------------|------------------|
| `ai.generation.*` | AIGenerationWorker |
| `notification.*` | NotificationWorker |
| `mp.trends.*` | TrendsWorker |
| `mp.narrative.cmd.*` | NarrativeWorker |

---

## 3. Identified Gaps & Inefficiencies

### 🔴 HIGH Priority Gaps

1. **AI Video Generation Pipeline**
   - Topics defined but not emitted
   - No worker consuming `ai.generation.requested`
   - **Fix:** Add events in `ai_video_generation.py`

2. **Notification System**
   - `notification.created/sent` defined but never used
   - No notification delivery worker
   - **Fix:** Create `NotificationWorker` subscribing to key events

3. **Duplicate Topic Naming**
   - `schedule.*` vs `mp.scheduler.*` - confusing overlap
   - `media.analysis.*` vs `analysis.*` inconsistent
   - **Fix:** Deprecate `mp.scheduler.*`, use `schedule.*`

### 🟡 MEDIUM Priority Gaps

4. **Trends Pipeline Not Implemented**
   - 8 `mp.trends.*` topics defined but unused
   - Trend detection feature incomplete
   - **Fix:** Implement TrendsWorker or remove dead topics

5. **UI Events Not Connected**
   - `mp.ui.evt.toast/invalidate/activity` not used
   - Frontend not subscribing to these
   - **Fix:** Connect frontend WebSocket to these topics

6. **Health Check Not Implemented**
   - `system.health.check` defined but never emitted
   - No periodic health monitoring
   - **Fix:** Add to scheduler heartbeat

### 🟢 LOW Priority Gaps

7. **Hydration Events Unused**
   - `mp.hydration.*` topics not implemented
   - Feature may be deprecated/unused

8. **Rules Events Incomplete**
   - `mp.rules.evt.rule_updated/deprecated/template_created` not used
   - Only `rule_created` (via `KNOWLEDGE_BASE_RULE_APPLIED`)

---

## 4. Efficiency Issues

### Inefficiency 1: Event Bus Singleton Access

**Current Pattern (inefficient):**
```python
event_bus = EventBus.get_instance()
await event_bus.publish(...)
```

**Recommended Pattern:**
```python
# Inject once at module level
from services.event_bus import event_bus
await event_bus.publish(...)
```

### Inefficiency 2: asyncio.create_task for Fire-and-Forget

**Current Pattern (some endpoints):**
```python
asyncio.create_task(event_bus.publish(...))
```

**Issue:** Task may be garbage collected before completion

**Recommended:**
```python
# For critical events, await directly
await event_bus.publish(...)

# For non-critical, use background tasks
background_tasks.add_task(emit_event, topic, payload)
```

### Inefficiency 3: Missing Correlation IDs

**Issue:** Many events don't pass correlation IDs, breaking traceability

**Current:**
```python
await event_bus.publish(Topics.MEDIA_INGESTED, {"media_id": id})
```

**Recommended:**
```python
await event_bus.publish(Topics.MEDIA_INGESTED, {"media_id": id}, correlation_id=request_id)
```

---

## 5. Recommendations

### Immediate Actions (HIGH)

1. **Add AI Generation Events**
   - File: `api/endpoints/ai_video_generation.py`
   - Add: `AI_GENERATION_REQUESTED`, `STARTED`, `PROGRESS`, `COMPLETED`, `FAILED`

2. **Create NotificationWorker**
   - Subscribe to: `publish.completed`, `publish.failed`, `analysis.completed`
   - Emit: `notification.created`, `notification.sent`

3. **Clean Up Duplicate Topics**
   - Deprecate `mp.scheduler.*` in favor of `schedule.*`
   - Document which topics are canonical

### Short-term Actions (MEDIUM)

4. **Implement UI Toast Events**
   - Frontend: Subscribe to `mp.ui.evt.toast` via WebSocket
   - Backend: Emit toast events on key actions

5. **Add Retry Events**
   - Emit `publish.retrying` in `PublishWorker` retry logic
   - Track retry counts in event payload

6. **Health Check Integration**
   - Emit `system.health.check` every 60s from scheduler
   - Include worker status, queue depths

### Long-term Actions (LOW)

7. **Trends Pipeline**
   - Either implement TrendsWorker or remove 8 unused topics
   - Connect to external trend APIs

8. **Hydration Feature**
   - Evaluate if `mp.hydration.*` is needed
   - Remove if feature abandoned

---

## 6. Topic Naming Convention Violations

| Current | Issue | Suggested |
|---------|-------|-----------|
| `mp.experiments.cmd.plan_run` | Inconsistent with other topics | `experiment.run.requested` |
| `mp.narrative.evt.plan_generated` | Too verbose | `narrative.plan.generated` |
| `mp.rules.evt.rule_created` | Redundant prefix | `rules.created` |
| `mp.scheduler.cmd.create_items` | Conflicts with `schedule.*` | Remove/deprecate |

**Standard Convention:** `{domain}.{entity}.{action}`
- `media.analysis.completed` ✅
- `mp.experiments.evt.run_started` ❌ (non-standard prefix)

---

## 7. Coverage Summary

| Category | Defined | Used | Coverage |
|----------|---------|------|----------|
| Media Lifecycle | 4 | 4 | 100% |
| Analysis Pipeline | 13 | 10 | 77% |
| Publishing | 11 | 9 | 82% |
| Scheduling | 12 | 7 | 58% |
| Metrics | 5 | 4 | 80% |
| AI Generation | 5 | 1 | 20% |
| Clip Extraction | 9 | 9 | 100% |
| Notifications | 2 | 0 | 0% |
| Trends | 8 | 0 | 0% |
| UI Events | 3 | 0 | 0% |
| System | 5 | 4 | 80% |
| **TOTAL** | **88** | **~52** | **~59%** |

---

## 8. Next Steps

1. ✅ Review this audit with the team
2. 🔲 Prioritize HIGH gaps for immediate implementation
3. 🔲 Create tickets for MEDIUM gaps
4. 🔲 Decide on deprecating unused topics
5. 🔲 Update `topics.py` with deprecation markers
6. 🔲 Re-audit in 30 days to measure improvement

---

*Generated by PubSub Architecture Audit Tool*
