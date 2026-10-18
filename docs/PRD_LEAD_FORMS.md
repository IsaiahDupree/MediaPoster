# PRD: Lead Forms

**Version:** 1.0  
**Date:** February 1, 2026  
**Status:** Ready for Implementation  
**Effort:** 1-2 weeks  
**Priority:** 🟡 High

---

## Executive Summary

Build a lead form system (WaitlistLab-style) that captures leads, scores them using FATE, and triggers automated follow-up sequences via DM or email.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       LEAD FORMS SYSTEM                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                    FORM BUILDER                          │  │
│   │                                                          │  │
│   │  Questions:                    Scoring Rules:            │  │
│   │  ┌────────────────────┐       ┌────────────────────┐    │  │
│   │  │ Email (required)   │       │ Budget $5k+ = +30  │    │  │
│   │  │ Name               │       │ Company size = +20 │    │  │
│   │  │ Company            │       │ Timeline <1mo = +25│    │  │
│   │  │ Budget [dropdown]  │       │                    │    │  │
│   │  │ Timeline [select]  │       └────────────────────┘    │  │
│   │  └────────────────────┘                                  │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                  SUBMISSION HANDLER                      │  │
│   │                                                          │  │
│   │  1. Validate form data                                   │  │
│   │  2. Create lead record                                   │  │
│   │  3. Calculate form score + FATE score                    │  │
│   │  4. Assign tier (hot/warm/cold)                         │  │
│   │  5. Trigger email sequence                               │  │
│   │  6. Notify via webhook (optional)                        │  │
│   │                                                          │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│   ┌────────────────┐ ┌────────────────┐ ┌────────────────┐     │
│   │  LEAD SCORING  │ │ EMAIL SEQUENCE │ │   ANALYTICS    │     │
│   │  (FATE reuse)  │ │  (Resend)      │ │   Dashboard    │     │
│   └────────────────┘ └────────────────┘ └────────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

```sql
-- Lead forms
CREATE TABLE lead_forms (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE,
    form_type VARCHAR(50) DEFAULT 'waitlist',
    
    -- Questions (JSON array)
    questions JSONB NOT NULL DEFAULT '[]',
    -- [{id, type, label, required, options}]
    
    -- Scoring rules
    scoring_rules JSONB,
    -- {field: {value: points}}
    
    -- Appearance
    theme JSONB DEFAULT '{}',
    thank_you_message TEXT,
    redirect_url TEXT,
    
    -- Automation
    email_sequence_id UUID,
    webhook_url TEXT,
    
    -- Stats
    submission_count INTEGER DEFAULT 0,
    conversion_count INTEGER DEFAULT 0,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Leads
CREATE TABLE leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    form_id UUID REFERENCES lead_forms(id),
    
    -- Contact
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    phone VARCHAR(50),
    
    -- Form responses
    form_data JSONB,
    
    -- Scoring
    lead_score INTEGER DEFAULT 0,
    lead_tier VARCHAR(20), -- hot, warm, cold
    scoring_breakdown JSONB,
    fate_score JSONB,
    
    -- Status
    status VARCHAR(50) DEFAULT 'new',
    -- new, contacted, qualified, converted, lost
    
    -- Conversion
    converted_at TIMESTAMPTZ,
    conversion_value DECIMAL,
    
    -- Tags
    tags VARCHAR(100)[],
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(email, form_id)
);

-- Indexes
CREATE INDEX idx_leads_form ON leads(form_id);
CREATE INDEX idx_leads_tier ON leads(lead_tier);
CREATE INDEX idx_leads_status ON leads(status);
CREATE INDEX idx_leads_email ON leads(email);
```

---

## API Endpoints

```yaml
# Forms
GET    /api/lead-forms              → List forms
POST   /api/lead-forms              → Create form
GET    /api/lead-forms/{id}         → Get form with stats
PUT    /api/lead-forms/{id}         → Update form
DELETE /api/lead-forms/{id}         → Delete form
POST   /api/lead-forms/{id}/duplicate → Clone form

# Public submission
POST   /api/waitlist                → Submit to waitlist (public)
GET    /api/waitlist/position/{id}  → Get waitlist position

# Leads
GET    /api/leads                   → List leads (with filters)
GET    /api/leads/{id}              → Get lead detail
PUT    /api/leads/{id}/status       → Update status
POST   /api/leads/{id}/score        → Re-score lead
DELETE /api/leads/{id}              → Delete lead

# Bulk operations
POST   /api/leads/export            → Export to CSV
POST   /api/leads/import            → Import from CSV
POST   /api/leads/tag               → Bulk add tags
```

---

## Lead Scoring Integration

```python
# Reuses existing FATE scoring from content-intelligence

class LeadScoringService:
    async def score_lead(self, lead, form):
        # 1. Apply form-specific rules
        form_score = self.apply_rules(lead.form_data, form.scoring_rules)
        
        # 2. Get FATE score (existing service)
        fate_response = await self.microservices.score_fate({
            "content": lead.form_data.get("message", ""),
            "context": {"email": lead.email}
        })
        
        # 3. Combine scores
        total = form_score * 0.6 + fate_response["overall"] * 0.4
        
        # 4. Assign tier
        tier = "hot" if total >= 70 else "warm" if total >= 40 else "cold"
        
        return {"score": total, "tier": tier}
```

---

## Form Builder UI

```
┌─────────────────────────────────────────────────────────────┐
│  Create Lead Form                              [Preview] [Save]│
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Form Name: [Waitlist Signup                    ]           │
│  Slug: /waitlist/[waitlist-signup              ]            │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  QUESTIONS                              [+ Add Field] │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  ≡ Email *           [email]    [Required ✓]        │   │
│  │  ≡ Full Name         [text]     [Required ✓]        │   │
│  │  ≡ Company           [text]     [Required ○]        │   │
│  │  ≡ Budget            [select]   [Required ○]        │   │
│  │     Options: <$1k, $1k-$5k, $5k+                    │   │
│  │  ≡ How did you hear  [text]     [Required ○]        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  SCORING RULES                                       │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  Budget:                                            │   │
│  │    $5k+     = [30] points                          │   │
│  │    $1k-$5k  = [20] points                          │   │
│  │    <$1k     = [10] points                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  AUTOMATION                                          │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │  Email Sequence: [Welcome Series          ▼]        │   │
│  │  Webhook URL:    [https://...            ]          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation: 1-2 Weeks

| Phase | Tasks | Effort |
|-------|-------|--------|
| **Days 1-3** | Database, form CRUD API, submission handler | 12h |
| **Days 4-6** | Lead scoring integration, tier assignment | 8h |
| **Days 7-9** | Form builder UI, lead management UI | 16h |
| **Days 10-12** | Email sequence triggers, webhooks, testing | 10h |

---

## Files to Create

```
Backend/services/lead_forms/
├── __init__.py
├── form_service.py
├── submission_handler.py
├── scoring_service.py
└── models.py

Backend/api/endpoints/lead_forms.py
Backend/api/endpoints/leads.py

dashboard/app/(dashboard)/leads/
├── page.tsx                 # Lead list
├── [id]/page.tsx            # Lead detail
├── forms/page.tsx           # Form list
├── forms/new/page.tsx       # Form builder
├── forms/[id]/page.tsx      # Edit form
└── components/
    ├── FormBuilder.tsx
    ├── QuestionEditor.tsx
    ├── ScoringRules.tsx
    ├── LeadTable.tsx
    ├── LeadScoreCard.tsx
    └── TierBadge.tsx
```

---

## Success Criteria

- [ ] Create forms with custom questions
- [ ] Public submission endpoint works
- [ ] Leads scored using FATE + custom rules
- [ ] Tiers assigned automatically
- [ ] Email sequences trigger on submit
- [ ] Lead management UI functional

---

*Document created: February 1, 2026*
