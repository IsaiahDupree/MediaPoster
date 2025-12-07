"""
End-to-End Test of Analytics System
Tests the complete flow without database
"""
import asyncio
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

from services.fetch_social_analytics import fetch_single_account


async def test_full_workflow():
    """Test complete analytics fetch workflow"""
    
    print("\n" + "="*80)
    print("🧪 END-TO-END ANALYTICS TEST")
    print("="*80 + "\n")
    
    # Test 1: Fetch TikTok analytics
    print("📊 Test 1: Fetching @isaiah_dupree TikTok analytics...")
    result = await fetch_single_account("tiktok", "isaiah_dupree")
    
    if result.get("success"):
        print("\n✅ Test 1 PASSED!")
        print(f"   Posts: {result.get('posts_saved', 0)}")
        print(f"   Views: {result.get('total_views', 0):,}")
        print(f"   Likes: {result.get('total_likes', 0):,}")
    else:
        print(f"\n❌ Test 1 FAILED: {result.get('error')}")
        return False
    
    # Save sample data
    output_file = Path(__file__).parent / "analytics_test_output.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    
    print(f"\n💾 Sample data saved to: {output_file}")
    
    print("\n" + "="*80)
    print("✅ ALL TESTS PASSED!")
    print("="*80 + "\n")
    
    print("📋 Next Steps:")
    print("1. Run database migration:")
    print("   docker exec -i supabase-db psql -U postgres -d postgres < migrations/social_media_analytics.sql")
    print("\n2. Or manually run the initialization:")
    print("   python initialize_social_analytics.py")
    print("\n3. Set up cron job:")
    print("   python setup_analytics_cron.py")
    
    return True


if __name__ == "__main__":
    asyncio.run(test_full_workflow())
