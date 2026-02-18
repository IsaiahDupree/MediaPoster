#!/usr/bin/env python3
"""
Startup checks for MediaPoster Backend
======================================
Ensures Docker → Supabase → PostgreSQL are running before the app starts.

Priority order:
  1. Docker Desktop  (required for Supabase local)
  2. Supabase local   (provides PG on port 54322 + Auth/Storage/Realtime)
  3. Homebrew PG      (last-resort fallback, plain PG only)
"""

import subprocess
import sys
import time
import socket
import os
import shutil
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# ─── Defaults ────────────────────────────────────────────────────────────────
SUPABASE_DB_PORT = 54322
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # …/MediaPoster
DOCKER_STARTUP_TIMEOUT = 60   # seconds to wait for Docker daemon
SUPABASE_STARTUP_TIMEOUT = 90  # seconds to wait for `supabase start`


# ─── Helpers ─────────────────────────────────────────────────────────────────

def parse_database_url():
    """Parse DATABASE_URL to extract host and port."""
    db_url = os.getenv("DATABASE_URL", f"postgresql://localhost:{SUPABASE_DB_PORT}/postgres")
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
        return "localhost", SUPABASE_DB_PORT


def check_port_open(host: str, port: int, timeout: float = 2.0) -> bool:
    """Return True if *host:port* is accepting TCP connections."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            return sock.connect_ex((host, port)) == 0
    except Exception:
        return False


def _run(cmd, **kwargs):
    """Thin wrapper around subprocess.run with sane defaults."""
    kwargs.setdefault("capture_output", True)
    kwargs.setdefault("text", True)
    kwargs.setdefault("timeout", 30)
    return subprocess.run(cmd, **kwargs)


# ─── Docker ──────────────────────────────────────────────────────────────────

def is_docker_running() -> bool:
    """Check whether the Docker daemon is responsive."""
    try:
        return _run(["docker", "info"], timeout=10).returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def ensure_docker_running() -> bool:
    """
    Make sure Docker Desktop is running.  If it isn't, open it and wait
    up to DOCKER_STARTUP_TIMEOUT seconds for the daemon to respond.
    """
    if is_docker_running():
        print("✓ Docker is running")
        return True

    print("🐳 Docker not running — starting Docker Desktop …")
    try:
        subprocess.run(["open", "-a", "Docker"], capture_output=True)
    except FileNotFoundError:
        print("  ✗ 'open' command not available (not macOS?)")
        return False

    deadline = time.time() + DOCKER_STARTUP_TIMEOUT
    while time.time() < deadline:
        time.sleep(3)
        if is_docker_running():
            print("✓ Docker Desktop started")
            return True
        remaining = int(deadline - time.time())
        print(f"  Waiting for Docker daemon … ({remaining}s remaining)")

    print("  ✗ Docker did not start within timeout")
    return False


# ─── Supabase ────────────────────────────────────────────────────────────────

def is_supabase_running() -> bool:
    """Check if Supabase local dev is up (PG on 54322)."""
    return check_port_open("localhost", SUPABASE_DB_PORT)


def _find_supabase_project() -> Path:
    """Locate the supabase/ config directory."""
    candidates = [
        PROJECT_ROOT / "supabase" / "config.toml",
        PROJECT_ROOT / "Backend" / "supabase" / "config.toml",
    ]
    for p in candidates:
        if p.exists():
            return p.parent.parent  # directory containing supabase/
    return PROJECT_ROOT


def ensure_supabase_running() -> bool:
    """
    Start Supabase local dev if not already running.
    Requires Docker to be running first.
    """
    if is_supabase_running():
        print(f"✓ Supabase local is running (port {SUPABASE_DB_PORT})")
        return True

    if not shutil.which("supabase"):
        print("  ✗ Supabase CLI not found — install with: brew install supabase/tap/supabase")
        return False

    project_dir = _find_supabase_project()
    print(f"🟢 Starting Supabase local dev in {project_dir} …")

    try:
        proc = subprocess.Popen(
            ["supabase", "start"],
            cwd=str(project_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        deadline = time.time() + SUPABASE_STARTUP_TIMEOUT
        while time.time() < deadline:
            # Check if port is up yet
            if is_supabase_running():
                print(f"✓ Supabase local started (port {SUPABASE_DB_PORT})")
                return True

            # Check if process exited early (error)
            ret = proc.poll()
            if ret is not None:
                out = proc.stdout.read() if proc.stdout else ""
                if is_supabase_running():
                    print(f"✓ Supabase local started (port {SUPABASE_DB_PORT})")
                    return True
                print(f"  ✗ `supabase start` exited with code {ret}")
                if out:
                    for line in out.strip().splitlines()[-5:]:
                        print(f"    {line}")
                return False

            remaining = int(deadline - time.time())
            print(f"  Waiting for Supabase … ({remaining}s remaining)")
            time.sleep(5)

        # Timed out
        proc.kill()
        print("  ✗ Supabase did not start within timeout")
        return False

    except Exception as e:
        print(f"  ✗ Error starting Supabase: {e}")
        return False


# ─── Homebrew Fallback ───────────────────────────────────────────────────────

def start_postgres_brew() -> bool:
    """Last-resort: start plain PostgreSQL via Homebrew."""
    print("🔄 Fallback: starting PostgreSQL via Homebrew …")
    for svc in ["postgresql@16", "postgresql@15", "postgresql"]:
        try:
            r = _run(["brew", "services", "start", svc])
            if r.returncode == 0:
                print(f"  ✓ Started {svc}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    print("  ✗ Homebrew PostgreSQL not available")
    return False


# ─── Orchestrator ────────────────────────────────────────────────────────────

def ensure_postgres_running(max_retries: int = 3, wait_seconds: int = 5) -> bool:
    """
    Ensure PostgreSQL is reachable.  Strategy:
      1. If PG is already responding → done.
      2. Ensure Docker Desktop is running.
      3. Run `supabase start` (provides PG on 54322 + everything else).
      4. Fallback to Homebrew PG on whatever port DATABASE_URL specifies.
    """
    host, port = parse_database_url()
    print(f"🔍 Checking PostgreSQL at {host}:{port} …")

    if check_port_open(host, port):
        print(f"✓ PostgreSQL is already running at {host}:{port}")
        return True

    print(f"✗ PostgreSQL not responding at {host}:{port}")

    # ── Step 1: Docker ────────────────────────────────────────────────────
    print("\n📦 Step 1 — Ensure Docker is running")
    docker_ok = ensure_docker_running()

    # ── Step 2: Supabase ──────────────────────────────────────────────────
    if docker_ok:
        print("\n📦 Step 2 — Ensure Supabase local is running")
        if ensure_supabase_running():
            # Verify the port we actually need
            for i in range(max_retries):
                if check_port_open(host, port):
                    print(f"✓ PostgreSQL ready at {host}:{port}")
                    return True
                time.sleep(wait_seconds)
                print(f"  Waiting for PG on {port} … ({i + 1}/{max_retries})")

    # ── Step 3: Homebrew fallback ─────────────────────────────────────────
    print("\n📦 Step 3 — Homebrew fallback")
    if start_postgres_brew():
        for i in range(max_retries):
            time.sleep(wait_seconds)
            if check_port_open(host, port):
                print(f"✓ PostgreSQL started via Homebrew at {host}:{port}")
                return True
            print(f"  Waiting … ({i + 1}/{max_retries})")

    # ── Failed ────────────────────────────────────────────────────────────
    print("\n❌ Failed to start PostgreSQL")
    print("Please start it manually:")
    print("  1. Open Docker Desktop")
    print("  2. cd to project root and run: supabase start")
    print("  Or as a fallback: brew services start postgresql@16")
    return False


def check_redis_running(host: str = "localhost", port: int = 6379) -> bool:
    """Check if Redis is running (optional service)."""
    return check_port_open(host, port)


def run_all_checks() -> bool:
    """
    Run all startup checks.
    Returns True if all required services are running.
    """
    print("=" * 50)
    print("🚀 MediaPoster Startup Checks")
    print("=" * 50)

    if not ensure_postgres_running():
        return False

    if check_redis_running():
        print("✓ Redis is running")
    else:
        print("⚠ Redis not running (optional — caching disabled)")

    print("=" * 50)
    print("✓ All startup checks passed")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = run_all_checks()
    sys.exit(0 if success else 1)
