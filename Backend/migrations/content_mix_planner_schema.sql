-- Content Mix Planner Schema
-- Long-term content scheduling with mixed content types

-- Content Mix Plans table
CREATE TABLE IF NOT EXISTS content_mix_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    total_posts INTEGER DEFAULT 0,
    config JSONB,
    content_distribution JSONB,
    status VARCHAR(50) DEFAULT 'draft',
    goal_id UUID REFERENCES narrative_goals(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Content Mix Slots table
CREATE TABLE IF NOT EXISTS content_mix_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES content_mix_plans(id) ON DELETE CASCADE,
    scheduled_date DATE NOT NULL,
    scheduled_time VARCHAR(10) DEFAULT '12:00',
    platform VARCHAR(50) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    pillar VARCHAR(255),
    content_id UUID,
    content_title TEXT,
    status VARCHAR(50) DEFAULT 'planned',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_content_mix_plans_status ON content_mix_plans(status);
CREATE INDEX IF NOT EXISTS idx_content_mix_plans_dates ON content_mix_plans(start_date, end_date);
CREATE INDEX IF NOT EXISTS idx_content_mix_slots_plan ON content_mix_slots(plan_id);
CREATE INDEX IF NOT EXISTS idx_content_mix_slots_date ON content_mix_slots(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_content_mix_slots_type ON content_mix_slots(content_type);

-- Comments
COMMENT ON TABLE content_mix_plans IS 'Long-term content plans with mixed content types';
COMMENT ON TABLE content_mix_slots IS 'Individual scheduled slots within a content mix plan';
COMMENT ON COLUMN content_mix_slots.content_type IS 'ugc_caption, carousel, ai_generated, animated, raw_ugc';
