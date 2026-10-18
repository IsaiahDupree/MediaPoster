#!/bin/bash
# Start all MediaPoster microservices

echo "🚀 Starting MediaPoster Microservices..."
echo "=========================================="

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# Base directory
BASE_DIR="$HOME/Documents/Software"

# Function to start a service
start_service() {
    local name=$1
    local dir=$2
    local cmd=$3
    local port=$4
    
    echo -e "${BLUE}Starting $name on port $port...${NC}"
    cd "$dir" || { echo "❌ Directory $dir not found"; return 1; }
    
    # Check if already running
    if lsof -i ":$port" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $name already running on port $port${NC}"
        return 0
    fi
    
    # Start in background
    nohup $cmd > "/tmp/${name}.log" 2>&1 &
    sleep 2
    
    if lsof -i ":$port" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ $name started on port $port${NC}"
    else
        echo "❌ Failed to start $name"
        tail -5 "/tmp/${name}.log"
    fi
}

# Start services
echo ""
echo "Starting services..."
echo ""

# Media Pipeline
start_service "media-pipeline" "$BASE_DIR/media-pipeline" "python app.py" 6004

# Content Intelligence
start_service "content-intelligence" "$BASE_DIR/content-intelligence" "python app.py" 6006

# MediaPoster Core (optional - might already be running)
# start_service "mediaposter" "$BASE_DIR/MediaPoster/Backend" "python main.py" 5555

echo ""
echo "=========================================="
echo "Services started! Logs in /tmp/"
echo ""
echo "Test connectivity:"
echo "  curl http://localhost:6004/health"
echo "  curl http://localhost:6006/health"
