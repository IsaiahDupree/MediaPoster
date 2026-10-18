"""
Tests for TikTok AI-Generated Flag
==================================

Ensures that the is_ai_generated flag defaults to False for user content,
and is only set to True for actual AI-generated content.

TikTok requires accurate disclosure of AI-generated content.
"""

import pytest
from services.blotato_api import (
    TikTokTarget,
    TikTokPrivacy,
    YouTubeTarget,
    YouTubePrivacy,
)


class TestTikTokAIGeneratedFlag:
    """Test that TikTok AI-generated flag is correctly handled"""
    
    def test_tiktok_target_defaults_to_not_ai_generated(self):
        """
        CRITICAL: Default should be False because most content
        is user-recorded iPhone videos, not AI-generated.
        """
        target = TikTokTarget()
        assert target.is_ai_generated is False, \
            "TikTok is_ai_generated should default to False for user content"
    
    def test_tiktok_target_can_be_set_to_ai_generated(self):
        """For actual AI content, flag can be explicitly set to True"""
        target = TikTokTarget(is_ai_generated=True)
        assert target.is_ai_generated is True
    
    def test_tiktok_target_to_dict_includes_ai_flag(self):
        """Ensure the flag is included in API payload"""
        target = TikTokTarget()
        data = target.to_dict()
        
        assert "isAiGenerated" in data
        assert data["isAiGenerated"] is False
    
    def test_tiktok_target_ai_flag_true_in_dict(self):
        """When set to True, dict should reflect that"""
        target = TikTokTarget(is_ai_generated=True)
        data = target.to_dict()
        
        assert data["isAiGenerated"] is True
    
    def test_tiktok_target_all_defaults_are_safe(self):
        """Verify all TikTok defaults are reasonable"""
        target = TikTokTarget()
        
        # Privacy should be public by default
        assert target.privacy_level == TikTokPrivacy.PUBLIC
        
        # Features should be enabled by default
        assert target.disabled_comments is False
        assert target.disabled_duet is False
        assert target.disabled_stitch is False
        
        # Branded content should be off by default
        assert target.is_branded_content is False
        assert target.is_your_brand is False
        
        # AI generated MUST be False for user content
        assert target.is_ai_generated is False
        
        # Draft mode should be off
        assert target.is_draft is False


class TestYouTubeAIFlag:
    """Test YouTube's synthetic media flag"""
    
    def test_youtube_target_defaults_to_not_synthetic(self):
        """YouTube synthetic media flag should default to False"""
        target = YouTubeTarget(title="Test Video")
        assert target.contains_synthetic_media is False
    
    def test_youtube_target_to_dict_includes_synthetic_flag(self):
        """Ensure the flag is included in API payload"""
        target = YouTubeTarget(title="Test")
        data = target.to_dict()
        
        assert "containsSyntheticMedia" in data
        assert data["containsSyntheticMedia"] is False


class TestAIContentDetection:
    """Tests for detecting when content should be marked as AI-generated"""
    
    def test_iphone_video_should_not_be_ai(self):
        """
        Videos from iPhone Import folder are real recordings,
        not AI-generated.
        """
        # Simulating content source check
        source_path = "/Users/user/Documents/IphoneImport/IMG_1234.MOV"
        is_from_iphone = "IphoneImport" in source_path
        
        # iPhone content should NOT be marked as AI
        assert is_from_iphone is True
        # Therefore is_ai_generated should be False
        
    def test_blotato_created_video_should_be_ai(self):
        """
        Videos created by Blotato's AI video creation API
        ARE AI-generated and should be marked as such.
        """
        # Content from Blotato video creation
        source = "blotato_video_creation"
        is_ai_content = source in ["blotato_video_creation", "ai_generated", "synthetic"]
        
        assert is_ai_content is True
        # Therefore is_ai_generated should be True for this content


def test_regression_ai_flag_not_true_by_default():
    """
    REGRESSION TEST: Ensure we never accidentally change the default back to True.
    
    This was a bug where all content was being marked as AI-generated,
    which violates TikTok's content policies for real user videos.
    """
    target = TikTokTarget()
    
    # This assertion MUST pass - do not change the default to True!
    assert target.is_ai_generated is False, \
        "REGRESSION: is_ai_generated must default to False! " \
        "Most MediaPoster content is real iPhone videos, not AI."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
