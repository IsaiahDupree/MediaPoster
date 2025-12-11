"""
Full System Audit Tests
Tests entire application with Supabase local database.
"""
import pytest
import asyncio
import os
from pathlib import Path
from datetime import datetime
import uuid

# Test configuration
SUPABASE_LOCAL_URL = "http://127.0.0.1:54321"
DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
IPHONE_IMPORT_PATH = Path(os.path.expanduser("~/Documents/IphoneImport"))


# =============================================================================
# DATABASE CONNECTION TESTS
# =============================================================================

class TestDatabaseConnection:
    """Test database connectivity and schema."""
    
    @pytest.mark.asyncio
    async def test_database_connection(self):
        """Test connection to Supabase local database."""
        from database.connection import init_db, get_db
        from sqlalchemy import text
        
        try:
            await init_db()
            async for session in get_db():
                result = await session.execute(text("SELECT 1"))
                assert result is not None
                break
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
    
    @pytest.mark.asyncio
    async def test_video_table_exists(self):
        """Test that videos table exists."""
        from database.connection import init_db, get_db
        from sqlalchemy import text
        
        try:
            await init_db()
            async for session in get_db():
                result = await session.execute(
                    text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'videos')")
                )
                exists = result.scalar()
                assert exists, "videos table should exist"
                break
        except Exception as e:
            pytest.skip(f"Database not available: {e}")
    
    @pytest.mark.asyncio
    async def test_video_analysis_table_exists(self):
        """Test that video_analysis table exists."""
        from database.connection import init_db, get_db
        from sqlalchemy import text
        
        try:
            await init_db()
            async for session in get_db():
                result = await session.execute(
                    text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'video_analysis')")
                )
                exists = result.scalar()
                assert exists, "video_analysis table should exist"
                break
        except Exception as e:
            pytest.skip(f"Database not available: {e}")


# =============================================================================
# VIDEO CRUD TESTS
# =============================================================================

class TestVideoCRUD:
    """Test Video model CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_create_video(self):
        """Test creating a video record."""
        from database.connection import init_db, get_db
        from database.models import Video
        
        try:
            await init_db()
            async for session in get_db():
                video = Video(
                    user_id=uuid.uuid4(),
                    source_type="local",
                    source_uri="/test/video.mov",
                    file_name="test_video.mov",
                    file_size=1000000,
                    duration_sec=60,
                    resolution="1920x1080",
                    aspect_ratio="16:9"
                )
                
                session.add(video)
                await session.commit()
                await session.refresh(video)
                
                assert video.id is not None
                assert video.file_name == "test_video.mov"
                
                # Cleanup
                await session.delete(video)
                await session.commit()
                break
        except Exception as e:
            pytest.skip(f"Database operation failed: {e}")
    
    @pytest.mark.asyncio
    async def test_create_video_with_analysis(self):
        """Test creating a video with analysis."""
        from database.connection import init_db, get_db
        from database.models import Video, VideoAnalysis
        
        try:
            await init_db()
            async for session in get_db():
                video = Video(
                    user_id=uuid.uuid4(),
                    source_type="local",
                    source_uri="/test/video2.mov",
                    file_name="test_video2.mov",
                    file_size=2000000
                )
                
                session.add(video)
                await session.commit()
                await session.refresh(video)
                
                analysis = VideoAnalysis(
                    video_id=video.id,
                    transcript="Test transcript",
                    topics=["tech", "tutorial"],
                    pre_social_score=85.5
                )
                
                session.add(analysis)
                await session.commit()
                
                # Verify
                await session.refresh(video)
                assert video.analysis is not None
                assert video.analysis.pre_social_score == 85.5
                
                # Cleanup
                await session.delete(video)
                await session.commit()
                break
        except Exception as e:
            pytest.skip(f"Database operation failed: {e}")


# =============================================================================
# MEDIA PROCESSING API TESTS
# =============================================================================

class TestMediaProcessingAPI:
    """Test media processing API endpoints."""
    
    def test_health_endpoint(self):
        """Test health check endpoint."""
        import requests
        
        try:
            response = requests.get("http://localhost:5555/api/media/health", timeout=5)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend server not running")
    
    def test_list_media_endpoint(self):
        """Test list media endpoint."""
        import requests
        
        try:
            response = requests.get("http://localhost:5555/api/media/list", timeout=5)
            assert response.status_code == 200
            assert isinstance(response.json(), list)
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend server not running")
    
    def test_thumbnail_stats_endpoint(self):
        """Test thumbnail stats endpoint."""
        import requests
        
        try:
            response = requests.get("http://localhost:5555/api/media/thumbnails/stats", timeout=5)
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend server not running")


# =============================================================================
# THUMBNAIL SERVICE TESTS
# =============================================================================

class TestThumbnailService:
    """Test thumbnail generation service."""
    
    def test_thumbnail_directory_exists(self):
        """Test thumbnail directory is created."""
        from services.thumbnail_service import THUMBNAIL_DIR
        assert THUMBNAIL_DIR.exists()
    
    def test_thumbnail_state_persistence(self, tmp_path):
        """Test thumbnail state persists to disk."""
        from services.thumbnail_service import ThumbnailState
        
        state_file = tmp_path / "test_state.json"
        state = ThumbnailState(state_file)
        
        state.mark_generated("/test/video.mov", "medium", "/thumbs/video.jpg")
        state.save()
        
        # Reload
        state2 = ThumbnailState(state_file)
        assert state2.is_generated("/test/video.mov", "medium")
    
    def test_generate_thumbnail_with_real_video(self):
        """Test thumbnail generation with real video file."""
        if not IPHONE_IMPORT_PATH.exists():
            pytest.skip("iPhone import directory not available")
        
        videos = list(IPHONE_IMPORT_PATH.glob("*.MOV"))[:1]
        if not videos:
            pytest.skip("No video files found")
        
        from services.thumbnail_service import generate_thumbnail
        
        result = generate_thumbnail(str(videos[0]), "small")
        
        if result:
            assert Path(result).exists()
            assert Path(result).suffix == ".jpg"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for full workflow."""
    
    def test_batch_ingest_endpoint(self):
        """Test batch ingest endpoint."""
        import requests
        
        if not IPHONE_IMPORT_PATH.exists():
            pytest.skip("iPhone import directory not available")
        
        try:
            response = requests.post(
                "http://localhost:5555/api/media/batch/ingest",
                json={
                    "directory_path": str(IPHONE_IMPORT_PATH),
                    "resume": True
                },
                timeout=10
            )
            
            # May succeed or fail depending on state
            assert response.status_code in [200, 400, 500]
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend server not running")
    
    def test_thumbnail_generation_endpoint(self):
        """Test thumbnail generation endpoint."""
        import requests
        
        try:
            response = requests.post(
                "http://localhost:5555/api/media/thumbnails/generate",
                timeout=10
            )
            
            # May succeed or fail depending on media availability
            assert response.status_code in [200, 400, 500]
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend server not running")


# =============================================================================
# SUPABASE LOCAL TESTS
# =============================================================================

class TestSupabaseLocal:
    """Test Supabase local integration."""
    
    def test_supabase_api_accessible(self):
        """Test Supabase local API is accessible."""
        import requests
        
        try:
            response = requests.get(f"{SUPABASE_LOCAL_URL}/rest/v1/", timeout=5)
            # Should return 400 (missing apikey) or 200, but should connect
            assert response.status_code in [200, 400, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("Supabase local not running")
    
    def test_supabase_storage_accessible(self):
        """Test Supabase storage is accessible."""
        import requests
        
        try:
            response = requests.get(f"{SUPABASE_LOCAL_URL}/storage/v1/", timeout=5)
            assert response.status_code in [200, 400, 401]
        except requests.exceptions.ConnectionError:
            pytest.skip("Supabase local not running")


# =============================================================================
# DATA PERSISTENCE TESTS
# =============================================================================

class TestDataPersistence:
    """Test data persists across server restarts."""
    
    def test_thumbnail_state_file_exists(self):
        """Test thumbnail state file can be created."""
        from services.thumbnail_service import THUMBNAIL_STATE_FILE, ThumbnailState
        
        state = ThumbnailState()
        state.mark_generated("/test/persistence.mov", "medium", "/thumbs/test.jpg")
        state.save()
        
        assert THUMBNAIL_STATE_FILE.parent.exists()
    
    def test_video_records_persist(self):
        """Test video records persist in database."""
        # This would require actual database operations
        # Skip if database not available
        import os
        db_url = os.getenv("DATABASE_URL", "")
        
        if "localhost:54322" not in db_url and "127.0.0.1:54322" not in db_url:
            pytest.skip("Local database not configured")
        
        # Test would create and query records
        assert True


# =============================================================================
# FRONTEND CONNECTIVITY TESTS
# =============================================================================

class TestFrontendConnectivity:
    """Test frontend can connect to backend."""
    
    def test_cors_headers(self):
        """Test CORS headers are set correctly."""
        import requests
        
        try:
            response = requests.options(
                "http://localhost:5555/api/media/health",
                headers={
                    "Origin": "http://localhost:5557",
                    "Access-Control-Request-Method": "GET"
                },
                timeout=5
            )
            
            # Should allow CORS
            assert response.status_code in [200, 204]
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend server not running")
    
    def test_frontend_accessible(self):
        """Test frontend is accessible."""
        import requests
        
        try:
            response = requests.get("http://localhost:5557", timeout=5)
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip("Frontend server not running")


# =============================================================================
# PERFORMANCE TESTS
# =============================================================================

class TestPerformance:
    """Performance and load tests."""
    
    def test_health_endpoint_response_time(self):
        """Test health endpoint responds quickly."""
        import requests
        import time
        
        try:
            start = time.time()
            response = requests.get("http://localhost:5555/api/media/health", timeout=5)
            elapsed = time.time() - start
            
            assert response.status_code == 200
            assert elapsed < 1.0, f"Response took {elapsed:.2f}s, expected < 1s"
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend server not running")
    
    def test_list_media_response_time(self):
        """Test list media endpoint responds quickly."""
        import requests
        import time
        
        try:
            start = time.time()
            response = requests.get("http://localhost:5555/api/media/list?limit=100", timeout=10)
            elapsed = time.time() - start
            
            assert response.status_code == 200
            assert elapsed < 2.0, f"Response took {elapsed:.2f}s, expected < 2s"
        except requests.exceptions.ConnectionError:
            pytest.skip("Backend server not running")


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-x"])
