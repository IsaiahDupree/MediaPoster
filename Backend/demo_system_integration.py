#!/usr/bin/env python3
"""
System Architecture Integration Demo (ARCH-001 to ARCH-008)
===========================================================
Demonstrates the complete end-to-end pipeline:

    Sora (1-3 part) → Stitch → Analyze → Auto-fill → Post to 22 Blotato accounts
                                                              ↓
    Tweet every 2h → Track Engagement → Optimize → Drive Offer Traffic

Features Demonstrated:
- ARCH-001: Master Orchestrator Service
- ARCH-002: 3-Part Sora Batch Coordination
- ARCH-003: Content Analyzer → Publisher Integration
- ARCH-004: Tweet Scheduler 2-Hour Interval
- ARCH-005: Offer Traffic Tracking Service
- ARCH-006: Analytics → AI Feedback Loop
- ARCH-007: Unified Pipeline API Endpoint
- ARCH-008: Pipeline Dashboard Widget

Usage:
    python demo_system_integration.py [--mock] [--theme "AI productivity"]
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import argparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from services.master_orchestrator import MasterOrchestrator, start_master_orchestrator
from services.event_bus import EventBus, Topics
from loguru import logger


class PipelineDemo:
    """Interactive demo of the system architecture integration."""

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self.event_bus: Optional[EventBus] = None
        self.orchestrator: Optional[MasterOrchestrator] = None
        self.events_received = []

    async def setup(self):
        """Initialize the demo environment."""
        logger.info("🚀 Setting up System Architecture Integration Demo...")

        # Initialize EventBus
        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("demo")

        # Subscribe to all pipeline events
        self._setup_event_listeners()

        # Initialize orchestrator (skip if in mock mode and missing API keys)
        try:
            self.orchestrator = await start_master_orchestrator(self.event_bus)
        except ValueError as e:
            if self.mock_mode and "API_KEY" in str(e):
                logger.warning(f"⚠️  {e} - Running in simplified mock mode")
                self.orchestrator = None
            else:
                raise

        logger.success("✅ Demo environment ready!")

    def _setup_event_listeners(self):
        """Subscribe to pipeline events for monitoring."""
        # Pipeline lifecycle events
        self.event_bus.subscribe(Topics.ORCHESTRATOR_PIPELINE_STARTED, self._on_event)
        self.event_bus.subscribe(Topics.ORCHESTRATOR_STEP_STARTED, self._on_event)
        self.event_bus.subscribe(Topics.ORCHESTRATOR_STEP_COMPLETED, self._on_event)
        self.event_bus.subscribe(Topics.ORCHESTRATOR_PIPELINE_COMPLETED, self._on_event)
        self.event_bus.subscribe(Topics.ORCHESTRATOR_PIPELINE_FAILED, self._on_event)

        # Sora events (ARCH-002)
        self.event_bus.subscribe(Topics.SORA_BATCH_STARTED, self._on_event)
        self.event_bus.subscribe(Topics.SORA_BATCH_COMPLETED, self._on_event)

        # Publish events (ARCH-003)
        self.event_bus.subscribe(Topics.PUBLISH_REQUESTED, self._on_event)
        self.event_bus.subscribe(Topics.PUBLISH_STARTED, self._on_event)
        self.event_bus.subscribe(Topics.PUBLISH_COMPLETED, self._on_event)

        # Tracking events (ARCH-005)
        self.event_bus.subscribe(Topics.CHECKBACK_SCHEDULED, self._on_event)
        self.event_bus.subscribe(Topics.CHECKBACK_COMPLETED, self._on_event)

        logger.debug("📫 Subscribed to pipeline events")

    async def _on_event(self, event):
        """Handle pipeline events."""
        self.events_received.append({
            "topic": event.topic,
            "timestamp": datetime.now().isoformat(),
            "payload": event.payload
        })

        # Log important events
        if "started" in event.topic.lower():
            logger.info(f"▶️  {event.topic}")
        elif "completed" in event.topic.lower():
            logger.success(f"✅ {event.topic}")
        elif "failed" in event.topic.lower():
            logger.error(f"❌ {event.topic}")

    async def demo_full_pipeline(self, theme: str = "AI productivity tips that save 10 hours per week"):
        """
        Demonstrate the complete end-to-end pipeline.

        ARCH-001: Master Orchestrator coordinates all subsystems
        ARCH-002: 3-part Sora video generation
        ARCH-003: Content analysis wired to publisher
        ARCH-004: Twitter campaign scheduling
        ARCH-005: Engagement tracking setup
        """
        logger.info(f"\n{'=' * 80}")
        logger.info("🎬 DEMO: Full Pipeline Execution")
        logger.info(f"{'=' * 80}")
        logger.info(f"Theme: {theme}")
        logger.info(f"Mode: {'MOCK' if self.mock_mode else 'PRODUCTION'}\n")

        if self.mock_mode:
            logger.warning("⚠️  Running in MOCK mode - Sora automation will be simulated")
            await self._run_mock_pipeline(theme)
        else:
            logger.info("🔴 Running in PRODUCTION mode - Real Sora automation will be used")
            await self._run_production_pipeline(theme)

    async def _run_mock_pipeline(self, theme: str):
        """Run pipeline with mocked Sora generation."""
        logger.info("\n📊 Pipeline Stage Summary:")
        logger.info("─" * 80)

        # Stage 1: Sora Generation (ARCH-002)
        logger.info("\n1️⃣  STAGE 1: SORA GENERATION (ARCH-002)")
        logger.info("   • Generating 3-part video series")
        logger.info("   • Theme: " + theme)
        logger.info("   • Status: MOCKED - Would generate via Safari automation")

        mock_sora_result = {
            "id": "demo_mock_123",
            "status": "completed",
            "successful_parts": 3,
            "failed_parts": 0,
            "stitched_video": "/tmp/demo_stitched.mp4",
            "analysis": {
                "viral_score": 87,
                "detected_hook": "The #1 AI productivity hack nobody talks about",
                "hashtags": ["AI", "productivity", "automation", "tips"],
                "topics": ["artificial intelligence", "time management", "automation"],
                "tone": "energetic",
                "call_to_action": {
                    "type": "profile_visit",
                    "text": "Follow for more AI tips",
                    "strength": 8
                },
                "content_type": "educational",
                "target_audience": "professionals"
            },
            "prompts": [
                "Part 1: Hook - Person struggling with manual tasks",
                "Part 2: Solution - AI automation in action",
                "Part 3: Results - Time saved and productivity boost"
            ]
        }

        logger.success("   ✅ Sora generation complete (mocked)")
        logger.info(f"   📊 Viral Score: {mock_sora_result['analysis']['viral_score']}/100")
        logger.info(f"   🎯 Hook: {mock_sora_result['analysis']['detected_hook']}")

        # Stage 2: Content Analysis (ARCH-003)
        logger.info("\n2️⃣  STAGE 2: CONTENT ANALYSIS (ARCH-003)")
        logger.info("   • Analysis provided by Sora pipeline")
        logger.info(f"   • Topics: {', '.join(mock_sora_result['analysis']['topics'])}")
        logger.info(f"   • Tone: {mock_sora_result['analysis']['tone']}")
        logger.info(f"   • Target Audience: {mock_sora_result['analysis']['target_audience']}")
        logger.success("   ✅ Content analysis ready")

        # Stage 3: Blotato Publishing (ARCH-003)
        logger.info("\n3️⃣  STAGE 3: BLOTATO PUBLISHING")
        logger.info("   • Would publish to 22 Blotato accounts:")
        logger.info("     - Instagram: 4 accounts")
        logger.info("     - TikTok: 4 accounts")
        logger.info("     - YouTube: 2 accounts")
        logger.info("     - Twitter: 1 account")
        logger.info("     - Threads: 4 accounts")
        logger.info("     - Others: 7 accounts")
        logger.info("   • Auto-generated captions from analysis")
        logger.info("   • Platform-specific formatting")
        logger.success("   ✅ Publishing queued (mocked)")

        # Stage 4: Twitter Campaign (ARCH-004)
        logger.info("\n4️⃣  STAGE 4: TWITTER CAMPAIGN (ARCH-004)")
        logger.info("   • Scheduling 12 tweets/day at 2-hour intervals")
        logger.info("   • Campaign strategy:")
        logger.info("     - Mix of awareness stages (unaware → most aware)")
        logger.info("     - Content types: Hook, Authority, Story, Emotional, CTA")
        logger.info("     - Driving traffic to video posts")
        logger.success("   ✅ Twitter campaign scheduled (mocked)")

        # Stage 5: Engagement Tracking (ARCH-005)
        logger.info("\n5️⃣  STAGE 5: ENGAGEMENT TRACKING (ARCH-005)")
        logger.info("   • Checkback periods: 1h, 6h, 24h, 72h, 7d")
        logger.info("   • Tracking:")
        logger.info("     - Views, likes, comments, shares")
        logger.info("     - Click-through rates")
        logger.info("     - Conversion attribution")
        logger.success("   ✅ Tracking setup complete (mocked)")

        # Stage 6: Analytics Feedback (ARCH-006)
        logger.info("\n6️⃣  STAGE 6: ANALYTICS FEEDBACK LOOP (ARCH-006)")
        logger.info("   • Metrics will be fed back to AI for optimization")
        logger.info("   • Learning what content performs best")
        logger.info("   • Adjusting future content strategy")
        logger.success("   ✅ Feedback loop configured")

        logger.info("\n" + "=" * 80)
        logger.success("🎉 PIPELINE COMPLETE (MOCK MODE)")
        logger.info("=" * 80)

        # Event summary
        logger.info(f"\n📊 Event Summary: {len(self.events_received)} events captured")

    async def _run_production_pipeline(self, theme: str):
        """Run real pipeline with actual Sora generation."""
        logger.warning("⚠️  PRODUCTION MODE - This will:")
        logger.warning("   • Open Safari and automate Sora")
        logger.warning("   • Generate real videos")
        logger.warning("   • Publish to actual Blotato accounts")
        logger.warning("   • Schedule real tweets")

        response = input("\nDo you want to continue? (yes/no): ")
        if response.lower() != "yes":
            logger.info("❌ Cancelled by user")
            return

        # Run actual pipeline
        result = await self.orchestrator.run_full_pipeline(
            theme=theme,
            num_parts=3,
            blotato_accounts=[807, 710, 243],  # Test with 3 accounts
            enable_twitter_campaign=True,
            twitter_posts_per_day=12,
            schedule_interval_hours=2
        )

        # Display results
        logger.info("\n" + "=" * 80)
        logger.info("📊 PIPELINE RESULTS")
        logger.info("=" * 80)
        logger.info(f"Pipeline ID: {result['id']}")
        logger.info(f"Status: {result['stage']}")
        logger.info(f"Stages Completed: {', '.join(result['stages_completed'])}")

        if result.get("sora_result"):
            sora = result["sora_result"]
            logger.info(f"\n🎬 Sora: {sora.get('successful_parts')}/{result['num_parts']} parts")
            logger.info(f"   Video: {sora.get('stitched_video')}")
            logger.info(f"   Viral Score: {sora.get('analysis', {}).get('viral_score', 0)}/100")

        if result.get("publish_results"):
            pub = result["publish_results"]
            logger.info(f"\n📤 Publishing: {len(pub.get('successful', []))} successful")

        if result.get("twitter_campaign"):
            tw = result["twitter_campaign"]
            logger.info(f"\n🐦 Twitter: {tw.get('posts_scheduled')} tweets scheduled")

        logger.info("\n" + "=" * 80)
        logger.success("🎉 PIPELINE COMPLETE")
        logger.info("=" * 80)

    async def demo_api_endpoint(self):
        """Demonstrate the unified API endpoint (ARCH-007)."""
        logger.info(f"\n{'=' * 80}")
        logger.info("🔌 DEMO: Unified Pipeline API Endpoint (ARCH-007)")
        logger.info(f"{'=' * 80}\n")

        api_example = """
# Trigger pipeline via HTTP API:
curl -X POST http://localhost:5555/api/orchestrator/pipeline \\
  -H "Content-Type: application/json" \\
  -d '{
    "theme": "AI productivity tips that save 10 hours per week",
    "num_parts": 3,
    "character": "@isaiahdupree",
    "blotato_accounts": [807, 710, 243],
    "enable_twitter_campaign": true,
    "twitter_posts_per_day": 12,
    "schedule_interval_hours": 2
  }'

# Get pipeline status:
curl http://localhost:5555/api/orchestrator/pipelines

# Health check:
curl http://localhost:5555/api/orchestrator/health
        """

        logger.info(api_example)

    def display_architecture_summary(self):
        """Display architecture integration summary."""
        logger.info(f"\n{'=' * 80}")
        logger.info("🏗️  SYSTEM ARCHITECTURE INTEGRATION SUMMARY")
        logger.info(f"{'=' * 80}\n")

        features = [
            {
                "id": "ARCH-001",
                "name": "Master Orchestrator Service",
                "status": "✅ COMPLETE",
                "file": "services/master_orchestrator.py"
            },
            {
                "id": "ARCH-002",
                "name": "3-Part Sora Batch Coordination",
                "status": "✅ COMPLETE",
                "file": "automation/sora/pipeline.py"
            },
            {
                "id": "ARCH-003",
                "name": "Content Analyzer → Publisher Integration",
                "status": "✅ COMPLETE",
                "file": "services/workers/publish_worker.py:172-209"
            },
            {
                "id": "ARCH-004",
                "name": "Tweet Scheduler 2-Hour Interval",
                "status": "✅ COMPLETE",
                "file": "services/twitter_campaign_service.py:1073-1107"
            },
            {
                "id": "ARCH-005",
                "name": "Offer Traffic Tracking Service",
                "status": "✅ COMPLETE",
                "file": "services/master_orchestrator.py:426-466"
            },
            {
                "id": "ARCH-006",
                "name": "Analytics → AI Feedback Loop",
                "status": "✅ COMPLETE",
                "file": "services/master_orchestrator.py:546-551"
            },
            {
                "id": "ARCH-007",
                "name": "Unified Pipeline API Endpoint",
                "status": "✅ COMPLETE",
                "file": "api/endpoints/orchestrator.py"
            },
            {
                "id": "ARCH-008",
                "name": "Pipeline Dashboard Widget",
                "status": "✅ COMPLETE",
                "file": "dashboard/app/orchestrator/page.tsx"
            }
        ]

        for feature in features:
            logger.info(f"{feature['status']} {feature['id']}: {feature['name']}")
            logger.info(f"   📁 {feature['file']}\n")

        logger.info("=" * 80)
        logger.success("🎉 All 8 System Architecture features are COMPLETE!")
        logger.info("=" * 80)


async def main():
    """Run the demo."""
    parser = argparse.ArgumentParser(description="System Architecture Integration Demo")
    parser.add_argument("--mock", action="store_true", help="Run in mock mode (no real Sora)")
    parser.add_argument("--theme", default="AI productivity tips that save 10 hours per week",
                        help="Video theme")
    parser.add_argument("--production", action="store_true", help="Run in production mode (real Sora)")
    args = parser.parse_args()

    # Configure logger
    logger.remove()
    logger.add(sys.stdout, format="<green>{time:HH:mm:ss}</green> | <level>{message}</level>")

    # Create demo
    demo = PipelineDemo(mock_mode=not args.production)

    # Setup
    await demo.setup()

    # Display architecture summary
    demo.display_architecture_summary()

    # Demo full pipeline
    await demo.demo_full_pipeline(args.theme)

    # Demo API endpoint
    await demo.demo_api_endpoint()

    logger.info("\n✨ Demo complete!")


if __name__ == "__main__":
    asyncio.run(main())
