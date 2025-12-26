#!/bin/bash
# Graceful Backend Stop Script

PORT=5555
PID_FILE="/tmp/mediaposter_backend.pid"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if kill -0 $PID 2>/dev/null; then
        echo -e "${GREEN}🛑 Stopping backend (PID: $PID)...${NC}"
        kill $PID 2>/dev/null
        sleep 2
        # Force kill if still running
        if kill -0 $PID 2>/dev/null; then
            kill -9 $PID 2>/dev/null
        fi
        rm -f $PID_FILE
        echo -e "${GREEN}✅ Backend stopped${NC}"
    else
        echo -e "${RED}⚠️  Process not running${NC}"
        rm -f $PID_FILE
    fi
else
    # Fallback: kill by port
    if lsof -ti :$PORT > /dev/null 2>&1; then
        echo -e "${GREEN}🛑 Stopping processes on port $PORT...${NC}"
        lsof -ti :$PORT | xargs kill -9 2>/dev/null
        echo -e "${GREEN}✅ Backend stopped${NC}"
    else
        echo -e "${RED}⚠️  No backend running on port $PORT${NC}"
    fi
fi
