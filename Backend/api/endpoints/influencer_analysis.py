"""
Influencer Analysis API Endpoints
=================================
Endpoints for analyzing competitor/influencer accounts and generating strategy reports.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger
import os
import json

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

class AnalyzeInfluencerRequest(BaseModel):
    platform: str = Field(..., description="Platform (instagram, tiktok, youtube)")
    username: str = Field(..., description="Username without @")
    include_posts: bool = Field(default=True, description="Whether to fetch top posts")


class InfluencerReportResponse(BaseModel):
    success: bool
    report: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/analyze")
async def analyze_influencer(
    request: AnalyzeInfluencerRequest,
    background_tasks: BackgroundTasks
):
    """
    Analyze an influencer account and generate a comprehensive strategy report.
    
    Returns AI-powered analysis including:
    - Unique positioning and content style
    - Content strategy and pillars
    - Target audience and funnel setup
    - Top posts and viral patterns
    - Key learnings and actionable tactics
    """
    try:
        from services.influencer_analyzer import InfluencerAnalyzer
        
        analyzer = InfluencerAnalyzer()
        
        # Clean username
        username = request.username.lstrip("@").strip()
        
        # Run analysis
        report = await analyzer.analyze_influencer(
            platform=request.platform,
            username=username,
            include_posts=request.include_posts
        )
        
        # Convert to dict
        from dataclasses import asdict
        report_dict = asdict(report)
        
        return {
            "success": True,
            "report": report_dict,
            "analyzed_at": report.analyzed_at
        }
        
    except Exception as e:
        logger.error(f"Influencer analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports")
async def list_reports(
    platform: Optional[str] = None,
    limit: int = 20
):
    """List saved influencer analysis reports"""
    engine = get_engine()
    
    query = """
        SELECT id, platform, username, display_name, follower_count,
               unique_positioning, content_strategy, analyzed_at, confidence_score
        FROM influencer_analysis_reports
        WHERE 1=1
    """
    params = {"limit": limit}
    
    if platform:
        query += " AND platform = :platform"
        params["platform"] = platform
    
    query += " ORDER BY analyzed_at DESC LIMIT :limit"
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params)
            reports = []
            for row in result:
                reports.append({
                    "id": str(row[0]),
                    "platform": row[1],
                    "username": row[2],
                    "display_name": row[3],
                    "follower_count": row[4],
                    "unique_positioning": row[5][:200] + "..." if row[5] and len(row[5]) > 200 else row[5],
                    "content_strategy": row[6][:200] + "..." if row[6] and len(row[6]) > 200 else row[6],
                    "analyzed_at": row[7].isoformat() if row[7] else None,
                    "confidence_score": row[8]
                })
            
            return {
                "success": True,
                "reports": reports,
                "count": len(reports)
            }
    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/{report_id}")
async def get_report(report_id: str):
    """Get a specific influencer analysis report"""
    engine = get_engine()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT report_data, analyzed_at
                FROM influencer_analysis_reports
                WHERE id = :id
            """), {"id": report_id})
            
            row = result.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Report not found")
            
            return {
                "success": True,
                "report": row[0],
                "analyzed_at": row[1].isoformat() if row[1] else None
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/by-username/{platform}/{username}")
async def get_report_by_username(platform: str, username: str):
    """Get report by platform and username"""
    engine = get_engine()
    
    username = username.lstrip("@").strip()
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT report_data, analyzed_at
                FROM influencer_analysis_reports
                WHERE platform = :platform AND username = :username
            """), {"platform": platform, "username": username})
            
            row = result.fetchone()
            if not row:
                return {
                    "success": False,
                    "error": "Report not found",
                    "hint": "Use POST /api/influencer/analyze to generate a report"
                }
            
            return {
                "success": True,
                "report": row[0],
                "analyzed_at": row[1].isoformat() if row[1] else None
            }
    except Exception as e:
        logger.error(f"Failed to get report: {e}")
        raise HTTPException(status_code=500, detail=str(e))
