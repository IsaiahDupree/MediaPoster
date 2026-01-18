"""
FATE Scoring Tests
==================
OPS-001: Tests for FATE framework scoring service

Tests all four elements:
- Focus (F): Pattern interrupts, curiosity gaps, stakes
- Authority (A): Numbers, proof, mechanisms
- Tribe (T): Identity markers, us-vs-them
- Emotion (E): Story beats, contrast, loss aversion, hope
"""

import pytest
from services.fate_scorer import FATEScorer, get_fate_scorer


@pytest.fixture
def scorer():
    """Create a fresh FATE scorer instance"""
    return FATEScorer()


class TestFocusScoring:
    """Test Focus element detection"""

    def test_detect_focus_hook_most_fail(self, scorer):
        """Test detection of 'most X fail' pattern"""
        text = "Most founders fail at validation because they ask the wrong question."
        score = scorer.score_focus(text)
        assert score > 0.5, f"Expected focus score > 0.5, got {score}"

    def test_detect_focus_what_if(self, scorer):
        """Test detection of 'what if' curiosity gap"""
        text = "What if everything you know about marketing is backwards?"
        score = scorer.score_focus(text)
        assert score > 0.4, f"Expected focus score > 0.4, got {score}"

    def test_detect_focus_pattern_interrupt(self, scorer):
        """Test detection of pattern interrupt"""
        text = "Stop trying to build an audience. Build a signal instead."
        score = scorer.score_focus(text)
        assert score > 0.4, f"Expected focus score > 0.4, got {score}"

    def test_weak_hook(self, scorer):
        """Test weak/generic opening has low focus score"""
        text = "Today I want to talk about some interesting things I learned recently."
        score = scorer.score_focus(text)
        assert score < 0.3, f"Expected focus score < 0.3 for weak hook, got {score}"

    def test_no_hook(self, scorer):
        """Test content with no hook scores low"""
        text = "We implemented the feature and it works well."
        score = scorer.score_focus(text)
        assert score < 0.3, f"Expected focus score < 0.3 for no hook, got {score}"


class TestAuthorityScoring:
    """Test Authority element detection"""

    def test_detect_authority_proof_with_numbers(self, scorer):
        """Test detection of numerical proof"""
        text = "I've helped 127 founders validate their ideas in the past 3 years."
        score = scorer.score_authority(text)
        assert score > 0.6, f"Expected authority score > 0.6, got {score}"

    def test_detect_authority_mechanism(self, scorer):
        """Test detection of mechanism explanation"""
        text = "Here's how the pattern works: First you identify the friction, then you quantify the cost."
        score = scorer.score_authority(text)
        assert score > 0.5, f"Expected authority score > 0.5, got {score}"

    def test_detect_authority_data(self, scorer):
        """Test detection of data/research references"""
        text = "The data shows that 78% of founders validate too late. After testing this with 50+ startups, the pattern is clear."
        score = scorer.score_authority(text)
        assert score > 0.7, f"Expected authority score > 0.7, got {score}"

    def test_missing_authority(self, scorer):
        """Test content without authority scores low"""
        text = "I think this might work. Maybe we should try it sometime."
        score = scorer.score_authority(text)
        assert score < 0.3, f"Expected authority score < 0.3, got {score}"


class TestTribeScoring:
    """Test Tribe element detection"""

    def test_detect_tribe_identity(self, scorer):
        """Test detection of identity-based language"""
        text = "If you're a bootstrapper, you've felt this pain. The VCs won't tell you this."
        score = scorer.score_tribe(text)
        assert score > 0.5, f"Expected tribe score > 0.5, got {score}"

    def test_detect_tribe_us_vs_them(self, scorer):
        """Test detection of us-vs-them framing"""
        text = "People like us don't need permission. While others wait for funding, we ship."
        score = scorer.score_tribe(text)
        assert score > 0.6, f"Expected tribe score > 0.6, got {score}"

    def test_detect_tribe_second_person(self, scorer):
        """Test detection of second-person engagement"""
        text = "You and I both know the real problem isn't the code. For founders who've been there, this hits different."
        score = scorer.score_tribe(text)
        assert score > 0.5, f"Expected tribe score > 0.5, got {score}"

    def test_missing_tribe(self, scorer):
        """Test content without tribe markers scores low"""
        text = "The solution was implemented successfully. It performs well in production."
        score = scorer.score_tribe(text)
        assert score < 0.3, f"Expected tribe score < 0.3, got {score}"


class TestEmotionScoring:
    """Test Emotion element detection"""

    def test_detect_emotion_story(self, scorer):
        """Test detection of story beats"""
        text = "I was broke, desperate, 6 months from shutting down. I wasted $40k on the wrong solution."
        score = scorer.score_emotion(text)
        assert score > 0.6, f"Expected emotion score > 0.6, got {score}"

    def test_detect_emotion_transformation(self, scorer):
        """Test detection of transformation narrative"""
        text = "Then everything changed. I finally realized the pattern. It transformed my entire approach."
        score = scorer.score_emotion(text)
        assert score > 0.5, f"Expected emotion score > 0.5, got {score}"

    def test_detect_emotion_vivid_language(self, scorer):
        """Test detection of vivid emotional language"""
        text = "Imagine waking up to 100 signups. Picture the relief when you finally crack the code. Feel the frustration melt away."
        score = scorer.score_emotion(text)
        assert score > 0.5, f"Expected emotion score > 0.5, got {score}"

    def test_missing_emotion(self, scorer):
        """Test content without emotion scores low"""
        text = "We updated the documentation and released version 2.0. Users can now access the new features."
        score = scorer.score_emotion(text)
        assert score < 0.3, f"Expected emotion score < 0.3, got {score}"


class TestCombinedScoring:
    """Test combined FATE scoring"""

    def test_combined_fate_balanced(self, scorer):
        """Test well-balanced FATE content scores high on all elements"""
        text = """Most founders fail at validation because they ask the wrong question.

After helping 127 founders, I found the real pattern. Here's how it works:

If you're bootstrapping, you've felt this pain. People like us can't afford to waste time.

I was there too. Broke, desperate, 6 months from failure. Then I discovered the one question that changed everything."""

        scores = scorer.score_all(text)

        assert scores["F"] > 0.4, f"Expected F > 0.4, got {scores['F']}"
        assert scores["A"] > 0.4, f"Expected A > 0.4, got {scores['A']}"
        assert scores["T"] > 0.4, f"Expected T > 0.4, got {scores['T']}"
        assert scores["E"] > 0.4, f"Expected E > 0.4, got {scores['E']}"

    def test_score_all_returns_dict(self, scorer):
        """Test score_all returns proper dictionary format"""
        text = "Some test content here"
        scores = scorer.score_all(text)

        assert isinstance(scores, dict)
        assert set(scores.keys()) == {"F", "A", "T", "E"}
        assert all(0.0 <= score <= 1.0 for score in scores.values())

    def test_empty_text_returns_zeros(self, scorer):
        """Test empty text returns zero scores"""
        scores = scorer.score_all("")

        assert scores["F"] == 0.0
        assert scores["A"] == 0.0
        assert scores["T"] == 0.0
        assert scores["E"] == 0.0

    def test_high_focus_low_authority(self, scorer):
        """Test content can score high on one element, low on another"""
        text = "What if everything you know is wrong? Stop trying to build an audience!"

        scores = scorer.score_all(text)

        assert scores["F"] > 0.4, "Should have high focus"
        assert scores["A"] < 0.3, "Should have low authority"

    def test_authority_heavy_educational_content(self, scorer):
        """Test educational content scores high on Authority"""
        text = """Here's how the mechanism works, based on testing with 89 companies.

The data shows 67% improvement when you follow this 3-step process.
After 5 years of research, the pattern is crystal clear."""

        scores = scorer.score_all(text)

        assert scores["A"] > 0.6, "Educational content should score high on Authority"

    def test_tribe_heavy_community_content(self, scorer):
        """Test community-focused content scores high on Tribe"""
        text = """If you're a founder, you know this struggle.

People like us don't wait for permission. We builders ship.
For bootstrappers who've been in the trenches, this resonates."""

        scores = scorer.score_all(text)

        assert scores["T"] > 0.6, "Community content should score high on Tribe"


class TestSingletonInstance:
    """Test singleton pattern for scorer"""

    def test_get_fate_scorer_returns_instance(self):
        """Test get_fate_scorer returns FATEScorer instance"""
        scorer = get_fate_scorer()
        assert isinstance(scorer, FATEScorer)

    def test_get_fate_scorer_returns_same_instance(self):
        """Test get_fate_scorer returns singleton"""
        scorer1 = get_fate_scorer()
        scorer2 = get_fate_scorer()
        assert scorer1 is scorer2


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_none_text(self, scorer):
        """Test None text is handled gracefully"""
        # Should not crash, should return 0.0
        score = scorer.score_focus(None)
        assert score == 0.0

    def test_very_long_text(self, scorer):
        """Test scoring works with very long text"""
        text = " ".join(["Most founders fail because of validation issues."] * 100)
        scores = scorer.score_all(text)

        # Should still return valid scores
        assert all(0.0 <= score <= 1.0 for score in scores.values())

    def test_special_characters(self, scorer):
        """Test special characters don't break scoring"""
        text = "What if… the *real* problem is validation? Here's why: 100% of founders need it!"
        scores = scorer.score_all(text)

        assert all(0.0 <= score <= 1.0 for score in scores.values())

    def test_unicode_text(self, scorer):
        """Test unicode characters are handled"""
        text = "Most founders fail 🚀 because they don't validate. I've helped 127 builders ✨"
        scores = scorer.score_all(text)

        assert all(0.0 <= score <= 1.0 for score in scores.values())


class TestRealWorldExamples:
    """Test with real-world content examples"""

    def test_educational_thread(self, scorer):
        """Test typical educational Twitter thread"""
        text = """Most founders fail at pricing because they anchor to cost.

Here's the real pattern I found after helping 127 companies:

Price = Value Delivered × Willingness to Pay × Urgency

Not cost + margin.

If you're bootstrapping, this is the unlock you need."""

        scores = scorer.score_all(text)

        assert scores["F"] > 0.5, "Educational threads should have strong focus"
        assert scores["A"] > 0.5, "Should have authority (mechanism + numbers)"
        assert scores["T"] > 0.3, "Should have some tribe element"

    def test_story_based_content(self, scorer):
        """Test story-driven content"""
        text = """I was 6 months from bankruptcy. Desperate. Broken.

Then I discovered one question that changed everything.

If you've felt this pain, you know what I mean.

The data from 89 founders proved it: this one shift increased conversions by 340%."""

        scores = scorer.score_all(text)

        assert scores["E"] > 0.6, "Story content should score high on Emotion"
        assert scores["A"] > 0.4, "Should have authority (data)"
        assert scores["T"] > 0.4, "Should have tribe (shared pain)"
