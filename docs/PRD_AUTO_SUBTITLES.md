# PRD: Auto-Subtitles / Captions

**Status:** Proposed
**Priority:** P0 — Immediate Impact
**Effort:** ~3-5 days
**Impact:** 40%+ increase in watch time on TikTok/Instagram Reels

---

## 1. Problem Statement

Videos without captions lose viewers — 80% of social media video is watched on mute. TikTok and Instagram Reels with burned-in subtitles consistently outperform captionless content by 40%+ in watch time and engagement. Currently, MediaPoster publishes videos with no subtitle processing.

## 2. Objective

Automatically transcribe every video in the publishing pipeline using OpenAI Whisper, then burn styled captions directly into the video file before it reaches Blotato. Zero manual effort after initial setup.

## 3. Success Metrics

| Metric | Target |
|--------|--------|
| Watch time increase | ≥ 30% across TikTok + Instagram |
| Transcription accuracy | ≥ 95% (English) |
| Processing latency | < 2 min per 60s video |
| Pipeline reliability | 99%+ success rate |

## 4. User Stories

- **As a creator**, I want every video I publish to automatically have captions so I don't have to manually add them.
- **As a creator**, I want caption styles that match trending TikTok/Reels aesthetics (bold, centered, word-by-word highlight).
- **As a creator**, I want the option to skip subtitles for specific videos (e.g., music-only content).

## 5. Technical Design

### 5.1 Architecture

```
Video File
  │
  ▼
┌─────────────────────┐
│  Whisper Transcriber │  ← OpenAI Whisper API or local whisper.cpp
│  (word-level timing) │
└─────────┬───────────┘
          │  SRT/VTT with timestamps
          ▼
┌─────────────────────┐
│  Caption Renderer    │  ← FFmpeg + ASS/SRT subtitle burn-in
│  (style presets)     │
└─────────┬───────────┘
          │  Video with burned-in captions
          ▼
┌─────────────────────┐
│  Existing Publish    │  ← BackgroundPublisher picks up captioned file
│  Pipeline            │
└─────────────────────┘
```

### 5.2 Components

#### A. Transcription Service (`services/subtitle_service.py`)

```python
class SubtitleService:
    async def transcribe(self, video_path: Path) -> TranscriptionResult:
        """Use OpenAI Whisper API for word-level timestamps"""
        
    def generate_srt(self, result: TranscriptionResult) -> str:
        """Convert to SRT with smart line breaks (max 2 lines, ~42 chars)"""
        
    def generate_ass(self, result: TranscriptionResult, style: str) -> str:
        """Convert to ASS with styled formatting"""
```

#### B. Caption Renderer (`services/caption_renderer.py`)

```python
class CaptionRenderer:
    STYLES = {
        "tiktok_bold":    {"font": "Montserrat-Bold", "size": 64, "outline": 4, "shadow": 2, "position": "center"},
        "minimal_white":  {"font": "Inter-Medium", "size": 48, "outline": 2, "shadow": 0, "position": "bottom"},
        "highlight_word": {"font": "Montserrat-Black", "size": 72, "outline": 5, "highlight": True},
        "none":           None,  # Skip captioning
    }
    
    async def burn_captions(self, video_path: Path, srt_path: Path, style: str = "tiktok_bold") -> Path:
        """Use FFmpeg to burn subtitles into video"""
```

#### C. Pipeline Integration

Hook into `BackgroundPublisher.publish()` between media verification and cloud upload:

```python
# In background_publisher.py, after file_path is resolved:
if should_add_captions(request):
    subtitle_service = SubtitleService()
    result = await subtitle_service.transcribe(file_path)
    srt_path = await subtitle_service.save_srt(result, file_path)
    renderer = CaptionRenderer()
    file_path = await renderer.burn_captions(file_path, srt_path, style=request.caption_style or "tiktok_bold")
```

### 5.3 Caption Style Presets

| Style | Description | Best For |
|-------|-------------|----------|
| `tiktok_bold` | White bold text, black outline, centered | TikTok, Reels |
| `minimal_white` | Clean white text, bottom-aligned | YouTube Shorts |
| `highlight_word` | Word-by-word color highlight animation | High-energy content |
| `karaoke` | Progressive fill color per word | Music/audio content |
| `none` | No captions | Music-only, B-roll |

### 5.4 Database Schema

```sql
-- Add to media_analysis or create new table
CREATE TABLE video_transcriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id UUID REFERENCES media(id),
    transcript TEXT,
    srt_content TEXT,
    language VARCHAR(10) DEFAULT 'en',
    word_count INT,
    confidence FLOAT,
    whisper_model VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Add caption_style to scheduled_posts
ALTER TABLE scheduled_posts ADD COLUMN caption_style VARCHAR(50) DEFAULT 'tiktok_bold';
```

### 5.5 Dependencies

- **OpenAI Whisper API** (`openai` package, already in use) — or local `whisper.cpp` for cost savings
- **FFmpeg** — for subtitle burn-in (likely already installed)
- **Fonts** — Montserrat, Inter (free Google Fonts)

## 6. Configuration

```env
# .env additions
WHISPER_MODEL=whisper-1           # OpenAI API model
WHISPER_LOCAL=false                # Set true to use local whisper.cpp
DEFAULT_CAPTION_STYLE=tiktok_bold
CAPTION_FONT_DIR=./assets/fonts
```

## 7. API Endpoints

```
POST /api/subtitles/transcribe    — Transcribe a video
POST /api/subtitles/preview       — Preview caption style on a frame
GET  /api/subtitles/{media_id}    — Get transcription for a media item
```

## 8. Rollout Plan

1. **Phase 1:** Whisper transcription + SRT generation
2. **Phase 2:** FFmpeg burn-in with `tiktok_bold` style
3. **Phase 3:** Multiple style presets + dashboard style picker
4. **Phase 4:** Word-level highlight animation

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Whisper API cost ($0.006/min) | Cache transcriptions; option for local Whisper |
| FFmpeg processing time | Run async; pre-process before scheduled time |
| Incorrect transcription | Allow manual edit via dashboard |
| Video quality loss from re-encoding | Use `-c:v libx264 -crf 18` for near-lossless |

## 10. Out of Scope (v1)

- Multi-language subtitle tracks
- Manual subtitle editing UI
- Translated subtitles
- Custom font upload
