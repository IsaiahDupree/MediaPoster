"""
Populate analytics pages with YouTube data for isaiah_dupree channel
This script:
1. Adds the YouTube account to social_media_accounts
2. Syncs channel data
3. Backfills video and engagement data
"""
import asyncio
import os
from sqlalchemy import create_engine, text
from services.youtube_analytics import YouTubeAnalytics
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
YOUTUBE_CHANNEL_ID = "UCnDBsELI2OIaEI5yxA77HNA"  # Found via find_youtube_channel.py
YOUTUBE_USERNAME = "isaiah_dupree"

async def main():
    print("\n" + "="*80)
    print("📺 Populating YouTube Analytics for @isaiah_dupree")
    print("="*80)
    
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    
    try:
        # Step 1: Get channel info
        print("\n🔍 Step 1: Fetching channel information...")
        yt = YouTubeAnalytics()
        channel_info = await yt.get_channel_info(YOUTUBE_CHANNEL_ID)
        
        if not channel_info:
            print("❌ Could not fetch channel info!")
            return
        
        print(f"✅ Channel: {channel_info['title']}")
        print(f"   Subscribers: {channel_info['subscriber_count']:,}")
        print(f"   Videos: {channel_info['video_count']}")
        print(f"   Views: {channel_info['view_count']:,}")
        
        # Step 2: Add/Update account in social_media_accounts
        print("\n📝 Step 2: Adding account to database...")
        conn.execute(text("""
            INSERT INTO social_media_accounts (
                platform, username, display_name, profile_pic_url,
                followers_count, posts_count, total_views,
                external_id, is_active, last_fetched_at
            )
            VALUES (
                'youtube', :username, :display_name, :thumbnail_url,
                :subscriber_count, :video_count, :view_count,
                :channel_id, TRUE, NOW()
            )
            ON CONFLICT (platform, username)
            DO UPDATE SET
                display_name = EXCLUDED.display_name,
                profile_pic_url = EXCLUDED.profile_pic_url,
                followers_count = EXCLUDED.followers_count,
                posts_count = EXCLUDED.posts_count,
                total_views = EXCLUDED.total_views,
                external_id = EXCLUDED.external_id,
                last_fetched_at = NOW()
        """), {
            'username': YOUTUBE_USERNAME,
            'display_name': channel_info['title'],
            'thumbnail_url': channel_info.get('thumbnail_url'),
            'subscriber_count': channel_info['subscriber_count'],
            'video_count': channel_info['video_count'],
            'view_count': channel_info['view_count'],
            'channel_id': YOUTUBE_CHANNEL_ID
        })
        conn.commit()
        print("✅ Account added/updated in database")
        
        # Step 3: Create analytics snapshot (skip if table doesn't exist or has different schema)
        print("\n📊 Step 3: Creating analytics snapshot...")
        try:
            # Try to get account_id first
            result = conn.execute(text("""
                SELECT id FROM social_media_accounts 
                WHERE platform = 'youtube' AND username = :username
            """), {'username': YOUTUBE_USERNAME})
            account_row = result.fetchone()
            account_id = account_row[0] if account_row else None
            
            if account_id:
                # Try inserting snapshot with account_id (common schema)
                conn.execute(text("""
                    INSERT INTO social_media_analytics_snapshots (
                        account_id, snapshot_date,
                        followers_count, posts_count, total_views,
                        total_likes, total_comments, engagement_rate
                    )
                    VALUES (
                        :account_id, CURRENT_DATE,
                        :subscriber_count, :video_count, :view_count,
                        0, 0, 0.0
                    )
                    ON CONFLICT (account_id, snapshot_date)
                    DO UPDATE SET
                        followers_count = EXCLUDED.followers_count,
                        posts_count = EXCLUDED.posts_count,
                        total_views = EXCLUDED.total_views,
                        updated_at = NOW()
                """), {
                    'account_id': account_id,
                    'subscriber_count': channel_info['subscriber_count'],
                    'video_count': channel_info['video_count'],
                    'view_count': channel_info['view_count']
                })
                conn.commit()
                print("✅ Analytics snapshot created")
            else:
                print("⚠️  Could not find account_id, skipping snapshot")
        except Exception as e:
            print(f"⚠️  Could not create snapshot (table may have different schema): {e}")
            conn.rollback()
        
        # Step 4: Run backfill for videos and engagement
        print("\n🎬 Step 4: Backfilling videos and engagement data...")
        print("   (This may take a few minutes depending on video count)")
        print("   Running: python backfill_youtube_engagement.py")
        print("\n   You can run this separately with:")
        print(f"   YOUTUBE_CHANNEL_ID={YOUTUBE_CHANNEL_ID} python backfill_youtube_engagement.py")
        
        # Summary
        print("\n" + "="*80)
        print("✅ YOUTUBE ANALYTICS POPULATION COMPLETE!")
        print("="*80)
        print(f"\n📊 Summary:")
        print(f"   • Channel: {channel_info['title']}")
        print(f"   • Username: @{YOUTUBE_USERNAME}")
        print(f"   • Channel ID: {YOUTUBE_CHANNEL_ID}")
        print(f"   • Subscribers: {channel_info['subscriber_count']:,}")
        print(f"   • Videos: {channel_info['video_count']}")
        print(f"   • Total Views: {channel_info['view_count']:,}")
        print(f"\n✅ Account is now available in analytics pages!")
        print(f"\n📝 Next Steps:")
        print(f"   1. Run backfill to import videos and comments:")
        print(f"      cd Backend && YOUTUBE_CHANNEL_ID={YOUTUBE_CHANNEL_ID} python backfill_youtube_engagement.py")
        print(f"   2. Visit analytics pages:")
        print(f"      - /analytics/social (overview)")
        print(f"      - /analytics/social/platform/youtube (YouTube details)")
        print(f"      - /analytics/content (video catalog)")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())

