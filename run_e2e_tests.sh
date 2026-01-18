#!/bin/bash
# =============================================================================
# MediaPoster E2E Test Suite Runner
# =============================================================================
# Runs full E2E tests against both backend and frontend services.
#
# Usage:
#   ./run_e2e_tests.sh          # Run all E2E tests
#   ./run_e2e_tests.sh backend  # Run backend API tests only
#   ./run_e2e_tests.sh frontend # Run frontend Playwright tests only
#   ./run_e2e_tests.sh quick    # Quick smoke tests only
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:5555}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5557}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          MediaPoster E2E Test Suite                            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# =============================================================================
# Helper Functions
# =============================================================================

check_backend() {
    echo -e "${YELLOW}Checking backend at ${BACKEND_URL}...${NC}"
    if curl -s --max-time 5 "${BACKEND_URL}/api/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is running${NC}"
        return 0
    else
        echo -e "${RED}✗ Backend is not running at ${BACKEND_URL}${NC}"
        return 1
    fi
}

check_frontend() {
    echo -e "${YELLOW}Checking frontend at ${FRONTEND_URL}...${NC}"
    if curl -s --max-time 5 "${FRONTEND_URL}" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Frontend is running${NC}"
        return 0
    else
        echo -e "${RED}✗ Frontend is not running at ${FRONTEND_URL}${NC}"
        return 1
    fi
}

run_backend_tests() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Running Backend API E2E Tests${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    cd "${SCRIPT_DIR}/Backend"
    
    # Load environment
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs) 2>/dev/null || true
    fi
    
    # Activate venv if it exists
    VENV_DIR="${SCRIPT_DIR}/Backend/venv"
    if [ -d "$VENV_DIR" ]; then
        echo -e "${GREEN}✓ Using venv at $VENV_DIR${NC}"
        source "$VENV_DIR/bin/activate"
        
        # Check/install pytest and httpx
        if ! python -c "import pytest" 2>/dev/null; then
            echo -e "${YELLOW}Installing pytest...${NC}"
            pip install --quiet pytest pytest-asyncio
        fi
        if ! python -c "import httpx" 2>/dev/null; then
            echo -e "${YELLOW}Installing httpx...${NC}"
            pip install --quiet httpx
        fi
        
        python -m pytest tests/test_e2e_api.py -v --tb=short
    else
        echo -e "${YELLOW}⚠ No venv found, using system Python${NC}"
        python3 -m pytest tests/test_e2e_api.py -v --tb=short
    fi
    
    BACKEND_EXIT=$?
    return $BACKEND_EXIT
}

run_frontend_tests() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Running Frontend E2E Tests (Playwright)${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    cd "${SCRIPT_DIR}/dashboard"
    
    # Check if playwright is installed
    if ! npx playwright --version > /dev/null 2>&1; then
        echo -e "${YELLOW}Installing Playwright...${NC}"
        npm install -D @playwright/test
        npx playwright install chromium
    fi
    
    FRONTEND_URL="${FRONTEND_URL}" npx playwright test tests/e2e/ --reporter=list
    
    FRONTEND_EXIT=$?
    return $FRONTEND_EXIT
}

run_quick_tests() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  Running Quick Smoke Tests${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    PASSED=0
    FAILED=0
    
    # Backend health check
    echo -n "  Backend health check... "
    if curl -s "${BACKEND_URL}/api/health" | grep -q "healthy"; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILED++))
    fi
    
    # Media list endpoint
    echo -n "  Media list endpoint... "
    if curl -s "${BACKEND_URL}/api/media-db/list?limit=1" | grep -q "media_id"; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILED++))
    fi
    
    # Media stats endpoint
    echo -n "  Media stats endpoint... "
    if curl -s "${BACKEND_URL}/api/media-db/stats" | grep -q "total_videos"; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILED++))
    fi
    
    # Sora pipeline endpoint (returns array or object)
    echo -n "  Sora pipeline endpoint... "
    SORA_RESP=$(curl -s "${BACKEND_URL}/api/sora-pipeline/projects")
    if [ "$SORA_RESP" = "[]" ] || echo "$SORA_RESP" | grep -q "project_id\|projects"; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILED++))
    fi
    
    # Blotato accounts endpoint (returns array directly)
    echo -n "  Blotato accounts endpoint... "
    if curl -s "${BACKEND_URL}/api/blotato/accounts" | grep -q "platform"; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILED++))
    fi
    
    # TikTok repurpose status
    echo -n "  TikTok repurpose endpoint... "
    if curl -s "${BACKEND_URL}/api/repurpose/tiktok/status" | grep -q "service"; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILED++))
    fi
    
    # Frontend page load
    echo -n "  Frontend page load... "
    if curl -s "${FRONTEND_URL}" | grep -q "html"; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILED++))
    fi
    
    # Source type in media response
    echo -n "  Source type in API response... "
    if curl -s "${BACKEND_URL}/api/media-db/list?limit=1" | grep -q "source_type"; then
        echo -e "${GREEN}PASS${NC}"
        ((PASSED++))
    else
        echo -e "${RED}FAIL${NC}"
        ((FAILED++))
    fi
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  Results: ${GREEN}${PASSED} passed${NC}, ${RED}${FAILED} failed${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if [ $FAILED -gt 0 ]; then
        return 1
    fi
    return 0
}

# =============================================================================
# Main
# =============================================================================

case "$1" in
    backend)
        check_backend || exit 1
        run_backend_tests
        ;;
    frontend)
        check_frontend || exit 1
        run_frontend_tests
        ;;
    quick)
        check_backend || exit 1
        check_frontend || exit 1
        run_quick_tests
        ;;
    *)
        # Run all tests
        echo -e "${YELLOW}Running full E2E test suite...${NC}"
        echo ""
        
        BACKEND_OK=true
        FRONTEND_OK=true
        
        check_backend || BACKEND_OK=false
        check_frontend || FRONTEND_OK=false
        
        if [ "$BACKEND_OK" = false ] && [ "$FRONTEND_OK" = false ]; then
            echo -e "${RED}Neither backend nor frontend are running!${NC}"
            echo ""
            echo "Start services with:"
            echo "  Backend:  cd Backend && python3 main.py"
            echo "  Frontend: cd dashboard && npm run dev"
            exit 1
        fi
        
        TOTAL_EXIT=0
        
        if [ "$BACKEND_OK" = true ]; then
            run_backend_tests || TOTAL_EXIT=1
        fi
        
        if [ "$FRONTEND_OK" = true ]; then
            run_frontend_tests || TOTAL_EXIT=1
        fi
        
        echo ""
        echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
        if [ $TOTAL_EXIT -eq 0 ]; then
            echo -e "${BLUE}║${NC}  ${GREEN}✓ All E2E Tests Passed!${NC}                                      ${BLUE}║${NC}"
        else
            echo -e "${BLUE}║${NC}  ${RED}✗ Some E2E Tests Failed${NC}                                       ${BLUE}║${NC}"
        fi
        echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
        
        exit $TOTAL_EXIT
        ;;
esac
