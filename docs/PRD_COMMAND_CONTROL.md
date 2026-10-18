# PRD: MediaPoster Command & Control + Data Exchange

**Version:** 1.0  
**Last Updated:** January 31, 2026  
**Owner:** Engineering Team

---

## 1. Objective

Enable **external systems** (orchestrator services, Safari Automation, schedulers) to:

- Submit pipeline commands to MediaPoster
- Receive reliable status + progress updates
- Fetch structured results and artifacts
- Operate safely and repeatably

This supports the full automation workflow: ingestion → analysis → highlight detection → clip generation → upload → monitoring.

---

## 2. Users

| User | Needs |
|------|-------|
| **Automation Orchestrator** | Submit commands, receive events, coordinate multi-app workflows |
| **Safari Automation Service** | Request video generation, watermark removal, get results |
| **Developer** | Stable API, contract tests, clear documentation |
| **Operator** | Monitor jobs, cancel runaway tasks, view failures |

---

## 3. Scope

### In Scope (v1)

- Control API on port 9100
- Command envelope + event envelope format
- Job lifecycle management (queued/running/succeeded/failed/cancelled)
- Event streaming (SSE)
- Result retrieval (clip URLs, metadata, post IDs)
- API key authentication
- Idempotency + deduplication
- Contract tests

### Out of Scope (v1)

- Multi-tenant auth + billing
- Public internet exposure by default
- Full workflow DSL (keep it simple: commands first)
- WebSocket (SSE sufficient for v1)

---

## 4. Functional Requirements

### FR-1: Command Submission

| ID | Requirement |
|----|-------------|
| FR-1.1 | Accept commands for all major modules: ingestion, analysis, highlights, clips, staging, publishing, monitoring |
| FR-1.2 | Return `job_id` within 250ms for normal load (enqueue-only, no blocking) |
| FR-1.3 | Validate command envelope schema before acceptance |
| FR-1.4 | Support idempotency keys to prevent duplicate execution |

### FR-2: Status & Progress

| ID | Requirement |
|----|-------------|
| FR-2.1 | `GET /v1/jobs/{job_id}` returns: state, stage, percent, timestamps, last event, error summary |
| FR-2.2 | `GET /v1/events/stream` streams events in order per job |
| FR-2.3 | Support cursor-based pagination for event history |
| FR-2.4 | Events must be persisted for replay |

### FR-3: Results

| ID | Requirement |
|----|-------------|
| FR-3.1 | Jobs produce structured `result` object with created IDs |
| FR-3.2 | Artifact locations provided as local paths or signed URLs |
| FR-3.3 | Metrics snapshots included when applicable |

### FR-4: Reliability

| ID | Requirement |
|----|-------------|
| FR-4.1 | Idempotency keys prevent duplicate work |
| FR-4.2 | Retries safe at stage boundaries |
| FR-4.3 | `job.failed` includes machine-readable error codes |
| FR-4.4 | Jobs can be cancelled mid-execution |

### FR-5: Security

| ID | Requirement |
|----|-------------|
| FR-5.1 | Support API key header authentication |
| FR-5.2 | Support JWT bearer token authentication |
| FR-5.3 | Default bind to localhost only |
| FR-5.4 | Optional IP allowlist for remote access |

---

## 5. Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-1 | Observability | Structured logs + event store |
| NFR-2 | Compatibility | Versioned endpoints `/v1/...` |
| NFR-3 | Performance | Control plane stays responsive even when workers busy |
| NFR-4 | Testing | Contract test suite + smoke tests |
| NFR-5 | Availability | Graceful degradation if core services down |

---

## 6. Data Model

### `c2_jobs` Table

| Column | Type | Description |
|--------|------|-------------|
| `job_id` | UUID | Primary key |
| `command_id` | VARCHAR(100) | Original command ID |
| `correlation_id` | UUID | Groups related jobs |
| `command` | VARCHAR(100) | Command name |
| `args` | JSONB | Command arguments |
| `state` | VARCHAR(50) | QUEUED, RUNNING, SUCCEEDED, FAILED, CANCELLED |
| `stage` | VARCHAR(100) | Current execution stage |
| `percent` | INTEGER | Progress percentage (0-100) |
| `result` | JSONB | Final result data |
| `error_code` | VARCHAR(50) | Error code if failed |
| `error_message` | TEXT | Error details |
| `idempotency_key` | VARCHAR(255) | For deduplication |
| `priority` | VARCHAR(20) | low, normal, high |
| `timeout_s` | INTEGER | Timeout in seconds |
| `created_at` | TIMESTAMPTZ | Job creation time |
| `started_at` | TIMESTAMPTZ | Execution start time |
| `completed_at` | TIMESTAMPTZ | Completion time |
| `updated_at` | TIMESTAMPTZ | Last update time |

### `c2_job_events` Table

| Column | Type | Description |
|--------|------|-------------|
| `event_id` | UUID | Primary key |
| `job_id` | UUID | FK to c2_jobs |
| `type` | VARCHAR(50) | Event type |
| `stage` | VARCHAR(100) | Stage name |
| `percent` | INTEGER | Progress at this event |
| `message` | TEXT | Human-readable message |
| `data` | JSONB | Event-specific data |
| `cursor` | VARCHAR(100) | For pagination/replay |
| `timestamp` | TIMESTAMPTZ | Event timestamp |

---

## 7. Epics & Acceptance Criteria

### Epic A: Control API Service

| Story | Description |
|-------|-------------|
| A1 | `POST /v1/commands` queues jobs and returns job IDs |
| A2 | `GET /v1/jobs/{id}` returns canonical state |
| A3 | `GET /v1/jobs` lists jobs with filters |
| A4 | `GET /v1/health` and `/v1/ready` implemented |

**Acceptance Criteria:**
- [ ] Can enqueue: `clip.generate`, `publish.blotato`, `monitor.check`
- [ ] A job can be observed end-to-end via polling
- [ ] Health endpoint returns within 100ms

### Epic B: Eventing

| Story | Description |
|-------|-------------|
| B1 | Workers emit events at each stage boundary |
| B2 | Events persisted and replayable |
| B3 | SSE streaming with reconnection via cursor |

**Acceptance Criteria:**
- [ ] Disconnect/reconnect does not lose events
- [ ] Job's full history can be replayed
- [ ] Events delivered within 1s of emission

### Epic C: Reliability

| Story | Description |
|-------|-------------|
| C1 | Idempotency enforced |
| C2 | Retry + cancel semantics implemented |
| C3 | Error taxonomy defined |

**Acceptance Criteria:**
- [ ] Duplicate commands with same idempotency key don't duplicate work
- [ ] Cancel stops further stages for pipeline jobs
- [ ] All errors have machine-readable codes

### Epic D: Security

| Story | Description |
|-------|-------------|
| D1 | API key auth implemented |
| D2 | Default bind to localhost |
| D3 | Optional allowlist for remote clients |

**Acceptance Criteria:**
- [ ] Unauthenticated calls rejected with 401
- [ ] Key rotation supported without downtime
- [ ] Remote access configurable via env vars

---

## 8. API Surface

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/commands` | Submit command |
| GET | `/v1/jobs/{job_id}` | Get job status |
| GET | `/v1/jobs` | List jobs |
| POST | `/v1/jobs/{job_id}/cancel` | Cancel job |
| POST | `/v1/jobs/{job_id}/retry` | Retry job |
| GET | `/v1/jobs/{job_id}/events` | Get job events |
| GET | `/v1/events/stream` | SSE event stream |
| GET | `/v1/health` | Liveness |
| GET | `/v1/ready` | Readiness |

---

## 9. Integration Points

### Internal (MediaPoster)

- **Celery**: Enqueue tasks for background processing
- **Redis**: Job state, event pub/sub
- **PostgreSQL**: Persistent job/event storage
- **Core API**: Call internal endpoints for operations

### External

- **Safari Automation Service** (port 7070): Sora video generation
- **Blotato API**: Social media publishing
- **OpenAI**: Transcription, vision analysis

---

## 10. Success Metrics

| Metric | Target |
|--------|--------|
| Command acceptance latency | < 250ms p99 |
| Event delivery latency | < 1s p99 |
| Job completion rate | > 95% |
| API availability | > 99.9% |

---

## 11. Milestones

| Phase | Deliverables | Target |
|-------|-------------|--------|
| Phase 1 | Command submission, job polling, basic auth | Week 1 |
| Phase 2 | SSE streaming, event persistence | Week 2 |
| Phase 3 | Full command catalog, Safari integration | Week 3 |
| Phase 4 | Contract tests, documentation | Week 4 |

---

## 12. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Worker overload | Jobs queue up | Implement backpressure, priority queues |
| Event loss | Missing status updates | Persist events before emitting |
| Security exposure | Unauthorized access | Default localhost, require auth |
| Schema evolution | Breaking changes | Version endpoints, maintain compatibility |

---

## 13. Related Documentation

| Doc | Path |
|-----|------|
| API Spec | `docs/C2_API_SPEC.md` |
| Safari Automation | `docs/SAFARI_AUTOMATION_SERVICE_API.md` |
| Supabase Storage | `docs/SAFARI_AUTOMATION_SUPABASE_STORAGE.md` |
