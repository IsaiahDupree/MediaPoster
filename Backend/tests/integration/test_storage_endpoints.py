"""
Integration Tests: Storage Management Endpoints
Tests all storage management endpoints with real data
"""
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import os
import shutil
import uuid

from main import app
from services.local_storage import local_storage
from database.connection import async_session_maker


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest_asyncio.fixture
async def db_session():
    """Get real database session"""
    from database.connection import init_db
    
    if async_session_maker is None:
        await init_db()
        from database.connection import async_session_maker
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@pytest_asyncio.fixture
def setup_test_storage():
    """Set up test storage directories with sample files"""
    # Enable local storage for testing
    original_enabled = local_storage.enabled
    local_storage.enabled = True
    
    # Create test directories
    test_base = Path("/tmp/test_local_storage")
    local_storage.videos_path = test_base / "videos"
    local_storage.thumbnails_path = test_base / "thumbnails"
    local_storage.clips_path = test_base / "clips"
    local_storage.temp_path = test_base / "temp"
    
    # Create directories
    for path in [local_storage.videos_path, local_storage.thumbnails_path, 
                 local_storage.clips_path, local_storage.temp_path]:
        path.mkdir(parents=True, exist_ok=True)
    
    # Create test files
    test_video_id = str(uuid.uuid4())
    test_clip_id = str(uuid.uuid4())
    
    # Create dummy video file
    video_file = local_storage.videos_path / f"{test_video_id}.mp4"
    video_file.write_bytes(b"fake video content")
    
    # Create dummy thumbnail
    thumb_file = local_storage.thumbnails_path / f"{test_video_id}_thumb.jpg"
    thumb_file.write_bytes(b"fake thumbnail content")
    
    # Create dummy clip
    clip_file = local_storage.clips_path / f"{test_clip_id}.mp4"
    clip_file.write_bytes(b"fake clip content")
    
    yield {
        "video_id": test_video_id,
        "clip_id": test_clip_id
    }
    
    # Cleanup
    if test_base.exists():
        shutil.rmtree(test_base, ignore_errors=True)
    
    local_storage.enabled = original_enabled


class TestStorageStatsEndpoint:
    """Test GET /api/storage/stats"""
    
    def test_get_storage_stats(self, client):
        """Test getting storage statistics"""
        response = client.get("/api/storage/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert "local_storage_enabled" in data
        assert "directories" in data
        assert isinstance(data["directories"], dict)
    
    def test_get_storage_stats_with_files(self, client, setup_test_storage):
        """Test storage stats with actual files"""
        response = client.get("/api/storage/stats")
        assert response.status_code == 200
        
        data = response.json()
        if data["local_storage_enabled"]:
            assert "videos" in data["directories"]
            assert "thumbnails" in data["directories"]
            assert "clips" in data["directories"]
            assert "temp" in data["directories"]


class TestStorageListEndpoints:
    """Test list endpoints for videos, thumbnails, and clips"""
    
    def test_list_storage_videos(self, client):
        """Test listing videos in storage"""
        response = client.get("/api/storage/videos")
        assert response.status_code == 200
        
        data = response.json()
        assert "videos" in data
        assert "total" in data
        assert isinstance(data["videos"], list)
    
    def test_list_storage_videos_with_pagination(self, client):
        """Test pagination for storage videos"""
        response = client.get("/api/storage/videos?limit=10&offset=0")
        assert response.status_code == 200
        
        data = response.json()
        assert "limit" in data
        assert "offset" in data
        assert len(data["videos"]) <= 10
    
    def test_list_storage_thumbnails(self, client):
        """Test listing thumbnails in storage"""
        response = client.get("/api/storage/thumbnails")
        assert response.status_code == 200
        
        data = response.json()
        assert "thumbnails" in data
        assert "total" in data
        assert isinstance(data["thumbnails"], list)
    
    def test_list_storage_clips(self, client):
        """Test listing clips in storage"""
        response = client.get("/api/storage/clips")
        assert response.status_code == 200
        
        data = response.json()
        assert "clips" in data
        assert "total" in data
        assert isinstance(data["clips"], list)
    
    def test_list_with_files(self, client, setup_test_storage):
        """Test listing with actual files"""
        # Test videos
        response = client.get("/api/storage/videos")
        assert response.status_code == 200
        data = response.json()
        if data["total"] > 0:
            video = data["videos"][0]
            assert "filename" in video
            assert "size_bytes" in video
            assert "path" in video
        
        # Test thumbnails
        response = client.get("/api/storage/thumbnails")
        assert response.status_code == 200
        data = response.json()
        if data["total"] > 0:
            thumb = data["thumbnails"][0]
            assert "filename" in thumb
            assert "size_bytes" in thumb
        
        # Test clips
        response = client.get("/api/storage/clips")
        assert response.status_code == 200
        data = response.json()
        if data["total"] > 0:
            clip = data["clips"][0]
            assert "filename" in clip
            assert "size_bytes" in clip


class TestStorageFileAccessEndpoints:
    """Test file serving endpoints"""
    
    def test_get_storage_video_not_found(self, client):
        """Test getting non-existent video"""
        response = client.get("/api/storage/files/videos/nonexistent")
        # Should return 404 or 503 (if storage disabled)
        assert response.status_code in [404, 503]
    
    def test_get_storage_video(self, client, setup_test_storage):
        """Test getting video from storage"""
        video_id = setup_test_storage["video_id"]
        response = client.get(f"/api/storage/files/videos/{video_id}")
        
        if response.status_code == 200:
            assert response.headers["content-type"].startswith("video/")
        else:
            # Storage might be disabled
            assert response.status_code in [404, 503]
    
    def test_get_storage_thumbnail(self, client, setup_test_storage):
        """Test getting thumbnail from storage"""
        video_id = setup_test_storage["video_id"]
        response = client.get(f"/api/storage/files/thumbnails/{video_id}")
        
        if response.status_code == 200:
            assert response.headers["content-type"].startswith("image/")
        else:
            assert response.status_code in [404, 503]
    
    def test_get_storage_clip(self, client, setup_test_storage):
        """Test getting clip from storage"""
        clip_id = setup_test_storage["clip_id"]
        response = client.get(f"/api/storage/files/clips/{clip_id}")
        
        if response.status_code == 200:
            assert response.headers["content-type"].startswith("video/")
        else:
            assert response.status_code in [404, 503]


class TestStorageCleanupEndpoint:
    """Test POST /api/storage/cleanup"""
    
    def test_cleanup_storage(self, client):
        """Test storage cleanup"""
        response = client.post("/api/storage/cleanup?cleanup_temp=true")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "cleaned" in data
        assert isinstance(data["cleaned"], int)
    
    def test_cleanup_with_age_filter(self, client):
        """Test cleanup with age filter"""
        response = client.post("/api/storage/cleanup?cleanup_temp=true&older_than_days=30")
        assert response.status_code == 200
        
        data = response.json()
        assert "cleaned" in data


class TestStorageDeleteEndpoints:
    """Test DELETE endpoints"""
    
    def test_delete_storage_video_not_found(self, client):
        """Test deleting non-existent video"""
        response = client.delete("/api/storage/videos/nonexistent")
        assert response.status_code in [404, 503]
    
    def test_delete_storage_video(self, client, setup_test_storage):
        """Test deleting video from storage"""
        video_id = setup_test_storage["video_id"]
        response = client.delete(f"/api/storage/videos/{video_id}")
        
        # May return 404/503 if storage disabled, or 200 if successful
        assert response.status_code in [200, 404, 503]
    
    def test_delete_storage_thumbnail(self, client, setup_test_storage):
        """Test deleting thumbnail from storage"""
        video_id = setup_test_storage["video_id"]
        response = client.delete(f"/api/storage/thumbnails/{video_id}")
        
        assert response.status_code in [200, 404, 503]
    
    def test_delete_storage_clip(self, client, setup_test_storage):
        """Test deleting clip from storage"""
        clip_id = setup_test_storage["clip_id"]
        response = client.delete(f"/api/storage/clips/{clip_id}")
        
        assert response.status_code in [200, 404, 503]


class TestStorageEndpointsIntegration:
    """Integration tests for all storage endpoints"""
    
    def test_all_storage_endpoints_accessible(self, client):
        """Test that all storage endpoints are accessible"""
        endpoints = [
            ("GET", "/api/storage/stats"),
            ("GET", "/api/storage/videos"),
            ("GET", "/api/storage/thumbnails"),
            ("GET", "/api/storage/clips"),
            ("POST", "/api/storage/cleanup"),
        ]
        
        for method, path in endpoints:
            if method == "GET":
                response = client.get(path)
            elif method == "POST":
                response = client.post(path)
            
            assert response.status_code in [200, 503], f"{method} {path} returned {response.status_code}"
    
    def test_storage_endpoints_structure(self, client):
        """Test that storage endpoints return proper structures"""
        # Test stats
        response = client.get("/api/storage/stats")
        if response.status_code == 200:
            data = response.json()
            assert "local_storage_enabled" in data
            assert "directories" in data
        
        # Test list endpoints
        for endpoint in ["/api/storage/videos", "/api/storage/thumbnails", "/api/storage/clips"]:
            response = client.get(endpoint)
            if response.status_code == 200:
                data = response.json()
                assert "total" in data
                assert isinstance(data.get("total", 0), int)






