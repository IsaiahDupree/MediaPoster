"""
Unit Tests for Video Analyzer (REPURPOSE-001)
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from services.repurpose.video_analyzer import (
    VideoAnalyzer,
    TranscriptWord,
    TranscriptSegment,
    Highlight
)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    mock_client = Mock()
    mock_client.audio = Mock()
    mock_client.audio.transcriptions = Mock()
    mock_client.chat = Mock()
    mock_client.chat.completions = Mock()
    return mock_client


@pytest.fixture
def analyzer(mock_openai_client):
    """Create analyzer with mocked OpenAI"""
    with patch('services.repurpose.video_analyzer.AsyncOpenAI') as mock_openai:
        mock_openai.return_value = mock_openai_client
        analyzer = VideoAnalyzer(api_key="test-key")
        analyzer.client = mock_openai_client
        return analyzer


class TestTranscriptDataStructures:
    """Test data structures"""

    def test_transcript_word(self):
        """Test TranscriptWord dataclass"""
        word = TranscriptWord(word="hello", start=0.0, end=0.5, confidence=0.95)
        assert word.word == "hello"
        assert word.start == 0.0
        assert word.end == 0.5
        assert word.confidence == 0.95

    def test_transcript_segment(self):
        """Test TranscriptSegment dataclass"""
        words = [
            TranscriptWord("hello", 0.0, 0.5),
            TranscriptWord("world", 0.6, 1.0)
        ]
        segment = TranscriptSegment(
            text="hello world",
            start=0.0,
            end=1.0,
            words=words
        )

        assert segment.text == "hello world"
        assert len(segment.words) == 2
        assert segment.sentiment_score == 0.0  # Default

        # Test to_dict
        data = segment.to_dict()
        assert data["text"] == "hello world"
        assert len(data["words"]) == 2

    def test_highlight(self):
        """Test Highlight dataclass"""
        highlight = Highlight(
            start=10.0,
            end=25.0,
            title="Key moment",
            transcript="This is a key moment",
            virality_score=85,
            hook_score=90,
            emotion_score=80,
            reason="Emotional peak",
            tags=["highlight", "emotion"]
        )

        assert highlight.start == 10.0
        assert highlight.end == 25.0
        assert highlight.virality_score == 85
        assert len(highlight.tags) == 2

        # Test to_dict
        data = highlight.to_dict()
        assert data["virality_score"] == 85
        assert "tags" in data


class TestVideoAnalyzerInit:
    """Test analyzer initialization"""

    def test_analyzer_requires_api_key(self):
        """Test that API key is required"""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ValueError, match="OpenAI API key required"):
                VideoAnalyzer()

    def test_analyzer_accepts_api_key(self):
        """Test analyzer accepts API key parameter"""
        with patch('services.repurpose.video_analyzer.AsyncOpenAI'):
            analyzer = VideoAnalyzer(api_key="test-key")
            assert analyzer.api_key == "test-key"


class TestTranscriptSegmentation:
    """Test transcript segmentation"""

    def test_segment_transcript_with_words(self, analyzer):
        """Test segmentation with word-level timing"""
        transcript_data = {
            "text": "Hello world. How are you?",
            "duration": 5.0,
            "words": [
                {"word": "Hello", "start": 0.0, "end": 0.5},
                {"word": "world.", "start": 0.6, "end": 1.0},
                {"word": "How", "start": 1.5, "end": 1.8},
                {"word": "are", "start": 1.9, "end": 2.1},
                {"word": "you?", "start": 2.2, "end": 2.5}
            ]
        }

        segments = analyzer._segment_transcript(transcript_data)

        assert len(segments) == 2  # Split on punctuation
        assert "Hello world" in segments[0].text
        assert "How are you" in segments[1].text

    def test_segment_transcript_without_words(self, analyzer):
        """Test segmentation fallback without word timing"""
        transcript_data = {
            "text": "Full transcript text",
            "duration": 60.0,
            "words": []
        }

        segments = analyzer._segment_transcript(transcript_data)

        assert len(segments) == 1
        assert segments[0].text == "Full transcript text"
        assert segments[0].start == 0
        assert segments[0].end == 60.0


class TestHighlightDetection:
    """Test highlight detection logic"""

    def test_detect_highlights_finds_peaks(self, analyzer):
        """Test that emotional peaks are detected"""
        # Create segments with varying emotion scores
        segments = [
            TranscriptSegment("Normal segment", 0, 5, emotion_intensity=0.3, energy_level=0.3),
            TranscriptSegment("Peak segment!", 5, 10, emotion_intensity=0.8, energy_level=0.9),
            TranscriptSegment("High segment", 10, 15, emotion_intensity=0.7, energy_level=0.7),
            TranscriptSegment("Normal again", 15, 20, emotion_intensity=0.4, energy_level=0.3),
        ]

        highlights = analyzer._detect_highlights(
            segments,
            min_duration=5,
            max_duration=60,
            target_count=10
        )

        assert len(highlights) > 0
        # First highlight should be the peak
        assert highlights[0].start == 5.0

    def test_remove_overlaps(self, analyzer):
        """Test overlap removal logic"""
        highlights = [
            Highlight(0, 10, "First", "text", 80, 80, 80, "peak", []),
            Highlight(5, 15, "Overlapping", "text", 90, 90, 90, "peak", []),  # Higher score, overlaps
            Highlight(20, 30, "Separate", "text", 70, 70, 70, "peak", []),
        ]

        result = analyzer._remove_overlaps(highlights)

        # Should keep the higher-scoring overlapping clip and the separate one
        assert len(result) == 2
        assert result[0].title == "Overlapping"  # Higher score
        assert result[1].title == "Separate"


class TestHelperMethods:
    """Test helper methods"""

    def test_generate_clip_title_short(self, analyzer):
        """Test title generation for short text"""
        text = "This is short"
        title = analyzer._generate_clip_title(text)
        assert title == "This is short"

    def test_generate_clip_title_long(self, analyzer):
        """Test title generation for long text"""
        text = "This is a very long piece of text that should be truncated to a reasonable length"
        title = analyzer._generate_clip_title(text, max_length=30)
        assert len(title) <= 30
        assert "..." in title


@pytest.mark.asyncio
class TestAsyncMethods:
    """Test async methods with mocks"""

    async def test_transcribe_video_success(self, analyzer, mock_openai_client, tmp_path):
        """Test successful video transcription"""
        # Create a temporary video file
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake video data")

        # Mock Whisper API response
        mock_response = Mock()
        mock_response.text = "Hello world"
        mock_response.language = "en"
        mock_response.duration = 5.0
        mock_response.words = [
            Mock(word="Hello", start=0.0, end=0.5),
            Mock(word="world", start=0.6, end=1.0)
        ]

        mock_openai_client.audio.transcriptions.create = AsyncMock(return_value=mock_response)

        result = await analyzer._transcribe_video(str(video_file))

        assert result["text"] == "Hello world"
        assert result["language"] == "en"
        assert len(result["words"]) == 2

    async def test_batch_sentiment_analysis(self, analyzer, mock_openai_client):
        """Test batch sentiment analysis"""
        texts = ["Happy text", "Sad text"]

        # Mock GPT response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '{"analyses": [{"sentiment": 0.8, "emotion": 0.7, "energy": 0.8}, {"sentiment": -0.5, "emotion": 0.6, "energy": 0.4}]}'

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await analyzer._batch_sentiment_analysis(texts)

        assert len(result) == 2
        assert result[0]["sentiment"] == 0.8
        assert result[1]["sentiment"] == -0.5

    async def test_calculate_virality_score(self, analyzer, mock_openai_client):
        """Test virality score calculation"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = '{"virality": 85, "hook": 90}'

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_response)

        result = await analyzer._calculate_virality_score(
            "Amazing content here",
            10.0,
            25.0
        )

        assert result["virality"] == 85
        assert result["hook"] == 90
        assert 0 <= result["virality"] <= 100
        assert 0 <= result["hook"] <= 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
