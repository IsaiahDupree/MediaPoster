# Video Rendering Full Integration

**Date:** December 28, 2024  
**Status:** ✅ Complete Integration

---

## 🎯 Overview

The format-agnostic video rendering system is now fully integrated with:
- ✅ Motion Canvas adapter for actual rendering
- ✅ TTS integration (listens to `tts.completed`)
- ✅ Visuals integration (listens to `visuals.completed`)
- ✅ WebSocket broadcasting (automatic via Event Bus)

---

## 🔌 Integration Details

### 1. Motion Canvas Adapter Integration

**Status:** ✅ Integrated

The `FormatVideoRenderWorker` now uses the Motion Canvas adapter to render scenes:

```python
# Convert scene graph to RenderRequest
render_request = self._scene_to_render_request(
    scene=scene,
    job_id=f"{job_id}_scene_{i}",
    tts_audio=tts_audio,
    visuals_assets=visuals_assets,
)

# Render using adapter
response = await self.renderer.render(
    request=render_request,
    on_progress=on_progress
)
```

**Scene Conversion:**
- Scene data → RenderRequest with layers
- Title/description → Text layers
- Visual assets → Image layers
- TTS audio → Audio tracks

**Final Composition:**
- Rendered scenes concatenated using FFmpeg
- Final video saved to `Backend/data/generated_videos/{job_id}_final.mp4`

---

### 2. TTS Integration

**Status:** ✅ Integrated

**Event Subscription:**
- Listens to `tts.completed` events

**Integration Flow:**
1. TTS worker emits `tts.completed` with `audio_path`
2. FormatVideoRenderWorker stores TTS audio in `_pending_tts`
3. When rendering starts, TTS audio is integrated into scenes
4. Audio added as AudioTrack in RenderRequest

**Code:**
```python
async def _handle_tts_completed(self, event: Event):
    correlation_id = event.correlation_id
    audio_path = event.payload.get("audio_path")
    
    self._pending_tts[correlation_id] = {
        "audio_path": audio_path,
        "duration": event.payload.get("duration_seconds"),
        ...
    }
```

**Usage:**
- Use same `correlation_id` for TTS and video render requests
- TTS audio automatically integrated into video

---

### 3. Visuals Integration

**Status:** ✅ Integrated

**Event Subscription:**
- Listens to `visuals.completed` events

**Integration Flow:**
1. Visuals worker emits `visuals.completed` with `visuals_path`
2. FormatVideoRenderWorker stores visuals in `_pending_visuals`
3. When rendering starts, visuals are integrated into scenes
4. Visuals added as Image layers in RenderRequest

**Code:**
```python
async def _handle_visuals_completed(self, event: Event):
    correlation_id = event.correlation_id
    visuals_path = event.payload.get("visuals_path")
    
    if correlation_id not in self._pending_visuals:
        self._pending_visuals[correlation_id] = []
    
    self._pending_visuals[correlation_id].append({
        "visuals_path": visuals_path,
        "visuals_type": event.payload.get("visuals_type"),
        ...
    })
```

**Usage:**
- Use same `correlation_id` for visuals and video render requests
- Visuals automatically integrated into video (up to 3 per scene)

---

### 4. WebSocket Broadcasting

**Status:** ✅ Automatic

**How It Works:**
- `ConnectionManager` subscribes to `"*"` (all events)
- All `video.render.*` events are automatically broadcast
- Frontend can subscribe to specific topics

**Frontend Subscription:**
```typescript
const wsUrl = `${WS_URL}/api/ws/events?topics=video.render.*`;

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'event') {
    const eventData = message.event;
    
    // Handle video.render.progress
    if (eventData.topic === 'video.render.progress') {
      updateProgress(eventData.payload.progress);
    }
    
    // Handle video.render.completed
    if (eventData.topic === 'video.render.completed') {
      showVideo(eventData.payload.final_video_path);
    }
  }
};
```

**Available Events:**
- `video.render.requested`
- `video.render.started`
- `video.render.scene_graph.built`
- `video.render.scene.started`
- `video.render.scene.completed`
- `video.render.progress`
- `video.render.composing`
- `video.render.completed`
- `video.render.failed`

---

## 🔄 Complete Rendering Flow

### Step 1: Request Rendering

```bash
POST /api/video-formats/render
{
  "content": {...},
  "format_id": "explainer_v1",
  "async_render": true
}
```

**Event Emitted:** `video.render.requested`

---

### Step 2: Generate TTS (Optional)

```bash
# TTS worker processes tts.requested
# Emits: tts.completed
```

**Event:** `tts.completed` → Stored in `_pending_tts`

---

### Step 3: Generate Visuals (Optional)

```bash
# Visuals worker processes visuals.requested
# Emits: visuals.completed
```

**Event:** `visuals.completed` → Stored in `_pending_visuals`

---

### Step 4: Build Scene Graph

**Event:** `video.render.started`

**Worker:**
1. Validates format and content
2. Builds scene graph from content + format
3. Emits `video.render.scene_graph.built`

---

### Step 5: Render Scenes

**For each scene:**
1. Emit `video.render.scene.started`
2. Convert scene to RenderRequest
3. Integrate TTS audio (if available)
4. Integrate visuals (if available)
5. Render using Motion Canvas adapter
6. Emit `video.render.progress` updates
7. Emit `video.render.scene.completed`

---

### Step 6: Compose Final Video

**Event:** `video.render.composing`

**Worker:**
1. Concatenate rendered scenes using FFmpeg
2. Create final video
3. Emit `video.render.completed` with `final_video_path`

---

## 📊 Progress Tracking

**Progress Events:**
```json
{
  "topic": "video.render.progress",
  "payload": {
    "job_id": "uuid",
    "progress": 0.75,
    "scenes_completed": 3,
    "total_scenes": 4,
    "current_scene_progress": 0.5
  }
}
```

**Progress Calculation:**
- Overall: `scenes_completed / total_scenes`
- Per-scene: `current_scene_progress` (0.0 to 1.0)

---

## 🧪 Testing

### Test Complete Flow

```python
import asyncio
from services.event_bus import EventBus, Topics

async def test_complete_flow():
    bus = EventBus.get_instance()
    correlation_id = "test-123"
    
    # 1. Request TTS
    await bus.publish(
        Topics.TTS_REQUESTED,
        {
            "job_id": "tts-123",
            "text": "Hello world",
            "model": "indextts2"
        },
        correlation_id=correlation_id
    )
    
    # 2. Request Visuals
    await bus.publish(
        Topics.VISUALS_REQUESTED,
        {
            "job_id": "visuals-123",
            "visuals_type": "broll"
        },
        correlation_id=correlation_id
    )
    
    # 3. Request Video Render (will wait for TTS/Visuals)
    await bus.publish(
        Topics.VIDEO_RENDER_REQUESTED,
        {
            "job_id": "video-123",
            "content": {...},
            "format_id": "explainer_v1"
        },
        correlation_id=correlation_id
    )
    
    # Subscribe to completion
    async def on_complete(event):
        print(f"✅ Video complete: {event.payload['final_video_path']}")
    
    bus.subscribe(Topics.VIDEO_RENDER_COMPLETED, on_complete)
    
    await asyncio.sleep(30)  # Wait for processing

asyncio.run(test_complete_flow())
```

---

## ✅ Status Summary

| Component | Status | Details |
|-----------|--------|---------|
| **Motion Canvas Adapter** | ✅ Integrated | Renders scenes from RenderRequest |
| **TTS Integration** | ✅ Integrated | Listens to `tts.completed`, integrates audio |
| **Visuals Integration** | ✅ Integrated | Listens to `visuals.completed`, integrates assets |
| **WebSocket Broadcasting** | ✅ Automatic | All events broadcast via ConnectionManager |
| **Scene Graph Building** | ✅ Working | Content + Format → Scene Graph |
| **Final Composition** | ✅ Working | FFmpeg concatenation of rendered scenes |
| **Progress Tracking** | ✅ Working | Real-time progress via events |

---

## 🚀 Next Steps

1. **Error Handling**
   - Retry failed scenes
   - Partial video generation
   - Error recovery

2. **Performance Optimization**
   - Parallel scene rendering
   - Caching rendered scenes
   - Optimize FFmpeg composition

3. **Advanced Features**
   - Scene transitions
   - Background music integration
   - Custom animations per format

---

*For format system details, see `FORMAT_AGNOSTIC_ARCHITECTURE.md`*  
*For pub/sub integration, see `VIDEO_RENDERING_PUBSUB_INTEGRATION.md`*

