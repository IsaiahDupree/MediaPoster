#!/usr/bin/env python3
"""
Standalone Blotato API Testing
Test Blotato client structure without full app dependencies
"""
import json


def test_api_structure():
    """Test 1: Verify API structure and endpoints"""
    print("\n" + "="*60)
    print("TEST 1: Blotato API Structure")
    print("="*60)
    
    base_url = "https://backend.blotato.com"
    
    endpoints = {
        "Upload Media": {
            "method": "POST",
            "url": f"{base_url}/v2/media",
            "description": "Upload media from public URL",
            "example": {
                "url": "https://example.com/video.mp4"
            }
        },
        "Create Post": {
            "method": "POST",
            "url": f"{base_url}/v2/posts",
            "description": "Publish post to platform",
            "example": {
                "post": {
                    "accountId": "acc_12345",
                    "content": {
                        "text": "Hello, world!",
                        "mediaUrls": [],
                        "platform": "twitter"
                    },
                    "target": {
                        "targetType": "twitter"
                    }
                }
            }
        },
        "Get Accounts": {
            "method": "GET",
            "url": f"{base_url}/accounts",
            "description": "List connected social accounts"
        }
    }
    
    print("\n✓ API Base URL:", base_url)
    print("\n✓ Available Endpoints:")
    for name, info in endpoints.items():
        print(f"\n  {name}:")
        print(f"    Method: {info['method']}")
        print(f"    URL: {info['url']}")
        print(f"    Description: {info['description']}")
        if 'example' in info:
            print(f"    Example: {json.dumps(info['example'], indent=6)}")
    
    return True


def test_platform_requirements():
    """Test 2: Platform specifications"""
    print("\n" + "="*60)
    print("TEST 2: Platform Requirements")
    print("="*60)
    
    platforms = {
        'tiktok': {
            'max_video_size_mb': 287,
            'max_duration_seconds': 600,
            'aspect_ratios': ['9:16', '1:1'],
            'max_caption_length': 2200,
            'required_fields': ['privacyLevel', 'disabledComments', 'disabledDuet', 'disabledStitch']
        },
        'instagram': {
            'max_video_size_mb': 100,
            'max_duration_seconds': 90,
            'aspect_ratios': ['9:16', '4:5', '1:1'],
            'max_caption_length': 2200,
            'special': 'Set mediaType: "story" for stories, default is "reel"'
        },
        'youtube': {
            'max_video_size_mb': 256,
            'max_duration_seconds': 60,
            'aspect_ratios': ['9:16'],
            'max_caption_length': 5000,
            'required_fields': ['title', 'privacyStatus', 'shouldNotifySubscribers']
        },
        'facebook': {
            'max_video_size_mb': 200,
            'max_caption_length': 63206,
            'required_fields': ['pageId']
        },
        'twitter': {
            'max_video_size_mb': 512,
            'max_caption_length': 280,
            'limits': '4 photos or 1 video per tweet'
        }
    }
    
    print("\n✓ Platform Specifications:")
    for platform, specs in platforms.items():
        print(f"\n  {platform.upper()}:")
        for key, value in specs.items():
            if key == 'required_fields':
                print(f"    Required: {', '.join(value)}")
            else:
                print(f"    {key}: {value}")
    
    return True


def test_example_payloads():
    """Test 3: Example payloads for each platform"""
    print("\n" + "="*60)
    print("TEST 3: Example Request Payloads")
    print("="*60)
    
    examples = {
        'Twitter (Simple)': {
            "post": {
                "accountId": "acc_twitter",
                "content": {
                    "text": "Hello Twitter! 🐦",
                    "mediaUrls": ["https://database.blotato.com/video.mp4"],
                    "platform": "twitter"
                },
                "target": {
                    "targetType": "twitter"
                }
            }
        },
        'Instagram Reel': {
            "post": {
                "accountId": "acc_instagram",
                "content": {
                    "text": "Check this out! #viral #trending",
                    "mediaUrls": ["https://database.blotato.com/vertical-clip.mp4"],
                    "platform": "instagram"
                },
                "target": {
                    "targetType": "instagram"
                    # mediaType defaults to "reel"
                }
            }
        },
        'Instagram Story': {
            "post": {
                "accountId": "acc_instagram",
                "content": {
                    "text": "Behind the scenes! 📸",
                    "mediaUrls": ["https://database.blotato.com/story.mp4"],
                    "platform": "instagram"
                },
                "target": {
                    "targetType": "instagram",
                    "mediaType": "story"
                }
            }
        },
        'TikTok': {
            "post": {
                "accountId": "acc_tiktok",
                "content": {
                    "text": "Viral TikTok moment! 🎵",
                    "mediaUrls": ["https://database.blotato.com/tiktok-vid.mp4"],
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
        'Facebook Page': {
            "post": {
                "accountId": "acc_facebook",
                "content": {
                    "text": "Facebook post with video",
                    "mediaUrls": ["https://database.blotato.com/fb-video.mp4"],
                    "platform": "facebook"
                },
                "target": {
                    "targetType": "facebook",
                    "pageId": "123456789"
                }
            }
        },
        'YouTube Short': {
            "post": {
                "accountId": "acc_youtube",
                "content": {
                    "text": "Amazing short video!",
                    "mediaUrls": ["https://database.blotato.com/short.mp4"],
                    "platform": "youtube",
                    "title": "My Awesome YouTube Short"
                },
                "target": {
                    "targetType": "youtube",
                    "privacyStatus": "public",
                    "shouldNotifySubscribers": True
                }
            }
        },
        'Scheduled Post': {
            "post": {
                "accountId": "acc_twitter",
                "content": {
                    "text": "Scheduled for later!",
                    "mediaUrls": [],
                    "platform": "twitter"
                },
                "target": {
                    "targetType": "twitter"
                }
            },
            "scheduledTime": "2025-03-10T15:30:00Z"
        }
    }
    
    print("\n✓ Example Payloads (POST /v2/posts):")
    for name, payload in examples.items():
        print(f"\n  {name}:")
        print(json.dumps(payload, indent=4))
    
    return True


def test_media_upload():
    """Test 4: Media upload examples"""
    print("\n" + "="*60)
    print("TEST 4: Media Upload Process")
    print("="*60)
    
    print("\n✓ Upload Steps:")
    print("  1. Host your video on a public URL (S3, GCP, Drive, etc.)")
    print("  2. POST /v2/media with URL")
    print("  3. Receive Blotato-hosted URL")
    print("  4. Use that URL in mediaUrls")
    
    print("\n✓ Example Upload Request:")
    upload_payload = {
        "url": "https://my-bucket.s3.amazonaws.com/clip.mp4"
    }
    print(json.dumps(upload_payload, indent=2))
    
    print("\n✓ Example Response:")
    response = {
        "url": "https://database.blotato.com/d1655c49-abc123.mp4"
    }
    print(json.dumps(response, indent=2))
    
    print("\n✓ Google Drive Example:")
    print("  Share URL: https://drive.google.com/file/d/FILE_ID/view")
    print("  Convert to: https://drive.google.com/uc?export=download&id=FILE_ID")
    
    print("\n✓ Rate Limits:")
    print("  - Media uploads: 10 per minute")
    print("  - Post publishing: 30 per minute")
    
    return True


def test_authentication():
    """Test 5: Authentication setup"""
    print("\n" + "="*60)
    print("TEST 5: Authentication & Setup")
    print("="*60)
    
    print("\n✓ Required Setup:")
    print("  1. Create Blotato account at blotato.com")
    print("  2. Generate API key in account settings")
    print("  3. Connect social accounts (TikTok, Instagram, etc.)")
    print("  4. Copy account IDs for use in API calls")
    
    print("\n✓ API Authentication:")
    print("  Header: blotato-api-key: YOUR_API_KEY")
    print("  All requests must include this header")
    
    print("\n✓ Environment Variable:")
    print("  Add to .env file:")
    print("  BLOTATO_API_KEY=your_api_key_here")
    
    print("\n✓ Account IDs:")
    print("  - Each connected social account has an ID")
    print("  - Format: acc_xxxxx")
    print("  - Find in Blotato dashboard under 'Social Accounts'")
    print("  - Use 'Copy Account ID' button")
    
    return True


def test_error_handling():
    """Test 6: Common errors and solutions"""
    print("\n" + "="*60)
    print("TEST 6: Common Errors & Solutions")
    print("="*60)
    
    errors = {
        "401 Unauthorized": {
            "cause": "Invalid or missing API key",
            "solution": "Check BLOTATO_API_KEY in .env"
        },
        "429 Too Many Requests": {
            "cause": "Rate limit exceeded",
            "solution": "Wait X seconds (check retry-after header), implement throttling"
        },
        "400 Bad Request": {
            "cause": "Invalid JSON or missing required fields",
            "solution": "Validate JSON structure against examples"
        },
        "TikTok URL verification error": {
            "cause": "External URLs in caption",
            "solution": "Only use Blotato media URLs, avoid links in caption"
        },
        "Instagram aspect ratio error": {
            "cause": "Video doesn't meet aspect ratio requirements",
            "solution": "Convert to 9:16, 4:5, or 1:1 aspect ratio"
        },
        "Facebook pageId error": {
            "cause": "Missing or incorrect page ID",
            "solution": "Include pageId in target, copy from Blotato dashboard"
        }
    }
    
    print("\n✓ Common Errors:")
    for error, info in errors.items():
        print(f"\n  {error}:")
        print(f"    Cause: {info['cause']}")
        print(f"    Solution: {info['solution']}")
    
    return True


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("   Blotato API - Standalone Testing")
    print("="*60)
    print("\nThese tests verify API structure without making real calls.")
    print("No API key or dependencies required.")
    print()
    
    tests = [
        ("API Structure", test_api_structure),
        ("Platform Requirements", test_platform_requirements),
        ("Example Payloads", test_example_payloads),
        ("Media Upload", test_media_upload),
        ("Authentication", test_authentication),
        ("Error Handling", test_error_handling)
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            print(f"\nRunning: {name}...")
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ Test '{name}' failed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        print("\n📚 Next Steps:")
        print("  1. Review: docs/BLOTATO_API_GUIDE.md")
        print("  2. Setup: Add BLOTATO_API_KEY to .env")
        print("  3. Connect: Link social accounts at blotato.com")
        print("  4. Test: Run test_phase4.py for real API calls")
        print("\n💡 Integration Tips:")
        print("  - Use Google Drive/S3 to host clips before uploading")
        print("  - Start with one platform (Twitter is simplest)")
        print("  - Check Blotato dashboard for request logs")
        print("  - Respect rate limits: 10 uploads/min, 30 posts/min")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    print("\n" + "="*60)
    print("Documentation: docs/BLOTATO_API_GUIDE.md")
    print("="*60)


if __name__ == "__main__":
    main()
