"""
Tests for Analysis Service (PRD2)
Verifies scoring logic, transcription, and analysis workflow
Target: ~30 tests
"""
import pytest
from uuid import uuid4
from unittest.mock import patch, MagicMock

from services.prd2.analysis_service import AnalysisService
from models.supabase_models import MediaAsset, SourceType, MediaType, MediaAnalysis

class TestAnalysisService:
    """Tests for AI analysis service"""

    @pytest.fixture
    def service(self):
        return AnalysisService()

    @pytest.fixture
    def sample_asset(self):
        return MediaAsset(
            owner_id=uuid4(),
            source_type=SourceType.LOCAL_UPLOAD,
            storage_path="/path/test.mp4",
            media_type=MediaType.VIDEO
        )

    # ============================================
    # Scoring Logic Tests
    # ============================================

    def test_calculate_perfect_score(self, service):
        """Test score calculation for perfect viral inputs"""
        vision = {
            "features": {
                "hook_strength": "high", # +30
                "pacing": "fast",        # +20
                "face_detected": True,   # +20
                "text_overlay": True     # +10
            }
        }
        transcript = "viral keyword"     # +20
        
        score, explanation = service._calculate_pre_social_score(vision, transcript)
        assert score == 100.0
        assert "Strong hook" in explanation

    def test_calculate_partial_score(self, service):
        """Test score calculation for partial inputs"""
        vision = {
            "features": {
                "hook_strength": "low", # 0
                "pacing": "slow",       # 0
                "face_detected": True,  # +20
                "text_overlay": False   # 0
            }
        }
        transcript = "boring text"      # 0
        
        score, explanation = service._calculate_pre_social_score(vision, transcript)
        assert score == 20.0
        assert "Face detected" in explanation

    def test_calculate_min_score(self, service):
        """Test minimum score"""
        vision = {"features": {}}
        transcript = ""
        score, _ = service._calculate_pre_social_score(vision, transcript)
        assert score == 0.0

    def test_calculate_score_cap(self, service):
        """Test score is capped at 100"""
        vision = {
            "features": {
                "hook_strength": "high", # +30
                "pacing": "fast",        # +20
                "face_detected": True,   # +20
                "text_overlay": True,    # +10
                "extra_feature": True    # (mocking generic boost if logic changes)
            }
        }
        transcript = "viral viral viral" # +20 => 100
        # Even if we added more logic, ensuring cap
        score, _ = service._calculate_pre_social_score(vision, transcript)
        assert score <= 100.0

    # ============================================
    # Component Mock Tests
    # ============================================

    def test_transcription_stub(self, service):
        """Test transcription returns string"""
        res = service._transcribe_audio("any")
        assert isinstance(res, str)
        assert len(res) > 0

    def test_vision_stub(self, service):
        """Test vision analysis returns dict"""
        res = service._analyze_frames("any")
        assert isinstance(res, dict)
        assert "features" in res

    # ============================================
    # Full Workflow Tests
    # ============================================

    def test_analyze_media_workflow(self, service, sample_asset):
        """Test full analysis workflow returns MediaAnalysis"""
        analysis = service.analyze_media(sample_asset)
        
        assert isinstance(analysis, MediaAnalysis)
        assert analysis.media_id == sample_asset.id
        assert analysis.pre_social_score is not None
        assert len(analysis.topics) > 0
        assert len(analysis.ai_caption_suggestions) > 0

    def test_analyze_integration_mock(self, service, sample_asset):
        """Test workflow with mocked internals"""
        with patch.object(service, '_transcribe_audio', return_value="viral"):
            with patch.object(service, '_analyze_frames', return_value={"features": {"pacing": "fast"}}):
                analysis = service.analyze_media(sample_asset)
                
                # "viral" (+20) + "fast" (+20) = 40
                assert analysis.pre_social_score == 40.0
                assert analysis.transcript == "viral"

    def test_analyze_media_id_link(self, service, sample_asset):
        """Test analysis correctly links to asset ID"""
        analysis = service.analyze_media(sample_asset)
        assert analysis.media_id == sample_asset.id

    def test_analysis_defaults(self, service, sample_asset):
        """Test default values in generated analysis"""
        analysis = service.analyze_media(sample_asset)
        assert analysis.frames_sampled > 0
        assert analysis.transcript_language == "en"

    # ============================================
    # Error Handling Tests
    # ============================================

    def test_analyze_invalid_asset(self, service):
        """Test handling of invalid asset (if strict type checking passes)"""
        # Pydantic handles type check, checking runtime behavior
        with pytest.raises(AttributeError):
            service.analyze_media(None)

    def test_scoring_empty_features(self, service):
        """Test scoring with missing feature keys"""
        vision = {"features": {}} # Empty
        score, _ = service._calculate_pre_social_score(vision, "")
        assert score == 0.0

    def test_scoring_case_insensitivity(self, service):
        """Test virality keywords are case insensitive"""
        vision = {"features": {}}
        score, _ = service._calculate_pre_social_score(vision, "VIRAL VIDEO")
        assert score == 20.0
