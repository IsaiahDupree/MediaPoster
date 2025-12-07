"""
Quick script to import TikTok analytics data into the dashboard
"""
from sqlalchemy import create_engine, text
import json
import uuid
from datetime import datetime

# Database connection
DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
engine = create_engine(DATABASE_URL)
conn = engine.connect()

print("\n🚀 Importing TikTok Analytics Data...\n")

# 1. Get or create workspace
print("1️⃣ Checking workspace...")
result = conn.execute(text("SELECT id FROM workspaces LIMIT 1"))
row = result.fetchone()

if row:
    workspace_id = str(row[0])
    print(f"   ✅ Using existing workspace: {workspace_id[:8]}...")
else:
    workspace_id = str(uuid.uuid4())
    conn.execute(text("""
        INSERT INTO workspaces (id, name, created_at, updated_at)
        VALUES (:id, 'Default Workspace', NOW(), NOW())
    """), {"id": workspace_id})
    conn.commit()
    print(f"   ✅ Created new workspace: {workspace_id[:8]}...")

# 2. Create social account for TikTok
print("\n2️⃣ Creating TikTok account...")
account_id = str(uuid.uuid4())

try:
    conn.execute(text("""
        INSERT INTO social_accounts (
            id, workspace_id, platform, handle, display_name, 
            status, created_at, updated_at
        ) VALUES (
            :id, :workspace_id, 'tiktok', 'isaiah_dupree', 
            'Isaiah Dupree', 'connected', NOW(), NOW()
        )
    """), {"id": account_id, "workspace_id": workspace_id})
    conn.commit()
    print(f"   ✅ Account created: @isaiah_dupree (TikTok)")
except Exception as e:
    if "duplicate key" in str(e).lower():
        print("   ⚠️  Account already exists, using existing...")
        result = conn.execute(text("""
            SELECT id FROM social_accounts 
            WHERE platform = 'tiktok' AND handle = 'isaiah_dupree'
        """))
        account_id = str(result.fetchone()[0])
    else:
        raise

# 3. Load TikTok analytics data
print("\n3️⃣ Loading analytics data...")
with open('isaiah_dupree_analytics.json') as f:
    data = json.load(f)

profile = data.get('profile', {})
analytics = data.get('analytics', {})
posts = data.get('recent_posts', [])

print(f"   📊 Profile: {profile.get('username', 'N/A')}")
print(f"   📊 Followers: {profile.get('followers', 0):,}")
print(f"   📊 Posts: {len(posts)}")
print(f"   📊 Total Views: {analytics.get('total_views', 0):,}")
print(f"   📊 Total Likes: {analytics.get('total_likes', 0):,}")

# 4. Save analytics snapshot
print("\n4️⃣ Saving analytics snapshot...")
try:
    conn.execute(text("""
        INSERT INTO social_analytics_snapshots (
            social_account_id, snapshot_date,
            followers_count, following_count, posts_count,
            total_views, total_likes, total_comments, total_shares,
            engagement_rate,
            created_at
        ) VALUES (
            :account_id, CURRENT_DATE,
            :followers, :following, :posts,
            :views, :likes, :comments, :shares,
            :engagement,
            NOW()
        )
        ON CONFLICT (social_account_id, snapshot_date) 
        DO UPDATE SET
            total_views = EXCLUDED.total_views,
            total_likes = EXCLUDED.total_likes
    """), {
        "account_id": account_id,
        "followers": profile.get('followers', 0),
        "following": profile.get('following', 0),
        "posts": len(posts),
        "views": analytics.get('total_views', 0),
        "likes": analytics.get('total_likes', 0),
        "comments": analytics.get('total_comments', 0),
        "shares": analytics.get('total_shares', 0),
        "engagement": analytics.get('engagement_rate', 0)
    })
    conn.commit()
    print("   ✅ Snapshot saved!")
except Exception as e:
    print(f"   ⚠️  Snapshot error: {e}")

# 5. Enable monitoring
print("\n5️⃣ Enabling analytics monitoring...")
try:
    conn.execute(text("""
        INSERT INTO social_analytics_config (
            social_account_id, monitoring_enabled, 
            provider_name, posts_per_fetch
        ) VALUES (
            :account_id, TRUE, 'rapidapi_tiktok', 50
        )
        ON CONFLICT (social_account_id) DO NOTHING
    """), {"account_id": account_id})
    conn.commit()
    print("   ✅ Monitoring enabled!")
except Exception as e:
    print(f"   ⚠️  Config error: {e}")

# 6. Save posts (first 10 for demo)
print("\n6️⃣ Saving posts...")
posts_saved = 0
for post in posts[:10]:
    try:
        conn.execute(text("""
            INSERT INTO social_posts_analytics (
                social_account_id, external_post_id, platform,
                post_url, caption, media_type, duration,
                posted_at, created_at
            ) VALUES (
                :account_id, :post_id, 'tiktok',
                :url, :caption, 'video', :duration,
                :posted_at, NOW()
            )
            ON CONFLICT (platform, external_post_id) DO NOTHING
        """), {
            "account_id": account_id,
            "post_id": post.get('id', ''),
            "url": post.get('url', ''),
            "caption": post.get('caption', '')[:500],
            "duration": post.get('duration', 0),
            "posted_at": post.get('posted_at')
        })
        conn.commit()
        posts_saved += 1
    except Exception as e:
        print(f"   ⚠️  Post save error: {e}")

print(f"   ✅ Saved {posts_saved} posts!")

# Done!
conn.close()

print("\n" + "="*60)
print("✅ IMPORT COMPLETE!")
print("="*60)
print("\n📊 Your dashboard is now populated with data!")
print("\n🌐 View it at:")
print("   http://localhost:3000/analytics/social")
print("\n📱 TikTok platform view:")
print("   http://localhost:3000/analytics/social/platform/tiktok")
print("\n" + "="*60 + "\n")
