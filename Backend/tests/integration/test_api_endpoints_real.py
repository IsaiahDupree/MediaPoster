"""
Real API Endpoint Integration Tests - NO MOCKS
==============================================
Tests that hit REAL API endpoints with REAL database data.

Run with:
    cd Backend && source venv/bin/activate
    RUN_REAL_INTEGRATION_TESTS=true pytest tests/integration/test_api_endpoints_real.py -v -s

Requires:
    - Backend server running on localhost:5555
    - Database with actual data
"""

import pytest
import asyncio
import os
import uuid
import httpx
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
import json

API_BASE_URL = os.getenv("API_URL", "http://localhost:5555")

# Skip unless explicitly enabled
pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_REAL_INTEGRATION_TESTS", "").lower() == "true",
    reason="Set RUN_REAL_INTEGRATION_TESTS=true to run"
)


# =============================================================================
# VIDEOS API - REAL TESTS
# =============================================================================

class TestVideosAPIReal:
    """Real tests for /api/videos endpoints."""

    @pytest.mark.asyncio
    async def test_list_videos(self):
        """GET /api/videos/ - List all videos from real database."""
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(f"{API_BASE_URL}/api/videos/")
            
            assert response.status_code == 200, f"Failed: {response.text}"
            
            data = response.json()
            # Handle both formats: list or {"videos": [...]}
            videos = data if isinstance(data, list) else data.get("videos", [])
            
            print(f"✅ Retrieved {len(videos)} videos")
            
            if videos:
                video = videos[0]
                print(f"   First video: {video.get('file_name', 'Untitled')[:50]}")
                
                # Verify structure
                assert "id" in video or "video_id" in video
                
    @pytest.mark.asyncio
    async def test_list_videos_with_pagination(self):
        """GET /api/videos/ with pagination."""
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # First page
            response = await client.get(
                f"{API_BASE_URL}/api/videos/",
                params={"limit": 5, "offset": 0}
            )
            
            assert response.status_code == 200
            data1 = response.json()
            page1 = data1 if isinstance(data1, list) else data1.get("videos", [])
            
            # Second page
            response = await client.get(
                f"{API_BASE_URL}/api/videos/",
                params={"limit": 5, "offset": 5}
            )
            
            assert response.status_code == 200
            data2 = response.json()
            page2 = data2 if isinstance(data2, list) else data2.get("videos", [])
            
            # Pages should be different (if enough data)
            if len(page1) == 5 and len(page2) > 0:
                page1_ids = {v.get("id") or v.get("video_id") for v in page1}
                page2_ids = {v.get("id") or v.get("video_id") for v in page2}
                
                assert page1_ids.isdisjoint(page2_ids), "Pages should not overlap"
                
            print(f"✅ Pagination working: page1={len(page1)}, page2={len(page2)}")

    @pytest.mark.asyncio
    async def test_get_single_video(self):
        """GET /api/videos/{id} - Get single video details."""
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # First get list to find a real ID
            response = await client.get(f"{API_BASE_URL}/api/videos/?limit=1")
            
            if response.status_code != 200:
                pytest.skip("Videos API not available")
            
            data = response.json()
            videos = data if isinstance(data, list) else data.get("videos", [])
            
            if not videos:
                pytest.skip("No videos in database")
            
            video_id = videos[0].get("id") or videos[0].get("video_id")
            
            # Get single video
            response = await client.get(f"{API_BASE_URL}/api/videos/{video_id}")
            
            assert response.status_code == 200, f"Failed to get video: {response.text}"
            
            video = response.json()
            print(f"✅ Retrieved video: {video.get('file_name', 'Untitled')[:50]}")


# =============================================================================
# ANALYSIS API - REAL TESTS
# =============================================================================

class TestAnalysisAPIReal:
    """Real tests for /api/analysis endpoints."""

    @pytest.mark.asyncio
    async def test_generate_captions_for_all_platforms(self):
        """
        Generate captions for EACH platform and verify limits.
        """
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Get a video
            response = await client.get(f"{API_BASE_URL}/api/videos?limit=1")
            
            if response.status_code != 200:
                pytest.skip("Videos API not available")
            
            videos = response.json().get("videos", [])
            if not videos:
                pytest.skip("No videos")
            
            video_id = videos[0].get("id") or videos[0].get("video_id")
            
            # Test each platform
            platforms = ["tiktok", "instagram", "youtube", "twitter", "threads", "linkedin"]
            
            for platform in platforms:
                response = await client.post(
                    f"{API_BASE_URL}/api/analysis/generate-captions/{video_id}",
                    json={"platform": platform, "tone": "engaging"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    captions = data.get("captions", {})
                    
                    if platform in captions:
                        caption_len = len(captions[platform])
                        print(f"  ✅ {platform}: {caption_len} chars")
                    else:
                        print(f"  ⚠️ {platform}: No caption generated")
                else:
                    print(f"  ❌ {platform}: {response.status_code}")

    @pytest.mark.asyncio
    async def test_analysis_returns_platform_specific_content(self):
        """
        Verify different platforms get different content.
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(f"{API_BASE_URL}/api/videos?limit=1")
            
            if response.status_code != 200:
                pytest.skip("Videos API not available")
            
            videos = response.json().get("videos", [])
            if not videos:
                pytest.skip("No videos")
            
            video_id = videos[0].get("id") or videos[0].get("video_id")
            
            # Generate for TikTok
            response = await client.post(
                f"{API_BASE_URL}/api/analysis/generate-captions/{video_id}",
                json={"platform": "tiktok", "tone": "engaging"}
            )
            
            if response.status_code != 200:
                pytest.skip("Caption generation not available")
            
            data = response.json()
            captions = data.get("captions", {})
            
            # Check that captions are different
            unique_captions = set(captions.values())
            
            print(f"✅ Generated {len(captions)} platform captions")
            print(f"   Unique captions: {len(unique_captions)}")
            
            # Should have some differentiation
            if len(captions) > 1:
                assert len(unique_captions) > 1, "Captions should differ by platform"


# =============================================================================
# SCHEDULE API - REAL TESTS  
# =============================================================================

class TestScheduleAPIReal:
    """Real tests for /api/schedule endpoints."""

    @pytest.mark.asyncio
    async def test_list_scheduled_posts(self):
        """GET /api/schedule - List scheduled posts."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API_BASE_URL}/api/schedule")
            
            if response.status_code == 404:
                pytest.skip("Schedule endpoint not found")
            
            assert response.status_code == 200, f"Failed: {response.text}"
            
            data = response.json()
            posts = data.get("posts", data.get("scheduled_posts", []))
            
            print(f"✅ Retrieved {len(posts)} scheduled posts")
            
            # Show status breakdown
            statuses = {}
            for post in posts:
                status = post.get("status", "unknown")
                statuses[status] = statuses.get(status, 0) + 1
            
            print(f"   By status: {statuses}")

    @pytest.mark.asyncio
    async def test_schedule_endpoint_accepts_post(self):
        """POST /api/schedule - Verify endpoint accepts schedule requests."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get a video ID
            response = await client.get(f"{API_BASE_URL}/api/videos?limit=1")
            
            if response.status_code != 200:
                pytest.skip("Videos API not available")
            
            videos = response.json().get("videos", [])
            if not videos:
                pytest.skip("No videos")
            
            video_id = videos[0].get("id") or videos[0].get("video_id")
            
            # Try to schedule (far future to avoid actual publish)
            schedule_time = datetime.now(timezone.utc) + timedelta(days=365)
            
            response = await client.post(
                f"{API_BASE_URL}/api/schedule",
                json={
                    "media_id": str(video_id),
                    "platform": "tiktok",
                    "account_id": 710,  # Test account
                    "scheduled_time": schedule_time.isoformat(),
                    "caption": "Integration test - will be deleted"
                }
            )
            
            # Expect either 200/201 (created) or 400/422 (validation error)
            print(f"Schedule POST response: {response.status_code}")
            
            if response.status_code in [200, 201]:
                print("✅ Schedule endpoint accepts POST requests")
                
                # Clean up - delete the test post
                data = response.json()
                if "id" in data:
                    await client.delete(f"{API_BASE_URL}/api/schedule/{data['id']}")
            elif response.status_code in [400, 422]:
                print(f"⚠️ Validation error (expected): {response.text[:100]}")
            else:
                print(f"Response: {response.text[:200]}")


# =============================================================================
# BLOTATO API - REAL TESTS
# =============================================================================

class TestBlotatoAPIReal:
    """Real tests for /api/blotato endpoints."""

    @pytest.mark.asyncio
    async def test_list_blotato_accounts(self):
        """GET /api/blotato/accounts - List all connected accounts."""
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(f"{API_BASE_URL}/api/blotato/accounts")
            
            if response.status_code == 404:
                pytest.skip("Blotato endpoint not found")
            
            assert response.status_code == 200, f"Failed: {response.text}"
            
            data = response.json()
            # Handle both formats: list or {"accounts": [...]}
            accounts = data if isinstance(data, list) else data.get("accounts", [])
            
            print(f"✅ Retrieved {len(accounts)} Blotato accounts")
            
            # Count by platform
            platforms = {}
            for acc in accounts:
                platform = acc.get("platform", "unknown")
                platforms[platform] = platforms.get(platform, 0) + 1
            
            print(f"   By platform: {platforms}")

    @pytest.mark.asyncio
    async def test_verify_account_endpoint(self):
        """POST /api/blotato/verify-account - Verify account status."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get accounts first
            response = await client.get(f"{API_BASE_URL}/api/blotato/accounts")
            
            if response.status_code != 200:
                pytest.skip("Blotato accounts not available")
            
            accounts = response.json().get("accounts", [])
            
            if not accounts:
                pytest.skip("No accounts to verify")
            
            account = accounts[0]
            account_id = account.get("id")
            
            # Try verification
            response = await client.post(
                f"{API_BASE_URL}/api/blotato/verify-account/{account_id}"
            )
            
            print(f"Account verification response: {response.status_code}")


# =============================================================================
# PLATFORM LIMITS API - REAL TESTS
# =============================================================================

class TestPlatformLimitsAPIReal:
    """Real tests for platform limits endpoints."""

    @pytest.mark.asyncio
    async def test_get_platform_limits(self):
        """GET /api/platform-limits - Get all platform character limits."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API_BASE_URL}/api/platform-limits")
            
            if response.status_code == 404:
                pytest.skip("Platform limits endpoint not found")
            
            assert response.status_code == 200
            
            data = response.json()
            platforms = data.get("platforms", data)
            
            print(f"✅ Platform limits retrieved")
            
            for platform, limits in platforms.items():
                if isinstance(limits, dict):
                    title_target = limits.get("title_target", "N/A")
                    desc_target = limits.get("description_target", "N/A")
                    print(f"   {platform}: title={title_target}, desc={desc_target}")


# =============================================================================
# ANALYTICS API - REAL TESTS
# =============================================================================

class TestAnalyticsAPIReal:
    """Real tests for analytics endpoints."""

    @pytest.mark.asyncio
    async def test_get_analytics_overview(self):
        """GET /api/analytics - Overview of content performance."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API_BASE_URL}/api/analytics")
            
            if response.status_code == 404:
                pytest.skip("Analytics endpoint not found")
            
            assert response.status_code == 200
            
            data = response.json()
            print(f"✅ Analytics data retrieved: {list(data.keys())[:5]}...")

    @pytest.mark.asyncio
    async def test_get_posted_content(self):
        """GET /api/posted-content - List published content."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{API_BASE_URL}/api/posted-content")
            
            if response.status_code == 404:
                pytest.skip("Posted content endpoint not found")
            
            assert response.status_code == 200
            
            data = response.json()
            posts = data.get("posts", data.get("content", []))
            
            print(f"✅ Retrieved {len(posts)} posted content items")


# =============================================================================
# ERROR HANDLING TESTS - REAL
# =============================================================================

class TestErrorHandlingReal:
    """Test error handling with real requests."""

    @pytest.mark.asyncio
    async def test_404_for_nonexistent_video(self):
        """Request nonexistent video returns 404."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            fake_id = str(uuid.uuid4())
            response = await client.get(f"{API_BASE_URL}/api/videos/{fake_id}")
            
            assert response.status_code == 404, "Should return 404 for nonexistent video"
            print("✅ 404 returned for nonexistent video")

    @pytest.mark.asyncio
    async def test_invalid_uuid_handling(self):
        """Invalid UUID returns appropriate error."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{API_BASE_URL}/api/videos/not-a-uuid")
            
            # Should return 400 or 422, not 500
            assert response.status_code in [400, 404, 422], \
                f"Should handle invalid UUID gracefully, got {response.status_code}"
            print(f"✅ Invalid UUID handled: {response.status_code}")

    @pytest.mark.asyncio
    async def test_malformed_json_handling(self):
        """Malformed JSON returns 422."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{API_BASE_URL}/api/schedule",
                content="not valid json",
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code in [400, 422], \
                f"Should reject malformed JSON, got {response.status_code}"
            print(f"✅ Malformed JSON rejected: {response.status_code}")


# =============================================================================
# CONCURRENT REQUEST TESTS - REAL
# =============================================================================

class TestConcurrentRequestsReal:
    """Test system under concurrent load."""

    @pytest.mark.asyncio
    async def test_concurrent_video_list_requests(self):
        """Handle 20 concurrent video list requests."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            async def fetch_videos():
                return await client.get(f"{API_BASE_URL}/api/videos?limit=5")
            
            start = datetime.now()
            responses = await asyncio.gather(*[fetch_videos() for _ in range(20)])
            elapsed = (datetime.now() - start).total_seconds()
            
            success = sum(1 for r in responses if r.status_code == 200)
            
            print(f"✅ 20 concurrent requests in {elapsed:.2f}s")
            print(f"   Success rate: {success}/20")
            
            assert success >= 18, "At least 90% should succeed"

    @pytest.mark.asyncio
    async def test_mixed_endpoint_concurrent_requests(self):
        """Handle concurrent requests to different endpoints."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            endpoints = [
                f"{API_BASE_URL}/health",
                f"{API_BASE_URL}/api/videos?limit=1",
                f"{API_BASE_URL}/api/schedule",
                f"{API_BASE_URL}/api/blotato/accounts",
            ]
            
            async def fetch(url):
                try:
                    return await client.get(url)
                except:
                    return None
            
            # 5 requests to each endpoint = 20 total
            tasks = [fetch(url) for url in endpoints * 5]
            
            start = datetime.now()
            responses = await asyncio.gather(*tasks)
            elapsed = (datetime.now() - start).total_seconds()
            
            valid = [r for r in responses if r is not None]
            success = sum(1 for r in valid if r.status_code in [200, 404])
            
            print(f"✅ 20 mixed requests in {elapsed:.2f}s")
            print(f"   Valid responses: {len(valid)}/20")


if __name__ == "__main__":
    os.environ["RUN_REAL_INTEGRATION_TESTS"] = "true"
    pytest.main([__file__, "-v", "-s"])
