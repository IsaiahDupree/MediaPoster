# Transcription Metadata System

> Comprehensive capture and storage of OpenAI Whisper transcription data for video analysis.

## Overview

The transcription metadata system captures all available data from OpenAI Whisper's `verbose_json` response, enabling detailed analysis of speech patterns, pacing, and content quality.

## What's Captured

### Core Transcription Data
| Field | Type | Description |
|-------|------|-------------|
| `transcript` | text | Full transcript text |
| `transcription_language` | text | Detected language code (e.g., "en") |
| `transcription_duration` | float | Audio duration in seconds |

### Word-Level Data
| Field | Type | Description |
|-------|------|-------------|
| `transcription_words` | jsonb | Array of word objects with timestamps |
| `transcription_word_count` | int | Total word count |

Word object structure:
```json
{
  "word": "Hello",
  "start": 0.0,
  "end": 0.5
}
```

### Segment-Level Data
| Field | Type | Description |
|-------|------|-------------|
| `transcription_segments` | jsonb | Array of segment objects |
| `transcription_segment_count` | int | Total segment count |

Segment object structure:
```json
{
  "id": 0,
  "start": 0.0,
  "end": 2.5,
  "text": "Hello, welcome to the video.",
  "avg_logprob": -0.25,
  "no_speech_prob": 0.01
}
```

### Pacing & Quality Metrics
| Field | Type | Description |
|-------|------|-------------|
| `transcription_avg_wpm` | float | Average words per minute |
| `transcription_pause_count` | int | Number of pauses detected |
| `transcription_avg_pause_duration` | float | Average pause length (seconds) |
| `transcription_avg_confidence` | float | Average confidence (0-1) |
| `transcription_silence_ratio` | float | Ratio of silence to speech |
| `transcribed_at` | timestamp | When transcription was performed |

## Database Schema

### Migration
```sql
-- File: supabase/migrations/20241227000004_add_transcription_metadata.sql

ALTER TABLE video_analysis
ADD COLUMN IF NOT EXISTS transcription_language TEXT,
ADD COLUMN IF NOT EXISTS transcription_duration NUMERIC(10, 3),
ADD COLUMN IF NOT EXISTS transcription_words JSONB,
ADD COLUMN IF NOT EXISTS transcription_segments JSONB,
ADD COLUMN IF NOT EXISTS transcription_word_count INTEGER,
ADD COLUMN IF NOT EXISTS transcription_segment_count INTEGER,
ADD COLUMN IF NOT EXISTS transcription_avg_wpm NUMERIC(8, 2),
ADD COLUMN IF NOT EXISTS transcription_pause_count INTEGER,
ADD COLUMN IF NOT EXISTS transcription_avg_pause_duration NUMERIC(8, 3),
ADD COLUMN IF NOT EXISTS transcription_avg_confidence NUMERIC(5, 4),
ADD COLUMN IF NOT EXISTS transcription_silence_ratio NUMERIC(5, 4),
ADD COLUMN IF NOT EXISTS transcribed_at TIMESTAMPTZ;
```

### SQLAlchemy Model
```python
# Backend/database/models.py - VideoAnalysis model

class VideoAnalysis(Base):
    # ... existing fields ...
    
    # Transcription metadata
    transcription_language = Column(String)
    transcription_duration = Column(Numeric(10, 3))
    transcription_words = Column(JSONB)
    transcription_segments = Column(JSONB)
    transcription_word_count = Column(Integer)
    transcription_segment_count = Column(Integer)
    transcription_avg_wpm = Column(Numeric(8, 2))
    transcription_pause_count = Column(Integer)
    transcription_avg_pause_duration = Column(Numeric(8, 3))
    transcription_avg_confidence = Column(Numeric(5, 4))
    transcription_silence_ratio = Column(Numeric(5, 4))
    transcribed_at = Column(DateTime(timezone=True))
```

## Implementation

### Transcription Service
```python
# Backend/services/transcription.py

class TranscriptionService:
    def transcribe_video(self, video_path: str) -> dict:
        """
        Transcribe video using OpenAI Whisper.
        Returns verbose_json with words and segments.
        """
        with open(video_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"]
            )
        return response.model_dump()
    
    def get_transcript_statistics(self, transcript_data: dict) -> dict:
        """Calculate pacing and quality metrics."""
        words = transcript_data.get("words", [])
        segments = transcript_data.get("segments", [])
        duration = transcript_data.get("duration", 0)
        
        # Calculate WPM
        word_count = len(words)
        wpm = (word_count / duration) * 60 if duration > 0 else 0
        
        # Detect pauses (gaps > 0.5s between words)
        pauses = []
        for i in range(1, len(words)):
            gap = words[i]["start"] - words[i-1]["end"]
            if gap > 0.5:
                pauses.append(gap)
        
        # Calculate confidence from segments
        avg_confidence = 0
        if segments:
            probs = [s.get("avg_logprob", 0) for s in segments]
            avg_confidence = sum(probs) / len(probs)
        
        return {
            "word_count": word_count,
            "avg_wpm": round(wpm, 2),
            "pause_count": len(pauses),
            "avg_pause_duration": sum(pauses) / len(pauses) if pauses else 0,
            "avg_confidence": avg_confidence,
        }
```

### Video Analyzer Integration
```python
# Backend/services/video_analyzer.py

async def analyze_video(self, video_path: str, media_id: str) -> dict:
    # ... transcription step ...
    
    transcript_data = await self.transcriber.transcribe_video(video_path)
    stats = self.transcriber.get_transcript_statistics(transcript_data)
    
    # Build metadata
    transcription_metadata = {
        "language": transcript_data.get("language"),
        "duration": transcript_data.get("duration"),
        "words": transcript_data.get("words", []),
        "segments": transcript_data.get("segments", []),
        "word_count": stats["word_count"],
        "segment_count": len(transcript_data.get("segments", [])),
        "avg_wpm": stats["avg_wpm"],
        "pause_count": stats["pause_count"],
        "avg_pause_duration": stats["avg_pause_duration"],
        "avg_confidence": stats["avg_confidence"],
        "silence_ratio": self._calculate_silence_ratio(transcript_data),
    }
    
    # Store in VideoAnalysis
    analysis_values = {
        "transcript": transcript_data.get("text"),
        "transcription_language": transcription_metadata["language"],
        "transcription_duration": transcription_metadata["duration"],
        "transcription_words": transcription_metadata["words"],
        "transcription_segments": transcription_metadata["segments"],
        # ... all other fields
    }
```

## Use Cases

### 1. Pacing Analysis
```python
# Check if video has good pacing for shorts
def is_good_pacing(analysis):
    wpm = analysis.transcription_avg_wpm
    return 120 <= wpm <= 180  # Optimal range for engagement
```

### 2. Hook Detection
```python
# Find the hook (first 3 seconds)
def get_hook_text(analysis):
    words = analysis.transcription_words or []
    hook_words = [w for w in words if w["start"] <= 3.0]
    return " ".join(w["word"] for w in hook_words)
```

### 3. Silence Detection
```python
# Find awkward silences
def find_long_pauses(analysis):
    words = analysis.transcription_words or []
    pauses = []
    for i in range(1, len(words)):
        gap = words[i]["start"] - words[i-1]["end"]
        if gap > 1.5:  # Silence > 1.5s
            pauses.append({
                "start": words[i-1]["end"],
                "end": words[i]["start"],
                "duration": gap
            })
    return pauses
```

### 4. Caption Generation
```python
# Generate SRT from word timestamps
def generate_srt(analysis):
    segments = analysis.transcription_segments or []
    srt_lines = []
    for i, seg in enumerate(segments, 1):
        start = format_timestamp(seg["start"])
        end = format_timestamp(seg["end"])
        srt_lines.append(f"{i}\n{start} --> {end}\n{seg['text']}\n")
    return "\n".join(srt_lines)
```

### 5. Quality Scoring
```python
# Score transcription quality
def score_audio_quality(analysis):
    confidence = analysis.transcription_avg_confidence or 0
    silence_ratio = analysis.transcription_silence_ratio or 0
    
    # Higher confidence = better audio quality
    # Lower silence ratio = more content
    quality_score = (confidence * 0.7) + ((1 - silence_ratio) * 0.3)
    return min(1.0, max(0.0, quality_score))
```

## API Access

The transcription metadata is included in video analysis responses:

```bash
GET /api/analysis/{media_id}
```

Response:
```json
{
  "id": "...",
  "media_id": "...",
  "transcript": "Hello, welcome to today's video...",
  "transcription_language": "en",
  "transcription_duration": 45.5,
  "transcription_word_count": 150,
  "transcription_segment_count": 12,
  "transcription_avg_wpm": 197.8,
  "transcription_pause_count": 3,
  "transcription_avg_pause_duration": 0.75,
  "transcription_avg_confidence": 0.92,
  "transcription_silence_ratio": 0.08,
  "transcription_words": [...],
  "transcription_segments": [...]
}
```

## File Structure

```
Backend/
├── services/
│   ├── transcription.py      # Whisper integration
│   └── video_analyzer.py     # Analysis orchestration
├── database/
│   └── models.py             # VideoAnalysis model

supabase/migrations/
└── 20241227000004_add_transcription_metadata.sql
```

## Related Features

- **Formats System** - Uses transcription for script timing
- **Caption Generation** - Word timestamps for karaoke captions
- **Clip Detection** - Pause patterns for natural cut points
- **Quality Gates** - Caption length validation
