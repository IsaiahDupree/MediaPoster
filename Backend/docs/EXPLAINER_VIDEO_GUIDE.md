# Explainer Video Generation Guide

**Date:** December 28, 2024  
**Status:** ✅ Working

---

## 🎯 Overview

Generate explainer videos with:
- ✅ AI-generated scripts
- ✅ Your voice via Hugging Face TTS
- ✅ Animated text overlays
- ✅ Professional video composition

---

## 🚀 Quick Start

### Prerequisites

1. **Voice Reference Audio**
   - Record 10-30 seconds of your voice
   - Save as WAV format (16kHz or 22kHz recommended)
   - Clear, quiet recording works best

2. **Hugging Face Token** (optional if TTS service is running)
   - Get token from: https://huggingface.co/settings/tokens
   - Needs access to IndexTTS2 model

3. **Backend Running** (optional)
   - If TTS service is running, no token needed
   - Otherwise, provide `--hf-token`

### Generate Video

```bash
python Backend/scripts/generate_thermodynamics_explainer.py \
  --voice-reference /path/to/your_voice.wav \
  --duration 60 \
  --hf-token YOUR_HF_TOKEN
```

---

## 📝 Video Formats & Briefs

### Supported Formats

The system supports multiple video formats:

| Format | Duration | Aspect Ratio | Use Case |
|--------|----------|--------------|----------|
| **Short Form** | 15-60s | 9:16 (vertical) | TikTok, Reels, Shorts |
| **Long Form** | 2-15min | 16:9 (horizontal) | YouTube, tutorials |
| **Explainer** | 30-90s | 9:16 or 16:9 | Educational content |

### Creative Brief Structure

```python
CreativeBrief(
    content_type=ContentType.TREND_BREAKDOWN,
    primary_text="Main content",
    duration_seconds=60,
    aspect_ratio="9:16",  # or "16:9"
    # ... style settings
)
```

---

## 🎤 Voice Generation

### Using TTS Service (Recommended)

If the backend TTS service is running:

```bash
# No token needed - uses local service
python Backend/scripts/generate_thermodynamics_explainer.py \
  --voice-reference voice.wav
```

### Using Hugging Face Directly

```bash
python Backend/scripts/generate_thermodynamics_explainer.py \
  --voice-reference voice.wav \
  --hf-token YOUR_TOKEN
```

### Voice Reference Requirements

- **Format**: WAV (recommended) or MP3
- **Duration**: 10-30 seconds
- **Quality**: Clear, minimal background noise
- **Sample Rate**: 16kHz or 22kHz

**Tips:**
- Record in a quiet room
- Speak naturally and clearly
- Include various phonemes (different sounds)
- Avoid background music or noise

---

## 📚 Customizing Content

### Modify Script

Edit `generate_thermodynamics_script()` in the script to customize:

```python
def generate_thermodynamics_script(duration_seconds: int = 60) -> dict:
    return {
        "title": "Your Topic",
        "segments": [
            {
                "id": "intro",
                "start": 0.0,
                "end": 5.0,
                "text": "Your text here",
                "visual": "text_overlay",
                "animation": "fade_in"
            },
            # ... more segments
        ]
    }
```

### Animation Styles

- `fade_in` / `fade_out` - Smooth fade
- `slide` - Slide in from side
- `scale` - Scale up/down
- `bounce` - Bounce animation

---

## 🎬 Output

The script generates:

1. **Voice Audio** (`Backend/data/tts_outputs/`)
   - WAV format
   - Your voice speaking the script

2. **Final Video** (`Backend/data/rendered_videos/`)
   - MP4 format
   - Combined visuals + voice
   - Automatically opens when done

---

## 🔧 Advanced Usage

### Custom Duration

```bash
python Backend/scripts/generate_thermodynamics_explainer.py \
  --voice-reference voice.wav \
  --duration 90  # 90 seconds
```

### Custom Resolution

```bash
python Backend/scripts/generate_thermodynamics_explainer.py \
  --voice-reference voice.wav \
  --width 1080 \
  --height 1920  # Vertical format
```

### Save to Specific Location

```bash
python Backend/scripts/generate_thermodynamics_explainer.py \
  --voice-reference voice.wav \
  --output /path/to/my_video.mp4
```

---

## 🐛 Troubleshooting

### TTS Generation Fails

**Error:** "TTS API not available"

**Solutions:**
1. Start backend: `cd Backend && uvicorn main:app --port 5555`
2. Or provide `--hf-token` for direct API access

### Voice Quality Issues

**Problem:** Voice doesn't sound like you

**Solutions:**
1. Use longer voice reference (20-30 seconds)
2. Record in better quality (higher sample rate)
3. Ensure reference has clear speech

### Video Rendering Fails

**Error:** "FFmpeg not found"

**Solution:**
```bash
brew install ffmpeg
```

---

## 📖 Related Documentation

- [Motion Canvas Setup](./MOTION_CANVAS_SETUP.md)
- [Video Text Overlay Guide](./VIDEO_TEXT_OVERLAY_GUIDE.md)
- [TTS Service Documentation](./MEDIA_FACTORY_SYSTEM_EXPLAINED.md#1-tts-service-text-to-speech)

---

## 🎯 Example: Complete Workflow

```bash
# 1. Record your voice (10-30 seconds)
# Save as: my_voice.wav

# 2. Generate explainer video
python Backend/scripts/generate_thermodynamics_explainer.py \
  --voice-reference my_voice.wav \
  --duration 60 \
  --hf-token hf_xxxxxxxxxxxxx

# 3. Video opens automatically!
# Output: Backend/data/rendered_videos/thermodynamics_explainer_*.mp4
```

---

*Last Updated: December 28, 2024*

