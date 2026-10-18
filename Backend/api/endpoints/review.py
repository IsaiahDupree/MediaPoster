"""
Performance Review API Endpoints

Provides endpoints for fetching and analyzing content performance data,
comparing UGC vs AI/Sora-style content.
"""

import asyncio
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/review", tags=["review"])

REPORT_PATH = Path(__file__).parent.parent.parent / "scripts" / "youtube_performance_report.json"


class CategoryStats(BaseModel):
    count: int
    avg_views: float
    avg_likes: float
    avg_score: float
    high_performers: List[str]
    low_performers: List[str]
    top_improvements: List[tuple]


class VideoReview(BaseModel):
    video_id: str
    title: str
    category: str
    views: int
    likes: int
    comments: Optional[int] = 0
    score: float
    verdict: str
    improvements: List[str]
    platform_url: Optional[str] = None


class PerformanceReviewResponse(BaseModel):
    generated_at: str
    total_videos: int
    categories: Dict[str, dict]
    reviews: List[dict]


@router.get("/performance")
async def get_performance_review() -> dict:
    """
    Get the latest performance review data.
    Returns category breakdowns and individual video reviews.
    """
    if not REPORT_PATH.exists():
        # Generate initial report if none exists
        await run_analysis()
    
    try:
        with open(REPORT_PATH, "r") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load review data: {str(e)}")


@router.post("/analyze")
async def run_analysis() -> dict:
    """
    Run a new performance analysis.
    This fetches the latest data from the database and generates a fresh report.
    """
    try:
        # Run the analysis script
        script_path = Path(__file__).parent.parent.parent / "scripts" / "youtube_performance_review.py"
        
        if not script_path.exists():
            raise HTTPException(status_code=500, detail="Analysis script not found")
        
        # Run script in background
        result = subprocess.run(
            ["python", str(script_path)],
            cwd=str(script_path.parent),
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500, 
                detail=f"Analysis failed: {result.stderr[:500]}"
            )
        
        # Load the generated report
        if REPORT_PATH.exists():
            with open(REPORT_PATH, "r") as f:
                data = json.load(f)
            return {
                "success": True,
                "message": "Analysis completed successfully",
                "data": data
            }
        else:
            raise HTTPException(status_code=500, detail="Report file not generated")
            
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Analysis timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/categories")
async def get_category_comparison() -> dict:
    """
    Get category comparison data for the chart.
    """
    if not REPORT_PATH.exists():
        return {"categories": {}}
    
    try:
        with open(REPORT_PATH, "r") as f:
            data = json.load(f)
        
        return {
            "categories": data.get("categories", {}),
            "generated_at": data.get("generated_at")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights")
async def get_insights() -> dict:
    """
    Get AI-generated insights about content performance.
    """
    if not REPORT_PATH.exists():
        return {"insights": []}
    
    try:
        with open(REPORT_PATH, "r") as f:
            data = json.load(f)
        
        categories = data.get("categories", {})
        reviews = data.get("reviews", [])
        
        insights = []
        
        # Category comparison insights
        if categories:
            sorted_cats = sorted(
                categories.items(),
                key=lambda x: x[1].get("avg_score", 0),
                reverse=True
            )
            
            if sorted_cats:
                winner = sorted_cats[0]
                insights.append({
                    "type": "winner",
                    "title": f"{winner[0]} content performs best",
                    "description": f"Average score of {winner[1]['avg_score']:.1f}/100",
                    "icon": "🏆"
                })
        
        # Engagement insights
        ugc_stats = categories.get("UGC", {})
        ai_stats = categories.get("AI/Sora-style", {})
        
        if ugc_stats and ai_stats:
            if ai_stats.get("avg_likes", 0) > ugc_stats.get("avg_likes", 0):
                insights.append({
                    "type": "engagement",
                    "title": "AI content drives more likes",
                    "description": f"AI: {ai_stats['avg_likes']:.0f} avg likes vs UGC: {ugc_stats['avg_likes']:.0f}",
                    "icon": "👍"
                })
            
            if ugc_stats.get("avg_views", 0) > ai_stats.get("avg_views", 0):
                insights.append({
                    "type": "reach",
                    "title": "UGC has better reach",
                    "description": f"UGC: {ugc_stats['avg_views']:.0f} avg views vs AI: {ai_stats['avg_views']:.0f}",
                    "icon": "👀"
                })
        
        # High performer count
        total_high = sum(len(c.get("high_performers", [])) for c in categories.values())
        total_low = sum(len(c.get("low_performers", [])) for c in categories.values())
        
        if total_high > 0:
            insights.append({
                "type": "success",
                "title": f"{total_high} high-performing videos",
                "description": "Scoring 70+ on performance scale",
                "icon": "🌟"
            })
        
        # Common improvements
        all_improvements = {}
        for cat_data in categories.values():
            for imp, count in cat_data.get("top_improvements", []):
                all_improvements[imp] = all_improvements.get(imp, 0) + count
        
        if all_improvements:
            top_imp = max(all_improvements.items(), key=lambda x: x[1])
            insights.append({
                "type": "improvement",
                "title": "Top improvement opportunity",
                "description": top_imp[0],
                "icon": "💡"
            })
        
        return {"insights": insights}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/video/{video_id}")
async def get_video_review(video_id: str) -> dict:
    """
    Get detailed review for a specific video.
    """
    if not REPORT_PATH.exists():
        raise HTTPException(status_code=404, detail="No review data available")
    
    try:
        with open(REPORT_PATH, "r") as f:
            data = json.load(f)
        
        reviews = data.get("reviews", [])
        
        for review in reviews:
            if review.get("video_id") == video_id:
                return review
        
        raise HTTPException(status_code=404, detail="Video not found in review")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
