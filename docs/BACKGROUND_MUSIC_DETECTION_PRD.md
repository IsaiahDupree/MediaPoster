# Background Music Detection PRD

## Overview
Add automated detection of background music in video content during the analysis pipeline. This enables smarter content recommendations, copyright risk assessment, and music overlay decisions.

## Problem Statement
Currently, the video analysis pipeline does not detect whether a video already contains background music. This leads to:
- Potential double-layering of music when adding tracks
- Missing copyright risk assessment for existing music
- Inability to filter content by music presence
- Suboptimal music recommendations

## Goals
1. **Detect** if video has existing background music
2. **Classify** the type of audio (speech-only, music-only, mixed, silence)
3. **Extract** music characteristics when present (tempo, genre hints, energy level)
4. **Assess** copyright risk indicators
5. **Store** results for filtering and recommendations

## Schema Changes

### New Fields in `video_analysis` Table
```sql
-- Audio Analysis Fields
audio_analysis JSONB,              -- Full audio analysis result
has_background_music BOOLEAN,      -- Quick boolean for filtering
audio_type TEXT,                   -- 'speech_only', 'music_only', 'mixed', 'silence', 'ambient'
music_confidence NUMERIC(4,3),     -- 0.0-1.0 confidence in music detection
speech_ratio NUMERIC(4,3),         -- Ratio of speech to total audio
music_characteristics JSONB,       -- {tempo_bpm, energy, genre_hints, mood}
copyright_risk TEXT,               -- 'low', 'medium', 'high', 'unknown'
audio_analyzed_at TIMESTAMP        -- When audio analysis was performed
```

### audio_analysis JSONB Structure
```json
{
  "has_music": true,
  "has_speech": true,
  "audio_type": "mixed",
  "confidence": 0.92,
  "segments": [
    {"start": 0.0, "end": 5.2, "type": "speech", "confidence": 0.95},
    {"start": 5.2, "end": 15.0, "type": "music", "confidence": 0.88},
    {"start": 15.0, "end": 20.0, "type": "mixed", "confidence": 0.91}
  ],
  "music_characteristics": {
    "tempo_bpm": 120,
    "energy": "high",
    "genre_hints": ["pop", "electronic"],
    "mood": "upbeat",
    "is_copyrighted_likely": false
  },
  "speech_characteristics": {
    "language": "en",
    "speaker_count": 1,
    "clarity": "clear"
  },
  "overall_loudness_db": -14.2,
  "dynamic_range_db": 12.5
}
```

## Implementation Phases

### Phase 1: Schema & Basic Detection Service
**Duration:** 1 session
**Deliverables:**
- Database migration for new fields
- Basic audio extraction service using ffmpeg
- Simple music detection using audio analysis (librosa or similar)
- API endpoint: `POST /api/analysis/audio/{media_id}`

### Phase 2: Integration with Analysis Pipeline
**Duration:** 1 session
**Deliverables:**
- Integrate audio analysis into existing deep analysis flow
- Update `analyze_video` function to call audio analysis
- Store results in `video_analysis` table
- Add `has_background_music` filter to media list API

### Phase 3: Advanced Detection & UI
**Duration:** 1 session
**Deliverables:**
- Enhanced music characteristic extraction
- Copyright risk assessment
- UI display in media detail page
- Filter by music presence on media list page

## Technical Approach

### Audio Analysis Method
1. **Extract audio** from video using ffmpeg
2. **Analyze audio features** using librosa:
   - Spectral features (frequency distribution)
   - Rhythmic features (beat detection, tempo)
   - Energy/loudness patterns
3. **Classify segments** using feature thresholds or ML model
4. **Use OpenAI Whisper** (already have) for speech detection overlap

### Detection Signals
| Signal | Music Indicator | Speech Indicator |
|--------|-----------------|------------------|
| Consistent beat | Strong | Weak |
| Melodic patterns | Strong | Weak |
| Variable pitch | Medium | Strong |
| Rhythmic consistency | Strong | Weak |
| Frequency spread | Wide = Music | Narrow = Speech |

## API Endpoints

### POST /api/analysis/audio/{media_id}
Trigger audio analysis for a specific video.

**Response:**
```json
{
  "success": true,
  "media_id": "uuid",
  "has_background_music": true,
  "audio_type": "mixed",
  "confidence": 0.92,
  "music_characteristics": {...},
  "copyright_risk": "low"
}
```

### GET /api/media-db/list (Updated)
Add filter parameter: `has_music=true|false|any`

## Success Metrics
- Detection accuracy > 85%
- False positive rate < 10%
- Analysis time < 30s per video
- Zero regression in existing analysis pipeline

## Dependencies
- ffmpeg (already installed)
- librosa (Python audio analysis library)
- OpenAI Whisper (already integrated for transcription)

## Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Slow analysis | Run async, cache results |
| Memory usage for long videos | Process in chunks |
| False positives from ambient sounds | Use confidence thresholds |
| Copyright detection accuracy | Mark as "unknown" when uncertain |

## Out of Scope (Future)
- Actual music identification (Shazam-style)
- Music fingerprinting for copyright matching
- Automatic music removal
- Beat-sync video editing
