# Schema Alignment Notes

## Current Modules vs Existing Schema

### ✅ Aligned (No Changes Needed)

| Module | Data Type | Existing Table | Status |
|--------|-----------|----------------|--------|
| **Scheduler** | Post tracking | `social_media_posts` | ✅ Compatible |
| **Scheduler** | Metrics snapshots | `social_media_post_analytics` | ✅ Compatible |
| **Search** | User results | `social_media_accounts` | ✅ Compatible |
| **Search** | Video results | `social_media_posts` | ✅ Compatible |
| **Search** | Hashtag results | `social_media_hashtags` | ✅ Compatible |
| **API** | Comments | `social_media_comments` | ✅ Compatible |
| **API** | API usage | `api_usage_tracking` | ✅ Compatible |

### ⚠️ Enhancements Recommended

#### 1. Check-Back Schedule Tracking

The scheduler stores check schedules in JSON files. For production, add to `social_media_posts`:

```sql
-- Add to social_media_posts table
ALTER TABLE social_media_posts ADD COLUMN IF NOT EXISTS
    check_schedule JSONB DEFAULT '[]'::jsonb;

ALTER TABLE social_media_posts ADD COLUMN IF NOT EXISTS
    next_check_at TIMESTAMP;

ALTER TABLE social_media_posts ADD COLUMN IF NOT EXISTS
    tracking_complete BOOLEAN DEFAULT FALSE;

CREATE INDEX idx_posts_next_check ON social_media_posts(next_check_at)
WHERE tracking_complete = FALSE;
```

#### 2. Comment Replies Support

The API returns nested comments. Add parent tracking:

```sql
-- Already exists in social_media_comments:
-- parent_comment_id INTEGER REFERENCES social_media_comments(id)
-- is_reply BOOLEAN DEFAULT FALSE

-- Add reply count tracking from API
ALTER TABLE social_media_comments ADD COLUMN IF NOT EXISTS
    api_reply_count INTEGER DEFAULT 0;
```

### 🔨 New Tables Needed

#### 1. Direct Messages (Messenger Module)

```sql
-- Conversations table
CREATE TABLE IF NOT EXISTS social_media_conversations (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES social_media_accounts(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL DEFAULT 'tiktok',
    
    -- Participant
    participant_username VARCHAR(255) NOT NULL,
    participant_id VARCHAR(255),
    participant_display_name VARCHAR(255),
    participant_avatar_url TEXT,
    
    -- Status
    last_message_at TIMESTAMP,
    last_message_preview TEXT,
    unread_count INTEGER DEFAULT 0,
    is_muted BOOLEAN DEFAULT FALSE,
    is_archived BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(account_id, platform, participant_username)
);

CREATE INDEX idx_conversations_account ON social_media_conversations(account_id);
CREATE INDEX idx_conversations_last_msg ON social_media_conversations(last_message_at DESC);

-- Messages table
CREATE TABLE IF NOT EXISTS social_media_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES social_media_conversations(id) ON DELETE CASCADE,
    
    -- Message content
    external_message_id VARCHAR(255),
    message_text TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'text', -- text, image, video, sticker
    media_url TEXT,
    
    -- Sender
    is_outgoing BOOLEAN NOT NULL, -- true = we sent, false = they sent
    sender_username VARCHAR(255),
    
    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    sent_at TIMESTAMP NOT NULL,
    delivered_at TIMESTAMP,
    read_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(conversation_id, external_message_id)
);

CREATE INDEX idx_messages_conversation ON social_media_messages(conversation_id);
CREATE INDEX idx_messages_sent_at ON social_media_messages(sent_at DESC);
```

#### 2. Engagement Actions Log

```sql
-- Track all automation actions for safety/audit
CREATE TABLE IF NOT EXISTS automation_actions (
    id SERIAL PRIMARY KEY,
    account_id INTEGER REFERENCES social_media_accounts(id),
    platform VARCHAR(50) NOT NULL DEFAULT 'tiktok',
    
    -- Action details
    action_type VARCHAR(50) NOT NULL, -- like, comment, follow, message, search
    target_type VARCHAR(50), -- video, user, hashtag
    target_id VARCHAR(255),
    target_url TEXT,
    
    -- Content (for comments/messages)
    content_text TEXT,
    
    -- Result
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,
    
    -- Rate limiting
    action_date DATE DEFAULT CURRENT_DATE,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_actions_account_date ON automation_actions(account_id, action_date);
CREATE INDEX idx_actions_type ON automation_actions(action_type);

-- View for rate limit checking
CREATE OR REPLACE VIEW daily_action_counts AS
SELECT 
    account_id,
    action_date,
    action_type,
    COUNT(*) as action_count
FROM automation_actions
WHERE action_date = CURRENT_DATE
GROUP BY account_id, action_date, action_type;
```

---

## Migration Priority

### Phase 1: Immediate (Optional Enhancements)
```sql
-- Add check schedule fields
ALTER TABLE social_media_posts ADD COLUMN IF NOT EXISTS check_schedule JSONB;
ALTER TABLE social_media_posts ADD COLUMN IF NOT EXISTS next_check_at TIMESTAMP;
ALTER TABLE social_media_posts ADD COLUMN IF NOT EXISTS tracking_complete BOOLEAN DEFAULT FALSE;
```

### Phase 2: When Using Messaging
```sql
-- Create conversations and messages tables
-- (See full SQL above)
```

### Phase 3: Production Safety
```sql
-- Create automation_actions table for audit logging
-- (See full SQL above)
```

---

## Current Module Storage

Until database integration, modules store data in:

| Module | Storage | Location |
|--------|---------|----------|
| Scheduler | JSON files | `./tracked_posts/{video_id}.json` |
| Search | In-memory | No persistence |
| Messenger | In-memory | No persistence |
| API | JSON files | `./extracted_data/*.json` |

---

## Integration Recommendations

### 1. Scheduler → Database

```python
# Instead of JSON files, use:
async def track_post(self, url: str):
    # Insert into social_media_posts
    post = await db.execute("""
        INSERT INTO social_media_posts 
        (platform, external_post_id, post_url, check_schedule, next_check_at)
        VALUES ('tiktok', $1, $2, $3, $4)
        RETURNING id
    """, video_id, url, schedule_json, next_check)
    
    # Insert initial metrics
    await db.execute("""
        INSERT INTO social_media_post_analytics 
        (post_id, snapshot_date, likes_count, views_count, ...)
        VALUES ($1, NOW(), $2, $3, ...)
    """, post.id, metrics.likes, metrics.views)
```

### 2. Comments → Database

```python
# Store API comments
for comment in api_comments:
    await db.execute("""
        INSERT INTO social_media_comments 
        (post_id, platform, external_comment_id, comment_text, 
         author_username, likes_count, api_reply_count, commented_at)
        VALUES ($1, 'tiktok', $2, $3, $4, $5, $6, $7)
        ON CONFLICT (platform, external_comment_id) DO UPDATE
        SET likes_count = $5, api_reply_count = $6
    """, post_id, comment['id'], comment['text'], 
        comment['user']['nickname'], comment['digg_count'], 
        comment['reply_total'], comment['create_time'])
```

---

## Summary

| Category | Status | Migration |
|----------|--------|-----------|
| **Posts & Metrics** | ✅ Schema ready | - |
| **Comments** | ✅ Schema ready | - |
| **Hashtags** | ✅ Schema ready | - |
| **Check-back Schedule** | ✅ Migration ready | `add_automation_features.sql` |
| **Direct Messages** | ✅ Migration ready | `add_automation_features.sql` |
| **Action Logging** | ✅ Migration ready | `add_automation_features.sql` |

---

## Migration Created: `add_automation_features.sql`

### Run Migration

```bash
# Via Docker (if using local Supabase)
cat Backend/migrations/add_automation_features.sql | \
  docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres

# Via psql directly
psql $DATABASE_URL -f Backend/migrations/add_automation_features.sql
```

### What Gets Created

**New Tables (4):**
- `social_media_conversations` - DM threads
- `social_media_messages` - Individual DMs
- `automation_actions` - Action audit log
- `message_templates` - Reusable templates

**New Columns on `social_media_posts` (5):**
- `check_schedule` - JSON array of scheduled check times
- `next_check_at` - Next scheduled check timestamp
- `tracking_complete` - Boolean when all checks done
- `tracking_started_at` - When tracking began
- `checks_completed` - Number of checks completed

**Views (4):**
- `posts_pending_checkback` - Posts due for checking
- `daily_action_counts` - Rate limit tracking
- `hourly_action_distribution` - Timing analysis
- `active_conversations_summary` - DM overview

**Functions (3):**
- `check_rate_limit(account_id, action_type, limit)` - Rate limit check
- `get_next_check_time(post_id)` - Get next check timestamp
- `record_check_completion(post_id)` - Mark check complete

---

## Database-Backed Scheduler

After running the migration, use `tiktok_scheduler_db.py`:

```python
from automation.tiktok_scheduler_db import TikTokSchedulerDB

scheduler = TikTokSchedulerDB()
await scheduler.connect()

# Track a post
await scheduler.track_post("https://tiktok.com/@user/video/123")

# Run pending checks
await scheduler.run_pending_checks()

# Get analytics
analytics = await scheduler.get_post_analytics(post_id)

await scheduler.close()
```

### CLI Usage

```bash
# Set environment variables
export DATABASE_URL="postgresql://..."
export RAPIDAPI_KEY="your_key"

# Commands
python automation/tiktok_scheduler_db.py track <url>
python automation/tiktok_scheduler_db.py check
python automation/tiktok_scheduler_db.py list
python automation/tiktok_scheduler_db.py analytics <post_id>
```

The current modules work with JSON file storage (`tiktok_scheduler.py`) or database storage (`tiktok_scheduler_db.py`). Use JSON for testing, database for production.
