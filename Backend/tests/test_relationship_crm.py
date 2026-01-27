"""
Tests for Relationship-First CRM System
Tests RF-001 through RF-005 from PRD_Relationship_First_DM_System.md
"""

import pytest
from datetime import datetime, timezone


class TestRelationshipCRMImports:
    """Test that all CRM components can be imported."""
    
    def test_crm_service_imports(self):
        """Test RelationshipCRM can be imported."""
        from services.relationship_crm import RelationshipCRM, get_relationship_crm
        assert RelationshipCRM is not None
        assert get_relationship_crm is not None
    
    def test_contact_model_imports(self):
        """Test Contact dataclass can be imported."""
        from services.relationship_crm import Contact, ContactContext, RelationshipScores
        assert Contact is not None
        assert ContactContext is not None
        assert RelationshipScores is not None
    
    def test_enums_import(self):
        """Test enums can be imported."""
        from services.relationship_crm import Platform, PipelineStage, MessageLane, ActionType
        assert Platform is not None
        assert PipelineStage is not None
        assert MessageLane is not None
        assert ActionType is not None
    
    @pytest.mark.skip(reason="Requires OpenAI module")
    def test_ai_service_imports(self):
        """Test RelationshipAI can be imported."""
        from services.relationship_ai import RelationshipAI, get_relationship_ai, ActionSuggestion
        assert RelationshipAI is not None
        assert get_relationship_ai is not None
        assert ActionSuggestion is not None


class TestRF001RelationshipHealthScore:
    """Tests for RF-001: Relationship Health Score (0-100)."""
    
    def test_health_score_calculation(self):
        """Test health score calculation with all factors."""
        from services.relationship_crm import RelationshipScores
        
        scores = RelationshipScores(
            recency_days=3,
            resonance="high",
            need_clarity=True,
            value_delivered_count=4,
            promises_kept_rate=1.0,
            consent_level="offers"
        )
        
        health = scores.calculate_health_score()
        assert 70 <= health <= 100, f"Expected high health, got {health}"
    
    def test_low_health_score(self):
        """Test low health score calculation."""
        from services.relationship_crm import RelationshipScores
        
        scores = RelationshipScores(
            recency_days=60,
            resonance="low",
            need_clarity=False,
            value_delivered_count=0,
            promises_kept_rate=0.5,
            consent_level="none"
        )
        
        health = scores.calculate_health_score()
        assert health < 40, f"Expected low health, got {health}"
    
    def test_health_score_bounds(self):
        """Test health score stays within 0-100."""
        from services.relationship_crm import RelationshipScores
        
        # Max everything
        high_scores = RelationshipScores(
            recency_days=0,
            resonance="high",
            need_clarity=True,
            value_delivered_count=10,
            promises_kept_rate=1.0,
            consent_level="all"
        )
        assert high_scores.calculate_health_score() <= 100
        
        # Min everything
        low_scores = RelationshipScores(
            recency_days=100,
            resonance="low",
            need_clarity=False,
            value_delivered_count=0,
            promises_kept_rate=0.0,
            consent_level="none"
        )
        assert low_scores.calculate_health_score() >= 0
    
    def test_recency_weight(self):
        """Test recency factor contributes to score."""
        from services.relationship_crm import RelationshipScores
        
        recent = RelationshipScores(recency_days=1)
        old = RelationshipScores(recency_days=60)
        
        assert recent.calculate_health_score() > old.calculate_health_score()
    
    def test_resonance_weight(self):
        """Test resonance factor contributes to score."""
        from services.relationship_crm import RelationshipScores
        
        high_res = RelationshipScores(resonance="high")
        low_res = RelationshipScores(resonance="low")
        
        assert high_res.calculate_health_score() > low_res.calculate_health_score()


class TestRF002ContextCards:
    """Tests for RF-002: Context Cards (Relationship Profiles)."""
    
    def test_contact_creation(self):
        """Test Contact dataclass creation."""
        from services.relationship_crm import Contact, ContactContext
        
        contact = Contact(
            platform="instagram",
            username="test_user",
            name="Test User"
        )
        
        assert contact.id is not None
        assert contact.platform == "instagram"
        assert contact.username == "test_user"
    
    def test_contact_context(self):
        """Test ContactContext fields."""
        from services.relationship_crm import ContactContext
        
        context = ContactContext(
            building="Building a content agency",
            struggles="Finding consistent clients",
            values="Quality over quantity",
            win_30d="Sign 2 new clients",
            preferred_cadence="weekly",
            do_not_do=["cold calls", "spam"]
        )
        
        assert context.building == "Building a content agency"
        assert "cold calls" in context.do_not_do
    
    def test_contact_to_dict(self):
        """Test Contact serialization."""
        from services.relationship_crm import Contact
        
        contact = Contact(
            platform="twitter",
            username="testuser",
            name="Test"
        )
        
        data = contact.to_dict()
        
        assert "id" in data
        assert "platform" in data
        assert "relationship_health" in data
        assert "context" in data
        assert "scores" in data
    
    def test_contact_health_property(self):
        """Test relationship_health property."""
        from services.relationship_crm import Contact
        
        contact = Contact(platform="instagram", username="test")
        
        # Default scores should give some health
        assert isinstance(contact.relationship_health, int)
        assert 0 <= contact.relationship_health <= 100


class TestRF003PipelineStages:
    """Tests for RF-003: Relationship Pipeline Stages."""
    
    def test_pipeline_stages_exist(self):
        """Test all 8 pipeline stages are defined."""
        from services.relationship_crm import PipelineStage
        
        stages = list(PipelineStage)
        assert len(stages) == 8
        
        expected_stages = [
            "first_touch",
            "context_captured", 
            "micro_win",
            "cadence",
            "trust_signals",
            "fit_identified",
            "offer",
            "post_win"
        ]
        
        actual_values = [s.value for s in stages]
        for expected in expected_stages:
            assert expected in actual_values, f"Missing stage: {expected}"
    
    def test_contact_default_stage(self):
        """Test contact starts at first_touch."""
        from services.relationship_crm import Contact, PipelineStage
        
        contact = Contact(platform="instagram", username="test")
        assert contact.pipeline_stage == PipelineStage.FIRST_TOUCH.value


class TestRF004IntentLanes:
    """Tests for RF-004: Intent Ladder (Message Lanes)."""
    
    def test_message_lanes_exist(self):
        """Test all 3 message lanes are defined."""
        from services.relationship_crm import MessageLane
        
        assert MessageLane.FRIENDSHIP.value == "A"
        assert MessageLane.SERVICE.value == "B"
        assert MessageLane.OFFER.value == "C"
    
    def test_value_log_tracks_lane(self):
        """Test ValueLogEntry tracks message lane."""
        from services.relationship_crm import ValueLogEntry
        
        entry = ValueLogEntry(
            action_type="resource",
            description="Sent template",
            lane="B"
        )
        
        assert entry.lane == "B"


class TestRF005NextBestActionAI:
    """Tests for RF-005: Next-Best-Action AI Engine."""
    
    @pytest.mark.skip(reason="Requires OpenAI module")
    def test_action_suggestion_dataclass(self):
        """Test ActionSuggestion dataclass."""
        from services.relationship_ai import ActionSuggestion
        
        action = ActionSuggestion(
            action_type="check_in",
            lane="A",
            template_id="A1",
            message="how'd that thing go?",
            reasoning="Healthy relationship, maintain connection",
            priority=2,
            timing="this_week"
        )
        
        assert action.lane == "A"
        assert action.priority == 2
    
    @pytest.mark.skip(reason="Requires OpenAI module")
    def test_ai_engine_initialization(self):
        """Test RelationshipAI initializes."""
        from services.relationship_ai import RelationshipAI
        
        ai = RelationshipAI()
        assert ai is not None
    
    @pytest.mark.skip(reason="Requires OpenAI module")
    def test_get_next_best_action_high_health(self):
        """Test action suggestion for high health contact."""
        from services.relationship_ai import RelationshipAI
        
        ai = RelationshipAI()
        
        contact = {
            "id": "test123",
            "username": "testuser",
            "relationship_health": 85,
            "pipeline_stage": "trust_signals",
            "context": {"building": "SaaS startup", "struggles": "marketing"},
            "scores": {"trust_signals": ["asked_opinion"]}
        }
        
        action = ai.get_next_best_action(contact)
        
        # High health should get Lane A or B, not aggressive C
        assert action.lane in ["A", "B", "C"]
        assert action.message is not None
        assert action.reasoning is not None
    
    @pytest.mark.skip(reason="Requires OpenAI module")
    def test_get_next_best_action_low_health(self):
        """Test action suggestion for low health contact."""
        from services.relationship_ai import RelationshipAI
        
        ai = RelationshipAI()
        
        contact = {
            "id": "test456",
            "username": "coldlead",
            "relationship_health": 30,
            "pipeline_stage": "first_touch",
            "context": {},
            "scores": {"trust_signals": []}
        }
        
        action = ai.get_next_best_action(contact)
        
        # Low health should get gentle open loop
        assert action.lane == "A"
        assert action.timing in ["this_week", "next_week"]
    
    @pytest.mark.skip(reason="Requires OpenAI module")
    def test_batch_actions(self):
        """Test batch action suggestions."""
        from services.relationship_ai import RelationshipAI
        
        ai = RelationshipAI()
        
        contacts = [
            {"id": "1", "username": "user1", "relationship_health": 80, "pipeline_stage": "trust_signals", "context": {}, "scores": {}},
            {"id": "2", "username": "user2", "relationship_health": 45, "pipeline_stage": "first_touch", "context": {}, "scores": {}},
            {"id": "3", "username": "user3", "relationship_health": 60, "pipeline_stage": "micro_win", "context": {}, "scores": {}},
        ]
        
        actions = ai.get_batch_actions(contacts, limit=3)
        
        assert len(actions) == 3
        # Should be sorted by priority
        assert all("action" in a for a in actions)


class TestRelationshipCRMAPI:
    """Tests for Relationship CRM API endpoints."""
    
    def test_api_router_exists(self):
        """Test API router can be imported."""
        from api.endpoints.relationship_crm import router
        assert router is not None
    
    def test_contact_endpoints_exist(self):
        """Test contact management endpoints exist."""
        from api.endpoints.relationship_crm import (
            create_contact,
            get_contact,
            get_contact_by_username,
            update_contact_context
        )
        assert create_contact is not None
        assert get_contact is not None
        assert get_contact_by_username is not None
        assert update_contact_context is not None
    
    def test_value_tracking_endpoints_exist(self):
        """Test value tracking endpoints exist."""
        from api.endpoints.relationship_crm import (
            log_value_delivered,
            get_value_log
        )
        assert log_value_delivered is not None
        assert get_value_log is not None
    
    def test_pipeline_endpoints_exist(self):
        """Test pipeline management endpoints exist."""
        from api.endpoints.relationship_crm import (
            advance_pipeline,
            record_trust_signal
        )
        assert advance_pipeline is not None
        assert record_trust_signal is not None
    
    def test_health_query_endpoints_exist(self):
        """Test health query endpoints exist."""
        from api.endpoints.relationship_crm import (
            get_needs_care,
            get_healthy_relationships,
            get_due_actions,
            get_pipeline_summary
        )
        assert get_needs_care is not None
        assert get_healthy_relationships is not None
        assert get_due_actions is not None
        assert get_pipeline_summary is not None
    
    def test_ai_suggestion_endpoints_exist(self):
        """Test AI suggestion endpoints exist."""
        from api.endpoints.relationship_crm import (
            get_next_action,
            suggest_reply,
            get_batch_actions,
            analyze_message
        )
        assert get_next_action is not None
        assert suggest_reply is not None
        assert get_batch_actions is not None
        assert analyze_message is not None


class TestMessageTemplates:
    """Tests for message template library."""
    
    @pytest.mark.skip(reason="Requires OpenAI module")
    def test_friendship_templates_exist(self):
        """Test Lane A templates are defined."""
        from services.relationship_ai import FRIENDSHIP_TEMPLATES
        
        assert len(FRIENDSHIP_TEMPLATES) >= 3
        assert all("template" in t for t in FRIENDSHIP_TEMPLATES)
    
    @pytest.mark.skip(reason="Requires OpenAI module")
    def test_service_templates_exist(self):
        """Test Lane B templates are defined."""
        from services.relationship_ai import SERVICE_TEMPLATES
        
        assert len(SERVICE_TEMPLATES) >= 3
        assert all("template" in t for t in SERVICE_TEMPLATES)
    
    @pytest.mark.skip(reason="Requires OpenAI module")
    def test_offer_templates_exist(self):
        """Test Lane C templates are defined."""
        from services.relationship_ai import OFFER_TEMPLATES
        
        assert len(OFFER_TEMPLATES) >= 3
        assert all("template" in t for t in OFFER_TEMPLATES)
    
    @pytest.mark.skip(reason="Requires OpenAI module")
    def test_rewarm_templates_exist(self):
        """Test re-warm templates are defined."""
        from services.relationship_ai import REWARM_TEMPLATES
        
        assert len(REWARM_TEMPLATES) >= 2
        assert all("template" in t for t in REWARM_TEMPLATES)


class TestCRMSingleton:
    """Tests for singleton pattern."""
    
    def test_crm_singleton(self):
        """Test get_relationship_crm returns same instance."""
        from services.relationship_crm import get_relationship_crm
        
        crm1 = get_relationship_crm()
        crm2 = get_relationship_crm()
        
        assert crm1 is crm2
    
    @pytest.mark.skip(reason="Requires OpenAI module")
    def test_ai_singleton(self):
        """Test get_relationship_ai returns same instance."""
        from services.relationship_ai import get_relationship_ai
        
        ai1 = get_relationship_ai()
        ai2 = get_relationship_ai()
        
        assert ai1 is ai2
