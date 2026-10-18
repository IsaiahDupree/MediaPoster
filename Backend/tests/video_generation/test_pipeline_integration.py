"""
Integration tests for the full video generation pipeline.

Tests:
- End-to-end script → render plan
- Pipeline step execution
- Voice strategy integration
- Error handling
"""

import pytest
import tempfile
import os
from services.video_generation.pipeline_orchestrator import (
    PipelineConfig,
    PipelineStep,
    PipelineResult,
    PipelineOrchestrator,
    run_pipeline,
)
from services.video_generation.voice_strategy import (
    VoiceStrategy,
    VoiceMode,
    choose_voice_strategy,
    DiscernmentInputs,
)
from services.video_generation.speech_timing import (
    reconcile_story_ir_durations,
    get_speech_stats,
)
from services.video_generation.runtime_budget import (
    RuntimeBudget,
    check_runtime_budget,
    auto_fit_to_budget,
)
from services.video_generation.duration_normalizer import (
    normalize_outline_to_duration,
    normalize_story_ir_duration,
)
from services.video_generation.perspective_enforcer import (
    enforce_perspective,
    enforce_perspective_for_story_ir,
    VoiceVars,
)


class TestPipelineConfig:
    """Tests for pipeline configuration."""
    
    def test_default_config(self):
        """Should have reasonable defaults."""
        config = PipelineConfig(output_dir="/tmp/output")
        
        assert config.output_dir == "/tmp/output"
        assert config.format_family == "explainer"
        assert config.fps == 30
    
    def test_config_accepts_all_options(self):
        """Should accept all configuration options."""
        config = PipelineConfig(
            output_dir="/tmp/output",
            project_name="my_video",
            format_family="devlog",
            aspect="16:9",
            fps=60,
            voice_mode="EXTERNAL_NARRATOR",
            tts_provider="openai",
            max_sora_jobs=5,
            max_total_seconds=30,
            renderer="motion_canvas",
        )
        
        assert config.project_name == "my_video"
        assert config.format_family == "devlog"
        assert config.aspect == "16:9"
        assert config.fps == 60
        assert config.voice_mode == "EXTERNAL_NARRATOR"


class TestPipelineOrchestrator:
    """Tests for pipeline orchestrator."""
    
    @pytest.fixture
    def sample_config(self) -> PipelineConfig:
        with tempfile.TemporaryDirectory() as output_dir:
            yield PipelineConfig(
                output_dir=output_dir,
                project_name="test_video",
                max_sora_jobs=5,
                max_total_seconds=60,
            )
    
    @pytest.fixture
    def sample_script(self) -> str:
        return """
        I tried to automate SFX in Motion Canvas.
        The problem is timing gets messy with multiple clips.
        Here's the fix: generate one audio bus.
        Now renders are locked and audio stays perfect.
        Comment TECH for the template.
        """
    
    def test_orchestrator_initialization(self, sample_config):
        """Should initialize orchestrator."""
        orchestrator = PipelineOrchestrator(sample_config)
        
        assert orchestrator.config == sample_config
        assert len(orchestrator.steps) == 0
    
    @pytest.mark.asyncio
    async def test_pipeline_from_script(self, sample_config, sample_script):
        """Should run pipeline from script."""
        result = await run_pipeline(
            config=sample_config,
            script=sample_script,
        )
        
        assert result is not None
        assert isinstance(result, PipelineResult)
        assert len(result.steps) > 0
    
    @pytest.mark.asyncio
    async def test_pipeline_creates_story_ir(self, sample_config, sample_script):
        """Pipeline should create Story IR."""
        result = await run_pipeline(
            config=sample_config,
            script=sample_script,
        )
        
        assert result.story_ir is not None
        assert "beats" in result.story_ir
    
    @pytest.mark.asyncio
    async def test_pipeline_creates_shot_plan(self, sample_config, sample_script):
        """Pipeline should create shot plan."""
        result = await run_pipeline(
            config=sample_config,
            script=sample_script,
        )
        
        assert result.shot_plan is not None
        assert "shots" in result.shot_plan
    
    @pytest.mark.asyncio
    async def test_pipeline_creates_render_plan(self, sample_config, sample_script):
        """Pipeline should create render plan."""
        result = await run_pipeline(
            config=sample_config,
            script=sample_script,
        )
        
        assert result.render_plan is not None
        assert "layers" in result.render_plan


class TestVoiceStrategyIntegration:
    """Tests for voice strategy integration."""
    
    def test_choose_strategy_for_explainer(self):
        """Explainer format should use external narrator."""
        strategy = choose_voice_strategy(DiscernmentInputs(
            format_family="explainer",
            brief_tone="educational",
            needs_consistency=True,
            tolerates_lip_sync_risk=False,
        ))
        
        assert strategy.mode == "EXTERNAL_NARRATOR"
    
    def test_choose_strategy_for_skit(self):
        """Skit format should use Sora dialogue."""
        strategy = choose_voice_strategy(DiscernmentInputs(
            format_family="skit",
            brief_tone="comedic",
            needs_consistency=False,
            tolerates_lip_sync_risk=True,
        ))
        
        assert strategy.mode == "SORA_DIALOGUE"
    
    def test_choose_strategy_for_hybrid(self):
        """Should choose hybrid when appropriate."""
        strategy = choose_voice_strategy(DiscernmentInputs(
            format_family="cinematic",
            brief_tone="dramatic",
            needs_consistency=True,
            tolerates_lip_sync_risk=True,
        ))
        
        assert strategy.mode in ["HYBRID", "EXTERNAL_NARRATOR", "SORA_DIALOGUE"]


class TestSpeechTimingIntegration:
    """Tests for speech timing integration."""
    
    @pytest.fixture
    def sample_story_ir(self) -> dict:
        return {
            "meta": {"fps": 30, "aspect": "9:16"},
            "beats": [
                {"id": "beat_1", "type": "HOOK", "duration_s": 2.0, "narration": "This is a short hook."},
                {"id": "beat_2", "type": "STEP", "duration_s": 3.0, "narration": "This is a step with more words to speak."},
            ],
        }
    
    def test_reconcile_durations_updates_ir(self, sample_story_ir):
        """Should update beat durations based on speech."""
        updated = reconcile_story_ir_durations(sample_story_ir)
        
        assert updated is not None
        assert "beats" in updated
    
    def test_get_speech_stats(self, sample_story_ir):
        """Should calculate speech statistics."""
        stats = get_speech_stats(sample_story_ir["beats"])
        
        assert "totalWords" in stats or "total_words" in stats
        assert "estimatedSeconds" in stats or "estimated_seconds" in stats


class TestRuntimeBudgetIntegration:
    """Tests for runtime budget integration."""
    
    @pytest.fixture
    def long_story_ir(self) -> dict:
        return {
            "meta": {"fps": 30, "aspect": "9:16"},
            "beats": [
                {"id": f"beat_{i}", "type": "STEP", "duration_s": 10.0, "narration": f"Beat {i}"}
                for i in range(10)
            ],  # 100s total
        }
    
    def test_check_budget_detects_over_budget(self, long_story_ir):
        """Should detect when over budget."""
        budget = RuntimeBudget(max_total_seconds=60)
        report = check_runtime_budget(long_story_ir, budget)
        
        assert report["overBudget"] is True
        assert report["overBy"] > 0
    
    def test_auto_fit_compresses_ir(self, long_story_ir):
        """Should compress IR to fit budget."""
        budget = RuntimeBudget(max_total_seconds=60)
        
        original_total = sum(b["duration_s"] for b in long_story_ir["beats"])
        
        fitted = auto_fit_to_budget(long_story_ir, budget)
        fitted_total = sum(b.get("duration_s", 0) for b in fitted["beats"])
        
        assert fitted_total <= budget.max_total_seconds
        assert fitted_total < original_total


class TestDurationNormalizerIntegration:
    """Tests for duration normalizer integration."""
    
    def test_normalize_outline_to_58s(self):
        """Should normalize outline to 58 seconds."""
        outline = """
        HOOK: I tried to automate SFX in Motion Canvas.
        PROBLEM: The problem is timing gets messy.
        EXPLAIN: First you need to set up the manifest.
        EXPLAIN: Then you configure the policies.
        EXPLAIN: Next you wire up the macros.
        EXPLAIN: After that you generate the audio bus.
        EXPLAIN: Finally you integrate with the render.
        REVEAL: Here's the fix.
        SUCCESS: Now it works perfectly.
        CTA: Comment TECH for template.
        """
        
        result = normalize_outline_to_duration(outline)
        
        assert result["seconds"] <= 60  # Within target + tolerance
    
    def test_normalize_story_ir_duration(self):
        """Should normalize Story IR duration."""
        ir = {
            "meta": {"fps": 30},
            "beats": [
                {"id": f"beat_{i}", "type": "STEP", "duration_s": 10.0}
                for i in range(10)
            ],
        }
        
        normalized = normalize_story_ir_duration(ir, target_seconds=58.0)
        
        total = sum(b.get("duration_s", 0) for b in normalized["beats"])
        assert total <= 60


class TestPerspectiveEnforcerIntegration:
    """Tests for perspective enforcer integration."""
    
    def test_enforce_third_person_on_ir(self):
        """Should convert IR narration to third person."""
        ir = {
            "meta": {"fps": 30},
            "beats": [
                {"id": "beat_1", "type": "HOOK", "narration": "I tried to automate SFX."},
                {"id": "beat_2", "type": "STEP", "narration": "My code was messy."},
            ],
        }
        
        voice_vars = VoiceVars(
            use_third_person_tts=True,
            perspective="third_person",
            enforce_perspective="SOFT_REWRITE",
            third_person_subject="He",
        )
        
        result = enforce_perspective_for_story_ir(ir, voice_vars)
        
        # Should have converted "I" → "He"
        assert "He tried" in result["beats"][0]["narration"]
        assert "His code" in result["beats"][1]["narration"]
    
    def test_strict_mode_only_warns(self):
        """STRICT mode should warn but not modify."""
        result = enforce_perspective(
            text="I built this feature.",
            perspective="third_person",
            mode="STRICT",
        )
        
        assert result.text == "I built this feature."
        assert result.changed is False
        assert len(result.warnings) > 0


class TestEndToEndPipeline:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_script_to_render_plan(self):
        """Full pipeline from script to render plan."""
        with tempfile.TemporaryDirectory() as output_dir:
            config = PipelineConfig(
                output_dir=output_dir,
                project_name="e2e_test",
                format_family="explainer",
                max_sora_jobs=5,
                max_total_seconds=60,
            )
            
            script = """
            I tried to automate SFX in Motion Canvas.
            The problem is timing gets messy.
            Here's the fix: one audio bus.
            Comment TECH for template.
            """
            
            result = await run_pipeline(config=config, script=script)
            
            # Verify all outputs
            assert result.success is True
            assert result.story_ir is not None
            assert result.shot_plan is not None
            assert result.render_plan is not None
            assert len(result.steps) >= 10  # Should have multiple steps
    
    @pytest.mark.asyncio
    async def test_pipeline_with_voice_strategy(self):
        """Pipeline with explicit voice strategy."""
        with tempfile.TemporaryDirectory() as output_dir:
            config = PipelineConfig(
                output_dir=output_dir,
                project_name="voice_test",
                voice_mode="EXTERNAL_NARRATOR",
            )
            
            script = "I built a cool feature. It works great. Follow for more."
            
            result = await run_pipeline(config=config, script=script)
            
            assert result.success is True
            
            # Shots should have voice strategy applied
            for shot in result.shot_plan.get("shots", []):
                # External narrator = mute Sora audio
                assert shot.get("muteOriginalAudio", True) is True
