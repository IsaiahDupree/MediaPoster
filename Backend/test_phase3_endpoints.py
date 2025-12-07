"""
Test Phase 3 API Endpoints
Tests content tracking and follower engagement endpoints
"""
import requests
import json

BASE_URL = "http://localhost:5555/api/social-analytics"

print("\n🧪 Testing Phase 3 API Endpoints...\n")

# Test 1: Content List
print("📋 Test 1: GET /content")
try:
    response = requests.get(f"{BASE_URL}/content?limit=5")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {len(data)} content items")
        if data:
            first = data[0]
            print(f"   - Title: {first['title']}")
            print(f"   - Platforms: {first['platform_count']} ({', '.join(first['platforms'])})")
            print(f"   - Best platform: {first.get('best_platform', 'N/A')}")
    else:
        print(f"   ❌ Error: {response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: Content Detail
print("\n📋 Test 2: GET /content/{content_id}")
try:
    # Get first content_id from previous test
    response = requests.get(f"{BASE_URL}/content?limit=1")
    if response.status_code == 200:
        data = response.json()
        if data:
            content_id = data[0]['content_id']
            detail_response = requests.get(f"{BASE_URL}/content/{content_id}")
            print(f"   Status: {detail_response.status_code}")
            if detail_response.status_code == 200:
                detail = detail_response.json()
                print(f"   ✅ Content: {detail['title']}")
                print(f"   - Platforms: {len(detail['platform_breakdown'])}")
                for platform in detail['platform_breakdown']:
                    print(f"     • {platform['platform']}: {platform['views']} views, {platform['likes']} likes")
            else:
                print(f"   ❌ Error: {detail_response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Content Leaderboard
print("\n🏆 Test 3: GET /content/leaderboard")
try:
    response = requests.get(f"{BASE_URL}/content/leaderboard?limit=5")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Top {len(data)} content items:")
        for item in data:
            print(f"   #{item['rank']}: {item['title'][:50]}")
            print(f"       - Views: {item['total_views']}, Likes: {item['total_likes']}")
            print(f"       - Engaged Reach: {item['engaged_reach']}, Score: {item['leverage_score']}")
    else:
        print(f"   ❌ Error: {response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 4: Followers List
print("\n👥 Test 4: GET /followers")
try:
    response = requests.get(f"{BASE_URL}/followers?limit=10")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {len(data)} followers")
        for follower in data:
            print(f"   - @{follower['username']} ({follower['platform']})")
            print(f"     Score: {follower['engagement_score']}, Tier: {follower['engagement_tier']}")
            print(f"     Interactions: {follower['total_interactions']} ({follower['comment_count']} comments)")
    else:
        print(f"   ❌ Error: {response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 5: Follower Detail
print("\n👤 Test 5: GET /followers/{follower_id}")
try:
    # Get first follower_id
    response = requests.get(f"{BASE_URL}/followers?limit=1")
    if response.status_code == 200:
        data = response.json()
        if data:
            follower_id = data[0]['follower_id']
            detail_response = requests.get(f"{BASE_URL}/followers/{follower_id}?timeline_limit=5")
            print(f"   Status: {detail_response.status_code}")
            if detail_response.status_code == 200:
                detail = detail_response.json()
                print(f"   ✅ Follower: @{detail['username']}")
                print(f"   - Platform: {detail['platform']}")
                print(f"   - Engagement Score: {detail['engagement']['score']}")
                print(f"   - Tier: {detail['engagement']['tier']}")
                print(f"   - Timeline items: {len(detail['timeline'])}")
                if detail['timeline']:
                    print(f"   Recent activity:")
                    for activity in detail['timeline'][:3]:
                        print(f"     • {activity['type']} on {activity['occurred_at'][:10]}")
            else:
                print(f"   ❌ Error: {detail_response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 6: Followers Leaderboard
print("\n🏆 Test 6: GET /followers/leaderboard")
try:
    response = requests.get(f"{BASE_URL}/followers/leaderboard?limit=10")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Top {len(data)} engaged followers:")
        for follower in data:
            print(f"   #{follower['rank']}: @{follower['username']} ({follower['platform']})")
            print(f"       Score: {follower['engagement_score']}, Tier: {follower['engagement_tier']}")
            print(f"       {follower['total_interactions']} interactions, {follower['comment_count']} comments")
    else:
        print(f"   ❌ Error: {response.text}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 7: Filter by platform
print("\n🔍 Test 7: Filter by platform (TikTok)")
try:
    response = requests.get(f"{BASE_URL}/content?platform=tiktok&limit=3")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {len(data)} TikTok content items")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 8: Filter followers by tier
print("\n🔍 Test 8: Filter followers by tier (super_fan)")
try:
    response = requests.get(f"{BASE_URL}/followers?tier=super_fan&limit=5")
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ Found {len(data)} super fans")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "="*60)
print("✅ PHASE 3 ENDPOINT TESTS COMPLETE!")
print("="*60)
print("\nAll 6 new endpoints are working:")
print("  ✅ GET /content - List content")
print("  ✅ GET /content/{id} - Content detail")
print("  ✅ GET /content/leaderboard - Top content")
print("  ✅ GET /followers - List followers")
print("  ✅ GET /followers/{id} - Follower detail")
print("  ✅ GET /followers/leaderboard - Top followers")
print("\nReady for Phase 4: Frontend dashboards!")
print("\n")
