#!/bin/bash
# Comprehensive Analysis Service Test
# Tests the analysis service to ensure it works correctly

API_URL="http://localhost:5555"
TIMEOUT=300

echo ""
echo "=================================================================================="
echo "🧪 COMPREHENSIVE ANALYSIS SERVICE TEST"
echo "=================================================================================="
echo ""

# Step 1: Get a video that needs analysis
echo "📋 Step 1: Finding unanalyzed video..."
VIDEO_LIST=$(curl -s "$API_URL/api/media-db/list?limit=10")

if [ $? -ne 0 ]; then
    echo "❌ Failed to list videos"
    exit 1
fi

# Extract first video ID
VIDEO_ID=$(echo "$VIDEO_LIST" | python3 -c "import sys, json; d=json.load(sys.stdin); videos=d.get('media', []); print(videos[0].get('media_id') or videos[0].get('id', '')) if videos else print('')" 2>/dev/null)

if [ -z "$VIDEO_ID" ]; then
    echo "❌ No videos found"
    exit 1
fi

FILENAME=$(echo "$VIDEO_LIST" | python3 -c "import sys, json; d=json.load(sys.stdin); videos=d.get('media', []); print(videos[0].get('filename', 'unknown')) if videos else print('unknown')" 2>/dev/null)

echo "✅ Found test video: $VIDEO_ID"
echo "   Filename: $FILENAME"

# Step 2: Check current analysis status
echo ""
echo "📊 Step 2: Checking current analysis status..."
ANALYSIS=$(curl -s "$API_URL/api/media-db/analysis/$VIDEO_ID")

if echo "$ANALYSIS" | python3 -m json.tool > /dev/null 2>&1; then
    TRANSCRIPT=$(echo "$ANALYSIS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('transcript', '')))" 2>/dev/null || echo "0")
    TOPICS=$(echo "$ANALYSIS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('topics', [])))" 2>/dev/null || echo "0")
    SCORE=$(echo "$ANALYSIS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('pre_social_score', 'N/A'))" 2>/dev/null || echo "N/A")
    
    echo "   Transcript: $TRANSCRIPT chars"
    echo "   Topics: $TOPICS items"
    echo "   Score: $SCORE"
else
    echo "   No analysis found"
fi

# Step 3: Start analysis
echo ""
echo "🚀 Step 3: Starting analysis..."
START_TIME=$(date +%s)
ANALYZE_RESPONSE=$(curl -s -X POST "$API_URL/api/media-db/analyze/$VIDEO_ID?force=true")

if echo "$ANALYZE_RESPONSE" | python3 -m json.tool > /dev/null 2>&1; then
    STATUS=$(echo "$ANALYZE_RESPONSE" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('status', 'unknown'))" 2>/dev/null || echo "unknown")
    echo "✅ Analysis started: $STATUS"
else
    echo "❌ Failed to start analysis"
    exit 1
fi

# Step 4: Poll for completion
echo ""
echo "⏳ Step 4: Waiting for analysis to complete..."
echo "   (This may take 1-5 minutes depending on video length)"
MAX_WAIT=$TIMEOUT
POLL_INTERVAL=3
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    sleep $POLL_INTERVAL
    ELAPSED=$((ELAPSED + POLL_INTERVAL))
    
    ANALYSIS=$(curl -s "$API_URL/api/media-db/analysis/$VIDEO_ID")
    if echo "$ANALYSIS" | python3 -m json.tool > /dev/null 2>&1; then
        TRANSCRIPT=$(echo "$ANALYSIS" | python3 -c "import sys, json; d=json.load(sys.stdin); t=d.get('transcript', ''); print('1' if t and len(t) > 10 else '0')" 2>/dev/null || echo "0")
        TOPICS=$(echo "$ANALYSIS" | python3 -c "import sys, json; d=json.load(sys.stdin); t=d.get('topics', []); print('1' if t and len(t) > 0 else '0')" 2>/dev/null || echo "0")
        SCORE=$(echo "$ANALYSIS" | python3 -c "import sys, json; d=json.load(sys.stdin); print('1' if d.get('pre_social_score') is not None else '0')" 2>/dev/null || echo "0")
        
        if [ "$TRANSCRIPT" = "1" ] && [ "$TOPICS" = "1" ] && [ "$SCORE" = "1" ]; then
            END_TIME=$(date +%s)
            DURATION=$((END_TIME - START_TIME))
            echo ""
            echo "✅ Analysis completed in $DURATION seconds!"
            break
        fi
        
        if [ $((ELAPSED % 15)) -eq 0 ]; then
            echo "   [${ELAPSED}s] Still analyzing... transcript=$TRANSCRIPT, topics=$TOPICS, score=$SCORE"
        fi
    fi
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo ""
    echo "⏱️  Timeout after $MAX_WAIT seconds"
    exit 1
fi

# Step 5: Verify final analysis
echo ""
echo "🔍 Step 5: Verifying final analysis..."
FINAL_ANALYSIS=$(curl -s "$API_URL/api/media-db/analysis/$VIDEO_ID")

if echo "$FINAL_ANALYSIS" | python3 -m json.tool > /dev/null 2>&1; then
    TRANSCRIPT=$(echo "$FINAL_ANALYSIS" | python3 -c "import sys, json; d=json.load(sys.stdin); t=d.get('transcript', ''); print(len(t))" 2>/dev/null || echo "0")
    TOPICS=$(echo "$FINAL_ANALYSIS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d.get('topics', [])))" 2>/dev/null || echo "0")
    SCORE=$(echo "$FINAL_ANALYSIS" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('pre_social_score', 'N/A'))" 2>/dev/null || echo "N/A")
    
    echo "   Transcript: $TRANSCRIPT chars"
    echo "   Topics: $TOPICS items"
    echo "   Score: $SCORE"
    
    if [ "$TRANSCRIPT" -gt 10 ] && [ "$TOPICS" -gt 0 ] && [ "$SCORE" != "N/A" ]; then
        echo ""
        echo "✅ SUCCESS: Analysis is complete!"
        exit 0
    else
        echo ""
        echo "❌ ANALYSIS INCOMPLETE"
        exit 1
    fi
else
    echo "❌ Failed to get final analysis"
    exit 1
fi

