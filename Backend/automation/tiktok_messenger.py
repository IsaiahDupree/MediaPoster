"""
TikTok Messenger - Browser automation for direct messages.

Usage:
    from automation.tiktok_messenger import TikTokMessenger
    
    messenger = TikTokMessenger(safari_controller)
    messenger.open_inbox()
    messenger.send_message("username", "Hello!")
"""

import time
import pyautogui
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    """Represents a TikTok DM message."""
    sender: str
    text: str
    timestamp: str
    is_self: bool = False


@dataclass  
class Conversation:
    """Represents a DM conversation."""
    username: str
    last_message: str
    timestamp: str
    unread: bool = False


class TikTokMessenger:
    """
    Browser automation for TikTok direct messages.
    
    Requires:
    - Safari controller with run_js capability
    - TikTok account logged in
    - PyAutoGUI permissions
    """
    
    # Selectors for DM interface (discovered via browser inspection)
    SELECTORS = {
        # Navigation
        "messages_icon": '[data-e2e="message-icon"]',
        "messages_link": 'a[href*="/messages"]',
        
        # Inbox
        "conversation_list": '[class*="DivConversationListContainer"]',
        "conversation_item": '[class*="DivConversationItem"]',
        "conversation_username": '[class*="PUsername"]',
        "unread_badge": '[class*="DivUnreadBadge"]',
        
        # Chat window
        "message_input": '[class*="DivInputContainer"] [contenteditable="true"]',
        "message_input_alt": '[data-e2e="message-input"]',
        "send_button": '[class*="DivSendButton"]',
        "send_button_alt": '[data-e2e="send-message-btn"]',
        
        # Messages
        "message_list": '[class*="DivMessageList"]',
        "message_item": '[class*="DivMessageItem"]',
        "message_text": '[class*="PMessageText"]',
        "message_time": '[class*="SpanMessageTime"]',
        
        # New message
        "new_message_btn": '[class*="DivNewMessageButton"]',
        "user_search_input": '[class*="InputSearch"]',
        "user_search_result": '[class*="DivSearchResult"]',
    }
    
    def __init__(self, safari_controller):
        """
        Initialize messenger with Safari controller.
        
        Args:
            safari_controller: SafariController instance with run_js method
        """
        self.safari = safari_controller
        self.current_conversation: Optional[str] = None
    
    def open_inbox(self) -> bool:
        """
        Navigate to messages inbox.
        
        Returns:
            True if inbox opened successfully
        """
        # Try clicking messages icon first
        result = self.safari.run_js(f"""
            var icon = document.querySelector('{self.SELECTORS["messages_icon"]}');
            if (icon) {{ icon.click(); return 'CLICKED_ICON'; }}
            
            var link = document.querySelector('{self.SELECTORS["messages_link"]}');
            if (link) {{ link.click(); return 'CLICKED_LINK'; }}
            
            return 'NOT_FOUND';
        """)
        
        if 'NOT_FOUND' in result:
            # Navigate directly
            self.safari.navigate("https://www.tiktok.com/messages")
        
        time.sleep(2)
        
        # Verify inbox loaded
        check = self.safari.run_js(f"""
            var list = document.querySelector('{self.SELECTORS["conversation_list"]}');
            var input = document.querySelector('{self.SELECTORS["message_input"]}');
            return (list || input) ? 'INBOX_LOADED' : 'NOT_LOADED';
        """)
        
        return 'LOADED' in check
    
    def get_conversations(self) -> List[Conversation]:
        """
        Get list of conversations from inbox.
        
        Returns:
            List of Conversation objects
        """
        result = self.safari.run_js("""
            var conversations = [];
            var items = document.querySelectorAll('[class*="DivConversationItem"], [class*="ConversationListItem"]');
            
            items.forEach(function(item) {
                var username = item.querySelector('[class*="Username"], [class*="PName"]');
                var lastMsg = item.querySelector('[class*="LastMessage"], [class*="PPreview"]');
                var time = item.querySelector('[class*="Time"], [class*="SpanTime"]');
                var unread = item.querySelector('[class*="Unread"], [class*="Badge"]');
                
                conversations.push({
                    username: username ? username.innerText.trim() : 'Unknown',
                    last_message: lastMsg ? lastMsg.innerText.trim() : '',
                    timestamp: time ? time.innerText.trim() : '',
                    unread: !!unread
                });
            });
            
            return JSON.stringify(conversations);
        """)
        
        try:
            import json
            data = json.loads(result)
            return [Conversation(**c) for c in data]
        except:
            return []
    
    def open_conversation(self, username: str) -> bool:
        """
        Open conversation with a specific user.
        
        Args:
            username: TikTok username (without @)
            
        Returns:
            True if conversation opened
        """
        # Search for user in conversation list
        result = self.safari.run_js(f"""
            var items = document.querySelectorAll('[class*="DivConversationItem"], [class*="ConversationListItem"]');
            
            for (var i = 0; i < items.length; i++) {{
                var text = items[i].innerText.toLowerCase();
                if (text.includes('{username.lower()}')) {{
                    items[i].click();
                    return 'FOUND_AND_CLICKED';
                }}
            }}
            
            return 'NOT_FOUND';
        """)
        
        if 'FOUND' in result:
            time.sleep(1)
            self.current_conversation = username
            return True
        
        return False
    
    def start_new_conversation(self, username: str) -> bool:
        """
        Start a new conversation with a user.
        
        Args:
            username: TikTok username to message
            
        Returns:
            True if conversation started
        """
        # Click new message button
        self.safari.run_js(f"""
            var btn = document.querySelector('{self.SELECTORS["new_message_btn"]}');
            if (!btn) btn = document.querySelector('[class*="NewMessage"], [aria-label*="New message"]');
            if (btn) btn.click();
        """)
        
        time.sleep(1)
        
        # Search for user
        search_result = self.safari.run_js(f"""
            var input = document.querySelector('{self.SELECTORS["user_search_input"]}');
            if (!input) input = document.querySelector('input[placeholder*="Search"]');
            if (input) {{
                input.focus();
                input.value = '{username}';
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return 'SEARCHING';
            }}
            return 'NO_INPUT';
        """)
        
        if 'SEARCHING' not in search_result:
            return False
        
        time.sleep(2)  # Wait for search results
        
        # Click on user result
        result = self.safari.run_js(f"""
            var results = document.querySelectorAll('{self.SELECTORS["user_search_result"]}');
            if (!results.length) results = document.querySelectorAll('[class*="SearchResult"], [class*="UserItem"]');
            
            for (var i = 0; i < results.length; i++) {{
                if (results[i].innerText.toLowerCase().includes('{username.lower()}')) {{
                    results[i].click();
                    return 'SELECTED';
                }}
            }}
            
            return 'NOT_FOUND';
        """)
        
        if 'SELECTED' in result:
            time.sleep(1)
            self.current_conversation = username
            return True
        
        return False
    
    def send_message(self, text: str) -> bool:
        """
        Send a message in the current conversation.
        
        Args:
            text: Message text to send
            
        Returns:
            True if message sent
        """
        if not self.current_conversation:
            print("No conversation open")
            return False
        
        # Focus message input
        focus_result = self.safari.run_js(f"""
            var input = document.querySelector('{self.SELECTORS["message_input"]}');
            if (!input) input = document.querySelector('{self.SELECTORS["message_input_alt"]}');
            if (!input) input = document.querySelector('[contenteditable="true"]');
            
            if (input) {{
                input.focus();
                input.click();
                return 'FOCUSED';
            }}
            return 'NO_INPUT';
        """)
        
        if 'FOCUSED' not in focus_result:
            print("Could not find message input")
            return False
        
        time.sleep(0.3)
        
        # Type message using PyAutoGUI (more reliable than JS for contenteditable)
        pyautogui.typewrite(text, interval=0.02)
        time.sleep(0.5)
        
        # Click send button
        send_result = self.safari.run_js(f"""
            var btn = document.querySelector('{self.SELECTORS["send_button"]}');
            if (!btn) btn = document.querySelector('{self.SELECTORS["send_button_alt"]}');
            if (!btn) btn = document.querySelector('[aria-label*="Send"]');
            
            if (btn) {{
                btn.click();
                return 'SENT';
            }}
            
            return 'NO_BUTTON';
        """)
        
        if 'SENT' in send_result:
            time.sleep(1)
            return True
        
        # Fallback: try Enter key
        pyautogui.press('return')
        time.sleep(1)
        return True
    
    def get_messages(self, limit: int = 50) -> List[Message]:
        """
        Get messages from current conversation.
        
        Args:
            limit: Maximum messages to retrieve
            
        Returns:
            List of Message objects
        """
        result = self.safari.run_js(f"""
            var messages = [];
            var items = document.querySelectorAll('[class*="DivMessageItem"], [class*="MessageBubble"]');
            
            var count = Math.min(items.length, {limit});
            for (var i = 0; i < count; i++) {{
                var item = items[i];
                var text = item.querySelector('[class*="MessageText"], [class*="PText"]');
                var time = item.querySelector('[class*="Time"], [class*="SpanTime"]');
                var isSelf = item.className.includes('Self') || item.className.includes('Sent');
                
                messages.push({{
                    sender: isSelf ? 'self' : 'other',
                    text: text ? text.innerText.trim() : '',
                    timestamp: time ? time.innerText.trim() : '',
                    is_self: isSelf
                }});
            }}
            
            return JSON.stringify(messages);
        """)
        
        try:
            import json
            data = json.loads(result)
            return [Message(**m) for m in data]
        except:
            return []
    
    def send_to_user(self, username: str, text: str) -> bool:
        """
        Convenience method: open inbox, find/start conversation, send message.
        
        Args:
            username: TikTok username to message
            text: Message text
            
        Returns:
            True if message sent successfully
        """
        # Open inbox
        if not self.open_inbox():
            print("Failed to open inbox")
            return False
        
        # Try to open existing conversation
        if not self.open_conversation(username):
            # Start new conversation
            if not self.start_new_conversation(username):
                print(f"Could not find or start conversation with {username}")
                return False
        
        # Send message
        return self.send_message(text)


def discover_dm_selectors(safari_controller) -> Dict[str, str]:
    """
    Discover DM interface selectors by inspecting the page.
    Run this with Safari on /messages page to find current selectors.
    """
    safari_controller.navigate("https://www.tiktok.com/messages")
    time.sleep(3)
    
    result = safari_controller.run_js("""
        var selectors = {};
        
        // Find all elements with common DM-related class patterns
        var patterns = ['Message', 'Conversation', 'Chat', 'Input', 'Send', 'Inbox'];
        
        patterns.forEach(function(pattern) {
            var elements = document.querySelectorAll('[class*="' + pattern + '"]');
            elements.forEach(function(el) {
                var key = pattern + '_' + el.tagName;
                if (!selectors[key]) {
                    selectors[key] = {
                        tag: el.tagName,
                        classes: el.className.split(' ').filter(c => c.includes(pattern))[0] || '',
                        sample: el.innerText ? el.innerText.substring(0, 30) : ''
                    };
                }
            });
        });
        
        return JSON.stringify(selectors, null, 2);
    """)
    
    print("Discovered DM Selectors:")
    print(result)
    return result
