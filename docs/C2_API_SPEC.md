# MediaPoster Command & Control Interface Spec (C2 API)

**Last Updated:** January 31, 2026  
**Version:** 1.0  
**Status:** Active

---

## 1. Overview

The Command & Control (C2) API provides a stable "remote control" surface for MediaPoster, allowing external systems to:

- Submit pipeline commands
- Receive reliable status + progress
- Fetch structured results/artifacts
- Operate safely and repeatably

### Architecture

```
┌─────────────────────────┐     ┌─────────────────────────────────┐
│  External Orchestrator  │     │  MediaPoster                    │
│  (Safari Automation,    │     │                                 │
│   Scheduler, etc.)      │     │  ┌───────────────────────────┐  │
│                         │     │  │ Control Plane (:9100)     │  │
│  ┌───────────────────┐  │HTTP │  │ - POST /v1/commands       │  │
│  │ Command Submitter │──┼─────┼──│ - GET /v1/jobs/{id}       │  │
│  │                   │  │     │  │ - GET /v1/events/stream   │  │
│  └───────────────────┘  │     │  └───────────┬───────────────┘  │
│                         │     │              │                  │
│  ┌───────────────────┐  │ SSE │              ▼                  │
│  │ Event Listener    │◀─┼─────┼──────────────┤                  │
│  │                   │  │     │              │                  │
│  └───────────────────┘  │     │  ┌───────────▼───────────────┐  │
│                         │     │  │ Core API (:5555)          │  │
└─────────────────────────┘     │  │ - FastAPI                 │  │
                                │  │ - Celery Workers          │  │
                                │  │ - Redis + PostgreSQL      │  │
                                │  └───────────────────────────┘  │
                                │                                 │
                                │  ┌───────────────────────────┐  │
                                │  │ Dashboard (:5557)         │  │
                                │  │ - Next.js                 │  │
                                │  └───────────────────────────┘  │
                                └─────────────────────────────────┘
```

---

## 2. Port Topology

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| Core API (existing) | 5555 | HTTP | FastAPI internal endpoints |
| Dashboard (existing) | 5557 | HTTP | Next.js frontend |
| **Control API (new)** | **9100** | HTTP/SSE | External command interface |
| Event Stream (optional) | 9101 | WebSocket | Real-time events (or use SSE on 9100) |

---

## 3. Command Envelope

All commands use a consistent JSON envelope format:

```json
{
  "version": "1.0",
  "command_id": "cmd_01HZY...unique",
  "correlation_id": "corr_01HZY...group",
  "issued_at": "2026-01-30T22:14:05Z",
  "issued_by": "orchestrator|user|system",
  "command": "clip.generate",
  "target": {
    "service": "mediaposter",
    "instance_id": "mac-mini-01"
  },
  "args": {
    "video_id": "vid_123",
    "start_ms": 45200,
    "end_ms": 78200,
    "preset": "viral_v1",
    "platforms": ["tiktok", "instagram_reels"]
  },
  "idempotency_key": "clip.generate:vid_123:45200:78200:viral_v1",
  "priority": "normal",
  "timeout_s": 3600
}
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `version` | string | Yes | Protocol version (currently "1.0") |
| `command_id` | string | Yes | Unique ID for this command |
| `correlation_id` | string | No | Groups related commands together |
| `issued_at` | ISO8601 | Yes | When command was issued |
| `issued_by` | string | No | Who/what issued the command |
| `command` | string | Yes | Command name (e.g., "clip.generate") |
| `target` | object | No | Target service/instance |
| `args` | object | Yes | Command-specific arguments |
| `idempotency_key` | string | No | Prevents duplicate execution |
| `priority` | string | No | "low", "normal", "high" |
| `timeout_s` | integer | No | Timeout in seconds |

---

## 4. Acknowledgment Response

Immediate response when command is accepted:

```json
{
  "accepted": true,
  "job_id": "job_01HZY...",
  "command_id": "cmd_01HZY...",
  "queued_at": "2026-01-30T22:14:06Z"
}
```

---

## 5. Event Envelope

Events emitted during job execution:

```json
{
  "version": "1.0",
  "event_id": "evt_01HZY...",
  "correlation_id": "corr_01HZY...",
  "job_id": "job_01HZY...",
  "timestamp": "2026-01-30T22:16:22Z",
  "type": "job.progress",
  "stage": "ai_analysis",
  "percent": 42,
  "message": "transcription complete",
  "data": {
    "transcript_id": "tr_456",
    "duration_s": 812
  }
}
```

### Event Types

| Type | Description |
|------|-------------|
| `job.queued` | Job accepted and queued |
| `job.started` | Job execution started |
| `job.progress` | Progress update |
| `job.stage_complete` | A stage finished |
| `job.completed` | Job finished successfully |
| `job.failed` | Job failed |
| `job.cancelled` | Job was cancelled |

---

## 6. API Endpoints

### Commands

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/v1/commands` | Submit a command envelope |
| `POST` | `/v1/jobs/{job_id}/cancel` | Cancel a running job |
| `POST` | `/v1/jobs/{job_id}/retry` | Retry from last checkpoint |

### Jobs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/jobs/{job_id}` | Get job status and result |
| `GET` | `/v1/jobs` | List jobs (with filters) |
| `GET` | `/v1/jobs/{job_id}/events` | Get job events (paginated) |

### Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/events/stream` | SSE stream of events |

### Results

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/artifacts/{artifact_id}` | Get artifact (signed URL or path) |
| `GET` | `/v1/videos/{video_id}` | Get video metadata |
| `GET` | `/v1/clips/{clip_id}` | Get clip metadata |
| `GET` | `/v1/posts/{post_id}` | Get post metadata |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/v1/health` | Liveness check |
| `GET` | `/v1/ready` | Readiness check (Redis, DB, workers) |

---

## 7. Command Catalog

### Ingestion

| Command | Description | Args |
|---------|-------------|------|
| `ingest.sync` | Sync from iPhone sources | `source` |
| `ingest.scan` | Scan local watch folder | `folder_path` |
| `ingest.register` | Register a video | `video_path` or `cloud_url` |

### Analysis

| Command | Description | Args |
|---------|-------------|------|
| `analyze.transcribe` | Transcribe video | `video_id` |
| `analyze.vision` | AI vision analysis | `video_id` |
| `analyze.summarize` | Summarize content | `video_id` |

### Highlights

| Command | Description | Args |
|---------|-------------|------|
| `highlights.detect` | Detect highlights | `video_id`, `strategy` |
| `highlights.approve` | Approve highlight | `highlight_id` |
| `highlights.reject` | Reject highlight | `highlight_id` |

### Clips

| Command | Description | Args |
|---------|-------------|------|
| `clip.generate` | Generate clip | `video_id`, `start_ms`, `end_ms`, `preset` |
| `clip.render_variations` | Render variations | `clip_id`, `variations` |

### Staging & Publishing

| Command | Description | Args |
|---------|-------------|------|
| `stage.upload` | Upload to staging | `clip_id`, `provider` |
| `publish.blotato` | Publish via Blotato | `clip_id`, `platforms` |

### Monitoring

| Command | Description | Args |
|---------|-------------|------|
| `monitor.check` | Check post metrics | `post_id` |
| `monitor.schedule` | Schedule checks | `post_id`, `delays` |
| `monitor.autodelete` | Auto-delete low perf | `post_id`, `ruleset` |

### Utilities

| Command | Description | Args |
|---------|-------------|------|
| `watermark.remove` | Remove watermark | `clip_id` or `video_path` |
| `config.get` | Get config value | `key` |
| `config.set` | Set config value | `key`, `value` |
| `system.snapshot` | Get system state | - |

### Safari Automation (via Safari Automation Service)

| Command | Description | Args |
|---------|-------------|------|
| `safari.sora.generate` | Generate Sora video | `prompt`, `character` |
| `safari.sora.generate.clean` | Generate + remove watermark | `prompt`, `character` |
| `safari.sora.clean` | Clean existing video | `input_path` |

---

## 8. Job States

```
QUEUED → RUNNING → SUCCEEDED
                 ↘ FAILED
                 ↘ CANCELLED
```

| State | Description |
|-------|-------------|
| `QUEUED` | Job accepted, waiting for worker |
| `RUNNING` | Job is executing |
| `SUCCEEDED` | Job completed successfully |
| `FAILED` | Job failed (see error) |
| `CANCELLED` | Job was cancelled |

---

## 9. Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Invalid command or args |
| `DEPENDENCY_DOWN` | Required service unavailable |
| `PROCESSING_FAILED` | Processing error |
| `UPLOAD_FAILED` | Upload to platform failed |
| `TIMEOUT` | Job exceeded timeout |
| `CANCELLED` | Job was cancelled |

---

## 10. Security

### Authentication

- **API Key**: `X-API-Key` header
- **JWT Bearer**: `Authorization: Bearer <token>` header

### Default Configuration

- Bind to `127.0.0.1` (localhost only)
- Optional IP allowlist for remote access
- Key rotation without downtime

---

## 11. Usage Examples

### Submit a Command (Python)

```python
import requests

response = requests.post(
    "http://localhost:9100/v1/commands",
    headers={"X-API-Key": "your-api-key"},
    json={
        "version": "1.0",
        "command_id": "cmd_123",
        "command": "clip.generate",
        "args": {
            "video_id": "vid_456",
            "start_ms": 0,
            "end_ms": 60000,
            "preset": "viral_v1"
        }
    }
)

job_id = response.json()["job_id"]
```

### Poll Job Status

```python
status = requests.get(
    f"http://localhost:9100/v1/jobs/{job_id}",
    headers={"X-API-Key": "your-api-key"}
).json()

print(f"Status: {status['state']}, Progress: {status['percent']}%")
```

### Subscribe to Events (SSE)

```python
import sseclient

url = "http://localhost:9100/v1/events/stream"
headers = {"X-API-Key": "your-api-key"}

client = sseclient.SSEClient(url, headers=headers)
for event in client.events():
    print(f"Event: {event.data}")
```

### cURL Example

```bash
# Submit command
curl -X POST http://localhost:9100/v1/commands \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "version": "1.0",
    "command_id": "cmd_test_001",
    "command": "analyze.transcribe",
    "args": {"video_id": "vid_123"}
  }'

# Check job status
curl http://localhost:9100/v1/jobs/job_xxx \
  -H "X-API-Key: your-api-key"
```

---

## 12. Related Documentation

| Doc | Location |
|-----|----------|
| PRD | `docs/PRD_COMMAND_CONTROL.md` |
| Safari Automation API | `docs/SAFARI_AUTOMATION_SERVICE_API.md` |
| Supabase Storage | `docs/SAFARI_AUTOMATION_SUPABASE_STORAGE.md` |
