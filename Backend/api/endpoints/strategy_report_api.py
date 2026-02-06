"""
Strategy Report API Endpoints
Weekly AI-generated content strategy reports.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
from loguru import logger

from services.strategy_report_service import get_strategy_report_service

router = APIRouter(prefix="/api/strategy-report", tags=["Strategy Reports"])


class GenerateReportRequest(BaseModel):
    """Request to generate a strategy report"""
    user_performance: Optional[Dict[str, Any]] = None
    trending_data: Optional[Dict[str, Any]] = None


@router.get("/health")
async def health_check():
    """Health check for strategy report service"""
    service = get_strategy_report_service()
    reports = service.list_reports()
    return {
        "status": "healthy",
        "service": "strategy-reports",
        "total_reports": len(reports),
    }


@router.post("/generate")
async def generate_report(request: GenerateReportRequest = GenerateReportRequest()):
    """
    Generate a weekly strategy report.
    
    Combines competitor analysis, trending data, and AI recommendations
    into an actionable weekly content plan.
    
    Optional: Pass user_performance data for personalized recommendations.
    """
    service = get_strategy_report_service()

    try:
        report = await service.generate_report(
            user_performance=request.user_performance,
            trending_data=request.trending_data,
        )

        return {
            "status": "generated",
            "report": report.model_dump(),
        }

    except Exception as e:
        logger.error(f"Error generating strategy report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_report():
    """Get the most recently generated strategy report"""
    service = get_strategy_report_service()
    report = service.get_latest_report()

    if not report:
        raise HTTPException(
            status_code=404,
            detail="No reports generated yet. POST /api/strategy-report/generate first.",
        )

    return report.model_dump()


@router.get("/latest/markdown")
async def get_latest_report_markdown():
    """Get the latest report as markdown text"""
    service = get_strategy_report_service()
    report = service.get_latest_report()

    if not report:
        raise HTTPException(status_code=404, detail="No reports generated yet.")

    return {
        "week_start": report.week_start,
        "week_end": report.week_end,
        "markdown": report.report_markdown,
    }


@router.get("/week/{week_start}")
async def get_report_for_week(week_start: str):
    """
    Get a report for a specific week.
    
    Args:
        week_start: ISO date string (YYYY-MM-DD) for the Monday of the week
    """
    service = get_strategy_report_service()
    report = service.get_report_for_week(week_start)

    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"No report found for week starting {week_start}",
        )

    return report.model_dump()


@router.get("/list")
async def list_reports():
    """List all generated strategy reports"""
    service = get_strategy_report_service()
    reports = service.list_reports()
    return {
        "count": len(reports),
        "reports": reports,
    }
