# Event-Driven Architecture PRD
## Topic-Based Pub/Sub for Long-Running Workflows

**Version:** 1.0  
**Date:** December 22, 2025  
**Status:** Draft  

---

## Executive Summary

This PRD outlines the implementation of a **topic-based publish/subscribe (pub/sub) architecture** for MediaPoster's long-running workflows. The goal is to enable loosely-coupled, asynchronous communication between services, improving scalability, observability, and fault tolerance for multi-threaded processing pipelines.

---

## Problem Statement

### Current Challenges
1. **Tight Coupling** - Services directly call each other, creating dependencies
2. **Long Processing Times** - Video analysis, AI generation, and publishing can take 1-30+ minutes
3. **No Visibility** - Hard to track progress of multi-step workflows
4. **Retry Complexity** - Failed steps require custom retry logic per service
5. **Scaling Limitations** - Cannot easily scale individual workflow steps
6. **Blocking Operations** - Frontend waits for long operations to complete

### Current Long-Running Workflows
| Workflow | Duration | Steps |
|----------|----------|-------|
| Video Analysis | 2-5 min | Transcript → Visual → AI Analysis → Platform Content |
| Content Publishing | 30s-3 min | Upload → Blotato → Platform → Poll URL |
| Bulk Import | 5-30 min | Scan → Metadata → Thumbnails → DB Insert |
| Metrics Backfill | 2-10 min | Fetch → Parse → Store → Aggregate |
| AI Video Generation | 5-15 min | Prompt → Generate → Download → Process |

---

## Proposed Solution

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EVENT BUS (Message Broker)                          │
│                                                                             │
│  Topics:                                                                    │
│  ├── media.ingested          (new video added)                             │
│  ├── media.analysis.started  (analysis began)                              │
│  ├── media.analysis.completed (analysis finished)                          │
│  ├── media.analysis.failed   (analysis error)                              │
│  ├── publish.requested       (user/scheduler requests publish)             │
│  ├── publish.uploading       (uploading to cloud/blotato)                  │
│  ├── publish.submitted       (sent to platform)                            │
│  ├── publish.completed       (URL obtained)                                │
│  ├── publish.failed          (publish error)                               │
│  ├── metrics.fetch.requested (backfill request)                            │
│  ├── metrics.updated         (new metrics available)                       │
│  ├── ai.generation.requested (AI video request)                            │
│  ├── ai.generation.completed (AI video ready)                              │
│  └── scheduler.tick          (periodic scheduler heartbeat)                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
        │                    │                    │                    │
        ▼                    ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│   Ingestion  │    │   Analysis   │    │   Publisher  │    │   Metrics    │
│   Worker     │    │   Worker     │    │   Worker     │    │   Worker     │
├──────────────┤    ├──────────────┤    ├──────────────┤    ├──────────────┤
│ Subscribes:  │    │ Subscribes:  │    │ Subscribes:  │    │ Subscribes:  │
│ - file.added │    │ - media.     │    │ - publish.   │    │ - metrics.   │
│              │    │   ingested   │    │   requested  │    │   fetch.req  │
│ Publishes:   │    │ Publishes:   │    │ Publishes:   │    │ Publishes:   │
│ - media.     │    │ - analysis.  │    │ - publish.   │    │ - metrics.   │
│   ingested   │    │   completed  │    │   completed  │    │   updated    │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
```

### Message Structure

```python
@dataclass
class Event:
    id: str                    # UUID for deduplication
    topic: str                 # e.g., "media.analysis.completed"
    timestamp: datetime        # When event was created
    source: str                # Service that created event
    correlation_id: str        # Links related events in a workflow
    payload: Dict[str, Any]    # Event-specific data
    metadata: Dict[str, Any]   # Tracing, retry info, etc.

# Example Event
{
    "id": "evt_abc123",
    "topic": "publish.completed",
    "timestamp": "2025-12-22T19:25:19Z",
    "source": "publisher-worker",
    "correlation_id": "workflow_xyz789",
    "payload": {
        "media_id": "8d978df0-429c-4df7-a521-2db44c1a34dd",
        "platform": "instagram",
        "platform_url": "https://instagram.com/reel/DSksR59ji2l/",
        "submission_id": "4c57d422-5736-42ee-b99a-f686495207e7"
    },
    "metadata": {
        "attempt": 1,
        "duration_ms": 45000,
        "worker_id": "publisher-01"
    }
}
```

---

## Implementation Phases

### Phase 1: Event Bus Foundation (Week 1-2)

**Goal:** Establish the core messaging infrastructure

**Components:**
1. **EventBus Class** - Central message broker
2. **Event Model** - Standardized event structure
3. **Topic Registry** - Define all topics
4. **In-Memory Implementation** - For single-instance dev

```python
# Backend/services/event_bus.py

class EventBus:
    """
    Topic-based pub/sub event bus.
    Allows services to communicate asynchronously via topics.
    """
    
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._event_log: List[Event] = []
        self._dead_letter_queue: List[Event] = []
    
    async def publish(self, topic: str, payload: Dict, correlation_id: str = None) -> str:
        """Publish an event to a topic"""
        event = Event(
            id=str(uuid4()),
            topic=topic,
            timestamp=datetime.utcnow(),
            source=self._get_source(),
            correlation_id=correlation_id or str(uuid4()),
            payload=payload
        )
        
        self._event_log.append(event)
        await self._dispatch(event)
        return event.id
    
    def subscribe(self, topic: str, handler: Callable):
        """Subscribe a handler to a topic (supports wildcards)"""
        self._subscribers[topic].append(handler)
    
    async def _dispatch(self, event: Event):
        """Dispatch event to all matching subscribers"""
        for pattern, handlers in self._subscribers.items():
            if self._matches(pattern, event.topic):
                for handler in handlers:
                    try:
                        await handler(event)
                    except Exception as e:
                        self._dead_letter_queue.append(event)
                        logger.error(f"Handler failed: {e}")
```

**Topics to Define:**
```python
class Topics:
    # Media Lifecycle
    MEDIA_INGESTED = "media.ingested"
    MEDIA_DELETED = "media.deleted"
    
    # Analysis Pipeline
    ANALYSIS_REQUESTED = "media.analysis.requested"
    ANALYSIS_STARTED = "media.analysis.started"
    ANALYSIS_PROGRESS = "media.analysis.progress"
    ANALYSIS_COMPLETED = "media.analysis.completed"
    ANALYSIS_FAILED = "media.analysis.failed"
    
    # Publishing Pipeline
    PUBLISH_REQUESTED = "publish.requested"
    PUBLISH_UPLOADING = "publish.uploading"
    PUBLISH_SUBMITTED = "publish.submitted"
    PUBLISH_POLLING = "publish.polling"
    PUBLISH_COMPLETED = "publish.completed"
    PUBLISH_FAILED = "publish.failed"
    
    # Scheduling
    SCHEDULE_CREATED = "schedule.created"
    SCHEDULE_DUE = "schedule.due"
    SCHEDULER_TICK = "scheduler.tick"
    
    # Metrics
    METRICS_FETCH_REQUESTED = "metrics.fetch.requested"
    METRICS_UPDATED = "metrics.updated"
    
    # AI Generation
    AI_GENERATION_REQUESTED = "ai.generation.requested"
    AI_GENERATION_PROGRESS = "ai.generation.progress"
    AI_GENERATION_COMPLETED = "ai.generation.completed"
    AI_GENERATION_FAILED = "ai.generation.failed"
```

---

### Phase 2: Worker Pattern (Week 2-3)

**Goal:** Create reusable worker base class for long-running processors

```python
# Backend/services/workers/base_worker.py

class BaseWorker(ABC):
    """
    Base class for event-driven workers.
    Handles subscription, processing, and error handling.
    """
    
    def __init__(self, event_bus: EventBus, worker_id: str = None):
        self.event_bus = event_bus
        self.worker_id = worker_id or f"{self.__class__.__name__}-{uuid4().hex[:8]}"
        self.is_running = False
        self._setup_subscriptions()
    
    @abstractmethod
    def get_subscriptions(self) -> List[str]:
        """Return list of topics this worker subscribes to"""
        pass
    
    @abstractmethod
    async def handle_event(self, event: Event) -> None:
        """Process a received event"""
        pass
    
    def _setup_subscriptions(self):
        for topic in self.get_subscriptions():
            self.event_bus.subscribe(topic, self._wrapped_handler)
    
    async def _wrapped_handler(self, event: Event):
        """Wrapper that adds logging, metrics, and error handling"""
        start = time.time()
        logger.info(f"[{self.worker_id}] 📥 Received: {event.topic}")
        
        try:
            await self.handle_event(event)
            duration = time.time() - start
            logger.info(f"[{self.worker_id}] ✅ Completed in {duration:.2f}s")
        except Exception as e:
            logger.error(f"[{self.worker_id}] ❌ Failed: {e}")
            await self._handle_failure(event, e)
    
    async def emit(self, topic: str, payload: Dict, correlation_id: str = None):
        """Convenience method to publish events"""
        return await self.event_bus.publish(
            topic=topic,
            payload=payload,
            correlation_id=correlation_id
        )
```

**Example: Analysis Worker**
```python
class AnalysisWorker(BaseWorker):
    """Handles video analysis pipeline"""
    
    def get_subscriptions(self) -> List[str]:
        return [
            Topics.MEDIA_INGESTED,
            Topics.ANALYSIS_REQUESTED
        ]
    
    async def handle_event(self, event: Event) -> None:
        media_id = event.payload.get("media_id")
        
        # Emit progress updates
        await self.emit(Topics.ANALYSIS_STARTED, {
            "media_id": media_id,
            "step": "transcript"
        }, event.correlation_id)
        
        # Run analysis steps...
        transcript = await self._run_transcript(media_id)
        
        await self.emit(Topics.ANALYSIS_PROGRESS, {
            "media_id": media_id,
            "step": "visual",
            "progress": 33
        }, event.correlation_id)
        
        visual = await self._run_visual_analysis(media_id)
        
        await self.emit(Topics.ANALYSIS_PROGRESS, {
            "media_id": media_id,
            "step": "ai_analysis",
            "progress": 66
        }, event.correlation_id)
        
        analysis = await self._run_ai_analysis(media_id, transcript, visual)
        
        # Emit completion
        await self.emit(Topics.ANALYSIS_COMPLETED, {
            "media_id": media_id,
            "analysis": analysis
        }, event.correlation_id)
```

---

### Phase 3: Workflow Orchestration (Week 3-4)

**Goal:** Track multi-step workflows and provide visibility

```python
# Backend/services/workflow_manager.py

class WorkflowManager:
    """
    Tracks workflow state across multiple events.
    Provides visibility into long-running processes.
    """
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self.workflows: Dict[str, Workflow] = {}
        self._subscribe_to_all()
    
    def _subscribe_to_all(self):
        """Subscribe to all topics to track workflow state"""
        self.event_bus.subscribe("*", self._track_event)
    
    async def _track_event(self, event: Event):
        """Update workflow state based on event"""
        cid = event.correlation_id
        
        if cid not in self.workflows:
            self.workflows[cid] = Workflow(id=cid)
        
        workflow = self.workflows[cid]
        workflow.events.append(event)
        workflow.last_updated = event.timestamp
        workflow.current_step = self._infer_step(event.topic)
        
        if event.topic.endswith(".completed"):
            workflow.status = "completed"
        elif event.topic.endswith(".failed"):
            workflow.status = "failed"
        else:
            workflow.status = "in_progress"
    
    def get_workflow_status(self, correlation_id: str) -> Dict:
        """Get current status of a workflow"""
        workflow = self.workflows.get(correlation_id)
        if not workflow:
            return {"status": "not_found"}
        
        return {
            "id": workflow.id,
            "status": workflow.status,
            "current_step": workflow.current_step,
            "events": len(workflow.events),
            "duration_ms": workflow.duration_ms,
            "last_updated": workflow.last_updated.isoformat()
        }
```

---

### Phase 4: Frontend Integration (Week 4-5)

**Goal:** Real-time workflow visibility via WebSocket

```typescript
// Frontend: useWorkflowStatus hook
const useWorkflowStatus = (correlationId: string) => {
  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  
  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:5555/ws/workflow/${correlationId}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data);
      
      // Show toast on step completion
      if (data.type === 'step_completed') {
        toast.success(`${data.step} completed`);
      }
    };
    
    return () => ws.close();
  }, [correlationId]);
  
  return status;
};

// Usage in component
const PublishingStatus = ({ mediaId }) => {
  const { status, currentStep, progress, events } = useWorkflowStatus(mediaId);
  
  return (
    <div className="workflow-tracker">
      <ProgressBar value={progress} />
      <StepIndicator steps={[
        { name: 'Upload to Cloud', status: getStepStatus('upload') },
        { name: 'Upload to Blotato', status: getStepStatus('blotato') },
        { name: 'Publish to Platform', status: getStepStatus('publish') },
        { name: 'Get URL', status: getStepStatus('polling') },
      ]} />
      <EventLog events={events} />
    </div>
  );
};
```

---

### Phase 5: Persistence & Scaling (Week 5-6)

**Goal:** Add Redis/PostgreSQL backing for production scale

**Options:**
1. **Redis Pub/Sub** - Simple, fast, no persistence
2. **Redis Streams** - Persistent, consumer groups, replay
3. **PostgreSQL LISTEN/NOTIFY** - Already have Postgres, simple
4. **RabbitMQ** - Full-featured, complex
5. **Kafka** - Enterprise scale, overkill for us

**Recommended: Redis Streams**
```python
class RedisEventBus(EventBus):
    """Redis Streams-backed event bus for production"""
    
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        self.consumer_group = "mediaposter-workers"
    
    async def publish(self, topic: str, payload: Dict, correlation_id: str = None):
        event = self._create_event(topic, payload, correlation_id)
        
        # Add to Redis stream
        await self.redis.xadd(
            f"events:{topic}",
            {"data": json.dumps(event.dict())}
        )
        
        return event.id
    
    async def consume(self, topics: List[str], handler: Callable):
        """Consume events from topics with consumer group"""
        streams = {f"events:{t}": ">" for t in topics}
        
        while True:
            messages = await self.redis.xreadgroup(
                self.consumer_group,
                self.worker_id,
                streams,
                count=10,
                block=5000
            )
            
            for stream, items in messages:
                for item_id, data in items:
                    event = Event(**json.loads(data["data"]))
                    await handler(event)
                    await self.redis.xack(stream, self.consumer_group, item_id)
```

---

## API Endpoints

### Workflow Status API
```
GET /api/workflows/{correlation_id}
GET /api/workflows/{correlation_id}/events
GET /api/workflows/active
GET /api/workflows/failed

WebSocket /ws/workflow/{correlation_id}
```

### Event API (Debug/Admin)
```
GET /api/events/topics
GET /api/events/recent?topic={topic}&limit=50
GET /api/events/{event_id}
POST /api/events/replay/{event_id}
```

---

## Logging Format

Standardized log format for event tracing:

```
2025-12-22 14:25:19 | INFO | [publisher-01] 📤 publish.requested | cid=wf_abc123 | media_id=8d978df0
2025-12-22 14:25:20 | INFO | [publisher-01] ⬆️  publish.uploading | cid=wf_abc123 | step=gdrive
2025-12-22 14:25:25 | INFO | [publisher-01] ⬆️  publish.uploading | cid=wf_abc123 | step=blotato
2025-12-22 14:25:30 | INFO | [publisher-01] 📨 publish.submitted | cid=wf_abc123 | submission_id=4c57d422
2025-12-22 14:25:45 | INFO | [publisher-01] 🔍 publish.polling | cid=wf_abc123 | attempt=3/30
2025-12-22 14:26:15 | INFO | [publisher-01] ✅ publish.completed | cid=wf_abc123 | url=https://...
```

---

## Benefits

| Before | After |
|--------|-------|
| Direct service calls | Async event-driven |
| No visibility into long tasks | Real-time progress tracking |
| Custom retry per service | Unified retry/dead-letter handling |
| Hard to scale individual steps | Scale workers independently |
| Blocking API calls | Non-blocking with callbacks |
| Tightly coupled services | Loosely coupled via topics |

---

## Success Metrics

1. **Visibility** - 100% of long-running workflows trackable
2. **Reliability** - <1% failed events with retry mechanism
3. **Performance** - <100ms event dispatch latency
4. **Scalability** - Support 10x concurrent workflows
5. **Developer Experience** - Add new workflow in <1 hour

---

## Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| 1. Event Bus Foundation | Week 1-2 | EventBus class, Topics, In-memory impl |
| 2. Worker Pattern | Week 2-3 | BaseWorker, AnalysisWorker, PublishWorker |
| 3. Workflow Orchestration | Week 3-4 | WorkflowManager, Status API |
| 4. Frontend Integration | Week 4-5 | WebSocket, Progress UI, Event Log |
| 5. Persistence & Scaling | Week 5-6 | Redis Streams, Consumer Groups |
| 6. Migration | Week 6-7 | Migrate existing services to events |

---

## Files to Create

```
Backend/
├── services/
│   ├── event_bus/
│   │   ├── __init__.py
│   │   ├── event.py           # Event dataclass
│   │   ├── topics.py          # Topic constants
│   │   ├── bus.py             # EventBus base class
│   │   ├── memory_bus.py      # In-memory implementation
│   │   └── redis_bus.py       # Redis Streams implementation
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── base.py            # BaseWorker class
│   │   ├── analysis_worker.py
│   │   ├── publish_worker.py
│   │   ├── metrics_worker.py
│   │   └── ai_worker.py
│   └── workflow_manager.py    # Workflow tracking
├── api/
│   └── endpoints/
│       ├── workflows.py       # Workflow status API
│       └── events.py          # Event debug API
└── websockets/
    └── workflow_ws.py         # WebSocket for real-time updates
```

---

## Next Steps

1. **Review & Approve** this PRD
2. **Phase 1 Implementation** - Start with EventBus foundation
3. **Migrate PostScheduler** - First service to use events
4. **Add Analysis Pipeline** - Second major workflow
5. **Frontend Progress UI** - Real-time visibility

---

*Last Updated: December 22, 2025*
