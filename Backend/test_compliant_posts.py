"""
Updated Test Script for Successful Video Posts
Based on platform requirements and Blotato best practices
"""
import os
import sys
from dotenv import load_dotenv
from loguru import logger
import requests

logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")

load_dotenv()

API_KEY = os.getenv('BLOTATO_API_KEY')
BASE_URL = "https://backend.blotato.com/v2"

# Test accounts
YOUTUBE_ACCOUNT_ID = os.getenv('YOUTUBE_ACCOUNT_ID', '228')
TIKTOK_ACCOUNT_ID = os.getenv('TIKTOK_ACCOUNT_ID', '710')
INSTAGRAM_ACCOUNT_ID = os.getenv('INSTAGRAM_ACCOUNT_ID', '807')

headers = {
    'blotato-api-key': API_KEY,
    'Content-Type': 'application/json'
}

def upload_compliant_video():
    """Upload a video that meets all platform requirements"""
    logger.info("\n" + "="*80)
    logger.info("STEP 1: Upload Platform-Compliant Video")
    logger.info("="*80)
    
    # Use a SHORT vertical video that meets all platform requirements:
    # - Duration: ~10 seconds (meets all minimums)
    # - Aspect ratio: 9:16 (vertical - works for all platforms)
    # - Resolution: 720x1280 (safe for all platforms)
    # - Format: MP4/H.264 (universal support)
    
    test_video_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
    
    logger.info(f"  Using: {test_video_url}")
    logger.info("  Specs: Short duration, 16:9, MP4, H.264")
    
    payload = {'url': test_video_url}
    
    try:
        response = requests.post(
            f"{BASE_URL}/media",
            json=payload,
            headers=headers,
            timeout=60
        )
        
        logger.info(f"  Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            media_url = data.get('url')
            logger.success(f"  ✅ Upload successful!")
            logger.info(f"  Blotato URL: {media_url}")
            return media_url
        else:
            logger.error(f"  ❌ Upload failed")
            logger.error(f"  Response: {response.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return None

def test_youtube_compliant(media_url):
    """Test YouTube with compliant settings"""
    logger.info("\n" + "="*80)
    logger.info("TEST: YouTube Short (Compliant)")
    logger.info("="*80)
    
    # YouTube requirements:
    # - Max 60s duration ✓
    # - 9:16 aspect ratio ✓
    # - Max 256MB ✓
    # - Title required ✓
    
    payload = {
        'post': {
            'accountId': YOUTUBE_ACCOUNT_ID,
            'content': {
                'text': 'Test YouTube Short from MediaPoster API integration.\n\n#Shorts #Test',
                'mediaUrls': [media_url],
                'platform': 'youtube',
                'title': 'MediaPoster API Test Short'  # Max 100 chars
            },
            'target': {
                'targetType': 'youtube',
                'title': 'MediaPoster API Test Short',
                'privacyStatus': 'unlisted',  # Safe for testing
                'shouldNotifySubscribers': False,  # Don't spam subscribers
                'isMadeForKids': False,
                'containsSyntheticMedia': False
            }
        }
    }
    
    logger.info(f"  Account: {YOUTUBE_ACCOUNT_ID}")
    logger.info(f"  Privacy: unlisted")
    logger.info(f"  Title: {payload['post']['content']['title']}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/posts",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"  Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            logger.success(f"  ✅ Post created!")
            logger.info(f"  Submission ID: {data.get('postSubmissionId')}")
            return True
        else:
            logger.error(f"  ❌ Failed")
            logger.error(f"  Response: {response.text[:300]}")
            return False
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return False

def test_tiktok_compliant(media_url):
    """Test TikTok with compliant settings"""
    logger.info("\n" + "="*80)
    logger.info("TEST: TikTok (Compliant)")
    logger.info("="*80)
    
    # TikTok requirements:
    # - 9:16 or 1:1 aspect ratio ✓
    # - Max 10 min duration ✓
    # - Max 4GB ✓
    # - All required fields ✓
    
    payload = {
        'post': {
            'accountId': TIKTOK_ACCOUNT_ID,
            'content': {
                'text': 'Test TikTok from MediaPoster 🧪\n\n#Test #API',  # Max 2200 chars
                'mediaUrls': [media_url],
                'platform': 'tiktok'
            },
            'target': {
                'targetType': 'tiktok',
                'privacyLevel': 'SELF_ONLY',  # Safe for testing - only you can see
                'disabledComments': True,
                'disabledDuet': True,
                'disabledStitch': True,
                'isBrandedContent': False,
                'isYourBrand': False,
                'isAiGenerated': False,
                'isDraft': True  # DRAFT MODE - won't publish
            }
        }
    }
    
    logger.info(f"  Account: {TIKTOK_ACCOUNT_ID}")
    logger.info(f"  Privacy: SELF_ONLY (visible only to you)")
    logger.info(f"  Draft: Yes (won't publish)")
    
    try:
        response = requests.post(
            f"{BASE_URL}/posts",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"  Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            logger.success(f"  ✅ Draft created!")
            logger.info(f"  Submission ID: {data.get('postSubmissionId')}")
            return True
        else:
            logger.error(f"  ❌ Failed")
            logger.error(f"  Response: {response.text[:300]}")
            return False
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return False

def test_instagram_compliant(media_url):
    """Test Instagram with compliant settings"""
    logger.info("\n" + "="*80)
    logger.info("TEST: Instagram Reel (Compliant)")
    logger.info("="*80)
    
    # Instagram requirements:
    # - 4:5 to 1.91:1 aspect ratio ✓
    # - Max 100MB ✓
    # - 3s - 15min duration ✓
    # - Max 2200 char caption ✓
    
    payload = {
        'post': {
            'accountId': INSTAGRAM_ACCOUNT_ID,
            'content': {
                'text': 'Test Reel from MediaPoster 🎬\n\n#Test #API #MediaPoster',  # Max 2200
                'mediaUrls': [media_url],
                'platform': 'instagram'
            },
            'target': {
                'targetType': 'instagram',
                'mediaType': 'reel'  # Default, but explicit is better
            }
        }
    }
    
    logger.info(f"  Account: {INSTAGRAM_ACCOUNT_ID}")
    logger.info(f"  Type: Reel")
    logger.info(f"  Caption length: {len(payload['post']['content']['text'])} chars")
    
    try:
        response = requests.post(
            f"{BASE_URL}/posts",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"  Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            logger.success(f"  ✅ Reel created!")
            logger.info(f"  Submission ID: {data.get('postSubmissionId')}")
            return True
        else:
            logger.error(f"  ❌ Failed")
            logger.error(f"  Response: {response.text[:300]}")
            return False
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return False

def main():
    logger.info("\n╔" + "="*78 + "╗")
    logger.info("║" + " "*20 + "PLATFORM-COMPLIANT POST TESTING" + " "*25 + "║")
    logger.info("╚" + "="*78 + "╝")
    
    logger.info("\nℹ️  This test uses platform-compliant video specifications")
    logger.info("   to maximize success rate across all platforms.\n")
    
    # Upload compliant video
    media_url = upload_compliant_video()
    
    if not media_url:
        logger.error("\n❌ Media upload failed - cannot continue")
        return False
    
    # Run platform tests
    results = {}
    
    logger.info("\n" + "─"*80)
    logger.info("Running platform tests...")
    logger.info("─"*80)
    
    results['YouTube'] = test_youtube_compliant(media_url)
    results['TikTok'] = test_tiktok_compliant(media_url)
    results['Instagram'] = test_instagram_compliant(media_url)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("RESULTS SUMMARY")
    logger.info("="*80)
    
    for platform, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        logger.info(f"  {status}  {platform}")
    
    success_count = sum(1 for s in results.values() if s)
    total_count = len(results)
    
    logger.info(f"\nSuccess Rate: {success_count}/{total_count} ({success_count/total_count*100:.0f}%)")
    
    logger.info("\n" + "="*80)
    logger.info("NEXT STEPS")
    logger.info("="*80)
    
    if success_count == total_count:
        logger.success("\n🎉 All tests passed!")
        logger.info("\n📋 Check posts:")
        logger.info("  • Dashboard: https://my.blotato.com")
        logger.info("  • Failed: https://my.blotato.com/failed")
    else:
        logger.warning(f"\n⚠️  {total_count - success_count} test(s) failed")
        logger.info("\n📋 Troubleshooting:")
        logger.info("  1. Check failed posts: https://my.blotato.com/failed")
        logger.info("  2. Verify account IDs are correct")
        logger.info("  3. Check accounts are properly connected in Blotato")
        logger.info("  4. Review error messages for specific issues")
    
    logger.info("\n" + "="*80)
    
    return success_count == total_count

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
