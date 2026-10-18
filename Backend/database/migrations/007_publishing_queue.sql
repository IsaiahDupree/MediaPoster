-- Publishing Queue System
-- Supports scheduled multi-platform publishing with priority and retry logic

CREATE TABLE IF NOT EXISTS publishing_queue (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Content references
    content_item_id UUID,
    clip_id UUID,
    
    -- Scheduling
    scheduled_for TIMESTAMP WITH TIME ZONE NOT NULL,
    priority INTEGER DEFAULT 0,  -- Higher = more important
    
    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'queued',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    last_error TEXT,
    
    -- Platform configuration
    platform VARCHAR(50) NOT NULL,
    platform_metadata JSONB DEFAULT '{}',
    
    -- Post content
    caption TEXT,
    hashtags TEXT[],
    thumbnail_url VARCHAR(500),
    video_url VARCHAR(500),
    
    -- Publishing results
    published_at TIMESTAMP WITH TIME ZONE,
    platform_post_id VARCHAR(255),
    platform_url VARCHAR(500),
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID,
    
    -- Constraints
    CONSTRAINT fk_content_item FOREIGN KEY (content_item_id) 
        REFERENCES content_items(id) ON DELETE SET NULL,
    CONSTRAINT fk_clip FOREIGN KEY (clip_id) 
        REFERENCES video_clips(id) ON DELETE SET NULL,
    CONSTRAINT valid_status CHECK (status IN ('queued', 'processing', 'published', 'failed', 'cancelled')),
    CONSTRAINT valid_platform CHECK (platform IN ('tiktok', 'instagram', 'youtube', 'linkedin', 'twitter', 'facebook', 'snapchat', 'threads', 'pinterest'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_queue_scheduled_status ON publishing_queue(scheduled_for, status) 
    WHERE status IN ('queued', 'processing');

CREATE INDEX IF NOT EXISTS idx_queue_status ON publishing_queue(status);

CREATE INDEX IF NOT EXISTS idx_queue_priority ON publishing_queue(priority DESC, scheduled_for ASC)
    WHERE status = 'queued';

CREATE INDEX IF NOT EXISTS idx_queue_platform ON publishing_queue(platform, status);

CREATE INDEX IF NOT EXISTS idx_queue_content_item ON publishing_queue(content_item_id) WHERE content_item_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_queue_clip ON publishing_queue(clip_id) WHERE clip_id IS NOT NULL;

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_publishing_queue_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER publishing_queue_update_timestamp
    BEFORE UPDATE ON publishing_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_publishing_queue_timestamp();

-- Helper function to get next items from queue
CREATE OR REPLACE FUNCTION get_next_queue_items(
    p_limit INTEGER DEFAULT 10,
    p_platform VARCHAR DEFAULT NULL
)
RETURNS TABLE (
    id UUID,
    content_item_id UUID,
    clip_id UUID,
    platform VARCHAR,
    scheduled_for TIMESTAMP WITH TIME ZONE,
    priority INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        q.id,
        q.content_item_id,
        q.clip_id,
        q.platform,
        q.scheduled_for,
        q.priority
    FROM publishing_queue q
    WHERE q.status = 'queued'
        AND q.scheduled_for <= NOW()
        AND (p_platform IS NULL OR q.platform = p_platform)
    ORDER BY q.priority DESC, q.scheduled_for ASC
    LIMIT p_limit
    FOR UPDATE SKIP LOCKED;  -- Prevent concurrent processing
END;
$$ LANGUAGE plpgsql;

-- Helper function to update queue item status
CREATE OR REPLACE FUNCTION update_queue_status(
    p_id UUID,
    p_status VARCHAR,
    p_error TEXT DEFAULT NULL,
    p_platform_post_id VARCHAR DEFAULT NULL,
    p_platform_url VARCHAR DEFAULT NULL
)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE publishing_queue
    SET status = p_status,
        last_error = p_error,
        platform_post_id = p_platform_post_id,
        platform_url = p_platform_url,
        published_at = CASE WHEN p_status = 'published' THEN NOW() ELSE published_at END
    WHERE id = p_id;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Helper function to retry failed items
CREATE OR REPLACE FUNCTION retry_queue_item(p_id UUID)
RETURNS BOOLEAN AS $$
DECLARE
    current_retry_count INTEGER;
    max_retry_count INTEGER;
BEGIN
    SELECT retry_count, max_retries
    INTO current_retry_count, max_retry_count
    FROM publishing_queue
    WHERE id = p_id;
    
    IF current_retry_count < max_retry_count THEN
        UPDATE publishing_queue
        SET status = 'queued',
            retry_count = retry_count + 1,
            last_error = NULL
        WHERE id = p_id;
        RETURN TRUE;
    ELSE
        RETURN FALSE;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Helper function to get queue statistics
CREATE OR REPLACE FUNCTION get_queue_statistics()
RETURNS TABLE (
    status VARCHAR,
    platform VARCHAR,
    count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        q.status,
        q.platform,
        COUNT(*) as count
    FROM publishing_queue q
    GROUP BY q.status, q.platform
    ORDER BY q.status, q.platform;
END;
$$ LANGUAGE plpgsql;

-- RLS Policies
ALTER TABLE publishing_queue ENABLE ROW LEVEL SECURITY;

CREATE POLICY publishing_queue_select_policy ON publishing_queue
    FOR SELECT
    USING (created_by = auth.uid());

CREATE POLICY publishing_queue_insert_policy ON publishing_queue
    FOR INSERT
    WITH CHECK (created_by = auth.uid());

CREATE POLICY publishing_queue_update_policy ON publishing_queue
    FOR UPDATE
    USING (created_by = auth.uid());

CREATE POLICY publishing_queue_delete_policy ON publishing_queue
    FOR DELETE
    USING (created_by = auth.uid());

-- Comments
COMMENT ON TABLE publishing_queue IS 'Scheduled publishing queue with priority and retry support';
COMMENT ON COLUMN publishing_queue.priority IS 'Higher values = higher priority (0-100)';
COMMENT ON COLUMN publishing_queue.platform_metadata IS 'Platform-specific configuration (duet settings, visibility, etc.)';
COMMENT ON COLUMN publishing_queue.status IS 'Current status: queued, processing, published, failed, cancelled';
