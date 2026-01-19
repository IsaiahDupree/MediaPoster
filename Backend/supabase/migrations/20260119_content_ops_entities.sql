-- Content Ops Entities Migration
-- Phase 2: Brand, Offer, ICP, ContentTemplate, Touchpoint
-- Date: 2026-01-19

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- BRANDS TABLE (ENTITY-001)
-- ============================================================================
CREATE TABLE IF NOT EXISTS brands (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT,
    logo_url TEXT,
    website_url TEXT,

    -- Brand voice and values
    brand_voice JSONB, -- {tone: str, keywords: List[str], avoid: List[str]}
    core_values TEXT[],
    target_audience TEXT,

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for brands
CREATE INDEX IF NOT EXISTS idx_brands_is_active ON brands(is_active);
CREATE INDEX IF NOT EXISTS idx_brands_created_at ON brands(created_at DESC);

-- ============================================================================
-- OFFERS TABLE (ENTITY-002)
-- ============================================================================
CREATE TABLE IF NOT EXISTS offers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,

    title TEXT NOT NULL,
    description TEXT,
    offer_type VARCHAR(50), -- product, service, lead_magnet, content, event

    -- Offer details
    landing_page_url TEXT,
    cta_text TEXT, -- Default CTA for this offer
    terms TEXT, -- Terms and conditions

    -- Pricing (optional)
    price NUMERIC(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0, -- Higher = more priority
    valid_from TIMESTAMPTZ,
    valid_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for offers
CREATE INDEX IF NOT EXISTS idx_offers_brand_id ON offers(brand_id);
CREATE INDEX IF NOT EXISTS idx_offers_is_active ON offers(is_active);
CREATE INDEX IF NOT EXISTS idx_offers_priority ON offers(priority DESC);
CREATE INDEX IF NOT EXISTS idx_offers_valid_until ON offers(valid_until);

-- ============================================================================
-- ICPs TABLE (ENTITY-003)
-- ============================================================================
CREATE TABLE IF NOT EXISTS icps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    name TEXT NOT NULL, -- e.g., "Solo Founder", "Enterprise CMO"
    description TEXT,

    -- Demographics
    age_range VARCHAR(50), -- e.g., "25-34", "35-44"
    location TEXT[], -- Countries/regions
    job_titles TEXT[],
    company_size VARCHAR(50), -- e.g., "1-10", "11-50", "51-200"

    -- Psychographics
    pain_points TEXT[],
    goals TEXT[],
    interests TEXT[],
    objections TEXT[],

    -- Awareness level (default for this ICP)
    default_awareness_level VARCHAR(50), -- unaware, problem_aware, solution_aware, product_aware, most_aware

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for icps
CREATE INDEX IF NOT EXISTS idx_icps_is_active ON icps(is_active);
CREATE INDEX IF NOT EXISTS idx_icps_awareness_level ON icps(default_awareness_level);

-- ============================================================================
-- CONTENT_TEMPLATES TABLE (TPL-001 to TPL-008)
-- ============================================================================
CREATE TABLE IF NOT EXISTS content_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,

    -- Template identity
    name TEXT NOT NULL,
    description TEXT,
    template_type VARCHAR(50), -- post, email, dm, ad, story

    -- Template content
    prompt_text TEXT NOT NULL, -- AI prompt with {variable} placeholders
    required_variables TEXT[], -- Extracted variable names

    -- FATE weights (must sum to ~1.0)
    fate_focus FLOAT NOT NULL,
    fate_authority FLOAT NOT NULL,
    fate_tribe FLOAT NOT NULL,
    fate_emotion FLOAT NOT NULL,

    -- Awareness level
    awareness_level VARCHAR(50) NOT NULL, -- unaware, problem_aware, solution_aware, product_aware, most_aware

    -- CTA configuration
    cta_strength VARCHAR(20), -- none, soft, direct
    cta_template TEXT, -- Optional CTA template

    -- Performance tracking
    usage_count INTEGER DEFAULT 0,
    avg_reward_score FLOAT DEFAULT 0.0,
    performance_label VARCHAR(20), -- winner, promising, average, loser, untested

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT, -- User ID or "system"
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Validation constraint: FATE weights should sum to ~1.0 (allow 0.95-1.05 range)
    CONSTRAINT check_fate_weights CHECK (
        (fate_focus + fate_authority + fate_tribe + fate_emotion) BETWEEN 0.95 AND 1.05
    )
);

-- Indexes for content_templates
CREATE INDEX IF NOT EXISTS idx_templates_brand_id ON content_templates(brand_id);
CREATE INDEX IF NOT EXISTS idx_templates_awareness_level ON content_templates(awareness_level);
CREATE INDEX IF NOT EXISTS idx_templates_performance ON content_templates(performance_label);
CREATE INDEX IF NOT EXISTS idx_templates_is_active ON content_templates(is_active);
CREATE INDEX IF NOT EXISTS idx_templates_avg_reward ON content_templates(avg_reward_score DESC);

-- ============================================================================
-- TOUCHPOINTS TABLE (ENTITY-004)
-- ============================================================================
CREATE TABLE IF NOT EXISTS touchpoints (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Traceback chain
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    offer_id UUID NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    icp_id UUID REFERENCES icps(id) ON DELETE CASCADE,
    template_id UUID REFERENCES content_templates(id) ON DELETE CASCADE,

    -- Touchpoint details
    channel VARCHAR(50) NOT NULL, -- twitter, instagram, email, dm, ad
    message_type VARCHAR(50), -- post, story, comment, dm, email

    -- Content reference
    posted_content_id UUID REFERENCES posted_content(id) ON DELETE SET NULL,
    shortlink TEXT, -- Attribution shortlink

    -- Performance metrics (copied from posted_content on checkback)
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    reposts INTEGER DEFAULT 0,

    -- Calculated scores
    engagement_rate FLOAT DEFAULT 0.0,
    click_rate FLOAT DEFAULT 0.0,
    reward_score FLOAT DEFAULT 0.0,

    -- Metadata
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for touchpoints
CREATE INDEX IF NOT EXISTS idx_touchpoints_offer_id ON touchpoints(offer_id);
CREATE INDEX IF NOT EXISTS idx_touchpoints_icp_id ON touchpoints(icp_id);
CREATE INDEX IF NOT EXISTS idx_touchpoints_template_id ON touchpoints(template_id);
CREATE INDEX IF NOT EXISTS idx_touchpoints_channel ON touchpoints(channel);
CREATE INDEX IF NOT EXISTS idx_touchpoints_published_at ON touchpoints(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_touchpoints_reward_score ON touchpoints(reward_score DESC);

-- ============================================================================
-- UPDATED_AT TRIGGERS
-- ============================================================================

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for all tables
CREATE TRIGGER update_brands_updated_at BEFORE UPDATE ON brands
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_offers_updated_at BEFORE UPDATE ON offers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_icps_updated_at BEFORE UPDATE ON icps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_content_templates_updated_at BEFORE UPDATE ON content_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_touchpoints_updated_at BEFORE UPDATE ON touchpoints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SAMPLE DATA (Optional - for development)
-- ============================================================================

-- Sample Brand
INSERT INTO brands (name, description, core_values, target_audience)
VALUES (
    'MediaPoster',
    'AI-powered content automation platform',
    ARRAY['Innovation', 'Automation', 'Quality'],
    'Solo founders and small teams looking to scale their social media presence'
) ON CONFLICT DO NOTHING;

-- Get the brand_id for subsequent inserts
DO $$
DECLARE
    brand_uuid UUID;
BEGIN
    SELECT id INTO brand_uuid FROM brands WHERE name = 'MediaPoster' LIMIT 1;

    IF brand_uuid IS NOT NULL THEN
        -- Sample Offer
        INSERT INTO offers (brand_id, title, description, offer_type, cta_text, landing_page_url, priority)
        VALUES (
            brand_uuid,
            'Free Trial - 7 Days',
            'Try MediaPoster free for 7 days, no credit card required',
            'lead_magnet',
            'Start Your Free Trial',
            'https://mediaposter.ai/trial',
            100
        ) ON CONFLICT DO NOTHING;

        -- Sample ICP
        INSERT INTO icps (
            name,
            description,
            age_range,
            job_titles,
            pain_points,
            goals,
            default_awareness_level
        )
        VALUES (
            'Solo Founder',
            'Indie hackers building products alone',
            '25-44',
            ARRAY['Founder', 'CEO', 'Solo Developer'],
            ARRAY['No time for social media', 'Inconsistent posting', 'Low engagement'],
            ARRAY['Build audience', 'Drive traffic', 'Grow revenue'],
            'problem_aware'
        ) ON CONFLICT DO NOTHING;

        -- Sample Template
        INSERT INTO content_templates (
            brand_id,
            name,
            description,
            template_type,
            prompt_text,
            required_variables,
            fate_focus,
            fate_authority,
            fate_tribe,
            fate_emotion,
            awareness_level,
            cta_strength,
            cta_template,
            performance_label
        )
        VALUES (
            brand_uuid,
            'Problem-Aware Hook',
            'Hook that surfaces a painful problem',
            'post',
            'You''re spending {hours} hours/week on {task}, but seeing {result}. Here''s why: {reason}',
            ARRAY['hours', 'task', 'result', 'reason'],
            0.4,  -- Focus (hook)
            0.3,  -- Authority (mechanism)
            0.2,  -- Tribe (relatability)
            0.1,  -- Emotion (pain)
            'problem_aware',
            'soft',
            'Want to fix this? Here''s how →',
            'untested'
        ) ON CONFLICT DO NOTHING;
    END IF;
END $$;

-- ============================================================================
-- GRANTS (Adjust based on your Supabase role configuration)
-- ============================================================================

-- Grant permissions to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON brands TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON offers TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON icps TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON content_templates TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON touchpoints TO authenticated;

-- Grant permissions to service role (for backend API)
GRANT ALL ON brands TO service_role;
GRANT ALL ON offers TO service_role;
GRANT ALL ON icps TO service_role;
GRANT ALL ON content_templates TO service_role;
GRANT ALL ON touchpoints TO service_role;

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE brands IS 'Brand entities representing companies/products (ENTITY-001)';
COMMENT ON TABLE offers IS 'Offers/CTAs linked to brands (ENTITY-002)';
COMMENT ON TABLE icps IS 'Ideal Customer Profiles - target audience personas (ENTITY-003)';
COMMENT ON TABLE content_templates IS 'AI content templates with FATE weights and awareness levels (TPL-001 to TPL-008)';
COMMENT ON TABLE touchpoints IS 'Attribution chain: Brand → Offer → ICP → Template (ENTITY-004)';

COMMENT ON COLUMN content_templates.fate_focus IS 'FATE Framework: Focus weight (novelty, hook) - must sum to ~1.0';
COMMENT ON COLUMN content_templates.fate_authority IS 'FATE Framework: Authority weight (credibility, proof) - must sum to ~1.0';
COMMENT ON COLUMN content_templates.fate_tribe IS 'FATE Framework: Tribe weight (identity, us-vs-them) - must sum to ~1.0';
COMMENT ON COLUMN content_templates.fate_emotion IS 'FATE Framework: Emotion weight (story, visceral buy-in) - must sum to ~1.0';
COMMENT ON COLUMN touchpoints.reward_score IS 'Calculated reward: 1.0*z(click_rate) + 0.8*z(reply_rate) + 0.6*z(repost_rate) + 0.4*z(like_rate)';
