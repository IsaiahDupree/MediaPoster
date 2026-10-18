"""
Email Sequence Service (EMAIL-001 through EMAIL-008)
=====================================================
Provides Resend email client, sequence builder, template editor,
queue processor, webhook receiver, unified outreach, triggers,
and email analytics.

EMAIL-001: Resend Email Client - send emails via Resend API with tracking
EMAIL-002: Email Sequence Builder - multi-step sequences with delays and conditions
EMAIL-003: Email Template Editor - templates with variable rendering
EMAIL-004: Email Queue Processor - background processing with rate limiting and retries
EMAIL-005: Email Webhook Receiver - Resend webhook handling for delivery/open/click/bounce
EMAIL-006: Unified Outreach Service - merge DM + Email channels
EMAIL-007: Email Sequence Triggers - form submit, lead tier change, tag, manual triggers
EMAIL-008: Email Analytics Dashboard - sent, delivered, opened, clicked, converted metrics

Usage:
    from services.email_sequence_service import EmailSequenceService, get_email_sequence_service

    svc = get_email_sequence_service()
    svc.create_template("Welcome", "welcome", "Hello {{first_name}}", "<p>Welcome!</p>")
    seq = svc.create_sequence("Welcome Series", trigger_type="form_submit")
    svc.add_step(seq.id, subject="Welcome!", body_html="<p>Hi {{first_name}}</p>")
"""

import hashlib
import hmac
import logging
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================================
# EMAIL-001: Resend Email Client
# ============================================================================

class EmailStatus(str, Enum):
    """Email delivery status."""
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    FAILED = "failed"
    SKIPPED = "skipped"


class TriggerType(str, Enum):
    """Sequence trigger types (EMAIL-007)."""
    FORM_SUBMIT = "form_submit"
    LEAD_TIER_CHANGE = "lead_tier_change"
    TAG_ADDED = "tag_added"
    MANUAL = "manual"
    SCHEDULE = "schedule"


class WebhookEventType(str, Enum):
    """Resend webhook event types (EMAIL-005)."""
    EMAIL_SENT = "email.sent"
    EMAIL_DELIVERED = "email.delivered"
    EMAIL_OPENED = "email.opened"
    EMAIL_CLICKED = "email.clicked"
    EMAIL_BOUNCED = "email.bounced"
    EMAIL_COMPLAINED = "email.complained"


@dataclass
class ResendConfig:
    """Resend API configuration (EMAIL-001)."""
    api_key: str = ""
    from_email: str = "hello@yourdomain.com"
    from_name: str = "MediaPoster"
    webhook_secret: str = ""
    rate_limit_per_second: int = 10

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_email": self.from_email,
            "from_name": self.from_name,
            "is_configured": self.is_configured(),
            "rate_limit_per_second": self.rate_limit_per_second,
        }


@dataclass
class SentEmail:
    """Record of a sent email (EMAIL-001)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    resend_id: Optional[str] = None
    to_email: str = ""
    to_name: str = ""
    from_email: str = ""
    from_name: str = ""
    reply_to: str = ""
    subject: str = ""
    body_html: str = ""
    body_text: str = ""
    tags: Dict[str, str] = field(default_factory=dict)
    status: str = EmailStatus.PENDING
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    error_message: str = ""
    clicks: List[Dict[str, Any]] = field(default_factory=list)
    sequence_id: Optional[str] = None
    step_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "resend_id": self.resend_id,
            "to_email": self.to_email,
            "to_name": self.to_name,
            "subject": self.subject,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "opened_at": self.opened_at.isoformat() if self.opened_at else None,
            "clicked_at": self.clicked_at.isoformat() if self.clicked_at else None,
            "bounced_at": self.bounced_at.isoformat() if self.bounced_at else None,
            "tags": self.tags,
            "sequence_id": self.sequence_id,
            "step_id": self.step_id,
        }


# ============================================================================
# EMAIL-002: Email Sequence Builder
# ============================================================================

@dataclass
class SequenceStep:
    """A step in an email sequence (EMAIL-002)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    sequence_id: str = ""
    step_number: int = 1
    delay_value: int = 0
    delay_unit: str = "hours"  # minutes, hours, days
    subject: str = ""
    preview_text: str = ""
    body_html: str = ""
    body_text: str = ""
    from_name: str = ""
    from_email: str = ""
    reply_to: str = ""
    variables: List[str] = field(default_factory=list)
    skip_conditions: Optional[Dict[str, Any]] = None
    sent_count: int = 0
    open_count: int = 0
    click_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def get_delay_timedelta(self) -> timedelta:
        """Convert delay to timedelta."""
        if self.delay_unit == "minutes":
            return timedelta(minutes=self.delay_value)
        elif self.delay_unit == "hours":
            return timedelta(hours=self.delay_value)
        elif self.delay_unit == "days":
            return timedelta(days=self.delay_value)
        return timedelta()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sequence_id": self.sequence_id,
            "step_number": self.step_number,
            "delay_value": self.delay_value,
            "delay_unit": self.delay_unit,
            "subject": self.subject,
            "preview_text": self.preview_text,
            "body_html": self.body_html,
            "from_name": self.from_name,
            "sent_count": self.sent_count,
            "open_count": self.open_count,
            "click_count": self.click_count,
        }


@dataclass
class EmailSequence:
    """An email sequence definition (EMAIL-002)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    description: str = ""
    trigger_type: str = TriggerType.MANUAL
    trigger_config: Dict[str, Any] = field(default_factory=dict)
    target_type: str = "leads"
    target_filter: Optional[Dict[str, Any]] = None
    is_active: bool = True
    send_time_preference: str = "immediate"
    timezone: str = "America/New_York"
    skip_weekends: bool = False
    include_unsubscribe: bool = True
    unsubscribe_text: str = "Unsubscribe"
    total_sent: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    total_bounced: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger_type": self.trigger_type,
            "trigger_config": self.trigger_config,
            "is_active": self.is_active,
            "send_time_preference": self.send_time_preference,
            "skip_weekends": self.skip_weekends,
            "total_sent": self.total_sent,
            "total_opened": self.total_opened,
            "total_clicked": self.total_clicked,
            "total_bounced": self.total_bounced,
        }


# ============================================================================
# EMAIL-003: Email Template Editor
# ============================================================================

@dataclass
class EmailTemplate:
    """Reusable email template (EMAIL-003)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    category: str = "general"  # welcome, nurture, sales, transactional
    subject: str = ""
    preview_text: str = ""
    body_html: str = ""
    body_text: str = ""
    variables: List[str] = field(default_factory=list)
    thumbnail_url: str = ""
    is_default: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "subject": self.subject,
            "preview_text": self.preview_text,
            "body_html": self.body_html,
            "variables": self.variables,
            "is_default": self.is_default,
        }


# ============================================================================
# EMAIL-004: Queue Item
# ============================================================================

@dataclass
class QueuedEmail:
    """An email in the processing queue (EMAIL-004)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    sequence_id: Optional[str] = None
    step_id: Optional[str] = None
    lead_id: Optional[str] = None
    to_email: str = ""
    to_name: str = ""
    from_email: str = ""
    from_name: str = ""
    reply_to: str = ""
    subject: str = ""
    body_html: str = ""
    body_text: str = ""
    scheduled_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = EmailStatus.PENDING
    resend_id: str = ""
    sent_at: Optional[datetime] = None
    error_message: str = ""
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sequence_id": self.sequence_id,
            "step_id": self.step_id,
            "to_email": self.to_email,
            "subject": self.subject,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "status": self.status,
            "retry_count": self.retry_count,
        }


# ============================================================================
# EMAIL-006: Unified Outreach
# ============================================================================

@dataclass
class OutreachTouch:
    """A unified outreach touch (EMAIL-006)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    contact_id: str = ""
    channel: str = ""  # email, dm_instagram, dm_twitter, dm_linkedin
    message: str = ""
    subject: str = ""
    status: str = ""
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "contact_id": self.contact_id,
            "channel": self.channel,
            "message": self.message,
            "subject": self.subject,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
        }


# ============================================================================
# EMAIL-007: Trigger Registration
# ============================================================================

@dataclass
class TriggerRegistration:
    """A registered trigger for a sequence (EMAIL-007)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    sequence_id: str = ""
    trigger_type: str = TriggerType.MANUAL
    trigger_config: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    last_fired_at: Optional[datetime] = None
    fire_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sequence_id": self.sequence_id,
            "trigger_type": self.trigger_type,
            "trigger_config": self.trigger_config,
            "is_active": self.is_active,
            "fire_count": self.fire_count,
        }


# ============================================================================
# Main Service
# ============================================================================

class EmailSequenceService:
    """
    Email Sequence Service (EMAIL-001 through EMAIL-008).

    In-memory implementation for testing. Production would use
    Supabase tables and the actual Resend API.
    """

    _instance: Optional["EmailSequenceService"] = None

    def __init__(
        self,
        resend_api_key: str = "",
        from_email: str = "hello@yourdomain.com",
        from_name: str = "MediaPoster",
    ):
        # EMAIL-001: Resend config
        self.config = ResendConfig(
            api_key=resend_api_key or os.environ.get("RESEND_API_KEY", ""),
            from_email=from_email,
            from_name=from_name,
            webhook_secret=os.environ.get("RESEND_WEBHOOK_SECRET", ""),
        )

        # In-memory stores
        self._sent_emails: Dict[str, SentEmail] = {}
        self._sequences: Dict[str, EmailSequence] = {}
        self._steps: Dict[str, SequenceStep] = {}  # step_id -> step
        self._templates: Dict[str, EmailTemplate] = {}
        self._queue: Dict[str, QueuedEmail] = {}
        self._unsubscribes: Dict[str, datetime] = {}  # email -> unsub time
        self._enrollments: Dict[str, Dict[str, Any]] = {}  # email+seq_id -> enrollment
        self._triggers: Dict[str, TriggerRegistration] = {}
        self._outreach_touches: List[OutreachTouch] = []
        self._webhook_events: List[Dict[str, Any]] = []

        # Stats
        self._stats = {
            "emails_sent": 0,
            "emails_delivered": 0,
            "emails_opened": 0,
            "emails_clicked": 0,
            "emails_bounced": 0,
            "webhooks_received": 0,
            "queue_processed": 0,
            "triggers_fired": 0,
        }

    @classmethod
    def get_instance(cls, **kwargs) -> "EmailSequenceService":
        if cls._instance is None:
            cls._instance = cls(**kwargs)
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    # ========================================================================
    # EMAIL-001: Resend Email Client
    # ========================================================================

    def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        to_name: str = "",
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        reply_to: str = "",
        tags: Optional[Dict[str, str]] = None,
        sequence_id: Optional[str] = None,
        step_id: Optional[str] = None,
    ) -> SentEmail:
        """Send a single email (EMAIL-001).

        In production, calls Resend API. In-memory for testing.
        """
        # Check unsubscribe
        if to_email in self._unsubscribes:
            email = SentEmail(
                to_email=to_email,
                to_name=to_name,
                subject=subject,
                status=EmailStatus.SKIPPED,
            )
            self._sent_emails[email.id] = email
            return email

        now = datetime.now(timezone.utc)
        email = SentEmail(
            to_email=to_email,
            to_name=to_name,
            from_email=from_email or self.config.from_email,
            from_name=from_name or self.config.from_name,
            reply_to=reply_to,
            subject=subject,
            body_html=body_html,
            tags=tags or {},
            status=EmailStatus.SENT,
            sent_at=now,
            resend_id=f"resend_{uuid4().hex[:12]}",
            sequence_id=sequence_id,
            step_id=step_id,
        )

        self._sent_emails[email.id] = email
        self._stats["emails_sent"] += 1

        logger.info(f"Email sent to {to_email}: {subject}")
        return email

    def send_batch(self, emails: List[Dict[str, Any]]) -> List[SentEmail]:
        """Send a batch of emails (EMAIL-001)."""
        results = []
        for e in emails:
            result = self.send_email(
                to_email=e["to_email"],
                subject=e["subject"],
                body_html=e["body_html"],
                to_name=e.get("to_name", ""),
                tags=e.get("tags"),
            )
            results.append(result)
        return results

    def get_sent_email(self, email_id: str) -> Optional[SentEmail]:
        """Get a sent email by ID."""
        return self._sent_emails.get(email_id)

    def get_sent_emails(
        self,
        to_email: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[SentEmail]:
        """Get sent emails with optional filtering."""
        results = list(self._sent_emails.values())
        if to_email:
            results = [e for e in results if e.to_email == to_email]
        if status:
            results = [e for e in results if e.status == status]
        results.sort(key=lambda e: e.sent_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return results[:limit]

    # ========================================================================
    # EMAIL-002: Email Sequence Builder
    # ========================================================================

    def create_sequence(
        self,
        name: str,
        description: str = "",
        trigger_type: str = TriggerType.MANUAL,
        trigger_config: Optional[Dict[str, Any]] = None,
        is_active: bool = True,
        skip_weekends: bool = False,
        send_time_preference: str = "immediate",
    ) -> EmailSequence:
        """Create an email sequence (EMAIL-002)."""
        seq = EmailSequence(
            name=name,
            description=description,
            trigger_type=trigger_type,
            trigger_config=trigger_config or {},
            is_active=is_active,
            skip_weekends=skip_weekends,
            send_time_preference=send_time_preference,
        )
        self._sequences[seq.id] = seq
        return seq

    def get_sequence(self, sequence_id: str) -> Optional[EmailSequence]:
        """Get a sequence by ID."""
        return self._sequences.get(sequence_id)

    def list_sequences(
        self, is_active: Optional[bool] = None
    ) -> List[EmailSequence]:
        """List sequences with optional filter."""
        results = list(self._sequences.values())
        if is_active is not None:
            results = [s for s in results if s.is_active == is_active]
        return results

    def update_sequence(self, sequence_id: str, **kwargs) -> Optional[EmailSequence]:
        """Update a sequence."""
        seq = self._sequences.get(sequence_id)
        if not seq:
            return None
        for key, val in kwargs.items():
            if hasattr(seq, key):
                setattr(seq, key, val)
        seq.updated_at = datetime.now(timezone.utc)
        return seq

    def delete_sequence(self, sequence_id: str) -> bool:
        """Delete a sequence and its steps."""
        if sequence_id not in self._sequences:
            return False
        del self._sequences[sequence_id]
        # Remove associated steps
        step_ids = [sid for sid, s in self._steps.items() if s.sequence_id == sequence_id]
        for sid in step_ids:
            del self._steps[sid]
        return True

    def activate_sequence(self, sequence_id: str) -> bool:
        """Activate a sequence."""
        seq = self._sequences.get(sequence_id)
        if not seq:
            return False
        seq.is_active = True
        seq.updated_at = datetime.now(timezone.utc)
        return True

    def pause_sequence(self, sequence_id: str) -> bool:
        """Pause a sequence."""
        seq = self._sequences.get(sequence_id)
        if not seq:
            return False
        seq.is_active = False
        seq.updated_at = datetime.now(timezone.utc)
        return True

    def add_step(
        self,
        sequence_id: str,
        subject: str,
        body_html: str,
        delay_value: int = 0,
        delay_unit: str = "hours",
        step_number: Optional[int] = None,
        preview_text: str = "",
        from_name: str = "",
        from_email: str = "",
        reply_to: str = "",
        skip_conditions: Optional[Dict[str, Any]] = None,
    ) -> Optional[SequenceStep]:
        """Add a step to a sequence (EMAIL-002)."""
        if sequence_id not in self._sequences:
            return None

        # Auto-assign step number
        if step_number is None:
            existing = self.get_sequence_steps(sequence_id)
            step_number = len(existing) + 1

        step = SequenceStep(
            sequence_id=sequence_id,
            step_number=step_number,
            delay_value=delay_value,
            delay_unit=delay_unit,
            subject=subject,
            preview_text=preview_text,
            body_html=body_html,
            from_name=from_name,
            from_email=from_email,
            reply_to=reply_to,
            skip_conditions=skip_conditions,
        )
        self._steps[step.id] = step
        return step

    def get_sequence_steps(self, sequence_id: str) -> List[SequenceStep]:
        """Get all steps for a sequence, ordered by step_number."""
        steps = [s for s in self._steps.values() if s.sequence_id == sequence_id]
        steps.sort(key=lambda s: s.step_number)
        return steps

    def update_step(self, step_id: str, **kwargs) -> Optional[SequenceStep]:
        """Update a step."""
        step = self._steps.get(step_id)
        if not step:
            return None
        for key, val in kwargs.items():
            if hasattr(step, key):
                setattr(step, key, val)
        return step

    def delete_step(self, step_id: str) -> bool:
        """Delete a step."""
        if step_id not in self._steps:
            return False
        del self._steps[step_id]
        return True

    def reorder_steps(self, sequence_id: str, step_order: List[Dict[str, Any]]) -> bool:
        """Reorder steps in a sequence."""
        for item in step_order:
            step = self._steps.get(item["step_id"])
            if step and step.sequence_id == sequence_id:
                step.step_number = item["step_number"]
        return True

    # ========================================================================
    # EMAIL-003: Email Template Editor
    # ========================================================================

    def create_template(
        self,
        name: str,
        category: str = "general",
        subject: str = "",
        body_html: str = "",
        body_text: str = "",
        variables: Optional[List[str]] = None,
        is_default: bool = False,
    ) -> EmailTemplate:
        """Create an email template (EMAIL-003)."""
        # Auto-detect variables from template
        if variables is None:
            variables = self._extract_variables(body_html)
            variables.extend(v for v in self._extract_variables(subject) if v not in variables)

        tpl = EmailTemplate(
            name=name,
            category=category,
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            variables=variables,
            is_default=is_default,
        )
        self._templates[tpl.id] = tpl
        return tpl

    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def list_templates(self, category: Optional[str] = None) -> List[EmailTemplate]:
        """List templates with optional category filter."""
        results = list(self._templates.values())
        if category:
            results = [t for t in results if t.category == category]
        return results

    def update_template(self, template_id: str, **kwargs) -> Optional[EmailTemplate]:
        """Update a template."""
        tpl = self._templates.get(template_id)
        if not tpl:
            return None
        for key, val in kwargs.items():
            if hasattr(tpl, key):
                setattr(tpl, key, val)
        tpl.updated_at = datetime.now(timezone.utc)
        return tpl

    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id not in self._templates:
            return False
        del self._templates[template_id]
        return True

    def render_template(
        self, template_id: str, variables: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        """Render a template with variables (EMAIL-003).

        Returns dict with 'subject' and 'body_html' keys.
        """
        tpl = self._templates.get(template_id)
        if not tpl:
            return None
        return self._render_content(tpl.subject, tpl.body_html, variables)

    def preview_template(
        self, subject: str, body_html: str, variables: Dict[str, Any]
    ) -> Dict[str, str]:
        """Preview template rendering without saving (EMAIL-003)."""
        return self._render_content(subject, body_html, variables)

    def _render_content(
        self, subject: str, body_html: str, variables: Dict[str, Any]
    ) -> Dict[str, str]:
        """Render subject and body with Jinja2-style variable substitution."""
        rendered_subject = subject
        rendered_body = body_html
        for key, val in variables.items():
            pattern = "{{" + key + "}}"
            rendered_subject = rendered_subject.replace(pattern, str(val))
            rendered_body = rendered_body.replace(pattern, str(val))
        return {"subject": rendered_subject, "body_html": rendered_body}

    def _extract_variables(self, text: str) -> List[str]:
        """Extract {{variable}} names from text."""
        return list(set(re.findall(r"\{\{(\w+)\}\}", text)))

    # ========================================================================
    # EMAIL-004: Email Queue Processor
    # ========================================================================

    def enqueue_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        to_name: str = "",
        scheduled_at: Optional[datetime] = None,
        sequence_id: Optional[str] = None,
        step_id: Optional[str] = None,
        lead_id: Optional[str] = None,
    ) -> QueuedEmail:
        """Add an email to the processing queue (EMAIL-004)."""
        item = QueuedEmail(
            to_email=to_email,
            to_name=to_name,
            from_email=self.config.from_email,
            from_name=self.config.from_name,
            subject=subject,
            body_html=body_html,
            scheduled_at=scheduled_at or datetime.now(timezone.utc),
            sequence_id=sequence_id,
            step_id=step_id,
            lead_id=lead_id,
        )
        self._queue[item.id] = item
        return item

    def get_queue_item(self, queue_id: str) -> Optional[QueuedEmail]:
        """Get a queue item by ID."""
        return self._queue.get(queue_id)

    def get_queue(
        self,
        status: Optional[str] = None,
        sequence_id: Optional[str] = None,
    ) -> List[QueuedEmail]:
        """Get queue items with optional filtering."""
        results = list(self._queue.values())
        if status:
            results = [q for q in results if q.status == status]
        if sequence_id:
            results = [q for q in results if q.sequence_id == sequence_id]
        results.sort(key=lambda q: q.scheduled_at)
        return results

    def get_due_emails(self, limit: int = 50) -> List[QueuedEmail]:
        """Get emails that are due to be sent (EMAIL-004)."""
        now = datetime.now(timezone.utc)
        due = [
            q for q in self._queue.values()
            if q.status == EmailStatus.PENDING and q.scheduled_at <= now
        ]
        due.sort(key=lambda q: q.scheduled_at)
        return due[:limit]

    def process_queue(self, batch_size: int = 50) -> Dict[str, int]:
        """Process all due emails in the queue (EMAIL-004).

        Returns stats: {processed, sent, failed, skipped}.
        """
        due = self.get_due_emails(limit=batch_size)
        sent = 0
        failed = 0
        skipped = 0

        for item in due:
            item.status = EmailStatus.PROCESSING

            # Check unsubscribe
            if item.to_email in self._unsubscribes:
                item.status = EmailStatus.SKIPPED
                skipped += 1
                continue

            try:
                result = self.send_email(
                    to_email=item.to_email,
                    to_name=item.to_name,
                    subject=item.subject,
                    body_html=item.body_html,
                    sequence_id=item.sequence_id,
                    step_id=item.step_id,
                )
                item.status = EmailStatus.SENT
                item.resend_id = result.resend_id or ""
                item.sent_at = result.sent_at

                # Update step stats
                if item.step_id and item.step_id in self._steps:
                    self._steps[item.step_id].sent_count += 1

                # Update sequence stats
                if item.sequence_id and item.sequence_id in self._sequences:
                    self._sequences[item.sequence_id].total_sent += 1

                # Schedule next step
                self._schedule_next_step(item)

                sent += 1
            except Exception as e:
                item.status = EmailStatus.FAILED
                item.error_message = str(e)
                item.retry_count += 1
                item.last_retry_at = datetime.now(timezone.utc)
                failed += 1

        self._stats["queue_processed"] += len(due)
        return {
            "processed": len(due),
            "sent": sent,
            "failed": failed,
            "skipped": skipped,
        }

    def cancel_queued_email(self, queue_id: str) -> bool:
        """Cancel a queued email."""
        item = self._queue.get(queue_id)
        if not item or item.status != EmailStatus.PENDING:
            return False
        item.status = EmailStatus.SKIPPED
        return True

    def retry_failed(self, queue_id: str) -> bool:
        """Retry a failed queue item."""
        item = self._queue.get(queue_id)
        if not item or item.status != EmailStatus.FAILED:
            return False
        item.status = EmailStatus.PENDING
        item.scheduled_at = datetime.now(timezone.utc)
        return True

    def _schedule_next_step(self, item: QueuedEmail):
        """Schedule the next step in a sequence after sending."""
        if not item.sequence_id or not item.step_id:
            return

        steps = self.get_sequence_steps(item.sequence_id)
        current = self._steps.get(item.step_id)
        if not current:
            return

        # Find next step
        next_step = None
        for s in steps:
            if s.step_number > current.step_number:
                next_step = s
                break

        if not next_step:
            return  # Sequence complete

        # Check skip conditions
        if next_step.skip_conditions:
            # In production, check lead status etc.
            pass

        # Schedule
        scheduled_at = datetime.now(timezone.utc) + next_step.get_delay_timedelta()
        self.enqueue_email(
            to_email=item.to_email,
            to_name=item.to_name,
            subject=next_step.subject,
            body_html=next_step.body_html,
            scheduled_at=scheduled_at,
            sequence_id=item.sequence_id,
            step_id=next_step.id,
            lead_id=item.lead_id,
        )

    # ========================================================================
    # EMAIL-005: Webhook Receiver
    # ========================================================================

    def process_webhook(
        self,
        event_type: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Process a Resend webhook event (EMAIL-005).

        Args:
            event_type: Webhook event type (e.g., "email.delivered")
            data: Event data payload
            headers: Optional webhook headers for signature verification

        Returns:
            Processing result.
        """
        self._stats["webhooks_received"] += 1
        self._webhook_events.append({
            "type": event_type,
            "data": data,
            "received_at": datetime.now(timezone.utc).isoformat(),
        })

        # Find the sent email by resend_id or queue email_id
        email_id = data.get("email_id") or data.get("resend_id")
        sent_email = None
        for e in self._sent_emails.values():
            if e.resend_id == email_id or e.id == email_id:
                sent_email = e
                break

        if not sent_email:
            return {"status": "ignored", "reason": "email_not_found"}

        now = datetime.now(timezone.utc)

        if event_type == WebhookEventType.EMAIL_DELIVERED:
            sent_email.status = EmailStatus.DELIVERED
            sent_email.delivered_at = now
            self._stats["emails_delivered"] += 1

        elif event_type == WebhookEventType.EMAIL_OPENED:
            if not sent_email.opened_at:
                sent_email.opened_at = now
                self._stats["emails_opened"] += 1
                # Update step/sequence stats
                if sent_email.step_id and sent_email.step_id in self._steps:
                    self._steps[sent_email.step_id].open_count += 1
                if sent_email.sequence_id and sent_email.sequence_id in self._sequences:
                    self._sequences[sent_email.sequence_id].total_opened += 1

        elif event_type == WebhookEventType.EMAIL_CLICKED:
            if not sent_email.clicked_at:
                sent_email.clicked_at = now
                self._stats["emails_clicked"] += 1
                if sent_email.step_id and sent_email.step_id in self._steps:
                    self._steps[sent_email.step_id].click_count += 1
                if sent_email.sequence_id and sent_email.sequence_id in self._sequences:
                    self._sequences[sent_email.sequence_id].total_clicked += 1
            # Track click URL
            click_url = data.get("url", "")
            if click_url:
                sent_email.clicks.append({"url": click_url, "clicked_at": now.isoformat()})

        elif event_type == WebhookEventType.EMAIL_BOUNCED:
            sent_email.status = EmailStatus.BOUNCED
            sent_email.bounced_at = now
            self._stats["emails_bounced"] += 1
            if sent_email.sequence_id and sent_email.sequence_id in self._sequences:
                self._sequences[sent_email.sequence_id].total_bounced += 1

        elif event_type == WebhookEventType.EMAIL_COMPLAINED:
            # Auto-unsubscribe on complaint
            self.unsubscribe(sent_email.to_email, reason="complaint")

        return {"status": "processed", "event_type": event_type, "email_id": sent_email.id}

    def verify_webhook_signature(
        self, payload: bytes, headers: Dict[str, str]
    ) -> bool:
        """Verify Resend webhook signature (EMAIL-005)."""
        secret = self.config.webhook_secret
        if not secret:
            return True  # No secret configured, accept all

        signature = headers.get("svix-signature", "")
        timestamp = headers.get("svix-timestamp", "")
        msg_id = headers.get("svix-id", "")

        if not signature or not timestamp:
            return False

        # Construct signed content
        signed_content = f"{msg_id}.{timestamp}.{payload.decode('utf-8')}"
        expected = hmac.new(
            secret.encode(), signed_content.encode(), hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

    def get_webhook_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent webhook events."""
        return self._webhook_events[-limit:]

    # ========================================================================
    # EMAIL-005 (cont): Unsubscribe Management
    # ========================================================================

    def unsubscribe(self, email: str, reason: str = "user_request") -> bool:
        """Unsubscribe an email address."""
        if email in self._unsubscribes:
            return False
        self._unsubscribes[email] = datetime.now(timezone.utc)
        return True

    def is_unsubscribed(self, email: str) -> bool:
        """Check if an email is unsubscribed."""
        return email in self._unsubscribes

    def get_unsubscribes(self) -> List[Dict[str, Any]]:
        """Get all unsubscribed emails."""
        return [
            {"email": email, "unsubscribed_at": ts.isoformat()}
            for email, ts in self._unsubscribes.items()
        ]

    # ========================================================================
    # EMAIL-006: Unified Outreach Service
    # ========================================================================

    def log_outreach_touch(
        self,
        contact_id: str,
        channel: str,
        message: str,
        subject: str = "",
        status: str = "sent",
    ) -> OutreachTouch:
        """Log an outreach touch across any channel (EMAIL-006)."""
        touch = OutreachTouch(
            contact_id=contact_id,
            channel=channel,
            message=message,
            subject=subject,
            status=status,
            sent_at=datetime.now(timezone.utc),
        )
        self._outreach_touches.append(touch)
        return touch

    def get_contact_touches(
        self, contact_id: str, channel: Optional[str] = None
    ) -> List[OutreachTouch]:
        """Get all outreach touches for a contact (EMAIL-006)."""
        touches = [t for t in self._outreach_touches if t.contact_id == contact_id]
        if channel:
            touches = [t for t in touches if t.channel == channel]
        touches.sort(key=lambda t: t.sent_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return touches

    def get_outreach_summary(self, contact_id: str) -> Dict[str, Any]:
        """Get unified outreach summary for a contact (EMAIL-006)."""
        touches = self.get_contact_touches(contact_id)
        channels = {}
        for t in touches:
            if t.channel not in channels:
                channels[t.channel] = {"count": 0, "last_sent": None}
            channels[t.channel]["count"] += 1
            if t.sent_at:
                channels[t.channel]["last_sent"] = t.sent_at.isoformat()

        return {
            "contact_id": contact_id,
            "total_touches": len(touches),
            "channels": channels,
        }

    # ========================================================================
    # EMAIL-007: Email Sequence Triggers
    # ========================================================================

    def register_trigger(
        self,
        sequence_id: str,
        trigger_type: str,
        trigger_config: Optional[Dict[str, Any]] = None,
    ) -> Optional[TriggerRegistration]:
        """Register a trigger for a sequence (EMAIL-007)."""
        if sequence_id not in self._sequences:
            return None

        trigger = TriggerRegistration(
            sequence_id=sequence_id,
            trigger_type=trigger_type,
            trigger_config=trigger_config or {},
        )
        self._triggers[trigger.id] = trigger
        return trigger

    def fire_trigger(
        self,
        trigger_type: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Fire a trigger event and enroll matching contacts (EMAIL-007).

        Args:
            trigger_type: Type of trigger (form_submit, lead_tier_change, etc.)
            context: Trigger context data (email, lead_id, form_id, etc.)

        Returns:
            List of enrollment results.
        """
        results = []
        email = context.get("email", "")
        lead_id = context.get("lead_id")

        if not email:
            return results

        # Find matching triggers
        for trigger in self._triggers.values():
            if not trigger.is_active:
                continue
            if trigger.trigger_type != trigger_type:
                continue

            # Check trigger config match
            if not self._matches_trigger_config(trigger, context):
                continue

            seq = self._sequences.get(trigger.sequence_id)
            if not seq or not seq.is_active:
                continue

            # Enroll in sequence
            enrollment = self.enroll_in_sequence(
                sequence_id=trigger.sequence_id,
                email=email,
                lead_id=lead_id,
            )
            if enrollment:
                trigger.fire_count += 1
                trigger.last_fired_at = datetime.now(timezone.utc)
                self._stats["triggers_fired"] += 1
                results.append(enrollment)

        return results

    def _matches_trigger_config(
        self, trigger: TriggerRegistration, context: Dict[str, Any]
    ) -> bool:
        """Check if context matches trigger config."""
        config = trigger.trigger_config

        if trigger.trigger_type == TriggerType.FORM_SUBMIT:
            if "form_id" in config:
                return context.get("form_id") == config["form_id"]
            return True  # No specific form filter

        elif trigger.trigger_type == TriggerType.LEAD_TIER_CHANGE:
            if "to_tier" in config:
                return context.get("new_tier") == config["to_tier"]
            return True

        elif trigger.trigger_type == TriggerType.TAG_ADDED:
            if "tag" in config:
                return context.get("tag") == config["tag"]
            return True

        return True  # Manual and schedule always match

    def get_triggers(self, sequence_id: Optional[str] = None) -> List[TriggerRegistration]:
        """Get registered triggers."""
        triggers = list(self._triggers.values())
        if sequence_id:
            triggers = [t for t in triggers if t.sequence_id == sequence_id]
        return triggers

    def enroll_in_sequence(
        self,
        sequence_id: str,
        email: str,
        lead_id: Optional[str] = None,
        name: str = "",
        variables: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Enroll a contact in a sequence (EMAIL-007)."""
        seq = self._sequences.get(sequence_id)
        if not seq or not seq.is_active:
            return None

        if self.is_unsubscribed(email):
            return None

        # Check if already enrolled
        enrollment_key = f"{email}:{sequence_id}"
        if enrollment_key in self._enrollments:
            existing = self._enrollments[enrollment_key]
            if existing.get("status") == "active":
                return None  # Already enrolled

        steps = self.get_sequence_steps(sequence_id)
        if not steps:
            return None

        first_step = steps[0]

        # Render content with variables
        render_vars = variables or {}
        render_vars.setdefault("first_name", name.split()[0] if name else "there")
        rendered = self._render_content(first_step.subject, first_step.body_html, render_vars)

        # Schedule first email
        scheduled_at = datetime.now(timezone.utc) + first_step.get_delay_timedelta()
        queued = self.enqueue_email(
            to_email=email,
            to_name=name,
            subject=rendered["subject"],
            body_html=rendered["body_html"],
            scheduled_at=scheduled_at,
            sequence_id=sequence_id,
            step_id=first_step.id,
            lead_id=lead_id,
        )

        enrollment = {
            "email": email,
            "sequence_id": sequence_id,
            "status": "active",
            "enrolled_at": datetime.now(timezone.utc).isoformat(),
            "first_email_scheduled": scheduled_at.isoformat(),
            "queue_id": queued.id,
        }
        self._enrollments[enrollment_key] = enrollment
        return enrollment

    # ========================================================================
    # EMAIL-008: Email Analytics Dashboard
    # ========================================================================

    def get_email_analytics(self) -> Dict[str, Any]:
        """Get overall email analytics (EMAIL-008)."""
        total_sent = self._stats["emails_sent"]
        total_delivered = self._stats["emails_delivered"]
        total_opened = self._stats["emails_opened"]
        total_clicked = self._stats["emails_clicked"]
        total_bounced = self._stats["emails_bounced"]

        return {
            "total_sent": total_sent,
            "total_delivered": total_delivered,
            "total_opened": total_opened,
            "total_clicked": total_clicked,
            "total_bounced": total_bounced,
            "open_rate": (total_opened / total_sent * 100) if total_sent else 0,
            "click_rate": (total_clicked / total_sent * 100) if total_sent else 0,
            "bounce_rate": (total_bounced / total_sent * 100) if total_sent else 0,
            "delivery_rate": (total_delivered / total_sent * 100) if total_sent else 0,
        }

    def get_sequence_analytics(self, sequence_id: str) -> Optional[Dict[str, Any]]:
        """Get analytics for a specific sequence (EMAIL-008)."""
        seq = self._sequences.get(sequence_id)
        if not seq:
            return None

        steps = self.get_sequence_steps(sequence_id)
        step_analytics = []
        for step in steps:
            step_analytics.append({
                "step_number": step.step_number,
                "subject": step.subject,
                "sent_count": step.sent_count,
                "open_count": step.open_count,
                "click_count": step.click_count,
                "open_rate": (step.open_count / step.sent_count * 100) if step.sent_count else 0,
                "click_rate": (step.click_count / step.sent_count * 100) if step.sent_count else 0,
            })

        # Count enrollments
        enrollments = [
            e for e in self._enrollments.values()
            if e.get("sequence_id") == sequence_id
        ]
        active = [e for e in enrollments if e.get("status") == "active"]
        completed = [e for e in enrollments if e.get("status") == "completed"]

        return {
            "sequence_id": sequence_id,
            "name": seq.name,
            "total_sent": seq.total_sent,
            "total_opened": seq.total_opened,
            "total_clicked": seq.total_clicked,
            "total_bounced": seq.total_bounced,
            "open_rate": (seq.total_opened / seq.total_sent * 100) if seq.total_sent else 0,
            "click_rate": (seq.total_clicked / seq.total_sent * 100) if seq.total_sent else 0,
            "total_enrolled": len(enrollments),
            "active_in_sequence": len(active),
            "completed": len(completed),
            "steps": step_analytics,
        }

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics (EMAIL-008)."""
        queue = list(self._queue.values())
        return {
            "total": len(queue),
            "pending": len([q for q in queue if q.status == EmailStatus.PENDING]),
            "sent": len([q for q in queue if q.status == EmailStatus.SENT]),
            "failed": len([q for q in queue if q.status == EmailStatus.FAILED]),
            "skipped": len([q for q in queue if q.status == EmailStatus.SKIPPED]),
            "processing": len([q for q in queue if q.status == EmailStatus.PROCESSING]),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get overall service stats."""
        return {
            **self._stats,
            "sequences": len(self._sequences),
            "templates": len(self._templates),
            "queue_size": len(self._queue),
            "unsubscribes": len(self._unsubscribes),
            "enrollments": len(self._enrollments),
            "triggers": len(self._triggers),
            "config": self.config.to_dict(),
        }


# ============================================================================
# Module-level singleton accessor
# ============================================================================

def get_email_sequence_service(**kwargs) -> EmailSequenceService:
    """Get or create the singleton EmailSequenceService."""
    return EmailSequenceService.get_instance(**kwargs)
