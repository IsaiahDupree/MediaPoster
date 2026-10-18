-- Instagram Research Enhancements
-- Hook library, strategy reports, content gap analysis, benchmarks

-- =============================================================================
-- HOOK LIBRARY: Saved hooks extracted from competitor content
-- =============================================================================

CREATE TABLE IF NOT EXISTS saved_hooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Hook content
    hook_text TEXT NOT NULL,
    hook_type TEXT NOT NULL,  -- question, bold_statement, controversy, curiosity, pain_point, transformation
    
    -- Source tracking
    source_account TEXT,  -- competitor username
    source_post_id UUID REFERENCES competitor_post(post_id) ON DELETE SET NULL,
    source_platform TEXT DEFAULT 'instagram',
    
    -- Performance context
    source_views INTEGER,
    source_likes INTEGER,
    source_comments INTEGER,
    performance_score FLOAT,  -- weighted engagement score
    
    -- User annotations
    notes TEXT,
    tags TEXT[],
    is_favorite BOOLEAN DEFAULT FALSE,
    times_used INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_saved_hooks_type ON saved_hooks(hook_type);
CREATE INDEX idx_saved_hooks_score ON saved_hooks(performance_score DESC);
CREATE INDEX idx_saved_hooks_source ON saved_hooks(source_account);

-- =============================================================================
-- STRATEGY REPORTS: Weekly auto-generated strategy reports
-- =============================================================================

CREATE TABLE IF NOT EXISTS strategy_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Report period
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    
    -- Performance summary
    performance_summary JSONB DEFAULT '{}',
    -- {posts_published, total_views, new_followers, engagement_rate, vs_last_week}
    
    -- Top content this week
    top_content JSONB DEFAULT '[]',
    -- [{title, views, engagement_rate, content_id}]
    
    -- Trending recommendations
    trending_recommendations JSONB DEFAULT '{}',
    -- {hashtags: [], sounds: [], formats: []}
    
    -- AI-generated content ideas
    content_ideas JSONB DEFAULT '[]',
    -- [{title, hook_type, format, hashtags, sound, why_it_works}]
    
    -- Action items
    action_items JSONB DEFAULT '[]',
    -- [{action, priority, category, completed}]
    
    -- Full markdown report
    report_markdown TEXT,
    
    -- Generation metadata
    competitors_analyzed TEXT[],
    model_used TEXT DEFAULT 'gpt-4o-mini',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(week_start)
);

CREATE INDEX idx_strategy_reports_week ON strategy_reports(week_start DESC);

-- =============================================================================
-- CONTENT GAP ANALYSIS: Themes competitors cover that user doesn't
-- =============================================================================

CREATE TABLE IF NOT EXISTS content_gap_analysis (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Compared accounts
    competitor_usernames TEXT[] NOT NULL,
    
    -- Gap themes
    gap_themes JSONB DEFAULT '[]',
    -- [{theme, competitor_avg_views, competitor_post_count, opportunity_score, suggested_content}]
    
    -- Overlap themes (both user and competitors cover)
    overlap_themes JSONB DEFAULT '[]',
    -- [{theme, user_avg_views, competitor_avg_views, delta_pct}]
    
    -- User-only themes (user covers, competitors don't)
    unique_themes JSONB DEFAULT '[]',
    
    -- Overall score
    gap_coverage_score FLOAT,  -- 0-100, how much user covers competitor themes
    
    -- AI reasoning
    ai_analysis TEXT,
    model_used TEXT DEFAULT 'gpt-4o-mini',
    
    analyzed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_content_gap_analyzed ON content_gap_analysis(analyzed_at DESC);

-- =============================================================================
-- PERFORMANCE BENCHMARKS: Periodic benchmark snapshots
-- =============================================================================

CREATE TABLE IF NOT EXISTS performance_benchmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- User metrics
    user_engagement_rate FLOAT,
    user_avg_views FLOAT,
    user_avg_likes FLOAT,
    user_posting_frequency FLOAT,  -- posts per week
    user_follower_growth_pct FLOAT,  -- 30-day growth %
    
    -- Competitor averages
    competitor_engagement_rate FLOAT,
    competitor_avg_views FLOAT,
    competitor_avg_likes FLOAT,
    competitor_posting_frequency FLOAT,
    competitor_follower_growth_pct FLOAT,
    
    -- Per-competitor breakdown
    competitor_breakdown JSONB DEFAULT '[]',
    -- [{username, engagement_rate, avg_views, posting_freq, follower_growth}]
    
    -- Deltas and status
    deltas JSONB DEFAULT '{}',
    -- {engagement_rate: {value, status: 'above'|'below'|'at'}, ...}
    
    -- Action recommendations
    recommendations JSONB DEFAULT '[]',
    -- [{metric, status, action, priority}]
    
    benchmarked_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_benchmarks_date ON performance_benchmarks(benchmarked_at DESC);

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE saved_hooks IS 'Curated hook library extracted from competitor analysis';
COMMENT ON TABLE strategy_reports IS 'Weekly AI-generated content strategy reports';
COMMENT ON TABLE content_gap_analysis IS 'Content theme gap analysis between user and competitors';
COMMENT ON TABLE performance_benchmarks IS 'Performance benchmark snapshots comparing user vs competitors';
