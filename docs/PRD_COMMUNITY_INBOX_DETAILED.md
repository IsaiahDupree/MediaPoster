# PRD: Community Inbox (Detailed)

**Version:** 1.0  
**Date:** February 1, 2026  
**Status:** Ready for Implementation  
**Track:** T2.1 Community & Engagement  
**Effort:** 5-6 weeks  
**Priority:** 🔴 Critical

---

## Executive Summary

Build a unified inbox that aggregates comments, DMs, and mentions from all connected social platforms (Instagram, TikTok, Twitter, YouTube, Threads) into a single interface with AI-powered reply suggestions, sentiment analysis, and automation rules.

---

## Problem Statement

- Comments and DMs scattered across 5+ platforms
- No unified view of community engagement
- Manual reply process is time-consuming
- Missing engagement opportunities
- No sentiment tracking or prioritization
- Cannot convert comments into content ideas efficiently

---

## Goals

| Goal | Metric | Target |
|------|--------|--------|
| Response time | Avg reply time | <2 hours |
| Coverage | Messages responded to | 90%+ |
| Efficiency | Time spent on replies | -50% |
| Conversion | Comments → Content ideas | 10+ per week |
| Sentiment | Negative sentiment addressed | 100% |

---

## User Stories

### US-1: Unified Message View
**As a** creator  
**I want** all comments and DMs in one place  
**So that** I don't miss engagement opportunities

### US-2: AI Reply Assistance
**As a** creator  
**I want** AI-suggested replies  
**So that** I can respond faster while maintaining my voice

### US-3: Priority Queue
**As a** creator  
**I want** high-value messages prioritized  
**So that** I focus on the most impactful interactions

### US-4: Comment to Content
**As a** creator  
**I want** to convert comments into content ideas  
**So that** I can create content my audience wants

### US-5: Automation Rules
**As a** creator  
**I want** auto-responses for common questions  
**So that** I save time on repetitive replies

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        COMMUNITY INBOX SYSTEM                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    PLATFORM CONNECTORS                           │   │
│  ├─────────┬─────────┬─────────┬─────────┬─────────┬──────────────┤   │
│  │Instagram│ TikTok  │ Twitter │ YouTube │ Threads │   Future     │   │
│  │Connector│Connector│Connector│Connector│Connector│  Platforms   │   │
│  └────┬────┴────┬────┴────┬────┴────┬────┴────┬────┴──────────────┘   │
│       │         │         │         │         │                        │
│       ▼         ▼         ▼         ▼         ▼                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    MESSAGE AGGREGATOR                            │   │
│  │  • Deduplication  • Normalization  • Threading  • Timestamps    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                │                                        │
│       ┌───────────────────────┼───────────────────────┐                │
│       ▼                       ▼                       ▼                │
│  ┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│  │  SENTIMENT  │    │   ENGAGEMENT    │    │   AUTOMATION    │        │
│  │  ANALYZER   │    │    SCORER       │    │     ENGINE      │        │
│  │  (OpenAI)   │    │  (Value calc)   │    │  (Rules-based)  │        │
│  └─────────────┘    └─────────────────┘    └─────────────────┘        │
│       │                       │                       │                │
│       └───────────────────────┼───────────────────────┘                │
│                               ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      PRIORITY QUEUE                              │   │
│  │  Score = (Sentiment × 2) + Engagement + Recency + Value         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                               │                                        │
│                               ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    AI REPLY SERVICE                              │   │
│  │  • Context-aware suggestions  • Brand voice matching             │   │
│  │  • Saved reply templates      • One-click send                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

```sql
-- Migration: 20260201_community_inbox.sql

-- Inbox messages (aggregated from all platforms)
CREATE TABLE inbox_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    platform VARCHAR(20) NOT NULL, -- instagram, tiktok, twitter, youtube, threads
    platform_message_id VARCHAR(255),
    message_type VARCHAR(20) NOT NULL, -- comment, dm, mention, reply
    
    -- Sender info
    sender_username VARCHAR(255),
    sender_display_name VARCHAR(255),
    sender_avatar_url TEXT,
    sender_follower_count INTEGER,
    sender_is_verified BOOLEAN DEFAULT FALSE,
    
    -- Content reference
    content_id UUID REFERENCES content(id),
    content_url TEXT,
    content_title TEXT,
    
    -- Message content
    text TEXT,
    media_urls JSONB,
    
    -- Threading
    parent_message_id UUID REFERENCES inbox_messages(id),
    thread_id UUID,
    
    -- Status
    status VARCHAR(20) DEFAULT 'unread', -- unread, read, replied, archived
    is_starred BOOLEAN DEFAULT FALSE,
    assigned_to UUID,
    
    -- Scores
    sentiment_score FLOAT, -- -1 to 1
    sentiment_label VARCHAR(20), -- positive, neutral, negative
    engagement_score FLOAT, -- 0 to 100
    priority_score FLOAT, -- calculated
    
    -- Timestamps
    platform_created_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    read_at TIMESTAMPTZ,
    replied_at TIMESTAMPTZ,
    
    UNIQUE(platform, platform_message_id)
);

-- Inbox replies (our responses)
CREATE TABLE inbox_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES inbox_messages(id) ON DELETE CASCADE,
    
    reply_text TEXT NOT NULL,
    reply_type VARCHAR(20) DEFAULT 'manual', -- manual, ai_suggested, saved_reply, auto
    
    -- If AI generated
    ai_model VARCHAR(50),
    ai_prompt TEXT,
    
    -- If from saved reply
    saved_reply_id UUID,
    
    -- Status
    status VARCHAR(20) DEFAULT 'draft', -- draft, sent, failed
    platform_reply_id VARCHAR(255),
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    sent_at TIMESTAMPTZ
);

-- Saved replies (templates)
CREATE TABLE saved_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),
    
    template_text TEXT NOT NULL,
    variables JSONB, -- [{name: "first_name", default: "friend"}]
    
    -- Usage tracking
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    
    -- Targeting
    platforms VARCHAR(20)[], -- which platforms this applies to
    message_types VARCHAR(20)[], -- comment, dm, etc
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Message tags
CREATE TABLE inbox_message_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES inbox_messages(id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(message_id, tag)
);

-- Content ideas from comments
CREATE TABLE inbox_content_ideas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_message_id UUID REFERENCES inbox_messages(id),
    
    idea_title VARCHAR(255),
    idea_description TEXT,
    idea_type VARCHAR(50), -- video, post, story, thread
    
    status VARCHAR(20) DEFAULT 'new', -- new, planned, created, dismissed
    content_id UUID REFERENCES content(id), -- if created
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Automation rules
CREATE TABLE inbox_automation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Conditions (AND logic)
    conditions JSONB NOT NULL,
    -- Example: {
    --   "platforms": ["instagram", "tiktok"],
    --   "message_types": ["comment"],
    --   "contains_keywords": ["price", "cost", "how much"],
    --   "sentiment": "positive"
    -- }
    
    -- Actions
    action_type VARCHAR(50) NOT NULL, -- auto_reply, tag, assign, archive, notify
    action_config JSONB NOT NULL,
    -- Example for auto_reply: {"saved_reply_id": "uuid", "delay_seconds": 60}
    
    -- Stats
    trigger_count INTEGER DEFAULT 0,
    last_triggered_at TIMESTAMPTZ,
    
    priority INTEGER DEFAULT 0, -- higher = checked first
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_inbox_messages_platform ON inbox_messages(platform);
CREATE INDEX idx_inbox_messages_status ON inbox_messages(status);
CREATE INDEX idx_inbox_messages_priority ON inbox_messages(priority_score DESC);
CREATE INDEX idx_inbox_messages_created ON inbox_messages(created_at DESC);
CREATE INDEX idx_inbox_messages_sender ON inbox_messages(sender_username);
CREATE INDEX idx_inbox_messages_thread ON inbox_messages(thread_id);
CREATE INDEX idx_inbox_fulltext ON inbox_messages USING gin(to_tsvector('english', text));
```

---

## API Endpoints (17 Total)

### Messages

```yaml
# GET /api/inbox/messages
# List messages with filters
Query Parameters:
  platform: string (optional)
  status: string (optional) - unread, read, replied, archived
  message_type: string (optional)
  sentiment: string (optional)
  search: string (optional)
  starred: boolean (optional)
  page: number
  limit: number
  sort: string - priority, created_at, sentiment
  
Response:
  messages: InboxMessage[]
  total: number
  unread_count: number

# GET /api/inbox/messages/{id}
# Get single message with thread
Response:
  message: InboxMessage
  thread: InboxMessage[]
  suggested_replies: string[]

# GET /api/inbox/messages/unread/count
# Quick count by platform
Response:
  total: number
  by_platform: {instagram: 5, tiktok: 3, ...}

# PUT /api/inbox/messages/{id}/status
# Update message status
Request:
  status: "read" | "replied" | "archived"
Response:
  success: boolean

# PUT /api/inbox/messages/{id}/assign
# Assign to team member
Request:
  user_id: uuid
Response:
  success: boolean

# POST /api/inbox/messages/{id}/tags
# Add tags to message
Request:
  tags: string[]
Response:
  success: boolean

# POST /api/inbox/messages/{id}/star
# Toggle star
Response:
  is_starred: boolean
```

### Replies

```yaml
# POST /api/inbox/messages/{id}/reply
# Send a reply
Request:
  text: string
  reply_type: "manual" | "saved_reply"
  saved_reply_id: uuid (optional)
Response:
  reply: InboxReply
  status: "sent" | "failed"

# GET /api/inbox/messages/{id}/ai-suggestions
# Get AI reply suggestions
Response:
  suggestions: [
    {text: string, tone: string, confidence: number}
  ]

# POST /api/inbox/messages/{id}/ai-generate
# Generate custom AI reply
Request:
  tone: string - friendly, professional, casual
  include_cta: boolean
  max_length: number
Response:
  text: string
```

### Saved Replies

```yaml
# GET /api/inbox/saved-replies
# List all saved replies
Response:
  replies: SavedReply[]

# POST /api/inbox/saved-replies
# Create saved reply
Request:
  name: string
  category: string
  template_text: string
  variables: [{name, default}]
  platforms: string[]
Response:
  reply: SavedReply

# PUT /api/inbox/saved-replies/{id}
# Update saved reply

# DELETE /api/inbox/saved-replies/{id}
# Delete saved reply
```

### Content Ideas

```yaml
# POST /api/inbox/messages/{id}/to-idea
# Convert message to content idea
Request:
  idea_title: string
  idea_type: string
Response:
  idea: ContentIdea

# GET /api/inbox/content-ideas
# List content ideas from inbox
Response:
  ideas: ContentIdea[]
```

### Automation

```yaml
# GET /api/inbox/automation/rules
# List automation rules
Response:
  rules: AutomationRule[]

# POST /api/inbox/automation/rules
# Create rule
Request:
  name: string
  conditions: object
  action_type: string
  action_config: object
Response:
  rule: AutomationRule

# POST /api/inbox/sync/{platform}
# Manually trigger sync
Response:
  messages_synced: number
  status: "success" | "partial" | "failed"
```

---

## Platform Connectors

### Instagram Connector
```python
# Backend/services/inbox/platform_connectors/instagram_connector.py

class InstagramConnector:
    """Fetch comments and DMs from Instagram."""
    
    async def fetch_comments(self, since: datetime) -> List[InboxMessage]:
        """Fetch comments using RapidAPI or Graph API."""
        pass
    
    async def fetch_dms(self, since: datetime) -> List[InboxMessage]:
        """Fetch DMs using Safari automation."""
        pass
    
    async def send_reply(self, message_id: str, text: str) -> bool:
        """Send reply via Safari automation."""
        pass
```

### TikTok Connector
```python
class TikTokConnector:
    async def fetch_comments(self, since: datetime) -> List[InboxMessage]:
        """Fetch comments using RapidAPI."""
        pass
    
    async def send_reply(self, message_id: str, text: str) -> bool:
        """Send reply via Safari automation."""
        pass
```

### Twitter Connector
```python
class TwitterConnector:
    async def fetch_mentions(self, since: datetime) -> List[InboxMessage]:
        """Fetch mentions and replies."""
        pass
    
    async def fetch_dms(self, since: datetime) -> List[InboxMessage]:
        """Fetch DMs via Safari automation."""
        pass
    
    async def send_reply(self, message_id: str, text: str) -> bool:
        pass
```

### YouTube Connector
```python
class YouTubeConnector:
    async def fetch_comments(self, since: datetime) -> List[InboxMessage]:
        """Fetch comments using YouTube Data API."""
        pass
    
    async def send_reply(self, message_id: str, text: str) -> bool:
        """Reply to comment via API."""
        pass
```

---

## AI Reply Service

```python
# Backend/services/inbox/ai_reply_service.py

class AIReplyService:
    """Generate AI-powered reply suggestions."""
    
    def __init__(self):
        self.client = OpenAI()
    
    async def generate_suggestions(
        self,
        message: InboxMessage,
        context: dict,
        count: int = 3
    ) -> List[ReplySuggestion]:
        """Generate multiple reply options."""
        
        prompt = f"""
        Generate {count} reply suggestions for this social media message.
        
        Platform: {message.platform}
        Original message: "{message.text}"
        Sender: @{message.sender_username} ({message.sender_follower_count} followers)
        Sentiment: {message.sentiment_label}
        
        Context:
        - Brand voice: Friendly, authentic, helpful
        - Content topic: {context.get('content_topic')}
        
        Generate replies that:
        1. Match the brand voice
        2. Are appropriate for the platform
        3. Encourage engagement
        4. Are concise (under 280 chars for Twitter)
        
        Return JSON array with: text, tone, confidence
        """
        
        response = await self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return parse_suggestions(response)
    
    async def analyze_sentiment(
        self,
        text: str
    ) -> tuple[float, str]:
        """Analyze message sentiment."""
        # Returns (score: -1 to 1, label: positive/neutral/negative)
        pass
    
    async def calculate_engagement_score(
        self,
        message: InboxMessage
    ) -> float:
        """Calculate commenter value score (0-100)."""
        score = 0
        
        # Follower count factor (0-30)
        if message.sender_follower_count > 100000:
            score += 30
        elif message.sender_follower_count > 10000:
            score += 20
        elif message.sender_follower_count > 1000:
            score += 10
        
        # Verified badge (0-20)
        if message.sender_is_verified:
            score += 20
        
        # Message length/effort (0-20)
        if len(message.text) > 100:
            score += 20
        elif len(message.text) > 50:
            score += 10
        
        # Question indicator (0-15)
        if '?' in message.text:
            score += 15
        
        # Positive sentiment bonus (0-15)
        if message.sentiment_score > 0.5:
            score += 15
        
        return min(score, 100)
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Week 1)
| Task | Effort |
|------|--------|
| Database schema migration | 4h |
| Base models and services | 8h |
| Platform connector interface | 4h |
| Instagram connector (comments) | 8h |
| Basic API endpoints | 8h |
| Message sync scheduler | 4h |

### Phase 2: UI Foundation (Week 2)
| Task | Effort |
|------|--------|
| Inbox list page | 8h |
| Message detail view | 6h |
| Thread view | 4h |
| Quick actions (read, archive, star) | 4h |
| Platform filters | 4h |
| Search functionality | 6h |

### Phase 3: AI Features (Week 3)
| Task | Effort |
|------|--------|
| Sentiment analyzer integration | 6h |
| AI reply suggestions | 8h |
| Engagement scoring | 4h |
| Priority queue algorithm | 4h |
| Reply generation | 6h |

### Phase 4: Platform Expansion (Week 4)
| Task | Effort |
|------|--------|
| TikTok connector | 8h |
| Twitter connector | 8h |
| YouTube connector | 6h |
| Threads connector | 6h |
| Reply sending (Safari) | 8h |

### Phase 5: Advanced Features (Weeks 5-6)
| Task | Effort |
|------|--------|
| Saved replies system | 8h |
| Automation rules engine | 12h |
| Comment → Content pipeline | 6h |
| Analytics dashboard | 8h |
| Real-time updates (Supabase) | 6h |

---

## Files to Create

```
Backend/services/inbox/
├── __init__.py
├── inbox_service.py           # Core CRUD operations
├── ai_reply_service.py        # AI suggestions
├── sentiment_analyzer.py      # Sentiment analysis
├── engagement_scorer.py       # Value calculation
├── automation_service.py      # Rules engine
├── sync_scheduler.py          # Background sync
├── models.py                  # Pydantic models
└── platform_connectors/
    ├── __init__.py
    ├── base_connector.py
    ├── instagram_connector.py
    ├── tiktok_connector.py
    ├── twitter_connector.py
    ├── youtube_connector.py
    └── threads_connector.py

Backend/api/endpoints/inbox.py

Backend/services/workers/inbox_sync_worker.py

dashboard/app/(dashboard)/inbox/
├── page.tsx                   # Main inbox view
├── [id]/page.tsx              # Message detail
├── saved-replies/page.tsx     # Templates
├── automation/page.tsx        # Rules
├── ideas/page.tsx             # Content ideas
└── components/
    ├── MessageList.tsx
    ├── MessageDetail.tsx
    ├── ThreadView.tsx
    ├── ReplyComposer.tsx
    ├── AISuggestions.tsx
    ├── SavedReplyPicker.tsx
    ├── FilterBar.tsx
    ├── PriorityBadge.tsx
    └── AutomationRuleBuilder.tsx
```

---

## Success Criteria

- [ ] All 5 platforms syncing automatically
- [ ] <5 second load time for inbox
- [ ] AI suggestions available within 2 seconds
- [ ] 90%+ messages replied within 2 hours
- [ ] 10+ content ideas generated per week
- [ ] 5+ automation rules active

---

*Document created: February 1, 2026*
