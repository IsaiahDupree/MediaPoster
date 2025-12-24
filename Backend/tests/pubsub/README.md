# Pub/Sub Service Test Suite

Comprehensive test suite for the event-driven pub/sub architecture.

## Quick Start

```bash
# Run all pub/sub tests
pytest Backend/tests/pubsub/ -v

# Run test harness with all categories
python Backend/tests/pubsub/test_harness.py

# Run specific category
pytest Backend/tests/pubsub/test_unit_*.py -v
```

## Test Matrix

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                        PUB/SUB TEST MATRIX                                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ SERVICE              │ UNIT │ CONTRACT │ IDEMPOTENCY │ INTEGRATION │ E2E    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ SchedulerService     │  ✓   │    ✓     │      ✓      │      ✓      │   ✓    ║
║ NarrativePlanner     │  ✓   │    ✓     │      ✓      │      ✓      │   ✓    ║
║ ExperimentsService   │  ✓   │    ✓     │      ✓      │      ✓      │   ✓    ║
║ Worker/Queue         │  ✓   │    ✓     │      ✓      │      ✓      │   ✓    ║
║ EventBus             │  ✓   │    ✓     │      -      │      ✓      │   ✓    ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

## Test Structure

### 1. Unit Tests (`test_unit_*.py`)
**Goal:** Pure logic tests without broker/DB - Fast, cheap, high ROI

| File | Description |
|------|-------------|
| `test_unit_topic_routing.py` | Topic pattern matching, wildcards, handler dispatch |
| `test_unit_step_machine.py` | State transitions (queued→running→succeeded/failed) |
| `test_unit_scoring_logic.py` | Pillar distribution, constraints, video scoring |
| `test_unit_event_routing.py` | Event routing logic |

### 2. Contract Tests (`test_contract_*.py`)
**Goal:** Prevent breaking changes in message shape

| File | Description |
|------|-------------|
| `test_contract_message_schema.py` | Message envelope validation, versioning |
| `test_contract_event_schemas.py` | Event-specific schema validation |

### 3. Integration Tests (`test_integration_*.py`)
**Goal:** Real broker/DB semantics - locking, concurrency, retries

| File | Description |
|------|-------------|
| `test_integration_broker_db.py` | Queue locking, visibility timeout, DLQ |
| `test_integration_event_persistence.py` | Event history, replay |

### 4. Idempotency Tests (`test_idempotency_*.py`)
**Goal:** Make duplicates harmless

| File | Description |
|------|-------------|
| `test_idempotency.py` | Core idempotency patterns |
| `test_idempotency_workers.py` | Worker deduplication |

### 5. Service-Specific Tests (`test_*_service.py`)
**Goal:** Individual service behavior

| File | Description |
|------|-------------|
| `test_scheduler_service.py` | Due schedule selection, no duplicate runs, next_run_at |
| `test_narrative_planner_service.py` | Pillar constraints, rejection log, events |
| `test_experiments_service.py` | Control/variant tagging, sample gating, winner |
| `test_worker_services.py` | Individual worker functionality |

### 6. E2E Workflow Tests (`test_e2e_*.py`)
**Goal:** Full pipeline validation

| File | Description |
|------|-------------|
| `test_e2e_workflows.py` | Media→analysis→publish, narrative planning, experiments |

### 7. Observability Tests (`test_observability_*.py`)
**Goal:** Timeline correctness for Agent Panel UI

| File | Description |
|------|-------------|
| `test_observability_timeline.py` | Event ordering, lifecycle, no sensitive data |

### 8. Load Tests (`test_load_*.py`)
**Goal:** Performance under pressure (optional)

| File | Description |
|------|-------------|
| `test_load_performance.py` | Throughput, latency, queue depth |

## Running Tests

```bash
# Run all pub/sub tests
pytest Backend/tests/pubsub/ -v

# Run specific test category
pytest Backend/tests/pubsub/test_unit_*.py -v
pytest Backend/tests/pubsub/test_contract_*.py -v
pytest Backend/tests/pubsub/test_integration_*.py -v
pytest Backend/tests/pubsub/test_idempotency*.py -v
pytest Backend/tests/pubsub/test_*_service.py -v

# Run with coverage
pytest Backend/tests/pubsub/ --cov=services.event_bus --cov=services.workers

# Run test harness (all categories in order)
python Backend/tests/pubsub/test_harness.py
python Backend/tests/pubsub/test_harness.py --no-integration  # Skip DB tests
python Backend/tests/pubsub/test_harness.py --load            # Include load tests
```

## Test Fixtures

| Fixture | Description |
|---------|-------------|
| `event_bus` | Fresh EventBus instance (reset for each test) |
| `mock_event_bus` | Mock for isolated unit tests |
| `db_session` | Async database session |
| `workflow_tracker` | Collects all events in workflow |
| `event_collector` | Collects events for assertions |
| `idempotency_key_generator` | Generate idempotency keys |

## Timeline Invariants

The test harness validates these invariants:

1. **Run lifecycle:** Every run has `run.queued` → `run.started` → terminal
2. **Step lifecycle:** Every step has `step.started` → `step.completed`/`step.failed`
3. **Event ordering:** Timestamps are chronological
4. **No sensitive data:** Thought summaries don't contain secrets

## Adding New Tests

When adding a new worker or event type:

1. **Add unit test** for routing logic
2. **Add contract test** for event schema
3. **Add integration test** if it touches DB
4. **Add idempotency test** if it creates records
5. **Add E2E test** if it's a major workflow
6. **Add service test** for specific service behavior

## Notes

- Tests use `asyncio.sleep()` for async coordination
- Database tests are skipped if `DATABASE_URL` not set
- Mock external services (file system, APIs) when possible
- Use `correlation_id` to track workflows
- Use idempotency keys to prevent duplicates

