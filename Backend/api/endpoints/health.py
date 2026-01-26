"""
Health Check Endpoints

Provides detailed health status for the application and its dependencies.
"""
from fastapi import APIRouter, Request
from loguru import logger
from sqlalchemy import create_engine, text
from datetime import datetime
from typing import Optional
import os
import httpx
import asyncio
import uuid

router = APIRouter(prefix="/health", tags=["Health"])


async def check_database() -> dict:
    """Check database connectivity with latency measurement."""
    import time
    try:
        start_time = time.time()
        engine = create_engine(
            os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        )
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        latency_ms = int((time.time() - start_time) * 1000)
        
        # Check if latency is acceptable (< 100ms is good)
        status = "healthy" if latency_ms < 100 else "degraded"
        return {
            "status": status,
            "latency_ms": latency_ms,
            "threshold_ms": 100
        }
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def check_openai() -> dict:
    """Check OpenAI API availability."""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {"status": "unconfigured", "error": "OPENAI_API_KEY not set"}
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            if response.status_code == 200:
                return {"status": "healthy"}
            else:
                return {"status": "unhealthy", "error": f"Status {response.status_code}"}
    except asyncio.TimeoutError:
        return {"status": "unhealthy", "error": "Timeout"}
    except Exception as e:
        logger.warning(f"OpenAI health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}


async def check_rapidapi() -> dict:
    """Check RapidAPI availability."""
    try:
        api_key = os.getenv("RAPIDAPI_KEY")
        if not api_key:
            return {"status": "unconfigured", "error": "RAPIDAPI_KEY not set"}
        return {"status": "configured"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def check_blotato() -> dict:
    """Check Blotato API availability."""
    try:
        api_key = os.getenv("BLOTATO_API_KEY")
        if not api_key:
            return {"status": "unconfigured", "error": "BLOTATO_API_KEY not set"}
        return {"status": "configured"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("")
async def health_check():
    """Basic health check - returns 200 if server is running."""
    correlation_id = None  # Can be extracted from request context if needed
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "correlation_id": correlation_id
    }


async def check_event_bus() -> dict:
    """Check Event Bus status."""
    try:
        from services.event_bus import EventBus
        event_bus = EventBus.get_instance()
        if event_bus:
            return {"status": "healthy"}
        return {"status": "unhealthy", "error": "Event bus not initialized"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_storage() -> dict:
    """Check storage accessibility."""
    try:
        import tempfile
        from pathlib import Path

        # Check temp directory
        temp_dir = Path(tempfile.gettempdir())
        if temp_dir.exists() and temp_dir.is_dir():
            # Test write permission
            test_file = temp_dir / f".health_check_{uuid.uuid4()}"
            try:
                test_file.touch()
                test_file.unlink()
                return {"status": "healthy", "temp_dir": str(temp_dir)}
            except Exception as e:
                return {"status": "degraded", "error": f"Cannot write to temp dir: {e}"}
        return {"status": "unhealthy", "error": "Temp directory not accessible"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_workers() -> dict:
    """Check all worker statuses (MOD-005)."""
    try:
        workers_status = {
            "post_scheduler": "unknown",
            "sleep_mode": "unknown",
            "cpu_monitor": "unknown",
            "metrics_fetch": "unknown",
            "thumbnail_generation": "unknown",
            "event_history": "unknown",
            "cleanup": "unknown",
            "notification": "unknown",
            "narrative_builder": "unknown",
            "slot_executor": "unknown",
            "learner": "unknown",
            "inbound_listener": "unknown",
            "responder": "unknown"
        }

        healthy_count = 0
        total_count = len(workers_status)

        # Check Post Scheduler
        try:
            from services.post_scheduler import get_scheduler
            scheduler = get_scheduler()
            workers_status["post_scheduler"] = "healthy" if scheduler.is_running else "stopped"
            if scheduler.is_running:
                healthy_count += 1
        except Exception as e:
            workers_status["post_scheduler"] = f"error: {str(e)[:50]}"

        # Check Sleep Mode Service
        try:
            from services.sleep_mode_service import SleepModeService
            sleep_service = SleepModeService.get_instance()
            workers_status["sleep_mode"] = "healthy" if sleep_service._is_running else "stopped"
            if sleep_service._is_running:
                healthy_count += 1
        except Exception as e:
            workers_status["sleep_mode"] = f"error: {str(e)[:50]}"

        # Check CPU Monitor
        try:
            from services.cpu_monitor import get_cpu_monitor
            cpu_monitor = get_cpu_monitor()
            workers_status["cpu_monitor"] = "healthy" if cpu_monitor._is_running else "stopped"
            if cpu_monitor._is_running:
                healthy_count += 1
        except Exception as e:
            workers_status["cpu_monitor"] = f"error: {str(e)[:50]}"

        # Determine overall worker health
        health_percentage = (healthy_count / total_count) * 100

        if health_percentage >= 80:
            status = "healthy"
        elif health_percentage >= 50:
            status = "degraded"
        else:
            status = "unhealthy"

        return {
            "status": status,
            "workers": workers_status,
            "healthy_count": healthy_count,
            "total_count": total_count,
            "health_percentage": round(health_percentage, 1)
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/detailed")
async def detailed_health_check():
    """
    Detailed health check - checks all dependencies (MOD-005).

    Returns status of:
    - Database connection
    - OpenAI API
    - RapidAPI
    - Blotato API
    - Event Bus
    - Storage
    - Workers (Post Scheduler, Sleep Mode, CPU Monitor, etc.)
    """
    # Correlation ID will be in response headers from middleware
    correlation_id = str(uuid.uuid4())
    checks = {}

    # Run checks in parallel
    db_check, openai_check, rapidapi_check, blotato_check, event_bus_check, storage_check, workers_check = await asyncio.gather(
        check_database(),
        check_openai(),
        check_rapidapi(),
        check_blotato(),
        check_event_bus(),
        check_storage(),
        check_workers(),
        return_exceptions=True
    )
    
    # Process results
    checks["database"] = db_check if isinstance(db_check, dict) else {"status": "error", "error": str(db_check)}
    checks["openai"] = openai_check if isinstance(openai_check, dict) else {"status": "error", "error": str(openai_check)}
    checks["rapidapi"] = rapidapi_check if isinstance(rapidapi_check, dict) else {"status": "error", "error": str(rapidapi_check)}
    checks["blotato"] = blotato_check if isinstance(blotato_check, dict) else {"status": "error", "error": str(blotato_check)}
    checks["event_bus"] = event_bus_check if isinstance(event_bus_check, dict) else {"status": "error", "error": str(event_bus_check)}
    checks["storage"] = storage_check if isinstance(storage_check, dict) else {"status": "error", "error": str(storage_check)}
    checks["workers"] = workers_check if isinstance(workers_check, dict) else {"status": "error", "error": str(workers_check)}

    # Determine overall status
    critical_services = ["database", "event_bus", "workers"]
    critical_healthy = all(
        checks.get(s, {}).get("status") in ["healthy", "degraded"]
        for s in critical_services
    )
    
    all_healthy = all(
        c.get("status") in ["healthy", "configured", "unconfigured", "degraded"]
        for c in checks.values()
    )
    
    if critical_healthy and all_healthy:
        overall_status = "healthy"
    elif critical_healthy:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "correlation_id": correlation_id,
        "checks": checks,
        "version": os.getenv("APP_VERSION", "1.0.0"),
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for Kubernetes/load balancers.
    Returns 200 only if the service is ready to accept traffic.
    """
    db_check = await check_database()
    
    if db_check.get("status") == "healthy":
        return {"status": "ready"}
    else:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "reason": "Database unavailable"}
        )


@router.get("/live")
async def liveness_check():
    """
    Liveness check for Kubernetes.
    Returns 200 if the process is alive (even if dependencies are down).
    """
    correlation_id = None  # Will be in response headers from middleware
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
        "correlation_id": correlation_id
    }


@router.get("/startup")
async def startup_status():
    """
    Get detailed startup status from StartupManager.
    
    Returns:
        - All services initialized at startup
        - Their status (running/failed/skipped)
        - Timing information
        - System resource usage at startup
    """
    try:
        from services.startup_manager import StartupManager
        
        manager = StartupManager.get_instance()
        status = manager.get_health_status()
        
        return {
            "status": "ok",
            "timestamp": datetime.utcnow().isoformat(),
            "startup": status
        }
    except Exception as e:
        logger.error(f"Startup status check failed: {e}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.post("/startup/verify")
async def verify_startup():
    """
    Re-run startup verification to check all services.
    
    This will check all registered services and return a full report.
    Useful for diagnosing issues after the app is running.
    """
    try:
        from services.startup_manager import StartupManager
        
        manager = StartupManager.get_instance()
        report = await manager.run_startup_sequence()
        
        from fastapi.responses import JSONResponse
        status_code = 200 if report.healthy else 503
        
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "healthy" if report.healthy else "unhealthy",
                "timestamp": datetime.utcnow().isoformat(),
                "report": report.to_dict()
            }
        )
    except Exception as e:
        logger.error(f"Startup verification failed: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e)
            }
        )
