#!/bin/bash
# Check Backend status

cd "$(dirname "$0")"

PORT=5555
PID_FILE="logs/backend.pid"

echo "🔍 Backend Status Check"
echo "======================"
echo ""

# Check if process is running on port
PID=$(lsof -ti:$PORT 2>/dev/null)
if [ ! -z "$PID" ]; then
    echo "✅ Backend is RUNNING"
    echo "   PID: $PID"
    echo "   Port: $PORT"
    echo "   URL: http://localhost:$PORT"
    echo "   Docs: http://localhost:$PORT/docs"
    echo ""
    
    # Check health endpoint
    echo "🏥 Health Check:"
    HEALTH=$(curl -s http://localhost:$PORT/health 2>/dev/null)
    if [ ! -z "$HEALTH" ]; then
        echo "   ✅ Backend is responding"
        echo "   Response: $HEALTH"
    else
        echo "   ⚠️  Backend is running but not responding"
    fi
    echo ""
    
    # Show recent logs
    if [ -f "logs/backend.log" ]; then
        echo "📝 Recent logs (last 5 lines):"
        tail -5 logs/backend.log
    fi
else
    echo "❌ Backend is NOT RUNNING"
    echo ""
    echo "To start: ./start_daemon.sh"
fi






