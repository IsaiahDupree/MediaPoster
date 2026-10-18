# Video Rendering Pub/Sub Integration

**Date:** December 28, 2024  
**Status:** ✅ Integrated with Event Bus

---

## 🎯 Overview

The format-agnostic video rendering system is now fully integrated with the Event Bus pub/sub infrastructure. This enables:

- ✅ Asynchronous video rendering
- ✅ Event-driven architecture
- ✅ Progress tracking via events
- ✅ Scalable worker-based processing
- ✅ Integration with other services (TTS, Visuals, etc.)

---

## 📡 Event Topics

### Video Rendering Events

| Topic | Description | Payload |
|-------|-------------|---------|
| `video.render.requested` | New format-based render job | `{job_id, content, format_id, adapter}` |
| `video.render.started` | Job picked up by worker | `{job_id, format_id, adapter}` |
| `video.render.scene_graph.built` | Scene graph created | `{job_id, scene_count, total_duration}` |
| `video.render.scene.started` | Individual scene rendering started | `{job_id, scene_index, scene_type}` |
| `video.render.scene.completed` | Individual scene completed | `{job_id, scene_index, scene_type}` |
| `video.render.progress` | Progress update | `{job_id, progress, scenes_completed, total_scenes}` |
| `video.render.composing` | Composing final video | `{job_id}` |
| `video.render.completed` | Video rendered successfully | `{job_id, format_id, scene_count, total_duration}` |
| `video.render.failed` | Render error | `{job_id, error}` |

### Format Events

| Topic | Description | Payload |
|-------|-------------|---------|
| `video.format.selected` | Format selected for content | `{format_id, content_id}` |
| `video.format.validated` | Format validation passed | `{format_id, content_id}` |

---

## 🔄 Rendering Flow

### 1. Request Rendering

**API Endpoint:**
```
POST /api/video-formats/render
{
  "content": {...},  // Universal content schema
  "format_id": "explainer_v1",
  "adapter": "motion_canvas",
  "async_render": true
}
```

**Event Emitted:**
```json
{
  "topic": "video.render.requested",
  "payload": {
    "job_id": "uuid",
    "content": {...},
    "format_id": "explainer_v1",
    "adapter": "motion_canvas"
  }
}
```

### 2. Worker Processing

**FormatVideoRenderWorker** subscribes to `video.render.requested` and:

1. Validates format and content
2. Emits `video.render.started`
3. Builds scene graph
4. Emits `video.render.scene_graph.built`
5. Renders each scene
6. Emits `video.render.scene.started/completed` for each
7. Emits `video.render.progress` updates
8. Composes final video
9. Emits `video.render.composing`
10. Emits `video.render.completed` or `video.render.failed`

### 3. Progress Tracking

Subscribe to progress events:

```python
from services.event_bus import EventBus, Topics

bus = EventBus.get_instance()

async def on_progress(event):
    print(f"Progress: {event.payload['progress']:.1%}")
    print(f"Scenes: {event.payload['scenes_completed']}/{event.payload['total_scenes']}")

bus.subscribe(Topics.VIDEO_RENDER_PROGRESS, on_progress)
```

---

## 🏗️ Architecture

```
API Request
    ↓
POST /api/video-formats/render
    ↓
Event Bus: video.render.requested
    ↓
FormatVideoRenderWorker
    ↓
VideoRenderService.build_scene_graph()
    ↓
Scene Graph (List[Scene])
    ↓
Adapter Rendering (Motion Canvas / Remotion)
    ↓
Final Video
    ↓
Event Bus: video.render.completed
```

---

## 🔌 Integration Points

### TTS Integration

When TTS completes, it can trigger video rendering:

```python
# TTS emits: tts.completed
# FormatVideoRenderWorker listens and integrates audio
```

### Visuals Integration

When visuals complete, they can be integrated:

```python
# Visuals emits: visuals.completed
# FormatVideoRenderWorker listens and integrates assets
```

---

## 📊 Worker Configuration

**FormatVideoRenderWorker** is automatically started in `main.py`:

```python
from services.video_renderer.format_worker import FormatVideoRenderWorker

format_render_worker = FormatVideoRenderWorker(event_bus)
await format_render_worker.start()
```

**Subscriptions:**
- `video.render.requested` - Main rendering requests
- `tts.completed` - TTS audio integration
- `visuals.completed` - Visual asset integration

---

## 🧪 Testing

### Test Async Rendering

```python
import asyncio
from services.event_bus import EventBus, Topics

async def test_render():
    bus = EventBus.get_instance()
    
    # Subscribe to completion
    async def on_complete(event):
        print(f"✅ Render complete: {event.payload['job_id']}")
    
    bus.subscribe(Topics.VIDEO_RENDER_COMPLETED, on_complete)
    
    # Request render
    await bus.publish(
        Topics.VIDEO_RENDER_REQUESTED,
        {
            "job_id": "test-123",
            "content": {...},
            "format_id": "explainer_v1",
            "adapter": "motion_canvas"
        }
    )
    
    await asyncio.sleep(5)  # Wait for processing

asyncio.run(test_render())
```

---

## 📝 API Usage

### Synchronous (Preview Only)

```bash
curl -X POST http://localhost:8000/api/video-formats/render \
  -H "Content-Type: application/json" \
  -d '{
    "content": {...},
    "format_id": "explainer_v1",
    "async_render": false
  }'
```

**Returns:** Scene graph (no actual rendering)

### Asynchronous (Full Rendering)

```bash
curl -X POST http://localhost:8000/api/video-formats/render \
  -H "Content-Type: application/json" \
  -d '{
    "content": {...},
    "format_id": "explainer_v1",
    "async_render": true
  }'
```

**Returns:** Job ID and correlation ID

**Then subscribe to events:**
- `video.render.progress` - Progress updates
- `video.render.completed` - Completion notification

---

## ✅ Status

- ✅ Topics added to `Topics` class
- ✅ FormatVideoRenderWorker created
- ✅ API endpoints emit events
- ✅ Worker auto-started in main.py
- ✅ Progress tracking via events
- ⏳ Adapter rendering (TODO: Connect to Motion Canvas adapter)
- ⏳ TTS/Visuals integration (TODO: Implement handlers)

---

## 🚀 Next Steps

1. **Connect Adapter Rendering**
   - Integrate Motion Canvas adapter
   - Actually render scenes
   - Generate final video

2. **TTS Integration**
   - Listen to `tts.completed`
   - Integrate audio into render jobs

3. **Visuals Integration**
   - Listen to `visuals.completed`
   - Integrate visual assets

4. **WebSocket Updates**
   - Broadcast progress to frontend
   - Real-time UI updates

---

*For format system details, see `FORMAT_AGNOSTIC_ARCHITECTURE.md`*

