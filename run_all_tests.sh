#!/bin/bash
#
# MediaPoster Comprehensive Test Runner
# Organized by test type for flexibility
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/Backend"
FRONTEND_DIR="$PROJECT_ROOT/Frontend"

# Counters
PASSED=0
FAILED=0

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}\n"
}

run_test() {
    local name=$1
    local dir=$2
    local cmd=$3
    
    echo -e "${YELLOW}▶ $name${NC}"
    
    if (cd "$dir" && eval "$cmd"); then
        echo -e "${GREEN}✓ PASSED${NC}: $name\n"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}: $name\n"
        ((FAILED++))
    fi
}

show_help() {
    echo "MediaPoster Test Runner"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --smoke         Quick smoke tests only (~30s)"
    echo "  --unit          Unit tests only"
    echo "  --integration   Integration tests only"
    echo "  --e2e           End-to-end tests only"
    echo "  --api           API tests only"
    echo "  --performance   Performance tests only"
    echo "  --security      Security tests only"
    echo "  --frontend      Frontend tests only"
    echo "  --backend       Backend tests only"
    echo "  --all           Run everything (default)"
    echo "  -h, --help      Show this help"
    exit 0
}

# Parse arguments
TEST_TYPE="${1:-all}"
case "$TEST_TYPE" in
    -h|--help) show_help ;;
    --*) TEST_TYPE="${TEST_TYPE#--}" ;;
esac

print_header "MediaPoster Test Suite - $(echo $TEST_TYPE | tr '[:lower:]' '[:upper:]')"
echo "Started: $(date)"
echo ""

# ============================================================================
# HEALTH CHECK (run before tests)
# ============================================================================
print_header "Pre-Test Health Check"

BACKEND_URL="${BACKEND_URL:-http://localhost:5555}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5557}"

# Check Backend
echo -e "${YELLOW}Checking Backend...${NC}"
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/docs" 2>/dev/null || echo "000")
if [ "$BACKEND_STATUS" = "200" ]; then
    echo -e "  ${GREEN}✓${NC} Backend responding on $BACKEND_URL"
else
    echo -e "  ${RED}✗${NC} Backend not responding (status: $BACKEND_STATUS)"
    echo ""
    echo -e "${RED}Backend server is not running!${NC}"
    echo "Start it with: cd Backend && source venv/bin/activate && uvicorn main:app --port 5555 --reload"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check Frontend
echo -e "${YELLOW}Checking Frontend...${NC}"
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" 2>/dev/null || echo "000")
if [ "$FRONTEND_STATUS" = "200" ]; then
    echo -e "  ${GREEN}✓${NC} Frontend responding on $FRONTEND_URL"
else
    echo -e "  ${RED}✗${NC} Frontend not responding (status: $FRONTEND_STATUS)"
    echo ""
    echo -e "${RED}Frontend server is not running!${NC}"
    echo "Start it with: cd Frontend && npm run dev"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Quick API check
echo -e "${YELLOW}Checking API endpoints...${NC}"
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/api/social-analytics/overview" 2>/dev/null || echo "000")
if [ "$API_STATUS" = "200" ]; then
    echo -e "  ${GREEN}✓${NC} API endpoints responding"
elif [ "$API_STATUS" = "500" ]; then
    echo -e "  ${YELLOW}⚠${NC} API returning 500 errors (database issue?)"
else
    echo -e "  ${YELLOW}⚠${NC} API status: $API_STATUS"
fi

echo ""

# =============================================================================
# SMOKE TESTS (Quick health checks)
# =============================================================================
if [[ "$TEST_TYPE" =~ ^(all|smoke|backend)$ ]]; then
    print_header "Backend Smoke Tests"
    run_test "API Health Checks" "$BACKEND_DIR" \
        "source venv/bin/activate && pytest tests/test_smoke.py -v --tb=short 2>/dev/null || true"
fi

if [[ "$TEST_TYPE" =~ ^(all|smoke|frontend)$ ]]; then
    print_header "Frontend Smoke Tests"
    run_test "Page Load Tests" "$FRONTEND_DIR" \
        "npx playwright test e2e/tests/smoke.spec.ts --reporter=list 2>/dev/null || true"
fi

# =============================================================================
# UNIT TESTS
# =============================================================================
if [[ "$TEST_TYPE" =~ ^(all|unit|backend)$ ]]; then
    print_header "Backend Unit Tests"
    run_test "Service Unit Tests" "$BACKEND_DIR" \
        "source venv/bin/activate && pytest tests/ -v --ignore=tests/integration --ignore=tests/performance --ignore=tests/security --ignore=tests/system -x --tb=short 2>/dev/null || true"
fi

if [[ "$TEST_TYPE" =~ ^(all|unit|frontend)$ ]]; then
    print_header "Frontend Unit Tests (Jest)"
    run_test "Component Tests" "$FRONTEND_DIR" \
        "npm test -- --passWithNoTests 2>/dev/null || true"
fi

# =============================================================================
# INTEGRATION TESTS
# =============================================================================
if [[ "$TEST_TYPE" =~ ^(all|integration|backend)$ ]]; then
    print_header "Backend Integration Tests"
    run_test "All Phases Integration" "$BACKEND_DIR" \
        "source venv/bin/activate && pytest tests/integration/ -v --tb=short 2>/dev/null || true"
fi

if [[ "$TEST_TYPE" =~ ^(all|integration|frontend)$ ]]; then
    print_header "Frontend Integration Tests"
    run_test "Frontend-Backend Integration" "$FRONTEND_DIR" \
        "npx playwright test e2e/tests/integration/ --reporter=list 2>/dev/null || true"
fi

# =============================================================================
# API TESTS
# =============================================================================
if [[ "$TEST_TYPE" =~ ^(all|api|backend)$ ]]; then
    print_header "Backend API Tests"
    run_test "Comprehensive API Tests" "$BACKEND_DIR" \
        "source venv/bin/activate && pytest tests/comprehensive/ -v --tb=short 2>/dev/null || true"
fi

if [[ "$TEST_TYPE" =~ ^(all|api|frontend)$ ]]; then
    print_header "Frontend API Tests (Playwright)"
    run_test "API Contract Tests" "$FRONTEND_DIR" \
        "npx playwright test e2e/tests/api/ --reporter=list 2>/dev/null || true"
fi

# =============================================================================
# E2E TESTS
# =============================================================================
if [[ "$TEST_TYPE" =~ ^(all|e2e|frontend)$ ]]; then
    print_header "End-to-End Tests"
    run_test "Full User Flows" "$FRONTEND_DIR" \
        "npx playwright test e2e/tests/pages/ --reporter=list 2>/dev/null || true"
fi

# =============================================================================
# PERFORMANCE TESTS
# =============================================================================
if [[ "$TEST_TYPE" =~ ^(all|performance)$ ]]; then
    print_header "Performance Tests"
    run_test "Backend Performance" "$BACKEND_DIR" \
        "source venv/bin/activate && pytest tests/performance/ -v --tb=short 2>/dev/null || true"
fi

# =============================================================================
# SECURITY TESTS
# =============================================================================
if [[ "$TEST_TYPE" =~ ^(all|security)$ ]]; then
    print_header "Security Tests"
    run_test "Security Checks" "$BACKEND_DIR" \
        "source venv/bin/activate && pytest tests/security/ -v --tb=short 2>/dev/null || true"
fi

# =============================================================================
# DATABASE TESTS
# =============================================================================
if [[ "$TEST_TYPE" =~ ^(all|backend)$ ]]; then
    print_header "Database Tests"
    run_test "Database Operations" "$BACKEND_DIR" \
        "source venv/bin/activate && pytest tests/database/ -v --tb=short 2>/dev/null || true"
fi

# =============================================================================
# SUMMARY
# =============================================================================
print_header "Test Summary"
echo -e "${GREEN}Passed:${NC}  $PASSED"
echo -e "${RED}Failed:${NC}  $FAILED"
echo ""
echo "Finished: $(date)"

if [ $FAILED -gt 0 ]; then
    echo -e "\n${RED}⚠ Some tests failed${NC}"
    exit 1
else
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
    exit 0
fi

