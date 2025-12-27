#!/usr/bin/env python3
"""
Environment Health Check Script for MediaPoster Backend

This script validates the Python environment, dependencies, and services
before starting the backend server. Run this automatically on startup.

Usage:
    python scripts/env_check.py [--fix] [--verbose]
"""

import sys
import os
import subprocess
from pathlib import Path
from typing import Tuple, List, Optional
import argparse

# ============================================================================
# Configuration
# ============================================================================

REQUIRED_PYTHON_VERSION = (3, 11)  # Minimum version
MAX_PYTHON_VERSION = (3, 14)  # Maximum tested version

BACKEND_DIR = Path(__file__).parent.parent
VENV_DIR = BACKEND_DIR / "venv"
VENV311_DIR = BACKEND_DIR / "venv311"  # AI/ML environment with PyTorch

# ============================================================================
# Virtual Environment Configurations
# ============================================================================
VENV_CONFIGS = {
    "venv": {
        "path": VENV_DIR,
        "python_version": (3, 11),  # Minimum
        "description": "Main application (FastAPI, general tasks)",
        "critical_packages": [
            ("fastapi", "fastapi", "0.100.0"),
            ("uvicorn", "uvicorn", "0.20.0"),
            ("pydantic", "pydantic", "2.0.0"),
            ("sqlalchemy", "sqlalchemy", "2.0.0"),
            ("psycopg2", "psycopg2-binary", "2.9.0"),
            ("openai", "openai", "1.0.0"),
            ("httpx", "httpx", "0.25.0"),
            ("aiohttp", "aiohttp", "3.9.0"),
            ("PIL", "Pillow", "10.0.0"),
            ("numpy", "numpy", "1.24.0"),
            ("dotenv", "python-dotenv", "1.0.0"),
            ("supabase", "supabase", "2.0.0"),
        ],
    },
    "venv311": {
        "path": VENV311_DIR,
        "python_version": (3, 11),  # Required for PyTorch compatibility
        "description": "AI/ML tasks (PyTorch, Whisper transcription)",
        "critical_packages": [
            ("torch", "torch", "2.0.0"),
            ("whisper", "openai-whisper", "1.0.0"),
            ("numpy", "numpy", "1.24.0"),
        ],
    },
}

CRITICAL_PACKAGES = VENV_CONFIGS["venv"]["critical_packages"]

OPTIONAL_PACKAGES = [
    ("cv2", "opencv-python", "4.8.0"),
    ("moviepy", "moviepy", "1.0.0"),
    ("assemblyai", "assemblyai", "0.20.0"),
]

REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "OPENAI_API_KEY",
]

OPTIONAL_ENV_VARS = [
    "BLOTATO_API_KEY",
    "RAPIDAPI_KEY",
    "SUPABASE_URL",
    "SUPABASE_KEY",
]

# ============================================================================
# Helper Functions
# ============================================================================

class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_header(text: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")


def print_ok(text: str):
    print(f"  {Colors.GREEN}✓{Colors.RESET} {text}")


def print_warn(text: str):
    print(f"  {Colors.YELLOW}⚠{Colors.RESET} {text}")


def print_error(text: str):
    print(f"  {Colors.RED}✗{Colors.RESET} {text}")


def print_info(text: str):
    print(f"  {Colors.BLUE}ℹ{Colors.RESET} {text}")


def parse_version(version_str: str) -> Tuple[int, ...]:
    """Parse version string to tuple of ints."""
    try:
        # Handle versions like "2.9.11 (dt dec pq3 ext lo64)"
        version_str = version_str.split()[0]
        parts = version_str.split(".")
        return tuple(int(p) for p in parts[:3])
    except (ValueError, IndexError):
        return (0, 0, 0)


def version_gte(current: str, minimum: str) -> bool:
    """Check if current version >= minimum version."""
    return parse_version(current) >= parse_version(minimum)


# ============================================================================
# Check Functions
# ============================================================================

def check_venv() -> Tuple[bool, str]:
    """Check if running in the correct virtual environment."""
    current_python = Path(sys.executable).resolve()
    
    if not VENV_DIR.exists():
        return False, f"Virtual environment not found at {VENV_DIR}"
    
    # Check if we're in ANY virtual environment
    in_any_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    
    # Check if VIRTUAL_ENV env var points to our venv
    virtual_env = os.environ.get('VIRTUAL_ENV', '')
    in_our_venv = str(VENV_DIR) in virtual_env or str(VENV_DIR) in str(current_python)
    
    if in_our_venv or (in_any_venv and 'MediaPoster' in str(current_python)):
        return True, f"Running in venv: {current_python}"
    
    if in_any_venv:
        return True, f"Running in a virtual environment: {current_python}"
    
    # Check if the venv python exists and has the packages
    venv_python = VENV_DIR / "bin" / "python"
    if venv_python.exists():
        return False, f"Not in venv. Run: source {VENV_DIR}/bin/activate"
    
    return False, f"Virtual environment not properly set up at {VENV_DIR}"


def check_python_version() -> Tuple[bool, str]:
    """Check Python version compatibility."""
    version = sys.version_info[:3]
    version_str = f"{version[0]}.{version[1]}.{version[2]}"
    
    if version[:2] < REQUIRED_PYTHON_VERSION:
        return False, f"Python {version_str} is too old. Minimum: {REQUIRED_PYTHON_VERSION[0]}.{REQUIRED_PYTHON_VERSION[1]}"
    
    if version[:2] > MAX_PYTHON_VERSION:
        return False, f"Python {version_str} may be untested. Max tested: {MAX_PYTHON_VERSION[0]}.{MAX_PYTHON_VERSION[1]}"
    
    return True, f"Python {version_str}"


def check_package(import_name: str, package_name: str, min_version: str) -> Tuple[bool, str, Optional[str]]:
    """Check if a package is installed and meets version requirements."""
    try:
        mod = __import__(import_name)
        version = getattr(mod, "__version__", getattr(mod, "VERSION", "unknown"))
        
        if version == "unknown":
            return True, f"{package_name}: installed (version unknown)", version
        
        if version_gte(str(version), min_version):
            return True, f"{package_name}: {version}", version
        else:
            return False, f"{package_name}: {version} (need >= {min_version})", version
    except ImportError:
        return False, f"{package_name}: NOT INSTALLED", None


def check_env_var(var_name: str) -> Tuple[bool, str]:
    """Check if environment variable is set."""
    value = os.environ.get(var_name)
    if value:
        # Mask sensitive values
        if "KEY" in var_name or "SECRET" in var_name or "PASSWORD" in var_name:
            display = f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "****"
        else:
            display = value[:50] + "..." if len(value) > 50 else value
        return True, f"{var_name}: {display}"
    return False, f"{var_name}: NOT SET"


def check_database() -> Tuple[bool, str]:
    """Check database connectivity."""
    try:
        import sqlalchemy
        db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
        engine = sqlalchemy.create_engine(db_url)
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT 1"))
            result.fetchone()
        return True, "Database connection successful"
    except Exception as e:
        return False, f"Database connection failed: {str(e)[:100]}"


def check_supabase() -> Tuple[bool, str]:
    """Check Supabase status."""
    try:
        result = subprocess.run(
            ["supabase", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if "running" in result.stdout.lower():
            return True, "Supabase is running"
        return False, "Supabase is not running"
    except FileNotFoundError:
        return False, "Supabase CLI not found"
    except subprocess.TimeoutExpired:
        return False, "Supabase status check timed out"
    except Exception as e:
        return False, f"Supabase check failed: {str(e)[:50]}"


def check_port(port: int) -> Tuple[bool, str]:
    """Check if a port is available."""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.close()
        return True, f"Port {port} is available"
    except socket.error:
        return False, f"Port {port} is already in use"


def check_secondary_venv(venv_name: str, config: dict) -> List[Tuple[bool, str]]:
    """
    Check a secondary virtual environment by running Python in a subprocess.
    
    Returns list of (ok, message) tuples for each check.
    """
    results = []
    venv_path = config["path"]
    python_path = venv_path / "bin" / "python"
    
    # Check if venv exists
    if not venv_path.exists():
        results.append((False, f"{venv_name}: Directory not found at {venv_path}"))
        return results
    
    if not python_path.exists():
        results.append((False, f"{venv_name}: Python not found at {python_path}"))
        return results
    
    # Check Python version
    try:
        result = subprocess.run(
            [str(python_path), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            results.append((True, f"{venv_name}: Python {version}"))
        else:
            results.append((False, f"{venv_name}: Failed to get Python version"))
    except Exception as e:
        results.append((False, f"{venv_name}: Error checking Python: {str(e)[:50]}"))
    
    # Check critical packages
    for import_name, package_name, min_version in config.get("critical_packages", []):
        try:
            check_code = f'''
import json
try:
    mod = __import__("{import_name}")
    version = getattr(mod, "__version__", getattr(mod, "VERSION", "unknown"))
    print(json.dumps({{"ok": True, "version": str(version)}}))
except ImportError as e:
    print(json.dumps({{"ok": False, "error": str(e)}}))
'''
            result = subprocess.run(
                [str(python_path), "-c", check_code],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                output = json.loads(result.stdout.strip())
                if output.get("ok"):
                    results.append((True, f"{venv_name}/{package_name}: {output.get('version', 'installed')}"))
                else:
                    results.append((False, f"{venv_name}/{package_name}: {output.get('error', 'NOT INSTALLED')}"))
            else:
                results.append((False, f"{venv_name}/{package_name}: Check failed - {result.stderr[:50]}"))
        except subprocess.TimeoutExpired:
            results.append((False, f"{venv_name}/{package_name}: Check timed out"))
        except Exception as e:
            results.append((False, f"{venv_name}/{package_name}: Error - {str(e)[:50]}"))
    
    return results


# ============================================================================
# Main Check Functions
# ============================================================================

def run_all_checks(verbose: bool = False) -> Tuple[int, int, int]:
    """Run all environment checks. Returns (passed, warnings, failed)."""
    passed = 0
    warnings = 0
    failed = 0
    
    # Load .env file
    try:
        from dotenv import load_dotenv
        env_path = BACKEND_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass
    
    # 1. Virtual Environment Check
    print_header("Virtual Environment")
    ok, msg = check_venv()
    if ok:
        print_ok(msg)
        passed += 1
    else:
        print_error(msg)
        print_info("Run: source venv/bin/activate")
        failed += 1
    
    # 2. Python Version Check
    print_header("Python Version")
    ok, msg = check_python_version()
    if ok:
        print_ok(msg)
        passed += 1
    else:
        print_error(msg)
        failed += 1
    
    # 3. Critical Dependencies
    print_header("Critical Dependencies")
    for import_name, package_name, min_version in CRITICAL_PACKAGES:
        ok, msg, _ = check_package(import_name, package_name, min_version)
        if ok:
            print_ok(msg)
            passed += 1
        else:
            print_error(msg)
            print_info(f"Run: pip install {package_name}>={min_version}")
            failed += 1
    
    # 4. Optional Dependencies
    if verbose:
        print_header("Optional Dependencies")
        for import_name, package_name, min_version in OPTIONAL_PACKAGES:
            ok, msg, _ = check_package(import_name, package_name, min_version)
            if ok:
                print_ok(msg)
                passed += 1
            else:
                print_warn(msg)
                warnings += 1
    
    # 5. Environment Variables
    print_header("Environment Variables")
    for var in REQUIRED_ENV_VARS:
        ok, msg = check_env_var(var)
        if ok:
            print_ok(msg)
            passed += 1
        else:
            print_error(msg)
            failed += 1
    
    if verbose:
        for var in OPTIONAL_ENV_VARS:
            ok, msg = check_env_var(var)
            if ok:
                print_ok(msg)
                passed += 1
            else:
                print_warn(msg)
                warnings += 1
    
    # 6. Database Connectivity
    print_header("Database")
    ok, msg = check_database()
    if ok:
        print_ok(msg)
        passed += 1
    else:
        print_error(msg)
        print_info("Run: supabase start")
        failed += 1
    
    # 7. Supabase Status
    ok, msg = check_supabase()
    if ok:
        print_ok(msg)
        passed += 1
    else:
        print_warn(msg)
        warnings += 1
    
    # 8. Port Check
    print_header("Port Availability")
    ok, msg = check_port(5555)
    if ok:
        print_ok(msg)
        passed += 1
    else:
        print_warn(msg + " (backend may already be running)")
        warnings += 1
    
    # 9. Secondary Virtual Environments (AI/ML)
    print_header("AI/ML Environment (venv311)")
    venv311_config = VENV_CONFIGS.get("venv311")
    if venv311_config:
        venv311_results = check_secondary_venv("venv311", venv311_config)
        for ok, msg in venv311_results:
            if ok:
                print_ok(msg)
                passed += 1
            else:
                # AI/ML env is optional but important - warn instead of fail
                print_warn(msg)
                warnings += 1
    else:
        print_warn("venv311 configuration not found")
        warnings += 1
    
    return passed, warnings, failed


def print_summary(passed: int, warnings: int, failed: int):
    """Print summary of all checks."""
    print_header("Summary")
    total = passed + warnings + failed
    
    print(f"  Total checks: {total}")
    print(f"  {Colors.GREEN}Passed: {passed}{Colors.RESET}")
    print(f"  {Colors.YELLOW}Warnings: {warnings}{Colors.RESET}")
    print(f"  {Colors.RED}Failed: {failed}{Colors.RESET}")
    
    if failed == 0:
        print(f"\n  {Colors.GREEN}{Colors.BOLD}✓ Environment is ready!{Colors.RESET}")
        return 0
    else:
        print(f"\n  {Colors.RED}{Colors.BOLD}✗ Fix {failed} issue(s) before starting{Colors.RESET}")
        return 1


# ============================================================================
# Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="MediaPoster Backend Environment Check")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show optional checks")
    parser.add_argument("--fix", "-f", action="store_true", help="Attempt to fix issues (not yet implemented)")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only show errors and summary")
    args = parser.parse_args()
    
    print(f"\n{Colors.BOLD}MediaPoster Backend Environment Check{Colors.RESET}")
    print(f"Backend Dir: {BACKEND_DIR}")
    
    passed, warnings, failed = run_all_checks(verbose=args.verbose)
    exit_code = print_summary(passed, warnings, failed)
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
