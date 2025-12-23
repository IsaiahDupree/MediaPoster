"""
Video Orchestrator Models Tests
===============================
Unit tests for video orchestrator data models and schemas.

Run tests:
    pytest tests/test_video_orchestrator_models.py -v
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# ENUM TESTS
# =============================================================================

class TestEnums:
    """Test enum definitions."""
    
    def test_provider_name_values(self):
        """Test ProviderName enum values."""
        from services.video_orchestrator.models import ProviderName
        
        assert ProviderName.SORA.value == "sora"
        assert ProviderName.RUNWAY.value == "runway"
        assert ProviderName.KLING.value == "kling"
        assert ProviderName.MOCK.value == "mock"
    
    def test_clip_run_status_values(self):
        """Test ClipRunStatus enum values."""
        from services.video_orchestrator.models import ClipRunStatus
        
        assert ClipRunStatus.QUEUED.value == "queued"
        assert ClipRunStatus.RUNNING.value == "running"
        assert ClipRunStatus.SUCCEEDED.value == "succeeded"
        assert ClipRunStatus.FAILED.value == "failed"
    
    def test_assessment_verdict_values(self):
        """Test AssessmentVerdict enum values."""
        from services.video_orchestrator.models import AssessmentVerdict
        
        assert AssessmentVerdict.PASS.value == "pass"
        assert AssessmentVerdict.FAIL.value == "fail"
        assert AssessmentVerdict.NEEDS_REVIEW.value == "needs_review"
    
    def test_plan_status_values(self):
        """Test PlanStatus enum values."""
        from services.video_orchestrator.models import PlanStatus
        
        assert PlanStatus.DRAFT.value == "draft"
        assert PlanStatus.READY.value == "ready"
        assert PlanStatus.RUNNING.value == "running"
        assert PlanStatus.COMPLETED.value == "completed"
        assert PlanStatus.FAILED.value == "failed"
    
    def test_clip_state_values(self):
        """Test ClipState enum values."""
        from services.video_orchestrator.models import ClipState
        
        assert ClipState.PENDING.value == "pending"
        assert ClipState.GENERATING.value == "generating"
        assert ClipState.PASSED.value == "passed"
        assert ClipState.FAILED.value == "failed"
    
    def test_repair_strategy_values(self):
        """Test RepairStrategy enum values."""
        from services.video_orchestrator.models import RepairStrategy
        
        assert RepairStrategy.PROMPT_PATCH.value == "prompt_patch"
        assert RepairStrategy.REMIX.value == "remix"
        assert RepairStrategy.FALLBACK_PROVIDER.value == "fallback_provider"


# =============================================================================
# CONFIG MODEL TESTS
# =============================================================================

class TestNarrationConfig:
    """Test NarrationConfig model."""
    
    def test_default_creation(self):
        """Test default NarrationConfig."""
        from services.video_orchestrator.models import NarrationConfig, NarrationMode
        
        config = NarrationConfig()
        
        assert config.mode == NarrationMode.EXTERNAL_VOICEOVER
        assert config.text == ""
        assert config.speaker == "narrator"
        assert config.language == "en"
    
    def test_to_dict(self):
        """Test NarrationConfig serialization."""
        from services.video_orchestrator.models import NarrationConfig, NarrationMode
        
        config = NarrationConfig(
            mode=NarrationMode.GENERATED_IN_VIDEO,
            text="Hello world",
            speaker="host",
            language="es"
        )
        
        data = config.to_dict()
        
        assert data["mode"] == "generated_in_video"
        assert data["text"] == "Hello world"
        assert data["speaker"] == "host"
        assert data["language"] == "es"
    
    def test_from_dict(self):
        """Test NarrationConfig deserialization."""
        from services.video_orchestrator.models import NarrationConfig, NarrationMode
        
        data = {
            "mode": "external_voiceover",
            "text": "Test narration",
            "speaker": "narrator",
            "language": "en"
        }
        
        config = NarrationConfig.from_dict(data)
        
        assert config.mode == NarrationMode.EXTERNAL_VOICEOVER
        assert config.text == "Test narration"


class TestVisualIntent:
    """Test VisualIntent model."""
    
    def test_default_creation(self):
        """Test default VisualIntent."""
        from services.video_orchestrator.models import VisualIntent
        
        intent = VisualIntent()
        
        assert intent.prompt == ""
        assert intent.must_include == []
        assert intent.must_avoid == []
    
    def test_to_dict(self):
        """Test VisualIntent serialization."""
        from services.video_orchestrator.models import VisualIntent
        
        intent = VisualIntent(
            prompt="A person walking in park",
            must_include=["person", "park"],
            must_avoid=["violence"],
            camera="wide shot",
            setting="outdoor"
        )
        
        data = intent.to_dict()
        
        assert data["prompt"] == "A person walking in park"
        assert "person" in data["must_include"]
        assert "violence" in data["must_avoid"]
    
    def test_from_dict(self):
        """Test VisualIntent deserialization."""
        from services.video_orchestrator.models import VisualIntent
        
        data = {
            "prompt": "Test prompt",
            "must_include": ["element1"],
            "must_avoid": ["bad_element"],
            "camera": "close-up"
        }
        
        intent = VisualIntent.from_dict(data)
        
        assert intent.prompt == "Test prompt"
        assert "element1" in intent.must_include
        assert intent.camera == "close-up"


class TestProviderHints:
    """Test ProviderHints model."""
    
    def test_default_creation(self):
        """Test default ProviderHints."""
        from services.video_orchestrator.models import ProviderHints, ProviderName
        
        hints = ProviderHints()
        
        assert hints.primary_provider == ProviderName.SORA
        assert hints.model == "sora-2"
        assert hints.size == "1280x720"
    
    def test_to_dict(self):
        """Test ProviderHints serialization."""
        from services.video_orchestrator.models import ProviderHints, ProviderName
        
        hints = ProviderHints(
            primary_provider=ProviderName.RUNWAY,
            model="gen-3",
            size="1920x1080",
            seed=12345
        )
        
        data = hints.to_dict()
        
        assert data["primary_provider"] == "runway"
        assert data["model"] == "gen-3"
        assert data["seed"] == 12345
    
    def test_from_dict(self):
        """Test ProviderHints deserialization."""
        from services.video_orchestrator.models import ProviderHints, ProviderName
        
        data = {
            "primary_provider": "sora",
            "model": "sora-2-pro",
            "size": "720x1280"
        }
        
        hints = ProviderHints.from_dict(data)
        
        assert hints.primary_provider == ProviderName.SORA
        assert hints.model == "sora-2-pro"


class TestAcceptanceCriteria:
    """Test AcceptanceCriteria model."""
    
    def test_default_creation(self):
        """Test default AcceptanceCriteria."""
        from services.video_orchestrator.models import AcceptanceCriteria
        
        criteria = AcceptanceCriteria.default()
        
        assert criteria.score_threshold == 0.8
        assert len(criteria.checks) == 4
    
    def test_to_dict(self):
        """Test AcceptanceCriteria serialization."""
        from services.video_orchestrator.models import AcceptanceCriteria, AcceptanceCheck, CheckType
        
        criteria = AcceptanceCriteria(
            score_threshold=0.75,
            checks=[
                AcceptanceCheck(type=CheckType.VISUAL_REQUIREMENTS, weight=0.5),
                AcceptanceCheck(type=CheckType.DURATION_OK, weight=0.5)
            ]
        )
        
        data = criteria.to_dict()
        
        assert data["score_threshold"] == 0.75
        assert len(data["checks"]) == 2
    
    def test_from_dict(self):
        """Test AcceptanceCriteria deserialization."""
        from services.video_orchestrator.models import AcceptanceCriteria
        
        data = {
            "score_threshold": 0.9,
            "checks": [
                {"type": "visual_requirements", "weight": 0.4},
                {"type": "continuity", "weight": 0.6}
            ]
        }
        
        criteria = AcceptanceCriteria.from_dict(data)
        
        assert criteria.score_threshold == 0.9
        assert len(criteria.checks) == 2


class TestPlanConstraints:
    """Test PlanConstraints model."""
    
    def test_default_creation(self):
        """Test default PlanConstraints."""
        from services.video_orchestrator.models import PlanConstraints
        
        constraints = PlanConstraints()
        
        assert constraints.max_total_seconds == 300  # 5 minutes
        assert constraints.default_clip_seconds == 8
        assert constraints.aspect_ratio == "16:9"
    
    def test_max_duration_is_5_minutes(self):
        """Test that default max is 5 minutes (300 seconds)."""
        from services.video_orchestrator.models import PlanConstraints
        
        constraints = PlanConstraints()
        
        # 5 minutes = 300 seconds
        assert constraints.max_total_seconds == 300
        assert constraints.max_total_seconds / 60 == 5
    
    def test_to_dict(self):
        """Test PlanConstraints serialization."""
        from services.video_orchestrator.models import PlanConstraints
        
        constraints = PlanConstraints(
            max_total_seconds=180,
            default_clip_seconds=12,
            aspect_ratio="9:16"
        )
        
        data = constraints.to_dict()
        
        assert data["max_total_seconds"] == 180
        assert data["default_clip_seconds"] == 12
        assert data["aspect_ratio"] == "9:16"
    
    def test_from_dict(self):
        """Test PlanConstraints deserialization."""
        from services.video_orchestrator.models import PlanConstraints
        
        data = {
            "max_total_seconds": 240,
            "default_clip_seconds": 8,
            "pacing": {"words_per_minute": 130},
            "retry_policy": {"max_attempts_per_clip": 5}
        }
        
        constraints = PlanConstraints.from_dict(data)
        
        assert constraints.max_total_seconds == 240
        assert constraints.pacing.words_per_minute == 130
        assert constraints.retry_policy.max_attempts_per_clip == 5


class TestRepairInstruction:
    """Test RepairInstruction model."""
    
    def test_prompt_patch_strategy(self):
        """Test prompt patch repair instruction."""
        from services.video_orchestrator.models import RepairInstruction, RepairStrategy
        
        instruction = RepairInstruction(
            strategy=RepairStrategy.PROMPT_PATCH,
            prompt_delta="Add more detail about the setting"
        )
        
        assert instruction.strategy == RepairStrategy.PROMPT_PATCH
        assert "detail" in instruction.prompt_delta
    
    def test_fallback_provider_strategy(self):
        """Test fallback provider repair instruction."""
        from services.video_orchestrator.models import RepairInstruction, RepairStrategy, ProviderName
        
        instruction = RepairInstruction(
            strategy=RepairStrategy.FALLBACK_PROVIDER,
            fallback_provider=ProviderName.RUNWAY
        )
        
        assert instruction.strategy == RepairStrategy.FALLBACK_PROVIDER
        assert instruction.fallback_provider == ProviderName.RUNWAY
    
    def test_to_dict(self):
        """Test RepairInstruction serialization."""
        from services.video_orchestrator.models import RepairInstruction, RepairStrategy
        
        instruction = RepairInstruction(
            strategy=RepairStrategy.REMIX,
            notes="Try with different seed"
        )
        
        data = instruction.to_dict()
        
        assert data["strategy"] == "remix"
        assert data["notes"] == "Try with different seed"


# =============================================================================
# CORE ENTITY TESTS
# =============================================================================

class TestVideoProject:
    """Test VideoProject model."""
    
    def test_creation(self):
        """Test VideoProject creation."""
        from services.video_orchestrator.models import VideoProject
        
        project = VideoProject(
            title="Test Project",
            description="A test video project",
            tags=["test", "demo"]
        )
        
        assert project.title == "Test Project"
        assert "test" in project.tags
        assert isinstance(project.id, UUID)
    
    def test_default_timestamps(self):
        """Test VideoProject has timestamps."""
        from services.video_orchestrator.models import VideoProject
        
        project = VideoProject(title="Test")
        
        assert project.created_at is not None
        assert project.updated_at is not None


class TestClipPlan:
    """Test ClipPlan model."""
    
    def test_creation(self):
        """Test ClipPlan creation."""
        from services.video_orchestrator.models import ClipPlan, PlanStatus
        
        project_id = uuid4()
        plan = ClipPlan(
            project_id=project_id,
            version="1.0.0",
            status=PlanStatus.DRAFT
        )
        
        assert plan.project_id == project_id
        assert plan.version == "1.0.0"
        assert plan.status == PlanStatus.DRAFT
    
    def test_default_constraints(self):
        """Test ClipPlan has default constraints."""
        from services.video_orchestrator.models import ClipPlan
        
        plan = ClipPlan()
        
        assert plan.constraints.max_total_seconds == 300
        assert plan.constraints.default_clip_seconds == 8


class TestClipPlanClip:
    """Test ClipPlanClip model."""
    
    def test_creation(self):
        """Test ClipPlanClip creation."""
        from services.video_orchestrator.models import ClipPlanClip, ClipState
        
        scene_id = uuid4()
        clip = ClipPlanClip(
            scene_id=scene_id,
            clip_order=0,
            target_seconds=12
        )
        
        assert clip.scene_id == scene_id
        assert clip.target_seconds == 12
        assert clip.state == ClipState.PENDING
    
    def test_default_components(self):
        """Test ClipPlanClip has default components."""
        from services.video_orchestrator.models import ClipPlanClip
        
        clip = ClipPlanClip()
        
        assert clip.narration is not None
        assert clip.visual_intent is not None
        assert clip.provider_hints is not None
        assert clip.acceptance is not None


class TestClipRun:
    """Test ClipRun model."""
    
    def test_creation(self):
        """Test ClipRun creation."""
        from services.video_orchestrator.models import ClipRun, ProviderName, ClipRunStatus
        
        clip_id = uuid4()
        run = ClipRun(
            clip_plan_clip_id=clip_id,
            provider=ProviderName.SORA,
            provider_generation_id="gen_123",
            attempt=1
        )
        
        assert run.clip_plan_clip_id == clip_id
        assert run.provider == ProviderName.SORA
        assert run.status == ClipRunStatus.QUEUED
    
    def test_status_progression(self):
        """Test ClipRun status can progress."""
        from services.video_orchestrator.models import ClipRun, ClipRunStatus
        
        run = ClipRun()
        assert run.status == ClipRunStatus.QUEUED
        
        run.status = ClipRunStatus.RUNNING
        assert run.status == ClipRunStatus.RUNNING
        
        run.status = ClipRunStatus.SUCCEEDED
        assert run.status == ClipRunStatus.SUCCEEDED


class TestAssessment:
    """Test Assessment model."""
    
    def test_pass_assessment(self):
        """Test passing assessment."""
        from services.video_orchestrator.models import Assessment, AssessmentVerdict
        
        run_id = uuid4()
        assessment = Assessment(
            clip_run_id=run_id,
            verdict=AssessmentVerdict.PASS,
            score=0.92,
            reasons=["All checks passed"]
        )
        
        assert assessment.verdict == AssessmentVerdict.PASS
        assert assessment.score == 0.92
    
    def test_fail_assessment_with_repair(self):
        """Test failing assessment with repair instruction."""
        from services.video_orchestrator.models import (
            Assessment, AssessmentVerdict, RepairInstruction, RepairStrategy
        )
        
        run_id = uuid4()
        assessment = Assessment(
            clip_run_id=run_id,
            verdict=AssessmentVerdict.FAIL,
            score=0.45,
            reasons=["Visual requirements not met", "Duration too short"],
            repair_instruction=RepairInstruction(
                strategy=RepairStrategy.PROMPT_PATCH,
                prompt_delta="Ensure the scene shows the required elements"
            )
        )
        
        assert assessment.verdict == AssessmentVerdict.FAIL
        assert assessment.repair_instruction is not None
        assert assessment.repair_instruction.strategy == RepairStrategy.PROMPT_PATCH


# =============================================================================
# SCHEMA VALIDATION TESTS
# =============================================================================

class TestSchemaValidation:
    """Test Pydantic schema validation."""
    
    def test_create_project_request_valid(self):
        """Test valid CreateProjectRequest."""
        from services.video_orchestrator.schemas import CreateProjectRequest
        
        request = CreateProjectRequest(
            title="My Video",
            description="Test video",
            tags=["demo"]
        )
        
        assert request.title == "My Video"
    
    def test_create_project_request_title_required(self):
        """Test CreateProjectRequest requires title."""
        from services.video_orchestrator.schemas import CreateProjectRequest
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            CreateProjectRequest()
    
    def test_constraints_config_max_duration(self):
        """Test ConstraintsConfig max_total_seconds limit."""
        from services.video_orchestrator.schemas import ConstraintsConfig
        from pydantic import ValidationError
        
        # Valid: 300 seconds (5 min)
        config = ConstraintsConfig(max_total_seconds=300)
        assert config.max_total_seconds == 300
        
        # Invalid: > 300 seconds
        with pytest.raises(ValidationError):
            ConstraintsConfig(max_total_seconds=400)
    
    def test_constraints_config_clip_seconds_range(self):
        """Test ConstraintsConfig clip seconds range (4-12)."""
        from services.video_orchestrator.schemas import ConstraintsConfig
        from pydantic import ValidationError
        
        # Valid range
        config = ConstraintsConfig(default_clip_seconds=8)
        assert config.default_clip_seconds == 8
        
        # Invalid: < 4
        with pytest.raises(ValidationError):
            ConstraintsConfig(default_clip_seconds=2)
        
        # Invalid: > 12
        with pytest.raises(ValidationError):
            ConstraintsConfig(default_clip_seconds=20)
    
    def test_sora_generate_request_valid(self):
        """Test valid SoraGenerateRequest."""
        from services.video_orchestrator.schemas import SoraGenerateRequest
        
        request = SoraGenerateRequest(
            prompt="A cat playing piano",
            model="sora-2",
            size="1280x720",
            seconds=8
        )
        
        assert request.prompt == "A cat playing piano"
        assert request.seconds == 8
    
    def test_sora_generate_request_model_validation(self):
        """Test SoraGenerateRequest model validation."""
        from services.video_orchestrator.schemas import SoraGenerateRequest
        from pydantic import ValidationError
        
        # Valid models
        SoraGenerateRequest(prompt="Test", model="sora-2")
        SoraGenerateRequest(prompt="Test", model="sora-2-pro")
        
        # Invalid model
        with pytest.raises(ValidationError):
            SoraGenerateRequest(prompt="Test", model="invalid-model")
    
    def test_pacing_config_wpm_range(self):
        """Test PacingConfig words_per_minute range (90-200)."""
        from services.video_orchestrator.schemas import PacingConfig
        from pydantic import ValidationError
        
        # Valid
        config = PacingConfig(words_per_minute=150)
        assert config.words_per_minute == 150
        
        # Invalid: < 90
        with pytest.raises(ValidationError):
            PacingConfig(words_per_minute=50)
        
        # Invalid: > 200
        with pytest.raises(ValidationError):
            PacingConfig(words_per_minute=250)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestModelIntegration:
    """Test model integration scenarios."""
    
    def test_full_clip_plan_structure(self):
        """Test creating a complete clip plan structure."""
        from services.video_orchestrator.models import (
            VideoProject, ClipPlan, Scene, ClipPlanClip,
            PlanStatus, ClipState, NarrationConfig, VisualIntent,
            NarrationMode
        )
        
        # Create project
        project = VideoProject(title="Demo Video")
        
        # Create plan
        plan = ClipPlan(
            project_id=project.id,
            status=PlanStatus.DRAFT
        )
        
        # Create scene
        scene = Scene(
            clip_plan_id=plan.id,
            name="Opening Hook",
            goal="Grab attention",
            beats=["Introduce topic", "Create curiosity"]
        )
        
        # Create clips
        clip1 = ClipPlanClip(
            scene_id=scene.id,
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(
                mode=NarrationMode.EXTERNAL_VOICEOVER,
                text="Welcome to our video!"
            ),
            visual_intent=VisualIntent(
                prompt="A presenter in modern studio, welcoming gesture",
                must_include=["presenter", "studio"]
            )
        )
        
        clip2 = ClipPlanClip(
            scene_id=scene.id,
            clip_order=1,
            target_seconds=12,
            narration=NarrationConfig(
                mode=NarrationMode.EXTERNAL_VOICEOVER,
                text="Today we'll explore something amazing."
            ),
            visual_intent=VisualIntent(
                prompt="Dynamic transition to topic reveal",
                must_include=["transition", "topic"]
            )
        )
        
        # Verify structure
        assert project.id is not None
        assert plan.project_id == project.id
        assert scene.clip_plan_id == plan.id
        assert clip1.scene_id == scene.id
        assert clip2.scene_id == scene.id
        assert clip1.clip_order < clip2.clip_order
    
    def test_assessment_with_breakdown(self):
        """Test assessment with check breakdown."""
        from services.video_orchestrator.models import (
            Assessment, AssessmentVerdict, CheckBreakdown, RepairInstruction, RepairStrategy
        )
        
        assessment = Assessment(
            clip_run_id=uuid4(),
            verdict=AssessmentVerdict.FAIL,
            score=0.65,
            reasons=["Visual requirements partially met", "Duration slightly off"],
            breakdown=[
                CheckBreakdown(
                    type="visual_requirements",
                    weight=0.3,
                    score=0.7,
                    notes="Missing one required element"
                ),
                CheckBreakdown(
                    type="continuity",
                    weight=0.25,
                    score=0.8,
                    notes="Character consistent"
                ),
                CheckBreakdown(
                    type="duration_ok",
                    weight=0.2,
                    score=0.5,
                    notes="8.5s vs target 8s"
                ),
                CheckBreakdown(
                    type="no_artifacts",
                    weight=0.25,
                    score=0.6,
                    notes="Minor text glitch detected"
                )
            ],
            repair_instruction=RepairInstruction(
                strategy=RepairStrategy.PROMPT_PATCH,
                prompt_delta="Ensure all required elements visible, avoid text"
            )
        )
        
        # Verify weighted score calculation would work
        weighted_sum = sum(b.weight * b.score for b in assessment.breakdown)
        assert 0.6 < weighted_sum < 0.7


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
