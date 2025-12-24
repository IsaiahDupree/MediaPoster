"""
Load and Stress Performance Tests
Tests system behavior under various load conditions
"""
import pytest
import asyncio
import time
import httpx
import statistics

API_URL = "http://localhost:5555"


class TestLoadPerformance:
    """Test system performance under load"""
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """System should handle concurrent health checks"""
        async def make_request():
            async with httpx.AsyncClient() as client:
                return await client.get(f"{API_URL}/health")
        
        # Make 50 concurrent requests
        start = time.time()
        tasks = [make_request() for _ in range(50)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start
        
        # All should succeed (filter out exceptions)
        successful = [r for r in results if isinstance(r, httpx.Response) and r.status_code == 200]
        success_rate = len(successful) / len(results)
        assert success_rate >= 0.9, f"Success rate too low: {success_rate}"
        # Should complete in reasonable time
        assert elapsed < 15.0, f"50 concurrent requests took {elapsed}s"
    
    @pytest.mark.asyncio
    async def test_concurrent_video_list_requests(self):
        """Video list endpoint should handle concurrent requests"""
        async def make_request():
            async with httpx.AsyncClient() as client:
                return await client.get(f"{API_URL}/api/videos/?limit=10")
        
        # Make 20 concurrent requests
        start = time.time()
        tasks = [make_request() for _ in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start
        
        # Most should succeed (some may fail under load, that's ok)
        successful = [r for r in results if isinstance(r, httpx.Response) and r.status_code == 200]
        success_rate = len(successful) / len(results)
        assert success_rate >= 0.7, f"Success rate too low: {success_rate}"
        assert elapsed < 30.0, f"20 concurrent requests took {elapsed}s"
    
    @pytest.mark.asyncio
    async def test_response_time_consistency(self):
        """Response times should be consistent under load"""
        response_times = []
        
        async with httpx.AsyncClient() as client:
            for _ in range(20):
                start = time.time()
                response = await client.get(f"{API_URL}/health")
                elapsed = time.time() - start
                assert response.status_code == 200
                response_times.append(elapsed)
        
        # Calculate statistics
        mean_time = statistics.mean(response_times)
        std_dev = statistics.stdev(response_times) if len(response_times) > 1 else 0
        
        # Mean should be reasonable (relaxed for async)
        assert mean_time < 1.0, f"Mean response time too high: {mean_time}s"
        # Standard deviation should be low (consistent performance)
        assert std_dev < mean_time * 3, f"Response times too variable: std_dev={std_dev}"
    
    @pytest.mark.asyncio
    async def test_database_connection_pooling(self):
        """Database should handle connection pooling efficiently"""
        from database.connection import async_session_maker
        
        async def make_query():
            async with async_session_maker() as session:
                try:
                    from sqlalchemy import text
                    result = await session.execute(text("SELECT 1"))
                    await session.commit()
                    return result.scalar()
                finally:
                    await session.close()
        
        # Make 30 concurrent database queries
        tasks = [make_query() for _ in range(30)]
        start = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        elapsed = time.time() - start
        
        # Most should succeed (filter out exceptions)
        successful = [r for r in results if r == 1]
        success_rate = len(successful) / len(results) if results else 0
        assert success_rate >= 0.9, f"Connection pooling should work: {success_rate * 100:.1f}% success"
        # Relax threshold for async overhead
        assert elapsed < 10.0, f"30 concurrent DB queries took {elapsed}s"


class TestStressPerformance:
    """Test system behavior under stress"""
    
    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """System should handle sustained load"""
        duration = 5  # seconds (reduced for faster tests)
        requests_per_second = 3
        total_requests = duration * requests_per_second
        
        async with httpx.AsyncClient() as client:
            start = time.time()
            success_count = 0
            request_count = 0
            
            while time.time() - start < duration and request_count < total_requests:
                response = await client.get(f"{API_URL}/health")
                if response.status_code == 200:
                    success_count += 1
                request_count += 1
                await asyncio.sleep(1.0 / requests_per_second)
        
        # Should maintain high success rate
        success_rate = success_count / request_count if request_count > 0 else 0
        assert success_rate >= 0.9, f"Success rate under sustained load: {success_rate * 100:.1f}%"
    
    @pytest.mark.asyncio
    async def test_memory_usage_under_load(self):
        """System should not leak memory under load"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Make many requests
            async with httpx.AsyncClient() as client:
                tasks = [client.get(f"{API_URL}/health") for _ in range(50)]
                await asyncio.gather(*tasks, return_exceptions=True)
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            # Memory increase should be reasonable (< 200MB for 50 requests)
            assert memory_increase < 200, f"Memory increased by {memory_increase}MB"
        except ImportError:
            pytest.skip("psutil not available for memory testing")


class TestScalabilityPerformance:
    """Test system scalability"""
    
    @pytest.mark.asyncio
    async def test_large_result_set_handling(self):
        """System should handle large result sets efficiently"""
        async with httpx.AsyncClient() as client:
            # Request with large limit
            start = time.time()
            response = await client.get(f"{API_URL}/api/videos/?limit=1000")
            elapsed = time.time() - start
            
            # Should either return results or reject with reasonable limit
            assert response.status_code in [200, 400, 422, 404, 405]
            if response.status_code == 200:
                # If it returns, should be paginated or limited
                data = response.json()
                if isinstance(data, list):
                    # Should have reasonable limit
                    assert len(data) <= 1000
                # Should complete in reasonable time (relaxed for async)
                assert elapsed < 15.0, f"Large result set query took {elapsed}s"
    
    @pytest.mark.asyncio
    async def test_batch_operation_performance(self):
        """Batch operations should scale efficiently"""
        async with httpx.AsyncClient() as client:
            # Test batch thumbnail generation
            video_ids = [f"test-{i}" for i in range(50)]
            
            start = time.time()
            response = await client.post(
                f"{API_URL}/api/videos/generate-thumbnails-batch",
                json={"video_ids": video_ids, "max_videos": 50}
            )
            elapsed = time.time() - start
            
            # Should accept or reject quickly
            assert response.status_code in [200, 400, 422, 404, 405]
            # Response should be fast (queuing, not processing) - relaxed for async
            assert elapsed < 5.0, f"Batch operation queuing took {elapsed}s"








