"""
Tests for Trend Flash Video System
Tests trend detection, scoring, and content generation.
"""

import pytest
from datetime import datetime, timezone


class TestTrendFlashImports:
    """Test that all trend flash components can be imported."""
    
    def test_trend_radar_imports(self):
        """Test TrendRadar can be imported."""
        from services.trend_flash import TrendRadar, get_trend_radar
        assert TrendRadar is not None
        assert get_trend_radar is not None
    
    def test_trend_cluster_imports(self):
        """Test TrendCluster can be imported."""
        from services.trend_flash import TrendCluster
        assert TrendCluster is not None
    
    def test_flash_generator_imports(self):
        """Test FlashGenerator can be imported."""
        from services.trend_flash import FlashGenerator, get_flash_generator
        assert FlashGenerator is not None
        assert get_flash_generator is not None
    
    def test_content_model_imports(self):
        """Test TrendFlashContent can be imported."""
        from services.trend_flash import TrendFlashContent
        assert TrendFlashContent is not None
    
    def test_templates_import(self):
        """Test script templates can be imported."""
        from services.trend_flash import SCRIPT_TEMPLATES
        assert SCRIPT_TEMPLATES is not None
        assert "educational" in SCRIPT_TEMPLATES
        assert "contrarian" in SCRIPT_TEMPLATES
        assert "meme" in SCRIPT_TEMPLATES
    
    def test_intent_keywords_import(self):
        """Test intent keywords can be imported."""
        from services.trend_flash import INTENT_KEYWORDS
        assert INTENT_KEYWORDS is not None
        assert "how to" in INTENT_KEYWORDS
        assert "tutorial" in INTENT_KEYWORDS


class TestTrendCluster:
    """Tests for TrendCluster dataclass."""
    
    def test_cluster_creation(self):
        """Test TrendCluster creation with defaults."""
        from services.trend_flash import TrendCluster
        
        cluster = TrendCluster(
            topic="AI content automation"
        )
        
        assert cluster.id is not None
        assert cluster.topic == "AI content automation"
        assert cluster.velocity == 0.0
        assert cluster.trend_score == 0.0
        assert cluster.status == "detected"
    
    def test_cluster_with_full_data(self):
        """Test TrendCluster with all fields populated."""
        from services.trend_flash import TrendCluster
        
        cluster = TrendCluster(
            topic="using AI tools",
            keywords=["ai", "tools", "automation"],
            summary="People asking about AI content tools",
            velocity=45.2,
            mentions_count=127,
            unique_authors=89,
            platforms=["instagram", "tiktok", "twitter"],
            platform_count=3,
            top_questions=["what tool do you use?", "how do you automate?"],
            intent_keywords_found=["what tool", "how do you"],
            trend_score=130.5,
            cross_platform_multiplier=1.6,
            intent_multiplier=1.5
        )
        
        assert cluster.velocity == 45.2
        assert cluster.platform_count == 3
        assert len(cluster.top_questions) == 2
        assert cluster.trend_score == 130.5
    
    def test_cluster_to_dict(self):
        """Test TrendCluster serialization."""
        from services.trend_flash import TrendCluster
        
        cluster = TrendCluster(
            topic="test topic",
            velocity=10.0,
            trend_score=50.0
        )
        
        data = cluster.to_dict()
        
        assert "id" in data
        assert data["topic"] == "test topic"
        assert data["velocity"] == 10.0
        assert data["trend_score"] == 50.0


class TestTrendFlashContent:
    """Tests for TrendFlashContent dataclass."""
    
    def test_content_creation(self):
        """Test TrendFlashContent creation with defaults."""
        from services.trend_flash import TrendFlashContent
        
        content = TrendFlashContent(
            cluster_id="test-cluster-123"
        )
        
        assert content.id is not None
        assert content.cluster_id == "test-cluster-123"
        assert content.script_variant == "educational"
        assert content.video_type == "remotion"
        assert content.status == "pending"
    
    def test_content_with_script(self):
        """Test TrendFlashContent with script data."""
        from services.trend_flash import TrendFlashContent
        
        content = TrendFlashContent(
            cluster_id="cluster-456",
            script_hook="everyone's talking about AI today",
            script_context="it's popping up on ig and tiktok",
            script_take="the real move is consistency",
            script_action="do this: step 1, step 2, step 3",
            script_cta="comment 'workflow' for the template",
            script_variant="educational"
        )
        
        assert content.script_hook != ""
        assert content.script_cta != ""
    
    def test_content_to_dict(self):
        """Test TrendFlashContent serialization."""
        from services.trend_flash import TrendFlashContent
        
        content = TrendFlashContent(
            cluster_id="cluster-789",
            title_tiktok="🔥 AI tools everyone needs",
            title_instagram="✨ The truth about AI content"
        )
        
        data = content.to_dict()
        
        assert "id" in data
        assert "script" in data
        assert "titles" in data
        assert data["titles"]["tiktok"] == "🔥 AI tools everyone needs"


class TestScoringFormula:
    """Tests for the trend scoring formula."""
    
    def test_base_score(self):
        """Test score with no multipliers."""
        from services.trend_flash import TrendCluster, get_trend_radar
        
        cluster = TrendCluster(
            topic="test",
            velocity=10.0,
            platform_count=1,
            intent_keywords_found=[]
        )
        
        radar = get_trend_radar()
        radar._calculate_score(cluster)
        
        assert cluster.cross_platform_multiplier == 1.0
        assert cluster.intent_multiplier == 1.0
        assert cluster.trend_score == 10.0  # velocity * 1.0 * 1.0
    
    def test_cross_platform_multiplier_2(self):
        """Test +30% for 2 platforms."""
        from services.trend_flash import TrendCluster, get_trend_radar
        
        cluster = TrendCluster(
            topic="test",
            velocity=10.0,
            platform_count=2,
            platforms=["instagram", "tiktok"],
            intent_keywords_found=[]
        )
        
        radar = get_trend_radar()
        radar._calculate_score(cluster)
        
        assert cluster.cross_platform_multiplier == 1.3
        assert cluster.trend_score == 13.0  # 10 * 1.3 * 1.0
    
    def test_cross_platform_multiplier_3plus(self):
        """Test +60% for 3+ platforms."""
        from services.trend_flash import TrendCluster, get_trend_radar
        
        cluster = TrendCluster(
            topic="test",
            velocity=10.0,
            platform_count=3,
            platforms=["instagram", "tiktok", "twitter"],
            intent_keywords_found=[]
        )
        
        radar = get_trend_radar()
        radar._calculate_score(cluster)
        
        assert cluster.cross_platform_multiplier == 1.6
        assert cluster.trend_score == 16.0  # 10 * 1.6 * 1.0
    
    def test_intent_multiplier_single(self):
        """Test +50% for 1-2 intent keywords."""
        from services.trend_flash import TrendCluster, get_trend_radar
        
        cluster = TrendCluster(
            topic="test",
            velocity=10.0,
            platform_count=1,
            intent_keywords_found=["how to"]
        )
        
        radar = get_trend_radar()
        radar._calculate_score(cluster)
        
        assert cluster.intent_multiplier == 1.5
        assert cluster.trend_score == 15.0  # 10 * 1.0 * 1.5
    
    def test_intent_multiplier_multiple(self):
        """Test +80% for 3+ intent keywords."""
        from services.trend_flash import TrendCluster, get_trend_radar
        
        cluster = TrendCluster(
            topic="test",
            velocity=10.0,
            platform_count=1,
            intent_keywords_found=["how to", "tutorial", "template"]
        )
        
        radar = get_trend_radar()
        radar._calculate_score(cluster)
        
        assert cluster.intent_multiplier == 1.8
        assert cluster.trend_score == 18.0  # 10 * 1.0 * 1.8
    
    def test_combined_multipliers(self):
        """Test combined cross-platform + intent multipliers."""
        from services.trend_flash import TrendCluster, get_trend_radar
        
        cluster = TrendCluster(
            topic="test",
            velocity=100.0,
            platform_count=3,
            platforms=["instagram", "tiktok", "twitter"],
            intent_keywords_found=["how to", "tutorial", "template"]
        )
        
        radar = get_trend_radar()
        radar._calculate_score(cluster)
        
        # 100 * 1.6 * 1.8 = 288
        assert cluster.cross_platform_multiplier == 1.6
        assert cluster.intent_multiplier == 1.8
        assert cluster.trend_score == 288.0


class TestScriptTemplates:
    """Tests for script template structure."""
    
    def test_educational_template_parts(self):
        """Test educational template has all parts."""
        from services.trend_flash import SCRIPT_TEMPLATES
        
        template = SCRIPT_TEMPLATES["educational"]
        
        assert "hook" in template
        assert "context" in template
        assert "take" in template
        assert "action" in template
        assert "cta" in template
    
    def test_contrarian_template_parts(self):
        """Test contrarian template has all parts."""
        from services.trend_flash import SCRIPT_TEMPLATES
        
        template = SCRIPT_TEMPLATES["contrarian"]
        
        assert "hook" in template
        assert "{trend}" in template["hook"]
    
    def test_meme_template_parts(self):
        """Test meme template has all parts."""
        from services.trend_flash import SCRIPT_TEMPLATES
        
        template = SCRIPT_TEMPLATES["meme"]
        
        assert "hook" in template
        assert "cta" in template


class TestTrendRadar:
    """Tests for TrendRadar service."""
    
    def test_radar_initialization(self):
        """Test TrendRadar initializes correctly."""
        from services.trend_flash import TrendRadar
        
        radar = TrendRadar()
        assert radar is not None
        assert radar.engine is not None
    
    def test_radar_singleton(self):
        """Test get_trend_radar returns same instance."""
        from services.trend_flash import get_trend_radar
        
        r1 = get_trend_radar()
        r2 = get_trend_radar()
        
        assert r1 is r2
    
    def test_get_clusters(self):
        """Test getting clusters."""
        from services.trend_flash import get_trend_radar
        
        radar = get_trend_radar()
        clusters = radar.get_clusters(limit=10)
        
        assert isinstance(clusters, list)
    
    def test_get_top_clusters(self):
        """Test getting top clusters."""
        from services.trend_flash import get_trend_radar
        
        radar = get_trend_radar()
        clusters = radar.get_top_clusters(limit=3)
        
        assert isinstance(clusters, list)
        assert len(clusters) <= 3


class TestFlashGenerator:
    """Tests for FlashGenerator service."""
    
    def test_generator_initialization(self):
        """Test FlashGenerator initializes correctly."""
        from services.trend_flash import FlashGenerator
        
        generator = FlashGenerator()
        assert generator is not None
        assert generator.engine is not None
    
    def test_generator_singleton(self):
        """Test get_flash_generator returns same instance."""
        from services.trend_flash import get_flash_generator
        
        g1 = get_flash_generator()
        g2 = get_flash_generator()
        
        assert g1 is g2
    
    def test_get_content_list(self):
        """Test getting content list."""
        from services.trend_flash import get_flash_generator
        
        generator = get_flash_generator()
        content = generator.get_content_list(limit=10)
        
        assert isinstance(content, list)


class TestTrendFlashAPI:
    """Tests for Trend Flash API endpoints."""
    
    def test_api_router_exists(self):
        """Test API router can be imported."""
        from api.endpoints.trend_flash import router
        assert router is not None
    
    def test_detection_endpoints_exist(self):
        """Test detection endpoints exist."""
        from api.endpoints.trend_flash import (
            detect_trends,
            get_clusters,
            get_cluster,
            get_top_clusters
        )
        assert detect_trends is not None
        assert get_clusters is not None
        assert get_cluster is not None
        assert get_top_clusters is not None
    
    def test_generation_endpoints_exist(self):
        """Test generation endpoints exist."""
        from api.endpoints.trend_flash import (
            generate_content,
            get_content_list,
            get_content
        )
        assert generate_content is not None
        assert get_content_list is not None
        assert get_content is not None
    
    def test_pipeline_endpoints_exist(self):
        """Test pipeline endpoints exist."""
        from api.endpoints.trend_flash import (
            run_full_pipeline,
            get_stats
        )
        assert run_full_pipeline is not None
        assert get_stats is not None


class TestIntentKeywords:
    """Tests for intent keyword detection."""
    
    def test_all_intent_keywords_defined(self):
        """Test all intent keywords are present."""
        from services.trend_flash import INTENT_KEYWORDS
        
        expected = [
            "how do i", "how to", "what tool", "tutorial",
            "template", "workflow", "step by step"
        ]
        
        for keyword in expected:
            assert keyword in INTENT_KEYWORDS
    
    def test_intent_keyword_count(self):
        """Test reasonable number of intent keywords."""
        from services.trend_flash import INTENT_KEYWORDS
        
        assert len(INTENT_KEYWORDS) >= 10
