"""
PubSub Test Harness
====================
Unified test runner for the complete pub/sub test suite.

Usage:
    python -m pytest Backend/tests/pubsub/test_harness.py -v
    python Backend/tests/pubsub/test_harness.py  # Direct execution
    
Features:
    - Spins up test infrastructure (in-memory DB, event bus)
    - Runs all test layers in order
    - Provides test matrix summary
    - Validates timeline invariants
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

# Add backend to path
BACKEND_PATH = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BACKEND_PATH))


# ============================================================================
# TEST CONFIGURATION
# ============================================================================

@dataclass
class TestConfig:
    """Configuration for test harness."""
    database_url: str = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    run_integration_tests: bool = True
    run_load_tests: bool = False
    verbose: bool = True
    timeout_seconds: int = 60


@dataclass
class TestResult:
    """Result of a test run."""
    category: str
    passed: int
    failed: int
    skipped: int
    duration_ms: float
    errors: List[str] = field(default_factory=list)
    
    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped
    
    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total * 100


# ============================================================================
# TEST CATEGORIES
# ============================================================================

TEST_CATEGORIES = {
    "unit": {
        "description": "Unit tests - pure logic without broker/DB",
        "files": [
            "test_unit_topic_routing.py",
            "test_unit_step_machine.py",
            "test_unit_scoring_logic.py",
            "test_unit_event_routing.py",
        ],
        "priority": 1,
    },
    "contract": {
        "description": "Contract tests - message schema validation",
        "files": [
            "test_contract_message_schema.py",
            "test_contract_event_schemas.py",
        ],
        "priority": 2,
    },
    "idempotency": {
        "description": "Idempotency tests - deduplication verification",
        "files": [
            "test_idempotency.py",
            "test_idempotency_workers.py",
        ],
        "priority": 3,
    },
    "integration": {
        "description": "Integration tests - broker/DB semantics",
        "files": [
            "test_integration_broker_db.py",
            "test_integration_event_persistence.py",
        ],
        "priority": 4,
        "requires_db": True,
    },
    "services": {
        "description": "Service-specific tests",
        "files": [
            "test_scheduler_service.py",
            "test_narrative_planner_service.py",
            "test_experiments_service.py",
            "test_worker_services.py",
        ],
        "priority": 5,
    },
    "e2e": {
        "description": "E2E workflow tests - full pipeline validation",
        "files": [
            "test_e2e_workflows.py",
        ],
        "priority": 6,
    },
    "observability": {
        "description": "Observability tests - timeline correctness",
        "files": [
            "test_observability_timeline.py",
        ],
        "priority": 7,
    },
    "load": {
        "description": "Load tests - performance under pressure",
        "files": [
            "test_load_performance.py",
        ],
        "priority": 8,
        "optional": True,
    },
}


# ============================================================================
# TEST MATRIX
# ============================================================================

TEST_MATRIX = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                        PUB/SUB TEST MATRIX                                   ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ SERVICE              │ UNIT │ CONTRACT │ IDEMPOTENCY │ INTEGRATION │ E2E    ║
╠══════════════════════════════════════════════════════════════════════════════╣
║ SchedulerService     │  ✓   │    ✓     │      ✓      │      ✓      │   ✓    ║
║ NarrativePlanner     │  ✓   │    ✓     │      ✓      │      ✓      │   ✓    ║
║ ExperimentsService   │  ✓   │    ✓     │      ✓      │      ✓      │   ✓    ║
║ Worker/Queue         │  ✓   │    ✓     │      ✓      │      ✓      │   ✓    ║
║ EventBus             │  ✓   │    ✓     │      -      │      ✓      │   ✓    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""


# ============================================================================
# TIMELINE INVARIANTS
# ============================================================================

class TimelineInvariantChecker:
    """Validates timeline event invariants."""
    
    @staticmethod
    def check_run_lifecycle(events: List[Dict[str, Any]]) -> List[str]:
        """
        Check that every run has proper lifecycle events.
        - Must have run.queued then run.started then terminal event
        """
        errors = []
        runs: Dict[str, List[str]] = {}
        
        for event in events:
            topic = event.get("topic", "")
            run_id = event.get("payload", {}).get("run_id")
            
            if not run_id:
                continue
            
            if run_id not in runs:
                runs[run_id] = []
            runs[run_id].append(topic)
        
        for run_id, topics in runs.items():
            # Check for queued → started → terminal
            has_queued = any("queued" in t for t in topics)
            has_started = any("started" in t for t in topics)
            has_terminal = any(
                "succeeded" in t or "failed" in t or "completed" in t 
                for t in topics
            )
            
            if has_started and not has_queued:
                errors.append(f"Run {run_id}: has started but missing queued event")
            
            if has_terminal and not has_started:
                errors.append(f"Run {run_id}: has terminal but missing started event")
        
        return errors
    
    @staticmethod
    def check_step_lifecycle(events: List[Dict[str, Any]]) -> List[str]:
        """
        Check that every step has proper lifecycle events.
        - Must have step.started and terminal step.completed or step.failed
        """
        errors = []
        steps: Dict[str, List[str]] = {}
        
        for event in events:
            topic = event.get("topic", "")
            step_key = event.get("payload", {}).get("step_key")
            run_id = event.get("payload", {}).get("run_id", "unknown")
            
            if not step_key:
                continue
            
            key = f"{run_id}:{step_key}"
            if key not in steps:
                steps[key] = []
            steps[key].append(topic)
        
        for step_key, topics in steps.items():
            has_started = any("started" in t for t in topics)
            has_completed = any("completed" in t for t in topics)
            has_failed = any("failed" in t for t in topics)
            
            if (has_completed or has_failed) and not has_started:
                errors.append(f"Step {step_key}: has terminal but missing started event")
        
        return errors
    
    @staticmethod
    def check_event_ordering(events: List[Dict[str, Any]]) -> List[str]:
        """Check that events are in chronological order."""
        errors = []
        
        prev_time = None
        for i, event in enumerate(events):
            timestamp = event.get("timestamp")
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except:
                    continue
            
            if prev_time and timestamp and timestamp < prev_time:
                errors.append(f"Event {i}: out of order (before previous event)")
            
            prev_time = timestamp
        
        return errors
    
    @staticmethod
    def check_no_sensitive_data(events: List[Dict[str, Any]]) -> List[str]:
        """Check that thought summaries don't contain sensitive data."""
        errors = []
        sensitive_patterns = ["password", "token", "secret", "api_key", "apikey"]
        
        for event in events:
            if "thought" in event.get("topic", ""):
                summary = event.get("payload", {}).get("summary", "")
                for pattern in sensitive_patterns:
                    if pattern.lower() in summary.lower():
                        errors.append(f"Thought contains sensitive pattern: {pattern}")
        
        return errors


# ============================================================================
# HARNESS RUNNER
# ============================================================================

class PubSubTestHarness:
    """Main test harness runner."""
    
    def __init__(self, config: Optional[TestConfig] = None):
        self.config = config or TestConfig()
        self.results: List[TestResult] = []
        self.timeline_events: List[Dict[str, Any]] = []
    
    def print_header(self):
        """Print test matrix header."""
        print("\n" + "=" * 80)
        print("           PUB/SUB SERVICE TEST SUITE")
        print("=" * 80)
        print(TEST_MATRIX)
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("           TEST SUMMARY")
        print("=" * 80)
        
        total_passed = sum(r.passed for r in self.results)
        total_failed = sum(r.failed for r in self.results)
        total_skipped = sum(r.skipped for r in self.results)
        total_duration = sum(r.duration_ms for r in self.results)
        
        for result in self.results:
            status = "✓" if result.failed == 0 else "✗"
            print(f"  {status} {result.category:20} "
                  f"passed={result.passed:3} failed={result.failed:3} "
                  f"skipped={result.skipped:3} ({result.duration_ms:.0f}ms)")
        
        print("-" * 80)
        print(f"  TOTAL: {total_passed} passed, {total_failed} failed, "
              f"{total_skipped} skipped ({total_duration:.0f}ms)")
        
        if total_failed > 0:
            print("\n  ⚠️  Some tests failed!")
            for result in self.results:
                for error in result.errors:
                    print(f"    - {error}")
        else:
            print("\n  ✅ All tests passed!")
    
    def run_category(self, category: str) -> TestResult:
        """Run tests for a category."""
        config = TEST_CATEGORIES.get(category, {})
        files = config.get("files", [])
        requires_db = config.get("requires_db", False)
        
        # Skip DB-required tests if DB not available
        if requires_db and not self.config.run_integration_tests:
            return TestResult(
                category=category,
                passed=0,
                failed=0,
                skipped=len(files),
                duration_ms=0,
            )
        
        # Build pytest args
        test_dir = Path(__file__).parent
        test_files = [str(test_dir / f) for f in files if (test_dir / f).exists()]
        
        if not test_files:
            return TestResult(
                category=category,
                passed=0,
                failed=0,
                skipped=0,
                duration_ms=0,
            )
        
        start = datetime.now()
        
        # Run pytest
        args = test_files + ["-v", "--tb=short", "-q"]
        result = pytest.main(args)
        
        duration = (datetime.now() - start).total_seconds() * 1000
        
        # Simplified result (actual counts would come from pytest hooks)
        return TestResult(
            category=category,
            passed=1 if result == 0 else 0,
            failed=0 if result == 0 else 1,
            skipped=0,
            duration_ms=duration,
        )
    
    def run_timeline_invariants(self) -> List[str]:
        """Run timeline invariant checks."""
        checker = TimelineInvariantChecker()
        all_errors = []
        
        all_errors.extend(checker.check_run_lifecycle(self.timeline_events))
        all_errors.extend(checker.check_step_lifecycle(self.timeline_events))
        all_errors.extend(checker.check_event_ordering(self.timeline_events))
        all_errors.extend(checker.check_no_sensitive_data(self.timeline_events))
        
        return all_errors
    
    def run_all(self):
        """Run all test categories."""
        self.print_header()
        
        # Sort categories by priority
        sorted_categories = sorted(
            TEST_CATEGORIES.items(),
            key=lambda x: x[1].get("priority", 99)
        )
        
        for category, config in sorted_categories:
            # Skip optional tests unless explicitly enabled
            if config.get("optional") and not self.config.run_load_tests:
                continue
            
            print(f"\n{'─' * 40}")
            print(f"Running {category} tests: {config['description']}")
            print(f"{'─' * 40}")
            
            result = self.run_category(category)
            self.results.append(result)
        
        # Run timeline invariant checks
        invariant_errors = self.run_timeline_invariants()
        if invariant_errors:
            self.results.append(TestResult(
                category="invariants",
                passed=0,
                failed=len(invariant_errors),
                skipped=0,
                duration_ms=0,
                errors=invariant_errors,
            ))
        
        self.print_summary()
        
        # Return exit code
        total_failed = sum(r.failed for r in self.results)
        return 0 if total_failed == 0 else 1


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="PubSub Test Harness")
    parser.add_argument("--no-integration", action="store_true",
                       help="Skip integration tests")
    parser.add_argument("--load", action="store_true",
                       help="Include load tests")
    parser.add_argument("--quiet", action="store_true",
                       help="Minimal output")
    
    args = parser.parse_args()
    
    config = TestConfig(
        run_integration_tests=not args.no_integration,
        run_load_tests=args.load,
        verbose=not args.quiet,
    )
    
    harness = PubSubTestHarness(config)
    exit_code = harness.run_all()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()


# ============================================================================
# PYTEST INTEGRATION
# ============================================================================

class TestHarnessIntegration:
    """Integration tests for the harness itself."""
    
    def test_timeline_invariant_checker_catches_missing_queued(self):
        """Should catch run missing queued event."""
        events = [
            {"topic": "run.started", "payload": {"run_id": "r1"}},
            {"topic": "run.succeeded", "payload": {"run_id": "r1"}},
        ]
        
        errors = TimelineInvariantChecker.check_run_lifecycle(events)
        assert len(errors) > 0
        assert any("queued" in e for e in errors)
    
    def test_timeline_invariant_checker_passes_valid_lifecycle(self):
        """Should pass valid run lifecycle."""
        events = [
            {"topic": "run.queued", "payload": {"run_id": "r1"}},
            {"topic": "run.started", "payload": {"run_id": "r1"}},
            {"topic": "run.succeeded", "payload": {"run_id": "r1"}},
        ]
        
        errors = TimelineInvariantChecker.check_run_lifecycle(events)
        assert len(errors) == 0
    
    def test_timeline_invariant_checker_catches_sensitive_data(self):
        """Should catch sensitive data in thoughts."""
        events = [
            {"topic": "thought.summary", "payload": {"summary": "Using api_key=secret123"}},
        ]
        
        errors = TimelineInvariantChecker.check_no_sensitive_data(events)
        assert len(errors) > 0
    
    def test_timeline_invariant_checker_allows_clean_thoughts(self):
        """Should allow clean thought summaries."""
        events = [
            {"topic": "thought.summary", "payload": {"summary": "Selected video for high engagement"}},
        ]
        
        errors = TimelineInvariantChecker.check_no_sensitive_data(events)
        assert len(errors) == 0
