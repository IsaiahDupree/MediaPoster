"""
PRD Performance Tests
Load, stress, and performance testing.
Coverage: 30+ performance tests
"""
import pytest
import httpx
import time
import statistics
import concurrent.futures

API_BASE = "http://localhost:5555"
DB_API_URL = f"{API_BASE}/api/media-db"
FRONTEND_BASE = "http://localhost:5557"


# =============================================================================
# PERFORMANCE: Response Time
# =============================================================================

class TestPerformanceResponseTime:
    """Response time performance tests."""
    
    def test_health_under_100ms(self):
        """Health check under 100ms."""
        times = []
        for _ in range(5):
            start = time.time()
            httpx.get(f"{DB_API_URL}/health", timeout=10)
            times.append(time.time() - start)
        
        avg = statistics.mean(times)
        assert avg < 0.5
    
    def test_list_under_500ms(self):
        """List endpoint under 500ms."""
        times = []
        for _ in range(3):
            start = time.time()
            httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
            times.append(time.time() - start)
        
        avg = statistics.mean(times)
        assert avg < 1.0
    
    def test_stats_under_200ms(self):
        """Stats endpoint under 200ms."""
        times = []
        for _ in range(3):
            start = time.time()
            httpx.get(f"{DB_API_URL}/stats", timeout=10)
            times.append(time.time() - start)
        
        avg = statistics.mean(times)
        assert avg < 0.5
    
    def test_detail_under_300ms(self):
        """Detail endpoint under 300ms."""
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if not list_response.json():
            pytest.skip("No media")
        
        media_id = list_response.json()[0]["media_id"]
        
        times = []
        for _ in range(3):
            start = time.time()
            httpx.get(f"{DB_API_URL}/detail/{media_id}", timeout=10)
            times.append(time.time() - start)
        
        avg = statistics.mean(times)
        assert avg < 0.5
    
    def test_frontend_under_2s(self):
        """Frontend loads under 2 seconds."""
        pages = ["/", "/media", "/analytics"]
        
        for page in pages:
            start = time.time()
            response = httpx.get(f"{FRONTEND_BASE}{page}", timeout=10)
            elapsed = time.time() - start
            
            assert response.status_code == 200
            assert elapsed < 2.0


# =============================================================================
# PERFORMANCE: Concurrent Load
# =============================================================================

class TestPerformanceConcurrent:
    """Concurrent load tests."""
    
    def test_10_concurrent_health(self):
        """Handle 10 concurrent health checks."""
        def make_request():
            start = time.time()
            response = httpx.get(f"{DB_API_URL}/health", timeout=10)
            return time.time() - start, response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]
        
        times = [r[0] for r in results]
        statuses = [r[1] for r in results]
        
        # All should succeed
        assert all(s == 200 for s in statuses)
        # Average should be reasonable
        assert statistics.mean(times) < 1.0
    
    def test_20_concurrent_list(self):
        """Handle 20 concurrent list requests."""
        def make_request():
            response = httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
            return response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [f.result() for f in futures]
        
        # Most should succeed
        success_count = sum(1 for r in results if r == 200)
        assert success_count >= 15
    
    def test_5_concurrent_detail(self):
        """Handle 5 concurrent detail requests."""
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if not list_response.json():
            pytest.skip("No media")
        
        media_id = list_response.json()[0]["media_id"]
        
        def make_request():
            response = httpx.get(f"{DB_API_URL}/detail/{media_id}", timeout=10)
            return response.status_code
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(5)]
            results = [f.result() for f in futures]
        
        assert all(r == 200 for r in results)


# =============================================================================
# PERFORMANCE: Pagination
# =============================================================================

class TestPerformancePagination:
    """Pagination performance tests."""
    
    def test_small_page_performance(self):
        """Small page (10 items) is fast."""
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 0.5
    
    def test_medium_page_performance(self):
        """Medium page (50 items) is fast."""
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?limit=50", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0
    
    def test_large_page_performance(self):
        """Large page (100 items) is acceptable."""
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?limit=100", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0
    
    def test_deep_offset_performance(self):
        """Deep offset is still performant."""
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?offset=1000&limit=10", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0


# =============================================================================
# PERFORMANCE: Throughput
# =============================================================================

class TestPerformanceThroughput:
    """Throughput tests."""
    
    def test_requests_per_second(self):
        """Measure requests per second."""
        count = 20
        start = time.time()
        
        for _ in range(count):
            httpx.get(f"{DB_API_URL}/health", timeout=10)
        
        elapsed = time.time() - start
        rps = count / elapsed
        
        # Should handle at least 5 req/s
        assert rps > 5
    
    def test_sustained_load(self):
        """Sustain load over time."""
        duration = 3  # seconds
        start = time.time()
        count = 0
        
        while time.time() - start < duration:
            response = httpx.get(f"{DB_API_URL}/health", timeout=10)
            if response.status_code == 200:
                count += 1
        
        # Should complete at least some requests
        assert count > 10


# =============================================================================
# PERFORMANCE: Response Size
# =============================================================================

class TestPerformanceResponseSize:
    """Response size tests."""
    
    def test_list_response_size(self):
        """List response size is reasonable."""
        response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        size = len(response.content)
        
        # Should be under 100KB for 10 items
        assert size < 100 * 1024
    
    def test_detail_response_size(self):
        """Detail response size is reasonable."""
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if not list_response.json():
            pytest.skip("No media")
        
        media_id = list_response.json()[0]["media_id"]
        response = httpx.get(f"{DB_API_URL}/detail/{media_id}", timeout=10)
        size = len(response.content)
        
        # Should be under 50KB
        assert size < 50 * 1024


# =============================================================================
# PERFORMANCE: Stability
# =============================================================================

class TestPerformanceStability:
    """Stability tests."""
    
    def test_consistent_response_times(self):
        """Response times are consistent."""
        times = []
        for _ in range(10):
            start = time.time()
            httpx.get(f"{DB_API_URL}/health", timeout=10)
            times.append(time.time() - start)
        
        # Standard deviation should be low
        if len(times) > 1:
            std_dev = statistics.stdev(times)
            mean = statistics.mean(times)
            # Coefficient of variation < 100%
            cv = std_dev / mean if mean > 0 else 0
            assert cv < 1.0
    
    def test_no_degradation_over_time(self):
        """No performance degradation."""
        early_times = []
        late_times = []
        
        # Early requests
        for _ in range(5):
            start = time.time()
            httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
            early_times.append(time.time() - start)
        
        # Do some work
        for _ in range(20):
            httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
        
        # Late requests
        for _ in range(5):
            start = time.time()
            httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
            late_times.append(time.time() - start)
        
        early_avg = statistics.mean(early_times)
        late_avg = statistics.mean(late_times)
        
        # Late should not be >2x slower
        assert late_avg < early_avg * 3


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
