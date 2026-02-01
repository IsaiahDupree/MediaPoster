#!/usr/bin/env python3
"""
Integration test script for MediaPoster microservices.
Tests connectivity and real implementations of media-pipeline and content-intelligence.
"""
import asyncio
import httpx
import sys
from typing import Dict, Any

# Service URLs
SERVICES = {
    "media-pipeline": "http://localhost:6004",
    "content-intelligence": "http://localhost:6006",
}


async def test_health(client: httpx.AsyncClient, service: str, url: str) -> bool:
    """Test service health endpoint."""
    try:
        response = await client.get(f"{url}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ {service}: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"  ❌ {service}: HTTP {response.status_code}")
            return False
    except httpx.ConnectError:
        print(f"  ❌ {service}: Not reachable")
        return False


async def test_fate_scoring(client: httpx.AsyncClient) -> bool:
    """Test FATE scoring with real implementation."""
    url = f"{SERVICES['content-intelligence']}/api/score/fate"
    payload = {
        "content": "Most founders fail because they don't understand this pattern. I've helped 127 entrepreneurs discover the mechanism behind growth.",
        "content_id": "test-123"
    }
    
    try:
        response = await client.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            impl = data.get("implementation", "unknown")
            scores = data.get("fate_score", {})
            print(f"  ✅ FATE Scoring ({impl}): F={scores.get('focus', 0):.2f}, A={scores.get('authority', 0):.2f}, T={scores.get('tribe', 0):.2f}, E={scores.get('emotion', 0):.2f}")
            return impl == "real"
        else:
            print(f"  ❌ FATE Scoring: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ FATE Scoring: {e}")
        return False


async def test_awareness_classification(client: httpx.AsyncClient) -> bool:
    """Test awareness classification with real implementation."""
    url = f"{SERVICES['content-intelligence']}/api/classify/awareness"
    payload = {"content": "Are you struggling with getting views on your content?"}
    
    try:
        response = await client.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            impl = data.get("implementation", "unknown")
            level = data.get("awareness_level", "unknown")
            confidence = data.get("confidence", 0)
            print(f"  ✅ Awareness ({impl}): {level} (confidence: {confidence:.2f})")
            return impl == "real"
        else:
            print(f"  ❌ Awareness: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Awareness: {e}")
        return False


async def test_sentiment_analysis(client: httpx.AsyncClient) -> bool:
    """Test sentiment analysis with real implementation."""
    url = f"{SERVICES['content-intelligence']}/api/analyze/sentiment"
    payload = {"text": "This is absolutely amazing! I love how easy it is to use."}
    
    try:
        response = await client.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            impl = data.get("implementation", "unknown")
            sentiment = data.get("sentiment", "unknown")
            score = data.get("score", 0)
            print(f"  ✅ Sentiment ({impl}): {sentiment} (score: {score:.2f})")
            return impl == "real"
        else:
            print(f"  ❌ Sentiment: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Sentiment: {e}")
        return False


async def test_format_detection(client: httpx.AsyncClient) -> bool:
    """Test format detection with real implementation."""
    url = f"{SERVICES['media-pipeline']}/api/format/detect"
    payload = {
        "file_path": "/tmp/test.mp4",
        "transcript": "Hello everyone, welcome to my channel. Today I want to share some important tips with you about content creation."
    }
    
    try:
        response = await client.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            impl = data.get("implementation", "unknown")
            fmt = data.get("format", {})
            primary = fmt.get("primary_format", "unknown")
            print(f"  ✅ Format Detection ({impl}): {primary}")
            return impl == "real"
        else:
            print(f"  ❌ Format Detection: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Format Detection: {e}")
        return False


async def test_title_generation(client: httpx.AsyncClient) -> bool:
    """Test AI title generation."""
    url = f"{SERVICES['content-intelligence']}/api/generate/title"
    payload = {
        "content": "How to grow your TikTok following to 100K in 30 days",
        "platform": "tiktok",
        "style": "viral",
        "count": 3
    }
    
    try:
        response = await client.post(url, json=payload)
        if response.status_code == 200:
            data = response.json()
            provider = data.get("ai_provider", "unknown")
            titles = data.get("titles", [])
            print(f"  ✅ Title Generation ({provider}): {len(titles)} titles generated")
            return True
        else:
            print(f"  ❌ Title Generation: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"  ❌ Title Generation: {e}")
        return False


async def main():
    """Run all integration tests."""
    print("\n" + "="*60)
    print("🔬 MediaPoster Microservices Integration Tests")
    print("="*60 + "\n")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test health
        print("📡 Health Checks:")
        health_results = []
        for service, url in SERVICES.items():
            result = await test_health(client, service, url)
            health_results.append(result)
        
        if not all(health_results):
            print("\n⚠️  Some services are not healthy. Start them with:")
            print("   cd ~/Documents/Software/media-pipeline && source venv/bin/activate && python app.py &")
            print("   cd ~/Documents/Software/content-intelligence && source venv/bin/activate && python app.py &")
            print()
        
        # Test real implementations
        print("\n🧪 Real Implementation Tests:")
        
        real_tests = [
            ("FATE Scoring", test_fate_scoring(client)),
            ("Awareness Classification", test_awareness_classification(client)),
            ("Sentiment Analysis", test_sentiment_analysis(client)),
            ("Format Detection", test_format_detection(client)),
            ("Title Generation", test_title_generation(client)),
        ]
        
        results = []
        for name, coro in real_tests:
            try:
                result = await coro
                results.append((name, result))
            except Exception as e:
                print(f"  ❌ {name}: {e}")
                results.append((name, False))
        
        # Summary
        print("\n" + "="*60)
        passed = sum(1 for _, r in results if r)
        total = len(results)
        
        if passed == total:
            print(f"✅ All {total} tests passed!")
        else:
            print(f"⚠️  {passed}/{total} tests passed")
        
        print("="*60 + "\n")
        
        return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
