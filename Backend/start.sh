#!/bin/bash
# ============================================================================
# MediaPoster Backend Startup Script
# ============================================================================
# This script:
# 1. Validates the Python environment
# 2. Activates the virtual environment
# 3. Runs environment health checks
# 4. Starts the backend server
# ============================================================================

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR"
VENV_DIR="$BACKEND_DIR/venv"

echo -e "${BOLD}${BLUE}============================================${NC}"
echo -e "${BOLD}${BLUE}  MediaPoster Backend Startup${NC}"
echo -e "${BOLD}${BLUE}============================================${NC}"
echo ""

# ============================================================================
# Step 1: Check Virtual Environment
# ============================================================================
echo -e "${BLUE}[1/4]${NC} Checking virtual environment..."

if [ ! -d "$VENV_DIR" ]; then
    echo -e "${RED}✗ Virtual environment not found at $VENV_DIR${NC}"
    echo -e "${YELLOW}  Creating virtual environment...${NC}"
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Verify we're in the venv
PYTHON_PATH=$(which python)
if [[ "$PYTHON_PATH" != *"$VENV_DIR"* ]]; then
    echo -e "${RED}✗ Failed to activate virtual environment${NC}"
    echo -e "${YELLOW}  Python path: $PYTHON_PATH${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Virtual environment activated${NC}"
echo -e "  Python: $(python --version)"
echo -e "  Path: $PYTHON_PATH"

# ============================================================================
# Step 2: Check Python Version
# ============================================================================
echo ""
echo -e "${BLUE}[2/4]${NC} Checking Python version..."

PYTHON_VERSION=$(python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PYTHON_MAJOR=$(python -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$(python -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo -e "${RED}✗ Python $PYTHON_VERSION is too old. Minimum: 3.11${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# ============================================================================
# Step 3: Run Environment Health Check
# ============================================================================
echo ""
echo -e "${BLUE}[3/4]${NC} Running environment health check..."

# Check if env_check.py exists
if [ -f "$BACKEND_DIR/scripts/env_check.py" ]; then
    # Run health check (non-blocking on warnings)
    if python "$BACKEND_DIR/scripts/env_check.py" --quiet; then
        echo -e "${GREEN}✓ Environment health check passed${NC}"
    else
        echo -e "${YELLOW}⚠ Environment has issues (see above)${NC}"
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${RED}Startup cancelled${NC}"
            exit 1
        fi
    fi
else
    echo -e "${YELLOW}⚠ Health check script not found, skipping...${NC}"
fi

# ============================================================================
# Step 4: Load Environment and Start Server
# ============================================================================
echo ""
echo -e "${BLUE}[4/4]${NC} Starting backend server..."

# Load .env file if exists
if [ -f "$BACKEND_DIR/.env" ]; then
    echo -e "  Loading .env file..."
    set -a
    source "$BACKEND_DIR/.env"
    set +a
fi

# Check if port 5555 is already in use
if lsof -Pi :5555 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠ Port 5555 is already in use${NC}"
    read -p "Kill existing process? (y/N) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        lsof -ti :5555 | xargs kill -9 2>/dev/null
        sleep 1
        echo -e "${GREEN}✓ Killed existing process${NC}"
    else
        echo -e "${RED}Cannot start - port in use${NC}"
        exit 1
    fi
fi

# Start the server
echo ""
echo -e "${GREEN}${BOLD}Starting uvicorn on http://localhost:5555${NC}"
echo -e "${BLUE}Press Ctrl+C to stop${NC}"
echo ""

cd "$BACKEND_DIR"
exec python -m uvicorn main:app --host 0.0.0.0 --port 5555 --reload