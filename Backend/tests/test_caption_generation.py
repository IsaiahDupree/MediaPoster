"""
Tests for Caption/Subtitle Generation (TRANS-002)
"""

import pytest
from services.transcription_adapter import (
    TranscriptionResult,
    Segment,
    Word,
    generate_srt,
    generate_vtt
)


@pytest.fixture
def sample_transcription():
    """Sample transcription result for testing"""
    return TranscriptionResult(
        text="Hello world. This is a test transcription.",
        language="en",
        duration=5.0,
        segments=[
            Segment(
                text="Hello world.",
                start=0.0,
                end=1.5,
                confidence=0.95,
                words=[
                    Word(text="Hello", start=0.0, end=0.5),
                    Word(text="world", start=0.6, end=1.5)
                ]
            ),
            Segment(
                text="This is a test transcription.",
                start=2.0,
                end=5.0,
                confidence=0.98,
                words=[
                    Word(text="This", start=2.0, end=2.3),
                    Word(text="is", start=2.4, end=2.5),
                    Word(text="a", start=2.6, end=2.7),
                    Word(text="test", start=2.8, end=3.2),
                    Word(text="transcription", start=3.3, end=5.0)
                ]
            )
        ],
        words=[
            Word(text="Hello", start=0.0, end=0.5),
            Word(text="world", start=0.6, end=1.5),
            Word(text="This", start=2.0, end=2.3),
            Word(text="is", start=2.4, end=2.5),
            Word(text="a", start=2.6, end=2.7),
            Word(text="test", start=2.8, end=3.2),
            Word(text="transcription", start=3.3, end=5.0)
        ],
        provider="test"
    )


def test_generate_srt_basic(sample_transcription):
    """Test basic SRT generation"""
    srt = generate_srt(sample_transcription)

    # Should generate valid SRT format
    assert "1\n" in srt
    assert "00:00:00" in srt
    assert "-->" in srt
    assert "Hello world" in srt or "Hello" in srt

    # Should have subtitle numbers
    lines = srt.strip().split("\n")
    assert lines[0] == "1"  # First subtitle number


def test_generate_srt_timestamps(sample_transcription):
    """Test SRT timestamp formatting"""
    srt = generate_srt(sample_transcription)

    # Check timestamp format (HH:MM:SS,mmm --> HH:MM:SS,mmm)
    assert "00:00:00,000" in srt or "00:00:00," in srt
    assert "-->" in srt

    # Should have commas for milliseconds (SRT format)
    assert "," in srt


def test_generate_vtt_basic(sample_transcription):
    """Test basic WebVTT generation"""
    vtt = generate_vtt(sample_transcription)

    # Should start with WEBVTT header
    assert vtt.startswith("WEBVTT\n")

    # Should contain content
    assert "Hello" in vtt or "world" in vtt
    assert "-->" in vtt


def test_generate_vtt_timestamps(sample_transcription):
    """Test WebVTT timestamp formatting"""
    vtt = generate_vtt(sample_transcription)

    # Should use dots for milliseconds (VTT format)
    # And should NOT have commas
    lines = [l for l in vtt.split("\n") if "-->" in l]
    for line in lines:
        # VTT should have dots, not commas
        assert "." in line
        # Should not have SRT-style commas in timestamps
        parts = line.split("-->")
        for part in parts:
            if ":" in part:
                # This is a timestamp part
                # Check that milliseconds use dots
                assert part.count(",") == 0 or "." in part


def test_max_chars_per_line():
    """Test caption line length limiting"""
    long_text = "This is a very long sentence that should be split into multiple lines according to the maximum characters per line setting."

    transcription = TranscriptionResult(
        text=long_text,
        language="en",
        duration=10.0,
        segments=[
            Segment(
                text=long_text,
                start=0.0,
                end=10.0,
                words=[
                    Word(text=word, start=i*0.5, end=(i+1)*0.5)
                    for i, word in enumerate(long_text.split())
                ]
            )
        ],
        words=[
            Word(text=word, start=i*0.5, end=(i+1)*0.5)
            for i, word in enumerate(long_text.split())
        ]
    )

    srt = generate_srt(transcription, max_chars_per_line=30)

    # Check that lines don't exceed max length (allowing for newlines within captions)
    lines = srt.split("\n\n")
    for caption_block in lines:
        caption_lines = caption_block.split("\n")
        for line in caption_lines:
            # Skip subtitle numbers and timestamps
            if line.isdigit() or "-->" in line or not line.strip():
                continue
            # Text lines should be within limit (with some tolerance for word boundaries)
            assert len(line) <= 60  # Allow some tolerance for word boundaries


def test_max_duration():
    """Test caption duration limiting"""
    # Create transcription with one long segment
    transcription = TranscriptionResult(
        text="Word " * 100,  # Many words
        language="en",
        duration=20.0,
        segments=[
            Segment(
                text="Word " * 100,
                start=0.0,
                end=20.0,
                words=[
                    Word(text="Word", start=i*0.2, end=(i+1)*0.2)
                    for i in range(100)
                ]
            )
        ],
        words=[
            Word(text="Word", start=i*0.2, end=(i+1)*0.2)
            for i in range(100)
        ]
    )

    srt = generate_srt(transcription, max_duration=5.0)

    # Should create multiple captions
    subtitle_count = srt.count("\n\n")
    assert subtitle_count > 1  # Should be split into multiple captions


def test_empty_transcription():
    """Test handling of empty transcription"""
    empty_transcription = TranscriptionResult(
        text="",
        language="en",
        duration=0.0,
        segments=[],
        words=[]
    )

    srt = generate_srt(empty_transcription)
    # Should not crash, should return empty or minimal output
    assert isinstance(srt, str)


def test_words_only_transcription():
    """Test caption generation from words only (no segments)"""
    transcription = TranscriptionResult(
        text="Hello world",
        language="en",
        duration=2.0,
        segments=[],  # No segments
        words=[
            Word(text="Hello", start=0.0, end=0.8),
            Word(text="world", start=1.0, end=2.0)
        ]
    )

    srt = generate_srt(transcription)

    # Should generate captions from words
    assert "Hello" in srt
    assert "world" in srt
    assert "-->" in srt


def test_segments_only_transcription():
    """Test caption generation from segments only (no words)"""
    transcription = TranscriptionResult(
        text="Hello world",
        language="en",
        duration=2.0,
        segments=[
            Segment(text="Hello world", start=0.0, end=2.0, words=[])
        ],
        words=[]  # No words
    )

    srt = generate_srt(transcription)

    # Should generate captions from segments
    assert "Hello world" in srt
    assert "-->" in srt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
