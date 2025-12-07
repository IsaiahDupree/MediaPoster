"""
Test comprehensive post workflow with URL retrieval
"""
import os
import sys
from dotenv import load_dotenv
from loguru import logger
import requests

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.monitoring.post_tracker import PostTracker

load_dotenv()

API_KEY = os.getenv('BLOTATO_API_KEY')
BASE_URL = "https://backend.blotato.com/v2"

def test_post_and_track():
    """Create a post and track it until published"""
    logger.info("\n╔" + "="*78 + "╗")
    logger.info("║" + " "*20 + "POST & TRACK WORKFLOW TEST" + " "*32 + "║")
    logger.info("╚" + "="*78 + "╝\n")
    
    headers = {
        'blotato-api-key': API_KEY,
        'Content-Type': 'application/json'
    }
    
    # Step 1: Upload media
    logger.info("STEP 1: Upload Test Media")
    logger.info("─"*80)
    
    media_response = requests.post(
        f"{BASE_URL}/media",
        json={'url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4'},
        headers=headers,
        timeout=60
    )
    
    if media_response.status_code != 201:
        logger.error(f"Media upload failed: {media_response.text}")
        return False
    
    media_url = media_response.json().get('url')
    logger.success(f"✅ Media uploaded: {media_url[:60]}...\n")
    
    # Step 2: Create post
    logger.info("STEP 2: Create Test Post")
    logger.info("─"*80)
    
    post_payload = {
        'post': {
            'accountId': '228',  # YouTube
            'content': {
                'text': 'Workflow test - tracking URL retrieval',
                'mediaUrls': [media_url],
                'platform': 'youtube',
                'title': 'URL Tracking Test'
            },
            'target': {
                'targetType': 'youtube',
                'title': 'URL Tracking Test',
                'privacyStatus': 'unlisted',
                'shouldNotifySubscribers': False
            }
        }
    }
    
    post_response = requests.post(
        f"{BASE_URL}/posts",
        json=post_payload,
        headers=headers,
        timeout=30
    )
    
    if post_response.status_code != 201:
        logger.error(f"Post creation failed: {post_response.text}")
        return False
    
    submission_id = post_response.json().get('postSubmissionId')
    logger.success(f"✅ Post created!")
    logger.info(f"   Submission ID: {submission_id}\n")
    
    # Step 3: Track until published
    logger.info("STEP 3: Track Post Status")
    logger.info("─"*80 + "\n")
    
    tracker = PostTracker(API_KEY)
    result = tracker.poll_until_complete(submission_id, max_wait_seconds=300)
    
    if not result:
        logger.error("❌ Tracking failed")
        return False
    
    # Step 4: Display results
    logger.info("\n" + "="*80)
    logger.info("FINAL RESULTS")
    logger.info("="*80)
    
    status = result.get('status')
    url = result.get('url')
    wait_time = result.get('wait_time', result.get('waited', 0))
    
    logger.info(f"\nSubmission ID: {submission_id}")
    logger.info(f"Status: {status}")
    logger.info(f"Wait Time: {wait_time}s")
    
    if url:
        logger.success(f"\n🎉 Published URL Retrieved!")
        logger.info(f"   {url}")
        logger.info(f"\n   This URL can now be used for:")
        logger.info(f"   • Analytics collection")
        logger.info(f"   • Comment fetching")
        logger.info(f"   • Sentiment analysis")
        logger.info(f"   • Performance tracking")
    else:
        logger.warning(f"\n⚠️  Post completed but URL not available")
    
    logger.info("\n" + "="*80)
    
    return url is not None

if __name__ == '__main__':
    success = test_post_and_track()
    sys.exit(0 if success else 1)
