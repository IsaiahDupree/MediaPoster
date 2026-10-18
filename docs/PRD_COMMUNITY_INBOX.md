# PRD: Community Inbox (Unified Comments/DMs)

**Version:** 1.0  
**Date:** January 19, 2026  
**Status:** Proposed  
**Priority:** High  
**Estimated Effort:** 3 weeks

---

## Executive Summary

MediaPoster needs a unified Community Inbox to manage comments, DMs, and mentions across all connected social platforms from a single interface. This feature includes AI-powered reply suggestions leveraging the existing Content Ops FATE stack, saved reply templates, and the ability to convert engaging comments into content ideas.

---

## Problem Statement

### Current State
- Safari automation exists for individual platform DMs
- Comment automation scripts run independently
- No unified view of all conversations
- No AI assistance for replies
- Manual switching between platforms

### Competitive Gap

| Competitor | Feature | MediaPoster |
|------------|---------|-------------|
| Buffer | Community module with AI replies | ❌ Fragmented automation |
| Later | Social Inbox with sentiment | ❌ None |
| Sprout Social | Unified inbox with CRM | ❌ None |

### User Pain Points
1. Switching between 5+ platform apps to respond
2. Missing important comments/DMs
3. Inconsistent response times
4. No way to prioritize high-value conversations
5. Repetitive typing for common questions

---

## Goals & Success Metrics

### Goals
1. Consolidate all social conversations in one inbox
2. Reduce response time with AI suggestions
3. Identify high-value engagement opportunities
4. Enable team collaboration on responses
5. Convert engagement into content ideas

### Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Response time | < 2 hours average | Time from message to reply |
| AI suggestion usage | > 40% of replies | Replies using AI suggestions |
| Inbox zero rate | > 80% daily | % of messages addressed |
| Content conversions | 5+ per week | Comments → content ideas |
| Engagement score improvement | +15% | FATE score delta |

---

## Features

### Phase 1: Unified Inbox Core (Week 1)

#### 1.1 Message Aggregation
- **Supported platforms:**
  - Instagram (comments, DMs, mentions)
  - TikTok (comments, DMs)
  - Twitter/X (replies, DMs, mentions)
  - YouTube (comments)
  - Threads (comments, mentions)
  - Facebook (comments, messages)
- **Message types:**
  - Comments on posts
  - Direct messages
  - Mentions/tags
  - Story replies
  - Review responses

#### 1.2 Inbox Interface
- **Unified feed:** All messages in chronological order
- **Filters:**
  - By platform
  - By message type (comment/DM/mention)
  - By status (unread/replied/archived)
  - By sentiment (positive/neutral/negative)
  - By engagement score
- **Bulk actions:**
  - Mark as read
  - Archive
  - Assign to team member
  - Add to content ideas

#### 1.3 Conversation Threading
- **Thread view:** See full conversation history
- **Context panel:** View original post being commented on
- **User profile:** Quick view of commenter's profile
- **Previous interactions:** History with this user

### Phase 2: AI-Powered Responses (Week 2)

#### 2.1 AI Reply Suggestions
- **Integration with Content Ops FATE stack:**
  - Match reply tone to brand voice
  - Consider awareness level of commenter
  - Optimize for engagement
- **Suggestion types:**
  - Quick reply (1-2 sentences)
  - Detailed response
  - Question to continue conversation
  - Call-to-action reply
- **Personalization:**
  - Use commenter's name
  - Reference their comment specifics
  - Match platform tone (casual TikTok vs professional LinkedIn)

#### 2.2 Sentiment Analysis
- **Real-time scoring:**
  - Positive (😊)
  - Neutral (😐)
  - Negative (😠)
  - Urgent (🚨)
- **Priority queuing:** Negative/urgent first
- **Alert triggers:** Notify on potential crisis

#### 2.3 Engagement Scoring
- **Commenter value score:**
  - Follower count
  - Engagement rate
  - Previous interactions
  - Influencer status
- **Comment value score:**
  - Virality potential
  - Conversation starter
  - Content idea potential

### Phase 3: Productivity Features (Week 3)

#### 3.1 Saved Replies Library
- **Template categories:**
  - Thank you responses
  - FAQ answers
  - Product inquiries
  - Collaboration requests
  - Negative feedback handling
- **Variables/placeholders:**
  - `{name}` - Commenter's name
  - `{platform}` - Platform name
  - `{product}` - Referenced product
  - `{link}` - Relevant link
- **Keyboard shortcuts:** Quick insert

#### 3.2 Comment → Content Pipeline
- **"Save as idea" action:** One-click to content ideas
- **Auto-categorization:** Suggest content type
- **Trend detection:** Identify frequently asked questions
- **Content suggestions:** "10 people asked about X, create a video"

#### 3.3 Team Collaboration
- **Assignment:** Route messages to team members
- **Internal notes:** Private comments on conversations
- **Collision detection:** Prevent duplicate replies
- **Activity log:** Who replied, when

#### 3.4 Automation Rules
- **Auto-responses:**
  - Welcome message for first-time commenters
  - Thank you for positive reviews
  - Acknowledgment for DMs
- **Auto-tagging:**
  - Tag by keyword
  - Tag by sentiment
  - Tag by user type
- **Auto-assignment:**
  - Route by platform
  - Route by keyword
  - Route by user value

---

## Technical Architecture

### Database Schema

```sql
-- Unified messages table
CREATE TABLE inbox_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    platform VARCHAR(20) NOT NULL, -- instagram, tiktok, twitter, youtube, threads, facebook
    platform_message_id VARCHAR(255) NOT NULL,
    message_type VARCHAR(20) NOT NULL, -- comment, dm, mention, story_reply
    
    -- Content
    content TEXT NOT NULL,
    media_url TEXT,
    
    -- Sender info
    sender_platform_id VARCHAR(255) NOT NULL,
    sender_username VARCHAR(100),
    sender_display_name VARCHAR(200),
    sender_profile_url TEXT,
    sender_follower_count INTEGER,
    
    -- Context
    post_id UUID REFERENCES posts(id),
    post_platform_id VARCHAR(255),
    parent_message_id UUID REFERENCES inbox_messages(id),
    thread_id UUID,
    
    -- Analysis
    sentiment VARCHAR(20), -- positive, neutral, negative
    sentiment_score FLOAT,
    engagement_score FLOAT,
    is_urgent BOOLEAN DEFAULT false,
    
    -- Status
    status VARCHAR(20) DEFAULT 'unread', -- unread, read, replied, archived
    assigned_to UUID REFERENCES users(id),
    replied_at TIMESTAMPTZ,
    
    -- Timestamps
    platform_created_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, platform_message_id)
);

-- Replies sent
CREATE TABLE inbox_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    message_id UUID REFERENCES inbox_messages(id) NOT NULL,
    user_id UUID REFERENCES users(id) NOT NULL,
    
    content TEXT NOT NULL,
    platform_reply_id VARCHAR(255),
    
    -- AI tracking
    used_ai_suggestion BOOLEAN DEFAULT false,
    used_saved_reply_id UUID REFERENCES saved_replies(id),
    ai_suggestion_text TEXT,
    
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'sent' -- sent, failed, pending
);

-- Saved replies library
CREATE TABLE saved_replies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    
    title VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(50),
    
    -- Variables used
    variables JSONB DEFAULT '[]',
    
    -- Usage stats
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Content ideas from comments
CREATE TABLE inbox_content_ideas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    message_id UUID REFERENCES inbox_messages(id),
    
    title VARCHAR(200) NOT NULL,
    description TEXT,
    suggested_format VARCHAR(50), -- video, carousel, story, post
    
    status VARCHAR(20) DEFAULT 'idea', -- idea, planned, created
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Automation rules
CREATE TABLE inbox_automation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    
    name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    
    -- Trigger conditions
    trigger_type VARCHAR(50) NOT NULL, -- new_message, keyword, sentiment, first_time
    trigger_conditions JSONB NOT NULL,
    
    -- Actions
    action_type VARCHAR(50) NOT NULL, -- auto_reply, tag, assign, notify
    action_config JSONB NOT NULL,
    
    -- Stats
    trigger_count INTEGER DEFAULT 0,
    last_triggered_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Message tags
CREATE TABLE inbox_message_tags (
    message_id UUID REFERENCES inbox_messages(id) ON DELETE CASCADE,
    tag VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (message_id, tag)
);

-- Indexes for performance
CREATE INDEX idx_inbox_messages_user_status ON inbox_messages(user_id, status);
CREATE INDEX idx_inbox_messages_platform ON inbox_messages(user_id, platform);
CREATE INDEX idx_inbox_messages_thread ON inbox_messages(thread_id);
CREATE INDEX idx_inbox_messages_sentiment ON inbox_messages(user_id, sentiment);
CREATE INDEX idx_inbox_messages_created ON inbox_messages(created_at DESC);
```

### API Endpoints

```
# Inbox Management
GET    /api/inbox/messages                    # List messages (with filters)
GET    /api/inbox/messages/{id}               # Get single message with thread
GET    /api/inbox/messages/unread/count       # Unread count per platform
PUT    /api/inbox/messages/{id}/status        # Update status (read/archived)
PUT    /api/inbox/messages/{id}/assign        # Assign to team member
POST   /api/inbox/messages/{id}/tags          # Add tags

# Replies
POST   /api/inbox/messages/{id}/reply         # Send reply
GET    /api/inbox/messages/{id}/ai-suggestions # Get AI suggestions
POST   /api/inbox/messages/{id}/ai-generate   # Generate custom AI reply

# Saved Replies
GET    /api/inbox/saved-replies               # List saved replies
POST   /api/inbox/saved-replies               # Create saved reply
PUT    /api/inbox/saved-replies/{id}          # Update saved reply
DELETE /api/inbox/saved-replies/{id}          # Delete saved reply

# Content Ideas
POST   /api/inbox/messages/{id}/to-idea       # Convert to content idea
GET    /api/inbox/content-ideas               # List content ideas from inbox

# Automation
GET    /api/inbox/automation/rules            # List rules
POST   /api/inbox/automation/rules            # Create rule
PUT    /api/inbox/automation/rules/{id}       # Update rule
DELETE /api/inbox/automation/rules/{id}       # Delete rule

# Analytics
GET    /api/inbox/analytics/response-time     # Average response times
GET    /api/inbox/analytics/sentiment         # Sentiment breakdown
GET    /api/inbox/analytics/volume            # Message volume trends

# Sync
POST   /api/inbox/sync/{platform}             # Manual sync for platform
GET    /api/inbox/sync/status                 # Sync status per platform
```

### Integration with Existing Safari Automation

```python
# Backend/services/inbox/platform_connectors/
├── __init__.py
├── base_connector.py           # Abstract base class
├── instagram_connector.py      # Uses safari_instagram_dm.py
├── tiktok_connector.py         # Uses safari_tiktok_automation
├── twitter_connector.py        # Uses safari_twitter_poster.py
├── youtube_connector.py        # YouTube Data API
├── threads_connector.py        # Safari automation
└── facebook_connector.py       # Graph API / Safari

# Each connector implements:
class PlatformConnector:
    async def fetch_messages(self, since: datetime) -> List[Message]
    async def send_reply(self, message_id: str, content: str) -> bool
    async def mark_as_read(self, message_id: str) -> bool
```

### AI Reply Generation Service

```python
# Backend/services/inbox/ai_reply_service.py

class AIReplyService:
    """
    Generates reply suggestions using OpenAI GPT-4
    Integrates with Content Ops FATE stack for brand voice
    """
    
    async def generate_suggestions(
        self,
        message: InboxMessage,
        brand_voice: BrandVoice,
        context: dict
    ) -> List[ReplySuggestion]:
        """
        Returns 3-4 reply options:
        - Quick acknowledgment
        - Detailed response
        - Engaging question
        - CTA response
        """
        
    async def analyze_sentiment(
        self,
        content: str
    ) -> SentimentResult:
        """
        Returns sentiment score and urgency flag
        """
        
    async def score_engagement_potential(
        self,
        message: InboxMessage,
        sender_profile: dict
    ) -> float:
        """
        Returns 0-100 score for engagement priority
        """
```

### File Structure

```
Backend/
├── services/
│   └── inbox/
│       ├── __init__.py
│       ├── inbox_service.py          # Core inbox operations
│       ├── ai_reply_service.py       # AI suggestions
│       ├── sentiment_analyzer.py     # Sentiment analysis
│       ├── engagement_scorer.py      # Commenter scoring
│       ├── saved_reply_service.py    # Template management
│       ├── automation_service.py     # Rule engine
│       ├── content_idea_service.py   # Comment → idea conversion
│       └── platform_connectors/      # Per-platform adapters
│           ├── base_connector.py
│           ├── instagram_connector.py
│           ├── tiktok_connector.py
│           └── ...
├── api/
│   └── endpoints/
│       └── inbox_api.py              # API routes
├── workers/
│   └── inbox_sync_worker.py          # Background sync

dashboard/
├── app/
│   └── (dashboard)/
│       └── inbox/
│           ├── page.tsx              # Main inbox view
│           ├── [id]/
│           │   └── page.tsx          # Conversation detail
│           ├── saved-replies/
│           │   └── page.tsx          # Saved replies manager
│           └── automation/
│               └── page.tsx          # Automation rules
├── components/
│   └── inbox/
│       ├── MessageList.tsx           # Message feed
│       ├── MessageCard.tsx           # Single message
│       ├── ConversationThread.tsx    # Thread view
│       ├── ReplyComposer.tsx         # Reply with AI suggestions
│       ├── AISuggestionPanel.tsx     # AI reply options
│       ├── SentimentBadge.tsx        # Sentiment indicator
│       ├── SavedReplyPicker.tsx      # Insert saved reply
│       └── AutomationRuleEditor.tsx  # Rule builder
```

---

## User Interface

### Main Inbox View
```
┌─────────────────────────────────────────────────────────────────────┐
│  Community Inbox                    🔔 23 new    [Compose] [Sync]   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Filters: [All ▼] [Unread ▼] [All Platforms ▼] [All Sentiment ▼]    │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ IG 😊 @fashionlover123                              2 min ago   │ │
│  │ "Love this outfit! Where did you get the jacket? 🔥"            │ │
│  │ On: "Summer collection drop" • Score: 85                        │ │
│  │ [Quick Reply] [AI Suggest] [Archive]                            │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ TT 😐 @newuser_2024                                 15 min ago  │ │
│  │ "How long does shipping take?"                                   │ │
│  │ DM • Score: 45                                                   │ │
│  │ [Quick Reply] [AI Suggest] [Use Template: Shipping FAQ]         │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ X  😠 @unhappy_customer                            1 hour ago   │ │
│  │ "Still waiting for my order. This is unacceptable!"             │ │
│  │ Mention • Score: 92 • 🚨 URGENT                                 │ │
│  │ [View Thread] [AI Suggest] [Escalate]                           │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Reply Composer with AI
```
┌─────────────────────────────────────────────────────────────────────┐
│  Reply to @fashionlover123                                    [×]   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  Original: "Love this outfit! Where did you get the jacket? 🔥"     │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ AI Suggestions                                    [Regenerate]  │ │
│  │                                                                  │ │
│  │ ○ Quick: "Thank you! 💕 The jacket is from @brandname!"        │ │
│  │                                                                  │ │
│  │ ○ Detailed: "Thanks so much! The jacket is the Milano         │ │
│  │   from @brandname - I linked it in my bio! 🔗"                  │ │
│  │                                                                  │ │
│  │ ○ Engaging: "Aww thank you! What's your go-to jacket          │ │
│  │   style? I'm obsessed with oversized fits lately 👀"           │ │
│  │                                                                  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  Your reply:                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │ Thank you! 💕 The jacket is from @brandname - linked in bio!   │ │
│  │                                                                  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                       │
│  [📝 Saved Replies] [✨ Improve with AI]        [Cancel] [Send →]   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Timeline

### Week 1: Core Inbox
| Day | Task |
|-----|------|
| 1-2 | Database schema, message models |
| 3 | Platform connectors (Instagram, TikTok) |
| 4 | Platform connectors (Twitter, YouTube) |
| 5 | Inbox API endpoints, message sync |

### Week 2: AI & Analysis
| Day | Task |
|-----|------|
| 6 | Sentiment analysis integration |
| 7 | AI reply suggestion service |
| 8 | Engagement scoring |
| 9 | Frontend inbox UI |
| 10 | Reply composer with AI |

### Week 3: Productivity
| Day | Task |
|-----|------|
| 11 | Saved replies system |
| 12 | Automation rules engine |
| 13 | Comment → content idea flow |
| 14 | Team collaboration features |
| 15 | Testing, polish, documentation |

---

## Dependencies

- **OpenAI GPT-4:** AI reply generation
- **Existing Safari automation:** Platform connectors
- **Content Ops FATE stack:** Brand voice integration
- **Supabase Realtime:** Live inbox updates
- **Background workers:** Message sync

---

## Future Enhancements

1. **CRM integration:** Link conversations to customer profiles
2. **Smart routing:** AI-based assignment to team members
3. **Response SLA:** Track and alert on response time goals
4. **Sentiment trends:** Track sentiment over time
5. **Competitor mention alerts:** Monitor competitor mentions
6. **Voice replies:** Audio message support

---

**Document Owner:** Product Team  
**Last Updated:** January 19, 2026  
**Next Review:** February 2026
