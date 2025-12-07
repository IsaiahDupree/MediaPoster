#!/bin/bash
# Start Backend as a daemon (independent process)
# This ensures the backend won't be killed when the frontend stops

cd "$(dirname "$0")"

echo "🚀 Starting MediaPoster Backend as daemon..."
echo "============================================"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Kill any existing process on port 5555
PORT=5555
PID=$(lsof -ti:$PORT 2>/dev/null)
if [ ! -z "$PID" ]; then
    echo "⚠️  Port $PORT is in use by PID $PID. Killing it..."
    kill -9 $PID
    sleep 1
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Start backend in background with nohup (survives terminal closure)
echo "📡 Starting backend on port 5555..."
echo "📝 Logs: logs/backend.log"
echo "🔗 API: http://localhost:5555/docs"
echo ""
echo "To stop: ./stop_daemon.sh or kill \$(lsof -ti:5555)"

nohup uvicorn main:app --host 0.0.0.0 --port 5555 --reload > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Save PID to file for easy stopping
echo $BACKEND_PID > logs/backend.pid

# Wait a moment and check if it started
sleep 3
if ps -p $BACKEND_PID > /dev/null; then
    echo "✅ Backend started successfully (PID: $BACKEND_PID)"
    echo "📊 Check status: tail -f logs/backend.log"
else
    echo "❌ Backend failed to start. Check logs/backend.log"
    exit 1
fi






