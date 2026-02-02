"""
Tests for Meta Ads Testing Services (AD-001 to AD-008)
=====================================================
Tests transcript extraction, variation generation, batch rendering,
campaign deployment, performance tracking, AI learning, campaign management,
and dynamic creative optimization.
"""
import pytest
from unittest.mock import patch
import importlib


# Reset singletons before each test module
def reset_singletons():
    """Reset all ad_testing singletons for clean tests."""
    import Backend.services.ad_testing.transcript_extractor as te
    import Backend.services.ad_testing.variation_generator as vg
    import Backend.services.ad_testing.batch_renderer as br
    import Backend.services.ad_testing.campaign_deployer as cd
    import Backend.services.ad_testing.performance_tracker as pt
    import Backend.services.ad_testing.ai_learner as al
    import Backend.services.ad_testing.campaign_manager as cm
    import Backend.services.ad_testing.dco_optimizer as dco
    for mod in [te, vg, br, cd, pt, al, cm, dco]:
        for attr in dir(mod):
            if attr.startswith("_instance") or attr.startswith("_singleton"):
                setattr(mod, attr, None)


@pytest.fixture(autouse=True)
def clean_singletons():
    """Reset singletons before each test."""
    reset_singletons()
    yield
    reset_singletons()


# ============================================================
# AD-001: Transcript Element Extraction
# ============================================================
class TestAD001_TranscriptExtraction:
    """Tests for TranscriptElementExtractor (AD-001)."""

    def test_extract_elements_returns_dict(self):
        from Backend.services.ad_testing import get_extractor
        extractor = get_extractor()
        transcript = "Stop scrolling! Are you tired of wasting money on ads that don't convert? Our tool saves you 10 hours per week. Join 5000+ marketers. Click the link below to get started!"
        result = extractor.extract_elements(transcript)
        assert isinstance(result, dict)
        assert "hooks" in result
        assert "ctas" in result

    def test_extract_hooks(self):
        from Backend.services.ad_testing import get_extractor
        extractor = get_extractor()
        transcript = "Stop scrolling! Wait, you need to hear this. Are you tired of losing money?"
        hooks = extractor.extract_hooks(transcript)
        assert isinstance(hooks, list)
        assert len(hooks) > 0

    def test_extract_pain_points(self):
        from Backend.services.ad_testing import get_extractor
        extractor = get_extractor()
        transcript = "Tired of wasting money on ads? Struggling to get results? Frustrated with low engagement?"
        points = extractor.extract_pain_points(transcript)
        assert isinstance(points, list)

    def test_extract_ctas(self):
        from Backend.services.ad_testing import get_extractor
        extractor = get_extractor()
        transcript = "Click the link below! Sign up today! Don't miss out - grab your spot now!"
        ctas = extractor.extract_ctas(transcript)
        assert isinstance(ctas, list)

    def test_extract_benefits(self):
        from Backend.services.ad_testing import get_extractor
        extractor = get_extractor()
        transcript = "Save 10 hours per week. Increase your ROAS by 3x. Cut ad spend in half."
        benefits = extractor.extract_benefits(transcript)
        assert isinstance(benefits, list)

    def test_extract_social_proofs(self):
        from Backend.services.ad_testing import get_extractor
        extractor = get_extractor()
        transcript = "Join 5000+ marketers who trust us. Featured in Forbes. 4.9 star rating."
        proofs = extractor.extract_social_proofs(transcript)
        assert isinstance(proofs, list)

    def test_extract_empty_transcript(self):
        from Backend.services.ad_testing import get_extractor
        extractor = get_extractor()
        result = extractor.extract_elements("")
        assert isinstance(result, dict)

    def test_singleton_pattern(self):
        from Backend.services.ad_testing import get_extractor
        a = get_extractor()
        b = get_extractor()
        assert a is b


# ============================================================
# AD-002: Ad Variation Generator
# ============================================================
class TestAD002_VariationGenerator:
    """Tests for AdVariationGenerator (AD-002)."""

    def _sample_elements(self):
        return {
            "hooks": ["Stop scrolling!", "Wait, you need to see this"],
            "pain_points": ["Wasting money on ads", "Low engagement"],
            "benefits": ["Save 10 hours/week", "3x ROAS improvement"],
            "ctas": ["Click the link", "Sign up now"],
            "social_proofs": ["5000+ marketers", "Featured in Forbes"],
        }

    def test_generate_variations_matrix(self):
        from Backend.services.ad_testing import get_variation_generator
        gen = get_variation_generator()
        variations = gen.generate_variations(self._sample_elements(), strategy="matrix")
        assert isinstance(variations, list)
        assert len(variations) > 0

    def test_generate_variations_hook_swap(self):
        from Backend.services.ad_testing import get_variation_generator
        gen = get_variation_generator()
        variations = gen.generate_variations(self._sample_elements(), strategy="hook_swap")
        assert isinstance(variations, list)
        assert len(variations) > 0

    def test_generate_variations_cta_swap(self):
        from Backend.services.ad_testing import get_variation_generator
        gen = get_variation_generator()
        variations = gen.generate_variations(self._sample_elements(), strategy="cta_swap")
        assert isinstance(variations, list)
        assert len(variations) > 0

    def test_variation_has_required_fields(self):
        from Backend.services.ad_testing import get_variation_generator
        gen = get_variation_generator()
        variations = gen.generate_variations(self._sample_elements(), strategy="matrix", max_variations=5)
        for var in variations:
            assert "id" in var
            assert "strategy" in var

    def test_max_variations_respected(self):
        from Backend.services.ad_testing import get_variation_generator
        gen = get_variation_generator()
        variations = gen.generate_variations(self._sample_elements(), strategy="matrix", max_variations=3)
        assert len(variations) <= 3

    def test_platforms_expansion(self):
        from Backend.services.ad_testing import get_variation_generator
        gen = get_variation_generator()
        variations = gen.generate_variations(
            self._sample_elements(),
            strategy="hook_swap",
            platforms=["facebook", "instagram"],
            max_variations=20,
        )
        assert isinstance(variations, list)

    def test_singleton_pattern(self):
        from Backend.services.ad_testing import get_variation_generator
        a = get_variation_generator()
        b = get_variation_generator()
        assert a is b


# ============================================================
# AD-003: Batch Video Rendering
# ============================================================
class TestAD003_BatchRenderer:
    """Tests for AdBatchRenderer (AD-003)."""

    def _sample_variations(self):
        return [
            {"id": "var_1", "headline": "Save Time", "body": "Our tool helps", "cta": "Sign up", "hook": "Stop!", "strategy": "matrix", "platform": "facebook"},
            {"id": "var_2", "headline": "Boost ROAS", "body": "3x results", "cta": "Click now", "hook": "Wait!", "strategy": "matrix", "platform": "instagram"},
        ]

    def test_create_batch(self):
        from Backend.services.ad_testing import get_batch_renderer
        renderer = get_batch_renderer()
        batch_id = renderer.create_batch(self._sample_variations())
        assert isinstance(batch_id, str)
        assert len(batch_id) > 0

    def test_render_batch(self):
        from Backend.services.ad_testing import get_batch_renderer
        renderer = get_batch_renderer()
        batch_id = renderer.create_batch(self._sample_variations())
        result = renderer.render_batch(batch_id)
        assert isinstance(result, dict)
        assert "status" in result or "rendered" in result or "batch_id" in result

    def test_get_batch_status(self):
        from Backend.services.ad_testing import get_batch_renderer
        renderer = get_batch_renderer()
        batch_id = renderer.create_batch(self._sample_variations())
        status = renderer.get_batch_status(batch_id)
        assert isinstance(status, dict)

    def test_list_batches(self):
        from Backend.services.ad_testing import get_batch_renderer
        renderer = get_batch_renderer()
        renderer.create_batch(self._sample_variations())
        batches = renderer.list_batches()
        assert isinstance(batches, list)
        assert len(batches) >= 1

    def test_singleton_pattern(self):
        from Backend.services.ad_testing import get_batch_renderer
        a = get_batch_renderer()
        b = get_batch_renderer()
        assert a is b


# ============================================================
# AD-004: Meta Ads Campaign Deployment
# ============================================================
class TestAD004_CampaignDeployer:
    """Tests for MetaCampaignDeployer (AD-004)."""

    def test_create_campaign(self):
        from Backend.services.ad_testing import get_campaign_deployer
        deployer = get_campaign_deployer()
        result = deployer.create_campaign("Test Campaign", "CONVERSIONS", 5000)
        assert isinstance(result, dict)
        assert "id" in result

    def test_create_campaign_with_variations(self):
        from Backend.services.ad_testing import get_campaign_deployer
        deployer = get_campaign_deployer()
        variations = [
            {"id": "v1", "headline": "Test", "body": "Body", "cta": "LEARN_MORE", "hook": "Hey!"},
        ]
        result = deployer.create_campaign("Test", "CONVERSIONS", 5000, ad_variations=variations)
        assert isinstance(result, dict)
        assert "id" in result

    def test_create_ad_set(self):
        from Backend.services.ad_testing import get_campaign_deployer
        deployer = get_campaign_deployer()
        campaign = deployer.create_campaign("Test", "CONVERSIONS", 5000)
        ad_set = deployer.create_ad_set(
            campaign["id"],
            audience={"age_min": 18, "age_max": 45, "interests": ["marketing"]},
            budget_cents=2500,
        )
        assert isinstance(ad_set, dict)
        assert "id" in ad_set

    def test_create_ad(self):
        from Backend.services.ad_testing import get_campaign_deployer
        deployer = get_campaign_deployer()
        campaign = deployer.create_campaign("Test", "CONVERSIONS", 5000)
        ad_set = deployer.create_ad_set(
            campaign["id"],
            audience={"age_min": 18, "age_max": 45},
            budget_cents=2500,
        )
        ad = deployer.create_ad(ad_set["id"], "creative_123", "Headline", "Body text")
        assert isinstance(ad, dict)
        assert "id" in ad

    def test_list_campaigns(self):
        from Backend.services.ad_testing import get_campaign_deployer
        deployer = get_campaign_deployer()
        deployer.create_campaign("Test1", "CONVERSIONS", 5000)
        campaigns = deployer.list_campaigns()
        assert isinstance(campaigns, list)
        assert len(campaigns) >= 1

    def test_get_campaign(self):
        from Backend.services.ad_testing import get_campaign_deployer
        deployer = get_campaign_deployer()
        campaign = deployer.create_campaign("Test", "CONVERSIONS", 5000)
        found = deployer.get_campaign(campaign["id"])
        assert found is not None
        assert found["id"] == campaign["id"]

    def test_update_campaign_status(self):
        from Backend.services.ad_testing import get_campaign_deployer
        deployer = get_campaign_deployer()
        campaign = deployer.create_campaign("Test", "CONVERSIONS", 5000)
        result = deployer.update_campaign_status(campaign["id"], "PAUSED")
        assert result is True

    def test_singleton_pattern(self):
        from Backend.services.ad_testing import get_campaign_deployer
        a = get_campaign_deployer()
        b = get_campaign_deployer()
        assert a is b


# ============================================================
# AD-005: Meta Ads Performance Tracking
# ============================================================
class TestAD005_PerformanceTracker:
    """Tests for MetaAdsPerformanceTracker (AD-005)."""

    def test_track_impression(self):
        from Backend.services.ad_testing import get_performance_tracker
        tracker = get_performance_tracker()
        tracker.track_impression("ad_001")
        metrics = tracker.get_ad_metrics("ad_001")
        assert metrics["impressions"] >= 1

    def test_track_click(self):
        from Backend.services.ad_testing import get_performance_tracker
        tracker = get_performance_tracker()
        tracker.track_impression("ad_002")
        tracker.track_click("ad_002")
        metrics = tracker.get_ad_metrics("ad_002")
        assert metrics["clicks"] >= 1

    def test_get_ad_metrics_ctr(self):
        from Backend.services.ad_testing import get_performance_tracker
        tracker = get_performance_tracker()
        for _ in range(100):
            tracker.track_impression("ad_003")
        for _ in range(5):
            tracker.track_click("ad_003")
        metrics = tracker.get_ad_metrics("ad_003")
        assert metrics["impressions"] == 100
        assert metrics["clicks"] == 5
        assert metrics["ctr"] == pytest.approx(5.0, abs=0.5)

    def test_calculate_hook_rate(self):
        from Backend.services.ad_testing import get_performance_tracker
        tracker = get_performance_tracker()
        tracker.track_impression("ad_004")
        rate = tracker.calculate_hook_rate("ad_004")
        assert isinstance(rate, float)

    def test_calculate_hold_rate(self):
        from Backend.services.ad_testing import get_performance_tracker
        tracker = get_performance_tracker()
        tracker.track_impression("ad_005")
        rate = tracker.calculate_hold_rate("ad_005")
        assert isinstance(rate, float)

    def test_reset_ad_metrics(self):
        from Backend.services.ad_testing import get_performance_tracker
        tracker = get_performance_tracker()
        tracker.track_impression("ad_006")
        tracker.reset_ad_metrics("ad_006")
        metrics = tracker.get_ad_metrics("ad_006")
        assert metrics["impressions"] == 0

    def test_get_event_count(self):
        from Backend.services.ad_testing import get_performance_tracker
        tracker = get_performance_tracker()
        tracker.track_impression("ad_007")
        tracker.track_click("ad_007")
        count = tracker.get_event_count()
        assert count >= 2

    def test_singleton_pattern(self):
        from Backend.services.ad_testing import get_performance_tracker
        a = get_performance_tracker()
        b = get_performance_tracker()
        assert a is b


# ============================================================
# AD-006: AI Learning & Recommendations
# ============================================================
class TestAD006_AILearner:
    """Tests for AdAILearner (AD-006)."""

    def _setup_campaign_data(self):
        """Set up campaign with tracked performance data."""
        from Backend.services.ad_testing import get_campaign_deployer, get_performance_tracker
        deployer = get_campaign_deployer()
        tracker = get_performance_tracker()
        campaign = deployer.create_campaign("AI Test", "CONVERSIONS", 10000)
        ad_set = deployer.create_ad_set(
            campaign["id"],
            audience={"age_min": 18, "age_max": 45},
            budget_cents=5000,
        )
        ad1 = deployer.create_ad(ad_set["id"], "c1", "Good Ad", "Body", cta_type="LEARN_MORE")
        ad2 = deployer.create_ad(ad_set["id"], "c2", "Bad Ad", "Body", cta_type="SIGN_UP")
        # Good ad: high CTR
        for _ in range(100):
            tracker.track_impression(ad1["id"])
        for _ in range(10):
            tracker.track_click(ad1["id"])
        # Bad ad: low CTR
        for _ in range(100):
            tracker.track_impression(ad2["id"])
        for _ in range(1):
            tracker.track_click(ad2["id"])
        return campaign["id"]

    def test_analyze_results(self):
        from Backend.services.ad_testing import get_ai_learner
        learner = get_ai_learner()
        campaign_id = self._setup_campaign_data()
        result = learner.analyze_results(campaign_id)
        assert isinstance(result, dict)

    def test_identify_winning_patterns(self):
        from Backend.services.ad_testing import get_ai_learner, get_performance_tracker
        learner = get_ai_learner()
        tracker = get_performance_tracker()
        # Track some data
        for _ in range(200):
            tracker.track_impression("pattern_ad_1")
        for _ in range(20):
            tracker.track_click("pattern_ad_1")
        metrics = [tracker.get_ad_metrics("pattern_ad_1")]
        patterns = learner.identify_winning_patterns(metrics)
        assert isinstance(patterns, list)

    def test_generate_next_test_suggestions(self):
        from Backend.services.ad_testing import get_ai_learner
        learner = get_ai_learner()
        campaign_id = self._setup_campaign_data()
        suggestions = learner.generate_next_test_suggestions(campaign_id)
        assert isinstance(suggestions, list)

    def test_get_audience_insights(self):
        from Backend.services.ad_testing import get_ai_learner
        learner = get_ai_learner()
        campaign_id = self._setup_campaign_data()
        insights = learner.get_audience_insights(campaign_id)
        assert isinstance(insights, dict)

    def test_singleton_pattern(self):
        from Backend.services.ad_testing import get_ai_learner
        a = get_ai_learner()
        b = get_ai_learner()
        assert a is b


# ============================================================
# AD-007: Meta Ads Campaign Management
# ============================================================
class TestAD007_CampaignManager:
    """Tests for MetaCampaignManager (AD-007)."""

    def _setup_campaign(self):
        from Backend.services.ad_testing import get_campaign_deployer, get_performance_tracker
        deployer = get_campaign_deployer()
        tracker = get_performance_tracker()
        campaign = deployer.create_campaign("Managed", "CONVERSIONS", 10000)
        ad_set = deployer.create_ad_set(
            campaign["id"],
            audience={"age_min": 18, "age_max": 45},
            budget_cents=5000,
        )
        ad1 = deployer.create_ad(ad_set["id"], "c1", "Winner", "Great body")
        ad2 = deployer.create_ad(ad_set["id"], "c2", "Loser", "Bad body")
        # Winner: high CTR
        for _ in range(200):
            tracker.track_impression(ad1["id"])
        for _ in range(20):
            tracker.track_click(ad1["id"])
        # Loser: very low CTR
        for _ in range(200):
            tracker.track_impression(ad2["id"])
        for _ in range(1):
            tracker.track_click(ad2["id"])
        return campaign["id"], ad_set["id"]

    def test_pause_underperformers(self):
        from Backend.services.ad_testing import get_campaign_manager
        manager = get_campaign_manager()
        campaign_id, _ = self._setup_campaign()
        paused = manager.pause_underperformers(campaign_id)
        assert isinstance(paused, list)

    def test_scale_winners(self):
        from Backend.services.ad_testing import get_campaign_manager
        manager = get_campaign_manager()
        campaign_id, _ = self._setup_campaign()
        scaled = manager.scale_winners(campaign_id)
        assert isinstance(scaled, list)

    def test_duplicate_ad_set(self):
        from Backend.services.ad_testing import get_campaign_manager, get_campaign_deployer
        deployer = get_campaign_deployer()
        manager = get_campaign_manager()
        # Ensure manager uses same deployer instance
        manager._deployer = deployer
        _, ad_set_id = self._setup_campaign()
        new_id = manager.duplicate_ad_set(ad_set_id)
        assert isinstance(new_id, str)
        assert len(new_id) > 0

    def test_get_campaign_health(self):
        from Backend.services.ad_testing import get_campaign_manager
        manager = get_campaign_manager()
        campaign_id, _ = self._setup_campaign()
        health = manager.get_campaign_health(campaign_id)
        assert isinstance(health, dict)

    def test_get_action_log(self):
        from Backend.services.ad_testing import get_campaign_manager
        manager = get_campaign_manager()
        campaign_id, _ = self._setup_campaign()
        manager.pause_underperformers(campaign_id)
        log = manager.get_action_log(campaign_id)
        assert isinstance(log, list)

    def test_singleton_pattern(self):
        from Backend.services.ad_testing import get_campaign_manager
        a = get_campaign_manager()
        b = get_campaign_manager()
        assert a is b


# ============================================================
# AD-008: Dynamic Creative Optimization
# ============================================================
class TestAD008_DCOOptimizer:
    """Tests for DynamicCreativeOptimizer (AD-008)."""

    def test_create_dco_campaign(self):
        from Backend.services.ad_testing import get_dco_optimizer
        dco = get_dco_optimizer()
        campaign_id = dco.create_dco_campaign(
            videos=["video1.mp4", "video2.mp4"],
            texts=["Save time", "Boost ROAS"],
            headlines=["The #1 Tool", "Stop Wasting Money"],
            ctas=["LEARN_MORE", "SIGN_UP"],
        )
        assert isinstance(campaign_id, str)
        assert len(campaign_id) > 0

    def test_get_winning_combinations(self):
        from Backend.services.ad_testing import get_dco_optimizer
        dco = get_dco_optimizer()
        cid = dco.create_dco_campaign(
            videos=["v1.mp4"], texts=["text1"], headlines=["h1"], ctas=["LEARN_MORE"],
        )
        # Record some data
        campaign = dco.get_campaign(cid)
        if campaign and "combinations" in campaign:
            for combo in campaign["combinations"][:2]:
                for _ in range(50):
                    dco.record_combo_impression(combo["combo_id"])
                for _ in range(5):
                    dco.record_combo_click(combo["combo_id"])
        winners = dco.get_winning_combinations(cid)
        assert isinstance(winners, list)

    def test_auto_optimize(self):
        from Backend.services.ad_testing import get_dco_optimizer
        dco = get_dco_optimizer()
        cid = dco.create_dco_campaign(
            videos=["v1.mp4", "v2.mp4"],
            texts=["t1", "t2"],
            headlines=["h1", "h2"],
            ctas=["LEARN_MORE", "SIGN_UP"],
        )
        campaign = dco.get_campaign(cid)
        if campaign and "combinations" in campaign:
            combos = campaign["combinations"]
            # Good combo
            for _ in range(100):
                dco.record_combo_impression(combos[0]["combo_id"])
            for _ in range(15):
                dco.record_combo_click(combos[0]["combo_id"])
            # Bad combo
            if len(combos) > 1:
                for _ in range(100):
                    dco.record_combo_impression(combos[1]["combo_id"])
                for _ in range(1):
                    dco.record_combo_click(combos[1]["combo_id"])
        result = dco.auto_optimize(cid)
        assert isinstance(result, dict)

    def test_get_creative_performance(self):
        from Backend.services.ad_testing import get_dco_optimizer
        dco = get_dco_optimizer()
        cid = dco.create_dco_campaign(
            videos=["v1.mp4"], texts=["t1"], headlines=["h1"], ctas=["CTA1"],
        )
        perf = dco.get_creative_performance(cid)
        assert isinstance(perf, dict)

    def test_list_campaigns(self):
        from Backend.services.ad_testing import get_dco_optimizer
        dco = get_dco_optimizer()
        dco.create_dco_campaign(
            videos=["v1.mp4"], texts=["t1"], headlines=["h1"], ctas=["CTA1"],
        )
        campaigns = dco.list_campaigns()
        assert isinstance(campaigns, list)
        assert len(campaigns) >= 1

    def test_record_combo_impression(self):
        from Backend.services.ad_testing import get_dco_optimizer
        dco = get_dco_optimizer()
        cid = dco.create_dco_campaign(
            videos=["v1.mp4"], texts=["t1"], headlines=["h1"], ctas=["CTA1"],
        )
        campaign = dco.get_campaign(cid)
        if campaign and "combinations" in campaign and len(campaign["combinations"]) > 0:
            combo_id = campaign["combinations"][0]["combo_id"]
            dco.record_combo_impression(combo_id)
            # No exception = success

    def test_singleton_pattern(self):
        from Backend.services.ad_testing import get_dco_optimizer
        a = get_dco_optimizer()
        b = get_dco_optimizer()
        assert a is b
