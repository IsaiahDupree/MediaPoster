# Media Factory PRD: End-to-End Content Production Pipeline

**Version:** 1.0  
**Date:** December 26, 2024  
**Status:** Planning Phase  
**Owner:** MediaPoster Development Team

---

## Executive Summary

This PRD defines a complete "media factory" system that transforms content briefs into published videos across platforms. The system uses a clean, service-oriented architecture with JSON contracts, enabling agentic workflows and provider swapping without breaking changes.

**Core Value Proposition:**
- Input: Content brief (trend + angle + audience)
- Output: Published video (Shorts, Reels, TikTok, longform) with analytics
- Process: Fully automated pipeline with quality gates

---

## 1. System Architecture

### 1.1 Pipeline Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    INPUT: Content Brief                         │
│  (Topic, Angle, Audience, Platform, Style Preset, UGC Clips)   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
   ┌────▼────┐                    ┌─────▼─────┐
   │ Stage A │                    │  Trend   │
   │ Script  │                    │ Analysis │
   │ + Shot  │                    │  Engine  │
   │  Plan   │                    └──────────┘
   └────┬────┘
        │
   ┌────▼────┐
   │ Stage B │
   │   TTS   │ (Hugging Face API)
   └────┬────┘
        │
   ┌────▼────┐
   │ Stage C │
   │  Music  │ (Suno/SoundCloud)
   └────┬────┘
        │
   ┌────▼────┐
   │ Stage D │
   │Visuals  │ (Matting, B-Roll, Memes)
   └────┬────┘
        │
   ┌────▼────┐
   │ Stage E│
   │Remotion │ (Composition + Render)
   └────┬────┘
        │
   ┌────▼────┐
   │ Stage F │
   │Publish  │ (Multi-platform + Analytics)
   └─────────┘
```

### 1.2 Service Contracts (JSON)

All services communicate via JSON contracts, enabling:
- Provider swapping (HF ↔ ElevenLabs, Suno ↔ SoundCloud)
- Independent service scaling
- Agentic orchestration
- Testing and debugging

---

## 2. Stage A: Script + Shot Plan

### 2.1 Input Contract

```json
{
  "brief_id": "uuid",
  "trend_cluster": {
    "name": "AI stickman explainer videos",
    "why_now": "Multiple channels reposting similar format",
    "evidence": {
      "top_questions": ["how do they make these?", "what tools?"],
      "intent_signals": ["template requests", "repo requests"]
    }
  },
  "angle": {
    "target_niche": "creators + solopreneurs",
    "promise": "Turn any trend into a repeatable video brief",
    "unique_lens": "engineering-style scoring rubric"
  },
  "video_spec": {
    "format": "Shorts",
    "length_sec": 45,
    "hook_sec": 1.2,
    "pattern_interrupt_sec": 4,
    "caption_style": "burned-in + emphasized keywords"
  },
  "style_preset": "dev_vlog_meme"  // or "explainer", "brand_promo"
}
```

### 2.2 Output Contract: `script.json`

```json
{
  "brief_id": "uuid",
  "title": "If you can rank trends, you can print content",
  "hook": "If you can rank trends, you can print content—here's the rubric.",
  "segments": [
    {
      "id": "seg_001",
      "t": "0-2",
      "text": "If you can rank trends, you can print content—here's the rubric.",
      "intent": "hook",
      "on_screen": ["TREND ≠ STRATEGY"],
      "visual_style": "big_text_punch_in",
      "emphasis_words": ["rank", "print", "rubric"]
    },
    {
      "id": "seg_002",
      "t": "2-12",
      "text": "Most people chase trends with no product fit and wonder why it doesn't convert.",
      "intent": "problem",
      "on_screen": ["Problem: No Product Fit"],
      "visual_style": "diagram",
      "emphasis_words": ["chase", "product fit", "convert"]
    }
  ],
  "metadata": {
    "total_duration_sec": 45,
    "word_count": 120,
    "estimated_tts_duration": 42
  }
}
```

### 2.3 Output Contract: `shotlist.json`

```json
{
  "brief_id": "uuid",
  "fps": 30,
  "resolution": "1080x1920",
  "shots": [
    {
      "id": "shot_001",
      "t": "0-2",
      "type": "text_overlay",
      "content": {
        "text": "TREND ≠ STRATEGY",
        "style": "big_bold",
        "animation": "punch_in"
      },
      "background": "solid_color",
      "color": "#000000"
    },
    {
      "id": "shot_002",
      "t": "2-12",
      "type": "diagram",
      "content": {
        "template": "problem_solution",
        "text": "Problem: No Product Fit"
      },
      "background": "b_roll",
      "b_roll_keywords": ["trending", "social media", "analytics"]
    }
  ]
}
```

### 2.4 Implementation

- **Service**: `ScriptGeneratorService`
- **Input**: Content brief (from trend analysis or manual)
- **Output**: `script.json` + `shotlist.json`
- **AI Model**: GPT-4 or Claude (via existing MediaPoster AI services)

---

## 3. Stage B: Voice (TTS)

### 3.1 Input Contract

```json
{
  "script_id": "uuid",
  "script_json": {...},  // From Stage A
  "voice_config": {
    "model": "indextts2",  // or "coqui_xtts", "hf_metavoice"
    "voice_reference": "/path/to/voice.wav",
    "emotion": {
      "method": "vectors",
      "vectors": {"happy": 0.8, "calm": 0.2},
      "weight": 0.8
    }
  },
  "output_format": "wav",
  "sample_rate": 22050
}
```

### 3.2 Output Contract: `voice.json`

```json
{
  "script_id": "uuid",
  "audio_path": "/data/tts_outputs/voice_123.wav",
  "duration_seconds": 42.5,
  "word_timestamps": [
    {
      "word": "If",
      "start": 0.0,
      "end": 0.15,
      "segment_id": "seg_001"
    },
    {
      "word": "you",
      "start": 0.15,
      "end": 0.3,
      "segment_id": "seg_001"
    }
  ],
  "sentence_timestamps": [
    {
      "text": "If you can rank trends, you can print content—here's the rubric.",
      "start": 0.0,
      "end": 2.1,
      "segment_id": "seg_001"
    }
  ],
  "model_used": "indextts2",
  "generation_time": 3.4
}
```

### 3.3 Implementation

- **Service**: TTS Service (✅ Already implemented)
- **Provider**: Hugging Face API (IndexTTS2) - **API-based, not local**
- **Integration**: Via event bus (`tts.requested` → `tts.completed`)

**Critical Requirement**: Use Hugging Face API, not local models, for cross-platform compatibility.

---

## 4. Stage C: Music Bed

### 4.1 Input Contract

```json
{
  "script_id": "uuid",
  "duration_seconds": 45,
  "mood_tags": ["energetic", "tech", "upbeat"],
  "bpm_target": 120,
  "style": "background_music",
  "ducking_rules": {
    "duck_under_voice": true,
    "duck_db": -6
  }
}
```

### 4.2 Output Contract: `music.json`

```json
{
  "script_id": "uuid",
  "audio_path": "/data/music/music_123.wav",
  "duration_seconds": 45,
  "bpm": 120,
  "provider": "suno",  // or "soundcloud", "local"
  "track_id": "suno_abc123",
  "metadata": {
    "title": "Tech Background Loop",
    "artist": "Suno AI"
  }
}
```

### 4.3 Implementation

- **Service**: Music Service (🚧 To be implemented)
- **Providers**: Suno API, SoundCloud API, local library
- **Integration**: Via event bus (`music.requested` → `music.completed`)

---

## 5. Stage D: Visuals

### 5.1 Input Contract

```json
{
  "script_id": "uuid",
  "shotlist_json": {...},  // From Stage A
  "ugc_sources": [
    {
      "type": "video",
      "path": "/path/to/ugc.mp4",
      "operation": "matting",  // Extract person/object
      "position": "bottom_left",
      "size": "30%"
    }
  ],
  "b_roll_requirements": [
    {
      "keywords": ["trending", "social media"],
      "duration": 12,
      "style": "stock_footage"
    }
  ],
  "meme_templates": [
    {
      "template_id": "meme_001",
      "text": "TREND ≠ STRATEGY",
      "t": "0-2"
    }
  ]
}
```

### 5.2 Output Contract: `visuals.json`

```json
{
  "script_id": "uuid",
  "assets": {
    "ugc_cutout": {
      "path": "/data/matting/ugc_cutout_123.mov",
      "has_alpha": true,
      "duration": 45
    },
    "b_roll": [
      {
        "path": "/data/broll/broll_001.mp4",
        "keywords": ["trending", "social media"],
        "duration": 12
      }
    ],
    "memes": [
      {
        "path": "/data/memes/meme_001.png",
        "template_id": "meme_001"
      }
    ]
  },
  "timeline_visuals": [
    {
      "t": "0-2",
      "type": "text_overlay",
      "asset_path": "/data/memes/meme_001.png"
    }
  ]
}
```

### 5.3 Video Matting (SAM 2)

**Implementation**: Use SAM 2 via Hugging Face API for video segmentation

**Input**:
```json
{
  "source_video": "/path/to/ugc.mp4",
  "operation": "extract_person",  // or "extract_object", "remove_background"
  "target_description": "person in center",  // SAM 2 prompt
  "model": "sam2",  // Via Hugging Face API
  "output_format": "mov",
  "preserve_alpha": true
}
```

**Output**:
```json
{
  "job_id": "uuid",
  "output_path": "/data/matting/cutout_123.mov",
  "mask_path": "/data/matting/mask_123.mov",
  "processing_time": 120.5,
  "model_used": "sam2",
  "frames_processed": 1350
}
```

**Critical Requirement**: Use Hugging Face Inference API for SAM 2, not local installation, for:
- Cross-platform compatibility (Mac/Windows)
- No local GPU requirements
- Consistent behavior
- Easier scaling

### 5.4 Implementation

- **Service**: Matting Service (🚧 To be implemented)
- **Provider**: Hugging Face Inference API (SAM 2)
- **Integration**: Via event bus (`matting.requested` → `matting.completed`)

---

## 6. Stage E: Edit + Render (Remotion)

### 6.1 Input Contract: `timeline.json`

```json
{
  "brief_id": "uuid",
  "fps": 30,
  "resolution": "1080x1920",
  "duration": 45,
  "layers": [
    {
      "id": "layer_001",
      "type": "video",
      "source": "/data/matting/ugc_cutout_123.mov",
      "position": {"x": 0, "y": 1200, "width": 540, "height": 720},
      "start": 0,
      "end": 45,
      "opacity": 1.0
    },
    {
      "id": "layer_002",
      "type": "video",
      "source": "/data/broll/broll_001.mp4",
      "position": {"x": 0, "y": 0, "width": 1080, "height": 1920},
      "start": 2,
      "end": 14,
      "opacity": 0.8
    },
    {
      "id": "layer_003",
      "type": "text",
      "content": "TREND ≠ STRATEGY",
      "position": {"x": 540, "y": 960},
      "start": 0,
      "end": 2,
      "style": {
        "fontSize": 72,
        "fontWeight": "bold",
        "color": "#FFFFFF"
      },
      "animation": "punch_in"
    }
  ],
  "audio": [
    {
      "id": "audio_001",
      "type": "voice",
      "source": "/data/tts_outputs/voice_123.wav",
      "start": 0,
      "volume": 1.0
    },
    {
      "id": "audio_002",
      "type": "music",
      "source": "/data/music/music_123.wav",
      "start": 0,
      "volume": 0.3,
      "ducking": {
        "duck_under": "audio_001",
        "duck_db": -6
      }
    }
  ],
  "events": [
    {
      "t": 0,
      "type": "zoom",
      "target": "layer_003",
      "scale": 1.2,
      "duration": 0.5
    },
    {
      "t": 2,
      "type": "caption_highlight",
      "words": ["rank", "print", "rubric"],
      "duration": 2.1
    }
  ],
  "captions": {
    "enabled": true,
    "style": "burned_in",
    "source": "/data/tts_outputs/voice_123.json",  // word_timestamps
    "emphasis_words": true
  }
}
```

### 6.2 Output Contract

```json
{
  "brief_id": "uuid",
  "video_path": "/data/renders/final_123.mp4",
  "video_url": "https://...",
  "duration_seconds": 45,
  "file_size_mb": 125.3,
  "render_time": 180.5,
  "variants": [
    {
      "format": "shorts",
      "path": "/data/renders/final_123_shorts.mp4"
    },
    {
      "format": "reels",
      "path": "/data/renders/final_123_reels.mp4"
    }
  ],
  "thumbnails": [
    {
      "path": "/data/renders/thumb_123_001.jpg",
      "timestamp": 1.0
    }
  ]
}
```

### 6.3 Implementation

- **Service**: Remotion Service (🚧 To be implemented)
- **Framework**: Remotion (React-based video composition)
- **Integration**: Via event bus (`remotion.requested` → `remotion.completed`)
- **Multi-source Support**:
  - Local files
  - URLs (download and cache)
  - TTS audio (subscribe to `tts.completed`)
  - MediaPoster media library
  - Matting outputs (subscribe to `matting.completed`)

---

## 7. Stage F: Distribution

### 7.1 Input Contract

```json
{
  "brief_id": "uuid",
  "video_path": "/data/renders/final_123.mp4",
  "platforms": ["youtube_shorts", "tiktok", "instagram_reels"],
  "metadata": {
    "title": "If you can rank trends, you can print content",
    "description": "...",
    "hashtags": ["#trending", "#content"],
    "thumbnail": "/data/renders/thumb_123_001.jpg"
  },
  "scheduled_for": "2024-12-27T10:00:00Z"
}
```

### 7.2 Output Contract

```json
{
  "brief_id": "uuid",
  "published": [
    {
      "platform": "youtube_shorts",
      "url": "https://youtube.com/shorts/...",
      "post_id": "abc123",
      "published_at": "2024-12-27T10:00:00Z"
    }
  ],
  "analytics_events": [
    {
      "event": "video.published",
      "brief_id": "uuid",
      "platform": "youtube_shorts",
      "timestamp": "2024-12-27T10:00:00Z"
    }
  ]
}
```

### 7.3 Implementation

- **Service**: Publishing Service (✅ Already exists in MediaPoster)
- **Integration**: Subscribe to `remotion.completed`
- **Platforms**: YouTube, TikTok, Instagram, etc. (via existing Blotato integration)

---

## 8. Content Brief System

### 8.1 Trend → Brief Pipeline

```
Trend Cards (Raw Input)
    ↓
Clusters (Merge Duplicates)
    ↓
Angles (Niche Convergence)
    ↓
Briefs (Production-Ready)
```

### 8.2 Brief Scoring: "Worth Covering" (0-100)

**Scoring Formula:**
- **Velocity** (0-25): Views/hour growth, shares/saves rate, comment velocity
- **Intent** (0-20): "How do I...", "What tool...", "Template?", "Link?", "Price?"
- **Product Fit** (0-25): Can you point to your service/product/lead magnet?
- **Differentiation** (0-15): Can you add unique lens (engineering, frameworks, teardown)?
- **Production Feasibility** (0-15): Can you produce it fast at quality bar?

**Threshold**: Only publish if Score ≥ 70, OR Score ≥ 60 + strategic tie-in

### 8.3 Brief Template

```json
{
  "brief_id": "uuid",
  "trend_cluster": {
    "name": "AI stickman explainer videos",
    "why_now": "Multiple channels reposting similar format",
    "evidence": {
      "top_questions": ["how do they make these?", "what tools?"],
      "intent_signals": ["template requests", "repo requests"]
    }
  },
  "angle": {
    "target_niche": "creators + solopreneurs",
    "promise": "Turn any trend into a repeatable video brief",
    "unique_lens": "engineering-style scoring rubric"
  },
  "score": 78,
  "video_spec": {
    "format": "Shorts",
    "length_sec": 45,
    "hook_sec": 1.2,
    "pattern_interrupt_sec": 4
  },
  "script_beats": [...],
  "visual_plan": [...],
  "cta": {
    "type": "comment_keyword",
    "keyword": "BRIEF",
    "deliverable": "Trend-to-Brief JSON + scoring sheet"
  }
}
```

### 8.4 Implementation

- **Service**: Content Brief Service (🚧 Enhance existing)
- **Integration**: Trend analysis → Brief generation → Pipeline trigger

---

## 9. Quality Standards

### 9.1 Minimum Baseline (Non-Negotiable)

**Audio:**
- Voice clarity first (no noise, no room echo)
- Music ducking under voice consistently (no "fighting")

**Pacing:**
- Hook within first 1.0-1.5 seconds
- Pattern interrupt every 3-6 seconds (visual change, emphasis, cut, zoom)

**Captions:**
- Burned-in captions, accurate, readable
- Emphasis words highlighted (not karaoke spam)

**Visual Clarity:**
- No clutter: one main idea per "screen moment"
- Intentional b-roll/memes (not random)

**CTA:**
- One primary CTA max (comment keyword / link / newsletter / product)

### 9.2 Service Tiers

1. **Standard**: Clean captions + basic motion + stock/meme overlays
2. **Pro**: Timed graphics + dynamic b-roll selection + on-screen frameworks
3. **Premium**: UGC matting + scene choreography + custom graphics + multi-variant outputs

### 9.3 Acceptance Checklist

- [ ] Hook lands in first 1.5s
- [ ] Captions error rate low (no obvious fails)
- [ ] No dead air > 0.3s unless intentional
- [ ] Audio levels stable (voice always intelligible)
- [ ] Visual changes at least every 3-6s
- [ ] CTA exists and matches topic intent

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- ✅ TTS Service (Already done)
- 🚧 SAM 2 Matting Service (Hugging Face API)
- 🚧 Remotion Service (Basic composition)
- 🚧 Content Brief Enhancement

### Phase 2: Integration (Week 3-4)
- 🚧 End-to-end pipeline (Brief → Script → TTS → Remotion → Publish)
- 🚧 Multi-source loader for Remotion
- 🚧 Quality gates and validation

### Phase 3: Enhancement (Week 5-6)
- 🚧 Music Service
- 🚧 B-roll generation/selection
- 🚧 Meme template system
- 🚧 Multi-variant rendering (Shorts, Reels, TikTok)

### Phase 4: Optimization (Week 7-8)
- 🚧 Performance optimization
- 🚧 Error recovery and retry logic
- 🚧 Comprehensive testing
- 🚧 Documentation and deployment guides

---

## 11. Technical Requirements

### 11.1 API Requirements

**All services must use APIs, not local models:**
- ✅ TTS: Hugging Face API (IndexTTS2)
- 🚧 Matting: Hugging Face Inference API (SAM 2)
- 🚧 Music: Suno API / SoundCloud API
- ✅ Remotion: Local (React-based, but can be containerized)

### 11.2 Cross-Platform Compatibility

- **Mac**: ✅ Supported
- **Windows**: ✅ Supported (via APIs, not local models)
- **Linux**: ✅ Supported (via APIs)

### 11.3 Dependencies

- Python 3.11+
- Node.js 20+ (for Remotion)
- FFmpeg (for video processing)
- Docker (optional, for containerization)

---

## 12. Success Metrics

- **Pipeline Completion Rate**: >95%
- **Quality Gate Pass Rate**: >90%
- **Average Render Time**: <5 minutes for 45s video
- **Multi-platform Publishing**: 100% success rate
- **Content Brief → Published Video**: <30 minutes end-to-end

---

## 13. Next Steps

1. **Research & Test SAM 2** via Hugging Face API
2. **Implement Remotion Service** with multi-source support
3. **Enhance Content Brief System** with scoring and templates
4. **Build End-to-End Pipeline** with quality gates
5. **Test & Optimize** for production readiness

---

## Appendix A: JSON Schema Definitions

(To be added in implementation phase)

## Appendix B: Error Handling & Retry Logic

(To be added in implementation phase)

## Appendix C: Deployment Guide

(To be added in implementation phase)

