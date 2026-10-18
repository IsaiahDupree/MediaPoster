"""
Unit tests for Awareness Level Classifier (OPS-002)
===================================================
Tests the rule-based awareness level classification system.
"""

import pytest
from services.awareness_classifier import (
    AwarenessClassifier,
    AwarenessLevel,
    get_awareness_classifier
)


class TestAwarenessClassifier:
    """Test suite for AwarenessClassifier"""

    @pytest.fixture
    def classifier(self):
        """Get classifier instance"""
        return get_awareness_classifier()

    def test_singleton_pattern(self, classifier):
        """Test that get_awareness_classifier returns same instance"""
        classifier2 = get_awareness_classifier()
        assert classifier is classifier2

    def test_unaware_classification(self, classifier):
        """Test UNAWARE level detection"""
        texts = [
            "Most people don't know this shocking truth about productivity...",
            "Here's a story about what happened when I stopped using social media",
            "Take this quiz to see if you're one of the successful founders",
            "Picture this: You wake up and check your email...",
            "Ever wonder why some people succeed and others fail?",
        ]

        for text in texts:
            result = classifier.classify(text)
            assert result.level == AwarenessLevel.UNAWARE, f"Failed for: {text}"
            assert result.confidence > 0.3

    def test_problem_aware_classification(self, classifier):
        """Test PROBLEM_AWARE level detection"""
        texts = [
            "Struggling with low engagement on your posts? Here's why...",
            "Tired of wasting time on content that doesn't convert?",
            "If you're like me, you keep trying different approaches but nothing works",
            "The real problem is that most founders don't understand their audience",
            "Why does your content never get the traction you expect?",
        ]

        for text in texts:
            result = classifier.classify(text)
            assert result.level == AwarenessLevel.PROBLEM_AWARE, f"Failed for: {text}"
            assert result.confidence > 0.3

    def test_solution_aware_classification(self, classifier):
        """Test SOLUTION_AWARE level detection"""
        texts = [
            "There are 3 ways to grow your audience, but only one actually works",
            "Here's how the best creators find viral topics in under 10 minutes",
            "Traditional approaches vs. AI-powered content: which wins?",
            "Case study: How we 10x'd engagement with this simple framework",
            "Studies show that 73% of successful creators use this method",
        ]

        for text in texts:
            result = classifier.classify(text)
            assert result.level == AwarenessLevel.SOLUTION_AWARE, f"Failed for: {text}"
            assert result.confidence > 0.3

    def test_product_aware_classification(self, classifier):
        """Test PRODUCT_AWARE level detection"""
        texts = [
            "Our tool helps you find trending topics 10x faster than manual research",
            "Unlike other platforms, KeywordRadar.app focuses on demand signals",
            "What makes this different? It's built specifically for indie founders",
            "You might be thinking: 'Another content tool?' Here's the thing...",
            "With TrendScout, you get real-time trend alerts and AI-powered briefs",
        ]

        for text in texts:
            result = classifier.classify(text)
            assert result.level == AwarenessLevel.PRODUCT_AWARE, f"Failed for: {text}"
            assert result.confidence > 0.3

    def test_most_aware_classification(self, classifier):
        """Test MOST_AWARE level detection"""
        texts = [
            "Get started today with our 14-day free trial. No credit card required.",
            "Limited time: Get 50% off the annual plan. Only 10 spots left!",
            "Try it free for 30 days. Cancel anytime, money-back guarantee.",
            "Sign up now for just $29/month and start finding viral topics today",
            "Buy now and get instant access to our premium content library",
        ]

        for text in texts:
            result = classifier.classify(text)
            assert result.level == AwarenessLevel.MOST_AWARE, f"Failed for: {text}"
            assert result.confidence > 0.3

    def test_empty_text(self, classifier):
        """Test handling of empty text"""
        result = classifier.classify("")
        assert result.confidence == 0.0
        assert result.level == AwarenessLevel.UNAWARE  # Default

    def test_mixed_signals(self, classifier):
        """Test text with multiple awareness signals"""
        text = """
        Struggling to find trending topics? (Problem-Aware)
        There are many tools out there, but most don't work. (Solution-Aware)
        Our platform uses AI to surface demand signals in real-time. (Product-Aware)
        Get started free today! (Most-Aware)
        """

        result = classifier.classify(text)
        # Should classify based on strongest signal
        assert result.level in [
            AwarenessLevel.PRODUCT_AWARE,
            AwarenessLevel.MOST_AWARE
        ]
        assert result.confidence > 0.3

    def test_score_all(self, classifier):
        """Test score_all returns all level scores"""
        text = "Struggling with content creation? Here's how top creators do it."
        scores = classifier.score_all(text)

        assert isinstance(scores, dict)
        assert len(scores) == 5
        assert all(0.0 <= score <= 1.0 for score in scores.values())
        assert "problem_aware" in scores
        assert "solution_aware" in scores

    def test_confidence_threshold(self, classifier):
        """Test minimum confidence threshold"""
        # Very generic text with no clear awareness signals
        text = "This is some content."
        result = classifier.classify(text, min_confidence=0.3)

        # Should still return a result, but with low confidence
        assert result.confidence < 0.3

    def test_real_world_examples(self, classifier):
        """Test with real-world content examples"""

        # Example 1: PROBLEM_AWARE tweet
        text1 = """
        Why do most founders fail at content marketing?

        They're posting 3x/day but getting zero engagement.
        Spending hours creating posts that nobody reads.
        Trying every "viral" trend but nothing sticks.

        The real problem? They're creating content in a vacuum.
        """
        result1 = classifier.classify(text1)
        assert result1.level == AwarenessLevel.PROBLEM_AWARE

        # Example 2: SOLUTION_AWARE thread
        text2 = """
        There are 3 ways to grow your audience:

        1. Post consistently (most people do this)
        2. Engage with others (some people do this)
        3. Use AI to find trending topics (almost nobody does this)

        Here's how the 3rd approach works:
        - AI scans thousands of posts
        - Identifies emerging patterns
        - Surfaces high-demand topics
        - Gives you a brief to work from

        Case study: @founder went from 200 to 20K followers in 6 months using this.
        """
        result2 = classifier.classify(text2)
        assert result2.level == AwarenessLevel.SOLUTION_AWARE

        # Example 3: MOST_AWARE offer
        text3 = """
        Get TrendScout for $29/month

        ✅ Real-time trend alerts
        ✅ AI-powered content briefs
        ✅ Engagement analytics
        ✅ 14-day free trial
        ✅ Cancel anytime

        Join 1,000+ creators who've 10x'd their reach.

        Start free today: trendscout.app
        """
        result3 = classifier.classify(text3)
        assert result3.level == AwarenessLevel.MOST_AWARE

    def test_edge_cases(self, classifier):
        """Test edge cases and boundary conditions"""

        # Very short text
        result1 = classifier.classify("Buy now!")
        assert result1.level == AwarenessLevel.MOST_AWARE

        # Very long text
        long_text = "This is a story. " * 100 + "Take our quiz!"
        result2 = classifier.classify(long_text)
        assert result2.confidence > 0.0

        # Text with special characters
        result3 = classifier.classify("Struggling with 💡 ideas?")
        assert result3.level == AwarenessLevel.PROBLEM_AWARE

        # All caps
        result4 = classifier.classify("SIGN UP NOW FOR FREE TRIAL")
        assert result4.level == AwarenessLevel.MOST_AWARE


class TestAwarenessScoreDataclass:
    """Test AwarenessScore dataclass"""

    def test_to_dict(self):
        """Test to_dict method"""
        from services.awareness_classifier import AwarenessScore

        score = AwarenessScore(
            level=AwarenessLevel.PROBLEM_AWARE,
            confidence=0.75,
            scores={"unaware": 0.1, "problem_aware": 0.75}
        )

        result = score.to_dict()
        assert result["level"] == "problem_aware"
        assert result["confidence"] == 0.75
        assert "scores" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
