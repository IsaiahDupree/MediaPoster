#!/usr/bin/env python3
"""
YouTube Performance Review System

Fetches YouTube stats for posted content and analyzes performance
by content category (UGC vs AI/Sora-style).

Usage:
    python youtube_performance_review.py [--fetch-stats] [--generate-report]
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")

@dataclass
class VideoStats:
    video_id: str
    title: str
    views: int
    likes: int
    comments: int
    shares: int
    watch_time_hours: float
    avg_view_duration_seconds: float
    avg_view_percentage: float
    subscribers_gained: int
    impressions: int
    click_through_rate: float
    fetched_at: datetime

@dataclass
class ContentReview:
    video_id: str
    title: str
    content_category: str  # 'UGC', 'AI/Sora-style', 'Other'
    content_type: str
    published_at: datetime
    platform_url: str
    
    # Performance metrics
    views: int = 0
    likes: int = 0
    comments: int = 0
    engagement_rate: float = 0.0
    
    # Scores
    performance_score: float = 0.0  # 0-100
    
    # Review
    strengths: List[str] = None
    weaknesses: List[str] = None
    improvements: List[str] = None
    overall_verdict: str = ""

class YouTubePerformanceReviewer:
    """Fetches and analyzes YouTube performance data."""
    
    def __init__(self):
        self.api_key = YOUTUBE_API_KEY
        self.db_url = DATABASE_URL
        
    async def get_posted_youtube_content(self) -> List[Dict]:
        """Get all posted YouTube content from database."""
        import asyncpg
        
        conn = await asyncpg.connect(self.db_url)
        try:
            rows = await conn.fetch("""
                SELECT 
                    sp.id,
                    sp.clip_id,
                    sp.title,
                    sp.platform_url,
                    sp.platform_post_id,
                    sp.published_at,
                    sp.caption,
                    va.content_format,
                    va.content_type,
                    va.pre_social_score,
                    va.sentiment_score,
                    va.hooks,
                    va.tone,
                    CASE 
                        WHEN va.content_format IN ('animated', 'broll_scenic', 'broll_action') THEN 'AI/Sora-style'
                        WHEN va.content_format IN ('talking_head', 'interview', 'live_event', 'tutorial_hands') THEN 'UGC'
                        ELSE 'Other'
                    END as content_category
                FROM scheduled_posts sp
                LEFT JOIN video_analysis va ON va.video_id = sp.clip_id
                WHERE sp.platform = 'youtube' 
                  AND sp.status = 'posted' 
                  AND sp.platform_url IS NOT NULL
                ORDER BY sp.published_at DESC
            """)
            return [dict(row) for row in rows]
        finally:
            await conn.close()
    
    async def fetch_youtube_stats(self, video_id: str) -> Optional[Dict]:
        """Fetch stats for a single YouTube video."""
        if not self.api_key:
            print("⚠️ YOUTUBE_API_KEY not set - using mock data")
            return self._mock_stats(video_id)
        
        async with httpx.AsyncClient() as client:
            # Get video statistics
            stats_url = f"https://www.googleapis.com/youtube/v3/videos"
            params = {
                "part": "statistics,contentDetails",
                "id": video_id,
                "key": self.api_key
            }
            
            try:
                response = await client.get(stats_url, params=params)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("items"):
                        item = data["items"][0]
                        stats = item.get("statistics", {})
                        return {
                            "views": int(stats.get("viewCount", 0)),
                            "likes": int(stats.get("likeCount", 0)),
                            "comments": int(stats.get("commentCount", 0)),
                            "favorites": int(stats.get("favoriteCount", 0)),
                        }
                else:
                    print(f"  ⚠️ API error for {video_id}: {response.status_code}")
            except Exception as e:
                print(f"  ❌ Error fetching {video_id}: {e}")
        
        return None
    
    def _mock_stats(self, video_id: str) -> Dict:
        """Generate mock stats for testing without API key."""
        import random
        return {
            "views": random.randint(10, 5000),
            "likes": random.randint(0, 200),
            "comments": random.randint(0, 50),
            "favorites": 0
        }
    
    def calculate_engagement_rate(self, stats: Dict, views: int) -> float:
        """Calculate engagement rate from stats."""
        if views == 0:
            return 0.0
        engagements = stats.get("likes", 0) + stats.get("comments", 0)
        return (engagements / views) * 100
    
    def calculate_performance_score(self, stats: Dict, days_since_post: int) -> float:
        """Calculate overall performance score (0-100)."""
        views = stats.get("views", 0)
        likes = stats.get("likes", 0)
        comments = stats.get("comments", 0)
        
        # Normalize by days since post (expect more for older videos)
        daily_views = views / max(days_since_post, 1)
        
        # Scoring weights
        view_score = min(daily_views / 100 * 40, 40)  # Up to 40 points
        like_score = min(likes / 50 * 30, 30)          # Up to 30 points
        comment_score = min(comments / 10 * 30, 30)    # Up to 30 points
        
        return round(view_score + like_score + comment_score, 1)
    
    def generate_review(self, content: Dict, stats: Dict) -> ContentReview:
        """Generate a performance review for a piece of content."""
        days_since = (datetime.now() - content["published_at"].replace(tzinfo=None)).days if content["published_at"] else 1
        
        views = stats.get("views", 0) if stats else 0
        likes = stats.get("likes", 0) if stats else 0
        comments = stats.get("comments", 0) if stats else 0
        
        engagement_rate = self.calculate_engagement_rate(stats or {}, views)
        performance_score = self.calculate_performance_score(stats or {}, days_since)
        
        # Analyze strengths and weaknesses
        strengths = []
        weaknesses = []
        improvements = []
        
        # View analysis
        daily_views = views / max(days_since, 1)
        if daily_views > 100:
            strengths.append(f"Strong view velocity ({daily_views:.0f}/day)")
        elif daily_views < 10:
            weaknesses.append(f"Low view velocity ({daily_views:.1f}/day)")
            improvements.append("Improve thumbnail and title for better CTR")
        
        # Engagement analysis
        if engagement_rate > 5:
            strengths.append(f"High engagement rate ({engagement_rate:.1f}%)")
        elif engagement_rate < 1:
            weaknesses.append(f"Low engagement ({engagement_rate:.2f}%)")
            improvements.append("Add stronger call-to-action in video")
        
        # Like ratio
        if views > 0:
            like_ratio = (likes / views) * 100
            if like_ratio > 4:
                strengths.append(f"Excellent like ratio ({like_ratio:.1f}%)")
            elif like_ratio < 1:
                weaknesses.append("Low like ratio - content may not resonate")
                improvements.append("Test different content angles or hooks")
        
        # Comments analysis
        if comments > 10:
            strengths.append(f"Good comment activity ({comments} comments)")
        elif comments == 0 and views > 100:
            weaknesses.append("No comments despite views")
            improvements.append("Ask questions to encourage comments")
        
        # Content-specific analysis
        content_category = content.get("content_category", "Other")
        if content_category == "AI/Sora-style":
            if views < 50:
                improvements.append("AI content may need stronger narrative hook")
            if engagement_rate < 2:
                improvements.append("Consider adding voiceover to AI visuals")
        elif content_category == "UGC":
            if engagement_rate < 3:
                improvements.append("UGC should have higher engagement - review authenticity")
        
        # Overall verdict
        if performance_score >= 70:
            verdict = "🌟 HIGH PERFORMER - Replicate this style"
        elif performance_score >= 40:
            verdict = "✅ AVERAGE - Room for improvement"
        else:
            verdict = "⚠️ UNDERPERFORMER - Needs optimization"
        
        return ContentReview(
            video_id=content.get("platform_post_id", ""),
            title=content.get("title", "Untitled"),
            content_category=content_category,
            content_type=content.get("content_type", "unknown"),
            published_at=content.get("published_at"),
            platform_url=content.get("platform_url", ""),
            views=views,
            likes=likes,
            comments=comments,
            engagement_rate=engagement_rate,
            performance_score=performance_score,
            strengths=strengths,
            weaknesses=weaknesses,
            improvements=improvements,
            overall_verdict=verdict
        )
    
    async def generate_category_report(self, reviews: List[ContentReview]) -> Dict:
        """Generate aggregate report by content category."""
        categories = {}
        
        for review in reviews:
            cat = review.content_category
            if cat not in categories:
                categories[cat] = {
                    "count": 0,
                    "total_views": 0,
                    "total_likes": 0,
                    "total_comments": 0,
                    "total_score": 0,
                    "high_performers": [],
                    "low_performers": [],
                    "common_improvements": {}
                }
            
            categories[cat]["count"] += 1
            categories[cat]["total_views"] += review.views
            categories[cat]["total_likes"] += review.likes
            categories[cat]["total_comments"] += review.comments
            categories[cat]["total_score"] += review.performance_score
            
            if review.performance_score >= 70:
                categories[cat]["high_performers"].append(review.title)
            elif review.performance_score < 30:
                categories[cat]["low_performers"].append(review.title)
            
            for imp in (review.improvements or []):
                categories[cat]["common_improvements"][imp] = \
                    categories[cat]["common_improvements"].get(imp, 0) + 1
        
        # Calculate averages
        for cat, data in categories.items():
            if data["count"] > 0:
                data["avg_views"] = round(data["total_views"] / data["count"], 1)
                data["avg_likes"] = round(data["total_likes"] / data["count"], 1)
                data["avg_comments"] = round(data["total_comments"] / data["count"], 1)
                data["avg_score"] = round(data["total_score"] / data["count"], 1)
                
                # Top improvements
                data["top_improvements"] = sorted(
                    data["common_improvements"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
        
        return categories
    
    async def run_full_review(self, fetch_live_stats: bool = False) -> Dict:
        """Run complete performance review."""
        print("=" * 60)
        print("📊 YouTube Performance Review System")
        print("=" * 60)
        
        # Get content from database
        print("\n📥 Fetching posted YouTube content...")
        content_list = await self.get_posted_youtube_content()
        print(f"  Found {len(content_list)} posted YouTube videos")
        
        # Fetch stats if requested
        reviews = []
        print("\n🔍 Analyzing content...")
        
        for i, content in enumerate(content_list):
            video_id = content.get("platform_post_id", "")
            
            # Only fetch for valid YouTube IDs (11 chars)
            stats = None
            if fetch_live_stats and len(video_id) == 11:
                print(f"  [{i+1}/{len(content_list)}] Fetching stats for {video_id}...")
                stats = await self.fetch_youtube_stats(video_id)
                await asyncio.sleep(0.5)  # Rate limiting
            else:
                # Use mock data for testing
                stats = self._mock_stats(video_id)
            
            review = self.generate_review(content, stats)
            reviews.append(review)
        
        # Generate category report
        print("\n📈 Generating category analysis...")
        category_report = await self.generate_category_report(reviews)
        
        # Print summary
        self._print_summary(reviews, category_report)
        
        # Save report
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_videos": len(reviews),
            "categories": {
                cat: {
                    "count": data["count"],
                    "avg_views": data.get("avg_views", 0),
                    "avg_likes": data.get("avg_likes", 0),
                    "avg_score": data.get("avg_score", 0),
                    "high_performers": data["high_performers"][:5],
                    "low_performers": data["low_performers"][:5],
                    "top_improvements": data.get("top_improvements", [])
                }
                for cat, data in category_report.items()
            },
            "reviews": [
                {
                    "video_id": r.video_id,
                    "title": r.title,
                    "category": r.content_category,
                    "views": r.views,
                    "likes": r.likes,
                    "score": r.performance_score,
                    "verdict": r.overall_verdict,
                    "improvements": r.improvements
                }
                for r in reviews
            ]
        }
        
        # Save to file
        output_path = Path(__file__).parent / "youtube_performance_report.json"
        with open(output_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
        print(f"\n📁 Report saved to {output_path}")
        
        return report
    
    def _print_summary(self, reviews: List[ContentReview], category_report: Dict):
        """Print formatted summary."""
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE SUMMARY BY CATEGORY")
        print("=" * 60)
        
        for cat, data in category_report.items():
            print(f"\n{'─' * 50}")
            print(f"📁 {cat} ({data['count']} videos)")
            print(f"{'─' * 50}")
            print(f"  Avg Views:    {data.get('avg_views', 0):,.0f}")
            print(f"  Avg Likes:    {data.get('avg_likes', 0):,.0f}")
            print(f"  Avg Comments: {data.get('avg_comments', 0):,.0f}")
            print(f"  Avg Score:    {data.get('avg_score', 0):.1f}/100")
            
            if data["high_performers"]:
                print(f"\n  🌟 Top Performers:")
                for title in data["high_performers"][:3]:
                    print(f"     • {title[:40]}")
            
            if data["low_performers"]:
                print(f"\n  ⚠️ Needs Improvement:")
                for title in data["low_performers"][:3]:
                    print(f"     • {title[:40]}")
            
            if data.get("top_improvements"):
                print(f"\n  💡 Common Recommendations:")
                for imp, count in data["top_improvements"][:3]:
                    print(f"     • {imp} ({count}x)")
        
        # Overall comparison
        print("\n" + "=" * 60)
        print("📈 CATEGORY COMPARISON")
        print("=" * 60)
        
        sorted_cats = sorted(
            category_report.items(),
            key=lambda x: x[1].get("avg_score", 0),
            reverse=True
        )
        
        for i, (cat, data) in enumerate(sorted_cats, 1):
            score = data.get("avg_score", 0)
            bar_len = int(score / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            print(f"  {i}. {cat:15} [{bar}] {score:.1f}")
        
        # Winner
        if sorted_cats:
            winner = sorted_cats[0]
            print(f"\n🏆 Best Performing Category: {winner[0]}")
            print(f"   Average Score: {winner[1].get('avg_score', 0):.1f}/100")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="YouTube Performance Review")
    parser.add_argument("--fetch-stats", action="store_true", 
                       help="Fetch live stats from YouTube API")
    parser.add_argument("--generate-report", action="store_true",
                       help="Generate performance report")
    args = parser.parse_args()
    
    reviewer = YouTubePerformanceReviewer()
    
    # Default: run full review with mock stats
    fetch_live = args.fetch_stats if args.fetch_stats else False
    await reviewer.run_full_review(fetch_live_stats=fetch_live)


if __name__ == "__main__":
    asyncio.run(main())
