"""
Safari Session API Endpoints
==============================
API for managing Safari automation sessions and accounts.

Features:
- SSM-001: Session Health Dashboard
- SSM-002: Safari Accounts Table
- SSM-003: Session Logs Table
- SSM-004: Multi-Account Registry
- SSM-005: Account Switching API
- SSM-007: Analytics API Endpoints
- SSM-015: Session Status API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from loguru import logger

from services.safari_session_service import get_safari_session_service


router = APIRouter(prefix="/api/safari/sessions", tags=["Safari Sessions"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class RegisterAccountRequest(BaseModel):
    """Request to register a new Safari account"""
    platform: str = Field(..., description="Platform name (twitter, tiktok, instagram, etc.)")
    username: str = Field(..., description="Platform username")
    display_name: Optional[str] = Field(None, description="Display name")
    refresh_interval_minutes: int = Field(30, description="Refresh interval in minutes")
    auto_refresh: bool = Field(True, description="Enable auto-refresh")
    priority: int = Field(0, description="Priority level (higher = more important)")


class UpdateStatusRequest(BaseModel):
    """Request to update account status"""
    is_logged_in: bool = Field(..., description="Whether logged in")
    indicator_found: Optional[str] = Field(None, description="CSS selector found")
    error: Optional[str] = Field(None, description="Error message if check failed")


class SetActiveAccountRequest(BaseModel):
    """Request to set active account for a platform"""
    account_id: UUID = Field(..., description="Account UUID to activate")


# ============================================================================
# ACCOUNT MANAGEMENT (SSM-002, SSM-004, SSM-005)
# ============================================================================

@router.post("/accounts/register")
async def register_account(request: RegisterAccountRequest):
    """
    Register a new Safari account (SSM-004)

    Adds a new account to the Safari session registry.

    Args:
        request: Account registration details

    Returns:
        Account ID and details
    """
    try:
        service = get_safari_session_service()

        account_id = await service.register_account(
            platform=request.platform,
            username=request.username,
            display_name=request.display_name,
            refresh_interval_minutes=request.refresh_interval_minutes,
            auto_refresh=request.auto_refresh,
            priority=request.priority
        )

        return {
            "success": True,
            "message": "Account registered successfully",
            "data": {
                "account_id": str(account_id),
                "platform": request.platform,
                "username": request.username
            }
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error registering account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts")
async def get_all_accounts():
    """
    Get all registered Safari accounts (SSM-002, SSM-004)

    Returns all accounts across all platforms.

    Returns:
        List of accounts with their details
    """
    try:
        service = get_safari_session_service()
        accounts = await service.get_all_accounts()

        return {
            "success": True,
            "data": {
                "accounts": accounts,
                "count": len(accounts)
            }
        }

    except Exception as e:
        logger.error(f"Error getting accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{account_id}")
async def get_account(account_id: UUID):
    """
    Get account details by ID (SSM-002)

    Args:
        account_id: Account UUID

    Returns:
        Account details
    """
    try:
        service = get_safari_session_service()
        account = await service.get_account(account_id)

        if not account:
            raise HTTPException(status_code=404, detail="Account not found")

        return {
            "success": True,
            "data": account
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/platform/{platform}")
async def get_platform_accounts(platform: str, active_only: bool = False):
    """
    Get all accounts for a platform (SSM-004)

    Args:
        platform: Platform name
        active_only: Only return active accounts

    Returns:
        List of accounts for the platform
    """
    try:
        service = get_safari_session_service()
        accounts = await service.get_platform_accounts(platform, active_only)

        return {
            "success": True,
            "data": {
                "platform": platform,
                "accounts": accounts,
                "count": len(accounts)
            }
        }

    except Exception as e:
        logger.error(f"Error getting platform accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/{account_id}/status")
async def update_account_status(account_id: UUID, request: UpdateStatusRequest):
    """
    Update account login status (SSM-002)

    Args:
        account_id: Account UUID
        request: Status update details

    Returns:
        Success confirmation
    """
    try:
        service = get_safari_session_service()

        await service.update_account_status(
            account_id=account_id,
            is_logged_in=request.is_logged_in,
            indicator_found=request.indicator_found,
            error=request.error
        )

        return {
            "success": True,
            "message": "Account status updated"
        }

    except Exception as e:
        logger.error(f"Error updating account status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/platform/{platform}/set-active")
async def set_active_account(platform: str, request: SetActiveAccountRequest):
    """
    Set active account for a platform (SSM-005)

    Deactivates all other accounts for the platform and activates the specified account.

    Args:
        platform: Platform name
        request: Account to activate

    Returns:
        Success confirmation
    """
    try:
        service = get_safari_session_service()

        await service.set_active_account(
            platform=platform,
            account_id=request.account_id
        )

        return {
            "success": True,
            "message": f"Account activated for {platform}",
            "data": {
                "platform": platform,
                "account_id": str(request.account_id)
            }
        }

    except Exception as e:
        logger.error(f"Error setting active account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SESSION LOGGING (SSM-003, SSM-007)
# ============================================================================

@router.get("/logs")
async def get_session_logs(
    account_id: Optional[UUID] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
):
    """
    Get session logs (SSM-003, SSM-007)

    Retrieve session event logs with optional filtering.

    Args:
        account_id: Filter by account ID
        event_type: Filter by event type
        status: Filter by status
        limit: Maximum number of logs (default: 100, max: 500)

    Returns:
        List of session logs
    """
    try:
        # Limit to max 500
        limit = min(limit, 500)

        service = get_safari_session_service()
        logs = await service.get_session_logs(
            account_id=account_id,
            event_type=event_type,
            status=status,
            limit=limit
        )

        return {
            "success": True,
            "data": {
                "logs": logs,
                "count": len(logs),
                "filters": {
                    "account_id": str(account_id) if account_id else None,
                    "event_type": event_type,
                    "status": status,
                    "limit": limit
                }
            }
        }

    except Exception as e:
        logger.error(f"Error getting session logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/account/{account_id}")
async def get_account_logs(account_id: UUID, limit: int = 100):
    """
    Get logs for a specific account (SSM-003)

    Args:
        account_id: Account UUID
        limit: Maximum number of logs

    Returns:
        List of logs for the account
    """
    try:
        service = get_safari_session_service()
        logs = await service.get_session_logs(account_id=account_id, limit=limit)

        return {
            "success": True,
            "data": {
                "account_id": str(account_id),
                "logs": logs,
                "count": len(logs)
            }
        }

    except Exception as e:
        logger.error(f"Error getting account logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SESSION HEALTH (SSM-001, SSM-015)
# ============================================================================

@router.get("/health")
async def get_session_health():
    """
    Get session health status (SSM-001, SSM-015)

    Returns overall session health across all platforms and accounts.

    Returns:
        Session health metrics and platform status
    """
    try:
        service = get_safari_session_service()
        health = await service.get_session_health()

        return {
            "success": True,
            "data": health
        }

    except Exception as e:
        logger.error(f"Error getting session health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_session_status():
    """
    Get quick session status (SSM-015)

    Returns a simplified status view for dashboard display.

    Returns:
        Quick status overview
    """
    try:
        service = get_safari_session_service()
        health = await service.get_session_health()

        # Simplify for quick status
        platforms = health.get("platforms", [])

        status_summary = {
            "active": sum(1 for p in platforms if p.get("status") == "active"),
            "stale": sum(1 for p in platforms if p.get("status") == "stale"),
            "expired": sum(1 for p in platforms if p.get("status") == "expired"),
            "no_account": sum(1 for p in platforms if p.get("status") == "no_active_account")
        }

        return {
            "success": True,
            "data": {
                "summary": status_summary,
                "total_accounts": health.get("total_accounts", 0),
                "logged_in_count": health.get("logged_in_count", 0),
                "last_updated": health.get("last_updated")
            }
        }

    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/platforms")
async def get_platform_list():
    """
    Get list of supported platforms

    Returns:
        List of platform names
    """
    from automation.safari_session_manager import Platform

    return {
        "success": True,
        "data": {
            "platforms": [p.value for p in Platform],
            "count": len(Platform)
        }
    }
