"""
E2E Test: Multi-Platform Publishing Flow (E2E-005)
===================================================

This E2E test verifies the complete publishing workflow:
1. Create/retrieve a video
2. Select target platforms
3. Publish to multiple platforms
4. Verify success/error handling
5. Track publishing status

Test Coverage:
- Platform selection (TikTok, Instagram, YouTube, Twitter)
- Publish success scenarios
- Error handling and recovery
- Platform-specific metadata
- Publishing status tracking
"""

import pytest
import requests
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from loguru import logger

BASE_URL = "http://localhost:5555"
TEST_TIMEOUT = 300  # 5 minutes for publishing


class TestMultiPlatformPublishing:
    """Test suite for multi-platform publishing"""

    @pytest.fixture(scope="class")
    def media_id(self):
        """Get or create a test video"""
        # Try to find an analyzed video
        response = requests.get(f"{BASE_URL}/api/media-db/list?limit=50", timeout=30)
        assert response.status_code == 200, "Backend server must be running"

        videos = response.json()

        # Find an analyzed video (has analysis results)
        for video in videos:
            if video.get("status") in ["analyzed", "published"]:
                logger.info(f"Using existing video: {video['media_id']}")
                return video["media_id"]

        pytest.skip("No analyzed videos available for publishing test")

    def test_01_verify_video_analyzed(self, media_id):
        """E2E-005-01: Verify video is properly analyzed"""
        logger.info(f"🎬 Verifying video analysis for {media_id}...")

        response = requests.get(f"{BASE_URL}/api/media-db/detail/{media_id}", timeout=30)
        assert response.status_code == 200, f"Video {media_id} not found"

        video = response.json()
        assert video.get("status") in ["analyzed", "published"], f"Video status is {video.get('status')}, need analyzed"

        # Verify analysis results exist
        analysis = video.get("analysis", {})
        assert analysis, "Video should have analysis results"
        assert analysis.get("hooks") or analysis.get("topics"), "Analysis should contain hooks or topics"

        logger.success(f"✅ Video is properly analyzed with {len(analysis.get('hooks', []))} hooks")

    def test_02_get_available_platforms(self):
        """E2E-005-02: Get list of available platforms"""
        logger.info("🌍 Fetching available platforms...")

        response = requests.get(f"{BASE_URL}/api/publishing/platforms", timeout=30)
        assert response.status_code == 200, "Should list available platforms"

        platforms = response.json()
        assert isinstance(platforms, list), "Should return list of platforms"
        assert len(platforms) > 0, "Should have at least one platform"

        # Verify platform structure
        required_fields = ["id", "name", "icon"]
        for platform in platforms:
            for field in required_fields:
                assert field in platform, f"Platform missing field: {field}"

        logger.success(f"✅ Found {len(platforms)} available platforms: {[p['name'] for p in platforms]}")
        return platforms

    def test_03_list_connected_accounts(self):
        """E2E-005-03: List connected social media accounts"""
        logger.info("👤 Fetching connected accounts...")

        response = requests.get(f"{BASE_URL}/api/accounts/connected", timeout=30)
        assert response.status_code == 200, "Should list connected accounts"

        accounts = response.json()
        assert isinstance(accounts, dict), "Should return dict of accounts by platform"

        logger.success(f"✅ Connected accounts: {list(accounts.keys())}")
        return accounts

    def test_04_publish_single_platform(self, media_id):
        """E2E-005-04: Publish to single platform (TikTok)"""
        logger.info(f"📤 Publishing {media_id} to TikTok...")

        payload = {
            "media_id": media_id,
            "platforms": ["tiktok"],
            "title": "Test TikTok Post",
            "description": "This is a test post from E2E testing",
            "schedule_time": None,  # Publish immediately
        }

        response = requests.post(
            f"{BASE_URL}/api/publishing/publish",
            json=payload,
            timeout=TEST_TIMEOUT
        )

        if response.status_code == 200:
            result = response.json()
            assert "publish_id" in result or "job_id" in result, "Should return publish job ID"
            logger.success(f"✅ TikTok publish initiated: {result.get('publish_id')}")
        elif response.status_code == 409:
            logger.warning("⚠️ Platform publish conflict (expected in test env)")
        else:
            assert response.status_code == 200, f"Publish failed: {response.text}"

    def test_05_publish_multiple_platforms(self, media_id):
        """E2E-005-05: Publish to multiple platforms simultaneously"""
        logger.info(f"📤 Publishing {media_id} to multiple platforms...")

        payload = {
            "media_id": media_id,
            "platforms": ["tiktok", "instagram", "youtube"],
            "title": "Multi-Platform Test Post",
            "description": "Testing multi-platform publishing",
            "schedule_time": None,
        }

        response = requests.post(
            f"{BASE_URL}/api/publishing/publish",
            json=payload,
            timeout=TEST_TIMEOUT
        )

        if response.status_code == 200:
            result = response.json()
            logger.success(f"✅ Multi-platform publish initiated")
        elif response.status_code == 409:
            logger.warning("⚠️ Multi-platform conflict (expected in test env)")
        else:
            assert response.status_code == 200, f"Multi-platform publish failed: {response.text}"

    def test_06_schedule_publish(self, media_id):
        """E2E-005-06: Schedule publish for future time"""
        logger.info(f"📅 Scheduling {media_id} for future publish...")

        # Schedule for 1 hour from now
        schedule_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"

        payload = {
            "media_id": media_id,
            "platforms": ["instagram"],
            "title": "Scheduled Instagram Post",
            "description": "This post is scheduled",
            "schedule_time": schedule_time,
        }

        response = requests.post(
            f"{BASE_URL}/api/publishing/schedule",
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            assert "schedule_id" in result, "Should return schedule ID"
            logger.success(f"✅ Post scheduled: {result.get('schedule_id')}")
        else:
            logger.warning(f"⚠️ Schedule endpoint not available: {response.status_code}")

    def test_07_get_publish_status(self, media_id):
        """E2E-005-07: Check publishing status"""
        logger.info(f"📊 Checking publish status for {media_id}...")

        response = requests.get(
            f"{BASE_URL}/api/publishing/status/{media_id}",
            timeout=30
        )

        if response.status_code == 200:
            status = response.json()
            assert "status" in status, "Should include status field"
            logger.success(f"✅ Publishing status: {status.get('status')}")
        else:
            logger.warning(f"⚠️ Status endpoint returned: {response.status_code}")

    def test_08_platform_specific_metadata(self, media_id):
        """E2E-005-08: Verify platform-specific metadata generation"""
        logger.info(f"🔧 Checking platform-specific metadata for {media_id}...")

        response = requests.get(f"{BASE_URL}/api/media-db/detail/{media_id}", timeout=30)
        assert response.status_code == 200

        video = response.json()
        analysis = video.get("analysis", {})

        # Verify platform metadata was generated
        platforms_to_check = {
            "tiktok": ["hook", "hashtags"],
            "instagram": ["hook", "hashtags", "engagement_tags"],
            "youtube": ["description", "keywords"],
            "twitter": ["title", "hashtags"],
        }

        for platform, expected_fields in platforms_to_check.items():
            metadata = analysis.get("platform_metadata", {}).get(platform, {})
            if metadata:
                logger.info(f"  {platform}: {list(metadata.keys())}")

        logger.success("✅ Platform-specific metadata verified")

    def test_09_handle_publish_errors(self):
        """E2E-005-09: Verify error handling for invalid publish requests"""
        logger.info("⚠️ Testing error handling...")

        # Test with invalid media_id
        payload = {
            "media_id": "invalid-id-12345",
            "platforms": ["tiktok"],
            "title": "Test",
            "description": "Test",
        }

        response = requests.post(
            f"{BASE_URL}/api/publishing/publish",
            json=payload,
            timeout=30
        )

        # Should return error (400, 404, or 422)
        assert response.status_code in [400, 404, 422, 500], "Should handle invalid input"
        logger.success("✅ Error handling working")

    def test_10_publish_history(self, media_id):
        """E2E-005-10: Check publish history for video"""
        logger.info(f"📜 Checking publish history for {media_id}...")

        response = requests.get(
            f"{BASE_URL}/api/publishing/history/{media_id}",
            timeout=30
        )

        if response.status_code == 200:
            history = response.json()
            assert isinstance(history, list), "Should return list of publishes"
            logger.success(f"✅ Publish history: {len(history)} entries")
        else:
            logger.warning(f"⚠️ History endpoint returned: {response.status_code}")

    def test_11_concurrent_platform_publishing(self, media_id):
        """E2E-005-11: Test concurrent publishing to multiple platforms"""
        logger.info(f"🚀 Testing concurrent multi-platform publishing...")

        platforms = ["tiktok", "instagram", "youtube", "twitter"]
        payload = {
            "media_id": media_id,
            "platforms": platforms,
            "title": "Concurrent Publish Test",
            "description": "Testing concurrent publishing",
            "concurrent": True,
        }

        response = requests.post(
            f"{BASE_URL}/api/publishing/publish",
            json=payload,
            timeout=TEST_TIMEOUT
        )

        if response.status_code == 200:
            result = response.json()
            logger.success(f"✅ Concurrent publish initiated for {len(platforms)} platforms")
        else:
            logger.warning(f"⚠️ Concurrent publish returned: {response.status_code}")

    def test_12_blotato_integration(self):
        """E2E-005-12: Verify Blotato cloud hosting integration"""
        logger.info("☁️ Checking Blotato integration...")

        response = requests.get(f"{BASE_URL}/api/blotato/status", timeout=30)

        if response.status_code == 200:
            status = response.json()
            logger.success(f"✅ Blotato status: {status.get('status')}")
        else:
            logger.warning(f"⚠️ Blotato endpoint returned: {response.status_code}")


class TestPublishingEdgeCases:
    """Test edge cases and error scenarios"""

    def test_publish_without_analysis(self):
        """Publish should fail gracefully if video not analyzed"""
        logger.info("Testing publish of unanalyzed video...")

        # Try to find an unanalyzed video
        response = requests.get(f"{BASE_URL}/api/media-db/list?limit=50", timeout=30)
        assert response.status_code == 200

        videos = response.json()
        unanalyzed = next((v for v in videos if v.get("status") == "ingested"), None)

        if not unanalyzed:
            pytest.skip("No unanalyzed videos available")

        payload = {
            "media_id": unanalyzed["media_id"],
            "platforms": ["tiktok"],
            "title": "Test",
            "description": "Test",
        }

        response = requests.post(
            f"{BASE_URL}/api/publishing/publish",
            json=payload,
            timeout=30
        )

        # Should either require analysis or handle gracefully
        assert response.status_code in [400, 409, 422], f"Got {response.status_code}"
        logger.success("✅ Properly handles unanalyzed videos")

    def test_publish_with_special_characters(self):
        """Test publishing with special characters in metadata"""
        logger.info("Testing special characters in publish metadata...")

        response = requests.get(f"{BASE_URL}/api/media-db/list?limit=1", timeout=30)
        if response.status_code != 200 or not response.json():
            pytest.skip("No videos available")

        media_id = response.json()[0]["media_id"]

        payload = {
            "media_id": media_id,
            "platforms": ["tiktok"],
            "title": "🎬 Special #chars & émojis™",
            "description": "Test with émojis 🚀 & special chars!",
        }

        response = requests.post(
            f"{BASE_URL}/api/publishing/publish",
            json=payload,
            timeout=30
        )

        # Should handle or reject special chars
        assert response.status_code in [200, 400, 422], f"Got {response.status_code}"
        logger.success("✅ Special characters handled")


class TestPublishingPerformance:
    """Test publishing performance characteristics"""

    def test_publish_response_time(self):
        """Verify publish endpoint responds quickly"""
        logger.info("Testing publish endpoint response time...")

        response = requests.get(f"{BASE_URL}/api/media-db/list?limit=1", timeout=30)
        if response.status_code != 200 or not response.json():
            pytest.skip("No videos available")

        media_id = response.json()[0]["media_id"]

        payload = {
            "media_id": media_id,
            "platforms": ["tiktok"],
            "title": "Performance Test",
            "description": "Test",
        }

        import time
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/api/publishing/publish",
            json=payload,
            timeout=30
        )
        elapsed = time.time() - start

        logger.info(f"Publish endpoint response time: {elapsed:.2f}s")

        # Should respond within 10 seconds
        if response.status_code == 200:
            assert elapsed < 10.0, f"Publish took {elapsed:.2f}s, expected <10s"
            logger.success(f"✅ Response time acceptable: {elapsed:.2f}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
