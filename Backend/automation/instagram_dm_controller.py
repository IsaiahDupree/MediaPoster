#!/usr/bin/env python3
"""
Instagram DM Controller - Safari automation for Instagram Direct Messages
==========================================================================
Implements IG-DM-001 through IG-DM-005 for managing Instagram DMs
via Safari browser automation with AppleScript.

Feature IDs:
- IG-DM-001: Navigation & Authentication
- IG-DM-002: Inbox Management
- IG-DM-003: Message Send/Read
- IG-DM-004: New Conversation
- IG-DM-005: Media & Message Requests

Supports dev mode with in-memory state tracking (no Safari required).
"""
import subprocess
import time
import json
import os
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from uuid import uuid4
from loguru import logger

# Import session manager for login verification
try:
    from automation.safari_session_manager import SafariSessionManager, Platform
    HAS_SESSION_MANAGER = True
except ImportError:
    try:
        from safari_session_manager import SafariSessionManager, Platform
        HAS_SESSION_MANAGER = True
    except ImportError:
        HAS_SESSION_MANAGER = False
        logger.warning("Session manager not available for Instagram DM controller")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class InstagramMessage:
    """A single message in an Instagram DM conversation."""
    id: str = field(default_factory=lambda: str(uuid4()))
    conversation_id: str = ""
    sender: str = ""          # username of sender
    text: str = ""
    media_url: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_read: bool = False
    is_outgoing: bool = False
    is_liked: bool = False

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender": self.sender,
            "text": self.text,
            "media_url": self.media_url,
            "timestamp": self.timestamp.isoformat(),
            "is_read": self.is_read,
            "is_outgoing": self.is_outgoing,
            "is_liked": self.is_liked,
        }


@dataclass
class InstagramConversation:
    """An Instagram DM conversation."""
    id: str = field(default_factory=lambda: str(uuid4()))
    participant_username: str = ""
    participant_display_name: Optional[str] = None
    last_message_preview: str = ""
    last_message_at: Optional[datetime] = None
    is_read: bool = True
    is_muted: bool = False
    is_message_request: bool = False
    messages: List[InstagramMessage] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "participant_username": self.participant_username,
            "participant_display_name": self.participant_display_name,
            "last_message_preview": self.last_message_preview,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "is_read": self.is_read,
            "is_muted": self.is_muted,
            "is_message_request": self.is_message_request,
            "message_count": len(self.messages),
        }


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------

class InstagramDMController:
    """
    Safari-based DM controller for Instagram.

    Provides methods for navigating to the Instagram inbox, reading and
    sending messages, starting new conversations, sending media, and
    handling message requests.

    In dev mode (``dev_mode=True``), all operations are performed against
    in-memory state so that Safari does not need to be running.
    """

    # Instagram URLs
    INSTAGRAM_BASE_URL = "https://www.instagram.com"
    INSTAGRAM_INBOX_URL = "https://www.instagram.com/direct/inbox/"
    INSTAGRAM_LOGIN_URL = "https://www.instagram.com/accounts/login/"
    INSTAGRAM_MESSAGE_REQUESTS_URL = "https://www.instagram.com/direct/requests/"

    _instance: Optional["InstagramDMController"] = None

    @classmethod
    def get_instance(cls, dev_mode: bool = False) -> "InstagramDMController":
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            cls._instance = cls(dev_mode=dev_mode)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton (useful in tests)."""
        cls._instance = None

    def __init__(self, dev_mode: bool = False):
        self.dev_mode = dev_mode

        # Session manager for login verification
        if HAS_SESSION_MANAGER and not dev_mode:
            self.session_manager = SafariSessionManager()
        else:
            self.session_manager = None

        # In-memory state --------------------------------------------------
        self.conversations: Dict[str, InstagramConversation] = {}
        self.message_requests: Dict[str, InstagramConversation] = {}
        self.is_authenticated: bool = False
        self.current_url: str = ""
        self.username: Optional[str] = None

        # Rate-limiting
        self.messages_sent_count: int = 0
        self.last_message_sent_at: Optional[datetime] = None

        logger.info("InstagramDMController initialized (dev_mode={})", dev_mode)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_applescript(self, script: str, timeout: int = 60) -> tuple:
        """Run an AppleScript snippet and return ``(success, output)``."""
        if self.dev_mode:
            return True, "dev_mode"
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "AppleScript timeout"
        except Exception as e:
            return False, str(e)

    def _escape_for_js(self, text: str) -> str:
        """Escape a string for safe embedding in JavaScript."""
        return (
            text
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("'", "\\'")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
        )

    def _navigate_to(self, url: str) -> bool:
        """Navigate Safari to *url*."""
        if self.dev_mode:
            self.current_url = url
            return True
        script = f'''
        tell application "Safari"
            activate
            if (count of windows) = 0 then
                make new document
            end if
            set URL of current tab of window 1 to "{url}"
        end tell
        '''
        success, _ = self._run_applescript(script)
        if success:
            self.current_url = url
            time.sleep(3)
        return success

    def _get_current_url(self) -> Optional[str]:
        """Return the current URL from Safari."""
        if self.dev_mode:
            return self.current_url
        script = '''
        tell application "Safari"
            tell window 1
                return URL of current tab
            end tell
        end tell
        '''
        success, url = self._run_applescript(script)
        if success:
            self.current_url = url
            return url
        return None

    # ==================================================================
    # IG-DM-001  Navigation & Authentication
    # ==================================================================

    def navigate_to_inbox(self) -> Dict[str, Any]:
        """
        Navigate Safari to the Instagram DM inbox.

        Returns:
            Dict with ``success`` flag and current URL.
        """
        logger.info("Navigating to Instagram DM inbox")
        success = self._navigate_to(self.INSTAGRAM_INBOX_URL)
        if success:
            return {"success": True, "url": self.INSTAGRAM_INBOX_URL}
        return {"success": False, "error": "Failed to navigate to Instagram inbox"}

    def authenticate(self) -> Dict[str, Any]:
        """
        Verify that the user is authenticated on Instagram in Safari.

        In dev mode this always succeeds and sets ``is_authenticated``.

        Returns:
            Dict with ``authenticated`` flag and optional username.
        """
        logger.info("Checking Instagram authentication status")

        if self.dev_mode:
            self.is_authenticated = True
            self.username = "dev_user"
            return {"authenticated": True, "username": self.username}

        # Use session manager if available
        if self.session_manager:
            try:
                logged_in = self.session_manager.require_login(Platform.INSTAGRAM)
                if logged_in:
                    self.is_authenticated = True
                    return {"authenticated": True}
                return {"authenticated": False, "error": "Not logged in to Instagram"}
            except Exception as e:
                logger.warning("Session manager check failed: {}", e)

        # Fallback: navigate and inspect the page
        self._navigate_to(self.INSTAGRAM_BASE_URL)
        script = '''
        tell application "Safari"
            tell window 1
                tell current tab
                    set jsResult to do JavaScript "
                        (function() {
                            var profileLink = document.querySelector('a[href*=\\"/direct/inbox/\\"]');
                            var navProfile = document.querySelector('img[data-testid=\\"user-avatar\\"]');
                            var searchIcon = document.querySelector('a[href=\\"/explore/\\"]');
                            if (profileLink || navProfile || searchIcon) {
                                return JSON.stringify({authenticated: true});
                            }
                            var loginForm = document.querySelector('form[id=\\"loginForm\\"]');
                            var loginBtn = document.querySelector('button[type=\\"submit\\"]');
                            if (loginForm) {
                                return JSON.stringify({authenticated: false, reason: 'login_form_visible'});
                            }
                            return JSON.stringify({authenticated: false, reason: 'unknown'});
                        })();
                    "
                    return jsResult
                end tell
            end tell
        end tell
        '''
        success, result = self._run_applescript(script)
        if success and result:
            try:
                data = json.loads(result)
                self.is_authenticated = data.get("authenticated", False)
                return data
            except json.JSONDecodeError:
                pass
        self.is_authenticated = False
        return {"authenticated": False, "error": "Unable to determine auth status"}

    # ==================================================================
    # IG-DM-002  Inbox Management
    # ==================================================================

    def get_inbox(self) -> Dict[str, Any]:
        """
        Retrieve the Instagram DM inbox (list of conversations with metadata).

        Returns:
            Dict with ``success``, ``count``, ``unread_count``, and
            ``conversations`` list.
        """
        logger.info("Fetching Instagram DM inbox")

        if self.dev_mode:
            convos = [c.to_dict() for c in self.conversations.values()]
            unread = sum(1 for c in self.conversations.values() if not c.is_read)
            return {
                "success": True,
                "count": len(convos),
                "unread_count": unread,
                "conversations": convos,
            }

        self._navigate_to(self.INSTAGRAM_INBOX_URL)
        script = '''
        tell application "Safari"
            tell window 1
                tell current tab
                    set jsResult to do JavaScript "
                        (function() {
                            var conversations = [];
                            var items = document.querySelectorAll('[role=\\"listitem\\"], [class*=\\"x9f619\\"] a[href*=\\"/direct/t/\\"]');
                            for (var i = 0; i < items.length; i++) {
                                var item = items[i];
                                var nameEl = item.querySelector('[class*=\\"x1lliihq\\"], span[dir=\\"auto\\"]');
                                var previewEl = item.querySelector('[class*=\\"xuxw1ft\\"], span[class*=\\"message\\"]');
                                var timeEl = item.querySelector('time');
                                var unreadEl = item.querySelector('[class*=\\"unread\\"], [aria-label*=\\"unread\\"]');
                                if (nameEl) {
                                    conversations.push({
                                        name: nameEl.innerText,
                                        preview: previewEl ? previewEl.innerText.substring(0, 100) : '',
                                        time: timeEl ? timeEl.getAttribute('datetime') : null,
                                        unread: !!unreadEl
                                    });
                                }
                            }
                            return JSON.stringify(conversations);
                        })();
                    "
                    return jsResult
                end tell
            end tell
        end tell
        '''
        success, result = self._run_applescript(script)
        if success and result and result != "dev_mode":
            try:
                conversations = json.loads(result)
                unread_count = sum(1 for c in conversations if c.get("unread"))
                return {
                    "success": True,
                    "count": len(conversations),
                    "unread_count": unread_count,
                    "conversations": conversations,
                }
            except json.JSONDecodeError:
                pass
        return {"success": False, "error": "Failed to fetch inbox"}

    def get_conversations(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Return a list of conversation dicts (convenience wrapper).

        Args:
            limit: Maximum conversations to return.

        Returns:
            List of conversation dicts.
        """
        inbox = self.get_inbox()
        conversations = inbox.get("conversations", [])
        return conversations[:limit]

    def mark_as_read(self, conv_id: str) -> Dict[str, Any]:
        """
        Mark a conversation as read.

        Args:
            conv_id: Conversation identifier.

        Returns:
            Dict with ``success`` flag.
        """
        logger.info("Marking Instagram conversation {} as read", conv_id)

        if self.dev_mode:
            conv = self.conversations.get(conv_id)
            if conv:
                conv.is_read = True
                for msg in conv.messages:
                    msg.is_read = True
                return {"success": True, "conversation_id": conv_id}
            return {"success": False, "error": "Conversation not found"}

        # In Safari, navigating into a conversation marks it as read
        dm_url = f"{self.INSTAGRAM_BASE_URL}/direct/t/{conv_id}/"
        success = self._navigate_to(dm_url)
        if success:
            time.sleep(2)
            return {"success": True, "conversation_id": conv_id}
        return {"success": False, "error": "Failed to open conversation"}

    # ==================================================================
    # IG-DM-003  Message Send / Read
    # ==================================================================

    def send_message(self, conv_id: str, text: str) -> Dict[str, Any]:
        """
        Send a text message in an existing conversation.

        Args:
            conv_id: Conversation identifier.
            text: Message text to send.

        Returns:
            Dict with ``success`` flag and message details.
        """
        if not text.strip():
            return {"success": False, "error": "Message text cannot be empty"}

        logger.info("Sending IG message in conversation {}: {}", conv_id, text[:50])

        if self.dev_mode:
            conv = self.conversations.get(conv_id)
            if not conv:
                return {"success": False, "error": "Conversation not found"}
            msg = InstagramMessage(
                conversation_id=conv_id,
                sender=self.username or "dev_user",
                text=text,
                is_outgoing=True,
                is_read=True,
            )
            conv.messages.append(msg)
            conv.last_message_preview = text[:100]
            conv.last_message_at = msg.timestamp
            self.messages_sent_count += 1
            self.last_message_sent_at = msg.timestamp
            return {"success": True, "message_id": msg.id, "text": text}

        # Safari automation path
        escaped_text = self._escape_for_js(text)
        script = f'''
        tell application "Safari"
            tell window 1
                tell current tab
                    set jsResult to do JavaScript "
                        (function() {{
                            var input = document.querySelector('textarea[placeholder*=\\"Message\\"], [contenteditable=\\"true\\"][role=\\"textbox\\"], [aria-label*=\\"Message\\"]');
                            if (input) {{
                                input.focus();
                                if (input.tagName === 'TEXTAREA') {{
                                    var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                                    nativeSetter.call(input, \\"{escaped_text}\\");
                                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                }} else {{
                                    document.execCommand('insertText', false, \\"{escaped_text}\\");
                                }}
                                return 'typed';
                            }}
                            return 'input_not_found';
                        }})();
                    "
                    return jsResult
                end tell
            end tell
        end tell
        '''
        success, result = self._run_applescript(script)
        if not success or result != "typed":
            return {"success": False, "error": f"Failed to type message: {result}"}

        time.sleep(0.5)

        # Click send button or press Enter
        send_script = '''
        tell application "Safari"
            tell window 1
                tell current tab
                    set jsResult to do JavaScript "
                        (function() {
                            var sendBtn = document.querySelector('button[type=\\"submit\\"]');
                            if (!sendBtn) {
                                var buttons = document.querySelectorAll('button');
                                for (var i = 0; i < buttons.length; i++) {
                                    if (buttons[i].innerText === 'Send') {
                                        sendBtn = buttons[i];
                                        break;
                                    }
                                }
                            }
                            if (sendBtn && !sendBtn.disabled) {
                                sendBtn.click();
                                return 'sent';
                            }
                            return 'send_not_found';
                        })();
                    "
                    return jsResult
                end tell
            end tell
        end tell
        '''
        success, result = self._run_applescript(send_script)
        if success and result == "sent":
            self.messages_sent_count += 1
            self.last_message_sent_at = datetime.now(timezone.utc)
            logger.info("IG message sent in conversation {}", conv_id)
            return {"success": True, "conversation_id": conv_id, "text": text}
        return {"success": False, "error": f"Failed to send message: {result}"}

    def read_messages(self, conv_id: str, limit: int = 50) -> Dict[str, Any]:
        """
        Read messages from a conversation.

        Args:
            conv_id: Conversation identifier.
            limit: Maximum messages to return.

        Returns:
            Dict with ``success``, ``count``, and ``messages`` list.
        """
        logger.info("Reading IG messages for conversation {}", conv_id)

        if self.dev_mode:
            conv = self.conversations.get(conv_id)
            if not conv:
                return {"success": False, "error": "Conversation not found"}
            msgs = [m.to_dict() for m in conv.messages[-limit:]]
            return {"success": True, "count": len(msgs), "messages": msgs}

        # Navigate to conversation first
        dm_url = f"{self.INSTAGRAM_BASE_URL}/direct/t/{conv_id}/"
        self._navigate_to(dm_url)
        time.sleep(2)

        script = f'''
        tell application "Safari"
            tell window 1
                tell current tab
                    set jsResult to do JavaScript "
                        (function() {{
                            var messages = [];
                            var items = document.querySelectorAll('[role=\\"row\\"], [class*=\\"message\\"]');
                            for (var i = 0; i < Math.min(items.length, {limit}); i++) {{
                                var item = items[i];
                                var textEl = item.querySelector('span[dir=\\"auto\\"], [class*=\\"_aacl\\"]');
                                var timeEl = item.querySelector('time');
                                var isSent = item.querySelector('[class*=\\"xexx8yu\\"]') !== null;
                                if (textEl && textEl.innerText.trim()) {{
                                    messages.push({{
                                        text: textEl.innerText,
                                        time: timeEl ? timeEl.getAttribute('datetime') : null,
                                        is_outgoing: isSent
                                    }});
                                }}
                            }}
                            return JSON.stringify(messages);
                        }})();
                    "
                    return jsResult
                end tell
            end tell
        end tell
        '''
        success, result = self._run_applescript(script)
        if success and result:
            try:
                messages = json.loads(result)
                return {"success": True, "count": len(messages), "messages": messages}
            except json.JSONDecodeError:
                pass
        return {"success": False, "error": "Failed to read messages"}

    # ==================================================================
    # IG-DM-004  New Conversation
    # ==================================================================

    def new_conversation(self, username: str, message: str) -> Dict[str, Any]:
        """
        Start a new DM conversation with an Instagram user.

        Args:
            username: Instagram username to message.
            message: Initial message text.

        Returns:
            Dict with ``success`` flag and conversation details.
        """
        if not username.strip():
            return {"success": False, "error": "Username cannot be empty"}
        if not message.strip():
            return {"success": False, "error": "Message cannot be empty"}

        logger.info("Starting new IG conversation with @{}", username)

        if self.dev_mode:
            # Check for existing conversation
            for conv in self.conversations.values():
                if conv.participant_username == username:
                    send_result = self.send_message(conv.id, message)
                    return {
                        "success": send_result.get("success", False),
                        "conversation_id": conv.id,
                        "is_new": False,
                        "username": username,
                    }

            conv = InstagramConversation(
                participant_username=username,
                participant_display_name=username,
            )
            self.conversations[conv.id] = conv
            msg = InstagramMessage(
                conversation_id=conv.id,
                sender=self.username or "dev_user",
                text=message,
                is_outgoing=True,
                is_read=True,
            )
            conv.messages.append(msg)
            conv.last_message_preview = message[:100]
            conv.last_message_at = msg.timestamp
            self.messages_sent_count += 1
            self.last_message_sent_at = msg.timestamp
            return {
                "success": True,
                "conversation_id": conv.id,
                "is_new": True,
                "username": username,
                "message_id": msg.id,
            }

        # Safari: use the new message compose flow
        new_msg_url = f"{self.INSTAGRAM_BASE_URL}/direct/new/"
        self._navigate_to(new_msg_url)
        time.sleep(2)

        # Search for the user in the recipient field
        escaped_username = self._escape_for_js(username)
        search_script = f'''
        tell application "Safari"
            tell window 1
                tell current tab
                    set jsResult to do JavaScript "
                        (function() {{
                            var searchInput = document.querySelector('input[placeholder*=\\"Search\\"], input[name=\\"queryBox\\"]');
                            if (searchInput) {{
                                searchInput.focus();
                                var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                                nativeSetter.call(searchInput, '{escaped_username}');
                                searchInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                return 'searching';
                            }}
                            return 'not_found';
                        }})();
                    "
                    return jsResult
                end tell
            end tell
        end tell
        '''
        success, result = self._run_applescript(search_script)
        if not success or result == "not_found":
            return {"success": False, "error": "Could not find search input for new message"}

        time.sleep(2)

        # Click on the user in results
        click_script = f'''
        tell application "Safari"
            tell window 1
                tell current tab
                    set jsResult to do JavaScript "
                        (function() {{
                            var results = document.querySelectorAll('[role=\\"listbox\\"] button, [class*=\\"x1i10hfl\\"]');
                            for (var i = 0; i < results.length; i++) {{
                                if (results[i].innerText.toLowerCase().includes('{escaped_username.lower()}')) {{
                                    results[i].click();
                                    return 'clicked';
                                }}
                            }}
                            return 'no_match';
                        }})();
                    "
                    return jsResult
                end tell
            end tell
        end tell
        '''
        success, result = self._run_applescript(click_script)
        if not success or result == "no_match":
            return {"success": False, "error": f"User @{username} not found in search results"}

        time.sleep(1)

        # Click "Chat" / "Next" button
        next_script = '''
        tell application "Safari"
            tell window 1
                tell current tab
                    set jsResult to do JavaScript "
                        (function() {
                            var btns = document.querySelectorAll('button');
                            for (var i = 0; i < btns.length; i++) {
                                var txt = btns[i].innerText.toLowerCase();
                                if (txt === 'chat' || txt === 'next') {
                                    btns[i].click();
                                    return 'opened';
                                }
                            }
                            return 'no_next';
                        })();
                    "
                    return jsResult
                end tell
            end tell
        end tell
        '''
        self._run_applescript(next_script)
        time.sleep(2)

        # Send the initial message
        send_result = self.send_message("new", message)
        if send_result.get("success"):
            return {
                "success": True,
                "is_new": True,
                "username": username,
                "text": message,
            }
        return {"success": False, "error": f"Failed to send initial message: {send_result.get('error')}"}

    # ==================================================================
    # IG-DM-005  Media & Message Requests
    # ==================================================================

    def send_media(self, conv_id: str, media_path: str) -> Dict[str, Any]:
        """
        Send a media file (image/video) in a conversation.

        Args:
            conv_id: Conversation identifier.
            media_path: Absolute path to the media file.

        Returns:
            Dict with ``success`` flag.
        """
        if not media_path:
            return {"success": False, "error": "media_path is required"}

        logger.info("Sending IG media in conversation {}: {}", conv_id, media_path)

        if self.dev_mode:
            conv = self.conversations.get(conv_id)
            if not conv:
                return {"success": False, "error": "Conversation not found"}
            if not os.path.exists(media_path):
                return {"success": False, "error": f"File not found: {media_path}"}
            msg = InstagramMessage(
                conversation_id=conv_id,
                sender=self.username or "dev_user",
                text="[media]",
                media_url=media_path,
                is_outgoing=True,
                is_read=True,
            )
            conv.messages.append(msg)
            conv.last_message_preview = "[media]"
            conv.last_message_at = msg.timestamp
            self.messages_sent_count += 1
            return {"success": True, "message_id": msg.id, "media_path": media_path}

        if not os.path.exists(media_path):
            return {"success": False, "error": f"File not found: {media_path}"}

        # Click the photo/media button in the IG DM interface
        attach_script = '''
        tell application "Safari"
            tell window 1
                tell current tab
                    set jsResult to do JavaScript "
                        (function() {
                            var attachBtn = document.querySelector('[aria-label*=\\"photo\\"], [aria-label*=\\"Add Photo\\"], svg[aria-label*=\\"Photo\\"]');
                            if (attachBtn) {
                                var clickTarget = attachBtn.closest('button') || attachBtn.closest('div[role=\\"button\\"]') || attachBtn;
                                clickTarget.click();
                                return 'clicked';
                            }
                            var fileInput = document.querySelector('input[type=\\"file\\"][accept*=\\"image\\"]');
                            if (fileInput) {
                                fileInput.click();
                                return 'input_clicked';
                            }
                            return 'not_found';
                        })();
                    "
                    return jsResult
                end tell
            end tell
        end tell
        '''
        success, result = self._run_applescript(attach_script)
        if not success or result == "not_found":
            return {"success": False, "error": "Could not find media attachment button"}

        time.sleep(1)

        # Use System Events to interact with the file picker
        abs_path = os.path.abspath(media_path)
        directory = os.path.dirname(abs_path)
        filename = os.path.basename(abs_path)

        file_picker_script = f'''
        tell application "System Events"
            tell process "Safari"
                delay 1
                keystroke "g" using {{command down, shift down}}
                delay 0.5
                keystroke "{directory}"
                delay 0.3
                keystroke return
                delay 1
                keystroke "{filename}"
                delay 0.3
                keystroke return
                delay 1
            end tell
        end tell
        '''
        success, _ = self._run_applescript(file_picker_script)
        if success:
            self.messages_sent_count += 1
            self.last_message_sent_at = datetime.now(timezone.utc)
            logger.info("IG media sent in conversation {}: {}", conv_id, filename)
            time.sleep(2)
            return {"success": True, "conversation_id": conv_id, "media_path": media_path}
        return {"success": False, "error": "Failed to attach media via file picker"}

    def handle_message_requests(self) -> Dict[str, Any]:
        """
        Navigate to and retrieve Instagram message requests.

        Message requests are DMs from users the account does not follow.

        Returns:
            Dict with ``success``, ``count``, and ``requests`` list.
        """
        logger.info("Fetching Instagram message requests")

        if self.dev_mode:
            requests = [c.to_dict() for c in self.message_requests.values()]
            return {
                "success": True,
                "count": len(requests),
                "requests": requests,
            }

        self._navigate_to(self.INSTAGRAM_MESSAGE_REQUESTS_URL)
        time.sleep(3)

        script = '''
        tell application "Safari"
            tell window 1
                tell current tab
                    set jsResult to do JavaScript "
                        (function() {
                            var requests = [];
                            var items = document.querySelectorAll('[role=\\"listitem\\"], [class*=\\"x9f619\\"]');
                            for (var i = 0; i < items.length; i++) {
                                var item = items[i];
                                var nameEl = item.querySelector('span[dir=\\"auto\\"]');
                                var previewEl = item.querySelector('[class*=\\"message\\"], span:nth-child(2)');
                                var timeEl = item.querySelector('time');
                                if (nameEl) {
                                    requests.push({
                                        name: nameEl.innerText,
                                        preview: previewEl ? previewEl.innerText.substring(0, 100) : '',
                                        time: timeEl ? timeEl.getAttribute('datetime') : null
                                    });
                                }
                            }
                            return JSON.stringify(requests);
                        })();
                    "
                    return jsResult
                end tell
            end tell
        end tell
        '''
        success, result = self._run_applescript(script)
        if success and result and result != "dev_mode":
            try:
                requests = json.loads(result)
                return {
                    "success": True,
                    "count": len(requests),
                    "requests": requests,
                }
            except json.JSONDecodeError:
                pass
        return {"success": False, "error": "Failed to fetch message requests"}

    # ------------------------------------------------------------------
    # Stats / helpers
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return current controller statistics."""
        return {
            "platform": "instagram",
            "dev_mode": self.dev_mode,
            "is_authenticated": self.is_authenticated,
            "username": self.username,
            "total_conversations": len(self.conversations),
            "message_requests": len(self.message_requests),
            "messages_sent": self.messages_sent_count,
            "last_message_sent_at": (
                self.last_message_sent_at.isoformat()
                if self.last_message_sent_at
                else None
            ),
        }


# ---------------------------------------------------------------------------
# Module-level singleton accessor
# ---------------------------------------------------------------------------

def get_instagram_dm_controller(dev_mode: bool = False) -> InstagramDMController:
    """Return the singleton ``InstagramDMController`` instance."""
    return InstagramDMController.get_instance(dev_mode=dev_mode)
