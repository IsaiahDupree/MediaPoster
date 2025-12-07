"""
Test Social Analytics API Endpoints
Quick test to verify all endpoints work
"""
import asyncio
import httpx
import json


async def test_all_endpoints():
    """Test all analytics API endpoints"""
    
    base_url = "http://localhost:5555/api/social-analytics"
    
    print("\n" + "="*80)
    print("🧪 TESTING SOCIAL ANALYTICS API ENDPOINTS")
    print("="*80 + "\n")
    
    async with httpx.AsyncClient() as client:
        
        # Test 1: Overview
        print("📊 Test 1: GET /overview")
        try:
            response = await client.get(f"{base_url}/overview")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"   Total Platforms: {data.get('total_platforms')}")
                print(f"   Total Accounts: {data.get('total_accounts')}")
                print(f"   Total Followers: {data.get('total_followers'):,}")
                print(f"   Total Views: {data.get('total_views'):,}")
            else:
                print(f"❌ Status: {response.status_code}")
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
        
        # Test 2: Accounts
        print("👥 Test 2: GET /accounts")
        try:
            response = await client.get(f"{base_url}/accounts")
            if response.status_code == 200:
                accounts = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"   Accounts Found: {len(accounts)}")
                if accounts:
                    for acc in accounts[:3]:
                        print(f"   - {acc['platform']}: @{acc['username']} ({acc['followers_count']:,} followers)")
            else:
                print(f"❌ Status: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
        
        # Test 3: Content Mapping
        print("🔗 Test 3: GET /content-mapping")
        try:
            response = await client.get(f"{base_url}/content-mapping")
            if response.status_code == 200:
                mappings = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"   Content Items: {len(mappings)}")
                if mappings:
                    for item in mappings[:3]:
                        print(f"   - {item.get('video_title', 'Untitled')}")
                        print(f"     Platforms: {', '.join(item['platforms'])}")
                        print(f"     Views: {item['total_views']:,}")
            else:
                print(f"❌ Status: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
        
        # Test 4: Platform Detail (TikTok)
        print("📱 Test 4: GET /platform/tiktok")
        try:
            response = await client.get(f"{base_url}/platform/tiktok")
            if response.status_code == 200:
                platform_data = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"   Platform: {platform_data.get('platform')}")
                print(f"   Accounts: {len(platform_data.get('accounts', []))}")
                print(f"   Trend Data Points: {len(platform_data.get('trends', []))}")
                print(f"   Top Posts: {len(platform_data.get('top_posts', []))}")
            else:
                print(f"❌ Status: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
        
        # Test 5: Posts
        print("📝 Test 5: GET /posts")
        try:
            response = await client.get(f"{base_url}/posts?limit=10")
            if response.status_code == 200:
                posts = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"   Posts Found: {len(posts)}")
                if posts:
                    for post in posts[:3]:
                        print(f"   - {post['platform']}: {post['current_views']:,} views")
                        print(f"     Has Video: {post['has_video']}, Has Clip: {post['has_clip']}")
            else:
                print(f"❌ Status: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
        
        # Test 6: Trends
        print("📈 Test 6: GET /trends")
        try:
            response = await client.get(f"{base_url}/trends?days=7")
            if response.status_code == 200:
                trends = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"   Period: {trends.get('period_days')} days")
                print(f"   Data Points: {trends.get('data_points')}")
            else:
                print(f"❌ Status: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")
        
        print()
        
        # Test 7: Top Hashtags
        print("#️⃣  Test 7: GET /hashtags/top")
        try:
            response = await client.get(f"{base_url}/hashtags/top?limit=5")
            if response.status_code == 200:
                hashtags = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"   Top Hashtags: {len(hashtags)}")
                if hashtags:
                    for tag in hashtags[:5]:
                        print(f"   - #{tag['hashtag']}: {tag['uses']} uses, {tag['engagement_rate']}% engagement")
            else:
                print(f"❌ Status: {response.status_code}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "="*80)
    print("✅ API ENDPOINT TESTS COMPLETE")
    print("="*80 + "\n")
    
    print("📋 Next Steps:")
    print("1. Start frontend: cd Frontend && npm run dev")
    print("2. Navigate to: http://localhost:5173/analytics")
    print("3. Explore the dashboard!")


if __name__ == "__main__":
    print("\n⚠️  Make sure backend is running:")
    print("   cd Backend && ./venv/bin/python -m uvicorn main:app --reload --port 5555\n")
    
    input("Press Enter to start tests...")
    
    asyncio.run(test_all_endpoints())
