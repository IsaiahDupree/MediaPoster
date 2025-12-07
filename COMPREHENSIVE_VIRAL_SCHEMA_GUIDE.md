# 🎬 Comprehensive Viral Video Analysis Schema

## Overview

This enhanced schema captures **EVERY dimension** of viral video analysis from the conversation, enabling you to:
- Analyze videos across 8+ lenses simultaneously
- Align words, frames, and platform metrics to the same timeline
- Detect patterns that consistently lead to virality
- Generate AI-powered insights and recommendations

---

## 📊 Schema Dimensions

### **1. Word-Level Timeline Analysis** (`video_words`)

**Purpose**: Analyze transcript at word-level granularity

**Captures**:
- Individual words with precise timestamps (start_s, end_s)
- Linguistic features (POS, emphasis, questions)
- Speech function (hook, proof, CTA, pain_point)
- Sentiment per word/phrase
- Pacing metrics (words per minute by segment)

**Example Use Cases**:
```sql
-- Find all emphasis words in hooks
SELECT word_text, start_s
FROM video_words
WHERE speech_function = 'hook'
  AND is_emphasis_word = true;

-- Calculate pacing in first 10 seconds
SELECT 
  COUNT(*) * 6.0 as words_per_minute
FROM video_words
WHERE video_id = ?
  AND start_s BETWEEN 0 AND 10;
```

**Enables**:
- ✅ Pacing analysis (fast vs slow segments)
- ✅ Emphasis detection for auto-captions
- ✅ Question density tracking
- ✅ Complexity scoring (reading grade level)

---

### **2. Frame-by-Frame Visual Analysis** (`video_frames`)

**Purpose**: Analyze visual composition at 0.5-1s intervals

**Captures**:
- **Shot types**: close_up, wide, screen_record, over_shoulder
- **Camera motion**: static, pan, zoom
- **Presence**: face visibility, eye contact, facial expressions
- **Objects**: detected items (laptop, phone, whiteboard)
- **Text overlays**: OCR text, emphasis level
- **Visual style**: brightness, color temperature, saturation
- **Pattern interrupts**: zoom punches, hard cuts, color shifts
- **Meme elements**: reaction faces, trending formats
- **Composition**: rule of thirds, visual clutter score

**Example Use Cases**:
```sql
-- Find hook frames with face + eye contact + text
SELECT frame_time_s
FROM video_frames
WHERE is_hook_frame = true
  AND eyes_to_camera = true
  AND has_text_overlay = true;

-- Detect pattern interrupts in first 10s
SELECT frame_time_s, pattern_interrupt_type
FROM video_frames
WHERE video_id = ?
  AND frame_time_s < 10
  AND is_pattern_interrupt = true;
```

**Enables**:
- ✅ Visual-verbal alignment analysis
- ✅ Pattern interrupt detection
- ✅ Hook frame selection for thumbnails
- ✅ Composition quality scoring

---

### **3. Audio & Voice Analysis** (`video_audio_analysis`)

**Purpose**: Analyze voice delivery and pacing

**Captures**:
- **Voice tone**: calm_teacher, hype_coach, rant, storyteller
- **Energy & pacing**: speaking pace, words per minute
- **Pauses**: count, duration, strategic silence
- **Emphasis moments**: volume changes, stressed words
- **Language complexity**: reading grade, jargon density
- **Questions**: rhetorical vs genuine, direct address count
- **Music**: background audio energy, beat sync

**Example Use Cases**:
```sql
-- Find high-energy segments
SELECT start_s, end_s, voice_tone
FROM video_audio_analysis
WHERE energy_level = 'high'
  AND speaking_pace = 'fast';

-- Analyze question density
SELECT 
  segment_id,
  question_count,
  rhetorical_question_count
FROM video_audio_analysis
WHERE video_id = ?
ORDER BY question_count DESC;
```

**Enables**:
- ✅ Pacing optimization recommendations
- ✅ Tone consistency analysis
- ✅ Strategic pause detection
- ✅ Music-beat sync verification

---

### **4. Enhanced Timeline Structure** (`video_segments`)

**Purpose**: Break video into narrative segments

**New Fields**:
- `hook_subtype`: pattern_interrupt, question, story, direct_promise
- `context_elements`: ICP, stakes, urgency markers
- `payload_type`: steps, demo, story_beats, layered_info
- `payoff_type`: before/after, final_tip, summary
- `pacing_score`, `clarity_score`, `value_density`: Quality metrics

**Segment Types**:
1. **Hook** (0-3s): Scroll-stop moment
2. **Context** (3-10s): Who it's for, what's at stake
3. **Payload** (10-45s): Value delivery
4. **Payoff**: Key takeaway
5. **CTA** (last 3-10s): Call to action + open loop

**Example Use Cases**:
```sql
-- Find videos with strong story-based hooks
SELECT v.file_name, vs.start_s, vs.end_s
FROM video_segments vs
JOIN videos v ON vs.video_id = v.id
WHERE vs.segment_type = 'hook'
  AND vs.hook_subtype = 'story'
  AND vs.clarity_score > 0.8;
```

---

### **5. Copy Layer Analysis** (`video_copy_elements`)

**Purpose**: Track all text elements (hooks, CTAs, overlays)

**Captures**:
- **Hook types**: contrarian, pain_callout, curiosity_gap, pattern_break
- **CTA types**: engagement, conversion, open_loop, manychat_keyword
- **CTA keywords**: For ManyChat automation ("PROMPT", "TECH")
- **Text styling**: fonts, colors, animations, emphasis
- **Positioning**: screen position, duration
- **Visual support**: Is CTA backed by on-screen text?

**Example Use Cases**:
```sql
-- Find high-performing pain hook patterns
SELECT text_content, hook_strength_score
FROM video_copy_elements
WHERE element_type = 'hook'
  AND hook_subtype = 'pain_callout'
  AND hook_strength_score > 0.8;

-- Analyze CTA keyword performance
SELECT 
  cta_keyword,
  AVG(cta_clarity) as avg_clarity,
  COUNT(*) as usage_count
FROM video_copy_elements
WHERE cta_subtype = 'manychat_keyword'
GROUP BY cta_keyword;
```

**Enables**:
- ✅ Hook formula library
- ✅ CTA effectiveness tracking
- ✅ ManyChat keyword optimization
- ✅ Text overlay best practices

---

### **6. Psychology & FATE Model** (Enhanced `video_analysis`)

**New Fields**:
- **FATE breakdowns**: Detailed components for each score
  - `focus_elements`: specificity, audience narrowness
  - `authority_elements`: credentials, proof types
  - `tribe_elements`: identity calls, shared enemies, in-jokes
  - `emotion_elements`: stakes, transformation promises
  
- **AIDA Model**: attention, interest, desire, action scores
- **Story structure**: problem_solution, before_after, hero_journey
- **Target ICP**: Specific audience persona
- **Language style**: plain_simple, gen_z_meme, technical_decoded
- **Humor level**: none, subtle, moderate, heavy

**Example Use Cases**:
```sql
-- Find videos with strong tribe appeal
SELECT 
  v.file_name,
  va.tribe_score,
  va.tribe_elements
FROM videos v
JOIN video_analysis va ON v.id = va.video_id
WHERE va.tribe_score > 0.7
  AND va.story_structure = 'us_vs_them';
```

---

### **7. Algorithm & Platform Intent** (`video_platform_intent`)

**Purpose**: Track optimization goals per video

**Captures**:
- **Primary metric**: views, saves, shares, comments, profile_taps
- **Funnel stage**: awareness, interest, consideration, conversion
- **Funnels into**: newsletter, course, community
- **Platform optimization**: Which platforms this video targets
- **Format specs**: aspect ratio, target duration

**Example Use Cases**:
```sql
-- Find save-optimized content
SELECT v.file_name, vpi.primary_metric
FROM videos v
JOIN video_platform_intent vpi ON v.id = vpi.video_id
WHERE vpi.primary_metric = 'saves'
  AND 'instagram_reels' = ANY(vpi.optimized_for_platforms::jsonb);
```

---

### **8. Offer & Monetization** (`video_offer_analysis`)

**Purpose**: Track monetization strategy per video

**Captures**:
- **Offer layer**: none, seed, soft_pitch, hard_pitch
- **Offer type**: course, SaaS, service, free_download
- **Proof mode**: story, dashboard, testimonial, demo
- **Credibility signals**: credentials, results, social proof
- **Lead magnet**: Type and delivery mechanism

**Example Use Cases**:
```sql
-- Find soft-pitch videos with high proof
SELECT 
  v.file_name,
  voa.offer_type,
  voa.proof_mode
FROM videos v
JOIN video_offer_analysis voa ON v.id = voa.video_id
WHERE voa.offer_layer = 'soft_pitch'
  AND voa.results_shown = true;
```

---

### **9. Retention Events** (`video_retention_events`)

**Purpose**: Track exact moments of retention changes

**Captures**:
- **Event types**: retention_drop, spike, replay, pause
- **Timing**: Exact second + percentage through video
- **Magnitude**: Delta change (-1 to +1)
- **Context**: Words spoken, frame shown, segment
- **Analysis**: Likely cause + recommendation

**Example Use Cases**:
```sql
-- Find common drop points across videos
SELECT 
  time_pct,
  COUNT(*) as occurrence_count,
  AVG(delta) as avg_drop_severity
FROM video_retention_events
WHERE event_type = 'retention_drop'
  AND severity IN ('major', 'critical')
GROUP BY time_pct
ORDER BY occurrence_count DESC;

-- Analyze retention drops aligned with frames
SELECT 
  vre.time_s,
  vre.delta,
  vf.shot_type,
  vf.visual_clutter_score,
  vre.likely_cause
FROM video_retention_events vre
JOIN video_frames vf ON vre.frame_id = vf.id
WHERE vre.event_type = 'retention_drop';
```

**Enables**:
- ✅ Precise drop point identification
- ✅ Pattern recognition (drops at jargon, messy visuals)
- ✅ Frame-word alignment analysis
- ✅ Automatic recommendations

---

### **10. Pattern Library** (`viral_patterns` + `video_pattern_matches`)

**Purpose**: Learn and catalog what works

**Captures**:
- **Pattern definition**: Combination of elements that work together
- **Performance stats**: Average FATE score, retention, engagement
- **Sample size**: How many videos match this pattern
- **Confidence**: Reliability score

**Example Pattern**:
```json
{
  "pattern_name": "Pain Hook + Screen Demo + Fast Pace",
  "components": {
    "hook_type": "pain",
    "visual_type": "screen_record",
    "pacing": "fast",
    "has_text_overlay": true,
    "duration_range": [20, 40]
  },
  "avg_fate_score": 0.82,
  "video_count": 15,
  "confidence_score": 0.91
}
```

**Example Use Cases**:
```sql
-- Find your top-performing patterns
SELECT 
  pattern_name,
  avg_fate_score,
  avg_watch_pct,
  video_count
FROM viral_patterns
WHERE video_count >= 5
  AND confidence_score > 0.7
ORDER BY avg_fate_score DESC;

-- Match new video to existing patterns
SELECT 
  vp.pattern_name,
  vpm.match_strength
FROM video_pattern_matches vpm
JOIN viral_patterns vp ON vpm.pattern_id = vp.id
WHERE vpm.video_id = ?
ORDER BY vpm.match_strength DESC;
```

---

## 🔄 How Everything Connects

### **Timeline Alignment Example**

At **t=3.2s**, a retention drop occurs:

```sql
-- Get complete context at 3.2 seconds
WITH context AS (
  SELECT
    -- Words spoken
    (SELECT jsonb_agg(word_text ORDER BY start_s)
     FROM video_words
     WHERE video_id = ? AND start_s BETWEEN 2.7 AND 3.7
    ) as words,
    
    -- Visual frame
    (SELECT row_to_json(vf)
     FROM video_frames vf
     WHERE video_id = ? 
     ORDER BY ABS(frame_time_s - 3.2)
     LIMIT 1
    ) as frame,
    
    -- Segment
    (SELECT segment_type
     FROM video_segments
     WHERE video_id = ?
       AND start_s <= 3.2 AND end_s >= 3.2
    ) as segment,
    
    -- Retention event
    (SELECT delta, likely_cause
     FROM video_retention_events
     WHERE video_id = ?
       AND time_s = 3.2
    ) as event
)
SELECT * FROM context;
```

**Result**:
```json
{
  "words": ["Notion", "second", "brain", "asynchronous"],
  "frame": {
    "shot_type": "screen_record",
    "visual_clutter_score": 0.82,
    "text_on_screen": "⚠️ TOO MANY TABS ⚠️",
    "face_visible": false
  },
  "segment": "context",
  "event": {
    "delta": -0.18,
    "likely_cause": "Switched to jargon + messy visual without face"
  }
}
```

---

## 📈 Power Queries

### **1. Find Your Best Hook Formula**
```sql
SELECT 
  vce.hook_subtype,
  vf.shot_type,
  vf.eyes_to_camera,
  va.emotion_type,
  AVG(va.hook_strength_score) as avg_strength,
  AVG(va.fate_combined_score) as avg_fate,
  COUNT(*) as video_count
FROM video_copy_elements vce
JOIN video_frames vf ON vce.video_id = vf.video_id 
  AND vf.frame_time_s < 3
JOIN video_analysis va ON vce.video_id = va.video_id
WHERE vce.element_type = 'hook'
GROUP BY vce.hook_subtype, vf.shot_type, vf.eyes_to_camera, va.emotion_type
HAVING COUNT(*) >= 3
ORDER BY avg_fate DESC;
```

### **2. CTA Performance by Style**
```sql
SELECT 
  vce.cta_subtype,
  vce.has_visual_support,
  vaa.voice_tone,
  AVG(vce.cta_clarity) as avg_clarity,
  -- Would join with platform metrics to get response rate
  COUNT(*) as usage_count
FROM video_copy_elements vce
JOIN video_audio_analysis vaa ON vce.video_id = vaa.video_id
WHERE vce.element_type = 'cta'
GROUP BY vce.cta_subtype, vce.has_visual_support, vaa.voice_tone
ORDER BY avg_clarity DESC;
```

### **3. Retention Drop Patterns**
```sql
SELECT 
  vf.shot_type,
  vf.face_visible,
  vaa.speaking_pace,
  AVG(vre.delta) as avg_drop,
  COUNT(*) as occurrence_count
FROM video_retention_events vre
JOIN video_frames vf ON vre.frame_id = vf.id
JOIN video_audio_analysis vaa ON vre.segment_id = vaa.segment_id
WHERE vre.event_type = 'retention_drop'
  AND vre.severity IN ('major', 'critical')
GROUP BY vf.shot_type, vf.face_visible, vaa.speaking_pace
ORDER BY occurrence_count DESC;
```

---

## 🎯 Implementation Roadmap

### **Phase 1: Core Tables** (Week 1)
- ✅ Run migration
- ✅ Create sample data
- ✅ Test basic queries

### **Phase 2: Word Analysis** (Week 2)
- Integrate Whisper transcription
- Parse timestamps
- Populate video_words table
- Build pacing calculator

### **Phase 3: Frame Analysis** (Week 3)
- Sample frames every 0.5-1s
- Run vision AI (GPT-4 Vision or similar)
- Detect faces, objects, text
- Calculate visual quality scores

### **Phase 4: Pattern Detection** (Week 4)
- Analyze existing videos
- Identify high-performing patterns
- Build pattern matching algorithm
- Create viral_patterns library

### **Phase 5: Insights Engine** (Ongoing)
- Align timeline data
- Generate retention insights
- Create recommendations
- Auto-suggest improvements

---

## 🚀 Quick Start

### Run the Migration:
```bash
cat Backend/migrations/add_comprehensive_viral_schema.sql | \
  docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres
```

### Verify Installation:
```sql
-- Check all new tables exist
SELECT tablename 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename LIKE '%video%'
ORDER BY tablename;
```

You should see:
- video_analysis (enhanced)
- video_audio_analysis ✨
- video_copy_elements ✨
- video_frames ✨
- video_offer_analysis ✨
- video_pattern_matches ✨
- video_platform_intent ✨
- video_retention_events ✨
- video_segments (enhanced)
- video_words ✨
- viral_patterns ✨

---

**This is the most comprehensive viral video analysis schema ever created! 🎬**

You can now analyze EVERY dimension of what makes content viral!
