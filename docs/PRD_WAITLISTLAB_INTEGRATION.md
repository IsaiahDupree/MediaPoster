# PRD: WaitlistLab Integration

**Version:** 1.0  
**Date:** February 1, 2026  
**Status:** Ready for Implementation  
**Track:** New Track - Lead Generation  
**Effort:** 5 weeks  
**Priority:** 🟡 High

---

## Executive Summary

Integrate WaitlistLab functionality into MediaPoster by reusing **70% of existing infrastructure**. This adds lead generation, Meta Ads automation, and email sequences without building from scratch.

---

## Strategic Rationale

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           WHY INTEGRATE WAITLISTLAB?                                 │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│   MEDIAPOSTER TODAY                      MEDIAPOSTER + WAITLISTLAB                  │
│   ─────────────────────                  ──────────────────────────                 │
│   Content Creation                       Content Creation                            │
│   Content Publishing                     Content Publishing                          │
│   Analytics & Insights                   Analytics & Insights                        │
│                                          + Lead Generation                          │
│                                          + Meta Ads Automation                      │
│                                          + Email Sequences                          │
│                                          + Waitlist Management                      │
│                                                                                      │
│   REVENUE MODEL                                                                      │
│   ─────────────                                                                     │
│   Brand building (indirect)      →       Direct lead capture + conversion           │
│                                                                                      │
│   BUILD vs BUY                                                                       │
│   ────────────                                                                      │
│   Build from scratch: 12+ weeks          Reuse existing: 5 weeks                    │
│   70% of WaitlistLab features already exist in MediaPoster                          │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Infrastructure Reuse Map

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                        WAITLISTLAB → MEDIAPOSTER MAPPING                             │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐ │
│  │                         100% REUSE (No Changes)                               │ │
│  ├───────────────────────────────────────────────────────────────────────────────┤ │
│  │                                                                               │ │
│  │  ┌─────────────────────┐     ┌─────────────────────────────────────────────┐ │ │
│  │  │  WAITLISTLAB NEED   │ ──► │  MEDIAPOSTER EXISTING                       │ │ │
│  │  └─────────────────────┘     └─────────────────────────────────────────────┘ │ │
│  │                                                                               │ │
│  │  Supabase Database      ──►  ✅ Already connected (same project)             │ │
│  │  OpenAI GPT-4           ──►  ✅ Already integrated (all models)              │ │
│  │  Remotion Rendering     ──►  ✅ media-pipeline /api/remotion/render         │ │
│  │  Rules Engine           ──►  ✅ Automation Center rules system               │ │
│  │  Event Architecture     ──►  ✅ Pub/Sub event bus exists                     │ │
│  │  Cron/Scheduler         ──►  ✅ Agent Framework scheduler                    │ │
│  │                                                                               │ │
│  └───────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐ │
│  │                         80% REUSE (Minor Extension)                           │ │
│  ├───────────────────────────────────────────────────────────────────────────────┤ │
│  │                                                                               │ │
│  │  Lead Scoring           ──►  ✅ FATE scoring + extend for lead tiers         │ │
│  │  AI Planner             ──►  ✅ Narrative Scheduler + extend for ads         │ │
│  │  Fatigue Detection      ──►  ✅ Analytics Feedback + extend for ad fatigue   │ │
│  │  Webhooks               ──►  ✅ Event handlers + add Meta webhook            │ │
│  │                                                                               │ │
│  └───────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐ │
│  │                         50% REUSE (Significant Extension)                     │ │
│  ├───────────────────────────────────────────────────────────────────────────────┤ │
│  │                                                                               │ │
│  │  Lead Forms             ──►  ⚠️ Community Inbox + add form builder           │ │
│  │  Email Sequences        ──►  ⚠️ DM Outreach + add Resend channel            │ │
│  │  Creative Factory       ──►  ⚠️ Remotion + add ad templates                  │ │
│  │                                                                               │ │
│  └───────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
│  ┌───────────────────────────────────────────────────────────────────────────────┐ │
│  │                         0% REUSE (New Build Required)                         │ │
│  ├───────────────────────────────────────────────────────────────────────────────┤ │
│  │                                                                               │ │
│  │  Meta Marketing API     ──►  ❌ New service (covered in PRD_META_ADS)        │ │
│  │  Resend Email           ──►  ❌ New integration                               │ │
│  │  Meta Conversions API   ──►  ❌ New integration                               │ │
│  │                                                                               │ │
│  └───────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                          MEDIAPOSTER + WAITLISTLAB UNIFIED PLATFORM                          │
├─────────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                              │
│  ╔═══════════════════════════════════════════════════════════════════════════════════════╗ │
│  ║                                   FRONTEND LAYER                                       ║ │
│  ╠═══════════════════════════════════════════════════════════════════════════════════════╣ │
│  ║                                                                                        ║ │
│  ║   ┌───────────────────────────────────────────────────────────────────────────────┐  ║ │
│  ║   │                       Next.js Dashboard (Port 5557)                           │  ║ │
│  ║   │                                                                               │  ║ │
│  ║   │  ┌─────────────────────────────────────────────────────────────────────────┐ │  ║ │
│  ║   │  │                    EXISTING MODULES                                      │ │  ║ │
│  ║   │  │                                                                          │ │  ║ │
│  ║   │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │ │  ║ │
│  ║   │  │  │ Content  │ │Automation│ │ Schedule │ │Analytics │ │  Narrative   │  │ │  ║ │
│  ║   │  │  │ Library  │ │  Center  │ │ Calendar │ │Dashboard │ │   Builder    │  │ │  ║ │
│  ║   │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │ │  ║ │
│  ║   │  └─────────────────────────────────────────────────────────────────────────┘ │  ║ │
│  ║   │                                                                               │  ║ │
│  ║   │  ┌─────────────────────────────────────────────────────────────────────────┐ │  ║ │
│  ║   │  │                    NEW WAITLISTLAB MODULES                               │ │  ║ │
│  ║   │  │                                                                          │ │  ║ │
│  ║   │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐  │ │  ║ │
│  ║   │  │  │   Ads    │ │  Lead    │ │ Waitlist │ │  Email   │ │  Landing     │  │ │  ║ │
│  ║   │  │  │Autopilot │ │  Forms   │ │   Mgmt   │ │Sequences │ │   Pages      │  │ │  ║ │
│  ║   │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────┘  │ │  ║ │
│  ║   │  └─────────────────────────────────────────────────────────────────────────┘ │  ║ │
│  ║   └───────────────────────────────────────────────────────────────────────────────┘  ║ │
│  ║                                                                                        ║ │
│  ╚════════════════════════════════════════════════════════════════════════════════════════╝ │
│                                            │                                                 │
│                                            ▼                                                 │
│  ╔═══════════════════════════════════════════════════════════════════════════════════════╗ │
│  ║                                   API LAYER                                            ║ │
│  ╠═══════════════════════════════════════════════════════════════════════════════════════╣ │
│  ║                                                                                        ║ │
│  ║   ┌───────────────────────────────────────────────────────────────────────────────┐  ║ │
│  ║   │                       FastAPI Backend (Port 5555)                             │  ║ │
│  ║   │                                                                               │  ║ │
│  ║   │  ┌─────────────────────────────┬─────────────────────────────────────────┐  │  ║ │
│  ║   │  │    EXISTING ENDPOINTS       │       NEW ENDPOINTS                      │  │  ║ │
│  ║   │  ├─────────────────────────────┼─────────────────────────────────────────┤  │  ║ │
│  ║   │  │                             │                                         │  │  ║ │
│  ║   │  │  /api/content/*             │  /api/ads-autopilot/*                   │  │  ║ │
│  ║   │  │  /api/automation/*     ◄────┼──── REUSES rules engine                 │  │  ║ │
│  ║   │  │  /api/narrative/*           │  /api/lead-forms/*                      │  │  ║ │
│  ║   │  │  /api/experiments/*         │  /api/waitlist/*                        │  │  ║ │
│  ║   │  │  /api/score/fate       ◄────┼──── REUSES for lead scoring             │  │  ║ │
│  ║   │  │  /api/dm/*             ◄────┼──── EXTENDS with email channel          │  │  ║ │
│  ║   │  │  /api/crm/*            ◄────┼──── REUSES for lead management          │  │  ║ │
│  ║   │  │  /api/analytics/*      ◄────┼──── EXTENDS with ad metrics             │  │  ║ │
│  ║   │  │                             │  /api/meta-ads/*                        │  │  ║ │
│  ║   │  │                             │  /api/email-sequences/*                 │  │  ║ │
│  ║   │  │                             │  /api/webhooks/meta/*                   │  │  ║ │
│  ║   │  │                             │                                         │  │  ║ │
│  ║   │  └─────────────────────────────┴─────────────────────────────────────────┘  │  ║ │
│  ║   └───────────────────────────────────────────────────────────────────────────────┘  ║ │
│  ║                                                                                        ║ │
│  ╚════════════════════════════════════════════════════════════════════════════════════════╝ │
│                                            │                                                 │
│           ┌────────────────────────────────┼────────────────────────────────┐               │
│           ▼                                ▼                                ▼               │
│  ╔═══════════════════════╗  ╔═══════════════════════════╗  ╔═══════════════════════════╗  │
│  ║   EXISTING SERVICES   ║  ║    EXTENDED SERVICES      ║  ║     NEW SERVICES          ║  │
│  ╠═══════════════════════╣  ╠═══════════════════════════╣  ╠═══════════════════════════╣  │
│  ║                       ║  ║                           ║  ║                           ║  │
│  ║  ┌─────────────────┐  ║  ║  ┌─────────────────────┐  ║  ║  ┌─────────────────────┐  ║  │
│  ║  │ media-pipeline  │  ║  ║  │  Lead Scoring       │  ║  ║  │  Meta Publisher     │  ║  │
│  ║  │   (6004)        │  ║  ║  │  (FATE + tiers)     │  ║  ║  │  (Marketing API)    │  ║  │
│  ║  │                 │  ║  ║  └─────────────────────┘  ║  ║  └─────────────────────┘  ║  │
│  ║  │ • Remotion ✅   │  ║  ║  ┌─────────────────────┐  ║  ║  ┌─────────────────────┐  ║  │
│  ║  │ • TTS ✅        │  ║  ║  │  Outreach Service   │  ║  ║  │  Resend Client      │  ║  │
│  ║  │ • Transcribe ✅ │  ║  ║  │  (DM + Email)       │  ║  ║  │  (Email delivery)   │  ║  │
│  ║  └─────────────────┘  ║  ║  └─────────────────────┘  ║  ║  └─────────────────────┘  ║  │
│  ║  ┌─────────────────┐  ║  ║  ┌─────────────────────┐  ║  ║  ┌─────────────────────┐  ║  │
│  ║  │content-intel    │  ║  ║  │  Rules Engine       │  ║  ║  │  CAPI Integration   │  ║  │
│  ║  │   (6006)        │  ║  ║  │  (+ ad conditions)  │  ║  ║  │  (Server tracking)  │  ║  │
│  ║  │                 │  ║  ║  └─────────────────────┘  ║  ║  └─────────────────────┘  ║  │
│  ║  │ • FATE Score ✅ │  ║  ║  ┌─────────────────────┐  ║  ║  ┌─────────────────────┐  ║  │
│  ║  │ • AI Analysis ✅│  ║  ║  │  Analytics          │  ║  ║  │  Creative Factory   │  ║  │
│  ║  │ • CRM ✅        │  ║  ║  │  (+ ad performance) │  ║  ║  │  (Ad templates)     │  ║  │
│  ║  └─────────────────┘  ║  ║  └─────────────────────┘  ║  ║  └─────────────────────┘  ║  │
│  ║                       ║  ║                           ║  ║                           ║  │
│  ╚═══════════════════════╝  ╚═══════════════════════════╝  ╚═══════════════════════════╝  │
│                                            │                                                 │
│                                            ▼                                                 │
│  ╔═══════════════════════════════════════════════════════════════════════════════════════╗ │
│  ║                                 EXTERNAL SERVICES                                      ║ │
│  ╠═══════════════════════════════════════════════════════════════════════════════════════╣ │
│  ║                                                                                        ║ │
│  ║  ┌────────────────────────────────────────────────────────────────────────────────┐  ║ │
│  ║  │                          EXISTING (Already Connected)                          │  ║ │
│  ║  │                                                                                │  ║ │
│  ║  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │  ║ │
│  ║  │  │ Supabase │ │  OpenAI  │ │  Groq    │ │Anthropic │ │      Blotato         │ │  ║ │
│  ║  │  │ Postgres │ │  GPT-4   │ │  LLaMA   │ │  Claude  │ │   Social Publish     │ │  ║ │
│  ║  │  │ Auth     │ │  Whisper │ │          │ │          │ │   22 accounts        │ │  ║ │
│  ║  │  │ Storage  │ │  Vision  │ │          │ │          │ │                      │ │  ║ │
│  ║  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────────────────┘ │  ║ │
│  ║  └────────────────────────────────────────────────────────────────────────────────┘  ║ │
│  ║                                                                                        ║ │
│  ║  ┌────────────────────────────────────────────────────────────────────────────────┐  ║ │
│  ║  │                          NEW (To Be Connected)                                 │  ║ │
│  ║  │                                                                                │  ║ │
│  ║  │  ┌──────────────────────────┐ ┌──────────────────────────────────────────────┐│  ║ │
│  ║  │  │     Meta/Facebook        │ │               Resend                         ││  ║ │
│  ║  │  │                          │ │                                              ││  ║ │
│  ║  │  │  • Marketing API v21.0   │ │  • Transactional emails                     ││  ║ │
│  ║  │  │  • Graph API             │ │  • Email sequences                          ││  ║ │
│  ║  │  │  • Conversions API       │ │  • Delivery webhooks                        ││  ║ │
│  ║  │  │  • Lead Ads webhooks     │ │  • Templates                                ││  ║ │
│  ║  │  │  • Instagram Business    │ │                                              ││  ║ │
│  ║  │  └──────────────────────────┘ └──────────────────────────────────────────────┘│  ║ │
│  ║  └────────────────────────────────────────────────────────────────────────────────┘  ║ │
│  ║                                                                                        ║ │
│  ╚════════════════════════════════════════════════════════════════════════════════════════╝ │
│                                                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema (Extends Existing)

```sql
-- Migration: 20260201_waitlistlab_integration.sql

-- ═══════════════════════════════════════════════════════════════
-- OFFERS (Products/Services for ads and landing pages)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    slug VARCHAR(100) UNIQUE, -- URL-friendly identifier
    
    -- Pricing
    price DECIMAL,
    currency VARCHAR(3) DEFAULT 'USD',
    price_display VARCHAR(100), -- "Free", "$97", "$997/year"
    
    -- Landing page
    landing_page_url TEXT,
    landing_page_template VARCHAR(50), -- waitlist, sales, lead_magnet
    
    -- Tracking
    pixel_id VARCHAR(50),
    conversion_event VARCHAR(100) DEFAULT 'Lead',
    
    -- Targets
    target_cpa DECIMAL,
    target_roas DECIMAL,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════
-- LEAD FORMS (Extends community inbox concept)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE lead_forms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    offer_id UUID REFERENCES offers(id),
    
    -- Form config
    name VARCHAR(255) NOT NULL,
    form_type VARCHAR(50) DEFAULT 'waitlist', -- waitlist, lead_magnet, application
    
    -- Questions (JSON array)
    questions JSONB NOT NULL DEFAULT '[]',
    -- Example:
    -- [
    --   {"id": "email", "type": "email", "label": "Email", "required": true},
    --   {"id": "name", "type": "text", "label": "Full Name", "required": true},
    --   {"id": "company", "type": "text", "label": "Company", "required": false},
    --   {"id": "budget", "type": "select", "label": "Budget", "options": ["<$1k", "$1k-$5k", "$5k+"]}
    -- ]
    
    -- Scoring rules
    scoring_rules JSONB,
    -- Example:
    -- {
    --   "budget": {"$5k+": 30, "$1k-$5k": 20, "<$1k": 10},
    --   "company_size": {"enterprise": 40, "mid-market": 25, "startup": 15}
    -- }
    
    -- Appearance
    theme JSONB DEFAULT '{}',
    thank_you_message TEXT,
    redirect_url TEXT,
    
    -- Meta Lead Ads integration
    meta_form_id VARCHAR(50),
    
    -- Stats
    submission_count INTEGER DEFAULT 0,
    conversion_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════
-- LEADS (Unified lead table, extends existing CRM)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Source
    form_id UUID REFERENCES lead_forms(id),
    offer_id UUID REFERENCES offers(id),
    source VARCHAR(50), -- form, meta_lead_ad, manual, api
    source_meta_id VARCHAR(100), -- Meta's lead ID if from Lead Ad
    
    -- Contact info
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    phone VARCHAR(50),
    
    -- Form responses (full data)
    form_data JSONB,
    
    -- Scoring
    lead_score INTEGER DEFAULT 0, -- 0-100
    lead_tier VARCHAR(20), -- hot, warm, cold
    scoring_breakdown JSONB,
    -- Example:
    -- {
    --   "form_score": 45,
    --   "engagement_score": 20,
    --   "fit_score": 35
    -- }
    
    -- FATE integration (reuses existing scoring)
    fate_score JSONB,
    -- From content-intelligence /api/score/fate
    
    -- Tags
    tags VARCHAR(100)[],
    
    -- Status pipeline
    status VARCHAR(50) DEFAULT 'new', -- new, contacted, qualified, converted, lost
    
    -- Conversion tracking
    converted_at TIMESTAMPTZ,
    conversion_value DECIMAL,
    
    -- Link to existing CRM contact if exists
    dm_contact_id UUID, -- REFERENCES dm_contacts(id) from DM system
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(email, offer_id)
);

-- ═══════════════════════════════════════════════════════════════
-- EMAIL SEQUENCES (Extends DM outreach with email channel)
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE email_sequences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    offer_id UUID REFERENCES offers(id),
    
    name VARCHAR(255) NOT NULL,
    description TEXT,
    trigger VARCHAR(50) NOT NULL, -- form_submit, lead_tier_change, manual
    
    -- Timing
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE email_sequence_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id UUID REFERENCES email_sequences(id) ON DELETE CASCADE,
    
    -- Order
    step_number INTEGER NOT NULL,
    
    -- Timing
    delay_hours INTEGER DEFAULT 0, -- Hours after previous step
    send_at_time TIME, -- Optional specific time
    skip_weekends BOOLEAN DEFAULT FALSE,
    
    -- Content
    subject VARCHAR(255) NOT NULL,
    body_html TEXT NOT NULL,
    body_text TEXT,
    
    -- Personalization (variables)
    variables JSONB, -- ["first_name", "company", "offer_name"]
    
    -- Conditions (skip if)
    skip_conditions JSONB,
    -- Example: {"lead_status": "converted"}
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE email_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
    sequence_step_id UUID REFERENCES email_sequence_steps(id),
    
    -- Scheduling
    scheduled_at TIMESTAMPTZ NOT NULL,
    
    -- Content (rendered)
    to_email VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    body_html TEXT NOT NULL,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending', -- pending, sent, failed, skipped
    
    -- Resend tracking
    resend_email_id VARCHAR(100),
    sent_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    clicked_at TIMESTAMPTZ,
    bounced BOOLEAN DEFAULT FALSE,
    
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ═══════════════════════════════════════════════════════════════
-- META ADS (Condensed from PRD_META_ADS_AUTOPILOT)
-- ═══════════════════════════════════════════════════════════════

-- Reference: See PRD_META_ADS_AUTOPILOT.md for full schema
-- Tables: meta_objects, performance_daily, autopilot_rules, autopilot_actions

-- ═══════════════════════════════════════════════════════════════
-- INDEXES
-- ═══════════════════════════════════════════════════════════════

CREATE INDEX idx_leads_email ON leads(email);
CREATE INDEX idx_leads_offer ON leads(offer_id);
CREATE INDEX idx_leads_tier ON leads(lead_tier);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_created ON leads(created_at DESC);

CREATE INDEX idx_email_queue_scheduled ON email_queue(scheduled_at);
CREATE INDEX idx_email_queue_status ON email_queue(status);
CREATE INDEX idx_email_queue_lead ON email_queue(lead_id);

CREATE INDEX idx_lead_forms_offer ON lead_forms(offer_id);
```

---

## API Endpoints

### Lead Forms

```yaml
# GET /api/lead-forms
# List all forms
Response:
  forms: LeadForm[]

# POST /api/lead-forms
# Create new form
Request:
  offer_id: uuid
  name: string
  form_type: string
  questions: Question[]
  scoring_rules: object
Response:
  form: LeadForm

# GET /api/lead-forms/{id}
# Get form with stats
Response:
  form: LeadForm
  stats: {submissions, conversions, avg_score}

# POST /api/lead-forms/{id}/duplicate
# Duplicate form
Response:
  form: LeadForm

# PUT /api/lead-forms/{id}
# Update form

# DELETE /api/lead-forms/{id}
# Delete form
```

### Waitlist / Leads

```yaml
# POST /api/waitlist
# Submit to waitlist (public endpoint)
Request:
  form_id: uuid
  data: {email, name, ...responses}
Response:
  lead_id: uuid
  score: number
  tier: string
  position: number (optional)

# GET /api/waitlist/leads
# List leads with filters
Query:
  offer_id: uuid
  tier: string
  status: string
  search: string
  sort: string
Response:
  leads: Lead[]
  stats: {total, by_tier, by_status}

# GET /api/waitlist/leads/{id}
# Get lead detail
Response:
  lead: Lead
  emails_sent: Email[]
  activity: Activity[]

# PUT /api/waitlist/leads/{id}/status
# Update lead status
Request:
  status: string
  note: string

# POST /api/waitlist/leads/{id}/score
# Re-score lead (calls FATE)
Response:
  lead: Lead
  scoring_breakdown: object
```

### Email Sequences

```yaml
# GET /api/email-sequences
# List sequences
Response:
  sequences: EmailSequence[]

# POST /api/email-sequences
# Create sequence
Request:
  offer_id: uuid
  name: string
  trigger: string
  steps: SequenceStep[]
Response:
  sequence: EmailSequence

# GET /api/email-sequences/{id}
# Get sequence with steps
Response:
  sequence: EmailSequence
  steps: SequenceStep[]
  stats: {sent, opened, clicked}

# POST /api/email-sequences/{id}/activate
# Activate sequence

# POST /api/email-sequences/{id}/pause
# Pause sequence

# GET /api/email-sequences/queue
# View email queue
Query:
  status: string
Response:
  emails: QueuedEmail[]

# POST /api/email-sequences/process
# Process email queue (cron endpoint)
```

### Webhooks

```yaml
# POST /api/webhooks/meta/leadgen
# Receive Meta Lead Ad submissions
Request: (from Meta)
  leadgen_id: string
  form_id: string
  page_id: string
Response:
  received: true

# POST /api/webhooks/resend
# Receive email delivery events
Request: (from Resend)
  type: "email.sent" | "email.delivered" | "email.opened" | "email.clicked" | "email.bounced"
  data: {...}
Response:
  received: true
```

---

## Service Integration Details

### 1. Lead Scoring (Reuses FATE)

```python
# Backend/services/waitlistlab/lead_scoring.py

class LeadScoringService:
    """Score leads using FATE + custom form rules."""
    
    def __init__(self):
        self.fate_client = MicroservicesClient()  # Existing!
    
    async def score_lead(
        self,
        lead: Lead,
        form: LeadForm
    ) -> LeadScore:
        """Calculate lead score combining FATE + form rules."""
        
        # 1. Get FATE score from existing service
        fate_score = await self.fate_client.score_fate({
            "content": lead.form_data.get("message", ""),
            "context": {
                "email": lead.email,
                "source": lead.source
            }
        })
        
        # 2. Apply form-specific scoring rules
        form_score = self.apply_form_rules(lead.form_data, form.scoring_rules)
        
        # 3. Calculate engagement score (if existing DM contact)
        engagement_score = 0
        if lead.dm_contact_id:
            # Reuse existing CRM relationship score
            crm_score = await self.fate_client.get_relationship_score(
                lead.dm_contact_id
            )
            engagement_score = crm_score.get("score", 0) * 0.3
        
        # 4. Combine scores
        total_score = (
            form_score * 0.5 +
            fate_score.get("overall", 0) * 0.3 +
            engagement_score * 0.2
        )
        
        # 5. Assign tier
        tier = self.score_to_tier(total_score)
        
        return LeadScore(
            score=int(total_score),
            tier=tier,
            breakdown={
                "form_score": form_score,
                "fate_score": fate_score.get("overall", 0),
                "engagement_score": engagement_score
            }
        )
    
    def score_to_tier(self, score: int) -> str:
        if score >= 70: return "hot"
        if score >= 40: return "warm"
        return "cold"
```

### 2. Email Sequences (Extends DM Outreach)

```python
# Backend/services/waitlistlab/email_sequences.py

class EmailSequenceService:
    """Email sequences using Resend, extends DM outreach patterns."""
    
    def __init__(self):
        self.resend = ResendClient()
        self.dm_outreach = DMOutreachService()  # Existing!
    
    async def trigger_sequence(
        self,
        lead: Lead,
        sequence: EmailSequence
    ):
        """Start email sequence for lead."""
        
        for step in sequence.steps:
            # Calculate send time
            send_at = self.calculate_send_time(
                base_time=datetime.now(),
                delay_hours=step.delay_hours,
                send_at_time=step.send_at_time,
                skip_weekends=step.skip_weekends
            )
            
            # Check skip conditions
            if self.should_skip(lead, step.skip_conditions):
                continue
            
            # Render email content
            rendered = self.render_template(
                subject=step.subject,
                body=step.body_html,
                variables=self.get_variables(lead)
            )
            
            # Queue email
            await self.queue_email(
                lead_id=lead.id,
                step_id=step.id,
                scheduled_at=send_at,
                to_email=lead.email,
                subject=rendered["subject"],
                body_html=rendered["body"]
            )
    
    async def process_queue(self):
        """Process due emails (cron job)."""
        
        due_emails = await self.get_due_emails()
        
        for email in due_emails:
            try:
                # Send via Resend
                result = await self.resend.send(
                    to=email.to_email,
                    subject=email.subject,
                    html=email.body_html
                )
                
                # Update status
                email.status = "sent"
                email.resend_email_id = result["id"]
                email.sent_at = datetime.now()
                
                # Also log to DM outreach for unified tracking
                await self.dm_outreach.log_touch(
                    contact_id=email.lead.dm_contact_id,
                    channel="email",
                    message_preview=email.subject
                )
                
            except Exception as e:
                email.status = "failed"
                email.error_message = str(e)
                email.retry_count += 1
            
            await self.repo.update(email)
```

### 3. Creative Factory (Extends Remotion)

```python
# Backend/services/waitlistlab/creative_factory.py

class CreativeFactory:
    """Generate ad creatives using existing Remotion integration."""
    
    def __init__(self):
        self.remotion = MicroservicesClient()  # Existing!
        self.ai = OpenAIClient()  # Existing!
    
    async def generate_ad_creatives(
        self,
        offer: Offer,
        source_content_id: UUID = None,
        count: int = 10
    ) -> List[AdCreative]:
        """Generate ad creative variations."""
        
        # 1. Get hooks/CTAs from AI (existing service)
        hooks = await self.ai.generate_hooks(offer.description, count=count)
        ctas = await self.ai.generate_ctas(offer.name)
        
        # 2. Generate creatives
        creatives = []
        for i, hook in enumerate(hooks):
            # Use existing Remotion render endpoint
            render_result = await self.remotion.render_remotion(
                brief={
                    "title": offer.name,
                    "hook": hook,
                    "cta": ctas[i % len(ctas)],
                    "landing_url": offer.landing_page_url
                },
                template="AdCreative"
            )
            
            creatives.append(AdCreative(
                offer_id=offer.id,
                hook=hook,
                cta=ctas[i % len(ctas)],
                video_path=render_result["output_path"]
            ))
        
        return creatives
```

### 4. Rules Engine Extension

```python
# Backend/services/waitlistlab/ads_rules.py

class AdsRulesEngine:
    """Extend existing rules engine for ad automation."""
    
    def __init__(self):
        self.rules_engine = AutomationRulesEngine()  # Existing!
    
    # Register new rule types for ads
    NEW_RULE_TYPES = {
        "pause_ad": self.action_pause_ad,
        "enable_ad": self.action_enable_ad,
        "increase_budget": self.action_increase_budget,
        "decrease_budget": self.action_decrease_budget,
        "create_variant": self.action_create_variant,
        "notify_fatigue": self.action_notify_fatigue,
    }
    
    # Register new condition types
    NEW_CONDITIONS = {
        "ctr": lambda obj, op, val: compare(obj.ctr, op, val),
        "cpc": lambda obj, op, val: compare(obj.cpc, op, val),
        "cpm": lambda obj, op, val: compare(obj.cpm, op, val),
        "roas": lambda obj, op, val: compare(obj.roas, op, val),
        "spend": lambda obj, op, val: compare(obj.spend, op, val),
        "frequency": lambda obj, op, val: compare(obj.frequency, op, val),
        "hook_rate": lambda obj, op, val: compare(obj.hook_rate, op, val),
    }
    
    async def register_extensions(self):
        """Register new rule types with existing engine."""
        for rule_type, action in self.NEW_RULE_TYPES.items():
            self.rules_engine.register_action(rule_type, action)
        
        for condition, evaluator in self.NEW_CONDITIONS.items():
            self.rules_engine.register_condition(condition, evaluator)
```

---

## Implementation Phases

### Phase 1: Database & Lead Forms (Week 1)
| Task | Effort | Reuses |
|------|--------|--------|
| Database migration | 4h | Supabase ✅ |
| Lead form CRUD API | 6h | - |
| Lead scoring integration | 4h | FATE ✅ |
| Form builder UI | 12h | Dashboard ✅ |
| Public form submission | 4h | - |

### Phase 2: Email Integration (Week 2)
| Task | Effort | Reuses |
|------|--------|--------|
| Resend client | 4h | - |
| Email sequence service | 8h | DM Outreach ✅ |
| Queue processor | 4h | Agent Framework ✅ |
| Webhook handlers | 4h | Event Bus ✅ |
| Email UI | 12h | Dashboard ✅ |

### Phase 3: Meta Integration (Weeks 3-4)
| Task | Effort | Reuses |
|------|--------|--------|
| Meta API client | 8h | - |
| Lead Ads webhook | 4h | Event Bus ✅ |
| Campaign management | 12h | - |
| Insights fetcher | 8h | - |
| Creative factory | 6h | Remotion ✅ |
| Ads autopilot UI | 12h | Dashboard ✅ |

### Phase 4: Rules & Analytics (Week 5)
| Task | Effort | Reuses |
|------|--------|--------|
| Rules engine extension | 6h | Automation Center ✅ |
| Fatigue detector | 4h | Analytics Feedback ✅ |
| AI insights | 6h | OpenAI ✅ |
| Unified analytics | 8h | Analytics Dashboard ✅ |
| Testing & polish | 8h | - |

---

## Files to Create

```
Backend/services/waitlistlab/
├── __init__.py
├── lead_scoring.py          # Extends FATE
├── lead_forms.py            # Form management
├── email_sequences.py       # Extends DM Outreach
├── creative_factory.py      # Extends Remotion
├── ads_rules.py             # Extends Automation
├── webhooks.py              # Meta + Resend handlers
└── models.py

Backend/services/email/
├── __init__.py
├── resend_client.py         # New
├── template_renderer.py     # New
└── queue_processor.py       # New

Backend/api/endpoints/
├── lead_forms.py            # New
├── waitlist.py              # New
├── email_sequences.py       # New
└── webhooks_meta.py         # New

dashboard/app/(dashboard)/waitlist/
├── page.tsx                 # Leads list
├── leads/[id]/page.tsx      # Lead detail
├── forms/page.tsx           # Form builder
├── forms/[id]/page.tsx      # Form editor
├── emails/page.tsx          # Email sequences
└── components/
    ├── LeadTable.tsx
    ├── LeadScoreCard.tsx
    ├── FormBuilder.tsx
    ├── EmailSequenceEditor.tsx
    └── LeadTierBadge.tsx
```

---

## Environment Variables

```bash
# ═══════════════════════════════════════════════════════════════
# EXISTING (Already configured in MediaPoster)
# ═══════════════════════════════════════════════════════════════
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=xxx
OPENAI_API_KEY=sk-xxx

# ═══════════════════════════════════════════════════════════════
# NEW (Add for WaitlistLab features)
# ═══════════════════════════════════════════════════════════════

# Resend (Email)
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL=hello@yourdomain.com
RESEND_WEBHOOK_SECRET=whsec_xxx

# Meta/Facebook
META_APP_ID=xxx
META_APP_SECRET=xxx
META_ACCESS_TOKEN=xxx
META_AD_ACCOUNT_ID=act_xxx
META_PIXEL_ID=xxx
META_PAGE_ID=xxx
META_WEBHOOK_VERIFY_TOKEN=xxx

# Cron
CRON_SECRET=xxx
```

---

## Effort Summary

| Category | Build from Scratch | With MediaPoster Reuse | Savings |
|----------|-------------------|------------------------|---------|
| Database | 2 weeks | 2 days | 85% |
| AI Services | 3 weeks | 0 (already done) | 100% |
| Video Rendering | 2 weeks | 0 (already done) | 100% |
| Rules Engine | 2 weeks | 2 days | 85% |
| Lead Scoring | 1 week | 1 day | 85% |
| Email Sequences | 1 week | 1 week | 0% |
| Meta API | 2 weeks | 2 weeks | 0% |
| Dashboard UI | 2 weeks | 1 week | 50% |
| **Total** | **12+ weeks** | **5 weeks** | **58%** |

---

## Success Criteria

- [ ] Lead forms capture submissions
- [ ] Lead scoring uses FATE system
- [ ] Email sequences trigger on form submit
- [ ] Meta Lead Ads webhook works
- [ ] Remotion renders ad creatives
- [ ] Rules engine manages ads
- [ ] Unified dashboard shows all data
- [ ] <2 hour to deploy new offer

---

*Document created: February 1, 2026*
