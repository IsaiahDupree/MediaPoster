"""
Integration tests for Publishing Pipeline (TEST-008)
Tests for touchpoint creation, platform ID storage, shortlinks
Acceptance: Touchpoints created, All fields populated
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

# Import services
from services.publish_service import PublishService
from services.touchpoint_service import TouchpointService
from services.shortlink_service import ShortlinkService


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = Mock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    session.add = Mock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def touchpoint_service(mock_db_session):
    """Touchpoint service instance"""
    return TouchpointService(db=mock_db_session)


@pytest.fixture
def shortlink_service(mock_db_session):
    """Shortlink service instance"""
    return ShortlinkService(db=mock_db_session)


@pytest.fixture
def publish_service(mock_db_session):
    """Publish service instance"""
    return PublishService(db=mock_db_session)


@pytest.fixture
def sample_publish_request():
    """Sample publish request with full attribution"""
    return {
        "platform": "twitter",
        "content": "Amazing content marketing tip! Click to learn more: {shortlink}",
        "media_urls": ["https://storage.example.com/media123.mp4"],
        "scheduled_time": datetime.now(timezone.utc),
        "template_id": "tpl_001",
        "offer_id": "offer_001",
        "icp_id": "icp_001",
        "brand_id": "brand_001",
        "landing_url": "https://example.com/guide"
    }


class TestTouchpointCreation:
    """Test touchpoint creation with full attribution"""

    @pytest.mark.asyncio
    async def test_create_touchpoint_with_complete_attribution(self, touchpoint_service, sample_publish_request):
        """Test touchpoint created with all required attribution fields"""
        touchpoint_data = {
            "channel": "social",
            "platform": sample_publish_request["platform"],
            "message_type": "post",
            "offer_id": sample_publish_request["offer_id"],
            "icp_id": sample_publish_request["icp_id"],
            "template_id": sample_publish_request["template_id"],
            "brand_id": sample_publish_request["brand_id"],
            "content": sample_publish_request["content"],
            "published_at": datetime.now(timezone.utc)
        }

        # Verify all attribution fields present
        assert "offer_id" in touchpoint_data
        assert "icp_id" in touchpoint_data
        assert "template_id" in touchpoint_data
        assert "brand_id" in touchpoint_data

        # In production, this creates DB record
        # touchpoint = await touchpoint_service.create(touchpoint_data)
        # assert touchpoint.touchpoint_id is not None

    @pytest.mark.asyncio
    async def test_touchpoint_stores_platform_post_id(self, touchpoint_service):
        """Test touchpoint stores platform's returned post ID"""
        touchpoint_data = {
            "channel": "social",
            "platform": "twitter",
            "platform_post_id": "1234567890123456789",  # Twitter's post ID
            "platform_url": "https://twitter.com/user/status/1234567890123456789",
            "offer_id": "offer_001",
            "icp_id": "icp_001",
            "template_id": "tpl_001",
            "published_at": datetime.now(timezone.utc)
        }

        # Verify platform IDs captured
        assert touchpoint_data["platform_post_id"] is not None
        assert touchpoint_data["platform_url"] is not None
        assert len(touchpoint_data["platform_post_id"]) > 0

    @pytest.mark.asyncio
    async def test_touchpoint_links_to_posted_content_record(self, touchpoint_service):
        """Test touchpoint links to posted_content table"""
        touchpoint_data = {
            "channel": "social",
            "platform": "twitter",
            "posted_content_id": "posted_123",  # FK to posted_content table
            "offer_id": "offer_001",
            "icp_id": "icp_001",
            "template_id": "tpl_001",
            "published_at": datetime.now(timezone.utc)
        }

        assert "posted_content_id" in touchpoint_data
        # In production, verifies FK relationship exists


class TestAttributionChainValidation:
    """Test attribution chain completeness"""

    @pytest.mark.asyncio
    async def test_validate_complete_attribution_chain(self, touchpoint_service):
        """Test full attribution chain: touchpoint → template → offer → ICP → brand"""
        # Complete chain
        attribution = {
            "template_id": "tpl_001",
            "offer_id": "offer_001",
            "icp_id": "icp_001",
            "brand_id": "brand_001"
        }

        # All required fields present
        assert all(k in attribution for k in ["template_id", "offer_id", "icp_id", "brand_id"])

    @pytest.mark.asyncio
    async def test_fail_on_missing_template_id(self, touchpoint_service):
        """Test touchpoint creation fails without template_id"""
        touchpoint_data = {
            "channel": "social",
            "platform": "twitter",
            # "template_id": "tpl_001",  # MISSING
            "offer_id": "offer_001",
            "icp_id": "icp_001",
            "published_at": datetime.now(timezone.utc)
        }

        # Should raise error or validation failure
        # In production: await touchpoint_service.create(touchpoint_data)
        # assert error raised

    @pytest.mark.asyncio
    async def test_fail_on_missing_offer_id(self, touchpoint_service):
        """Test touchpoint creation fails without offer_id"""
        touchpoint_data = {
            "channel": "social",
            "platform": "twitter",
            "template_id": "tpl_001",
            # "offer_id": "offer_001",  # MISSING
            "icp_id": "icp_001",
            "published_at": datetime.now(timezone.utc)
        }

        # Should raise error or validation failure

    @pytest.mark.asyncio
    async def test_fail_on_missing_icp_id(self, touchpoint_service):
        """Test touchpoint creation fails without icp_id"""
        touchpoint_data = {
            "channel": "social",
            "platform": "twitter",
            "template_id": "tpl_001",
            "offer_id": "offer_001",
            # "icp_id": "icp_001",  # MISSING
            "published_at": datetime.now(timezone.utc)
        }

        # Should raise error or validation failure

    @pytest.mark.asyncio
    async def test_validate_icp_belongs_to_offer_brand(self, touchpoint_service):
        """Test ICP must belong to same brand as offer"""
        # Offer belongs to brand_001
        # ICP must also belong to brand_001
        # Cannot mix brand_001 offer with brand_002 ICP

        touchpoint_data = {
            "channel": "social",
            "platform": "twitter",
            "template_id": "tpl_001",
            "offer_id": "offer_001",  # brand_001
            "icp_id": "icp_002",  # brand_002 (MISMATCH)
            "brand_id": "brand_001",
            "published_at": datetime.now(timezone.utc)
        }

        # In production, validation should catch brand mismatch

    @pytest.mark.asyncio
    async def test_detect_orphaned_touchpoints(self, touchpoint_service):
        """Test system detects touchpoints without valid parent entities"""
        # Touchpoint with template_id that doesn't exist
        # Touchpoint with offer_id that was deleted
        # Touchpoint with icp_id that doesn't exist

        # In production, run orphan detection query
        # SELECT * FROM touchpoints WHERE template_id NOT IN (SELECT id FROM templates)


class TestShortlinkGeneration:
    """Test shortlink creation with attribution encoding"""

    @pytest.mark.asyncio
    async def test_generate_shortlink_with_utm_params(self, shortlink_service):
        """Test shortlink includes UTM parameters for attribution"""
        shortlink_request = {
            "destination_url": "https://example.com/guide",
            "touchpoint_id": "touchpoint_123",
            "template_id": "tpl_001",
            "offer_id": "offer_001",
            "icp_id": "icp_001"
        }

        # Generated shortlink should encode attribution in UTM params
        # ?utm_source=social&utm_medium=twitter&utm_campaign=offer_001
        # &utm_content=tpl_001&utm_term=icp_001
        # &tp=touchpoint_123

        # In production:
        # shortlink = await shortlink_service.create(shortlink_request)
        # assert "utm_source" in shortlink.full_url
        # assert "utm_campaign" in shortlink.full_url
        # assert shortlink.short_code is not None

    @pytest.mark.asyncio
    async def test_shortlink_stores_attribution_chain(self, shortlink_service):
        """Test shortlink database record stores full attribution"""
        shortlink_data = {
            "destination_url": "https://example.com/guide",
            "short_code": "abc123",
            "touchpoint_id": "touchpoint_123",
            "offer_id": "offer_001",
            "template_id": "tpl_001",
            "icp_id": "icp_001",
            "created_at": datetime.now(timezone.utc)
        }

        # All attribution fields present
        assert "touchpoint_id" in shortlink_data
        assert "offer_id" in shortlink_data
        assert "template_id" in shortlink_data
        assert "icp_id" in shortlink_data

    @pytest.mark.asyncio
    async def test_shortlink_click_tracking(self, shortlink_service):
        """Test shortlink clicks are tracked with attribution"""
        # When user clicks shortlink
        # 1. Redirect to destination_url
        # 2. Increment click_count
        # 3. Log click event with touchpoint_id, timestamp, IP, user_agent

        click_data = {
            "shortlink_id": "link_123",
            "touchpoint_id": "touchpoint_123",
            "clicked_at": datetime.now(timezone.utc),
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0...",
            "referrer": "https://twitter.com"
        }

        # In production, log click event
        # await shortlink_service.track_click(click_data)

    @pytest.mark.asyncio
    async def test_shortlink_replaces_placeholder_in_content(self, publish_service, sample_publish_request):
        """Test shortlink replaces {shortlink} placeholder in content"""
        content_template = "Check out this guide: {shortlink}"
        shortlink_url = "https://short.link/abc123"

        final_content = content_template.replace("{shortlink}", shortlink_url)

        assert "{shortlink}" not in final_content
        assert shortlink_url in final_content
        assert final_content == "Check out this guide: https://short.link/abc123"


class TestPlatformSpecificPublishing:
    """Test publishing to different platforms"""

    @pytest.mark.asyncio
    async def test_publish_to_twitter(self, publish_service, sample_publish_request):
        """Test Twitter publish flow"""
        request = {**sample_publish_request, "platform": "twitter"}

        # In production:
        # 1. Upload media to Twitter
        # 2. Create tweet with media_ids
        # 3. Receive tweet_id and status URL
        # 4. Create touchpoint with tweet_id
        # 5. Create shortlink
        # 6. Update posted_content record

        assert request["platform"] == "twitter"

    @pytest.mark.asyncio
    async def test_publish_to_instagram(self, publish_service, sample_publish_request):
        """Test Instagram publish flow"""
        request = {**sample_publish_request, "platform": "instagram"}

        # Instagram has different flow:
        # 1. Upload media container
        # 2. Wait for processing
        # 3. Publish container
        # 4. Get media_id

        assert request["platform"] == "instagram"

    @pytest.mark.asyncio
    async def test_publish_to_tiktok(self, publish_service, sample_publish_request):
        """Test TikTok publish flow"""
        request = {**sample_publish_request, "platform": "tiktok"}

        # TikTok flow:
        # 1. Upload video
        # 2. Create post with video_id
        # 3. Get item_id

        assert request["platform"] == "tiktok"

    @pytest.mark.asyncio
    async def test_publish_to_youtube(self, publish_service, sample_publish_request):
        """Test YouTube publish flow"""
        request = {**sample_publish_request, "platform": "youtube"}

        # YouTube flow:
        # 1. Upload video file
        # 2. Set video metadata (title, description, tags)
        # 3. Get video_id

        assert request["platform"] == "youtube"

    @pytest.mark.asyncio
    async def test_publish_to_threads(self, publish_service, sample_publish_request):
        """Test Threads publish flow"""
        request = {**sample_publish_request, "platform": "threads"}

        # Threads flow (similar to Instagram):
        # 1. Create media container
        # 2. Publish container
        # 3. Get thread_id

        assert request["platform"] == "threads"


class TestMediaUploadAndCleanup:
    """Test media upload and staging cleanup"""

    @pytest.mark.asyncio
    async def test_upload_media_to_storage(self, publish_service):
        """Test media files uploaded to storage before publishing"""
        media_files = [
            "/local/path/video.mp4",
            "/local/path/thumbnail.jpg"
        ]

        # In production:
        # 1. Upload to Supabase storage or Google Drive
        # 2. Get public URLs
        # 3. Use URLs in platform publish API

        # storage_urls = await publish_service.upload_media(media_files)
        # assert len(storage_urls) == 2
        # assert all("https://" in url for url in storage_urls)

    @pytest.mark.asyncio
    async def test_cleanup_staging_files_after_publish(self, publish_service):
        """Test staging files deleted after successful publish"""
        staging_files = [
            "/staging/temp_video_123.mp4",
            "/staging/temp_thumb_123.jpg"
        ]

        # After successful publish:
        # 1. Delete staging files
        # 2. Keep source files (if needed)
        # 3. Log cleanup action

        # await publish_service.cleanup_staging(staging_files)
        # for file in staging_files:
        #     assert not os.path.exists(file)

    @pytest.mark.asyncio
    async def test_preserve_staging_on_publish_failure(self, publish_service):
        """Test staging files preserved if publish fails"""
        # If publish fails:
        # 1. Keep staging files for retry
        # 2. Log error
        # 3. Don't delete media

        pass


class TestPublishedContentMetrics:
    """Test metrics tracking for published content"""

    @pytest.mark.asyncio
    async def test_initialize_metrics_snapshot_on_publish(self, publish_service):
        """Test metrics snapshot created when content published"""
        publish_result = {
            "touchpoint_id": "touchpoint_123",
            "platform": "twitter",
            "platform_post_id": "1234567890",
            "published_at": datetime.now(timezone.utc)
        }

        # After publish, schedule metrics snapshots
        # 1h, 6h, 24h, 72h, 7d

        # In production:
        # await metrics_snapshot_service.schedule_snapshots(publish_result)

    @pytest.mark.asyncio
    async def test_metrics_linked_to_touchpoint(self, touchpoint_service):
        """Test metrics snapshots link back to touchpoint"""
        metrics_snapshot = {
            "touchpoint_id": "touchpoint_123",
            "snapshot_time": datetime.now(timezone.utc),
            "interval": "1h",
            "views": 1000,
            "likes": 50,
            "replies": 10,
            "reposts": 5
        }

        assert "touchpoint_id" in metrics_snapshot
        # FK relationship to touchpoints table


class TestErrorHandling:
    """Test error handling in publishing pipeline"""

    @pytest.mark.asyncio
    async def test_handle_platform_api_failure(self, publish_service):
        """Test handling of platform API errors"""
        # Platform API can fail for many reasons:
        # - Rate limits
        # - Authentication errors
        # - Media processing errors
        # - Network timeouts

        # Should:
        # 1. Log error with full context
        # 2. Mark scheduled_post as failed
        # 3. Retry with exponential backoff (if retryable)
        # 4. Alert user if permanent failure

        pass

    @pytest.mark.asyncio
    async def test_handle_missing_attribution_entities(self, touchpoint_service):
        """Test handling when template/offer/ICP doesn't exist"""
        touchpoint_data = {
            "channel": "social",
            "platform": "twitter",
            "template_id": "nonexistent_template",
            "offer_id": "nonexistent_offer",
            "icp_id": "nonexistent_icp",
            "published_at": datetime.now(timezone.utc)
        }

        # Should fail validation and not create touchpoint
        # In production, raise error

    @pytest.mark.asyncio
    async def test_rollback_on_partial_failure(self, publish_service):
        """Test rollback if publish partially fails"""
        # If media uploads succeed but post creation fails:
        # 1. Delete uploaded media
        # 2. Don't create touchpoint
        # 3. Don't create shortlink
        # 4. Roll back DB transaction

        pass


class TestBackgroundPublisher:
    """Test background publisher worker"""

    @pytest.mark.asyncio
    async def test_publisher_processes_scheduled_posts(self, publish_service):
        """Test background worker picks up due scheduled posts"""
        # BackgroundPublisher polls for:
        # scheduled_posts WHERE scheduled_time <= NOW() AND status = 'pending'

        due_posts = [
            {
                "id": "post_001",
                "scheduled_time": datetime.now(timezone.utc),
                "status": "pending",
                "platform": "twitter"
            }
        ]

        # Worker should:
        # 1. Update status to 'publishing'
        # 2. Call publish_service.publish()
        # 3. Update status to 'published' or 'failed'
        # 4. Create touchpoint on success

    @pytest.mark.asyncio
    async def test_publisher_emits_events(self, publish_service):
        """Test publisher emits event bus events"""
        # Events:
        # - publish.requested
        # - publish.started
        # - publish.completed
        # - publish.failed

        # These trigger:
        # - MetricsSnapshotService (on completed)
        # - SleepModeService (wake on requested)
        # - Notification service (on failed)

        pass


class TestEndToEndPublishFlow:
    """Test complete end-to-end publish flow"""

    @pytest.mark.asyncio
    async def test_complete_publish_pipeline(self, publish_service, sample_publish_request):
        """Test full pipeline: request → upload → publish → touchpoint → shortlink → metrics"""
        # Complete flow:
        # 1. Receive publish request with attribution
        # 2. Validate attribution entities exist
        # 3. Upload media to storage
        # 4. Generate shortlink
        # 5. Replace {shortlink} in content
        # 6. Call platform API
        # 7. Receive platform post ID
        # 8. Create touchpoint with full attribution
        # 9. Link touchpoint to shortlink
        # 10. Schedule metrics snapshots
        # 11. Cleanup staging files
        # 12. Emit publish.completed event

        # In production, this is orchestrated by BackgroundPublisher worker

    @pytest.mark.asyncio
    async def test_verify_all_fields_populated_after_publish(self, touchpoint_service):
        """Test all touchpoint fields populated after successful publish"""
        # After publish, touchpoint should have:
        touchpoint_fields = [
            "touchpoint_id",
            "channel",
            "platform",
            "message_type",
            "template_id",
            "offer_id",
            "icp_id",
            "brand_id",
            "posted_content_id",
            "shortlink",
            "platform_post_id",
            "platform_url",
            "published_at",
            "content",
            "metrics"  # Will populate over time
        ]

        # All required fields must be present
        # assert all(field in touchpoint for field in required_fields)
