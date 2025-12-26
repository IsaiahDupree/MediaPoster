"""
Edge case tests for media_processing_db list_media endpoint.
Tests for None values, incomplete analysis, and data integrity issues.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
import uuid

API_BASE = "http://localhost:5555"
DB_API_URL = f"{API_BASE}/api/media-db"


class TestListMediaEdgeCases:
    """Test edge cases that could cause 500 errors in list_media endpoint."""
    
    def test_list_handles_none_topics(self):
        """
        Test that list endpoint handles videos with None topics without crashing.
        This tests the specific bug: len(analysis.get('topics', [])) when topics is None
        """
        response = httpx.get(f"{DB_API_URL}/list?limit=500", timeout=30)
        
        # Should not return 500 even if some videos have None topics
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Error: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        
        # Verify all items have required fields even if topics is None
        for item in data:
            assert "media_id" in item
            assert "filename" in item
            assert "status" in item
            # topics can be None, but should not cause errors
            if "topics" in item:
                # topics should be None or a list, never cause len() errors
                assert item["topics"] is None or isinstance(item["topics"], list)
    
    def test_list_handles_incomplete_analysis(self):
        """
        Test that list endpoint handles videos with incomplete analysis.
        Videos with missing transcript, topics, or score should still be returned.
        """
        response = httpx.get(f"{DB_API_URL}/list?limit=500", timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should return videos even if analysis is incomplete
        incomplete_count = 0
        for item in data:
            # Videos can have incomplete analysis (missing transcript, topics, or score)
            if item.get("status") == "ingested":
                incomplete_count += 1
                # Should still have all required fields
                assert "media_id" in item
                assert "filename" in item
        
        # Log for debugging
        print(f"Found {incomplete_count} videos with incomplete analysis")
    
    def test_list_handles_missing_analysis(self):
        """
        Test that list endpoint handles videos with no analysis record.
        """
        response = httpx.get(f"{DB_API_URL}/list?limit=500", timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        # All items should be valid even without analysis
        for item in data:
            assert "media_id" in item
            assert "status" in item
            # transcript, topics, pre_social_score can all be None
            assert item.get("transcript") is None or isinstance(item.get("transcript"), str)
            assert item.get("topics") is None or isinstance(item.get("topics"), list)
            assert item.get("pre_social_score") is None or isinstance(item.get("pre_social_score"), (int, float))
    
    def test_list_handles_none_transcript(self):
        """
        Test that list endpoint handles videos with None transcript.
        """
        response = httpx.get(f"{DB_API_URL}/list?limit=500", timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle None transcript without errors
        for item in data:
            transcript = item.get("transcript")
            # transcript can be None
            assert transcript is None or isinstance(transcript, str)
    
    def test_list_handles_none_pre_social_score(self):
        """
        Test that list endpoint handles videos with None pre_social_score.
        """
        response = httpx.get(f"{DB_API_URL}/list?limit=500", timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle None score without errors
        for item in data:
            score = item.get("pre_social_score")
            # score can be None
            assert score is None or isinstance(score, (int, float))
    
    def test_list_handles_malformed_topics(self):
        """
        Test that list endpoint handles videos with malformed topics (string instead of list).
        """
        response = httpx.get(f"{DB_API_URL}/list?limit=500", timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should handle malformed topics gracefully
        for item in data:
            topics = item.get("topics")
            # topics should be None, list, or handled gracefully
            assert topics is None or isinstance(topics, list) or isinstance(topics, str)
    
    def test_list_returns_valid_json_structure(self):
        """
        Test that all returned items have valid structure and no NoneType errors.
        """
        response = httpx.get(f"{DB_API_URL}/list?limit=500", timeout=30)
        
        assert response.status_code == 200
        data = response.json()
        
        required_fields = ["media_id", "filename", "status", "created_at"]
        optional_fields = ["transcript", "topics", "pre_social_score", "curation_status", "thumbnail_path"]
        
        for item in data:
            # Check required fields
            for field in required_fields:
                assert field in item, f"Missing required field: {field}"
                assert item[field] is not None, f"Required field {field} is None"
            
            # Check optional fields - can be None but should not cause errors
            for field in optional_fields:
                if field in item:
                    value = item[field]
                    # None is acceptable, but if present should be correct type
                    if value is not None:
                        if field == "topics":
                            assert isinstance(value, list), f"topics should be list, got {type(value)}"
                        elif field == "pre_social_score":
                            assert isinstance(value, (int, float)), f"pre_social_score should be number, got {type(value)}"
                        elif field == "transcript":
                            assert isinstance(value, str), f"transcript should be string, got {type(value)}"
    
    def test_list_with_large_limit(self):
        """
        Test that list endpoint handles large limits (500) without crashing.
        """
        response = httpx.get(f"{DB_API_URL}/list?limit=500", timeout=60)
        
        # Should not return 500 even with large limit
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Error: {response.text}"
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

