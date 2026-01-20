"""
Tests for Blotato Rate Limit Handler (BLOT-004)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from services.api_rate_limiter import APIRateLimiter, APICallLog


class TestBlotatoRateLimiter:
    """Test BLOT-004: Blotato Rate Limit Handler"""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session"""
        db = Mock()
        query_mock = Mock()
        db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.count.return_value = 0  # Default: no calls in last minute
        query_mock.add = Mock()
        query_mock.commit = Mock()
        return db

    def test_blotato_upload_rate_limit_config(self, mock_db):
        """Verify Blotato upload rate limit is configured (10/min)"""
        limiter = APIRateLimiter(db=mock_db, api_name="blotato_upload")

        config = limiter.budgets.get("blotato_upload")

        assert config is not None
        assert config["per_minute_limit"] == 10
        assert config["safety_margin"] == 0.9

    def test_blotato_publish_rate_limit_config(self, mock_db):
        """Verify Blotato publish rate limit is configured (30/min)"""
        limiter = APIRateLimiter(db=mock_db, api_name="blotato_publish")

        config = limiter.budgets.get("blotato_publish")

        assert config is not None
        assert config["per_minute_limit"] == 30
        assert config["safety_margin"] == 0.9

    def test_can_make_call_per_minute_within_limit(self, mock_db):
        """Test that calls are allowed when within rate limit"""
        limiter = APIRateLimiter(db=mock_db, api_name="blotato_upload")

        # Mock 5 calls in last minute (below limit of 10)
        query_mock = Mock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.count.return_value = 5

        allowed, reason = limiter.can_make_call_per_minute("/media")

        assert allowed is True
        assert "remaining" in reason.lower()

    def test_can_make_call_per_minute_exceeds_limit(self, mock_db):
        """Test that calls are blocked when rate limit exceeded"""
        limiter = APIRateLimiter(db=mock_db, api_name="blotato_upload")

        # Mock 10 calls in last minute (at limit)
        # With 90% safety margin, effective limit is 9
        query_mock = Mock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.count.return_value = 10

        allowed, reason = limiter.can_make_call_per_minute("/media")

        assert allowed is False
        assert "rate limit exceeded" in reason.lower()

    def test_upload_limit_vs_publish_limit(self, mock_db):
        """Test that upload (10/min) and publish (30/min) have different limits"""
        upload_limiter = APIRateLimiter(db=mock_db, api_name="blotato_upload")
        publish_limiter = APIRateLimiter(db=mock_db, api_name="blotato_publish")

        upload_config = upload_limiter.budgets["blotato_upload"]
        publish_config = publish_limiter.budgets["blotato_publish"]

        # Upload limit is 10/min
        assert upload_config["per_minute_limit"] == 10

        # Publish limit is 30/min (3x upload)
        assert publish_config["per_minute_limit"] == 30
        assert publish_config["per_minute_limit"] == upload_config["per_minute_limit"] * 3

    def test_safety_margin_reduces_effective_limit(self, mock_db):
        """Test that safety margin (90%) reduces the effective limit"""
        limiter = APIRateLimiter(db=mock_db, api_name="blotato_upload")

        # Blotato allows 10/min, but with 90% margin we use only 9
        config = limiter.budgets["blotato_upload"]
        effective_limit = int(config["per_minute_limit"] * config["safety_margin"])

        assert effective_limit == 9  # 90% of 10

    def test_safety_margin_for_publish(self, mock_db):
        """Test safety margin for publish endpoint (30/min → 27/min)"""
        limiter = APIRateLimiter(db=mock_db, api_name="blotato_publish")

        config = limiter.budgets["blotato_publish"]
        effective_limit = int(config["per_minute_limit"] * config["safety_margin"])

        assert effective_limit == 27  # 90% of 30

    def test_no_per_minute_limit_for_other_apis(self, mock_db):
        """Test that APIs without per-minute limits are not restricted"""
        limiter = APIRateLimiter(db=mock_db, api_name="some_other_api")

        allowed, reason = limiter.can_make_call_per_minute("/endpoint")

        assert allowed is True
        assert "no per-minute limit" in reason.lower()


class TestBlotatoRateLimiterFeatureAcceptance:
    """
    Acceptance criteria tests for BLOT-004:
    - Handle 10/min upload and 30/min publish rate limits
    """

    @pytest.fixture
    def mock_db(self):
        db = Mock()
        query_mock = Mock()
        db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.count.return_value = 0
        return db

    def test_acceptance_10_per_minute_upload_limit(self, mock_db):
        """
        Acceptance: Handle 10/min upload rate limit
        """
        limiter = APIRateLimiter(db=mock_db, api_name="blotato_upload")

        # Verify 10/min limit exists
        config = limiter.budgets.get("blotato_upload")
        assert config is not None, "blotato_upload must have rate limit config"
        assert config["per_minute_limit"] == 10, "Upload limit must be 10/min"

        # Verify can_make_call_per_minute method exists and works
        allowed, _ = limiter.can_make_call_per_minute("/media")
        assert isinstance(allowed, bool), "Method must return boolean"

    def test_acceptance_30_per_minute_publish_limit(self, mock_db):
        """
        Acceptance: Handle 30/min publish rate limit
        """
        limiter = APIRateLimiter(db=mock_db, api_name="blotato_publish")

        # Verify 30/min limit exists
        config = limiter.budgets.get("blotato_publish")
        assert config is not None, "blotato_publish must have rate limit config"
        assert config["per_minute_limit"] == 30, "Publish limit must be 30/min"

        # Verify can_make_call_per_minute method exists and works
        allowed, _ = limiter.can_make_call_per_minute("/posts")
        assert isinstance(allowed, bool), "Method must return boolean"

    def test_acceptance_rate_limit_enforced(self, mock_db):
        """
        Acceptance: Rate limits are actually enforced
        """
        limiter = APIRateLimiter(db=mock_db, api_name="blotato_upload")

        # Simulate 10 calls in last minute (at limit with 90% safety margin = 9)
        query_mock = Mock()
        mock_db.query.return_value = query_mock
        query_mock.filter.return_value = query_mock
        query_mock.count.return_value = 10

        allowed, reason = limiter.can_make_call_per_minute("/media")

        # Call must be blocked
        assert allowed is False, "Calls beyond rate limit must be blocked"
        assert "exceeded" in reason.lower(), "Reason must indicate limit exceeded"
