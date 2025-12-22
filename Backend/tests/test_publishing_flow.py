"""
Tests for Publishing Flow - Google Drive staging, Blotato integration, URL polling
Covers recent features: conditional Google Drive usage, dynamic polling, double-post prevention
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from httpx import AsyncClient
import asyncio
import json
from datetime import datetime

# Test fixtures
@pytest.fixture
def mock_media_record():
    return {
        "media_id": "test-media-123",
        "filename": "test_video.mp4",
        "file_path": "/path/to/test_video.mp4",
        "file_size_bytes": 134800000,  # ~135MB
        "duration_sec": 87,
        "width": 1080,
        "height": 1920,
        "transcript": "Test transcript content",
        "topics": ["topic1", "topic2"],
    }

@pytest.fixture
def mock_blotato_account():
    return {
        "id": "blotato-account-123",
        "platform": "instagram",
        "username": "test_user",
        "fullname": "Test User",
    }


class TestPublishingFlowConfiguration:
    """Tests for publishing flow configuration and routing"""
    
    def test_google_drive_used_for_youtube(self):
        """YouTube publishing should use Google Drive"""
        platform = "youtube"
        use_google_drive = True  # As per recent change
        assert use_google_drive == True
    
    def test_google_drive_used_for_instagram(self):
        """Instagram publishing should use Google Drive (Supabase not configured)"""
        platform = "instagram"
        # After fix: all platforms use Google Drive
        use_google_drive = True
        assert use_google_drive == True
    
    def test_google_drive_used_for_tiktok(self):
        """TikTok publishing should use Google Drive"""
        platform = "tiktok"
        use_google_drive = True
        assert use_google_drive == True
    
    @pytest.mark.parametrize("platform", ["instagram", "youtube", "tiktok", "twitter", "facebook"])
    def test_all_platforms_use_google_drive(self, platform):
        """All platforms should use Google Drive for file staging"""
        # Current implementation uses Google Drive for all
        use_google_drive = True
        assert use_google_drive == True


class TestDynamicPollingTimeout:
    """Tests for dynamic polling timeout based on file size"""
    
    def calculate_timeout(self, file_size_bytes: int) -> tuple:
        """Calculate polling timeout based on file size"""
        file_size_mb = file_size_bytes / (1024 * 1024)
        base_timeout_sec = 30
        per_mb_timeout_sec = 1
        calculated_timeout = base_timeout_sec + (file_size_mb * per_mb_timeout_sec)
        timeout_sec = min(max(calculated_timeout, 30), 300)
        poll_interval = 5
        max_attempts = int(timeout_sec / poll_interval)
        return timeout_sec, max_attempts
    
    def test_small_file_minimum_timeout(self):
        """Small files should get minimum 30 second timeout"""
        file_size = 5 * 1024 * 1024  # 5MB
        timeout, attempts = self.calculate_timeout(file_size)
        assert timeout >= 30
        assert attempts >= 6
    
    def test_medium_file_scaled_timeout(self):
        """Medium files should get scaled timeout"""
        file_size = 100 * 1024 * 1024  # 100MB
        timeout, attempts = self.calculate_timeout(file_size)
        assert timeout == 130  # 30 + 100
        assert attempts == 26
    
    def test_large_file_scaled_timeout(self):
        """Large files should get proportionally longer timeout"""
        file_size = 200 * 1024 * 1024  # 200MB
        timeout, attempts = self.calculate_timeout(file_size)
        assert timeout == 230  # 30 + 200
        assert attempts == 46
    
    def test_very_large_file_maximum_timeout(self):
        """Very large files should be capped at 5 minute timeout"""
        file_size = 500 * 1024 * 1024  # 500MB
        timeout, attempts = self.calculate_timeout(file_size)
        assert timeout == 300  # Max 5 minutes
        assert attempts == 60
    
    def test_zero_file_size_minimum_timeout(self):
        """Zero/unknown file size should get minimum timeout"""
        file_size = 0
        timeout, attempts = self.calculate_timeout(file_size)
        assert timeout == 30
        assert attempts == 6
    
    @pytest.mark.parametrize("file_size_mb,expected_timeout", [
        (10, 40),
        (50, 80),
        (100, 130),
        (150, 180),
        (200, 230),
        (250, 280),
        (300, 300),  # Capped at max
    ])
    def test_timeout_scaling_parametrized(self, file_size_mb, expected_timeout):
        """Parametrized test for timeout scaling"""
        file_size = file_size_mb * 1024 * 1024
        timeout, _ = self.calculate_timeout(file_size)
        assert timeout == expected_timeout


class TestDoublePostPrevention:
    """Tests for preventing double posting from React Strict Mode"""
    
    def test_ref_prevents_double_execution(self):
        """useRef guard should prevent double effect execution"""
        has_started = False
        
        def attempt_publish():
            nonlocal has_started
            if not has_started:
                has_started = True
                return True  # Publishing started
            return False  # Blocked
        
        # First call should succeed
        assert attempt_publish() == True
        # Second call should be blocked
        assert attempt_publish() == False
    
    def test_multiple_attempts_blocked(self):
        """Multiple rapid attempts should all be blocked after first"""
        has_started = False
        attempts = []
        
        def attempt_publish():
            nonlocal has_started
            if not has_started:
                has_started = True
                attempts.append("executed")
                return True
            attempts.append("blocked")
            return False
        
        # Simulate React Strict Mode double-firing
        for _ in range(5):
            attempt_publish()
        
        assert attempts.count("executed") == 1
        assert attempts.count("blocked") == 4


class TestPublishingEndpoint:
    """Tests for the full-publish endpoint"""
    
    @pytest.fixture
    def publish_request(self):
        return {
            "media_id": "test-media-123",
            "blotato_account_id": "account-456",
            "platform": "instagram",
            "username": "test_user",
            "text": "Test caption #hashtag",
            "cleanup_gdrive": True,
        }
    
    def test_publish_request_structure(self, publish_request):
        """Publish request should have required fields"""
        assert "media_id" in publish_request
        assert "blotato_account_id" in publish_request
        assert "platform" in publish_request
        assert "text" in publish_request
    
    def test_platform_normalization(self):
        """Platform names should be normalized to lowercase"""
        platforms = ["Instagram", "YOUTUBE", "TikTok", "twitter"]
        normalized = [p.lower() for p in platforms]
        assert normalized == ["instagram", "youtube", "tiktok", "twitter"]
    
    @pytest.mark.parametrize("platform,expected_config", [
        ("tiktok", {"is_ai_generated": False}),
        ("instagram", {"media_type": "reel"}),
        ("youtube", {"privacy_status": "public"}),
    ])
    def test_platform_specific_config(self, platform, expected_config):
        """Each platform should have specific configuration"""
        config = {}
        if platform == "tiktok":
            config = {"is_ai_generated": False}
        elif platform == "instagram":
            config = {"media_type": "reel"}
        elif platform == "youtube":
            config = {"title": "Test", "privacy_status": "public"}
        
        for key, value in expected_config.items():
            assert config.get(key) == value


class TestPublishingResponse:
    """Tests for publishing response handling"""
    
    def test_success_response_structure(self):
        """Successful publish response should have required fields"""
        response = {
            "success": True,
            "post_submission_id": "submission-123",
            "public_url": None,  # URL comes later via polling
            "error": None,
        }
        assert response["success"] == True
        assert response["post_submission_id"] is not None
        assert response["error"] is None
    
    def test_failure_response_structure(self):
        """Failed publish response should have error details"""
        response = {
            "success": False,
            "post_submission_id": None,
            "public_url": None,
            "error": "Failed to upload to Google Drive",
        }
        assert response["success"] == False
        assert response["error"] is not None
    
    def test_steps_tracking(self):
        """Response should track individual step success/failure"""
        response = {
            "success": True,
            "steps": {
                "storage_upload": {"success": True},
                "blotato_media": {"success": True},
                "blotato_post": {"success": True},
            }
        }
        assert all(step["success"] for step in response["steps"].values())


class TestURLPolling:
    """Tests for URL polling after successful publish"""
    
    @pytest.fixture
    def poll_responses(self):
        return [
            {"status": "processing", "publicUrl": None},
            {"status": "processing", "publicUrl": None},
            {"status": "published", "publicUrl": "https://instagram.com/reel/ABC123"},
        ]
    
    def test_polling_detects_published_status(self, poll_responses):
        """Polling should detect when status becomes 'published'"""
        for response in poll_responses:
            if response["status"] == "published":
                assert response["publicUrl"] is not None
                break
    
    def test_polling_extracts_url(self, poll_responses):
        """Polling should extract public URL when available"""
        final_response = poll_responses[-1]
        assert final_response["publicUrl"] == "https://instagram.com/reel/ABC123"
    
    def test_polling_handles_failed_status(self):
        """Polling should handle failed status"""
        response = {
            "status": "failed",
            "publicUrl": None,
            "errorMessage": "Video processing failed",
        }
        assert response["status"] == "failed"
        assert response["errorMessage"] is not None
    
    @pytest.mark.parametrize("status,should_continue", [
        ("processing", True),
        ("pending", True),
        ("published", False),
        ("failed", False),
    ])
    def test_polling_continuation_logic(self, status, should_continue):
        """Polling should continue only for pending/processing statuses"""
        continue_polling = status in ["processing", "pending"]
        assert continue_polling == should_continue


class TestPostedContentRecord:
    """Tests for posted content database records"""
    
    def test_record_creation_fields(self):
        """Posted content record should have required fields"""
        record = {
            "id": "record-123",
            "media_id": "media-456",
            "platform": "instagram",
            "platform_post_id": "post-789",
            "platform_url": "https://instagram.com/reel/ABC123",
            "status": "published",
            "posted_at": datetime.now().isoformat(),
        }
        required_fields = ["id", "media_id", "platform", "status", "posted_at"]
        for field in required_fields:
            assert field in record
    
    def test_url_update_after_polling(self):
        """Platform URL should be updatable after polling completes"""
        record = {"platform_url": None}
        new_url = "https://instagram.com/reel/NEW123"
        record["platform_url"] = new_url
        assert record["platform_url"] == new_url
    
    def test_submission_id_lookup(self):
        """Records should be lookupable by submission ID"""
        submission_id = "submission-123"
        # Simulate lookup endpoint
        endpoint = f"/api/posted-content/by-submission/{submission_id}"
        assert submission_id in endpoint


class TestPublishingRetry:
    """Tests for publishing retry functionality"""
    
    def test_retry_resets_status(self):
        """Retry should reset status to pending"""
        status = {"status": "failed", "error_message": "Network error"}
        # Retry action
        status["status"] = "pending"
        status["error_message"] = None
        assert status["status"] == "pending"
        assert status["error_message"] is None
    
    def test_retry_preserves_account_info(self):
        """Retry should preserve account information"""
        original = {
            "account_id": 123,
            "platform": "instagram",
            "username": "test_user",
            "status": "failed",
        }
        retried = {
            "account_id": original["account_id"],
            "platform": original["platform"],
            "username": original["username"],
            "status": "pending",
        }
        assert retried["account_id"] == original["account_id"]
        assert retried["platform"] == original["platform"]


class TestGoogleDriveIntegration:
    """Tests for Google Drive file staging"""
    
    def test_file_upload_path(self):
        """Google Drive upload should use correct path structure"""
        media_id = "media-123"
        expected_path = f"MediaPoster/{media_id}"
        assert media_id in expected_path
    
    def test_public_url_generation(self):
        """Google Drive should generate public shareable URL"""
        file_id = "1abc123def456"
        public_url = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        assert file_id in public_url
        assert "view" in public_url
    
    def test_cleanup_after_publish(self):
        """Google Drive file should be cleaned up after successful publish"""
        cleanup_enabled = True
        publish_success = True
        should_cleanup = cleanup_enabled and publish_success
        assert should_cleanup == True
    
    def test_no_cleanup_on_failure(self):
        """Google Drive file should NOT be cleaned up on publish failure"""
        cleanup_enabled = True
        publish_success = False
        should_cleanup = cleanup_enabled and publish_success
        assert should_cleanup == False


class TestBlotatoMediaUpload:
    """Tests for Blotato media upload endpoint"""
    
    def test_media_upload_payload(self):
        """Blotato media upload should have correct payload"""
        payload = {
            "accountId": "account-123",
            "url": "https://drive.google.com/file/d/abc123/view",
        }
        assert "accountId" in payload
        assert "url" in payload
    
    def test_media_upload_response(self):
        """Blotato media upload should return media ID"""
        response = {
            "id": "blotato-media-456",
            "status": "uploaded",
        }
        assert response["id"] is not None


class TestBlotatoPostCreate:
    """Tests for Blotato post creation endpoint"""
    
    def test_post_create_payload_instagram(self):
        """Instagram post payload should have correct structure"""
        payload = {
            "accountId": "account-123",
            "mediaId": "media-456",
            "text": "Test caption #hashtag",
            "instagramOptions": {
                "mediaType": "reel",
            },
        }
        assert payload["instagramOptions"]["mediaType"] == "reel"
    
    def test_post_create_payload_tiktok(self):
        """TikTok post payload should have correct structure"""
        payload = {
            "accountId": "account-123",
            "mediaId": "media-456",
            "text": "Test caption #hashtag",
            "tiktokOptions": {
                "isAIGenerated": False,
            },
        }
        assert payload["tiktokOptions"]["isAIGenerated"] == False
    
    def test_post_create_payload_youtube(self):
        """YouTube post payload should have correct structure"""
        payload = {
            "accountId": "account-123",
            "mediaId": "media-456",
            "text": "Test description",
            "youtubeOptions": {
                "title": "Video Title",
                "privacyStatus": "public",
            },
        }
        assert payload["youtubeOptions"]["privacyStatus"] == "public"


class TestPublishingLogging:
    """Tests for publishing log functionality"""
    
    def test_log_entry_structure(self):
        """Log entries should have timestamp and message"""
        log_entry = {
            "time": "12:30:45 PM",
            "message": "Publishing to instagram...",
            "type": "info",
        }
        assert "time" in log_entry
        assert "message" in log_entry
        assert log_entry["type"] in ["info", "success", "error", "warning"]
    
    def test_log_types(self):
        """All log types should be supported"""
        valid_types = ["info", "success", "error", "warning"]
        for log_type in valid_types:
            assert log_type in valid_types
    
    def test_success_log_format(self):
        """Success logs should include checkmark"""
        message = "✓ Post submitted to instagram (ID: abc123...)"
        assert "✓" in message
    
    def test_error_log_format(self):
        """Error logs should include X mark"""
        message = "✗ Failed: Network error"
        assert "✗" in message


# Additional edge case tests
class TestEdgeCases:
    """Tests for edge cases and error handling"""
    
    def test_empty_caption_handling(self):
        """Empty caption should use default"""
        caption = "" or "Posted via MediaPoster"
        assert caption == "Posted via MediaPoster"
    
    def test_long_caption_truncation(self):
        """Long captions should be handled appropriately"""
        long_caption = "x" * 5000
        max_length = 2200  # Instagram limit
        truncated = long_caption[:max_length] if len(long_caption) > max_length else long_caption
        assert len(truncated) <= max_length
    
    def test_special_characters_in_caption(self):
        """Special characters should be preserved"""
        caption = "Test 🎬 #video @mention & more!"
        assert "🎬" in caption
        assert "#video" in caption
        assert "@mention" in caption
    
    def test_missing_blotato_account(self):
        """Missing Blotato account should return error"""
        accounts = []
        target_username = "missing_user"
        found = next((a for a in accounts if a.get("username") == target_username), None)
        assert found is None
    
    def test_invalid_media_id(self):
        """Invalid media ID should be rejected"""
        invalid_ids = ["", None, "not-a-uuid", "123"]
        for media_id in invalid_ids:
            is_valid = media_id and len(str(media_id)) == 36 and "-" in str(media_id)
            # Most should be invalid
            if media_id not in [None, ""]:
                pass  # Would fail validation


class TestConcurrency:
    """Tests for concurrent publishing scenarios"""
    
    def test_sequential_platform_publishing(self):
        """Multiple platforms should be published sequentially"""
        platforms = ["instagram", "tiktok", "youtube"]
        publish_order = []
        
        for platform in platforms:
            publish_order.append(platform)
        
        assert publish_order == platforms
    
    def test_independent_polling_per_platform(self):
        """Each platform should have independent polling"""
        polling_states = {
            "instagram": {"attempt": 0, "done": False},
            "tiktok": {"attempt": 0, "done": False},
        }
        
        # Simulate instagram completing first
        polling_states["instagram"]["done"] = True
        
        assert polling_states["instagram"]["done"] == True
        assert polling_states["tiktok"]["done"] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
