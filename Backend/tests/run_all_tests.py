#!/usr/bin/env python3
"""
Run All Tests Script
Executes all test suites for the MediaPoster backend.
"""

import subprocess
import sys
import os
from datetime import datetime

# Test files to run
TEST_FILES = [
    "test_content_growth.py",
    "test_metrics_scheduler.py",
    "test_approval_queue.py",
    "test_image_analysis.py",
    "test_posted_media.py",
]

def run_tests(verbose=True, coverage=False):
    """Run all test files"""
    
    # Change to tests directory
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(tests_dir)
    
    print("=" * 60)
    print(f"MediaPoster Backend Test Suite")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    results = {}
    
    for test_file in TEST_FILES:
        if not os.path.exists(test_file):
            print(f"⚠️  Skipping {test_file} - file not found")
            results[test_file] = "skipped"
            continue
        
        print(f"\n{'=' * 60}")
        print(f"Running: {test_file}")
        print("=" * 60)
        
        cmd = [sys.executable, "-m", "pytest", test_file]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd = [sys.executable, "-m", "pytest", f"--cov=../api", test_file]
        
        try:
            result = subprocess.run(cmd, capture_output=not verbose)
            
            if result.returncode == 0:
                results[test_file] = "passed"
                print(f"✅ {test_file}: PASSED")
            else:
                results[test_file] = "failed"
                print(f"❌ {test_file}: FAILED")
                if not verbose:
                    print(result.stdout.decode())
                    print(result.stderr.decode())
        except Exception as e:
            results[test_file] = f"error: {e}"
            print(f"💥 {test_file}: ERROR - {e}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for r in results.values() if r == "passed")
    failed = sum(1 for r in results.values() if r == "failed")
    skipped = sum(1 for r in results.values() if r == "skipped")
    errors = sum(1 for r in results.values() if r.startswith("error"))
    
    for test_file, result in results.items():
        icon = "✅" if result == "passed" else "❌" if result == "failed" else "⚠️"
        print(f"  {icon} {test_file}: {result}")
    
    print()
    print(f"Total: {len(TEST_FILES)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped} | Errors: {errors}")
    print("=" * 60)
    
    return 0 if failed == 0 and errors == 0 else 1


def run_single_test(test_file, verbose=True):
    """Run a single test file"""
    tests_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(tests_dir)
    
    cmd = [sys.executable, "-m", "pytest", test_file]
    if verbose:
        cmd.append("-v")
    
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run MediaPoster backend tests")
    parser.add_argument("-v", "--verbose", action="store_true", default=True,
                       help="Verbose output")
    parser.add_argument("-q", "--quiet", action="store_true",
                       help="Quiet output")
    parser.add_argument("--coverage", action="store_true",
                       help="Run with coverage")
    parser.add_argument("-f", "--file", type=str,
                       help="Run specific test file")
    
    args = parser.parse_args()
    
    if args.file:
        sys.exit(run_single_test(args.file, not args.quiet))
    else:
        sys.exit(run_tests(not args.quiet, args.coverage))
