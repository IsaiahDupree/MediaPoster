-- ============================================================================
-- Experiments Scheduler Schema
-- AI-Powered Content Experimentation & Learning System
-- ============================================================================

-- Add origin tracking to scheduled_posts
ALTER TABLE scheduled_posts 
ADD COLUMN IF NOT EXISTS origin_type VARCHAR(20) DEFAULT 'user',
ADD COLUMN IF NOT EXISTS experiment_id UUID,
ADD COLUMN IF NOT EXISTS hypothesis_id UUID,
ADD COLUMN IF NOT EXISTS variant VARCHAR(20);

-- Create index for origin-based queries
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_origin ON scheduled_posts(origin_type);
CREATE INDEX IF NOT EXISTS idx_scheduled_posts_experiment ON scheduled_posts(experiment_id);

-- ============================================================================
-- Experiments Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    goal TEXT NOT NULL,
    
    -- Status tracking
    status VARCHAR(20) DEFAULT 'draft',  -- draft, active, paused, completed, cancelled
    
    -- Timing
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    
    -- Configuration
    success_criteria JSONB DEFAULT '{}',
    target_accounts TEXT[],  -- Which accounts to use for testing
    resource_types TEXT[],   -- ugc, ai_generated, edited, etc.
    
    -- Results
    results JSONB DEFAULT '{}',
    learnings TEXT,
    winner_video_ids UUID[],
    
    -- Metadata
    created_by VARCHAR(50) DEFAULT 'system',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- Hypotheses Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS hypotheses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id) ON DELETE CASCADE,
    
    -- The hypothesis
    statement TEXT NOT NULL,
    
    -- Variables
    independent_variable VARCHAR(255),  -- What we're changing
    dependent_variable VARCHAR(255),    -- What we're measuring
    control_description TEXT,           -- Baseline approach
    variant_description TEXT,           -- Test approach
    
    -- Success criteria
    success_metric VARCHAR(100),        -- view_count, engagement_rate, etc.
    success_threshold FLOAT,            -- e.g., 1.4 means 40% improvement
    min_sample_size INT DEFAULT 10,
    
    -- Results
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, passed, failed, inconclusive
    confidence_level FLOAT,
    actual_improvement FLOAT,
    control_avg FLOAT,
    variant_avg FLOAT,
    p_value FLOAT,
    learnings TEXT,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- Content Patterns (Learnings Database)
-- ============================================================================
CREATE TABLE IF NOT EXISTS content_patterns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Pattern classification
    pattern_type VARCHAR(50),  -- hook, format, timing, caption, audio, angle
    category VARCHAR(100),
    
    -- The pattern
    name VARCHAR(255),
    description TEXT,
    
    -- Performance metrics
    success_rate FLOAT,
    avg_improvement FLOAT,
    confidence FLOAT,
    
    -- Evidence
    supporting_experiments UUID[],
    sample_size INT DEFAULT 0,
    
    -- Application guidance
    when_to_use TEXT,
    when_to_avoid TEXT,
    best_for_pillars TEXT[],
    
    -- Evolution tracking
    first_discovered TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_validated TIMESTAMP WITH TIME ZONE,
    times_applied INT DEFAULT 0,
    times_successful INT DEFAULT 0,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    promoted_to_framework BOOLEAN DEFAULT FALSE
);

-- ============================================================================
-- Content Frameworks (Proven Templates)
-- ============================================================================
CREATE TABLE IF NOT EXISTS content_frameworks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Framework info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Structure
    structure JSONB,  -- Step-by-step approach
    
    -- Application
    best_for TEXT[],          -- Content types this works for
    pillars TEXT[],           -- Narrative pillars this aligns with
    platforms TEXT[],         -- Platforms this works on
    
    -- Performance
    avg_performance_lift FLOAT,
    times_validated INT DEFAULT 0,
    success_rate FLOAT,
    
    -- Source patterns
    source_patterns UUID[],
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- ============================================================================
-- Experiment Winners (Promotion Candidates)
-- ============================================================================
CREATE TABLE IF NOT EXISTS experiment_winners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source
    experiment_id UUID REFERENCES experiments(id),
    hypothesis_id UUID REFERENCES hypotheses(id),
    post_id UUID,
    video_id UUID,
    
    -- Performance
    performance_metrics JSONB,  -- views, engagement, retention, etc.
    ranking_score FLOAT,        -- Composite score for comparison
    
    -- Promotion status
    winner_type VARCHAR(50),    -- 'winner', 'winner_of_winners', 'promoted'
    promoted_to_narrative BOOLEAN DEFAULT FALSE,
    promoted_at TIMESTAMP WITH TIME ZONE,
    
    -- Narrative performance (after promotion)
    narrative_performance JSONB,
    
    -- Metadata
    detected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- Experiment Agent Actions Log
-- ============================================================================
CREATE TABLE IF NOT EXISTS experiment_agent_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    experiment_id UUID REFERENCES experiments(id),
    
    -- Action details
    action_type VARCHAR(100) NOT NULL,
    action_params JSONB,
    
    -- Execution
    status VARCHAR(20) DEFAULT 'pending',  -- pending, executing, completed, failed
    result JSONB,
    error_message TEXT,
    
    -- Reasoning
    reasoning TEXT,           -- Why the agent took this action
    expected_outcome TEXT,    -- What the agent expected
    
    -- Timing
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    executed_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- Indexes for Performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_experiments_status ON experiments(status);
CREATE INDEX IF NOT EXISTS idx_hypotheses_experiment ON hypotheses(experiment_id);
CREATE INDEX IF NOT EXISTS idx_hypotheses_status ON hypotheses(status);
CREATE INDEX IF NOT EXISTS idx_patterns_type ON content_patterns(pattern_type);
CREATE INDEX IF NOT EXISTS idx_winners_experiment ON experiment_winners(experiment_id);
CREATE INDEX IF NOT EXISTS idx_winners_promoted ON experiment_winners(promoted_to_narrative);
CREATE INDEX IF NOT EXISTS idx_agent_actions_experiment ON experiment_agent_actions(experiment_id);

-- ============================================================================
-- Update Trigger
-- ============================================================================
CREATE OR REPLACE FUNCTION update_experiments_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER experiments_updated_at
    BEFORE UPDATE ON experiments
    FOR EACH ROW
    EXECUTE FUNCTION update_experiments_updated_at();

CREATE TRIGGER hypotheses_updated_at
    BEFORE UPDATE ON hypotheses
    FOR EACH ROW
    EXECUTE FUNCTION update_experiments_updated_at();

-- ============================================================================
-- Comments
-- ============================================================================
COMMENT ON TABLE experiments IS 'AI-powered content experiments for testing hypotheses';
COMMENT ON TABLE hypotheses IS 'Testable hypotheses within experiments';
COMMENT ON TABLE content_patterns IS 'Learned patterns from successful experiments';
COMMENT ON TABLE content_frameworks IS 'Proven content creation frameworks';
COMMENT ON TABLE experiment_winners IS 'High-performing content candidates for narrative promotion';
COMMENT ON TABLE experiment_agent_actions IS 'Log of AI agent actions during experiments';
