"""
Comment Fetcher Service (INBOX-002)
====================================
Fetches comments from X, Instagram, TikTok, YouTube, and other platforms
and stores them in the unified Community Inbox.

Features:
- Multi-platform comment fetching
- Automatic identity mapping
- Duplicate detection
- Sentiment analysis integration
- Event-driven architecture
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from uuid import uuid4
from loguru import logger

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CommunityInboxMessage, PlatformPost, Person, Identity
from database.connection import async_session_maker
from services.event_bus import EventBus, Topics
from services.sentiment_analyzer import get_sentiment_analyzer


class CommentFetcherService:
    """
    INBOX-002: Comment Fetcher Service

    Fetches comments from multiple platforms and stores them
    in the unified Community Inbox.

    Usage:
        fetcher = CommentFetcherService.get_instance()
        await fetcher.start()

        # Fetch comments for a specific post
        await fetcher.fetch_comments_for_post(
            platform="instagram",
            post_id="abc123",
            workspace_id="workspace-uuid"
        )

        # Fetch all recent comments (last 24h)
        await fetcher.fetch_recent_comments(workspace_id="workspace-uuid")
    """

    _instance: Optional["CommentFetcherService"] = None

    def __init__(self):
        """Initialize comment fetcher service"""
        if CommentFetcherService._instance is not None:
            raise RuntimeError("Use CommentFetcherService.get_instance()")

        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("comment-fetcher-service")

        self._is_running = False
        self._fetch_task: Optional[asyncio.Task] = None
        self._fetch_interval = 300  # Fetch every 5 minutes

        # Platform-specific fetchers
        self._platform_fetchers = {
            "instagram": self._fetch_instagram_comments,
            "tiktok": self._fetch_tiktok_comments,
            "youtube": self._fetch_youtube_comments,
            "twitter": self._fetch_twitter_comments,
            "facebook": self._fetch_facebook_comments,
            "threads": self._fetch_threads_comments,
            "linkedin": self._fetch_linkedin_comments,
        }

        logger.info("💬 Comment Fetcher Service initialized")

    @classmethod
    def get_instance(cls) -> "CommentFetcherService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start the comment fetcher service"""
        if self._is_running:
            logger.warning("Comment fetcher service already running")
            return

        self._is_running = True
        self._fetch_task = asyncio.create_task(self._fetch_loop())

        await self.event_bus.publish(
            Topics.SYSTEM_STARTUP,
            {
                "service": "comment_fetcher",
                "started_at": datetime.now(timezone.utc).isoformat()
            }
        )

        logger.success("✓ Comment Fetcher Service started")

    async def stop(self) -> None:
        """Stop the comment fetcher service"""
        self._is_running = False

        if self._fetch_task:
            self._fetch_task.cancel()
            try:
                await self._fetch_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 Comment Fetcher Service stopped")

    async def fetch_recent_comments(
        self,
        workspace_id: str,
        hours: int = 24
    ) -> Dict[str, int]:
        """
        Fetch recent comments from all platforms

        Args:
            workspace_id: Workspace UUID
            hours: How many hours back to fetch (default: 24)

        Returns:
            Dictionary with platform names and comment counts
        """
        logger.info(f"📥 Fetching comments from last {hours}h for workspace {workspace_id}")

        results = {}

        async with async_session_maker() as session:
            # Get all recent platform posts
            since = datetime.now(timezone.utc) - timedelta(hours=hours)

            stmt = select(PlatformPost).where(
                and_(
                    PlatformPost.published_at >= since,
                    PlatformPost.status == "published"
                )
            )

            result = await session.execute(stmt)
            posts = result.scalars().all()

            logger.info(f"Found {len(posts)} published posts in last {hours}h")

            # Group posts by platform
            posts_by_platform = {}
            for post in posts:
                if post.platform not in posts_by_platform:
                    posts_by_platform[post.platform] = []
                posts_by_platform[post.platform].append(post)

            # Fetch comments for each platform
            for platform, platform_posts in posts_by_platform.items():
                if platform not in self._platform_fetchers:
                    logger.warning(f"No fetcher for platform: {platform}")
                    continue

                platform_count = 0
                for post in platform_posts:
                    try:
                        count = await self.fetch_comments_for_post(
                            platform=platform,
                            post_id=post.platform_post_id,
                            workspace_id=workspace_id,
                            session=session
                        )
                        platform_count += count
                    except Exception as e:
                        logger.error(f"Error fetching comments for {platform} post {post.id}: {e}")

                results[platform] = platform_count

        total = sum(results.values())
        logger.success(f"✓ Fetched {total} total comments across {len(results)} platforms")

        return results

    async def fetch_comments_for_post(
        self,
        platform: str,
        post_id: str,
        workspace_id: str,
        session: Optional[AsyncSession] = None
    ) -> int:
        """
        Fetch comments for a specific post

        Args:
            platform: Platform name (instagram, tiktok, etc.)
            post_id: Platform-specific post ID
            workspace_id: Workspace UUID
            session: Optional database session (creates new if not provided)

        Returns:
            Number of new comments fetched
        """
        if platform not in self._platform_fetchers:
            logger.warning(f"No fetcher for platform: {platform}")
            return 0

        fetcher = self._platform_fetchers[platform]

        # Use provided session or create new one
        if session:
            return await fetcher(post_id, workspace_id, session)
        else:
            async with async_session_maker() as new_session:
                return await fetcher(post_id, workspace_id, new_session)

    async def _fetch_instagram_comments(
        self,
        post_id: str,
        workspace_id: str,
        session: AsyncSession
    ) -> int:
        """Fetch Instagram comments using RapidAPI or Safari automation"""
        logger.debug(f"Fetching Instagram comments for post {post_id}")

        try:
            # Try RapidAPI first
            from connectors.rapidapi_comments import fetch_instagram_comments

            comments = await fetch_instagram_comments(post_id)

            if not comments:
                return 0

            # Store comments in database
            new_count = 0
            for comment in comments:
                exists = await self._check_comment_exists(
                    platform="instagram",
                    source_content_id=post_id,
                    author_handle=comment.get("username"),
                    created_at_platform=comment.get("timestamp"),
                    session=session
                )

                if exists:
                    continue

                # Map user to person (if exists)
                author_person_id = await self._find_or_create_person(
                    username=comment.get("username"),
                    platform="instagram",
                    workspace_id=workspace_id,
                    session=session
                )

                # Analyze sentiment
                analyzer = get_sentiment_analyzer()
                sentiment_result = await analyzer.analyze_text(comment.get("text", ""))
                sentiment = {
                    "score": sentiment_result.score,
                    "label": sentiment_result.label,
                    "emotions": list(sentiment_result.emotions.keys()) if sentiment_result.emotions else []
                }

                # Create inbox message
                inbox_message = CommunityInboxMessage(
                    id=uuid4(),
                    workspace_id=workspace_id,
                    platform="instagram",
                    message_type="comment",
                    source_content_id=post_id,
                    source_url=comment.get("permalink"),
                    author_person_id=author_person_id,
                    author_handle=comment.get("username"),
                    author_name=comment.get("full_name"),
                    author_id_platform=comment.get("user_id"),
                    author_profile_url=f"https://instagram.com/{comment.get('username')}",
                    text=comment.get("text", ""),
                    conversation_id=f"instagram_{post_id}",
                    is_thread_root=comment.get("parent_id") is None,
                    sentiment_score=sentiment.get("score"),
                    sentiment_label=sentiment.get("label"),
                    emotion_tags=sentiment.get("emotions", []),
                    intent=self._classify_intent(comment.get("text", "")),
                    created_at_platform=datetime.fromisoformat(comment.get("timestamp")),
                    platform_data=comment
                )

                session.add(inbox_message)
                new_count += 1

            await session.commit()

            logger.success(f"✓ Fetched {new_count} new Instagram comments for post {post_id}")

            # Emit event
            await self.event_bus.publish(
                "inbox.comments.fetched",
                {
                    "platform": "instagram",
                    "post_id": post_id,
                    "comment_count": new_count,
                    "workspace_id": workspace_id
                }
            )

            return new_count

        except Exception as e:
            logger.error(f"Error fetching Instagram comments: {e}")
            return 0

    async def _fetch_tiktok_comments(
        self,
        post_id: str,
        workspace_id: str,
        session: AsyncSession
    ) -> int:
        """Fetch TikTok comments using RapidAPI"""
        logger.debug(f"Fetching TikTok comments for post {post_id}")

        try:
            from connectors.rapidapi_comments import fetch_tiktok_comments

            comments = await fetch_tiktok_comments(post_id)

            if not comments:
                return 0

            new_count = 0
            for comment in comments:
                exists = await self._check_comment_exists(
                    platform="tiktok",
                    source_content_id=post_id,
                    author_handle=comment.get("unique_id"),
                    created_at_platform=comment.get("create_time"),
                    session=session
                )

                if exists:
                    continue

                # Map user to person
                author_person_id = await self._find_or_create_person(
                    username=comment.get("unique_id"),
                    platform="tiktok",
                    workspace_id=workspace_id,
                    session=session
                )

                # Analyze sentiment
                analyzer = get_sentiment_analyzer()
                sentiment_result = await analyzer.analyze_text(comment.get("text", ""))
                sentiment = {
                    "score": sentiment_result.score,
                    "label": sentiment_result.label,
                    "emotions": list(sentiment_result.emotions.keys()) if sentiment_result.emotions else []
                }

                # Create inbox message
                inbox_message = CommunityInboxMessage(
                    id=uuid4(),
                    workspace_id=workspace_id,
                    platform="tiktok",
                    message_type="comment",
                    source_content_id=post_id,
                    author_person_id=author_person_id,
                    author_handle=comment.get("unique_id"),
                    author_name=comment.get("nickname"),
                    author_id_platform=comment.get("uid"),
                    text=comment.get("text", ""),
                    conversation_id=f"tiktok_{post_id}",
                    sentiment_score=sentiment.get("score"),
                    sentiment_label=sentiment.get("label"),
                    emotion_tags=sentiment.get("emotions", []),
                    intent=self._classify_intent(comment.get("text", "")),
                    created_at_platform=datetime.fromtimestamp(comment.get("create_time"), tz=timezone.utc),
                    platform_data=comment
                )

                session.add(inbox_message)
                new_count += 1

            await session.commit()

            logger.success(f"✓ Fetched {new_count} new TikTok comments for post {post_id}")

            return new_count

        except Exception as e:
            logger.error(f"Error fetching TikTok comments: {e}")
            return 0

    async def _fetch_youtube_comments(
        self,
        post_id: str,
        workspace_id: str,
        session: AsyncSession
    ) -> int:
        """Fetch YouTube comments using YouTube Data API"""
        logger.debug(f"Fetching YouTube comments for video {post_id}")

        # TODO: Implement YouTube API integration
        # See: https://developers.google.com/youtube/v3/docs/commentThreads/list

        return 0

    async def _fetch_twitter_comments(
        self,
        post_id: str,
        workspace_id: str,
        session: AsyncSession
    ) -> int:
        """Fetch Twitter/X replies"""
        logger.debug(f"Fetching Twitter replies for tweet {post_id}")

        # TODO: Implement Twitter API integration
        # See: Backend/connectors/twitter_connector.py

        return 0

    async def _fetch_facebook_comments(
        self,
        post_id: str,
        workspace_id: str,
        session: AsyncSession
    ) -> int:
        """Fetch Facebook comments"""
        logger.debug(f"Fetching Facebook comments for post {post_id}")

        # TODO: Implement Facebook Graph API integration

        return 0

    async def _fetch_threads_comments(
        self,
        post_id: str,
        workspace_id: str,
        session: AsyncSession
    ) -> int:
        """Fetch Threads comments"""
        logger.debug(f"Fetching Threads comments for post {post_id}")

        # TODO: Implement Threads API integration

        return 0

    async def _fetch_linkedin_comments(
        self,
        post_id: str,
        workspace_id: str,
        session: AsyncSession
    ) -> int:
        """Fetch LinkedIn comments"""
        logger.debug(f"Fetching LinkedIn comments for post {post_id}")

        # TODO: Implement LinkedIn API integration

        return 0

    async def _check_comment_exists(
        self,
        platform: str,
        source_content_id: str,
        author_handle: str,
        created_at_platform: Any,
        session: AsyncSession
    ) -> bool:
        """Check if comment already exists in database"""
        stmt = select(CommunityInboxMessage).where(
            and_(
                CommunityInboxMessage.platform == platform,
                CommunityInboxMessage.source_content_id == source_content_id,
                CommunityInboxMessage.author_handle == author_handle,
                CommunityInboxMessage.created_at_platform == created_at_platform
            )
        )

        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def _find_or_create_person(
        self,
        username: str,
        platform: str,
        workspace_id: str,
        session: AsyncSession
    ) -> Optional[str]:
        """Find or create person from username"""
        # Check if identity exists
        stmt = select(Identity).where(
            and_(
                Identity.channel == platform,
                Identity.handle == username
            )
        )

        result = await session.execute(stmt)
        identity = result.scalar_one_or_none()

        if identity:
            return str(identity.person_id)

        # Create new person and identity
        person = Person(
            id=uuid4(),
            workspace_id=workspace_id,
            full_name=username
        )
        session.add(person)

        identity = Identity(
            person_id=person.id,
            channel=platform,
            handle=username,
            is_verified=False
        )
        session.add(identity)

        await session.flush()

        return str(person.id)

    def _classify_intent(self, text: str) -> str:
        """Classify comment intent (simple keyword-based)"""
        text_lower = text.lower()

        if any(q in text_lower for q in ["?", "how", "what", "when", "where", "why", "which"]):
            return "question"
        elif any(p in text_lower for p in ["love", "amazing", "great", "awesome", "fantastic", "perfect"]):
            return "praise"
        elif any(c in text_lower for c in ["bad", "hate", "terrible", "awful", "worst", "disappointed"]):
            return "critique"
        elif any(s in text_lower for s in ["spam", "click here", "check out", "buy now", "visit"]):
            return "spam"
        else:
            return "engagement"

    async def _fetch_loop(self) -> None:
        """Background loop to periodically fetch comments"""
        logger.info("🔍 Comment fetch loop started")

        while self._is_running:
            try:
                # Get all workspaces and fetch comments
                async with async_session_maker() as session:
                    from database.models import Workspace

                    stmt = select(Workspace)
                    result = await session.execute(stmt)
                    workspaces = result.scalars().all()

                    for workspace in workspaces:
                        try:
                            await self.fetch_recent_comments(
                                workspace_id=str(workspace.id),
                                hours=1  # Fetch last hour of comments
                            )
                        except Exception as e:
                            logger.error(f"Error fetching comments for workspace {workspace.id}: {e}")

                # Wait for next fetch
                await asyncio.sleep(self._fetch_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in comment fetch loop: {e}")
                await asyncio.sleep(self._fetch_interval)

        logger.info("🛑 Comment fetch loop stopped")


# Singleton accessor
def get_comment_fetcher() -> CommentFetcherService:
    """Get the singleton comment fetcher instance"""
    return CommentFetcherService.get_instance()
