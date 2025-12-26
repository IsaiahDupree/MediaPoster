#!/bin/bash
# Robust Backend Startup Script
# Handles port conflicts, graceful shutdown, and logging

PORT=5555
LOG_FILE="/tmp/mediaposter_backend.log"
PID_FILE="/tmp/mediaposter_backend.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting MediaPoster Backend...${NC}"

# Kill any existing processes on the port
if lsof -ti :$PORT > /dev/null 2>&1; then
    echo -e "${YELLOW}⚠️  Port $PORT in use, cleaning up...${NC}"
    lsof -ti :$PORT | xargs kill -9 2>/dev/null
    sleep 2
fi

# Remove old PID file
rm -f $PID_FILE

# Activate virtual environment
cd "$(dirname "$0")"
source venv/bin/activate

# Start backend without reload mode for stability
echo -e "${GREEN}📝 Logging to $LOG_FILE${NC}"
echo "=== Backend started at $(date) ===" >> $LOG_FILE

# Run with nohup to survive terminal close, disable reload for stability
nohup python -c "
import uvicorn
import sys
sys.path.insert(0, '.')

# Import and run without reload for stability
from main import app
uvicorn.run(app, host='0.0.0.0', port=$PORT, log_level='info', reload=False)
" >> $LOG_FILE 2>&1 &

# Save PID
echo $! > $PID_FILE
sleep 3

# Verify it started
if curl -s --max-time 5 "http://localhost:$PORT/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Backend started successfully on port $PORT (PID: $(cat $PID_FILE))${NC}"
    echo -e "${GREEN}📊 Health check: http://localhost:$PORT/api/health${NC}"
else
    echo -e "${RED}❌ Backend failed to start. Check logs: $LOG_FILE${NC}"
    tail -20 $LOG_FILE
    exit 1
fi
