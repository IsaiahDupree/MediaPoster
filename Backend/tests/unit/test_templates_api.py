"""
Content Templates API Tests
============================
Tests for Template CRUD API endpoints (TPL-007, TPL-006, TPL-008)

Test Coverage:
- TPL-001: ContentTemplate model validation
- TPL-006: Template variable substitution
- TPL-007: CRUD API operations
- TPL-008: Template forking
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
import os
from uuid import uuid4

from database.models import Base, ContentTemplate, Brand
from database.connection import get_db
from main import app


# Test database URL
TEST_DB_URL = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres_test")


@pytest_asyncio.fixture
async def test_db():
    """Create test database session"""
    engine = create_async_engine(TEST_DB_URL, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Create session maker
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db):
    """Create test client with database override"""
    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_template(test_db):
    """Create a sample template for testing"""
    template = ContentTemplate(
        name="Test Template",
        description="A test template",
        template_type="post",
        prompt_text="Write about {topic} for {audience} focusing on {pain}",
        required_variables=["topic", "audience", "pain"],
        fate_focus=0.3,
        fate_authority=0.3,
        fate_tribe=0.2,
        fate_emotion=0.2,
        awareness_level="problem_aware",
        cta_strength="soft",
        is_active=True,
        created_by="test"
    )

    test_db.add(template)
    await test_db.commit()
    await test_db.refresh(template)

    return template


class TestTemplateModel:
    """Test TPL-001: ContentTemplate model"""

    @pytest.mark.asyncio
    async def test_template_creation(self, test_db):
        """Test creating a content template"""
        template = ContentTemplate(
            name="Symptom Mirror",
            description="Mirrors pain points with empathy",
            template_type="post",
            prompt_text="Write about {pain}",
            required_variables=["pain"],
            fate_focus=0.2,
            fate_authority=0.15,
            fate_tribe=0.4,
            fate_emotion=0.25,
            awareness_level="problem_aware",
            cta_strength="none",
            is_active=True,
            created_by="system"
        )

        test_db.add(template)
        await test_db.commit()
        await test_db.refresh(template)

        assert template.id is not None
        assert template.name == "Symptom Mirror"
        assert template.awareness_level == "problem_aware"
        assert template.fate_focus + template.fate_authority + template.fate_tribe + template.fate_emotion == 1.0

    @pytest.mark.asyncio
    async def test_template_fate_weights(self, test_db):
        """Test FATE weights sum to 1.0"""
        template = ContentTemplate(
            name="Test FATE",
            prompt_text="Test",
            fate_focus=0.25,
            fate_authority=0.25,
            fate_tribe=0.25,
            fate_emotion=0.25,
            awareness_level="solution_aware",
            cta_strength="soft",
            created_by="test"
        )

        total = template.fate_focus + template.fate_authority + template.fate_tribe + template.fate_emotion

        assert abs(total - 1.0) < 0.01  # Within tolerance


class TestTemplateListAPI:
    """Test TPL-007: Template listing and filtering"""

    @pytest.mark.asyncio
    async def test_list_templates(self, client, sample_template):
        """Test GET /api/templates"""
        response = client.get("/api/templates")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["data"]) > 0
        assert data["data"][0]["name"] == "Test Template"

    @pytest.mark.asyncio
    async def test_filter_by_awareness_level(self, client, sample_template):
        """Test filtering templates by awareness level"""
        response = client.get("/api/templates?awareness_level=problem_aware")

        assert response.status_code == 200
        data = response.json()

        assert all(t["awareness_level"] == "problem_aware" for t in data["data"])

    @pytest.mark.asyncio
    async def test_filter_by_template_type(self, client, sample_template):
        """Test filtering templates by type"""
        response = client.get("/api/templates?template_type=post")

        assert response.status_code == 200
        data = response.json()

        assert all(t["template_type"] == "post" for t in data["data"])

    @pytest.mark.asyncio
    async def test_pagination(self, client, sample_template):
        """Test pagination parameters"""
        response = client.get("/api/templates?limit=5&offset=0")

        assert response.status_code == 200
        data = response.json()

        assert len(data["data"]) <= 5
        assert data["limit"] == 5
        assert data["offset"] == 0


class TestTemplateGetAPI:
    """Test TPL-007: Get specific template"""

    @pytest.mark.asyncio
    async def test_get_template(self, client, sample_template):
        """Test GET /api/templates/{id}"""
        response = client.get(f"/api/templates/{sample_template.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["id"] == str(sample_template.id)
        assert data["data"]["name"] == "Test Template"
        assert "fate_weights" in data["data"]
        assert data["data"]["fate_weights"]["F"] == 0.3

    @pytest.mark.asyncio
    async def test_get_nonexistent_template(self, client):
        """Test getting a template that doesn't exist"""
        fake_id = uuid4()
        response = client.get(f"/api/templates/{fake_id}")

        assert response.status_code == 404


class TestTemplateCreateAPI:
    """Test TPL-007: Create template"""

    @pytest.mark.asyncio
    async def test_create_template(self, client):
        """Test POST /api/templates"""
        request = {
            "name": "New Template",
            "description": "A new test template",
            "template_type": "post",
            "prompt_text": "Write about {topic}",
            "fate_weights": {
                "F": 0.3,
                "A": 0.3,
                "T": 0.2,
                "E": 0.2
            },
            "awareness_level": "solution_aware",
            "cta_strength": "soft"
        }

        response = client.post("/api/templates/", json=request)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "id" in data["data"]
        assert data["data"]["name"] == "New Template"
        assert data["data"]["required_variables"] == ["topic"]

    @pytest.mark.asyncio
    async def test_create_template_validation_fails(self, client):
        """Test creating template with invalid FATE weights"""
        request = {
            "name": "Invalid Template",
            "prompt_text": "Test",
            "fate_weights": {
                "F": 0.5,  # Sum > 1.0
                "A": 0.3,
                "T": 0.3,
                "E": 0.3
            },
            "awareness_level": "problem_aware",
            "cta_strength": "none"
        }

        response = client.post("/api/templates/", json=request)

        # Should fail validation
        assert response.status_code == 422 or response.status_code == 400

    @pytest.mark.asyncio
    async def test_create_template_extracts_variables(self, client):
        """Test that template creation extracts variables correctly"""
        request = {
            "name": "Variable Test",
            "prompt_text": "Write about {topic} for {audience} with {tone}",
            "fate_weights": {"F": 0.25, "A": 0.25, "T": 0.25, "E": 0.25},
            "awareness_level": "problem_aware",
            "cta_strength": "soft"
        }

        response = client.post("/api/templates/", json=request)

        assert response.status_code == 200
        data = response.json()

        required_vars = data["data"]["required_variables"]
        assert set(required_vars) == {"topic", "audience", "tone"}


class TestTemplateUpdateAPI:
    """Test TPL-007: Update template"""

    @pytest.mark.asyncio
    async def test_update_template(self, client, sample_template):
        """Test PUT /api/templates/{id}"""
        request = {
            "name": "Updated Template Name",
            "description": "Updated description"
        }

        response = client.put(f"/api/templates/{sample_template.id}", json=request)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["name"] == "Updated Template Name"

    @pytest.mark.asyncio
    async def test_update_template_prompt_text(self, client, sample_template):
        """Test updating prompt text re-extracts variables"""
        request = {
            "prompt_text": "New prompt with {new_variable}"
        }

        response = client.put(f"/api/templates/{sample_template.id}", json=request)

        assert response.status_code == 200

        # Get template to verify variables updated
        get_response = client.get(f"/api/templates/{sample_template.id}")
        data = get_response.json()

        assert "new_variable" in data["data"]["required_variables"]


class TestTemplateDeleteAPI:
    """Test TPL-007: Delete template"""

    @pytest.mark.asyncio
    async def test_delete_template(self, client, sample_template):
        """Test DELETE /api/templates/{id} (soft delete)"""
        response = client.delete(f"/api/templates/{sample_template.id}")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True

        # Verify it's soft deleted (is_active = False)
        get_response = client.get(f"/api/templates/{sample_template.id}")
        template_data = get_response.json()

        # Template still exists but is inactive
        assert template_data["data"]["is_active"] is False


class TestTemplateRenderAPI:
    """Test TPL-006: Template variable substitution"""

    @pytest.mark.asyncio
    async def test_render_template(self, client, sample_template):
        """Test POST /api/templates/render"""
        request = {
            "template_id": str(sample_template.id),
            "variables": {
                "topic": "AI marketing",
                "audience": "B2B SaaS founders",
                "pain": "low conversion rates"
            }
        }

        response = client.post("/api/templates/render", json=request)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "rendered_text" in data["data"]
        assert "AI marketing" in data["data"]["rendered_text"]
        assert "B2B SaaS founders" in data["data"]["rendered_text"]
        assert "low conversion rates" in data["data"]["rendered_text"]

    @pytest.mark.asyncio
    async def test_render_with_missing_variables(self, client, sample_template):
        """Test rendering with missing required variables"""
        request = {
            "template_id": str(sample_template.id),
            "variables": {
                "topic": "AI marketing"
                # Missing 'audience' and 'pain'
            }
        }

        response = client.post("/api/templates/render", json=request)

        assert response.status_code == 400
        data = response.json()

        assert "missing_variables" in data["detail"]

    @pytest.mark.asyncio
    async def test_render_nonexistent_template(self, client):
        """Test rendering a template that doesn't exist"""
        fake_id = uuid4()
        request = {
            "template_id": str(fake_id),
            "variables": {"topic": "test"}
        }

        response = client.post("/api/templates/render", json=request)

        assert response.status_code == 404


class TestTemplateForkAPI:
    """Test TPL-008: Template forking"""

    @pytest.mark.asyncio
    async def test_fork_template(self, client, sample_template):
        """Test POST /api/templates/{id}/fork"""
        request = {
            "new_name": "Forked Template",
            "modifications": "Modified for different audience"
        }

        response = client.post(f"/api/templates/{sample_template.id}/fork", json=request)

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["forked_name"] == "Forked Template"
        assert data["data"]["original_id"] == str(sample_template.id)

        # Verify forked template exists and has same content
        forked_id = data["data"]["forked_id"]
        get_response = client.get(f"/api/templates/{forked_id}")
        forked_data = get_response.json()

        assert forked_data["data"]["name"] == "Forked Template"
        assert forked_data["data"]["prompt_text"] == sample_template.prompt_text
        assert forked_data["data"]["fate_weights"]["F"] == 0.3

    @pytest.mark.asyncio
    async def test_fork_preserves_original(self, client, sample_template):
        """Test that forking doesn't modify the original"""
        original_name = sample_template.name

        request = {
            "new_name": "Forked Copy"
        }

        response = client.post(f"/api/templates/{sample_template.id}/fork", json=request)

        assert response.status_code == 200

        # Verify original is unchanged
        get_response = client.get(f"/api/templates/{sample_template.id}")
        original_data = get_response.json()

        assert original_data["data"]["name"] == original_name


class TestTemplateStatsAPI:
    """Test template statistics endpoint"""

    @pytest.mark.asyncio
    async def test_get_template_stats(self, client, sample_template):
        """Test GET /api/templates/stats/overview"""
        response = client.get("/api/templates/stats/overview")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "total_templates" in data["data"]
        assert "by_awareness_level" in data["data"]
        assert data["data"]["total_templates"] > 0


class TestVariableExtraction:
    """Test variable extraction from prompt text"""

    def test_extract_simple_variables(self):
        """Test extracting simple variables"""
        from services.template_validator import TemplateValidator

        validator = TemplateValidator()
        prompt = "Write about {topic} for {audience}"

        variables = validator.extract_variables(prompt)

        assert variables == {"topic", "audience"}

    def test_extract_complex_variables(self):
        """Test extracting variables with underscores and numbers"""
        from services.template_validator import TemplateValidator

        validator = TemplateValidator()
        prompt = "Focus on {pain_point_1} and {solution_2} for {target_audience}"

        variables = validator.extract_variables(prompt)

        assert variables == {"pain_point_1", "solution_2", "target_audience"}

    def test_no_variables(self):
        """Test text with no variables"""
        from services.template_validator import TemplateValidator

        validator = TemplateValidator()
        prompt = "This is a plain text template"

        variables = validator.extract_variables(prompt)

        assert len(variables) == 0


class TestFATEValidation:
    """Test FATE weight validation"""

    def test_valid_fate_weights(self):
        """Test valid FATE weights"""
        from services.template_validator import TemplateValidator

        validator = TemplateValidator()
        weights = {"F": 0.3, "A": 0.3, "T": 0.2, "E": 0.2}

        is_valid, errors = validator.validate_fate_weights(weights)

        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_fate_sum(self):
        """Test FATE weights that don't sum to 1.0"""
        from services.template_validator import TemplateValidator

        validator = TemplateValidator()
        weights = {"F": 0.5, "A": 0.3, "T": 0.2, "E": 0.2}  # Sum = 1.2

        is_valid, errors = validator.validate_fate_weights(weights)

        assert is_valid is False
        assert any("sum" in error.lower() for error in errors)

    def test_missing_fate_keys(self):
        """Test FATE weights missing required keys"""
        from services.template_validator import TemplateValidator

        validator = TemplateValidator()
        weights = {"F": 0.5, "A": 0.3, "T": 0.2}  # Missing E

        is_valid, errors = validator.validate_fate_weights(weights)

        assert is_valid is False
        assert any("Missing" in error for error in errors)
