"""
System Health Monitoring Endpoints
===================================
Provides comprehensive health checks and metrics for the MediaPoster system.
"""

from fastapi import APIRouter
from datetime import datetime, timedelta
from typing import Optional
import os

from sqlalchemy import create_engine, text

router = APIRouter()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")


def get_engine():
    return create_engine(DATABASE_URL)


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "MediaPoster Backend",
        "version": "2.0.0"
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status."""
    engine = get_engine()
    
    components = {
        "api": {"status": "healthy", "message": "API responding"},
        "database": {"status": "unknown", "message": "Not checked"},
        "narrative_builder": {"status": "unknown", "message": "Not checked"},
        "experiments": {"status": "unknown", "message": "Not checked"},
        "calendar": {"status": "unknown", "message": "Not checked"},
    }
    
    # Check database connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            components["database"] = {"status": "healthy", "message": "Connected"}
    except Exception as e:
        components["database"] = {"status": "unhealthy", "message": str(e)[:100]}
    
    # Check narrative builder tables
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'narrative_goals')
            """)).scalar()
            if result:
                count = conn.execute(text("SELECT COUNT(*) FROM narrative_goals")).scalar()
                components["narrative_builder"] = {"status": "healthy", "message": f"{count} goals"}
            else:
                components["narrative_builder"] = {"status": "warning", "message": "Tables not created"}
    except Exception as e:
        components["narrative_builder"] = {"status": "warning", "message": str(e)[:50]}
    
    # Check experiments tables
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'experiments')
            """)).scalar()
            if result:
                count = conn.execute(text("SELECT COUNT(*) FROM experiments")).scalar()
                components["experiments"] = {"status": "healthy", "message": f"{count} experiments"}
            else:
                components["experiments"] = {"status": "warning", "message": "Tables not created"}
    except Exception as e:
        components["experiments"] = {"status": "warning", "message": str(e)[:50]}
    
    # Check calendar/scheduled_posts
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'scheduled_posts')
            """)).scalar()
            if result:
                count = conn.execute(text("SELECT COUNT(*) FROM scheduled_posts WHERE status = 'scheduled'")).scalar()
                components["calendar"] = {"status": "healthy", "message": f"{count} pending posts"}
            else:
                components["calendar"] = {"status": "warning", "message": "Tables not created"}
    except Exception as e:
        components["calendar"] = {"status": "warning", "message": str(e)[:50]}
    
    # Determine overall status
    statuses = [c["status"] for c in components.values()]
    if all(s == "healthy" for s in statuses):
        overall = "healthy"
    elif any(s == "unhealthy" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"
    
    return {
        "status": overall,
        "timestamp": datetime.utcnow().isoformat(),
        "components": components
    }


@router.get("/metrics/overview")
async def get_overview_metrics():
    """Get comprehensive metrics for the dashboard overview."""
    engine = get_engine()
    
    metrics = {
        "narrative_builder": {
            "active_goals": 0,
            "scheduled_posts": 0,
            "kb_rules_applied": 0,
            "trend_opportunities": 0,
        },
        "experiments": {
            "running": 0,
            "completed": 0,
            "total_learnings": 0,
            "avg_uplift": 0,
        },
        "calendar": {
            "mainline_pending": 0,
            "experiment_pending": 0,
            "manual_pending": 0,
            "today_posts": 0,
        },
        "content": {
            "total_videos": 0,
            "analyzed": 0,
            "high_performers": 0,
            "fresh": 0,
        },
    }
    
    with engine.connect() as conn:
        # Narrative Builder metrics
        try:
            goals = conn.execute(text("""
                SELECT COUNT(*) FROM narrative_goals WHERE status = 'active'
            """)).scalar()
            metrics["narrative_builder"]["active_goals"] = goals or 0
        except:
            pass
        
        try:
            rules = conn.execute(text("""
                SELECT COUNT(*) FROM kb_rules WHERE status = 'active'
            """)).scalar()
            metrics["narrative_builder"]["kb_rules_applied"] = rules or 0
            metrics["experiments"]["total_learnings"] = rules or 0
        except:
            pass
        
        try:
            trends = conn.execute(text("""
                SELECT COUNT(*) FROM trend_opportunities 
                WHERE status = 'active' AND priority = 'high'
            """)).scalar()
            metrics["narrative_builder"]["trend_opportunities"] = trends or 0
        except:
            pass
        
        # Experiments metrics
        try:
            running = conn.execute(text("""
                SELECT COUNT(*) FROM experiments WHERE status = 'running'
            """)).scalar()
            completed = conn.execute(text("""
                SELECT COUNT(*) FROM experiments WHERE status = 'completed'
            """)).scalar()
            metrics["experiments"]["running"] = running or 0
            metrics["experiments"]["completed"] = completed or 0
        except:
            pass
        
        # Calendar metrics
        try:
            mainline = conn.execute(text("""
                SELECT COUNT(*) FROM scheduled_posts 
                WHERE status = 'scheduled' AND origin = 'NARRATIVE'
            """)).scalar()
            experiment = conn.execute(text("""
                SELECT COUNT(*) FROM scheduled_posts 
                WHERE status = 'scheduled' AND origin = 'EXPERIMENT'
            """)).scalar()
            manual = conn.execute(text("""
                SELECT COUNT(*) FROM scheduled_posts 
                WHERE status = 'scheduled' AND (origin = 'MANUAL' OR origin IS NULL)
            """)).scalar()
            metrics["calendar"]["mainline_pending"] = mainline or 0
            metrics["calendar"]["experiment_pending"] = experiment or 0
            metrics["calendar"]["manual_pending"] = manual or 0
            metrics["narrative_builder"]["scheduled_posts"] = mainline or 0
        except:
            pass
        
        # Today's posts
        try:
            today = conn.execute(text("""
                SELECT COUNT(*) FROM scheduled_posts 
                WHERE status = 'scheduled' 
                AND DATE(scheduled_at) = CURRENT_DATE
            """)).scalar()
            metrics["calendar"]["today_posts"] = today or 0
        except:
            pass
        
        # Content metrics
        try:
            total = conn.execute(text("SELECT COUNT(*) FROM videos")).scalar()
            analyzed = conn.execute(text("""
                SELECT COUNT(*) FROM videos WHERE analyzed = true
            """)).scalar()
            metrics["content"]["total_videos"] = total or 0
            metrics["content"]["analyzed"] = analyzed or 0
        except:
            pass
        
        try:
            high_performers = conn.execute(text("""
                SELECT COUNT(*) FROM video_analysis 
                WHERE pre_social_score >= 80
            """)).scalar()
            metrics["content"]["high_performers"] = high_performers or 0
        except:
            pass
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics
    }


@router.get("/metrics/two-brain")
async def get_two_brain_metrics():
    """Get metrics specific to the two-brain architecture."""
    engine = get_engine()
    
    with engine.connect() as conn:
        # Get account role distribution
        account_roles = {"MAINLINE": 0, "EXPERIMENT_ARM": 0, "other": 0}
        try:
            result = conn.execute(text("""
                SELECT account_role, COUNT(*) 
                FROM social_accounts 
                GROUP BY account_role
            """)).fetchall()
            for row in result:
                role = row[0] or "other"
                if role in account_roles:
                    account_roles[role] = row[1]
                else:
                    account_roles["other"] += row[1]
        except:
            pass
        
        # Get KB rules by type
        kb_rules_by_type = {}
        try:
            result = conn.execute(text("""
                SELECT rule_type, COUNT(*) 
                FROM kb_rules 
                WHERE status = 'active'
                GROUP BY rule_type
            """)).fetchall()
            for row in result:
                kb_rules_by_type[row[0]] = row[1]
        except:
            pass
        
        # Get post distribution by origin
        posts_by_origin = {"NARRATIVE": 0, "EXPERIMENT": 0, "MANUAL": 0}
        try:
            result = conn.execute(text("""
                SELECT COALESCE(origin, 'MANUAL'), COUNT(*) 
                FROM scheduled_posts 
                WHERE status = 'scheduled'
                GROUP BY origin
            """)).fetchall()
            for row in result:
                origin = row[0] or "MANUAL"
                if origin in posts_by_origin:
                    posts_by_origin[origin] = row[1]
        except:
            pass
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "account_roles": account_roles,
            "kb_rules_by_type": kb_rules_by_type,
            "posts_by_origin": posts_by_origin,
            "architecture": {
                "mainline_brain": {
                    "name": "Narrative Builder",
                    "purpose": "Content strategy and scheduling",
                    "posts_to": "MAINLINE accounts",
                    "features": ["Goals", "7-Day Planning", "KB Rules", "Trends"]
                },
                "scientist_brain": {
                    "name": "Experiments",
                    "purpose": "A/B testing and learning",
                    "posts_to": "EXPERIMENT_ARM accounts",
                    "features": ["Hypothesis Testing", "Confidence Calc", "Rule Generation"]
                },
                "shared": {
                    "name": "Knowledge Base",
                    "purpose": "Store and apply learnings",
                    "components": ["Rules", "Templates", "Constraints", "Playbooks"]
                }
            }
        }
