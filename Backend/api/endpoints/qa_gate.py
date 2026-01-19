"""
QA Gate API (OPS-009)
=====================
API endpoints for content quality assurance before publishing.

Endpoints:
- POST /api/v1/qa/check - Check content quality
- GET /api/v1/qa/health - QA service health check
"""

from fastapi import APIRouter, HTTPException
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from loguru import logger

from services.qa_gate_service import (
    get_qa_gate_service,
    QAResult
)


router = APIRouter(prefix="/api/v1/qa", tags=["QA Gate"])


class QACheckRequest(BaseModel):
    """Request to check content quality"""
    content: str = Field(..., description="Content to check")
    template_id: str = Field(..., description="Template ID used")
    awareness_level: int = Field(..., ge=1, le=5, description="Target awareness level (1-5)")
    platform: str = Field(..., description="Target platform (x, instagram, tiktok, etc.)")
    fate_scores: Optional[Dict[str, float]] = Field(default=None, description="FATE scores")
    classified_awareness: Optional[int] = Field(default=None, description="Classified awareness level")


@router.post("/check")
async def check_content_quality(request: QACheckRequest) -> QAResult:
    """
    Check content quality before publishing

    Request:
    ```json
    {
      "content": "Generated content...",
      "template_id": "tpl_problem_aware_001",
      "awareness_level": 2,
      "platform": "x",
      "fate_scores": {"F": 0.75, "A": 0.68, "T": 0.82, "E": 0.71},
      "classified_awareness": 2
    }
    ```

    Response:
    ```json
    {
      "status": "PASS|WARN|FAIL",
      "passed": true,
      "issues": [
        {
          "severity": "warning",
          "category": "fate",
          "message": "Low F score: 0.25 (minimum: 0.30)",
          "details": {...}
        }
      ],
      "scores": {"F": 0.75, "A": 0.68, "T": 0.82, "E": 0.71},
      "metadata": {...}
    }
    ```

    Args:
        request: QA check request

    Returns:
        QA result with status and issues
    """
    try:
        logger.info(
            f"🛡️ QA check request | "
            f"Platform: {request.platform} | "
            f"Awareness: {request.awareness_level} | "
            f"Length: {len(request.content)} chars"
        )

        qa_gate = get_qa_gate_service()
        result = qa_gate.check(
            content=request.content,
            template_id=request.template_id,
            awareness_level=request.awareness_level,
            platform=request.platform,
            fate_scores=request.fate_scores,
            classified_awareness=request.classified_awareness
        )

        logger.info(f"✓ QA check complete | Status: {result.status} | Issues: {len(result.issues)}")

        return result

    except Exception as e:
        logger.error(f"QA check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def qa_gate_health():
    """
    Health check for QA gate service

    Returns service status and configuration.
    """
    try:
        qa_gate = get_qa_gate_service()

        return {
            "success": True,
            "data": {
                "service": "qa_gate",
                "status": "operational",
                "forbidden_patterns_count": len(qa_gate.forbidden_regexes),
                "min_fate_scores": qa_gate.DEFAULT_MIN_FATE_SCORES,
                "supported_platforms": list(PLATFORM_CONSTRAINTS.keys())
            }
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Import for health endpoint
from services.qa_gate_service import PLATFORM_CONSTRAINTS
