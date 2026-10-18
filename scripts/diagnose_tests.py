#!/usr/bin/env python3
"""
Test Diagnostic Script
Identifies common test failures and suggests fixes
"""
import subprocess
import sys
import json
import requests
from datetime import datetime

# Colors
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

BACKEND_URL = "http://localhost:5555"
FRONTEND_URL = "http://localhost:5557"


def print_header(text):
    print(f"\n{BLUE}{'═' * 60}{NC}")
    print(f"{BLUE}  {text}{NC}")
    print(f"{BLUE}{'═' * 60}{NC}\n")


def print_pass(text):
    print(f"  {GREEN}✓{NC} {text}")


def print_fail(text):
    print(f"  {RED}✗{NC} {text}")


def print_warn(text):
    print(f"  {YELLOW}⚠{NC} {text}")


def print_info(text):
    print(f"  {BLUE}ℹ{NC} {text}")


def check_server(name, url, timeout=5):
    """Check if a server is responding"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code, response.elapsed.total_seconds()
    except requests.exceptions.ConnectionError:
        return None, 0
    except requests.exceptions.Timeout:
        return "timeout", timeout


def diagnose_backend_errors():
    """Diagnose common backend test failures"""
    print_header("Backend Diagnostics")
    
    issues = []
    
    # Check main endpoints
    endpoints_to_check = [
        ("/docs", "API Documentation"),
        ("/api/social-analytics/overview", "Analytics Overview"),
        ("/api/social-analytics/accounts", "Social Accounts"),
        ("/api/videos", "Videos"),
        ("/api/platform/posts", "Platform Posts"),
        ("/api/platform/platforms", "Platforms List"),
        ("/api/goals", "Goals"),
        ("/api/publishing/scheduled", "Scheduled Posts"),
        ("/api/clips", "Clips"),
        ("/openapi.json", "OpenAPI Spec"),
    ]
    
    for endpoint, name in endpoints_to_check:
        status, time = check_server(name, f"{BACKEND_URL}{endpoint}")
        
        if status == 200:
            print_pass(f"{name}: OK ({time:.2f}s)")
        elif status == 500:
            print_fail(f"{name}: Server Error (500)")
            issues.append({
                "endpoint": endpoint,
                "name": name,
                "error": "500 Internal Server Error",
                "likely_cause": "Database query error or async session issue"
            })
        elif status == 404:
            print_warn(f"{name}: Not Found (404)")
        elif status is None:
            print_fail(f"{name}: Connection refused")
            issues.append({
                "endpoint": endpoint,
                "name": name,
                "error": "Connection refused",
                "likely_cause": "Backend server not running"
            })
        else:
            print_warn(f"{name}: Status {status}")
    
    return issues


def diagnose_database():
    """Check database connectivity"""
    print_header("Database Diagnostics")
    
    issues = []
    
    # Try to get data from an endpoint that requires DB
    try:
        response = requests.get(f"{BACKEND_URL}/api/social-analytics/accounts", timeout=10)
        data = response.json()
        
        if response.status_code == 200:
            if isinstance(data, list):
                print_pass(f"Database responding: {len(data)} accounts found")
            else:
                print_pass("Database responding")
        elif response.status_code == 500:
            print_fail("Database query failed (500)")
            
            # Check for specific error patterns
            error_text = str(data)
            if "AsyncSession" in error_text:
                issues.append({
                    "type": "async_session",
                    "error": "AsyncSession object has no attribute 'query'",
                    "fix": "Use `select()` with `session.execute()` instead of `session.query()`"
                })
            elif "syntax error" in error_text.lower():
                issues.append({
                    "type": "sql_syntax",
                    "error": "SQL syntax error",
                    "fix": "Check SQL query parameters and syntax"
                })
            elif "connection" in error_text.lower():
                issues.append({
                    "type": "connection",
                    "error": "Database connection failed",
                    "fix": "Check DATABASE_URL and ensure PostgreSQL is running"
                })
    except Exception as e:
        print_fail(f"Database check failed: {e}")
        issues.append({
            "type": "connection",
            "error": str(e),
            "fix": "Ensure backend server is running"
        })
    
    return issues


def diagnose_frontend():
    """Check frontend health"""
    print_header("Frontend Diagnostics")
    
    issues = []
    
    pages_to_check = [
        ("/", "Homepage"),
        ("/dashboard", "Dashboard"),
        ("/analytics", "Analytics"),
        ("/content", "Content"),
        ("/schedule", "Schedule"),
        ("/settings", "Settings"),
        ("/videos", "Videos"),
    ]
    
    for path, name in pages_to_check:
        status, time = check_server(name, f"{FRONTEND_URL}{path}")
        
        if status == 200:
            print_pass(f"{name}: OK ({time:.2f}s)")
        elif status is None:
            print_fail(f"{name}: Connection refused")
            issues.append({
                "page": path,
                "name": name,
                "error": "Connection refused",
                "likely_cause": "Frontend server not running"
            })
        else:
            print_warn(f"{name}: Status {status}")
    
    return issues


def check_known_issues():
    """Check for known test issues"""
    print_header("Known Issue Patterns")
    
    known_issues = [
        {
            "pattern": "AsyncSession object has no attribute 'query'",
            "cause": "SQLAlchemy 2.0 breaking change",
            "fix": "Replace session.query(Model) with select(Model) + session.execute()",
            "files": ["api/endpoints/platform_publishing.py", "api/endpoints/clips.py"]
        },
        {
            "pattern": "syntax error at or near \":\"",
            "cause": "Named parameter syntax issue with raw SQL",
            "fix": "Use bindparam() or text() with proper parameter binding",
            "files": ["api/endpoints/social_analytics.py"]
        },
        {
            "pattern": "attached to a different loop",
            "cause": "Async event loop mismatch in tests",
            "fix": "Use pytest-asyncio fixtures properly or ensure single event loop",
            "files": ["tests/"]
        },
        {
            "pattern": "No QueryClient set",
            "cause": "React Query context missing in tests",
            "fix": "Wrap test components in QueryClientProvider",
            "files": ["Frontend/src/components/**/__tests__/"]
        },
        {
            "pattern": "timeout of 30000ms exceeded",
            "cause": "Page load taking too long or waiting for missing element",
            "fix": "Check if page renders correctly, increase timeout, or fix selectors",
            "files": ["Frontend/e2e/tests/"]
        },
    ]
    
    for issue in known_issues:
        print(f"  {YELLOW}Pattern:{NC} {issue['pattern']}")
        print(f"    Cause: {issue['cause']}")
        print(f"    Fix:   {issue['fix']}")
        print(f"    Files: {', '.join(issue['files'])}")
        print()
    
    return known_issues


def run_quick_backend_test():
    """Run a quick backend smoke test and capture output"""
    print_header("Quick Backend Test")
    
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", "tests/test_smoke.py", "-v", "--tb=short", "-x"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd="Backend"
        )
        
        output = result.stdout + result.stderr
        
        # Count results
        passed = output.count(" PASSED")
        failed = output.count(" FAILED")
        
        print(f"  Passed: {GREEN}{passed}{NC}")
        print(f"  Failed: {RED}{failed}{NC}")
        
        # Extract failure reasons
        if failed > 0:
            print(f"\n  {YELLOW}Failure Details:{NC}")
            for line in output.split('\n'):
                if 'FAILED' in line or 'Error' in line or 'error' in line.lower():
                    # Truncate long lines
                    if len(line) > 100:
                        line = line[:100] + "..."
                    print(f"    {line.strip()}")
        
        return passed, failed
    except subprocess.TimeoutExpired:
        print_fail("Test timed out after 60s")
        return 0, -1
    except FileNotFoundError:
        print_fail("Could not run pytest (not in correct directory?)")
        return 0, -1


def generate_report():
    """Generate a full diagnostic report"""
    print(f"\n{BLUE}{'═' * 60}{NC}")
    print(f"{BLUE}  MediaPoster Test Diagnostics{NC}")
    print(f"{BLUE}  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NC}")
    print(f"{BLUE}{'═' * 60}{NC}")
    
    all_issues = []
    
    # Run diagnostics
    backend_issues = diagnose_backend_errors()
    all_issues.extend(backend_issues)
    
    db_issues = diagnose_database()
    all_issues.extend(db_issues)
    
    frontend_issues = diagnose_frontend()
    all_issues.extend(frontend_issues)
    
    known = check_known_issues()
    
    # Summary
    print_header("Summary & Recommendations")
    
    if not all_issues:
        print_pass("All services responding correctly")
        print_info("If tests still fail, check the 'Known Issue Patterns' above")
    else:
        print(f"  Found {RED}{len(all_issues)}{NC} issues:\n")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue.get('name', issue.get('type', 'Unknown'))}")
            print(f"     Error: {issue.get('error', 'Unknown')}")
            if 'fix' in issue:
                print(f"     Fix: {issue['fix']}")
            if 'likely_cause' in issue:
                print(f"     Cause: {issue['likely_cause']}")
            print()
    
    print_header("Quick Fixes")
    print("""
  1. Restart Backend:
     cd Backend && source venv/bin/activate && uvicorn main:app --port 5555 --reload

  2. Restart Frontend:
     cd Frontend && npm run dev

  3. Check Database:
     cd supabase && supabase status

  4. Run specific test with verbose output:
     cd Backend && pytest tests/test_smoke.py::TestSmoke::test_platform_posts_responds -v -s

  5. Run frontend tests with debug:
     cd Frontend && npx playwright test --debug
""")


if __name__ == "__main__":
    generate_report()
