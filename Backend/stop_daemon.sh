#!/bin/bash
# Stop Backend daemon process

cd "$(dirname "$0")"

PORT=5555
PID_FILE="logs/backend.pid"

# Try to get PID from file first
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "🛑 Stopping backend (PID: $PID)..."
        kill $PID
        sleep 2
        # Force kill if still running
        if ps -p $PID > /dev/null 2>&1; then
            kill -9 $PID
        fi
        rm "$PID_FILE"
        echo "✅ Backend stopped"
    else
        echo "⚠️  PID from file not running, checking port..."
        rm "$PID_FILE"
    fi
fi

# Also check port directly
PID=$(lsof -ti:$PORT 2>/dev/null)
if [ ! -z "$PID" ]; then
    echo "🛑 Stopping process on port $PORT (PID: $PID)..."
    kill $PID 2>/dev/null
    sleep 1
    # Force kill if still running
    if lsof -ti:$PORT > /dev/null 2>&1; then
        kill -9 $PID 2>/dev/null
    fi
    echo "✅ Backend stopped"
else
    echo "ℹ️  No backend process found on port $PORT"
fi






