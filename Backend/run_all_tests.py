#!/usr/bin/env python3
"""
Comprehensive Backend Test Runner
Systematically runs all tests and generates a detailed report
"""
import subprocess
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Test categories
TEST_CATEGORIES = {
    "integration": "tests/integration",
    "comprehensive": "tests/comprehensive",
    "e2e": "tests/e2e",
    "database": "tests/database",
    "performance": "tests/performance",
    "contract": "tests/contract",
    "api": "tests/api",
    "pubsub": "tests/pubsub",
    "phase0": "tests/phase0",
    "phase1": "tests/phase1",
    "prd2": "tests/prd2",
    "regression": "tests/regression",
    "usability": "tests/usability",
    "root": "tests"
}

class TestRunner:
    def __init__(self):
        self.results = defaultdict(lambda: {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "duration": 0,
            "files": []
        })
        self.start_time = time.time()
        
    def find_test_files(self, directory):
        """Find all test_*.py files in directory"""
        test_dir = Path(directory)
        if not test_dir.exists():
            return []
        return sorted(test_dir.glob("test_*.py"))
    
    def run_pytest(self, test_path, category):
        """Run pytest on a test file or directory"""
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_path),
            "-v",
            "--tb=short",
            "-q"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout per test
                cwd=Path(__file__).parent
            )
            
            # Parse pytest output
            output = result.stdout + result.stderr
            
            # Look for pytest summary line like "308 passed, 3 failed in 3.05s"
            import re
            summary_match = re.search(r'(\d+)\s+passed', output)
            passed = int(summary_match.group(1)) if summary_match else 0
            
            failed_match = re.search(r'(\d+)\s+failed', output)
            failed = int(failed_match.group(1)) if failed_match else 0
            
            skipped_match = re.search(r'(\d+)\s+skipped', output)
            skipped = int(skipped_match.group(1)) if skipped_match else 0
            
            error_match = re.search(r'(\d+)\s+error', output)
            errors = int(error_match.group(1)) if error_match else 0
            
            duration_match = re.search(r'in\s+([\d.]+)s', output)
            duration = float(duration_match.group(1)) if duration_match else 0
            
            return {
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "error": errors,
                "duration": duration,
                "success": result.returncode == 0,
                "output": output if failed > 0 or errors > 0 else ""
            }
                
        except subprocess.TimeoutExpired:
            return {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "error": 1,
                "duration": 300,
                "success": False,
                "timeout": True
            }
        except Exception as e:
            return {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "error": 1,
                "duration": 0,
                "success": False,
                "exception": str(e)
            }
    
    def run_python_test(self, test_path, category):
        """Run a standalone Python test file"""
        cmd = [sys.executable, str(test_path)]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=Path(__file__).parent
            )
            
            # Simple pass/fail based on exit code
            return {
                "passed": 1 if result.returncode == 0 else 0,
                "failed": 0 if result.returncode == 0 else 1,
                "skipped": 0,
                "error": 0,
                "duration": 0,
                "success": result.returncode == 0
            }
            
        except subprocess.TimeoutExpired:
            return {
                "passed": 0,
                "failed": 1,
                "skipped": 0,
                "error": 0,
                "duration": 120,
                "success": False,
                "timeout": True
            }
        except Exception as e:
            return {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "error": 1,
                "duration": 0,
                "success": False,
                "exception": str(e)
            }
    
    def run_category(self, category, path):
        """Run all tests in a category"""
        print(f"\n{'='*80}")
        print(f"Running {category.upper()} tests from {path}")
        print(f"{'='*80}")
        
        test_files = self.find_test_files(path)
        
        if not test_files:
            print(f"  No test files found in {path}")
            return
        
        print(f"  Found {len(test_files)} test files")
        
        for test_file in test_files:
            print(f"  Testing: {test_file.name}...", end=" ", flush=True)
            
            # Try pytest first
            result = self.run_pytest(test_file, category)
            
            # Update results
            self.results[category]["passed"] += result["passed"]
            self.results[category]["failed"] += result["failed"]
            self.results[category]["skipped"] += result["skipped"]
            self.results[category]["errors"] += result["error"]
            self.results[category]["duration"] += result["duration"]
            self.results[category]["files"].append({
                "name": test_file.name,
                "result": result
            })
            
            # Print result
            if result["success"]:
                print(f"✅ {result['passed']} passed")
            elif result.get("timeout"):
                print(f"⏱️  TIMEOUT")
            else:
                print(f"❌ {result['failed']} failed, {result['error']} errors")
    
    def generate_report(self):
        """Generate comprehensive test report"""
        total_time = time.time() - self.start_time
        
        # Calculate totals
        total_passed = sum(cat["passed"] for cat in self.results.values())
        total_failed = sum(cat["failed"] for cat in self.results.values())
        total_skipped = sum(cat["skipped"] for cat in self.results.values())
        total_errors = sum(cat["errors"] for cat in self.results.values())
        total_tests = total_passed + total_failed + total_skipped
        
        # Generate report
        report = []
        report.append("\n" + "="*80)
        report.append("BACKEND TEST SUITE REPORT")
        report.append("="*80)
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Duration: {total_time:.2f}s")
        report.append("")
        
        # Summary
        report.append("SUMMARY")
        report.append("-" * 80)
        report.append(f"Total Tests:    {total_tests}")
        report.append(f"Passed:         {total_passed} ({total_passed/total_tests*100 if total_tests > 0 else 0:.1f}%)")
        report.append(f"Failed:         {total_failed}")
        report.append(f"Skipped:        {total_skipped}")
        report.append(f"Errors:         {total_errors}")
        report.append("")
        
        # Category breakdown
        report.append("CATEGORY BREAKDOWN")
        report.append("-" * 80)
        
        for category, results in sorted(self.results.items()):
            if results["passed"] + results["failed"] + results["errors"] == 0:
                continue
                
            total = results["passed"] + results["failed"] + results["skipped"]
            pass_rate = (results["passed"] / total * 100) if total > 0 else 0
            
            report.append(f"\n{category.upper()}")
            report.append(f"  Files:    {len(results['files'])}")
            report.append(f"  Passed:   {results['passed']}")
            report.append(f"  Failed:   {results['failed']}")
            report.append(f"  Errors:   {results['errors']}")
            report.append(f"  Pass Rate: {pass_rate:.1f}%")
            report.append(f"  Duration: {results['duration']:.2f}s")
        
        report.append("\n" + "="*80)
        
        # Save report
        report_text = "\n".join(report)
        report_file = Path(__file__).parent / "test_report.txt"
        report_file.write_text(report_text)
        
        print(report_text)
        print(f"\nReport saved to: {report_file}")
        
        return total_failed + total_errors == 0


def main():
    print("🧪 Backend Test Suite Runner")
    print("="*80)
    
    runner = TestRunner()
    
    # Run tests by category
    for category, path in TEST_CATEGORIES.items():
        if category == "root":
            # Skip root-level tests for now (run via categories)
            continue
        runner.run_category(category, path)
    
    # Generate report
    success = runner.generate_report()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
