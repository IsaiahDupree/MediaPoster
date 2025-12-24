#!/usr/bin/env python3
"""
Comprehensive Test Runner - All Test Types Against All Endpoints
Runs unit, integration, API, performance, security, database, and E2E tests
"""
import subprocess
import sys
import os
import re
from datetime import datetime
from pathlib import Path

# Change to Backend directory
os.chdir(Path(__file__).parent.parent)

# Test categories with actual file paths
TEST_CATEGORIES = {
    "unit": {
        "description": "Unit tests - Individual functions/classes",
        "paths": [
            "tests/test_scheduler_unit_logic.py",
            "tests/test_assessor.py",
            "tests/test_video_providers.py",
            "tests/test_music_selector.py",
            "tests/test_caption_generation.py",
        ],
        "markers": None
    },
    "api_endpoints": {
        "description": "API/Endpoint tests - All REST endpoints",
        "paths": [
            "tests/test_health_api.py",
            "tests/test_accounts_api.py",
            "tests/test_media_api.py",
            "tests/test_schedule_api.py",
            "tests/test_content_api.py",
            "tests/test_posting_api.py",
            "tests/test_video_api_endpoints.py",
            "tests/test_api_edge_cases.py",
            "tests/test_api_endpoints_comprehensive.py",
            "tests/test_posted_content_api.py",
            "tests/test_automation_api.py",
            "tests/test_scheduler_api.py",
            "tests/test_calendar_api.py",
        ],
        "markers": None
    },
    "integration": {
        "description": "Integration tests - Component interactions",
        "paths": [
            "tests/integration/",
            "tests/test_api_integration.py",
            "tests/test_schedule_integration.py",
            "tests/test_integration_scheduling.py",
        ],
        "markers": "integration"
    },
    "performance": {
        "description": "Performance tests - Latency, load, throughput",
        "paths": [
            "tests/performance/test_backend_performance.py",
            "tests/performance/test_latency_performance.py",
            "tests/database/test_database_performance.py",
        ],
        "markers": "not load"
    },
    "security": {
        "description": "Security tests - Input validation, authentication",
        "paths": [
            "tests/security/",
        ],
        "markers": None
    },
    "database": {
        "description": "Database tests - Constraints, performance, integrity",
        "paths": [
            "tests/database/",
        ],
        "markers": None
    },
    "contract": {
        "description": "Contract tests - API contract validation",
        "paths": [
            "tests/contract/",
        ],
        "markers": None
    },
    "comprehensive": {
        "description": "Comprehensive/E2E tests - Full workflows",
        "paths": [
            "tests/comprehensive/",
        ],
        "markers": None
    }
}

def parse_pytest_output(output):
    """Parse pytest output to extract test counts"""
    passed = 0
    failed = 0
    skipped = 0
    errors = 0
    
    # Look for summary line like "5 passed, 2 failed, 1 skipped in 1.23s"
    # Or "========== 5 failed, 2 passed, 1 skipped, 1 error in 1.23s ==========="
    summary_patterns = [
        r'(\d+)\s+passed.*?(\d+)\s+failed.*?(\d+)\s+skipped.*?(\d+)\s+error',
        r'(\d+)\s+failed.*?(\d+)\s+passed.*?(\d+)\s+skipped.*?(\d+)\s+error',
        r'(\d+)\s+passed.*?(\d+)\s+failed.*?(\d+)\s+error',
        r'(\d+)\s+failed.*?(\d+)\s+passed.*?(\d+)\s+error',
        r'(\d+)\s+passed.*?(\d+)\s+failed',
        r'(\d+)\s+failed.*?(\d+)\s+passed',
    ]
    
    for pattern in summary_patterns:
        match = re.search(pattern, output)
        if match:
            groups = match.groups()
            if len(groups) >= 2:
                # Try to identify which is which
                if 'passed' in output[match.start():match.end()]:
                    passed_idx = output[match.start():match.end()].find('passed') - 10
                    failed_idx = output[match.start():match.end()].find('failed') - 10
                    if passed_idx < failed_idx:
                        passed = int(groups[0])
                        failed = int(groups[1])
                    else:
                        passed = int(groups[1])
                        failed = int(groups[0])
                else:
                    # Default: first is failed, second is passed
                    failed = int(groups[0])
                    passed = int(groups[1])
                
                if len(groups) >= 3:
                    skipped = int(groups[2]) if 'skipped' in output[match.start():match.end()] else 0
                if len(groups) >= 4:
                    errors = int(groups[3]) if 'error' in output[match.start():match.end()] else 0
            break
    
    # Also look for individual patterns as fallback
    if passed == 0 and failed == 0:
        passed_match = re.search(r'(\d+)\s+passed', output)
        if passed_match:
            passed = int(passed_match.group(1))
    
    if failed == 0:
        failed_match = re.search(r'(\d+)\s+failed', output)
        if failed_match:
            failed = int(failed_match.group(1))
    
    if skipped == 0:
        skipped_match = re.search(r'(\d+)\s+skipped', output)
        if skipped_match:
            skipped = int(skipped_match.group(1))
    
    if errors == 0:
        error_match = re.search(r'(\d+)\s+error', output)
        if error_match:
            errors = int(error_match.group(1))
    
    return {"passed": passed, "failed": failed, "skipped": skipped, "errors": errors}

def run_test_category(category, config):
    """Run tests for a specific category"""
    print(f"\n{'='*80}")
    print(f"🧪 {category.upper()} TESTS")
    print(f"{config['description']}")
    print(f"{'='*80}\n")
    
    # Build pytest command
    cmd = [sys.executable, "-m", "pytest"]
    
    # Add paths (filter out non-existent)
    valid_paths = []
    for path in config["paths"]:
        full_path = Path(path)
        if full_path.exists() or (full_path.is_dir() and any(full_path.iterdir())):
            valid_paths.append(path)
    
    if not valid_paths:
        print(f"⚠️  No valid test paths found for {category}")
        return False, {"passed": 0, "failed": 0, "skipped": 0, "errors": 0}
    
    cmd.extend(valid_paths)
    
    # Add markers
    if config.get("markers"):
        cmd.extend(["-m", config["markers"]])
    
    # Add flags
    cmd.extend([
        "-v",
        "--tb=short",
        "--disable-warnings",
        "--maxfail=10",  # Stop after 10 failures per category
    ])
    
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per category
        )
        
        output = result.stdout + result.stderr
        results = parse_pytest_output(output)
        
        # Print last 30 lines of output
        output_lines = output.split('\n')
        print('\n'.join(output_lines[-30:]))
        
        if result.returncode == 0:
            print(f"\n✅ {category.upper()}: PASSED ({results['passed']} passed)")
        else:
            print(f"\n❌ {category.upper()}: FAILED ({results['failed']} failed, {results['errors']} errors, {results['passed']} passed)")
        
        return result.returncode == 0, results
        
    except subprocess.TimeoutExpired:
        print(f"⏱️  {category.upper()} tests timed out after 5 minutes")
        return False, {"passed": 0, "failed": 0, "skipped": 0, "errors": 1}
    except Exception as e:
        print(f"💥 Error running {category} tests: {e}")
        return False, {"passed": 0, "failed": 0, "skipped": 0, "errors": 1}

def main():
    """Run all test categories"""
    print("="*80)
    print("🚀 MEDIAPOSTER COMPREHENSIVE TEST SUITE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Check backend status
    import socket
    backend_running = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 5555))
        sock.close()
        backend_running = (result == 0)
    except:
        pass
    
    if backend_running:
        print("✅ Backend server is running on port 5555")
    else:
        print("⚠️  Backend server not running on port 5555")
        print("   Some tests may fail. Start with: cd Backend && python main.py")
    
    print()
    
    all_results = {}
    total_passed = 0
    total_failed = 0
    total_skipped = 0
    total_errors = 0
    
    # Run each category
    for category, config in TEST_CATEGORIES.items():
        success, results = run_test_category(category, config)
        all_results[category] = {
            "success": success,
            "results": results
        }
        
        total_passed += results["passed"]
        total_failed += results["failed"]
        total_skipped += results["skipped"]
        total_errors += results["errors"]
    
    # Print final summary
    print("\n" + "="*80)
    print("📊 FINAL TEST SUMMARY")
    print("="*80)
    print()
    
    for category, data in all_results.items():
        icon = "✅" if data["success"] else "❌"
        r = data["results"]
        print(f"{icon} {category.upper():20} | Passed: {r['passed']:4} | Failed: {r['failed']:4} | Skipped: {r['skipped']:4} | Errors: {r['errors']:4}")
    
    print()
    print("-"*80)
    print(f"TOTAL: Passed: {total_passed:4} | Failed: {total_failed:4} | Skipped: {total_skipped:4} | Errors: {total_errors:4}")
    print("="*80)
    
    # Calculate success rate
    total_tests = total_passed + total_failed + total_errors
    if total_tests > 0:
        success_rate = (total_passed / total_tests) * 100
        print(f"\nSuccess Rate: {success_rate:.1f}%")
    
    # Exit code
    return 0 if total_failed == 0 and total_errors == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
