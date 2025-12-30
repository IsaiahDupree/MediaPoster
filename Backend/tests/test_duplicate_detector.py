"""
Duplicate Detector Tests
========================
Tests for content duplicate detection system.
"""
import pytest
import httpx
from typing import Dict, Any

BASE_URL = "http://localhost:5555/api/v1/content-guard"


class TestDuplicateDetection:
    """Tests for duplicate content detection"""

    @pytest.mark.asyncio
    async def test_info_endpoint(self):
        """Test info endpoint returns feature list"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{BASE_URL}/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "name" in data
        assert "features" in data
        assert len(data["features"]) >= 4

    @pytest.mark.asyncio
    async def test_register_and_check_duplicate(self):
        """Test registering content and detecting duplicate"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Register content
            register_response = await client.post(
                f"{BASE_URL}/register-content",
                json={
                    "content_id": "test_dup_001",
                    "account_id": "test_account_001",
                    "platform": "instagram",
                    "transcript": "This is a test video about productivity hacks for remote workers."
                }
            )
            
            assert register_response.status_code == 200
            
            # Check exact duplicate
            check_response = await client.post(
                f"{BASE_URL}/check-duplicate",
                json={
                    "account_id": "test_account_001",
                    "transcript": "This is a test video about productivity hacks for remote workers.",
                    "platform": "instagram"
                }
            )
            
            assert check_response.status_code == 200
            data = check_response.json()
            
            assert data["is_duplicate"] == True
            assert data["similarity_score"] == 1.0
            assert data["can_post"] == False

    @pytest.mark.asyncio
    async def test_similar_content_detection(self):
        """Test detection of similar (not exact) content"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Register original content
            await client.post(
                f"{BASE_URL}/register-content",
                json={
                    "content_id": "test_sim_001",
                    "account_id": "test_account_002",
                    "platform": "instagram",
                    "transcript": "Five amazing productivity tips that will change your life and help you work from home more efficiently."
                }
            )
            
            # Check similar content (rephrased)
            check_response = await client.post(
                f"{BASE_URL}/check-duplicate",
                json={
                    "account_id": "test_account_002",
                    "transcript": "Here are five incredible productivity hacks that will transform how you work from home and boost your efficiency.",
                    "platform": "tiktok"
                }
            )
            
            assert check_response.status_code == 200
            data = check_response.json()
            
            # Should detect as similar
            assert data["similarity_score"] > 0.5

    @pytest.mark.asyncio
    async def test_unique_content_allowed(self):
        """Test that unique content is allowed"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Register original content
            await client.post(
                f"{BASE_URL}/register-content",
                json={
                    "content_id": "test_unique_001",
                    "account_id": "test_account_003",
                    "platform": "instagram",
                    "transcript": "Today we're cooking a delicious pasta recipe with homemade sauce."
                }
            )
            
            # Check completely different content
            check_response = await client.post(
                f"{BASE_URL}/check-duplicate",
                json={
                    "account_id": "test_account_003",
                    "transcript": "Let's talk about the latest developments in artificial intelligence and machine learning.",
                    "platform": "instagram"
                }
            )
            
            assert check_response.status_code == 200
            data = check_response.json()
            
            assert data["is_duplicate"] == False
            assert data["can_post"] == True
            assert data["similarity_score"] < 0.5

    @pytest.mark.asyncio
    async def test_batch_check(self):
        """Test batch duplicate checking"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Register some content first
            await client.post(
                f"{BASE_URL}/register-content",
                json={
                    "content_id": "test_batch_001",
                    "account_id": "test_account_004",
                    "platform": "instagram",
                    "transcript": "Morning routine video for success mindset."
                }
            )
            
            # Batch check
            batch_response = await client.post(
                f"{BASE_URL}/batch-check",
                json={
                    "account_id": "test_account_004",
                    "items": [
                        {"transcript": "Morning routine video for success mindset.", "platform": "tiktok"},
                        {"transcript": "Evening workout routine for better sleep.", "platform": "instagram"},
                        {"transcript": "Completely new content about travel tips.", "platform": "instagram"}
                    ]
                }
            )
            
            assert batch_response.status_code == 200
            data = batch_response.json()
            
            assert data["total_checked"] == 3
            assert "results" in data
            assert len(data["results"]) == 3

    @pytest.mark.asyncio
    async def test_account_history(self):
        """Test getting account posting history"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Register some content
            await client.post(
                f"{BASE_URL}/register-content",
                json={
                    "content_id": "test_hist_001",
                    "account_id": "test_account_005",
                    "platform": "instagram",
                    "transcript": "History test content one."
                }
            )
            
            await client.post(
                f"{BASE_URL}/register-content",
                json={
                    "content_id": "test_hist_002",
                    "account_id": "test_account_005",
                    "platform": "tiktok",
                    "transcript": "History test content two."
                }
            )
            
            # Get history
            history_response = await client.get(
                f"{BASE_URL}/account-history/test_account_005"
            )
            
            assert history_response.status_code == 200
            data = history_response.json()
            
            assert data["account_id"] == "test_account_005"
            assert data["count"] >= 2

    @pytest.mark.asyncio
    async def test_cross_platform_detection(self):
        """Test that duplicates are detected across platforms"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Register content on Instagram
            await client.post(
                f"{BASE_URL}/register-content",
                json={
                    "content_id": "test_cross_001",
                    "account_id": "test_account_006",
                    "platform": "instagram",
                    "transcript": "Cross platform test content about fitness and health."
                }
            )
            
            # Check same content for TikTok
            check_response = await client.post(
                f"{BASE_URL}/check-duplicate",
                json={
                    "account_id": "test_account_006",
                    "transcript": "Cross platform test content about fitness and health.",
                    "platform": "tiktok"  # Different platform
                }
            )
            
            assert check_response.status_code == 200
            data = check_response.json()
            
            # Should still detect as duplicate
            assert data["is_duplicate"] == True
            assert data["similar_post_platform"] == "instagram"

    @pytest.mark.asyncio
    async def test_strict_mode(self):
        """Test strict mode catches more similar content"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Register content
            await client.post(
                f"{BASE_URL}/register-content",
                json={
                    "content_id": "test_strict_001",
                    "account_id": "test_account_007",
                    "platform": "instagram",
                    "transcript": "Learn the best strategies for growing your social media presence and building an engaged audience."
                }
            )
            
            # Check with strict mode
            check_response = await client.post(
                f"{BASE_URL}/check-duplicate",
                json={
                    "account_id": "test_account_007",
                    "transcript": "Discover top strategies for expanding your social media reach and cultivating a loyal following.",
                    "platform": "instagram",
                    "strict": True
                }
            )
            
            assert check_response.status_code == 200
            data = check_response.json()
            
            # Strict mode should catch this as similar
            assert data["similarity_score"] > 0.3


# Run with: pytest Backend/tests/test_duplicate_detector.py -v --asyncio-mode=auto
if __name__ == "__main__":
    import asyncio
    
    async def run_quick_tests():
        """Quick smoke tests"""
        print("🧪 Running Duplicate Detector Quick Tests...")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test info endpoint
            print("\n1. Testing /info...")
            r = await client.get(f"{BASE_URL}/info")
            assert r.status_code == 200
            print(f"   ✅ {r.json()['name']} loaded")
            
            # Test register
            print("\n2. Testing /register-content...")
            r = await client.post(f"{BASE_URL}/register-content", json={
                "content_id": "quick_test_001",
                "account_id": "quick_test_account",
                "platform": "instagram",
                "transcript": "Quick test content for duplicate detection."
            })
            assert r.status_code == 200
            print(f"   ✅ Registered: {r.json()['content_id']}")
            
            # Test check duplicate
            print("\n3. Testing /check-duplicate (exact match)...")
            r = await client.post(f"{BASE_URL}/check-duplicate", json={
                "account_id": "quick_test_account",
                "transcript": "Quick test content for duplicate detection.",
                "platform": "tiktok"
            })
            assert r.status_code == 200
            print(f"   ✅ Is duplicate: {r.json()['is_duplicate']}")
            print(f"   ✅ Similarity: {r.json()['similarity_score']:.1%}")
            
            # Test unique content
            print("\n4. Testing /check-duplicate (unique)...")
            r = await client.post(f"{BASE_URL}/check-duplicate", json={
                "account_id": "quick_test_account",
                "transcript": "This is completely different content about cooking recipes.",
                "platform": "instagram"
            })
            assert r.status_code == 200
            print(f"   ✅ Is duplicate: {r.json()['is_duplicate']}")
            print(f"   ✅ Can post: {r.json()['can_post']}")
        
        print("\n✅ All quick tests passed!")
    
    asyncio.run(run_quick_tests())
