# 🎯 Schema Consolidation Plan

## Overview
You've shared **5 different schema designs** that need to be unified into MediaPoster. Here's how they map together:

---

## 1️⃣ **Core Domains**

### **A. Identity & People** (EverReach CRM)
- `users` - App users/workspace members
- `workspaces` - Multi-tenant workspaces
- `people` - External humans (audience, leads)
- `identities` - Social handles per person
- `person_events` - Interactions across platforms
- `person_insights` - AI-derived preferences
- `segments` - Audience grouping
- `outbound_messages` - DMs, emails sent

### **B. Content & Media**
- `videos` - Source video files
- `content_items` - Canonical content (cross-platform)
- `content_variants` - Platform-specific versions
- `clips` - Time-range segments from videos
- `clip_styles` - Captions + headline overlays per platform

### **C. Viral Analysis** (NEW - Just created)
- `video_analysis` - FATE scores, hooks, CTAs
- `video_words` - Word-level timestamps
- `video_frames` - Frame-by-frame visual analysis
- `video_audio_analysis` - Voice, pacing, music
- `video_copy_elements` - Hooks, CTAs, text overlays
- `video_segments` - Timeline structure (hook/body/CTA)
- `video_retention_events` - Drop points
- `viral_patterns` - Pattern library

### **D. Publishing & Distribution**
- `social_accounts` - Connected platforms
- `posts` - Scheduled/published content
- `post_platform_publish` - Platform IDs/URLs
- `post_checkbacks` - Metrics at 1h, 6h, 24h, 7d
- `post_comments` - Comments + sentiment
- `metric_rollups` - NSM aggregations

### **E. AI & Automation**
- `ai_generations` - Title/caption/hashtag variants
- `vision_jobs` - OpenAI Vision calls
- `transcript_words` - Whisper output
- `music_recommendations` - Best music per video
- `thumbnail_candidates` - Best frames for thumbnails
- `insights` - Auto-generated recommendations

### **F. Connectors & Integration**
- `external_accounts` - OAuth tokens (Meta, YouTube, TikTok)
- `meta_connections` - FB/IG/Threads mapping
- `esp_accounts` - Email service providers
- `enrichment_jobs` - Social→email lookups

---

## 2️⃣ **Schema Overlaps & Conflicts**

### **CONFLICT 1: Videos**
- Schema A: Simple `videos` table
- Schema B: `videos` + `content_items` split
- Schema C: `videos` with comprehensive analysis
- **RESOLUTION**: Keep one `videos` table, link to `content_items` for cross-platform canonical ID

### **CONFLICT 2: Posts**
- Schema A: `posts` + `content_variants`
- Schema B: `posts` + `platform_posts`
- **RESOLUTION**: Merge into `posts` + `content_variants` + `post_platform_publish`

### **CONFLICT 3: Transcripts**
- Schema A: `video_transcripts` + `transcript_words`
- Schema B: `transcripts` + `transcript_words`
- **RESOLUTION**: Use `video_transcripts` (more explicit naming)

### **CONFLICT 4: Frames**
- Schema A: `video_frames` + `frame_analysis` (separated)
- Schema B: `video_frames` (combined)
- **RESOLUTION**: Keep separated for clean Vision API jobs

### **CONFLICT 5: Metrics**
- Schema A: `content_metrics` + `content_rollups`
- Schema B: `post_checkbacks` + `metric_rollups`
- **RESOLUTION**: Merge into unified checkback system

---

## 3️⃣ **Unified Entity Relationship**

```
IDENTITY GRAPH:
workspaces
  ├─ users (workspace_members)
  ├─ people (audience)
  │   ├─ identities (social handles)
  │   ├─ person_events (interactions)
  │   └─ person_insights (AI analysis)
  └─ segments
      └─ segment_members

CONTENT GRAPH:
content_items (canonical)
  ├─ videos (source files)
  │   ├─ video_transcripts
  │   │   └─ video_words
  │   ├─ video_segments
  │   ├─ video_frames
  │   │   └─ frame_analysis
  │   ├─ video_analysis (FATE)
  │   ├─ video_audio_analysis
  │   ├─ video_copy_elements
  │   └─ video_retention_events
  ├─ clips (time ranges)
  │   └─ clip_styles (per platform)
  └─ content_variants (platform posts)
      ├─ posts (scheduled)
      ├─ post_platform_publish
      ├─ post_checkbacks
      └─ post_comments

AI & RECOMMENDATIONS:
  ├─ ai_generations
  ├─ vision_jobs
  ├─ music_recommendations
  ├─ thumbnail_candidates
  ├─ viral_patterns
  └─ insights

CONNECTORS:
  ├─ social_accounts
  ├─ external_accounts
  ├─ meta_connections
  ├─ esp_accounts
  └─ enrichment_jobs
```

---

## 4️⃣ **Migration Strategy**

### **Phase 1: Core + Identity** (Week 1)
- ✅ `workspaces`, `users`, `workspace_members`
- ✅ `people`, `identities`, `person_events`
- ✅ `segments`, `segment_members`

### **Phase 2: Content Foundation** (Week 2)
- ✅ `content_items`, `videos`
- ✅ `content_variants`
- ✅ `clips`, `clip_styles`

### **Phase 3: Viral Analysis** (Week 3)
- ✅ `video_analysis`, `video_segments`
- ✅ `video_words`, `video_frames`
- ✅ `video_audio_analysis`
- ✅ `video_copy_elements`
- ✅ `viral_patterns`

### **Phase 4: Publishing** (Week 4)
- ✅ `social_accounts`, `posts`
- ✅ `post_platform_publish`
- ✅ `post_checkbacks`, `post_comments`

### **Phase 5: AI & Insights** (Week 5)
- ✅ `ai_generations`, `vision_jobs`
- ✅ `music_recommendations`
- ✅ `thumbnail_candidates`
- ✅ `insights`

### **Phase 6: Connectors** (Week 6)
- ✅ `external_accounts`, `meta_connections`
- ✅ `esp_accounts`, `enrichment_jobs`

---

## 5️⃣ **Next Steps**

1. **Review this consolidation** - Make sure all domains are needed
2. **Create Phase 1 migration** - Start with core + identity
3. **Build incrementally** - Don't try to implement everything at once
4. **Test each phase** - Ensure data flows correctly before moving on

---

## 6️⃣ **Recommended Approach**

### **Option A: Full System (All 6 Phases)**
Build the complete EverReach + MediaPoster + Viral Analysis system.
- **Timeline**: 6-8 weeks
- **Complexity**: Very High
- **Value**: Complete solution

### **Option B: MediaPoster First (Phases 2-5)**
Focus on content → viral analysis → publishing → insights.
Skip the full CRM (people graph) for now.
- **Timeline**: 4 weeks
- **Complexity**: High
- **Value**: Immediate viral video insights

### **Option C: Viral Analysis Only (Phase 3)**
Just add the comprehensive viral analysis to your existing videos table.
- **Timeline**: 1 week
- **Complexity**: Medium
- **Value**: Quick wins, learn patterns

---

## 🎯 **My Recommendation**

Start with **Option C** (Viral Analysis Only):

1. ✅ Run `add_comprehensive_viral_schema.sql` (already created)
2. ✅ Build word + frame analyzers
3. ✅ Populate viral patterns
4. ✅ See what works for YOUR content
5. → Then expand to publishing/calendar
6. → Then consider full CRM if needed

**Why?** You'll get immediate value, learn what matters, and avoid over-engineering.

---

Want me to create:
1. **Phase 1 migration** (just the essentials)?
2. **Complete unified schema** (all 6 phases)?
3. **ERD visualization** (dbdiagram.io format)?
