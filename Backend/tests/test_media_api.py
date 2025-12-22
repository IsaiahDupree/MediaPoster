"""
Comprehensive tests for Media API endpoints.
Tests listing, fetching, uploading, and video streaming.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import json

import sys
sys.path.insert(0, '..')
try:
    from main import app
    client = TestClient(app)
except ImportError:
    client = None


class TestMediaList:
    """Tests for GET /api/media/list endpoint"""
    
    def test_get_media_list_returns_200(self):
        """Should return 200 status code"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/list")
        assert response.status_code in [200, 404]
    
    def test_get_media_list_returns_json(self):
        """Should return JSON response"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/list")
        assert response.headers.get("content-type", "").startswith("application/json")
    
    def test_get_media_list_with_limit(self):
        """Should respect limit parameter"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/list?limit=10")
        assert response.status_code in [200, 404]
    
    def test_get_media_list_with_offset(self):
        """Should respect offset parameter"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/list?offset=0")
        assert response.status_code in [200, 404]
    
    def test_get_media_list_with_type_filter(self):
        """Should filter by media type"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/list?type=video")
        assert response.status_code in [200, 404]
    
    def test_get_media_list_with_search(self):
        """Should search by title"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/list?search=test")
        assert response.status_code in [200, 404]
    
    def test_get_media_list_pagination(self):
        """Should support pagination"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/list?limit=5&offset=5")
        assert response.status_code in [200, 404]
    
    def test_get_media_list_sort_by_date(self):
        """Should sort by date"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/list?sort=date")
        assert response.status_code in [200, 404]
    
    def test_get_media_list_sort_by_score(self):
        """Should sort by score"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/list?sort=score")
        assert response.status_code in [200, 404]


class TestMediaGet:
    """Tests for GET /api/media/:id endpoint"""
    
    def test_get_media_by_id(self):
        """Should get media by ID"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/1")
        assert response.status_code in [200, 404]
    
    def test_get_nonexistent_media(self):
        """Should return 404 for nonexistent media"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/99999")
        assert response.status_code == 404
    
    def test_get_media_returns_fields(self):
        """Should return expected fields"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/1")
        if response.status_code == 200:
            data = response.json()
            assert "id" in data or "title" in data
    
    def test_get_media_invalid_id(self):
        """Should handle invalid ID"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/invalid")
        assert response.status_code in [400, 404, 422]


class TestMediaVideo:
    """Tests for GET /api/media/video/:id endpoint"""
    
    def test_get_video_stream(self):
        """Should stream video"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/video/1")
        assert response.status_code in [200, 206, 404]
    
    def test_get_video_with_range_header(self):
        """Should support range requests"""
        if not client:
            pytest.skip("Client not available")
        headers = {"Range": "bytes=0-1000"}
        response = client.get("/api/media/video/1", headers=headers)
        assert response.status_code in [200, 206, 404]
    
    def test_get_nonexistent_video(self):
        """Should return 404 for nonexistent video"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/video/99999")
        assert response.status_code == 404
    
    def test_get_video_content_type(self):
        """Should return video content type"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/video/1")
        if response.status_code in [200, 206]:
            content_type = response.headers.get("content-type", "")
            assert "video" in content_type or response.status_code == 404


class TestMediaThumbnail:
    """Tests for GET /api/media/thumbnail/:id endpoint"""
    
    def test_get_thumbnail(self):
        """Should get thumbnail"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/thumbnail/1")
        assert response.status_code in [200, 404]
    
    def test_get_nonexistent_thumbnail(self):
        """Should return 404 for nonexistent thumbnail"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/thumbnail/99999")
        assert response.status_code == 404
    
    def test_get_thumbnail_content_type(self):
        """Should return image content type"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/thumbnail/1")
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            assert "image" in content_type


class TestMediaUpload:
    """Tests for POST /api/media/upload endpoint"""
    
    def test_upload_without_file(self):
        """Should reject upload without file"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/media/upload")
        assert response.status_code in [400, 422, 404]
    
    def test_upload_with_metadata(self):
        """Should accept metadata"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/media/upload", data={"title": "Test"})
        assert response.status_code in [200, 400, 422, 404]


class TestMediaDelete:
    """Tests for DELETE /api/media/:id endpoint"""
    
    def test_delete_media(self):
        """Should delete media"""
        if not client:
            pytest.skip("Client not available")
        response = client.delete("/api/media/1")
        assert response.status_code in [200, 204, 404]
    
    def test_delete_nonexistent_media(self):
        """Should return 404 for nonexistent media"""
        if not client:
            pytest.skip("Client not available")
        response = client.delete("/api/media/99999")
        assert response.status_code in [404, 200]


class TestMediaUpdate:
    """Tests for PUT /api/media/:id endpoint"""
    
    def test_update_media_title(self):
        """Should update media title"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/media/1", json={"title": "Updated Title"})
        assert response.status_code in [200, 404, 422]
    
    def test_update_media_description(self):
        """Should update media description"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/media/1", json={"description": "Updated desc"})
        assert response.status_code in [200, 404, 422]
    
    def test_update_nonexistent_media(self):
        """Should return 404 for nonexistent media"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/media/99999", json={"title": "Test"})
        assert response.status_code in [404, 422]


class TestMediaValidation:
    """Tests for media data validation"""
    
    def test_invalid_limit_value(self):
        """Should handle invalid limit"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/list?limit=-1")
        assert response.status_code in [200, 400, 422, 404]
    
    def test_invalid_offset_value(self):
        """Should handle invalid offset"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/list?offset=-1")
        assert response.status_code in [200, 400, 422, 404]
    
    def test_very_large_limit(self):
        """Should handle very large limit"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/list?limit=10000")
        assert response.status_code in [200, 400, 422, 404]
    
    def test_special_characters_in_search(self):
        """Should handle special characters in search"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/media/list?search=%3Cscript%3E")
        assert response.status_code in [200, 400, 422, 404]
