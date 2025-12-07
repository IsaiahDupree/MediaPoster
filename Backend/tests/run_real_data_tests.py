#!/usr/bin/env python3
"""
Run Integration Tests with Real Video Data
Discovers and uses actual video files from the system
"""
import sys
import subprocess
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

def main():
    """Run tests with real video data"""
    print("=" * 60)
    print("Running Integration Tests with Real Video Data")
    print("=" * 60)
    print()
    
    # Test files to run
    test_files = [
        "Backend/tests/integration/test_endpoints_with_real_video_data.py",
        "Backend/tests/integration/test_with_real_video_files.py",
        "Backend/tests/integration/test_new_endpoints_real_data.py"
    ]
    
    # Run pytest with verbose output
    cmd = [
        "python", "-m", "pytest",
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        *test_files
    ]
    
    print(f"Running: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, cwd=backend_path.parent)
    
    if result.returncode == 0:
        print()
        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("✗ Some tests failed")
        print("=" * 60)
    
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())






