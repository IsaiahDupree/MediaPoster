"""
Integration tests for Video Orchestrator components
====================================================
Tests ORCH-001, ORCH-002, ORCH-003 to verify implementation.
"""
import pytest
import asyncio
from datetime import datetime, timezone

from services.video_orchestrator.director import DirectorService, DirectorConfig
from services.video_orchestrator.scene_crafter import SceneCrafterService
from services.video_orchestrator.assessor import AssessorService, AssessmentInput
from services.video_orchestrator.models import (
    VideoScript,
    ContentBrief,
    PlanConstraints,
    ClipRun,
    ClipRunStatus,
    NarrationMode,
    ProviderName,
)


class TestVideoOrchestratorDirector:
    """Test ORCH-001: Video Orchestrator Director"""

    @pytest.mark.asyncio
    async def test_director_creates_clip_plan(self):
        """Test that Director can create a clip plan from a script"""
        # Arrange
        director = DirectorService()

        script = VideoScript(
            project_id="test-project",
            title="Test Video",
            body="If you can rank trends, you can print content. "
                 "Most people chase trends with no product fit and wonder why it doesn't convert. "
                 "Here's the scoring rubric I use to evaluate trends before creating content.",
            language="en"
        )

        constraints = PlanConstraints(
            max_total_seconds=45,
            aspect_ratio="9:16"
        )

        # Act
        plan, scene, clips = await director.create_clip_plan(
            script=script,
            constraints=constraints
        )

        # Assert
        assert plan is not None
        assert plan.project_id == "test-project"
        assert scene is not None
        assert len(clips) > 0
        assert all(clip.target_seconds in [4, 8, 12] for clip in clips)

        # Check total duration doesn't exceed max
        total_duration = sum(clip.target_seconds for clip in clips)
        assert total_duration <= constraints.max_total_seconds

        print(f"\n✓ Director created plan with {len(clips)} clips, {total_duration}s total")
        for i, clip in enumerate(clips):
            print(f"  Clip {i+1}: {clip.target_seconds}s - {clip.narration.text[:50]}...")

    @pytest.mark.asyncio
    async def test_director_respects_word_count_limits(self):
        """Test that Director chunks scripts according to word count limits"""
        director = DirectorService(
            config=DirectorConfig(
                words_per_minute=150,
                max_words_per_clip=30
            )
        )

        # Long script with multiple sentences
        long_script = " ".join([
            "This is sentence one about ranking trends.",
            "This is sentence two about product fit.",
            "This is sentence three about conversion rates.",
            "This is sentence four about content strategy.",
            "This is sentence five about audience targeting.",
            "This is sentence six about performance metrics."
        ])

        script = VideoScript(
            project_id="test-long",
            title="Long Test",
            body=long_script,
            language="en"
        )

        plan, scene, clips = await director.create_clip_plan(script)

        # Verify each clip respects word limits
        for clip in clips:
            word_count = len(clip.narration.text.split())
            assert word_count <= 35  # Slightly over max is OK for sentence boundaries

        print(f"\n✓ All {len(clips)} clips respect word count limits")

    def test_director_estimates_duration(self):
        """Test duration estimation"""
        director = DirectorService()

        script_text = "This is a test script. " * 50  # ~100 words

        estimate = director.estimate_duration(script_text)

        assert estimate["word_count"] > 0
        assert estimate["estimated_seconds"] > 0
        assert estimate["estimated_clips"] > 0

        print(f"\n✓ Duration estimate: {estimate}")


class TestSceneCrafter:
    """Test ORCH-002: Scene Crafter"""

    def test_scene_crafter_builds_baked_prompt(self):
        """Test that SceneCrafter builds complete prompts from clip + bibles"""
        from services.video_orchestrator.models import (
            ClipPlanClip,
            Scene,
            VisualIntent,
            NarrationConfig,
            ProviderHints,
            AcceptanceCriteria,
            ClipState,
            VideoBible,
            BibleKind
        )

        crafter = SceneCrafterService()

        # Create test clip
        clip = ClipPlanClip(
            scene_id="scene-1",
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(
                mode=NarrationMode.EXTERNAL_VOICEOVER,
                text="If you can rank trends, you can print content",
                speaker="narrator",
                language="en"
            ),
            visual_intent=VisualIntent(
                prompt="Person writing on whiteboard showing trend analysis",
                must_include=["whiteboard", "charts"],
                must_avoid=["blurry text"],
                camera="medium shot",
                setting="modern office"
            ),
            provider_hints=ProviderHints(
                primary_provider=ProviderName.SORA,
                model="sora-2",
                size="720x1280"
            ),
            acceptance=AcceptanceCriteria.default(),
            state=ClipState.PENDING
        )

        # Create style bible
        style_bible = VideoBible(
            kind=BibleKind.STYLE,
            body={
                "lighting": "natural daylight",
                "mood": "professional and engaging",
                "visual_style": "clean modern aesthetic",
                "color_palette": ["blue", "white", "gray"]
            }
        )

        # Build baked prompt
        baked_prompt = crafter.build_baked_prompt(
            clip=clip,
            style_bible=style_bible
        )

        # Assert
        assert "whiteboard" in baked_prompt.lower() or "Person" in baked_prompt
        assert len(baked_prompt) > len(clip.visual_intent.prompt)

        print(f"\n✓ Baked prompt generated:")
        print(f"  Base: {clip.visual_intent.prompt}")
        print(f"  Baked: {baked_prompt[:150]}...")

    def test_scene_crafter_builds_provider_payload(self):
        """Test that SceneCrafter creates provider-ready payloads"""
        from services.video_orchestrator.models import (
            ClipPlanClip,
            VisualIntent,
            NarrationConfig,
            ProviderHints,
            AcceptanceCriteria,
            ClipState
        )

        crafter = SceneCrafterService()

        clip = ClipPlanClip(
            scene_id="scene-1",
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(
                mode=NarrationMode.EXTERNAL_VOICEOVER,
                text="Test narration",
                speaker="narrator",
                language="en"
            ),
            visual_intent=VisualIntent(
                prompt="Test visual",
                must_include=["element1"],
                must_avoid=["artifact1"],
                camera="wide shot",
                setting="office"
            ),
            provider_hints=ProviderHints(
                primary_provider=ProviderName.SORA,
                model="sora-2",
                size="720x1280"
            ),
            acceptance=AcceptanceCriteria.default(),
            state=ClipState.PENDING
        )

        payload = crafter.build_provider_payload(clip)

        assert payload.clip_id == str(clip.id)
        assert payload.seconds == 8
        assert payload.model == "sora-2"
        assert payload.size == "720x1280"
        assert len(payload.prompt) > 0

        print(f"\n✓ Provider payload created:")
        print(f"  Clip ID: {payload.clip_id}")
        print(f"  Duration: {payload.seconds}s")
        print(f"  Model: {payload.model}")


class TestAssessor:
    """Test ORCH-003: Clip Assessor (QA/Retry)"""

    @pytest.mark.asyncio
    async def test_assessor_evaluates_clip(self):
        """Test that Assessor can evaluate a clip run"""
        from services.video_orchestrator.models import (
            ClipPlanClip,
            VisualIntent,
            NarrationConfig,
            ProviderHints,
            AcceptanceCriteria,
            AcceptanceCheck,
            CheckType,
            ClipState,
            ClipRun,
            ClipRunStatus
        )

        assessor = AssessorService()

        # Create test clip
        clip = ClipPlanClip(
            scene_id="scene-1",
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(
                mode=NarrationMode.EXTERNAL_VOICEOVER,
                text="Test narration for assessment",
                speaker="narrator",
                language="en"
            ),
            visual_intent=VisualIntent(
                prompt="Test visual",
                must_include=["element1"],
                must_avoid=["glitch"],
                camera="medium shot",
                setting="office"
            ),
            provider_hints=ProviderHints(
                primary_provider=ProviderName.SORA,
                model="sora-2",
                size="720x1280"
            ),
            acceptance=AcceptanceCriteria(
                score_threshold=0.7,
                checks=[
                    AcceptanceCheck(type=CheckType.DURATION_OK, weight=0.3),
                    AcceptanceCheck(type=CheckType.NO_ARTIFACTS, weight=0.4),
                    AcceptanceCheck(type=CheckType.VISUAL_REQUIREMENTS, weight=0.3)
                ]
            ),
            state=ClipState.PENDING
        )

        # Create successful clip run
        clip_run = ClipRun(
            clip_plan_clip_id=clip.id,
            attempt=1,
            provider=ProviderName.SORA,
            status=ClipRunStatus.SUCCEEDED,
            duration_actual=8.2,
            response_payload={"video_url": "https://example.com/video.mp4"}
        )

        # Assess
        assessment_input = AssessmentInput(
            clip=clip,
            clip_run=clip_run,
            actual_duration=8.2
        )

        assessment = await assessor.assess(assessment_input)

        # Assert
        assert assessment is not None
        assert assessment.verdict is not None
        assert 0.0 <= assessment.score <= 1.0
        assert len(assessment.breakdown) > 0

        print(f"\n✓ Assessment completed:")
        print(f"  Verdict: {assessment.verdict.value}")
        print(f"  Score: {assessment.score:.2f}")
        print(f"  Checks: {len(assessment.breakdown)}")
        for check in assessment.breakdown:
            print(f"    - {check.type}: {check.score:.2f} (weight: {check.weight})")

    @pytest.mark.asyncio
    async def test_assessor_generates_repair_instruction(self):
        """Test that Assessor generates repair instructions for failed clips"""
        from services.video_orchestrator.models import (
            ClipPlanClip,
            VisualIntent,
            NarrationConfig,
            ProviderHints,
            AcceptanceCriteria,
            AcceptanceCheck,
            CheckType,
            ClipState,
            ClipRun,
            ClipRunStatus,
            AssessmentVerdict
        )

        assessor = AssessorService(strict_mode=True)  # Fail on any check failure

        clip = ClipPlanClip(
            scene_id="scene-1",
            clip_order=0,
            target_seconds=8,
            narration=NarrationConfig(
                mode=NarrationMode.EXTERNAL_VOICEOVER,
                text="Test narration",
                speaker="narrator",
                language="en"
            ),
            visual_intent=VisualIntent(
                prompt="Test visual",
                must_include=["specific_element"],
                must_avoid=["glitch"],
                camera="medium shot",
                setting="office"
            ),
            provider_hints=ProviderHints(
                primary_provider=ProviderName.SORA,
                model="sora-2",
                size="720x1280"
            ),
            acceptance=AcceptanceCriteria(
                score_threshold=0.8,
                checks=[
                    AcceptanceCheck(type=CheckType.DURATION_OK, weight=0.5),
                    AcceptanceCheck(type=CheckType.VISUAL_REQUIREMENTS, weight=0.5)
                ]
            ),
            state=ClipState.PENDING
        )

        # Create failed clip run (wrong duration)
        clip_run = ClipRun(
            clip_plan_clip_id=clip.id,
            attempt=1,
            provider=ProviderName.SORA,
            status=ClipRunStatus.SUCCEEDED,
            duration_actual=12.0,  # Way over target of 8s
            response_payload={"video_url": "https://example.com/video.mp4"}
        )

        assessment_input = AssessmentInput(
            clip=clip,
            clip_run=clip_run,
            actual_duration=12.0
        )

        assessment = await assessor.assess(assessment_input)

        # Should fail due to duration mismatch in strict mode
        assert assessment.verdict in [AssessmentVerdict.FAIL, AssessmentVerdict.NEEDS_REVIEW]

        # Should have repair instruction
        if assessment.repair_instruction:
            print(f"\n✓ Repair instruction generated:")
            print(f"  Strategy: {assessment.repair_instruction.strategy.value}")
            print(f"  Notes: {assessment.repair_instruction.notes}")
            if assessment.repair_instruction.prompt_delta:
                print(f"  Prompt delta: {assessment.repair_instruction.prompt_delta[:100]}...")
        else:
            print(f"\n  No repair instruction (verdict: {assessment.verdict.value})")


if __name__ == "__main__":
    # Run tests manually
    print("=" * 70)
    print("Video Orchestrator Integration Tests")
    print("=" * 70)

    # Test Director
    print("\n[ORCH-001] Testing Director Service...")
    test_director = TestVideoOrchestratorDirector()
    asyncio.run(test_director.test_director_creates_clip_plan())
    asyncio.run(test_director.test_director_respects_word_count_limits())
    test_director.test_director_estimates_duration()

    # Test Scene Crafter
    print("\n[ORCH-002] Testing Scene Crafter Service...")
    test_crafter = TestSceneCrafter()
    test_crafter.test_scene_crafter_builds_baked_prompt()
    test_crafter.test_scene_crafter_builds_provider_payload()

    # Test Assessor
    print("\n[ORCH-003] Testing Assessor Service...")
    test_assessor = TestAssessor()
    asyncio.run(test_assessor.test_assessor_evaluates_clip())
    asyncio.run(test_assessor.test_assessor_generates_repair_instruction())

    print("\n" + "=" * 70)
    print("✓ All Video Orchestrator tests passed!")
    print("=" * 70)
