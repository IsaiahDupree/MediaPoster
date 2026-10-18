"""
Unit Tests for Twitter Connector

Tests ADAPT-001, ADAPT-002 implementations.
"""

import pytest
import os
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

# Set test environment
os.environ["BLOTATO_API_KEY"] = "test_blotato_key"
os.environ["TWITTER_ACCOUNT_ID"] = "4151"
os.environ["TWITTER_BEARER_TOKEN"] = "test_bearer_token"

from connectors.twitter.connector import TwitterConnector
from connectors.base import ContentVariant, PlatformMetricSnapshot


class TestTwitterConnectorInit:
    """Test Twitter connector initialization"""

    def test_connector_id(self):
        """Test connector has correct ID"""
        connector = TwitterConnector()
        assert connector.id == "twitter"

    def test_connector_display_name(self):
        """Test connector has display name"""
        connector = TwitterConnector()
        assert connector.display_name == "Twitter/X"

    def test_supported_platforms(self):
        """Test connector supports Twitter platform"""
        connector = TwitterConnector()
        platforms = connector.list_supported_platforms()
        assert "twitter" in platforms
        assert len(platforms) == 1

    def test_is_enabled_with_blotato(self):
        """Test connector is enabled with Blotato API key"""
        connector = TwitterConnector()
        assert connector.is_enabled() is True

    def test_is_enabled_without_keys(self):
        """Test connector is disabled without API keys"""
        # Clear env vars
        old_blotato = os.environ.pop("BLOTATO_API_KEY", None)
        old_bearer = os.environ.pop("TWITTER_BEARER_TOKEN", None)

        connector = TwitterConnector()
        assert connector.is_enabled() is False

        # Restore
        if old_blotato:
            os.environ["BLOTATO_API_KEY"] = old_blotato
        if old_bearer:
            os.environ["TWITTER_BEARER_TOKEN"] = old_bearer


class TestTweetTextValidation:
    """Test tweet text validation and preparation"""

    def test_validate_tweet_text_valid(self):
        """Test valid tweet text passes validation"""
        connector = TwitterConnector()
        assert connector.validate_tweet_text("Hello, Twitter!") is True

    def test_validate_tweet_text_too_long(self):
        """Test tweet text exceeding 280 chars fails"""
        connector = TwitterConnector()
        long_text = "a" * 281
        assert connector.validate_tweet_text(long_text) is False

    def test_validate_tweet_text_exactly_280(self):
        """Test tweet text with exactly 280 chars passes"""
        connector = TwitterConnector()
        text = "a" * 280
        assert connector.validate_tweet_text(text) is True

    def test_prepare_tweet_text_from_title(self):
        """Test preparing tweet from variant title"""
        connector = TwitterConnector()
        variant = ContentVariant(
            content_id="test-123",
            platform="twitter",
            title="This is my tweet",
            description="This is a longer description"
        )
        text = connector._prepare_tweet_text(variant)
        assert text == "This is my tweet"

    def test_prepare_tweet_text_from_description(self):
        """Test preparing tweet from description when no title"""
        connector = TwitterConnector()
        variant = ContentVariant(
            content_id="test-123",
            platform="twitter",
            description="This is my description"
        )
        text = connector._prepare_tweet_text(variant)
        assert text == "This is my description"

    def test_prepare_tweet_text_truncate_long_title(self):
        """Test truncating long title to 280 chars"""
        connector = TwitterConnector()
        long_title = "a" * 300
        variant = ContentVariant(
            content_id="test-123",
            platform="twitter",
            title=long_title
        )
        text = connector._prepare_tweet_text(variant)
        assert len(text) == 280
        assert text.endswith("...")

    def test_split_into_thread(self):
        """Test splitting long text into thread"""
        connector = TwitterConnector()
        long_text = "First sentence. Second sentence. Third sentence. " * 20
        tweets = connector.split_into_thread(long_text, max_length=100)

        # Should create multiple tweets
        assert len(tweets) > 1

        # Each tweet should be <= 100 chars
        for tweet in tweets:
            assert len(tweet) <= 100


class TestPublishing:
    """Test tweet publishing functionality (ADAPT-001)"""

    @pytest.mark.asyncio
    async def test_publish_variant_success(self):
        """Test successful tweet publishing"""
        connector = TwitterConnector()

        # Mock Blotato API
        with patch.object(connector.blotato, 'publish_post', new_callable=AsyncMock) as mock_publish:
            mock_publish.return_value = {
                "postSubmissionId": "tweet_123456",
                "status": "submitted"
            }

            variant = ContentVariant(
                content_id="test-content",
                platform="twitter",
                title="Hello, Twitter! This is a test tweet.",
                media_url="https://example.com/image.jpg"
            )

            result = await connector.publish_variant(variant)

            # Verify result
            assert result["platform_post_id"] == "tweet_123456"
            assert result["status"] == "submitted"
            assert "twitter.com" in result["url"]

            # Verify Blotato API was called
            mock_publish.assert_called_once()
            call_args = mock_publish.call_args
            assert call_args.kwargs["account_id"] == "4151"

    @pytest.mark.asyncio
    async def test_publish_variant_text_too_long(self):
        """Test publishing fails with text > 280 chars"""
        connector = TwitterConnector()

        variant = ContentVariant(
            content_id="test-content",
            platform="twitter",
            title="a" * 281  # Too long
        )

        with pytest.raises(ValueError, match="exceeds 280 characters"):
            await connector.publish_variant(variant)

    @pytest.mark.asyncio
    async def test_publish_variant_no_blotato_key(self):
        """Test publishing fails without Blotato API key"""
        # Clear Blotato key
        old_key = os.environ.pop("BLOTATO_API_KEY", None)

        connector = TwitterConnector()

        variant = ContentVariant(
            content_id="test-content",
            platform="twitter",
            title="Test tweet"
        )

        with pytest.raises(RuntimeError, match="Blotato API key not configured"):
            await connector.publish_variant(variant)

        # Restore key
        if old_key:
            os.environ["BLOTATO_API_KEY"] = old_key

    @pytest.mark.asyncio
    async def test_publish_thread_success(self):
        """Test successful thread publishing"""
        connector = TwitterConnector()

        # Mock Blotato API
        with patch.object(connector.blotato, 'publish_post', new_callable=AsyncMock) as mock_publish:
            mock_publish.return_value = {
                "postSubmissionId": "thread_123456",
                "status": "submitted"
            }

            variant = ContentVariant(
                content_id="test-content",
                platform="twitter",
                title="First tweet in thread"
            )

            additional_tweets = [
                "Second tweet in thread",
                "Third tweet in thread"
            ]

            result = await connector.publish_thread(variant, additional_tweets)

            # Verify result
            assert result["platform_post_id"] == "thread_123456"
            assert result["thread_length"] == 3
            assert result["status"] == "submitted"

            # Verify Blotato API was called with thread
            mock_publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_thread_tweet_too_long(self):
        """Test thread publishing fails if any tweet > 280 chars"""
        connector = TwitterConnector()

        variant = ContentVariant(
            content_id="test-content",
            platform="twitter",
            title="First tweet"
        )

        additional_tweets = [
            "Second tweet",
            "a" * 281  # Third tweet too long
        ]

        with pytest.raises(ValueError, match="exceeds 280 characters"):
            await connector.publish_thread(variant, additional_tweets)


class TestMetricsFetching:
    """Test metrics fetching functionality (ADAPT-002)"""

    @pytest.mark.asyncio
    async def test_fetch_tweet_metrics_success(self):
        """Test successful metrics fetching"""
        connector = TwitterConnector()

        # Mock Twitter API response
        mock_response = {
            "data": {
                "id": "1234567890",
                "public_metrics": {
                    "like_count": 100,
                    "retweet_count": 25,
                    "reply_count": 10,
                    "quote_count": 5,
                    "bookmark_count": 15
                },
                "organic_metrics": {
                    "impression_count": 5000,
                    "url_link_clicks": 50,
                    "user_profile_clicks": 20
                }
            }
        }

        with patch.object(connector, '_fetch_tweet_metrics', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = {
                "impression_count": 5000,
                "like_count": 100,
                "retweet_count": 25,
                "reply_count": 10,
                "quote_count": 5,
                "bookmark_count": 15,
                "url_link_clicks": 50,
                "user_profile_clicks": 20
            }

            # Create variant with tweet ID using object.__setattr__ to bypass Pydantic
            variant = ContentVariant(
                content_id="test-content",
                platform="twitter"
            )
            object.__setattr__(variant, 'platform_post_id', "1234567890")

            snapshots = await connector.fetch_metrics_for_variant(variant)

            # Verify snapshot
            assert len(snapshots) == 1
            snapshot = snapshots[0]

            assert snapshot.platform == "twitter"
            assert snapshot.platform_post_id == "1234567890"
            assert snapshot.views == 5000
            assert snapshot.likes == 100
            assert snapshot.shares == 25
            assert snapshot.comments == 10
            assert snapshot.raw_payload["quote_count"] == 5
            assert snapshot.raw_payload["bookmark_count"] == 15

    @pytest.mark.asyncio
    async def test_fetch_metrics_no_bearer_token(self):
        """Test metrics fetching returns empty list without bearer token"""
        # Clear bearer token
        old_token = os.environ.pop("TWITTER_BEARER_TOKEN", None)
        old_access_token = os.environ.pop("TWITTER_ACCESS_TOKEN", None)

        connector = TwitterConnector()

        variant = ContentVariant(
            content_id="test-content",
            platform="twitter"
        )
        object.__setattr__(variant, 'platform_post_id', "1234567890")

        snapshots = await connector.fetch_metrics_for_variant(variant)

        # Should return empty list with warning
        assert len(snapshots) == 0

        # Restore tokens
        if old_token:
            os.environ["TWITTER_BEARER_TOKEN"] = old_token
        if old_access_token:
            os.environ["TWITTER_ACCESS_TOKEN"] = old_access_token

    @pytest.mark.asyncio
    async def test_fetch_metrics_no_tweet_id(self):
        """Test metrics fetching returns empty with no tweet ID"""
        connector = TwitterConnector()

        variant = ContentVariant(
            content_id="test-content",
            platform="twitter"
        )
        # No platform_post_id set

        snapshots = await connector.fetch_metrics_for_variant(variant)

        # Should return empty list
        assert len(snapshots) == 0


class TestDirectMessages:
    """Test DM functionality (ADAPT-003)"""

    @pytest.mark.asyncio
    async def test_send_dm_via_safari(self):
        """Test sending DM via Safari automation"""
        connector = TwitterConnector()

        with patch('connectors.twitter.connector.SafariTwitterDM') as mock_safari:
            mock_dm_instance = Mock()
            mock_dm_instance.send_dm.return_value = True
            mock_safari.return_value = mock_dm_instance

            result = await connector.send_dm("testuser", "Hello from MediaPoster!")

            # Verify success
            assert result["success"] is True
            assert result["method"] == "safari"
            assert result["timestamp"] is not None

            # Verify Safari automation was called
            mock_dm_instance.send_dm.assert_called_once_with("testuser", "Hello from MediaPoster!")

    @pytest.mark.asyncio
    async def test_send_dm_safari_failure(self):
        """Test DM sending fails when Safari automation fails"""
        connector = TwitterConnector()

        with patch('connectors.twitter.connector.SafariTwitterDM') as mock_safari:
            mock_dm_instance = Mock()
            mock_dm_instance.send_dm.return_value = False  # Failed
            mock_safari.return_value = mock_dm_instance

            with pytest.raises(RuntimeError, match="Safari DM automation failed"):
                await connector.send_dm("testuser", "Hello")

    @pytest.mark.asyncio
    async def test_check_dm_inbox(self):
        """Test checking DM inbox"""
        connector = TwitterConnector()

        mock_conversations = [
            {"username": "user1", "preview": "Hey!", "unread": True},
            {"username": "user2", "preview": "Thanks", "unread": False}
        ]

        with patch('connectors.twitter.connector.SafariTwitterDM') as mock_safari:
            mock_dm_instance = Mock()
            mock_dm_instance.check_inbox.return_value = mock_conversations
            mock_safari.return_value = mock_dm_instance

            conversations = await connector.check_dm_inbox()

            # Verify conversations returned
            assert len(conversations) == 2
            assert conversations[0]["username"] == "user1"
            assert conversations[0]["unread"] is True
            assert conversations[1]["username"] == "user2"
            assert conversations[1]["unread"] is False

    @pytest.mark.asyncio
    async def test_get_unread_dm_count(self):
        """Test getting unread DM count"""
        connector = TwitterConnector()

        with patch('connectors.twitter.connector.SafariTwitterDM') as mock_safari:
            mock_dm_instance = Mock()
            mock_dm_instance.get_unread_count.return_value = 3
            mock_safari.return_value = mock_dm_instance

            count = await connector.get_unread_dm_count()

            # Verify count
            assert count == 3

    @pytest.mark.asyncio
    async def test_send_bulk_dms(self):
        """Test sending bulk DMs to multiple recipients"""
        connector = TwitterConnector()

        recipients = ["user1", "user2", "user3"]
        expected_results = {
            "user1": True,
            "user2": True,
            "user3": False  # Failed for user3
        }

        with patch('connectors.twitter.connector.SafariTwitterDM') as mock_safari:
            mock_dm_instance = Mock()
            mock_dm_instance.send_bulk_dms.return_value = expected_results
            mock_safari.return_value = mock_dm_instance

            results = await connector.send_bulk_dms(recipients, "Bulk message", delay_between=1.0)

            # Verify results
            assert results == expected_results
            assert results["user1"] is True
            assert results["user2"] is True
            assert results["user3"] is False

            # Verify Safari automation was called with correct params
            mock_dm_instance.send_bulk_dms.assert_called_once()
            call_args = mock_dm_instance.send_bulk_dms.call_args
            assert call_args[0][0] == recipients
            assert call_args[0][1] == "Bulk message"
            assert call_args[0][2] == 1.0

    @pytest.mark.asyncio
    async def test_get_user_id_by_username(self):
        """Test getting Twitter user ID from username"""
        connector = TwitterConnector()

        mock_response_data = {
            "data": {
                "id": "123456789",
                "username": "testuser"
            }
        }

        with patch('httpx.AsyncClient') as mock_client:
            mock_get = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.get = mock_get

            user_id = await connector._get_user_id_by_username("testuser")

            # Verify user ID
            assert user_id == "123456789"

            # Verify API was called correctly
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_dm_without_safari_fallback(self):
        """Test DM sending fails without Safari fallback enabled"""
        # Clear bearer token to force API path
        old_token = os.environ.pop("TWITTER_BEARER_TOKEN", None)

        connector = TwitterConnector()

        with pytest.raises(RuntimeError, match="Unable to send DM"):
            await connector.send_dm("testuser", "Hello", use_safari_fallback=False)

        # Restore token
        if old_token:
            os.environ["TWITTER_BEARER_TOKEN"] = old_token


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
