#!/usr/bin/env python3
"""
Test Script: Full System Architecture Integration
=================================================
Demonstrates the complete ARCH-001 to ARCH-008 pipeline:

Workflow:
    Sora (1-3 part) → Stitch → Analyze → Auto-fill → Post to 22 Blotato accounts
                                                           ↓
    Tweet every 2h → Track Engagement → Optimize → Drive Offer Traffic

Usage:
    python scripts/test_full_pipeline.py
    python scripts/test_full_pipeline.py --theme "AI automation" --dry-run
"""

import asyncio
import sys
from pathlib import Path

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.event_bus import EventBus
from services.blotato_service import BlotatoService
from services.twitter_campaign_service import TwitterCampaignService
from services.offer_traffic_tracker import OfferTrafficTracker
from services.analytics_feedback_loop import AnalyticsFeedbackLoop
from loguru import logger
import argparse


async def test_full_pipeline(
    theme: str = "AI automation revolutionizing content creation",
    num_parts: int = 3,
    character: str = "@isaiahdupree",
    offer_url: str = "https://blotato.com",
    dry_run: bool = False
):
    """
    Test the complete system architecture integration.

    Args:
        theme: Video theme
        num_parts: Number of video parts (1-3)
        character: Sora character
        offer_url: Offer URL for traffic tracking
        dry_run: If True, only logs what would happen
    """
    logger.info("="*80)
    logger.info("🚀 SYSTEM ARCHITECTURE INTEGRATION TEST")
    logger.info("="*80)
    logger.info(f"Theme: {theme}")
    logger.info(f"Parts: {num_parts}")
    logger.info(f"Character: {character}")
    logger.info(f"Offer: {offer_url}")
    logger.info(f"Dry Run: {dry_run}")
    logger.info("="*80)

    # Initialize services
    logger.info("\n📦 Initializing Services...")
    event_bus = EventBus.get_instance()
    orchestrator = MasterOrchestrator.get_instance(event_bus=event_bus, use_db=False)

    # Start orchestrator
    logger.info("🎯 Starting Master Orchestrator...")
    await orchestrator.start()

    if dry_run:
        logger.info("\n🔍 DRY RUN MODE - Showing pipeline steps:\n")

        steps = [
            ("ARCH-001", "Master Orchestrator", "Coordinates all subsystems via EventBus"),
            ("ARCH-002", "Sora 3-Part Generation", f"Generate {num_parts} video parts about: {theme}"),
            ("", "         └─ Part 1", "Hook (first 5 seconds)"),
            ("", "         └─ Part 2", "Main content"),
            ("", "         └─ Part 3", "Payoff/CTA"),
            ("", "Video Stitching", "Combine all parts into final video"),
            ("ARCH-003", "Content Analysis", "AI analyzes video and generates titles/descriptions"),
            ("", "         └─ Detected Hook", "First 3 seconds attention grabber"),
            ("", "         └─ Topics", "Main themes and topics"),
            ("", "         └─ Tone & Pacing", "Emotional tone and delivery speed"),
            ("", "Publishing", f"Distribute to platforms with auto-filled metadata"),
            ("", "         └─ Blotato", "22 accounts across TikTok, Instagram, YouTube, etc."),
            ("ARCH-004", "Twitter Campaign", "Schedule 12 tweets every 2 hours"),
            ("", "         └─ Tweet Types", "Hook, Authority, Story, Emotional, CTA"),
            ("ARCH-005", "Offer Tracking", f"Generate UTM links for: {offer_url}"),
            ("", "         └─ Click Tracking", "Monitor clicks and conversions"),
            ("ARCH-006", "Analytics Feedback", "Track engagement metrics for optimization"),
            ("", "         └─ Checkback Periods", "1h, 6h, 24h, 72h, 7d"),
            ("ARCH-007", "API Endpoint", "POST /api/orchestrator/pipeline/start"),
            ("ARCH-008", "Dashboard Widget", "Real-time pipeline status visualization"),
        ]

        for arch_id, step_name, description in steps:
            if arch_id:
                logger.info(f"[{arch_id}] {step_name:<25} → {description}")
            else:
                logger.info(f"         {step_name:<25} → {description}")

        logger.info("\n✅ Dry run complete. To execute for real, remove --dry-run flag")
        return

    # Run actual pipeline
    logger.info("\n🎬 Starting Full Pipeline Execution...\n")

    try:
        # Create pipeline configuration
        config = PipelineConfig(
            theme=theme,
            num_parts=num_parts,
            character=character,
            publish_platforms=["tiktok", "instagram", "youtube"],
            schedule_tweets=True,
            tweets_per_day=12,  # Every 2 hours (ARCH-004)
            offer_url=offer_url,
            metadata={
                "test_run": True,
                "initiated_by": "test_full_pipeline.py"
            }
        )

        # Start pipeline
        pipeline_id = await orchestrator.start_pipeline(config)
        logger.info(f"✅ Pipeline started: {pipeline_id}")

        # Monitor pipeline status
        logger.info("\n📊 Monitoring pipeline progress...")
        max_wait = 300  # 5 minutes
        elapsed = 0
        poll_interval = 5

        while elapsed < max_wait:
            status = orchestrator.get_pipeline_status(pipeline_id)

            current_status = status.get("status", "unknown")
            current_step = status.get("current_step", "unknown")

            logger.info(f"[{elapsed}s] Status: {current_status} | Step: {current_step}")

            if current_status in ["completed", "failed"]:
                break

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        # Get final status
        final_status = orchestrator.get_pipeline_status(pipeline_id)

        logger.info("\n" + "="*80)
        logger.info("🏁 PIPELINE EXECUTION COMPLETE")
        logger.info("="*80)
        logger.info(f"Pipeline ID: {pipeline_id}")
        logger.info(f"Status: {final_status.get('status')}")
        logger.info(f"Theme: {final_status.get('theme')}")

        outputs = final_status.get("outputs", {})

        # Sora results
        sora_output = outputs.get("sora", {})
        if sora_output:
            logger.info(f"\n[ARCH-002] Sora Generation:")
            logger.info(f"  Video: {sora_output.get('stitched_video')}")
            analysis = sora_output.get("analysis", {})
            if analysis:
                logger.info(f"  Hook: {analysis.get('detected_hook', 'N/A')}")
                logger.info(f"  Tone: {analysis.get('tone', 'N/A')}")
                logger.info(f"  Topics: {', '.join(analysis.get('topics', []))}")

        # Publishing results
        publish_jobs = outputs.get("publish_jobs", [])
        if publish_jobs:
            logger.info(f"\n[ARCH-003] Publishing Results:")
            for job in publish_jobs:
                status_icon = "✅" if job.get("status") == "completed" else "❌"
                logger.info(f"  {status_icon} {job.get('platform')}: {job.get('status')}")

        # Twitter campaign
        twitter_output = outputs.get("twitter", {})
        if twitter_output:
            logger.info(f"\n[ARCH-004] Twitter Campaign:")
            logger.info(f"  Tweets Scheduled: {twitter_output.get('tweets_scheduled', 0)}")
            logger.info(f"  Interval: Every 2 hours")

        logger.info("\n" + "="*80)
        logger.info("✅ System Architecture Integration Test Complete!")
        logger.info("="*80)

        return final_status

    except Exception as e:
        logger.error(f"❌ Pipeline execution failed: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        # Cleanup
        await orchestrator.stop()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Test MediaPoster System Architecture Integration (ARCH-001 to ARCH-008)"
    )
    parser.add_argument(
        "--theme",
        type=str,
        default="AI automation revolutionizing content creation",
        help="Video theme/topic"
    )
    parser.add_argument(
        "--parts",
        type=int,
        default=3,
        choices=[1, 2, 3],
        help="Number of video parts"
    )
    parser.add_argument(
        "--character",
        type=str,
        default="@isaiahdupree",
        help="Sora character"
    )
    parser.add_argument(
        "--offer",
        type=str,
        default="https://blotato.com",
        help="Offer URL for traffic tracking"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without executing"
    )

    args = parser.parse_args()

    # Run the test
    asyncio.run(test_full_pipeline(
        theme=args.theme,
        num_parts=args.parts,
        character=args.character,
        offer_url=args.offer,
        dry_run=args.dry_run
    ))


if __name__ == "__main__":
    main()
