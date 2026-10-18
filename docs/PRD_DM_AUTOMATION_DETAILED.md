# PRD: DM Automation System (Detailed)

**Version:** 1.0  
**Date:** February 1, 2026  
**Status:** Ready for Implementation  
**Track:** T4.1 Sales & DM Automation  
**Effort:** 4-5 weeks  
**Priority:** 🟡 High

---

## Executive Summary

Build a relationship-first DM automation system inspired by Revio but with a key differentiator: instead of "lead scoring" (who's ready to buy), MediaPoster uses "relationship health scoring" (who needs care). This creates authentic connections that convert better long-term.

---

## Key Differentiator

```
┌─────────────────────────────────────────────────────────────────┐
│                    REVIO vs MEDIAPOSTER                          │
├────────────────────────┬────────────────────────────────────────┤
│         REVIO          │           MEDIAPOSTER                   │
├────────────────────────┼────────────────────────────────────────┤
│ Lead Score = "buy soon"│ Relationship Health = "who needs care" │
│ Push offers            │ Build genuine connection first         │
│ Conversion-first       │ Relationship-first, conversion follows │
│ Quantity of outreach   │ Quality of relationship                │
│ One-size automation    │ Personalized touch cadences            │
└────────────────────────┴────────────────────────────────────────┘
```

---

## Goals

| Goal | Metric | Target |
|------|--------|--------|
| Relationship health | Avg score across contacts | 70+ |
| Response rate | DMs that get replies | 40%+ |
| 3:1 Rule | Non-offer touches per offer | 3:1 minimum |
| Conversion | Relationships → Customers | 15%+ |
| Time savings | Hours saved per week | 10+ hours |

---

## Core Concepts

### 1. Relationship Health Score (0-100)

```python
Relationship Health Score = (
    Recency Score (0-20) +      # Days since last interaction
    Frequency Score (0-20) +    # Number of touches in 30 days
    Value Delivered (0-20) +    # Non-offer value provided
    Engagement Score (0-15) +   # Their engagement with our content
    Response Rate (0-15) +      # How often they reply
    Trust Signals (0-10)        # Saved posts, shares, tags
)
```

### 2. Eight-Stage Relationship Pipeline

| Stage | Name | Description | Touch Frequency |
|-------|------|-------------|-----------------|
| 1 | **Cold** | No interaction yet | Weekly curiosity |
| 2 | **Engaged** | Liked/commented once | 2x weekly |
| 3 | **Warm** | Multiple engagements | 3x weekly |
| 4 | **Connected** | DM conversation started | Every 2-3 days |
| 5 | **Trusting** | Shared value, they respond | Every 2 days |
| 6 | **Ready** | Expressed interest/pain | Daily support |
| 7 | **Customer** | Made purchase | Weekly check-in |
| 8 | **Advocate** | Refers others | Monthly appreciation |

### 3. Intent Ladder (A/B/C Lanes)

| Lane | Intent | Approach |
|------|--------|----------|
| **A** | Friendship | Pure relationship building, no business talk |
| **B** | Service | Share value, answer questions, help |
| **C** | Offer | Present opportunities when appropriate |

**Rule:** Most contacts stay in Lane A/B. Only move to C when:
- 3+ value touches delivered
- Pain point expressed
- Direct question about services

### 4. The 3:1 Rule

For every offer/pitch, deliver **3 non-offer touches**:
- Celebrate their wins
- Share helpful resources
- Ask about their journey
- Comment on their content
- Share relevant insights

---

## User Stories

### US-1: Relationship Dashboard
**As a** creator  
**I want** to see all my relationships in one place  
**So that** I know who needs attention

### US-2: Context Cards
**As a** creator  
**I want** to track what I know about each contact  
**So that** I can personalize every interaction

### US-3: AI-Suggested Actions
**As a** creator  
**I want** AI to tell me the best next action  
**So that** I never wonder what to say

### US-4: Automated Cadences
**As a** creator  
**I want** automated reminders for touch cadences  
**So that** no relationship goes cold

### US-5: 3:1 Enforcement
**As a** creator  
**I want** the system to prevent pitching too soon  
**So that** I build trust before asking

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      DM AUTOMATION SYSTEM                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    CONTACT MANAGER                               │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │   Import    │  │   Context   │  │    Relationship         │  │   │
│  │  │  Contacts   │  │   Cards     │  │    Health Scoring       │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                │                                        │
│                                ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    PIPELINE ENGINE                               │   │
│  │  ┌─────────────────────────────────────────────────────────┐   │   │
│  │  │ Cold → Engaged → Warm → Connected → Trusting → Ready    │   │   │
│  │  │                           → Customer → Advocate          │   │   │
│  │  └─────────────────────────────────────────────────────────┘   │   │
│  │                                                                  │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                         │   │
│  │  │ Lane A  │  │ Lane B  │  │ Lane C  │                         │   │
│  │  │Friendship│  │ Service │  │  Offer  │                         │   │
│  │  └─────────┘  └─────────┘  └─────────┘                         │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                │                                        │
│                                ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    AI ACTION ENGINE                              │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │  Next Best  │  │   Message   │  │     3:1 Rule            │  │   │
│  │  │   Action    │  │  Generator  │  │    Enforcement          │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                │                                        │
│                                ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    TOUCH CADENCE ENGINE                          │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │   │
│  │  │   Daily     │  │   Weekly    │  │      Monthly            │  │   │
│  │  │   Queue     │  │   Queue     │  │      Queue              │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                │                                        │
│                                ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    DM SENDER (Safari Automation)                 │   │
│  │  Instagram │ Twitter │ LinkedIn │ Facebook │ Threads            │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

```sql
-- Migration: 20260201_dm_automation.sql

-- DM Contacts (CRM)
CREATE TABLE dm_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Identity
    platform VARCHAR(20) NOT NULL,
    platform_user_id VARCHAR(255),
    username VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    avatar_url TEXT,
    bio TEXT,
    
    -- Stats
    follower_count INTEGER,
    following_count INTEGER,
    post_count INTEGER,
    is_verified BOOLEAN DEFAULT FALSE,
    
    -- Pipeline
    pipeline_stage VARCHAR(20) DEFAULT 'cold', -- 8 stages
    intent_lane VARCHAR(1) DEFAULT 'A', -- A, B, C
    
    -- Scores
    relationship_health_score FLOAT DEFAULT 0,
    recency_score FLOAT DEFAULT 0,
    frequency_score FLOAT DEFAULT 0,
    value_score FLOAT DEFAULT 0,
    engagement_score FLOAT DEFAULT 0,
    response_rate FLOAT DEFAULT 0,
    trust_signals_score FLOAT DEFAULT 0,
    
    -- 3:1 Tracking
    non_offer_touches INTEGER DEFAULT 0,
    offer_touches INTEGER DEFAULT 0,
    last_offer_at TIMESTAMPTZ,
    can_offer BOOLEAN GENERATED ALWAYS AS (non_offer_touches >= 3 * offer_touches) STORED,
    
    -- Context Card
    context_card JSONB DEFAULT '{}',
    -- {
    --   "building": "What they're working on",
    --   "struggles": ["Pain point 1", "Pain point 2"],
    --   "values": ["Family", "Growth"],
    --   "wins": ["Recent achievement"],
    --   "interests": ["Topic 1", "Topic 2"],
    --   "notes": "Personal notes"
    -- }
    
    -- Tags
    tags VARCHAR(100)[],
    
    -- Source
    source VARCHAR(50), -- manual, comment, dm_first, follower, import
    source_content_id UUID,
    
    -- Timestamps
    first_interaction_at TIMESTAMPTZ,
    last_interaction_at TIMESTAMPTZ,
    last_touch_at TIMESTAMPTZ,
    next_touch_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(platform, username)
);

-- DM Conversations
CREATE TABLE dm_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES dm_contacts(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL,
    
    -- Status
    status VARCHAR(20) DEFAULT 'active', -- active, paused, archived
    unread_count INTEGER DEFAULT 0,
    
    -- Last message
    last_message_text TEXT,
    last_message_at TIMESTAMPTZ,
    last_message_by VARCHAR(10), -- 'us' or 'them'
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- DM Messages
CREATE TABLE dm_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES dm_conversations(id) ON DELETE CASCADE,
    contact_id UUID REFERENCES dm_contacts(id),
    
    -- Direction
    direction VARCHAR(10) NOT NULL, -- inbound, outbound
    
    -- Content
    text TEXT,
    media_urls JSONB,
    
    -- Classification
    message_type VARCHAR(20), -- curiosity, support, celebration, value, offer, response
    intent_lane VARCHAR(1), -- A, B, C
    is_offer BOOLEAN DEFAULT FALSE,
    
    -- Status
    status VARCHAR(20) DEFAULT 'sent', -- draft, queued, sent, delivered, read, failed
    platform_message_id VARCHAR(255),
    
    -- AI
    ai_generated BOOLEAN DEFAULT FALSE,
    ai_model VARCHAR(50),
    
    -- Timestamps
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Value Delivered (tracking non-offer touches)
CREATE TABLE dm_value_delivered (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES dm_contacts(id) ON DELETE CASCADE,
    
    value_type VARCHAR(50) NOT NULL, 
    -- Types: curiosity_question, celebration, resource_share, helpful_reply, 
    --        content_comment, story_reply, genuine_compliment
    
    description TEXT,
    message_id UUID REFERENCES dm_messages(id),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Offers (tracking pitch touches)
CREATE TABLE dm_offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES dm_contacts(id) ON DELETE CASCADE,
    message_id UUID REFERENCES dm_messages(id),
    
    offer_type VARCHAR(50), -- soft_mention, direct_pitch, follow_up
    offer_description TEXT,
    
    -- Outcome
    outcome VARCHAR(20), -- pending, interested, declined, converted
    outcome_at TIMESTAMPTZ,
    conversion_value DECIMAL,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Touch Cadence Queue
CREATE TABLE dm_touch_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES dm_contacts(id) ON DELETE CASCADE,
    
    -- Scheduling
    scheduled_at TIMESTAMPTZ NOT NULL,
    touch_type VARCHAR(50) NOT NULL, -- daily_check, weekly_value, monthly_appreciation
    
    -- Suggested action
    suggested_action VARCHAR(100),
    suggested_message TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- pending, completed, skipped
    completed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- AI Action Suggestions
CREATE TABLE dm_action_suggestions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES dm_contacts(id) ON DELETE CASCADE,
    
    action_type VARCHAR(50) NOT NULL,
    -- Types: send_curiosity, celebrate_win, share_resource, ask_question,
    --        comment_on_content, move_to_lane_b, make_offer
    
    reason TEXT,
    suggested_message TEXT,
    priority INTEGER, -- 1-10
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- pending, accepted, dismissed
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

-- Indexes
CREATE INDEX idx_contacts_platform ON dm_contacts(platform);
CREATE INDEX idx_contacts_stage ON dm_contacts(pipeline_stage);
CREATE INDEX idx_contacts_health ON dm_contacts(relationship_health_score DESC);
CREATE INDEX idx_contacts_next_touch ON dm_contacts(next_touch_at);
CREATE INDEX idx_messages_conversation ON dm_messages(conversation_id);
CREATE INDEX idx_messages_contact ON dm_messages(contact_id);
CREATE INDEX idx_touch_queue_scheduled ON dm_touch_queue(scheduled_at);
CREATE INDEX idx_touch_queue_status ON dm_touch_queue(status);
```

---

## API Endpoints

### Contacts

```yaml
# GET /api/dm/contacts
# List all contacts with filters
Query:
  platform: string
  pipeline_stage: string
  intent_lane: string
  min_health: number
  needs_attention: boolean
  tags: string[]
  search: string
  sort: "health" | "last_touch" | "next_touch"
Response:
  contacts: Contact[]
  stats: {total, by_stage, avg_health}

# GET /api/dm/contacts/{id}
# Get contact with full context
Response:
  contact: Contact
  context_card: ContextCard
  recent_messages: Message[]
  value_delivered: ValueDelivered[]
  offers: Offer[]
  suggested_actions: Action[]

# POST /api/dm/contacts
# Create new contact
Request:
  platform: string
  username: string
  source: string
  context_card: object
Response:
  contact: Contact

# PUT /api/dm/contacts/{id}
# Update contact
Request:
  pipeline_stage: string
  intent_lane: string
  context_card: object
  tags: string[]

# PUT /api/dm/contacts/{id}/context
# Update context card
Request:
  building: string
  struggles: string[]
  values: string[]
  wins: string[]
  interests: string[]
  notes: string
```

### Pipeline

```yaml
# GET /api/dm/pipeline
# Get pipeline overview
Response:
  stages: [
    {stage: "cold", count: 45, avg_health: 12},
    {stage: "engaged", count: 23, avg_health: 35},
    ...
  ]

# POST /api/dm/contacts/{id}/stage
# Move contact to new stage
Request:
  stage: string
  reason: string
Response:
  contact: Contact

# GET /api/dm/pipeline/{stage}
# Get contacts in stage
Response:
  contacts: Contact[]
```

### Messages

```yaml
# GET /api/dm/conversations
# List conversations
Query:
  status: string
  unread: boolean
Response:
  conversations: Conversation[]

# GET /api/dm/conversations/{id}/messages
# Get messages in conversation
Response:
  messages: Message[]

# POST /api/dm/contacts/{id}/message
# Send message
Request:
  text: string
  message_type: string
  is_offer: boolean
Response:
  message: Message
  status: "sent" | "queued" | "failed"

# POST /api/dm/contacts/{id}/value
# Log value delivered
Request:
  value_type: string
  description: string
  message_id: uuid (optional)
```

### AI Actions

```yaml
# GET /api/dm/contacts/{id}/suggestions
# Get AI-suggested actions
Response:
  suggestions: [
    {
      action_type: string,
      reason: string,
      suggested_message: string,
      priority: number
    }
  ]

# POST /api/dm/contacts/{id}/generate-message
# Generate personalized message
Request:
  intent: "curiosity" | "support" | "celebration" | "value" | "offer"
  context: string (optional)
Response:
  message: string
  tone: string

# GET /api/dm/daily-queue
# Get today's touch queue
Response:
  queue: [
    {
      contact: Contact,
      touch_type: string,
      suggested_action: string,
      suggested_message: string
    }
  ]
```

### Analytics

```yaml
# GET /api/dm/analytics
# Get DM analytics
Query:
  period: "7d" | "30d" | "90d"
Response:
  metrics: {
    total_contacts: number,
    avg_health: number,
    response_rate: number,
    conversations_started: number,
    offers_made: number,
    conversions: number,
    value_touches: number
  }
  by_stage: {...}
  by_platform: {...}

# GET /api/dm/analytics/3-1-ratio
# Get 3:1 compliance
Response:
  overall_ratio: number,
  by_contact: [{contact_id, ratio, compliant}]
```

---

## Core Services

### 1. Relationship Health Calculator
```python
# Backend/services/dm/relationship_health.py

class RelationshipHealthCalculator:
    """Calculate relationship health score."""
    
    def calculate_health_score(self, contact: Contact) -> float:
        """Calculate overall health score (0-100)."""
        
        scores = {
            "recency": self.calc_recency_score(contact),      # 0-20
            "frequency": self.calc_frequency_score(contact),  # 0-20
            "value": self.calc_value_score(contact),          # 0-20
            "engagement": self.calc_engagement_score(contact),# 0-15
            "response": self.calc_response_score(contact),    # 0-15
            "trust": self.calc_trust_score(contact),          # 0-10
        }
        
        return sum(scores.values())
    
    def calc_recency_score(self, contact: Contact) -> float:
        """Score based on days since last interaction (0-20)."""
        days = (datetime.now() - contact.last_interaction_at).days
        if days <= 1: return 20
        if days <= 3: return 16
        if days <= 7: return 12
        if days <= 14: return 8
        if days <= 30: return 4
        return 0
    
    def calc_value_score(self, contact: Contact) -> float:
        """Score based on non-offer value delivered (0-20)."""
        value_count = contact.non_offer_touches
        if value_count >= 10: return 20
        if value_count >= 7: return 16
        if value_count >= 5: return 12
        if value_count >= 3: return 8
        if value_count >= 1: return 4
        return 0
```

### 2. AI Action Engine
```python
# Backend/services/dm/ai_action_engine.py

class AIActionEngine:
    """Generate next-best-action suggestions."""
    
    async def get_suggestions(
        self,
        contact: Contact,
        count: int = 3
    ) -> List[ActionSuggestion]:
        """Generate prioritized action suggestions."""
        
        suggestions = []
        
        # Check relationship health
        if contact.relationship_health_score < 30:
            suggestions.append(self.suggest_reactivation(contact))
        
        # Check recency
        days_since_touch = (datetime.now() - contact.last_touch_at).days
        if days_since_touch > 3:
            suggestions.append(self.suggest_touch(contact))
        
        # Check 3:1 ratio
        if contact.can_offer and contact.pipeline_stage in ["trusting", "ready"]:
            suggestions.append(self.suggest_soft_offer(contact))
        
        # Check for celebration opportunities
        if await self.has_recent_win(contact):
            suggestions.append(self.suggest_celebration(contact))
        
        # Sort by priority and return top N
        return sorted(suggestions, key=lambda x: x.priority, reverse=True)[:count]
    
    async def generate_message(
        self,
        contact: Contact,
        intent: str,
        context: str = None
    ) -> str:
        """Generate personalized message using GPT."""
        
        prompt = f"""
        Generate a DM for Instagram.
        
        Contact: @{contact.username}
        Relationship stage: {contact.pipeline_stage}
        Intent lane: {contact.intent_lane}
        
        Context card:
        - Building: {contact.context_card.get('building')}
        - Struggles: {contact.context_card.get('struggles')}
        - Interests: {contact.context_card.get('interests')}
        - Recent wins: {contact.context_card.get('wins')}
        
        Intent: {intent}
        Additional context: {context or 'None'}
        
        Generate a message that:
        1. Is authentic and personal
        2. References something specific about them
        3. Feels like it's from a friend, not a marketer
        4. Is concise (under 200 chars)
        5. {"Does NOT mention any offer or business" if intent != 'offer' else "Naturally introduces the offer"}
        
        Return only the message text.
        """
        
        response = await self.openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content
```

### 3. Touch Cadence Manager
```python
# Backend/services/dm/cadence_manager.py

class TouchCadenceManager:
    """Manage touch cadence scheduling."""
    
    CADENCE_BY_STAGE = {
        "cold": timedelta(days=7),
        "engaged": timedelta(days=3),
        "warm": timedelta(days=2),
        "connected": timedelta(days=2),
        "trusting": timedelta(days=2),
        "ready": timedelta(days=1),
        "customer": timedelta(days=7),
        "advocate": timedelta(days=30),
    }
    
    async def schedule_next_touch(self, contact: Contact) -> TouchQueue:
        """Schedule next touch based on stage."""
        
        cadence = self.CADENCE_BY_STAGE.get(contact.pipeline_stage, timedelta(days=7))
        next_touch = datetime.now() + cadence
        
        # Determine touch type
        touch_type = self.determine_touch_type(contact)
        
        # Generate suggested message
        suggested = await self.ai_engine.generate_message(
            contact,
            intent=self.intent_for_touch(touch_type)
        )
        
        return await self.create_queue_item(
            contact_id=contact.id,
            scheduled_at=next_touch,
            touch_type=touch_type,
            suggested_message=suggested
        )
    
    async def get_daily_queue(self) -> List[TouchQueue]:
        """Get all touches scheduled for today."""
        return await self.repo.get_pending_touches_before(
            datetime.now() + timedelta(days=1)
        )
```

### 4. Three-One Rule Enforcer
```python
# Backend/services/dm/three_one_enforcer.py

class ThreeOneEnforcer:
    """Enforce 3:1 value-to-offer ratio."""
    
    def can_make_offer(self, contact: Contact) -> tuple[bool, str]:
        """Check if offer is allowed."""
        
        if contact.non_offer_touches < 3:
            return False, f"Need {3 - contact.non_offer_touches} more value touches"
        
        ratio = contact.non_offer_touches / max(contact.offer_touches + 1, 1)
        if ratio < 3:
            needed = (contact.offer_touches + 1) * 3 - contact.non_offer_touches
            return False, f"Ratio is {ratio:.1f}:1, need {needed} more value touches"
        
        return True, "Offer allowed"
    
    def log_value_touch(self, contact: Contact, value_type: str) -> Contact:
        """Log a non-offer touch."""
        contact.non_offer_touches += 1
        contact.last_touch_at = datetime.now()
        return contact
    
    def log_offer_touch(self, contact: Contact) -> Contact:
        """Log an offer touch."""
        contact.offer_touches += 1
        contact.last_offer_at = datetime.now()
        return contact
```

---

## Implementation Phases

### Phase 1: Contact Management (Week 1)
| Task | Effort |
|------|--------|
| Database schema | 4h |
| Contact CRUD API | 6h |
| Context card system | 4h |
| Import from existing sources | 6h |
| Basic contact list UI | 8h |
| Contact detail page | 8h |

### Phase 2: Pipeline & Health (Week 2)
| Task | Effort |
|------|--------|
| Relationship health calculator | 6h |
| Pipeline stage logic | 4h |
| Intent lane system | 4h |
| 3:1 rule enforcer | 4h |
| Pipeline board UI | 8h |
| Health dashboard | 6h |

### Phase 3: Messaging (Week 3)
| Task | Effort |
|------|--------|
| Conversation management | 6h |
| Message sending (Safari) | 8h |
| Message logging | 4h |
| Value delivered tracking | 4h |
| Conversation UI | 8h |
| Message composer | 6h |

### Phase 4: AI Engine (Week 4)
| Task | Effort |
|------|--------|
| AI action suggestions | 8h |
| Message generation | 6h |
| Touch cadence manager | 6h |
| Daily queue system | 4h |
| Action suggestions UI | 6h |
| Daily queue UI | 6h |

### Phase 5: Analytics & Polish (Week 5)
| Task | Effort |
|------|--------|
| Analytics dashboard | 8h |
| 3:1 compliance reports | 4h |
| Bulk actions | 4h |
| Import/export contacts | 4h |
| Background sync | 6h |
| Testing & polish | 8h |

---

## Files to Create

```
Backend/services/dm/
├── __init__.py
├── contact_service.py
├── conversation_service.py
├── relationship_health.py
├── pipeline_manager.py
├── ai_action_engine.py
├── cadence_manager.py
├── three_one_enforcer.py
├── message_sender.py
├── analytics_service.py
└── models.py

Backend/api/endpoints/dm.py

Backend/services/workers/dm_cadence_worker.py

dashboard/app/(dashboard)/dm/
├── page.tsx                   # Pipeline board
├── contacts/page.tsx          # Contact list
├── contacts/[id]/page.tsx     # Contact detail
├── conversations/page.tsx     # All conversations
├── daily-queue/page.tsx       # Today's touches
├── analytics/page.tsx         # DM analytics
└── components/
    ├── PipelineBoard.tsx
    ├── ContactCard.tsx
    ├── ContextCardEditor.tsx
    ├── HealthMeter.tsx
    ├── ConversationView.tsx
    ├── MessageComposer.tsx
    ├── ActionSuggestions.tsx
    ├── ThreeOneIndicator.tsx
    └── DailyQueueList.tsx
```

---

## Integration with Safari Automation

```python
# Backend/services/dm/message_sender.py

class DMMessageSender:
    """Send DMs via Safari automation."""
    
    def __init__(self):
        self.safari_automation = SafariAutomation()
    
    async def send_instagram_dm(
        self,
        username: str,
        message: str
    ) -> SendResult:
        """Send Instagram DM via Safari."""
        
        return await self.safari_automation.send_dm(
            platform="instagram",
            recipient=username,
            message=message
        )
    
    async def send_twitter_dm(
        self,
        username: str,
        message: str
    ) -> SendResult:
        """Send Twitter DM via Safari."""
        
        return await self.safari_automation.send_dm(
            platform="twitter",
            recipient=username,
            message=message
        )
```

---

## Success Criteria

- [ ] All contacts have relationship health scores
- [ ] 8-stage pipeline tracking working
- [ ] 3:1 rule enforced system-wide
- [ ] AI generates contextual messages
- [ ] Daily queue surfacing touches
- [ ] Response rate > 40%
- [ ] 10+ hours saved per week

---

## Value Touch Examples

| Type | Example |
|------|---------|
| **Curiosity** | "Saw your post about X - what inspired that?" |
| **Celebration** | "Congrats on hitting 10K! 🎉 How are you feeling?" |
| **Resource** | "Thought of you when I saw this article about Y" |
| **Support** | "How's the [project they mentioned] going?" |
| **Compliment** | "Your content on Z is so helpful - learned a lot!" |
| **Story Reply** | "Love that sunset! Where was that?" |
| **Comment** | Genuine comment on their recent post |

---

*Document created: February 1, 2026*
