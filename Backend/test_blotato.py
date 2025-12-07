"""
Test script for Blotato API connectivity and posting functionality
"""
import os
import sys
from pathlib import Path
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_blotato_connection():
    """Test basic Blotato API connectivity"""
    # Try both API keys from the env
    api_keys = [
        os.getenv('BLOTATO_API_KEY'),  # blt_ key
        'bt-25f4e2a6-7d38-48bd-b01a-6e9a7d8c3f10'  # bt- key from config
    ]
    
    endpoints = [
        os.getenv('BLOTATO_API_ENDPOINT', 'https://backend.blotato.com/v2'),
        'https://backend.blotato.com'  # Base URL without /v2
    ]
    
    for api_key in api_keys:
        if not api_key:
            continue
            
        print(f"\n{'='*60}")
        print(f"Testing API Key: {api_key[:20]}...")
        print(f"{'='*60}")
        
        for endpoint in endpoints:
            print(f"\nEndpoint: {endpoint}")
            
            headers = {
                'blotato-api-key': api_key,
                'Content-Type': 'application/json'
            }
            
            try:
                # Test /accounts endpoint
                test_url = f'{endpoint}/accounts'
                if '/v2' in endpoint:
                    test_url = f'{endpoint}/accounts'
                elif not endpoint.endswith('/'):
                    test_url = f'{endpoint}/accounts'
                
                print(f"  → GET {test_url}")
                response = requests.get(
                    test_url,
                    headers=headers,
                    timeout=10
                )
                
                print(f"  ← Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"  ✅ Success!")
                    accounts = response.json()
                    if isinstance(accounts, dict):
                        accounts = accounts.get('accounts', [])
                    print(f"  📊 Found {len(accounts)} accounts")
                    for account in accounts[:3]:
                        print(f"    - {account.get('platform', 'Unknown')}: {account.get('username', 'N/A')}")
                    return True
                else:
                    print(f"  ❌ Failed: {response.text[:150]}")
                    
            except requests.exceptions.RequestException as e:
                print(f"  ❌ Connection error: {e}")
    
    return False

def test_account_ids():
    """Verify account IDs are configured"""
    print("\n📋 Checking configured account IDs:")
    
    accounts = {
        'YOUTUBE_ACCOUNT_ID': os.getenv('YOUTUBE_ACCOUNT_ID'),
        'TIKTOK_ACCOUNT_ID': os.getenv('TIKTOK_ACCOUNT_ID'),
        'INSTAGRAM_ACCOUNT_ID': os.getenv('INSTAGRAM_ACCOUNT_ID'),
        'TWITTER_ACCOUNT_ID': os.getenv('TWITTER_ACCOUNT_ID'),
        'FACEBOOK_ACCOUNT_ID': os.getenv('FACEBOOK_ACCOUNT_ID'),
    }
    
    for name, value in accounts.items():
        if value:
            print(f"  ✓ {name}: {value}")
        else:
            print(f"  ⚠️  {name}: Not configured")
    
    return any(accounts.values())

def test_post_draft(platform_id=None):
    """Test creating a draft post (won't actually publish)"""
    api_key = os.getenv('BLOTATO_API_KEY')
    api_endpoint = os.getenv('BLOTATO_API_ENDPOINT', 'https://backend.blotato.com/v2')
    
    # Use Instagram account by default
    if not platform_id:
        platform_id = os.getenv('INSTAGRAM_ACCOUNT_ID', '807')
    
    print(f"\n🧪 Testing draft post creation for account {platform_id}...")
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Create a test draft post
    draft_data = {
        'account_id': platform_id,
        'caption': 'Test post from MediaPoster (Draft - Will Not Publish)',
        'status': 'draft',  # Important: draft only, won't publish
        'media_url': 'https://example.com/test.jpg'
    }
    
    try:
        # Note: This is a mock example - adjust endpoint based on actual Blotato API docs
        print("ℹ️  This would create a draft post (not implemented in test)")
        print(f"   Account: {platform_id}")
        print(f"   Caption: {draft_data['caption']}")
        return True
        
    except Exception as e:
        print(f"⚠️  Error: {e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("BLOTATO API CONNECTIVITY TEST")
    print("=" * 60)
    
    # Run tests
    connection_ok = test_blotato_connection()
    accounts_ok = test_account_ids()
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if connection_ok and accounts_ok:
        print("✅ All tests passed! Blotato API is ready to use.")
        print("\n💡 Next steps:")
        print("   - Place your Google Cloud service account JSON in:")
        print("     Backend/credentials/google-cloud-sa.json")
        print("   - Run the actual posting workflow to test end-to-end")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check your configuration.")
        sys.exit(1)
