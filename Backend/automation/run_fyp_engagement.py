#!/usr/bin/env python3
"""
TikTok FYP Engagement Script
Like and comment on 3 videos in a row from the For You Page.

This script:
1. Navigates to FYP
2. For each of 3 videos:
   - Likes the video
   - Posts a comment
   - Moves to the next video
3. Uses Safari extension if available, falls back to pyautogui
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Try to import loguru, fall back to print if not available
try:
    from loguru import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    logger = logging.getLogger(__name__)
    # Create simple logger interface
    class SimpleLogger:
        def info(self, msg): print(f"ℹ️  {msg}")
        def warning(self, msg): print(f"⚠️  {msg}")
        def error(self, msg): print(f"❌ {msg}")
        def success(self, msg): print(f"✅ {msg}")
        def debug(self, msg): pass
    logger = SimpleLogger()

from automation.tiktok_engagement import TikTokEngagement


async def engage_with_fyp_videos(
    num_videos: int = 3,
    comment_template: str = "Great content! 🔥",
    use_extension: bool = True
) -> List[Dict]:
    """
    Like and comment on multiple videos from the FYP.
    
    Args:
        num_videos: Number of videos to engage with
        comment_template: Comment text template (timestamp will be added)
        use_extension: If True, prefer Safari extension for typing
        
    Returns:
        List of results for each video
    """
    engagement = TikTokEngagement()
    results = []
    
    try:
        logger.info("🚀 Starting FYP engagement automation")
        logger.info(f"   Videos: {num_videos}")
        logger.info(f"   Comment template: {comment_template}")
        
        # Step 1: Start and find existing TikTok session
        logger.info("\n" + "="*60)
        logger.info("📍 STEP 1: INITIALIZATION")
        logger.info("="*60)
        logger.info("🔍 Looking for Safari window with TikTok...")
        await engagement.start("https://www.tiktok.com/foryou", find_existing=True)
        await asyncio.sleep(2)  # Wait for page to load
        
        # Verify we're on TikTok
        current_url = await engagement.get_current_url()
        logger.info(f"   ✅ Current URL: {current_url}")
        logger.info(f"   📊 URL length: {len(current_url)} characters")
        
        # Check login status
        logger.info("\n   🔐 Checking login status...")
        is_logged_in = await engagement.check_login_status()
        if is_logged_in:
            logger.info("   ✅ User is logged in - all actions available")
        else:
            logger.warning("   ⚠️  Not logged in - some actions may fail")
            logger.info("   💡 Please log in manually in Safari and run again")
            logger.info("   💡 Or the script will try to navigate to FYP anyway...")
        
        # Navigate to FYP if not already there
        logger.info("\n   🧭 Checking if on FYP...")
        if "/foryou" not in current_url and not current_url.endswith("/en/"):
            logger.info("   ⚠️  Not on FYP, navigating...")
            logger.info("   📍 Navigating to For You Page...")
            nav_result = await engagement.navigate_to_fyp()
            logger.info(f"   📊 Navigation result: {nav_result}")
            await asyncio.sleep(3)
            current_url = await engagement.get_current_url()
            logger.info(f"   ✅ Now on: {current_url}")
        else:
            logger.info("   ✅ Already on FYP - ready to proceed")
        
        logger.info("\n" + "="*60)
        logger.info("✅ INITIALIZATION COMPLETE")
        logger.info("="*60)
        
        # Main engagement loop
        for i in range(num_videos):
            logger.info(f"\n{'='*60}")
            logger.info(f"📹 VIDEO {i+1}/{num_videos}")
            logger.info(f"{'='*60}")
            
            video_result = {
                "video_number": i + 1,
                "success": False,
                "liked": False,
                "commented": False,
                "comment_text": "",
                "error": None,
                "like_verified": False,
                "comment_verified": False,
                "username_visible": False
            }
            
            try:
                # Get current video info
                logger.info("\n   📹 Getting video information...")
                video_info = await engagement.get_current_video_info()
                username = video_info.get('username', 'unknown')
                caption = video_info.get('caption', '')
                video_id = video_info.get('video_id', 'unknown')
                like_count = video_info.get('like_count', 'unknown')
                
                logger.info(f"   👤 Username: @{username}")
                logger.info(f"   📝 Caption: {caption[:60]}{'...' if len(caption) > 60 else ''}")
                logger.info(f"   🆔 Video ID: {video_id}")
                logger.info(f"   ❤️  Like count: {like_count}")
                
                # Step 2: Like the video
                logger.info("\n   " + "-"*50)
                logger.info("   ❤️  STEP 2: LIKING VIDEO")
                logger.info("   " + "-"*50)
                logger.info("   🖱️  Clicking like button...")
                like_result = await engagement.like_current_video()
                video_result["liked"] = like_result
                
                if like_result:
                    logger.info("   ✅ Like button clicked")
                    # CRITICAL: Verify like status is actually "liked"
                    await asyncio.sleep(1)  # Wait for state to update
                    is_liked = await engagement.is_video_liked()
                    logger.info(f"   🔍 Like status verified: {is_liked}")
                    
                    if not is_liked:
                        logger.error("   ❌ FAILURE: Video is NOT liked - like action failed!")
                        video_result["error"] = "Like status is unliked"
                        video_result["liked"] = False
                        video_result["like_verified"] = False
                    else:
                        logger.info("   ✅ Video is confirmed LIKED")
                        video_result["liked"] = True
                        video_result["like_verified"] = True
                    
                    await asyncio.sleep(1)  # Small delay between actions
                else:
                    logger.warning("   ⚠️  Could not like video - button may not be clickable")
                    video_result["error"] = "Could not click like button"
                
                # Step 3: Post a comment
                logger.info("\n   " + "-"*50)
                logger.info("   💬 STEP 3: POSTING COMMENT")
                logger.info("   " + "-"*50)
                
                # Generate unique comment with timestamp
                timestamp = datetime.now().strftime("%H%M%S")
                comment_text = f"{comment_template} {timestamp}"
                video_result["comment_text"] = comment_text
                
                logger.info(f"   📝 Comment text: {comment_text}")
                logger.info(f"   🔧 Using extension: {use_extension}")
                logger.info("   🖱️  Opening comments panel...")
                
                comment_result = await engagement.post_comment(
                    comment_text,
                    verify=True,
                    use_extension=use_extension
                )
                
                logger.info(f"   📊 Comment result: {comment_result.get('success', False)}")
                logger.info(f"   📊 Method used: {comment_result.get('method', 'unknown')}")
                
                if comment_result.get("success"):
                    logger.info(f"   ✅ Comment posted successfully!")
                    logger.info(f"   📝 Posted text: {comment_text}")
                    
                    # CRITICAL: Verify comment is at top and username is visible
                    logger.info("   🔍 Verifying comment at top of list...")
                    await asyncio.sleep(2)  # Wait for comment to appear
                    
                    # Get current username for verification
                    current_username = video_info.get('username', '')
                    if not current_username or current_username == 'unknown':
                        # Try to get logged-in username
                        try:
                            username_js = """
                            (function() {
                                var profile = document.querySelector('[data-e2e="profile-icon"]');
                                if (profile) {
                                    var link = profile.closest('a[href*="/@"]');
                                    if (link) {
                                        var href = link.getAttribute('href') || '';
                                        var match = href.match(/@([^/]+)/);
                                        return match ? match[1] : '';
                                    }
                                }
                                return '';
                            })();
                            """
                            username_result = await engagement._run_js(username_js)
                            if username_result and username_result != '""':
                                current_username = username_result.strip('"')
                        except:
                            pass
                    
                    verification = await engagement.verify_comment_at_top(comment_text, current_username)
                    
                    logger.info(f"   📊 Verification results:")
                    logger.info(f"      Found at top: {verification.get('found_at_top', False)}")
                    logger.info(f"      Username match: {verification.get('username_match', False)}")
                    logger.info(f"      Comment match: {verification.get('comment_match', False)}")
                    
                    if verification.get("top_comment"):
                        top = verification["top_comment"]
                        logger.info(f"      Top comment: @{top.get('username', '?')}: {top.get('text', '')[:40]}...")
                    
                    # CRITICAL: Check if username is displayed at top
                    if verification.get("top_comments"):
                        top_comment = verification["top_comments"][0] if verification["top_comments"] else None
                        username_visible = top_comment and top_comment.get("username") and top_comment.get("username") != "unknown"
                        
                        if not username_visible:
                            logger.error("   ❌ FAILURE: Username not displayed at top!")
                            video_result["error"] = "Username not displayed at top"
                            video_result["commented"] = False
                            video_result["username_visible"] = False
                            video_result["comment_verified"] = False
                        elif not verification.get("found_at_top"):
                            logger.error("   ❌ FAILURE: Comment not at top of list!")
                            video_result["error"] = "Comment not at top"
                            video_result["commented"] = False
                            video_result["comment_verified"] = False
                        else:
                            logger.info("   ✅ Comment verified at top with username visible")
                            video_result["commented"] = True
                            video_result["comment_verified"] = True
                            video_result["username_visible"] = True
                            # Success requires both like AND comment to be verified
                            video_result["success"] = video_result.get("like_verified", False) and True
                    else:
                        logger.error("   ❌ FAILURE: No comments found in list!")
                        video_result["error"] = "No comments found"
                        video_result["commented"] = False
                else:
                    error = comment_result.get("error", "Unknown error")
                    video_result["error"] = error
                    logger.error(f"   ❌ Failed to post comment")
                    logger.error(f"   📊 Error: {error}")
                    if comment_result.get("steps"):
                        logger.info("   📋 Step results:")
                        for step_name, step_result in comment_result.get("steps", {}).items():
                            status = "✅" if step_result.get("success") else "❌"
                            logger.info(f"      {status} {step_name}: {step_result.get('error', 'OK')}")
                
                # Step 4: Move to next video (if not last)
                if i < num_videos - 1:
                    logger.info("\n   " + "-"*50)
                    logger.info("   ⏭️  STEP 4: MOVING TO NEXT VIDEO")
                    logger.info("   " + "-"*50)
                    logger.info("   📍 Current URL before navigation: {current_url}")
                    logger.info("   🖱️  Triggering next video...")
                    
                    nav_result = await engagement.go_to_next_video()
                    logger.info(f"   📊 Navigation result: {nav_result}")
                    await asyncio.sleep(2)  # Wait for next video to load
                    
                    # Update current URL
                    current_url = await engagement.get_current_url()
                    logger.info(f"   ✅ Now on: {current_url}")
                    logger.info(f"   ⏱️  Waiting 2 seconds for video to load...")
                else:
                    logger.info("\n   ✅ Last video processed - no navigation needed")
                
            except Exception as e:
                logger.error(f"   ❌ Error on video {i+1}: {e}")
                video_result["error"] = str(e)
            
            results.append(video_result)
            
            # Small delay between videos
            if i < num_videos - 1:
                await asyncio.sleep(1)
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info("📊 ENGAGEMENT SUMMARY")
        logger.info(f"{'='*60}")
        
        success_count = sum(1 for r in results if r.get("success"))
        liked_count = sum(1 for r in results if r.get("liked"))
        commented_count = sum(1 for r in results if r.get("commented"))
        
        logger.info(f"✅ Successfully engaged: {success_count}/{num_videos}")
        logger.info(f"❤️  Videos liked (verified): {liked_count}/{num_videos}")
        logger.info(f"💬 Comments posted (verified at top): {commented_count}/{num_videos}")
        
        logger.info("\n📋 Detailed Results:")
        for i, result in enumerate(results, 1):
            status = "✅" if result.get("success") else "❌"
            logger.info(f"   Video {i}: {status}")
            logger.info(f"      Liked (verified): {result.get('like_verified', False)}")
            logger.info(f"      Commented (verified): {result.get('comment_verified', False)}")
            logger.info(f"      Username visible: {result.get('username_visible', False)}")
            if result.get("comment_text"):
                logger.info(f"      Comment: {result['comment_text']}")
            if result.get("error"):
                logger.error(f"      ❌ Error: {result['error']}")
        
        # Final verification summary
        logger.info("\n" + "="*60)
        logger.info("🔍 VERIFICATION SUMMARY")
        logger.info("="*60)
        all_likes_verified = all(r.get("like_verified", False) for r in results)
        all_comments_verified = all(r.get("comment_verified", False) for r in results)
        all_usernames_visible = all(r.get("username_visible", False) for r in results)
        
        logger.info(f"   All likes verified: {'✅' if all_likes_verified else '❌'}")
        logger.info(f"   All comments at top: {'✅' if all_comments_verified else '❌'}")
        logger.info(f"   All usernames visible: {'✅' if all_usernames_visible else '❌'}")
        
        if not all_likes_verified:
            logger.error("   ❌ FAILURE: Some videos are not actually liked!")
        if not all_comments_verified:
            logger.error("   ❌ FAILURE: Some comments are not at the top!")
        if not all_usernames_visible:
            logger.error("   ❌ FAILURE: Some usernames are not displayed!")
        
        return results
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise
        
    finally:
        await engagement.cleanup()
        logger.info("\n🧹 Cleanup complete")


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Like and comment on TikTok videos from FYP"
    )
    parser.add_argument(
        "-n", "--num-videos",
        type=int,
        default=3,
        help="Number of videos to engage with (default: 3)"
    )
    parser.add_argument(
        "-c", "--comment",
        type=str,
        default="Great content! 🔥",
        help="Comment template (timestamp will be added) (default: 'Great content! 🔥')"
    )
    parser.add_argument(
        "--no-extension",
        action="store_true",
        help="Don't use Safari extension (use pyautogui instead)"
    )
    
    args = parser.parse_args()
    
    # Run engagement
    results = await engage_with_fyp_videos(
        num_videos=args.num_videos,
        comment_template=args.comment,
        use_extension=not args.no_extension
    )
    
    # Exit with error code if any failed
    success_count = sum(1 for r in results if r.get("success"))
    if success_count < args.num_videos:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())

