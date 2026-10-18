# SupoClip - Clip Extraction Process Analysis

## Overview

SupoClip is a tool that automatically extracts engaging short-form clips from long-form videos. This document analyzes its process for potential integration into MediaPoster.

**Source:** `../supoclip-reference/`

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Video Input   │────▶│  AssemblyAI     │────▶│   AI Analysis   │
│ (YouTube/Upload)│     │  Transcription  │     │ (Segment Select)│
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Final Clips    │◀────│ Add Subtitles   │◀────│  Smart Crop     │
│  (9:16 format)  │     │ (Word-level)    │     │ (Face Detection)│
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Step-by-Step Process

### 1. Video Input & Download
**File:** `youtube_utils.py`

```python
# Downloads YouTube video using yt-dlp
video_path = download_youtube_video(raw_source["url"])
```

- Supports YouTube URLs and direct uploads
- Downloads to temp directory for processing

---

### 2. Transcript Generation (AssemblyAI)
**File:** `video_utils.py` → `get_video_transcript()`

```python
# Configure AssemblyAI with word-level timestamps
config_obj = aai.TranscriptionConfig(
    speaker_labels=False,
    punctuate=True,
    format_text=True,
    speech_model=aai.SpeechModel.best  # Best quality model
)

transcript = transcriber.transcribe(str(video_path), config=config_obj)
```

**Key Features:**
- Word-level timing for precise subtitles
- Groups words into 8-word segments (~3-4 seconds)
- Formats as `[MM:SS - MM:SS] text` for AI analysis
- Caches transcript data for subtitle generation

**Output Format:**
```
[00:05 - 00:12] Welcome back to the channel today we're going
[00:12 - 00:18] to talk about something really interesting
```

---

### 3. AI Segment Selection
**File:** `ai.py` → `get_most_relevant_parts_by_transcript()`

**Uses:** `pydantic_ai` with structured output

```python
class TranscriptSegment(BaseModel):
    start_time: str      # "MM:SS" format
    end_time: str        # "MM:SS" format
    text: str            # Transcript text
    relevance_score: float  # 0.0 to 1.0
    reasoning: str       # Why this segment is relevant
```

**Selection Criteria:**
1. **Strong Hooks** - Attention-grabbing opening lines
2. **Valuable Content** - Tips, insights, interesting facts
3. **Emotional Moments** - Excitement, surprise, humor
4. **Complete Thoughts** - Self-contained ideas
5. **Entertaining** - Shareable content

**Constraints:**
- Segments: 10-45 seconds optimal
- Minimum: 5 seconds
- Returns: 3-7 segments per video

---

### 4. Smart Cropping (Face Detection)
**File:** `video_utils.py` → `detect_optimal_crop_region()`

**Target Ratio:** 9:16 (vertical/short-form)

**Face Detection Methods (in order of preference):**
1. **MediaPipe** - Most accurate (if available)
2. **OpenCV DNN** - Good accuracy
3. **Haar Cascade** - Fallback

```python
# Sample frames every 0.5 seconds for face detection
sample_interval = min(0.5, duration / 10)

# Use weighted average of face centers
weighted_x = sum(x * area * confidence for x, y, area, confidence in face_centers)
weighted_y = sum(y * area * confidence for x, y, area, confidence in face_centers)

# Bias towards upper portion for better face framing
weighted_y = max(0, weighted_y - new_height * 0.1)
```

**Fallback:** Center crop if no faces detected

---

### 5. Clip Creation
**File:** `video_utils.py` → `create_optimized_clip()`

```python
# Load video and extract segment
video = VideoFileClip(str(video_path))
clip = video.subclipped(start_time, end_time)

# Apply smart crop
cropped_clip = clip.cropped(
    x1=x_offset, y1=y_offset,
    x2=x_offset + new_width, y2=y_offset + new_height
)
```

**Encoding Settings (High Quality):**
```python
{
    "codec": "libx264",
    "audio_codec": "aac",
    "bitrate": "8000k",
    "audio_bitrate": "256k",
    "preset": "medium",
    "ffmpeg_params": ["-crf", "20", "-pix_fmt", "yuv420p"]
}
```

---

### 6. Subtitle Generation
**File:** `video_utils.py` → `create_assemblyai_subtitles()`

**Uses cached word-level timing from AssemblyAI**

```python
# Group 3 words per subtitle for readability
words_per_subtitle = 3

# Create styled text clips
text_clip = TextClip(
    text=text,
    font=processor.font_path,
    font_size=final_font_size,
    color=font_color,
    stroke_color='black',
    stroke_width=1,
    method='label',
    text_align='center'
).with_duration(segment_duration).with_start(segment_start)

# Position at 75% down (lower middle)
vertical_position = int(video_height * 0.75 - text_height // 2)
```

---

## Dependencies

```
# Core
moviepy>=2.0
opencv-python
numpy

# Transcription
assemblyai

# AI Analysis  
pydantic-ai
pydantic

# YouTube
yt-dlp

# Optional (better face detection)
mediapipe
```

---

## Integration Points for MediaPoster

### Option 1: Direct Integration
Copy these functions into MediaPoster's Backend:
- `get_video_transcript()` - Transcription
- `get_most_relevant_parts_by_transcript()` - AI selection
- `detect_optimal_crop_region()` - Smart cropping
- `create_optimized_clip()` - Clip generation
- `create_assemblyai_subtitles()` - Captions

### Option 2: Service Integration
Run SupoClip as a separate service and call via API:
```python
POST /start
{
    "source": {"url": "https://youtube.com/..."},
    "font_options": {
        "font_family": "TikTokSans-Regular",
        "font_size": 24,
        "font_color": "#FFFFFF"
    }
}
```

### Option 3: Selective Feature Adoption
Pick specific features:
1. **AI Segment Selection** - Use the prompt/model for finding engaging clips
2. **Face-Centered Cropping** - Smart 9:16 conversion
3. **Word-Level Subtitles** - AssemblyAI integration for captions

---

## Key Learnings

1. **AssemblyAI's word-level timing** is crucial for precise subtitle sync
2. **3-4 words per subtitle** is optimal for readability
3. **Face detection sampling every 0.5s** balances accuracy vs speed
4. **Weighted face center averaging** handles multiple faces/movement
5. **10-45 second clips** work best for short-form content
6. **Structured AI output** (Pydantic models) ensures consistent results

---

*Generated: December 22, 2025*
*Source: github.com/IsaiahDupree/supoclip*
