"""
Assessor Service Tests
======================
Unit tests for Assessor service and repair logic.

Run tests:
    pytest tests/test_assessor.py -v
"""

import asyncio
import pytest
from uuid import uuid4
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# CHECK RESULT TESTS
# =============================================================================

class TestCheckResult:
    """Test CheckResult dataclass."""
    
    def test_weighted_score(self):
        """Test weighted score calculation."""
        from services.video_orchestrator.assessor import CheckResult
        from services.video_orchestrator.models import CheckType
        
        result = CheckResult(
            check_type=CheckType.VISUAL_REQUIREMENTS,
            passed=True,
            score=0.8,
            weight=0.3
        )
        
        assert result.weighted_score == 0.24  # 0.8 * 0.3
    
    def test_check_result_with_evidence(self):
        """Test CheckResult with evidence."""
        from services.video_orchestrator.assessor import CheckResult
        from services.video_orchestrator.models import CheckType
        
        result = CheckResult(
            check_type=CheckType.DURATION_OK,
            passed=True,
            score=0.9,
            weight=0.2,
            notes="Duration within tolerance",
            evidence={"target": 8, "actual": 7.8}
        )
        
        assert result.evidence["target"] == 8
        assert result.evidence["actual"] == 7.8


# =============================================================================
# ASSESSOR SERVICE TESTS
# =============================================================================

class TestAssessorService:
    """Test AssessorService."""
    
    @pytest.fixture
    def sample_clip(self):
        """Create sample clip for assessment."""
        from services.video_orchestrator.models import (
            ClipPlanClip, NarrationConfig, VisualIntent, ProviderHints,
            AcceptanceCriteria, AcceptanceCheck, NarrationMode, ProviderName,
            CheckType
        )
        
        return ClipPlanClip(
            scene_id=uuid4(),
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(
                mode=NarrationMode.EXTERNAL_VOICEOVER,
                text="Welcome to our video about technology."
            ),
            visual_intent=VisualIntent(
                prompt="A presenter in a modern studio",
                must_include=["presenter", "studio"],
                must_avoid=["glitchy text"]
            ),
            provider_hints=ProviderHints(
                primary_provider=ProviderName.SORA,
                model="sora-2"
            ),
            acceptance=AcceptanceCriteria(
                score_threshold=0.8,
                checks=[
                    AcceptanceCheck(type=CheckType.VISUAL_REQUIREMENTS, weight=0.3),
                    AcceptanceCheck(type=CheckType.CONTINUITY, weight=0.25),
                    AcceptanceCheck(type=CheckType.NO_ARTIFACTS, weight=0.25),
                    AcceptanceCheck(type=CheckType.DURATION_OK, weight=0.2)
                ]
            )
        )
    
    @pytest.fixture
    def sample_clip_run(self):
        """Create sample clip run."""
        from services.video_orchestrator.models import (
            ClipRun, ProviderName, ClipRunStatus
        )
        
        return ClipRun(
            clip_plan_clip_id=uuid4(),
            provider=ProviderName.SORA,
            provider_generation_id="gen_test_123",
            attempt=1,
            status=ClipRunStatus.SUCCEEDED,
            duration_actual=8.0
        )
    
    @pytest.mark.asyncio
    async def test_assess_passing_clip(self, sample_clip, sample_clip_run):
        """Test assessment of a passing clip."""
        from services.video_orchestrator.assessor import AssessorService, AssessmentInput
        from services.video_orchestrator.models import AssessmentVerdict
        
        assessor = AssessorService()
        
        input = AssessmentInput(
            clip=sample_clip,
            clip_run=sample_clip_run,
            actual_duration=8.0
        )
        
        assessment = await assessor.assess(input)
        
        assert assessment.verdict == AssessmentVerdict.PASS
        assert assessment.score >= 0.8
        assert len(assessment.breakdown) == 4
        assert assessment.repair_instruction is None
    
    @pytest.mark.asyncio
    async def test_assess_failing_duration(self, sample_clip, sample_clip_run):
        """Test assessment with failing duration."""
        from services.video_orchestrator.assessor import AssessorService, AssessmentInput
        from services.video_orchestrator.models import AssessmentVerdict
        
        assessor = AssessorService()
        
        # Set actual duration way off target
        input = AssessmentInput(
            clip=sample_clip,
            clip_run=sample_clip_run,
            actual_duration=15.0  # Target is 8s
        )
        
        assessment = await assessor.assess(input)
        
        # Find duration check in breakdown
        duration_check = next(
            (b for b in assessment.breakdown if b.type == "duration_ok"),
            None
        )
        
        assert duration_check is not None
        assert duration_check.score < 0.7  # Should be low score
    
    @pytest.mark.asyncio
    async def test_assess_strict_mode(self, sample_clip, sample_clip_run):
        """Test strict mode fails on any check failure."""
        from services.video_orchestrator.assessor import AssessorService, AssessmentInput
        from services.video_orchestrator.models import AssessmentVerdict
        
        assessor = AssessorService(strict_mode=True)
        
        # Duration way off
        input = AssessmentInput(
            clip=sample_clip,
            clip_run=sample_clip_run,
            actual_duration=20.0
        )
        
        assessment = await assessor.assess(input)
        
        # Strict mode should fail
        assert assessment.verdict == AssessmentVerdict.FAIL
    
    @pytest.mark.asyncio
    async def test_assess_generates_repair_instruction(self, sample_clip, sample_clip_run):
        """Test that failed assessment generates repair instruction."""
        from services.video_orchestrator.assessor import AssessorService, AssessmentInput
        from services.video_orchestrator.models import (
            AssessmentVerdict, AcceptanceCriteria, AcceptanceCheck, CheckType
        )
        
        # Create clip with high threshold that will fail
        sample_clip.acceptance = AcceptanceCriteria(
            score_threshold=0.99,  # Very high threshold
            checks=[
                AcceptanceCheck(type=CheckType.VISUAL_REQUIREMENTS, weight=0.5),
                AcceptanceCheck(type=CheckType.DURATION_OK, weight=0.5)
            ]
        )
        
        assessor = AssessorService()
        
        input = AssessmentInput(
            clip=sample_clip,
            clip_run=sample_clip_run,
            actual_duration=12.0  # Off target
        )
        
        assessment = await assessor.assess(input)
        
        # Should fail due to high threshold
        if assessment.verdict == AssessmentVerdict.FAIL:
            assert assessment.repair_instruction is not None
            assert assessment.repair_instruction.strategy is not None


# =============================================================================
# TRANSCRIPT CHECK TESTS
# =============================================================================

class TestTranscriptCheck:
    """Test transcript matching logic."""
    
    @pytest.fixture
    def assessor(self):
        from services.video_orchestrator.assessor import AssessorService
        return AssessorService()
    
    @pytest.mark.asyncio
    async def test_external_voiceover_passes(self, assessor):
        """Test external voiceover mode always passes transcript check."""
        from services.video_orchestrator.assessor import AssessmentInput
        from services.video_orchestrator.models import (
            ClipPlanClip, NarrationConfig, VisualIntent, ProviderHints,
            AcceptanceCriteria, AcceptanceCheck, NarrationMode, ProviderName,
            CheckType, ClipRun, ClipRunStatus
        )
        
        clip = ClipPlanClip(
            scene_id=uuid4(),
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(
                mode=NarrationMode.EXTERNAL_VOICEOVER,
                text="This text will be overlaid"
            ),
            visual_intent=VisualIntent(prompt="Test"),
            provider_hints=ProviderHints(primary_provider=ProviderName.SORA),
            acceptance=AcceptanceCriteria(
                score_threshold=0.8,
                checks=[AcceptanceCheck(type=CheckType.TRANSCRIPT_MATCH, weight=1.0)]
            )
        )
        
        clip_run = ClipRun(
            clip_plan_clip_id=clip.id,
            provider=ProviderName.SORA,
            provider_generation_id="gen_123",
            status=ClipRunStatus.SUCCEEDED
        )
        
        input = AssessmentInput(clip=clip, clip_run=clip_run)
        
        result = await assessor._check_transcript_match(input, 1.0, {})
        
        assert result.passed is True
        assert result.score == 1.0
    
    @pytest.mark.asyncio
    async def test_no_narration_passes(self, assessor):
        """Test no narration mode passes transcript check."""
        from services.video_orchestrator.assessor import AssessmentInput
        from services.video_orchestrator.models import (
            ClipPlanClip, NarrationConfig, VisualIntent, ProviderHints,
            AcceptanceCriteria, NarrationMode, ProviderName, ClipRun, ClipRunStatus
        )
        
        clip = ClipPlanClip(
            scene_id=uuid4(),
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(mode=NarrationMode.NONE, text=""),
            visual_intent=VisualIntent(prompt="Test"),
            provider_hints=ProviderHints(primary_provider=ProviderName.SORA),
            acceptance=AcceptanceCriteria()
        )
        
        clip_run = ClipRun(
            clip_plan_clip_id=clip.id,
            provider=ProviderName.SORA,
            provider_generation_id="gen_123",
            status=ClipRunStatus.SUCCEEDED
        )
        
        input = AssessmentInput(clip=clip, clip_run=clip_run)
        
        result = await assessor._check_transcript_match(input, 1.0, {})
        
        assert result.passed is True


# =============================================================================
# DURATION CHECK TESTS
# =============================================================================

class TestDurationCheck:
    """Test duration checking logic."""
    
    @pytest.fixture
    def assessor(self):
        from services.video_orchestrator.assessor import AssessorService
        return AssessorService()
    
    @pytest.fixture
    def base_clip(self):
        from services.video_orchestrator.models import (
            ClipPlanClip, NarrationConfig, VisualIntent, ProviderHints,
            AcceptanceCriteria, NarrationMode, ProviderName
        )
        
        return ClipPlanClip(
            scene_id=uuid4(),
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(mode=NarrationMode.NONE, text=""),
            visual_intent=VisualIntent(prompt="Test"),
            provider_hints=ProviderHints(primary_provider=ProviderName.SORA),
            acceptance=AcceptanceCriteria()
        )
    
    @pytest.mark.asyncio
    async def test_exact_duration_passes(self, assessor, base_clip):
        """Test exact duration match passes."""
        from services.video_orchestrator.assessor import AssessmentInput
        from services.video_orchestrator.models import ClipRun, ProviderName, ClipRunStatus
        
        clip_run = ClipRun(
            clip_plan_clip_id=base_clip.id,
            provider=ProviderName.SORA,
            provider_generation_id="gen_123",
            status=ClipRunStatus.SUCCEEDED,
            duration_actual=8.0
        )
        
        input = AssessmentInput(clip=base_clip, clip_run=clip_run, actual_duration=8.0)
        
        result = await assessor._check_duration(input, 0.2, {})
        
        assert result.passed is True
        assert result.score == 1.0
    
    @pytest.mark.asyncio
    async def test_within_tolerance_passes(self, assessor, base_clip):
        """Test duration within tolerance passes."""
        from services.video_orchestrator.assessor import AssessmentInput
        from services.video_orchestrator.models import ClipRun, ProviderName, ClipRunStatus
        
        clip_run = ClipRun(
            clip_plan_clip_id=base_clip.id,
            provider=ProviderName.SORA,
            provider_generation_id="gen_123",
            status=ClipRunStatus.SUCCEEDED
        )
        
        input = AssessmentInput(
            clip=base_clip,
            clip_run=clip_run,
            actual_duration=8.5  # 0.5s off, within 1s tolerance
        )
        
        result = await assessor._check_duration(input, 0.2, {"tolerance_seconds": 1.0})
        
        assert result.passed is True
    
    @pytest.mark.asyncio
    async def test_outside_tolerance_fails(self, assessor, base_clip):
        """Test duration outside tolerance fails."""
        from services.video_orchestrator.assessor import AssessmentInput
        from services.video_orchestrator.models import ClipRun, ProviderName, ClipRunStatus
        
        clip_run = ClipRun(
            clip_plan_clip_id=base_clip.id,
            provider=ProviderName.SORA,
            provider_generation_id="gen_123",
            status=ClipRunStatus.SUCCEEDED
        )
        
        input = AssessmentInput(
            clip=base_clip,
            clip_run=clip_run,
            actual_duration=15.0  # Way off
        )
        
        result = await assessor._check_duration(input, 0.2, {"tolerance_seconds": 1.0})
        
        assert result.passed is False
        assert result.score < 0.5


# =============================================================================
# REPAIR INSTRUCTION TESTS
# =============================================================================

class TestRepairInstruction:
    """Test repair instruction generation."""
    
    def test_prompt_patch_for_first_attempt(self):
        """Test prompt patch strategy for first attempt failures."""
        from services.video_orchestrator.assessor import AssessorService, CheckResult
        from services.video_orchestrator.models import (
            ClipPlanClip, NarrationConfig, VisualIntent, ProviderHints,
            AcceptanceCriteria, NarrationMode, ProviderName, ClipRun,
            ClipRunStatus, RepairStrategy, CheckType
        )
        
        assessor = AssessorService()
        
        clip = ClipPlanClip(
            scene_id=uuid4(),
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(mode=NarrationMode.NONE, text=""),
            visual_intent=VisualIntent(
                prompt="Test",
                must_include=["presenter", "studio"]
            ),
            provider_hints=ProviderHints(primary_provider=ProviderName.SORA),
            acceptance=AcceptanceCriteria()
        )
        
        clip_run = ClipRun(
            clip_plan_clip_id=clip.id,
            provider=ProviderName.SORA,
            provider_generation_id="gen_123",
            attempt=1,  # First attempt
            status=ClipRunStatus.SUCCEEDED
        )
        
        check_results = [
            CheckResult(
                check_type=CheckType.VISUAL_REQUIREMENTS,
                passed=False,
                score=0.4,
                weight=0.5,
                notes="Missing required elements"
            )
        ]
        
        instruction = assessor._generate_repair_instruction(
            check_results, clip, clip_run
        )
        
        assert instruction.strategy == RepairStrategy.PROMPT_PATCH
        assert "presenter" in instruction.prompt_delta or "studio" in instruction.prompt_delta
    
    def test_remix_for_second_attempt(self):
        """Test remix strategy for second attempt visual failures."""
        from services.video_orchestrator.assessor import AssessorService, CheckResult
        from services.video_orchestrator.models import (
            ClipPlanClip, NarrationConfig, VisualIntent, ProviderHints,
            AcceptanceCriteria, NarrationMode, ProviderName, ClipRun,
            ClipRunStatus, RepairStrategy, CheckType
        )
        
        assessor = AssessorService()
        
        clip = ClipPlanClip(
            scene_id=uuid4(),
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(mode=NarrationMode.NONE, text=""),
            visual_intent=VisualIntent(prompt="Test", must_include=["presenter"]),
            provider_hints=ProviderHints(primary_provider=ProviderName.SORA),
            acceptance=AcceptanceCriteria()
        )
        
        clip_run = ClipRun(
            clip_plan_clip_id=clip.id,
            provider=ProviderName.SORA,
            provider_generation_id="gen_123",
            attempt=2,  # Second attempt
            status=ClipRunStatus.SUCCEEDED
        )
        
        check_results = [
            CheckResult(
                check_type=CheckType.VISUAL_REQUIREMENTS,
                passed=False,
                score=0.4,
                weight=0.5,
                notes="Missing required elements"
            )
        ]
        
        instruction = assessor._generate_repair_instruction(
            check_results, clip, clip_run
        )
        
        assert instruction.strategy == RepairStrategy.REMIX
    
    def test_fallback_for_third_attempt(self):
        """Test fallback provider for third+ attempt failures."""
        from services.video_orchestrator.assessor import AssessorService, CheckResult
        from services.video_orchestrator.models import (
            ClipPlanClip, NarrationConfig, VisualIntent, ProviderHints,
            AcceptanceCriteria, NarrationMode, ProviderName, ClipRun,
            ClipRunStatus, RepairStrategy, CheckType
        )
        
        assessor = AssessorService()
        
        clip = ClipPlanClip(
            scene_id=uuid4(),
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(mode=NarrationMode.NONE, text=""),
            visual_intent=VisualIntent(prompt="Test"),
            provider_hints=ProviderHints(primary_provider=ProviderName.SORA),
            acceptance=AcceptanceCriteria()
        )
        
        clip_run = ClipRun(
            clip_plan_clip_id=clip.id,
            provider=ProviderName.SORA,
            provider_generation_id="gen_123",
            attempt=3,  # Third attempt - triggers fallback
            status=ClipRunStatus.SUCCEEDED
        )
        
        check_results = [
            CheckResult(
                check_type=CheckType.VISUAL_REQUIREMENTS,
                passed=False,
                score=0.4,
                weight=0.5,
                notes="Still failing"
            )
        ]
        
        instruction = assessor._generate_repair_instruction(
            check_results, clip, clip_run
        )
        
        assert instruction.strategy == RepairStrategy.FALLBACK_PROVIDER
        assert instruction.fallback_provider == ProviderName.RUNWAY


# =============================================================================
# QUICK ASSESS TESTS
# =============================================================================

class TestQuickAssess:
    """Test quick_assess method."""
    
    @pytest.mark.asyncio
    async def test_quick_assess_succeeded_run(self):
        """Test quick assess for succeeded run."""
        from services.video_orchestrator.assessor import AssessorService
        from services.video_orchestrator.models import (
            ClipPlanClip, NarrationConfig, VisualIntent, ProviderHints,
            AcceptanceCriteria, NarrationMode, ProviderName, ClipRun, ClipRunStatus
        )
        
        assessor = AssessorService()
        
        clip = ClipPlanClip(
            scene_id=uuid4(),
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(mode=NarrationMode.NONE, text=""),
            visual_intent=VisualIntent(prompt="Test"),
            provider_hints=ProviderHints(primary_provider=ProviderName.SORA),
            acceptance=AcceptanceCriteria()
        )
        
        clip_run = ClipRun(
            clip_plan_clip_id=clip.id,
            provider=ProviderName.SORA,
            provider_generation_id="gen_123",
            status=ClipRunStatus.SUCCEEDED,
            response_payload={"id": "gen_123", "status": "completed"}
        )
        
        passed, score, reason = await assessor.quick_assess(clip_run, clip)
        
        assert passed is True
        assert score >= 0.8
    
    @pytest.mark.asyncio
    async def test_quick_assess_failed_run(self):
        """Test quick assess for failed run."""
        from services.video_orchestrator.assessor import AssessorService
        from services.video_orchestrator.models import (
            ClipPlanClip, NarrationConfig, VisualIntent, ProviderHints,
            AcceptanceCriteria, NarrationMode, ProviderName, ClipRun, ClipRunStatus
        )
        
        assessor = AssessorService()
        
        clip = ClipPlanClip(
            scene_id=uuid4(),
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(mode=NarrationMode.NONE, text=""),
            visual_intent=VisualIntent(prompt="Test"),
            provider_hints=ProviderHints(primary_provider=ProviderName.SORA),
            acceptance=AcceptanceCriteria()
        )
        
        clip_run = ClipRun(
            clip_plan_clip_id=clip.id,
            provider=ProviderName.SORA,
            provider_generation_id="gen_123",
            status=ClipRunStatus.FAILED
        )
        
        passed, score, reason = await assessor.quick_assess(clip_run, clip)
        
        assert passed is False
        assert "failed" in reason.lower()


# =============================================================================
# REPAIR EXECUTOR TESTS
# =============================================================================

class TestRepairExecutor:
    """Test RepairExecutor."""
    
    @pytest.mark.asyncio
    async def test_execute_prompt_patch(self):
        """Test executing prompt patch repair."""
        from services.video_orchestrator.assessor import RepairExecutor
        from services.video_orchestrator.models import (
            ClipPlanClip, NarrationConfig, VisualIntent, ProviderHints,
            AcceptanceCriteria, NarrationMode, ProviderName, ClipRun,
            ClipRunStatus, RepairInstruction, RepairStrategy
        )
        from services.video_providers.base import CreateClipInput
        
        executor = RepairExecutor()
        
        clip = ClipPlanClip(
            scene_id=uuid4(),
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(mode=NarrationMode.NONE, text=""),
            visual_intent=VisualIntent(prompt="A person walking"),
            provider_hints=ProviderHints(primary_provider=ProviderName.SORA),
            acceptance=AcceptanceCriteria()
        )
        
        clip_run = ClipRun(
            clip_plan_clip_id=clip.id,
            provider=ProviderName.SORA,
            provider_generation_id="gen_123",
            status=ClipRunStatus.SUCCEEDED
        )
        
        instruction = RepairInstruction(
            strategy=RepairStrategy.PROMPT_PATCH,
            prompt_delta="Add vibrant colors"
        )
        
        result = await executor.execute_repair(clip, instruction, clip_run)
        
        assert isinstance(result, CreateClipInput)
        assert "vibrant colors" in result.prompt or "walking" in result.prompt
    
    @pytest.mark.asyncio
    async def test_execute_remix(self):
        """Test executing remix repair."""
        from services.video_orchestrator.assessor import RepairExecutor
        from services.video_orchestrator.models import (
            ClipPlanClip, NarrationConfig, VisualIntent, ProviderHints,
            AcceptanceCriteria, NarrationMode, ProviderName, ClipRun,
            ClipRunStatus, RepairInstruction, RepairStrategy
        )
        from services.video_providers.base import RemixClipInput
        
        executor = RepairExecutor()
        
        clip = ClipPlanClip(
            scene_id=uuid4(),
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(mode=NarrationMode.NONE, text=""),
            visual_intent=VisualIntent(prompt="A person walking"),
            provider_hints=ProviderHints(primary_provider=ProviderName.SORA),
            acceptance=AcceptanceCriteria()
        )
        
        clip_run = ClipRun(
            clip_plan_clip_id=clip.id,
            provider=ProviderName.SORA,
            provider_generation_id="gen_original_123",
            status=ClipRunStatus.SUCCEEDED
        )
        
        instruction = RepairInstruction(
            strategy=RepairStrategy.REMIX,
            prompt_delta="Make it more cinematic"
        )
        
        result = await executor.execute_repair(clip, instruction, clip_run)
        
        assert isinstance(result, RemixClipInput)
        assert result.source_generation_id == "gen_original_123"
        assert "cinematic" in result.prompt_delta


# =============================================================================
# RUN CONFIGURATION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
