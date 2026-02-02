"""
Tests for Lead Form Service (LEAD-001 through LEAD-008)
=======================================================
Validates form builder, submission handler, lead scoring, management
dashboard, public waitlist, CSV import/export, webhook integration,
and email sequence triggering.
"""
import pytest
from services.lead_form_service import (
    LeadFormService,
    get_lead_form_service,
    LeadForm,
    Lead,
    WaitlistEntry,
    LeadWebhook,
    LeadFieldType,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def svc():
    """Fresh LeadFormService for every test."""
    LeadFormService.reset_instance()
    return LeadFormService()


@pytest.fixture
def sample_form(svc):
    """Create a sample form with questions and scoring rules."""
    return svc.create_form(
        name="Beta Signup",
        form_type="waitlist",
        slug="beta-signup",
        questions=[
            {"name": "email", "type": "email", "required": True},
            {"name": "name", "type": "text", "required": True},
            {"name": "company", "type": "text", "required": False},
            {"name": "role", "type": "select", "required": False},
            {"name": "budget", "type": "number", "required": False},
        ],
        scoring_rules=[
            {"field": "company", "operator": "exists", "points": 20},
            {"field": "role", "operator": "equals", "value": "CTO", "points": 30},
            {"field": "budget", "operator": "gt", "value": "1000", "points": 50},
        ],
        email_sequence_id="seq_welcome_001",
        webhook_url="https://hooks.example.com/leads",
    )


# ============================================================================
# LEAD-001: Lead Form Builder
# ============================================================================

class TestLEAD001_FormBuilder:
    """LEAD-001: Lead Form Builder"""

    def test_create_form(self, svc):
        """LEAD-001: Should create a form with all fields populated."""
        form = svc.create_form(name="Test Form", form_type="general")
        assert form.id is not None
        assert form.name == "Test Form"
        assert form.form_type == "general"
        assert form.is_active is True
        assert form.submission_count == 0

    def test_create_form_auto_slug(self, svc):
        """LEAD-001: Should auto-generate a slug from the name."""
        form = svc.create_form(name="My Great Form")
        assert form.slug == "my-great-form"

    def test_create_form_custom_slug(self, svc):
        """LEAD-001: Should accept a custom slug."""
        form = svc.create_form(name="Test", slug="custom-slug")
        assert form.slug == "custom-slug"

    def test_get_form_by_id(self, svc, sample_form):
        """LEAD-001: Should retrieve a form by ID."""
        fetched = svc.get_form(sample_form.id)
        assert fetched is not None
        assert fetched.id == sample_form.id
        assert fetched.name == "Beta Signup"

    def test_get_form_by_slug(self, svc, sample_form):
        """LEAD-001: Should retrieve a form by slug."""
        fetched = svc.get_form_by_slug("beta-signup")
        assert fetched is not None
        assert fetched.id == sample_form.id

    def test_get_form_by_slug_not_found(self, svc):
        """LEAD-001: Should return None for unknown slug."""
        assert svc.get_form_by_slug("nonexistent") is None

    def test_list_forms(self, svc):
        """LEAD-001: Should list all forms."""
        svc.create_form(name="Form A")
        svc.create_form(name="Form B")
        assert len(svc.list_forms()) == 2

    def test_list_forms_active_only(self, svc):
        """LEAD-001: Should filter inactive forms."""
        f1 = svc.create_form(name="Active Form")
        f2 = svc.create_form(name="Inactive Form")
        svc.update_form(f2.id, is_active=False)
        active = svc.list_forms(active_only=True)
        assert len(active) == 1
        assert active[0].id == f1.id

    def test_update_form(self, svc, sample_form):
        """LEAD-001: Should update form fields."""
        updated = svc.update_form(sample_form.id, name="Updated Name", thank_you_message="Thanks!")
        assert updated.name == "Updated Name"
        assert updated.thank_you_message == "Thanks!"

    def test_update_form_not_found(self, svc):
        """LEAD-001: Should return None for unknown form ID."""
        assert svc.update_form("nonexistent", name="X") is None

    def test_delete_form(self, svc, sample_form):
        """LEAD-001: Should delete a form."""
        assert svc.delete_form(sample_form.id) is True
        assert svc.get_form(sample_form.id) is None

    def test_delete_form_not_found(self, svc):
        """LEAD-001: Should return False for unknown form ID."""
        assert svc.delete_form("nonexistent") is False

    def test_form_to_dict(self, svc, sample_form):
        """LEAD-001: Form should serialize to dict."""
        d = sample_form.to_dict()
        assert d["name"] == "Beta Signup"
        assert "questions" in d
        assert "scoring_rules" in d
        assert "is_active" in d


# ============================================================================
# LEAD-002: Lead Form Submission Handler
# ============================================================================

class TestLEAD002_SubmissionHandler:
    """LEAD-002: Lead Form Submission Handler"""

    def test_submit_form_basic(self, svc, sample_form):
        """LEAD-002: Should create a lead from a valid submission."""
        lead = svc.submit_form(sample_form.id, {"email": "user@example.com", "name": "Jane"})
        assert lead.id is not None
        assert lead.email == "user@example.com"
        assert lead.name == "Jane"
        assert lead.form_id == sample_form.id

    def test_submit_form_bumps_count(self, svc, sample_form):
        """LEAD-002: Submission should increment submission_count."""
        svc.submit_form(sample_form.id, {"email": "a@test.com", "name": "A"})
        svc.submit_form(sample_form.id, {"email": "b@test.com", "name": "B"})
        form = svc.get_form(sample_form.id)
        assert form.submission_count == 2

    def test_submit_form_missing_email(self, svc, sample_form):
        """LEAD-002: Should reject submission without email."""
        with pytest.raises(ValueError, match="email"):
            svc.submit_form(sample_form.id, {"name": "No Email"})

    def test_submit_form_invalid_email(self, svc, sample_form):
        """LEAD-002: Should reject submission with invalid email."""
        with pytest.raises(ValueError, match="email"):
            svc.submit_form(sample_form.id, {"email": "not-an-email", "name": "Bad"})

    def test_submit_form_not_found(self, svc):
        """LEAD-002: Should reject submission for unknown form."""
        with pytest.raises(ValueError, match="Form not found"):
            svc.submit_form("nonexistent", {"email": "user@test.com"})

    def test_submit_form_inactive(self, svc, sample_form):
        """LEAD-002: Should reject submission for inactive form."""
        svc.update_form(sample_form.id, is_active=False)
        with pytest.raises(ValueError, match="inactive"):
            svc.submit_form(sample_form.id, {"email": "user@test.com", "name": "X"})

    def test_submit_form_required_field_missing(self, svc, sample_form):
        """LEAD-002: Should reject when a required question is missing."""
        with pytest.raises(ValueError, match="Required field missing"):
            svc.submit_form(sample_form.id, {"email": "user@test.com"})  # 'name' is required

    def test_submit_form_stores_form_data(self, svc, sample_form):
        """LEAD-002: Should store all submitted data in form_data."""
        lead = svc.submit_form(
            sample_form.id,
            {"email": "data@test.com", "name": "Data", "company": "Acme", "role": "CTO"},
        )
        assert lead.form_data["company"] == "Acme"
        assert lead.form_data["role"] == "CTO"

    def test_lead_to_dict(self, svc, sample_form):
        """LEAD-002: Lead should serialize to dict."""
        lead = svc.submit_form(sample_form.id, {"email": "d@test.com", "name": "Dict"})
        d = lead.to_dict()
        assert "id" in d
        assert "email" in d
        assert "lead_score" in d
        assert "tags" in d


# ============================================================================
# LEAD-003: Lead Scoring with FATE
# ============================================================================

class TestLEAD003_LeadScoring:
    """LEAD-003: Lead Scoring with FATE"""

    def test_score_lead_cold(self, svc, sample_form):
        """LEAD-003: Lead with no matching rules should be cold."""
        lead = svc.submit_form(sample_form.id, {"email": "cold@test.com", "name": "Cold"})
        scored = svc.score_lead(lead.id)
        assert scored.lead_tier == "cold"
        assert scored.lead_score < 40

    def test_score_lead_warm(self, svc, sample_form):
        """LEAD-003: Lead matching some rules should be warm (40-79)."""
        lead = svc.submit_form(sample_form.id, {
            "email": "warm@test.com",
            "name": "Warm",
            "company": "Acme Inc",
            "role": "CTO",
        })
        scored = svc.score_lead(lead.id)
        # company exists (20) + role=CTO (30) = 50 => warm
        assert scored.lead_score == 50
        assert scored.lead_tier == "warm"

    def test_score_lead_hot(self, svc, sample_form):
        """LEAD-003: Lead matching many rules should be hot (>=80)."""
        lead = svc.submit_form(sample_form.id, {
            "email": "hot@test.com",
            "name": "Hot",
            "company": "BigCorp",
            "role": "CTO",
            "budget": "5000",
        })
        scored = svc.score_lead(lead.id)
        # company exists (20) + role=CTO (30) + budget>1000 (50) = 100 => hot
        assert scored.lead_score == 100
        assert scored.lead_tier == "hot"

    def test_score_lead_breakdown(self, svc, sample_form):
        """LEAD-003: Should return detailed scoring breakdown."""
        lead = svc.submit_form(sample_form.id, {
            "email": "bd@test.com", "name": "Breakdown", "company": "Test",
        })
        scored = svc.score_lead(lead.id)
        assert "company" in scored.scoring_breakdown
        assert scored.scoring_breakdown["company"]["matched"] is True
        assert scored.scoring_breakdown["company"]["points"] == 20

    def test_score_lead_not_found(self, svc):
        """LEAD-003: Should raise ValueError for unknown lead."""
        with pytest.raises(ValueError, match="Lead not found"):
            svc.score_lead("nonexistent")

    def test_score_lead_contains_operator(self, svc):
        """LEAD-003: 'contains' operator should match substrings."""
        form = svc.create_form(
            name="Contains Test",
            scoring_rules=[{"field": "bio", "operator": "contains", "value": "engineer", "points": 40}],
        )
        lead = svc.submit_form(form.id, {"email": "eng@test.com", "bio": "Senior Engineer at Acme"})
        scored = svc.score_lead(lead.id)
        assert scored.lead_score == 40

    def test_score_lead_lt_operator(self, svc):
        """LEAD-003: 'lt' operator should compare numbers."""
        form = svc.create_form(
            name="LT Test",
            scoring_rules=[{"field": "age", "operator": "lt", "value": "30", "points": 25}],
        )
        lead = svc.submit_form(form.id, {"email": "young@test.com", "age": "25"})
        scored = svc.score_lead(lead.id)
        assert scored.lead_score == 25


# ============================================================================
# LEAD-004: Lead Management Dashboard
# ============================================================================

class TestLEAD004_Management:
    """LEAD-004: Lead Management Dashboard"""

    def test_get_lead(self, svc, sample_form):
        """LEAD-004: Should retrieve a lead by ID."""
        lead = svc.submit_form(sample_form.id, {"email": "get@test.com", "name": "Get"})
        fetched = svc.get_lead(lead.id)
        assert fetched is not None
        assert fetched.email == "get@test.com"

    def test_list_leads(self, svc, sample_form):
        """LEAD-004: Should list all leads."""
        svc.submit_form(sample_form.id, {"email": "a@test.com", "name": "A"})
        svc.submit_form(sample_form.id, {"email": "b@test.com", "name": "B"})
        assert len(svc.list_leads()) == 2

    def test_list_leads_by_form(self, svc):
        """LEAD-004: Should filter leads by form_id."""
        f1 = svc.create_form(name="Form 1")
        f2 = svc.create_form(name="Form 2")
        svc.submit_form(f1.id, {"email": "a@test.com"})
        svc.submit_form(f2.id, {"email": "b@test.com"})
        svc.submit_form(f1.id, {"email": "c@test.com"})
        assert len(svc.list_leads(form_id=f1.id)) == 2
        assert len(svc.list_leads(form_id=f2.id)) == 1

    def test_update_lead_status(self, svc, sample_form):
        """LEAD-004: Should update lead status."""
        lead = svc.submit_form(sample_form.id, {"email": "st@test.com", "name": "Status"})
        updated = svc.update_lead_status(lead.id, "contacted")
        assert updated.status == "contacted"

    def test_update_lead_status_converted(self, svc, sample_form):
        """LEAD-004: Converting a lead should set converted_at and bump form count."""
        lead = svc.submit_form(sample_form.id, {"email": "conv@test.com", "name": "Convert"})
        svc.update_lead_status(lead.id, "converted")
        assert lead.converted_at is not None
        form = svc.get_form(sample_form.id)
        assert form.conversion_count == 1

    def test_update_lead_status_invalid(self, svc, sample_form):
        """LEAD-004: Should reject invalid status values."""
        lead = svc.submit_form(sample_form.id, {"email": "inv@test.com", "name": "Invalid"})
        with pytest.raises(ValueError, match="Invalid status"):
            svc.update_lead_status(lead.id, "bogus")

    def test_add_remove_tag(self, svc, sample_form):
        """LEAD-004: Should add and remove tags on a lead."""
        lead = svc.submit_form(sample_form.id, {"email": "tag@test.com", "name": "Tag"})
        svc.add_lead_tag(lead.id, "vip")
        svc.add_lead_tag(lead.id, "enterprise")
        assert "vip" in lead.tags
        assert "enterprise" in lead.tags
        svc.remove_lead_tag(lead.id, "vip")
        assert "vip" not in lead.tags
        assert "enterprise" in lead.tags

    def test_add_duplicate_tag(self, svc, sample_form):
        """LEAD-004: Adding the same tag twice should not duplicate."""
        lead = svc.submit_form(sample_form.id, {"email": "dup@test.com", "name": "Dup"})
        svc.add_lead_tag(lead.id, "vip")
        svc.add_lead_tag(lead.id, "vip")
        assert lead.tags.count("vip") == 1

    def test_filter_leads_by_tier(self, svc, sample_form):
        """LEAD-004: Should filter leads by tier."""
        l1 = svc.submit_form(sample_form.id, {
            "email": "hot@test.com", "name": "Hot", "company": "X", "role": "CTO", "budget": "5000",
        })
        l2 = svc.submit_form(sample_form.id, {"email": "cold@test.com", "name": "Cold"})
        svc.score_lead(l1.id)
        svc.score_lead(l2.id)
        hot = svc.filter_leads(tier="hot")
        assert len(hot) == 1
        assert hot[0].email == "hot@test.com"

    def test_filter_leads_by_min_score(self, svc, sample_form):
        """LEAD-004: Should filter leads by minimum score."""
        l1 = svc.submit_form(sample_form.id, {
            "email": "high@test.com", "name": "High", "company": "Y", "role": "CTO",
        })
        l2 = svc.submit_form(sample_form.id, {"email": "low@test.com", "name": "Low"})
        svc.score_lead(l1.id)
        svc.score_lead(l2.id)
        results = svc.filter_leads(min_score=40)
        assert len(results) == 1
        assert results[0].email == "high@test.com"

    def test_filter_leads_by_tags(self, svc, sample_form):
        """LEAD-004: Should filter leads by tags."""
        l1 = svc.submit_form(sample_form.id, {"email": "t1@test.com", "name": "T1"})
        l2 = svc.submit_form(sample_form.id, {"email": "t2@test.com", "name": "T2"})
        svc.add_lead_tag(l1.id, "vip")
        svc.add_lead_tag(l1.id, "enterprise")
        svc.add_lead_tag(l2.id, "vip")
        results = svc.filter_leads(tags=["vip", "enterprise"])
        assert len(results) == 1
        assert results[0].id == l1.id


# ============================================================================
# LEAD-005: Public Waitlist API
# ============================================================================

class TestLEAD005_Waitlist:
    """LEAD-005: Public Waitlist API"""

    def test_join_waitlist(self, svc, sample_form):
        """LEAD-005: Should create a waitlist entry with position."""
        entry = svc.join_waitlist(sample_form.id, "wait1@test.com", "Waiter 1")
        assert entry.position == 1
        assert entry.email == "wait1@test.com"
        assert entry.status == "pending"
        assert len(entry.referral_code) > 0

    def test_waitlist_position_increments(self, svc, sample_form):
        """LEAD-005: Positions should auto-increment."""
        e1 = svc.join_waitlist(sample_form.id, "w1@test.com")
        e2 = svc.join_waitlist(sample_form.id, "w2@test.com")
        e3 = svc.join_waitlist(sample_form.id, "w3@test.com")
        assert e1.position == 1
        assert e2.position == 2
        assert e3.position == 3

    def test_waitlist_duplicate_email(self, svc, sample_form):
        """LEAD-005: Should reject duplicate email on same form."""
        svc.join_waitlist(sample_form.id, "dup@test.com")
        with pytest.raises(ValueError, match="already on waitlist"):
            svc.join_waitlist(sample_form.id, "dup@test.com")

    def test_get_waitlist_position(self, svc, sample_form):
        """LEAD-005: Should return position info."""
        e1 = svc.join_waitlist(sample_form.id, "pos1@test.com")
        svc.join_waitlist(sample_form.id, "pos2@test.com")
        info = svc.get_waitlist_position(e1.id)
        assert info["position"] == 1
        assert info["total"] == 2
        assert info["status"] == "pending"
        assert "referral_code" in info

    def test_get_waitlist_position_not_found(self, svc):
        """LEAD-005: Should return None for unknown entry."""
        assert svc.get_waitlist_position("nonexistent") is None

    def test_list_waitlist_ordered(self, svc, sample_form):
        """LEAD-005: Should list waitlist entries in position order."""
        svc.join_waitlist(sample_form.id, "a@test.com")
        svc.join_waitlist(sample_form.id, "b@test.com")
        svc.join_waitlist(sample_form.id, "c@test.com")
        entries = svc.list_waitlist(sample_form.id)
        assert len(entries) == 3
        assert entries[0].position < entries[1].position < entries[2].position

    def test_approve_waitlist_entry(self, svc, sample_form):
        """LEAD-005: Should approve a waitlist entry."""
        entry = svc.join_waitlist(sample_form.id, "approve@test.com")
        approved = svc.approve_waitlist_entry(entry.id)
        assert approved.status == "approved"

    def test_approve_waitlist_not_found(self, svc):
        """LEAD-005: Should return None for unknown entry."""
        assert svc.approve_waitlist_entry("nonexistent") is None

    def test_waitlist_referral(self, svc, sample_form):
        """LEAD-005: Should track referral code from another entry."""
        e1 = svc.join_waitlist(sample_form.id, "ref1@test.com")
        e2 = svc.join_waitlist(sample_form.id, "ref2@test.com", referred_by=e1.referral_code)
        assert e2.referred_by == e1.referral_code

    def test_waitlist_form_not_found(self, svc):
        """LEAD-005: Should raise for unknown form."""
        with pytest.raises(ValueError, match="Form not found"):
            svc.join_waitlist("nonexistent", "x@test.com")

    def test_waitlist_entry_to_dict(self, svc, sample_form):
        """LEAD-005: WaitlistEntry should serialize to dict."""
        entry = svc.join_waitlist(sample_form.id, "dict@test.com")
        d = entry.to_dict()
        assert "id" in d
        assert "position" in d
        assert "referral_code" in d


# ============================================================================
# LEAD-006: Lead CSV Import / Export
# ============================================================================

class TestLEAD006_CSVImportExport:
    """LEAD-006: Lead CSV Import/Export"""

    def test_export_leads_csv(self, svc, sample_form):
        """LEAD-006: Should export leads to CSV string."""
        svc.submit_form(sample_form.id, {"email": "csv1@test.com", "name": "CSV1"})
        svc.submit_form(sample_form.id, {"email": "csv2@test.com", "name": "CSV2"})
        csv_str = svc.export_leads_csv()
        assert "csv1@test.com" in csv_str
        assert "csv2@test.com" in csv_str
        assert "email" in csv_str  # header

    def test_export_leads_csv_by_form(self, svc):
        """LEAD-006: Should export leads filtered by form."""
        f1 = svc.create_form(name="F1")
        f2 = svc.create_form(name="F2")
        svc.submit_form(f1.id, {"email": "f1@test.com"})
        svc.submit_form(f2.id, {"email": "f2@test.com"})
        csv_str = svc.export_leads_csv(form_id=f1.id)
        assert "f1@test.com" in csv_str
        assert "f2@test.com" not in csv_str

    def test_import_leads_csv(self, svc, sample_form):
        """LEAD-006: Should import leads from CSV string."""
        csv_text = "email,name,phone\nimport1@test.com,Import One,555-1234\nimport2@test.com,Import Two,555-5678\n"
        imported = svc.import_leads_csv(csv_text, sample_form.id)
        assert len(imported) == 2
        assert imported[0].email == "import1@test.com"
        assert imported[1].name == "Import Two"

    def test_import_leads_csv_with_tags(self, svc, sample_form):
        """LEAD-006: Should parse semicolon-separated tags."""
        csv_text = "email,name,tags\ntags@test.com,Tags,vip;enterprise\n"
        imported = svc.import_leads_csv(csv_text, sample_form.id)
        assert "vip" in imported[0].tags
        assert "enterprise" in imported[0].tags

    def test_import_leads_csv_form_not_found(self, svc):
        """LEAD-006: Should raise for unknown form."""
        with pytest.raises(ValueError, match="Form not found"):
            svc.import_leads_csv("email\ntest@x.com\n", "nonexistent")

    def test_roundtrip_csv(self, svc, sample_form):
        """LEAD-006: Export then import should preserve data."""
        svc.submit_form(sample_form.id, {"email": "round@test.com", "name": "Round"})
        csv_str = svc.export_leads_csv(form_id=sample_form.id)
        # Create a new form to import into
        f2 = svc.create_form(name="Import Target")
        imported = svc.import_leads_csv(csv_str, f2.id)
        assert len(imported) == 1
        assert imported[0].email == "round@test.com"

    def test_import_skips_empty_email(self, svc, sample_form):
        """LEAD-006: Should skip rows with empty email."""
        csv_text = "email,name\nvalid@test.com,Valid\n,Empty\n"
        imported = svc.import_leads_csv(csv_text, sample_form.id)
        assert len(imported) == 1


# ============================================================================
# LEAD-007: Lead Webhook Integration
# ============================================================================

class TestLEAD007_Webhooks:
    """LEAD-007: Lead Webhook Integration"""

    def test_register_webhook(self, svc, sample_form):
        """LEAD-007: Should register a webhook."""
        wh = svc.register_webhook(sample_form.id, "https://hooks.test.com/lead", ["submission", "scored"])
        assert wh.id is not None
        assert wh.url == "https://hooks.test.com/lead"
        assert "submission" in wh.events

    def test_fire_webhooks_on_submission(self, svc, sample_form):
        """LEAD-007: Should fire webhook on form submission."""
        svc.register_webhook(sample_form.id, "https://hooks.test.com/a", ["submission"])
        svc.submit_form(sample_form.id, {"email": "hook@test.com", "name": "Hook"})
        assert len(svc._fired_webhooks) >= 1
        assert svc._fired_webhooks[0]["event"] == "submission"

    def test_fire_webhooks_event_filter(self, svc, sample_form):
        """LEAD-007: Should only fire for matching events."""
        svc.register_webhook(sample_form.id, "https://hooks.test.com/b", ["scored"])
        svc.submit_form(sample_form.id, {"email": "filter@test.com", "name": "Filter"})
        # No "scored" event yet, only "submission"
        scored_fires = [f for f in svc._fired_webhooks if f["event"] == "scored"]
        assert len(scored_fires) == 0

    def test_fire_webhooks_increments_count(self, svc, sample_form):
        """LEAD-007: Should increment fire_count on webhook."""
        wh = svc.register_webhook(sample_form.id, "https://hooks.test.com/c", ["submission"])
        svc.submit_form(sample_form.id, {"email": "count1@test.com", "name": "C1"})
        svc.submit_form(sample_form.id, {"email": "count2@test.com", "name": "C2"})
        updated_wh = svc._webhooks[wh.id]
        assert updated_wh.fire_count == 2
        assert updated_wh.last_fired_at is not None

    def test_list_webhooks(self, svc, sample_form):
        """LEAD-007: Should list webhooks for a form."""
        svc.register_webhook(sample_form.id, "https://a.com", ["submission"])
        svc.register_webhook(sample_form.id, "https://b.com", ["scored"])
        f2 = svc.create_form(name="Other")
        svc.register_webhook(f2.id, "https://c.com", ["submission"])
        assert len(svc.list_webhooks(form_id=sample_form.id)) == 2
        assert len(svc.list_webhooks()) == 3

    def test_inactive_webhook_not_fired(self, svc, sample_form):
        """LEAD-007: Inactive webhooks should not fire."""
        wh = svc.register_webhook(sample_form.id, "https://inactive.test.com", ["submission"])
        wh.is_active = False
        svc.submit_form(sample_form.id, {"email": "inactive@test.com", "name": "Inactive"})
        assert len(svc._fired_webhooks) == 0

    def test_webhook_to_dict(self, svc, sample_form):
        """LEAD-007: LeadWebhook should serialize to dict."""
        wh = svc.register_webhook(sample_form.id, "https://dict.com", ["submission"])
        d = wh.to_dict()
        assert "id" in d
        assert "url" in d
        assert "events" in d
        assert "fire_count" in d


# ============================================================================
# LEAD-008: Lead Email Sequence Trigger
# ============================================================================

class TestLEAD008_EmailSequenceTrigger:
    """LEAD-008: Lead Email Sequence Trigger"""

    def test_trigger_warm_lead(self, svc, sample_form):
        """LEAD-008: Warm lead should trigger email sequence."""
        lead = svc.submit_form(sample_form.id, {
            "email": "warm@test.com", "name": "Warm", "company": "Co", "role": "CTO",
        })
        svc.score_lead(lead.id)  # 50 points -> warm
        result = svc.trigger_email_sequence(lead.id, tier_threshold="warm")
        assert result is not None
        assert result["email_sequence_id"] == "seq_welcome_001"
        assert result["lead_tier"] == "warm"

    def test_trigger_hot_lead(self, svc, sample_form):
        """LEAD-008: Hot lead should trigger at warm threshold."""
        lead = svc.submit_form(sample_form.id, {
            "email": "hot@test.com", "name": "Hot",
            "company": "BigCo", "role": "CTO", "budget": "5000",
        })
        svc.score_lead(lead.id)  # 100 points -> hot
        result = svc.trigger_email_sequence(lead.id, tier_threshold="warm")
        assert result is not None
        assert result["lead_tier"] == "hot"

    def test_trigger_cold_lead_rejected(self, svc, sample_form):
        """LEAD-008: Cold lead should not trigger at warm threshold."""
        lead = svc.submit_form(sample_form.id, {"email": "cold@test.com", "name": "Cold"})
        svc.score_lead(lead.id)  # 0 points -> cold
        result = svc.trigger_email_sequence(lead.id, tier_threshold="warm")
        assert result is None

    def test_trigger_no_sequence_configured(self, svc):
        """LEAD-008: Should return None when form has no email_sequence_id."""
        form = svc.create_form(name="No Seq")
        lead = svc.submit_form(form.id, {"email": "noseq@test.com"})
        lead.lead_tier = "hot"
        result = svc.trigger_email_sequence(lead.id, tier_threshold="warm")
        assert result is None

    def test_trigger_lead_not_found(self, svc):
        """LEAD-008: Should return None for unknown lead."""
        assert svc.trigger_email_sequence("nonexistent") is None

    def test_trigger_cold_threshold(self, svc, sample_form):
        """LEAD-008: Cold threshold should trigger for any lead."""
        lead = svc.submit_form(sample_form.id, {"email": "any@test.com", "name": "Any"})
        svc.score_lead(lead.id)
        result = svc.trigger_email_sequence(lead.id, tier_threshold="cold")
        assert result is not None

    def test_trigger_enrollment_info(self, svc, sample_form):
        """LEAD-008: Enrollment dict should contain required fields."""
        lead = svc.submit_form(sample_form.id, {
            "email": "info@test.com", "name": "Info", "company": "Co", "role": "CTO",
        })
        svc.score_lead(lead.id)
        result = svc.trigger_email_sequence(lead.id, tier_threshold="warm")
        assert result is not None
        assert "lead_id" in result
        assert "email" in result
        assert "enrolled_at" in result
        assert "form_id" in result


# ============================================================================
# Singleton & Field Type Tests
# ============================================================================

class TestSingletonAndFieldTypes:
    """Cross-cutting singleton and enum tests."""

    def test_singleton_pattern(self):
        """Should use singleton pattern."""
        LeadFormService.reset_instance()
        svc1 = get_lead_form_service()
        svc2 = get_lead_form_service()
        assert svc1 is svc2
        LeadFormService.reset_instance()

    def test_reset_instance(self):
        """reset_instance should clear the singleton."""
        LeadFormService.reset_instance()
        svc1 = get_lead_form_service()
        LeadFormService.reset_instance()
        svc2 = get_lead_form_service()
        assert svc1 is not svc2
        LeadFormService.reset_instance()

    def test_field_type_enum(self):
        """LeadFieldType enum should have all types."""
        assert LeadFieldType.TEXT == "text"
        assert LeadFieldType.EMAIL == "email"
        assert LeadFieldType.PHONE == "phone"
        assert LeadFieldType.SELECT == "select"
        assert LeadFieldType.CHECKBOX == "checkbox"
        assert LeadFieldType.TEXTAREA == "textarea"
        assert LeadFieldType.NUMBER == "number"
        assert LeadFieldType.URL == "url"

    def test_lead_default_values(self):
        """Lead dataclass should have correct defaults."""
        lead = Lead()
        assert lead.lead_score == 0.0
        assert lead.lead_tier == "cold"
        assert lead.status == "new"
        assert lead.tags == []
        assert lead.form_data == {}

    def test_waitlist_entry_default_values(self):
        """WaitlistEntry dataclass should have correct defaults."""
        entry = WaitlistEntry()
        assert entry.status == "pending"
        assert entry.position == 0
        assert len(entry.referral_code) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
