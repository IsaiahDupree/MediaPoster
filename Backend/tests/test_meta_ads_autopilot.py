"""
Tests for Meta Ads Autopilot Service (META-001 through META-008)
================================================================
"""
import pytest
from datetime import datetime, timezone


# ============================================================================
# META-001: Meta Marketing API Client
# ============================================================================

class TestMETA001_MarketingAPIClient:
    """META-001: Meta Marketing API Client"""

    def test_client_initialization(self):
        """META-001: Client should initialize with default config."""
        from services.meta_ads_autopilot import MetaMarketingClient
        client = MetaMarketingClient()
        assert client is not None
        assert client._request_count == 0

    def test_client_config(self):
        """META-001: MetaAPIConfig should have correct fields."""
        from services.meta_ads_autopilot import MetaAPIConfig
        config = MetaAPIConfig(access_token="test_token", ad_account_id="act_123")
        assert config.is_configured is True
        assert config.api_version == "v19.0"

    def test_client_config_unconfigured(self):
        """META-001: Unconfigured client should report not configured."""
        from services.meta_ads_autopilot import MetaAPIConfig
        config = MetaAPIConfig()
        assert config.is_configured is False

    def test_client_singleton(self):
        """META-001: Singleton should return same instance."""
        from services.meta_ads_autopilot import get_meta_marketing_client
        c1 = get_meta_marketing_client()
        c2 = get_meta_marketing_client()
        assert c1 is c2

    @pytest.mark.asyncio
    async def test_create_campaign(self):
        """META-001: Should create campaign."""
        from services.meta_ads_autopilot import MetaMarketingClient
        client = MetaMarketingClient()
        campaign = await client.create_campaign("Test Campaign", "CONVERSIONS", 5000)
        assert campaign["id"].startswith("camp_")
        assert campaign["name"] == "Test Campaign"
        assert campaign["objective"] == "CONVERSIONS"
        assert campaign["daily_budget"] == 5000
        assert campaign["status"] == "PAUSED"

    @pytest.mark.asyncio
    async def test_create_ad_set(self):
        """META-001: Should create ad set within campaign."""
        from services.meta_ads_autopilot import MetaMarketingClient
        client = MetaMarketingClient()
        campaign = await client.create_campaign("Test", "TRAFFIC", 1000)
        ad_set = await client.create_ad_set(
            campaign_id=campaign["id"],
            name="Test Ad Set",
            targeting={"age_min": 18, "age_max": 65},
            daily_budget_cents=500,
        )
        assert ad_set["id"].startswith("adset_")
        assert ad_set["campaign_id"] == campaign["id"]

    @pytest.mark.asyncio
    async def test_create_ad(self):
        """META-001: Should create ad within ad set."""
        from services.meta_ads_autopilot import MetaMarketingClient
        client = MetaMarketingClient()
        campaign = await client.create_campaign("Test", "TRAFFIC", 1000)
        ad_set = await client.create_ad_set(campaign["id"], "AS1", {}, 500)
        creative = await client.upload_creative("/tmp/v.mp4", "Head", "Body")
        ad = await client.create_ad(ad_set["id"], "Ad1", creative["id"])
        assert ad["id"].startswith("ad_")
        assert ad["creative_id"] == creative["id"]

    @pytest.mark.asyncio
    async def test_list_campaigns(self):
        """META-001: Should list campaigns."""
        from services.meta_ads_autopilot import MetaMarketingClient
        client = MetaMarketingClient()
        await client.create_campaign("C1", "TRAFFIC", 1000)
        await client.create_campaign("C2", "REACH", 2000)
        campaigns = await client.list_campaigns()
        assert len(campaigns) == 2

    @pytest.mark.asyncio
    async def test_update_campaign_status(self):
        """META-001: Should update campaign status."""
        from services.meta_ads_autopilot import MetaMarketingClient
        client = MetaMarketingClient()
        campaign = await client.create_campaign("Test", "TRAFFIC", 1000)
        result = await client.update_campaign_status(campaign["id"], "ACTIVE")
        assert result is True
        updated = await client.get_campaign(campaign["id"])
        assert updated["status"] == "ACTIVE"

    def test_config_endpoint(self):
        """META-001: Config should generate correct endpoints."""
        from services.meta_ads_autopilot import MetaAPIConfig
        config = MetaAPIConfig()
        endpoint = config.get_endpoint("act_123/campaigns")
        assert "v19.0" in endpoint
        assert "act_123/campaigns" in endpoint

    def test_config_to_dict(self):
        """META-001: Config should serialize to dict."""
        from services.meta_ads_autopilot import MetaAPIConfig
        config = MetaAPIConfig(ad_account_id="act_123")
        d = config.to_dict()
        assert "ad_account_id" in d
        assert "is_configured" in d


# ============================================================================
# META-002: Ad Creative Variation Generator
# ============================================================================

class TestMETA002_VariationGenerator:
    """META-002: Ad Creative Variation Generator"""

    def test_generator_initialization(self):
        """META-002: Generator should initialize."""
        from services.meta_ads_autopilot import AdCreativeVariationGenerator
        gen = AdCreativeVariationGenerator()
        assert gen is not None

    def test_generator_singleton(self):
        """META-002: Singleton should return same instance."""
        from services.meta_ads_autopilot import get_ad_creative_variation_generator
        g1 = get_ad_creative_variation_generator()
        g2 = get_ad_creative_variation_generator()
        assert g1 is g2

    def test_generate_matrix_variations(self):
        """META-002: Matrix strategy should generate hook x CTA x pain_point combos."""
        from services.meta_ads_autopilot import AdCreativeVariationGenerator
        gen = AdCreativeVariationGenerator()
        variations = gen.generate_variations(
            hooks=["Hook A", "Hook B"],
            ctas=["CTA 1", "CTA 2"],
            pain_points=["Pain 1"],
            max_variations=100,
        )
        assert len(variations) == 4  # 2 x 2 x 1
        assert all("id" in v for v in variations)
        assert all("headline" in v for v in variations)

    def test_generate_max_limit(self):
        """META-002: Should respect max_variations limit."""
        from services.meta_ads_autopilot import AdCreativeVariationGenerator
        gen = AdCreativeVariationGenerator()
        variations = gen.generate_variations(
            hooks=[f"Hook {i}" for i in range(10)],
            ctas=[f"CTA {i}" for i in range(10)],
            pain_points=[f"Pain {i}" for i in range(10)],
            max_variations=50,
        )
        assert len(variations) == 50

    def test_hook_swap_variations(self):
        """META-002: Hook swap should keep body, swap hooks."""
        from services.meta_ads_autopilot import AdCreativeVariationGenerator
        gen = AdCreativeVariationGenerator()
        variations = gen.generate_hook_swap_variations(
            base_body="Check this out!",
            hooks=["Hook A", "Hook B", "Hook C"],
        )
        assert len(variations) == 3
        assert all(v["strategy"] == "hook_swap" for v in variations)
        assert all(v["body"] == "Check this out!" for v in variations)

    def test_cta_swap_variations(self):
        """META-002: CTA swap should keep body, swap CTAs."""
        from services.meta_ads_autopilot import AdCreativeVariationGenerator
        gen = AdCreativeVariationGenerator()
        variations = gen.generate_cta_swap_variations(
            base_body="Learn more",
            base_hook="Amazing!",
            ctas=["Buy now", "Sign up", "Get started"],
        )
        assert len(variations) == 3
        assert all(v["strategy"] == "cta_swap" for v in variations)

    def test_variation_count(self):
        """META-002: Should track total generated variations."""
        from services.meta_ads_autopilot import AdCreativeVariationGenerator
        gen = AdCreativeVariationGenerator()
        gen.generate_variations(["H1"], ["C1"], ["P1"])
        assert gen.get_variation_count() >= 1


# ============================================================================
# META-003: Batch Video Rendering
# ============================================================================

class TestMETA003_BatchRendering:
    """META-003: Batch Video Rendering"""

    def test_renderer_initialization(self):
        """META-003: Renderer should initialize with concurrency."""
        from services.meta_ads_autopilot import MetaBatchRenderer
        renderer = MetaBatchRenderer(max_concurrent=8)
        assert renderer.max_concurrent == 8

    def test_renderer_singleton(self):
        """META-003: Singleton should return same instance."""
        from services.meta_ads_autopilot import get_meta_batch_renderer
        r1 = get_meta_batch_renderer()
        r2 = get_meta_batch_renderer()
        assert r1 is r2

    def test_create_render_batch(self):
        """META-003: Should create batch from variations."""
        from services.meta_ads_autopilot import MetaBatchRenderer
        renderer = MetaBatchRenderer()
        variations = [
            {"id": "v1", "headline": "Test 1", "body": "Body 1"},
            {"id": "v2", "headline": "Test 2", "body": "Body 2"},
        ]
        batch_id = renderer.create_render_batch(variations)
        assert batch_id.startswith("render_")
        status = renderer.get_batch_status(batch_id)
        assert status["total"] == 2
        assert status["status"] == "pending"

    @pytest.mark.asyncio
    async def test_start_batch(self):
        """META-003: Should render batch and mark completed."""
        from services.meta_ads_autopilot import MetaBatchRenderer
        renderer = MetaBatchRenderer()
        batch_id = renderer.create_render_batch([
            {"id": "v1", "headline": "H1"},
        ])
        result = await renderer.start_batch(batch_id)
        assert result["status"] == "completed"
        assert result["completed"] == 1

    def test_list_batches(self):
        """META-003: Should list all batches."""
        from services.meta_ads_autopilot import MetaBatchRenderer
        renderer = MetaBatchRenderer()
        renderer.create_render_batch([{"id": "v1", "headline": "H"}])
        renderer.create_render_batch([{"id": "v2", "headline": "H"}])
        batches = renderer.list_batches()
        assert len(batches) == 2


# ============================================================================
# META-004: Meta Campaign Deployment
# ============================================================================

class TestMETA004_CampaignDeployment:
    """META-004: Meta Campaign Deployment"""

    def test_deployment_initialization(self):
        """META-004: Deployment should initialize."""
        from services.meta_ads_autopilot import MetaCampaignDeployment
        dep = MetaCampaignDeployment()
        assert dep is not None

    def test_deployment_singleton(self):
        """META-004: Singleton should return same instance."""
        from services.meta_ads_autopilot import get_meta_campaign_deployment
        d1 = get_meta_campaign_deployment()
        d2 = get_meta_campaign_deployment()
        assert d1 is d2

    @pytest.mark.asyncio
    async def test_deploy_test_campaign(self):
        """META-004: Should deploy a full test campaign."""
        from services.meta_ads_autopilot import MetaCampaignDeployment
        dep = MetaCampaignDeployment()
        variations = [
            {"id": "v1", "headline": "Test", "body": "Body", "output_path": "/tmp/v.mp4"},
        ]
        result = await dep.deploy_test_campaign(
            name="Test Campaign",
            variations=variations,
            targeting={"age_min": 18},
            daily_budget_cents=5000,
        )
        assert result["status"] == "deployed"
        assert result["ads_count"] == 1
        assert result["campaign_id"].startswith("camp_")

    @pytest.mark.asyncio
    async def test_list_deployments(self):
        """META-004: Should list deployments."""
        from services.meta_ads_autopilot import MetaCampaignDeployment
        dep = MetaCampaignDeployment()
        await dep.deploy_test_campaign("C1", [{"id": "v1", "headline": "H", "body": "B"}], {}, 1000)
        deployments = await dep.list_deployments()
        assert len(deployments) >= 1


# ============================================================================
# META-005: Meta Insights Fetcher
# ============================================================================

class TestMETA005_InsightsFetcher:
    """META-005: Meta Insights Fetcher"""

    def test_fetcher_initialization(self):
        """META-005: Fetcher should initialize."""
        from services.meta_ads_autopilot import MetaInsightsFetcher
        fetcher = MetaInsightsFetcher()
        assert fetcher.get_fetch_count() == 0

    def test_fetcher_singleton(self):
        """META-005: Singleton should return same instance."""
        from services.meta_ads_autopilot import get_meta_insights_fetcher
        f1 = get_meta_insights_fetcher()
        f2 = get_meta_insights_fetcher()
        assert f1 is f2

    @pytest.mark.asyncio
    async def test_fetch_campaign_insights(self):
        """META-005: Should fetch campaign insights."""
        from services.meta_ads_autopilot import MetaInsightsFetcher
        fetcher = MetaInsightsFetcher()
        insights = await fetcher.fetch_campaign_insights("camp_123")
        assert "impressions" in insights
        assert "cpm" in insights
        assert "cpc" in insights
        assert "ctr" in insights
        assert "roas" in insights
        assert insights["campaign_id"] == "camp_123"

    @pytest.mark.asyncio
    async def test_fetch_ad_insights(self):
        """META-005: Should fetch ad-level insights."""
        from services.meta_ads_autopilot import MetaInsightsFetcher
        fetcher = MetaInsightsFetcher()
        insights = await fetcher.fetch_ad_insights("ad_123")
        assert "hook_rate" in insights
        assert "hold_rate" in insights
        assert "video_views" in insights

    @pytest.mark.asyncio
    async def test_caching(self):
        """META-005: Should cache fetched insights."""
        from services.meta_ads_autopilot import MetaInsightsFetcher
        fetcher = MetaInsightsFetcher()
        await fetcher.fetch_campaign_insights("camp_456")
        cached = fetcher.get_cached_insights("camp_456")
        assert cached is not None
        assert cached["campaign_id"] == "camp_456"

    @pytest.mark.asyncio
    async def test_fetch_count(self):
        """META-005: Should track fetch count."""
        from services.meta_ads_autopilot import MetaInsightsFetcher
        fetcher = MetaInsightsFetcher()
        await fetcher.fetch_campaign_insights("c1")
        await fetcher.fetch_ad_insights("a1")
        assert fetcher.get_fetch_count() == 2


# ============================================================================
# META-006: Ads Performance Dashboard
# ============================================================================

class TestMETA006_PerformanceDashboard:
    """META-006: Ads Performance Dashboard"""

    def test_dashboard_initialization(self):
        """META-006: Dashboard should initialize."""
        from services.meta_ads_autopilot import AdsPerformanceDashboard
        dashboard = AdsPerformanceDashboard()
        assert dashboard is not None

    def test_dashboard_singleton(self):
        """META-006: Singleton should return same instance."""
        from services.meta_ads_autopilot import get_ads_performance_dashboard
        d1 = get_ads_performance_dashboard()
        d2 = get_ads_performance_dashboard()
        assert d1 is d2

    @pytest.mark.asyncio
    async def test_get_overview(self):
        """META-006: Should return campaign overview."""
        from services.meta_ads_autopilot import AdsPerformanceDashboard
        dashboard = AdsPerformanceDashboard()
        overview = await dashboard.get_overview(["camp_1", "camp_2"])
        assert overview["total_campaigns"] == 2
        assert "total_spend" in overview
        assert "total_impressions" in overview
        assert "campaigns" in overview

    @pytest.mark.asyncio
    async def test_identify_winners(self):
        """META-006: Should return list of winners."""
        from services.meta_ads_autopilot import AdsPerformanceDashboard
        dashboard = AdsPerformanceDashboard()
        winners = await dashboard.identify_winners("camp_1")
        assert isinstance(winners, list)

    @pytest.mark.asyncio
    async def test_spend_timeline(self):
        """META-006: Should return daily spend timeline."""
        from services.meta_ads_autopilot import AdsPerformanceDashboard
        dashboard = AdsPerformanceDashboard()
        timeline = await dashboard.get_spend_timeline("camp_1", days=7)
        assert len(timeline) == 7
        assert "date" in timeline[0]
        assert "spend" in timeline[0]


# ============================================================================
# META-007: AI Ads Insights Engine
# ============================================================================

class TestMETA007_AIInsightsEngine:
    """META-007: AI Ads Insights Engine"""

    def test_engine_initialization(self):
        """META-007: Engine should initialize."""
        from services.meta_ads_autopilot import AIAdsInsightsEngine
        engine = AIAdsInsightsEngine()
        assert engine is not None

    def test_engine_singleton(self):
        """META-007: Singleton should return same instance."""
        from services.meta_ads_autopilot import get_ai_ads_insights_engine
        e1 = get_ai_ads_insights_engine()
        e2 = get_ai_ads_insights_engine()
        assert e1 is e2

    @pytest.mark.asyncio
    async def test_analyze_performance(self):
        """META-007: Should analyze campaign performance."""
        from services.meta_ads_autopilot import AIAdsInsightsEngine
        engine = AIAdsInsightsEngine()
        result = await engine.analyze_campaign_performance({
            "campaign_id": "camp_1",
            "ctr": 2.5,
            "cpc": 0.50,
            "roas": 2.0,
            "impressions": 10000,
            "clicks": 250,
        })
        assert "performance_rating" in result
        assert "recommendations" in result
        assert result["performance_rating"] == "good"

    @pytest.mark.asyncio
    async def test_performance_rating_excellent(self):
        """META-007: Excellent performance should be rated correctly."""
        from services.meta_ads_autopilot import AIAdsInsightsEngine
        engine = AIAdsInsightsEngine()
        result = await engine.analyze_campaign_performance({
            "ctr": 5.0, "roas": 5.0, "impressions": 1000, "clicks": 50,
        })
        assert result["performance_rating"] == "excellent"

    @pytest.mark.asyncio
    async def test_performance_rating_needs_improvement(self):
        """META-007: Poor performance should be flagged."""
        from services.meta_ads_autopilot import AIAdsInsightsEngine
        engine = AIAdsInsightsEngine()
        result = await engine.analyze_campaign_performance({
            "ctr": 0.1, "roas": 0.1,
        })
        assert result["performance_rating"] == "needs_improvement"

    @pytest.mark.asyncio
    async def test_compare_variations(self):
        """META-007: Should compare ad variations."""
        from services.meta_ads_autopilot import AIAdsInsightsEngine
        engine = AIAdsInsightsEngine()
        result = await engine.compare_variations([
            {"ad_id": "a1", "ctr": 2.0},
            {"ad_id": "a2", "ctr": 5.0},
            {"ad_id": "a3", "ctr": 1.0},
        ])
        assert result["winner"]["ad_id"] == "a2"
        assert result["total_variations"] == 3

    def test_insights_history(self):
        """META-007: Should track insights history."""
        from services.meta_ads_autopilot import AIAdsInsightsEngine
        engine = AIAdsInsightsEngine()
        assert len(engine.get_insights_history()) == 0


# ============================================================================
# META-008: Campaign Budget Optimizer
# ============================================================================

class TestMETA008_BudgetOptimizer:
    """META-008: Campaign Budget Optimizer"""

    def test_optimizer_initialization(self):
        """META-008: Optimizer should initialize."""
        from services.meta_ads_autopilot import CampaignBudgetOptimizer
        optimizer = CampaignBudgetOptimizer()
        assert optimizer is not None

    def test_optimizer_singleton(self):
        """META-008: Singleton should return same instance."""
        from services.meta_ads_autopilot import get_campaign_budget_optimizer
        o1 = get_campaign_budget_optimizer()
        o2 = get_campaign_budget_optimizer()
        assert o1 is o2

    def test_add_rule(self):
        """META-008: Should add optimization rules."""
        from services.meta_ads_autopilot import CampaignBudgetOptimizer
        optimizer = CampaignBudgetOptimizer()
        rule = optimizer.add_rule("Low CTR", "ctr", "<", 0.5, "pause")
        assert rule["id"].startswith("rule_")
        assert rule["metric"] == "ctr"
        assert len(optimizer.get_rules()) == 1

    @pytest.mark.asyncio
    async def test_evaluate_campaign_triggers_rule(self):
        """META-008: Should trigger rules when conditions met."""
        from services.meta_ads_autopilot import CampaignBudgetOptimizer
        optimizer = CampaignBudgetOptimizer()
        optimizer.add_rule("Low CTR", "ctr", "<", 1.0, "pause")
        actions = await optimizer.evaluate_campaign("camp_1", {"ctr": 0.3})
        assert len(actions) == 1
        assert actions[0]["action"] == "pause"

    @pytest.mark.asyncio
    async def test_evaluate_no_trigger(self):
        """META-008: Should not trigger when conditions not met."""
        from services.meta_ads_autopilot import CampaignBudgetOptimizer
        optimizer = CampaignBudgetOptimizer()
        optimizer.add_rule("Low CTR", "ctr", "<", 1.0, "pause")
        actions = await optimizer.evaluate_campaign("camp_1", {"ctr": 2.0})
        assert len(actions) == 0

    @pytest.mark.asyncio
    async def test_scale_winners(self):
        """META-008: Should increase budget for winners."""
        from services.meta_ads_autopilot import CampaignBudgetOptimizer, MetaMarketingClient
        client = MetaMarketingClient()
        campaign = await client.create_campaign("Winner", "CONVERSIONS", 1000)
        optimizer = CampaignBudgetOptimizer(client=client)
        result = await optimizer.scale_winners(campaign["id"], 50.0)
        assert result["new_budget"] == 1500
        assert result["increase_pct"] == 50.0

    def test_optimization_history(self):
        """META-008: Should track optimization history."""
        from services.meta_ads_autopilot import CampaignBudgetOptimizer
        optimizer = CampaignBudgetOptimizer()
        assert len(optimizer.get_optimization_history()) == 0


# ============================================================================
# Cross-feature tests
# ============================================================================

class TestMetaAdsAutopilotGeneral:
    """General tests for Meta Ads Autopilot."""

    def test_all_services_importable(self):
        """All META services should be importable."""
        from services.meta_ads_autopilot import (
            MetaMarketingClient,
            AdCreativeVariationGenerator,
            MetaBatchRenderer,
            MetaCampaignDeployment,
            MetaInsightsFetcher,
            AdsPerformanceDashboard,
            AIAdsInsightsEngine,
            CampaignBudgetOptimizer,
        )
        assert MetaMarketingClient is not None
        assert AdCreativeVariationGenerator is not None
        assert MetaBatchRenderer is not None
        assert MetaCampaignDeployment is not None
        assert MetaInsightsFetcher is not None
        assert AdsPerformanceDashboard is not None
        assert AIAdsInsightsEngine is not None
        assert CampaignBudgetOptimizer is not None

    def test_all_singletons_importable(self):
        """All singleton accessors should be importable."""
        from services.meta_ads_autopilot import (
            get_meta_marketing_client,
            get_ad_creative_variation_generator,
            get_meta_batch_renderer,
            get_meta_campaign_deployment,
            get_meta_insights_fetcher,
            get_ads_performance_dashboard,
            get_ai_ads_insights_engine,
            get_campaign_budget_optimizer,
        )
        assert all([
            get_meta_marketing_client,
            get_ad_creative_variation_generator,
            get_meta_batch_renderer,
            get_meta_campaign_deployment,
            get_meta_insights_fetcher,
            get_ads_performance_dashboard,
            get_ai_ads_insights_engine,
            get_campaign_budget_optimizer,
        ])

    def test_enum_values(self):
        """Enum classes should have expected values."""
        from services.meta_ads_autopilot import (
            CampaignObjective, AdStatus, BidStrategy,
        )
        assert CampaignObjective.CONVERSIONS.value == "CONVERSIONS"
        assert AdStatus.ACTIVE.value == "ACTIVE"
        assert BidStrategy.LOWEST_COST.value == "LOWEST_COST"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
