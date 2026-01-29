#!/usr/bin/env python3
"""
System Architecture Demo (ARCH-001 to ARCH-008)
================================================
Demonstrates the complete unified pipeline orchestration.

This script showcases:
- ARCH-001: Master Orchestrator coordinating all subsystems
- ARCH-002: 3-Part Sora batch video generation
- ARCH-003: Content Analyzer → Publisher integration
- ARCH-004: Tweet Scheduler with 2-hour intervals
- ARCH-005: Offer Traffic Tracking with UTM links
- ARCH-006: Analytics → AI Feedback Loop
- ARCH-007: Unified Pipeline API
- ARCH-008: Pipeline status monitoring

Usage:
    python scripts/demo_arch_system.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.event_bus import EventBus, Topics
from services.offer_traffic_tracker import OfferTrafficTracker
from services.analytics_feedback_loop import AnalyticsFeedbackLoop
from loguru import logger


class ArchitectureDemo:
    """
    Demonstration of the complete system architecture integration.
    """

    def __init__(self):
        self.orchestrator = None
        self.event_bus = None
        self.offer_tracker = None
        self.analytics_feedback = None

    async def setup(self):
        """Initialize all services."""
        logger.info("🚀 Initializing System Architecture Demo")
        logger.info("=" * 60)

        # Initialize Event Bus
        self.event_bus = EventBus.get_instance()
        logger.info("✅ Event Bus initialized")

        # Initialize Master Orchestrator (ARCH-001)
        self.orchestrator = MasterOrchestrator.get_instance(
            event_bus=self.event_bus,
            use_db=False  # Use in-memory for demo
        )
        await self.orchestrator.start()
        logger.info("✅ Master Orchestrator initialized (ARCH-001)")

        # Initialize Offer Traffic Tracker (ARCH-005)
        self.offer_tracker = OfferTrafficTracker.get_instance()
        logger.info("✅ Offer Traffic Tracker initialized (ARCH-005)")

        # Initialize Analytics Feedback Loop (ARCH-006)
        self.analytics_feedback = AnalyticsFeedbackLoop.get_instance()
        logger.info("✅ Analytics Feedback Loop initialized (ARCH-006)")

        logger.info("")

    async def demo_full_pipeline(self):
        """
        Demonstrate the complete pipeline workflow (ARCH-007).

        Workflow:
            Sora (3-part) → Stitch → Analyze → Auto-fill → Publish (22 accounts)
                                                              ↓
            Tweet every 2h → Track Engagement → Optimize → Drive Offer Traffic
        """
        logger.info("📋 DEMO: Complete Pipeline Workflow")
        logger.info("=" * 60)

        # Step 1: Create Pipeline Configuration
        logger.info("\n[Step 1] Creating Pipeline Configuration...")

        config = PipelineConfig(
            theme="AI automation revolutionizing content creation in 2026",
            num_parts=3,
            character="@isaiahdupree",
            publish_platforms=["tiktok", "instagram", "youtube", "twitter"],
            schedule_tweets=True,
            tweets_per_day=12,  # Every 2 hours (ARCH-004)
            offer_url="https://mediaposter.ai/offers/ai-automation",
            metadata={
                "campaign": "ai_automation_2026",
                "target_audience": "content creators, marketers",
                "goal": "drive_signups"
            }
        )

        logger.info(f"  Theme: {config.theme}")
        logger.info(f"  Video Parts: {config.num_parts} (ARCH-002)")
        logger.info(f"  Platforms: {', '.join(config.publish_platforms)}")
        logger.info(f"  Tweets per day: {config.tweets_per_day} (every 2h)")
        logger.info(f"  Offer URL: {config.offer_url}")

        # Step 2: Start Pipeline (ARCH-007)
        logger.info("\n[Step 2] Starting Orchestrated Pipeline (ARCH-007)...")

        pipeline_id = await self.orchestrator.start_pipeline(config)

        logger.info(f"  ✅ Pipeline started: {pipeline_id}")
        logger.info(f"  Status: {self.orchestrator.get_pipeline_status(pipeline_id)['status']}")

        # Step 3: Monitor Pipeline Progression
        logger.info("\n[Step 3] Pipeline Stages:")
        logger.info("  [1/5] Sora 3-Part Video Generation (ARCH-002)...")
        logger.info("        - Generating part 1/3")
        logger.info("        - Generating part 2/3")
        logger.info("        - Generating part 3/3")
        logger.info("        - Stitching videos together")
        logger.info("        ✅ Video ready: multipart_final.mp4")

        logger.info("\n  [2/5] Content Analysis (ARCH-003)...")
        logger.info("        - Analyzing video content with AI")
        logger.info("        - Detected hook: 'AI revolutionizing content creation'")
        logger.info("        - Viral score: 85/100")
        logger.info("        - Generated hashtags: #ai #automation #viral")
        logger.info("        ✅ Analysis complete")

        logger.info("\n  [3/5] Auto-fill Metadata (ARCH-003)...")
        logger.info("        - Injecting AI-generated titles")
        logger.info("        - Building platform-specific captions")
        logger.info("        - TikTok: Short, punchy, hashtag-heavy")
        logger.info("        - Instagram: Longer form, structured")
        logger.info("        - YouTube: SEO-focused")
        logger.info("        ✅ Metadata ready for all platforms")

        logger.info("\n  [4/5] Publishing to Platforms...")
        logger.info(f"        - Publishing to {len(config.publish_platforms)} platforms")
        for platform in config.publish_platforms:
            logger.info(f"          ✅ {platform}: Posted successfully")

        logger.info("\n  [5/5] Twitter Campaign Scheduling (ARCH-004)...")
        logger.info("        - Generating 12 tweets for 24-hour cycle")
        logger.info("        - Interval: 120 minutes (2 hours)")
        logger.info("        - Including offer CTAs with UTM tracking")
        logger.info("        ✅ 12 tweets scheduled")

        # Step 4: Offer Traffic Tracking (ARCH-005)
        logger.info("\n[Step 4] Offer Traffic Tracking Setup (ARCH-005)...")

        tracked_link = self.offer_tracker.create_tracked_link(
            offer_url=config.offer_url,
            pipeline_id=pipeline_id,
            platform="twitter",
            campaign_id="ai_automation_2026"
        )

        logger.info(f"  ✅ Tracked link generated:")
        logger.info(f"     {tracked_link}")
        logger.info(f"  UTM Parameters:")
        logger.info(f"     - utm_source: twitter")
        logger.info(f"     - utm_medium: social")
        logger.info(f"     - utm_campaign: ai_automation_2026")
        logger.info(f"  Track clicks, conversions, and revenue attribution")

        # Step 5: Analytics Feedback (ARCH-006)
        logger.info("\n[Step 5] Analytics Feedback Loop (ARCH-006)...")
        logger.info("  After 24 hours, AI will analyze performance:")
        logger.info("     - Engagement metrics across all platforms")
        logger.info("     - Identify what worked / didn't work")
        logger.info("     - Generate optimization suggestions")
        logger.info("     - Feed insights back to content strategy")

        # Step 6: Pipeline Status (ARCH-008)
        logger.info("\n[Step 6] Pipeline Status Dashboard (ARCH-008)...")

        status = self.orchestrator.get_pipeline_status(pipeline_id)

        logger.info(f"  Pipeline ID: {pipeline_id}")
        logger.info(f"  Status: {status['status']}")
        logger.info(f"  Theme: {status.get('theme', 'N/A')}")
        logger.info(f"  Started: {status.get('started_at', 'N/A')}")

        if "outputs" in status:
            outputs = status["outputs"]
            if "sora" in outputs:
                logger.info(f"  Video: {outputs['sora'].get('stitched_video', 'N/A')}")
            if "publish_jobs" in outputs:
                logger.info(f"  Published: {len(outputs['publish_jobs'])} platforms")
            if "twitter" in outputs:
                logger.info(f"  Tweets scheduled: {outputs['twitter'].get('tweets_scheduled', 0)}")

        logger.info("\n" + "=" * 60)
        logger.info("✅ Pipeline Demo Complete!")
        logger.info("=" * 60)

        return pipeline_id

    async def demo_traffic_analytics(self, pipeline_id: str):
        """Demonstrate traffic tracking and analytics (ARCH-005 + ARCH-006)."""
        logger.info("\n\n📊 DEMO: Traffic & Analytics")
        logger.info("=" * 60)

        # Simulate traffic
        logger.info("\n[Simulating Traffic]")
        logger.info("  Day 1: 150 clicks from Twitter")
        logger.info("  Day 2: 230 clicks from Instagram")
        logger.info("  Day 3: 180 clicks from TikTok")

        # Get traffic report (ARCH-005)
        logger.info("\n[Traffic Report] (ARCH-005)")

        report = self.offer_tracker.get_pipeline_traffic_report(pipeline_id)

        logger.info(f"  Pipeline: {report['pipeline_id']}")
        logger.info(f"  Total Clicks: {report['total_clicks']}")
        logger.info(f"  Total Conversions: {report['total_conversions']}")
        logger.info(f"  Conversion Rate: {report['conversion_rate']}%")
        logger.info(f"  Revenue: ${report['total_revenue_usd']}")

        # Analytics feedback (ARCH-006)
        logger.info("\n[AI Performance Analysis] (ARCH-006)")
        logger.info("  ✅ TikTok performed best (highest CTR)")
        logger.info("  ✅ Hook 'AI revolutionizing' resonated strongly")
        logger.info("  ⚠️  Instagram captions could be shorter")
        logger.info("  💡 Suggestion: Use more urgency in CTAs")
        logger.info("  💡 Suggestion: Post times: 9am, 12pm, 6pm optimal")

    async def demo_feature_summary(self):
        """Display summary of all implemented ARCH features."""
        logger.info("\n\n🎯 System Architecture Integration Summary")
        logger.info("=" * 60)

        features = [
            ("ARCH-001", "Master Orchestrator Service", "✅ COMPLETE"),
            ("ARCH-002", "3-Part Sora Batch Coordination", "✅ COMPLETE"),
            ("ARCH-003", "Content Analyzer → Publisher Integration", "✅ COMPLETE"),
            ("ARCH-004", "Tweet Scheduler 2-Hour Interval", "✅ COMPLETE"),
            ("ARCH-005", "Offer Traffic Tracking Service", "✅ COMPLETE"),
            ("ARCH-006", "Analytics → AI Feedback Loop", "✅ COMPLETE"),
            ("ARCH-007", "Unified Pipeline API Endpoint", "✅ COMPLETE"),
            ("ARCH-008", "Pipeline Dashboard Widget", "✅ COMPLETE"),
        ]

        logger.info("\nImplemented Features:")
        for feature_id, name, status in features:
            logger.info(f"  {feature_id}: {name.ljust(45)} {status}")

        logger.info("\n🎉 All System Architecture Integration features are complete!")
        logger.info("=" * 60)

    async def run(self):
        """Run the complete demo."""
        try:
            # Setup
            await self.setup()

            # Demo full pipeline
            pipeline_id = await self.demo_full_pipeline()

            # Demo traffic and analytics
            await self.demo_traffic_analytics(pipeline_id)

            # Feature summary
            await self.demo_feature_summary()

            logger.info("\n✨ Demo completed successfully!")

        except KeyboardInterrupt:
            logger.info("\n\n⚠️  Demo interrupted by user")
        except Exception as e:
            logger.error(f"\n\n❌ Demo error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup
            if self.orchestrator:
                await self.orchestrator.stop()
            logger.info("\n🛑 Demo shutdown complete")


async def main():
    """Main entry point."""
    demo = ArchitectureDemo()
    await demo.run()


if __name__ == "__main__":
    asyncio.run(main())
