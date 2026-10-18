# 🚀 Pub/Sub Architecture Improvements

**Analysis of gaps and inefficiencies that could be improved through event-driven architecture**

---

## 📊 Current State

### ✅ What Exists

1. **Event Bus Infrastructure**
   - `Backend/services/event_bus/` - In-memory event bus
   - Redis adapter available (`redis_adapter.py`)
   - Topic registry (`topics.py`) with 50+ topics
   - WebSocket support for real-time frontend updates

2. **Services Using Events**
   - `PostScheduler` - Publishes `schedule.due`, `publish.*` events
   - `SchedulerWorker` - Emits `schedule.due` events
   - `PublishWorker` - Handles publish events
   - `AnalysisWorker` - Handles analysis events

3. **WebSocket Integration**
   - `/api/websocket` endpoint for real-time updates
   - `useEventStream` hook in frontend
   - Connection manager for topic filtering

---

## 🔍 Identified Gaps & Inefficiencies

### 1. **Frontend Polling Instead of Real-Time Events** ⚠️ HIGH PRIORITY

**Problem:**
- Frontend polls for analysis completion every 2 seconds
- Frontend polls for publish status
- Frontend polls for analytics updates
- Wastes resources, creates latency

**Current Implementation:**
```typescript
// dashboard/app/(dashboard)/media/[id]/page.tsx
while (attempts < maxAttempts) {
  await new Promise(resolve => setTimeout(resolve, 2000));
  const res = await fetch(`${DB_API_URL}/analysis/${media.media_id}`);
  // Check if complete...
}
```

**Improvement:**
```typescript
// Subscribe to analysis events via WebSocket
useEventStream({
  topics: [`media.analysis.${mediaId}`, 'media.analysis.completed'],
  onEvent: (event) => {
    if (event.topic === 'media.analysis.completed' && event.media_id === mediaId) {
      setAnalysisComplete(true);
    }
  }
});
```

**Topics Needed:**
- `media.analysis.{media_id}.progress` - Progress updates
- `media.analysis.{media_id}.completed` - Completion
- `publish.{post_id}.status` - Publish status updates
- `analytics.{account_id}.updated` - Analytics refresh

**Impact:** 
- ⚡ Eliminates polling overhead
- 📉 Reduces API load by 90%+
- ⏱️ Real-time updates (0ms latency vs 2s polling)

---

### 2. **Direct Service Calls Instead of Events** ⚠️ MEDIUM PRIORITY

**Problem:**
Services directly import and call each other, creating tight coupling:

```python
# Backend/api/blotato_router.py
from services.publish_service import get_publish_service
publish_service = get_publish_service()
result = await publish_service.full_publish_flow(...)
```

**Current Tight Coupling:**
- `blotato_router.py` → directly calls `publish_service`
- `narrative_scheduler` → directly calls `DirectorService`
- `content_orchestration` → directly calls multiple services
- `data_hydration_service` → directly calls orchestrator

**Improvement:**
```python
# Publish event instead of direct call
await event_bus.publish(Topics.PUBLISH_REQUESTED, {
    "media_id": media_id,
    "platform": platform,
    "account_id": account_id
})

# Service subscribes to event
@event_bus.subscribe(Topics.PUBLISH_REQUESTED)
async def handle_publish_request(event):
    result = await publish_service.full_publish_flow(...)
    await event_bus.publish(Topics.PUBLISH_COMPLETED, result)
```

**Benefits:**
- 🔌 Loose coupling - services don't know about each other
- 🔄 Easy to add new subscribers (logging, analytics, notifications)
- 🧪 Easier testing - mock events instead of services
- 📈 Better scalability - can add multiple workers

---

### 3. **Synchronous Batch Operations** ⚠️ MEDIUM PRIORITY

**Problem:**
Batch operations run sequentially, blocking other work:

```python
# Backend/scripts/import_and_analyze_for_month.py
for video in videos:
    await ingest_video(video)  # Blocks until complete
    await analyze_video(video)  # Blocks until complete
```

**Current Issues:**
- `import_and_analyze_for_month.py` - Sequential processing
- `batch_processor.py` - Processes one at a time
- Analytics refresh - Sequential account fetching

**Improvement:**
```python
# Emit events for parallel processing
for video in videos:
    await event_bus.publish(Topics.MEDIA_INGEST_REQUESTED, {
        "file_path": video.path,
        "priority": "normal"
    })

# Workers process in parallel
@event_bus.subscribe(Topics.MEDIA_INGEST_REQUESTED)
async def ingest_worker(event):
    await ingest_video(event.file_path)
    await event_bus.publish(Topics.MEDIA_INGESTED, {...})
```

**Benefits:**
- ⚡ Parallel processing - 10x faster
- 📊 Better resource utilization
- 🔄 Automatic retry via dead-letter queue
- 📈 Horizontal scaling - add more workers

---

### 4. **No Event-Driven Analytics Updates** ⚠️ HIGH PRIORITY

**Problem:**
Analytics are fetched on-demand, not event-driven:

```typescript
// dashboard/app/(dashboard)/analytics/page.tsx
const fetchAnalytics = async () => {
  const res = await fetch(`${API_URL}/api/social-analytics/overview`);
  // Manual refresh required
};
```

**Current Flow:**
1. User clicks "Refresh"
2. Frontend calls API
3. Backend fetches from third-party APIs
4. Updates database
5. Returns to frontend

**Improvement:**
```python
# Backend automatically refreshes analytics
@event_bus.subscribe(Topics.PUBLISH_COMPLETED)
async def refresh_analytics_on_publish(event):
    # Trigger analytics refresh for this account
    await event_bus.publish(Topics.ANALYTICS_REFRESH_REQUESTED, {
        "account_id": event.account_id,
        "platform": event.platform
    })

# Frontend subscribes to updates
useEventStream({
  topics: ['analytics.*.updated'],
  onEvent: (event) => {
    updateAnalyticsInUI(event.data);
  }
});
```

**Benefits:**
- 🔄 Automatic updates when posts are published
- ⚡ Real-time analytics without manual refresh
- 📊 Always up-to-date data
- 🎯 Targeted updates (only changed accounts)

---

### 5. **No Event Replay/History** ⚠️ LOW PRIORITY

**Problem:**
Events are logged but not queryable or replayable:

```python
# Backend/services/event_bus/bus.py
self._event_log: List[Event] = []  # In-memory only
self._max_log_size = 1000  # Limited history
```

**Current Limitations:**
- Events lost on restart
- Can't query past events
- Can't replay for debugging
- No event sourcing

**Improvement:**
```python
# Store events in database
@event_bus.subscribe("*")  # Subscribe to all events
async def persist_event(event):
    await db.execute("""
        INSERT INTO event_history (topic, payload, timestamp)
        VALUES (:topic, :payload, :timestamp)
    """, {
        "topic": event.topic,
        "payload": json.dumps(event.payload),
        "timestamp": event.timestamp
    })

# Replay events
async def replay_events(topic: str, since: datetime):
    events = await db.execute("""
        SELECT * FROM event_history
        WHERE topic = :topic AND timestamp >= :since
        ORDER BY timestamp
    """)
    for event in events:
        await event_bus.replay(event)
```

**Benefits:**
- 🔍 Debugging - see what happened
- 🔄 Recovery - replay failed events
- 📊 Analytics - analyze event patterns
- 🕐 Audit trail - compliance

---

### 6. **No Event-Driven Notifications** ⚠️ MEDIUM PRIORITY

**Problem:**
No pub/sub for user notifications:

```python
# Currently: Direct database writes
await db.execute("""
    INSERT INTO notifications (user_id, message)
    VALUES (:user_id, :message)
""")
```

**Improvement:**
```python
# Emit notification events
await event_bus.publish(Topics.NOTIFICATION_CREATED, {
    "user_id": user_id,
    "type": "publish_completed",
    "message": "Post published successfully",
    "metadata": {"post_id": post_id, "platform_url": url}
})

# Multiple subscribers
@event_bus.subscribe(Topics.NOTIFICATION_CREATED)
async def send_email_notification(event):
    if event.type == "publish_completed":
        await email_service.send(...)

@event_bus.subscribe(Topics.NOTIFICATION_CREATED)
async def send_push_notification(event):
    await push_service.send(...)

@event_bus.subscribe(Topics.NOTIFICATION_CREATED)
async def store_notification(event):
    await db.execute("INSERT INTO notifications ...")
```

**Benefits:**
- 🔔 Multiple notification channels (email, push, in-app)
- 🔌 Easy to add new channels
- 📊 Notification analytics
- 🎯 Targeted notifications

---

### 7. **No Event-Driven Thumbnail Generation** ⚠️ LOW PRIORITY

**Problem:**
Thumbnails generated on-demand, blocking requests:

```python
# Backend/services/media_provider.py
async def get_thumbnail_response(...):
    # Generate on-the-fly if missing
    thumb_path = generate_thumbnail(file_path, size)
```

**Improvement:**
```python
# Emit event when media is ingested
@event_bus.subscribe(Topics.MEDIA_INGESTED)
async def generate_thumbnails(event):
    await event_bus.publish(Topics.THUMBNAIL_GENERATION_REQUESTED, {
        "media_id": event.media_id,
        "sizes": ["small", "medium", "large"]
    })

# Worker generates thumbnails
@event_bus.subscribe(Topics.THUMBNAIL_GENERATION_REQUESTED)
async def thumbnail_worker(event):
    for size in event.sizes:
        thumb = await generate_thumbnail(event.media_id, size)
        await event_bus.publish(Topics.THUMBNAIL_READY, {
            "media_id": event.media_id,
            "size": size,
            "path": thumb
        })
```

**Benefits:**
- ⚡ Non-blocking - thumbnails ready before needed
- 📊 Better UX - no waiting for generation
- 🔄 Automatic retry on failure
- 📈 Parallel generation for multiple sizes

---

### 8. **No Event-Driven Experiment Tracking** ⚠️ MEDIUM PRIORITY

**Problem:**
Experiment results updated manually:

```python
# Currently: Direct database updates
await db.execute("""
    UPDATE experiments
    SET results = :results
    WHERE id = :id
""")
```

**Improvement:**
```python
# Emit events when analytics are fetched
@event_bus.subscribe(Topics.ANALYTICS_UPDATED)
async def update_experiments(event):
    # Find experiments using this post
    experiments = await find_experiments_for_post(event.post_id)
    for exp in experiments:
        await event_bus.publish(Topics.EXPERIMENT_METRIC_RECORDED, {
            "experiment_id": exp.id,
            "variant": exp.variant,
            "metrics": event.metrics
        })
```

**Benefits:**
- 🔄 Automatic experiment tracking
- 📊 Real-time experiment results
- 🎯 A/B test winner detection
- 📈 Statistical significance calculations

---

### 9. **No Event-Driven Content Recommendations** ⚠️ LOW PRIORITY

**Problem:**
Recommendations generated on-demand:

```python
# Backend/services/ai_recommendation_service.py
async def generate_daily_recommendations(user_id):
    # Heavy computation on every request
    recommendations = await compute_recommendations(...)
```

**Improvement:**
```python
# Pre-compute recommendations on schedule
@event_bus.subscribe(Topics.ANALYTICS_UPDATED)
async def trigger_recommendation_update(event):
    await event_bus.publish(Topics.RECOMMENDATIONS_REFRESH_REQUESTED, {
        "user_id": event.user_id,
        "trigger": "analytics_updated"
    })

# Worker generates recommendations
@event_bus.subscribe(Topics.RECOMMENDATIONS_REFRESH_REQUESTED)
async def recommendation_worker(event):
    recommendations = await compute_recommendations(event.user_id)
    await event_bus.publish(Topics.RECOMMENDATIONS_READY, {
        "user_id": event.user_id,
        "recommendations": recommendations
    })
```

**Benefits:**
- ⚡ Faster response - pre-computed
- 📊 Always fresh recommendations
- 🔄 Automatic updates when data changes
- 📈 Better user experience

---

### 10. **No Event-Driven Narrative Builder Updates** ⚠️ MEDIUM PRIORITY

**Problem:**
Narrative builder manually refreshes:

```typescript
// dashboard/app/(dashboard)/narrative-builder/page.tsx
const fetchSignals = async () => {
  const res = await fetch(`${API_URL}/api/narrative-builder/signals`);
  // Manual refresh
};
```

**Improvement:**
```python
# Emit events when content is published
@event_bus.subscribe(Topics.PUBLISH_COMPLETED)
async def update_narrative_signals(event):
    await event_bus.publish(Topics.NARRATIVE_SIGNALS_UPDATED, {
        "goal_id": event.goal_id,
        "new_post": event.post_id
    })
```

**Benefits:**
- 🔄 Automatic narrative updates
- 📊 Real-time content signals
- 🎯 Better content planning
- 📈 Improved recommendations

---

## 🎯 Implementation Priority

### Phase 1: High Impact, Low Effort (Week 1)
1. ✅ **Frontend Real-Time Updates** - Replace polling with WebSocket events
2. ✅ **Event-Driven Analytics** - Auto-refresh on publish

### Phase 2: Medium Impact, Medium Effort (Week 2-3)
3. ✅ **Decouple Services** - Replace direct calls with events
4. ✅ **Parallel Batch Processing** - Event-driven workers
5. ✅ **Event-Driven Notifications** - Multi-channel notifications

### Phase 3: Lower Priority (Week 4+)
6. ✅ **Event History/Replay** - Persist events to database
7. ✅ **Event-Driven Thumbnails** - Pre-generate on ingest
8. ✅ **Event-Driven Experiments** - Auto-track results
9. ✅ **Event-Driven Recommendations** - Pre-compute suggestions
10. ✅ **Event-Driven Narrative Builder** - Auto-update signals

---

## 📋 New Topics Needed

```python
# Add to Backend/services/event_bus/topics.py

# Analytics
ANALYTICS_REFRESH_REQUESTED = "analytics.refresh.requested"
ANALYTICS_UPDATED = "analytics.updated"
ANALYTICS_ACCOUNT_UPDATED = "analytics.account.{account_id}.updated"

# Notifications
NOTIFICATION_CREATED = "notification.created"
NOTIFICATION_SENT = "notification.sent"

# Thumbnails
THUMBNAIL_GENERATION_REQUESTED = "thumbnail.generation.requested"
THUMBNAIL_READY = "thumbnail.ready"

# Experiments
EXPERIMENT_METRIC_RECORDED = "experiment.metric.recorded"
EXPERIMENT_WINNER_DETECTED = "experiment.winner.detected"

# Recommendations
RECOMMENDATIONS_REFRESH_REQUESTED = "recommendations.refresh.requested"
RECOMMENDATIONS_READY = "recommendations.ready"

# Narrative Builder
NARRATIVE_SIGNALS_UPDATED = "narrative.signals.updated"
NARRATIVE_GOAL_PROGRESS_UPDATED = "narrative.goal.progress.updated"
```

---

## 🔧 Implementation Example

### Before (Direct Call):
```python
# Backend/api/endpoints/schedule.py
from services.background_publisher import get_background_publisher

publisher = get_background_publisher()
result = await publisher.publish(request)
```

### After (Event-Driven):
```python
# Backend/api/endpoints/schedule.py
from services.event_bus import EventBus, Topics

event_bus = EventBus.get_instance()
await event_bus.publish(Topics.PUBLISH_REQUESTED, {
    "media_id": request.media_id,
    "platform": request.platform,
    "account_id": request.account_id
})

# Service subscribes
@event_bus.subscribe(Topics.PUBLISH_REQUESTED)
async def handle_publish(event):
    publisher = get_background_publisher()
    result = await publisher.publish(...)
    await event_bus.publish(Topics.PUBLISH_COMPLETED, result)
```

---

## 📊 Expected Benefits

| Improvement | Performance Gain | Resource Savings | User Experience |
|-------------|------------------|------------------|-----------------|
| Real-time updates | 90% less API calls | 80% less server load | Instant feedback |
| Parallel processing | 10x faster batches | Better CPU usage | Faster workflows |
| Event-driven analytics | Auto-updates | No manual refresh | Always current |
| Decoupled services | Easier scaling | Better testability | More reliable |

---

## 🚀 Next Steps

1. **Audit current polling** - Identify all polling locations
2. **Add WebSocket subscriptions** - Replace polling with events
3. **Decouple services** - Replace direct calls with events
4. **Add event persistence** - Store events in database
5. **Add event replay** - Enable debugging/recovery

---

**Last Updated:** December 24, 2025

