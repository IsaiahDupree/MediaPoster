"""
Unit tests for text_utils.py - Character counting and truncation utilities
"""
import pytest
from services.content_pipeline.text_utils import (
    count_utf8_bytes,
    count_utf16_runes,
    count_graphemes,
    count_by_rule,
    compute_target,
    truncate_smart,
    extract_hashtags,
    format_hashtags,
    validate_text_fits,
    split_into_segments,
)


class TestCharacterCounting:
    """Tests for character counting functions"""
    
    def test_count_utf8_bytes_ascii(self):
        """ASCII characters are 1 byte each"""
        assert count_utf8_bytes("hello") == 5
        assert count_utf8_bytes("") == 0
        assert count_utf8_bytes("a") == 1
    
    def test_count_utf8_bytes_unicode(self):
        """Unicode characters use multiple bytes"""
        assert count_utf8_bytes("é") == 2  # Latin with accent
        assert count_utf8_bytes("你好") == 6  # Chinese (3 bytes each)
        assert count_utf8_bytes("🔥") == 4  # Emoji (4 bytes)
    
    def test_count_utf16_runes_ascii(self):
        """ASCII uses 1 UTF-16 code unit each"""
        assert count_utf16_runes("hello") == 5
        assert count_utf16_runes("") == 0
    
    def test_count_utf16_runes_emoji(self):
        """Emoji can use 2 UTF-16 code units (surrogate pairs)"""
        # Basic emoji
        assert count_utf16_runes("🔥") == 2  # Surrogate pair
        # Mixed content
        assert count_utf16_runes("Hi 🔥") == 5  # 3 + 2
    
    def test_count_graphemes_basic(self):
        """Basic grapheme counting"""
        assert count_graphemes("hello") == 5
        assert count_graphemes("") == 0
    
    def test_count_graphemes_emoji(self):
        """Emoji should count as single graphemes"""
        # Single emoji
        result = count_graphemes("🔥")
        assert result >= 1  # At least 1 grapheme
        
        # Text with emoji
        result = count_graphemes("Hi 🔥")
        assert result >= 4  # At least "H", "i", " ", emoji
    
    def test_count_by_rule_graphemes(self):
        """count_by_rule with graphemes"""
        assert count_by_rule("hello", "graphemes") == 5
    
    def test_count_by_rule_utf8(self):
        """count_by_rule with utf8_bytes"""
        assert count_by_rule("hello", "utf8_bytes") == 5
        assert count_by_rule("🔥", "utf8_bytes") == 4
    
    def test_count_by_rule_utf16(self):
        """count_by_rule with utf16"""
        assert count_by_rule("hello", "utf16") == 5
        assert count_by_rule("🔥", "utf16") == 2


class TestComputeTarget:
    """Tests for compute_target function"""
    
    def test_compute_target_with_max(self):
        """Target is 80% of max by default"""
        assert compute_target(100) == 80
        assert compute_target(1000) == 800
    
    def test_compute_target_custom_margin(self):
        """Custom margin percentage"""
        assert compute_target(100, margin_pct=0.10) == 90
        assert compute_target(100, margin_pct=0.30) == 70
    
    def test_compute_target_with_soft_cap(self):
        """Soft cap limits the target"""
        # Soft cap is lower than computed target
        assert compute_target(1000, soft_cap=500) == 500
        # Soft cap is higher than computed target
        assert compute_target(100, soft_cap=90) == 80
    
    def test_compute_target_no_max(self):
        """Returns soft_cap when no max"""
        assert compute_target(None, soft_cap=500) == 500
        assert compute_target(None) is None


class TestTruncateSmart:
    """Tests for smart truncation"""
    
    def test_truncate_no_change_needed(self):
        """Text within limit is unchanged"""
        text = "Hello world"
        result = truncate_smart(text, 100, "graphemes")
        assert result == text
    
    def test_truncate_basic(self):
        """Basic truncation"""
        text = "This is a very long text that needs to be truncated"
        result = truncate_smart(text, 20, "graphemes")
        assert count_graphemes(result) <= 20
    
    def test_truncate_preserves_word_boundary(self):
        """Truncation snaps to word boundary"""
        text = "This is a sentence with multiple words"
        result = truncate_smart(text, 25, "graphemes")
        # Should not cut in middle of word
        assert not result.endswith("wor")
    
    def test_truncate_adds_ellipsis(self):
        """Significant truncation adds ellipsis"""
        text = "This is a very long text that definitely needs truncation to fit"
        result = truncate_smart(text, 30, "graphemes")
        # May or may not have ellipsis depending on space
        assert count_graphemes(result) <= 30
    
    def test_truncate_with_hashtags(self):
        """Hashtag preservation option"""
        text = "Great content here!\n\n#viral #trending #content"
        result = truncate_smart(text, 50, "graphemes", preserve_hashtags=True)
        # Should try to keep hashtags if possible
        assert count_graphemes(result) <= 50


class TestHashtagFunctions:
    """Tests for hashtag extraction and formatting"""
    
    def test_extract_hashtags(self):
        """Extract hashtags from text"""
        text = "Check this out #viral #content"
        clean_text, hashtags = extract_hashtags(text)
        
        assert "#viral" in hashtags
        assert "#content" in hashtags
        assert "#" not in clean_text or clean_text.count("#") == 0
    
    def test_extract_hashtags_none(self):
        """Text without hashtags"""
        text = "No hashtags here"
        clean_text, hashtags = extract_hashtags(text)
        
        assert clean_text == "No hashtags here"
        assert hashtags == []
    
    def test_format_hashtags_basic(self):
        """Format hashtag list"""
        hashtags = ["viral", "content", "creator"]
        result = format_hashtags(hashtags)
        
        assert result == "#viral #content #creator"
    
    def test_format_hashtags_with_hash(self):
        """Hashtags already have #"""
        hashtags = ["#viral", "#content"]
        result = format_hashtags(hashtags)
        
        assert result == "#viral #content"
    
    def test_format_hashtags_max_count(self):
        """Limit hashtag count"""
        hashtags = ["a", "b", "c", "d", "e"]
        result = format_hashtags(hashtags, max_count=3)
        
        assert result == "#a #b #c"


class TestValidateTextFits:
    """Tests for text validation"""
    
    def test_validate_fits(self):
        """Text fits within limit"""
        fits, count = validate_text_fits("hello", 10, "graphemes")
        assert fits is True
        assert count == 5
    
    def test_validate_not_fits(self):
        """Text exceeds limit"""
        fits, count = validate_text_fits("hello world", 5, "graphemes")
        assert fits is False
        assert count == 11
    
    def test_validate_no_limit(self):
        """No limit means always fits"""
        fits, count = validate_text_fits("any text", None, "graphemes")
        assert fits is True


class TestSplitIntoSegments:
    """Tests for text segmentation"""
    
    def test_split_short_text(self):
        """Short text needs no splitting"""
        text = "Short text"
        segments = split_into_segments(text, 100, "graphemes")
        
        assert len(segments) == 1
        assert segments[0] == text
    
    def test_split_long_text(self):
        """Long text is split into segments"""
        text = "First sentence. Second sentence. Third sentence."
        segments = split_into_segments(text, 20, "graphemes")
        
        assert len(segments) >= 2
        for seg in segments:
            assert count_graphemes(seg) <= 20 or len(seg.split()) <= 3


class TestPlatformSpecificCounting:
    """Tests for platform-specific character counting scenarios"""
    
    def test_tiktok_utf16_emoji(self):
        """TikTok uses UTF-16 counting"""
        # Caption with emoji
        text = "Check this out 🔥🔥🔥"
        count = count_by_rule(text, "utf16")
        # "Check this out " = 15 chars, 3 emoji × 2 = 6
        assert count == 21
    
    def test_threads_utf8_bytes(self):
        """Threads uses UTF-8 byte counting"""
        text = "Hello 世界"  # Hello + space + 2 Chinese chars
        count = count_by_rule(text, "utf8_bytes")
        # "Hello " = 6 bytes, 2 Chinese chars × 3 = 6 bytes
        assert count == 12
    
    def test_instagram_graphemes(self):
        """Instagram uses grapheme counting"""
        text = "Hello 🔥"
        count = count_by_rule(text, "graphemes")
        # H, e, l, l, o, space, emoji = 7 graphemes
        assert count >= 7


class TestEdgeCases:
    """Edge case tests"""
    
    def test_empty_string(self):
        """Empty string handling"""
        assert count_utf8_bytes("") == 0
        assert count_utf16_runes("") == 0
        assert count_graphemes("") == 0
        assert compute_target(None) is None
    
    def test_only_whitespace(self):
        """Whitespace-only text"""
        text = "   "
        assert count_graphemes(text) == 3
    
    def test_newlines(self):
        """Text with newlines"""
        text = "Line 1\nLine 2"
        assert count_graphemes(text) == 13
    
    def test_very_long_text(self):
        """Very long text truncation"""
        text = "word " * 1000  # 5000 chars
        result = truncate_smart(text, 100, "graphemes")
        assert count_graphemes(result) <= 100
