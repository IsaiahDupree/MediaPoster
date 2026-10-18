# PRD: Engagement Autopilot

**Status:** Proposed
**Priority:** P2 — Game-Changer
**Effort:** ~10-14 days
**Impact:** 2-5x follower growth through automated, authentic engagement

---

## 1. Problem Statement

Organic growth on social media requires consistent engagement — replying to comments, liking related content, following engaged users, responding to DMs. This is extremely time-consuming (1-3 hours/day) and difficult to maintain across 22 accounts. The Safari automation scaffolding already exists but isn't wired into an intelligent engagement strategy.

## 2. Objective

Build an AI-powered engagement autopilot that:
1. Auto-replies to comments on your posts with context-aware, authentic responses
2. Proactively engages with content from niche-relevant creators
3. Auto-follows users who engage with your content
4. Manages DM conversations with AI-assisted responses
5. Operates within platform rate limits and maintains authentic behavior patterns

## 3. Success Metrics

| Metric | Target |
|--------|--------|
| Follower growth rate | ≥ 2x current organic growth |
| Comment reply rate | ≥ 95% of comments get a reply within 2 hours |
| Reply authenticity score | ≥ 4/5 (human review of AI replies) |
| Time saved | ≥ 10 hrs/week on manual engagement |
| Account safety | 0 bans, 0 restrictions |

## 4. User Stories

- **As a creator**, I want every comment on my posts to get a thoughtful reply so my audience feels heard and the algorithm boosts my content.
- **As a creator**, I want the system to engage with similar creators' content to grow my visibility in the niche.
- **As a creator**, I want AI-drafted DM responses that I can approve or auto-send for common message types.
- **As a creator**, I want engagement to look natural — randomized timing, varying response lengths, human-like behavior patterns.
- **As a creator**, I want to set guardrails (never auto-reply to hate comments, never follow certain accounts, etc.).

## 5. Technical Design

### 5.1 Architecture

```
┌─────────────────────────────────────────────────┐
│                ENGAGEMENT AUTOPILOT              │
│                                                   │
│  ┌──────────────┐    ┌──────────────────────┐    │
│  │  Comment      │    │  Proactive           │    │
│  │  Monitor      │    │  Engagement Engine    │    │
│  │  (reply to    │    │  (like/comment on     │    │
│  │   own posts)  │    │   niche content)      │    │
│  └──────┬───────┘    └──────────┬───────────┘    │
│         │                       │                 │
│         ▼                       ▼                 │
│  ┌──────────────────────────────────────────┐    │
│  │  AI Response Engine (GPT)                 │    │
│  │  - Comment replies (context-aware)        │    │
│  │  - DM responses (template + AI hybrid)    │    │
│  │  - Engagement comments (niche-relevant)   │    │
│  └──────────────────┬───────────────────────┘    │
│                      │                            │
│                      ▼                            │
│  ┌──────────────────────────────────────────┐    │
│  │  Rate Limiter & Humanizer                 │    │
│  │  - Random delays (30s - 5min)             │    │
│  │  - Daily action caps per platform         │    │
│  │  - Session-based activity windows         │    │
│  │  - Typing simulation                      │    │
│  └──────────────────┬───────────────────────┘    │
│                      │                            │
│                      ▼                            │
│  ┌──────────────────────────────────────────┐    │
│  │  Safari Automation Layer                  │    │
│  │  (existing SafariAppController)           │    │
│  └──────────────────────────────────────────┘    │
│                                                   │
└─────────────────────────────────────────────────┘
```

### 5.2 Components

#### A. Comment Monitor (`services/engagement/comment_monitor.py`)

```python
class CommentMonitor:
    async def fetch_new_comments(self, account_id: str, platform: str) -> List[Comment]:
        """Pull new unreplied comments from recent posts (API or scraper)"""
    
    async def classify_comment(self, comment: Comment) -> CommentClassification:
        """
        AI classification:
        - sentiment: positive, neutral, negative, hate
        - type: question, compliment, feedback, spam, troll
        - priority: high (question), medium (compliment), low (spam)
        - requires_reply: bool
        """
    
    async def generate_reply(self, comment: Comment, post_context: str) -> str:
        """
        GPT generates contextual reply:
        - Matches creator's voice/tone
        - References the specific comment content
        - Varies length and style (not all replies look templated)
        - Includes occasional emoji (matching creator's style)
        """
```

#### B. Proactive Engagement Engine (`services/engagement/proactive_engine.py`)

```python
class ProactiveEngagementEngine:
    async def find_niche_content(self, platform: str) -> List[EngagementTarget]:
        """
        Find content to engage with:
        - Posts from niche-relevant creators
        - Posts using monitored hashtags
        - Posts from users who engaged with your content
        """
    
    async def generate_engagement_comment(self, target: EngagementTarget) -> str:
        """
        AI generates a genuine, value-adding comment.
        Rules:
        - No generic "Great post!" comments
        - Must reference specific content in the post
        - Add value (insight, question, related experience)
        - 1-3 sentences max
        """
    
    async def execute_engagement_session(self, platform: str, duration_minutes: int = 30):
        """
        Simulate a natural engagement session:
        - Scroll feed for X minutes
        - Like 10-20 posts
        - Comment on 3-5 posts
        - Follow 2-3 engaged users
        - Random delays between actions
        """
```

#### C. Rate Limiter & Humanizer (`services/engagement/rate_limiter.py`)

```python
class EngagementRateLimiter:
    DAILY_LIMITS = {
        "tiktok":    {"likes": 100, "comments": 30, "follows": 20, "dms": 10},
        "instagram": {"likes": 80,  "comments": 25, "follows": 15, "dms": 10},
        "twitter":   {"likes": 100, "comments": 50, "follows": 25, "dms": 20},
        "threads":   {"likes": 60,  "comments": 20, "follows": 10, "dms": 5},
        "youtube":   {"likes": 50,  "comments": 20, "follows": 0,  "dms": 0},
    }
    
    HUMANIZER_CONFIG = {
        "min_delay_seconds": 30,
        "max_delay_seconds": 300,
        "session_duration_minutes": 20,
        "sessions_per_day": 4,
        "session_gap_hours": 3,
        "typing_speed_cps": 5,  # characters per second
        "scroll_pause_range": (2, 8),  # seconds
    }
    
    async def can_perform_action(self, account_id: str, platform: str, action: str) -> bool:
        """Check if action is within daily limits"""
    
    async def humanize_delay(self, action_type: str) -> float:
        """Return a randomized human-like delay before performing action"""
```

#### D. Safety & Guardrails

```python
class EngagementGuardrails:
    NEVER_REPLY_TO = ["hate_speech", "spam", "scam", "explicit"]
    NEVER_FOLLOW = ["bot_accounts", "spam_accounts", "competitor_haters"]
    
    REPLY_GUIDELINES = {
        "never_mention": ["politics", "religion", "controversy"],
        "always_positive": True,
        "max_reply_length": 200,
        "never_argue": True,
        "report_hate": True,
    }
    
    async def should_engage(self, target: EngagementTarget) -> Tuple[bool, str]:
        """Pre-flight safety check before any engagement action"""
    
    async def review_reply(self, reply: str, comment: Comment) -> Tuple[bool, str]:
        """AI safety review of generated reply before posting"""
```

### 5.3 Database Schema

```sql
CREATE TABLE engagement_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id VARCHAR(50) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    action_type VARCHAR(20) NOT NULL,  -- reply, like, comment, follow, dm
    target_user VARCHAR(255),
    target_post_id VARCHAR(255),
    content TEXT,                       -- reply/comment text
    status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, executed, failed, skipped
    ai_generated BOOLEAN DEFAULT TRUE,
    human_approved BOOLEAN DEFAULT FALSE,
    executed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE engagement_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id VARCHAR(50) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    session_start TIMESTAMPTZ,
    session_end TIMESTAMPTZ,
    actions_performed INT DEFAULT 0,
    likes_count INT DEFAULT 0,
    comments_count INT DEFAULT 0,
    follows_count INT DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active'
);

CREATE TABLE engagement_daily_stats (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    account_id VARCHAR(50) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    stat_date DATE NOT NULL,
    total_replies INT DEFAULT 0,
    total_likes INT DEFAULT 0,
    total_comments INT DEFAULT 0,
    total_follows INT DEFAULT 0,
    total_dms INT DEFAULT 0,
    new_followers_gained INT DEFAULT 0,
    UNIQUE(account_id, platform, stat_date)
);

CREATE INDEX idx_engagement_actions ON engagement_actions(account_id, platform, created_at);
CREATE INDEX idx_engagement_daily ON engagement_daily_stats(stat_date DESC);
```

### 5.4 Modes of Operation

| Mode | Description | Auto-Reply | Proactive | Follows |
|------|-------------|------------|-----------|---------|
| **Full Auto** | Everything runs automatically | Yes | Yes | Yes |
| **Reply Only** | Only auto-reply to own comments | Yes | No | No |
| **Assist** | AI drafts, human approves | Draft | Draft | Draft |
| **Monitor** | Collect data, no actions | No | No | No |
| **Off** | Disabled | No | No | No |

## 6. Integration with Existing Safari Automation

The existing scaffolding in `automation/safari_app_controller.py` handles:
- Safari session management
- JavaScript execution via extension bridge
- Cookie-based session persistence
- Per-platform login state

This PRD builds the **intelligence layer** on top:
- What to engage with (AI-driven targeting)
- What to say (GPT-generated replies)
- When to engage (humanized scheduling)
- Safety guardrails (never engage inappropriately)

## 7. API Endpoints

```
GET  /api/engagement/dashboard                — Overview stats
GET  /api/engagement/actions?status=pending   — Pending actions for approval
POST /api/engagement/actions/:id/approve      — Approve a pending action
POST /api/engagement/actions/:id/reject       — Reject a pending action
POST /api/engagement/session/start            — Start an engagement session
POST /api/engagement/session/stop             — Stop current session
GET  /api/engagement/settings                 — Get engagement config
PUT  /api/engagement/settings                 — Update engagement config
GET  /api/engagement/stats?period=7d          — Engagement stats
```

## 8. Cron Schedule

| Job | Frequency | Description |
|-----|-----------|-------------|
| `check_new_comments` | Every 30 minutes | Fetch and classify new comments |
| `auto_reply_comments` | Every 30 minutes | Reply to classified comments |
| `engagement_session` | 4x daily (9am, 12pm, 5pm, 9pm) | 20-min proactive engagement session |
| `daily_stats` | Daily at midnight | Compile daily engagement stats |

## 9. Rollout Plan

1. **Phase 1:** Comment monitor + AI reply generation (assist mode — human approval)
2. **Phase 2:** Auto-reply mode with safety guardrails
3. **Phase 3:** Proactive engagement engine (like/comment on niche content)
4. **Phase 4:** Auto-follow logic with intelligent targeting
5. **Phase 5:** Full autopilot mode + DM automation integration

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Account ban for automation | Strict rate limits; human-like delays; session-based activity |
| AI reply sounds robotic | Fine-tune prompts with creator's actual replies; vary style |
| Engaging with wrong content | Niche relevance filter; never-engage blocklist; safety review |
| Platform API changes | Abstract interaction layer; fall back to Safari automation |
| Creator voice inconsistency | Include 20+ example replies in system prompt for voice matching |

## 11. Cost Estimate

| Item | Monthly Cost |
|------|-------------|
| GPT-4o-mini for reply generation | ~$15 (10K replies/month) |
| GPT-4o for safety classification | ~$5 |
| RapidAPI for comment fetching | ~$20 |
| **Total** | **~$40/month** |

## 12. Out of Scope (v1)

- Video comment responses (replying with video)
- Cross-platform engagement coordination
- Influencer outreach automation
- Paid collaboration management
- Community management dashboard with unified inbox
