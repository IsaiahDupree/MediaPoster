#!/bin/bash
# Test connectivity to all microservices

echo "🔍 Testing MediaPoster Microservices Connectivity"
echo "=================================================="

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

test_service() {
    local name=$1
    local url=$2
    
    if curl -s "$url" > /dev/null 2>&1; then
        response=$(curl -s "$url")
        status=$(echo "$response" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
        if [ "$status" = "healthy" ]; then
            echo -e "${GREEN}✅ $name - HEALTHY${NC}"
            return 0
        else
            echo -e "${RED}❌ $name - UNHEALTHY (status: $status)${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ $name - DOWN (no response)${NC}"
        return 1
    fi
}

echo ""
echo "Testing services..."
echo ""

# Test each service
test_service "MediaPoster Core (:5555)" "http://localhost:5555/api/external/health"
test_service "Safari Automation (:6001)" "http://localhost:6001/health"
test_service "Remotion (:6002)" "http://localhost:6002/health"
test_service "Media Pipeline (:6004)" "http://localhost:6004/health"
test_service "Content Intelligence (:6006)" "http://localhost:6006/health"

echo ""
echo "=================================================="
echo "Test complete!"
