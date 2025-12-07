"""
Focused Pinterest Testing
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
PINTEREST_ACCOUNT_ID = os.getenv('PINTEREST_ACCOUNT_ID', '173')
PINTEREST_BOARD_ID = os.getenv('PINTEREST_BOARD_ID', '1139481211908910388')

headers = {
    'blotato-api-key': API_KEY,
    'Content-Type': 'application/json'
}

logger.info("="*80)
logger.info("PINTEREST FOCUSED TEST")
logger.info("="*80)
logger.info(f"\nAccount ID: {PINTEREST_ACCOUNT_ID}")
logger.info(f"Board ID: {PINTEREST_BOARD_ID}")

# Step 1: Upload image
logger.info("\n" + "─"*80)
logger.info("STEP 1: Upload Test Image")
logger.info("─"*80)

payload = {'url': 'https://picsum.photos/1080/1920'}
logger.info(f"Uploading: {payload['url']}")

response = requests.post(f"{BASE_URL}/media", json=payload, headers=headers, timeout=30)
logger.info(f"Status: {response.status_code}")

if response.status_code == 201:
    data = response.json()
    media_url = data.get('url')
    logger.success(f"✅ Upload successful!")
    logger.info(f"Blotato URL: {media_url}")
    
    # Step 2: Create Pinterest pin
    logger.info("\n" + "─"*80)
    logger.info("STEP 2: Create Pinterest Pin")
    logger.info("─"*80)
    
    pin_payload = {
        'post': {
            'accountId': PINTEREST_ACCOUNT_ID,
            'content': {
                'text': '🧪 Test Pin from MediaPoster\\n\\nTesting Pinterest integration.\\n\\n#test #mediaposter',
                'mediaUrls': [media_url],
                'platform': 'pinterest'
            },
            'target': {
                'targetType': 'pinterest',
                'boardId': PINTEREST_BOARD_ID,
                'title': 'MediaPoster Test Pin',
                'altText': 'Test image for Pinterest',
                'link': 'https://example.com'
            }
        }
    }
    
    logger.info(f"Creating pin on board {PINTEREST_BOARD_ID}...")
    
    response = requests.post(f"{BASE_URL}/posts", json=pin_payload, headers=headers, timeout=30)
    logger.info(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        data = response.json()
        logger.success(f"✅ Pin created successfully!")
        logger.info(f"Submission ID: {data.get('postSubmissionId')}")
        logger.info(f"\\nCheck at: https://my.blotato.com")
    else:
        logger.error(f"❌ Pin creation failed")
        logger.error(f"Response: {response.text}")
else:
    logger.error(f"❌ Image upload failed")
    logger.error(f"Response: {response.text}")

logger.info("\\n" + "="*80)
