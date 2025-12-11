# TikTok Automation Test Index

## Test Categories

### 1. API Tests (No Browser Required)

| File | Tests | Description |
|------|-------|-------------|
| `test_tiktok_api.py` | ~10 | RapidAPI tiktok-scraper7 endpoints |
| `test_tiktok_features.py` | ~6 | Scheduler, API search |

**Run:**
```bash
# All API tests
pytest automation/tests/test_tiktok_api.py automation/tests/test_tiktok_features.py -v

# Just scheduler
pytest automation/tests/test_tiktok_features.py::TestScheduler -v

# Just API search  
pytest automation/tests/test_tiktok_features.py::TestAPISearch -v
```

---

### 2. Browser Automation Tests (Safari Required)

| File | Tests | Description |
|------|-------|-------------|
| `test_tiktok_browser_automation.py` | ~30 | Navigation, engagement, comments, data extraction |
| `test_pyautogui_automation.py` | ~20 | PyAutoGUI integration tests |
| `test_pyautogui_automation_full.py` | ~15 | Full engagement flows |

**Prerequisites:**
- Safari open with TikTok logged in
- Safari > Settings > Advanced > Allow JavaScript from Apple Events ✓

**Run:**
```bash
# All browser tests
pytest automation/tests/test_tiktok_browser_automation.py -v -s

# Specific categories
pytest automation/tests/test_tiktok_browser_automation.py::TestNavigation -v -s
pytest automation/tests/test_tiktok_browser_automation.py::TestEngagement -v -s
pytest automation/tests/test_tiktok_browser_automation.py::TestComments -v -s
pytest automation/tests/test_tiktok_browser_automation.py::TestDataExtraction -v -s
pytest automation/tests/test_tiktok_browser_automation.py::TestBrowserSearch -v -s
pytest automation/tests/test_tiktok_browser_automation.py::TestBrowserMessaging -v -s
pytest automation/tests/test_tiktok_browser_automation.py::TestFullEngagementFlow -v -s
```

---

### 3. PRD Requirement Tests

| File | Tests | Description |
|------|-------|-------------|
| `tests/test_prd_requirements.py` | 154 | Backend unit tests for PRD |
| `tests/test_prd_integration.py` | 51 | Integration/E2E tests |

**Run:**
```bash
# All PRD tests
pytest tests/test_prd_requirements.py tests/test_prd_integration.py -v

# Specific sections
pytest tests/test_prd_requirements.py::TestSchedulingAlgorithm -v
pytest tests/test_prd_requirements.py::TestAICoachInsights -v
```

---

### 4. Regression/Smoke Tests

| File | Tests | Description |
|------|-------|-------------|
| `test_regression_smoke_api.py` | 54 | Smoke tests for automation API |

**Run:**
```bash
pytest automation/tests/test_regression_smoke_api.py -v
```

---

## Quick Reference

### Run All Tests (No Browser)
```bash
cd Backend
source venv/bin/activate
pytest automation/tests/test_tiktok_api.py \
       automation/tests/test_tiktok_features.py \
       automation/tests/test_regression_smoke_api.py \
       tests/test_prd_requirements.py \
       tests/test_prd_integration.py -v
```

### Run All Browser Tests
```bash
cd Backend
source venv/bin/activate
pytest automation/tests/test_tiktok_browser_automation.py -v -s
```

### Run Everything
```bash
cd Backend
source venv/bin/activate
pytest automation/tests/ tests/test_prd*.py -v
```

---

## Test Counts

| Category | Count |
|----------|-------|
| API Tests | ~16 |
| Browser Tests | ~65 |
| PRD Tests | ~205 |
| Regression Tests | ~54 |
| **Total** | **~340** |

---

## Environment Variables

| Variable | Required For |
|----------|--------------|
| `RAPIDAPI_KEY` | API tests, scheduler |
| `DATABASE_URL` | Database scheduler tests |

```bash
# Load from .env
export $(cat .env | xargs)

# Or set manually
export RAPIDAPI_KEY="your_key"
export DATABASE_URL="postgresql://postgres:postgres@localhost:54322/postgres"
```
