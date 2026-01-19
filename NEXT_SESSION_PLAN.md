# Next Session Plan: Platform Adapters Implementation

## Session Goal
Implement Phase 3 Platform Adapters to enable multi-platform content publishing.

## Priority Features (Phase 3)

### 1. X/Twitter Adapter (ADAPT-001 to ADAPT-003)

**ADAPT-001: X/Twitter Adapter - Publish** [P0]
- **Files to create:**
  - `Backend/adapters/twitter_adapter.py`
  - `Backend/api/endpoints/twitter_publish.py`
- **Implementation:**
  - OAuth 2.0 authentication
  - Tweet publishing (text + media)
  - Thread support
  - Character limit validation (280)
  - Media upload to Twitter CDN
- **Testing:**
  - Mock Twitter API responses
  - Character count validation
  - Thread assembly logic
- **Acceptance:**
  - Can publish single tweets
  - Can publish threads
  - Media attachments work

**ADAPT-002: X/Twitter Adapter - Metrics** [P0]
- **Files to create:**
  - `Backend/adapters/twitter_metrics.py`
  - `Backend/api/endpoints/twitter_metrics.py`
- **Implementation:**
  - Twitter API v2 metrics fetch
  - Metrics: views, likes, retweets, replies, bookmarks
  - Historical metrics at checkback intervals (1h, 6h, 24h, 72h, 7d)
  - Rate limit handling
- **Testing:**
  - Metrics parsing
  - Rate limit backoff
- **Acceptance:**
  - Fetch metrics for published tweets
  - Store in database
  - Trigger checkback wake events

**ADAPT-003: X/Twitter Adapter - DMs** [P1]
- **Files to create:**
  - `Backend/adapters/twitter_dm.py`
  - `Backend/api/endpoints/twitter_dm.py`
- **Implementation:**
  - Send DMs via Twitter API
  - DM permission check
  - Conversation threading
  - Template support
- **Testing:**
  - DM sending
  - Permission validation
- **Acceptance:**
  - Can send DMs to followers
  - Respects DM permissions

### 2. Instagram Adapter (ADAPT-004 to ADAPT-006)

**ADAPT-004: Instagram Adapter - Publish API** [P0]
- **Files to create:**
  - `Backend/adapters/instagram_adapter.py`
  - `Backend/api/endpoints/instagram_publish.py`
- **Implementation:**
  - Instagram Graph API publish
  - Container creation → publish workflow
  - Caption + hashtags
  - Location tagging
  - Product tagging (shopping)
  - Carousel support (multi-image)
- **Testing:**
  - Container creation
  - Publish workflow
  - Carousel logic
- **Acceptance:**
  - Single image posts work
  - Carousel posts work
  - Caption + hashtags applied

**ADAPT-005: Instagram Adapter - DMs Safari** [P1]
- **Files to create:**
  - `Backend/automation/instagram_dm_safari.py`
  - `Backend/api/endpoints/instagram_dm.py`
- **Implementation:**
  - Safari automation for DM sending (Graph API doesn't support DMs)
  - AppleScript automation
  - Message templates
  - Conversation state tracking
- **Testing:**
  - Safari automation tests
  - Message sending
- **Acceptance:**
  - Can send DMs via Safari automation
  - Reliable delivery

**ADAPT-006: Instagram Adapter - Metrics** [P0]
- **Files to create:**
  - `Backend/adapters/instagram_metrics.py`
  - `Backend/api/endpoints/instagram_metrics.py`
- **Implementation:**
  - Instagram Graph API metrics
  - Metrics: impressions, reach, likes, comments, saves, shares
  - Insights API integration
  - Checkback scheduling
- **Testing:**
  - Metrics parsing
  - Multi-metric aggregation
- **Acceptance:**
  - Fetch post metrics
  - Store in database

### 3. TikTok Adapter (ADAPT-007 to ADAPT-009)

**ADAPT-007: TikTok Adapter - Publish** [P0]
- **Files to create:**
  - `Backend/adapters/tiktok_adapter.py`
  - `Backend/api/endpoints/tiktok_publish.py`
- **Implementation:**
  - TikTok Creator API publish
  - Video upload to TikTok CDN
  - Privacy settings (public, friends, private)
  - Duet/Stitch settings
  - Comment settings
- **Testing:**
  - Video upload
  - Privacy settings
- **Acceptance:**
  - Can publish videos
  - Privacy settings applied

**ADAPT-008: TikTok Adapter - Metrics** [P0]
- **Files to create:**
  - `Backend/adapters/tiktok_metrics.py`
  - `Backend/api/endpoints/tiktok_metrics.py`
- **Implementation:**
  - TikTok Research API metrics
  - Metrics: views, likes, comments, shares
  - Fallback to Safari scraping if API unavailable
- **Testing:**
  - API metrics parsing
  - Safari fallback
- **Acceptance:**
  - Fetch metrics from API or Safari

**ADAPT-009: TikTok Adapter - DMs** [P1]
- **Files to create:**
  - `Backend/automation/tiktok_dm_safari.py`
  - `Backend/api/endpoints/tiktok_dm.py`
- **Implementation:**
  - Safari automation for DMs (no official DM API)
  - Message sending
  - Conversation tracking
- **Testing:**
  - Safari automation
- **Acceptance:**
  - Can send DMs

### 4. YouTube Adapter (ADAPT-010 to ADAPT-011)

**ADAPT-010: YouTube Adapter - Publish** [P0]
- **Files to create:**
  - `Backend/adapters/youtube_adapter.py`
  - `Backend/api/endpoints/youtube_publish.py`
- **Implementation:**
  - YouTube Data API v3 upload
  - Video upload to YouTube
  - Title, description, tags
  - Category, privacy settings
  - Thumbnail upload
  - Playlist assignment
- **Testing:**
  - Video upload
  - Metadata application
- **Acceptance:**
  - Videos upload successfully
  - Metadata applied

**ADAPT-011: YouTube Adapter - Analytics** [P0]
- **Files to create:**
  - `Backend/adapters/youtube_analytics.py`
  - `Backend/api/endpoints/youtube_analytics.py`
- **Implementation:**
  - YouTube Analytics API
  - Metrics: views, watch time, likes, comments, shares, subscribers gained
  - Revenue metrics (if monetized)
  - Traffic sources
  - Audience retention
- **Testing:**
  - Metrics parsing
  - Multi-dimension queries
- **Acceptance:**
  - Fetch comprehensive video analytics

### 5. Threads Adapter (ADAPT-012)

**ADAPT-012: Threads Adapter** [P1]
- **Files to create:**
  - `Backend/adapters/threads_adapter.py`
  - `Backend/api/endpoints/threads_publish.py`
- **Implementation:**
  - Threads API publish (similar to Instagram)
  - Text + media posts
  - Reply threading
  - Metrics: likes, replies, reposts, quotes
- **Testing:**
  - Post publishing
  - Metrics retrieval
- **Acceptance:**
  - Can publish to Threads
  - Fetch metrics

### 6. Stories Support (ADAPT-013)

**ADAPT-013: Stories Support (Instagram/Facebook)** [P1]
- **Files to create:**
  - `Backend/adapters/stories_adapter.py`
  - `Backend/api/endpoints/stories_publish.py`
- **Implementation:**
  - Instagram Stories API
  - Facebook Stories API
  - 24-hour expiration handling
  - Story mentions, stickers, links
  - Story metrics (views, exits, taps)
- **Testing:**
  - Story publishing
  - Expiration tracking
- **Acceptance:**
  - Stories publish to Instagram/Facebook
  - Metrics tracked

## Implementation Approach

### Step 1: X/Twitter First (Most Critical)
Start with X/Twitter since it has the simplest API and highest priority for PRD goals.

1. Implement ADAPT-001 (Twitter publish)
2. Add tests
3. Implement ADAPT-002 (Twitter metrics)
4. Integrate with sleep mode checkback
5. Implement ADAPT-003 (Twitter DMs) if time permits

### Step 2: Instagram Second (High Engagement)
Instagram is second priority due to visual content focus.

1. Implement ADAPT-004 (Instagram publish via Graph API)
2. Add carousel support
3. Implement ADAPT-006 (Instagram metrics)
4. Implement ADAPT-005 (Instagram DMs via Safari) if needed

### Step 3: TikTok Third (Viral Potential)
TikTok for short-form video distribution.

1. Implement ADAPT-007 (TikTok publish)
2. Implement ADAPT-008 (TikTok metrics with Safari fallback)

### Step 4: YouTube Fourth (Long-Form)
YouTube for long-form content and SEO.

1. Implement ADAPT-010 (YouTube upload)
2. Implement ADAPT-011 (YouTube analytics)

### Step 5: Threads & Stories (Nice-to-Have)
Complete Phase 3 with Threads and Stories support.

## Database Schema Additions

### Platform Accounts Table
```sql
CREATE TABLE IF NOT EXISTS platform_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform VARCHAR(50) NOT NULL, -- 'twitter', 'instagram', 'tiktok', 'youtube', 'threads'
    username VARCHAR(255) NOT NULL,
    account_id VARCHAR(255), -- Platform-specific account ID
    access_token TEXT, -- OAuth token
    refresh_token TEXT,
    token_expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Platform Posts Table
```sql
CREATE TABLE IF NOT EXISTS platform_posts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform_account_id UUID REFERENCES platform_accounts(id),
    platform VARCHAR(50) NOT NULL,
    platform_post_id VARCHAR(255), -- Platform-specific post ID
    platform_url TEXT, -- URL to the post
    content_id UUID, -- Reference to local content
    caption TEXT,
    hashtags TEXT[],
    status VARCHAR(50), -- 'publishing', 'published', 'failed'
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Platform Metrics Table
```sql
CREATE TABLE IF NOT EXISTS platform_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    platform_post_id UUID REFERENCES platform_posts(id),
    platform VARCHAR(50) NOT NULL,
    metric_type VARCHAR(50), -- 'views', 'likes', 'comments', etc.
    metric_value BIGINT,
    checkback_interval VARCHAR(10), -- '1h', '6h', '24h', '72h', '7d'
    fetched_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Testing Strategy

1. **Unit Tests**: Test each adapter in isolation with mocked API responses
2. **Integration Tests**: Test end-to-end publish flow with test accounts
3. **Rate Limit Tests**: Verify backoff and retry logic
4. **Error Handling**: Test API errors, network failures, auth failures

## Success Criteria

- [ ] All 13 adapter features pass tests
- [ ] Can publish to X/Twitter, Instagram, TikTok, YouTube
- [ ] Metrics fetch for all platforms
- [ ] DMs work for X/Twitter and Instagram (Safari)
- [ ] Sleep mode wake triggers work with checkback periods
- [ ] Rate limiting prevents API bans
- [ ] Error handling gracefully degrades

## Estimated Time

- **X/Twitter**: 4-6 hours
- **Instagram**: 6-8 hours
- **TikTok**: 4-6 hours
- **YouTube**: 4-6 hours
- **Threads**: 2-3 hours
- **Stories**: 3-4 hours

**Total: 23-33 hours** (3-4 full work days)

## Dependencies

- OAuth credentials for each platform
- Test accounts for each platform
- Blotato API (already configured)
- Safari automation for DMs (already working)

## Next Session Commands

```bash
# Start backend
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload

# Run tests
pytest tests/unit/test_twitter_adapter.py -v
pytest tests/unit/test_instagram_adapter.py -v
pytest tests/unit/test_tiktok_adapter.py -v
pytest tests/unit/test_youtube_adapter.py -v

# Test platform publish
curl -X POST http://localhost:5555/api/twitter/publish -H "Content-Type: application/json" -d '{"content_id": "...", "caption": "Test tweet"}'
```

---

**Prepared by:** Claude Code Agent
**Session:** 2026-01-18
**Status:** Ready for implementation
