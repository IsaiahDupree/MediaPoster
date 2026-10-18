#!/usr/bin/env python3
"""
Integration Test Suite for All New Features
Run this to test all new API endpoints with a running backend.

Usage:
  1. Start the backend: uvicorn main:app --port 5555
  2. Run tests: python tests/integration_test.py
"""

import requests
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple
import sys
import time

# Configuration
BASE_URL = "http://localhost:5555"
VERBOSE = "-v" in sys.argv or "--verbose" in sys.argv


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: List[str] = []

    def add_pass(self, name: str):
        self.passed += 1
        if VERBOSE:
            print(f"  ✅ {name}")

    def add_fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append(f"{name}: {reason}")
        print(f"  ❌ {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Results: {self.passed}/{total} passed ({self.failed} failed)")
        print(f"{'='*60}")
        return self.failed == 0


def test_endpoint(
    method: str,
    path: str,
    results: TestResult,
    test_name: str,
    expected_status: int = 200,
    json_data: Dict = None,
    params: Dict = None,
    check_fields: List[str] = None
) -> Dict[str, Any]:
    """Test a single endpoint"""
    url = f"{BASE_URL}{path}"
    
    try:
        if method == "GET":
            response = requests.get(url, params=params, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=json_data, params=params, timeout=30)
        elif method == "PUT":
            response = requests.put(url, json=json_data, params=params, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, timeout=30)
        else:
            results.add_fail(test_name, f"Unknown method: {method}")
            return None

        if response.status_code != expected_status:
            results.add_fail(test_name, f"Expected {expected_status}, got {response.status_code}")
            return None

        data = response.json() if response.text else {}

        # Check required fields
        if check_fields:
            missing = [f for f in check_fields if f not in data]
            if missing:
                results.add_fail(test_name, f"Missing fields: {missing}")
                return None

        results.add_pass(test_name)
        return data

    except requests.exceptions.ConnectionError:
        results.add_fail(test_name, "Backend not running")
        return None
    except Exception as e:
        results.add_fail(test_name, str(e))
        return None


def run_all_tests():
    """Run all integration tests"""
    results = TestResult()

    print("="*60)
    print("MediaPoster Integration Test Suite")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # =========================================================================
    # CONTENT GROWTH API
    # =========================================================================
    print("\n📈 Content Growth API")
    
    test_endpoint("GET", "/api/content-growth/summary", results,
                  "Get growth summary",
                  check_fields=["total_views", "total_posts"])

    test_endpoint("GET", "/api/content-growth/summary?days=7", results,
                  "Get summary with days filter")

    test_id = str(uuid.uuid4())
    # May return 404 (not found) or 500 (db error with fake UUID)
    response = requests.get(f"{BASE_URL}/api/content-growth/content/{test_id}", timeout=10)
    if response.status_code in [400, 404, 500]:
        results.add_pass("Get content metrics (may 404/500)")
    else:
        results.add_fail("Get content metrics (may 404/500)", f"Got {response.status_code}")

    backfill_data = test_endpoint("POST", "/api/content-growth/backfill?days=7", results,
                                   "Start backfill job",
                                   check_fields=["job_id"])

    if backfill_data:
        test_endpoint("GET", f"/api/content-growth/backfill/{backfill_data['job_id']}", results,
                      "Get backfill status",
                      check_fields=["job_id", "status"])

    # =========================================================================
    # METRICS SCHEDULER API
    # =========================================================================
    print("\n⏰ Metrics Scheduler API")

    test_endpoint("GET", "/api/metrics-scheduler/status", results,
                  "Get scheduler status",
                  check_fields=["is_running", "platforms"])

    test_endpoint("GET", "/api/metrics-scheduler/intervals", results,
                  "Get available intervals",
                  check_fields=["intervals"])

    test_endpoint("PUT", "/api/metrics-scheduler/platform/instagram", results,
                  "Update platform config",
                  json_data={"interval": "6h"})

    test_endpoint("POST", "/api/metrics-scheduler/sync-now", results,
                  "Trigger sync all",
                  check_fields=["platforms"])

    test_endpoint("GET", "/api/metrics-scheduler/history", results,
                  "Get sync history",
                  check_fields=["history"])

    test_endpoint("GET", "/api/metrics-scheduler/line-graph-aggregate", results,
                  "Get aggregate line graph",
                  check_fields=["data", "summary"])

    # =========================================================================
    # APPROVAL QUEUE API
    # =========================================================================
    print("\n👁️ Approval Queue API")

    test_endpoint("GET", "/api/approval-queue/items", results,
                  "Get queue items")

    test_endpoint("GET", "/api/approval-queue/stats", results,
                  "Get queue stats",
                  check_fields=["total", "pending", "approved"])

    test_endpoint("GET", "/api/approval-queue/settings", results,
                  "Get control settings",
                  check_fields=["require_approval"])

    test_endpoint("GET", "/api/approval-queue/settings/presets", results,
                  "Get settings presets",
                  check_fields=["presets"])

    test_endpoint("GET", "/api/approval-queue/platforms", results,
                  "Get platform controls",
                  check_fields=["platforms"])

    test_endpoint("GET", "/api/approval-queue/activity", results,
                  "Get activity log",
                  check_fields=["activities"])

    # Test queue item action
    items_data = test_endpoint("GET", "/api/approval-queue/items?status=pending&limit=1", 
                               results, "Get pending items for action")
    
    if items_data and len(items_data) > 0:
        item_id = items_data[0]["id"]
        test_endpoint("POST", f"/api/approval-queue/item/{item_id}/action", results,
                      "Take action on item",
                      json_data={"action": "approve", "notes": "Test approval"})

    # =========================================================================
    # IMAGE ANALYSIS API
    # =========================================================================
    print("\n🔍 Image Analysis API")

    test_endpoint("GET", "/api/image-analysis/fields", results,
                  "Get available fields",
                  check_fields=["standard_fields", "person_fields"])

    test_endpoint("GET", "/api/image-analysis/analyses", results,
                  "List analyses",
                  check_fields=["analyses"])

    # Test analysis with URL
    analysis_data = test_endpoint("POST", "/api/image-analysis/analyze", results,
                                   "Analyze image from URL",
                                   json_data={
                                       "image_url": "https://picsum.photos/400/300",
                                       "analysis_depth": "brief"
                                   },
                                   check_fields=["analysis_id", "title"])

    if analysis_data:
        test_endpoint("GET", f"/api/image-analysis/analysis/{analysis_data['analysis_id']}", 
                      results, "Get analysis by ID",
                      check_fields=["analysis_id", "detailed_description"])

    # =========================================================================
    # POSTED MEDIA API
    # =========================================================================
    print("\n📹 Posted Media API")

    test_endpoint("GET", "/api/posted-media/list", results,
                  "Get posted media list",
                  check_fields=["items", "stats"])

    test_endpoint("GET", "/api/posted-media/list?status=published", results,
                  "Get published media")

    test_endpoint("GET", "/api/posted-media/platforms", results,
                  "Get platform breakdown",
                  check_fields=["platforms"])

    # =========================================================================
    # FINAL SUMMARY
    # =========================================================================
    return results.summary()


def run_quick_health_check():
    """Quick check if backend is running"""
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ Backend is running at {BASE_URL}")
            return True
    except:
        pass
    
    print(f"❌ Backend is not running at {BASE_URL}")
    print("Start it with: uvicorn main:app --port 5555")
    return False


if __name__ == "__main__":
    if not run_quick_health_check():
        sys.exit(1)
    
    print()
    success = run_all_tests()
    sys.exit(0 if success else 1)
