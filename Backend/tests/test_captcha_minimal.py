"""
Minimal TikTok Captcha Solver Test
Tests only connectivity and one captcha type to minimize API usage.
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
    """Test basic API connectivity (no API call made)."""
    logger.info("Testing API connectivity...")
    
    try:
        solver = TikTokCaptchaSolver()
        logger.success("✅ TikTokCaptchaSolver initialized successfully")
        logger.info(f"API URL: {solver.api_url}")
        logger.info(f"RapidAPI Host: {solver.rapidapi_host}")
        logger.info(f"API Key configured: {'Yes' if solver.rapidapi_key else 'No'}")
        if solver.rapidapi_key:
            logger.info(f"API Key preview: {solver.rapidapi_key[:10]}...{solver.rapidapi_key[-5:]}")
        return True
    except Exception as e:
        logger.error(f"❌ Initialization failed: {e}")
        return False


async def test_single_captcha():
    """Test solving ONE captcha (3D type) - this makes an actual API call."""
    logger.warning("\n⚠️  WARNING: This will make an actual API call and consume credits!")
    logger.info("Testing 3D captcha solver (single test to minimize API usage)...")
    
    # Sample 3D captcha URL from the API documentation
    test_url = "https://p19-rc-captcha-va.ibyteimg.com/tos-maliva-i-b4yrtqhy5a-us/3d_2385_8c09f6e7854724719b59d73732791824b8e49385_1.jpg~tplv-b4yrtqhy5a-3.webp"
    
    try:
        solver = TikTokCaptchaSolver()
        logger.info(f"Attempting to solve 3D captcha from URL...")
        logger.info(f"URL: {test_url[:60]}...")
        
        result = await solver.solve_3d(
            image_source=test_url,
            width=348,
            height=216
        )
        
        logger.success(f"✅ 3D captcha solved successfully!")
        logger.info(f"Response type: {type(result)}")
        logger.info(f"Response keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")
        logger.info(f"Response preview: {str(result)[:200]}...")
        return True
        
    except Exception as e:
        logger.error(f"❌ 3D captcha test failed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False


async def main():
    """Run minimal tests."""
    logger.info("=" * 60)
    logger.info("TikTok Captcha Solver - Minimal Test")
    logger.info("=" * 60)
    logger.warning("⚠️  This test will make 1 API call (3D captcha only)")
    logger.info("")
    
    # Test 1: Connectivity (no API call)
    connectivity_ok = await test_api_connectivity()
    
    if not connectivity_ok:
        logger.error("Cannot proceed - initialization failed")
        return False
    
    # Ask user if they want to proceed with actual API call
    logger.info("\n" + "=" * 60)
    logger.info("Ready to make API call. This will consume API credits.")
    logger.info("Proceeding with 3D captcha test...")
    logger.info("=" * 60)
    
    # Test 2: Single captcha solve (actual API call)
    captcha_ok = await test_single_captcha()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)
    
    logger.info(f"{'✅ PASS' if connectivity_ok else '❌ FAIL'} - API Connectivity")
    logger.info(f"{'✅ PASS' if captcha_ok else '❌ FAIL'} - 3D Captcha Solving")
    
    total_passed = sum([connectivity_ok, captcha_ok])
    logger.info(f"\nTotal: {total_passed}/2 tests passed")
    
    if total_passed == 2:
        logger.success("\n🎉 All tests passed!")
    else:
        logger.warning(f"\n⚠️  {2 - total_passed} test(s) failed")
    
    return total_passed == 2


if __name__ == "__main__":
    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

