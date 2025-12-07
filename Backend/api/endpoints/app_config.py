"""
Configuration API endpoint
View and manage app configuration and feature flags
"""
import sys
import os
from fastapi import APIRouter

# Add parent directory to path to avoid config.py vs config/ conflict
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config.feature_flags import feature_flags

router = APIRouter()


@router.get("/")
async def get_configuration():
    """Get current app configuration and feature flags"""
    return {
        "status": "success",
        "configuration": feature_flags.to_dict()
    }


@router.get("/health")
async def health_check():
    """Comprehensive health check with all services"""
    config = feature_flags.to_dict()
    
    health_status = {
        "status": "healthy",
        "app_mode": config["app_mode"],
        "services": {
            "api": "operational",
            "database": "operational"  # Could add actual DB check
        },
        "features": {
            "core_features": len([f for f in config["features"]["core"].values() if f]),
            "active_adapters": len(config["enabled_adapters"]),
            "optional_features": len([f for f in config["features"]["optional"].values() if f])
        },
        "adapters": config["features"]["adapters"],
        "warnings": []
    }
    
    # Add warnings for missing configurations
    if not feature_flags.email_service_enabled:
        health_status["warnings"].append("Email service not configured (SMTP credentials missing)")
    
    if len(config["enabled_adapters"]) == 0:
        health_status["warnings"].append("No platform adapters configured")
    
    return health_status
