"""
Trend Intelligence API Endpoints
================================
API for the trend-to-content pipeline.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, HTTPException, BackgroundTasks
from pydantic import BaseModel

from services.trend_intelligence.ingest_service import get_ingest_service
from services.trend_intelligence.cluster_service import get_cluster_service
from services.trend_intelligence.brief_service import get_brief_service
from services.trend_intelligence.render_service import get_trend_render_service
from services.trend_intelligence.job_queue import get_job_queue, QueueType, JobStatus
from services.trend_intelligence.workers import register_all_handlers
from services.trend_intelligence.scheduler import get_scheduler, ScheduleConfig
from services.trend_intelligence.seedless_crawler import get_seedless_crawler, CrawlConfig
from services.trend_intelligence.trend_crawler import get_trend_crawler
from services.trend_intelligence.youtube_crawler import get_youtube_crawler


router = APIRouter(prefix="/api/v1", tags=["Trend Intelligence"])


# =========================================
# Request/Response Models
# =========================================

class IngestRequest(BaseModel):
    platform: str = "instagram"
    username: Optional[str] = None
    hashtag: Optional[str] = None
    count: int = 12


class BriefRequest(BaseModel):
    cluster_id: str
    platform_target: str = "tiktok"
    tone: Dict[str, Any] = {"style": "engaging"}
    brand_safe_mode: bool = True


class RenderRequest(BaseModel):
    brief_id: str
    format_template_id: str
    overrides: Dict[str, Any] = {}


class OneClickRenderRequest(BaseModel):
    cluster_id: str
    platform_target: str = "tiktok"
    tone: str = "engaging"
    brand_safe_mode: bool = True
    format_template_id: str = "00000000-0000-0000-0000-000000000101"
    overrides: Dict[str, Any] = {}


# =========================================
# Trends Endpoints
# =========================================

@router.get("/trends")
async def list_trends(
    niche: Optional[str] = None,
    platform: Optional[str] = None,
    status: Optional[str] = Query(None, description="emerging|rising|peak|declining"),
    window: str = Query("24h", description="1h|6h|24h|3d|7d"),
    limit: int = Query(20, le=100)
):
    """Get trending topics/hashtags/sounds"""
    service = get_cluster_service()
    trends = await service.get_trending(
        status=status,
        limit=limit
    )
    
    return {
        "trends": trends,
        "count": len(trends),
        "window": window
    }


@router.get("/trends/{cluster_id}")
async def get_trend(cluster_id: str):
    """Get a specific trend with lingo and score history"""
    service = get_cluster_service()
    trends = await service.get_trending(limit=100)
    
    trend = next((t for t in trends if str(t.get("id")) == cluster_id), None)
    if not trend:
        raise HTTPException(status_code=404, detail="Trend not found")
    
    return trend


@router.get("/trends/{cluster_id}/posts")
async def get_trend_posts(
    cluster_id: str,
    limit: int = Query(20, le=50)
):
    """Get sample posts for a trend"""
    brief_service = get_brief_service()
    posts = await brief_service._get_sample_posts(cluster_id, limit=limit)
    
    return {
        "cluster_id": cluster_id,
        "posts": posts,
        "count": len(posts)
    }


# =========================================
# Ingest Endpoints
# =========================================

@router.post("/ingest")
async def ingest_content(
    request: IngestRequest,
    background_tasks: BackgroundTasks
):
    """Ingest content from a platform"""
    service = get_ingest_service()
    
    posts = []
    
    if request.platform == "instagram":
        if request.username:
            posts = await service.ingest_instagram_user(
                username=request.username,
                count=request.count
            )
        elif request.hashtag:
            posts = await service.ingest_instagram_hashtag(
                hashtag=request.hashtag,
                count=request.count
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail="Must provide username or hashtag"
            )
    
    elif request.platform == "tiktok":
        if request.username:
            posts = await service.ingest_tiktok_user(
                username=request.username,
                count=request.count
            )
        else:
            raise HTTPException(
                status_code=400, 
                detail="Must provide username for TikTok"
            )
    
    else:
        raise HTTPException(status_code=400, detail=f"Platform {request.platform} not supported")
    
    return {
        "success": True,
        "platform": request.platform,
        "posts_ingested": len(posts)
    }


@router.post("/ingest/cluster")
async def run_clustering(
    background_tasks: BackgroundTasks
):
    """Run clustering on ingested posts"""
    service = get_cluster_service()
    
    # Run clustering
    hashtag_clusters = await service.cluster_by_hashtag(min_posts=2)
    audio_clusters = await service.cluster_by_audio(min_posts=2)
    
    # Compute scores
    scores = await service.compute_scores(time_window="24h")
    
    return {
        "success": True,
        "hashtag_clusters": len(hashtag_clusters),
        "audio_clusters": len(audio_clusters),
        "scores_computed": len(scores)
    }


@router.post("/ingest/lingo/{cluster_id}")
async def extract_lingo(cluster_id: str):
    """Extract lingo patterns for a cluster"""
    service = get_cluster_service()
    lingo = await service.extract_lingo(cluster_id)
    
    if not lingo:
        raise HTTPException(status_code=500, detail="Failed to extract lingo")
    
    return {
        "success": True,
        "lingo": lingo.to_dict()
    }


# =========================================
# Briefs Endpoints
# =========================================

@router.post("/briefs")
async def create_brief(request: BriefRequest):
    """Generate a content brief from a trend cluster"""
    service = get_brief_service()
    
    brief = await service.generate_brief(
        cluster_id=request.cluster_id,
        platform_target=request.platform_target,
        tone=request.tone,
        brand_safe_mode=request.brand_safe_mode
    )
    
    if not brief:
        raise HTTPException(status_code=500, detail="Failed to generate brief")
    
    return {
        "success": True,
        "brief_id": brief.id,
        "brief": brief.to_dict()
    }


@router.get("/briefs/{brief_id}")
async def get_brief(brief_id: str):
    """Get a content brief by ID"""
    service = get_brief_service()
    brief = await service.get_brief(brief_id)
    
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found")
    
    return brief


@router.get("/briefs")
async def list_briefs(
    status: Optional[str] = None,
    limit: int = Query(20, le=100)
):
    """List content briefs"""
    service = get_brief_service()
    briefs = await service.list_briefs(status=status, limit=limit)
    
    return {
        "briefs": briefs,
        "count": len(briefs)
    }


# =========================================
# Renders Endpoints
# =========================================

@router.post("/renders")
async def create_render(
    request: RenderRequest,
    background_tasks: BackgroundTasks
):
    """Create a render job from a brief"""
    service = get_trend_render_service()
    
    job = await service.create_render_job(
        brief_id=request.brief_id,
        format_template_id=request.format_template_id,
        overrides=request.overrides
    )
    
    if not job:
        raise HTTPException(status_code=500, detail="Failed to create render job")
    
    # Execute in background
    background_tasks.add_task(service.execute_render, job.id)
    
    return {
        "success": True,
        "render_job_id": job.id,
        "status": job.status.value
    }


@router.get("/renders/{job_id}")
async def get_render(job_id: str):
    """Get render job status"""
    service = get_trend_render_service()
    job = await service.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")
    
    return job


@router.get("/renders")
async def list_renders(
    status: Optional[str] = None,
    limit: int = Query(20, le=100)
):
    """List render jobs"""
    service = get_trend_render_service()
    jobs = await service.list_jobs(status=status, limit=limit)
    
    return {
        "jobs": jobs,
        "count": len(jobs)
    }


@router.post("/renders/callback")
async def render_callback(data: Dict[str, Any]):
    """Callback endpoint for Remotion service"""
    service = get_trend_render_service()
    
    job_id = data.get("render_job_id") or data.get("job_id")
    status = data.get("status")
    
    if not job_id:
        return {"received": False, "error": "No job_id provided"}
    
    if status == "succeeded" or status == "completed":
        await service._update_job_result(job_id, {
            "video_url": data.get("video_url") or data.get("video_path"),
            "video_path": data.get("video_path"),
            "duration_sec": data.get("duration_seconds") or data.get("metadata", {}).get("duration_sec"),
            "size_bytes": data.get("file_size_mb", 0) * 1024 * 1024 if data.get("file_size_mb") else data.get("metadata", {}).get("size_bytes"),
        })
    elif status == "failed":
        await service._update_job_error(job_id, data.get("error", "Unknown error"))
    
    return {"received": True, "job_id": job_id, "status": status}


@router.get("/renders/output/{job_id}")
async def get_render_output(job_id: str):
    """Get or stream rendered video file"""
    from fastapi.responses import FileResponse
    from pathlib import Path
    
    # Check multiple possible output locations
    output_paths = [
        Path(f"data/trend_renders/{job_id}.mp4"),
        Path(f"data/remotion_outputs/{job_id}.mp4"),
    ]
    
    for path in output_paths:
        if path.exists():
            return FileResponse(
                path=str(path),
                media_type="video/mp4",
                filename=f"{job_id}.mp4"
            )
    
    # Check database for video_path
    service = get_trend_render_service()
    job = await service.get_job(job_id)
    
    if job and job.get("output"):
        output = job["output"]
        if isinstance(output, str):
            import json
            output = json.loads(output)
        video_path = output.get("video_path")
        if video_path and Path(video_path).exists():
            return FileResponse(
                path=video_path,
                media_type="video/mp4",
                filename=f"{job_id}.mp4"
            )
    
    raise HTTPException(status_code=404, detail=f"Render output not found for job {job_id}")


# =========================================
# Format Templates Endpoints
# =========================================

@router.get("/formats")
async def list_formats():
    """List available format templates"""
    service = get_trend_render_service()
    
    from sqlalchemy import create_engine, text
    import os
    
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT * FROM format_templates ORDER BY name"))
        templates = [dict(row._mapping) for row in result.fetchall()]
    
    return {
        "formats": templates,
        "count": len(templates)
    }


@router.get("/formats/{format_id}")
async def get_format(format_id: str):
    """Get a format template by ID"""
    service = get_trend_render_service()
    template = await service._get_template(format_id)
    
    if not template:
        raise HTTPException(status_code=404, detail="Format template not found")
    
    return template


# =========================================
# One-Click Flow
# =========================================

@router.post("/oneclick/render_from_trend")
async def oneclick_render(
    request: OneClickRenderRequest,
    background_tasks: BackgroundTasks
):
    """
    One-click flow: trend → brief → render
    
    Takes a cluster_id and produces a video in one call.
    """
    brief_service = get_brief_service()
    render_service = get_trend_render_service()
    
    # Step 1: Generate brief
    brief = await brief_service.generate_brief(
        cluster_id=request.cluster_id,
        platform_target=request.platform_target,
        tone={"style": request.tone},
        brand_safe_mode=request.brand_safe_mode
    )
    
    if not brief:
        raise HTTPException(status_code=500, detail="Failed to generate brief")
    
    # Step 2: Create render job
    job = await render_service.create_render_job(
        brief_id=brief.id,
        format_template_id=request.format_template_id,
        overrides=request.overrides
    )
    
    if not job:
        raise HTTPException(status_code=500, detail="Failed to create render job")
    
    # Step 3: Execute render in background
    background_tasks.add_task(render_service.execute_render, job.id)
    
    return {
        "success": True,
        "brief_id": brief.id,
        "render_job_id": job.id,
        "status": "queued",
        "poll_url": f"/api/v1/renders/{job.id}"
    }


# =========================================
# Pipeline Endpoints
# =========================================

@router.post("/pipeline/full")
async def run_full_pipeline(
    username: Optional[str] = None,
    hashtag: Optional[str] = None,
    background_tasks: BackgroundTasks = None
):
    """
    Run the full pipeline:
    1. Ingest posts
    2. Cluster into trends
    3. Score trends
    4. Extract lingo for top trends
    """
    ingest_service = get_ingest_service()
    cluster_service = get_cluster_service()
    
    results = {
        "ingest": {},
        "cluster": {},
        "score": {},
        "lingo": {}
    }
    
    # Step 1: Ingest
    if username:
        posts = await ingest_service.ingest_instagram_user(username)
        results["ingest"]["posts"] = len(posts)
    elif hashtag:
        posts = await ingest_service.ingest_instagram_hashtag(hashtag)
        results["ingest"]["posts"] = len(posts)
    
    # Step 2: Cluster
    hashtag_clusters = await cluster_service.cluster_by_hashtag(min_posts=2)
    audio_clusters = await cluster_service.cluster_by_audio(min_posts=2)
    results["cluster"]["hashtags"] = len(hashtag_clusters)
    results["cluster"]["audio"] = len(audio_clusters)
    
    # Step 3: Score
    scores = await cluster_service.compute_scores(time_window="24h")
    results["score"]["computed"] = len(scores)
    
    # Step 4: Extract lingo for top 5 clusters
    all_clusters = hashtag_clusters + audio_clusters
    for cluster in all_clusters[:5]:
        if cluster.id:
            lingo = await cluster_service.extract_lingo(cluster.id)
            if lingo:
                results["lingo"][cluster.id] = True
    
    return {
        "success": True,
        "results": results
    }


# =========================================
# Job Queue Endpoints
# =========================================

class JobRequest(BaseModel):
    queue: str
    payload: Dict[str, Any] = {}
    priority: int = 0


@router.post("/jobs")
async def enqueue_job(request: JobRequest):
    """Add a job to a queue"""
    queue = get_job_queue()
    
    try:
        queue_type = QueueType(request.queue)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid queue: {request.queue}")
    
    job_id = await queue.enqueue(
        queue=queue_type,
        payload=request.payload,
        priority=request.priority
    )
    
    return {
        "success": True,
        "job_id": job_id,
        "queue": request.queue
    }


@router.get("/jobs")
async def list_jobs(
    queue: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(20, le=100)
):
    """List jobs from the queue"""
    job_queue = get_job_queue()
    
    queue_type = QueueType(queue) if queue else None
    job_status = JobStatus(status) if status else None
    
    jobs = await job_queue.get_recent_jobs(
        queue=queue_type,
        status=job_status,
        limit=limit
    )
    
    return {
        "jobs": jobs,
        "count": len(jobs)
    }


@router.get("/jobs/stats")
async def get_queue_stats():
    """Get statistics for all queues"""
    queue = get_job_queue()
    stats = await queue.get_queue_stats()
    
    return {
        "queues": stats,
        "total_pending": sum(q.get("pending", 0) for q in stats.values()),
        "total_running": sum(q.get("running", 0) for q in stats.values()),
        "total_completed": sum(q.get("completed", 0) for q in stats.values()),
        "total_failed": sum(q.get("failed", 0) for q in stats.values()),
    }


@router.post("/jobs/process/{queue_name}")
async def process_queue(queue_name: str):
    """Manually process the next job in a queue"""
    job_queue = get_job_queue()
    
    try:
        queue_type = QueueType(queue_name)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid queue: {queue_name}")
    
    # Ensure handlers are registered
    register_all_handlers(job_queue)
    
    try:
        result = await job_queue.process_queue(queue_type)
        if result is None:
            return {"message": "No pending jobs in queue", "queue": queue_name}
        
        return {
            "success": True,
            "queue": queue_name,
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================
# Pipeline Trigger Endpoints
# =========================================

class PipelineRequest(BaseModel):
    sources: List[Dict[str, Any]] = []
    generate_briefs: bool = False
    auto_render: bool = False


@router.post("/pipeline/queue")
async def queue_pipeline(request: PipelineRequest):
    """
    Queue a full pipeline run.
    
    Sources format: [{"platform": "instagram", "username": "example"}]
    """
    queue = get_job_queue()
    
    job_ids = []
    for source in request.sources:
        job_id = await queue.enqueue(
            QueueType.INGEST,
            {
                **source,
                "generate_briefs": request.generate_briefs,
                "auto_render": request.auto_render,
            },
            priority=10
        )
        job_ids.append(job_id)
    
    return {
        "success": True,
        "jobs_queued": len(job_ids),
        "job_ids": job_ids,
        "message": "Pipeline jobs queued. Use GET /api/v1/jobs/stats to monitor progress."
    }


@router.post("/pipeline/run-all")
async def run_full_pipeline(
    background_tasks: BackgroundTasks,
    sources: Optional[List[Dict[str, Any]]] = None
):
    """
    Run the full pipeline synchronously (for testing).
    
    Executes: Ingest → Cluster → Score → Lingo
    """
    queue = get_job_queue()
    register_all_handlers(queue)
    
    results = {
        "ingest": [],
        "cluster": None,
        "score": None,
        "lingo": None,
    }
    
    # Run ingest for each source
    if sources:
        for source in sources:
            await queue.enqueue(QueueType.INGEST, source, priority=10)
            result = await queue.process_queue(QueueType.INGEST)
            results["ingest"].append(result)
    
    # Run cluster
    await queue.enqueue(QueueType.CLUSTER, {"min_posts": 2})
    results["cluster"] = await queue.process_queue(QueueType.CLUSTER)
    
    # Run score
    await queue.enqueue(QueueType.SCORE, {"time_windows": ["24h"]})
    results["score"] = await queue.process_queue(QueueType.SCORE)
    
    # Run lingo
    await queue.enqueue(QueueType.LINGO, {"top_n": 5})
    results["lingo"] = await queue.process_queue(QueueType.LINGO)
    
    return {
        "success": True,
        "results": results
    }


@router.get("/queues")
async def list_queues():
    """List all available queues"""
    return {
        "queues": [
            {"name": "q_ingest", "description": "Pull posts from platforms"},
            {"name": "q_enrich", "description": "Add transcripts, comments, OCR"},
            {"name": "q_embed", "description": "Create text embeddings"},
            {"name": "q_cluster", "description": "Group posts into trends"},
            {"name": "q_score", "description": "Compute velocity scores"},
            {"name": "q_lingo", "description": "Extract phrases and meaning"},
            {"name": "q_brief", "description": "Generate content briefs"},
            {"name": "q_render", "description": "Render videos"},
            {"name": "q_notify", "description": "Fire webhooks"},
        ]
    }


# =========================================
# Autonomous Discovery Endpoints
# =========================================

class SourceRequest(BaseModel):
    platform: str = "tiktok"
    source_type: str = "account"  # 'account' or 'hashtag'
    identifier: str  # username or hashtag


@router.post("/sources")
async def add_source(request: SourceRequest):
    """Add a source (account/hashtag) to track for trend discovery"""
    scheduler = get_scheduler()
    
    source_id = await scheduler.add_source(
        platform=request.platform,
        source_type=request.source_type,
        identifier=request.identifier
    )
    
    return {
        "success": True,
        "source_id": source_id,
        "message": f"Now tracking {request.platform}/{request.identifier}"
    }


@router.get("/sources")
async def list_sources():
    """List all tracked sources"""
    scheduler = get_scheduler()
    sources = await scheduler.get_active_sources()
    
    return {
        "sources": sources,
        "count": len(sources)
    }


@router.delete("/sources/{source_id}")
async def remove_source(source_id: str):
    """Stop tracking a source"""
    scheduler = get_scheduler()
    await scheduler.remove_source(source_id)
    
    return {"success": True, "message": "Source deactivated"}


@router.post("/scheduler/start")
async def start_scheduler(background_tasks: BackgroundTasks):
    """Start autonomous trend discovery"""
    scheduler = get_scheduler()
    background_tasks.add_task(scheduler.start)
    
    return {
        "success": True,
        "message": "Autonomous discovery started",
        "schedule": {
            "ingest_interval": "6 hours",
            "cluster_interval": "2 hours",
            "score_interval": "1 hour",
            "alert_check": "30 minutes"
        }
    }


@router.post("/scheduler/stop")
async def stop_scheduler():
    """Stop autonomous trend discovery"""
    scheduler = get_scheduler()
    await scheduler.stop()
    
    return {"success": True, "message": "Scheduler stopped"}


@router.post("/scheduler/run-now")
async def run_pipeline_now(background_tasks: BackgroundTasks):
    """Manually trigger full discovery pipeline"""
    scheduler = get_scheduler()
    background_tasks.add_task(scheduler.run_full_pipeline)
    
    return {
        "success": True,
        "message": "Pipeline triggered. Running: Ingest → Cluster → Score → Alerts"
    }


@router.get("/scheduler/status")
async def scheduler_status():
    """Get scheduler status (DEPRECATED - use seedless crawler)"""
    scheduler = get_scheduler()
    sources = await scheduler.get_active_sources()
    
    return {
        "running": scheduler._running,
        "active_sources": len(sources),
        "deprecated": True,
        "message": "Use /api/v1/discover for seedless trend discovery",
        "config": {
            "ingest_interval_hours": scheduler.config.ingest_interval_hours,
            "cluster_interval_hours": scheduler.config.cluster_interval_hours,
            "score_interval_hours": scheduler.config.score_interval_hours,
            "alert_interval_minutes": scheduler.config.alert_interval_minutes,
        }
    }


# =========================================
# Seedless Discovery Endpoints
# =========================================

@router.post("/discover")
async def discover_trends(background_tasks: BackgroundTasks):
    """
    Run seedless trend discovery.
    
    Samples random content from platform discovery surfaces,
    then uses clustering to find what's trending without keywords.
    """
    crawler = get_seedless_crawler()
    background_tasks.add_task(crawler.discover)
    
    return {
        "success": True,
        "message": "Seedless discovery started",
        "description": "Sampling → Ingesting → Extracting → Scoring → Saving"
    }


@router.post("/discover/sync")
async def discover_trends_sync():
    """
    Run seedless discovery synchronously (waits for results).
    Use for testing or when you need immediate results.
    """
    crawler = get_seedless_crawler()
    results = await crawler.discover()
    
    return {
        "success": True,
        "results": results
    }


class CrawlConfigRequest(BaseModel):
    sample_size: int = 500
    lookback_hours: int = 72
    region: str = "US"
    min_velocity: float = 0.1
    min_mentions: int = 3


@router.post("/discover/configure")
async def configure_crawler(config: CrawlConfigRequest):
    """Configure the seedless crawler (DEPRECATED - use /crawl instead)"""
    return {
        "deprecated": True,
        "message": "Use POST /api/v1/crawl for account-seeded discovery"
    }


# =========================================
# Account-Seeded Trend Crawler (Recommended)
# =========================================

class SeedAccountRequest(BaseModel):
    platform: str = "tiktok"  # 'tiktok' or 'instagram'
    username: str
    niche: str = ""


class CrawlRequest(BaseModel):
    seed_accounts: Optional[List[SeedAccountRequest]] = None
    posts_per_account: int = 30


@router.post("/crawl")
async def crawl_trends(request: CrawlRequest = None):
    """
    Account-seeded trend discovery (recommended approach).
    
    Crawls seed accounts and extracts trends from their content.
    No keywords needed - trends are discovered automatically.
    """
    crawler = get_trend_crawler()
    
    # Set seed accounts if provided
    if request and request.seed_accounts:
        crawler.set_seed_accounts([
            {"platform": a.platform, "username": a.username, "niche": a.niche}
            for a in request.seed_accounts
        ])
    
    posts_per = request.posts_per_account if request else 30
    results = await crawler.discover(posts_per_account=posts_per)
    
    return {
        "success": True,
        "results": results
    }


@router.post("/crawl/seed-accounts")
async def set_seed_accounts(accounts: List[SeedAccountRequest]):
    """Set the seed accounts for trend crawling"""
    crawler = get_trend_crawler()
    crawler.set_seed_accounts([
        {"platform": a.platform, "username": a.username, "niche": a.niche}
        for a in accounts
    ])
    
    return {
        "success": True,
        "seed_accounts": len(accounts),
        "message": f"Set {len(accounts)} seed accounts for crawling"
    }


@router.get("/crawl/seed-accounts")
async def get_seed_accounts():
    """Get current seed accounts"""
    crawler = get_trend_crawler()
    
    # Also load from DB
    await crawler.load_seed_accounts_from_db()
    
    return {
        "seed_accounts": [
            {"platform": a.platform, "username": a.username, "niche": a.niche}
            for a in crawler.seed_accounts
        ],
        "count": len(crawler.seed_accounts)
    }


# =========================================
# YouTube Trend Crawler
# =========================================

class YouTubeChannelRequest(BaseModel):
    channel_id: str
    title: str = ""
    niche: str = ""


class YouTubeCrawlRequest(BaseModel):
    channels: Optional[List[YouTubeChannelRequest]] = None
    videos_per_channel: int = 50
    analyze_comments: bool = False  # Phase 3: Enable comment analysis
    analyze_thumbnails: bool = False  # Phase 4: Enable thumbnail analysis
    analyze_keywords: bool = False  # Phase 5: Enable keyword opportunity analysis


@router.post("/crawl/youtube")
async def crawl_youtube_trends(request: YouTubeCrawlRequest = None):
    """
    YouTube trend discovery using Data API v3.
    
    Crawls channel uploads playlists and extracts:
    - Title templates ("I tried X", "X explained")
    - Entity trends (products, tools, people)
    - Format trends (Shorts, duration buckets)
    - Topic clusters (OpenAI embeddings)
    - Audience interests (from comments, if enabled)
    
    Scoring uses channel-normalized uplift.
    """
    crawler = get_youtube_crawler()
    
    # Set channels if provided
    if request and request.channels:
        crawler.set_channels([
            {"channel_id": c.channel_id, "title": c.title, "niche": c.niche}
            for c in request.channels
        ])
    
    videos_per = request.videos_per_channel if request else 50
    analyze_comments = request.analyze_comments if request else False
    analyze_thumbnails = request.analyze_thumbnails if request else False
    analyze_keywords = request.analyze_keywords if request else False
    
    results = await crawler.discover(
        videos_per_channel=videos_per,
        analyze_comments=analyze_comments,
        analyze_thumbnails=analyze_thumbnails,
        analyze_keywords=analyze_keywords
    )
    
    return {
        "success": True,
        "results": results
    }


@router.post("/crawl/youtube/channels")
async def set_youtube_channels(channels: List[YouTubeChannelRequest]):
    """Set YouTube channels for trend crawling"""
    crawler = get_youtube_crawler()
    crawler.set_channels([
        {"channel_id": c.channel_id, "title": c.title, "niche": c.niche}
        for c in channels
    ])
    
    return {
        "success": True,
        "channels": len(channels),
        "message": f"Set {len(channels)} YouTube channels for crawling"
    }


@router.get("/crawl/youtube/channels")
async def get_youtube_channels():
    """Get current YouTube channels"""
    crawler = get_youtube_crawler()
    
    # Load from DB
    await crawler.load_channels_from_db()
    
    return {
        "channels": [
            {"channel_id": c.channel_id, "title": c.title, "niche": c.niche}
            for c in crawler.channels
        ],
        "count": len(crawler.channels)
    }
