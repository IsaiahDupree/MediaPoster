#!/usr/bin/env python3
"""
Startup checks for MediaPoster Backend
Ensures PostgreSQL database is running before the app starts.
"""

import subprocess
import sys
import time
import socket
import os
from pathlib import Path

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


def parse_database_url():
    """Parse DATABASE_URL to extract host and port"""
    db_url = os.getenv("DATABASE_URL", "postgresql://localhost:5432/postgres")
    
    # Parse postgresql://user:pass@host:port/dbname
    try:
        if "@" in db_url:
            host_part = db_url.split("@")[1].split("/")[0]
        else:
            host_part = db_url.split("://")[1].split("/")[0]
        
        if ":" in host_part:
            host, port = host_part.rsplit(":", 1)
            port = int(port)
        else:
            host = host_part
            port = 5432
        
        return host, port
    except Exception:
        return "localhost", 5432


def check_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a port is open and accepting connections"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def check_postgres_running(host: str = "localhost", port: int = 5432) -> bool:
    """Check if PostgreSQL is running and accepting connections"""
    return check_port_open(host, port)


def start_postgres_brew() -> bool:
    """Start PostgreSQL via Homebrew services (macOS)"""
    print("🔄 Starting PostgreSQL via Homebrew...")
    try:
        result = subprocess.run(
            ["brew", "services", "start", "postgresql@16"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            print("✓ PostgreSQL service started")
            return True
        else:
            # Try without version
            result = subprocess.run(
                ["brew", "services", "start", "postgresql"],
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.returncode == 0
    except FileNotFoundError:
        print("  Homebrew not found")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def start_postgres_docker() -> bool:
    """Start PostgreSQL via Docker"""
    print("🔄 Starting PostgreSQL via Docker...")
    try:
        # Check if docker is available
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=10)
        if result.returncode != 0:
            print("  Docker not running, attempting to start...")
            # Try to start Docker Desktop on macOS
            subprocess.run(["open", "-a", "Docker"], capture_output=True)
            time.sleep(10)  # Wait for Docker to start
        
        # Check if postgres container exists
        result = subprocess.run(
            ["docker", "ps", "-a", "--filter", "name=mediaposter-postgres", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if "mediaposter-postgres" in result.stdout:
            # Container exists, start it
            print("  Starting existing container...")
            subprocess.run(
                ["docker", "start", "mediaposter-postgres"],
                capture_output=True,
                timeout=30
            )
        else:
            # Create new container
            print("  Creating new PostgreSQL container...")
            subprocess.run([
                "docker", "run", "-d",
                "--name", "mediaposter-postgres",
                "-e", "POSTGRES_USER=postgres",
                "-e", "POSTGRES_PASSWORD=postgres",
                "-e", "POSTGRES_DB=postgres",
                "-p", "5432:5432",
                "postgres:16-alpine"
            ], capture_output=True, timeout=60)
        
        return True
    except FileNotFoundError:
        print("  Docker not found")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def start_postgres_systemd() -> bool:
    """Start PostgreSQL via systemd (Linux)"""
    print("🔄 Starting PostgreSQL via systemd...")
    try:
        result = subprocess.run(
            ["sudo", "systemctl", "start", "postgresql"],
            capture_output=True,
            timeout=30
        )
        return result.returncode == 0
    except Exception:
        return False


def ensure_postgres_running(max_retries: int = 3, wait_seconds: int = 5) -> bool:
    """
    Ensure PostgreSQL is running, attempting to start it if not.
    
    Returns True if PostgreSQL is running, False otherwise.
    """
    host, port = parse_database_url()
    print(f"🔍 Checking PostgreSQL at {host}:{port}...")
    
    # First check if already running
    if check_postgres_running(host, port):
        print(f"✓ PostgreSQL is running at {host}:{port}")
        return True
    
    print(f"✗ PostgreSQL not responding at {host}:{port}")
    
    # Try different start methods
    start_methods = [
        ("Homebrew", start_postgres_brew),
        ("Docker", start_postgres_docker),
    ]
    
    # Add systemd for Linux
    if sys.platform == "linux":
        start_methods.append(("systemd", start_postgres_systemd))
    
    for method_name, start_func in start_methods:
        print(f"\n📦 Trying {method_name}...")
        if start_func():
            # Wait and check if it's now running
            for i in range(max_retries):
                time.sleep(wait_seconds)
                if check_postgres_running(host, port):
                    print(f"✓ PostgreSQL started successfully via {method_name}")
                    return True
                print(f"  Waiting... ({i + 1}/{max_retries})")
    
    print("\n❌ Failed to start PostgreSQL")
    print("Please start PostgreSQL manually:")
    print("  - macOS: brew services start postgresql@16")
    print("  - Docker: docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=postgres postgres:16")
    print("  - Linux: sudo systemctl start postgresql")
    return False


def check_redis_running(host: str = "localhost", port: int = 6379) -> bool:
    """Check if Redis is running (optional service)"""
    return check_port_open(host, port)


def run_all_checks() -> bool:
    """
    Run all startup checks.
    Returns True if all required services are running.
    """
    print("=" * 50)
    print("🚀 MediaPoster Startup Checks")
    print("=" * 50)
    
    # PostgreSQL is required
    if not ensure_postgres_running():
        return False
    
    # Redis is optional
    if check_redis_running():
        print("✓ Redis is running")
    else:
        print("⚠ Redis not running (optional - caching disabled)")
    
    print("=" * 50)
    print("✓ All startup checks passed")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
