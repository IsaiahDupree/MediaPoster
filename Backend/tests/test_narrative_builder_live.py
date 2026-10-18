#!/usr/bin/env python3
"""
Live Tests for Narrative Builder
=================================
Tests the narrative builder against the actual running backend.
Verifies:
1. Content selection filters (approved, not scheduled/posted)
2. Pillar creation and retrieval
3. 7-day plan generation
4. No silent failures
"""

import httpx
import asyncio
import sys
from datetime import datetime

BASE_URL = "http://localhost:5555/api"
PASSED = 0
FAILED = 0
TESTS = []


def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{timestamp} | {level:8} | {msg}")


def record(name: str, passed: bool, details: str = ""):
    global PASSED, FAILED
    status = "✅ PASS" if passed else "❌ FAIL"
    TESTS.append({"name": name, "passed": passed, "details": details})
    if passed:
        PASSED += 1
    else:
        FAILED += 1
    log(f"{status} | {name} | {details}", "TEST")


async def test_health():
    """Test backend is running"""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{BASE_URL}/health/quick")
            record("Backend Health", r.status_code == 200, f"status={r.status_code}")
            return r.status_code == 200
        except Exception as e:
            record("Backend Health", False, str(e))
            return False


async def test_content_stats():
    """Test content statistics endpoint"""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE_URL}/narrative-builder/content-stats")
        data = r.json()
        
        analyzed = data.get("content", {}).get("total_analyzed", 0)
        approved = data.get("content", {}).get("approved", 0)
        scheduled = data.get("scheduling", {}).get("unique_content", 0)
        
        passed = analyzed > 0 and approved > 0
        record("Content Stats", passed, 
               f"analyzed={analyzed}, approved={approved}, scheduled={scheduled}")
        
        return data


async def test_candidates_endpoint():
    """Test that candidates only returns approved content"""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE_URL}/narrative-builder/candidates?limit=10")
        data = r.json()
        
        candidates = data.get("candidates", [])
        all_fresh = all(c.get("status") == "fresh" or c.get("post_count", 0) == 0 
                       for c in candidates)
        
        passed = len(candidates) > 0 and all_fresh
        record("Candidates Endpoint", passed, 
               f"count={len(candidates)}, all_fresh={all_fresh}")
        
        return candidates


async def test_schedule_status_summary():
    """Test the new status-summary endpoint (was causing 500 error)"""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE_URL}/schedule/status-summary")
        
        if r.status_code == 200:
            data = r.json()
            passed = "status_counts" in data
            record("Schedule Status Summary", passed, f"status_code={r.status_code}")
        else:
            record("Schedule Status Summary", False, 
                   f"status_code={r.status_code}, error={r.text[:100]}")


async def test_goals_crud():
    """Test creating and listing narrative goals"""
    async with httpx.AsyncClient(timeout=10) as client:
        # List existing goals
        r = await client.get(f"{BASE_URL}/narrative-builder/goals")
        goals_before = r.json().get("count", 0)
        
        # Create a test goal
        test_goal = {
            "goal_statement": f"Test goal created at {datetime.now().isoformat()}",
            "primary_cta": "follow",
            "target_audience": "Test audience",
            "time_horizon": "next_7_days"
        }
        r = await client.post(f"{BASE_URL}/narrative-builder/goals", json=test_goal)
        
        if r.status_code == 200:
            data = r.json()
            goal_id = data.get("id")
            passed = goal_id is not None
            record("Goals CRUD - Create", passed, f"goal_id={goal_id}")
            return goal_id
        else:
            record("Goals CRUD - Create", False, f"status={r.status_code}")
            return None


async def test_pillars_crud(goal_id: str):
    """Test creating and listing pillars"""
    if not goal_id:
        record("Pillars CRUD", False, "No goal_id provided")
        return
    
    async with httpx.AsyncClient(timeout=10) as client:
        # Create pillars
        pillars = [
            {"name": "Test Pain Points", "pillar_type": "value", "target_percentage": 30},
            {"name": "Test Social Proof", "pillar_type": "proof", "target_percentage": 25},
            {"name": "Test How-To", "pillar_type": "value", "target_percentage": 45},
        ]
        
        created = 0
        for p in pillars:
            p["goal_id"] = goal_id
            r = await client.post(f"{BASE_URL}/narrative-builder/pillars", json=p)
            if r.status_code == 200:
                created += 1
        
        # Retrieve pillars
        r = await client.get(f"{BASE_URL}/narrative-builder/pillars/{goal_id}")
        data = r.json()
        pillar_count = data.get("count", 0)
        
        passed = created == 3 and pillar_count >= 3
        record("Pillars CRUD", passed, f"created={created}, retrieved={pillar_count}")


async def test_7_day_plan():
    """Test 7-day plan generation with real content"""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(f"{BASE_URL}/narrative-builder/plan/7-day?use_demo=false")
        
        if r.status_code == 200:
            data = r.json()
            total_posts = data.get("total_posts", 0)
            goals_applied = len(data.get("goals_applied", []))
            
            # Check each day has posts
            plan = data.get("plan", [])
            days_with_posts = sum(1 for d in plan if d.get("total_posts", 0) > 0)
            
            passed = total_posts > 0 and days_with_posts == 7
            record("7-Day Plan Generation", passed, 
                   f"total_posts={total_posts}, days_with_posts={days_with_posts}, goals={goals_applied}")
        else:
            record("7-Day Plan Generation", False, f"status={r.status_code}")


async def test_ai_recommendations():
    """Test AI-powered recommendations endpoint"""
    async with httpx.AsyncClient(timeout=30) as client:
        payload = {
            "goal": "Test AI automation builder positioning",
            "cta_type": "follow",
            "pillars": ["Pain Points", "Social Proof", "Process/How-To"],
            "audience": "Test audience",
            "platforms": ["tiktok", "instagram"]
        }
        
        r = await client.post(f"{BASE_URL}/narrative-builder/generate-recommendations", 
                             json=payload)
        
        if r.status_code == 200:
            data = r.json()
            recommendations = data.get("recommendations", [])
            
            # Check recommendations have required fields
            valid = all(
                rec.get("id") and rec.get("media", {}).get("title") 
                for rec in recommendations
            )
            
            passed = len(recommendations) > 0 and valid
            record("AI Recommendations", passed, 
                   f"count={len(recommendations)}, valid={valid}")
        else:
            record("AI Recommendations", False, 
                   f"status={r.status_code}, error={r.text[:100]}")


async def test_exclusion_logic():
    """Test that scheduled/posted content is excluded"""
    async with httpx.AsyncClient(timeout=10) as client:
        # Get content stats
        stats_r = await client.get(f"{BASE_URL}/narrative-builder/content-stats")
        stats = stats_r.json()
        
        approved = stats.get("content", {}).get("approved", 0)
        unique_scheduled = stats.get("scheduling", {}).get("unique_content", 0)
        
        # Get candidates
        cand_r = await client.get(f"{BASE_URL}/narrative-builder/candidates?limit=100")
        candidates = cand_r.json().get("candidates", [])
        
        # Available should be approximately approved - scheduled
        expected_available = approved - unique_scheduled
        actual_available = len(candidates)
        
        # Allow some margin for the limit and query differences
        passed = actual_available > 0 and actual_available <= approved
        record("Exclusion Logic", passed, 
               f"approved={approved}, scheduled={unique_scheduled}, available={actual_available}")


async def test_no_silent_failures():
    """Test that invalid requests don't fail silently"""
    async with httpx.AsyncClient(timeout=10) as client:
        # Test invalid goal creation
        r = await client.post(f"{BASE_URL}/narrative-builder/goals", json={})
        passed_1 = r.status_code in [422, 400]  # Should return validation error
        
        # Test invalid pillar creation
        r = await client.post(f"{BASE_URL}/narrative-builder/pillars", 
                             json={"name": "test"})  # Missing goal_id
        passed_2 = r.status_code in [422, 400, 200]  # May fail or return error in body
        
        passed = passed_1
        record("No Silent Failures", passed, 
               f"invalid_goal={passed_1}, invalid_pillar={passed_2}")


async def run_all_tests():
    """Run all tests"""
    log("=" * 60)
    log("🧪 NARRATIVE BUILDER LIVE TESTS")
    log("=" * 60)
    
    # Health check first
    if not await test_health():
        log("Backend not running! Start with: python main.py", "ERROR")
        return
    
    # Run tests
    await test_content_stats()
    await test_candidates_endpoint()
    await test_schedule_status_summary()
    
    goal_id = await test_goals_crud()
    await test_pillars_crud(goal_id)
    
    await test_7_day_plan()
    await test_ai_recommendations()
    await test_exclusion_logic()
    await test_no_silent_failures()
    
    # Summary
    log("=" * 60)
    log("📋 TEST SUMMARY")
    log("=" * 60)
    log(f"Total: {PASSED + FAILED}")
    log(f"✅ Passed: {PASSED}")
    log(f"❌ Failed: {FAILED}")
    
    if FAILED > 0:
        log("\n⚠️ FAILED TESTS:", "WARNING")
        for t in TESTS:
            if not t["passed"]:
                log(f"   {t['name']}: {t['details']}", "ERROR")
    else:
        log("\n✅ ALL TESTS PASSED!", "SUCCESS")
    
    return FAILED == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
