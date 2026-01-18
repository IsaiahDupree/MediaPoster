#!/usr/bin/env python3
"""
Start Twitter Campaign System
Run this after Docker/Supabase is running to:
1. Apply the database migration
2. Generate and schedule 60 tweets/day
3. Start the background scheduler
"""
import os
import sys
import asyncio
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from sqlalchemy import create_engine, text
from loguru import logger


def apply_migration():
    """Apply the Twitter campaign migration."""
    logger.info("📦 Applying Twitter campaign migration...")
    
    migration_path = Path(__file__).parent.parent.parent / "supabase/migrations/20260113000000_twitter_campaign_system.sql"
    
    if not migration_path.exists():
        logger.error(f"Migration file not found: {migration_path}")
        return False
    
    engine = create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"))
    
    with open(migration_path, 'r') as f:
        sql = f.read()
    
    try:
        with engine.connect() as conn:
            # Split by semicolons and execute each statement
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            for stmt in statements:
                if stmt and not stmt.startswith('--'):
                    try:
                        conn.execute(text(stmt))
                    except Exception as e:
                        # Skip errors for already existing objects
                        if 'already exists' not in str(e).lower():
                            logger.warning(f"Statement warning: {e}")
            conn.commit()
        
        logger.success("✅ Migration applied successfully")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


async def generate_and_schedule_tweets():
    """Generate 60 tweets and schedule them."""
    from services.twitter_campaign_service import get_campaign_service
    
    service = get_campaign_service()
    
    logger.info("🐦 Running daily Twitter campaign...")
    result = await service.run_daily_campaign()
    
    logger.success(f"✅ Generated and scheduled {result['total_scheduled']} tweets")
    logger.info(f"   Products: {', '.join(result['products'])}")
    
    return result


async def start_scheduler():
    """Start the background scheduler."""
    from services.twitter_campaign_scheduler import start_twitter_campaign_scheduler
    
    logger.info("🚀 Starting Twitter campaign scheduler...")
    scheduler = await start_twitter_campaign_scheduler()
    
    logger.success("✅ Scheduler running - tweets will be posted automatically")
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        logger.info("Stopping scheduler...")
        from services.twitter_campaign_scheduler import stop_twitter_campaign_scheduler
        await stop_twitter_campaign_scheduler()


async def main():
    """Main entry point."""
    print("=" * 60)
    print("Twitter Campaign System - 60 tweets/day")
    print("Products: Everreach, BlankLogo, Apple App Kit")
    print("=" * 60)
    print()
    
    # Step 1: Apply migration
    if not apply_migration():
        print("\n❌ Failed to apply migration. Is Docker/Supabase running?")
        print("   Run: docker start && supabase start")
        return
    
    # Step 2: Generate and schedule tweets
    result = await generate_and_schedule_tweets()
    
    # Step 3: Ask if user wants to start scheduler
    print()
    print("=" * 60)
    print("Tweets scheduled! Options:")
    print("  1. Start background scheduler (posts automatically)")
    print("  2. Exit (use API to start scheduler later)")
    print("=" * 60)
    
    choice = input("\nStart scheduler now? (y/n): ").strip().lower()
    
    if choice == 'y':
        await start_scheduler()
    else:
        print("\nTo start scheduler later:")
        print("  POST http://localhost:5555/api/twitter-campaign/scheduler/start")
        print("\nTo manually process due tweets:")
        print("  POST http://localhost:5555/api/twitter-campaign/process-due")


if __name__ == "__main__":
    asyncio.run(main())
