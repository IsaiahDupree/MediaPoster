# 📊 Comprehensive Social Media Analytics Schema

**Status**: ✅ **DEPLOYED TO DATABASE**  
**Date**: November 22, 2025  
**Platforms Supported**: All 9 (TikTok, Instagram, YouTube, Twitter/X, Facebook, Pinterest, Bluesky, Threads, LinkedIn)

---

## 🎯 What We Built

A **comprehensive analytics system** that extends your existing `social_accounts` table with deep tracking capabilities for all 9 social media platforms.

### ✅ Deployment Status

```
✅ 12 Core Tables Created
✅ 2 Views Created  
✅ Integrated with Existing Schema
✅ Ready for All 9 Platforms
✅ Connected to local Supabase (127.0.0.1:54322)
```

---

## 📊 Schema Overview

### Core Tables (12)

1. **`social_analytics_config`** - Monitoring configuration per account
2. **`social_analytics_snapshots`** - Daily account metrics
3. **`social_posts_analytics`** - All tracked posts with URLs
4. **`social_post_metrics`** - Historical post performance
5. **`social_hashtags`** - Hashtag performance tracking
6. **`social_post_hashtags`** - Post-hashtag relationships
7. **`social_comments`** - Comments and replies
8. **`social_audience_demographics`** - Age, gender, location data
9. **`social_api_usage`** - Rate limit monitoring
10. **`social_fetch_jobs`** - Job tracking
11. Plus 2 supporting tables

### Views (2)

1. **`social_analytics_latest`** - Current metrics per account
2. **`social_post_performance`** - Latest post performance

---

## 🏗️ Schema Details

### 1. Configuration Table

**`social_analytics_config`** - Set up monitoring per account

```sql
CREATE TABLE social_analytics_config (
    social_account_id UUID → links to social_accounts(id)
    monitoring_enabled BOOLEAN DEFAULT TRUE
    fetch_frequency INTERVAL DEFAULT '24 hours'
    last_fetched_at TIMESTAMP
    posts_per_fetch INTEGER DEFAULT 50
    provider_name VARCHAR(100) -- 'rapidapi_tiktok', etc.
    ...
)
```

**Usage:**
```sql
-- Enable monitoring for an account
INSERT INTO social_analytics_config (
    social_account_id, 
    monitoring_enabled,
    provider_name
) VALUES (
    '123e4567-e89b-12d3-a456-426614174000',
    TRUE,
    'rapidapi_tiktok'
);
```

---

### 2. Daily Snapshots

**`social_analytics_snapshots`** - Historical account metrics

```sql
CREATE TABLE social_analytics_snapshots (
    social_account_id UUID
    snapshot_date DATE
    
    -- Universal Metrics
    followers_count INTEGER
    following_count INTEGER
    posts_count INTEGER
    total_likes BIGINT
    total_comments BIGINT
    total_views BIGINT
    total_shares BIGINT
    
    -- Platform-Specific
    subscribers_count INTEGER -- YouTube
    pins_count INTEGER -- Pinterest
    retweets_count BIGINT -- Twitter/X
    watch_time_minutes BIGINT -- YouTube
    
    -- Calculated
    engagement_rate DECIMAL(5,2)
    follower_growth INTEGER
    ...
)
```

**Supports:**
- ✅ TikTok (followers, likes, views, shares)
- ✅ Instagram (followers, likes, comments, saves)
- ✅ YouTube (subscribers, views, watch time)
- ✅ Twitter/X (followers, retweets, likes)
- ✅ Facebook (followers, reactions, shares)
- ✅ Pinterest (followers, pins, repins)
- ✅ LinkedIn (connections, reactions, shares)
- ✅ Bluesky (followers, reposts, likes)
- ✅ Threads (followers, likes, replies)

---

### 3. Posts Table

**`social_posts_analytics`** - All tracked social posts

```sql
CREATE TABLE social_posts_analytics (
    social_account_id UUID
    external_post_id VARCHAR(255)
    platform VARCHAR(50)
    post_url TEXT -- Full URL for content matching!
    
    -- Content
    caption TEXT
    title VARCHAR(500)
    media_type VARCHAR(50)
    media_url TEXT
    duration INTEGER
    
    -- Link to Internal Content
    video_id UUID -- Links to your videos table
    clip_id UUID -- Links to your clips table
    
    -- Timestamps
    posted_at TIMESTAMP
    ...
)
```

**Key Features:**
- ✅ **Post URLs saved** for content matching
- ✅ Links to `video_id` and `clip_id`
- ✅ Support for all media types
- ✅ Platform-specific fields

---

### 4. Post Performance Metrics

**`social_post_metrics`** - Track post growth over time

```sql
CREATE TABLE social_post_metrics (
    post_id INTEGER → links to social_posts_analytics(id)
    snapshot_date DATE
    snapshot_hour INTEGER -- For hourly tracking!
    
    -- Core Engagement
    likes_count BIGINT
    comments_count BIGINT
    views_count BIGINT
    shares_count BIGINT
    saves_count BIGINT
    
    -- Video Metrics
    watch_time_seconds BIGINT
    completion_rate DECIMAL(5,2)
    
    -- Reach
    impressions BIGINT
    reach BIGINT
    
    engagement_rate DECIMAL(5,2)
    ...
)
```

**Enables:**
- 📈 Hourly performance tracking
- 📈 Growth trends
- 📈 Virality analysis
- 📈 Best time to post analysis

---

### 5. Hashtags

**`social_hashtags`** + **`social_post_hashtags`**

```sql
-- Track all hashtags
CREATE TABLE social_hashtags (
    hashtag VARCHAR(255) UNIQUE
    total_uses BIGINT
    total_views BIGINT
    avg_engagement_rate DECIMAL(5,2)
)

-- Link hashtags to posts
CREATE TABLE social_post_hashtags (
    post_id INTEGER
    hashtag_id INTEGER
    position INTEGER
)
```

**Features:**
- Aggregate performance across all posts
- Find best-performing hashtags
- Track hashtag trends

---

### 6. Comments

**`social_comments`** - Store and analyze comments

```sql
CREATE TABLE social_comments (
    post_id INTEGER
    external_comment_id VARCHAR(255)
    comment_text TEXT
    author_username VARCHAR(255)
    
    parent_comment_id INTEGER -- For replies
    is_reply BOOLEAN
    
    likes_count INTEGER
    is_creator_reply BOOLEAN -- Your replies!
    
    sentiment VARCHAR(20) -- 'positive', 'negative', 'neutral'
    sentiment_score DECIMAL(3,2)
    ...
)
```

**Capabilities:**
- Thread tracking (replies to replies)
- Identify creator responses
- Sentiment analysis ready
- Track comment engagement

---

### 7. Audience Demographics

**`social_audience_demographics`** - Know your audience

```sql
CREATE TABLE social_audience_demographics (
    social_account_id UUID
    snapshot_date DATE
    
    -- Age Groups
    age_13_17 DECIMAL(5,2)
    age_18_24 DECIMAL(5,2)
    age_25_34 DECIMAL(5,2)
    age_35_44 DECIMAL(5,2)
    age_45_plus DECIMAL(5,2)
    
    -- Gender
    gender_male DECIMAL(5,2)
    gender_female DECIMAL(5,2)
    
    -- Locations (JSONB)
    top_countries JSONB
    top_cities JSONB
    top_languages JSONB
    
    -- Activity Patterns
    peak_hours JSONB -- [14, 18, 20]
    peak_days JSONB -- ['monday', 'wednesday']
)
```

**Insights:**
- Best time to post
- Geographic targeting
- Age/gender targeting
- Content timing optimization

---

### 8. API Usage Tracking

**`social_api_usage`** - Monitor rate limits

```sql
CREATE TABLE social_api_usage (
    provider_name VARCHAR(100)
    platform VARCHAR(50)
    endpoint VARCHAR(255)
    request_count INTEGER
    success BOOLEAN
    latency_ms INTEGER
    date DATE
)
```

**Monitors:**
- Daily API usage per provider
- Success rates
- Performance (latency)
- Cost tracking
- Rate limit management

---

### 9. Fetch Jobs

**`social_fetch_jobs`** - Track analytics collection

```sql
CREATE TABLE social_fetch_jobs (
    social_account_id UUID
    job_type VARCHAR(50)
    status VARCHAR(50) -- 'pending', 'running', 'completed'
    
    posts_fetched INTEGER
    comments_fetched INTEGER
    error_message TEXT
    
    started_at TIMESTAMP
    completed_at TIMESTAMP
)
```

---

## 🔍 Views for Easy Querying

### View 1: Latest Analytics

**`social_analytics_latest`** - Current state of all accounts

```sql
SELECT * FROM social_analytics_latest;
```

Returns:
- Account username, platform, status
- Latest follower count, posts count
- Total views, likes, comments
- Engagement rate
- Follower growth
- Last fetch time

### View 2: Post Performance

**`social_post_performance`** - Latest metrics for all posts

```sql
SELECT * FROM social_post_performance
WHERE platform = 'tiktok'
ORDER BY current_views DESC
LIMIT 10;
```

Returns:
- Post URL, caption, media type
- Current views, likes, comments
- Engagement rate
- Account username
- Last updated timestamp

---

## 💡 Usage Examples

### Example 1: Set Up Monitoring for TikTok Account

```sql
-- 1. Get your social_account_id from existing table
SELECT id, handle, platform FROM social_accounts 
WHERE platform = 'tiktok';

-- 2. Enable analytics monitoring
INSERT INTO social_analytics_config (
    social_account_id,
    monitoring_enabled,
    fetch_frequency,
    posts_per_fetch,
    provider_name
) VALUES (
    'your-account-uuid-here',
    TRUE,
    '24 hours',
    50,
    'rapidapi_tiktok'
);
```

### Example 2: Save Daily Snapshot

```sql
INSERT INTO social_analytics_snapshots (
    social_account_id,
    snapshot_date,
    followers_count,
    total_views,
    total_likes,
    engagement_rate
) VALUES (
    'your-account-uuid',
    CURRENT_DATE,
    1500,
    32092,
    4043,
    12.60
);
```

### Example 3: Track a Post

```sql
-- Save post
INSERT INTO social_posts_analytics (
    social_account_id,
    external_post_id,
    platform,
    post_url,
    caption,
    media_type,
    duration,
    posted_at
) VALUES (
    'your-account-uuid',
    '7574994077389786382',
    'tiktok',
    'https://www.tiktok.com/@isaiah_dupree/video/7574994077389786382',
    'Test post from MediaPoster',
    'video',
    17,
    '2024-11-20 15:00:00'
) RETURNING id;

-- Save initial metrics
INSERT INTO social_post_metrics (
    post_id,
    snapshot_date,
    likes_count,
    views_count,
    comments_count
) VALUES (
    123, -- post_id from above
    CURRENT_DATE,
    86,
    2,
    0
);
```

### Example 4: Link Post to Your Video

```sql
-- Find the post
SELECT id, post_url FROM social_posts_analytics
WHERE post_url LIKE '%7574994077389786382%';

-- Link to your video
UPDATE social_posts_analytics
SET video_id = 'your-video-uuid-here',
    clip_id = 'your-clip-uuid-here'
WHERE id = 123;

-- Or use the content mapping approach from earlier schema
```

### Example 5: Query Analytics

```sql
-- Get latest analytics for all accounts
SELECT 
    username,
    platform,
    followers_count,
    engagement_rate,
    follower_growth
FROM social_analytics_latest
WHERE monitoring_enabled = TRUE
ORDER BY followers_count DESC;

-- Get top performing posts (last 7 days)
SELECT 
    account_username,
    caption,
    current_views,
    current_likes,
    engagement_rate,
    post_url
FROM social_post_performance
WHERE posted_at >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY current_views DESC
LIMIT 10;

-- Track post growth
SELECT 
    snapshot_date,
    views_count,
    likes_count,
    engagement_rate
FROM social_post_metrics
WHERE post_id = 123
ORDER BY snapshot_date;
```

---

## 🎯 Integration with Existing System

### Links to Existing Tables

```
social_accounts (existing)
    ↓
social_analytics_config (new)
    ↓
social_analytics_snapshots (new)
    ↓
social_posts_analytics (new)
    ├── video_id → videos table (existing)
    └── clip_id → clips table (existing)
```

### Platform Support Matrix

| Platform | Account Metrics | Post Metrics | Comments | Demographics |
|----------|----------------|--------------|----------|--------------|
| TikTok | ✅ | ✅ | ✅ | ⚠️ Limited |
| Instagram | ✅ | ✅ | ✅ | ✅ |
| YouTube | ✅ | ✅ | ✅ | ✅ |
| Twitter/X | ✅ | ✅ | ✅ | ⚠️ Limited |
| Facebook | ✅ | ✅ | ✅ | ✅ |
| Pinterest | ✅ | ✅ | ⚠️ Limited | ⚠️ Limited |
| LinkedIn | ✅ | ✅ | ✅ | ✅ |
| Bluesky | ✅ | ✅ | ✅ | ⚠️ Limited |
| Threads | ✅ | ✅ | ✅ | ⚠️ Limited |

---

## 🚀 Next Steps

### 1. Add Your First Account

```bash
# Open Supabase Studio
open http://127.0.0.1:54323

# Or use Python
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
./venv/bin/python
```

```python
from sqlalchemy import create_engine, text
engine = create_engine('postgresql://postgres:postgres@127.0.0.1:54322/postgres')
conn = engine.connect()

# Get an existing social_account
result = conn.execute(text("""
    SELECT id, handle, platform FROM social_accounts LIMIT 5
"""))
for row in result:
    print(f"{row[1]} ({row[2]}): {row[0]}")

# Or insert a new one if needed
```

### 2. Update Analytics Service

Update `/Backend/services/social_analytics_service.py` to use UUID instead of INTEGER for social_account_id.

### 3. Test Data Collection

```bash
python services/fetch_social_analytics.py tiktok isaiah_dupree
```

### 4. Set Up Cron Job

```bash
python setup_analytics_cron.py
```

---

## 📊 Database Schema Diagram

```
┌─────────────────────┐
│  social_accounts    │ (Existing - Publishing)
│  ----------------   │
│  id (UUID)          │
│  platform           │
│  handle             │
│  access_token       │
└──────────┬──────────┘
           │
           ├──────────────────────────────────────┐
           │                                       │
           ▼                                       ▼
┌──────────────────────┐              ┌─────────────────────┐
│ social_analytics_    │              │ social_posts_       │
│ snapshots            │              │ analytics           │
│ ----------------     │              │ ---------------     │
│ Daily account stats  │              │ All tracked posts   │
│ • followers          │              │ • post_url         │
│ • engagement         │              │ • video_id         │
│ • growth             │              │ • clip_id          │
└──────────────────────┘              └─────────┬───────────┘
                                                 │
                                                 ▼
                                      ┌─────────────────────┐
                                      │ social_post_metrics │
                                      │ ------------------- │
                                      │ Historical tracking │
                                      │ • Hourly snapshots  │
                                      │ • Growth trends     │
                                      └─────────────────────┘
```

---

## ✅ Summary

**What You Have Now:**

✅ **12 Comprehensive Tables** covering all analytics needs  
✅ **2 Views** for easy querying  
✅ **9 Platform Support** (TikTok, Instagram, YouTube, etc.)  
✅ **Content Mapping** (link posts to videos/clips)  
✅ **Historical Tracking** (daily + hourly snapshots)  
✅ **Hashtag Analytics** (performance tracking)  
✅ **Comment Tracking** (with sentiment analysis ready)  
✅ **Demographics** (age, gender, location)  
✅ **API Usage Monitoring** (rate limits)  
✅ **Job Tracking** (fetch job history)  

**Database Location:**
- Host: `127.0.0.1`
- Port: `54322`
- Database: `postgres`
- Studio: `http://127.0.0.1:54323`

**Next Action:**
Query your new tables in Supabase Studio or start collecting analytics data!

```sql
-- See all your new tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_name LIKE 'social_%'
ORDER BY table_name;
```

🎉 **Schema is live and ready for all 9 platforms!**
