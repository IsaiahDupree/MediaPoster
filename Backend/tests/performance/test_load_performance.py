"""
Load and Stress Performance Tests
Tests system behavior under various load conditions
"""
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from main import app
import statistics


@pytest.fixture
def client():
    return TestClient(app)


class TestLoadPerformance:
    """Test system performance under load"""
    
    def test_concurrent_health_checks(self, client):
        """System should handle concurrent health checks"""
        def make_request():
            return client.get("/health")
        
        # Make 50 concurrent requests
        with ThreadPoolExecutor(max_workers=50) as executor:
            start = time.time()
            futures = [executor.submit(make_request) for _ in range(50)]
            results = [f.result() for f in futures]
            elapsed = time.time() - start
        
        # All should succeed
        assert all(r.status_code == 200 for r in results)
        # Should complete in reasonable time
        assert elapsed < 10.0, f"50 concurrent requests took {elapsed}s"
    
    def test_concurrent_video_list_requests(self, client):
        """Video list endpoint should handle concurrent requests"""
        def make_request():
            return client.get("/api/videos/?limit=10")
        
        # Make 20 concurrent requests
        with ThreadPoolExecutor(max_workers=20) as executor:
            start = time.time()
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in futures]
            elapsed = time.time() - start
        
        # Most should succeed (some may fail under load, that's ok)
        success_rate = sum(1 for r in results if r.status_code == 200) / len(results)
        assert success_rate >= 0.8, f"Success rate too low: {success_rate}"
        assert elapsed < 30.0, f"20 concurrent requests took {elapsed}s"
    
    def test_response_time_consistency(self, client):
        """Response times should be consistent under load"""
        response_times = []
        
        for _ in range(20):
            start = time.time()
            response = client.get("/health")
            elapsed = time.time() - start
            assert response.status_code == 200
            response_times.append(elapsed)
        
        # Calculate statistics
        mean_time = statistics.mean(response_times)
        std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0
        
        # Mean should be reasonable
        assert mean_time < 0.5, f"Mean response time too high: {mean_time}s"
        # Standard deviation should be low (consistent performance)
        assert std_dev < mean_time * 2, f"Response times too variable: std_dev={std_dev}"
    
    def test_database_connection_pooling(self):
        """Database should handle connection pooling efficiently"""
        import asyncio
        from database.connection import async_session_maker
        
        async def make_query():
            async with async_session_maker() as session:
                from sqlalchemy import text
                result = await session.execute(text("SELECT 1"))
                return result.scalar()
        
        # Make 30 concurrent database queries
        async def run_concurrent_queries():
            tasks = [make_query() for _ in range(30)]
            start = time.time()
            results = await asyncio.gather(*tasks)
            elapsed = time.time() - start
            return results, elapsed
        
        results, elapsed = asyncio.run(run_concurrent_queries())
        
        # All should succeed
        assert all(r == 1 for r in results)
        # Should complete efficiently with connection pooling
        assert elapsed < 5.0, f"30 concurrent DB queries took {elapsed}s"


class TestStressPerformance:
    """Test system behavior under stress"""
    
    def test_sustained_load(self, client):
        """System should handle sustained load"""
        duration = 10  # seconds
        requests_per_second = 5
        total_requests = duration * requests_per_second
        
        start = time.time()
        success_count = 0
        
        while time.time() - start < duration:
            response = client.get("/health")
            if response.status_code == 200:
                success_count += 1
            time.sleep(1.0 / requests_per_second)
        
        # Should maintain high success rate
        success_rate = success_count / total_requests
        assert success_rate >= 0.95, f"Success rate under sustained load: {success_rate}"
    
    def test_memory_usage_under_load(self, client):
        """System should not leak memory under load"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make many requests
        for _ in range(100):
            client.get("/health")
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (< 100MB for 100 requests)
        assert memory_increase < 100, f"Memory increased by {memory_increase}MB"


class TestScalabilityPerformance:
    """Test system scalability"""
    
    def test_large_result_set_handling(self, client):
        """System should handle large result sets efficiently"""
        # Request with large limit
        start = time.time()
        response = client.get("/api/videos/?limit=1000")
        elapsed = time.time() - start
        
        # Should either return results or reject with reasonable limit
        assert response.status_code in [200, 400, 422]
        if response.status_code == 200:
            # If it returns, should be paginated or limited
            data = response.json()
            if isinstance(data, list):
                # Should have reasonable limit
                assert len(data) <= 1000
            # Should complete in reasonable time
            assert elapsed < 10.0, f"Large result set query took {elapsed}s"
    
    def test_batch_operation_performance(self, client):
        """Batch operations should scale efficiently"""
        # Test batch thumbnail generation
        video_ids = [f"test-{i}" for i in range(50)]
        
        start = time.time()
        response = client.post(
            "/api/videos/generate-thumbnails-batch",
            json={"video_ids": video_ids, "max_videos": 50}
        )
        elapsed = time.time() - start
        
        # Should accept or reject quickly
        assert response.status_code in [200, 400, 422]
        # Response should be fast (queuing, not processing)
        assert elapsed < 2.0, f"Batch operation queuing took {elapsed}s"






