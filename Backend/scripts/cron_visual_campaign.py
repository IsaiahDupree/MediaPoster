#!/usr/bin/env python3
"""
Visual Campaign Cron Job
Runs daily to:
1. Generate new Instagram carousels and TikTok picture videos
2. Render pending content
3. Post content that's due
"""
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# Configure logging
log_file = Path(__file__).parent.parent / "logs" / "visual_campaign_cron.log"
log_file.parent.mkdir(exist_ok=True)
logger.add(log_file, rotation="10 MB", retention="7 days")


async def run_daily_campaign():
    """Run daily visual content generation and scheduling."""
    from services.visual_campaign_service import get_visual_campaign_service
    
    logger.info("=" * 60)
    logger.info("VISUAL CAMPAIGN CRON - Daily Content Generation")
    logger.info("=" * 60)
    
    service = get_visual_campaign_service()
    result = await service.run_daily_visual_campaign()
    
    logger.info(f"Generated: {result.get('carousels_scheduled', 0)} carousels, {result.get('videos_scheduled', 0)} videos")
    return result


async def render_pending():
    """Render pending visual content."""
    from services.visual_remotion_renderer import get_visual_renderer
    
    logger.info("Rendering pending content...")
    renderer = get_visual_renderer()
    result = await renderer.render_pending_content()
    
    logger.info(f"Rendered: {result.get('rendered', 0)} items")
    return result


async def post_due_content():
    """Post content that's due."""
    from services.visual_poster_service import get_visual_poster_service
    
    logger.info("Posting due content...")
    poster = get_visual_poster_service()
    result = await poster.process_due_content()
    
    logger.info(f"Posted: {result.get('posted', 0)} items, Failed: {result.get('failed', 0)}")
    return result


async def main():
    """Main cron job entry point."""
    start_time = datetime.now()
    logger.info(f"Visual Campaign Cron started at {start_time}")
    
    try:
        # 1. Generate and schedule new content (once daily)
        if len(sys.argv) > 1 and sys.argv[1] == "generate":
            await run_daily_campaign()
        
        # 2. Render pending content
        await render_pending()
        
        # 3. Post due content
        await post_due_content()
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.success(f"Visual Campaign Cron completed in {elapsed:.1f}s")
        
    except Exception as e:
        logger.error(f"Visual Campaign Cron failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
