"""
Test: Like and Comment on 3 Consecutive Videos from FYP

This test verifies the complete workflow:
1. Navigate to FYP
2. For each of 3 videos:
   - Like the video
   - Post a comment
   - Move to next video
3. Verify all actions succeeded
"""
import pytest
import asyncio
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from automation.tiktok_engagement import TikTokEngagement

# Mark as E2E test (requires browser)
pytestmark = pytest.mark.e2e


class TestFYP3Videos:
    """Test liking and commenting on 3 consecutive videos from FYP."""
    
    @pytest.mark.asyncio
    async def test_like_and_comment_3_videos(self, screenshot):
        """
        E2E: Like and comment on 3 consecutive videos from FYP.
        
        This is the main test that verifies the complete workflow.
        """
        engagement = TikTokEngagement(browser_type="safari")
        results = []
        
        try:
            screenshot.log("="*70)
            screenshot.log("🚀 TEST: Like and Comment on 3 Consecutive Videos from FYP")
            screenshot.log("="*70)
            
            # Step 1: Initialize and navigate to FYP
            screenshot.log("\n📍 STEP 1: INITIALIZATION")
            screenshot.log("-"*70)
            screenshot.log("🔍 Finding Safari window with TikTok...")
            
            await engagement.start("https://www.tiktok.com/foryou", find_existing=True)
            await asyncio.sleep(2)
            screenshot.capture_safari_window("01_initialized")
            
            current_url = await engagement.get_current_url()
            screenshot.log(f"✅ Current URL: {current_url}")
            
            # Check login status
            is_logged_in = await engagement.check_login_status()
            screenshot.log(f"🔐 Login status: {'✅ Logged in' if is_logged_in else '❌ Not logged in'}")
            
            if not is_logged_in:
                screenshot.log("⚠️  WARNING: Not logged in - test may fail")
                pytest.skip("Must be logged in to like and comment")
            
            # Navigate to FYP if needed
            if "/foryou" not in current_url and not current_url.endswith("/en/"):
                screenshot.log("📍 Not on FYP, navigating...")
                await engagement.navigate_to_fyp()
                await asyncio.sleep(3)
                current_url = await engagement.get_current_url()
                screenshot.log(f"✅ Now on: {current_url}")
            
            screenshot.capture_safari_window("02_on_fyp")
            screenshot.log("✅ Ready to start engagement cycle")
            
            # Main engagement loop for 3 videos
            num_videos = 3
            comment_template = "Great content! 🔥"
            
            for i in range(num_videos):
                screenshot.log("\n" + "="*70)
                screenshot.log(f"📹 VIDEO {i+1}/{num_videos}")
                screenshot.log("="*70)
                
                video_result = {
                    "video_number": i + 1,
                    "success": False,
                    "liked": False,
                    "commented": False,
                    "comment_text": "",
                    "error": None,
                    "video_info": {}
                }
                
                try:
                    # Get video info
                    screenshot.log(f"\n   📹 Getting video {i+1} information...")
                    video_info = await engagement.get_current_video_info()
                    video_result["video_info"] = video_info
                    
                    username = video_info.get('username', 'unknown')
                    caption = video_info.get('caption', '')
                    video_id = video_info.get('video_id', 'unknown')
                    
                    screenshot.log(f"   👤 Username: @{username}")
                    screenshot.log(f"   📝 Caption: {caption[:50]}...")
                    screenshot.log(f"   🆔 Video ID: {video_id}")
                    screenshot.capture_safari_window(f"03_video_{i+1}_info")
                    
                    # Like the video
                    screenshot.log(f"\n   ❤️  Liking video {i+1}...")
                    screenshot.capture_safari_window(f"04_video_{i+1}_before_like")
                    
                    like_result = await engagement.like_current_video()
                    video_result["liked"] = like_result
                    await asyncio.sleep(1)
                    
                    if like_result:
                        screenshot.log(f"   ✅ Video {i+1} liked successfully")
                        is_liked = await engagement.is_video_liked()
                        screenshot.log(f"   🔍 Like status verified: {is_liked}")
                    else:
                        screenshot.log(f"   ⚠️  Could not like video {i+1}")
                    
                    screenshot.capture_safari_window(f"05_video_{i+1}_after_like")
                    
                    # Post comment
                    screenshot.log(f"\n   💬 Posting comment on video {i+1}...")
                    timestamp = datetime.now().strftime("%H%M%S")
                    comment_text = f"{comment_template} {timestamp}"
                    video_result["comment_text"] = comment_text
                    
                    screenshot.log(f"   📝 Comment: {comment_text}")
                    screenshot.capture_safari_window(f"06_video_{i+1}_before_comment")
                    
                    comment_result = await engagement.post_comment(
                        comment_text,
                        verify=True,
                        use_extension=True
                    )
                    
                    await asyncio.sleep(2)  # Wait for comment to appear
                    
                    if comment_result.get("success"):
                        video_result["commented"] = True
                        video_result["success"] = True
                        screenshot.log(f"   ✅ Comment posted on video {i+1}")
                        
                        if comment_result.get("verified"):
                            screenshot.log(f"   ✅ Comment verified in comments list")
                        else:
                            screenshot.log(f"   ⚠️  Comment posted but not verified")
                    else:
                        error = comment_result.get("error", "Unknown error")
                        video_result["error"] = error
                        screenshot.log(f"   ❌ Failed to post comment: {error}")
                    
                    screenshot.capture_safari_window(f"07_video_{i+1}_after_comment")
                    
                    # Move to next video (if not last)
                    if i < num_videos - 1:
                        screenshot.log(f"\n   ⏭️  Moving to next video...")
                        screenshot.capture_safari_window(f"08_video_{i+1}_before_next")
                        
                        nav_result = await engagement.go_to_next_video()
                        screenshot.log(f"   📊 Navigation result: {nav_result}")
                        await asyncio.sleep(2)
                        
                        current_url = await engagement.get_current_url()
                        screenshot.log(f"   ✅ Now on: {current_url}")
                        screenshot.capture_safari_window(f"09_video_{i+1}_after_next")
                    
                except Exception as e:
                    screenshot.log(f"   ❌ Error on video {i+1}: {e}")
                    video_result["error"] = str(e)
                    screenshot.capture_safari_window(f"error_video_{i+1}")
                
                results.append(video_result)
                
                # Small delay between videos
                if i < num_videos - 1:
                    await asyncio.sleep(1)
            
            # Summary
            screenshot.log("\n" + "="*70)
            screenshot.log("📊 TEST SUMMARY")
            screenshot.log("="*70)
            
            success_count = sum(1 for r in results if r.get("success"))
            liked_count = sum(1 for r in results if r.get("liked"))
            commented_count = sum(1 for r in results if r.get("commented"))
            
            screenshot.log(f"✅ Successfully engaged: {success_count}/{num_videos}")
            screenshot.log(f"❤️  Videos liked: {liked_count}/{num_videos}")
            screenshot.log(f"💬 Comments posted: {commented_count}/{num_videos}")
            
            screenshot.log("\n📋 Detailed Results:")
            for i, result in enumerate(results, 1):
                status = "✅" if result.get("success") else "❌"
                screenshot.log(f"   Video {i}: {status}")
                screenshot.log(f"      Liked: {result.get('liked', False)}")
                screenshot.log(f"      Commented: {result.get('commented', False)}")
                if result.get("comment_text"):
                    screenshot.log(f"      Comment: {result['comment_text']}")
                if result.get("error"):
                    screenshot.log(f"      Error: {result['error']}")
            
            screenshot.capture_safari_window("10_final_summary")
            
            # CRITICAL Assertions - must verify actual state
            all_likes_verified = all(r.get("like_verified", False) for r in results)
            all_comments_verified = all(r.get("comment_verified", False) for r in results)
            all_usernames_visible = all(r.get("username_visible", False) for r in results)
            
            screenshot.log("\n" + "="*70)
            screenshot.log("🔍 VERIFICATION CHECKS")
            screenshot.log("="*70)
            screenshot.log(f"   All likes verified (actually liked): {'✅' if all_likes_verified else '❌'}")
            screenshot.log(f"   All comments at top: {'✅' if all_comments_verified else '❌'}")
            screenshot.log(f"   All usernames visible: {'✅' if all_usernames_visible else '❌'}")
            
            # Fail if any verification fails
            if not all_likes_verified:
                screenshot.log("   ❌ FAILURE: Some videos are NOT actually liked (like status is unliked)")
                for i, r in enumerate(results, 1):
                    if not r.get("like_verified"):
                        screenshot.log(f"      Video {i}: Like status is unliked")
            
            if not all_comments_verified:
                screenshot.log("   ❌ FAILURE: Some comments are NOT at the top")
                for i, r in enumerate(results, 1):
                    if not r.get("comment_verified"):
                        screenshot.log(f"      Video {i}: Comment not at top")
            
            if not all_usernames_visible:
                screenshot.log("   ❌ FAILURE: Some usernames are NOT displayed at top")
                for i, r in enumerate(results, 1):
                    if not r.get("username_visible"):
                        screenshot.log(f"      Video {i}: Username not visible")
            
            # Assertions - these will fail the test if not met
            assert all_likes_verified, f"FAILURE: Some videos are not actually liked (like status is unliked)"
            assert all_comments_verified, f"FAILURE: Some comments are not at the top of the list"
            assert all_usernames_visible, f"FAILURE: Some usernames are not displayed at the top"
            assert success_count == num_videos, f"Expected {num_videos} successful engagements, got {success_count}"
            
            screenshot.log("\n✅ TEST PASSED: All 3 videos liked and commented successfully!")
            screenshot.log("   ✅ All likes verified (actually liked)")
            screenshot.log("   ✅ All comments at top of list")
            screenshot.log("   ✅ All usernames visible at top")
            
        except Exception as e:
            screenshot.log(f"\n❌ TEST FAILED: {e}")
            screenshot.capture_safari_window("error_final")
            raise
            
        finally:
            await engagement.cleanup()
            screenshot.log("\n🧹 Cleanup complete")
            screenshot.capture_safari_window("11_cleanup")

