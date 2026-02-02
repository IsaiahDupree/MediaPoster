"""
Lead Form Service (LEAD-001 through LEAD-008)
==============================================
In-memory lead form builder, submission handler, scoring engine,
management dashboard, public waitlist, CSV import/export, webhook
integration, and email sequence triggering for MediaPoster.

Provides:
    - Lead Form Builder (LEAD-001)
    - Lead Form Submission Handler (LEAD-002)
    - Lead Scoring with FATE (LEAD-003)
    - Lead Management Dashboard (LEAD-004)
    - Public Waitlist API (LEAD-005)
    - Lead CSV Import/Export (LEAD-006)
    - Lead Webhook Integration (LEAD-007)
    - Lead Email Sequence Trigger (LEAD-008)

Usage:
    from services.lead_form_service import LeadFormService, get_lead_form_service

    svc = get_lead_form_service()
    form = svc.create_form(name="Beta Waitlist", form_type="waitlist")
    lead = svc.submit_form(form.id, {"email": "user@example.com", "name": "Jane"})
    svc.score_lead(lead.id)
"""

import csv
import io
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================

class LeadFieldType(str, Enum):
    """Supported field types for lead form questions."""
    TEXT = "text"
    EMAIL = "email"
    PHONE = "phone"
    SELECT = "select"
    CHECKBOX = "checkbox"
    TEXTAREA = "textarea"
    NUMBER = "number"
    URL = "url"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class LeadForm:
    """Lead form definition (LEAD-001)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    name: str = ""
    slug: str = ""
    form_type: str = "general"  # general, waitlist, survey, quiz
    questions: List[Dict[str, Any]] = field(default_factory=list)
    scoring_rules: List[Dict[str, Any]] = field(default_factory=list)
    theme: Dict[str, Any] = field(default_factory=dict)
    thank_you_message: str = "Thank you for your submission!"
    redirect_url: Optional[str] = None
    email_sequence_id: Optional[str] = None
    webhook_url: Optional[str] = None
    submission_count: int = 0
    conversion_count: int = 0
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Lead:
    """Lead record created from a form submission (LEAD-002)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    form_id: str = ""
    email: str = ""
    name: str = ""
    phone: str = ""
    form_data: Dict[str, Any] = field(default_factory=dict)
    lead_score: float = 0.0
    lead_tier: str = "cold"  # hot, warm, cold
    scoring_breakdown: Dict[str, Any] = field(default_factory=dict)
    status: str = "new"  # new, contacted, qualified, converted, lost
    converted_at: Optional[str] = None
    conversion_value: float = 0.0
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WaitlistEntry:
    """Waitlist entry for public waitlist API (LEAD-005)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    email: str = ""
    name: str = ""
    form_id: str = ""
    position: int = 0
    status: str = "pending"  # pending, approved, converted
    referral_code: str = field(default_factory=lambda: str(uuid4())[:8])
    referred_by: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LeadWebhook:
    """Webhook configuration for lead events (LEAD-007)."""
    id: str = field(default_factory=lambda: str(uuid4()))
    form_id: str = ""
    url: str = ""
    events: List[str] = field(default_factory=list)  # e.g. ["submission", "scored", "converted"]
    is_active: bool = True
    last_fired_at: Optional[str] = None
    fire_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================================
# Validation Helpers
# ============================================================================

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE_RE = re.compile(r"^[\d\s\+\-\(\)]{7,20}$")
_URL_RE = re.compile(r"^https?://\S+$")


def _validate_field(value: Any, field_type: str) -> bool:
    """Return True when *value* is valid for *field_type*."""
    if field_type == LeadFieldType.EMAIL:
        return isinstance(value, str) and bool(_EMAIL_RE.match(value))
    if field_type == LeadFieldType.PHONE:
        return isinstance(value, str) and bool(_PHONE_RE.match(value))
    if field_type == LeadFieldType.URL:
        return isinstance(value, str) and bool(_URL_RE.match(value))
    if field_type == LeadFieldType.NUMBER:
        try:
            float(value)
            return True
        except (TypeError, ValueError):
            return False
    if field_type == LeadFieldType.CHECKBOX:
        return isinstance(value, bool)
    # TEXT, SELECT, TEXTAREA -- any non-empty string is fine
    return isinstance(value, str) and len(value) > 0


# ============================================================================
# Lead Form Service
# ============================================================================

class LeadFormService:
    """
    Lead Form Service (LEAD-001 through LEAD-008).

    Manages lead forms, submissions, scoring, waitlists, CSV import/export,
    webhook integration, and email sequence triggers using in-memory stores.
    """

    _instance: Optional["LeadFormService"] = None

    def __init__(self) -> None:
        # In-memory stores
        self._forms: Dict[str, LeadForm] = {}
        self._leads: Dict[str, Lead] = {}
        self._waitlist: Dict[str, WaitlistEntry] = {}  # id -> entry
        self._webhooks: Dict[str, LeadWebhook] = {}
        # Track webhook payloads for testing / auditing
        self._fired_webhooks: List[Dict[str, Any]] = []
        logger.info("LeadFormService initialized")

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "LeadFormService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for testing)."""
        cls._instance = None

    # ------------------------------------------------------------------
    # LEAD-001: Lead Form Builder
    # ------------------------------------------------------------------

    def create_form(
        self,
        name: str,
        form_type: str = "general",
        slug: Optional[str] = None,
        questions: Optional[List[Dict[str, Any]]] = None,
        scoring_rules: Optional[List[Dict[str, Any]]] = None,
        theme: Optional[Dict[str, Any]] = None,
        thank_you_message: str = "Thank you for your submission!",
        redirect_url: Optional[str] = None,
        email_sequence_id: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> LeadForm:
        """Create a new lead form definition (LEAD-001)."""
        generated_slug = slug or name.lower().replace(" ", "-")
        form = LeadForm(
            name=name,
            slug=generated_slug,
            form_type=form_type,
            questions=questions or [],
            scoring_rules=scoring_rules or [],
            theme=theme or {},
            thank_you_message=thank_you_message,
            redirect_url=redirect_url,
            email_sequence_id=email_sequence_id,
            webhook_url=webhook_url,
        )
        self._forms[form.id] = form
        logger.info("LEAD-001: Form created: %s (%s)", form.id, name)
        return form

    def get_form(self, form_id: str) -> Optional[LeadForm]:
        """Get a form by ID (LEAD-001)."""
        return self._forms.get(form_id)

    def get_form_by_slug(self, slug: str) -> Optional[LeadForm]:
        """Get a form by slug (LEAD-001)."""
        for form in self._forms.values():
            if form.slug == slug:
                return form
        return None

    def list_forms(self, active_only: bool = False) -> List[LeadForm]:
        """List all forms (LEAD-001)."""
        forms = list(self._forms.values())
        if active_only:
            forms = [f for f in forms if f.is_active]
        return forms

    def update_form(self, form_id: str, **kwargs: Any) -> Optional[LeadForm]:
        """Update an existing form (LEAD-001)."""
        form = self._forms.get(form_id)
        if not form:
            return None
        for key, value in kwargs.items():
            if hasattr(form, key):
                setattr(form, key, value)
        form.updated_at = datetime.now(timezone.utc).isoformat()
        logger.info("LEAD-001: Form updated: %s", form_id)
        return form

    def delete_form(self, form_id: str) -> bool:
        """Delete a form (LEAD-001)."""
        if form_id in self._forms:
            del self._forms[form_id]
            logger.info("LEAD-001: Form deleted: %s", form_id)
            return True
        return False

    # ------------------------------------------------------------------
    # LEAD-002: Lead Form Submission Handler
    # ------------------------------------------------------------------

    def submit_form(
        self,
        form_id: str,
        data: Dict[str, Any],
    ) -> Lead:
        """
        Process a form submission, validate data, and create a lead record (LEAD-002).

        Args:
            form_id: ID of the form being submitted.
            data: Key-value mapping of submitted form fields.  Must include
                  at least ``email``.

        Returns:
            The created Lead record.

        Raises:
            ValueError: When the form is not found, is inactive, email is
                        missing/invalid, or a required field fails validation.
        """
        form = self._forms.get(form_id)
        if not form:
            raise ValueError(f"Form not found: {form_id}")
        if not form.is_active:
            raise ValueError(f"Form is inactive: {form_id}")

        # Email is always required
        email = data.get("email", "")
        if not email or not _validate_field(email, LeadFieldType.EMAIL):
            raise ValueError("A valid email address is required")

        # Validate each question marked as required
        for question in form.questions:
            field_name = question.get("name") or question.get("field")
            field_type = question.get("type", LeadFieldType.TEXT)
            required = question.get("required", False)
            value = data.get(field_name)
            if required and (value is None or value == ""):
                raise ValueError(f"Required field missing: {field_name}")
            if value is not None and value != "" and not _validate_field(value, field_type):
                raise ValueError(f"Invalid value for field '{field_name}' (expected {field_type})")

        lead = Lead(
            form_id=form_id,
            email=email,
            name=data.get("name", ""),
            phone=data.get("phone", ""),
            form_data=data,
        )
        self._leads[lead.id] = lead
        form.submission_count += 1
        logger.info("LEAD-002: Lead created: %s from form %s", lead.id, form_id)

        # Fire webhooks for this form
        self.fire_webhooks(form_id, "submission", lead.to_dict())

        return lead

    # ------------------------------------------------------------------
    # LEAD-003: Lead Scoring with FATE
    # ------------------------------------------------------------------

    def score_lead(self, lead_id: str) -> Lead:
        """
        Calculate a lead score using the form's scoring rules and assign a tier (LEAD-003).

        Each scoring rule is a dict with:
            - field: the form_data key to evaluate
            - operator: "equals", "contains", "gt", "lt", "exists"
            - value: the comparison value (unused for "exists")
            - points: integer points to add when rule matches

        Tier assignment:
            - score >= 80 -> "hot"
            - score >= 40 -> "warm"
            - else         -> "cold"

        Raises:
            ValueError: When lead is not found.
        """
        lead = self._leads.get(lead_id)
        if not lead:
            raise ValueError(f"Lead not found: {lead_id}")

        form = self._forms.get(lead.form_id)
        rules = form.scoring_rules if form else []

        total_score = 0.0
        breakdown: Dict[str, Any] = {}

        for rule in rules:
            rule_field = rule.get("field", "")
            operator = rule.get("operator", "exists")
            rule_value = rule.get("value")
            points = rule.get("points", 0)
            data_value = lead.form_data.get(rule_field)

            matched = False
            if operator == "equals" and data_value == rule_value:
                matched = True
            elif operator == "contains" and isinstance(data_value, str) and isinstance(rule_value, str) and rule_value.lower() in data_value.lower():
                matched = True
            elif operator == "gt":
                try:
                    matched = float(data_value) > float(rule_value)
                except (TypeError, ValueError):
                    matched = False
            elif operator == "lt":
                try:
                    matched = float(data_value) < float(rule_value)
                except (TypeError, ValueError):
                    matched = False
            elif operator == "exists":
                matched = data_value is not None and data_value != ""

            if matched:
                total_score += points
                breakdown[rule_field] = {
                    "operator": operator,
                    "points": points,
                    "matched": True,
                }
            else:
                breakdown[rule_field] = {
                    "operator": operator,
                    "points": 0,
                    "matched": False,
                }

        lead.lead_score = total_score
        lead.scoring_breakdown = breakdown

        if total_score >= 80:
            lead.lead_tier = "hot"
        elif total_score >= 40:
            lead.lead_tier = "warm"
        else:
            lead.lead_tier = "cold"

        logger.info("LEAD-003: Lead %s scored %.1f -> %s", lead_id, total_score, lead.lead_tier)

        # Fire webhooks
        if form:
            self.fire_webhooks(form.form_id if hasattr(form, "form_id") else lead.form_id, "scored", lead.to_dict())

        return lead

    # ------------------------------------------------------------------
    # LEAD-004: Lead Management Dashboard
    # ------------------------------------------------------------------

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        """Get a lead by ID (LEAD-004)."""
        return self._leads.get(lead_id)

    def list_leads(self, form_id: Optional[str] = None) -> List[Lead]:
        """List all leads, optionally filtered by form (LEAD-004)."""
        leads = list(self._leads.values())
        if form_id:
            leads = [l for l in leads if l.form_id == form_id]
        return leads

    def update_lead_status(self, lead_id: str, status: str) -> Optional[Lead]:
        """
        Update a lead's status (LEAD-004).

        Valid statuses: new, contacted, qualified, converted, lost.
        """
        valid_statuses = {"new", "contacted", "qualified", "converted", "lost"}
        if status not in valid_statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")
        lead = self._leads.get(lead_id)
        if not lead:
            return None
        lead.status = status
        if status == "converted":
            lead.converted_at = datetime.now(timezone.utc).isoformat()
            # Bump conversion count on the form
            form = self._forms.get(lead.form_id)
            if form:
                form.conversion_count += 1
        logger.info("LEAD-004: Lead %s status -> %s", lead_id, status)
        return lead

    def add_lead_tag(self, lead_id: str, tag: str) -> Optional[Lead]:
        """Add a tag to a lead (LEAD-004)."""
        lead = self._leads.get(lead_id)
        if not lead:
            return None
        if tag not in lead.tags:
            lead.tags.append(tag)
        return lead

    def remove_lead_tag(self, lead_id: str, tag: str) -> Optional[Lead]:
        """Remove a tag from a lead (LEAD-004)."""
        lead = self._leads.get(lead_id)
        if not lead:
            return None
        if tag in lead.tags:
            lead.tags.remove(tag)
        return lead

    def filter_leads(
        self,
        min_score: Optional[float] = None,
        tier: Optional[str] = None,
        status: Optional[str] = None,
        form_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Lead]:
        """
        Filter leads by multiple criteria (LEAD-004).

        All provided filters are combined with AND logic.
        """
        leads = list(self._leads.values())
        if form_id is not None:
            leads = [l for l in leads if l.form_id == form_id]
        if min_score is not None:
            leads = [l for l in leads if l.lead_score >= min_score]
        if tier is not None:
            leads = [l for l in leads if l.lead_tier == tier]
        if status is not None:
            leads = [l for l in leads if l.status == status]
        if tags:
            leads = [l for l in leads if all(t in l.tags for t in tags)]
        return leads

    # ------------------------------------------------------------------
    # LEAD-005: Public Waitlist API
    # ------------------------------------------------------------------

    def join_waitlist(
        self,
        form_id: str,
        email: str,
        name: str = "",
        referred_by: Optional[str] = None,
    ) -> WaitlistEntry:
        """
        Add someone to the public waitlist (LEAD-005).

        Each entry receives an auto-incrementing position and a unique
        referral code.

        Raises:
            ValueError: When form not found or email already on waitlist.
        """
        form = self._forms.get(form_id)
        if not form:
            raise ValueError(f"Form not found: {form_id}")

        # Check for duplicate email on the same form
        for entry in self._waitlist.values():
            if entry.form_id == form_id and entry.email == email:
                raise ValueError(f"Email already on waitlist: {email}")

        # Calculate position
        existing_count = sum(
            1 for e in self._waitlist.values() if e.form_id == form_id
        )
        position = existing_count + 1

        entry = WaitlistEntry(
            email=email,
            name=name,
            form_id=form_id,
            position=position,
            referred_by=referred_by,
        )
        self._waitlist[entry.id] = entry
        logger.info("LEAD-005: Waitlist entry #%d for form %s", position, form_id)
        return entry

    def get_waitlist_position(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """Get current waitlist position info (LEAD-005)."""
        entry = self._waitlist.get(entry_id)
        if not entry:
            return None
        total = sum(1 for e in self._waitlist.values() if e.form_id == entry.form_id)
        return {
            "id": entry.id,
            "email": entry.email,
            "position": entry.position,
            "total": total,
            "status": entry.status,
            "referral_code": entry.referral_code,
        }

    def list_waitlist(self, form_id: str) -> List[WaitlistEntry]:
        """List waitlist entries for a form, ordered by position (LEAD-005)."""
        entries = [e for e in self._waitlist.values() if e.form_id == form_id]
        return sorted(entries, key=lambda e: e.position)

    def approve_waitlist_entry(self, entry_id: str) -> Optional[WaitlistEntry]:
        """Approve a waitlist entry (LEAD-005)."""
        entry = self._waitlist.get(entry_id)
        if not entry:
            return None
        entry.status = "approved"
        logger.info("LEAD-005: Waitlist entry %s approved", entry_id)
        return entry

    # ------------------------------------------------------------------
    # LEAD-006: Lead CSV Import / Export
    # ------------------------------------------------------------------

    def export_leads_csv(self, form_id: Optional[str] = None) -> str:
        """
        Export leads as a CSV string (LEAD-006).

        Includes columns: id, form_id, email, name, phone, lead_score,
        lead_tier, status, tags, created_at.
        """
        leads = self.list_leads(form_id=form_id)
        output = io.StringIO()
        fieldnames = [
            "id", "form_id", "email", "name", "phone",
            "lead_score", "lead_tier", "status", "tags", "created_at",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for lead in leads:
            writer.writerow({
                "id": lead.id,
                "form_id": lead.form_id,
                "email": lead.email,
                "name": lead.name,
                "phone": lead.phone,
                "lead_score": lead.lead_score,
                "lead_tier": lead.lead_tier,
                "status": lead.status,
                "tags": ";".join(lead.tags),
                "created_at": lead.created_at,
            })
        return output.getvalue()

    def import_leads_csv(self, csv_text: str, form_id: str) -> List[Lead]:
        """
        Import leads from a CSV string (LEAD-006).

        Expected columns at minimum: ``email``.  Optional: ``name``,
        ``phone``, ``tags`` (semicolon-separated).

        Returns:
            List of created Lead records.

        Raises:
            ValueError: When CSV is empty or form not found.
        """
        form = self._forms.get(form_id)
        if not form:
            raise ValueError(f"Form not found: {form_id}")

        reader = csv.DictReader(io.StringIO(csv_text))
        imported: List[Lead] = []
        for row in reader:
            email = row.get("email", "").strip()
            if not email:
                continue
            tags_raw = row.get("tags", "")
            tags = [t.strip() for t in tags_raw.split(";") if t.strip()] if tags_raw else []
            lead = Lead(
                form_id=form_id,
                email=email,
                name=row.get("name", "").strip(),
                phone=row.get("phone", "").strip(),
                tags=tags,
                form_data=dict(row),
            )
            self._leads[lead.id] = lead
            imported.append(lead)
        logger.info("LEAD-006: Imported %d leads into form %s", len(imported), form_id)
        return imported

    # ------------------------------------------------------------------
    # LEAD-007: Lead Webhook Integration
    # ------------------------------------------------------------------

    def register_webhook(
        self,
        form_id: str,
        url: str,
        events: Optional[List[str]] = None,
    ) -> LeadWebhook:
        """Register a webhook for a form's lead events (LEAD-007)."""
        webhook = LeadWebhook(
            form_id=form_id,
            url=url,
            events=events or ["submission"],
        )
        self._webhooks[webhook.id] = webhook
        logger.info("LEAD-007: Webhook registered: %s for form %s", webhook.id, form_id)
        return webhook

    def fire_webhooks(
        self,
        form_id: str,
        event: str,
        payload: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Fire all matching webhooks for a form event (LEAD-007).

        In production this would make HTTP POST requests.  In the in-memory
        implementation we record the fired payload for testing.

        Returns:
            List of fired webhook records.
        """
        fired: List[Dict[str, Any]] = []
        for webhook in self._webhooks.values():
            if webhook.form_id != form_id:
                continue
            if not webhook.is_active:
                continue
            if event not in webhook.events:
                continue
            record = {
                "webhook_id": webhook.id,
                "form_id": form_id,
                "event": event,
                "url": webhook.url,
                "payload": payload,
                "fired_at": datetime.now(timezone.utc).isoformat(),
            }
            webhook.last_fired_at = record["fired_at"]
            webhook.fire_count += 1
            fired.append(record)
            self._fired_webhooks.append(record)
            logger.info("LEAD-007: Webhook fired: %s -> %s (%s)", webhook.id, webhook.url, event)
        return fired

    def list_webhooks(self, form_id: Optional[str] = None) -> List[LeadWebhook]:
        """List registered webhooks, optionally for a specific form (LEAD-007)."""
        webhooks = list(self._webhooks.values())
        if form_id:
            webhooks = [w for w in webhooks if w.form_id == form_id]
        return webhooks

    # ------------------------------------------------------------------
    # LEAD-008: Lead Email Sequence Trigger
    # ------------------------------------------------------------------

    def trigger_email_sequence(
        self,
        lead_id: str,
        tier_threshold: str = "warm",
    ) -> Optional[Dict[str, Any]]:
        """
        Trigger an email sequence enrollment when a lead reaches a tier threshold (LEAD-008).

        The form must have ``email_sequence_id`` configured.

        Args:
            lead_id: Lead to evaluate.
            tier_threshold: Minimum tier to trigger ("hot", "warm", or "cold").

        Returns:
            A dict describing the enrollment, or ``None`` if the lead does
            not meet the threshold or no sequence is configured.
        """
        lead = self._leads.get(lead_id)
        if not lead:
            return None

        tier_order = {"cold": 0, "warm": 1, "hot": 2}
        lead_tier_value = tier_order.get(lead.lead_tier, 0)
        threshold_value = tier_order.get(tier_threshold, 1)

        if lead_tier_value < threshold_value:
            return None

        form = self._forms.get(lead.form_id)
        if not form or not form.email_sequence_id:
            return None

        enrollment = {
            "lead_id": lead.id,
            "email": lead.email,
            "lead_tier": lead.lead_tier,
            "lead_score": lead.lead_score,
            "email_sequence_id": form.email_sequence_id,
            "form_id": form.id,
            "enrolled_at": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(
            "LEAD-008: Lead %s enrolled in sequence %s (tier=%s)",
            lead_id, form.email_sequence_id, lead.lead_tier,
        )

        # Fire webhooks for the enrollment event
        self.fire_webhooks(lead.form_id, "email_sequence_enrolled", enrollment)

        return enrollment


# ============================================================================
# Module-level Convenience Function
# ============================================================================

def get_lead_form_service() -> LeadFormService:
    """Get the singleton LeadFormService instance."""
    return LeadFormService.get_instance()
