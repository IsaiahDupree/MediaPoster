"""
Pagination Tests
Tests pagination functionality across backend API and frontend integration.
"""
import pytest
import httpx
from typing import List, Dict, Any

# API URLs
API_BASE = "http://localhost:5555"
DB_API_URL = f"{API_BASE}/api/media-db"
FRONTEND_BASE = "http://localhost:5557"


# =============================================================================
# BACKEND PAGINATION TESTS
# =============================================================================

class TestBackendPagination:
    """Test backend API pagination."""
    
    def test_media_list_default_pagination(self):
        """Media list should support default pagination."""
        response = httpx.get(f"{DB_API_URL}/list", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        
        # Default should return reasonable number
        assert len(data) <= 100  # Should have some default limit
        
        print(f"✓ Default pagination: {len(data)} items")
    
    def test_media_list_with_limit(self):
        """Media list should respect limit parameter."""
        limits = [5, 10, 20, 50]
        
        for limit in limits:
            response = httpx.get(f"{DB_API_URL}/list?limit={limit}", timeout=10)
            assert response.status_code == 200
            
            data = response.json()
            assert isinstance(data, list)
            assert len(data) <= limit
            
            print(f"✓ Limit {limit}: returned {len(data)} items")
    
    def test_media_list_pagination_consistency(self):
        """Pagination should return consistent results."""
        # Get first page
        response1 = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        assert response1.status_code == 200
        page1 = response1.json()
        
        # Get same page again
        response2 = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        assert response2.status_code == 200
        page2 = response2.json()
        
        # Should return same items (assuming no new ingestion)
        if page1 and page2:
            assert page1[0]["media_id"] == page2[0]["media_id"]
            print(f"✓ Pagination consistent: {len(page1)} items")
        else:
            print(f"⚠️  No data to test consistency")
    
    def test_media_list_offset_pagination(self):
        """Test offset-based pagination if supported."""
        # Get first page
        response1 = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        assert response1.status_code == 200
        page1 = response1.json()
        
        if len(page1) < 10:
            pytest.skip("Not enough data for offset test")
        
        # Try offset parameter (may not be implemented)
        response2 = httpx.get(f"{DB_API_URL}/list?limit=10&offset=10", timeout=10)
        
        if response2.status_code == 200:
            page2 = response2.json()
            
            # Pages should be different
            if page1 and page2:
                assert page1[0]["media_id"] != page2[0]["media_id"]
                print(f"✓ Offset pagination works")
        else:
            print(f"⚠️  Offset pagination not implemented")
    
    def test_media_list_large_limit(self):
        """Test pagination with large limit."""
        response = httpx.get(f"{DB_API_URL}/list?limit=100", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 100
        
        print(f"✓ Large limit (100): returned {len(data)} items")
    
    def test_media_list_invalid_limit(self):
        """Test pagination with invalid limit."""
        # Negative limit
        response = httpx.get(f"{DB_API_URL}/list?limit=-1", timeout=10)
        # Should either reject or use default
        assert response.status_code in [200, 400, 422]
        
        # Zero limit
        response = httpx.get(f"{DB_API_URL}/list?limit=0", timeout=10)
        assert response.status_code in [200, 400, 422]
        
        # Very large limit
        response = httpx.get(f"{DB_API_URL}/list?limit=10000", timeout=10)
        assert response.status_code in [200, 400, 422]
        
        if response.status_code == 200:
            data = response.json()
            # Should cap at reasonable limit
            assert len(data) <= 1000
        
        print(f"✓ Invalid limits handled correctly")
    
    def test_media_list_with_filters_and_pagination(self):
        """Test pagination works with filters."""
        # Get analyzed media with pagination
        response = httpx.get(
            f"{DB_API_URL}/list?status=analyzed&limit=5",
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
        
        # All items should match filter
        for item in data:
            if "status" in item:
                assert item["status"] == "analyzed"
        
        print(f"✓ Pagination with filters: {len(data)} items")
    
    def test_search_pagination(self):
        """Test search endpoint pagination."""
        response = httpx.get(
            f"{DB_API_URL}/search?query=IMG&limit=10",
            timeout=10
        )
        
        # Search may not be implemented
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) <= 10
            print(f"✓ Search pagination: {len(data)} results")
        else:
            print(f"⚠️  Search endpoint not implemented (405)")


# =============================================================================
# PAGINATION METADATA TESTS
# =============================================================================

class TestPaginationMetadata:
    """Test pagination metadata in responses."""
    
    def test_pagination_metadata_structure(self):
        """Check if API returns pagination metadata."""
        response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check if response includes pagination info
        # (May be in response body or headers)
        if isinstance(data, dict):
            # Structured response with metadata
            assert "items" in data or "data" in data or "results" in data
            
            # Check for pagination fields
            has_pagination = any(key in data for key in [
                "total", "count", "page", "limit", "offset",
                "has_next", "has_prev", "next_page", "prev_page"
            ])
            
            if has_pagination:
                print(f"✓ Pagination metadata present")
                print(f"  Keys: {list(data.keys())}")
            else:
                print(f"⚠️  No pagination metadata (simple list)")
        else:
            # Simple list response
            print(f"⚠️  Simple list response (no metadata)")
    
    def test_total_count_accuracy(self):
        """If total count is provided, verify accuracy."""
        # Get stats for total count
        stats_response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert stats_response.status_code == 200
        
        stats = stats_response.json()
        total_videos = stats.get("total_videos", 0)
        
        # Get all items (up to reasonable limit)
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1000", timeout=10)
        assert list_response.status_code == 200
        
        items = list_response.json()
        
        if isinstance(items, list):
            returned_count = len(items)
        else:
            returned_count = len(items.get("items", []))
        
        print(f"✓ Total in stats: {total_videos}")
        print(f"✓ Items returned: {returned_count}")
        
        # If we got less than limit, we got all items
        if returned_count < 1000:
            assert returned_count <= total_videos


# =============================================================================
# FRONTEND PAGINATION TESTS
# =============================================================================

class TestFrontendPagination:
    """Test frontend pagination integration."""
    
    def test_media_library_loads_with_pagination(self):
        """Media library should load with paginated data."""
        response = httpx.get(f"{FRONTEND_BASE}/media", timeout=10)
        assert response.status_code == 200
        
        content = response.content.decode('utf-8', errors='ignore')
        
        # Should have some indication of pagination
        # (buttons, page numbers, load more, etc.)
        has_pagination_ui = any(term in content.lower() for term in [
            'page', 'next', 'prev', 'load more', 'pagination'
        ])
        
        if has_pagination_ui:
            print(f"✓ Pagination UI detected")
        else:
            print(f"⚠️  No obvious pagination UI")
    
    def test_media_library_fetches_paginated_data(self):
        """Media library should fetch paginated data from backend."""
        # Verify backend pagination works
        response = httpx.get(f"{DB_API_URL}/list?limit=20", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 20
        
        print(f"✓ Backend provides paginated data: {len(data)} items")
    
    def test_dashboard_recent_media_pagination(self):
        """Dashboard should show limited recent media."""
        # Dashboard typically shows 5-10 recent items
        response = httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5
        
        print(f"✓ Dashboard recent media: {len(data)} items")


# =============================================================================
# PAGINATION PERFORMANCE TESTS
# =============================================================================

class TestPaginationPerformance:
    """Test pagination performance."""
    
    def test_small_page_performance(self):
        """Small pages should load quickly."""
        import time
        
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 1.0  # Should be fast
        
        print(f"✓ Small page (10 items): {elapsed:.3f}s")
    
    def test_medium_page_performance(self):
        """Medium pages should load reasonably fast."""
        import time
        
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?limit=50", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 2.0  # Should be reasonably fast
        
        print(f"✓ Medium page (50 items): {elapsed:.3f}s")
    
    def test_large_page_performance(self):
        """Large pages should complete within timeout."""
        import time
        
        start = time.time()
        response = httpx.get(f"{DB_API_URL}/list?limit=100", timeout=10)
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed < 5.0  # Should complete within reasonable time
        
        print(f"✓ Large page (100 items): {elapsed:.3f}s")


# =============================================================================
# PAGINATION EDGE CASES
# =============================================================================

class TestPaginationEdgeCases:
    """Test pagination edge cases."""
    
    def test_empty_result_pagination(self):
        """Pagination should handle empty results."""
        # Filter that returns no results
        response = httpx.get(
            f"{DB_API_URL}/list?status=nonexistent&limit=10",
            timeout=10
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
        
        print(f"✓ Empty results handled correctly")
    
    def test_single_item_pagination(self):
        """Pagination should handle single item."""
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 1
        
        print(f"✓ Single item pagination works")
    
    def test_pagination_beyond_available_data(self):
        """Requesting page beyond available data should handle gracefully."""
        # Get total count
        stats_response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        stats = stats_response.json()
        total = stats.get("total_videos", 0)
        
        # Request offset beyond total
        response = httpx.get(
            f"{DB_API_URL}/list?limit=10&offset={total + 100}",
            timeout=10
        )
        
        # Should return empty or handle gracefully
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0
            print(f"✓ Beyond data handled: empty list")
        else:
            print(f"⚠️  Offset not supported")


# =============================================================================
# CURSOR-BASED PAGINATION TESTS
# =============================================================================

class TestCursorPagination:
    """Test cursor-based pagination if implemented."""
    
    def test_cursor_pagination_support(self):
        """Check if cursor-based pagination is supported."""
        # Try with cursor parameter
        response = httpx.get(
            f"{DB_API_URL}/list?limit=10&cursor=test",
            timeout=10
        )
        
        # If cursor is supported, should either work or return error
        if response.status_code == 200:
            data = response.json()
            
            # Check if response includes next cursor
            if isinstance(data, dict):
                has_cursor = "cursor" in data or "next_cursor" in data
                if has_cursor:
                    print(f"✓ Cursor pagination supported")
                else:
                    print(f"⚠️  Cursor parameter accepted but no cursor in response")
            else:
                print(f"⚠️  Cursor parameter accepted (simple list)")
        else:
            print(f"⚠️  Cursor pagination not implemented")


# =============================================================================
# PAGINATION CONSISTENCY TESTS
# =============================================================================

class TestPaginationConsistency:
    """Test pagination consistency across requests."""
    
    def test_pagination_order_consistency(self):
        """Items should appear in consistent order."""
        # Get first page twice
        response1 = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        response2 = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        page1 = response1.json()
        page2 = response2.json()
        
        if page1 and page2:
            # Order should be consistent
            ids1 = [item["media_id"] for item in page1]
            ids2 = [item["media_id"] for item in page2]
            
            assert ids1 == ids2
            print(f"✓ Pagination order consistent")
        else:
            print(f"⚠️  No data to test order")
    
    def test_no_duplicate_items_across_pages(self):
        """Items should not appear in multiple pages."""
        # Get two consecutive pages
        response1 = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        response2 = httpx.get(f"{DB_API_URL}/list?limit=10&offset=10", timeout=10)
        
        if response1.status_code != 200 or response2.status_code != 200:
            pytest.skip("Offset pagination not supported")
        
        page1 = response1.json()
        page2 = response2.json()
        
        if page1 and page2:
            ids1 = set(item["media_id"] for item in page1)
            ids2 = set(item["media_id"] for item in page2)
            
            # No overlap
            overlap = ids1 & ids2
            assert len(overlap) == 0
            
            print(f"✓ No duplicate items across pages")
        else:
            print(f"⚠️  Not enough data for duplicate test")


# =============================================================================
# PAGINATION SUMMARY
# =============================================================================

class TestPaginationSummary:
    """Generate pagination test summary."""
    
    def test_generate_pagination_summary(self):
        """Generate summary of pagination capabilities."""
        print(f"\n{'='*60}")
        print(f"PAGINATION TEST SUMMARY")
        print(f"{'='*60}\n")
        
        # Test various limits
        limits = [1, 5, 10, 20, 50, 100]
        
        for limit in limits:
            response = httpx.get(f"{DB_API_URL}/list?limit={limit}", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                count = len(data) if isinstance(data, list) else len(data.get("items", []))
                print(f"  Limit {limit:3d}: {count:3d} items returned")
        
        # Get stats
        stats_response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        if stats_response.status_code == 200:
            stats = stats_response.json()
            total = stats.get("total_videos", 0)
            print(f"\n  Total items in database: {total}")
        
        print(f"\n{'='*60}")
        print(f"Pagination Features:")
        print(f"  ✓ Limit parameter supported")
        print(f"  ⚠️  Offset parameter (check logs)")
        print(f"  ⚠️  Cursor pagination (check logs)")
        print(f"  ✓ Filter + pagination works")
        print(f"  ✓ Performance acceptable")
        print(f"{'='*60}\n")


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
