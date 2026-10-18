"""
Video Toolkit API Endpoints

Pub/Sub endpoints for video toolkit extraction and synchronization.
"""
import os
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

from services.video_toolkit_pubsub import (
    VideoToolkitService,
    ExtractRequest,
    ToolkitResource,
    get_toolkit_service
)

router = APIRouter(prefix="/api/video-toolkit", tags=["Video Toolkit"])


class ExtractRequestModel(BaseModel):
    """Request model for toolkit extraction"""
    target_dir: str
    include_motion_canvas: bool = False
    include_docs: bool = True
    include_scripts: bool = True
    include_assets: bool = True
    components_only: bool = False


class GitPushRequestModel(BaseModel):
    """Request model for GitHub push"""
    repo_path: str
    commit_message: str = "Update video toolkit resources"
    branch: str = "main"


@router.get("/resources")
async def list_resources():
    """
    List all available resources in the video toolkit.
    
    Returns components, scripts, docs, and config files.
    """
    service = get_toolkit_service()
    resources = service.list_resources()
    
    # Group by type
    by_type = {}
    for r in resources:
        if r.type not in by_type:
            by_type[r.type] = []
        by_type[r.type].append({
            "name": r.name,
            "path": r.path,
            "size_bytes": r.size_bytes,
            "last_modified": r.last_modified
        })
    
    return {
        "total": len(resources),
        "by_type": by_type,
        "resources": [
            {
                "name": r.name,
                "path": r.path,
                "type": r.type,
                "size_bytes": r.size_bytes,
                "last_modified": r.last_modified
            }
            for r in resources
        ]
    }


@router.get("/resources/summary")
async def resources_summary():
    """
    Get a summary of video toolkit resources.
    """
    service = get_toolkit_service()
    resources = service.list_resources()
    
    # Calculate stats
    by_type = {}
    total_size = 0
    
    for r in resources:
        if r.type not in by_type:
            by_type[r.type] = {"count": 0, "size_bytes": 0}
        by_type[r.type]["count"] += 1
        by_type[r.type]["size_bytes"] += r.size_bytes
        total_size += r.size_bytes
    
    return {
        "total_resources": len(resources),
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
        "by_type": by_type,
        "source_path": str(service.remotion_path)
    }


@router.post("/extract")
async def extract_toolkit(request: ExtractRequestModel):
    """
    Extract video toolkit to target directory.
    
    Publishes TOOLKIT_EXTRACT_REQUESTED and TOOLKIT_EXTRACT_COMPLETED events.
    """
    service = get_toolkit_service()
    
    extract_request = ExtractRequest(
        target_dir=request.target_dir,
        include_motion_canvas=request.include_motion_canvas,
        include_docs=request.include_docs,
        include_scripts=request.include_scripts,
        include_assets=request.include_assets,
        components_only=request.components_only
    )
    
    result = service.extract(extract_request)
    
    if not result.success:
        raise HTTPException(status_code=500, detail={"errors": result.errors})
    
    return {
        "success": result.success,
        "target_dir": result.target_dir,
        "files_copied": result.files_copied,
        "total_size_bytes": result.total_size_bytes,
        "total_size_mb": round(result.total_size_bytes / (1024 * 1024), 2),
        "timestamp": result.timestamp
    }


@router.post("/push")
async def push_to_github(request: GitPushRequestModel):
    """
    Push changes to GitHub.
    
    Publishes TOOLKIT_GITHUB_PUSH_REQUESTED and TOOLKIT_GITHUB_PUSH_COMPLETED events.
    """
    service = get_toolkit_service()
    
    result = service.push_to_github(
        repo_path=request.repo_path,
        commit_message=request.commit_message,
        branch=request.branch
    )
    
    if not result.success:
        raise HTTPException(status_code=500, detail={"errors": result.errors})
    
    return {
        "success": result.success,
        "repo_path": result.repo_path,
        "commit_hash": result.commit_hash,
        "branch": result.branch,
        "files_changed": result.files_changed,
        "message": result.message
    }


@router.post("/extract-and-push")
async def extract_and_push(
    target_dir: str = Query(..., description="Target directory for extraction"),
    repo_path: str = Query(None, description="Repository path (defaults to target_dir)"),
    commit_message: str = Query("Update video toolkit resources"),
    include_motion_canvas: bool = Query(False),
    include_docs: bool = Query(True),
    include_scripts: bool = Query(True)
):
    """
    Extract toolkit and push to GitHub in one operation.
    
    Combined workflow for convenience.
    """
    service = get_toolkit_service()
    
    # Extract
    extract_request = ExtractRequest(
        target_dir=target_dir,
        include_motion_canvas=include_motion_canvas,
        include_docs=include_docs,
        include_scripts=include_scripts,
        include_assets=True,
        components_only=False
    )
    
    extract_result = service.extract(extract_request)
    
    if not extract_result.success:
        raise HTTPException(status_code=500, detail={
            "step": "extract",
            "errors": extract_result.errors
        })
    
    # Push
    push_repo = repo_path or target_dir
    push_result = service.push_to_github(
        repo_path=push_repo,
        commit_message=commit_message,
        branch="main"
    )
    
    return {
        "extract": {
            "success": extract_result.success,
            "files_copied": extract_result.files_copied,
            "total_size_mb": round(extract_result.total_size_bytes / (1024 * 1024), 2)
        },
        "push": {
            "success": push_result.success,
            "commit_hash": push_result.commit_hash,
            "files_changed": push_result.files_changed,
            "message": push_result.message if push_result.success else push_result.errors
        }
    }


@router.get("/topics")
async def list_topics():
    """
    List available pub/sub topics for video toolkit.
    """
    return {
        "topics": [
            {
                "name": "video_toolkit.extract",
                "description": "Extract toolkit to target directory",
                "events": ["TOOLKIT_EXTRACT_REQUESTED", "TOOLKIT_EXTRACT_COMPLETED", "TOOLKIT_EXTRACT_FAILED"]
            },
            {
                "name": "video_toolkit.sync",
                "description": "Sync resources between projects",
                "events": ["TOOLKIT_SYNC_REQUESTED", "TOOLKIT_SYNC_COMPLETED", "TOOLKIT_SYNC_FAILED"]
            },
            {
                "name": "video_toolkit.push",
                "description": "Push changes to GitHub",
                "events": ["TOOLKIT_GITHUB_PUSH_REQUESTED", "TOOLKIT_GITHUB_PUSH_COMPLETED", "TOOLKIT_GITHUB_PUSH_FAILED"]
            },
            {
                "name": "video_toolkit.status",
                "description": "Status updates for operations",
                "events": ["TOOLKIT_STATUS_UPDATE"]
            }
        ]
    }
