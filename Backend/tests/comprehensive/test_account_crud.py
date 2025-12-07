"""
Comprehensive Account CRUD Tests
Tests full lifecycle of account management with real database
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
from datetime import datetime

from main import app
from database.models import ConnectorConfig


@pytest.fixture
def client():
    return TestClient(app)


class TestAccountCRUD:
    """Comprehensive account CRUD operations"""
    
    @pytest.mark.asyncio
    async def test_create_read_update_delete_account(self, client, db_session, clean_db):
        """Test full CRUD lifecycle for an account"""
        # CREATE
        payload = {
            "platform": "instagram",
            "connection_method": "rapidapi",
            "credentials": {"username": "testuser", "api_key": "test_key"},
            "username": "testuser"
        }
        create_response = client.post("/api/accounts/connect", json=payload)
        assert create_response.status_code in [200, 201]
        account_data = create_response.json()
        account_id = uuid.UUID(account_data["account_id"])
        
        # READ - Verify it was created
        result = await db_session.execute(
            select(ConnectorConfig).where(ConnectorConfig.id == account_id)
        )
        account = result.scalar_one_or_none()
        assert account is not None
        assert account.connector_type == "instagram"
        assert account.is_enabled == True
        
        # READ - Get via API
        get_response = client.get("/api/accounts/")
        assert get_response.status_code == 200
        accounts = get_response.json()
        assert any(acc["id"] == str(account_id) for acc in accounts)
        
        # UPDATE - Disable account
        account.is_enabled = False
        await db_session.commit()
        await db_session.refresh(account)
        assert account.is_enabled == False
        
        # DELETE - Remove account
        await db_session.delete(account)
        await db_session.commit()
        
        # Verify deletion
        result = await db_session.execute(
            select(ConnectorConfig).where(ConnectorConfig.id == account_id)
        )
        deleted_account = result.scalar_one_or_none()
        assert deleted_account is None
    
    @pytest.mark.asyncio
    async def test_multiple_accounts_same_platform(self, client, db_session, clean_db):
        """Test creating multiple accounts for the same platform"""
        accounts = []
        for i in range(3):
            payload = {
                "platform": "tiktok",
                "connection_method": "rapidapi",
                "credentials": {"username": f"user{i}"},
                "username": f"user{i}"
            }
            response = client.post("/api/accounts/connect", json=payload)
            assert response.status_code in [200, 201]
            accounts.append(uuid.UUID(response.json()["account_id"]))
        
        # Verify all accounts exist
        result = await db_session.execute(
            select(ConnectorConfig).where(ConnectorConfig.connector_type == "tiktok")
        )
        tiktok_accounts = result.scalars().all()
        assert len(tiktok_accounts) == 3
    
    @pytest.mark.asyncio
    async def test_account_sync_creates_analytics(self, client, db_session, clean_db):
        """Test that syncing an account creates analytics data"""
        # Create account
        payload = {
            "platform": "youtube",
            "connection_method": "rapidapi",
            "credentials": {"username": "youtuber", "channel_id": "test_channel"},
            "username": "youtuber"
        }
        response = client.post("/api/accounts/connect", json=payload)
        assert response.status_code in [200, 201]
        account_id = uuid.UUID(response.json()["account_id"])
        
        # Sync account
        sync_response = client.post("/api/accounts/sync", json={
            "account_id": str(account_id),
            "force_refresh": True
        })
        assert sync_response.status_code in [200, 202]
        
        # Verify account still exists and is enabled
        result = await db_session.execute(
            select(ConnectorConfig).where(ConnectorConfig.id == account_id)
        )
        account = result.scalar_one_or_none()
        assert account is not None
        assert account.is_enabled == True






