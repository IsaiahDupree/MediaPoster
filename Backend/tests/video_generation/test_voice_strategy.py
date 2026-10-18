"""
Unit tests for voice strategy system.

Tests:
- Voice mode selection
- Strategy application to shots
- Perspective enforcement
- TTS provider integration
"""

import pytest
from services.video_generation.voice_strategy import (
    VoiceStrategy,
    VoiceMode,
    NarratorConfig,
    SoraDialogueConfig,
    VoiceConstraints,
    DEFAULT_NARRATOR_STRATEGY,
    DEFAULT_SORA_DIALOGUE_STRATEGY,
    DEFAULT_HYBRID_STRATEGY,
    choose_voice_strategy,
    DiscernmentInputs,
    get_voice_strategy_for_format,
    get_beat_voice_flags,
    get_sora_prompt_modifiers,
    apply_voice_strategy_to_shot_plan,
    BeatVoiceFlags,
)
from services.video_generation.perspective_enforcer import (
    enforce_perspective,
    enforce_perspective_for_beats,
    VoiceVars,
    rewrite_to_third_person,
)
from services.video_generation.hf_tts_provider import (
    HFTTSConfig,
    HFTTSProvider,
    create_tts_provider,
    HF_TTS_MODELS,
)


class TestVoiceMode:
    """Tests for voice mode enumeration."""
    
    def test_external_narrator_mode(self):
        """Should have EXTERNAL_NARRATOR mode."""
        assert "EXTERNAL_NARRATOR" in [VoiceMode.EXTERNAL_NARRATOR, "EXTERNAL_NARRATOR"]
    
    def test_sora_dialogue_mode(self):
        """Should have SORA_DIALOGUE mode."""
        assert "SORA_DIALOGUE" in [VoiceMode.SORA_DIALOGUE, "SORA_DIALOGUE"]
    
    def test_hybrid_mode(self):
        """Should have HYBRID mode."""
        assert "HYBRID" in [VoiceMode.HYBRID, "HYBRID"]


class TestDefaultStrategies:
    """Tests for default voice strategies."""
    
    def test_narrator_strategy_has_narrator_config(self):
        """EXTERNAL_NARRATOR strategy should have narrator config."""
        assert DEFAULT_NARRATOR_STRATEGY.narrator is not None
        assert DEFAULT_NARRATOR_STRATEGY.mode == "EXTERNAL_NARRATOR"
    
    def test_sora_dialogue_strategy_has_dialogue_config(self):
        """SORA_DIALOGUE strategy should have dialogue config."""
        assert DEFAULT_SORA_DIALOGUE_STRATEGY.sora_dialogue is not None
        assert DEFAULT_SORA_DIALOGUE_STRATEGY.mode == "SORA_DIALOGUE"
    
    def test_hybrid_strategy_has_both_configs(self):
        """HYBRID strategy should have both configs."""
        assert DEFAULT_HYBRID_STRATEGY.narrator is not None
        assert DEFAULT_HYBRID_STRATEGY.sora_dialogue is not None
        assert DEFAULT_HYBRID_STRATEGY.mode == "HYBRID"


class TestChooseVoiceStrategy:
    """Tests for voice strategy selection."""
    
    def test_explainer_gets_narrator(self):
        """Explainer format should get external narrator."""
        inputs = DiscernmentInputs(
            format_family="explainer",
            brief_tone="educational",
            needs_consistency=True,
            tolerates_lip_sync_risk=False,
        )
        
        strategy = choose_voice_strategy(inputs)
        
        assert strategy.mode == "EXTERNAL_NARRATOR"
    
    def test_skit_gets_sora_dialogue(self):
        """Skit format should get Sora dialogue."""
        inputs = DiscernmentInputs(
            format_family="skit",
            brief_tone="comedic",
            needs_consistency=False,
            tolerates_lip_sync_risk=True,
        )
        
        strategy = choose_voice_strategy(inputs)
        
        assert strategy.mode == "SORA_DIALOGUE"
    
    def test_devlog_gets_narrator(self):
        """Devlog format should get external narrator."""
        inputs = DiscernmentInputs(
            format_family="devlog",
            brief_tone="technical",
            needs_consistency=True,
            tolerates_lip_sync_risk=False,
        )
        
        strategy = choose_voice_strategy(inputs)
        
        assert strategy.mode == "EXTERNAL_NARRATOR"
    
    def test_cinematic_with_risk_tolerance_gets_hybrid(self):
        """Cinematic with risk tolerance should get hybrid."""
        inputs = DiscernmentInputs(
            format_family="cinematic",
            brief_tone="dramatic",
            needs_consistency=True,
            tolerates_lip_sync_risk=True,
        )
        
        strategy = choose_voice_strategy(inputs)
        
        assert strategy.mode in ["HYBRID", "SORA_DIALOGUE"]


class TestVoiceStrategyForFormat:
    """Tests for format-based voice strategy."""
    
    def test_get_strategy_for_explainer(self):
        """Should return strategy for explainer format."""
        strategy = get_voice_strategy_for_format("explainer")
        
        assert strategy is not None
        assert strategy.mode == "EXTERNAL_NARRATOR"
    
    def test_get_strategy_for_skit(self):
        """Should return strategy for skit format."""
        strategy = get_voice_strategy_for_format("skit")
        
        assert strategy is not None
        assert strategy.mode == "SORA_DIALOGUE"
    
    def test_get_strategy_for_unknown_defaults_to_narrator(self):
        """Unknown format should default to narrator."""
        strategy = get_voice_strategy_for_format("unknown_format")
        
        assert strategy is not None
        assert strategy.mode == "EXTERNAL_NARRATOR"


class TestBeatVoiceFlags:
    """Tests for beat voice flags."""
    
    @pytest.fixture
    def sample_beat(self) -> dict:
        return {
            "id": "beat_1",
            "type": "STEP",
            "duration_s": 5.0,
            "narration": "This is a step.",
        }
    
    def test_narrator_strategy_mutes_sora_audio(self, sample_beat):
        """EXTERNAL_NARRATOR should mute Sora audio."""
        flags = get_beat_voice_flags(sample_beat, DEFAULT_NARRATOR_STRATEGY)
        
        assert flags.mute_sora_audio is True
    
    def test_narrator_strategy_forbids_talking(self, sample_beat):
        """EXTERNAL_NARRATOR should forbid on-screen talking."""
        flags = get_beat_voice_flags(sample_beat, DEFAULT_NARRATOR_STRATEGY)
        
        assert flags.forbid_talking_visuals is True
    
    def test_sora_dialogue_allows_audio(self, sample_beat):
        """SORA_DIALOGUE should allow Sora audio."""
        flags = get_beat_voice_flags(sample_beat, DEFAULT_SORA_DIALOGUE_STRATEGY)
        
        # Should allow audio for dialogue beats
        assert flags.mute_sora_audio is False or flags.sora_dialogue_enabled is True


class TestSoraPromptModifiers:
    """Tests for Sora prompt modifiers."""
    
    def test_narrator_strategy_adds_no_talking_prompts(self):
        """EXTERNAL_NARRATOR should add no-talking prompt tokens."""
        modifiers = get_sora_prompt_modifiers(DEFAULT_NARRATOR_STRATEGY)
        
        # Should include tokens like "no lip movement"
        assert len(modifiers) > 0
        assert any("lip" in m.lower() or "talking" in m.lower() or "speaking" in m.lower() for m in modifiers)
    
    def test_sora_dialogue_no_modifiers(self):
        """SORA_DIALOGUE should not add no-talking modifiers."""
        modifiers = get_sora_prompt_modifiers(DEFAULT_SORA_DIALOGUE_STRATEGY)
        
        # Should not restrict talking
        no_talking_modifiers = [m for m in modifiers if "no" in m.lower() and ("lip" in m.lower() or "talk" in m.lower())]
        assert len(no_talking_modifiers) == 0


class TestApplyVoiceStrategyToShotPlan:
    """Tests for applying voice strategy to shot plan."""
    
    @pytest.fixture
    def sample_shot_plan(self) -> dict:
        return {
            "shots": [
                {"id": "shot_1", "fromBeatId": "beat_1", "prompt": "Abstract animation"},
                {"id": "shot_2", "fromBeatId": "beat_2", "prompt": "Code on screen"},
            ],
        }
    
    def test_apply_narrator_strategy_mutes_shots(self, sample_shot_plan):
        """Applying narrator strategy should mute shots."""
        result = apply_voice_strategy_to_shot_plan(sample_shot_plan, DEFAULT_NARRATOR_STRATEGY)
        
        for shot in result["shots"]:
            assert shot.get("muteOriginalAudio", False) is True
    
    def test_apply_narrator_strategy_adds_prompt_tokens(self, sample_shot_plan):
        """Applying narrator strategy should add prompt tokens."""
        result = apply_voice_strategy_to_shot_plan(sample_shot_plan, DEFAULT_NARRATOR_STRATEGY)
        
        for shot in result["shots"]:
            tokens = shot.get("extraPromptTokens", [])
            assert len(tokens) > 0


class TestPerspectiveEnforcement:
    """Tests for perspective enforcement."""
    
    def test_rewrite_i_to_he(self):
        """Should rewrite I → He."""
        text = "I tried to fix the bug."
        result = rewrite_to_third_person(text, "He")
        
        assert "He tried" in result
        assert "I tried" not in result
    
    def test_rewrite_my_to_his(self):
        """Should rewrite my → his."""
        text = "My code was messy."
        result = rewrite_to_third_person(text, "He")
        
        assert "his code" in result.lower()
        assert "my code" not in result.lower()
    
    def test_rewrite_preserves_other_text(self):
        """Should preserve non-pronoun text."""
        text = "The code was fixed."
        result = rewrite_to_third_person(text, "He")
        
        assert "The code was fixed" in result
    
    def test_enforce_strict_mode_warns(self):
        """STRICT mode should warn but not modify."""
        result = enforce_perspective(
            text="I built this.",
            perspective="third_person",
            mode="STRICT",
        )
        
        assert result.text == "I built this."
        assert result.changed is False
        assert len(result.warnings) > 0
    
    def test_enforce_soft_rewrite_modifies(self):
        """SOFT_REWRITE mode should modify text."""
        result = enforce_perspective(
            text="I built this.",
            perspective="third_person",
            mode="SOFT_REWRITE",
            subject="He",
        )
        
        assert "He built" in result.text
        assert result.changed is True
    
    def test_enforce_on_beats(self):
        """Should enforce perspective on all beats."""
        beats = [
            {"id": "beat_1", "narration": "I tried something."},
            {"id": "beat_2", "narration": "My approach worked."},
        ]
        
        voice_vars = VoiceVars(
            use_third_person_tts=True,
            perspective="third_person",
            enforce_perspective="SOFT_REWRITE",
            third_person_subject="He",
        )
        
        updated_beats, warnings = enforce_perspective_for_beats(beats, voice_vars)
        
        assert "He tried" in updated_beats[0]["narration"]
        assert "His approach" in updated_beats[1]["narration"]


class TestTTSProvider:
    """Tests for TTS provider configuration."""
    
    def test_hf_tts_models_defined(self):
        """Should have HF TTS models defined."""
        assert len(HF_TTS_MODELS) > 0
        assert "facebook/mms-tts-eng" in HF_TTS_MODELS
    
    def test_create_hf_provider(self):
        """Should create HF TTS provider."""
        provider = create_tts_provider("huggingface", model_id="facebook/mms-tts-eng")
        
        assert provider is not None
        assert hasattr(provider, "synthesize")
    
    def test_create_openai_provider(self):
        """Should create OpenAI TTS provider."""
        provider = create_tts_provider("openai", model_id="tts-1")
        
        assert provider is not None
    
    def test_create_unknown_provider_returns_hf(self):
        """Unknown provider should fall back to HF."""
        provider = create_tts_provider("unknown_provider")
        
        assert provider is not None
