#!/bin/bash
# Quick start script for MediaPoster backend

echo "🚀 MediaPoster Backend - Quick Start"
echo "===================================="
echo ""

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

echo ""
echo "✅ Environment ready!"
echo ""
echo "Choose an option:"
echo "  1. Run interactive tests (recommended first time)"
echo "  2. Start API server"
echo "  3. Start API server with auto-reload (development)"
echo ""
read -p "Enter choice (1-3): " choice

# Function to kill process on port
kill_port() {
    PORT=$1
    PID=$(lsof -ti:$PORT)
    if [ ! -z "$PID" ]; then
        echo "⚠️  Port $PORT is in use by PID $PID. Killing it..."
        kill -9 $PID
        echo "✅ Port $PORT freed."
    fi
}

case $choice in
    1)
        echo ""
        echo "Starting interactive tests..."
        python3 test_local.py
        ;;
    2)
        echo ""
        echo "Starting API server..."
        kill_port 5555
        echo "Visit: http://localhost:5555/docs"
        uvicorn main:app --host 0.0.0.0 --port 5555
        ;;
    3)
        echo ""
        echo "Starting API server with auto-reload..."
        kill_port 5555
        echo "Visit: http://localhost:5555/docs"
        uvicorn main:app --host 0.0.0.0 --port 5555 --reload
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
