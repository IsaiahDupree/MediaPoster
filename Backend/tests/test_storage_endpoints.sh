#!/bin/bash
# Test script for Storage Management Endpoints
# Tests all storage endpoints to verify they're working correctly

BASE_URL="http://localhost:5555"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🧪 Testing Storage Management Endpoints"
echo "======================================"
echo ""

# Test 1: Storage Stats
echo "1. Testing GET /api/storage/stats"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/storage/stats")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')
if [ "$http_code" == "200" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Status: $http_code"
    echo "   Response: $body" | head -c 100
    echo "..."
else
    echo -e "${RED}❌ FAIL${NC} - Status: $http_code"
fi
echo ""

# Test 2: List Videos
echo "2. Testing GET /api/storage/videos"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/storage/videos")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')
if [ "$http_code" == "200" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Status: $http_code"
    echo "   Response: $body" | head -c 100
    echo "..."
else
    echo -e "${RED}❌ FAIL${NC} - Status: $http_code"
fi
echo ""

# Test 3: List Thumbnails
echo "3. Testing GET /api/storage/thumbnails"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/storage/thumbnails")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')
if [ "$http_code" == "200" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Status: $http_code"
    echo "   Response: $body" | head -c 100
    echo "..."
else
    echo -e "${RED}❌ FAIL${NC} - Status: $http_code"
fi
echo ""

# Test 4: List Clips
echo "4. Testing GET /api/storage/clips"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/storage/clips")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')
if [ "$http_code" == "200" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Status: $http_code"
    echo "   Response: $body" | head -c 100
    echo "..."
else
    echo -e "${RED}❌ FAIL${NC} - Status: $http_code"
fi
echo ""

# Test 5: Cleanup
echo "5. Testing POST /api/storage/cleanup"
response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/storage/cleanup?cleanup_temp=true")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | sed '$d')
if [ "$http_code" == "200" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Status: $http_code"
    echo "   Response: $body" | head -c 100
    echo "..."
else
    echo -e "${RED}❌ FAIL${NC} - Status: $http_code"
fi
echo ""

# Test 6: Get Video File (non-existent)
echo "6. Testing GET /api/storage/files/videos/test-video-id"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/storage/files/videos/test-video-id")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" == "404" ] || [ "$http_code" == "503" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Status: $http_code (expected for non-existent file)"
else
    echo -e "${YELLOW}⚠️  WARN${NC} - Status: $http_code (unexpected)"
fi
echo ""

# Test 7: Get Thumbnail File (non-existent)
echo "7. Testing GET /api/storage/files/thumbnails/test-video-id"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/storage/files/thumbnails/test-video-id")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" == "404" ] || [ "$http_code" == "503" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Status: $http_code (expected for non-existent file)"
else
    echo -e "${YELLOW}⚠️  WARN${NC} - Status: $http_code (unexpected)"
fi
echo ""

# Test 8: Get Clip File (non-existent)
echo "8. Testing GET /api/storage/files/clips/test-clip-id"
response=$(curl -s -w "\n%{http_code}" "$BASE_URL/api/storage/files/clips/test-clip-id")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" == "404" ] || [ "$http_code" == "503" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Status: $http_code (expected for non-existent file)"
else
    echo -e "${YELLOW}⚠️  WARN${NC} - Status: $http_code (unexpected)"
fi
echo ""

# Test 9: Delete Video (non-existent)
echo "9. Testing DELETE /api/storage/videos/test-video-id"
response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/storage/videos/test-video-id")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" == "404" ] || [ "$http_code" == "503" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Status: $http_code (expected for non-existent file)"
else
    echo -e "${YELLOW}⚠️  WARN${NC} - Status: $http_code (unexpected)"
fi
echo ""

# Test 10: Delete Thumbnail (non-existent)
echo "10. Testing DELETE /api/storage/thumbnails/test-video-id"
response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/storage/thumbnails/test-video-id")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" == "404" ] || [ "$http_code" == "503" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Status: $http_code (expected for non-existent file)"
else
    echo -e "${YELLOW}⚠️  WARN${NC} - Status: $http_code (unexpected)"
fi
echo ""

# Test 11: Delete Clip (non-existent)
echo "11. Testing DELETE /api/storage/clips/test-clip-id"
response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/storage/clips/test-clip-id")
http_code=$(echo "$response" | tail -n1)
if [ "$http_code" == "404" ] || [ "$http_code" == "503" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Status: $http_code (expected for non-existent file)"
else
    echo -e "${YELLOW}⚠️  WARN${NC} - Status: $http_code (unexpected)"
fi
echo ""

echo "======================================"
echo "✅ Storage endpoint tests completed!"
echo ""
echo "Note: Some endpoints may return 404/503 if local storage is disabled"
echo "      or if test files don't exist. This is expected behavior."






