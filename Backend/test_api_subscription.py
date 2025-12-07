"""
Quick API Test Script

Simple script to test if the RapidAPI TikTok Captcha Solver subscription is active.
"""

import asyncio
import os
from dotenv import load_dotenv
import aiohttp

load_dotenv()

async def test_api_subscription():
    """Check if RapidAPI subscription is active."""
    
    api_key = os.getenv("RAPIDAPI_KEY")
    
    if not api_key:
        print("❌ RAPIDAPI_KEY not found in environment")
        return False
    
    print(f"✅ API Key found: {api_key[:20]}...")
    
    # Test URL from the API documentation
    test_url = "https://p19-rc-captcha-va.ibyteimg.com/tos-maliva-i-b4yrtqhy5a-us/3d_2385_8c09f6e7854724719b59d73732791824b8e49385_1.jpg~tplv-b4yrtqhy5a-3.webp"
    
    payload = {
        "b64External_or_url": test_url,
        "width": "348",
        "height": "216",
        "version": "2",
        "proxy": ""
    }
    
    headers = {
        "Content-Type": "application/json",
        "x-rapidapi-host": "tiktok-captcha-solver6.p.rapidapi.com",
        "x-rapidapi-key": api_key
    }
    
    endpoint = "https://tiktok-captcha-solver6.p.rapidapi.com/3d"
    
    print(f"\n🔍 Testing API endpoint: {endpoint}")
    print(f"📦 Payload: {payload}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(endpoint, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                status = response.status
                text = await response.text()
                
                print(f"\n📊 Response Status: {status}")
                print(f"📄 Response Body: {text}")
                
                if status == 200:
                    print("\n✅ SUCCESS! API is working and subscription is active!")
                    return True
                elif status == 403:
                    print("\n❌ SUBSCRIPTION REQUIRED")
                    print("Visit: https://rapidapi.com/CapService/api/tiktok-captcha-solver6")
                    print("Click 'Subscribe to Test' and choose a plan")
                    return False
                elif status == 429:
                    print("\n⚠️ RATE LIMITED - Too many requests")
                    return False
                else:
                    print(f"\n⚠️ Unexpected status: {status}")
                    return False
                    
        except Exception as e:
            print(f"\n❌ Error: {e}")
            return False

if __name__ == "__main__":
    print("=" * 60)
    print("RapidAPI TikTok Captcha Solver - Subscription Test")
    print("=" * 60)
    
    result = asyncio.run(test_api_subscription())
    
    if not result:
        print("\n" + "=" * 60)
        print("NEXT STEPS:")
        print("=" * 60)
        print("1. Go to: https://rapidapi.com/CapService/api/tiktok-captcha-solver6")
        print("2. Click 'Pricing' tab")
        print("3. Subscribe to a plan (there may be a free tier)")
        print("4. Re-run this script to verify")
        print("=" * 60)
