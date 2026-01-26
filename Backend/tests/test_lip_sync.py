"""
Tests for Lip-Sync Mouth Layers (CHAR-004)
"""
import pytest
from services.ai_video_pipeline.lip_sync import (
    LipSyncEngine,
    Viseme,
    WordTimestamp,
    VisemeFrame,
    LipSyncAnimation,
    get_lip_sync_engine
)


class TestLipSyncEngine:
    """Test lip-sync animation generation"""

    @pytest.mark.asyncio
    async def test_empty_word_list(self):
        """Test handling of empty word list"""
        engine = LipSyncEngine(default_fps=30)
        animation = await engine.generate_lip_sync(
            word_timestamps=[],
            fps=30
        )

        assert animation.duration == 0.0
        assert animation.total_frames == 0
        assert len(animation.frames) == 0

    @pytest.mark.asyncio
    async def test_single_word_animation(self):
        """Test animation for a single word"""
        engine = LipSyncEngine(default_fps=30)
        animation = await engine.generate_lip_sync(
            word_timestamps=[
                {"word": "hello", "start": 0.0, "end": 0.5}
            ],
            fps=30
        )

        assert animation.duration == 0.5
        assert animation.fps == 30
        assert animation.total_frames == 16  # 0.5s * 30fps + 1
        assert len(animation.frames) == 16

        # Check that frames within word time have visemes
        for frame in animation.frames:
            if 0.0 <= frame.time <= 0.5:
                assert frame.viseme != Viseme.REST or frame.intensity == 0.0
                assert frame.word == "hello"

    @pytest.mark.asyncio
    async def test_multiple_words_animation(self):
        """Test animation with multiple words"""
        engine = LipSyncEngine(default_fps=30)
        animation = await engine.generate_lip_sync(
            word_timestamps=[
                {"word": "hello", "start": 0.0, "end": 0.5},
                {"word": "world", "start": 0.6, "end": 1.1}
            ],
            fps=30,
            character_id="char_123"
        )

        assert animation.duration == 1.1
        assert animation.character_id == "char_123"
        assert len(animation.frames) == 34  # 1.1s * 30fps + 1

        # Check silence gap between words (0.5s to 0.6s)
        silence_frames = [f for f in animation.frames if 0.5 < f.time < 0.6]
        assert all(f.viseme == Viseme.REST for f in silence_frames)

    @pytest.mark.asyncio
    async def test_viseme_sequence_for_hello(self):
        """Test that 'hello' produces expected viseme sequence"""
        engine = LipSyncEngine(default_fps=30)
        animation = await engine.generate_lip_sync(
            word_timestamps=[
                {"word": "hello", "start": 0.0, "end": 0.5}
            ],
            fps=30
        )

        # Get visemes for "hello" frames
        hello_frames = [f for f in animation.frames if f.word == "hello"]
        visemes = [f.viseme for f in hello_frames]

        # Should contain E, L, O visemes (from WORD_TO_VISEME_HINTS)
        assert Viseme.E in visemes  # "h" or "e"
        assert Viseme.L in visemes  # "ll"
        assert Viseme.O in visemes  # "o"

    @pytest.mark.asyncio
    async def test_custom_fps(self):
        """Test animation with custom FPS"""
        engine = LipSyncEngine(default_fps=60)
        animation = await engine.generate_lip_sync(
            word_timestamps=[
                {"word": "test", "start": 0.0, "end": 1.0}
            ],
            fps=60
        )

        assert animation.fps == 60
        assert animation.total_frames == 61  # 1.0s * 60fps + 1
        assert len(animation.frames) == 61

    @pytest.mark.asyncio
    async def test_metadata_preservation(self):
        """Test that metadata is preserved"""
        engine = LipSyncEngine()
        metadata = {"script_id": "script_123", "version": "1.0"}

        animation = await engine.generate_lip_sync(
            word_timestamps=[
                {"word": "test", "start": 0.0, "end": 0.5}
            ],
            metadata=metadata
        )

        assert animation.metadata == metadata

    def test_frame_timing_accuracy(self):
        """Test that frame times are accurate"""
        engine = LipSyncEngine(default_fps=30)
        frames = engine._generate_frames(
            words=[WordTimestamp("test", 0.0, 1.0)],
            fps=30,
            total_frames=31
        )

        # Check frame times are evenly spaced
        for i, frame in enumerate(frames):
            expected_time = i * (1.0 / 30)
            assert abs(frame.time - expected_time) < 0.0001
            assert frame.frame_number == i

    def test_viseme_for_common_words(self):
        """Test viseme generation for common words"""
        engine = LipSyncEngine()

        # Test "hello" (has hint)
        viseme = engine._get_viseme_for_word("hello", 0.5)
        assert viseme in [Viseme.E, Viseme.L, Viseme.O]

        # Test "world" (has hint)
        viseme = engine._get_viseme_for_word("world", 0.5)
        assert viseme in [Viseme.W, Viseme.E, Viseme.L, Viseme.T]

        # Test "yes" (has hint)
        viseme = engine._get_viseme_for_word("yes", 0.5)
        assert viseme in [Viseme.E, Viseme.S]


class TestLipSyncAnimationExport:
    """Test animation export formats"""

    @pytest.mark.asyncio
    async def test_to_dict_export(self):
        """Test conversion to dictionary"""
        engine = LipSyncEngine(default_fps=30)
        animation = await engine.generate_lip_sync(
            word_timestamps=[
                {"word": "test", "start": 0.0, "end": 0.5}
            ],
            character_id="char_123"
        )

        data = animation.to_dict()

        assert "frames" in data
        assert "duration" in data
        assert "fps" in data
        assert "total_frames" in data
        assert "character_id" in data
        assert data["character_id"] == "char_123"
        assert len(data["frames"]) == len(animation.frames)

        # Check frame structure
        frame = data["frames"][0]
        assert "frame" in frame
        assert "time" in frame
        assert "viseme" in frame
        assert "intensity" in frame

    @pytest.mark.asyncio
    async def test_remotion_export(self):
        """Test Remotion-compatible export"""
        engine = LipSyncEngine(default_fps=30)
        animation = await engine.generate_lip_sync(
            word_timestamps=[
                {"word": "test", "start": 0.0, "end": 0.5}
            ],
            character_id="char_123"
        )

        remotion_data = engine.export_for_remotion(animation)

        assert remotion_data["type"] == "lip_sync_animation"
        assert remotion_data["fps"] == 30
        assert remotion_data["duration"] == 0.5
        assert remotion_data["characterId"] == "char_123"
        assert "frames" in remotion_data
        assert "durationInFrames" in remotion_data


class TestVisemeImageURLs:
    """Test viseme image URL generation"""

    def test_get_viseme_image_url(self):
        """Test URL generation for mouth layers"""
        engine = LipSyncEngine()

        url = engine.get_viseme_image_url(
            character_id="char_123",
            viseme=Viseme.A,
            base_url="/characters"
        )

        assert url == "/characters/char_123/mouth_a.png"

    def test_all_visemes_have_urls(self):
        """Test that all visemes can generate URLs"""
        engine = LipSyncEngine()

        for viseme in Viseme:
            url = engine.get_viseme_image_url(
                character_id="test_char",
                viseme=viseme
            )
            assert url.endswith(f"mouth_{viseme.value}.png")


class TestFactoryFunction:
    """Test factory function"""

    def test_get_lip_sync_engine(self):
        """Test factory function creates engine"""
        engine = get_lip_sync_engine(fps=30)
        assert isinstance(engine, LipSyncEngine)
        assert engine.default_fps == 30

    def test_get_lip_sync_engine_custom_fps(self):
        """Test factory with custom FPS"""
        engine = get_lip_sync_engine(fps=60)
        assert engine.default_fps == 60


class TestFeatureAcceptance:
    """Feature acceptance tests for CHAR-004"""

    @pytest.mark.asyncio
    async def test_acceptance_mouth_states_animate(self):
        """
        Acceptance: Mouth states animate
        Verify that mouth shapes change over time based on words
        """
        engine = LipSyncEngine(default_fps=30)
        animation = await engine.generate_lip_sync(
            word_timestamps=[
                {"word": "hello", "start": 0.0, "end": 0.5},
                {"word": "world", "start": 0.6, "end": 1.1}
            ],
            fps=30
        )

        # Get all unique visemes used
        unique_visemes = set(f.viseme for f in animation.frames)

        # Should have multiple different mouth shapes
        assert len(unique_visemes) > 1

        # Should include REST for silence
        assert Viseme.REST in unique_visemes

        # Should have visemes from words
        word_visemes = set(
            f.viseme for f in animation.frames
            if f.word is not None
        )
        assert len(word_visemes) > 0

        print("✓ Mouth states animate with changing visemes")

    @pytest.mark.asyncio
    async def test_acceptance_word_timestamps_drive_shapes(self):
        """
        Acceptance: Word timestamps drive shapes
        Verify that visemes align with word timing
        """
        engine = LipSyncEngine(default_fps=30)
        animation = await engine.generate_lip_sync(
            word_timestamps=[
                {"word": "hello", "start": 0.0, "end": 0.5},
                {"word": "world", "start": 1.0, "end": 1.5}
            ],
            fps=30
        )

        # Check frames during first word (0.0-0.5s)
        hello_frames = [f for f in animation.frames if 0.0 <= f.time <= 0.5]
        assert all(f.word == "hello" for f in hello_frames)
        assert all(f.intensity > 0.0 for f in hello_frames)

        # Check frames during silence (0.5-1.0s)
        silence_frames = [f for f in animation.frames if 0.5 < f.time < 1.0]
        assert all(f.viseme == Viseme.REST for f in silence_frames)
        assert all(f.word is None for f in silence_frames)

        # Check frames during second word (1.0-1.5s)
        world_frames = [f for f in animation.frames if 1.0 <= f.time <= 1.5]
        assert all(f.word == "world" for f in world_frames)
        assert all(f.intensity > 0.0 for f in world_frames)

        print("✓ Word timestamps accurately drive mouth shapes")
