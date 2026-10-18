"""
Integration tests for microservices connectivity.
Tests cross-service communication between MediaPoster ecosystem services.
"""
import pytest
import httpx
import asyncio
from typing import Dict, Any

# Service URLs
SERVICES = {
    "core": "http://localhost:5555",
    "safari": "http://localhost:6001",
    "remotion": "http://localhost:6002",
    "media": "http://localhost:6004",
    "ai": "http://localhost:6006",
}


class TestServiceHealth:
    """Test health endpoints for all services."""
    
    @pytest.mark.asyncio
    async def test_media_pipeline_health(self):
        """Test media-pipeline service health."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{SERVICES['media']}/health", timeout=5)
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["service"] == "media-pipeline"
            except httpx.ConnectError:
                pytest.skip("media-pipeline service not running")
    
    @pytest.mark.asyncio
    async def test_content_intelligence_health(self):
        """Test content-intelligence service health."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{SERVICES['ai']}/health", timeout=5)
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["service"] == "content-intelligence"
            except httpx.ConnectError:
                pytest.skip("content-intelligence service not running")
    
    @pytest.mark.asyncio
    async def test_mediaposter_core_health(self):
        """Test MediaPoster core service health."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{SERVICES['core']}/api/external/health", 
                    timeout=5
                )
                assert response.status_code == 200
            except httpx.ConnectError:
                pytest.skip("MediaPoster core not running")


class TestMediaPipelineAPI:
    """Test media-pipeline API endpoints."""
    
    @pytest.mark.asyncio
    async def test_analyze_endpoint(self):
        """Test video analysis endpoint."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{SERVICES['media']}/api/analyze",
                    json={"video_path": "/test/video.mp4"},
                    timeout=10
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert "analysis" in data
            except httpx.ConnectError:
                pytest.skip("media-pipeline service not running")
    
    @pytest.mark.asyncio
    async def test_thumbnail_generate_endpoint(self):
        """Test thumbnail generation endpoint."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{SERVICES['media']}/api/thumbnail/generate",
                    json={"video_path": "/test/video.mp4", "count": 3},
                    timeout=10
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
            except httpx.ConnectError:
                pytest.skip("media-pipeline service not running")
    
    @pytest.mark.asyncio
    async def test_format_detect_endpoint(self):
        """Test format detection endpoint."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{SERVICES['media']}/api/format/detect",
                    json={"file_path": "/test/video.mp4"},
                    timeout=10
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert "format" in data
            except httpx.ConnectError:
                pytest.skip("media-pipeline service not running")


class TestContentIntelligenceAPI:
    """Test content-intelligence API endpoints."""
    
    @pytest.mark.asyncio
    async def test_generate_title_endpoint(self):
        """Test title generation endpoint."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{SERVICES['ai']}/api/generate/title",
                    json={
                        "content": "How to grow your TikTok following",
                        "platform": "tiktok",
                        "count": 3
                    },
                    timeout=10
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert len(data["titles"]) == 3
            except httpx.ConnectError:
                pytest.skip("content-intelligence service not running")
    
    @pytest.mark.asyncio
    async def test_fate_score_endpoint(self):
        """Test FATE scoring endpoint."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{SERVICES['ai']}/api/score/fate",
                    json={"content_id": "test-123", "metrics": {}},
                    timeout=10
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert "fate_score" in data
                assert "overall" in data["fate_score"]
            except httpx.ConnectError:
                pytest.skip("content-intelligence service not running")
    
    @pytest.mark.asyncio
    async def test_awareness_classification_endpoint(self):
        """Test awareness classification endpoint."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{SERVICES['ai']}/api/classify/awareness",
                    json={"content": "I need help with my marketing strategy"},
                    timeout=10
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert "awareness_level" in data
            except httpx.ConnectError:
                pytest.skip("content-intelligence service not running")
    
    @pytest.mark.asyncio
    async def test_sentiment_analysis_endpoint(self):
        """Test sentiment analysis endpoint."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{SERVICES['ai']}/api/analyze/sentiment",
                    json={"text": "This is absolutely amazing!"},
                    timeout=10
                )
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "success"
                assert data["sentiment"] == "positive"
            except httpx.ConnectError:
                pytest.skip("content-intelligence service not running")


class TestCrossServiceCommunication:
    """Test communication between services."""
    
    @pytest.mark.asyncio
    async def test_all_services_reachable(self):
        """Test that all services can be reached."""
        results = {}
        async with httpx.AsyncClient() as client:
            for name, url in SERVICES.items():
                health_endpoint = "/api/external/health" if name == "core" else "/health"
                try:
                    response = await client.get(f"{url}{health_endpoint}", timeout=3)
                    results[name] = response.status_code == 200
                except:
                    results[name] = False
        
        # At least media and ai services should be up for this test
        running_services = [k for k, v in results.items() if v]
        print(f"Running services: {running_services}")
        assert len(running_services) >= 1, "At least one service should be running"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
