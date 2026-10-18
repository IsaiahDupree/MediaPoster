#!/usr/bin/env python3
"""
Test Safari Automations - Verify Sora and Twitter automation works
Run this script to test the Safari browser automations.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from loguru import logger
import time


def test_sora_credits():
    """Test Sora credit checking via Safari."""
    logger.info("=" * 60)
    logger.info("🎬 TESTING SORA CREDIT CHECK")
    logger.info("=" * 60)
    
    try:
        from automation.sora_full_automation import SoraFullAutomation
        
        sora = SoraFullAutomation()
        
        # Navigate to Sora
        logger.info("Navigating to Sora...")
        sora.navigate_to_explore()
        time.sleep(2)
        
        # Check login
        logger.info("Checking login status...")
        logged_in = sora.check_login()
        logger.info(f"Login status: {'✅ Logged in' if logged_in else '❌ Not logged in'}")
        
        if not logged_in:
            logger.warning("⚠️ Please login to Sora manually, then re-run this test")
            return False
        
        # Get usage/credits
        logger.info("Getting usage information...")
        usage = sora.get_usage()
        logger.info(f"Usage data: {usage}")
        
        credits_left = usage.get('video_gens_left', 'unknown')
        logger.success(f"✅ Sora Credits: {credits_left} video gens remaining")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Sora test failed: {e}")
        return False


def test_twitter_login():
    """Test Twitter login check via Safari."""
    logger.info("=" * 60)
    logger.info("🐦 TESTING TWITTER LOGIN CHECK")
    logger.info("=" * 60)
    
    try:
        from automation.safari_twitter_poster import SafariTwitterPoster
        
        poster = SafariTwitterPoster(use_x_domain=True)
        
        # Open Twitter
        logger.info("Opening Twitter/X...")
        poster.open_twitter()
        time.sleep(4)
        
        # Try simple login check first (faster, more reliable)
        logger.info("Checking login status (simple check)...")
        simple_status = poster.simple_login_check()
        logger.info(f"Simple check: {simple_status}")
        
        if simple_status.get('logged_in') is True:
            logger.success(f"✅ Logged into Twitter (URL: {simple_status.get('url', 'unknown')[:50]}...)")
            return True
        elif simple_status.get('logged_in') is False:
            reason = simple_status.get('reason', 'unknown')
            logger.warning(f"⚠️ Not logged into Twitter: {reason}")
            logger.info("Please login to Twitter manually, then re-run this test")
            return False
        
        # Fall back to detailed check
        logger.info("Running detailed login check...")
        status = poster.check_login_status()
        logger.info(f"Detailed check: {status}")
        
        if status.get('logged_in'):
            username = status.get('username', 'unknown')
            logger.success(f"✅ Logged into Twitter as: @{username}")
            return True
        else:
            reason = status.get('reason', 'unknown')
            logger.warning(f"⚠️ Not logged into Twitter: {reason}")
            logger.info("Please login to Twitter manually, then re-run this test")
            return False
            
    except Exception as e:
        logger.error(f"❌ Twitter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_twitter_compose():
    """Test Twitter compose functionality (without posting)."""
    logger.info("=" * 60)
    logger.info("📝 TESTING TWITTER COMPOSE (DRY RUN)")
    logger.info("=" * 60)
    
    try:
        from automation.safari_twitter_poster import SafariTwitterPoster
        
        poster = SafariTwitterPoster(use_x_domain=True)
        
        # Open compose
        logger.info("Opening compose modal...")
        success = poster.open_compose()
        
        if success:
            logger.success("✅ Compose modal opened successfully")
            
            # Type test text (but don't post)
            test_text = "This is a test tweet - DO NOT POST (automation test)"
            logger.info(f"Typing test text: {test_text[:50]}...")
            
            typed = poster.type_tweet_via_js(test_text)
            if typed:
                logger.success("✅ Text typed successfully")
                logger.info("⚠️ NOT clicking post button (dry run)")
                return True
            else:
                logger.warning("⚠️ Text typing may have issues")
                return False
        else:
            logger.error("❌ Failed to open compose modal")
            return False
            
    except Exception as e:
        logger.error(f"❌ Twitter compose test failed: {e}")
        return False


def test_daily_automation_status():
    """Test the daily automation manager status."""
    logger.info("=" * 60)
    logger.info("📊 TESTING DAILY AUTOMATION STATUS")
    logger.info("=" * 60)
    
    try:
        from services.daily_automation import DailyAutomationManager
        from services.event_bus import EventBus
        
        event_bus = EventBus.get_instance()
        manager = DailyAutomationManager.get_instance(event_bus)
        
        status = manager.get_status()
        logger.info(f"Automation Status:")
        logger.info(f"  - Initialized: {status.get('initialized')}")
        logger.info(f"  - Started at: {status.get('started_at')}")
        
        sora_status = status.get('sora', {})
        logger.info(f"  - Sora running: {sora_status.get('running')}")
        logger.info(f"  - Sora credits: {sora_status.get('credits')}")
        
        twitter_status = status.get('twitter', {})
        logger.info(f"  - Twitter running: {twitter_status.get('running')}")
        logger.info(f"  - Twitter posts today: {twitter_status.get('posts_today')}")
        
        logger.success("✅ Daily automation status retrieved")
        return True
        
    except Exception as e:
        logger.error(f"❌ Status check failed: {e}")
        return False


def main():
    """Run all Safari automation tests."""
    logger.info("🚀 Safari Automation Tests")
    logger.info("This will open Safari and test various automations.\n")
    
    results = {}
    
    # Test 1: Sora Credits
    results['sora_credits'] = test_sora_credits()
    time.sleep(2)
    
    # Test 2: Twitter Login
    results['twitter_login'] = test_twitter_login()
    time.sleep(2)
    
    # Test 3: Twitter Compose (if logged in)
    if results['twitter_login']:
        results['twitter_compose'] = test_twitter_compose()
    else:
        results['twitter_compose'] = None
        logger.info("⏭️ Skipping compose test (not logged in)")
    
    # Test 4: Daily Automation Status
    results['automation_status'] = test_daily_automation_status()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("📋 TEST SUMMARY")
    logger.info("=" * 60)
    
    for test_name, passed in results.items():
        if passed is None:
            status = "⏭️ SKIPPED"
        elif passed:
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        logger.info(f"  {test_name}: {status}")
    
    all_passed = all(v is True or v is None for v in results.values())
    
    if all_passed:
        logger.success("\n🎉 All tests passed! Safari automations are ready.")
    else:
        logger.warning("\n⚠️ Some tests failed. Check above for details.")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
