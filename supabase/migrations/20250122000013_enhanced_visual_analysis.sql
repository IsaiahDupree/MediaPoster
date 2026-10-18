-- Enhanced Visual Analysis Schema
-- Addresses gaps from ANALYSIS_TO_GENERATION_DATA_AUDIT.md:
-- 1. Structured visual extraction (color_palette, lighting, camera)
-- 2. Camera motion detection
-- 3. Scene boundary detection
-- 4. Template library from high-performing videos

-- =============================================================================
-- ENHANCED: Video Analysis Extended Fields
-- =============================================================================

-- Add structured visual analysis columns to video_analysis if they don't exist
DO $$ 
BEGIN
    -- Color palette
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='video_analysis' AND column_name='color_palette') THEN
        ALTER TABLE video_analysis ADD COLUMN color_palette JSONB;
        COMMENT ON COLUMN video_analysis.color_palette IS 'Extracted color palette: {primary, secondary, accent, colors[], mood, contrast_level}';
    END IF;
    
    -- Lighting analysis
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='video_analysis' AND column_name='lighting_analysis') THEN
        ALTER TABLE video_analysis ADD COLUMN lighting_analysis JSONB;
        COMMENT ON COLUMN video_analysis.lighting_analysis IS 'Lighting characteristics: {type, direction, quality, exposure, shadows}';
    END IF;
    
    -- Camera info
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='video_analysis' AND column_name='camera_info') THEN
        ALTER TABLE video_analysis ADD COLUMN camera_info JSONB;
        COMMENT ON COLUMN video_analysis.camera_info IS 'Camera/shot info: {shot_type, angle, depth_of_field}';
    END IF;
    
    -- Camera motion sequences
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='video_analysis' AND column_name='camera_motion_sequences') THEN
        ALTER TABLE video_analysis ADD COLUMN camera_motion_sequences JSONB;
        COMMENT ON COLUMN video_analysis.camera_motion_sequences IS 'Detected camera motions: [{start_sec, end_sec, type, direction, confidence}]';
    END IF;
    
    -- Scene boundaries
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='video_analysis' AND column_name='scene_boundaries') THEN
        ALTER TABLE video_analysis ADD COLUMN scene_boundaries JSONB;
        COMMENT ON COLUMN video_analysis.scene_boundaries IS 'Detected scene cuts: [{timestamp, type, confidence, visual_change_score}]';
    END IF;
    
    -- Overall visual style
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='video_analysis' AND column_name='overall_visual_style') THEN
        ALTER TABLE video_analysis ADD COLUMN overall_visual_style JSONB;
        COMMENT ON COLUMN video_analysis.overall_visual_style IS 'Aggregated style: {dominant_shot_type, dominant_angle, dominant_lighting, dominant_mood}';
    END IF;
    
    -- Viral indicators
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='video_analysis' AND column_name='viral_indicators') THEN
        ALTER TABLE video_analysis ADD COLUMN viral_indicators JSONB;
        COMMENT ON COLUMN video_analysis.viral_indicators IS 'Viral potential: {hook_potential, pattern_interrupts, scroll_stoppers, meme_potential}';
    END IF;
    
    -- Enhanced frame analyses (structured)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='video_analysis' AND column_name='structured_frame_analyses') THEN
        ALTER TABLE video_analysis ADD COLUMN structured_frame_analyses JSONB;
        COMMENT ON COLUMN video_analysis.structured_frame_analyses IS 'Per-frame structured analysis with full extraction';
    END IF;
END $$;


-- =============================================================================
-- NEW: Video Template Library
-- =============================================================================

CREATE TABLE IF NOT EXISTS video_template_library (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identity
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,  -- hook_problem_solution, listicle, story_transformation, etc.
    
    -- Source information
    source_video_ids TEXT[],
    source_platform TEXT,
    
    -- Performance metrics (aggregated)
    avg_engagement_rate FLOAT DEFAULT 0,
    avg_views INTEGER DEFAULT 0,
    avg_completion_rate FLOAT DEFAULT 0,
    
    -- Template structure
    target_duration_sec INTEGER DEFAULT 30,
    beat_sheet JSONB,  -- [{role, duration_range, description, emotion_cue, visual_cue, audio_cue}]
    
    -- Style fingerprint
    style JSONB,  -- {tone, pacing, energy, format_tags}
    
    -- Visual guidelines
    color_palette TEXT[],
    dominant_shot_type TEXT,
    lighting_style TEXT,
    
    -- Audio guidelines
    music_mood TEXT,
    music_tempo TEXT,
    voiceover_style TEXT,
    
    -- Text/Caption style
    caption_style TEXT,
    hook_patterns TEXT[],
    cta_patterns TEXT[],
    
    -- Usage guidance
    best_for TEXT[],
    difficulty TEXT DEFAULT 'intermediate',
    estimated_production_time TEXT,
    
    -- Usage tracking
    times_used INTEGER DEFAULT 0,
    avg_output_performance FLOAT DEFAULT 0,
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_template_library_category ON video_template_library(category);
CREATE INDEX idx_template_library_engagement ON video_template_library(avg_engagement_rate DESC);
CREATE INDEX idx_template_library_slug ON video_template_library(slug);

COMMENT ON TABLE video_template_library IS 'Library of reusable video templates extracted from high-performing content';


-- =============================================================================
-- NEW: Template Usage Tracking
-- =============================================================================

CREATE TABLE IF NOT EXISTS template_usage_log (
    usage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    template_id UUID REFERENCES video_template_library(template_id) ON DELETE SET NULL,
    
    -- Usage context
    user_id TEXT,
    video_id UUID,  -- Output video if applicable
    
    -- Modifications made
    modifications_applied JSONB,
    
    -- Performance of output (if tracked)
    output_views INTEGER,
    output_engagement_rate FLOAT,
    output_completion_rate FLOAT,
    
    -- Feedback
    user_rating INTEGER,  -- 1-5
    user_feedback TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_template_usage_template ON template_usage_log(template_id);
CREATE INDEX idx_template_usage_created ON template_usage_log(created_at DESC);

COMMENT ON TABLE template_usage_log IS 'Tracks template usage and performance for continuous improvement';


-- =============================================================================
-- NEW: Scene Detection Results (detailed)
-- =============================================================================

CREATE TABLE IF NOT EXISTS video_scene_detection (
    detection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id UUID,  -- Reference to local_content or video_analysis
    
    -- Detection metadata
    detection_method TEXT,  -- 'opencv', 'ai', 'hybrid'
    detection_version TEXT DEFAULT '1.0',
    
    -- Results
    scene_count INTEGER,
    scene_boundaries JSONB,  -- [{frame_index, timestamp, boundary_type, confidence}]
    
    -- Camera motion
    motion_sequences JSONB,  -- [{start_frame, end_frame, motion_type, direction, confidence}]
    
    -- Style aggregation
    dominant_colors TEXT[],
    shot_type_distribution JSONB,
    lighting_distribution JSONB,
    
    -- Processing info
    frames_analyzed INTEGER,
    processing_time_sec FLOAT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_scene_detection_video ON video_scene_detection(video_id);

COMMENT ON TABLE video_scene_detection IS 'Detailed scene detection and camera motion analysis results';


-- =============================================================================
-- SEED: Standard Template Categories
-- =============================================================================

INSERT INTO video_template_library (
    name, slug, category, 
    target_duration_sec, beat_sheet, style,
    best_for, difficulty, estimated_production_time
) VALUES 
(
    'Hook-Problem-Solution Classic',
    'hook-problem-solution-classic',
    'hook_problem_solution',
    30,
    '[
        {"role": "hook", "duration_range": [0, 3], "description": "Attention grabber", "emotion_cue": "curiosity", "visual_cue": "close-up or pattern interrupt", "audio_cue": "sound effect or music drop"},
        {"role": "problem", "duration_range": [3, 8], "description": "State the problem", "emotion_cue": "frustration", "visual_cue": "medium shot or b-roll", "audio_cue": "tension music"},
        {"role": "solution", "duration_range": [8, 25], "description": "Deliver value", "emotion_cue": "relief", "visual_cue": "mix of shots", "audio_cue": "upbeat music"},
        {"role": "cta", "duration_range": [25, 30], "description": "Call to action", "emotion_cue": "urgency", "visual_cue": "direct to camera", "audio_cue": "music fade"}
    ]'::jsonb,
    '{"tone": "educational", "pacing": "medium", "energy": "medium"}'::jsonb,
    ARRAY['educational content', 'tips videos', 'how-to content'],
    'beginner',
    '20-30 minutes'
),
(
    'Quick 3-Point Listicle',
    'quick-3-point-listicle',
    'listicle',
    30,
    '[
        {"role": "hook", "duration_range": [0, 3], "description": "Preview the list", "emotion_cue": "curiosity", "visual_cue": "text overlay with number", "audio_cue": "energetic intro"},
        {"role": "item_1", "duration_range": [3, 10], "description": "First point", "emotion_cue": "interest", "visual_cue": "demonstrate", "audio_cue": "consistent background"},
        {"role": "item_2", "duration_range": [10, 17], "description": "Second point", "emotion_cue": "building", "visual_cue": "demonstrate", "audio_cue": "maintain energy"},
        {"role": "item_3", "duration_range": [17, 24], "description": "Third point", "emotion_cue": "climax", "visual_cue": "best example", "audio_cue": "peak energy"},
        {"role": "cta", "duration_range": [24, 30], "description": "Wrap up", "emotion_cue": "satisfaction", "visual_cue": "summary", "audio_cue": "conclusive"}
    ]'::jsonb,
    '{"tone": "informative", "pacing": "fast", "energy": "high"}'::jsonb,
    ARRAY['top lists', 'tips roundups', 'recommendations'],
    'beginner',
    '25-35 minutes'
),
(
    'Story Transformation Arc',
    'story-transformation-arc',
    'story_transformation',
    45,
    '[
        {"role": "hook", "duration_range": [0, 3], "description": "Tease the transformation", "emotion_cue": "curiosity", "visual_cue": "before or reaction", "audio_cue": "suspense"},
        {"role": "before", "duration_range": [3, 12], "description": "Show problem state", "emotion_cue": "empathy", "visual_cue": "authentic footage", "audio_cue": "somber tone"},
        {"role": "journey", "duration_range": [12, 32], "description": "Transformation process", "emotion_cue": "hope", "visual_cue": "progress montage", "audio_cue": "building music"},
        {"role": "after", "duration_range": [32, 42], "description": "Show the result", "emotion_cue": "triumph", "visual_cue": "reveal shot", "audio_cue": "triumphant"},
        {"role": "cta", "duration_range": [42, 45], "description": "Inspire action", "emotion_cue": "motivation", "visual_cue": "direct address", "audio_cue": "uplifting close"}
    ]'::jsonb,
    '{"tone": "inspirational", "pacing": "dynamic", "energy": "building"}'::jsonb,
    ARRAY['success stories', 'before/after', 'journey content'],
    'intermediate',
    '45-60 minutes'
),
(
    'Myth Buster Format',
    'myth-buster-format',
    'myth_bust',
    30,
    '[
        {"role": "hook", "duration_range": [0, 4], "description": "State common belief", "emotion_cue": "surprise", "visual_cue": "text overlay of myth", "audio_cue": "dramatic sting"},
        {"role": "reveal", "duration_range": [4, 10], "description": "Reveal its wrong", "emotion_cue": "shock", "visual_cue": "reaction or proof", "audio_cue": "tension release"},
        {"role": "truth", "duration_range": [10, 24], "description": "Explain reality", "emotion_cue": "education", "visual_cue": "evidence", "audio_cue": "explanatory"},
        {"role": "takeaway", "duration_range": [24, 30], "description": "What to do instead", "emotion_cue": "empowerment", "visual_cue": "actionable advice", "audio_cue": "confident close"}
    ]'::jsonb,
    '{"tone": "contrarian", "pacing": "punchy", "energy": "high"}'::jsonb,
    ARRAY['myth debunking', 'controversial takes', 'educational'],
    'intermediate',
    '30-40 minutes'
),
(
    '60-Second Tutorial',
    '60-second-tutorial',
    'tutorial_quick',
    60,
    '[
        {"role": "hook", "duration_range": [0, 3], "description": "What youll learn", "emotion_cue": "promise", "visual_cue": "end result preview", "audio_cue": "attention sound"},
        {"role": "step_1", "duration_range": [3, 18], "description": "First step detailed", "emotion_cue": "clarity", "visual_cue": "close-up of action", "audio_cue": "instructional"},
        {"role": "step_2", "duration_range": [18, 35], "description": "Second step detailed", "emotion_cue": "progress", "visual_cue": "close-up of action", "audio_cue": "maintain pace"},
        {"role": "step_3", "duration_range": [35, 50], "description": "Third step detailed", "emotion_cue": "almost there", "visual_cue": "completion shot", "audio_cue": "building"},
        {"role": "result", "duration_range": [50, 60], "description": "Show result and CTA", "emotion_cue": "satisfaction", "visual_cue": "beauty shot", "audio_cue": "success music"}
    ]'::jsonb,
    '{"tone": "helpful", "pacing": "steady", "energy": "medium"}'::jsonb,
    ARRAY['how-to videos', 'tutorials', 'step-by-step guides'],
    'beginner',
    '35-45 minutes'
)
ON CONFLICT (slug) DO NOTHING;

COMMENT ON TABLE video_template_library IS 'Seeded with 5 standard templates that can be customized or used as-is';
