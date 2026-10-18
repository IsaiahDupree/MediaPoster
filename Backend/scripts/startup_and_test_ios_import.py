#!/usr/bin/env python3
"""
Startup and iOS Import Test Script

This script:
1. Checks/Starts Supabase database
2. Starts backend server
3. Tests iOS import functionality
4. Tests duplicate deletion
"""
import subprocess
import time
import sys
import os
import requests
import json
from pathlib import Path
from typing import Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

API_URL = "http://localhost:5555"
SUPABASE_DIR = Path(__file__).parent.parent.parent / "supabase"
BACKEND_DIR = Path(__file__).parent.parent


def check_supabase_running() -> bool:
    """Check if Supabase is running"""
    try:
        result = subprocess.run(
            ["supabase", "status"],
            cwd=SUPABASE_DIR,
            capture_output=True,
            text=True,
            timeout=10
        )
        return "API URL" in result.stdout
    except Exception as e:
        print(f"  ⚠️  Error checking Supabase: {e}")
        return False


def start_supabase() -> bool:
    """Start Supabase database"""
    print("🔄 Starting Supabase...")
    try:
        if not SUPABASE_DIR.exists():
            print(f"  ❌ Supabase directory not found: {SUPABASE_DIR}")
            return False
        
        # Check if already running
        if check_supabase_running():
            print("  ✅ Supabase already running")
            return True
        
        # Start Supabase
        print("  🚀 Starting Supabase (this may take a minute)...")
        process = subprocess.Popen(
            ["supabase", "start"],
            cwd=SUPABASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for startup (max 2 minutes)
        for i in range(120):
            time.sleep(1)
            if check_supabase_running():
                print("  ✅ Supabase started successfully")
                return True
            if process.poll() is not None:
                # Process finished, check output
                stdout, stderr = process.communicate()
                if "API URL" in stdout.decode():
                    print("  ✅ Supabase started")
                    return True
                else:
                    print(f"  ❌ Supabase failed to start: {stderr.decode()}")
                    return False
        
        print("  ⚠️  Supabase startup timeout (still checking...)")
        return check_supabase_running()
    except Exception as e:
        print(f"  ❌ Error starting Supabase: {e}")
        return False


def check_backend_running() -> bool:
    """Check if backend is running"""
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def start_backend() -> bool:
    """Start backend server (in background)"""
    print("\n🔄 Starting Backend...")
    try:
        if check_backend_running():
            print("  ✅ Backend already running")
            return True
        
        print("  🚀 Starting backend server...")
        print("  ⚠️  Note: Backend will run in background. Use Ctrl+C to stop.")
        print("  📝 To start manually: cd Backend && source venv/bin/activate && uvicorn main:app --port 5555 --reload")
        
        # Start backend in background
        process = subprocess.Popen(
            ["uvicorn", "main:app", "--port", "5555", "--reload"],
            cwd=BACKEND_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for startup (max 30 seconds)
        for i in range(30):
            time.sleep(1)
            if check_backend_running():
                print("  ✅ Backend started successfully")
                return True
        
        print("  ⚠️  Backend startup timeout (still checking...)")
        return check_backend_running()
    except Exception as e:
        print(f"  ❌ Error starting backend: {e}")
        print("  💡 Try starting manually: cd Backend && source venv/bin/activate && uvicorn main:app --port 5555 --reload")
        return False


def test_ios_import_scan(import_path: str) -> Optional[dict]:
    """Test iOS import scan"""
    print("\n📱 Testing iOS Import Scan...")
    try:
        response = requests.post(
            f"{API_URL}/api/import/ios/scan",
            json={
                "path": import_path,
                "filters": {
                    "media_types": ["video", "image"],
                    "min_size_mb": 0,
                    "max_size_mb": 10000,
                    "skip_duplicates": True,
                    "auto_analyze": False
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"  ✅ Scan successful:")
            print(f"     • Total files: {data.get('total_count', 0)}")
            print(f"     • Duplicates: {data.get('duplicates_count', 0)}")
            print(f"     • To import: {data.get('to_import_count', 0)}")
            return data
        else:
            print(f"  ❌ Scan failed: {response.status_code}")
            print(f"     {response.text}")
            return None
    except Exception as e:
        print(f"  ❌ Error during scan: {e}")
        return None


def get_duplicates() -> Optional[list]:
    """Get list of duplicate videos"""
    print("\n🔍 Finding Duplicates...")
    try:
        response = requests.get(
            f"{API_URL}/api/ai-curation/duplicates",
            params={"threshold": 0.9},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            duplicates = data.get("duplicates", [])
            print(f"  ✅ Found {len(duplicates)} duplicate groups")
            return duplicates
        else:
            print(f"  ❌ Failed to get duplicates: {response.status_code}")
            print(f"     {response.text}")
            return None
    except Exception as e:
        print(f"  ❌ Error getting duplicates: {e}")
        return None


def delete_duplicates(group_id: str, keep_video_id: str, delete_video_ids: list) -> bool:
    """Delete duplicate videos"""
    print(f"\n🗑️  Deleting Duplicates (Group: {group_id[:8]}...)")
    try:
        response = requests.post(
            f"{API_URL}/api/ai-curation/duplicates/delete",
            json={
                "group_id": group_id,
                "keep_video_id": keep_video_id,
                "delete_video_ids": delete_video_ids
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            deleted = data.get("deleted_count", 0)
            print(f"  ✅ Deleted {deleted} duplicate(s)")
            return True
        else:
            print(f"  ❌ Delete failed: {response.status_code}")
            print(f"     {response.text}")
            return False
    except Exception as e:
        print(f"  ❌ Error deleting duplicates: {e}")
        return False


def main():
    """Main execution"""
    print("=" * 60)
    print("🚀 MediaPoster Startup & iOS Import Test")
    print("=" * 60)
    
    # Step 1: Start Supabase
    print("\n📦 Step 1: Starting Supabase Database")
    if not start_supabase():
        print("\n❌ Failed to start Supabase. Please start manually:")
        print("   cd supabase && supabase start")
        return 1
    
    # Step 2: Start Backend
    print("\n🔧 Step 2: Starting Backend Server")
    if not start_backend():
        print("\n❌ Failed to start backend. Please start manually:")
        print("   cd Backend && source venv/bin/activate && uvicorn main:app --port 5555 --reload")
        return 1
    
    # Wait a bit for services to be ready
    print("\n⏳ Waiting for services to be ready...")
    time.sleep(3)
    
    # Step 3: Test iOS Import
    print("\n📱 Step 3: Testing iOS Import")
    import_path = os.path.expanduser("~/Documents/IphoneImport")
    
    if not Path(import_path).exists():
        print(f"  ⚠️  Import path not found: {import_path}")
        print("  💡 Please provide the path to your iPhone import directory:")
        import_path = input("  Path: ").strip()
    
    if Path(import_path).exists():
        scan_result = test_ios_import_scan(import_path)
        
        if scan_result:
            print("\n✅ iOS Import scan completed successfully!")
            
            # Step 4: Find and delete duplicates
            print("\n🗑️  Step 4: Finding and Deleting Duplicates")
            duplicates = get_duplicates()
            
            if duplicates:
                print(f"\n  Found {len(duplicates)} duplicate groups")
                print("  ⚠️  To delete duplicates, use the API or frontend")
                print("  💡 Example API call:")
                print(f"     POST {API_URL}/api/ai-curation/duplicates/delete")
                print("     {")
                print('       "group_id": "...",')
                print('       "keep_video_id": "...",')
                print('       "delete_video_ids": ["..."]')
                print("     }")
            else:
                print("  ✅ No duplicates found")
        else:
            print("\n⚠️  iOS Import scan failed. Check backend logs.")
    else:
        print(f"\n⚠️  Import path not found: {import_path}")
        print("  Skipping iOS import test")
    
    # Summary
    print("\n" + "=" * 60)
    print("✅ Startup Complete!")
    print("=" * 60)
    print("\n📊 Services Status:")
    print(f"  • Supabase: {'✅ Running' if check_supabase_running() else '❌ Not running'}")
    print(f"  • Backend: {'✅ Running' if check_backend_running() else '❌ Not running'}")
    print("\n🔗 URLs:")
    print(f"  • Backend API: {API_URL}")
    print(f"  • API Docs: {API_URL}/docs")
    print(f"  • Health Check: {API_URL}/api/health")
    print("\n💡 To stop services:")
    print("  • Backend: Find the process and kill it (or Ctrl+C if in foreground)")
    print("  • Supabase: cd supabase && supabase stop")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

