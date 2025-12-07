#!/bin/bash
# Restart Backend daemon
# Stops the current instance and starts a new one

cd "$(dirname "$0")"

echo "🔄 Restarting MediaPoster Backend..."
echo "===================================="

# Stop existing backend
if [ -f "stop_daemon.sh" ]; then
    ./stop_daemon.sh
else
    echo "⚠️  stop_daemon.sh not found, trying to kill process on port 5555..."
    PORT=5555
    PID=$(lsof -ti:$PORT 2>/dev/null)
    if [ ! -z "$PID" ]; then
        echo "Stopping process $PID..."
        kill $PID 2>/dev/null
        sleep 2
        # Force kill if still running
        if lsof -ti:$PORT > /dev/null 2>&1; then
            kill -9 $PID 2>/dev/null
        fi
    fi
fi

# Wait a moment for cleanup
sleep 2

# Start backend
if [ -f "start_daemon.sh" ]; then
    ./start_daemon.sh
else
    echo "❌ start_daemon.sh not found"
    exit 1
fi

echo ""
echo "✅ Backend restarted successfully"






