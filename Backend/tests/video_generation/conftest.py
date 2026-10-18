"""
Pytest configuration and shared fixtures for video generation tests.
"""

import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_script():
    """Sample script for testing."""
    return """
    I tried to automate SFX in Motion Canvas.
    The problem is timing gets messy with multiple clips.
    Here's the fix: generate one audio bus.
    Now renders are locked and audio stays perfect.
    Comment TECH for the template.
    """


@pytest.fixture
def sample_story_ir_dict():
    """Sample Story IR as dict for testing."""
    return {
        "meta": {
            "fps": 30,
            "aspect": "9:16",
            "title": "Test Video",
        },
        "beats": [
            {
                "id": "beat_hook",
                "type": "HOOK",
                "duration_s": 2.5,
                "narration": "I tried to automate SFX in Motion Canvas.",
            },
            {
                "id": "beat_problem",
                "type": "PROBLEM",
                "duration_s": 3.0,
                "narration": "The problem is timing gets messy.",
            },
            {
                "id": "beat_reveal",
                "type": "REVEAL",
                "duration_s": 4.0,
                "narration": "Here's the fix: generate one audio bus.",
            },
            {
                "id": "beat_success",
                "type": "SUCCESS",
                "duration_s": 3.0,
                "narration": "Now renders are locked and audio stays perfect.",
            },
            {
                "id": "beat_cta",
                "type": "CTA",
                "duration_s": 2.5,
                "narration": "Comment TECH for the template.",
            },
        ],
    }


@pytest.fixture
def sample_render_plan():
    """Sample Remotion render plan for testing."""
    return {
        "version": "2.0.0",
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "durationInFrames": 450,  # 15 seconds at 30fps
        "layers": [
            {
                "id": "bg_hook",
                "kind": "VIDEO",
                "from": 0,
                "durationInFrames": 75,
                "src": "plates/plate_hook.mp4",
                "zIndex": 0,
                "muted": True,
            },
            {
                "id": "bg_problem",
                "kind": "VIDEO",
                "from": 75,
                "durationInFrames": 90,
                "src": "plates/plate_problem.mp4",
                "zIndex": 0,
                "muted": True,
            },
            {
                "id": "bg_reveal",
                "kind": "VIDEO",
                "from": 165,
                "durationInFrames": 120,
                "src": "plates/plate_reveal.mp4",
                "zIndex": 0,
                "muted": True,
            },
            {
                "id": "bg_success",
                "kind": "VIDEO",
                "from": 285,
                "durationInFrames": 90,
                "src": "plates/plate_success.mp4",
                "zIndex": 0,
                "muted": True,
            },
            {
                "id": "bg_cta",
                "kind": "VIDEO",
                "from": 375,
                "durationInFrames": 75,
                "src": "plates/plate_cta.mp4",
                "zIndex": 0,
                "muted": True,
            },
        ],
    }


@pytest.fixture
def sample_sfx_cues():
    """Sample SFX cues for testing."""
    from services.video_generation.remotion_sfx import RemotionSfxCue
    
    return [
        RemotionSfxCue(frame=0, sfx_id="whoosh_fast", volume=1.0),
        RemotionSfxCue(frame=75, sfx_id="transition_soft", volume=0.8),
        RemotionSfxCue(frame=165, sfx_id="reveal_chime", volume=0.9),
        RemotionSfxCue(frame=285, sfx_id="success_ding", volume=0.85),
        RemotionSfxCue(frame=375, sfx_id="cta_pop", volume=0.9),
    ]


@pytest.fixture
def sample_narration_cues():
    """Sample narration cues for testing."""
    return [
        {"beatId": "beat_hook", "fromFrame": 0, "durationInFrames": 75, "durationSeconds": 2.5},
        {"beatId": "beat_problem", "fromFrame": 75, "durationInFrames": 90, "durationSeconds": 3.0},
        {"beatId": "beat_reveal", "fromFrame": 165, "durationInFrames": 120, "durationSeconds": 4.0},
        {"beatId": "beat_success", "fromFrame": 285, "durationInFrames": 90, "durationSeconds": 3.0},
        {"beatId": "beat_cta", "fromFrame": 375, "durationInFrames": 75, "durationSeconds": 2.5},
    ]


@pytest.fixture
def mock_sfx_directory(temp_output_dir):
    """Create mock SFX files for testing."""
    sfx_dir = os.path.join(temp_output_dir, "sfx")
    os.makedirs(sfx_dir, exist_ok=True)
    
    sfx_files = [
        "whoosh_fast.wav",
        "transition_soft.wav",
        "reveal_chime.wav",
        "success_ding.wav",
        "cta_pop.wav",
    ]
    
    for sfx_file in sfx_files:
        path = os.path.join(sfx_dir, sfx_file)
        with open(path, "wb") as f:
            # Write minimal WAV header (44 bytes) + some data
            f.write(b"RIFF")
            f.write((44 + 1000).to_bytes(4, "little"))
            f.write(b"WAVEfmt ")
            f.write((16).to_bytes(4, "little"))
            f.write((1).to_bytes(2, "little"))  # PCM
            f.write((1).to_bytes(2, "little"))  # Mono
            f.write((44100).to_bytes(4, "little"))  # Sample rate
            f.write((44100).to_bytes(4, "little"))  # Byte rate
            f.write((1).to_bytes(2, "little"))  # Block align
            f.write((8).to_bytes(2, "little"))  # Bits per sample
            f.write(b"data")
            f.write((1000).to_bytes(4, "little"))
            f.write(b"\x80" * 1000)  # Silence
    
    return sfx_dir


@pytest.fixture
def pipeline_config(temp_output_dir):
    """Create pipeline configuration for testing."""
    from services.video_generation.pipeline_orchestrator import PipelineConfig
    
    return PipelineConfig(
        output_dir=temp_output_dir,
        project_name="test_video",
        format_family="explainer",
        aspect="9:16",
        fps=30,
        max_sora_jobs=5,
        max_total_seconds=60,
        renderer="ffmpeg",  # Use FFmpeg for testing (no external deps)
    )


@pytest.fixture
def voice_vars_third_person():
    """Voice vars for third person TTS."""
    from services.video_generation.perspective_enforcer import VoiceVars
    
    return VoiceVars(
        use_third_person_tts=True,
        perspective="third_person",
        enforce_perspective="SOFT_REWRITE",
        third_person_subject="He",
        tts_provider="huggingface",
        tts_model_id="facebook/mms-tts-eng",
    )


@pytest.fixture
def runtime_budget_strict():
    """Strict runtime budget for testing."""
    from services.video_generation.runtime_budget import RuntimeBudget
    
    return RuntimeBudget(
        max_total_seconds=30,
        vo_speedup_limit=1.15,
        buffer_scale_min=0.7,
    )


@pytest.fixture
def runtime_budget_relaxed():
    """Relaxed runtime budget for testing."""
    from services.video_generation.runtime_budget import RuntimeBudget
    
    return RuntimeBudget(
        max_total_seconds=120,
        vo_speedup_limit=1.0,
        buffer_scale_min=1.0,
    )
