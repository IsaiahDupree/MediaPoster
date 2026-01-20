"""
Unit tests for SFX Library features.

Tests for:
- SFX-001: SFX Library Manifest
- SFX-002: Beat Extractor
- SFX-003: AI SFX Selection
- SFX-004: Audio Events Timeline
- SFX-005: FFmpeg Audio Mixer
- SFX-006: SFX QA Gates
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime

from services.sfx_library.types import (
    SfxItem,
    SfxManifest,
    SfxLicense,
    SfxAudioEvent,
    MusicAudioEvent,
    VoiceoverAudioEvent,
    AudioEvents,
)
from services.sfx_library.manifest import (
    load_manifest,
    save_manifest,
    get_sfx_by_id,
    search_sfx_by_tags,
)
from services.sfx_library.beat_extractor import extract_beats_from_script
from services.sfx_library.audio_utils import (
    merge_audio_events,
    clamp_events_to_duration,
    snap_sfx_to_beats,
    thin_sfx_events,
    finalize_audio_events,
    get_sfx_density_stats,
)
from services.sfx_library.validator import (
    validate_audio_events,
    validate_and_fix_events,
    run_qa_gate,
)
from services.sfx_library.context_pack import build_sfx_context_pack
from services.media_factory.contracts.script import ScriptSchema, ScriptBeatSchema


class TestSfxManifest:
    """Tests for SFX-001: SFX Library Manifest"""

    def test_create_sfx_item(self):
        """Test creating an SFX item"""
        item = SfxItem(
            id="whoosh_001",
            file="sfx/whoosh_fast.wav",
            tags=["whoosh", "transition", "fast"],
            description="Fast whoosh transition",
            intensity=7,
            category="transition",
        )

        assert item.id == "whoosh_001"
        assert item.file == "sfx/whoosh_fast.wav"
        assert "whoosh" in item.tags
        assert item.intensity == 7
        assert item.category == "transition"

    def test_create_sfx_manifest(self):
        """Test creating an SFX manifest"""
        items = [
            SfxItem(
                id="whoosh_001",
                file="sfx/whoosh_fast.wav",
                tags=["whoosh", "transition"],
                description="Fast whoosh",
                intensity=7,
            ),
            SfxItem(
                id="impact_001",
                file="sfx/impact_heavy.wav",
                tags=["impact", "heavy"],
                description="Heavy impact",
                intensity=9,
            ),
        ]

        manifest = SfxManifest(version="1.0", items=items)

        assert manifest.version == "1.0"
        assert len(manifest.items) == 2
        assert manifest.get_by_id("whoosh_001") is not None
        assert manifest.get_by_id("impact_001") is not None
        assert manifest.get_by_id("nonexistent") is None

    def test_manifest_get_id_set(self):
        """Test getting ID set from manifest"""
        items = [
            SfxItem(id="sfx_001", file="a.wav", tags=["test"]),
            SfxItem(id="sfx_002", file="b.wav", tags=["test"]),
        ]
        manifest = SfxManifest(version="1.0", items=items)

        id_set = manifest.get_id_set()
        assert id_set == {"sfx_001", "sfx_002"}

    def test_save_and_load_manifest(self):
        """Test saving and loading manifest"""
        items = [
            SfxItem(
                id="test_001",
                file="test.wav",
                tags=["test"],
                description="Test SFX",
                intensity=5,
                category="ui",
            )
        ]
        manifest = SfxManifest(version="1.0", items=items)

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"

            # Save
            save_manifest(manifest, manifest_path)
            assert manifest_path.exists()

            # Load
            loaded = load_manifest(manifest_path)
            assert loaded.version == "1.0"
            assert len(loaded.items) == 1
            assert loaded.items[0].id == "test_001"
            assert loaded.items[0].intensity == 5

    def test_search_sfx_by_tags(self):
        """Test searching SFX by tags"""
        items = [
            SfxItem(id="whoosh_001", file="a.wav", tags=["whoosh", "fast", "transition"]),
            SfxItem(id="whoosh_002", file="b.wav", tags=["whoosh", "slow", "transition"]),
            SfxItem(id="impact_001", file="c.wav", tags=["impact", "heavy"]),
        ]
        manifest = SfxManifest(version="1.0", items=items)

        # Search for whoosh
        results = search_sfx_by_tags(manifest, ["whoosh"])
        assert len(results) == 2
        assert all("whoosh" in r.tags for r in results)

        # Search for fast whoosh
        results = search_sfx_by_tags(manifest, ["whoosh", "fast"])
        assert len(results) == 2  # Both whoosh items match at least one tag
        # First result should have better match (both tags)
        assert "fast" in results[0].tags

        # Search for impact
        results = search_sfx_by_tags(manifest, ["impact"])
        assert len(results) == 1
        assert results[0].id == "impact_001"

    def test_get_sfx_by_id(self):
        """Test getting SFX by ID"""
        items = [
            SfxItem(id="sfx_001", file="a.wav", tags=["test"]),
            SfxItem(id="sfx_002", file="b.wav", tags=["test"]),
        ]
        manifest = SfxManifest(version="1.0", items=items)

        item = get_sfx_by_id(manifest, "sfx_001")
        assert item is not None
        assert item.id == "sfx_001"

        item = get_sfx_by_id(manifest, "nonexistent")
        assert item is None


class TestAudioEvents:
    """Tests for SFX-004: Audio Events Timeline"""

    def test_create_sfx_audio_event(self):
        """Test creating SFX audio event"""
        event = SfxAudioEvent(sfx_id="whoosh_001", frame=30, volume=0.8)

        assert event.type == "sfx"
        assert event.sfx_id == "whoosh_001"
        assert event.frame == 30
        assert event.volume == 0.8

    def test_create_music_audio_event(self):
        """Test creating music audio event"""
        event = MusicAudioEvent(src="music.mp3", frame=0, volume=0.3)

        assert event.type == "music"
        assert event.src == "music.mp3"
        assert event.frame == 0
        assert event.volume == 0.3

    def test_create_voiceover_audio_event(self):
        """Test creating voiceover audio event"""
        event = VoiceoverAudioEvent(src="voice.wav", frame=0, volume=1.0)

        assert event.type == "voiceover"
        assert event.src == "voice.wav"
        assert event.frame == 0
        assert event.volume == 1.0

    def test_audio_events_timeline(self):
        """Test audio events timeline"""
        events = [
            VoiceoverAudioEvent(src="voice.wav", frame=0, volume=1.0),
            MusicAudioEvent(src="music.mp3", frame=0, volume=0.25),
            SfxAudioEvent(sfx_id="whoosh_001", frame=30, volume=0.8),
            SfxAudioEvent(sfx_id="impact_001", frame=90, volume=0.9),
        ]

        timeline = AudioEvents(fps=30, events=events)

        assert timeline.fps == 30
        assert len(timeline.events) == 4

        # Test filtering
        sfx_events = timeline.get_sfx_events()
        assert len(sfx_events) == 2
        assert all(e.type == "sfx" for e in sfx_events)

        music_events = timeline.get_music_events()
        assert len(music_events) == 1
        assert music_events[0].type == "music"

        voiceover_events = timeline.get_voiceover_events()
        assert len(voiceover_events) == 1
        assert voiceover_events[0].type == "voiceover"

    def test_merge_audio_events(self):
        """Test merging audio events"""
        base = AudioEvents(
            fps=30,
            events=[
                VoiceoverAudioEvent(src="voice.wav", frame=0, volume=1.0),
                MusicAudioEvent(src="music.mp3", frame=0, volume=0.3),
            ],
        )

        sfx_only = AudioEvents(
            fps=30,
            events=[
                SfxAudioEvent(sfx_id="whoosh_001", frame=30, volume=0.8),
                SfxAudioEvent(sfx_id="impact_001", frame=90, volume=0.9),
            ],
        )

        merged = merge_audio_events(base, sfx_only)

        assert merged.fps == 30
        assert len(merged.events) == 4
        assert len(merged.get_voiceover_events()) == 1
        assert len(merged.get_music_events()) == 1
        assert len(merged.get_sfx_events()) == 2

    def test_clamp_events_to_duration(self):
        """Test clamping events to duration"""
        events = AudioEvents(
            fps=30,
            events=[
                SfxAudioEvent(sfx_id="sfx_001", frame=30, volume=0.8),
                SfxAudioEvent(sfx_id="sfx_002", frame=90, volume=0.8),
                SfxAudioEvent(sfx_id="sfx_003", frame=150, volume=0.8),  # Beyond duration
            ],
        )

        # Clamp to 120 frames (4 seconds at 30fps)
        clamped = clamp_events_to_duration(events, 120, drop_if_beyond=True)

        sfx_events = clamped.get_sfx_events()
        assert len(sfx_events) == 2  # Third event dropped
        assert all(e.frame <= 120 for e in sfx_events)

    def test_get_sfx_density_stats(self):
        """Test SFX density statistics"""
        events = AudioEvents(
            fps=30,
            events=[
                VoiceoverAudioEvent(src="voice.wav", frame=0, volume=1.0),
                SfxAudioEvent(sfx_id="sfx_001", frame=30, volume=0.8),
                SfxAudioEvent(sfx_id="sfx_002", frame=60, volume=0.8),
                SfxAudioEvent(sfx_id="sfx_003", frame=90, volume=0.8),
            ],
        )

        stats = get_sfx_density_stats(events)

        assert "sfx_count" in stats
        assert "total_frames" in stats
        assert "density" in stats
        assert stats["sfx_count"] == 3
        assert stats["density"] > 0


class TestBeatExtractor:
    """Tests for SFX-002: Beat Extractor"""

    def test_extract_beats_from_script(self):
        """Test extracting narrative beats from script"""
        # Create a sample script
        beats = [
            ScriptBeatSchema(
                id="seg_001",
                t="0-3",
                text="This is the hook that grabs attention",
                intent="hook",
                on_screen=["bold text"],
                visual_style="big_text_punch_in",
                emphasis_words=["hook", "attention"],
            ),
            ScriptBeatSchema(
                id="seg_002",
                t="3-8",
                text="Here's the problem everyone faces",
                intent="problem",
                on_screen=["problem illustration"],
                visual_style="diagram",
                emphasis_words=["problem"],
            ),
            ScriptBeatSchema(
                id="seg_003",
                t="8-15",
                text="And here's the solution that solves it",
                intent="solution",
                on_screen=["solution demo"],
                visual_style="b_roll",
                emphasis_words=["solution", "solves"],
            ),
        ]

        script = ScriptSchema(
            brief_id="test_brief",
            title="Test Video",
            hook="Hook text",
            segments=beats,
            metadata={"total_duration_sec": 15, "word_count": 30},
        )

        # Extract beats
        extracted_beats = extract_beats_from_script(script)

        # Should extract narrative beats from script
        assert len(extracted_beats) >= 3
        assert any(b.get("intent") == "hook" for b in extracted_beats)
        assert any(b.get("intent") == "problem" for b in extracted_beats)
        assert any(b.get("intent") == "solution" for b in extracted_beats)


class TestSfxValidator:
    """Tests for SFX-006: SFX QA Gates"""

    def test_validate_audio_events(self):
        """Test audio events validation"""
        manifest = SfxManifest(
            version="1.0",
            items=[
                SfxItem(id="whoosh_001", file="a.wav", tags=["whoosh"]),
                SfxItem(id="impact_001", file="b.wav", tags=["impact"]),
            ],
        )

        events = AudioEvents(
            fps=30,
            events=[
                VoiceoverAudioEvent(src="voice.wav", frame=0, volume=1.0),
                SfxAudioEvent(sfx_id="whoosh_001", frame=30, volume=0.8),
                SfxAudioEvent(sfx_id="impact_001", frame=90, volume=0.9),
            ],
        )

        # Should validate successfully - returns empty list for valid events
        invalid_ids = validate_audio_events(events, manifest)
        assert len(invalid_ids) == 0

    def test_validate_audio_events_with_invalid_ids(self):
        """Test audio events validation with invalid IDs"""
        manifest = SfxManifest(
            version="1.0",
            items=[
                SfxItem(id="whoosh_001", file="a.wav", tags=["whoosh"]),
            ],
        )

        events = AudioEvents(
            fps=30,
            events=[
                SfxAudioEvent(sfx_id="whoosh_001", frame=30, volume=0.8),
                SfxAudioEvent(sfx_id="nonexistent_001", frame=90, volume=0.9),
            ],
        )

        # Should return list of invalid IDs
        invalid_ids = validate_audio_events(events, manifest)
        assert len(invalid_ids) == 1
        assert "nonexistent_001" in invalid_ids

    def test_validate_and_fix_events(self):
        """Test validating and auto-fixing events"""
        manifest = SfxManifest(
            version="1.0",
            items=[
                SfxItem(id="whoosh_001", file="a.wav", tags=["whoosh", "fast"]),
                SfxItem(id="impact_001", file="b.wav", tags=["impact", "heavy"]),
            ],
        )

        events = AudioEvents(
            fps=30,
            events=[
                SfxAudioEvent(sfx_id="whoosh_001", frame=30, volume=0.8),
                SfxAudioEvent(sfx_id="whoosh_002", frame=60, volume=0.8),  # Invalid but similar
            ],
        )

        # Should auto-fix similar IDs
        cleaned, report = validate_and_fix_events(events, manifest, allow_auto_fix=True)

        # Check that we got cleaned events
        assert len(cleaned.get_sfx_events()) >= 1

    def test_run_qa_gate(self):
        """Test QA gate for audio timeline"""
        manifest = SfxManifest(
            version="1.0",
            items=[
                SfxItem(id="whoosh_001", file="a.wav", tags=["whoosh"]),
                SfxItem(id="impact_001", file="b.wav", tags=["impact"]),
            ],
        )

        events = AudioEvents(
            fps=30,
            events=[
                SfxAudioEvent(sfx_id="whoosh_001", frame=30, volume=0.8),
                SfxAudioEvent(sfx_id="impact_001", frame=90, volume=0.9),
            ],
        )

        # Should pass QA gate
        qa_report = run_qa_gate(events, manifest)
        assert qa_report.passed is True
        assert len(qa_report.issues) == 0


class TestSfxContextPack:
    """Tests for SFX-003: AI SFX Selection context generation"""

    def test_build_sfx_context_pack(self):
        """Test building SFX context pack for LLMs"""
        items = [
            SfxItem(
                id="whoosh_001",
                file="whoosh.wav",
                tags=["whoosh", "fast", "transition"],
                description="Fast whoosh transition",
                intensity=7,
                category="transition",
            ),
            SfxItem(
                id="impact_001",
                file="impact.wav",
                tags=["impact", "heavy"],
                description="Heavy impact sound",
                intensity=9,
                category="impact",
            ),
        ]
        manifest = SfxManifest(version="1.0", items=items)

        # Build context pack
        context = build_sfx_context_pack(
            manifest, intensity_range=(5, 10), categories=["transition", "impact"]
        )

        assert "items" in context
        assert len(context["items"]) == 2
        assert context["version"] == "1.0"

        # Check context items have required fields
        for item in context["items"]:
            assert "id" in item
            assert "tags" in item
            assert "description" in item
            assert "intensity" in item


class TestAudioUtils:
    """Tests for audio utility functions"""

    def test_snap_sfx_to_beats(self):
        """Test snapping SFX events to narrative beats"""
        events = AudioEvents(
            fps=30,
            events=[
                SfxAudioEvent(sfx_id="sfx_001", frame=28, volume=0.8),  # Close to beat at 30
                SfxAudioEvent(sfx_id="sfx_002", frame=92, volume=0.8),  # Close to beat at 90
            ],
        )

        # Define beats (narrative moments)
        beats = [{"frame": 30}, {"frame": 90}, {"frame": 150}]

        # Snap events to beats
        snapped = snap_sfx_to_beats(events, beats, max_snap_frames=5)

        sfx_events = snapped.get_sfx_events()
        # Events should be snapped to nearest beats
        assert sfx_events[0].frame == 30  # Snapped from 28
        assert sfx_events[1].frame == 90  # Snapped from 92

    def test_thin_sfx_events(self):
        """Test thinning SFX events to reduce density"""
        # Create dense SFX events (too many)
        events = AudioEvents(
            fps=30,
            events=[
                SfxAudioEvent(sfx_id="sfx_001", frame=i, volume=0.8) for i in range(0, 300, 5)
            ],
        )

        # Should have 60 events (every 5 frames for 300 frames)
        assert len(events.get_sfx_events()) == 60

        # Thin to max density (e.g., max 20 events per 300 frames)
        thinned = thin_sfx_events(events, max_density=20 / 300)

        # Should reduce number of events
        assert len(thinned.get_sfx_events()) < 60

    def test_finalize_audio_events(self):
        """Test finalizing audio events for rendering"""
        events = AudioEvents(
            fps=30,
            events=[
                VoiceoverAudioEvent(src="voice.wav", frame=0, volume=1.0),
                SfxAudioEvent(sfx_id="sfx_001", frame=35, volume=0.8),
                SfxAudioEvent(sfx_id="sfx_002", frame=320, volume=0.8),  # Beyond duration
            ],
        )

        # Finalize (clamp to 300 frames = 10 seconds)
        finalized = finalize_audio_events(
            events, duration_in_frames=300, snap_to_beats=[], max_density=0.1
        )

        sfx_events = finalized.get_sfx_events()
        # Event beyond duration should be dropped
        assert len(sfx_events) == 1
        assert all(e.frame <= 300 for e in sfx_events)


class TestSfxLicense:
    """Test SFX licensing information"""

    def test_create_sfx_license(self):
        """Test creating SFX license"""
        license = SfxLicense(
            source="freesound.org",
            requires_attribution=True,
            attribution_text="Sound by Artist Name",
            url="https://freesound.org/sound/123/",
        )

        assert license.source == "freesound.org"
        assert license.requires_attribution is True
        assert "Artist Name" in license.attribution_text

    def test_sfx_item_with_license(self):
        """Test SFX item with license information"""
        license = SfxLicense(
            source="epidemic_sound", requires_attribution=False, url="https://example.com"
        )

        item = SfxItem(
            id="music_001",
            file="music.mp3",
            tags=["music", "background"],
            description="Background music",
            license=license,
        )

        assert item.license is not None
        assert item.license.source == "epidemic_sound"
        assert item.license.requires_attribution is False


@pytest.mark.asyncio
class TestAudioMixer:
    """Tests for SFX-005: FFmpeg Audio Mixer"""

    async def test_audio_mixer_import(self):
        """Test that audio mixer module can be imported"""
        from services.sfx_library.audio_mixer import (
            mix_audio_bus,
            mix_tracks,
            get_audio_duration,
        )

        # Should import without error
        assert mix_audio_bus is not None
        assert mix_tracks is not None
        assert get_audio_duration is not None

    # Note: Full audio mixer tests would require actual audio files
    # and FFmpeg to be installed. These are integration tests.


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
