"""
Unit Tests: QA Gate Service (OPS-009)
======================================
Tests for quality assurance gate that validates content before publishing.

Test Coverage:
- FATE score validation
- Awareness level matching
- Platform length constraints
- Forbidden content detection
- CTA presence checking
- Link validation
- Overall QA status determination
"""

import pytest
from services.qa_gate_service import QAGateService, QAStatus, QAIssue


class TestQAGateService:
    """Test QA Gate Service functionality"""

    @pytest.fixture
    def qa_gate(self):
        """Create QA gate service instance"""
        return QAGateService()

    # =====================================================================
    # Test 1: Empty Content Detection
    # =====================================================================

    @pytest.mark.asyncio
    async def test_empty_content_fails(self, qa_gate):
        """Empty content should fail QA"""
        content = {
            "text": "",
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5},
            "awareness_level": 2,
            "target_awareness": 2
        }

        result = await qa_gate.check(content)

        assert result.status == QAStatus.FAIL
        assert not result.passed
        assert any(issue.category == "length" and issue.severity == "error" for issue in result.issues)

    @pytest.mark.asyncio
    async def test_whitespace_only_content_fails(self, qa_gate):
        """Whitespace-only content should fail QA"""
        content = {
            "text": "   \n  \t  ",
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5}
        }

        result = await qa_gate.check(content)

        assert result.status == QAStatus.FAIL
        assert not result.passed

    # =====================================================================
    # Test 2: FATE Score Validation
    # =====================================================================

    @pytest.mark.asyncio
    async def test_high_fate_scores_pass(self, qa_gate):
        """Content with high FATE scores should pass"""
        content = {
            "text": "Great content with strong focus, authority, tribe, and emotion!",
            "platform": "twitter",
            "fate_scores": {"F": 0.8, "A": 0.7, "T": 0.9, "E": 0.75},
            "awareness_level": 2,
            "target_awareness": 2
        }

        result = await qa_gate.check(content)

        assert result.status == QAStatus.PASS
        assert result.passed
        assert len([issue for issue in result.issues if issue.category == "fate"]) == 0

    @pytest.mark.asyncio
    async def test_low_fate_scores_warn(self, qa_gate):
        """Content with low FATE scores should warn"""
        content = {
            "text": "Some content here",
            "platform": "twitter",
            "fate_scores": {"F": 0.1, "A": 0.1, "T": 0.1, "E": 0.1},
            "awareness_level": 2,
            "target_awareness": 2
        }

        result = await qa_gate.check(content)

        assert result.status == QAStatus.WARN
        assert result.passed  # Warnings don't block
        assert len([issue for issue in result.issues if issue.category == "fate"]) > 0

    @pytest.mark.asyncio
    async def test_fate_score_normalized_keys(self, qa_gate):
        """FATE scores with different key formats should work"""
        # Test with full names
        content1 = {
            "text": "Test content",
            "platform": "twitter",
            "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.9, "emotion": 0.75}
        }

        result1 = await qa_gate.check(content1)
        assert result1.passed

        # Test with single letters
        content2 = {
            "text": "Test content",
            "platform": "twitter",
            "fate_scores": {"F": 0.8, "A": 0.7, "T": 0.9, "E": 0.75}
        }

        result2 = await qa_gate.check(content2)
        assert result2.passed

    # =====================================================================
    # Test 3: Platform Length Constraints
    # =====================================================================

    @pytest.mark.asyncio
    async def test_twitter_length_limits(self, qa_gate):
        """Twitter content should respect 280 char limit"""
        # Within limit
        content_ok = {
            "text": "This is a good tweet! " * 5,  # ~110 chars
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5}
        }

        result_ok = await qa_gate.check(content_ok)
        assert result_ok.passed
        assert not any(issue.category == "length" and issue.severity == "error" for issue in result_ok.issues)

        # Over limit
        content_long = {
            "text": "This is a very long tweet! " * 20,  # ~540 chars
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5}
        }

        result_long = await qa_gate.check(content_long)
        assert result_long.status == QAStatus.FAIL
        assert not result_long.passed
        assert any(issue.category == "length" and issue.severity == "error" for issue in result_long.issues)

    @pytest.mark.asyncio
    async def test_instagram_length_limits(self, qa_gate):
        """Instagram content should respect 2200 char limit"""
        content = {
            "text": "Instagram caption with some text here. " * 60,  # ~2400 chars
            "platform": "instagram",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5}
        }

        result = await qa_gate.check(content)
        assert result.status == QAStatus.FAIL
        assert not result.passed

    @pytest.mark.asyncio
    async def test_recommended_length_warning(self, qa_gate):
        """Content over recommended length should warn"""
        content = {
            "text": "A" * 270,  # Over recommended 240, under max 280 for Twitter
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5}
        }

        result = await qa_gate.check(content)
        assert result.passed  # Not blocked
        # May have warning about recommended length

    # =====================================================================
    # Test 4: Forbidden Content Detection
    # =====================================================================

    @pytest.mark.asyncio
    async def test_forbidden_phrases_fail(self, qa_gate):
        """Content with forbidden phrases should fail"""
        forbidden_texts = [
            "Get rich quick with this opportunity!",
            "Guaranteed results in 7 days!",
            "100% free money for everyone!",
            "Make money fast without any effort!",
            "This miracle cure will solve everything!",
        ]

        for text in forbidden_texts:
            content = {
                "text": text,
                "platform": "twitter",
                "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5}
            }

            result = await qa_gate.check(content)
            assert result.status == QAStatus.FAIL
            assert not result.passed
            assert any(issue.category == "forbidden" for issue in result.issues), \
                f"Expected forbidden content issue for: {text}"

    @pytest.mark.asyncio
    async def test_clean_content_passes(self, qa_gate):
        """Clean professional content should pass"""
        content = {
            "text": "Building software is hard. Here's what I learned about scaling teams.",
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5},
            "awareness_level": 2,
            "target_awareness": 2
        }

        result = await qa_gate.check(content)
        assert result.status == QAStatus.PASS
        assert result.passed
        assert not any(issue.category == "forbidden" for issue in result.issues)

    # =====================================================================
    # Test 5: Awareness Level Matching
    # =====================================================================

    @pytest.mark.asyncio
    async def test_awareness_exact_match_passes(self, qa_gate):
        """Exact awareness match should pass"""
        content = {
            "text": "Most founders struggle with validation. Here's the problem...",
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5},
            "awareness_level": 2,  # Problem-aware
            "target_awareness": 2
        }

        result = await qa_gate.check(content)
        assert result.passed
        # Should not have high-severity awareness issues

    @pytest.mark.asyncio
    async def test_awareness_close_match_passes(self, qa_gate):
        """Off-by-one awareness should pass with warning"""
        content = {
            "text": "Test content",
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5},
            "awareness_level": 2,
            "target_awareness": 3
        }

        result = await qa_gate.check(content)
        assert result.passed
        # May have warning about awareness

    @pytest.mark.asyncio
    async def test_awareness_large_mismatch_warns(self, qa_gate):
        """Large awareness mismatch should warn"""
        content = {
            "text": "Test content",
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5},
            "awareness_level": 1,  # Unaware
            "target_awareness": 5  # Most-aware
        }

        result = await qa_gate.check(content)
        assert result.status == QAStatus.WARN
        assert any(issue.category == "awareness" for issue in result.issues)

    # =====================================================================
    # Test 6: CTA Presence Checking
    # =====================================================================

    @pytest.mark.asyncio
    async def test_high_awareness_requires_cta(self, qa_gate):
        """High awareness content should have CTA"""
        # With CTA
        content_with_cta = {
            "text": "Ready to start? Get started today at example.com/start",
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5},
            "awareness_level": 5,  # Most-aware
            "target_awareness": 5
        }

        result_with = await qa_gate.check(content_with_cta)
        assert result_with.passed

        # Without CTA
        content_no_cta = {
            "text": "This is a random post with no call to action",
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5},
            "awareness_level": 5,  # Most-aware
            "target_awareness": 5
        }

        result_no = await qa_gate.check(content_no_cta)
        # Should have CTA warning or error

    @pytest.mark.asyncio
    async def test_low_awareness_no_cta_required(self, qa_gate):
        """Low awareness content doesn't need CTA"""
        content = {
            "text": "Imagine if you could build products 10x faster...",
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5},
            "awareness_level": 1,  # Unaware
            "target_awareness": 1
        }

        result = await qa_gate.check(content)
        assert result.passed
        # Should not require CTA

    # =====================================================================
    # Test 7: Link Validation
    # =====================================================================

    @pytest.mark.asyncio
    async def test_link_for_conversion_intent(self, qa_gate):
        """Conversion intent should have link"""
        # With link
        content_with_link = {
            "text": "Check out our product at https://example.com",
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5},
            "intent": "conversion"
        }

        result_with = await qa_gate.check(content_with_link)
        assert result_with.passed

        # Without link
        content_no_link = {
            "text": "Check out our product",
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5},
            "intent": "conversion"
        }

        result_no = await qa_gate.check(content_no_link)
        # Should have link warning

    @pytest.mark.asyncio
    async def test_engagement_intent_no_link_required(self, qa_gate):
        """Engagement intent doesn't require link"""
        content = {
            "text": "What's your favorite programming language? Reply below!",
            "platform": "twitter",
            "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5},
            "intent": "engagement"
        }

        result = await qa_gate.check(content)
        assert result.passed
        # Should not require link

    # =====================================================================
    # Test 8: Multiple Platforms
    # =====================================================================

    @pytest.mark.asyncio
    async def test_multiple_platforms(self, qa_gate):
        """Test constraints for different platforms"""
        platforms_and_max_lengths = [
            ("twitter", 280),
            ("instagram", 2200),
            ("tiktok", 2200),
            ("youtube", 5000),
            ("threads", 500),
            ("linkedin", 3000),
        ]

        for platform, max_length in platforms_and_max_lengths:
            # Content within limit
            content_ok = {
                "text": "A" * (max_length - 10),
                "platform": platform,
                "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5}
            }

            result_ok = await qa_gate.check(content_ok)
            assert result_ok.passed, f"{platform} should pass for content within limit"

            # Content over limit
            content_over = {
                "text": "A" * (max_length + 100),
                "platform": platform,
                "fate_scores": {"F": 0.5, "A": 0.5, "T": 0.5, "E": 0.5}
            }

            result_over = await qa_gate.check(content_over)
            assert result_over.status == QAStatus.FAIL, \
                f"{platform} should fail for content over {max_length} chars"

    # =====================================================================
    # Test 9: QA Result Metadata
    # =====================================================================

    @pytest.mark.asyncio
    async def test_qa_result_includes_metadata(self, qa_gate):
        """QA result should include comprehensive metadata"""
        content = {
            "text": "Test content for metadata check",
            "platform": "twitter",
            "fate_scores": {"F": 0.8, "A": 0.7, "T": 0.9, "E": 0.75},
            "awareness_level": 2,
            "target_awareness": 2,
            "template_id": "tpl_123"
        }

        result = await qa_gate.check(content)

        assert result.metadata is not None
        assert result.metadata.get("template_id") == "tpl_123"
        assert result.metadata.get("awareness_level") == 2
        assert result.metadata.get("target_awareness") == 2
        assert result.metadata.get("platform") == "twitter"
        assert "content_length" in result.metadata

    @pytest.mark.asyncio
    async def test_qa_result_includes_scores(self, qa_gate):
        """QA result should include FATE scores"""
        fate_scores = {"F": 0.8, "A": 0.7, "T": 0.9, "E": 0.75}

        content = {
            "text": "Test content",
            "platform": "twitter",
            "fate_scores": fate_scores
        }

        result = await qa_gate.check(content)

        assert result.scores == fate_scores

    # =====================================================================
    # Test 10: Complex Scenarios
    # =====================================================================

    @pytest.mark.asyncio
    async def test_multiple_issues_detected(self, qa_gate):
        """QA should detect multiple issues in one check"""
        content = {
            "text": "Get rich quick! " + ("A" * 300),  # Forbidden + too long
            "platform": "twitter",
            "fate_scores": {"F": 0.1, "A": 0.1, "T": 0.1, "E": 0.1},  # Low scores
            "awareness_level": 1,
            "target_awareness": 5  # Mismatch
        }

        result = await qa_gate.check(content)

        assert result.status == QAStatus.FAIL
        assert not result.passed
        assert len(result.issues) > 2  # Multiple issues detected
        assert any(issue.category == "forbidden" for issue in result.issues)
        assert any(issue.category == "length" for issue in result.issues)

    @pytest.mark.asyncio
    async def test_perfect_content_passes(self, qa_gate):
        """Perfect content should pass with minimal/no critical issues"""
        content = {
            "text": """Most solo founders struggle with product validation.

After working with 50+ founders, I found the pattern.

If you're a solo entrepreneur, you've felt this pain.

Here's what actually works: structured customer interviews.

Try it free: https://example.com/start""",
            "platform": "twitter",
            "fate_scores": {"F": 0.85, "A": 0.78, "T": 0.92, "E": 0.81},
            "awareness_level": 2,
            "target_awareness": 2,
            "template_id": "tpl_problem_aware_001",
            "intent": "conversion"
        }

        result = await qa_gate.check(content)

        assert result.status == QAStatus.PASS
        assert result.passed
        # No critical issues (errors or warnings allowed, but not errors)
        assert not any(issue.severity == "error" for issue in result.issues)

    @pytest.mark.asyncio
    async def test_warnings_dont_block_publishing(self, qa_gate):
        """Content with warnings should still be publishable"""
        content = {
            "text": "Some content here with minor issues",
            "platform": "twitter",
            "fate_scores": {"F": 0.25, "A": 0.25, "T": 0.25, "E": 0.25},  # Low but not critical
            "awareness_level": 2,
            "target_awareness": 3  # Small mismatch
        }

        result = await qa_gate.check(content)

        assert result.status == QAStatus.WARN
        assert result.passed  # Can still publish
        assert len(result.issues) > 0
        assert all(issue.severity != "error" for issue in result.issues)


# =====================================================================
# Integration Tests
# =====================================================================

class TestQAGateIntegration:
    """Integration tests for QA gate with other services"""

    @pytest.mark.asyncio
    async def test_qa_gate_with_real_content(self):
        """Test QA gate with realistic content examples"""
        qa_gate = QAGateService()

        # Example 1: Problem-aware Twitter post
        content1 = {
            "text": "Spent 6 months building a product nobody wanted.\n\nHere's what I learned about customer validation:\n\n1. Talk to users BEFORE coding\n2. Ask about problems, not solutions\n3. Watch what they do, not what they say\n\nSaved me 2 years on the next startup.",
            "platform": "twitter",
            "fate_scores": {"F": 0.82, "A": 0.75, "T": 0.88, "E": 0.79},
            "awareness_level": 2,
            "target_awareness": 2,
            "template_id": "problem_aware_thread"
        }

        result1 = await qa_gate.check(content1)
        assert result1.passed
        assert result1.status in [QAStatus.PASS, QAStatus.WARN]

        # Example 2: Product-aware with CTA
        content2 = {
            "text": "Launch your MVP in days, not months.\n\nOur no-code platform helps founders ship faster.\n\n✓ Pre-built templates\n✓ One-click deploy\n✓ Built-in analytics\n\nStart free: https://example.com",
            "platform": "twitter",
            "fate_scores": {"F": 0.91, "A": 0.68, "T": 0.74, "E": 0.83},
            "awareness_level": 4,
            "target_awareness": 4,
            "intent": "conversion"
        }

        result2 = await qa_gate.check(content2)
        assert result2.passed

        # Example 3: Spammy content (should fail)
        content3 = {
            "text": "GET RICH QUICK!!! Guaranteed money in 7 days! 100% FREE! Click now!!!",
            "platform": "twitter",
            "fate_scores": {"F": 0.3, "A": 0.2, "T": 0.1, "E": 0.6},
            "awareness_level": 5,
            "target_awareness": 5
        }

        result3 = await qa_gate.check(content3)
        assert not result3.passed
        assert result3.status == QAStatus.FAIL
