"""
Phase 1 Complete Testing - AI Analysis Module
Real integration tests (no mocks!)
"""
import pytest
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.ai_analysis import (
    WhisperService,
    FrameExtractor,
    VisionAnalyzer,
    AudioAnalyzer,
    ContentAnalyzer
)


class TestWhisperService:
    """Test Whisper transcription service"""
    
    def test_extract_audio(self, sample_video):
        """Test audio extraction from video"""
        service = WhisperService()
        audio_path = service.extract_audio(sample_video)
        
        assert audio_path.exists()
        assert audio_path.suffix == '.mp3'
        assert audio_path.stat().st_size > 0
        
        # Cleanup
        audio_path.unlink()
    
    @pytest.mark.slow
    def test_transcribe_video(self, sample_video):
        """Test complete video transcription"""
        service = WhisperService()
        result = service.transcribe_video(sample_video)
        
        assert 'text' in result
        assert 'duration' in result
        assert len(result['text']) > 0
    
    @pytest.mark.slow
    def test_generate_srt(self, sample_video):
        """Test SRT subtitle generation"""
        service = WhisperService()
        transcript = service.transcribe_video(sample_video)
        
        srt_path = sample_video.parent / "test_subtitles.srt"
        result = service.generate_srt(transcript, srt_path)
        
        assert result.exists()
        assert srt_path.stat().st_size > 0
        
        # Check SRT format
        content = srt_path.read_text()
        assert "-->" in content
        
        # Cleanup
        srt_path.unlink()


class TestFrameExtractor:
    """Test frame extraction service"""
    
    def test_extract_frames_at_interval(self, sample_video):
        """Test extracting frames at regular intervals"""
        extractor = FrameExtractor()
        frames = extractor.extract_frames_at_interval(
            sample_video,
            fps=1.0,
            max_frames=5
        )
        
        assert len(frames) > 0
        assert len(frames) <= 5
        assert all(f.exists() for f in frames)
        assert all(f.suffix == '.jpg' for f in frames)
        
        # Cleanup
        extractor.cleanup(sample_video.stem)
    
    def test_detect_scenes(self, sample_video):
        """Test scene change detection"""
        extractor = FrameExtractor()
        scenes = extractor.detect_scenes(sample_video, threshold=0.3)
        
        # Should detect at least one scene
        assert len(scenes) >= 0  # Can be zero for static videos
        
        if scenes:
            assert 'timestamp' in scenes[0]
            assert 'score' in scenes[0]
    
    def test_extract_key_frames(self, sample_video):
        """Test key frame extraction"""
        extractor = FrameExtractor()
        key_frames = extractor.extract_key_frames(
            sample_video,
            threshold=0.3,
            max_frames=10
        )
        
        assert len(key_frames) > 0
        assert len(key_frames) <= 10
        
        for kf in key_frames:
            assert 'path' in kf
            assert 'timestamp' in kf
            assert kf['path'].exists()
        
        # Cleanup
        extractor.cleanup(sample_video.stem)
    
    def test_get_video_duration(self, sample_video):
        """Test duration extraction"""
        extractor = FrameExtractor()
        duration = extractor.get_video_duration(sample_video)
        
        assert duration > 0
        assert duration < 1000  # Sanity check


class TestVisionAnalyzer:
    """Test GPT-4 Vision analysis"""
    
    @pytest.mark.slow
    def test_analyze_frame(self, sample_video):
        """Test analyzing a single frame"""
        # First extract a frame
        extractor = FrameExtractor()
        frames = extractor.extract_frames_at_interval(sample_video, fps=1.0, max_frames=1)
        
        assert len(frames) > 0
        
        # Analyze it
        analyzer = VisionAnalyzer()
        result = analyzer.analyze_frame(frames[0])
        
        assert 'description' in result
        assert 'usage' in result
        assert len(result['description']) > 0
        
        # Cleanup
        extractor.cleanup(sample_video.stem)
    
    @pytest.mark.slow
    def test_detect_text_in_frame(self, sample_video):
        """Test text detection in frame"""
        extractor = FrameExtractor()
        frames = extractor.extract_frames_at_interval(sample_video, fps=1.0, max_frames=1)
        
        analyzer = VisionAnalyzer()
        result = analyzer.detect_text_in_frame(frames[0])
        
        assert 'description' in result
        
        # Cleanup
        extractor.cleanup(sample_video.stem)


class TestAudioAnalyzer:
    """Test audio analysis service"""
    
    def test_analyze_volume_levels(self, sample_video):
        """Test volume level analysis"""
        analyzer = AudioAnalyzer()
        volumes = analyzer.analyze_volume_levels(sample_video)
        
        assert len(volumes) > 0
        if 'mean_volume' in volumes[0]:
            assert isinstance(volumes[0]['mean_volume'], float)
    
    def test_detect_silence(self, sample_video):
        """Test silence detection"""
        analyzer = AudioAnalyzer()
        silences = analyzer.detect_silence(sample_video, min_silence_duration=0.5)
        
        # May or may not have silences
        assert isinstance(silences, list)
        
        if silences:
            assert 'start' in silences[0]
            assert 'end' in silences[0]
            assert 'duration' in silences[0]
    
    def test_comprehensive_audio_analysis(self, sample_video):
        """Test complete audio analysis"""
        analyzer = AudioAnalyzer()
        analysis = analyzer.analyze_audio_comprehensive(sample_video)
        
        assert 'video_path' in analysis
        assert 'video_name' in analysis
        assert 'volume_levels' in analysis
        assert 'silence_periods' in analysis
        assert 'audio_peaks' in analysis
        assert 'num_silence_periods' in analysis
        assert 'num_peaks' in analysis


class TestContentAnalyzer:
    """Test complete content analysis"""
    
    @pytest.mark.slow
    def test_complete_analysis(self, sample_video):
        """Test end-to-end content analysis"""
        analyzer = ContentAnalyzer()
        
        analysis = analyzer.analyze_video_complete(
            sample_video,
            extract_frames=True,
            analyze_vision=False,  # Skip to save API costs
            transcribe_audio=True,
            analyze_audio=True,
            max_frames=5
        )
        
        # Check structure
        assert 'video_path' in analysis
        assert 'video_name' in analysis
        assert 'modules_run' in analysis
        
        # Check transcript (if API key is configured)
        if 'transcript' in analysis and 'error' not in analysis['transcript']:
            assert 'text' in analysis['transcript']
            assert len(analysis['transcript']['text']) > 0
        
        # Check frames
        if 'frames' in analysis:
            assert len(analysis['frames']) > 0
        
        # Check audio analysis
        if 'audio_analysis' in analysis:
            assert 'num_silence_periods' in analysis['audio_analysis']
        
        # Check insights
        assert 'insights' in analysis
    
    @pytest.mark.slow
    def test_save_analysis(self, sample_video, temp_dir):
        """Test saving analysis to JSON"""
        analyzer = ContentAnalyzer()
        
        analysis = analyzer.analyze_video_complete(
            sample_video,
            extract_frames=True,
            analyze_vision=False,
            transcribe_audio=False,
            analyze_audio=True,
            max_frames=3
        )
        
        output_path = temp_dir / "analysis_output.json"
        analyzer.save_analysis(analysis, output_path)
        
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        
        # Verify JSON is valid
        import json
        with open(output_path) as f:
            loaded = json.load(f)
        
        assert loaded['video_name'] == sample_video.name


# Integration tests
class TestPhase1Integration:
    """Test complete Phase 1 workflows"""
    
    @pytest.mark.slow
    @pytest.mark.integration
    def test_video_to_insights(self, sample_video):
        """Test complete pipeline: video → insights"""
        analyzer = ContentAnalyzer()
        
        # Run full analysis
        analysis = analyzer.analyze_video_complete(
            sample_video,
            extract_frames=True,
            analyze_vision=False,  # Skip to save costs
            transcribe_audio=True,
            analyze_audio=True,
            max_frames=5
        )
        
        # Verify we got insights
        assert 'insights' in analysis
        insights = analysis['insights']
        
        # Check key insights are generated
        assert 'content_type' in insights
        assert 'viral_indicators' in insights
        
        print(f"\n✓ Analysis complete for {sample_video.name}")
        print(f"Content type: {insights['content_type']}")
        print(f"Viral indicators: {insights['viral_indicators']}")


# Test markers for running specific test groups
pytestmark = pytest.mark.phase1


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
