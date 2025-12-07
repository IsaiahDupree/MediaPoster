"""
Test Instagram (807) posting and URL retrieval
"""
import os
import sys
from dotenv import load_dotenv
from loguru import logger
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from modules.monitoring.post_tracker import PostTracker

load_dotenv()

API_KEY = os.getenv('BLOTATO_API_KEY')
BASE_URL = "https://backend.blotato.com/v2"
INSTAGRAM_ACCOUNT_ID = "807"

def test_instagram_post_and_track():
    """Post to Instagram and track until URL is available"""
    logger.info("\n╔" + "="*78 + "╗")
    logger.info("║" + " "*22 + "INSTAGRAM URL RETRIEVAL TEST" + " "*27 + "║")
    logger.info("╚" + "="*78 + "╝\n")
    
    headers = {
        'blotato-api-key': API_KEY,
        'Content-Type': 'application/json'
    }
    
    # Step 1: Upload media
    logger.info("STEP 1: Upload Media")
    logger.info("─"*80)
    
    media_response = requests.post(
        f"{BASE_URL}/media",
        json={'url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4'},
        headers=headers,
        timeout=60
    )
    
    if media_response.status_code != 201:
        logger.error(f"❌ Media upload failed: {media_response.text}")
        return False
    
    media_url = media_response.json().get('url')
    logger.success(f"✅ Media uploaded\n")
    
    # Step 2: Create Instagram Reel
    logger.info("STEP 2: Create Instagram Reel")
    logger.info("─"*80)
    
    post_payload = {
        'post': {
            'accountId': INSTAGRAM_ACCOUNT_ID,
            'content': {
                'text': 'Testing Instagram URL retrieval 🎬\n\n#Test #MediaPoster',
                'mediaUrls': [media_url],
                'platform': 'instagram'
            },
            'target': {
                'targetType': 'instagram',
                'mediaType': 'reel'
            }
        }
    }
    
    logger.info(f"Account: {INSTAGRAM_ACCOUNT_ID}")
    logger.info(f"Type: Reel")
    
    post_response = requests.post(
        f"{BASE_URL}/posts",
        json=post_payload,
        headers=headers,
        timeout=30
    )
    
    if post_response.status_code != 201:
        logger.error(f"❌ Post creation failed: {post_response.text}")
        return False
    
    submission_id = post_response.json().get('postSubmissionId')
    logger.success(f"✅ Reel posted!")
    logger.info(f"Submission ID: {submission_id}\n")
    
    # Step 3: Track until published
    logger.info("STEP 3: Track Until Published")
    logger.info("─"*80 + "\n")
    
    tracker = PostTracker(API_KEY)
    result = tracker.poll_until_complete(
        submission_id, 
        max_wait_seconds=600,  # Instagram can take longer
        poll_interval=30
    )
    
    if not result:
        logger.error("❌ Tracking failed")
        return False
    
    # Step 4: Display results
    logger.info("\n" + "="*80)
    logger.info("RESULTS")
    logger.info("="*80 + "\n")
    
    status = result.get('status')
    url = result.get('url')
    wait_time = result.get('wait_time', result.get('waited', 0))
    
    logger.info(f"Platform: Instagram")
    logger.info(f"Account: {INSTAGRAM_ACCOUNT_ID}")
    logger.info(f"Submission ID: {submission_id}")
    logger.info(f"Status: {status}")
    logger.info(f"Wait Time: {wait_time}s")
    
    if url:
        logger.success(f"\n🎉 SUCCESS! Instagram Reel URL Retrieved:")
        logger.info(f"\n   {url}\n")
        logger.info(f"This URL can be used for:")
        logger.info(f"  • Analytics tracking")
        logger.info(f"  • Comment collection")
        logger.info(f"  • Engagement monitoring")
        logger.info(f"  • Sentiment analysis")
    else:
        logger.warning(f"\n⚠️  Post status: {status}")
        logger.info(f"Full response: {result}")
    
    logger.info("\n" + "="*80 + "\n")
    
    return url is not None

if __name__ == '__main__':
    success = test_instagram_post_and_track()
    sys.exit(0 if success else 1)
