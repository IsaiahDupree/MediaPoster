"""
Tests for Posting Service (PRD2)
Verifies publishing workflow, error handling, and metrics creation
Target: ~30 tests
"""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from services.prd2.posting_service import PostingService
from models.supabase_models import (
    PostingSchedule, MediaAsset, MediaAnalysis, 
    ScheduleStatus, Platform, SourceType, MediaType
)

class TestPostingService:
    """Tests for posting workflow"""

    @pytest.fixture
    def service(self):
        return PostingService()

    @pytest.fixture
    def setup_data(self):
        """Create linked asset, analysis, and schedule"""
        asset = MediaAsset(
            id=uuid4(), owner_id=uuid4(), source_type=SourceType.LOCAL_UPLOAD,
            storage_path="valid_path", media_type=MediaType.VIDEO
        )
        analysis = MediaAnalysis(media_id=asset.id)
        # Scheduled in past (due)
        schedule = PostingSchedule(
            id=uuid4(), media_id=asset.id, platform=Platform.TIKTOK,
            scheduled_at=datetime.utcnow() - timedelta(hours=1)
        )
        return asset, analysis, schedule

    # ============================================
    # Workflow Logic Tests
    # ============================================

    def test_process_due_posts_success(self, service, setup_data):
        """Test successful posting workflow"""
        asset, analysis, schedule = setup_data
        
        results = service.process_due_posts([schedule], [asset], [analysis])
        
        assert len(results) == 1
        updated_schedule, metrics = results[0]
        
        assert updated_schedule.status == ScheduleStatus.POSTED
        assert updated_schedule.external_post_id is not None
        assert metrics.schedule_id == schedule.id

    def test_process_future_posts_ignored(self, service, setup_data):
        """Test future posts are not processed"""
        asset, analysis, schedule = setup_data
        schedule.scheduled_at = datetime.utcnow() + timedelta(hours=1)
        
        results = service.process_due_posts([schedule], [asset], [analysis])
        assert len(results) == 0
        assert schedule.status == ScheduleStatus.PENDING

    def test_process_failed_post_simulated(self, service, setup_data):
        """Test failure scenario (simulated by filename)"""
        asset, analysis, schedule = setup_data
        asset.storage_path = "error_trigger"
        
        results = service.process_due_posts([schedule], [asset], [analysis])
        
        assert len(results) == 0  # No metrics created for failed
        assert schedule.status == ScheduleStatus.FAILED

    def test_process_missing_asset(self, service, setup_data):
        """Test handling of orphaned schedule"""
        _, analysis, schedule = setup_data
        
        # Don't pass asset
        results = service.process_due_posts([schedule], [], [analysis])
        
        assert len(results) == 0
        assert schedule.status == ScheduleStatus.FAILED

    def test_process_missing_analysis(self, service, setup_data):
        """Test processing without analysis data"""
        asset, _, schedule = setup_data
        
        results = service.process_due_posts([schedule], [asset], [])
        
        assert len(results) == 0
        assert schedule.status == ScheduleStatus.FAILED

    # ============================================
    # Metrics Initialization Tests
    # ============================================

    def test_metrics_initialization(self, service, setup_data):
        """Test metrics creation details"""
        _, _, schedule = setup_data
        metrics = service._initialize_metrics(schedule.id)
        
        assert metrics.views == 0
        assert metrics.schedule_id == schedule.id

    # ============================================
    # Blotato Integration Mock Tests
    # ============================================

    def test_blotato_mock_success(self, service, setup_data):
        """Verify mock returns true"""
        asset, analysis, schedule = setup_data
        assert service._publish_to_blotato(schedule, asset, analysis) is True

    def test_blotato_mock_failure(self, service, setup_data):
        """Verify mock returns false on error trigger"""
        asset, analysis, schedule = setup_data
        asset.storage_path = "error_file"
        assert service._publish_to_blotato(schedule, asset, analysis) is False

    # ============================================
    # Bulk Processing Tests
    # ============================================

    def test_bulk_processing_mixed(self, service):
        """Test processing mixed due/future items"""
        schedules = []
        assets = []
        analyses = []
        
        # 1. Due
        a1 = MediaAsset(id=uuid4(), owner_id=uuid4(), source_type="local_upload", storage_path="p", media_type="video")
        s1 = PostingSchedule(id=uuid4(), media_id=a1.id, platform="tiktok", scheduled_at=datetime.utcnow() - timedelta(hours=1))
        
        # 2. Future
        a2 = MediaAsset(id=uuid4(), owner_id=uuid4(), source_type="local_upload", storage_path="p", media_type="video")
        s2 = PostingSchedule(id=uuid4(), media_id=a2.id, platform="tiktok", scheduled_at=datetime.utcnow() + timedelta(hours=1))
        
        schedules = [s1, s2]
        assets = [a1, a2]
        analyses = [MediaAnalysis(media_id=a1.id), MediaAnalysis(media_id=a2.id)]
        
        results = service.process_due_posts(schedules, assets, analyses)
        
        assert len(results) == 1
        assert s1.status == ScheduleStatus.POSTED
        assert s2.status == ScheduleStatus.PENDING

    # ============================================
    # Error state transitions
    # ============================================

    def test_already_posted_ignored(self, service, setup_data):
        """Test that POSTED items are skipped even if time is past"""
        asset, analysis, schedule = setup_data
        schedule.status = ScheduleStatus.POSTED
        
        results = service.process_due_posts([schedule], [asset], [analysis])
        assert len(results) == 0
