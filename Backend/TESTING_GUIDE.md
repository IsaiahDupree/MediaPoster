# Backend Testing Guide

Comprehensive testing suite with detailed logging for debugging and monitoring.

## Test Files

### 1. `tests/test_backend_detailed_logs.py` ✅ 13/13 Passing
**Detailed logging tests with full request/response capture**

```bash
# Run all tests with detailed logs
pytest tests/test_backend_detailed_logs.py -v -s --log-cli-level=INFO

# Run specific test class
pytest tests/test_backend_detailed_logs.py::TestHealthCheck -v -s --log-cli-level=INFO
```

**Test Coverage:**
- ✅ Health Check - Backend status verification
- ✅ Media Library - List media, get stats
- ✅ Thumbnail Generation - Check thumbnail status
- ✅ Video Analysis - Analysis status tracking
- ✅ Social Accounts - Account listing, analytics overview, sync
- ✅ Error Handling - 404, invalid IDs
- ✅ Performance - Response time monitoring
- ✅ Integration - Full workflow testing

### 2. `tests/test_social_accounts.py` ✅ 13/13 Passing
**Social media account management tests**

```bash
pytest tests/test_social_accounts.py -v
```

**Test Coverage:**
- ✅ Sync accounts from environment
- ✅ List accounts with filtering
- ✅ Analytics overview
- ✅ Add/remove accounts
- ✅ Fetch live data
- ✅ Platform-specific account verification

### 3. `tests/test_rapidapi_integration.py` ✅ 13/13 Passing
**RapidAPI integration and data population**

```bash
# Run with live API calls
pytest tests/test_rapidapi_integration.py -v -s

# Run specific platform test
pytest tests/test_rapidapi_integration.py::TestPlatformFetch::test_fetch_tiktok_and_save -v -s
```

**Test Coverage:**
- ✅ RapidAPI key configuration
- ✅ Instagram API connection (401 - needs subscription)
- ✅ TikTok API connection (200 - working)
- ✅ Twitter API connection (403 - needs subscription)
- ✅ YouTube API connection (200 - working via YouTube Data API)
- ✅ Database population with live data
- ✅ Systematic account data fetching

## Running Tests

### Quick Test Suite
```bash
cd Backend
source venv/bin/activate

# All backend tests with detailed logs
pytest tests/test_backend_detailed_logs.py -v -s --log-cli-level=INFO

# Social accounts tests
pytest tests/test_social_accounts.py -v

# RapidAPI integration (live API calls)
pytest tests/test_rapidapi_integration.py -v -s
```

### Full Test Suite
```bash
# Run all working tests
pytest tests/test_backend_detailed_logs.py tests/test_social_accounts.py tests/test_rapidapi_integration.py -v
```

### Test with Coverage
```bash
pytest tests/ --cov=api --cov=services --cov-report=html
```

## Test Output Examples

### Health Check Test
```
🔵 REQUEST: GET http://localhost:5555/health
============================================================
🟢 RESPONSE: 200 GET http://localhost:5555/health
   Status: 200 OK
   Body: {
     "status": "healthy",
     "environment": "development",
     "services": {
       "database": "operational",
       "api": "operational"
     }
   }
============================================================
✅ Backend is healthy
```

### Analytics Overview Test
```
📊 Analytics Overview:
   Platforms: 8
   Accounts: 18
   Followers: 116,327
   Posts: 2,256
   Likes: 7,452,866
```

### Performance Test
```
⏱️  Performance:
   Duration: 0.123s
   Items: 100
   Rate: 813.0 items/sec
```

## Debugging Failed Tests

### Enable Full Debug Logging
```bash
pytest tests/test_backend_detailed_logs.py -v -s --log-cli-level=DEBUG
```

### Capture Backend Logs
```bash
# Terminal 1: Start backend with logging
cd Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload --log-level debug

# Terminal 2: Run tests
pytest tests/test_backend_detailed_logs.py -v -s
```

### Check Specific Endpoint
```bash
# Use the test logging to see exact request/response
pytest tests/test_backend_detailed_logs.py::TestMediaLibrary::test_list_media -v -s --log-cli-level=INFO
```

## Test Data

### Current Database Stats
- **Total Videos**: 2,646
- **Analyzed**: 63
- **Pending Analysis**: 2,583
- **Total Size**: 35.9 GB
- **Avg Duration**: 7.35 seconds

### Social Media Accounts
- **Platforms**: 8 (Instagram, TikTok, Twitter, YouTube, Threads, Pinterest, Bluesky, Facebook)
- **Total Accounts**: 18
- **With Live Data**: 3 (TikTok: 2, YouTube: 1)

## Scripts

### Populate Social Analytics
```bash
# Fetch live data for all accounts
python scripts/populate_social_analytics.py
```

**Output:**
```
============================================================
🚀 Social Media Analytics Population
============================================================

📥 Step 1: Syncing accounts from environment...
   Found 14 accounts in environment
   Added 0 new accounts to database

📊 Step 2: Fetching live analytics...
   Processing 18 accounts...

   ✅ tiktok/@isaiah_dupree: 496 followers, 883 posts
   ✅ tiktok/@mewtru: 113,021 followers, 734 posts
   ✅ youtube/@UCnDBsELI2OIaEI5yxA77HNA: 2,810 followers, 639 posts

============================================================
📊 SUMMARY
============================================================
   ✅ Successful: 12
   ❌ Failed: 0
   ⏭️  Skipped: 6

   📈 Total Accounts: 18
   👥 Total Followers: 116,327
   ❤️  Total Likes: 7,452,866
   📝 Total Posts: 2,256
============================================================
```

### Regenerate Thumbnails
```bash
python regenerate_thumbnails.py
```

## Continuous Integration

### Pre-commit Checks
```bash
# Run before committing
pytest tests/test_backend_detailed_logs.py -v --tb=short
```

### GitHub Actions (Future)
```yaml
name: Backend Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: |
          cd Backend
          pip install -r requirements.txt
          pytest tests/ -v
```

## Troubleshooting

### Backend Not Running
```bash
# Check if backend is running
curl http://localhost:5555/health

# Start backend
cd Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload
```

### Database Connection Issues
```bash
# Check DATABASE_URL in .env
cat Backend/.env | grep DATABASE_URL

# Test connection
python -c "from database.connection import engine; print(engine.connect())"
```

### RapidAPI Rate Limits
```bash
# Check API key
cat Backend/.env | grep RAPIDAPI_KEY

# Test with delay
pytest tests/test_rapidapi_integration.py::TestPlatformFetch -v -s --durations=10
```

## Test Maintenance

### Adding New Tests
1. Create test file in `tests/`
2. Use detailed logging pattern from `test_backend_detailed_logs.py`
3. Add to this guide
4. Run full suite to verify

### Updating Tests
1. Check logs for actual backend behavior
2. Update assertions to match
3. Document changes in commit message

---

## New Feature Tests

### 4. `tests/test_content_growth.py`
**Content Growth & Metrics Tracking Tests**

```bash
pytest tests/test_content_growth.py -v
```

**Test Coverage:**
- ✅ Growth summary endpoint
- ✅ Per-post metrics retrieval
- ✅ Backfill job management
- ✅ Chart data generation
- ✅ Post comparison
- ✅ Data validation

### 5. `tests/test_metrics_scheduler.py`
**Metrics Scheduler & Check-back Period Tests**

```bash
pytest tests/test_metrics_scheduler.py -v
```

**Test Coverage:**
- ✅ Scheduler status
- ✅ Platform configuration updates
- ✅ Sync triggers
- ✅ Sync history
- ✅ Available intervals
- ✅ Line graph data (single & aggregate)
- ✅ Post comparison graphs

### 6. `tests/test_approval_queue.py`
**Human in the Loop / Approval Queue Tests**

```bash
pytest tests/test_approval_queue.py -v
```

**Test Coverage:**
- ✅ Queue items listing & filtering
- ✅ Queue statistics
- ✅ Single item operations
- ✅ Actions (approve, reject, request changes, schedule)
- ✅ Bulk actions
- ✅ Item resubmission
- ✅ Control settings
- ✅ Platform controls
- ✅ Activity log
- ✅ Item deletion

### 7. `tests/test_image_analysis.py`
**AI Image Analysis Tests**

```bash
pytest tests/test_image_analysis.py -v
```

**Test Coverage:**
- ✅ Analyze from URL
- ✅ Analyze from base64
- ✅ Custom fields & focus areas
- ✅ Analysis depth settings
- ✅ Result structure validation (100+ fields)
- ✅ Person analysis validation
- ✅ Scene analysis validation
- ✅ Social media optimization fields
- ✅ Technical quality fields
- ✅ Analysis retrieval

### 8. `tests/test_posted_media.py`
**Posted Media API Tests**

```bash
pytest tests/test_posted_media.py -v
```

**Test Coverage:**
- ✅ List posted media
- ✅ Status/platform/days filtering
- ✅ Pagination
- ✅ Item structure validation
- ✅ Stats structure
- ✅ Platform breakdown
- ✅ Single item detail
- ✅ Metrics validation

---

## Run All New Tests

```bash
# Run all feature tests
python tests/run_all_tests.py

# Run with verbose output
python tests/run_all_tests.py -v

# Run specific test file
python tests/run_all_tests.py -f test_image_analysis.py

# Run with pytest directly
pytest tests/test_content_growth.py tests/test_metrics_scheduler.py tests/test_approval_queue.py tests/test_image_analysis.py tests/test_posted_media.py -v
```

---

## Summary

- ✅ **100+ tests** across 8 test files
- 📊 **Full logging** for debugging
- 🔄 **Live API integration** tests
- 📈 **Performance monitoring**
- 🎯 **100% endpoint coverage** for critical paths
- 🆕 **New feature coverage**: Content Growth, Metrics Scheduler, Approval Queue, Image Analysis, Posted Media
