"""
Tests for Clip Editor Service
Tests clip configuration, platform variants, and timing validation
"""
import pytest
import uuid
from datetime import datetime

from services.clip_editor import ClipEditor
from database.models import VideoClip, AnalyzedVideo, ContentItem


@pytest.fixture
def editor(db_session):
    """Create clip editor for testing"""
    return ClipEditor(db_session)


@pytest.fixture
def test_video(db_session):
    """Create a test video"""
    # Create content item first
    content = ContentItem(
        id=uuid.uuid4(),
        title="Test Video",
        description="Test Description",
        source_url="http://example.com/video.mp4",
        type="video",
        # status="analyzed" # status is not in ContentItem model based on view_file output
    )
    db_session.add(content)
    
    video = AnalyzedVideo(
        id=content.id, # One-to-one relationship shares ID
        duration_seconds=120.0
    )
    db_session.add(video)
    db_session.commit()
    return video


@pytest.fixture
def test_clip(db_session, test_video):
    """Create a test clip"""
    clip = VideoClip(
        id=uuid.uuid4(),
        video_id=test_video.id,
        user_id=uuid.uuid4(),
        start_time=10.0,
        end_time=45.0,
        title="Test Clip",
        clip_type="custom",
        status="draft"
    )
    db_session.add(clip)
    db_session.commit()
    return clip


class TestClipCreation:
    """Test clip creation functionality"""
    
    def test_create_clip_success(self, editor, test_video):
        """Test successful clip creation"""
        clip = editor.create_clip(
            video_id=str(test_video.id),
            user_id=str(uuid.uuid4()),
            start_time=10.0,
            end_time=45.0,
            title="My Awesome Clip",
            description="This is a test clip",
            clip_type="highlight"
        )
        
        assert clip.id is not None
        assert clip.title == "My Awesome Clip"
        assert clip.start_time == 10.0
        assert clip.end_time == 45.0
        assert clip.status == "draft"
    
    def test_create_clip_with_configs(self, editor, test_video):
        """Test creating clip with overlay and caption configs"""
        overlay_config = {"text": "WATCH THIS", "position": "bottom"}
        caption_config = {"style": "bold", "animation": "fade_in"}
        thumbnail_config = {"frame_time": 15.0}
        
        clip = editor.create_clip(
            video_id=str(test_video.id),
            user_id=str(uuid.uuid4()),
            start_time=5.0,
            end_time=25.0,
            overlay_config=overlay_config,
            caption_config=caption_config,
            thumbnail_config=thumbnail_config
        )
        
        assert clip.overlay_config == overlay_config
        assert clip.caption_config == caption_config
        assert clip.thumbnail_config == thumbnail_config
    
    def test_create_clip_ai_suggested(self, editor, test_video):
        """Test creating AI-suggested clip"""
        clip = editor.create_clip(
            video_id=str(test_video.id),
            user_id=str(uuid.uuid4()),
            start_time=0.0,
            end_time=30.0,
            ai_suggested=True,
            ai_score=0.85,
            ai_reasoning="Strong hook with good visual engagement"
        )
        
        assert clip.ai_suggested is True
        assert clip.ai_score == 0.85
        assert clip.ai_reasoning is not None
    
    def test_create_clip_invalid_video_raises_error(self, editor):
        """Test that creating clip with invalid video raises error"""
        with pytest.raises(ValueError, match="not found"):
            editor.create_clip(
                video_id=str(uuid.uuid4()),
                user_id=str(uuid.uuid4()),
                start_time=0.0,
                end_time=30.0
            )


class TestTimingValidation:
    """Test clip timing validation"""
    
    def test_negative_start_time_raises_error(self, editor, test_video):
        """Test that negative start time raises error"""
        with pytest.raises(ValueError, match="Start time cannot be negative"):
            editor.create_clip(
                video_id=str(test_video.id),
                user_id="user1",
                start_time=-5.0,
                end_time=30.0
            )
    
    def test_end_before_start_raises_error(self, editor, test_video):
        """Test that end time before start raises error"""
        with pytest.raises(ValueError, match="End time must be greater"):
            editor.create_clip(
                video_id=str(test_video.id),
                user_id="user1",
                start_time=50.0,
                end_time=30.0
            )
    
    def test_exceeds_video_duration_raises_error(self, editor, test_video):
        """Test that clip exceeding video duration raises error"""
        with pytest.raises(ValueError, match="exceeds video duration"):
            editor.create_clip(
                video_id=str(test_video.id),
                user_id="user1",
                start_time=100.0,
                end_time=150.0  # Video is only 120s
            )
    
    def test_too_short_clip_raises_error(self, editor, test_video):
        """Test that clip shorter than 5s raises error"""
        with pytest.raises(ValueError, match="at least 5 seconds"):
            editor.create_clip(
                video_id=str(test_video.id),
                user_id="user1",
                start_time=10.0,
                end_time=12.0  # Only 2 seconds
            )


class TestClipUpdates:
    """Test clip configuration updates"""
    
    def test_update_clip_config(self, editor, test_clip, db_session):
        """Test updating clip configuration"""
        new_overlay = {"text": "NEW TEXT", "position": "top"}
        
        updated_clip = editor.update_clip_config(
            clip_id=str(test_clip.id),
            overlay_config=new_overlay,
            title="Updated Title"
        )
        
        assert updated_clip.overlay_config == new_overlay
        assert updated_clip.title == "Updated Title"
        
        # Verify in DB
        db_session.refresh(test_clip)
        assert test_clip.title == "Updated Title"
    
    def test_update_clip_status(self, editor, test_clip):
        """Test updating clip status"""
        updated_clip = editor.update_clip_config(
            clip_id=str(test_clip.id),
            status="ready"
        )
        
        assert updated_clip.status == "ready"
    
    def test_update_nonexistent_clip_raises_error(self, editor):
        """Test updating nonexistent clip raises error"""
        with pytest.raises(ValueError, match="not found"):
            editor.update_clip_config(
                clip_id=str(uuid.uuid4()),
                title="New Title"
            )


class TestPlatformVariants:
    """Test platform variant generation"""
    
    def test_generate_all_platform_variants(self, editor, test_clip):
        """Test generating variants for all platforms"""
        variants = editor.generate_platform_variants(str(test_clip.id))
        
        # Should have variants for all major platforms
        assert "tiktok" in variants
        assert "youtube" in variants
        assert "instagram_reel" in variants
        
        # Each variant should have required fields
        for platform, config in variants.items():
            assert "aspect_ratio" in config
            assert "orientation" in config
            assert "dimensions" in config
            assert "recommended_duration" in config
    
    def test_generate_specific_platform_variants(self, editor, test_clip):
        """Test generating variants for specific platforms"""
        platforms = ["tiktok", "youtube"]
        variants = editor.generate_platform_variants(
            str(test_clip.id),
            platforms=platforms
        )
        
        assert len(variants) == 2
        assert "tiktok" in variants
        assert "youtube" in variants
        assert "instagram_feed" not in variants
    
    def test_platform_variant_has_correct_dimensions(self, editor, test_clip):
        """Test that platform variants have correct dimensions"""
        variants = editor.generate_platform_variants(
            str(test_clip.id),
            platforms=["tiktok", "youtube"]
        )
        
        # TikTok should be vertical (9:16)
        tiktok = variants["tiktok"]
        assert tiktok["orientation"] == "portrait"
        assert tiktok["dimensions"]["width"] == 1080
        assert tiktok["dimensions"]["height"] == 1920
        
        # YouTube should be landscape (16:9)
        youtube = variants["youtube"]
        assert youtube["orientation"] == "landscape"
        assert youtube["dimensions"]["width"] == 1280
        assert youtube["dimensions"]["height"] == 720
    
    def test_platform_variant_duration_recommendations(self, editor, test_clip):
        """Test that duration recommendations are platform-specific"""
        variants = editor.generate_platform_variants(
            str(test_clip.id),
            platforms=["tiktok", "youtube"]
        )
        
        # TikTok optimal: 15-60s
        tiktok_rec = variants["tiktok"]["recommended_duration"]
        assert tiktok_rec["min"] == 15
        assert tiktok_rec["max"] == 60
        
        # YouTube optimal: 60-180s
        youtube_rec = variants["youtube"]["recommended_duration"]
        assert youtube_rec["min"] == 60
        assert youtube_rec["max"] == 180


class TestClipRetrieval:
    """Test clip retrieval methods"""
    
    def test_get_clip_preview_data(self, editor, test_clip):
        """Test getting clip preview data"""
        preview = editor.get_clip_preview_data(str(test_clip.id))
        
        assert preview["clip_id"] == str(test_clip.id)
        assert preview["start_time"] == test_clip.start_time
        assert preview["end_time"] == test_clip.end_time
        assert "duration" in preview
        assert preview["status"] == "draft"
    
    def test_get_video_clips(self, editor, test_video, test_clip):
        """Test getting all clips for a video"""
        clips = editor.get_video_clips(str(test_video.id))
        
        assert len(clips) >= 1
        assert any(c.id == test_clip.id for c in clips)
    
    def test_get_video_clips_with_status_filter(self, editor, test_video, test_clip):
        """Test getting clips filtered by status"""
        clips = editor.get_video_clips(str(test_video.id), status="draft")
        
        assert all(c.status == "draft" for c in clips)
    
    def test_get_preview_nonexistent_clip_raises_error(self, editor):
        """Test getting preview for nonexistent clip raises error"""
        with pytest.raises(ValueError, match="not found"):
            editor.get_clip_preview_data(str(uuid.uuid4()))


class TestClipDeletion:
    """Test clip deletion"""
    
    def test_delete_clip_success(self, editor, test_clip, db_session):
        """Test successful clip deletion"""
        result = editor.delete_clip(str(test_clip.id))
        
        assert result is True
        
        # Verify in DB
        db_session.expire_all()
        deleted = db_session.query(VideoClip).filter_by(id=test_clip.id).first()
        assert deleted is None
    
    def test_delete_nonexistent_clip_returns_false(self, editor):
        """Test deleting nonexistent clip returns False"""
        result = editor.delete_clip(str(uuid.uuid4()))
        
        assert result is False


class TestPlatformConfigs:
    """Test platform-specific configuration generation"""
    
    def test_caption_config_portrait(self, editor):
        """Test caption config for portrait orientation"""
        caption_config = editor._get_platform_caption_config("tiktok", "portrait")
        
        assert caption_config["enabled"] is True
        assert caption_config["font_size"] == "large"  # Larger for portrait
        assert "position" in caption_config
    
    def test_caption_config_landscape(self, editor):
        """Test caption config for landscape orientation"""
        caption_config = editor._get_platform_caption_config("youtube", "landscape")
        
        assert caption_config["enabled"] is True
        assert caption_config["font_size"] == "medium"  # Medium for landscape
    
    def test_overlay_config_generation(self, editor):
        """Test overlay config generation"""
        overlay_config = editor._get_platform_overlay_config("tiktok", "portrait")
        
        assert "position" in overlay_config
        assert "font_size" in overlay_config
        assert overlay_config["enabled"] is False  # Default disabled
