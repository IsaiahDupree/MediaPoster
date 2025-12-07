# MediaPoster Testing & Infrastructure Documentation

> Last Updated: December 7, 2025

## Table of Contents

1. [Overview](#overview)
2. [Testing Infrastructure](#testing-infrastructure)
3. [Database Setup](#database-setup)
4. [API Endpoints](#api-endpoints)
5. [Health Checks & Diagnostics](#health-checks--diagnostics)
6. [Running Tests](#running-tests)
7. [Troubleshooting](#troubleshooting)

---

## Overview

MediaPoster is a comprehensive social media management platform with:

- **Backend**: FastAPI + SQLAlchemy (async) + PostgreSQL (Supabase)
- **Frontend**: Next.js 14 + React + TailwindCSS
- **Database**: Supabase (local development) / PostgreSQL

### Architecture

```
MediaPoster/
├── Backend/           # FastAPI application
│   ├── api/endpoints/ # API route handlers
│   ├── database/      # SQLAlchemy models & connection
│   ├── services/      # Business logic
│   ├── tests/         # Test suites
│   └── main.py        # Application entry point
├── Frontend/          # Next.js application
│   ├── src/app/       # App router pages
│   ├── src/components/# React components
│   └── e2e/tests/     # Playwright E2E tests
├── supabase/          # Database migrations
│   └── migrations/    # SQL migration files
└── scripts/           # Utility scripts
```

---

## Testing Infrastructure

### Test Types

| Type | Location | Framework | Purpose |
|------|----------|-----------|---------|
| **Smoke Tests** | `Backend/tests/test_smoke.py` | pytest + requests | Quick health checks |
| **Unit Tests** | `Backend/tests/unit/` | pytest | Isolated function tests |
| **Integration Tests** | `Backend/tests/integration/` | pytest | Multi-component tests |
| **API Tests** | `Frontend/e2e/tests/api/` | Playwright | API contract validation |
| **E2E Tests** | `Frontend/e2e/tests/` | Playwright | User flow testing |
| **Performance Tests** | `Backend/tests/performance/` | pytest | Load & response time |
| **Security Tests** | `Backend/tests/security/` | pytest | Vulnerability checks |
| **Accessibility Tests** | `Frontend/e2e/tests/accessibility.spec.ts` | Playwright + axe-core | WCAG compliance |
| **Visual Regression** | `Frontend/e2e/tests/visual/` | Playwright | Screenshot comparison |

### Test Configuration

**pytest.ini** (Backend):
```ini
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = session
testpaths = tests
filterwarnings =
    ignore::DeprecationWarning
```

**playwright.config.ts** (Frontend):
- Runs tests in Chromium, Firefox, WebKit
- Mobile viewport testing enabled
- Base URL: `http://localhost:5557`

---

## Database Setup

### Local Development with Supabase

```bash
# Start Supabase (from project root)
cd /path/to/MediaPoster
supabase start

# Apply migrations
supabase db reset

# Check status
supabase status
```

### Key Tables

| Table | Purpose |
|-------|---------|
| `social_accounts` | Connected social media accounts |
| `social_analytics_snapshots` | Daily analytics data |
| `social_analytics_config` | Monitoring configuration |
| `videos` | Video library |
| `clips` | Generated clips |
| `scheduled_posts` | Publishing queue |
| `content_items` | Content management |
| `posting_goals` | User goals |

### Important Views

| View | Purpose |
|------|---------|
| `social_analytics_latest` | Latest analytics per account |
| `social_post_performance` | Post performance metrics |
| `content_cross_platform_summary` | Cross-platform content stats |

### Migrations Applied

1. `20241121000000_everreach_blend_schema.sql` - Core schema
2. `20250121000000_content_base_tables.sql` - Content tables
3. `20250121000005-7_content_intelligence_*.sql` - Analytics
4. `20251125100000_social_accounts.sql` - Social accounts
5. `20251126000000_social_analytics_extension.sql` - Analytics views

---

## API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/social-analytics/overview` | GET | Dashboard overview |
| `/api/social-analytics/accounts` | GET | Connected accounts |
| `/api/social-analytics/trends` | GET | Analytics trends |
| `/api/social-analytics/content` | GET | Content performance |
| `/api/videos/` | GET | Video library |
| `/api/clips/` | GET | Generated clips |
| `/api/goals/` | GET | User goals |
| `/api/publishing/scheduled` | GET | Scheduled posts |
| `/api/platform/platforms` | GET | Available platforms |
| `/api/platform/posts` | GET | Published posts |
| `/docs` | GET | API documentation (Swagger) |
| `/openapi.json` | GET | OpenAPI specification |

### Authentication

Currently using mock authentication. Production will use Supabase Auth.

---

## Health Checks & Diagnostics

### Health Check Script

```bash
./scripts/health_check.sh
```

Checks:
- Backend server (port 5555)
- Frontend server (port 5557)
- Database connectivity
- API endpoint responses

### Diagnostic Script

```bash
python3 scripts/diagnose_tests.py
```

Provides:
- Backend endpoint status
- Database connectivity
- Frontend page status
- Known issue patterns
- Recommended fixes

### Manual Health Check

```bash
# Backend
curl http://localhost:5555/docs

# Frontend
curl http://localhost:5557

# Database (via API)
curl http://localhost:5555/api/social-analytics/accounts
```

---

## Running Tests

### Quick Start

```bash
# Backend smoke tests (requires running server)
cd Backend
source venv/bin/activate
pytest tests/test_smoke.py -v

# Frontend E2E tests (requires running servers)
cd Frontend
npx playwright test e2e/tests/smoke.spec.ts
```

### Full Test Suite

```bash
# From project root
./run_all_tests.sh

# Run specific test types
./run_all_tests.sh --smoke      # Quick health checks
./run_all_tests.sh --unit       # Unit tests
./run_all_tests.sh --e2e        # End-to-end tests
./run_all_tests.sh --api        # API tests
./run_all_tests.sh --security   # Security tests
```

### Test Commands Reference

```bash
# Backend Tests
cd Backend && source venv/bin/activate
pytest tests/test_smoke.py -v           # Smoke tests
pytest tests/unit/ -v                   # Unit tests
pytest tests/integration/ -v            # Integration tests
pytest tests/security/ -v               # Security tests
pytest tests/performance/ -v            # Performance tests

# Frontend Tests
cd Frontend
npm test                                # Jest unit tests
npx playwright test                     # All Playwright tests
npx playwright test --debug             # Debug mode
npx playwright test --ui                # UI mode
```

---

## Troubleshooting

### Common Issues

#### 1. "AsyncSession object has no attribute 'query'"

**Cause**: SQLAlchemy 2.0 breaking change

**Fix**: Replace sync query pattern with async:
```python
# Old (SQLAlchemy 1.x)
db.query(Model).filter_by(id=id).first()

# New (SQLAlchemy 2.0)
result = await db.execute(select(Model).where(Model.id == id))
item = result.scalar_one_or_none()
```

#### 2. "Event loop is closed" / "attached to a different loop"

**Cause**: TestClient with async database sessions

**Fix**: Use `requests` library for smoke tests against running server:
```python
import requests
response = requests.get("http://localhost:5555/api/endpoint")
```

#### 3. SQL Syntax Error with Named Parameters

**Cause**: PostgreSQL type casting (`::INTEGER`) conflicts with SQLAlchemy named parameters

**Fix**: Use `CAST()` instead:
```sql
-- Old
WHERE date >= CURRENT_DATE - :days::INTEGER

-- New  
WHERE date >= CURRENT_DATE - CAST(:days AS INTEGER)
```

#### 4. Missing Database Tables/Columns

**Fix**: Apply migrations or add columns manually:
```bash
# Apply all migrations
supabase db reset

# Add single column
docker exec supabase_db_MediaPoster psql -U postgres -d postgres \
  -c "ALTER TABLE table_name ADD COLUMN IF NOT EXISTS column_name TYPE;"
```

#### 5. Supabase Port Conflict

**Cause**: Another Supabase project using port 54322

**Fix**:
```bash
# Stop other project
supabase stop --project-id other-project-name

# Start MediaPoster
cd MediaPoster && supabase start
```

### Debug Commands

```bash
# Check server status
lsof -ti:5555,5557

# View backend logs
tail -f Backend/logs/app.log

# Test specific endpoint
curl -v http://localhost:5555/api/endpoint

# Check database tables
docker exec supabase_db_MediaPoster psql -U postgres -d postgres \
  -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public';"
```

---

## Environment Variables

### Backend (.env)

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_KEY=your-anon-key
DEBUG=true
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_API_URL=http://localhost:5555
NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

---

## Development Workflow

### Starting Development Environment

```bash
# 1. Start Supabase
cd MediaPoster && supabase start

# 2. Start Backend (Terminal 1)
cd Backend
source venv/bin/activate
uvicorn main:app --port 5555 --reload

# 3. Start Frontend (Terminal 2)
cd Frontend
npm run dev

# 4. Run health check
./scripts/health_check.sh
```

### Before Committing

```bash
# Run smoke tests
cd Backend && pytest tests/test_smoke.py -v

# Run linting
cd Frontend && npm run lint

# Run diagnostics
python3 scripts/diagnose_tests.py
```

---

## CI/CD Integration

### GitHub Actions (Recommended)

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: supabase/setup-cli@v1
      - run: supabase start
      - run: cd Backend && pip install -r requirements.txt
      - run: cd Backend && pytest tests/test_smoke.py -v

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: cd Frontend && npm ci
      - run: cd Frontend && npx playwright install
      - run: cd Frontend && npx playwright test
```

---

## Contributing

1. Create feature branch from `main`
2. Write tests for new features
3. Run full test suite before PR
4. Update documentation as needed

## Support

- Check `scripts/diagnose_tests.py` for automated troubleshooting
- Review logs in `Backend/logs/`
- Consult this documentation for common issues
