"""
Pinterest & YouTube Account Testing
Tests uploads and discovers platform-specific limitations
"""
import os
import sys
from dotenv import load_dotenv
from loguru import logger
import requests
from pathlib import Path

logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")

load_dotenv()

API_KEY = os.getenv('BLOTATO_API_KEY')
BASE_URL = "https://backend.blotato.com/v2"

# Account IDs to test
PINTEREST_ACCOUNT_ID = os.getenv('PINTEREST_ACCOUNT_ID', '173')
PINTEREST_BOARD_ID = os.getenv('PINTEREST_BOARD_ID', '1139481211908910388')
YOUTUBE_ACCOUNT_ID = os.getenv('YOUTUBE_ACCOUNT_ID', '228')

class PlatformTester:
    """Test platform capabilities and limitations"""
    
    def __init__(self):
        self.headers = {
            'blotato-api-key': API_KEY,
            'Content-Type': 'application/json'
        }
        self.test_media_url = None
    
    def upload_test_media(self, media_type='image'):
        """Upload test media to Blotato"""
        logger.info("\n" + "="*80)
        logger.info("STEP 1: Upload Test Media")
        logger.info("="*80)
        
        # Use reliable test URLs
        test_urls = {
            'image': 'https://picsum.photos/1080/1920',  # 9:16 vertical image
            'video': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',  # Public Google Cloud video
        }
        
        payload = {'url': test_urls[media_type]}
        
        logger.info(f"  Uploading {media_type}: {payload['url']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/media",
                json=payload,
                headers=self.headers,
                timeout=60
            )
            
            logger.info(f"  Status: {response.status_code}")
            
            if response.status_code == 201:
                data = response.json()
                self.test_media_url = data.get('url')
                logger.success(f"  ✅ Upload successful!")
                logger.info(f"  Blotato URL: {self.test_media_url}")
                return True
            else:
                logger.error(f"  ❌ Upload failed")
                logger.error(f"  Response: {response.text[:200]}")
                return False
                
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            return False
    
    def test_pinterest(self, test_image=True, test_video=False):
        """Test Pinterest capabilities"""
        logger.info("\n" + "="*80)
        logger.info("PINTEREST TESTING (Account ID: {})".format(PINTEREST_ACCOUNT_ID))
        logger.info("="*80)
        
        # Pinterest Platform Specs
        logger.info("\n📋 Pinterest Specifications:")
        logger.info("  • Max Caption: No strict limit (but recommended ~500 chars)")
        logger.info("  • Supports: Images, Videos")
        logger.info("  • Requires: Board ID")
        logger.info("  • Optional: Title, Alt Text, Link")
        
        results = {'account_id': PINTEREST_ACCOUNT_ID, 'tests': []}
        
        # Test 1: Simple Pin with Image
        if test_image:
            logger.info("\n" + "─"*80)
            logger.info("TEST 1: Create Image Pin (Draft)")
            logger.info("─"*80)
            
            if not self.test_media_url or not self.upload_test_media('image'):
                logger.error("  ⚠️  Skipping - no media uploaded")
            else:
                payload = {
                    'post': {
                        'accountId': PINTEREST_ACCOUNT_ID,
                        'content': {
                            'text': '🧪 Test Pin from MediaPoster\n\nTesting Pinterest integration with Blotato API.\n\n#test #mediaposter',
                            'mediaUrls': [self.test_media_url],
                            'platform': 'pinterest'
                        },
                        'target': {
                            'targetType': 'pinterest',
                            'boardId': PINTEREST_BOARD_ID,
                            'title': 'Test Pin - MediaPoster Integration',
                            'altText': 'Test image for Pinterest API integration',
                            'link': 'https://example.com'
                        }
                    }
                }
                
                result = self._create_post(payload, "Pinterest Image Pin")
                results['tests'].append(result)
        
        # Test 2: Pin without optional fields
        logger.info("\n" + "─"*80)
        logger.info("TEST 2: Minimal Pin (Required Fields Only)")
        logger.info("─"*80)
        
        if self.test_media_url:
            payload = {
                'post': {
                    'accountId': PINTEREST_ACCOUNT_ID,
                    'content': {
                        'text': 'Minimal test pin',
                        'mediaUrls': [self.test_media_url],
                        'platform': 'pinterest'
                    },
                    'target': {
                        'targetType': 'pinterest',
                        'boardId': PINTEREST_BOARD_ID
                    }
                }
            }
            
            result = self._create_post(payload, "Minimal Pinterest Pin")
            results['tests'].append(result)
        
        return results
    
    def test_youtube(self, test_video=True):
        """Test YouTube Shorts capabilities"""
        logger.info("\n" + "="*80)
        logger.info("YOUTUBE SHORTS TESTING (Account ID: {})".format(YOUTUBE_ACCOUNT_ID))
        logger.info("="*80)
        
        # YouTube Platform Specs
        logger.info("\n📋 YouTube Shorts Specifications:")
        logger.info("  • Max Video Size: 256MB")
        logger.info("  • Max Duration: 60 seconds")
        logger.info("  • Aspect Ratio: 9:16 (vertical)")
        logger.info("  • Max Title: 100 characters")
        logger.info("  • Max Description: 5000 characters")
        logger.info("  • Required: title, privacyStatus, shouldNotifySubscribers")
        logger.info("  • Optional: isMadeForKids, containsSyntheticMedia")
        
        results = {'account_id': YOUTUBE_ACCOUNT_ID, 'tests': []}
        
        # Test 1: Public Short
        if test_video:
            logger.info("\n" + "─"*80)
            logger.info("TEST 1: Public YouTube Short")
            logger.info("─"*80)
            
            # Upload video for YouTube
            if not self.upload_test_media('video'):
                logger.error("  ⚠️  Skipping - video upload failed")
            else:
                payload = {
                    'post': {
                        'accountId': YOUTUBE_ACCOUNT_ID,
                        'content': {
                            'text': '🧪 Testing YouTube Shorts integration via Blotato API.\n\nThis is a test video from MediaPoster.\n\n#Shorts #Test',
                            'mediaUrls': [self.test_media_url],
                            'platform': 'youtube',
                            'title': 'Test Short - MediaPoster Integration'
                        },
                        'target': {
                            'targetType': 'youtube',
                            'title': 'Test Short - MediaPoster Integration',
                            'privacyStatus': 'public',
                            'shouldNotifySubscribers': False,
                            'isMadeForKids': False,
                            'containsSyntheticMedia': False
                        }
                    }
                }
                
                result = self._create_post(payload, "Public YouTube Short")
                results['tests'].append(result)
        
        # Test 2: Private Short
        logger.info("\n" + "─"*80)
        logger.info("TEST 2: Private YouTube Short")
        logger.info("─"*80)
        
        if self.test_media_url:
            payload = {
                'post': {
                    'accountId': YOUTUBE_ACCOUNT_ID,
                    'content': {
                        'text': 'Private test short',
                        'mediaUrls': [self.test_media_url],
                        'platform': 'youtube',
                        'title': 'Private Test - Will Not Appear Publicly'
                    },
                    'target': {
                        'targetType': 'youtube',
                        'title': 'Private Test - Will Not Appear Publicly',
                        'privacyStatus': 'private',
                        'shouldNotifySubscribers': False
                    }
                }
            }
            
            result = self._create_post(payload, "Private YouTube Short")
            results['tests'].append(result)
        
        # Test 3: Unlisted Short
        logger.info("\n" + "─"*80)
        logger.info("TEST 3: Unlisted YouTube Short")
        logger.info("─"*80)
        
        if self.test_media_url:
            payload = {
                'post': {
                    'accountId': YOUTUBE_ACCOUNT_ID,
                    'content': {
                        'text': 'Unlisted test',
                        'mediaUrls': [self.test_media_url],
                        'platform': 'youtube',
                        'title': 'Unlisted Test Short'
                    },
                    'target': {
                        'targetType': 'youtube',
                        'title': 'Unlisted Test Short',
                        'privacyStatus': 'unlisted',
                        'shouldNotifySubscribers': False
                    }
                }
            }
            
            result = self._create_post(payload, "Unlisted YouTube Short")
            results['tests'].append(result)
        
        return results
    
    def _create_post(self, payload, test_name):
        """Helper to create a post and return results"""
        logger.info(f"\n  Creating: {test_name}")
        logger.info(f"  Account ID: {payload['post']['accountId']}")
        logger.info(f"  Platform: {payload['post']['content']['platform']}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/posts",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            
            logger.info(f"  Status: {response.status_code}")
            
            if response.status_code == 201:
                data = response.json()
                submission_id = data.get('postSubmissionId')
                logger.success(f"  ✅ Post created successfully!")
                logger.info(f"  Submission ID: {submission_id}")
                logger.info(f"  Check status: https://my.blotato.com/failed")
                
                return {
                    'test': test_name,
                    'success': True,
                    'submission_id': submission_id,
                    'account_id': payload['post']['accountId']
                }
            else:
                logger.error(f"  ❌ Post creation failed")
                logger.error(f"  Response: {response.text[:300]}")
                
                return {
                    'test': test_name,
                    'success': False,
                    'error': response.text,
                    'status_code': response.status_code,
                    'account_id': payload['post']['accountId']
                }
                
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            return {
                'test': test_name,
                'success': False,
                'error': str(e),
                'account_id': payload['post']['accountId']
            }


def main():
    logger.info("\n╔" + "="*78 + "╗")
    logger.info("║" + " "*18 + "PINTEREST & YOUTUBE CAPABILITY TESTING" + " "*21 + "║")
    logger.info("╚" + "="*78 + "╝")
    
    if not API_KEY:
        logger.error("\n❌ BLOTATO_API_KEY not found")
        return False
    
    logger.info(f"\nAPI Key: {API_KEY[:25]}...")
    logger.info(f"\nAccounts to test:")
    logger.info(f"  • Pinterest: {PINTEREST_ACCOUNT_ID} (Board: {PINTEREST_BOARD_ID})")
    logger.info(f"  • YouTube: {YOUTUBE_ACCOUNT_ID}")
    
    tester = PlatformTester()
    
    # Test Pinterest
    pinterest_results = tester.test_pinterest(test_image=True)
    
    # Test YouTube
    youtube_results = tester.test_youtube(test_video=True)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("="*80)
    
    all_tests = pinterest_results['tests'] + youtube_results['tests']
    
    logger.info(f"\nTotal Tests Run: {len(all_tests)}")
    logger.info(f"Successful: {sum(1 for t in all_tests if t['success'])}")
    logger.info(f"Failed: {sum(1 for t in all_tests if not t['success'])}")
    
    logger.info("\n📊 Detailed Results:")
    for test in all_tests:
        status = "✅" if test['success'] else "❌"
        logger.info(f"\n  {status} {test['test']}")
        logger.info(f"     Account: {test['account_id']}")
        if test['success']:
            logger.info(f"     Submission ID: {test.get('submission_id')}")
        else:
            logger.info(f"     Error: {test.get('error', 'Unknown')[:100]}")
    
    logger.info("\n" + "="*80)
    logger.info("NEXT STEPS")
    logger.info("="*80)
    
    if any(t['success'] for t in all_tests):
        logger.success("\n✅ Some posts were created successfully!")
        logger.info("\n📋 To view posts:")
        logger.info("  • Check Blotato dashboard: https://my.blotato.com")
        logger.info("  • Failed posts: https://my.blotato.com/failed")
        logger.info("  • Posts are queued and will publish shortly")
    else:
        logger.warning("\n⚠️  No posts were created successfully")
        logger.info("\n💡 Common issues:")
        logger.info("  • Account IDs may need to be in acc_ format")
        logger.info("  • Check if accounts are properly connected in Blotato")
        logger.info("  • Verify board ID for Pinterest")
    
    logger.info("\n" + "="*80)
    
    return any(t['success'] for t in all_tests)


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
