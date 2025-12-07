"""
Test script for TikTok Captcha Solver Service

Tests the captcha solver API integration with sample data.
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from services.tiktok_captcha_solver import TikTokCaptchaSolver
from loguru import logger


async def test_api_connectivity():
    """Test basic API connectivity."""
    logger.info("Testing API connectivity...")
    
    try:
        solver = TikTokCaptchaSolver()
        logger.success("✅ TikTokCaptchaSolver initialized successfully")
        logger.info(f"API URL: {solver.api_url}")
        logger.info(f"RapidAPI Host: {solver.rapidapi_host}")
        return True
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        return False


async def test_3d_captcha():
    """Test solving a 3D captcha with a sample URL."""
    logger.info("\nTesting 3D captcha solver...")
    
    # Sample 3D captcha URL from the API documentation
    test_url = "https://p19-rc-captcha-va.ibyteimg.com/tos-maliva-i-b4yrtqhy5a-us/3d_2385_8c09f6e7854724719b59d73732791824b8e49385_1.jpg~tplv-b4yrtqhy5a-3.webp"
    
    try:
        solver = TikTokCaptchaSolver()
        result = await solver.solve_3d(
            image_source=test_url,
            width=348,
            height=216
        )
        
        logger.success(f"✅ 3D captcha solved successfully!")
        logger.info(f"Response: {result}")
        return True
        
    except Exception as e:
        logger.error(f"❌ 3D captcha test failed: {e}")
        return False


async def test_all_captcha_types():
    """Test configuration for all supported captcha types."""
    logger.info("\nTesting all captcha type endpoints...")
    
    solver = TikTokCaptchaSolver()
    
async def test_all_captcha_types():
    """Test configuration for all supported captcha types."""
    logger.info("\nTesting all captcha type endpoints...")
    
    solver = TikTokCaptchaSolver()
    
    # Check endpoints - all should use the same base endpoint now
    base_endpoint = f"{solver.api_url}/tiktok/captcha"
    
    logger.info(f"  Base Endpoint: {base_endpoint}")
    logger.info(f"  Supported Types: {solver.VALID_CAPTCHA_TYPES}")
        
    logger.success("✅ All endpoints configured")
    return True


async def test_slide_captcha():
    """Test solving a Slide captcha."""
    logger.info("\nTesting Slide captcha solver...")
    
    # Sample Slide captcha URL
    test_url = "https://p19-rc-captcha-sg.ibyteimg.com/tos-alisg-i-749px8mig0-sg/df21c974043a4d36bd1149d1ad7a898f~tplv-749px8mig0-3.webp"
    
    try:
        solver = TikTokCaptchaSolver()
        result = await solver.solve_slide(
            image_source=test_url,
            width=348,
            height=216
        )
        
        logger.success(f"✅ Slide captcha solved successfully!")
        logger.info(f"Response: {result}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Slide captcha test failed: {e}")
        return False


async def test_whirl_captcha():
    """Test solving a Whirl captcha."""
    logger.info("\nTesting Whirl captcha solver...")
    
    # Sample Whirl captcha URL
    test_url = "https://p16-rc-captcha-va.ibyteimg.com/tos-maliva-i-b4yrtqhy5a-us/22a2883b8b6e4f45ae3aeeb94cc446f4~tplv-b4yrtqhy5a-3.webp"
    
    try:
        solver = TikTokCaptchaSolver()
        result = await solver.solve_whirl(
            image_source=test_url,
            width=348,
            height=216
        )
        
        logger.success(f"✅ Whirl captcha solved successfully!")
        logger.info(f"Response: {result}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Whirl captcha test failed: {e}")
        return False


async def run_all_tests():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("TikTok Captcha Solver Test Suite")
    logger.info("=" * 60)
    
    tests = [
        ("API Connectivity", test_api_connectivity),
        ("All Endpoints", test_all_captcha_types),
        ("3D Captcha Solving", test_3d_captcha),
        ("Slide Captcha Solving", test_slide_captcha),
        ("Whirl Captcha Solving", test_whirl_captcha),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status} - {test_name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("\n🎉 All tests passed!")
    else:
        logger.warning(f"\n⚠️  {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
