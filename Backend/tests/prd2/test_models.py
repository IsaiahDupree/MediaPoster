"""
Tests for PRD2 Supabase Models
Verifies schema definitions, enums, and defaults
Target: ~50 tests
"""
import pytest
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import ValidationError

from models.supabase_models import (
    MediaAsset, MediaAnalysis, PostingSchedule, PostingMetrics,
    Comment, AICoachInsight, CreativeBriefV2, DerivativeMediaPlan,
    SourceType, MediaType, MediaStatus, Platform, ScheduleStatus,
    SentimentLabel, DerivativeFormat, PlanStatus
)


class TestSupabaseModels:
    """Tests for Supabase Pydantic models"""

    # ============================================
    # MediaAsset Tests
    # ============================================
    
    def test_media_asset_creation(self):
        """Test basic creation of MediaAsset"""
        asset = MediaAsset(
            owner_id=uuid4(),
            source_type=SourceType.LOCAL_UPLOAD,
            storage_path="/path/to/file.mp4",
            media_type=MediaType.VIDEO
        )
        assert asset.status == MediaStatus.INGESTED
        assert isinstance(asset.id, UUID)
        assert isinstance(asset.created_at, datetime)

    def test_media_asset_enums(self):
        """Test MediaAsset enum validations"""
        asset = MediaAsset(
            owner_id=uuid4(),
            source_type="kalodata_clip",  # String conversion
            storage_path="path",
            media_type="image",
            platform_hint="tiktok"
        )
        assert asset.source_type == SourceType.KALODATA_CLIP
        assert asset.media_type == MediaType.IMAGE
        assert asset.platform_hint == Platform.TIKTOK

    def test_media_asset_optional_fields(self):
        """Test MediaAsset optional fields"""
        asset = MediaAsset(
            owner_id=uuid4(),
            source_type=SourceType.LOCAL_UPLOAD,
            storage_path="path",
            media_type=MediaType.VIDEO,
            duration_sec=60.5,
            resolution="1080x1920"
        )
        assert asset.duration_sec == 60.5
        assert asset.resolution == "1080x1920"

    def test_media_asset_invalid_enum(self):
        """Test MediaAsset with invalid enum raises error"""
        with pytest.raises(ValidationError):
            MediaAsset(
                owner_id=uuid4(),
                source_type="INVALID_SOURCE",
                storage_path="path",
                media_type=MediaType.VIDEO
            )

    def test_media_asset_defaults(self):
        """Test default values for MediaAsset"""
        asset = MediaAsset(
            owner_id=uuid4(),
            source_type=SourceType.REPURPOSED,
            storage_path="path",
            media_type=MediaType.VIDEO
        )
        assert asset.status == MediaStatus.INGESTED
        assert asset.platform_hint == Platform.MULTI

    # ============================================
    # MediaAnalysis Tests
    # ============================================

    def test_media_analysis_creation(self):
        """Test basic creation of MediaAnalysis"""
        analysis = MediaAnalysis(
            media_id=uuid4(),
            transcript="Hello world"
        )
        assert analysis.transcript == "Hello world"
        assert analysis.frames_sampled == 0
        assert analysis.sentiment_overall is None

    def test_media_analysis_scores(self):
        """Test score constraints range 0-100"""
        analysis = MediaAnalysis(
            media_id=uuid4(),
            pre_social_score=85.5
        )
        assert analysis.pre_social_score == 85.5
        
        with pytest.raises(ValidationError):
            MediaAnalysis(media_id=uuid4(), pre_social_score=101.0)
            
        with pytest.raises(ValidationError):
            MediaAnalysis(media_id=uuid4(), pre_social_score=-1.0)

    def test_media_analysis_json_fields(self):
        """Test JSON field defaults"""
        analysis = MediaAnalysis(media_id=uuid4())
        assert analysis.topics == []
        assert analysis.virality_features == {}
        assert analysis.ai_caption_suggestions == []

    def test_media_analysis_full_population(self):
        """Test fully populated MediaAnalysis"""
        analysis = MediaAnalysis(
            media_id=uuid4(),
            transcript="Text",
            transcript_language="fr",
            topics=["tech", "ai"],
            frames_sampled=10,
            best_frame_index=5,
            best_frame_url="http://url.com/img.jpg",
            virality_features={"hook_strength": "high"},
            pre_social_score=90.0,
            pre_social_explanation="Good hook"
        )
        assert analysis.transcript_language == "fr"
        assert "tech" in analysis.topics
        assert analysis.best_frame_index == 5

    # ============================================
    # PostingSchedule Tests
    # ============================================

    def test_posting_schedule_creation(self):
        """Test creation of PostingSchedule"""
        schedule = PostingSchedule(
            media_id=uuid4(),
            platform=Platform.TIKTOK,
            scheduled_at=datetime.utcnow()
        )
        assert schedule.status == ScheduleStatus.PENDING
        assert schedule.platform == Platform.TIKTOK

    def test_posting_schedule_status_update(self):
        """Test status update logic"""
        schedule = PostingSchedule(
            media_id=uuid4(),
            platform=Platform.YOUTUBE_SHORTS,
            scheduled_at=datetime.utcnow(),
            status=ScheduleStatus.POSTED,
            external_post_id="ext-123"
        )
        assert schedule.status == ScheduleStatus.POSTED
        assert schedule.external_post_id == "ext-123"

    def test_posting_schedule_invalid_platform(self):
        """Test invalid platform enum"""
        with pytest.raises(ValidationError):
            PostingSchedule(
                media_id=uuid4(),
                platform="myspace",
                scheduled_at=datetime.utcnow()
            )

    # ============================================
    # PostingMetrics Tests
    # ============================================

    def test_posting_metrics_defaults(self):
        """Test zero defaults for metrics"""
        metrics = PostingMetrics(schedule_id=uuid4())
        assert metrics.views == 0
        assert metrics.likes == 0
        assert metrics.shares == 0

    def test_posting_metrics_population(self):
        """Test population of metrics"""
        metrics = PostingMetrics(
            schedule_id=uuid4(),
            views=1000,
            likes=100,
            ctr=5.5,
            post_social_score=80.0
        )
        assert metrics.views == 1000
        assert metrics.ctr == 5.5
        assert metrics.post_social_score == 80.0

    def test_posting_metrics_score_validation(self):
        """Test post_social_score validation"""
        with pytest.raises(ValidationError):
            PostingMetrics(schedule_id=uuid4(), post_social_score=150)

    # ============================================
    # Comment Tests
    # ============================================

    def test_comment_creation(self):
        """Test Comment creation"""
        comment = Comment(
            schedule_id=uuid4(),
            platform_comment_id="c1",
            author_handle="@user",
            text="Great video!"
        )
        assert comment.like_count == 0
        assert comment.sentiment_label == SentimentLabel.NEUTRAL

    def test_comment_sentiment_enum(self):
        """Test SentimentLabel enum"""
        comment = Comment(
            schedule_id=uuid4(),
            platform_comment_id="c1",
            author_handle="u",
            text="t",
            sentiment_label="positive"
        )
        assert comment.sentiment_label == SentimentLabel.POSITIVE

    # ============================================
    # AICoachInsight Tests
    # ============================================

    def test_coach_insight_creation(self):
        """Test AICoachInsight creation"""
        insight = AICoachInsight(
            media_id=uuid4(),
            checkpoint="24h",
            summary="Doing well",
            what_worked=["Hook", "Pacing"],
            what_to_change=["CTA"]
        )
        assert insight.checkpoint == "24h"
        assert len(insight.what_worked) == 2
        assert insight.next_actions == []

    def test_coach_insight_optional_schedule(self):
        """Test optional schedule_id"""
        insight = AICoachInsight(
            media_id=uuid4(),
            checkpoint="7d",
            summary="Done"
        )
        assert insight.schedule_id is None

    # ============================================
    # CreativeBriefV2 Tests
    # ============================================

    def test_creative_brief_v2_creation(self):
        """Test CreativeBriefV2 creation"""
        brief = CreativeBriefV2(
            source_type=SourceType.KALODATA_CLIP,
            angle_name="Viral Hook",
            target_audience="Gen Z",
            core_promise="Entertainment"
        )
        assert brief.ready_for_use is False
        assert brief.hook_ideas == []

    def test_creative_brief_structured_fields(self):
        """Test structured dict fields"""
        brief = CreativeBriefV2(
            source_type=SourceType.PROMPT_ONLY,
            angle_name="Test",
            target_audience="Test",
            core_promise="Test",
            script_outline={"intro": ["Line 1"]},
            visual_directions={"broll": ["Shot 1"]}
        )
        assert brief.script_outline["intro"][0] == "Line 1"

    # ============================================
    # DerivativeMediaPlan Tests
    # ============================================

    def test_derivative_plan_creation(self):
        """Test DerivativeMediaPlan creation"""
        plan = DerivativeMediaPlan(
            format_type=DerivativeFormat.BROLL_TEXT,
            instructions="Overlay text on video",
            target_platform=Platform.TIKTOK,
            estimated_length_sec=15
        )
        assert plan.status == PlanStatus.PLANNED
        assert plan.estimated_length_sec == 15

    def test_derivative_plan_enums(self):
        """Test DerivativeFormat enum"""
        plan = DerivativeMediaPlan(
            format_type="face_cam",
            instructions="Talk to camera",
            target_platform="instagram_reels",
            estimated_length_sec=30
        )
        assert plan.format_type == DerivativeFormat.FACE_CAM

    # ============================================
    # Integration / Reference Tests
    # ============================================

    def test_model_interconnectedness(self):
        """Test that models can logically link via IDs"""
        media = MediaAsset(
            owner_id=uuid4(),
            source_type=SourceType.LOCAL_UPLOAD,
            storage_path="path",
            media_type=MediaType.VIDEO
        )
        
        analysis = MediaAnalysis(media_id=media.id)
        
        schedule = PostingSchedule(
            media_id=media.id,
            platform=Platform.TIKTOK,
            scheduled_at=datetime.utcnow()
        )
        
        metrics = PostingMetrics(schedule_id=schedule.id)
        
        assert analysis.media_id == media.id
        assert schedule.media_id == media.id
        assert metrics.schedule_id == schedule.id
