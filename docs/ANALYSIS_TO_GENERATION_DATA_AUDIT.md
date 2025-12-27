# Analysis to Video Generation: Comprehensive Data Audit

This document maps all analysis data captured by the MediaPoster system and how it flows to creative briefs, CopyPlan generation, and Remotion video rendering.

> **Status**: ✅ Fully Implemented (v3.2)
> **Last Updated**: December 27, 2024

## 📊 Complete Analysis Data Model

### 1. VideoAnalysis Database Fields (`video_analysis` table)

| Field | Type | Source | Used In Creative Brief | Used In Video Generation |
|-------|------|--------|----------------------|-------------------------|
| **Core Content** |
| `transcript` | Text | Whisper API | ✅ Yes - script basis | ✅ Yes - narration |
| `topics` | Text[] | GPT-4 Analysis | ✅ Yes - key points | ✅ Yes - theme |
| `hooks` | Text[] | GPT-4 Analysis | ✅ Yes - hook section | ✅ Yes - opening scene |
| `tone` | Text | GPT-4 Analysis | ✅ Yes - style guide | ✅ Yes - mood directive |
| `pacing` | Text | GPT-4 Analysis | ✅ Yes - shot timing | ✅ Yes - clip duration |
| `key_moments` | JSONB | GPT-4 Analysis | ✅ Yes - shot treatment | ✅ Yes - scene breaks |
| `detected_hook` | Text | GPT-4 Analysis | ✅ Yes - key message | ✅ Yes - first 3s script |
| **Visual Analysis** |
| `visual_analysis` | JSONB | GPT-4 Vision | ✅ Yes - look & feel | ✅ Yes - visual prompts |
| `deep_analysis` | JSONB | GPT-4 Vision | ⚠️ Partial | ⚠️ Partial |
| `frame_analyses` | JSONB | GPT-4 Vision | ✅ Yes - shot descriptions | ✅ Yes - scene prompts |
| **Audio Analysis** |
| `audio_analysis` | JSONB | FFmpeg/ML | ⚠️ Partial | ✅ Yes - audio cues |
| `has_background_music` | Boolean | Audio Analysis | ✅ Yes - music suggestion | ✅ Yes - audio track |
| `audio_type` | Text | Audio Analysis | ⚠️ Partial | ✅ Yes - audio mixing |
| `music_confidence` | Numeric | Audio Analysis | ❌ No | ⚠️ Partial |
| `speech_ratio` | Numeric | Audio Analysis | ❌ No | ⚠️ Partial |
| `music_characteristics` | JSONB | Audio Analysis | ✅ Yes - music cue | ✅ Yes - BPM/mood |
| **Transcription Metadata** |
| `transcription_data` | JSONB | Whisper API | ⚠️ Partial | ✅ Yes - word timing |
| `transcription_language` | Text | Whisper API | ✅ Yes - localization | ✅ Yes - TTS voice |
| `transcription_duration_sec` | Numeric | Whisper API | ✅ Yes - duration target | ✅ Yes - clip length |
| `transcription_word_count` | Integer | Whisper API | ✅ Yes - script length | ✅ Yes - pacing calc |
| `words_per_minute` | Numeric | Calculated | ✅ Yes - pacing guide | ✅ Yes - TTS speed |
| `significant_pauses` | JSONB | Calculated | ⚠️ Partial | ✅ Yes - scene breaks |
| `avg_confidence` | Numeric | Whisper API | ❌ No | ❌ No |
| `silence_ratio` | Numeric | Calculated | ⚠️ Partial | ✅ Yes - pacing |
| **Content Metadata** |
| `pre_social_score` | Numeric | GPT-4 Analysis | ✅ Yes - rationale | ❌ No |
| `pillar_tags` | Text[] | GPT-4 Analysis | ✅ Yes - audience | ✅ Yes - theme |
| `format_tags` | Text[] | Calculated | ✅ Yes - format | ✅ Yes - aspect ratio |
| `music_suggestion` | JSONB | GPT-4 Analysis | ✅ Yes - music cue | ✅ Yes - audio track |
| **Music Matching** |
| `suggested_music_id` | Text | AI Matching | ✅ Yes - music cue | ✅ Yes - audio track |
| `music_match_score` | Numeric | AI Matching | ❌ No | ❌ No |
| `music_match_reasoning` | Text | AI Matching | ✅ Yes - music section | ❌ No |
| `music_alternatives` | JSONB | AI Matching | ⚠️ Partial | ⚠️ Partial |

### 2. Analysis Service Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        VIDEO ANALYSIS PIPELINE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────┐    ┌───────────────┐    ┌──────────────┐                │
│  │  Video    │───▶│ Whisper API   │───▶│ Transcript   │                │
│  │  File     │    │ (venv311)     │    │ + Metadata   │                │
│  └───────────┘    └───────────────┘    └──────────────┘                │
│       │                                       │                         │
│       │           ┌───────────────┐          │                         │
│       └──────────▶│ Frame Extract │          │                         │
│                   │ (FFmpeg)      │          │                         │
│                   └───────────────┘          │                         │
│                          │                   │                         │
│                          ▼                   ▼                         │
│                   ┌───────────────┐   ┌──────────────┐                 │
│                   │ GPT-4 Vision  │   │ GPT-4 Text   │                 │
│                   │ Analysis      │   │ Analysis     │                 │
│                   └───────────────┘   └──────────────┘                 │
│                          │                   │                         │
│                          ▼                   ▼                         │
│                   ┌─────────────────────────────────┐                  │
│                   │     VideoAnalysis Record        │                  │
│                   │  (60+ fields of rich data)      │                  │
│                   └─────────────────────────────────┘                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 🎬 Creative Brief Data Requirements

### CreativeBrief Model Fields → Analysis Source

| Brief Field | Required Analysis Data | Current Status |
|-------------|----------------------|----------------|
| **Product Section** |
| `product_name` | External (product DB) | N/A |
| `category` | `pillar_tags[0]` | ✅ Available |
| `price_range` | External (product DB) | N/A |
| **Performance Rationale** |
| `revenue_30d` | External (metrics DB) | N/A |
| `viral_score` | `pre_social_score` | ✅ Available |
| `top_video_contribution` | External (metrics DB) | N/A |
| **Target Audience** |
| `pain_points` | `topics` / GPT-4 extraction | ⚠️ Needs extraction |
| `emotional_drivers` | `tone` + `hooks` analysis | ⚠️ Needs extraction |
| `niche` | `pillar_tags` | ✅ Available |
| **Core Insight** |
| `core_promise` | `detected_hook` or `hooks[0]` | ✅ Available |
| `angle_types` | `topics` + `format_tags` | ✅ Available |
| **Key Message** |
| `hook_line` | `detected_hook` | ✅ Available |
| `cta_style` | GPT-4 extraction | ⚠️ Needs extraction |
| **Shot Treatment** |
| `scenes[]` | `frame_analyses` + `key_moments` | ✅ Available |
| `camera_direction` | `visual_analysis.shot_type` | ⚠️ Partial |
| `action` | `visual_analysis.description` | ✅ Available |
| `on_screen_text` | `visual_analysis.text_detected` | ⚠️ Partial |
| **Look & Feel** |
| `color_palette` | `visual_analysis.colors` | ⚠️ Needs extraction |
| `lighting` | `visual_analysis.lighting` | ⚠️ Needs extraction |
| `setting` | `visual_analysis.setting` | ⚠️ Partial |
| **Music** |
| `music_mood` | `music_suggestion.mood` | ✅ Available |
| `music_genre` | `music_suggestion.genre` | ✅ Available |
| `music_tempo` | `music_characteristics.tempo_bpm` | ✅ Available |

## 🔧 Video Generation Service Requirements

### NarrativeVideoBrief → Analysis Source

| Generation Field | Required Analysis Data | Current Status |
|-----------------|----------------------|----------------|
| `topic` | `topics[0]` | ✅ Available |
| `objective` | From narrative goal | External |
| `hook` | `detected_hook` | ✅ Available |
| `key_points` | `topics` | ✅ Available |
| `call_to_action` | GPT-4 extraction | ⚠️ Needs extraction |
| `target_duration_seconds` | `transcription_duration_sec` | ✅ Available |
| `tone` | `tone` | ✅ Available |
| `audience` | `pillar_tags` | ✅ Available |
| `visual_style` | From `visual_analysis` | ⚠️ Needs extraction |

### ClipPlan Generation → Analysis Source

| Clip Field | Required Analysis Data | Current Status |
|------------|----------------------|----------------|
| `narration.text` | `transcript` (segmented) | ✅ Available |
| `target_seconds` | `transcription_duration_sec` / clips | ✅ Available |
| `visual_prompt` | `frame_analyses[i].description` | ✅ Available |
| `shot_type` | `visual_analysis.shot_type` | ⚠️ Partial |
| `setting` | `visual_analysis.setting` | ⚠️ Partial |
| `camera_motion` | From `visual_analysis` | ⚠️ Needs extraction |
| `objects` | `visual_analysis.objects` | ⚠️ Partial |

## 🚨 GAP Analysis: Missing Data Extractions

### High Priority Gaps

1. **CTA Extraction** - Need to extract call-to-action from transcript
   - Current: Not extracted
   - Solution: Add GPT-4 extraction step for CTA patterns

2. **Emotional Drivers** - Need to identify emotional triggers
   - Current: Only `tone` captured
   - Solution: Expand GPT-4 analysis prompt

3. **Pain Points** - Need explicit pain point extraction
   - Current: Implied in `topics`
   - Solution: Add dedicated extraction

4. **Visual Style Details** - Need structured visual extraction
   - Current: Unstructured in `visual_analysis`
   - Solution: Structured GPT-4 Vision prompts

### Medium Priority Gaps

5. **Color Palette** - Not explicitly extracted
   - Current: May be in `visual_analysis` description
   - Solution: Add color extraction to Vision analysis

6. **Camera Motion** - Not captured
   - Current: Missing
   - Solution: Add to frame comparison analysis

7. **Scene Boundaries** - Automatic scene detection
   - Current: Manual via `key_moments`
   - Solution: Use `significant_pauses` + visual changes

## 📋 Recommended Analysis Prompt Enhancements

### Enhanced GPT-4 Content Analysis Prompt

```python
ENHANCED_ANALYSIS_PROMPT = """
Analyze this video transcript for viral potential and content patterns.

TRANSCRIPT:
{transcript}

Provide analysis in JSON format with the following structure:
{
  "topics": [list of 3-5 main topics/themes],
  "hooks": [list of 2-4 attention-grabbing phrases],
  "detected_hook": "single best hook phrase",
  "tone": "overall tone",
  "pacing": "delivery speed",
  "key_moments": {
    "timestamp": "description"
  },
  
  // NEW: Emotional & Pain Point Analysis
  "emotional_triggers": [list of emotional elements],
  "pain_points": [list of problems/frustrations addressed],
  "emotional_journey": {
    "opening_emotion": "",
    "peak_emotion": "",
    "closing_emotion": ""
  },
  
  // NEW: CTA Analysis
  "call_to_action": {
    "type": "follow|subscribe|purchase|dm|link",
    "text": "exact CTA text",
    "timestamp": "when CTA appears"
  },
  
  // NEW: Scene Structure
  "scene_structure": [
    {
      "start_sec": 0,
      "end_sec": 3,
      "role": "hook|problem|solution|proof|cta",
      "summary": "brief description"
    }
  ],
  
  // Existing fields
  "viral_score": <0-100>,
  "viral_analysis": "explanation",
  "improvement_suggestions": [2-3 suggestions],
  "music_suggestion": {
    "mood": "",
    "genre": "",
    "tempo": "fast/medium/slow",
    "reasoning": ""
  }
}
"""
```

### Enhanced GPT-4 Vision Analysis Prompt

```python
ENHANCED_VISION_PROMPT = """
Analyze this video frame for content creation purposes.

Provide structured analysis:
{
  // Basic Visual
  "description": "detailed description",
  "shot_type": "close-up|medium|wide|POV|overhead",
  "camera_angle": "eye-level|low|high|dutch",
  "camera_motion": "static|pan|tilt|zoom|tracking|handheld",
  
  // Setting & Objects
  "setting": "specific location description",
  "main_objects": ["list", "of", "objects"],
  "text_on_screen": "any visible text",
  "text_style": "caption|title|subtitle|graphics",
  
  // Style Elements
  "lighting": "natural|studio|dramatic|soft|harsh",
  "color_palette": ["primary", "secondary", "accent"],
  "color_mood": "warm|cool|neutral|vibrant|muted",
  "visual_style": "professional|ugc|raw|polished",
  
  // People & Emotion
  "people_present": true/false,
  "people_count": 0,
  "facial_expression": "emotion if visible",
  "body_language": "description",
  
  // Viral Elements
  "hook_potential": 0-100,
  "pattern_interrupt": true/false,
  "meme_potential": true/false,
  "scroll_stopper_elements": ["list"]
}
"""
```

## 🔄 Data Flow to Video Generation Services

### Complete Pipeline

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  VideoAnalysis  │────▶│  Creative Brief  │────▶│  Video Generation │
│  (60+ fields)   │     │  Service         │     │  (Sora/Runway)    │
└─────────────────┘     └──────────────────┘     └───────────────────┘
        │                        │                        │
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│ transcript      │────▶│ script           │────▶│ narration         │
│ topics          │────▶│ key_points       │────▶│ theme             │
│ hooks           │────▶│ hook_line        │────▶│ opening_scene     │
│ tone            │────▶│ tone_guide       │────▶│ mood_directive    │
│ pacing          │────▶│ shot_timing      │────▶│ clip_duration     │
│ visual_analysis │────▶│ look_and_feel    │────▶│ visual_prompts    │
│ music_suggestion│────▶│ music_cue        │────▶│ audio_track       │
│ key_moments     │────▶│ shot_treatment   │────▶│ scene_breaks      │
│ frame_analyses  │────▶│ shot_descriptions│────▶│ per_clip_prompts  │
└─────────────────┘     └──────────────────┘     └───────────────────┘
```

## ✅ Implementation Status

### Completed ✓

1. [x] Add `call_to_action` extraction to `ContentAnalyzer.analyze_transcript()`
2. [x] Add `pain_points` extraction to analysis prompt
3. [x] Add `emotional_drivers` extraction to analysis prompt
4. [x] Add `scene_structure` extraction to analysis
5. [x] Add `emotional_journey` extraction (opening/peak/closing)
6. [x] Add `content_type` classification
7. [x] Add `target_audience` extraction
8. [x] Create database migration for new fields (v3.2)
9. [x] Create Content Pipeline schema (10 new tables)
10. [x] Create `platform_text_constraints` with official limits
11. [x] Implement `CopyPlanService` for platform-optimized copy
12. [x] Implement `RemotionSpecService` for video rendering specs
13. [x] Create TypeScript types for frontend integration
14. [x] Create API endpoints for content pipeline

### Pending

- [ ] Enhance Vision analysis with structured extraction
- [ ] Add `camera_motion` detection via frame comparison
- [ ] Build automatic scene boundary detection from visual changes
- [ ] Create template library from high-performing videos

---

## 🆕 Content Pipeline System (Implemented)

### New Database Tables

| Table | Purpose |
|-------|---------|
| `content_asset` | Canonical video/media assets with dedup hashes |
| `deep_audit` | Comprehensive AI analysis (pre-post) |
| `platform_post` | Published content across platforms |
| `post_snapshot` | Performance metrics at T+1h, T+24h, T+7d |
| `retention_series` | Watch-time retention curves |
| `comment_event` | Individual comments with sentiment |
| `platform_text_constraints` | Character limits per platform/surface |
| `copy_plan` | AI-generated platform-optimized copy |
| `remotion_render_spec` | Video composition specs for Remotion |
| `beat_sheet` | Scene/segment structure with timing |

### Platform Text Constraints (80% Target Rule)

| Platform | Surface | Field | Max | Target (80%) |
|----------|---------|-------|-----|--------------|
| YouTube | video | title | 100 | 80 |
| YouTube | video | description | 5000 | 4000 |
| Instagram | reel | caption | 2200 | 1760 |
| TikTok | video | caption | 2200 | 1760 |
| X | standard_post | caption | 280 | 224 |
| LinkedIn | post | caption | 3000 | 2400 |
| Threads | post | caption | 500 | 400 |
| Pinterest | pin | title | 100 | 80 |

### API Endpoints

```
GET  /api/content-pipeline/constraints
GET  /api/content-pipeline/constraints/{platform}/{surface}
POST /api/content-pipeline/copy-plan/generate
GET  /api/content-pipeline/copy-plan/{id}
POST /api/content-pipeline/remotion-spec/generate
GET  /api/content-pipeline/remotion-spec/{id}
GET  /api/content-pipeline/remotion-spec/compositions
```

### CopyPlan Generation Flow

```
VideoAnalysis → CopyPlanInput → LLM Generation → Enforcement Pass → CopyPlanV1
     ↓              ↓                ↓                 ↓              ↓
 - hook         - topics         - GPT-4o-mini    - truncate      - title variants
 - topics       - pain_points    - platform       - char count    - caption
 - tone         - cta            - specific       - fits check    - description
 - pain_points  - audience       - prompts        - word boundary - hashtags
```

### RemotionRenderSpec Generation Flow

```
VideoAnalysis → DeepAuditData → RemotionSpecService → RemotionRenderSpecV1
     ↓              ↓                  ↓                    ↓
 - transcript   - words[]         - words_to_segments   - captions
 - scene_struct - beat_sheet      - scene_to_beats      - beats
 - duration     - source_url      - build_timeline      - timeline
```

---

*Updated: 2024-12-27*
*Analysis Version: 3.2*

*Related Files:*
- `/Backend/services/video_analyzer.py`
- `/Backend/services/content_analyzer.py`
- `/Backend/services/content_pipeline/` (NEW)
  - `text_utils.py` - Character counting & truncation
  - `copy_plan_service.py` - CopyPlan generation
  - `remotion_spec_service.py` - Remotion spec builder
- `/Backend/api/endpoints/content_pipeline.py` (NEW)
- `/Backend/models/creative_brief_models.py`
- `/Backend/services/creative_brief_service.py`
- `/Backend/database/models.py` (VideoAnalysis class)
- `/dashboard/app/types/content-pipeline.ts` (NEW)
- `/supabase/migrations/20241227000007_content_pipeline_schema.sql` (NEW)
- `/supabase/migrations/20241227000008_platform_constraints_seed.sql` (NEW)
