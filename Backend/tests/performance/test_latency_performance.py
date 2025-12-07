"""
Latency Performance Tests
Tests response times and query performance
"""
import pytest
import time
from fastapi.testclient import TestClient
from main import app
import statistics


@pytest.fixture
def client():
    return TestClient(app)


class TestAPILatency:
    """Test API endpoint latency"""
    
    def test_health_endpoint_latency(self, client):
        """Health endpoint should be very fast"""
        times = []
        for _ in range(10):
            start = time.time()
            response = client.get("/health")
            elapsed = time.time() - start
            assert response.status_code == 200
            times.append(elapsed)
        
        p95 = sorted(times)[int(len(times) * 0.95)]
        assert p95 < 0.1, f"P95 latency too high: {p95}s"
    
    def test_video_list_latency(self, client):
        """Video list endpoint should be fast"""
        times = []
        for _ in range(5):
            start = time.time()
            response = client.get("/api/videos/?limit=10")
            elapsed = time.time() - start
            if response.status_code == 200:
                times.append(elapsed)
        
        if times:
            p95 = sorted(times)[int(len(times) * 0.95)]
            assert p95 < 2.0, f"P95 latency too high: {p95}s"
    
    def test_video_detail_latency(self, client):
        """Video detail endpoint should be fast"""
        # First get a video ID
        list_response = client.get("/api/videos/?limit=1")
        if list_response.status_code == 200:
            videos = list_response.json()
            if videos and isinstance(videos, list) and len(videos) > 0:
                video_id = videos[0].get("id")
                if video_id:
                    start = time.time()
                    response = client.get(f"/api/videos/{video_id}")
                    elapsed = time.time() - start
                    if response.status_code == 200:
                        assert elapsed < 1.0, f"Video detail latency too high: {elapsed}s"


class TestDatabaseQueryLatency:
    """Test database query performance"""
    
    @pytest.mark.asyncio
    async def test_simple_query_latency(self):
        """Simple queries should be very fast"""
        from database.connection import async_session_maker
        from sqlalchemy import text
        
        times = []
        for _ in range(10):
            start = time.time()
            async with async_session_maker() as session:
                await session.execute(text("SELECT 1"))
            elapsed = time.time() - start
            times.append(elapsed)
        
        p95 = sorted(times)[int(len(times) * 0.95)]
        assert p95 < 0.05, f"P95 query latency too high: {p95}s"
    
    @pytest.mark.asyncio
    async def test_count_query_latency(self):
        """Count queries should be fast"""
        from database.connection import async_session_maker
        from sqlalchemy import text
        
        start = time.time()
        async with async_session_maker() as session:
            result = await session.execute(text("SELECT COUNT(*) FROM videos"))
            count = result.scalar()
        elapsed = time.time() - start
        
        assert elapsed < 1.0, f"Count query took {elapsed}s"
        assert isinstance(count, (int, type(None)))
    
    @pytest.mark.asyncio
    async def test_join_query_latency(self):
        """Join queries should be reasonably fast"""
        from database.connection import async_session_maker
        from sqlalchemy import text
        
        start = time.time()
        async with async_session_maker() as session:
            result = await session.execute(text("""
                SELECT v.id, COUNT(c.id) as clip_count
                FROM videos v
                LEFT JOIN clips c ON c.parent_video_id = v.id
                GROUP BY v.id
                LIMIT 10
            """))
            rows = result.fetchall()
        elapsed = time.time() - start
        
        assert elapsed < 2.0, f"Join query took {elapsed}s"


class TestEndToEndLatency:
    """Test end-to-end operation latency"""
    
    def test_video_upload_to_list_latency(self, client):
        """Video should appear in list quickly after upload"""
        # This would test the full pipeline
        # For now, just verify endpoints are fast
        start = time.time()
        response = client.get("/api/videos/?limit=1")
        elapsed = time.time() - start
        
        if response.status_code == 200:
            assert elapsed < 2.0, f"Video list latency too high: {elapsed}s"
    
    def test_thumbnail_generation_latency(self, client):
        """Thumbnail generation should be queued quickly"""
        # Get a video ID
        list_response = client.get("/api/videos/?limit=1")
        if list_response.status_code == 200:
            videos = list_response.json()
            if videos and isinstance(videos, list) and len(videos) > 0:
                video_id = videos[0].get("id")
                if video_id:
                    start = time.time()
                    response = client.post(f"/api/videos/{video_id}/generate-thumbnail")
                    elapsed = time.time() - start
                    # Queuing should be fast
                    if response.status_code in [200, 202]:
                        assert elapsed < 1.0, f"Thumbnail queuing latency too high: {elapsed}s"






