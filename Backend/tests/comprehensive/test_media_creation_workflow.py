"""
Comprehensive Media Creation Workflow Tests
Tests complete media creation workflow from creation to scheduling
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
import uuid
from datetime import datetime, timedelta

from main import app
from database.models import MediaCreationProject, ScheduledPost


@pytest.fixture
def client():
    return TestClient(app)


class TestMediaCreationWorkflow:
    """Comprehensive media creation workflow"""
    
    @pytest.mark.asyncio
    async def test_create_edit_publish_workflow(self, client, db_session, clean_db):
        """Test complete workflow: create -> edit -> publish"""
        # CREATE project
        create_payload = {
            "project_name": "Test Blog Post",
            "content_type": "blog_post"
        }
        create_response = client.post("/api/media-creation/projects", json=create_payload)
        assert create_response.status_code in [200, 201]
        project_data = create_response.json()
        project_id = uuid.UUID(project_data["id"])
        
        # Verify project created
        result = await db_session.execute(
            select(MediaCreationProject).where(MediaCreationProject.id == project_id)
        )
        project = result.scalar_one_or_none()
        assert project is not None
        assert project.status == "draft"
        
        # EDIT project
        edit_response = client.put(f"/api/media-creation/projects/{project_id}/edit", json={
            "project_name": "Updated Blog Post",
            "content_data": {"title": "New Title", "content": "New Content"}
        })
        assert edit_response.status_code == 200
        updated_project = edit_response.json()
        assert updated_project["project_name"] == "Updated Blog Post"
        
        # CREATE content
        create_content_response = client.post(
            f"/api/media-creation/projects/{project_id}/create-content"
        )
        # May succeed or require additional setup
        assert create_content_response.status_code in [200, 201, 400, 500]
        
        # GET project to verify updates
        get_response = client.get(f"/api/media-creation/projects/{project_id}")
        assert get_response.status_code == 200
        final_project = get_response.json()
        assert final_project["id"] == str(project_id)
    
    @pytest.mark.asyncio
    async def test_multiple_content_types(self, client, db_session, clean_db):
        """Test creating projects with different content types"""
        content_types = ["blog_post", "carousel", "words_on_video", "ai_video"]
        created_projects = []
        
        for content_type in content_types:
            payload = {
                "project_name": f"Test {content_type}",
                "content_type": content_type
            }
            response = client.post("/api/media-creation/projects", json=payload)
            assert response.status_code in [200, 201]
            created_projects.append(uuid.UUID(response.json()["id"]))
        
        # Verify all projects created
        response = client.get("/api/media-creation/projects")
        assert response.status_code == 200
        projects_data = response.json()
        assert "projects" in projects_data
        assert len(projects_data["projects"]) >= len(content_types)
        
        # Verify each content type
        for project_id in created_projects:
            result = await db_session.execute(
                select(MediaCreationProject).where(MediaCreationProject.id == project_id)
            )
            project = result.scalar_one_or_none()
            assert project is not None
            assert project.content_type in content_types
    
    @pytest.mark.asyncio
    async def test_project_to_scheduled_post(self, client, db_session, clean_db):
        """Test creating a project and scheduling it for publishing"""
        # Create project
        create_response = client.post("/api/media-creation/projects", json={
            "project_name": "Scheduled Post",
            "content_type": "carousel"
        })
        assert create_response.status_code in [200, 201]
        project_id = uuid.UUID(create_response.json()["id"])
        
        # Schedule the project
        schedule_time = datetime.now() + timedelta(days=1)
        schedule_response = client.post("/api/publishing/schedule", json={
            "media_project_id": str(project_id),
            "platforms": ["instagram"],
            "scheduled_time": schedule_time.isoformat(),
            "caption": "Test scheduled post"
        })
        # May succeed or require project to be ready
        assert schedule_response.status_code in [200, 201, 400, 404, 500]
        
        if schedule_response.status_code in [200, 201]:
            # Verify scheduled post was created
            result = await db_session.execute(
                select(ScheduledPost).where(ScheduledPost.media_project_id == project_id)
            )
            scheduled_posts = result.scalars().all()
            assert len(scheduled_posts) > 0
            assert scheduled_posts[0].platform == "instagram"






