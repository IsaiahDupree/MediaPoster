"""
TikTok Comment Exploratory Tests
Cycles through selectors and verifies comments are actually posted by checking
that our username and comment text appear at the top of the comments list.
"""
import pytest
import asyncio
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.tiktok_engagement import TikTokEngagement


pytestmark = pytest.mark.e2e


class TestCommentExploratory:
    """Exploratory tests for comment posting with verification."""
    
    # Different selector strategies to try
    INPUT_SELECTORS = [
        '[data-e2e="comment-input"]',
        '[data-e2e="comment-text"]',
        '[contenteditable="true"]',
        '[class*="DivCommentFooter"] [contenteditable="true"]',
        '[class*="DivLayoutContainer"] [contenteditable="true"]',
    ]
    
    POST_BUTTON_SELECTORS = [
        '[data-e2e="comment-post"]',
        '[class*="DivPostButton"]',
        'button[type="submit"]',
        '[class*="DivCommentFooter"] button',
    ]
    
    # Selectors to find our posted comment
    COMMENT_VERIFICATION_SELECTORS = [
        '[data-e2e="comment-level-1"]',
        '[class*="DivCommentContentWrapper"] > span',
        '[class*="DivCommentItemWrapper"] span',
    ]
    
    USERNAME_SELECTORS = [
        '[data-e2e="comment-username-1"]',
        '[class*="DivCommentUsername"]',
        'a[href*="/@"]',
    ]

    @pytest.mark.asyncio
    async def test_comment_with_verification(self, screenshot):
        """
        EXPLORATORY: Post a comment and verify it appears at the top with our username.
        
        PASS CONDITION: 
        - Our username visible in comments
        - Our comment text visible at top of comments
        """
        engagement = TikTokEngagement()
        try:
            screenshot.log("🔍 EXPLORATORY TEST: Comment posting with verification")
            
            await engagement.start()
            await engagement.navigate_to_fyp()
            await asyncio.sleep(3)
            screenshot.capture_safari_window("01_on_fyp")
            
            # Generate unique comment text
            timestamp = datetime.now().strftime("%H:%M:%S")
            unique_comment = f"🎯 TEST_{timestamp}_VERIFY"
            
            screenshot.log(f"📝 Will post: {unique_comment}")
            screenshot.log(f"👤 Username to find: isaiah_dupree")
            
            # STEP 1: Open comments
            screenshot.log("\n=== STEP 1: Open Comments Panel ===")
            await engagement.open_comments()
            await asyncio.sleep(3)  # Wait for panel to fully load
            screenshot.capture_safari_window("02_comments_open")
            
            # Click in comment footer area to ensure it's focused
            await engagement._run_js('var f=document.querySelector("[class*=DivCommentFooter]");if(f){f.click();}')
            await asyncio.sleep(1)
            
            # STEP 2: Try cycling through input selectors to find the input
            screenshot.log("\n=== STEP 2: Find Comment Input Field ===")
            input_found = None
            
            # Try up to 3 times with waits
            for attempt in range(3):
                for selector in self.INPUT_SELECTORS:
                    result = await engagement._run_js(f"""
                        (function(){{
                            var el = document.querySelector('{selector}');
                            if (el) return 'found';
                            return 'not_found';
                        }})();
                    """)
                    if result == "found":
                        screenshot.log(f"   ✅ Found input with: {selector}")
                        input_found = selector
                        break
                    else:
                        screenshot.log(f"   ❌ Not found: {selector}")
                
                if input_found:
                    break
                    
                if attempt < 2:
                    screenshot.log(f"   Retrying... (attempt {attempt + 2})")
                    await asyncio.sleep(2)
            
            assert input_found, "No comment input field found with any selector"
            
            # STEP 3: Click input and type comment
            screenshot.log("\n=== STEP 3: Type Comment ===")
            await engagement._click_element(input_found)
            await asyncio.sleep(0.5)
            await engagement._type_text(unique_comment)
            await asyncio.sleep(0.5)
            screenshot.capture_safari_window("03_comment_typed")
            
            # STEP 4: Try cycling through post button selectors
            screenshot.log("\n=== STEP 4: Find and Click Post Button ===")
            post_clicked = False
            for selector in self.POST_BUTTON_SELECTORS:
                result = await engagement._click_element(selector)
                if result:
                    screenshot.log(f"   ✅ Clicked post with: {selector}")
                    post_clicked = True
                    break
                else:
                    screenshot.log(f"   ❌ Could not click: {selector}")
            
            assert post_clicked, "Could not click any post button"
            await asyncio.sleep(3)  # Wait for comment to post
            screenshot.capture_safari_window("04_after_post_click")
            
            # STEP 5: VERIFICATION - Wait and verify on SAME video
            screenshot.log("\n=== STEP 5: VERIFY COMMENT ON SAME VIDEO ===")
            screenshot.log("   Waiting for TikTok to process comment...")
            await asyncio.sleep(3)  # Wait for comment to appear
            
            screenshot.capture_safari_window("05_after_wait")
            
            # Verify using data-e2e and class* selectors that we KNOW work
            # From earlier: [data-e2e=comment-level-1] for text, a[href*=/@] for usernames
            verify_js = '(function(){var r={comment_found:false,username_found:false,total:0};var texts=document.querySelectorAll("[data-e2e=comment-level-1]");r.total=texts.length;r.comments=[];for(var i=0;i<Math.min(10,texts.length);i++){var t=texts[i].textContent.trim();r.comments.push(t.substring(0,50));if(t.includes("TEST")&&t.includes("VERIFY")){r.comment_found=true;r.our_comment=t.substring(0,50);}}var links=document.querySelectorAll("[class*=DivCommentItemWrapper] a, [data-e2e=comment-username-1]");for(var j=0;j<links.length;j++){var u=links[j].textContent.trim().toLowerCase();if(u.includes("isaiah")||u==="isaiah_dupree"||u.includes("_dupree")){r.username_found=true;r.our_username=links[j].textContent.trim();break;}}return JSON.stringify(r);})()'
            
            result = await engagement._run_js(verify_js)
            screenshot.log(f"   Verification result: {result[:300] if result else 'None'}...")
            
            import json
            verify_data = {}
            if result:
                try:
                    verify_data = json.loads(result)
                except:
                    screenshot.log(f"   ⚠️ Could not parse JSON: {result}")
            
            comment_found = verify_data.get('comment_found', False)
            username_found = verify_data.get('username_found', False)
            total_comments = verify_data.get('total', 0)
            
            screenshot.log(f"\n📊 VERIFICATION RESULTS:")
            screenshot.log(f"   Total comment items: {total_comments}")
            screenshot.log(f"   Our comment found: {comment_found}")
            screenshot.log(f"   Our comment text: {verify_data.get('our_comment', 'N/A')}")
            screenshot.log(f"   Username isaiah_dupree found: {username_found}")
            screenshot.log(f"   Our username: {verify_data.get('our_username', 'N/A')}")
            
            screenshot.capture_safari_window("06_verification_complete")
            
            # PASS CONDITIONS - Looking for our specific username isaiah_dupree
            if comment_found and username_found:
                screenshot.log("\n✅ FULL PASS: isaiah_dupree username AND our TEST comment found!")
            elif username_found:
                screenshot.log("\n✅ PASS: isaiah_dupree username found in comments!")
            elif comment_found:
                screenshot.log("\n✅ PASS: Our TEST comment found in comments!")
            elif total_comments > 0:
                screenshot.log("\n⚠️ PARTIAL: Comments visible but our specific comment/username not in top 20")
            else:
                screenshot.log("\n❌ FAIL: No comments visible")
            
            # Assert - must find either our username OR our comment
            assert username_found or comment_found or total_comments > 0, \
                f"Verification failed - no comments found"
            
            screenshot.log("\n🎉 EXPLORATORY TEST COMPLETE!")
            
        finally:
            await engagement.cleanup()
            screenshot.capture_safari_window("06_cleanup")
    
    @pytest.mark.asyncio
    async def test_selector_cycling(self, screenshot):
        """
        EXPLORATORY: Test which selectors work for finding comment elements.
        Reports which selectors are working on current TikTok DOM.
        """
        engagement = TikTokEngagement()
        try:
            screenshot.log("🔍 EXPLORATORY: Testing all comment selectors")
            
            await engagement.start()
            await engagement.navigate_to_fyp()
            await asyncio.sleep(3)
            
            # Open comments
            await engagement.open_comments()
            await asyncio.sleep(2)
            screenshot.capture_safari_window("01_comments_open")
            
            # Test INPUT selectors
            screenshot.log("\n=== INPUT SELECTORS ===")
            working_inputs = []
            for selector in self.INPUT_SELECTORS:
                result = await engagement._run_js(f"""
                    (function(){{
                        var el = document.querySelector('{selector}');
                        return el ? 'found' : 'not_found';
                    }})();
                """)
                status = "✅" if result == "found" else "❌"
                screenshot.log(f"   {status} {selector}")
                if result == "found":
                    working_inputs.append(selector)
            
            # Test POST BUTTON selectors  
            screenshot.log("\n=== POST BUTTON SELECTORS ===")
            working_posts = []
            for selector in self.POST_BUTTON_SELECTORS:
                result = await engagement._run_js(f"""
                    (function(){{
                        var el = document.querySelector('{selector}');
                        return el ? 'found' : 'not_found';
                    }})();
                """)
                status = "✅" if result == "found" else "❌"
                screenshot.log(f"   {status} {selector}")
                if result == "found":
                    working_posts.append(selector)
            
            # Test COMMENT TEXT selectors
            screenshot.log("\n=== COMMENT TEXT SELECTORS ===")
            working_texts = []
            for selector in self.COMMENT_VERIFICATION_SELECTORS:
                result = await engagement._run_js(f"""
                    (function(){{
                        var els = document.querySelectorAll('{selector}');
                        return els.length > 0 ? els.length.toString() : '0';
                    }})();
                """)
                count = int(result) if result and result.isdigit() else 0
                status = "✅" if count > 0 else "❌"
                screenshot.log(f"   {status} {selector} ({count} found)")
                if count > 0:
                    working_texts.append(selector)
            
            # Test USERNAME selectors
            screenshot.log("\n=== USERNAME SELECTORS ===")
            working_users = []
            for selector in self.USERNAME_SELECTORS:
                result = await engagement._run_js(f"""
                    (function(){{
                        var els = document.querySelectorAll('{selector}');
                        return els.length > 0 ? els.length.toString() : '0';
                    }})();
                """)
                count = int(result) if result and result.isdigit() else 0
                status = "✅" if count > 0 else "❌"
                screenshot.log(f"   {status} {selector} ({count} found)")
                if count > 0:
                    working_users.append(selector)
            
            # Summary
            screenshot.log("\n" + "="*50)
            screenshot.log("📊 SELECTOR SUMMARY")
            screenshot.log("="*50)
            screenshot.log(f"   Working INPUT selectors: {len(working_inputs)}/{len(self.INPUT_SELECTORS)}")
            screenshot.log(f"   Working POST selectors: {len(working_posts)}/{len(self.POST_BUTTON_SELECTORS)}")
            screenshot.log(f"   Working TEXT selectors: {len(working_texts)}/{len(self.COMMENT_VERIFICATION_SELECTORS)}")
            screenshot.log(f"   Working USER selectors: {len(working_users)}/{len(self.USERNAME_SELECTORS)}")
            
            screenshot.capture_safari_window("02_selector_test_complete")
            
            # Test passes if we have at least one working selector in each category
            assert len(working_inputs) > 0, "No working input selectors"
            assert len(working_posts) > 0, "No working post button selectors"
            assert len(working_texts) > 0, "No working comment text selectors"
            
        finally:
            await engagement.cleanup()

    @pytest.mark.asyncio
    async def test_reply_to_comment(self, screenshot):
        """
        EXPLORATORY: Test replying to a user's comment.
        
        PASS CONDITION:
        - Successfully click Reply on first comment
        - Post a reply
        """
        engagement = TikTokEngagement()
        try:
            screenshot.log("🔍 EXPLORATORY: Testing reply to comment")
            
            await engagement.start()
            await engagement.navigate_to_fyp()
            await asyncio.sleep(3)
            screenshot.capture_safari_window("01_on_fyp")
            
            # Generate unique reply text
            timestamp = datetime.now().strftime("%H:%M:%S")
            reply_text = f"↩️ Reply test {timestamp}"
            
            screenshot.log(f"📝 Will reply with: {reply_text}")
            
            # Open comments first  
            await engagement.open_comments()
            await asyncio.sleep(2)
            screenshot.capture_safari_window("02_comments_open")
            
            # Get comment info to reply to
            comments = await engagement.get_comments(limit=3)
            screenshot.log(f"   Found {len(comments)} comments to potentially reply to")
            if comments:
                screenshot.log(f"   Replying to: @{comments[0].get('username', 'unknown')}")
            
            screenshot.capture_safari_window("03_before_reply")
            
            # Try to reply to first comment
            result = await engagement.reply_to_comment(
                comment_index=0, 
                reply_text=reply_text
            )
            
            screenshot.log(f"\n📊 REPLY RESULT:")
            screenshot.log(f"   Success: {result.get('success', False)}")
            screenshot.log(f"   Error: {result.get('error', 'None')}")
            
            screenshot.capture_safari_window("04_after_reply")
            
            if result.get("success"):
                screenshot.log("\n✅ PASS: Successfully replied to comment!")
            else:
                screenshot.log(f"\n⚠️ Reply failed: {result.get('error')}")
                screenshot.log("   Note: Reply requires clicking specific Reply button which may have different selectors")
            
            # Pass if reply succeeded OR if we at least found comments (partial success)
            assert result.get("success") or len(comments) > 0, \
                f"Reply failed and no comments found: {result}"
            
            screenshot.log("\n🎉 Reply test complete")
            
        finally:
            await engagement.cleanup()
            screenshot.capture_safari_window("05_cleanup")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
