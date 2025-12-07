#!/usr/bin/env python3
"""
Comprehensive endpoint testing script
Tests all API endpoints to identify issues
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5555"

# Define all endpoints to test
ENDPOINTS = {
    "Health Check": {"method": "GET", "path": "/health"},
    "API Health": {"method": "GET", "path": "/api/health"},
    
    # Videos
    "List Videos": {"method": "GET", "path": "/api/videos/"},
    "Video Detail": {"method": "GET", "path": "/api/videos/fb9ae98b-a3be-4685-af0b-76ef96931076", "expect_404": True},  # 404 is OK if video doesn't exist
    
    # Analytics
    "Analytics Summary": {"method": "GET", "path": "/api/analytics/summary"},
    "Analytics Trends": {"method": "GET", "path": "/api/analytics/trends"},
    
    # Goals
    "List Goals": {"method": "GET", "path": "/api/goals"},
    
    # Calendar
    "Calendar Posts": {"method": "GET", "path": "/api/calendar/posts"},
    
    # People
    "List People": {"method": "GET", "path": "/api/people"},
    
    # Content
    "List Content": {"method": "GET", "path": "/api/content"},
    "Content Metrics": {"method": "GET", "path": "/api/content/metrics"},
    
    # Clips
    "List Clips": {"method": "GET", "path": "/api/clips"},
    
    # Publishing
    "Publishing Queue": {"method": "GET", "path": "/api/publishing/queue"},
    "Publishing Analytics": {"method": "GET", "path": "/api/publishing/analytics"},
    
    # Jobs
    "List Jobs": {"method": "GET", "path": "/api/jobs"},
    
    # App Config
    "App Config": {"method": "GET", "path": "/api/config"},
}

def test_endpoint(name, config):
    """Test a single endpoint"""
    method = config["method"]
    path = config["path"]
    url = f"{BASE_URL}{path}"
    
    headers = {
        "Origin": "http://localhost:5557",
        "Accept": "application/json"
    }
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=5)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=config.get("data", {}), timeout=5)
        else:
            return {"status": "SKIP", "message": "Method not supported"}
        
        # Check CORS headers
        has_cors = "access-control-allow-origin" in response.headers
        
        # Check if 404 is expected (e.g., for non-existent resources)
        expect_404 = config.get("expect_404", False)
        is_pass = response.status_code < 400 or (response.status_code == 404 and expect_404)
        
        result = {
            "status": "PASS" if is_pass else "FAIL",
            "status_code": response.status_code,
            "has_cors": has_cors,
            "reason": response.reason
        }
        
        # Add error details if failed
        if response.status_code >= 400 and not (response.status_code == 404 and expect_404):
            try:
                error_data = response.json()
                result["error"] = error_data.get("message", error_data.get("detail", str(error_data)))
            except:
                result["error"] = response.text[:200] if response.text else "No error message"
        
        return result
        
    except requests.exceptions.ConnectionError:
        return {"status": "ERROR", "message": "Connection refused - backend not running?"}
    except requests.exceptions.Timeout:
        return {"status": "ERROR", "message": "Request timeout"}
    except Exception as e:
        return {"status": "ERROR", "message": str(e)}

def main():
    """Run all endpoint tests"""
    print("=" * 80)
    print(f"Backend API Endpoint Test Suite")
    print(f"Testing against: {BASE_URL}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()
    
    results = {}
    pass_count = 0
    fail_count = 0
    error_count = 0
    
    for name, config in ENDPOINTS.items():
        print(f"Testing: {name:<30} ", end="", flush=True)
        result = test_endpoint(name, config)
        results[name] = result
        
        status = result.get("status", "UNKNOWN")
        if status == "PASS":
            print(f"✅ {result['status_code']} - CORS: {'✓' if result.get('has_cors') else '✗'}")
            pass_count += 1
        elif status == "FAIL":
            print(f"❌ {result['status_code']} - {result.get('reason', 'Unknown')}")
            if "error" in result:
                print(f"   └─ Error: {result['error'][:100]}...")
            fail_count += 1
        else:
            print(f"⚠️  {result.get('message', 'Unknown error')}")
            error_count += 1
    
    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Endpoints: {len(ENDPOINTS)}")
    print(f"✅ Passed: {pass_count}")
    print(f"❌ Failed: {fail_count}")
    print(f"⚠️  Errors: {error_count}")
    print()
    
    # Print CORS issues
    cors_issues = [name for name, result in results.items() 
                   if result.get("status") == "PASS" and not result.get("has_cors")]
    if cors_issues:
        print("⚠️  Endpoints missing CORS headers:")
        for name in cors_issues:
            print(f"   - {name}")
        print()
    
    # Print failed endpoints with details
    if fail_count > 0:
        print("❌ Failed Endpoints:")
        for name, result in results.items():
            if result.get("status") == "FAIL":
                print(f"\n   {name}:")
                print(f"   Status: {result['status_code']} {result.get('reason', '')}")
                if "error" in result:
                    print(f"   Error: {result['error']}")
    
    print("=" * 80)
    
    # Return exit code
    return 0 if fail_count == 0 and error_count == 0 else 1

if __name__ == "__main__":
    exit(main())
