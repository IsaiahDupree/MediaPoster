#!/bin/bash
#
# MediaPoster Health Check Script
# Run before tests to ensure all services are ready
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BACKEND_URL="${BACKEND_URL:-http://localhost:5555}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5557}"
DATABASE_URL="${DATABASE_URL:-postgresql://postgres:postgres@127.0.0.1:54322/postgres}"

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  MediaPoster Health Check${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

PASSED=0
FAILED=0
WARNINGS=0

check_pass() {
    echo -e "  ${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "  ${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "  ${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

# ============================================================================
# 1. Check Backend Server
# ============================================================================
echo -e "${BLUE}Backend Server ($BACKEND_URL)${NC}"

# Check if process is running
if lsof -ti:5555 > /dev/null 2>&1; then
    check_pass "Process running on port 5555"
else
    check_fail "No process on port 5555"
fi

# Check HTTP response
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/docs" 2>/dev/null || echo "000")
if [ "$BACKEND_STATUS" = "200" ]; then
    check_pass "HTTP responding (status: $BACKEND_STATUS)"
else
    check_fail "HTTP not responding (status: $BACKEND_STATUS)"
fi

# Check API endpoint
API_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/api/social-analytics/overview" 2>/dev/null || echo "000")
if [ "$API_STATUS" = "200" ]; then
    check_pass "API endpoint responding (status: $API_STATUS)"
elif [ "$API_STATUS" = "500" ]; then
    check_warn "API endpoint returning 500 (database issue?)"
else
    check_fail "API endpoint not responding (status: $API_STATUS)"
fi

echo ""

# ============================================================================
# 2. Check Frontend Server
# ============================================================================
echo -e "${BLUE}Frontend Server ($FRONTEND_URL)${NC}"

# Check if process is running
if lsof -ti:5557 > /dev/null 2>&1; then
    check_pass "Process running on port 5557"
else
    check_fail "No process on port 5557"
fi

# Check HTTP response
FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL" 2>/dev/null || echo "000")
if [ "$FRONTEND_STATUS" = "200" ]; then
    check_pass "HTTP responding (status: $FRONTEND_STATUS)"
else
    check_fail "HTTP not responding (status: $FRONTEND_STATUS)"
fi

echo ""

# ============================================================================
# 3. Check Database
# ============================================================================
echo -e "${BLUE}Database Connection${NC}"

# Check if Supabase/PostgreSQL is running
if lsof -ti:54322 > /dev/null 2>&1; then
    check_pass "PostgreSQL process on port 54322"
else
    check_warn "No PostgreSQL on port 54322 (may be using remote DB)"
fi

# Try a simple database query via the API
DB_TEST=$(curl -s "$BACKEND_URL/api/social-analytics/accounts" 2>/dev/null)
if echo "$DB_TEST" | grep -q "error\|Error\|failed" 2>/dev/null; then
    check_warn "Database may have issues (check backend logs)"
else
    check_pass "Database queries working"
fi

echo ""

# ============================================================================
# 4. Check Dependencies
# ============================================================================
echo -e "${BLUE}Dependencies${NC}"

# Check Node.js
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    check_pass "Node.js installed ($NODE_VERSION)"
else
    check_fail "Node.js not installed"
fi

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    check_pass "Python installed ($PYTHON_VERSION)"
else
    check_fail "Python not installed"
fi

# Check Playwright
if [ -d "Frontend/node_modules/@playwright" ]; then
    check_pass "Playwright installed"
else
    check_warn "Playwright may not be installed"
fi

echo ""

# ============================================================================
# 5. Quick API Diagnostics
# ============================================================================
echo -e "${BLUE}API Endpoint Diagnostics${NC}"

ENDPOINTS=(
    "/api/social-analytics/overview"
    "/api/social-analytics/accounts"
    "/api/videos"
    "/api/goals"
    "/api/publishing/scheduled"
)

for endpoint in "${ENDPOINTS[@]}"; do
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL$endpoint" 2>/dev/null || echo "000")
    RESPONSE_TIME=$(curl -s -o /dev/null -w "%{time_total}" "$BACKEND_URL$endpoint" 2>/dev/null || echo "0")
    
    if [ "$STATUS" = "200" ]; then
        echo -e "  ${GREEN}✓${NC} $endpoint (${STATUS}, ${RESPONSE_TIME}s)"
    elif [ "$STATUS" = "500" ]; then
        echo -e "  ${YELLOW}⚠${NC} $endpoint (${STATUS} - server error)"
    else
        echo -e "  ${RED}✗${NC} $endpoint (${STATUS})"
    fi
done

echo ""

# ============================================================================
# Summary
# ============================================================================
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "  ${GREEN}Passed:${NC}   $PASSED"
echo -e "  ${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "  ${RED}Failed:${NC}   $FAILED"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"

if [ $FAILED -gt 0 ]; then
    echo -e "\n${RED}Health check failed. Fix issues before running tests.${NC}"
    echo ""
    echo "To start servers:"
    echo "  Backend:  cd Backend && source venv/bin/activate && uvicorn main:app --port 5555 --reload"
    echo "  Frontend: cd Frontend && npm run dev"
    exit 1
elif [ $WARNINGS -gt 0 ]; then
    echo -e "\n${YELLOW}Health check passed with warnings. Tests may have issues.${NC}"
    exit 0
else
    echo -e "\n${GREEN}All health checks passed! Ready for testing.${NC}"
    exit 0
fi
