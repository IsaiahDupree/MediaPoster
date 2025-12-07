"""
Test Suite for Enhanced Analysis API Endpoints
Tests segment management, validation, and performance endpoints
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import uuid

from main import app
from database.models import VideoSegment, AnalyzedVideo


client = TestClient(app)


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    with patch('api.endpoints.enhanced_analysis.get_db') as mock:
        db = MagicMock()
        mock.return_value = db
        yield db


class TestSegmentCRUD:
    """Test segment CRUD endpoints"""
    
    def test_create_segment_success(self, mock_db_session):
        """Test successful segment creation"""
        with patch('api.endpoints.enhanced_analysis.SegmentEditor') as MockEditor:
            mock_editor = MockEditor.return_value
            mock_segment = Mock(spec=VideoSegment)
            mock_segment.id = uuid.uuid4()
            mock_editor.create_segment.return_value = mock_segment
            
            response = client.post(
                "/api/enhanced-analysis/segments",
                json={
                    "video_id": str(uuid.uuid4()),
                    "start_time": 5.0,
                    "end_time": 15.0,
                    "segment_type": "hook"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "segment_id" in data
            assert data["status"] == "created"
    
    def test_create_segment_invalid_data(self, mock_db_session):
        """Test segment creation with invalid timing"""
        with patch('api.endpoints.enhanced_analysis.SegmentEditor') as MockEditor:
            mock_editor = MockEditor.return_value
            mock_editor.create_segment.side_effect = ValueError("End time must be greater than start")
            
            response = client.post(
                "/api/enhanced-analysis/segments",
                json={
                    "video_id": str(uuid.uuid4()),
                    "start_time": 20.0,
                    "end_time": 10.0,
                    "segment_type": "hook"
                }
            )
            
            assert response.status_code == 400
            assert "End time must be greater than start" in response.json()["detail"]
    
    def test_update_segment_success(self, mock_db_session):
        """Test successful segment update"""
        with patch('api.endpoints.enhanced_analysis.SegmentEditor') as MockEditor:
            mock_editor = MockEditor.return_value
            mock_segment = Mock(spec=VideoSegment)
            mock_segment.id = uuid.uuid4()
            mock_editor.update_segment.return_value = mock_segment
            
            segment_id = str(uuid.uuid4())
            response = client.put(
                f"/api/enhanced-analysis/segments/{segment_id}",
                json={
                    "segment_type": "body",
                    "edit_reason": "Reclassified"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "updated"
    
    def test_delete_segment_success(self, mock_db_session):
        """Test successful segment deletion"""
        with patch('api.endpoints.enhanced_analysis.SegmentEditor') as MockEditor:
            mock_editor = MockEditor.return_value
            mock_editor.delete_segment.return_value = True
            
            segment_id = str(uuid.uuid4())
            response = client.delete(f"/api/enhanced-analysis/segments/{segment_id}")
            
            assert response.status_code == 200
            assert "deleted" in response.json()["message"]
    
    def test_delete_nonexistent_segment(self, mock_db_session):
        """Test deleting non-existent segment"""
        with patch('api.endpoints.enhanced_analysis.SegmentEditor') as MockEditor:
            mock_editor = MockEditor.return_value
            mock_editor.delete_segment.return_value = False
            
            segment_id = str(uuid.uuid4())
            response = client.delete(f"/api/enhanced-analysis/segments/{segment_id}")
            
            assert response.status_code == 404


class TestSegmentOperations:
    """Test split and merge operations"""
    
    def test_split_segment(self, mock_db_session):
        """Test segment splitting"""
        with patch('api.endpoints.enhanced_analysis.SegmentEditor') as MockEditor:
            mock_editor = MockEditor.return_value
            
            seg1 = Mock(spec=VideoSegment)
            seg1.id = uuid.uuid4()
            seg2 = Mock(spec=VideoSegment)
            seg2.id = uuid.uuid4()
            
            mock_editor.split_segment.return_value = (seg1, seg2)
            
            segment_id = str(uuid.uuid4())
            response = client.post(
                f"/api/enhanced-analysis/segments/{segment_id}/split",
                json={
                    "split_time": 12.5,
                    "edit_reason": "Split at midpoint"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "segments" in data
            assert len(data["segments"]) == 2
    
    def test_split_invalid_time(self, mock_db_session):
        """Test split with invalid time"""
        with patch('api.endpoints.enhanced_analysis.SegmentEditor') as MockEditor:
            mock_editor = MockEditor.return_value
            mock_editor.split_segment.side_effect = ValueError("Split time must be between")
            
            segment_id = str(uuid.uuid4())
            response = client.post(
                f"/api/enhanced-analysis/segments/{segment_id}/split",
                json={"split_time": 100.0}
            )
            
            assert response.status_code == 400
    
    def test_merge_segments(self, mock_db_session):
        """Test segment merging"""
        with patch('api.endpoints.enhanced_analysis.SegmentEditor') as MockEditor:
            mock_editor = MockEditor.return_value
            
            merged = Mock(spec=VideoSegment)
            merged.id = uuid.uuid4()
            mock_editor.merge_segments.return_value = merged
            
            response = client.post(
                "/api/enhanced-analysis/segments/merge",
                json={
                    "segment_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
                    "merged_type": "body"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "merged"


class TestValidation:
    """Test validation endpoints"""
    
    def test_validate_analysis(self, mock_db_session):
        """Test analysis validation"""
        with patch('api.endpoints.enhanced_analysis.SegmentEditor') as MockEditor:
            from services.segment_editor import ValidationResult, ValidationIssue
            
            mock_editor = MockEditor.return_value
            mock_result = ValidationResult(
                is_valid=True,
                issues=[],
                total_segments=5,
                manual_segments=2,
                auto_segments=3
            )
            mock_editor.validate_segments.return_value = mock_result
            
            video_id = str(uuid.uuid4())
            response = client.get(f"/api/enhanced-analysis/videos/{video_id}/validate")
            
            assert response.status_code == 200
            data = response.json()
            assert data["is_valid"] is True
            assert data["total_segments"] == 5


class TestPerformanceEndpoints:
    """Test performance correlation endpoints"""
    
    def test_get_top_patterns(self, mock_db_session):
        """Test getting top performing patterns"""
        with patch('api.endpoints.enhanced_analysis.PerformanceCorrelator') as MockCorrelator:
            mock_correlator = MockCorrelator.return_value
            mock_correlator.find_top_performing_patterns.return_value = [
                {"pattern": "fear", "avg_score": 0.85, "sample_size": 10, "type": "hook"},
                {"pattern": "authority", "avg_score": 0.75, "sample_size": 8, "type": "hook"}
            ]
            
            response = client.get(
                "/api/enhanced-analysis/patterns/top-performing?pattern_type=hook&limit=10"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["pattern"] == "fear"
    
    def test_predict_performance(self, mock_db_session):
        """Test performance prediction"""
        with patch('api.endpoints.enhanced_analysis.PerformanceCorrelator') as MockCorrelator:
            mock_correlator = MockCorrelator.return_value
            mock_correlator.predict_segment_performance.return_value = {
                "predicted_score": 0.72,
                "confidence": "medium",
                "factors": {
                    "baseline": 0.5,
                    "hook_impact": 0.15,
                    "emotion_impact": 0.07
                }
            }
            
            response = client.post(
                "/api/enhanced-analysis/predict",
                json={
                    "segment_type": "hook",
                    "psychology_tags": {"fate_patterns": ["fear"]},
                    "duration": 10.0
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "predicted_score" in data
            assert data["confidence"] == "medium"


class TestExport:
    """Test export functionality"""
    
    def test_export_analysis(self, mock_db_session):
        """Test exporting analysis data"""
        with patch('api.endpoints.enhanced_analysis.ContentAnalysisOrchestrator') as MockOrch:
            mock_orch = MockOrch.return_value
            mock_orch.export_analysis.return_value = {
                "video_id": str(uuid.uuid4()),
                "duration": 60.0,
                "transcript": "Test transcript",
                "segments": []
            }
            
            video_id = str(uuid.uuid4())
            response = client.get(f"/api/enhanced-analysis/videos/{video_id}/export")
            
            assert response.status_code == 200
            data = response.json()
            assert "video_id" in data
            assert "segments" in data
    
    def test_export_nonexistent_video(self, mock_db_session):
        """Test exporting non-existent video"""
        with patch('api.endpoints.enhanced_analysis.ContentAnalysisOrchestrator') as MockOrch:
            mock_orch = MockOrch.return_value
            mock_orch.export_analysis.side_effect = ValueError("Video not found")
            
            video_id = str(uuid.uuid4())
            response = client.get(f"/api/enhanced-analysis/videos/{video_id}/export")
            
            assert response.status_code == 404
