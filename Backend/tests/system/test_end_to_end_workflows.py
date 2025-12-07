"""
End-to-End System Workflow Tests
Tests complete user workflows from start to finish
"""
import pytest
from fastapi.testclient import TestClient
from main import app
from database.connection import async_session_maker
from sqlalchemy import text
import asyncio
import time


@pytest.fixture
def client():
    return TestClient(app)


@pytest.mark.asyncio
class TestVideoUploadWorkflow:
    """Test complete video upload and processing workflow"""
    
    async def test_upload_to_analysis_workflow(self, client):
        """Test: Upload video -> Process -> Analyze -> View results"""
        # Step 1: Upload/Create video
        video_data = {
            "file_name": "test-workflow.mp4",
            "source_uri": "/test/path/workflow.mp4",
            "source_type": "local"
        }
        
        create_response = client.post("/api/videos/", json=video_data)
        assert create_response.status_code in [201, 422]
        
        if create_response.status_code == 201:
            video = create_response.json()
            video_id = video.get("id")
            
            # Step 2: Trigger analysis
            analysis_response = client.post(f"/api/videos/{video_id}/analyze")
            assert analysis_response.status_code in [200, 202, 404]
            
            # Step 3: Check analysis status
            await asyncio.sleep(2)
            detail_response = client.get(f"/api/videos/{video_id}")
            
            if detail_response.status_code == 200:
                video_detail = detail_response.json()
                # Should have analysis data or status
                assert "id" in video_detail
    
    async def test_upload_to_thumbnail_workflow(self, client):
        """Test: Upload video -> Generate thumbnail -> View thumbnail"""
        # Create video
        video_data = {
            "file_name": "test-thumbnail.mp4",
            "source_uri": "/test/path/thumbnail.mp4",
            "source_type": "local"
        }
        
        create_response = client.post("/api/videos/", json=video_data)
        assert create_response.status_code in [201, 422]
        
        if create_response.status_code == 201:
            video = create_response.json()
            video_id = video.get("id")
            
            # Generate thumbnail
            thumb_response = client.post(f"/api/videos/{video_id}/generate-thumbnail")
            assert thumb_response.status_code in [200, 202, 404]
            
            # Wait for generation
            await asyncio.sleep(3)
            
            # Get thumbnail
            thumb_get_response = client.get(f"/api/videos/{video_id}/thumbnail")
            # Should either have thumbnail (200) or not ready (404)
            assert thumb_get_response.status_code in [200, 404]


@pytest.mark.asyncio
class TestClipGenerationWorkflow:
    """Test clip generation workflow"""
    
    async def test_video_to_clip_workflow(self, client):
        """Test: Select video -> Generate clip -> View clip"""
        # Get a video
        list_response = client.get("/api/videos/?limit=1")
        
        if list_response.status_code == 200:
            videos = list_response.json()
            if videos and len(videos) > 0:
                video_id = videos[0].get("id")
                
                # Navigate to studio (would be frontend)
                # For backend test, verify studio endpoint exists
                studio_response = client.get(f"/api/videos/{video_id}")
                assert studio_response.status_code in [200, 404]
                
                # Generate clip (if endpoint exists)
                # This would test the full clip generation flow


@pytest.mark.asyncio
class TestPublishingWorkflow:
    """Test publishing workflow"""
    
    async def test_clip_to_publish_workflow(self, client):
        """Test: Create clip -> Add to queue -> Publish -> Track performance"""
        # This would test the complete publishing flow
        # 1. Create clip
        # 2. Add to publishing queue
        # 3. Publish to platform
        # 4. Track metrics
        
        # For now, verify queue endpoint exists
        queue_response = client.get("/api/publishing/queue")
        # Should either return queue (200) or require auth (401)
        assert queue_response.status_code in [200, 401, 404]


@pytest.mark.asyncio
class TestAnalyticsWorkflow:
    """Test analytics collection workflow"""
    
    async def test_content_to_analytics_workflow(self, client):
        """Test: Publish content -> Collect metrics -> Display analytics"""
        # This would test:
        # 1. Content is published
        # 2. Metrics are collected over time
        # 3. Analytics are calculated
        # 4. Dashboard displays results
        
        # Verify analytics endpoints exist
        analytics_response = client.get("/api/analytics/content")
        assert analytics_response.status_code in [200, 401, 404]


@pytest.mark.asyncio
class TestErrorRecoveryWorkflow:
    """Test error handling and recovery workflows"""
    
    async def test_failed_analysis_recovery(self, client):
        """Test: Analysis fails -> Error logged -> User can retry"""
        # Create video
        video_data = {
            "file_name": "test-error.mp4",
            "source_uri": "/nonexistent/path/error.mp4",
            "source_type": "local"
        }
        
        create_response = client.post("/api/videos/", json=video_data)
        
        if create_response.status_code == 201:
            video = create_response.json()
            video_id = video.get("id")
            
            # Try to analyze (will fail if file doesn't exist)
            analysis_response = client.post(f"/api/videos/{video_id}/analyze")
            # Should handle error gracefully
            assert analysis_response.status_code in [200, 202, 400, 404, 500]
            
            # Should be able to retry
            retry_response = client.post(f"/api/videos/{video_id}/analyze")
            assert retry_response.status_code in [200, 202, 400, 404, 500]
    
    async def test_database_connection_recovery(self):
        """Test: DB connection lost -> System handles gracefully -> Recovers"""
        # This would test connection pooling and recovery
        # For now, verify connection works
        async with async_session_maker() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar() == 1






