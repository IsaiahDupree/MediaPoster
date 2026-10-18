#!/usr/bin/env python3
"""
Tests for Instagram DM Controller
====================================
Covers IG-DM-001 through IG-DM-005.

All tests run in dev mode so Safari is never required.
"""
import os
import sys
import tempfile
import pytest
import pytest_asyncio

# Ensure Backend is on the path so imports resolve.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from automation.instagram_dm_controller import (
    InstagramDMController,
    InstagramConversation,
    InstagramMessage,
    get_instagram_dm_controller,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton between every test."""
    InstagramDMController.reset_instance()
    yield
    InstagramDMController.reset_instance()


@pytest.fixture
def controller() -> InstagramDMController:
    """Return a fresh dev-mode controller."""
    return InstagramDMController(dev_mode=True)


@pytest.fixture
def controller_with_conversation(controller: InstagramDMController):
    """Return a controller that already has one conversation seeded."""
    conv = InstagramConversation(
        participant_username="alice",
        participant_display_name="Alice",
    )
    controller.conversations[conv.id] = conv
    controller.is_authenticated = True
    controller.username = "dev_user"
    return controller, conv


@pytest.fixture
def controller_with_message_requests(controller: InstagramDMController):
    """Return a controller with message requests seeded."""
    req = InstagramConversation(
        participant_username="stranger",
        participant_display_name="Stranger",
        is_message_request=True,
        last_message_preview="Hey! Love your content",
    )
    controller.message_requests[req.id] = req
    controller.is_authenticated = True
    controller.username = "dev_user"
    return controller, req


# ===========================================================================
# IG-DM-001  Navigation & Authentication
# ===========================================================================

class TestIGDM001_Navigation:
    """Tests for IG-DM-001: Navigation & Auth."""

    def test_navigate_to_inbox_success(self, controller: InstagramDMController):
        """navigate_to_inbox should succeed and return the inbox URL."""
        result = controller.navigate_to_inbox()
        assert result["success"] is True
        assert "instagram.com/direct/inbox" in result["url"]

    def test_navigate_to_inbox_sets_current_url(self, controller: InstagramDMController):
        """After navigation the controller's current_url should be updated."""
        controller.navigate_to_inbox()
        assert controller.current_url == InstagramDMController.INSTAGRAM_INBOX_URL

    def test_authenticate_dev_mode(self, controller: InstagramDMController):
        """In dev mode, authenticate should always succeed."""
        result = controller.authenticate()
        assert result["authenticated"] is True
        assert controller.is_authenticated is True
        assert controller.username == "dev_user"

    def test_singleton_pattern(self):
        """get_instagram_dm_controller should return the same instance."""
        c1 = get_instagram_dm_controller(dev_mode=True)
        c2 = get_instagram_dm_controller(dev_mode=True)
        assert c1 is c2


# ===========================================================================
# IG-DM-002  Inbox Management
# ===========================================================================

class TestIGDM002_InboxManagement:
    """Tests for IG-DM-002: Inbox Management."""

    def test_get_inbox_empty(self, controller: InstagramDMController):
        """get_inbox on an empty controller should return zero conversations."""
        result = controller.get_inbox()
        assert result["success"] is True
        assert result["count"] == 0
        assert result["unread_count"] == 0

    def test_get_inbox_with_conversations(self, controller_with_conversation):
        """get_inbox should list existing conversations."""
        ctrl, conv = controller_with_conversation
        result = ctrl.get_inbox()
        assert result["success"] is True
        assert result["count"] == 1
        assert result["conversations"][0]["participant_username"] == "alice"

    def test_get_conversations_limit(self, controller: InstagramDMController):
        """get_conversations should respect the limit parameter."""
        for i in range(5):
            c = InstagramConversation(participant_username=f"user_{i}")
            controller.conversations[c.id] = c
        convos = controller.get_conversations(limit=3)
        assert len(convos) == 3

    def test_mark_as_read(self, controller_with_conversation):
        """mark_as_read should set is_read=True on conversation and messages."""
        ctrl, conv = controller_with_conversation
        conv.is_read = False
        msg = InstagramMessage(conversation_id=conv.id, text="hi", is_read=False)
        conv.messages.append(msg)

        result = ctrl.mark_as_read(conv.id)
        assert result["success"] is True
        assert conv.is_read is True
        assert conv.messages[0].is_read is True


# ===========================================================================
# IG-DM-003  Message Send / Read
# ===========================================================================

class TestIGDM003_MessageSendRead:
    """Tests for IG-DM-003: Message Send/Read."""

    def test_send_message_success(self, controller_with_conversation):
        """send_message should append a message to the conversation."""
        ctrl, conv = controller_with_conversation
        result = ctrl.send_message(conv.id, "Hello Instagram!")
        assert result["success"] is True
        assert result["text"] == "Hello Instagram!"
        assert len(conv.messages) == 1
        assert conv.messages[0].is_outgoing is True

    def test_send_message_empty_text(self, controller_with_conversation):
        """send_message with empty text should fail."""
        ctrl, conv = controller_with_conversation
        result = ctrl.send_message(conv.id, "   ")
        assert result["success"] is False
        assert "empty" in result["error"].lower()

    def test_send_message_nonexistent_conv(self, controller: InstagramDMController):
        """send_message for a missing conversation should fail."""
        result = controller.send_message("nonexistent_id", "Hi")
        assert result["success"] is False

    def test_read_messages(self, controller_with_conversation):
        """read_messages should return all messages in a conversation."""
        ctrl, conv = controller_with_conversation
        ctrl.send_message(conv.id, "msg1")
        ctrl.send_message(conv.id, "msg2")
        result = ctrl.read_messages(conv.id)
        assert result["success"] is True
        assert result["count"] == 2
        assert result["messages"][0]["text"] == "msg1"
        assert result["messages"][1]["text"] == "msg2"


# ===========================================================================
# IG-DM-004  New Conversation
# ===========================================================================

class TestIGDM004_NewConversation:
    """Tests for IG-DM-004: New Conversation."""

    def test_new_conversation_creates_entry(self, controller: InstagramDMController):
        """new_conversation should create a conversation and send the first message."""
        controller.is_authenticated = True
        controller.username = "dev_user"
        result = controller.new_conversation("bob", "Hey Bob!")
        assert result["success"] is True
        assert result["is_new"] is True
        assert result["username"] == "bob"
        assert len(controller.conversations) == 1

    def test_new_conversation_reuses_existing(self, controller_with_conversation):
        """new_conversation with an existing contact should reuse the conversation."""
        ctrl, conv = controller_with_conversation
        result = ctrl.new_conversation("alice", "Hey again Alice")
        assert result["success"] is True
        assert result["is_new"] is False
        assert result["conversation_id"] == conv.id
        assert len(ctrl.conversations) == 1

    def test_new_conversation_empty_username(self, controller: InstagramDMController):
        """new_conversation with empty username should fail."""
        result = controller.new_conversation("", "Hello")
        assert result["success"] is False
        assert "empty" in result["error"].lower()


# ===========================================================================
# IG-DM-005  Media & Message Requests
# ===========================================================================

class TestIGDM005_MediaRequests:
    """Tests for IG-DM-005: Media & Message Requests."""

    def test_send_media_success(self, controller_with_conversation):
        """send_media with a valid file should succeed."""
        ctrl, conv = controller_with_conversation
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(b"fake_image_data")
            temp_path = f.name
        try:
            result = ctrl.send_media(conv.id, temp_path)
            assert result["success"] is True
            assert result["media_path"] == temp_path
            assert len(conv.messages) == 1
            assert conv.messages[0].media_url == temp_path
        finally:
            os.unlink(temp_path)

    def test_send_media_file_not_found(self, controller_with_conversation):
        """send_media with a nonexistent file should fail."""
        ctrl, conv = controller_with_conversation
        result = ctrl.send_media(conv.id, "/nonexistent/file.jpg")
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_handle_message_requests_empty(self, controller: InstagramDMController):
        """handle_message_requests with no requests should return empty list."""
        result = controller.handle_message_requests()
        assert result["success"] is True
        assert result["count"] == 0
        assert result["requests"] == []
