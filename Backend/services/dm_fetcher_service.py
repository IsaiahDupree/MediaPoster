"""
DM Fetcher Service (INBOX-003)
==============================
Fetches DMs from X (Twitter), Instagram, Threads, and other platforms
and stores them in the unified Community Inbox.

Features:
- Multi-platform DM fetching (Instagram, Twitter, Threads)
- Thread grouping and conversation management
- Automatic identity mapping
- Duplicate detection
- Sentiment analysis integration
- Event-driven architecture

Usage:
    fetcher = DMFetcherService.get_instance()
    await fetcher.start()

    # Fetch DMs for a specific user
    await fetcher.fetch_user_dms(
        platform="instagram",
        user_id="abc123",
        workspace_id="workspace-uuid"
    )

    # Fetch all recent DMs (last 24h)
    await fetcher.fetch_recent_dms(workspace_id="workspace-uuid")
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4
from loguru import logger

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CommunityInboxMessage, Person, Identity
from database.connection import async_session_maker
from services.event_bus import EventBus, Topics
from services.sentiment_analyzer import get_sentiment_analyzer


class DMFetcherService:
    """
    INBOX-003: DM Fetcher Service

    Fetches DMs from multiple platforms and stores them
    in the unified Community Inbox with thread grouping.

    Supported Platforms:
    - Instagram (via Meta Graph API)
    - Twitter/X (via Twitter API v2)
    - Threads (via Meta Graph API)
    """

    _instance: Optional["DMFetcherService"] = None

    def __init__(self):
        """Initialize DM fetcher service"""
        if DMFetcherService._instance is not None:
            raise RuntimeError("Use DMFetcherService.get_instance()")

        self.event_bus = EventBus.get_instance()
        self.event_bus.set_source("dm-fetcher-service")
        self.sentiment_analyzer = get_sentiment_analyzer()

        self._is_running = False
        self._fetch_task: Optional[asyncio.Task] = None
        self._fetch_interval = 600  # Fetch every 10 minutes

        # Platform-specific fetchers
        self._platform_fetchers = {
            "instagram": self._fetch_instagram_dms,
            "twitter": self._fetch_twitter_dms,
            "threads": self._fetch_threads_dms,
        }

        logger.info("💬 DM Fetcher Service initialized")

    @classmethod
    def get_instance(cls) -> "DMFetcherService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start the DM fetcher service"""
        if self._is_running:
            logger.warning("DM fetcher service already running")
            return

        self._is_running = True
        self._fetch_task = asyncio.create_task(self._fetch_loop())

        await self.event_bus.publish(
            Topics.SYSTEM_STARTUP,
            {
                "service": "dm_fetcher",
                "started_at": datetime.now(timezone.utc).isoformat()
            }
        )

        logger.success("✓ DM Fetcher Service started")

    async def stop(self) -> None:
        """Stop the DM fetcher service"""
        self._is_running = False

        if self._fetch_task:
            self._fetch_task.cancel()
            try:
                await self._fetch_task
            except asyncio.CancelledError:
                pass

        logger.info("🛑 DM Fetcher Service stopped")

    # =========================================================================
    # MAIN FETCH METHODS
    # =========================================================================

    async def fetch_recent_dms(
        self,
        workspace_id: str,
        hours: int = 24,
        platforms: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Fetch recent DMs from all platforms

        Args:
            workspace_id: Workspace UUID
            hours: How many hours back to fetch (default: 24)
            platforms: List of platforms to fetch from (default: all)

        Returns:
            Dictionary with platform names and DM counts
        """
        if not platforms:
            platforms = list(self._platform_fetchers.keys())

        logger.info(f"📥 Fetching DMs from last {hours}h for workspace {workspace_id}")

        results = {}

        for platform in platforms:
            if platform not in self._platform_fetchers:
                logger.warning(f"Unsupported platform: {platform}")
                continue

            try:
                fetcher = self._platform_fetchers[platform]
                count = await fetcher(workspace_id, hours)
                results[platform] = count
                logger.info(f"✓ Fetched {count} DMs from {platform}")
            except Exception as e:
                logger.error(f"✗ Error fetching {platform} DMs: {str(e)}")
                results[platform] = 0

        # Publish event
        await self.event_bus.publish(
            "inbox.dms.fetched",
            {
                "workspace_id": workspace_id,
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

        return results

    async def fetch_user_dms(
        self,
        platform: str,
        user_id: str,
        workspace_id: str,
        limit: int = 100
    ) -> int:
        """
        Fetch DMs for a specific user

        Args:
            platform: Platform name (instagram, twitter, threads)
            user_id: Platform user ID
            workspace_id: Workspace UUID
            limit: Max DMs to fetch

        Returns:
            Number of DMs fetched
        """
        if platform not in self._platform_fetchers:
            raise ValueError(f"Unsupported platform: {platform}")

        logger.info(f"📨 Fetching DMs from {platform} user {user_id}")

        async with async_session_maker() as session:
            # Platform-specific fetch
            if platform == "instagram":
                return await self._fetch_instagram_user_dms(
                    session, user_id, workspace_id, limit
                )
            elif platform == "twitter":
                return await self._fetch_twitter_user_dms(
                    session, user_id, workspace_id, limit
                )
            elif platform == "threads":
                return await self._fetch_threads_user_dms(
                    session, user_id, workspace_id, limit
                )

        return 0

    # =========================================================================
    # PLATFORM-SPECIFIC FETCHERS
    # =========================================================================

    async def _fetch_instagram_dms(
        self,
        workspace_id: str,
        hours: int
    ) -> int:
        """Fetch recent Instagram DMs"""
        logger.debug(f"Fetching Instagram DMs from last {hours}h")

        async with async_session_maker() as session:
            # Get connected Instagram account
            # Note: In production, would fetch from user's connected accounts
            # For now, using placeholder logic that can be extended

            dm_count = 0
            # TODO: Implement actual Instagram API calls
            # This would involve:
            # 1. Get user's Instagram Business Account ID
            # 2. Call Meta Graph API: GET /{ig-user-id}/conversations
            # 3. For each conversation, fetch messages
            # 4. Group messages into threads
            # 5. Store in database

            return dm_count

    async def _fetch_instagram_user_dms(
        self,
        session: AsyncSession,
        user_id: str,
        workspace_id: str,
        limit: int
    ) -> int:
        """Fetch DMs from specific Instagram user"""
        logger.debug(f"Fetching Instagram DMs from user {user_id}")

        # TODO: Implement actual Instagram API calls
        # Would fetch conversation thread with specific user

        return 0

    async def _fetch_twitter_dms(
        self,
        workspace_id: str,
        hours: int
    ) -> int:
        """Fetch recent Twitter/X DMs"""
        logger.debug(f"Fetching Twitter DMs from last {hours}h")

        async with async_session_maker() as session:
            dm_count = 0
            # TODO: Implement actual Twitter API calls
            # This would involve:
            # 1. Call Twitter API v2: GET /2/dm_events
            # 2. Filter by timestamp
            # 3. For each DM, create InboxMessage
            # 4. Group related messages into conversations
            # 5. Store in database

            return dm_count

    async def _fetch_twitter_user_dms(
        self,
        session: AsyncSession,
        user_id: str,
        workspace_id: str,
        limit: int
    ) -> int:
        """Fetch DMs from specific Twitter user"""
        logger.debug(f"Fetching Twitter DMs from user {user_id}")

        # TODO: Implement actual Twitter API calls
        # Would fetch DM conversation with specific user

        return 0

    async def _fetch_threads_dms(
        self,
        workspace_id: str,
        hours: int
    ) -> int:
        """Fetch recent Threads DMs"""
        logger.debug(f"Fetching Threads DMs from last {hours}h")

        async with async_session_maker() as session:
            dm_count = 0
            # TODO: Implement actual Threads API calls
            # Threads uses Meta Graph API similar to Instagram
            # Similar flow as Instagram DM fetching

            return dm_count

    async def _fetch_threads_user_dms(
        self,
        session: AsyncSession,
        user_id: str,
        workspace_id: str,
        limit: int
    ) -> int:
        """Fetch DMs from specific Threads user"""
        logger.debug(f"Fetching Threads DMs from user {user_id}")

        # TODO: Implement actual Threads API calls

        return 0

    # =========================================================================
    # THREAD GROUPING & MESSAGE PROCESSING
    # =========================================================================

    async def _group_dms_into_threads(
        self,
        messages: List[Dict[str, Any]]
    ) -> List[Tuple[str, List[Dict[str, Any]]]]:
        """
        Group individual DMs into conversation threads

        Args:
            messages: List of DM dictionaries

        Returns:
            List of (thread_id, messages) tuples
        """
        threads: Dict[str, List[Dict[str, Any]]] = {}

        for msg in messages:
            # Extract or generate thread ID
            thread_id = msg.get("conversation_id") or msg.get("thread_id")

            if not thread_id:
                # For platforms without native thread IDs,
                # group by platform + sender (bidirectional conversation)
                sender_id = msg.get("sender_id", "unknown")
                platform = msg.get("platform", "unknown")
                thread_id = f"{platform}:{sender_id}"

            if thread_id not in threads:
                threads[thread_id] = []

            threads[thread_id].append(msg)

        # Sort messages within each thread by timestamp
        for thread_id in threads:
            threads[thread_id].sort(
                key=lambda m: m.get("timestamp", datetime.now(timezone.utc))
            )

        logger.info(f"📦 Grouped {len(messages)} DMs into {len(threads)} threads")

        return list(threads.items())

    async def _check_dm_exists(
        self,
        session: AsyncSession,
        platform: str,
        platform_message_id: str,
        workspace_id: str
    ) -> bool:
        """Check if DM already exists in database (deduplication)"""
        stmt = select(CommunityInboxMessage).where(
            and_(
                CommunityInboxMessage.platform == platform,
                CommunityInboxMessage.platform_message_id == platform_message_id,
                CommunityInboxMessage.workspace_id == workspace_id,
                CommunityInboxMessage.message_type == "dm"
            )
        )

        result = await session.execute(stmt)
        return result.scalars().first() is not None

    async def _find_or_create_person(
        self,
        session: AsyncSession,
        platform: str,
        username: str,
        name: Optional[str] = None,
        avatar_url: Optional[str] = None,
        follower_count: int = 0,
        workspace_id: Optional[str] = None
    ) -> Person:
        """Find or create person record for DM sender"""
        # Try to find existing person by platform identity
        stmt = select(Person).join(Identity).where(
            and_(
                Identity.platform == platform,
                Identity.username == username,
                Person.workspace_id == workspace_id
            )
        )

        result = await session.execute(stmt)
        person = result.scalars().first()

        if person:
            return person

        # Create new person
        person_id = str(uuid4())
        person = Person(
            id=person_id,
            name=name or username,
            workspace_id=workspace_id,
            created_at=datetime.now(timezone.utc)
        )

        session.add(person)
        await session.flush()

        # Create identity record
        identity = Identity(
            id=str(uuid4()),
            person_id=person_id,
            platform=platform,
            username=username,
            avatar_url=avatar_url,
            follower_count=follower_count,
            created_at=datetime.now(timezone.utc)
        )

        session.add(identity)
        await session.flush()

        logger.info(f"👤 Created person: {username} on {platform}")

        return person

    async def _store_dm_message(
        self,
        session: AsyncSession,
        message_data: Dict[str, Any],
        thread_id: str,
        workspace_id: str
    ) -> Optional[CommunityInboxMessage]:
        """Store DM message in unified inbox"""
        # Check for duplicate
        if await self._check_dm_exists(
            session,
            message_data["platform"],
            message_data["platform_message_id"],
            workspace_id
        ):
            return None

        # Get or create person
        person = await self._find_or_create_person(
            session=session,
            platform=message_data["platform"],
            username=message_data["sender_username"],
            name=message_data.get("sender_name"),
            avatar_url=message_data.get("sender_avatar_url"),
            follower_count=message_data.get("sender_follower_count", 0),
            workspace_id=workspace_id
        )

        # Analyze sentiment
        sentiment_score = 0.0
        sentiment_label = "neutral"
        if self.sentiment_analyzer:
            try:
                sentiment = await self.sentiment_analyzer.analyze(
                    message_data.get("content", "")
                )
                sentiment_score = sentiment.get("score", 0.0)
                sentiment_label = sentiment.get("label", "neutral")
            except Exception as e:
                logger.warning(f"Sentiment analysis failed: {str(e)}")

        # Create message record
        message = CommunityInboxMessage(
            id=str(uuid4()),
            workspace_id=workspace_id,
            platform=message_data["platform"],
            message_type="dm",
            sender_id=person.id,
            sender_username=message_data["sender_username"],
            sender_name=message_data.get("sender_name", ""),
            sender_avatar_url=message_data.get("sender_avatar_url"),
            sender_follower_count=message_data.get("sender_follower_count", 0),
            content=message_data.get("content", ""),
            media_url=message_data.get("media_url"),
            conversation_id=thread_id,
            thread_id=thread_id,
            is_thread_root=message_data.get("is_thread_root", False),
            platform_message_id=message_data["platform_message_id"],
            received_at=message_data.get("received_at", datetime.now(timezone.utc)),
            sentiment_label=sentiment_label,
            sentiment_score=sentiment_score,
            status="unread",
            priority="medium",
            created_at=datetime.now(timezone.utc)
        )

        session.add(message)
        await session.flush()

        logger.debug(f"📨 Stored DM: {message_data['platform']} from @{message_data['sender_username']}")

        return message

    # =========================================================================
    # BACKGROUND FETCH LOOP
    # =========================================================================

    async def _fetch_loop(self) -> None:
        """Background loop that periodically fetches DMs"""
        logger.info("🔄 DM Fetcher background loop started")

        while self._is_running:
            try:
                # TODO: Get list of all workspaces with connected accounts
                # For now, this is a placeholder
                # In production:
                # 1. Query User table to get all workspaces
                # 2. For each workspace, check which platforms are connected
                # 3. Fetch DMs from those platforms

                await asyncio.sleep(self._fetch_interval)

            except Exception as e:
                logger.error(f"Error in DM fetch loop: {str(e)}")
                await asyncio.sleep(self._fetch_interval)

        logger.info("🛑 DM Fetcher background loop stopped")


# =============================================================================
# SINGLETON
# =============================================================================

_dm_fetcher_instance: Optional[DMFetcherService] = None


def get_dm_fetcher_service() -> DMFetcherService:
    """Get singleton instance of DMFetcherService"""
    global _dm_fetcher_instance
    if _dm_fetcher_instance is None:
        _dm_fetcher_instance = DMFetcherService()
    return _dm_fetcher_instance
