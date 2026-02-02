"""
Meta Ads Testing Services (AD-001 to AD-008)
=============================================
End-to-end Meta ad testing pipeline: transcript extraction, variation generation,
batch rendering, campaign deployment, performance tracking, AI learning,
campaign management, and dynamic creative optimization.

Usage:
    from services.ad_testing import (
        get_extractor,
        get_variation_generator,
        get_batch_renderer,
        get_campaign_deployer,
        get_performance_tracker,
        get_ai_learner,
        get_campaign_manager,
        get_dco_optimizer,
    )

    # AD-001: Extract ad elements from transcript
    extractor = get_extractor()
    elements = extractor.extract_elements(transcript)

    # AD-002: Generate ad variations
    generator = get_variation_generator()
    variations = generator.generate_variations(elements, strategy="matrix")

    # AD-003: Render variations in batch
    renderer = get_batch_renderer()
    batch_id = renderer.create_batch(variations)

    # AD-004: Deploy to Meta
    deployer = get_campaign_deployer()
    campaign = deployer.create_campaign("Test", "CONVERSIONS", 5000, variations)

    # AD-005: Track performance
    tracker = get_performance_tracker()
    metrics = tracker.get_ad_metrics(ad_id)

    # AD-006: AI learns from results
    learner = get_ai_learner()
    insights = learner.analyze_results(campaign_id)

    # AD-007: Manage campaigns
    manager = get_campaign_manager()
    paused = manager.pause_underperformers(campaign_id, threshold=0.5)

    # AD-008: Dynamic Creative Optimization
    dco = get_dco_optimizer()
    dco_id = dco.create_dco_campaign(videos, texts, headlines, ctas)
"""

from .transcript_extractor import TranscriptElementExtractor, get_extractor
from .variation_generator import AdVariationGenerator, get_variation_generator
from .batch_renderer import AdBatchRenderer, get_batch_renderer
from .campaign_deployer import MetaCampaignDeployer, get_campaign_deployer
from .performance_tracker import MetaAdsPerformanceTracker, get_performance_tracker
from .ai_learner import AdAILearner, get_ai_learner
from .campaign_manager import MetaCampaignManager, get_campaign_manager
from .dco_optimizer import DynamicCreativeOptimizer, get_dco_optimizer

__all__ = [
    # AD-001
    "TranscriptElementExtractor",
    "get_extractor",
    # AD-002
    "AdVariationGenerator",
    "get_variation_generator",
    # AD-003
    "AdBatchRenderer",
    "get_batch_renderer",
    # AD-004
    "MetaCampaignDeployer",
    "get_campaign_deployer",
    # AD-005
    "MetaAdsPerformanceTracker",
    "get_performance_tracker",
    # AD-006
    "AdAILearner",
    "get_ai_learner",
    # AD-007
    "MetaCampaignManager",
    "get_campaign_manager",
    # AD-008
    "DynamicCreativeOptimizer",
    "get_dco_optimizer",
]
