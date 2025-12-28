# Motion Canvas Setup Guide

**Date:** December 28, 2024  
**Status:** ✅ Project Created

---

## 🎯 Overview

Motion Canvas is set up for creating animated graphics and text overlays. It's perfect for:
- ✅ Vector animations
- ✅ Animated text graphics
- ✅ Explainer videos
- ✅ Programmatic video generation

---

## 📦 Project Structure

```
MotionCanvas/
├── package.json          # Dependencies and scripts
├── vite.config.ts        # Vite configuration
├── tsconfig.json         # TypeScript configuration
└── src/
    ├── project.ts        # Main project file (registers scenes)
    └── scenes/          # Scene files
        ├── animatedText.tsx
        ├── videoTextOverlay.tsx
        └── ...
```

---

## 🚀 Quick Start

### 1. Start the Editor

```bash
cd MotionCanvas
npm start
```

The editor will open at: **http://localhost:9000**

### 2. Create Animated Text

```bash
# Create a new animated text scene
python Backend/scripts/create_animated_text.py \
  --text "Hello World!" \
  --style bounce \
  --font-size 72

# Or create without rendering (just the scene file)
python Backend/scripts/create_animated_text.py \
  --text "My Text" \
  --style fade \
  --no-render
```

### 3. List Available Scenes

```bash
python Backend/scripts/test_motion_canvas.py --list
```

### 4. Test Setup

```bash
python Backend/scripts/test_motion_canvas.py --check
```

---

## 🎨 Animation Styles

Available animation styles:

| Style | Description |
|-------|-------------|
| `fade` | Fade in/out (default) |
| `bounce` | Bounce animation with scale |
| `slide` | Slide in from bottom |
| `scale` | Scale up/down animation |

---

## 📝 Creating Scenes

### Method 1: Using the Script (Recommended)

```bash
python Backend/scripts/create_animated_text.py \
  --text "Your Text Here" \
  --style bounce \
  --font-size 64 \
  --color "#FF0000"
```

### Method 2: Manual Creation

1. Create a new file in `MotionCanvas/src/scenes/myScene.tsx`
2. Use the template from `animatedText.tsx` as a starting point
3. Update `project.ts` to include your scene

---

## 🎬 Rendering

Motion Canvas uses Vite for rendering. There are two ways to render:

### Option 1: Via Editor (Recommended)

1. Start the editor: `npm start`
2. Open http://localhost:9000
3. Select your scene
4. Click "Export" → Choose format (MP4, PNG sequence, etc.)

### Option 2: Via Command Line

```bash
cd MotionCanvas
npm run build -- --mode render
```

Note: Command-line rendering may require additional configuration.

---

## 🔧 Integration with MediaPoster

The Motion Canvas adapter is in:
- `Backend/services/video_renderer/motion_canvas_adapter.py`

It can be used programmatically:

```python
from services.video_renderer import MotionCanvasAdapter, RenderRequest, Layer

renderer = MotionCanvasAdapter(
    project_dir="/path/to/MotionCanvas"
)

request = RenderRequest(
    job_id="test-123",
    composition="animatedText",
    layers=[
        Layer(
            id="text1",
            type="text",
            content="Hello World",
            position={"x": 0, "y": 0},
        )
    ],
    audio_tracks=[],
    duration=5.0,
    fps=30,
)

response = await renderer.render(request)
print(f"Video: {response.video_path}")
```

---

## 📚 Scene Examples

### Example 1: Simple Fade Text

```typescript
import {makeScene2D} from '@motion-canvas/2d';
import {Txt} from '@motion-canvas/2d/lib/components';
import {createRef} from '@motion-canvas/core';

export default makeScene2D(function* (view) {
  const textRef = createRef<Txt>();
  const text = new Txt({
    ref: textRef,
    text: 'Hello World',
    fontSize: 72,
    fill: '#ffffff',
  });
  
  view.add(text);
  
  textRef().opacity(0);
  yield* textRef().opacity(1, 1);
  yield* textRef().opacity(0, 1);
});
```

### Example 2: Bounce Animation

```typescript
// See animatedText.tsx for full example
// Features: scale, bounce, fade animations
```

---

## 🐛 Troubleshooting

### Editor Won't Start

```bash
# Check if dependencies are installed
cd MotionCanvas
npm install

# Check Node.js version (needs 16+)
node --version
```

### Scene Not Showing

1. Check that scene is in `src/scenes/`
2. Verify scene is imported in `src/project.ts`
3. Check browser console for errors

### Rendering Fails

- Motion Canvas primarily uses the editor for rendering
- Command-line rendering may require additional setup
- For production, consider using the editor's export feature

---

## 🆚 Motion Canvas vs FFmpeg

| Feature | Motion Canvas | FFmpeg |
|---------|---------------|--------|
| **Text overlay on video** | ⚠️ Not ideal | ✅ Perfect |
| **Animated graphics** | ✅ Excellent | ❌ No |
| **Vector animations** | ✅ Excellent | ❌ No |
| **Setup complexity** | ⚠️ Requires project | ✅ None |
| **Rendering speed** | ⚠️ Slower | ✅ Fast |
| **Best for** | Animated graphics | Video overlays |

**Recommendation:**
- Use **FFmpeg** for simple text overlays on existing videos
- Use **Motion Canvas** for animated graphics and vector animations

---

## 📖 Resources

- [Motion Canvas Documentation](https://motioncanvas.io/)
- [Motion Canvas GitHub](https://github.com/motion-canvas/motion-canvas)
- [Video Renderer Adapter](./VIDEO_RENDERER_ADAPTER.md)

---

## ✅ Current Status

- ✅ Project structure created
- ✅ Dependencies installed
- ✅ Example scenes created (`animatedText`, `videoTextOverlay`)
- ✅ Python scripts for scene creation
- ✅ Integration with MediaPoster adapter

**Next Steps:**
1. Start editor: `cd MotionCanvas && npm start`
2. Create animated text: `python Backend/scripts/create_animated_text.py --text "Test"`
3. Export from editor

---

*Last Updated: December 28, 2024*

