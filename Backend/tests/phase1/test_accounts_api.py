"""
Tests for Phase 1: Multi-Platform Analytics - Accounts API
Tests account connection, syncing, and status endpoints
Uses REAL database connections
"""
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime

from main import app
from database.connection import get_db
from database.models import ConnectorConfig


@pytest.fixture
def client():
    """Synchronous test client"""
    return TestClient(app)


@pytest.fixture
async def async_client(db_session):
    """Async test client with database dependency override"""
    from httpx import ASGITransport
    from database.connection import init_db, async_session_maker
    
    # Ensure database is initialized for async_session_maker in endpoints
    if async_session_maker is None:
        await init_db()
    
    # Override get_db dependency to use test session
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


class TestAccountsAPI:
    """Test accounts API endpoints with REAL database"""
    
    @pytest.mark.asyncio
    async def test_get_connected_accounts(self, async_client, db_session, clean_db):
        """Test getting list of connected accounts"""
        # Create a test account with unique user_id to avoid constraint violations
        test_user_id = uuid.uuid4()  # Use unique UUID instead of fixed one
        test_account = ConnectorConfig(
            id=uuid.uuid4(),
            user_id=test_user_id,
            workspace_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),  # Use test workspace
            connector_type="instagram",
            config={"username": "testuser", "handle": "@testuser"},
            is_enabled=True
        )
        db_session.add(test_account)
        await db_session.commit()
        
        response = await async_client.get("/api/accounts/")
        if response.status_code != 200:
            print(f"Error response: {response.status_code}")
            print(f"Response body: {response.text}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(acc["platform"] == "instagram" for acc in data)
    
    @pytest.mark.asyncio
    async def test_connect_account(self, async_client, db_session, clean_db):
        """Test connecting a new account with REAL database"""
        payload = {
            "platform": "instagram",
            "connection_method": "rapidapi",
            "credentials": {"username": "newuser"},
            "username": "newuser"
        }
        response = await async_client.post("/api/accounts/connect", json=payload)
        assert response.status_code in [200, 201]
        
        if response.status_code in [200, 201]:
            data = response.json()
            assert "account_id" in data
            assert data["platform"] == "instagram"
            
            # Verify it was saved to database
            from sqlalchemy import select
            result = await db_session.execute(
                select(ConnectorConfig).where(ConnectorConfig.id == uuid.UUID(data["account_id"]))
            )
            account = result.scalar_one_or_none()
            assert account is not None
            assert account.connector_type == "instagram"
    
    def test_connect_account_invalid_platform(self, client):
        """Test connecting with invalid platform"""
        payload = {
            "platform": "invalid_platform",
            "connection_method": "rapidapi",
            "credentials": {"username": "testuser"},
            "username": "testuser"
        }
        response = client.post("/api/accounts/connect", json=payload)
        # Should return 400 for validation error
        assert response.status_code == 400
        data = response.json()
        assert "Invalid platform" in data.get("detail", "")
    
    @pytest.mark.asyncio
    async def test_sync_account(self, async_client, db_session, clean_db):
        """Test syncing an account with REAL database"""
        # Create a test account first with unique user_id
        test_user_id = uuid.uuid4()
        test_account = ConnectorConfig(
            id=uuid.uuid4(),
            user_id=test_user_id,
            workspace_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            connector_type="instagram",
            config={"username": "testuser"},
            is_enabled=True
        )
        db_session.add(test_account)
        await db_session.commit()
        
        sync_payload = {
            "account_id": str(test_account.id),
            "force_refresh": True
        }
        response = await async_client.post("/api/accounts/sync", json=sync_payload)
        # Should start sync (202) or complete (200)
        assert response.status_code in [200, 202]
    
    @pytest.mark.asyncio
    async def test_get_accounts_status(self, async_client, db_session, clean_db):
        """Test getting accounts status with REAL database"""
        # Create test accounts with unique user_id
        test_user_id = uuid.uuid4()
        test_workspace_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        accounts = [
            ConnectorConfig(
                id=uuid.uuid4(),
                user_id=test_user_id,
                workspace_id=test_workspace_id,
                connector_type="instagram",
                config={"username": "user1"},
                is_enabled=True
            ),
            ConnectorConfig(
                id=uuid.uuid4(),
                user_id=test_user_id,
                workspace_id=test_workspace_id,
                connector_type="tiktok",
                config={"username": "user2"},
                is_enabled=True
            )
        ]
        for account in accounts:
            db_session.add(account)
        await db_session.commit()
        
        response = await async_client.get("/api/accounts/status")
        assert response.status_code == 200
        data = response.json()
        assert "total_accounts" in data
        assert data["total_accounts"] >= 2
        assert "platforms_connected" in data


class TestAccountSync:
    """Test account synchronization functionality with REAL database"""
    
    @pytest.mark.asyncio
    async def test_youtube_sync(self, db_session, clean_db):
        """Test YouTube account sync with REAL database"""
        from api.endpoints.accounts import _sync_youtube_account
        
        # Create real account with unique user_id
        test_user_id = uuid.uuid4()
        account = ConnectorConfig(
            id=uuid.uuid4(),
            user_id=test_user_id,
            workspace_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            connector_type="youtube",
            config={"username": "testchannel", "account_id": "channel123"},
            is_enabled=True
        )
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)
        
        # Sync (may fail if YouTube API not configured, but should not crash)
        try:
            await _sync_youtube_account(db_session, account, "testchannel", "channel123")
        except Exception as e:
            # Expected if API keys not configured
            assert "API" in str(e) or "key" in str(e).lower() or "auth" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_rapidapi_sync(self, db_session, clean_db):
        """Test RapidAPI account sync with REAL database"""
        from api.endpoints.accounts import _sync_rapidapi_account
        
        # Create real account with unique user_id
        test_user_id = uuid.uuid4()
        account = ConnectorConfig(
            id=uuid.uuid4(),
            user_id=test_user_id,
            workspace_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            connector_type="instagram",
            config={"username": "testuser"},
            is_enabled=True
        )
        db_session.add(account)
        await db_session.commit()
        await db_session.refresh(account)
        
        # Sync (may fail if RapidAPI not configured, but should not crash)
        try:
            await _sync_rapidapi_account(db_session, account, "instagram", "testuser")
        except Exception as e:
            # Expected if API keys not configured
            assert "API" in str(e) or "key" in str(e).lower() or "auth" in str(e).lower()

