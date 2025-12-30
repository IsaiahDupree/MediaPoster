"""
MediaPoster FastAPI Backend
Main application entry point
"""
from dotenv import load_dotenv
load_dotenv()  # Load .env file before any other imports

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
import os
from contextlib import asynccontextmanager
from loguru import logger
import sys

from config import settings
from api.endpoints import videos, ingestion, jobs, analytics, analysis, highlights, clips, content, segments, messages, briefs, people, content_metrics, email, app_config, calendar, workspaces, trends
from api.endpoints import event_history, video_routing_api
from api.endpoints import tts, matting, remotion, pipeline, music, visuals
from database.connection import init_db, close_db

# Event Bus imports
from services.event_bus import EventBus, Topics
from services.workflow_manager import WorkflowManager
from services.analytics_refresh_handler import get_analytics_refresh_handler

# Configure logging with enhanced output
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> | <level>{message}</level>",
    backtrace=True,
    diagnose=True,
)
logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} | {message}",
    backtrace=True,
    diagnose=True,
)
logger.add(
    "logs/errors.log",
    rotation="100 MB",
    retention="30 days",
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}\n{exception}",
    backtrace=True,
    diagnose=True,
)


def run_startup_checks():
    """Run startup checks to ensure required services are running"""
    try:
        from scripts.startup_checks import ensure_postgres_running, parse_database_url
        host, port = parse_database_url()
        logger.info(f"🔍 Checking PostgreSQL at {host}:{port}...")
        
        if ensure_postgres_running(max_retries=3, wait_seconds=3):
            logger.success("✓ PostgreSQL is running")
            return True
        else:
            logger.error("❌ PostgreSQL could not be started")
            return False
    except Exception as e:
        logger.warning(f"Startup checks skipped: {e}")
        return True  # Continue anyway, let DB connection handle it


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events with error recovery"""
    # Startup
    logger.info("🚀 Starting MediaPoster Backend")
    logger.info(f"Environment: {settings.app_env}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Run startup checks (ensure DB is running)
    run_startup_checks()
    
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
    
    # Initialize Event Bus and Workflow Manager
    event_bus = None
    workflow_manager = None
    try:
        event_bus = EventBus.get_instance()
        event_bus.set_source("mediaposter-backend")
        workflow_manager = WorkflowManager.get_instance(event_bus)
        await event_bus.publish(Topics.SYSTEM_STARTUP, {"environment": settings.app_env})
        logger.success("✓ Event Bus initialized")
        
        # Initialize analytics refresh handler (subscribes to publish events)
        try:
            get_analytics_refresh_handler()
            logger.success("✓ Analytics refresh handler initialized")
        except Exception as e:
            logger.warning(f"⚠️  Analytics refresh handler initialization failed: {e}")
    except Exception as e:
        logger.warning(f"⚠️  Event Bus initialization failed: {e}")
    
    # Start the Post Scheduler background worker
    post_scheduler = None
    try:
        from services.post_scheduler import PostScheduler
        post_scheduler = PostScheduler()
        await post_scheduler.start()
        logger.success("✓ Post Scheduler started (checking every 60s)")
    except Exception as e:
        logger.warning(f"⚠️  Post Scheduler failed to start: {e}")
    
    # Start the Metrics Fetch Worker (auto-fetches metrics after publish)
    metrics_worker = None
    try:
        from services.workers.metrics_fetch_worker import MetricsFetchWorker
        from services.workers.thumbnail_generation_worker import ThumbnailGenerationWorker
        from services.workers.event_history_worker import EventHistoryWorker
        
        metrics_worker = MetricsFetchWorker(event_bus)
        await metrics_worker.start()
        
        thumbnail_worker = ThumbnailGenerationWorker(event_bus)
        await thumbnail_worker.start()
        
        # Start event history worker (persists all events to database)
        event_history_worker = EventHistoryWorker(event_bus)
        await event_history_worker.start()
        logger.success("✓ Event History Worker started")
        logger.success("✓ Metrics Fetch Worker started")
    except Exception as e:
        logger.warning(f"⚠️  Metrics Fetch Worker failed to start: {e}")
    
    # Start the Cleanup Worker (cleans up orphaned resources on media deletion)
    cleanup_worker = None
    try:
        from services.workers.cleanup_worker import CleanupWorker
        cleanup_worker = CleanupWorker(event_bus)
        await cleanup_worker.start()
        logger.success("✓ Cleanup Worker started")
    except Exception as e:
        logger.warning(f"⚠️  Cleanup Worker failed to start: {e}")
    
    # Start the Notification Worker (generates notifications for key events)
    notification_worker = None
    try:
        from services.workers.notification_worker import NotificationWorker
        notification_worker = NotificationWorker(event_bus)
        await notification_worker.start()
        logger.success("✓ Notification Worker started")
    except Exception as e:
        logger.warning(f"⚠️  Notification Worker failed to start: {e}")
    
    # Start the Narrative Builder Worker (auto-updates signals on publish/analysis)
    narrative_worker = None
    try:
        from services.workers.narrative_builder_worker import NarrativeBuilderWorker
        narrative_worker = NarrativeBuilderWorker(event_bus)
        await narrative_worker.start()
        logger.success("✓ Narrative Builder Worker started")
    except Exception as e:
        logger.warning(f"⚠️  Narrative Builder Worker failed to start: {e}")
    
    # Start the TTS Worker (text-to-speech generation service)
    tts_worker = None
    try:
        from services.tts.worker import TTSWorker
        tts_worker = TTSWorker(event_bus)
        await tts_worker.start()
        logger.success("✓ TTS Worker started")
    except Exception as e:
        logger.warning(f"⚠️  TTS Worker failed to start: {e}")
    
    # Start the Matting Worker (video matting/segmentation service)
    matting_worker = None
    try:
        from services.matting.worker import MattingWorker
        matting_worker = MattingWorker(event_bus)
        await matting_worker.start()
        logger.success("✓ Matting Worker started")
    except Exception as e:
        logger.warning(f"⚠️  Matting Worker failed to start: {e}")
    
    # Start the Remotion Worker (video composition and rendering service)
    remotion_worker = None
    try:
        from services.remotion.worker import RemotionWorker
        remotion_worker = RemotionWorker(event_bus)
        await remotion_worker.start()
        logger.success("✓ Remotion Worker started")
    except Exception as e:
        logger.warning(f"⚠️  Remotion Worker failed to start: {e}")
    
    # Start the Music Worker (music generation and selection service)
    music_worker = None
    try:
        from services.music.worker import MusicWorker
        music_worker = MusicWorker(event_bus)
        await music_worker.start()
        logger.success("✓ Music Worker started")
    except Exception as e:
        logger.warning(f"⚠️  Music Worker failed to start: {e}")
    
    # Start the Visuals Worker (visual assets service)
    visuals_worker = None
    try:
        from services.visuals.worker import VisualsWorker
        visuals_worker = VisualsWorker(event_bus)
        await visuals_worker.start()
        logger.success("✓ Visuals Worker started")
    except Exception as e:
        logger.warning(f"⚠️  Visuals Worker failed to start: {e}")
    
    # Start the Format Video Render Worker (format-agnostic video rendering)
    format_render_worker = None
    try:
        from services.video_renderer.format_worker import FormatVideoRenderWorker
        format_render_worker = FormatVideoRenderWorker(event_bus)
        await format_render_worker.start()
        logger.success("✓ Format Video Render Worker started")
    except Exception as e:
        logger.warning(f"⚠️  Format Video Render Worker failed to start: {e}")
    
    yield
    
    # Stop the Notification Worker on shutdown
    if notification_worker:
        try:
            await notification_worker.stop()
            logger.success("✓ Notification Worker stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping Notification Worker: {e}")
    
    # Stop the Narrative Builder Worker on shutdown
    if narrative_worker:
        try:
            await narrative_worker.stop()
            logger.success("✓ Narrative Builder Worker stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping Narrative Builder Worker: {e}")
    
    # Stop the Cleanup Worker on shutdown
    if cleanup_worker:
        try:
            await cleanup_worker.stop()
            logger.success("✓ Cleanup Worker stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping Cleanup Worker: {e}")
    
    # Stop the Metrics Fetch Worker on shutdown
    if metrics_worker:
        try:
            await metrics_worker.stop()
            logger.success("✓ Metrics Fetch Worker stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping Metrics Fetch Worker: {e}")
    
    # Stop the scheduler on shutdown
    if post_scheduler:
        try:
            await post_scheduler.stop()
            logger.success("✓ Post Scheduler stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping Post Scheduler: {e}")
    
    # Stop the TTS Worker on shutdown
    if tts_worker:
        try:
            await tts_worker.stop()
            logger.success("✓ TTS Worker stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping TTS Worker: {e}")
    
    # Stop the Matting Worker on shutdown
    if matting_worker:
        try:
            await matting_worker.stop()
            logger.success("✓ Matting Worker stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping Matting Worker: {e}")
    
    # Stop the Remotion Worker on shutdown
    if remotion_worker:
        try:
            await remotion_worker.stop()
            logger.success("✓ Remotion Worker stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping Remotion Worker: {e}")
    
    # Stop the Music Worker on shutdown
    if music_worker:
        try:
            await music_worker.stop()
            logger.success("✓ Music Worker stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping Music Worker: {e}")
    
    # Stop the Visuals Worker on shutdown
    if visuals_worker:
        try:
            await visuals_worker.stop()
            logger.success("✓ Visuals Worker stopped")
        except Exception as e:
            logger.warning(f"⚠️  Error stopping Visuals Worker: {e}")
    
    # Shutdown Event Bus
    if event_bus:
        try:
            await event_bus.shutdown()
            logger.success("✓ Event Bus shutdown")
        except Exception as e:
            logger.warning(f"⚠️  Error shutting down Event Bus: {e}")
    
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

# Error tracking middleware
from middleware.error_tracking import ErrorTrackingMiddleware, RequestLoggingMiddleware
app.add_middleware(ErrorTrackingMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# BUG FIX: Add correlation ID middleware (must be early in the stack)
from middleware.correlation_id import CorrelationIDMiddleware
app.add_middleware(CorrelationIDMiddleware)

# BUG FIX: Add rate limiting middleware
from middleware.rate_limiting import RateLimitMiddleware
app.add_middleware(RateLimitMiddleware, default_limit=100, default_window=60)

# BUG FIX: Add global exception handlers for standardized error handling
from utils.error_handling import handle_exception, AppError, ValidationError

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """Handle custom application errors."""
    correlation_id = getattr(request.state, "correlation_id", exc.correlation_id)
    http_exc = exc.to_http_exception()
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail,
        headers={"X-Correlation-ID": correlation_id}
    )

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    # Convert errors to safe string representation to avoid loguru format issues
    errors_list = exc.errors()
    errors_str = str(errors_list).replace("{", "{{").replace("}", "}}")
    logger.warning(f"[{correlation_id}] Validation error: {errors_str}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "correlation_id": correlation_id,
            "error_code": "VALIDATION_ERROR",
            "details": errors_list
        },
        headers={"X-Correlation-ID": correlation_id}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions."""
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    http_exc = handle_exception(exc, correlation_id, {"path": request.url.path, "method": request.method})
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail,
        headers={"X-Correlation-ID": correlation_id}
    )

# Mount static files for thumbnails
THUMBNAIL_DIR = "/tmp/mediaposter/thumbnails"
if os.path.exists(THUMBNAIL_DIR):
    app.mount("/thumbnails", StaticFiles(directory=THUMBNAIL_DIR), name="thumbnails")


# Serve video files by ID
@app.get("/api/media/video/{video_id}")
async def serve_video(video_id: str):
    """Serve video file by video ID from database"""
    from sqlalchemy import create_engine, text
    import mimetypes
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT source_uri FROM videos WHERE id = :id"), {"id": video_id}).fetchone()
        
    if not result or not result[0]:
        return JSONResponse(status_code=404, content={"error": "Video not found"})
    
    file_path = result[0]
    if not os.path.exists(file_path):
        return JSONResponse(status_code=404, content={"error": "Video file not found on disk"})
    
    mime_type, _ = mimetypes.guess_type(file_path)
    return FileResponse(
        file_path,
        media_type=mime_type or "video/mp4",
        filename=os.path.basename(file_path)
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

# Trends & Analytics (Standalone System)
app.include_router(trends.router, prefix="/api", tags=["Trends & Analytics"])

# AI Video Generation
from api.endpoints import ai_video
app.include_router(ai_video.router, prefix="/api", tags=["AI Video Generation"])

# AI Video Generation with Pub/Sub (Sora, Runway, etc.)
from api.endpoints import ai_video_generation
app.include_router(ai_video_generation.router, tags=["AI Video Generation Pub/Sub"])

# Format-Agnostic Video Rendering API
try:
    from api.endpoints import video_format_api
    app.include_router(video_format_api.router, tags=["Video Format Rendering"])
    logger.success("✓ Video Format API registered")
except Exception as e:
    logger.warning(f"⚠️  Video Format API registration failed: {e}")

# Comment Engagement & Automation with Pub/Sub (Audience, Fans, Inbox)
from api.endpoints import comment_engagement
app.include_router(comment_engagement.router, tags=["Comment Engagement"])

# Knowledge Base (Rules, Templates, Playbooks)
from api.endpoints import knowledge_base
app.include_router(knowledge_base.router, prefix="/api", tags=["Knowledge Base"])

# Trend Opportunities (Opportunity Signals for Narrative Builder & Experiments)
from api.endpoints import trend_opportunities
app.include_router(trend_opportunities.router, prefix="/api", tags=["Trend Opportunities"])

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

# Posted Content Tracking
from api.endpoints import posted_content
app.include_router(posted_content.router, prefix="/api", tags=["Posted Content"])

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

# Platform Data Orchestrator (Unified Failover System)
from api.endpoints import data_orchestrator
app.include_router(data_orchestrator.router, prefix="/api/orchestrator", tags=["Data Orchestrator"])

# Data Hydration (Centralized Data for All Pages)
from api.endpoints import data_hydration
app.include_router(data_hydration.router, prefix="/api/hydration", tags=["Data Hydration"])

# Content Calendar & Schedule API
from api.endpoints import schedule
app.include_router(schedule.router, prefix="/api/schedule", tags=["Content Schedule"])

# Post Scheduler (Background Worker)
from api.endpoints import post_scheduler_api
app.include_router(post_scheduler_api.router, prefix="/api/scheduler", tags=["Post Scheduler"])

# Database Health Checks (Docker/Supabase)
from api.endpoints import db_health
app.include_router(db_health.router, prefix="/api/db-health", tags=["Database Health"])

# Analyzed Content (for scheduling modal)
from api.endpoints import analyzed_content
app.include_router(analyzed_content.router, prefix="/api/analyzed-content", tags=["Analyzed Content"])

# Social Media Accounts (RapidAPI Live Fetch)
from api.endpoints import social_accounts
app.include_router(social_accounts.router, prefix="/api/social-accounts", tags=["Social Accounts"])
# Also register at /api/social for frontend compatibility
app.include_router(social_accounts.router, prefix="/api/social", tags=["Social Accounts"])

# YouTube Analytics (Google Cloud Console / YouTube Data API v3)
from api.endpoints import youtube_analytics
app.include_router(youtube_analytics.router, prefix="/api/youtube-analytics", tags=["YouTube Analytics"])

# TikTok Analytics (Safari Automation)
from api.endpoints import tiktok_analytics
app.include_router(tiktok_analytics.router, prefix="/api/tiktok-analytics", tags=["TikTok Analytics"])

# RapidAPI Comments (TikTok, Instagram, Threads, Facebook)
from api.endpoints import rapidapi_comments
app.include_router(rapidapi_comments.router, prefix="/api/rapidapi-comments", tags=["RapidAPI Comments"])

# Blotato Test Page (Connectivity & Scrapers)
from api.endpoints import blotato_test
app.include_router(blotato_test.router, prefix="/api/blotato", tags=["Blotato Test"])

# Scheduling Workflow
from api.endpoints import scheduling
app.include_router(scheduling.router, prefix="/api/scheduling", tags=["Scheduling"])

# Event Bus & Workflows (Pub/Sub Architecture)
from api.endpoints import events, workflows, websocket
app.include_router(events.router, prefix="/api", tags=["Events"])
app.include_router(workflows.router, prefix="/api", tags=["Workflows"])
app.include_router(websocket.router, prefix="/api", tags=["WebSocket"])

# Event History (Querying & Replay)
app.include_router(event_history.router, tags=["Event History"])

# Trend Queries (Advanced Discovery System)
from api.endpoints import trend_queries_api
app.include_router(trend_queries_api.router, tags=["Trend Queries"])

# Video Orientation & Routing (YouTube Integration)
app.include_router(video_routing_api.router, prefix="/api/videos", tags=["Video Routing"])

# Dashboard Widgets
from api.endpoints import dashboard
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

# Inventory-aware scheduler
from api.endpoints import inventory_scheduler
app.include_router(inventory_scheduler.router, tags=["Inventory Scheduler"])

# Connected Accounts (Phase 1)
from api.endpoints import accounts
app.include_router(accounts.router, tags=["Accounts"])

# App Settings
from api.endpoints import app_settings
app.include_router(app_settings.router, tags=["Settings"])

# Health Checks
from api.endpoints import health
app.include_router(health.router, tags=["Health"])

# Trend Intelligence System (v1)
try:
    from api.endpoints import trend_intelligence
    app.include_router(trend_intelligence.router, tags=["Trend Intelligence"])
    logger.success("✓ Trend Intelligence API registered")
except Exception as e:
    logger.warning(f"⚠️  Trend Intelligence API registration failed: {e}")

# Channel Analyzer (TubeLab-style metrics)
try:
    from api.endpoints import channel_analyzer
    app.include_router(channel_analyzer.router, tags=["Channel Analyzer"])
    logger.success("✓ Channel Analyzer API registered")
except Exception as e:
    logger.warning(f"⚠️  Channel Analyzer API registration failed: {e}")

# ReelTrends (Instagram Creator Tools)
try:
    from api.endpoints import reeltrends
    app.include_router(reeltrends.router, tags=["ReelTrends"])
    logger.success("✓ ReelTrends API registered")
except Exception as e:
    logger.warning(f"⚠️  ReelTrends API registration failed: {e}")

# Explainer Video Engine (Motion Canvas)
try:
    from api import explainer_video
    app.include_router(explainer_video.router, tags=["Explainer Video"])
    logger.success("✓ Explainer Video API registered")
except Exception as e:
    logger.warning(f"⚠️  Explainer Video API registration failed: {e}")
app.include_router(tts.router, tags=["TTS Service"])
app.include_router(matting.router, tags=["Video Matting Service"])
app.include_router(remotion.router, tags=["Remotion Service"])
app.include_router(pipeline.router, tags=["Pipeline Service"])
app.include_router(music.router, tags=["Music Service"])
app.include_router(visuals.router, tags=["Visuals Service"])

# Virtual Environment Manager (Python 3.11 for AI/ML tasks)
from api.endpoints import venv_status
app.include_router(venv_status.router, tags=["Virtual Environments"])

# Post-Social Score (Phase 3)
from api.endpoints import post_social_score
app.include_router(post_social_score.router, tags=["Post-Social Score"])

# Audio Analysis (Background Music Detection)
from api.endpoints import audio_analysis
app.include_router(audio_analysis.router, tags=["Audio Analysis"])

# Music Matching (Auto Background Music Suggestion)
from api.endpoints import music_matching
app.include_router(music_matching.router, tags=["Music Matching"])

# Goal Recommendations (Phase 3)
from api.endpoints import goal_recommendations
app.include_router(goal_recommendations.router, tags=["Goal Recommendations"])

# AI Coaching (Phase 3)
from api.endpoints import coaching
app.include_router(coaching.router, tags=["Coaching"])

# Narrative Builder (AI Content Strategy)
from api.endpoints import narrative_builder
app.include_router(narrative_builder.router, tags=["Narrative Builder"])

# Format Discovery (B-Roll + Text Candidate Detection)
from api.endpoints import format_discovery
app.include_router(format_discovery.router, tags=["Format Discovery"])

# B-Roll Candidates (Story-Driven B-Roll Selection)
from api.endpoints import broll_candidates
app.include_router(broll_candidates.router, tags=["B-Roll Candidates"])

# B-Roll Video Producer (AI Text Overlays + Remotion Rendering)
from api.endpoints import broll_producer
app.include_router(broll_producer.router, prefix="/api", tags=["B-Roll Producer"])

# Sora Video Pipeline (Multi-clip AI Video Generation)
from api.endpoints import sora_pipeline
app.include_router(sora_pipeline.router, prefix="/api", tags=["Sora Video Pipeline"])

# TikTok Repurpose Pipeline (Fetch, Download, Analyze, Cross-post)
from api.endpoints import tiktok_repurpose
app.include_router(tiktok_repurpose.router, prefix="/api", tags=["TikTok Repurpose"])

# B-Roll Detection (Speech-based B-Roll Classification)
from api.endpoints import broll
app.include_router(broll.router, tags=["B-Roll Detection"])

# Content Format Detection (Talking Head, B-Roll, Animated, etc.)
from api.endpoints import content_format
app.include_router(content_format.router, tags=["Content Format"])

# Video Toolkit Pub/Sub (Extract & Sync Remotion resources)
from api.endpoints import video_toolkit
app.include_router(video_toolkit.router, tags=["Video Toolkit"])

# SFX Library (AI-addressable sound effects)
from api.endpoints import sfx_library
app.include_router(sfx_library.router, tags=["SFX Library"])

# Video Generation Pipeline (Sora + Render)
from api.endpoints import video_pipeline
app.include_router(video_pipeline.router, tags=["Video Pipeline"])

# Formats API (Video Format Templates)
from api.endpoints import formats_api
app.include_router(formats_api.router, tags=["Formats"])

# Duplicate Detection (Find similar transcripts)
from api.endpoints import duplicate_detection
app.include_router(duplicate_detection.router, tags=["Duplicate Detection"])

# Posted Content Matcher (Cross-reference posted vs local library)
from api.endpoints import posted_content_matcher
app.include_router(posted_content_matcher.router, tags=["Posted Content Matcher"])

# Video Render (Creative Brief → Video Pipeline)
from api.endpoints import video_render
app.include_router(video_render.router, tags=["Video Render"])

# Backend Health (Detailed monitoring and error tracking)
from api.endpoints import backend_health
app.include_router(backend_health.router, tags=["Backend Health"])

# Analysis Scheduler (Nightly batch analysis jobs)
from api.endpoints import analysis_scheduler
app.include_router(analysis_scheduler.router, tags=["Analysis Scheduler"])

# Prompt Generation Settings (Voice, Tone, Style, Limits)
from api.endpoints import prompt_settings
app.include_router(prompt_settings.router, prefix="/api", tags=["Prompt Settings"])

# Experiments (Growth Lab)
from api.endpoints import experiments
app.include_router(experiments.router, tags=["Experiments"])

# Optimal Posting Times (Phase 4)
from api.endpoints import optimal_posting_times
app.include_router(optimal_posting_times.router, tags=["Optimal Posting Times"])

# Media Creation (Phase 5)
from api.endpoints import media_creation
app.include_router(media_creation.router, tags=["Media Creation"])

# Formats System (Clips Studio - Parameterized Video Generation)
from api.endpoints import formats
app.include_router(formats.router, prefix="/api/formats", tags=["Formats"])

# Content Pipeline (CopyPlan + RemotionRenderSpec)
from api.endpoints import content_pipeline
app.include_router(content_pipeline.router, prefix="/api/content-pipeline", tags=["Content Pipeline"])

# Influencer Analysis
from api.endpoints import influencer_analysis
app.include_router(influencer_analysis.router, prefix="/api/influencer", tags=["Influencer Analysis"])

# Music Crawler
from api.endpoints import music_crawler
app.include_router(music_crawler.router, prefix="/api/music-crawler", tags=["Music Crawler"])

# Competitor Audit System
from api.endpoints import competitor_audit
app.include_router(competitor_audit.router, prefix="/api/competitor-audit", tags=["Competitor Audit"])

# Publishing endpoints
from api.endpoints import publishing
app.include_router(publishing.router, prefix="/api/publishing", tags=["Publishing"])

# Storage Management endpoints
from api.endpoints import storage
app.include_router(storage.router, prefix="/api", tags=["Storage Management"])

# AI-Assisted Curation (Sentiment, Duplicates, Auto-curate, Bulk ops)
from api import ai_curation
app.include_router(ai_curation.router, tags=["AI Curation"])

# Social Data Fetcher (RapidAPI integration for frontend pages)
from api.endpoints import social_data_fetcher
app.include_router(social_data_fetcher.router, tags=["Social Data Fetcher"])

# Media Processing (Mobile/Web uploads with smart resume)
from api import media_processing
app.include_router(media_processing.router, tags=["Media Processing"])

# Media Provider Service (Centralized media serving & streaming)
from api.endpoints import media_provider
app.include_router(media_provider.router, tags=["Media Provider"])

# Clip Extraction (Long-form to Short-form, SupoClip-style)
from api.endpoints import clip_extraction
app.include_router(clip_extraction.router, prefix="/api", tags=["Clip Extraction"])

# Database-backed Media Processing (persists to Supabase)
from api import media_processing_db
app.include_router(media_processing_db.router, tags=["Media Processing (Database)"])

# Redirect /api/media-db to /api/media-db/list for backwards compatibility
from fastapi.responses import RedirectResponse
@app.get("/api/media-db", include_in_schema=False)
async def media_db_redirect(limit: int = 50, offset: int = 0, analyzed_only: bool = False, media_type: str = None):
    params = f"limit={limit}&offset={offset}"
    if analyzed_only:
        params += "&analyzed_only=true"
    if media_type:
        params += f"&media_type={media_type}"
    return RedirectResponse(url=f"/api/media-db/list?{params}", status_code=307)

# Blotato API Integration (Social Publishing & AI Videos)
from api import blotato_router
app.include_router(blotato_router.router, tags=["Blotato API"])

# AI Chat (Chat with all data)
from api import ai_chat
app.include_router(ai_chat.router, tags=["AI Chat"])

# Video Orchestrator (Sora-first video generation)
from api.endpoints import video_orchestrator
app.include_router(video_orchestrator.router, prefix="/api", tags=["Video Orchestrator"])

# Analytics Comparison (Cross-account and cross-platform)
from api import analytics_compare
app.include_router(analytics_compare.router, tags=["Analytics Compare"])

# Posted Media (Published content from connected accounts)
from api import posted_media

# Instagram TrendTok (Instagram analytics and trend discovery)
from api.endpoints import instagram_api
app.include_router(instagram_api.router, prefix="/api/instagram", tags=["Instagram TrendTok"])

# Instagram Automation (Comment/DM automation based on Riona-AI-Agent)
from api.endpoints import instagram_automation
app.include_router(instagram_automation.router, prefix="/api", tags=["Instagram Automation"])

# TikTok Automation (DM automation)
from api.endpoints import tiktok_automation
app.include_router(tiktok_automation.router, prefix="/api", tags=["TikTok Automation"])

# Twitter/X Automation (DM automation)
from api.endpoints import twitter_automation
app.include_router(twitter_automation.router, prefix="/api", tags=["Twitter Automation"])

# Trends API (Trending audio, hashtags, formats)
from api.endpoints import trends_api
app.include_router(trends_api.router, prefix="/api/trends", tags=["Trends Discovery"])

# Audio Service (Instagram audio fetch, store, stream)
from api.endpoints import audio_api
app.include_router(audio_api.router, tags=["Audio Service"])

# iOS Import (device import with duplicate detection)
from api.endpoints import ios_import_api
app.include_router(ios_import_api.router, tags=["iOS Import"])

# Android Import (device import via ADB with duplicate detection)
from api.endpoints import android_import_api
app.include_router(android_import_api.router, tags=["Android Import"])
from api.endpoints import voice_cloning_quality
app.include_router(voice_cloning_quality.router, prefix="/api/voice-cloning-quality", tags=["Voice Cloning Quality"])

# Competitor Research (track and analyze competitor content)
from api.endpoints import competitor_api
app.include_router(competitor_api.router, tags=["Competitor Research"])

# Content Analyzer API (AI-powered video analysis)
from api.endpoints import content_analyzer_api
app.include_router(content_analyzer_api.router, prefix="/api/content-analyzer", tags=["Content Analyzer"])

# Posting Optimizer API (Best time to post)
from api.endpoints import posting_optimizer_api
app.include_router(posting_optimizer_api.router, prefix="/api/posting-optimizer", tags=["Posting Optimizer"])

# Hashtag Generator API (AI-powered hashtag recommendations)
from api.endpoints import hashtag_generator_api
app.include_router(hashtag_generator_api.router, prefix="/api/hashtags", tags=["Hashtag Generator"])
app.include_router(posted_media.router, tags=["Posted Media"])

# Database Backup endpoints
from api.endpoints import backup
app.include_router(backup.router, tags=["Database Backup"])

# Analysis Health endpoints
from api.endpoints import analysis_health
app.include_router(analysis_health.router, tags=["Analysis Health"])

# Analysis Validation endpoints
from api.endpoints import analysis_validation
app.include_router(analysis_validation.router, tags=["Analysis Validation"])

# Comprehensive App Validation endpoints
from api.endpoints import app_validation
app.include_router(app_validation.router, tags=["App Validation"])

# Content Growth (Metrics tracking over time)
from api import content_growth
app.include_router(content_growth.router, tags=["Content Growth"])

# Metrics Scheduler (Configurable check-back periods)
from api import metrics_scheduler_api
app.include_router(metrics_scheduler_api.router, tags=["Metrics Scheduler"])

# Human in the Loop (Approval Queue)
from api import approval_queue
app.include_router(approval_queue.router, tags=["Approval Queue"])

# AI Image Analysis
from api import image_analysis
app.include_router(image_analysis.router, tags=["Image Analysis"])

# Content Pipeline (Automated sourcing, approval, scheduling)
from api import content_pipeline
app.include_router(content_pipeline.router, tags=["Content Pipeline"])

# RapidAPI Metrics (Multi-API Instagram/LinkedIn with rate limit management)
from api import rapidapi_metrics
app.include_router(rapidapi_metrics.router, tags=["RapidAPI Metrics"])

# AI Narrative Scheduler (Goal-based content scheduling with AI reasoning)
from api.endpoints import narrative_scheduler
app.include_router(narrative_scheduler.router, tags=["Narrative Scheduler"])

# Content Mix Planner (Long-term scheduling with mixed content types)
from api.endpoints import content_mix_api
app.include_router(content_mix_api.router, tags=["Content Mix Planner"])

# Comment Automation (AI-powered comment engagement across platforms)
from api import comment_automation
app.include_router(comment_automation.router, tags=["Comment Automation"])

# System Health & Metrics (Phase 9)
from api.endpoints import system
app.include_router(system.router, prefix="/api/system", tags=["System Health"])

# Agent Panel (AI Agent monitoring and control)
from api.endpoints import agent_panel
app.include_router(agent_panel.router, tags=["Agent Panel"])

# Automation Center (Unified agent scheduling and runs)
from api.endpoints import automation
app.include_router(automation.router, tags=["Automation Center"])

# Scheduler (Tick and worker processing)
from api.endpoints import scheduler
app.include_router(scheduler.router, tags=["Scheduler"])

# Device Import (iOS/Android media import with duplicate detection)
# TODO: import_router module not found - commented out for now
# from routers import import_router
# app.include_router(import_router.router, tags=["Device Import"])


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
