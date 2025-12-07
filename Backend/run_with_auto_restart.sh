#!/bin/bash
# Run backend with auto-restart on failure
# This script monitors the backend and restarts it if it crashes

cd "$(dirname "$0")"

echo "🔄 Starting Backend with Auto-Restart..."
echo "========================================"

# Configuration
MAX_RESTARTS=10
RESTART_DELAY=5
RESTART_COUNT=0
LOG_FILE="logs/auto_restart.log"

# Create logs directory
mkdir -p logs

# Function to log messages
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check if backend is healthy
check_health() {
    local response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5555/health 2>/dev/null)
    if [ "$response" = "200" ]; then
        return 0
    else
        return 1
    fi
}

# Function to start backend
start_backend() {
    log_message "Starting backend (attempt $((RESTART_COUNT + 1))/$MAX_RESTARTS)..."
    
    # Activate venv
    source venv/bin/activate
    
    # Start backend
    uvicorn main:app --host 0.0.0.0 --port 5555 --reload > logs/backend.log 2>&1 &
    local PID=$!
    
    # Wait for startup
    sleep 5
    
    # Check if process is still running
    if ! ps -p $PID > /dev/null 2>&1; then
        log_message "❌ Backend process died immediately"
        return 1
    fi
    
    # Check health
    local health_checks=0
    while [ $health_checks -lt 6 ]; do
        sleep 2
        if check_health; then
            log_message "✅ Backend is healthy (PID: $PID)"
            echo $PID > logs/backend.pid
            return 0
        fi
        health_checks=$((health_checks + 1))
    done
    
    log_message "⚠️  Backend started but health check failed"
    kill $PID 2>/dev/null
    return 1
}

# Main loop
while [ $RESTART_COUNT -lt $MAX_RESTARTS ]; do
    if start_backend; then
        # Monitor the process
        PID=$(cat logs/backend.pid 2>/dev/null)
        if [ -z "$PID" ]; then
            log_message "⚠️  Could not read PID, monitoring port instead"
            PID=$(lsof -ti:5555 2>/dev/null)
        fi
        
        if [ -z "$PID" ]; then
            log_message "❌ Could not find backend process"
            RESTART_COUNT=$((RESTART_COUNT + 1))
            sleep $RESTART_DELAY
            continue
        fi
        
        log_message "👀 Monitoring backend (PID: $PID)..."
        
        # Monitor process and health
        while ps -p $PID > /dev/null 2>&1; do
            sleep 10
            
            # Check health every 30 seconds
            if ! check_health; then
                log_message "⚠️  Health check failed, but process still running"
            fi
        done
        
        log_message "❌ Backend process died (PID: $PID)"
    else
        log_message "❌ Failed to start backend"
    fi
    
    RESTART_COUNT=$((RESTART_COUNT + 1))
    
    if [ $RESTART_COUNT -lt $MAX_RESTARTS ]; then
        log_message "⏳ Waiting $RESTART_DELAY seconds before restart..."
        sleep $RESTART_DELAY
    else
        log_message "❌ Max restarts ($MAX_RESTARTS) reached. Stopping."
        exit 1
    fi
done






