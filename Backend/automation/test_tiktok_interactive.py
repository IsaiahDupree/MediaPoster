"""
TikTok Interactive Test Suite
Comprehensive testing of all engagement features, messaging, and data extraction.
Run this to test all TikTok automation capabilities.
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

sys.path.append(str(Path(__file__).parent.parent))

from automation.tiktok_engagement import TikTokEngagement
from automation.safari_app_controller import SafariAppController


class TikTokTestSuite:
    """
    Comprehensive test suite for TikTok automation.
    Tests all engagement buttons, navigation, comments, and messaging.
    """
    
    # Updated selectors based on actual TikTok UI
    SELECTORS = {
        # Video engagement (from screenshot 1)
        "like_button": '[data-e2e="like-icon"], [data-e2e="browse-like-icon"], button[aria-label*="like" i]',
        "like_count": '[data-e2e="like-count"], [data-e2e="browse-like-count"]',
        "comment_button": '[data-e2e="comment-icon"], [data-e2e="browse-comment-icon"], button[aria-label*="comment" i]',
        "comment_count": '[data-e2e="comment-count"]',
        "save_button": '[data-e2e="bookmark-icon"], [data-e2e="collect-icon"], button[aria-label*="save" i]',
        "save_count": '[data-e2e="bookmark-count"]',
        "share_button": '[data-e2e="share-icon"], [data-e2e="browse-share-icon"], button[aria-label*="share" i]',
        "share_count": '[data-e2e="share-count"]',
        "follow_button": '[data-e2e="follow-button"]',
        
        # Video info
        "video_username": '[data-e2e="browse-username"], a[href*="/@"]',
        "video_caption": '[data-e2e="browse-video-desc"], [data-e2e="video-desc"]',
        "video_music": '[data-e2e="video-music"]',
        
        # Comments section (from screenshot 2)
        "comments_panel": '[data-e2e="comment-list"], [class*="DivCommentListContainer"]',
        "comment_items": '[data-e2e="comment-item"], [class*="DivCommentItemContainer"]',
        "comment_username": '[data-e2e="comment-username-1"]',
        "comment_text": '[data-e2e="comment-level-1"]',
        "comment_input": '[data-e2e="comment-input"], [placeholder*="comment" i], textarea',
        "comment_post_button": '[data-e2e="comment-post"], button[type="submit"]',
        "comment_close": 'button[aria-label*="Close" i], [data-e2e="comment-close"]',
        
        # Left sidebar navigation (from screenshot 3)
        "nav_for_you": 'a[href="/foryou"], a[href="/en/"]',
        "nav_shop": 'a[href*="shop"]',
        "nav_explore": 'a[href*="explore"]',
        "nav_following": 'a[href="/following"]',
        "nav_friends": 'a[href*="friends"]',
        "nav_live": 'a[href*="live"]',
        "nav_messages": 'a[href*="messages"], [data-e2e="message-icon"], [href="/messages"]',
        "nav_activity": 'a[href*="activity"]',
        "nav_upload": 'a[href*="upload"]',
        "nav_profile": 'a[href*="profile"], [data-e2e="profile-icon"]',
        
        # Messages page (from screenshot 4)
        "messages_list": '[class*="DivConversationList"]',
        "message_conversation": '[class*="DivConversationItem"]',
        "message_username": '[class*="SpanNickname"]',
        "message_preview": '[class*="SpanLastMessage"]',
        "message_input": '[placeholder*="message" i], [data-e2e="message-input"], input[type="text"]',
        "message_send": '[data-e2e="message-send"], button[type="submit"]',
        "message_content": '[class*="DivMessageContent"]',
    }
    
    def __init__(self):
        self.engagement = TikTokEngagement(browser_type="safari")
        self.safari_controller = SafariAppController()
        self.test_results = {}
        self.collected_data = {}
    
    async def run_js(self, js_code: str) -> str:
        """Execute JavaScript in Safari."""
        try:
            script = f'''
            tell application "Safari"
                tell front window
                    tell current tab
                        do JavaScript "{js_code.replace('"', '\\"').replace(chr(10), ' ')}"
                    end tell
                end tell
            end tell
            '''
            return self.safari_controller._run_applescript(script)
        except Exception as e:
            logger.debug(f"JS error: {e}")
            return ""
    
    async def get_element_text(self, selector: str) -> str:
        """Get text content of an element."""
        js = f"""
        (function() {{
            var selectors = '{selector}'.split(', ');
            for (var i = 0; i < selectors.length; i++) {{
                var el = document.querySelector(selectors[i].trim());
                if (el) return el.textContent.trim();
            }}
            return '';
        }})();
        """
        return await self.run_js(js)
    
    async def get_elements_data(self, selector: str, limit: int = 10) -> List[Dict]:
        """Get data from multiple elements."""
        js = f"""
        (function() {{
            var results = [];
            var els = document.querySelectorAll('{selector}');
            for (var i = 0; i < Math.min(els.length, {limit}); i++) {{
                results.push({{
                    text: els[i].textContent.trim().substring(0, 200),
                    tag: els[i].tagName
                }});
            }}
            return JSON.stringify(results);
        }})();
        """
        result = await self.run_js(js)
        try:
            return json.loads(result)
        except:
            return []
    
    async def click_element(self, selector: str) -> bool:
        """Click an element."""
        js = f"""
        (function() {{
            var selectors = '{selector}'.split(', ');
            for (var i = 0; i < selectors.length; i++) {{
                var el = document.querySelector(selectors[i].trim());
                if (el) {{ el.click(); return 'clicked'; }}
            }}
            return 'not_found';
        }})();
        """
        result = await self.run_js(js)
        return 'clicked' in result.lower()
    
    # ==================== TEST FUNCTIONS ====================
    
    async def test_video_info(self) -> Dict:
        """Extract all video information."""
        logger.info("📹 Testing video info extraction...")
        
        info = {
            "username": await self.get_element_text(self.SELECTORS["video_username"]),
            "caption": await self.get_element_text(self.SELECTORS["video_caption"]),
            "music": await self.get_element_text(self.SELECTORS["video_music"]),
            "likes": await self.get_element_text(self.SELECTORS["like_count"]),
            "comments": await self.get_element_text(self.SELECTORS["comment_count"]),
            "saves": await self.get_element_text(self.SELECTORS["save_count"]),
            "shares": await self.get_element_text(self.SELECTORS["share_count"]),
        }
        
        self.collected_data["current_video"] = info
        logger.info(f"   Username: {info['username']}")
        logger.info(f"   Likes: {info['likes']}")
        logger.info(f"   Comments: {info['comments']}")
        
        return info
    
    async def test_engagement_buttons(self) -> Dict:
        """Test all engagement buttons."""
        logger.info("🎯 Testing engagement buttons...")
        
        results = {
            "like_exists": False,
            "comment_exists": False,
            "save_exists": False,
            "share_exists": False,
            "follow_exists": False
        }
        
        # Check like button
        js = f"document.querySelector('{self.SELECTORS['like_button']}') ? 'found' : 'not_found'"
        results["like_exists"] = 'found' in await self.run_js(js)
        
        # Check comment button
        js = f"document.querySelector('{self.SELECTORS['comment_button']}') ? 'found' : 'not_found'"
        results["comment_exists"] = 'found' in await self.run_js(js)
        
        # Check save button
        js = f"document.querySelector('{self.SELECTORS['save_button']}') ? 'found' : 'not_found'"
        results["save_exists"] = 'found' in await self.run_js(js)
        
        # Check share button
        js = f"document.querySelector('{self.SELECTORS['share_button']}') ? 'found' : 'not_found'"
        results["share_exists"] = 'found' in await self.run_js(js)
        
        # Check follow button
        js = f"document.querySelector('{self.SELECTORS['follow_button']}') ? 'found' : 'not_found'"
        results["follow_exists"] = 'found' in await self.run_js(js)
        
        for btn, exists in results.items():
            status = "✅" if exists else "❌"
            logger.info(f"   {status} {btn}: {exists}")
        
        self.test_results["engagement_buttons"] = results
        return results
    
    async def test_open_comments(self) -> List[Dict]:
        """Open comments and extract comment data."""
        logger.info("💬 Testing comments section...")
        
        # Click comment button
        clicked = await self.click_element(self.SELECTORS["comment_button"])
        if not clicked:
            logger.warning("   Could not click comment button")
            return []
        
        await asyncio.sleep(2)  # Wait for comments to load
        
        # Extract comments
        js = """
        (function() {
            var comments = [];
            var items = document.querySelectorAll('[data-e2e="comment-item"], [class*="DivCommentItem"]');
            for (var i = 0; i < Math.min(items.length, 10); i++) {
                var item = items[i];
                var username = item.querySelector('[data-e2e="comment-username-1"], [class*="SpanUserName"]');
                var text = item.querySelector('[data-e2e="comment-level-1"], [class*="SpanComment"]');
                var likes = item.querySelector('[class*="like-count"], [data-e2e="comment-like-count"]');
                comments.push({
                    username: username ? username.textContent.trim() : '',
                    text: text ? text.textContent.trim().substring(0, 200) : '',
                    likes: likes ? likes.textContent.trim() : '0'
                });
            }
            return JSON.stringify(comments);
        })();
        """
        result = await self.run_js(js)
        
        try:
            comments = json.loads(result)
        except:
            comments = []
        
        self.collected_data["comments"] = comments
        
        logger.info(f"   Found {len(comments)} comments:")
        for c in comments[:5]:
            logger.info(f"      @{c.get('username', '?')}: {c.get('text', '')[:50]}...")
        
        return comments
    
    async def test_navigation_sidebar(self) -> Dict:
        """Test sidebar navigation detection."""
        logger.info("🧭 Testing navigation sidebar...")
        
        nav_items = {
            "for_you": self.SELECTORS["nav_for_you"],
            "shop": self.SELECTORS["nav_shop"],
            "explore": self.SELECTORS["nav_explore"],
            "following": self.SELECTORS["nav_following"],
            "messages": self.SELECTORS["nav_messages"],
            "profile": self.SELECTORS["nav_profile"],
        }
        
        results = {}
        for name, selector in nav_items.items():
            js = f"document.querySelector('{selector}') ? 'found' : 'not_found'"
            results[name] = 'found' in await self.run_js(js)
            status = "✅" if results[name] else "❌"
            logger.info(f"   {status} {name}")
        
        self.test_results["navigation"] = results
        return results
    
    async def navigate_to_messages(self) -> bool:
        """Navigate to the messages page."""
        logger.info("📬 Navigating to messages...")
        
        # Try clicking the messages link
        clicked = await self.click_element(self.SELECTORS["nav_messages"])
        
        if not clicked:
            # Try direct navigation
            script = '''
            tell application "Safari"
                tell front window
                    set URL of current tab to "https://www.tiktok.com/messages"
                end tell
            end tell
            '''
            self.safari_controller._run_applescript(script)
        
        await asyncio.sleep(3)  # Wait for page load
        
        # Verify we're on messages page
        current_url = await self.safari_controller.get_current_url()
        success = 'messages' in current_url.lower()
        
        if success:
            logger.success("   ✅ Now on messages page")
        else:
            logger.warning(f"   ⚠️ Navigation uncertain. URL: {current_url}")
        
        return success
    
    async def get_conversations(self) -> List[Dict]:
        """Get list of message conversations."""
        logger.info("📋 Getting conversations list...")
        
        js = """
        (function() {
            var conversations = [];
            var items = document.querySelectorAll('[class*="DivConversationItem"], [class*="conversation"]');
            if (items.length === 0) {
                items = document.querySelectorAll('li, [role="listitem"]');
            }
            for (var i = 0; i < Math.min(items.length, 15); i++) {
                var item = items[i];
                var text = item.textContent.trim();
                if (text.length > 5 && text.length < 500) {
                    // Try to extract username and preview
                    var lines = text.split('\\n').filter(l => l.trim());
                    conversations.push({
                        raw: text.substring(0, 100),
                        name: lines[0] || '',
                        preview: lines[1] || '',
                        date: lines[2] || ''
                    });
                }
            }
            return JSON.stringify(conversations);
        })();
        """
        result = await self.run_js(js)
        
        try:
            conversations = json.loads(result)
        except:
            conversations = []
        
        self.collected_data["conversations"] = conversations
        
        logger.info(f"   Found {len(conversations)} conversations:")
        for c in conversations[:5]:
            logger.info(f"      {c.get('name', '?')}: {c.get('preview', '')[:40]}...")
        
        return conversations
    
    async def read_messages(self, conversation_index: int = 0) -> List[Dict]:
        """Read messages from a conversation."""
        logger.info(f"📖 Reading messages from conversation {conversation_index}...")
        
        # Click on conversation
        js = f"""
        (function() {{
            var items = document.querySelectorAll('[class*="DivConversationItem"], [class*="conversation"], li');
            if (items.length > {conversation_index}) {{
                items[{conversation_index}].click();
                return 'clicked';
            }}
            return 'not_found';
        }})();
        """
        await self.run_js(js)
        await asyncio.sleep(2)
        
        # Extract messages
        js = """
        (function() {
            var messages = [];
            var items = document.querySelectorAll('[class*="DivMessage"], [class*="message"]');
            for (var i = 0; i < Math.min(items.length, 20); i++) {
                var item = items[i];
                var text = item.textContent.trim();
                if (text.length > 0 && text.length < 1000) {
                    messages.push({
                        text: text,
                        isSent: item.className.includes('sent') || item.className.includes('right')
                    });
                }
            }
            return JSON.stringify(messages);
        })();
        """
        result = await self.run_js(js)
        
        try:
            messages = json.loads(result)
        except:
            messages = []
        
        self.collected_data["messages"] = messages
        
        logger.info(f"   Found {len(messages)} messages")
        for m in messages[:5]:
            direction = "→" if m.get('isSent') else "←"
            logger.info(f"      {direction} {m.get('text', '')[:50]}...")
        
        return messages
    
    async def send_message(self, message: str) -> bool:
        """Send a message in the current conversation."""
        logger.info(f"✉️ Sending message: {message[:30]}...")
        
        # Find and click message input
        clicked = await self.click_element(self.SELECTORS["message_input"])
        if not clicked:
            logger.warning("   Could not find message input")
            return False
        
        await asyncio.sleep(0.5)
        
        # Type message using AppleScript keystroke
        script = f'''
        tell application "System Events"
            tell process "Safari"
                keystroke "{message.replace('"', '\\"')}"
                delay 0.5
                keystroke return
            end tell
        end tell
        '''
        try:
            self.safari_controller._run_applescript(script)
            await asyncio.sleep(1)
            logger.success("   ✅ Message sent!")
            return True
        except Exception as e:
            logger.error(f"   Failed to send message: {e}")
            return False
    
    async def post_comment(self, comment: str) -> bool:
        """Post a comment on the current video."""
        logger.info(f"💬 Posting comment: {comment[:30]}...")
        
        # Make sure comments are open
        await self.click_element(self.SELECTORS["comment_button"])
        await asyncio.sleep(1)
        
        # Find and click comment input
        clicked = await self.click_element(self.SELECTORS["comment_input"])
        if not clicked:
            logger.warning("   Could not find comment input")
            return False
        
        await asyncio.sleep(0.5)
        
        # Type comment
        script = f'''
        tell application "System Events"
            tell process "Safari"
                keystroke "{comment.replace('"', '\\"')}"
            end tell
        end tell
        '''
        try:
            self.safari_controller._run_applescript(script)
            await asyncio.sleep(0.5)
            
            # Click post
            await self.click_element(self.SELECTORS["comment_post_button"])
            await asyncio.sleep(1)
            
            logger.success("   ✅ Comment posted!")
            return True
        except Exception as e:
            logger.error(f"   Failed to post comment: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests and collect results."""
        logger.info("=" * 60)
        logger.info("🧪 TikTok Automation Test Suite")
        logger.info("=" * 60)
        
        # 1. Test video info extraction
        print("\n")
        await self.test_video_info()
        
        # 2. Test engagement buttons
        print("\n")
        await self.test_engagement_buttons()
        
        # 3. Test comments
        print("\n") 
        await self.test_open_comments()
        
        # 4. Test navigation
        print("\n")
        await self.test_navigation_sidebar()
        
        # 5. Navigate to messages
        print("\n")
        await self.navigate_to_messages()
        
        # 6. Get conversations
        print("\n")
        await self.get_conversations()
        
        # 7. Read messages from first conversation
        print("\n")
        await self.read_messages(0)
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary."""
        print("\n")
        logger.info("=" * 60)
        logger.info("📊 TEST SUMMARY")
        logger.info("=" * 60)
        
        # Video info
        video = self.collected_data.get("current_video", {})
        if video:
            logger.info(f"Video: @{video.get('username', '?')} - {video.get('likes', '?')} likes")
        
        # Comments
        comments = self.collected_data.get("comments", [])
        logger.info(f"Comments collected: {len(comments)}")
        
        # Conversations
        convos = self.collected_data.get("conversations", [])
        logger.info(f"Conversations found: {len(convos)}")
        
        # Messages
        messages = self.collected_data.get("messages", [])
        logger.info(f"Messages read: {len(messages)}")
        
        # Buttons
        buttons = self.test_results.get("engagement_buttons", {})
        active = sum(1 for v in buttons.values() if v)
        logger.info(f"Engagement buttons found: {active}/{len(buttons)}")
        
        # Save results
        output_file = Path(__file__).parent / "test_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "collected_data": self.collected_data,
                "test_results": self.test_results
            }, f, indent=2)
        logger.success(f"\n✅ Results saved to: {output_file}")


async def interactive_mode():
    """Interactive mode for testing individual features."""
    print("\n" + "=" * 60)
    print("🎮 TikTok Interactive Testing Mode")
    print("=" * 60)
    
    suite = TikTokTestSuite()
    
    # Launch Safari if not already open
    print("\n📱 Launching Safari (navigate to TikTok if needed)...")
    await suite.safari_controller.launch_safari("https://www.tiktok.com/foryou")
    await asyncio.sleep(3)
    
    while True:
        print("\n🎯 Choose an action:")
        print("  1. Get video info")
        print("  2. Check engagement buttons")
        print("  3. Open & read comments")
        print("  4. Post a comment")
        print("  5. Go to messages")
        print("  6. Get conversations")
        print("  7. Read messages")
        print("  8. Send a message")
        print("  9. Run all tests")
        print("  0. Exit")
        
        try:
            choice = input("\nChoice (0-9): ").strip()
            
            if choice == "0":
                break
            elif choice == "1":
                await suite.test_video_info()
            elif choice == "2":
                await suite.test_engagement_buttons()
            elif choice == "3":
                await suite.test_open_comments()
            elif choice == "4":
                comment = input("Enter comment: ").strip()
                if comment:
                    await suite.post_comment(comment)
            elif choice == "5":
                await suite.navigate_to_messages()
            elif choice == "6":
                await suite.get_conversations()
            elif choice == "7":
                idx = int(input("Conversation index (0-based): ").strip() or "0")
                await suite.read_messages(idx)
            elif choice == "8":
                msg = input("Enter message: ").strip()
                if msg:
                    await suite.send_message(msg)
            elif choice == "9":
                await suite.run_all_tests()
            else:
                print("Invalid choice")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")
    
    print("\n👋 Goodbye!")


if __name__ == "__main__":
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        asyncio.run(TikTokTestSuite().run_all_tests())
    else:
        asyncio.run(interactive_mode())
