#!/usr/bin/env python3
"""
Populate Social Media Analytics Database
Fetches real data from all configured social accounts via RapidAPI and YouTube Data API.

Run: python scripts/populate_social_analytics.py
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import time

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from services.rapidapi_social_fetcher import RapidAPISocialFetcher, Platform
from loguru import logger


async def populate_all_accounts():
    """Fetch and save analytics for all configured social accounts."""
    start_time = time.time()
    
    logger.info("="*80)
    logger.info("🚀 Social Media Analytics Population")
    logger.info("="*80)
    logger.info(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("❌ DATABASE_URL not found in environment")
        return
    
    logger.info("🔌 Connecting to database...")
    engine = create_engine(db_url)
    fetcher = RapidAPISocialFetcher()
    logger.info("✅ Database connected")
    logger.info("")
    
    # First, sync accounts from env
    logger.info("="*80)
    logger.info("📥 STEP 1: Syncing Accounts from Environment")
    logger.info("="*80)
    env_accounts = []
    
    platforms_config = {
        "instagram": os.getenv("INSTAGRAM_USERNAMES", ""),
        "tiktok": os.getenv("TIKTOK_USERNAMES", ""),
        "twitter": os.getenv("TWITTER_USERNAMES", ""),
        "youtube": os.getenv("YOUTUBE_CHANNEL_IDS", ""),  # Use channel IDs for YouTube
        "threads": os.getenv("THREADS_USERNAMES", ""),
        "pinterest": os.getenv("PINTEREST_USERNAMES", ""),
        "bluesky": os.getenv("BLUESKY_USERNAMES", ""),
        "facebook": os.getenv("FACEBOOK_PAGE_NAMES", ""),
    }
    
    for platform, usernames in platforms_config.items():
        for username in usernames.split(","):
            username = username.strip()
            if username:
                env_accounts.append({"platform": platform, "username": username})
    
    logger.info(f"📋 Found {len(env_accounts)} accounts in environment")
    
    # Sync to database
    logger.info("💾 Syncing to database...")
    with engine.connect() as conn:
        added = 0
        for acc in env_accounts:
            existing = conn.execute(text("""
                SELECT id FROM social_media_accounts 
                WHERE platform = :platform AND username = :username
            """), acc).fetchone()
            
            if not existing:
                conn.execute(text("""
                    INSERT INTO social_media_accounts (platform, username, is_active)
                    VALUES (:platform, :username, TRUE)
                """), acc)
                added += 1
        conn.commit()
        logger.info(f"✅ Added {added} new accounts to database")
        logger.info("")
    
    # Get all accounts from database
    logger.info("="*80)
    logger.info("📊 STEP 2: Fetching Live Analytics")
    logger.info("="*80)
    with engine.connect() as conn:
        accounts = conn.execute(text("""
            SELECT id, platform, username FROM social_media_accounts
            WHERE is_active = TRUE
            ORDER BY platform, username
        """)).fetchall()
    
    logger.info(f"📋 Processing {len(accounts)} accounts...")
    logger.info("")
    
    results = {"success": 0, "failed": 0, "skipped": 0, "rate_limited": 0}
    total_accounts = len(accounts)
    
    for idx, (acc_id, platform, username) in enumerate(accounts, 1):
        progress = f"[{idx}/{total_accounts}]"
        logger.info(f"  {progress} 🔍 Fetching {platform}/@{username}...")
        
        try:
            data = None
            fetch_start = time.time()
            
            # Fetch based on platform
            if platform == "instagram":
                data = await fetcher.fetch_instagram_analytics(username)
            elif platform == "tiktok":
                data = await fetcher.fetch_tiktok_analytics(username)
            elif platform == "twitter":
                data = await fetcher.fetch_twitter_analytics(username)
            elif platform == "youtube":
                data = await fetcher.fetch_youtube_analytics(username)
            else:
                logger.info(f"    ⏭️  No fetcher available for {platform}")
                results["skipped"] += 1
                continue
            
            fetch_time = time.time() - fetch_start
            
            # Check if we got real data
            if data and (data.followers_count > 0 or data.posts_count > 0):
                status = "✅"
                results["success"] += 1
            elif data:
                status = "⚠️"
                results["success"] += 1  # Still count as success, just no data yet
            else:
                status = "❌"
                results["failed"] += 1
                logger.error(f"    ❌ Failed to fetch data ({fetch_time:.1f}s)")
                continue
            
            # Update database
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE social_media_accounts SET
                        followers_count = :followers,
                        following_count = :following,
                        posts_count = :posts,
                        total_views = :views,
                        total_likes = :likes,
                        engagement_rate = :engagement,
                        is_verified = :verified,
                        profile_pic_url = :pic,
                        last_fetched_at = NOW()
                    WHERE id = :id
                """), {
                    "id": acc_id,
                    "followers": data.followers_count,
                    "following": data.following_count,
                    "posts": data.posts_count,
                    "views": data.total_views,
                    "likes": data.total_likes,
                    "engagement": data.engagement_rate,
                    "verified": data.is_verified,
                    "pic": data.profile_pic_url,
                })
                conn.commit()
            
            followers_str = f"{data.followers_count:,}" if data.followers_count else "0"
            posts_str = f"{data.posts_count:,}" if data.posts_count else "0"
            logger.info(f"    {status} {followers_str} followers, {posts_str} posts ({fetch_time:.1f}s)")
            
            # Rate limiting
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"    ❌ Error: {str(e)[:100]}")
            results["failed"] += 1
    
    # Print summary
    total_elapsed = time.time() - start_time
    logger.info("")
    logger.info("="*80)
    logger.info("📊 SUMMARY")
    logger.info("="*80)
    logger.info(f"✅ Successful: {results['success']}")
    logger.info(f"❌ Failed: {results['failed']}")
    logger.info(f"⏭️  Skipped: {results['skipped']}")
    logger.info(f"⏱️  Total time: {total_elapsed:.1f}s ({total_elapsed/60:.1f} minutes)")
    logger.info("")
    
    # Get final stats
    with engine.connect() as conn:
        stats = conn.execute(text("""
            SELECT 
                COUNT(*) as total,
                SUM(followers_count) as followers,
                SUM(total_likes) as likes,
                SUM(posts_count) as posts
            FROM social_media_accounts
            WHERE is_active = TRUE
        """)).fetchone()
        
        logger.info("📈 Database Statistics:")
        logger.info(f"   📊 Total Accounts: {stats[0]}")
        logger.info(f"   👥 Total Followers: {stats[1]:,}" if stats[1] else "   👥 Total Followers: 0")
        logger.info(f"   ❤️  Total Likes: {stats[2]:,}" if stats[2] else "   ❤️  Total Likes: 0")
        logger.info(f"   📝 Total Posts: {stats[3]:,}" if stats[3] else "   📝 Total Posts: 0")
    
    logger.info("")
    logger.info("="*80)
    logger.info(f"✅ Complete! {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(populate_all_accounts())
