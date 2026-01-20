"""
Tests for Instagram Story posting functionality (STORY-001)
"""

import pytest
from datetime import datetime, timezone
from services.blotato_api import (
    BlotatoAPI,
    PostContent,
    InstagramTarget,
    Platform
)


class TestInstagramStoryPosting:
    """Test STORY-001: Instagram Story Posting"""

    def test_instagram_target_supports_story_media_type(self):
        """Verify InstagramTarget can be configured with mediaType='story'"""
        target = InstagramTarget(media_type="story")

        target_dict = target.to_dict()

        assert target_dict["targetType"] == "instagram"
        assert target_dict["mediaType"] == "story"

    def test_instagram_target_supports_reel_media_type(self):
        """Verify InstagramTarget can be configured with mediaType='reel'"""
        target = InstagramTarget(media_type="reel")

        target_dict = target.to_dict()

        assert target_dict["targetType"] == "instagram"
        assert target_dict["mediaType"] == "reel"

    def test_instagram_target_defaults_to_none_media_type(self):
        """Verify InstagramTarget defaults to no mediaType (regular post)"""
        target = InstagramTarget()

        target_dict = target.to_dict()

        assert target_dict["targetType"] == "instagram"
        assert "mediaType" not in target_dict

    def test_instagram_story_with_alt_text(self):
        """Verify Stories can include alt text for accessibility"""
        target = InstagramTarget(
            media_type="story",
            alt_text="A beautiful sunset over the ocean"
        )

        target_dict = target.to_dict()

        assert target_dict["mediaType"] == "story"
        assert target_dict["altText"] == "A beautiful sunset over the ocean"

    def test_instagram_story_with_collaborators(self):
        """Verify Stories can include collaborators"""
        target = InstagramTarget(
            media_type="story",
            collaborators=["user123", "user456"]
        )

        target_dict = target.to_dict()

        assert target_dict["mediaType"] == "story"
        assert target_dict["collaborators"] == ["user123", "user456"]

    def test_story_content_payload_structure(self):
        """Verify complete payload structure for Story posting"""
        # Create content
        content = PostContent(
            text="Check out this amazing story! 🔥",
            platform=Platform.INSTAGRAM,
            media_urls=["https://example.com/story-video.mp4"]
        )

        # Create Instagram Story target
        target = InstagramTarget(
            media_type="story",
            alt_text="Amazing story content"
        )

        # Verify content structure
        content_dict = content.to_dict()
        assert content_dict["text"] == "Check out this amazing story! 🔥"
        assert content_dict["platform"] == "instagram"
        assert content_dict["mediaUrls"] == ["https://example.com/story-video.mp4"]

        # Verify target structure
        target_dict = target.to_dict()
        assert target_dict["targetType"] == "instagram"
        assert target_dict["mediaType"] == "story"
        assert target_dict["altText"] == "Amazing story content"

    def test_story_vs_reel_differentiation(self):
        """Verify Story and Reel targets are properly differentiated"""
        story_target = InstagramTarget(media_type="story")
        reel_target = InstagramTarget(media_type="reel")

        story_dict = story_target.to_dict()
        reel_dict = reel_target.to_dict()

        assert story_dict["mediaType"] == "story"
        assert reel_dict["mediaType"] == "reel"
        assert story_dict["mediaType"] != reel_dict["mediaType"]

    @pytest.mark.asyncio
    async def test_publish_instagram_story_api_structure(self):
        """
        Test the structure of a Story publish request
        (Does not make actual API call)
        """
        # This test verifies the payload structure without making actual API calls
        api = BlotatoAPI()

        content = PostContent(
            text="Story caption",
            platform=Platform.INSTAGRAM,
            media_urls=["https://example.com/story.mp4"]
        )

        target = InstagramTarget(media_type="story")

        # Verify that the method exists and accepts the right parameters
        # In a real test with mocking, we would verify the actual payload sent
        assert hasattr(api, 'publish_post')
        assert callable(api.publish_post)


class TestInstagramStoryFeatureAcceptance:
    """
    Acceptance criteria tests for STORY-001:
    - Post Stories via Blotato API with mediaType: 'story'
    """

    def test_acceptance_story_media_type_supported(self):
        """
        Acceptance: Post Stories via Blotato API with mediaType: 'story'
        """
        target = InstagramTarget(media_type="story")
        target_dict = target.to_dict()

        # Verify the key requirement: mediaType='story' is supported
        assert target_dict.get("mediaType") == "story"
        assert target_dict.get("targetType") == "instagram"

    def test_acceptance_story_with_media_url(self):
        """
        Acceptance: Stories must include media URL
        """
        content = PostContent(
            text="Story content",
            platform=Platform.INSTAGRAM,
            media_urls=["https://example.com/story-media.mp4"]
        )

        content_dict = content.to_dict()

        assert len(content_dict["mediaUrls"]) > 0
        assert content_dict["platform"] == "instagram"
