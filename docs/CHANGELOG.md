# MediaPoster Changelog

## [Unreleased] - December 7, 2025

### Testing Infrastructure

#### Added
- **Comprehensive Test Suite** - Full testing infrastructure with multiple test types:
  - Smoke tests (`Backend/tests/test_smoke.py`)
  - Unit tests (`Backend/tests/unit/`)
  - Integration tests (`Backend/tests/integration/`)
  - API contract tests (`Backend/tests/contract/`)
  - Security tests (`Backend/tests/security/`)
  - Performance tests (`Backend/tests/performance/`)
  - Regression tests (`Backend/tests/regression/`)
  - Load tests with Locust (`Backend/tests/load/`)
  
- **Frontend E2E Tests** (Playwright):
  - Smoke tests (`Frontend/e2e/tests/smoke.spec.ts`)
  - API tests (`Frontend/e2e/tests/api/`)
  - Accessibility tests (`Frontend/e2e/tests/accessibility.spec.ts`)
  - Visual regression tests (`Frontend/e2e/tests/visual/`)
  - User flow tests (`Frontend/e2e/tests/user-flows/`)
  - UI regression tests (`Frontend/e2e/tests/regression/`)

- **Health Check Script** (`scripts/health_check.sh`):
  - Validates backend server (port 5555)
  - Validates frontend server (port 5557)
  - Checks database connectivity
  - Tests API endpoint health
  - Color-coded output with pass/fail/warning status

- **Diagnostic Script** (`scripts/diagnose_tests.py`):
  - Comprehensive endpoint testing
  - Database connectivity validation
  - Known issue pattern detection
  - Automated fix suggestions

- **Test Runner** (`run_all_tests.sh`):
  - Categorized test execution
  - Pre-test health checks
  - Support for `--smoke`, `--unit`, `--e2e`, `--api`, `--security`, `--performance` flags
  - Backend-only and frontend-only options

- **Test Plan Document** (`COMPREHENSIVE_TEST_PLAN.md`):
  - Test organization strategy
  - Command reference
  - CI/CD integration guide

### Database

#### Added
- **Social Accounts Migration** (`20251125100000_social_accounts.sql`):
  - `social_accounts` table for tracking connected platforms
  - Support for all 9 platforms (TikTok, Instagram, YouTube, etc.)
  - OAuth token storage
  - Workspace association

- **Social Analytics Extension** (`20251126000000_social_analytics_extension.sql`):
  - `social_analytics_config` - Monitoring configuration
  - `social_analytics_snapshots` - Daily metrics
  - `social_posts_analytics` - Post tracking
  - `social_post_metrics` - Historical performance
  - `social_hashtags` - Hashtag analytics
  - `social_comments` - Comment tracking
  - `social_audience_demographics` - Audience data
  - `social_api_usage` - API tracking
  - `social_fetch_jobs` - Job management
  - `social_analytics_latest` view
  - `social_post_performance` view

#### Fixed
- Added missing `thumbnail_url` column to `content_items` table
- Added missing `file_size` column to `videos` table
- Fixed `content_cross_platform_summary` view (removed non-existent columns)
- Fixed `workspace_architecture` migration (changed `auth.safe_user_id` to `public.safe_user_id`)

### Backend

#### Added
- **New Endpoint** - `GET /api/publishing/scheduled`:
  - Returns list of scheduled posts
  - Supports `limit` and `status` query parameters
  - Returns empty array when no posts exist

#### Fixed
- **SQL Parameter Binding** (`api/endpoints/social_analytics.py`):
  - Changed `:days::INTEGER` to `CAST(:days AS INTEGER)`
  - Fixes psycopg2 syntax error with named parameters

- **AsyncSession Compatibility** (`api/endpoints/platform_publishing.py`):
  - Converted `list_posts`, `get_post_details`, `schedule_post_checkbacks` to async
  - Replaced `db.query()` with `select()` + `await db.execute()`
  - Uses SQLAlchemy 2.0 patterns

- **Platforms Endpoint** (`api/endpoints/platform_publishing.py`):
  - Converted `get_available_platforms` to async
  - Removed unnecessary database dependency
  - Returns platform types directly from enum

- **OpenAPI Spec Error** (`api/endpoints/coaching.py`):
  - Added missing `List` import from typing
  - Fixes Pydantic type definition error

### Frontend

#### Added
- **Videos Page Redirect** (`src/app/videos/page.tsx`):
  - Redirects `/videos` to `/video-library`
  - Resolves 404 error on videos route

### Tests

#### Fixed
- **Smoke Tests** (`Backend/tests/test_smoke.py`):
  - Rewrote to use `requests` library instead of `TestClient`
  - Avoids async event loop conflicts with `AsyncSession`
  - Tests against running server at configurable `BACKEND_URL`

- **pytest Configuration** (`Backend/pytest.ini`):
  - Changed `asyncio_default_fixture_loop_scope` to `session`
  - Added deprecation warning filters

### Documentation

#### Added
- `docs/TESTING_AND_INFRASTRUCTURE.md` - Comprehensive testing guide
- `docs/CHANGELOG.md` - This file

---

## Previous Versions

### Initial Release

- FastAPI backend with async SQLAlchemy
- Next.js 14 frontend with App Router
- Supabase for database and auth
- Multi-platform social media analytics
- Video library and clip generation
- Content scheduling and publishing
- AI coaching recommendations
- Goals and recommendations engine
