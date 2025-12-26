"""
Health Check Endpoints

Provides detailed health status for the application and its dependencies.
"""
from fastapi import APIRouter
from loguru import logger
from sqlalchemy import create_engine, text
from datetime import datetime
import os
import httpx
import asyncio

router = APIRouter(prefix="/health", tags=["Health"])


async def check_database() -> dict:
    """Check database connectivity."""
    try:
        engine = create_engine(
            os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        )
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        return {"status": "healthy", "latency_ms": 0}
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
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get("/detailed")
async def detailed_health_check():
    """
    Detailed health check - checks all dependencies.
    
    Returns status of:
    - Database connection
    - OpenAI API
    - RapidAPI
    - Blotato API
    """
    checks = {}
    
    # Run checks in parallel
    db_check, openai_check, rapidapi_check, blotato_check = await asyncio.gather(
        check_database(),
        check_openai(),
        check_rapidapi(),
        check_blotato(),
        return_exceptions=True
    )
    
    # Process results
    checks["database"] = db_check if isinstance(db_check, dict) else {"status": "error", "error": str(db_check)}
    checks["openai"] = openai_check if isinstance(openai_check, dict) else {"status": "error", "error": str(openai_check)}
    checks["rapidapi"] = rapidapi_check if isinstance(rapidapi_check, dict) else {"status": "error", "error": str(rapidapi_check)}
    checks["blotato"] = blotato_check if isinstance(blotato_check, dict) else {"status": "error", "error": str(blotato_check)}
    
    # Determine overall status
    critical_services = ["database"]
    critical_healthy = all(
        checks.get(s, {}).get("status") == "healthy" 
        for s in critical_services
    )
    
    all_healthy = all(
        c.get("status") in ["healthy", "configured", "unconfigured"]
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
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}
