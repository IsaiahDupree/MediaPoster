#!/bin/bash
# Comprehensive Service Test Suite
# Tests all backend services using curl

API_URL="http://localhost:5555"
PASSED=0
FAILED=0
TOTAL=0

echo ""
echo "=================================================================================="
echo "🚀 COMPREHENSIVE SERVICE TEST SUITE"
echo "=================================================================================="
echo ""

test_service() {
    local name=$1
    local endpoint=$2
    local method=${3:-GET}
    
    TOTAL=$((TOTAL + 1))
    echo ""
    echo "=================================================================================="
    echo "🧪 Testing: $name"
    echo "=================================================================================="
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$API_URL$endpoint" 2>&1)
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_URL$endpoint" 2>&1)
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo "✅ PASS: $name (HTTP $http_code)"
        if [ -n "$body" ] && [ "$body" != "null" ]; then
            # Try to extract useful info from JSON
            if echo "$body" | python3 -m json.tool > /dev/null 2>&1; then
                echo "   Response: $(echo "$body" | python3 -c "import sys, json; d=json.load(sys.stdin); print(json.dumps(d, indent=2)[:200])" 2>/dev/null || echo "Valid JSON")"
            fi
        fi
        PASSED=$((PASSED + 1))
        return 0
    else
        echo "❌ FAIL: $name (HTTP $http_code)"
        echo "   Response: ${body:0:200}"
        FAILED=$((FAILED + 1))
        return 1
    fi
}

# Test all services
test_service "Health Check" "/health"
test_service "Media List" "/api/media-db/list?limit=10"
test_service "Media Stats" "/api/media-db/stats"
test_service "Social Accounts" "/api/social/accounts"
test_service "Scheduled Posts" "/api/schedule/list?limit=10"
test_service "Narrative Goals" "/api/narrative/goals"
test_service "Experiments" "/api/experiments/list"
test_service "App Validation" "/api/app-validation/health-check"
test_service "Analysis Status" "/api/media-db/analysis-status"
test_service "Backup Stats" "/api/backup/stats"
test_service "Ingestion Status" "/api/ingestion/status"

# Print summary
echo ""
echo "=================================================================================="
echo "📊 TEST SUMMARY"
echo "=================================================================================="
echo ""
echo "Results: $PASSED/$TOTAL tests passed"
echo ""

if [ $FAILED -eq 0 ]; then
    echo "✅ All tests passed!"
    exit 0
else
    echo "❌ $FAILED test(s) failed"
    exit 1
fi

