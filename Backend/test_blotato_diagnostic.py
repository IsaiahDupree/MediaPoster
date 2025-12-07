"""
Quick Blotato API diagnostic test
Tests multiple authentication methods and endpoints
"""
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('BLOTATO_API_KEY')

print("\n" + "="*80)
print("BLOTATO API DIAGNOSTIC TEST")
print("="*80)
print(f"\nAPI Key: {API_KEY[:25]}...")

# Test different combinations
test_configs = [
    {
        "name": "v2 endpoint with blotato-api-key header",
        "url": "https://backend.blotato.com/v2/accounts",
        "headers": {"blotato-api-key": API_KEY}
    },
    {
        "name": "Base endpoint with blotato-api-key header", 
        "url": "https://backend.blotato.com/accounts",
        "headers": {"blotato-api-key": API_KEY}
    },
    {
        "name": "v2 endpoint with Authorization Bearer",
        "url": "https://backend.blotato.com/v2/accounts",
        "headers": {"Authorization": f"Bearer {API_KEY}"}
    },
    {
        "name": "v2 endpoint with x-api-key header",
        "url": "https://backend.blotato.com/v2/accounts",
        "headers": {"x-api-key": API_KEY}
    },
    {
        "name": "Base /api/accounts with blotato-api-key",
        "url": "https://backend.blotato.com/api/accounts",
        "headers": {"blotato-api-key": API_KEY}
    },
]

for config in test_configs:
    print(f"\n{'─'*80}")
    print(f"Testing: {config['name']}")
    print(f"URL: {config['url']}")
    print(f"Headers: {list(config['headers'].keys())}")
    
    try:
        response = requests.get(
            config['url'],
            headers=config['headers'],
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SUCCESS!")
            try:
                data = response.json()
                print(f"Response: {data}")
            except:
                print(f"Response: {response.text[:200]}")
            break
        else:
            print(f"Response: {response.text[:150]}")
            
    except Exception as e:
        print(f"Error: {e}")

print("\n" + "="*80)
print("\n💡 If all tests fail with 401:")
print("  1. Verify API key is correct in Blotato dashboard")
print("  2. Check if key has required permissions")
print("  3. Try generating a new API key")
print("  4. Contact Blotato support if issue persists")
