-- Growth Data Plane Enhancement Migration
-- Migration: 015_growth_data_plane
-- Created: 2026-01-25
-- Features: GDP-001 through GDP-005

-- This enhances the existing people graph with GDP-specific tables for:
-- - Email message and event tracking (Resend webhooks)
-- - Subscription tracking (Stripe integration)
-- - Deals and revenue attribution
-- - Enhanced person features for segmentation

-- =====================================================
-- EMAIL MESSAGES: Resend email tracking
-- =====================================================

CREATE TABLE IF NOT EXISTS email_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  email_id TEXT UNIQUE NOT NULL,  -- Resend email_id from webhook
  from_email TEXT NOT NULL,
  to_email TEXT NOT NULL,
  subject TEXT,
  html_body TEXT,
  text_body TEXT,
  tags JSONB,  -- For person_id mapping: {"person_id": "uuid"}
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  sent_at TIMESTAMPTZ,
  delivered_at TIMESTAMPTZ,
  bounced_at TIMESTAMPTZ,
  bounce_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_email_messages_person ON email_messages(person_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_messages_email_id ON email_messages(email_id);
CREATE INDEX IF NOT EXISTS idx_email_messages_to_email ON email_messages(to_email);
CREATE INDEX IF NOT EXISTS idx_email_messages_sent ON email_messages(sent_at DESC);

COMMENT ON TABLE email_messages IS 'Email messages sent via Resend';
COMMENT ON COLUMN email_messages.email_id IS 'Resend email_id from webhook';
COMMENT ON COLUMN email_messages.tags IS 'Resend tags including person_id mapping';

-- =====================================================
-- EMAIL EVENTS: Email engagement tracking
-- =====================================================

CREATE TABLE IF NOT EXISTS email_events (
  id BIGSERIAL PRIMARY KEY,
  email_message_id UUID REFERENCES email_messages(id) ON DELETE CASCADE,
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL CHECK (event_type IN (
    'delivered', 'opened', 'clicked', 'bounced', 'complained', 'unsubscribed'
  )),
  event_data JSONB,  -- Click URL, bounce reason, etc.
  ip_address INET,
  user_agent TEXT,
  occurred_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_email_events_message ON email_events(email_message_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_events_person ON email_events(person_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_events_type ON email_events(event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_email_events_occurred ON email_events(occurred_at DESC);

COMMENT ON TABLE email_events IS 'Email engagement events from Resend webhooks';

-- =====================================================
-- SUBSCRIPTIONS: Stripe subscription tracking
-- =====================================================

CREATE TABLE IF NOT EXISTS subscriptions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  stripe_customer_id TEXT UNIQUE,
  stripe_subscription_id TEXT UNIQUE,
  status TEXT CHECK (status IN (
    'trialing', 'active', 'past_due', 'canceled', 'unpaid', 'paused', 'incomplete'
  )),
  plan_id TEXT,
  plan_name TEXT,
  billing_period TEXT CHECK (billing_period IN ('monthly', 'yearly', 'lifetime')),
  amount_cents INTEGER,
  currency TEXT DEFAULT 'usd',
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  cancel_at TIMESTAMPTZ,
  canceled_at TIMESTAMPTZ,
  trial_start TIMESTAMPTZ,
  trial_end TIMESTAMPTZ,
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_subscriptions_person ON subscriptions(person_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_customer ON subscriptions(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_stripe_sub ON subscriptions(stripe_subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_status ON subscriptions(status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(person_id) WHERE status IN ('active', 'trialing');

COMMENT ON TABLE subscriptions IS 'Stripe subscription status per person';
COMMENT ON COLUMN subscriptions.amount_cents IS 'Subscription amount in cents (MRR)';

-- =====================================================
-- DEALS: Revenue attribution and pipeline tracking
-- =====================================================

CREATE TABLE IF NOT EXISTS deals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  deal_name TEXT,
  stage TEXT CHECK (stage IN (
    'lead', 'qualified', 'demo_scheduled', 'demo_completed', 'proposal',
    'negotiation', 'closed_won', 'closed_lost'
  )),
  value_cents INTEGER,
  currency TEXT DEFAULT 'usd',
  probability NUMERIC CHECK (probability >= 0 AND probability <= 1),
  close_date DATE,
  source TEXT,  -- 'organic', 'paid', 'referral', etc.
  attribution JSONB,  -- First/last touch attribution data
  metadata JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_deals_person ON deals(person_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_deals_stage ON deals(stage);
CREATE INDEX IF NOT EXISTS idx_deals_close_date ON deals(close_date DESC);
CREATE INDEX IF NOT EXISTS idx_deals_source ON deals(source);

COMMENT ON TABLE deals IS 'Sales pipeline and revenue attribution';
COMMENT ON COLUMN deals.attribution IS 'Attribution data (first/last touch, content touchpoints)';

-- =====================================================
-- PERSON FEATURES: Enhanced ML features for segmentation
-- =====================================================

CREATE TABLE IF NOT EXISTS person_features (
  person_id UUID PRIMARY KEY REFERENCES people(id) ON DELETE CASCADE,
  -- Engagement features
  total_emails_sent INTEGER DEFAULT 0,
  total_emails_opened INTEGER DEFAULT 0,
  total_emails_clicked INTEGER DEFAULT 0,
  email_open_rate NUMERIC,
  email_click_rate NUMERIC,
  last_email_opened_at TIMESTAMPTZ,
  last_email_clicked_at TIMESTAMPTZ,

  -- Product usage features
  total_posts_created INTEGER DEFAULT 0,
  total_posts_published INTEGER DEFAULT 0,
  total_platforms_connected INTEGER DEFAULT 0,
  platforms_connected TEXT[],
  first_post_created_at TIMESTAMPTZ,
  last_post_created_at TIMESTAMPTZ,
  first_post_published_at TIMESTAMPTZ,
  last_post_published_at TIMESTAMPTZ,

  -- Monetization features
  subscription_status TEXT,
  subscription_mrr_cents INTEGER DEFAULT 0,
  lifetime_value_cents INTEGER DEFAULT 0,
  days_to_first_purchase INTEGER,
  is_paying BOOLEAN DEFAULT FALSE,

  -- Engagement scores
  product_usage_score NUMERIC,  -- 0-1 score based on usage
  engagement_score NUMERIC,     -- 0-1 score based on email/content engagement
  likelihood_to_churn NUMERIC,  -- 0-1 predicted churn probability

  -- Computed at
  computed_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_person_features_paying ON person_features(person_id) WHERE is_paying = TRUE;
CREATE INDEX IF NOT EXISTS idx_person_features_engagement ON person_features(engagement_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_person_features_usage ON person_features(product_usage_score DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS idx_person_features_churn ON person_features(likelihood_to_churn DESC NULLS LAST);

COMMENT ON TABLE person_features IS 'Computed ML features for segmentation and predictions';
COMMENT ON COLUMN person_features.product_usage_score IS 'Computed engagement score based on product usage (0-1)';
COMMENT ON COLUMN person_features.likelihood_to_churn IS 'Predicted churn probability (0-1)';

-- =====================================================
-- ATTRIBUTION TOUCHPOINTS: Click tracking with cookies
-- =====================================================

CREATE TABLE IF NOT EXISTS attribution_touchpoints (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID REFERENCES people(id) ON DELETE SET NULL,
  session_id UUID,  -- First-party cookie session ID
  click_id TEXT UNIQUE NOT NULL,  -- /c/{click_id} redirect
  email_message_id UUID REFERENCES email_messages(id) ON DELETE SET NULL,
  destination_url TEXT NOT NULL,
  utm_source TEXT,
  utm_medium TEXT,
  utm_campaign TEXT,
  utm_content TEXT,
  utm_term TEXT,
  referrer TEXT,
  ip_address INET,
  user_agent TEXT,
  clicked_at TIMESTAMPTZ DEFAULT NOW(),
  converted_at TIMESTAMPTZ,
  conversion_value_cents INTEGER,
  metadata JSONB
);

CREATE INDEX IF NOT EXISTS idx_attribution_person ON attribution_touchpoints(person_id, clicked_at DESC);
CREATE INDEX IF NOT EXISTS idx_attribution_session ON attribution_touchpoints(session_id, clicked_at DESC);
CREATE INDEX IF NOT EXISTS idx_attribution_click_id ON attribution_touchpoints(click_id);
CREATE INDEX IF NOT EXISTS idx_attribution_email ON attribution_touchpoints(email_message_id);
CREATE INDEX IF NOT EXISTS idx_attribution_clicked ON attribution_touchpoints(clicked_at DESC);

COMMENT ON TABLE attribution_touchpoints IS 'Click redirect tracking for email → conversion attribution';
COMMENT ON COLUMN attribution_touchpoints.click_id IS 'Unique click ID for /c/{click_id} redirects';

-- =====================================================
-- EXTERNAL IDENTITY MAPPINGS: PostHog, Stripe, Meta
-- =====================================================

CREATE TABLE IF NOT EXISTS external_identities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID REFERENCES people(id) ON DELETE CASCADE,
  provider TEXT NOT NULL CHECK (provider IN ('posthog', 'stripe', 'meta_pixel', 'ga4')),
  external_id TEXT NOT NULL,
  metadata JSONB,
  linked_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(provider, external_id)
);

CREATE INDEX IF NOT EXISTS idx_external_identities_person ON external_identities(person_id);
CREATE INDEX IF NOT EXISTS idx_external_identities_provider ON external_identities(provider, external_id);

COMMENT ON TABLE external_identities IS 'Links person_id to external analytics/payment platforms';
COMMENT ON COLUMN external_identities.external_id IS 'PostHog distinct_id, Stripe customer_id, etc.';

-- =====================================================
-- UPDATE PERSON_EVENTS FOR GDP COMPLIANCE
-- =====================================================

-- Add new event types for GDP tracking
ALTER TABLE person_events DROP CONSTRAINT IF EXISTS person_events_event_type_check;
ALTER TABLE person_events ADD COLUMN IF NOT EXISTS event_source TEXT;  -- 'web', 'app', 'email', 'stripe', 'api'
ALTER TABLE person_events ADD COLUMN IF NOT EXISTS event_id TEXT;  -- External event ID (Resend, Stripe, etc.)

CREATE INDEX IF NOT EXISTS idx_person_events_source ON person_events(event_source, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_person_events_event_id ON person_events(event_id);

COMMENT ON COLUMN person_events.event_source IS 'Source of event: web, app, email, stripe, api';
COMMENT ON COLUMN person_events.event_id IS 'External event ID from source system';

-- =====================================================
-- SEGMENT ENHANCEMENTS FOR GDP
-- =====================================================

-- Add segment type and auto-refresh
ALTER TABLE segments ADD COLUMN IF NOT EXISTS segment_type TEXT CHECK (segment_type IN ('static', 'dynamic', 'behavioral'));
ALTER TABLE segments ADD COLUMN IF NOT EXISTS auto_refresh_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE segments ADD COLUMN IF NOT EXISTS refresh_frequency INTERVAL;
ALTER TABLE segments ADD COLUMN IF NOT EXISTS last_refreshed_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_segments_auto_refresh ON segments(auto_refresh_enabled, last_refreshed_at);

COMMENT ON COLUMN segments.segment_type IS 'Static (manual), dynamic (SQL), or behavioral (ML)';
COMMENT ON COLUMN segments.auto_refresh_enabled IS 'Auto-recompute segment membership';

-- =====================================================
-- ENABLE RLS ON NEW TABLES
-- =====================================================

ALTER TABLE email_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE email_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE deals ENABLE ROW LEVEL SECURITY;
ALTER TABLE person_features ENABLE ROW LEVEL SECURITY;
ALTER TABLE attribution_touchpoints ENABLE ROW LEVEL SECURITY;
ALTER TABLE external_identities ENABLE ROW LEVEL SECURITY;

-- =====================================================
-- FUNCTIONS AND TRIGGERS
-- =====================================================

-- Function to update person_features on email events
CREATE OR REPLACE FUNCTION update_person_features_email()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO person_features (person_id, total_emails_opened, last_email_opened_at, updated_at)
  VALUES (NEW.person_id, 1, NEW.occurred_at, NOW())
  ON CONFLICT (person_id) DO UPDATE SET
    total_emails_opened = person_features.total_emails_opened + 1,
    last_email_opened_at = GREATEST(person_features.last_email_opened_at, NEW.occurred_at),
    email_open_rate = CAST(person_features.total_emails_opened + 1 AS NUMERIC) / NULLIF(person_features.total_emails_sent, 0),
    updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on email_events for 'opened' events
CREATE TRIGGER trigger_update_person_features_email_opened
AFTER INSERT ON email_events
FOR EACH ROW
WHEN (NEW.event_type = 'opened')
EXECUTE FUNCTION update_person_features_email();

-- Function to update person_features on email clicks
CREATE OR REPLACE FUNCTION update_person_features_email_click()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO person_features (person_id, total_emails_clicked, last_email_clicked_at, updated_at)
  VALUES (NEW.person_id, 1, NEW.occurred_at, NOW())
  ON CONFLICT (person_id) DO UPDATE SET
    total_emails_clicked = person_features.total_emails_clicked + 1,
    last_email_clicked_at = GREATEST(person_features.last_email_clicked_at, NEW.occurred_at),
    email_click_rate = CAST(person_features.total_emails_clicked + 1 AS NUMERIC) / NULLIF(person_features.total_emails_opened, 0),
    updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on email_events for 'clicked' events
CREATE TRIGGER trigger_update_person_features_email_clicked
AFTER INSERT ON email_events
FOR EACH ROW
WHEN (NEW.event_type = 'clicked')
EXECUTE FUNCTION update_person_features_email_click();

-- Function to update subscription status in person_features
CREATE OR REPLACE FUNCTION update_person_features_subscription()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO person_features (person_id, subscription_status, subscription_mrr_cents, is_paying, updated_at)
  VALUES (NEW.person_id, NEW.status, NEW.amount_cents, NEW.status IN ('active', 'trialing'), NOW())
  ON CONFLICT (person_id) DO UPDATE SET
    subscription_status = NEW.status,
    subscription_mrr_cents = NEW.amount_cents,
    is_paying = NEW.status IN ('active', 'trialing'),
    updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger on subscriptions
CREATE TRIGGER trigger_update_person_features_subscription
AFTER INSERT OR UPDATE ON subscriptions
FOR EACH ROW
EXECUTE FUNCTION update_person_features_subscription();

-- =====================================================
-- VIEWS FOR COMMON QUERIES
-- =====================================================

-- View: Active subscribers with email engagement
CREATE OR REPLACE VIEW active_subscribers_with_engagement AS
SELECT
  p.id AS person_id,
  p.full_name,
  p.primary_email,
  s.status AS subscription_status,
  s.plan_name,
  s.amount_cents AS mrr_cents,
  pf.email_open_rate,
  pf.email_click_rate,
  pf.total_posts_created,
  pf.total_posts_published,
  pf.engagement_score,
  pf.product_usage_score
FROM people p
LEFT JOIN subscriptions s ON s.person_id = p.id AND s.status IN ('active', 'trialing')
LEFT JOIN person_features pf ON pf.person_id = p.id
WHERE s.id IS NOT NULL
ORDER BY pf.engagement_score DESC NULLS LAST;

COMMENT ON VIEW active_subscribers_with_engagement IS 'Active subscribers ranked by engagement';

-- View: High-value leads (engaged but not paying)
CREATE OR REPLACE VIEW high_value_leads AS
SELECT
  p.id AS person_id,
  p.full_name,
  p.primary_email,
  pf.total_posts_created,
  pf.total_platforms_connected,
  pf.engagement_score,
  pf.product_usage_score,
  pf.last_post_created_at
FROM people p
JOIN person_features pf ON pf.person_id = p.id
WHERE pf.is_paying = FALSE
  AND pf.product_usage_score > 0.5
  AND pf.total_posts_created >= 3
ORDER BY pf.product_usage_score DESC;

COMMENT ON VIEW high_value_leads IS 'Engaged users who are not yet paying (high conversion probability)';

-- =====================================================
-- GRANT PERMISSIONS
-- =====================================================

-- Grant access to service role (Supabase Edge Functions)
GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;

-- Grant read-only access to authenticated users (via RLS policies)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO authenticated;

-- =====================================================
-- COMPLETION
-- =====================================================

-- Log migration completion
DO $$
BEGIN
  RAISE NOTICE 'Growth Data Plane migration completed successfully';
  RAISE NOTICE 'Features: GDP-001 (Schema), GDP-002 (Person/Identity), GDP-003 (Events)';
  RAISE NOTICE 'Features: GDP-004 (Email tracking), GDP-005 (Subscription tracking)';
  RAISE NOTICE 'Next steps: Implement Resend webhook handler, Stripe webhook handler';
END $$;
