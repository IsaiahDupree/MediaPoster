"""
Platform Publishers Unit Tests
===============================
Tests for the platform publishing connectors
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
import json
from datetime import datetime

from services.platform_publishers import (
    PublishStatus,
    Platform,
    MediaType,
    PublishRequest,
    PublishResult,
    BasePlatformPublisher,
    TikTokPublisher,
    YouTubePublisher,
)


class TestPublishStatus:
    """Tests for PublishStatus enum"""

    def test_status_values(self):
        assert PublishStatus.PENDING == "pending"
        assert PublishStatus.UPLOADING == "uploading"
        assert PublishStatus.PROCESSING == "processing"
        assert PublishStatus.PUBLISHED == "published"
        assert PublishStatus.FAILED == "failed"
        assert PublishStatus.SCHEDULED == "scheduled"


class TestPlatform:
    """Tests for Platform enum"""

    def test_platform_values(self):
        assert Platform.TIKTOK == "tiktok"
        assert Platform.YOUTUBE == "youtube"
        assert Platform.INSTAGRAM == "instagram"
        assert Platform.TWITTER == "twitter"
        assert Platform.LINKEDIN == "linkedin"
        assert Platform.THREADS == "threads"


class TestMediaType:
    """Tests for MediaType enum"""

    def test_media_type_values(self):
        assert MediaType.VIDEO == "video"
        assert MediaType.IMAGE == "image"
        assert MediaType.CAROUSEL == "carousel"
        assert MediaType.STORY == "story"
        assert MediaType.REEL == "reel"
        assert MediaType.SHORT == "short"


class TestPublishRequest:
    """Tests for PublishRequest model"""

    def test_create_basic_request(self):
        request = PublishRequest(
            media_path="/path/to/video.mp4",
            media_type=MediaType.VIDEO,
            description="Test description",
            account_id="account-123",
            platform=Platform.TIKTOK,
        )
        
        assert request.media_path == "/path/to/video.mp4"
        assert request.media_type == MediaType.VIDEO
        assert request.description == "Test description"
        assert request.account_id == "account-123"
        assert request.platform == Platform.TIKTOK

    def test_default_values(self):
        request = PublishRequest(
            media_path="/path/to/video.mp4",
            media_type=MediaType.VIDEO,
            description="Test",
            account_id="account-123",
            platform=Platform.YOUTUBE,
        )
        
        assert request.title is None
        assert request.hashtags == []
        assert request.scheduled_time is None
        assert request.thumbnail_path is None
        assert request.privacy == "public"
        assert request.metadata == {}

    def test_full_request(self):
        request = PublishRequest(
            media_path="/path/to/video.mp4",
            media_type=MediaType.REEL,
            title="My Video Title",
            description="Full description",
            hashtags=["#fyp", "#viral"],
            account_id="account-123",
            platform=Platform.INSTAGRAM,
            scheduled_time="2026-01-20T10:00:00Z",
            thumbnail_path="/path/to/thumb.jpg",
            privacy="unlisted",
            metadata={"category": "entertainment"},
        )
        
        assert request.title == "My Video Title"
        assert len(request.hashtags) == 2
        assert request.scheduled_time == "2026-01-20T10:00:00Z"
        assert request.thumbnail_path == "/path/to/thumb.jpg"
        assert request.privacy == "unlisted"
        assert request.metadata["category"] == "entertainment"


class TestPublishResult:
    """Tests for PublishResult model"""

    def test_successful_result(self):
        result = PublishResult(
            success=True,
            status=PublishStatus.PUBLISHED,
            platform=Platform.TIKTOK,
            post_id="post-12345",
            post_url="https://tiktok.com/@user/video/12345",
            published_at="2026-01-13T20:00:00Z",
        )
        
        assert result.success is True
        assert result.status == PublishStatus.PUBLISHED
        assert result.post_id == "post-12345"
        assert result.post_url is not None

    def test_failed_result(self):
        result = PublishResult(
            success=False,
            status=PublishStatus.FAILED,
            platform=Platform.YOUTUBE,
            error_message="Upload quota exceeded",
        )
        
        assert result.success is False
        assert result.status == PublishStatus.FAILED
        assert result.error_message == "Upload quota exceeded"
        assert result.post_id is None


class TestTikTokPublisher:
    """Tests for TikTokPublisher"""

    @pytest.fixture
    def publisher(self):
        return TikTokPublisher(credentials={"access_token": "test-token"})

    @pytest.fixture
    def publish_request(self):
        return PublishRequest(
            media_path="/path/to/video.mp4",
            media_type=MediaType.VIDEO,
            description="Test video",
            hashtags=["#fyp", "#test"],
            account_id="account-123",
            platform=Platform.TIKTOK,
        )

    def test_platform_attribute(self, publisher):
        assert publisher.platform == Platform.TIKTOK

    def test_api_base_url(self, publisher):
        assert publisher.API_BASE == "https://open.tiktokapis.com/v2"

    @pytest.mark.asyncio
    async def test_publish_missing_token(self, publish_request):
        publisher = TikTokPublisher(credentials={})
        result = await publisher.publish(publish_request)
        
        assert result.success is False
        assert result.status == PublishStatus.FAILED
        assert "Missing access token" in result.error_message

    @pytest.mark.asyncio
    async def test_publish_success(self, publisher, publish_request):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "upload_url": "https://upload.tiktok.com/test",
                "publish_id": "publish-123",
            }
        }
        
        mock_upload_response = MagicMock()
        mock_upload_response.status_code = 200
        
        with patch.object(publisher, '_get_client') as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(side_effect=[mock_response, mock_response])
            client.put = AsyncMock(return_value=mock_upload_response)
            mock_client.return_value = client
            
            with patch('os.path.getsize', return_value=1000000):
                with patch('builtins.open', mock_open(read_data=b'video data')):
                    result = await publisher.publish(publish_request)
        
        assert result.success is True
        assert result.status == PublishStatus.PUBLISHED
        assert result.platform == Platform.TIKTOK

    @pytest.mark.asyncio
    async def test_publish_init_failure(self, publisher, publish_request):
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        
        with patch.object(publisher, '_get_client') as mock_client:
            client = AsyncMock()
            client.post = AsyncMock(return_value=mock_response)
            mock_client.return_value = client
            
            with patch('os.path.getsize', return_value=1000000):
                result = await publisher.publish(publish_request)
        
        assert result.success is False
        assert result.status == PublishStatus.FAILED
        assert "Init failed" in result.error_message

    @pytest.mark.asyncio
    async def test_validate_credentials_success(self, publisher):
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(publisher, '_get_client') as mock_client:
            client = AsyncMock()
            client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = client
            
            result = await publisher.validate_credentials()
        
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_credentials_failure(self, publisher):
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        with patch.object(publisher, '_get_client') as mock_client:
            client = AsyncMock()
            client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = client
            
            result = await publisher.validate_credentials()
        
        assert result is False

    @pytest.mark.asyncio
    async def test_get_account_info_success(self, publisher):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "user": {
                    "display_name": "Test User",
                    "follower_count": 10000,
                }
            }
        }
        
        with patch.object(publisher, '_get_client') as mock_client:
            client = AsyncMock()
            client.get = AsyncMock(return_value=mock_response)
            mock_client.return_value = client
            
            result = await publisher.get_account_info()
        
        assert result["display_name"] == "Test User"
        assert result["follower_count"] == 10000

    @pytest.mark.asyncio
    async def test_close_client(self, publisher):
        publisher._client = AsyncMock()
        await publisher.close()
        
        assert publisher._client is None


class TestYouTubePublisher:
    """Tests for YouTubePublisher"""

    @pytest.fixture
    def publisher(self):
        return YouTubePublisher(credentials={"access_token": "test-token"})

    @pytest.fixture
    def publish_request(self):
        return PublishRequest(
            media_path="/path/to/video.mp4",
            media_type=MediaType.VIDEO,
            title="My YouTube Video",
            description="Test description for YouTube",
            hashtags=["#shorts", "#viral"],
            account_id="channel-123",
            platform=Platform.YOUTUBE,
        )

    def test_platform_attribute(self, publisher):
        assert publisher.platform == Platform.YOUTUBE

    def test_api_base_url(self, publisher):
        assert publisher.API_BASE == "https://www.googleapis.com/youtube/v3"

    def test_upload_url(self, publisher):
        assert publisher.UPLOAD_URL == "https://www.googleapis.com/upload/youtube/v3/videos"

    def test_chunk_size(self, publisher):
        assert publisher.CHUNK_SIZE == 10 * 1024 * 1024  # 10MB

    def test_max_retries(self, publisher):
        assert publisher.MAX_RETRIES == 5


class TestBasePlatformPublisher:
    """Tests for base publisher functionality"""

    @pytest.mark.asyncio
    async def test_get_client_creates_client(self):
        publisher = TikTokPublisher(credentials={"access_token": "test"})
        
        client = await publisher._get_client()
        
        assert client is not None
        assert publisher._client is client
        
        await publisher.close()

    @pytest.mark.asyncio
    async def test_get_client_reuses_existing(self):
        publisher = TikTokPublisher(credentials={"access_token": "test"})
        
        client1 = await publisher._get_client()
        client2 = await publisher._get_client()
        
        assert client1 is client2
        
        await publisher.close()


class TestPublishResultMetadata:
    """Tests for result metadata handling"""

    def test_result_with_metadata(self):
        result = PublishResult(
            success=True,
            status=PublishStatus.PUBLISHED,
            platform=Platform.INSTAGRAM,
            post_id="ig-12345",
            metadata={
                "media_id": "media-123",
                "permalink": "https://instagram.com/p/abc",
                "likes_count": 0,
            }
        )
        
        assert result.metadata["media_id"] == "media-123"
        assert "permalink" in result.metadata

    def test_default_empty_metadata(self):
        result = PublishResult(
            success=True,
            status=PublishStatus.PUBLISHED,
            platform=Platform.TWITTER,
        )
        
        assert result.metadata == {}


class TestPublishRequestValidation:
    """Tests for request validation"""

    def test_required_fields(self):
        with pytest.raises(ValueError):
            PublishRequest()

    def test_platform_validation(self):
        request = PublishRequest(
            media_path="/path/to/video.mp4",
            media_type=MediaType.VIDEO,
            description="Test",
            account_id="123",
            platform=Platform.THREADS,
        )
        
        assert request.platform == Platform.THREADS
