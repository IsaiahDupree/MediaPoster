-- ============================================================================
-- AI MEDIA GENERATIONS - ENHANCED SCHEMA
-- ============================================================================
-- Tracks AI-generated media (video, images, audio) aligned with media library
-- Links to videos table for unified content management
-- ============================================================================

-- Add columns to existing ai_video_generations if they don't exist
DO $$ 
BEGIN
    -- AI-generated title and description
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ai_video_generations' AND column_name = 'ai_title') THEN
        ALTER TABLE ai_video_generations ADD COLUMN ai_title TEXT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ai_video_generations' AND column_name = 'ai_description') THEN
        ALTER TABLE ai_video_generations ADD COLUMN ai_description TEXT;
    END IF;
    
    -- Style and camera motion tracking
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ai_video_generations' AND column_name = 'style_preset') THEN
        ALTER TABLE ai_video_generations ADD COLUMN style_preset TEXT;
    END IF;
    
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ai_video_generations' AND column_name = 'camera_motion') THEN
        ALTER TABLE ai_video_generations ADD COLUMN camera_motion TEXT;
    END IF;
    
    -- Character references
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ai_video_generations' AND column_name = 'character_ids') THEN
        ALTER TABLE ai_video_generations ADD COLUMN character_ids UUID[];
    END IF;
    
    -- Enhanced prompt (with style/motion keywords applied)
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ai_video_generations' AND column_name = 'enhanced_prompt') THEN
        ALTER TABLE ai_video_generations ADD COLUMN enhanced_prompt TEXT;
    END IF;
    
    -- Link to videos table for unified library
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ai_video_generations' AND column_name = 'video_id') THEN
        ALTER TABLE ai_video_generations ADD COLUMN video_id UUID REFERENCES videos(id) ON DELETE SET NULL;
    END IF;
    
    -- Cost tracking
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ai_video_generations' AND column_name = 'credits_used') THEN
        ALTER TABLE ai_video_generations ADD COLUMN credits_used DECIMAL(10, 2);
    END IF;
    
    -- User ID for multi-user support
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name = 'ai_video_generations' AND column_name = 'user_id') THEN
        ALTER TABLE ai_video_generations ADD COLUMN user_id UUID;
    END IF;
END $$;

-- ============================================================================
-- AI CHARACTERS TABLE
-- ============================================================================
-- Stores character definitions for consistent character appearance across videos

CREATE TABLE IF NOT EXISTS ai_characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    avatar_emoji TEXT DEFAULT '👤',
    reference_image_url TEXT,
    
    -- Attributes
    attributes JSONB DEFAULT '{}',
    -- Expected structure:
    -- {
    --   "gender": "female",
    --   "age": "25",
    --   "hairColor": "red",
    --   "hairStyle": "long wavy",
    --   "eyeColor": "green",
    --   "bodyType": "athletic",
    --   "clothing": "casual streetwear",
    --   "distinguishingFeatures": "freckles"
    -- }
    
    -- Usage tracking
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_characters_user ON ai_characters(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_characters_usage ON ai_characters(usage_count DESC);

-- ============================================================================
-- AI STYLE PRESETS TABLE (for custom user presets)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_style_presets (
    id TEXT PRIMARY KEY, -- e.g., 'cinematic', 'anime', or custom UUID
    user_id UUID, -- NULL = system preset, UUID = user custom preset
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    keywords TEXT NOT NULL, -- comma-separated keywords to append to prompt
    color_gradient TEXT, -- tailwind gradient class
    category TEXT DEFAULT 'general', -- general, cinematic, animated, artistic
    is_system BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_style_presets_user ON ai_style_presets(user_id);
CREATE INDEX IF NOT EXISTS idx_ai_style_presets_category ON ai_style_presets(category);

-- Insert system style presets
INSERT INTO ai_style_presets (id, name, description, icon, keywords, color_gradient, category, is_system) VALUES
    ('cinematic', 'Cinematic', 'Film-like visuals with dramatic lighting', '🎬', '35mm film, shallow depth of field, cinematic lighting, movie quality', 'from-amber-500 to-orange-600', 'cinematic', TRUE),
    ('photorealistic', 'Photorealistic', 'Ultra-realistic, lifelike footage', '📷', '8K, photorealistic, natural lighting, hyper-detailed', 'from-gray-500 to-slate-600', 'general', TRUE),
    ('anime', 'Anime', 'Japanese animation style', '🎨', 'anime style, hand-drawn, vibrant colors, cel-shaded', 'from-pink-500 to-rose-600', 'animated', TRUE),
    ('cyberpunk', 'Cyberpunk', 'Futuristic neon aesthetics', '🌃', 'cyberpunk, neon lights, rain, dystopian, holographic', 'from-cyan-500 to-blue-600', 'artistic', TRUE),
    ('film_noir', 'Film Noir', 'Classic black-and-white dramatic style', '🎩', 'black and white, high contrast, dramatic shadows, noir', 'from-zinc-600 to-zinc-800', 'cinematic', TRUE),
    ('dreamy', 'Dreamy', 'Soft, ethereal visuals', '☁️', 'soft focus, pastel colors, ethereal glow, dreamy atmosphere', 'from-purple-400 to-pink-400', 'artistic', TRUE),
    ('stop_motion', 'Stop Motion', 'Frame-by-frame animation look', '🎭', 'stop motion, claymation, handcrafted, tactile textures', 'from-yellow-500 to-amber-600', 'animated', TRUE),
    ('vintage', 'Vintage', 'Retro film aesthetics', '📼', 'VHS, film grain, 70s aesthetic, faded colors, retro', 'from-orange-400 to-red-500', 'artistic', TRUE),
    ('surreal', 'Surreal', 'Abstract, dreamlike imagery', '🌀', 'surreal, Salvador Dali, impossible geometry, dreamscape', 'from-violet-500 to-purple-600', 'artistic', TRUE),
    ('documentary', 'Documentary', 'Raw, authentic footage style', '📹', 'documentary style, handheld, natural, unscripted feel', 'from-emerald-500 to-green-600', 'cinematic', TRUE)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- AI CAMERA MOTIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_camera_motions (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    icon TEXT,
    keywords TEXT NOT NULL,
    is_system BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

INSERT INTO ai_camera_motions (id, name, description, icon, keywords, is_system) VALUES
    ('static', 'Static', 'Camera remains stationary', '⏸️', 'static shot, locked off camera', TRUE),
    ('slow_pan', 'Slow Pan', 'Gradual horizontal movement', '↔️', 'slow pan, smooth horizontal movement', TRUE),
    ('tilt', 'Tilt', 'Gradual vertical movement', '↕️', 'slow tilt, vertical camera movement', TRUE),
    ('dolly_in', 'Dolly In', 'Camera moves toward subject', '🎯', 'dolly in, push in, moving closer', TRUE),
    ('dolly_out', 'Dolly Out', 'Camera moves away from subject', '🔙', 'dolly out, pull back, reveal shot', TRUE),
    ('orbit', 'Orbit', 'Camera circles around subject', '🔄', 'orbit shot, 360 rotation, circling camera', TRUE),
    ('tracking', 'Tracking', 'Camera follows moving subject', '🏃', 'tracking shot, follow shot, moving with subject', TRUE),
    ('crane', 'Crane', 'Vertical movement, high to low', '🏗️', 'crane shot, jib shot, ascending descending', TRUE),
    ('zoom', 'Zoom', 'Lens zoom effect', '🔍', 'zoom in, zoom out, lens zoom', TRUE),
    ('handheld', 'Handheld', 'Slight shake for documentary feel', '✋', 'handheld camera, slight shake, organic movement', TRUE),
    ('drone', 'Drone', 'Aerial sweeping movements', '🚁', 'drone shot, aerial view, sweeping aerial movement', TRUE),
    ('first_person', 'First Person', 'POV perspective', '👁️', 'first person POV, point of view shot', TRUE)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- AI GENERATION JOBS TABLE (for tracking async generation status)
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_generation_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    generation_id UUID REFERENCES ai_video_generations(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    external_job_id TEXT, -- ID from the provider's API
    status TEXT NOT NULL DEFAULT 'queued', -- queued, processing, rendering, completed, failed
    progress INTEGER DEFAULT 0,
    queue_position INTEGER,
    estimated_completion TIMESTAMPTZ,
    
    -- Events log
    events JSONB DEFAULT '[]',
    -- [{timestamp, event, details}, ...]
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ai_generation_jobs_status ON ai_generation_jobs(status);
CREATE INDEX IF NOT EXISTS idx_ai_generation_jobs_generation ON ai_generation_jobs(generation_id);

-- ============================================================================
-- FUNCTION: Link AI generation to videos table after completion
-- ============================================================================

CREATE OR REPLACE FUNCTION link_ai_generation_to_videos()
RETURNS TRIGGER AS $$
BEGIN
    -- When an AI generation completes with an output URL, create a videos entry
    IF NEW.status = 'completed' AND NEW.output_url IS NOT NULL AND NEW.video_id IS NULL THEN
        INSERT INTO videos (user_id, source_type, source_uri, file_name, duration_sec, resolution, aspect_ratio)
        VALUES (
            COALESCE(NEW.user_id, '00000000-0000-0000-0000-000000000000'::UUID),
            'ai_generated',
            NEW.output_url,
            COALESCE(NEW.ai_title, 'AI Generated Video'),
            NEW.duration_seconds::INTEGER,
            NEW.resolution,
            NEW.aspect_ratio
        )
        RETURNING id INTO NEW.video_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger (drop first if exists)
DROP TRIGGER IF EXISTS trg_link_ai_generation ON ai_video_generations;
CREATE TRIGGER trg_link_ai_generation
    BEFORE UPDATE ON ai_video_generations
    FOR EACH ROW
    EXECUTE FUNCTION link_ai_generation_to_videos();

-- ============================================================================
-- VIEW: Unified media library (UGC + AI generated)
-- ============================================================================

CREATE OR REPLACE VIEW unified_media_library AS
SELECT 
    v.id,
    v.file_name as title,
    v.source_type,
    v.source_uri as url,
    v.duration_sec,
    v.resolution,
    v.aspect_ratio,
    v.created_at,
    'ugc' as origin,
    NULL::TEXT as ai_provider,
    NULL::TEXT as ai_prompt,
    NULL::TEXT as style_preset,
    va.pre_social_score as score,
    va.topics,
    va.tone
FROM videos v
LEFT JOIN video_analysis va ON v.id = va.video_id
WHERE v.source_type != 'ai_generated'

UNION ALL

SELECT 
    COALESCE(aig.video_id, aig.id) as id,
    COALESCE(aig.ai_title, 'AI Video') as title,
    'ai_generated' as source_type,
    aig.output_url as url,
    aig.duration_seconds::INTEGER as duration_sec,
    aig.resolution,
    aig.aspect_ratio,
    aig.created_at,
    'ai' as origin,
    aig.provider as ai_provider,
    aig.prompt as ai_prompt,
    aig.style_preset,
    NULL::NUMERIC as score,
    NULL::TEXT[] as topics,
    NULL::TEXT as tone
FROM ai_video_generations aig
WHERE aig.status = 'completed';

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE ai_characters IS 'Reusable character definitions for consistent AI video generation';
COMMENT ON TABLE ai_style_presets IS 'Visual style presets for AI video generation (system + custom)';
COMMENT ON TABLE ai_camera_motions IS 'Camera motion presets for AI video generation';
COMMENT ON TABLE ai_generation_jobs IS 'Async job tracking for AI video generation requests';
COMMENT ON VIEW unified_media_library IS 'Combined view of UGC uploads and AI-generated media';
