# Automatic Background Music Matching PRD

## Overview
Intelligent system for automatically matching and associating background music with video content. Provides seamless music suggestions during scheduling, auto-association during analysis, and high-quality music overlay using Remotion.

## Problem Statement
Currently, users must manually select background music for their videos. This creates friction in the scheduling workflow and requires musical knowledge to make good choices. Users want:
- Automatic music suggestions based on video content
- Easy accept/shuffle workflow for music selection
- Professional-quality music overlay in final renders
- Transparent reasoning for why music was selected

## User Stories

### As a content creator:
1. When I open the schedule panel, I want the system to automatically suggest compatible background music
2. I want to preview/play the suggested music before accepting
3. I want to shuffle to see alternative music options
4. I want to understand why specific music was recommended
5. I want the music to be professionally mixed into my video at the right volume

### As a power user:
1. I want music to be auto-associated during video analysis
2. I want to filter my library by "has music" vs "needs music"
3. I want to see music compatibility scores in the media detail page

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MUSIC MATCHING PIPELINE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐   │
│  │   Video     │───▶│   Content    │───▶│  Music Matcher      │   │
│  │   Analysis  │    │   Features   │    │  (Compatibility)    │   │
│  └─────────────┘    └──────────────┘    └─────────────────────┘   │
│        │                   │                      │                │
│        │                   │                      ▼                │
│        │                   │            ┌─────────────────────┐   │
│        │                   │            │  Music Library      │   │
│        │                   │            │  (Ranked Results)   │   │
│        │                   │            └─────────────────────┘   │
│        │                   │                      │                │
│        ▼                   ▼                      ▼                │
│  ┌───────────────────────────────────────────────────────────┐    │
│  │                 VIDEO_ANALYSIS TABLE                       │    │
│  │  - suggested_music_id                                      │    │
│  │  - music_match_score                                       │    │
│  │  - music_match_reasoning                                   │    │
│  │  - music_alternatives (JSONB array of top 5)               │    │
│  └───────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                    SCHEDULE PANEL WORKFLOW                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. User opens Schedule Panel                                       │
│          │                                                          │
│          ▼                                                          │
│  2. Check: Does video have suggested_music_id?                      │
│          │                                                          │
│     ┌────┴────┐                                                     │
│     │ NO      │ YES                                                 │
│     ▼         ▼                                                     │
│  3. Show Loading    3. Load music details                           │
│     "Finding music..."    │                                         │
│          │                │                                         │
│          ▼                ▼                                         │
│  4. Call /api/music/suggest/{media_id}                              │
│          │                                                          │
│          ▼                                                          │
│  5. Display Music Card:                                             │
│     ┌──────────────────────────────────┐                           │
│     │ 🎵 Suggested Music               │                           │
│     │ ┌─────────────────────────────┐  │                           │
│     │ │ "Corporate Tech" - 2:30    │  │                           │
│     │ │ ▶️ Preview  🔀 Shuffle     │  │                           │
│     │ └─────────────────────────────┘  │                           │
│     │ Match: 87% | Mood: Upbeat       │                           │
│     │ "Matches your energetic tone"   │                           │
│     │                                  │                           │
│     │ [ ] Include background music    │                           │
│     └──────────────────────────────────┘                           │
│          │                                                          │
│          ▼                                                          │
│  6. User accepts/shuffles/disables                                  │
│          │                                                          │
│          ▼                                                          │
│  7. On Save/Publish:                                                │
│     - If music enabled: Call Remotion to overlay                    │
│     - Quality gates: Volume levels, ducking                         │
│     - Publish final rendered video                                  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Schema Changes

### video_analysis table additions
```sql
-- Music matching fields
ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS suggested_music_id TEXT;
ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS music_match_score NUMERIC(4,3);
ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS music_match_reasoning TEXT;
ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS music_alternatives JSONB;
ALTER TABLE video_analysis ADD COLUMN IF NOT EXISTS music_matched_at TIMESTAMP WITH TIME ZONE;

-- Structure of music_alternatives JSONB:
-- [
--   {"music_id": "track-123", "score": 0.87, "reasoning": "High energy match"},
--   {"music_id": "track-456", "score": 0.82, "reasoning": "Genre alignment"},
--   ...
-- ]
```

### scheduled_posts table additions
```sql
ALTER TABLE scheduled_posts ADD COLUMN IF NOT EXISTS music_id TEXT;
ALTER TABLE scheduled_posts ADD COLUMN IF NOT EXISTS include_music BOOLEAN DEFAULT false;
ALTER TABLE scheduled_posts ADD COLUMN IF NOT EXISTS music_volume NUMERIC(3,2) DEFAULT 0.3;
```

## API Endpoints

### POST /api/music/suggest/{media_id}
Suggest best matching music for a video. Returns top matches with reasoning.

**Request:**
```json
{
  "refresh": false,    // Force re-calculation even if cached
  "top_n": 5          // Number of alternatives to return
}
```

**Response:**
```json
{
  "success": true,
  "media_id": "uuid",
  "suggested_music": {
    "music_id": "corporate-tech",
    "title": "Corporate Tech",
    "artist": "MediaPoster Library",
    "duration": 180,
    "preview_url": "/api/music/preview/corporate-tech",
    "download_url": "/api/music/file/corporate-tech",
    "match_score": 0.87,
    "reasoning": "High energy corporate content matches professional upbeat music"
  },
  "alternatives": [
    {"music_id": "energetic-pop", "score": 0.82, "title": "Energetic Pop"},
    {"music_id": "hip-hop-flow", "score": 0.75, "title": "Hip Hop Flow"}
  ],
  "analysis_summary": {
    "detected_mood": "energetic",
    "energy_level": 0.8,
    "content_type": "corporate",
    "topics": ["business", "technology"]
  }
}
```

### POST /api/music/shuffle/{media_id}
Get next best alternative music, excluding already seen tracks.

### GET /api/music/preview/{music_id}
Stream audio preview of music track.

### POST /api/render/with-music
Render video with music overlay using Remotion.

**Request:**
```json
{
  "media_id": "uuid",
  "music_id": "corporate-tech",
  "music_volume": 0.3,
  "duck_on_speech": true,
  "fade_in_ms": 1000,
  "fade_out_ms": 2000
}
```

## Implementation Phases

### Phase 1: Music Matching Service Enhancement (Backend)
**Duration:** 1 session
**Deliverables:**
- Enhance `MusicSelector` with scoring explanations
- Create `/api/music/suggest/{media_id}` endpoint
- Create `/api/music/shuffle/{media_id}` endpoint
- Add music preview streaming endpoint
- Database migration for music fields in video_analysis

### Phase 2: Auto-Music During Analysis
**Duration:** 1 session
**Deliverables:**
- Integrate music matching into video analysis pipeline
- Auto-populate `suggested_music_id` after analysis completes
- Store alternatives and reasoning
- Add `has_music_suggestion` filter to media list

### Phase 3: Schedule Panel Music UI
**Duration:** 1 session
**Deliverables:**
- Music suggestion card in schedule modal
- Play/preview button for music
- Shuffle button for alternatives
- "Include music" checkbox
- Volume slider (0.1 - 0.5)
- Loading state while finding music

### Phase 4: Remotion Music Overlay Integration
**Duration:** 1 session
**Deliverables:**
- Enhance Remotion composer for music overlay
- Audio ducking when speech detected
- Fade in/out transitions
- Volume normalization
- Quality gate checks before publish
- Integration with schedule/publish flow

### Phase 5: Testing & Polish
**Duration:** 1 session
**Deliverables:**
- Unit tests for music matching service
- Integration tests for full pipeline
- E2E tests for schedule modal workflow
- Performance optimization
- Edge case handling (no music library, analysis failures)

## Quality Gates for Music Overlay

Before publishing video with music:
1. **Volume Check** - Music not louder than -12dB average
2. **Speech Preservation** - Duck music 6dB when speech detected
3. **Duration Match** - Music loops/fades appropriately for video length
4. **Format Validation** - Output matches platform requirements
5. **Preview Generation** - 5-second preview available before publish

## Music Matching Algorithm

```python
def calculate_compatibility(video_analysis, music_track):
    score = 0.0
    reasons = []
    
    # Mood alignment (40% weight)
    mood_score = mood_compatibility(video_analysis.mood, music_track.moods)
    score += mood_score * 0.4
    if mood_score > 0.7:
        reasons.append(f"Mood alignment: {video_analysis.mood}")
    
    # Energy level match (30% weight)
    energy_diff = abs(video_analysis.energy_level - music_track.energy_level)
    energy_score = 1.0 - energy_diff
    score += energy_score * 0.3
    if energy_score > 0.7:
        reasons.append("Energy level matches video pace")
    
    # Content type alignment (20% weight)
    content_score = content_type_match(video_analysis.content_type, music_track.genre)
    score += content_score * 0.2
    if content_score > 0.5:
        reasons.append(f"Genre fits {video_analysis.content_type} content")
    
    # Duration compatibility (10% weight)
    duration_score = duration_compatibility(video_analysis.duration, music_track.duration)
    score += duration_score * 0.1
    
    return score, ". ".join(reasons)
```

## UI Mockup - Schedule Modal Music Section

```
┌────────────────────────────────────────────────────────────────┐
│ 🎵 Background Music                              [?] Optional  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │ ♪ "Corporate Tech"                                       │ │
│  │   Duration: 2:30 | BPM: 120 | Genre: Corporate          │ │
│  │                                                          │ │
│  │   ▶️ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 0:00 │ │
│  │                                                          │ │
│  │   Match: ████████░░ 87%                                  │ │
│  │   "Matches your energetic corporate tone"                │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                                │
│  [ ✓ ] Include background music                               │
│                                                                │
│  Volume: ━━━━━━━●━━━━━━━ 30%                                  │
│                                                                │
│  [ 🔀 Shuffle ]  [ ❌ No Music ]                              │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Success Metrics
- Music suggestion accuracy > 80% user acceptance rate
- Schedule-to-publish flow time < 30 seconds
- Rendered video quality matches source
- Zero audio clipping or distortion
- Music preview loads in < 1 second

## Dependencies
- Existing `MusicSelector` service
- Existing Remotion service
- Music library with analyzed tracks
- OpenAI for enhanced mood detection (optional)

## Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Empty music library | Ship with default royalty-free tracks |
| Slow matching | Cache results in video_analysis table |
| Poor matches | Allow user to disable/shuffle |
| Render failures | Preview before publish, quality gates |
| Copyright issues | Only use royalty-free music library |

## Out of Scope (Future)
- Music fingerprinting from original video
- Custom music upload
- Tempo-synced video editing
- AI music generation
- Platform-specific music (TikTok sounds)
