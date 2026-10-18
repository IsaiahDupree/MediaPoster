"""
Tests for Content Intelligence Phase 3: Psychology & Tagging
Tests transcription, psychology tagging, and content analysis orchestration
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, AnalyzedVideo, VideoSegment, VideoWord
from services.transcription import TranscriptionService
from services.psychology_tagger import PsychologyTagger
from services.content_analysis_orchestrator import ContentAnalysisOrchestrator


@pytest.fixture
def db_session():
    """Create test database session"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestTranscriptionService:
    """Test transcription service"""
    
    def test_initialization_without_api_key(self):
        """Test initialization without API key"""
        service = TranscriptionService(api_key=None)
        
        assert service.is_enabled() is False
    
    def test_initialization_with_api_key(self):
        """Test initialization with API key"""
        service = TranscriptionService(api_key="fake-key")
        
        assert service.client is not None
    
    @patch('openai.OpenAI')
    def test_transcribe_video(self, mock_openai_class):
        """Test video transcription with word timestamps"""
        # Mock OpenAI response
        mock_client = Mock()
        mock_transcript = Mock()
        mock_transcript.text = "Hello world this is a test"
        mock_transcript.language = "en"
        mock_transcript.duration = 5.0
        mock_transcript.words = [
            Mock(word="Hello", start=0.0, end=0.5),
            Mock(word="world", start=0.5, end=1.0),
            Mock(word="this", start=1.0, end=1.3),
            Mock(word="is", start=1.3, end=1.5),
            Mock(word="a", start=1.5, end=1.6),
            Mock(word="test", start=1.6, end=2.0)
        ]
        mock_transcript.segments = []
        
        mock_client.audio.transcriptions.create.return_value = mock_transcript
        mock_openai_class.return_value = mock_client
        
        service = TranscriptionService(api_key="fake-key")
        service.client = mock_client
        
        # Create a fake video file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"fake video data")
            video_path = f.name
        
        try:
            result = service.transcribe_video(video_path)
            
            assert result["text"] == "Hello world this is a test"
            assert result["language"] == "en"
            assert result["duration"] == 5.0
            assert len(result["words"]) == 6
            assert result["words"][0]["word"] == "Hello"
            assert result["words"][0]["start"] == 0.0
        finally:
            import os
            os.unlink(video_path)
    
    def test_get_transcript_statistics(self):
        """Test transcript statistics calculation"""
        service = TranscriptionService(api_key="fake-key")
        
        transcript_data = {
            "text": "This is a test transcript for statistics",
            "words": [
                {"word": "This", "start": 0.0, "end": 0.3},
                {"word": "is", "start": 0.3, "end": 0.5},
                {"word": "a", "start": 0.5, "end": 0.6},
                {"word": "test", "start": 1.2, "end": 1.5},  # Long pause before this
                {"word": "transcript", "start": 1.5, "end": 2.0},
                {"word": "for", "start": 2.0, "end": 2.2},
                {"word": "statistics", "start": 2.2, "end": 2.8}
            ]
        }
        
        stats = service.get_transcript_statistics(transcript_data)
        
        assert stats["total_words"] == 7
        assert stats["total_duration_s"] == 2.8
        assert stats["words_per_minute"] > 0
        assert stats["total_pauses"] > 0  # Should detect the 0.6s pause


class TestPsychologyTagger:
    """Test psychology tagging service"""
    
    def test_initialization_without_api_key(self):
        """Test initialization without API key"""
        tagger = PsychologyTagger(api_key=None)
        
        assert tagger.is_enabled() is False
    
    @patch('openai.OpenAI')
    def test_classify_segments(self, mock_openai_class):
        """Test segment classification"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='''[
            {
                "segment_type": "hook",
                "start_pct": 0.0,
                "end_pct": 0.1,
                "summary": "Pain-point introduction",
                "key_phrases": ["struggling with", "tired of"]
            },
            {
                "segment_type": "body",
                "start_pct": 0.1,
                "end_pct": 0.8,
                "summary": "Value delivery",
                "key_phrases": ["here's how", "simple steps"]
            },
            {
                "segment_type": "cta",
                "start_pct": 0.8,
                "end_pct": 1.0,
                "summary": "Call to action",
                "key_phrases": ["comment below", "link in bio"]
            }
        ]'''))]
        mock_client.chat.completions.create.return_value = mock_response
        
        tagger = PsychologyTagger(api_key="fake-key")
        tagger.client = mock_client
        
        result = tagger.classify_segments(
            "Struggling with social media? Here's how to automate it. Comment below!",
            duration_s=60.0
        )
        
        assert "segments" in result
        assert len(result["segments"]) == 3
        assert result["segments"][0]["segment_type"] == "hook"
        assert result["segments"][0]["start_s"] == 0.0
        assert result["segments"][2]["segment_type"] == "cta"
    
    @patch('openai.OpenAI')
    def test_tag_fate_framework(self, mock_openai_class):
        """Test FATE framework tagging"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='''{
            "focus": "solo entrepreneurs struggling with content automation",
            "authority_signal": "15 years experience",
            "tribe_marker": "we're the people who build systems",
            "emotion": "relief"
        }'''))]
        mock_client.chat.completions.create.return_value = mock_response
        
        tagger = PsychologyTagger(api_key="fake-key")
        tagger.client = mock_client
        
        result = tagger.tag_fate_framework(
            "I've spent 15 years building automation systems. If you're a solo entrepreneur...",
            segment_type="hook"
        )
        
        assert result["focus"] == "solo entrepreneurs struggling with content automation"
        assert result["authority_signal"] == "15 years experience"
        assert result["emotion"] == "relief"
    
    @patch('openai.OpenAI')
    def test_classify_hook_type(self, mock_openai_class):
        """Test hook type classification"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='''{
            "hook_type": "pain",
            "hook_score": 0.85,
            "reasoning": "Directly addresses a pain point",
            "improvements": ["Make it more specific", "Add urgency"]
        }'''))]
        mock_client.chat.completions.create.return_value = mock_response
        
        tagger = PsychologyTagger(api_key="fake-key")
        tagger.client = mock_client
        
        result = tagger.classify_hook_type("If you're tired of posting daily...")
        
        assert result["hook_type"] == "pain"
        assert result["hook_score"] == 0.85
        assert len(result["improvements"]) == 2
    
    @patch('openai.OpenAI')
    def test_extract_cta_keywords(self, mock_openai_class):
        """Test CTA keyword extraction"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='''{
            "has_cta": true,
            "cta_type": "engagement",
            "cta_keywords": ["Tech", "PROMPT"],
            "cta_text": "Comment Tech to get the automation blueprint",
            "cta_clarity_score": 0.9,
            "suggestions": ["Add visual text overlay"]
        }'''))]
        mock_client.chat.completions.create.return_value = mock_response
        
        tagger = PsychologyTagger(api_key="fake-key")
        tagger.client = mock_client
        
        result = tagger.extract_cta_keywords("Comment Tech to get the automation blueprint")
        
        assert result["has_cta"] is True
        assert result["cta_type"] == "engagement"
        assert "Tech" in result["cta_keywords"]
        assert result["cta_clarity_score"] == 0.9
    
    @patch('openai.OpenAI')
    def test_analyze_sentiment_emotion(self, mock_openai_class):
        """Test sentiment and emotion analysis"""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='''{
            "sentiment_score": 0.7,
            "primary_emotion": "excitement",
            "emotion_intensity": 0.8,
            "tone": "hype_coach"
        }'''))]
        mock_client.chat.completions.create.return_value = mock_response
        
        tagger = PsychologyTagger(api_key="fake-key")
        tagger.client = mock_client
        
        result = tagger.analyze_sentiment_emotion("This is amazing! You're going to love this!")
        
        assert result["sentiment_score"] == 0.7
        assert result["primary_emotion"] == "excitement"
        assert result["tone"] == "hype_coach"


class TestContentAnalysisOrchestrator:
    """Test content analysis orchestrator"""
    
    def test_initialization(self, db_session):
        """Test orchestrator initialization"""
        orchestrator = ContentAnalysisOrchestrator(
            db=db_session,
            openai_api_key="fake-key"
        )
        
        assert orchestrator.transcription is not None
        assert orchestrator.psychology is not None
        assert orchestrator.video_analysis is not None
    
    def test_is_ready(self, db_session):
        """Test readiness check"""
        with patch.object(TranscriptionService, 'is_enabled', return_value=True), \
             patch.object(PsychologyTagger, 'is_enabled', return_value=True), \
             patch('services.frame_sampler.FrameSamplerService.check_ffmpeg_installed', return_value=True):
            
            orchestrator = ContentAnalysisOrchestrator(
                db=db_session,
                openai_api_key="fake-key"
            )
            
            readiness = orchestrator.is_ready()
            
            assert readiness["transcription_enabled"] is True
            assert readiness["psychology_enabled"] is True
            assert readiness["ffmpeg_installed"] is True
    
    @patch.object(TranscriptionService, 'transcribe_video')
    @patch.object(TranscriptionService, 'get_transcript_statistics')
    @patch.object(PsychologyTagger, 'comprehensive_analysis')
    @patch('services.frame_sampler.FrameSamplerService.check_ffmpeg_installed', return_value=False)
    def test_analyze_video_complete_without_visual(
        self, mock_ffmpeg, mock_psych, mock_stats, mock_transcribe, db_session
    ):
        """Test complete analysis without visual (transcription + psychology only)"""
        # Mock transcription
        mock_transcribe.return_value = {
            "text": "Full transcript here",
            "duration": 60.0,
            "words": [
                {"word": "Full", "start": 0.0, "end": 0.5}
            ]
        }
        
        mock_stats.return_value = {
            "total_words": 1,
            "words_per_minute": 60.0
        }
        
        # Mock psychology analysis
        mock_psych.return_value = {
            "segments": {
                "segments": [
                    {
                        "segment_type": "hook",
                        "start_s": 0.0,
                        "end_s": 5.0,
                        "fate_tags": {
                            "focus": "test focus",
                            "emotion": "curiosity"
                        }
                    }
                ]
            },
            "hook_analysis": {"hook_type": "pain"},
            "cta_analysis": {"has_cta": True}
        }
        
        orchestrator = ContentAnalysisOrchestrator(
            db=db_session,
            openai_api_key="fake-key"
        )
        
        result = orchestrator.analyze_video_complete(
            video_path="/fake/video.mp4",
            store_in_db=True
        )
        
        assert result["success"] is True
        assert "transcription" in result
        assert "psychology" in result
        assert result["transcription"]["text"] == "Full transcript here"
    
    def test_store_segments(self, db_session):
        """Test storing segments in database"""
        video = AnalyzedVideo(duration_seconds=60.0)
        db_session.add(video)
        db_session.commit()
        
        segments = [
            {
                "segment_type": "hook",
                "start_s": 0.0,
                "end_s": 5.0,
                "hook_type": "pain",
                "fate_tags": {
                    "focus": "automation struggles",
                    "emotion": "frustration"
                }
            },
            {
                "segment_type": "body",
                "start_s": 5.0,
                "end_s": 55.0,
                "fate_tags": {
                    "authority_signal": "15 years experience"
                }
            }
        ]
        
        orchestrator = ContentAnalysisOrchestrator(db=db_session)
        count = orchestrator._store_segments(video.id, segments)
        
        assert count == 2
        
        # Verify stored segments
        stored = db_session.query(VideoSegment).filter_by(video_id=video.id).all()
        assert len(stored) == 2
        assert stored[0].segment_type == "hook"
        assert stored[0].hook_type == "pain"
        assert stored[0].emotion == "frustration"
    
    def test_store_words(self, db_session):
        """Test storing words in database"""
        video = AnalyzedVideo(duration_seconds=10.0)
        db_session.add(video)
        db_session.commit()
        
        words = [
            {"word": "Hello", "start": 0.0, "end": 0.5},
            {"word": "world", "start": 0.5, "end": 1.0},
            {"word": "test", "start": 1.0, "end": 1.5}
        ]
        
        orchestrator = ContentAnalysisOrchestrator(db=db_session)
        count = orchestrator._store_words(video.id, words)
        
        assert count == 3
        
        # Verify stored words
        stored = db_session.query(VideoWord).filter_by(video_id=video.id).all()
        assert len(stored) == 3
        assert stored[0].word == "Hello"
        assert stored[0].word_index == 0
        assert stored[2].word == "test"
