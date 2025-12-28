"""
Backend Health API Endpoints
Provides detailed health status, error reports, and monitoring
"""
from fastapi import APIRouter, Depends
from loguru import logger
from typing import Optional

from services.backend_health_monitor import get_health_monitor

router = APIRouter(prefix="/api/health", tags=["Backend Health"])


@router.get("/detailed")
async def get_detailed_health():
    """
    Get comprehensive health status with all checks.
    Includes database, memory, external drive, and error stats.
    """
    monitor = get_health_monitor()
    return await monitor.run_all_checks()


@router.get("/errors")
async def get_recent_errors(limit: int = 20):
    """Get recent errors with details"""
    monitor = get_health_monitor()
    return {
        "errors": monitor.get_recent_errors(limit),
        "total_errors": monitor.error_count,
        "total_requests": monitor.request_count
    }


@router.get("/errors/summary")
async def get_error_summary(hours: int = 24):
    """Get error summary grouped by type and endpoint"""
    monitor = get_health_monitor()
    return monitor.get_error_summary(hours)


@router.get("/quick")
async def quick_health_check():
    """Quick health check - just confirms service is running"""
    monitor = get_health_monitor()
    return {
        "status": "running",
        "uptime_seconds": (monitor.start_time and 
            ((__import__('datetime').datetime.now() - monitor.start_time).total_seconds()) or 0),
        "request_count": monitor.request_count,
        "error_count": monitor.error_count
    }


@router.post("/test-error")
async def test_error_tracking():
    """Test endpoint to verify error tracking is working"""
    monitor = get_health_monitor()
    try:
        raise ValueError("Test error for verification - this is intentional")
    except Exception as e:
        monitor.record_error(e, "/api/health/test-error", {"test": True})
        return {
            "message": "Error tracked successfully",
            "error_count": monitor.error_count,
            "recent_errors": monitor.get_recent_errors(1)
        }
