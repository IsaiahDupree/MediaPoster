# Groq Transcription Service

This document explains how MediaPoster uses Groq for audio transcription, the processing pipeline, and available functions.

## Overview

MediaPoster uses **Groq's Whisper API** as the primary transcription provider. Groq offers:
- **100% free transcription** (no cost per token)
- **Fast inference** (~10x faster than OpenAI)
- **High accuracy** using Whisper Large V3 model

## Configuration

### Environment Variable
```bash
# Backend/.env
GROQ_API_KEY=gsk_your_api_key_here
```

### Model Registry Configuration
```python
# config/model_registry.py
TaskType.TRANSCRIPTION: ModelConfig(
    provider="groq",
    model="whisper-large-v3",
    api_key_env="GROQ_API_KEY",
    cost_input=0.0,
    cost_output=0.0
)
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Transcription Pipeline                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Video File                                                      │
│      │                                                           │
│      ▼                                                           │
│  ┌─────────────────────┐                                        │
│  │  WhisperTranscriber │  services/whisper_transcriber.py       │
│  │  - Extract audio    │                                        │
│  │  - FFmpeg → MP3     │                                        │
│  └──────────┬──────────┘                                        │
│             │                                                    │
│             ▼                                                    │
│  ┌─────────────────────┐                                        │
│  │     AIClient        │  services/ai_client.py                 │
│  │  - Groq SDK         │                                        │
│  │  - API calls        │                                        │
│  └──────────┬──────────┘                                        │
│             │                                                    │
│             ▼                                                    │
│  ┌─────────────────────┐                                        │
│  │ TranscriptionAdapter│  services/transcription_adapter.py     │
│  │  - Normalize output │                                        │
│  │  - Unified format   │                                        │
│  └──────────┬──────────┘                                        │
│             │                                                    │
│             ▼                                                    │
│  ┌─────────────────────┐                                        │
│  │   video_analysis    │  Database table                        │
│  │   - transcript      │                                        │
│  │   - segments        │                                        │
│  └─────────────────────┘                                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Key Files & Functions

### 1. `services/whisper_transcriber.py` - Main Transcription Service

```python
from services.whisper_transcriber import WhisperTranscriber

transcriber = WhisperTranscriber()

# Full pipeline: extract audio + transcribe
result = transcriber.transcribe_video("/path/to/video.mp4")

# Result structure:
{
    "text": "Full transcript text...",
    "language": "en",
    "duration": 45.3,
    "segments": [
        {"start": 0.0, "end": 2.5, "text": "Hello everyone"},
        {"start": 2.5, "end": 5.0, "text": "Welcome to my video"}
    ]
}
```

**Key Methods:**
| Method | Description |
|--------|-------------|
| `transcribe_video(path)` | Complete pipeline: extract audio → transcribe |
| `extract_audio(path)` | Extract audio from video using FFmpeg |
| `transcribe(audio_path)` | Transcribe audio file via Groq API |
| `has_audio_stream(path)` | Check if file has audio (FFprobe) |

### 2. `services/ai_client.py` - Unified AI Interface

```python
from config.model_registry import TaskType, ModelRegistry
from services.ai_client import AIClient

# Get transcription config
config = ModelRegistry.get_model_config(TaskType.TRANSCRIPTION)
client = AIClient(config)

# Direct transcription
result = client.transcribe("/path/to/audio.mp3", language="en")
```

**Transcribe Method:**
```python
def transcribe(self, audio_path: str, language: str = "en") -> Dict[str, Any]:
    """
    Unified transcription interface
    
    Args:
        audio_path: Path to audio file
        language: Language code (default: "en")
    
    Returns:
        Dict with transcript and metadata
    """
```

### 3. `services/transcription_adapter.py` - Output Normalization

Adapts different provider outputs to a unified format:

```python
from services.transcription_adapter import TranscriptionAdapter, TranscriptionResult

adapter = TranscriptionAdapter()
result: TranscriptionResult = adapter.adapt(response, provider="groq")

# Unified result has:
result.text        # Full transcript
result.language    # Detected language
result.duration    # Audio duration
result.segments    # Time-stamped segments
result.words       # Word-level timestamps
result.provider    # "groq"
result.model       # "whisper-large-v3"
```

### 4. `config/model_registry.py` - Model Configuration

```python
from config.model_registry import TaskType, ModelRegistry

# Get config for any AI task
config = ModelRegistry.get_model_config(TaskType.TRANSCRIPTION)

print(config.provider)      # "groq"
print(config.model)         # "whisper-large-v3"
print(config.api_key_env)   # "GROQ_API_KEY"
print(config.cost_input)    # 0.0 (free!)
```

## Supported Providers

The system supports multiple transcription providers with automatic fallback:

| Provider | Model | Cost | Speed | Quality |
|----------|-------|------|-------|---------|
| **Groq** (default) | whisper-large-v3 | Free | ⚡ Fastest | ⭐⭐⭐⭐⭐ |
| OpenAI | whisper-1 | $0.006/min | Medium | ⭐⭐⭐⭐⭐ |
| Deepgram | nova-2 | $0.0043/min | Fast | ⭐⭐⭐⭐ |
| AssemblyAI | universal-1 | $0.0065/min | Medium | ⭐⭐⭐⭐⭐ |

## Audio Extraction

Videos are preprocessed before transcription:

```bash
# FFmpeg command used for audio extraction
ffmpeg -i video.mp4 \
    -vn \                    # No video
    -acodec libmp3lame \     # MP3 codec
    -ar 16000 \              # 16kHz sample rate (optimal for Whisper)
    -ac 1 \                  # Mono channel
    -b:a 64k \               # 64kbps bitrate
    -y \                     # Overwrite
    output_audio.mp3
```

## Transcript Storage

Transcripts are stored in the `video_analysis` table:

```sql
-- Check transcript for a video
SELECT 
    v.file_name,
    va.transcript,
    va.language,
    LENGTH(va.transcript) as transcript_length
FROM videos v
JOIN video_analysis va ON va.video_id = v.id
WHERE va.transcript IS NOT NULL
LIMIT 5;
```

## Usage Examples

### Basic Transcription
```python
from services.whisper_transcriber import WhisperTranscriber

transcriber = WhisperTranscriber()
result = transcriber.transcribe_video("/path/to/video.mp4")
print(result["text"])
```

### With Analysis Pipeline
```python
from services.video_analyzer import VideoAnalyzer

analyzer = VideoAnalyzer()
analysis = await analyzer.analyze_video(video_id)

# Transcript is part of full analysis
print(analysis["transcript"])
print(analysis["topics"])
print(analysis["hooks"])
```

### Check Audio Before Processing
```python
transcriber = WhisperTranscriber()

if transcriber.has_audio_stream("/path/to/video.mp4"):
    result = transcriber.transcribe_video("/path/to/video.mp4")
else:
    print("No audio stream found")
```

## Error Handling

Common errors and solutions:

| Error | Cause | Solution |
|-------|-------|----------|
| `GROQ_API_KEY not found` | Missing env var | Add to `.env` file |
| `No audio stream found` | Video has no audio | Check file with FFprobe |
| `Rate limit exceeded` | Too many requests | AIClient auto-retries with fallback |
| `FFmpeg failed` | Audio extraction error | Check FFmpeg installation |

## Rate Limits

Groq free tier limits:
- **Audio**: 20 requests/minute
- **File size**: 25MB max per audio file
- **Duration**: ~10 hours/day estimated

The `AIClient` handles rate limits with automatic fallback to OpenAI if needed.

## Cost Comparison

For 1 hour of audio:

| Provider | Cost |
|----------|------|
| **Groq** | **$0.00** |
| OpenAI | $0.36 |
| Deepgram | $0.26 |
| AssemblyAI | $0.39 |

**MediaPoster saves 100% on transcription costs by using Groq.**

## API Endpoints

### `/api/analysis/transcribe` (POST)
```json
// Request
{
    "video_id": "uuid-here"
}

// Response
{
    "success": true,
    "transcript": "Full transcript text...",
    "duration": 45.3,
    "language": "en"
}
```

### `/api/videos/{id}/analysis` (GET)
Returns full analysis including transcript.

## Related Documentation

- [Model Registry](./MODEL_REGISTRY.md) - AI model configuration
- [Video Analysis Pipeline](./VIDEO_ANALYSIS.md) - Full analysis flow
- [AI Services](./AI_SERVICES.md) - All AI integrations
