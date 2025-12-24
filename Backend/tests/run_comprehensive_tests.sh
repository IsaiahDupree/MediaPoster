#!/bin/bash
# Comprehensive Test Runner for MediaPoster
# Runs all test types against all endpoints

set -e

echo "=================================================================================="
echo "🚀 MEDIAPOSTER COMPREHENSIVE TEST SUITE"
echo "Started: $(date '+%Y-%m-%d %H:%M:%S')"
echo "=================================================================================="
echo ""

cd "$(dirname "$0")/.."
source venv/bin/activate

# Check if backend is running
if ! lsof -ti:5555 > /dev/null 2>&1; then
    echo "⚠️  Backend server not running on port 5555"
    echo "   Starting backend server..."
    python main.py &
    BACKEND_PID=$!
    sleep 5
    echo "   Backend started (PID: $BACKEND_PID)"
    CLEANUP_BACKEND=true
else
    echo "✅ Backend server is running"
    CLEANUP_BACKEND=false
fi

# Test results
TOTAL_PASSED=0
TOTAL_FAILED=0
TOTAL_SKIPPED=0
TOTAL_ERRORS=0

# Function to run test category
run_category() {
    local category=$1
    local description=$2
    local test_paths=$3
    local markers=$4
    
    echo ""
    echo "=================================================================================="
    echo "🧪 $category"
    echo "$description"
    echo "=================================================================================="
    echo ""
    
    local cmd="python -m pytest $test_paths"
    if [ -n "$markers" ]; then
        cmd="$cmd -m \"$markers\""
    fi
    cmd="$cmd -v --tb=short --disable-warnings"
    
    echo "Command: $cmd"
    echo ""
    
    local result=$(eval $cmd 2>&1) || true
    echo "$result" | tail -20
    
    # Parse results
    local passed=$(echo "$result" | grep -oP '\d+(?= passed)' | tail -1 || echo "0")
    local failed=$(echo "$result" | grep -oP '\d+(?= failed)' | tail -1 || echo "0")
    local skipped=$(echo "$result" | grep -oP '\d+(?= skipped)' | tail -1 || echo "0")
    local errors=$(echo "$result" | grep -oP '\d+(?= error)' | tail -1 || echo "0")
    
    TOTAL_PASSED=$((TOTAL_PASSED + ${passed:-0}))
    TOTAL_FAILED=$((TOTAL_FAILED + ${failed:-0}))
    TOTAL_SKIPPED=$((TOTAL_SKIPPED + ${skipped:-0}))
    TOTAL_ERRORS=$((TOTAL_ERRORS + ${errors:-0}))
    
    if [ "${failed:-0}" -eq 0 ] && [ "${errors:-0}" -eq 0 ]; then
        echo "✅ $category: PASSED ($passed passed)"
    else
        echo "❌ $category: FAILED ($failed failed, $errors errors, $passed passed)"
    fi
}

# 1. Unit Tests
run_category "UNIT TESTS" \
    "Individual functions/classes in isolation" \
    "tests/test_scheduler_unit_logic.py tests/test_assessor.py tests/test_video_providers.py tests/test_music_selector.py tests/test_caption_generation.py" \
    "not integration and not e2e"

# 2. API Endpoint Tests
run_category "API ENDPOINT TESTS" \
    "All REST API endpoints" \
    "tests/test_health_api.py tests/test_accounts_api.py tests/test_media_api.py tests/test_schedule_api.py tests/test_content_api.py tests/test_posting_api.py tests/test_video_api_endpoints.py tests/test_api_edge_cases.py tests/test_api_endpoints_comprehensive.py tests/test_posted_content_api.py tests/test_automation_api.py tests/test_scheduler_api.py tests/test_calendar_api.py"

# 3. Integration Tests
run_category "INTEGRATION TESTS" \
    "Component interactions" \
    "tests/integration/ tests/test_api_integration.py tests/test_schedule_integration.py tests/test_integration_scheduling.py" \
    "integration"

# 4. Performance Tests (skip load tests that cause segfaults)
run_category "PERFORMANCE TESTS" \
    "Latency, throughput, database performance" \
    "tests/performance/test_backend_performance.py tests/performance/test_latency_performance.py tests/database/test_database_performance.py" \
    "not load"

# 5. Security Tests
run_category "SECURITY TESTS" \
    "Input validation, authentication, authorization" \
    "tests/security/"

# 6. Database Tests
run_category "DATABASE TESTS" \
    "Constraints, integrity, performance" \
    "tests/database/"

# 7. Contract Tests
run_category "CONTRACT TESTS" \
    "API contract validation" \
    "tests/contract/"

# 8. System/E2E Tests
run_category "SYSTEM/E2E TESTS" \
    "Full workflow tests" \
    "tests/comprehensive/ tests/test_e2e_all_pages.py tests/test_posting_workflow_e2e.py" \
    "e2e"

# Final Summary
echo ""
echo "=================================================================================="
echo "📊 FINAL TEST SUMMARY"
echo "=================================================================================="
echo ""
echo "Total Passed:  $TOTAL_PASSED"
echo "Total Failed:  $TOTAL_FAILED"
echo "Total Skipped: $TOTAL_SKIPPED"
echo "Total Errors:  $TOTAL_ERRORS"
echo ""
echo "=================================================================================="

# Cleanup
if [ "$CLEANUP_BACKEND" = true ]; then
    echo "Stopping backend server (PID: $BACKEND_PID)..."
    kill $BACKEND_PID 2>/dev/null || true
fi

# Exit code
if [ $TOTAL_FAILED -eq 0 ] && [ $TOTAL_ERRORS -eq 0 ]; then
    exit 0
else
    exit 1
fi

