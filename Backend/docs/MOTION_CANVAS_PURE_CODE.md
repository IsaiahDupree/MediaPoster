# Motion Canvas - Pure Code Workflow

**Date:** December 28, 2024  
**Status:** ✅ Scene Generation Working, Rendering Requires Editor

---

## 🎯 Overview

Motion Canvas can be used **purely from code** to:
- ✅ **Generate scenes programmatically** (fully working)
- ⚠️ **Render to video** (requires editor or additional setup)

---

## ✅ What Works from Code

### 1. Scene Generation (100% Code)

You can create Motion Canvas scenes entirely from Python:

```python
from Backend.scripts.create_animated_text import create_animated_text_scene, update_project_file

# Create scene
scene_file = create_animated_text_scene(
    project_dir=Path("MotionCanvas"),
    scene_name="my_scene",
    text="Hello World",
    style="bounce",
    font_size=72,
)

# Update project
update_project_file(project_dir, "my_scene")
```

**Scripts:**
- `create_animated_text.py` - Create animated text scenes
- `complete_animated_text_workflow.py` - End-to-end scene creation

### 2. Using the Adapter (Code Generation)

The Motion Canvas adapter can generate scene code:

```python
from services.video_renderer import MotionCanvasAdapter, RenderRequest, Layer

adapter = MotionCanvasAdapter()
request = RenderRequest(
    job_id="test-123",
    composition="AnimatedText",
    layers=[
        Layer(
            id="text1",
            type="text",
            content="Hello World",
            style={"fontSize": 72, "color": "#ffffff"},
        )
    ],
    audio_tracks=[],
    duration=5.0,
    fps=30,
)

# This generates the scene file
response = await adapter.render(request)
```

---

## ⚠️ Rendering Limitations

Motion Canvas **does not have a direct CLI** for programmatic rendering. The rendering options are:

### Option 1: Editor (Recommended)

1. Generate scene from code (✅ works)
2. Start editor: `cd MotionCanvas && npm start`
3. Open http://localhost:9000
4. Select scene and export

### Option 2: Headless Browser (Advanced)

Requires Puppeteer/Playwright setup. Not currently implemented.

### Option 3: FFmpeg Fallback (Simple Text)

For simple text overlays, use FFmpeg instead:

```bash
python Backend/scripts/add_text_to_video.py \
  --text "Hello World" \
  --random
```

---

## 🚀 Complete Code Workflow

### Step 1: Create Scene from Code

```bash
python Backend/scripts/create_animated_text.py \
  --text "Hello World" \
  --style bounce \
  --font-size 72
```

This creates:
- `MotionCanvas/src/scenes/hello_world.tsx`
- Updates `MotionCanvas/src/project.ts`

### Step 2: Render (Choose One)

**Option A: Editor**
```bash
cd MotionCanvas && npm start
# Then export from UI
```

**Option B: FFmpeg (Simple Text)**
```bash
python Backend/scripts/add_text_to_video.py \
  --text "Hello World" \
  --random
```

---

## 📝 Available Scripts

| Script | Purpose | Status |
|--------|---------|--------|
| `create_animated_text.py` | Create animated text scene | ✅ Working |
| `complete_animated_text_workflow.py` | End-to-end scene creation | ✅ Working |
| `render_from_code.py` | Attempt programmatic render | ⚠️ Limited |
| `render_motion_canvas.py` | Render existing scene | ⚠️ Requires editor |
| `test_motion_canvas.py` | Test setup and list scenes | ✅ Working |

---

## 💡 Recommended Approach

### For Animated Graphics (Motion Canvas)

1. **Generate scene from code:**
   ```bash
   python Backend/scripts/create_animated_text.py --text "My Text" --style bounce
   ```

2. **Render via editor:**
   ```bash
   cd MotionCanvas && npm start
   # Export from UI
   ```

### For Simple Text Overlays (FFmpeg)

```bash
python Backend/scripts/add_text_to_video.py \
  --text "My Text" \
  --random \
  --position center
```

**Why:** FFmpeg is simpler, faster, and works 100% from code.

---

## 🔧 Using the Adapter Programmatically

The `MotionCanvasAdapter` can generate scenes programmatically:

```python
from services.video_renderer import MotionCanvasAdapter, RenderRequest, Layer

adapter = MotionCanvasAdapter(
    project_dir="/path/to/MotionCanvas"
)

# Create request
request = RenderRequest(
    job_id="my-job",
    composition="MyComposition",
    layers=[
        Layer(
            id="text1",
            type="text",
            content="Hello",
            style={"fontSize": 64},
        )
    ],
    audio_tracks=[],
    duration=5.0,
    fps=30,
)

# Generate scene (this works!)
response = await adapter.render(request)
# Note: Rendering may require editor
```

---

## 📚 Example: Complete Workflow

```python
#!/usr/bin/env python3
"""Create and render animated text from code"""

from pathlib import Path
from create_animated_text import create_animated_text_scene, update_project_file

# 1. Create scene
scene_file = create_animated_text_scene(
    project_dir=Path("MotionCanvas"),
    scene_name="my_animation",
    text="Hello from Code!",
    style="bounce",
    font_size=72,
)

# 2. Update project
update_project_file(Path("MotionCanvas"), "my_animation")

print(f"✅ Scene created: {scene_file}")
print("💡 Render with: cd MotionCanvas && npm start")
```

---

## 🎯 Summary

**What works 100% from code:**
- ✅ Scene generation
- ✅ Scene file creation
- ✅ Project file updates
- ✅ Code generation from Python

**What requires editor:**
- ⚠️ Video rendering (primary method)
- ⚠️ Preview/playback

**Alternative for pure code:**
- ✅ FFmpeg for simple text overlays
- ✅ Motion Canvas for complex animations (with editor)

---

## 🔗 Related Docs

- [Motion Canvas Setup](./MOTION_CANVAS_SETUP.md)
- [Video Text Overlay Guide](./VIDEO_TEXT_OVERLAY_GUIDE.md)
- [Video Renderer Adapter](./VIDEO_RENDERER_ADAPTER.md)

---

*Last Updated: December 28, 2024*

