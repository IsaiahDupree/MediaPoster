"""
Tests for Social Accounts API
Tests account management and analytics display.
"""
import pytest
import httpx

API_BASE = "http://localhost:5555"


class TestSocialAccountsSync:
    """Tests for syncing accounts from env."""
    
    def test_sync_from_env_endpoint_exists(self):
        """Sync endpoint should exist."""
        response = httpx.post(f"{API_BASE}/api/social-accounts/accounts/sync-from-env", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "added" in data or "existing" in data
    
    def test_sync_returns_counts(self):
        """Sync should return account counts."""
        response = httpx.post(f"{API_BASE}/api/social-accounts/accounts/sync-from-env", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data.get("added", 0), int)
        assert isinstance(data.get("existing", 0), int)
        assert isinstance(data.get("total_env_accounts", 0), int)


class TestAccountsList:
    """Tests for listing accounts."""
    
    def test_get_accounts_returns_list(self):
        """Get accounts should return a list."""
        response = httpx.get(f"{API_BASE}/api/social-accounts/accounts", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_accounts_have_required_fields(self):
        """Accounts should have required fields."""
        response = httpx.get(f"{API_BASE}/api/social-accounts/accounts", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        if data:
            account = data[0]
            required_fields = ["id", "platform", "username", "followers_count", "is_active"]
            for field in required_fields:
                assert field in account, f"Missing field: {field}"
    
    def test_filter_by_platform(self):
        """Should filter accounts by platform."""
        response = httpx.get(f"{API_BASE}/api/social-accounts/accounts?platform=instagram", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        for account in data:
            assert account["platform"] == "instagram"


class TestAnalyticsOverview:
    """Tests for analytics overview endpoint."""
    
    def test_overview_returns_structure(self):
        """Overview should return expected structure."""
        response = httpx.get(f"{API_BASE}/api/social-analytics/overview", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        required_fields = [
            "total_platforms", "total_accounts", "total_followers",
            "total_views", "total_likes", "platform_breakdown"
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"
    
    def test_platform_breakdown_is_list(self):
        """Platform breakdown should be a list."""
        response = httpx.get(f"{API_BASE}/api/social-analytics/overview", timeout=10)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data["platform_breakdown"], list)
    
    def test_account_counts_match(self):
        """Total accounts should match sum of platform accounts."""
        response = httpx.get(f"{API_BASE}/api/social-analytics/overview", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        platform_total = sum(p["total_accounts"] for p in data["platform_breakdown"])
        assert platform_total == data["total_accounts"]


class TestAddRemoveAccounts:
    """Tests for adding and removing accounts."""
    
    def test_add_account(self):
        """Should add a new account."""
        response = httpx.post(
            f"{API_BASE}/api/social-accounts/accounts",
            json={"platform": "instagram", "username": "test_account_cascade"},
            timeout=10
        )
        # Should succeed or say already exists
        assert response.status_code in [200, 201]
        data = response.json()
        assert "account_id" in data or "message" in data


class TestFetchLive:
    """Tests for live analytics fetching."""
    
    def test_fetch_all_starts(self):
        """Fetch all should start background process."""
        response = httpx.post(f"{API_BASE}/api/social-accounts/accounts/fetch-all", timeout=10)
        assert response.status_code in [200, 202]
        data = response.json()
        assert "status" in data or "message" in data


class TestEnvAccountsLoaded:
    """Tests that env accounts are properly loaded."""
    
    def test_instagram_accounts_exist(self):
        """Instagram accounts from env should exist."""
        response = httpx.get(f"{API_BASE}/api/social-accounts/accounts?platform=instagram", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        usernames = [a["username"] for a in data]
        # At least one of these should exist
        expected = ["the_isaiah_dupree", "the_isaiah_dupree_", "dupree_isaiah_", "dupree_isaiah"]
        found = any(u in usernames for u in expected)
        assert found, f"Expected one of {expected} in {usernames}"
    
    def test_tiktok_accounts_exist(self):
        """TikTok accounts from env should exist."""
        response = httpx.get(f"{API_BASE}/api/social-accounts/accounts?platform=tiktok", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        usernames = [a["username"] for a in data]
        expected = ["isaiah_dupree", "soursides_is_sour"]
        found = any(u in usernames for u in expected)
        assert found, f"Expected one of {expected} in {usernames}"
    
    def test_all_platforms_have_accounts(self):
        """All major platforms should have at least one account."""
        response = httpx.get(f"{API_BASE}/api/social-analytics/overview", timeout=10)
        assert response.status_code == 200
        data = response.json()
        
        platforms = [p["platform"] for p in data["platform_breakdown"]]
        expected_platforms = ["instagram", "tiktok", "youtube", "twitter"]
        
        for platform in expected_platforms:
            assert platform in platforms, f"Missing platform: {platform}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
