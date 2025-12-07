"""
Comprehensive All-Account Testing Suite
Tests all configured Blotato accounts and provides detailed status report
"""
import os
import sys
from dotenv import load_dotenv
from loguru import logger
import requests
from datetime import datetime
import json

logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")

load_dotenv()

API_KEY = os.getenv('BLOTATO_API_KEY')
BASE_URL = "https://backend.blotato.com/v2"

# All configured accounts
ACCOUNTS = {
    'YouTube': {'id': os.getenv('YOUTUBE_ACCOUNT_ID', '228'), 'platform': 'youtube'},
    'TikTok': {'id': os.getenv('TIKTOK_ACCOUNT_ID', '710'), 'platform': 'tiktok'},
    'Instagram': {'id': os.getenv('INSTAGRAM_ACCOUNT_ID', '807'), 'platform': 'instagram'},
    'Instagram (Alt 1)': {'id': os.getenv('INSTAGRAM_ACCOUNT_ID_ALT', '670'), 'platform': 'instagram'},
    'Instagram (Alt 2)': {'id': os.getenv('INSTAGRAM_ACCOUNT_ID_ALT_2', '1369'), 'platform': 'instagram'},
    'Instagram (Alt 3)': {'id': os.getenv('INSTAGRAM_ACCOUNT_ID_ALT_3', '2308'), 'platform': 'instagram'},
    'Twitter': {'id': os.getenv('TWITTER_ACCOUNT_ID', '571'), 'platform': 'twitter'},
    'Facebook': {'id': os.getenv('FACEBOOK_ACCOUNT_ID', '786'), 'platform': 'facebook'},
    'Pinterest': {'id': os.getenv('PINTEREST_ACCOUNT_ID', '173'), 'platform': 'pinterest'},
    'Bluesky': {'id': os.getenv('BLUESKY_ACCOUNT_ID', '2'), 'platform': 'bluesky'},
    'Threads': {'id': os.getenv('THREADS_ACCOUNT_ID', '243'), 'platform': 'threads'},
}

headers = {
    'blotato-api-key': API_KEY,
    'Content-Type': 'application/json'
}

class AccountTester:
    """Test individual accounts"""
    
    def __init__(self):
        self.test_media_url = None
        self.results = []
    
    def upload_test_media(self):
        """Upload test video once for all tests"""
        if self.test_media_url:
            return self.test_media_url
        
        logger.info("\n📤 Uploading test media...")
        
        # Use compliant test video
        test_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
        
        try:
            response = requests.post(
                f"{BASE_URL}/media",
                json={'url': test_url},
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 201:
                data = response.json()
                self.test_media_url = data.get('url')
                logger.success(f"✅ Media uploaded: {self.test_media_url[:60]}...")
                return self.test_media_url
            else:
                logger.error(f"❌ Upload failed: {response.text[:100]}")
                return None
        except Exception as e:
            logger.error(f"❌ Upload error: {e}")
            return None
    
    def test_account(self, name, account_info):
        """Test posting to a single account"""
        account_id = account_info['id']
        platform = account_info['platform']
        
        logger.info(f"\n{'─'*80}")
        logger.info(f"Testing: {name}")
        logger.info(f"Account ID: {account_id} | Platform: {platform}")
        logger.info(f"{'─'*80}")
        
        if not account_id:
            return self._record_result(name, account_id, platform, False, "Not configured", None, None)
        
        # Build platform-specific payload
        payload = self._build_payload(account_id, platform)
        
        if not payload:
            return self._record_result(name, account_id, platform, False, "Unsupported platform config", None, None)
        
        # Attempt to create post
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
                submission_id = data.get('postSubmissionId')
                logger.success(f"  ✅ POST CREATED!")
                logger.info(f"  Submission ID: {submission_id}")
                return self._record_result(name, account_id, platform, True, "Success", submission_id, None)
            else:
                error_msg = response.text[:200]
                logger.error(f"  ❌ FAILED")
                logger.error(f"  Error: {error_msg}")
                
                # Categorize error
                category = self._categorize_error(error_msg)
                return self._record_result(name, account_id, platform, False, category, None, error_msg)
                
        except Exception as e:
            logger.error(f"  ❌ Exception: {e}")
            return self._record_result(name, account_id, platform, False, "Network error", None, str(e))
    
    def _build_payload(self, account_id, platform):
        """Build platform-specific post payload"""
        if not self.test_media_url:
            return None
        
        base_content = {
            'text': f'Test post from MediaPoster - {platform} integration test',
            'mediaUrls': [self.test_media_url],
            'platform': platform
        }
        
        # Platform-specific configurations
        targets = {
            'youtube': {
                'targetType': 'youtube',
                'title': 'MediaPoster Test',
                'privacyStatus': 'unlisted',
                'shouldNotifySubscribers': False
            },
            'tiktok': {
                'targetType': 'tiktok',
                'privacyLevel': 'SELF_ONLY',
                'disabledComments': True,
                'disabledDuet': True,
                'disabledStitch': True,
                'isBrandedContent': False,
                'isYourBrand': False,
                'isAiGenerated': False,
                'isDraft': True
            },
            'instagram': {
                'targetType': 'instagram',
                'mediaType': 'reel'
            },
            'twitter': {
                'targetType': 'twitter'
            },
            'facebook': {
                'targetType': 'facebook',
                'pageId': os.getenv('FACEBOOK_PAGE_ID')
            },
            'pinterest': {
                'targetType': 'pinterest',
                'boardId': os.getenv('PINTEREST_BOARD_ID', '0')
            },
            'threads': {
                'targetType': 'threads'
            },
            'bluesky': {
                'targetType': 'bluesky'
            }
        }
        
        target = targets.get(platform)
        if not target:
            return None
        
        # Add title for YouTube
        if platform == 'youtube':
            base_content['title'] = 'MediaPoster Test'
        
        return {
            'post': {
                'accountId': account_id,
                'content': base_content,
                'target': target
            }
        }
    
    def _categorize_error(self, error_msg):
        """Categorize error for reporting"""
        error_lower = error_msg.lower()
        
        if 'unauthorized' in error_lower or '401' in error_msg:
            return "Needs reconnection"
        elif 'restricted' in error_lower or 'verification' in error_lower:
            return "Restricted - needs verification"
        elif 'wrong account' in error_lower or 'account id' in error_lower:
            return "Invalid account ID"
        elif 'page id' in error_lower:
            return "Missing/invalid page ID"
        elif 'rate limit' in error_lower or '429' in error_msg:
            return "Rate limited"
        elif 'invalid' in error_lower:
            return "Invalid configuration"
        else:
            return "Unknown error"
    
    def _record_result(self, name, account_id, platform, success, status, submission_id, error):
        """Record test result"""
        result = {
            'name': name,
            'account_id': account_id,
            'platform': platform,
            'success': success,
            'status': status,
            'submission_id': submission_id,
            'error': error,
            'tested_at': datetime.now().isoformat()
        }
        self.results.append(result)
        return result
    
    def generate_report(self):
        """Generate comprehensive test report"""
        logger.info("\n" + "="*80)
        logger.info("COMPREHENSIVE ACCOUNT TEST REPORT")
        logger.info("="*80)
        
        total = len(self.results)
        successful = sum(1 for r in self.results if r['success'])
        failed = total - successful
        
        logger.info(f"\nTotal Accounts Tested: {total}")
        logger.info(f"Successful: {successful} ({successful/total*100:.1f}%)")
        logger.info(f"Failed: {failed} ({failed/total*100:.1f}%)")
        
        # Group by status
        logger.info("\n" + "─"*80)
        logger.info("RESULTS BY STATUS")
        logger.info("─"*80)
        
        # Successful accounts
        success_results = [r for r in self.results if r['success']]
        if success_results:
            logger.success(f"\n✅ WORKING ACCOUNTS ({len(success_results)}):")
            for r in success_results:
                logger.info(f"  • {r['name']} ({r['account_id']})")
                logger.info(f"    Submission: {r['submission_id']}")
        
        # Failed accounts by category
        failed_results = [r for r in self.results if not r['success']]
        if failed_results:
            # Group by status
            by_status = {}
            for r in failed_results:
                status = r['status']
                if status not in by_status:
                    by_status[status] = []
                by_status[status].append(r)
            
            for status, results in by_status.items():
                logger.warning(f"\n⚠️  {status.upper()} ({len(results)}):")
                for r in results:
                    logger.info(f"  • {r['name']} ({r['account_id']})")
                    if r['error']:
                        logger.info(f"    Error: {r['error'][:100]}")
        
        # Actionable items
        logger.info("\n" + "="*80)
        logger.info("ACTIONABLE ITEMS")
        logger.info("="*80)
        
        needs_reconnect = [r for r in failed_results if 'reconnection' in r['status'].lower()]
        needs_verification = [r for r in failed_results if 'verification' in r['status'].lower()]
        config_issues = [r for r in failed_results if 'invalid' in r['status'].lower() or 'page id' in r['status'].lower()]
        
        if needs_reconnect:
            logger.warning(f"\n🔌 {len(needs_reconnect)} account(s) need reconnection:")
            for r in needs_reconnect:
                logger.info(f"  • {r['name']} - Log into Blotato and reconnect")
        
        if needs_verification:
            logger.warning(f"\n✉️  {len(needs_verification)} account(s) need verification:")
            for r in needs_verification:
                logger.info(f"  • {r['name']} - Email help@blotato.com for verification")
        
        if config_issues:
            logger.warning(f"\n⚙️  {len(config_issues)} account(s) have config issues:")
            for r in config_issues:
                logger.info(f"  • {r['name']} - {r['status']}")
        
        # Save report to file
        report_file = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        logger.info(f"\n📄 Detailed report saved to: {report_file}")
        logger.info("="*80)
        
        return self.results

def main():
    logger.info("\n╔" + "="*78 + "╗")
    logger.info("║" + " "*22 + "ALL-ACCOUNT TESTING SUITE" + " "*31 + "║")
    logger.info("╚" + "="*78 + "╝")
    
    if not API_KEY:
        logger.error("\n❌ BLOTATO_API_KEY not found")
        return False
    
    tester = AccountTester()
    
    # Upload media once
    if not tester.upload_test_media():
        logger.error("\n❌ Failed to upload test media - cannot continue")
        return False
    
    # Test all accounts
    logger.info(f"\n🧪 Testing {len(ACCOUNTS)} accounts...\n")
    
    for name, info in ACCOUNTS.items():
        tester.test_account(name, info)
    
    # Generate report
    results = tester.generate_report()
    
    # Return success if at least some accounts worked
    return any(r['success'] for r in results)

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
