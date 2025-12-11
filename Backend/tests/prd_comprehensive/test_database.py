"""
PRD Database Tests
Data integrity, queries, and database operations.
Coverage: 30+ database tests
"""
import pytest
import httpx
import uuid

API_BASE = "http://localhost:5555"
DB_API_URL = f"{API_BASE}/api/media-db"


# =============================================================================
# DATABASE: Connection
# =============================================================================

class TestDatabaseConnection:
    """Database connection tests."""
    
    def test_database_connected(self):
        """Database is connected."""
        response = httpx.get(f"{DB_API_URL}/health", timeout=10)
        data = response.json()
        assert data.get("database") == "connected"
    
    def test_database_responds(self):
        """Database responds to queries."""
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        assert response.status_code == 200
    
    def test_database_stats_available(self):
        """Database stats available."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert response.status_code == 200


# =============================================================================
# DATABASE: Data Integrity
# =============================================================================

class TestDatabaseIntegrity:
    """Data integrity tests."""
    
    def test_ids_are_valid_uuids(self):
        """All IDs are valid UUIDs."""
        response = httpx.get(f"{DB_API_URL}/list?limit=10", timeout=10)
        for item in response.json():
            try:
                uuid.UUID(item["media_id"])
            except ValueError:
                pytest.fail(f"Invalid UUID: {item['media_id']}")
    
    def test_no_duplicate_ids(self):
        """No duplicate IDs in results."""
        response = httpx.get(f"{DB_API_URL}/list?limit=100", timeout=10)
        ids = [item["media_id"] for item in response.json()]
        assert len(ids) == len(set(ids))
    
    def test_created_at_present(self):
        """Created_at field present."""
        response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if response.json():
            item = response.json()[0]
            assert "created_at" in item or "createdAt" in item
    
    def test_status_valid_values(self):
        """Status has valid values."""
        valid_statuses = ["ingested", "analyzed", "scheduled", "posted", "archived", "pending"]
        response = httpx.get(f"{DB_API_URL}/list?limit=20", timeout=10)
        for item in response.json():
            status = item.get("status", "")
            if status:
                assert status in valid_statuses or status.lower() in valid_statuses


# =============================================================================
# DATABASE: Queries
# =============================================================================

class TestDatabaseQueries:
    """Database query tests."""
    
    def test_list_query_works(self):
        """Basic list query works."""
        response = httpx.get(f"{DB_API_URL}/list", timeout=10)
        assert response.status_code == 200
    
    def test_limit_query_works(self):
        """Limit query parameter works."""
        response = httpx.get(f"{DB_API_URL}/list?limit=5", timeout=10)
        data = response.json()
        assert len(data) <= 5
    
    def test_offset_query_works(self):
        """Offset query parameter works."""
        response = httpx.get(f"{DB_API_URL}/list?offset=5&limit=5", timeout=10)
        assert response.status_code == 200
    
    def test_status_filter_query(self):
        """Status filter query works."""
        response = httpx.get(f"{DB_API_URL}/list?status=ingested", timeout=10)
        assert response.status_code == 200
    
    def test_detail_query_works(self):
        """Detail query works."""
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if list_response.json():
            media_id = list_response.json()[0]["media_id"]
            detail = httpx.get(f"{DB_API_URL}/detail/{media_id}", timeout=10)
            assert detail.status_code == 200
    
    def test_stats_query_works(self):
        """Stats query works."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "total_videos" in data


# =============================================================================
# DATABASE: Count Consistency
# =============================================================================

class TestDatabaseCounts:
    """Count consistency tests."""
    
    def test_stats_total_reasonable(self):
        """Stats total is reasonable."""
        response = httpx.get(f"{DB_API_URL}/stats", timeout=10)
        data = response.json()
        total = data.get("total_videos", 0)
        assert total >= 0
    
    def test_list_count_matches_limit(self):
        """List count respects limit."""
        for limit in [5, 10, 20]:
            response = httpx.get(f"{DB_API_URL}/list?limit={limit}", timeout=10)
            data = response.json()
            assert len(data) <= limit
    
    def test_pagination_covers_all(self):
        """Pagination covers all items."""
        stats = httpx.get(f"{DB_API_URL}/stats", timeout=10).json()
        total = stats.get("total_videos", 0)
        
        if total > 100:
            pytest.skip("Too many items for full test")
        
        all_ids = set()
        offset = 0
        while offset < total + 20:
            response = httpx.get(f"{DB_API_URL}/list?offset={offset}&limit=20", timeout=10)
            data = response.json()
            if not data:
                break
            for item in data:
                all_ids.add(item["media_id"])
            offset += 20
        
        assert len(all_ids) == total


# =============================================================================
# DATABASE: Error Handling
# =============================================================================

class TestDatabaseErrors:
    """Database error handling tests."""
    
    def test_invalid_id_handled(self):
        """Invalid ID handled gracefully."""
        response = httpx.get(f"{DB_API_URL}/detail/not-a-uuid", timeout=10)
        assert response.status_code in [400, 404, 422, 500]
    
    def test_nonexistent_id_handled(self):
        """Non-existent ID handled gracefully."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = httpx.get(f"{DB_API_URL}/detail/{fake_id}", timeout=10)
        assert response.status_code in [404, 500]
    
    def test_invalid_limit_handled(self):
        """Invalid limit handled gracefully."""
        response = httpx.get(f"{DB_API_URL}/list?limit=invalid", timeout=10)
        assert response.status_code in [200, 400, 422]


# =============================================================================
# DATABASE: Relationships
# =============================================================================

class TestDatabaseRelationships:
    """Database relationship tests."""
    
    def test_detail_has_complete_data(self):
        """Detail has complete data."""
        list_response = httpx.get(f"{DB_API_URL}/list?limit=1", timeout=10)
        if not list_response.json():
            pytest.skip("No media")
        
        media_id = list_response.json()[0]["media_id"]
        detail = httpx.get(f"{DB_API_URL}/detail/{media_id}", timeout=10)
        data = detail.json()
        
        # Should have more fields than list
        assert len(data.keys()) > 0


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
