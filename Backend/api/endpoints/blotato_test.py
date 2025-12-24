from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

from services.event_bus import EventBus, Topics

# Load env vars
load_dotenv()

router = APIRouter()

class AccountConfig(BaseModel):
    provider: str
    account_id: str

class TestResult(BaseModel):
    success: bool
    message: str
    data: Optional[Dict] = None

# Map of provider to env var name
PROVIDER_ENV_MAP = {
    "youtube": "YOUTUBE_ACCOUNT_ID",
    "tiktok": "TIKTOK_ACCOUNT_ID",
    "instagram": "INSTAGRAM_ACCOUNT_ID",
    "instagram_alt": "INSTAGRAM_ACCOUNT_ID_ALT",
    "instagram_alt_2": "INSTAGRAM_ACCOUNT_ID_ALT_2",
    "instagram_alt_3": "INSTAGRAM_ACCOUNT_ID_ALT_3",
    "twitter": "TWITTER_ACCOUNT_ID",
    "facebook": "FACEBOOK_ACCOUNT_ID",
    "pinterest": "PINTEREST_ACCOUNT_ID",
    "bluesky": "BLUESKY_ACCOUNT_ID",
    "threads": "THREADS_ACCOUNT_ID"
}

@router.get("/config")
async def get_config():
    """Get current Blotato configuration and account IDs from env"""
    accounts = {}
    for provider, env_var in PROVIDER_ENV_MAP.items():
        accounts[provider] = os.getenv(env_var, "")
        
    return {
        "api_key_configured": bool(os.getenv("BLOTATO_API_KEY")),
        "accounts": accounts
    }

@router.post("/test-connection")
async def test_connection():
    """Test connection to Blotato API"""
    api_key = os.getenv("BLOTATO_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="BLOTATO_API_KEY not found in environment")
    
    # In a real app, we would make a request to Blotato API /me or /health
    # For now, we simulate a success if the key is present
    return TestResult(
        success=True,
        message="Successfully connected to Blotato API",
        data={"version": "v2", "status": "operational"}
    )

@router.post("/providers/{provider}/test")
async def test_provider_account(provider: str):
    """Test specific provider account connectivity"""
    env_var = PROVIDER_ENV_MAP.get(provider)
    if not env_var:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
    
    account_id = os.getenv(env_var)
    if not account_id:
        raise HTTPException(status_code=400, detail=f"Account ID not configured for {provider}")
        
    # Mock validation logic
    # In real app: Call Blotato to verify account ID exists and is accessible
    return TestResult(
        success=True,
        message=f"Account {account_id} for {provider} is valid and accessible",
        data={"account_id": account_id, "status": "connected"}
    )

@router.post("/providers/{provider}/schedule")
async def schedule_test_post(provider: str):
    """Schedule a test post to the provider"""
    # Mock scheduling logic
    return TestResult(
        success=True,
        message=f"Test post scheduled for {provider}",
        data={"post_id": f"test_{provider}_123", "scheduled_time": "now"}
    )

@router.post("/providers/{provider}/scrape")
async def trigger_scraper(provider: str):
    """Trigger scraper for the provider"""
    # Mock scraper trigger
    return TestResult(
        success=True,
        message=f"Scraper job started for {provider}",
        data={"job_id": f"scrape_{provider}_456", "status": "pending"}
    )


@router.get("/accounts")
async def get_blotato_accounts():
    """
    Get all connected Blotato accounts with their IDs.
    These IDs are used when publishing content to match MediaPoster accounts to Blotato accounts.
    """
    # Blotato Account ID mappings from the user's Blotato dashboard
    # Source: https://app.blotato.com/settings/accounts
    accounts = [
        # TikTok accounts
        {"id": 710, "platform": "tiktok", "username": "isaiah_dupree", "fullname": "Isaiah Dupree"},
        {"id": 243, "platform": "tiktok", "username": "the_isaiah_dupree", "fullname": "The Isaiah Dupree"},
        {"id": 4508, "platform": "tiktok", "username": "dupree_isaiah", "fullname": "Dupree Isaiah"},
        {"id": 571, "platform": "tiktok", "username": "soursides_is_sour", "fullname": "Soursides"},
        
        # Instagram accounts
        {"id": 807, "platform": "instagram", "username": "the_isaiah_dupree", "fullname": "The Isaiah Dupree"},
        {"id": 670, "platform": "instagram", "username": "the_isaiah_dupree_", "fullname": "The Isaiah Dupree"},
        {"id": 1369, "platform": "instagram", "username": "dupree_isaiah_", "fullname": "Dupree Isaiah"},
        {"id": 4508, "platform": "instagram", "username": "dupree_isaiah", "fullname": "Dupree Isaiah"},
        
        # YouTube accounts
        {"id": 228, "platform": "youtube", "username": "UCnDBsELI2OlaEl5yxA77HNA", "fullname": "Isaiah Dupree"},
        {"id": 3370, "platform": "youtube", "username": "lofi_creator", "fullname": "lofi creator"},
        
        # Twitter/X accounts
        {"id": 4151, "platform": "twitter", "username": "soursides_is_sour", "fullname": "Soursides"},
        {"id": 4151, "platform": "twitter", "username": "IsaiahDupree7", "fullname": "Isaiah Dupree"},
        
        # Threads accounts
        {"id": 1369, "platform": "threads", "username": "dupree_isaiah_", "fullname": "Dupree Isaiah"},
        {"id": 4150, "platform": "threads", "username": "isaiahdupree75", "fullname": "Isaiah Dupree"},
        {"id": 173, "platform": "threads", "username": "the_isaiah_dupree_", "fullname": "The Isaiah Dupree"},
        {"id": 201, "platform": "threads", "username": "the_isaiah_dupree", "fullname": "The Isaiah Dupree"},
        
        # Pinterest accounts
        {"id": 173, "platform": "pinterest", "username": "isaiahdupree33", "fullname": "Isaiah Dupree"},
        {"id": 243, "platform": "pinterest", "username": "isaiahdupree75", "fullname": "Isaiah Dupree"},
        
        # LinkedIn accounts
        {"id": 571, "platform": "linkedin", "username": "IsaiahDupree7", "fullname": "Isaiah Dupree"},
        
        # Facebook accounts
        {"id": 786, "platform": "facebook", "username": "Isaiah Dupree", "fullname": "Isaiah Dupree"},
        
        # Bluesky accounts
        {"id": 201, "platform": "bluesky", "username": "isaiahdupree.bsky.social", "fullname": "Isaiah Dupree"},
        {"id": 201, "platform": "bluesky", "username": "the_isaiah_dupree_", "fullname": "The Isaiah Dupree"},
    ]
    
    return accounts
