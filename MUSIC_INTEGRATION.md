# 🎵 Music Integration - AI-Powered Background Music

## Overview

MediaPoster now includes **AI-powered background music selection** that automatically chooses the best music track for your clips based on content analysis!

---

## ✨ Features

### 1. AI Music Selection
- **GPT-4 powered** analysis of video content
- Matches music to video topics, mood, and platform
- Returns top 3 recommendations with confidence scores
- Provides reasoning for each selection

### 2. Smart Audio Mixing
- Mix music with original video audio
- Adjustable volume levels (music vs. video)
- Automatic fade in/out for smooth transitions
- Loop music to match video duration
- Option to completely replace audio

### 3. Music Library System
- JSON-based music library
- 8 default genres included
- Easy to add custom tracks
- Tag-based organization

---

## 🎼 Available Genres

| Genre | Moods | Best For |
|-------|-------|----------|
| **Upbeat** | Energetic, happy, fun | Viral content, TikTok, dance |
| **Calm** | Peaceful, relaxing, meditation | Wellness, nature, ASMR |
| **Dramatic** | Epic, intense, powerful | Storytelling, reveals |
| **Hip Hop** | Urban, cool, street | Lifestyle, fashion, culture |
| **Electronic** | EDM, dance, futuristic | Party, gaming, technology |
| **Emotional** | Inspiring, heartfelt | Motivation, success stories |
| **Corporate** | Professional, modern | Business, technology |
| **Acoustic** | Organic, natural, warm | Travel, lifestyle, authentic |

---

## 🚀 How to Use

### Option 1: AI-Powered Selection (Recommended)

```python
from modules.clip_generation import ClipAssembler

assembler = ClipAssembler()

clip_result = assembler.create_clip(
    video_path=video_path,
    highlight=highlight,
    transcript=transcript,
    video_context=video_context,
    add_music=True,  # Enable AI music selection
    music_volume=0.3  # 30% music volume
)
```

**What happens:**
1. AI analyzes video content (transcript, topics, mood)
2. Matches against music library
3. Selects best track (e.g., "Energetic Pop" with 92% confidence)
4. Mixes music at appropriate volume
5. Adds fade in/out for smooth audio

### Option 2: Manual Track Selection

```python
clip_result = assembler.create_clip(
    video_path=video_path,
    highlight=highlight,
    transcript=transcript,
    video_context=video_context,
    add_music=True,
    music_track_id='upbeat_001',  # Specific track
    music_volume=0.25  # 25% music volume
)
```

---

## 📁 Music Library Setup

### 1. Create Music Directory

```bash
mkdir -p backend/data/music
```

### 2. Add Music Files

Place your royalty-free music tracks in:
```
backend/data/music/
├── upbeat_pop.mp3
├── calm_ambient.mp3
├── epic_cinematic.mp3
├── urban_beats.mp3
└── ...
```

### 3. Music Library JSON

Created automatically at `backend/data/music/library.json`:

```json
[
  {
    "id": "upbeat_001",
    "title": "Energetic Pop",
    "file": "data/music/upbeat_pop.mp3",
    "genre": "upbeat",
    "mood": ["energetic", "happy", "fun"],
    "tempo": "fast",
    "duration": 180,
    "tags": ["viral", "tiktok", "instagram", "youth"]
  }
]
```

### 4. Add Custom Tracks

```python
from modules.clip_generation import MusicSelector

selector = MusicSelector()

custom_track = {
    "id": "custom_001",
    "title": "My Custom Track",
    "file": "data/music/my_track.mp3",
    "genre": "electronic",
    "mood": ["energetic", "dance"],
    "tempo": "fast",
    "duration": 175,
    "tags": ["party", "night", "club"]
}

selector.add_track(custom_track)
```

---

## ⚙️ Configuration

### Volume Settings

```python
# Default (recommended)
music_volume=0.3  # 30% music
video_volume=1.0  # 100% original audio

# Quieter music
music_volume=0.2  # 20% music

# Replace audio entirely
from modules.clip_generation import AudioMixer
mixer = AudioMixer()
mixer.replace_audio(video_path, music_path, output_path)
```

### Fade Settings

Controlled in `AudioMixer`:
- **Fade in**: 1.0 seconds (default)
- **Fade out**: 1.0 seconds (default)
- Smooth transitions, no jarring starts/stops

---

## 🎯 AI Selection Process

```
Video Content
    ↓
1. Extract context:
   - Transcript text
   - Topics/keywords
   - Mood/tone
   - Platform (TikTok/Instagram/YouTube)
   - Duration
    ↓
2. GPT-4 Analysis:
   - Match content to music moods
   - Consider platform style
   - Evaluate pacing/energy
   - Check emotional resonance
    ↓
3. Recommendations:
   - Top 3 tracks
   - Confidence scores (0-100%)
   - Reasoning for each
    ↓
4. Auto-Select:
   - Use highest confidence track
   - Mix with video audio
   - Apply fades
    ↓
Final Clip with Perfect Music! 🎵
```

---

## 📊 Example Output

```json
{
  "clip_path": "clip_10s_25s_0.87_tiktok.mp4",
  "duration": 25.0,
  "has_music": true,
  "music_track": {
    "id": "upbeat_001",
    "title": "Energetic Pop",
    "genre": "upbeat",
    "confidence": 0.92,
    "reasoning": "Energetic pop track matches the upbeat life hack content and viral TikTok style"
  },
  "music_volume": 0.3,
  "video_volume": 1.0
}
```

---

## 🎹 Recommended Music Sources

### Royalty-Free Music Platforms:
- **Epidemic Sound** - Popular with creators
- **Artlist** - High quality, simple licensing
- **AudioJungle** - One-time purchase
- **Bensound** - Free with attribution
- **YouTube Audio Library** - Free
- **Purple Planet** - Free royalty-free music
- **Incompetech** - Kevin MacLeod's library

### Music Requirements:
- ✅ Royalty-free or properly licensed
- ✅ MP3 format (recommended)
- ✅ 2-3 minutes duration (for looping)
- ✅ Clear genre/mood classification

---

## 🧪 Testing

```bash
# Test music concepts locally
cd backend
python3 test_music_local.py

# Test with real clips (when you have music files)
python3 test_phase3.py
# Choose option 4 (Create Complete Clip)
# Enable music when prompted
```

---

## 💡 Best Practices

### Content Matching
- **Viral/energetic content** → Upbeat, Electronic
- **Tutorials/education** → Corporate, Calm
- **Storytelling** → Dramatic, Emotional
- **Lifestyle/vlog** → Acoustic, Hip Hop

### Volume Guidelines
- **TikTok/Reels**: 25-35% music (let dialogue stand out)
- **No dialogue**: 50-70% music or replace entirely
- **B-roll**: 40-50% music
- **Intro/outro**: Can go higher (60-80%)

### Platform Considerations
- **TikTok**: Trendy, upbeat music performs better
- **Instagram**: Smooth, aesthetic music
- **YouTube**: Match to content type (educational = calm)

---

## 🔧 Technical Details

### FFmpeg Audio Mixing
```bash
# What happens under the hood:
ffmpeg -i video.mp4 -i music.mp3 \
  -filter_complex "[1:a]atrim=duration=25,
                   afade=t=in:d=1,
                   afade=t=out:st=24:d=1,
                   volume=0.3[music];
                   [0:a]volume=1.0[video_audio];
                   [video_audio][music]amix=inputs=2[audio_out]" \
  -map 0:v -map "[audio_out]" \
  -c:v copy -c:a aac output.mp4
```

### Supported Audio Formats
- MP3 (recommended - best compatibility)
- WAV (uncompressed, large files)
- AAC/M4A (good quality, smaller)
- OGG (open format)

---

## 📈 Integration Stats

**New Files Created**: 2 core modules
- `music_selector.py` (~350 lines)
- `audio_mixer.py` (~200 lines)

**Enhanced Files**: 1
- `clip_assembler.py` (added music step)

**Total Addition**: ~550 lines of production code

**Dependencies**: Uses existing OpenAI + FFmpeg

---

## 🎊 Quick Start Checklist

- [ ] Create `backend/data/music/` directory
- [ ] Add 5-10 royalty-free music tracks
- [ ] Music library auto-generates on first run
- [ ] Test with: `python3 test_music_local.py`
- [ ] Generate clip with music: `add_music=True`
- [ ] Adjust volume to taste (0.2-0.4 recommended)
- [ ] Review AI selections and refine tags
- [ ] Build your perfect music library!

---

## 🚀 Result

**Before**: Clips with original audio only  
**After**: Professional clips with perfectly matched background music!

- ✅ AI selects the perfect track every time
- ✅ Smooth audio mixing (no jarring transitions)
- ✅ Platform-optimized audio levels
- ✅ Automatic looping and fading
- ✅ Viral-ready content with music boost!

---

**Version**: 1.0.0  
**Status**: ✅ Production Ready  
**Cost**: Free (uses existing OpenAI credits for selection)

**Test it now:**
```bash
cd backend
python3 test_music_local.py
```

🎵 **Make your clips sound as good as they look!** 🎵
