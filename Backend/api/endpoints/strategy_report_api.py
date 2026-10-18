"""
Strategy Report API Endpoints
Weekly AI-generated content strategy reports.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
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


@router.post("/full-pipeline")
async def run_full_research_pipeline():
    """
    Run the complete weekly research pipeline in one call:
    1. Batch analyze all competitors (AI analysis)
    2. Run content gap analysis
    3. Run performance benchmark
    4. Generate weekly strategy report combining all results

    Returns a summary of everything generated.
    """
    from services.competitor_service import get_competitor_service
    from services.competitor_analysis_service import get_analysis_service
    from services.content_gap_service import get_content_gap_service
    from services.benchmark_service import get_benchmark_service
    from services.hook_library_service import get_hook_library_service

    results = {
        "steps_completed": [],
        "steps_failed": [],
    }

    # Step 1: Batch analyze competitors
    try:
        competitor_svc = get_competitor_service()
        analysis_svc = get_analysis_service()
        accounts = competitor_svc.get_stored_accounts()
        analyzed = 0
        for username in accounts:
            try:
                content = competitor_svc.load_stored_content(username)
                if content:
                    learnings = await analysis_svc.analyze_account(username)
                    if learnings:
                        analyzed += 1
            except Exception as e:
                logger.warning(f"Skip @{username} analysis: {e}")
        results["competitor_analyses"] = analyzed
        results["steps_completed"].append("batch_analyze")
    except Exception as e:
        logger.error(f"Batch analyze failed: {e}")
        results["steps_failed"].append({"step": "batch_analyze", "error": str(e)})

    # Step 2: Extract hooks from all analyses
    try:
        hook_svc = get_hook_library_service()
        hook_result = await hook_svc.auto_populate_from_all_competitors()
        results["hooks_extracted"] = hook_result.get("hooks_added", 0)
        results["steps_completed"].append("extract_hooks")
    except Exception as e:
        logger.error(f"Hook extraction failed: {e}")
        results["steps_failed"].append({"step": "extract_hooks", "error": str(e)})

    # Step 3: Content gap analysis
    try:
        gap_svc = get_content_gap_service()
        gap_result = await gap_svc.analyze_gaps()
        results["gap_themes_found"] = len(gap_result.gap_themes)
        results["gap_coverage_score"] = gap_result.gap_coverage_score
        results["steps_completed"].append("gap_analysis")
    except Exception as e:
        logger.error(f"Gap analysis failed: {e}")
        results["steps_failed"].append({"step": "gap_analysis", "error": str(e)})

    # Step 4: Benchmark
    try:
        bench_svc = get_benchmark_service()
        bench_result = await bench_svc.run_benchmark()
        results["benchmark_score"] = bench_result.overall_score
        results["steps_completed"].append("benchmark")
    except Exception as e:
        logger.error(f"Benchmark failed: {e}")
        results["steps_failed"].append({"step": "benchmark", "error": str(e)})

    # Step 5: Generate strategy report
    try:
        report_svc = get_strategy_report_service()
        report = await report_svc.generate_report()
        results["report_week"] = report.week_start
        results["report_ideas"] = len(report.content_ideas)
        results["report_actions"] = len(report.action_items)
        results["steps_completed"].append("strategy_report")
    except Exception as e:
        logger.error(f"Strategy report failed: {e}")
        results["steps_failed"].append({"step": "strategy_report", "error": str(e)})

    results["status"] = "completed" if not results["steps_failed"] else "partial"
    return results


@router.get("/export")
async def export_research_data():
    """
    Export all research data as a single JSON bundle.
    Includes: competitor analyses, hooks, gap analysis, benchmarks, and latest report.
    Useful for backups or sharing research insights.
    """
    import json as json_mod
    from services.competitor_service import get_competitor_service, COMPETITOR_RESEARCH_DIR
    from services.hook_library_service import get_hook_library_service
    from services.content_gap_service import get_content_gap_service
    from services.benchmark_service import get_benchmark_service

    export: Dict[str, Any] = {
        "exported_at": datetime.now().isoformat(),
        "competitors": [],
        "hooks": [],
        "gap_analysis": None,
        "benchmark": None,
        "strategy_report": None,
    }

    # Competitors
    try:
        svc = get_competitor_service()
        for username in svc.get_stored_accounts():
            entry = {"username": username}
            analysis_path = svc.storage_dir / "accounts" / username / "analysis" / "learnings.json"
            if analysis_path.exists():
                with open(analysis_path) as f:
                    entry["analysis"] = json_mod.load(f)
            export["competitors"].append(entry)
    except Exception as e:
        logger.warning(f"Export competitors error: {e}")

    # Hooks
    try:
        hook_svc = get_hook_library_service()
        export["hooks"] = hook_svc.get_hooks(limit=500)
    except Exception as e:
        logger.warning(f"Export hooks error: {e}")

    # Gap analysis
    try:
        gap_svc = get_content_gap_service()
        gap = gap_svc.get_latest_analysis()
        if gap:
            export["gap_analysis"] = gap.model_dump()
    except Exception as e:
        logger.warning(f"Export gap analysis error: {e}")

    # Benchmark
    try:
        bench_svc = get_benchmark_service()
        bench = bench_svc.get_latest_benchmark()
        if bench:
            export["benchmark"] = bench.model_dump()
    except Exception as e:
        logger.warning(f"Export benchmark error: {e}")

    # Strategy report
    try:
        report_svc = get_strategy_report_service()
        report = report_svc.get_latest_report()
        if report:
            export["strategy_report"] = report.model_dump()
    except Exception as e:
        logger.warning(f"Export report error: {e}")

    return export
