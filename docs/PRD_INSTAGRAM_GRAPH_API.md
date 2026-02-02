# PRD: Instagram Graph API Integration

**Version:** 1.0  
**Date:** February 1, 2026  
**Status:** Ready for Implementation  
**Track:** T6.1 Platform Integrations  
**Effort:** 2-3 weeks  
**Priority:** 🟢 Medium

---

## Executive Summary

Integrate Instagram's official Graph API to access owned account data, official insights, and publishing capabilities—replacing/complementing the current RapidAPI scraping approach for owned accounts.

---

## Current vs Target State

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    INSTAGRAM DATA ACCESS COMPARISON                                  │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         CURRENT STATE                                        │   │
│  │                                                                              │   │
│  │   ┌─────────────────┐                    ┌─────────────────────────────┐    │   │
│  │   │   RapidAPI      │                    │    Safari Automation        │    │   │
│  │   │                 │                    │                             │    │   │
│  │   │  ✅ Any account │                    │  ✅ DMs                      │    │   │
│  │   │  ✅ Posts/Reels │                    │  ✅ Comments                 │    │   │
│  │   │  ✅ Profiles    │                    │  ✅ Posting                  │    │   │
│  │   │                 │                    │                             │    │   │
│  │   │  ❌ Rate limited│                    │  ❌ Fragile selectors       │    │   │
│  │   │  ❌ No insights │                    │  ❌ No API metrics          │    │   │
│  │   │  ❌ No owned    │                    │  ❌ Manual session          │    │   │
│  │   │     account data│                    │                             │    │   │
│  │   └─────────────────┘                    └─────────────────────────────┘    │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│                                    ▼                                                 │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         TARGET STATE                                         │   │
│  │                                                                              │   │
│  │   ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────────┐   │   │
│  │   │  Graph API      │ │   RapidAPI      │ │    Safari Automation        │   │   │
│  │   │  (Owned)        │ │   (Discovery)   │ │    (Fallback)               │   │   │
│  │   │                 │ │                 │ │                             │   │   │
│  │   │  ✅ Official    │ │  ✅ Competitor  │ │  ✅ DMs (no API)            │   │   │
│  │   │     insights    │ │     research    │ │  ✅ Stories                 │   │   │
│  │   │  ✅ Real-time   │ │  ✅ Trending    │ │  ✅ Edge cases              │   │   │
│  │   │     metrics     │ │     content     │ │                             │   │   │
│  │   │  ✅ Follower    │ │                 │ │                             │   │   │
│  │   │     activity    │ │                 │ │                             │   │   │
│  │   │  ✅ Publishing  │ │                 │ │                             │   │   │
│  │   │                 │ │                 │ │                             │   │   │
│  │   └─────────────────┘ └─────────────────┘ └─────────────────────────────┘   │   │
│  │                                                                              │   │
│  │   Strategy: Use Graph API for owned accounts, RapidAPI for discovery,       │   │
│  │             Safari for features without API support                          │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                       INSTAGRAM GRAPH API INTEGRATION                                │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         OAUTH FLOW                                           │   │
│  │                                                                              │   │
│  │   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────────┐     │   │
│  │   │  User    │───▶│  Login   │───▶│ Authorize│───▶│   Token          │     │   │
│  │   │  Clicks  │    │  with FB │    │  Scopes  │    │   Exchange       │     │   │
│  │   └──────────┘    └──────────┘    └──────────┘    └────────┬─────────┘     │   │
│  │                                                             │                │   │
│  │   Required Scopes:                                          │                │   │
│  │   • instagram_basic                                         │                │   │
│  │   • instagram_content_publish                               │                │   │
│  │   • instagram_manage_comments                               │                │   │
│  │   • instagram_manage_insights                               │                │   │
│  │   • pages_show_list                                         │                │   │
│  │   • pages_read_engagement                                   ▼                │   │
│  │                                                  ┌──────────────────────┐   │   │
│  │                                                  │  Store Access Token  │   │   │
│  │                                                  │  + Page ID           │   │   │
│  │                                                  │  + IG Account ID     │   │   │
│  │                                                  └──────────────────────┘   │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                           │                                         │
│                                           ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         GRAPH API CLIENT                                     │   │
│  │                                                                              │   │
│  │   Base URL: https://graph.facebook.com/v19.0                                │   │
│  │                                                                              │   │
│  │   ┌─────────────────────────────────────────────────────────────────────┐  │   │
│  │   │                    AVAILABLE ENDPOINTS                              │  │   │
│  │   ├─────────────────────────────────────────────────────────────────────┤  │   │
│  │   │                                                                     │  │   │
│  │   │  Account & Profile:                                                 │  │   │
│  │   │  GET /{ig-user-id}                     → Profile info               │  │   │
│  │   │  GET /{ig-user-id}/media               → Media list                 │  │   │
│  │   │                                                                     │  │   │
│  │   │  Insights (Official Metrics):                                       │  │   │
│  │   │  GET /{ig-user-id}/insights            → Account insights           │  │   │
│  │   │  GET /{ig-media-id}/insights           → Media insights             │  │   │
│  │   │                                                                     │  │   │
│  │   │  Publishing:                                                        │  │   │
│  │   │  POST /{ig-user-id}/media              → Create container           │  │   │
│  │   │  POST /{ig-user-id}/media_publish      → Publish container          │  │   │
│  │   │                                                                     │  │   │
│  │   │  Comments:                                                          │  │   │
│  │   │  GET /{ig-media-id}/comments           → Get comments               │  │   │
│  │   │  POST /{ig-media-id}/comments          → Reply to comment           │  │   │
│  │   │                                                                     │  │   │
│  │   │  Stories:                                                           │  │   │
│  │   │  GET /{ig-user-id}/stories             → Get stories                │  │   │
│  │   │                                                                     │  │   │
│  │   └─────────────────────────────────────────────────────────────────────┘  │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                           │                                         │
│           ┌───────────────────────────────┼───────────────────────────────┐        │
│           ▼                               ▼                               ▼        │
│  ┌─────────────────────┐  ┌───────────────────────────┐  ┌─────────────────────┐  │
│  │   INSIGHTS SERVICE  │  │    PUBLISHING SERVICE     │  │  ENGAGEMENT SERVICE │  │
│  │                     │  │                           │  │                     │  │
│  │  • Account metrics  │  │  • Image posts            │  │  • Fetch comments   │  │
│  │  • Media performance│  │  • Video/Reels            │  │  • Reply to comments│  │
│  │  • Audience data    │  │  • Carousels              │  │  • Get mentions     │  │
│  │  • Online followers │  │  • Stories                │  │  • Sync to inbox    │  │
│  │  • Demographics     │  │  • Schedule via Blotato   │  │                     │  │
│  │                     │  │                           │  │                     │  │
│  └─────────────────────┘  └───────────────────────────┘  └─────────────────────┘  │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Available Insights

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         INSTAGRAM INSIGHTS AVAILABLE                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                    ACCOUNT-LEVEL INSIGHTS                                    │   │
│  │                                                                              │   │
│  │  Metric                      │ Description                    │ Period       │   │
│  │  ────────────────────────────┼────────────────────────────────┼────────────  │   │
│  │  impressions                 │ Total impressions              │ day/week     │   │
│  │  reach                       │ Unique accounts reached        │ day/week     │   │
│  │  follower_count              │ Total followers                │ lifetime     │   │
│  │  profile_views               │ Profile visits                 │ day          │   │
│  │  website_clicks              │ Bio link clicks                │ day          │   │
│  │  email_contacts              │ Email button taps              │ day          │   │
│  │  get_directions_clicks       │ Direction taps                 │ day          │   │
│  │  phone_call_clicks           │ Call button taps               │ day          │   │
│  │  text_message_clicks         │ Text button taps               │ day          │   │
│  │                                                                              │   │
│  │  AUDIENCE DATA:                                                              │   │
│  │  online_followers            │ When followers are online      │ lifetime     │   │
│  │  audience_city               │ Top cities                     │ lifetime     │   │
│  │  audience_country            │ Top countries                  │ lifetime     │   │
│  │  audience_gender_age         │ Gender/age breakdown           │ lifetime     │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                    MEDIA-LEVEL INSIGHTS                                      │   │
│  │                                                                              │   │
│  │  Metric                      │ Description                    │ Available    │   │
│  │  ────────────────────────────┼────────────────────────────────┼────────────  │   │
│  │  impressions                 │ Total times seen               │ All media    │   │
│  │  reach                       │ Unique accounts                │ All media    │   │
│  │  engagement                  │ Likes + comments + saves       │ All media    │   │
│  │  saved                       │ Times saved                    │ All media    │   │
│  │  likes                       │ Like count                     │ All media    │   │
│  │  comments                    │ Comment count                  │ All media    │   │
│  │  shares                      │ Share count                    │ All media    │   │
│  │  video_views                 │ 3-second views                 │ Video/Reels  │   │
│  │  plays                       │ Total plays                    │ Reels        │   │
│  │  total_interactions          │ All interactions               │ Reels        │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                    STORY INSIGHTS                                            │   │
│  │                                                                              │   │
│  │  Metric                      │ Description                                   │   │
│  │  ────────────────────────────┼────────────────────────────────────────────   │   │
│  │  impressions                 │ Total views                                   │   │
│  │  reach                       │ Unique viewers                                │   │
│  │  taps_forward                │ Taps to next story                           │   │
│  │  taps_back                   │ Taps to previous story                       │   │
│  │  exits                       │ Story exits                                   │   │
│  │  replies                     │ DM replies to story                          │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

```sql
-- Migration: 20260201_instagram_graph_api.sql

-- Instagram accounts (connected via OAuth)
CREATE TABLE instagram_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identity
    ig_user_id VARCHAR(50) NOT NULL UNIQUE, -- Instagram user ID
    username VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    profile_picture_url TEXT,
    bio TEXT,
    website TEXT,
    
    -- Connected Facebook page
    fb_page_id VARCHAR(50),
    fb_page_name VARCHAR(255),
    
    -- OAuth tokens
    access_token TEXT NOT NULL,
    token_expires_at TIMESTAMPTZ,
    refresh_token TEXT,
    
    -- Account type
    account_type VARCHAR(20), -- 'BUSINESS', 'CREATOR', 'PERSONAL'
    
    -- Stats (cached)
    follower_count INTEGER,
    following_count INTEGER,
    media_count INTEGER,
    
    -- Link to Blotato (if exists)
    blotato_account_id INTEGER,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_synced_at TIMESTAMPTZ,
    sync_error TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Account-level insights (daily snapshots)
CREATE TABLE ig_account_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES instagram_accounts(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    
    -- Reach & Impressions
    impressions INTEGER,
    reach INTEGER,
    
    -- Profile activity
    profile_views INTEGER,
    website_clicks INTEGER,
    email_contacts INTEGER,
    phone_call_clicks INTEGER,
    get_directions_clicks INTEGER,
    text_message_clicks INTEGER,
    
    -- Followers
    follower_count INTEGER,
    follower_change INTEGER, -- Delta from previous day
    
    -- Engagement
    total_interactions INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(account_id, date)
);

-- Audience demographics
CREATE TABLE ig_audience_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES instagram_accounts(id) ON DELETE CASCADE,
    
    -- Online times (hourly for each day of week)
    online_followers JSONB,
    -- Example: {"monday": {"0": 100, "1": 50, ...}, "tuesday": {...}}
    
    -- Top cities
    audience_city JSONB,
    -- Example: [{"city": "New York", "count": 1000}, ...]
    
    -- Top countries
    audience_country JSONB,
    -- Example: [{"country": "US", "count": 5000}, ...]
    
    -- Gender/Age breakdown
    audience_gender_age JSONB,
    -- Example: {"M.18-24": 500, "F.25-34": 800, ...}
    
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Media insights (individual posts/reels)
CREATE TABLE ig_media_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES instagram_accounts(id) ON DELETE CASCADE,
    
    -- Media identification
    ig_media_id VARCHAR(50) NOT NULL,
    media_type VARCHAR(20), -- 'IMAGE', 'VIDEO', 'CAROUSEL_ALBUM', 'REELS'
    permalink TEXT,
    thumbnail_url TEXT,
    caption TEXT,
    
    -- Timestamps
    ig_timestamp TIMESTAMPTZ, -- When posted on Instagram
    
    -- Metrics
    impressions INTEGER,
    reach INTEGER,
    engagement INTEGER,
    likes INTEGER,
    comments INTEGER,
    saved INTEGER,
    shares INTEGER,
    
    -- Video-specific
    video_views INTEGER,
    plays INTEGER,
    
    -- Link to content library
    content_id UUID, -- Reference to content table
    
    -- Sync
    last_synced_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(account_id, ig_media_id)
);

-- Story insights
CREATE TABLE ig_story_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id UUID REFERENCES instagram_accounts(id) ON DELETE CASCADE,
    
    ig_story_id VARCHAR(50) NOT NULL,
    media_url TEXT,
    
    -- Metrics
    impressions INTEGER,
    reach INTEGER,
    taps_forward INTEGER,
    taps_back INTEGER,
    exits INTEGER,
    replies INTEGER,
    
    -- Timestamps
    ig_timestamp TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(account_id, ig_story_id)
);

-- Indexes
CREATE INDEX idx_ig_accounts_username ON instagram_accounts(username);
CREATE INDEX idx_ig_insights_date ON ig_account_insights(date);
CREATE INDEX idx_ig_insights_account ON ig_account_insights(account_id);
CREATE INDEX idx_ig_media_account ON ig_media_insights(account_id);
CREATE INDEX idx_ig_media_timestamp ON ig_media_insights(ig_timestamp DESC);
```

---

## API Endpoints

### OAuth

```yaml
# GET /api/instagram/auth/url
# Get OAuth authorization URL
Response:
  url: string
  state: string

# GET /api/instagram/auth/callback
# OAuth callback (redirect from Facebook)
Query:
  code: string
  state: string
Response:
  redirect to dashboard with success/error

# POST /api/instagram/auth/refresh
# Refresh access token
Request:
  account_id: uuid
Response:
  success: boolean
  expires_at: datetime
```

### Accounts

```yaml
# GET /api/instagram/accounts
# List connected accounts
Response:
  accounts: InstagramAccount[]

# GET /api/instagram/accounts/{id}
# Get account details with recent insights
Response:
  account: InstagramAccount
  recent_insights: AccountInsight[]
  audience: AudienceData

# DELETE /api/instagram/accounts/{id}
# Disconnect account

# POST /api/instagram/accounts/{id}/sync
# Force sync account data
Response:
  synced: true
  insights_updated: number
  media_updated: number
```

### Insights

```yaml
# GET /api/instagram/accounts/{id}/insights
# Get account insights
Query:
  date_from: date
  date_to: date
  metrics: string[] (optional)
Response:
  insights: AccountInsight[]
  summary:
    avg_reach: number
    total_impressions: number
    follower_growth: number

# GET /api/instagram/accounts/{id}/audience
# Get audience demographics
Response:
  audience: AudienceData
  best_posting_times: [{day, hour, score}]

# GET /api/instagram/accounts/{id}/media
# Get media with insights
Query:
  limit: number
  cursor: string
  media_type: string
Response:
  media: MediaInsight[]
  next_cursor: string

# GET /api/instagram/media/{id}/insights
# Get specific media insights
Response:
  media: MediaInsight
  insights_history: [{date, impressions, reach}]
```

### Publishing

```yaml
# POST /api/instagram/accounts/{id}/publish
# Publish content (creates container + publishes)
Request:
  media_type: "IMAGE" | "VIDEO" | "CAROUSEL" | "REELS"
  media_url: string (or)
  media_urls: string[] (for carousel)
  caption: string
  share_to_feed: boolean (for reels)
  location_id: string (optional)
Response:
  ig_media_id: string
  permalink: string

# GET /api/instagram/accounts/{id}/container/{container_id}/status
# Check publishing status
Response:
  status: "IN_PROGRESS" | "FINISHED" | "ERROR"
  status_code: string
```

### Comments

```yaml
# GET /api/instagram/media/{id}/comments
# Get comments on media
Response:
  comments: Comment[]

# POST /api/instagram/comments/{id}/reply
# Reply to a comment
Request:
  message: string
Response:
  comment_id: string

# POST /api/instagram/comments/{id}/hide
# Hide a comment

# DELETE /api/instagram/comments/{id}
# Delete a comment
```

---

## Core Services

### 1. Instagram Graph API Client

```python
# Backend/services/instagram/graph_api_client.py

import httpx
from typing import Optional, List

class InstagramGraphAPIClient:
    """Instagram Graph API client."""
    
    BASE_URL = "https://graph.facebook.com/v19.0"
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.client = httpx.AsyncClient()
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict = None,
        data: dict = None
    ) -> dict:
        """Make API request."""
        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        params["access_token"] = self.access_token
        
        response = await self.client.request(
            method=method,
            url=url,
            params=params,
            json=data
        )
        
        if response.status_code != 200:
            error = response.json().get("error", {})
            raise InstagramAPIError(
                code=error.get("code"),
                message=error.get("message")
            )
        
        return response.json()
    
    # ==================== Account ====================
    
    async def get_account(self, ig_user_id: str) -> dict:
        """Get account info."""
        return await self._request(
            "GET",
            ig_user_id,
            params={
                "fields": "id,username,name,profile_picture_url,biography,website,followers_count,follows_count,media_count"
            }
        )
    
    # ==================== Insights ====================
    
    async def get_account_insights(
        self,
        ig_user_id: str,
        metrics: List[str],
        period: str = "day",
        since: int = None,
        until: int = None
    ) -> dict:
        """Get account-level insights."""
        params = {
            "metric": ",".join(metrics),
            "period": period
        }
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        
        return await self._request(
            "GET",
            f"{ig_user_id}/insights",
            params=params
        )
    
    async def get_media_insights(
        self,
        ig_media_id: str,
        metrics: List[str]
    ) -> dict:
        """Get media-level insights."""
        return await self._request(
            "GET",
            f"{ig_media_id}/insights",
            params={"metric": ",".join(metrics)}
        )
    
    async def get_audience_demographics(
        self,
        ig_user_id: str
    ) -> dict:
        """Get audience data."""
        return await self._request(
            "GET",
            f"{ig_user_id}/insights",
            params={
                "metric": "audience_city,audience_country,audience_gender_age,online_followers",
                "period": "lifetime"
            }
        )
    
    # ==================== Media ====================
    
    async def get_media_list(
        self,
        ig_user_id: str,
        limit: int = 25,
        after: str = None
    ) -> dict:
        """Get list of media."""
        params = {
            "fields": "id,media_type,media_url,thumbnail_url,permalink,caption,timestamp,like_count,comments_count",
            "limit": limit
        }
        if after:
            params["after"] = after
        
        return await self._request(
            "GET",
            f"{ig_user_id}/media",
            params=params
        )
    
    # ==================== Publishing ====================
    
    async def create_media_container(
        self,
        ig_user_id: str,
        media_type: str,
        media_url: str = None,
        caption: str = None,
        **kwargs
    ) -> str:
        """Create media container (step 1 of publishing)."""
        data = {}
        
        if media_type == "IMAGE":
            data["image_url"] = media_url
        elif media_type in ["VIDEO", "REELS"]:
            data["video_url"] = media_url
            data["media_type"] = media_type
        
        if caption:
            data["caption"] = caption
        
        data.update(kwargs)
        
        result = await self._request(
            "POST",
            f"{ig_user_id}/media",
            data=data
        )
        return result["id"]
    
    async def publish_media(
        self,
        ig_user_id: str,
        container_id: str
    ) -> str:
        """Publish media container (step 2)."""
        result = await self._request(
            "POST",
            f"{ig_user_id}/media_publish",
            data={"creation_id": container_id}
        )
        return result["id"]
    
    async def get_container_status(
        self,
        container_id: str
    ) -> dict:
        """Check publishing status."""
        return await self._request(
            "GET",
            container_id,
            params={"fields": "status_code"}
        )
    
    # ==================== Comments ====================
    
    async def get_comments(
        self,
        ig_media_id: str,
        limit: int = 50
    ) -> dict:
        """Get comments on media."""
        return await self._request(
            "GET",
            f"{ig_media_id}/comments",
            params={
                "fields": "id,text,username,timestamp,like_count,replies{id,text,username,timestamp}",
                "limit": limit
            }
        )
    
    async def reply_to_comment(
        self,
        ig_comment_id: str,
        message: str
    ) -> str:
        """Reply to a comment."""
        result = await self._request(
            "POST",
            f"{ig_comment_id}/replies",
            data={"message": message}
        )
        return result["id"]
```

### 2. Insights Sync Service

```python
# Backend/services/instagram/insights_sync.py

class InstagramInsightsSyncService:
    """Sync Instagram insights to database."""
    
    ACCOUNT_METRICS = [
        "impressions", "reach", "profile_views",
        "website_clicks", "follower_count"
    ]
    
    MEDIA_METRICS = [
        "impressions", "reach", "engagement",
        "saved", "video_views", "plays"
    ]
    
    async def sync_account(self, account_id: UUID) -> SyncResult:
        """Sync all data for an account."""
        account = await self.repo.get(account_id)
        client = InstagramGraphAPIClient(account.access_token)
        
        results = {
            "insights_synced": 0,
            "media_synced": 0,
            "audience_synced": False
        }
        
        # 1. Sync account insights (last 30 days)
        try:
            insights = await client.get_account_insights(
                account.ig_user_id,
                metrics=self.ACCOUNT_METRICS,
                period="day"
            )
            results["insights_synced"] = await self.store_account_insights(
                account_id, insights
            )
        except InstagramAPIError as e:
            logger.error(f"Failed to sync insights: {e}")
        
        # 2. Sync audience demographics
        try:
            audience = await client.get_audience_demographics(
                account.ig_user_id
            )
            await self.store_audience_data(account_id, audience)
            results["audience_synced"] = True
        except InstagramAPIError as e:
            logger.error(f"Failed to sync audience: {e}")
        
        # 3. Sync media insights
        try:
            media_list = await client.get_media_list(
                account.ig_user_id,
                limit=50
            )
            for media in media_list.get("data", []):
                media_insights = await client.get_media_insights(
                    media["id"],
                    metrics=self.MEDIA_METRICS
                )
                await self.store_media_insights(account_id, media, media_insights)
                results["media_synced"] += 1
        except InstagramAPIError as e:
            logger.error(f"Failed to sync media: {e}")
        
        # Update last synced
        account.last_synced_at = datetime.now()
        await self.repo.update(account)
        
        return SyncResult(**results)
    
    async def get_best_posting_times(
        self,
        account_id: UUID
    ) -> List[dict]:
        """Analyze online_followers to find best posting times."""
        audience = await self.repo.get_audience_data(account_id)
        
        if not audience or not audience.online_followers:
            return []
        
        # Flatten and score each time slot
        time_scores = []
        for day, hours in audience.online_followers.items():
            for hour, count in hours.items():
                time_scores.append({
                    "day": day,
                    "hour": int(hour),
                    "online_count": count,
                    "score": count  # Could add more factors
                })
        
        # Sort by score and return top times
        time_scores.sort(key=lambda x: x["score"], reverse=True)
        return time_scores[:10]
```

---

## Implementation Phases

### Phase 1: OAuth & Account Connection (Days 1-4)
| Task | Effort |
|------|--------|
| Facebook App setup | 2h |
| OAuth flow implementation | 8h |
| Token storage & refresh | 4h |
| Account connection UI | 8h |
| Account list page | 4h |

### Phase 2: Insights Fetching (Days 5-9)
| Task | Effort |
|------|--------|
| Graph API client | 8h |
| Account insights sync | 6h |
| Media insights sync | 6h |
| Audience data sync | 4h |
| Best posting times calc | 4h |

### Phase 3: Dashboard & Analytics (Days 10-14)
| Task | Effort |
|------|--------|
| Insights dashboard UI | 10h |
| Media performance view | 6h |
| Audience demographics UI | 6h |
| Comparison with Blotato data | 4h |

### Phase 4: Publishing & Engagement (Days 15-20)
| Task | Effort |
|------|--------|
| Publishing service | 8h |
| Comment fetching | 4h |
| Comment replies | 4h |
| Integration with inbox | 6h |
| Cron job for sync | 4h |

---

## Files to Create

```
Backend/services/instagram/
├── __init__.py
├── graph_api_client.py      # API wrapper
├── oauth_service.py         # OAuth flow
├── insights_sync.py         # Sync service
├── publishing_service.py    # Publishing
├── comments_service.py      # Comments
└── models.py

Backend/api/endpoints/
├── instagram_auth.py        # OAuth endpoints
├── instagram_accounts.py    # Account management
├── instagram_insights.py    # Insights API
└── instagram_publishing.py  # Publishing API

dashboard/app/(dashboard)/instagram/
├── page.tsx                 # Account list
├── connect/page.tsx         # OAuth flow
├── [accountId]/page.tsx     # Account dashboard
├── [accountId]/insights/page.tsx
├── [accountId]/media/page.tsx
└── components/
    ├── AccountCard.tsx
    ├── InsightsChart.tsx
    ├── AudienceDemographics.tsx
    ├── BestTimesChart.tsx
    └── MediaGrid.tsx
```

---

## Environment Variables

```bash
# Facebook/Instagram App
FACEBOOK_APP_ID=xxx
FACEBOOK_APP_SECRET=xxx
INSTAGRAM_REDIRECT_URI=http://localhost:5557/api/instagram/auth/callback
```

---

## Success Criteria

- [ ] OAuth flow connects Instagram Business accounts
- [ ] Account insights sync daily
- [ ] Media insights available for all posts
- [ ] Audience demographics displayed
- [ ] Best posting times calculated
- [ ] Publishing works (optional - can use Blotato)
- [ ] Comments sync to Community Inbox

---

*Document created: February 1, 2026*
