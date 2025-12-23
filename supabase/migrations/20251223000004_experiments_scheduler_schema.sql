-- Experiments Scheduler Schema
-- AI-Powered Content Experimentation & Learning System

-- =============================================================================
-- EXPERIMENTS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID,
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    goal TEXT NOT NULL,
    
    experiment_type VARCHAR(50), -- hook, format, timing, caption, audio, content_angle
    
    status VARCHAR(20) DEFAULT 'draft', -- draft, active, paused, completed, archived
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    
    success_criteria JSONB DEFAULT '{}',
    results JSONB DEFAULT '{}',
    learnings TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_experiments_type ON experiments(experiment_type);

-- =============================================================================
-- HYPOTHESES TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS hypotheses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id) ON DELETE CASCADE,
    
    statement TEXT NOT NULL, -- "Videos with questions in first 2 seconds get 40% more views"
    
    independent_variable VARCHAR(255), -- What we're changing
    dependent_variable VARCHAR(255),   -- What we're measuring
    control_description TEXT,          -- Baseline approach
    variant_description TEXT,          -- Test approach
    
    success_metric VARCHAR(100),       -- view_count, engagement_rate, etc.
    success_threshold FLOAT,           -- 1.4 = 40% improvement required
    min_sample_size INT DEFAULT 10,
    
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, passed, failed, inconclusive
    confidence_level FLOAT,
    actual_improvement FLOAT,
    learnings TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_hypotheses_experiment ON hypotheses(experiment_id);
CREATE INDEX IF NOT EXISTS idx_hypotheses_status ON hypotheses(status);

-- =============================================================================
-- EXPERIMENT VARIANTS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS experiment_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    hypothesis_id UUID REFERENCES hypotheses(id) ON DELETE CASCADE,
    
    variant_type VARCHAR(20) NOT NULL, -- control, variant_a, variant_b
    description TEXT,
    
    video_id UUID,
    content_id UUID,
    
    modifications JSONB DEFAULT '{}', -- What was changed from control
    
    post_count INT DEFAULT 0,
    total_views BIGINT DEFAULT 0,
    total_engagement BIGINT DEFAULT 0,
    avg_watch_time_pct FLOAT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_variants_hypothesis ON experiment_variants(hypothesis_id);
CREATE INDEX IF NOT EXISTS idx_variants_type ON experiment_variants(variant_type);

-- =============================================================================
-- CONTENT PATTERNS (Learnings)
-- =============================================================================

CREATE TABLE IF NOT EXISTS content_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID,
    
    pattern_type VARCHAR(50), -- hook, format, timing, caption, audio
    description TEXT,
    
    success_rate FLOAT,
    avg_improvement FLOAT,
    
    supporting_experiments UUID[],
    sample_size INT DEFAULT 0,
    confidence FLOAT,
    
    when_to_use TEXT,
    when_to_avoid TEXT,
    
    first_discovered TIMESTAMPTZ DEFAULT NOW(),
    last_validated TIMESTAMPTZ,
    times_applied INT DEFAULT 0,
    
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_patterns_type ON content_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_patterns_active ON content_patterns(is_active);

-- =============================================================================
-- EXPERIMENT WINNERS (Promotion Pipeline)
-- =============================================================================

CREATE TABLE IF NOT EXISTS experiment_winners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id),
    hypothesis_id UUID REFERENCES hypotheses(id),
    
    video_id UUID,
    post_id UUID,
    
    performance_metrics JSONB DEFAULT '{}',
    -- views, engagement_rate, watch_time_pct, etc.
    
    promoted_to_narrative BOOLEAN DEFAULT FALSE,
    promoted_at TIMESTAMPTZ,
    narrative_run_id UUID, -- Link to agent_runs when promoted
    
    narrative_performance JSONB DEFAULT '{}',
    -- How it performed in narrative builder
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_winners_experiment ON experiment_winners(experiment_id);
CREATE INDEX IF NOT EXISTS idx_winners_promoted ON experiment_winners(promoted_to_narrative);

-- =============================================================================
-- POST ORIGIN TRACKING (Add to scheduled_posts if exists)
-- =============================================================================

DO $$
BEGIN
    -- Add origin tracking to scheduled_posts if table exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'scheduled_posts') THEN
        ALTER TABLE scheduled_posts ADD COLUMN IF NOT EXISTS origin_type VARCHAR(20) DEFAULT 'user';
        ALTER TABLE scheduled_posts ADD COLUMN IF NOT EXISTS experiment_id UUID;
        ALTER TABLE scheduled_posts ADD COLUMN IF NOT EXISTS hypothesis_id UUID;
        ALTER TABLE scheduled_posts ADD COLUMN IF NOT EXISTS variant VARCHAR(20);
        
        CREATE INDEX IF NOT EXISTS idx_scheduled_posts_origin ON scheduled_posts(origin_type);
        CREATE INDEX IF NOT EXISTS idx_scheduled_posts_experiment ON scheduled_posts(experiment_id);
    END IF;
END $$;

-- =============================================================================
-- VIEWS FOR ANALYTICS
-- =============================================================================

CREATE OR REPLACE VIEW v_experiment_results AS
SELECT 
    e.id as experiment_id,
    e.name as experiment_name,
    e.experiment_type,
    e.status as experiment_status,
    h.id as hypothesis_id,
    h.statement as hypothesis,
    h.status as hypothesis_status,
    h.success_threshold,
    h.actual_improvement,
    h.confidence_level,
    (SELECT COUNT(*) FROM experiment_variants WHERE hypothesis_id = h.id) as variant_count,
    (SELECT SUM(post_count) FROM experiment_variants WHERE hypothesis_id = h.id) as total_posts,
    (SELECT SUM(total_views) FROM experiment_variants WHERE hypothesis_id = h.id) as total_views
FROM experiments e
LEFT JOIN hypotheses h ON h.experiment_id = e.id
ORDER BY e.created_at DESC, h.created_at DESC;

CREATE OR REPLACE VIEW v_pattern_leaderboard AS
SELECT 
    pattern_type,
    description,
    success_rate,
    avg_improvement,
    sample_size,
    confidence,
    times_applied,
    RANK() OVER (PARTITION BY pattern_type ORDER BY avg_improvement DESC) as rank_in_type
FROM content_patterns
WHERE is_active = TRUE
ORDER BY avg_improvement DESC;

-- =============================================================================
-- SEED SAMPLE EXPERIMENTS
-- =============================================================================

INSERT INTO experiments (name, description, goal, experiment_type, status)
VALUES 
    ('Question Hook Test', 'Test if opening with a question increases engagement', 'Improve hook retention', 'hook', 'active'),
    ('6PM Posting Test', 'Test if 6PM posts perform better than random times', 'Optimize posting schedule', 'timing', 'active'),
    ('Trending Audio Test', 'Test if trending sounds increase reach', 'Maximize viral potential', 'audio', 'draft')
ON CONFLICT DO NOTHING;

-- Add sample hypotheses
INSERT INTO hypotheses (experiment_id, statement, independent_variable, dependent_variable, success_metric, success_threshold, min_sample_size, status)
SELECT 
    e.id,
    'Videos with questions in the first 2 seconds get 40% more views',
    'Hook type (question vs statement)',
    'View count and completion rate',
    'view_count',
    1.4,
    10,
    'running'
FROM experiments e WHERE e.name = 'Question Hook Test'
ON CONFLICT DO NOTHING;

INSERT INTO hypotheses (experiment_id, statement, independent_variable, dependent_variable, success_metric, success_threshold, min_sample_size, status)
SELECT 
    e.id,
    'Posts at 6PM EST get 30% more engagement than posts at random times',
    'Post time',
    'Engagement rate',
    'engagement_rate',
    1.3,
    10,
    'pending'
FROM experiments e WHERE e.name = '6PM Posting Test'
ON CONFLICT DO NOTHING;

-- =============================================================================
-- COMMENTS
-- =============================================================================

COMMENT ON TABLE experiments IS 'Content experiments for A/B testing and optimization';
COMMENT ON TABLE hypotheses IS 'Testable hypotheses within experiments';
COMMENT ON TABLE experiment_variants IS 'Control and variant content for A/B tests';
COMMENT ON TABLE content_patterns IS 'Learned patterns from successful experiments';
COMMENT ON TABLE experiment_winners IS 'Winning content promoted to narrative builder';
