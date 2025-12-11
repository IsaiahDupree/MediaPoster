# Implementation Specifications

**Detailed Technical Specs for Priority Features**

---

## 🔥 P0 Features - Sprint 1-2

### 1. Best Time to Post

#### Database Schema
```sql
-- Engagement by hour tracking
CREATE TABLE engagement_by_hour (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID REFERENCES accounts(id),
  platform VARCHAR(50) NOT NULL,
  day_of_week INTEGER NOT NULL, -- 0=Sunday, 6=Saturday
  hour INTEGER NOT NULL, -- 0-23
  avg_engagement_rate DECIMAL(5,2),
  avg_reach INTEGER,
  avg_impressions INTEGER,
  sample_count INTEGER DEFAULT 0,
  last_updated TIMESTAMP DEFAULT NOW(),
  UNIQUE(account_id, platform, day_of_week, hour)
);

-- Optimal times per account
CREATE TABLE optimal_posting_times (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID REFERENCES accounts(id),
  platform VARCHAR(50) NOT NULL,
  day_of_week INTEGER NOT NULL,
  optimal_hour INTEGER NOT NULL,
  confidence_score DECIMAL(3,2), -- 0.00-1.00
  engagement_boost_percent DECIMAL(5,2),
  rank INTEGER, -- 1-7 for top 7 times
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX idx_optimal_times_account ON optimal_posting_times(account_id, platform);
```

#### API Endpoints
```python
# /api/optimal-times/

@router.get("/calculate/{account_id}")
async def calculate_optimal_times(account_id: str, platform: str = None):
    """
    Calculate optimal posting times based on historical engagement.
    Analyzes last 90 days of data.
    """
    pass

@router.get("/{account_id}")
async def get_optimal_times(account_id: str, platform: str = None):
    """Get stored optimal posting times for account."""
    pass

@router.post("/apply")
async def apply_optimal_time(post_id: str):
    """Apply optimal time to a scheduled post."""
    pass

@router.get("/heatmap/{account_id}")
async def get_engagement_heatmap(account_id: str, platform: str):
    """Get 7x24 engagement heatmap data for calendar display."""
    pass
```

#### Algorithm
```python
def calculate_best_times(account_id: str, platform: str) -> List[OptimalTime]:
    """
    Algorithm:
    1. Fetch all posts from last 90 days
    2. Group by day_of_week and hour
    3. Calculate average engagement rate per slot
    4. Weight recent data higher (exponential decay)
    5. Normalize across time zones
    6. Return top 7 slots ranked by score
    """
    
    # Weight factors
    RECENCY_WEIGHT = 0.8  # Recent posts weighted higher
    SAMPLE_MIN = 3  # Minimum samples for confidence
    
    # Engagement score = (likes + comments*2 + shares*3 + saves*4) / reach
    
    # Confidence = min(1.0, sample_count / 10) * consistency_score
    
    pass
```

#### Frontend Components
```tsx
// Calendar heat map overlay
interface TimeSlot {
  day: number; // 0-6
  hour: number; // 0-23
  score: number; // 0-100
  isOptimal: boolean;
}

// CalendarHeatMap.tsx
export function CalendarHeatMap({ accountId, platform }) {
  // Render 7x24 grid with color intensity
  // Green = high engagement, Red = low
  // Stars on optimal times
}

// OptimalTimeSelector.tsx
export function OptimalTimeSelector({ onSelect }) {
  // Show top 7 times with one-click selection
  // "Schedule at best time" button
}
```

---

### 2. Social Inbox / Comments

#### Database Schema
```sql
-- Unified comments table
CREATE TABLE social_comments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id UUID REFERENCES accounts(id),
  platform VARCHAR(50) NOT NULL,
  platform_comment_id VARCHAR(255) NOT NULL,
  post_id VARCHAR(255), -- Platform post ID
  parent_comment_id UUID REFERENCES social_comments(id), -- For replies
  
  -- Author info
  author_username VARCHAR(255),
  author_display_name VARCHAR(255),
  author_profile_url TEXT,
  author_avatar_url TEXT,
  
  -- Content
  content TEXT NOT NULL,
  content_type VARCHAR(50) DEFAULT 'text', -- text, image, sticker
  
  -- Metadata
  like_count INTEGER DEFAULT 0,
  reply_count INTEGER DEFAULT 0,
  sentiment VARCHAR(20), -- positive, negative, neutral
  sentiment_score DECIMAL(3,2),
  
  -- Status
  status VARCHAR(50) DEFAULT 'unread', -- unread, read, replied, archived, flagged
  is_from_creator BOOLEAN DEFAULT FALSE,
  
  -- Timestamps
  platform_created_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  
  UNIQUE(platform, platform_comment_id)
);

-- Replies sent from MediaPoster
CREATE TABLE comment_replies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  comment_id UUID REFERENCES social_comments(id),
  content TEXT NOT NULL,
  status VARCHAR(50) DEFAULT 'pending', -- pending, sent, failed
  platform_reply_id VARCHAR(255),
  sent_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Saved replies / templates
CREATE TABLE saved_replies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID,
  title VARCHAR(255) NOT NULL,
  content TEXT NOT NULL,
  category VARCHAR(100),
  use_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_comments_account_status ON social_comments(account_id, status);
CREATE INDEX idx_comments_platform ON social_comments(platform, platform_created_at DESC);
CREATE INDEX idx_comments_sentiment ON social_comments(sentiment);
```

#### API Endpoints
```python
# /api/inbox/

@router.get("/list")
async def list_comments(
    account_id: str = None,
    platform: str = None,
    status: str = None,  # unread, read, replied, archived, flagged
    sentiment: str = None,  # positive, negative, neutral
    search: str = None,
    limit: int = 50,
    offset: int = 0
):
    """List comments with filtering."""
    pass

@router.get("/{comment_id}")
async def get_comment(comment_id: str):
    """Get single comment with thread."""
    pass

@router.post("/{comment_id}/reply")
async def reply_to_comment(comment_id: str, content: str):
    """Send reply to comment via platform API."""
    pass

@router.patch("/{comment_id}/status")
async def update_status(comment_id: str, status: str):
    """Update comment status (read, archived, flagged)."""
    pass

@router.post("/bulk-action")
async def bulk_action(comment_ids: List[str], action: str):
    """Bulk update status for multiple comments."""
    pass

@router.post("/sync")
async def sync_comments(account_id: str = None):
    """Sync comments from all connected platforms."""
    pass

@router.get("/stats")
async def get_inbox_stats(account_id: str = None):
    """Get inbox statistics (unread count, by platform, etc.)."""
    pass

# Saved replies
@router.get("/saved-replies")
async def list_saved_replies():
    pass

@router.post("/saved-replies")
async def create_saved_reply(title: str, content: str, category: str = None):
    pass

# AI suggestions
@router.post("/suggest-reply")
async def suggest_reply(comment_id: str):
    """Generate AI-suggested reply for comment."""
    pass
```

#### Platform Integrations
```python
# services/comment_sync.py

class CommentSyncService:
    async def sync_instagram(self, account_id: str):
        """
        Instagram Graph API:
        GET /{media-id}/comments
        Fields: id, text, timestamp, username, like_count, replies
        """
        pass
    
    async def sync_tiktok(self, account_id: str):
        """
        TikTok API:
        GET /video/comment/list/
        """
        pass
    
    async def sync_youtube(self, account_id: str):
        """
        YouTube Data API:
        GET /commentThreads
        """
        pass
    
    async def sync_facebook(self, account_id: str):
        """
        Facebook Graph API:
        GET /{post-id}/comments
        """
        pass

class CommentReplyService:
    async def reply_instagram(self, comment_id: str, message: str):
        """POST /{comment-id}/replies"""
        pass
    
    async def reply_tiktok(self, comment_id: str, message: str):
        """POST /video/comment/reply/"""
        pass
```

#### Frontend Components
```tsx
// /inbox/page.tsx

interface Comment {
  id: string;
  platform: 'instagram' | 'tiktok' | 'youtube' | 'facebook';
  author: {
    username: string;
    displayName: string;
    avatarUrl: string;
  };
  content: string;
  likeCount: number;
  replyCount: number;
  sentiment: 'positive' | 'negative' | 'neutral';
  status: 'unread' | 'read' | 'replied' | 'archived' | 'flagged';
  createdAt: string;
  postTitle?: string;
}

// Components needed:
// - InboxSidebar (filters, stats)
// - CommentList (virtualized for performance)
// - CommentCard (single comment display)
// - CommentThread (parent + replies)
// - ReplyComposer (with saved replies, AI suggest)
// - BulkActionBar (when items selected)
```

---

## 🟡 P1 Features - Sprint 3

### 3. First Comment Scheduling

#### Database Changes
```sql
ALTER TABLE scheduled_posts 
ADD COLUMN first_comment TEXT,
ADD COLUMN first_comment_status VARCHAR(50) DEFAULT 'pending';
```

#### API Changes
```python
class ScheduledPostCreate(BaseModel):
    # ... existing fields
    first_comment: Optional[str] = None

@router.post("/posts/{post_id}/first-comment")
async def post_first_comment(post_id: str):
    """Post the first comment after main post is published."""
    pass
```

#### Publishing Flow
```python
async def publish_post(post_id: str):
    post = await get_post(post_id)
    
    # 1. Publish main post
    result = await publish_to_platform(post)
    
    # 2. If first comment exists, post it
    if post.first_comment and result.success:
        await asyncio.sleep(2)  # Brief delay
        await post_comment(
            platform=post.platform,
            post_id=result.platform_post_id,
            content=post.first_comment
        )
```

---

### 4. Hashtag Manager

#### Database Schema
```sql
CREATE TABLE hashtag_groups (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID,
  name VARCHAR(255) NOT NULL,
  hashtags TEXT[] NOT NULL, -- Array of hashtags
  color VARCHAR(20), -- For UI display
  use_count INTEGER DEFAULT 0,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE hashtag_analytics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hashtag VARCHAR(255) NOT NULL,
  platform VARCHAR(50) NOT NULL,
  avg_reach INTEGER,
  avg_engagement DECIMAL(5,2),
  post_count INTEGER,
  last_used TIMESTAMP,
  UNIQUE(hashtag, platform)
);
```

#### API Endpoints
```python
@router.get("/groups")
async def list_hashtag_groups(workspace_id: str = None):
    pass

@router.post("/groups")
async def create_hashtag_group(name: str, hashtags: List[str], color: str = None):
    pass

@router.put("/groups/{group_id}")
async def update_hashtag_group(group_id: str, name: str = None, hashtags: List[str] = None):
    pass

@router.delete("/groups/{group_id}")
async def delete_hashtag_group(group_id: str):
    pass

@router.get("/suggest")
async def suggest_hashtags(content: str = None, existing: List[str] = None):
    """AI-powered hashtag suggestions."""
    pass

@router.get("/analytics")
async def get_hashtag_analytics(hashtags: List[str] = None):
    pass
```

---

## 🟢 P2 Features - Sprint 4-5

### 5. Link in Bio

#### Database Schema
```sql
CREATE TABLE link_in_bio_pages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID,
  subdomain VARCHAR(100) UNIQUE NOT NULL, -- username.mediaposter.link
  
  -- Profile
  title VARCHAR(255),
  bio TEXT,
  avatar_url TEXT,
  
  -- Theme
  theme_id VARCHAR(50) DEFAULT 'default',
  background_color VARCHAR(20),
  text_color VARCHAR(20),
  button_color VARCHAR(20),
  button_style VARCHAR(20), -- filled, outline, rounded
  font_family VARCHAR(50),
  
  -- Settings
  show_branding BOOLEAN DEFAULT TRUE,
  custom_css TEXT,
  
  -- Analytics
  total_views INTEGER DEFAULT 0,
  total_clicks INTEGER DEFAULT 0,
  
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE link_in_bio_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  page_id UUID REFERENCES link_in_bio_pages(id) ON DELETE CASCADE,
  
  -- Content
  title VARCHAR(255) NOT NULL,
  url TEXT NOT NULL,
  icon VARCHAR(50), -- emoji or icon name
  thumbnail_url TEXT,
  
  -- Display
  display_order INTEGER DEFAULT 0,
  is_featured BOOLEAN DEFAULT FALSE,
  is_visible BOOLEAN DEFAULT TRUE,
  
  -- Analytics
  click_count INTEGER DEFAULT 0,
  
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE link_in_bio_social_links (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  page_id UUID REFERENCES link_in_bio_pages(id) ON DELETE CASCADE,
  platform VARCHAR(50) NOT NULL, -- instagram, tiktok, youtube, etc.
  url TEXT NOT NULL,
  display_order INTEGER DEFAULT 0
);

CREATE TABLE link_in_bio_analytics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  page_id UUID REFERENCES link_in_bio_pages(id),
  link_id UUID REFERENCES link_in_bio_links(id),
  event_type VARCHAR(50), -- page_view, link_click
  referrer TEXT,
  user_agent TEXT,
  country VARCHAR(10),
  created_at TIMESTAMP DEFAULT NOW()
);
```

#### API Endpoints
```python
# Page management
@router.get("/pages")
@router.post("/pages")
@router.get("/pages/{page_id}")
@router.put("/pages/{page_id}")
@router.delete("/pages/{page_id}")

# Links
@router.get("/pages/{page_id}/links")
@router.post("/pages/{page_id}/links")
@router.put("/pages/{page_id}/links/{link_id}")
@router.delete("/pages/{page_id}/links/{link_id}")
@router.post("/pages/{page_id}/links/reorder")

# Public page
@router.get("/p/{subdomain}")  # Returns page data
@router.post("/p/{subdomain}/track")  # Track view/click

# Analytics
@router.get("/pages/{page_id}/analytics")
```

---

### 6. Holiday Calendar

#### Data File
```json
// data/holidays.json
{
  "holidays": [
    {
      "date": "2025-01-01",
      "name": "New Year's Day",
      "emoji": "🎉",
      "type": "major",
      "regions": ["global"],
      "content_ideas": [
        "New year, new goals - share your resolutions",
        "Year in review post",
        "Thank your followers for the past year"
      ]
    },
    {
      "date": "2025-02-14",
      "name": "Valentine's Day",
      "emoji": "❤️",
      "type": "major",
      "regions": ["us", "uk", "ca"],
      "content_ideas": [
        "Share what you love about your work",
        "Customer appreciation post",
        "Self-love content"
      ]
    },
    // ... more holidays
  ],
  "social_media_days": [
    {
      "date": "2025-03-30",
      "name": "National Social Media Day",
      "emoji": "📱",
      "content_ideas": [
        "Behind the scenes of your social strategy",
        "Tips for your followers"
      ]
    }
    // ... more awareness days
  ]
}
```

#### API Endpoints
```python
@router.get("/holidays")
async def get_holidays(
    start_date: str,
    end_date: str,
    regions: List[str] = ["us", "global"]
):
    """Get holidays for date range."""
    pass

@router.get("/holidays/{date}")
async def get_holiday_details(date: str):
    """Get holiday with content suggestions."""
    pass
```

---

## 📁 File Structure

```
Backend/
├── api/
│   ├── optimal_posting_times.py  # ✅ EXISTS
│   ├── inbox.py                  # NEW
│   ├── hashtag_manager.py        # NEW
│   ├── link_in_bio.py            # NEW
│   └── holidays.py               # NEW
├── services/
│   ├── comment_sync.py           # NEW
│   ├── comment_reply.py          # NEW
│   ├── sentiment_analysis.py     # NEW
│   └── best_time_calculator.py   # NEW
└── data/
    └── holidays.json             # NEW

dashboard/app/(dashboard)/
├── visual-planner/               # ✅ EXISTS
├── carousel-creator/             # ✅ EXISTS
├── ai-chat/                      # ✅ EXISTS
├── inbox/                        # NEW
│   └── page.tsx
├── hashtags/                     # NEW
│   └── page.tsx
├── link-in-bio/                  # NEW
│   ├── page.tsx
│   └── [pageId]/
│       └── page.tsx
└── schedule/
    └── page.tsx                  # ENHANCE with heat map
```

---

## ✅ Implementation Checklist

### Week 1-2: P0 Features
- [ ] Best Time to Post
  - [ ] Database schema
  - [ ] Calculation algorithm
  - [ ] API endpoints
  - [ ] Calendar heat map UI
  - [ ] Quick-schedule button
- [ ] Social Inbox (Start)
  - [ ] Database schema
  - [ ] API design
  - [ ] Instagram integration

### Week 3-4: Social Inbox Complete
- [ ] Social Inbox
  - [ ] TikTok integration
  - [ ] YouTube integration
  - [ ] Facebook integration
  - [ ] Reply functionality
  - [ ] Inbox UI
  - [ ] Filtering & search
  - [ ] Bulk actions
  - [ ] Saved replies

### Week 5-6: Content Tools
- [ ] First Comment
  - [ ] Schema update
  - [ ] UI in composer
  - [ ] Publishing flow
- [ ] Hashtag Manager
  - [ ] Database schema
  - [ ] CRUD API
  - [ ] Manager UI
  - [ ] Insert in composer
- [ ] Holiday Calendar
  - [ ] Data file
  - [ ] API
  - [ ] Calendar overlay

### Week 7-8: Link in Bio
- [ ] Page builder
- [ ] Theme system
- [ ] Public page serving
- [ ] Analytics

---

**Last Updated:** December 8, 2025
