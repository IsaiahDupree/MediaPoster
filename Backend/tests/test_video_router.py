"""
Unit Tests for Video Router Service
Tests video routing logic based on orientation and duration
"""
import pytest

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.video.video_router import VideoRouter, RoutingDecision
from services.video.video_analyzer import Orientation


class TestVideoRouter:
    """Test suite for video router"""
    
    @pytest.fixture
    def router(self):
        """Create router instance"""
        return VideoRouter()
    
    def test_router_initialization(self, router):
        """Test router initializes correctly"""
        assert router is not None
        assert router.SHORT_FORM_THRESHOLD == 60
    
    def test_route_vertical_short_to_tiktok_reels(self, router):
        """Test vertical < 60s routes to TikTok and Reels"""
        decision = router.determine_platforms(
            video_id="test_1",
            orientation=Orientation.VERTICAL,
            duration=45.0
        )
        
        assert "tiktok" in decision.recommended_platforms
        assert "instagram_reels" in decision.recommended_platforms
        assert "youtube_shorts" in decision.recommended_platforms
        assert decision.routing_rule == "vertical_short_form"
        assert decision.auto_routed is True
    
    def test_route_vertical_medium_to_reels(self, router):
        """Test vertical 60-90s routes to Reels"""
        decision = router.determine_platforms(
            video_id="test_2",
            orientation=Orientation.VERTICAL,
            duration=75.0
        )
        
        assert "instagram_reels" in decision.recommended_platforms
        assert "youtube_shorts" in decision.recommended_platforms
        assert decision.routing_rule == "vertical_medium_form"
    
    def test_route_vertical_long_to_reels_only(self, router):
        """Test vertical > 90s routes to Instagram Reels only"""
        decision = router.determine_platforms(
            video_id="test_3",
            orientation=Orientation.VERTICAL,
            duration=120.0
        )
        
        assert "instagram_reels" in decision.recommended_platforms
        assert len(decision.recommended_platforms) == 1
        assert decision.routing_rule == "vertical_long_form"
    
    def test_route_horizontal_short_to_youtube_shorts(self, router):
        """Test horizontal < 60s routes to YouTube Shorts"""
        decision = router.determine_platforms(
            video_id="test_4",
            orientation=Orientation.HORIZONTAL,
            duration=45.0
        )
        
        assert "youtube_shorts" in decision.recommended_platforms
        assert "facebook" in decision.recommended_platforms
        assert decision.routing_rule == "horizontal_short_form"
    
    def test_route_horizontal_long_to_youtube(self, router):
        """Test horizontal > 60s routes to YouTube main channel"""
        decision = router.determine_platforms(
            video_id="test_5",
            orientation=Orientation.HORIZONTAL,
            duration=125.0
        )
        
        assert "youtube" in decision.recommended_platforms
        assert len(decision.recommended_platforms) == 1
        assert decision.routing_rule == "horizontal_long_form"
        assert "YouTube main channel" in decision.reasoning
    
    def test_route_horizontal_long_with_channel_preference(self, router):
        """Test horizontal > 60s with YouTube channel preference"""
        decision = router.determine_platforms(
            video_id="test_6",
            orientation=Orientation.HORIZONTAL,
            duration=125.0,
            user_preferences={"default_youtube_channel": "channel_123"}
        )
        
        assert "youtube" in decision.recommended_platforms
        assert decision.youtube_channel_id == "channel_123"
    
    def test_route_square_to_instagram_facebook(self, router):
        """Test square videos route to Instagram Feed and Facebook"""
        decision = router.determine_platforms(
            video_id="test_7",
            orientation=Orientation.SQUARE,
            duration=60.0
        )
        
        assert "instagram_feed" in decision.recommended_platforms
        assert "facebook" in decision.recommended_platforms
        assert decision.routing_rule == "square_format"
    
    def test_manual_override(self, router):
        """Test manual platform override"""
        decision = router.determine_platforms(
            video_id="test_8",
            orientation=Orientation.HORIZONTAL,
            duration=125.0,
            manual_override=["tiktok", "instagram_reels"]
        )
        
        assert "tiktok" in decision.recommended_platforms
        assert "instagram_reels" in decision.recommended_platforms
        assert decision.routing_rule == "manual_override"
        assert decision.auto_routed is False
    
    def test_should_route_to_youtube_true(self, router):
        """Test should_route_to_youtube returns True for horizontal > 60s"""
        result = router.should_route_to_youtube(
            Orientation.HORIZONTAL,
            duration=125.0
        )
        assert result is True
    
    def test_should_route_to_youtube_false_vertical(self, router):
        """Test should_route_to_youtube returns False for vertical"""
        result = router.should_route_to_youtube(
            Orientation.VERTICAL,
            duration=125.0
        )
        assert result is False
    
    def test_should_route_to_youtube_false_short(self, router):
        """Test should_route_to_youtube returns False for short duration"""
        result = router.should_route_to_youtube(
            Orientation.HORIZONTAL,
            duration=45.0
        )
        assert result is False
    
    def test_get_routing_rule_vertical_short(self, router):
        """Test routing rule name for vertical short"""
        rule = router.get_routing_rule_name(Orientation.VERTICAL, 45.0)
        assert rule == "vertical_short_form"
    
    def test_get_routing_rule_vertical_medium(self, router):
        """Test routing rule name for vertical medium"""
        rule = router.get_routing_rule_name(Orientation.VERTICAL, 75.0)
        assert rule == "vertical_medium_form"
    
    def test_get_routing_rule_vertical_long(self, router):
        """Test routing rule name for vertical long"""
        rule = router.get_routing_rule_name(Orientation.VERTICAL, 120.0)
        assert rule == "vertical_long_form"
    
    def test_get_routing_rule_horizontal_short(self, router):
        """Test routing rule name for horizontal short"""
        rule = router.get_routing_rule_name(Orientation.HORIZONTAL, 45.0)
        assert rule == "horizontal_short_form"
    
    def test_get_routing_rule_horizontal_long(self, router):
        """Test routing rule name for horizontal long"""
        rule = router.get_routing_rule_name(Orientation.HORIZONTAL, 125.0)
        assert rule == "horizontal_long_form"
    
    def test_get_routing_rule_square(self, router):
        """Test routing rule name for square"""
        rule = router.get_routing_rule_name(Orientation.SQUARE, 60.0)
        assert rule == "square_format"
    
    def test_alternative_platforms_provided(self, router):
        """Test that alternative platforms are suggested"""
        decision = router.determine_platforms(
            video_id="test_9",
            orientation=Orientation.HORIZONTAL,
            duration=125.0
        )
        
        assert decision.alternative_platforms is not None
        assert "facebook" in decision.alternative_platforms
    
    def test_can_override_flag(self, router):
        """Test that can_override flag is set correctly"""
        decision = router.determine_platforms(
            video_id="test_10",
            orientation=Orientation.HORIZONTAL,
            duration=125.0
        )
        
        assert decision.can_override is True
    
    def test_reasoning_includes_duration(self, router):
        """Test that reasoning includes duration information"""
        decision = router.determine_platforms(
            video_id="test_11",
            orientation=Orientation.HORIZONTAL,
            duration=125.0
        )
        
        assert "60 seconds" in decision.reasoning or "60s" in decision.reasoning
    
    def test_edge_case_exactly_60_seconds_vertical(self, router):
        """Test routing for exactly 60 seconds vertical video"""
        decision = router.determine_platforms(
            video_id="test_12",
            orientation=Orientation.VERTICAL,
            duration=60.0
        )
        
        # Should be treated as medium form (>= 60s)
        assert decision.routing_rule == "vertical_medium_form"
    
    def test_edge_case_exactly_60_seconds_horizontal(self, router):
        """Test routing for exactly 60 seconds horizontal video"""
        decision = router.determine_platforms(
            video_id="test_13",
            orientation=Orientation.HORIZONTAL,
            duration=60.0
        )
        
        # Should be treated as short form (< 60s is False, so >= 60s)
        # Actually, 60.0 is not < 60, so it goes to long form
        assert decision.routing_rule == "horizontal_long_form"
        assert "youtube" in decision.recommended_platforms
    
    def test_very_short_video(self, router):
        """Test routing for very short video (< 10s)"""
        decision = router.determine_platforms(
            video_id="test_14",
            orientation=Orientation.VERTICAL,
            duration=5.0
        )
        
        assert "tiktok" in decision.recommended_platforms
        assert decision.routing_rule == "vertical_short_form"
    
    def test_very_long_video(self, router):
        """Test routing for very long video (> 10 minutes)"""
        decision = router.determine_platforms(
            video_id="test_15",
            orientation=Orientation.HORIZONTAL,
            duration=720.0  # 12 minutes
        )
        
        assert "youtube" in decision.recommended_platforms
        assert decision.routing_rule == "horizontal_long_form"
    
    def test_multiple_videos_batch_routing(self, router):
        """Test routing multiple videos in sequence"""
        videos = [
            ("v1", Orientation.VERTICAL, 30.0),
            ("v2", Orientation.HORIZONTAL, 120.0),
            ("v3", Orientation.SQUARE, 45.0),
        ]
        
        decisions = []
        for video_id, orientation, duration in videos:
            decision = router.determine_platforms(video_id, orientation, duration)
            decisions.append(decision)
        
        assert len(decisions) == 3
        assert "tiktok" in decisions[0].recommended_platforms
        assert "youtube" in decisions[1].recommended_platforms
        assert "instagram_feed" in decisions[2].recommended_platforms


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
