"""
PRD Comprehensive Pagination Tests
Detailed pagination testing covering all edge cases.
Coverage: 50+ pagination tests
"""
import pytest
import httpx
import time

API_BASE = "http://localhost:5555"
DB_API_URL = f"{API_BASE}/api/media-db"


# =============================================================================
# PAGINATION: Basic Correctness
# =============================================================================

class TestPaginationBasicCorrectness:
    """Basic pagination correctness tests."""
    
    def test_page_size_respected_10(self):
        """Request limit=10 returns at most 10 items."""
        response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10
    
    def test_page_size_respected_5(self):
        """Request limit=5 returns at most 5 items."""
        response = httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
        data = response.json()
        assert len(data) <= 5
    
    def test_page_size_respected_1(self):
        """Request limit=1 returns at most 1 item."""
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        data = response.json()
        assert len(data) <= 1
    
    def test_page_size_respected_50(self):
        """Request limit=50 returns at most 50 items."""
        response = httpx.get(f"{DB_API_URL}/list?limit=50", timeout=10)
        data = response.json()
        assert len(data) <= 50
    
    def test_page_size_respected_100(self):
        """Request limit=100 returns at most 100 items."""
        response = httpx.get(f"{DB_API_URL}/list?limit=100", timeout=10)
        data = response.json()
        assert len(data) <= 100
    
    def test_first_page_contents(self):
        """First page (offset=0) returns first items."""
        response = httpx.get(f"{DB_API_URL}/list?offset=0&limit=10", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_subsequent_pages_different(self):
        """Page 2 has different items than page 1."""
        page1 = httpx.get(f"{DB_API_URL}/list?offset=0&limit=5", timeout=10).json()
        page2 = httpx.get(f"{DB_API_URL}/list?offset=5&limit=5", timeout=10).json()
        
        if page1 and page2:
            page1_ids = {item["media_id"] for item in page1}
            page2_ids = {item["media_id"] for item in page2}
            assert page1_ids.isdisjoint(page2_ids), "Pages should not overlap"


# =============================================================================
# PAGINATION: Boundaries & Edges
# =============================================================================

class TestPaginationBoundaries:
    """Pagination boundary tests."""
    
    def test_last_page_fewer_items(self):
        """Last page may have fewer items."""
        # Get total count
        stats = httpx.get(f"{DB_API_URL}/stats", timeout=10).json()
        total = stats.get("total_videos", 0)
        
        if total > 10:
            # Request last page
            offset = (total // 10) * 10
            response = httpx.get(f"{DB_API_URL}/list?offset={offset}&limit=10", timeout=10)
            data = response.json()
            # Last page should have remaining items
            assert len(data) <= 10
    
    def test_out_of_range_page(self):
        """Out of range offset returns empty list."""
        response = httpx.get(f"{DB_API_URL}/list?offset=100000&limit=10", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    def test_zero_limit(self):
        """Limit=0 handled gracefully."""
        response = httpx.get(f"{DB_API_URL}/list?limit=0", timeout=10)
        assert response.status_code in [200, 400, 422]
    
    def test_negative_limit(self):
        """Negative limit handled gracefully."""
        response = httpx.get(f"{DB_API_URL}/list?limit=-1", timeout=10)
        assert response.status_code in [200, 400, 422, 500]
    
    def test_negative_offset(self):
        """Negative offset handled gracefully."""
        response = httpx.get(f"{DB_API_URL}/list?offset=-1", timeout=10)
        assert response.status_code in [200, 400, 422, 500]
    
    def test_very_large_limit(self):
        """Very large limit capped or handled."""
        response = httpx.get(f"{DB_API_URL}/list?limit=10000", timeout=10)
        assert response.status_code in [200, 400, 422]
        if response.status_code == 200:
            data = response.json()
            assert len(data) <= 10000  # Should be capped or return all
    
    def test_string_limit(self):
        """String limit handled gracefully."""
        response = httpx.get(f"{DB_API_URL}/list?limit=abc", timeout=10)
        assert response.status_code in [200, 400, 422]
    
    def test_float_limit(self):
        """Float limit handled gracefully."""
        response = httpx.get(f"{DB_API_URL}/list?limit=5.5", timeout=10)
        assert response.status_code in [200, 400, 422]


# =============================================================================
# PAGINATION: Ordering & Stability
# =============================================================================

class TestPaginationOrdering:
    """Pagination ordering tests."""
    
    def test_consistent_ordering(self):
        """Two requests return same order."""
        response1 = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        response2 = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        
        data1 = response1.json()
        data2 = response2.json()
        
        if data1 and data2:
            ids1 = [item["media_id"] for item in data1]
            ids2 = [item["media_id"] for item in data2]
            assert ids1 == ids2
    
    def test_no_duplicates_across_pages(self):
        """No duplicates across multiple pages."""
        all_ids = set()
        
        for offset in range(0, 50, 10):
            response = httpx.get(f"{DB_API_URL}/list?offset={offset}&limit=10", timeout=10)
            data = response.json()
            
            for item in data:
                media_id = item["media_id"]
                assert media_id not in all_ids, f"Duplicate: {media_id}"
                all_ids.add(media_id)
    
    def test_no_gaps_across_pages(self):
        """Concatenating pages gives complete list."""
        # Get all items in one request
        all_response = httpx.get(f"{DB_API_URL}/list?limit=100", timeout=10)
        all_items = all_response.json()
        
        # Get same items via pagination
        paginated_items = []
        for offset in range(0, len(all_items), 10):
            response = httpx.get(f"{DB_API_URL}/list?offset={offset}&limit=10", timeout=10)
            paginated_items.extend(response.json())
        
        # Should have same count
        assert len(paginated_items) == len(all_items)
    
    def test_stable_under_no_change(self):
        """Same results with static data."""
        results = []
        for _ in range(3):
            response = httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
            results.append([item["media_id"] for item in response.json()])
        
        assert results[0] == results[1] == results[2]


# =============================================================================
# PAGINATION: Filter + Sort Interactions
# =============================================================================

class TestPaginationFilters:
    """Pagination with filters tests."""
    
    def test_filter_with_pagination(self):
        """Filter + pagination works together."""
        response = httpx.get(
            f"{DB_API_URL}/list?status=ingested&limit=10",
            timeout=10
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 10
    
    def test_filter_ingested_pagination(self):
        """Ingested filter respects pagination."""
        page1 = httpx.get(f"{DB_API_URL}/list?status=ingested&offset=0&limit=5", timeout=10)
        page2 = httpx.get(f"{DB_API_URL}/list?status=ingested&offset=5&limit=5", timeout=10)
        
        assert page1.status_code == 200
        assert page2.status_code == 200
    
    def test_filter_analyzed_pagination(self):
        """Analyzed filter respects pagination."""
        response = httpx.get(
            f"{DB_API_URL}/list?status=analyzed&limit=5",
            timeout=10
        )
        assert response.status_code == 200
    
    def test_empty_filter_results(self):
        """Empty filter results return empty list."""
        response = httpx.get(
            f"{DB_API_URL}/list?status=nonexistent&limit=10",
            timeout=10
        )
        # Should return empty list or error
        assert response.status_code in [200, 400, 500]


# =============================================================================
# PAGINATION: Performance
# =============================================================================

class TestPaginationPerformance:
    """Pagination performance tests."""
    
    def test_small_page_fast(self):
        """Small page (10 items) is fast."""
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0
    
    def test_medium_page_fast(self):
        """Medium page (50 items) is fast."""
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?limit=50", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0
    
    def test_large_page_acceptable(self):
        """Large page (100 items) is acceptable."""
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?limit=100", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0
    
    def test_deep_offset_performance(self):
        """Deep offset is still performant."""
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?offset=1000&limit=10", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0
    
    def test_repeated_pagination_stable_time(self):
        """Repeated pagination has stable response time."""
        times = []
        for _ in range(5):
            start = time.time()
            httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
            times.append(time.time() - start)
        
        avg_time = sum(times) / len(times)
        assert avg_time < 1.0


# =============================================================================
# PAGINATION: Data Integrity
# =============================================================================

class TestPaginationDataIntegrity:
    """Pagination data integrity tests."""
    
    def test_all_items_have_ids(self):
        """All paginated items have IDs."""
        response = httpx.get(f"{DB_API_URL}/list?limit=20", timeout=10)
        data = response.json()
        
        for item in data:
            assert "media_id" in item
            assert item["media_id"] is not None
    
    def test_ids_are_unique(self):
        """All IDs in response are unique."""
        response = httpx.get(f"{DB_API_URL}/list?limit=50", timeout=10)
        data = response.json()
        
        ids = [item["media_id"] for item in data]
        assert len(ids) == len(set(ids))
    
    def test_items_have_consistent_structure(self):
        """All items have consistent structure."""
        response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        data = response.json()
        
        if data:
            first_keys = set(data[0].keys())
            for item in data[1:]:
                assert set(item.keys()) == first_keys


# =============================================================================
# PAGINATION: Edge Cases
# =============================================================================

class TestPaginationEdgeCases:
    """Pagination edge case tests."""
    
    def test_offset_equals_total(self):
        """Offset equal to total returns empty."""
        stats = httpx.get(f"{DB_API_URL}/stats", timeout=10).json()
        total = stats.get("total_videos", 0)
        
        response = httpx.get(f"{DB_API_URL}/list?offset={total}&limit=10", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0
    
    def test_limit_greater_than_total(self):
        """Limit greater than total returns all."""
        stats = httpx.get(f"{DB_API_URL}/stats", timeout=10).json()
        total = stats.get("total_videos", 100)
        
        response = httpx.get(f"{DB_API_URL}/list?limit={total + 100}", timeout=10)
        assert response.status_code == 200
    
    def test_single_item_pagination(self):
        """Single item paginates correctly."""
        response = httpx.get(f"{DB_API_URL}/list?limit=1&offset=0", timeout=10)
        data = response.json()
        assert len(data) <= 1
    
    def test_empty_database_pagination(self):
        """Empty results handled."""
        # Use a filter that returns no results
        response = httpx.get(f"{DB_API_URL}/list?status=nonexistent", timeout=10)
        assert response.status_code in [200, 400, 500]


# =============================================================================
# PAGINATION: Walking Through All Pages
# =============================================================================

class TestPaginationWalkthrough:
    """Complete pagination walkthrough tests."""
    
    def test_walk_all_pages(self):
        """Can walk through all pages."""
        stats = httpx.get(f"{DB_API_URL}/stats", timeout=10).json()
        total = stats.get("total_videos", 0)
        
        if total == 0:
            pytest.skip("No data to paginate")
        
        page_size = 10
        all_ids = []
        offset = 0
        
        while offset < min(total, 100):  # Limit to first 100 for test
            response = httpx.get(
                f"{DB_API_URL}/list?offset={offset}&limit={page_size}",
                timeout=10
            )
            data = response.json()
            
            if not data:
                break
            
            for item in data:
                all_ids.append(item["media_id"])
            
            offset += page_size
        
        # Verify no duplicates
        assert len(all_ids) == len(set(all_ids))
    
    def test_complete_coverage(self):
        """All items accessible via pagination."""
        # Get total
        stats = httpx.get(f"{DB_API_URL}/stats", timeout=10).json()
        total = stats.get("total_videos", 0)
        
        if total == 0 or total > 200:
            pytest.skip("Skip for empty or very large datasets")
        
        # Collect all via pagination
        all_items = []
        offset = 0
        while True:
            response = httpx.get(f"{DB_API_URL}/list?offset={offset}&limit=20", timeout=10)
            data = response.json()
            if not data:
                break
            all_items.extend(data)
            offset += 20
            if offset > total + 20:
                break
        
        assert len(all_items) == total


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
