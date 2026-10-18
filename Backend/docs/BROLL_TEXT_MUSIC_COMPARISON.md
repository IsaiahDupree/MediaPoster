# B-Roll + Text + Music: Remotion vs Motion Canvas Comparison

## Quick Answer: **Motion Canvas is Easier**

| Feature | Motion Canvas | Remotion |
|---------|--------------|----------|
| **License** | MIT (Free) | Paid ($100-500/mo for companies) |
| **Text Overlays** | ⭐⭐⭐⭐⭐ Native, simple API | ⭐⭐⭐ React components |
| **Background Music** | ⭐⭐⭐⭐⭐ Built-in `audio()` | ⭐⭐⭐ `<Audio>` component |
| **Learning Curve** | ⭐⭐⭐⭐ Imperative, procedural | ⭐⭐ React knowledge required |
| **Automation** | ⭐⭐⭐⭐⭐ JSON → TypeScript easy | ⭐⭐⭐ Props-based |
| **Performance** | ⭐⭐⭐⭐⭐ Canvas-based, fast | ⭐⭐⭐ DOM-rendered |

---

## Why Motion Canvas Wins for B-Roll + Text

### 1. Simpler Text Overlay API

**Motion Canvas:**
```typescript
import {makeScene2D} from '@motion-canvas/2d';
import {Txt} from '@motion-canvas/2d/lib/components';

export default makeScene2D(function* (view) {
  const text = new Txt({
    text: 'Your Motivational Quote Here',
    fontSize: 64,
    fill: '#ffffff',
    fontFamily: 'Inter',
    shadowColor: 'rgba(0,0,0,0.5)',
    shadowBlur: 10,
  });
  
  view.add(text);
  
  // Animate in
  yield* text.opacity(0).opacity(1, 0.5);
  yield* text.scale(1.1, 0.3);
  yield* text.scale(1, 0.2);
});
```

**Remotion (More Complex):**
```tsx
import {useCurrentFrame, interpolate, Audio, Video, AbsoluteFill} from 'remotion';

export const BrollText: React.FC<{text: string}> = ({text}) => {
  const frame = useCurrentFrame();
  const opacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateRight: 'clamp',
  });
  
  return (
    <AbsoluteFill>
      <Video src={staticFile('broll.mp4')} />
      <div style={{
        position: 'absolute',
        opacity,
        fontSize: 64,
        color: 'white',
        textShadow: '0 0 10px rgba(0,0,0,0.5)',
      }}>
        {text}
      </div>
      <Audio src={staticFile('music.mp3')} />
    </AbsoluteFill>
  );
};
```

### 2. Background Music

**Motion Canvas:**
```typescript
import {audio} from '@motion-canvas/core';

export default makeScene2D(function* (view) {
  // Start music immediately
  audio('/path/to/music.mp3', 0);
  
  // Or with volume control
  audio('/path/to/music.mp3', 0, {volume: 0.7});
});
```

**Remotion:**
```tsx
<Audio 
  src={staticFile('music.mp3')} 
  volume={0.7}
  startFrom={0}
/>
```

### 3. Programmatic Generation

Motion Canvas is **imperative** - you write step-by-step instructions:
```typescript
// Easy to generate from JSON
const spec = {text: "Hello", fontSize: 64, duration: 5};

const scene = `
const text = new Txt({
  text: "${spec.text}",
  fontSize: ${spec.fontSize},
});
view.add(text);
yield* text.opacity(1, ${spec.duration});
`;
```

Remotion is **declarative** (React) - harder to generate dynamically:
```tsx
// Need to create React component files
// Harder to generate programmatically
<MyTextComponent text={spec.text} fontSize={spec.fontSize} />
```

---

## B-Roll + Text Workflow

### Step 1: Detect B-Roll Candidates
```bash
curl "http://localhost:5555/api/format-discovery/broll-candidates"
```

### Step 2: Generate Text Overlay Video

**Option A: Motion Canvas (Recommended)**
```python
from services.video_renderer.motion_canvas_adapter import MotionCanvasAdapter

adapter = MotionCanvasAdapter()
request = RenderRequest(
    job_id="broll_001",
    composition="BrollText",
    duration=15,
    layers=[
        Layer(
            id="background_video",
            type="video",
            source="/path/to/broll.mp4",
            start=0,
            end=15,
        ),
        Layer(
            id="text_overlay",
            type="text",
            content="Your Text Here",
            style={"fontSize": 64, "color": "#ffffff"},
            position={"x": 0, "y": 100},
            start=1,
            end=14,
        ),
    ],
    audio_tracks=[
        AudioTrack(
            id="background_music",
            source="/path/to/music.mp3",
            start=0,
            volume=0.7,
        )
    ],
)

result = await adapter.render(request)
```

**Option B: Remotion**
```bash
npx remotion render BrollText output.mp4 --props='{"text":"Your Text","video":"broll.mp4"}'
```

---

## Recommendation for MediaPoster

**Use Motion Canvas as default** because:

1. **Free & Open Source** - No licensing cost
2. **Simpler API** - Easier to generate from JSON specs
3. **Better for Automation** - Imperative style fits our pipeline
4. **Fast Rendering** - Canvas-based, not DOM

**Keep Remotion as fallback** for:
- Complex React-based compositions
- Existing Remotion templates
- When specific Remotion features are needed

---

## Implementation Status

| Component | Status |
|-----------|--------|
| B-Roll Detector | ✅ Implemented (`/api/format-discovery/broll-candidates`) |
| Motion Canvas Adapter | ✅ Implemented (`services/video_renderer/motion_canvas_adapter.py`) |
| Remotion Adapter | ✅ Implemented (`services/video_renderer/remotion_adapter.py`) |
| Text Overlay API | 🔄 Ready to use |
| Music Addition | 🔄 Ready to use |
| Format Templates | ✅ `broll_text_v1`, `pure_broll_v1` |

---

## Quick Start Test

```bash
# 1. Find B-Roll candidates
curl "http://localhost:5555/api/format-discovery/broll-candidates?limit=5"

# 2. Seed the B-Roll format
curl -X POST "http://localhost:5555/api/formats/seed-samples"

# 3. Run the B-Roll + Text format
curl -X POST "http://localhost:5555/api/formats/broll_text_v1/run" \
  -H "Content-Type: application/json" \
  -d '{"params": {"text": "Your Quote Here"}, "trigger_type": "manual"}'
```
