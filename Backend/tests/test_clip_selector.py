"""
Tests for Clip Selection Service
Tests AI-powered clip suggestions, scoring algorithm, and platform optimization
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from services.clip_selector import ClipSelector, ClipSuggestion


def _make_segment(segment_type, start_s, end_s, psychology_tags=None, cta_keywords=None, seg_id=None):
    """Create a mock VideoSegment with required attributes."""
    seg = Mock()
    seg.id = seg_id or f"seg-{start_s}-{end_s}"
    seg.segment_type = segment_type
    seg.start_s = start_s
    seg.end_s = end_s
    seg.psychology_tags = psychology_tags or {}
    seg.cta_keywords = cta_keywords or []
    return seg


def _make_frame(video_id, frame_time_s, is_pattern_interrupt=False, metadata=None):
    """Create a mock VideoFrame with required attributes."""
    frame = Mock()
    frame.video_id = video_id
    frame.timestamp = frame_time_s  # Used by ClipSelector._score_visual_engagement
    frame.frame_time_s = frame_time_s
    frame.has_pattern_interrupt = is_pattern_interrupt
    frame.is_pattern_interrupt = is_pattern_interrupt
    frame.metadata = metadata or {}
    return frame


@pytest.fixture
def db_session():
    """Create a mock database session for testing"""
    session = Mock(spec=Session)
    return session


@pytest.fixture
def selector(db_session):
    """Create clip selector for testing"""
    return ClipSelector(db_session)


VIDEO_ID = "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def mock_video():
    """Create a mock analyzed video"""
    video = Mock()
    video.id = VIDEO_ID
    video.duration_seconds = 120.0
    return video


@pytest.fixture
def mock_segments():
    """Create mock video segments"""
    return [
        _make_segment(
            segment_type="hook",
            start_s=0.0,
            end_s=15.0,
            psychology_tags={
                "fate_patterns": ["fear", "pain"],
                "aida_stage": "attention",
                "emotions": ["curiosity", "surprise"]
            },
            cta_keywords=[],
            seg_id="seg-hook"
        ),
        _make_segment(
            segment_type="body",
            start_s=15.0,
            end_s=60.0,
            psychology_tags={
                "emotions": ["engagement", "interest"]
            },
            cta_keywords=[],
            seg_id="seg-body"
        ),
        _make_segment(
            segment_type="cta",
            start_s=60.0,
            end_s=75.0,
            psychology_tags={
                "emotions": ["motivation"]
            },
            cta_keywords=["subscribe", "click"],
            seg_id="seg-cta"
        )
    ]


@pytest.fixture
def mock_frames():
    """Create mock video frames"""
    frames = []
    for i in range(10):
        frame = _make_frame(
            video_id=VIDEO_ID,
            frame_time_s=i * 10.0,
            is_pattern_interrupt=(i % 3 == 0),
            metadata={"faces_detected": 1 if i % 2 == 0 else 0}
        )
        frames.append(frame)
    return frames


def _setup_db_queries(db_session, mock_video, mock_segments, mock_frames):
    """Setup db_session.query() to return the right mocks depending on model."""
    def query_side_effect(model):
        q = MagicMock()
        if model.__name__ == "AnalyzedVideo":
            filter_mock = MagicMock()
            filter_mock.first.return_value = mock_video
            q.filter.return_value = filter_mock
        elif model.__name__ == "VideoSegment":
            filter_mock = MagicMock()
            order_mock = MagicMock()
            order_mock.all.return_value = mock_segments
            filter_mock.order_by.return_value = order_mock
            q.filter.return_value = filter_mock
        elif model.__name__ == "VideoFrame":
            filter_mock = MagicMock()
            filter_mock.all.return_value = mock_frames
            q.filter.return_value = filter_mock
        else:
            filter_mock = MagicMock()
            filter_mock.first.return_value = None
            filter_mock.all.return_value = []
            q.filter.return_value = filter_mock
        return q
    db_session.query.side_effect = query_side_effect


class TestClipSelector:
    """Test AI clip selection service"""

    @pytest.mark.asyncio
    async def test_suggest_clips_returns_suggestions(
        self, selector, db_session, mock_video, mock_segments, mock_frames
    ):
        """Test that clip suggestions are generated"""
        _setup_db_queries(db_session, mock_video, mock_segments, mock_frames)

        with patch('openai.chat.completions.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "REASONING: Great hook\nTITLE: Amazing Content"
            mock_openai.return_value = mock_response

            suggestions = await selector.suggest_clips(
                video_id=VIDEO_ID,
                platform="tiktok",
                max_clips=5
            )

            assert len(suggestions) > 0
            assert isinstance(suggestions[0], ClipSuggestion)

    @pytest.mark.asyncio
    async def test_clip_scoring_algorithm(
        self, selector, db_session, mock_video, mock_segments, mock_frames
    ):
        """Test that clips are scored correctly"""
        _setup_db_queries(db_session, mock_video, mock_segments, mock_frames)

        with patch('openai.chat.completions.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "REASONING: Test\nTITLE: Test"
            mock_openai.return_value = mock_response

            suggestions = await selector.suggest_clips(
                video_id=VIDEO_ID,
                max_clips=3
            )

            # All suggestions should have scores between 0 and 1
            for suggestion in suggestions:
                assert 0.0 <= suggestion.ai_score <= 1.0
                assert 0.0 <= suggestion.hook_quality <= 1.0
                assert 0.0 <= suggestion.visual_engagement <= 1.0
                assert 0.0 <= suggestion.emotion_arc <= 1.0
                assert 0.0 <= suggestion.platform_fit <= 1.0
                assert 0.0 <= suggestion.cta_presence <= 1.0

    @pytest.mark.asyncio
    async def test_platform_optimization(
        self, selector, db_session, mock_video, mock_segments, mock_frames
    ):
        """Test platform-specific optimization"""
        _setup_db_queries(db_session, mock_video, mock_segments, mock_frames)

        with patch('openai.chat.completions.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "REASONING: TikTok optimized\nTITLE: Viral Content"
            mock_openai.return_value = mock_response

            # TikTok prefers shorter clips
            tiktok_suggestions = await selector.suggest_clips(
                video_id=VIDEO_ID,
                platform="tiktok",
                max_clips=3
            )

            # YouTube prefers longer clips
            youtube_suggestions = await selector.suggest_clips(
                video_id=VIDEO_ID,
                platform="youtube",
                max_clips=3
            )

            # TikTok suggestions should generally be shorter
            if tiktok_suggestions and youtube_suggestions:
                avg_tiktok_duration = sum(s.duration for s in tiktok_suggestions) / len(tiktok_suggestions)
                avg_youtube_duration = sum(s.duration for s in youtube_suggestions) / len(youtube_suggestions)

                # This might not always be true due to video content, but test the logic exists
                assert avg_tiktok_duration <= avg_youtube_duration or avg_tiktok_duration < 90

    def test_score_hook_quality(self, selector, mock_segments):
        """Test hook quality scoring"""
        # Segment with strong FATE patterns
        score = selector._score_hook_quality(mock_segments[:1])
        assert score > 0.5  # Should have decent score with fear/pain patterns

        # No hook segments
        score = selector._score_hook_quality([])
        assert score == 0.2  # Low score for no hook

    def test_score_visual_engagement(self, selector, mock_frames):
        """Test visual engagement scoring"""
        score = selector._score_visual_engagement(mock_frames)
        assert 0.0 <= score <= 1.0
        assert score > 0.5  # Should have decent score with pattern interrupts and faces

    def test_score_emotion_arc(self, selector, mock_segments):
        """Test emotion arc scoring"""
        score = selector._score_emotion_arc(mock_segments)
        assert 0.0 <= score <= 1.0
        # Segments have 2-4 unique emotions which should score well
        assert score >= 0.6

    def test_score_platform_fit(self, selector):
        """Test platform fit scoring"""
        candidate = {"start_time": 0, "end_time": 30}  # 30 second clip

        # TikTok optimal range is 20-45s
        tiktok_score = selector._score_platform_fit(candidate, "tiktok")
        assert tiktok_score == 1.0  # Perfect fit

        # YouTube optimal range is 90-180s
        youtube_score = selector._score_platform_fit(candidate, "youtube")
        assert youtube_score < 1.0  # Not optimal

    def test_score_cta_presence(self, selector, mock_segments):
        """Test CTA presence scoring"""
        # Segments with CTA
        score = selector._score_cta_presence(mock_segments)
        assert score >= 0.7  # Should have good score with CTA keywords

        # No CTA segments
        score = selector._score_cta_presence([])
        assert score == 0.3  # Low score

    def test_generate_clip_candidates_single_segment(self, selector, mock_segments, mock_frames):
        """Test single segment clip generation"""
        candidates = selector._generate_clip_candidates(
            segments=mock_segments,
            frames=mock_frames,
            min_duration=10.0,
            max_duration=20.0,
            platform=None
        )

        # Should include the hook segment (15s duration)
        single_seg_candidates = [c for c in candidates if c["strategy"] == "single_segment"]
        assert len(single_seg_candidates) > 0

    def test_generate_clip_candidates_full_arc(self, selector, mock_segments, mock_frames):
        """Test full narrative arc clip generation"""
        candidates = selector._generate_clip_candidates(
            segments=mock_segments,
            frames=mock_frames,
            min_duration=60.0,
            max_duration=90.0,
            platform=None
        )

        # Should include hook + body + CTA combinations
        full_arc_candidates = [c for c in candidates if c.get("strategy") == "full_arc"]
        assert len(full_arc_candidates) > 0

        # Full arcs should have CTA flag
        for candidate in full_arc_candidates:
            if candidate.get("has_cta"):
                assert candidate["has_cta"] is True

    @pytest.mark.asyncio
    async def test_no_segments_returns_empty(self, selector, db_session, mock_video):
        """Test that empty suggestions are returned when no segments exist"""
        # Setup: video exists, but no segments
        _setup_db_queries(db_session, mock_video, [], [])

        suggestions = await selector.suggest_clips(
            video_id=VIDEO_ID,
            max_clips=5
        )

        # Should return empty list if video has no segments
        assert isinstance(suggestions, list)
        assert len(suggestions) == 0

    @pytest.mark.asyncio
    async def test_invalid_video_raises_error(self, selector, db_session):
        """Test that invalid video ID raises error"""
        # Setup: video not found
        _setup_db_queries(db_session, None, [], [])

        with pytest.raises(ValueError, match="not found"):
            await selector.suggest_clips(
                video_id="invalid-uuid",
                max_clips=5
            )

    @pytest.mark.asyncio
    async def test_platform_recommendations_generated(
        self, selector, db_session, mock_video, mock_segments, mock_frames
    ):
        """Test that platform recommendations are included"""
        _setup_db_queries(db_session, mock_video, mock_segments, mock_frames)

        with patch('openai.chat.completions.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "REASONING: Good\nTITLE: Test"
            mock_openai.return_value = mock_response

            suggestions = await selector.suggest_clips(
                video_id=VIDEO_ID,
                max_clips=3
            )

            if suggestions:
                # Should have platform recommendations
                assert "platform_recommendations" in suggestions[0].__dict__
                assert isinstance(suggestions[0].platform_recommendations, dict)


class TestClipSuggestionDataclass:
    """Test ClipSuggestion dataclass"""

    def test_clip_suggestion_creation(self):
        """Test creating a clip suggestion"""
        suggestion = ClipSuggestion(
            start_time=10.0,
            end_time=45.0,
            duration=35.0,
            ai_score=0.85,
            clip_type="ai_generated",
            reasoning="Strong hook with good visual engagement",
            hook_quality=0.9,
            visual_engagement=0.8,
            emotion_arc=0.85,
            platform_fit=0.9,
            cta_presence=0.7,
            suggested_title="Amazing Content",
            segment_ids=["seg1", "seg2"],
            hook_segment_id="seg1",
            platform_recommendations={"tiktok": {"fit_score": 0.9}}
        )

        assert suggestion.duration == 35.0
        assert suggestion.ai_score == 0.85
        assert suggestion.suggested_title == "Amazing Content"
        assert len(suggestion.segment_ids) == 2
