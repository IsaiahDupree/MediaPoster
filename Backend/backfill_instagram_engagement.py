"""
Backfill Instagram analytics data into the content tracking schema
Imports posts, engagement metrics, and thumbnails
"""
import asyncio
import json
from sqlalchemy import create_engine, text
from datetime import datetime
from services.instagram_analytics import fetch_instagram_analytics
from services.follower_tracking import get_or_create_follower, update_engagement_scores
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


async def main():
    print("\n🔄 Backfilling Instagram Engagement Data...\n")
    
    # Get Instagram username from environment or prompt
    username = os.getenv("INSTAGRAM_USERNAME")
    if not username:
        username = input("Enter your Instagram username: ")
    
    # Fetch analytics
    print(f"📸 Fetching Instagram analytics for: @{username}\n")
    data = await fetch_instagram_analytics(username, max_posts=20)
    
    # Save raw data
    output_file = f"instagram_analytics_{username}.json"
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n💾 Saved raw data to {output_file}\n")
    
    # Import into database
    conn = engine.connect()
    
    try:
        posts = data.get('posts', [])
        print(f"📊 Processing {len(posts)} Instagram posts\n")
        
        for idx, post in enumerate(posts, 1):
            media_id = post['media_id']
            shortcode = post['shortcode']
            caption = post.get('caption', '')
            
            print(f"Processing post {idx}/{len(posts)}: {shortcode}")
            
            # Extract title from caption (first sentence)
            if caption:
                title = caption.split('.')[0].split('!')[0].split('?')[0]
                title = title[:100].strip()
                # Remove hashtags for cleaner title
                title = ' '.join(word for word in title.split() if not word.startswith('#'))
                title = title[:80].strip() or f"Instagram Post {idx}"
            else:
                title = f"Instagram Post {idx}"
            
            # Use full caption as description
            description = caption if caption else f"Instagram post"
            
            # Create slug from title
            slug_base = title.lower()
            slug_base = ''.join(c if c.isalnum() or c.isspace() else '' for c in slug_base)
            slug_base = '-'.join(slug_base.split())[:50]
            slug = f"{slug_base}-{shortcode}" if slug_base else f"instagram-{shortcode}"
            
            # Parse posted date
            taken_at = post.get('taken_at')
            if taken_at:
                try:
                    post_date = datetime.fromtimestamp(taken_at)
                except:
                    post_date = datetime.now()
            else:
                post_date = datetime.now()
            
            # Get thumbnail
            thumbnail_url = post.get('thumbnail_url')
            if thumbnail_url:
                print(f"  ✅ Got thumbnail")
            
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
                "description": description or f"Instagram post posted on {post_date.strftime('%Y-%m-%d')}",
                "slug": slug,
                "thumbnail_url": thumbnail_url
            })
            
            content_row = result.fetchone()
            if content_row:
                content_id = str(content_row[0])
                print(f"  ✅ Content item: {content_id}")
            else:
                result = conn.execute(text("""
                    SELECT id FROM content_items WHERE slug = :slug
                """), {"slug": slug})
                content_row = result.fetchone()
                content_id = str(content_row[0]) if content_row else None
            
            if not content_id:
                print(f"  ⚠️  Skipping - couldn't get content_id")
                continue
            
            # Link to Instagram platform
            post_url = post.get('url')
            result = conn.execute(text("""
                INSERT INTO content_posts (content_id, platform, external_post_id, permalink_url, posted_at)
                VALUES (:content_id, 'instagram', :external_post_id, :permalink_url, :posted_at)
                ON CONFLICT (platform, external_post_id) DO NOTHING
            """), {
                "content_id": content_id,
                "external_post_id": shortcode,
                "permalink_url": post_url,
                "posted_at": post_date
            })
            
            if result.rowcount > 0:
                print(f"  ✅ Linked to Instagram")
            
            # Extract hashtags from caption
            if caption:
                hashtags = [word[1:].lower() for word in caption.split() if word.startswith('#')]
                for tag in hashtags[:10]:  # Limit to 10 tags
                    conn.execute(text("""
                        INSERT INTO content_tags (content_id, tag_type, tag_value)
                        VALUES (:content_id, 'hashtag', :tag_value)
                        ON CONFLICT DO NOTHING
                    """), {
                        "content_id": content_id,
                        "tag_value": tag
                    })
            
            # Commit so content is visible
            conn.commit()
            
            # Get metrics
            like_count = post.get('like_count', 0)
            comment_count = post.get('comment_count', 0)
            play_count = post.get('play_count', 0)
            
            print(f"  📊 {like_count} likes, {comment_count} comments, {play_count} plays")
            
            # Record aggregate likes (no individual liker data from API)
            if like_count > 0:
                follower_id = get_or_create_follower(
                    platform='instagram',
                    platform_user_id='instagram_users_aggregate',
                    username='instagram_users',
                    display_name='Instagram Users (Aggregate)'
                )
                
                from services.follower_tracking import record_interaction
                record_interaction(
                    follower_id=follower_id,
                    content_id=content_id,
                    platform='instagram',
                    interaction_type='like',
                    occurred_at=post_date,
                    metadata={'count': like_count, 'is_aggregate': True}
                )
            
            print(f"  ✅ Post processed\n")
        
        # Calculate engagement scores
        print("\n📊 Calculating engagement scores...")
        update_engagement_scores()
        
        # Get summary stats
        result = conn.execute(text("""
            SELECT COUNT(*) FROM content_items
        """))
        content_count = result.fetchone()[0]
        
        result = conn.execute(text("""
            SELECT COUNT(*) FROM content_posts WHERE platform = 'instagram'
        """))
        instagram_count = result.fetchone()[0]
        
        result = conn.execute(text("""
            SELECT COUNT(*) FROM followers WHERE platform = 'instagram'
        """))
        follower_count = result.fetchone()[0]
        
        result = conn.execute(text("""
            SELECT COUNT(*) FROM follower_interactions WHERE platform = 'instagram'
        """))
        interaction_count = result.fetchone()[0]
        
        print("\n" + "="*60)
        print("✅ INSTAGRAM BACKFILL COMPLETE!")
        print("="*60)
        print(f"\n📊 Database Summary:")
        print(f"   • Content items: {content_count}")
        print(f"   • Instagram posts: {instagram_count}")
        print(f"   • Followers tracked: {follower_count}")
        print(f"   • Interactions recorded: {interaction_count}")
        
        # Show profile stats
        profile = data.get('profile', {})
        print(f"\n👤 Profile Stats:")
        print(f"   • @{profile.get('username')}")
        print(f"   • {profile.get('follower_count', 0):,} followers")
        print(f"   • {profile.get('media_count', 0)} total posts")
        print(f"   • {'✅ Verified' if profile.get('is_verified') else '❌ Not verified'}")
        
        # Show top posts
        result = conn.execute(text("""
            SELECT 
                ci.title,
                COALESCE(SUM(
                    CASE 
                        WHEN fi.metadata::jsonb->>'count' IS NOT NULL 
                        THEN (fi.metadata::jsonb->>'count')::int 
                        ELSE 1 
                    END
                ), 0) as total_likes
            FROM content_items ci
            JOIN content_posts cp ON ci.id = cp.content_id
            LEFT JOIN follower_interactions fi ON ci.id = fi.content_id
            WHERE cp.platform = 'instagram' AND fi.interaction_type = 'like'
            GROUP BY ci.id, ci.title
            ORDER BY total_likes DESC
            LIMIT 5
        """))
        
        top_posts = result.fetchall()
        if top_posts:
            print(f"\n🏆 Top Instagram Posts:")
            for post in top_posts:
                print(f"   • {post[0]}: {post[1]:,} likes")
        
        print(f"\n✅ Ready for analytics dashboard!")
        
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
