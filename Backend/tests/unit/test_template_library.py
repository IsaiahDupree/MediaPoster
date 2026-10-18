"""
Unit Tests for Template Library Service
=======================================
Tests for template creation, matching, and management.
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
import json


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_analysis_data():
    """Sample video analysis data"""
    return {
        "beat_sheet": [
            {"role": "hook", "start_sec": 0, "end_sec": 3, "summary": "Attention grabber"},
            {"role": "problem", "start_sec": 3, "end_sec": 10, "summary": "State problem"},
            {"role": "solution", "start_sec": 10, "end_sec": 25, "summary": "Deliver value"},
            {"role": "cta", "start_sec": 25, "end_sec": 30, "summary": "Call to action"}
        ],
        "visual_analysis": {
            "dominant_shot_type": "medium",
            "dominant_lighting": "natural",
            "caption_style": "fast_captions",
            "color_palette": ["#FF5733", "#33FF57", "#3357FF"]
        },
        "hooks": ["Stop doing this one thing!", "Nobody tells you this secret"],
        "tone": "educational",
        "pacing": "fast",
        "music_suggestion": {"mood": "upbeat", "tempo": "medium"},
        "transcription_duration_sec": 30,
        "pillar_tags": ["growth", "tips"],
        "format_tags": ["tutorial", "tips"],
        "content_type": "tutorial",
        "call_to_action": {"type": "link_bio", "text": "Link in bio"}
    }


@pytest.fixture
def sample_performance_metrics():
    """Sample performance metrics"""
    return {
        "engagement_rate": 0.08,
        "views": 100000,
        "completion_rate": 0.65
    }


# ============================================================================
# TemplateLibrary Tests
# ============================================================================

class TestTemplateLibrary:
    """Tests for TemplateLibrary service"""
    
    @pytest.fixture
    def library(self):
        """Create template library with mocked dependencies"""
        with patch('services.template_library.create_engine'):
            with patch('services.template_library.OpenAI'):
                from services.template_library import TemplateLibrary
                lib = TemplateLibrary(
                    db_url="postgresql://test:test@localhost/test",
                    openai_api_key="test_key"
                )
                return lib
    
    def test_standard_structures_defined(self, library):
        """Test that standard structures are defined"""
        assert "hook_problem_solution" in library.STANDARD_STRUCTURES
        assert "listicle" in library.STANDARD_STRUCTURES
        assert "story_transformation" in library.STANDARD_STRUCTURES
        assert "tutorial_quick" in library.STANDARD_STRUCTURES
        assert "myth_bust" in library.STANDARD_STRUCTURES
    
    def test_standard_structure_has_beats(self, library):
        """Test that each standard structure has beats"""
        for name, beats in library.STANDARD_STRUCTURES.items():
            assert len(beats) >= 2, f"{name} should have at least 2 beats"
            assert beats[0].role == "hook", f"{name} should start with hook"
    
    def test_map_content_type_to_category_tutorial(self, library):
        """Test content type mapping for tutorials"""
        category = library._map_content_type_to_category("tutorial")
        assert category == "tutorial_quick"
    
    def test_map_content_type_to_category_listicle(self, library):
        """Test content type mapping for listicles"""
        category = library._map_content_type_to_category("3 tips for growth")
        assert category == "listicle"
    
    def test_map_content_type_to_category_story(self, library):
        """Test content type mapping for stories"""
        category = library._map_content_type_to_category("transformation story")
        assert category == "story_transformation"
    
    def test_map_content_type_to_category_myth(self, library):
        """Test content type mapping for myth busting"""
        category = library._map_content_type_to_category("myth debunk")
        assert category == "myth_bust"
    
    def test_map_content_type_to_category_default(self, library):
        """Test content type mapping defaults to hook_problem_solution"""
        category = library._map_content_type_to_category("unknown_type")
        assert category == "hook_problem_solution"
    
    def test_determine_energy_high(self, library):
        """Test energy determination for high energy"""
        energy = library._determine_energy("exciting", {"mood": "upbeat", "tempo": "fast"})
        assert energy == "high"
    
    def test_determine_energy_low(self, library):
        """Test energy determination for low energy"""
        energy = library._determine_energy("calm", {"mood": "relaxed", "tempo": "slow"})
        assert energy == "low"
    
    def test_determine_energy_medium(self, library):
        """Test energy determination defaults to medium"""
        energy = library._determine_energy("neutral", {})
        assert energy == "medium"
    
    def test_extract_cta_patterns(self, library, sample_analysis_data):
        """Test CTA pattern extraction"""
        patterns = library._extract_cta_patterns(sample_analysis_data)
        
        assert len(patterns) > 0
        assert "Link in bio" in patterns
    
    def test_determine_best_for_tutorial(self, library, sample_analysis_data):
        """Test best-for determination for tutorials"""
        best_for = library._determine_best_for("tutorial_quick", sample_analysis_data)
        
        assert len(best_for) > 0
        assert any("tutorial" in bf.lower() or "how-to" in bf.lower() for bf in best_for)
    
    def test_assess_difficulty_simple(self, library):
        """Test difficulty assessment for simple templates"""
        from services.template_library import BeatTemplate
        
        beats = [
            BeatTemplate("hook", (0, 3), "hook", "curiosity", "close-up", "sound"),
            BeatTemplate("cta", (27, 30), "cta", "urgency", "direct", "fade")
        ]
        visual = {"dominant_shot_type": "medium"}
        
        difficulty = library._assess_difficulty(beats, visual)
        assert difficulty == "beginner"
    
    def test_assess_difficulty_complex(self, library):
        """Test difficulty assessment for complex templates"""
        from services.template_library import BeatTemplate
        
        beats = [BeatTemplate(f"beat{i}", (i*5, i*5+5), f"beat {i}", "emotion", "visual", "audio") 
                 for i in range(8)]
        visual = {"dominant_shot_type": "tracking", "caption_style": "fast_captions"}
        
        difficulty = library._assess_difficulty(beats, visual)
        assert difficulty in ["intermediate", "advanced"]
    
    def test_estimate_production_time_short(self, library):
        """Test production time estimation for short templates"""
        from services.template_library import BeatTemplate
        
        beats = [BeatTemplate("hook", (0, 3), "", "", "", "")]
        time = library._estimate_production_time(beats)
        
        assert "15" in time or "20" in time
    
    def test_estimate_production_time_long(self, library):
        """Test production time estimation for long templates"""
        from services.template_library import BeatTemplate
        
        beats = [BeatTemplate(f"beat{i}", (i*5, i*5+5), "", "", "", "") for i in range(8)]
        time = library._estimate_production_time(beats)
        
        assert "45" in time or "60" in time
    
    def test_slugify(self, library):
        """Test slug generation"""
        slug = library._slugify("Fast Caption Tutorial V1")
        
        assert slug == "fast-caption-tutorial-v1"
        assert " " not in slug
    
    def test_slugify_special_chars(self, library):
        """Test slug generation with special characters"""
        slug = library._slugify("Hook-Problem-Solution (Classic)")
        
        assert "(" not in slug
        assert ")" not in slug
        assert slug.replace("-", "").isalnum()
    
    @pytest.mark.asyncio
    async def test_create_template_from_video(self, library, sample_analysis_data, sample_performance_metrics):
        """Test template creation from video analysis"""
        # Mock AI name generation
        library._generate_template_name = AsyncMock(return_value="Tutorial Hook Fast V1")
        
        template = await library.create_template_from_video(
            video_id="video123",
            analysis_data=sample_analysis_data,
            performance_metrics=sample_performance_metrics
        )
        
        assert template.name == "Tutorial Hook Fast V1"
        assert "video123" in template.source_video_ids
        assert template.avg_engagement_rate == 0.08
        assert template.avg_views == 100000
        assert template.target_duration_sec == 30
        assert len(template.beat_sheet) > 0
    
    @pytest.mark.asyncio
    async def test_create_template_without_beat_sheet(self, library, sample_performance_metrics):
        """Test template creation uses default beats when none provided"""
        library._generate_template_name = AsyncMock(return_value="Default Template")
        
        analysis_data = {
            "visual_analysis": {},
            "hooks": [],
            "tone": "neutral",
            "pacing": "medium",
            "music_suggestion": {},
            "transcription_duration_sec": 30,
            "pillar_tags": [],
            "format_tags": [],
            "content_type": "general",
            "call_to_action": {}
        }
        
        template = await library.create_template_from_video(
            video_id="video456",
            analysis_data=analysis_data,
            performance_metrics=sample_performance_metrics
        )
        
        # Should use default hook_problem_solution structure
        assert len(template.beat_sheet) >= 2
    
    @pytest.mark.asyncio
    async def test_match_content_to_template(self, library):
        """Test template matching"""
        # Mock list_templates to return test templates
        library.list_templates = AsyncMock(return_value=[
            {
                "template_id": "t1",
                "name": "Tutorial Template",
                "category": "tutorial_quick",
                "target_duration_sec": 30,
                "style": {"tone": "educational"},
                "avg_engagement_rate": 0.08,
                "beat_sheet": [{"role": "hook"}, {"role": "cta"}]
            },
            {
                "template_id": "t2",
                "name": "Story Template",
                "category": "story_transformation",
                "target_duration_sec": 45,
                "style": {"tone": "inspirational"},
                "avg_engagement_rate": 0.06,
                "beat_sheet": [{"role": "hook"}, {"role": "after"}]
            }
        ])
        
        content_analysis = {
            "content_type": "tutorial quick tips",
            "tone": "educational",
            "topics": ["growth"],
            "transcription_duration_sec": 28
        }
        
        matches = await library.match_content_to_template(content_analysis)
        
        assert len(matches) > 0
        # Tutorial template should match better
        assert matches[0].template_name == "Tutorial Template"
        assert matches[0].match_score > 30


# ============================================================================
# VideoTemplate Tests
# ============================================================================

class TestVideoTemplate:
    """Tests for VideoTemplate dataclass"""
    
    def test_video_template_creation(self):
        """Test VideoTemplate dataclass creation"""
        from services.template_library import VideoTemplate
        
        template = VideoTemplate(
            name="Test Template",
            slug="test-template",
            category="tutorial_quick",
            target_duration_sec=30
        )
        
        assert template.name == "Test Template"
        assert template.category == "tutorial_quick"
        assert template.times_used == 0
        assert template.avg_output_performance == 0.0
    
    def test_video_template_defaults(self):
        """Test VideoTemplate default values"""
        from services.template_library import VideoTemplate
        
        template = VideoTemplate()
        
        assert template.source_video_ids == []
        assert template.beat_sheet == []
        assert template.style == {}
        assert template.difficulty == "intermediate"


# ============================================================================
# BeatTemplate Tests
# ============================================================================

class TestBeatTemplate:
    """Tests for BeatTemplate dataclass"""
    
    def test_beat_template_creation(self):
        """Test BeatTemplate dataclass creation"""
        from services.template_library import BeatTemplate
        
        beat = BeatTemplate(
            role="hook",
            duration_range=(0, 3),
            description="Attention grabber",
            emotion_cue="curiosity",
            visual_cue="close-up",
            audio_cue="sound effect"
        )
        
        assert beat.role == "hook"
        assert beat.duration_range == (0, 3)
        assert beat.emotion_cue == "curiosity"
        assert beat.text_overlay is None
    
    def test_beat_template_with_text(self):
        """Test BeatTemplate with text overlay"""
        from services.template_library import BeatTemplate
        
        beat = BeatTemplate(
            role="cta",
            duration_range=(25, 30),
            description="Call to action",
            emotion_cue="urgency",
            visual_cue="direct",
            audio_cue="fade",
            text_overlay="Subscribe Now!"
        )
        
        assert beat.text_overlay == "Subscribe Now!"


# ============================================================================
# TemplateMatch Tests
# ============================================================================

class TestTemplateMatch:
    """Tests for TemplateMatch dataclass"""
    
    def test_template_match_creation(self):
        """Test TemplateMatch dataclass creation"""
        from services.template_library import TemplateMatch
        
        match = TemplateMatch(
            template_id="t1",
            template_name="Tutorial Template",
            match_score=85.0,
            match_reasons=["Content type matches", "Similar duration"],
            suggested_modifications=["Extend hook by 1 second"]
        )
        
        assert match.template_id == "t1"
        assert match.match_score == 85.0
        assert len(match.match_reasons) == 2
        assert len(match.suggested_modifications) == 1


# ============================================================================
# Integration-Style Tests
# ============================================================================

class TestTemplateWorkflow:
    """Tests for complete template workflow"""
    
    @pytest.fixture
    def library(self):
        """Create template library"""
        with patch('services.template_library.create_engine'):
            with patch('services.template_library.OpenAI'):
                from services.template_library import TemplateLibrary
                return TemplateLibrary(db_url="test", openai_api_key="test")
    
    @pytest.mark.asyncio
    async def test_full_template_creation_workflow(self, library, sample_analysis_data, sample_performance_metrics):
        """Test complete template creation workflow"""
        library._generate_template_name = AsyncMock(return_value="High Performance Tutorial")
        
        # Create template
        template = await library.create_template_from_video(
            video_id="vid1",
            analysis_data=sample_analysis_data,
            performance_metrics=sample_performance_metrics
        )
        
        # Verify all fields populated
        assert template.name == "High Performance Tutorial"
        assert template.slug == "high-performance-tutorial"
        assert template.category == "tutorial_quick"
        assert template.avg_engagement_rate == 0.08
        assert len(template.beat_sheet) >= 2
        assert template.style.get("tone") == "educational"
        assert "upbeat" in template.music_mood
        assert len(template.best_for) > 0
        assert template.difficulty in ["beginner", "intermediate", "advanced"]


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
