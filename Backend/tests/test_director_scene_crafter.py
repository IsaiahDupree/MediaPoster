"""
Director and Scene Crafter Tests
=================================
Unit tests for Director and SceneCrafter services.

Run tests:
    pytest tests/test_director_scene_crafter.py -v
"""

import asyncio
import pytest
from uuid import uuid4
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# DIRECTOR CONFIG TESTS
# =============================================================================

class TestDirectorConfig:
    """Test DirectorConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        from services.video_orchestrator.director import DirectorConfig
        
        config = DirectorConfig()
        
        assert config.words_per_minute == 150
        assert config.min_clip_seconds == 4
        assert config.max_clip_seconds == 12
        assert config.default_clip_seconds == 8
    
    def test_words_for_duration(self):
        """Test words_for_duration calculation."""
        from services.video_orchestrator.director import DirectorConfig
        
        config = DirectorConfig(words_per_minute=150)
        
        # At 150 wpm = 2.5 words per second
        assert config.words_for_duration(4) == 10   # 4s = ~10 words
        assert config.words_for_duration(8) == 20   # 8s = ~20 words
        assert config.words_for_duration(12) == 30  # 12s = ~30 words
    
    def test_custom_wpm(self):
        """Test custom words per minute."""
        from services.video_orchestrator.director import DirectorConfig
        
        config = DirectorConfig(words_per_minute=120)
        
        # At 120 wpm = 2 words per second
        assert config.words_for_duration(8) == 16


# =============================================================================
# DIRECTOR SERVICE TESTS
# =============================================================================

class TestDirectorService:
    """Test DirectorService."""
    
    def test_split_into_sentences(self):
        """Test sentence splitting."""
        from services.video_orchestrator.director import DirectorService
        
        director = DirectorService()
        
        text = "Hello world. This is a test! What do you think? Final sentence."
        sentences = director._split_into_sentences(text)
        
        assert len(sentences) == 4
        assert sentences[0] == "Hello world."
        assert sentences[1] == "This is a test!"
    
    def test_count_words(self):
        """Test word counting."""
        from services.video_orchestrator.director import DirectorService
        
        director = DirectorService()
        
        assert director._count_words("Hello world") == 2
        assert director._count_words("One two three four five") == 5
        assert director._count_words("") == 0
    
    def test_calculate_duration(self):
        """Test duration calculation for word counts."""
        from services.video_orchestrator.director import DirectorService
        
        director = DirectorService()
        
        # Short text -> 4s
        assert director._calculate_duration(8) == 4
        
        # Medium text -> 8s
        assert director._calculate_duration(18) == 8
        
        # Long text -> 12s
        assert director._calculate_duration(30) == 12
    
    def test_chunk_script_basic(self):
        """Test basic script chunking."""
        from services.video_orchestrator.director import DirectorService
        from services.video_orchestrator.models import PlanConstraints, PacingConstraints
        
        director = DirectorService()
        
        script = """
        Welcome to our video. This is the first part of our story.
        Now we move to the second part. Here we explain the main concept.
        Finally, we conclude with our call to action. Thank you for watching.
        """
        
        constraints = PlanConstraints(
            pacing=PacingConstraints(max_words_per_clip=25)
        )
        
        segments = director._chunk_script(script.strip(), constraints)
        
        assert len(segments) >= 1
        for segment in segments:
            assert segment.word_count <= 30  # Some tolerance
            assert segment.suggested_duration in [4, 8, 12]
    
    def test_chunk_respects_max_words(self):
        """Test chunking respects max words per clip."""
        from services.video_orchestrator.director import DirectorService
        from services.video_orchestrator.models import PlanConstraints, PacingConstraints
        
        director = DirectorService()
        
        # Long script with sentence boundaries
        script = "This is sentence one. This is sentence two. This is sentence three. This is sentence four. This is sentence five. This is sentence six. This is sentence seven. This is sentence eight."
        
        constraints = PlanConstraints(
            pacing=PacingConstraints(max_words_per_clip=15)
        )
        
        segments = director._chunk_script(script, constraints)
        
        # Should create multiple segments
        assert len(segments) >= 2
        
        # Each segment should be under limit (with some tolerance for sentence boundaries)
        for segment in segments:
            assert segment.word_count <= 20  # Some tolerance
    
    def test_validate_total_duration(self):
        """Test duration validation truncates if needed."""
        from services.video_orchestrator.director import DirectorService, ScriptSegment
        
        director = DirectorService()
        
        # Create segments totaling 400 seconds
        segments = [
            ScriptSegment(text=f"Segment {i}", word_count=20, start_index=0, end_index=10, suggested_duration=12)
            for i in range(34)  # 34 * 12 = 408s
        ]
        
        # Validate with 300s max
        validated = director._validate_total_duration(segments, 300)
        
        # Should be truncated
        total = sum(s.suggested_duration for s in validated)
        assert total <= 300
    
    def test_generate_visual_intent(self):
        """Test visual intent generation."""
        from services.video_orchestrator.director import DirectorService, ScriptSegment
        
        director = DirectorService()
        
        segment = ScriptSegment(
            text="Welcome to our amazing product demonstration.",
            word_count=6,
            start_index=0,
            end_index=50,
            suggested_duration=8
        )
        
        intent = director._generate_visual_intent(segment, None, 0, 5)
        
        assert intent.prompt != ""
        assert "opening" in intent.prompt.lower() or "Welcome" in intent.prompt
        assert len(intent.must_include) > 0
        assert "glitchy text" in intent.must_avoid
    
    def test_estimate_duration(self):
        """Test duration estimation."""
        from services.video_orchestrator.director import DirectorService
        
        director = DirectorService()
        
        # 150 words at 150 wpm = 60 seconds
        script = " ".join(["word"] * 150)
        estimate = director.estimate_duration(script)
        
        assert estimate["word_count"] == 150
        assert estimate["estimated_seconds"] == 60
        assert estimate["estimated_minutes"] == 1.0
        assert estimate["exceeds_max"] is False
        
        # 1000 words at 150 wpm = 400 seconds (exceeds 5 min)
        long_script = " ".join(["word"] * 1000)
        long_estimate = director.estimate_duration(long_script)
        
        assert long_estimate["exceeds_max"] is True


class TestDirectorCreateClipPlan:
    """Test DirectorService.create_clip_plan."""
    
    @pytest.fixture
    def sample_script(self):
        """Create sample script."""
        from services.video_orchestrator.models import VideoScript
        
        return VideoScript(
            project_id=uuid4(),
            title="Test Script",
            body="""
            Welcome to our video about amazing technology.
            Today we'll explore three key innovations that are changing the world.
            First, artificial intelligence is transforming how we work and live.
            Machine learning algorithms can now perform tasks that once required human expertise.
            Second, renewable energy is becoming more affordable and accessible.
            Solar and wind power are now competitive with traditional energy sources.
            Third, biotechnology is revolutionizing healthcare and medicine.
            New treatments and diagnostics are saving lives every day.
            Thank you for watching. Don't forget to subscribe!
            """,
            language="en"
        )
    
    @pytest.mark.asyncio
    async def test_create_clip_plan_basic(self, sample_script):
        """Test basic clip plan creation."""
        from services.video_orchestrator.director import DirectorService
        from services.video_orchestrator.models import PlanStatus, ClipState
        
        director = DirectorService()
        
        plan, scene, clips = await director.create_clip_plan(sample_script)
        
        # Verify plan
        assert plan.status == PlanStatus.DRAFT
        assert plan.script_id == sample_script.id
        assert plan.project_id == sample_script.project_id
        
        # Verify scene
        assert scene.name == "Main Content"
        assert scene.clip_plan_id == plan.id
        
        # Verify clips
        assert len(clips) > 0
        for i, clip in enumerate(clips):
            assert clip.scene_id == scene.id
            assert clip.clip_order == i
            assert clip.state == ClipState.PENDING
            assert clip.target_seconds in [4, 8, 12]
            assert clip.narration.text != ""
    
    @pytest.mark.asyncio
    async def test_create_clip_plan_with_brief(self, sample_script):
        """Test clip plan with content brief."""
        from services.video_orchestrator.director import DirectorService
        from services.video_orchestrator.models import ContentBrief
        
        director = DirectorService()
        
        brief = ContentBrief(
            project_id=sample_script.project_id,
            objective="Explain new technology trends",
            audience="Tech enthusiasts",
            tone="Professional and engaging",
            key_points=["AI", "renewable energy", "biotechnology"]
        )
        
        plan, scene, clips = await director.create_clip_plan(sample_script, brief)
        
        assert plan.brief_id == brief.id
        assert scene.goal == brief.objective
    
    @pytest.mark.asyncio
    async def test_create_clip_plan_respects_constraints(self, sample_script):
        """Test clip plan respects constraints."""
        from services.video_orchestrator.director import DirectorService
        from services.video_orchestrator.models import PlanConstraints, PacingConstraints
        
        director = DirectorService()
        
        constraints = PlanConstraints(
            max_total_seconds=60,  # Only 60 seconds
            default_clip_seconds=8,
            pacing=PacingConstraints(
                words_per_minute=150,
                max_words_per_clip=20
            )
        )
        
        plan, scene, clips = await director.create_clip_plan(
            sample_script,
            constraints=constraints
        )
        
        total_duration = sum(c.target_seconds for c in clips)
        assert total_duration <= 60
    
    @pytest.mark.asyncio
    async def test_plan_json_contains_summary(self, sample_script):
        """Test plan_json contains clip summary."""
        from services.video_orchestrator.director import DirectorService
        
        director = DirectorService()
        
        plan, scene, clips = await director.create_clip_plan(sample_script)
        
        assert "total_clips" in plan.plan_json
        assert "total_duration" in plan.plan_json
        assert "segments" in plan.plan_json
        assert plan.plan_json["total_clips"] == len(clips)


# =============================================================================
# SCENE CRAFTER TESTS
# =============================================================================

class TestStyleRules:
    """Test StyleRules parsing."""
    
    def test_to_prompt_fragment(self):
        """Test StyleRules to prompt conversion."""
        from services.video_orchestrator.scene_crafter import StyleRules
        
        rules = StyleRules(
            lighting="soft natural light",
            color_palette=["blue", "white", "gray"],
            mood="professional",
            visual_style="modern minimalist"
        )
        
        fragment = rules.to_prompt_fragment()
        
        assert "soft natural light" in fragment
        assert "professional" in fragment
        assert "modern minimalist" in fragment


class TestCharacterRules:
    """Test CharacterRules parsing."""
    
    def test_to_prompt_fragment(self):
        """Test CharacterRules to prompt conversion."""
        from services.video_orchestrator.scene_crafter import CharacterRules
        
        rules = CharacterRules(
            name="Alex",
            appearance="young professional, dark hair",
            clothing="business casual",
            personality_traits=["confident", "friendly"]
        )
        
        fragment = rules.to_prompt_fragment()
        
        assert "Alex" in fragment
        assert "young professional" in fragment
        assert "business casual" in fragment


class TestSceneCrafterService:
    """Test SceneCrafterService."""
    
    @pytest.fixture
    def sample_clip(self):
        """Create sample clip."""
        from services.video_orchestrator.models import (
            ClipPlanClip, NarrationConfig, VisualIntent, ProviderHints,
            AcceptanceCriteria, NarrationMode, ProviderName
        )
        
        return ClipPlanClip(
            scene_id=uuid4(),
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(
                mode=NarrationMode.EXTERNAL_VOICEOVER,
                text="Welcome to our video about technology."
            ),
            visual_intent=VisualIntent(
                prompt="A presenter in a modern studio",
                must_include=["presenter", "studio"],
                must_avoid=["glitchy text"],
                camera="medium shot",
                setting="professional environment"
            ),
            provider_hints=ProviderHints(
                primary_provider=ProviderName.SORA,
                model="sora-2",
                size="1280x720"
            ),
            acceptance=AcceptanceCriteria.default()
        )
    
    @pytest.fixture
    def sample_style_bible(self):
        """Create sample style bible."""
        from services.video_orchestrator.models import VideoBible, BibleKind
        
        return VideoBible(
            project_id=uuid4(),
            kind=BibleKind.STYLE,
            name="Corporate Style",
            body={
                "lighting": "soft studio lighting",
                "color_palette": ["blue", "white"],
                "mood": "professional",
                "visual_style": "clean and modern",
                "avoid": ["cluttered backgrounds"]
            }
        )
    
    @pytest.fixture
    def sample_character_bible(self):
        """Create sample character bible."""
        from services.video_orchestrator.models import VideoBible, BibleKind
        
        return VideoBible(
            project_id=uuid4(),
            kind=BibleKind.CHARACTER,
            name="Host Character",
            body={
                "name": "Alex",
                "appearance": "professional presenter, mid-30s",
                "clothing": "business casual attire",
                "personality_traits": ["confident", "approachable"]
            }
        )
    
    def test_build_baked_prompt_basic(self, sample_clip):
        """Test basic prompt building."""
        from services.video_orchestrator.scene_crafter import SceneCrafterService
        
        crafter = SceneCrafterService()
        
        prompt = crafter.build_baked_prompt(sample_clip)
        
        assert "presenter" in prompt.lower() or "studio" in prompt.lower()
        assert "medium shot" in prompt.lower()
        assert "glitchy text" in prompt.lower()  # In avoid
    
    def test_build_baked_prompt_with_bibles(
        self, sample_clip, sample_style_bible, sample_character_bible
    ):
        """Test prompt building with bibles."""
        from services.video_orchestrator.scene_crafter import SceneCrafterService
        
        crafter = SceneCrafterService()
        
        prompt = crafter.build_baked_prompt(
            sample_clip,
            style_bible=sample_style_bible,
            character_bible=sample_character_bible
        )
        
        # Should include style elements
        assert "soft studio lighting" in prompt or "professional" in prompt
        
        # Should include character elements
        assert "Alex" in prompt or "presenter" in prompt
    
    def test_build_provider_payload(self, sample_clip):
        """Test provider payload building."""
        from services.video_orchestrator.scene_crafter import SceneCrafterService
        from services.video_providers.base import CreateClipInput
        
        crafter = SceneCrafterService()
        
        payload = crafter.build_provider_payload(sample_clip)
        
        assert isinstance(payload, CreateClipInput)
        assert payload.clip_id == str(sample_clip.id)
        assert payload.seconds == 8
        assert payload.model == "sora-2"
        assert payload.size == "1280x720"
        assert len(payload.prompt) > 0
    
    def test_build_remix_payload(self, sample_clip):
        """Test remix payload building."""
        from services.video_orchestrator.scene_crafter import SceneCrafterService
        from services.video_providers.base import RemixClipInput
        
        crafter = SceneCrafterService()
        
        payload = crafter.build_remix_payload(
            sample_clip,
            source_generation_id="gen_abc123",
            prompt_delta="Add more vibrant colors"
        )
        
        assert isinstance(payload, RemixClipInput)
        assert payload.source_generation_id == "gen_abc123"
        assert payload.prompt_delta == "Add more vibrant colors"
        assert payload.seconds == 8
    
    def test_apply_prompt_patch_append(self):
        """Test prompt patching - append mode."""
        from services.video_orchestrator.scene_crafter import SceneCrafterService
        
        crafter = SceneCrafterService()
        
        original = "A person walking in a park"
        patch = "wearing a red jacket"
        
        result = crafter.apply_prompt_patch(original, patch)
        
        assert original in result
        assert "red jacket" in result
    
    def test_apply_prompt_patch_replace(self):
        """Test prompt patching - replace mode."""
        from services.video_orchestrator.scene_crafter import SceneCrafterService
        
        crafter = SceneCrafterService()
        
        original = "A person walking in a park"
        patch = "REPLACE:A dog running on a beach"
        
        result = crafter.apply_prompt_patch(original, patch)
        
        assert result == "A dog running on a beach"
        assert original not in result
    
    def test_apply_prompt_patch_prepend(self):
        """Test prompt patching - prepend mode."""
        from services.video_orchestrator.scene_crafter import SceneCrafterService
        
        crafter = SceneCrafterService()
        
        original = "A person walking in a park"
        patch = "PREPEND:Cinematic shot of"
        
        result = crafter.apply_prompt_patch(original, patch)
        
        assert result.startswith("Cinematic shot of")
        assert original in result
    
    def test_get_provider_size_for_aspect(self):
        """Test aspect ratio to size conversion."""
        from services.video_orchestrator.scene_crafter import SceneCrafterService
        from services.video_providers.base import ProviderName
        
        crafter = SceneCrafterService()
        
        assert crafter.get_provider_size_for_aspect("16:9", ProviderName.SORA) == "1280x720"
        assert crafter.get_provider_size_for_aspect("9:16", ProviderName.SORA) == "720x1280"
    
    def test_estimate_prompt_tokens(self):
        """Test token estimation."""
        from services.video_orchestrator.scene_crafter import SceneCrafterService
        
        crafter = SceneCrafterService()
        
        # ~4 chars per token
        prompt = "A" * 400  # 400 chars = ~100 tokens
        tokens = crafter.estimate_prompt_tokens(prompt)
        
        assert tokens == 100


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestDirectorSceneCrafterIntegration:
    """Integration tests for Director + SceneCrafter workflow."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test full Director -> SceneCrafter workflow."""
        from services.video_orchestrator.director import DirectorService
        from services.video_orchestrator.scene_crafter import SceneCrafterService
        from services.video_orchestrator.models import VideoScript, VideoBible, BibleKind
        from services.video_providers.base import CreateClipInput
        
        # 1. Create script
        script = VideoScript(
            project_id=uuid4(),
            title="Product Demo",
            body="""
            Welcome to our product demonstration.
            Today we'll show you three amazing features.
            First, the intuitive user interface makes everything easy.
            Second, powerful automation saves you time.
            Third, seamless integration connects all your tools.
            Thank you for watching!
            """
        )
        
        # 2. Create bibles
        style_bible = VideoBible(
            project_id=script.project_id,
            kind=BibleKind.STYLE,
            name="Demo Style",
            body={
                "lighting": "bright studio",
                "mood": "enthusiastic",
                "visual_style": "modern tech"
            }
        )
        
        # 3. Director creates plan
        director = DirectorService()
        plan, scene, clips = await director.create_clip_plan(script)
        
        assert len(clips) >= 1  # At least one clip
        
        # 4. SceneCrafter builds payloads
        crafter = SceneCrafterService()
        payloads = []
        
        for clip in clips:
            payload = crafter.build_provider_payload(
                clip,
                style_bible=style_bible
            )
            payloads.append(payload)
            
            assert isinstance(payload, CreateClipInput)
            assert payload.seconds in [4, 8, 12]
            assert len(payload.prompt) > 0
        
        # 5. Verify all clips have payloads
        assert len(payloads) == len(clips)
        
        # 6. Verify total duration is reasonable
        total_duration = sum(p.seconds for p in payloads)
        assert total_duration <= 300  # Max 5 minutes


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
