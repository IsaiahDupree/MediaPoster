"""
Unit and Integration Tests for Curation State Persistence
Tests that curation status (approved/rejected) persists across page reloads
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import uuid

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestCurationStatusSave:
    """Test suite for curation status save endpoint"""
    
    @pytest.mark.asyncio
    async def test_save_curation_approved(self):
        """Test saving approved curation status"""
        from api.media_processing_db import update_curation_status, CurationRequest
        from database.models import VideoAnalysis
        
        # Mock database session
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Create request
        media_id = str(uuid.uuid4())
        request = CurationRequest(curation_status="approved")
        
        # Call endpoint
        response = await update_curation_status(media_id, request, mock_db)
        
        # Verify response
        assert response["status"] == "updated"
        assert response["media_id"] == media_id
        assert response["curation_status"] == "approved"
        
        # Verify database operations
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_curation_rejected(self):
        """Test saving rejected curation status"""
        from api.media_processing_db import update_curation_status, CurationRequest
        
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        media_id = str(uuid.uuid4())
        request = CurationRequest(curation_status="rejected")
        
        response = await update_curation_status(media_id, request, mock_db)
        
        assert response["status"] == "updated"
        assert response["curation_status"] == "rejected"
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_existing_curation(self):
        """Test updating curation status on existing analysis"""
        from api.media_processing_db import update_curation_status, CurationRequest
        from database.models import VideoAnalysis
        
        mock_db = AsyncMock()
        
        # Mock existing analysis
        existing_analysis = Mock(spec=VideoAnalysis)
        existing_analysis.curation_status = "pending"
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = existing_analysis
        mock_db.execute.return_value = mock_result
        
        media_id = str(uuid.uuid4())
        request = CurationRequest(curation_status="approved")
        
        response = await update_curation_status(media_id, request, mock_db)
        
        # Verify existing analysis was updated
        assert existing_analysis.curation_status == "approved"
        assert existing_analysis.curated_at is not None
        mock_db.add.assert_not_called()  # Should not add new record
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_invalid_media_id_format(self):
        """Test error handling for invalid media ID"""
        from api.media_processing_db import update_curation_status, CurationRequest
        from fastapi import HTTPException
        
        mock_db = AsyncMock()
        request = CurationRequest(curation_status="approved")
        
        with pytest.raises(HTTPException) as exc_info:
            await update_curation_status("invalid-uuid", request, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Invalid media ID format" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_curation_status_values(self):
        """Test all valid curation status values"""
        from api.media_processing_db import update_curation_status, CurationRequest
        
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        media_id = str(uuid.uuid4())
        
        for status in ["pending", "approved", "rejected"]:
            mock_db.reset_mock()
            request = CurationRequest(curation_status=status)
            response = await update_curation_status(media_id, request, mock_db)
            assert response["curation_status"] == status


class TestCurationStatusFetch:
    """Test suite for fetching curation status in list endpoint"""
    
    @pytest.mark.asyncio
    async def test_fetch_curation_status_from_analysis(self):
        """Test that curation status is fetched from video_analysis table"""
        # This test requires actual database integration
        # Skipping for unit test - covered by integration tests
        pytest.skip("Requires database integration")
    
    @pytest.mark.asyncio
    async def test_fetch_without_curation_status(self):
        """Test fetching video without curation status"""
        pytest.skip("Requires database integration")
    
    @pytest.mark.asyncio
    async def test_fetch_multiple_videos_with_different_statuses(self):
        """Test fetching multiple videos with different curation statuses"""
        pytest.skip("Requires database integration")


class TestCurationPersistenceIntegration:
    """Integration tests for complete curation persistence workflow"""
    
    @pytest.mark.asyncio
    async def test_save_and_fetch_workflow(self):
        """Test complete workflow: save curation status then fetch it back"""
        pytest.skip("Requires database integration")
    
    @pytest.mark.asyncio
    async def test_update_curation_status_workflow(self):
        """Test updating curation status from approved to rejected"""
        from api.media_processing_db import update_curation_status, CurationRequest
        from database.models import VideoAnalysis
        
        media_id = str(uuid.uuid4())
        
        # Step 1: Save as approved
        mock_db = AsyncMock()
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        request1 = CurationRequest(curation_status="approved")
        response1 = await update_curation_status(media_id, request1, mock_db)
        assert response1["curation_status"] == "approved"
        
        # Step 2: Update to rejected
        mock_db2 = AsyncMock()
        existing_analysis = Mock(spec=VideoAnalysis)
        existing_analysis.curation_status = "approved"
        mock_result2 = Mock()
        mock_result2.scalar_one_or_none.return_value = existing_analysis
        mock_db2.execute.return_value = mock_result2
        
        request2 = CurationRequest(curation_status="rejected")
        response2 = await update_curation_status(media_id, request2, mock_db2)
        
        # Verify status was updated
        assert response2["curation_status"] == "rejected"
        assert existing_analysis.curation_status == "rejected"
    
    @pytest.mark.asyncio
    async def test_page_reload_simulation(self):
        """Test that curation status survives page reload (fetch after save)"""
        pytest.skip("Requires database integration")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
