"""
Content Type Handlers
Specific handlers for each content type (blog, carousel, words-on-video, etc.)
"""
import logging
from typing import Dict, List, Any, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from services.ai_content_generator import AIContentGenerator, AIProvider
from loguru import logger

logger = logging.getLogger(__name__)


class ContentTypeHandler:
    """Base class for content type handlers"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.ai_generator = AIContentGenerator()
    
    async def create_content(self, project_id: UUID, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create content of this type"""
        raise NotImplementedError
    
    async def edit_content(self, project_id: UUID, edits: Dict[str, Any]) -> Dict[str, Any]:
        """Edit content of this type"""
        raise NotImplementedError
    
    async def render_preview(self, project_id: UUID) -> str:
        """Generate preview URL for content"""
        raise NotImplementedError


class BlogPostHandler(ContentTypeHandler):
    """Handler for blog post creation"""
    
    async def create_content(self, project_id: UUID, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a blog post"""
        topic = config.get("topic", "")
        length = config.get("length", "medium")
        tone = config.get("tone", "professional")
        provider = AIProvider(config.get("ai_provider", "openai"))
        
        # Generate blog post using AI
        blog_content = await self.ai_generator.generate_blog_post(
            topic=topic,
            length=length,
            tone=tone,
            provider=provider
        )
        
        return {
            "type": "blog_post",
            "content": blog_content,
            "status": "ready"
        }
    
    async def edit_content(self, project_id: UUID, edits: Dict[str, Any]) -> Dict[str, Any]:
        """Edit blog post (title, body, etc.)"""
        return {
            "type": "blog_post",
            "edits_applied": edits,
            "status": "updated"
        }
    
    async def render_preview(self, project_id: UUID) -> str:
        """Generate preview URL"""
        return f"/preview/blog/{project_id}"


class CarouselHandler(ContentTypeHandler):
    """Handler for carousel creation"""
    
    async def create_content(self, project_id: UUID, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a carousel"""
        prompt = config.get("prompt", "")
        slide_count = config.get("slide_count", 5)
        style = config.get("style", "modern")
        use_ai = config.get("use_ai", False)
        provider = AIProvider(config.get("ai_provider", "stability"))
        
        if use_ai:
            # Generate carousel images using AI
            images = await self.ai_generator.generate_carousel_images(
                prompt=prompt,
                slide_count=slide_count,
                style=style,
                provider=provider
            )
            
            return {
                "type": "ai_generated_carousel",
                "slides": images,
                "status": "ready"
            }
        else:
            # Manual carousel (user uploads images)
            return {
                "type": "carousel",
                "slides": [],
                "status": "draft"
            }
    
    async def edit_content(self, project_id: UUID, edits: Dict[str, Any]) -> Dict[str, Any]:
        """Edit carousel (reorder slides, change text, etc.)"""
        return {
            "type": "carousel",
            "edits_applied": edits,
            "status": "updated"
        }
    
    async def render_preview(self, project_id: UUID) -> str:
        """Generate preview URL"""
        return f"/preview/carousel/{project_id}"


class WordsOnVideoHandler(ContentTypeHandler):
    """Handler for words-on-video content"""
    
    async def create_content(self, project_id: UUID, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create words-on-video content"""
        video_url = config.get("video_url")
        text_overlays = config.get("text_overlays", [])
        style = config.get("style", "bold")
        
        # Generate text overlay configurations
        processed_overlays = []
        for overlay in text_overlays:
            text_config = await self.ai_generator.generate_text_overlay(
                base_text=overlay.get("text", ""),
                style=style,
                font_size=overlay.get("font_size", 48)
            )
            text_config.update({
                "start_time": overlay.get("start_time", 0),
                "end_time": overlay.get("end_time", 5),
                "position": overlay.get("position", "center")
            })
            processed_overlays.append(text_config)
        
        return {
            "type": "words_on_video",
            "video_url": video_url,
            "text_overlays": processed_overlays,
            "status": "ready"
        }
    
    async def edit_content(self, project_id: UUID, edits: Dict[str, Any]) -> Dict[str, Any]:
        """Edit words-on-video (change text, timing, position)"""
        return {
            "type": "words_on_video",
            "edits_applied": edits,
            "status": "updated"
        }
    
    async def render_preview(self, project_id: UUID) -> str:
        """Generate preview URL"""
        return f"/preview/words-on-video/{project_id}"


class BrollWithTextHandler(ContentTypeHandler):
    """Handler for B-roll with text overlay"""
    
    async def create_content(self, project_id: UUID, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create B-roll video with text overlay"""
        broll_video_url = config.get("broll_video_url")
        music_url = config.get("music_url")
        text_overlay = config.get("text_overlay", "")
        theme = config.get("theme", "minimal")
        
        return {
            "type": "broll_with_text",
            "broll_video_url": broll_video_url,
            "music_url": music_url,
            "text_overlay": text_overlay,
            "theme": theme,
            "status": "ready"
        }
    
    async def edit_content(self, project_id: UUID, edits: Dict[str, Any]) -> Dict[str, Any]:
        """Edit B-roll content"""
        return {
            "type": "broll_with_text",
            "edits_applied": edits,
            "status": "updated"
        }
    
    async def render_preview(self, project_id: UUID) -> str:
        """Generate preview URL"""
        return f"/preview/broll/{project_id}"


class AIVideoHandler(ContentTypeHandler):
    """Handler for AI-generated video"""
    
    async def create_content(self, project_id: UUID, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create AI-generated video"""
        prompt = config.get("prompt", "")
        duration = config.get("duration", 15)
        style = config.get("style", "cinematic")
        provider = AIProvider(config.get("ai_provider", "runway"))
        
        # Generate video using AI
        video_result = await self.ai_generator.generate_video(
            prompt=prompt,
            duration=duration,
            style=style,
            provider=provider
        )
        
        return {
            "type": "ai_generated_video",
            "video": video_result,
            "status": "ready"
        }
    
    async def edit_content(self, project_id: UUID, edits: Dict[str, Any]) -> Dict[str, Any]:
        """Edit AI video (regenerate with new prompt, etc.)"""
        return {
            "type": "ai_generated_video",
            "edits_applied": edits,
            "status": "updated"
        }
    
    async def render_preview(self, project_id: UUID) -> str:
        """Generate preview URL"""
        return f"/preview/ai-video/{project_id}"


def get_content_handler(content_type: str, db: AsyncSession) -> ContentTypeHandler:
    """Get appropriate handler for content type"""
    handlers = {
        "blog_post": BlogPostHandler,
        "carousel": CarouselHandler,
        "ai_generated_carousel": CarouselHandler,
        "words_on_video": WordsOnVideoHandler,
        "broll_with_text": BrollWithTextHandler,
        "ai_generated_video": AIVideoHandler,
        "video": WordsOnVideoHandler,  # Default video handler
    }
    
    handler_class = handlers.get(content_type, ContentTypeHandler)
    return handler_class(db)






