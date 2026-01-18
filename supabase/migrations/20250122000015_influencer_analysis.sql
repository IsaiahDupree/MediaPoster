-- Influencer Analysis Reports table
-- Stores AI-generated analysis reports for competitor/influencer accounts

CREATE TABLE IF NOT EXISTS influencer_analysis_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,
    username TEXT NOT NULL,
    display_name TEXT,
    follower_count INTEGER DEFAULT 0,
    
    -- Analysis summary
    unique_positioning TEXT,
    content_strategy TEXT,
    target_audience TEXT,
    who_they_help TEXT,
    funnel_setup TEXT,
    
    -- Arrays
    key_learnings TEXT[],
    actionable_tactics TEXT[],
    content_pillars TEXT[],
    viral_patterns TEXT[],
    
    -- Full report JSON
    report_data JSONB,
    
    -- Metadata
    analyzed_at TIMESTAMPTZ DEFAULT NOW(),
    confidence_score FLOAT,
    analysis_version TEXT DEFAULT '1.0',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, username)
);

CREATE INDEX IF NOT EXISTS idx_influencer_reports_platform ON influencer_analysis_reports(platform);
CREATE INDEX IF NOT EXISTS idx_influencer_reports_username ON influencer_analysis_reports(username);
CREATE INDEX IF NOT EXISTS idx_influencer_reports_analyzed ON influencer_analysis_reports(analyzed_at DESC);
CREATE INDEX IF NOT EXISTS idx_influencer_reports_followers ON influencer_analysis_reports(follower_count DESC);

COMMENT ON TABLE influencer_analysis_reports IS 'AI-generated analysis reports for competitor/influencer accounts';
