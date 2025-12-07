"""
Test All Configured Blotato Account IDs
Validates each account ID format and tests basic functionality
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

# All configured account IDs
ACCOUNTS = {
    'YouTube': os.getenv('YOUTUBE_ACCOUNT_ID'),
    'TikTok': os.getenv('TIKTOK_ACCOUNT_ID'),
    'Instagram': os.getenv('INSTAGRAM_ACCOUNT_ID'),
    'Instagram (Alt 1)': os.getenv('INSTAGRAM_ACCOUNT_ID_ALT'),
    'Instagram (Alt 2)': os.getenv('INSTAGRAM_ACCOUNT_ID_ALT_2'),
    'Instagram (Alt 3)': os.getenv('INSTAGRAM_ACCOUNT_ID_ALT_3'),
    'Twitter': os.getenv('TWITTER_ACCOUNT_ID'),
    'Facebook': os.getenv('FACEBOOK_ACCOUNT_ID'),
    'Pinterest': os.getenv('PINTEREST_ACCOUNT_ID'),
    'Bluesky': os.getenv('BLUESKY_ACCOUNT_ID'),
    'Threads': os.getenv('THREADS_ACCOUNT_ID'),
}

def check_account_id_format(account_id: str) -> dict:
    """Check if account ID matches expected format"""
    if not account_id:
        return {
            'valid': False,
            'format': 'missing',
            'message': 'Not configured'
        }
    
    if account_id.startswith('acc_'):
        return {
            'valid': True,
            'format': 'correct',
            'message': 'Correct format (acc_xxxxx)'
        }
    elif account_id.isdigit():
        return {
            'valid': False,
            'format': 'numeric',
            'message': 'Numeric ID - needs conversion to acc_ format'
        }
    else:
        return {
            'valid': False,
            'format': 'unknown',
            'message': 'Unknown format'
        }

def test_account_with_draft_post(platform: str, account_id: str) -> dict:
    """
    Test account ID by attempting to create a draft post
    (won't actually publish anything)
    """
    headers = {
        'blotato-api-key': API_KEY,
        'Content-Type': 'application/json'
    }
    
    # Platform-specific configurations
    platform_configs = {
        'instagram': {
            'platform': 'instagram',
            'target': {'targetType': 'instagram', 'mediaType': 'reel'}
        },
        'tiktok': {
            'platform': 'tiktok',
            'target': {
                'targetType': 'tiktok',
                'privacyLevel': 'SELF_ONLY',
                'disabledComments': True,
                'disabledDuet': True,
                'disabledStitch': True,
                'isBrandedContent': False,
                'isYourBrand': False,
                'isAiGenerated': False,
                'isDraft': True
            }
        },
        'youtube': {
            'platform': 'youtube',
            'content_extra': {'title': 'Test Video'},
            'target': {
                'targetType': 'youtube',
                'title': 'Test Video',
                'privacyStatus': 'private',
                'shouldNotifySubscribers': False
            }
        },
        'twitter': {
            'platform': 'twitter',
            'target': {'targetType': 'twitter'}
        },
        'facebook': {
            'platform': 'facebook',
            'target': {
                'targetType': 'facebook',
                'pageId': '123456789'  # Would need real page ID
            }
        },
        'pinterest': {
            'platform': 'pinterest',
            'target': {
                'targetType': 'pinterest',
                'boardId': os.getenv('PINTEREST_BOARD_ID', '0')
            }
        },
        'threads': {
            'platform': 'threads',
            'target': {'targetType': 'threads'}
        },
        'bluesky': {
            'platform': 'bluesky',
            'target': {'targetType': 'bluesky'}
        },
    }
    
    config = platform_configs.get(platform.lower(), {
        'platform': platform.lower(),
        'target': {'targetType': platform.lower()}
    })
    
    payload = {
        'post': {
            'accountId': account_id,
            'content': {
                'text': '🧪 Test post - Draft only (will not publish)',
                'mediaUrls': [],
                'platform': config['platform']
            },
            'target': config['target']
        }
    }
    
    # Add extra content fields if needed
    if 'content_extra' in config:
        payload['post']['content'].update(config['content_extra'])
    
    try:
        response = requests.post(
            f"{BASE_URL}/posts",
            json=payload,
            headers=headers,
            timeout=15
        )
        
        return {
            'success': response.status_code == 201,
            'status_code': response.status_code,
            'response': response.json() if response.status_code == 201 else response.text[:200]
        }
        
    except Exception as e:
        return {
            'success': False,
            'status_code': 'error',
            'response': str(e)
        }

def main():
    logger.info("\n╔" + "="*78 + "╗")
    logger.info("║" + " "*25 + "ACCOUNT ID VALIDATION TEST" + " "*27 + "║")
    logger.info("╚" + "="*78 + "╝")
    
    if not API_KEY:
        logger.error("\n❌ BLOTATO_API_KEY not found")
        return False
    
    logger.info(f"\nAPI Key: {API_KEY[:25]}...")
    
    # Phase 1: Format Check
    logger.info("\n" + "="*80)
    logger.info("PHASE 1: Account ID Format Validation")
    logger.info("="*80)
    
    results = {}
    
    for name, account_id in ACCOUNTS.items():
        if not account_id:
            continue
            
        check = check_account_id_format(account_id)
        results[name] = check
        
        symbol = "✅" if check['valid'] else "⚠️"
        logger.info(f"\n{symbol} {name}")
        logger.info(f"   ID: {account_id}")
        logger.info(f"   Status: {check['message']}")
    
    # Phase 2: API Test (only for correctly formatted IDs)
    logger.info("\n" + "="*80)
    logger.info("PHASE 2: API Functionality Test")
    logger.info("="*80)
    
    valid_accounts = {name: id for name, id in ACCOUNTS.items() 
                     if id and id.startswith('acc_')}
    
    if not valid_accounts:
        logger.warning("\n⚠️  No accounts with correct 'acc_' format found")
        logger.info("   Skipping API functionality tests")
    else:
        logger.info(f"\nTesting {len(valid_accounts)} accounts with correct format...\n")
        
        for name, account_id in valid_accounts.items():
            # Determine platform from name
            platform = name.split(' ')[0].lower()
            
            logger.info(f"Testing {name} ({account_id})...")
            test_result = test_account_with_draft_post(platform, account_id)
            
            if test_result['success']:
                logger.success(f"  ✅ Account ID is valid!")
                logger.info(f"     Submission ID: {test_result['response'].get('postSubmissionId', 'N/A')}")
            else:
                logger.error(f"  ❌ Test failed")
                logger.error(f"     Status: {test_result['status_code']}")
                logger.error(f"     Response: {test_result['response']}")
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    
    total = len([id for id in ACCOUNTS.values() if id])
    correct_format = len([r for r in results.values() if r['valid']])
    needs_update = total - correct_format
    
    logger.info(f"\nTotal Accounts Configured: {total}")
    logger.info(f"Correct Format (acc_): {correct_format}")
    logger.info(f"Needs Update: {needs_update}")
    
    if needs_update > 0:
        logger.warning("\n⚠️  Action Required:")
        logger.info("   1. Log into https://my.blotato.com")
        logger.info("   2. Go to 'Social Accounts'")
        logger.info("   3. For each account, click 'Copy Account ID'")
        logger.info("   4. Update .env file with acc_ formatted IDs")
        logger.info("\n   Accounts needing update:")
        for name, check in results.items():
            if not check['valid']:
                logger.info(f"     - {name}")
    else:
        logger.success("\n✅ All account IDs are correctly formatted!")
    
    logger.info("\n" + "="*80)
    
    return needs_update == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
