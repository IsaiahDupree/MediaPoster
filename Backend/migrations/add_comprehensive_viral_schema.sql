-- COMPREHENSIVE VIRAL VIDEO ANALYSIS SCHEMA
-- Based on complete viral video breakdown framework
-- Includes: Timeline, Psychology (FATE), Visual, Audio, Copy, Platform metrics

-- =============================================================================
-- 1. WORD-LEVEL TIMELINE ANALYSIS
-- =============================================================================

CREATE TABLE IF NOT EXISTS video_words (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  segment_id UUID REFERENCES video_segments(id) ON DELETE CASCADE,
  
  -- Word Data
  word_index INTEGER NOT NULL,  -- Position in transcript
  word_text TEXT NOT NULL,
  start_s NUMERIC(8,3) NOT NULL,
  end_s NUMERIC(8,3) NOT NULL,
  
  -- Structure
  sentence_id INTEGER,
  paragraph_id INTEGER,
  speaker TEXT DEFAULT 'primary',  -- For future multi-speaker
  
  -- Linguistic Features
  part_of_speech TEXT,  -- noun, verb, adjective, etc.
  is_emphasis_word BOOLEAN DEFAULT false,  -- "STOP", "NEVER", "SECRET", numbers
  is_question BOOLEAN DEFAULT false,
  is_list_marker BOOLEAN DEFAULT false,  -- "first", "second", "third"
  syllable_count INTEGER,
  
  -- Function/Intent
  speech_function TEXT CHECK (speech_function IN (
    'hook', 'proof', 'step', 'metaphor', 'cta', 'future_promise', 
    'pain_point', 'solution', 'transition'
  )),
  
  -- Sentiment (per word/phrase)
  sentiment_score NUMERIC(3,2) CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
  emotion_tag TEXT,  -- curiosity, frustration, hope, excitement
  
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes for word-level analysis
CREATE INDEX idx_video_words_video_id ON video_words(video_id);
CREATE INDEX idx_video_words_segment_id ON video_words(segment_id);
CREATE INDEX idx_video_words_timeline ON video_words(video_id, start_s);
CREATE INDEX idx_video_words_emphasis ON video_words(is_emphasis_word) WHERE is_emphasis_word = true;
CREATE INDEX idx_video_words_function ON video_words(speech_function);

-- =============================================================================
-- 2. FRAME / IMAGE ANALYSIS
-- =============================================================================

CREATE TABLE IF NOT EXISTS video_frames (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  segment_id UUID REFERENCES video_segments(id) ON DELETE SET NULL,
  
  -- Frame Info
  frame_time_s NUMERIC(8,2) NOT NULL,
  frame_number INTEGER,
  
  -- Shot Type & Camera
  shot_type TEXT CHECK (shot_type IN (
    'close_up', 'medium', 'wide', 'screen_record', 
    'over_shoulder', 'pov', 'aerial'
  )),
  camera_motion TEXT CHECK (camera_motion IN ('static', 'slight', 'aggressive', 'pan', 'zoom')),
  
  -- Presence & Subjects
  presence TEXT CHECK (presence IN (
    'face', 'full_body', 'hands_only', 'no_human', 'multiple_people'
  )),
  face_visible BOOLEAN DEFAULT false,
  eyes_to_camera BOOLEAN DEFAULT false,
  facial_expression TEXT,  -- smile, serious, surprise, thinking
  
  -- Objects & Environment
  objects_detected JSONB,  -- ["phone", "laptop", "whiteboard"]
  scene_type TEXT,  -- office, outdoors, studio, home
  
  -- Text & Graphics
  text_on_screen TEXT,  -- OCR extracted text
  has_text_overlay BOOLEAN DEFAULT false,
  text_emphasis_level TEXT CHECK (text_emphasis_level IN ('none', 'subtle', 'moderate', 'bold')),
  
  -- Visual Style
  brightness_level TEXT CHECK (brightness_level IN ('dark', 'normal', 'bright', 'overexposed')),
  color_temperature TEXT CHECK (color_temperature IN ('cool', 'neutral', 'warm')),
  color_saturation TEXT CHECK (color_saturation IN ('desaturated', 'normal', 'vibrant', 'hyper')),
  visual_clutter_score NUMERIC(3,2) CHECK (visual_clutter_score >= 0 AND visual_clutter_score <= 1),
  
  -- Pattern Interrupts & Hooks
  is_pattern_interrupt BOOLEAN DEFAULT false,
  pattern_interrupt_type TEXT,  -- zoom_punch, hard_cut, color_shift, overlay_appear
  is_hook_frame BOOLEAN DEFAULT false,  -- Suitable for first 3 seconds
  
  -- Meme & Cultural Elements
  has_meme_element BOOLEAN DEFAULT false,
  meme_type TEXT,  -- reaction_face, overlay_meme, cultural_reference, trending_format
  
  -- Brand Elements
  logo_visible BOOLEAN DEFAULT false,
  logo_type TEXT,  -- personal_brand, product, sponsor
  
  -- Quality Metrics
  sharpness_score NUMERIC(3,2),
  composition_score NUMERIC(3,2),  -- Rule of thirds, leading lines, etc.
  
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_video_frames_video_id ON video_frames(video_id);
CREATE INDEX idx_video_frames_time ON video_frames(video_id, frame_time_s);
CREATE INDEX idx_video_frames_hook ON video_frames(is_hook_frame) WHERE is_hook_frame = true;
CREATE INDEX idx_video_frames_pattern ON video_frames(is_pattern_interrupt) WHERE is_pattern_interrupt = true;
CREATE INDEX idx_video_frames_shot_type ON video_frames(shot_type);

-- =============================================================================
-- 3. AUDIO & VOICE ANALYSIS
-- =============================================================================

CREATE TABLE IF NOT EXISTS video_audio_analysis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  segment_id UUID REFERENCES video_segments(id) ON DELETE CASCADE,
  
  -- Time Range
  start_s NUMERIC(8,2),
  end_s NUMERIC(8,2),
  
  -- Voice Characteristics
  voice_tone TEXT CHECK (voice_tone IN (
    'calm_teacher', 'hype_coach', 'rant', 'confessional', 
    'storyteller', 'technical', 'casual_friend'
  )),
  energy_level TEXT CHECK (energy_level IN ('low', 'medium', 'high', 'variable')),
  speaking_pace TEXT CHECK (speaking_pace IN ('slow', 'medium', 'fast', 'rapid_fire')),
  
  -- Pacing Metrics
  words_per_minute NUMERIC(6,2),
  pause_count INTEGER,
  avg_pause_duration_ms INTEGER,
  longest_pause_ms INTEGER,
  
  -- Emphasis & Delivery
  emphasis_moments JSONB,  -- [{time_s: 5.2, word: "NEVER", intensity: 0.9}]
  volume_variance TEXT CHECK (volume_variance IN ('monotone', 'moderate', 'dynamic')),
  
  -- Language Style
  language_complexity TEXT CHECK (language_complexity IN (
    'simple', 'conversational', 'technical', 'academic', 'slang_heavy'
  )),
  reading_grade_level NUMERIC(3,1),  -- Flesch-Kincaid
  jargon_density NUMERIC(3,2),  -- % of technical/specialized terms
  
  -- Questions & Hooks
  question_count INTEGER DEFAULT 0,
  rhetorical_question_count INTEGER DEFAULT 0,
  direct_address_count INTEGER DEFAULT 0,  -- "You", "Your"
  
  -- Music & Background Audio
  has_background_music BOOLEAN DEFAULT false,
  music_energy TEXT CHECK (music_energy IN ('none', 'ambient', 'chill', 'moderate', 'high')),
  music_genre TEXT,
  beat_synced_to_cuts BOOLEAN DEFAULT false,
  silence_moments JSONB,  -- Strategic silence for emphasis
  
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_audio_analysis_video_id ON video_audio_analysis(video_id);
CREATE INDEX idx_audio_analysis_segment_id ON video_audio_analysis(segment_id);
CREATE INDEX idx_audio_analysis_tone ON video_audio_analysis(voice_tone);

-- =============================================================================
-- 4. ENHANCED VIDEO SEGMENTS (Timeline Structure)
-- =============================================================================

-- Add new columns to existing video_segments table
ALTER TABLE video_segments 
  ADD COLUMN IF NOT EXISTS hook_subtype TEXT CHECK (hook_subtype IN (
    'pattern_interrupt_visual', 'pattern_interrupt_line', 'question', 
    'story', 'direct_promise', 'contrarian', 'gap', 'absurd'
  )),
  ADD COLUMN IF NOT EXISTS context_elements JSONB,  -- {icp: "...", stake: "...", urgency: "..."}
  ADD COLUMN IF NOT EXISTS payload_type TEXT CHECK (payload_type IN (
    'steps_framework', 'demonstration', 'story_beats', 'layered_info', 'comparison'
  )),
  ADD COLUMN IF NOT EXISTS payoff_type TEXT CHECK (payoff_type IN (
    'before_after', 'final_tip', 'hidden_rule', 'summary_punchy'
  )),
  ADD COLUMN IF NOT EXISTS pacing_score NUMERIC(3,2),  -- How well-paced (0-1)
  ADD COLUMN IF NOT EXISTS clarity_score NUMERIC(3,2),  -- How clear (0-1)
  ADD COLUMN IF NOT EXISTS value_density NUMERIC(3,2);  -- Value per second (0-1)

-- =============================================================================
-- 5. COPY LAYER (Hooks, CTAs, On-Screen Text)
-- =============================================================================

CREATE TABLE IF NOT EXISTS video_copy_elements (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  segment_id UUID REFERENCES video_segments(id) ON DELETE SET NULL,
  
  -- Element Type
  element_type TEXT CHECK (element_type IN ('hook', 'cta', 'on_screen_text', 'caption', 'title')) NOT NULL,
  
  -- Timing
  appears_at_s NUMERIC(8,2),
  disappears_at_s NUMERIC(8,2),
  duration_s NUMERIC(6,2),
  
  -- Content
  text_content TEXT NOT NULL,
  text_length INTEGER,
  
  -- Hook Specific
  hook_subtype TEXT CHECK (hook_subtype IN (
    'contrarian', 'pain_callout', 'aspirational', 'curiosity_gap', 
    'pattern_break', 'question', 'story_tease', 'direct_promise'
  )),
  hook_strength_score NUMERIC(3,2),
  
  -- CTA Specific
  cta_subtype TEXT CHECK (cta_subtype IN (
    'conversion', 'engagement', 'open_loop', 'conversation', 
    'manychat_keyword', 'link_in_bio', 'dm_me', 'save_share'
  )),
  cta_keyword TEXT,  -- For ManyChat style: "PROMPT", "TECH"
  cta_clarity NUMERIC(3,2),
  has_visual_support BOOLEAN DEFAULT false,  -- On-screen text backing it up
  
  -- Style & Formatting
  font_style TEXT,
  text_color TEXT,
  background_style TEXT,
  animation_type TEXT,
  emphasis_level TEXT CHECK (emphasis_level IN ('subtle', 'moderate', 'bold', 'extreme')),
  
  -- Positioning
  screen_position TEXT CHECK (screen_position IN (
    'top', 'middle', 'bottom', 'top_left', 'top_right', 
    'bottom_left', 'bottom_right', 'center', 'following_subject'
  )),
  
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_copy_elements_video_id ON video_copy_elements(video_id);
CREATE INDEX idx_copy_elements_type ON video_copy_elements(element_type);
CREATE INDEX idx_copy_elements_hook ON video_copy_elements(hook_subtype);
CREATE INDEX idx_copy_elements_cta ON video_copy_elements(cta_subtype);

-- =============================================================================
-- 6. PSYCHOLOGY & FATE MODEL (Enhanced)
-- =============================================================================

ALTER TABLE video_analysis
  -- Add more granular FATE breakdowns
  ADD COLUMN IF NOT EXISTS focus_elements JSONB,  -- {specificity: 0.9, audience_narrow: true, single_promise: true}
  ADD COLUMN IF NOT EXISTS authority_elements JSONB,  -- {credentials: true, proof_type: "dashboard", experience_years: 15}
  ADD COLUMN IF NOT EXISTS tribe_elements JSONB,  -- {identity_call: true, shared_enemy: "...", in_jokes: [...]}
  ADD COLUMN IF NOT EXISTS emotion_elements JSONB,  -- {stakes: "...", transformation: "..."}
  
  -- AIDA Model
  ADD COLUMN IF NOT EXISTS attention_score NUMERIC(3,2),  -- First 3s effectiveness
  ADD COLUMN IF NOT EXISTS interest_score NUMERIC(3,2),   -- Maintains curiosity
  ADD COLUMN IF NOT EXISTS desire_score NUMERIC(3,2),     -- Builds want
  ADD COLUMN IF NOT EXISTS action_score NUMERIC(3,2),     -- CTA effectiveness
  
  -- Pattern Recognition
  ADD COLUMN IF NOT EXISTS story_structure TEXT CHECK (story_structure IN (
    'problem_solution', 'before_after', 'hero_journey', 'comparison', 
    'reveal', 'tutorial', 'case_study', 'rant', 'listicle'
  )),
  ADD COLUMN IF NOT EXISTS pacing_overall TEXT CHECK (pacing_overall IN ('fast', 'medium', 'slow', 'variable')),
  
  -- Target Audience
  ADD COLUMN IF NOT EXISTS target_icp TEXT,  -- "solopreneur", "creator", "engineer"
  ADD COLUMN IF NOT EXISTS identity_specificity NUMERIC(3,2),
  
  -- Language & Tone
  ADD COLUMN IF NOT EXISTS language_style TEXT CHECK (language_style IN (
    'plain_simple', 'conversational', 'technical_decoded', 
    'gen_z_meme', 'professional', 'academic'
  )),
  ADD COLUMN IF NOT EXISTS humor_level TEXT CHECK (humor_level IN ('none', 'subtle', 'moderate', 'heavy'));

-- =============================================================================
-- 7. ALGORITHM & PLATFORM METRICS
-- =============================================================================

CREATE TABLE IF NOT EXISTS video_platform_intent (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  
  -- Intended Metrics (What you're optimizing for)
  primary_metric TEXT CHECK (primary_metric IN (
    'views', 'watch_time', 'saves', 'shares', 'comments', 
    'profile_taps', 'clicks', 'followers'
  )),
  secondary_metric TEXT,
  
  -- Funnel Intent
  funnel_stage TEXT CHECK (funnel_stage IN (
    'awareness', 'interest', 'consideration', 'conversion', 'retention'
  )),
  funnels_into TEXT,  -- newsletter, course, app, community
  
  -- Platform Optimization
  optimized_for_platforms JSONB,  -- ["tiktok", "instagram_reels", "youtube_shorts"]
  aspect_ratio TEXT,  -- "9:16", "1:1", "16:9"
  target_duration_s INTEGER,
  
  created_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- 8. OFFER & MONETIZATION LAYER
-- =============================================================================

CREATE TABLE IF NOT EXISTS video_offer_analysis (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  
  -- Offer Strategy
  offer_layer TEXT CHECK (offer_layer IN ('none', 'seed', 'soft_pitch', 'hard_pitch', 'proof_stack')),
  offer_type TEXT CHECK (offer_type IN (
    'course', 'saas', 'automation_service', 'free_download', 
    'consultation', 'community', 'physical_product', 'affiliate'
  )),
  offer_name TEXT,
  
  -- Proof Mode
  proof_mode TEXT CHECK (proof_mode IN (
    'story', 'dashboard', 'testimonial', 'screen_record', 
    'before_after', 'case_study', 'demo'
  )),
  
  -- Credibility Signals
  credentials_mentioned BOOLEAN DEFAULT false,
  results_shown BOOLEAN DEFAULT false,
  social_proof_type TEXT,  -- follower_count, client_results, awards
  
  -- Lead Magnet Strategy
  has_lead_magnet BOOLEAN DEFAULT false,
  lead_magnet_type TEXT,  -- template, checklist, guide, tool, mini_course
  delivery_mechanism TEXT,  -- comment_keyword, link_in_bio, dm, landing_page
  
  created_at TIMESTAMPTZ DEFAULT now()
);

-- =============================================================================
-- 9. RETENTION & ENGAGEMENT EVENTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS video_retention_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  
  -- Event Type
  event_type TEXT CHECK (event_type IN (
    'retention_drop', 'retention_spike', 'replay_moment', 
    'skip_forward', 'skip_back', 'pause_moment'
  )) NOT NULL,
  
  -- Timing
  time_s NUMERIC(8,2) NOT NULL,
  time_pct NUMERIC(5,2),  -- % through video
  
  -- Magnitude
  delta NUMERIC(5,4),  -- Change in retention (-1 to +1)
  severity TEXT CHECK (severity IN ('minor', 'moderate', 'major', 'critical')),
  
  -- Context (from aligned data)
  words_at_moment JSONB,  -- Words spoken around this time
  frame_id UUID REFERENCES video_frames(id),
  segment_id UUID REFERENCES video_segments(id),
  
  -- Analysis
  likely_cause TEXT,  -- From pattern matching
  recommendation TEXT,  -- How to fix
  
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_retention_events_video_id ON video_retention_events(video_id);
CREATE INDEX idx_retention_events_type ON video_retention_events(event_type);
CREATE INDEX idx_retention_events_time ON video_retention_events(video_id, time_s);

-- =============================================================================
-- 10. PATTERN ANALYSIS & INSIGHTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS viral_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  
  -- Pattern Definition
  pattern_name TEXT NOT NULL,
  pattern_type TEXT CHECK (pattern_type IN (
    'hook_formula', 'content_structure', 'visual_style', 
    'cta_strategy', 'retention_driver'
  )),
  
  -- Pattern Components
  components JSONB NOT NULL,  -- What makes this pattern
  /*
    Example:
    {
      "hook_type": "pain",
      "visual_type": "talking_head",
      "emotion": "relief",
      "has_text_overlay": true,
      "duration_range": [15, 30]
    }
  */
  
  -- Performance Stats
  avg_fate_score NUMERIC(3,2),
  avg_retention_3s NUMERIC(3,2),
  avg_watch_pct NUMERIC(3,2),
  avg_engagement_rate NUMERIC(3,2),
  
  -- Sample Size
  video_count INTEGER DEFAULT 0,
  last_updated TIMESTAMPTZ DEFAULT now(),
  
  -- Confidence
  confidence_score NUMERIC(3,2),  -- How reliable is this pattern
  
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Link videos to patterns
CREATE TABLE IF NOT EXISTS video_pattern_matches (
  video_id UUID REFERENCES videos(id) ON DELETE CASCADE,
  pattern_id UUID REFERENCES viral_patterns(id) ON DELETE CASCADE,
  match_strength NUMERIC(3,2),  -- How well video matches pattern (0-1)
  PRIMARY KEY (video_id, pattern_id)
);

-- =============================================================================
-- VIEWS FOR EASY QUERYING
-- =============================================================================

-- Complete video analysis view
CREATE OR REPLACE VIEW videos_complete_analysis AS
SELECT 
  v.*,
  va.*,
  vpi.primary_metric,
  vpi.funnel_stage,
  voa.offer_layer,
  voa.offer_type,
  COUNT(DISTINCT vw.id) as total_words,
  COUNT(DISTINCT vf.id) as total_frames,
  COUNT(DISTINCT vs.id) as total_segments,
  COUNT(DISTINCT vre.id) FILTER (WHERE vre.event_type = 'retention_drop') as retention_drops,
  COUNT(DISTINCT vce.id) FILTER (WHERE vce.element_type = 'cta') as cta_count
FROM videos v
LEFT JOIN video_analysis va ON v.id = va.video_id
LEFT JOIN video_platform_intent vpi ON v.id = vpi.video_id
LEFT JOIN video_offer_analysis voa ON v.id = voa.video_id
LEFT JOIN video_words vw ON v.id = vw.video_id
LEFT JOIN video_frames vf ON v.id = vf.video_id
LEFT JOIN video_segments vs ON v.id = vs.video_id
LEFT JOIN video_retention_events vre ON v.id = vre.video_id
LEFT JOIN video_copy_elements vce ON v.id = vce.video_id
GROUP BY v.id, va.id, vpi.id, voa.id;

-- High-performing patterns view
CREATE OR REPLACE VIEW top_viral_patterns AS
SELECT 
  vp.*,
  STRING_AGG(v.file_name, ', ') as example_videos
FROM viral_patterns vp
LEFT JOIN video_pattern_matches vpm ON vp.id = vpm.pattern_id
LEFT JOIN videos v ON vpm.video_id = v.id
WHERE vp.avg_fate_score > 0.7
  AND vp.video_count >= 3
GROUP BY vp.id
ORDER BY vp.avg_fate_score DESC;

-- =============================================================================
-- SUCCESS MESSAGE
-- =============================================================================

DO $$
BEGIN
    RAISE NOTICE '╔════════════════════════════════════════════════╗';
    RAISE NOTICE '║  COMPREHENSIVE VIRAL SCHEMA CREATED! 🎬         ║';
    RAISE NOTICE '╚════════════════════════════════════════════════╝';
    RAISE NOTICE '';
    RAISE NOTICE 'New Tables Created:';
    RAISE NOTICE '  ✓ video_words (word-level timestamps)';
    RAISE NOTICE '  ✓ video_frames (frame-by-frame analysis)';
    RAISE NOTICE '  ✓ video_audio_analysis (voice & pacing)';
    RAISE NOTICE '  ✓ video_copy_elements (hooks, CTAs, text)';
    RAISE NOTICE '  ✓ video_platform_intent (algorithm optimization)';
    RAISE NOTICE '  ✓ video_offer_analysis (monetization)';
    RAISE NOTICE '  ✓ video_retention_events (drops & spikes)';
    RAISE NOTICE '  ✓ viral_patterns (pattern library)';
    RAISE NOTICE '';
    RAISE NOTICE 'Enhanced Tables:';
    RAISE NOTICE '  ✓ video_analysis (FATE + AIDA expanded)';
    RAISE NOTICE '  ✓ video_segments (timeline structure enhanced)';
    RAISE NOTICE '';
    RAISE NOTICE 'Ready for comprehensive viral analysis!';
END $$;
