# Media Services Implementation Status

## Overview

This document tracks the implementation status of three new pub/sub services for media creation:
1. **TTS Service** - Text-to-speech with multiple model adapters
2. **Remotion Service** - Video editing and composition
3. **Video Matting Service** - Object/people removal and compositing

---

## ✅ TTS Service - COMPLETE (Foundation)

### Status: **Foundation Complete, Ready for Extension**

### What's Implemented:

1. **Event Topics** ✅
   - `tts.requested` - New TTS job
   - `tts.started` - Job picked up
   - `tts.progress` - Progress update
   - `tts.completed` - Audio generated
   - `tts.failed` - Generation error
   - `tts.model.loaded/unloaded` - Model lifecycle

2. **Data Models** ✅
   - `TTSRequest` - Request model with emotion config
   - `TTSResponse` - Response model
   - `TTSJobStatus` - Job tracking
   - `TTSModel` enum - Supported models
   - `EmotionMethod` enum - Emotion control methods

3. **Adapter Pattern** ✅
   - `TTSAdapter` base class (abstract)
   - `IndexTTS2Adapter` - Uses existing `call_indextts2_api.py`
   - Extensible for additional models

4. **TTS Worker** ✅
   - Subscribes to `tts.requested`
   - Processes jobs asynchronously
   - Emits progress and completion events
   - Error handling and job tracking

5. **API Endpoints** ✅
   - `POST /api/tts/generate` - Request TTS generation
   - `GET /api/tts/status/{job_id}` - Check job status (placeholder)
   - `GET /api/tts/models` - List available models

### Files Created:

```
Backend/
├── services/
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── models.py              ✅
│   │   ├── worker.py              ✅
│   │   └── adapters/
│   │       ├── __init__.py        ✅
│   │       ├── base.py            ✅
│   │       └── indextts2.py       ✅
└── api/
    └── endpoints/
        └── tts.py                 ✅
```

### Integration Points:

- ✅ Topics added to `Backend/services/event_bus/topics.py`
- ✅ Uses existing EventBus system
- ✅ Follows BaseWorker pattern
- ✅ Integrates with existing TTS code at `/Users/isaiahdupree/Documents/Software/TTS`

### Next Steps for TTS:

1. **Additional Adapters** (Future)
   - `CoquiXTTSAdapter` - For Coqui XTTS model
   - `HuggingFaceAdapter` - Generic HF model adapter
   - Support for more emotion methods

2. **Job Status Storage** (Future)
   - Store job status in database
   - Implement proper status lookup endpoint
   - Add job history and cleanup

3. **Testing** (Future)
   - Unit tests for adapters
   - Integration tests for worker
   - API endpoint tests

---

## 🚧 Remotion Service - NOT STARTED

### Status: **Design Complete, Implementation Pending**

### Design:

1. **Event Topics** (Defined)
   - `remotion.requested` - New render job
   - `remotion.started` - Job picked up
   - `remotion.composing` - Building composition
   - `remotion.rendering` - Rendering video
   - `remotion.progress` - Progress update
   - `remotion.completed` - Video rendered
   - `remotion.failed` - Render error

2. **Architecture** (Planned)
   - Remotion worker subscribes to `remotion.requested`
   - Multi-source loader (local, URL, TTS, MediaPoster)
   - Composition builder
   - Video renderer using Remotion CLI
   - Progress tracking and event emission

### Files to Create:

```
Backend/
├── services/
│   └── remotion/
│       ├── __init__.py
│       ├── models.py              # RemotionRequest, RemotionResponse
│       ├── worker.py               # RemotionWorker
│       ├── composer.py             # Composition builder
│       └── source_loader.py        # Multi-source loader
└── api/
    └── endpoints/
        └── remotion.py             # API endpoints
```

### Integration Points:

- Remotion code at `/Users/isaiahdupree/Documents/Software/Remotion`
- Uses Remotion CLI for rendering
- Can subscribe to `tts.completed` for audio integration

---

## 🚧 Video Matting Service - NOT STARTED

### Status: **Research Complete, Implementation Pending**

### Research Results:

1. **RMBG-1.4** (Recommended)
   - Fast, accurate background removal
   - Python library: `rembg` or `rembg[new]`
   - Good for people and objects
   - Easy to integrate

2. **SAM2** (Meta AI)
   - Advanced segmentation
   - Can segment specific objects/people
   - More resource-intensive
   - Requires more setup

3. **Custom Models**
   - Extensible architecture for future models

### Design:

1. **Event Topics** (Defined)
   - `matting.requested` - New matting job
   - `matting.started` - Job picked up
   - `matting.segmenting` - Segmenting objects
   - `matting.extracting` - Extracting foreground
   - `matting.compositing` - Compositing into target
   - `matting.progress` - Progress update
   - `matting.completed` - Video processed
   - `matting.failed` - Processing error

2. **Architecture** (Planned)
   - Matting worker subscribes to `matting.requested`
   - Model adapter pattern (similar to TTS)
   - Frame-by-frame processing
   - Alpha channel support for compositing
   - Progress tracking and event emission

### Files to Create:

```
Backend/
├── services/
│   └── matting/
│       ├── __init__.py
│       ├── models.py              # MattingRequest, MattingResponse
│       ├── worker.py               # MattingWorker
│       └── models/
│           ├── __init__.py
│           ├── base.py             # MattingModel ABC
│           ├── rmbg.py             # RMBG-1.4 implementation
│           └── sam2.py             # SAM2 implementation (future)
└── api/
    └── endpoints/
        └── matting.py              # API endpoints
```

### Integration Points:

- Can subscribe to `remotion.completed` for video processing
- Can integrate with MediaPoster media library

---

## Integration with MediaPoster

### Workflow Examples:

#### 1. TTS → Remotion → Publish
```
User requests TTS
  → tts.requested
  → tts.completed (audio_path)

Remotion subscribes to tts.completed
  → Creates composition with TTS audio
  → remotion.requested
  → remotion.completed (video_path)

Publishing subscribes to remotion.completed
  → Publishes video to platforms
```

#### 2. Video Matting → Remotion
```
User requests matting
  → matting.requested
  → matting.completed (output_video, mask)

Remotion uses matted video
  → remotion.requested (with matted source)
  → remotion.completed
```

---

## Next Steps

### Priority 1: Complete TTS Service
- [ ] Add job status database storage
- [ ] Implement proper status lookup
- [ ] Add Coqui XTTS adapter
- [ ] Add Hugging Face generic adapter
- [ ] Integration tests

### Priority 2: Implement Remotion Service
- [ ] Create Remotion models
- [ ] Create Remotion worker
- [ ] Implement multi-source loader
- [ ] Implement composition builder
- [ ] Create API endpoints
- [ ] Integration with TTS service

### Priority 3: Implement Video Matting Service
- [ ] Research and choose primary model (RMBG-1.4 recommended)
- [ ] Create matting models
- [ ] Create matting worker
- [ ] Implement RMBG-1.4 adapter
- [ ] Create API endpoints
- [ ] Integration with Remotion service

### Priority 4: Integration & Testing
- [ ] End-to-end workflow tests
- [ ] Performance optimization
- [ ] Error handling improvements
- [ ] Documentation
- [ ] Deployment guides

---

## Usage Examples

### TTS Service

```python
# Via API
POST /api/tts/generate
{
  "text": "Hello, world!",
  "model": "indextts2",
  "voice_reference": "/path/to/voice.wav",
  "emotion": {
    "method": "vectors",
    "vectors": {"happy": 0.8, "calm": 0.2}
  }
}

# Via Event Bus
await event_bus.publish(
    Topics.TTS_REQUESTED,
    {
        "text": "Hello, world!",
        "model": "indextts2",
        "voice_reference": "/path/to/voice.wav"
    }
)
```

### Remotion Service (Planned)

```python
# Via API
POST /api/remotion/render
{
  "composition": "MainComposition",
  "props": {
    "sources": [
      {"type": "audio", "source": "tts", "tts_job_id": "uuid"},
      {"type": "video", "source": "local", "path": "/path/to/video.mp4"}
    ]
  }
}
```

### Video Matting Service (Planned)

```python
# Via API
POST /api/matting/process
{
  "source_video": "/path/to/source.mp4",
  "target_video": "/path/to/target.mp4",
  "operation": "composite",
  "model": "rmbg-1.4"
}
```

---

## Notes

- All services follow the same pub/sub pattern
- Services can be used independently or in workflows
- Event-driven architecture enables loose coupling
- Extensible adapter pattern for multiple models
- All services integrate with MediaPoster's existing event bus

