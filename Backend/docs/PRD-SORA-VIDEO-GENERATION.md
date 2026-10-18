# PRD: Sora Video Generation Pipeline

**Version:** 1.0.0  
**Status:** Draft  
**Author:** Isaiah Dupree  
**Date:** December 28, 2025

---

## Executive Summary

A format-agnostic video generation pipeline that uses **Sora** for AI scene generation and **Remotion/Motion Canvas** for final stitching. The system uses a semantic **Intermediate Representation (IR)** to decouple content planning from visual rendering.

### Key Capabilities

1. **Format-Agnostic IR** - Semantic timeline beats (HOOK, STEP, CTA) independent of visuals
2. **Sora Integration** - Programmatic video generation via OpenAI Videos API
3. **Format Packs** - Swappable visual styles (stick-figure, dev-vlog, documentary)
4. **Trend + Brief Input** - Generate content from trend data and content briefs
5. **Asset Caching** - Hash-based caching to avoid regenerating unchanged shots
6. **Multi-Renderer Support** - Output to Remotion or Motion Canvas

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SORA VIDEO GENERATION PIPELINE                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │ Trend Data   │───▶│  Story IR    │───▶│  Shot Plan               │  │
│  │ + Brief      │    │  Generator   │    │  (Sora-facing)           │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘  │
│                             │                        │                  │
│                             ▼                        ▼                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐  │
│  │ Format Pack  │───▶│  Render Plan │◀───│  Sora Runner             │  │
│  │ Selection    │    │  Generator   │    │  (async job mgmt)        │  │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘  │
│                             │                        │                  │
│                             ▼                        ▼                  │
│                    ┌──────────────────────────────────────────────┐    │
│                    │              ASSET MANIFEST                   │    │
│                    │  clips[], music[], sfx[], captions            │    │
│                    └──────────────────────────────────────────────┘    │
│                                        │                                │
│                    ┌───────────────────┴───────────────────┐           │
│                    ▼                                       ▼           │
│           ┌──────────────┐                        ┌──────────────┐     │
│           │   Remotion   │                        │Motion Canvas │     │
│           │   Renderer   │                        │   Renderer   │     │
│           └──────────────┘                        └──────────────┘     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Data Schemas

### 1. Trend Item (`trend_item_v1`)

```json
{
  "id": "trend_123",
  "platform": "tiktok",
  "topic": "productivity hacks",
  "angleCandidates": [
    "most practical angle",
    "contrarian take"
  ],
  "evidence": [
    { "type": "title", "text": "5 Apps That Changed My Life", "url": "..." },
    { "type": "comment", "text": "This actually works!", "url": "..." },
    { "type": "stat", "text": "2.5M views in 24 hours" }
  ]
}
```

### 2. Content Brief (`content_brief_v1`)

```json
{
  "goal": "educate",
  "audience": "aspiring entrepreneurs",
  "promise": "double your productivity in one week",
  "constraints": {
    "maxSeconds": 58,
    "avoidClaims": ["guaranteed results", "no effort required"]
  },
  "CTA": {
    "text": "Save this and try it today!",
    "url": "https://..."
  },
  "keyPoints": [
    "Time blocking technique",
    "2-minute rule",
    "Weekly review ritual"
  ]
}
```

### 3. Story IR (`story_ir_v1`)

The semantic timeline - format-agnostic representation.

```json
{
  "meta": {
    "fps": 30,
    "aspect": "9:16",
    "language": "en",
    "tone": "witty-direct",
    "maxSeconds": 58
  },
  "variables": {
    "topic": "productivity hacks",
    "angle": "most practical angle",
    "audience": "aspiring entrepreneurs",
    "promise": "double your productivity"
  },
  "beats": [
    {
      "id": "beat_hook",
      "type": "HOOK",
      "duration_s": 2.5,
      "narration": "If you're trying to double your productivity, do this first.",
      "on_screen": { "headline": "Double Your Productivity", "sub": "productivity hacks" },
      "broll": [{ "intent": "abstract", "query": "productivity simple icon animation" }],
      "audio": { "music_energy": "high", "sfx": ["whoosh"] }
    },
    {
      "id": "beat_step_1",
      "type": "STEP",
      "duration_s": 5.0,
      "narration": "Step 1: Time blocking technique.",
      "on_screen": { "label": "Step 1", "bullet": "Time blocking technique" },
      "broll": [{ "intent": "ui-demo", "query": "calendar time blocking" }],
      "audio": { "music_energy": "mid", "sfx": ["click"] }
    }
  ]
}
```

**Beat Types:**

| Type | Purpose | Typical Duration |
|------|---------|------------------|
| `HOOK` | Grab attention | 2-3s |
| `PROMISE` | Set expectation | 2-3s |
| `STEP` | Main content points | 4-6s |
| `PROOF` | Evidence/testimonial | 3-5s |
| `CTA` | Call to action | 2-3s |
| `OUTRO` | Sign-off | 1-2s |

### 4. Format Pack (`format_pack_v1`)

Defines visual structure rules.

```json
{
  "id": "listicle_stickfigure_v1",
  "family": "explainer",
  "rules": {
    "ordering": ["HOOK", "PROMISE", "STEP*", "CTA"],
    "defaults": {
      "HOOK": { "duration_s": 2.5 },
      "STEP": { "duration_s": 4.5 },
      "CTA": { "duration_s": 2.0 }
    },
    "constraints": {
      "max_total_s": 58,
      "max_steps": 8
    }
  },
  "renderStrategy": {
    "soraBeatTypes": ["HOOK", "STEP", "PROOF"],
    "nativeBeatTypes": ["PROMISE", "CTA", "OUTRO"]
  },
  "componentMap": {
    "PROMISE": "ScenePromiseCard",
    "CTA": "SceneCTA",
    "OUTRO": "SceneCTA"
  },
  "voice_strategy": {
    "mode": "EXTERNAL_NARRATOR",
    "narrator": {
      "provider": "huggingface",
      "modelId": "tts-model-id",
      "perspective": "third_person"
    },
    "constraints": {
      "forbidOnScreenTalkingWhenNarrated": true,
      "ambienceOnlyWhenNarrated": true
    }
  }
}
```

### 5. Shot Plan (`shot_plan_v1`)

Sora-facing generation requests.

```json
{
  "meta": {
    "fps": 30,
    "aspect": "9:16",
    "size": "720x1280"
  },
  "style_bible": {
    "global_tokens": [
      "clean flat 2D explainer",
      "high contrast",
      "minimal shading",
      "simple stick figure character"
    ],
    "negative_tokens": ["busy background", "photorealism", "tiny text"]
  },
  "references": {
    "file_ids": ["file_abc123"]
  },
  "shots": [
    {
      "id": "shot_beat_hook",
      "fromBeatId": "beat_hook",
      "seconds": 3,
      "prompt": "Stick figure on left. Big headline pops in: 'Do this first'. Subtle push-in.",
      "model": "sora-2",
      "size": "720x1280",
      "tags": ["HOOK"],
      "cacheKey": "sha256_hash_here"
    }
  ]
}
```

### 6. Asset Manifest (`asset_manifest_v1`)

Generated assets after Sora jobs complete.

```json
{
  "clips": [
    {
      "shotId": "shot_beat_hook",
      "beatId": "beat_hook",
      "src": "r2://clips/abc123.mp4",
      "seconds": 3.0,
      "hasAudio": true
    }
  ],
  "music": [],
  "sfx": [],
  "captions": { "src": "r2://captions/captions.srt" }
}
```

### 7. Render Plan (`render_plan_remotion_v1`)

Final Remotion timeline.

```json
{
  "meta": {
    "fps": 30,
    "size": { "w": 720, "h": 1280 }
  },
  "timeline": [
    {
      "id": "tl_beat_hook",
      "from": 0,
      "durationInFrames": 90,
      "kind": "video",
      "src": "r2://clips/abc123.mp4"
    },
    {
      "id": "tl_beat_promise",
      "from": 90,
      "durationInFrames": 75,
      "kind": "native",
      "componentName": "ScenePromiseCard",
      "props": { "beat": {...}, "variables": {...} }
    }
  ]
}
```

---

## Components

### 1. Story IR Generator

Transforms trend + brief into semantic beats.

```python
def make_story_ir(trend: TrendItemV1, brief: ContentBriefV1) -> StoryIRV1:
    """
    1. Extract topic, angle from trend
    2. Build beat sequence from brief.keyPoints
    3. Generate narration per beat
    4. Assign b-roll intents
    5. Clamp to maxSeconds constraint
    """
```

### 2. Shot Plan Generator

Transforms IR + format pack into Sora requests.

```python
def make_shot_plan(
    ir: StoryIRV1,
    format_pack: FormatPackV1,
    style_bible: StyleBible
) -> ShotPlanV1:
    """
    1. Filter beats by format.renderStrategy.soraBeatTypes
    2. Generate prompts from beat content + style tokens
    3. Compute cache keys (hash of prompt + refs)
    4. Return Sora-ready shot requests
    """
```

### 3. Sora Runner

Manages async video generation jobs.

```python
async def run_sora_shot_plan(
    shot_plan: ShotPlanV1,
    api_key: str,
    out_dir: str,
    concurrency: int = 3
) -> AssetManifestV1:
    """
    1. Check cache for existing clips (by cacheKey)
    2. POST /v1/videos for new shots
    3. Poll until completed
    4. Download content to local/R2
    5. Return asset manifest
    """
```

**Sora API Flow:**
```
POST /v1/videos          → Create job
GET /v1/videos/{id}      → Poll status
GET /v1/videos/{id}/content → Download MP4
POST /v1/videos/{id}/remix  → Modify existing
```

### 4. Format Selector

Auto-selects best format pack from signals.

```python
def select_format(
    trend: TrendItemV1,
    brief: ContentBriefV1,
    available_packs: list[FormatPackV1]
) -> FormatPackV1:
    """
    Score each pack by:
    - Platform fit (+3)
    - Goal fit (+3)
    - Sora preference (+3 if high reliance wanted)
    - Content density (fast pace for many points)
    """
```

### 5. Render Plan Generator

Creates Remotion/Motion Canvas timeline.

```python
def make_render_plan(
    ir: StoryIRV1,
    format_pack: FormatPackV1,
    assets: AssetManifestV1
) -> RenderPlanRemotionV1:
    """
    1. Iterate beats in order
    2. Map Sora clips by beatId
    3. Map native beats to components
    4. Calculate frame positions
    """
```

### 6. Voice Engine

Handles narration (external TTS vs Sora dialogue).

```python
class VoiceEngine:
    async def build(
        ir: StoryIRV1,
        strategy: VoiceStrategy,
        fps: int
    ) -> VoiceBuildResult:
        """
        Returns:
        - audio_plan (stitched narration or NONE)
        - shot_audio_policy (mute Sora, forbid talking visuals)
        - adjusted IR with reconciled durations
        """
```

**Voice Modes:**

| Mode | Description | Use Case |
|------|-------------|----------|
| `EXTERNAL_NARRATOR` | TTS narration, mute Sora audio | Explainers |
| `SORA_DIALOGUE` | Keep Sora audio, characters speak | Skits |
| `HYBRID` | Narrator + some dialogue beats | Mixed |

### 7. Speech Budget Planner

Ensures speech fits clip duration.

```python
def plan_speech_budget(
    beats: list[Beat],
    voice_mode: VoiceMode,
    tts_durations: dict[str, float]
) -> list[BeatSpeechBudget]:
    """
    Per beat:
    - speechSeconds (from TTS or WPM estimate)
    - maxUtilization (0.78 for narrator, 0.62 for dialogue)
    - requiredClipSeconds
    - suggestion (EXTEND_BEAT, SPLIT_BEAT, SWITCH_TO_NARRATOR)
    """
```

---

## File Structure

```
project/
├── services/
│   └── video_generation/
│       ├── __init__.py
│       ├── types.py              # All schema types
│       ├── story_ir.py           # IR generator
│       ├── shot_plan.py          # Shot plan generator
│       ├── sora_runner.py        # Sora API client
│       ├── format_selector.py    # Format pack selection
│       ├── render_plan.py        # Remotion plan generator
│       ├── voice_engine.py       # TTS/narration handling
│       └── speech_budget.py      # Duration calculations
├── api/
│   └── endpoints/
│       └── video_generation.py   # API routes
├── data/
│   └── format_packs/
│       ├── listicle_stickfigure_v1.json
│       ├── devlog_screen_v1.json
│       └── doc_broll_v1.json
└── assets/
    └── sora_cache/               # Cached MP4s by hash
```

---

## API Endpoints

### Generate Video

```
POST /api/video-generation/generate
```

**Request:**
```json
{
  "trend": { ... },
  "brief": { ... },
  "format_pack_id": "listicle_stickfigure_v1",
  "voice_vars": {
    "useThirdPersonTTS": true,
    "tts": { "provider": "huggingface", "modelId": "..." }
  }
}
```

**Response:**
```json
{
  "job_id": "gen_123",
  "status": "processing",
  "story_ir": { ... },
  "shot_plan": { ... }
}
```

### Check Status

```
GET /api/video-generation/status/{job_id}
```

### Get Render Plan

```
GET /api/video-generation/render-plan/{job_id}
```

---

## Pipeline Flow

```
1. Receive trend + brief
   ↓
2. select_format() → format_pack
   ↓
3. make_story_ir(trend, brief) → story_ir
   ↓
4. voice_engine.build(story_ir) → adjust durations + audio_plan
   ↓
5. make_shot_plan(story_ir, format) → shot_plan
   ↓
6. apply_voice_policy(shot_plan) → add mute/no-talking constraints
   ↓
7. run_sora(shot_plan) → asset_manifest
   ↓
8. make_render_plan(story_ir, format, assets) → render_plan
   ↓
9. Remotion renders final MP4
```

---

## Caching Strategy

### Shot Cache Key

```python
cache_key = sha256(json.dumps({
    "model": shot.model,
    "size": shot.size,
    "prompt": shot.prompt,
    "refs": reference_file_ids
}))
```

### Cache Check

```python
cache_path = f"sora_cache/{cache_key}.mp4"
if os.path.exists(cache_path):
    return existing_asset  # Skip Sora API call
```

---

## Voice Strategy Details

### Third-Person TTS Enforcement

```python
def enforce_perspective(text: str, mode: str) -> str:
    """
    SOFT_REWRITE: Convert I/you → he/they
    STRICT: Reject if first/second person detected
    """
    if mode == "STRICT" and has_first_or_second_person(text):
        raise PerspectiveViolationError()
    return rewrite_to_third_person(text)
```

### Speech Budget Rules

| Voice Mode | Max Utilization | Max Dialogue Clip |
|------------|-----------------|-------------------|
| EXTERNAL_NARRATOR | 0.78 | N/A |
| SORA_DIALOGUE | 0.62 | 6s |
| HYBRID | 0.78 (narrated), 0.62 (dialogue) | 6s |

---

## Format Packs

### Listicle Stick Figure

```json
{
  "id": "listicle_stickfigure_v1",
  "renderStrategy": {
    "soraBeatTypes": ["HOOK", "STEP", "PROOF"],
    "nativeBeatTypes": ["PROMISE", "CTA"]
  },
  "voice_strategy": {
    "mode": "EXTERNAL_NARRATOR"
  }
}
```

### Dev Vlog

```json
{
  "id": "devlog_screen_v1",
  "renderStrategy": {
    "soraBeatTypes": ["PROOF"],
    "nativeBeatTypes": ["HOOK", "PROMISE", "STEP", "CTA"]
  },
  "voice_strategy": {
    "mode": "EXTERNAL_NARRATOR"
  }
}
```

### Documentary B-Roll

```json
{
  "id": "doc_broll_v1",
  "renderStrategy": {
    "soraBeatTypes": ["HOOK", "PROOF"],
    "nativeBeatTypes": ["PROMISE", "STEP", "CTA"]
  },
  "voice_strategy": {
    "mode": "HYBRID",
    "soraDialogue": {
      "allowBeatTypes": ["HOOK"],
      "maxSecondsPerBeat": 3
    }
  }
}
```

---

## Remotion Integration

### Render From Plan Component

```tsx
export const RenderFromPlan: React.FC<{ plan: RenderPlanRemotionV1 }> = ({ plan }) => {
  return (
    <AbsoluteFill>
      {plan.timeline.map((t) => (
        <Sequence key={t.id} from={t.from} durationInFrames={t.durationInFrames}>
          {t.kind === "video" ? (
            <Video src={t.src} />
          ) : (
            <DynamicComponent name={t.componentName} props={t.props} />
          )}
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Shot Cache Hit Rate | > 60% |
| Average Generation Time | < 5 min/video |
| Voice-Visual Sync | < 100ms drift |
| Format Pack Reuse | > 10 videos/pack |

---

## Future Enhancements

### Phase 2
- [ ] Remix API for shot refinement
- [ ] A/B testing different format packs
- [ ] Automatic caption generation

### Phase 3
- [ ] Multi-character scenes
- [ ] Dynamic b-roll selection from stock
- [ ] Real-time preview during generation

### Phase 4
- [ ] User-uploaded reference images
- [ ] Custom format pack builder UI
- [ ] Batch video generation
