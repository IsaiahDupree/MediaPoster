"""
MediaPoster Control Plane API

External command & control interface on port 9100.
Allows other services to submit commands, receive status, and fetch results.

Usage:
    uvicorn control_plane.main:app --host 127.0.0.1 --port 9100
    
    # Or with auto-reload for development
    uvicorn control_plane.main:app --host 127.0.0.1 --port 9100 --reload
"""

import os
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from .schemas import HealthResponse, ReadyResponse, ErrorResponse
from .routers import commands, jobs, events


API_KEY = os.environ.get("C2_API_KEY", "dev-api-key")
BIND_HOST = os.environ.get("C2_BIND_HOST", "127.0.0.1")
PORT = int(os.environ.get("C2_PORT", "9100"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    logger.info(f"Control Plane API starting on {BIND_HOST}:{PORT}")
    yield
    logger.info("Control Plane API shutting down")


app = FastAPI(
    title="MediaPoster Control Plane API",
    description="External command & control interface for MediaPoster",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def verify_api_key(request: Request):
    """Verify API key from header."""
    api_key = request.headers.get("X-API-Key")
    auth_header = request.headers.get("Authorization", "")
    
    if api_key == API_KEY:
        return True
    
    if auth_header.startswith("Bearer ") and auth_header[7:] == API_KEY:
        return True
    
    if os.environ.get("C2_AUTH_DISABLED", "false").lower() == "true":
        return True
    
    raise HTTPException(
        status_code=401,
        detail="Invalid or missing API key"
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=str(exc),
            code="INTERNAL_ERROR"
        ).model_dump()
    )


@app.get("/v1/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Liveness check - returns healthy if the service is running.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow()
    )


@app.get("/v1/ready", response_model=ReadyResponse, tags=["Health"])
async def readiness_check():
    """
    Readiness check - verifies all dependencies are available.
    """
    checks = {}
    all_ready = True
    
    try:
        import redis
        r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))
        r.ping()
        checks["redis"] = True
    except Exception:
        checks["redis"] = False
        all_ready = False
    
    try:
        from sqlalchemy import create_engine, text
        db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception:
        checks["database"] = False
        all_ready = False
    
    try:
        import httpx
        response = httpx.get("http://localhost:7070/health", timeout=2.0)
        checks["safari_automation"] = response.status_code == 200
    except Exception:
        checks["safari_automation"] = False
    
    return ReadyResponse(
        ready=all_ready,
        checks=checks
    )


app.include_router(
    commands.router,
    prefix="/v1",
    tags=["Commands"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    jobs.router,
    prefix="/v1",
    tags=["Jobs"],
    dependencies=[Depends(verify_api_key)]
)

app.include_router(
    events.router,
    prefix="/v1",
    tags=["Events"],
    dependencies=[Depends(verify_api_key)]
)


@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint with API info."""
    return {
        "service": "MediaPoster Control Plane",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/v1/health",
        "ready": "/v1/ready"
    }


def start():
    """Start the Control Plane API server."""
    import uvicorn
    uvicorn.run(
        "control_plane.main:app",
        host=BIND_HOST,
        port=PORT,
        reload=os.environ.get("C2_RELOAD", "false").lower() == "true"
    )


if __name__ == "__main__":
    start()
