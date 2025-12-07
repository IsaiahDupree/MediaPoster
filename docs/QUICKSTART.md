# MediaPoster Quick Start Guide

Get up and running in 5 minutes.

## Prerequisites

- Node.js 18+
- Python 3.11+
- Docker Desktop (for Supabase)
- Supabase CLI

## 1. Start Database

```bash
cd MediaPoster
supabase start
```

Wait for "Started supabase local development setup" message.

## 2. Start Backend

```bash
cd Backend
source venv/bin/activate  # or: python -m venv venv && source venv/bin/activate
pip install -r requirements.txt  # first time only
uvicorn main:app --port 5555 --reload
```

Backend runs at: http://localhost:5555
API Docs at: http://localhost:5555/docs

## 3. Start Frontend

```bash
cd Frontend
npm install  # first time only
npm run dev
```

Frontend runs at: http://localhost:5557

## 4. Verify Everything Works

```bash
# Option 1: Health check script
./scripts/health_check.sh

# Option 2: Run diagnostics
python3 scripts/diagnose_tests.py

# Option 3: Run smoke tests
cd Backend && pytest tests/test_smoke.py -v
```

## Quick Commands

| Task | Command |
|------|---------|
| Start all services | `supabase start && cd Backend && uvicorn main:app --port 5555 --reload` |
| Run smoke tests | `cd Backend && pytest tests/test_smoke.py -v` |
| Run E2E tests | `cd Frontend && npx playwright test` |
| View API docs | Open http://localhost:5555/docs |
| View database | Open http://localhost:54323 (Supabase Studio) |
| Check health | `./scripts/health_check.sh` |
| Run diagnostics | `python3 scripts/diagnose_tests.py` |

## Common URLs

| Service | URL |
|---------|-----|
| Frontend | http://localhost:5557 |
| Backend API | http://localhost:5555 |
| API Documentation | http://localhost:5555/docs |
| Supabase Studio | http://localhost:54323 |
| Supabase API | http://localhost:54321 |

## Troubleshooting

### Port already in use?

```bash
# Find and kill process on port
lsof -ti:5555 | xargs kill -9  # Backend
lsof -ti:5557 | xargs kill -9  # Frontend
```

### Database not connecting?

```bash
# Check Supabase status
supabase status

# Restart Supabase
supabase stop && supabase start

# Reset database (applies all migrations)
supabase db reset
```

### Tests failing?

```bash
# Run diagnostics for detailed info
python3 scripts/diagnose_tests.py
```

## Next Steps

- Read [TESTING_AND_INFRASTRUCTURE.md](./TESTING_AND_INFRASTRUCTURE.md) for testing guide
- Check [CHANGELOG.md](./CHANGELOG.md) for recent changes
- Review [COMPREHENSIVE_TEST_PLAN.md](../COMPREHENSIVE_TEST_PLAN.md) for test strategy
