# Performance Tests & Accounts Page Updates

## Summary

All requested features have been implemented:

### 1. ✅ Performance Tests
Created comprehensive backend performance tests in `Backend/tests/performance/test_backend_performance.py`:

**Test Coverage:**
- **Response Time Tests**: Health checks, analytics endpoints, accounts list, comments
- **Concurrency Tests**: Multiple simultaneous requests
- **Database Query Performance**: Filtered queries, pagination
- **Memory Usage**: Detect memory leaks
- **Optimization Opportunities**: N+1 queries, caching analysis

**To Run:**
```bash
cd Backend
source venv/bin/activate
# Make sure backend server is running on localhost:5555
python -m pytest tests/performance/test_backend_performance.py -v -s
```

**Expected Results:**
- Health checks: < 50ms average
- Analytics overview: < 500ms
- Accounts list: < 300ms
- Comments endpoint: < 400ms
- Concurrent requests: All succeed
- Memory: < 50MB increase for 50 requests

### 2. ✅ Refresh Analytics with RapidAPI Warnings

**Features:**
- Refresh button on each account card
- **RapidAPI Platforms** (Twitter, LinkedIn, Pinterest, Bluesky, Instagram, TikTok) show warning dialog
- **Double-click confirmation** required for RapidAPI accounts
- Non-RapidAPI platforms (YouTube, etc.) refresh immediately
- Warning explains monthly call limits

**Implementation:**
- `Frontend/src/app/accounts/page.tsx` - Accounts page with refresh functionality
- `Backend/api/endpoints/social_accounts.py` - Added `/accounts/{account_id}/sync` endpoint
- Warning dialog shows on first click for RapidAPI accounts
- Second click (or "I Understand" button) proceeds with sync

### 3. ✅ Fixed Remove Account Popup

**Problem:** Dialog was closing immediately when clicking remove

**Solution:**
- Added `onPointerDownOutside` and `onEscapeKeyDown` handlers to prevent closing during pending operations
- Dialog now stays open until operation completes or user explicitly cancels
- Disabled cancel button during pending state
- Proper state management to prevent accidental closes

**Files Updated:**
- `Frontend/src/app/accounts/page.tsx` - Fixed AlertDialog behavior
- `Frontend/src/components/ui/alert-dialog.tsx` - Created AlertDialog component

### 4. ✅ Accounts Page with Content Count & View Graphs

**New Page:** `/accounts`

**Features:**
- **Account Cards Grid**: Shows all accounts with:
  - Platform icon and username
  - Post count
  - Follower count
  - Last synced time
  - Action buttons (Refresh, Delete, External Link)

- **Account Detail Panel**: When account is selected:
  - **Stats Grid**: Total views, likes, posts, engagement rate
  - **Views Over Time Chart**: Line graph showing views and likes trends (7d/30d/90d)
  - **Recent Posts List**: Shows last 5 posts with links and metrics

- **API Integration**:
  - `GET /api/social-analytics/accounts` - List all accounts
  - `GET /api/social-analytics/account/{account_id}/trends` - Get view trends
  - `GET /api/social-analytics/posts?account_id={id}` - Get account posts
  - `POST /api/social-analytics/accounts/{account_id}/sync` - Refresh account
  - `DELETE /api/social-analytics/accounts/{account_id}` - Remove account

**Graph Features:**
- Line chart using Recharts
- Shows views and likes over time
- Time range selector (7, 30, 90 days)
- Responsive design
- Tooltips with formatted dates

## Files Created/Modified

### New Files:
1. `Backend/tests/performance/test_backend_performance.py` - Performance test suite
2. `Frontend/src/app/accounts/page.tsx` - Accounts management page
3. `Frontend/src/components/ui/alert-dialog.tsx` - AlertDialog component

### Modified Files:
1. `Backend/api/endpoints/social_accounts.py` - Added sync endpoint
2. `Backend/api/endpoints/social_analytics.py` - Added account trends endpoint, updated posts endpoint

## Usage

### Running Performance Tests:
```bash
cd Backend
source venv/bin/activate

# Start backend server first
# Then run tests
python -m pytest tests/performance/test_backend_performance.py -v -s
```

### Accessing Accounts Page:
Navigate to `/accounts` in your frontend application.

### Refreshing Analytics:
1. Click "Refresh" button on any account card
2. For RapidAPI accounts, a warning dialog appears
3. Click "Refresh" again (double-click) or click "I Understand, Proceed"
4. Account data will be synced from the platform API

### Removing Accounts:
1. Click trash icon on account card
2. Confirmation dialog appears and stays open
3. Click "Remove Account" to confirm
4. Account is marked as inactive

## Notes

- Performance tests require the backend server to be running
- RapidAPI platforms are: twitter, linkedin, pinterest, bluesky, instagram, tiktok
- View trends require analytics snapshots to be populated (run backfill scripts)
- The accounts page automatically fetches data when an account is selected

