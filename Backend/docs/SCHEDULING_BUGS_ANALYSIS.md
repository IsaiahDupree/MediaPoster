# Scheduling System Bug Analysis

**Date:** 2025-12-26  
**Scope:** Backend and Frontend scheduling processes

---

## 🔴 CRITICAL BUGS

### Bug 1: Race Condition in `PublisherService.mark_post_as_publishing()`

**Location:** `Backend/services/publisher_service.py:136-162`

**Problem:**
```python
async def mark_post_as_publishing(self, post_id: UUID) -> bool:
    result = await self.db.execute(
        select(ScheduledPost).where(ScheduledPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    
    if post:
        post.status = 'publishing'  # ❌ NOT ATOMIC - Race condition here!
        await self.db.commit()
```

**Issue:**
- Reads post, then updates status
- Between read and update, another process could also read and update
- No `FOR UPDATE` lock or atomic update
- Multiple workers could both mark the same post as 'publishing'

**Impact:** 
- Double publishing attempts
- Status inconsistencies
- Failed publishes due to concurrent access

**Fix Required:**
```python
async def mark_post_as_publishing(self, post_id: UUID) -> bool:
    """Atomically update status to 'publishing' only if still 'scheduled'"""
    from sqlalchemy import update
    
    result = await self.db.execute(
        update(ScheduledPost)
        .where(
            ScheduledPost.id == post_id,
            ScheduledPost.status == 'scheduled'  # Only if still scheduled
        )
        .values(status='publishing')
    )
    await self.db.commit()
    return result.rowcount > 0
```

---

### Bug 2: Multiple Publishing Paths Without Coordination

**Locations:**
- `Backend/api/endpoints/publishing.py:_publish_via_blotato()` (Background task)
- `Backend/services/post_scheduler.py:_publish_post()` (Scheduler worker)
- `Backend/tasks/scheduled_publishing.py:publish_scheduled_post()` (Celery task)

**Problem:**
Three different systems can all try to publish the same post:
1. **Background task** from `schedule_post()` - runs immediately for future posts
2. **PostScheduler** - checks every 60 seconds for due posts
3. **Celery task** - triggered by `check_scheduled_posts()` every minute

**Scenario:**
1. Post scheduled for 2:00 PM
2. At 2:00 PM, PostScheduler picks it up → status = 'publishing'
3. At 2:00 PM, Celery task also picks it up → tries to publish again
4. Both attempt to publish → double publish or conflict

**Impact:**
- Duplicate posts on platforms
- Wasted API calls
- Inconsistent status

**Fix Required:**
- Use `FOR UPDATE SKIP LOCKED` in ALL publishing paths
- Ensure only ONE system handles due posts (recommend PostScheduler only)
- Remove duplicate logic

---

### Bug 3: Status Reset Logic in `_publish_via_blotato()`

**Location:** `Backend/api/endpoints/publishing.py:333-344`

**Problem:**
```python
# If post is due now or in the past, let the scheduler handle it
if scheduled_time <= now:
    logger.info(f"Post {post_id} is due now, letting scheduler handle it")
    # Reset status back to scheduled so scheduler can pick it up
    async with async_session_maker() as db:
        await db.execute(
            update(ScheduledPost)
            .where(ScheduledPost.id == uuid.UUID(post_id))
            .values(status='scheduled')  # ❌ Resets without checking current status!
        )
        await db.commit()
    return
```

**Issue:**
- Resets status to 'scheduled' without checking if it's already 'publishing' or 'published'
- Could reset a post that's already being processed
- No atomic check-and-reset

**Impact:**
- Interrupts in-progress publishes
- Status inconsistencies
- Lost publishes

**Fix Required:**
```python
if scheduled_time <= now:
    # Only reset if still in 'publishing' state (meaning we set it but shouldn't have)
    async with async_session_maker() as db:
        result = await db.execute(
            update(ScheduledPost)
            .where(
                ScheduledPost.id == uuid.UUID(post_id),
                ScheduledPost.status == 'publishing'  # Only reset if we set it
            )
            .values(status='scheduled')
        )
        if result.rowcount == 0:
            logger.info(f"Post {post_id} already being handled by another process")
        await db.commit()
    return
```

---

## 🟡 MEDIUM BUGS

### Bug 4: Missing Transaction in Status Updates

**Location:** `Backend/services/publisher_service.py:164-198`

**Problem:**
```python
async def mark_post_as_published(...):
    result = await self.db.execute(...)
    post = result.scalar_one_or_none()
    
    if post:
        post.status = 'published'
        post.published_at = datetime.now()
        post.platform_post_id = platform_post_id
        # ... multiple field updates ...
        await self.db.commit()  # ❌ No transaction wrapper
```

**Issue:**
- Multiple field updates not wrapped in transaction
- If commit fails partway through, partial updates
- No rollback on error

**Impact:**
- Inconsistent data
- Partial status updates

**Fix Required:**
```python
async def mark_post_as_published(...):
    try:
        result = await self.db.execute(
            update(ScheduledPost)
            .where(ScheduledPost.id == post_id)
            .values(
                status='published',
                published_at=datetime.now(),
                platform_post_id=platform_post_id,
                platform_url=platform_url,
                last_error=None
            )
        )
        await self.db.commit()
        return result.rowcount > 0
    except Exception as e:
        await self.db.rollback()
        raise
```

---

### Bug 5: Frontend Status Update Race Condition

**Location:** `dashboard/app/(dashboard)/schedule/page.tsx:229-249`

**Problem:**
```typescript
// Handle publish completed - update post status
if (eventData.topic === 'publish.completed') {
  setSchedule(prev => prev.map(post => {
    if (payload.post_id && post.id === payload.post_id) {
      return {
        ...post,
        status: 'posted' as const,  // ❌ Optimistic update without verification
        platformUrl: payload.platform_url,
        publishedAt: new Date().toISOString(),
      };
    }
    return post;
  }));
  
  // Refetch schedule to ensure consistency
  fetchSchedule();  // ❌ But this happens AFTER state update
}
```

**Issue:**
- Optimistic state update before verification
- `fetchSchedule()` called after state update (async)
- If refetch fails or is slow, UI shows wrong status
- No error handling if refetch fails

**Impact:**
- UI shows incorrect status
- User confusion
- Potential for duplicate actions

**Fix Required:**
```typescript
if (eventData.topic === 'publish.completed') {
  // Refetch FIRST to get accurate state
  fetchSchedule().then(() => {
    // Then update UI if needed
    setSchedule(prev => prev.map(post => {
      if (payload.post_id && post.id === payload.post_id) {
        return {
          ...post,
          status: 'posted' as const,
          platformUrl: payload.platform_url,
          publishedAt: new Date().toISOString(),
        };
      }
      return post;
    }));
  }).catch(err => {
    console.error('Failed to refetch schedule:', err);
    // Still update optimistically but show warning
  });
}
```

---

### Bug 6: Missing Status Validation in Update Endpoint

**Location:** `Backend/api/endpoints/schedule.py:404-443`

**Problem:**
```python
# Check current status before allowing updates
with engine.connect() as conn:
    current_status_result = conn.execute(...)
    current_row = current_status_result.fetchone()
    # ... get current_status ...

# Validate status transitions
if update.status is not None and update.status != current_status:
    if current_status in ('publishing', 'published'):
        raise HTTPException(...)  # ✅ Good check
    
    # ❌ BUT: What if status changes BETWEEN check and update?
    # Another process could change status after we read it
```

**Issue:**
- Check status, then update later (non-atomic)
- Status could change between check and update
- No `FOR UPDATE` lock

**Impact:**
- Updates to posts that shouldn't be updated
- Status inconsistencies

**Fix Required:**
```python
# Use atomic update with WHERE clause to prevent race conditions
with engine.connect() as conn:
    # Check AND lock in one query
    current_status_result = conn.execute(text("""
        SELECT status, scheduled_time 
        FROM scheduled_posts 
        WHERE id = :id
        FOR UPDATE  -- Lock the row
    """), {"id": post_id})
    
    # Then update with status check in WHERE clause
    result = conn.execute(text(f"""
        UPDATE scheduled_posts 
        SET {', '.join(updates)}
        WHERE id = :id
          AND status NOT IN ('publishing', 'published')  -- Atomic check
    """), params)
```

---

## 🟢 MINOR BUGS / IMPROVEMENTS

### Bug 7: Inconsistent Error Handling

**Location:** Multiple files

**Problem:**
- Some functions return `False` on error
- Others raise exceptions
- Others return error dicts
- Inconsistent error handling makes debugging hard

**Recommendation:**
- Standardize error handling
- Use exceptions for unrecoverable errors
- Return Result objects for recoverable errors

---

### Bug 8: Missing Idempotency in Celery Tasks

**Location:** `Backend/tasks/scheduled_publishing.py:49-88`

**Problem:**
```python
def publish_scheduled_post(self, post_id: str):
    async def _publish():
        # ... no idempotency check ...
        result = await publisher.publish_scheduled_post(post_uuid)
```

**Issue:**
- Celery can retry tasks
- No idempotency check before publishing
- Could republish on retry

**Fix:**
- Check status before publishing
- Use idempotency keys
- Skip if already published

---

### Bug 9: Frontend Missing Error Recovery

**Location:** `dashboard/app/(dashboard)/schedule/page.tsx`

**Problem:**
- WebSocket connection failures not handled
- No retry logic for failed fetches
- State can get out of sync if API calls fail

**Recommendation:**
- Add WebSocket reconnection logic
- Add retry for failed API calls
- Add periodic sync to catch missed updates

---

## 📊 Summary

### Critical Bugs: 3
1. Race condition in `mark_post_as_publishing()`
2. Multiple publishing paths without coordination
3. Status reset logic issues

### Medium Bugs: 3
4. Missing transactions
5. Frontend status update race condition
6. Missing status validation in updates

### Minor Bugs: 3
7. Inconsistent error handling
8. Missing idempotency in Celery tasks
9. Frontend missing error recovery

---

## 🔧 Recommended Fix Priority

1. **IMMEDIATE:** Fix Bug 1 (Race condition in status updates)
2. **IMMEDIATE:** Fix Bug 2 (Multiple publishing paths)
3. **HIGH:** Fix Bug 3 (Status reset logic)
4. **MEDIUM:** Fix Bug 4 (Missing transactions)
5. **MEDIUM:** Fix Bug 5 (Frontend race condition)
6. **MEDIUM:** Fix Bug 6 (Status validation)
7. **LOW:** Fix Bugs 7-9 (Improvements)

---

## 🧪 Testing Recommendations

1. **Concurrency Tests:**
   - Multiple workers trying to publish same post
   - Rapid status updates
   - Concurrent schedule/update operations

2. **Race Condition Tests:**
   - Status changes during publish
   - Updates during status transitions
   - WebSocket events during API calls

3. **Idempotency Tests:**
   - Retry same publish multiple times
   - Duplicate WebSocket events
   - Repeated status updates

