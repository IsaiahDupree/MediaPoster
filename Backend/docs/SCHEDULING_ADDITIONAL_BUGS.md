# Additional Scheduling & Analysis Bugs Found

**Date:** 2025-12-26  
**Scope:** Additional bugs beyond the 6 critical ones already fixed

---

## 🔴 CRITICAL BUGS (Additional)

### Bug 7: No Analysis Verification Before Scheduling

**Location:** `Backend/api/endpoints/publishing.py:145-200`

**Problem:**
```python
# Schedule post without checking if analysis exists
# If analysis doesn't exist, post will fail when publishing
```

**Issue:**
- Can schedule posts for media that hasn't been analyzed
- Post will fail at publish time with unclear error
- No validation that analysis data exists before scheduling

**Impact:**
- Wasted scheduled posts
- Confusing error messages
- Poor user experience

**Fix Required:**
```python
# Before scheduling, verify analysis exists
analysis_result = await db.execute(
    select(VideoAnalysis).filter(VideoAnalysis.video_id == clip.video_id)
)
analysis = analysis_result.scalar_one_or_none()

if not analysis:
    raise HTTPException(
        status_code=400,
        detail="Media must be analyzed before scheduling. Please run analysis first."
    )
```

---

### Bug 8: No Media File Existence Check at Schedule Time

**Location:** `Backend/api/endpoints/publishing.py:80-145`

**Problem:**
- Can schedule posts for media files that don't exist
- No validation that file exists at schedule time
- File might be deleted between schedule and publish

**Impact:**
- Posts fail at publish time
- No early warning to user

**Fix Required:**
```python
# Verify media file exists before scheduling
if clip_id:
    clip = result.scalar_one_or_none()
    if clip and clip.file_path:
        file_path = Path(clip.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Media file not found: {clip.file_path}"
            )
```

---

### Bug 9: Timezone Handling Inconsistency

**Location:** Multiple files

**Problem:**
- Mixing timezone-aware and naive datetimes
- `datetime.now()` vs `datetime.now(timezone.utc)`
- Inconsistent timezone handling across endpoints

**Example:**
```python
# In publishing.py
now = datetime.now(timezone.utc)  # ✅ Good

# In schedule.py
now = datetime.now()  # ❌ Naive datetime
```

**Impact:**
- Incorrect time comparisons
- Scheduling at wrong times
- Timezone-related bugs

**Fix Required:**
- Standardize on `datetime.now(timezone.utc)` everywhere
- Always convert naive datetimes to UTC
- Add timezone validation

---

## 🟡 MEDIUM BUGS (Additional)

### Bug 10: Race Condition: Analysis Completes During Scheduling

**Location:** `Backend/api/endpoints/publishing.py:150-200`

**Problem:**
- User schedules post (analysis not ready)
- Analysis completes in background
- Post might use stale analysis data or miss new data

**Impact:**
- Inconsistent captions/titles
- Missing latest analysis insights

**Fix Required:**
- Always fetch latest analysis at publish time (not schedule time)
- Or: Wait for analysis completion before allowing scheduling

---

### Bug 11: Missing Platform Account Validation Before Scheduling

**Location:** `Backend/api/endpoints/publishing.py:80-145`

**Problem:**
- Can schedule posts with invalid Blotato account IDs
- No validation that account exists and is connected
- Post fails at publish time

**Impact:**
- Wasted scheduled posts
- Late error discovery

**Fix Required:**
```python
# Validate Blotato account before scheduling
# Check account exists and is connected
```

---

### Bug 12: Scheduled Time Edge Cases Not Handled

**Location:** `Backend/api/endpoints/publishing.py:126-136`

**Problem:**
```python
if request.scheduled_time < now:
    raise HTTPException(...)
```

**Issues:**
- What if `scheduled_time == now`? (exactly equal)
- What if scheduled_time is 1 millisecond in the past?
- What if clock drift causes time to be slightly in past?

**Impact:**
- Posts might be rejected incorrectly
- Edge cases cause confusion

**Fix Required:**
```python
# Use <= for exact equality, add buffer for clock drift
time_diff = (request.scheduled_time - now).total_seconds()
if time_diff < -1.0:  # Allow 1 second buffer for clock drift
    raise HTTPException(...)
```

---

### Bug 13: No Validation for Analysis Completeness

**Location:** `Backend/services/background_publisher.py:377-400`

**Problem:**
- Analysis might exist but be incomplete
- Missing transcript, topics, or platform_content
- Post publishes with incomplete data

**Impact:**
- Poor quality posts
- Missing captions/hashtags

**Fix Required:**
```python
# Check analysis completeness
if not analysis.transcript:
    logger.warning("Analysis missing transcript")
if not analysis.topics:
    logger.warning("Analysis missing topics")
# Decide: fail or proceed with partial data?
```

---

### Bug 14: Media Deletion After Scheduling Not Handled

**Location:** `Backend/services/post_scheduler.py:283-350`

**Problem:**
- Post scheduled successfully
- Media file gets deleted
- Post tries to publish → fails

**Impact:**
- Failed publishes
- No early warning

**Fix Required:**
- Check file exists at publish time
- Mark post as failed with clear error
- Optionally: Check file exists periodically before publish time

---

### Bug 15: Retry Logic Doesn't Reset on Manual Reschedule

**Location:** `Backend/api/endpoints/schedule.py:485-493`

**Problem:**
```python
if update.status == 'scheduled':
    updates.append("retry_count = 0")
```

**Issue:**
- Only resets if status is explicitly set to 'scheduled'
- If user reschedules (changes scheduled_time) but doesn't change status,
  retry_count doesn't reset
- Post might have retry_count=3 but be rescheduled

**Impact:**
- Posts might not retry after reschedule
- Inconsistent retry behavior

**Fix Required:**
```python
# Reset retry_count when rescheduling (even if status unchanged)
if update.scheduled_at is not None:
    updates.append("retry_count = 0")
    updates.append("last_error = NULL")
```

---

## 🟢 MINOR BUGS / IMPROVEMENTS

### Bug 16: No Validation for Very Far Future Scheduling

**Problem:**
- Can schedule posts years in the future
- No warning or limit

**Recommendation:**
- Add reasonable limit (e.g., 1 year)
- Warn if scheduling > 30 days in future

---

### Bug 17: Missing Caption/Title Fallback Logic

**Location:** `Backend/api/endpoints/publishing.py:150-200`

**Problem:**
- If analysis missing, falls back to generic "Check this out"
- But doesn't warn user that caption is generic

**Recommendation:**
- Warn user if using fallback caption
- Suggest running analysis first

---

### Bug 18: No Validation for Platform-Specific Requirements

**Problem:**
- Different platforms have different requirements
- No validation that content meets platform requirements
- E.g., TikTok has max caption length, Instagram has hashtag limits

**Recommendation:**
- Add platform-specific validation
- Check caption length, hashtag count, etc.

---

### Bug 19: Scheduled Time Precision Issues

**Problem:**
- Database stores timestamp with microsecond precision
- Frontend might send time with millisecond precision
- Clock drift between systems

**Recommendation:**
- Normalize to second precision
- Add buffer for clock drift

---

### Bug 20: Missing Idempotency for Schedule Endpoint

**Problem:**
- Can accidentally schedule same post twice
- No idempotency key support

**Recommendation:**
- Add idempotency key to schedule endpoint
- Prevent duplicate scheduling

---

## 📊 Summary

### Additional Critical Bugs: 3
7. No analysis verification before scheduling
8. No media file existence check
9. Timezone handling inconsistency

### Additional Medium Bugs: 8
10. Race condition: analysis completes during scheduling
11. Missing platform account validation
12. Scheduled time edge cases
13. No validation for analysis completeness
14. Media deletion after scheduling
15. Retry logic doesn't reset on reschedule
16. No validation for very far future
17. Missing caption/title fallback warning

### Minor Bugs: 4
18. No platform-specific validation
19. Scheduled time precision issues
20. Missing idempotency for schedule endpoint

---

## 🔧 Recommended Fix Priority

1. **IMMEDIATE:** Bug 7 (Analysis verification)
2. **IMMEDIATE:** Bug 8 (Media file check)
3. **HIGH:** Bug 9 (Timezone handling)
4. **HIGH:** Bug 11 (Account validation)
5. **MEDIUM:** Bug 10, 12, 13, 14, 15
6. **LOW:** Bug 16-20

---

## 🧪 Testing Recommendations

1. **Analysis Verification Tests:**
   - Schedule without analysis → should fail
   - Schedule with incomplete analysis → should warn or fail
   - Analysis completes during scheduling → should use latest

2. **Media Verification Tests:**
   - Schedule deleted media → should fail
   - Media deleted after scheduling → should fail at publish
   - Media path changes → should handle correctly

3. **Timezone Tests:**
   - Naive datetime handling
   - Timezone boundary cases
   - Clock drift handling

4. **Edge Case Tests:**
   - Schedule exactly at 'now'
   - Schedule very far future
   - Schedule 1 second in future
   - Concurrent scheduling attempts

5. **Retry Logic Tests:**
   - Retry count increments
   - Max retries reached
   - Retry reset on reschedule
   - Exponential backoff

