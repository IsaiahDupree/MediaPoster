# Media Factory - Quick Reference Guide

**Last Updated:** December 26, 2024  
**Status:** Production Ready ✅

---

## 🎯 Overview

The Media Factory is an end-to-end content production pipeline that transforms trends into published videos automatically.

### Complete Pipeline Flow

```
Trends → Enhanced Brief → Script → TTS → Music → Visuals → Remotion → Publish
```

---

## 📦 Services

### Phase 1: Core Services ✅

#### 1. TTS Service
- **Model**: IndexTTS2 (Hugging Face API)
- **Features**: Emotion control, voice cloning
- **API**: `POST /api/tts/generate`
- **Events**: `tts.requested`, `tts.completed`, `tts.failed`

#### 2. Matting Service
- **Models**: RVM (primary), MediaPipe (fallback)
- **Features**: Video matting, alpha channel support
- **API**: `POST /api/matting/process`
- **Events**: `matting.requested`, `matting.completed`, `matting.failed`

#### 3. Remotion Service
- **Framework**: Remotion (React-based)
- **Features**: Multi-source loading, dynamic composition
- **API**: `POST /api/remotion/render`
- **Events**: `remotion.requested`, `remotion.completed`, `remotion.failed`

---

### Phase 2: Intelligence & Orchestration ✅

#### 4. Enhanced Content Brief Service
- **Features**: Scoring (0-100), clustering, angle generation, script generation
- **Scoring**: Velocity (0-25), Intent (0-20), Product Fit (0-25), Differentiation (0-15), Feasibility (0-15)
- **Threshold**: ≥70 (or ≥60 strategic)
- **Output**: `script.json` compatible with Media Factory

#### 5. Pipeline Orchestrator
- **Stages**: Brief → Script → TTS → Music → Visuals → Remotion → Publish
- **API**: `POST /api/pipeline/execute`
- **Status**: `GET /api/pipeline/status/{pipeline_id}`
- **Events**: `pipeline.requested`, `pipeline.completed`, `pipeline.failed`

---

### Phase 3: Assets & Media ✅

#### 6. Music Service
- **Sources**: Suno (local), SoundCloud (RapidAPI), Social Platforms (RapidAPI)
- **API**: `POST /api/music/request`
- **Events**: `music.requested`, `music.completed`, `music.failed`
- **Adapters**: SunoAdapter, SoundCloudAdapter, SocialPlatformAdapter

#### 7. Visuals Service
- **Types**: Meme, B-roll, UGC, Stock, Generated
- **Sources**: Local, RapidAPI, MediaPoster, UGC Library
- **API**: `POST /api/visuals/request`
- **Events**: `visuals.requested`, `visuals.completed`, `visuals.failed`
- **Adapters**: MemeAdapter, BrollAdapter, UGCAdapter

---

## 🔌 API Endpoints

### TTS
- `POST /api/tts/generate` - Generate speech
- `GET /api/tts/status/{job_id}` - Check status
- `GET /api/tts/models` - List models

### Matting
- `POST /api/matting/process` - Process video matting
- `GET /api/matting/status/{job_id}` - Check status
- `GET /api/matting/models` - List models

### Remotion
- `POST /api/remotion/render` - Render video
- `GET /api/remotion/status/{job_id}` - Check status
- `GET /api/remotion/source-types` - List source types

### Pipeline
- `POST /api/pipeline/execute` - Execute pipeline
- `GET /api/pipeline/status/{pipeline_id}` - Check status

### Music
- `POST /api/music/request` - Request music
- `GET /api/music/sources` - List sources

### Visuals
- `POST /api/visuals/request` - Request visuals
- `GET /api/visuals/types` - List types
- `GET /api/visuals/sources` - List sources

---

## 📡 Event Bus Topics

### TTS (7 topics)
- `tts.requested`, `tts.started`, `tts.progress`, `tts.completed`, `tts.failed`, `tts.model.loaded`, `tts.model.unloaded`

### Matting (8 topics)
- `matting.requested`, `matting.started`, `matting.segmenting`, `matting.extracting`, `matting.compositing`, `matting.progress`, `matting.completed`, `matting.failed`

### Remotion (7 topics)
- `remotion.requested`, `remotion.started`, `remotion.composing`, `remotion.rendering`, `remotion.progress`, `remotion.completed`, `remotion.failed`

### Content Brief (4 topics)
- `content.brief.generated`, `content.brief.scored`, `content.brief.approved`, `content.brief.script.generated`

### Pipeline (7 topics)
- `pipeline.requested`, `pipeline.started`, `pipeline.stage.started`, `pipeline.stage.completed`, `pipeline.progress`, `pipeline.completed`, `pipeline.failed`

### Music (7 topics)
- `music.requested`, `music.started`, `music.searching`, `music.downloading`, `music.progress`, `music.completed`, `music.failed`

### Visuals (7 topics)
- `visuals.requested`, `visuals.started`, `visuals.fetching`, `visuals.processing`, `visuals.progress`, `visuals.completed`, `visuals.failed`

**Total: 47 event topics**

---

## 🏗️ Architecture

### Adapter Pattern
All services use adapters for provider swapping:
- **TTS**: IndexTTS2Adapter (extensible)
- **Matting**: RVMAdapter, MediaPipeAdapter (extensible)
- **Music**: SunoAdapter, SoundCloudAdapter, SocialPlatformAdapter
- **Visuals**: MemeAdapter, BrollAdapter, UGCAdapter

### Event-Driven
- Loose coupling via event bus
- Async processing
- Progress tracking
- Error handling

### Multi-Source Support
- Local files
- RapidAPI (SoundCloud, social platforms)
- MediaPoster library
- UGC content

---

## 🚀 Quick Start

### 1. Execute Full Pipeline

```bash
POST /api/pipeline/execute
{
  "brief_id": "brief_123",
  "stages": ["brief", "script", "tts", "music", "visuals", "remotion", "publish"]
}
```

### 2. Check Pipeline Status

```bash
GET /api/pipeline/status/{pipeline_id}
```

### 3. Request Individual Services

```bash
# TTS
POST /api/tts/generate
{
  "text": "Hello, world!",
  "model": "indextts2",
  "voice_reference": "/path/to/voice.wav"
}

# Music
POST /api/music/request
{
  "source": "social_platform",
  "search_criteria": {
    "trending": true,
    "platform": "tiktok"
  }
}

# Visuals
POST /api/visuals/request
{
  "visuals_type": "broll",
  "source": "local",
  "search_criteria": {
    "keywords": ["tech", "lifestyle"]
  }
}
```

---

## 📊 Scoring System

### "Worth Covering" Score (0-100)

- **Velocity** (0-25): Views/hour growth, shares/saves rate, comment velocity
- **Intent** (0-20): "How do I...", "What tool...", "Template?", "Link?", "Price?"
- **Product Fit** (0-25): Can you point to service/product/lead magnet?
- **Differentiation** (0-15): Can you add unique lens?
- **Production Feasibility** (0-15): Can you produce it fast at quality bar?

**Threshold**: Only publish if Score ≥ 70, OR Score ≥ 60 + strategic tie-in

---

## 🔧 Configuration

### Environment Variables

```bash
# RapidAPI
RAPIDAPI_KEY=your_rapidapi_key

# Hugging Face
HF_TOKEN=your_hf_token

# OpenAI (for brief generation)
OPENAI_API_KEY=your_openai_key

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/db
```

### Directory Structure

```
data/
├── suno/              # Suno downloaded files
├── music/             # Music cache
│   ├── soundcloud/
│   └── tiktok/
├── memes/             # Meme templates
├── broll/             # B-roll footage
├── ugc/               # UGC content
├── tts_outputs/       # TTS generated audio
├── matting_outputs/   # Matting results
└── remotion_outputs/  # Rendered videos
```

---

## 🧪 Testing

### Run All Tests

```bash
pytest Backend/tests/media_factory/ -v
```

### Run Specific Service Tests

```bash
# TTS
pytest Backend/tests/media_factory/test_tts_service.py -v

# Matting
pytest Backend/tests/media_factory/test_matting_service.py -v

# Pipeline
pytest Backend/tests/media_factory/test_pipeline.py -v
```

### Test SAM 2 / Matting

```bash
python Backend/scripts/test_sam2_huggingface.py --image /path/to/image.jpg --model rmbg14
```

---

## 📚 Documentation

- **PRD**: `Backend/docs/MEDIA_FACTORY_PRD.md` - Complete system design
- **Phase 1**: `Backend/docs/PHASE_1_COMPLETE.md` - TTS, Matting, Remotion
- **Phase 2**: `Backend/docs/PHASE_2_COMPLETE.md` - Brief, Pipeline
- **Phase 3**: `Backend/docs/PHASE_3_COMPLETE.md` - Music, Visuals
- **Matting Comparison**: `Backend/docs/MATTING_SOLUTIONS_COMPARISON.md`
- **Implementation Phases**: `Backend/docs/IMPLEMENTATION_PHASES.md`

---

## 🎯 Key Features

✅ **End-to-End Automation** - Trends → Published Video  
✅ **Multi-Source Support** - Local, RapidAPI, MediaPoster  
✅ **Adapter Pattern** - Easy provider swapping  
✅ **Event-Driven** - Loose coupling, scalable  
✅ **Scoring System** - Quality filtering (0-100)  
✅ **Progress Tracking** - Real-time status updates  
✅ **Error Handling** - Graceful failure recovery  

---

## 🚧 Future Enhancements

- Multi-variant rendering (Shorts, Reels, TikTok)
- Quality gates automation
- Performance optimization
- Advanced analytics
- Real-time collaboration

---

## 📞 Support

For issues or questions:
1. Check documentation in `Backend/docs/`
2. Review test files in `Backend/tests/media_factory/`
3. Check event bus logs for debugging

---

**Media Factory is production-ready!** 🎉
