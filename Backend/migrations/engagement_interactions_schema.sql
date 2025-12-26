-- Engagement Interactions Schema
-- Tracks all automated engagement actions (comments, likes, follows, DMs)

CREATE TABLE IF NOT EXISTS engagement_interactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_username VARCHAR(255) NOT NULL,
    interaction_type VARCHAR(50) NOT NULL, -- 'comment', 'like', 'follow', 'dm', 'unfollow'
    target_url TEXT,
    target_username VARCHAR(255),
    content TEXT, -- Comment text, DM content, etc.
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    platform VARCHAR(50) DEFAULT 'instagram',
    session_id UUID, -- Links to engagement session
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_engagement_account ON engagement_interactions(account_username);
CREATE INDEX IF NOT EXISTS idx_engagement_type ON engagement_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_engagement_target ON engagement_interactions(target_url);
CREATE INDEX IF NOT EXISTS idx_engagement_created ON engagement_interactions(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_engagement_platform ON engagement_interactions(platform);

-- Engagement Sessions table
CREATE TABLE IF NOT EXISTS engagement_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_username VARCHAR(255) NOT NULL,
    platform VARCHAR(50) DEFAULT 'instagram',
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    status VARCHAR(50) DEFAULT 'running', -- 'running', 'completed', 'failed', 'paused'
    config JSONB DEFAULT '{}', -- hashtags, target users, max posts, etc.
    results JSONB DEFAULT '{}', -- posts_interacted, comments_posted, etc.
    errors JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sessions_account ON engagement_sessions(account_username);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON engagement_sessions(status);
CREATE INDEX IF NOT EXISTS idx_sessions_platform ON engagement_sessions(platform);

-- Comment templates table (for fallback when AI unavailable)
CREATE TABLE IF NOT EXISTS comment_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR(100), -- 'general', 'fitness', 'travel', 'food', etc.
    template TEXT NOT NULL,
    hashtag_triggers TEXT[], -- Hashtags that trigger this template
    usage_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert some default templates
INSERT INTO comment_templates (category, template, hashtag_triggers) VALUES
    ('general', 'This is exactly what I needed to see today! 🙌', ARRAY['inspiration', 'motivation']),
    ('general', 'Love the energy in this! 🔥', ARRAY['vibes', 'energy']),
    ('general', 'So inspiring, thanks for sharing!', ARRAY['inspire', 'journey']),
    ('fitness', 'The dedication here is unreal 💪', ARRAY['fitness', 'gym', 'workout']),
    ('travel', 'Adding this to my bucket list! ✈️', ARRAY['travel', 'wanderlust', 'explore']),
    ('food', 'This looks absolutely delicious! 🤤', ARRAY['food', 'foodie', 'yummy']),
    ('creative', 'The creativity here is next level ✨', ARRAY['art', 'creative', 'design'])
ON CONFLICT DO NOTHING;

-- Trigger to update usage stats
CREATE OR REPLACE FUNCTION update_template_usage()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.interaction_type = 'comment' AND NEW.success = true THEN
        -- Update template usage if content matches a template
        UPDATE comment_templates
        SET usage_count = usage_count + 1,
            last_used_at = NOW()
        WHERE template = NEW.content;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_template_usage ON engagement_interactions;
CREATE TRIGGER trigger_template_usage
    AFTER INSERT ON engagement_interactions
    FOR EACH ROW
    EXECUTE FUNCTION update_template_usage();
