-- =============================================================================
-- NARRATIVE BUILDER & EXPERIMENTS ARCHITECTURE - Phase 1 Migration
-- =============================================================================
-- This migration implements the foundation for the two-brain architecture:
-- - Account roles (MAINLINE vs EXPERIMENT_ARM)
-- - Knowledge base tables (rules, templates, playbooks)
-- - Schedule origin tracking
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. ACCOUNT ROLES
-- -----------------------------------------------------------------------------
-- Add account_role to social_accounts to separate mainline from experiment accounts

ALTER TABLE social_accounts 
ADD COLUMN IF NOT EXISTS account_role VARCHAR(20) DEFAULT 'MAINLINE';

-- Add check constraint for valid roles
DO $$ 
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'social_accounts_role_check'
  ) THEN
    ALTER TABLE social_accounts 
    ADD CONSTRAINT social_accounts_role_check 
    CHECK (account_role IN ('MAINLINE', 'EXPERIMENT_ARM', 'ARCHIVE', 'SEED'));
  END IF;
END $$;

-- Index for filtering by role
CREATE INDEX IF NOT EXISTS idx_social_accounts_role ON social_accounts(account_role);

-- -----------------------------------------------------------------------------
-- 2. KNOWLEDGE BASE - RULES
-- -----------------------------------------------------------------------------
-- Rules are learnings produced by experiments and consumed by narrative builder

CREATE TABLE IF NOT EXISTS kb_rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID,
  
  -- Rule classification
  rule_type VARCHAR(50) NOT NULL, -- 'hook', 'format', 'timing', 'caption', 'cta', 'thumbnail'
  name VARCHAR(255),
  description TEXT,
  
  -- Conditions for when this rule applies
  conditions JSONB NOT NULL DEFAULT '{}'::jsonb,
  -- Example: {"platform": ["tiktok", "instagram"], "format": ["vertical"], "length_range": [15, 30]}
  
  -- The recommendation/action
  recommendation TEXT NOT NULL,
  
  -- Statistical metrics
  expected_lift DECIMAL(5,2), -- e.g., 12.5 means +12.5%
  confidence DECIMAL(3,2), -- 0.00 to 1.00
  sample_size INTEGER,
  p_value DECIMAL(6,4),
  
  -- Validation tracking
  last_validated TIMESTAMPTZ,
  validation_count INTEGER DEFAULT 0,
  
  -- Source tracking
  source_experiment_id UUID,
  source_experiment_ids UUID[] DEFAULT '{}',
  
  -- Status
  status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'deprecated', 'testing')),
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kb_rules_type ON kb_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_kb_rules_status ON kb_rules(status);
CREATE INDEX IF NOT EXISTS idx_kb_rules_conditions ON kb_rules USING gin(conditions);

-- -----------------------------------------------------------------------------
-- 3. KNOWLEDGE BASE - TEMPLATES
-- -----------------------------------------------------------------------------
-- Reusable content templates (hooks, captions, CTAs)

CREATE TABLE IF NOT EXISTS kb_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID,
  
  -- Template classification
  template_type VARCHAR(50) NOT NULL, -- 'hook', 'caption', 'cta', 'thumbnail_text'
  name VARCHAR(255) NOT NULL,
  description TEXT,
  
  -- The actual template content
  content TEXT NOT NULL,
  -- Example: "Are you still struggling with {{pain_point}}? Here's what changed everything..."
  
  -- Variables that can be substituted
  variables JSONB DEFAULT '[]'::jsonb,
  -- Example: ["pain_point", "solution", "time_frame"]
  
  -- Performance tracking
  performance_score DECIMAL(5,2),
  usage_count INTEGER DEFAULT 0,
  avg_engagement_rate DECIMAL(5,2),
  
  -- Conditions for when to use
  best_for JSONB DEFAULT '{}'::jsonb,
  -- Example: {"niche": ["business", "productivity"], "tone": "conversational"}
  
  -- Source tracking
  source_experiment_id UUID,
  
  -- Status
  status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'deprecated', 'testing')),
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kb_templates_type ON kb_templates(template_type);
CREATE INDEX IF NOT EXISTS idx_kb_templates_status ON kb_templates(status);

-- -----------------------------------------------------------------------------
-- 4. KNOWLEDGE BASE - CONSTRAINTS
-- -----------------------------------------------------------------------------
-- Fatigue thresholds, cooldowns, frequency limits

CREATE TABLE IF NOT EXISTS kb_constraints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID,
  
  -- Constraint classification
  constraint_type VARCHAR(50) NOT NULL, -- 'fatigue', 'cooldown', 'frequency', 'timing'
  name VARCHAR(255) NOT NULL,
  description TEXT,
  
  -- Scope of the constraint
  scope VARCHAR(50) NOT NULL, -- 'platform', 'topic', 'format', 'template', 'global'
  scope_value VARCHAR(255), -- e.g., 'tiktok', 'productivity', 'vertical'
  
  -- Threshold values
  threshold_value DECIMAL(10,2) NOT NULL,
  threshold_unit VARCHAR(50), -- 'posts', 'hours', 'days', 'percent'
  window_days INTEGER, -- Time window for the constraint
  
  -- Priority (higher = more important)
  priority INTEGER DEFAULT 50,
  
  -- Status
  status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'disabled')),
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kb_constraints_type ON kb_constraints(constraint_type);
CREATE INDEX IF NOT EXISTS idx_kb_constraints_scope ON kb_constraints(scope, scope_value);

-- -----------------------------------------------------------------------------
-- 5. KNOWLEDGE BASE - PLAYBOOKS
-- -----------------------------------------------------------------------------
-- Collections of rules, templates, and constraints for specific use cases

CREATE TABLE IF NOT EXISTS kb_playbooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID,
  
  -- Playbook info
  name VARCHAR(255) NOT NULL,
  description TEXT,
  use_case VARCHAR(50), -- 'launch_week', 'evergreen', 'viral_response', 'growth_sprint'
  
  -- Components (references to other KB items)
  rule_ids UUID[] DEFAULT '{}',
  template_ids UUID[] DEFAULT '{}',
  constraint_ids UUID[] DEFAULT '{}',
  
  -- Additional configuration
  config JSONB DEFAULT '{}'::jsonb,
  
  -- Usage tracking
  usage_count INTEGER DEFAULT 0,
  last_used_at TIMESTAMPTZ,
  
  -- Status
  status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'archived', 'draft')),
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kb_playbooks_use_case ON kb_playbooks(use_case);

-- -----------------------------------------------------------------------------
-- 6. NARRATIVE GOALS
-- -----------------------------------------------------------------------------
-- Goals for the narrative builder to optimize towards

CREATE TABLE IF NOT EXISTS narrative_goals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID,
  
  -- Goal info
  name VARCHAR(255) NOT NULL,
  description TEXT,
  goal_type VARCHAR(50) NOT NULL, -- 'campaign', 'series', 'funnel_stage', 'growth'
  
  -- Target metrics
  target_metric VARCHAR(100), -- e.g., 'followers', 'engagement_rate', 'saves'
  target_value DECIMAL(15,2),
  current_value DECIMAL(15,2),
  
  -- Time bounds
  start_date DATE,
  end_date DATE,
  
  -- Content requirements
  content_pillars JSONB DEFAULT '[]'::jsonb, -- Topics/themes to cover
  platform_mix JSONB DEFAULT '{}'::jsonb, -- e.g., {"tiktok": 0.5, "instagram": 0.3, "youtube": 0.2}
  posting_cadence JSONB DEFAULT '{}'::jsonb, -- e.g., {"min_per_day": 1, "max_per_day": 3}
  
  -- Linked playbook
  playbook_id UUID REFERENCES kb_playbooks(id),
  
  -- Priority
  priority INTEGER DEFAULT 50,
  
  -- Status
  status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'paused', 'completed', 'archived')),
  progress_percent DECIMAL(5,2) DEFAULT 0,
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_narrative_goals_status ON narrative_goals(status);
CREATE INDEX IF NOT EXISTS idx_narrative_goals_type ON narrative_goals(goal_type);

-- -----------------------------------------------------------------------------
-- 7. SCHEDULE ORIGIN TRACKING
-- -----------------------------------------------------------------------------
-- Track where scheduled posts originated from

-- Check if scheduled_posts table exists and add columns
DO $$
BEGIN
  -- Add to scheduled_posts if it exists
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'scheduled_posts') THEN
    ALTER TABLE scheduled_posts 
    ADD COLUMN IF NOT EXISTS origin VARCHAR(20) DEFAULT 'MANUAL',
    ADD COLUMN IF NOT EXISTS policy_id UUID,
    ADD COLUMN IF NOT EXISTS goal_id UUID,
    ADD COLUMN IF NOT EXISTS experiment_id UUID,
    ADD COLUMN IF NOT EXISTS experiment_arm VARCHAR(50),
    ADD COLUMN IF NOT EXISTS correlation_id UUID,
    ADD COLUMN IF NOT EXISTS idempotency_key VARCHAR(255);
    
    -- Add check constraint for origin
    IF NOT EXISTS (
      SELECT 1 FROM pg_constraint WHERE conname = 'scheduled_posts_origin_check'
    ) THEN
      ALTER TABLE scheduled_posts 
      ADD CONSTRAINT scheduled_posts_origin_check 
      CHECK (origin IN ('NARRATIVE', 'EXPERIMENT', 'MANUAL', 'SYSTEM'));
    END IF;
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 8. EXPERIMENT ENHANCEMENTS
-- -----------------------------------------------------------------------------
-- Enhance experiments table with account role tracking

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'experiments') THEN
    ALTER TABLE experiments 
    ADD COLUMN IF NOT EXISTS account_role VARCHAR(20) DEFAULT 'EXPERIMENT_ARM',
    ADD COLUMN IF NOT EXISTS knowledge_rule_ids UUID[] DEFAULT '{}';
  END IF;
END $$;

-- -----------------------------------------------------------------------------
-- 9. HYDRATION SNAPSHOTS
-- -----------------------------------------------------------------------------
-- Store periodic state snapshots for decision engines

CREATE TABLE IF NOT EXISTS hydration_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID,
  account_group_id UUID,
  
  -- Snapshot scope
  scope VARCHAR(50) NOT NULL, -- 'mainline', 'experiment', 'all'
  
  -- The actual state data
  state_data JSONB NOT NULL DEFAULT '{}'::jsonb,
  -- Contains: content_metrics, fatigue_scores, topic_coverage, etc.
  
  -- Feature vectors for ML
  features JSONB DEFAULT '{}'::jsonb,
  
  -- Metadata
  snapshot_type VARCHAR(50) DEFAULT 'scheduled', -- 'scheduled', 'triggered', 'manual'
  triggered_by VARCHAR(100),
  
  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days')
);

CREATE INDEX IF NOT EXISTS idx_hydration_snapshots_scope ON hydration_snapshots(scope);
CREATE INDEX IF NOT EXISTS idx_hydration_snapshots_created ON hydration_snapshots(created_at DESC);

-- Cleanup old snapshots (keep last 7 days)
CREATE INDEX IF NOT EXISTS idx_hydration_snapshots_expires ON hydration_snapshots(expires_at);

-- -----------------------------------------------------------------------------
-- 10. UPDATE TRIGGERS
-- -----------------------------------------------------------------------------

-- Auto-update updated_at timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply to new tables
DO $$
DECLARE
  t TEXT;
BEGIN
  FOR t IN SELECT unnest(ARRAY['kb_rules', 'kb_templates', 'kb_constraints', 'kb_playbooks', 'narrative_goals'])
  LOOP
    EXECUTE format('
      DROP TRIGGER IF EXISTS update_%s_updated_at ON %s;
      CREATE TRIGGER update_%s_updated_at
        BEFORE UPDATE ON %s
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();
    ', t, t, t, t);
  END LOOP;
END $$;

-- -----------------------------------------------------------------------------
-- 11. SEED DEFAULT CONSTRAINTS
-- -----------------------------------------------------------------------------

INSERT INTO kb_constraints (constraint_type, name, scope, scope_value, threshold_value, threshold_unit, window_days, description)
VALUES 
  ('fatigue', 'Topic Fatigue - 3 days', 'topic', NULL, 1, 'posts', 3, 'Don''t repeat the same topic within 3 days'),
  ('fatigue', 'Template Fatigue - 7 days', 'template', NULL, 2, 'posts', 7, 'Don''t use the same template more than twice per week'),
  ('frequency', 'Max Daily Posts - TikTok', 'platform', 'tiktok', 3, 'posts', 1, 'Maximum 3 posts per day on TikTok'),
  ('frequency', 'Max Daily Posts - Instagram', 'platform', 'instagram', 2, 'posts', 1, 'Maximum 2 posts per day on Instagram'),
  ('cooldown', 'Post Cooldown - 4 hours', 'global', NULL, 4, 'hours', 1, 'Minimum 4 hours between posts on same platform'),
  ('timing', 'Prime Time Window', 'global', NULL, 18, 'hours', 1, 'Prefer posting between 6PM-9PM local time')
ON CONFLICT DO NOTHING;

-- -----------------------------------------------------------------------------
-- DONE
-- -----------------------------------------------------------------------------
