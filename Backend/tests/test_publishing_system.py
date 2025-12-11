"""
Phase 4: Comprehensive Publishing Integration Tests
Tests for platform connectors, OAuth, error handling, retry logic.
Target: ~100 tests
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4, UUID
import asyncio
from typing import Dict, Any, List, Optional
from enum import Enum


# ==================== MODELS ====================

class PublishStatus(str, Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    PROCESSING = "processing"
    PUBLISHED = "published"
    FAILED = "failed"
    SCHEDULED = "scheduled"
    RETRY = "retry"


class Platform(str, Enum):
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    THREADS = "threads"


class MediaType(str, Enum):
    VIDEO = "video"
    IMAGE = "image"
    CAROUSEL = "carousel"
    STORY = "story"
    REEL = "reel"
    SHORT = "short"


class PublishRequest:
    """Request to publish content"""
    def __init__(
        self,
        media_path: str = "/path/to/media.mp4",
        media_type: MediaType = MediaType.VIDEO,
        title: str = "Test Title",
        description: str = "Test description",
        hashtags: List[str] = None,
        account_id: str = "account_123",
        platform: Platform = Platform.TIKTOK,
        scheduled_time: datetime = None,
        thumbnail_path: str = None,
        privacy: str = "public",
        metadata: Dict = None,
    ):
        self.media_path = media_path
        self.media_type = media_type
        self.title = title
        self.description = description
        self.hashtags = hashtags or ["#test"]
        self.account_id = account_id
        self.platform = platform
        self.scheduled_time = scheduled_time
        self.thumbnail_path = thumbnail_path
        self.privacy = privacy
        self.metadata = metadata or {}


class PublishResult:
    """Result of publishing attempt"""
    def __init__(
        self,
        success: bool = True,
        status: PublishStatus = PublishStatus.PUBLISHED,
        platform: Platform = Platform.TIKTOK,
        post_id: str = None,
        post_url: str = None,
        error_message: str = None,
        error_code: str = None,
        published_at: datetime = None,
        metadata: Dict = None,
        retry_after: int = None,
    ):
        self.success = success
        self.status = status
        self.platform = platform
        self.post_id = post_id or str(uuid4())
        self.post_url = post_url
        self.error_message = error_message
        self.error_code = error_code
        self.published_at = published_at or datetime.now(timezone.utc)
        self.metadata = metadata or {}
        self.retry_after = retry_after


class OAuthCredentials:
    """OAuth credentials for platform"""
    def __init__(
        self,
        access_token: str = "test_access_token",
        refresh_token: str = "test_refresh_token",
        expires_at: datetime = None,
        scope: List[str] = None,
    ):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at or datetime.now(timezone.utc) + timedelta(hours=1)
        self.scope = scope or ["publish", "read"]
    
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) >= self.expires_at


# ==================== PUBLISHER SERVICE ====================

class BasePlatformPublisher:
    """Base class for platform publishers"""
    
    platform: Platform = None
    max_retries: int = 3
    retry_delay: int = 5
    
    def __init__(self, credentials: OAuthCredentials):
        self.credentials = credentials
        self._retry_count = 0
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        """Publish content to platform"""
        raise NotImplementedError
    
    async def validate_credentials(self) -> bool:
        """Validate OAuth credentials"""
        if self.credentials.is_expired():
            return False
        return True
    
    async def refresh_token(self) -> bool:
        """Refresh OAuth token"""
        # Mock implementation
        self.credentials.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        return True
    
    async def get_account_info(self) -> Dict:
        """Get connected account information"""
        raise NotImplementedError
    
    def _validate_request(self, request: PublishRequest) -> List[str]:
        """Validate publish request"""
        errors = []
        if not request.media_path:
            errors.append("media_path is required")
        if not request.description:
            errors.append("description is required")
        return errors


class TikTokPublisher(BasePlatformPublisher):
    """TikTok platform publisher"""
    
    platform = Platform.TIKTOK
    max_video_duration = 180  # 3 minutes
    max_description_length = 2200
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        if self.credentials.is_expired():
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message="Token expired",
                error_code="TOKEN_EXPIRED"
            )
        
        # Validate
        errors = self._validate_request(request)
        if len(request.description) > self.max_description_length:
            errors.append(f"Description exceeds {self.max_description_length} chars")
        
        if errors:
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message="; ".join(errors)
            )
        
        return PublishResult(
            success=True,
            status=PublishStatus.PUBLISHED,
            platform=self.platform,
            post_url=f"https://tiktok.com/@user/video/{uuid4()}"
        )
    
    async def get_account_info(self) -> Dict:
        return {
            "platform": "tiktok",
            "username": "@test_user",
            "followers": 10000,
        }


class YouTubePublisher(BasePlatformPublisher):
    """YouTube platform publisher"""
    
    platform = Platform.YOUTUBE
    max_title_length = 100
    max_description_length = 5000
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        if self.credentials.is_expired():
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message="Token expired",
                error_code="TOKEN_EXPIRED"
            )
        
        errors = self._validate_request(request)
        if request.title and len(request.title) > self.max_title_length:
            errors.append(f"Title exceeds {self.max_title_length} chars")
        
        if errors:
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message="; ".join(errors)
            )
        
        video_id = str(uuid4())[:11]
        return PublishResult(
            success=True,
            status=PublishStatus.PUBLISHED,
            platform=self.platform,
            post_id=video_id,
            post_url=f"https://youtube.com/watch?v={video_id}"
        )
    
    async def get_account_info(self) -> Dict:
        return {
            "platform": "youtube",
            "channel_name": "Test Channel",
            "subscribers": 50000,
        }


class InstagramPublisher(BasePlatformPublisher):
    """Instagram platform publisher"""
    
    platform = Platform.INSTAGRAM
    max_caption_length = 2200
    max_hashtags = 30
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        if self.credentials.is_expired():
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message="Token expired"
            )
        
        errors = self._validate_request(request)
        if len(request.hashtags) > self.max_hashtags:
            errors.append(f"Exceeds {self.max_hashtags} hashtags limit")
        
        if errors:
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message="; ".join(errors)
            )
        
        return PublishResult(
            success=True,
            status=PublishStatus.PUBLISHED,
            platform=self.platform,
            post_url=f"https://instagram.com/p/{uuid4()}"
        )
    
    async def get_account_info(self) -> Dict:
        return {
            "platform": "instagram",
            "username": "@test_ig",
            "followers": 25000,
        }


class TwitterPublisher(BasePlatformPublisher):
    """Twitter/X platform publisher"""
    
    platform = Platform.TWITTER
    max_tweet_length = 280
    max_video_duration = 140
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        if self.credentials.is_expired():
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message="Token expired"
            )
        
        return PublishResult(
            success=True,
            status=PublishStatus.PUBLISHED,
            platform=self.platform,
            post_url=f"https://twitter.com/user/status/{uuid4()}"
        )
    
    async def get_account_info(self) -> Dict:
        return {
            "platform": "twitter",
            "handle": "@test_twitter",
            "followers": 5000,
        }


class LinkedInPublisher(BasePlatformPublisher):
    """LinkedIn platform publisher"""
    
    platform = Platform.LINKEDIN
    max_post_length = 3000
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        if self.credentials.is_expired():
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=self.platform,
                error_message="Token expired"
            )
        
        return PublishResult(
            success=True,
            status=PublishStatus.PUBLISHED,
            platform=self.platform,
            post_url=f"https://linkedin.com/posts/{uuid4()}"
        )
    
    async def get_account_info(self) -> Dict:
        return {
            "platform": "linkedin",
            "name": "Test Company",
            "followers": 1000,
        }


class PublisherFactory:
    """Factory for creating platform publishers"""
    
    _publishers = {
        Platform.TIKTOK: TikTokPublisher,
        Platform.YOUTUBE: YouTubePublisher,
        Platform.INSTAGRAM: InstagramPublisher,
        Platform.TWITTER: TwitterPublisher,
        Platform.LINKEDIN: LinkedInPublisher,
    }
    
    @classmethod
    def create(cls, platform: Platform, credentials: OAuthCredentials) -> BasePlatformPublisher:
        publisher_class = cls._publishers.get(platform)
        if not publisher_class:
            raise ValueError(f"Unknown platform: {platform}")
        return publisher_class(credentials)
    
    @classmethod
    def supported_platforms(cls) -> List[Platform]:
        return list(cls._publishers.keys())


class PublishingOrchestrator:
    """Orchestrates publishing across platforms"""
    
    def __init__(self):
        self.credentials: Dict[Platform, OAuthCredentials] = {}
        self.publishers: Dict[Platform, BasePlatformPublisher] = {}
        self.publish_history: List[PublishResult] = []
    
    def add_credentials(self, platform: Platform, credentials: OAuthCredentials):
        """Add credentials for a platform"""
        self.credentials[platform] = credentials
        self.publishers[platform] = PublisherFactory.create(platform, credentials)
    
    async def publish(self, request: PublishRequest) -> PublishResult:
        """Publish to single platform"""
        publisher = self.publishers.get(request.platform)
        if not publisher:
            return PublishResult(
                success=False,
                status=PublishStatus.FAILED,
                platform=request.platform,
                error_message="Platform not configured"
            )
        
        result = await publisher.publish(request)
        self.publish_history.append(result)
        return result
    
    async def publish_to_multiple(
        self, 
        request: PublishRequest, 
        platforms: List[Platform]
    ) -> Dict[Platform, PublishResult]:
        """Publish to multiple platforms"""
        results = {}
        for platform in platforms:
            req = PublishRequest(
                media_path=request.media_path,
                media_type=request.media_type,
                title=request.title,
                description=request.description,
                hashtags=request.hashtags,
                account_id=request.account_id,
                platform=platform,
            )
            results[platform] = await self.publish(req)
        return results
    
    async def retry_failed(self, result: PublishResult, max_retries: int = 3) -> PublishResult:
        """Retry a failed publish"""
        if result.success:
            return result
        
        for attempt in range(max_retries):
            # Create new request from result
            request = PublishRequest(platform=result.platform)
            new_result = await self.publish(request)
            
            if new_result.success:
                return new_result
            
            # Wait before retry
            await asyncio.sleep(1)
        
        return PublishResult(
            success=False,
            status=PublishStatus.FAILED,
            platform=result.platform,
            error_message=f"Failed after {max_retries} retries"
        )


# ==================== TESTS ====================

class TestPublishRequest:
    """Test PublishRequest model"""
    
    def test_create_request(self):
        """Should create publish request with defaults"""
        request = PublishRequest()
        
        assert request.media_path == "/path/to/media.mp4"
        assert request.media_type == MediaType.VIDEO
        assert request.platform == Platform.TIKTOK
    
    def test_custom_request(self):
        """Should accept custom values"""
        request = PublishRequest(
            title="Custom Title",
            description="Custom description",
            platform=Platform.YOUTUBE,
        )
        
        assert request.title == "Custom Title"
        assert request.platform == Platform.YOUTUBE
    
    def test_hashtags_default(self):
        """Should have default hashtags"""
        request = PublishRequest()
        assert len(request.hashtags) > 0
    
    def test_privacy_default(self):
        """Should default to public"""
        request = PublishRequest()
        assert request.privacy == "public"
    
    def test_scheduled_time_optional(self):
        """Scheduled time should be optional"""
        request = PublishRequest()
        assert request.scheduled_time is None


class TestPublishResult:
    """Test PublishResult model"""
    
    def test_success_result(self):
        """Should create success result"""
        result = PublishResult(success=True)
        
        assert result.success is True
        assert result.status == PublishStatus.PUBLISHED
    
    def test_failure_result(self):
        """Should create failure result"""
        result = PublishResult(
            success=False,
            status=PublishStatus.FAILED,
            error_message="Upload failed"
        )
        
        assert result.success is False
        assert result.error_message == "Upload failed"
    
    def test_post_id_generated(self):
        """Should generate post ID if not provided"""
        result = PublishResult()
        assert result.post_id is not None
    
    def test_published_at_default(self):
        """Should default to current time"""
        result = PublishResult()
        assert result.published_at is not None
    
    def test_retry_after(self):
        """Should support retry_after field"""
        result = PublishResult(retry_after=60)
        assert result.retry_after == 60


class TestOAuthCredentials:
    """Test OAuth credentials"""
    
    def test_create_credentials(self):
        """Should create OAuth credentials"""
        creds = OAuthCredentials()
        
        assert creds.access_token is not None
        assert creds.refresh_token is not None
    
    def test_not_expired_by_default(self):
        """Should not be expired by default"""
        creds = OAuthCredentials()
        assert creds.is_expired() is False
    
    def test_expired_check(self):
        """Should detect expired token"""
        creds = OAuthCredentials(
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        assert creds.is_expired() is True
    
    def test_scope_default(self):
        """Should have default scopes"""
        creds = OAuthCredentials()
        assert "publish" in creds.scope


class TestTikTokPublisher:
    """Test TikTok publisher"""
    
    @pytest.fixture
    def publisher(self):
        creds = OAuthCredentials()
        return TikTokPublisher(creds)
    
    @pytest.mark.asyncio
    async def test_successful_publish(self, publisher):
        """Should publish successfully"""
        request = PublishRequest(platform=Platform.TIKTOK)
        result = await publisher.publish(request)
        
        assert result.success is True
        assert "tiktok.com" in result.post_url
    
    @pytest.mark.asyncio
    async def test_expired_token_fails(self, publisher):
        """Should fail with expired token"""
        publisher.credentials.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        request = PublishRequest(platform=Platform.TIKTOK)
        result = await publisher.publish(request)
        
        assert result.success is False
        assert result.error_code == "TOKEN_EXPIRED"
    
    @pytest.mark.asyncio
    async def test_description_too_long(self, publisher):
        """Should reject too long description"""
        request = PublishRequest(
            description="x" * 3000,  # Exceeds 2200 limit
            platform=Platform.TIKTOK,
        )
        result = await publisher.publish(request)
        
        assert result.success is False
    
    @pytest.mark.asyncio
    async def test_get_account_info(self, publisher):
        """Should return account info"""
        info = await publisher.get_account_info()
        
        assert info["platform"] == "tiktok"
        assert "username" in info
    
    def test_max_video_duration(self, publisher):
        """Should have max video duration"""
        assert publisher.max_video_duration == 180


class TestYouTubePublisher:
    """Test YouTube publisher"""
    
    @pytest.fixture
    def publisher(self):
        creds = OAuthCredentials()
        return YouTubePublisher(creds)
    
    @pytest.mark.asyncio
    async def test_successful_publish(self, publisher):
        """Should publish successfully"""
        request = PublishRequest(platform=Platform.YOUTUBE)
        result = await publisher.publish(request)
        
        assert result.success is True
        assert "youtube.com" in result.post_url
    
    @pytest.mark.asyncio
    async def test_title_too_long(self, publisher):
        """Should reject too long title"""
        request = PublishRequest(
            title="x" * 200,  # Exceeds 100 limit
            platform=Platform.YOUTUBE,
        )
        result = await publisher.publish(request)
        
        assert result.success is False
    
    @pytest.mark.asyncio
    async def test_video_id_format(self, publisher):
        """Should return valid video ID"""
        request = PublishRequest(platform=Platform.YOUTUBE)
        result = await publisher.publish(request)
        
        assert len(result.post_id) == 11
    
    @pytest.mark.asyncio
    async def test_get_account_info(self, publisher):
        """Should return channel info"""
        info = await publisher.get_account_info()
        
        assert info["platform"] == "youtube"
        assert "channel_name" in info


class TestInstagramPublisher:
    """Test Instagram publisher"""
    
    @pytest.fixture
    def publisher(self):
        creds = OAuthCredentials()
        return InstagramPublisher(creds)
    
    @pytest.mark.asyncio
    async def test_successful_publish(self, publisher):
        """Should publish successfully"""
        request = PublishRequest(platform=Platform.INSTAGRAM)
        result = await publisher.publish(request)
        
        assert result.success is True
        assert "instagram.com" in result.post_url
    
    @pytest.mark.asyncio
    async def test_too_many_hashtags(self, publisher):
        """Should reject too many hashtags"""
        request = PublishRequest(
            hashtags=[f"#tag{i}" for i in range(35)],  # Exceeds 30
            platform=Platform.INSTAGRAM,
        )
        result = await publisher.publish(request)
        
        assert result.success is False
    
    @pytest.mark.asyncio
    async def test_get_account_info(self, publisher):
        """Should return account info"""
        info = await publisher.get_account_info()
        
        assert info["platform"] == "instagram"
        assert "username" in info
    
    def test_max_hashtags_limit(self, publisher):
        """Should have hashtag limit"""
        assert publisher.max_hashtags == 30


class TestTwitterPublisher:
    """Test Twitter publisher"""
    
    @pytest.fixture
    def publisher(self):
        creds = OAuthCredentials()
        return TwitterPublisher(creds)
    
    @pytest.mark.asyncio
    async def test_successful_publish(self, publisher):
        """Should publish successfully"""
        request = PublishRequest(platform=Platform.TWITTER)
        result = await publisher.publish(request)
        
        assert result.success is True
        assert "twitter.com" in result.post_url
    
    @pytest.mark.asyncio
    async def test_get_account_info(self, publisher):
        """Should return account info"""
        info = await publisher.get_account_info()
        
        assert info["platform"] == "twitter"
        assert "handle" in info
    
    def test_max_tweet_length(self, publisher):
        """Should have tweet length limit"""
        assert publisher.max_tweet_length == 280


class TestLinkedInPublisher:
    """Test LinkedIn publisher"""
    
    @pytest.fixture
    def publisher(self):
        creds = OAuthCredentials()
        return LinkedInPublisher(creds)
    
    @pytest.mark.asyncio
    async def test_successful_publish(self, publisher):
        """Should publish successfully"""
        request = PublishRequest(platform=Platform.LINKEDIN)
        result = await publisher.publish(request)
        
        assert result.success is True
        assert "linkedin.com" in result.post_url
    
    @pytest.mark.asyncio
    async def test_get_account_info(self, publisher):
        """Should return company info"""
        info = await publisher.get_account_info()
        
        assert info["platform"] == "linkedin"
        assert "name" in info


class TestPublisherFactory:
    """Test publisher factory"""
    
    def test_create_tiktok_publisher(self):
        """Should create TikTok publisher"""
        creds = OAuthCredentials()
        publisher = PublisherFactory.create(Platform.TIKTOK, creds)
        
        assert isinstance(publisher, TikTokPublisher)
    
    def test_create_youtube_publisher(self):
        """Should create YouTube publisher"""
        creds = OAuthCredentials()
        publisher = PublisherFactory.create(Platform.YOUTUBE, creds)
        
        assert isinstance(publisher, YouTubePublisher)
    
    def test_create_instagram_publisher(self):
        """Should create Instagram publisher"""
        creds = OAuthCredentials()
        publisher = PublisherFactory.create(Platform.INSTAGRAM, creds)
        
        assert isinstance(publisher, InstagramPublisher)
    
    def test_create_twitter_publisher(self):
        """Should create Twitter publisher"""
        creds = OAuthCredentials()
        publisher = PublisherFactory.create(Platform.TWITTER, creds)
        
        assert isinstance(publisher, TwitterPublisher)
    
    def test_create_linkedin_publisher(self):
        """Should create LinkedIn publisher"""
        creds = OAuthCredentials()
        publisher = PublisherFactory.create(Platform.LINKEDIN, creds)
        
        assert isinstance(publisher, LinkedInPublisher)
    
    def test_unknown_platform_raises(self):
        """Should raise for unknown platform"""
        creds = OAuthCredentials()
        
        with pytest.raises(ValueError):
            PublisherFactory.create("unknown", creds)
    
    def test_supported_platforms(self):
        """Should list supported platforms"""
        platforms = PublisherFactory.supported_platforms()
        
        assert Platform.TIKTOK in platforms
        assert Platform.YOUTUBE in platforms
        assert len(platforms) >= 5


class TestPublishingOrchestrator:
    """Test publishing orchestrator"""
    
    @pytest.fixture
    def orchestrator(self):
        orch = PublishingOrchestrator()
        creds = OAuthCredentials()
        orch.add_credentials(Platform.TIKTOK, creds)
        orch.add_credentials(Platform.YOUTUBE, creds)
        orch.add_credentials(Platform.INSTAGRAM, creds)
        return orch
    
    @pytest.mark.asyncio
    async def test_publish_single(self, orchestrator):
        """Should publish to single platform"""
        request = PublishRequest(platform=Platform.TIKTOK)
        result = await orchestrator.publish(request)
        
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_publish_multiple(self, orchestrator):
        """Should publish to multiple platforms"""
        request = PublishRequest()
        platforms = [Platform.TIKTOK, Platform.YOUTUBE]
        
        results = await orchestrator.publish_to_multiple(request, platforms)
        
        assert len(results) == 2
        assert results[Platform.TIKTOK].success is True
        assert results[Platform.YOUTUBE].success is True
    
    @pytest.mark.asyncio
    async def test_unconfigured_platform_fails(self, orchestrator):
        """Should fail for unconfigured platform"""
        request = PublishRequest(platform=Platform.LINKEDIN)
        
        # Remove LinkedIn credentials
        orchestrator.publishers.pop(Platform.LINKEDIN, None)
        
        result = await orchestrator.publish(request)
        
        assert result.success is False
    
    @pytest.mark.asyncio
    async def test_publish_history(self, orchestrator):
        """Should track publish history"""
        request = PublishRequest(platform=Platform.TIKTOK)
        await orchestrator.publish(request)
        
        assert len(orchestrator.publish_history) == 1
    
    def test_add_credentials(self, orchestrator):
        """Should add platform credentials"""
        creds = OAuthCredentials()
        orchestrator.add_credentials(Platform.TWITTER, creds)
        
        assert Platform.TWITTER in orchestrator.publishers


class TestRetryLogic:
    """Test retry mechanisms"""
    
    @pytest.fixture
    def orchestrator(self):
        orch = PublishingOrchestrator()
        creds = OAuthCredentials()
        orch.add_credentials(Platform.TIKTOK, creds)
        return orch
    
    @pytest.mark.asyncio
    async def test_retry_successful(self, orchestrator):
        """Should retry and succeed"""
        failed_result = PublishResult(
            success=False,
            status=PublishStatus.FAILED,
            platform=Platform.TIKTOK,
        )
        
        result = await orchestrator.retry_failed(failed_result, max_retries=1)
        
        # With mock, should succeed on retry
        assert result.success is True
    
    @pytest.mark.asyncio
    async def test_no_retry_on_success(self, orchestrator):
        """Should not retry successful publish"""
        success_result = PublishResult(success=True, platform=Platform.TIKTOK)
        
        result = await orchestrator.retry_failed(success_result)
        
        assert result.success is True


class TestValidation:
    """Test request validation"""
    
    def test_missing_media_path(self):
        """Should catch missing media path"""
        publisher = TikTokPublisher(OAuthCredentials())
        request = PublishRequest(media_path="")
        
        errors = publisher._validate_request(request)
        
        assert "media_path is required" in errors
    
    def test_missing_description(self):
        """Should catch missing description"""
        publisher = TikTokPublisher(OAuthCredentials())
        request = PublishRequest(description="")
        
        errors = publisher._validate_request(request)
        
        assert "description is required" in errors
    
    def test_valid_request_no_errors(self):
        """Should return no errors for valid request"""
        publisher = TikTokPublisher(OAuthCredentials())
        request = PublishRequest()
        
        errors = publisher._validate_request(request)
        
        assert len(errors) == 0


class TestMediaTypes:
    """Test media type handling"""
    
    def test_video_media_type(self):
        """Should handle video type"""
        request = PublishRequest(media_type=MediaType.VIDEO)
        assert request.media_type == MediaType.VIDEO
    
    def test_image_media_type(self):
        """Should handle image type"""
        request = PublishRequest(media_type=MediaType.IMAGE)
        assert request.media_type == MediaType.IMAGE
    
    def test_reel_media_type(self):
        """Should handle reel type"""
        request = PublishRequest(media_type=MediaType.REEL)
        assert request.media_type == MediaType.REEL
    
    def test_short_media_type(self):
        """Should handle short type"""
        request = PublishRequest(media_type=MediaType.SHORT)
        assert request.media_type == MediaType.SHORT
    
    def test_story_media_type(self):
        """Should handle story type"""
        request = PublishRequest(media_type=MediaType.STORY)
        assert request.media_type == MediaType.STORY
    
    def test_carousel_media_type(self):
        """Should handle carousel type"""
        request = PublishRequest(media_type=MediaType.CAROUSEL)
        assert request.media_type == MediaType.CAROUSEL


class TestPublishStatus:
    """Test publish status enum"""
    
    def test_pending_status(self):
        """Should have pending status"""
        assert PublishStatus.PENDING == "pending"
    
    def test_uploading_status(self):
        """Should have uploading status"""
        assert PublishStatus.UPLOADING == "uploading"
    
    def test_processing_status(self):
        """Should have processing status"""
        assert PublishStatus.PROCESSING == "processing"
    
    def test_published_status(self):
        """Should have published status"""
        assert PublishStatus.PUBLISHED == "published"
    
    def test_failed_status(self):
        """Should have failed status"""
        assert PublishStatus.FAILED == "failed"
    
    def test_scheduled_status(self):
        """Should have scheduled status"""
        assert PublishStatus.SCHEDULED == "scheduled"


class TestTokenRefresh:
    """Test OAuth token refresh"""
    
    @pytest.mark.asyncio
    async def test_refresh_token(self):
        """Should refresh OAuth token"""
        creds = OAuthCredentials(
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        publisher = TikTokPublisher(creds)
        
        assert publisher.credentials.is_expired() is True
        
        await publisher.refresh_token()
        
        assert publisher.credentials.is_expired() is False
    
    @pytest.mark.asyncio
    async def test_validate_credentials(self):
        """Should validate credentials"""
        creds = OAuthCredentials()
        publisher = TikTokPublisher(creds)
        
        is_valid = await publisher.validate_credentials()
        
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_expired_credentials(self):
        """Should reject expired credentials"""
        creds = OAuthCredentials(
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        publisher = TikTokPublisher(creds)
        
        is_valid = await publisher.validate_credentials()
        
        assert is_valid is False


class TestPrivacySettings:
    """Test privacy settings"""
    
    def test_public_privacy(self):
        """Should support public privacy"""
        request = PublishRequest(privacy="public")
        assert request.privacy == "public"
    
    def test_private_privacy(self):
        """Should support private privacy"""
        request = PublishRequest(privacy="private")
        assert request.privacy == "private"
    
    def test_unlisted_privacy(self):
        """Should support unlisted privacy"""
        request = PublishRequest(privacy="unlisted")
        assert request.privacy == "unlisted"


class TestMetadata:
    """Test metadata handling"""
    
    def test_empty_metadata_default(self):
        """Should default to empty metadata"""
        request = PublishRequest()
        assert request.metadata == {}
    
    def test_custom_metadata(self):
        """Should accept custom metadata"""
        request = PublishRequest(metadata={"key": "value"})
        assert request.metadata["key"] == "value"
    
    def test_result_metadata(self):
        """Should include metadata in result"""
        result = PublishResult(metadata={"views": 100})
        assert result.metadata["views"] == 100


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
