"""
Backfill YouTube analytics data into the content tracking schema
Imports videos, comments, and actual follower engagement
"""
import asyncio
import json
from sqlalchemy import create_engine, text
from datetime import datetime
from services.youtube_analytics import fetch_youtube_analytics
from services.follower_tracking import get_or_create_follower, record_interaction, analyze_sentiment, update_engagement_scores
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

async def main():
    print("\n🔄 Backfilling YouTube Engagement Data...\n")
    
    # Get YouTube channel ID from environment or prompt
    channel_id = os.getenv("YOUTUBE_CHANNEL_ID")
    if not channel_id:
        channel_id = input("Enter your YouTube channel ID: ")
    
    # Fetch analytics
    print(f"📺 Fetching YouTube analytics for channel: {channel_id}\n")
    data = await fetch_youtube_analytics(channel_id, max_videos=20)
    
    # Save raw data
    output_file = f"youtube_analytics_{channel_id}.json"
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n💾 Saved raw data to {output_file}\n")
    
    # Import into database
    conn = engine.connect()
    
    try:
        videos = data.get('videos', [])
        print(f"📊 Processing {len(videos)} YouTube videos\n")
        
        for idx, video in enumerate(videos, 1):
            video_id = video['video_id']
            title = video['title']
            description = video.get('description', '')[:500]  # Truncate for storage
            
            print(f"Processing video {idx}/{len(videos)}: {title[:60]}...")
            
            # Parse published date
            published_at = video.get('published_at')
            if published_at:
                try:
                    video_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                except:
                    video_date = datetime.now()
            else:
                video_date = datetime.now()
            
            # Create slug from title
            slug_base = title.lower()
            slug_base = ''.join(c if c.isalnum() or c.isspace() else '' for c in slug_base)
            slug_base = '-'.join(slug_base.split())[:50]
            slug = f"{slug_base}-{video_id}" if slug_base else f"youtube-{video_id}"
            
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
                "description": description or f"YouTube video: {title}",
                "slug": slug,
                "thumbnail_url": video.get('thumbnail_url')
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
            
            # Link to YouTube platform
            result = conn.execute(text("""
                INSERT INTO content_posts (content_id, platform, external_post_id, permalink_url, posted_at)
                VALUES (:content_id, 'youtube', :external_post_id, :permalink_url, :posted_at)
                ON CONFLICT (platform, external_post_id) DO NOTHING
            """), {
                "content_id": content_id,
                "external_post_id": video_id,
                "permalink_url": video['url'],
                "posted_at": video_date
            })
            
            if result.rowcount > 0:
                print(f"  ✅ Linked to YouTube")
            
            # Add tags from video tags
            for tag in video.get('tags', [])[:10]:  # Limit to 10 tags
                conn.execute(text("""
                    INSERT INTO content_tags (content_id, tag, platform)
                    VALUES (:content_id, :tag, 'youtube')
                    ON CONFLICT DO NOTHING
                """), {
                    "content_id": content_id,
                    "tag": tag.lower()
                })
            
            # Commit so content is visible
            conn.commit()
            
            # Get metrics
            view_count = video.get('view_count', 0)
            like_count = video.get('like_count', 0)
            comment_count = video.get('comment_count', 0)
            
            print(f"  📊 {view_count:,} views, {like_count} likes, {comment_count} comments")
            
            # Process comments (REAL FOLLOWER DATA!)
            comments = video.get('comments', [])
            if comments:
                print(f"  💬 Processing {len(comments)} comments with commenter data...")
                
                for comment in comments:
                    # Get or create follower from YouTube commenter
                    follower_id = get_or_create_follower(
                        platform='youtube',
                        platform_user_id=comment['author_channel_id'] or f"yt_{comment['author_name']}",
                        username=comment['author_name'],
                        display_name=comment['author_name'],
                        profile_url=comment.get('author_channel_url'),
                        avatar_url=comment.get('author_profile_image')
                    )
                    
                    # Analyze sentiment of comment
                    sentiment_score, sentiment_label = analyze_sentiment(comment['text'])
                    
                    # Parse comment date
                    comment_date = datetime.fromisoformat(comment['published_at'].replace('Z', '+00:00'))
                    
                    # Record comment interaction
                    record_interaction(
                        follower_id=follower_id,
                        content_id=content_id,
                        platform='youtube',
                        interaction_type='comment',
                        interaction_value=comment['text'],
                        occurred_at=comment_date,
                        sentiment_score=sentiment_score,
                        sentiment_label=sentiment_label,
                        metadata={
                            'comment_id': comment['comment_id'],
                            'like_count': comment.get('like_count', 0),
                            'is_reply': comment.get('is_reply', False)
                        }
                    )
                
                print(f"  ✅ Recorded {len(comments)} comments from real users")
            
            # Record aggregate likes (since we don't have individual liker data)
            if like_count > 0:
                follower_id = get_or_create_follower(
                    platform='youtube',
                    platform_user_id='youtube_users_aggregate',
                    username='youtube_users',
                    display_name='YouTube Users (Aggregate)'
                )
                
                record_interaction(
                    follower_id=follower_id,
                    content_id=content_id,
                    platform='youtube',
                    interaction_type='like',
                    occurred_at=video_date,
                    metadata={'count': like_count, 'is_aggregate': True}
                )
            
            print(f"  ✅ Video processed\n")
        
        # Calculate engagement scores
        print("\n📊 Calculating engagement scores...")
        update_engagement_scores()  # No parameters - updates all followers
        
        # Get summary stats
        result = conn.execute(text("""
            SELECT COUNT(*) FROM content_items
        """))
        content_count = result.fetchone()[0]
        
        result = conn.execute(text("""
            SELECT COUNT(*) FROM content_posts WHERE platform = 'youtube'
        """))
        youtube_count = result.fetchone()[0]
        
        result = conn.execute(text("""
            SELECT COUNT(*) FROM followers WHERE platform = 'youtube'
        """))
        follower_count = result.fetchone()[0]
        
        result = conn.execute(text("""
            SELECT COUNT(*) FROM follower_interactions WHERE platform = 'youtube'
        """))
        interaction_count = result.fetchone()[0]
        
        result = conn.execute(text("""
            SELECT COUNT(*) FROM follower_interactions 
            WHERE platform = 'youtube' AND interaction_type = 'comment'
        """))
        comment_interaction_count = result.fetchone()[0]
        
        print("\n" + "="*60)
        print("✅ YOUTUBE BACKFILL COMPLETE!")
        print("="*60)
        print(f"\n📊 Database Summary:")
        print(f"   • Content items: {content_count}")
        print(f"   • YouTube videos: {youtube_count}")
        print(f"   • Followers tracked: {follower_count} (REAL USERS!)")
        print(f"   • Interactions recorded: {interaction_count}")
        print(f"   • Comments from users: {comment_interaction_count}")
        
        # Show top commenters
        result = conn.execute(text("""
            SELECT 
                f.username,
                f.display_name,
                COUNT(*) as comment_count,
                AVG(fi.sentiment_score) as avg_sentiment
            FROM followers f
            JOIN follower_interactions fi ON f.id = fi.follower_id
            WHERE f.platform = 'youtube' AND fi.interaction_type = 'comment'
            GROUP BY f.id, f.username, f.display_name
            ORDER BY comment_count DESC
            LIMIT 5
        """))
        
        top_commenters = result.fetchall()
        if top_commenters:
            print(f"\n🏆 Top YouTube Commenters:")
            for commenter in top_commenters:
                sentiment = "😊" if commenter[3] and commenter[3] > 0.3 else "😐" if commenter[3] and commenter[3] > -0.3 else "😠" if commenter[3] else "❓"
                print(f"   • @{commenter[0]}: {commenter[2]} comments {sentiment}")
        
        print(f"\n✅ Ready for analytics dashboard!")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
