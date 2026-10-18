-- Migration 002: Indexes, Audit Log, Full-Text Search, Materialized Views
-- ACTP fine-grained database features

-- ─── Composite Indexes ───────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_perf_logs_creative_metric_time
  ON actp_performance_logs (creative_id, metric_type, measured_at DESC);

CREATE INDEX IF NOT EXISTS idx_organic_posts_platform_status
  ON actp_organic_posts (platform, status);

CREATE INDEX IF NOT EXISTS idx_ad_deployments_status_platform
  ON actp_ad_deployments (status, platform);

CREATE INDEX IF NOT EXISTS idx_creatives_round_winner
  ON actp_creatives (round_id, is_winner);

CREATE INDEX IF NOT EXISTS idx_creatives_campaign_score
  ON actp_creatives (campaign_id, organic_score DESC NULLS LAST);

CREATE INDEX IF NOT EXISTS idx_rounds_campaign_status
  ON actp_rounds (campaign_id, status);

CREATE INDEX IF NOT EXISTS idx_winner_selections_round_rank
  ON actp_winner_selections (round_id, rank);

-- ─── Unique Constraints ──────────────────────────────────
ALTER TABLE actp_organic_posts
  ADD CONSTRAINT uq_organic_post_creative_platform
  UNIQUE (creative_id, platform)
  -- Allow re-publish after deletion
  ;

-- ─── Soft Delete on Campaigns ────────────────────────────
ALTER TABLE actp_campaigns ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ DEFAULT NULL;
CREATE INDEX IF NOT EXISTS idx_campaigns_deleted ON actp_campaigns (deleted_at) WHERE deleted_at IS NULL;

-- ─── Campaign Tags ───────────────────────────────────────
ALTER TABLE actp_campaigns ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;
CREATE INDEX IF NOT EXISTS idx_campaigns_tags ON actp_campaigns USING GIN (tags);

-- ─── Full-Text Search on Creatives ───────────────────────
ALTER TABLE actp_creatives ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;

CREATE OR REPLACE FUNCTION actp_creatives_search_update() RETURNS trigger AS $$
BEGIN
  NEW.search_vector := to_tsvector('english',
    coalesce(NEW.hook, '') || ' ' ||
    coalesce(NEW.cta, '') || ' ' ||
    coalesce(NEW.angle, '') || ' ' ||
    coalesce(NEW.script, '')
  );
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_creatives_search ON actp_creatives;
CREATE TRIGGER trg_creatives_search
  BEFORE INSERT OR UPDATE OF hook, cta, angle, script ON actp_creatives
  FOR EACH ROW EXECUTE FUNCTION actp_creatives_search_update();

CREATE INDEX IF NOT EXISTS idx_creatives_fts ON actp_creatives USING GIN (search_vector);

-- ─── Creative Tags ───────────────────────────────────────
ALTER TABLE actp_creatives ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;
CREATE INDEX IF NOT EXISTS idx_creatives_tags ON actp_creatives USING GIN (tags);

-- ─── Audit Log Table ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS actp_audit_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  entity_type TEXT NOT NULL,          -- 'campaign', 'round', 'creative', 'ad_deployment'
  entity_id UUID NOT NULL,
  action TEXT NOT NULL,                -- 'created', 'status_changed', 'updated', 'deleted'
  old_value JSONB,
  new_value JSONB,
  actor TEXT DEFAULT 'system',         -- user_id or 'system' or 'scheduler'
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_entity ON actp_audit_log (entity_type, entity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_action ON actp_audit_log (action, created_at DESC);

-- Trigger: audit campaign status changes
CREATE OR REPLACE FUNCTION actp_audit_campaign_status() RETURNS trigger AS $$
BEGIN
  IF OLD.status IS DISTINCT FROM NEW.status THEN
    INSERT INTO actp_audit_log (entity_type, entity_id, action, old_value, new_value)
    VALUES ('campaign', NEW.id, 'status_changed',
            jsonb_build_object('status', OLD.status),
            jsonb_build_object('status', NEW.status));
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_campaign ON actp_campaigns;
CREATE TRIGGER trg_audit_campaign
  AFTER UPDATE OF status ON actp_campaigns
  FOR EACH ROW EXECUTE FUNCTION actp_audit_campaign_status();

-- Trigger: audit round status changes
CREATE OR REPLACE FUNCTION actp_audit_round_status() RETURNS trigger AS $$
BEGIN
  IF OLD.status IS DISTINCT FROM NEW.status THEN
    INSERT INTO actp_audit_log (entity_type, entity_id, action, old_value, new_value)
    VALUES ('round', NEW.id, 'status_changed',
            jsonb_build_object('status', OLD.status),
            jsonb_build_object('status', NEW.status));
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_round ON actp_rounds;
CREATE TRIGGER trg_audit_round
  AFTER UPDATE OF status ON actp_rounds
  FOR EACH ROW EXECUTE FUNCTION actp_audit_round_status();

-- ─── Materialized View: Campaign Summaries ───────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS actp_campaign_summary AS
SELECT
  c.id AS campaign_id,
  c.name,
  c.status,
  c.mode,
  c.created_at,
  COUNT(DISTINCT r.id) AS total_rounds,
  COUNT(DISTINCT cr.id) AS total_creatives,
  COUNT(DISTINCT cr.id) FILTER (WHERE cr.is_winner = true) AS total_winners,
  COALESCE(SUM(ad.spend_cents), 0) AS total_spend_cents,
  MAX(cr.organic_score) AS best_organic_score,
  MAX(cr.ad_score) AS best_ad_score,
  MAX(r.round_number) AS latest_round
FROM actp_campaigns c
LEFT JOIN actp_rounds r ON r.campaign_id = c.id
LEFT JOIN actp_creatives cr ON cr.campaign_id = c.id
LEFT JOIN actp_ad_deployments ad ON ad.creative_id = cr.id
WHERE c.deleted_at IS NULL
GROUP BY c.id, c.name, c.status, c.mode, c.created_at;

CREATE UNIQUE INDEX IF NOT EXISTS idx_campaign_summary_id ON actp_campaign_summary (campaign_id);

-- ─── Materialized View: Creative Leaderboard ─────────────
CREATE MATERIALIZED VIEW IF NOT EXISTS actp_creative_leaderboard AS
SELECT
  cr.id AS creative_id,
  cr.campaign_id,
  cr.round_id,
  cr.hook,
  cr.angle,
  cr.generation_source,
  cr.is_winner,
  cr.organic_score,
  cr.ad_score,
  COALESCE(cr.organic_score, 0) * 0.4 + COALESCE(cr.ad_score, 0) * 0.6 AS composite_score,
  cr.created_at,
  c.name AS campaign_name
FROM actp_creatives cr
JOIN actp_campaigns c ON c.id = cr.campaign_id
WHERE c.deleted_at IS NULL
ORDER BY composite_score DESC;

-- ─── Data Retention Function ─────────────────────────────
CREATE OR REPLACE FUNCTION actp_cleanup_old_logs(retention_days INT DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
  deleted_count INTEGER;
BEGIN
  DELETE FROM actp_performance_logs
  WHERE measured_at < NOW() - (retention_days || ' days')::interval;
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ─── Campaign Templates Table ────────────────────────────
CREATE TABLE IF NOT EXISTS actp_campaign_templates (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  description TEXT,
  config JSONB NOT NULL DEFAULT '{}'::jsonb,
  angles JSONB DEFAULT '[]'::jsonb,
  target_audience JSONB DEFAULT '{}'::jsonb,
  mode TEXT DEFAULT 'offer',
  tags JSONB DEFAULT '[]'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── Winning Patterns Table ──────────────────────────────
CREATE TABLE IF NOT EXISTS actp_winning_patterns (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id UUID REFERENCES actp_campaigns(id),
  creative_id UUID REFERENCES actp_creatives(id),
  pattern_type TEXT NOT NULL,          -- 'hook', 'cta', 'angle', 'style', 'composite'
  pattern_data JSONB NOT NULL,
  score FLOAT,
  niche TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_winning_patterns_type ON actp_winning_patterns (pattern_type, score DESC);
CREATE INDEX IF NOT EXISTS idx_winning_patterns_niche ON actp_winning_patterns (niche);

-- ─── Metric Snapshots Table ──────────────────────────────
CREATE TABLE IF NOT EXISTS actp_metric_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  creative_id UUID NOT NULL REFERENCES actp_creatives(id) ON DELETE CASCADE,
  platform TEXT NOT NULL,
  snapshot_hour INT NOT NULL,          -- hours since post: 1, 3, 6, 12, 24, 48
  metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
  captured_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_snapshots_creative_platform_hour
  ON actp_metric_snapshots (creative_id, platform, snapshot_hour);

-- ─── Scheduled Tasks Table ───────────────────────────────
CREATE TABLE IF NOT EXISTS actp_scheduled_tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_type TEXT NOT NULL,             -- 'collect_metrics', 'select_winners', 'refresh_views'
  entity_type TEXT NOT NULL,           -- 'round', 'campaign', 'creative'
  entity_id UUID NOT NULL,
  scheduled_at TIMESTAMPTZ NOT NULL,
  executed_at TIMESTAMPTZ,
  status TEXT DEFAULT 'pending',       -- 'pending', 'running', 'completed', 'failed'
  result JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scheduled_tasks_pending
  ON actp_scheduled_tasks (scheduled_at) WHERE status = 'pending';

-- ─── Dead Letter Queue ───────────────────────────────────
CREATE TABLE IF NOT EXISTS actp_dead_letter_queue (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  job_type TEXT NOT NULL,
  payload JSONB NOT NULL,
  error TEXT,
  retry_count INT DEFAULT 0,
  max_retries INT DEFAULT 3,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  last_attempted_at TIMESTAMPTZ
);

-- ─── Webhook Configurations ──────────────────────────────
CREATE TABLE IF NOT EXISTS actp_webhooks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  url TEXT NOT NULL,
  events JSONB NOT NULL DEFAULT '[]'::jsonb,  -- ['campaign.started', 'round.completed', 'winner.selected']
  secret TEXT,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ─── RLS on new tables ───────────────────────────────────
ALTER TABLE actp_audit_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE actp_campaign_templates ENABLE ROW LEVEL SECURITY;
ALTER TABLE actp_winning_patterns ENABLE ROW LEVEL SECURITY;
ALTER TABLE actp_metric_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE actp_scheduled_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE actp_dead_letter_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE actp_webhooks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on audit_log" ON actp_audit_log FOR ALL USING (true);
CREATE POLICY "Service role full access on templates" ON actp_campaign_templates FOR ALL USING (true);
CREATE POLICY "Service role full access on patterns" ON actp_winning_patterns FOR ALL USING (true);
CREATE POLICY "Service role full access on snapshots" ON actp_metric_snapshots FOR ALL USING (true);
CREATE POLICY "Service role full access on tasks" ON actp_scheduled_tasks FOR ALL USING (true);
CREATE POLICY "Service role full access on dlq" ON actp_dead_letter_queue FOR ALL USING (true);
CREATE POLICY "Service role full access on webhooks" ON actp_webhooks FOR ALL USING (true);

-- Refresh materialized views function
CREATE OR REPLACE FUNCTION actp_refresh_views() RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW CONCURRENTLY actp_campaign_summary;
  REFRESH MATERIALIZED VIEW actp_creative_leaderboard;
END;
$$ LANGUAGE plpgsql;
