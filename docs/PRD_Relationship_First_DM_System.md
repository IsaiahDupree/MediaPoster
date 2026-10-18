# PRD: Relationship-First DM Automation System

**Version:** 3.0  
**Date:** January 26, 2026  
**Status:** ✅ Core Implementation Complete  
**Priority:** High  
**Estimated Effort:** 4-6 weeks (Core: 1 day complete)  
**Competitor Analysis:** Revio (getrevio.com)

### Implementation Status

| Requirement | Status | Location |
|-------------|--------|----------|
| RF-001: Health Score | ✅ Complete | `Backend/services/relationship_crm.py` |
| RF-002: Context Cards | ✅ Complete | `Backend/services/relationship_crm.py` |
| RF-003: Pipeline Stages | ✅ Complete | `Backend/services/relationship_crm.py` |
| RF-004: Intent Lanes | ✅ Complete | `Backend/services/relationship_ai.py` |
| RF-005: Next-Best-Action AI | ✅ Complete | `Backend/services/relationship_ai.py` |
| RF-006: Fit Signal Detection | ✅ Complete | `Backend/services/relationship_fit_signals.py` |
| RF-007: Touch Cadences | ✅ Complete | `Backend/services/relationship_cadence.py` |
| RF-008: Success Metrics | ✅ Complete | `Backend/services/relationship_metrics.py` |
| Dashboard UI | ✅ Complete | `dashboard/app/(dashboard)/relationships/page.tsx` |
| API Endpoints | ✅ Complete | `Backend/api/endpoints/relationship_crm.py` |
| Tests | ✅ 19 Passing | `Backend/tests/test_relationship_features.py` |

---

## Executive Summary

Build an AI-powered relationship CRM focused on **trust momentum** and **long-term LTV** rather than aggressive closing. Unlike traditional DM automation tools that optimize for conversions, this system scores **relationship health** and helps users build genuine friendships that naturally lead to business opportunities.

**Key Differentiator:**
```
Revio: "Lead score = buy soon"
MediaPoster: "Relationship health = who needs care"
```

---

## Competitive Analysis: Revio (getrevio.com)

### What Revio Does

| Feature | Description |
|---------|-------------|
| Follower Scraping | Builds lead universe from IG/FB followers |
| AI Lead Scoring | 0-100 score for conversion likelihood |
| Automated Outbound DMs | Messages qualified prospects automatically |
| AI Copilot | Reply suggestions trained on "closed won chats" |
| AI Sales Coach | Scores every chat, provides feedback |
| Unified DM Inbox | Centralized IG/FB messages (LinkedIn coming soon) |
| Personal Audio Follow-ups | Voice notes + video testimonials |
| Pipeline Analytics | Real-time funnel visualization |
| Booking Integration | 24/7 appointment scheduling |

### Revio URLs

| Type | URL |
|------|-----|
| Main site | https://www.getrevio.com |
| App login | https://app.prod.getrevio.cloud/ |
| SSO login | https://valley.getrevio.cloud/ |
| Third-party review | https://sourceforge.net/software/product/Revio/ |
| Feature review | https://www.automateed.com/revio-review |
| Comparison | https://ghlextension.com/versus-getrevio.html |

### Revio Pricing
- ~$500/month for ~20-seat teams (reported)
- Exact pricing requires demo booking

### What's NOT Public About Revio
- Official API/webhook docs
- Rate limits for IG/FB automation
- Compliance guardrails

---

## Our Differentiation: Relationship-First Framework

### Philosophy

Instead of optimizing for "close rate," we optimize for **trust momentum**. LTV is a byproduct of genuine relationships.

### Core Principles

| Principle | Description |
|-----------|-------------|
| **Consent > Conversion** | Ask before advising, pitching, or booking |
| **Micro-wins > Big Promises** | Tiny help delivered fast beats "let's hop on a call" |
| **Reliability is the Product** | Follow-ups, resources, remembering details |
| **3:1 Rule** | For every 1 offer touch, do 3 relationship/value touches |

---

## Feature Specifications

### RF-001: Relationship Health Score (0-100)

**Priority:** P0 (Critical)

Score = "who needs care," not "who needs a pitch."

| Factor | Weight | Signal |
|--------|--------|--------|
| **Recency** | 20% | Days since last meaningful touch |
| **Resonance** | 20% | Reply depth (details/emotion vs "lol") |
| **Need Clarity** | 15% | Do you understand their goal + pain? |
| **Value Delivered** | 20% | Wins delivered in last 30 days |
| **Reliability** | 15% | Promises kept rate |
| **Consent** | 10% | Opt-in level for updates/offers |

#### Score Interpretation

| Score | Action |
|-------|--------|
| 80-100 | Nurture + light collaboration, ask what they're focused on |
| 60-79 | Deliver a micro-win, capture context, establish cadence |
| 40-59 | Re-warm gently (story reply + one question) |
| <40 | Don't chase — leave a kind open loop, re-engage later |

---

### RF-002: Context Cards (Relationship Profiles)

**Priority:** P0 (Critical)

Minimum info to support people like a real friend + pro.

```json
{
  "contact_id": "uuid",
  "platform": "instagram|tiktok|twitter|threads",
  "username": "@example",
  
  "identity": {
    "name": "string",
    "handle": "string",
    "timezone": "America/New_York",
    "how_we_met": "story reply on Dec 15"
  },
  
  "context": {
    "building": "What are they working on right now?",
    "struggles": "What's hard for them lately?",
    "values": "What do they care about (values/style/constraints)?",
    "win_30d": "What would a win look like in 30 days?",
    "preferred_cadence": "daily|weekly|monthly",
    "do_not_do": ["hate calls", "hate spam"]
  },
  
  "scores": {
    "relationship_health": 75,
    "recency_days": 3,
    "resonance": "high",
    "value_delivered_count": 4,
    "trust_signals": ["asked_opinion", "referred_friend"]
  },
  
  "pipeline": {
    "stage": "trust_signals",
    "last_touch": "2026-01-20",
    "next_action": "celebration_prompt",
    "next_action_date": "2026-01-27"
  },
  
  "value_log": [
    {"date": "2026-01-15", "type": "resource", "description": "sent template"},
    {"date": "2026-01-10", "type": "intro", "description": "connected to @other"}
  ]
}
```

---

### RF-003: Relationship Pipeline Stages

**Priority:** P0 (Critical)

8-stage pipeline focused on trust-building:

```
1. First Touch          → They engage / you engage
2. Context Captured     → You know their situation
3. Micro-Win Delivered  → You helped in a tangible way
4. Cadence Established  → Light ongoing touch
5. Trust Signals        → They ask opinions / refer / share personal updates
6. Fit Identified       → A solvable problem appears repeatedly
7. Permissioned Offer   → Only after consent
8. Post-Win Expansion   → Keep helping after purchase
```

**Key Insight:** Most people skip stages 2-5 and wonder why LTV sucks.

**Golden Trigger to Offer:**
- Fit repeats (same pain shows up 2-3 times)
- They've accepted help before
- They ask "what would you do?"

---

### RF-004: Intent Ladder (Non-Salesy Messaging)

**Priority:** P0 (Critical)

Messages live in three lanes:

| Lane | Purpose | Examples |
|------|---------|----------|
| **A: Friendship** | No business | "How did that thing go?" |
| **B: Service** | Value-first | Resources, templates, quick audits, intros |
| **C: Offer** | Permission-based | "Want me to show you a simple way to fix this?" |

**Rule:** Ask permission before offering → stops being pushy.

---

### RF-005: Next-Best-Action AI Engine

**Priority:** P0 (Critical)

AI suggests relationship-building actions, not pitches.

#### Lane A — Friendship Templates

| ID | Template |
|----|----------|
| A1 | "yo—how'd that thing go from last week?" |
| A2 | "ok that's a real win. what do you think made it click?" |
| A3 | "random but i remembered you said you were aiming for ___ — still the plan?" |

#### Lane B — Service Templates

| ID | Template |
|----|----------|
| B1 | "want ideas or just want to vent?" |
| B2 | "if i send you a quick template/checklist for that, would it help?" |
| B3 | "send the screenshot/link — i'll tell you the 1 thing i'd fix first" |
| B4 | "i know someone doing that well. want an intro?" |
| B5 | "this might save you time: [link]. if you tell me your setup i'll tailor it." |

#### Lane C — Offer Templates (Permissioned Only)

| ID | Template |
|----|----------|
| C1 | "you've mentioned ___ a couple times — feels like that's the bottleneck." |
| C2 | "want me to show you a simple way i solve that? no pressure." |
| C3 | "do you want a quick suggestion, or do you want me to actually help you implement it?" |
| C4 | "cool — wanna do 15 min and i'll map the fastest path?" |

#### Retention Templates

| ID | Template |
|----|----------|
| R1 | "how's it feeling now that ___ is live? anything still annoying?" |
| R2 | "i found a tweak that might boost results — want it?" |
| R3 | "what part felt most helpful? i'm tightening the playbook." |
| R4 | "if you know anyone stuck on ___ i'm happy to help them too." |

#### Re-Warm Templates

| ID | Template |
|----|----------|
| W1 | "no rush to reply — what are you focused on this month?" |
| W2 | "saw this and thought of you: [link]. want the 30-sec takeaway?" |

---

### RF-006: Fit Signal Detection

**Priority:** P1 (High)

AI detects when to offer specific products/services.

```json
{
  "offer_fit": {
    "relationship_crm": {
      "signals": [
        "i keep forgetting to follow up",
        "my network is messy",
        "i lost track of mentors/clients",
        "i hate feeling like i'm spamming people"
      ],
      "offer_line": "i built a relationship OS for this—want a quick look when it's ready?"
    },
    "content_analytics": {
      "signals": [
        "my posts aren't converting",
        "i don't know what content is working",
        "i need a repeatable system"
      ],
      "offer_line": "want me to show you a simple way to track what's actually moving the needle?"
    },
    "keyword_research": {
      "signals": [
        "i don't know what to post",
        "i need better topics/hooks",
        "seo feels random"
      ],
      "offer_line": "want a list of topics/hooks tailored to your niche that you can post this week?"
    },
    "automation_services": {
      "signals": [
        "this is taking me forever",
        "i'm drowning in manual work",
        "i need a system"
      ],
      "offer_line": "if you want, i can either (a) give you a quick blueprint, or (b) build the automation with you."
    }
  }
}
```

---

### RF-007: Touch Cadences

**Priority:** P1 (High)

Structured recurring engagement system.

#### Daily (Light)
- Reply to stories
- "how's it going" check-ins for hot relationships

#### Weekly (Structured)
- 10 people: Send a micro-win, resource, or intro
- 10 people: Ask a curiosity question
- 5 people: Permissioned offer (only if fit)

#### Monthly (Deep)
- "Catch-up / reflection" messages
- Ask: "what are you focused on next month?"

---

### RF-008: Success Metrics

**Priority:** P1 (High)

Track relationship quality, not just conversion.

| Metric | What It Measures |
|--------|------------------|
| Meaningful replies/week | Engagement quality |
| % contacts with context cards | Relationship depth |
| Micro-wins delivered/month | Value creation |
| Time-to-follow-up | Reliability |
| Permissioned offers accepted | Offer timing accuracy |
| Referrals/introductions | Trust indicator |

---

## Technical Architecture

### Database Schema

```sql
-- Contacts with relationship context
CREATE TABLE dm_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    username VARCHAR(100) NOT NULL,
    display_name VARCHAR(200),
    profile_url TEXT,
    timezone VARCHAR(50),
    how_we_met TEXT,
    
    -- Context card
    building TEXT,
    struggles TEXT,
    values_style TEXT,
    win_30d TEXT,
    preferred_cadence VARCHAR(20) DEFAULT 'weekly',
    do_not_do TEXT[],
    
    -- Scores
    relationship_health INTEGER DEFAULT 50,
    recency_days INTEGER,
    resonance VARCHAR(20) DEFAULT 'medium',
    value_delivered_count INTEGER DEFAULT 0,
    trust_signals TEXT[],
    
    -- Pipeline
    pipeline_stage VARCHAR(50) DEFAULT 'first_touch',
    last_touch TIMESTAMPTZ,
    next_action VARCHAR(50),
    next_action_date DATE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, platform, username)
);

-- Conversation history
CREATE TABLE dm_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES dm_contacts(id) ON DELETE CASCADE,
    platform VARCHAR(20) NOT NULL,
    platform_message_id VARCHAR(255),
    
    message_type VARCHAR(20) NOT NULL, -- inbound, outbound
    content TEXT NOT NULL,
    intent_lane VARCHAR(20), -- friendship, service, offer
    template_id VARCHAR(20), -- A1, B3, C2, etc.
    ai_suggested BOOLEAN DEFAULT FALSE,
    ai_suggestion_used BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Value tracking (micro-wins)
CREATE TABLE dm_value_delivered (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES dm_contacts(id) ON DELETE CASCADE,
    value_type VARCHAR(50) NOT NULL, -- resource, intro, feedback, template
    description TEXT,
    link TEXT,
    delivered_at TIMESTAMPTZ DEFAULT NOW()
);

-- Offer tracking
CREATE TABLE dm_offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contact_id UUID REFERENCES dm_contacts(id) ON DELETE CASCADE,
    offer_type VARCHAR(100) NOT NULL,
    fit_signals TEXT[],
    permissioned BOOLEAN DEFAULT FALSE,
    accepted BOOLEAN,
    outcome TEXT,
    offered_at TIMESTAMPTZ DEFAULT NOW()
);

-- Touch cadence tracking
CREATE TABLE dm_touch_cadence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) NOT NULL,
    cadence_type VARCHAR(20) NOT NULL, -- daily, weekly, monthly
    scheduled_date DATE NOT NULL,
    completed BOOLEAN DEFAULT FALSE,
    contacts_touched INTEGER DEFAULT 0,
    micro_wins_sent INTEGER DEFAULT 0,
    curiosity_questions INTEGER DEFAULT 0,
    permissioned_offers INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_dm_contacts_health ON dm_contacts(relationship_health DESC);
CREATE INDEX idx_dm_contacts_stage ON dm_contacts(pipeline_stage);
CREATE INDEX idx_dm_contacts_next_action ON dm_contacts(next_action_date);
CREATE INDEX idx_dm_conversations_contact ON dm_conversations(contact_id, created_at DESC);
```

---

### API Endpoints

```
# Contacts
GET    /api/dm/contacts                       # List contacts with filters
GET    /api/dm/contacts/{id}                  # Get contact with context card
POST   /api/dm/contacts                       # Create contact
PUT    /api/dm/contacts/{id}                  # Update context card
PUT    /api/dm/contacts/{id}/stage            # Update pipeline stage
GET    /api/dm/contacts/needs-care            # Low health score contacts

# Conversations
GET    /api/dm/contacts/{id}/conversations    # Get conversation history
POST   /api/dm/contacts/{id}/message          # Send message (via Safari)
GET    /api/dm/contacts/{id}/ai-suggestion    # Get AI next-best-action

# Value Tracking
POST   /api/dm/contacts/{id}/value            # Log value delivered
GET    /api/dm/contacts/{id}/value-log        # Get value history

# Offers
POST   /api/dm/contacts/{id}/offer            # Log offer made
GET    /api/dm/offers/analysis                # Offer timing analysis

# Cadence
GET    /api/dm/cadence/today                  # Today's touch list
POST   /api/dm/cadence/complete               # Mark cadence complete
GET    /api/dm/cadence/stats                  # Cadence completion stats

# Analytics
GET    /api/dm/analytics/health-distribution  # Health score distribution
GET    /api/dm/analytics/pipeline-funnel      # Pipeline stage funnel
GET    /api/dm/analytics/relationship-metrics # Key relationship metrics
```

---

### Pub/Sub Topics

```python
# Relationship DM Topics
DM_CONTACT_CREATED = "dm.contact.created"
DM_CONTACT_UPDATED = "dm.contact.updated"
DM_CONTACT_STAGE_CHANGED = "dm.contact.stage.changed"

DM_MESSAGE_SENT = "dm.message.sent"
DM_MESSAGE_RECEIVED = "dm.message.received"
DM_AI_SUGGESTION_GENERATED = "dm.ai.suggestion.generated"
DM_AI_SUGGESTION_USED = "dm.ai.suggestion.used"

DM_VALUE_DELIVERED = "dm.value.delivered"
DM_OFFER_MADE = "dm.offer.made"
DM_OFFER_ACCEPTED = "dm.offer.accepted"

DM_HEALTH_SCORE_UPDATED = "dm.health.score.updated"
DM_HEALTH_SCORE_LOW = "dm.health.score.low"
DM_TRUST_SIGNAL_DETECTED = "dm.trust.signal.detected"
DM_FIT_SIGNAL_DETECTED = "dm.fit.signal.detected"

DM_CADENCE_REMINDER = "dm.cadence.reminder"
DM_CADENCE_COMPLETED = "dm.cadence.completed"
```

---

## Implementation: Safari Automation

### Local vs Remote Safari

| Approach | Pros | Cons |
|----------|------|------|
| **Local Safari** | Real-time debugging, uses your IP, less bot detection | Requires machine always on, doesn't scale |
| **Remote Safari** | 24/7 operation, scalable, fresh environment | Requires Mac VM (MacStadium, AWS), more setup |
| **Playwright WebKit** | Cross-platform, scriptable, runs on Linux | Not exactly Safari, may trigger some detection |

### Recommended Approach

1. **Development:** Local Safari WebDriver for debugging
2. **Production:** Remote Safari on MacStadium or AWS Mac instance
3. **Fallback:** Playwright WebKit for testing

### Safety Guidelines

| Guideline | Implementation |
|-----------|----------------|
| Conservative volumes | Max 50 DMs/day per account |
| High personalization | Use context card for every message |
| Randomized timing | 2-5 minute delays between messages |
| Human-like behavior | Scroll, pause, type at realistic speed |
| Error detection | Monitor for login challenges, 2FA |
| Rate limit back-off | Exponential back-off on errors |

### Integration with Existing Safari Automation

```python
# Backend/services/dm_automation/
├── __init__.py
├── dm_service.py               # Core DM operations
├── relationship_scorer.py      # Calculate health scores
├── next_action_engine.py       # AI next-best-action
├── fit_signal_detector.py      # Detect offer opportunities
├── cadence_manager.py          # Touch cadence scheduling
└── platform_connectors/
    ├── instagram_dm.py         # Uses safari_instagram_dm.py
    ├── tiktok_dm.py            # Uses safari_tiktok_automation
    ├── twitter_dm.py           # Uses safari_twitter_poster.py
    └── threads_dm.py           # Safari automation
```

---

## Case Studies & Research

### LTV Impact of Relationship-First Approach

| Source | Finding |
|--------|---------|
| Revio Insight (banks) | Personalized outreach increased wallet share per customer |
| Gainsight | 40% revenue growth, 45% share price increase for adopters |
| Real estate CRM | 30% conversion rate increase, 2.3× faster response time |
| B2B SaaS | 40% less admin time, 18% faster sales cycle |
| EveryoneSocial | 68% of B2B customers lost due to perceived apathy, not product |

### Best Practices from Research

1. **CRM as Revenue Engine** — Not a static database
2. **Rich Contact Profiles** — Track interests, past interactions, context
3. **Social Listening** — Monitor what prospects talk about
4. **Value in Every Touchpoint** — Send useful content, not just check-ins
5. **Track Relationship Metrics** — Satisfaction, repeat rate, referrals, tenure

### AI Trends in Relationship Management

| Trend | Application |
|-------|-------------|
| Predictive churn detection | Intervene before customers leave |
| AI personalization at scale | Tailored messages for thousands |
| Relationship intelligence | Map connections within networks |
| Conversational intelligence | Analyze calls for coaching moments |
| Content generation | AI-drafted posts for thought leadership |

---

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Database schema (dm_contacts, dm_conversations, etc.)
- [ ] Relationship health scoring algorithm
- [ ] Pipeline stage tracking
- [ ] Context card CRUD

### Phase 2: AI Integration (Week 2-3)
- [ ] Next-best-action AI engine (OpenAI GPT-4)
- [ ] Fit signal detection
- [ ] Intent lane classification
- [ ] 3:1 rule enforcement

### Phase 3: Automation (Week 3-4)
- [ ] Safari connector integration (IG, TikTok, Twitter, Threads)
- [ ] Daily/weekly/monthly cadence automation
- [ ] Context card auto-population from conversations
- [ ] Permissioned offer timing detection

### Phase 4: Analytics & UI (Week 5-6)
- [ ] Relationship health dashboard
- [ ] Pipeline funnel visualization
- [ ] Cadence completion tracking
- [ ] LTV correlation analysis

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Meaningful replies/week | > 50 |
| Context cards filled | > 80% of active contacts |
| Micro-wins delivered/month | > 20 |
| Avg time-to-follow-up | < 24 hours |
| Permissioned offer acceptance | > 30% |
| Referrals/month | > 5 |
| Relationship health avg | > 70 |

---

## Dependencies

- **OpenAI GPT-4** — AI suggestions, fit signal detection
- **Existing Safari automation** — Platform connectors
- **Supabase** — Database storage
- **Pub/sub event bus** — Event-driven architecture

---

## References

- Revio (getrevio.com) — AI Sales CRM
- Gainsight — Customer success research
- Folk CRM — Relationship-first CRM approach
- EveryoneSocial — Relationship selling statistics
- Instagram Graph API docs
- Safari WebDriver documentation

---

**Document Owner:** Product Team  
**Last Updated:** January 25, 2026  
**Status:** Ready for Implementation
