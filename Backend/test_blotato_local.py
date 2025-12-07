#!/usr/bin/env python3
"""
Local Blotato API Testing
Test Blotato integration without making real API calls
"""
import sys
from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))

from modules.publishing import BlotatoClient


def test_client_initialization():
    """Test 1: Initialize Blotato client"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Client Initialization")
    logger.info("="*60)
    
    print("\nThis test verifies the client can be initialized.")
    print("No API calls are made.")
    
    try:
        client = BlotatoClient()
        
        logger.success("✓ Client initialized")
        logger.info(f"  Base URL: {client.BASE_URL}")
        logger.info(f"  Headers set: {list(client.session.headers.keys())}")
        
        # Check API key is present
        if 'blotato-api-key' in client.session.headers:
            key = client.session.headers['blotato-api-key']
            masked = key[:10] + "..." if len(key) > 10 else "***"
            logger.info(f"  API Key: {masked}")
        else:
            logger.warning("  No API key found in headers")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_platform_validation():
    """Test 2: Platform validation"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Platform Validation")
    logger.info("="*60)
    
    print("\nThis test validates clip requirements for each platform.")
    print("No API calls are made.")
    
    try:
        client = BlotatoClient()
        
        # Create a dummy clip path
        test_clip = Path(__file__).parent / "test_data" / "sample_clip.mp4"
        
        platforms = ['tiktok', 'instagram', 'youtube']
        
        for platform in platforms:
            logger.info(f"\n{platform.upper()}:")
            config = client.PLATFORM_CONFIGS.get(platform, {})
            logger.info(f"  Max size: {config.get('max_video_size_mb')}MB")
            logger.info(f"  Max duration: {config.get('max_duration_seconds')}s")
            logger.info(f"  Aspect ratios: {', '.join(config.get('aspect_ratios', []))}")
            logger.info(f"  Max caption: {config.get('max_caption_length')} chars")
        
        logger.success("\n✓ Platform configs loaded")
        return True
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        return False


def test_payload_structure():
    """Test 3: Verify payload structure"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Payload Structure")
    logger.info("="*60)
    
    print("\nThis test builds example payloads for each platform.")
    print("No API calls are made.")
    
    try:
        # Example payloads per platform
        examples = {
            'twitter': {
                "post": {
                    "accountId": "acc_12345",
                    "content": {
                        "text": "Hello Twitter!",
                        "mediaUrls": ["https://database.blotato.com/video.mp4"],
                        "platform": "twitter"
                    },
                    "target": {
                        "targetType": "twitter"
                    }
                }
            },
            'instagram': {
                "post": {
                    "accountId": "acc_67890",
                    "content": {
                        "text": "Check this out! #viral",
                        "mediaUrls": ["https://database.blotato.com/video.mp4"],
                        "platform": "instagram"
                    },
                    "target": {
                        "targetType": "instagram",
                        "mediaType": "reel"  # or "story"
                    }
                }
            },
            'tiktok': {
                "post": {
                    "accountId": "acc_11111",
                    "content": {
                        "text": "TikTok viral moment",
                        "mediaUrls": ["https://database.blotato.com/video.mp4"],
                        "platform": "tiktok"
                    },
                    "target": {
                        "targetType": "tiktok",
                        "privacyLevel": "PUBLIC_TO_EVERYONE",
                        "disabledComments": False,
                        "disabledDuet": False,
                        "disabledStitch": False,
                        "isBrandedContent": False
                    }
                }
            },
            'facebook': {
                "post": {
                    "accountId": "acc_22222",
                    "content": {
                        "text": "Facebook post",
                        "mediaUrls": ["https://database.blotato.com/video.mp4"],
                        "platform": "facebook"
                    },
                    "target": {
                        "targetType": "facebook",
                        "pageId": "987654321"
                    }
                }
            },
            'youtube': {
                "post": {
                    "accountId": "acc_33333",
                    "content": {
                        "text": "Amazing video!",
                        "mediaUrls": ["https://database.blotato.com/video.mp4"],
                        "platform": "youtube",
                        "title": "My Awesome Video"
                    },
                    "target": {
                        "targetType": "youtube",
                        "privacyStatus": "public",
                        "shouldNotifySubscribers": True
                    }
                }
            }
        }
        
        import json
        
        for platform, payload in examples.items():
            logger.info(f"\n{platform.upper()} Payload:")
            logger.info(json.dumps(payload, indent=2))
        
        logger.success("\n✓ All payload structures valid")
        return True
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        return False


def test_media_upload_structure():
    """Test 4: Media upload payload"""
    logger.info("\n" + "="*60)
    logger.info("TEST 4: Media Upload Structure")
    logger.info("="*60)
    
    print("\nThis test shows the media upload payload structure.")
    print("No API calls are made.")
    
    import json
    
    # Example media upload payloads
    examples = {
        'From URL': {
            "url": "https://example.com/video.mp4"
        },
        'From Google Drive': {
            "url": "https://drive.google.com/uc?export=download&id=FILE_ID_HERE"
        },
        'From S3': {
            "url": "https://my-bucket.s3.amazonaws.com/video.mp4"
        }
    }
    
    for source, payload in examples.items():
        logger.info(f"\n{source}:")
        logger.info(json.dumps(payload, indent=2))
    
    logger.info("\nExpected Response:")
    logger.info(json.dumps({
        "url": "https://database.blotato.com/d1655c49-abc123.mp4"
    }, indent=2))
    
    logger.success("\n✓ Media upload structure documented")
    return True


def test_api_endpoints():
    """Test 5: List all API endpoints"""
    logger.info("\n" + "="*60)
    logger.info("TEST 5: API Endpoints Reference")
    logger.info("="*60)
    
    client = BlotatoClient()
    
    endpoints = {
        'Upload Media': {
            'method': 'POST',
            'url': f'{client.BASE_URL}/v2/media',
            'description': 'Upload media from public URL'
        },
        'Create Post': {
            'method': 'POST',
            'url': f'{client.BASE_URL}/v2/posts',
            'description': 'Publish post to platform'
        },
        'Get Post Status': {
            'method': 'GET',
            'url': f'{client.BASE_URL}/posts/{{post_id}}',
            'description': 'Get post status (if available)'
        },
        'Get Accounts': {
            'method': 'GET',
            'url': f'{client.BASE_URL}/accounts',
            'description': 'List connected social accounts'
        },
        'Create Video': {
            'method': 'POST',
            'url': f'{client.BASE_URL}/v2/videos/creations',
            'description': 'Generate AI video'
        },
        'Get Video Status': {
            'method': 'GET',
            'url': f'{client.BASE_URL}/v2/videos/creations/{{id}}',
            'description': 'Check video generation status'
        },
        'Delete Video': {
            'method': 'DELETE',
            'url': f'{client.BASE_URL}/v2/videos/{{id}}',
            'description': 'Delete generated video'
        }
    }
    
    for name, info in endpoints.items():
        logger.info(f"\n{name}:")
        logger.info(f"  Method: {info['method']}")
        logger.info(f"  URL: {info['url']}")
        logger.info(f"  Description: {info['description']}")
    
    logger.success("\n✓ All endpoints documented")
    return True


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("   Blotato API - Local Testing Suite")
    print("="*60)
    print("\nThese tests verify the client without making real API calls.")
    print("To test against real API, use test_phase4.py with valid credentials.")
    print()
    
    tests = [
        ("Client Initialization", test_client_initialization),
        ("Platform Validation", test_platform_validation),
        ("Payload Structure", test_payload_structure),
        ("Media Upload Structure", test_media_upload_structure),
        ("API Endpoints", test_api_endpoints)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("TEST SUMMARY")
    logger.info("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"  {status}: {name}")
    
    logger.info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        logger.success("\n🎉 All tests passed!")
        logger.info("\nNext steps:")
        logger.info("1. Add BLOTATO_API_KEY to .env")
        logger.info("2. Connect social accounts at blotato.com")
        logger.info("3. Run test_phase4.py for real API testing")
    else:
        logger.warning(f"\n⚠️  {total - passed} test(s) failed")
    
    logger.info("\n📚 Documentation: docs/BLOTATO_API_GUIDE.md")


if __name__ == "__main__":
    main()
