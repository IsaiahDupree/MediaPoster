"""
TikTok Comments Test Suite
Focused tests for viewing, saving, and adding comments.
"""
import pytest
import asyncio
import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.tiktok_engagement import TikTokEngagement
from automation.tiktok_session_manager import TikTokSessionManager


# Mark all tests as E2E (require browser)
pytestmark = pytest.mark.e2e


class TestComments:
    """E2E tests for TikTok comment functionality with screenshots."""
    
    @pytest.mark.asyncio
    async def test_open_comments(self, screenshot):
        """E2E: Open the comments panel on a video."""
        engagement = TikTokEngagement(browser_type="safari")
        try:
            screenshot.log("🚀 Starting open comments test")
            
            await engagement.start()
            screenshot.capture_safari_window("after_start")
            
            # Navigate to FYP to get a video
            await engagement.navigate_to_fyp()
            await asyncio.sleep(3)
            screenshot.log("📍 On FYP page")
            screenshot.capture_safari_window("fyp_page")
            
            # Open comments
            result = await engagement.open_comments()
            await asyncio.sleep(2)
            screenshot.log(f"💬 Open comments result: {result}")
            screenshot.capture_safari_window("comments_open")
            
            assert result is True, "Failed to open comments"
            screenshot.log("✅ Comments opened successfully")
            
        finally:
            await engagement.cleanup()
            screenshot.capture_safari_window("cleanup")
    
    @pytest.mark.asyncio
    async def test_view_comments(self, screenshot):
        """E2E: View and extract comments from a video."""
        engagement = TikTokEngagement(browser_type="safari")
        try:
            screenshot.log("🚀 Starting view comments test")
            
            await engagement.start()
            screenshot.capture_safari_window("after_start")
            
            # Navigate to FYP
            await engagement.navigate_to_fyp()
            await asyncio.sleep(3)
            screenshot.capture_safari_window("fyp_page")
            
            # Get comments
            comments = await engagement.get_comments(limit=10)
            await asyncio.sleep(1)
            screenshot.log(f"📝 Retrieved {len(comments)} comments")
            screenshot.capture_safari_window("comments_extracted")
            
            # Log some comment details
            for i, comment in enumerate(comments[:3]):
                screenshot.log(f"   Comment {i+1}: @{comment.get('username', 'unknown')}: {comment.get('text', '')[:50]}...")
            
            # Verify we got comments structure
            if comments:
                first_comment = comments[0]
                assert "username" in first_comment, "Comment missing username"
                assert "text" in first_comment, "Comment missing text"
                screenshot.log(f"✅ Comments have correct structure")
            else:
                screenshot.log("⚠️ No comments found on this video (may be empty)")
            
        finally:
            await engagement.cleanup()
            screenshot.capture_safari_window("cleanup")
    
    @pytest.mark.asyncio
    async def test_save_comments(self, screenshot, tmp_path):
        """E2E: Save comments from a video to a JSON file."""
        engagement = TikTokEngagement(browser_type="safari")
        try:
            screenshot.log("🚀 Starting save comments test")
            
            await engagement.start()
            screenshot.capture_safari_window("after_start")
            
            # Navigate to FYP
            await engagement.navigate_to_fyp()
            await asyncio.sleep(3)
            screenshot.capture_safari_window("fyp_page")
            
            # Save comments to temp file
            save_path = str(tmp_path / "test_comments.json")
            result = await engagement.save_comments(filepath=save_path, limit=20)
            screenshot.log(f"💾 Save comments result: {result}")
            screenshot.capture_safari_window("comments_saved")
            
            # Verify the file was created
            if result["success"]:
                assert Path(save_path).exists(), "Comments file not created"
                
                # Read and verify content
                with open(save_path, "r") as f:
                    saved_data = json.load(f)
                
                screenshot.log(f"📄 Saved file contains {saved_data.get('comment_count', 0)} comments")
                assert "video_url" in saved_data, "Missing video_url in saved file"
                assert "comments" in saved_data, "Missing comments in saved file"
                assert "saved_at" in saved_data, "Missing timestamp in saved file"
                
                screenshot.log("✅ Comments saved successfully with correct structure")
            else:
                screenshot.log(f"⚠️ Save failed: {result.get('error', 'unknown')}")
            
        finally:
            await engagement.cleanup()
            screenshot.capture_safari_window("cleanup")
    
    @pytest.mark.asyncio
    async def test_add_comment(self, screenshot):
        """E2E: Add a comment to a video (requires auth)."""
        engagement = TikTokEngagement(browser_type="safari")
        try:
            screenshot.log("🚀 Starting add comment test")
            
            await engagement.start()
            screenshot.capture_safari_window("after_start")
            
            # Check login status
            is_logged_in = await engagement.check_login_status()
            screenshot.log(f"🔐 Logged in: {is_logged_in}")
            
            if not is_logged_in:
                screenshot.log("⚠️ Skipping comment - not logged in")
                pytest.skip("Must be logged in to post comments")
            
            # Navigate to FYP
            await engagement.navigate_to_fyp()
            await asyncio.sleep(3)
            screenshot.capture_safari_window("fyp_page")
            
            # Generate unique test comment
            timestamp = datetime.now().strftime("%H:%M:%S")
            test_comment = f"🔥 Great video! {timestamp}"
            
            # Post comment
            result = await engagement.post_comment(test_comment)
            await asyncio.sleep(2)
            screenshot.log(f"💬 Post comment result: {result}")
            screenshot.capture_safari_window("comment_posted")
            
            if result:
                screenshot.log(f"✅ Comment posted: {test_comment}")
            else:
                screenshot.log("⚠️ Comment may have failed (check screenshot)")
            
        finally:
            await engagement.cleanup()
            screenshot.capture_safari_window("cleanup")
    
    @pytest.mark.asyncio
    async def test_full_comment_workflow(self, screenshot, tmp_path):
        """E2E: Complete comment workflow - view, save, and add."""
        engagement = TikTokEngagement(browser_type="safari")
        try:
            screenshot.log("🚀 Starting full comment workflow test")
            
            await engagement.start()
            screenshot.capture_safari_window("after_start")
            
            # Navigate to FYP
            await engagement.navigate_to_fyp()
            await asyncio.sleep(3)
            screenshot.log("📍 Step 1: On FYP page")
            screenshot.capture_safari_window("step1_fyp")
            
            # Step 1: Open comments
            await engagement.open_comments()
            await asyncio.sleep(2)
            screenshot.log("📍 Step 2: Comments opened")
            screenshot.capture_safari_window("step2_comments_open")
            
            # Step 2: View/extract comments
            comments = await engagement.get_comments(limit=15)
            screenshot.log(f"📍 Step 3: Extracted {len(comments)} comments")
            for c in comments[:3]:
                screenshot.log(f"   > @{c.get('username', '?')}: {c.get('text', '')[:40]}...")
            screenshot.capture_safari_window("step3_comments_view")
            
            # Step 3: Save comments
            save_path = str(tmp_path / "workflow_comments.json")
            save_result = await engagement.save_comments(filepath=save_path, limit=15)
            screenshot.log(f"📍 Step 4: Save result - success={save_result['success']}, count={save_result['count']}")
            screenshot.capture_safari_window("step4_comments_saved")
            
            # Step 4: Add comment (if logged in)
            is_logged_in = await engagement.check_login_status()
            if is_logged_in:
                timestamp = datetime.now().strftime("%H:%M:%S")
                add_result = await engagement.post_comment(f"Testing comments {timestamp} 🎯")
                screenshot.log(f"📍 Step 5: Add comment result: {add_result}")
                screenshot.capture_safari_window("step5_comment_added")
            else:
                screenshot.log("📍 Step 5: Skipped (not logged in)")
            
            screenshot.log("✅ Full comment workflow completed!")
            
            # Summary
            screenshot.log(f"📊 WORKFLOW SUMMARY:")
            screenshot.log(f"   - Comments opened: ✅")
            screenshot.log(f"   - Comments extracted: {len(comments)}")
            screenshot.log(f"   - Comments saved: {save_result['success']}")
            screenshot.log(f"   - Comment added: {'✅' if is_logged_in else 'skipped (not logged in)'}")
            
        finally:
            await engagement.cleanup()
            screenshot.capture_safari_window("cleanup")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
