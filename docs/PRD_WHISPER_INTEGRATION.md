# PRD: Whisper Integration

**Version:** 1.0  
**Date:** February 1, 2026  
**Status:** Ready for Implementation  
**Track:** T1.2 Video Intelligence  
**Effort:** 1 week  
**Priority:** 🔴 Critical (Immediate)

---

## Executive Summary

Integrate OpenAI Whisper API for automatic video/audio transcription throughout MediaPoster. This enables transcript-driven content analysis, highlight detection, caption generation, and repurposing workflows.

---

## Problem Statement

Currently, MediaPoster lacks automatic transcription capabilities:
- Users must manually transcribe or upload transcripts
- Content analysis cannot access spoken content
- Highlight detection relies only on visual cues
- Caption generation requires external tools
- Repurposing workflow is incomplete without transcripts

---

## Goals

| Goal | Metric | Target |
|------|--------|--------|
| Auto-transcribe uploaded videos | Transcription rate | 100% of videos |
| Accuracy | Word error rate | <5% (Whisper standard) |
| Speed | Processing time | <2min for 10min video |
| Integration | Systems connected | 5+ (analyzer, repurposing, captions) |

---

## User Stories

### US-1: Content Creator Uploads Video
**As a** content creator  
**I want** my uploaded videos automatically transcribed  
**So that** I can search, analyze, and repurpose spoken content

**Acceptance Criteria:**
- [ ] Upload video triggers transcription job
- [ ] Transcript stored in database with timestamps
- [ ] Transcript visible in content detail view
- [ ] Searchable across all content

### US-2: Content Analyzer Uses Transcript
**As a** system  
**I want** to analyze transcript content  
**So that** I can detect hooks, CTAs, key statements, and sentiment

**Acceptance Criteria:**
- [ ] Transcript fed to AI content analyzer
- [ ] Hook detection from spoken content
- [ ] Key statement extraction
- [ ] Sentiment analysis per segment

### US-3: Repurposing Engine Uses Transcript
**As a** content creator  
**I want** transcripts available for clip generation  
**So that** I can find the best moments to repurpose

**Acceptance Criteria:**
- [ ] Transcript drives highlight detection
- [ ] Clip boundaries align with speech segments
- [ ] Caption generation from transcript

---

## Technical Architecture

### System Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     WHISPER INTEGRATION                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  Video   │───▶│  FFmpeg  │───▶│ Whisper  │───▶│ Database │  │
│  │  Upload  │    │  Extract │    │   API    │    │  Store   │  │
│  └──────────┘    │  Audio   │    └──────────┘    └──────────┘  │
│                  └──────────┘           │                       │
│                                         ▼                       │
│                              ┌──────────────────┐               │
│                              │   Downstream     │               │
│                              │   Consumers      │               │
│                              ├──────────────────┤               │
│                              │ • Content Analyzer│              │
│                              │ • Highlight Detector│            │
│                              │ • Caption Generator│             │
│                              │ • Repurposing Engine│            │
│                              │ • Search Index    │              │
│                              └──────────────────┘               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Design

#### 1. Transcription Service
```python
# Backend/services/transcription/whisper_service.py

class WhisperService:
    """OpenAI Whisper transcription service."""
    
    def __init__(self):
        self.client = OpenAI()
        self.model = "whisper-1"
    
    async def transcribe_file(
        self,
        audio_path: str,
        language: str = None,
        response_format: str = "verbose_json"
    ) -> TranscriptionResult:
        """Transcribe audio file with timestamps."""
        pass
    
    async def transcribe_video(
        self,
        video_path: str,
        extract_audio: bool = True
    ) -> TranscriptionResult:
        """Extract audio and transcribe video."""
        pass
    
    def segment_transcript(
        self,
        transcript: TranscriptionResult,
        segment_duration: int = 30
    ) -> List[TranscriptSegment]:
        """Split transcript into timed segments."""
        pass
```

#### 2. Audio Extraction
```python
# Backend/services/transcription/audio_extractor.py

class AudioExtractor:
    """FFmpeg-based audio extraction."""
    
    async def extract_audio(
        self,
        video_path: str,
        output_format: str = "mp3",
        sample_rate: int = 16000
    ) -> str:
        """Extract audio track from video file."""
        # FFmpeg command: ffmpeg -i video.mp4 -vn -ar 16000 audio.mp3
        pass
    
    async def split_audio(
        self,
        audio_path: str,
        chunk_duration: int = 600  # 10 minutes
    ) -> List[str]:
        """Split long audio into chunks for API limits."""
        pass
```

#### 3. Transcript Models
```python
# Backend/models/transcript.py

class TranscriptSegment(BaseModel):
    """A segment of transcribed speech."""
    id: str
    start_time: float  # seconds
    end_time: float
    text: str
    confidence: float
    speaker: Optional[str] = None  # For diarization
    
class TranscriptionResult(BaseModel):
    """Complete transcription result."""
    id: str
    content_id: str
    language: str
    duration: float
    segments: List[TranscriptSegment]
    full_text: str
    word_timestamps: Optional[List[WordTimestamp]] = None
    created_at: datetime
```

---

## Database Schema

```sql
-- Migration: 20260201_whisper_transcription.sql

-- Transcription jobs
CREATE TABLE transcription_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID REFERENCES content(id),
    status VARCHAR(20) DEFAULT 'pending', -- pending, processing, completed, failed
    audio_path TEXT,
    model VARCHAR(50) DEFAULT 'whisper-1',
    language VARCHAR(10),
    error_message TEXT,
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Transcripts
CREATE TABLE transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID REFERENCES content(id) UNIQUE,
    job_id UUID REFERENCES transcription_jobs(id),
    language VARCHAR(10),
    duration_seconds FLOAT,
    full_text TEXT,
    word_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transcript segments (with timestamps)
CREATE TABLE transcript_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transcript_id UUID REFERENCES transcripts(id) ON DELETE CASCADE,
    segment_index INTEGER,
    start_time FLOAT,  -- seconds
    end_time FLOAT,
    text TEXT,
    confidence FLOAT,
    speaker VARCHAR(50),  -- for diarization
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Word-level timestamps (optional, for karaoke captions)
CREATE TABLE transcript_words (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    segment_id UUID REFERENCES transcript_segments(id) ON DELETE CASCADE,
    word_index INTEGER,
    word TEXT,
    start_time FLOAT,
    end_time FLOAT,
    confidence FLOAT
);

-- Indexes
CREATE INDEX idx_transcripts_content ON transcripts(content_id);
CREATE INDEX idx_segments_transcript ON transcript_segments(transcript_id);
CREATE INDEX idx_segments_time ON transcript_segments(start_time, end_time);
CREATE INDEX idx_transcripts_fulltext ON transcripts USING gin(to_tsvector('english', full_text));
```

---

## API Endpoints

### Transcription API

```yaml
# POST /api/transcription/transcribe
# Trigger transcription for a video/audio file
Request:
  content_id: uuid (optional - link to existing content)
  file_path: string (required if no content_id)
  language: string (optional - auto-detect if not provided)
  
Response:
  job_id: uuid
  status: "pending"
  estimated_time_seconds: number

# GET /api/transcription/jobs/{job_id}
# Check transcription job status
Response:
  job_id: uuid
  status: "pending" | "processing" | "completed" | "failed"
  progress: number (0-100)
  transcript_id: uuid (if completed)
  error: string (if failed)

# GET /api/transcription/transcript/{content_id}
# Get transcript for content
Response:
  id: uuid
  content_id: uuid
  language: string
  duration_seconds: number
  full_text: string
  word_count: number
  segments: [
    {
      id: uuid
      start_time: number
      end_time: number
      text: string
      confidence: number
    }
  ]

# GET /api/transcription/search
# Search across all transcripts
Request:
  query: string
  content_ids: uuid[] (optional)
  
Response:
  results: [
    {
      content_id: uuid
      segment_id: uuid
      text: string
      start_time: number
      end_time: number
      relevance_score: number
    }
  ]
```

---

## Implementation Tasks

### Phase 1: Core Infrastructure (Days 1-2)

| Task | Description | Effort |
|------|-------------|--------|
| T1.2.1 | Create database migration | 2h |
| T1.2.2 | Create transcript models (Pydantic) | 2h |
| T1.2.3 | Implement AudioExtractor service | 4h |
| T1.2.4 | Implement WhisperService | 4h |
| T1.2.5 | Add transcription API endpoints | 4h |

### Phase 2: Integration (Days 3-4)

| Task | Description | Effort |
|------|-------------|--------|
| T1.2.6 | Auto-trigger on video upload | 3h |
| T1.2.7 | Feed to content analyzer | 4h |
| T1.2.8 | Add transcript to content detail UI | 4h |
| T1.2.9 | Implement search across transcripts | 3h |

### Phase 3: Advanced Features (Day 5)

| Task | Description | Effort |
|------|-------------|--------|
| T1.2.10 | Speaker diarization (basic) | 4h |
| T1.2.11 | Long video chunking (>25MB) | 2h |
| T1.2.12 | Background job queue integration | 2h |

---

## Files to Create

```
Backend/services/transcription/
├── __init__.py
├── whisper_service.py      # OpenAI Whisper API client
├── audio_extractor.py      # FFmpeg audio extraction
├── transcript_service.py   # CRUD operations
└── models.py               # Pydantic models

Backend/api/endpoints/transcription.py  # API routes

Backend/services/workers/transcription_worker.py  # Background jobs

supabase/migrations/20260201_whisper_transcription.sql

dashboard/app/(dashboard)/content/[id]/transcript/
├── page.tsx               # Transcript viewer
└── components/
    ├── TranscriptViewer.tsx
    ├── SegmentList.tsx
    └── SearchTranscripts.tsx
```

---

## Integration Points

### 1. Content Analyzer
```python
# In content_analyzer.py
async def analyze_content(content_id: str):
    # Get transcript if available
    transcript = await transcript_service.get_transcript(content_id)
    
    if transcript:
        # Analyze spoken content
        hooks = await detect_hooks_from_transcript(transcript.full_text)
        ctas = await detect_ctas_from_transcript(transcript.full_text)
        key_statements = await extract_key_statements(transcript.segments)
```

### 2. Repurposing Engine
```python
# In highlight_detector.py
async def detect_highlights(content_id: str):
    transcript = await transcript_service.get_transcript(content_id)
    
    # Find emotional peaks
    emotional_segments = await analyze_emotion_per_segment(transcript.segments)
    
    # Find key moments
    key_moments = await find_key_moments(transcript.full_text)
    
    # Return clip suggestions with timestamps
    return generate_clip_suggestions(emotional_segments, key_moments)
```

### 3. Caption Generator
```python
# In caption_service.py
async def generate_captions(content_id: str, style: str = "karaoke"):
    transcript = await transcript_service.get_transcript(content_id)
    
    if style == "karaoke":
        # Use word-level timestamps
        words = await transcript_service.get_word_timestamps(transcript.id)
        return generate_karaoke_captions(words)
    else:
        # Use segment-level
        return generate_subtitle_captions(transcript.segments)
```

---

## Environment Variables

```bash
# Already configured
OPENAI_API_KEY=sk-...

# New (optional)
WHISPER_MODEL=whisper-1
WHISPER_CHUNK_SIZE_MB=25
FFMPEG_PATH=/usr/local/bin/ffmpeg
```

---

## Cost Estimation

| Usage | Rate | Monthly Estimate |
|-------|------|------------------|
| Whisper API | $0.006/min | ~$18/month (3000 min) |
| Storage (transcripts) | Supabase included | $0 |
| FFmpeg processing | Local CPU | $0 |

---

## Success Criteria

- [ ] 100% of uploaded videos get transcribed
- [ ] Transcription completes within 2 minutes for 10-minute videos
- [ ] Transcripts searchable across all content
- [ ] Content analyzer uses transcript data
- [ ] Word-level timestamps available for caption generation

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| API rate limits | High | Implement queue with backoff |
| Large files (>25MB) | Medium | Chunk audio before upload |
| Non-English content | Medium | Auto-detect language |
| Cost overruns | Low | Monitor usage, set alerts |

---

## Future Enhancements

1. **Speaker Diarization** - Identify multiple speakers
2. **Real-time Transcription** - Live streaming support
3. **Custom Vocabulary** - Brand terms, technical jargon
4. **Translation** - Multi-language support
5. **Whisper Local** - Self-hosted for cost savings

---

*Document created: February 1, 2026*
