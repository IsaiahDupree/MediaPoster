-- Analysis Enhancement: Manual Segment Editing
-- Adds support for manual segment editing, tracking, and validation

-- =====================================================
-- SEGMENT EDITING ENHANCEMENTS
-- =====================================================

-- Add columns to track manual edits
ALTER TABLE video_segments 
    ADD COLUMN IF NOT EXISTS is_manual BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS edited_by UUID,
    ADD COLUMN IF NOT EXISTS edit_reason TEXT,
    ADD COLUMN IF NOT EXISTS original_segment_id UUID,
    ADD COLUMN IF NOT EXISTS confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1);

-- Add index for manual segments
CREATE INDEX IF NOT EXISTS idx_video_segments_is_manual ON video_segments(is_manual) WHERE is_manual = true;

-- Add index for edited segments
CREATE INDEX IF NOT EXISTS idx_video_segments_edited_by ON video_segments(edited_by) WHERE edited_by IS NOT NULL;

-- =====================================================
-- SEGMENT PERFORMANCE TRACKING
-- =====================================================

CREATE TABLE IF NOT EXISTS segment_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    segment_id BIGINT NOT NULL,
    post_id UUID NOT NULL,
    
    -- Metrics at segment timestamps
    views_at_start INTEGER DEFAULT 0,
    views_at_end INTEGER DEFAULT 0,
    retention_rate FLOAT CHECK (retention_rate >= 0 AND retention_rate <= 1),
    
    -- Engagement during segment
    likes_during INTEGER DEFAULT 0,
    comments_during INTEGER DEFAULT 0,
    shares_during INTEGER DEFAULT 0,
    replays_during INTEGER DEFAULT 0,
    
    -- Calculated scores
    engagement_score FLOAT,
    effectiveness_score FLOAT,
    
    -- Metadata
    measured_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_segment FOREIGN KEY (segment_id) REFERENCES video_segments(id) ON DELETE CASCADE,
    CONSTRAINT fk_post FOREIGN KEY (post_id) REFERENCES platform_posts(id) ON DELETE CASCADE,
    CONSTRAINT unique_segment_post UNIQUE(segment_id, post_id)
);

-- Indexes for performance queries
CREATE INDEX IF NOT EXISTS idx_segment_performance_segment_id ON segment_performance(segment_id);
CREATE INDEX IF NOT EXISTS idx_segment_performance_post_id ON segment_performance(post_id);
CREATE INDEX IF NOT EXISTS idx_segment_performance_engagement_score ON segment_performance(engagement_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_segment_performance_effectiveness_score ON segment_performance(effectiveness_score DESC NULLS LAST);

-- =====================================================
-- SEGMENT EDIT HISTORY
-- =====================================================

CREATE TABLE IF NOT EXISTS segment_edit_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    segment_id BIGINT NOT NULL,
    edited_by UUID NOT NULL,
    
    -- What changed
    edit_type VARCHAR(50) NOT NULL,  -- created, updated, split, merged, deleted
    field_changes JSONB,  -- Before/after values
    
    -- Why it changed
    edit_reason TEXT,
    
    -- When
    edited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT fk_segment_history FOREIGN KEY (segment_id) REFERENCES video_segments(id) ON DELETE CASCADE,
    CONSTRAINT valid_edit_type CHECK (edit_type IN ('created', 'updated', 'split', 'merged', 'deleted', 'reclassified'))
);

CREATE INDEX IF NOT EXISTS idx_segment_edit_history_segment_id ON segment_edit_history(segment_id);
CREATE INDEX IF NOT EXISTS idx_segment_edit_history_edited_by ON segment_edit_history(edited_by);
CREATE INDEX IF NOT EXISTS idx_segment_edit_history_edited_at ON segment_edit_history(edited_at DESC);

-- =====================================================
-- HELPER FUNCTIONS
-- =====================================================

-- Function to validate segment timing for a video
CREATE OR REPLACE FUNCTION validate_video_segments(p_video_id UUID)
RETURNS TABLE (
    issue_type VARCHAR,
    segment_id UUID,
    details TEXT
) AS $$
BEGIN
    -- Check for overlapping segments
    RETURN QUERY
    SELECT 
        'overlap'::VARCHAR as issue_type,
        s1.id as segment_id,
        format('Overlaps with segment %s', s2.id) as details
    FROM video_segments s1
    INNER JOIN video_segments s2 ON s1.video_id = s2.video_id
    WHERE s1.video_id = p_video_id
        AND s1.id < s2.id
        AND s1.start_time < s2.end_time
        AND s1.end_time > s2.start_time;
    
    -- Check for invalid timing (end before start)
    RETURN QUERY
    SELECT 
        'invalid_timing'::VARCHAR,
        id,
        'End time is before or equal to start time'
    FROM video_segments
    WHERE video_id = p_video_id
        AND end_time <= start_time;
    
    -- Check for segments with zero/negative duration
    RETURN QUERY
    SELECT 
        'zero_duration'::VARCHAR,
        id,
        format('Duration is %.2f seconds', end_time - start_time)
    FROM video_segments
    WHERE video_id = p_video_id
        AND (end_time - start_time) < 0.1;
END;
$$ LANGUAGE plpgsql;

-- Function to find gaps between segments
CREATE OR REPLACE FUNCTION find_segment_gaps(p_video_id UUID, p_min_gap_seconds FLOAT DEFAULT 1.0)
RETURNS TABLE (
    gap_start FLOAT,
    gap_end FLOAT,
    gap_duration FLOAT
) AS $$
BEGIN
    RETURN QUERY
    WITH ordered_segments AS (
        SELECT 
            start_time,
            end_time,
            LEAD(start_time) OVER (ORDER BY start_time) as next_start
        FROM video_segments
        WHERE video_id = p_video_id
        ORDER BY start_time
    )
    SELECT 
        end_time as gap_start,
        next_start as gap_end,
        next_start - end_time as gap_duration
    FROM ordered_segments
    WHERE next_start IS NOT NULL
        AND (next_start - end_time) >= p_min_gap_seconds;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate segment performance score
CREATE OR REPLACE FUNCTION calculate_segment_performance_score(
    p_retention_rate FLOAT,
    p_likes INTEGER,
    p_comments INTEGER,
    p_shares INTEGER,
    p_views INTEGER
)
RETURNS FLOAT AS $$
DECLARE
    engagement_rate FLOAT;
    performance_score FLOAT;
BEGIN
    -- Calculate engagement rate
    IF p_views > 0 THEN
        engagement_rate := (p_likes + p_comments + p_shares)::FLOAT / p_views;
    ELSE
        engagement_rate := 0;
    END IF;
    
    -- Weighted score formula
    -- Retention: 40%, Engagement: 30%, Shares: 20%, Comments: 10%
    performance_score := 
        (COALESCE(p_retention_rate, 0) * 0.4) +
        (LEAST(engagement_rate, 0.2) / 0.2 * 0.3) +  -- Cap at 20% engagement
        (LEAST(p_shares::FLOAT / GREATEST(p_views, 1), 0.05) / 0.05 * 0.2) +  -- Cap at 5% share rate
        (LEAST(p_comments::FLOAT / GREATEST(p_views, 1), 0.1) / 0.1 * 0.1);  -- Cap at 10% comment rate
    
    RETURN LEAST(performance_score, 1.0);  -- Cap at 1.0
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-calculate performance scores
CREATE OR REPLACE FUNCTION update_segment_performance_scores()
RETURNS TRIGGER AS $$
BEGIN
    NEW.engagement_score := calculate_segment_performance_score(
        NEW.retention_rate,
        NEW.likes_during,
        NEW.comments_during,
        NEW.shares_during,
        NEW.views_at_start
    );
    
    NEW.effectiveness_score := NEW.engagement_score;  -- Can be customized later
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER segment_performance_score_trigger
    BEFORE INSERT OR UPDATE ON segment_performance
    FOR EACH ROW
    EXECUTE FUNCTION update_segment_performance_scores();

-- =====================================================
-- ROW LEVEL SECURITY
-- =====================================================

-- Enable RLS on new tables
ALTER TABLE segment_performance ENABLE ROW LEVEL SECURITY;
ALTER TABLE segment_edit_history ENABLE ROW LEVEL SECURITY;

-- Policies for segment_performance
CREATE POLICY segment_performance_select_policy ON segment_performance
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM video_segments vs
        INNER JOIN videos v ON vs.video_id = v.id
        WHERE vs.id = segment_performance.segment_id
        AND v.user_id = auth.uid()
    ));

CREATE POLICY segment_performance_insert_policy ON segment_performance
    FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM video_segments vs
        INNER JOIN videos v ON vs.video_id = v.id
        WHERE vs.id = segment_performance.segment_id
        AND v.user_id = auth.uid()
    ));

-- Policies for segment_edit_history
CREATE POLICY segment_edit_history_select_policy ON segment_edit_history
    FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM video_segments vs
        INNER JOIN videos v ON vs.video_id = v.id
        WHERE vs.id = segment_edit_history.segment_id
        AND v.user_id = auth.uid()
    ));

CREATE POLICY segment_edit_history_insert_policy ON segment_edit_history
    FOR INSERT
    WITH CHECK (edited_by = auth.uid());

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE segment_performance IS 'Tracks performance metrics for video segments across different platform posts';
COMMENT ON TABLE segment_edit_history IS 'Audit log of all manual edits made to video segments';

COMMENT ON COLUMN video_segments.is_manual IS 'Whether this segment was manually created/edited';
COMMENT ON COLUMN video_segments.edited_by IS 'User ID who made manual edits';
COMMENT ON COLUMN video_segments.confidence_score IS 'AI confidence score for auto-generated segments (0-1)';
COMMENT ON COLUMN segment_performance.retention_rate IS 'Percentage of viewers who watched the entire segment';
COMMENT ON COLUMN segment_performance.effectiveness_score IS 'Overall segment effectiveness score (0-1)';
