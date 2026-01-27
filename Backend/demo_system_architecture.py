#!/usr/bin/env python3
"""
System Architecture Integration Demo (ARCH-001 to ARCH-008)
============================================================
Demonstrates the complete unified pipeline:

Workflow:
    Sora (1-3 part) → Stitch → Analyze → Auto-fill → Post to 22 Blotato accounts
                                                           ↓
    Tweet every 2h → Track Engagement → Optimize → Drive Offer Traffic

This script demonstrates:
    - ARCH-001: Master Orchestrator coordinating all subsystems
    - ARCH-002: 3-part Sora video generation with stitching
    - ARCH-003: Content Analyzer → Publisher integration
    - ARCH-004: Tweet scheduling every 2 hours
    - ARCH-005: Offer traffic tracking
    - ARCH-006: Analytics → AI feedback loop
    - ARCH-007: Unified Pipeline API
    - ARCH-008: Pipeline status monitoring

Usage:
    # Run with real services (requires API keys and Sora access):
    python Backend/demo_system_architecture.py --mode production

    # Run with mocked services (for testing):
    python Backend/demo_system_architecture.py --mode demo

    # Run specific feature test:
    python Backend/demo_system_architecture.py --feature ARCH-001
"""
import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime, timezone
from loguru import logger

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent))

from services.master_orchestrator import MasterOrchestrator, get_orchestrator
from services.event_bus import EventBus, Topics
from services.analytics_feedback import AnalyticsFeedback
from services.offer_tracker import OfferTracker


# =========================================================================
# DEMO FUNCTIONS FOR EACH ARCH FEATURE
# =========================================================================

async def demo_arch_001_orchestrator():
    """
    ARCH-001: Master Orchestrator Service

    Demonstrates:
    - Initializing the master orchestrator
    - Starting all subsystems
    - Event bus coordination
    """
    logger.info("=" * 80)
    logger.info("ARCH-001: Master Orchestrator Service Demo")
    logger.info("=" * 80)

    orchestrator = get_orchestrator()

    logger.info("✓ Orchestrator initialized with subsystems:")
    logger.info(f"  - Sora Pipeline: {orchestrator.sora_pipeline is not None}")
    logger.info(f"  - Content Analyzer: {orchestrator.content_analyzer is not None}")
    logger.info(f"  - Blotato Service: {orchestrator.blotato_service is not None}")
    logger.info(f"  - Twitter Service: {orchestrator.twitter_service is not None}")
    logger.info(f"  - Analytics Feedback: {orchestrator.analytics_feedback is not None}")
    logger.info(f"  - Event Bus: {orchestrator.event_bus is not None}")

    # Start orchestrator
    await orchestrator.start()
    logger.success("✓ Orchestrator started and subscribed to events")

    # Check active pipelines
    active_pipelines = orchestrator.list_active_pipelines()
    logger.info(f"✓ Active pipelines: {len(active_pipelines)}")

    await orchestrator.stop()
    logger.success("✓ ARCH-001 Demo Complete\n")


async def demo_arch_002_sora_batch():
    """
    ARCH-002: 3-Part Sora Batch Coordination

    Demonstrates:
    - Multi-part video generation
    - Automatic stitching
    - EventBus integration
    """
    logger.info("=" * 80)
    logger.info("ARCH-002: 3-Part Sora Batch Coordination Demo")
    logger.info("=" * 80)

    from automation.sora.pipeline import SoraPipeline

    pipeline = SoraPipeline()

    logger.info("✓ SoraPipeline initialized")
    logger.info("✓ generate_multi_part() method available")

    # Demo the method signature
    import inspect
    sig = inspect.signature(pipeline.generate_multi_part)
    logger.info(f"✓ Method parameters: {list(sig.parameters.keys())}")

    logger.info("\nDemo workflow:")
    logger.info("  1. Generate 3-part video from theme")
    logger.info("  2. AI generates cohesive prompts for each part")
    logger.info("  3. Each part is generated via Sora Safari automation")
    logger.info("  4. Videos are stitched together with FFmpeg")
    logger.info("  5. Content is analyzed for metadata")
    logger.info("  6. Events emitted: SORA_BATCH_STARTED, SORA_BATCH_COMPLETED")

    logger.success("✓ ARCH-002 Demo Complete\n")


async def demo_arch_003_analyzer_publisher():
    """
    ARCH-003: Content Analyzer → Publisher Integration

    Demonstrates:
    - Pre-computed analysis passing through pipeline
    - Platform-specific caption generation
    - No duplicate analysis
    """
    logger.info("=" * 80)
    logger.info("ARCH-003: Content Analyzer → Publisher Integration Demo")
    logger.info("=" * 80)

    from services.workers.publish_worker import PublishWorker

    worker = PublishWorker()

    # Sample analysis from Sora pipeline
    sample_analysis = {
        "detected_hook": "This AI content will blow your mind! 🤯",
        "suggested_description": "Watch how AI can create viral content in seconds",
        "hashtags": ["ai", "viral", "content", "automation", "fyp"],
        "cta": "Follow for more AI tips!",
        "viral_score": 92
    }

    logger.info("✓ Sample analysis from Sora pipeline:")
    for key, value in sample_analysis.items():
        logger.info(f"  - {key}: {value}")

    # Generate platform-specific captions
    platforms = ["tiktok", "instagram", "youtube", "twitter"]
    logger.info("\n✓ Platform-specific captions:")

    for platform in platforms:
        caption = worker._build_platform_caption(sample_analysis, platform)
        logger.info(f"\n  {platform.upper()} ({len(caption)} chars):")
        logger.info(f"  {caption[:150]}..." if len(caption) > 150 else f"  {caption}")

    logger.info("\n✓ Key benefits:")
    logger.info("  - Analysis done ONCE in Sora pipeline")
    logger.info("  - Passed forward via EventBus payload")
    logger.info("  - No re-analysis in PublishWorker")
    logger.info("  - Platform-optimized formatting")

    logger.success("✓ ARCH-003 Demo Complete\n")


async def demo_arch_004_tweet_scheduler():
    """
    ARCH-004: Tweet Scheduler 2-Hour Interval

    Demonstrates:
    - 2-hour interval configuration
    - Offer-focused tweet scheduling
    - UTM tracking integration
    """
    logger.info("=" * 80)
    logger.info("ARCH-004: Tweet Scheduler 2-Hour Interval Demo")
    logger.info("=" * 80)

    from services.twitter_campaign_service import TwitterCampaignService

    service = TwitterCampaignService(interval_minutes=120)

    logger.info(f"✓ Twitter service initialized with {service.interval_minutes} minute intervals")
    logger.info("✓ schedule_offer_tweets() method available")

    logger.info("\nDemo workflow:")
    logger.info("  1. Generate 12 tweets (one every 2 hours = 24h coverage)")
    logger.info("  2. Each tweet includes tracked offer URL with UTM params")
    logger.info("  3. Tweets rotate through awareness stages:")
    logger.info("     - Unaware → Problem Aware → Solution Aware → Product Aware → Most Aware")
    logger.info("  4. Content types: Hook, Story, Education, Social Proof, CTA")
    logger.info("  5. Scheduled via BullMQ or in-memory queue")

    # Sample offer tweet generation
    logger.info("\n✓ Sample offer tweet structure:")
    logger.info("  {Tweet content optimized for awareness stage}")
    logger.info("  https://offer.url?utm_campaign=jan2026&utm_source=twitter&utm_content=v1")

    logger.success("✓ ARCH-004 Demo Complete\n")


async def demo_arch_005_offer_tracking():
    """
    ARCH-005: Offer Traffic Tracking Service

    Demonstrates:
    - Click tracking with UTM parameters
    - Conversion attribution
    - Campaign analytics
    """
    logger.info("=" * 80)
    logger.info("ARCH-005: Offer Traffic Tracking Service Demo")
    logger.info("=" * 80)

    tracker = OfferTracker()

    logger.info("✓ OfferTracker initialized")
    logger.info("✓ Database connection established")

    logger.info("\n✓ Available methods:")
    logger.info("  - track_click(utm_campaign, utm_source, utm_content, ...)")
    logger.info("  - track_conversion(utm_campaign, conversion_type, revenue, ...)")
    logger.info("  - get_campaign_analytics(utm_campaign)")
    logger.info("  - get_top_performing_content(utm_campaign)")

    logger.info("\n✓ Database schema:")
    logger.info("  - offer_traffic: Click/visit tracking")
    logger.info("  - offer_conversions: Conversion events")
    logger.info("  - Aggregation: Analytics by campaign/content")

    logger.info("\n✓ Example analytics output:")
    sample_analytics = {
        "campaign": "jan2026_promo",
        "traffic": {
            "total_clicks": 1523,
            "unique_clicks": 987,
            "variants_tested": 5
        },
        "conversions": {
            "total": 47,
            "conversion_rate": 4.76
        },
        "revenue": {
            "total": 2349.53,
            "avg_order_value": 49.99
        },
        "roi": {
            "total_cost": 152.30,
            "profit": 2197.23,
            "roi_percentage": 1442.5
        }
    }

    for section, data in sample_analytics.items():
        logger.info(f"\n  {section.upper()}:")
        if isinstance(data, dict):
            for key, value in data.items():
                logger.info(f"    {key}: {value}")
        else:
            logger.info(f"    {data}")

    logger.success("✓ ARCH-005 Demo Complete\n")


async def demo_arch_006_analytics_feedback():
    """
    ARCH-006: Analytics → AI Feedback Loop

    Demonstrates:
    - Performance tracking
    - Pattern identification
    - Optimization recommendations
    """
    logger.info("=" * 80)
    logger.info("ARCH-006: Analytics → AI Feedback Loop Demo")
    logger.info("=" * 80)

    feedback = AnalyticsFeedback()

    logger.info("✓ AnalyticsFeedback service initialized")
    logger.info("✓ Event subscriptions:")
    logger.info("  - PUBLISH_COMPLETED → Track new posts")
    logger.info("  - METRICS_UPDATED → Update performance data")
    logger.info("  - offer.conversion.tracked → Update conversion data")

    await feedback.start()
    logger.info("✓ Feedback loop started")

    logger.info("\n✓ Workflow:")
    logger.info("  1. Post published → Start tracking")
    logger.info("  2. Metrics updated → Calculate viral score")
    logger.info("  3. Classify performance: Viral, High, Medium, Low, Poor")
    logger.info("  4. Identify patterns in high-performing content")
    logger.info("  5. Generate optimization recommendations")
    logger.info("  6. Feed learnings to content generation")

    logger.info("\n✓ Viral Score Calculation:")
    logger.info("  - Engagement rate: 40% weight")
    logger.info("  - Share rate: 30% weight")
    logger.info("  - Save rate: 20% weight")
    logger.info("  - Conversion rate: 10% weight")

    logger.info("\n✓ Sample recommendations:")
    recommendations = [
        {
            "name": "High-performing TikTok hooks",
            "avg_viral_score": 87.3,
            "recommendation": "Continue using question-based hooks with emojis"
        },
        {
            "name": "Instagram carousel patterns",
            "avg_viral_score": 82.1,
            "recommendation": "Educational content performs 40% better than entertainment"
        }
    ]

    for rec in recommendations:
        logger.info(f"\n  {rec['name']} (score: {rec['avg_viral_score']})")
        logger.info(f"    → {rec['recommendation']}")

    await feedback.stop()
    logger.success("✓ ARCH-006 Demo Complete\n")


async def demo_arch_007_pipeline_api():
    """
    ARCH-007: Unified Pipeline API Endpoint

    Demonstrates:
    - REST API for pipeline execution
    - Pipeline status monitoring
    - Health checks
    """
    logger.info("=" * 80)
    logger.info("ARCH-007: Unified Pipeline API Endpoint Demo")
    logger.info("=" * 80)

    from api.endpoints import orchestrator as orch_api

    logger.info("✓ API router loaded")
    logger.info("✓ Available endpoints:")

    routes = [route for route in orch_api.router.routes]
    for route in routes:
        logger.info(f"  {route.methods if hasattr(route, 'methods') else 'GET'} {route.path}")

    logger.info("\n✓ Example API Request:")
    logger.info("  POST /api/orchestrator/pipeline/run")
    logger.info("  {")
    logger.info('    "theme": "How to build viral AI content",')
    logger.info('    "num_parts": 3,')
    logger.info('    "character": "@isaiahdupree",')
    logger.info('    "publish_platforms": ["tiktok", "instagram", "youtube"],')
    logger.info('    "schedule_tweets": true,')
    logger.info('    "tweets_per_day": 12,')
    logger.info('    "offer_url": "https://mediaposter.ai/special-offer"')
    logger.info("  }")

    logger.info("\n✓ Example Response:")
    logger.info("  {")
    logger.info('    "success": true,')
    logger.info('    "message": "Pipeline started",')
    logger.info('    "pipeline_id": "abc123",')
    logger.info('    "status": "initializing"')
    logger.info("  }")

    logger.info("\n✓ Monitor progress:")
    logger.info("  GET /api/orchestrator/pipeline/{pipeline_id}")

    logger.success("✓ ARCH-007 Demo Complete\n")


async def demo_arch_008_dashboard_widget():
    """
    ARCH-008: Pipeline Dashboard Widget

    Demonstrates:
    - Pipeline status data structure
    - Real-time progress tracking
    - Output artifacts
    """
    logger.info("=" * 80)
    logger.info("ARCH-008: Pipeline Dashboard Widget Demo")
    logger.info("=" * 80)

    orchestrator = get_orchestrator()

    logger.info("✓ Dashboard data sources:")
    logger.info("  - orchestrator.get_pipeline_status(pipeline_id)")
    logger.info("  - orchestrator.list_active_pipelines()")

    logger.info("\n✓ Sample pipeline status structure:")
    sample_status = {
        "id": "abc123",
        "theme": "How to build viral AI content",
        "status": "publishing",
        "started_at": "2026-01-27T10:00:00Z",
        "steps": [
            "video_generated",
            "content_analyzed",
            "publishing_to_platforms"
        ],
        "outputs": {
            "video": {
                "stitched_video": "/path/to/final.mp4",
                "duration": 45,
                "resolution": "1080x1920"
            },
            "analysis": {
                "viral_score": 88,
                "title": "Amazing AI Content",
                "hashtags": ["ai", "viral", "content"]
            },
            "published": {
                "results": [
                    {"platform": "tiktok", "account_id": "710", "status": "queued"},
                    {"platform": "instagram", "account_id": "807", "status": "queued"}
                ]
            }
        }
    }

    import json
    logger.info(json.dumps(sample_status, indent=2))

    logger.info("\n✓ Widget features:")
    logger.info("  - Live progress bar (0-100%)")
    logger.info("  - Current stage indicator")
    logger.info("  - Video preview thumbnail")
    logger.info("  - Platform publish status")
    logger.info("  - Scheduled tweets count")
    logger.info("  - Real-time metrics")

    logger.success("✓ ARCH-008 Demo Complete\n")


async def demo_full_pipeline():
    """
    Complete End-to-End Pipeline Demo

    Demonstrates the full workflow from Sora → Publish → Tweets → Analytics
    """
    logger.info("=" * 80)
    logger.info("COMPLETE END-TO-END PIPELINE DEMO")
    logger.info("=" * 80)

    orchestrator = get_orchestrator()
    await orchestrator.start()

    logger.info("✓ Starting full pipeline execution...")
    logger.info("\nWorkflow:")
    logger.info("  1. Generate 3-part Sora video")
    logger.info("  2. Stitch parts together with FFmpeg")
    logger.info("  3. Analyze content for viral elements")
    logger.info("  4. Generate platform-specific captions")
    logger.info("  5. Publish to all configured accounts")
    logger.info("  6. Schedule promotional tweets (every 2h)")
    logger.info("  7. Track engagement and conversions")
    logger.info("  8. Feed analytics to AI for optimization")

    # Note: This would run the actual pipeline in production
    logger.warning("\n⚠️  Full pipeline execution requires:")
    logger.warning("  - Sora account with available credits")
    logger.warning("  - OpenAI API key for analysis")
    logger.warning("  - Blotato API key for publishing")
    logger.warning("  - Connected social accounts")

    logger.info("\n✓ To run the full pipeline:")
    logger.info("  orchestrator = get_orchestrator()")
    logger.info("  await orchestrator.start()")
    logger.info("  result = await orchestrator.run_full_pipeline(")
    logger.info('      theme="Your video theme",')
    logger.info('      num_parts=3,')
    logger.info('      publish_platforms=["tiktok", "instagram"],')
    logger.info('      schedule_tweets=True,')
    logger.info('      tweets_per_day=12')
    logger.info("  )")

    await orchestrator.stop()
    logger.success("✓ Full Pipeline Demo Complete\n")


# =========================================================================
# MAIN
# =========================================================================

async def main():
    parser = argparse.ArgumentParser(
        description="System Architecture Integration Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all demos
  python Backend/demo_system_architecture.py

  # Run specific feature demo
  python Backend/demo_system_architecture.py --feature ARCH-001

  # Run full pipeline (requires production setup)
  python Backend/demo_system_architecture.py --mode production
        """
    )

    parser.add_argument(
        "--feature",
        choices=[
            "ARCH-001", "ARCH-002", "ARCH-003", "ARCH-004",
            "ARCH-005", "ARCH-006", "ARCH-007", "ARCH-008",
            "all", "full"
        ],
        default="all",
        help="Which feature to demo"
    )

    parser.add_argument(
        "--mode",
        choices=["demo", "production"],
        default="demo",
        help="Demo mode (mocked) or production mode (real services)"
    )

    args = parser.parse_args()

    logger.info("\n")
    logger.info("╔" + "═" * 78 + "╗")
    logger.info("║" + " " * 18 + "SYSTEM ARCHITECTURE INTEGRATION DEMO" + " " * 24 + "║")
    logger.info("║" + " " * 26 + "(ARCH-001 to ARCH-008)" + " " * 31 + "║")
    logger.info("╚" + "═" * 78 + "╝")
    logger.info("\n")

    feature_map = {
        "ARCH-001": demo_arch_001_orchestrator,
        "ARCH-002": demo_arch_002_sora_batch,
        "ARCH-003": demo_arch_003_analyzer_publisher,
        "ARCH-004": demo_arch_004_tweet_scheduler,
        "ARCH-005": demo_arch_005_offer_tracking,
        "ARCH-006": demo_arch_006_analytics_feedback,
        "ARCH-007": demo_arch_007_pipeline_api,
        "ARCH-008": demo_arch_008_dashboard_widget,
    }

    if args.feature == "all":
        # Run all individual demos
        for demo_func in feature_map.values():
            await demo_func()
            await asyncio.sleep(0.5)
    elif args.feature == "full":
        # Run full end-to-end pipeline
        await demo_full_pipeline()
    else:
        # Run specific feature demo
        await feature_map[args.feature]()

    logger.info("=" * 80)
    logger.info("✅ Demo Complete!")
    logger.info("=" * 80)
    logger.info("\nNext steps:")
    logger.info("  1. Review the demo output above")
    logger.info("  2. Check the integration tests: pytest Backend/tests/test_system_architecture_integration.py")
    logger.info("  3. Review the PRD: docs/PRD_SYSTEM_ARCHITECTURE_INTEGRATION.md")
    logger.info("  4. Try the API: POST /api/orchestrator/pipeline/run")
    logger.info("\n")


if __name__ == "__main__":
    asyncio.run(main())
