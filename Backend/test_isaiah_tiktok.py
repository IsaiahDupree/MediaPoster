"""
Test fetching analytics for @isaiah_dupree on TikTok
"""
import asyncio
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables FIRST before importing scrapers
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

# Now import scrapers after env is loaded
from services.scrapers import get_tiktok_analytics, get_tiktok_profile, get_factory, Platform


async def test_isaiah_dupree_analytics():
    """Fetch complete analytics for @isaiah_dupree"""
    username = "isaiah_dupree"
    
    print("\n" + "="*80)
    print(f"📊 FETCHING ANALYTICS FOR @{username}")
    print("="*80 + "\n")
    
    # Verify API key
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        print("❌ RAPIDAPI_KEY not found! Please check your .env file")
        return
    print(f"✅ Using API Key: {api_key[:20]}...{api_key[-10:]}\n")
    
    # Step 1: Get Profile
    print("Step 1: Fetching profile data...")
    profile = await get_tiktok_profile(username)
    
    if not profile:
        print(f"❌ Failed to fetch profile for @{username}")
        return
    
    print(f"\n✅ Profile fetched successfully!")
    print(f"   Username: @{profile.username}")
    print(f"   Full Name: {profile.full_name}")
    print(f"   Bio: {profile.bio[:100]}..." if len(profile.bio) > 100 else f"   Bio: {profile.bio}")
    print(f"   Followers: {profile.followers_count:,}")
    print(f"   Following: {profile.following_count:,}")
    print(f"   Total Videos: {profile.posts_count:,}")
    print(f"   Verified: {'✅' if profile.is_verified else '❌'}")
    print(f"   Business: {'✅' if profile.is_business else '❌'}")
    
    # Step 2: Get Complete Analytics
    print(f"\n\nStep 2: Fetching analytics (last 50 posts)...")
    analytics = await get_tiktok_analytics(username, posts_limit=50)
    
    if not analytics:
        print(f"❌ Failed to fetch analytics for @{username}")
        return
    
    print(f"\n✅ Analytics fetched successfully!")
    print(f"\n{'='*80}")
    print("📈 ANALYTICS SUMMARY")
    print("="*80)
    
    print(f"\n🎬 Content Metrics:")
    print(f"   Total Posts Analyzed: {len(analytics.posts)}")
    print(f"   Total Likes: {analytics.total_likes:,}")
    print(f"   Total Comments: {analytics.total_comments:,}")
    print(f"   Total Views: {analytics.total_views:,}")
    print(f"   Total Shares: {analytics.total_shares:,}")
    
    print(f"\n📊 Engagement Metrics:")
    print(f"   Engagement Rate: {analytics.engagement_rate}%")
    print(f"   Avg Likes per Post: {analytics.avg_likes_per_post:,.1f}")
    print(f"   Avg Comments per Post: {analytics.avg_comments_per_post:,.1f}")
    
    # Step 3: Show Top Performing Content
    if analytics.best_performing_post:
        print(f"\n🏆 Best Performing Post:")
        best = analytics.best_performing_post
        print(f"   Post ID: {best.post_id}")
        print(f"   URL: {best.url}")
        print(f"   Caption: {best.caption[:100]}..." if len(best.caption) > 100 else f"   Caption: {best.caption}")
        print(f"   Likes: {best.likes_count:,}")
        print(f"   Comments: {best.comments_count:,}")
        print(f"   Views: {best.views_count:,}")
        print(f"   Shares: {best.shares_count:,}")
        print(f"   Posted: {best.posted_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 4: Show Top Hashtags
    if analytics.top_hashtags:
        print(f"\n#️⃣ Top Hashtags:")
        for i, hashtag in enumerate(analytics.top_hashtags[:10], 1):
            print(f"   {i}. {hashtag}")
    
    # Step 5: Show Recent Posts
    print(f"\n📹 Recent Posts (Last 10):")
    print("-" * 80)
    for i, post in enumerate(analytics.posts[:10], 1):
        print(f"\n{i}. {post.caption[:80]}..." if len(post.caption) > 80 else f"\n{i}. {post.caption}")
        print(f"   👁️  {post.views_count:,} views | ❤️  {post.likes_count:,} likes | 💬 {post.comments_count:,} comments")
        print(f"   🔗 {post.url}")
    
    # Save to JSON
    output_file = Path(__file__).parent / "isaiah_dupree_analytics.json"
    analytics_data = {
        "username": profile.username,
        "profile": {
            "full_name": profile.full_name,
            "bio": profile.bio,
            "followers": profile.followers_count,
            "following": profile.following_count,
            "posts_count": profile.posts_count,
            "verified": profile.is_verified,
            "business": profile.is_business
        },
        "analytics": {
            "posts_analyzed": len(analytics.posts),
            "total_likes": analytics.total_likes,
            "total_comments": analytics.total_comments,
            "total_views": analytics.total_views,
            "total_shares": analytics.total_shares,
            "engagement_rate": analytics.engagement_rate,
            "avg_likes_per_post": analytics.avg_likes_per_post,
            "avg_comments_per_post": analytics.avg_comments_per_post
        },
        "best_post": {
            "url": analytics.best_performing_post.url,
            "caption": analytics.best_performing_post.caption,
            "likes": analytics.best_performing_post.likes_count,
            "comments": analytics.best_performing_post.comments_count,
            "views": analytics.best_performing_post.views_count,
            "shares": analytics.best_performing_post.shares_count
        } if analytics.best_performing_post else None,
        "top_hashtags": analytics.top_hashtags,
        "recent_posts": [
            {
                "url": post.url,
                "caption": post.caption,
                "likes": post.likes_count,
                "comments": post.comments_count,
                "views": post.views_count,
                "shares": post.shares_count,
                "posted_at": post.posted_at.isoformat()
            }
            for post in analytics.posts[:20]
        ]
    }
    
    with open(output_file, 'w') as f:
        json.dump(analytics_data, f, indent=2)
    
    print(f"\n\n💾 Analytics saved to: {output_file}")
    print("\n" + "="*80)
    print("✅ ANALYTICS COMPLETE!")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(test_isaiah_dupree_analytics())
