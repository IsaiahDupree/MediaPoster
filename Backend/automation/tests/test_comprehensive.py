"""
TikTok Comprehensive Engagement Test
Tests all actions with before/after screenshots for visual proof.
"""
import pytest
import asyncio
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.tiktok_engagement import TikTokEngagement


pytestmark = pytest.mark.e2e


class TestComprehensiveEngagement:
    """Comprehensive E2E tests with before/after screenshots for all actions."""
    
    @pytest.mark.asyncio
    async def test_all_engagement_actions(self, screenshot):
        """
        E2E: Test all engagement actions with before/after screenshots.
        Actions: Like, Save/Bookmark, Share with Copy Link, Comment
        """
        engagement = TikTokEngagement(browser_type="safari")
        try:
            screenshot.log("🚀 Starting comprehensive engagement test")
            
            # Start and navigate to FYP
            await engagement.start()
            await engagement.navigate_to_fyp()
            await asyncio.sleep(3)
            screenshot.log("📍 On For You Page - ready to test actions")
            screenshot.capture_safari_window("01_fyp_ready")
            
            # ============ LIKE TEST ============
            screenshot.log("\n=== TESTING LIKE ===")
            screenshot.capture_safari_window("02_before_like")
            
            like_result = await engagement.like_current_video()
            await asyncio.sleep(1)
            
            screenshot.log(f"❤️ Like result: {like_result}")
            screenshot.capture_safari_window("03_after_like")
            
            # Check like status
            is_liked = await engagement.is_video_liked()
            screenshot.log(f"   Is video liked? {is_liked}")
            
            # ============ SAVE/BOOKMARK TEST ============
            screenshot.log("\n=== TESTING SAVE/BOOKMARK ===")
            screenshot.capture_safari_window("04_before_save")
            
            save_result = await engagement.save_video()
            await asyncio.sleep(1)
            
            screenshot.log(f"🔖 Save result: {save_result}")
            screenshot.capture_safari_window("05_after_save")
            
            # Check save status
            is_saved = await engagement.is_video_saved()
            screenshot.log(f"   Is video saved? {is_saved}")
            
            # ============ SHARE WITH COPY LINK TEST ============
            screenshot.log("\n=== TESTING SHARE + COPY LINK ===")
            screenshot.capture_safari_window("06_before_share")
            
            share_result = await engagement.share_video(copy_link=True)
            await asyncio.sleep(1)
            
            screenshot.log(f"📤 Share result: {share_result}")
            screenshot.log(f"   Link copied: {share_result.get('link_copied', False)}")
            screenshot.capture_safari_window("07_after_share_copy_link")
            
            # Close share menu by clicking elsewhere or pressing escape
            await engagement._run_js("document.body.click();")
            await asyncio.sleep(1)
            
            # ============ COMMENT TEST ============
            screenshot.log("\n=== TESTING COMMENT ===")
            screenshot.capture_safari_window("08_before_comment")
            
            # Open comments first
            await engagement.open_comments()
            await asyncio.sleep(2)
            screenshot.capture_safari_window("09_comments_panel_open")
            
            # Post a unique comment
            timestamp = datetime.now().strftime("%H:%M:%S")
            test_comment = f"🎯 Automated test {timestamp}"
            
            comment_result = await engagement.post_comment(test_comment)
            await asyncio.sleep(2)
            
            screenshot.log(f"💬 Comment result: {comment_result}")
            screenshot.log(f"   Comment text: {test_comment}")
            screenshot.capture_safari_window("10_after_comment_posted")
            
            # ============ SUMMARY ============
            screenshot.log("\n" + "="*50)
            screenshot.log("📊 COMPREHENSIVE TEST SUMMARY")
            screenshot.log("="*50)
            screenshot.log(f"✅ Like: {like_result}")
            screenshot.log(f"✅ Save/Bookmark: {save_result}")
            screenshot.log(f"✅ Share: {share_result.get('shared', False)}")
            screenshot.log(f"✅ Copy Link: {share_result.get('link_copied', False)}")
            screenshot.log(f"✅ Comment: {comment_result}")
            screenshot.log("="*50)
            
            # Final screenshot
            screenshot.capture_safari_window("11_final_state")
            
        finally:
            await engagement.cleanup()
            screenshot.capture_safari_window("12_cleanup")
    
    @pytest.mark.asyncio
    async def test_share_copy_link_only(self, screenshot):
        """E2E: Test share and copy link specifically."""
        engagement = TikTokEngagement(browser_type="safari")
        try:
            screenshot.log("🚀 Testing Share + Copy Link")
            
            await engagement.start()
            await engagement.navigate_to_fyp()
            await asyncio.sleep(3)
            screenshot.capture_safari_window("01_video_ready")
            
            # Before share
            screenshot.log("📸 Before clicking share")
            screenshot.capture_safari_window("02_before_share")
            
            # Share and copy link
            result = await engagement.share_video(copy_link=True)
            await asyncio.sleep(1.5)
            
            screenshot.log(f"📤 Share opened: {result.get('shared')}")
            screenshot.log(f"🔗 Link copied: {result.get('link_copied')}")
            screenshot.log(f"📎 URL: {result.get('url')}")
            
            # After share - showing share menu
            screenshot.capture_safari_window("03_share_menu_open")
            
            screenshot.log("✅ Share + Copy Link test complete")
            
        finally:
            await engagement.cleanup()
    
    @pytest.mark.asyncio
    async def test_save_bookmark(self, screenshot):
        """E2E: Test save/bookmark functionality."""
        engagement = TikTokEngagement(browser_type="safari")
        try:
            screenshot.log("🚀 Testing Save/Bookmark")
            
            await engagement.start()
            await engagement.navigate_to_fyp()
            await asyncio.sleep(3)
            screenshot.capture_safari_window("01_video_ready")
            
            # Check initial state
            initial_saved = await engagement.is_video_saved()
            screenshot.log(f"📌 Initial saved state: {initial_saved}")
            screenshot.capture_safari_window("02_before_save")
            
            # Save the video
            result = await engagement.save_video()
            await asyncio.sleep(1)
            
            screenshot.log(f"🔖 Save result: {result}")
            screenshot.capture_safari_window("03_after_save")
            
            # Check final state
            final_saved = await engagement.is_video_saved()
            screenshot.log(f"📌 Final saved state: {final_saved}")
            
            screenshot.log("✅ Save/Bookmark test complete")
            
        finally:
            await engagement.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
