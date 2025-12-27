"""
Competitor Audit API Endpoints
==============================
Full competitor analysis workflow: collect, analyze, generate reports and templates.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
import os
import asyncio

from sqlalchemy import create_engine, text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
_engine = None

def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL)
    return _engine

router = APIRouter()


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class StartAuditRequest(BaseModel):
    platform: str = Field(..., description="Platform: instagram, tiktok, youtube")
    handle: str = Field(..., description="Username without @")
    post_count: int = Field(default=20, description="Number of posts to analyze")
    include_deep_audit: bool = Field(default=True, description="Run AI deep analysis")
    include_funnel_map: bool = Field(default=True, description="Map their funnel")
    include_templates: bool = Field(default=True, description="Generate templates")


class AuditStatusResponse(BaseModel):
    run_id: str
    status: str
    progress_pct: int
    current_step: Optional[str]
    account_id: Optional[str]
    report_id: Optional[str]
    error: Optional[str]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/start")
async def start_competitor_audit(
    request: StartAuditRequest,
    background_tasks: BackgroundTasks
):
    """
    Start a full competitor audit.
    
    This kicks off a background job that:
    1. Collects profile and posts
    2. Runs AI deep analysis on each post
    3. Maps their funnel structure
    4. Ranks top posts
    5. Generates comprehensive report
    6. Creates Remotion-ready templates
    
    Returns a run_id to track progress.
    """
    engine = get_engine()
    handle = request.handle.lstrip("@").strip()
    
    # Create audit run record
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO competitor_audit_run (
                    platform, handle, requested_post_count,
                    include_deep_audit, include_funnel_map, include_templates,
                    status, progress_pct, current_step
                ) VALUES (
                    :platform, :handle, :post_count,
                    :deep_audit, :funnel_map, :templates,
                    'pending', 0, 'Queued'
                )
                RETURNING run_id
            """), {
                "platform": request.platform,
                "handle": handle,
                "post_count": request.post_count,
                "deep_audit": request.include_deep_audit,
                "funnel_map": request.include_funnel_map,
                "templates": request.include_templates
            })
            conn.commit()
            row = result.fetchone()
            run_id = str(row[0])
    except Exception as e:
        logger.error(f"Failed to create audit run: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # Start background task
    background_tasks.add_task(
        run_full_audit,
        run_id=run_id,
        platform=request.platform,
        handle=handle,
        post_count=request.post_count,
        include_deep_audit=request.include_deep_audit,
        include_funnel_map=request.include_funnel_map,
        include_templates=request.include_templates
    )
    
    return {
        "success": True,
        "run_id": run_id,
        "message": f"Audit started for @{handle} on {request.platform}",
        "estimated_time": f"{request.post_count * 3 + 30} seconds"
    }


@router.get("/status/{run_id}")
async def get_audit_status(run_id: str):
    """Get status of an audit run"""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT run_id, status, progress_pct, current_step,
                       account_id, report_id, error_message,
                       platform, handle, started_at, completed_at
                FROM competitor_audit_run
                WHERE run_id = :run_id
            """), {"run_id": run_id})
            
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Audit run not found")
            
            return {
                "run_id": str(row[0]),
                "status": row[1],
                "progress_pct": row[2],
                "current_step": row[3],
                "account_id": str(row[4]) if row[4] else None,
                "report_id": str(row[5]) if row[5] else None,
                "error": row[6],
                "platform": row[7],
                "handle": row[8],
                "started_at": row[9].isoformat() if row[9] else None,
                "completed_at": row[10].isoformat() if row[10] else None
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audit status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report/{report_id}")
async def get_audit_report(report_id: str):
    """Get a completed audit report"""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT r.report_id, r.account_id, r.posts_analyzed,
                       r.unique_factors, r.strategy, r.funnel_summary,
                       r.top_posts_analysis, r.playbook,
                       r.overall_strategy_score, r.funnel_clarity_score,
                       r.report_markdown, r.generated_at,
                       a.platform, a.handle, a.display_name, a.follower_count
                FROM competitor_audit_report r
                JOIN competitor_account a ON r.account_id = a.account_id
                WHERE r.report_id = :report_id
            """), {"report_id": report_id})
            
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Report not found")
            
            return {
                "success": True,
                "report": {
                    "report_id": str(row[0]),
                    "account_id": str(row[1]),
                    "posts_analyzed": row[2],
                    "unique_factors": row[3],
                    "strategy": row[4],
                    "funnel_summary": row[5],
                    "top_posts": row[6],
                    "playbook": row[7],
                    "scores": {
                        "strategy": row[8],
                        "funnel_clarity": row[9]
                    },
                    "markdown": row[10],
                    "generated_at": row[11].isoformat() if row[11] else None,
                    "account": {
                        "platform": row[12],
                        "handle": row[13],
                        "display_name": row[14],
                        "follower_count": row[15]
                    }
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
async def list_templates(
    account_id: Optional[str] = None,
    limit: int = 20
):
    """List available competitor templates"""
    engine = get_engine()
    
    query = """
        SELECT t.template_id, t.template_name, t.template_slug,
               t.style_fingerprint, t.best_for, t.difficulty_level,
               t.estimated_production_time, t.preview_thumbnail_url,
               a.platform, a.handle
        FROM competitor_template_pack t
        JOIN competitor_account a ON t.account_id = a.account_id
        WHERE 1=1
    """
    params = {"limit": limit}
    
    if account_id:
        query += " AND t.account_id = :account_id"
        params["account_id"] = account_id
    
    query += " ORDER BY t.created_at DESC LIMIT :limit"
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            templates = []
            for row in result:
                templates.append({
                    "template_id": str(row[0]),
                    "template_name": row[1],
                    "template_slug": row[2],
                    "style_fingerprint": row[3],
                    "best_for": row[4],
                    "difficulty_level": row[5],
                    "estimated_production_time": row[6],
                    "preview_thumbnail_url": row[7],
                    "source": {
                        "platform": row[8],
                        "handle": row[9]
                    }
                })
            
            return {
                "success": True,
                "templates": templates,
                "count": len(templates)
            }
    except Exception as e:
        logger.error(f"Failed to list templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}")
async def get_template(template_id: str):
    """Get a specific template with full Remotion spec"""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT t.template_id, t.template_name, t.template_slug,
                       t.style_fingerprint, t.beat_sheet_template,
                       t.remotion_render_spec, t.placeholders, t.swap_rules,
                       t.best_for, t.difficulty_level, t.estimated_production_time,
                       t.preview_thumbnail_url,
                       a.platform, a.handle
                FROM competitor_template_pack t
                JOIN competitor_account a ON t.account_id = a.account_id
                WHERE t.template_id = :template_id
            """), {"template_id": template_id})
            
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Template not found")
            
            return {
                "success": True,
                "template": {
                    "template_id": str(row[0]),
                    "template_name": row[1],
                    "template_slug": row[2],
                    "style_fingerprint": row[3],
                    "beat_sheet_template": row[4],
                    "remotion_render_spec": row[5],
                    "placeholders": row[6],
                    "swap_rules": row[7],
                    "best_for": row[8],
                    "difficulty_level": row[9],
                    "estimated_production_time": row[10],
                    "preview_thumbnail_url": row[11],
                    "source": {
                        "platform": row[12],
                        "handle": row[13]
                    }
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts")
async def list_tracked_accounts(limit: int = 50):
    """List all tracked competitor accounts"""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT account_id, platform, handle, display_name,
                       follower_count, post_count, last_full_audit_at, avatar_url
                FROM competitor_account
                WHERE is_active = TRUE
                ORDER BY follower_count DESC
                LIMIT :limit
            """), {"limit": limit})
            
            accounts = []
            for row in result:
                accounts.append({
                    "account_id": str(row[0]),
                    "platform": row[1],
                    "handle": row[2],
                    "display_name": row[3],
                    "follower_count": row[4],
                    "post_count": row[5],
                    "last_audit": row[6].isoformat() if row[6] else None,
                    "avatar_url": row[7]
                })
            
            return {
                "success": True,
                "accounts": accounts,
                "count": len(accounts)
            }
    except Exception as e:
        logger.error(f"Failed to list accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{account_id}/posts")
async def get_account_posts(
    account_id: str,
    limit: int = 20,
    sort_by: str = "views"
):
    """Get posts for a tracked account with rankings"""
    engine = get_engine()
    
    sort_columns = {
        "views": "views DESC",
        "likes": "likes DESC",
        "comments": "comments DESC",
        "recent": "posted_at DESC"
    }
    sort_clause = sort_columns.get(sort_by, "views DESC")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"""
                SELECT post_id, platform_post_id, permalink, posted_at,
                       caption_text, hashtags, media_type, thumbnail_url,
                       views, likes, comments, shares
                FROM competitor_post
                WHERE account_id = :account_id
                ORDER BY {sort_clause}
                LIMIT :limit
            """), {"account_id": account_id, "limit": limit})
            
            posts = []
            for row in result:
                posts.append({
                    "post_id": str(row[0]),
                    "platform_post_id": row[1],
                    "permalink": row[2],
                    "posted_at": row[3].isoformat() if row[3] else None,
                    "caption_preview": (row[4] or "")[:150] + "..." if row[4] and len(row[4]) > 150 else row[4],
                    "hashtags": row[5],
                    "media_type": row[6],
                    "thumbnail_url": row[7],
                    "metrics": {
                        "views": row[8],
                        "likes": row[9],
                        "comments": row[10],
                        "shares": row[11]
                    }
                })
            
            return {
                "success": True,
                "posts": posts,
                "count": len(posts),
                "sorted_by": sort_by
            }
    except Exception as e:
        logger.error(f"Failed to get posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# BACKGROUND TASK: Full Audit Workflow
# =============================================================================

async def run_full_audit(
    run_id: str,
    platform: str,
    handle: str,
    post_count: int,
    include_deep_audit: bool,
    include_funnel_map: bool,
    include_templates: bool
):
    """
    Execute the full competitor audit workflow.
    Updates progress in the database as it runs.
    """
    engine = get_engine()
    
    def update_progress(status: str, progress: int, step: str, **kwargs):
        """Update audit run progress"""
        try:
            with engine.connect() as conn:
                updates = ["status = :status", "progress_pct = :progress", "current_step = :step"]
                params = {"run_id": run_id, "status": status, "progress": progress, "step": step}
                
                if kwargs.get("account_id"):
                    updates.append("account_id = :account_id")
                    params["account_id"] = kwargs["account_id"]
                if kwargs.get("report_id"):
                    updates.append("report_id = :report_id")
                    params["report_id"] = kwargs["report_id"]
                if kwargs.get("error"):
                    updates.append("error_message = :error")
                    params["error"] = kwargs["error"]
                if status == "collecting":
                    updates.append("started_at = NOW()")
                if status == "complete":
                    updates.append("completed_at = NOW()")
                
                conn.execute(text(f"""
                    UPDATE competitor_audit_run
                    SET {', '.join(updates)}
                    WHERE run_id = :run_id
                """), params)
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")
    
    try:
        # Import services
        from services.competitor_audit.collector import CompetitorCollector
        from services.competitor_audit.deep_audit import CompetitorDeepAuditService, PostDeepAudit
        from services.competitor_audit.funnel_mapper import FunnelMapper
        from services.competitor_audit.post_ranker import PostRanker
        from services.competitor_audit.report_generator import CompetitorReportGenerator
        from services.competitor_audit.template_exporter import TemplateExporter
        
        # Step 1: Collect profile and posts
        update_progress("collecting", 10, "Collecting profile...")
        collector = CompetitorCollector()
        
        profile = await collector.collect_profile(platform, handle)
        if not profile:
            update_progress("failed", 10, "Failed to fetch profile", error="Could not fetch profile")
            return
        
        account_id = await collector.save_profile(profile)
        update_progress("collecting", 20, "Collecting posts...", account_id=account_id)
        
        posts = await collector.collect_posts(platform, handle, post_count, profile.platform_user_id)
        posts_saved = await collector.save_posts(account_id, posts)
        
        logger.info(f"Collected {posts_saved} posts for @{handle}")
        
        # Step 2: Deep audit posts
        post_audits: List[PostDeepAudit] = []
        if include_deep_audit:
            update_progress("analyzing", 30, "Running deep analysis...")
            deep_audit_service = CompetitorDeepAuditService()
            
            for i, post in enumerate(posts):
                progress = 30 + int((i / len(posts)) * 30)
                update_progress("analyzing", progress, f"Analyzing post {i+1}/{len(posts)}")
                
                audit = await deep_audit_service.audit_post(
                    post_id=str(post.platform_post_id),
                    caption_text=post.caption_text or "",
                    duration_sec=post.duration_sec
                )
                post_audits.append(audit)
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
            
            # Aggregate account-level audit
            account_audit = await deep_audit_service.audit_account(account_id, post_audits)
        else:
            from services.competitor_audit.deep_audit import AccountDeepAudit
            account_audit = AccountDeepAudit(account_id=account_id, posts_analyzed=len(posts))
        
        # Step 3: Map funnel
        if include_funnel_map:
            update_progress("analyzing", 65, "Mapping funnel...")
            funnel_mapper = FunnelMapper()
            
            post_captions = [
                {"post_id": p.platform_post_id, "caption": p.caption_text}
                for p in posts
            ]
            
            cta_counts = {}
            for audit in post_audits:
                cta = audit.cta.cta_type if audit.cta else "none"
                cta_counts[cta] = cta_counts.get(cta, 0) + 1
            
            funnel_map = await funnel_mapper.map_funnel(
                account_id=account_id,
                bio_text=profile.bio_text or "",
                linkout_urls=profile.linkout_urls or [],
                post_captions=post_captions,
                cta_counts=cta_counts
            )
            await funnel_mapper.save_funnel_map(funnel_map)
        else:
            from services.competitor_audit.funnel_mapper import FunnelMap
            funnel_map = FunnelMap(account_id=account_id)
        
        # Step 4: Rank posts
        update_progress("analyzing", 75, "Ranking posts...")
        ranker = PostRanker()
        
        posts_data = [
            {
                "post_id": p.platform_post_id,
                "views": p.views,
                "likes": p.likes,
                "comments": p.comments,
                "shares": p.shares,
                "posted_at": p.posted_at,
                "hook_score": next((a.hook_score for a in post_audits if a.post_id == p.platform_post_id), 0),
                "beat_sheet": next((a.beat_sheet for a in post_audits if a.post_id == p.platform_post_id), None)
            }
            for p in posts
        ]
        
        ranking = ranker.rank_posts(
            account_id=account_id,
            posts=posts_data,
            platform=platform
        )
        await ranker.save_ranking(ranking)
        
        # Step 5: Generate report
        update_progress("generating", 85, "Generating report...")
        report_gen = CompetitorReportGenerator()
        
        # Build posts_data with all needed fields
        full_posts_data = [
            {
                "post_id": p.platform_post_id,
                "permalink": p.permalink,
                "caption_text": p.caption_text,
                "posted_at": p.posted_at,
                "views": p.views,
                "likes": p.likes,
                "comments": p.comments,
                "shares": p.shares
            }
            for p in posts
        ]
        
        report = await report_gen.generate_report(
            account_id=account_id,
            platform=platform,
            handle=handle,
            display_name=profile.display_name,
            follower_count=profile.follower_count,
            account_audit=account_audit,
            funnel_map=funnel_map,
            ranking=ranking,
            posts_data=full_posts_data
        )
        report_id = await report_gen.save_report(report)
        
        # Step 6: Generate templates from top posts
        if include_templates:
            update_progress("generating", 92, "Generating templates...")
            template_exporter = TemplateExporter()
            
            top_posts = ranking.rankings[:3]
            for post_score in top_posts:
                audit = next((a for a in post_audits if a.post_id == post_score.post_id), None)
                post_data = next((p for p in posts if p.platform_post_id == post_score.post_id), None)
                
                if audit and post_data:
                    template = template_exporter.create_template_from_audit(
                        post_audit=audit,
                        post_data={
                            "thumbnail_url": post_data.thumbnail_url,
                            "duration_sec": post_data.duration_sec or 30
                        },
                        account_id=account_id
                    )
                    await template_exporter.save_template(template)
        
        # Complete!
        update_progress("complete", 100, "Complete!", report_id=report_id)
        logger.info(f"Audit complete for @{handle}: report_id={report_id}")
        
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        update_progress("failed", 0, f"Error: {str(e)[:100]}", error=str(e))
