-- Content Ops Entities Migration (Phase 2)
-- Adds Brand, Offer, ICP, Template, Touchpoint, and Shortlink tables

-- =====================================================
-- BRANDS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS brands (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_brands_is_active ON brands(is_active);

-- =====================================================
-- OFFERS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,

    title TEXT NOT NULL,
    description TEXT,
    offer_type VARCHAR(50), -- product, service, lead_magnet, content, event

    -- Offer details
    landing_page_url TEXT,
    cta_text TEXT,
    terms TEXT,

    -- Pricing (optional)
    price NUMERIC(10, 2),
    currency VARCHAR(3) DEFAULT 'USD',

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    priority INTEGER DEFAULT 0,
    valid_from TIMESTAMP WITH TIME ZONE,
    valid_until TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_offers_brand_id ON offers(brand_id);
CREATE INDEX idx_offers_is_active ON offers(is_active);

-- =====================================================
-- ICPs (Ideal Customer Profiles) TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS icps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name TEXT NOT NULL,
    description TEXT,

    -- Demographics
    age_range VARCHAR(50),
    location TEXT[],
    job_titles TEXT[],
    company_size VARCHAR(50),

    -- Psychographics
    pain_points TEXT[],
    goals TEXT[],
    interests TEXT[],
    objections TEXT[],

    -- Awareness level (default for this ICP)
    default_awareness_level VARCHAR(50), -- unaware, problem_aware, solution_aware, product_aware, most_aware

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_icps_is_active ON icps(is_active);

-- =====================================================
-- CONTENT TEMPLATES TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS content_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,

    -- Template identity
    name TEXT NOT NULL,
    description TEXT,
    template_type VARCHAR(50), -- post, email, dm, ad, story

    -- Template content
    prompt_text TEXT NOT NULL,
    required_variables TEXT[],

    -- FATE weights (must sum to ~1.0)
    fate_focus FLOAT NOT NULL,
    fate_authority FLOAT NOT NULL,
    fate_tribe FLOAT NOT NULL,
    fate_emotion FLOAT NOT NULL,

    -- Awareness level
    awareness_level VARCHAR(50) NOT NULL, -- unaware, problem_aware, solution_aware, product_aware, most_aware

    -- CTA configuration
    cta_strength VARCHAR(20), -- none, soft, direct
    cta_template TEXT,

    -- Performance tracking
    usage_count INTEGER DEFAULT 0,
    avg_reward_score FLOAT DEFAULT 0.0,
    performance_label VARCHAR(20), -- winner, promising, average, loser

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_templates_brand_id ON content_templates(brand_id);
CREATE INDEX idx_templates_awareness_level ON content_templates(awareness_level);
CREATE INDEX idx_templates_performance ON content_templates(performance_label);

-- =====================================================
-- TOUCHPOINTS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS touchpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Traceback chain
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,
    offer_id UUID NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    icp_id UUID REFERENCES icps(id) ON DELETE CASCADE,
    template_id UUID REFERENCES content_templates(id) ON DELETE CASCADE,

    -- Touchpoint details
    channel VARCHAR(50) NOT NULL,
    message_type VARCHAR(50),

    -- Content reference
    posted_content_id UUID, -- References posted_content when that table exists
    shortlink TEXT,

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
    published_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_touchpoints_offer_id ON touchpoints(offer_id);
CREATE INDEX idx_touchpoints_icp_id ON touchpoints(icp_id);
CREATE INDEX idx_touchpoints_template_id ON touchpoints(template_id);
CREATE INDEX idx_touchpoints_channel ON touchpoints(channel);
CREATE INDEX idx_touchpoints_published_at ON touchpoints(published_at);

-- =====================================================
-- SHORTLINKS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS shortlinks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Shortlink details
    short_code VARCHAR(20) UNIQUE NOT NULL,
    destination_url TEXT NOT NULL,

    -- Attribution chain
    touchpoint_id UUID REFERENCES touchpoints(id) ON DELETE CASCADE,
    offer_id UUID REFERENCES offers(id) ON DELETE CASCADE,
    template_id UUID REFERENCES content_templates(id) ON DELETE SET NULL,
    icp_id UUID REFERENCES icps(id) ON DELETE SET NULL,

    -- UTM parameters
    utm_source VARCHAR(100),
    utm_medium VARCHAR(100),
    utm_campaign VARCHAR(200),
    utm_content VARCHAR(200),
    utm_term VARCHAR(200),

    -- Click tracking
    click_count INTEGER DEFAULT 0,
    last_clicked_at TIMESTAMP WITH TIME ZONE,

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_shortlinks_short_code ON shortlinks(short_code);
CREATE INDEX idx_shortlinks_touchpoint_id ON shortlinks(touchpoint_id);
CREATE INDEX idx_shortlinks_offer_id ON shortlinks(offer_id);

-- =====================================================
-- UPDATE TRIGGERS FOR updated_at
-- =====================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_brands_updated_at BEFORE UPDATE ON brands
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_offers_updated_at BEFORE UPDATE ON offers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_icps_updated_at BEFORE UPDATE ON icps
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_templates_updated_at BEFORE UPDATE ON content_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_touchpoints_updated_at BEFORE UPDATE ON touchpoints
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_shortlinks_updated_at BEFORE UPDATE ON shortlinks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- COMMENTS
-- =====================================================

-- =====================================================
-- CREATOR PROFILES TABLE (ENTITY-004)
-- =====================================================

CREATE TABLE IF NOT EXISTS creator_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

    -- Profile details
    name VARCHAR(200) NOT NULL,
    description TEXT,

    -- Voice rules
    voice_tone TEXT[], -- ["casual", "educational", "witty"]
    voice_style TEXT[], -- ["first_person", "storytelling", "data_driven"]

    -- Banned phrases
    banned_phrases TEXT[], -- ["click here", "limited time only"]
    banned_patterns TEXT[], -- ["ALL CAPS", "excessive emojis"]

    -- Tone descriptors
    tone_descriptors JSONB, -- {"formality": "casual", "humor": "high", "technical": "medium"}

    -- Content preferences
    preferred_length_min INTEGER,
    preferred_length_max INTEGER,
    preferred_formats TEXT[], -- ["thread", "single_post", "carousel"]

    -- Language and style
    language VARCHAR(10) DEFAULT 'en',
    emoji_policy VARCHAR(50), -- "none", "minimal", "moderate", "heavy"
    hashtag_policy VARCHAR(50), -- "none", "end_only", "inline", "both"

    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_creator_profiles_workspace_id ON creator_profiles(workspace_id);
CREATE INDEX idx_creator_profiles_is_active ON creator_profiles(is_active);

CREATE TRIGGER update_creator_profiles_updated_at BEFORE UPDATE ON creator_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- CONTENT PLANS TABLE (ENTITY-005)
-- =====================================================

CREATE TABLE IF NOT EXISTS content_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    creator_profile_id UUID REFERENCES creator_profiles(id) ON DELETE CASCADE,

    -- Plan details
    name VARCHAR(200) NOT NULL,
    description TEXT,

    -- Time range
    week_start_date DATE NOT NULL,
    week_end_date DATE NOT NULL,

    -- Plan strategy
    target_posts_per_day INTEGER DEFAULT 3,
    awareness_distribution JSONB, -- {"unaware": 0.1, "problem_aware": 0.4, ...}
    fate_emphasis JSONB, -- {"focus": 0.3, "authority": 0.25, ...}

    -- Status
    status VARCHAR(50) DEFAULT 'draft', -- draft, active, executing, completed, archived
    execution_progress FLOAT DEFAULT 0.0, -- 0.0 to 1.0

    -- Learnings from execution
    learnings JSONB, -- {"winning_templates": [], "losing_templates": [], ...}
    avg_performance_score FLOAT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_content_plans_workspace_id ON content_plans(workspace_id);
CREATE INDEX idx_content_plans_creator_profile_id ON content_plans(creator_profile_id);
CREATE INDEX idx_content_plans_week_start_date ON content_plans(week_start_date);
CREATE INDEX idx_content_plans_status ON content_plans(status);

CREATE TRIGGER update_content_plans_updated_at BEFORE UPDATE ON content_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- PROMPT RUNS TABLE (ENTITY-006)
-- =====================================================

CREATE TABLE IF NOT EXISTS prompt_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Full traceback chain
    content_plan_id UUID REFERENCES content_plans(id) ON DELETE CASCADE,
    content_slot_id UUID, -- FK added later to avoid circular dependency
    template_id UUID NOT NULL REFERENCES content_templates(id) ON DELETE CASCADE,
    offer_id UUID NOT NULL REFERENCES offers(id) ON DELETE CASCADE,
    icp_id UUID REFERENCES icps(id) ON DELETE CASCADE,
    brand_id UUID REFERENCES brands(id) ON DELETE CASCADE,

    -- Template snapshot (in case template changes)
    template_snapshot JSONB,

    -- Input variables
    input_variables JSONB NOT NULL, -- {"pain": "...", "outcome": "...", ...}

    -- Prompt details
    prompt_text TEXT NOT NULL,
    system_prompt TEXT,

    -- AI model details
    model_name VARCHAR(100), -- "gpt-4o", "claude-3-opus", etc.
    temperature FLOAT DEFAULT 0.7,
    max_tokens INTEGER,

    -- Generated output
    generated_text TEXT NOT NULL,
    generated_variants JSONB, -- Multiple variants if requested
    selected_variant_index INTEGER DEFAULT 0,

    -- QA Gate results
    qa_status VARCHAR(50), -- "pending", "passed", "failed", "needs_review"
    qa_flags JSONB, -- {"banned_phrase": false, "spam_pattern": false, ...}
    qa_reviewed_by VARCHAR(100),
    qa_reviewed_at TIMESTAMP WITH TIME ZONE,

    -- Publication details
    published_touchpoint_id UUID REFERENCES touchpoints(id) ON DELETE SET NULL,
    published_at TIMESTAMP WITH TIME ZONE,

    -- Performance (copied from touchpoint after metrics collection)
    engagement_rate FLOAT,
    click_rate FLOAT,
    reward_score FLOAT,
    performance_label VARCHAR(50), -- "winner", "loser", "neutral", "insufficient_data"

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_prompt_runs_content_plan_id ON prompt_runs(content_plan_id);
CREATE INDEX idx_prompt_runs_template_id ON prompt_runs(template_id);
CREATE INDEX idx_prompt_runs_offer_id ON prompt_runs(offer_id);
CREATE INDEX idx_prompt_runs_published_at ON prompt_runs(published_at);
CREATE INDEX idx_prompt_runs_performance_label ON prompt_runs(performance_label);
CREATE INDEX idx_prompt_runs_qa_status ON prompt_runs(qa_status);

CREATE TRIGGER update_prompt_runs_updated_at BEFORE UPDATE ON prompt_runs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- CONTENT SLOTS TABLE
-- =====================================================

CREATE TABLE IF NOT EXISTS content_slots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_plan_id UUID NOT NULL REFERENCES content_plans(id) ON DELETE CASCADE,

    -- Slot details
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Awareness × FATE targeting
    awareness_level VARCHAR(50), -- unaware, problem_aware, solution_aware, product_aware, most_aware
    fate_primary VARCHAR(50), -- focus, authority, tribe, emotion

    -- Routing
    offer_id UUID REFERENCES offers(id) ON DELETE SET NULL,
    icp_id UUID REFERENCES icps(id) ON DELETE SET NULL,
    template_id UUID REFERENCES content_templates(id) ON DELETE SET NULL,

    -- Platform targeting
    platforms TEXT[], -- ["twitter", "instagram", "tiktok"]
    content_format VARCHAR(50), -- "post", "thread", "video", "carousel"

    -- Execution status
    status VARCHAR(50) DEFAULT 'pending', -- pending, generating, qa_review, approved, published, failed
    executed_at TIMESTAMP WITH TIME ZONE,
    touchpoint_id UUID REFERENCES touchpoints(id) ON DELETE SET NULL,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_content_slots_content_plan_id ON content_slots(content_plan_id);
CREATE INDEX idx_content_slots_scheduled_time ON content_slots(scheduled_time);
CREATE INDEX idx_content_slots_status ON content_slots(status);
CREATE INDEX idx_content_slots_awareness_level ON content_slots(awareness_level);

CREATE TRIGGER update_content_slots_updated_at BEFORE UPDATE ON content_slots
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =====================================================
-- ADD FOREIGN KEY CONSTRAINTS (after both tables exist)
-- =====================================================

ALTER TABLE prompt_runs
ADD CONSTRAINT fk_prompt_runs_content_slot
FOREIGN KEY (content_slot_id) REFERENCES content_slots(id) ON DELETE SET NULL;

-- =====================================================
-- COMMENTS
-- =====================================================

COMMENT ON TABLE brands IS 'Brand entities for Content Ops - represents companies/products';
COMMENT ON TABLE offers IS 'Offers linked to brands - products/services/CTAs';
COMMENT ON TABLE icps IS 'Ideal Customer Profiles - target audience personas';
COMMENT ON TABLE content_templates IS 'Content templates with FATE weights and awareness levels';
COMMENT ON TABLE touchpoints IS 'Links Brand → Offer → ICP → Template with attribution';
COMMENT ON TABLE shortlinks IS 'Shortlink tracking for full attribution chain';
COMMENT ON TABLE creator_profiles IS 'Creator voice rules, banned phrases, tone descriptors (ENTITY-004)';
COMMENT ON TABLE content_plans IS 'Weekly content plans with Awareness × FATE strategy (ENTITY-005)';
COMMENT ON TABLE content_slots IS 'Individual time slots in a content plan';
COMMENT ON TABLE prompt_runs IS 'Full traceback of template → prompt → offer → ICP → slot (ENTITY-006)';
