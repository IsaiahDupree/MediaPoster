#!/usr/bin/env python3
"""
Server Manager - Health checks and auto-start for Frontend and Backend servers
"""
import os
import sys
import time
import subprocess
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
PROJECT_ROOT = Path(__file__).parent.parent
BACKEND_DIR = PROJECT_ROOT / "Backend"
FRONTEND_DIR = PROJECT_ROOT / "dashboard"

# Load .env files
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(FRONTEND_DIR / ".env.local")

# Server configuration
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "5555"))
BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", os.getenv("PORT", "5557")))

BACKEND_URL = f"http://localhost:{BACKEND_PORT}"
FRONTEND_URL = f"http://localhost:{FRONTEND_PORT}"


def check_server_health(url: str, timeout: float = 5.0) -> bool:
    """Check if a server is healthy by making a request."""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code < 500
    except requests.exceptions.ConnectionError:
        return False
    except requests.exceptions.Timeout:
        return False
    except Exception:
        return False


def check_backend_health() -> bool:
    """Check if the backend server is healthy."""
    # Try health endpoint first, then root
    for endpoint in ["/health", "/api/health", "/docs", "/"]:
        if check_server_health(f"{BACKEND_URL}{endpoint}"):
            return True
    return False


def check_frontend_health() -> bool:
    """Check if the frontend server is healthy."""
    return check_server_health(FRONTEND_URL)


def is_port_in_use(port: int) -> bool:
    """Check if a port is in use."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0


def start_backend_server(terminal: bool = True) -> subprocess.Popen | None:
    """Start the backend server."""
    if is_port_in_use(BACKEND_PORT):
        print(f"Backend port {BACKEND_PORT} already in use")
        return None
    
    venv_python = BACKEND_DIR / "venv" / "bin" / "python"
    if not venv_python.exists():
        venv_python = "python"
    
    cmd = [
        str(venv_python), "-m", "uvicorn",
        "main:app",
        "--host", BACKEND_HOST,
        "--port", str(BACKEND_PORT),
        "--reload"
    ]
    
    if terminal:
        # Start in a new Terminal window (macOS)
        script = f'''
        tell application "Terminal"
            do script "cd {BACKEND_DIR} && source venv/bin/activate && uvicorn main:app --host {BACKEND_HOST} --port {BACKEND_PORT} --reload"
            activate
        end tell
        '''
        subprocess.run(["osascript", "-e", script])
        return None
    else:
        return subprocess.Popen(
            cmd,
            cwd=BACKEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )


def start_frontend_server(terminal: bool = True) -> subprocess.Popen | None:
    """Start the frontend server."""
    if is_port_in_use(FRONTEND_PORT):
        print(f"Frontend port {FRONTEND_PORT} already in use")
        return None
    
    if terminal:
        # Start in a new Terminal window (macOS)
        script = f'''
        tell application "Terminal"
            do script "cd {FRONTEND_DIR} && PORT={FRONTEND_PORT} npm run dev"
            activate
        end tell
        '''
        subprocess.run(["osascript", "-e", script])
        return None
    else:
        env = os.environ.copy()
        env["PORT"] = str(FRONTEND_PORT)
        return subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=FRONTEND_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )


def wait_for_server(check_func, name: str, timeout: int = 30) -> bool:
    """Wait for a server to become healthy."""
    print(f"Waiting for {name} to start...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        if check_func():
            print(f"✓ {name} is healthy")
            return True
        time.sleep(1)
    print(f"✗ {name} failed to start within {timeout}s")
    return False


def ensure_servers_running(use_terminals: bool = True) -> dict:
    """Ensure both servers are running, start them if needed."""
    status = {
        "backend": {"healthy": False, "started": False},
        "frontend": {"healthy": False, "started": False}
    }
    
    # Check backend
    if check_backend_health():
        print(f"✓ Backend already running at {BACKEND_URL}")
        status["backend"]["healthy"] = True
    else:
        print(f"Starting backend server on port {BACKEND_PORT}...")
        start_backend_server(terminal=use_terminals)
        status["backend"]["started"] = True
        if wait_for_server(check_backend_health, "Backend", timeout=30):
            status["backend"]["healthy"] = True
    
    # Check frontend
    if check_frontend_health():
        print(f"✓ Frontend already running at {FRONTEND_URL}")
        status["frontend"]["healthy"] = True
    else:
        print(f"Starting frontend server on port {FRONTEND_PORT}...")
        start_frontend_server(terminal=use_terminals)
        status["frontend"]["started"] = True
        if wait_for_server(check_frontend_health, "Frontend", timeout=30):
            status["frontend"]["healthy"] = True
    
    return status


def get_server_status() -> dict:
    """Get current server status."""
    return {
        "backend": {
            "url": BACKEND_URL,
            "port": BACKEND_PORT,
            "healthy": check_backend_health(),
            "port_in_use": is_port_in_use(BACKEND_PORT)
        },
        "frontend": {
            "url": FRONTEND_URL,
            "port": FRONTEND_PORT,
            "healthy": check_frontend_health(),
            "port_in_use": is_port_in_use(FRONTEND_PORT)
        }
    }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="MediaPoster Server Manager")
    parser.add_argument("command", choices=["status", "start", "check"], 
                       help="Command to run")
    parser.add_argument("--no-terminal", action="store_true",
                       help="Start servers in background (not in new terminals)")
    
    args = parser.parse_args()
    
    if args.command == "status":
        status = get_server_status()
        print("\n=== Server Status ===")
        for name, info in status.items():
            health = "✓ Healthy" if info["healthy"] else "✗ Not responding"
            port_status = "in use" if info["port_in_use"] else "free"
            print(f"{name.capitalize()}: {info['url']} - {health} (port {port_status})")
    
    elif args.command == "start":
        ensure_servers_running(use_terminals=not args.no_terminal)
    
    elif args.command == "check":
        status = get_server_status()
        all_healthy = all(s["healthy"] for s in status.values())
        sys.exit(0 if all_healthy else 1)
