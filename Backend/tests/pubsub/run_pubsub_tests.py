#!/usr/bin/env python3
"""
Pub/Sub Test Runner
===================
Runs all pub/sub tests with proper categorization and reporting.
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type: str = "all", verbose: bool = True, coverage: bool = False):
    """Run pub/sub tests by category."""
    
    test_dir = Path(__file__).parent
    
    test_categories = {
        "unit": "test_unit_*.py",
        "contract": "test_contract_*.py",
        "integration": "test_integration_*.py",
        "idempotency": "test_idempotency_*.py",
        "e2e": "test_e2e_*.py",
        "observability": "test_observability_*.py",
        "worker": "test_worker_*.py",
        "load": "test_load_*.py",
        "all": "test_*.py"
    }
    
    if test_type not in test_categories:
        print(f"Unknown test type: {test_type}")
        print(f"Available types: {', '.join(test_categories.keys())}")
        return 1
    
    pattern = test_categories[test_type]
    test_path = test_dir / pattern
    
    cmd = ["pytest", str(test_path)]
    
    if verbose:
        cmd.append("-v")
    
    if coverage:
        cmd.extend([
            "--cov=services.event_bus",
            "--cov=services.workers",
            "--cov-report=html",
            "--cov-report=term"
        ])
    
    print(f"Running {test_type} tests: {pattern}")
    print(f"Command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, cwd=test_dir.parent.parent)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run pub/sub tests")
    parser.add_argument(
        "type",
        nargs="?",
        default="all",
        choices=["unit", "contract", "integration", "idempotency", "e2e", "observability", "worker", "load", "all"],
        help="Test category to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=True,
        help="Verbose output"
    )
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    args = parser.parse_args()
    
    return run_tests(args.type, args.verbose, args.coverage)


if __name__ == "__main__":
    sys.exit(main())

