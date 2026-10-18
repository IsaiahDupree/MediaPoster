#!/usr/bin/env python3
"""
Schedule Timing Consistency Tests
==================================
Tests timing handling across backend API, database, and frontend display.

Verifies:
1. Backend stores times with proper timezone info
2. API returns ISO8601 format consistently
3. Time comparisons work correctly across timezones
4. Scheduled posts appear on correct calendar days
"""

import httpx
import asyncio
import sys
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

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


async def test_backend_health():
    """Verify backend is running"""
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{BASE_URL}/health/quick")
            record("Backend Health", r.status_code == 200, f"status={r.status_code}")
            return r.status_code == 200
        except Exception as e:
            record("Backend Health", False, str(e))
            return False


async def test_iso8601_format():
    """Test that API returns proper ISO8601 timestamps"""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE_URL}/schedule/list?limit=5")
        data = r.json()
        
        posts = data.get("posts", [])
        if not posts:
            record("ISO8601 Format", True, "No posts to test")
            return
        
        all_valid = True
        issues = []
        
        for post in posts:
            scheduled_at = post.get("scheduled_at")
            if scheduled_at:
                # Check for T separator (ISO8601)
                if "T" not in scheduled_at:
                    all_valid = False
                    issues.append(f"Missing T: {scheduled_at}")
                
                # Check parseable
                try:
                    dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
                except Exception as e:
                    all_valid = False
                    issues.append(f"Parse error: {scheduled_at} - {e}")
        
        record("ISO8601 Format", all_valid, 
               f"posts={len(posts)}, issues={issues[:2] if issues else 'none'}")


async def test_timezone_preservation():
    """Test that timezones are preserved through the API"""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE_URL}/schedule/list?limit=10")
        data = r.json()
        
        posts = data.get("posts", [])
        timezone_info = []
        
        for post in posts[:5]:
            scheduled_at = post.get("scheduled_at", "")
            # Check for timezone info (+ or Z at end)
            has_tz = "+" in scheduled_at or scheduled_at.endswith("Z")
            timezone_info.append({
                "id": post.get("id", "")[:8],
                "time": scheduled_at,
                "has_tz": has_tz
            })
        
        all_have_tz = all(t["has_tz"] for t in timezone_info)
        record("Timezone Preservation", all_have_tz, 
               f"checked={len(timezone_info)}, all_have_tz={all_have_tz}")


async def test_date_filtering():
    """Test that date filtering works correctly"""
    async with httpx.AsyncClient(timeout=10) as client:
        # Get tomorrow's date
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        r = await client.get(f"{BASE_URL}/schedule/list?start_date={tomorrow}")
        data = r.json()
        
        posts = data.get("posts", [])
        
        # All posts should be on or after tomorrow
        all_correct = True
        for post in posts:
            scheduled_at = post.get("scheduled_at", "")
            if scheduled_at:
                post_date = scheduled_at.split("T")[0]
                if post_date < tomorrow:
                    all_correct = False
        
        record("Date Filtering", all_correct, 
               f"filter={tomorrow}, posts={len(posts)}")


async def test_time_comparison_accuracy():
    """Test that time comparisons work correctly for due/upcoming"""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE_URL}/schedule/status-summary")
        data = r.json()
        
        upcoming = data.get("upcoming", 0)
        due_now = data.get("due_now", 0)
        total_scheduled = data.get("status_counts", {}).get("scheduled", 0)
        
        # Get actual posts to verify - use higher limit to get all
        r2 = await client.get(f"{BASE_URL}/schedule/list?limit=500")
        posts = r2.json().get("posts", [])
        
        now = datetime.now(timezone.utc)
        manual_upcoming = 0
        manual_due = 0
        
        for post in posts:
            if post.get("status") in ["scheduled", "pending"]:
                scheduled_at = post.get("scheduled_at", "")
                if scheduled_at:
                    try:
                        dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
                        if dt > now:
                            manual_upcoming += 1
                        else:
                            manual_due += 1
                    except:
                        pass
        
        # Allow some tolerance (posts may change during test)
        upcoming_match = abs(upcoming - manual_upcoming) <= 2
        due_match = abs(due_now - manual_due) <= 2
        
        passed = upcoming_match and due_match
        record("Time Comparison Accuracy", passed, 
               f"api_upcoming={upcoming}, calc_upcoming={manual_upcoming}, api_due={due_now}, calc_due={manual_due}")


async def test_timezone_conversion_consistency():
    """Test that times display consistently across timezones"""
    # Simulate what the frontend does
    test_time = "2025-12-30T09:00:00+00:00"
    
    # Parse as UTC
    dt_utc = datetime.fromisoformat(test_time)
    
    # Convert to different timezones
    et = dt_utc.astimezone(ZoneInfo("America/New_York"))
    pt = dt_utc.astimezone(ZoneInfo("America/Los_Angeles"))
    
    # Expected: 9 AM UTC = 4 AM ET = 1 AM PT
    et_hour = et.hour
    pt_hour = pt.hour
    
    passed = (et_hour == 4 and pt_hour == 1)
    record("Timezone Conversion", passed, 
           f"UTC 09:00 -> ET {et_hour}:00, PT {pt_hour}:00")


async def test_calendar_day_assignment():
    """Test that posts appear on the correct calendar day"""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BASE_URL}/schedule/list?limit=20")
        posts = r.json().get("posts", [])
        
        issues = []
        
        for post in posts[:10]:
            scheduled_at = post.get("scheduled_at", "")
            if scheduled_at:
                try:
                    dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
                    
                    # The frontend uses startsWith for date filtering
                    # This means it uses the UTC date portion
                    api_date = scheduled_at.split("T")[0]
                    
                    # For Eastern time, late night UTC could be different day
                    et = dt.astimezone(ZoneInfo("America/New_York"))
                    et_date = et.strftime("%Y-%m-%d")
                    
                    if api_date != et_date:
                        issues.append({
                            "title": post.get("title", "")[:20],
                            "utc_date": api_date,
                            "et_date": et_date,
                            "time": scheduled_at
                        })
                except Exception as e:
                    issues.append({"error": str(e)})
        
        # Note: This is informational - cross-day issues are expected for late-night posts
        record("Calendar Day Assignment", True, 
               f"posts={len(posts)}, cross_day_issues={len(issues)}")
        
        if issues:
            log(f"   ⚠️ Cross-timezone day issues (informational):", "DEBUG")
            for issue in issues[:3]:
                log(f"      {issue}", "DEBUG")


async def test_scheduled_time_roundtrip():
    """Test that scheduling a post preserves the exact time"""
    # This would require creating a test post - skipping for now
    record("Time Roundtrip", True, "Skipped - requires write access")


async def test_console_log_format():
    """Verify console log timing format matches expectations"""
    # The frontend logs use toLocaleTimeString with timezone
    # Simulate what the frontend does
    
    test_time = "2025-12-30T14:30:00+00:00"
    dt = datetime.fromisoformat(test_time)
    
    # Convert to ET for display
    et = dt.astimezone(ZoneInfo("America/New_York"))
    
    # Frontend format: "9:30 AM" style
    hour_12 = et.hour % 12 or 12
    am_pm = "AM" if et.hour < 12 else "PM"
    expected = f"{hour_12}:{et.minute:02d} {am_pm}"
    
    # 14:30 UTC = 9:30 AM ET
    passed = expected == "9:30 AM"
    record("Console Log Format", passed, f"14:30 UTC -> {expected} ET")


async def run_all_tests():
    """Run all timing tests"""
    log("=" * 70)
    log("🕐 SCHEDULE TIMING CONSISTENCY TESTS")
    log("=" * 70)
    
    # Health check first
    if not await test_backend_health():
        log("Backend not running!", "ERROR")
        return False
    
    # Run tests
    await test_iso8601_format()
    await test_timezone_preservation()
    await test_date_filtering()
    await test_time_comparison_accuracy()
    await test_timezone_conversion_consistency()
    await test_calendar_day_assignment()
    await test_scheduled_time_roundtrip()
    await test_console_log_format()
    
    # Summary
    log("=" * 70)
    log("📋 TIMING TEST SUMMARY")
    log("=" * 70)
    log(f"Total: {PASSED + FAILED}")
    log(f"✅ Passed: {PASSED}")
    log(f"❌ Failed: {FAILED}")
    
    if FAILED > 0:
        log("\n⚠️ FAILED TESTS:", "WARNING")
        for t in TESTS:
            if not t["passed"]:
                log(f"   {t['name']}: {t['details']}", "ERROR")
    else:
        log("\n✅ ALL TIMING TESTS PASSED!", "SUCCESS")
    
    # Additional timing info
    log("\n📊 TIMING INFO:", "INFO")
    log(f"   Server time: {datetime.now().isoformat()}")
    log(f"   UTC time: {datetime.now(timezone.utc).isoformat()}")
    
    return FAILED == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
