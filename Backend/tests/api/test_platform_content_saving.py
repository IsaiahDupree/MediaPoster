"""
Tests for platform_content saving functionality

PROBLEM EXPLANATION:
===================
The platform_content field in video_analysis table is a JSONB column that stores
platform-specific content recommendations (title, description, hashtags, etc. for each platform).

ISSUE:
- The PUT /api/media-db/analysis/{media_id} endpoint had platform_content saving COMMENTED OUT
- Even though the column exists in the database (JSONB type)
- This meant any updates to platform_content via the API were silently ignored
- The data was accepted in the request but never persisted to the database

FIX:
- Uncommented the platform_content saving logic in both update and create paths
- Now platform_content is properly saved when provided in the request
"""
import pytest
import requests
import json
from uuid import uuid4


BASE_URL = "http://localhost:5555"


def test_platform_content_saves_on_update():
    """Test that platform_content is saved when updating existing analysis"""
    # First, we need a video with analysis
    # This test assumes you have at least one analyzed video in the database
    
    # Get list of analyzed videos
    response = requests.get(f"{BASE_URL}/api/media-db/list?limit=10", timeout=30)
    assert response.status_code == 200, f"Failed to get video list: {response.status_code}"
    videos = response.json()
    
    # Find an analyzed video
    analyzed_video = None
    for video in videos:
        if video.get("status") == "analyzed":
            analyzed_video = video
            break
    
    if not analyzed_video:
        pytest.skip("No analyzed videos found in database")
    
    media_id = analyzed_video["media_id"]
    
    # Test data - platform content with title and description
    test_platform_content = [
        {
            "platform": "tiktok",
            "account_id": 710,
            "title": "Test Title from API",
            "description": "Test Description from API",
            "hashtags": ["#test", "#api"],
            "optimal_length": "15-60s"
        },
        {
            "platform": "instagram",
            "account_id": 710,
            "title": "IG Test Title",
            "description": "IG Test Description",
            "hashtags": ["#instagram", "#test"]
        }
    ]
    
    # Update analysis with platform_content
    update_response = requests.put(
        f"{BASE_URL}/api/media-db/analysis/{media_id}",
        json={
            "platform_content": test_platform_content
        },
        timeout=30
    )
    
    assert update_response.status_code == 200, f"Update failed: {update_response.text}"
    update_data = update_response.json()
    assert update_data["status"] == "saved"
    
    # Verify it was saved by fetching the analysis
    detail_response = requests.get(f"{BASE_URL}/api/media-db/detail/{media_id}", timeout=30)
    assert detail_response.status_code == 200
    
    detail_data = detail_response.json()
    saved_platform_content = detail_data.get("platform_content")
    
    assert saved_platform_content is not None, "platform_content should be saved"
    assert isinstance(saved_platform_content, list), "platform_content should be a list"
    assert len(saved_platform_content) == 2, "Should have 2 platform entries"
    
    # Verify TikTok entry
    tiktok_entry = next((pc for pc in saved_platform_content if pc["platform"] == "tiktok"), None)
    assert tiktok_entry is not None, "TikTok entry should exist"
    assert tiktok_entry["title"] == "Test Title from API"
    assert tiktok_entry["description"] == "Test Description from API"
    
    print(f"✅ platform_content saved successfully for video {media_id}")


def test_platform_content_saves_on_create():
    """Test that platform_content is saved when creating new analysis"""
    # This test requires a video without analysis
    # Get list of videos
    response = requests.get(f"{BASE_URL}/api/media-db/list?limit=10", timeout=30)
    assert response.status_code == 200
    videos = response.json()
    
    # Find a video without analysis
    unanalyzed_video = None
    for video in videos:
        if video.get("status") == "ingested":
            unanalyzed_video = video
            break
    
    if not unanalyzed_video:
        pytest.skip("No unanalyzed videos found")
    
    media_id = unanalyzed_video["media_id"]
    
    # Create analysis with platform_content
    test_platform_content = [
        {
            "platform": "tiktok",
            "title": "New Analysis Title",
            "description": "New Analysis Description"
        }
    ]
    
    create_response = requests.put(
        f"{BASE_URL}/api/media-db/analysis/{media_id}",
        json={
            "transcript": "Test transcript",
            "topics": ["test", "api"],
            "platform_content": test_platform_content
        },
        timeout=30
    )
    
    assert create_response.status_code == 200
    
    # Verify it was saved
    detail_response = requests.get(f"{BASE_URL}/api/media-db/detail/{media_id}", timeout=30)
    assert detail_response.status_code == 200
    
    detail_data = detail_response.json()
    saved_platform_content = detail_data.get("platform_content")
    
    assert saved_platform_content is not None
    assert len(saved_platform_content) == 1
    assert saved_platform_content[0]["title"] == "New Analysis Title"
    
    print(f"✅ platform_content saved on create for video {media_id}")


def test_platform_content_persistence():
    """Test that platform_content persists across multiple updates"""
    # Get an analyzed video
    response = requests.get(f"{BASE_URL}/api/media-db/list?limit=10", timeout=30)
    videos = response.json()
    analyzed_video = next((v for v in videos if v.get("status") == "analyzed"), None)
    
    if not analyzed_video:
        pytest.skip("No analyzed videos found")
    
    media_id = analyzed_video["media_id"]
    
    # First update
    platform_content_1 = [
        {"platform": "tiktok", "title": "First Title", "description": "First Desc"}
    ]
    
    requests.put(
        f"{BASE_URL}/api/media-db/analysis/{media_id}",
        json={"platform_content": platform_content_1},
        timeout=30
    )
    
    # Second update (should preserve previous data if not overwritten)
    platform_content_2 = [
        {"platform": "tiktok", "title": "Second Title", "description": "Second Desc"},
        {"platform": "instagram", "title": "IG Title", "description": "IG Desc"}
    ]
    
    requests.put(
        f"{BASE_URL}/api/media-db/analysis/{media_id}",
        json={"platform_content": platform_content_2},
        timeout=30
    )
    
    # Verify final state
    detail_response = requests.get(f"{BASE_URL}/api/media-db/detail/{media_id}", timeout=30)
    detail_data = detail_response.json()
    saved_content = detail_data.get("platform_content")
    
    assert saved_content is not None
    assert len(saved_content) == 2
    assert saved_content[0]["title"] == "Second Title"  # Should be updated
    assert saved_content[1]["platform"] == "instagram"  # Should have both platforms
    
    print(f"✅ platform_content persists correctly across updates")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

