"""
Unit tests for CopyPlanService - Platform-optimized copy generation
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import asdict

from services.content_pipeline.copy_plan_service import (
    CopyPlanService,
    CopyPlanInput,
    CopyVariant,
    TextConstraint,
    PlatformCopyVariant,
    CopyPlanV1,
)


class TestTextConstraint:
    """Tests for TextConstraint dataclass"""
    
    def test_constraint_defaults(self):
        """Default values are set correctly"""
        constraint = TextConstraint(
            platform="youtube",
            surface="video",
            field="title",
            max_chars=100
        )
        assert constraint.target_margin_pct == 0.20
        assert constraint.count_rule == "graphemes"
        assert constraint.max_hashtags is None
    
    def test_constraint_with_all_fields(self):
        """All fields can be set"""
        constraint = TextConstraint(
            platform="instagram",
            surface="reel",
            field="caption",
            max_chars=2200,
            soft_cap_chars=1760,
            target_margin_pct=0.20,
            count_rule="graphemes",
            max_hashtags=30,
            max_mentions=20
        )
        assert constraint.max_chars == 2200
        assert constraint.max_hashtags == 30


class TestCopyPlanInput:
    """Tests for CopyPlanInput dataclass"""
    
    def test_input_required_fields(self):
        """Required fields must be provided"""
        inputs = CopyPlanInput(
            hook="Stop scrolling!",
            topics=["productivity", "tips"]
        )
        assert inputs.hook == "Stop scrolling!"
        assert inputs.topics == ["productivity", "tips"]
    
    def test_input_optional_fields(self):
        """Optional fields have defaults"""
        inputs = CopyPlanInput(
            hook="Test hook",
            topics=["test"]
        )
        assert inputs.keywords == []
        assert inputs.audience == []
        assert inputs.cta is None
        assert inputs.pain_points == []
    
    def test_input_with_cta(self):
        """CTA can be included"""
        inputs = CopyPlanInput(
            hook="Test",
            topics=["test"],
            cta={"type": "follow", "text": "Follow for more!"}
        )
        assert inputs.cta["type"] == "follow"


class TestCopyVariant:
    """Tests for CopyVariant dataclass"""
    
    def test_variant_fits(self):
        """Variant that fits within limit"""
        variant = CopyVariant(
            text="Short text",
            char_count=10,
            target_chars=100,
            max_chars=100,
            fits=True
        )
        assert variant.fits is True
    
    def test_variant_does_not_fit(self):
        """Variant that exceeds limit"""
        variant = CopyVariant(
            text="Very long text...",
            char_count=150,
            max_chars=100,
            fits=False
        )
        assert variant.fits is False


class TestCopyPlanService:
    """Tests for CopyPlanService"""
    
    @pytest.fixture
    def service(self):
        """Create service instance with mocked DB"""
        with patch.object(CopyPlanService, '_load_constraints'):
            service = CopyPlanService(openai_api_key="test-key")
            # Add mock constraints
            service._constraints_cache = {
                "youtube:video:title": TextConstraint(
                    platform="youtube", surface="video", field="title",
                    max_chars=100, soft_cap_chars=80
                ),
                "youtube:video:description": TextConstraint(
                    platform="youtube", surface="video", field="description",
                    max_chars=5000, soft_cap_chars=4000
                ),
                "instagram:reel:caption": TextConstraint(
                    platform="instagram", surface="reel", field="caption",
                    max_chars=2200, soft_cap_chars=1760, max_hashtags=30
                ),
                "tiktok:video:caption": TextConstraint(
                    platform="tiktok", surface="video", field="caption",
                    max_chars=2200, soft_cap_chars=1760, count_rule="utf16"
                ),
            }
            return service
    
    def test_get_constraint_exists(self, service):
        """Get existing constraint"""
        constraint = service.get_constraint("youtube", "video", "title")
        assert constraint is not None
        assert constraint.max_chars == 100
    
    def test_get_constraint_not_exists(self, service):
        """Get non-existent constraint returns None"""
        constraint = service.get_constraint("unknown", "surface", "field")
        assert constraint is None
    
    def test_build_copy_variant_within_limit(self, service):
        """Build variant that fits within limit"""
        constraint = TextConstraint(
            platform="youtube", surface="video", field="title",
            max_chars=100, soft_cap_chars=80
        )
        variant = service.build_copy_variant("Short title", constraint)
        
        assert variant.text == "Short title"
        assert variant.fits is True
        assert variant.char_count == 11
    
    def test_build_copy_variant_truncation(self, service):
        """Build variant that needs truncation"""
        constraint = TextConstraint(
            platform="youtube", surface="video", field="title",
            max_chars=20, soft_cap_chars=16
        )
        long_text = "This is a very long title that needs truncation"
        variant = service.build_copy_variant(long_text, constraint)
        
        assert variant.char_count <= 20
        assert variant.fits is True
    
    def test_build_copy_variant_no_constraint(self, service):
        """Build variant without constraint"""
        variant = service.build_copy_variant("Any text", None)
        
        assert variant.text == "Any text"
        assert variant.fits is True
    
    @pytest.mark.asyncio
    async def test_generate_copy_for_platform_youtube(self, service):
        """Generate copy for YouTube"""
        inputs = CopyPlanInput(
            hook="Stop wasting time on social media",
            topics=["productivity", "time management"],
            cta={"type": "subscribe", "text": "Subscribe for more tips!"}
        )
        
        # Mock LLM response
        service._call_llm = AsyncMock(return_value={
            "titles": ["5 Productivity Hacks", "Stop Wasting Time"],
            "description": "Learn how to be more productive...",
            "hashtags": ["productivity", "tips"]
        })
        
        variant = await service.generate_copy_for_platform(inputs, "youtube", "video")
        
        assert variant.platform == "youtube"
        assert variant.surface == "video"
        assert variant.title_variants is not None
        assert len(variant.title_variants) >= 1
    
    @pytest.mark.asyncio
    async def test_generate_copy_plan_multiple_platforms(self, service):
        """Generate copy for multiple platforms"""
        inputs = CopyPlanInput(
            hook="Check this out!",
            topics=["viral", "content"]
        )
        
        # Mock LLM
        service._call_llm = AsyncMock(return_value={
            "titles": ["Great Title"],
            "caption": "Amazing content!",
            "description": "Full description here.",
            "hashtags": ["viral"]
        })
        
        # Mock save
        service._save_copy_plan = AsyncMock()
        
        plan = await service.generate_copy_plan(
            inputs=inputs,
            platforms=["youtube", "instagram"]
        )
        
        assert plan.schema == "copy_plan_v1"
        assert len(plan.variants) >= 2  # At least youtube + instagram
    
    def test_from_video_analysis(self):
        """Create CopyPlanInput from video analysis"""
        analysis = {
            "detected_hook": "POV: You're struggling",
            "topics": ["motivation", "success", "mindset"],
            "tone": "inspirational",
            "pain_points": ["lack of direction", "feeling stuck"],
            "emotional_drivers": ["desire for change", "hope"],
            "call_to_action": {
                "type": "follow",
                "text": "Follow for more!"
            },
            "content_type": "motivational",
            "target_audience": {
                "demographic": "young professionals",
                "interests": ["self-improvement"]
            }
        }
        
        inputs = CopyPlanService.from_video_analysis(analysis)
        
        assert inputs.hook == "POV: You're struggling"
        assert "motivation" in inputs.topics
        assert inputs.tone == "inspirational"
        assert inputs.pain_points == ["lack of direction", "feeling stuck"]
        assert inputs.cta["type"] == "follow"
    
    def test_from_video_analysis_minimal(self):
        """Create CopyPlanInput from minimal analysis"""
        analysis = {
            "hooks": ["First hook"],
            "topics": ["topic1"]
        }
        
        inputs = CopyPlanService.from_video_analysis(analysis)
        
        assert inputs.hook == "First hook"
        assert inputs.topics == ["topic1"]


class TestCopyPlanV1:
    """Tests for CopyPlanV1 dataclass"""
    
    def test_plan_structure(self):
        """Plan has correct structure"""
        plan = CopyPlanV1(
            inputs=CopyPlanInput(hook="Test", topics=["test"]),
            variants=[]
        )
        
        assert plan.schema == "copy_plan_v1"
        assert plan.inputs.hook == "Test"
        assert plan.variants == []
    
    def test_plan_with_variants(self):
        """Plan with platform variants"""
        variant = PlatformCopyVariant(
            platform="youtube",
            surface="video",
            constraints={},
            generation_meta={"model": "gpt-4o-mini"}
        )
        
        plan = CopyPlanV1(
            inputs=CopyPlanInput(hook="Test", topics=["test"]),
            variants=[variant]
        )
        
        assert len(plan.variants) == 1
        assert plan.variants[0].platform == "youtube"


class TestPlatformSpecificConstraints:
    """Tests for platform-specific constraint handling"""
    
    @pytest.fixture
    def service(self):
        with patch.object(CopyPlanService, '_load_constraints'):
            service = CopyPlanService(openai_api_key="test-key")
            service._constraints_cache = {
                "tiktok:video:caption": TextConstraint(
                    platform="tiktok", surface="video", field="caption",
                    max_chars=2200, count_rule="utf16"
                ),
                "threads:post:caption": TextConstraint(
                    platform="threads", surface="post", field="caption",
                    max_chars=500, count_rule="utf8_bytes"
                ),
            }
            return service
    
    def test_tiktok_utf16_counting(self, service):
        """TikTok uses UTF-16 character counting"""
        constraint = service.get_constraint("tiktok", "video", "caption")
        assert constraint.count_rule == "utf16"
        
        # Emoji takes 2 UTF-16 code units
        text_with_emoji = "Test 🔥"
        variant = service.build_copy_variant(text_with_emoji, constraint)
        assert variant.char_count == 7  # "Test " (5) + emoji (2)
    
    def test_threads_utf8_counting(self, service):
        """Threads uses UTF-8 byte counting"""
        constraint = service.get_constraint("threads", "post", "caption")
        assert constraint.count_rule == "utf8_bytes"
