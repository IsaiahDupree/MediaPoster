#!/bin/bash
# Sora Service Test Runner
# 
# Usage:
#   ./run_sora_tests.sh          # Run all unit tests
#   ./run_sora_tests.sh --all    # Run all tests including integration
#   ./run_sora_tests.sh --int    # Run only integration tests (uses API credits!)
#   ./run_sora_tests.sh --install # Install/check dependencies

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$BACKEND_DIR/venv"

cd "$BACKEND_DIR"

echo "🧪 Sora Service Test Suite"
echo "=========================="

# =============================================================================
# Activate Virtual Environment
# =============================================================================
activate_venv() {
    if [ -d "$VENV_DIR" ]; then
        echo -e "${GREEN}✓ Found venv at $VENV_DIR${NC}"
        source "$VENV_DIR/bin/activate"
        echo -e "${GREEN}✓ Activated venv ($(python --version))${NC}"
    else
        echo -e "${YELLOW}⚠ No venv found. Creating...${NC}"
        python3 -m venv "$VENV_DIR"
        source "$VENV_DIR/bin/activate"
        echo -e "${GREEN}✓ Created and activated venv${NC}"
    fi
}

# =============================================================================
# Check and Install Dependencies
# =============================================================================
check_dependencies() {
    echo ""
    echo "Checking dependencies..."
    
    MISSING=()
    
    # Check pytest
    if ! python -c "import pytest" 2>/dev/null; then
        MISSING+=("pytest")
    fi
    
    # Check openai
    if ! python -c "import openai" 2>/dev/null; then
        MISSING+=("openai")
    fi
    
    # Check httpx
    if ! python -c "import httpx" 2>/dev/null; then
        MISSING+=("httpx")
    fi
    
    # Check pytest-asyncio
    if ! python -c "import pytest_asyncio" 2>/dev/null; then
        MISSING+=("pytest-asyncio")
    fi
    
    if [ ${#MISSING[@]} -gt 0 ]; then
        echo -e "${YELLOW}⚠ Missing packages: ${MISSING[*]}${NC}"
        echo "Installing..."
        pip install --quiet "${MISSING[@]}"
        echo -e "${GREEN}✓ Dependencies installed${NC}"
    else
        echo -e "${GREEN}✓ All dependencies present${NC}"
    fi
}

install_all_deps() {
    echo "Installing all test dependencies..."
    pip install --quiet pytest pytest-asyncio openai httpx python-dotenv
    echo -e "${GREEN}✓ All dependencies installed${NC}"
}

# =============================================================================
# Main
# =============================================================================

# Always activate venv first
activate_venv

# Load environment
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs) 2>/dev/null || true
fi

case "$1" in
    --install)
        install_all_deps
        check_dependencies
        exit 0
        ;;
    --all)
        check_dependencies
        echo ""
        echo "Running ALL tests (including integration - uses API credits!)"
        python -m pytest tests/test_sora_service.py -v --tb=short
        ;;
    --int|--integration)
        check_dependencies
        echo ""
        echo "Running INTEGRATION tests only (uses API credits!)"
        python -m pytest tests/test_sora_service.py -v -m integration --tb=short
        ;;
    --quick)
        check_dependencies
        echo ""
        echo "Running quick unit tests only"
        python -m pytest tests/test_sora_service.py -v -m "not integration" --tb=line -q
        ;;
    *)
        check_dependencies
        echo ""
        echo "Running unit tests (no API credits used)"
        python -m pytest tests/test_sora_service.py -v -m "not integration" --tb=short
        ;;
esac

echo ""
echo -e "${GREEN}✅ Tests completed!${NC}"
