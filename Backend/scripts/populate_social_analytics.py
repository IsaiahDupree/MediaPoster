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

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, text
from services.rapidapi_social_fetcher import RapidAPISocialFetcher, Platform


async def populate_all_accounts():
    """Fetch and save analytics for all configured social accounts."""
    
    db_url = os.getenv("DATABASE_URL")
    engine = create_engine(db_url)
    fetcher = RapidAPISocialFetcher()
    
    print("=" * 60)
    print("🚀 Social Media Analytics Population")
    print(f"   Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # First, sync accounts from env
    print("\n📥 Step 1: Syncing accounts from environment...")
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
    
    print(f"   Found {len(env_accounts)} accounts in environment")
    
    # Sync to database
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
        print(f"   Added {added} new accounts to database")
    
    # Get all accounts from database
    print("\n📊 Step 2: Fetching live analytics...")
    with engine.connect() as conn:
        accounts = conn.execute(text("""
            SELECT id, platform, username FROM social_media_accounts
            WHERE is_active = TRUE
            ORDER BY platform, username
        """)).fetchall()
    
    print(f"   Processing {len(accounts)} accounts...\n")
    
    results = {"success": 0, "failed": 0, "skipped": 0, "rate_limited": 0}
    
    for acc_id, platform, username in accounts:
        try:
            data = None
            
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
                print(f"   ⏭️  {platform}/@{username} - No fetcher available")
                results["skipped"] += 1
                continue
            
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
                        bio = :bio,
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
                    "bio": data.bio[:500] if data.bio else None,
                    "pic": data.profile_pic_url,
                })
                conn.commit()
            
            print(f"   {status} {platform}/@{username}: {data.followers_count:,} followers, {data.posts_count} posts")
            
            # Rate limiting delay
            await asyncio.sleep(0.3)
            
        except Exception as e:
            print(f"   ❌ {platform}/@{username}: Error - {str(e)[:50]}")
            results["failed"] += 1
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print(f"   ✅ Successful: {results['success']}")
    print(f"   ❌ Failed: {results['failed']}")
    print(f"   ⏭️  Skipped: {results['skipped']}")
    
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
        
        print(f"\n   📈 Total Accounts: {stats[0]}")
        print(f"   👥 Total Followers: {stats[1]:,}")
        print(f"   ❤️  Total Likes: {stats[2]:,}")
        print(f"   📝 Total Posts: {stats[3]:,}")
    
    print("\n" + "=" * 60)
    print(f"✅ Complete! {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(populate_all_accounts())
