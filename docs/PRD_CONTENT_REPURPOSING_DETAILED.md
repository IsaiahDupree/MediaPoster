# PRD: Content Repurposing Engine (Detailed)

**Version:** 1.0  
**Date:** February 1, 2026  
**Status:** Ready for Implementation  
**Track:** T3.1 Content Repurposing  
**Effort:** 4-6 weeks  
**Priority:** 🟡 High

---

## Executive Summary

Build an Opus.pro-style content repurposing engine that transforms long-form videos into viral short-form clips with AI-powered highlight detection, smart reframing, animated captions, and virality prediction.

---

## Competitive Analysis

| Feature | Opus.pro | MediaPoster Current | MediaPoster Target |
|---------|----------|---------------------|-------------------|
| ClipAnything | ✅ | ⚠️ Basic | ✅ Full |
| ReframeAnything | ✅ | ❌ | ✅ |
| AI B-Roll | ✅ | ❌ | ✅ |
| Virality Score (0-100) | ✅ | ❌ | ✅ |
| AI Captions | ✅ | ❌ | ✅ |
| Multi-platform export | ✅ | ❌ | ✅ |
| Hook detection | ✅ | ⚠️ | ✅ |
| Emotional peak detection | ✅ | ❌ | ✅ |

---

## Goals

| Goal | Metric | Target |
|------|--------|--------|
| Clip generation speed | Time per clip | <30 seconds |
| Highlight accuracy | User approval rate | 80%+ |
| Virality prediction | Correlation with actual views | >0.6 |
| Export formats | Supported ratios | 4 (9:16, 1:1, 16:9, 4:5) |
| Caption styles | Available options | 20+ |

---

## User Stories

### US-1: Import Long-Form Video
**As a** creator  
**I want** to import videos from YouTube, Twitch, or local files  
**So that** I can repurpose my existing content

### US-2: Auto-Detect Highlights
**As a** creator  
**I want** AI to find the best moments automatically  
**So that** I don't have to watch the entire video

### US-3: Generate Clips
**As a** creator  
**I want** clips generated with proper framing for each platform  
**So that** my content looks native everywhere

### US-4: Add Captions
**As a** creator  
**I want** animated captions that highlight key words  
**So that** my clips are engaging even on mute

### US-5: Predict Virality
**As a** creator  
**I want** to know which clips will perform best  
**So that** I can prioritize my posting schedule

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    CONTENT REPURPOSING ENGINE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      SOURCE IMPORTER                             │   │
│  ├─────────┬─────────┬─────────┬─────────┬─────────────────────────┤   │
│  │ YouTube │ Twitch  │  RSS    │  Local  │    Direct Upload        │   │
│  │ yt-dlp  │ VOD API │  Feed   │  File   │                         │   │
│  └────┬────┴────┬────┴────┬────┴────┬────┴─────────────────────────┘   │
│       └─────────┴─────────┴─────────┘                                   │
│                         │                                               │
│                         ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    ANALYSIS PIPELINE                             │   │
│  │  ┌─────────┐  ┌──────────┐  ┌───────────┐  ┌─────────────────┐  │   │
│  │  │ Whisper │─▶│ Emotion  │─▶│   Hook    │─▶│   Highlight     │  │   │
│  │  │Transcribe│ │ Detector │  │ Detector  │  │   Ranker        │  │   │
│  │  └─────────┘  └──────────┘  └───────────┘  └─────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                         │                                               │
│                         ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    CLIP GENERATOR                                │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │   │
│  │  │  Face/Object  │  │    Smart      │  │    B-Roll         │   │   │
│  │  │   Tracking    │  │   Reframing   │  │  Integration      │   │   │
│  │  └───────────────┘  └───────────────┘  └───────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                         │                                               │
│                         ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    CAPTION RENDERER                              │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │   │
│  │  │ Karaoke │  │Subtitle │  │Emphasis │  │ Custom  │            │   │
│  │  │  Style  │  │  Style  │  │  Style  │  │ Fonts   │            │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                         │                                               │
│                         ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    VIRALITY PREDICTOR                            │   │
│  │  Score = Hook(30) + Emotion(25) + Pacing(20) + Topic(15) +      │   │
│  │          Visual(10)                                              │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                         │                                               │
│                         ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    EXPORT SERVICE                                │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │   │
│  │  │  9:16   │  │   1:1   │  │  16:9   │  │   4:5   │            │   │
│  │  │ TikTok  │  │  Insta  │  │ YouTube │  │  Feed   │            │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

```sql
-- Migration: 20260201_content_repurposing.sql

-- Source videos (imported long-form content)
CREATE TABLE repurpose_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source info
    source_type VARCHAR(20) NOT NULL, -- youtube, twitch, local, upload
    source_url TEXT,
    source_id VARCHAR(255), -- YouTube video ID, etc.
    
    -- Video metadata
    title VARCHAR(500),
    description TEXT,
    duration_seconds INTEGER,
    thumbnail_url TEXT,
    
    -- Local files
    video_path TEXT,
    audio_path TEXT,
    
    -- Processing status
    status VARCHAR(20) DEFAULT 'pending', -- pending, downloading, analyzing, ready, failed
    error_message TEXT,
    
    -- Analysis results
    transcript_id UUID,
    analysis_complete BOOLEAN DEFAULT FALSE,
    highlight_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transcripts with word-level timestamps
CREATE TABLE repurpose_transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES repurpose_sources(id) ON DELETE CASCADE,
    
    language VARCHAR(10),
    full_text TEXT,
    
    -- Word-level timestamps for captions
    words JSONB, -- [{word, start, end, confidence}]
    
    -- Segment-level for analysis
    segments JSONB, -- [{start, end, text, emotion_score}]
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Detected highlights
CREATE TABLE repurpose_highlights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES repurpose_sources(id) ON DELETE CASCADE,
    
    -- Timing
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    duration FLOAT GENERATED ALWAYS AS (end_time - start_time) STORED,
    
    -- Content
    title VARCHAR(255),
    transcript_excerpt TEXT,
    
    -- Scores (0-100)
    hook_score FLOAT,
    emotion_score FLOAT,
    pacing_score FLOAT,
    topic_score FLOAT,
    virality_score FLOAT, -- composite
    
    -- Detection reason
    detection_reason VARCHAR(100), -- emotional_peak, strong_hook, key_statement, etc.
    
    -- User actions
    is_approved BOOLEAN,
    is_rejected BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Generated clips
CREATE TABLE repurpose_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES repurpose_sources(id) ON DELETE CASCADE,
    highlight_id UUID REFERENCES repurpose_highlights(id),
    
    -- Timing (may differ from highlight)
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    
    -- Configuration
    aspect_ratio VARCHAR(10) NOT NULL, -- 9:16, 1:1, 16:9, 4:5
    target_platform VARCHAR(20), -- tiktok, instagram_reels, youtube_shorts, twitter
    
    -- Reframing
    reframe_mode VARCHAR(20) DEFAULT 'auto', -- auto, face_track, center, custom
    reframe_config JSONB,
    
    -- Captions
    caption_style VARCHAR(50),
    caption_config JSONB, -- {font, color, animation, position}
    
    -- B-Roll
    broll_segments JSONB, -- [{start, end, source_url, type}]
    
    -- Scores
    virality_score FLOAT,
    
    -- Output
    status VARCHAR(20) DEFAULT 'pending', -- pending, rendering, complete, failed
    output_path TEXT,
    file_size_bytes BIGINT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    rendered_at TIMESTAMPTZ
);

-- Render jobs
CREATE TABLE repurpose_renders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id UUID REFERENCES repurpose_clips(id) ON DELETE CASCADE,
    
    -- Job tracking
    status VARCHAR(20) DEFAULT 'queued', -- queued, processing, complete, failed
    progress INTEGER DEFAULT 0, -- 0-100
    
    -- Timing
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    processing_time_ms INTEGER,
    
    -- Output
    output_path TEXT,
    output_url TEXT,
    
    -- Errors
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- B-Roll library
CREATE TABLE broll_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    source VARCHAR(20) NOT NULL, -- pexels, pixabay, user
    source_id VARCHAR(255),
    
    -- Metadata
    title VARCHAR(255),
    description TEXT,
    tags VARCHAR(100)[],
    
    -- File info
    url TEXT NOT NULL,
    thumbnail_url TEXT,
    duration_seconds FLOAT,
    aspect_ratio VARCHAR(10),
    
    -- Usage tracking
    use_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_sources_status ON repurpose_sources(status);
CREATE INDEX idx_highlights_source ON repurpose_highlights(source_id);
CREATE INDEX idx_highlights_virality ON repurpose_highlights(virality_score DESC);
CREATE INDEX idx_clips_source ON repurpose_clips(source_id);
CREATE INDEX idx_clips_status ON repurpose_clips(status);
CREATE INDEX idx_broll_tags ON broll_library USING gin(tags);
```

---

## API Endpoints

### Sources

```yaml
# POST /api/repurpose/sources
# Import a new source
Request:
  source_type: "youtube" | "twitch" | "local" | "upload"
  source_url: string (for youtube/twitch)
  file: File (for upload)
Response:
  source: RepurposeSource
  job_id: string

# GET /api/repurpose/sources
# List all sources
Response:
  sources: RepurposeSource[]

# GET /api/repurpose/sources/{id}
# Get source with highlights
Response:
  source: RepurposeSource
  transcript: Transcript
  highlights: Highlight[]

# DELETE /api/repurpose/sources/{id}
# Delete source and all clips
```

### Highlights

```yaml
# GET /api/repurpose/sources/{id}/highlights
# Get detected highlights
Query:
  min_virality: number (0-100)
  sort: "virality" | "time"
Response:
  highlights: Highlight[]

# POST /api/repurpose/highlights/{id}/approve
# Approve highlight for clipping

# POST /api/repurpose/highlights/{id}/reject
# Reject highlight

# POST /api/repurpose/highlights
# Manually create highlight
Request:
  source_id: uuid
  start_time: number
  end_time: number
  title: string
```

### Clips

```yaml
# POST /api/repurpose/clips
# Generate a clip
Request:
  source_id: uuid
  highlight_id: uuid (optional)
  start_time: number
  end_time: number
  aspect_ratio: "9:16" | "1:1" | "16:9" | "4:5"
  target_platform: string
  caption_style: string
  reframe_mode: string
Response:
  clip: Clip
  render_job_id: string

# GET /api/repurpose/clips
# List clips
Query:
  source_id: uuid
  status: string
Response:
  clips: Clip[]

# GET /api/repurpose/clips/{id}
# Get clip details with render status

# POST /api/repurpose/clips/{id}/render
# Re-render clip with new settings

# GET /api/repurpose/clips/{id}/download
# Download rendered clip
```

### Captions

```yaml
# GET /api/repurpose/caption-styles
# List available styles
Response:
  styles: [
    {id, name, preview_url, config}
  ]

# POST /api/repurpose/clips/{id}/captions
# Update caption settings
Request:
  style: string
  config: {font, color, size, animation, position}
```

### B-Roll

```yaml
# GET /api/repurpose/broll/search
# Search B-Roll library
Query:
  query: string
  source: "pexels" | "pixabay" | "all"
Response:
  results: BRollItem[]

# POST /api/repurpose/clips/{id}/broll
# Add B-Roll to clip
Request:
  segments: [{start, end, broll_id}]
```

---

## Core Services

### 1. Source Importer
```python
# Backend/services/repurposing/source_importer.py

class SourceImporter:
    async def import_youtube(self, url: str) -> RepurposeSource:
        """Download YouTube video using yt-dlp."""
        pass
    
    async def import_twitch_vod(self, url: str) -> RepurposeSource:
        """Download Twitch VOD."""
        pass
    
    async def import_local(self, path: str) -> RepurposeSource:
        """Import local file."""
        pass
    
    async def process_upload(self, file: UploadFile) -> RepurposeSource:
        """Handle direct upload."""
        pass
```

### 2. Highlight Detector
```python
# Backend/services/repurposing/highlight_detector.py

class HighlightDetector:
    """AI-powered highlight detection."""
    
    async def detect_highlights(
        self,
        source: RepurposeSource,
        transcript: Transcript,
        target_count: int = 10
    ) -> List[Highlight]:
        """Find best moments using multiple signals."""
        
        # 1. Detect emotional peaks
        emotional_peaks = await self.detect_emotional_peaks(transcript)
        
        # 2. Find strong hooks
        hooks = await self.detect_hooks(transcript)
        
        # 3. Identify key statements
        key_statements = await self.detect_key_statements(transcript)
        
        # 4. Analyze pacing changes
        pacing_changes = await self.analyze_pacing(transcript)
        
        # 5. Merge and rank
        candidates = self.merge_candidates(
            emotional_peaks, hooks, key_statements, pacing_changes
        )
        
        # 6. Score and select top highlights
        scored = await self.score_highlights(candidates)
        return scored[:target_count]
    
    async def detect_emotional_peaks(
        self,
        transcript: Transcript
    ) -> List[Candidate]:
        """Find moments with high emotional intensity."""
        # Use OpenAI to analyze emotion per segment
        pass
    
    async def detect_hooks(
        self,
        transcript: Transcript
    ) -> List[Candidate]:
        """Find strong opening statements."""
        # Look for: questions, bold claims, curiosity gaps
        pass
```

### 3. Smart Reframer
```python
# Backend/services/repurposing/smart_reframer.py

class SmartReframer:
    """Intelligent video reframing with face/object tracking."""
    
    async def reframe_video(
        self,
        video_path: str,
        target_ratio: str,
        mode: str = "auto"
    ) -> str:
        """Reframe video to target aspect ratio."""
        
        if mode == "face_track":
            # Track faces and keep them centered
            return await self.reframe_with_face_tracking(video_path, target_ratio)
        elif mode == "speaker_track":
            # Track active speaker
            return await self.reframe_with_speaker_tracking(video_path, target_ratio)
        else:
            # Smart crop based on scene analysis
            return await self.reframe_smart_crop(video_path, target_ratio)
    
    async def detect_faces(self, video_path: str) -> List[FaceTrack]:
        """Detect and track faces using OpenCV/MediaPipe."""
        pass
    
    async def detect_speaker(self, video_path: str, audio_path: str) -> List[SpeakerTrack]:
        """Identify active speaker based on lip movement + audio."""
        pass
```

### 4. Caption Renderer
```python
# Backend/services/repurposing/caption_renderer.py

class CaptionRenderer:
    """Render animated captions on video."""
    
    STYLES = {
        "karaoke": KaraokeStyle,
        "subtitle": SubtitleStyle,
        "hormozi": HormoziStyle,
        "emphasis": EmphasisStyle,
        "minimal": MinimalStyle,
    }
    
    async def render_captions(
        self,
        video_path: str,
        words: List[WordTimestamp],
        style: str,
        config: CaptionConfig
    ) -> str:
        """Add captions to video."""
        
        style_class = self.STYLES.get(style, SubtitleStyle)
        renderer = style_class(config)
        
        return await renderer.render(video_path, words)
    
    def get_available_fonts(self) -> List[str]:
        """List available fonts for captions."""
        pass
```

### 5. Virality Predictor
```python
# Backend/services/repurposing/virality_predictor.py

class ViralityPredictor:
    """Predict virality score for clips."""
    
    async def predict_virality(
        self,
        clip: Clip,
        transcript: str
    ) -> ViralityScore:
        """Calculate virality score (0-100)."""
        
        scores = {
            "hook": await self.score_hook(transcript[:500]),      # 0-30
            "emotion": await self.score_emotion(transcript),       # 0-25
            "pacing": await self.score_pacing(clip.duration),      # 0-20
            "topic": await self.score_topic_relevance(transcript), # 0-15
            "visual": await self.score_visual_appeal(clip),        # 0-10
        }
        
        total = sum(scores.values())
        
        return ViralityScore(
            total=total,
            breakdown=scores,
            recommendation=self.get_recommendation(scores)
        )
    
    async def score_hook(self, opening: str) -> float:
        """Score the hook strength (0-30)."""
        # Factors: curiosity gap, bold claim, question, controversy
        pass
    
    async def score_emotion(self, text: str) -> float:
        """Score emotional intensity (0-25)."""
        pass
```

### 6. B-Roll Service
```python
# Backend/services/repurposing/broll_service.py

class BRollService:
    """Search and integrate B-Roll footage."""
    
    async def search_pexels(self, query: str, count: int = 10) -> List[BRollItem]:
        """Search Pexels for stock footage."""
        pass
    
    async def search_pixabay(self, query: str, count: int = 10) -> List[BRollItem]:
        """Search Pixabay for stock footage."""
        pass
    
    async def suggest_broll(
        self,
        transcript: str,
        segments: List[TranscriptSegment]
    ) -> List[BRollSuggestion]:
        """AI-suggest B-Roll for transcript segments."""
        # Use GPT to identify good B-Roll moments
        pass
    
    async def insert_broll(
        self,
        video_path: str,
        broll_segments: List[BRollSegment]
    ) -> str:
        """Insert B-Roll into video using FFmpeg."""
        pass
```

---

## Implementation Phases

### Phase 1: Source Import & Transcription (Week 1)
| Task | Effort |
|------|--------|
| Database schema | 4h |
| YouTube importer (yt-dlp) | 6h |
| Twitch VOD importer | 4h |
| Local file import | 2h |
| Direct upload handler | 4h |
| Whisper integration | 4h |
| Basic UI: Import page | 8h |

### Phase 2: Highlight Detection (Week 2)
| Task | Effort |
|------|--------|
| Emotional peak detector | 8h |
| Hook detector | 6h |
| Key statement extractor | 4h |
| Pacing analyzer | 4h |
| Highlight ranker | 6h |
| UI: Highlight review | 8h |

### Phase 3: Clip Generation (Week 3)
| Task | Effort |
|------|--------|
| Face tracking (OpenCV) | 8h |
| Smart reframing | 8h |
| Aspect ratio conversion | 6h |
| FFmpeg render pipeline | 8h |
| UI: Clip editor | 8h |

### Phase 4: Captions & Polish (Week 4)
| Task | Effort |
|------|--------|
| Karaoke caption style | 6h |
| Subtitle caption style | 4h |
| Hormozi/emphasis style | 6h |
| Font system | 4h |
| Caption preview | 6h |
| UI: Caption customizer | 8h |

### Phase 5: B-Roll & Virality (Weeks 5-6)
| Task | Effort |
|------|--------|
| Pexels API integration | 4h |
| Pixabay API integration | 4h |
| AI B-Roll suggestions | 6h |
| B-Roll insertion | 6h |
| Virality scoring model | 8h |
| Export options (ZIP, direct) | 6h |
| Analytics dashboard | 8h |

---

## Files to Create

```
Backend/services/repurposing/
├── __init__.py
├── source_importer.py
├── highlight_detector.py
├── smart_reframer.py
├── caption_renderer.py
├── virality_predictor.py
├── broll_service.py
├── render_service.py
├── export_service.py
└── models.py

Backend/services/repurposing/caption_styles/
├── base.py
├── karaoke.py
├── subtitle.py
├── hormozi.py
├── emphasis.py
└── minimal.py

Backend/api/endpoints/repurpose.py

Backend/services/workers/repurpose_worker.py

dashboard/app/(dashboard)/repurpose/
├── page.tsx                   # Source list
├── import/page.tsx            # Import new
├── [sourceId]/page.tsx        # Source detail + highlights
├── [sourceId]/clips/page.tsx  # Clips for source
├── clip/[clipId]/page.tsx     # Clip editor
└── components/
    ├── SourceImporter.tsx
    ├── HighlightTimeline.tsx
    ├── ClipEditor.tsx
    ├── ReframePreview.tsx
    ├── CaptionStyler.tsx
    ├── BRollPicker.tsx
    ├── ViralityMeter.tsx
    └── ExportPanel.tsx
```

---

## Environment Variables

```bash
# Video download
YOUTUBE_COOKIES_PATH=  # For age-restricted videos

# B-Roll APIs
PEXELS_API_KEY=
PIXABAY_API_KEY=

# Processing
FFMPEG_PATH=/usr/local/bin/ffmpeg
MAX_CONCURRENT_RENDERS=3
```

---

## Success Criteria

- [ ] Import videos from YouTube, Twitch, local files
- [ ] Auto-detect 10+ highlights per video
- [ ] Generate clips in all 4 aspect ratios
- [ ] 5+ caption styles available
- [ ] Virality score correlates with actual performance
- [ ] <30 second render time per clip
- [ ] B-Roll suggestions for each clip

---

*Document created: February 1, 2026*
