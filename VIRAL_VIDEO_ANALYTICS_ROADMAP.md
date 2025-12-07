# 🎬 Viral Video Analytics & Content Intelligence Roadmap

## Vision: Transform Raw Content Into Data-Driven Viral Growth

Based on your comprehensive viral video framework, this roadmap shows how we'll evolve from basic video management to a full content intelligence platform.

---

## ✅ **Phase 1: Foundation** (COMPLETE)

### What We Have Now
- ✅ Video library with pagination (50/100/250 per page)
- ✅ Basic search (file name)
- ✅ Source filtering (local, gdrive, supabase)
- ✅ **Media type filtering** (videos vs images)
- ✅ **Sort by**: created_at, file_name, file_size, duration_sec
- ✅ **Duration filters**: min/max seconds
- ✅ **File size filters**: min/max bytes
- ✅ Thumbnail status filter
- ✅ Analysis status filter

### Current Schema
```sql
videos:
  - id, user_id
  - source_type, source_uri
  - file_name, file_size
  - duration_sec, resolution, aspect_ratio
  - thumbnail_path
  - created_at, updated_at
```

---

## 🚧 **Phase 2: Timeline & Structure Analysis** (IN PROGRESS)

### Goal
Tag every second of video with **Timeline/Structure Lens** components.

### Schema Extensions Needed
```sql
video_segments:
  - id, video_id
  - segment_type (hook, context, payload, payoff, cta)
  - start_s, end_s
  - hook_type (scroll_stop, pattern_interrupt, question, story, promise)
  - focus_target (identity/ICP)
  - emotion_lever (relief, excitement, curiosity, FOMO)
  - created_at

segment_metadata:
  - segment_id
  - words_per_minute
  - sentiment_score
  - complexity_score
  - intended_outcome (awareness, engagement, conversion)
```

### UI Changes
**Filters to Add:**
- Segment Type: Hook | Context | Body | CTA
- Hook Type: Pain | Curiosity | Aspirational | Contrarian
- Emotion: Relief | Excitement | FOMO | Curiosity
- Duration Range: 0-15s (shorts) | 15-60s | 60s+

**Sort Options to Add:**
- Hook Strength Score
- Retention at 3s
- CTA Response Rate

---

## 📊 **Phase 3: Word-Level Timeline Analysis**

### Goal
Analyze transcript with word-level timestamps to understand pacing, emphasis, and speech patterns.

### Schema Extensions
```sql
video_words:
  - id, video_id, segment_id
  - word, start_s, end_s
  - speaker (for multi-speaker later)
  - sentence_id
  - pos (part of speech)
  - is_emphasis_word (caps, key terms)
  - is_question
  - is_list_marker
  - sentiment_score
  - speech_function (hook | proof | step | CTA)
  
word_analytics:
  - video_id
  - avg_words_per_minute
  - pause_count
  - emphasis_word_count
  - question_count
  - reading_grade_level
```

### Features
- **Pacing Analysis**: words_per_minute heatmap over time
- **Emphasis Detection**: Auto-highlight key words for captions
- **Question Density**: Track engagement-driving questions
- **Complexity Tracking**: Syllable count, grade level per segment

### UI Filters
- Words Per Minute: Fast (180+) | Medium (120-180) | Slow (<120)
- Has Questions: Yes | No
- Complexity: Simple | Medium | Technical
- Emphasis Words: High | Medium | Low

---

## 🎨 **Phase 4: Frame / Image Analysis**

### Goal
Sample frames every 0.5-1s and analyze visual composition.

### Schema Extensions
```sql
video_frames:
  - id, video_id, segment_id
  - frame_time_s
  - shot_type (close_up, medium, wide, screen_record)
  - camera_motion (static, slight, aggressive)
  - presence (face, full_body, hands, no_human)
  - objects_detected (json array)
  - text_on_screen (OCR)
  - brightness_level
  - color_temperature
  - visual_clutter_score (0-1)
  - is_pattern_interrupt
  - is_hook_frame
  - has_meme_element

frame_alignment:
  - frame_id, word_id
  - visual_support (reinforcing | neutral | distracting)
  - alignment_score
```

### Features
- **Pattern Interrupt Detection**: Big changes in color/zoom/location
- **Hook Frame Analysis**: Faces visible, eyes to camera, bold text
- **Visual-Verbal Alignment**: When you say X, does visual support it?
- **Meme Element Detection**: Reaction faces, overlay memes

### UI Filters
- Shot Type: Close-up | Medium | Wide | Screen Record
- Has Face: Yes | No
- Pattern Interrupts: High | Medium | Low | None
- Visual Clutter: Clean | Medium | Busy
- Meme Elements: Yes | No

### Sort Options
- Visual Engagement Score
- Pattern Interrupt Density
- Face-to-Camera Time %

---

## 📱 **Phase 5: Platform Check-Back Metrics**

### Goal
Track performance over time at multiple checkpoints after posting.

### Schema Extensions
```sql
platform_posts:
  - id, video_id, clip_id
  - platform (tiktok, instagram, youtube, etc.)
  - platform_post_id
  - posted_at
  - post_metadata (caption, hashtags, etc.)

post_checkbacks:
  - id, platform_post_id
  - checkback_h (1, 6, 24, 72, 168)
  - views, unique_viewers, impressions
  - avg_watch_time_s, avg_watch_pct
  - retention_curve (json)
  - likes, comments, shares, saves
  - profile_taps, link_clicks
  - like_rate, comment_rate, share_rate, save_rate, ctr
  - checked_at

post_comments:
  - id, platform_post_id
  - comment_text
  - created_at
  - sentiment_score
  - emotion_tags (json)
  - intent (question | praise | critique | spam)
  - theme_tags (json)
  - is_cta_response
  - cta_keyword

comment_analytics:
  - platform_post_id, checkback_h
  - avg_sentiment
  - top_positive_themes (json)
  - top_negative_themes (json)
  - top_questions (json)
  - cta_response_count_by_keyword (json)
```

### Features
- **Retention Drop Alignment**: Map drops to exact words + frames
- **Hook Quality vs Performance**: First 3s retention correlation
- **CTA Structure vs Conversion**: Keyword comment tracking
- **Visual Memes vs Shares**: Meme frame correlation with shares

### UI Features
**Filters:**
- Performance: Top 10% | Above Avg | Below Avg | Bottom 10%
- Retention: High (>70%) | Medium (40-70%) | Low (<40%)
- Engagement Rate: High | Medium | Low
- Has CTA Responses: Yes | No
- Posted Date Range: Last 7d | 30d | 90d | All Time

**Sort:**
- Views | Watch Time % | Engagement Rate
- Shares | Saves | Comments
- CTA Response Rate

---

## 🧠 **Phase 6: Psychology & FATE Model Tagging**

### Goal
Tag content with psychological levers: Focus, Authority, Tribe, Emotion.

### Schema Extensions
```sql
video_psychology:
  - video_id, segment_id
  - focus_type (hyper_specific_problem, narrow_audience, clear_promise)
  - focus_target (identity/persona)
  - authority_type (credentials, tried_it, proof)
  - authority_score (0-1)
  - tribe_signals (identity_calls, shared_enemy, in_jokes)
  - emotion_type (relief, excitement, curiosity, fomo)
  - emotion_intensity (0-1)

hook_analysis:
  - video_id
  - hook_type (contrarian, pain, aspirational, gap, absurd)
  - focus_score, authority_score, tribe_score, emotion_score
  - combined_fate_score
```

### UI Filters
- **Focus**: Hyper-Specific | Narrow Audience | Clear Promise
- **Authority**: Credentials | Proof | Experience
- **Tribe**: Identity Call | Shared Enemy | In-Jokes
- **Emotion**: Relief | Excitement | Curiosity | FOMO
- **FATE Score**: High (>0.7) | Medium (0.4-0.7) | Low (<0.4)

---

## 🎯 **Phase 7: CTA & Conversion Tracking**

### Schema Extensions
```sql
video_ctas:
  - id, video_id, segment_id
  - cta_type (conversion, engagement, open_loop, conversation)
  - cta_mechanic (comment_keyword, link_bio, dm_me, save_share)
  - cta_text
  - start_s, end_s
  - has_on_screen_text
  - has_eye_contact
  - keyword (for manychat style)

cta_performance:
  - cta_id, platform_post_id
  - response_count
  - response_rate (responses / views)
  - avg_response_time_h
  - conversion_count (for conversion CTAs)
```

### UI Filters
- CTA Type: Engagement | Conversion | Open Loop
- CTA Mechanic: Comment Keyword | Link | DM | Save
- Has Keyword: Yes | No
- Response Rate: High | Medium | Low

---

## 📈 **Phase 8: North Star Metrics Dashboard**

### Three Core Metrics
```
NSM #1: Weekly Engaged Reach
  = unique users who (comment + save + share + profile_tap + link_click)

NSM #2: Content Leverage Score
  = (comments + saves + shares + profile_taps) / posts_published

NSM #3: Warm Lead Flow
  = link_clicks + DM_starts + email_signups per week
```

### Dashboard Sections

**Overview:**
- NSM strip (current, % change, sparkline)
- Output vs Results chart (posts vs engaged reach)
- Platform split (stacked bars)
- Content type performance by hook_type, visual_type, cta_type
- Posting cadence heatmap

**Post Performance:**
- Retention curve with timeline heatmap
- Word + frame context at drops/peaks
- CTA effectiveness tracking
- Comment sentiment & themes
- Hook/visual diagnostics

**Insights Widget:**
- Pattern mining: "Hooks with [pattern] have +X% retention"
- Recommendations: "Use this hook pattern in 3 posts next week"
- Experiments: Auto-suggest A/B tests
- Schedule optimization: Best times per platform

---

## 🎨 **Phase 9: Clip Generation with Advanced Styling**

### Caption System
```sql
caption_styles:
  - id, name
  - font_family, font_weight, font_size
  - text_color, background_style
  - position (bottom, mid, top)
  - animation_style (fade, pop, typewriter, karaoke)
  - keyword_emphasis_enabled
  - emphasis_color, emphasis_size_multiplier

clip_captions:
  - clip_id, caption_style_id
  - enabled
  - custom_overrides (json)
```

### Headline Overlay System
```sql
clip_headlines:
  - clip_id
  - main_text, subtext
  - position (top_bar, bottom_bar, mid_left, mid_right)
  - font_family, font_size, text_color
  - background_style (pill, banner, transparent, blur)
  - show_duration (full_clip | timed_segments)
  - timed_segments (json: [{start_s, end_s, text}])
```

### UI Features
- **Caption Editor**: Live preview with styles
- **Headline Designer**: Drag-and-drop positioning
- **Keyword Emphasis**: Auto-highlight from transcript analysis
- **Multi-Segment Headlines**: Different text per time range

---

## 📅 **Phase 10: Smart Content Calendar**

### Features
- **AI Auto-Schedule**: Pick clips + suggest best days/times
- **Performance Overlays**: Color-coded by NSM contribution
- **Drag-Drop Rescheduling**: Update in real-time
- **Metadata AI**: Generate/regenerate title/caption/hashtags
- **Variant Management**: Save multiple AI versions for A/B tests

### Schema
```sql
posting_schedule:
  - id, clip_id
  - platform, scheduled_time
  - status (draft, scheduled, published, failed)
  - metadata_variant_id

metadata_variants:
  - id, clip_id
  - variant_type (title, caption, hashtags)
  - content
  - ai_generated
  - selected_for_platform
  - created_at
```

---

## 🧪 **Phase 11: Experimentation Framework**

### Features
- **A/B Test Creator**: Test hook patterns, CTA styles, visual templates
- **Test Tracking**: Compare variants across NSMs
- **Winner Detection**: Auto-flag winners after statistical significance
- **Pattern Library**: Save winning patterns for reuse

### Schema
```sql
experiments:
  - id, name, hypothesis
  - start_date, end_date
  - control_clip_ids (json), variant_clip_ids (json)
  - metric_focus (retention, engagement, ctr, etc.)
  - status (running, complete, cancelled)

experiment_results:
  - experiment_id
  - control_avg, variant_avg
  - statistical_significance
  - winner (control | variant | inconclusive)
  - insights (json)
```

---

## 🔄 **Implementation Phases**

### **Q1 2025: Core Analytics** 
- ✅ Phase 1: Foundation (DONE)
- 🚧 Phase 2: Timeline & Structure (30% complete)
- 🔜 Phase 3: Word-Level Analysis
- 🔜 Phase 5: Platform Checkbacks (basic)

### **Q2 2025: Intelligence Layer**
- Phase 4: Frame Analysis
- Phase 6: Psychology Tagging
- Phase 7: CTA Tracking
- Phase 8: NSM Dashboard (basic)

### **Q3 2025: Creation Tools**
- Phase 9: Advanced Clip Generation
- Phase 10: Smart Calendar
- Phase 8: NSM Dashboard (advanced insights)

### **Q4 2025: Optimization**
- Phase 11: Experimentation Framework
- ML Models: Retention prediction, Hook scoring
- Auto-optimization: Schedule, metadata, thumbnails

---

## 💻 **Current UI State (Phase 1 Complete)**

### Available Now
```
Video Library Filters:
├─ Search (file name/path)
├─ Source Type (local, gdrive, supabase)
├─ Media Type (video, image) ✨ NEW
├─ Duration Range (min/max seconds) ✨ NEW
├─ File Size Range (min/max bytes) ✨ NEW
├─ Has Thumbnail (yes/no) ✨ NEW
└─ Has Analysis (yes/no) ✨ NEW

Sort Options:
├─ Created Date (newest/oldest)
├─ File Name (A-Z, Z-A)
├─ File Size (largest/smallest) ✨ NEW
└─ Duration (longest/shortest) ✨ NEW

Pagination:
└─ 25, 50, 100, 250 per page
```

### Coming Next (Phase 2)
```
Filters:
├─ Segment Type (hook, body, CTA)
├─ Hook Type (pain, curiosity, etc.)
├─ Emotion (relief, excitement, FOMO)
└─ Performance Tier (top 10%, avg, bottom 10%)

Sort:
├─ Hook Strength Score
├─ Retention at 3s
└─ Engagement Rate
```

---

## 📊 **Testing Strategy**

### Backend Tests
- Unit: Each filter, sort, NSM calculation
- Integration: Pipeline flows (upload → analyze → metrics)
- Performance: 10k+ videos, complex queries <500ms
- Load: Concurrent uploads, analysis jobs

### Frontend Tests
- Component: Each filter UI, timeline editor
- Integration: Filter → API → results flow
- E2E: Upload → tag → schedule → analytics
- Visual: Caption/headline overlays, charts

### AI/Analytics Tests
- Golden datasets with known metrics
- Retention drop alignment accuracy
- Sentiment classification accuracy
- Pattern detection recall/precision

---

## 🎯 **Success Metrics**

### Platform Metrics (What We Track)
- Videos ingested per week
- Analysis completion rate
- Filter/sort usage patterns
- User engagement with insights

### Your Growth Metrics (North Stars)
- Weekly Engaged Reach trend
- Content Leverage Score improvement
- Warm Lead Flow growth
- Time from idea → published clip

---

## 🚀 **Next Immediate Actions**

1. **Frontend**: Add media type, duration, size filters to UI
2. **Backend**: Implement video segment table + basic tagging
3. **Analysis**: Build word-level timestamp extraction
4. **Testing**: Create test suite for current filters

---

This roadmap transforms your vision into concrete phases. We're at **Phase 1 complete**, with the foundation solid for building the full viral video intelligence platform!

**Want to prioritize a specific phase? Let me know!** 🎬
