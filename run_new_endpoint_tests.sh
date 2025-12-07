#!/bin/bash
# Run tests for new endpoints on both backend and frontend

set -e

echo "=========================================="
echo "Running New Endpoint Tests"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Backend Tests
echo -e "${BLUE}=== Backend Tests ===${NC}"
echo "Running backend integration tests..."
echo ""

cd Backend
if [ -d "venv" ]; then
    source venv/bin/activate
    python -m pytest tests/integration/test_new_endpoints_real_data.py \
        tests/integration/test_endpoints_with_real_video_data.py \
        tests/integration/test_with_real_video_files.py \
        -v --tb=short
    BACKEND_EXIT=$?
else
    echo -e "${YELLOW}Warning: venv not found, trying without it${NC}"
    python3 -m pytest tests/integration/test_new_endpoints_real_data.py \
        tests/integration/test_endpoints_with_real_video_data.py \
        tests/integration/test_with_real_video_files.py \
        -v --tb=short
    BACKEND_EXIT=$?
fi
cd ..

echo ""
echo -e "${BLUE}=== Frontend Tests ===${NC}"
echo "Running frontend E2E tests..."
echo ""

cd Frontend
if [ -f "package.json" ]; then
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}Installing dependencies...${NC}"
        npm install
    fi
    
    # Run the new endpoint tests
    npm run test:e2e -- e2e/tests/api/new-endpoints-real-data.spec.ts e2e/tests/api/real-video-data.spec.ts
    FRONTEND_EXIT=$?
else
    echo -e "${YELLOW}Warning: Frontend package.json not found${NC}"
    FRONTEND_EXIT=1
fi
cd ..

echo ""
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="

if [ $BACKEND_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓ Backend tests passed${NC}"
else
    echo -e "${YELLOW}✗ Backend tests failed (exit code: $BACKEND_EXIT)${NC}"
fi

if [ $FRONTEND_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓ Frontend tests passed${NC}"
else
    echo -e "${YELLOW}✗ Frontend tests failed (exit code: $FRONTEND_EXIT)${NC}"
fi

echo ""

# Exit with error if any tests failed
if [ $BACKEND_EXIT -ne 0 ] || [ $FRONTEND_EXIT -ne 0 ]; then
    exit 1
else
    exit 0
fi






