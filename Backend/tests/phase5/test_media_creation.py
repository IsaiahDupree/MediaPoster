"""
Tests for Phase 5: Media Creation System
Tests various content type creation, editing, and AI generation
Uses REAL database connections
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import uuid
from datetime import datetime

from main import app
from services.media_creation_service import MediaCreationService
from services.content_type_handlers import get_content_handler
from database.models import MediaCreationProject


class TestMediaCreationAPI:
    """Test media creation API endpoints"""
    
    def test_get_content_types(self, client):
        """Test getting list of content types"""
        response = client.get("/api/media-creation/content-types")
        assert response.status_code == 200
        data = response.json()
        
        assert "content_types" in data
        assert isinstance(data["content_types"], list)
        assert len(data["content_types"]) > 0
        
        # Check for expected content types
        type_ids = [t["id"] for t in data["content_types"]]
        assert "blog_post" in type_ids
        assert "carousel" in type_ids
        assert "words_on_video" in type_ids
    
    @pytest.mark.asyncio
    async def test_create_project(self, client, db_session, clean_db):
        """Test creating a media project with REAL database"""
        payload = {
            "project_name": "Test Blog Post",
            "content_type": "blog_post"
        }
        response = client.post("/api/media-creation/projects", json=payload)
        assert response.status_code in [200, 201]
        
        data = response.json()
        assert "id" in data
        assert data["project_name"] == "Test Blog Post"
        assert data["content_type"] == "blog_post"
        
        # Verify it was saved to database
        from sqlalchemy import select
        result = await db_session.execute(
            select(MediaCreationProject).where(MediaCreationProject.id == uuid.UUID(data["id"]))
        )
        project = result.scalar_one_or_none()
        assert project is not None
        assert project.project_name == "Test Blog Post"
    
    @pytest.mark.asyncio
    async def test_get_projects(self, client, db_session, clean_db):
        """Test getting user projects with REAL database"""
        # Create test projects
        projects = [
            MediaCreationProject(
                id=uuid.uuid4(),
                user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                project_name="Project 1",
                content_type="blog_post",
                status="draft"
            ),
            MediaCreationProject(
                id=uuid.uuid4(),
                user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
                project_name="Project 2",
                content_type="carousel",
                status="ready"
            )
        ]
        for project in projects:
            db_session.add(project)
        await db_session.commit()
        
        response = client.get("/api/media-creation/projects")
        assert response.status_code == 200
        
        data = response.json()
        assert "projects" in data
        assert isinstance(data["projects"], list)
        assert len(data["projects"]) >= 2
    
    @pytest.mark.asyncio
    async def test_get_project(self, client, db_session, clean_db):
        """Test getting a specific project with REAL database"""
        # Create test project
        test_project = MediaCreationProject(
            id=uuid.uuid4(),
            user_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            project_name="Test Project",
            content_type="carousel",
            content_data={"test": "data"},
            status="draft"
        )
        db_session.add(test_project)
        await db_session.commit()
        
        project_id = str(test_project.id)
        
        # Get the project
        response = client.get(f"/api/media-creation/projects/{project_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == project_id
        assert data["project_name"] == "Test Project"
        assert "content_data" in data


class TestContentTypeHandlers:
    """Test content type handlers"""
    
    @pytest.mark.asyncio
    async def test_blog_post_handler(self, mock_db):
        """Test blog post creation"""
        from services.content_type_handlers import BlogPostHandler
        
        handler = BlogPostHandler(mock_db)
        project_id = uuid.uuid4()
        
        config = {
            "topic": "AI in content creation",
            "length": "medium",
            "tone": "professional",
            "ai_provider": "openai"
        }
        
        with patch.object(handler.ai_generator, 'generate_blog_post', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {
                "title": "AI in Content Creation",
                "body": "This is a blog post...",
                "summary": "Key insights",
                "keywords": ["AI", "content"]
            }
            
            result = await handler.create_content(project_id, config)
            assert result["type"] == "blog_post"
            assert "content" in result
    
    @pytest.mark.asyncio
    async def test_carousel_handler(self, mock_db):
        """Test carousel creation"""
        from services.content_type_handlers import CarouselHandler
        
        handler = CarouselHandler(mock_db)
        project_id = uuid.uuid4()
        
        config = {
            "prompt": "Modern tech carousel",
            "slide_count": 5,
            "style": "modern",
            "use_ai": True,
            "ai_provider": "stability"
        }
        
        with patch.object(handler.ai_generator, 'generate_carousel_images', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = [
                {"url": "https://example.com/slide1.png", "slide_number": 1},
                {"url": "https://example.com/slide2.png", "slide_number": 2}
            ]
            
            result = await handler.create_content(project_id, config)
            assert result["type"] == "ai_generated_carousel"
            assert "slides" in result
    
    @pytest.mark.asyncio
    async def test_words_on_video_handler(self, mock_db):
        """Test words-on-video creation"""
        from services.content_type_handlers import WordsOnVideoHandler
        
        handler = WordsOnVideoHandler(mock_db)
        project_id = uuid.uuid4()
        
        config = {
            "video_url": "https://example.com/video.mp4",
            "text_overlays": [
                {"text": "Hello", "start_time": 0, "end_time": 3, "position": "center"}
            ],
            "style": "bold"
        }
        
        with patch.object(handler.ai_generator, 'generate_text_overlay', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {
                "text": "Hello",
                "style": "bold",
                "font_size": 48,
                "position": "center"
            }
            
            result = await handler.create_content(project_id, config)
            assert result["type"] == "words_on_video"
            assert "text_overlays" in result
    
    @pytest.mark.asyncio
    async def test_ai_video_handler(self, mock_db):
        """Test AI video generation"""
        from services.content_type_handlers import AIVideoHandler
        
        handler = AIVideoHandler(mock_db)
        project_id = uuid.uuid4()
        
        config = {
            "prompt": "A cinematic sunset over mountains",
            "duration": 15,
            "style": "cinematic",
            "ai_provider": "runway"
        }
        
        with patch.object(handler.ai_generator, 'generate_video', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {
                "url": "https://example.com/video.mp4",
                "duration": 15,
                "prompt": config["prompt"],
                "style": "cinematic",
                "provider": "runway"
            }
            
            result = await handler.create_content(project_id, config)
            assert result["type"] == "ai_generated_video"
            assert "video" in result


class TestAIContentGenerator:
    """Test AI content generator"""
    
    @pytest.mark.asyncio
    async def test_generate_blog_post(self):
        """Test blog post generation"""
        from services.ai_content_generator import AIContentGenerator, AIProvider
        
        generator = AIContentGenerator()
        
        with patch.object(generator, '_generate_with_openai', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {
                "title": "Test Blog",
                "body": "Content...",
                "provider": "openai"
            }
            
            result = await generator.generate_blog_post(
                topic="Test topic",
                length="medium",
                tone="professional",
                provider=AIProvider.OPENAI
            )
            assert "title" in result
            assert "body" in result
    
    @pytest.mark.asyncio
    async def test_generate_carousel_images(self):
        """Test carousel image generation"""
        from services.ai_content_generator import AIContentGenerator, AIProvider
        
        generator = AIContentGenerator()
        
        with patch.object(generator, '_generate_image_stability', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "https://example.com/image.png"
            
            result = await generator.generate_carousel_images(
                prompt="Modern design",
                slide_count=3,
                style="modern",
                provider=AIProvider.STABILITY
            )
            assert isinstance(result, list)
            assert len(result) == 3
            assert all("url" in slide for slide in result)
    
    @pytest.mark.asyncio
    async def test_generate_video(self):
        """Test video generation"""
        from services.ai_content_generator import AIContentGenerator, AIProvider
        
        generator = AIContentGenerator()
        
        with patch.object(generator, '_generate_video_runway', new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = {
                "url": "https://example.com/video.mp4",
                "duration": 15,
                "provider": "runway"
            }
            
            result = await generator.generate_video(
                prompt="Cinematic scene",
                duration=15,
                style="cinematic",
                provider=AIProvider.RUNWAY
            )
            assert "url" in result
            assert result["duration"] == 15

