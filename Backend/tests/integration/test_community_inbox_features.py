"""
Integration tests for Community Inbox features (INBOX-003, 006, 008)

Tests for:
- INBOX-003: DM Fetcher Service
- INBOX-006: Auto-Reply Rules Engine
- INBOX-008: Inbox Analytics
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from services.dm_fetcher_service import DMFetcherService, get_dm_fetcher_service
from services.inbox.auto_reply_engine import AutoReplyEngine, get_auto_reply_engine
from services.inbox.analytics_service import InboxAnalyticsService, get_inbox_analytics_service
from database.models import CommunityInboxMessage, InboxAutoReplyRule, InboxAnalytics
from database.connection import async_session_maker


# =============================================================================
# INBOX-003: DM FETCHER SERVICE TESTS
# =============================================================================

class TestDMFetcherService:
    """Test suite for DM Fetcher Service"""

    @pytest.mark.asyncio
    async def test_dm_fetcher_singleton(self):
        """Test DM Fetcher singleton pattern"""
        fetcher1 = DMFetcherService.get_instance()
        fetcher2 = DMFetcherService.get_instance()

        assert fetcher1 is fetcher2
        assert fetcher1 is not None

    @pytest.mark.asyncio
    async def test_dm_fetcher_initialization(self):
        """Test DM Fetcher initializes correctly"""
        fetcher = get_dm_fetcher_service()

        assert fetcher is not None
        assert hasattr(fetcher, 'start')
        assert hasattr(fetcher, 'stop')
        assert hasattr(fetcher, 'fetch_recent_dms')

    @pytest.mark.asyncio
    async def test_dm_fetcher_has_platform_fetchers(self):
        """Test DM Fetcher has all platform fetchers"""
        fetcher = get_dm_fetcher_service()

        assert "instagram" in fetcher._platform_fetchers
        assert "twitter" in fetcher._platform_fetchers
        assert "threads" in fetcher._platform_fetchers

    @pytest.mark.asyncio
    async def test_group_dms_into_threads(self):
        """Test thread grouping logic"""
        fetcher = get_dm_fetcher_service()

        # Mock DM messages
        messages = [
            {
                "conversation_id": "conv_123",
                "platform": "instagram",
                "sender_id": "user_1",
                "timestamp": datetime.now(timezone.utc),
                "content": "Hello"
            },
            {
                "conversation_id": "conv_123",
                "platform": "instagram",
                "sender_id": "user_1",
                "timestamp": datetime.now(timezone.utc),
                "content": "How are you?"
            },
            {
                "conversation_id": "conv_456",
                "platform": "twitter",
                "sender_id": "user_2",
                "timestamp": datetime.now(timezone.utc),
                "content": "Hi there"
            }
        ]

        threads = await fetcher._group_dms_into_threads(messages)

        assert len(threads) == 2
        assert threads[0][0] in ["conv_123", "conv_456"]
        assert len(threads[0][1]) > 0

    @pytest.mark.asyncio
    async def test_check_dm_exists_deduplication(self):
        """Test duplicate detection"""
        fetcher = get_dm_fetcher_service()
        workspace_id = "test_workspace"

        async with async_session_maker() as session:
            # Create a test message
            message = CommunityInboxMessage(
                id="test_msg_1",
                workspace_id=workspace_id,
                platform="instagram",
                message_type="dm",
                platform_message_id="ig_msg_123",
                sender_username="test_user",
                content="Test DM",
                received_at=datetime.now(timezone.utc),
                status="unread"
            )

            session.add(message)
            await session.commit()

            # Check if it exists
            exists = await fetcher._check_dm_exists(
                session,
                "instagram",
                "ig_msg_123",
                workspace_id
            )

            assert exists is True

            # Check non-existent
            not_exists = await fetcher._check_dm_exists(
                session,
                "twitter",
                "tw_msg_456",
                workspace_id
            )

            assert not_exists is False


# =============================================================================
# INBOX-006: AUTO-REPLY RULES ENGINE TESTS
# =============================================================================

class TestAutoReplyEngine:
    """Test suite for Auto-Reply Rules Engine"""

    @pytest.mark.asyncio
    async def test_auto_reply_singleton(self):
        """Test Auto-Reply Engine singleton pattern"""
        engine1 = AutoReplyEngine.get_instance()
        engine2 = AutoReplyEngine.get_instance()

        assert engine1 is engine2
        assert engine1 is not None

    @pytest.mark.asyncio
    async def test_create_auto_reply_rule(self):
        """Test creating an auto-reply rule"""
        engine = get_auto_reply_engine()

        rule_id = await engine.create_rule(
            name="Test Rule",
            reply_template="Thanks for reaching out!",
            keywords=["hello", "hi"],
            priority=50
        )

        assert rule_id is not None
        assert len(rule_id) > 0

    @pytest.mark.asyncio
    async def test_keyword_matching_contains(self):
        """Test keyword matching with 'contains' strategy"""
        engine = get_auto_reply_engine()

        # Test 'contains' match
        result = engine._match_keywords(
            "Hello there!",
            ["hello"],
            "contains"
        )
        assert result is True

        # Test no match
        result = engine._match_keywords(
            "Good morning",
            ["hello"],
            "contains"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_keyword_matching_exact(self):
        """Test keyword matching with 'exact' strategy"""
        engine = get_auto_reply_engine()

        # Exact match
        result = engine._match_keywords(
            "hello",
            ["hello"],
            "exact"
        )
        assert result is True

        # Partial match should fail
        result = engine._match_keywords(
            "hello world",
            ["hello"],
            "exact"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_keyword_matching_regex(self):
        """Test keyword matching with 'regex' strategy"""
        engine = get_auto_reply_engine()

        # Regex match
        result = engine._match_keywords(
            "Contact us for pricing",
            ["pric.*"],
            "regex"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_sentiment_matching(self):
        """Test sentiment filtering"""
        engine = get_auto_reply_engine()

        # Positive match
        result = engine._match_sentiment("positive", "positive")
        assert result is True

        # Negative match
        result = engine._match_sentiment("positive", "negative")
        assert result is False

        # Any always matches
        result = engine._match_sentiment("neutral", "any")
        assert result is True

    @pytest.mark.asyncio
    async def test_variable_substitution(self):
        """Test variable substitution in replies"""
        engine = get_auto_reply_engine()

        # Create mock message
        message = CommunityInboxMessage(
            id="test_msg",
            workspace_id="test_ws",
            platform="instagram",
            message_type="comment",
            sender_username="john_doe",
            sender_name="John Doe",
            content="Test message",
            received_at=datetime.now(timezone.utc),
            status="unread"
        )

        # Create rule with variables
        rule = InboxAutoReplyRule(
            id="test_rule",
            workspace_id="test_ws",
            name="Test",
            reply_template="Hi {name}, thanks for reaching out on {platform}!",
            keyword_triggers=["hello"],
            is_active=True
        )

        reply = await engine._execute_rule(rule, message)

        assert "John Doe" in reply
        assert "instagram" in reply
        assert "{" not in reply  # No unsubstituted variables

    @pytest.mark.asyncio
    async def test_daily_usage_limit(self):
        """Test daily usage quota enforcement"""
        engine = get_auto_reply_engine()

        # Reset daily usage
        engine._daily_usage = {}
        engine._usage_reset_time = datetime.now(timezone.utc)

        # Create mock rule
        rule = InboxAutoReplyRule(
            id="limited_rule",
            workspace_id="test_ws",
            name="Limited",
            reply_template="Reply",
            max_uses_per_day=1,
            uses_today=0,
            is_active=True
        )

        async with async_session_maker() as session:
            # First use should pass
            can_apply = await engine._can_apply_rule(rule, session)
            assert can_apply is True

            # Increment usage
            await engine._increment_rule_usage(rule.id, session)

            # Second use should fail
            can_apply = await engine._can_apply_rule(rule, session)
            assert can_apply is False

    @pytest.mark.asyncio
    async def test_get_active_rules(self):
        """Test retrieving active rules"""
        engine = get_auto_reply_engine()
        workspace_id = "test_workspace"

        # Create test rule
        rule_id = await engine.create_rule(
            name="Active Rule",
            reply_template="Active",
            workspace_id=workspace_id,
            priority=50
        )

        # Get active rules
        rules = await engine.get_active_rules(workspace_id)

        # Verify rule is in list
        rule_ids = [r.id for r in rules]
        assert rule_id in rule_ids


# =============================================================================
# INBOX-008: INBOX ANALYTICS TESTS
# =============================================================================

class TestInboxAnalytics:
    """Test suite for Inbox Analytics"""

    @pytest.mark.asyncio
    async def test_analytics_singleton(self):
        """Test Analytics singleton pattern"""
        analytics1 = InboxAnalyticsService.get_instance()
        analytics2 = InboxAnalyticsService.get_instance()

        assert analytics1 is analytics2
        assert analytics1 is not None

    @pytest.mark.asyncio
    async def test_calculate_metrics(self):
        """Test metric calculation"""
        analytics = get_inbox_analytics_service()
        workspace_id = "test_workspace"

        # Create test messages
        messages = [
            CommunityInboxMessage(
                id=f"msg_{i}",
                workspace_id=workspace_id,
                platform="instagram" if i % 2 == 0 else "twitter",
                message_type="comment",
                sender_username=f"user_{i}",
                content=f"Test message {i}",
                sentiment_label="positive" if i % 3 == 0 else "neutral",
                response_time_minutes=45 if i % 2 == 0 else 60,
                responded_at=datetime.now(timezone.utc) if i % 2 == 0 else None,
                received_at=datetime.now(timezone.utc),
                status="replied" if i % 2 == 0 else "unread"
            )
            for i in range(10)
        ]

        metrics = analytics._calculate_metrics(messages, workspace_id)

        assert metrics["total_messages"] == 10
        assert "response_metrics" in metrics
        assert "by_platform" in metrics
        assert "by_sentiment" in metrics
        assert metrics["response_metrics"]["response_rate"] > 0

    @pytest.mark.asyncio
    async def test_response_rate_calculation(self):
        """Test response rate calculation"""
        analytics = get_inbox_analytics_service()
        workspace_id = "test_workspace"

        # Create messages with different statuses
        messages = [
            CommunityInboxMessage(
                id="msg_responded",
                workspace_id=workspace_id,
                platform="instagram",
                message_type="comment",
                sender_username="user_1",
                content="Message 1",
                responded_at=datetime.now(timezone.utc),
                received_at=datetime.now(timezone.utc),
                status="replied"
            ),
            CommunityInboxMessage(
                id="msg_unread",
                workspace_id=workspace_id,
                platform="instagram",
                message_type="comment",
                sender_username="user_2",
                content="Message 2",
                received_at=datetime.now(timezone.utc),
                status="unread"
            )
        ]

        metrics = analytics._calculate_metrics(messages, workspace_id)

        # 1 out of 2 responded = 50%
        assert metrics["response_metrics"]["response_rate"] == 50.0

    @pytest.mark.asyncio
    async def test_response_time_statistics(self):
        """Test response time statistics calculation"""
        analytics = get_inbox_analytics_service()
        workspace_id = "test_workspace"

        # Create messages with response times
        messages = [
            CommunityInboxMessage(
                id=f"msg_{i}",
                workspace_id=workspace_id,
                platform="instagram",
                message_type="comment",
                sender_username=f"user_{i}",
                content=f"Message {i}",
                response_time_minutes=30 + (i * 10),  # 30, 40, 50, 60, 70
                responded_at=datetime.now(timezone.utc),
                received_at=datetime.now(timezone.utc),
                status="replied"
            )
            for i in range(5)
        ]

        metrics = analytics._calculate_metrics(messages, workspace_id)
        response_metrics = metrics["response_metrics"]

        assert response_metrics["avg_response_time"] == 50.0
        assert response_metrics["median_response_time"] == 50.0
        assert response_metrics["p95_response_time"] > 0
        assert response_metrics["p99_response_time"] > 0

    @pytest.mark.asyncio
    async def test_platform_breakdown(self):
        """Test platform breakdown calculation"""
        analytics = get_inbox_analytics_service()

        today = datetime.now(timezone.utc).date()
        start_of_day = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)

        async with async_session_maker() as session:
            # Create test messages
            for platform in ["instagram", "twitter", "tiktok"]:
                for i in range(3):
                    msg = CommunityInboxMessage(
                        id=f"{platform}_msg_{i}",
                        workspace_id="test_ws",
                        platform=platform,
                        message_type="comment",
                        sender_username=f"user_{i}",
                        content=f"Test from {platform}",
                        received_at=start_of_day,
                        status="replied" if i % 2 == 0 else "unread"
                    )
                    session.add(msg)

            await session.commit()

            # Get breakdown
            breakdown = await analytics.get_platform_breakdown(
                "test_ws",
                datetime.now(timezone.utc)
            )

            assert "instagram" in breakdown
            assert "twitter" in breakdown
            assert "tiktok" in breakdown
            assert breakdown["instagram"]["total"] == 3

    @pytest.mark.asyncio
    async def test_sentiment_distribution(self):
        """Test sentiment distribution calculation"""
        analytics = get_inbox_analytics_service()
        workspace_id = "test_workspace"

        today = datetime.now(timezone.utc).date()

        async with async_session_maker() as session:
            # Create messages with different sentiments
            sentiments = ["positive", "positive", "neutral", "negative"]
            for i, sentiment in enumerate(sentiments):
                msg = CommunityInboxMessage(
                    id=f"sentiment_msg_{i}",
                    workspace_id=workspace_id,
                    platform="instagram",
                    message_type="comment",
                    sender_username=f"user_{i}",
                    content=f"Message {i}",
                    sentiment_label=sentiment,
                    received_at=datetime.now(timezone.utc),
                    status="unread"
                )
                session.add(msg)

            await session.commit()

            # Get distribution
            distribution = await analytics.get_sentiment_distribution(
                workspace_id,
                start_date=today.isoformat(),
                end_date=today.isoformat()
            )

            assert len(distribution) > 0

    @pytest.mark.asyncio
    async def test_response_time_stats(self):
        """Test response time statistics"""
        analytics = get_inbox_analytics_service()
        workspace_id = "test_workspace"

        async with async_session_maker() as session:
            # Create messages with response times
            response_times = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
            for i, rt in enumerate(response_times):
                msg = CommunityInboxMessage(
                    id=f"rt_msg_{i}",
                    workspace_id=workspace_id,
                    platform="instagram",
                    message_type="comment",
                    sender_username=f"user_{i}",
                    content=f"Message {i}",
                    response_time_minutes=rt,
                    responded_at=datetime.now(timezone.utc),
                    received_at=datetime.now(timezone.utc),
                    status="replied"
                )
                session.add(msg)

            await session.commit()

            # Get stats
            stats = await analytics.get_response_time_stats(workspace_id)

            assert stats["avg"] == 55.0
            assert stats["min"] == 10
            assert stats["max"] == 100
            assert stats["count"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
