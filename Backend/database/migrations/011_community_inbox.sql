-- INBOX-001: Community Inbox Database
-- Unified table for comments and DMs across all platforms
-- Version: 1.0
-- Date: 2026-01-21

-- ==============================================================================
-- COMMUNITY INBOX MESSAGES
-- ==============================================================================

CREATE TABLE IF NOT EXISTS community_inbox_messages (
    -- Identifiers
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

    -- Platform-agnostic fields
    platform TEXT NOT NULL CHECK (platform IN (
        'instagram', 'tiktok', 'youtube', 'twitter', 'facebook',
        'linkedin', 'threads', 'snapchat', 'pinterest', 'bluesky'
    )),
    message_type TEXT NOT NULL CHECK (message_type IN (
        'comment', 'dm', 'reply', 'mention', 'story_reply'
    )),

    -- Source context
    source_content_id TEXT, -- post_id, video_id, tweet_id, etc.
    source_url TEXT, -- full URL to original content
    platform_post_id UUID REFERENCES platform_posts(id) ON DELETE SET NULL,

    -- Author info (use identity mapping)
    author_person_id UUID REFERENCES people(id) ON DELETE SET NULL,
    author_handle TEXT NOT NULL,
    author_name TEXT,
    author_id_platform TEXT, -- platform-specific user ID
    author_profile_url TEXT,
    author_avatar_url TEXT,

    -- Message content
    text TEXT NOT NULL,
    media_urls TEXT[], -- for image/video attachments

    -- Conversation threading
    conversation_id TEXT, -- group related messages
    parent_message_id UUID REFERENCES community_inbox_messages(id) ON DELETE CASCADE,
    thread_position INTEGER DEFAULT 0,
    is_thread_root BOOLEAN DEFAULT false,

    -- Analysis/engagement (INBOX-007: Sentiment Analysis)
    sentiment_score FLOAT, -- -1 to +1
    sentiment_label TEXT CHECK (sentiment_label IN ('positive', 'neutral', 'negative')),
    emotion_tags TEXT[],
    intent TEXT CHECK (intent IN (
        'question', 'praise', 'critique', 'spam', 'engagement',
        'inquiry', 'feedback', 'support', 'complaint'
    )),
    theme_tags TEXT[],
    is_cta_response BOOLEAN DEFAULT false,
    cta_keyword TEXT,

    -- Lead qualification (INBOX qualification flow)
    is_qualified_lead BOOLEAN DEFAULT false,
    qualification_state TEXT DEFAULT 'initial' CHECK (qualification_state IN (
        'initial', 'qualifying', 'qualified', 'disqualified', 'converted'
    )),
    qualification_score FLOAT, -- 0-100
    qualification_notes TEXT,

    -- Moderation
    is_spam BOOLEAN DEFAULT false,
    is_hidden BOOLEAN DEFAULT false,
    requires_review BOOLEAN DEFAULT false,
    moderation_tags TEXT[],

    -- Response tracking
    response_status TEXT DEFAULT 'unanswered' CHECK (response_status IN (
        'unanswered', 'pending', 'responded', 'closed', 'escalated', 'ignored'
    )),
    responded_at TIMESTAMPTZ,
    response_text TEXT,
    response_author_id UUID REFERENCES people(id) ON DELETE SET NULL,
    response_method TEXT CHECK (response_method IN (
        'manual', 'ai_suggested', 'auto_rule', 'template'
    )),

    -- Priority & assignment
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'urgent')),
    assigned_to_user_id UUID REFERENCES people(id) ON DELETE SET NULL,
    assigned_at TIMESTAMPTZ,

    -- Timestamps
    created_at_platform TIMESTAMPTZ, -- when posted on platform
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    read_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,

    -- Metadata storage (raw platform response for extensibility)
    platform_data JSONB DEFAULT '{}'::jsonb,

    -- Metrics
    engagement_score FLOAT DEFAULT 0.0,
    response_time_minutes INTEGER -- time to first response
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_community_inbox_workspace ON community_inbox_messages(workspace_id);
CREATE INDEX IF NOT EXISTS idx_community_inbox_platform ON community_inbox_messages(platform);
CREATE INDEX IF NOT EXISTS idx_community_inbox_message_type ON community_inbox_messages(message_type);
CREATE INDEX IF NOT EXISTS idx_community_inbox_response_status ON community_inbox_messages(response_status);
CREATE INDEX IF NOT EXISTS idx_community_inbox_created_at ON community_inbox_messages(created_at_platform DESC);
CREATE INDEX IF NOT EXISTS idx_community_inbox_author_person ON community_inbox_messages(author_person_id);
CREATE INDEX IF NOT EXISTS idx_community_inbox_conversation ON community_inbox_messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_community_inbox_parent ON community_inbox_messages(parent_message_id);
CREATE INDEX IF NOT EXISTS idx_community_inbox_source_content ON community_inbox_messages(source_content_id);
CREATE INDEX IF NOT EXISTS idx_community_inbox_qualification ON community_inbox_messages(qualification_state, is_qualified_lead);
CREATE INDEX IF NOT EXISTS idx_community_inbox_sentiment ON community_inbox_messages(sentiment_label);
CREATE INDEX IF NOT EXISTS idx_community_inbox_priority ON community_inbox_messages(priority, response_status);

-- Full-text search index for message text
CREATE INDEX IF NOT EXISTS idx_community_inbox_text_search ON community_inbox_messages USING gin(to_tsvector('english', text));

-- Enable RLS
ALTER TABLE community_inbox_messages ENABLE ROW LEVEL SECURITY;

-- Comments
COMMENT ON TABLE community_inbox_messages IS 'INBOX-001: Unified inbox for comments and DMs across all platforms';
COMMENT ON COLUMN community_inbox_messages.conversation_id IS 'Groups related messages (e.g., all replies to a DM thread)';
COMMENT ON COLUMN community_inbox_messages.qualification_score IS 'Lead qualification score (0-100) for INBOX qualification flow';
COMMENT ON COLUMN community_inbox_messages.sentiment_score IS 'AI sentiment score from -1 (negative) to +1 (positive)';
COMMENT ON COLUMN community_inbox_messages.response_time_minutes IS 'Time to first response in minutes (for INBOX-008 analytics)';

-- ==============================================================================
-- INBOX CONVERSATIONS
-- ==============================================================================

CREATE TABLE IF NOT EXISTS inbox_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    conversation_id TEXT UNIQUE NOT NULL, -- matches community_inbox_messages.conversation_id

    -- Conversation metadata
    platform TEXT NOT NULL,
    root_message_id UUID REFERENCES community_inbox_messages(id) ON DELETE CASCADE,
    message_count INTEGER DEFAULT 1,

    -- Participants
    author_person_id UUID REFERENCES people(id) ON DELETE SET NULL,
    author_handle TEXT NOT NULL,

    -- Status
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'closed', 'archived')),

    -- Timestamps
    first_message_at TIMESTAMPTZ,
    last_message_at TIMESTAMPTZ,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inbox_conversations_workspace ON inbox_conversations(workspace_id);
CREATE INDEX IF NOT EXISTS idx_inbox_conversations_conversation_id ON inbox_conversations(conversation_id);
CREATE INDEX IF NOT EXISTS idx_inbox_conversations_author ON inbox_conversations(author_person_id);
CREATE INDEX IF NOT EXISTS idx_inbox_conversations_status ON inbox_conversations(status);
CREATE INDEX IF NOT EXISTS idx_inbox_conversations_last_message ON inbox_conversations(last_message_at DESC);

ALTER TABLE inbox_conversations ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE inbox_conversations IS 'INBOX-001: Groups related messages into conversations';

-- ==============================================================================
-- AUTO-REPLY RULES (INBOX-006)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS inbox_auto_reply_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

    -- Rule configuration
    name TEXT NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,

    -- Trigger conditions
    platforms TEXT[] NOT NULL, -- which platforms this rule applies to
    message_types TEXT[] NOT NULL, -- comment, dm, mention, etc.

    -- Matching criteria
    keyword_triggers TEXT[], -- keywords that trigger this rule
    keyword_match_type TEXT DEFAULT 'contains' CHECK (keyword_match_type IN ('exact', 'contains', 'starts_with', 'regex')),
    sentiment_filter TEXT CHECK (sentiment_filter IN ('positive', 'neutral', 'negative', 'any')),

    -- Reply configuration
    reply_template TEXT NOT NULL,
    reply_delay_seconds INTEGER DEFAULT 0, -- delay before sending reply

    -- Limits
    max_uses_per_day INTEGER, -- rate limit
    uses_today INTEGER DEFAULT 0,
    last_reset_at TIMESTAMPTZ DEFAULT NOW(),

    -- Priority
    priority INTEGER DEFAULT 0, -- higher priority rules matched first

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_triggered_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_inbox_auto_reply_workspace ON inbox_auto_reply_rules(workspace_id);
CREATE INDEX IF NOT EXISTS idx_inbox_auto_reply_active ON inbox_auto_reply_rules(is_active, priority DESC);

ALTER TABLE inbox_auto_reply_rules ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE inbox_auto_reply_rules IS 'INBOX-006: Auto-reply rules engine for keyword-based responses';

-- ==============================================================================
-- INBOX ANALYTICS (INBOX-008)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS inbox_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

    -- Time period
    date DATE NOT NULL,
    platform TEXT NOT NULL,

    -- Volume metrics
    messages_received INTEGER DEFAULT 0,
    messages_responded INTEGER DEFAULT 0,
    messages_closed INTEGER DEFAULT 0,
    messages_ignored INTEGER DEFAULT 0,

    -- Response metrics
    avg_response_time_minutes FLOAT,
    median_response_time_minutes FLOAT,
    response_rate FLOAT, -- % of messages responded to

    -- Sentiment metrics
    positive_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    avg_sentiment_score FLOAT,

    -- Qualification metrics
    qualified_leads_count INTEGER DEFAULT 0,
    conversion_count INTEGER DEFAULT 0,
    qualification_rate FLOAT,

    -- AI usage metrics
    ai_suggestions_used INTEGER DEFAULT 0,
    auto_replies_sent INTEGER DEFAULT 0,
    manual_replies_sent INTEGER DEFAULT 0,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(workspace_id, date, platform)
);

CREATE INDEX IF NOT EXISTS idx_inbox_analytics_workspace_date ON inbox_analytics(workspace_id, date DESC);
CREATE INDEX IF NOT EXISTS idx_inbox_analytics_platform ON inbox_analytics(platform);

ALTER TABLE inbox_analytics ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE inbox_analytics IS 'INBOX-008: Daily inbox analytics aggregated by platform';

-- ==============================================================================
-- INBOX RESPONSE TEMPLATES (for quick replies)
-- ==============================================================================

CREATE TABLE IF NOT EXISTS inbox_response_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,

    -- Template info
    name TEXT NOT NULL,
    category TEXT, -- e.g., 'greeting', 'faq', 'support', 'sales'
    template_text TEXT NOT NULL,

    -- Usage
    platforms TEXT[], -- which platforms this template applies to
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_inbox_templates_workspace ON inbox_response_templates(workspace_id);
CREATE INDEX IF NOT EXISTS idx_inbox_templates_category ON inbox_response_templates(category);

ALTER TABLE inbox_response_templates ENABLE ROW LEVEL SECURITY;

COMMENT ON TABLE inbox_response_templates IS 'INBOX: Saved reply templates for quick responses';

-- ==============================================================================
-- FUNCTIONS & TRIGGERS
-- ==============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_inbox_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_community_inbox_messages_updated_at
    BEFORE UPDATE ON community_inbox_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_inbox_updated_at();

CREATE TRIGGER update_inbox_conversations_updated_at
    BEFORE UPDATE ON inbox_conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_inbox_updated_at();

CREATE TRIGGER update_inbox_auto_reply_rules_updated_at
    BEFORE UPDATE ON inbox_auto_reply_rules
    FOR EACH ROW
    EXECUTE FUNCTION update_inbox_updated_at();

CREATE TRIGGER update_inbox_analytics_updated_at
    BEFORE UPDATE ON inbox_analytics
    FOR EACH ROW
    EXECUTE FUNCTION update_inbox_updated_at();

CREATE TRIGGER update_inbox_response_templates_updated_at
    BEFORE UPDATE ON inbox_response_templates
    FOR EACH ROW
    EXECUTE FUNCTION update_inbox_updated_at();

-- Function to calculate response time
CREATE OR REPLACE FUNCTION calculate_response_time()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.responded_at IS NOT NULL AND NEW.created_at_platform IS NOT NULL THEN
        NEW.response_time_minutes = EXTRACT(EPOCH FROM (NEW.responded_at - NEW.created_at_platform)) / 60;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER calculate_message_response_time
    BEFORE UPDATE ON community_inbox_messages
    FOR EACH ROW
    WHEN (NEW.responded_at IS NOT NULL AND OLD.responded_at IS NULL)
    EXECUTE FUNCTION calculate_response_time();
