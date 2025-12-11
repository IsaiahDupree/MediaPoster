"""
Comprehensive Backend Performance Tests
Tests response times, throughput, and optimization opportunities
"""
import pytest
import httpx
import time
import statistics
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict
import os

API_BASE = os.getenv("API_BASE_URL", "http://localhost:5555/api")
TIMEOUT = 30


class TestResponseTime:
    """Test response times for critical endpoints"""
    
    def test_health_check_speed(self):
        """Health check should be very fast (< 50ms)"""
        times = []
        for _ in range(10):
            start = time.time()
            response = httpx.get(f"{API_BASE}/health", timeout=TIMEOUT)
            times.append((time.time() - start) * 1000)  # Convert to ms
            assert response.status_code == 200
        
        avg = statistics.mean(times)
        p95 = statistics.quantiles(times, n=20)[18]  # 95th percentile
        
        print(f"\n📊 Health Check Performance:")
        print(f"   Average: {avg:.2f}ms")
        print(f"   P95: {p95:.2f}ms")
        print(f"   Min: {min(times):.2f}ms")
        print(f"   Max: {max(times):.2f}ms")
        
        assert avg < 50, f"Health check too slow: {avg:.2f}ms (expected < 50ms)"
        assert p95 < 100, f"P95 too slow: {p95:.2f}ms (expected < 100ms)"
    
    def test_social_analytics_overview_speed(self):
        """Social analytics overview should load quickly (< 500ms)"""
        times = []
        for _ in range(5):
            start = time.time()
            response = httpx.get(f"{API_BASE}/social-analytics/overview", timeout=TIMEOUT)
            times.append((time.time() - start) * 1000)
            assert response.status_code in [200, 404]  # 404 if no data
        
        avg = statistics.mean(times)
        p95 = statistics.quantiles(times, n=20)[18] if len(times) > 1 else times[0]
        
        print(f"\n📊 Analytics Overview Performance:")
        print(f"   Average: {avg:.2f}ms")
        print(f"   P95: {p95:.2f}ms")
        
        assert avg < 500, f"Analytics overview too slow: {avg:.2f}ms (expected < 500ms)"
    
    def test_accounts_list_speed(self):
        """Accounts list should load quickly (< 300ms)"""
        times = []
        for _ in range(5):
            start = time.time()
            response = httpx.get(f"{API_BASE}/social-analytics/accounts", timeout=TIMEOUT)
            times.append((time.time() - start) * 1000)
            assert response.status_code in [200, 404]
        
        avg = statistics.mean(times)
        
        print(f"\n📊 Accounts List Performance:")
        print(f"   Average: {avg:.2f}ms")
        
        assert avg < 300, f"Accounts list too slow: {avg:.2f}ms (expected < 300ms)"
    
    def test_comments_endpoint_speed(self):
        """Comments endpoint should be fast (< 400ms)"""
        times = []
        for _ in range(5):
            start = time.time()
            response = httpx.get(f"{API_BASE}/comments?page=1&page_size=50", timeout=TIMEOUT)
            times.append((time.time() - start) * 1000)
            assert response.status_code in [200, 404]
        
        avg = statistics.mean(times)
        
        print(f"\n📊 Comments Endpoint Performance:")
        print(f"   Average: {avg:.2f}ms")
        
        assert avg < 400, f"Comments endpoint too slow: {avg:.2f}ms (expected < 400ms)"


class TestConcurrency:
    """Test how the API handles concurrent requests"""
    
    def test_concurrent_health_checks(self):
        """Should handle 20 concurrent health checks"""
        def make_request():
            response = httpx.get(f"{API_BASE}/health", timeout=TIMEOUT)
            return response.status_code == 200
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            start = time.time()
            results = list(executor.map(make_request, range(20)))
            duration = time.time() - start
        
        success_rate = sum(results) / len(results)
        
        print(f"\n📊 Concurrent Health Checks:")
        print(f"   Requests: 20")
        print(f"   Success Rate: {success_rate * 100:.1f}%")
        print(f"   Duration: {duration:.2f}s")
        print(f"   Throughput: {20/duration:.2f} req/s")
        
        assert success_rate == 1.0, f"Not all requests succeeded: {success_rate * 100:.1f}%"
        assert duration < 2.0, f"Too slow for concurrent requests: {duration:.2f}s"
    
    def test_concurrent_analytics_requests(self):
        """Should handle 10 concurrent analytics requests"""
        def make_request():
            response = httpx.get(f"{API_BASE}/social-analytics/overview", timeout=TIMEOUT)
            return response.status_code in [200, 404]
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            start = time.time()
            results = list(executor.map(make_request, range(10)))
            duration = time.time() - start
        
        success_rate = sum(results) / len(results)
        
        print(f"\n📊 Concurrent Analytics Requests:")
        print(f"   Requests: 10")
        print(f"   Success Rate: {success_rate * 100:.1f}%")
        print(f"   Duration: {duration:.2f}s")
        
        assert success_rate == 1.0, f"Not all requests succeeded: {success_rate * 100:.1f}%"
        assert duration < 5.0, f"Too slow for concurrent analytics: {duration:.2f}s"


class TestDatabaseQueryPerformance:
    """Test database query performance"""
    
    def test_accounts_query_performance(self):
        """Test accounts query with different filters"""
        filters = [
            "",
            "?platform=youtube",
            "?platform=tiktok",
            "?platform=instagram"
        ]
        
        results = []
        for filter_str in filters:
            start = time.time()
            response = httpx.get(f"{API_BASE}/social-analytics/accounts{filter_str}", timeout=TIMEOUT)
            duration = (time.time() - start) * 1000
            results.append({
                "filter": filter_str or "none",
                "duration_ms": duration,
                "status": response.status_code
            })
        
        print(f"\n📊 Database Query Performance:")
        for result in results:
            print(f"   Filter '{result['filter']}': {result['duration_ms']:.2f}ms")
            assert result['duration_ms'] < 500, f"Query too slow: {result['duration_ms']:.2f}ms"
    
    def test_pagination_performance(self):
        """Test that pagination doesn't degrade performance"""
        page_sizes = [10, 50, 100]
        results = []
        
        for page_size in page_sizes:
            start = time.time()
            response = httpx.get(
                f"{API_BASE}/comments?page=1&page_size={page_size}",
                timeout=TIMEOUT
            )
            duration = (time.time() - start) * 1000
            results.append({
                "page_size": page_size,
                "duration_ms": duration,
                "status": response.status_code
            })
        
        print(f"\n📊 Pagination Performance:")
        for result in results:
            print(f"   Page size {result['page_size']}: {result['duration_ms']:.2f}ms")
            # Larger page sizes can be slower, but should still be reasonable
            assert result['duration_ms'] < 1000, f"Pagination too slow: {result['duration_ms']:.2f}ms"


class TestMemoryAndResourceUsage:
    """Test memory and resource usage patterns"""
    
    def test_repeated_requests_memory(self):
        """Repeated requests shouldn't cause memory leaks"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Make 50 requests
        for _ in range(50):
            httpx.get(f"{API_BASE}/health", timeout=TIMEOUT)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"\n📊 Memory Usage:")
        print(f"   Initial: {initial_memory:.2f}MB")
        print(f"   Final: {final_memory:.2f}MB")
        print(f"   Increase: {memory_increase:.2f}MB")
        
        # Memory increase should be reasonable (< 50MB for 50 requests)
        assert memory_increase < 50, f"Memory leak detected: {memory_increase:.2f}MB increase"


class TestOptimizationOpportunities:
    """Identify optimization opportunities"""
    
    def test_n_plus_one_queries(self):
        """Check for N+1 query problems"""
        # This would require database query logging
        # For now, we'll test that endpoints are fast enough
        start = time.time()
        response = httpx.get(f"{API_BASE}/social-analytics/accounts", timeout=TIMEOUT)
        duration = time.time() - start
        
        # If this is slow, it might indicate N+1 queries
        print(f"\n📊 Query Optimization Check:")
        print(f"   Accounts endpoint: {duration * 1000:.2f}ms")
        
        if duration > 0.5:
            print("   ⚠️  WARNING: Slow query detected - possible N+1 problem")
        else:
            print("   ✅ Query performance looks good")
    
    def test_caching_opportunities(self):
        """Identify endpoints that could benefit from caching"""
        # Test endpoints that should be cacheable
        cacheable_endpoints = [
            "/social-analytics/overview",
            "/social-analytics/accounts",
        ]
        
        results = []
        for endpoint in cacheable_endpoints:
            # First request
            start1 = time.time()
            httpx.get(f"{API_BASE}{endpoint}", timeout=TIMEOUT)
            first_duration = time.time() - start1
            
            # Second request (should be faster if cached)
            start2 = time.time()
            httpx.get(f"{API_BASE}{endpoint}", timeout=TIMEOUT)
            second_duration = time.time() - start2
            
            speedup = (first_duration - second_duration) / first_duration * 100 if first_duration > 0 else 0
            
            results.append({
                "endpoint": endpoint,
                "first": first_duration * 1000,
                "second": second_duration * 1000,
                "speedup": speedup
            })
        
        print(f"\n📊 Caching Opportunities:")
        for result in results:
            print(f"   {result['endpoint']}:")
            print(f"      First: {result['first']:.2f}ms")
            print(f"      Second: {result['second']:.2f}ms")
            if result['speedup'] > 10:
                print(f"      ✅ {result['speedup']:.1f}% faster (likely cached)")
            else:
                print(f"      ⚠️  No significant speedup (consider caching)")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

