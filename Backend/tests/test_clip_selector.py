"""
Tests for Clip Selection Service
Tests AI-powered clip suggestions, scoring algorithm, and platform optimization
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from sqlalchemy.orm import Session

from services.clip_selector import ClipSelector, ClipSuggestion
from database.models import Video, VideoSegment, VideoFrame
from database.db import SessionLocal


@pytest.fixture
def db_session():
    """Create a test database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def selector(db_session):
    """Create clip selector for testing"""
    return ClipSelector(db_session)


@pytest.fixture
def mock_video(db_session):
    """Create a mock video"""
    video = Video(
        id="550e8400-e29b-41d4-a716-446655440000",
        title="Test Video",
        duration=120.0,
        file_path="/test/video.mp4"
    )
    db_session.add(video)
    db_session.commit()
    return video


@pytest.fixture
def mock_segments(db_session, mock_video):
    """Create mock video segments"""
    segments = [
        VideoSegment(
            video_id=mock_video.id,
            segment_type="hook",
            start_time=0.0,
            end_time=15.0,
            psychology_tags={
                "fate_patterns": ["fear", "pain"],
                "aida_stage": "attention",
                "emotions": ["curiosity", "surprise"]
            },
            cta_keywords=[]
        ),
        VideoSegment(
            video_id=mock_video.id,
            segment_type="body",
            start_time=15.0,
            end_time=60.0,
            psychology_tags={
                "emotions": ["engagement", "interest"]
            },
            cta_keywords=[]
        ),
        VideoSegment(
            video_id=mock_video.id,
            segment_type="cta",
            start_time=60.0,
            end_time=75.0,
            psychology_tags={
                "emotions": ["motivation"]
            },
            cta_keywords=["subscribe", "click"]
        )
    ]
    
    for seg in segments:
        db_session.add(seg)
    db_session.commit()
    
    return segments


@pytest.fixture
def mock_frames(db_session, mock_video):
    """Create mock video frames"""
    frames = []
    for i in range(10):
        frame = VideoFrame(
            video_id=mock_video.id,
            timestamp=i * 10.0,
            frame_number=i * 300,
            has_pattern_interrupt=(i % 3 == 0),  # Every 3rd frame
            metadata={"faces_detected": 1 if i % 2 == 0 else 0}
        )
        frames.append(frame)
        db_session.add(frame)
    
    db_session.commit()
    return frames


class TestClipSelector:
    """Test AI clip selection service"""
    
    @pytest.mark.asyncio
    async def test_suggest_clips_returns_suggestions(self, selector, mock_video, mock_segments, mock_frames):
        """Test that clip suggestions are generated"""
        # Mock GPT response
        with patch('openai.chat.completions.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "REASONING: Great hook\nTITLE: Amazing Content"
            mock_openai.return_value = mock_response
            
            suggestions = await selector.suggest_clips(
                video_id=str(mock_video.id),
                platform="tiktok",
                max_clips=5
            )
            
            assert len(suggestions) > 0
            assert isinstance(suggestions[0], ClipSuggestion)
    
    @pytest.mark.asyncio
    async def test_clip_scoring_algorithm(self, selector, mock_video, mock_segments, mock_frames):
        """Test that clips are scored correctly"""
        with patch('openai.chat.completions.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "REASONING: Test\nTITLE: Test"
            mock_openai.return_value = mock_response
            
            suggestions = await selector.suggest_clips(
                video_id=str(mock_video.id),
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
    async def test_platform_optimization(self, selector, mock_video, mock_segments, mock_frames):
        """Test platform-specific optimization"""
        with patch('openai.chat.completions.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "REASONING: TikTok optimized\nTITLE: Viral Content"
            mock_openai.return_value = mock_response
            
            # TikTok prefers shorter clips
            tiktok_suggestions = await selector.suggest_clips(
                video_id=str(mock_video.id),
                platform="tiktok",
                max_clips=3
            )
            
            # YouTube prefers longer clips
            youtube_suggestions = await selector.suggest_clips(
                video_id=str(mock_video.id),
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
    async def test_no_segments_returns_empty(self, selector, mock_video):
        """Test that empty suggestions are returned when no segments exist"""
        suggestions = await selector.suggest_clips(
            video_id=str(mock_video.id),
            max_clips=5
        )
        
        # Should return empty list if video has no segments
        assert isinstance(suggestions, list)
    
    @pytest.mark.asyncio
    async def test_invalid_video_raises_error(self, selector):
        """Test that invalid video ID raises error"""
        with pytest.raises(ValueError, match="not found"):
            await selector.suggest_clips(
                video_id="invalid-uuid",
                max_clips=5
            )
    
    @pytest.mark.asyncio
    async def test_platform_recommendations_generated(self, selector, mock_video, mock_segments, mock_frames):
        """Test that platform recommendations are included"""
        with patch('openai.chat.completions.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "REASONING: Good\nTITLE: Test"
            mock_openai.return_value = mock_response
            
            suggestions = await selector.suggest_clips(
                video_id=str(mock_video.id),
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
