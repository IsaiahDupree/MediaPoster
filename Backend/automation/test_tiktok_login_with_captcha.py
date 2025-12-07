"""
Test TikTok Login with Captcha Solving Integration
This script tests the full flow: Chrome profile discovery -> Login -> Captcha solving
"""
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from automation.tiktok_login_automation import TikTokLoginAutomation
from automation.chrome_profile_manager import ChromeProfileManager


async def test_chrome_profile_discovery():
    """Test Chrome profile discovery and selection."""
    logger.info("=" * 60)
    logger.info("Step 1: Chrome Profile Discovery")
    logger.info("=" * 60)
    
    manager = ChromeProfileManager()
    
    # List all profiles
    manager.list_profiles()
    
    # Try to get saved profile or default
    profile = manager.get_saved_profile()
    if not profile:
        profile = manager.select_profile("Default")
    
    if profile:
        logger.success(f"✅ Profile selected: {profile['name']}")
        logger.info(f"   Path: {profile['path']}")
        
        # Save it
        manager.save_profile_config(profile)
        return profile
    else:
        logger.error("❌ No Chrome profile found")
        return None


async def test_tiktok_login_with_captcha():
    """Test TikTok login with integrated captcha solving."""
    logger.info("\n" + "=" * 60)
    logger.info("Step 2: TikTok Login with Captcha Solving")
    logger.info("=" * 60)
    
    # Check for credentials
    import os
    username = os.getenv("TIKTOK_USERNAME")
    password = os.getenv("TIKTOK_PASSWORD")
    
    if not username or not password:
        logger.error("❌ TIKTOK_USERNAME and TIKTOK_PASSWORD must be set in .env")
        return False
    
    logger.info(f"Username: {username}")
    logger.info("Password: [REDACTED]")
    
    # Get saved profile name
    manager = ChromeProfileManager()
    saved_profile = manager.get_saved_profile()
    profile_name = saved_profile['name'] if saved_profile else None
    
    # Initialize automation
    logger.info("\nInitializing TikTok login automation...")
    logger.info("⚠️  This will:")
    logger.info("   1. Start Chrome with your saved profile")
    logger.info("   2. Navigate to TikTok")
    logger.info("   3. Attempt login")
    logger.info("   4. Detect and solve any captchas automatically")
    logger.info("   5. Save session if successful")
    
    automation = TikTokLoginAutomation(
        headless=False,  # Must be visible for captcha solving
        save_session=True,
        profile_name=profile_name
    )
    
    try:
        logger.info("\nStarting login flow...")
        success = await automation.login()
        
        if success:
            logger.success("\n✅ TikTok login completed successfully!")
            logger.info("Session saved - you can reuse it next time")
            return True
        else:
            logger.error("\n❌ TikTok login failed")
            logger.info("Check screenshots directory for debugging")
            return False
            
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Automation interrupted by user")
        return False
    except Exception as e:
        logger.error(f"\n❌ Error during automation: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False
    finally:
        logger.info("\nCleaning up...")
        await automation.cleanup()


async def main():
    """Run the full test flow."""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    logger.info("=" * 60)
    logger.info("TikTok Login with Captcha Solving - Full Test Flow")
    logger.info("=" * 60)
    logger.info("")
    logger.warning("⚠️  This test will:")
    logger.warning("   - Discover and save your Chrome profile")
    logger.warning("   - Open Chrome browser (non-headless)")
    logger.warning("   - Attempt TikTok login")
    logger.warning("   - Solve captchas if they appear")
    logger.warning("   - Make API calls to captcha solver (consumes credits)")
    logger.info("")
    
    # Step 1: Chrome Profile Discovery
    profile = await test_chrome_profile_discovery()
    if not profile:
        logger.error("Cannot proceed without Chrome profile")
        return False
    
    # Step 2: TikTok Login with Captcha
    success = await test_tiktok_login_with_captcha()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    logger.info(f"Chrome Profile: {'✅ Found' if profile else '❌ Not Found'}")
    logger.info(f"TikTok Login: {'✅ Success' if success else '❌ Failed'}")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

