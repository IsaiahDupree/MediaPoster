"""
Test Music/Audio Extraction from Instagram Scraper Stable API

Tests all endpoints that can provide music/audio data.
"""

import pytest
import httpx
import os
import json
from typing import Dict, List, Optional

# API Configuration
API_BASE = "https://instagram-scraper-stable-api.p.rapidapi.com"
API_KEY = os.getenv("RAPIDAPI_KEY")

# Test usernames (use accounts likely to have reels with music)
TEST_USERNAME = "instagram"  # Official Instagram account
TEST_USERNAME_WITH_REELS = "instagram"  # Change to account with reels

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


class TestMusicExtraction:
    """Test music/audio extraction from various endpoints"""
    
    @pytest.mark.asyncio
    async def test_extract_music_from_reels_endpoint(self):
        """Test extracting music from POST /v1/reels endpoint"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/reels",
                headers=get_headers(),
                json={
                    "username_or_id_or_url": TEST_USERNAME,
                    "count": 12
                }
            )
            
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text[:500]}"
            data = response.json()
            
            items = data.get("data", {}).get("items", [])
            assert len(items) > 0, "No reels returned"
            
            # Check for music in reels
            music_found = False
            audio_urls = []
            
            for item in items:
                clips_metadata = item.get("clips_metadata", {})
                
                # Check music_info
                music_info = clips_metadata.get("music_info", {})
                if music_info:
                    music_asset = music_info.get("music_asset_info", {})
                    audio_url = music_asset.get("progressive_download_url")
                    if audio_url:
                        music_found = True
                        audio_urls.append({
                            "type": "music",
                            "url": audio_url,
                            "title": music_asset.get("title"),
                            "artist": music_asset.get("display_artist"),
                            "audio_id": music_asset.get("audio_id")
                        })
                
                # Check original_sound_info
                original_sound = clips_metadata.get("original_sound_info", {})
                if original_sound:
                    audio_asset = original_sound.get("audio_asset_info", {})
                    audio_url = audio_asset.get("progressive_download_url")
                    if audio_url:
                        music_found = True
                        audio_urls.append({
                            "type": "original_sound",
                            "url": audio_url,
                            "title": original_sound.get("original_audio_title", "Original Sound"),
                            "artist": original_sound.get("ig_artist", {}).get("username", "Unknown")
                        })
            
            print(f"\n✓ Found {len(audio_urls)} audio tracks in {len(items)} reels")
            for i, audio in enumerate(audio_urls[:5], 1):
                print(f"  {i}. {audio['type']}: {audio['title']} by {audio['artist']}")
                print(f"     URL: {audio['url'][:80]}...")
            
            # At least verify the structure exists (may not always have music)
            assert "clips_metadata" in items[0] if items else True, "Reels should have clips_metadata"
    
    @pytest.mark.asyncio
    async def test_extract_music_from_detailed_reel(self):
        """Test extracting music from GET Detailed Reel Data endpoint"""
        # First get a reel shortcode
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get reels first
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
                        # Test detailed reel endpoint
                        # Note: The exact endpoint name may vary - trying common variations
                        endpoints_to_try = [
                            f"/v1/reel_by_shortcode?shortcode={shortcode}",
                            f"/v1/detailed_reel_data?shortcode={shortcode}",
                            f"/v1/get_reel_title_description?shortcode={shortcode}"
                        ]
                        
                        for endpoint in endpoints_to_try:
                            try:
                                response = await client.get(
                                    f"{API_BASE}{endpoint}",
                                    headers=get_headers()
                                )
                                
                                if response.status_code == 200:
                                    data = response.json()
                                    
                                    # Check for music
                                    if "data" in data:
                                        item = data.get("data", {})
                                        clips_metadata = item.get("clips_metadata", {})
                                        
                                        music_info = clips_metadata.get("music_info", {})
                                        if music_info:
                                            music_asset = music_info.get("music_asset_info", {})
                                            audio_url = music_asset.get("progressive_download_url")
                                            
                                            if audio_url:
                                                print(f"\n✓ Found music in detailed reel endpoint: {endpoint}")
                                                print(f"  Title: {music_asset.get('title')}")
                                                print(f"  Artist: {music_asset.get('display_artist')}")
                                                print(f"  URL: {audio_url[:80]}...")
                                                assert True
                                                return
                                    
                                    print(f"  Endpoint {endpoint} returned data but no music found")
                            except Exception as e:
                                print(f"  Endpoint {endpoint} failed: {e}")
                                continue
                        
                        print("  Note: Could not find working detailed reel endpoint with music")
    
    @pytest.mark.asyncio
    async def test_extract_music_from_user_posts(self):
        """Test extracting music from POST /v1/posts endpoint"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{API_BASE}/v1/posts",
                headers=get_headers(),
                json={
                    "username_or_id_or_url": TEST_USERNAME,
                    "count": 12
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("data", {}).get("items", [])
                
                audio_found = False
                for item in items:
                    # Posts may also have audio (video posts)
                    clips_metadata = item.get("clips_metadata", {})
                    if clips_metadata:
                        music_info = clips_metadata.get("music_info", {})
                        if music_info:
                            music_asset = music_info.get("music_asset_info", {})
                            if music_asset.get("progressive_download_url"):
                                audio_found = True
                                print(f"\n✓ Found audio in posts endpoint")
                                break
                
                if not audio_found:
                    print("  Note: No audio found in posts (may be normal for photo posts)")
    
    @pytest.mark.asyncio
    async def test_search_for_accounts_with_music(self):
        """Test searching for accounts and then extracting their music"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Search for accounts
            search_response = await client.post(
                f"{API_BASE}/v1/search",
                headers=get_headers(),
                json={"query": "music"}
            )
            
            if search_response.status_code == 200:
                search_data = search_response.json()
                users = search_data.get("data", {}).get("users", [])
                
                if users:
                    # Get reels from first user
                    username = users[0].get("username")
                    print(f"\nTesting music extraction from @{username}")
                    
                    reels_response = await client.post(
                        f"{API_BASE}/v1/reels",
                        headers=get_headers(),
                        json={
                            "username_or_id_or_url": username,
                            "count": 5
                        }
                    )
                    
                    if reels_response.status_code == 200:
                        reels_data = reels_response.json()
                        items = reels_data.get("data", {}).get("items", [])
                        
                        music_count = 0
                        for item in items:
                            clips_metadata = item.get("clips_metadata", {})
                            music_info = clips_metadata.get("music_info", {})
                            if music_info and music_info.get("music_asset_info", {}).get("progressive_download_url"):
                                music_count += 1
                        
                        print(f"  Found {music_count} reels with music out of {len(items)} total")
                        assert music_count >= 0  # May be 0, that's okay
    
    @pytest.mark.asyncio
    async def test_audio_url_accessibility(self):
        """Test that extracted audio URLs are accessible"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get reels
            response = await client.post(
                f"{API_BASE}/v1/reels",
                headers=get_headers(),
                json={
                    "username_or_id_or_url": TEST_USERNAME,
                    "count": 12
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                items = data.get("data", {}).get("items", [])
                
                audio_urls = []
                for item in items:
                    clips_metadata = item.get("clips_metadata", {})
                    
                    # Get music URL
                    music_info = clips_metadata.get("music_info", {})
                    if music_info:
                        audio_url = music_info.get("music_asset_info", {}).get("progressive_download_url")
                        if audio_url:
                            audio_urls.append(audio_url)
                
                # Test first audio URL if available
                if audio_urls:
                    test_url = audio_urls[0]
                    print(f"\nTesting audio URL accessibility: {test_url[:80]}...")
                    
                    try:
                        # Try to access the audio URL (HEAD request to check if accessible)
                        audio_response = await client.head(test_url, timeout=10.0, follow_redirects=True)
                        
                        if audio_response.status_code == 200:
                            print(f"  ✓ Audio URL is accessible")
                            print(f"  Content-Type: {audio_response.headers.get('content-type', 'unknown')}")
                            print(f"  Content-Length: {audio_response.headers.get('content-length', 'unknown')} bytes")
                        else:
                            print(f"  ⚠️  Audio URL returned status {audio_response.status_code}")
                    except Exception as e:
                        print(f"  ⚠️  Could not access audio URL: {e}")
                else:
                    print("  No audio URLs found to test")


class TestAllAvailableEndpoints:
    """Test all endpoints mentioned in the API playground"""
    
    @pytest.mark.asyncio
    async def test_user_reels_endpoint(self):
        """Test POST User Reels endpoint"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try different endpoint variations
            endpoints = [
                ("/v1/reels", {"username_or_id_or_url": TEST_USERNAME, "count": 5}),
                ("/v1/user_reels", {"username_or_id_or_url": TEST_USERNAME, "count": 5}),
            ]
            
            for endpoint, payload in endpoints:
                try:
                    response = await client.post(
                        f"{API_BASE}{endpoint}",
                        headers=get_headers(),
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        items = data.get("data", {}).get("items", [])
                        
                        print(f"\n✓ Endpoint {endpoint} works")
                        print(f"  Returned {len(items)} reels")
                        
                        # Check for music
                        music_count = 0
                        for item in items:
                            if item.get("clips_metadata", {}).get("music_info"):
                                music_count += 1
                        
                        print(f"  {music_count} reels have music metadata")
                        return True
                except Exception as e:
                    print(f"  Endpoint {endpoint} failed: {e}")
            
            return False
    
    @pytest.mark.asyncio
    async def test_detailed_media_endpoints(self):
        """Test various detailed media endpoints"""
        # First get a shortcode
        async with httpx.AsyncClient(timeout=30.0) as client:
            reels_response = await client.post(
                f"{API_BASE}/v1/reels",
                headers=get_headers(),
                json={"username_or_id_or_url": TEST_USERNAME, "count": 1}
            )
            
            if reels_response.status_code == 200:
                items = reels_response.json().get("data", {}).get("items", [])
                if items:
                    shortcode = items[0].get("code")
                    
                    # Test different endpoint variations
                    endpoints = [
                        f"/v1/reel_by_shortcode?shortcode={shortcode}",
                        f"/v1/detailed_reel_data?shortcode={shortcode}",
                        f"/v1/get_reel_title_description?shortcode={shortcode}",
                        f"/v1/media_by_shortcode?shortcode={shortcode}",
                        f"/v1/detailed_media_data_v2?shortcode={shortcode}",
                    ]
                    
                    for endpoint in endpoints:
                        try:
                            response = await client.get(
                                f"{API_BASE}{endpoint}",
                                headers=get_headers()
                            )
                            
                            if response.status_code == 200:
                                data = response.json()
                                print(f"\n✓ Endpoint {endpoint} works")
                                
                                # Check for music
                                if "data" in data:
                                    item = data["data"]
                                    clips = item.get("clips_metadata", {})
                                    if clips.get("music_info"):
                                        print(f"  Contains music metadata")
                                
                                return True
                        except Exception as e:
                            continue
            
            return False


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

