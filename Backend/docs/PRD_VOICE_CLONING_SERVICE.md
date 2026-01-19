# PRD: Voice Cloning Service Integration

## Overview

A serverless voice cloning service deployed on Modal Labs using IndexTTS-2 for high-quality voice synthesis. This service integrates with MediaPoster's Media Factory pipeline to enable AI-generated voiceovers for content creation.

## Business Value

- **Scalable Voice Content**: Generate unlimited voiceovers without recording
- **Brand Consistency**: Clone brand voices for consistent content
- **Cost Efficient**: Scales to zero when idle (~$0 when not in use)
- **Fast Turnaround**: Generate voiceovers in seconds vs hours of recording

## Integration with Media Factory

```
┌─────────────────────────────────────────────────────────────────┐
│                     MEDIA FACTORY PIPELINE                       │
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │  Script  │───▶│ VOICE CLONE  │───▶│   B-Roll     │           │
│  │  (Text)  │    │   SERVICE    │    │  Assembly    │           │
│  └──────────┘    └──────────────┘    └──────────────┘           │
│                         │                    │                   │
│                         ▼                    ▼                   │
│                  ┌──────────────┐    ┌──────────────┐           │
│                  │ Voice Audio  │    │   Remotion   │           │
│                  │   (WAV)      │───▶│   Render     │           │
│                  └──────────────┘    └──────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### Phase 1: Core Voice Cloning Service

#### VC-001: Modal Voice Clone Deployment Script
- **Description**: Python script to deploy IndexTTS-2 on Modal Labs
- **Files**: `scripts/modal_voice_clone.py`
- **Acceptance Criteria**:
  - Deploys to Modal with `modal deploy`
  - Uses T4 GPU with 16GB memory
  - Scales to zero after 5 min idle
  - Health endpoint returns status

#### VC-002: Voice Reference Management
- **Description**: Store and manage voice reference files
- **Files**: `Backend/services/voice_reference_service.py`, `Backend/api/endpoints/voice_references.py`
- **Acceptance Criteria**:
  - CRUD endpoints for voice references
  - Store in Supabase storage bucket
  - Validate audio format (WAV, MP3, FLAC)
  - Metadata: name, duration, sample_rate, created_at

#### VC-003: Voice Clone API Client
- **Description**: Python client to call Modal voice clone service
- **Files**: `Backend/services/voice_clone_client.py`
- **Acceptance Criteria**:
  - Async HTTP client with retries
  - Handle cold start timeouts (60s)
  - Base64 encode/decode audio
  - Emotion control parameters

#### VC-004: Voice Clone Database Schema
- **Description**: Database tables for voice cloning
- **Files**: `Backend/migrations/voice_cloning.sql`
- **Schema**:
  ```sql
  CREATE TABLE voice_references (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    duration_seconds FLOAT,
    sample_rate INT,
    brand_id UUID REFERENCES brands(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
  );
  
  CREATE TABLE voice_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    voice_reference_id UUID REFERENCES voice_references(id),
    input_text TEXT NOT NULL,
    output_path TEXT,
    duration_seconds FLOAT,
    emotion_method TEXT DEFAULT 'Same as the voice reference',
    emotion_weight FLOAT DEFAULT 0.8,
    status TEXT DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
  );
  ```

### Phase 2: Media Factory Integration

#### VC-005: TTS Pipeline Voice Clone Option
- **Description**: Add voice cloning as TTS option in media factory
- **Files**: `Backend/services/media_factory/tts_service.py`
- **Acceptance Criteria**:
  - Option to use cloned voice vs standard TTS
  - Falls back to standard TTS on error
  - Caches generated audio by text hash

#### VC-006: Script-to-Voiceover Worker
- **Description**: Background worker to generate voiceovers from scripts
- **Files**: `Backend/workers/voiceover_worker.py`
- **Acceptance Criteria**:
  - Processes queue of voiceover requests
  - Splits long text into chunks (<500 chars)
  - Concatenates audio segments
  - Updates job status

#### VC-007: Voice Selection UI Component
- **Description**: Dashboard UI to select/preview voice references
- **Files**: `dashboard/components/voice-selector.tsx`
- **Acceptance Criteria**:
  - List available voice references
  - Audio preview player
  - Upload new voice reference
  - Select for content generation

#### VC-008: Batch Voiceover Generation
- **Description**: Generate voiceovers for multiple scripts
- **Files**: `Backend/api/endpoints/batch_voiceover.py`
- **Acceptance Criteria**:
  - Accept array of text inputs
  - Process in parallel (max 5 concurrent)
  - Return job ID for status polling
  - Webhook on completion

### Phase 3: Advanced Features

#### VC-009: Emotion Control API
- **Description**: Fine-grained emotion control for voice output
- **Files**: `Backend/services/voice_emotion_service.py`
- **Acceptance Criteria**:
  - Emotion options: Neutral, Happy, Sad, Angry, Excited
  - Emotion weight slider (0.0-1.0)
  - Preview before generation

#### VC-010: Voice Analytics Dashboard
- **Description**: Track voice clone usage and costs
- **Files**: `dashboard/app/analytics/voice/page.tsx`
- **Acceptance Criteria**:
  - Total generations count
  - Minutes of audio generated
  - Cost estimates
  - Most used voice references

#### VC-011: Voice Clone Caching Layer
- **Description**: Cache frequently used voice+text combinations
- **Files**: `Backend/services/voice_cache_service.py`
- **Acceptance Criteria**:
  - Hash-based cache key (voice_id + text_hash)
  - Redis cache with 24h TTL
  - Cache hit/miss metrics
  - Cache invalidation API

#### VC-012: Multi-Voice Content
- **Description**: Generate content with multiple voices (dialogue)
- **Files**: `Backend/services/multi_voice_service.py`
- **Acceptance Criteria**:
  - Parse script for speaker tags
  - Map speakers to voice references
  - Generate and interleave audio
  - Timing/pacing controls

## API Reference

### Clone Voice Endpoint

**Internal Endpoint:** `POST /api/v1/voice/clone`

**Request:**
```json
{
  "voice_reference_id": "uuid",
  "text": "Text to synthesize",
  "emotion_method": "Same as the voice reference",
  "emotion_weight": 0.8
}
```

**Response:**
```json
{
  "id": "generation-uuid",
  "audio_url": "https://storage.../output.wav",
  "duration_seconds": 5.2,
  "status": "completed"
}
```

### Voice References CRUD

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/voice/references` | List all voice references |
| POST | `/api/v1/voice/references` | Upload new voice reference |
| GET | `/api/v1/voice/references/{id}` | Get voice reference details |
| DELETE | `/api/v1/voice/references/{id}` | Delete voice reference |
| POST | `/api/v1/voice/references/{id}/preview` | Generate preview audio |

## Voice Reference Best Practices

| Aspect | Recommendation |
|--------|----------------|
| **Duration** | 10-30 seconds |
| **Format** | WAV or MP3 |
| **Sample Rate** | 22050 Hz or higher |
| **Quality** | Clear, minimal background noise |
| **Content** | Natural speech with varied intonation |

## Modal Service Configuration

```python
# Cost-optimized settings
app = modal.App("voice-clone-indextts2")

@app.function(
    gpu="T4",
    memory=16384,
    timeout=600,
    scaledown_window=300,  # 5 min idle -> scale to zero
)
```

## Cost Estimates

| Usage | Estimated Cost |
|-------|----------------|
| Idle | $0 (scales to zero) |
| Cold start | ~30-60 seconds |
| Per generation | ~$0.001-0.005 |
| 1000 generations/month | ~$1-5 |

## Error Handling

| Error | Cause | Resolution |
|-------|-------|------------|
| Cold start timeout | First request after idle | Retry with 90s timeout |
| Audio decode error | Invalid voice reference | Validate format on upload |
| Rate limit | HuggingFace space limits | Add request queue with delays |
| GPU quota | Modal usage limits | Upgrade Modal plan |

## Security Considerations

1. **Voice Reference Storage**: Private Supabase bucket with RLS
2. **API Authentication**: Bearer token required
3. **Rate Limiting**: Max 10 requests/minute per user
4. **Content Filtering**: Block harmful text inputs

## Testing Requirements

| Test | Description |
|------|-------------|
| `test_voice_clone_client.py` | Unit tests for Modal client |
| `test_voice_reference_crud.py` | API endpoint tests |
| `test_media_factory_integration.py` | End-to-end pipeline test |
| `test_voice_caching.py` | Cache behavior tests |

## Deployment Checklist

- [ ] Modal account setup with GPU quota
- [ ] Deploy `modal_voice_clone.py`
- [ ] Create Supabase storage bucket `voice-references`
- [ ] Run database migrations
- [ ] Configure environment variables
- [ ] Test health endpoint
- [ ] Generate first voiceover

## Environment Variables

```bash
# Modal
MODAL_VOICE_CLONE_ENDPOINT=https://YOUR_USERNAME--voice-clone-indextts2-api-clone-voice.modal.run

# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
VOICE_REFERENCES_BUCKET=voice-references
```

## Related Documentation

- [Media Factory PRD](./MEDIA_FACTORY_PRD.md)
- [Modal Labs Docs](https://modal.com/docs)
- [IndexTTS-2 HuggingFace](https://huggingface.co/spaces/IndexTeam/IndexTTS-2-Demo)
