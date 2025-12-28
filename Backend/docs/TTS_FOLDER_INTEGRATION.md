# TTS Folder Integration Guide

**Date:** December 28, 2024  
**Status:** ✅ Complete

---

## 🎯 Overview

This guide explains how to use the TTS folder resources (`/Users/isaiahdupree/Documents/Software/TTS`) to generate explainer videos with your voice.

---

## 📁 TTS Folder Structure

```
/Users/isaiahdupree/Documents/Software/TTS/
├── call_indextts2_api.py          # Main TTS API function
├── audio_samples/                 # Voice reference samples (WAV)
├── training_data/                 # Training audio files
├── isolated_audio/                # Isolated voice samples
├── IndexTTS2/                     # Local IndexTTS2 installation
└── [documentation files]
```

---

## 🚀 Quick Start

### Generate Explainer Video

```bash
# Basic usage (auto-finds voice from TTS folder)
python Backend/scripts/generate_explainer_with_tts_folder.py \
  --topic "Thermodynamics" \
  --duration 60

# With specific voice
python Backend/scripts/generate_explainer_with_tts_folder.py \
  --topic "Thermodynamics" \
  --duration 60 \
  --voice "/Users/isaiahdupree/Documents/Software/TTS/audio_samples/Your Voice.wav"

# With Hugging Face token (for better quota)
python Backend/scripts/generate_explainer_with_tts_folder.py \
  --topic "Thermodynamics" \
  --duration 60 \
  --hf-token YOUR_HF_TOKEN
```

---

## 🎤 Voice Reference Selection

The script automatically searches for voice references in this order:

1. **audio_samples/** (preferred)
   - Real voice samples
   - Best quality for cloning

2. **training_data/**
   - Training audio files
   - Good for voice cloning

3. **isolated_audio/**
   - Isolated voice samples
   - Clean audio

4. **refined_audio/**
   - Refined/processed audio
   - High quality

**Selection Criteria:**
- Prefers larger files (better for cloning)
- WAV format preferred over MP3
- Automatically picks best available

---

## 📝 Script Generation

The script automatically generates content based on topic:

### Supported Topics

- **Thermodynamics** - Pre-written content about thermodynamics
- **Any topic** - Generic explainer structure

### Script Structure

```json
{
  "title": "Topic Explained",
  "duration_seconds": 60,
  "segments": [
    {
      "id": "segment_01",
      "start": 0.0,
      "end": 15.0,
      "text": "Introduction text...",
      "visual": "text_overlay",
      "animation": "fade_in"
    },
    // ... more segments
  ]
}
```

---

## 🎬 Video Generation Process

### Step 1: Script Generation
- Creates structured script with segments
- Calculates timing based on duration
- Assigns visuals and animations

### Step 2: Voice Generation
- Uses `call_indextts2_api.py` from TTS folder
- Clones voice from reference audio
- Generates WAV audio file

### Step 3: Video Composition
- Creates video with FFmpeg
- Adds text overlays for each segment
- Syncs audio with visuals
- Exports final MP4

---

## 🔧 TTS API Details

### Using call_indextts2_api.py

```python
from call_indextts2_api import call_indextts2_api

success = call_indextts2_api(
    voice_reference="/path/to/voice.wav",
    text="Your text here",
    output_file="/path/to/output.wav",
    emo_control_method="Same as the voice reference",
    emotion_weight=0.8,
    max_text_tokens=120,
)
```

### Emotion Control

**Methods:**
1. **"Same as the voice reference"** (default)
   - Uses emotion from reference audio
   - Natural, consistent

2. **"Use emotion vectors"**
   - Control specific emotions
   - Example: `emotion_vectors={"happy": 0.8, "calm": 0.2}`

3. **"Use emotion reference audio"**
   - Extract emotion from another audio file
   - Example: `emotion_reference="/path/to/emotion_audio.wav"`

---

## 📊 Available Voice Samples

The TTS folder contains voice samples in:

- **audio_samples/** - Real voice recordings
  - Examples: "AI Appointment Setters Explained.wav"
  - "Posted via MediaPoster.wav"
  - Various topic-based samples

- **training_data/** - Training audio
  - Conversational samples
  - Emotion samples
  - Technical terms
  - Numbers and dates

---

## 🎯 Complete Workflow

```bash
# 1. Generate explainer video
python Backend/scripts/generate_explainer_with_tts_folder.py \
  --topic "Thermodynamics" \
  --duration 60

# Output:
# - Script: Generated automatically
# - Voice: Backend/data/tts_outputs/explainer_*.wav
# - Video: Backend/data/rendered_videos/explainer_thermodynamics_*.mp4
```

---

## 🔍 Finding Voice References

### List Available Voices

```bash
# Audio samples
ls /Users/isaiahdupree/Documents/Software/TTS/audio_samples/*.wav

# Training data
ls /Users/isaiahdupree/Documents/Software/TTS/training_data/*.wav
```

### Use Specific Voice

```bash
python Backend/scripts/generate_explainer_with_tts_folder.py \
  --topic "Thermodynamics" \
  --voice "/Users/isaiahdupree/Documents/Software/TTS/audio_samples/Your Voice.wav"
```

---

## ⚙️ Configuration

### Hugging Face Token

Set token for better quota:

```bash
export HF_TOKEN="your_token_here"
# Or pass via --hf-token flag
```

### Video Resolution

```bash
# Vertical (Shorts/Reels)
python Backend/scripts/generate_explainer_with_tts_folder.py \
  --topic "Thermodynamics" \
  --width 1080 \
  --height 1920

# Horizontal (YouTube)
python Backend/scripts/generate_explainer_with_tts_folder.py \
  --topic "Thermodynamics" \
  --width 1920 \
  --height 1080
```

---

## 🐛 Troubleshooting

### TTS API Not Available

**Error:** "TTS API not available"

**Solution:**
```bash
pip install gradio_client
```

### No Voice Reference Found

**Error:** "No voice reference found in TTS folder"

**Solution:**
1. Place a WAV file in `audio_samples/` or `training_data/`
2. Or specify with `--voice` flag

### GPU Quota Exceeded

**Error:** "You have exceeded your GPU quota"

**Solutions:**
1. Wait 10-30 minutes (quota resets)
2. Set HF_TOKEN (may help with quota)
3. Use local IndexTTS2 (no quota limits)

### FFmpeg Not Found

**Error:** "FFmpeg not found"

**Solution:**
```bash
brew install ffmpeg
```

---

## 📚 Related Documentation

- [TTS Folder README](../../../TTS/README.md)
- [IndexTTS2 API Guide](../../../TTS/INDEXTTS2_API_GUIDE.md)
- [Explainer Video Guide](./EXPLAINER_VIDEO_GUIDE.md)
- [Video Formats Research](./VIDEO_FORMATS_AND_BRIEFS_RESEARCH.md)

---

## ✅ What Works

- ✅ Auto-find voice references from TTS folder
- ✅ Generate scripts for any topic
- ✅ Voice cloning with IndexTTS2
- ✅ Video composition with text overlays
- ✅ Automatic video opening

---

*Last Updated: December 28, 2024*

