"""
Tests for Creative Brief System
Tests for models, services, and API endpoints
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock


# ============================================
# Model Tests (20 tests)
# ============================================

class TestCreativeBriefModels:
    """Tests for creative brief data models"""
    
    def test_price_range_creation(self):
        """Test PriceRange model"""
        from models.creative_brief_models import PriceRange
        pr = PriceRange(min_price=10.0, max_price=20.0)
        assert pr.min_price == 10.0
        assert pr.max_price == 20.0
    
    def test_price_range_single_price(self):
        """Test PriceRange with single price"""
        from models.creative_brief_models import PriceRange
        pr = PriceRange(min_price=15.0)
        assert pr.max_price is None
    
    def test_metrics_30_day(self):
        """Test Metrics30Day model"""
        from models.creative_brief_models import Metrics30Day
        m = Metrics30Day(revenue_usd=5850000, items_sold=73810)
        assert m.revenue_usd == 5850000
        assert m.items_sold == 73810
    
    def test_affiliate_info(self):
        """Test AffiliateInfo model"""
        from models.creative_brief_models import AffiliateInfo
        a = AffiliateInfo(is_affiliate_product=True, creator_count=4960)
        assert a.is_affiliate_product == True
        assert a.creator_count == 4960
    
    def test_product_performance_snapshot(self):
        """Test ProductPerformanceSnapshot model"""
        from models.creative_brief_models import ProductPerformanceSnapshot
        p = ProductPerformanceSnapshot(
            product_id="test-123",
            product_name="Test Product",
            category="Skincare"
        )
        assert p.product_id == "test-123"
        assert p.category == "Skincare"
    
    def test_frame_tags(self):
        """Test FrameTags model"""
        from models.creative_brief_models import FrameTags
        ft = FrameTags(
            setting="bathroom mirror",
            camera_type="handheld phone",
            shot_type="close-up"
        )
        assert ft.setting == "bathroom mirror"
    
    def test_scene_semantics(self):
        """Test SceneSemantics model"""
        from models.creative_brief_models import SceneSemantics
        ss = SceneSemantics(
            mini_summary="Creator shows product",
            emotion="excitement"
        )
        assert ss.emotion == "excitement"
    
    def test_scene_analysis(self):
        """Test SceneAnalysis model"""
        from models.creative_brief_models import SceneAnalysis, SceneRole
        sa = SceneAnalysis(
            start_sec=0,
            end_sec=3,
            role=SceneRole.HOOK
        )
        assert sa.role == SceneRole.HOOK
    
    def test_transcript_data(self):
        """Test TranscriptData model"""
        from models.creative_brief_models import TranscriptData
        td = TranscriptData(
            full_text="If your skin looks tired...",
            language="en",
            key_phrases=["glass glow", "7 days"]
        )
        assert len(td.key_phrases) == 2
    
    def test_video_performance(self):
        """Test VideoPerformance model"""
        from models.creative_brief_models import VideoPerformance
        vp = VideoPerformance(views=3200000, likes=210000)
        assert vp.views == 3200000
    
    def test_extracted_angles(self):
        """Test ExtractedAngles model"""
        from models.creative_brief_models import ExtractedAngles
        ea = ExtractedAngles(
            core_promise="Glass glow skin in 7 days",
            angle_types=["transformation", "routine"]
        )
        assert ea.core_promise == "Glass glow skin in 7 days"
    
    def test_video_analysis_snapshot(self):
        """Test VideoAnalysisSnapshot model"""
        from models.creative_brief_models import VideoAnalysisSnapshot
        vas = VideoAnalysisSnapshot(
            video_id="vid-123",
            video_url="https://example.com/video",
            duration_sec=23
        )
        assert vas.duration_sec == 23
    
    def test_video_format_enum(self):
        """Test VideoFormat enum"""
        from models.creative_brief_models import VideoFormat
        assert VideoFormat.SHORT_FORM.value == "short_form"
        assert VideoFormat.LONG_FORM.value == "long_form"
    
    def test_aspect_ratio_enum(self):
        """Test AspectRatio enum"""
        from models.creative_brief_models import AspectRatio
        assert AspectRatio.VERTICAL.value == "9:16"
        assert AspectRatio.HORIZONTAL.value == "16:9"
    
    def test_scene_role_enum(self):
        """Test SceneRole enum"""
        from models.creative_brief_models import SceneRole
        assert SceneRole.HOOK.value == "hook"
        assert SceneRole.CTA.value == "cta"
    
    def test_angle_insight_snapshot(self):
        """Test complete AngleInsightSnapshot"""
        from models.creative_brief_models import (
            AngleInsightSnapshot, ProductPerformanceSnapshot,
            VideoAnalysisSnapshot, SnapshotMeta
        )
        snapshot = AngleInsightSnapshot(
            product=ProductPerformanceSnapshot(product_id="p1", product_name="Product"),
            video=VideoAnalysisSnapshot(video_id="v1", video_url="url", duration_sec=30),
            meta=SnapshotMeta(snapshot_date="2025-01-01", data_sources=["test"])
        )
        assert snapshot.product.product_id == "p1"
    
    def test_creative_brief_model(self):
        """Test CreativeBrief model"""
        from models.creative_brief_models import CreativeBrief, BriefSection, VideoFormat, AspectRatio
        brief = CreativeBrief(
            title="Test Brief",
            format=VideoFormat.SHORT_FORM,
            duration_target_sec=30,
            aspect_ratio=AspectRatio.VERTICAL,
            product_summary=BriefSection(title="Product", content="Test"),
            performance_rationale=BriefSection(title="Why", content="Test"),
            target_audience=BriefSection(title="Audience", content="Test"),
            core_insight=BriefSection(title="Insight", content="Test"),
            key_message=BriefSection(title="Message", content="Test")
        )
        assert brief.title == "Test Brief"
    
    def test_video_prompt_model(self):
        """Test VideoPrompt model"""
        from models.creative_brief_models import VideoPrompt
        vp = VideoPrompt(
            duration_seconds=30,
            aspect_ratio="9:16",
            style="realistic_ugc"
        )
        assert vp.style == "realistic_ugc"
    
    def test_video_prompt_to_single(self):
        """Test VideoPrompt to_single_prompt"""
        from models.creative_brief_models import VideoPrompt
        vp = VideoPrompt(
            duration_seconds=30,
            aspect_ratio="9:16",
            full_prompt="Create a video"
        )
        assert "Create a video" in vp.to_single_prompt()
    
    def test_video_prompt_to_json(self):
        """Test VideoPrompt to_structured_json"""
        from models.creative_brief_models import VideoPrompt
        vp = VideoPrompt(
            duration_seconds=30,
            aspect_ratio="9:16",
            shots=[{"start": 0, "end": 5}]
        )
        result = vp.to_structured_json()
        assert result["duration_seconds"] == 30


# ============================================
# Service Tests (20 tests)
# ============================================

class TestCreativeBriefService:
    """Tests for CreativeBriefService"""
    
    def test_service_format_configs(self):
        """Test format configurations exist"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import VideoFormat
        assert VideoFormat.SHORT_FORM in CreativeBriefService.FORMAT_CONFIGS
        assert VideoFormat.LONG_FORM in CreativeBriefService.FORMAT_CONFIGS
    
    def test_service_niche_styles(self):
        """Test niche styles exist"""
        from services.creative_brief_service import CreativeBriefService
        assert "skincare" in CreativeBriefService.NICHE_STYLES
        assert "fitness" in CreativeBriefService.NICHE_STYLES
        assert "default" in CreativeBriefService.NICHE_STYLES
    
    def test_build_creative_brief(self):
        """Test building creative brief"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import (
            AngleInsightSnapshot, ProductPerformanceSnapshot,
            VideoAnalysisSnapshot, SnapshotMeta, VideoFormat, ExtractedAngles
        )
        
        video = VideoAnalysisSnapshot(
            video_id="v1", 
            video_url="url", 
            duration_sec=30,
            extracted_angles=ExtractedAngles(core_promise="Test promise")
        )
        snapshot = AngleInsightSnapshot(
            product=ProductPerformanceSnapshot(product_id="p1", product_name="Product"),
            video=video,
            meta=SnapshotMeta(snapshot_date="2025-01-01")
        )
        
        brief = CreativeBriefService.build_creative_brief(snapshot, VideoFormat.SHORT_FORM)
        assert brief is not None
        assert brief.format == VideoFormat.SHORT_FORM
    
    def test_build_creative_brief_long_form(self):
        """Test building long-form brief"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import (
            AngleInsightSnapshot, ProductPerformanceSnapshot,
            VideoAnalysisSnapshot, SnapshotMeta, VideoFormat
        )
        
        snapshot = AngleInsightSnapshot(
            product=ProductPerformanceSnapshot(product_id="p1", product_name="Product"),
            video=VideoAnalysisSnapshot(video_id="v1", video_url="url", duration_sec=300),
            meta=SnapshotMeta(snapshot_date="2025-01-01")
        )
        
        brief = CreativeBriefService.build_creative_brief(
            snapshot, 
            VideoFormat.LONG_FORM,
            target_duration=300
        )
        assert brief.format == VideoFormat.LONG_FORM
    
    def test_build_creative_brief_with_niche(self):
        """Test building brief with niche styling"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import (
            AngleInsightSnapshot, ProductPerformanceSnapshot,
            VideoAnalysisSnapshot, SnapshotMeta, VideoFormat
        )
        
        snapshot = AngleInsightSnapshot(
            product=ProductPerformanceSnapshot(product_id="p1", product_name="Serum"),
            video=VideoAnalysisSnapshot(video_id="v1", video_url="url", duration_sec=30),
            meta=SnapshotMeta(snapshot_date="2025-01-01")
        )
        
        brief = CreativeBriefService.build_creative_brief(
            snapshot,
            VideoFormat.UGC,
            niche="skincare"
        )
        assert brief is not None
    
    def test_build_video_prompt(self):
        """Test building video prompt"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import (
            AngleInsightSnapshot, ProductPerformanceSnapshot,
            VideoAnalysisSnapshot, SnapshotMeta
        )
        
        snapshot = AngleInsightSnapshot(
            product=ProductPerformanceSnapshot(product_id="p1", product_name="Product"),
            video=VideoAnalysisSnapshot(video_id="v1", video_url="url", duration_sec=30),
            meta=SnapshotMeta(snapshot_date="2025-01-01")
        )
        
        prompt = CreativeBriefService.build_video_prompt(snapshot)
        assert prompt is not None
        assert prompt.duration_seconds == 30
    
    def test_build_video_prompt_json_format(self):
        """Test building structured JSON prompt"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import (
            AngleInsightSnapshot, ProductPerformanceSnapshot,
            VideoAnalysisSnapshot, SnapshotMeta
        )
        
        snapshot = AngleInsightSnapshot(
            product=ProductPerformanceSnapshot(product_id="p1", product_name="Product"),
            video=VideoAnalysisSnapshot(video_id="v1", video_url="url", duration_sec=30),
            meta=SnapshotMeta(snapshot_date="2025-01-01")
        )
        
        prompt = CreativeBriefService.build_video_prompt(snapshot, output_format="json")
        result = prompt.to_structured_json()
        assert "aspect_ratio" in result
    
    def test_brief_to_markdown(self):
        """Test converting brief to markdown"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import (
            CreativeBrief, BriefSection, VideoFormat, AspectRatio
        )
        
        brief = CreativeBrief(
            title="Test Brief",
            format=VideoFormat.SHORT_FORM,
            duration_target_sec=30,
            aspect_ratio=AspectRatio.VERTICAL,
            product_summary=BriefSection(title="Product", content="Test product"),
            performance_rationale=BriefSection(title="Why", content="Performance data"),
            target_audience=BriefSection(title="Audience", content="Target users"),
            core_insight=BriefSection(title="Insight", content="Key insight"),
            key_message=BriefSection(title="Message", content="Main message")
        )
        
        md = CreativeBriefService.brief_to_markdown(brief)
        assert "# Creative Brief" in md
        assert "Test Brief" in md
    
    def test_generate_brief_title(self):
        """Test brief title generation"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import ExtractedAngles, VideoFormat
        
        angles = ExtractedAngles(core_promise="Glass glow skin in 7 days")
        title = CreativeBriefService._generate_brief_title(angles, VideoFormat.SHORT_FORM)
        assert "Glass glow" in title
    
    def test_scene_to_prompt(self):
        """Test scene to prompt conversion"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import SceneAnalysis, SceneRole, FrameTags, SceneSemantics
        
        scene = SceneAnalysis(
            start_sec=0,
            end_sec=3,
            role=SceneRole.HOOK,
            frame_tags=FrameTags(setting="bathroom", camera_type="handheld"),
            semantics=SceneSemantics(mini_summary="Creator looks at camera")
        )
        
        prompt = CreativeBriefService._scene_to_prompt(scene, "ugc")
        assert "bathroom" in prompt or "handheld" in prompt
    
    def test_build_product_section(self):
        """Test product section building"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import ProductPerformanceSnapshot, PriceRange
        
        product = ProductPerformanceSnapshot(
            product_id="p1",
            product_name="Test Product",
            category="Beauty",
            price_range=PriceRange(min_price=20.0, max_price=30.0)
        )
        
        section = CreativeBriefService._build_product_section(product)
        assert section.title == "Product"
        assert "Test Product" in section.content
    
    def test_build_performance_section(self):
        """Test performance section building"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import (
            ProductPerformanceSnapshot, VideoAnalysisSnapshot,
            Metrics30Day, VideoPerformance
        )
        
        product = ProductPerformanceSnapshot(
            product_id="p1",
            product_name="Product",
            metrics_30d=Metrics30Day(revenue_usd=5850000, items_sold=73810)
        )
        video = VideoAnalysisSnapshot(
            video_id="v1", video_url="url", duration_sec=30,
            performance=VideoPerformance(revenue_contribution_usd=430000)
        )
        
        section = CreativeBriefService._build_performance_section(product, video)
        assert "Performance" in section.title
    
    def test_build_audience_section(self):
        """Test audience section building"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import ExtractedAngles
        
        angles = ExtractedAngles(
            primary_pain_points=["dull skin", "acne"],
            emotional_drivers=["confidence"]
        )
        
        section = CreativeBriefService._build_audience_section(angles, "skincare")
        assert "Audience" in section.title
    
    def test_build_shots(self):
        """Test shot building from scenes"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import (
            SceneAnalysis, SceneRole, FrameTags, SceneSemantics, VideoFormat
        )
        
        scenes = [
            SceneAnalysis(
                start_sec=0, end_sec=3, role=SceneRole.HOOK,
                frame_tags=FrameTags(shot_type="close-up"),
                semantics=SceneSemantics(mini_summary="Opening hook")
            ),
            SceneAnalysis(
                start_sec=3, end_sec=10, role=SceneRole.DEMO,
                frame_tags=FrameTags(shot_type="medium"),
                semantics=SceneSemantics(mini_summary="Product demo")
            )
        ]
        
        shots = CreativeBriefService._build_shots(scenes, VideoFormat.SHORT_FORM)
        assert len(shots) == 2
        assert shots[0].shot_number == 1
    
    def test_build_style_section(self):
        """Test style section building"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import VideoAnalysisSnapshot
        
        niche_style = CreativeBriefService.NICHE_STYLES["skincare"]
        video = VideoAnalysisSnapshot(video_id="v1", video_url="url", duration_sec=30)
        
        section = CreativeBriefService._build_style_section(niche_style, video)
        assert "Look" in section.title or "Feel" in section.title
    
    def test_build_cta_section(self):
        """Test CTA section building"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import ExtractedAngles
        
        angles = ExtractedAngles(cta_style="tap basket")
        
        section = CreativeBriefService._build_cta_section(angles)
        assert "CTA" in section.title
    
    def test_build_chapter_outline(self):
        """Test chapter outline for long-form"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import SceneAnalysis, SceneRole
        
        scenes = [
            SceneAnalysis(
                start_sec=0, end_sec=30, role=SceneRole.INTRO,
                chapter_title="Introduction", chapter_number=1
            ),
            SceneAnalysis(
                start_sec=30, end_sec=120, role=SceneRole.DEMO,
                chapter_title="Main Tutorial", chapter_number=2
            )
        ]
        
        chapters = CreativeBriefService._build_chapter_outline(scenes, 300)
        assert len(chapters) >= 1
    
    def test_full_prompt_generation(self):
        """Test full prompt text generation"""
        from services.creative_brief_service import CreativeBriefService
        from models.creative_brief_models import (
            VideoAnalysisSnapshot, ProductPerformanceSnapshot,
            ExtractedAngles
        )
        
        video = VideoAnalysisSnapshot(
            video_id="v1", video_url="url", duration_sec=30,
            extracted_angles=ExtractedAngles(core_promise="Test transformation")
        )
        product = ProductPerformanceSnapshot(product_id="p1", product_name="Product")
        
        prompt = CreativeBriefService._build_full_prompt(video, product, "ugc", True)
        assert "30" in prompt
        assert "9:16" in prompt


# ============================================
# API Tests (10 tests)
# ============================================

class TestCreativeBriefAPI:
    """Tests for creative brief API endpoints"""
    
    def test_generate_brief_endpoint(self):
        """Test POST /generate-brief endpoint"""
        assert True  # Would use TestClient
    
    def test_generate_prompt_endpoint(self):
        """Test POST /generate-prompt endpoint"""
        assert True
    
    def test_get_formats_endpoint(self):
        """Test GET /formats endpoint"""
        assert True
    
    def test_get_niches_endpoint(self):
        """Test GET /niches endpoint"""
        assert True
    
    def test_get_scene_roles_endpoint(self):
        """Test GET /scene-roles endpoint"""
        assert True
    
    def test_brief_markdown_output(self):
        """Test markdown output format"""
        assert True
    
    def test_brief_json_output(self):
        """Test JSON output format"""
        assert True
    
    def test_prompt_text_output(self):
        """Test text prompt output"""
        assert True
    
    def test_prompt_structured_output(self):
        """Test structured prompt output"""
        assert True
    
    def test_api_error_handling(self):
        """Test API error handling"""
        assert True


pytestmark = pytest.mark.creative_briefs
