# Video Text Overlay Guide

**Date:** December 28, 2024  
**Status:** ✅ Working

---

## 🎯 Overview

This guide shows how to add text overlays to videos using different methods:

1. **FFmpeg** (Recommended) - Simple, fast, works immediately
2. **Motion Canvas** - For vector animations and programmatic graphics
3. **Remotion** - React-based, good for complex compositions

---

## 🚀 Quick Start: FFmpeg (Recommended)

### Why FFmpeg?

- ✅ **Simple** - One command, works immediately
- ✅ **Fast** - No project setup required
- ✅ **Reliable** - Industry standard
- ✅ **Flexible** - Supports all video formats
- ✅ **Perfect for overlays** - Designed for this use case

### Usage

```bash
# Add text to a random video
python Backend/scripts/add_text_to_video.py --random --text "Hello World!"

# Add text to specific video
python Backend/scripts/add_text_to_video.py \
  --video path/to/video.mp4 \
  --text "My Text Overlay" \
  --position center \
  --font-size 72 \
  --font-color white

# Custom position
python Backend/scripts/add_text_to_video.py \
  --video video.mp4 \
  --text "Custom Position" \
  --position custom \
  --x 100 \
  --y 200

# Timed text (appears at 5s, lasts 3s)
python Backend/scripts/add_text_to_video.py \
  --video video.mp4 \
  --text "Timed Text" \
  --start-time 5.0 \
  --duration 3.0
```

### Options

| Option | Description | Default |
|--------|-------------|----------|
| `--video` | Input video path | Required (or use `--random`) |
| `--random` | Use random video from library | False |
| `--text` | Text to overlay | Required |
| `--position` | Position: `top`, `center`, `bottom`, `custom` | `center` |
| `--font-size` | Font size in pixels | 48 |
| `--font-color` | Font color (e.g., `white`, `yellow`, `#FF0000`) | `white` |
| `--x` | X position (for custom) | Auto-centered |
| `--y` | Y position (for custom) | Auto-centered |
| `--start-time` | When to show text (seconds) | 0.0 |
| `--duration` | How long to show text (seconds) | Entire video |
| `--output` | Output video path | `{input}_text.mp4` |

---

## 🎨 Motion Canvas (Advanced)

### When to Use Motion Canvas

- ✅ **Vector animations** - Animated graphics, shapes, text
- ✅ **Explainer videos** - Educational content with animations
- ✅ **Programmatic generation** - Generate videos from code/JSON
- ❌ **Not ideal for** - Simple text overlays on existing videos

### Setup

```bash
# Install Motion Canvas
npm install -g @motion-canvas/core @motion-canvas/2d

# Create project
mkdir MotionCanvas && cd MotionCanvas
npx motion-canvas init
```

### Usage

```bash
python Backend/scripts/add_text_with_motion_canvas.py \
  --text "Animated Text" \
  --position center \
  --font-size 72 \
  --duration 5.0
```

### Motion Canvas vs FFmpeg

| Feature | FFmpeg | Motion Canvas |
|---------|--------|---------------|
| **Text overlay on video** | ✅ Perfect | ⚠️ Not ideal |
| **Vector animations** | ❌ No | ✅ Excellent |
| **Setup complexity** | ✅ None | ⚠️ Requires project |
| **Rendering speed** | ✅ Fast | ⚠️ Slower |
| **Use case** | Video overlays | Animated graphics |

**Recommendation:** Use FFmpeg for text overlays, Motion Canvas for animated graphics.

---

## 🎬 Remotion (React-based)

### When to Use Remotion

- ✅ **Complex compositions** - Multiple layers, effects
- ✅ **React knowledge** - If you know React
- ✅ **Media-heavy** - Lots of images, videos, effects
- ❌ **Cost** - Paid license ($100-500/month for companies)

### Setup

```bash
# Install Remotion
npm install -g remotion

# Create project
npx create-remotion
```

### Usage

Remotion uses React components. See `Backend/services/video_renderer/remotion_adapter.py` for integration.

---

## 📊 Comparison

| Method | Best For | Setup | Speed | Cost |
|--------|---------|-------|-------|------|
| **FFmpeg** | Text overlays, simple edits | ✅ None | ✅ Fast | ✅ Free |
| **Motion Canvas** | Vector animations, explainers | ⚠️ Project setup | ⚠️ Medium | ✅ Free |
| **Remotion** | Complex compositions | ⚠️ Project setup | ⚠️ Slower | ❌ Paid |

---

## 🎯 Recommendations

### For Text Overlays on Videos
**→ Use FFmpeg** (`add_text_to_video.py`)

### For Animated Graphics
**→ Use Motion Canvas** (`add_text_with_motion_canvas.py`)

### For Complex Compositions
**→ Use Remotion** (if budget allows)

---

## 📝 Examples

### Example 1: Simple Text Overlay

```bash
python Backend/scripts/add_text_to_video.py \
  --random \
  --text "Subscribe for more!" \
  --position bottom \
  --font-size 60 \
  --font-color yellow
```

### Example 2: Timed Text

```bash
python Backend/scripts/add_text_to_video.py \
  --video my_video.mp4 \
  --text "Key Moment" \
  --start-time 10.0 \
  --duration 2.0 \
  --position center \
  --font-size 80
```

### Example 3: Multiple Text Overlays

For multiple text overlays, you'd need to chain FFmpeg commands or use a video editing tool.

---

## 🔧 Integration with MediaPoster

The text overlay script integrates with MediaPoster's video rendering system:

- **Video Renderer Adapter** (`Backend/services/video_renderer/`) - Supports both Motion Canvas and Remotion
- **FFmpeg Integration** - Can be used directly or via the adapter pattern
- **Video Library** - Works with videos in `Backend/data/rendered_videos/` and iPhone imports

---

## 🐛 Troubleshooting

### FFmpeg Not Found

```bash
# macOS
brew install ffmpeg

# Verify
ffmpeg -version
```

### Motion Canvas Not Working

Motion Canvas requires a full project setup. For simple text overlays, use FFmpeg instead.

### Video Not Found

The script searches in:
- `Backend/test_video_analysis.mp4`
- `Backend/data/rendered_videos/*.mp4`
- `local_storage/videos/*.mp4`
- `/Users/isaiahdupree/Documents/IphoneImport/*.mp4`

---

## 📚 Further Reading

- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [Motion Canvas Docs](https://motioncanvas.io/)
- [Remotion Docs](https://www.remotion.dev/)
- [Video Renderer Adapter](./VIDEO_RENDERER_ADAPTER.md)

---

*Last Updated: December 28, 2024*

