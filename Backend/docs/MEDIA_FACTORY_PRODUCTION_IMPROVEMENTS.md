# Media Factory - Production Improvements

**Date:** December 26, 2024  
**Status:** Production-Ready Enhancements ✅

---

## 📋 Overview

This document details the production-ready improvements added to the Media Factory system:
1. Data Contracts (stable interfaces)
2. Idempotency + Retries + Dead Letter Queue
3. Persistent Orchestration (database-backed)
4. Event Bus Documentation
5. Quality Gates

---

## 1. Data Contracts ✅

### Purpose

Data contracts define **stable interfaces** for all data structures in the pipeline. This enables:
- **Provider Swapping**: Swap adapters without breaking contracts
- **Multi-Server Rendering**: Any server can render if it receives the same contract
- **Version Compatibility**: Schema validation ensures compatibility
- **Type Safety**: Pydantic models provide runtime validation

### Contracts Defined

#### TrendCard Schema
- **Location**: `Backend/services/media_factory/contracts/trend_card.py`
- **Purpose**: Raw trend input from social platforms
- **Fields**: trend_id, trend_type, trend_name, platform, velocity signals, evidence, format

#### Cluster Schema
- **Location**: `Backend/services/media_factory/contracts/cluster.py`
- **Purpose**: Clustered trends (merged duplicates)
- **Fields**: cluster_id, name, trends, summary, aggregated metrics

#### Content Brief Schema
- **Location**: `Backend/services/media_factory/contracts/content_brief.py`
- **Purpose**: Production-ready brief with scoring
- **Fields**: brief_id, status, cluster, angle, score, content, video spec, CTA

#### Script Schema
- **Location**: `Backend/services/media_factory/contracts/script.py`
- **Purpose**: script.json (Stage A output, TTS input)
- **Fields**: brief_id, title, hook, segments (beats with timing), metadata

#### Timeline Schema
- **Location**: `Backend/services/media_factory/contracts/timeline.py`
- **Purpose**: timeline.json (Remotion input)
- **Fields**: fps, resolution, duration, layers, audio tracks, captions

#### Render Job Schema
- **Location**: `Backend/services/media_factory/contracts/render_job.py`
- **Purpose**: Remotion render job specification
- **Fields**: job_id, composition, timeline, props, output config

#### Publish Job Schema
- **Location**: `Backend/services/media_factory/contracts/publish_job.py`
- **Purpose**: Multi-platform publishing job
- **Fields**: job_id, video_path, platforms, platform configs

### Usage

```python
from services.media_factory.contracts import ScriptSchema, TimelineSchema

# Validate script.json
script = ScriptSchema(**script_data)

# Validate timeline.json
timeline = TimelineSchema(**timeline_data)
```

---

## 2. Idempotency + Retries + Dead Letter Queue ✅

### Purpose

Ensure **reliable, idempotent operations** with automatic retry and failure tracking.

### Components

#### Idempotency Manager
- **Location**: `Backend/services/media_factory/idempotency.py`
- **Key Format**: `{job_id}:{stage_name}:{input_hash}`
- **Features**:
  - Generate deterministic idempotency keys
  - Check if operation already executed
  - Store results with TTL

#### Retry Manager
- **Location**: `Backend/services/media_factory/idempotency.py`
- **Policies**:
  - `NO_RETRY`: No retries
  - `EXPONENTIAL_BACKOFF`: 1s, 2s, 4s, 8s... (default)
  - `LINEAR_BACKOFF`: 1s, 2s, 3s, 4s...
  - `FIXED_DELAY`: Fixed delay between retries
- **Default**: 3 retries with exponential backoff

#### Dead Letter Queue
- **Location**: `Backend/services/media_factory/idempotency.py`
- **Features**:
  - Store failed operations with error details
  - Payload snapshots for debugging
  - Retry count tracking
  - Query by job_id, stage_name
  - Automatic size limiting (max 1000 entries)

### Usage

```python
from services.media_factory.idempotency import IdempotencyManager, RetryManager, DeadLetterQueue

# Idempotency
idempotency = IdempotencyManager()
key = idempotency.generate_idempotency_key(job_id, "tts", input_data)
result = idempotency.check_idempotency(key)
if not result:
    # Execute operation
    result = await execute_operation()
    idempotency.store_result(key, result)

# Retry
retry = RetryManager(max_retries=3, policy=RetryPolicy.EXPONENTIAL_BACKOFF)
result = await retry.execute_with_retry(operation, "TTS Generation", text, voice_ref)

# DLQ
dlq = DeadLetterQueue()
dlq.add_failure(job_id, "tts", "API timeout", payload, correlation_id, retry_count=3)
failures = dlq.get_failures(job_id="job_123")
```

---

## 3. Persistent Orchestration ✅

### Purpose

Replace **in-memory job status** with **database-backed persistence** for scalability and reliability.

### Database Models

#### MediaFactoryJob
- **Table**: `media_factory_jobs`
- **Fields**: job_id, correlation_id, status, progress, brief_id, stages, timing, error, final_output
- **Indexes**: status, correlation_id, created_at

#### MediaFactoryJobStage
- **Table**: `media_factory_job_stages`
- **Fields**: id, job_id, stage_name, stage_order, status, progress, input_data, output_data, idempotency_key, retry_count
- **Indexes**: job_id+stage_name, status, idempotency_key

#### MediaFactoryArtifact
- **Table**: `media_factory_artifacts`
- **Fields**: id, job_id, stage_name, artifact_type, file_path, file_size_bytes, file_hash, metadata, expires_at
- **Indexes**: job_id+stage_name, file_hash, expires_at

#### MediaFactoryEvent
- **Table**: `media_factory_events` (optional audit log)
- **Fields**: id, job_id, correlation_id, event_type, event_topic, event_payload, source, occurred_at
- **Indexes**: correlation_id, event_topic, occurred_at

#### MediaFactoryDLQ
- **Table**: `media_factory_dlq`
- **Fields**: id, job_id, stage_name, error, payload, retry_count, idempotency_key, resolved
- **Indexes**: job_id+stage_name, resolved, failed_at

### Migration

```sql
-- Create tables (run migration)
-- See: Backend/database/models_media_factory.py
```

### Usage

```python
from database.models_media_factory import MediaFactoryJob, MediaFactoryJobStage

# Create job
job = MediaFactoryJob(
    job_id=uuid4(),
    correlation_id=correlation_id,
    status="pending",
    brief_id=brief_id
)
db.add(job)
db.commit()

# Update stage
stage = MediaFactoryJobStage(
    job_id=job.job_id,
    stage_name="tts",
    stage_order=1,
    status="running",
    idempotency_key=idempotency_key
)
db.add(stage)
db.commit()
```

---

## 4. Event Bus Documentation ✅

### Current Implementation

The Event Bus supports **two backends**:

#### 1. In-Memory (Default)
- **Transport**: Python in-memory dictionary
- **Guarantees**: **At-least-once** delivery
- **Ordering**: **Per-topic ordering** (events to same topic processed in order)
- **Backpressure**: **None** (unbounded queue)
- **Persistence**: **None** (lost on restart)
- **Use Case**: Development, single-process

#### 2. Redis Streams (Production)
- **Transport**: Redis Streams
- **Guarantees**: **At-least-once** delivery (with consumer groups)
- **Ordering**: **Per-stream ordering** (events in same stream processed in order)
- **Backpressure**: **Stream length limits** (MAXLEN, default 10,000)
- **Persistence**: **Durable** (survives restarts)
- **Use Case**: Production, multi-server, distributed

### Configuration

```bash
# In-memory (default)
# No configuration needed

# Redis Streams
REDIS_URL=redis://localhost:6379
EVENT_BUS_BACKEND=redis
```

### Guarantees

| Aspect | In-Memory | Redis Streams |
|-------|-----------|---------------|
| **Delivery** | At-least-once | At-least-once |
| **Ordering** | Per-topic | Per-stream |
| **Persistence** | None | Durable |
| **Scalability** | Single-process | Multi-server |
| **Backpressure** | None | Stream limits |
| **Exactly-Once** | ❌ No | ❌ No (at-least-once) |

### Backpressure Strategy

**In-Memory:**
- No backpressure (unbounded queue)
- Risk: Memory exhaustion with slow consumers

**Redis Streams:**
- `MAXLEN` limits stream length (default: 10,000)
- Oldest events are evicted when limit reached
- Consumer groups prevent message loss

### Production Recommendations

**For Production:**
1. **Use Redis Streams** (`EVENT_BUS_BACKEND=redis`)
2. **Monitor stream lengths** (alert if > 80% capacity)
3. **Use consumer groups** for distributed processing
4. **Set appropriate MAXLEN** based on throughput
5. **Monitor DLQ** for failed events

**For Development:**
- In-memory is fine (faster, simpler)

---

## 5. Quality Gates ✅

### Purpose

**Automated quality checks** between pipeline stages to ensure production-ready output.

### Gates Defined

#### Audio Quality Gate
- **Location**: `Backend/services/media_factory/quality_gates.py`
- **Checks**:
  - ✅ Loudness range (-23 to -16 LUFS)
  - ✅ Clipping detection (max 0.1% clipped samples)
  - ✅ Silence detection (max 5% silence)
  - ✅ Signal-to-noise ratio (min 20 dB)
- **Status**: Basic implementation (uses ffprobe, production would use audio analysis library)

#### Caption Quality Gate
- **Location**: `Backend/services/media_factory/quality_gates.py`
- **Checks**:
  - ✅ Word error heuristics
  - ✅ Max line length (42 characters)
  - ✅ Max words per line (7 words)
  - ✅ Timing accuracy (90% accuracy)
  - ✅ Safe area compliance (10% margin)
- **Status**: Implemented

#### Visual Quality Gate
- **Location**: `Backend/services/media_factory/quality_gates.py`
- **Checks**:
  - ✅ Max text density (30% of screen)
  - ✅ Motion cadence (pattern interrupt every 3-6 seconds)
  - ✅ Resolution/aspect ratio compliance
  - ✅ Color contrast (future)
- **Status**: Implemented

#### Publish Quality Gate
- **Location**: `Backend/services/media_factory/quality_gates.py`
- **Checks**:
  - ✅ File size (max 100 MB)
  - ✅ Codec compatibility (h264)
  - ✅ Duration limits (15-60 seconds)
  - ✅ Platform constraints (future)
- **Status**: Implemented

### Usage

```python
from services.media_factory.quality_gates import QualityGateManager

gate_manager = QualityGateManager()

# Check audio
audio_result = await gate_manager.check_audio("/path/to/audio.wav")
if audio_result.status != GateStatus.PASS:
    # Handle failure
    pass

# Check captions
caption_result = await gate_manager.check_captions(captions_data=words)

# Check visuals
visual_result = await gate_manager.check_visuals(timeline_data)

# Check publish readiness
publish_result = await gate_manager.check_publish("/path/to/video.mp4", "tiktok")

# Check all
all_results = await gate_manager.check_all(
    audio_path="/path/to/audio.wav",
    captions_data=words,
    timeline_data=timeline,
    video_path="/path/to/video.mp4",
    platform="tiktok"
)
```

### Integration with Pipeline

Quality gates should be called **between stages**:

```python
# After TTS stage
audio_result = await gate_manager.check_audio(tts_output_path)
if audio_result.status == GateStatus.FAIL:
    # Fail pipeline or retry
    raise QualityGateError(f"Audio quality failed: {audio_result.message}")

# After Remotion stage
publish_result = await gate_manager.check_publish(video_path, platform)
if publish_result.status == GateStatus.FAIL:
    # Fail pipeline
    raise QualityGateError(f"Publish quality failed: {publish_result.message}")
```

---

## 📊 Summary

### ✅ Completed

1. **Data Contracts** - 7 schemas defined (TrendCard, Cluster, Brief, Script, Timeline, RenderJob, PublishJob)
2. **Idempotency** - Idempotency keys, retry policies, DLQ
3. **Persistent Orchestration** - 5 database tables (jobs, stages, artifacts, events, DLQ)
4. **Event Bus Documentation** - Transport, guarantees, backpressure documented
5. **Quality Gates** - 4 gates implemented (Audio, Caption, Visual, Publish)

### 🚧 Future Enhancements

1. **Exactly-Once Delivery** - Add idempotency to event bus
2. **Advanced Audio Analysis** - Use audio analysis library (not just ffprobe)
3. **ML-Based Quality Scoring** - Train models for quality prediction
4. **Automatic Retry from DLQ** - Retry failed operations after fixes
5. **Quality Gate Dashboard** - Visualize quality metrics over time

---

## 📚 Files Created

### Data Contracts
- `Backend/services/media_factory/contracts/` (7 files)

### Idempotency & Retry
- `Backend/services/media_factory/idempotency.py`

### Database Models
- `Backend/database/models_media_factory.py`

### Quality Gates
- `Backend/services/media_factory/quality_gates.py`

### Documentation
- `Backend/docs/MEDIA_FACTORY_PRODUCTION_IMPROVEMENTS.md` (this file)

---

*These improvements make the Media Factory production-ready with proper error handling, persistence, and quality assurance.*

