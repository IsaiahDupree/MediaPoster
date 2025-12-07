"""
Backfill TikTok analytics data into the new engagement tracking schema
"""
import json
import requests
from pathlib import Path
from sqlalchemy import create_engine, text
from datetime import datetime
from services.follower_tracking import get_or_create_follower, record_interaction, update_engagement_scores
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


def get_tiktok_thumbnail(video_url: str) -> str:
    """
    Get TikTok video thumbnail using oEmbed API
    """
    try:
        oembed_url = f"https://www.tiktok.com/oembed?url={video_url}"
        response = requests.get(oembed_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('thumbnail_url')
    except Exception as e:
        print(f"    ⚠️  Could not fetch thumbnail: {e}")
    return None

print("\n🔄 Backfilling TikTok Engagement Data...\n")

# Load TikTok data
json_file = Path(__file__).parent / 'isaiah_dupree_analytics.json'
with open(json_file, 'r') as f:
    data = json.load(f)

posts = data.get('recent_posts', [])
print(f"📊 Found {len(posts)} TikTok posts to process\n")

conn = engine.connect()

try:
    # Process each post
    for idx, post in enumerate(posts, 1):
        # Extract post data
        post_url = post.get('url', post.get('post_url', ''))
        full_caption = post.get('caption', '')
        external_post_id = post_url.split('/')[-1] if post_url else f"post_{idx}"
        posted_at = post.get('posted_at', post.get('created_at'))
        
        # Create a clean title from caption
        if full_caption:
            # Take first sentence or first 100 chars for title
            title = full_caption.split('.')[0].split('!')[0].split('?')[0]
            title = title[:100].strip()
            # Remove hashtags and emojis for cleaner title
            title = ' '.join(word for word in title.split() if not word.startswith('#'))
            title = title[:80].strip() or f"TikTok Video {idx}"
        else:
            title = f"TikTok Video {idx}"
        
        # Use full caption as description
        description = full_caption if full_caption else f"TikTok video posted on {posted_at or 'unknown date'}"
        
        # Create a meaningful slug
        slug_base = title.lower()
        slug_base = ''.join(c if c.isalnum() or c.isspace() else '' for c in slug_base)
        slug_base = '-'.join(slug_base.split())[:50]
        slug = f"{slug_base}-{external_post_id}" if slug_base else f"tiktok-{external_post_id}"
        
        print(f"Processing post {idx}/{len(posts)}: {title}")
        
        # Fetch thumbnail from TikTok
        print(f"  🖼️  Fetching thumbnail...")
        thumbnail_url = get_tiktok_thumbnail(post_url)
        if thumbnail_url:
            print(f"  ✅ Got thumbnail")
        
        # Parse date
        if posted_at:
            try:
                post_date = datetime.fromisoformat(posted_at.replace('Z', '+00:00'))
            except:
                post_date = datetime.now()
        else:
            post_date = datetime.now()
        
        # Create content item
        result = conn.execute(text("""
            INSERT INTO content_items (title, description, slug, thumbnail_url)
            VALUES (:title, :description, :slug, :thumbnail_url)
            ON CONFLICT (slug) DO UPDATE SET
                title = EXCLUDED.title,
                description = EXCLUDED.description,
                thumbnail_url = EXCLUDED.thumbnail_url
            RETURNING id
        """), {
            "title": title,
            "description": description,
            "slug": slug,
            "thumbnail_url": thumbnail_url
        })
        
        content_row = result.fetchone()
        if content_row:
            content_id = str(content_row[0])
            print(f"  ✅ Created content_item: {content_id}")
        else:
            # Content already exists, get its ID
            result = conn.execute(text("""
                SELECT id FROM content_items WHERE slug = :slug
            """), {"slug": slug})
            content_row = result.fetchone()
            content_id = str(content_row[0]) if content_row else None
            print(f"  ℹ️  Content already exists: {content_id}")
        
        if not content_id:
            print(f"  ⚠️  Skipping - couldn't get content_id")
            continue
        
        # Create content_post linking to TikTok
        result = conn.execute(text("""
            INSERT INTO content_posts (
                content_id, 
                platform, 
                external_post_id, 
                permalink_url, 
                posted_at
            )
            VALUES (:content_id, 'tiktok', :external_post_id, :permalink_url, :posted_at)
            ON CONFLICT DO NOTHING
            RETURNING id
        """), {
            "content_id": content_id,
            "external_post_id": external_post_id,
            "permalink_url": post_url,
            "posted_at": post_date
        })
        
        if result.rowcount > 0:
            print(f"  ✅ Linked to TikTok platform")
        
        # Commit the content creation so it's visible to record_interaction
        conn.commit()
        
        # Get metrics
        views = post.get('views', 0) or 0
        likes = post.get('likes', 0) or 0
        comments_count = post.get('comments', 0) or 0
        shares = post.get('shares', 0) or 0
        
        print(f"  📊 Metrics: {views} views, {likes} likes, {comments_count} comments, {shares} shares")
        
        # Since we don't have individual commenter data in the JSON,
        # we'll create aggregate interactions for the account owner
        # In real scraping, we'd get actual commenter info
        
        if likes > 0:
            # Create a generic "TikTok Users" follower for aggregate likes
            follower_id = get_or_create_follower(
                platform='tiktok',
                platform_user_id='tiktok_users_aggregate',
                username='tiktok_users',
                display_name='TikTok Users (Aggregate)'
            )
            
            # Record like interaction (aggregate)
            record_interaction(
                follower_id=follower_id,
                interaction_type='like',
                platform='tiktok',
                occurred_at=post_date,
                content_id=content_id,
                metadata={'count': likes, 'is_aggregate': True}
            )
        
        conn.commit()
        print(f"  ✅ Post processed\n")
    
    # Update all engagement scores
    print("\n📊 Calculating engagement scores...")
    update_engagement_scores()
    conn.commit()
    
    print("\n" + "="*60)
    print("✅ BACKFILL COMPLETE!")
    print("="*60)
    
    # Show summary
    result = conn.execute(text("SELECT COUNT(*) FROM content_items"))
    content_count = result.scalar()
    
    result = conn.execute(text("SELECT COUNT(*) FROM content_posts WHERE platform = 'tiktok'"))
    posts_count = result.scalar()
    
    result = conn.execute(text("SELECT COUNT(*) FROM followers"))
    followers_count = result.scalar()
    
    result = conn.execute(text("SELECT COUNT(*) FROM follower_interactions"))
    interactions_count = result.scalar()
    
    print(f"\n📊 Database Summary:")
    print(f"   • Content items: {content_count}")
    print(f"   • TikTok posts: {posts_count}")
    print(f"   • Followers tracked: {followers_count}")
    print(f"   • Interactions recorded: {interactions_count}")
    
    # Show top content
    print(f"\n🏆 Top Content:")
    result = conn.execute(text("""
        SELECT title, platform_count, platforms, total_comments, total_likes
        FROM content_cross_platform_summary
        ORDER BY total_likes DESC
        LIMIT 5
    """))
    
    for row in result:
        print(f"   • {row[0][:50]}: {row[2]} platforms, {row[3]} comments, {row[4]} likes")
    
    print("\n✅ Ready for Phase 3: API endpoints and frontend!")
    print("\n")

except Exception as e:
    conn.rollback()
    print(f"\n❌ Error: {e}\n")
    raise

finally:
    conn.close()
