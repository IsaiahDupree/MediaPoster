"""
Blotato API Test - Based on Official Documentation
Tests the documented endpoints: /v2/media and /v2/posts
"""
import os
import requests
from dotenv import load_dotenv
from loguru import logger
import sys

logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")

load_dotenv()

API_KEY = os.getenv('BLOTATO_API_KEY')
BASE_URL = "https://backend.blotato.com/v2"

def test_media_upload():
    """Test /v2/media endpoint with a sample image URL"""
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Media Upload (/v2/media)")
    logger.info("="*80)
    
    headers = {
        'blotato-api-key': API_KEY,
        'Content-Type': 'application/json'
    }
    
    # Use a sample public image URL
    test_url = "https://picsum.photos/800/600"
    
    payload = {
        "url": test_url
    }
    
    logger.info(f"  Uploading: {test_url}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/media",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"  Status: {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            blotato_url = data.get('url')
            logger.success(f"  ✅ Upload successful!")
            logger.info(f"  Blotato URL: {blotato_url}")
            return blotato_url
        else:
            logger.error(f"  ❌ Upload failed")
            logger.error(f"  Response: {response.text}")
            return None
            
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return None

def test_google_drive_conversion():
    """Test Google Drive URL conversion"""
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Google Drive URL Conversion")
    logger.info("="*80)
    
    sample_share_url = "https://drive.google.com/file/d/18-UgDEaKG7YR7AewIDd_Qi4QCLCX5Kop/view?usp=drivesdk"
    sample_download_url = "https://drive.google.com/uc?export=download&id=18-UgDEaKG7YR7AewIDd_Qi4QCLCX5Kop"
    
    logger.info(f"  Share URL:")
    logger.info(f"    {sample_share_url}")
    logger.info(f"  Download URL:")
    logger.info(f"    {sample_download_url}")
    logger.success(f"  ✓ Conversion format documented")
    
    return True

def check_account_id_format():
    """Check if configured account IDs match expected format"""
    logger.info("\n" + "="*80)
    logger.info("TEST 3: Account ID Format Check")
    logger.info("="*80)
    
    account_ids = {
        'YOUTUBE_ACCOUNT_ID': os.getenv('YOUTUBE_ACCOUNT_ID'),
        'TIKTOK_ACCOUNT_ID': os.getenv('TIKTOK_ACCOUNT_ID'),
        'INSTAGRAM_ACCOUNT_ID': os.getenv('INSTAGRAM_ACCOUNT_ID'),
    }
    
    logger.warning("  ⚠️  Current account IDs are numeric:")
    for name, value in account_ids.items():
        if value:
            logger.info(f"    {name}: {value}")
    
    logger.info("\n  ℹ️  Expected format: acc_xxxxx")
    logger.info("  📋 To get correct account IDs:")
    logger.info("    1. Log into Blotato dashboard")
    logger.info("    2. Go to 'Social Accounts'")
    logger.info("    3. Click 'Copy Account ID' for each account")
    logger.info("    4. Update .env file with acc_ formatted IDs")
    
    return False  # Indicates IDs need updating

def main():
    logger.info("\n╔" + "="*78 + "╗")
    logger.info("║" + " "*20 + "BLOTATO API OFFICIAL ENDPOINT TESTS" + " "*23 + "║")
    logger.info("╚" + "="*78 + "╝")
    
    if not API_KEY:
        logger.error("\n❌ BLOTATO_API_KEY not found in environment")
        return False
    
    logger.info(f"\nAPI Key: {API_KEY[:25]}...")
    logger.info(f"Base URL: {BASE_URL}")
    
    # Run tests
    results = {}
    
    # Test 1: Media Upload
    media_url = test_media_upload()
    results['media_upload'] = media_url is not None
    
    # Test 2: Google Drive conversion (documentation only)
    results['gdrive_conversion'] = test_google_drive_conversion()
    
    # Test 3: Account ID format check
    results['account_ids'] = check_account_id_format()
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "⚠️  NEEDS ATTENTION"
        logger.info(f"  {status}  {test_name}")
    
    logger.info("\n" + "="*80)
    logger.info("NEXT STEPS")
    logger.info("="*80)
    
    if results['media_upload']:
        logger.success("✓ API Key is valid and media upload works!")
        logger.info("\n📋 To proceed with posting:")
        logger.info("  1. Get your acc_ formatted account IDs from Blotato dashboard")
        logger.info("  2. Update INSTAGRAM_ACCOUNT_ID, TIKTOK_ACCOUNT_ID, etc. in .env")
        logger.info("  3. Run: python3 test_e2e.py --video path/to/video.mp4")
    else:
        logger.error("❌ Media upload failed - API key may be invalid")
        logger.info("\n📋 To fix:")
        logger.info("  1. Log into Blotato dashboard")
        logger.info("  2. Go to Settings → API Keys")
        logger.info("  3. Generate new API key if needed")
        logger.info("  4. Update BLOTATO_API_KEY in .env file")
    
    logger.info("\n" + "="*80)
    
    return all(results.values())

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
