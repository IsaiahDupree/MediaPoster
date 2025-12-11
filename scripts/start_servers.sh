#!/bin/bash
# Start both Frontend and Backend servers in separate Terminal windows

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Load environment variables
source "$PROJECT_ROOT/Backend/.env" 2>/dev/null || true
source "$PROJECT_ROOT/dashboard/.env.local" 2>/dev/null || true

BACKEND_PORT="${BACKEND_PORT:-5555}"
FRONTEND_PORT="${PORT:-5557}"

echo "=== MediaPoster Server Startup ==="
echo "Backend Port: $BACKEND_PORT"
echo "Frontend Port: $FRONTEND_PORT"
echo ""

# Start Backend in new Terminal
osascript -e "
tell application \"Terminal\"
    do script \"cd '$PROJECT_ROOT/Backend' && source venv/bin/activate && echo '🚀 Starting Backend on port $BACKEND_PORT...' && uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --reload\"
    set custom title of front window to \"MediaPoster Backend :$BACKEND_PORT\"
end tell
"

# Wait a moment before starting frontend
sleep 2

# Start Frontend in new Terminal
osascript -e "
tell application \"Terminal\"
    do script \"cd '$PROJECT_ROOT/dashboard' && echo '🚀 Starting Frontend on port $FRONTEND_PORT...' && PORT=$FRONTEND_PORT npm run dev\"
    set custom title of front window to \"MediaPoster Frontend :$FRONTEND_PORT\"
end tell
"

echo "✓ Servers starting in separate Terminal windows"
echo ""
echo "Backend: http://localhost:$BACKEND_PORT"
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo ""
echo "API Docs: http://localhost:$BACKEND_PORT/docs"
