#!/usr/bin/env python3
"""
Daily Twitter Campaign Cron Job
Run this via launchd or cron to generate and schedule 60 tweets daily.
"""
import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from loguru import logger

# Configure logging for cron
log_file = Path(__file__).parent.parent / "logs" / "twitter_campaign.log"
log_file.parent.mkdir(exist_ok=True)
logger.add(log_file, rotation="1 day", retention="7 days")


async def run_daily_campaign():
    """Run the daily Twitter campaign generation."""
    logger.info("=" * 60)
    logger.info(f"Twitter Campaign Cron Job - {datetime.now()}")
    logger.info("=" * 60)
    
    try:
        from services.twitter_campaign_service import get_campaign_service
        
        service = get_campaign_service()
        result = await service.run_daily_campaign()
        
        logger.success(f"✅ Generated {result['total_scheduled']} tweets")
        logger.info(f"Products: {', '.join(result['products'])}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Campaign generation failed: {e}")
        raise


async def process_due_tweets():
    """Process any tweets that are due for posting."""
    try:
        from services.twitter_campaign_service import get_campaign_service
        
        service = get_campaign_service()
        result = await service.process_due_tweets()
        
        if result['processed'] > 0:
            logger.info(f"Processed {result['processed']} due tweets: "
                       f"✅ {result['success']} | ❌ {result['failed']}")
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Failed to process due tweets: {e}")
        raise


async def main():
    """Main entry point for cron job."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Twitter Campaign Cron Job')
    parser.add_argument('--generate', action='store_true', help='Generate daily tweets')
    parser.add_argument('--process', action='store_true', help='Process due tweets')
    parser.add_argument('--all', action='store_true', help='Run both generate and process')
    
    args = parser.parse_args()
    
    if args.all or (not args.generate and not args.process):
        await run_daily_campaign()
        await process_due_tweets()
    elif args.generate:
        await run_daily_campaign()
    elif args.process:
        await process_due_tweets()


if __name__ == "__main__":
    asyncio.run(main())
