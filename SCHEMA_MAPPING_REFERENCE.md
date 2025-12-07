# 🗺️ Schema Mapping Reference

## How Your 5 Schema Designs Map to MediaPoster

This document shows exactly how each table from your conversations maps to the final unified schema.

---

## 📋 Schema Source Legend

- **[CRM]** = People graph / EverReach CRM schema
- **[PUB]** = Publishing & calendar schema  
- **[VISION]** = OpenAI Vision + music + thumbnails schema
- **[VIRAL]** = Comprehensive viral analysis schema
- **[ALIGN]** = Timeline alignment schema

---

## 1️⃣ Identity & Access

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [PUB] `users` | `users` | ✅ Phase 1 | phase_1_essentials.sql |
| [PUB] `workspaces` | `workspaces` | ✅ Phase 1 | phase_1_essentials.sql |
| [PUB] `workspace_members` | `workspace_members` | ✅ Phase 1 | phase_1_essentials.sql |
| [CRM] `people` | `people` | 📋 Phase 5 | Not yet created |
| [CRM] `identities` | `identities` | 📋 Phase 5 | Not yet created |

---

## 2️⃣ Content & Media

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [CRM] `content_items` | `content_items` | ✅ Phase 1 | phase_1_essentials.sql |
| [PUB] `videos` | `videos` (enhanced) | ✅ Phase 1 | phase_1_essentials.sql |
| [PUB] `clips` | `clips` | ✅ Phase 1 | phase_1_essentials.sql |
| [PUB] `clip_styles` | `clip_styles` | ✅ Phase 1 | phase_1_essentials.sql |
| [CRM] `content_variants` | Merged into `posts` + `content_items` | ✅ Phase 1 | - |

**Mapping Logic**:
- `content_items` = Canonical content (one video = one content_item)
- `videos` = Source file storage
- `clips` = Time ranges within videos
- Posts reference both `clip_id` and `content_item_id`

---

## 3️⃣ Transcripts & Words

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [VISION] `video_transcripts` | `video_transcripts` | 🎬 Phase 2 | add_comprehensive_viral_schema.sql |
| [ALIGN] `transcripts` | Renamed to `video_transcripts` | 🎬 Phase 2 | - |
| [ALIGN] `transcript_words` | `video_words` | 🎬 Phase 2 | add_comprehensive_viral_schema.sql |
| [VISION] `transcript_words` | Merged into `video_words` | 🎬 Phase 2 | - |
| [VISION] `transcript_analysis` | Part of `video_analysis` | 🎬 Phase 2 | add_comprehensive_viral_schema.sql |
| [ALIGN] `segment_word_rollups` | Computed on-the-fly or part of `video_segments` | 🎬 Phase 2 | - |

**Consolidation**:
- One `video_words` table with all word-level features
- No separate rollup table (compute when needed)

---

## 4️⃣ Frames & Visual Analysis

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [VISION] `video_frames` | `video_frames` | 🎬 Phase 2 | add_comprehensive_viral_schema.sql |
| [ALIGN] `video_frames` | Same as above | 🎬 Phase 2 | - |
| [VISION] `vision_jobs` | `vision_jobs` | 📋 Phase 5 | Not yet created |
| [VISION] `frame_analysis` | Merged into `video_frames` | 🎬 Phase 2 | - |
| [ALIGN] `frame_analysis` | Merged into `video_frames` | 🎬 Phase 2 | - |

**Consolidation**:
- `video_frames` includes all analysis fields directly
- No separate `frame_analysis` table (keeps it simpler)
- `vision_jobs` will be added later for tracking API calls

---

## 5️⃣ Segments & Timeline

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [VISION] `video_segments` | `video_segments` | 🎬 Phase 2 | add_comprehensive_viral_schema.sql |
| [ALIGN] `video_segments` | Same as above | 🎬 Phase 2 | - |
| [VIRAL] Enhanced segments | `video_segments` (with extra columns) | 🎬 Phase 2 | add_comprehensive_viral_schema.sql |

**Features**:
- Segment types: hook, context, body, cta, outro
- Hook subtypes: pain, curiosity, aspirational, etc.
- Enhanced with pacing, clarity, value_density scores

---

## 6️⃣ Audio & Voice

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [VIRAL] `video_audio_analysis` | `video_audio_analysis` | 🎬 Phase 2 | add_comprehensive_viral_schema.sql |

**New table** - captures:
- Voice tone, pacing, energy
- Pauses and emphasis
- Music analysis
- Language complexity

---

## 7️⃣ Copy Elements (Hooks, CTAs)

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [VIRAL] `video_copy_elements` | `video_copy_elements` | 🎬 Phase 2 | add_comprehensive_viral_schema.sql |

**New table** - tracks:
- Hooks with strength scores
- CTAs with clarity scores
- On-screen text overlays
- Text styling and positioning

---

## 8️⃣ Viral Analysis & FATE

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| Basic `video_analysis` | `video_analysis` (enhanced) | 🎬 Phase 2 | add_comprehensive_viral_schema.sql |
| [VIRAL] Enhanced FATE | Part of `video_analysis` | 🎬 Phase 2 | - |
| [VIRAL] `video_platform_intent` | `video_platform_intent` | 🎬 Phase 2 | add_comprehensive_viral_schema.sql |
| [VIRAL] `video_offer_analysis` | `video_offer_analysis` | 🎬 Phase 2 | add_comprehensive_viral_schema.sql |

**Enhancements**:
- FATE model (Focus, Authority, Tribe, Emotion)
- AIDA model scores
- Story structure classification
- Target audience identification

---

## 9️⃣ Music & Thumbnails

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [VISION] `music_tracks` | `music_tracks` | 📋 Phase 5 | Not yet created |
| [VISION] `video_music_analysis` | `video_music_analysis` | 📋 Phase 5 | Not yet created |
| [VISION] `music_recommendations` | `music_recommendations` | 📋 Phase 5 | Not yet created |
| [VISION] `thumbnail_candidates` | `thumbnail_candidates` | 📋 Phase 5 | Not yet created |

**Status**: Coming in Phase 5 (AI Recommendations)

---

## 🔟 Publishing & Posts

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [PUB] `social_accounts` | `social_accounts` | ✅ Phase 1 | phase_1_essentials.sql |
| [PUB] `posts` | `posts` | ✅ Phase 1 | phase_1_essentials.sql |
| [PUB] `post_platform_publish` | `post_platform_publish` | ✅ Phase 1 | phase_1_essentials.sql |
| [CRM] `external_accounts` | Merged into `social_accounts` | ✅ Phase 1 | - |
| [CRM] `meta_connections` | `meta_connections` | 📋 Phase 6 | Not yet created |

**Consolidation**:
- `social_accounts` handles all platform connections
- `meta_connections` will be separate helper for FB/IG/Threads

---

## 1️⃣1️⃣ Metrics & Checkbacks

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [PUB] `post_checkbacks` | `post_checkbacks` | 📋 Phase 4 | Not yet created |
| [ALIGN] `platform_post_checkbacks` | Same as `post_checkbacks` | 📋 Phase 4 | - |
| [CRM] `content_metrics` | Merged into `post_checkbacks` | 📋 Phase 4 | - |
| [PUB] `post_comments` | `post_comments` | 📋 Phase 4 | Not yet created |
| [ALIGN] `platform_post_comments` | Same as `post_comments` | 📋 Phase 4 | - |
| [PUB] `metric_rollups` | `metric_rollups` | 📋 Phase 4 | Not yet created |
| [CRM] `content_rollups` | Merged into `metric_rollups` | 📋 Phase 4 | - |

**Status**: Coming in Phase 4 (Publishing & Metrics)

---

## 1️⃣2️⃣ Retention & Events

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [ALIGN] `retention_events` | `video_retention_events` | 🎬 Phase 2 | add_comprehensive_viral_schema.sql |
| [VIRAL] `video_retention_events` | Same as above | 🎬 Phase 2 | - |
| [PUB] `post_retention_points` | Merged into `post_checkbacks.retention_curve` (JSONB) | 📋 Phase 4 | - |

**Consolidation**:
- Retention curve stored as JSONB in checkbacks
- Individual drops/spikes in `video_retention_events`

---

## 1️⃣3️⃣ Patterns & Insights

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [VIRAL] `viral_patterns` | `viral_patterns` | 🎬 Phase 2 | add_comprehensive_viral_schema.sql |
| [VIRAL] `video_pattern_matches` | `video_pattern_matches` | 🎬 Phase 2 | add_comprehensive_viral_schema.sql |
| [PUB] `insights` | `insights` | 📋 Phase 4 | Not yet created |

**New capabilities**:
- Auto-learn winning patterns
- Match confidence scoring
- Generate recommendations

---

## 1️⃣4️⃣ AI Generations

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [PUB] `ai_generations` | `ai_generations` | 📋 Phase 5 | Not yet created |
| [VISION] `ai_generations` | Same as above | 📋 Phase 5 | - |

**Powers**:
- Title/caption/hashtag variants
- Hook generation
- Music/thumbnail suggestions

---

## 1️⃣5️⃣ People Graph (CRM)

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [CRM] `people` | `people` | 📋 Phase 5 | Not yet created |
| [CRM] `identities` | `identities` | 📋 Phase 5 | Not yet created |
| [CRM] `person_events` | `person_events` | 📋 Phase 5 | Not yet created |
| [CRM] `person_insights` | `person_insights` | 📋 Phase 5 | Not yet created |
| [CRM] `segments` | `segments` | 📋 Phase 5 | Not yet created |
| [CRM] `segment_members` | `segment_members` | 📋 Phase 5 | Not yet created |
| [CRM] `segment_insights` | `segment_insights` | 📋 Phase 5 | Not yet created |
| [CRM] `outbound_messages` | `outbound_messages` | 📋 Phase 5 | Not yet created |

**Optional**: Only needed if building full EverReach CRM

---

## 1️⃣6️⃣ Experiments

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [PUB] `experiments` | `experiments` | 📋 Phase 4 | Not yet created |
| [PUB] `experiment_variants` | `experiment_variants` | 📋 Phase 4 | Not yet created |
| [CRM] `content_experiments` | Same as `experiments` | 📋 Phase 4 | - |

---

## 1️⃣7️⃣ Email & ESP

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [CRM] `esp_accounts` | `esp_accounts` | 📋 Phase 6 | Not yet created |
| [CRM] `email_events_raw` | `email_events_raw` | 📋 Phase 6 | Not yet created |

**Optional**: Only if adding email capabilities

---

## 1️⃣8️⃣ Enrichment

| Your Schema | Final Table | Status | Migration |
|------------|-------------|--------|-----------|
| [CRM] `enrichment_jobs` | `enrichment_jobs` | 📋 Phase 6 | Not yet created |

**Optional**: Only for social→email lookups via RapidAPI

---

## 🎯 Summary by Phase

### **✅ Phase 1 (DONE)** - 10 tables
Foundation for content, clips, posts, publishing

### **🎬 Phase 2 (READY)** - 10 tables
Complete viral video analysis

### **📋 Phase 4 (PLANNED)** - 5 tables
Publishing metrics, checkbacks, insights, experiments

### **📋 Phase 5 (PLANNED)** - 12 tables
AI generations, music, thumbnails, vision jobs, people graph

### **📋 Phase 6 (OPTIONAL)** - 4 tables
ESP, enrichment, advanced connectors

---

## 🚀 Recommended Path

### **Start Here** (2 migrations):
1. ✅ `phase_1_essentials.sql`
2. 🎬 `add_comprehensive_viral_schema.sql`

**Result**: You'll have everything except:
- ❌ Checkback metrics (add later when you start publishing)
- ❌ People/CRM graph (only if you need it)
- ❌ Email ESP (only if you need it)

### **Add Later** (as needed):
3. Publishing metrics when you start posting
4. People graph if you want CRM
5. Email/ESP if you add email capabilities

---

## 📊 Table Count by Source

- **Phase 1 Essentials**: 10 tables
- **Comprehensive Viral**: 11 tables (+ enhances existing)
- **People Graph (Optional)**: 8 tables
- **Publishing Metrics**: 5 tables
- **AI & Recommendations**: 5 tables
- **ESP & Enrichment**: 4 tables

**Total if you use everything**: ~43 tables

**Recommended start**: 21 tables (Phase 1 + Viral Analysis)

---

**This mapping shows exactly how all 5 conversations consolidate into one coherent system! 🎯**
