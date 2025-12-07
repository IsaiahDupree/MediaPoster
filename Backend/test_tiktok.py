"""
TikTok Integration Test
Tests only the TikTok account configuration
"""
import os
import sys
from dotenv import load_dotenv
from loguru import logger
import requests
import json

# Setup logging
logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")

load_dotenv()

API_KEY = os.getenv('BLOTATO_API_KEY')
BASE_URL = "https://backend.blotato.com/v2"
TIKTOK_ID = os.getenv('TIKTOK_ACCOUNT_ID', '710')

headers = {
    'blotato-api-key': API_KEY,
    'Content-Type': 'application/json'
}

import base64
import time

def test_tiktok():
    logger.info("\n🎵 Testing TikTok Integration with Local Video")
    logger.info(f"Account ID: {TIKTOK_ID}")
    
    if not API_KEY:
        logger.error("❌ BLOTATO_API_KEY not found")
        return
        
    # 1. Upload Local Media
    local_file = "temp/AAZS8060.MOV"
    logger.info(f"\n📤 Reading local file: {local_file}")
    
    try:
        with open(local_file, "rb") as f:
            video_data = f.read()
            
        # Encode to base64
        b64_data = base64.b64encode(video_data).decode('utf-8')
        # Create data URI (try video/quicktime for MOV)
        data_uri = f"data:video/quicktime;base64,{b64_data}"
        
        logger.info(f"File size: {len(video_data) / 1024 / 1024:.2f} MB")
        logger.info("Uploading to Blotato...")
        
        media_resp = requests.post(
            f"{BASE_URL}/media",
            json={'url': data_uri},
            headers=headers,
            timeout=120  # Longer timeout for upload
        )
        
        if media_resp.status_code != 201:
            logger.error(f"❌ Upload failed: {media_resp.text[:200]}")
            return
            
        media_url = media_resp.json().get('url')
        logger.success(f"✅ Media uploaded: {media_url[:50]}...")
        
    except FileNotFoundError:
        logger.error(f"❌ File not found: {local_file}")
        return
    except Exception as e:
        logger.error(f"❌ Upload error: {e}")
        return

    # 2. Create Post
    logger.info("\n📝 Creating TikTok post...")
    
    payload = {
        'post': {
            'accountId': TIKTOK_ID,
            'content': {
                'text': 'Test post from MediaPoster - Local iPhone Video #test',
                'mediaUrls': [media_url],
                'platform': 'tiktok'
            },
            'target': {
                'targetType': 'tiktok',
                'privacyLevel': 'PUBLIC_TO_EVERYONE',  # Public post
                'disabledComments': False,  # Allow comments
                'disabledDuet': False,  # Allow duets
                'disabledStitch': False,  # Allow stitches
                'isBrandedContent': False,
                'isYourBrand': False,
                'isAiGenerated': False,
                'isDraft': False  # Publish immediately
            }
        }
    }
    
    try:
        post_resp = requests.post(
            f"{BASE_URL}/posts",
            json=payload,
            headers=headers,
            timeout=30
        )
        
        logger.info(f"Status: {post_resp.status_code}")
        
        if post_resp.status_code == 201:
            data = post_resp.json()
            submission_id = data.get('postSubmissionId')
            logger.success(f"✅ TIKTOK POST SUBMITTED!")
            logger.info(f"Submission ID: {submission_id}")
            
            # 3. Check Status
            logger.info("\n⏳ Checking post status...")
            for i in range(5):
                time.sleep(5)
                status_resp = requests.get(
                    f"{BASE_URL}/posts/{submission_id}",
                    headers=headers
                )
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    status = status_data.get('status')
                    logger.info(f"  Attempt {i+1}: {status}")
                    if status == 'COMPLETED':
                        logger.success("✅ Post processing COMPLETED!")
                        break
                    elif status == 'FAILED':
                        logger.error(f"❌ Post processing FAILED: {status_data.get('error')}")
                        break
                else:
                    logger.warning(f"  Could not fetch status: {status_resp.status_code}")
            
        else:
            logger.error(f"❌ FAILED: {post_resp.text}")
            
    except Exception as e:
        logger.error(f"❌ Request error: {e}")

if __name__ == "__main__":
    test_tiktok()
