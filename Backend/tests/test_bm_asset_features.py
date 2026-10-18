"""
Tests for BM-013 to BM-017 (Content Repurposing) and ASSET-001 to ASSET-003.
"""
import pytest


class TestBM013_ViralClipDetection:
    """BM-013: Content Repurposing: Viral Clip Detection"""

    def test_detector_imports(self):
        from services.viral_clip_detector import ViralClipDetector
        assert ViralClipDetector is not None

    def test_detect_method(self):
        from services.viral_clip_detector import ViralClipDetector
        d = ViralClipDetector()
        segments = [
            {"start": 0, "end": 30, "text": "What's the secret to going viral? Let me tell you the truth."},
            {"start": 30, "end": 60, "text": "Here is some regular content."},
            {"start": 60, "end": 90, "text": "This is absolutely incredible and amazing content that will blow your mind?"},
        ]
        candidates = d.detect(segments)
        assert len(candidates) >= 1
        assert candidates[0].score > 0

    def test_get_top_clips(self):
        from services.viral_clip_detector import ViralClipDetector
        d = ViralClipDetector(min_score=0.1)
        segments = [
            {"start": 0, "end": 30, "text": "What is the secret hack to success?"},
            {"start": 30, "end": 60, "text": "Regular content without hooks."},
        ]
        top = d.get_top_clips(segments, max_clips=3)
        assert isinstance(top, list)


class TestBM014_SmartReframing:
    """BM-014: Content Repurposing: Smart Reframing"""

    def test_reframer_imports(self):
        from services.smart_reframer import SmartReframer, ReframeConfig
        assert SmartReframer is not None
        assert ReframeConfig is not None

    def test_config_defaults(self):
        from services.smart_reframer import ReframeConfig
        config = ReframeConfig()
        assert config.target_width == 1080
        assert config.target_height == 1920
        assert config.aspect_ratio == "9:16"

    def test_reframe_method(self):
        from services.smart_reframer import SmartReframer
        r = SmartReframer()
        assert hasattr(r, 'reframe')
        assert hasattr(r, 'reframe_batch')


class TestBM015_CaptionGeneration:
    """BM-015: Content Repurposing: Caption Generation"""

    def test_generator_imports(self):
        from services.caption_generator import CaptionGenerator, CaptionStyle
        assert CaptionGenerator is not None
        assert CaptionStyle is not None

    def test_generate_srt(self):
        from services.caption_generator import CaptionGenerator, CaptionSegment
        import tempfile, os
        g = CaptionGenerator(output_dir=tempfile.mkdtemp())
        segments = [
            CaptionSegment(start=0, end=3, text="Hello world"),
            CaptionSegment(start=3, end=6, text="This is a test"),
        ]
        srt_path = g.generate_srt(segments)
        assert os.path.exists(srt_path)
        content = open(srt_path).read()
        assert "Hello world" in content
        assert "00:00:00,000 --> 00:00:03,000" in content

    def test_burn_captions_method(self):
        from services.caption_generator import CaptionGenerator
        g = CaptionGenerator()
        assert hasattr(g, 'burn_captions')


class TestBM016_TitleCardOverlay:
    """BM-016: Content Repurposing: Title Card Overlay"""

    def test_generator_imports(self):
        from services.title_card_generator import TitleCardGenerator, TitleCardConfig
        assert TitleCardGenerator is not None
        assert TitleCardConfig is not None

    def test_config_defaults(self):
        from services.title_card_generator import TitleCardConfig
        config = TitleCardConfig()
        assert config.width == 1080
        assert config.height == 1920
        assert config.duration_seconds == 3.0

    def test_generate_method(self):
        from services.title_card_generator import TitleCardGenerator
        g = TitleCardGenerator()
        assert hasattr(g, 'generate')
        assert hasattr(g, 'prepend_to_video')


class TestBM017_VlogToShortsPipeline:
    """BM-017: Dev Vlog to YouTube Shorts Pipeline"""

    def test_pipeline_imports(self):
        from services.vlog_to_shorts_pipeline import VlogToShortsPipeline
        assert VlogToShortsPipeline is not None

    def test_process_method(self):
        from services.vlog_to_shorts_pipeline import VlogToShortsPipeline
        p = VlogToShortsPipeline()
        assert hasattr(p, 'process')
        assert hasattr(p, 'process_and_render')

    def test_generated_short_dataclass(self):
        from services.vlog_to_shorts_pipeline import GeneratedShort
        s = GeneratedShort(
            short_id="s1",
            source_video_id="v1",
            file_path="/tmp/test.mp4",
            title="Test Short",
            description="A test",
            duration_seconds=45,
        )
        assert s.is_vertical == True
        assert s.status == "ready"

    def test_get_stats(self):
        from services.vlog_to_shorts_pipeline import VlogToShortsPipeline
        p = VlogToShortsPipeline()
        stats = p.get_stats()
        assert stats["total_generated"] == 0


class TestASSET001_GiphyIntegration:
    """ASSET-001: Giphy Integration"""

    def test_service_imports(self):
        from services.giphy_service import GiphyService
        assert GiphyService is not None

    def test_search_method(self):
        from services.giphy_service import GiphyService
        s = GiphyService()
        assert hasattr(s, 'search')
        assert hasattr(s, 'get_trending')

    def test_result_dataclass(self):
        from services.giphy_service import GiphyResult
        r = GiphyResult(gif_id="123", title="Test", url="http://test.gif", embed_url="http://embed")
        assert r.gif_id == "123"


class TestASSET002_PexelsIntegration:
    """ASSET-002: Pexels Integration"""

    def test_service_imports(self):
        from services.pexels_service import PexelsService
        assert PexelsService is not None

    def test_search_methods(self):
        from services.pexels_service import PexelsService
        s = PexelsService()
        assert hasattr(s, 'search_photos')
        assert hasattr(s, 'search_videos')

    def test_photo_dataclass(self):
        from services.pexels_service import PexelsPhoto
        p = PexelsPhoto(photo_id=1, photographer="Test", url="http://test", src_original="http://orig", src_large="http://lg", src_medium="http://md")
        assert p.photo_id == 1


class TestASSET003_UnsplashIntegration:
    """ASSET-003: Unsplash Integration"""

    def test_service_imports(self):
        from services.unsplash_service import UnsplashService
        assert UnsplashService is not None

    def test_search_method(self):
        from services.unsplash_service import UnsplashService
        s = UnsplashService()
        assert hasattr(s, 'search')
        assert hasattr(s, 'get_random')

    def test_photo_dataclass(self):
        from services.unsplash_service import UnsplashPhoto
        p = UnsplashPhoto(
            photo_id="abc", description="Test", photographer="Jane",
            url_raw="", url_full="", url_regular="", url_small="", url_thumb="",
        )
        assert p.photo_id == "abc"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
