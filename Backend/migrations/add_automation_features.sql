-- ============================================================================
-- AUTOMATION FEATURES SCHEMA EXTENSION
-- Adds check-back scheduling and DM/messaging support
-- Version: 1.0
-- Date: 2025-12-07
-- ============================================================================

-- ============================================================================
-- PART 1: CHECK-BACK SCHEDULE ENHANCEMENT
-- Add tracking columns to social_media_posts
-- ============================================================================

-- Add check schedule fields to existing posts table
ALTER TABLE social_media_posts 
ADD COLUMN IF NOT EXISTS check_schedule JSONB DEFAULT '[]'::jsonb;

ALTER TABLE social_media_posts 
ADD COLUMN IF NOT EXISTS next_check_at TIMESTAMP;

ALTER TABLE social_media_posts 
ADD COLUMN IF NOT EXISTS tracking_complete BOOLEAN DEFAULT FALSE;

ALTER TABLE social_media_posts 
ADD COLUMN IF NOT EXISTS tracking_started_at TIMESTAMP;

ALTER TABLE social_media_posts 
ADD COLUMN IF NOT EXISTS checks_completed INTEGER DEFAULT 0;

-- Index for finding posts that need checking
CREATE INDEX IF NOT EXISTS idx_posts_next_check 
ON social_media_posts(next_check_at) 
WHERE tracking_complete = FALSE AND next_check_at IS NOT NULL;

-- Index for active tracking
CREATE INDEX IF NOT EXISTS idx_posts_tracking_active 
ON social_media_posts(tracking_complete) 
WHERE tracking_complete = FALSE;

COMMENT ON COLUMN social_media_posts.check_schedule IS 'JSON array of scheduled check times (ISO timestamps)';
COMMENT ON COLUMN social_media_posts.next_check_at IS 'Next scheduled check timestamp';
COMMENT ON COLUMN social_media_posts.tracking_complete IS 'True when all scheduled checks are done';
COMMENT ON COLUMN social_media_posts.tracking_started_at IS 'When we started tracking this post';
COMMENT ON COLUMN social_media_posts.checks_completed IS 'Number of check-back cycles completed';

-- ============================================================================
-- PART 2: DIRECT MESSAGES / CONVERSATIONS
-- For TikTok DM automation
-- ============================================================================

-- Conversations table (DM threads)
CREATE TABLE IF NOT EXISTS social_media_conversations (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES social_media_accounts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL DEFAULT 'tiktok',
    
    -- Participant info
    participant_username VARCHAR(255) NOT NULL,
    participant_id VARCHAR(255),
    participant_display_name VARCHAR(255),
    participant_avatar_url TEXT,
    participant_verified BOOLEAN DEFAULT FALSE,
    
    -- Conversation state
    last_message_at TIMESTAMP,
    last_message_preview TEXT,
    last_message_is_outgoing BOOLEAN,
    unread_count INTEGER DEFAULT 0,
    
    -- Status flags
    is_muted BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    is_blocked BOOLEAN DEFAULT FALSE,
    is_spam BOOLEAN DEFAULT FALSE,
    
    -- Automation flags
    auto_reply_enabled BOOLEAN DEFAULT FALSE,
    follow_up_scheduled_at TIMESTAMP,
    
    -- Timestamps
    conversation_started_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(account_id, platform, participant_username)
);

CREATE INDEX idx_conversations_account ON social_media_conversations(account_id);
CREATE INDEX idx_conversations_platform ON social_media_conversations(platform);
CREATE INDEX idx_conversations_last_msg ON social_media_conversations(last_message_at DESC);
CREATE INDEX idx_conversations_unread ON social_media_conversations(unread_count) WHERE unread_count > 0;
CREATE INDEX idx_conversations_follow_up ON social_media_conversations(follow_up_scheduled_at) 
WHERE follow_up_scheduled_at IS NOT NULL;

COMMENT ON TABLE social_media_conversations IS 'DM conversation threads with users';

-- Messages table (individual DMs)
CREATE TABLE IF NOT EXISTS social_media_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES social_media_conversations(id) ON DELETE CASCADE,
    
    -- Message identification
    external_message_id VARCHAR(255),
    
    -- Content
    message_text TEXT,
    message_type VARCHAR(50) DEFAULT 'text', -- text, image, video, sticker, gif, voice
    media_url TEXT,
    media_thumbnail_url TEXT,
    
    -- Direction
    is_outgoing BOOLEAN NOT NULL, -- true = we sent, false = they sent
    sender_username VARCHAR(255),
    
    -- Status
    status VARCHAR(50) DEFAULT 'sent', -- sent, delivered, read, failed
    is_read BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    sent_at TIMESTAMP NOT NULL,
    delivered_at TIMESTAMP,
    read_at TIMESTAMP,
    
    -- Metadata
    reply_to_message_id INTEGER REFERENCES social_media_messages(id),
    metadata JSONB,
    
    -- Automation
    is_automated BOOLEAN DEFAULT FALSE,
    template_used VARCHAR(255),
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(conversation_id, external_message_id)
);

CREATE INDEX idx_messages_conversation ON social_media_messages(conversation_id);
CREATE INDEX idx_messages_sent_at ON social_media_messages(sent_at DESC);
CREATE INDEX idx_messages_outgoing ON social_media_messages(is_outgoing);
CREATE INDEX idx_messages_status ON social_media_messages(status);

COMMENT ON TABLE social_media_messages IS 'Individual DM messages within conversations';

-- ============================================================================
-- PART 3: AUTOMATION ACTIONS LOG
-- Track all engagement actions for safety/audit
-- ============================================================================

CREATE TABLE IF NOT EXISTS automation_actions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES social_media_accounts(id),
    platform VARCHAR(50) NOT NULL DEFAULT 'tiktok',
    
    -- Action details
    action_type VARCHAR(50) NOT NULL, -- like, comment, follow, unfollow, message, search, view
    target_type VARCHAR(50), -- video, user, hashtag, sound, conversation
    target_id VARCHAR(255),
    target_url TEXT,
    target_username VARCHAR(255),
    
    -- Content (for comments/messages)
    content_text TEXT,
    
    -- Result
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    error_code VARCHAR(50),
    
    -- Context
    session_id VARCHAR(255),
    triggered_by VARCHAR(50), -- manual, scheduled, auto_reply, workflow
    
    -- Rate limiting
    action_date DATE DEFAULT CURRENT_DATE,
    action_hour INTEGER DEFAULT EXTRACT(HOUR FROM NOW()),
    
    -- Performance
    execution_time_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_actions_account_date ON automation_actions(account_id, action_date);
CREATE INDEX idx_actions_type ON automation_actions(action_type);
CREATE INDEX idx_actions_target ON automation_actions(target_type, target_id);
CREATE INDEX idx_actions_success ON automation_actions(success);
CREATE INDEX idx_actions_date_hour ON automation_actions(action_date, action_hour);

COMMENT ON TABLE automation_actions IS 'Audit log of all automation actions for rate limiting and safety';

-- ============================================================================
-- PART 4: MESSAGE TEMPLATES
-- Pre-defined message templates for automation
-- ============================================================================

CREATE TABLE IF NOT EXISTS message_templates (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES social_media_accounts(id),
    
    -- Template info
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100), -- welcome, follow_up, thank_you, promo, custom
    
    -- Content
    template_text TEXT NOT NULL,
    variables JSONB, -- Available variables: {username}, {video_title}, etc.
    
    -- Usage stats
    times_used INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_templates_account ON message_templates(account_id);
CREATE INDEX idx_templates_category ON message_templates(category);

COMMENT ON TABLE message_templates IS 'Reusable message templates for DM automation';

-- ============================================================================
-- PART 5: VIEWS FOR EASY QUERYING
-- ============================================================================

-- Posts needing check-back
CREATE OR REPLACE VIEW posts_pending_checkback AS
SELECT 
    p.id,
    p.platform,
    p.post_url,
    p.external_post_id,
    p.caption,
    p.posted_at,
    p.next_check_at,
    p.checks_completed,
    p.tracking_started_at,
    a.username as account_username,
    EXTRACT(EPOCH FROM (NOW() - p.next_check_at)) / 60 as minutes_overdue
FROM social_media_posts p
JOIN social_media_accounts a ON p.account_id = a.id
WHERE p.tracking_complete = FALSE 
AND p.next_check_at IS NOT NULL
AND p.next_check_at <= NOW()
ORDER BY p.next_check_at ASC;

-- Daily action counts for rate limiting
CREATE OR REPLACE VIEW daily_action_counts AS
SELECT 
    account_id,
    action_date,
    action_type,
    COUNT(*) as action_count,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as failure_count
FROM automation_actions
WHERE action_date >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY account_id, action_date, action_type;

-- Hourly action distribution (for timing analysis)
CREATE OR REPLACE VIEW hourly_action_distribution AS
SELECT 
    account_id,
    action_type,
    action_hour,
    COUNT(*) as action_count
FROM automation_actions
WHERE action_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY account_id, action_type, action_hour
ORDER BY action_hour;

-- Active conversations summary
CREATE OR REPLACE VIEW active_conversations_summary AS
SELECT 
    c.id,
    c.platform,
    c.participant_username,
    c.participant_display_name,
    c.last_message_at,
    c.last_message_preview,
    c.unread_count,
    a.username as our_account,
    (SELECT COUNT(*) FROM social_media_messages WHERE conversation_id = c.id) as total_messages,
    (SELECT COUNT(*) FROM social_media_messages WHERE conversation_id = c.id AND is_outgoing = TRUE) as sent_messages,
    (SELECT COUNT(*) FROM social_media_messages WHERE conversation_id = c.id AND is_outgoing = FALSE) as received_messages
FROM social_media_conversations c
JOIN social_media_accounts a ON c.account_id = a.id
WHERE c.is_archived = FALSE
ORDER BY c.last_message_at DESC;

-- ============================================================================
-- PART 6: HELPER FUNCTIONS
-- ============================================================================

-- Function to check if action is within rate limit
CREATE OR REPLACE FUNCTION check_rate_limit(
    p_account_id INTEGER,
    p_action_type VARCHAR(50),
    p_daily_limit INTEGER DEFAULT 100
) RETURNS BOOLEAN AS $$
DECLARE
    current_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO current_count
    FROM automation_actions
    WHERE account_id = p_account_id
    AND action_type = p_action_type
    AND action_date = CURRENT_DATE;
    
    RETURN current_count < p_daily_limit;
END;
$$ LANGUAGE plpgsql;

-- Function to get next check time for a post
CREATE OR REPLACE FUNCTION get_next_check_time(p_post_id INTEGER)
RETURNS TIMESTAMP AS $$
DECLARE
    schedule JSONB;
    completed INTEGER;
    next_time TIMESTAMP;
BEGIN
    SELECT check_schedule, checks_completed 
    INTO schedule, completed
    FROM social_media_posts 
    WHERE id = p_post_id;
    
    IF schedule IS NULL OR jsonb_array_length(schedule) <= completed THEN
        RETURN NULL;
    END IF;
    
    SELECT (schedule->>completed)::TIMESTAMP INTO next_time;
    RETURN next_time;
END;
$$ LANGUAGE plpgsql;

-- Function to record a check completion
CREATE OR REPLACE FUNCTION record_check_completion(p_post_id INTEGER)
RETURNS VOID AS $$
DECLARE
    schedule JSONB;
    completed INTEGER;
BEGIN
    UPDATE social_media_posts
    SET checks_completed = checks_completed + 1
    WHERE id = p_post_id;
    
    -- Get updated values
    SELECT check_schedule, checks_completed INTO schedule, completed
    FROM social_media_posts WHERE id = p_post_id;
    
    -- Update next_check_at or mark complete
    IF jsonb_array_length(schedule) <= completed THEN
        UPDATE social_media_posts
        SET tracking_complete = TRUE, next_check_at = NULL
        WHERE id = p_post_id;
    ELSE
        UPDATE social_media_posts
        SET next_check_at = (schedule->>completed)::TIMESTAMP
        WHERE id = p_post_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- PART 7: DEFAULT RATE LIMITS
-- ============================================================================

INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('automation_rate_limits', '{
    "like": {"daily": 100, "hourly": 20},
    "comment": {"daily": 20, "hourly": 5},
    "follow": {"daily": 50, "hourly": 10},
    "unfollow": {"daily": 50, "hourly": 10},
    "message": {"daily": 20, "hourly": 5},
    "search": {"daily": 200, "hourly": 50}
}', 'Rate limits for automation actions by type')
ON CONFLICT (setting_key) DO UPDATE 
SET setting_value = EXCLUDED.setting_value,
    updated_at = NOW();

INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('checkback_schedule_default', '[
    {"offset_hours": 1, "name": "1 hour"},
    {"offset_hours": 6, "name": "6 hours"},
    {"offset_hours": 12, "name": "12 hours"},
    {"offset_hours": 24, "name": "1 day"},
    {"offset_hours": 48, "name": "2 days"},
    {"offset_hours": 72, "name": "3 days"},
    {"offset_hours": 168, "name": "1 week"},
    {"offset_hours": 336, "name": "2 weeks"},
    {"offset_hours": 720, "name": "30 days"}
]', 'Default check-back schedule for post tracking')
ON CONFLICT (setting_key) DO UPDATE 
SET setting_value = EXCLUDED.setting_value,
    updated_at = NOW();

-- ============================================================================
-- SUCCESS MESSAGE
-- ============================================================================

DO $$ 
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '✅ Automation Features Schema Created Successfully!';
    RAISE NOTICE '';
    RAISE NOTICE '📊 New Tables:';
    RAISE NOTICE '   - social_media_conversations (DM threads)';
    RAISE NOTICE '   - social_media_messages (individual DMs)';
    RAISE NOTICE '   - automation_actions (action audit log)';
    RAISE NOTICE '   - message_templates (reusable templates)';
    RAISE NOTICE '';
    RAISE NOTICE '📈 Enhanced Tables:';
    RAISE NOTICE '   - social_media_posts (+check_schedule, +next_check_at, +tracking_complete)';
    RAISE NOTICE '';
    RAISE NOTICE '🔧 Views:';
    RAISE NOTICE '   - posts_pending_checkback';
    RAISE NOTICE '   - daily_action_counts';
    RAISE NOTICE '   - hourly_action_distribution';
    RAISE NOTICE '   - active_conversations_summary';
    RAISE NOTICE '';
    RAISE NOTICE '⚙️ Functions:';
    RAISE NOTICE '   - check_rate_limit(account_id, action_type, limit)';
    RAISE NOTICE '   - get_next_check_time(post_id)';
    RAISE NOTICE '   - record_check_completion(post_id)';
    RAISE NOTICE '';
    RAISE NOTICE '🎯 Ready for TikTok automation!';
END $$;
