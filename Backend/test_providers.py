"""
Test and compare social media providers
Run comparison tests to determine best provider per platform
"""
import asyncio
import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from services.scrapers import get_factory, Platform, initialize_providers
from services.scrapers.provider_factory import ProviderFactory
import json

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_tiktok_providers():
    """Test and compare TikTok providers"""
    print("\n" + "="*60)
    print("🎵 TIKTOK PROVIDER COMPARISON")
    print("="*60 + "\n")
    
    factory = get_factory()
    test_username = "tiktok"  # Official TikTok account
    
    results = await factory.compare_providers(Platform.TIKTOK, test_username)
    
    print(f"Testing with username: @{test_username}\n")
    print(f"{'Provider':<30} {'Priority':<10} {'Latency':<12} {'Success':<10} {'Complete':<10}")
    print("-" * 75)
    
    for result in results:
        provider = result['provider']
        priority = f"#{result['priority']}"
        latency = f"{result['latency_ms']:.0f}ms" if result['latency_ms'] > 0 else "N/A"
        success = "✅ Yes" if result['success'] else "❌ No"
        complete = f"{result['data_completeness']:.0f}%" if result['success'] else "0%"
        error = f" ({result['error']})" if result.get('error') else ""
        
        print(f"{provider:<30} {priority:<10} {latency:<12} {success:<10} {complete:<10}{error}")
    
    # Show recommendation
    print("\n📊 Recommendation:")
    successful = [r for r in results if r['success']]
    if successful:
        best = min(successful, key=lambda x: x['latency_ms'])
        print(f"✨ Use: {best['provider']}")
        print(f"   - Latency: {best['latency_ms']:.0f}ms")
        print(f"   - Completeness: {best['data_completeness']:.0f}%")
    else:
        print("❌ No working providers found")


async def test_instagram_providers():
    """Test and compare Instagram providers"""
    print("\n" + "="*60)
    print("📸 INSTAGRAM PROVIDER COMPARISON")
    print("="*60 + "\n")
    
    factory = get_factory()
    test_username = "instagram"  # Official Instagram account
    
    results = await factory.compare_providers(Platform.INSTAGRAM, test_username)
    
    print(f"Testing with username: @{test_username}\n")
    print(f"{'Provider':<30} {'Priority':<10} {'Latency':<12} {'Success':<10} {'Complete':<10}")
    print("-" * 75)
    
    for result in results:
        provider = result['provider']
        priority = f"#{result['priority']}"
        latency = f"{result['latency_ms']:.0f}ms" if result['latency_ms'] > 0 else "N/A"
        success = "✅ Yes" if result['success'] else "❌ No"
        complete = f"{result['data_completeness']:.0f}%" if result['success'] else "0%"
        error = f" ({result['error']})" if result.get('error') else ""
        
        print(f"{provider:<30} {priority:<10} {latency:<12} {success:<10} {complete:<10}{error}")
    
    # Show recommendation
    print("\n📊 Recommendation:")
    successful = [r for r in results if r['success']]
    if successful:
        best = min(successful, key=lambda x: x['latency_ms'])
        print(f"✨ Use: {best['provider']}")
        print(f"   - Latency: {best['latency_ms']:.0f}ms")
        print(f"   - Completeness: {best['data_completeness']:.0f}%")
    else:
        print("❌ No working providers found")


async def test_automatic_fallback():
    """Test automatic fallback mechanism"""
    print("\n" + "="*60)
    print("🔄 AUTOMATIC FALLBACK TEST")
    print("="*60 + "\n")
    
    factory = get_factory()
    
    # Test TikTok fallback
    print("Testing TikTok with automatic fallback...")
    profile = await factory.execute_with_fallback(
        Platform.TIKTOK,
        "get_profile",
        "tiktok"
    )
    
    if profile:
        print(f"✅ Success! Got profile for @{profile.username}")
        print(f"   - Followers: {profile.followers_count:,}")
        print(f"   - Posts: {profile.posts_count:,}")
    else:
        print("❌ Failed to get profile with all providers")
    
    # Test Instagram fallback
    print("\nTesting Instagram with automatic fallback...")
    profile = await factory.execute_with_fallback(
        Platform.INSTAGRAM,
        "get_profile",
        "instagram"
    )
    
    if profile:
        print(f"✅ Success! Got profile for @{profile.username}")
        print(f"   - Followers: {profile.followers_count:,}")
        print(f"   - Posts: {profile.posts_count:,}")
    else:
        print("❌ Failed to get profile with all providers")


async def show_performance_stats():
    """Show accumulated performance statistics"""
    print("\n" + "="*60)
    print("📈 PERFORMANCE STATISTICS")
    print("="*60 + "\n")
    
    factory = get_factory()
    stats = factory.get_all_stats()
    
    if not stats:
        print("No statistics available yet. Run some tests first!")
        return
    
    for provider_name, provider_stats in stats.items():
        print(f"\n{provider_name}:")
        print(f"  Total Requests: {provider_stats['total_requests']}")
        print(f"  Success Rate: {provider_stats['success_rate']}%")
        print(f"  Avg Latency: {provider_stats['avg_latency_ms']:.0f}ms")
        print(f"  Successful: {provider_stats['successful_requests']}")
        print(f"  Failed: {provider_stats['failed_requests']}")


async def main():
    """Run all provider tests"""
    print("\n" + "="*80)
    print(" " * 20 + "🧪 PROVIDER COMPARISON TEST SUITE")
    print("="*80)
    
    # Verify API key
    api_key = os.getenv("RAPIDAPI_KEY")
    if api_key:
        print(f"\n✅ RAPIDAPI_KEY loaded: {api_key[:20]}...{api_key[-10:]}")
    else:
        print("\n❌ RAPIDAPI_KEY not found in environment!")
        print("Please check your .env file")
        return
    
    # Initialize providers
    print("\nInitializing providers...")
    factory = initialize_providers()
    
    # Show registered providers
    print("\n📋 Registered Providers:")
    for platform in [Platform.TIKTOK, Platform.INSTAGRAM]:
        providers = factory.get_providers(platform)
        print(f"\n{platform.value.upper()}:")
        for p in providers:
            status = "✅ Enabled" if p.enabled else "❌ Disabled"
            print(f"  {p.priority}. {p.name} - {status}")
    
    # Run comparison tests
    try:
        await test_tiktok_providers()
    except Exception as e:
        logger.error(f"TikTok test failed: {e}")
    
    try:
        await test_instagram_providers()
    except Exception as e:
        logger.error(f"Instagram test failed: {e}")
    
    # Test fallback
    try:
        await test_automatic_fallback()
    except Exception as e:
        logger.error(f"Fallback test failed: {e}")
    
    # Show stats
    await show_performance_stats()
    
    print("\n" + "="*80)
    print(" " * 30 + "✅ TESTS COMPLETE")
    print("="*80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
