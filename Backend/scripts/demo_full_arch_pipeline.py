#!/usr/bin/env python3
"""
Full Architecture Pipeline Demo (ARCH-001 to ARCH-008)
=======================================================
Demonstrates the complete end-to-end system architecture workflow:

1. ARCH-001: Master Orchestrator coordination
2. ARCH-002: 3-Part Sora video generation with auto-stitching
3. ARCH-003: Content Analyzer → Publisher integration (auto-fill metadata)
4. ARCH-004: Tweet Scheduler with 2-hour intervals
5. ARCH-005: Offer Traffic Tracking with UTM links
6. ARCH-006: Analytics → AI Feedback Loop
7. ARCH-007: Unified Pipeline API
8. ARCH-008: Pipeline Dashboard monitoring

Workflow:
    Sora (1-3 part) → Stitch → Analyze → Auto-fill → Post to 22 Blotato accounts
                                                          ↓
    Tweet every 2h → Track Engagement → Optimize → Drive Offer Traffic

Usage:
    python Backend/scripts/demo_full_arch_pipeline.py

Options:
    --theme "Your video theme"
    --num-parts 3
    --character "@isaiahdupree"
    --skip-sora  # Skip actual Sora generation (for testing)
    --dry-run    # Show what would happen without executing
"""

import asyncio
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
import json

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.event_bus import EventBus, Topics
from services.offer_traffic_tracker import OfferTrafficTracker
from services.analytics_feedback_loop import AnalyticsFeedbackLoop
from loguru import logger


class ArchitectureDemo:
    """
    Demonstration of the complete system architecture integration.

    This script showcases all ARCH-001 to ARCH-008 features working together
    in a unified workflow.
    """

    def __init__(self, skip_sora: bool = False, dry_run: bool = False):
        self.skip_sora = skip_sora
        self.dry_run = dry_run

        # Initialize services
        logger.info("🏗️  Initializing System Architecture Demo...")

        self.event_bus = EventBus.get_instance()
        self.orchestrator = MasterOrchestrator.get_instance(use_db=True)
        self.traffic_tracker = OfferTrafficTracker.get_instance()
        self.analytics_feedback = AnalyticsFeedbackLoop.get_instance()

        # Event listener for real-time monitoring
        self._setup_event_listeners()

        logger.info("✅ All services initialized")

    def _setup_event_listeners(self):
        """Set up event listeners for real-time pipeline monitoring (ARCH-008)."""

        # Listen to all orchestrator events for dashboard-style updates
        self.event_bus.subscribe(
            Topics.ORCHESTRATOR_PIPELINE_STARTED,
            self._on_pipeline_started
        )
        self.event_bus.subscribe(
            Topics.ORCHESTRATOR_PIPELINE_COMPLETED,
            self._on_pipeline_completed
        )
        self.event_bus.subscribe(
            Topics.SORA_BATCH_STARTED,
            self._on_sora_started
        )
        self.event_bus.subscribe(
            Topics.SORA_BATCH_COMPLETED,
            self._on_sora_completed
        )
        self.event_bus.subscribe(
            Topics.PUBLISH_REQUESTED,
            self._on_publish_requested
        )
        self.event_bus.subscribe(
            "blotato.publish.completed",
            self._on_publish_completed
        )
        self.event_bus.subscribe(
            "twitter.campaign.scheduled",
            self._on_twitter_scheduled
        )

        logger.info("📡 Event listeners configured for pipeline monitoring")

    async def _on_pipeline_started(self, event):
        """Handle pipeline start event."""
        logger.info(f"🚀 [PIPELINE STARTED] {event.payload.get('theme')}")

    async def _on_pipeline_completed(self, event):
        """Handle pipeline completion event."""
        logger.success(f"🎉 [PIPELINE COMPLETED] {event.payload.get('theme')}")

    async def _on_sora_started(self, event):
        """Handle Sora batch start event."""
        logger.info(f"🎬 [SORA] Starting {event.payload.get('num_parts')}-part generation...")

    async def _on_sora_completed(self, event):
        """Handle Sora batch completion event."""
        payload = event.payload
        logger.success(
            f"✅ [SORA] Completed: {payload.get('successful_parts')}/{payload.get('num_parts')} parts"
        )
        if payload.get('stitched_video'):
            logger.info(f"   Video: {payload.get('stitched_video')}")

    async def _on_publish_requested(self, event):
        """Handle publish request event."""
        platform = event.payload.get('platform')
        logger.info(f"📤 [PUBLISH] Requested for {platform}")

    async def _on_publish_completed(self, event):
        """Handle publish completion event."""
        platform = event.payload.get('platform')
        logger.success(f"✅ [PUBLISH] Completed for {platform}")

    async def _on_twitter_scheduled(self, event):
        """Handle Twitter campaign scheduled event."""
        count = event.payload.get('tweets_scheduled', 0)
        logger.success(f"✅ [TWITTER] Scheduled {count} tweets")

    async def run_full_pipeline(
        self,
        theme: str,
        num_parts: int = 3,
        character: str = None,
        publish_platforms: list = None,
        schedule_tweets: bool = True,
        tweets_per_day: int = 12,
        offer_url: str = None
    ):
        """
        Run the full architecture pipeline demonstration.

        This showcases all ARCH features in a single cohesive workflow.
        """

        print("\n" + "="*80)
        print("🏗️  SYSTEM ARCHITECTURE INTEGRATION DEMO")
        print("="*80)
        print(f"Theme: {theme}")
        print(f"Parts: {num_parts}")
        print(f"Character: {character or 'None'}")
        print(f"Platforms: {', '.join(publish_platforms or ['tiktok', 'instagram', 'youtube'])}")
        print(f"Tweets: {tweets_per_day}/day (every {int(1440/tweets_per_day)} min)")
        print(f"Offer: {offer_url or 'None'}")
        print("="*80 + "\n")

        if self.dry_run:
            logger.info("🔍 DRY RUN MODE - No actual execution")
            logger.info("\nWould execute:")
            logger.info(f"  1. Generate {num_parts}-part Sora video on theme: {theme}")
            logger.info(f"  2. Stitch parts into single video")
            logger.info(f"  3. Analyze content with AI for metadata")
            logger.info(f"  4. Publish to {len(publish_platforms or [])} platforms")
            if schedule_tweets:
                logger.info(f"  5. Schedule {tweets_per_day} tweets/day")
            if offer_url:
                logger.info(f"  6. Track offer traffic with UTM links")
            return None

        # Start the orchestrator service
        await self.orchestrator.start()

        # ARCH-001: Master Orchestrator coordinates all subsystems
        logger.info("\n📋 [ARCH-001] Master Orchestrator - Starting Pipeline")

        # Create pipeline configuration
        config = PipelineConfig(
            theme=theme,
            num_parts=num_parts,
            character=character,
            publish_platforms=publish_platforms or ["tiktok", "instagram", "youtube"],
            schedule_tweets=schedule_tweets,
            tweets_per_day=tweets_per_day,
            offer_url=offer_url
        )

        # Start the pipeline
        pipeline_id = await self.orchestrator.start_pipeline(config)

        logger.info(f"✅ Pipeline started: {pipeline_id}")

        # Wait for pipeline to complete (with timeout)
        logger.info("\n⏳ Waiting for pipeline to complete...")
        logger.info("   (This may take 10-15 minutes for actual Sora generation)")

        # Poll for completion
        max_wait_seconds = 1800  # 30 minutes max
        poll_interval = 5
        elapsed = 0

        while elapsed < max_wait_seconds:
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

            status = self.orchestrator.get_pipeline_status(pipeline_id)

            if status.get("status") == "completed":
                logger.success(f"\n🎉 Pipeline completed in {elapsed} seconds!")
                break
            elif status.get("status") == "failed":
                logger.error(f"\n❌ Pipeline failed: {status.get('error')}")
                break

            # Show progress
            current_step = status.get("current_step", "unknown")
            logger.info(f"   [{elapsed}s] Current step: {current_step}")

        # Get final status
        final_status = self.orchestrator.get_pipeline_status(pipeline_id)

        # Display results
        self._display_results(pipeline_id, final_status)

        # Demonstrate analytics feedback (ARCH-006)
        if offer_url and final_status.get("status") == "completed":
            logger.info("\n📊 [ARCH-006] Analytics Feedback Loop - Would analyze in 24h")
            logger.info(f"   Analytics endpoint: /api/orchestrator/pipeline/{pipeline_id}/analytics")

        # Stop orchestrator
        await self.orchestrator.stop()

        return pipeline_id

    def _display_results(self, pipeline_id: str, status: dict):
        """Display pipeline results (ARCH-008: Dashboard-style output)."""

        print("\n" + "="*80)
        print("📊 PIPELINE RESULTS")
        print("="*80)

        print(f"\nPipeline ID: {pipeline_id}")
        print(f"Status: {status.get('status', 'unknown').upper()}")
        print(f"Started: {status.get('started_at', 'N/A')}")

        if status.get('completed_at'):
            print(f"Completed: {status.get('completed_at')}")

        # Sora results
        if "sora" in status.get("outputs", {}):
            sora_output = status["outputs"]["sora"]
            print(f"\n🎬 Sora Generation:")
            print(f"   Video: {sora_output.get('stitched_video', 'N/A')}")

            if "analysis" in sora_output:
                analysis = sora_output["analysis"]
                print(f"   Title (TikTok): {analysis.get('title_tiktok', 'N/A')[:60]}...")
                print(f"   Hashtags: {', '.join(analysis.get('hashtags', [])[:5])}")

        # Publishing results
        publish_jobs = status.get("outputs", {}).get("publish_jobs", [])
        if publish_jobs:
            print(f"\n📤 Publishing:")
            for job in publish_jobs:
                platform = job.get("platform")
                job_status = job.get("status")
                print(f"   {platform}: {job_status}")

        # Twitter results
        if "twitter" in status.get("outputs", {}):
            twitter_output = status["outputs"]["twitter"]
            print(f"\n🐦 Twitter Campaign:")
            print(f"   Tweets scheduled: {twitter_output.get('tweets_scheduled', 0)}")

        # Offer tracking info
        config_dict = status.get("config", {})
        if hasattr(config_dict, '__dict__'):
            config_dict = config_dict.__dict__

        offer_url = config_dict.get("offer_url")
        if offer_url:
            print(f"\n🔗 Offer Tracking:")
            print(f"   Offer URL: {offer_url}")
            print(f"   Traffic endpoint: /api/orchestrator/pipeline/{pipeline_id}/traffic")

        print("\n" + "="*80 + "\n")


async def main():
    """Main entry point for the demo."""

    parser = argparse.ArgumentParser(
        description="Full Architecture Pipeline Demo (ARCH-001 to ARCH-008)"
    )
    parser.add_argument(
        "--theme",
        default="AI automation revolutionizing content creation",
        help="Video theme/topic"
    )
    parser.add_argument(
        "--num-parts",
        type=int,
        default=3,
        choices=[1, 2, 3, 4, 5],
        help="Number of video parts (1-5)"
    )
    parser.add_argument(
        "--character",
        default=None,
        help="Sora @character (e.g., @isaiahdupree)"
    )
    parser.add_argument(
        "--platforms",
        nargs="+",
        default=["tiktok", "instagram", "youtube"],
        help="Platforms to publish to"
    )
    parser.add_argument(
        "--tweets-per-day",
        type=int,
        default=12,
        help="Number of tweets per day"
    )
    parser.add_argument(
        "--offer-url",
        default=None,
        help="Offer URL to track and promote"
    )
    parser.add_argument(
        "--skip-sora",
        action="store_true",
        help="Skip actual Sora generation (for testing)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without executing"
    )

    args = parser.parse_args()

    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    # Create and run demo
    demo = ArchitectureDemo(
        skip_sora=args.skip_sora,
        dry_run=args.dry_run
    )

    try:
        pipeline_id = await demo.run_full_pipeline(
            theme=args.theme,
            num_parts=args.num_parts,
            character=args.character,
            publish_platforms=args.platforms,
            schedule_tweets=True,
            tweets_per_day=args.tweets_per_day,
            offer_url=args.offer_url
        )

        if pipeline_id and not args.dry_run:
            logger.success(f"\n✅ Demo completed! Pipeline ID: {pipeline_id}")
            logger.info("\nNext steps:")
            logger.info(f"  1. Check status: GET /api/orchestrator/pipeline/{pipeline_id}")
            logger.info(f"  2. View analytics: GET /api/orchestrator/pipeline/{pipeline_id}/analytics")
            logger.info(f"  3. Check traffic: GET /api/orchestrator/pipeline/{pipeline_id}/traffic")
            logger.info(f"  4. List all pipelines: GET /api/orchestrator/pipelines")

    except KeyboardInterrupt:
        logger.warning("\n⚠️  Demo interrupted by user")
    except Exception as e:
        logger.error(f"\n❌ Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
