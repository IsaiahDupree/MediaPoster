#!/usr/bin/env python3
"""
Robust Backend Runner
=====================
Runs the backend with:
- Signal handling for graceful shutdown
- Auto-restart on crash
- Health monitoring
- Detailed logging
"""

import asyncio
import os
import signal
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Configuration
MAX_RESTART_ATTEMPTS = 5
RESTART_DELAY_SECONDS = 3
HEALTH_CHECK_INTERVAL = 30
BACKEND_PORT = 5555

# State
restart_count = 0
last_restart_time = None
should_run = True
process = None


def log(level: str, message: str):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    symbol = {"INFO": "ℹ️", "WARN": "⚠️", "ERROR": "❌", "SUCCESS": "✅"}.get(level, "•")
    print(f"[{timestamp}] {symbol} {message}", flush=True)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    global should_run
    signal_name = signal.Signals(signum).name
    log("WARN", f"Received {signal_name} - initiating graceful shutdown...")
    should_run = False
    
    if process and process.poll() is None:
        log("INFO", "Sending SIGTERM to backend process...")
        process.terminate()
        try:
            process.wait(timeout=10)
            log("SUCCESS", "Backend process terminated gracefully")
        except subprocess.TimeoutExpired:
            log("WARN", "Backend didn't stop in time, sending SIGKILL...")
            process.kill()


def check_port_available():
    """Check if port is available, kill existing process if needed"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', BACKEND_PORT))
    sock.close()
    
    if result == 0:
        log("WARN", f"Port {BACKEND_PORT} is in use, attempting to free it...")
        os.system(f"lsof -ti :{BACKEND_PORT} | xargs kill -9 2>/dev/null")
        time.sleep(1)
        return False
    return True


def start_backend():
    """Start the backend process"""
    global process, restart_count, last_restart_time
    
    check_port_available()
    
    backend_dir = Path(__file__).parent
    venv_python = backend_dir / "venv" / "bin" / "python"
    main_py = backend_dir / "main.py"
    
    if not venv_python.exists():
        log("ERROR", f"Virtual environment not found: {venv_python}")
        return None
    
    log("INFO", f"Starting backend on port {BACKEND_PORT}...")
    
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"  # Ensure output is not buffered
    
    process = subprocess.Popen(
        [str(venv_python), str(main_py)],
        cwd=str(backend_dir),
        env=env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    
    restart_count += 1
    last_restart_time = datetime.now()
    
    log("SUCCESS", f"Backend started (PID: {process.pid}, restart #{restart_count})")
    return process


def health_check():
    """Check if backend is responding"""
    import urllib.request
    import urllib.error
    
    try:
        url = f"http://localhost:{BACKEND_PORT}/api/health/quick"
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status == 200
    except (urllib.error.URLError, Exception):
        return False


def main():
    global should_run, process, restart_count
    
    log("INFO", "=" * 60)
    log("INFO", "MediaPoster Backend Runner - Robust Mode")
    log("INFO", "=" * 60)
    log("INFO", f"Max restart attempts: {MAX_RESTART_ATTEMPTS}")
    log("INFO", f"Restart delay: {RESTART_DELAY_SECONDS}s")
    log("INFO", f"Health check interval: {HEALTH_CHECK_INTERVAL}s")
    log("INFO", "=" * 60)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start backend
    process = start_backend()
    if not process:
        log("ERROR", "Failed to start backend")
        sys.exit(1)
    
    # Wait for startup
    time.sleep(3)
    
    # Monitor loop
    last_health_check = time.time()
    consecutive_failures = 0
    
    while should_run:
        # Check if process is still running
        if process.poll() is not None:
            exit_code = process.returncode
            log("ERROR", f"Backend process exited with code {exit_code}")
            
            if restart_count >= MAX_RESTART_ATTEMPTS:
                log("ERROR", f"Max restart attempts ({MAX_RESTART_ATTEMPTS}) reached. Giving up.")
                should_run = False
                break
            
            log("INFO", f"Restarting in {RESTART_DELAY_SECONDS} seconds...")
            time.sleep(RESTART_DELAY_SECONDS)
            
            process = start_backend()
            if not process:
                log("ERROR", "Failed to restart backend")
                should_run = False
                break
            
            time.sleep(3)  # Wait for startup
            consecutive_failures = 0
        
        # Periodic health check
        if time.time() - last_health_check >= HEALTH_CHECK_INTERVAL:
            if health_check():
                consecutive_failures = 0
                log("INFO", f"Health check passed (uptime since last restart: {datetime.now() - last_restart_time})")
            else:
                consecutive_failures += 1
                log("WARN", f"Health check failed ({consecutive_failures} consecutive)")
                
                if consecutive_failures >= 3:
                    log("ERROR", "Too many health check failures, restarting backend...")
                    if process and process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
            
            last_health_check = time.time()
        
        time.sleep(1)
    
    log("INFO", "Backend runner shutting down")
    
    # Cleanup
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
    
    log("SUCCESS", "Shutdown complete")


if __name__ == "__main__":
    main()
