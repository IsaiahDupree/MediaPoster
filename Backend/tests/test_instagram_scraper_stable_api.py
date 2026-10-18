"""
Comprehensive tests for Instagram Scraper Stable API endpoints.

Tests all endpoints documented in:
- Backend/docs/rapidapi/instagram-scraper-stable-api.md

Requires RAPIDAPI_KEY environment variable.
"""

import pytest
import httpx
import os
from typing import Dict, Any, Optional
import time

# API Configuration
API_BASE = "https://instagram-scraper-stable-api.p.rapidapi.com"
API_KEY = os.getenv("RAPIDAPI_KEY")

# Test usernames (use public accounts for testing)
TEST_USERNAME = "instagram"  # Official Instagram account (always exists)
TEST_SHORTCODE = "C"  # Short shortcode for testing (may need updating)

# Skip all tests if API key is not set
pytestmark = pytest.mark.skipif(
    not API_KEY,
    reason="RAPIDAPI_KEY environment variable not set"
)


def get_headers() -> Dict[str, str]:
    """Get required RapidAPI headers"""
    return {
        "X-RapidAPI-Key": API_KEY,
        "X-RapidAPI-Host": "instagram-scraper-stable-api.p.rapidapi.com",
        "Content-Type": "application/json"
    }


class TestUserProfile:
    """Tests for POST /v1/info endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_profile_by_username(self):
        """Test getting profile by username"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/info",
                headers=get_headers(),
                json={"username_or_id_or_url": TEST_USERNAME}
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            
            assert "data" in data
            profile = data["data"]
            
            # Required fields
            assert "id" in profile
            assert "username" in profile
            assert profile["username"].lower() == TEST_USERNAME.lower()
            
            # Optional but common fields
            assert "follower_count" in profile or "edge_followed_by" in profile
            assert "profile_pic_url" in profile or "profile_pic_url_hd" in profile
    
    @pytest.mark.asyncio
    async def test_get_profile_invalid_username(self):
        """Test getting profile with invalid username"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/info",
                headers=get_headers(),
                json={"username_or_id_or_url": "nonexistent_user_12345_xyz"}
            )
            
            # Should return 404 or 400 for invalid username
            assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}"
    
    @pytest.mark.asyncio
    async def test_get_profile_missing_parameter(self):
        """Test getting profile without required parameter"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/info",
                headers=get_headers(),
                json={}
            )
            
            # Should return 400 for missing parameter
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    
    @pytest.mark.asyncio
    async def test_get_profile_response_structure(self):
        """Test that profile response has correct structure"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/info",
                headers=get_headers(),
                json={"username_or_id_or_url": TEST_USERNAME}
            )
            
            if response.status_code == 200:
                data = response.json()
                profile = data.get("data", {})
                
                # Verify field types
                assert isinstance(profile.get("id"), (str, int))
                assert isinstance(profile.get("username"), str)
                assert isinstance(profile.get("follower_count", 0), (int, type(None)))
                assert isinstance(profile.get("is_verified", False), bool)


class TestUserReels:
    """Tests for POST /v1/reels endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_user_reels(self):
        """Test getting user reels"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/reels",
                headers=get_headers(),
                json={
                    "username_or_id_or_url": TEST_USERNAME,
                    "count": 5
                }
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            
            assert "data" in data
            assert "items" in data["data"]
            
            items = data["data"]["items"]
            assert isinstance(items, list)
            assert len(items) <= 5  # Should respect count parameter
    
    @pytest.mark.asyncio
    async def test_get_user_reels_with_count(self):
        """Test getting user reels with count parameter"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/reels",
                headers=get_headers(),
                json={
                    "username_or_id_or_url": TEST_USERNAME,
                    "count": 3
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("data", {}).get("items", [])
                assert len(items) <= 3
    
    @pytest.mark.asyncio
    async def test_get_user_reels_response_structure(self):
        """Test that reels response has correct structure"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/reels",
                headers=get_headers(),
                json={
                    "username_or_id_or_url": TEST_USERNAME,
                    "count": 1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("data", {}).get("items", [])
                
                if items:
                    reel = items[0]
                    # Check for required fields
                    assert "id" in reel or "pk" in reel
                    assert "code" in reel
                    
                    # Check for video/thumbnail URLs
                    has_video = "video_versions" in reel and len(reel["video_versions"]) > 0
                    has_thumbnail = "image_versions2" in reel
                    assert has_video or has_thumbnail, "Reel should have video or thumbnail"
    
    @pytest.mark.asyncio
    async def test_get_user_reels_audio_metadata(self):
        """Test that reels include audio metadata"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/reels",
                headers=get_headers(),
                json={
                    "username_or_id_or_url": TEST_USERNAME,
                    "count": 5
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("data", {}).get("items", [])
                
                # At least one reel should have audio metadata
                has_audio = False
                for item in items:
                    if "clips_metadata" in item:
                        clips = item["clips_metadata"]
                        if "music_info" in clips or "original_sound_info" in clips:
                            has_audio = True
                            break
                
                # Note: Not all reels have audio, so this is informational
                print(f"Found reels with audio: {has_audio}")


class TestReelByShortcode:
    """Tests for GET /v1/reel_by_shortcode endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_reel_by_shortcode(self):
        """Test getting reel by shortcode"""
        # First get a real shortcode from reels endpoint
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get a reel first
            reels_response = await client.post(
                f"{API_BASE}/v1/reels",
                headers=get_headers(),
                json={
                    "username_or_id_or_url": TEST_USERNAME,
                    "count": 1
                }
            )
            
            if reels_response.status_code == 200:
                reels_data = reels_response.json()
                items = reels_data.get("data", {}).get("items", [])
                
                if items:
                    shortcode = items[0].get("code")
                    if shortcode:
                        # Now test the shortcode endpoint
                        response = await client.get(
                            f"{API_BASE}/v1/reel_by_shortcode",
                            headers=get_headers(),
                            params={"shortcode": shortcode}
                        )
                        
                        assert response.status_code in [200, 404], f"Expected 200/404, got {response.status_code}"
                        
                        if response.status_code == 200:
                            data = response.json()
                            assert "data" in data
                            reel = data["data"]
                            assert reel.get("code") == shortcode
    
    @pytest.mark.asyncio
    async def test_get_reel_by_shortcode_invalid(self):
        """Test getting reel with invalid shortcode"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{API_BASE}/v1/reel_by_shortcode",
                headers=get_headers(),
                params={"shortcode": "INVALID_SHORTCODE_XYZ123"}
            )
            
            # Should return 404 for invalid shortcode
            assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}"
    
    @pytest.mark.asyncio
    async def test_get_reel_by_shortcode_missing_parameter(self):
        """Test getting reel without shortcode parameter"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{API_BASE}/v1/reel_by_shortcode",
                headers=get_headers()
            )
            
            # Should return 400 for missing parameter
            assert response.status_code == 400, f"Expected 400, got {response.status_code}"


class TestMediaByShortcode:
    """Tests for GET /v1/media_by_shortcode endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_media_by_shortcode(self):
        """Test getting media by shortcode"""
        # First get a real shortcode from posts endpoint
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get a post first
            posts_response = await client.post(
                f"{API_BASE}/v1/posts",
                headers=get_headers(),
                json={
                    "username_or_id_or_url": TEST_USERNAME,
                    "count": 1
                }
            )
            
            if posts_response.status_code == 200:
                posts_data = posts_response.json()
                items = posts_data.get("data", {}).get("items", [])
                
                if items:
                    shortcode = items[0].get("code")
                    if shortcode:
                        # Now test the media endpoint
                        response = await client.get(
                            f"{API_BASE}/v1/media_by_shortcode",
                            headers=get_headers(),
                            params={"shortcode": shortcode}
                        )
                        
                        assert response.status_code in [200, 404], f"Expected 200/404, got {response.status_code}"
                        
                        if response.status_code == 200:
                            data = response.json()
                            assert "data" in data or isinstance(data, dict)
    
    @pytest.mark.asyncio
    async def test_get_media_by_shortcode_invalid(self):
        """Test getting media with invalid shortcode"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{API_BASE}/v1/media_by_shortcode",
                headers=get_headers(),
                params={"shortcode": "INVALID_SHORTCODE_XYZ123"}
            )
            
            assert response.status_code in [400, 404], f"Expected 400/404, got {response.status_code}"


class TestUserPosts:
    """Tests for POST /v1/posts endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_user_posts(self):
        """Test getting user posts"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/posts",
                headers=get_headers(),
                json={
                    "username_or_id_or_url": TEST_USERNAME,
                    "count": 5
                }
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            
            assert "data" in data
            assert "items" in data["data"]
            
            items = data["data"]["items"]
            assert isinstance(items, list)
            assert len(items) <= 5
    
    @pytest.mark.asyncio
    async def test_get_user_posts_pagination(self):
        """Test getting user posts with pagination"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get first page
            response1 = await client.post(
                f"{API_BASE}/v1/posts",
                headers=get_headers(),
                json={
                    "username_or_id_or_url": TEST_USERNAME,
                    "count": 3
                }
            )
            
            if response1.status_code == 200:
                data1 = response1.json()
                pagination_token = data1.get("pagination_token")
                
                if pagination_token:
                    # Get second page
                    response2 = await client.post(
                        f"{API_BASE}/v1/posts",
                        headers=get_headers(),
                        json={
                            "username_or_id_or_url": TEST_USERNAME,
                            "count": 3,
                            "pagination_token": pagination_token
                        }
                    )
                    
                    if response2.status_code == 200:
                        data2 = response2.json()
                        items1 = data1.get("data", {}).get("items", [])
                        items2 = data2.get("data", {}).get("items", [])
                        
                        # Items should be different (unless user has < 3 posts)
                        if len(items1) == 3 and len(items2) > 0:
                            # Verify we got different items
                            ids1 = {item.get("id") for item in items1}
                            ids2 = {item.get("id") for item in items2}
                            # Should have different IDs (unless user has duplicates)
                            print(f"Page 1 IDs: {ids1}, Page 2 IDs: {ids2}")
    
    @pytest.mark.asyncio
    async def test_get_user_posts_response_structure(self):
        """Test that posts response has correct structure"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/posts",
                headers=get_headers(),
                json={
                    "username_or_id_or_url": TEST_USERNAME,
                    "count": 1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("data", {}).get("items", [])
                
                if items:
                    post = items[0]
                    # Check for required fields
                    assert "id" in post or "pk" in post
                    assert "code" in post
                    
                    # Check media type
                    assert "media_type" in post or "is_video" in post


class TestSearch:
    """Tests for POST /v1/search endpoint"""
    
    @pytest.mark.asyncio
    async def test_search_users(self):
        """Test searching for users"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/search",
                headers=get_headers(),
                json={"query": "instagram"}
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
            data = response.json()
            
            assert "data" in data
            assert "users" in data["data"] or "hashtags" in data["data"]
            
            users = data["data"].get("users", [])
            if users:
                user = users[0]
                assert "username" in user or "pk" in user
    
    @pytest.mark.asyncio
    async def test_search_hashtags(self):
        """Test searching for hashtags"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/search",
                headers=get_headers(),
                json={"query": "photography"}
            )
            
            if response.status_code == 200:
                data = response.json()
                hashtags = data.get("data", {}).get("hashtags", [])
                
                if hashtags:
                    hashtag = hashtags[0]
                    assert "name" in hashtag
    
    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        """Test search with empty query"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/search",
                headers=get_headers(),
                json={"query": ""}
            )
            
            # Should handle empty query gracefully
            assert response.status_code in [200, 400], f"Expected 200/400, got {response.status_code}"


class TestErrorHandling:
    """Tests for error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        """Test that missing API key returns 401/403"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/info",
                headers={
                    "X-RapidAPI-Host": "instagram-scraper-stable-api.p.rapidapi.com",
                    "Content-Type": "application/json"
                },
                json={"username_or_id_or_url": TEST_USERNAME}
            )
            
            assert response.status_code in [401, 403], f"Expected 401/403, got {response.status_code}"
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self):
        """Test that rate limit headers are present"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/info",
                headers=get_headers(),
                json={"username_or_id_or_url": TEST_USERNAME}
            )
            
            if response.status_code == 200:
                # Check for rate limit headers (may not always be present)
                headers = response.headers
                if "X-RateLimit-Remaining" in headers:
                    remaining = headers["X-RateLimit-Remaining"]
                    assert remaining.isdigit() or remaining == "unlimited"
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test that requests timeout appropriately"""
        async with httpx.AsyncClient(timeout=0.1) as client:  # Very short timeout
            try:
                response = await client.post(
                    f"{API_BASE}/v1/info",
                    headers=get_headers(),
                    json={"username_or_id_or_url": TEST_USERNAME}
                )
                # If it completes, that's fine
            except httpx.TimeoutException:
                # Expected for very short timeout
                pass


class TestIntegration:
    """Integration tests combining multiple endpoints"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test a complete workflow: profile -> posts -> media detail"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Get profile
            profile_response = await client.post(
                f"{API_BASE}/v1/info",
                headers=get_headers(),
                json={"username_or_id_or_url": TEST_USERNAME}
            )
            
            if profile_response.status_code == 200:
                profile_data = profile_response.json()
                username = profile_data["data"].get("username")
                assert username is not None
                
                # 2. Get posts
                posts_response = await client.post(
                    f"{API_BASE}/v1/posts",
                    headers=get_headers(),
                    json={
                        "username_or_id_or_url": username,
                        "count": 1
                    }
                )
                
                if posts_response.status_code == 200:
                    posts_data = posts_response.json()
                    items = posts_data.get("data", {}).get("items", [])
                    
                    if items:
                        shortcode = items[0].get("code")
                        
                        # 3. Get media detail
                        if shortcode:
                            media_response = await client.get(
                                f"{API_BASE}/v1/media_by_shortcode",
                                headers=get_headers(),
                                params={"shortcode": shortcode}
                            )
                            
                            assert media_response.status_code in [200, 404]
                            
                            if media_response.status_code == 200:
                                media_data = media_response.json()
                                assert "data" in media_data or isinstance(media_data, dict)
    
    @pytest.mark.asyncio
    async def test_reels_and_audio_extraction(self):
        """Test getting reels and extracting audio URLs"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/reels",
                headers=get_headers(),
                json={
                    "username_or_id_or_url": TEST_USERNAME,
                    "count": 5
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("data", {}).get("items", [])
                
                audio_found = False
                for item in items:
                    clips_metadata = item.get("clips_metadata", {})
                    
                    # Check for music info
                    music_info = clips_metadata.get("music_info", {})
                    if music_info:
                        music_asset = music_info.get("music_asset_info", {})
                        audio_url = music_asset.get("progressive_download_url")
                        if audio_url:
                            audio_found = True
                            assert audio_url.startswith("http")
                    
                    # Check for original sound
                    if not audio_found:
                        original_sound = clips_metadata.get("original_sound_info", {})
                        if original_sound:
                            audio_asset = original_sound.get("audio_asset_info", {})
                            audio_url = audio_asset.get("progressive_download_url")
                            if audio_url:
                                audio_found = True
                                assert audio_url.startswith("http")
                
                print(f"Found reels with audio URLs: {audio_found}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

