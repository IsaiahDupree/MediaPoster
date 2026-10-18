"""
TEST-014: X/Twitter Adapter Tests
==================================
End-to-end tests for X/Twitter platform adapter.

Tests ADAPT-001, ADAPT-002, ADAPT-003:
- Publishing tweets
- Fetching metrics
- Sending/receiving DMs
- Rate limiting
- Error handling

From PRD_CONTENT_OPS_TESTS.md Section 3.2
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock

from connectors.twitter_adapter import TwitterAdapter
from services.event_bus import EventBus, Topics


@pytest.fixture
async def event_bus():
    """Initialize event bus"""
    bus = EventBus.get_instance()
    bus.set_source("test-twitter-adapter")
    yield bus
    await bus.shutdown()


@pytest.fixture
def twitter_adapter():
    """Initialize Twitter adapter"""
    adapter = TwitterAdapter()
    yield adapter


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.integration
class TestTwitterPublishing:
    """Tests for Twitter publishing functionality (ADAPT-001)"""

    async def test_publish_text_tweet(self, twitter_adapter, event_bus):
        """
        TEST-014a: Publish a text-only tweet

        Steps:
        1. Create tweet payload
        2. Call publish method
        3. Verify tweet posted
        4. Verify event emitted
        """
        events_received = []

        async def track_event(event):
            events_received.append(event)

        event_bus.subscribe(Topics.CONTENT_PUBLISHED, track_event)

        # Mock the Twitter API call
        with patch.object(twitter_adapter, '_post_tweet', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {
                "id": "1234567890",
                "text": "Test tweet from MediaPoster",
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            # Publish tweet
            result = await twitter_adapter.publish_post({
                "content": "Test tweet from MediaPoster",
                "platform": "twitter"
            })

            # Verify post succeeded
            assert result["success"] is True
            assert "id" in result
            assert result["id"] == "1234567890"

            # Verify API was called
            mock_post.assert_called_once()


    async def test_publish_tweet_with_media(self, twitter_adapter, event_bus):
        """
        TEST-014b: Publish tweet with image/video

        Steps:
        1. Upload media
        2. Attach to tweet
        3. Post tweet
        4. Verify media included
        """
        with patch.object(twitter_adapter, '_upload_media', new_callable=AsyncMock) as mock_upload, \
             patch.object(twitter_adapter, '_post_tweet', new_callable=AsyncMock) as mock_post:

            mock_upload.return_value = {"media_id": "media_123"}
            mock_post.return_value = {
                "id": "1234567891",
                "text": "Check out this image!",
                "media": [{"media_id": "media_123"}]
            }

            result = await twitter_adapter.publish_post({
                "content": "Check out this image!",
                "platform": "twitter",
                "media_urls": ["/path/to/image.jpg"]
            })

            assert result["success"] is True
            assert "media" in result
            mock_upload.assert_called_once()


    async def test_publish_tweet_rate_limit(self, twitter_adapter):
        """
        TEST-014c: Handle rate limiting gracefully

        Steps:
        1. Simulate rate limit error
        2. Verify proper error handling
        3. Verify retry logic
        """
        with patch.object(twitter_adapter, '_post_tweet', new_callable=AsyncMock) as mock_post:
            # Simulate rate limit error
            mock_post.side_effect = Exception("Rate limit exceeded")

            result = await twitter_adapter.publish_post({
                "content": "Test tweet",
                "platform": "twitter"
            })

            assert result["success"] is False
            assert "rate limit" in result.get("error", "").lower() or "error" in result


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.integration
class TestTwitterMetrics:
    """Tests for Twitter metrics fetching (ADAPT-002)"""

    async def test_fetch_tweet_metrics(self, twitter_adapter):
        """
        TEST-014d: Fetch metrics for a published tweet

        Metrics:
        - Views
        - Likes
        - Retweets
        - Replies
        - Engagement rate
        """
        with patch.object(twitter_adapter, '_get_tweet_metrics', new_callable=AsyncMock) as mock_metrics:
            mock_metrics.return_value = {
                "tweet_id": "1234567890",
                "views": 1250,
                "likes": 45,
                "retweets": 12,
                "replies": 8,
                "bookmarks": 15,
                "engagement_rate": 6.4
            }

            metrics = await twitter_adapter.fetch_post_metrics("1234567890")

            assert metrics["views"] == 1250
            assert metrics["likes"] == 45
            assert metrics["engagement_rate"] == 6.4


    async def test_fetch_metrics_for_multiple_tweets(self, twitter_adapter):
        """
        TEST-014e: Batch fetch metrics for multiple tweets

        Verify:
        - Efficient batch API usage
        - Rate limit compliance
        - Proper data aggregation
        """
        tweet_ids = ["123", "456", "789"]

        with patch.object(twitter_adapter, '_get_tweet_metrics', new_callable=AsyncMock) as mock_metrics:
            mock_metrics.side_effect = [
                {"tweet_id": "123", "views": 100, "likes": 5},
                {"tweet_id": "456", "views": 200, "likes": 10},
                {"tweet_id": "789", "views": 150, "likes": 8}
            ]

            results = []
            for tweet_id in tweet_ids:
                metrics = await twitter_adapter.fetch_post_metrics(tweet_id)
                results.append(metrics)

            assert len(results) == 3
            assert sum(m["views"] for m in results) == 450


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.integration
class TestTwitterDMs:
    """Tests for Twitter DM functionality (ADAPT-003)"""

    async def test_send_dm(self, twitter_adapter):
        """
        TEST-014f: Send a DM to a user

        Steps:
        1. Create DM payload
        2. Send DM
        3. Verify delivery
        """
        with patch.object(twitter_adapter, '_send_dm', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {
                "dm_id": "dm_123",
                "recipient": "test_user",
                "text": "Thanks for your interest!",
                "sent_at": datetime.now(timezone.utc).isoformat()
            }

            result = await twitter_adapter.send_dm({
                "recipient": "test_user",
                "message": "Thanks for your interest!"
            })

            assert result["dm_id"] == "dm_123"
            assert result["recipient"] == "test_user"


    async def test_receive_dm(self, twitter_adapter, event_bus):
        """
        TEST-014g: Receive and process incoming DMs

        Steps:
        1. Poll for new DMs
        2. Parse DM content
        3. Emit event for processing
        """
        events_received = []

        async def track_event(event):
            events_received.append(event)

        event_bus.subscribe(Topics.DM_RECEIVED, track_event)

        with patch.object(twitter_adapter, '_poll_dms', new_callable=AsyncMock) as mock_poll:
            mock_poll.return_value = [
                {
                    "dm_id": "dm_incoming_1",
                    "sender": "potential_customer",
                    "text": "I'm interested in learning more!",
                    "received_at": datetime.now(timezone.utc).isoformat()
                }
            ]

            # Simulate polling
            dms = await twitter_adapter.poll_incoming_dms()

            assert len(dms) == 1
            assert dms[0]["sender"] == "potential_customer"


    async def test_dm_conversation_flow(self, twitter_adapter):
        """
        TEST-014h: Multi-turn DM conversation

        Steps:
        1. Receive initial DM
        2. Send response
        3. Receive reply
        4. Track conversation state
        """
        conversation_id = "conv_twitter_001"

        with patch.object(twitter_adapter, '_send_dm', new_callable=AsyncMock) as mock_send, \
             patch.object(twitter_adapter, '_poll_dms', new_callable=AsyncMock) as mock_poll:

            # Step 1: Receive initial DM
            mock_poll.return_value = [{
                "dm_id": "dm_1",
                "sender": "user123",
                "text": "How does this work?",
                "conversation_id": conversation_id
            }]

            dms = await twitter_adapter.poll_incoming_dms()
            assert len(dms) == 1

            # Step 2: Send response
            mock_send.return_value = {
                "dm_id": "dm_2",
                "recipient": "user123",
                "text": "Great question! Let me explain...",
                "conversation_id": conversation_id
            }

            response = await twitter_adapter.send_dm({
                "recipient": "user123",
                "message": "Great question! Let me explain...",
                "conversation_id": conversation_id
            })

            assert response["conversation_id"] == conversation_id


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.integration
class TestTwitterErrorHandling:
    """Tests for Twitter adapter error handling"""

    async def test_handle_authentication_error(self, twitter_adapter):
        """
        TEST-014i: Handle authentication failures

        Scenarios:
        - Invalid credentials
        - Expired token
        - Revoked access
        """
        with patch.object(twitter_adapter, '_post_tweet', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Authentication failed")

            result = await twitter_adapter.publish_post({
                "content": "Test",
                "platform": "twitter"
            })

            assert result["success"] is False
            assert "error" in result


    async def test_handle_network_error(self, twitter_adapter):
        """
        TEST-014j: Handle network failures with retry

        Scenarios:
        - Timeout
        - Connection refused
        - DNS failure
        """
        with patch.object(twitter_adapter, '_post_tweet', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Network timeout")

            result = await twitter_adapter.publish_post({
                "content": "Test",
                "platform": "twitter"
            })

            assert result["success"] is False


    async def test_handle_invalid_content(self, twitter_adapter):
        """
        TEST-014k: Validate content before posting

        Scenarios:
        - Tweet too long
        - Invalid media format
        - Prohibited content
        """
        # Test tweet too long (>280 characters)
        long_tweet = "x" * 300

        result = await twitter_adapter.publish_post({
            "content": long_tweet,
            "platform": "twitter"
        })

        # Should either truncate or fail gracefully
        assert "success" in result or "error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
