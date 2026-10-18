"""
End-to-End Pipeline Tests for PRD2 System
Verifies the full lifecycle of a media asset from ingestion to derivative planning.
"""
import pytest
import shutil
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timedelta

from models.supabase_models import (
    MediaAsset, MediaAnalysis, PostingSchedule, PostingMetrics,
    MediaStatus, ScheduleStatus, SourceType, MediaType, Platform
)
from services.prd2.ingestion_service import IngestionService
from services.prd2.analysis_service import AnalysisService
from services.prd2.scheduling_service import SchedulingService
from services.prd2.posting_service import PostingService
from services.prd2.metrics_service import MetricsService
from services.prd2.coach_service import CoachService

class TestE2EPipeline:
    """Full system integration tests"""

    @pytest.fixture
    def environment(self, tmp_path):
        """Setup services and temp directories"""
        inbox = tmp_path / "inbox"
        inbox.mkdir()
        (inbox / "viral_clip.mp4").write_text("content")
        
        return {
            "ingest": IngestionService(str(inbox)),
            "analyze": AnalysisService(),
            "schedule": SchedulingService(),
            "post": PostingService(),
            "metrics": MetricsService(),
            "coach": CoachService(),
            "inbox_path": inbox
        }

    def test_full_lifecycle_viral_hit(self, environment):
        """
        Scenario: 
        1. Ingest a video
        2. Analyze it (mocked as viral)
        3. Schedule it
        4. Post it
        5. Poll metrics (viral result)
        6. Coach realizes it's a hit -> Suggests Remix
        """
        owner_id = uuid4()
        srv = environment
        
        # 1. INGEST
        assets = srv["ingest"].ingest_new_files(owner_id)
        assert len(assets) == 1
        asset = assets[0]
        assert asset.status == MediaStatus.INGESTED
        
        # 2. ANALYZE
        # We Mock internal analysis logic to guarantee high pre-score
        # But here we rely on the service's current mock which depends on features
        # Let's patch the analysis service for deterministic E2E behavior without full mock
        # Actually the service has mocked logic: 
        # _calculate_pre_social_score checks for features/transcript logic
        # We'll just assume the default behavior for now, or use a separate test-specific subclass if needed.
        # WAIT: The current AnalysisService stub uses hardcoded internal methods. 
        # We need to rely on what `analyze_media` calls.
        # It calls `_analyze_frames` which returns a hardcoded dict with "hook_strength": "high", "pacing": "fast", etc.
        # This results in a high score automatically. Perfect for this test.
        
        analysis = srv["analyze"].analyze_media(asset)
        assert analysis.pre_social_score > 50  # Based on current stub
        asset.status = MediaStatus.ANALYZED
        
        # 3. SCHEDULE
        schedules = srv["schedule"].generate_schedule([asset])
        assert len(schedules) == 1
        schedule = schedules[0]
        assert schedule.status == ScheduleStatus.PENDING
        
        # Force schedule to be "due" for posting
        schedule.scheduled_at = datetime.utcnow() - timedelta(minutes=5)
        
        # 4. POST
        results = srv["post"].process_due_posts(
            schedules=[schedule], 
            assets=[asset], 
            analysis=[analysis]
        )
        assert len(results) == 1
        published_schedule, metrics_row = results[0]
        assert published_schedule.status == ScheduleStatus.POSTED
        assert metrics_row.views == 0
        
        # 5. POLLING METRICS
        # Poll "viral_123" to get high numbers (hardcoded in MetricsService check)
        srv["metrics"].poll_metrics(metrics_row, "viral_123", Platform.TIKTOK)
        assert metrics_row.views == 1000000
        assert metrics_row.post_social_score > 90 # High engagement logic
        
        # 6. COACH INSIGHTS
        insight = srv["coach"].generate_insight(
            analysis, metrics_row, comments=[], checkpoint="24h"
        )
        assert "Viral hit" in insight.summary
        assert insight.input_snapshot["post_score"] > 90
        
        # 7. DERIVATIVE PLANS
        plans = srv["coach"].generate_derivative_plans(insight)
        assert len(plans) == 2  # Face Cam + Broll
        assert plans[0].status == "planned"

    def test_full_lifecycle_flop(self, environment):
        """
        Scenario:
        Low performance -> Coach suggestions for improvement
        """
        owner_id = uuid4()
        srv = environment
        
        # 1-4. Setup (Ingest->Post)
        assets = srv["ingest"].ingest_new_files(owner_id)
        asset = assets[0]
        analysis = srv["analyze"].analyze_media(asset) # High pre-score (stub)
        schedule = srv["schedule"].generate_schedule([asset])[0]
        schedule.scheduled_at = datetime.utcnow() - timedelta(minutes=5)
        _, metrics_row = srv["post"].process_due_posts([schedule], [asset], [analysis])[0]
        
        # 5. POLL METRICS (Average/Flop)
        # using any ID other than 'viral' results in low stats
        srv["metrics"].poll_metrics(metrics_row, "avg_video_id", Platform.TIKTOK)
        assert metrics_row.views == 100
        assert metrics_row.post_social_score < 50
        
        # 6. COACH
        insight = srv["coach"].generate_insight(
            analysis, metrics_row, [], "7d"
        )
        
        # High pre-score (70+) vs Low post-score (<50) -> Underperformed
        assert "Underperformed" in insight.summary
        
        # 7. PLANS
        plans = srv["coach"].generate_derivative_plans(insight)
        assert len(plans) == 0 # Don't remix a flop
