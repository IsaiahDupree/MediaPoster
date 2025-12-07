# Real Database Tests Implementation

## Overview
All tests now use **REAL database connections** instead of mocks. This ensures we're testing actual implementations and database interactions.

---

## Setup

### Database Connection
- Tests use the **actual Supabase/PostgreSQL database**
- Database is initialized via `init_db()` before all tests
- Each test gets a fresh database session
- Tables are cleaned between tests using `TRUNCATE`

### Configuration
- Database URL: `postgresql://postgres:postgres@127.0.0.1:54322/postgres` (default)
- Can be overridden via `DATABASE_URL` environment variable
- Database must be running before tests execute

---

## Test Structure

### Fixtures

#### `setup_database` (session-scoped)
- Initializes real database connection
- Runs once before all tests
- Closes connection after all tests

#### `db_session` (function-scoped)
- Provides real async database session
- Commits on success, rolls back on error
- Automatically closes after test

#### `clean_db` (function-scoped)
- Truncates test tables before each test
- Ensures clean state for each test
- Respects foreign key constraints

---

## Test Updates

### Phase 1: Multi-Platform Analytics
✅ **All tests updated to use real database**
- `test_get_connected_accounts` - Creates real `ConnectorConfig` records
- `test_connect_account` - Actually saves accounts to database
- `test_sync_account` - Uses real account records
- `test_get_accounts_status` - Queries real database
- `test_get_dashboard_overview` - Uses real database engine

### Phase 3: Goals & Coaching
✅ **All tests updated to use real database**
- `test_get_goals` - Creates real `PostingGoal` records
- `test_create_goal` - Actually saves goals to database
- `test_get_post_social_score` - Uses real database queries
- `test_calculate_post_social_score` - Real score calculations
- All normalization tests use real database

### Phase 4: Publishing & Scheduling
✅ **All tests updated to use real database**
- `test_get_optimal_times_for_platform` - Real database queries
- `test_get_calendar_posts` - Creates real `ScheduledPost` records

### Phase 5: Media Creation
✅ **All tests updated to use real database**
- `test_create_project` - Creates real `MediaCreationProject` records
- `test_get_projects` - Queries real database
- `test_get_project` - Fetches real project data

---

## Key Changes

### Removed Mocks
- ❌ No more `AsyncMock` for database sessions
- ❌ No more `MagicMock` for query results
- ❌ No more `override_db_dependency` fixtures
- ❌ No more patching `async_session_maker`

### Added Real Implementations
- ✅ Real database connections via `async_session_maker`
- ✅ Real SQL queries and transactions
- ✅ Real data persistence and retrieval
- ✅ Real foreign key relationships

---

## Running Tests

### Prerequisites
1. **Database must be running**
   ```bash
   # If using Docker Supabase
   docker-compose up -d
   ```

2. **Environment variables set**
   ```bash
   export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
   ```

### Run All Tests
```bash
cd Backend
source venv/bin/activate
pytest tests/ -v
```

### Run Specific Phase
```bash
pytest tests/phase1/ -v
pytest tests/phase3/ -v
pytest tests/phase4/ -v
pytest tests/phase5/ -v
```

---

## Benefits

### 1. **Real Integration Testing**
- Tests actual database interactions
- Catches real SQL errors
- Validates actual data persistence

### 2. **Confidence in Implementation**
- Tests prove the code actually works
- No false positives from mocks
- Real error handling validation

### 3. **Database Schema Validation**
- Tests fail if schema is wrong
- Validates foreign key constraints
- Ensures migrations are correct

### 4. **Performance Insights**
- Real query performance
- Actual database bottlenecks
- Real transaction behavior

---

## Test Data Management

### Clean State
- Each test starts with clean database
- `clean_db` fixture truncates tables
- No test data pollution

### Test Data Creation
- Tests create their own data
- Data is cleaned after each test
- No shared state between tests

### Example Test Pattern
```python
@pytest.mark.asyncio
async def test_create_goal(self, client, db_session, clean_db):
    """Test creating a new goal with REAL database"""
    payload = {
        "goal_type": "performance",
        "goal_name": "Test Goal",
        "target_metrics": {"followers": 1000},
        "priority": 1
    }
    response = client.post("/api/goals/", json=payload)
    assert response.status_code in [200, 201]
    
    # Verify it was saved
    from sqlalchemy import select
    result = await db_session.execute(
        select(PostingGoal).where(PostingGoal.id == uuid.UUID(data["id"]))
    )
    goal = result.scalar_one_or_none()
    assert goal is not None
```

---

## Troubleshooting

### Database Not Initialized
**Error**: `Database not initialized. Call init_db() first.`

**Solution**: Ensure database is running and `DATABASE_URL` is set correctly.

### Table Does Not Exist
**Error**: `relation "table_name" does not exist`

**Solution**: Run database migrations to create tables.

### Foreign Key Violations
**Error**: `foreign key constraint fails`

**Solution**: Ensure tables are truncated in correct order (see `clean_db` fixture).

---

## Next Steps

1. ✅ Real database connections implemented
2. ✅ All phase tests updated
3. ⏳ Add more comprehensive test data scenarios
4. ⏳ Add performance benchmarks
5. ⏳ Add database migration tests

---

**Last Updated**: 2025-11-26  
**Status**: ✅ **Real Database Tests Implemented**






