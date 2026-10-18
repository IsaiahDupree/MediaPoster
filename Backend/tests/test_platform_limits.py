"""
Unit Tests for Platform Character Limits

Tests the platform_limits.py configuration module for:
- Correct limit values for each platform
- 20% buffer calculation
- Fallback for unknown platforms
- Helper function behavior
"""

import pytest
from config.platform_limits import (
    get_platform_limits,
    get_all_platforms,
    PLATFORM_LIMITS,
    DEFAULT_PROMPT_SETTINGS,
    PROMPT_TEMPLATES,
    TONE_MODIFIERS,
    STYLE_MODIFIERS,
    PlatformLimits,
)


class TestPlatformLimits:
    """Test platform limit values and calculations"""

    def test_all_major_platforms_defined(self):
        """Ensure all major social platforms have limits defined"""
        required_platforms = [
            'instagram', 'tiktok', 'youtube', 'twitter', 
            'threads', 'pinterest', 'linkedin', 'bluesky', 'facebook'
        ]
        
        for platform in required_platforms:
            assert platform in PLATFORM_LIMITS, f"Missing platform: {platform}"
            limits = PLATFORM_LIMITS[platform]
            assert limits.title_max > 0, f"{platform} title_max should be positive"
            assert limits.description_max > 0, f"{platform} description_max should be positive"

    def test_target_is_80_percent_of_max(self):
        """Verify target values are 80% of max (20% buffer)"""
        for platform, limits in PLATFORM_LIMITS.items():
            if platform in ['x', 'ig', 'fb', 'yt', 'yt_shorts', 'tt', 'li', 'pin', 'bsky']:
                continue  # Skip aliases
            
            expected_title_target = int(limits.title_max * 0.8)
            expected_desc_target = int(limits.description_max * 0.8)
            
            assert limits.title_target == expected_title_target, \
                f"{platform} title_target: expected {expected_title_target}, got {limits.title_target}"
            assert limits.description_target == expected_desc_target, \
                f"{platform} description_target: expected {expected_desc_target}, got {limits.description_target}"

    def test_aliases_point_to_correct_platforms(self):
        """Test that platform aliases work correctly"""
        assert PLATFORM_LIMITS['x'] == PLATFORM_LIMITS['twitter']
        assert PLATFORM_LIMITS['ig'] == PLATFORM_LIMITS['instagram']
        assert PLATFORM_LIMITS['fb'] == PLATFORM_LIMITS['facebook']
        assert PLATFORM_LIMITS['yt'] == PLATFORM_LIMITS['youtube']
        assert PLATFORM_LIMITS['tt'] == PLATFORM_LIMITS['tiktok']
        assert PLATFORM_LIMITS['li'] == PLATFORM_LIMITS['linkedin']
        assert PLATFORM_LIMITS['pin'] == PLATFORM_LIMITS['pinterest']
        assert PLATFORM_LIMITS['bsky'] == PLATFORM_LIMITS['bluesky']

    def test_instagram_limits(self):
        """Test Instagram specific limits"""
        limits = get_platform_limits('instagram')
        assert limits.title_max == 100
        assert limits.description_max == 2200  # Instagram caption limit
        assert limits.hashtags_max == 30
        assert limits.hashtags_recommended == 5

    def test_tiktok_limits(self):
        """Test TikTok specific limits"""
        limits = get_platform_limits('tiktok')
        assert limits.title_max == 100
        assert limits.description_max == 4000  # Updated TikTok limit
        assert limits.hashtags_recommended == 5

    def test_twitter_limits(self):
        """Test Twitter/X specific limits"""
        limits = get_platform_limits('twitter')
        assert limits.title_max == 280
        assert limits.description_max == 280  # Tweet length
        assert limits.hashtags_recommended == 2

    def test_youtube_limits(self):
        """Test YouTube specific limits"""
        limits = get_platform_limits('youtube')
        assert limits.title_max == 100
        assert limits.description_max == 5000

    def test_threads_limits(self):
        """Test Threads specific limits"""
        limits = get_platform_limits('threads')
        assert limits.title_max == 500
        assert limits.description_max == 500

    def test_pinterest_limits(self):
        """Test Pinterest specific limits"""
        limits = get_platform_limits('pinterest')
        assert limits.title_max == 100
        assert limits.description_max == 500

    def test_linkedin_limits(self):
        """Test LinkedIn specific limits"""
        limits = get_platform_limits('linkedin')
        assert limits.title_max == 100
        assert limits.description_max == 3000

    def test_bluesky_limits(self):
        """Test Bluesky specific limits"""
        limits = get_platform_limits('bluesky')
        assert limits.title_max == 300
        assert limits.description_max == 300


class TestGetPlatformLimits:
    """Test the get_platform_limits helper function"""

    def test_returns_correct_platform(self):
        """Test that function returns correct limits for known platforms"""
        limits = get_platform_limits('instagram')
        assert limits.platform == 'instagram'

    def test_case_insensitive(self):
        """Test that platform lookup is case-insensitive"""
        lower = get_platform_limits('instagram')
        upper = get_platform_limits('INSTAGRAM')
        mixed = get_platform_limits('InStAgRaM')
        
        assert lower.title_max == upper.title_max == mixed.title_max

    def test_strips_whitespace(self):
        """Test that whitespace is stripped from platform name"""
        with_space = get_platform_limits('  instagram  ')
        without_space = get_platform_limits('instagram')
        
        assert with_space.title_max == without_space.title_max

    def test_unknown_platform_returns_fallback(self):
        """Test that unknown platforms get conservative fallback limits"""
        limits = get_platform_limits('unknown_platform_xyz')
        
        assert limits.title_max == 100
        assert limits.description_max == 500
        assert limits.hashtags_max == 10


class TestGetAllPlatforms:
    """Test the get_all_platforms helper function"""

    def test_returns_dict(self):
        """Test that function returns a dictionary"""
        platforms = get_all_platforms()
        assert isinstance(platforms, dict)

    def test_excludes_aliases(self):
        """Test that aliases are excluded from the result"""
        platforms = get_all_platforms()
        
        # Aliases should not be present
        assert 'x' not in platforms
        assert 'ig' not in platforms
        assert 'fb' not in platforms
        
        # But main platforms should be
        assert 'twitter' in platforms
        assert 'instagram' in platforms
        assert 'facebook' in platforms

    def test_returns_platform_limits_objects(self):
        """Test that values are PlatformLimits instances"""
        platforms = get_all_platforms()
        
        for name, limits in platforms.items():
            assert isinstance(limits, PlatformLimits)


class TestPlatformLimitsDataclass:
    """Test the PlatformLimits dataclass"""

    def test_from_max_calculates_targets(self):
        """Test that from_max classmethod calculates targets correctly"""
        limits = PlatformLimits.from_max(
            platform="test",
            title_max=100,
            description_max=1000,
            hashtags_max=10,
            hashtags_recommended=5
        )
        
        assert limits.title_target == 80  # 80% of 100
        assert limits.description_target == 800  # 80% of 1000

    def test_optional_fields(self):
        """Test that optional fields default to None"""
        limits = PlatformLimits.from_max(
            platform="test",
            title_max=100,
            description_max=1000
        )
        
        assert limits.bio_max is None
        assert limits.comment_max is None


class TestPromptSettings:
    """Test prompt generation settings"""

    def test_default_settings_exist(self):
        """Test that default settings are defined"""
        assert 'voice' in DEFAULT_PROMPT_SETTINGS
        assert 'tone' in DEFAULT_PROMPT_SETTINGS
        assert 'style' in DEFAULT_PROMPT_SETTINGS
        assert 'emoji_usage' in DEFAULT_PROMPT_SETTINGS

    def test_prompt_templates_exist(self):
        """Test that prompt templates are defined"""
        assert 'conversational' in PROMPT_TEMPLATES
        assert 'professional' in PROMPT_TEMPLATES
        assert 'casual' in PROMPT_TEMPLATES
        assert 'humorous' in PROMPT_TEMPLATES

    def test_tone_modifiers_exist(self):
        """Test that tone modifiers are defined"""
        assert 'engaging' in TONE_MODIFIERS
        assert 'informative' in TONE_MODIFIERS
        assert 'persuasive' in TONE_MODIFIERS

    def test_style_modifiers_exist(self):
        """Test that style modifiers are defined"""
        assert 'concise' in STYLE_MODIFIERS
        assert 'detailed' in STYLE_MODIFIERS
        assert 'storytelling' in STYLE_MODIFIERS


class TestCharacterLimitEnforcement:
    """Test that limits are reasonable for content creation"""

    def test_title_limits_allow_meaningful_content(self):
        """Ensure title limits allow for meaningful titles"""
        for platform, limits in PLATFORM_LIMITS.items():
            if platform in ['x', 'ig', 'fb', 'yt', 'yt_shorts', 'tt', 'li', 'pin', 'bsky']:
                continue
            
            # Minimum 50 chars for a meaningful title
            assert limits.title_target >= 50, \
                f"{platform} title_target ({limits.title_target}) is too restrictive"

    def test_description_limits_allow_meaningful_content(self):
        """Ensure description limits allow for meaningful descriptions"""
        for platform, limits in PLATFORM_LIMITS.items():
            if platform in ['x', 'ig', 'fb', 'yt', 'yt_shorts', 'tt', 'li', 'pin', 'bsky']:
                continue
            
            # Minimum 100 chars for a meaningful description (except Twitter)
            if platform not in ['twitter', 'bluesky']:
                assert limits.description_target >= 100, \
                    f"{platform} description_target ({limits.description_target}) is too restrictive"

    def test_hashtag_recommendations_are_reasonable(self):
        """Ensure hashtag recommendations are reasonable"""
        for platform, limits in PLATFORM_LIMITS.items():
            if platform in ['x', 'ig', 'fb', 'yt', 'yt_shorts', 'tt', 'li', 'pin', 'bsky']:
                continue
            
            # Recommended should be less than or equal to max
            assert limits.hashtags_recommended <= limits.hashtags_max, \
                f"{platform} hashtags_recommended > hashtags_max"
            
            # Recommended should be at least 2
            assert limits.hashtags_recommended >= 2, \
                f"{platform} hashtags_recommended is too low"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
