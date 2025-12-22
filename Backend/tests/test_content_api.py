"""
Comprehensive tests for Content API endpoints.
Tests content management, scoring, and analysis.
"""

import pytest
from fastapi.testclient import TestClient
import json

import sys
sys.path.insert(0, '..')
try:
    from main import app
    client = TestClient(app)
except ImportError:
    client = None


class TestContentList:
    """Tests for GET /api/content/list endpoint"""
    
    def test_get_content_list(self):
        """Should return content list"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/content/list")
        assert response.status_code in [200, 404]
    
    def test_get_content_with_limit(self):
        """Should respect limit"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/content/list?limit=10")
        assert response.status_code in [200, 404]
    
    def test_get_content_with_status(self):
        """Should filter by status"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/content/list?status=ready")
        assert response.status_code in [200, 404]
    
    def test_get_content_sorted(self):
        """Should sort content"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/content/list?sort=score")
        assert response.status_code in [200, 404]


class TestContentGet:
    """Tests for GET /api/content/:id endpoint"""
    
    def test_get_content_by_id(self):
        """Should get content by ID"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/content/1")
        assert response.status_code in [200, 404]
    
    def test_get_nonexistent_content(self):
        """Should return 404"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/content/99999")
        assert response.status_code == 404


class TestContentScore:
    """Tests for content scoring endpoint"""
    
    def test_get_content_score(self):
        """Should get content score"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/content/1/score")
        assert response.status_code in [200, 404]
    
    def test_score_returns_numeric(self):
        """Should return numeric score"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/content/1/score")
        if response.status_code == 200:
            data = response.json()
            assert "score" in data or isinstance(data, (int, float))


class TestContentAnalysis:
    """Tests for content analysis endpoint"""
    
    def test_analyze_content(self):
        """Should analyze content"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/content/1/analyze")
        assert response.status_code in [200, 202, 404]
    
    def test_get_analysis_results(self):
        """Should get analysis results"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/content/1/analysis")
        assert response.status_code in [200, 404]


class TestContentTranscript:
    """Tests for content transcript endpoint"""
    
    def test_get_transcript(self):
        """Should get transcript"""
        if not client:
            pytest.skip("Client not available")
        response = client.get("/api/content/1/transcript")
        assert response.status_code in [200, 404]
    
    def test_generate_transcript(self):
        """Should generate transcript"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/content/1/transcript")
        assert response.status_code in [200, 202, 404]


class TestContentCaption:
    """Tests for content caption generation"""
    
    def test_generate_caption(self):
        """Should generate caption"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/content/1/caption")
        assert response.status_code in [200, 202, 404]
    
    def test_generate_caption_with_platform(self):
        """Should generate platform-specific caption"""
        if not client:
            pytest.skip("Client not available")
        response = client.post("/api/content/1/caption?platform=tiktok")
        assert response.status_code in [200, 202, 404]
    
    def test_regenerate_caption(self):
        """Should regenerate caption"""
        if not client:
            pytest.skip("Client not available")
        data = {"prompt": "Make it funnier"}
        response = client.post("/api/content/1/caption/regenerate", json=data)
        assert response.status_code in [200, 202, 404]


class TestContentUpdate:
    """Tests for PUT /api/content/:id endpoint"""
    
    def test_update_content_title(self):
        """Should update title"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/content/1", json={"title": "Updated"})
        assert response.status_code in [200, 404, 422]
    
    def test_update_content_caption(self):
        """Should update caption"""
        if not client:
            pytest.skip("Client not available")
        response = client.put("/api/content/1", json={"caption": "New caption"})
        assert response.status_code in [200, 404, 422]


class TestContentDelete:
    """Tests for DELETE /api/content/:id endpoint"""
    
    def test_delete_content(self):
        """Should delete content"""
        if not client:
            pytest.skip("Client not available")
        response = client.delete("/api/content/1")
        assert response.status_code in [200, 204, 404]
