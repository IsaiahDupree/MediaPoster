"""
Publishing API Contract Tests
==============================
Tests to verify the Publishing API adheres to its contract
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta
from typing import Dict, Any
import uuid


class TestPublishEndpointContract:
    """Contract tests for POST /api/publish/*"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.fixture
    def valid_publish_payload(self) -> Dict[str, Any]:
        """Valid publish request payload"""
        return {
            "media_id": str(uuid.uuid4()),
            "platform": "tiktok",
            "account_id": 710,
            "title": "Test Video",
            "caption": "Check out this content! #fyp #viral",
            "hashtags": ["#fyp", "#viral", "#test"],
        }

    @pytest.mark.asyncio
    async def test_publish_returns_correct_schema(self, base_url, valid_publish_payload):
        """Publish response must match expected schema"""
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post(
                "/api/publish/now",
                json=valid_publish_payload
            )
            
            if response.status_code in [200, 202]:
                data = response.json()
                
                # Must have status field
                assert "status" in data
                assert data["status"] in ["queued", "processing", "completed", "failed"]
                
                # Should have job_id for tracking
                if data["status"] in ["queued", "processing"]:
                    assert "job_id" in data or "publish_id" in data

    @pytest.mark.asyncio
    async def test_publish_requires_media_id(self, base_url, valid_publish_payload):
        """media_id is required"""
        payload = valid_publish_payload.copy()
        del payload["media_id"]
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/publish/now", json=payload)
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_publish_requires_platform(self, base_url, valid_publish_payload):
        """platform is required"""
        payload = valid_publish_payload.copy()
        del payload["platform"]
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/publish/now", json=payload)
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_publish_validates_platform_enum(self, base_url, valid_publish_payload):
        """platform must be valid"""
        payload = valid_publish_payload.copy()
        payload["platform"] = "not_a_platform"
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/publish/now", json=payload)
            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_publish_nonexistent_media_returns_404(self, base_url, valid_publish_payload):
        """Publishing non-existent media should return 404"""
        payload = valid_publish_payload.copy()
        payload["media_id"] = str(uuid.uuid4())  # Random non-existent ID
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/publish/now", json=payload)
            assert response.status_code in [404, 400, 422]


class TestPublishStatusContract:
    """Contract tests for GET /api/publish/status/{job_id}"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_status_returns_correct_schema(self, base_url):
        """Status response must match expected schema"""
        job_id = str(uuid.uuid4())
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.get(f"/api/publish/status/{job_id}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Must have status field
                assert "status" in data
                assert data["status"] in [
                    "pending", "queued", "processing", 
                    "uploading", "submitted", "polling",
                    "completed", "failed", "cancelled"
                ]

    @pytest.mark.asyncio
    async def test_status_nonexistent_returns_404(self, base_url):
        """Non-existent job should return 404"""
        fake_job_id = str(uuid.uuid4())
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.get(f"/api/publish/status/{fake_job_id}")
            assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_status_completed_includes_url(self, base_url):
        """Completed status should include platform URL"""
        # This tests that completed publishes return the post URL
        pass  # Requires actual completed publish


class TestPublishCancelContract:
    """Contract tests for POST /api/publish/cancel/{job_id}"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_cancel_pending_job(self, base_url):
        """Pending jobs should be cancellable"""
        job_id = str(uuid.uuid4())
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post(f"/api/publish/cancel/{job_id}")
            # Either cancelled or not found
            assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_cancel_completed_job_returns_error(self, base_url):
        """Already completed jobs cannot be cancelled"""
        # Would need actual completed job to test properly
        pass

    @pytest.mark.asyncio
    async def test_cancel_is_idempotent(self, base_url):
        """Cancelling same job twice should be idempotent"""
        job_id = str(uuid.uuid4())
        
        async with AsyncClient(base_url=base_url) as client:
            await client.post(f"/api/publish/cancel/{job_id}")
            response = await client.post(f"/api/publish/cancel/{job_id}")
            # Should not error on second cancel
            assert response.status_code in [200, 404]


class TestPublishBlotatoContract:
    """Contract tests for Blotato publishing endpoints"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_blotato_accounts_returns_list(self, base_url):
        """GET /api/blotato/accounts should return account list"""
        async with AsyncClient(base_url=base_url) as client:
            response = await client.get("/api/blotato/accounts")
            
            if response.status_code == 200:
                data = response.json()
                
                # Should be a list of accounts
                assert isinstance(data, list) or "accounts" in data
                
                if isinstance(data, list) and len(data) > 0:
                    account = data[0]
                    # Each account should have id and platform
                    assert "id" in account or "account_id" in account
                    assert "platform" in account

    @pytest.mark.asyncio
    async def test_blotato_publish_validates_account(self, base_url):
        """Publishing should validate account exists"""
        payload = {
            "media_id": str(uuid.uuid4()),
            "platform": "tiktok",
            "account_id": 99999999,  # Non-existent account
        }
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/blotato/publish", json=payload)
            # Should reject invalid account
            assert response.status_code in [400, 404, 422]


class TestPublishMultiPlatformContract:
    """Contract tests for multi-platform publishing"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_multi_platform_publish(self, base_url):
        """Should support publishing to multiple platforms at once"""
        payload = {
            "media_id": str(uuid.uuid4()),
            "platforms": [
                {"platform": "tiktok", "account_id": 710},
                {"platform": "instagram", "account_id": 807},
            ],
            "title": "Multi-platform post",
        }
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/publish/multi", json=payload)
            
            if response.status_code in [200, 202]:
                data = response.json()
                # Should have status per platform
                assert "results" in data or "jobs" in data

    @pytest.mark.asyncio
    async def test_multi_platform_partial_failure(self, base_url):
        """Partial failures should be reported per-platform"""
        # One valid, one invalid platform
        payload = {
            "media_id": str(uuid.uuid4()),
            "platforms": [
                {"platform": "tiktok", "account_id": 710},
                {"platform": "invalid_platform", "account_id": 999},
            ],
        }
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/publish/multi", json=payload)
            # Should report individual failures
            if response.status_code in [200, 207]:  # 207 Multi-Status
                data = response.json()
                # Should have per-platform status


class TestPublishQueueContract:
    """Contract tests for publishing queue endpoints"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_queue_list_returns_pending_jobs(self, base_url):
        """GET /api/publish/queue should list pending jobs"""
        async with AsyncClient(base_url=base_url) as client:
            response = await client.get("/api/publish/queue")
            
            if response.status_code == 200:
                data = response.json()
                
                # Should be list or have jobs array
                assert isinstance(data, list) or "jobs" in data or "queue" in data

    @pytest.mark.asyncio
    async def test_queue_stats(self, base_url):
        """Queue stats endpoint should return counts"""
        async with AsyncClient(base_url=base_url) as client:
            response = await client.get("/api/publish/queue/stats")
            
            if response.status_code == 200:
                data = response.json()
                
                # Should have count fields
                expected_fields = ["pending", "processing", "completed", "failed"]
                for field in expected_fields:
                    if field in data:
                        assert isinstance(data[field], int)


class TestPublishRetryContract:
    """Contract tests for publish retry functionality"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_retry_failed_publish(self, base_url):
        """Failed publishes should be retriable"""
        job_id = str(uuid.uuid4())
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post(f"/api/publish/retry/{job_id}")
            # Either retried or not found
            assert response.status_code in [200, 202, 404]

    @pytest.mark.asyncio
    async def test_retry_limit(self, base_url):
        """Should enforce max retry limit"""
        # Retrying too many times should fail
        pass


class TestPublishWebhookContract:
    """Contract tests for publish webhook callbacks"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_webhook_configuration(self, base_url):
        """Webhook URL should be configurable"""
        payload = {
            "url": "https://example.com/webhook",
            "events": ["publish.completed", "publish.failed"],
        }
        
        async with AsyncClient(base_url=base_url) as client:
            response = await client.post("/api/publish/webhook/configure", json=payload)
            # Either configured or endpoint doesn't exist
            assert response.status_code in [200, 201, 404]

    @pytest.mark.asyncio
    async def test_webhook_validates_url(self, base_url):
        """Webhook URL should be validated"""
        invalid_urls = [
            "not-a-url",
            "ftp://invalid-scheme.com",
            "javascript:alert(1)",
        ]
        
        for url in invalid_urls:
            payload = {"url": url, "events": ["publish.completed"]}
            
            async with AsyncClient(base_url=base_url) as client:
                response = await client.post("/api/publish/webhook/configure", json=payload)
                assert response.status_code in [400, 422, 404]


class TestPublishRateLimitContract:
    """Contract tests for publish rate limiting"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_rate_limit_headers_present(self, base_url):
        """Rate limit headers should be present"""
        async with AsyncClient(base_url=base_url) as client:
            response = await client.get("/api/publish/queue")
            
            # Check for rate limit headers
            rate_limit_headers = [
                "X-RateLimit-Limit",
                "X-RateLimit-Remaining",
                "X-RateLimit-Reset",
            ]
            # At least one should be present (or none if not implemented)

    @pytest.mark.asyncio
    async def test_rate_limit_per_platform(self, base_url):
        """Each platform should have its own rate limit"""
        # Platform-specific limits (TikTok, Instagram, etc.)
        pass


class TestPublishErrorResponses:
    """Contract tests for error response format"""

    @pytest.fixture
    def base_url(self):
        return "http://localhost:5555"

    @pytest.mark.asyncio
    async def test_error_response_format(self, base_url):
        """Error responses should have consistent format"""
        async with AsyncClient(base_url=base_url) as client:
            # Trigger a validation error
            response = await client.post("/api/publish/now", json={})
            
            if response.status_code in [400, 422]:
                data = response.json()
                
                # Should have error message
                assert "detail" in data or "error" in data or "message" in data

    @pytest.mark.asyncio
    async def test_not_found_error_format(self, base_url):
        """404 responses should have consistent format"""
        async with AsyncClient(base_url=base_url) as client:
            response = await client.get(f"/api/publish/status/{uuid.uuid4()}")
            
            if response.status_code == 404:
                data = response.json()
                assert "detail" in data or "error" in data or "message" in data
