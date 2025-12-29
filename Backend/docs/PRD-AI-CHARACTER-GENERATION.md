# PRD: AI Character Generation Pipeline

**Version:** 1.0.0  
**Status:** Draft  
**Author:** Isaiah Dupree  
**Date:** December 28, 2025

---

## Executive Summary

A complete pipeline for programmatically generating AI character assets, processing them for transparent backgrounds, auto-cropping, and integrating them into video productions via **Remotion** or **Motion Canvas**. Includes lip-sync support via word timestamps.

### Key Capabilities

1. **AI Character Generation** - Generate characters via image models (OpenAI, etc.)
2. **Background Removal** - Local (rembg/U2Net) or API (remove.bg)
3. **Auto-Cropping** - Trim transparent borders with padding
4. **Asset Manifest** - JSON index for Remotion consumption
5. **SVG-First Stick Figures** - Consistent, recolorable, clean alpha
6. **Batch Factory** - Generate multiple characters × themes × poses × accessories
7. **Mouth Layers** - Separate body/mouth for lip-sync animation
8. **Word Timestamp Lip-Sync** - Drive mouth shapes from ASR timestamps

---

## Problem Statement

### Current Pain Points

1. **Inconsistent Character Identity** - AI generates different-looking characters across poses
2. **Manual Asset Preparation** - Background removal, cropping done by hand
3. **No Manifest System** - Assets scattered without metadata
4. **Static Characters** - No lip-sync or pose animation
5. **Engine Lock-in** - Assets not portable between Remotion/Motion Canvas

### Solution

A unified pipeline where:
- Characters are generated programmatically with consistent prompts
- Background removal and cropping are automated
- A manifest tracks all variants with metadata
- Mouth layers enable real lip-sync from word timestamps
- Same assets work in Remotion and Motion Canvas

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                   AI CHARACTER GENERATION PIPELINE                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Prompt     │───▶│  AI Image    │───▶│  Background          │  │
│  │   Template   │    │  Generator   │    │  Removal (rembg)     │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│                                                    │                │
│                                                    ▼                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │  Manifest    │◀───│  Auto-Crop   │◀───│  Transparent PNG     │  │
│  │  (JSON)      │    │  (sharp)     │    │  with alpha          │  │
│  └──────────────┘    └──────────────┘    └──────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      REMOTION                                │   │
│  │  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐  │   │
│  │  │  Body PNG   │ +  │  Mouth PNG  │ +  │  Word Timestamps│  │   │
│  │  │  (pose)     │    │  (state)    │    │  (lip-sync)     │  │   │
│  │  └─────────────┘    └─────────────┘    └─────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Schemas

### 1. Character Manifest (`characters.manifest.json`)

```json
{
  "version": "1.0.0",
  "packs": [
    {
      "characterId": "neo",
      "displayName": "Neo Presenter",
      "style": "stick_figure_svg",
      "variants": [
        {
          "id": "classic/idle__glasses",
          "file": "characters/neo/classic/idle__glasses.body.png",
          "mouthClosed": "characters/neo/classic/idle__glasses.mouth_closed.png",
          "mouthOpenSmall": "characters/neo/classic/idle__glasses.mouth_open_small.png",
          "mouthOpenBig": "characters/neo/classic/idle__glasses.mouth_open_big.png",
          "tags": ["idle", "classic", "glasses"],
          "w": 480,
          "h": 720,
          "crop": { "left": 272, "top": 180, "width": 480, "height": 720 },
          "prompt": "Full-body stick figure...",
          "createdAt": "2025-12-28T20:00:00Z"
        }
      ]
    }
  ]
}
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `characterId` | string | ✅ | Unique character identifier |
| `displayName` | string | ✅ | Human-readable name |
| `style` | string | ✅ | "stick_figure_svg", "flat_vector", "3d_pixar" |
| `variants` | array | ✅ | All pose/theme/accessory combinations |
| `variants[].id` | string | ✅ | Variant key: `{theme}/{pose}__{accessory}` |
| `variants[].file` | string | ✅ | Body PNG path |
| `variants[].mouthClosed` | string | ❌ | Closed mouth layer |
| `variants[].mouthOpenSmall` | string | ❌ | Small open mouth |
| `variants[].mouthOpenBig` | string | ❌ | Big open mouth |
| `variants[].w` | number | ❌ | Width in pixels |
| `variants[].h` | number | ❌ | Height in pixels |
| `variants[].crop` | object | ❌ | Crop box used for alignment |

### 2. Pack Config (`characters.pack.config.json`)

Defines batch generation parameters.

```json
{
  "version": "1.0.0",
  "outputCharacterStyle": "stick_figure_svg",
  "poses": ["idle", "talk_1", "talk_2", "point_right", "point_left", "think", "surprised"],
  "themes": [
    { "id": "classic", "stroke": "#000000", "strokeWidth": 18 },
    { "id": "blue", "stroke": "#2F5BFF", "strokeWidth": 18 },
    { "id": "thick", "stroke": "#000000", "strokeWidth": 26 }
  ],
  "characters": [
    {
      "characterId": "neo",
      "displayName": "Neo",
      "accessories": ["glasses"],
      "vibe": "friendly"
    },
    {
      "characterId": "ivy",
      "displayName": "Ivy",
      "accessories": ["cap"],
      "vibe": "goofy"
    }
  ]
}
```

### 3. Word Timestamps (`words.json`)

From Whisper ASR for lip-sync.

```json
{
  "model": "whisper-1",
  "words": [
    { "text": "Hello", "start": 0.0, "end": 0.32 },
    { "text": "everyone", "start": 0.35, "end": 0.78 },
    { "text": "welcome", "start": 0.82, "end": 1.15 }
  ]
}
```

---

## Components

### 1. AI Image Generator

Generates character PNGs from prompts.

```typescript
async function generateCharacterImage(args: {
  prompt: string;
  outFileAbs: string;
  size?: "1024x1024" | "1536x1536";
}) {
  const res = await fetch("https://api.openai.com/v1/images", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "gpt-image-1",
      prompt: args.prompt,
      size: args.size ?? "1024x1024",
    }),
  });
  // ... save base64 to PNG
}
```

**Prompt Template for Consistency:**
```
Full-body character, front view, centered, no background / transparent background.
Same outfit, same proportions, same character identity.
Pose: idle / pointing / talking / thinking.
No props, no text, no watermark, clean silhouette.
```

### 2. Background Remover (rembg)

Local U2Net-based background removal.

```typescript
async function removeBackgroundRembg(args: {
  inFileAbs: string;
  outFileAbs: string;
}) {
  await spawn("python3", ["-m", "rembg", "i", args.inFileAbs, args.outFileAbs]);
}
```

**Requirements:**
```bash
python3 -m pip install rembg
```

### 3. Auto-Cropper

Trims transparent borders with padding.

```typescript
async function trimTransparent(args: {
  inFileAbs: string;
  outFileAbs: string;
  pad?: number;
}) {
  const img = sharp(args.inFileAbs);
  const { data, info } = await img.ensureAlpha().raw().toBuffer({ resolveWithObject: true });
  
  // Find alpha bounds
  let minX = w, minY = h, maxX = -1, maxY = -1;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const alpha = data[(y * w + x) * 4 + 3];
      if (alpha > 0) {
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
    }
  }
  
  // Apply padding and crop
  await sharp(args.inFileAbs)
    .extract({ left: minX - pad, top: minY - pad, width: cropW, height: cropH })
    .png()
    .toFile(args.outFileAbs);
}
```

### 4. SVG Stick Figure Generator

For maximum consistency, generate SVG first then render to PNG.

**System Prompt:**
```
Output only valid SVG markup.
viewBox="0 0 1024 1024", transparent background.
Stick figure: line, circle, path.
stroke="#000", stroke-width="18", stroke-linecap="round".
Center feet around y=880, head around y=260.
```

**Pose Prompts:**

| Pose | Description |
|------|-------------|
| `idle` | Arms relaxed slightly out from body |
| `talk_1` | Right hand slightly raised |
| `talk_2` | Left hand slightly raised |
| `point_right` | Right arm straight pointing right |
| `point_left` | Left arm straight pointing left |
| `think` | Right hand touching chin |
| `surprised` | Hands near head, mouth "O" |

### 5. SVG Post-Processor

Applies themes and injects accessories.

```typescript
function postProcessSvg(args: {
  svg: string;
  theme: { stroke: string; strokeWidth: number };
  accessory?: "none" | "glasses" | "cap" | "hoodie";
}) {
  // Inject <style> for consistent stroke
  // Inject accessory SVG elements
}
```

**Accessory SVG Templates:**

```typescript
const accessories = {
  glasses: `
    <circle cx="470" cy="270" r="34"></circle>
    <circle cx="554" cy="270" r="34"></circle>
    <line x1="504" y1="270" x2="520" y2="270"></line>
  `,
  cap: `
    <path d="M420 235 Q512 170 604 235"></path>
    <path d="M604 235 Q665 245 690 270"></path>
  `,
  hoodie: `
    <path d="M420 430 Q512 360 604 430"></path>
    <line x1="490" y1="470" x2="490" y2="560"></line>
  `
};
```

### 6. Mouth Layer Generator

Separate mouth from body for lip-sync.

```typescript
type MouthState = "closed" | "open_small" | "open_big";

function mouthSvg(state: MouthState) {
  const mouth = {
    closed: `<path d="M480 320 Q512 340 544 320" />`,
    open_small: `<ellipse cx="512" cy="330" rx="14" ry="18" />`,
    open_big: `<ellipse cx="512" cy="330" rx="20" ry="28" />`
  };
  
  return `<svg viewBox="0 0 1024 1024"><g id="mouth">${mouth[state]}</g></svg>`;
}
```

### 7. Crop Box Alignment

All layers (body + mouth states) use same crop box for perfect alignment.

```typescript
// 1. Find crop box from body alpha
const cropBox = await findAlphaCropBox({ inFileAbs: bodyPng });

// 2. Apply same crop to all mouth layers
await cropToBox({ inFileAbs: mouthClosedPng, box: cropBox });
await cropToBox({ inFileAbs: mouthOpenSmallPng, box: cropBox });
await cropToBox({ inFileAbs: mouthOpenBigPng, box: cropBox });
```

### 8. Word Timestamp Transcriber

Generate word-level timestamps for lip-sync.

```typescript
const transcription = await openai.audio.transcriptions.create({
  file: fs.createReadStream(audioPath),
  model: "whisper-1",
  response_format: "verbose_json",
  timestamp_granularities: ["word"],
});

// Returns: { words: [{ word, start, end }, ...] }
```

### 9. Mouth State Driver

Maps frame → mouth state based on word timestamps.

```typescript
function mouthStateAtFrame(args: {
  frame: number;
  fps: number;
  words: Word[];
  holdFramesAfterWord?: number;
}): MouthState {
  const t = args.frame / args.fps;
  
  // Find active word
  const active = args.words.find(w => t >= w.start && t <= w.end);
  if (active) return scoreWord(active);
  
  // Hold mouth briefly after word ends (prevents flicker)
  const holdSec = args.holdFramesAfterWord / args.fps;
  const justEnded = args.words.find(w => t > w.end && t <= w.end + holdSec);
  if (justEnded) return "open_small";
  
  return "closed";
}

function scoreWord(w: Word): MouthState {
  const dur = w.end - w.start;
  const vowels = (w.text.match(/[aeiou]/gi) ?? []).length;
  const score = dur * 2 + vowels * 0.35;
  
  if (score > 1.2) return "open_big";
  return "open_small";
}
```

---

## File Structure

```
project/
├── public/
│   └── assets/
│       ├── characters/
│       │   └── neo/
│       │       └── classic/
│       │           ├── idle__glasses.body.png
│       │           ├── idle__glasses.mouth_closed.png
│       │           ├── idle__glasses.mouth_open_small.png
│       │           ├── idle__glasses.mouth_open_big.png
│       │           ├── talk_1__glasses.body.png
│       │           └── ...
│       ├── characters.manifest.json
│       └── ._tmp/                    # Intermediate files
├── scripts/
│   ├── characters.pack.config.json
│   ├── build-stickfig-pack.ts        # Single character
│   ├── build-stickfig-packs.ts       # Batch factory
│   ├── stickfig/
│   │   ├── prompts.ts
│   │   ├── generate-svg.ts
│   │   ├── render-and-crop.ts
│   │   ├── svg-postprocess.ts
│   │   ├── mouth-layer.ts
│   │   ├── crop-utils.ts
│   │   └── pack-config.ts
│   └── asr/
│       └── transcribe-words.ts
├── src/
│   ├── characters/
│   │   └── selectVariant.ts
│   ├── mouth/
│   │   ├── types.ts
│   │   ├── mouthStateAtFrame.ts
│   │   └── talkPoseAtFrame.ts
│   └── CharacterSprite.tsx
└── types.ts
```

---

## Pipeline Commands

### Package.json Scripts

```json
{
  "scripts": {
    "char:build": "tsx scripts/build-stickfig-pack.ts neo",
    "char:build-all": "tsx scripts/build-stickfig-packs.ts scripts/characters.pack.config.json",
    "asr:transcribe": "tsx scripts/asr/transcribe-words.ts public/audio/voice.mp3 public/audio/words.json"
  }
}
```

### Full Generation Flow

```
1. Define characters.pack.config.json
   ↓
2. pnpm char:build-all
   → Generates all character/theme/pose/accessory combinations
   → Writes characters.manifest.json
   ↓
3. pnpm asr:transcribe (for lip-sync)
   → Generates words.json from audio
   ↓
4. Remotion reads manifest + words
   → Renders animated character with lip-sync
```

---

## Remotion Components

### CharacterSprite.tsx

```tsx
export const CharacterSprite: React.FC<{
  characterId: string;
  themeId?: string;
  accessory?: "none" | "glasses" | "cap" | "hoodie";
  mode?: "idle" | "talk" | "point_right" | "think" | "surprised";
  x?: number;
  y?: number;
  targetHeightPx?: number;
  words?: Word[];
}> = (props) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  // Load manifest
  const manifest = require("../public/assets/characters.manifest.json");
  const pack = manifest.packs.find(p => p.characterId === props.characterId);
  
  // Select pose variant
  const talking = props.words?.some(w => t >= w.start && t <= w.end);
  const pose = talking 
    ? (frame % Math.floor(fps / 6) < Math.floor(fps / 12) ? "talk_1" : "talk_2")
    : props.mode;
  
  const variantId = `${props.themeId}/${pose}__${props.accessory}`;
  const variant = pack.variants.find(v => v.id === variantId);
  
  // Calculate mouth state
  const mouthState = mouthStateAtFrame({ frame, fps, words: props.words ?? [] });
  
  // Scale to target height
  const scale = props.targetHeightPx / variant.h;
  
  return (
    <div style={{ transform: `scale(${scale})` }}>
      <Img src={staticFile(`assets/${variant.file}`)} />
      <Img src={staticFile(`assets/${variant[`mouth${capitalize(mouthState)}`]}`)} />
    </div>
  );
};
```

### Usage Example

```tsx
<CharacterSprite
  characterId="neo"
  themeId="classic"
  accessory="glasses"
  mode="talk"
  x={260}
  y={900}
  targetHeightPx={520}
  words={wordsJson.words}
/>
```

---

## Lip-Sync Details

### Mouth States

| State | Description | Trigger |
|-------|-------------|---------|
| `closed` | Neutral mouth line | No active word |
| `open_small` | Small ellipse | Short word, few vowels |
| `open_big` | Large ellipse | Long word, many vowels |

### Word Scoring Algorithm

```typescript
function scoreWord(word: Word): MouthState {
  const duration = word.end - word.start;
  const vowelCount = (word.text.match(/[aeiou]/gi) ?? []).length;
  
  const score = duration * 2 + vowelCount * 0.35;
  
  if (score > 1.2) return "open_big";   // Long/vowel-heavy
  if (score > 0.4) return "open_small"; // Normal
  return "open_small";                   // Default when speaking
}
```

### Hold Frames

Prevents mouth "flickering" between words:

```typescript
const holdFramesAfterWord = 3; // Keep mouth slightly open after word ends
```

---

## Character Styles

### Supported Styles

| Style | Description | Pros | Cons |
|-------|-------------|------|------|
| `stick_figure_svg` | SVG-first, rendered to PNG | Consistent, recolorable | Simple aesthetic |
| `flat_vector` | AI-generated flat art | More detailed | Identity drift |
| `3d_pixar` | AI-generated 3D style | Rich visuals | Hardest to maintain |

### Recommended: Stick Figure SVG

**Why:**
- Same proportions every time
- Easy theme changes (color, thickness)
- Clean alpha (transparent by default)
- Fast generation
- Instant recoloring

---

## Accessories

| Accessory | SVG Location | Description |
|-----------|--------------|-------------|
| `glasses` | Head region (y~270) | Two circles + bridge + temples |
| `cap` | Above head (y~235) | Curved cap + brim |
| `hoodie` | Shoulders (y~430) | Hood lines + drawstrings |

---

## Themes

| Theme | Stroke | Width | Use Case |
|-------|--------|-------|----------|
| `classic` | #000000 | 18 | Default black |
| `blue` | #2F5BFF | 18 | Brand color |
| `thick` | #000000 | 26 | Bold emphasis |

---

## Dependencies

```json
{
  "dependencies": {
    "openai": "^4.0.0",
    "@resvg/resvg-js": "^2.0.0",
    "sharp": "^0.33.0"
  },
  "devDependencies": {
    "tsx": "^4.0.0"
  }
}
```

**Python Requirements:**
```bash
pip install rembg  # For background removal
```

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Character Consistency | 95%+ | Same identity across poses |
| Asset Generation Time | < 30s/character | Full pack generation |
| Lip-Sync Accuracy | < 50ms drift | Word-to-mouth alignment |
| File Size | < 100KB/PNG | After cropping |
| Manifest Coverage | 100% | All assets indexed |

---

## Future Enhancements

### Phase 2
- [ ] Eyeblink animation layers
- [ ] Hand gesture layers
- [ ] Multiple character interactions

### Phase 3
- [ ] Video-based lip-sync (visemes)
- [ ] Emotion expressions (happy, sad, angry)
- [ ] Body language poses

### Phase 4
- [ ] AI upscaling for higher resolution
- [ ] Spritesheet generation for animation
- [ ] Real-time character generation API

---

## Appendix

### A. Full Pose Prompt Template

```
Create a single stick-figure character as valid SVG markup ONLY.
viewBox="0 0 1024 1024". Transparent background.
stroke="#000", stroke-width="18", stroke-linecap="round".
Head is a circle; body/arms/legs are single strokes.
Full body, centered. Feet near y=900. Head around y=260.
Add simple face: two small eye circles ONLY. DO NOT draw mouth.
No text, no props, no watermark.

Pose: TALK_1. Right hand slightly raised as if talking.
Face expression: friendly, slight smile implied by eyes.
```

### B. SVG Render to PNG

```typescript
import { Resvg } from "@resvg/resvg-js";

async function svgToPng(svg: string, outPath: string) {
  const resvg = new Resvg(svg, {
    fitTo: { mode: "width", value: 1024 },
    background: "transparent",
  });
  
  const pngData = resvg.render().asPng();
  await fs.writeFile(outPath, pngData);
}
```

### C. Whisper Word Timestamps

```typescript
const transcription = await openai.audio.transcriptions.create({
  file: fs.createReadStream("voice.mp3"),
  model: "whisper-1",
  response_format: "verbose_json",
  timestamp_granularities: ["word"],
});

// Output:
// { words: [{ word: "Hello", start: 0.0, end: 0.32 }, ...] }
```
