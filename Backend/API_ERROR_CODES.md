# API Error Codes Explanation

## RapidAPI Social Media Integration Errors

### Current Status

| Platform | Status Code | Meaning | Solution |
|----------|-------------|---------|----------|
| **Instagram** | 401 Unauthorized | API key not authorized for this endpoint | Need RapidAPI subscription |
| **TikTok** | 200 OK | ✅ Working | No action needed |
| **Twitter/X** | 403 Forbidden | Access denied to endpoint | Need RapidAPI subscription |
| **YouTube** | 200 OK | ✅ Working (via YouTube Data API v3) | No action needed |

---

## Error Code Details

### 401 Unauthorized - Instagram
```
📸 Instagram API Response: 401
```

**What it means:**
- Your RapidAPI key exists but doesn't have access to the Instagram Scraper API endpoint
- The API requires a paid subscription plan

**Why it happens:**
- Free tier doesn't include Instagram API access
- Or subscription expired
- Or wrong API endpoint being used

**Solution:**
1. Go to [RapidAPI Instagram Scraper](https://rapidapi.com/restyler/api/instagram-scraper-api2)
2. Subscribe to a plan (Basic, Pro, or Ultra)
3. Verify subscription is active
4. Re-run tests

**Cost:**
- Basic: ~$10-20/month for limited requests
- Pro: ~$50-100/month for more requests
- Check current pricing on RapidAPI

---

### 403 Forbidden - Twitter/X
```
𝕏 Twitter API Response: 403
```

**What it means:**
- Access to this specific endpoint is forbidden
- Similar to 401 but specifically means "I know who you are, but you can't access this"

**Why it happens:**
- Twitter API endpoint requires specific subscription
- Rate limits exceeded
- Endpoint deprecated or changed

**Solution:**
1. Check [RapidAPI Twitter API](https://rapidapi.com/omarmhaimdat/api/twitter241)
2. Verify subscription status
3. Check if endpoint URL is correct
4. Consider alternative Twitter APIs on RapidAPI

**Alternative:**
- Use Twitter's official API (requires Twitter Developer account)
- Use different RapidAPI Twitter provider

---

### 200 OK - TikTok ✅
```
🎵 TikTok API Response: 200
   Username: isaiah_dupree
   Followers: 496
   Likes: 7,076
```

**Status:** Working perfectly!
- Successfully fetching data
- No subscription issues
- Free tier or active subscription

---

### 200 OK - YouTube ✅
```
YouTube Data API returned 200
   Followers: 2,810
   Posts: 639
```

**Status:** Working perfectly!
- Using direct YouTube Data API v3 (not RapidAPI)
- Free tier: 10,000 quota units/day
- More reliable than RapidAPI

---

## Other Common HTTP Error Codes

### 400 Bad Request
**What it means:**
- The request was malformed
- Missing required parameters
- Invalid parameter values

**Example causes:**
```python
# Missing username
response = api.get("/user/info")  # ❌ No username provided

# Invalid format
response = api.get("/user/info", params={"username": ""})  # ❌ Empty username
```

**Solution:**
- Check request parameters
- Validate input data
- Review API documentation

---

### 404 Not Found
**What it means:**
- Endpoint doesn't exist
- Resource not found

**Example:**
```
GET /api/nonexistent-endpoint → 404
```

**Solution:**
- Verify endpoint URL
- Check API documentation
- Ensure resource exists

---

### 405 Method Not Allowed
**What it means:**
- Endpoint exists but doesn't support this HTTP method

**Example:**
```
POST /api/media-db/regenerate-thumbnails → 405
(Endpoint only accepts DELETE)
```

**Solution:**
- Use correct HTTP method (GET, POST, PUT, DELETE)
- Check API documentation

---

### 422 Unprocessable Entity
**What it means:**
- Request is valid but contains semantic errors
- Data validation failed

**Example:**
```python
# Invalid UUID format
GET /api/media-db/invalid-uuid-123 → 422
```

**Solution:**
- Validate data format
- Check UUID/ID format
- Review validation rules

---

### 429 Too Many Requests
**What it means:**
- Rate limit exceeded
- Too many requests in short time

**RapidAPI Rate Limits:**
- Free tier: ~100-500 requests/month
- Basic: ~10,000 requests/month
- Pro: ~100,000 requests/month

**Solution:**
```python
# Add delays between requests
import asyncio
await asyncio.sleep(0.5)  # 500ms delay

# Implement exponential backoff
for attempt in range(3):
    try:
        response = await api.get(...)
        break
    except RateLimitError:
        await asyncio.sleep(2 ** attempt)
```

---

### 500 Internal Server Error
**What it means:**
- Server-side error
- API crashed or encountered unexpected error

**Solution:**
- Retry request
- Check API status page
- Report to API provider if persistent

---

## Fixing Instagram & Twitter Access

### Option 1: Subscribe to RapidAPI Plans

**Instagram Scraper API:**
```bash
# Visit and subscribe
https://rapidapi.com/restyler/api/instagram-scraper-api2

# Plans:
- Basic: $9.99/month (10,000 requests)
- Pro: $49.99/month (100,000 requests)
```

**Twitter API:**
```bash
# Visit and subscribe
https://rapidapi.com/omarmhaimdat/api/twitter241

# Plans:
- Basic: $14.99/month (5,000 requests)
- Pro: $49.99/month (50,000 requests)
```

### Option 2: Use Alternative APIs

**Instagram Alternatives:**
- Instagram Graph API (official, requires Facebook Developer account)
- Other RapidAPI Instagram providers
- Web scraping (against ToS, not recommended)

**Twitter Alternatives:**
- Twitter API v2 (official, requires Twitter Developer account)
- Other RapidAPI Twitter providers

### Option 3: Mock Data for Testing

```python
# For development/testing without API costs
if os.getenv("USE_MOCK_DATA") == "true":
    return AccountAnalytics(
        platform=Platform.INSTAGRAM,
        username=username,
        followers_count=1000,  # Mock data
        posts_count=50,
        # ...
    )
```

---

## Testing Error Handling

### Run Tests to See All Error Codes
```bash
# See detailed error responses
pytest tests/test_rapidapi_integration.py::TestRapidAPIConnection -v -s

# Expected output:
# 📸 Instagram API Response: 401  ← Needs subscription
# 🎵 TikTok API Response: 200     ← Working
# 𝕏 Twitter API Response: 403     ← Needs subscription
```

### Check Current API Status
```bash
# Test each platform
python scripts/populate_social_analytics.py

# Output shows which APIs work:
# ✅ tiktok/@isaiah_dupree: 496 followers
# ⚠️ instagram/@the_isaiah_dupree: 0 followers (401)
# ⚠️ twitter/@IsaiahDupree7: 0 followers (403)
```

---

## Summary

### Working APIs (No Action Needed)
- ✅ **TikTok** - Fetching live data
- ✅ **YouTube** - Using YouTube Data API v3

### Need Subscription
- ⚠️ **Instagram** - 401 Unauthorized → Subscribe to RapidAPI plan
- ⚠️ **Twitter** - 403 Forbidden → Subscribe to RapidAPI plan

### Not Yet Implemented
- ⏭️ **Pinterest** - No fetcher
- ⏭️ **Threads** - No fetcher
- ⏭️ **Bluesky** - No fetcher
- ⏭️ **Facebook** - No fetcher

### Total Cost to Enable All
- Instagram: ~$10-50/month
- Twitter: ~$15-50/month
- **Total: ~$25-100/month** depending on usage tier

---

## Monitoring API Health

### Check API Status
```bash
# Run health check
curl http://localhost:5555/health

# Check social analytics
curl http://localhost:5555/api/social-analytics/overview
```

### View Detailed Logs
```bash
# Run tests with logging
pytest tests/test_backend_detailed_logs.py -v -s --log-cli-level=INFO
```

### Track API Calls
```python
# In tests/test_rapidapi_integration.py
# Each test shows:
# - Request URL
# - Response status code
# - Response body
# - Error messages
```
