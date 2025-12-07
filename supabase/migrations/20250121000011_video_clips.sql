-- Clip Generation System Database Schema
-- Creates tables for video clip selection, configuration, and publishing

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =====================================================
-- VIDEO CLIPS TABLE
-- =====================================================
-- Stores clip configurations extracted from analyzed videos

CREATE TABLE video_clips (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    video_id UUID NOT NULL,
    user_id UUID NOT NULL,
    
    -- Clip timing (in seconds)
    start_time FLOAT NOT NULL CHECK (start_time >= 0),
    end_time FLOAT NOT NULL CHECK (end_time > start_time),
    duration FLOAT GENERATED ALWAYS AS (end_time - start_time) STORED,
    
    -- Clip metadata
    title VARCHAR(500),
    description TEXT,
    clip_type VARCHAR(50) DEFAULT 'custom',  -- 'highlight', 'full', 'custom', 'ai_generated'
    
    -- Configuration (JSONB for flexibility)
    overlay_config JSONB DEFAULT '{}',  -- text overlays, positioning, styling
    caption_config JSONB DEFAULT '{}',  -- caption styling, animations, timing
    thumbnail_config JSONB DEFAULT '{}',  -- thumbnail frame selection, enhancements
    
    -- AI-generated insights
    ai_suggested BOOLEAN DEFAULT false,
    ai_score FLOAT CHECK (ai_score >= 0 AND ai_score <= 1),  -- 0-1 quality score
    ai_reasoning TEXT,  -- why this clip was selected by AI
    
    -- Segment associations (references to video_segments)
    segment_ids UUID[],  -- array of segment UUIDs
    hook_segment_id UUID,  -- primary hook segment
    
    -- Platform optimization
    platform_variants JSONB DEFAULT '{}',  -- platform-specific configurations
    target_platforms VARCHAR(50)[],  -- intended platforms for this clip
    
    -- Status tracking
    status VARCHAR(50) DEFAULT 'draft',  -- draft, ready, published, archived
    render_status VARCHAR(50),  -- pending, processing, completed, failed (if rendering enabled)
    rendered_url VARCHAR(500),  -- URL to rendered video file
    render_error TEXT,  -- error message if rendering failed
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_video FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    CONSTRAINT valid_clip_type CHECK (clip_type IN ('highlight', 'full', 'custom', 'ai_generated')),
    CONSTRAINT valid_status CHECK (status IN ('draft', 'ready', 'published', 'archived')),
    CONSTRAINT valid_render_status CHECK (render_status IS NULL OR render_status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_video_clips_video_id ON video_clips(video_id);
CREATE INDEX IF NOT EXISTS idx_video_clips_user_id ON video_clips(user_id);
CREATE INDEX IF NOT EXISTS idx_video_clips_status ON video_clips(status);
CREATE INDEX IF NOT EXISTS idx_video_clips_ai_suggested ON video_clips(ai_suggested) WHERE ai_suggested = true;
CREATE INDEX IF NOT EXISTS idx_video_clips_created_at ON video_clips(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_video_clips_target_platforms ON video_clips USING GIN(target_platforms);

-- Trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_video_clips_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER video_clips_updated_at_trigger
    BEFORE UPDATE ON video_clips
    FOR EACH ROW
    EXECUTE FUNCTION update_video_clips_updated_at();

-- =====================================================
-- CLIP POSTS JUNCTION TABLE
-- =====================================================
-- Many-to-many relationship between clips and platform posts

CREATE TABLE clip_posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    clip_id UUID NOT NULL,
    post_id UUID NOT NULL,
    platform VARCHAR(50) NOT NULL,
    
    -- Platform-specific overrides
    platform_config JSONB DEFAULT '{}',  -- platform-specific metadata overrides
    thumbnail_url VARCHAR(500),  -- platform-specific thumbnail
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_clip FOREIGN KEY (clip_id) REFERENCES video_clips(id) ON DELETE CASCADE,
    CONSTRAINT fk_post FOREIGN KEY (post_id) REFERENCES platform_posts(id) ON DELETE CASCADE,
    CONSTRAINT unique_clip_post UNIQUE(clip_id, post_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_clip_posts_clip_id ON clip_posts(clip_id);
CREATE INDEX IF NOT EXISTS idx_clip_posts_post_id ON clip_posts(post_id);
CREATE INDEX IF NOT EXISTS idx_clip_posts_platform ON clip_posts(platform);

-- =====================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- =====================================================

-- Enable RLS on video_clips
ALTER TABLE video_clips ENABLE ROW LEVEL SECURITY;

-- Users can view their own clips
CREATE POLICY video_clips_select_policy ON video_clips
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own clips
CREATE POLICY video_clips_insert_policy ON video_clips
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own clips
CREATE POLICY video_clips_update_policy ON video_clips
    FOR UPDATE
    USING (auth.uid() = user_id);

-- Users can delete their own clips
CREATE POLICY video_clips_delete_policy ON video_clips
    FOR DELETE
    USING (auth.uid() = user_id);

-- Enable RLS on clip_posts
ALTER TABLE clip_posts ENABLE ROW LEVEL SECURITY;

-- Users can view clip_posts for their clips
CREATE POLICY clip_posts_select_policy ON clip_posts
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM video_clips vc
        WHERE vc.id = clip_posts.clip_id
        AND vc.user_id = auth.uid()
    ));

-- Users can insert clip_posts for their clips
CREATE POLICY clip_posts_insert_policy ON clip_posts
    FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM video_clips vc
        WHERE vc.id = clip_posts.clip_id
        AND vc.user_id = auth.uid()
    ));

-- Users can delete clip_posts for their clips
CREATE POLICY clip_posts_delete_policy ON clip_posts
    FOR DELETE
    USING (EXISTS (
        SELECT 1 FROM video_clips vc
        WHERE vc.id = clip_posts.clip_id
        AND vc.user_id = auth.uid()
    ));

-- =====================================================
-- HELPER FUNCTIONS
-- =====================================================

-- Function to get all clips for a video with their post status
CREATE OR REPLACE FUNCTION get_video_clips_with_status(p_video_id UUID)
RETURNS TABLE (
    clip_id UUID,
    title VARCHAR,
    start_time FLOAT,
    end_time FLOAT,
    duration FLOAT,
    clip_type VARCHAR,
    ai_score FLOAT,
    status VARCHAR,
    post_count BIGINT,
    platforms VARCHAR[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        vc.id,
        vc.title,
        vc.start_time,
        vc.end_time,
        vc.duration,
        vc.clip_type,
        vc.ai_score,
        vc.status,
        COUNT(DISTINCT cp.post_id) as post_count,
        ARRAY_AGG(DISTINCT cp.platform) FILTER (WHERE cp.platform IS NOT NULL) as platforms
    FROM video_clips vc
    LEFT JOIN clip_posts cp ON vc.id = cp.clip_id
    WHERE vc.video_id = p_video_id
    GROUP BY vc.id
    ORDER BY vc.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get clip performance metrics
CREATE OR REPLACE FUNCTION get_clip_performance(p_clip_id UUID)
RETURNS TABLE (
    total_views BIGINT,
    total_likes BIGINT,
    total_shares BIGINT,
    total_comments BIGINT,
    avg_engagement_rate FLOAT,
    platform_breakdown JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        SUM(pc.total_views)::BIGINT as total_views,
        SUM(pc.total_likes)::BIGINT as total_likes,
        SUM(pc.total_shares)::BIGINT as total_shares,
        SUM(pc.total_comments)::BIGINT as total_comments,
        AVG(
            CASE 
                WHEN pc.total_views > 0 
                THEN ((pc.total_likes + pc.total_shares + pc.total_comments)::FLOAT / pc.total_views)
                ELSE 0
            END
        )::FLOAT as avg_engagement_rate,
        jsonb_object_agg(
            cp.platform,
            jsonb_build_object(
                'views', pc.total_views,
                'likes', pc.total_likes,
                'shares', pc.total_shares,
                'comments', pc.total_comments
            )
        ) as platform_breakdown
    FROM clip_posts cp
    INNER JOIN platform_posts pp ON cp.post_id = pp.id
    LEFT JOIN LATERAL (
        SELECT 
            MAX(views) as total_views,
            MAX(likes) as total_likes,
            MAX(shares) as total_shares,
            MAX(comments) as total_comments
        FROM platform_checkbacks
        WHERE post_id = pp.id
    ) pc ON true
    WHERE cp.clip_id = p_clip_id
    GROUP BY cp.clip_id;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE video_clips IS 'Stores clip configurations extracted from analyzed videos with AI suggestions and platform variants';
COMMENT ON TABLE clip_posts IS 'Junction table linking video clips to platform posts for multi-platform publishing';

COMMENT ON COLUMN video_clips.start_time IS 'Clip start time in seconds from video beginning';
COMMENT ON COLUMN video_clips.end_time IS 'Clip end time in seconds from video beginning';
COMMENT ON COLUMN video_clips.ai_score IS 'AI quality score from 0-1 based on hook quality, engagement, emotion arc, and platform fit';
COMMENT ON COLUMN video_clips.segment_ids IS 'Array of video_segment UUIDs that this clip encompasses';
COMMENT ON COLUMN video_clips.platform_variants IS 'JSONB object containing platform-specific configuration overrides';
