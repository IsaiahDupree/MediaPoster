# Video Formats and Briefs Research

**Date:** December 28, 2024  
**Purpose:** Research and documentation of video formats and brief structures for explainer videos

---

## 📊 Video Format Types

### 1. Short Form (15-60 seconds)
- **Aspect Ratio:** 9:16 (vertical)
- **Platforms:** TikTok, Instagram Reels, YouTube Shorts
- **Style:** Fast-paced, hook-driven, UGC-style
- **Use Case:** Quick explanations, viral content

### 2. Long Form (2-15 minutes)
- **Aspect Ratio:** 16:9 (horizontal)
- **Platforms:** YouTube, Facebook
- **Style:** Professional, detailed, tutorial-style
- **Use Case:** Deep dives, comprehensive explanations

### 3. Explainer Format (30-90 seconds)
- **Aspect Ratio:** 9:16 or 16:9 (flexible)
- **Platforms:** All platforms
- **Style:** Educational, clear, visual
- **Use Case:** Educational content, product demos

### 4. Ad Creative (15-45 seconds)
- **Aspect Ratio:** 9:16 (vertical)
- **Platforms:** TikTok Ads, Meta Ads
- **Style:** Polished UGC, conversion-focused
- **Use Case:** Paid advertising

---

## 📝 Creative Brief Structure

### Core Components

```python
CreativeBrief(
    # Content
    title: str
    primary_text: str
    secondary_text: Optional[str]
    
    # Format
    format: VideoFormat  # SHORT_FORM, LONG_FORM, etc.
    duration_seconds: int
    aspect_ratio: AspectRatio  # VERTICAL, HORIZONTAL
    
    # Style
    font_family: str
    primary_color: str
    animation_style: str  # fade, slide, scale, bounce
    
    # Media
    background_video_path: Optional[str]
    background_music_path: Optional[str]
    voice_audio_path: Optional[str]
    
    # Output
    output_width: int
    output_height: int
    fps: int
    quality: VideoQuality  # DRAFT, STANDARD, HIGH, PREMIUM
)
```

### Brief Sections

1. **Product Summary** - What is being explained
2. **Performance Rationale** - Why this content works
3. **Target Audience** - Who is this for
4. **Core Insight** - Key message
5. **Key Message** - Main takeaway
6. **Shot Treatment** - Visual descriptions
7. **Look and Feel** - Style guide
8. **Offer and CTA** - Call to action

---

## 🎬 Explainer Video Format

### AI Explainer Format (from codebase)

```json
{
  "id": "ai_explainer_v1",
  "name": "AI Explainer",
  "description": "Educational explainer videos with AI-generated visuals",
  "composition": {
    "fps": 30,
    "width": 1080,
    "height": 1920,
    "defaultDurationSec": 45
  },
  "defaults": {
    "params": {
      "hookIntensity": 0.8,
      "patternInterruptSec": 5,
      "captionStyle": "clean_subs"
    },
    "providers": {
      "tts": {"provider": "elevenlabs"},
      "music": {"provider": "library"},
      "visuals": {"provider": "pexels"}
    }
  }
}
```

### Script Structure

```json
{
  "title": "Topic Title",
  "duration_seconds": 60,
  "segments": [
    {
      "id": "intro",
      "start": 0.0,
      "end": 5.0,
      "text": "Introduction text",
      "visual": "text_overlay",
      "animation": "fade_in"
    },
    {
      "id": "main",
      "start": 5.0,
      "end": 50.0,
      "text": "Main content",
      "visual": "diagram",
      "animation": "slide"
    },
    {
      "id": "outro",
      "start": 50.0,
      "end": 60.0,
      "text": "Conclusion",
      "visual": "text_overlay",
      "animation": "fade_out"
    }
  ]
}
```

---

## 🎤 Voice Integration

### Hugging Face TTS (IndexTTS2)

**Capabilities:**
- ✅ Voice cloning from reference audio
- ✅ Emotion control
- ✅ Word-level timestamps
- ✅ Multiple languages

**Requirements:**
- Voice reference: 10-30 seconds WAV file
- Hugging Face token (for API access)
- Clear, quiet recording

**Usage:**
```python
# Via TTS Service API
POST /api/tts/generate
{
  "text": "Your script text",
  "model": "indextts2",
  "voice_reference": "/path/to/voice.wav"
}

# Or direct Hugging Face
from transformers import pipeline
tts = pipeline("text-to-speech", model="IndexTTS2")
audio = tts(text, voice_reference=voice_ref)
```

---

## 🎨 Visual Elements

### Text Overlays
- **Styles:** fade, slide, scale, bounce
- **Positions:** top, center, bottom, custom
- **Backgrounds:** Semi-transparent boxes for readability

### Diagrams
- Problem-solution templates
- Flow charts
- Concept maps
- Animated graphics

### B-Roll
- Stock footage
- Screen recordings
- Generated visuals
- Motion graphics

---

## 📐 Resolution Standards

| Format | Width | Height | Aspect Ratio |
|--------|-------|--------|--------------|
| **Vertical (Shorts)** | 1080 | 1920 | 9:16 |
| **Horizontal (YouTube)** | 1920 | 1080 | 16:9 |
| **Square** | 1080 | 1080 | 1:1 |
| **4K Vertical** | 2160 | 3840 | 9:16 |
| **4K Horizontal** | 3840 | 2160 | 16:9 |

---

## 🔄 Workflow

### 1. Brief Generation
- Define topic and format
- Generate script structure
- Determine visual needs

### 2. Script Creation
- Write or AI-generate script
- Break into segments
- Assign visuals and animations

### 3. Voice Generation
- Record or use voice reference
- Generate TTS audio
- Get word timestamps

### 4. Visual Creation
- Generate or source visuals
- Create text overlays
- Prepare animations

### 5. Video Composition
- Combine audio + visuals
- Sync timing
- Add music (optional)

### 6. Export
- Render to target format
- Quality check
- Publish

---

## 📚 References

- [Creative Brief Models](../models/creative_brief_models.py)
- [Video Format Schemas](../services/formats/schema.py)
- [Explainer Video Guide](./EXPLAINER_VIDEO_GUIDE.md)
- [TTS Service Documentation](./MEDIA_FACTORY_SYSTEM_EXPLAINED.md)

---

*Last Updated: December 28, 2024*

