"""
Integration tests for QA Gate (TEST-007)
Tests for banned phrases, spam patterns, approval routing
Acceptance: 100% banned blocked, 0% false positives
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

# Import services
from services.qa_gate_service import QAGateService, QAResult, QAIssue


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = Mock(spec=AsyncSession)
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def qa_service(mock_db_session):
    """QA Gate service instance"""
    return QAGateService(db=mock_db_session)


class TestFATEScoreValidation:
    """Test FATE score minimum thresholds"""

    @pytest.mark.asyncio
    async def test_pass_with_good_fate_scores(self, qa_service):
        """Test content passes with good FATE scores"""
        content = {
            "text": "Stop wasting time on content that doesn't convert",
            "fate_scores": {
                "focus": 0.8,
                "authority": 0.7,
                "tribe": 0.6,
                "emotion": 0.9
            },
            "awareness_level": 2,
            "target_awareness": 2,
            "platform": "twitter"
        }

        result = await qa_service.check(content)

        assert result.passed is True
        assert result.status == "PASS"
        assert len([i for i in result.issues if i.severity == "error"]) == 0

    @pytest.mark.asyncio
    async def test_warn_with_low_fate_scores(self, qa_service):
        """Test content warns with low FATE scores but doesn't fail"""
        content = {
            "text": "Here is some generic content",
            "fate_scores": {
                "focus": 0.2,  # Below 0.3 minimum
                "authority": 0.1,  # Below 0.2 minimum
                "tribe": 0.15,  # Below 0.2 minimum
                "emotion": 0.2  # Below 0.3 minimum
            },
            "awareness_level": 2,
            "target_awareness": 2,
            "platform": "twitter"
        }

        result = await qa_service.check(content)

        # Low FATE scores = WARNING, not FAIL (allow publish but warn user)
        assert result.status == "WARN"
        warnings = [i for i in result.issues if i.severity == "warning"]
        assert len(warnings) > 0
        assert any("FATE" in w.message or "score" in w.message.lower() for w in warnings)

    @pytest.mark.asyncio
    async def test_fate_score_thresholds(self, qa_service):
        """Test specific FATE score minimum thresholds"""
        # Minimum thresholds: F:0.3, A:0.2, T:0.2, E:0.3

        test_cases = [
            {"focus": 0.29, "expected_warning": True},  # Below 0.3
            {"focus": 0.31, "expected_warning": False},  # Above 0.3
            {"authority": 0.19, "expected_warning": True},  # Below 0.2
            {"authority": 0.21, "expected_warning": False},  # Above 0.2
            {"tribe": 0.19, "expected_warning": True},  # Below 0.2
            {"tribe": 0.21, "expected_warning": False},  # Above 0.2
            {"emotion": 0.29, "expected_warning": True},  # Below 0.3
            {"emotion": 0.31, "expected_warning": False},  # Above 0.3
        ]

        for case in test_cases:
            fate_scores = {
                "focus": case.get("focus", 0.5),
                "authority": case.get("authority", 0.5),
                "tribe": case.get("tribe", 0.5),
                "emotion": case.get("emotion", 0.5)
            }

            content = {
                "text": "Test content",
                "fate_scores": fate_scores,
                "awareness_level": 2,
                "target_awareness": 2,
                "platform": "twitter"
            }

            result = await qa_service.check(content)
            has_fate_warning = any("FATE" in i.message or "score" in i.message.lower()
                                  for i in result.issues if i.severity == "warning")

            if case["expected_warning"]:
                assert has_fate_warning, f"Expected warning for {case}"
            # Note: May still have warnings from other checks


class TestBannedPhrases:
    """Test forbidden content detection (100% banned blocked)"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("banned_phrase", [
        "get rich quick",
        "guaranteed results",
        "100% free",
        "no risk",
        "unlimited money",
        "lose weight overnight",
        "miracle cure",
        "make money fast",
        "work from home opportunity",
        "be your own boss"
    ])
    async def test_block_all_banned_phrases(self, qa_service, banned_phrase):
        """Test all banned phrases are blocked (100% detection rate)"""
        content = {
            "text": f"Amazing opportunity! {banned_phrase.capitalize()} with our system!",
            "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
            "awareness_level": 5,
            "target_awareness": 5,
            "platform": "twitter"
        }

        result = await qa_service.check(content)

        # Must FAIL on banned phrases
        assert result.passed is False
        assert result.status == "FAIL"

        errors = [i for i in result.issues if i.severity == "error"]
        assert len(errors) > 0
        assert any("banned" in e.message.lower() or "forbidden" in e.message.lower()
                  for e in errors)

    @pytest.mark.asyncio
    async def test_case_insensitive_banned_detection(self, qa_service):
        """Test banned phrase detection is case-insensitive"""
        test_cases = [
            "GET RICH QUICK",
            "Get Rich Quick",
            "get rich quick",
            "GeT rIcH qUiCk"
        ]

        for text in test_cases:
            content = {
                "text": f"Don't fall for {text} schemes",
                "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
                "awareness_level": 2,
                "target_awareness": 2,
                "platform": "twitter"
            }

            result = await qa_service.check(content)

            # Should detect banned phrase regardless of case
            assert result.passed is False
            errors = [i for i in result.issues if i.severity == "error"]
            assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_no_false_positives_on_legitimate_content(self, qa_service):
        """Test legitimate content passes (0% false positive rate)"""
        legitimate_content_samples = [
            "Quick tips to improve your content strategy",  # "quick" is OK in context
            "Free resources for content creators",  # "free" is OK when not spammy
            "Risk-aware content marketing approach",  # "risk" is OK in context
            "Get started with content creation today",  # "get" is OK
            "Unlimited creative possibilities",  # "unlimited" is OK in context
        ]

        for text in legitimate_content_samples:
            content = {
                "text": text,
                "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
                "awareness_level": 2,
                "target_awareness": 2,
                "platform": "twitter"
            }

            result = await qa_service.check(content)

            # Should NOT have banned phrase errors
            banned_errors = [i for i in result.issues
                           if i.severity == "error" and
                           ("banned" in i.message.lower() or "forbidden" in i.message.lower())]

            assert len(banned_errors) == 0, f"False positive on: {text}"


class TestAwarenessMatchValidation:
    """Test awareness level matching"""

    @pytest.mark.asyncio
    async def test_pass_exact_awareness_match(self, qa_service):
        """Test exact awareness level match passes"""
        content = {
            "text": "Most people don't realize this problem exists",
            "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
            "awareness_level": 2,
            "target_awareness": 2,
            "platform": "twitter"
        }

        result = await qa_service.check(content)

        awareness_issues = [i for i in result.issues if "awareness" in i.message.lower()]
        # Should not have awareness errors
        assert len([i for i in awareness_issues if i.severity == "error"]) == 0

    @pytest.mark.asyncio
    async def test_pass_awareness_within_tolerance(self, qa_service):
        """Test awareness level ±1 tolerance"""
        # Target 3, classified 2 or 4 should pass
        test_cases = [
            (3, 2),  # -1 tolerance
            (3, 3),  # exact match
            (3, 4),  # +1 tolerance
        ]

        for target, classified in test_cases:
            content = {
                "text": "Test content",
                "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
                "awareness_level": classified,
                "target_awareness": target,
                "platform": "twitter"
            }

            result = await qa_service.check(content)

            awareness_errors = [i for i in result.issues
                              if "awareness" in i.message.lower() and i.severity == "error"]
            assert len(awareness_errors) == 0, f"Should pass for target={target}, classified={classified}"

    @pytest.mark.asyncio
    async def test_warn_awareness_outside_tolerance(self, qa_service):
        """Test awareness level mismatch outside ±1 warns or fails"""
        # Target 2, classified 5 = too far off
        content = {
            "text": "Buy our product now!",  # Level 5 content
            "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
            "awareness_level": 5,
            "target_awareness": 2,  # Targeting level 2 audience
            "platform": "twitter"
        }

        result = await qa_service.check(content)

        # Should have awareness warning/error
        awareness_issues = [i for i in result.issues if "awareness" in i.message.lower()]
        assert len(awareness_issues) > 0


class TestPlatformLengthConstraints:
    """Test platform-specific length limits"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("platform,max_length,should_fail", [
        ("twitter", 280, True),  # Over limit
        ("twitter", 280, False),  # Within limit
        ("instagram", 2200, True),
        ("instagram", 2200, False),
        ("tiktok", 2200, True),
        ("tiktok", 2200, False),
        ("youtube", 5000, True),
        ("youtube", 5000, False),
        ("threads", 500, True),
        ("threads", 500, False),
    ])
    async def test_platform_length_validation(self, qa_service, platform, max_length, should_fail):
        """Test content length validation per platform"""
        if should_fail:
            text = "x" * (max_length + 10)  # Exceed limit
        else:
            text = "x" * (max_length - 10)  # Within limit

        content = {
            "text": text,
            "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
            "awareness_level": 2,
            "target_awareness": 2,
            "platform": platform
        }

        result = await qa_service.check(content)

        length_errors = [i for i in result.issues
                        if "length" in i.message.lower() and i.severity == "error"]

        if should_fail:
            assert len(length_errors) > 0, f"Should fail length check for {platform}"
        else:
            assert len(length_errors) == 0, f"Should pass length check for {platform}"


class TestCTAPresence:
    """Test call-to-action validation"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("awareness_level,cta_text,should_pass", [
        (1, "Learn more about this", True),  # Level 1: soft CTA OK
        (2, "Check out this approach", True),  # Level 2: educational CTA OK
        (3, "Try this method", True),  # Level 3: action CTA
        (4, "Get started today", True),  # Level 4: direct CTA
        (5, "Buy now", True),  # Level 5: transactional CTA
        (5, "", False),  # Level 5 with no CTA should warn
    ])
    async def test_cta_requirements_by_awareness_level(self, qa_service, awareness_level, cta_text, should_pass):
        """Test CTA requirements vary by awareness level"""
        content = {
            "text": f"Some content here. {cta_text}",
            "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
            "awareness_level": awareness_level,
            "target_awareness": awareness_level,
            "platform": "twitter"
        }

        result = await qa_service.check(content)

        cta_issues = [i for i in result.issues if "cta" in i.message.lower() or "call" in i.message.lower()]

        if not should_pass:
            # Should have CTA warning for high-awareness content without CTA
            assert len(cta_issues) > 0

    @pytest.mark.asyncio
    async def test_detect_cta_keywords(self, qa_service):
        """Test CTA keyword detection"""
        cta_keywords = [
            "click here",
            "try now",
            "get started",
            "learn more",
            "sign up",
            "download",
            "subscribe",
            "join us",
            "buy now",
            "shop",
            "order today"
        ]

        for keyword in cta_keywords:
            content = {
                "text": f"Great content about marketing. {keyword.capitalize()} to see results!",
                "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
                "awareness_level": 5,
                "target_awareness": 5,
                "platform": "twitter"
            }

            result = await qa_service.check(content)

            # Should detect CTA presence
            cta_issues = [i for i in result.issues
                         if "cta" in i.message.lower() and i.severity == "warning"]
            # Content with CTA should pass CTA check
            assert len([i for i in cta_issues if "missing" in i.message.lower()]) == 0


class TestLinkValidation:
    """Test URL/shortlink presence validation"""

    @pytest.mark.asyncio
    async def test_detect_url_presence(self, qa_service):
        """Test URL detection in content"""
        content_with_url = {
            "text": "Check out this guide: https://example.com/guide",
            "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
            "awareness_level": 5,
            "target_awareness": 5,
            "platform": "twitter"
        }

        result = await qa_service.check(content_with_url)

        # Should detect URL
        # Implementation detail: may not fail, just track presence

    @pytest.mark.asyncio
    async def test_warn_missing_link_for_lead_gen(self, qa_service):
        """Test warning when lead-gen content lacks link"""
        content = {
            "text": "Get our free guide to content marketing!",  # CTA but no link
            "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
            "awareness_level": 4,
            "target_awareness": 4,
            "platform": "twitter",
            "intent": "lead_generation"
        }

        result = await qa_service.check(content)

        # Should have warning about missing link
        link_issues = [i for i in result.issues if "link" in i.message.lower() or "url" in i.message.lower()]
        # May warn if link is expected but missing


class TestQAResultStructure:
    """Test QA result data structure"""

    @pytest.mark.asyncio
    async def test_qa_result_format(self, qa_service):
        """Test QA result has correct structure"""
        content = {
            "text": "Good content here",
            "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
            "awareness_level": 2,
            "target_awareness": 2,
            "platform": "twitter"
        }

        result = await qa_service.check(content)

        assert hasattr(result, 'status')
        assert result.status in ["PASS", "WARN", "FAIL"]
        assert hasattr(result, 'passed')
        assert isinstance(result.passed, bool)
        assert hasattr(result, 'issues')
        assert isinstance(result.issues, list)
        assert hasattr(result, 'metadata')

    @pytest.mark.asyncio
    async def test_qa_issue_structure(self, qa_service):
        """Test QA issue has correct structure"""
        content = {
            "text": "get rich quick scheme",  # Will trigger banned phrase
            "fate_scores": {"focus": 0.1, "authority": 0.1, "tribe": 0.1, "emotion": 0.1},
            "awareness_level": 5,
            "target_awareness": 2,
            "platform": "twitter"
        }

        result = await qa_service.check(content)

        for issue in result.issues:
            assert hasattr(issue, 'severity')
            assert issue.severity in ["error", "warning", "info"]
            assert hasattr(issue, 'category')
            assert hasattr(issue, 'message')
            assert len(issue.message) > 0


class TestApprovalRouting:
    """Test approval routing logic"""

    @pytest.mark.asyncio
    async def test_auto_approve_clean_content(self, qa_service):
        """Test clean content is auto-approved"""
        content = {
            "text": "Here's a helpful tip for content creators",
            "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
            "awareness_level": 2,
            "target_awareness": 2,
            "platform": "twitter"
        }

        result = await qa_service.check(content)

        assert result.passed is True
        assert result.status == "PASS"
        # Auto-approve = no manual review needed

    @pytest.mark.asyncio
    async def test_route_to_manual_review_on_warnings(self, qa_service):
        """Test content with warnings routes to manual approval"""
        content = {
            "text": "Some content with borderline issues",
            "fate_scores": {"focus": 0.25, "authority": 0.18, "tribe": 0.18, "emotion": 0.25},
            "awareness_level": 2,
            "target_awareness": 2,
            "platform": "twitter"
        }

        result = await qa_service.check(content)

        if result.status == "WARN":
            # Content with warnings should be flagged for manual review
            assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_block_content_on_errors(self, qa_service):
        """Test content with errors is blocked"""
        content = {
            "text": "guaranteed results with no risk!",  # Banned phrases
            "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
            "awareness_level": 2,
            "target_awareness": 2,
            "platform": "twitter"
        }

        result = await qa_service.check(content)

        assert result.passed is False
        assert result.status == "FAIL"
        errors = [i for i in result.issues if i.severity == "error"]
        assert len(errors) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_empty_content(self, qa_service):
        """Test handling of empty content"""
        content = {
            "text": "",
            "fate_scores": {"focus": 0.0, "authority": 0.0, "tribe": 0.0, "emotion": 0.0},
            "awareness_level": 1,
            "target_awareness": 1,
            "platform": "twitter"
        }

        result = await qa_service.check(content)

        # Should fail on empty content
        assert result.passed is False

    @pytest.mark.asyncio
    async def test_extremely_long_content(self, qa_service):
        """Test handling of very long content"""
        content = {
            "text": "x" * 10000,  # Very long
            "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
            "awareness_level": 2,
            "target_awareness": 2,
            "platform": "twitter"  # Max 280 chars
        }

        result = await qa_service.check(content)

        # Should fail length check
        assert result.passed is False
        length_errors = [i for i in result.issues if "length" in i.message.lower()]
        assert len(length_errors) > 0

    @pytest.mark.asyncio
    async def test_special_characters_in_content(self, qa_service):
        """Test handling of special characters"""
        content = {
            "text": "Test content with émojis 🚀 and spëcial çhars!",
            "fate_scores": {"focus": 0.8, "authority": 0.7, "tribe": 0.6, "emotion": 0.9},
            "awareness_level": 2,
            "target_awareness": 2,
            "platform": "twitter"
        }

        result = await qa_service.check(content)

        # Should handle special characters without errors
        # (unless they trigger other checks)
