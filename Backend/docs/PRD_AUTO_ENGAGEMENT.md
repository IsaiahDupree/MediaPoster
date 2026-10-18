# PRD: Auto-Engagement System

## Overview

A pub/sub-driven auto-engagement system for posting contextual AI-generated comments on social media platforms (Threads, Instagram, TikTok). The system prevents duplicate comments, enforces daily limits, and provides full observability through the existing event bus architecture.

## Goals

1. **Automated Engagement**: Post AI-generated contextual comments on social media
2. **No Duplicates**: Never comment on the same post twice
3. **Rate Limiting**: Enforce configurable daily limits per platform (default: 100/day)
4. **Controllability**: Pause/resume, adjust limits, and monitor via API
5. **Observability**: Full event trail through pub/sub for debugging and analytics
6. **Testability**: Comprehensive test suite for all components

## Architecture

### Event Flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  API/Scheduler  │────▶│    Event Bus     │────▶│ EngagementWorker    │
│  (trigger)      │     │  (pub/sub)       │     │ (process)           │
└─────────────────┘     └──────────────────┘     └─────────────────────┘
                               │                          │
                               │                          ▼
                               │                 ┌─────────────────────┐
                               │                 │ Platform Engagement │
                               │                 │ (Threads/IG/TikTok) │
                               │                 └─────────────────────┘
                               │                          │
                               ▼                          ▼
                        ┌──────────────────┐     ┌─────────────────────┐
                        │  Event Log       │     │ Comment Tracker     │
                        │  (history)       │     │ (Supabase)          │
                        └──────────────────┘     └─────────────────────┘
```

### Topics

| Topic | Description | Payload |
|-------|-------------|---------|
| `engagement.requested` | Request to engage with platform | `{platform, target_count, correlation_id}` |
| `engagement.started` | Worker picked up job | `{platform, worker_id}` |
| `engagement.post_found` | Found a post to engage with | `{platform, post_url, username}` |
| `engagement.comment_generated` | AI generated a comment | `{platform, post_url, comment_text}` |
| `engagement.comment_posted` | Comment successfully posted | `{platform, post_url, comment_text, proof_screenshot}` |
| `engagement.comment_skipped` | Post skipped (duplicate/rate limit) | `{platform, post_url, reason}` |
| `engagement.completed` | Engagement session completed | `{platform, comments_posted, comments_skipped}` |
| `engagement.failed` | Engagement failed | `{platform, error, step}` |
| `engagement.daily_limit_reached` | Daily limit hit | `{platform, limit, count}` |

### Database Schema

```sql
-- Comment tracking table
CREATE TABLE engagement_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL,           -- 'threads', 'instagram', 'tiktok'
    post_url TEXT NOT NULL,           -- URL of the post commented on
    post_username TEXT,               -- Creator of the post
    comment_text TEXT NOT NULL,       -- The comment we posted
    proof_screenshot TEXT,            -- Path to proof screenshot
    engagement_account TEXT,          -- Our account that posted
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicate comments on same post
    UNIQUE(platform, post_url)
);

-- Index for daily count queries
CREATE INDEX idx_engagement_comments_daily 
ON engagement_comments (platform, created_at);

-- Daily limits configuration
CREATE TABLE engagement_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform TEXT NOT NULL UNIQUE,
    daily_limit INTEGER NOT NULL DEFAULT 100,
    is_enabled BOOLEAN DEFAULT true,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default limits
INSERT INTO engagement_limits (platform, daily_limit) VALUES
    ('threads', 100),
    ('instagram', 100),
    ('tiktok', 100);
```

## Components

### 1. EngagementWorker (`services/workers/engagement_worker.py`)

Subscribes to `engagement.requested` and orchestrates the engagement flow:

```python
class EngagementWorker(BaseWorker):
    """
    Worker that processes engagement requests.
    
    Subscribes to: engagement.requested
    Emits: engagement.started, engagement.comment_posted, engagement.completed, etc.
    """
    
    def get_subscriptions(self) -> List[str]:
        return [Topics.ENGAGEMENT_REQUESTED]
    
    async def handle_event(self, event: Event) -> None:
        platform = event.payload.get("platform")
        target_count = event.payload.get("target_count", 1)
        
        # Check daily limit
        if await self.tracker.is_limit_reached(platform):
            await self.emit(Topics.ENGAGEMENT_DAILY_LIMIT_REACHED, {...})
            return
        
        # Run engagement
        result = await self.engage_platform(platform, target_count)
        
        await self.emit(Topics.ENGAGEMENT_COMPLETED, result)
```

### 2. CommentTracker (`services/engagement/comment_tracker.py`)

Tracks posted comments to prevent duplicates:

```python
class CommentTracker:
    """
    Tracks engagement comments in Supabase.
    
    Features:
    - Duplicate detection by post URL
    - Daily count tracking per platform
    - Rate limit enforcement
    """
    
    async def has_commented_on(self, platform: str, post_url: str) -> bool:
        """Check if we've already commented on this post."""
        
    async def record_comment(self, platform: str, post_url: str, 
                            comment_text: str, proof: str) -> str:
        """Record a new comment. Returns comment ID."""
        
    async def get_daily_count(self, platform: str) -> int:
        """Get today's comment count for platform."""
        
    async def is_limit_reached(self, platform: str) -> bool:
        """Check if daily limit is reached."""
```

### 3. EngagementService (`services/engagement/engagement_service.py`)

High-level API for triggering engagement:

```python
class EngagementService:
    """
    Service for managing auto-engagement.
    
    Provides API for:
    - Triggering engagement sessions
    - Checking status and limits
    - Pausing/resuming engagement
    """
    
    async def request_engagement(self, platform: str, count: int = 1) -> str:
        """Request engagement session. Returns correlation_id."""
        
    async def request_all_platforms(self, count_per_platform: int = 1) -> Dict[str, str]:
        """Request engagement on all platforms."""
        
    async def get_status(self, platform: str) -> Dict:
        """Get engagement status for platform."""
        
    async def set_daily_limit(self, platform: str, limit: int) -> None:
        """Update daily limit for platform."""
        
    async def pause_platform(self, platform: str) -> None:
        """Pause engagement for platform."""
        
    async def resume_platform(self, platform: str) -> None:
        """Resume engagement for platform."""
```

## API Endpoints

### POST `/api/engagement/request`

Trigger an engagement session.

```json
{
    "platform": "threads",     // or "instagram", "tiktok", "all"
    "count": 5                 // number of comments to post
}
```

Response:
```json
{
    "correlation_id": "eng-abc123",
    "platform": "threads",
    "requested_count": 5,
    "daily_remaining": 95
}
```

### GET `/api/engagement/status`

Get engagement status.

```json
{
    "platforms": {
        "threads": {
            "is_enabled": true,
            "daily_limit": 100,
            "today_count": 23,
            "remaining": 77,
            "last_engagement": "2026-01-25T12:00:00Z"
        },
        "instagram": {...},
        "tiktok": {...}
    },
    "total_today": 45
}
```

### POST `/api/engagement/limits`

Update daily limits.

```json
{
    "platform": "threads",
    "daily_limit": 150
}
```

### POST `/api/engagement/pause`

Pause engagement for a platform.

```json
{
    "platform": "threads"    // or "all"
}
```

### POST `/api/engagement/resume`

Resume engagement for a platform.

```json
{
    "platform": "threads"    // or "all"
}
```

## Configuration

```python
# config/engagement.py

ENGAGEMENT_CONFIG = {
    "threads": {
        "daily_limit": 100,
        "min_delay_seconds": 30,      # Minimum delay between comments
        "max_delay_seconds": 120,     # Maximum delay between comments
        "enabled": True
    },
    "instagram": {
        "daily_limit": 100,
        "min_delay_seconds": 45,
        "max_delay_seconds": 180,
        "enabled": True
    },
    "tiktok": {
        "daily_limit": 100,
        "min_delay_seconds": 30,
        "max_delay_seconds": 120,
        "enabled": True
    }
}
```

## Test Plan

### Unit Tests

1. **CommentTracker Tests**
   - `test_has_commented_on_returns_false_for_new_post`
   - `test_has_commented_on_returns_true_for_existing_post`
   - `test_record_comment_creates_entry`
   - `test_record_comment_raises_on_duplicate`
   - `test_get_daily_count_returns_correct_count`
   - `test_is_limit_reached_returns_true_at_limit`
   - `test_is_limit_reached_returns_false_below_limit`

2. **EngagementWorker Tests**
   - `test_worker_subscribes_to_correct_topics`
   - `test_worker_skips_when_limit_reached`
   - `test_worker_skips_duplicate_posts`
   - `test_worker_emits_correct_events`
   - `test_worker_handles_platform_errors`

3. **EngagementService Tests**
   - `test_request_engagement_publishes_event`
   - `test_request_all_platforms_publishes_multiple`
   - `test_set_daily_limit_updates_database`
   - `test_pause_platform_stops_processing`

### Integration Tests

1. **End-to-End Flow**
   - `test_full_engagement_flow_threads`
   - `test_full_engagement_flow_instagram`
   - `test_full_engagement_flow_tiktok`
   - `test_multi_platform_engagement`

2. **Duplicate Prevention**
   - `test_same_post_not_commented_twice`
   - `test_duplicate_across_sessions`

3. **Rate Limiting**
   - `test_stops_at_daily_limit`
   - `test_limit_resets_at_midnight`

### Controllability Tests

1. **Pause/Resume**
   - `test_pause_stops_engagement`
   - `test_resume_continues_engagement`
   - `test_pause_all_stops_all_platforms`

2. **Limit Adjustment**
   - `test_increase_limit_allows_more`
   - `test_decrease_limit_enforced`

## Rollout Plan

1. **Phase 1**: Deploy with low limits (10/day) for testing
2. **Phase 2**: Monitor for 1 week, verify no duplicates
3. **Phase 3**: Increase limits gradually (25, 50, 100)
4. **Phase 4**: Enable scheduled engagement (e.g., 3x daily)

## Success Metrics

- **No duplicates**: 0 duplicate comments ever
- **Uptime**: 99.9% engagement success rate
- **Latency**: < 60s per engagement cycle
- **Observability**: 100% events logged and traceable
