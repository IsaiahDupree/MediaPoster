# PRD: Programmatic SFX & Audio Pipeline System

**Version:** 1.0.0  
**Status:** Draft  
**Author:** Isaiah Dupree  
**Date:** December 28, 2025

---

## Executive Summary

A complete, AI-addressable sound effects and audio pipeline system that works with both **Remotion** and **Motion Canvas**. The system enables programmatic SFX placement, AI-driven audio event generation, and deterministic audio mixing for video production.

### Key Capabilities

1. **SFX Library** - Locally owned, normalized audio files with AI-addressable manifest
2. **Timeline Events** - Engine-agnostic JSON schema for audio placement
3. **Remotion Integration** - Native `<Html5Audio/>` layering via `<Sequence>`
4. **Motion Canvas Integration** - Single mixed audio track via FFmpeg
5. **AI Context System** - Token-efficient manifest for LLM-driven SFX selection
6. **Validation & Auto-fix** - Hallucination-proof ID validation with fallback matching
7. **Beat Extraction** - Script-to-timeline conversion with pacing estimation
8. **QA Gates** - Density warnings, gap detection, build-time safety checks

---

## Problem Statement

### Current Pain Points

1. **Manual SFX Placement** - Editors manually place sound effects, which is time-consuming
2. **Inconsistent Timing** - Audio drift between voiceover, music, and SFX
3. **AI Hallucinations** - LLMs generate non-existent sound effect IDs
4. **Engine Lock-in** - Different audio systems for Remotion vs Motion Canvas
5. **No Pacing Awareness** - SFX spam without cooldown/spacing policies
6. **Attribution Chaos** - Lost track of licensing requirements

### Solution

A unified pipeline where:
- AI generates `sfxId` references from a validated manifest
- A single `audio_events.json` drives both engines
- FFmpeg mixes all audio into one track for Motion Canvas
- Remotion layers SFX natively via `<Sequence>`
- QA gates prevent bad pacing from shipping

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SFX AUDIO PIPELINE                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Script     │───▶│  Beat        │───▶│  AI SFX Selection    │  │
│  │   (text)     │    │  Extractor   │    │  (LLM + Manifest)    │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                    │                │
│                                                    ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  Manifest    │───▶│  Validator   │◀───│  audio_events.json   │  │
│  │  (sfx IDs)   │    │  + Auto-fix  │    │  (AI output)         │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                    │                │
│                      ┌─────────────────────────────┼────────┐      │
│                      │                             │        │      │
│                      ▼                             ▼        ▼      │
│            ┌──────────────────┐          ┌──────────────────────┐  │
│            │    REMOTION      │          │   MOTION CANVAS      │  │
│            │  <SfxLayer/>     │          │   FFmpeg Mix         │  │
│            │  (native layer)  │          │   (audio_mix.wav)    │  │
│            └──────────────────┘          └──────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Schemas

### 1. SFX Manifest (`manifest.json`)

The source of truth for all available sound effects.

```json
{
  "version": "1.0",
  "items": [
    {
      "id": "ui_pop_01",
      "file": "ui/pop_01.wav",
      "tags": ["ui", "pop", "button", "light"],
      "description": "Short UI pop for button taps / bullet reveals",
      "intensity": 2,
      "category": "ui",
      "license": {
        "source": "mixkit",
        "requiresAttribution": false
      }
    },
    {
      "id": "whoosh_fast_02",
      "file": "transitions/whoosh_fast_02.wav",
      "tags": ["whoosh", "swoosh", "transition", "fast"],
      "description": "Fast whoosh for slide/zoom transitions",
      "intensity": 6,
      "category": "transition",
      "license": {
        "source": "zapsplat",
        "requiresAttribution": true,
        "attributionText": "Sound effects obtained from https://www.zapsplat.com"
      }
    }
  ]
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Stable key AI uses (snake_case) |
| `file` | string | ✅ | Relative path inside sfx root |
| `tags` | string[] | ✅ | Searchable keywords |
| `description` | string | ✅ | Human-readable, AI-searchable |
| `intensity` | number | ❌ | 1-10 scale for volume matching |
| `category` | string | ❌ | ui, transition, impact, glitch, etc. |
| `license` | object | ❌ | Attribution requirements |

### 2. Audio Events (`audio_events.json`)

Engine-agnostic timeline representation.

```json
{
  "fps": 30,
  "events": [
    { "type": "voiceover", "src": "assets/vo/episode_01.wav", "frame": 0, "volume": 1.0 },
    { "type": "music", "src": "assets/music/lofi_01.mp3", "frame": 0, "volume": 0.25 },
    { "type": "sfx", "sfxId": "ui_pop_01", "frame": 45, "volume": 0.8 },
    { "type": "sfx", "sfxId": "whoosh_fast_02", "frame": 120, "volume": 1.0 }
  ]
}
```

**Event Types:**

| Type | Fields | Description |
|------|--------|-------------|
| `sfx` | sfxId, frame, volume | Sound effect from manifest |
| `music` | src, frame, volume | Background music track |
| `voiceover` | src, frame, volume | Voice narration |

### 3. Timeline Events (`timeline.events.json`)

Named events for Motion Canvas `waitUntil()` integration.

```json
{
  "version": "1.0.0",
  "fps": 30,
  "events": [
    {
      "name": "hook_automation_intro_1a2b3c",
      "t": 0.0,
      "action": "hook",
      "blockId": "keyword_automation_intro_1a2b3c",
      "text": "I tried to automate SFX..."
    },
    {
      "name": "error_build_failed_9f8e7d",
      "t": 12.84,
      "action": "error",
      "blockId": "error_build_failed_9f8e7d",
      "text": "Build failed: audio drift"
    }
  ]
}
```

### 4. Visual Reveals Seed (`visual_reveals.seed.json`)

Pre-computed reveal timestamps for SFX policy before first render.

```json
{
  "version": "1.0.0",
  "reveals": [
    { "t": 0.0, "kind": "keyword", "key": "One Audio Bus" },
    { "t": 2.5, "kind": "bullet", "key": "Mix voice, music, and SFX into one file" },
    { "t": 5.2, "kind": "code", "key": "pnpm build:audio" }
  ],
  "meta": {
    "method": "paced_cursor",
    "totalSpan": 58.4
  }
}
```

### 5. QA Timeline Report (`qa.timeline_report.json`)

Build-time pacing analysis.

```json
{
  "version": "1.0.0",
  "totalEvents": 24,
  "durationSec": 58.4,
  "minGapSec": 0.35,
  "avgGapSec": 2.43,
  "denseZones": [
    { "start": 12.0, "end": 15.0, "count": 6 }
  ],
  "actionCounts": {
    "hook": 1,
    "reveal": 8,
    "explain": 10,
    "code": 2,
    "cta": 1
  },
  "gapWarnings": [
    { "a": "event_a", "b": "event_b", "gap": 0.28 }
  ]
}
```

---

## Components

### 1. Beat Extractor

Converts script text to timeline beats with frame offsets.

**Input:** Script text  
**Output:** Array of beats with `beatId`, `frame`, `text`, `action`

**Actions:**
- `hook` - Opening hook
- `problem` - Problem statement
- `reveal` - Key insight
- `explain` - Supporting detail
- `code` - Code example
- `error` - Error state
- `success` - Success state
- `cta` - Call to action
- `transition` - Scene transition

**Timing Model:**
- Default: 165 WPM (words per minute)
- Frame calculation: `frames = (wordCount / wpm) * 60 * fps`

### 2. AI Context Pack

Token-efficient manifest subset for LLM prompts.

```typescript
type SfxContextPack = {
  version: string;
  rules: string[];
  sfxIndex: Array<{
    id: string;
    tags: string[];
    desc: string;
    intensity?: number;
    category?: string;
  }>;
};
```

**Rules injected:**
1. ONLY use sfxId values from sfxIndex
2. Return ONLY JSON
3. Prefer exact tag matches
4. Keep volumes between 0.3 and 1.0

### 3. Validator & Auto-fix

Prevents hallucinated sfxIds from breaking the pipeline.

**Validation:**
1. Check if `sfxId` exists in manifest
2. If missing and `allowAutoFix=true`, find closest match by tags/description
3. Log all fixes and rejections

**Matching Algorithm:**
- +3 per overlapping tag
- +2 if category matches
- +1 per description token match
- Tie-break by intensity closeness

### 4. Anti-Spam Filter

Prevents SFX density issues.

**Rules:**
- Minimum 0.35s between SFX (configurable)
- Maximum 2 SFX per second (hard ceiling)
- Allow burst for transitions (optional)
- De-dupe same sfxId within 0.2s

### 5. FFmpeg Audio Mixer

Generates single `audio_mix.wav` for Motion Canvas.

**Process:**
1. Load manifest + events
2. Convert frames to milliseconds
3. Apply per-event volume
4. Apply `adelay` for each SFX start time
5. Mix all streams with `amix`

**Command structure:**
```bash
ffmpeg -y \
  -i voiceover.wav \
  -i music.mp3 \
  -i sfx_1.wav \
  -i sfx_2.wav \
  -filter_complex "[0:a]volume=1[v0];[1:a]volume=0.25[m0];[2:a]volume=0.8,adelay=1500|1500[s0];[3:a]volume=1,adelay=4000|4000[s1];[v0][m0][s0][s1]amix=inputs=4:duration=longest[mixout]" \
  -map "[mixout]" \
  -ac 2 -ar 48000 \
  audio_mix.wav
```

### 6. Remotion SfxLayer

React component for native SFX layering.

```tsx
<SfxLayer events={audioEvents} manifest={manifestMap} basePath="sfx/" />
```

**Renders:**
```tsx
{sfxEvents.map((e, idx) => (
  <Sequence key={`${e.sfxId}-${e.frame}-${idx}`} from={e.frame}>
    <Html5Audio src={staticFile(`sfx/${manifest[e.sfxId].file}`)} volume={e.volume} />
  </Sequence>
))}
```

### 7. QA Gate

Build-time pacing checks.

**Fail conditions:**
- Any gap < 0.20s (ultra-tight)
- Dense zone count >= 8 in 3s window
- More than 12 gap warnings

**Modes:**
- `fail` - Stop pipeline on violation
- `warn` - Log warning, continue

---

## File Structure

```
project/
├── assets/
│   ├── sfx/
│   │   ├── ui/
│   │   │   └── pop_01.wav
│   │   ├── transitions/
│   │   │   └── whoosh_fast_02.wav
│   │   ├── manifest.json
│   │   └── CREDITS.md
│   ├── music/
│   │   └── lofi_01.mp3
│   └── vo/
│       └── episode_01.wav
├── data/
│   ├── script.txt
│   ├── outline.txt
│   ├── audio_base.json          # voiceover + music
│   ├── audio_events.sfx.json    # sfx only (AI generated)
│   ├── audio_events.json        # merged final
│   ├── beats.sec.json
│   ├── hybrid_format.json
│   ├── visual_reveals.seed.json
│   ├── visual_reveals.json      # real capture (after render)
│   ├── timeline.events.json
│   ├── timeline.events.csv
│   ├── qa.timeline_report.json
│   └── marker_overlay_config.json
├── dist/
│   └── audio_mix.wav            # Motion Canvas uses this
├── public/
│   └── sfx/                     # Remotion uses staticFile()
├── src/
│   ├── shared/
│   │   ├── audio-types.ts
│   │   └── audio-validate.ts
│   ├── ai/
│   │   ├── sfx-context-pack.ts
│   │   ├── sfx-prompt.ts
│   │   ├── sfx-autofix.ts
│   │   ├── validate-and-fix-events.ts
│   │   ├── sfx-thin.ts
│   │   ├── sfx-context-filter.ts
│   │   └── sfx-e2e.ts
│   ├── audio/
│   │   ├── merge-events.ts
│   │   ├── clamp-duration.ts
│   │   ├── snap-to-beats.ts
│   │   └── finalize-events.ts
│   ├── remotion/
│   │   └── SfxLayer.tsx
│   └── overlays/
│       └── MarkerOverlay.tsx
├── scripts/
│   ├── build-audio-mix.ts
│   ├── merge-audio.ts
│   ├── run-sfx.ts
│   └── get-remotion-meta.ts
└── tools/
    ├── format/
    │   ├── generate-pack.ts
    │   ├── timing.ts
    │   ├── beat-extractor.ts
    │   ├── normalize-outline.ts
    │   ├── hard-clamp.ts
    │   ├── hard-pad-visual.ts
    │   ├── visual-fillers.ts
    │   └── write-csv.ts
    ├── sfx/
    │   ├── load-visual-reveals.ts
    │   └── write-macro-cues-from-policy.ts
    └── qa/
        ├── timeline-qa.ts
        └── timeline-gate.ts
```

---

## Pipeline Commands

### Package.json Scripts

```json
{
  "scripts": {
    "format:from-script": "ts-node tools/format/generate-from-script.ts",
    "format:prep": "pnpm format:from-script",
    
    "sfx:events": "ts-node scripts/run-sfx.ts",
    "sfx:policy": "ts-node tools/sfx/write-macro-cues-from-policy.ts",
    "sfx:compile": "ts-node scripts/compile-sfx.ts",
    
    "audio:merge": "ts-node scripts/merge-audio.ts --duration 1800 --snap true",
    "audio:bus": "ts-node scripts/build-audio-mix.ts",
    "audio:all": "pnpm sfx:events && pnpm audio:merge && pnpm audio:bus",
    
    "qa:timeline": "ts-node tools/qa/timeline-gate.ts",
    "qa:timeline:warn": "QA_MODE=warn ts-node tools/qa/timeline-gate.ts",
    
    "mc:render:auto": "motion-canvas render",
    "mc:hybrid:final": "pnpm format:prep && pnpm qa:timeline && pnpm mc:render:auto && pnpm sfx:policy && pnpm sfx:compile && pnpm audio:bus && pnpm mc:render:auto",
    
    "render:remotion": "remotion render"
  }
}
```

### Full Pipeline Flow

```
1. script.txt
   ↓
2. pnpm format:prep
   → outline.txt
   → hybrid_format.json
   → beats.sec.json
   → visual_reveals.seed.json
   → timeline.events.json
   → timeline.events.csv
   → qa.timeline_report.json
   ↓
3. pnpm qa:timeline
   → Pass/Fail gate
   ↓
4. pnpm mc:render:auto (first render)
   → visual_reveals.json (real capture)
   ↓
5. pnpm sfx:policy
   → macro_cues.json
   ↓
6. pnpm sfx:compile
   → audio_events.sfx.json
   ↓
7. pnpm audio:bus
   → dist/audio_mix.wav
   ↓
8. pnpm mc:render:auto (final render)
   → output.mp4
```

---

## SFX Sources

### Recommended Free Sources

| Source | License | Attribution | URL |
|--------|---------|-------------|-----|
| **Mixkit** | Free | Not required | mixkit.co |
| **Pixabay** | CC0/Custom | Check per sound | pixabay.com/sound-effects |
| **Freesound** | CC variants | Per-sound basis | freesound.org |
| **ZapSplat** | Standard | Required | zapsplat.com |

### Storage in Manifest

```json
{
  "license": {
    "source": "zapsplat",
    "requiresAttribution": true,
    "attributionText": "Sound effects obtained from https://www.zapsplat.com",
    "url": "https://www.zapsplat.com/license-type/standard-license/"
  }
}
```

---

## Integration Points

### With MediaPoster

1. **Video Render Service** - Use SFX pipeline for generated videos
2. **Narrative Builder** - AI-driven SFX selection based on content pillars
3. **Format Detection** - Match SFX intensity to content format (talking_head vs broll)

### With Remotion

```tsx
// src/remotion/Root.tsx
import sfxManifest from "../../assets/sfx/manifest.json";
import audioEvents from "../../data/audio_events.json";
import { SfxLayer } from "./SfxLayer";

export const MyComp = () => {
  const manifestMap = Object.fromEntries(
    sfxManifest.items.map((it) => [it.id, { file: it.file }])
  );
  
  return (
    <>
      {/* visuals */}
      <SfxLayer events={audioEvents} manifest={manifestMap} />
    </>
  );
};
```

### With Motion Canvas

```typescript
// motion-canvas/project.ts
import { makeProject } from "@motion-canvas/core";

export default makeProject({
  scenes: [/* your scenes */],
  audio: "dist/audio_mix.wav", // Generated by FFmpeg builder
});
```

---

## QA Gate Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QA_MODE` | `fail` | `fail` or `warn` |
| `QA_MIN_HARD_GAP` | `0.20` | Minimum seconds between events |
| `QA_MAX_DENSE_COUNT` | `8` | Max events in 3s window |
| `QA_MAX_GAP_WARNINGS` | `12` | Max gaps under MIN_GAP |

### CI/CD Integration

```yaml
# GitHub Actions
- name: QA Timeline Gate
  run: QA_MODE=fail pnpm qa:timeline
  
# Local dev
- run: QA_MODE=warn pnpm mc:hybrid:final
```

---

## Future Enhancements

### Phase 2
- [ ] Embedding-based SFX search (vector similarity)
- [ ] Auto-volume normalization based on content type
- [ ] Multi-language voiceover support

### Phase 3
- [ ] Real-time SFX preview in editor
- [ ] A/B testing for SFX variations
- [ ] Analytics on SFX engagement impact

### Phase 4
- [ ] Custom SFX generation via AI (text-to-audio)
- [ ] Adaptive SFX based on platform (TikTok vs YouTube)
- [ ] Collaborative SFX library across workspaces

---

## Dependencies

```json
{
  "dependencies": {
    "zod": "^3.24.0"
  },
  "devDependencies": {
    "ts-node": "^10.9.2",
    "@remotion/bundler": "^4.0.0",
    "@remotion/renderer": "^4.0.0",
    "@motion-canvas/core": "^3.0.0"
  }
}
```

**System Requirements:**
- FFmpeg (for audio mixing)
- Node.js 18+
- TypeScript 5+

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| SFX Placement Time | -80% | Manual vs automated |
| Audio Drift | < 50ms | Sync accuracy |
| AI Hallucination Rate | < 2% | Invalid sfxIds caught |
| QA Gate Pass Rate | > 95% | First-pass pacing |
| Build Time | < 30s | Full pipeline execution |

---

## Appendix

### A. Zod Schemas

See `src/shared/audio-validate.ts` for complete Zod validation schemas.

### B. Example Script Input

```
HOOK: I tried to automate SFX in Motion Canvas...
PROBLEM: But the timing kept drifting.
ERROR: Build failed: audio drift 😭
REVEAL: The fix is simple.
EXPLAIN: Mix everything into one audio bus.
CODE: pnpm build:audio
SUCCESS: Timing locked. Ship it.
CTA: Link in bio for the repo.
```

### C. Example Output

**beats.sec.json:**
```json
[
  { "beatId": "b01_hook", "t": 0.0, "action": "hook", "text": "I tried to automate SFX..." },
  { "beatId": "b02_problem", "t": 2.4, "action": "problem", "text": "But the timing kept drifting." }
]
```

**audio_events.json:**
```json
{
  "fps": 30,
  "events": [
    { "type": "voiceover", "src": "assets/vo/episode.wav", "frame": 0, "volume": 1.0 },
    { "type": "sfx", "sfxId": "ui_pop_01", "frame": 72, "volume": 0.8 },
    { "type": "sfx", "sfxId": "error_buzz_01", "frame": 144, "volume": 0.9 }
  ]
}
```
