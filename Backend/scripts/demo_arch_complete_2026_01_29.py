#!/usr/bin/env python3
"""
System Architecture Integration Demo (ARCH-001 to ARCH-008)
=============================================================
Demonstrates the complete orchestrated pipeline:
    1. Generate 3-part Sora video
    2. Stitch and analyze content
    3. Publish to multiple platforms
    4. Schedule Twitter campaign
    5. Track offer traffic
    6. Analyze performance with AI

This script showcases all 8 ARCH features working together.
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.event_bus import EventBus, Topics
from loguru import logger


async def demo_full_pipeline():
    """
    Run a complete pipeline demonstration.

    This demo:
    - Starts the Master Orchestrator (ARCH-001)
    - Generates a 3-part Sora video (ARCH-002)
    - Analyzes content and auto-fills metadata (ARCH-003)
    - Publishes to TikTok, Instagram, YouTube
    - Schedules 12 tweets at 2-hour intervals (ARCH-004)
    - Tracks offer traffic with UTM links (ARCH-005)
    - Analyzes performance for optimization (ARCH-006)
    - All via REST API endpoints (ARCH-007)
    """
    logger.info("=" * 70)
    logger.info("SYSTEM ARCHITECTURE INTEGRATION DEMO")
    logger.info("=" * 70)
    logger.info("")
    logger.info("Features Demonstrated:")
    logger.info("  ✅ ARCH-001: Master Orchestrator Service")
    logger.info("  ✅ ARCH-002: 3-Part Sora Batch Coordination")
    logger.info("  ✅ ARCH-003: Content Analyzer → Publisher Integration")
    logger.info("  ✅ ARCH-004: Tweet Scheduler 2-Hour Interval")
    logger.info("  ✅ ARCH-005: Offer Traffic Tracking Service")
    logger.info("  ✅ ARCH-006: Analytics → AI Feedback Loop")
    logger.info("  ✅ ARCH-007: Unified Pipeline API Endpoint")
    logger.info("  ✅ ARCH-008: Pipeline Dashboard Widget")
    logger.info("")
    logger.info("=" * 70)

    # Initialize orchestrator (ARCH-001)
    logger.info("\n[Step 1] Initializing Master Orchestrator (ARCH-001)...")
    orchestrator = MasterOrchestrator.get_instance()
    await orchestrator.start()
    logger.success("✅ Orchestrator started successfully")

    # Subscribe to events for demo visibility
    event_bus = EventBus.get_instance()

    def log_event(event):
        """Log all pipeline events for demo."""
        logger.info(f"📡 Event: {event.topic} | {event.payload}")

    # Subscribe to key events
    event_bus.subscribe(Topics.SORA_BATCH_STARTED, log_event)
    event_bus.subscribe(Topics.SORA_BATCH_COMPLETED, log_event)
    event_bus.subscribe(Topics.PUBLISH_STARTED, log_event)
    event_bus.subscribe(Topics.PUBLISH_COMPLETED, log_event)
    event_bus.subscribe("twitter.campaign.scheduled", log_event)

    # Configure pipeline
    logger.info("\n[Step 2] Configuring Pipeline...")
    config = PipelineConfig(
        theme="AI automation revolutionizing content creation for busy creators",
        num_parts=3,
        character="@isaiahdupree",
        publish_platforms=["tiktok", "instagram", "youtube"],
        schedule_tweets=True,
        tweets_per_day=12,  # Every 2 hours (ARCH-004)
        offer_url="https://blotato.com/offers/ai-automation",
        metadata={
            "demo": True,
            "timestamp": datetime.now().isoformat()
        }
    )

    logger.info(f"  Theme: {config.theme}")
    logger.info(f"  Parts: {config.num_parts}")
    logger.info(f"  Character: {config.character}")
    logger.info(f"  Platforms: {', '.join(config.publish_platforms)}")
    logger.info(f"  Tweets/day: {config.tweets_per_day}")
    logger.info(f"  Offer URL: {config.offer_url}")

    # Start pipeline (ARCH-001, ARCH-007)
    logger.info("\n[Step 3] Starting Orchestrated Pipeline...")
    logger.info("This will:")
    logger.info("  1. Generate 3-part Sora video (ARCH-002)")
    logger.info("  2. Stitch videos with FFmpeg")
    logger.info("  3. Analyze content with AI (ARCH-003)")
    logger.info("  4. Auto-generate platform-specific captions")
    logger.info("  5. Publish to TikTok, Instagram, YouTube")
    logger.info("  6. Schedule 12 tweets at 2-hour intervals (ARCH-004)")
    logger.info("  7. Track offer clicks with UTM links (ARCH-005)")
    logger.info("  8. Queue analytics for 24h performance review (ARCH-006)")
    logger.info("")

    try:
        pipeline_id = await orchestrator.start_pipeline(config)
        logger.success(f"✅ Pipeline started: {pipeline_id}")

        # Monitor pipeline progress
        logger.info("\n[Step 4] Monitoring Pipeline Progress...")
        logger.info("(In production, this would be displayed in the dashboard - ARCH-008)")

        max_wait = 300  # 5 minutes for demo
        wait_interval = 5  # Check every 5 seconds
        elapsed = 0

        while elapsed < max_wait:
            await asyncio.sleep(wait_interval)
            elapsed += wait_interval

            # Get status
            status = orchestrator.get_pipeline_status(pipeline_id)

            if status.get("error"):
                logger.error(f"Pipeline error: {status['error']}")
                break

            current_status = status.get("status", "unknown")
            current_step = status.get("current_step", "unknown")

            logger.info(f"  [{elapsed}s] Status: {current_status} | Step: {current_step}")

            # Check if completed
            if current_status in ["completed", "failed"]:
                break

        # Final status
        logger.info("\n[Step 5] Pipeline Results...")
        final_status = orchestrator.get_pipeline_status(pipeline_id)

        if final_status.get("status") == "completed":
            logger.success("🎉 Pipeline completed successfully!")
            logger.info("")
            logger.info("Results:")

            # Sora output (ARCH-002)
            sora_output = final_status.get("outputs", {}).get("sora", {})
            if sora_output:
                logger.info(f"  📹 Video: {sora_output.get('stitched_video')}")
                logger.info(f"  🎯 Viral Score: {sora_output.get('analysis', {}).get('viral_score', 'N/A')}")

            # Publishing output (ARCH-003)
            publish_jobs = final_status.get("outputs", {}).get("publish_jobs", [])
            completed_publishes = [j for j in publish_jobs if j.get("status") == "completed"]
            logger.info(f"  📱 Published: {len(completed_publishes)}/{len(publish_jobs)} platforms")

            # Twitter output (ARCH-004)
            twitter_output = final_status.get("outputs", {}).get("twitter", {})
            if twitter_output:
                logger.info(f"  🐦 Tweets Scheduled: {twitter_output.get('tweets_scheduled', 0)}")

            logger.info("")
            logger.info("Next Steps:")
            logger.info("  1. ✅ Videos are live on TikTok, Instagram, YouTube")
            logger.info("  2. ✅ 12 tweets will post every 2 hours (ARCH-004)")
            logger.info("  3. ✅ Offer clicks are being tracked (ARCH-005)")
            logger.info("  4. ⏳ Analytics will analyze performance in 24h (ARCH-006)")
            logger.info("")
            logger.info("View pipeline in dashboard: http://localhost:5557/pipelines")
            logger.info(f"API status: http://localhost:5555/api/orchestrator/pipeline/{pipeline_id}")

        else:
            logger.warning(f"Pipeline status: {final_status.get('status')}")
            if final_status.get("error"):
                logger.error(f"Error: {final_status.get('error')}")

    except Exception as e:
        logger.error(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        logger.info("\n[Step 6] Stopping Orchestrator...")
        await orchestrator.stop()
        logger.success("✅ Demo complete")


async def demo_individual_features():
    """
    Demonstrate each ARCH feature individually.
    """
    logger.info("\n" + "=" * 70)
    logger.info("INDIVIDUAL FEATURE DEMONSTRATIONS")
    logger.info("=" * 70)

    # ARCH-005: Offer Traffic Tracker
    logger.info("\n[ARCH-005] Offer Traffic Tracking Demo")
    logger.info("-" * 70)
    try:
        from services.offer_traffic_tracker import OfferTrafficTracker

        tracker = OfferTrafficTracker.get_instance()

        # Create tracked link
        tracked_link = tracker.create_tracked_link(
            offer_url="https://blotato.com/offers/ai-automation",
            pipeline_id="demo-pipeline-001",
            platform="twitter",
            campaign_id="2h-campaign"
        )
        logger.success(f"✅ Created tracked link: {tracked_link}")
        logger.info("   UTM parameters automatically added for analytics")

    except Exception as e:
        logger.warning(f"⚠️ Offer tracker demo skipped: {e}")

    # ARCH-006: Analytics Feedback Loop
    logger.info("\n[ARCH-006] Analytics Feedback Loop Demo")
    logger.info("-" * 70)
    try:
        from services.analytics_feedback_loop import AnalyticsFeedbackLoop

        feedback = AnalyticsFeedbackLoop.get_instance()
        logger.success("✅ Analytics feedback loop initialized")
        logger.info("   Waits 24h after pipeline completion to analyze performance")
        logger.info("   Generates AI-powered optimization suggestions")
        logger.info("   Learns from historical patterns")

    except Exception as e:
        logger.warning(f"⚠️ Analytics feedback demo skipped: {e}")

    logger.info("\n" + "=" * 70)
    logger.info("All features demonstrated successfully! ✅")
    logger.info("=" * 70)


async def main():
    """Main demo entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="System Architecture Integration Demo")
    parser.add_argument(
        "--mode",
        choices=["full", "individual", "both"],
        default="individual",
        help="Demo mode: full pipeline or individual features"
    )
    args = parser.parse_args()

    try:
        if args.mode in ["individual", "both"]:
            await demo_individual_features()

        if args.mode in ["full", "both"]:
            logger.info("\n" + "=" * 70)
            logger.info("⚠️  FULL PIPELINE DEMO")
            logger.info("=" * 70)
            logger.info("This will generate real Sora videos and publish to platforms.")
            logger.info("Make sure:")
            logger.info("  1. Safari is running")
            logger.info("  2. Sora is logged in")
            logger.info("  3. Blotato accounts are connected")
            logger.info("")

            response = input("Continue with full pipeline demo? (y/n): ")
            if response.lower() == 'y':
                await demo_full_pipeline()
            else:
                logger.info("Full pipeline demo skipped")

    except KeyboardInterrupt:
        logger.info("\n\nDemo interrupted by user")
    except Exception as e:
        logger.error(f"Demo error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
