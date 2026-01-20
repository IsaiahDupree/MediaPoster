-- Voice Cloning System Migration
-- Adds voice profiles and voice generation tracking tables
-- Feature: VC-004

-- Voice profiles table
CREATE TABLE IF NOT EXISTS voice_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,

    -- Profile metadata
    name VARCHAR(100) NOT NULL,
    description TEXT,

    -- Reference audio URLs (JSON array of S3/storage URLs)
    reference_urls JSONB DEFAULT '[]'::jsonb,

    -- Voice embedding (from Modal/external service)
    embedding_id VARCHAR(255),  -- External service's voice ID
    embedding_created_at TIMESTAMPTZ,

    -- Quality metrics
    quality_score FLOAT CHECK (quality_score >= 0.0 AND quality_score <= 1.0),
    quality_notes TEXT,

    -- Default settings
    default_speed FLOAT DEFAULT 1.0 CHECK (default_speed >= 0.5 AND default_speed <= 2.0),
    default_emotion VARCHAR(20) DEFAULT 'neutral',
    default_stability FLOAT DEFAULT 0.5 CHECK (default_stability >= 0.0 AND default_stability <= 1.0),

    -- Status
    is_default BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Voice generations table (tracks all TTS generation jobs)
CREATE TABLE IF NOT EXISTS voice_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE NOT NULL,
    voice_profile_id UUID REFERENCES voice_profiles(id) ON DELETE SET NULL,

    -- Input
    input_text TEXT NOT NULL,
    options JSONB DEFAULT '{}'::jsonb,  -- speed, pitch, emotion, stability

    -- Output
    output_url TEXT,
    duration_seconds FLOAT,
    file_size_bytes BIGINT,

    -- Processing status
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    modal_job_id VARCHAR(255),  -- External service job ID
    processing_time_ms INTEGER,
    error_message TEXT,

    -- Cost tracking
    cost_credits FLOAT DEFAULT 0.0,

    -- Usage tracking (where was this audio used?)
    used_in_clip_id UUID,
    used_in_post_id UUID,
    used_in_creative_brief_id UUID,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

-- Indexes for voice_profiles
CREATE INDEX IF NOT EXISTS idx_voice_profiles_user ON voice_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_voice_profiles_default ON voice_profiles(user_id) WHERE is_default = true;
CREATE INDEX IF NOT EXISTS idx_voice_profiles_active ON voice_profiles(user_id) WHERE is_active = true;

-- Indexes for voice_generations
CREATE INDEX IF NOT EXISTS idx_voice_generations_user ON voice_generations(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_voice_generations_profile ON voice_generations(voice_profile_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_voice_generations_status ON voice_generations(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_voice_generations_clip ON voice_generations(used_in_clip_id);
CREATE INDEX IF NOT EXISTS idx_voice_generations_post ON voice_generations(used_in_post_id);

-- Update trigger for voice_profiles
CREATE OR REPLACE FUNCTION update_voice_profile_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER voice_profiles_updated_at
    BEFORE UPDATE ON voice_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_voice_profile_updated_at();

-- Ensure only one default profile per user
CREATE OR REPLACE FUNCTION ensure_single_default_voice_profile()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.is_default = true THEN
        -- Unset all other default profiles for this user
        UPDATE voice_profiles
        SET is_default = false
        WHERE user_id = NEW.user_id
          AND id != NEW.id
          AND is_default = true;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER voice_profiles_single_default
    AFTER INSERT OR UPDATE ON voice_profiles
    FOR EACH ROW
    WHEN (NEW.is_default = true)
    EXECUTE FUNCTION ensure_single_default_voice_profile();

-- Voice analytics view
CREATE OR REPLACE VIEW voice_usage_analytics AS
SELECT
    vp.id AS voice_profile_id,
    vp.user_id,
    vp.name AS voice_name,
    COUNT(vg.id) AS total_generations,
    COUNT(CASE WHEN vg.status = 'completed' THEN 1 END) AS successful_generations,
    COUNT(CASE WHEN vg.status = 'failed' THEN 1 END) AS failed_generations,
    SUM(vg.duration_seconds) AS total_audio_seconds,
    SUM(vg.cost_credits) AS total_cost,
    AVG(vg.processing_time_ms) AS avg_processing_time_ms,
    MAX(vg.created_at) AS last_used_at
FROM voice_profiles vp
LEFT JOIN voice_generations vg ON vp.id = vg.voice_profile_id
GROUP BY vp.id, vp.user_id, vp.name;

COMMENT ON TABLE voice_profiles IS 'Voice profiles for voice cloning/TTS generation';
COMMENT ON TABLE voice_generations IS 'Voice generation jobs and history';
COMMENT ON VIEW voice_usage_analytics IS 'Analytics view for voice profile usage';
