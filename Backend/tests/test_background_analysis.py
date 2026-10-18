"""
Test that analysis jobs run in background without blocking app operation.
"""
import asyncio
import time
import httpx
import pytest

API_URL = "http://localhost:5555"


class TestBackgroundAnalysis:
    """Test that analysis runs in background and app remains responsive."""
    
    @pytest.mark.asyncio
    async def test_app_responsive_during_analysis(self):
        """
        Start analysis and verify app remains responsive.
        - Trigger batch analysis
        - Immediately make multiple API requests
        - All requests should complete quickly (< 1 second each)
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Start batch analysis (limit to 5 for testing)
            start_time = time.time()
            analyze_res = await client.post(f"{API_URL}/api/media-db/batch/analyze?limit=5")
            analyze_time = time.time() - start_time
            
            print(f"\n[Test] Batch analyze response time: {analyze_time:.3f}s")
            print(f"[Test] Analyze response: {analyze_res.json()}")
            
            # Batch analyze should return immediately (< 1 second)
            assert analyze_time < 1.0, f"Batch analyze took too long: {analyze_time}s"
            assert analyze_res.status_code == 200
            
            # 2. Make concurrent requests while analysis runs in background
            endpoints = [
                "/api/media-db/stats",
                "/api/media-db/health",
                "/api/media/health",
                "/api/media-db/list?limit=10",
                "/api/media-db/stats",  # Repeat to verify consistency
            ]
            
            print(f"\n[Test] Making {len(endpoints)} concurrent requests during analysis...")
            
            tasks = []
            for endpoint in endpoints:
                tasks.append(client.get(f"{API_URL}{endpoint}"))
            
            start_time = time.time()
            responses = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            print(f"[Test] All {len(endpoints)} requests completed in {total_time:.3f}s")
            
            # All requests should complete quickly
            assert total_time < 3.0, f"Concurrent requests took too long: {total_time}s"
            
            # All responses should be successful
            for i, res in enumerate(responses):
                assert res.status_code == 200, f"Request {endpoints[i]} failed: {res.status_code}"
                print(f"  ✓ {endpoints[i]} - {res.status_code}")
            
            print(f"\n[Test] ✅ App remained responsive during background analysis")
    
    @pytest.mark.asyncio
    async def test_multiple_analysis_requests_dont_block(self):
        """
        Multiple analysis requests should queue and not block each other.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Make 3 batch analyze requests in quick succession
            print("\n[Test] Making 3 batch analyze requests...")
            
            start_time = time.time()
            tasks = [
                client.post(f"{API_URL}/api/media-db/batch/analyze?limit=2"),
                client.post(f"{API_URL}/api/media-db/batch/analyze?limit=2"),
                client.post(f"{API_URL}/api/media-db/batch/analyze?limit=2"),
            ]
            responses = await asyncio.gather(*tasks)
            total_time = time.time() - start_time
            
            print(f"[Test] 3 batch analyze requests completed in {total_time:.3f}s")
            
            # All should return quickly (they just queue tasks)
            assert total_time < 2.0, f"Batch requests took too long: {total_time}s"
            
            for i, res in enumerate(responses):
                print(f"  Request {i+1}: {res.json()}")
                assert res.status_code == 200
            
            # Verify app still responsive after queuing multiple analyses
            health_res = await client.get(f"{API_URL}/api/media-db/health")
            assert health_res.status_code == 200
            
            print(f"\n[Test] ✅ Multiple analysis requests handled without blocking")
    
    @pytest.mark.asyncio  
    async def test_stats_update_during_analysis(self):
        """
        Stats endpoint should remain responsive and show updates during analysis.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get initial stats
            stats1 = await client.get(f"{API_URL}/api/media-db/stats")
            initial_stats = stats1.json()
            print(f"\n[Test] Initial stats: analyzed={initial_stats.get('analyzed_count')}")
            
            # Start analysis
            await client.post(f"{API_URL}/api/media-db/batch/analyze?limit=3")
            
            # Poll stats multiple times - should always be responsive
            print("[Test] Polling stats during analysis...")
            for i in range(5):
                start = time.time()
                stats_res = await client.get(f"{API_URL}/api/media-db/stats")
                elapsed = time.time() - start
                
                assert stats_res.status_code == 200
                assert elapsed < 1.0, f"Stats request {i} took too long: {elapsed}s"
                
                stats = stats_res.json()
                print(f"  Poll {i+1}: analyzed={stats.get('analyzed_count')} ({elapsed:.3f}s)")
                
                await asyncio.sleep(0.5)
            
            print(f"\n[Test] ✅ Stats endpoint remained responsive during analysis")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
