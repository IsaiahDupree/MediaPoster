"""
Video Format API Endpoints
==========================
API endpoints for format-agnostic video rendering.
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, List
from pathlib import Path
from loguru import logger
from uuid import uuid4

from services.video_renderer import VideoRenderService, FORMAT_REGISTRY
from services.event_bus import EventBus, Topics

router = APIRouter(prefix="/api/video-formats", tags=["video-formats"])


@router.get("/formats")
async def list_formats() -> Dict[str, Any]:
    """
    List all available video formats.
    
    Returns:
        Dictionary of format_id -> format_info
    """
    service = VideoRenderService()
    formats = service.list_formats()
    
    return {
        "formats": formats,
        "total": len(formats),
    }


@router.get("/formats/{format_id}")
async def get_format(format_id: str) -> Dict[str, Any]:
    """
    Get format configuration by ID.
    
    Args:
        format_id: Format identifier (e.g., 'explainer_v1')
    
    Returns:
        Format configuration
    """
    service = VideoRenderService()
    format_config = service.get_format(format_id)
    
    if not format_config:
        raise HTTPException(
            status_code=404,
            detail=f"Format '{format_id}' not found. Available: {list(FORMAT_REGISTRY.keys())}"
        )
    
    return format_config


@router.post("/render")
async def render_video(
    content: Dict[str, Any] = Body(...),
    format_id: str = Body(...),
    adapter: str = Body("motion_canvas", description="Rendering adapter"),
    async_render: bool = Body(True, description="Render asynchronously via event bus"),
) -> Dict[str, Any]:
    """
    Render a video using format-agnostic system.
    
    Request Body:
        - content: Universal content schema
        - format_id: Format identifier (e.g., 'explainer_v1')
        - adapter: Rendering adapter ('motion_canvas' or 'remotion')
        - async_render: If True, render via event bus (async). If False, render synchronously.
    
    Returns:
        Render job information
    """
    try:
        service = VideoRenderService()
        
        # Validate format
        if format_id not in FORMAT_REGISTRY:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format_id: {format_id}. Available: {list(FORMAT_REGISTRY.keys())}"
            )
        
        job_id = str(uuid4())
        correlation_id = str(uuid4())
        
        if async_render:
            # Emit event for async processing
            event_bus = EventBus.get_instance()
            await event_bus.publish(
                Topics.VIDEO_RENDER_REQUESTED,
                {
                    "job_id": job_id,
                    "content": content,
                    "format_id": format_id,
                    "adapter": adapter,
                },
                correlation_id=correlation_id,
                source="video-format-api"
            )
            
            logger.info(f"📡 Emitted VIDEO_RENDER_REQUESTED: {job_id} (format: {format_id})")
            
            return {
                "status": "queued",
                "job_id": job_id,
                "correlation_id": correlation_id,
                "format_id": format_id,
                "adapter": adapter,
                "message": "Render job queued. Subscribe to video.render.* events for progress.",
            }
        else:
            # Synchronous rendering (build scene graph only for now)
            scene_graph = service.build_scene_graph(content, format_id)
            
            return {
                "status": "success",
                "job_id": job_id,
                "format_id": format_id,
                "adapter": adapter,
                "scene_count": len(scene_graph),
                "scene_graph": scene_graph,
                "message": "Scene graph built. Rendering will be implemented in adapter layer.",
            }
        
    except Exception as e:
        logger.error(f"Error rendering video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preview-scene-graph")
async def preview_scene_graph(
    content: Dict[str, Any] = Body(...),
    format_id: str = Body(...),
) -> Dict[str, Any]:
    """
    Preview the scene graph without rendering.
    
    Useful for:
    - Validating content structure
    - Previewing scene breakdown
    - Debugging format configurations
    
    Request Body:
        - content: Universal content schema
        - format_id: Format identifier
    
    Returns:
        Scene graph preview
    """
    """
    Preview the scene graph without rendering.
    
    Useful for:
    - Validating content structure
    - Previewing scene breakdown
    - Debugging format configurations
    
    Request Body:
        - content: Universal content schema
        - format_id: Format identifier
    
    Returns:
        Scene graph preview
    """
    try:
        service = VideoRenderService()
        
        if format_id not in FORMAT_REGISTRY:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid format_id: {format_id}. Available: {list(FORMAT_REGISTRY.keys())}"
            )
        
        scene_graph = service.build_scene_graph(content, format_id)
        
        # Calculate total duration
        total_duration = sum(scene.get("duration", 0) for scene in scene_graph)
        
        return {
            "format_id": format_id,
            "format_name": FORMAT_REGISTRY[format_id].get("name"),
            "total_scenes": len(scene_graph),
            "total_duration": total_duration,
            "scenes": [
                {
                    "index": i,
                    "scene_type": scene.get("scene_type"),
                    "duration": scene.get("duration"),
                    "data_preview": {
                        "title": scene.get("data", {}).get("title"),
                        "type": scene.get("data", {}).get("type"),
                    }
                }
                for i, scene in enumerate(scene_graph)
            ],
        }
        
    except Exception as e:
        logger.error(f"Error previewing scene graph: {e}")
        raise HTTPException(status_code=500, detail=str(e))

