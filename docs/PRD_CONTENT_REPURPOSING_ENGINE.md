# PRD: Content Repurposing Engine

**Version:** 1.0  
**Date:** January 19, 2026  
**Status:** Proposed  
**Priority:** High  
**Estimated Effort:** 4-6 weeks

---

## Executive Summary

Transform long-form video content into multiple platform-optimized short clips automatically. Competes with Opus.pro (OpusClip) by offering AI-powered highlight detection, smart reframing, animated captions, and virality scoring.

---

## Problem Statement

| Current State | Gap |
|--------------|-----|
| Basic clip extraction exists | No AI highlight detection |
| Manual editing required | No auto aspect ratio conversion |
| No virality prediction | No data-driven clip selection |
| No automated captions | Manual subtitle work |

### Competitive Gap vs Opus.pro

| Opus Feature | MediaPoster Status |
|--------------|-------------------|
| ClipAnything (any genre) | ⚠️ Partial |
| ReframeAnything (aspect ratios) | ❌ Missing |
| AI B-Roll Generator | ❌ Missing |
| Virality Score (0-100) | ⚠️ Different scoring |
| AI Animated Captions | ❌ Missing |

---

## Goals & Success Metrics

| Metric | Target |
|--------|--------|
| Clips per long video | 10+ average |
| Processing time | < 5 min per 10 min video |
| Virality prediction accuracy | > 70% |
| User time saved | 90% reduction |

---

## Features

### Phase 1: AI Clip Detection (Week 1-2)

#### 1.1 Video Ingestion
- **Sources:** Direct upload, YouTube URL, Podcast RSS, Twitch VOD
- **Formats:** MP4, MOV, WebM
- **Metadata extraction:** Duration, resolution, frame rate

#### 1.2 Whisper Transcription
- Automatic speech-to-text
- Speaker diarization
- 50+ language support
- Filler word detection

#### 1.3 Highlight Detection
- **AI analysis criteria:**
  - Emotional peaks (laughter, intensity)
  - Key statements (insights, quotes)
  - Topic transitions
  - Viral potential indicators
- **Detection methods:**
  - Audio energy analysis
  - Sentiment shifts
  - Speech pace changes

#### 1.4 Clip Generation
- 15-60 second clips (configurable)
- Natural sentence boundaries
- Hook-first ordering
- Auto title suggestions
- Virality score (0-100)

### Phase 2: Smart Reframing (Week 2-3)

#### 2.1 Aspect Ratio Conversion
| Format | Platform |
|--------|----------|
| 9:16 | TikTok, Reels, Shorts |
| 1:1 | Instagram Feed, Twitter |
| 16:9 | YouTube, Twitter |
| 4:5 | Instagram Feed optimal |

#### 2.2 AI Object Tracking
- **Face detection & tracking** - Primary speaker focus
- **Multi-speaker switching** - Group conversations
- **Action tracking** - Follow moving subjects
- **Safe zones** - Keep important content visible

#### 2.3 B-Roll Integration
- AI suggests stock footage based on topic
- Sources: Pexels, Pixabay (free), Shutterstock (premium)
- Overlay styles: Full replace, PiP, split screen

### Phase 3: Captions & Branding (Week 3-4)

#### 3.1 AI Animated Captions
| Style | Description |
|-------|-------------|
| Karaoke | Word-by-word highlight |
| Subtitle | Sentence blocks |
| Emphasis | Key words pop |
| Minimal | Bottom bar |

#### 3.2 Caption Customization
- 20+ font options
- Color schemes
- Size & position
- Background style
- Animation type (fade, bounce, wave)

#### 3.3 Brand Templates
- Pre-built: TikTok trending, Podcast, Educational, Comedy
- Custom: Logo watermark, intro/outro, color matching

### Phase 4: Virality Scoring & Export (Week 4-5)

#### 4.1 Virality Prediction
- **Scoring factors:**
  - Hook strength (first 3 seconds)
  - Emotional intensity
  - Topic trending score
  - Retention prediction
- **Output:** 0-100 score with improvement suggestions

#### 4.2 Platform Optimization
| Platform | Optimization |
|----------|-------------|
| TikTok | Sound-on design, trending sounds |
| Reels | Music integration, hashtags |
| Shorts | Thumbnail, SEO title |
| Twitter | Attention hook, thread potential |

#### 4.3 Export Options
- Download all clips (ZIP)
- Direct publish to MediaPoster queue
- Cloud storage (S3, Google Drive)
- Batch operations

---

## Technical Architecture

### Database Schema

```sql
-- Source videos
CREATE TABLE repurpose_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    title VARCHAR(255) NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    source_url TEXT,
    file_path TEXT,
    duration_seconds INTEGER,
    status VARCHAR(20) DEFAULT 'pending',
    clips_generated INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Transcripts
CREATE TABLE repurpose_transcripts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES repurpose_sources(id) ON DELETE CASCADE,
    full_text TEXT NOT NULL,
    language VARCHAR(10) DEFAULT 'en',
    words JSONB NOT NULL,
    speakers JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Generated clips
CREATE TABLE repurpose_clips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES repurpose_sources(id) ON DELETE CASCADE,
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    title VARCHAR(255),
    transcript_segment TEXT,
    virality_score INTEGER,
    hook_score INTEGER,
    status VARCHAR(20) DEFAULT 'detected',
    is_approved BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Rendered clips
CREATE TABLE repurpose_renders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id UUID REFERENCES repurpose_clips(id) ON DELETE CASCADE,
    aspect_ratio VARCHAR(10) NOT NULL,
    target_platform VARCHAR(20),
    file_path TEXT,
    caption_style VARCHAR(50),
    render_status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### API Endpoints

```
# Source Management
POST   /api/repurpose/sources                  # Upload/import
GET    /api/repurpose/sources                  # List sources
POST   /api/repurpose/sources/{id}/process     # Start processing

# Clips
GET    /api/repurpose/sources/{id}/clips       # List clips
POST   /api/repurpose/clips/{id}/approve       # Approve clip
PUT    /api/repurpose/clips/{id}               # Edit clip

# Rendering
POST   /api/repurpose/clips/{id}/render        # Render clip
POST   /api/repurpose/clips/{id}/render-all    # All formats
GET    /api/repurpose/renders/{id}/download    # Download

# Export
POST   /api/repurpose/sources/{id}/export      # Export all (ZIP)
POST   /api/repurpose/sources/{id}/publish     # Queue for publishing
```

### File Structure

```
Backend/services/repurpose/
├── pipeline.py              # Main orchestrator
├── ingestion/
│   ├── youtube_importer.py
│   └── upload_handler.py
├── transcription/
│   ├── whisper_service.py
│   └── diarization.py
├── detection/
│   ├── highlight_detector.py
│   └── clip_generator.py
├── reframing/
│   ├── reframer.py
│   └── face_tracker.py
├── captions/
│   ├── caption_renderer.py
│   └── animation_engine.py
├── scoring/
│   └── virality_scorer.py
└── rendering/
    └── ffmpeg_renderer.py
```

---

## Implementation Timeline

| Week | Deliverables |
|------|-------------|
| 1 | Video ingestion, Whisper integration |
| 2 | Highlight detection, clip generation |
| 3 | Smart reframing, face tracking |
| 4 | Caption system, brand templates |
| 5 | Virality scoring, export pipeline |
| 6 | Frontend UI, testing, polish |

---

## Dependencies

- **Whisper API:** Transcription
- **FFmpeg:** Video processing
- **OpenCV:** Face detection
- **OpenAI GPT-4:** Highlight analysis
- **Pexels/Pixabay API:** Stock footage

---

## User Interface Preview

### Clip Review Interface
```
┌─────────────────────────────────────────────────────┐
│  Podcast Ep #45 - 12 clips detected                 │
├─────────────────────────────────────────────────────┤
│  Timeline                                           │
│  ├──[==]────[====]────[==]────[======]────────────┤ │
│     89🔥     76       82🔥      71                  │
│                                                     │
│  ┌────────────────────────────────────────────┐    │
│  │ Clip 1: "The key to success is..."  0:45   │    │
│  │ Virality: 89 🔥 | Hook: 92 | Emotion: 85   │    │
│  │ [Preview] [Edit] [Approve] [Reject]        │    │
│  └────────────────────────────────────────────┘    │
│                                                     │
│  [Export All] [Render 9:16] [Render 1:1] [Publish] │
└─────────────────────────────────────────────────────┘
```

---

**Document Owner:** Product Team  
**Last Updated:** January 19, 2026
