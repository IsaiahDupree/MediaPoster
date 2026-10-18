"""
Tests for DM Permission Service (OPS-017, OPS-018)
===================================================

OPS-017: DM Permission Gate
- No links in DMs until consent received
- Track consent status per contact
- Respect user preferences

OPS-018: Stop Command Handler
- Detect 'stop' in messages
- Mark contact as do-not-message
- Handle variations: "stop", "unsubscribe", "no thanks", etc.
"""

import pytest
import asyncio
from datetime import datetime, timezone

from services.dm_permission_service import (
    DMPermissionService,
    ConsentStatus,
    StopCommand,
    ContactPermissions,
)
from services.event_bus import EventBus


@pytest.fixture
def event_bus():
    """Get fresh event bus instance"""
    EventBus._instance = None
    return EventBus.get_instance()


@pytest.fixture
def dm_service(event_bus):
    """Get fresh DM permission service for each test"""
    DMPermissionService._instance = None
    return DMPermissionService.get_instance(event_bus)


class TestContactPermissions:
    """Test ContactPermissions dataclass"""

    def test_initial_state(self):
        """Test initial permission state"""
        perms = ContactPermissions(
            contact_id="user123",
            platform="twitter"
        )

        assert perms.contact_id == "user123"
        assert perms.platform == "twitter"
        assert perms.consent_status == ConsentStatus.UNKNOWN
        assert perms.message_count == 0
        assert perms.consent_granted_at is None

    def test_can_send_message_default(self):
        """Test can send message by default"""
        perms = ContactPermissions(
            contact_id="user123",
            platform="twitter"
        )

        assert perms.can_send_message() is True

    def test_can_send_message_after_stop(self):
        """Test cannot send message after stop"""
        perms = ContactPermissions(
            contact_id="user123",
            platform="twitter",
            consent_status=ConsentStatus.STOPPED
        )

        assert perms.can_send_message() is False

    def test_can_send_link_requires_consent(self):
        """Test links require consent (OPS-017)"""
        perms = ContactPermissions(
            contact_id="user123",
            platform="twitter"
        )

        # Unknown: no links
        assert perms.can_send_link() is False

        # Pending: no links
        perms.consent_status = ConsentStatus.PENDING
        assert perms.can_send_link() is False

        # Denied: no links
        perms.consent_status = ConsentStatus.DENIED
        assert perms.can_send_link() is False

        # Granted: links allowed
        perms.consent_status = ConsentStatus.GRANTED
        assert perms.can_send_link() is True

    def test_should_ask_consent(self):
        """Test should ask consent for unknown contacts"""
        perms = ContactPermissions(
            contact_id="user123",
            platform="twitter"
        )

        assert perms.should_ask_consent() is True

        perms.consent_status = ConsentStatus.PENDING
        assert perms.should_ask_consent() is False

    def test_to_dict(self):
        """Test conversion to dictionary"""
        perms = ContactPermissions(
            contact_id="user123",
            platform="twitter",
            consent_status=ConsentStatus.GRANTED,
            message_count=5
        )

        data = perms.to_dict()

        assert data["contact_id"] == "user123"
        assert data["platform"] == "twitter"
        assert data["consent_status"] == "granted"
        assert data["message_count"] == 5
        assert data["can_send_message"] is True
        assert data["can_send_link"] is True


class TestDMPermissionService:
    """Test DM Permission Service"""

    def test_singleton_pattern(self, event_bus):
        """Test singleton pattern"""
        DMPermissionService._instance = None
        service1 = DMPermissionService.get_instance(event_bus)
        service2 = DMPermissionService.get_instance()
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_get_permissions_creates_new(self, dm_service):
        """Test get_permissions creates new contact if not exists"""
        perms = await dm_service.get_permissions("twitter", "user123")

        assert perms.contact_id == "user123"
        assert perms.platform == "twitter"
        assert perms.consent_status == ConsentStatus.UNKNOWN

    @pytest.mark.asyncio
    async def test_get_permissions_returns_existing(self, dm_service):
        """Test get_permissions returns existing contact"""
        # Create contact
        perms1 = await dm_service.get_permissions("twitter", "user123")
        perms1.message_count = 5

        # Get again - should be same instance
        perms2 = await dm_service.get_permissions("twitter", "user123")
        assert perms2.message_count == 5

    @pytest.mark.asyncio
    async def test_check_can_send_message(self, dm_service):
        """Test checking if can send message"""
        # Unknown contact: can send
        assert await dm_service.check_can_send_message("twitter", "user123") is True

        # Stop contact: cannot send
        await dm_service.mark_stopped("twitter", "user123", "stop")
        assert await dm_service.check_can_send_message("twitter", "user123") is False

    @pytest.mark.asyncio
    async def test_check_can_send_link_requires_consent(self, dm_service):
        """Test OPS-017: links require consent"""
        # Unknown contact: no links
        assert await dm_service.check_can_send_link("twitter", "user123") is False

        # Grant consent: links allowed
        await dm_service.grant_consent("twitter", "user123")
        assert await dm_service.check_can_send_link("twitter", "user123") is True

    @pytest.mark.asyncio
    async def test_request_consent(self, dm_service):
        """Test requesting consent"""
        await dm_service.request_consent("twitter", "user123")

        perms = await dm_service.get_permissions("twitter", "user123")
        assert perms.consent_status == ConsentStatus.PENDING
        assert perms.consent_requested_at is not None

    @pytest.mark.asyncio
    async def test_grant_consent(self, dm_service):
        """Test granting consent"""
        await dm_service.grant_consent("twitter", "user123")

        perms = await dm_service.get_permissions("twitter", "user123")
        assert perms.consent_status == ConsentStatus.GRANTED
        assert perms.consent_granted_at is not None

    @pytest.mark.asyncio
    async def test_deny_consent(self, dm_service):
        """Test denying consent"""
        await dm_service.deny_consent("twitter", "user123")

        perms = await dm_service.get_permissions("twitter", "user123")
        assert perms.consent_status == ConsentStatus.DENIED

    @pytest.mark.asyncio
    async def test_mark_stopped(self, dm_service):
        """Test OPS-018: mark contact as stopped"""
        await dm_service.mark_stopped("twitter", "user123", "stop")

        perms = await dm_service.get_permissions("twitter", "user123")
        assert perms.consent_status == ConsentStatus.STOPPED
        assert perms.stopped_at is not None
        assert perms.stop_command == "stop"
        assert perms.can_send_message() is False

    @pytest.mark.asyncio
    async def test_record_message_sent(self, dm_service):
        """Test recording sent messages"""
        await dm_service.record_message_sent("twitter", "user123")
        await dm_service.record_message_sent("twitter", "user123")
        await dm_service.record_message_sent("twitter", "user123")

        perms = await dm_service.get_permissions("twitter", "user123")
        assert perms.message_count == 3
        assert perms.last_message_at is not None

    def test_detect_stop_command_variations(self, dm_service):
        """Test OPS-018: detect stop command variations"""
        stop_messages = [
            "stop",
            "STOP",
            "Stop messaging me",
            "Please stop",
            "unsubscribe",
            "UNSUBSCRIBE please",
            "no thanks",
            "No thanks, not interested",
            "leave me alone",
            "not interested",
            "remove me from your list",
            "opt out",
            "cancel",
            "don't message me",
            "dont message me anymore",
            "no more messages",
        ]

        for message in stop_messages:
            result = dm_service.detect_stop_command(message)
            assert result is not None, f"Failed to detect stop in: '{message}'"

    def test_detect_stop_command_false_positives(self, dm_service):
        """Test stop detection doesn't trigger on normal messages"""
        normal_messages = [
            "Hello, how are you?",
            "Thanks for reaching out!",
            "I'm interested in learning more",
            "Can you send me the link?",
            "Yes please",
        ]

        for message in normal_messages:
            result = dm_service.detect_stop_command(message)
            assert result is None, f"False positive stop detection in: '{message}'"

    def test_detect_consent_grant(self, dm_service):
        """Test detecting consent grants"""
        consent_messages = [
            "yes",
            "Yes please",
            "sure",
            "Sure, send it",
            "ok",
            "OK sounds good",
            "okay",
            "send me the link",
            "please send",
            "I'm interested",
            "yes, more info please",
        ]

        for message in consent_messages:
            result = dm_service.detect_consent_grant(message)
            assert result is True, f"Failed to detect consent in: '{message}'"

    def test_detect_consent_grant_negative(self, dm_service):
        """Test consent detection doesn't trigger on rejections"""
        negative_messages = [
            "no",
            "nope",
            "nah",
            "not interested",
            "maybe later",
        ]

        for message in negative_messages:
            result = dm_service.detect_consent_grant(message)
            assert result is False, f"False positive consent in: '{message}'"

    @pytest.mark.asyncio
    async def test_process_incoming_message_stop(self, dm_service):
        """Test processing incoming message with stop command"""
        result = await dm_service.process_incoming_message(
            "twitter", "user123", "Please stop messaging me"
        )

        assert result["stop_detected"] is True
        assert result["action_taken"] == "marked_stopped:stop"

        # Verify contact is stopped
        perms = await dm_service.get_permissions("twitter", "user123")
        assert perms.consent_status == ConsentStatus.STOPPED

    @pytest.mark.asyncio
    async def test_process_incoming_message_consent_grant(self, dm_service):
        """Test processing incoming message with consent grant"""
        result = await dm_service.process_incoming_message(
            "twitter", "user123", "Yes please send me the link"
        )

        assert result["consent_granted"] is True
        assert result["action_taken"] == "consent_granted"

        # Verify consent granted
        perms = await dm_service.get_permissions("twitter", "user123")
        assert perms.consent_status == ConsentStatus.GRANTED

    @pytest.mark.asyncio
    async def test_process_incoming_message_consent_deny(self, dm_service):
        """Test processing incoming message with consent denial"""
        result = await dm_service.process_incoming_message(
            "twitter", "user123", "no thanks"
        )

        # "no thanks" is both a stop pattern and denial
        # Stop takes priority
        assert result["stop_detected"] is True

    @pytest.mark.asyncio
    async def test_process_incoming_message_neutral(self, dm_service):
        """Test processing neutral incoming message"""
        result = await dm_service.process_incoming_message(
            "twitter", "user123", "Hello, I have a question"
        )

        assert result["stop_detected"] is False
        assert result["consent_granted"] is False
        assert result["consent_denied"] is False
        assert result["action_taken"] is None

    @pytest.mark.asyncio
    async def test_get_status_all(self, dm_service):
        """Test getting status for all contacts"""
        # Create some test contacts
        await dm_service.grant_consent("twitter", "user1")
        await dm_service.mark_stopped("twitter", "user2", "stop")
        await dm_service.deny_consent("instagram", "user3")

        status = await dm_service.get_status()

        assert status["stats"]["total"] == 3
        assert status["stats"]["by_status"]["granted"] == 1
        assert status["stats"]["by_status"]["stopped"] == 1
        assert status["stats"]["by_status"]["denied"] == 1

    @pytest.mark.asyncio
    async def test_get_status_filtered_by_platform(self, dm_service):
        """Test getting status filtered by platform"""
        await dm_service.grant_consent("twitter", "user1")
        await dm_service.grant_consent("instagram", "user2")

        status = await dm_service.get_status(platform="twitter")

        assert status["stats"]["total"] == 1
        assert status["contacts"][0]["platform"] == "twitter"

    @pytest.mark.asyncio
    async def test_get_status_filtered_by_consent_status(self, dm_service):
        """Test getting status filtered by consent status"""
        await dm_service.grant_consent("twitter", "user1")
        await dm_service.deny_consent("twitter", "user2")
        await dm_service.mark_stopped("twitter", "user3", "stop")

        status = await dm_service.get_status(
            consent_status=ConsentStatus.STOPPED
        )

        assert status["stats"]["total"] == 1
        assert status["contacts"][0]["consent_status"] == "stopped"

    @pytest.mark.asyncio
    async def test_reset_contact(self, dm_service):
        """Test resetting contact permissions"""
        # Create contact with some state
        await dm_service.grant_consent("twitter", "user123")
        await dm_service.record_message_sent("twitter", "user123")

        # Reset
        await dm_service.reset_contact("twitter", "user123")

        # Get again - should be fresh
        perms = await dm_service.get_permissions("twitter", "user123")
        assert perms.consent_status == ConsentStatus.UNKNOWN
        assert perms.message_count == 0

    @pytest.mark.asyncio
    async def test_multiple_platforms_same_user(self, dm_service):
        """Test same user ID on different platforms tracked separately"""
        await dm_service.grant_consent("twitter", "user123")
        await dm_service.mark_stopped("instagram", "user123", "stop")

        # Twitter: granted
        twitter_perms = await dm_service.get_permissions("twitter", "user123")
        assert twitter_perms.consent_status == ConsentStatus.GRANTED

        # Instagram: stopped
        instagram_perms = await dm_service.get_permissions("instagram", "user123")
        assert instagram_perms.consent_status == ConsentStatus.STOPPED

    @pytest.mark.asyncio
    async def test_thread_safety(self, dm_service):
        """Test concurrent access is thread-safe"""
        async def grant_and_check(user_id):
            await dm_service.grant_consent("twitter", user_id)
            perms = await dm_service.get_permissions("twitter", user_id)
            assert perms.consent_status == ConsentStatus.GRANTED

        # Run 10 concurrent operations
        tasks = [grant_and_check(f"user{i}") for i in range(10)]
        await asyncio.gather(*tasks)

        # Verify all 10 contacts created
        status = await dm_service.get_status()
        assert status["stats"]["total"] == 10


class TestStopCommandPriority:
    """Test OPS-018: stop command always takes priority"""

    @pytest.mark.asyncio
    async def test_stop_overrides_previous_consent(self, dm_service):
        """Test stop command overrides previously granted consent"""
        # Grant consent first
        await dm_service.grant_consent("twitter", "user123")
        assert await dm_service.check_can_send_link("twitter", "user123") is True

        # User says stop
        await dm_service.mark_stopped("twitter", "user123", "stop")
        assert await dm_service.check_can_send_message("twitter", "user123") is False
        assert await dm_service.check_can_send_link("twitter", "user123") is False

    @pytest.mark.asyncio
    async def test_stop_in_message_processing(self, dm_service):
        """Test stop detected in message processing"""
        # Process message with "yes" AND "stop" - stop takes priority
        result = await dm_service.process_incoming_message(
            "twitter", "user123", "yes please stop sending me messages"
        )

        assert result["stop_detected"] is True
        assert result["consent_granted"] is False

        perms = await dm_service.get_permissions("twitter", "user123")
        assert perms.consent_status == ConsentStatus.STOPPED


class TestEventPublishing:
    """Test event publishing for integration"""

    @pytest.mark.asyncio
    async def test_consent_requested_event(self, dm_service, event_bus):
        """Test consent requested event published"""
        events = []
        def capture_event(event):
            events.append(event)

        event_bus.subscribe("dm.consent.requested", capture_event)

        await dm_service.request_consent("twitter", "user123")

        # Give event bus time to process
        await asyncio.sleep(0.1)

        assert len(events) == 1
        assert events[0].payload["platform"] == "twitter"
        assert events[0].payload["contact_id"] == "user123"

    @pytest.mark.asyncio
    async def test_consent_granted_event(self, dm_service, event_bus):
        """Test consent granted event published"""
        events = []
        def capture_event(event):
            events.append(event)

        event_bus.subscribe("dm.consent.granted", capture_event)

        await dm_service.grant_consent("twitter", "user123")

        await asyncio.sleep(0.1)

        assert len(events) == 1
        assert events[0].payload["platform"] == "twitter"

    @pytest.mark.asyncio
    async def test_contact_stopped_event(self, dm_service, event_bus):
        """Test contact stopped event published"""
        events = []
        def capture_event(event):
            events.append(event)

        event_bus.subscribe("dm.contact.stopped", capture_event)

        await dm_service.mark_stopped("twitter", "user123", "unsubscribe")

        await asyncio.sleep(0.1)

        assert len(events) == 1
        assert events[0].payload["stop_command"] == "unsubscribe"
