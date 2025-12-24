# Pub/Sub Test Suite Documentation

**Created:** December 25, 2025  
**Status:** Comprehensive test suite for pub/sub architecture

---

## 📋 Test Categories

### 1. Unit Tests (`test_unit_*.py`)
**Goal:** Pure logic without broker/DB

**Files:**
- `test_unit_event_routing.py` - Topic matching, event routing, correlation IDs

**Coverage:**
- ✅ Topic pattern matching (wildcards, exact matches)
- ✅ Event routing to correct handlers
- ✅ Multiple subscribers per topic
- ✅ Correlation ID tracking
- ✅ Event metadata and source tracking

**Run:**
```bash
pytest Backend/tests/pubsub/test_unit_*.py -v
```

---

### 2. Contract Tests (`test_contract_*.py`)
**Goal:** Prevent breaking changes in message shape

**Files:**
- `test_contract_event_schemas.py` - Event schema validation

**Coverage:**
- ✅ Required fields validation
- ✅ Type checks and enum values
- ✅ Unknown fields ignored gracefully
- ✅ Event serialization/deserialization
- ✅ Backward compatibility

**Run:**
```bash
pytest Backend/tests/pubsub/test_contract_*.py -v
```

---

### 3. Integration Tests (`test_integration_*.py`)
**Goal:** Real broker/DB semantics

**Files:**
- `test_integration_event_persistence.py` - Event history & replay

**Coverage:**
- ✅ Events persisted to database
- ✅ Event querying with filters (topic, correlation_id, time range)
- ✅ Event replay functionality
- ✅ Workflow tracking by correlation_id
- ✅ Batch persistence

**Run:**
```bash
pytest Backend/tests/pubsub/test_integration_*.py -v
```

**Requirements:**
- Database must be running
- `event_history` table must exist (run migrations)

---

### 4. Idempotency Tests (`test_idempotency_*.py`)
**Goal:** Make duplicates harmless

**Files:**
- `test_idempotency_workers.py` - Worker deduplication

**Coverage:**
- ✅ No duplicate notifications
- ✅ No duplicate thumbnails
- ✅ Unique constraints prevent duplicates
- ✅ Correlation ID tracking
- ✅ Event ID deduplication

**Run:**
```bash
pytest Backend/tests/pubsub/test_idempotency_*.py -v
```

---

### 5. E2E Workflow Tests (`test_e2e_*.py`)
**Goal:** Full pipeline validation

**Files:**
- `test_e2e_workflows.py` - Complete workflows

**Coverage:**
- ✅ Media ingest → analysis → publish → metrics
- ✅ Narrative planning → scheduling → publishing
- ✅ Experiment creation → variants → metrics → winner
- ✅ Failure path with retry
- ✅ Parallel workflows

**Run:**
```bash
pytest Backend/tests/pubsub/test_e2e_*.py -v
```

---

### 6. Observability Tests (`test_observability_*.py`)
**Goal:** Timeline correctness

**Files:**
- `test_observability_timeline.py` - Event ordering, lifecycle

**Coverage:**
- ✅ Proper lifecycle events (requested → started → completed)
- ✅ Event ordering is consistent
- ✅ No sensitive data in events
- ✅ Timestamps are monotonic
- ✅ Correlation ID tracks workflows
- ✅ Event history completeness

**Run:**
```bash
pytest Backend/tests/pubsub/test_observability_*.py -v
```

---

### 7. Worker Service Tests (`test_worker_*.py`)
**Goal:** Individual worker functionality

**Files:**
- `test_worker_services.py` - Each worker tested

**Coverage:**
- ✅ NotificationWorker - Creates notifications
- ✅ ThumbnailGenerationWorker - Generates thumbnails
- ✅ NarrativeBuilderWorker - Updates signals
- ✅ EventHistoryWorker - Persists events

**Run:**
```bash
pytest Backend/tests/pubsub/test_worker_*.py -v
```

---

### 8. Load & Performance Tests (`test_load_*.py`)
**Goal:** Validate throughput

**Files:**
- `test_load_performance.py` - Performance under load

**Coverage:**
- ✅ Producer burst (1000 events)
- ✅ Multiple consumers scaling
- ✅ Event latency measurements
- ✅ Concurrent publishers
- ✅ Events per second throughput
- ✅ Memory usage under load

**Run:**
```bash
pytest Backend/tests/pubsub/test_load_*.py -v
```

---

## 🚀 Running Tests

### Run All Tests
```bash
# Using pytest directly
pytest Backend/tests/pubsub/ -v

# Using test runner
python Backend/tests/pubsub/run_pubsub_tests.py all
```

### Run by Category
```bash
# Unit tests only
python Backend/tests/pubsub/run_pubsub_tests.py unit

# Integration tests only
python Backend/tests/pubsub/run_pubsub_tests.py integration

# E2E tests only
python Backend/tests/pubsub/run_pubsub_tests.py e2e
```

### With Coverage
```bash
python Backend/tests/pubsub/run_pubsub_tests.py all --coverage
```

---

## 📊 Test Coverage Goals

| Category | Target Coverage | Current Status |
|----------|----------------|----------------|
| Unit Tests | 100% | ✅ Complete |
| Contract Tests | All schemas | ✅ Complete |
| Integration Tests | All paths | ✅ Complete |
| Idempotency | All workers | ✅ Complete |
| E2E Workflows | Major flows | ✅ Complete |
| Observability | Timeline correctness | ✅ Complete |
| Load Tests | Performance | ✅ Complete |

---

## 🧪 Test Fixtures

### `event_bus`
Fresh EventBus instance for each test
```python
@pytest.fixture
def event_bus():
    EventBus.reset_instance()
    bus = EventBus.get_instance()
    yield bus
    EventBus.reset_instance()
```

### `db_session`
Database session (skipped if DB not available)
```python
@pytest.fixture
async def db_session():
    if not async_session_maker:
        pytest.skip("Database not available")
    async with async_session_maker() as session:
        yield session
```

### `workflow_tracker`
Tracks all events in a workflow
```python
@pytest.fixture
async def workflow_tracker(event_bus):
    events = []
    async def track(event):
        events.append(event)
    event_bus.subscribe("*", track)
    yield events
```

---

## 🔧 Adding New Tests

When adding a new worker or event type:

1. **Unit Test** - Add to `test_unit_event_routing.py` if it affects routing
2. **Contract Test** - Add schema validation to `test_contract_event_schemas.py`
3. **Integration Test** - Add to `test_integration_*.py` if it touches DB
4. **Idempotency Test** - Add to `test_idempotency_*.py` if it creates records
5. **E2E Test** - Add workflow to `test_e2e_workflows.py`
6. **Worker Test** - Add to `test_worker_services.py`

---

## 📝 Test Patterns

### Testing Event Routing
```python
async def test_routing(bus):
    received = []
    async def handler(e): received.append(e)
    bus.subscribe("test.*", handler)
    await bus.publish("test.event", {})
    assert len(received) == 1
```

### Testing Workflow Tracking
```python
correlation_id = "workflow-123"
await bus.publish("event1", {}, correlation_id=correlation_id)
await bus.publish("event2", {}, correlation_id=correlation_id)
# Query by correlation_id to verify workflow
```

### Testing Idempotency
```python
# Publish same event twice
await bus.publish("event", {}, correlation_id="same")
await bus.publish("event", {}, correlation_id="same")
# Verify no duplicates in database
```

---

## ⚠️ Notes

- Tests use `asyncio.sleep()` for async coordination
- Database tests are skipped if DB not available
- Mock external services (file system, APIs) when possible
- Use correlation_ids to track workflows
- Event bus is reset between tests for isolation

---

**Last Updated:** December 25, 2025

