"""
TikTok Repurpose Service
=========================
Fetches TikTok videos via RapidAPI, downloads them, analyzes, and schedules cross-posts.

Pipeline:
1. Fetch video list from TikTok profile
2. Download videos locally
3. Associate as posted content with stats
4. Analyze videos (transcription, topics)
5. Schedule cross-posts to other platforms
"""
import os
import json
import asyncio
import httpx
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict
from loguru import logger
from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")


@dataclass
class TikTokVideo:
    """TikTok video metadata"""
    video_id: str
    username: str
    url: str
    caption: str
    
    # Metrics
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    
    # Media
    video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    duration: int = 0
    
    # Timestamps
    created_at: Optional[datetime] = None
    fetched_at: datetime = field(default_factory=datetime.utcnow)
    
    # Local storage
    local_path: Optional[str] = None
    downloaded: bool = False
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d['created_at'] = self.created_at.isoformat() if self.created_at else None
        d['fetched_at'] = self.fetched_at.isoformat()
        return d


@dataclass
class RepurposeResult:
    """Result from repurpose pipeline"""
    success: bool
    videos_fetched: int = 0
    videos_downloaded: int = 0
    videos_analyzed: int = 0
    crosspost_scheduled: int = 0
    errors: List[str] = field(default_factory=list)
    videos: List[Dict] = field(default_factory=list)


class TikTokRepurposeService:
    """
    Service for repurposing TikTok content to other platforms.
    
    Usage:
        service = TikTokRepurposeService()
        result = await service.run_full_pipeline(
            username="isaiahdupree",
            count=12,
            platforms=["instagram", "youtube", "threads", "twitter"],
            account_ids={"instagram": 807, "youtube": 228, "threads": 243, "twitter": 571}
        )
    """
    
    # Platform account mappings for @isaiahdupree
    DEFAULT_ACCOUNTS = {
        "instagram": 807,   # @the_isaiah_dupree
        "youtube": 228,     # Isaiah Dupree
        "threads": 243,     # @the_isaiah_dupree
        "twitter": 571,     # @IsaiahDupree7
    }
    
    def __init__(self):
        self.rapidapi_key = RAPIDAPI_KEY
        self.engine = create_engine(DATABASE_URL)
        
        # Storage paths
        self.base_storage = Path("/Volumes/My Passport/MediaPoster/workspace1/tiktok_repurpose")
        if not self.base_storage.exists():
            self.base_storage = Path("data/tiktok_repurpose")
        self.base_storage.mkdir(parents=True, exist_ok=True)
        
        # RapidAPI hosts (tiktok-scraper7 is the working one)
        self.tiktok_host = "tiktok-scraper7.p.rapidapi.com"
    
    def _get_headers(self, host: str) -> Dict[str, str]:
        """Get RapidAPI headers"""
        return {
            "X-RapidAPI-Key": self.rapidapi_key,
            "X-RapidAPI-Host": host
        }
    
    async def fetch_tiktok_videos(
        self,
        username: str,
        count: int = 12
    ) -> List[TikTokVideo]:
        """
        Fetch latest videos from a TikTok profile via RapidAPI.
        
        Args:
            username: TikTok username (without @)
            count: Number of videos to fetch
        
        Returns:
            List of TikTokVideo objects
        """
        if not self.rapidapi_key:
            logger.error("RAPIDAPI_KEY not configured")
            return []
        
        logger.info(f"📥 Fetching {count} videos from @{username}")
        
        videos = []
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Use /user/posts with unique_id parameter (tiktok-scraper7)
                response = await client.get(
                    f"https://{self.tiktok_host}/user/posts",
                    headers=self._get_headers(self.tiktok_host),
                    params={
                        "unique_id": username,
                        "count": count
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"TikTok API error: {response.status_code} - {response.text}")
                    return []
                
                data = response.json()
                
                logger.debug(f"TikTok API response: {data.get('code')}, msg: {data.get('msg')}")
                
                # Parse response - tiktok-scraper7 structure: data.videos
                if data.get('code') != 0:
                    logger.error(f"TikTok API error: {data.get('msg')}")
                    return []
                
                video_list = data.get('data', {}).get('videos', [])
                
                for item in video_list[:count]:
                    video = self._parse_tiktok_video(item, username)
                    if video:
                        videos.append(video)
                
                logger.success(f"✅ Fetched {len(videos)} videos from @{username}")
                
        except Exception as e:
            logger.error(f"Error fetching TikTok videos: {e}")
        
        return videos
    
    def _parse_tiktok_video(self, item: Dict, username: str) -> Optional[TikTokVideo]:
        """Parse TikTok API response into TikTokVideo object (tiktok-scraper7 format)"""
        try:
            # tiktok-scraper7 uses video_id or aweme_id
            video_id = str(item.get('video_id', item.get('aweme_id', item.get('id', ''))))
            
            if not video_id:
                return None
            
            # tiktok-scraper7 has stats at top level: play_count, digg_count, etc.
            views = item.get('play_count', item.get('playCount', 0))
            likes = item.get('digg_count', item.get('diggCount', 0))
            comments = item.get('comment_count', item.get('commentCount', 0))
            shares = item.get('share_count', item.get('shareCount', 0))
            saves = item.get('collect_count', item.get('collectCount', 0))
            
            # Video URL - tiktok-scraper7 uses 'play' field directly
            video_url = item.get('play', item.get('wmplay', ''))
            
            # Thumbnail
            thumbnail = item.get('cover', item.get('origin_cover', ''))
            
            # Duration is at top level
            duration = item.get('duration', 0)
            
            # Caption/title
            caption = item.get('title', item.get('desc', ''))
            
            # Created time - tiktok-scraper7 uses create_time as unix timestamp
            create_time = item.get('create_time', item.get('createTime'))
            created_at = None
            if create_time:
                if isinstance(create_time, (int, float)):
                    created_at = datetime.fromtimestamp(create_time)
            
            # Get author username if different
            author = item.get('author', {})
            actual_username = author.get('unique_id', username)
            
            return TikTokVideo(
                video_id=video_id,
                username=actual_username,
                url=f"https://www.tiktok.com/@{actual_username}/video/{video_id}",
                caption=caption,
                views=views,
                likes=likes,
                comments=comments,
                shares=shares,
                saves=saves,
                video_url=video_url,
                thumbnail_url=thumbnail,
                duration=duration,
                created_at=created_at,
            )
            
        except Exception as e:
            logger.error(f"Error parsing TikTok video: {e}")
            return None
    
    async def download_videos(
        self,
        videos: List[TikTokVideo]
    ) -> List[TikTokVideo]:
        """
        Download TikTok videos to local storage.
        
        Args:
            videos: List of TikTokVideo objects with video_url
        
        Returns:
            Updated list with local_path set
        """
        logger.info(f"📥 Downloading {len(videos)} videos...")
        
        downloaded = []
        
        async with httpx.AsyncClient(timeout=120, follow_redirects=True) as client:
            for video in videos:
                if not video.video_url:
                    logger.warning(f"No download URL for video {video.video_id}")
                    continue
                
                try:
                    # Download video
                    local_path = self.base_storage / f"{video.video_id}_{video.username}.mp4"
                    
                    # Skip if already downloaded
                    if local_path.exists():
                        logger.info(f"⏭️ Already downloaded: {local_path.name}")
                        video.local_path = str(local_path)
                        video.downloaded = True
                        downloaded.append(video)
                        continue
                    
                    logger.info(f"⬇️ Downloading {video.video_id}...")
                    
                    response = await client.get(video.video_url)
                    
                    if response.status_code == 200:
                        with open(local_path, 'wb') as f:
                            f.write(response.content)
                        
                        video.local_path = str(local_path)
                        video.downloaded = True
                        downloaded.append(video)
                        
                        size_mb = len(response.content) / (1024 * 1024)
                        logger.success(f"✅ Downloaded: {local_path.name} ({size_mb:.1f} MB)")
                    else:
                        logger.error(f"Download failed: {response.status_code}")
                        
                except Exception as e:
                    logger.error(f"Error downloading {video.video_id}: {e}")
        
        logger.success(f"✅ Downloaded {len(downloaded)}/{len(videos)} videos")
        return downloaded
    
    async def save_as_posted_content(
        self,
        videos: List[TikTokVideo],
        account_id: int = 710  # Default: isaiah_dupree TikTok
    ) -> int:
        """
        Save videos as posted content in database.
        
        Args:
            videos: List of TikTokVideo objects
            account_id: Blotato account ID (710 = isaiah_dupree TikTok)
        
        Returns:
            Number of records created
        """
        logger.info(f"💾 Saving {len(videos)} videos as posted content...")
        
        created = 0
        
        with self.engine.connect() as conn:
            for video in videos:
                try:
                    # Check if already exists
                    existing = conn.execute(text("""
                        SELECT id FROM posted_content 
                        WHERE platform = 'tiktok' AND platform_post_id = :post_id
                    """), {"post_id": video.video_id}).fetchone()
                    
                    if existing:
                        logger.info(f"⏭️ Already exists: {video.video_id}")
                        continue
                    
                    # Insert posted content
                    conn.execute(text("""
                        INSERT INTO posted_content (
                            platform, platform_post_id, platform_url,
                            account_id, account_username, caption,
                            status, posted_at, created_at,
                            views, likes, comments, shares
                        ) VALUES (
                            'tiktok', :post_id, :url,
                            :account_id, :username, :caption,
                            'published', :posted_at, NOW(),
                            :views, :likes, :comments, :shares
                        )
                    """), {
                        "post_id": video.video_id,
                        "url": video.url,
                        "account_id": account_id,
                        "username": video.username,
                        "caption": video.caption,
                        "posted_at": video.created_at or datetime.utcnow(),
                        "views": video.views,
                        "likes": video.likes,
                        "comments": video.comments,
                        "shares": video.shares,
                    })
                    
                    created += 1
                    logger.success(f"✅ Saved: {video.video_id}")
                    
                except Exception as e:
                    logger.error(f"Error saving {video.video_id}: {e}")
            
            conn.commit()
        
        logger.success(f"✅ Created {created} posted content records")
        return created
    
    async def generate_thumbnails(
        self,
        videos: List[TikTokVideo]
    ) -> int:
        """
        Generate thumbnails for downloaded videos using FFmpeg.
        
        Args:
            videos: List of TikTokVideo objects with local_path
        
        Returns:
            Number of thumbnails generated
        """
        import subprocess
        
        logger.info(f"🖼️ Generating thumbnails for {len(videos)} videos...")
        
        generated = 0
        thumbnail_dir = self.base_storage / "thumbnails"
        thumbnail_dir.mkdir(parents=True, exist_ok=True)
        
        for video in videos:
            if not video.local_path or not Path(video.local_path).exists():
                continue
            
            try:
                # Generate thumbnail at 1 second mark (or 25% into video)
                thumbnail_path = thumbnail_dir / f"{video.video_id}_thumb.jpg"
                
                # Skip if already exists
                if thumbnail_path.exists():
                    logger.info(f"⏭️ Thumbnail exists: {video.video_id}")
                    generated += 1
                    continue
                
                # Use FFmpeg to extract frame
                # Extract at 1 second or 25% of video duration
                seek_time = min(1.0, video.duration * 0.25) if video.duration > 0 else 1.0
                
                result = subprocess.run([
                    "ffmpeg", "-y",
                    "-ss", str(seek_time),
                    "-i", video.local_path,
                    "-vframes", "1",
                    "-q:v", "2",  # High quality JPEG
                    "-vf", "scale=720:-1",  # Scale to 720px width
                    str(thumbnail_path)
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0 and thumbnail_path.exists():
                    generated += 1
                    logger.success(f"✅ Generated thumbnail: {video.video_id}")
                else:
                    logger.error(f"FFmpeg error for {video.video_id}: {result.stderr[:200]}")
                    
            except subprocess.TimeoutExpired:
                logger.error(f"Thumbnail generation timed out: {video.video_id}")
            except Exception as e:
                logger.error(f"Error generating thumbnail for {video.video_id}: {e}")
        
        logger.success(f"✅ Generated {generated}/{len(videos)} thumbnails")
        return generated
    
    async def associate_thumbnails_with_media(self) -> int:
        """
        Associate generated thumbnails with existing videos in the media library.
        Updates thumbnail_path for videos that match TikTok video IDs.
        
        Returns:
            Number of records updated
        """
        logger.info("🔗 Associating thumbnails with media library entries...")
        
        # Get all thumbnail files
        thumb_dir = self.base_storage / "thumbnails"
        if not thumb_dir.exists():
            logger.warning("No thumbnails directory found")
            return 0
        
        updated = 0
        
        with self.engine.connect() as conn:
            for thumb_file in thumb_dir.glob("*_thumb.jpg"):
                # Extract video ID from filename (e.g., "7589407652501916983_thumb.jpg")
                video_id = thumb_file.stem.replace("_thumb", "")
                thumb_path = str(thumb_file)
                
                try:
                    # Update videos table where filename or source_uri contains the video ID
                    result = conn.execute(text("""
                        UPDATE videos 
                        SET thumbnail_path = :thumb_path
                        WHERE (file_name LIKE :pattern OR source_uri LIKE :pattern)
                          AND (thumbnail_path IS NULL OR thumbnail_path = '')
                    """), {
                        "thumb_path": thumb_path,
                        "pattern": f"%{video_id}%"
                    })
                    
                    if result.rowcount > 0:
                        updated += result.rowcount
                        logger.info(f"✅ Linked thumbnail for video {video_id}")
                    
                    # Also update posted_content table
                    conn.execute(text("""
                        UPDATE posted_content 
                        SET thumbnail_url = :thumb_path
                        WHERE (title LIKE :pattern OR platform_post_id LIKE :pattern)
                          AND (thumbnail_url IS NULL OR thumbnail_url = '')
                    """), {
                        "thumb_path": thumb_path,
                        "pattern": f"%{video_id}%"
                    })
                    
                    # Update scheduled_posts table
                    conn.execute(text("""
                        UPDATE scheduled_posts 
                        SET thumbnail_url = :thumb_path
                        WHERE (title LIKE :pattern OR media_url LIKE :pattern)
                          AND (thumbnail_url IS NULL OR thumbnail_url = '')
                    """), {
                        "thumb_path": thumb_path,
                        "pattern": f"%{video_id}%"
                    })
                    
                except Exception as e:
                    logger.error(f"Error associating thumbnail {video_id}: {e}")
            
            conn.commit()
        
        logger.success(f"✅ Associated {updated} thumbnails with media library")
        return updated
    
    async def save_to_media_library(
        self,
        videos: List[TikTokVideo]
    ) -> int:
        """
        Save downloaded videos to media library.
        
        Args:
            videos: List of TikTokVideo objects with local_path
        
        Returns:
            Number of records created
        """
        logger.info(f"📚 Saving {len(videos)} videos to media library...")
        
        created = 0
        
        with self.engine.connect() as conn:
            for video in videos:
                if not video.local_path or not video.downloaded:
                    continue
                
                try:
                    # Check if already in library
                    existing = conn.execute(text("""
                        SELECT id FROM videos 
                        WHERE source_uri = :uri OR file_name LIKE :pattern
                    """), {
                        "uri": video.local_path,
                        "pattern": f"%{video.video_id}%"
                    }).fetchone()
                    
                    if existing:
                        logger.info(f"⏭️ Already in library: {video.video_id}")
                        continue
                    
                    # Get file size
                    file_size = Path(video.local_path).stat().st_size if Path(video.local_path).exists() else 0
                    
                    # Generate thumbnail path
                    thumb_path = str(self.base_storage / "thumbnails" / f"{video.video_id}_thumb.jpg")
                    if not Path(thumb_path).exists():
                        thumb_path = None
                    
                    # Insert into videos table
                    conn.execute(text("""
                        INSERT INTO videos (
                            id, user_id, source_type, source_uri, file_name,
                            title, file_size, duration_sec, thumbnail_path, created_at
                        ) VALUES (
                            gen_random_uuid(),
                            '00000000-0000-0000-0000-000000000000'::uuid,
                            'tiktok_repurpose',
                            :source_uri,
                            :file_name,
                            :title,
                            :file_size,
                            :duration,
                            :thumbnail_path,
                            NOW()
                        )
                    """), {
                        "source_uri": video.local_path,
                        "file_name": Path(video.local_path).name,
                        "title": video.caption[:150] if video.caption else f"TikTok {video.video_id}",
                        "file_size": file_size,
                        "duration": video.duration,
                        "thumbnail_path": thumb_path,
                    })
                    
                    created += 1
                    
                except Exception as e:
                    logger.error(f"Error saving to library {video.video_id}: {e}")
            
            conn.commit()
        
        logger.success(f"✅ Added {created} videos to media library")
        return created
    
    async def analyze_videos(
        self,
        videos: List[TikTokVideo]
    ) -> List[Dict[str, Any]]:
        """
        Analyze downloaded videos and generate AI captions/titles.
        
        Args:
            videos: List of TikTokVideo objects with local_path
        
        Returns:
            List of analysis results with AI-generated content
        """
        logger.info(f"🔍 Analyzing {len(videos)} videos with AI...")
        
        results = []
        
        for video in videos:
            if not video.local_path or not Path(video.local_path).exists():
                logger.error(f"Video file not found: {video.local_path}")
                continue
            
            try:
                # Generate AI caption and title
                ai_content = await self._generate_ai_content(video)
                
                result = {
                    "video_id": video.video_id,
                    "original_caption": video.caption,
                    "ai_title": ai_content.get("title", ""),
                    "ai_caption": ai_content.get("caption", ""),
                    "hashtags": ai_content.get("hashtags", []),
                    "topics": ai_content.get("topics", []),
                    "local_path": video.local_path,
                }
                results.append(result)
                logger.success(f"✅ Analyzed: {video.video_id}")
                
            except Exception as e:
                logger.error(f"Error analyzing {video.video_id}: {e}")
        
        logger.success(f"✅ Analyzed {len(results)}/{len(videos)} videos")
        return results
    
    async def _generate_ai_content(self, video: TikTokVideo) -> Dict[str, Any]:
        """
        Generate AI caption and title for a video using OpenAI.
        
        Args:
            video: TikTokVideo with metadata
        
        Returns:
            Dict with title, caption, hashtags, topics
        """
        import openai
        
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            logger.warning("OPENAI_API_KEY not set, using original caption")
            return {
                "title": video.caption[:100] if video.caption else f"Video {video.video_id}",
                "caption": video.caption,
                "hashtags": [],
                "topics": []
            }
        
        client = openai.OpenAI(api_key=openai_key)
        
        # Build context from video metadata
        context = f"""
Original TikTok Video:
- Views: {video.views:,}
- Likes: {video.likes:,}
- Comments: {video.comments}
- Shares: {video.shares}
- Duration: {video.duration} seconds
- Original Caption: {video.caption or '(no caption)'}
"""
        
        prompt = f"""You are a viral social media content expert. Based on this TikTok video's performance data, create optimized content for cross-posting to Instagram, YouTube, Threads, and Twitter.

{context}

Generate:
1. A catchy, engaging TITLE (max 60 chars) that hooks viewers
2. A platform-optimized CAPTION (150-200 chars) that drives engagement
3. 5-8 relevant HASHTAGS (without #)
4. 3-5 content TOPICS/themes

Output as JSON:
{{
  "title": "...",
  "caption": "...",
  "hashtags": ["tag1", "tag2", ...],
  "topics": ["topic1", "topic2", ...]
}}

Make it authentic, relatable, and optimized for virality. NO emojis in title.
Output ONLY valid JSON."""

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a viral content strategist. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.8
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            
            import json
            data = json.loads(content)
            
            return {
                "title": data.get("title", video.caption[:100] if video.caption else ""),
                "caption": data.get("caption", video.caption),
                "hashtags": data.get("hashtags", []),
                "topics": data.get("topics", [])
            }
            
        except Exception as e:
            logger.error(f"AI content generation failed: {e}")
            return {
                "title": video.caption[:100] if video.caption else f"Video {video.video_id}",
                "caption": video.caption,
                "hashtags": [],
                "topics": []
            }
    
    async def schedule_crossposts(
        self,
        videos: List[TikTokVideo],
        platforms: List[str],
        account_ids: Optional[Dict[str, int]] = None,
        start_time: Optional[datetime] = None,
        interval_hours: float = 1.0,
        ai_content: Optional[List[Dict]] = None
    ) -> int:
        """
        Schedule cross-posts to other platforms.
        
        Args:
            videos: List of TikTokVideo objects
            platforms: List of platforms to post to
            account_ids: Map of platform to Blotato account ID
            start_time: When to start posting (default: now + 1 hour)
            interval_hours: Hours between posts
            ai_content: Optional AI-generated content per video
        
        Returns:
            Number of posts scheduled
        """
        logger.info(f"📅 Scheduling cross-posts to {platforms}...")
        
        account_ids = account_ids or self.DEFAULT_ACCOUNTS
        start_time = start_time or (datetime.utcnow() + timedelta(hours=1))
        
        # Build AI content lookup
        ai_lookup = {}
        if ai_content:
            for item in ai_content:
                ai_lookup[item["video_id"]] = item
        
        scheduled = 0
        current_time = start_time
        
        with self.engine.connect() as conn:
            for video in videos:
                if not video.local_path or not video.downloaded:
                    continue
                
                # Get AI content for this video
                ai_data = ai_lookup.get(video.video_id, {})
                ai_title = ai_data.get("ai_title", "")
                ai_caption = ai_data.get("ai_caption", "")
                hashtags = ai_data.get("hashtags", [])
                
                # Build final caption with hashtags
                if ai_caption:
                    hashtag_str = " ".join(f"#{tag}" for tag in hashtags[:5])
                    final_caption = f"{ai_caption}\n\n{hashtag_str}".strip()
                    final_title = ai_title or video.caption[:60] if video.caption else f"Video"
                else:
                    final_caption = video.caption or ""
                    final_title = video.caption[:60] if video.caption else f"Video {video.video_id}"
                
                for platform in platforms:
                    account_id = account_ids.get(platform)
                    if not account_id:
                        logger.warning(f"No account ID for {platform}")
                        continue
                    
                    try:
                        # Check if already scheduled
                        existing = conn.execute(text("""
                            SELECT id FROM scheduled_posts 
                            WHERE platform = :platform 
                            AND (caption LIKE :pattern OR title LIKE :pattern2)
                            AND status IN ('scheduled', 'publishing')
                        """), {
                            "platform": platform,
                            "pattern": f"%{video.video_id}%",
                            "pattern2": f"%{final_title[:30]}%"
                        }).fetchone()
                        
                        if existing:
                            logger.info(f"⏭️ Already scheduled: {video.video_id} -> {platform}")
                            continue
                        
                        # Create scheduled post with AI content
                        conn.execute(text("""
                            INSERT INTO scheduled_posts (
                                platform, account_id, account_username,
                                blotato_account_id, caption, title,
                                scheduled_time, scheduled_at,
                                post_type, media_type, status,
                                created_at
                            ) VALUES (
                                :platform, :account_id, :username,
                                :blotato_id, :caption, :title,
                                :scheduled_time, :scheduled_time,
                                'video', 'video', 'scheduled',
                                NOW()
                            )
                        """), {
                            "platform": platform,
                            "account_id": account_id,
                            "username": video.username,
                            "blotato_id": account_id,
                            "caption": final_caption,
                            "title": final_title,
                            "scheduled_time": current_time,
                        })
                        
                        scheduled += 1
                        logger.success(f"✅ Scheduled: {video.video_id} -> {platform} @ {current_time}")
                        logger.info(f"   📝 Title: {final_title}")
                        
                        # Increment time for next post
                        current_time += timedelta(hours=interval_hours)
                        
                    except Exception as e:
                        logger.error(f"Error scheduling {video.video_id} to {platform}: {e}")
            
            conn.commit()
        
        logger.success(f"✅ Scheduled {scheduled} cross-posts")
        return scheduled
    
    async def run_full_pipeline(
        self,
        username: str = "isaiahdupree",
        count: int = 12,
        platforms: Optional[List[str]] = None,
        account_ids: Optional[Dict[str, int]] = None,
        download: bool = True,
        analyze: bool = True,
        schedule_crosspost: bool = True
    ) -> RepurposeResult:
        """
        Run the complete TikTok repurpose pipeline.
        
        Args:
            username: TikTok username
            count: Number of videos to fetch
            platforms: Platforms to cross-post to
            account_ids: Account IDs for each platform
            download: Whether to download videos
            analyze: Whether to analyze videos
            schedule_crosspost: Whether to schedule cross-posts
        
        Returns:
            RepurposeResult with pipeline stats
        """
        logger.info(f"🚀 Starting TikTok repurpose pipeline for @{username}")
        
        platforms = platforms or ["instagram", "youtube", "threads", "twitter"]
        account_ids = account_ids or self.DEFAULT_ACCOUNTS
        
        result = RepurposeResult(success=False)
        
        try:
            # Step 1: Fetch videos
            videos = await self.fetch_tiktok_videos(username, count)
            result.videos_fetched = len(videos)
            
            if not videos:
                result.errors.append("No videos fetched")
                return result
            
            # Step 2: Download videos
            if download:
                videos = await self.download_videos(videos)
                result.videos_downloaded = len([v for v in videos if v.downloaded])
            
            # Step 3: Save as posted content
            await self.save_as_posted_content(videos)
            
            # Step 4: Save to media library
            await self.save_to_media_library(videos)
            
            # Step 4.5: Generate thumbnails
            await self.generate_thumbnails(videos)
            
            # Step 5: Analyze videos and generate AI content
            ai_content = []
            if analyze:
                ai_content = await self.analyze_videos(videos)
                result.videos_analyzed = len(ai_content)
            
            # Step 6: Schedule cross-posts with AI-generated content
            if schedule_crosspost:
                result.crosspost_scheduled = await self.schedule_crossposts(
                    videos, platforms, account_ids, ai_content=ai_content
                )
            
            result.success = True
            result.videos = [v.to_dict() for v in videos]
            
            logger.success(f"✅ Pipeline complete: {result.videos_fetched} fetched, "
                          f"{result.videos_downloaded} downloaded, "
                          f"{result.crosspost_scheduled} scheduled")
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            result.errors.append(str(e))
        
        return result


# Singleton instance
_service_instance = None

def get_repurpose_service() -> TikTokRepurposeService:
    global _service_instance
    if _service_instance is None:
        _service_instance = TikTokRepurposeService()
    return _service_instance
