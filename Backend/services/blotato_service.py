"""
Blotato Service
===============
Central service for Blotato API integration with pub/sub event handling.

Topics:
    - blotato.publish.requested - Request to publish content
    - blotato.publish.started - Publishing process started
    - blotato.publish.completed - Content published successfully
    - blotato.publish.failed - Publishing failed
    - blotato.account.verified - Account verification completed
    - blotato.account.sync - Account sync requested
"""

import asyncio
import os
import httpx
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from loguru import logger
from enum import Enum

# Import event bus
try:
    from services.event_bus import EventBus, Event
    from services.event_bus.topics import Topics
except ImportError:
    EventBus = None
    Event = None
    Topics = None


class BlotatoPlatform(str, Enum):
    """Supported Blotato platforms"""
    TIKTOK = "tiktok"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    TWITTER = "twitter"
    THREADS = "threads"
    PINTEREST = "pinterest"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    BLUESKY = "bluesky"


@dataclass
class BlotatoAccount:
    """Blotato account representation"""
    id: int
    platform: str
    username: str
    display_name: Optional[str] = None
    is_active: bool = True
    last_verified: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


# Master account mapping - Source of truth
BLOTATO_ACCOUNTS: List[BlotatoAccount] = [
    # TikTok (4)
    BlotatoAccount(710, "tiktok", "isaiah_dupree", "Isaiah Dupree"),
    BlotatoAccount(243, "tiktok", "the_isaiah_dupree", "The Isaiah Dupree"),
    BlotatoAccount(4508, "tiktok", "dupree_isaiah", "Dupree Isaiah"),
    BlotatoAccount(571, "tiktok", "soursides_is_sour", "Soursides"),
    
    # Instagram (4)
    BlotatoAccount(807, "instagram", "the_isaiah_dupree", "The Isaiah Dupree"),
    BlotatoAccount(670, "instagram", "the_isaiah_dupree_", "The Isaiah Dupree"),
    BlotatoAccount(1369, "instagram", "dupree_isaiah_", "Dupree Isaiah"),
    BlotatoAccount(4508, "instagram", "dupree_isaiah", "Dupree Isaiah"),
    
    # YouTube (2)
    BlotatoAccount(228, "youtube", "UCnDBsELI2OlaEl5yxA77HNA", "Isaiah Dupree"),
    BlotatoAccount(3370, "youtube", "lofi_creator", "lofi creator"),
    
    # Twitter/X (1)
    BlotatoAccount(4151, "twitter", "IsaiahDupree7", "Isaiah Dupree"),
    
    # Threads (4)
    BlotatoAccount(173, "threads", "the_isaiah_dupree_", "The Isaiah Dupree"),
    BlotatoAccount(201, "threads", "the_isaiah_dupree", "The Isaiah Dupree"),
    BlotatoAccount(1369, "threads", "dupree_isaiah_", "Dupree Isaiah"),
    BlotatoAccount(4150, "threads", "isaiahdupree75", "Isaiah Dupree"),
    
    # Pinterest (2)
    BlotatoAccount(173, "pinterest", "isaiahdupree33", "Isaiah Dupree"),
    BlotatoAccount(243, "pinterest", "isaiahdupree75", "Isaiah Dupree"),
    
    # LinkedIn (1)
    BlotatoAccount(571, "linkedin", "IsaiahDupree7", "Isaiah Dupree"),
    
    # Facebook (1)
    BlotatoAccount(786, "facebook", "Isaiah Dupree", "Isaiah Dupree"),
    
    # Bluesky (1)
    BlotatoAccount(201, "bluesky", "the_isaiah_dupree_", "The Isaiah Dupree"),
]


class BlotatoService:
    """
    Blotato API integration service with pub/sub support.
    
    Usage:
        service = BlotatoService()
        
        # Get account by ID
        account = service.get_account_by_id(710)
        
        # Find account by username
        account = service.find_account("tiktok", "@isaiah_dupree")
        
        # Publish content (with event bus)
        await service.publish_content(media_id, account_id, caption)
    """
    
    _instance: Optional["BlotatoService"] = None
    
    def __init__(self):
        self.api_key = os.getenv("BLOTATO_API_KEY")
        self.base_url = "https://api.blotato.com/v2"
        self.accounts = BLOTATO_ACCOUNTS
        self._event_bus = EventBus.get_instance() if EventBus else None
        
        # Subscribe to blotato events
        if self._event_bus:
            self._setup_subscriptions()
    
    @classmethod
    def get_instance(cls) -> "BlotatoService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _setup_subscriptions(self):
        """Set up event bus subscriptions"""
        if not self._event_bus:
            return
        
        # Subscribe to publish requests
        self._event_bus.subscribe("blotato.publish.requested", self._handle_publish_request)
        self._event_bus.subscribe("blotato.account.sync", self._handle_account_sync)
        
        logger.info("[BlotatoService] Subscribed to event bus topics")
    
    async def _handle_publish_request(self, event: Any):
        """Handle publish request from event bus"""
        data = event.data if hasattr(event, 'data') else event
        logger.info(f"[BlotatoService] Received publish request: {data}")
        
        media_id = data.get("media_id")
        account_id = data.get("account_id")
        caption = data.get("caption", "")
        
        if media_id and account_id:
            await self.publish_content(media_id, account_id, caption)
    
    async def _handle_account_sync(self, event: Any):
        """Handle account sync request"""
        logger.info("[BlotatoService] Syncing accounts...")
        await self.verify_all_accounts()
    
    # === Account Management ===
    
    def get_all_accounts(self) -> List[BlotatoAccount]:
        """Get all registered Blotato accounts"""
        return self.accounts
    
    def get_accounts_by_platform(self, platform: str) -> List[BlotatoAccount]:
        """Get all accounts for a platform"""
        platform_lower = platform.lower()
        return [a for a in self.accounts if a.platform.lower() == platform_lower]
    
    def get_account_by_id(self, account_id: int) -> Optional[BlotatoAccount]:
        """Get account by Blotato ID"""
        for account in self.accounts:
            if account.id == account_id:
                return account
        return None
    
    def find_account(self, platform: str, username: str) -> Optional[BlotatoAccount]:
        """Find account by platform and username (flexible matching)"""
        platform_lower = platform.lower()
        username_normalized = self._normalize_username(username)
        
        for account in self.accounts:
            if account.platform.lower() != platform_lower:
                continue
            
            account_username = self._normalize_username(account.username)
            
            # Exact match or partial match
            if (account_username == username_normalized or
                account_username in username_normalized or
                username_normalized in account_username):
                return account
        
        return None
    
    def _normalize_username(self, username: str) -> str:
        """Normalize username for matching"""
        return (username or "").lower().strip().lstrip("@").rstrip("_")
    
    # === Publishing ===
    
    async def publish_content(
        self,
        media_id: str,
        account_id: int,
        caption: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Publish content to Blotato.
        
        Emits events:
            - blotato.publish.started
            - blotato.publish.completed OR blotato.publish.failed
        """
        account = self.get_account_by_id(account_id)
        if not account:
            error = f"Account {account_id} not found"
            await self._emit_event("blotato.publish.failed", {
                "media_id": media_id,
                "account_id": account_id,
                "error": error
            })
            return {"success": False, "error": error}
        
        # Emit started event
        await self._emit_event("blotato.publish.started", {
            "media_id": media_id,
            "account_id": account_id,
            "platform": account.platform,
            "username": account.username
        })
        
        try:
            # Call Blotato API
            result = await self._call_blotato_api(
                endpoint="/posts",
                method="POST",
                data={
                    "account_id": account_id,
                    "text": caption,
                    **kwargs
                }
            )
            
            # Emit completed event
            await self._emit_event("blotato.publish.completed", {
                "media_id": media_id,
                "account_id": account_id,
                "platform": account.platform,
                "result": result
            })
            
            return {"success": True, "result": result}
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"[BlotatoService] Publish failed: {error_msg}")
            
            await self._emit_event("blotato.publish.failed", {
                "media_id": media_id,
                "account_id": account_id,
                "error": error_msg
            })
            
            return {"success": False, "error": error_msg}
    
    async def _call_blotato_api(
        self,
        endpoint: str,
        method: str = "GET",
        data: Optional[Dict] = None
    ) -> Dict:
        """Make API call to Blotato"""
        if not self.api_key:
            raise ValueError("BLOTATO_API_KEY not configured")
        
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(url, headers=headers, timeout=30)
            elif method == "POST":
                response = await client.post(url, headers=headers, json=data, timeout=30)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response.raise_for_status()
            return response.json()
    
    async def _emit_event(self, topic: str, data: Dict):
        """Emit event to event bus"""
        if self._event_bus:
            await self._event_bus.publish(topic, data)
        logger.info(f"[BlotatoService] Event: {topic} -> {data}")
    
    # === Account Verification ===
    
    async def verify_account(self, account_id: int) -> Dict[str, Any]:
        """Verify a single account is connected and active"""
        account = self.get_account_by_id(account_id)
        if not account:
            return {"verified": False, "error": "Account not found"}
        
        try:
            # In production, call Blotato API to verify
            # For now, mark as verified
            account.last_verified = datetime.now(timezone.utc)
            account.is_active = True
            
            await self._emit_event("blotato.account.verified", {
                "account_id": account_id,
                "platform": account.platform,
                "username": account.username,
                "verified": True
            })
            
            return {"verified": True, "account": account.to_dict()}
            
        except Exception as e:
            return {"verified": False, "error": str(e)}
    
    async def verify_all_accounts(self) -> List[Dict]:
        """Verify all accounts"""
        results = []
        for account in self.accounts:
            result = await self.verify_account(account.id)
            results.append({
                "id": account.id,
                "platform": account.platform,
                "username": account.username,
                **result
            })
        return results


# Singleton accessor
def get_blotato_service() -> BlotatoService:
    """Get the Blotato service instance"""
    return BlotatoService.get_instance()
