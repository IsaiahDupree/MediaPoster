"""
MediaPoster FastAPI Backend
Main application entry point
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys

from config import settings
from api.endpoints import videos, ingestion, jobs, analytics, analysis, highlights, clips, content, segments, messages, briefs, people, content_metrics, email, app_config, calendar, workspaces
from database.connection import init_db, close_db

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>"
)
logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} | {message}"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events with error recovery"""
    # Startup
    logger.info("🚀 Starting MediaPoster Backend")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Initialize database with retry logic
    max_db_retries = 5
    db_retry_count = 0
    db_initialized = False
    
    while db_retry_count < max_db_retries and not db_initialized:
        try:
            await init_db()
            logger.success("✓ Database connected")
            db_initialized = True
        except Exception as e:
            db_retry_count += 1
            logger.error(f"✗ Database connection failed (attempt {db_retry_count}/{max_db_retries}): {e}")
            if db_retry_count < max_db_retries:
                import asyncio
                await asyncio.sleep(2 ** db_retry_count)  # Exponential backoff
            else:
                logger.critical("✗ Failed to initialize database after all retries. Continuing anyway...")
    
    # Initialize connectors
    try:
        from connectors import initialize_adapters
        initialize_adapters()
        logger.success("✓ Connectors initialized")
    except Exception as e:
        logger.warning(f"⚠️  Connector initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down MediaPoster Backend")
    try:
        await close_db()
        logger.success("✓ Database connections closed")
    except Exception as e:
        logger.error(f"✗ Error closing database connections: {e}")


# Create FastAPI app
app = FastAPI(
    title="MediaPoster API",
    description="Social media automation and content posting API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware - allowing frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5557",  # Frontend dev server
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5557",
        "https://mediaposter.vercel.app",  # Production domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint with actual service checks"""
    from database.connection import async_session_maker
    from sqlalchemy import text
    import time
    
    health_status = {
        "status": "healthy",
        "environment": settings.app_env,
        "timestamp": time.time(),
        "services": {}
    }
    
    # Check database
    db_status = "operational"
    try:
        if async_session_maker:
            async with async_session_maker() as session:
                result = await session.execute(text("SELECT 1"))
                result.scalar()
        else:
            db_status = "not_initialized"
    except Exception as e:
        db_status = f"error: {str(e)[:50]}"
        health_status["status"] = "degraded"
    
    health_status["services"]["database"] = db_status
    health_status["services"]["api"] = "operational"
    
    # Return appropriate status code
    status_code = 200 if health_status["status"] == "healthy" else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/api/health")
async def api_health_check():
    """API health check endpoint with database verification"""
    from database.connection import async_session_maker
    from sqlalchemy import text
    import time
    
    health_status = {
        "status": "healthy",
        "api_version": "2.0.0",
        "timestamp": time.time(),
        "services": {}
    }
    
    # Check database
    db_status = "operational"
    try:
        if async_session_maker:
            async with async_session_maker() as session:
                result = await session.execute(text("SELECT 1"))
                result.scalar()
        else:
            db_status = "not_initialized"
    except Exception as e:
        db_status = f"error: {str(e)[:50]}"
        health_status["status"] = "degraded"
    
    health_status["services"]["database"] = db_status
    
    # Return appropriate status code
    status_code = 200 if health_status["status"] == "healthy" else 503
    from fastapi.responses import JSONResponse
    return JSONResponse(content=health_status, status_code=status_code)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "MediaPoster API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# WebSocket for real-time updates
active_connections: list[WebSocket] = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"WebSocket client connected. Total: {len(active_connections)}")
    
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received: {data}")
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(active_connections)}")


async def broadcast_update(message: dict):
    """Broadcast message to all connected WebSocket clients"""
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Error broadcasting to client: {e}")


# Include routers
app.include_router(videos.router, prefix="/api/videos", tags=["videos"])
app.include_router(ingestion.router, prefix="/api/ingestion", tags=["ingestion"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["analytics"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(highlights.router, prefix="/api/highlights", tags=["highlights"])
app.include_router(clips.router, prefix="/api/clips", tags=["Clips"])
app.include_router(content.router, prefix="/api/content", tags=["Content Graph"])
app.include_router(segments.router, prefix="/api/segments", tags=["Segments"])
app.include_router(messages.router, prefix="/api/messages", tags=["Message Engine"])
app.include_router(briefs.router, prefix="/api/briefs", tags=["Content Briefs"])
app.include_router(people.router, prefix="/api/people", tags=["People Graph"])
app.include_router(content_metrics.router, prefix="/api/content-metrics", tags=["Content Metrics"])
app.include_router(email.router, prefix="/api/email", tags=["Email Service"])
app.include_router(app_config.router, prefix="/api/config", tags=["Configuration"])
app.include_router(calendar.router, prefix="/api", tags=["Calendar"])
app.include_router(workspaces.router, prefix="/api/workspaces", tags=["Workspaces"])

# Content Intelligence - Platform Publishing
from api.endpoints import platform_publishing
app.include_router(platform_publishing.router, prefix="/api/platform", tags=["Platform Publishing"])

# Content Intelligence - Analytics & Insights
from api.endpoints import analytics_insights
app.include_router(analytics_insights.router, prefix="/api/analytics-ci", tags=["Analytics & Insights"])

# Content Intelligence - Trending Content (TikTok)
from api.endpoints import trending
app.include_router(trending.router, prefix="/api/trending", tags=["Trending Content"])

# Thumbnail Generation
from api.endpoints import thumbnails
app.include_router(thumbnails.router, prefix="/api/thumbnails", tags=["Thumbnails"])

# API Usage Monitoring
from api.endpoints import api_usage
app.include_router(api_usage.router, prefix="/api/api-usage", tags=["API Usage"])

# Clip Management
from api.endpoints import clip_management
app.include_router(clip_management.router, prefix="/api/clip-management", tags=["Clip Management"])

# Enhanced Analysis (Phase 2)
from api.endpoints import enhanced_analysis
app.include_router(enhanced_analysis.router, prefix="/api/enhanced-analysis", tags=["Enhanced Analysis"])

# Publishing Queue
from api.endpoints import publishing_queue
app.include_router(publishing_queue.router, prefix="/api/publishing", tags=["Publishing Queue"])

# Goals
from api.endpoints import goals
app.include_router(goals.router, tags=["Goals"])

# Goal Recommendations (Phase 3)
from api.endpoints import goal_recommendations
app.include_router(goal_recommendations.router, tags=["Goal Recommendations"])

# Viral Video Analysis (Unified Schema)
from api.endpoints import viral_analysis
app.include_router(viral_analysis.router, prefix="/api", tags=["Viral Analysis"])

# Social Media Analytics (Scrapers)
from api.endpoints import social_analytics
app.include_router(social_analytics.router, prefix="/api/social-analytics", tags=["Social Analytics"])

# Blotato Test Page (Connectivity & Scrapers)
from api.endpoints import blotato_test
app.include_router(blotato_test.router, prefix="/api/blotato", tags=["Blotato Test"])

# Scheduling Workflow
from api.endpoints import scheduling
app.include_router(scheduling.router, prefix="/api/scheduling", tags=["Scheduling"])

# Dashboard Widgets
from api.endpoints import dashboard
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

# Inventory-aware scheduler
from api.endpoints import inventory_scheduler
app.include_router(inventory_scheduler.router, tags=["Inventory Scheduler"])

# Connected Accounts (Phase 1)
from api.endpoints import accounts
app.include_router(accounts.router, tags=["Accounts"])

# Post-Social Score (Phase 3)
from api.endpoints import post_social_score
app.include_router(post_social_score.router, tags=["Post-Social Score"])

# Goal Recommendations (Phase 3)
from api.endpoints import goal_recommendations
app.include_router(goal_recommendations.router, tags=["Goal Recommendations"])

# AI Coaching (Phase 3)
from api.endpoints import coaching
app.include_router(coaching.router, tags=["Coaching"])

# Optimal Posting Times (Phase 4)
from api.endpoints import optimal_posting_times
app.include_router(optimal_posting_times.router, tags=["Optimal Posting Times"])

# Media Creation (Phase 5)
from api.endpoints import media_creation
app.include_router(media_creation.router, tags=["Media Creation"])

# Publishing endpoints
from api.endpoints import publishing
app.include_router(publishing.router, prefix="/api/publishing", tags=["Publishing"])

# Storage Management endpoints
from api.endpoints import storage
app.include_router(storage.router, prefix="/api", tags=["Storage Management"])
# Duplicate analytics router removed


# Error handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler with CORS headers"""
    logger.error(f"Unhandled exception: {exc}")
    
    # Get the origin from the request
    origin = request.headers.get("origin")
    allowed_origins = [
        "http://localhost:5557",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5557",
        "https://mediaposter.vercel.app",
    ]
    
    # Build headers dict with CORS if origin is allowed
    headers = {}
    if origin in allowed_origins:
        headers["access-control-allow-origin"] = origin
        headers["access-control-allow-credentials"] = "true"
        headers["access-control-expose-headers"] = "*"
    
    return JSONResponse(
        status_code=500,
        headers=headers,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "An error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5555,
        reload=settings.debug,
        log_level="info"
    )
