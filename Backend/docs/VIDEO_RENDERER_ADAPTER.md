# Video Renderer Adapter Pattern

**Date:** December 26, 2024  
**Status:** Implemented ✅  
**Default Engine:** Motion Canvas

---

## 🎯 Overview

The Video Renderer service uses an **adapter pattern** to support multiple rendering engines:

- **Motion Canvas** (default) - Open-source, canvas-based, faster
- **Remotion** (fallback) - React-based, DOM-rendered, paid license

This allows switching between engines without changing the rest of the codebase.

---

## 🏗️ Architecture

```
VideoRenderer (Abstract Base)
├── MotionCanvasAdapter (Default) ✅
│   └── Canvas-based, imperative API
│   └── Open-source (MIT)
│   └── Faster rendering
│
└── RemotionAdapter (Fallback)
    └── React-based, declarative API
    └── Paid license ($100-500/mo)
    └── DOM rendering
```

---

## 📦 Components

### 1. Base Classes (`base.py`)

**`VideoRenderer`** - Abstract base class
- `render()` - Render video from request
- `validate_request()` - Validate request
- `get_supported_formats()` - List supported formats
- `get_default_resolution()` - Get default resolution

**`RenderRequest`** - Unified request format
- `job_id` - Unique job identifier
- `composition` - Composition name/template
- `layers` - List of layers (video, image, text, audio)
- `audio_tracks` - List of audio tracks
- `duration` - Video duration in seconds
- `fps` - Frames per second
- `resolution` - Output resolution

**`RenderResponse`** - Unified response format
- `job_id` - Job identifier
- `video_path` - Path to rendered video
- `duration_seconds` - Actual duration
- `file_size_bytes` - File size
- `render_time_seconds` - Time taken to render
- `engine_used` - Which engine was used

### 2. Motion Canvas Adapter (`motion_canvas_adapter.py`)

**Default renderer** - Open-source, canvas-based

**Features:**
- ✅ Imperative API (procedural)
- ✅ Canvas rendering (faster)
- ✅ Vector animations
- ✅ Real-time preview
- ✅ No licensing fees

**Usage:**
```python
from services.video_renderer import MotionCanvasAdapter

adapter = MotionCanvasAdapter(project_dir="/path/to/motion-canvas")
response = await adapter.render(request)
```

### 3. Remotion Adapter (`remotion_adapter.py`)

**Fallback renderer** - React-based, DOM-rendered

**Features:**
- ✅ React components
- ✅ DOM rendering
- ✅ Rich ecosystem
- ⚠️ Paid license required ($100-500/mo)

**Usage:**
```python
from services.video_renderer import RemotionAdapter

adapter = RemotionAdapter(project_dir="/path/to/remotion")
response = await adapter.render(request)
```

### 4. Factory (`factory.py`)

**Creates renderer instances** with default to Motion Canvas

**Usage:**
```python
from services.video_renderer import VideoRendererFactory

# Default (Motion Canvas)
renderer = VideoRendererFactory.create_default()

# Specific engine
renderer = VideoRendererFactory.create(engine=RenderEngine.REMOTION)

# Environment override
# Set VIDEO_RENDERER_ENGINE=motion_canvas or remotion
```

### 5. Worker (`worker.py`)

**Event-driven worker** using adapter pattern

**Subscribes to:**
- `remotion.requested` (legacy, will be renamed)
- `tts.completed` (for audio integration)
- `matting.completed` (for video integration)

**Emits:**
- `remotion.started` / `video.render.started`
- `remotion.composing` / `video.render.composing`
- `remotion.rendering` / `video.render.rendering`
- `remotion.progress` / `video.render.progress`
- `remotion.completed` / `video.render.completed`
- `remotion.failed` / `video.render.failed`

---

## 🚀 Usage

### Basic Usage

```python
from services.video_renderer import VideoRendererFactory, RenderRequest, Layer, AudioTrack

# Create renderer (default: Motion Canvas)
renderer = VideoRendererFactory.create_default()

# Build request
request = RenderRequest(
    job_id="job_123",
    composition="ExplainerVideo",
    layers=[
        Layer(
            id="text_1",
            type="text",
            content="Hello World",
            start=0.0,
            end=5.0,
            position={"x": 0, "y": 0}
        )
    ],
    audio_tracks=[
        AudioTrack(
            id="voice_1",
            source="/path/to/voice.wav",
            start=0.0,
            volume=1.0
        )
    ],
    duration=30.0,
    fps=30
)

# Render
response = await renderer.render(request)
print(f"Video: {response.video_path}")
print(f"Engine: {response.engine_used}")
```

### With Progress Callback

```python
async def on_progress(progress: float):
    print(f"Progress: {progress * 100:.1f}%")

response = await renderer.render(request, on_progress=on_progress)
```

### Switching Engines

```python
# Use Remotion instead
from services.video_renderer import VideoRendererFactory, RenderEngine

renderer = VideoRendererFactory.create(engine=RenderEngine.REMOTION)
response = await renderer.render(request)
```

### Environment Variable Override

```bash
# Use Remotion
export VIDEO_RENDERER_ENGINE=remotion

# Use Motion Canvas (default)
export VIDEO_RENDERER_ENGINE=motion_canvas
```

---

## 🔄 Migration from Remotion

### Current State
- Remotion worker exists (`services/remotion/worker.py`)
- Uses RemotionComposer
- Direct Remotion CLI calls

### New State
- Video renderer worker (`services/video_renderer/worker.py`)
- Uses adapter pattern
- Default: Motion Canvas
- Fallback: Remotion

### Migration Steps

1. **Keep Remotion worker** (for backward compatibility)
2. **Use Video Renderer worker** (for new code)
3. **Gradually migrate** compositions to Motion Canvas
4. **Remove Remotion dependency** (optional, if not needed)

---

## 📊 Comparison

| Feature | Motion Canvas | Remotion |
|---------|---------------|----------|
| **Default** | ✅ Yes | ❌ No |
| **License** | ✅ Open-source | ⚠️ Paid ($100-500/mo) |
| **Rendering** | Canvas | DOM |
| **Performance** | ✅ Faster | Slower |
| **API Style** | Imperative | Declarative |
| **Best For** | Automation, vectors | Complex media |

---

## 🎯 Why Motion Canvas is Default

1. **Cost**: Open-source (no licensing fees)
2. **Performance**: Canvas rendering is faster
3. **Use Case**: Better for automated video generation
4. **Fit**: Perfect for explainer/educational videos
5. **Future**: Growing open-source community

---

## 🔮 Future Enhancements

1. **More Adapters**: Add support for other engines
2. **Auto-fallback**: Automatically fallback if default fails
3. **Performance Metrics**: Track render times per engine
4. **A/B Testing**: Compare outputs from different engines
5. **Composition Templates**: Shared templates across engines

---

*Last Updated: December 26, 2024*

