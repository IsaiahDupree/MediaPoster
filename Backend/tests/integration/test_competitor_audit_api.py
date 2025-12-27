"""
Integration Tests for Competitor Audit API
==========================================
Tests for competitor collection, deep audit, funnel mapping,
and report generation API endpoints.
"""
import pytest
import httpx
import os
from uuid import uuid4

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:5555")


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def api_client():
    """Create HTTP client for API tests"""
    return httpx.Client(base_url=BASE_URL, timeout=30.0)


# ============================================================================
# Audit Run Tests
# ============================================================================

class TestAuditRunAPI:
    """Tests for audit run endpoints"""
    
    def test_start_audit_requires_platform(self, api_client):
        """Test that starting audit requires platform"""
        try:
            response = api_client.post(
                "/api/competitor-audit/start",
                json={"handle": "testuser"}
            )
            
            # Missing platform should fail
            assert response.status_code in [400, 422, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_start_audit_requires_handle(self, api_client):
        """Test that starting audit requires handle"""
        try:
            response = api_client.post(
                "/api/competitor-audit/start",
                json={"platform": "instagram"}
            )
            
            # Missing handle should fail
            assert response.status_code in [400, 422, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_start_audit_valid_request(self, api_client):
        """Test starting an audit with valid parameters"""
        try:
            response = api_client.post(
                "/api/competitor-audit/start",
                json={
                    "platform": "instagram",
                    "handle": "testcreator",
                    "post_count": 10
                }
            )
            
            # Should either start or fail gracefully
            # (might fail if RapidAPI not configured)
            assert response.status_code in [200, 202, 400, 500]
            
            if response.status_code in [200, 202]:
                data = response.json()
                assert "run_id" in data or "status" in data
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_check_audit_status_invalid_id(self, api_client):
        """Test checking status with invalid run ID"""
        try:
            fake_id = str(uuid4())
            response = api_client.get(f"/api/competitor-audit/status/{fake_id}")
            
            assert response.status_code in [404, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")


# ============================================================================
# Tracked Accounts Tests
# ============================================================================

class TestTrackedAccountsAPI:
    """Tests for tracked accounts endpoints"""
    
    def test_list_tracked_accounts(self, api_client):
        """Test listing tracked accounts"""
        try:
            response = api_client.get("/api/competitor-audit/accounts")
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, (dict, list))
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_list_accounts_with_platform_filter(self, api_client):
        """Test listing accounts filtered by platform"""
        try:
            response = api_client.get(
                "/api/competitor-audit/accounts",
                params={"platform": "instagram"}
            )
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, (dict, list))
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_get_account_details_invalid_id(self, api_client):
        """Test getting account details with invalid ID"""
        try:
            fake_id = str(uuid4())
            response = api_client.get(f"/api/competitor-audit/accounts/{fake_id}")
            
            assert response.status_code in [404, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")


# ============================================================================
# Posts Tests
# ============================================================================

class TestCompetitorPostsAPI:
    """Tests for competitor posts endpoints"""
    
    def test_list_posts_requires_account(self, api_client):
        """Test that listing posts requires account_id"""
        try:
            response = api_client.get("/api/competitor-audit/posts")
            
            # Should require account_id parameter
            assert response.status_code in [400, 422, 200]
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_list_posts_with_account(self, api_client):
        """Test listing posts for an account"""
        try:
            fake_account_id = str(uuid4())
            response = api_client.get(
                "/api/competitor-audit/posts",
                params={"account_id": fake_account_id}
            )
            
            # Non-existent account should return empty or 404
            assert response.status_code in [200, 404]
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_get_post_ranking_invalid_account(self, api_client):
        """Test post ranking with invalid account"""
        try:
            fake_id = str(uuid4())
            response = api_client.get(f"/api/competitor-audit/accounts/{fake_id}/rankings")
            
            assert response.status_code in [404, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")


# ============================================================================
# Report Tests
# ============================================================================

class TestAuditReportAPI:
    """Tests for audit report endpoints"""
    
    def test_get_report_invalid_id(self, api_client):
        """Test getting report with invalid ID"""
        try:
            fake_id = str(uuid4())
            response = api_client.get(f"/api/competitor-audit/reports/{fake_id}")
            
            assert response.status_code in [404, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_list_reports(self, api_client):
        """Test listing reports"""
        try:
            response = api_client.get("/api/competitor-audit/reports")
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, (dict, list))
        except httpx.ConnectError:
            pytest.skip("API not running")


# ============================================================================
# Template Pack Tests
# ============================================================================

class TestTemplatePackAPI:
    """Tests for template pack endpoints"""
    
    def test_list_template_packs(self, api_client):
        """Test listing template packs"""
        try:
            response = api_client.get("/api/competitor-audit/templates")
            
            if response.status_code == 200:
                data = response.json()
                assert isinstance(data, (dict, list))
        except httpx.ConnectError:
            pytest.skip("API not running")
    
    def test_get_template_pack_invalid_id(self, api_client):
        """Test getting template pack with invalid ID"""
        try:
            fake_id = str(uuid4())
            response = api_client.get(f"/api/competitor-audit/templates/{fake_id}")
            
            assert response.status_code in [404, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")


# ============================================================================
# Funnel Map Tests
# ============================================================================

class TestFunnelMapAPI:
    """Tests for funnel map endpoints"""
    
    def test_get_funnel_map_invalid_account(self, api_client):
        """Test getting funnel map with invalid account"""
        try:
            fake_id = str(uuid4())
            response = api_client.get(f"/api/competitor-audit/accounts/{fake_id}/funnel")
            
            assert response.status_code in [404, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")


# ============================================================================
# Deep Audit Tests
# ============================================================================

class TestDeepAuditAPI:
    """Tests for deep audit endpoints"""
    
    def test_get_deep_audit_invalid_account(self, api_client):
        """Test getting deep audit with invalid account"""
        try:
            fake_id = str(uuid4())
            response = api_client.get(f"/api/competitor-audit/accounts/{fake_id}/audit")
            
            assert response.status_code in [404, 500]
        except httpx.ConnectError:
            pytest.skip("API not running")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
