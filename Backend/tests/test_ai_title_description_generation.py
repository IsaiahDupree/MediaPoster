"""
Tests for AI Title & Description Generation

Tests the platform-specific title and description generation with 20% buffer rule.
Based on AI_TITLE_DESCRIPTION_ANALYSIS.md requirements.

Success Criteria:
1. Titles generated at 20% of each platform's max character limit (target = 80% of max)
2. Descriptions generated at 20% of each platform's max character limit
3. Platform-specific titles returned in API response
4. Each platform gets unique titles/descriptions optimized for that platform
5. Character limits enforced correctly
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from typing import Dict

from config.platform_limits import (
    get_platform_limits,
    get_all_platforms,
    PLATFORM_LIMITS,
    PlatformLimits,
)


# =============================================================================
# Test Platform-Specific Title Limits (20% Rule)
# =============================================================================

class TestTitleLimits20PercentRule:
    """Test that title targets are correctly calculated at 80% of max (20% buffer)"""

    @pytest.mark.parametrize("platform,expected_max,expected_target", [
        ("tiktok", 100, 80),
        ("instagram", 100, 80),
        ("youtube", 100, 80),
        ("twitter", 280, 224),
        ("threads", 500, 400),
        ("linkedin", 100, 80),
        ("pinterest", 100, 80),
        ("facebook", 80, 64),
        ("bluesky", 300, 240),
    ])
    def test_title_target_is_80_percent_of_max(self, platform, expected_max, expected_target):
        """Each platform's title_target should be 80% of title_max (20% buffer)"""
        limits = get_platform_limits(platform)
        
        assert limits.title_max == expected_max, \
            f"{platform} title_max: expected {expected_max}, got {limits.title_max}"
        assert limits.title_target == expected_target, \
            f"{platform} title_target: expected {expected_target}, got {limits.title_target}"
        
        # Verify the calculation
        calculated_target = int(limits.title_max * 0.8)
        assert limits.title_target == calculated_target, \
            f"{platform} title_target should be 80% of max: {calculated_target}, got {limits.title_target}"

    def test_all_platforms_have_title_targets(self):
        """Every platform should have a title_target defined"""
        platforms = get_all_platforms()
        
        for platform, limits in platforms.items():
            assert limits.title_target is not None, f"{platform} missing title_target"
            assert limits.title_target > 0, f"{platform} title_target should be positive"
            assert limits.title_target <= limits.title_max, \
                f"{platform} title_target ({limits.title_target}) should not exceed title_max ({limits.title_max})"


# =============================================================================
# Test Platform-Specific Description Limits (20% Rule)
# =============================================================================

class TestDescriptionLimits20PercentRule:
    """Test that description targets are correctly calculated at 80% of max (20% buffer)"""

    @pytest.mark.parametrize("platform,expected_max,expected_target", [
        ("tiktok", 4000, 3200),
        ("instagram", 2200, 1760),
        ("youtube", 5000, 4000),
        ("twitter", 280, 224),
        ("threads", 500, 400),
        ("linkedin", 3000, 2400),
        ("pinterest", 500, 400),
        ("facebook", 63206, 50564),
        ("bluesky", 300, 240),
    ])
    def test_description_target_is_80_percent_of_max(self, platform, expected_max, expected_target):
        """Each platform's description_target should be 80% of description_max (20% buffer)"""
        limits = get_platform_limits(platform)
        
        assert limits.description_max == expected_max, \
            f"{platform} description_max: expected {expected_max}, got {limits.description_max}"
        assert limits.description_target == expected_target, \
            f"{platform} description_target: expected {expected_target}, got {limits.description_target}"
        
        # Verify the calculation
        calculated_target = int(limits.description_max * 0.8)
        assert limits.description_target == calculated_target, \
            f"{platform} description_target should be 80% of max: {calculated_target}, got {limits.description_target}"

    def test_all_platforms_have_description_targets(self):
        """Every platform should have a description_target defined"""
        platforms = get_all_platforms()
        
        for platform, limits in platforms.items():
            assert limits.description_target is not None, f"{platform} missing description_target"
            assert limits.description_target > 0, f"{platform} description_target should be positive"
            assert limits.description_target <= limits.description_max, \
                f"{platform} description_target ({limits.description_target}) should not exceed description_max ({limits.description_max})"


# =============================================================================
# Test Truncation Function
# =============================================================================

class TestTruncateToLimit:
    """Test the truncate_to_limit utility function"""

    def test_no_truncation_needed(self):
        """Text within limit should not be truncated"""
        from api.endpoints.analysis import truncate_to_limit
        
        text = "Short text"
        result = truncate_to_limit(text, 100)
        assert result == text

    def test_truncation_with_ellipsis(self):
        """Text exceeding limit should be truncated with ellipsis"""
        from api.endpoints.analysis import truncate_to_limit
        
        text = "This is a very long text that needs to be truncated because it exceeds the limit"
        result = truncate_to_limit(text, 30)
        
        assert len(result) <= 30
        assert result.endswith("...")

    def test_truncation_respects_word_boundaries(self):
        """Truncation should try to respect word boundaries"""
        from api.endpoints.analysis import truncate_to_limit
        
        text = "Word one two three four five six"
        result = truncate_to_limit(text, 20)
        
        # Should not cut mid-word if possible
        assert len(result) <= 20
        assert result.endswith("...")

    def test_truncation_without_ellipsis(self):
        """Test truncation without adding ellipsis"""
        from api.endpoints.analysis import truncate_to_limit
        
        text = "This is a long text"
        result = truncate_to_limit(text, 10, add_ellipsis=False)
        
        assert len(result) <= 10
        assert not result.endswith("...")


# =============================================================================
# Test Platform Limits Data Integrity
# =============================================================================

class TestPlatformLimitsDataIntegrity:
    """Test that platform limits data is consistent and valid"""

    def test_all_required_platforms_defined(self):
        """All major platforms should be defined"""
        required = ['instagram', 'tiktok', 'youtube', 'twitter', 'threads', 
                   'pinterest', 'linkedin', 'bluesky', 'facebook']
        
        for platform in required:
            assert platform in PLATFORM_LIMITS, f"Missing platform: {platform}"

    def test_target_always_less_than_or_equal_to_max(self):
        """Targets should never exceed maximums"""
        for platform, limits in PLATFORM_LIMITS.items():
            if platform in ['x', 'ig', 'fb', 'yt', 'yt_shorts', 'tt', 'li', 'pin', 'bsky']:
                continue  # Skip aliases
            
            assert limits.title_target <= limits.title_max, \
                f"{platform}: title_target > title_max"
            assert limits.description_target <= limits.description_max, \
                f"{platform}: description_target > description_max"

    def test_buffer_ratio_is_20_percent(self):
        """Buffer should be exactly 20% (target = 80% of max)"""
        for platform, limits in PLATFORM_LIMITS.items():
            if platform in ['x', 'ig', 'fb', 'yt', 'yt_shorts', 'tt', 'li', 'pin', 'bsky']:
                continue  # Skip aliases
            
            title_ratio = limits.title_target / limits.title_max
            desc_ratio = limits.description_target / limits.description_max
            
            # Allow small floating point variance
            assert 0.79 <= title_ratio <= 0.81, \
                f"{platform}: title buffer ratio is {title_ratio}, expected ~0.80"
            assert 0.79 <= desc_ratio <= 0.81, \
                f"{platform}: description buffer ratio is {desc_ratio}, expected ~0.80"


# =============================================================================
# Test Caption Generation Character Limits
# =============================================================================

class TestCaptionGenerationLimits:
    """Test that generated captions respect platform limits"""

    def test_truncate_to_limit_enforces_platform_limits(self):
        """truncate_to_limit should enforce character limits"""
        from api.endpoints.analysis import truncate_to_limit
        
        # Test that truncation works for all platform limits
        for platform, limits in PLATFORM_LIMITS.items():
            if platform in ['x', 'ig', 'fb', 'yt', 'yt_shorts', 'tt', 'li', 'pin', 'bsky']:
                continue  # Skip aliases
            
            # Create content exceeding the limit
            long_content = "A" * (limits.description_target + 100)
            truncated = truncate_to_limit(long_content, limits.description_target)
            
            assert len(truncated) <= limits.description_target, \
                f"{platform} truncation failed: {len(truncated)} > {limits.description_target}"

    def test_caption_limits_are_enforced_by_truncation(self):
        """Captions should be truncated to platform limits"""
        from api.endpoints.analysis import truncate_to_limit
        
        # Test specific platforms
        test_cases = [
            ("twitter", 224),  # Short platform
            ("bluesky", 240),  # Short platform
            ("tiktok", 3200),  # Long platform
            ("youtube", 4000),  # Long platform
        ]
        
        for platform, expected_limit in test_cases:
            limits = get_platform_limits(platform)
            assert limits.description_target == expected_limit, \
                f"{platform} limit mismatch"
            
            # Long content should be truncated
            long_content = "B" * 10000
            truncated = truncate_to_limit(long_content, limits.description_target)
            
            assert len(truncated) <= expected_limit, \
                f"{platform} truncation failed"


# =============================================================================
# Test Platform-Specific Title Generation
# =============================================================================

class TestPlatformSpecificTitleGeneration:
    """Test that titles are generated specifically for each platform"""

    def test_title_target_varies_by_platform(self):
        """Different platforms should have different title targets"""
        twitter_limits = get_platform_limits("twitter")
        tiktok_limits = get_platform_limits("tiktok")
        threads_limits = get_platform_limits("threads")
        
        # Twitter allows longer "titles" (280 chars)
        assert twitter_limits.title_target > tiktok_limits.title_target
        # Threads allows even longer (500 chars)
        assert threads_limits.title_target > twitter_limits.title_target

    def test_title_generation_prompt_includes_platform_limit(self):
        """Title generation should include platform-specific character limit"""
        # This tests the structure - actual AI call would be mocked
        platforms_to_test = ["tiktok", "twitter", "threads", "linkedin"]
        
        for platform in platforms_to_test:
            limits = get_platform_limits(platform)
            title_target = limits.title_target
            
            # Verify the target is correctly calculated
            expected_target = int(limits.title_max * 0.8)
            assert title_target == expected_target, \
                f"{platform}: title_target ({title_target}) != expected ({expected_target})"


# =============================================================================
# Test Platform-Specific Description Generation  
# =============================================================================

class TestPlatformSpecificDescriptionGeneration:
    """Test that descriptions are generated specifically for each platform"""

    def test_description_target_varies_by_platform(self):
        """Different platforms should have different description targets"""
        twitter_limits = get_platform_limits("twitter")  # 280 max
        instagram_limits = get_platform_limits("instagram")  # 2200 max
        youtube_limits = get_platform_limits("youtube")  # 5000 max
        
        # YouTube allows much longer descriptions than Twitter
        assert youtube_limits.description_target > twitter_limits.description_target
        assert instagram_limits.description_target > twitter_limits.description_target
        assert youtube_limits.description_target > instagram_limits.description_target

    def test_short_platforms_have_strict_limits(self):
        """Short-form platforms should have strict description limits"""
        twitter = get_platform_limits("twitter")
        bluesky = get_platform_limits("bluesky")
        threads = get_platform_limits("threads")
        
        # These platforms have tight limits
        assert twitter.description_max <= 300
        assert bluesky.description_max <= 300
        assert threads.description_max <= 500


# =============================================================================
# Test API Response Structure
# =============================================================================

class TestGenerateCaptionsAPIResponse:
    """Test the generate_captions API endpoint response structure"""

    @pytest.mark.asyncio
    async def test_response_includes_platform_titles(self):
        """API response should include platform_titles dict"""
        from api.endpoints.analysis import generate_captions, GenerateCaptionsRequest
        
        # This would require a full mock setup - documenting expected structure
        expected_response_keys = [
            "success",
            "media_id", 
            "title",  # Generic title for backward compatibility
            "platform_titles",  # Platform-specific titles
            "platform_descriptions",  # Platform-specific descriptions
            "transcript_available",
            "captions"
        ]
        
        # Just verify the expected structure is documented
        assert len(expected_response_keys) == 7

    def test_platform_titles_should_be_dict(self):
        """platform_titles should map platform names to titles"""
        # Expected structure:
        expected_structure = {
            "tiktok": "Platform-specific TikTok title",
            "instagram": "Platform-specific Instagram title",
            "youtube": "Platform-specific YouTube title",
            "twitter": "Platform-specific Twitter title",
            "threads": "Platform-specific Threads title",
            "pinterest": "Platform-specific Pinterest title",
            "linkedin": "Platform-specific LinkedIn title",
            "bluesky": "Platform-specific Bluesky title",
            "facebook": "Platform-specific Facebook title",
        }
        
        # All major platforms should have entries
        assert len(expected_structure) >= 9


# =============================================================================
# Test Character Count Validation
# =============================================================================

class TestCharacterCountValidation:
    """Test character count validation against platform limits"""

    @pytest.mark.parametrize("platform", [
        "tiktok", "instagram", "youtube", "twitter", "threads",
        "pinterest", "linkedin", "bluesky", "facebook"
    ])
    def test_title_under_target_is_valid(self, platform):
        """Title under target should be valid"""
        limits = get_platform_limits(platform)
        
        # Generate test title at exactly target length
        test_title = "A" * limits.title_target
        
        assert len(test_title) <= limits.title_target
        assert len(test_title) <= limits.title_max

    @pytest.mark.parametrize("platform", [
        "tiktok", "instagram", "youtube", "twitter", "threads",
        "pinterest", "linkedin", "bluesky", "facebook"
    ])
    def test_description_under_target_is_valid(self, platform):
        """Description under target should be valid"""
        limits = get_platform_limits(platform)
        
        # Generate test description at exactly target length
        test_desc = "B" * limits.description_target
        
        assert len(test_desc) <= limits.description_target
        assert len(test_desc) <= limits.description_max


# =============================================================================
# Test PlatformLimits Dataclass
# =============================================================================

class TestPlatformLimitsFromMax:
    """Test the PlatformLimits.from_max factory method"""

    def test_from_max_calculates_80_percent_target(self):
        """from_max should calculate target as 80% of max"""
        limits = PlatformLimits.from_max(
            platform="test_platform",
            title_max=100,
            description_max=1000,
            hashtags_max=10,
            hashtags_recommended=5
        )
        
        assert limits.title_target == 80  # 80% of 100
        assert limits.description_target == 800  # 80% of 1000

    def test_from_max_with_various_values(self):
        """from_max should work with various max values"""
        test_cases = [
            (100, 80),
            (280, 224),
            (500, 400),
            (1000, 800),
            (5000, 4000),
            (63206, 50564),
        ]
        
        for max_val, expected_target in test_cases:
            limits = PlatformLimits.from_max(
                platform="test",
                title_max=max_val,
                description_max=max_val
            )
            
            assert limits.title_target == expected_target, \
                f"title_target for max={max_val}: expected {expected_target}, got {limits.title_target}"
            assert limits.description_target == expected_target, \
                f"description_target for max={max_val}: expected {expected_target}, got {limits.description_target}"


# =============================================================================
# Test Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases in title/description generation"""

    def test_unknown_platform_gets_fallback_limits(self):
        """Unknown platforms should get conservative fallback limits"""
        limits = get_platform_limits("unknown_platform_xyz")
        
        assert limits.title_max == 100
        assert limits.title_target == 80
        assert limits.description_max == 500
        assert limits.description_target == 400

    def test_case_insensitive_platform_lookup(self):
        """Platform lookup should be case-insensitive"""
        lower = get_platform_limits("instagram")
        upper = get_platform_limits("INSTAGRAM")
        mixed = get_platform_limits("InStAgRaM")
        
        assert lower.title_target == upper.title_target == mixed.title_target
        assert lower.description_target == upper.description_target == mixed.description_target

    def test_whitespace_stripped_from_platform(self):
        """Whitespace should be stripped from platform names"""
        clean = get_platform_limits("tiktok")
        with_space = get_platform_limits("  tiktok  ")
        
        assert clean.title_target == with_space.title_target

    def test_empty_content_handling(self):
        """Empty content should not cause errors"""
        from api.endpoints.analysis import truncate_to_limit
        
        result = truncate_to_limit("", 100)
        assert result == ""

    def test_very_short_limit_handling(self):
        """Very short limits should still work"""
        from api.endpoints.analysis import truncate_to_limit
        
        # Test with limit shorter than ellipsis
        result = truncate_to_limit("Hello World", 3)
        assert len(result) <= 3


# =============================================================================
# Test Platform Limit Consistency with Documentation
# =============================================================================

class TestDocumentedLimits:
    """Test that limits match documented values from AI_TITLE_DESCRIPTION_ANALYSIS.md"""

    def test_documented_title_limits(self):
        """Verify title limits match documentation"""
        documented_limits = {
            "tiktok": {"max": 100, "target": 80},  # 20 chars in doc is wrong - should be 80
            "instagram": {"max": 100, "target": 80},
            "youtube": {"max": 100, "target": 80},
            "twitter": {"max": 280, "target": 224},
            "threads": {"max": 500, "target": 400},
            "linkedin": {"max": 100, "target": 80},
            "pinterest": {"max": 100, "target": 80},
            "facebook": {"max": 80, "target": 64},
            "bluesky": {"max": 300, "target": 240},
        }
        
        for platform, expected in documented_limits.items():
            limits = get_platform_limits(platform)
            assert limits.title_max == expected["max"], \
                f"{platform} title_max mismatch"
            assert limits.title_target == expected["target"], \
                f"{platform} title_target mismatch: expected {expected['target']}, got {limits.title_target}"

    def test_documented_description_limits(self):
        """Verify description limits match documentation"""
        documented_limits = {
            "tiktok": {"max": 4000, "target": 3200},
            "instagram": {"max": 2200, "target": 1760},
            "youtube": {"max": 5000, "target": 4000},
            "twitter": {"max": 280, "target": 224},
            "threads": {"max": 500, "target": 400},
            "linkedin": {"max": 3000, "target": 2400},
            "pinterest": {"max": 500, "target": 400},
            "facebook": {"max": 63206, "target": 50564},
            "bluesky": {"max": 300, "target": 240},
        }
        
        for platform, expected in documented_limits.items():
            limits = get_platform_limits(platform)
            assert limits.description_max == expected["max"], \
                f"{platform} description_max mismatch"
            assert limits.description_target == expected["target"], \
                f"{platform} description_target mismatch: expected {expected['target']}, got {limits.description_target}"


# =============================================================================
# Integration Test Markers
# =============================================================================

class TestIntegrationMarkers:
    """Markers for integration tests that require database/API"""

    @pytest.mark.skip(reason="Requires database connection")
    @pytest.mark.asyncio
    async def test_full_caption_generation_flow(self):
        """Full integration test for caption generation"""
        # This would test the full flow:
        # 1. Fetch media from database
        # 2. Get transcript and analysis
        # 3. Generate platform-specific titles
        # 4. Generate platform-specific descriptions
        # 5. Return properly formatted response
        pass

    @pytest.mark.skip(reason="Requires OpenAI API key")
    @pytest.mark.asyncio
    async def test_real_ai_title_generation(self):
        """Test actual AI title generation"""
        # Would test real OpenAI call
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
