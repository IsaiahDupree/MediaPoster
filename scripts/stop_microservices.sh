#!/bin/bash
# Stop all MediaPoster microservices

echo "🛑 Stopping MediaPoster Microservices..."
echo "=========================================="

# Function to stop service on port
stop_port() {
    local port=$1
    local name=$2
    
    pid=$(lsof -ti ":$port" 2>/dev/null)
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null
        echo "✓ Stopped $name (port $port, pid $pid)"
    else
        echo "- $name not running (port $port)"
    fi
}

stop_port 6004 "media-pipeline"
stop_port 6006 "content-intelligence"

echo ""
echo "Done!"
