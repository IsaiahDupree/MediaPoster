-- AI Narrative Scheduling System Tables
-- Supports goal-based content scheduling with AI reasoning

-- Narrative Goals
CREATE TABLE IF NOT EXISTS narrative_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID REFERENCES workspaces(id),
    
    goal_statement TEXT NOT NULL,
    primary_cta TEXT NOT NULL DEFAULT 'follow',
    target_audience TEXT,
    
    time_horizon TEXT DEFAULT 'next_7_days',
    start_date DATE,
    end_date DATE,
    
    target_followers INTEGER,
    target_engagement_rate FLOAT,
    target_conversions INTEGER,
    
    status TEXT DEFAULT 'active',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_narrative_goals_status ON narrative_goals(status);
CREATE INDEX IF NOT EXISTS idx_narrative_goals_workspace ON narrative_goals(workspace_id);

-- Narrative Pillars
CREATE TABLE IF NOT EXISTS narrative_pillars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID REFERENCES narrative_goals(id) ON DELETE CASCADE,
    
    name TEXT NOT NULL,
    description TEXT,
    pillar_type TEXT NOT NULL DEFAULT 'value',
    color TEXT DEFAULT '#3b82f6',
    keywords TEXT[],
    
    target_percentage FLOAT DEFAULT 20.0,
    min_posts_per_week INTEGER DEFAULT 1,
    max_posts_per_week INTEGER DEFAULT 5,
    priority INTEGER DEFAULT 5,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_narrative_pillars_goal ON narrative_pillars(goal_id);

-- Scheduling Constraints
CREATE TABLE IF NOT EXISTS scheduling_constraints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID REFERENCES narrative_goals(id) ON DELETE CASCADE,
    
    enabled_platforms TEXT[] DEFAULT ARRAY['tiktok', 'instagram'],
    max_posts_per_day INTEGER DEFAULT 3,
    min_posts_per_day INTEGER DEFAULT 1,
    max_posts_per_platform_per_day INTEGER DEFAULT 2,
    posting_windows JSONB,
    blackout_dates DATE[],
    timezone TEXT DEFAULT 'America/New_York',
    
    min_pre_social_score INTEGER DEFAULT 60,
    require_analysis BOOLEAN DEFAULT TRUE,
    max_same_pillar_consecutive INTEGER DEFAULT 2,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheduling_constraints_goal ON scheduling_constraints(goal_id);

-- Weekly Schedules (AI-generated plans)
CREATE TABLE IF NOT EXISTS weekly_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID REFERENCES narrative_goals(id),
    
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    
    total_posts INTEGER DEFAULT 0,
    pillar_distribution JSONB,
    platform_distribution JSONB,
    
    reasoning_chain JSONB,
    justification TEXT,
    
    status TEXT DEFAULT 'draft',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_weekly_schedules_goal ON weekly_schedules(goal_id);
CREATE INDEX IF NOT EXISTS idx_weekly_schedules_status ON weekly_schedules(status);
CREATE INDEX IF NOT EXISTS idx_weekly_schedules_dates ON weekly_schedules(week_start, week_end);

-- Schedule Slots (individual posts in a plan)
CREATE TABLE IF NOT EXISTS schedule_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID REFERENCES weekly_schedules(id) ON DELETE CASCADE,
    
    video_id UUID,
    video_title TEXT,
    platform TEXT NOT NULL,
    scheduled_date DATE NOT NULL,
    scheduled_time TEXT NOT NULL,
    pillar TEXT,
    selection_reason TEXT,
    expected_engagement FLOAT,
    
    actual_post_id UUID,
    actual_engagement FLOAT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_schedule_slots_schedule ON schedule_slots(schedule_id);
CREATE INDEX IF NOT EXISTS idx_schedule_slots_date ON schedule_slots(scheduled_date);

-- Schedule Performance (weekly metrics)
CREATE TABLE IF NOT EXISTS schedule_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID REFERENCES weekly_schedules(id),
    
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    
    total_posts INTEGER DEFAULT 0,
    total_views INTEGER DEFAULT 0,
    total_likes INTEGER DEFAULT 0,
    total_comments INTEGER DEFAULT 0,
    total_shares INTEGER DEFAULT 0,
    avg_engagement_rate FLOAT DEFAULT 0.0,
    
    followers_gained INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    goal_progress_pct FLOAT DEFAULT 0.0,
    
    pillar_performance JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_schedule_performance_schedule ON schedule_performance(schedule_id);
CREATE INDEX IF NOT EXISTS idx_schedule_performance_week ON schedule_performance(week_start);

-- Learnings (accumulated insights from performance)
CREATE TABLE IF NOT EXISTS learnings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    goal_id UUID REFERENCES narrative_goals(id),
    
    learning_type TEXT NOT NULL,
    insight TEXT NOT NULL,
    confidence FLOAT DEFAULT 0.0,
    action TEXT,
    
    source_schedule_id UUID REFERENCES weekly_schedules(id),
    applied BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_learnings_goal ON learnings(goal_id);
CREATE INDEX IF NOT EXISTS idx_learnings_applied ON learnings(applied);

-- Comments
COMMENT ON TABLE narrative_goals IS 'Defines overarching content strategy goals';
COMMENT ON TABLE narrative_pillars IS 'Content themes/pillars that support goals';
COMMENT ON TABLE scheduling_constraints IS 'Rules and limits for content scheduling';
COMMENT ON TABLE weekly_schedules IS 'AI-generated weekly content plans with reasoning';
COMMENT ON TABLE schedule_slots IS 'Individual posts within a weekly schedule';
COMMENT ON TABLE schedule_performance IS 'Performance tracking for completed schedules';
COMMENT ON TABLE learnings IS 'AI-generated insights from schedule performance';
