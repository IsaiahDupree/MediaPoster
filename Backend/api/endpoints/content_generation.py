"""
Content Generation API (OPS-008)
=================================
API endpoints for AI content generation with FATE scoring and awareness classification.

Endpoints:
- POST /api/v1/generate - Generate content variants
- GET /api/v1/prompt-runs/{run_id} - Get prompt run details
- GET /api/v1/prompt-runs - List recent prompt runs
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from loguru import logger

from services.content_generation_pipeline import (
    get_content_generation_pipeline,
    GenerationRequest,
    GenerationResult
)


router = APIRouter(prefix="/api/v1", tags=["Content Generation"])


@router.post("/generate")
async def generate_content(request: GenerationRequest) -> GenerationResult:
    """
    Generate AI content variants with FATE scoring

    Request:
    ```json
    {
      "template_id": "tpl_problem_aware_001",
      "offer_id": "offer_keyword_radar",
      "icp_id": "icp_indie_founders",
      "awareness_level": 2,
      "channel": "post",
      "platform": "x",
      "variants": 3,
      "temperature": 0.7,
      "model": "gpt-4o",
      "inputs": {
        "topic": "keyword research for SaaS",
        "angle": "time-saving"
      }
    }
    ```

    Response:
    ```json
    {
      "success": true,
      "variants": [
        {
          "prompt_run_id": "run_20260118_123456_abc123",
          "template_id": "tpl_problem_aware_001",
          "output_text": "Generated content...",
          "fate_scores": {"F": 0.75, "A": 0.68, "T": 0.82, "E": 0.71},
          "classified_awareness": 2,
          ...
        }
      ],
      "metadata": {...}
    }
    ```

    Args:
        request: Generation request

    Returns:
        Generation result with variants
    """
    try:
        logger.info(
            f"🎨 Content generation request | "
            f"Template: {request.template_id} | "
            f"Offer: {request.offer_id} | "
            f"ICP: {request.icp_id} | "
            f"Variants: {request.variants}"
        )

        pipeline = get_content_generation_pipeline()
        result = await pipeline.generate(request)

        if not result.success:
            logger.error(f"Generation failed: {result.error}")
            raise HTTPException(status_code=500, detail=result.error)

        logger.success(f"✅ Generated {len(result.variants)} variants")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Content generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/prompt-runs/{run_id}")
async def get_prompt_run(run_id: str):
    """
    Get prompt run details by ID

    Args:
        run_id: Prompt run ID

    Returns:
        Prompt run record with full attribution
    """
    # TODO: Implement database lookup
    raise HTTPException(status_code=501, detail="Not implemented yet - requires database integration")


@router.get("/prompt-runs")
async def list_prompt_runs(
    template_id: Optional[str] = None,
    offer_id: Optional[str] = None,
    icp_id: Optional[str] = None,
    limit: int = 20
):
    """
    List recent prompt runs with optional filters

    Query params:
    - template_id: Filter by template
    - offer_id: Filter by offer
    - icp_id: Filter by ICP
    - limit: Max results (default: 20)

    Returns:
        List of prompt run records
    """
    # TODO: Implement database query
    raise HTTPException(status_code=501, detail="Not implemented yet - requires database integration")


@router.get("/health")
async def content_generation_health():
    """
    Health check for content generation pipeline

    Returns service status and OpenAI API availability.
    """
    try:
        pipeline = get_content_generation_pipeline()

        # Check if OpenAI API key is configured
        has_api_key = bool(pipeline.openai_api_key)

        return {
            "success": True,
            "data": {
                "service": "content_generation_pipeline",
                "status": "operational",
                "openai_configured": has_api_key,
                "fate_scorer_available": True,
                "awareness_classifier_available": True
            }
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }
