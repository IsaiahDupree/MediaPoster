# PRD: Email Sequences (Resend Integration)

**Version:** 1.0  
**Date:** February 1, 2026  
**Status:** Ready for Implementation  
**Track:** T4 Extension - Outreach Channels  
**Effort:** 1-2 weeks  
**Priority:** 🟡 High

---

## Executive Summary

Add email as an outreach channel alongside existing DM automation. Integrate Resend for reliable email delivery, enable automated sequences triggered by events, and unify email + DM in a single outreach dashboard.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           EMAIL SEQUENCES SYSTEM                                     │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                         TRIGGER LAYER                                        │   │
│  │                                                                              │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐   │   │
│  │  │ Form Submit │ │ Lead Tier   │ │  Schedule   │ │    Manual           │   │   │
│  │  │   Event     │ │   Change    │ │   Trigger   │ │    Trigger          │   │   │
│  │  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────────┬──────────┘   │   │
│  │         └───────────────┴───────────────┴───────────────────┘               │   │
│  │                                    │                                         │   │
│  └────────────────────────────────────┼─────────────────────────────────────────┘   │
│                                       ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                       SEQUENCE ENGINE                                        │   │
│  │                                                                              │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │  Sequence: "Welcome Series"                                          │   │   │
│  │  │                                                                      │   │   │
│  │  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐          │   │   │
│  │  │  │ Email 1 │───▶│ Wait    │───▶│ Email 2 │───▶│ Wait    │───▶ ...  │   │   │
│  │  │  │ Welcome │    │ 1 day   │    │ Value   │    │ 2 days  │          │   │   │
│  │  │  └─────────┘    └─────────┘    └─────────┘    └─────────┘          │   │   │
│  │  │                                                                      │   │   │
│  │  │  Conditions:                                                         │   │   │
│  │  │  • Skip if lead converted                                           │   │   │
│  │  │  • Skip weekends (optional)                                         │   │   │
│  │  │  • Stop if unsubscribed                                             │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                              │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                              │
│                                       ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                       EMAIL QUEUE                                            │   │
│  │                                                                              │   │
│  │  ┌─────────────────────────────────────────────────────────────────────┐   │   │
│  │  │  ID  │ Lead      │ Subject          │ Scheduled     │ Status       │   │   │
│  │  ├──────┼───────────┼──────────────────┼───────────────┼──────────────┤   │   │
│  │  │  1   │ john@...  │ Welcome to...    │ 2026-02-01    │ ⏳ pending   │   │   │
│  │  │  2   │ jane@...  │ Here's your...   │ 2026-02-02    │ ⏳ pending   │   │   │
│  │  │  3   │ bob@...   │ Quick tip...     │ 2026-02-01    │ ✅ sent      │   │   │
│  │  └─────────────────────────────────────────────────────────────────────┘   │   │
│  │                                                                              │   │
│  │  Processed by cron every 5 minutes                                          │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                              │
│                                       ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                       RESEND CLIENT                                          │   │
│  │                                                                              │   │
│  │  ┌───────────────────────────────────────────────────────────────────────┐ │   │
│  │  │                                                                       │ │   │
│  │  │   API: https://api.resend.com/emails                                 │ │   │
│  │  │                                                                       │ │   │
│  │  │   POST /emails                                                       │ │   │
│  │  │   {                                                                  │ │   │
│  │  │     "from": "hello@yourdomain.com",                                 │ │   │
│  │  │     "to": "recipient@example.com",                                  │ │   │
│  │  │     "subject": "Welcome!",                                          │ │   │
│  │  │     "html": "<p>Hello {{first_name}}...</p>"                        │ │   │
│  │  │   }                                                                  │ │   │
│  │  │                                                                       │ │   │
│  │  │   Features:                                                          │ │   │
│  │  │   • Delivery tracking                                                │ │   │
│  │  │   • Open tracking                                                    │ │   │
│  │  │   • Click tracking                                                   │ │   │
│  │  │   • Bounce handling                                                  │ │   │
│  │  │                                                                       │ │   │
│  │  └───────────────────────────────────────────────────────────────────────┘ │   │
│  │                                                                              │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                              │
│                                       ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                       WEBHOOK RECEIVER                                       │   │
│  │                                                                              │   │
│  │  POST /api/webhooks/resend                                                   │   │
│  │                                                                              │   │
│  │  Events received:                                                            │   │
│  │  • email.sent       → Update status to 'sent'                               │   │
│  │  • email.delivered  → Update status to 'delivered'                          │   │
│  │  • email.opened     → Record open timestamp, trigger analytics              │   │
│  │  • email.clicked    → Record click, track link clicked                      │   │
│  │  • email.bounced    → Mark lead as invalid email                            │   │
│  │  • email.complained → Unsubscribe lead                                      │   │
│  │                                                                              │   │
│  └──────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Integration with Existing Systems

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                    UNIFIED OUTREACH SYSTEM                                           │
├─────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                    DM OUTREACH (EXISTING)                                    │   │
│  │                                                                              │   │
│  │  Channels: Instagram DM, Twitter DM, LinkedIn DM                            │   │
│  │  Delivery: Safari Automation                                                 │   │
│  │  Features: Touch cadences, 3:1 rule, relationship scoring                   │   │
│  │                                                                              │   │
│  └───────────────────────────────────┬─────────────────────────────────────────┘   │
│                                      │                                              │
│                                      │  MERGE                                       │
│                                      │                                              │
│  ┌───────────────────────────────────▼─────────────────────────────────────────┐   │
│  │                    EMAIL OUTREACH (NEW)                                      │   │
│  │                                                                              │   │
│  │  Channel: Email                                                              │   │
│  │  Delivery: Resend API                                                        │   │
│  │  Features: Sequences, templates, tracking                                    │   │
│  │                                                                              │   │
│  └───────────────────────────────────┬─────────────────────────────────────────┘   │
│                                      │                                              │
│                                      ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────────────┐   │
│  │                    UNIFIED OUTREACH SERVICE                                  │   │
│  │                                                                              │   │
│  │  class UnifiedOutreachService:                                              │   │
│  │      dm_service: DMOutreachService      # Existing                          │   │
│  │      email_service: EmailSequenceService # New                              │   │
│  │                                                                              │   │
│  │      async def send_touch(contact, channel, message):                       │   │
│  │          if channel == "email":                                             │   │
│  │              return await self.email_service.send(...)                      │   │
│  │          else:                                                              │   │
│  │              return await self.dm_service.send(...)                         │   │
│  │                                                                              │   │
│  │      async def get_all_touches(contact_id):                                 │   │
│  │          dm_touches = await self.dm_service.get_touches(...)               │   │
│  │          email_touches = await self.email_service.get_emails(...)          │   │
│  │          return merge_and_sort(dm_touches, email_touches)                   │   │
│  │                                                                              │   │
│  └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema

```sql
-- Migration: 20260201_email_sequences.sql

-- Email sequences (templates)
CREATE TABLE email_sequences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Basic info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Trigger
    trigger_type VARCHAR(50) NOT NULL, 
    -- 'form_submit', 'lead_tier_change', 'manual', 'schedule', 'tag_added'
    trigger_config JSONB,
    -- Example: {"form_id": "uuid"} or {"from_tier": "cold", "to_tier": "warm"}
    
    -- Target
    target_type VARCHAR(50) DEFAULT 'leads', -- 'leads', 'dm_contacts', 'all'
    target_filter JSONB, -- Optional filter criteria
    
    -- Settings
    is_active BOOLEAN DEFAULT TRUE,
    send_time_preference VARCHAR(20) DEFAULT 'immediate', -- 'immediate', 'business_hours', 'specific_time'
    timezone VARCHAR(50) DEFAULT 'America/New_York',
    skip_weekends BOOLEAN DEFAULT FALSE,
    
    -- Unsubscribe
    include_unsubscribe BOOLEAN DEFAULT TRUE,
    unsubscribe_text TEXT DEFAULT 'Unsubscribe',
    
    -- Stats (denormalized for performance)
    total_sent INTEGER DEFAULT 0,
    total_opened INTEGER DEFAULT 0,
    total_clicked INTEGER DEFAULT 0,
    total_bounced INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Sequence steps
CREATE TABLE email_sequence_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_id UUID REFERENCES email_sequences(id) ON DELETE CASCADE,
    
    -- Order
    step_number INTEGER NOT NULL,
    
    -- Delay
    delay_value INTEGER NOT NULL DEFAULT 0,
    delay_unit VARCHAR(20) NOT NULL DEFAULT 'hours', -- 'minutes', 'hours', 'days'
    
    -- Content
    subject VARCHAR(500) NOT NULL,
    preview_text VARCHAR(255), -- Email preview snippet
    body_html TEXT NOT NULL,
    body_text TEXT, -- Plain text fallback
    
    -- From (optional override)
    from_name VARCHAR(255),
    from_email VARCHAR(255),
    reply_to VARCHAR(255),
    
    -- Personalization
    variables JSONB DEFAULT '[]', -- ["first_name", "company", "offer_name"]
    
    -- Conditions
    skip_conditions JSONB,
    -- Example: {"lead_status": ["converted", "unsubscribed"]}
    
    -- A/B Testing (future)
    variants JSONB,
    
    -- Stats
    sent_count INTEGER DEFAULT 0,
    open_count INTEGER DEFAULT 0,
    click_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Email queue
CREATE TABLE email_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- References
    sequence_id UUID REFERENCES email_sequences(id) ON DELETE SET NULL,
    step_id UUID REFERENCES email_sequence_steps(id) ON DELETE SET NULL,
    lead_id UUID, -- Reference to leads table
    dm_contact_id UUID, -- Reference to dm_contacts table
    
    -- Recipient (denormalized for reliability)
    to_email VARCHAR(255) NOT NULL,
    to_name VARCHAR(255),
    
    -- Content (rendered at queue time)
    from_email VARCHAR(255) NOT NULL,
    from_name VARCHAR(255),
    reply_to VARCHAR(255),
    subject VARCHAR(500) NOT NULL,
    body_html TEXT NOT NULL,
    body_text TEXT,
    
    -- Scheduling
    scheduled_at TIMESTAMPTZ NOT NULL,
    
    -- Status
    status VARCHAR(20) DEFAULT 'pending',
    -- 'pending', 'processing', 'sent', 'delivered', 'opened', 'clicked', 'bounced', 'failed', 'skipped'
    
    -- Resend tracking
    resend_id VARCHAR(100),
    
    -- Event timestamps
    sent_at TIMESTAMPTZ,
    delivered_at TIMESTAMPTZ,
    opened_at TIMESTAMPTZ,
    first_clicked_at TIMESTAMPTZ,
    bounced_at TIMESTAMPTZ,
    
    -- Click tracking
    clicks JSONB DEFAULT '[]', -- [{url, clicked_at}]
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Email templates (reusable)
CREATE TABLE email_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100), -- 'welcome', 'nurture', 'sales', 'transactional'
    
    subject VARCHAR(500) NOT NULL,
    preview_text VARCHAR(255),
    body_html TEXT NOT NULL,
    body_text TEXT,
    
    -- Variables
    variables JSONB DEFAULT '[]',
    
    -- Preview
    thumbnail_url TEXT,
    
    is_default BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Unsubscribes
CREATE TABLE email_unsubscribes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    
    reason VARCHAR(100), -- 'user_request', 'bounce', 'complaint'
    source VARCHAR(100), -- 'link_click', 'manual', 'webhook'
    
    unsubscribed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_email_queue_scheduled ON email_queue(scheduled_at) WHERE status = 'pending';
CREATE INDEX idx_email_queue_status ON email_queue(status);
CREATE INDEX idx_email_queue_lead ON email_queue(lead_id);
CREATE INDEX idx_email_queue_contact ON email_queue(dm_contact_id);
CREATE INDEX idx_sequence_steps_sequence ON email_sequence_steps(sequence_id);
CREATE INDEX idx_unsubscribes_email ON email_unsubscribes(email);
```

---

## API Endpoints

### Sequences

```yaml
# GET /api/email/sequences
# List all sequences
Response:
  sequences: EmailSequence[]

# POST /api/email/sequences
# Create sequence
Request:
  name: string
  description: string
  trigger_type: string
  trigger_config: object
  is_active: boolean
Response:
  sequence: EmailSequence

# GET /api/email/sequences/{id}
# Get sequence with steps and stats
Response:
  sequence: EmailSequence
  steps: SequenceStep[]
  stats:
    total_enrolled: number
    active_in_sequence: number
    completed: number
    conversion_rate: number

# PUT /api/email/sequences/{id}
# Update sequence

# DELETE /api/email/sequences/{id}
# Delete sequence

# POST /api/email/sequences/{id}/activate
# Activate sequence

# POST /api/email/sequences/{id}/pause
# Pause sequence
```

### Steps

```yaml
# POST /api/email/sequences/{id}/steps
# Add step to sequence
Request:
  step_number: number
  delay_value: number
  delay_unit: string
  subject: string
  body_html: string
Response:
  step: SequenceStep

# PUT /api/email/sequences/{id}/steps/{stepId}
# Update step

# DELETE /api/email/sequences/{id}/steps/{stepId}
# Delete step

# POST /api/email/sequences/{id}/steps/reorder
# Reorder steps
Request:
  order: [{step_id: uuid, step_number: number}]
```

### Queue

```yaml
# GET /api/email/queue
# View email queue
Query:
  status: string
  sequence_id: uuid
  lead_id: uuid
Response:
  emails: QueuedEmail[]
  stats: {pending, sent, failed}

# POST /api/email/queue/process
# Process queue (cron endpoint)
Headers:
  x-cron-secret: string
Response:
  processed: number
  sent: number
  failed: number

# DELETE /api/email/queue/{id}
# Cancel queued email
```

### Templates

```yaml
# GET /api/email/templates
# List templates
Query:
  category: string
Response:
  templates: EmailTemplate[]

# POST /api/email/templates
# Create template
Request:
  name: string
  category: string
  subject: string
  body_html: string
Response:
  template: EmailTemplate

# POST /api/email/templates/{id}/preview
# Preview with sample data
Request:
  variables: {first_name: "John", ...}
Response:
  subject: string
  body_html: string
```

### Sending

```yaml
# POST /api/email/send
# Send single email (not part of sequence)
Request:
  to_email: string
  to_name: string
  template_id: uuid (or)
  subject: string
  body_html: string
  variables: object
Response:
  email_id: uuid
  resend_id: string
  status: string

# POST /api/email/enroll
# Enroll lead/contact in sequence
Request:
  sequence_id: uuid
  lead_id: uuid (or)
  dm_contact_id: uuid (or)
  email: string
Response:
  enrollment_id: uuid
  first_email_scheduled: datetime
```

### Webhooks

```yaml
# POST /api/webhooks/resend
# Receive Resend events
Headers:
  svix-id: string
  svix-timestamp: string
  svix-signature: string
Request:
  type: string
  data: {...}
Response:
  received: true
```

---

## Core Services

### 1. Resend Client

```python
# Backend/services/email/resend_client.py

import resend
from typing import Optional, List

class ResendClient:
    """Resend API client for email delivery."""
    
    def __init__(self):
        resend.api_key = os.environ["RESEND_API_KEY"]
        self.from_email = os.environ.get("RESEND_FROM_EMAIL", "hello@yourdomain.com")
        self.from_name = os.environ.get("RESEND_FROM_NAME", "Your Name")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        to_name: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: Optional[str] = None,
        tags: Optional[List[dict]] = None
    ) -> dict:
        """Send a single email via Resend."""
        
        params = {
            "from": f"{from_name or self.from_name} <{from_email or self.from_email}>",
            "to": [f"{to_name} <{to_email}>" if to_name else to_email],
            "subject": subject,
            "html": body_html,
        }
        
        if reply_to:
            params["reply_to"] = reply_to
        
        if tags:
            params["tags"] = tags
        
        response = resend.Emails.send(params)
        return response
    
    async def send_batch(
        self,
        emails: List[dict]
    ) -> List[dict]:
        """Send batch of emails."""
        return resend.Batch.send(emails)
    
    def verify_webhook(
        self,
        payload: bytes,
        headers: dict
    ) -> bool:
        """Verify Resend webhook signature."""
        # Use svix library for verification
        from svix.webhooks import Webhook
        
        wh = Webhook(os.environ["RESEND_WEBHOOK_SECRET"])
        try:
            wh.verify(payload, headers)
            return True
        except:
            return False
```

### 2. Sequence Engine

```python
# Backend/services/email/sequence_engine.py

class SequenceEngine:
    """Manage email sequence enrollment and progression."""
    
    def __init__(self):
        self.resend = ResendClient()
        self.template_renderer = TemplateRenderer()
    
    async def enroll(
        self,
        sequence_id: UUID,
        lead_id: Optional[UUID] = None,
        dm_contact_id: Optional[UUID] = None,
        email: str = None
    ) -> Enrollment:
        """Enroll a lead or contact in a sequence."""
        
        # Get sequence and steps
        sequence = await self.repo.get_sequence(sequence_id)
        steps = await self.repo.get_steps(sequence_id)
        
        if not steps:
            raise ValueError("Sequence has no steps")
        
        # Get contact info
        if lead_id:
            contact = await self.leads_repo.get(lead_id)
            email = contact.email
        elif dm_contact_id:
            contact = await self.dm_repo.get(dm_contact_id)
            email = contact.email  # If available
        
        if not email:
            raise ValueError("No email address provided")
        
        # Check if already enrolled
        existing = await self.repo.get_enrollment(sequence_id, email)
        if existing and existing.status == "active":
            raise ValueError("Already enrolled in this sequence")
        
        # Check unsubscribe
        if await self.is_unsubscribed(email):
            raise ValueError("Email is unsubscribed")
        
        # Schedule first email
        first_step = steps[0]
        scheduled_at = self.calculate_send_time(
            delay_value=first_step.delay_value,
            delay_unit=first_step.delay_unit,
            sequence=sequence
        )
        
        # Queue email
        queued = await self.queue_email(
            sequence=sequence,
            step=first_step,
            email=email,
            lead_id=lead_id,
            dm_contact_id=dm_contact_id,
            scheduled_at=scheduled_at
        )
        
        return Enrollment(
            sequence_id=sequence_id,
            email=email,
            first_email_scheduled=scheduled_at
        )
    
    async def progress_to_next_step(
        self,
        queue_item: EmailQueue
    ):
        """After sending, schedule next step if exists."""
        
        if not queue_item.step_id:
            return  # Not part of sequence
        
        # Get next step
        current_step = await self.repo.get_step(queue_item.step_id)
        next_step = await self.repo.get_next_step(
            queue_item.sequence_id,
            current_step.step_number
        )
        
        if not next_step:
            return  # Sequence complete
        
        # Check skip conditions
        if await self.should_skip(queue_item, next_step):
            # Recursively check next step
            return await self.progress_to_next_step(
                queue_item._replace(step_id=next_step.id)
            )
        
        # Schedule next email
        sequence = await self.repo.get_sequence(queue_item.sequence_id)
        scheduled_at = self.calculate_send_time(
            delay_value=next_step.delay_value,
            delay_unit=next_step.delay_unit,
            sequence=sequence,
            base_time=datetime.now()
        )
        
        await self.queue_email(
            sequence=sequence,
            step=next_step,
            email=queue_item.to_email,
            lead_id=queue_item.lead_id,
            dm_contact_id=queue_item.dm_contact_id,
            scheduled_at=scheduled_at
        )
```

### 3. Queue Processor

```python
# Backend/services/email/queue_processor.py

class QueueProcessor:
    """Process email queue (cron job)."""
    
    def __init__(self):
        self.resend = ResendClient()
        self.sequence_engine = SequenceEngine()
        self.batch_size = 50
    
    async def process(self) -> ProcessResult:
        """Process all due emails."""
        
        # Get pending emails that are due
        due_emails = await self.repo.get_due_emails(
            limit=self.batch_size
        )
        
        sent = 0
        failed = 0
        
        for email in due_emails:
            try:
                # Mark as processing
                email.status = "processing"
                await self.repo.update(email)
                
                # Final unsubscribe check
                if await self.is_unsubscribed(email.to_email):
                    email.status = "skipped"
                    await self.repo.update(email)
                    continue
                
                # Send via Resend
                result = await self.resend.send_email(
                    to_email=email.to_email,
                    to_name=email.to_name,
                    subject=email.subject,
                    body_html=email.body_html,
                    from_email=email.from_email,
                    from_name=email.from_name,
                    reply_to=email.reply_to,
                    tags=[
                        {"name": "sequence_id", "value": str(email.sequence_id)},
                        {"name": "step_id", "value": str(email.step_id)},
                    ]
                )
                
                # Update status
                email.status = "sent"
                email.resend_id = result["id"]
                email.sent_at = datetime.now()
                await self.repo.update(email)
                
                # Update sequence stats
                await self.sequence_engine.increment_sent(
                    email.sequence_id, email.step_id
                )
                
                # Schedule next step
                await self.sequence_engine.progress_to_next_step(email)
                
                # Log to unified outreach
                if email.dm_contact_id:
                    await self.dm_service.log_touch(
                        contact_id=email.dm_contact_id,
                        channel="email",
                        message=email.subject
                    )
                
                sent += 1
                
            except Exception as e:
                email.status = "failed"
                email.error_message = str(e)
                email.retry_count += 1
                email.last_retry_at = datetime.now()
                await self.repo.update(email)
                failed += 1
        
        return ProcessResult(
            processed=len(due_emails),
            sent=sent,
            failed=failed
        )
```

### 4. Template Renderer

```python
# Backend/services/email/template_renderer.py

from jinja2 import Environment, BaseLoader

class TemplateRenderer:
    """Render email templates with variables."""
    
    def __init__(self):
        self.env = Environment(loader=BaseLoader())
    
    def render(
        self,
        template_html: str,
        template_subject: str,
        variables: dict
    ) -> dict:
        """Render template with variables."""
        
        # Add default variables
        variables.setdefault("current_year", datetime.now().year)
        variables.setdefault("company_name", "Your Company")
        
        # Render subject
        subject_template = self.env.from_string(template_subject)
        rendered_subject = subject_template.render(**variables)
        
        # Render body
        body_template = self.env.from_string(template_html)
        rendered_body = body_template.render(**variables)
        
        return {
            "subject": rendered_subject,
            "body_html": rendered_body
        }
    
    def get_variables(
        self,
        lead: Lead = None,
        dm_contact: DMContact = None
    ) -> dict:
        """Extract variables from lead or contact."""
        
        variables = {}
        
        if lead:
            variables["email"] = lead.email
            variables["first_name"] = self.extract_first_name(lead.name)
            variables["name"] = lead.name
            variables["company"] = lead.form_data.get("company", "")
            variables["lead_tier"] = lead.lead_tier
        
        if dm_contact:
            variables["username"] = dm_contact.username
            variables["display_name"] = dm_contact.display_name
            variables["first_name"] = self.extract_first_name(
                dm_contact.display_name or dm_contact.username
            )
            variables["platform"] = dm_contact.platform
        
        return variables
```

---

## Implementation Phases

### Phase 1: Resend Integration (Days 1-3)
| Task | Effort |
|------|--------|
| Database migration | 3h |
| Resend client | 4h |
| Send single email API | 4h |
| Webhook handler | 4h |
| Template renderer | 3h |

### Phase 2: Sequence Engine (Days 4-6)
| Task | Effort |
|------|--------|
| Sequence CRUD API | 6h |
| Step management | 4h |
| Enrollment logic | 6h |
| Queue processor | 6h |
| Cron job setup | 2h |

### Phase 3: UI (Days 7-10)
| Task | Effort |
|------|--------|
| Sequence list page | 6h |
| Sequence builder UI | 10h |
| Step editor with preview | 6h |
| Template library | 4h |
| Queue monitoring | 4h |

### Phase 4: Integration (Days 11-14)
| Task | Effort |
|------|--------|
| Unified outreach service | 4h |
| DM contact email sync | 4h |
| Lead integration | 4h |
| Analytics dashboard | 6h |
| Testing | 8h |

---

## Files to Create

```
Backend/services/email/
├── __init__.py
├── resend_client.py         # Resend API wrapper
├── sequence_engine.py       # Sequence logic
├── queue_processor.py       # Cron job processor
├── template_renderer.py     # Jinja2 rendering
├── webhook_handler.py       # Resend webhooks
└── models.py                # Pydantic models

Backend/api/endpoints/
├── email_sequences.py       # Sequence API
├── email_templates.py       # Template API
└── webhooks_resend.py       # Webhook receiver

dashboard/app/(dashboard)/email/
├── page.tsx                 # Sequence list
├── sequences/[id]/page.tsx  # Sequence editor
├── templates/page.tsx       # Template library
├── queue/page.tsx           # Queue monitor
└── components/
    ├── SequenceBuilder.tsx
    ├── StepEditor.tsx
    ├── EmailPreview.tsx
    ├── TemplateSelector.tsx
    └── QueueTable.tsx
```

---

## Environment Variables

```bash
# Resend
RESEND_API_KEY=re_xxx
RESEND_FROM_EMAIL=hello@yourdomain.com
RESEND_FROM_NAME=Your Name
RESEND_WEBHOOK_SECRET=whsec_xxx

# Cron
CRON_SECRET=xxx
```

---

## Success Criteria

- [ ] Send emails via Resend API
- [ ] Sequences trigger on form submission
- [ ] Webhooks update email status
- [ ] Open/click tracking working
- [ ] Unsubscribe handling working
- [ ] <5 minute queue processing latency
- [ ] Email + DM unified in outreach dashboard

---

*Document created: February 1, 2026*
