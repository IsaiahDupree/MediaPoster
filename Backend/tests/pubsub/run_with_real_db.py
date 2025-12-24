#!/usr/bin/env python3
"""
Run Pub/Sub Tests with Real Database
=====================================
This script ensures the database is initialized before running tests.
"""

import sys
import subprocess
import asyncio
import os
from pathlib import Path

# Add Backend to path
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))
os.chdir(backend_path)

async def ensure_db_initialized():
    """Ensure database is initialized before tests."""
    from database.connection import init_db, async_session_maker
    
    print("🔌 Initializing database connection...")
    try:
        await init_db()
        if async_session_maker:
            print("✅ Database initialized successfully")
            return True
        else:
            print("⚠️  Database init completed but async_session_maker is None")
            print("   This may indicate a connection issue. Tests will skip DB-dependent tests.")
            return False
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        print("   Tests will skip DB-dependent tests.")
        return False


def run_tests_with_db(test_pattern: str = None):
    """Run tests with database initialized."""
    # Ensure DB is initialized
    db_ok = asyncio.run(ensure_db_initialized())
    
    # Build pytest command
    cmd = ["pytest", "Backend/tests/pubsub/"]
    
    if test_pattern:
        cmd.append(f"-k {test_pattern}")
    
    cmd.extend([
        "-v",
        "--tb=short",
        "-m", "not slow",  # Skip slow tests by default
    ])
    
    # Add markers for real DB tests
    if db_ok:
        print("\n📊 Running tests with REAL database...")
        cmd.extend(["-m", "integration or e2e"])
    else:
        print("\n📊 Running tests WITHOUT database (DB-dependent tests will skip)...")
        cmd.extend(["-m", "not integration and not e2e"])
    
    print(f"\n🚀 Command: {' '.join(cmd)}\n")
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent.parent)
    return result.returncode


if __name__ == "__main__":
    test_pattern = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(run_tests_with_db(test_pattern))

