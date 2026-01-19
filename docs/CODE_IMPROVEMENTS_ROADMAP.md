# Code Improvements Roadmap

**Version:** 1.0  
**Date:** January 19, 2026  
**Status:** Active  
**Priority:** High

---

## Executive Summary

This document outlines critical code improvements and technical debt items that should be addressed to improve MediaPoster's reliability, performance, and maintainability. Items are prioritized by impact and effort.

---

## 🔴 Critical Priority (Blocking Issues)

### 1. Fix Supabase Import Error

**Status:** ❌ Blocking  
**Impact:** High - Blocks 20+ database-dependent tests  
**Effort:** 30 minutes

**Error:**
```
ImportError: cannot import name 'create_client' from 'supabase'
```

**Location:** `Backend/database/connection.py:8`

**Root Cause:** Supabase Python SDK version mismatch. The `create_client` function was renamed in newer versions.

**Fix:**
```python
# Old (broken)
from supabase import create_client

# New (correct for supabase>=2.0.0)
from supabase import create_client, Client

# Or for older versions
from supabase.client import create_client
```

**Verification Steps:**
1. Check installed version: `pip show supabase`
2. Update import based on version
3. Run test suite: `pytest Backend/tests/ -v`

---

### 2. Create 25 AI Templates

**Status:** ⚠️ Infrastructure ready, content needed  
**Impact:** High - Enables Content Ops FATE stack  
**Effort:** 4-6 hours

**Current State:**
- Template validation service exists
- Database schema ready
- No actual templates created

**Required Templates by Category:**

| Category | Count | Examples |
|----------|-------|----------|
| Educational | 5 | How-to, Tutorial, Explainer, Myth-busting, Comparison |
| Entertainment | 5 | Comedy, Reaction, Challenge, Trend, Storytelling |
| Promotional | 5 | Product demo, Testimonial, Behind-scenes, Launch, Sale |
| Engagement | 5 | Q&A, Poll, This-or-that, Hot take, Controversial |
| Personal Brand | 5 | Day-in-life, Origin story, Lessons learned, Goals, Values |

**Template Schema:**
```python
{
    "id": "uuid",
    "name": "How-To Tutorial",
    "category": "educational",
    "structure": {
        "hook": "Question or problem statement",
        "body": ["Step 1", "Step 2", "Step 3"],
        "cta": "Follow for more tips"
    },
    "best_practices": ["Keep under 60 seconds", "Show don't tell"],
    "platform_variants": {
        "tiktok": {"max_length": 60, "style": "casual"},
        "instagram": {"max_length": 90, "style": "polished"},
        "youtube": {"max_length": 60, "style": "educational"}
    }
}
```

**Implementation Location:** `Backend/services/content_ops/templates/`

---

## 🟠 High Priority (Performance & Reliability)

### 3. Add Redis Caching Layer

**Status:** ❌ Not implemented  
**Impact:** High - Significant performance improvement  
**Effort:** 1-2 days

**Current State:** No caching - every request hits database

**Recommended Cache Points:**

| Data | TTL | Invalidation |
|------|-----|--------------|
| Trend data | 5 min | On new crawl |
| Analytics queries | 1 min | On new data |
| Template leaderboard | 5 min | On template update |
| User preferences | 10 min | On preference change |
| Platform status | 30 sec | On status check |

**Implementation:**
```python
# Backend/services/cache/redis_cache.py

import redis
from functools import wraps

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def cache(ttl_seconds: int, key_prefix: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            result = await func(*args, **kwargs)
            redis_client.setex(cache_key, ttl_seconds, json.dumps(result))
            return result
        return wrapper
    return decorator
```

**Files to Create:**
- `Backend/services/cache/__init__.py`
- `Backend/services/cache/redis_cache.py`
- `Backend/services/cache/cache_keys.py`

---

### 4. Standardize Error Handling

**Status:** ⚠️ Inconsistent across endpoints  
**Impact:** Medium - Better debugging, consistent API  
**Effort:** 2-3 hours

**Current State:** Mixed error response formats across endpoints

**Proposed Standard Format:**
```json
{
    "success": false,
    "error": {
        "code": "VALIDATION_ERROR",
        "message": "Invalid input provided",
        "details": {
            "field": "email",
            "reason": "Invalid email format"
        },
        "trace_id": "abc123-def456"
    },
    "timestamp": "2026-01-19T18:00:00Z"
}
```

**Error Codes:**
| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 400 | Invalid input |
| AUTH_ERROR | 401 | Not authenticated |
| FORBIDDEN | 403 | Not authorized |
| NOT_FOUND | 404 | Resource not found |
| RATE_LIMITED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Server error |
| SERVICE_UNAVAILABLE | 503 | Dependency down |

**Implementation:**
```python
# Backend/api/exceptions.py

class APIException(Exception):
    def __init__(self, code: str, message: str, details: dict = None, status: int = 400):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status = status

# Backend/api/middleware/error_handler.py

@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "trace_id": request.state.trace_id
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    )
```

---

### 5. Improve Health Checks

**Status:** ⚠️ Basic endpoint exists  
**Impact:** Medium - Better monitoring, faster debugging  
**Effort:** 2 hours

**Current State:** Simple `/health` returns `{"status": "ok"}`

**Proposed Detailed Health Check:**
```json
{
    "status": "healthy",
    "timestamp": "2026-01-19T18:00:00Z",
    "version": "1.0.0",
    "uptime_seconds": 86400,
    "checks": {
        "database": {
            "status": "healthy",
            "latency_ms": 12,
            "connection_pool": {
                "active": 5,
                "idle": 15,
                "max": 20
            }
        },
        "redis": {
            "status": "healthy",
            "latency_ms": 2
        },
        "external_apis": {
            "blotato": {"status": "healthy", "latency_ms": 150},
            "rapidapi": {"status": "degraded", "latency_ms": 2500},
            "openai": {"status": "healthy", "latency_ms": 300}
        },
        "workers": {
            "metrics_worker": {"status": "running", "last_run": "2026-01-19T17:55:00Z"},
            "thumbnail_worker": {"status": "stopped", "error": "Connection refused"}
        }
    }
}
```

**Implementation Location:** `Backend/api/endpoints/health_api.py`

---

## 🟡 Medium Priority (Quality of Life)

### 6. Add Rate Limit Headers

**Status:** ⚠️ Rate limiting exists, headers missing  
**Impact:** Low-Medium - Better client handling  
**Effort:** 1 hour

**Required Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640000000
Retry-After: 60  (only when rate limited)
```

**Implementation:**
```python
# Backend/api/middleware/rate_limit.py

@app.middleware("http")
async def rate_limit_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Get rate limit info for this request
    limit_info = get_rate_limit_info(request)
    
    response.headers["X-RateLimit-Limit"] = str(limit_info.limit)
    response.headers["X-RateLimit-Remaining"] = str(limit_info.remaining)
    response.headers["X-RateLimit-Reset"] = str(limit_info.reset_timestamp)
    
    return response
```

---

### 7. API Versioning

**Status:** ❌ Not implemented  
**Impact:** Medium - Enables backward-compatible changes  
**Effort:** 3-4 hours

**Current State:** All endpoints under `/api/`

**Proposed Structure:**
```
/api/v1/posts          # Current stable
/api/v2/posts          # New version with breaking changes
/api/latest/posts      # Alias to latest stable version
```

**Implementation:**
```python
# Backend/api/routes/__init__.py

from fastapi import APIRouter

v1_router = APIRouter(prefix="/api/v1")
v2_router = APIRouter(prefix="/api/v2")

# Include all v1 endpoints
v1_router.include_router(posts_v1.router)
v1_router.include_router(analytics_v1.router)

# v2 with new features
v2_router.include_router(posts_v2.router)
```

---

### 8. Connection Pooling

**Status:** ⚠️ Single connection  
**Impact:** Medium - Prevents connection exhaustion  
**Effort:** 2 hours

**Current State:** Single Supabase connection per request

**Recommended Configuration:**
```python
# Backend/database/pool.py

from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,          # Maintain 10 connections
    max_overflow=20,       # Allow 20 additional under load
    pool_timeout=30,       # Wait 30s for connection
    pool_recycle=1800,     # Recycle connections after 30 min
    pool_pre_ping=True     # Verify connection before use
)
```

---

## 🟢 Low Priority (Nice to Have)

### 9. Structured JSON Logging

**Status:** ❌ Basic logging  
**Impact:** Low - Better log aggregation  
**Effort:** 2 hours

**Current State:** Plain text logs

**Proposed Format:**
```json
{
    "timestamp": "2026-01-19T18:00:00Z",
    "level": "INFO",
    "message": "Request processed",
    "trace_id": "abc123",
    "user_id": "user_456",
    "endpoint": "/api/posts",
    "method": "POST",
    "duration_ms": 150,
    "status_code": 201
}
```

---

### 10. Correlation IDs

**Status:** ❌ Not implemented  
**Impact:** Low - Better distributed tracing  
**Effort:** 1 hour

**Implementation:**
```python
# Backend/api/middleware/correlation.py

import uuid

@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    
    return response
```

---

## Implementation Priority Matrix

| Task | Impact | Effort | Priority Score |
|------|--------|--------|----------------|
| Fix Supabase import | High | Low | 🔴 **10** |
| Create 25 AI templates | High | Medium | 🔴 **9** |
| Add Redis caching | High | Medium | 🟠 **8** |
| Standardize errors | Medium | Low | 🟠 **7** |
| Improve health checks | Medium | Low | 🟡 **6** |
| Rate limit headers | Low | Low | 🟡 **5** |
| API versioning | Medium | Medium | 🟡 **5** |
| Connection pooling | Medium | Low | 🟡 **5** |
| JSON logging | Low | Low | 🟢 **3** |
| Correlation IDs | Low | Low | 🟢 **2** |

---

## Quick Wins (This Week)

| Task | Time | Command to Verify |
|------|------|-------------------|
| Fix Supabase import | 30 min | `pytest Backend/tests/ -v` |
| Add rate limit headers | 1 hr | `curl -I localhost:5555/api/posts` |
| Improve health check | 2 hrs | `curl localhost:5555/health` |
| Standardize 5 endpoints | 2 hrs | Manual API testing |

---

## Testing Verification

After implementing each improvement:

```bash
# Run full test suite
pytest Backend/tests/ -v --tb=short

# Check specific areas
pytest Backend/tests/test_database.py -v      # After Supabase fix
pytest Backend/tests/test_cache.py -v         # After Redis
pytest Backend/tests/test_api.py -v           # After error handling

# Load testing (after pooling/caching)
locust -f Backend/tests/load/locustfile.py --host=http://localhost:5555
```

---

## Monitoring After Implementation

| Metric | Target | Tool |
|--------|--------|------|
| API response time (p95) | < 200ms | Prometheus/Grafana |
| Error rate | < 1% | Logging aggregation |
| Cache hit rate | > 80% | Redis stats |
| Database connections | < 80% pool | Pool metrics |

---

**Document Owner:** Engineering Team  
**Last Updated:** January 19, 2026  
**Next Review:** February 2026
