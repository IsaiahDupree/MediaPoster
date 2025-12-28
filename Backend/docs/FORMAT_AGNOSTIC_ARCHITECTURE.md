# Format-Agnostic Video Rendering Architecture

**Date:** December 28, 2024  
**Status:** ✅ Core Architecture Implemented

---

## 🎯 Core Concept

**Separate Format from Content**

```
Content → Format → Scene Graph → Render
```

This architecture enables:
- ✅ Multiple formats from same content
- ✅ Reusable scene components
- ✅ Pluggable rendering adapters
- ✅ Service-level abstraction

---

## 📐 Architecture Overview

```
VideoRenderService
├─ formats/          # Format definitions
│  ├─ explainer.py
│  ├─ listicle.py
│  ├─ comparison.py
│  ├─ narrative.py
│  └─ shorts.py
│
├─ scenes/           # Reusable scene components (future)
│  ├─ TopicScene.tsx
│  ├─ GridScene.tsx
│  └─ ComparisonScene.tsx
│
├─ adapters/         # Rendering engines
│  ├─ motion_canvas_adapter.py
│  └─ remotion_adapter.py
│
├─ schema/           # Data schemas
│  ├─ content.schema.json
│  └─ format.schema.json
│
└─ renderer.py        # Core rendering service
```

---

## 📋 Universal Content Schema

All content follows this format-agnostic schema:

```json
{
  "meta": {
    "project_id": "string",
    "language": "en",
    "tone": "neutral"
  },
  "items": [
    {
      "id": "string",
      "type": "topic | comparison | beat | scene",
      "title": "string",
      "description": "string",
      "audio": {
        "narration": "string",
        "duration": 60
      }
    }
  ]
}
```

---

## 🎨 Format Definitions

Each format is pure configuration:

### Explainer Format
- **Layout:** Single focus
- **Scene Order:** intro → item_loop → outro
- **Timing:** 60s per item
- **Best for:** Educational content, tutorials

### Listicle Format
- **Layout:** Grid
- **Scene Order:** intro → grid_intro → item_loop → outro
- **Timing:** 15s per item
- **Best for:** Top 10 lists, quick tips

### Comparison Format
- **Layout:** Split screen
- **Scene Order:** intro → item_loop → outro
- **Timing:** 45s per item
- **Best for:** Product comparisons, pros/cons

### Narrative Format
- **Layout:** Single focus
- **Scene Order:** intro → item_loop → outro
- **Timing:** 90s per item
- **Best for:** Storytelling, case studies

### Shorts Format
- **Layout:** Single focus (vertical)
- **Scene Order:** hook → item_loop → cta
- **Timing:** 5s per item
- **Best for:** TikTok, Instagram Reels, YouTube Shorts

---

## 🔄 Rendering Flow

1. **Content Input**
   - Universal content schema
   - Format-agnostic

2. **Format Selection**
   - Choose format (explainer_v1, listicle_v1, etc.)
   - Load format configuration

3. **Scene Graph Building**
   - Map content items to scenes
   - Apply format timing/visuals
   - Generate scene sequence

4. **Adapter Rendering**
   - Pass scene graph to adapter
   - Motion Canvas or Remotion
   - Generate final video

---

## 🚀 API Endpoints

### List Formats
```
GET /api/video-formats/formats
```

### Get Format
```
GET /api/video-formats/formats/{format_id}
```

### Render Video
```
POST /api/video-formats/render
{
  "content": {...},
  "format_id": "explainer_v1",
  "adapter": "motion_canvas"
}
```

### Preview Scene Graph
```
POST /api/video-formats/preview-scene-graph
{
  "content": {...},
  "format_id": "explainer_v1"
}
```

---

## 📝 Usage Example

```python
from services.video_renderer import VideoRenderService

# Initialize service
service = VideoRenderService()

# Create content (universal schema)
content = {
    "meta": {"project_id": "my_video"},
    "items": [
        {"id": "1", "type": "topic", "title": "Topic 1", ...},
        {"id": "2", "type": "topic", "title": "Topic 2", ...},
    ]
}

# Build scene graph for explainer format
scene_graph = service.build_scene_graph(content, "explainer_v1")

# Scene graph is ready for adapter rendering
# (Adapter integration coming next)
```

---

## ✅ Current Status

- ✅ Universal content schema defined
- ✅ Format definition schema created
- ✅ 5 core formats implemented
- ✅ Format registry system
- ✅ Scene graph builder
- ✅ API endpoints created
- ⏳ Adapter integration (next step)
- ⏳ Reusable scene components (future)

---

## 🎯 Next Steps

1. **Adapter Integration**
   - Connect scene graph to Motion Canvas adapter
   - Implement scene component rendering
   - Generate actual videos

2. **Reusable Scene Components**
   - Create TopicScene component
   - Create GridScene component
   - Create ComparisonScene component

3. **Format Auto-Selection**
   - Analyze content to suggest best format
   - Content type detection

4. **Custom Formats**
   - User-defined format creation
   - Format marketplace

---

## 🧠 Why This Architecture?

- **Formats change faster than content** → Separate them
- **Scenes are reusable** → Component-based
- **Config > code** → Format definitions are data
- **Engines scale, templates don't** → Service architecture

This is the same pattern used in:
- CMSs (Contentful, Strapi)
- Design systems (Figma, Sketch)
- Ad rendering engines (Google, Facebook)
- Internal creator tools (Canva, Adobe)

