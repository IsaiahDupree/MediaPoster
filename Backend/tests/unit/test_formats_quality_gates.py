"""
Unit tests for the Formats quality gates module.
Tests validation logic for render props and artifacts.
"""
import pytest
from unittest.mock import AsyncMock

from services.formats.quality_gates import (
    run_quality_gates,
    eval_gate,
    gate_required_fields,
    gate_duration,
    gate_captions,
    gate_audio_presence,
    gate_visual_density,
)
from services.formats.schema import GateLevel, GateResult


class TestGateRequiredFields:
    """Tests for required fields validation."""
    
    def test_all_fields_present(self):
        render_props = {
            "topic": "Test Topic",
            "script": {"segments": [{"id": "1", "text": "Hello"}]}
        }
        config = {"paths": ["topic", "script.segments"]}
        
        result = gate_required_fields("test", GateLevel.FAIL, config, render_props)
        
        assert result.ok is True
        assert "present" in result.message
    
    def test_missing_field(self):
        render_props = {"topic": "Test"}
        config = {"paths": ["topic", "script.segments"]}
        
        result = gate_required_fields("test", GateLevel.FAIL, config, render_props)
        
        assert result.ok is False
        assert "script.segments" in result.message
    
    def test_empty_paths_config(self):
        render_props = {}
        config = {"paths": []}
        
        result = gate_required_fields("test", GateLevel.WARN, config, render_props)
        
        assert result.ok is True
    
    def test_nested_missing_field(self):
        render_props = {"script": {"title": "Test"}}
        config = {"paths": ["script.segments"]}
        
        result = gate_required_fields("test", GateLevel.FAIL, config, render_props)
        
        assert result.ok is False


class TestGateDuration:
    """Tests for duration validation."""
    
    def test_within_limit(self):
        video_config = {"fps": 30, "duration_in_frames": 1500}  # 50 seconds
        config = {"maxSec": 60}
        
        result = gate_duration("dur", GateLevel.FAIL, config, video_config)
        
        assert result.ok is True
        assert "50.00s ok" in result.message
    
    def test_exceeds_limit(self):
        video_config = {"fps": 30, "duration_in_frames": 2100}  # 70 seconds
        config = {"maxSec": 60}
        
        result = gate_duration("dur", GateLevel.FAIL, config, video_config)
        
        assert result.ok is False
        assert "70.00s > 60" in result.message
    
    def test_exact_limit(self):
        video_config = {"fps": 30, "duration_in_frames": 1800}  # 60 seconds
        config = {"maxSec": 60}
        
        result = gate_duration("dur", GateLevel.FAIL, config, video_config)
        
        assert result.ok is True
    
    def test_camelCase_config(self):
        video_config = {"fps": 30, "durationInFrames": 900}  # 30 seconds
        config = {"max_sec": 60}
        
        result = gate_duration("dur", GateLevel.FAIL, config, video_config)
        
        assert result.ok is True


class TestGateCaptions:
    """Tests for caption length validation."""
    
    def test_all_captions_ok(self):
        render_props = {
            "script": {
                "segments": [
                    {"id": "1", "text": "Short caption"},
                    {"id": "2", "text": "Another short one"}
                ]
            }
        }
        config = {"maxCharsPerLine": 44}
        
        result = gate_captions("cap", GateLevel.WARN, config, render_props)
        
        assert result.ok is True
    
    def test_caption_too_long(self):
        render_props = {
            "script": {
                "segments": [
                    {"id": "1", "text": "This is a very long caption that exceeds the maximum allowed characters per line limit"}
                ]
            }
        }
        config = {"maxCharsPerLine": 44}
        
        result = gate_captions("cap", GateLevel.WARN, config, render_props)
        
        assert result.ok is False
        assert "1" in result.message
    
    def test_empty_segments(self):
        render_props = {"script": {"segments": []}}
        config = {"maxCharsPerLine": 44}
        
        result = gate_captions("cap", GateLevel.WARN, config, render_props)
        
        assert result.ok is True
    
    def test_multiple_long_captions(self):
        long_text = "A" * 50
        render_props = {
            "script": {
                "segments": [
                    {"id": "1", "text": long_text},
                    {"id": "2", "text": "ok"},
                    {"id": "3", "text": long_text},
                    {"id": "4", "text": long_text},
                    {"id": "5", "text": long_text},
                    {"id": "6", "text": long_text},
                    {"id": "7", "text": long_text},
                ]
            }
        }
        config = {"maxCharsPerLine": 44}
        
        result = gate_captions("cap", GateLevel.WARN, config, render_props)
        
        assert result.ok is False
        assert "…" in result.message  # Truncated list


class TestGateAudioPresence:
    """Tests for audio artifact validation."""
    
    def test_voice_present(self):
        artifacts = {"voice_url": "https://example.com/voice.mp3"}
        config = {"requireVoice": True}
        
        result = gate_audio_presence("audio", GateLevel.FAIL, config, artifacts)
        
        assert result.ok is True
    
    def test_voice_missing_required(self):
        artifacts = {}
        config = {"requireVoice": True}
        
        result = gate_audio_presence("audio", GateLevel.FAIL, config, artifacts)
        
        assert result.ok is False
        assert "missing voice" in result.message
    
    def test_voice_not_required(self):
        artifacts = {}
        config = {"requireVoice": False}
        
        result = gate_audio_presence("audio", GateLevel.WARN, config, artifacts)
        
        assert result.ok is True
    
    def test_nested_voice_url(self):
        artifacts = {"voice": {"url": "https://example.com/voice.mp3"}}
        config = {"require_voice": True}
        
        result = gate_audio_presence("audio", GateLevel.FAIL, config, artifacts)
        
        assert result.ok is True


class TestGateVisualDensity:
    """Tests for on-screen text density validation."""
    
    def test_density_ok(self):
        render_props = {
            "script": {
                "segments": [
                    {"id": "1", "on_screen": ["Word1", "Word2", "Word3"]}
                ]
            }
        }
        config = {"maxOnScreenWords": 12}
        
        result = gate_visual_density("vis", GateLevel.WARN, config, render_props)
        
        assert result.ok is True
    
    def test_too_many_words(self):
        render_props = {
            "script": {
                "segments": [
                    {"id": "1", "on_screen": ["This is a very long on-screen text that has way too many words for comfortable reading"]}
                ]
            }
        }
        config = {"maxOnScreenWords": 12}
        
        result = gate_visual_density("vis", GateLevel.WARN, config, render_props)
        
        assert result.ok is False
    
    def test_no_on_screen_text(self):
        render_props = {
            "script": {
                "segments": [{"id": "1", "text": "Spoken only"}]
            }
        }
        config = {"maxOnScreenWords": 12}
        
        result = gate_visual_density("vis", GateLevel.WARN, config, render_props)
        
        assert result.ok is True


class TestEvalGate:
    """Tests for gate evaluation dispatcher."""
    
    def test_unknown_gate_type_passes(self):
        gate = {"id": "unknown", "type": "future_gate", "level": "warn", "config": {}}
        
        result = eval_gate(gate, {}, {}, {})
        
        assert result.ok is True
        assert "unknown gate type" in result.message
    
    def test_gate_error_handling(self):
        gate = {"id": "error", "type": "required_fields", "level": "fail", "config": {"paths": None}}
        
        result = eval_gate(gate, {}, {}, {})
        
        assert result.ok is False
        assert "error" in result.message.lower()


class TestRunQualityGates:
    """Integration tests for full quality gate runs."""
    
    @pytest.mark.asyncio
    async def test_all_gates_pass(self):
        format_def = {"gates": []}
        quality_profile = {
            "gates_json": [
                {"id": "req", "type": "required_fields", "level": "fail", "config": {"paths": ["topic"]}}
            ]
        }
        render_props = {"topic": "Test", "script": {"segments": []}}
        video_config = {"fps": 30, "duration_in_frames": 900}
        
        result = await run_quality_gates(
            "pre", format_def, quality_profile, render_props, video_config
        )
        
        assert result.ok is True
        assert len(result.results) == 1
    
    @pytest.mark.asyncio
    async def test_fail_gate_stops_execution(self):
        format_def = {"gates": []}
        quality_profile = {
            "gates_json": [
                {"id": "req", "type": "required_fields", "level": "fail", "config": {"paths": ["missing"]}},
                {"id": "dur", "type": "duration", "level": "fail", "config": {"maxSec": 60}}
            ]
        }
        render_props = {"topic": "Test"}
        video_config = {"fps": 30, "duration_in_frames": 900}
        
        result = await run_quality_gates(
            "pre", format_def, quality_profile, render_props, video_config
        )
        
        assert result.ok is False
        # First gate fails, second might not be evaluated
        assert any(not r.ok for r in result.results)
    
    @pytest.mark.asyncio
    async def test_warn_gates_dont_fail(self):
        format_def = {"gates": []}
        quality_profile = {
            "gates_json": [
                {"id": "cap", "type": "captions", "level": "warn", "config": {"maxCharsPerLine": 10}}
            ]
        }
        render_props = {
            "topic": "Test",
            "script": {"segments": [{"id": "1", "text": "This is longer than 10 chars"}]}
        }
        video_config = {"fps": 30, "duration_in_frames": 900}
        
        result = await run_quality_gates(
            "pre", format_def, quality_profile, render_props, video_config
        )
        
        # Warn level doesn't cause overall failure
        assert result.ok is True
        assert not result.results[0].ok  # Individual gate failed
    
    @pytest.mark.asyncio
    async def test_combines_profile_and_format_gates(self):
        format_def = {
            "gates": [{"id": "format_gate", "type": "duration", "level": "warn", "config": {"maxSec": 30}}]
        }
        quality_profile = {
            "gates_json": [{"id": "profile_gate", "type": "required_fields", "level": "fail", "config": {"paths": ["topic"]}}]
        }
        render_props = {"topic": "Test"}
        video_config = {"fps": 30, "duration_in_frames": 600}  # 20 seconds
        
        result = await run_quality_gates(
            "pre", format_def, quality_profile, render_props, video_config
        )
        
        assert result.ok is True
        assert len(result.results) == 2
        gate_ids = [r.gate_id for r in result.results]
        assert "profile_gate" in gate_ids
        assert "format_gate" in gate_ids
