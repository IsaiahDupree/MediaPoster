"""
Influencer Analyzer Service
===========================
AI-powered analysis of influencer accounts for competitive intelligence.
Generates comprehensive reports on strategy, unique factors, funnel, and learnings.
"""
import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from loguru import logger

from openai import OpenAI
from sqlalchemy import create_engine, text


@dataclass
class TopPost:
    """Represents a top-performing post"""
    post_id: str
    url: Optional[str] = None
    caption: Optional[str] = None
    likes: int = 0
    comments: int = 0
    views: int = 0
    shares: int = 0
    engagement_rate: float = 0.0
    posted_at: Optional[str] = None
    content_type: Optional[str] = None
    hook: Optional[str] = None
    topics: List[str] = field(default_factory=list)


@dataclass
class InfluencerProfile:
    """Influencer profile data"""
    platform: str
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    follower_count: int = 0
    following_count: int = 0
    post_count: int = 0
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    avg_views: float = 0.0
    engagement_rate: float = 0.0
    profile_url: Optional[str] = None
    avatar_url: Optional[str] = None
    verified: bool = False
    category: Optional[str] = None


@dataclass
class InfluencerAnalysisReport:
    """Comprehensive influencer analysis report"""
    profile: InfluencerProfile
    
    # Unique factors
    unique_positioning: str = ""
    content_style: str = ""
    brand_voice: str = ""
    visual_aesthetic: str = ""
    
    # Strategy analysis
    content_strategy: str = ""
    posting_frequency: str = ""
    best_posting_times: List[str] = field(default_factory=list)
    content_pillars: List[str] = field(default_factory=list)
    hashtag_strategy: str = ""
    
    # Audience & funnel
    target_audience: str = ""
    who_they_help: str = ""
    how_they_attract: str = ""
    funnel_setup: str = ""
    monetization_model: str = ""
    
    # Top content
    top_posts: List[TopPost] = field(default_factory=list)
    viral_patterns: List[str] = field(default_factory=list)
    hook_patterns: List[str] = field(default_factory=list)
    
    # Learnings & applications
    key_learnings: List[str] = field(default_factory=list)
    actionable_tactics: List[str] = field(default_factory=list)
    content_ideas_inspired: List[str] = field(default_factory=list)
    
    # Metadata
    analyzed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    analysis_version: str = "1.0"
    confidence_score: float = 0.0


class InfluencerAnalyzer:
    """
    Service for analyzing influencer accounts and generating strategic reports.
    """
    
    def __init__(
        self,
        db_url: Optional[str] = None,
        openai_api_key: Optional[str] = None
    ):
        self.db_url = db_url or os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
        self.engine = create_engine(self.db_url)
        
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.openai_api_key) if self.openai_api_key else None
        
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY")
    
    async def fetch_profile_data(
        self,
        platform: str,
        username: str
    ) -> Optional[InfluencerProfile]:
        """
        Fetch influencer profile data from platform via RapidAPI.
        
        Args:
            platform: Platform name (instagram, tiktok, youtube, etc.)
            username: Username without @
        """
        import aiohttp
        
        if not self.rapidapi_key:
            logger.error("RAPIDAPI_KEY not configured")
            return None
        
        # Platform-specific API hosts
        api_configs = {
            "instagram": {
                "host": "instagram-looter2.p.rapidapi.com",
                "endpoint": "/v1/info",
                "params": {"username": username}
            },
            "tiktok": {
                "host": "tiktok-scraper7.p.rapidapi.com",
                "endpoint": "/user/info",
                "params": {"unique_id": username}
            },
            "youtube": {
                "host": "youtube-v31.p.rapidapi.com",
                "endpoint": "/channels",
                "params": {"forUsername": username, "part": "statistics,snippet"}
            }
        }
        
        config = api_configs.get(platform)
        if not config:
            logger.error(f"Unsupported platform: {platform}")
            return None
        
        try:
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": config["host"]
            }
            
            url = f"https://{config['host']}{config['endpoint']}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=config["params"], timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"API error: {response.status}")
                        return None
                    
                    data = await response.json()
                    return self._parse_profile_data(platform, username, data)
                    
        except Exception as e:
            logger.error(f"Failed to fetch profile: {e}")
            return None
    
    def _parse_profile_data(
        self,
        platform: str,
        username: str,
        data: Dict[str, Any]
    ) -> InfluencerProfile:
        """Parse API response into InfluencerProfile"""
        
        if platform == "instagram":
            user = data.get("user", data)
            return InfluencerProfile(
                platform=platform,
                username=username,
                display_name=user.get("full_name"),
                bio=user.get("biography"),
                follower_count=user.get("follower_count", 0),
                following_count=user.get("following_count", 0),
                post_count=user.get("media_count", 0),
                profile_url=f"https://instagram.com/{username}",
                avatar_url=user.get("profile_pic_url"),
                verified=user.get("is_verified", False),
                category=user.get("category")
            )
        
        elif platform == "tiktok":
            user = data.get("user", data.get("userInfo", {}).get("user", {}))
            stats = data.get("stats", data.get("userInfo", {}).get("stats", {}))
            return InfluencerProfile(
                platform=platform,
                username=username,
                display_name=user.get("nickname"),
                bio=user.get("signature"),
                follower_count=stats.get("followerCount", 0),
                following_count=stats.get("followingCount", 0),
                post_count=stats.get("videoCount", 0),
                avg_likes=stats.get("heartCount", 0) / max(stats.get("videoCount", 1), 1),
                profile_url=f"https://tiktok.com/@{username}",
                avatar_url=user.get("avatarLarger"),
                verified=user.get("verified", False)
            )
        
        elif platform == "youtube":
            items = data.get("items", [])
            if not items:
                return InfluencerProfile(platform=platform, username=username)
            
            channel = items[0]
            snippet = channel.get("snippet", {})
            stats = channel.get("statistics", {})
            
            return InfluencerProfile(
                platform=platform,
                username=username,
                display_name=snippet.get("title"),
                bio=snippet.get("description"),
                follower_count=int(stats.get("subscriberCount", 0)),
                post_count=int(stats.get("videoCount", 0)),
                avg_views=int(stats.get("viewCount", 0)) / max(int(stats.get("videoCount", 1)), 1),
                profile_url=f"https://youtube.com/@{username}",
                avatar_url=snippet.get("thumbnails", {}).get("high", {}).get("url")
            )
        
        return InfluencerProfile(platform=platform, username=username)
    
    async def fetch_top_posts(
        self,
        platform: str,
        username: str,
        limit: int = 10
    ) -> List[TopPost]:
        """Fetch top-performing posts from influencer"""
        import aiohttp
        
        if not self.rapidapi_key:
            return []
        
        api_configs = {
            "instagram": {
                "host": "instagram-looter2.p.rapidapi.com",
                "endpoint": "/v1/posts",
                "params": {"username": username}
            },
            "tiktok": {
                "host": "tiktok-scraper7.p.rapidapi.com",
                "endpoint": "/user/posts",
                "params": {"unique_id": username, "count": str(limit * 2)}
            }
        }
        
        config = api_configs.get(platform)
        if not config:
            return []
        
        try:
            headers = {
                "X-RapidAPI-Key": self.rapidapi_key,
                "X-RapidAPI-Host": config["host"]
            }
            
            url = f"https://{config['host']}{config['endpoint']}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=config["params"], timeout=30) as response:
                    if response.status != 200:
                        return []
                    
                    data = await response.json()
                    return self._parse_top_posts(platform, data, limit)
                    
        except Exception as e:
            logger.error(f"Failed to fetch posts: {e}")
            return []
    
    def _parse_top_posts(
        self,
        platform: str,
        data: Any,
        limit: int
    ) -> List[TopPost]:
        """Parse posts and return top performers"""
        posts = []
        
        # Get posts array
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("posts", data.get("data", data.get("videos", [])))
        else:
            return []
        
        for item in items:
            if platform == "instagram":
                post = TopPost(
                    post_id=str(item.get("pk") or item.get("id")),
                    url=f"https://instagram.com/p/{item.get('shortcode', '')}",
                    caption=item.get("caption", {}).get("text") if isinstance(item.get("caption"), dict) else item.get("caption"),
                    likes=item.get("like_count", 0),
                    comments=item.get("comment_count", 0),
                    views=item.get("play_count", item.get("view_count", 0)),
                    content_type="video" if item.get("is_video") else "image"
                )
            elif platform == "tiktok":
                stats = item.get("stats", {})
                post = TopPost(
                    post_id=str(item.get("id")),
                    url=f"https://tiktok.com/@/video/{item.get('id')}",
                    caption=item.get("desc"),
                    likes=stats.get("diggCount", item.get("digg_count", 0)),
                    comments=stats.get("commentCount", item.get("comment_count", 0)),
                    views=stats.get("playCount", item.get("play_count", 0)),
                    shares=stats.get("shareCount", item.get("share_count", 0)),
                    content_type="video"
                )
            else:
                continue
            
            posts.append(post)
        
        # Sort by engagement and return top
        posts.sort(key=lambda p: p.likes + p.comments * 2 + p.views * 0.01, reverse=True)
        return posts[:limit]
    
    async def analyze_influencer(
        self,
        platform: str,
        username: str,
        include_posts: bool = True
    ) -> InfluencerAnalysisReport:
        """
        Generate comprehensive influencer analysis report.
        
        Args:
            platform: Platform name
            username: Username without @
            include_posts: Whether to fetch and analyze top posts
        
        Returns:
            Complete InfluencerAnalysisReport
        """
        logger.info(f"Analyzing influencer: @{username} on {platform}")
        
        # Fetch profile data
        profile = await self.fetch_profile_data(platform, username)
        if not profile:
            profile = InfluencerProfile(platform=platform, username=username)
        
        # Fetch top posts
        top_posts = []
        if include_posts:
            top_posts = await self.fetch_top_posts(platform, username, limit=10)
        
        # Use AI to analyze
        report = await self._generate_ai_analysis(profile, top_posts)
        
        # Save to database
        await self._save_report(report)
        
        return report
    
    async def _generate_ai_analysis(
        self,
        profile: InfluencerProfile,
        top_posts: List[TopPost]
    ) -> InfluencerAnalysisReport:
        """Generate AI-powered analysis of influencer"""
        
        if not self.client:
            logger.warning("OpenAI not configured - returning basic report")
            return InfluencerAnalysisReport(profile=profile, top_posts=top_posts)
        
        # Build analysis prompt
        posts_context = ""
        if top_posts:
            posts_context = "\n\nTOP PERFORMING POSTS:\n"
            for i, post in enumerate(top_posts[:5], 1):
                posts_context += f"""
{i}. Likes: {post.likes:,} | Comments: {post.comments:,} | Views: {post.views:,}
   Caption: {(post.caption or '')[:200]}...
"""
        
        prompt = f"""Analyze this influencer account and provide a comprehensive strategic analysis.

PROFILE:
- Platform: {profile.platform}
- Username: @{profile.username}
- Display Name: {profile.display_name}
- Bio: {profile.bio}
- Followers: {profile.follower_count:,}
- Following: {profile.following_count:,}
- Posts: {profile.post_count:,}
- Category: {profile.category}
{posts_context}

Provide analysis in this JSON format:
{{
    "unique_positioning": "What makes them stand out from others in their niche",
    "content_style": "Their content creation approach and format preferences",
    "brand_voice": "Tone, language style, personality",
    "visual_aesthetic": "Visual style, colors, editing approach",
    
    "content_strategy": "Overall content strategy summary",
    "content_pillars": ["pillar1", "pillar2", "pillar3"],
    "posting_frequency": "How often they post",
    "best_posting_times": ["time1", "time2"],
    "hashtag_strategy": "How they use hashtags",
    
    "target_audience": "Who their content is for",
    "who_they_help": "The specific people/problems they address",
    "how_they_attract": "Methods used to attract followers",
    "funnel_setup": "How they move followers to customers/deeper engagement",
    "monetization_model": "How they likely make money",
    
    "viral_patterns": ["pattern1", "pattern2"],
    "hook_patterns": ["hook style 1", "hook style 2"],
    
    "key_learnings": ["learning1", "learning2", "learning3"],
    "actionable_tactics": ["tactic1", "tactic2", "tactic3"],
    "content_ideas_inspired": ["idea1", "idea2", "idea3"],
    
    "confidence_score": 0.85
}}

Be specific, actionable, and insightful. Base analysis on the data provided."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert social media strategist and competitive analyst. Provide detailed, actionable insights about influencer strategies."
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            return InfluencerAnalysisReport(
                profile=profile,
                unique_positioning=analysis.get("unique_positioning", ""),
                content_style=analysis.get("content_style", ""),
                brand_voice=analysis.get("brand_voice", ""),
                visual_aesthetic=analysis.get("visual_aesthetic", ""),
                content_strategy=analysis.get("content_strategy", ""),
                posting_frequency=analysis.get("posting_frequency", ""),
                best_posting_times=analysis.get("best_posting_times", []),
                content_pillars=analysis.get("content_pillars", []),
                hashtag_strategy=analysis.get("hashtag_strategy", ""),
                target_audience=analysis.get("target_audience", ""),
                who_they_help=analysis.get("who_they_help", ""),
                how_they_attract=analysis.get("how_they_attract", ""),
                funnel_setup=analysis.get("funnel_setup", ""),
                monetization_model=analysis.get("monetization_model", ""),
                top_posts=top_posts,
                viral_patterns=analysis.get("viral_patterns", []),
                hook_patterns=analysis.get("hook_patterns", []),
                key_learnings=analysis.get("key_learnings", []),
                actionable_tactics=analysis.get("actionable_tactics", []),
                content_ideas_inspired=analysis.get("content_ideas_inspired", []),
                confidence_score=analysis.get("confidence_score", 0.0)
            )
            
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            return InfluencerAnalysisReport(profile=profile, top_posts=top_posts)
    
    async def _save_report(self, report: InfluencerAnalysisReport):
        """Save analysis report to database"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO influencer_analysis_reports (
                        platform, username, display_name, follower_count,
                        unique_positioning, content_strategy, target_audience,
                        key_learnings, actionable_tactics, report_data, analyzed_at
                    ) VALUES (
                        :platform, :username, :display_name, :follower_count,
                        :unique_positioning, :content_strategy, :target_audience,
                        :key_learnings, :actionable_tactics, :report_data, :analyzed_at
                    )
                    ON CONFLICT (platform, username) DO UPDATE SET
                        follower_count = :follower_count,
                        unique_positioning = :unique_positioning,
                        content_strategy = :content_strategy,
                        report_data = :report_data,
                        analyzed_at = :analyzed_at
                """), {
                    "platform": report.profile.platform,
                    "username": report.profile.username,
                    "display_name": report.profile.display_name,
                    "follower_count": report.profile.follower_count,
                    "unique_positioning": report.unique_positioning,
                    "content_strategy": report.content_strategy,
                    "target_audience": report.target_audience,
                    "key_learnings": report.key_learnings,
                    "actionable_tactics": report.actionable_tactics,
                    "report_data": json.dumps(asdict(report)),
                    "analyzed_at": report.analyzed_at
                })
                conn.commit()
                logger.info(f"Saved report for @{report.profile.username}")
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
