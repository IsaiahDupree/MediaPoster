"""
Orchestrator Pipeline Demo (ARCH-001 to ARCH-007)
==================================================
Demonstrates the complete System Architecture Integration workflow.

Usage:
    # Start a simulated pipeline
    python demo_orchestrator_complete.py --theme "AI automation trends"

    # Check status
    python demo_orchestrator_complete.py --status <pipeline_id>

    # List pipelines
    python demo_orchestrator_complete.py --list
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import argparse
from loguru import logger
from services.master_orchestrator import MasterOrchestrator, PipelineConfig
from services.event_bus import EventBus


async def demo_pipeline(theme: str, num_parts: int = 3):
    """Demonstrate a complete pipeline execution."""
    logger.info("🎬 Orchestrator Pipeline Demo")
    logger.info("=" * 70)

    event_bus = EventBus.get_instance()
    orchestrator = MasterOrchestrator.get_instance(event_bus=event_bus, use_db=True)

    config = PipelineConfig(
        theme=theme,
        num_parts=num_parts,
        character="@isaiahdupree",
        publish_platforms=["tiktok", "instagram", "youtube"],
        schedule_tweets=True,
        tweets_per_day=12,
        offer_url="https://example.com/offer",
        metadata={"demo": True}
    )

    logger.info(f"📋 Config: {theme}, {num_parts} parts")
    pipeline_id = await orchestrator.start_pipeline(config)
    logger.success(f"✅ Pipeline started: {pipeline_id}")

    return pipeline_id


async def check_status(pipeline_id: str):
    """Check pipeline status."""
    orchestrator = MasterOrchestrator.get_instance()
    status = await orchestrator.get_pipeline_status(pipeline_id)

    if "error" in status:
        logger.error(f"❌ {status['error']}")
        return

    logger.info(f"📊 Status: {status.get('status')}")
    logger.info(f"   Theme: {status.get('theme')}")
    logger.info(f"   Started: {status.get('started_at')}")


async def list_pipelines():
    """List recent pipelines."""
    orchestrator = MasterOrchestrator.get_instance()
    pipelines = await orchestrator.list_pipelines(limit=10)

    logger.info(f"📋 Recent Pipelines ({len(pipelines)}):")
    for p in pipelines:
        logger.info(f"   {p.get('pipeline_id')}: {p.get('theme')} ({p.get('status')})")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", type=str)
    parser.add_argument("--num-parts", type=int, default=3)
    parser.add_argument("--status", type=str)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.status:
        asyncio.run(check_status(args.status))
    elif args.list:
        asyncio.run(list_pipelines())
    elif args.theme:
        asyncio.run(demo_pipeline(args.theme, args.num_parts))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
