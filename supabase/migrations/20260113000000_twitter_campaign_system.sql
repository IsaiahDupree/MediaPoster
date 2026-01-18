-- Twitter Campaign Automation System
-- Supports 60 tweets/day across multiple products with awareness stage cycling
-- Tracks URLs, analytics, and content performance

-- =============================================================================
-- PRODUCTS TABLE - Products being promoted
-- =============================================================================
CREATE TABLE IF NOT EXISTS campaign_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    description TEXT,
    website_url TEXT,
    tagline TEXT,
    key_features JSONB DEFAULT '[]',
    target_audience TEXT,
    competitors JSONB DEFAULT '[]',
    voice_style TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- AWARENESS STAGES - 5 stages of customer awareness
-- =============================================================================
CREATE TYPE awareness_stage AS ENUM (
    'unaware',           -- Don't know they have a problem
    'problem_aware',     -- Know the problem, not the solution
    'solution_aware',    -- Know solutions exist, comparing options
    'product_aware',     -- Know your product, need convincing
    'most_aware'         -- Ready to buy, just need a push
);

-- =============================================================================
-- TWEET TEMPLATES - AI-generated tweet templates by stage
-- =============================================================================
CREATE TABLE IF NOT EXISTS tweet_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES campaign_products(id) ON DELETE CASCADE,
    awareness_stage awareness_stage NOT NULL,
    content_type TEXT NOT NULL, -- 'hook', 'authority', 'story', 'emotional', 'cta'
    template_text TEXT NOT NULL,
    variables JSONB DEFAULT '{}', -- Placeholders like {product_name}, {benefit}
    performance_score FLOAT DEFAULT 0,
    times_used INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- SCHEDULED TWEETS - Queue of tweets to be posted
-- =============================================================================
CREATE TABLE IF NOT EXISTS scheduled_tweets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES campaign_products(id) ON DELETE CASCADE,
    template_id UUID REFERENCES tweet_templates(id) ON DELETE SET NULL,
    awareness_stage awareness_stage NOT NULL,
    content_type TEXT NOT NULL,
    tweet_text TEXT NOT NULL,
    scheduled_time TIMESTAMPTZ NOT NULL,
    blotato_account_id TEXT NOT NULL,
    status TEXT DEFAULT 'scheduled', -- scheduled, publishing, posted, failed
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- POSTED TWEETS - Tracking posted tweets for analytics
-- =============================================================================
CREATE TABLE IF NOT EXISTS posted_tweets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scheduled_tweet_id UUID REFERENCES scheduled_tweets(id) ON DELETE SET NULL,
    product_id UUID REFERENCES campaign_products(id) ON DELETE CASCADE,
    template_id UUID REFERENCES tweet_templates(id) ON DELETE SET NULL,
    awareness_stage awareness_stage NOT NULL,
    content_type TEXT NOT NULL,
    tweet_text TEXT NOT NULL,
    
    -- Platform tracking
    platform_post_id TEXT,
    platform_url TEXT,
    blotato_account_id TEXT,
    blotato_submission_id TEXT,
    
    -- Timestamps
    posted_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Analytics (updated periodically)
    impressions INTEGER DEFAULT 0,
    engagements INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    retweets INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    profile_visits INTEGER DEFAULT 0,
    
    -- Calculated scores
    engagement_rate FLOAT DEFAULT 0,
    performance_score FLOAT DEFAULT 0,
    
    -- Check-back tracking
    last_analytics_check TIMESTAMPTZ,
    analytics_check_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- CAMPAIGN CYCLES - Track which stage/type we're on
-- =============================================================================
CREATE TABLE IF NOT EXISTS campaign_cycles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES campaign_products(id) ON DELETE CASCADE,
    current_awareness_stage awareness_stage DEFAULT 'unaware',
    current_content_type TEXT DEFAULT 'hook',
    stage_tweet_count INTEGER DEFAULT 0,
    type_tweet_count INTEGER DEFAULT 0,
    total_tweets_today INTEGER DEFAULT 0,
    last_tweet_at TIMESTAMPTZ,
    last_stage_rotation TIMESTAMPTZ,
    last_type_rotation TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(product_id)
);

-- =============================================================================
-- USER WRITING STYLE - Capture user's voice
-- =============================================================================
CREATE TABLE IF NOT EXISTS user_writing_styles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT DEFAULT 'default',
    sample_tweets JSONB DEFAULT '[]', -- Sample tweets to learn from
    tone_keywords JSONB DEFAULT '[]', -- Words that capture the tone
    avoid_words JSONB DEFAULT '[]', -- Words to avoid
    style_description TEXT,
    generated_style_prompt TEXT, -- AI-generated style guide
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

-- =============================================================================
-- ANALYTICS CHECKBACK PERIODS
-- =============================================================================
CREATE TABLE IF NOT EXISTS analytics_checkbacks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    posted_tweet_id UUID REFERENCES posted_tweets(id) ON DELETE CASCADE,
    check_period TEXT NOT NULL, -- '1h', '6h', '24h', '48h', '7d'
    checked_at TIMESTAMPTZ DEFAULT NOW(),
    impressions INTEGER DEFAULT 0,
    engagements INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    retweets INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    engagement_rate FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- CONTENT PERFORMANCE INSIGHTS
-- =============================================================================
CREATE TABLE IF NOT EXISTS content_performance_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID REFERENCES campaign_products(id) ON DELETE CASCADE,
    period_start TIMESTAMPTZ NOT NULL,
    period_end TIMESTAMPTZ NOT NULL,
    
    -- Performance by stage
    best_awareness_stage awareness_stage,
    worst_awareness_stage awareness_stage,
    
    -- Performance by content type
    best_content_type TEXT,
    worst_content_type TEXT,
    
    -- Top performing tweets
    top_tweet_ids JSONB DEFAULT '[]',
    
    -- Insights
    insights_json JSONB DEFAULT '{}',
    recommendations JSONB DEFAULT '[]',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- INDEXES
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_scheduled_tweets_time ON scheduled_tweets(scheduled_time) WHERE status = 'scheduled';
CREATE INDEX IF NOT EXISTS idx_scheduled_tweets_product ON scheduled_tweets(product_id);
CREATE INDEX IF NOT EXISTS idx_posted_tweets_product ON posted_tweets(product_id);
CREATE INDEX IF NOT EXISTS idx_posted_tweets_stage ON posted_tweets(awareness_stage);
CREATE INDEX IF NOT EXISTS idx_posted_tweets_posted_at ON posted_tweets(posted_at DESC);
CREATE INDEX IF NOT EXISTS idx_posted_tweets_platform_url ON posted_tweets(platform_url) WHERE platform_url IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_tweet_templates_product_stage ON tweet_templates(product_id, awareness_stage);
CREATE INDEX IF NOT EXISTS idx_analytics_checkbacks_tweet ON analytics_checkbacks(posted_tweet_id);

-- =============================================================================
-- SEED DEFAULT PRODUCTS
-- =============================================================================
INSERT INTO campaign_products (name, slug, description, website_url, tagline, key_features, target_audience, voice_style)
VALUES 
(
    'Everreach',
    'everreach',
    'Personal CRM with AI features for managing relationships and growing your network',
    'https://everreach.app',
    'Your AI-powered personal CRM',
    '["AI-powered contact insights", "Relationship timeline", "Smart reminders", "Network growth tracking", "Integration with email & social"]',
    'Professionals, entrepreneurs, networkers, sales people, anyone who values relationships',
    'Professional yet friendly, knowledgeable, helpful, solution-oriented'
),
(
    'BlankLogo',
    'blanklogo',
    'AI watermark remover for Sora, Runway, Pika, TikTok and other AI-generated videos',
    'https://blanklogo.app',
    'Remove watermarks in 60 seconds',
    '["60-second processing", "No subscription required", "Browser-based", "Lossless quality", "Batch processing", "All AI platforms supported"]',
    'Content creators, video editors, social media managers, AI video enthusiasts, agencies',
    'Direct, confident, creator-focused, problem-solving'
),
(
    'Apple App Kit',
    'apple-app-kit',
    'Fully working paywall template using Superwall built on Expo, deployed on App Store',
    'https://github.com/isaiahdupree/apple-app-kit',
    'Ship your iOS app with a working paywall in minutes',
    '["Superwall integration", "Expo ready", "App Store approved", "Copy & paste implementation", "Revenue tracking", "A/B testing ready"]',
    'iOS developers, indie hackers, app entrepreneurs, React Native developers',
    'Technical but accessible, developer-friendly, practical, no-nonsense'
)
ON CONFLICT (slug) DO UPDATE SET
    description = EXCLUDED.description,
    website_url = EXCLUDED.website_url,
    tagline = EXCLUDED.tagline,
    key_features = EXCLUDED.key_features,
    target_audience = EXCLUDED.target_audience,
    voice_style = EXCLUDED.voice_style,
    updated_at = NOW();

-- Initialize campaign cycles for each product
INSERT INTO campaign_cycles (product_id)
SELECT id FROM campaign_products
ON CONFLICT (product_id) DO NOTHING;

-- =============================================================================
-- FUNCTIONS
-- =============================================================================

-- Function to rotate awareness stage
CREATE OR REPLACE FUNCTION rotate_awareness_stage(current_stage awareness_stage)
RETURNS awareness_stage AS $$
BEGIN
    CASE current_stage
        WHEN 'unaware' THEN RETURN 'problem_aware';
        WHEN 'problem_aware' THEN RETURN 'solution_aware';
        WHEN 'solution_aware' THEN RETURN 'product_aware';
        WHEN 'product_aware' THEN RETURN 'most_aware';
        WHEN 'most_aware' THEN RETURN 'unaware';
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- Function to rotate content type
CREATE OR REPLACE FUNCTION rotate_content_type(current_type TEXT)
RETURNS TEXT AS $$
BEGIN
    CASE current_type
        WHEN 'hook' THEN RETURN 'authority';
        WHEN 'authority' THEN RETURN 'story';
        WHEN 'story' THEN RETURN 'emotional';
        WHEN 'emotional' THEN RETURN 'cta';
        WHEN 'cta' THEN RETURN 'hook';
        ELSE RETURN 'hook';
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update timestamps
CREATE OR REPLACE FUNCTION update_campaign_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_campaign_products_timestamp
    BEFORE UPDATE ON campaign_products
    FOR EACH ROW EXECUTE FUNCTION update_campaign_timestamp();

CREATE TRIGGER update_tweet_templates_timestamp
    BEFORE UPDATE ON tweet_templates
    FOR EACH ROW EXECUTE FUNCTION update_campaign_timestamp();

CREATE TRIGGER update_scheduled_tweets_timestamp
    BEFORE UPDATE ON scheduled_tweets
    FOR EACH ROW EXECUTE FUNCTION update_campaign_timestamp();

CREATE TRIGGER update_posted_tweets_timestamp
    BEFORE UPDATE ON posted_tweets
    FOR EACH ROW EXECUTE FUNCTION update_campaign_timestamp();

CREATE TRIGGER update_campaign_cycles_timestamp
    BEFORE UPDATE ON campaign_cycles
    FOR EACH ROW EXECUTE FUNCTION update_campaign_timestamp();
