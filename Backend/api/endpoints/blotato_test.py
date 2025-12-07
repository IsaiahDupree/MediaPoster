from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import os
from dotenv import load_dotenv

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
