"""
Media Creation API Endpoints
Create and manage various types of media content
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import uuid

from database.connection import get_db
from database.models import MediaCreationProject, MediaCreationTemplate
from services.media_creation_service import MediaCreationService
from services.content_type_handlers import get_content_handler
from loguru import logger

router = APIRouter(prefix="/api/media-creation", tags=["Media Creation"])


class CreateProjectRequest(BaseModel):
    """Request to create a media project"""
    project_name: str
    content_type: str  # blog_post, video, carousel, etc.
    template_id: Optional[uuid.UUID] = None
    initial_data: Optional[Dict[str, Any]] = None


class UpdateProjectRequest(BaseModel):
    """Request to update project content"""
    content_data: Dict[str, Any]


class CreateContentRequest(BaseModel):
    """Request to create content for a project"""
    config: Dict[str, Any]  # Type-specific configuration


@router.get("/content-types")
async def get_content_types():
    """Get list of available content types"""
    return {
        "content_types": [
            {
                "id": "blog_post",
                "name": "Blog Post",
                "description": "AI-generated blog posts",
                "icon": "file-text",
                "supports_ai": True
            },
            {
                "id": "video",
                "name": "Video",
                "description": "Video editing and creation",
                "icon": "video",
                "supports_ai": False
            },
            {
                "id": "carousel",
                "name": "Carousel",
                "description": "Multi-slide carousel posts",
                "icon": "images",
                "supports_ai": False
            },
            {
                "id": "ai_generated_carousel",
                "name": "AI Carousel",
                "description": "AI-generated carousel images",
                "icon": "sparkles",
                "supports_ai": True
            },
            {
                "id": "ai_generated_video",
                "name": "AI Video",
                "description": "AI-generated video content",
                "icon": "film",
                "supports_ai": True
            },
            {
                "id": "words_on_video",
                "name": "Words on Video",
                "description": "Video with text overlays",
                "icon": "type",
                "supports_ai": False
            },
            {
                "id": "broll_with_text",
                "name": "B-Roll + Text",
                "description": "B-roll video with music and text",
                "icon": "music",
                "supports_ai": False
            }
        ]
    }


@router.get("/templates")
async def get_templates(
    content_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get available templates"""
    try:
        service = MediaCreationService(db)
        templates = await service.get_available_templates(content_type)
        
        return {
            "templates": [
                {
                    "id": str(t.id),
                    "name": t.template_name,
                    "content_type": t.content_type,
                    "description": t.description,
                    "theme": t.theme,
                    "config": t.template_config if isinstance(t.template_config, dict) else {}
                }
                for t in templates
            ]
        }
    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects", response_model=Dict[str, Any])
async def create_project(
    request: CreateProjectRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new media creation project"""
    try:
        user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")  # Placeholder
        
        service = MediaCreationService(db)
        project = await service.create_project(
            user_id=user_id,
            project_name=request.project_name,
            content_type=request.content_type,
            template_id=request.template_id,
            initial_data=request.initial_data
        )
        
        return {
            "id": str(project.id),
            "project_name": project.project_name,
            "content_type": project.content_type,
            "status": project.status,
            "created_at": project.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects")
async def get_projects(
    content_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get all projects for user"""
    try:
        user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")  # Placeholder
        
        service = MediaCreationService(db)
        projects = await service.get_user_projects(
            user_id=user_id,
            content_type=content_type,
            status=status
        )
        
        return {
            "projects": [
                {
                    "id": str(p.id),
                    "project_name": p.project_name,
                    "content_type": p.content_type,
                    "status": p.status,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat()
                }
                for p in projects
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific project"""
    try:
        service = MediaCreationService(db)
        project = await service.get_project(uuid.UUID(project_id))
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {
            "id": str(project.id),
            "project_name": project.project_name,
            "content_type": project.content_type,
            "content_data": project.content_data if isinstance(project.content_data, dict) else {},
            "status": project.status,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/create-content")
async def create_content(
    project_id: str,
    request: CreateContentRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create content for a project using appropriate handler"""
    try:
        service = MediaCreationService(db)
        project = await service.get_project(uuid.UUID(project_id))
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get appropriate handler
        handler = get_content_handler(project.content_type, db)
        
        # Create content
        content_result = await handler.create_content(
            project_id=uuid.UUID(project_id),
            config=request.config
        )
        
        # Update project with content
        await service.update_project_content(
            project_id=uuid.UUID(project_id),
            content_data=content_result
        )
        
        return {
            "project_id": project_id,
            "content": content_result,
            "status": "created"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/{project_id}/edit")
async def edit_project(
    project_id: str,
    request: UpdateProjectRequest,
    db: AsyncSession = Depends(get_db)
):
    """Edit project content"""
    try:
        service = MediaCreationService(db)
        project = await service.update_project_content(
            project_id=uuid.UUID(project_id),
            content_data=request.content_data
        )
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        return {
            "id": str(project.id),
            "status": "updated",
            "content_data": project.content_data if isinstance(project.content_data, dict) else {}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/preview")
async def get_preview(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get preview URL for project"""
    try:
        service = MediaCreationService(db)
        project = await service.get_project(uuid.UUID(project_id))
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        # Get appropriate handler
        handler = get_content_handler(project.content_type, db)
        
        # Generate preview URL
        preview_url = await handler.render_preview(uuid.UUID(project_id))
        
        return {
            "project_id": project_id,
            "preview_url": preview_url
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting preview: {e}")
        raise HTTPException(status_code=500, detail=str(e))






