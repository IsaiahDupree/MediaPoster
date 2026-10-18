# Media Services Architecture: TTS, Remotion, and Video Matting

## Overview

This document outlines the pub/sub architecture for three new media creation services:
1. **TTS Service** - Text-to-speech with multiple Hugging Face model adapters
2. **Remotion Service** - Video editing and composition service
3. **Video Matting Service** - Object/people removal and compositing

All services integrate with MediaPoster's existing event bus system.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    MediaPoster Event Bus                        │
│              (Backend/services/event_bus/bus.py)                │
└──────────────┬──────────────────┬──────────────────┬───────────┘
               │                  │                  │
       ┌───────▼──────┐   ┌───────▼──────┐   ┌───────▼──────┐
       │  TTS Service │   │Remotion Service│   │Video Matting │
       │   Worker     │   │    Worker      │   │   Service    │
       └───────┬──────┘   └───────┬──────┘   └───────┬──────┘
               │                  │                  │
       ┌───────▼──────┐   ┌───────▼──────┐   ┌───────▼──────┐
       │ TTS Adapters │   │ Remotion API  │   │ Matting     │
       │              │   │                │   │ Models      │
       │ - IndexTTS2  │   │ - Composition │   │ - RMBG-1.4  │
       │ - Coqui XTTS │   │ - Rendering    │   │ - SAM2      │
       │ - HF Models  │   │ - Multi-source │   │ - Custom    │
       └──────────────┘   └────────────────┘   └─────────────┘
```

---

## 1. TTS Service

### Purpose
Convert text to speech using multiple TTS models with emotion control and voice cloning.

### Event Topics

```python
# TTS Topics
TTS_REQUESTED = "tts.requested"              # New TTS job
TTS_STARTED = "tts.started"                  # Job picked up
TTS_PROGRESS = "tts.progress"                # Progress update
TTS_COMPLETED = "tts.completed"              # Audio generated
TTS_FAILED = "tts.failed"                     # Generation error
TTS_MODEL_LOADED = "tts.model.loaded"        # Model ready
TTS_MODEL_UNLOADED = "tts.model.unloaded"    # Model freed
```

### Request Payload

```json
{
  "text": "Hello, this is a test.",
  "model": "indextts2",  // or "coqui_xtts", "hf_metavoice", etc.
  "voice_reference": "/path/to/voice.wav",
  "emotion": {
    "method": "vectors",  // "reference", "vectors", "natural"
    "vectors": {
      "happy": 0.8,
      "calm": 0.2
    },
    "weight": 0.8
  },
  "output_format": "wav",  // "wav", "mp3"
  "sample_rate": 22050,
  "correlation_id": "uuid-here"
}
```

### Response Payload

```json
{
  "job_id": "uuid",
  "audio_path": "/path/to/output.wav",
  "audio_url": "https://...",
  "duration_seconds": 5.2,
  "model_used": "indextts2",
  "generation_time": 3.4,
  "correlation_id": "uuid-here"
}
```

### Adapter Pattern

```python
class TTSAdapter(ABC):
    @abstractmethod
    async def generate(self, text: str, config: dict) -> AudioFile:
        pass
    
    @abstractmethod
    def get_model_info(self) -> dict:
        pass

class IndexTTS2Adapter(TTSAdapter):
    # Uses existing call_indextts2_api.py
    
class CoquiXTTSAdapter(TTSAdapter):
    # Uses Coqui XTTS
    
class HuggingFaceAdapter(TTSAdapter):
    # Generic HF model adapter
```

---

## 2. Remotion Service

### Purpose
Video editing, composition, and rendering using Remotion framework. Supports pulling videos/audio from multiple sources.

### Event Topics

```python
# Remotion Topics
REMOTION_REQUESTED = "remotion.requested"        # New render job
REMOTION_STARTED = "remotion.started"            # Job picked up
REMOTION_COMPOSING = "remotion.composing"        # Building composition
REMOTION_RENDERING = "remotion.rendering"         # Rendering video
REMOTION_PROGRESS = "remotion.progress"          # Progress update
REMOTION_COMPLETED = "remotion.completed"         # Video rendered
REMOTION_FAILED = "remotion.failed"              # Render error
```

### Request Payload

```json
{
  "composition": "MainComposition",
  "props": {
    "title": "My Video",
    "duration": 30,
    "sources": [
      {
        "type": "video",
        "source": "local",
        "path": "/path/to/video.mp4"
      },
      {
        "type": "audio",
        "source": "tts",
        "tts_job_id": "uuid-of-tts-job"
      },
      {
        "type": "video",
        "source": "url",
        "url": "https://example.com/video.mp4"
      },
      {
        "type": "video",
        "source": "mediaposter",
        "media_id": "uuid"
      }
    ],
    "captions": {
      "enabled": true,
      "style": "word-synced"
    }
  },
  "output": {
    "format": "mp4",
    "resolution": "1080p",
    "fps": 30
  },
  "correlation_id": "uuid-here"
}
```

### Response Payload

```json
{
  "job_id": "uuid",
  "video_path": "/path/to/output.mp4",
  "video_url": "https://...",
  "duration_seconds": 30.0,
  "render_time": 45.2,
  "file_size_mb": 125.3,
  "correlation_id": "uuid-here"
}
```

---

## 3. Video Matting Service

### Purpose
Remove objects/people from videos and composite into other videos using AI models.

### Event Topics

```python
# Video Matting Topics
MATTING_REQUESTED = "matting.requested"          # New matting job
MATTING_STARTED = "matting.started"              # Job picked up
MATTING_SEGMENTING = "matting.segmenting"         # Segmenting objects
MATTING_EXTRACTING = "matting.extracting"         # Extracting foreground
MATTING_COMPOSITING = "matting.compositing"        # Compositing into target
MATTING_PROGRESS = "matting.progress"            # Progress update
MATTING_COMPLETED = "matting.completed"          # Video processed
MATTING_FAILED = "matting.failed"                # Processing error
```

### Request Payload

```json
{
  "source_video": "/path/to/source.mp4",
  "target_video": "/path/to/target.mp4",  // Optional, for compositing
  "operation": "remove",  // "remove", "extract", "composite"
  "model": "rmbg-1.4",  // "rmbg-1.4", "sam2", "custom"
  "targets": {
    "type": "people",  // "people", "objects", "background"
    "specific": ["person1", "person2"]  // Optional specific targets
  },
  "output": {
    "format": "mp4",
    "preserve_alpha": true  // For compositing
  },
  "correlation_id": "uuid-here"
}
```

### Response Payload

```json
{
  "job_id": "uuid",
  "output_path": "/path/to/output.mp4",
  "mask_path": "/path/to/mask.mp4",  // Alpha channel mask
  "processing_time": 120.5,
  "model_used": "rmbg-1.4",
  "correlation_id": "uuid-here"
}
```

### Model Options

1. **RMBG-1.4** (Recommended)
   - Fast, accurate background removal
   - Good for people and objects
   - Python library available

2. **SAM2** (Meta AI)
   - Advanced segmentation
   - Can segment specific objects/people
   - More resource-intensive

3. **Custom Models**
   - Extensible for future models

---

## Service Workers

Each service runs as a background worker that:
1. Subscribes to request topics
2. Processes jobs asynchronously
3. Publishes progress and completion events
4. Handles errors gracefully

### Worker Structure

```python
class TTSWorker:
    def __init__(self):
        self.event_bus = EventBus.get_instance()
        self.adapters = {}
        
    async def start(self):
        self.event_bus.subscribe(Topics.TTS_REQUESTED, self.handle_request)
        
    async def handle_request(self, event: Event):
        # Process TTS request
        # Load appropriate adapter
        # Generate audio
        # Publish completion event
```

---

## API Endpoints

Each service exposes REST endpoints for direct requests:

```
POST /api/tts/generate
POST /api/remotion/render
POST /api/matting/process
GET  /api/tts/status/{job_id}
GET  /api/remotion/status/{job_id}
GET  /api/matting/status/{job_id}
```

---

## Integration with MediaPoster

### Workflow Example: TTS → Remotion → Publish

```
1. User requests TTS generation
   → tts.requested event

2. TTS Worker processes
   → tts.completed event (with audio_path)

3. Remotion Worker subscribes to tts.completed
   → Creates composition with TTS audio
   → remotion.requested event

4. Remotion Worker renders
   → remotion.completed event (with video_path)

5. Publishing Worker subscribes to remotion.completed
   → Publishes video to platforms
```

---

## File Structure

```
Backend/
├── services/
│   ├── tts/
│   │   ├── __init__.py
│   │   ├── worker.py              # TTS worker
│   │   ├── adapters/
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # TTSAdapter ABC
│   │   │   ├── indextts2.py      # IndexTTS2 adapter
│   │   │   ├── coqui_xtts.py     # Coqui XTTS adapter
│   │   │   └── huggingface.py    # Generic HF adapter
│   │   └── models.py              # TTS job models
│   ├── remotion/
│   │   ├── __init__.py
│   │   ├── worker.py              # Remotion worker
│   │   ├── composer.py            # Composition builder
│   │   ├── source_loader.py       # Multi-source loader
│   │   └── models.py              # Remotion job models
│   └── matting/
│       ├── __init__.py
│       ├── worker.py              # Matting worker
│       ├── models/
│       │   ├── __init__.py
│       │   ├── rmbg.py           # RMBG-1.4 implementation
│       │   ├── sam2.py            # SAM2 implementation
│       │   └── base.py             # MattingModel ABC
│       └── models.py              # Matting job models
├── api/
│   └── endpoints/
│       ├── tts.py                 # TTS API endpoints
│       ├── remotion.py            # Remotion API endpoints
│       └── matting.py             # Matting API endpoints
└── services/
    └── event_bus/
        └── topics.py              # Add new topics here
```

---

## Next Steps

1. ✅ Add topics to `topics.py`
2. ✅ Create TTS service with adapters
3. ✅ Create Remotion service
4. ✅ Research and implement video matting
5. ✅ Create API endpoints
6. ✅ Create workers
7. ✅ Integration tests
8. ✅ Documentation

