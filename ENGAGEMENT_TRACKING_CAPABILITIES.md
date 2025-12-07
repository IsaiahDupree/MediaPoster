# Social Media API Capabilities & Engagement Tracking

**Date**: November 22, 2025, 9:43 PM  
**Purpose**: Document what data we can get from APIs and how to track engaged followers

---

## ✅ What Social Media APIs Actually Provide

### Comment Data by Platform

#### **TikTok** (via scrapers/unofficial APIs)
- ✅ **Who commented**: Username, profile link
- ✅ **When**: Exact timestamp (created_at)
- ✅ **What**: Comment text
- ⚠️ **Limitations**: Rate limits, may need multiple requests
- 📊 **Follower count**: Can get from profile if we scrape it

#### **Instagram** (official API + scraping)
- ✅ **Who commented**: Username, user_id, profile_picture_url
- ✅ **When**: Timestamp (created_time)
- ✅ **What**: Comment text
- ✅ **Replies**: Can get comment replies/threads
- ⚠️ **Limitations**: Official API requires business account + permissions

#### **YouTube** (official API - BEST for comments)
- ✅ **Who commented**: Channel name, channel_id, avatar URL
- ✅ **When**: Published_at timestamp (very accurate)
- ✅ **What**: Comment text
- ✅ **Like count**: How many likes the comment got
- ✅ **Reply count**: Number of replies
- ✅ **Author stats**: Can get subscriber count if public

#### **Twitter/X** (API v2)
- ✅ **Who**: Username, user_id, verified status
- ✅ **When**: Created_at timestamp
- ✅ **What**: Tweet text (reply)
- ✅ **Engagement**: Reply count, like count, retweet count
- ⚠️ **Limitations**: API costs money for high volume

#### **Facebook** (Graph API)
- ✅ **Who**: User_id, name (if permissions)
- ✅ **When**: Created_time
- ✅ **What**: Comment message
- ⚠️ **Limitations**: Requires page permissions, privacy restrictions

#### **LinkedIn** (unofficial)
- ⚠️ **Limited**: Harder to get comment data
- ✅ **When**: Timestamp available
- ⚠️ **Who**: Limited profile data

### Date/Timestamp Accuracy

**ALL platforms provide accurate timestamps** ✅

Format varies:
- ISO 8601: `2025-11-22T21:43:00Z`
- Unix epoch: `1700688180`
- Platform-specific formats

**We should always convert to TIMESTAMPTZ in PostgreSQL for consistency**

---

## 📊 Tracking Data Over Time

### What We Can Track

#### Per Follower/User:
1. **All interactions**:
   - Comments (with text, timestamp, sentiment)
   - Likes on our posts
   - Shares/retweets
   - Saves (platform-specific)
   - Profile visits (if available)

2. **Engagement frequency**:
   - First interaction date
   - Last interaction date
   - Total interactions
   - Interactions per week/month

3. **Engagement quality**:
   - Average comment length
   - Sentiment score (positive/negative/neutral)
   - Question vs statement vs praise
   - Response to CTAs (did they comment keyword?)

4. **Growth tracking**:
   - When they became a follower
   - If they're still following
   - Their own follower growth (if we track their profile)

---

## 🏆 Identifying Most Engaging Followers

### Engagement Score Formula

```
Engagement Score = 
  (comments * 5) + 
  (likes * 1) + 
  (shares * 10) + 
  (saves * 8) +
  (profile_visits * 3) +
  (link_clicks * 15)
```

**Weighted by recency**:
- Last 7 days: 1.0x
- Last 30 days: 0.8x
- Last 90 days: 0.5x
- Older: 0.2x

### Engagement Tiers

- 🔥 **Super Fans** (score > 500): Comment frequently, high-quality engagement
- ⭐ **Active Followers** (score 100-500): Regular engagement
- 👀 **Lurkers** (score 10-100): Occasional likes/views
- 😴 **Inactive** (score < 10): Rarely engage

---

## 📋 Database Schema for Follower Engagement

### New Tables Needed

```sql
-- followers: Track individual followers across platforms
CREATE TABLE followers (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id        UUID REFERENCES workspaces(id),
  platform            TEXT NOT NULL,
  platform_user_id    TEXT NOT NULL,  -- their user_id on platform
  username            TEXT,
  display_name        TEXT,
  profile_url         TEXT,
  avatar_url          TEXT,
  follower_count      BIGINT,  -- their follower count
  verified            BOOLEAN,
  first_seen_at       TIMESTAMPTZ DEFAULT NOW(),
  last_seen_at        TIMESTAMPTZ DEFAULT NOW(),
  is_following_us     BOOLEAN DEFAULT TRUE,
  metadata            JSONB,
  created_at          TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(workspace_id, platform, platform_user_id)
);

-- follower_interactions: Every interaction they have with our content
CREATE TABLE follower_interactions (
  id                  BIGSERIAL PRIMARY KEY,
  follower_id         UUID REFERENCES followers(id),
  post_id             UUID,  -- which of our posts
  content_id          UUID REFERENCES content_items(id),
  interaction_type    TEXT NOT NULL,  -- 'comment','like','share','save','profile_visit','link_click'
  interaction_value   TEXT,  -- comment text, etc.
  sentiment_score     NUMERIC,
  occurred_at         TIMESTAMPTZ NOT NULL,
  platform            TEXT NOT NULL,
  metadata            JSONB
);
CREATE INDEX idx_follower_interactions_follower ON follower_interactions(follower_id, occurred_at DESC);
CREATE INDEX idx_follower_interactions_post ON follower_interactions(post_id);
CREATE INDEX idx_follower_interactions_content ON follower_interactions(content_id);

-- follower_engagement_scores: Computed engagement metrics
CREATE TABLE follower_engagement_scores (
  id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  follower_id         UUID REFERENCES followers(id) UNIQUE,
  total_interactions  INT DEFAULT 0,
  comment_count       INT DEFAULT 0,
  like_count          INT DEFAULT 0,
  share_count         INT DEFAULT 0,
  save_count          INT DEFAULT 0,
  engagement_score    NUMERIC DEFAULT 0,
  engagement_tier     TEXT,  -- 'super_fan','active','lurker','inactive'
  avg_sentiment       NUMERIC,
  first_interaction   TIMESTAMPTZ,
  last_interaction    TIMESTAMPTZ,
  last_calculated_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### Views for Easy Querying

```sql
-- Most engaged followers (leaderboard)
CREATE VIEW top_engaged_followers AS
SELECT 
  f.id,
  f.platform,
  f.username,
  f.display_name,
  f.profile_url,
  fes.engagement_score,
  fes.engagement_tier,
  fes.total_interactions,
  fes.comment_count,
  fes.last_interaction,
  ROW_NUMBER() OVER (ORDER BY fes.engagement_score DESC) as rank
FROM followers f
JOIN follower_engagement_scores fes ON fes.follower_id = f.id
WHERE fes.last_interaction >= NOW() - INTERVAL '90 days'
ORDER BY fes.engagement_score DESC;

-- Follower activity timeline
CREATE VIEW follower_activity_timeline AS
SELECT 
  fi.follower_id,
  f.username,
  fi.interaction_type,
  fi.occurred_at,
  fi.interaction_value,
  fi.sentiment_score,
  ci.title as content_title
FROM follower_interactions fi
JOIN followers f ON f.id = fi.follower_id
LEFT JOIN content_items ci ON ci.id = fi.content_id
ORDER BY fi.occurred_at DESC;

-- Follower cohort analysis
CREATE VIEW follower_cohorts AS
SELECT 
  DATE_TRUNC('week', f.first_seen_at) as cohort_week,
  COUNT(DISTINCT f.id) as follower_count,
  AVG(fes.engagement_score) as avg_engagement_score,
  COUNT(DISTINCT CASE WHEN fes.last_interaction >= NOW() - INTERVAL '30 days' THEN f.id END) as active_count
FROM followers f
LEFT JOIN follower_engagement_scores fes ON fes.follower_id = f.id
GROUP BY DATE_TRUNC('week', f.first_seen_at)
ORDER BY cohort_week DESC;
```

---

## 🔄 Data Collection Flow

### When Fetching Social Analytics:

```python
# Pseudocode for collecting engagement data
def collect_post_engagement(post):
    # 1. Get comments from API
    comments = api.get_comments(post.external_post_id)
    
    for comment in comments:
        # 2. Get or create follower
        follower = get_or_create_follower(
            platform=post.platform,
            platform_user_id=comment.author_id,
            username=comment.author_username,
            profile_url=comment.author_profile_url
        )
        
        # 3. Record interaction
        record_interaction(
            follower_id=follower.id,
            post_id=post.id,
            content_id=post.content_id,
            interaction_type='comment',
            interaction_value=comment.text,
            occurred_at=comment.created_at,
            sentiment_score=analyze_sentiment(comment.text)
        )
    
    # 4. Get likes (if API provides user list)
    likers = api.get_post_likers(post.external_post_id)
    for liker in likers:
        follower = get_or_create_follower(...)
        record_interaction(..., interaction_type='like')
    
    # 5. Recalculate engagement scores
    recalculate_engagement_scores()
```

### Tracking Over Time:

**Daily Job** (run at midnight):
1. Fetch new comments/interactions from yesterday
2. Update `follower_interactions` table
3. Recalculate `follower_engagement_scores`
4. Identify new super fans
5. Send notifications for super fan milestones

**Weekly Job**:
1. Deep sync: fetch ALL comments for recent posts
2. Update follower profiles (username changes, avatar, follower count)
3. Mark inactive followers (no interaction in 90 days)
4. Generate engagement reports

---

## 📊 Frontend Dashboard Features

### Engaged Followers Page (`/analytics/followers`)

#### Top Section:
- 🏆 **Leaderboard**: Top 20 most engaged followers
- 📈 **Growth Chart**: New followers + engagement trend
- 🎯 **Engagement Tiers**: Count per tier (Super Fans, Active, Lurkers, Inactive)

#### Follower Cards:
```
┌─────────────────────────────────────────────┐
│ @username (TikTok) 🔥 Super Fan             │
│ ─────────────────────────────────────────── │
│ Engagement Score: 1,247                     │
│ 23 comments • 156 likes • 4 shares          │
│ Last active: 2 hours ago                    │
│ Avg sentiment: 😊 Positive                  │
│ [View Profile] [View Activity Timeline]     │
└─────────────────────────────────────────────┘
```

#### Activity Timeline (per follower):
```
Nov 22, 2025 9:00 PM - Commented on "How to automate..."
  "This is exactly what I needed! 🔥"
  
Nov 21, 2025 3:15 PM - Liked "5 TikTok hacks..."

Nov 20, 2025 1:30 PM - Commented on "My automation setup"
  "Can you share the template?"
```

#### Filters:
- Platform (TikTok, Instagram, YouTube, etc.)
- Engagement tier
- Date range (last 7/30/90 days)
- Sentiment (positive, neutral, negative)

---

## 🎯 Use Cases

### 1. **Identify Brand Ambassadors**
- Find super fans with high follower counts
- Reach out for collaboration/UGC
- Send them exclusive content/early access

### 2. **Improve Content Strategy**
- See which followers engage with which content types
- Identify topics that resonate with engaged followers
- Tailor content to super fans

### 3. **Community Management**
- Reply to super fans first
- Thank top commenters
- Re-engage lurkers with personalized content

### 4. **Conversion Tracking**
- Which followers clicked links?
- Which followers became customers?
- ROI per engagement tier

### 5. **Churn Prevention**
- Identify followers becoming less engaged
- Send re-engagement campaigns
- Personalized content recommendations

---

## 🚀 Implementation Priority

### Phase 1: Foundation ⭐
1. Create `followers`, `follower_interactions`, `follower_engagement_scores` tables
2. Update scraping jobs to store commenter data
3. Implement `get_or_create_follower()` function

### Phase 2: Engagement Scoring 📊
4. Build engagement score calculation job
5. Create `top_engaged_followers` view
6. Add API endpoint: `GET /api/social-analytics/followers`

### Phase 3: Frontend 🎨
7. Build `/analytics/followers` page
8. Add follower leaderboard widget to Overview
9. Add "Top Commenters" to post detail pages

### Phase 4: Advanced 🔥
10. Sentiment analysis for comments
11. Follower profile enrichment (external APIs)
12. Automated outreach to super fans
13. Cohort analysis and retention tracking

---

## 📝 API Endpoints to Add

### GET /api/social-analytics/followers
List all followers with engagement scores

**Query Params**:
- `platform`: Filter by platform
- `tier`: Filter by engagement tier
- `sort`: "engagement_score" | "comment_count" | "last_interaction"
- `limit`, `offset`: Pagination

**Response**:
```json
{
  "followers": [
    {
      "id": "uuid",
      "username": "creator_amy",
      "platform": "tiktok",
      "engagement_score": 1247,
      "engagement_tier": "super_fan",
      "total_interactions": 183,
      "comment_count": 23,
      "last_interaction": "2025-11-22T21:00:00Z"
    }
  ],
  "total": 342,
  "tiers": {
    "super_fan": 12,
    "active": 87,
    "lurker": 203,
    "inactive": 40
  }
}
```

### GET /api/social-analytics/followers/{follower_id}
Get detailed follower profile + activity timeline

**Response**:
```json
{
  "follower": {
    "id": "uuid",
    "username": "creator_amy",
    "display_name": "Amy | Creator",
    "platform": "tiktok",
    "profile_url": "https://...",
    "follower_count": 15000,
    "engagement_score": 1247,
    "first_seen": "2025-09-15T...",
    "last_interaction": "2025-11-22T..."
  },
  "stats": {
    "total_interactions": 183,
    "comments": 23,
    "likes": 156,
    "shares": 4
  },
  "timeline": [
    {
      "type": "comment",
      "occurred_at": "2025-11-22T21:00:00Z",
      "content_title": "How to automate TikTok",
      "value": "This is exactly what I needed!",
      "sentiment": "positive"
    }
  ]
}
```

### GET /api/social-analytics/followers/leaderboard
Top engaged followers ranked

### GET /api/social-analytics/followers/cohorts
Cohort analysis by first_seen week

---

## ✅ Summary: What We CAN Track

| Data Point | Available? | Notes |
|------------|-----------|-------|
| **Who commented** | ✅ Yes | Username, user_id, profile URL |
| **Accurate timestamps** | ✅ Yes | All platforms provide precise timestamps |
| **Track over time** | ✅ Yes | Store all interactions with timestamps |
| **Most engaging followers** | ✅ Yes | Calculate engagement scores + rankings |
| **Comment text** | ✅ Yes | Full comment content available |
| **Sentiment** | ✅ Yes | Can analyze with NLP |
| **Follower profiles** | ⚠️ Partial | Varies by platform/API access |
| **Like authors** | ⚠️ Limited | Some platforms don't expose who liked |
| **Share authors** | ⚠️ Limited | Usually just counts, not user list |

---

**Next Step**: Implement Phase 1 (database tables + scraping updates) to start collecting follower engagement data?
