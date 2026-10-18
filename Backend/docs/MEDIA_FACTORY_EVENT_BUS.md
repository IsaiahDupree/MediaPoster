# Media Factory Event Bus - Implementation Details

**Date:** December 26, 2024  
**Status:** Documented ✅

---

## 🚌 Event Bus Overview

The Media Factory uses an **event-driven architecture** with a central Event Bus for service communication.

### Two Backends

#### 1. In-Memory Event Bus (Default)
- **Location**: `Backend/services/event_bus/bus.py`
- **Transport**: Python in-memory dictionary
- **Use Case**: Development, single-process, testing

#### 2. Redis Streams Event Bus (Production)
- **Location**: `Backend/services/event_bus/redis_adapter.py`
- **Transport**: Redis Streams
- **Use Case**: Production, multi-server, distributed

---

## 📡 Transport Details

### In-Memory Event Bus

**Implementation:**
```python
class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._event_log: List[Event] = []
        self._dead_letter_queue: List[tuple[Event, Exception]] = []
```

**Characteristics:**
- **Storage**: Python dictionary (in-process memory)
- **Persistence**: None (lost on process restart)
- **Scalability**: Single process only
- **Latency**: Very low (< 1ms)
- **Throughput**: High (limited by Python GIL)

### Redis Streams Event Bus

**Implementation:**
```python
class RedisEventBus:
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or REDIS_URL
        self._redis = None  # Redis connection
```

**Characteristics:**
- **Storage**: Redis Streams (external Redis server)
- **Persistence**: Durable (survives restarts)
- **Scalability**: Multi-server, distributed
- **Latency**: Low (network round-trip, ~1-5ms)
- **Throughput**: Very high (Redis handles millions/sec)

**Stream Structure:**
```
mediaposter:events:{topic}  # One stream per topic
mediaposter:events:dlq       # Dead letter queue
```

**Consumer Groups:**
- Group: `mediaposter-workers`
- Consumers: Multiple workers can process same stream
- Auto-acknowledgment: Messages acked after successful processing

---

## 🔄 Delivery Guarantees

### At-Least-Once Delivery

**Both backends guarantee:**
- ✅ Events are delivered **at least once**
- ⚠️ Events may be delivered **multiple times** (duplicates possible)
- ❌ **Not exactly-once** (requires idempotent handlers)

**Why At-Least-Once:**
- Simpler implementation
- Handlers should be idempotent anyway
- Duplicate detection via idempotency keys

### Exactly-Once Delivery

**Not currently supported**, but can be achieved with:
1. **Idempotency keys** in handlers (already implemented)
2. **Deduplication** in event processing
3. **Transactional publishing** (future enhancement)

---

## 📊 Ordering Guarantees

### In-Memory Event Bus

**Per-Topic Ordering:**
- Events published to the **same topic** are processed **in order**
- Events to **different topics** may be processed **out of order**
- Handlers for same topic are called **sequentially**

**Example:**
```
Publish: tts.requested (id=1)
Publish: tts.requested (id=2)
Publish: music.requested (id=3)

Processing:
- tts.requested handlers process id=1, then id=2 (in order)
- music.requested handlers process id=3 (independent)
```

### Redis Streams Event Bus

**Per-Stream Ordering:**
- Events in the **same stream** are processed **in order**
- Events in **different streams** may be processed **out of order**
- Consumer groups maintain ordering within group

**Example:**
```
Stream: mediaposter:events:tts.requested
- Event 1 (timestamp: 1000)
- Event 2 (timestamp: 1001)
- Event 3 (timestamp: 1002)

Processing: Always 1 → 2 → 3 (in order)
```

---

## 🚦 Backpressure Strategy

### In-Memory Event Bus

**Strategy: None**
- ⚠️ **Unbounded queue** (no backpressure)
- ⚠️ Risk: Memory exhaustion with slow consumers
- ⚠️ No flow control

**Mitigation:**
- Monitor memory usage
- Limit event log size (`_max_log_size = 1000`)
- Fast handlers (don't block)

### Redis Streams Event Bus

**Strategy: Stream Length Limits**
- ✅ **MAXLEN** limits stream length (default: 10,000)
- ✅ Oldest events evicted when limit reached
- ✅ Prevents unbounded growth

**Configuration:**
```python
MAX_STREAM_LENGTH = 10000  # Max events per stream
```

**Behavior:**
- When stream reaches MAXLEN, oldest events are evicted
- New events are always added
- Consumers should process faster than producers

**Monitoring:**
```bash
# Check stream length
redis-cli XLEN mediaposter:events:tts.requested

# Alert if > 80% capacity (8000 events)
```

---

## 🔧 Configuration

### Environment Variables

```bash
# In-memory (default)
# No configuration needed

# Redis Streams
REDIS_URL=redis://localhost:6379
EVENT_BUS_BACKEND=redis
```

### Programmatic Selection

```python
from services.event_bus import get_event_bus

# Auto-selects based on EVENT_BUS_BACKEND env var
bus = get_event_bus()

# Or explicitly
from services.event_bus import EventBus, RedisEventBus

# In-memory
bus = EventBus.get_instance()

# Redis
bus = RedisEventBus.get_instance(redis_url="redis://localhost:6379")
```

---

## 📈 Production Recommendations

### For Production

1. **Use Redis Streams**
   ```bash
   EVENT_BUS_BACKEND=redis
   REDIS_URL=redis://your-redis-server:6379
   ```

2. **Monitor Stream Lengths**
   - Alert if stream > 80% capacity
   - Monitor consumer lag
   - Track DLQ size

3. **Use Consumer Groups**
   - Multiple workers can process same stream
   - Automatic load balancing
   - Automatic acknowledgment

4. **Set Appropriate MAXLEN**
   - Based on throughput: `events_per_second * retention_seconds`
   - Example: 100 events/sec * 100 seconds = 10,000

5. **Monitor DLQ**
   - Check `mediaposter:events:dlq` regularly
   - Investigate failures
   - Retry after fixes

### For Development

- **In-memory is fine** (faster, simpler, no Redis required)

---

## 🔍 Event Bus Statistics

### In-Memory

**No statistics** (would require instrumentation)

### Redis Streams

**Available Statistics:**
```python
bus._stats = {
    "events_published": 0,
    "events_consumed": 0,
    "events_failed": 0,
    "connection_errors": 0
}
```

**Redis Commands:**
```bash
# Stream info
redis-cli XINFO STREAM mediaposter:events:tts.requested

# Consumer group info
redis-cli XINFO GROUPS mediaposter:events:tts.requested

# Pending messages
redis-cli XPENDING mediaposter:events:tts.requested mediaposter-workers
```

---

## 🎯 Summary

| Aspect | In-Memory | Redis Streams |
|--------|-----------|---------------|
| **Transport** | Python dict | Redis Streams |
| **Persistence** | None | Durable |
| **Scalability** | Single-process | Multi-server |
| **Delivery** | At-least-once | At-least-once |
| **Ordering** | Per-topic | Per-stream |
| **Backpressure** | None | Stream limits |
| **Use Case** | Development | Production |

**Recommendation:** Use **Redis Streams** for production deployments.

---

*For implementation details, see `Backend/services/event_bus/bus.py` and `Backend/services/event_bus/redis_adapter.py`*

