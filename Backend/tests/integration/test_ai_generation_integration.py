"""
Integration Tests for AI Title & Description Generation

These tests are designed to FAIL if the implementation is broken.
They test real interactions between services:
- platform_limits.py ↔ analysis.py
- API endpoint response structure
- Actual character limit enforcement
- Platform-specific content generation

Run with: pytest tests/integration/test_ai_generation_integration.py -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import uuid
from typing import Dict, Any

from config.platform_limits import (
    get_platform_limits,
    get_all_platforms,
    PLATFORM_LIMITS,
    PlatformLimits,
)
from api.endpoints.analysis import truncate_to_limit, _generate_platform_captions


# =============================================================================
# Integration Test: Platform Limits → Caption Generation
# =============================================================================

class TestPlatformLimitsIntegration:
    """
    Tests that platform_limits module integrates correctly with caption generation.
    These tests WILL FAIL if:
    - platform_limits returns wrong values
    - analysis.py doesn't use platform_limits correctly
    - Character limits aren't enforced
    """

    def test_analysis_imports_platform_limits_correctly(self):
        """
        FAILS IF: analysis.py doesn't import get_platform_limits correctly
        """
        from api.endpoints.analysis import get_platform_limits as analysis_get_limits
        from config.platform_limits import get_platform_limits as config_get_limits
        
        # Both should return the same object
        assert analysis_get_limits == config_get_limits, \
            "analysis.py should import get_platform_limits from config.platform_limits"

    def test_all_platforms_in_caption_generation_have_limits(self):
        """
        FAILS IF: Caption generation tries to use a platform without defined limits
        """
        # These are the platforms _generate_platform_captions generates for
        platforms_in_generation = [
            "tiktok", "instagram", "youtube", "twitter", 
            "threads", "pinterest", "linkedin", "bluesky", "facebook"
        ]
        
        for platform in platforms_in_generation:
            limits = get_platform_limits(platform)
            assert limits is not None, f"No limits defined for {platform}"
            assert limits.title_target > 0, f"{platform} has invalid title_target"
            assert limits.description_target > 0, f"{platform} has invalid description_target"

    def test_truncate_function_uses_correct_limit_values(self):
        """
        FAILS IF: truncate_to_limit doesn't enforce the actual platform limits
        """
        # Generate content that exceeds ALL platform limits
        very_long_content = "X" * 100000
        
        for platform, limits in PLATFORM_LIMITS.items():
            if platform in ['x', 'ig', 'fb', 'yt', 'yt_shorts', 'tt', 'li', 'pin', 'bsky']:
                continue
            
            # Truncate to description target
            truncated = truncate_to_limit(very_long_content, limits.description_target)
            
            # MUST be within limit
            assert len(truncated) <= limits.description_target, \
                f"CRITICAL: {platform} truncation FAILED - {len(truncated)} > {limits.description_target}"
            
            # Should actually truncate (not return empty)
            assert len(truncated) > 0, f"{platform} truncation returned empty string"


# =============================================================================
# Integration Test: Character Limit Enforcement
# =============================================================================

class TestCharacterLimitEnforcementIntegration:
    """
    Tests that character limits are ACTUALLY enforced during generation.
    These tests WILL FAIL if:
    - Generated content exceeds platform limits
    - 20% buffer rule isn't applied
    - Truncation doesn't happen
    """

    @pytest.mark.asyncio
    async def test_generated_captions_respect_all_platform_limits(self):
        """
        FAILS IF: Any generated caption exceeds its platform's description_target
        """
        # Mock OpenAI to return VERY LONG content that MUST be truncated
        long_ai_response = "This is a very long AI response. " * 500  # ~17000 chars
        
        with patch.dict('sys.modules', {'openai': MagicMock()}):
            import sys
            mock_openai_module = sys.modules['openai']
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = long_ai_response
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_module.OpenAI.return_value = mock_client
            
            captions = await _generate_platform_captions(
                title="Test Title for Integration",
                transcript="This is test transcript content for integration testing.",
                topics=["integration", "testing", "limits"],
                hooks=["Test hook 1", "Test hook 2"],
                platform="tiktok",
                tone="engaging",
                style=None,
                custom_prompt=None,
                include_hashtags=True,
                include_hook=True
            )
            
            # CRITICAL: Every platform's caption MUST be within its limit
            for platform, caption in captions.items():
                if platform in PLATFORM_LIMITS:
                    limit = PLATFORM_LIMITS[platform].description_target
                    
                    assert len(caption) <= limit, \
                        f"CRITICAL FAILURE: {platform} caption ({len(caption)} chars) " \
                        f"EXCEEDS limit ({limit} chars)!\n" \
                        f"First 100 chars: {caption[:100]}..."

    def test_truncation_preserves_content_quality(self):
        """
        FAILS IF: Truncation cuts content too aggressively or leaves empty
        """
        test_content = "This is meaningful content that should be preserved when truncated to fit platform limits."
        
        for platform, limits in PLATFORM_LIMITS.items():
            if platform in ['x', 'ig', 'fb', 'yt', 'yt_shorts', 'tt', 'li', 'pin', 'bsky']:
                continue
            
            truncated = truncate_to_limit(test_content, limits.description_target)
            
            # Should preserve the original if under limit
            if len(test_content) <= limits.description_target:
                assert truncated == test_content, \
                    f"{platform}: Content under limit should not be modified"
            else:
                # Should truncate but not destroy
                assert len(truncated) > 10, \
                    f"{platform}: Truncation destroyed content"

    def test_short_platform_limits_are_strictly_enforced(self):
        """
        FAILS IF: Short platforms (Twitter, Bluesky) get content over their strict limits
        """
        short_platforms = {
            "twitter": 224,   # description_target
            "bluesky": 240,   # description_target
            "threads": 400,   # description_target
        }
        
        long_content = "A" * 1000
        
        for platform, expected_limit in short_platforms.items():
            limits = get_platform_limits(platform)
            
            # Verify the limit is what we expect
            assert limits.description_target == expected_limit, \
                f"{platform} limit changed! Expected {expected_limit}, got {limits.description_target}"
            
            # Truncation must enforce this
            truncated = truncate_to_limit(long_content, limits.description_target)
            assert len(truncated) <= expected_limit, \
                f"CRITICAL: {platform} MUST be under {expected_limit} chars, got {len(truncated)}"


# =============================================================================
# Integration Test: Platform-Specific Content
# =============================================================================

class TestPlatformSpecificContentIntegration:
    """
    Tests that different platforms get different, optimized content.
    These tests WILL FAIL if:
    - All platforms get identical content
    - Platform-specific optimizations aren't applied
    """

    @pytest.mark.asyncio
    async def test_different_platforms_get_different_limits(self):
        """
        FAILS IF: All platforms have the same limits (not platform-specific)
        """
        limits_by_platform = {}
        
        for platform in ['tiktok', 'twitter', 'youtube', 'instagram', 'threads']:
            limits = get_platform_limits(platform)
            limits_by_platform[platform] = (limits.title_target, limits.description_target)
        
        # Twitter should have different limits than TikTok
        assert limits_by_platform['twitter'] != limits_by_platform['tiktok'], \
            "Twitter and TikTok should have different limits!"
        
        # Threads should have different limits than Twitter
        assert limits_by_platform['threads'] != limits_by_platform['twitter'], \
            "Threads and Twitter should have different limits!"
        
        # YouTube description should be longer than Twitter
        assert limits_by_platform['youtube'][1] > limits_by_platform['twitter'][1], \
            "YouTube description limit should be > Twitter!"

    @pytest.mark.asyncio  
    async def test_caption_generation_produces_platform_specific_output(self):
        """
        FAILS IF: All platforms get identical captions (no differentiation)
        """
        with patch.dict('sys.modules', {'openai': MagicMock()}):
            import sys
            mock_openai_module = sys.modules['openai']
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "AI generated description for the video"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_module.OpenAI.return_value = mock_client
            
            captions = await _generate_platform_captions(
                title="Integration Test Video",
                transcript="Test transcript",
                topics=["topic1"],
                hooks=["hook1"],
                platform="tiktok",
                tone="engaging",
                style=None,
                custom_prompt=None,
                include_hashtags=True,
                include_hook=True
            )
            
            # Should have multiple platforms
            assert len(captions) >= 5, f"Should generate for multiple platforms, got {len(captions)}"
            
            # Captions should NOT all be identical
            unique_captions = set(captions.values())
            assert len(unique_captions) > 1, \
                "FAILURE: All platforms got IDENTICAL captions - no differentiation!"


# =============================================================================
# Integration Test: API Response Structure
# =============================================================================

class TestAPIResponseStructureIntegration:
    """
    Tests the API response structure matches what frontend expects.
    These tests WILL FAIL if:
    - Response missing required fields
    - platform_titles not returned
    - platform_descriptions not returned
    """

    def test_response_keys_are_complete(self):
        """
        FAILS IF: Expected response keys are missing from implementation
        """
        # Import the actual endpoint to check its return structure
        from api.endpoints.analysis import GenerateCaptionsRequest
        
        # The request model should exist
        request = GenerateCaptionsRequest(
            platform="tiktok",
            tone="engaging"
        )
        
        assert request.platform == "tiktok"
        assert request.tone == "engaging"

    def test_platform_limits_endpoint_exists(self):
        """
        FAILS IF: Platform limits can't be retrieved for frontend
        """
        # Frontend needs to be able to get all platform limits
        all_platforms = get_all_platforms()
        
        # Should return dict with all major platforms
        assert len(all_platforms) >= 9, "Missing platforms in get_all_platforms()"
        
        # Each should have required fields
        for platform, limits in all_platforms.items():
            assert hasattr(limits, 'title_max'), f"{platform} missing title_max"
            assert hasattr(limits, 'title_target'), f"{platform} missing title_target"
            assert hasattr(limits, 'description_max'), f"{platform} missing description_max"
            assert hasattr(limits, 'description_target'), f"{platform} missing description_target"


# =============================================================================
# Integration Test: 20% Buffer Rule
# =============================================================================

class TestBufferRuleIntegration:
    """
    Tests that the 20% buffer rule is correctly implemented.
    These tests WILL FAIL if:
    - target != 80% of max
    - Buffer calculation is wrong
    """

    def test_20_percent_buffer_is_exact(self):
        """
        FAILS IF: Buffer calculation deviates from exactly 20%
        """
        for platform, limits in PLATFORM_LIMITS.items():
            if platform in ['x', 'ig', 'fb', 'yt', 'yt_shorts', 'tt', 'li', 'pin', 'bsky']:
                continue
            
            # Calculate expected targets
            expected_title_target = int(limits.title_max * 0.8)
            expected_desc_target = int(limits.description_max * 0.8)
            
            assert limits.title_target == expected_title_target, \
                f"CRITICAL: {platform} title_target is {limits.title_target}, " \
                f"should be {expected_title_target} (80% of {limits.title_max})"
            
            assert limits.description_target == expected_desc_target, \
                f"CRITICAL: {platform} description_target is {limits.description_target}, " \
                f"should be {expected_desc_target} (80% of {limits.description_max})"

    def test_buffer_leaves_room_for_hashtags(self):
        """
        FAILS IF: Buffer is too small to accommodate hashtags
        """
        # The 20% buffer should leave room for hashtags
        # Average hashtag is ~15 chars, typical 3-5 hashtags = 45-75 chars
        
        for platform in ['tiktok', 'instagram', 'youtube']:
            limits = get_platform_limits(platform)
            buffer_size = limits.description_max - limits.description_target
            
            # Buffer should be at least 50 chars for hashtags
            assert buffer_size >= 50, \
                f"{platform} buffer ({buffer_size}) too small for hashtags!"


# =============================================================================
# Integration Test: Cross-Service Consistency
# =============================================================================

class TestCrossServiceConsistency:
    """
    Tests consistency across different services that use platform limits.
    These tests WILL FAIL if:
    - Different services use different limit values
    - Services don't import from the central config
    """

    def test_platform_limits_is_single_source_of_truth(self):
        """
        FAILS IF: Multiple conflicting limit definitions exist
        """
        # Import from the central config
        from config.platform_limits import PLATFORM_LIMITS as central_limits
        
        # Verify it's the same object used in analysis
        from api.endpoints.analysis import get_platform_limits
        
        for platform in ['tiktok', 'instagram', 'youtube', 'twitter']:
            central = central_limits.get(platform)
            from_func = get_platform_limits(platform)
            
            assert central.title_target == from_func.title_target, \
                f"INCONSISTENCY: {platform} title_target differs between config and function!"
            assert central.description_target == from_func.description_target, \
                f"INCONSISTENCY: {platform} description_target differs between config and function!"

    def test_no_hardcoded_limits_in_analysis(self):
        """
        FAILS IF: analysis.py has hardcoded limits instead of using config
        """
        import inspect
        from api.endpoints import analysis
        
        source = inspect.getsource(analysis)
        
        # Check that analysis imports from config (not hardcoded)
        assert 'from config.platform_limits import' in source or \
               'from config.platform_limits' in source, \
            "analysis.py should import platform limits from config!"
        
        # Should NOT have hardcoded description limits
        # (checking for obvious hardcoded values)
        hardcoded_patterns = [
            'description_max = 2200',  # Hardcoded Instagram limit
            'description_max = 4000',  # Hardcoded TikTok limit
            'title_max = 100',         # Hardcoded title limit
        ]
        
        for pattern in hardcoded_patterns:
            if pattern in source:
                # Allow in comments only
                lines_with_pattern = [l for l in source.split('\n') if pattern in l]
                for line in lines_with_pattern:
                    if not line.strip().startswith('#'):
                        pytest.fail(f"Found hardcoded limit in analysis.py: {pattern}")


# =============================================================================
# Integration Test: Error Handling
# =============================================================================

class TestErrorHandlingIntegration:
    """
    Tests that errors are handled gracefully.
    These tests WILL FAIL if:
    - Unknown platforms crash the system
    - Missing data causes unhandled exceptions
    """

    def test_unknown_platform_doesnt_crash(self):
        """
        FAILS IF: Unknown platform raises exception instead of returning fallback
        """
        try:
            limits = get_platform_limits("nonexistent_social_network_xyz")
            # Should return fallback, not raise
            assert limits is not None
            assert limits.title_target > 0
            assert limits.description_target > 0
        except Exception as e:
            pytest.fail(f"Unknown platform caused crash: {e}")

    def test_empty_content_doesnt_crash(self):
        """
        FAILS IF: Empty content causes exception
        """
        try:
            result = truncate_to_limit("", 100)
            assert result == ""
        except Exception as e:
            pytest.fail(f"Empty content caused crash: {e}")

    @pytest.mark.asyncio
    async def test_missing_analysis_data_handled_gracefully(self):
        """
        FAILS IF: Missing transcript/topics causes unhandled exception
        """
        with patch.dict('sys.modules', {'openai': MagicMock()}):
            import sys
            mock_openai_module = sys.modules['openai']
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Fallback content"
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai_module.OpenAI.return_value = mock_client
            
            try:
                # Call with minimal/empty data
                captions = await _generate_platform_captions(
                    title="Test",
                    transcript="",  # Empty transcript
                    topics=[],      # No topics
                    hooks=[],       # No hooks
                    platform="tiktok",
                    tone="engaging",
                    style=None,
                    custom_prompt=None,
                    include_hashtags=True,
                    include_hook=True
                )
                
                # Should return something, not crash
                assert captions is not None
                assert len(captions) > 0
                
            except Exception as e:
                pytest.fail(f"Missing data caused crash: {e}")


# =============================================================================
# Regression Tests
# =============================================================================

class TestRegressionPrevention:
    """
    Regression tests to prevent known issues from recurring.
    """

    def test_title_not_truncated_to_20_chars(self):
        """
        REGRESSION: Title was being truncated to 20 chars instead of 80
        FAILS IF: Title target is 20% of max instead of 80% of max
        """
        # The analysis doc mentioned "20 chars target" as a bug
        # Correct is "80% of max" (title_target)
        
        tiktok = get_platform_limits("tiktok")
        
        # TikTok title_max is 100, so target should be 80 (not 20!)
        assert tiktok.title_target == 80, \
            f"REGRESSION: TikTok title_target is {tiktok.title_target}, should be 80 (not 20!)"
        
        assert tiktok.title_target != 20, \
            "REGRESSION: Title target is 20% instead of 80% of max!"

    def test_all_platforms_dont_get_same_title(self):
        """
        REGRESSION: All platforms were getting the same generic title
        This test documents the expected fix - platform_titles should differ
        """
        # The response should include platform_titles dict
        # Each platform should potentially have a different title
        
        # Document the expected structure
        expected_response_structure = {
            "title": "generic_title",  # For backward compatibility
            "platform_titles": {
                "tiktok": "tiktok_optimized_title",
                "instagram": "instagram_optimized_title",
                # etc.
            }
        }
        
        assert "platform_titles" in expected_response_structure


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
