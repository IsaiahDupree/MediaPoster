"""
DM Permission Service (OPS-017, OPS-018)
========================================
Manages consent and permissions for DM automation.

OPS-017: DM Permission Gate
- No links in DMs until consent received
- Track consent status per contact
- Respect user preferences

OPS-018: Stop Command Handler
- Detect 'stop' in messages
- Mark contact as do-not-message
- Handle variations: "stop", "unsubscribe", "no thanks", etc.
"""

import asyncio
from typing import Dict, Optional, List, Set
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
from loguru import logger

from services.event_bus import EventBus, Topics


class ConsentStatus(Enum):
    """Consent status for DM communication"""
    UNKNOWN = "unknown"  # No interaction yet
    PENDING = "pending"  # Asked for consent, awaiting response
    GRANTED = "granted"  # Consent granted (can send links)
    DENIED = "denied"  # Consent denied (no links)
    STOPPED = "stopped"  # User said stop (no messages at all)


class StopCommand(Enum):
    """Stop command variations"""
    STOP = "stop"
    UNSUBSCRIBE = "unsubscribe"
    NO_THANKS = "no thanks"
    LEAVE_ME_ALONE = "leave me alone"
    NOT_INTERESTED = "not interested"
    REMOVE_ME = "remove me"


@dataclass
class ContactPermissions:
    """Permission state for a contact"""
    contact_id: str  # Platform-specific ID
    platform: str  # twitter, instagram, etc.
    consent_status: ConsentStatus = ConsentStatus.UNKNOWN
    consent_granted_at: Optional[datetime] = None
    consent_requested_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    stop_command: Optional[str] = None
    message_count: int = 0
    last_message_at: Optional[datetime] = None

    def can_send_message(self) -> bool:
        """Check if we can send any message"""
        return self.consent_status != ConsentStatus.STOPPED

    def can_send_link(self) -> bool:
        """Check if we can send links"""
        return self.consent_status == ConsentStatus.GRANTED

    def should_ask_consent(self) -> bool:
        """Check if we should ask for consent"""
        return self.consent_status == ConsentStatus.UNKNOWN

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "contact_id": self.contact_id,
            "platform": self.platform,
            "consent_status": self.consent_status.value,
            "consent_granted_at": self.consent_granted_at.isoformat() if self.consent_granted_at else None,
            "consent_requested_at": self.consent_requested_at.isoformat() if self.consent_requested_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "stop_command": self.stop_command,
            "message_count": self.message_count,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "can_send_message": self.can_send_message(),
            "can_send_link": self.can_send_link(),
            "should_ask_consent": self.should_ask_consent(),
        }


class DMPermissionService:
    """
    Service to manage DM permissions and consent.

    Ensures compliance with:
    - No unsolicited links in DMs
    - Respect "stop" commands
    - Track consent per contact
    """

    _instance: Optional["DMPermissionService"] = None

    # Stop command patterns (case-insensitive)
    STOP_PATTERNS = [
        "stop",
        "unsubscribe",
        "no thanks",
        "leave me alone",
        "not interested",
        "remove me",
        "opt out",
        "cancel",
        "don't message",
        "dont message",
        "no more",
    ]

    # Consent grant patterns (case-insensitive)
    CONSENT_PATTERNS = [
        "yes",
        "sure",
        "ok",
        "okay",
        "send",
        "please",
        "interested",
        "link",
        "more info",
    ]

    def __init__(self, event_bus: Optional[EventBus] = None):
        if DMPermissionService._instance is not None:
            raise RuntimeError("Use DMPermissionService.get_instance()")

        self.event_bus = event_bus or EventBus.get_instance()

        # Permissions: {platform:contact_id -> ContactPermissions}
        self._permissions: Dict[str, ContactPermissions] = {}

        # Lock for thread safety
        self._lock = asyncio.Lock()

        logger.info("✓ DM Permission Service initialized")

    @classmethod
    def get_instance(cls, event_bus: Optional[EventBus] = None) -> "DMPermissionService":
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls(event_bus)
        return cls._instance

    def _get_key(self, platform: str, contact_id: str) -> str:
        """Generate unique key for contact"""
        return f"{platform}:{contact_id}"

    async def get_permissions(self, platform: str, contact_id: str) -> ContactPermissions:
        """
        Get permissions for a contact.

        Args:
            platform: Platform name (twitter, instagram, etc.)
            contact_id: Platform-specific contact ID

        Returns:
            ContactPermissions object
        """
        async with self._lock:
            key = self._get_key(platform, contact_id)

            if key not in self._permissions:
                self._permissions[key] = ContactPermissions(
                    contact_id=contact_id,
                    platform=platform
                )

            return self._permissions[key]

    async def check_can_send_message(self, platform: str, contact_id: str) -> bool:
        """
        Check if we can send any message to this contact.

        Args:
            platform: Platform name
            contact_id: Contact ID

        Returns:
            True if message allowed, False if contact said stop
        """
        permissions = await self.get_permissions(platform, contact_id)
        return permissions.can_send_message()

    async def check_can_send_link(self, platform: str, contact_id: str) -> bool:
        """
        Check if we can send links to this contact (OPS-017).

        Args:
            platform: Platform name
            contact_id: Contact ID

        Returns:
            True if links allowed (consent granted), False otherwise
        """
        permissions = await self.get_permissions(platform, contact_id)
        return permissions.can_send_link()

    async def request_consent(self, platform: str, contact_id: str) -> None:
        """
        Mark that we've requested consent from this contact.

        Args:
            platform: Platform name
            contact_id: Contact ID
        """
        async with self._lock:
            permissions = await self.get_permissions(platform, contact_id)
            permissions.consent_status = ConsentStatus.PENDING
            permissions.consent_requested_at = datetime.now(timezone.utc)

            logger.info(
                f"📨 Consent requested: {platform}/{contact_id}"
            )

            # Publish event
            await self.event_bus.publish(
                Topics.DM_CONSENT_REQUESTED,
                {
                    "platform": platform,
                    "contact_id": contact_id,
                    "requested_at": permissions.consent_requested_at.isoformat()
                },
                source="dm-permission-service"
            )

    async def grant_consent(self, platform: str, contact_id: str) -> None:
        """
        Grant consent for sending links.

        Args:
            platform: Platform name
            contact_id: Contact ID
        """
        async with self._lock:
            permissions = await self.get_permissions(platform, contact_id)
            permissions.consent_status = ConsentStatus.GRANTED
            permissions.consent_granted_at = datetime.now(timezone.utc)

            logger.info(
                f"✅ Consent granted: {platform}/{contact_id}"
            )

            # Publish event
            await self.event_bus.publish(
                Topics.DM_CONSENT_GRANTED,
                {
                    "platform": platform,
                    "contact_id": contact_id,
                    "granted_at": permissions.consent_granted_at.isoformat()
                },
                source="dm-permission-service"
            )

    async def deny_consent(self, platform: str, contact_id: str) -> None:
        """
        Deny consent for sending links.

        Args:
            platform: Platform name
            contact_id: Contact ID
        """
        async with self._lock:
            permissions = await self.get_permissions(platform, contact_id)
            permissions.consent_status = ConsentStatus.DENIED

            logger.info(
                f"❌ Consent denied: {platform}/{contact_id}"
            )

            # Publish event
            await self.event_bus.publish(
                Topics.DM_CONSENT_DENIED,
                {
                    "platform": platform,
                    "contact_id": contact_id
                },
                source="dm-permission-service"
            )

    async def mark_stopped(
        self,
        platform: str,
        contact_id: str,
        stop_command: str
    ) -> None:
        """
        Mark contact as stopped (do-not-message) (OPS-018).

        Args:
            platform: Platform name
            contact_id: Contact ID
            stop_command: The stop command used
        """
        async with self._lock:
            permissions = await self.get_permissions(platform, contact_id)
            permissions.consent_status = ConsentStatus.STOPPED
            permissions.stopped_at = datetime.now(timezone.utc)
            permissions.stop_command = stop_command

            logger.warning(
                f"🛑 Contact stopped: {platform}/{contact_id} (command: '{stop_command}')"
            )

            # Publish event
            await self.event_bus.publish(
                Topics.DM_CONTACT_STOPPED,
                {
                    "platform": platform,
                    "contact_id": contact_id,
                    "stop_command": stop_command,
                    "stopped_at": permissions.stopped_at.isoformat()
                },
                source="dm-permission-service"
            )

    async def record_message_sent(self, platform: str, contact_id: str) -> None:
        """
        Record that we sent a message to this contact.

        Args:
            platform: Platform name
            contact_id: Contact ID
        """
        async with self._lock:
            permissions = await self.get_permissions(platform, contact_id)
            permissions.message_count += 1
            permissions.last_message_at = datetime.now(timezone.utc)

    def detect_stop_command(self, message: str) -> Optional[str]:
        """
        Detect if message contains a stop command (OPS-018).

        Args:
            message: Message text

        Returns:
            The stop command found, or None
        """
        message_lower = message.lower().strip()

        for pattern in self.STOP_PATTERNS:
            if pattern in message_lower:
                return pattern

        return None

    def detect_consent_grant(self, message: str) -> bool:
        """
        Detect if message grants consent.

        Args:
            message: Message text

        Returns:
            True if consent granted
        """
        message_lower = message.lower().strip()

        for pattern in self.CONSENT_PATTERNS:
            if pattern in message_lower:
                return True

        return False

    async def process_incoming_message(
        self,
        platform: str,
        contact_id: str,
        message: str
    ) -> Dict:
        """
        Process an incoming message and update permissions.

        Checks for:
        - Stop commands (OPS-018)
        - Consent grants
        - Consent denials

        Args:
            platform: Platform name
            contact_id: Contact ID
            message: Message text

        Returns:
            Dictionary with processing results
        """
        result = {
            "stop_detected": False,
            "consent_granted": False,
            "consent_denied": False,
            "action_taken": None
        }

        # Check for stop command first (highest priority)
        stop_command = self.detect_stop_command(message)
        if stop_command:
            await self.mark_stopped(platform, contact_id, stop_command)
            result["stop_detected"] = True
            result["action_taken"] = f"marked_stopped:{stop_command}"
            return result

        # Check for consent grant
        if self.detect_consent_grant(message):
            await self.grant_consent(platform, contact_id)
            result["consent_granted"] = True
            result["action_taken"] = "consent_granted"
            return result

        # Check for explicit denial
        message_lower = message.lower().strip()
        deny_patterns = ["no", "nope", "nah", "not interested"]
        for pattern in deny_patterns:
            if pattern in message_lower:
                await self.deny_consent(platform, contact_id)
                result["consent_denied"] = True
                result["action_taken"] = "consent_denied"
                return result

        return result

    async def get_status(
        self,
        platform: Optional[str] = None,
        consent_status: Optional[ConsentStatus] = None
    ) -> Dict:
        """
        Get permission status summary.

        Args:
            platform: Optional platform filter
            consent_status: Optional status filter

        Returns:
            Dictionary with status summary
        """
        async with self._lock:
            contacts = []

            for key, permissions in self._permissions.items():
                # Apply filters
                if platform and permissions.platform != platform:
                    continue
                if consent_status and permissions.consent_status != consent_status:
                    continue

                contacts.append(permissions.to_dict())

            # Calculate stats
            stats = {
                "total": len(contacts),
                "by_status": {
                    "unknown": 0,
                    "pending": 0,
                    "granted": 0,
                    "denied": 0,
                    "stopped": 0
                }
            }

            for contact in contacts:
                status = contact["consent_status"]
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

            return {
                "stats": stats,
                "contacts": contacts
            }

    async def reset_contact(self, platform: str, contact_id: str) -> None:
        """
        Reset permissions for a contact (for testing/admin).

        Args:
            platform: Platform name
            contact_id: Contact ID
        """
        async with self._lock:
            key = self._get_key(platform, contact_id)

            if key in self._permissions:
                del self._permissions[key]
                logger.info(f"♻️  Reset permissions: {platform}/{contact_id}")
