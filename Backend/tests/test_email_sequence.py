"""
Tests for Email Sequence Service (EMAIL-001 through EMAIL-008)
================================================================
Validates Resend email client, sequence builder, template editor,
queue processor, webhook receiver, unified outreach, triggers,
and email analytics dashboard.
"""
import pytest
from datetime import datetime, timedelta, timezone
from services.email_sequence_service import (
    EmailSequenceService,
    get_email_sequence_service,
    ResendConfig,
    SentEmail,
    EmailSequence,
    SequenceStep,
    EmailTemplate,
    QueuedEmail,
    OutreachTouch,
    TriggerRegistration,
    EmailStatus,
    TriggerType,
    WebhookEventType,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def svc():
    """Fresh EmailSequenceService for testing."""
    EmailSequenceService.reset_instance()
    return EmailSequenceService(
        resend_api_key="test_key_123",
        from_email="test@example.com",
        from_name="Test Sender",
    )


# ============================================================================
# EMAIL-001: Resend Email Client
# ============================================================================

class TestEMAIL001_ResendClient:
    """EMAIL-001: Resend Email Client"""

    def test_config_creation(self, svc):
        """EMAIL-001: Config has correct fields."""
        assert svc.config.api_key == "test_key_123"
        assert svc.config.from_email == "test@example.com"
        assert svc.config.from_name == "Test Sender"
        assert svc.config.is_configured() is True

    def test_config_not_configured(self):
        """EMAIL-001: Empty API key is not configured."""
        svc = EmailSequenceService()
        assert svc.config.is_configured() is False

    def test_config_to_dict(self, svc):
        """EMAIL-001: Config serializes to dict."""
        d = svc.config.to_dict()
        assert "from_email" in d
        assert "is_configured" in d
        assert d["is_configured"] is True

    def test_send_email(self, svc):
        """EMAIL-001: Send a single email."""
        result = svc.send_email(
            to_email="user@example.com",
            subject="Hello!",
            body_html="<p>Hi there</p>",
            to_name="User",
        )
        assert result.to_email == "user@example.com"
        assert result.subject == "Hello!"
        assert result.status == EmailStatus.SENT
        assert result.resend_id is not None
        assert result.sent_at is not None

    def test_send_email_increments_stats(self, svc):
        """EMAIL-001: Sending emails increments stats."""
        svc.send_email(to_email="a@b.com", subject="Test", body_html="<p>Hi</p>")
        svc.send_email(to_email="c@d.com", subject="Test2", body_html="<p>Hi</p>")
        assert svc._stats["emails_sent"] == 2

    def test_send_batch(self, svc):
        """EMAIL-001: Send batch of emails."""
        emails = [
            {"to_email": "a@b.com", "subject": "S1", "body_html": "<p>1</p>"},
            {"to_email": "c@d.com", "subject": "S2", "body_html": "<p>2</p>"},
            {"to_email": "e@f.com", "subject": "S3", "body_html": "<p>3</p>"},
        ]
        results = svc.send_batch(emails)
        assert len(results) == 3
        assert all(r.status == EmailStatus.SENT for r in results)

    def test_get_sent_email(self, svc):
        """EMAIL-001: Retrieve sent email by ID."""
        sent = svc.send_email(to_email="user@test.com", subject="Find me", body_html="<p>X</p>")
        found = svc.get_sent_email(sent.id)
        assert found is not None
        assert found.subject == "Find me"

    def test_get_sent_emails_filter(self, svc):
        """EMAIL-001: Filter sent emails."""
        svc.send_email(to_email="a@b.com", subject="S1", body_html="<p>1</p>")
        svc.send_email(to_email="a@b.com", subject="S2", body_html="<p>2</p>")
        svc.send_email(to_email="c@d.com", subject="S3", body_html="<p>3</p>")

        results = svc.get_sent_emails(to_email="a@b.com")
        assert len(results) == 2

    def test_sent_email_to_dict(self, svc):
        """EMAIL-001: SentEmail serializes to dict."""
        sent = svc.send_email(to_email="x@y.com", subject="Test", body_html="<p>X</p>")
        d = sent.to_dict()
        assert "id" in d
        assert "to_email" in d
        assert "status" in d
        assert "sent_at" in d


# ============================================================================
# EMAIL-002: Email Sequence Builder
# ============================================================================

class TestEMAIL002_SequenceBuilder:
    """EMAIL-002: Email Sequence Builder"""

    def test_create_sequence(self, svc):
        """EMAIL-002: Create a sequence."""
        seq = svc.create_sequence(
            name="Welcome Series",
            description="Welcome new users",
            trigger_type=TriggerType.FORM_SUBMIT,
        )
        assert seq.name == "Welcome Series"
        assert seq.trigger_type == TriggerType.FORM_SUBMIT
        assert seq.is_active is True
        assert seq.id is not None

    def test_get_sequence(self, svc):
        """EMAIL-002: Retrieve sequence by ID."""
        created = svc.create_sequence(name="Test Seq")
        found = svc.get_sequence(created.id)
        assert found is not None
        assert found.name == "Test Seq"

    def test_list_sequences(self, svc):
        """EMAIL-002: List all sequences."""
        svc.create_sequence(name="S1")
        svc.create_sequence(name="S2", is_active=False)
        svc.create_sequence(name="S3")

        all_seqs = svc.list_sequences()
        assert len(all_seqs) == 3

        active = svc.list_sequences(is_active=True)
        assert len(active) == 2

    def test_update_sequence(self, svc):
        """EMAIL-002: Update a sequence."""
        seq = svc.create_sequence(name="Old Name")
        updated = svc.update_sequence(seq.id, name="New Name", skip_weekends=True)
        assert updated.name == "New Name"
        assert updated.skip_weekends is True

    def test_delete_sequence(self, svc):
        """EMAIL-002: Delete a sequence and its steps."""
        seq = svc.create_sequence(name="To Delete")
        svc.add_step(seq.id, subject="S", body_html="<p>B</p>")
        assert svc.delete_sequence(seq.id) is True
        assert svc.get_sequence(seq.id) is None
        assert len(svc.get_sequence_steps(seq.id)) == 0

    def test_activate_pause_sequence(self, svc):
        """EMAIL-002: Activate and pause a sequence."""
        seq = svc.create_sequence(name="Toggle")
        svc.pause_sequence(seq.id)
        assert svc.get_sequence(seq.id).is_active is False
        svc.activate_sequence(seq.id)
        assert svc.get_sequence(seq.id).is_active is True

    def test_add_steps(self, svc):
        """EMAIL-002: Add steps to a sequence."""
        seq = svc.create_sequence(name="Multi-step")
        s1 = svc.add_step(seq.id, subject="Welcome!", body_html="<p>Hi</p>", delay_value=0)
        s2 = svc.add_step(seq.id, subject="Follow up", body_html="<p>Hey</p>", delay_value=1, delay_unit="days")
        s3 = svc.add_step(seq.id, subject="Last chance", body_html="<p>!</p>", delay_value=3, delay_unit="days")

        steps = svc.get_sequence_steps(seq.id)
        assert len(steps) == 3
        assert steps[0].step_number == 1
        assert steps[1].step_number == 2
        assert steps[2].step_number == 3
        assert steps[1].delay_value == 1
        assert steps[1].delay_unit == "days"

    def test_step_delay_timedelta(self, svc):
        """EMAIL-002: Step delay converts to timedelta."""
        seq = svc.create_sequence(name="Delays")
        step_h = svc.add_step(seq.id, subject="S", body_html="<p>B</p>", delay_value=6, delay_unit="hours")
        step_d = svc.add_step(seq.id, subject="S", body_html="<p>B</p>", delay_value=2, delay_unit="days")
        step_m = svc.add_step(seq.id, subject="S", body_html="<p>B</p>", delay_value=30, delay_unit="minutes")

        assert step_h.get_delay_timedelta() == timedelta(hours=6)
        assert step_d.get_delay_timedelta() == timedelta(days=2)
        assert step_m.get_delay_timedelta() == timedelta(minutes=30)

    def test_reorder_steps(self, svc):
        """EMAIL-002: Reorder steps."""
        seq = svc.create_sequence(name="Reorder")
        s1 = svc.add_step(seq.id, subject="First", body_html="<p>1</p>")
        s2 = svc.add_step(seq.id, subject="Second", body_html="<p>2</p>")

        svc.reorder_steps(seq.id, [
            {"step_id": s2.id, "step_number": 1},
            {"step_id": s1.id, "step_number": 2},
        ])

        steps = svc.get_sequence_steps(seq.id)
        assert steps[0].subject == "Second"
        assert steps[1].subject == "First"

    def test_sequence_to_dict(self, svc):
        """EMAIL-002: Sequence serializes to dict."""
        seq = svc.create_sequence(name="Serialize")
        d = seq.to_dict()
        assert "id" in d
        assert "name" in d
        assert "trigger_type" in d
        assert "total_sent" in d

    def test_step_to_dict(self, svc):
        """EMAIL-002: Step serializes to dict."""
        seq = svc.create_sequence(name="S")
        step = svc.add_step(seq.id, subject="Sub", body_html="<p>B</p>")
        d = step.to_dict()
        assert "id" in d
        assert "subject" in d
        assert "sent_count" in d


# ============================================================================
# EMAIL-003: Email Template Editor
# ============================================================================

class TestEMAIL003_TemplateEditor:
    """EMAIL-003: Email Template Editor"""

    def test_create_template(self, svc):
        """EMAIL-003: Create a template."""
        tpl = svc.create_template(
            name="Welcome",
            category="welcome",
            subject="Hello {{first_name}}",
            body_html="<p>Welcome, {{first_name}}! Your plan: {{plan}}</p>",
        )
        assert tpl.name == "Welcome"
        assert tpl.category == "welcome"
        assert "first_name" in tpl.variables
        assert "plan" in tpl.variables

    def test_list_templates_by_category(self, svc):
        """EMAIL-003: List templates by category."""
        svc.create_template(name="T1", category="welcome")
        svc.create_template(name="T2", category="sales")
        svc.create_template(name="T3", category="welcome")

        welcome = svc.list_templates(category="welcome")
        assert len(welcome) == 2

    def test_render_template(self, svc):
        """EMAIL-003: Render template with variables."""
        tpl = svc.create_template(
            name="Greet",
            subject="Hi {{first_name}}",
            body_html="<p>Hello {{first_name}}, welcome to {{company}}</p>",
        )
        rendered = svc.render_template(tpl.id, {"first_name": "Jane", "company": "Acme"})
        assert rendered is not None
        assert rendered["subject"] == "Hi Jane"
        assert "Hello Jane" in rendered["body_html"]
        assert "Acme" in rendered["body_html"]

    def test_preview_template(self, svc):
        """EMAIL-003: Preview template without saving."""
        rendered = svc.preview_template(
            subject="Deal for {{first_name}}",
            body_html="<p>{{offer}} for you!</p>",
            variables={"first_name": "Bob", "offer": "50% off"},
        )
        assert rendered["subject"] == "Deal for Bob"
        assert "50% off" in rendered["body_html"]

    def test_extract_variables(self, svc):
        """EMAIL-003: Extract variables from template."""
        tpl = svc.create_template(
            name="Auto",
            subject="{{greeting}} {{name}}",
            body_html="<p>Your code: {{code}}</p>",
        )
        assert "greeting" in tpl.variables
        assert "name" in tpl.variables
        assert "code" in tpl.variables

    def test_update_template(self, svc):
        """EMAIL-003: Update a template."""
        tpl = svc.create_template(name="Old", subject="Old Sub")
        svc.update_template(tpl.id, name="New", subject="New Sub")
        updated = svc.get_template(tpl.id)
        assert updated.name == "New"
        assert updated.subject == "New Sub"

    def test_delete_template(self, svc):
        """EMAIL-003: Delete a template."""
        tpl = svc.create_template(name="Delete Me")
        assert svc.delete_template(tpl.id) is True
        assert svc.get_template(tpl.id) is None

    def test_template_to_dict(self, svc):
        """EMAIL-003: Template serializes to dict."""
        tpl = svc.create_template(name="Ser", subject="S", body_html="<p>B</p>")
        d = tpl.to_dict()
        assert "id" in d
        assert "name" in d
        assert "category" in d
        assert "variables" in d


# ============================================================================
# EMAIL-004: Email Queue Processor
# ============================================================================

class TestEMAIL004_QueueProcessor:
    """EMAIL-004: Email Queue Processor"""

    def test_enqueue_email(self, svc):
        """EMAIL-004: Add email to queue."""
        item = svc.enqueue_email(
            to_email="user@test.com",
            subject="Queued",
            body_html="<p>Queued email</p>",
        )
        assert item.status == EmailStatus.PENDING
        assert item.to_email == "user@test.com"

    def test_get_due_emails(self, svc):
        """EMAIL-004: Get emails due for sending."""
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        future = datetime.now(timezone.utc) + timedelta(hours=1)

        svc.enqueue_email(to_email="a@b.com", subject="Due", body_html="<p>D</p>", scheduled_at=past)
        svc.enqueue_email(to_email="c@d.com", subject="Not due", body_html="<p>N</p>", scheduled_at=future)

        due = svc.get_due_emails()
        assert len(due) == 1
        assert due[0].subject == "Due"

    def test_process_queue(self, svc):
        """EMAIL-004: Process queue sends due emails."""
        past = datetime.now(timezone.utc) - timedelta(minutes=1)
        svc.enqueue_email(to_email="a@b.com", subject="S1", body_html="<p>1</p>", scheduled_at=past)
        svc.enqueue_email(to_email="c@d.com", subject="S2", body_html="<p>2</p>", scheduled_at=past)

        result = svc.process_queue()
        assert result["processed"] == 2
        assert result["sent"] == 2
        assert result["failed"] == 0

    def test_process_queue_skips_unsubscribed(self, svc):
        """EMAIL-004: Queue skips unsubscribed emails."""
        svc.unsubscribe("blocked@test.com")
        past = datetime.now(timezone.utc) - timedelta(minutes=1)
        svc.enqueue_email(to_email="blocked@test.com", subject="S", body_html="<p>B</p>", scheduled_at=past)

        result = svc.process_queue()
        assert result["skipped"] == 1
        assert result["sent"] == 0

    def test_cancel_queued_email(self, svc):
        """EMAIL-004: Cancel a queued email."""
        item = svc.enqueue_email(to_email="a@b.com", subject="Cancel", body_html="<p>C</p>")
        assert svc.cancel_queued_email(item.id) is True
        assert svc.get_queue_item(item.id).status == EmailStatus.SKIPPED

    def test_retry_failed(self, svc):
        """EMAIL-004: Retry a failed queue item."""
        item = svc.enqueue_email(to_email="a@b.com", subject="Fail", body_html="<p>F</p>")
        item.status = EmailStatus.FAILED
        assert svc.retry_failed(item.id) is True
        assert svc.get_queue_item(item.id).status == EmailStatus.PENDING

    def test_get_queue_filter(self, svc):
        """EMAIL-004: Get queue items with filters."""
        svc.enqueue_email(to_email="a@b.com", subject="S1", body_html="<p>1</p>")
        q2 = svc.enqueue_email(to_email="c@d.com", subject="S2", body_html="<p>2</p>")
        q2.status = EmailStatus.SENT

        pending = svc.get_queue(status=EmailStatus.PENDING)
        assert len(pending) == 1

    def test_queue_schedules_next_step(self, svc):
        """EMAIL-004: Processing queue schedules next sequence step."""
        seq = svc.create_sequence(name="Multi")
        s1 = svc.add_step(seq.id, subject="Step 1", body_html="<p>1</p>", delay_value=0)
        s2 = svc.add_step(seq.id, subject="Step 2", body_html="<p>2</p>", delay_value=1, delay_unit="days")

        past = datetime.now(timezone.utc) - timedelta(minutes=1)
        svc.enqueue_email(
            to_email="user@test.com",
            subject="Step 1",
            body_html="<p>1</p>",
            scheduled_at=past,
            sequence_id=seq.id,
            step_id=s1.id,
        )

        result = svc.process_queue()
        assert result["sent"] == 1

        # Should have scheduled step 2
        queue = svc.get_queue()
        step2_items = [q for q in queue if q.step_id == s2.id]
        assert len(step2_items) == 1
        assert step2_items[0].status == EmailStatus.PENDING

    def test_queued_email_to_dict(self, svc):
        """EMAIL-004: QueuedEmail serializes to dict."""
        item = svc.enqueue_email(to_email="a@b.com", subject="S", body_html="<p>B</p>")
        d = item.to_dict()
        assert "id" in d
        assert "to_email" in d
        assert "scheduled_at" in d
        assert "status" in d


# ============================================================================
# EMAIL-005: Email Webhook Receiver
# ============================================================================

class TestEMAIL005_WebhookReceiver:
    """EMAIL-005: Email Webhook Receiver"""

    def test_webhook_delivered(self, svc):
        """EMAIL-005: Process delivery webhook."""
        sent = svc.send_email(to_email="user@test.com", subject="Deliver", body_html="<p>D</p>")
        result = svc.process_webhook(
            WebhookEventType.EMAIL_DELIVERED,
            {"email_id": sent.resend_id},
        )
        assert result["status"] == "processed"
        assert svc.get_sent_email(sent.id).status == EmailStatus.DELIVERED
        assert svc.get_sent_email(sent.id).delivered_at is not None

    def test_webhook_opened(self, svc):
        """EMAIL-005: Process open webhook."""
        sent = svc.send_email(to_email="user@test.com", subject="Open", body_html="<p>O</p>")
        svc.process_webhook(WebhookEventType.EMAIL_OPENED, {"email_id": sent.resend_id})
        email = svc.get_sent_email(sent.id)
        assert email.opened_at is not None
        assert svc._stats["emails_opened"] == 1

    def test_webhook_clicked(self, svc):
        """EMAIL-005: Process click webhook with URL."""
        sent = svc.send_email(to_email="user@test.com", subject="Click", body_html="<p>C</p>")
        svc.process_webhook(
            WebhookEventType.EMAIL_CLICKED,
            {"email_id": sent.resend_id, "url": "https://example.com/page"},
        )
        email = svc.get_sent_email(sent.id)
        assert email.clicked_at is not None
        assert len(email.clicks) == 1
        assert email.clicks[0]["url"] == "https://example.com/page"

    def test_webhook_bounced(self, svc):
        """EMAIL-005: Process bounce webhook."""
        sent = svc.send_email(to_email="bad@test.com", subject="Bounce", body_html="<p>B</p>")
        svc.process_webhook(WebhookEventType.EMAIL_BOUNCED, {"email_id": sent.resend_id})
        email = svc.get_sent_email(sent.id)
        assert email.status == EmailStatus.BOUNCED
        assert email.bounced_at is not None

    def test_webhook_complained_unsubscribes(self, svc):
        """EMAIL-005: Complaint webhook auto-unsubscribes."""
        sent = svc.send_email(to_email="complainer@test.com", subject="Spam", body_html="<p>S</p>")
        svc.process_webhook(WebhookEventType.EMAIL_COMPLAINED, {"email_id": sent.resend_id})
        assert svc.is_unsubscribed("complainer@test.com") is True

    def test_webhook_unknown_email(self, svc):
        """EMAIL-005: Unknown email_id is ignored."""
        result = svc.process_webhook(
            WebhookEventType.EMAIL_DELIVERED,
            {"email_id": "unknown_id"},
        )
        assert result["status"] == "ignored"

    def test_unsubscribe_prevents_sending(self, svc):
        """EMAIL-005: Unsubscribed emails are skipped."""
        svc.unsubscribe("no@thanks.com")
        sent = svc.send_email(to_email="no@thanks.com", subject="Test", body_html="<p>T</p>")
        assert sent.status == EmailStatus.SKIPPED

    def test_get_unsubscribes(self, svc):
        """EMAIL-005: List unsubscribed emails."""
        svc.unsubscribe("a@b.com")
        svc.unsubscribe("c@d.com")
        unsubs = svc.get_unsubscribes()
        assert len(unsubs) == 2

    def test_webhook_events_stored(self, svc):
        """EMAIL-005: Webhook events are stored."""
        sent = svc.send_email(to_email="user@test.com", subject="S", body_html="<p>B</p>")
        svc.process_webhook(WebhookEventType.EMAIL_DELIVERED, {"email_id": sent.resend_id})
        events = svc.get_webhook_events()
        assert len(events) == 1
        assert events[0]["type"] == WebhookEventType.EMAIL_DELIVERED

    def test_webhook_updates_sequence_stats(self, svc):
        """EMAIL-005: Webhook updates sequence and step stats."""
        seq = svc.create_sequence(name="Track")
        step = svc.add_step(seq.id, subject="S", body_html="<p>B</p>")

        sent = svc.send_email(
            to_email="user@test.com",
            subject="S",
            body_html="<p>B</p>",
            sequence_id=seq.id,
            step_id=step.id,
        )
        svc.process_webhook(WebhookEventType.EMAIL_OPENED, {"email_id": sent.resend_id})

        assert step.open_count == 1
        assert seq.total_opened == 1


# ============================================================================
# EMAIL-006: Unified Outreach Service
# ============================================================================

class TestEMAIL006_UnifiedOutreach:
    """EMAIL-006: Unified Outreach Service"""

    def test_log_outreach_touch(self, svc):
        """EMAIL-006: Log an outreach touch."""
        touch = svc.log_outreach_touch(
            contact_id="c1",
            channel="email",
            message="Welcome email body",
            subject="Welcome",
        )
        assert touch.contact_id == "c1"
        assert touch.channel == "email"
        assert touch.sent_at is not None

    def test_get_contact_touches(self, svc):
        """EMAIL-006: Get touches for a contact."""
        svc.log_outreach_touch(contact_id="c1", channel="email", message="Email 1")
        svc.log_outreach_touch(contact_id="c1", channel="dm_instagram", message="DM 1")
        svc.log_outreach_touch(contact_id="c2", channel="email", message="Email 2")

        touches = svc.get_contact_touches("c1")
        assert len(touches) == 2

        email_only = svc.get_contact_touches("c1", channel="email")
        assert len(email_only) == 1

    def test_outreach_summary(self, svc):
        """EMAIL-006: Get outreach summary for a contact."""
        svc.log_outreach_touch(contact_id="c1", channel="email", message="E1")
        svc.log_outreach_touch(contact_id="c1", channel="email", message="E2")
        svc.log_outreach_touch(contact_id="c1", channel="dm_twitter", message="D1")

        summary = svc.get_outreach_summary("c1")
        assert summary["total_touches"] == 3
        assert summary["channels"]["email"]["count"] == 2
        assert summary["channels"]["dm_twitter"]["count"] == 1

    def test_outreach_touch_to_dict(self, svc):
        """EMAIL-006: OutreachTouch serializes to dict."""
        touch = svc.log_outreach_touch(contact_id="c1", channel="email", message="M")
        d = touch.to_dict()
        assert "id" in d
        assert "contact_id" in d
        assert "channel" in d


# ============================================================================
# EMAIL-007: Email Sequence Triggers
# ============================================================================

class TestEMAIL007_SequenceTriggers:
    """EMAIL-007: Email Sequence Triggers"""

    def test_register_trigger(self, svc):
        """EMAIL-007: Register a trigger for a sequence."""
        seq = svc.create_sequence(name="Welcome")
        svc.add_step(seq.id, subject="Hi", body_html="<p>Welcome</p>", delay_value=0)

        trigger = svc.register_trigger(
            sequence_id=seq.id,
            trigger_type=TriggerType.FORM_SUBMIT,
            trigger_config={"form_id": "form_123"},
        )
        assert trigger is not None
        assert trigger.trigger_type == TriggerType.FORM_SUBMIT
        assert trigger.trigger_config["form_id"] == "form_123"

    def test_fire_form_submit_trigger(self, svc):
        """EMAIL-007: Fire form submit trigger enrolls contact."""
        seq = svc.create_sequence(name="Welcome")
        svc.add_step(seq.id, subject="Hi {{first_name}}", body_html="<p>Welcome</p>", delay_value=0)

        svc.register_trigger(
            sequence_id=seq.id,
            trigger_type=TriggerType.FORM_SUBMIT,
            trigger_config={"form_id": "form_123"},
        )

        results = svc.fire_trigger(
            TriggerType.FORM_SUBMIT,
            {"email": "new@user.com", "form_id": "form_123"},
        )
        assert len(results) == 1
        assert results[0]["email"] == "new@user.com"
        assert results[0]["sequence_id"] == seq.id

    def test_fire_lead_tier_trigger(self, svc):
        """EMAIL-007: Fire lead tier change trigger."""
        seq = svc.create_sequence(name="Nurture Warm")
        svc.add_step(seq.id, subject="Congrats!", body_html="<p>You're warm now</p>", delay_value=0)

        svc.register_trigger(
            sequence_id=seq.id,
            trigger_type=TriggerType.LEAD_TIER_CHANGE,
            trigger_config={"to_tier": "warm"},
        )

        results = svc.fire_trigger(
            TriggerType.LEAD_TIER_CHANGE,
            {"email": "lead@test.com", "new_tier": "warm"},
        )
        assert len(results) == 1

    def test_fire_tag_added_trigger(self, svc):
        """EMAIL-007: Fire tag added trigger."""
        seq = svc.create_sequence(name="Tag Sequence")
        svc.add_step(seq.id, subject="Tagged!", body_html="<p>You got tagged</p>", delay_value=0)

        svc.register_trigger(
            sequence_id=seq.id,
            trigger_type=TriggerType.TAG_ADDED,
            trigger_config={"tag": "vip"},
        )

        results = svc.fire_trigger(
            TriggerType.TAG_ADDED,
            {"email": "vip@test.com", "tag": "vip"},
        )
        assert len(results) == 1

    def test_trigger_no_match(self, svc):
        """EMAIL-007: Non-matching trigger config doesn't fire."""
        seq = svc.create_sequence(name="Form Only")
        svc.add_step(seq.id, subject="S", body_html="<p>B</p>", delay_value=0)

        svc.register_trigger(
            sequence_id=seq.id,
            trigger_type=TriggerType.FORM_SUBMIT,
            trigger_config={"form_id": "form_123"},
        )

        results = svc.fire_trigger(
            TriggerType.FORM_SUBMIT,
            {"email": "user@test.com", "form_id": "form_999"},  # Wrong form
        )
        assert len(results) == 0

    def test_trigger_inactive_sequence(self, svc):
        """EMAIL-007: Inactive sequence doesn't enroll."""
        seq = svc.create_sequence(name="Paused", is_active=False)
        svc.add_step(seq.id, subject="S", body_html="<p>B</p>", delay_value=0)

        svc.register_trigger(
            sequence_id=seq.id,
            trigger_type=TriggerType.MANUAL,
        )

        results = svc.fire_trigger(TriggerType.MANUAL, {"email": "user@test.com"})
        assert len(results) == 0

    def test_trigger_increments_stats(self, svc):
        """EMAIL-007: Trigger firing increments stats."""
        seq = svc.create_sequence(name="Count")
        svc.add_step(seq.id, subject="S", body_html="<p>B</p>", delay_value=0)
        svc.register_trigger(sequence_id=seq.id, trigger_type=TriggerType.MANUAL)

        svc.fire_trigger(TriggerType.MANUAL, {"email": "user@test.com"})
        assert svc._stats["triggers_fired"] == 1

    def test_enroll_in_sequence(self, svc):
        """EMAIL-007: Enroll contact in sequence directly."""
        seq = svc.create_sequence(name="Direct Enroll")
        svc.add_step(seq.id, subject="Hi {{first_name}}", body_html="<p>Welcome</p>", delay_value=0)

        enrollment = svc.enroll_in_sequence(
            sequence_id=seq.id,
            email="direct@user.com",
            name="John Doe",
        )
        assert enrollment is not None
        assert enrollment["email"] == "direct@user.com"
        assert enrollment["status"] == "active"

    def test_enroll_duplicate_prevented(self, svc):
        """EMAIL-007: Duplicate enrollment is prevented."""
        seq = svc.create_sequence(name="No Dupes")
        svc.add_step(seq.id, subject="S", body_html="<p>B</p>", delay_value=0)

        svc.enroll_in_sequence(seq.id, email="user@test.com")
        result = svc.enroll_in_sequence(seq.id, email="user@test.com")
        assert result is None  # Duplicate blocked

    def test_get_triggers(self, svc):
        """EMAIL-007: Get triggers for a sequence."""
        seq = svc.create_sequence(name="Triggered")
        svc.add_step(seq.id, subject="S", body_html="<p>B</p>", delay_value=0)

        svc.register_trigger(seq.id, TriggerType.FORM_SUBMIT)
        svc.register_trigger(seq.id, TriggerType.TAG_ADDED)

        triggers = svc.get_triggers(sequence_id=seq.id)
        assert len(triggers) == 2

    def test_trigger_to_dict(self, svc):
        """EMAIL-007: TriggerRegistration serializes to dict."""
        seq = svc.create_sequence(name="S")
        svc.add_step(seq.id, subject="S", body_html="<p>B</p>", delay_value=0)

        trigger = svc.register_trigger(seq.id, TriggerType.MANUAL)
        d = trigger.to_dict()
        assert "id" in d
        assert "trigger_type" in d
        assert "fire_count" in d


# ============================================================================
# EMAIL-008: Email Analytics Dashboard
# ============================================================================

class TestEMAIL008_AnalyticsDashboard:
    """EMAIL-008: Email Analytics Dashboard"""

    def test_email_analytics(self, svc):
        """EMAIL-008: Get overall email analytics."""
        # Send some emails and simulate events
        e1 = svc.send_email(to_email="a@b.com", subject="S1", body_html="<p>1</p>")
        e2 = svc.send_email(to_email="c@d.com", subject="S2", body_html="<p>2</p>")
        e3 = svc.send_email(to_email="e@f.com", subject="S3", body_html="<p>3</p>")

        svc.process_webhook(WebhookEventType.EMAIL_DELIVERED, {"email_id": e1.resend_id})
        svc.process_webhook(WebhookEventType.EMAIL_DELIVERED, {"email_id": e2.resend_id})
        svc.process_webhook(WebhookEventType.EMAIL_OPENED, {"email_id": e1.resend_id})
        svc.process_webhook(WebhookEventType.EMAIL_CLICKED, {"email_id": e1.resend_id})

        analytics = svc.get_email_analytics()
        assert analytics["total_sent"] == 3
        assert analytics["total_delivered"] == 2
        assert analytics["total_opened"] == 1
        assert analytics["total_clicked"] == 1
        assert analytics["open_rate"] > 0
        assert analytics["click_rate"] > 0

    def test_sequence_analytics(self, svc):
        """EMAIL-008: Get sequence-level analytics."""
        seq = svc.create_sequence(name="Analytics Test")
        step = svc.add_step(seq.id, subject="S", body_html="<p>B</p>")

        e = svc.send_email(
            to_email="user@test.com",
            subject="S",
            body_html="<p>B</p>",
            sequence_id=seq.id,
            step_id=step.id,
        )
        seq.total_sent += 1
        step.sent_count += 1

        svc.process_webhook(WebhookEventType.EMAIL_OPENED, {"email_id": e.resend_id})

        analytics = svc.get_sequence_analytics(seq.id)
        assert analytics is not None
        assert analytics["total_sent"] == 1
        assert analytics["total_opened"] == 1
        assert analytics["open_rate"] == 100.0
        assert len(analytics["steps"]) == 1
        assert analytics["steps"][0]["open_count"] == 1

    def test_queue_stats(self, svc):
        """EMAIL-008: Get queue statistics."""
        svc.enqueue_email(to_email="a@b.com", subject="S1", body_html="<p>1</p>")
        svc.enqueue_email(to_email="c@d.com", subject="S2", body_html="<p>2</p>")
        q3 = svc.enqueue_email(to_email="e@f.com", subject="S3", body_html="<p>3</p>")
        q3.status = EmailStatus.SENT

        stats = svc.get_queue_stats()
        assert stats["total"] == 3
        assert stats["pending"] == 2
        assert stats["sent"] == 1

    def test_empty_analytics(self, svc):
        """EMAIL-008: Empty analytics returns zeros."""
        analytics = svc.get_email_analytics()
        assert analytics["total_sent"] == 0
        assert analytics["open_rate"] == 0
        assert analytics["click_rate"] == 0

    def test_get_stats(self, svc):
        """EMAIL-008: Overall service stats."""
        svc.send_email(to_email="a@b.com", subject="S", body_html="<p>B</p>")
        svc.create_sequence(name="S")
        svc.create_template(name="T")

        stats = svc.get_stats()
        assert stats["emails_sent"] == 1
        assert stats["sequences"] == 1
        assert stats["templates"] == 1
        assert "config" in stats


# ============================================================================
# Service-level tests
# ============================================================================

class TestEmailSequenceServiceGeneral:
    """General EmailSequenceService tests."""

    def test_singleton_pattern(self):
        """EmailSequenceService uses singleton pattern."""
        EmailSequenceService.reset_instance()
        s1 = get_email_sequence_service(resend_api_key="key1")
        s2 = get_email_sequence_service()
        assert s1 is s2
        EmailSequenceService.reset_instance()

    def test_reset_instance(self):
        """Reset instance creates new service."""
        EmailSequenceService.reset_instance()
        s1 = get_email_sequence_service(resend_api_key="key1")
        EmailSequenceService.reset_instance()
        s2 = get_email_sequence_service(resend_api_key="key2")
        assert s1 is not s2
        EmailSequenceService.reset_instance()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
