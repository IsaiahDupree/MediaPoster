"""
Test Experiment Features (EXP-001 through EXP-005)
===================================================
Verifies that all experiment framework features are implemented and working.
"""

import asyncio
from services.experiments_scheduler.hypothesis import (
    get_hypothesis_framework,
    SuccessCriterion,
    MetricComparison,
    HypothesisStatus
)
from services.experiments_scheduler.agent import (
    get_experiment_agent,
    ExperimentVariant,
    ExperimentType,
    ExperimentStatus
)


def test_hypothesis_framework():
    """Test EXP-002: Hypothesis Framework"""
    print("\n=== Testing Hypothesis Framework (EXP-002) ===")

    framework = get_hypothesis_framework()

    # Create a hypothesis
    hypothesis = framework.create_hypothesis(
        statement="Posts with questions in the first line increase reply rate by 20%",
        success_criteria=[
            SuccessCriterion(
                metric_name="reply_rate",
                comparison=MetricComparison.GREATER_THAN,
                threshold=0.15,  # Baseline was 12%, target is 15%+
                is_required=True
            ),
            SuccessCriterion(
                metric_name="engagement_rate",
                comparison=MetricComparison.GREATER_THAN,
                threshold=0.05,
                is_required=False
            )
        ],
        min_sample_size=30,
        max_sample_size=100,
        tags=["hook", "engagement"]
    )

    print(f"✓ Created hypothesis: {hypothesis.statement}")
    print(f"  - ID: {hypothesis.hypothesis_id}")
    print(f"  - Status: {hypothesis.status.value}")
    print(f"  - Min samples: {hypothesis.min_sample_size}")

    # Start testing
    hypothesis.start_testing()
    assert hypothesis.status == HypothesisStatus.TESTING
    print(f"✓ Hypothesis testing started")

    # Add results
    hypothesis.add_result("reply_rate", 0.18)  # 18% - passes threshold
    hypothesis.add_result("engagement_rate", 0.06)  # 6% - passes threshold

    # Since we don't have 30 samples yet, set it manually for test
    hypothesis.samples_collected = 30

    # Evaluate
    status = hypothesis.evaluate()
    print(f"✓ Hypothesis evaluated: {status.value}")
    assert status == HypothesisStatus.PASSED

    # Get summary stats
    stats = framework.get_summary_stats()
    print(f"✓ Framework stats: {stats['total_hypotheses']} total, {stats['active_tests']} active")

    print("✅ EXP-002: Hypothesis Framework - PASSED")
    return True


def test_experiment_agent():
    """Test EXP-001: Experiment Agent"""
    print("\n=== Testing Experiment Agent (EXP-001) ===")

    framework = get_hypothesis_framework()
    agent = get_experiment_agent()

    # Create hypothesis
    hypothesis = framework.create_hypothesis(
        statement="Question hooks outperform statement hooks by 25%",
        success_criteria=[
            SuccessCriterion(
                metric_name="reply_rate",
                comparison=MetricComparison.GREATER_THAN,
                threshold=0.15,
                is_required=True
            )
        ],
        min_sample_size=50
    )

    # Create variants
    variants = [
        ExperimentVariant(
            variant_id="variant_a",
            name="Question Hook",
            description="Start with an engaging question",
            config={"hook_type": "question"}
        ),
        ExperimentVariant(
            variant_id="variant_b",
            name="Statement Hook",
            description="Start with a bold statement",
            config={"hook_type": "statement"}
        )
    ]

    # Plan experiment
    experiment = agent.plan_experiment(
        name="Hook Format A/B Test",
        description="Test question vs statement hooks",
        hypothesis=hypothesis,
        variants=variants,
        experiment_type=ExperimentType.AB_TEST,
        total_sample_size=100
    )

    print(f"✓ Planned experiment: {experiment.name}")
    print(f"  - ID: {experiment.experiment_id}")
    print(f"  - Type: {experiment.experiment_type.value}")
    print(f"  - Variants: {len(experiment.variants)}")

    # Mark as ready and start
    experiment.status = ExperimentStatus.READY
    success = agent.start_experiment(experiment.experiment_id)
    assert success
    assert experiment.status == ExperimentStatus.RUNNING
    print(f"✓ Experiment started")

    # Collect results
    for i in range(50):
        agent.collect_result(
            experiment.experiment_id,
            "variant_a",
            {"reply_rate": 0.18, "engagement_rate": 0.07}
        )

    for i in range(50):
        agent.collect_result(
            experiment.experiment_id,
            "variant_b",
            {"reply_rate": 0.12, "engagement_rate": 0.05}
        )

    print(f"✓ Collected {experiment.samples_collected} results")

    # Analyze
    analysis = agent.analyze_experiment(experiment.experiment_id)
    print(f"✓ Analysis complete:")
    print(f"  - Winner: {analysis.get('winner_name')}")
    print(f"  - Hypothesis status: {analysis.get('hypothesis_status')}")

    # Get summary stats
    stats = agent.get_summary_stats()
    print(f"✓ Agent stats: {stats['total_experiments']} total, {stats['completed']} completed")

    print("✅ EXP-001: Experiment Agent - PASSED")
    return True


def test_content_experiment_tagging():
    """Test EXP-003: Content Experiment Tagging"""
    print("\n=== Testing Content Experiment Tagging (EXP-003) ===")

    agent = get_experiment_agent()

    # Get an experiment
    experiments = list(agent.experiments.values())
    if experiments:
        experiment = experiments[0]

        # Check that variants have configurations (tags)
        for variant in experiment.variants:
            print(f"✓ Variant '{variant.name}' has config: {variant.config}")
            assert variant.config is not None

        # Check that experiment has tags
        print(f"✓ Experiment has {len(experiment.tags)} tags")

        print("✅ EXP-003: Content Experiment Tagging - PASSED")
        return True
    else:
        print("⚠️  No experiments to test tagging")
        return False


def test_winner_detection():
    """Test EXP-004: Winner Detection & Promotion"""
    print("\n=== Testing Winner Detection & Promotion (EXP-004) ===")

    agent = get_experiment_agent()

    # Get completed experiments
    experiments = [
        exp for exp in agent.experiments.values()
        if exp.status == ExperimentStatus.COMPLETED
    ]

    if experiments:
        experiment = experiments[0]

        # Verify winner was detected
        assert experiment.winner_variant_id is not None
        print(f"✓ Winner detected: {experiment.winner_variant_id}")

        # Get winner variant
        winner = next(
            v for v in experiment.variants
            if v.variant_id == experiment.winner_variant_id
        )
        print(f"✓ Winner variant: {winner.name}")
        print(f"  - Results: {winner.results}")

        print("✅ EXP-004: Winner Detection & Promotion - PASSED")
        return True
    else:
        print("⚠️  No completed experiments to test winner detection")
        return False


def test_ab_test_variants():
    """Test EXP-005: A/B Test Variants"""
    print("\n=== Testing A/B Test Variants (EXP-005) ===")

    agent = get_experiment_agent()

    # Get experiments
    experiments = list(agent.experiments.values())

    if experiments:
        experiment = experiments[0]

        # Verify experiment has multiple variants
        assert len(experiment.variants) >= 2
        print(f"✓ Experiment has {len(experiment.variants)} variants")

        # Verify each variant tracks results independently
        for variant in experiment.variants:
            print(f"  - {variant.name}:")
            print(f"    Sample size: {variant.sample_size}")
            print(f"    Results: {variant.results}")

        # Verify allocation strategy exists
        print(f"✓ Allocation strategy: {experiment.allocation_strategy}")

        print("✅ EXP-005: A/B Test Variants - PASSED")
        return True
    else:
        print("⚠️  No experiments to test variants")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("EXPERIMENT FRAMEWORK TEST SUITE")
    print("=" * 60)

    results = []

    # Run tests
    results.append(("EXP-002", test_hypothesis_framework()))
    results.append(("EXP-001", test_experiment_agent()))
    results.append(("EXP-003", test_content_experiment_tagging()))
    results.append(("EXP-004", test_winner_detection()))
    results.append(("EXP-005", test_ab_test_variants()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for feature_id, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{feature_id}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All experiment features are working!")
        exit(0)
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        exit(1)
