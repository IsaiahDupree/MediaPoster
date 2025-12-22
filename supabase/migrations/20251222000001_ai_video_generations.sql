-- ============================================================================
-- AI VIDEO GENERATIONS
-- ============================================================================
-- Tracks AI-generated video requests and their outputs
-- ============================================================================

CREATE TABLE IF NOT EXISTS ai_video_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL, -- sora, runway, pika, kling, luma, minimax, haiper
    prompt TEXT NOT NULL,
    settings JSONB DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed
    
    -- Output
    output_url TEXT,
    thumbnail_url TEXT,
    duration_seconds DECIMAL(10, 2),
    resolution TEXT,
    aspect_ratio TEXT,
    file_size_bytes BIGINT,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    -- Optional: Link to media library after download
    media_id UUID,
    
    -- Metadata
    metadata JSONB DEFAULT '{}'
);

-- Index for querying by status and provider
CREATE INDEX IF NOT EXISTS idx_ai_video_generations_status ON ai_video_generations(status);
CREATE INDEX IF NOT EXISTS idx_ai_video_generations_provider ON ai_video_generations(provider);
CREATE INDEX IF NOT EXISTS idx_ai_video_generations_created ON ai_video_generations(created_at DESC);

-- View for recent generations
CREATE OR REPLACE VIEW recent_ai_videos AS
SELECT 
    id,
    provider,
    prompt,
    status,
    output_url,
    thumbnail_url,
    created_at,
    completed_at,
    EXTRACT(EPOCH FROM (completed_at - created_at)) as generation_time_seconds
FROM ai_video_generations
ORDER BY created_at DESC
LIMIT 50;
