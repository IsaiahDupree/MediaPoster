"""
Media Creation Service
Handles creation of various content types: blog, video, carousel, AI-generated, etc.
"""
import logging
from typing import Dict, List, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import json

from database.models import MediaCreationProject, MediaCreationTemplate, MediaCreationAsset
from loguru import logger

logger = logging.getLogger(__name__)


class MediaCreationService:
    """
    Service for creating various types of media content
    
    Supports:
    - Blog posts
    - Video editing
    - Carousels
    - AI-generated carousels
    - AI-generated videos
    - Words on video
    - B-roll with text overlay
    - Different themes and styles
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_project(
        self,
        user_id: UUID,
        project_name: str,
        content_type: str,
        template_id: Optional[UUID] = None,
        initial_data: Optional[Dict[str, Any]] = None
    ) -> MediaCreationProject:
        """
        Create a new media creation project
        
        Args:
            user_id: User ID
            project_name: Name of the project
            content_type: Type of content (blog_post, video, carousel, etc.)
            template_id: Optional template to use
            initial_data: Initial content data
            
        Returns:
            Created project
        """
        try:
            project = MediaCreationProject(
                user_id=user_id,
                project_name=project_name,
                content_type=content_type,
                template_id=template_id,
                content_data=initial_data or {},
                status='draft',
                is_draft=True
            )
            
            self.db.add(project)
            await self.db.commit()
            await self.db.refresh(project)
            
            logger.info(f"Created media project: {project.id} ({content_type})")
            return project
            
        except Exception as e:
            logger.error(f"Error creating media project: {e}")
            await self.db.rollback()
            raise
    
    async def get_project(self, project_id: UUID) -> Optional[MediaCreationProject]:
        """Get a media creation project"""
        try:
            result = await self.db.execute(
                select(MediaCreationProject).where(MediaCreationProject.id == project_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting project: {e}")
            return None
    
    async def update_project_content(
        self,
        project_id: UUID,
        content_data: Dict[str, Any]
    ) -> Optional[MediaCreationProject]:
        """Update project content data"""
        try:
            project = await self.get_project(project_id)
            if not project:
                return None
            
            # Merge content data
            current_data = project.content_data if isinstance(project.content_data, dict) else {}
            current_data.update(content_data)
            project.content_data = current_data
            project.updated_at = datetime.now()
            
            await self.db.commit()
            await self.db.refresh(project)
            
            return project
            
        except Exception as e:
            logger.error(f"Error updating project content: {e}")
            await self.db.rollback()
            return None
    
    async def add_asset(
        self,
        project_id: UUID,
        asset_type: str,
        asset_url: str,
        metadata: Optional[Dict[str, Any]] = None,
        order_index: Optional[int] = None
    ) -> Optional[MediaCreationAsset]:
        """Add an asset to a project"""
        try:
            asset = MediaCreationAsset(
                project_id=project_id,
                asset_type=asset_type,
                asset_url=asset_url,
                asset_metadata=metadata or {},  # Use asset_metadata instead of metadata
                order_index=order_index
            )
            
            self.db.add(asset)
            await self.db.commit()
            await self.db.refresh(asset)
            
            return asset
            
        except Exception as e:
            logger.error(f"Error adding asset: {e}")
            await self.db.rollback()
            return None
    
    async def get_user_projects(
        self,
        user_id: UUID,
        content_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[MediaCreationProject]:
        """Get all projects for a user"""
        try:
            query = select(MediaCreationProject).where(
                MediaCreationProject.user_id == user_id
            )
            
            if content_type:
                query = query.where(MediaCreationProject.content_type == content_type)
            if status:
                query = query.where(MediaCreationProject.status == status)
            
            query = query.order_by(MediaCreationProject.created_at.desc())
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting user projects: {e}")
            return []
    
    async def get_available_templates(
        self,
        content_type: Optional[str] = None
    ) -> List[MediaCreationTemplate]:
        """Get available templates"""
        try:
            query = select(MediaCreationTemplate).where(
                MediaCreationTemplate.is_active == True
            )
            
            if content_type:
                query = query.where(MediaCreationTemplate.content_type == content_type)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return []

