"""
Tests for ACTP Pipeline Orchestrator
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from services.creative_testing_pipeline.orchestrator import (
    PipelineOrchestrator,
    CAMPAIGN_TRANSITIONS,
    ROUND_TRANSITIONS,
)
from services.creative_testing_pipeline.models import (
    CampaignStatus,
    CreateCampaignRequest,
    RoundStatus,
    RoundType,
    TestCampaign,
    TestRound,
)
from services.creative_testing_pipeline.config import ACTPConfig


class TestCampaignStateTransitions:
    """Test campaign state machine transitions."""

    def test_valid_transitions_from_draft(self):
        allowed = CAMPAIGN_TRANSITIONS[CampaignStatus.DRAFT]
        assert CampaignStatus.GENERATING in allowed
        assert CampaignStatus.FAILED in allowed

    def test_valid_transitions_from_generating(self):
        allowed = CAMPAIGN_TRANSITIONS[CampaignStatus.GENERATING]
        assert CampaignStatus.ORGANIC_TESTING in allowed
        assert CampaignStatus.PAUSED in allowed

    def test_completed_has_no_transitions(self):
        assert CAMPAIGN_TRANSITIONS[CampaignStatus.COMPLETED] == []

    def test_paused_can_resume_to_multiple_states(self):
        allowed = CAMPAIGN_TRANSITIONS[CampaignStatus.PAUSED]
        assert len(allowed) >= 3


class TestRoundStateTransitions:
    """Test round state machine transitions."""

    def test_pending_goes_to_generating(self):
        allowed = ROUND_TRANSITIONS[RoundStatus.PENDING]
        assert RoundStatus.GENERATING in allowed

    def test_generating_goes_to_publishing(self):
        allowed = ROUND_TRANSITIONS[RoundStatus.GENERATING]
        assert RoundStatus.PUBLISHING in allowed

    def test_waiting_goes_to_collecting(self):
        allowed = ROUND_TRANSITIONS[RoundStatus.WAITING]
        assert RoundStatus.COLLECTING in allowed

    def test_completed_has_no_transitions(self):
        assert ROUND_TRANSITIONS[RoundStatus.COMPLETED] == []


class TestOrchestratorValidation:
    """Test orchestrator validation logic."""

    def setup_method(self):
        self.orchestrator = PipelineOrchestrator(db_client=None)

    def test_validate_valid_transition(self):
        # Should not raise
        self.orchestrator._validate_transition(
            CampaignStatus.DRAFT, CampaignStatus.GENERATING
        )

    def test_validate_invalid_transition(self):
        with pytest.raises(ValueError, match="Invalid campaign transition"):
            self.orchestrator._validate_transition(
                CampaignStatus.DRAFT, CampaignStatus.COMPLETED
            )

    def test_validate_round_valid_transition(self):
        self.orchestrator._validate_round_transition(
            RoundStatus.PENDING, RoundStatus.GENERATING
        )

    def test_validate_round_invalid_transition(self):
        with pytest.raises(ValueError, match="Invalid round transition"):
            self.orchestrator._validate_round_transition(
                RoundStatus.PENDING, RoundStatus.COMPLETED
            )


class TestDetermineNextRoundStatus:
    """Test round status progression logic."""

    def setup_method(self):
        self.orchestrator = PipelineOrchestrator(db_client=None)
        self.config = ACTPConfig()

    def test_generating_goes_to_publishing(self):
        test_round = TestRound(
            campaign_id="c1", round_number=1, round_type=RoundType.ORGANIC,
            status=RoundStatus.GENERATING,
        )
        result = self.orchestrator._determine_next_round_status(test_round, self.config)
        assert result == RoundStatus.PUBLISHING

    def test_publishing_goes_to_waiting(self):
        test_round = TestRound(
            campaign_id="c1", round_number=1, round_type=RoundType.ORGANIC,
            status=RoundStatus.PUBLISHING,
        )
        result = self.orchestrator._determine_next_round_status(test_round, self.config)
        assert result == RoundStatus.WAITING

    def test_waiting_returns_none_if_not_ready(self):
        future = datetime(2099, 1, 1, tzinfo=timezone.utc)
        test_round = TestRound(
            campaign_id="c1", round_number=1, round_type=RoundType.ORGANIC,
            status=RoundStatus.WAITING, wait_until=future,
        )
        result = self.orchestrator._determine_next_round_status(test_round, self.config)
        assert result is None

    def test_waiting_goes_to_collecting_when_ready(self):
        past = datetime(2020, 1, 1, tzinfo=timezone.utc)
        test_round = TestRound(
            campaign_id="c1", round_number=1, round_type=RoundType.ORGANIC,
            status=RoundStatus.WAITING, wait_until=past,
        )
        result = self.orchestrator._determine_next_round_status(test_round, self.config)
        assert result == RoundStatus.COLLECTING

    def test_collecting_goes_to_selecting(self):
        test_round = TestRound(
            campaign_id="c1", round_number=1, round_type=RoundType.ORGANIC,
            status=RoundStatus.COLLECTING,
        )
        result = self.orchestrator._determine_next_round_status(test_round, self.config)
        assert result == RoundStatus.SELECTING

    def test_selecting_organic_goes_to_completed(self):
        test_round = TestRound(
            campaign_id="c1", round_number=1, round_type=RoundType.ORGANIC,
            status=RoundStatus.SELECTING,
        )
        result = self.orchestrator._determine_next_round_status(test_round, self.config)
        assert result == RoundStatus.COMPLETED

    def test_selecting_ad_goes_to_deploying(self):
        test_round = TestRound(
            campaign_id="c1", round_number=1, round_type=RoundType.AD,
            status=RoundStatus.SELECTING,
        )
        result = self.orchestrator._determine_next_round_status(test_round, self.config)
        assert result == RoundStatus.DEPLOYING

    def test_deploying_goes_to_waiting(self):
        test_round = TestRound(
            campaign_id="c1", round_number=1, round_type=RoundType.AD,
            status=RoundStatus.DEPLOYING,
        )
        result = self.orchestrator._determine_next_round_status(test_round, self.config)
        assert result == RoundStatus.WAITING


class TestGetCurrentRound:
    """Test current round detection."""

    def setup_method(self):
        self.orchestrator = PipelineOrchestrator(db_client=None)

    def test_returns_non_completed_round(self):
        rounds = [
            TestRound(campaign_id="c1", round_number=1, round_type=RoundType.ORGANIC,
                      status=RoundStatus.COMPLETED),
            TestRound(campaign_id="c1", round_number=2, round_type=RoundType.AD,
                      status=RoundStatus.WAITING),
        ]
        result = self.orchestrator._get_current_round(rounds)
        assert result.round_number == 2

    def test_returns_none_when_all_completed(self):
        rounds = [
            TestRound(campaign_id="c1", round_number=1, round_type=RoundType.ORGANIC,
                      status=RoundStatus.COMPLETED),
        ]
        result = self.orchestrator._get_current_round(rounds)
        assert result is None

    def test_returns_highest_incomplete_round(self):
        rounds = [
            TestRound(campaign_id="c1", round_number=1, round_type=RoundType.ORGANIC,
                      status=RoundStatus.COMPLETED),
            TestRound(campaign_id="c1", round_number=2, round_type=RoundType.AD,
                      status=RoundStatus.GENERATING),
            TestRound(campaign_id="c1", round_number=3, round_type=RoundType.ORGANIC,
                      status=RoundStatus.PENDING),
        ]
        result = self.orchestrator._get_current_round(rounds)
        assert result.round_number == 3
