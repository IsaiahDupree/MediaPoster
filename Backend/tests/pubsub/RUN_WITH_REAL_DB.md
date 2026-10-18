# Running Tests with Real Database

## Prerequisites

1. **Supabase must be running locally:**
   ```bash
   # Start Supabase (if using Docker)
   supabase start
   
   # Or check if it's running
   ps aux | grep supabase
   ```

2. **Database URL must be set:**
   ```bash
   export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"
   ```

3. **Event history table must exist:**
   ```bash
   # Run migrations
   supabase migration up
   ```

## Running Tests

### All Tests (with DB when available)
```bash
cd Backend
pytest tests/pubsub/ -v
```

### Integration Tests (requires DB)
```bash
cd Backend
pytest tests/pubsub/test_integration_*.py -v
```

### E2E Tests (requires DB)
```bash
cd Backend
pytest tests/pubsub/test_e2e_*.py -v
```

### Using the Helper Script
```bash
cd Backend
python tests/pubsub/run_with_real_db.py
```

## Test Categories

### ✅ Tests that DON'T require DB:
- `test_unit_*.py` - Pure logic tests
- `test_contract_*.py` - Schema validation
- `test_idempotency_*.py` - Deduplication logic
- `test_load_performance.py` - Performance tests
- Most of `test_worker_services.py` - Worker logic

### 🔌 Tests that REQUIRE DB:
- `test_integration_event_persistence.py` - Event history
- `test_e2e_workflows.py` - Full workflows
- Some `test_worker_services.py` - Workers that persist data

## Troubleshooting

### Database not connecting?
1. Check Supabase is running: `supabase status`
2. Check DATABASE_URL: `echo $DATABASE_URL`
3. Test connection: `psql $DATABASE_URL -c "SELECT 1"`

### Tests skipping?
- Tests will automatically skip if DB is not available
- Check test output for "SKIPPED" messages
- Look for "Database not available" in logs

### async_session_maker is None?
- This happens if `init_db()` fails silently
- Check database connection string
- Check if Supabase is actually running
- Look for connection errors in logs

## Running with Real Data

To use real data from your database:

1. **Ensure you have data:**
   ```sql
   -- Check if you have videos
   SELECT COUNT(*) FROM videos;
   
   -- Check if you have events
   SELECT COUNT(*) FROM event_history;
   ```

2. **Run tests that use real data:**
   ```bash
   # Tests will use actual data from your database
   pytest tests/pubsub/test_integration_event_persistence.py -v
   ```

3. **Filter by real data:**
   ```bash
   # Only run tests that query real data
   pytest tests/pubsub/ -k "real_data or integration" -v
   ```

## Example: Full Test Run with DB

```bash
# 1. Start Supabase
supabase start

# 2. Set environment
export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54322/postgres"

# 3. Run all tests
cd Backend
pytest tests/pubsub/ -v --tb=short

# Expected: ~200 tests, most passing, some skipped if DB not available
```

