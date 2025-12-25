"""
Comprehensive App Validation Endpoint
=====================================
Validates all components of the application before critical operations.
"""
from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional, Dict, Any
from loguru import logger

from services.validation_framework import get_validation_framework

router = APIRouter(prefix="/api/app-validation", tags=["App Validation"])


@router.get("/all")
async def validate_all_components(
    components: Optional[str] = Query(None, description="Comma-separated list of components to validate")
):
    """
    Validate all application components or specific ones.
    
    Available components:
    - configuration: API keys, environment variables
    - database: Connectivity, schema, tables
    - external_apis: OpenAI, Blotato, RapidAPI connectivity
    - social_accounts: Account connectivity and tokens
    - scheduled_posts: Upcoming posts validation
    - narrative_setup: Narrative goals and pillars
    - experiment_setup: Experiments and hypotheses
    - file_system: Paths, permissions, disk space
    - event_bus: Event bus connectivity
    - media_processing: Media processing setup
    """
    framework = get_validation_framework()
    
    component_list = None
    if components:
        component_list = [c.strip() for c in components.split(",")]
    
    try:
        results = await framework.validate_all(component_list)
        
        # Convert to dict format
        results_dict = {
            component: result.to_dict()
            for component, result in results.items()
        }
        
        # Calculate overall health
        total_issues = sum(
            len(r["issues"]) for r in results_dict.values()
        )
        total_warnings = sum(
            len(r["warnings"]) for r in results_dict.values()
        )
        all_valid = all(
            r["valid"] for r in results_dict.values()
        )
        
        return {
            "overall_health": "healthy" if all_valid and total_issues == 0 else "unhealthy",
            "all_valid": all_valid,
            "total_issues": total_issues,
            "total_warnings": total_warnings,
            "components": results_dict,
            "summary": {
                "valid_components": sum(1 for r in results_dict.values() if r["valid"]),
                "invalid_components": sum(1 for r in results_dict.values() if not r["valid"]),
                "total_components": len(results_dict)
            }
        }
    
    except Exception as e:
        logger.error(f"Validation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@router.get("/component/{component_name}")
async def validate_single_component(component_name: str):
    """Validate a single component"""
    framework = get_validation_framework()
    
    if component_name not in framework.validators:
        raise HTTPException(
            status_code=404,
            detail=f"Component '{component_name}' not found. Available: {', '.join(framework.validators.keys())}"
        )
    
    try:
        results = await framework.validate_all([component_name])
        result = results[component_name]
        
        return {
            "component": component_name,
            "result": result.to_dict()
        }
    
    except Exception as e:
        logger.error(f"Validation failed for {component_name}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Validation error: {str(e)}")


@router.get("/health-check")
async def quick_health_check():
    """
    Quick health check - validates only critical components.
    Returns fast response for monitoring.
    """
    framework = get_validation_framework()
    
    critical_components = ["configuration", "database", "file_system"]
    
    try:
        results = await framework.validate_all(critical_components)
        
        critical_issues = sum(
            len(r.issues) for r in results.values()
        )
        
        is_healthy = critical_issues == 0
        
        return {
            "healthy": is_healthy,
            "critical_issues": critical_issues,
            "components_checked": list(results.keys()),
            "timestamp": results[critical_components[0]].validated_at.isoformat() if results else None
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "healthy": False,
            "error": str(e)
        }

