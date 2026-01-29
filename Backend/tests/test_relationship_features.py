"""
Tests for Relationship-First DM System Features
RF-006: Fit Signal Detection
RF-007: Touch Cadences
RF-008: Success Metrics
"""
import pytest
from datetime import datetime, date, timezone
from unittest.mock import Mock, patch, AsyncMock

from services.relationship_fit_signals import FitSignalDetector, FitSignalMatch, FIT_SIGNALS
from services.relationship_cadence import TouchCadenceManager, CadenceTask, DailyCadence, WeeklyCadence
from services.relationship_metrics import RelationshipMetricsService, RelationshipMetrics, PipelineFunnel


# =============================================================================
# RF-006: Fit Signal Detection Tests
# =============================================================================

class TestFitSignalDetector:
    """Tests for FitSignalDetector."""
    
    def test_initialization(self):
        """Test detector initializes correctly."""
        detector = FitSignalDetector()
        assert detector is not None
        assert len(detector.fit_signals) >= 6
        
    def test_simple_signal_detection_relationship_crm(self):
        """Test simple keyword-based detection for relationship CRM."""
        detector = FitSignalDetector()
        # Use exact signal phrases for reliable matching
        messages = [
            "i keep forgetting to follow up",
            "my network is messy",
            "i lost track of mentors/clients"
        ]
        
        matches = detector.detect_signals_simple(messages, {})
        
        assert len(matches) >= 1
        crm_match = next((m for m in matches if m.offer_type == "relationship_crm"), None)
        assert crm_match is not None
        assert crm_match.confidence > 0.3  # At least 1 signal found
        assert len(crm_match.matched_signals) >= 1
        
    def test_simple_signal_detection_automation(self):
        """Test simple detection for automation services."""
        detector = FitSignalDetector()
        # Use exact signal phrases for reliable matching
        messages = [
            "this is taking me forever",
            "i'm drowning in manual work",
            "i need a system"
        ]
        
        matches = detector.detect_signals_simple(messages, {})
        
        assert len(matches) >= 1
        auto_match = next((m for m in matches if m.offer_type == "automation_services"), None)
        assert auto_match is not None
        assert auto_match.confidence > 0.3  # At least 1 signal found
        
    def test_no_signals_detected(self):
        """Test when no fit signals are found."""
        detector = FitSignalDetector()
        messages = [
            "hey how are you",
            "nice weather today",
            "thanks for connecting"
        ]
        
        matches = detector.detect_signals_simple(messages, {})
        assert len(matches) == 0
        
    def test_golden_trigger_conditions_met(self):
        """Test golden trigger when all conditions are met."""
        detector = FitSignalDetector()
        
        contact = {
            "username": "test_user",
            "pipeline_stage": "trust_signals",
            "scores": {
                "trust_signals": ["asked_opinion", "shared_update"],
                "value_delivered_count": 3
            }
        }
        
        fit_match = FitSignalMatch(
            offer_type="relationship_crm",
            offer_name="Relationship CRM",
            matched_signals=["forgetting to follow up", "network messy"],
            confidence=0.8,
            offer_line="want a quick look?",
            context="",
            detected_at=datetime.now(timezone.utc)
        )
        
        ready, best_match = detector.check_golden_trigger(contact, [fit_match])
        
        assert ready is True
        assert best_match is not None
        assert best_match.offer_type == "relationship_crm"
        
    def test_golden_trigger_not_ready(self):
        """Test golden trigger when conditions not met."""
        detector = FitSignalDetector()
        
        contact = {
            "username": "test_user",
            "pipeline_stage": "first_touch",
            "scores": {
                "trust_signals": [],
                "value_delivered_count": 0
            }
        }
        
        fit_match = FitSignalMatch(
            offer_type="relationship_crm",
            offer_name="Relationship CRM",
            matched_signals=["one signal"],
            confidence=0.3,
            offer_line="want a quick look?",
            context="",
            detected_at=datetime.now(timezone.utc)
        )
        
        ready, best_match = detector.check_golden_trigger(contact, [fit_match])
        
        assert ready is False
        
    def test_offer_timing_ready(self):
        """Test offer timing when ready to offer."""
        detector = FitSignalDetector()
        
        contact = {
            "relationship_health": 75,
            "pipeline_stage": "trust_signals"
        }
        
        fit_match = FitSignalMatch(
            offer_type="test",
            offer_name="Test",
            matched_signals=[],
            confidence=0.7,
            offer_line="test offer",
            context="",
            detected_at=datetime.now(timezone.utc)
        )
        
        timing = detector.get_offer_timing_recommendation(contact, fit_match)
        
        assert timing["ready"] is True
        assert timing["timing"] == "now"
        
    def test_offer_timing_health_too_low(self):
        """Test offer timing when health is too low."""
        detector = FitSignalDetector()
        
        contact = {
            "relationship_health": 45,
            "pipeline_stage": "trust_signals"
        }
        
        fit_match = FitSignalMatch(
            offer_type="test",
            offer_name="Test",
            matched_signals=[],
            confidence=0.7,
            offer_line="test offer",
            context="",
            detected_at=datetime.now(timezone.utc)
        )
        
        timing = detector.get_offer_timing_recommendation(contact, fit_match)
        
        assert timing["ready"] is False
        assert "health too low" in timing["reason"].lower()


# =============================================================================
# RF-007: Touch Cadence Tests
# =============================================================================

class TestTouchCadenceManager:
    """Tests for TouchCadenceManager."""
    
    def test_initialization(self):
        """Test manager initializes correctly."""
        manager = TouchCadenceManager()
        assert manager is not None
        
    def test_daily_cadence_structure(self):
        """Test daily cadence has correct structure."""
        cadence = DailyCadence(date=date.today())
        
        assert hasattr(cadence, 'date')
        assert hasattr(cadence, 'story_replies')
        assert hasattr(cadence, 'hot_check_ins')
        assert isinstance(cadence.story_replies, list)
        assert isinstance(cadence.hot_check_ins, list)
        
    def test_weekly_cadence_structure(self):
        """Test weekly cadence has correct structure."""
        cadence = WeeklyCadence(week_start=date.today())
        
        assert hasattr(cadence, 'week_start')
        assert hasattr(cadence, 'micro_wins')
        assert hasattr(cadence, 'curiosity_questions')
        assert hasattr(cadence, 'permissioned_offers')
        
    def test_cadence_task_structure(self):
        """Test cadence task has all required fields."""
        task = CadenceTask(
            contact_id="123",
            contact_name="Test User",
            platform="instagram",
            task_type="check_in",
            priority=3,
            health_score=75,
            context="Building a startup"
        )
        
        assert task.contact_id == "123"
        assert task.contact_name == "Test User"
        assert task.platform == "instagram"
        assert task.task_type == "check_in"
        assert task.priority == 3
        assert task.health_score == 75


# =============================================================================
# RF-008: Success Metrics Tests
# =============================================================================

class TestRelationshipMetricsService:
    """Tests for RelationshipMetricsService."""
    
    def test_initialization(self):
        """Test service initializes correctly."""
        service = RelationshipMetricsService()
        assert service is not None
        
    def test_metrics_structure(self):
        """Test metrics dataclass has all required fields."""
        metrics = RelationshipMetrics()
        
        assert hasattr(metrics, 'meaningful_replies_week')
        assert hasattr(metrics, 'context_cards_filled_pct')
        assert hasattr(metrics, 'micro_wins_month')
        assert hasattr(metrics, 'avg_time_to_followup_hours')
        assert hasattr(metrics, 'permissioned_offer_acceptance_rate')
        assert hasattr(metrics, 'referrals_month')
        assert hasattr(metrics, 'avg_relationship_health')
        
    def test_pipeline_funnel_structure(self):
        """Test pipeline funnel has all stages."""
        funnel = PipelineFunnel()
        
        assert hasattr(funnel, 'first_touch')
        assert hasattr(funnel, 'context_captured')
        assert hasattr(funnel, 'micro_win')
        assert hasattr(funnel, 'cadence')
        assert hasattr(funnel, 'trust_signals')
        assert hasattr(funnel, 'fit_identified')
        assert hasattr(funnel, 'offer')
        assert hasattr(funnel, 'post_win')


# =============================================================================
# Integration Tests
# =============================================================================

class TestRelationshipFeaturesIntegration:
    """Integration tests for relationship features."""
    
    def test_fit_signal_to_offer_flow(self):
        """Test complete flow from signal detection to offer recommendation."""
        detector = FitSignalDetector()
        
        # Step 1: Detect signals
        messages = [
            "ugh i keep forgetting to follow up",
            "my network is all over the place",
            "i need help organizing my contacts"
        ]
        
        matches = detector.detect_signals_simple(messages, {})
        assert len(matches) > 0
        
        # Step 2: Check golden trigger
        contact = {
            "username": "active_user",
            "pipeline_stage": "trust_signals",
            "relationship_health": 75,
            "scores": {
                "trust_signals": ["asked_opinion"],
                "value_delivered_count": 2
            }
        }
        
        ready, best_match = detector.check_golden_trigger(contact, matches)
        
        # Step 3: Get timing recommendation
        if best_match:
            timing = detector.get_offer_timing_recommendation(contact, best_match)
            assert timing["ready"] is True
            
    def test_3_1_rule_concept(self):
        """Test 3:1 rule compliance calculation concept."""
        # Simulate the calculation
        value_touches = 9  # Lane A + B messages
        offer_touches = 2  # Lane C messages
        value_delivered = 3  # Resources/intros sent
        
        total_value = value_touches + value_delivered
        ratio = total_value / offer_touches if offer_touches > 0 else float('inf')
        
        # 12 value : 2 offers = 6:1 ratio, compliant
        assert ratio >= 3.0
        
        # Test non-compliant scenario
        value_touches = 2
        offer_touches = 3
        total_value = value_touches
        ratio = total_value / offer_touches
        
        # 2 value : 3 offers = 0.67:1 ratio, not compliant
        assert ratio < 3.0


# =============================================================================
# Template Tests
# =============================================================================

class TestFitSignalTemplates:
    """Test fit signal configurations."""
    
    def test_all_offers_have_required_fields(self):
        """Test all fit signal configs have required fields."""
        for offer_type, config in FIT_SIGNALS.items():
            assert "name" in config, f"{offer_type} missing name"
            assert "signals" in config, f"{offer_type} missing signals"
            assert "offer_line" in config, f"{offer_type} missing offer_line"
            assert len(config["signals"]) >= 3, f"{offer_type} needs more signals"
            
    def test_offer_lines_are_permission_based(self):
        """Test offer lines follow permission-based pattern."""
        permission_words = ["want", "would you like", "interested", "show you"]
        
        for offer_type, config in FIT_SIGNALS.items():
            offer_line = config["offer_line"].lower()
            has_permission = any(word in offer_line for word in permission_words)
            assert has_permission, f"{offer_type} offer line should ask permission"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
