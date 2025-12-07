"""
Test Phase 1 schema with sample data
"""
from sqlalchemy import create_engine, text
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")

print("\n🧪 Testing Phase 1 Schema...\n")

engine = create_engine(DATABASE_URL)
conn = engine.connect()

try:
    # Test 1: Create content item
    print("📝 Test 1: Creating content item...")
    result = conn.execute(text("""
        INSERT INTO content_items (title, description, slug)
        VALUES ('How to Automate TikTok', 'A guide to social media automation', 'automate-tiktok')
        RETURNING id, title
    """))
    content = result.fetchone()
    content_id = content[0]
    print(f"   ✅ Created: {content[1]} (ID: {content_id})")
    
    # Test 2: Link to platform posts
    print("\n📝 Test 2: Linking to platform posts...")
    conn.execute(text("""
        INSERT INTO content_posts (content_id, platform, external_post_id, permalink_url, posted_at)
        VALUES 
          (:content_id, 'tiktok', 'tt_123', 'https://tiktok.com/@me/video/123', NOW() - INTERVAL '2 days'),
          (:content_id, 'instagram', 'ig_456', 'https://instagram.com/p/456', NOW() - INTERVAL '1 day')
    """), {"content_id": content_id})
    print("   ✅ Linked to TikTok and Instagram")
    
    # Test 3: Create follower
    print("\n📝 Test 3: Creating follower...")
    result = conn.execute(text("""
        INSERT INTO followers (platform, platform_user_id, username, display_name, follower_count)
        VALUES ('tiktok', 'user_amy123', 'creator_amy', 'Amy | Creator', 15000)
        RETURNING id, username
    """))
    follower = result.fetchone()
    follower_id = follower[0]
    print(f"   ✅ Created: {follower[1]} (ID: {follower_id})")
    
    # Test 4: Record interactions
    print("\n📝 Test 4: Recording follower interactions...")
    conn.execute(text("""
        INSERT INTO follower_interactions (follower_id, content_id, interaction_type, interaction_value, occurred_at, platform)
        VALUES 
          (:follower_id, :content_id, 'comment', 'This is exactly what I needed! 🔥', NOW() - INTERVAL '1 day', 'tiktok'),
          (:follower_id, :content_id, 'like', NULL, NOW() - INTERVAL '1 day', 'tiktok'),
          (:follower_id, :content_id, 'share', NULL, NOW() - INTERVAL '12 hours', 'tiktok')
    """), {"follower_id": follower_id, "content_id": content_id})
    print("   ✅ Recorded 3 interactions (comment, like, share)")
    
    # Test 5: Calculate engagement score
    print("\n📝 Test 5: Calculating engagement score...")
    result = conn.execute(text("""
        INSERT INTO follower_engagement_scores (
          follower_id, 
          comment_count, 
          like_count, 
          share_count,
          total_interactions,
          engagement_score,
          engagement_tier,
          first_interaction,
          last_interaction,
          last_calculated_at
        )
        VALUES (
          :follower_id, 
          1, 
          1, 
          1,
          3,
          calculate_engagement_score(1, 1, 1, 0, 0, 0),
          determine_engagement_tier(calculate_engagement_score(1, 1, 1, 0, 0, 0)),
          NOW() - INTERVAL '1 day',
          NOW() - INTERVAL '12 hours',
          NOW()
        )
        RETURNING engagement_score, engagement_tier
    """), {"follower_id": follower_id})
    score = result.fetchone()
    print(f"   ✅ Score: {score[0]} | Tier: {score[1]}")
    
    # Test 6: Query views
    print("\n📝 Test 6: Querying views...")
    
    # Content cross-platform summary
    result = conn.execute(text("""
        SELECT title, platform_count, platforms, total_comments, total_likes
        FROM content_cross_platform_summary
        WHERE content_id = :content_id
    """), {"content_id": content_id})
    content_summary = result.fetchone()
    print(f"   ✅ Content Summary: {content_summary[0]}")
    print(f"      - Platforms: {content_summary[1]} ({content_summary[2]})")
    print(f"      - Engagement: {content_summary[3]} comments, {content_summary[4]} likes")
    
    # Top engaged followers
    result = conn.execute(text("""
        SELECT username, engagement_score, engagement_tier, comment_count
        FROM top_engaged_followers
        WHERE follower_id = :follower_id
    """), {"follower_id": follower_id})
    follower_summary = result.fetchone()
    print(f"\n   ✅ Top Follower: @{follower_summary[0]}")
    print(f"      - Score: {follower_summary[1]} | Tier: {follower_summary[2]}")
    print(f"      - Comments: {follower_summary[3]}")
    
    # Activity timeline
    result = conn.execute(text("""
        SELECT username, interaction_type, interaction_value, occurred_at
        FROM follower_activity_timeline
        WHERE follower_id = :follower_id
        ORDER BY occurred_at DESC
        LIMIT 3
    """), {"follower_id": follower_id})
    print(f"\n   ✅ Recent Activity:")
    for row in result:
        time = row[3].strftime("%b %d, %I:%M %p")
        if row[2]:
            print(f"      - {time}: {row[1]} - \"{row[2][:50]}...\"")
        else:
            print(f"      - {time}: {row[1]}")
    
    conn.commit()
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED!")
    print("="*60)
    print("\nPhase 1 schema is working correctly! 🎉")
    print("\nTest data created:")
    print(f"  - Content ID: {content_id}")
    print(f"  - Follower ID: {follower_id}")
    print("\nYou can now:")
    print("  1. Query the views to see cross-platform summaries")
    print("  2. Start building API endpoints")
    print("  3. Create frontend dashboards")
    print("\n")
    
except Exception as e:
    conn.rollback()
    print(f"\n❌ Test failed: {e}\n")
    raise
finally:
    conn.close()
