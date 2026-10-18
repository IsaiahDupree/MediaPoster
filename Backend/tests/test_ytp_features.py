"""
Tests for YTP (YouTube Pipeline) features
==========================================
Validates all YouTube pipeline services and integrations.
"""
import pytest
from datetime import datetime, timezone


class TestYTP001_PlaylistWatcher:
    """YTP-001: YouTube Playlist Watcher"""

    def test_pipeline_imports(self):
        from automation.youtube_playlist_pipeline import YouTubePlaylistPipeline
        assert YouTubePlaylistPipeline is not None

    def test_add_playlist(self):
        from automation.youtube_playlist_pipeline import YouTubePlaylistPipeline
        p = YouTubePlaylistPipeline.__new__(YouTubePlaylistPipeline)
        assert hasattr(p, 'add_playlist')

    def test_get_watched_playlists(self):
        from automation.youtube_playlist_pipeline import YouTubePlaylistPipeline
        p = YouTubePlaylistPipeline.__new__(YouTubePlaylistPipeline)
        assert hasattr(p, 'get_watched_playlists')


class TestYTP002_RapidAPITranscript:
    """YTP-002: RapidAPI Transcript Service"""

    def test_service_imports(self):
        from services.rapidapi_transcript import RapidAPITranscriptService
        assert RapidAPITranscriptService is not None

    def test_get_transcript_method(self):
        from services.rapidapi_transcript import RapidAPITranscriptService
        svc = RapidAPITranscriptService()
        assert hasattr(svc, 'get_transcript')

    def test_multi_language_support(self):
        from services.rapidapi_transcript import RapidAPITranscriptService
        svc = RapidAPITranscriptService()
        assert hasattr(svc, 'get_available_languages')
        assert hasattr(svc, 'get_multi_language_transcripts')


class TestYTP003_TranscriptAnalysis:
    """YTP-003: Transcript AI Analysis"""

    def test_analyzer_imports(self):
        from services.transcript_analyzer import TranscriptAnalyzer
        assert TranscriptAnalyzer is not None

    def test_analyze_method(self):
        from services.transcript_analyzer import TranscriptAnalyzer
        a = TranscriptAnalyzer()
        assert hasattr(a, 'analyze')

    def test_blog_generation(self):
        from services.transcript_analyzer import TranscriptAnalyzer
        a = TranscriptAnalyzer()
        assert hasattr(a, 'generate_blog_post')

    def test_analysis_dataclass(self):
        from services.transcript_analyzer import TranscriptAnalysis
        analysis = TranscriptAnalysis(video_id="test123")
        assert analysis.video_id == "test123"
        assert isinstance(analysis.key_topics, list)
        assert isinstance(analysis.social_hooks, list)


class TestYTP004_MediumPublisher:
    """YTP-004: Medium Blog Publisher"""

    def test_publisher_imports(self):
        from services.medium_publisher import MediumPublisher
        assert MediumPublisher is not None

    def test_publish_method(self):
        from services.medium_publisher import MediumPublisher
        p = MediumPublisher()
        assert hasattr(p, 'publish')
        assert hasattr(p, 'get_user')

    def test_medium_post_dataclass(self):
        from services.medium_publisher import MediumPost
        post = MediumPost(title="Test", content="Hello")
        assert post.title == "Test"
        assert post.publish_status == "draft"


class TestYTP005_SocialDistribution:
    """YTP-005: Multi-Platform Social Distribution"""

    def test_distributor_imports(self):
        from services.social_distributor import SocialDistributor
        assert SocialDistributor is not None

    def test_add_target(self):
        from services.social_distributor import SocialDistributor
        d = SocialDistributor()
        d.add_target("twitter")
        assert len(d.get_targets()) == 1

    def test_distribute_method(self):
        from services.social_distributor import SocialDistributor
        d = SocialDistributor()
        assert hasattr(d, 'distribute')

    def test_format_for_platform(self):
        from services.social_distributor import SocialDistributor
        d = SocialDistributor()
        result = d._format_for_platform(
            {"title": "Test", "social_hooks": ["Hook 1"], "hashtags": ["ai"]},
            "twitter"
        )
        assert "text" in result


class TestYTP006_GoogleSheetSync:
    """YTP-006: Google Sheet Sync"""

    def test_sync_imports(self):
        from services.sheets_sync import GoogleSheetsSync
        assert GoogleSheetsSync is not None

    def test_sync_methods(self):
        from services.sheets_sync import GoogleSheetsSync
        s = GoogleSheetsSync()
        assert hasattr(s, 'sync_row')
        assert hasattr(s, 'sync_batch')
        assert hasattr(s, 'get_processed_video_ids')

    def test_sheet_row_dataclass(self):
        from services.sheets_sync import SheetRow
        row = SheetRow(video_id="v1", title="Test", channel="Ch", processed_at="2026-01-01")
        assert row.video_id == "v1"


class TestYTP007_PipelineOrchestrator:
    """YTP-007: YouTube Playlist Pipeline Orchestrator"""

    def test_pipeline_singleton(self):
        from automation.youtube_playlist_pipeline import YouTubePlaylistPipeline
        p = YouTubePlaylistPipeline.get_instance()
        assert p is not None
        YouTubePlaylistPipeline.reset_instance()

    def test_process_video(self):
        from automation.youtube_playlist_pipeline import YouTubePlaylistPipeline
        p = YouTubePlaylistPipeline.__new__(YouTubePlaylistPipeline)
        assert hasattr(p, 'process_video')

    def test_get_stats(self):
        from automation.youtube_playlist_pipeline import YouTubePlaylistPipeline
        p = YouTubePlaylistPipeline.__new__(YouTubePlaylistPipeline)
        assert hasattr(p, 'get_stats')

    def test_api_endpoint_exists(self):
        from api.endpoints.youtube_automation import router
        assert router is not None
        paths = [r.path for r in router.routes]
        assert len(paths) >= 3


class TestYTP008_ThumbnailUpload:
    """YTP-008: Thumbnail Upload to Google Drive"""

    def test_uploader_imports(self):
        from services.drive_uploader import GoogleDriveUploader
        assert GoogleDriveUploader is not None

    def test_upload_method(self):
        from services.drive_uploader import GoogleDriveUploader
        u = GoogleDriveUploader()
        assert hasattr(u, 'upload')
        assert hasattr(u, 'upload_thumbnail')


class TestYTP009_Placeholder:
    """YTP-009 not in pending list - skip"""
    pass


class TestYTP011_MultiLanguage:
    """YTP-011: Multi-Language Transcript Support"""

    def test_rapidapi_multi_language(self):
        from services.rapidapi_transcript import RapidAPITranscriptService
        svc = RapidAPITranscriptService()
        assert hasattr(svc, 'get_multi_language_transcripts')

    def test_transcript_result_has_language(self):
        from services.rapidapi_transcript import RapidAPITranscriptResult
        r = RapidAPITranscriptResult(video_id="v1", language="es")
        assert r.language == "es"


class TestYTP012_VideoClipExtraction:
    """YTP-012: Video Clip Extraction"""

    def test_clipper_imports(self):
        from services.video_clipper import VideoClipper
        assert VideoClipper is not None

    def test_extract_methods(self):
        from services.video_clipper import VideoClipper
        c = VideoClipper()
        assert hasattr(c, 'extract_clip')
        assert hasattr(c, 'extract_clips')
        assert hasattr(c, 'extract_highlights')

    def test_clip_spec(self):
        from services.video_clipper import ClipSpec
        spec = ClipSpec(start_seconds=10, end_seconds=70, label="intro")
        assert spec.start_seconds == 10
        assert spec.label == "intro"


class TestYTP013_ContentAnalytics:
    """YTP-013: Content Performance Analytics"""

    def test_analytics_imports(self):
        from services.content_analytics import ContentAnalyticsService
        assert ContentAnalyticsService is not None

    def test_track_and_query(self):
        from services.content_analytics import ContentAnalyticsService, ContentMetrics
        svc = ContentAnalyticsService()
        svc.track(ContentMetrics(
            content_id="c1",
            source_video_id="v1",
            platform="twitter",
            views=100,
            likes=10,
        ))
        metrics = svc.get_metrics("c1")
        assert len(metrics) == 1
        assert metrics[0].views == 100

    def test_aggregate(self):
        from services.content_analytics import ContentAnalyticsService, ContentMetrics
        svc = ContentAnalyticsService()
        svc.track(ContentMetrics(content_id="c1", source_video_id="v1", platform="twitter", views=100, likes=10))
        svc.track(ContentMetrics(content_id="c2", source_video_id="v1", platform="instagram", views=200, likes=20))
        agg = svc.get_aggregate("v1")
        assert agg["total_views"] == 300
        assert agg["total_likes"] == 30


class TestYTP014_PromptABTesting:
    """YTP-014: A/B Testing for AI Prompts"""

    def test_service_imports(self):
        from services.prompt_ab_testing import PromptABTestingService
        assert PromptABTestingService is not None

    def test_variant_registration(self):
        from services.prompt_ab_testing import PromptABTestingService, PromptVariant
        svc = PromptABTestingService()
        svc.register_variants("test1", [
            PromptVariant(variant_id="a", name="A", prompt_template="Prompt A"),
            PromptVariant(variant_id="b", name="B", prompt_template="Prompt B"),
        ])
        selected = svc.select_variant("test1")
        assert selected is not None
        assert selected.variant_id in ["a", "b"]


class TestYTP015_ErrorMonitoring:
    """YTP-015: Error Monitoring & Alerts"""

    def test_monitor_imports(self):
        from services.pipeline_monitor import PipelineMonitor
        assert PipelineMonitor is not None

    def test_record_error(self):
        from services.pipeline_monitor import PipelineMonitor
        m = PipelineMonitor()
        err = m.record_error("download", "timeout", "Download timed out")
        assert err.pipeline_stage == "download"
        assert err.severity == "error"

    def test_get_health(self):
        from services.pipeline_monitor import PipelineMonitor
        m = PipelineMonitor()
        health = m.get_health()
        assert health["status"] == "healthy"


class TestYTP016_DurationRouter:
    """YTP-016: Video Duration Router"""

    def test_router_imports(self):
        from services.youtube.duration_router import DurationRouter
        assert DurationRouter is not None

    def test_short_video_routing(self):
        from services.youtube.duration_router import DurationRouter
        router = DurationRouter()
        decision = router.route("v1", 600)  # 10 min
        assert decision.route == "whisper_api"

    def test_long_video_routing(self):
        from services.youtube.duration_router import DurationRouter
        router = DurationRouter()
        decision = router.route("v2", 3600)  # 60 min
        assert decision.route == "local_chunked"
        assert decision.chunk_count == 6


class TestYTP017_LocalTranscription:
    """YTP-017: Local Transcription Service"""

    def test_service_imports(self):
        from services.youtube.local_transcription import LocalTranscriptionService
        assert LocalTranscriptionService is not None

    def test_transcribe_method(self):
        from services.youtube.local_transcription import LocalTranscriptionService
        svc = LocalTranscriptionService()
        assert hasattr(svc, 'transcribe')
        assert hasattr(svc, 'transcribe_chunks')


class TestYTP018_YTDLPDownloader:
    """YTP-018: yt-dlp Video Downloader"""

    def test_downloader_imports(self):
        from services.youtube.downloader import YTDLPDownloader
        assert YTDLPDownloader is not None

    def test_download_methods(self):
        from services.youtube.downloader import YTDLPDownloader
        d = YTDLPDownloader()
        assert hasattr(d, 'download')
        assert hasattr(d, 'download_audio')
        assert hasattr(d, 'get_video_info')


class TestYTP019_FFmpegAudioExtraction:
    """YTP-019: FFmpeg Audio Extraction"""

    def test_extractor_imports(self):
        from services.youtube.audio_extractor import FFmpegAudioExtractor
        assert FFmpegAudioExtractor is not None

    def test_extract_methods(self):
        from services.youtube.audio_extractor import FFmpegAudioExtractor
        e = FFmpegAudioExtractor()
        assert hasattr(e, 'extract')
        assert hasattr(e, 'split_audio')


class TestYTP020_WhisperAPI:
    """YTP-020: Whisper API Integration"""

    def test_transcriber_imports(self):
        from services.youtube.whisper_transcriber import WhisperAPITranscriber
        assert WhisperAPITranscriber is not None

    def test_transcribe_methods(self):
        from services.youtube.whisper_transcriber import WhisperAPITranscriber
        t = WhisperAPITranscriber()
        assert hasattr(t, 'transcribe')
        assert hasattr(t, 'transcribe_chunks')

    def test_result_dataclass(self):
        from services.youtube.whisper_transcriber import TranscriptionResult
        r = TranscriptionResult(audio_file="test.wav", text="hello")
        assert r.text == "hello"
        assert r.model == "whisper-1"


class TestYTP021_TranscriptCache:
    """YTP-021: Transcript Caching"""

    def test_cache_imports(self):
        from services.youtube.transcript_cache import TranscriptCache
        assert TranscriptCache is not None

    def test_cache_operations(self):
        from services.youtube.transcript_cache import TranscriptCache
        import tempfile
        cache = TranscriptCache(cache_dir=tempfile.mkdtemp())
        cache.put("vid1", {"text": "hello", "language": "en"})
        assert cache.has("vid1")
        result = cache.get("vid1")
        assert result["text"] == "hello"
        cache.invalidate("vid1")
        assert not cache.has("vid1")

    def test_cache_stats(self):
        from services.youtube.transcript_cache import TranscriptCache
        import tempfile
        cache = TranscriptCache(cache_dir=tempfile.mkdtemp())
        stats = cache.get_stats()
        assert "entries" in stats


class TestYTP022_TempFileCleanup:
    """YTP-022: Temp File Cleanup Service"""

    def test_cleanup_imports(self):
        from services.youtube.cleanup import TempFileCleanup
        assert TempFileCleanup is not None

    def test_cleanup_methods(self):
        from services.youtube.cleanup import TempFileCleanup
        c = TempFileCleanup()
        assert hasattr(c, 'cleanup_old_files')
        assert hasattr(c, 'cleanup_directory')
        assert hasattr(c, 'get_disk_usage')
        assert hasattr(c, 'should_cleanup')

    def test_disk_usage(self):
        from services.youtube.cleanup import TempFileCleanup
        c = TempFileCleanup()
        usage = c.get_disk_usage()
        assert "total_bytes" in usage
        assert "over_threshold" in usage


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
