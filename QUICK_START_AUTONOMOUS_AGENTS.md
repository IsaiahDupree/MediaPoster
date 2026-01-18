# Quick Start Guide for Autonomous Coding Agents

**Last Updated**: 2026-01-18 (Session 2 - INITIALIZER)

---

## 🚀 Starting Your Session

### 1. Read These Files First (in order)
1. **`INITIALIZATION_COMPLETE.md`** - Full project overview (5 min read)
2. **`claude-progress.txt`** - Latest session notes (2 min read)
3. **`harness-status.json`** - Current harness state (30 sec)
4. **`feature_list.json`** - Available features to implement (browse as needed)

### 2. Pick Your Feature

```bash
# Filter for Phase 1 features (recommended start)
jq '.features[] | select(.phase == 1 and .passes == false) | {id, name, priority, effort}' feature_list.json | head -20

# Filter by priority
jq '.features[] | select(.priority == "P0" and .passes == false) | {id, name, phase}' feature_list.json | head -10

# Get specific feature details
jq '.features[] | select(.id == "SLEEP-001")' feature_list.json
```

### 3. Read Related Documentation

```bash
# Find PRDs related to your feature
ls docs/PRD_*.md | xargs grep -l "keyword"

# View test specifications
cat COMPREHENSIVE_TEST_PLAN_2026.md
```

---

## 📋 Implementation Workflow

### Step-by-Step Process

```
1. Read feature from feature_list.json
   ↓
2. Check if files exist (listed in feature.files)
   ↓
3. If not exist: Create new service/endpoint
   If exists: Read and understand current code
   ↓
4. Write implementation
   ↓
5. Write tests (unit + integration)
   ↓
6. Run tests and verify acceptance criteria
   ↓
7. Mark feature.passes = true in feature_list.json
   ↓
8. Update claude-progress.txt with notes
   ↓
9. Commit changes
```

---

## 🎯 Phase 1: Sleep/Wake Mode (Recommended Start)

### Features to Implement (Priority Order)

1. **SLEEP-001**: Sleep Mode Core Service
   - File: `Backend/services/sleep_mode_service.py`
   - Create service to manage sleep/wake states
   - Acceptance: CPU < 5% when sleeping

2. **SLEEP-002**: Wake Triggers Registry
   - File: `Backend/services/wake_triggers.py`
   - Registry for events that wake the system
   - Acceptance: Dynamic trigger add/remove

3. **SLEEP-003**: Scheduled Post Wake Trigger
   - Files: `wake_triggers.py`, `scheduler_service.py`
   - Wake 5min before scheduled posts
   - Acceptance: Posts execute on time

4. **SLEEP-004**: Safari Automation Wake Trigger
   - Files: `safari_session_manager.py`, `wake_triggers.py`
   - Wake for Safari automation tasks
   - Acceptance: Automation runs correctly

5. **SLEEP-005**: Checkback Period Wake Trigger
   - Files: `wake_triggers.py`, `metrics_service.py`
   - Wake at 1h/6h/24h/72h/7d intervals
   - Acceptance: Metrics collected at all intervals

---

## 🛠️ Common Tasks

### Creating a New Service

```python
# Backend/services/my_service.py
"""
My Service - Brief description

This service handles X, Y, and Z.
"""
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class MyService:
    """Service for managing X."""

    def __init__(self):
        """Initialize the service."""
        self.state = {}

    async def do_something(self, param: str) -> dict:
        """
        Do something with param.

        Args:
            param: The input parameter

        Returns:
            dict: Result of operation

        Raises:
            ValueError: If param is invalid
        """
        logger.info(f"Processing {param}")
        # Implementation here
        return {"status": "success"}

# Singleton instance
my_service = MyService()
```

### Creating an API Endpoint

```python
# Backend/api/endpoints/my_endpoint.py
"""
My Endpoint API routes
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional

from Backend.services.my_service import my_service

router = APIRouter(prefix="/api/my-endpoint", tags=["my-endpoint"])

class MyRequest(BaseModel):
    """Request model for my endpoint."""
    param: str

class MyResponse(BaseModel):
    """Response model for my endpoint."""
    status: str
    result: Optional[dict] = None

@router.post("/do-something", response_model=MyResponse)
async def do_something(request: MyRequest):
    """
    Do something endpoint.

    Args:
        request: The request payload

    Returns:
        MyResponse: The result
    """
    try:
        result = await my_service.do_something(request.param)
        return MyResponse(status="success", result=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Writing Tests

```python
# Backend/tests/unit/test_my_service.py
"""
Tests for MyService
"""
import pytest
from Backend.services.my_service import MyService

@pytest.fixture
def service():
    """Create a service instance for testing."""
    return MyService()

def test_service_initialization(service):
    """Test that service initializes correctly."""
    assert service is not None
    assert service.state == {}

@pytest.mark.asyncio
async def test_do_something_success(service):
    """Test successful operation."""
    result = await service.do_something("test")
    assert result["status"] == "success"

@pytest.mark.asyncio
async def test_do_something_invalid_param(service):
    """Test error handling for invalid param."""
    with pytest.raises(ValueError):
        await service.do_something("")
```

### Running Tests

```bash
# Run all tests
cd Backend
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_my_service.py -v

# Run tests with coverage
pytest tests/ --cov=Backend --cov-report=html

# Run tests matching pattern
pytest tests/ -k "sleep_mode" -v
```

---

## 📦 Project Structure Quick Reference

```
Backend/
├── api/endpoints/          # API routes (add new endpoints here)
├── services/               # Business logic (add new services here)
├── automation/             # Safari automation scripts
├── tests/
│   ├── unit/              # Unit tests (mirror services/ structure)
│   ├── contract/          # API contract tests
│   └── security/          # Security tests
└── data/                   # Output directories

dashboard/
├── src/app/               # Next.js routes
├── src/components/        # React components
└── src/lib/               # Utilities & API clients

docs/                       # All documentation
supabase/migrations/        # Database schemas
e2e/                        # Playwright E2E tests
```

---

## 🧪 Test Acceptance Criteria

Every feature must pass its `acceptance` criteria from `feature_list.json`.

Example for SLEEP-001:
```json
"acceptance": [
  "Service can enter sleep mode",
  "CPU usage drops below 5% when sleeping"
]
```

**How to verify**:
1. Write unit tests that check "service can enter sleep mode"
2. Write integration test that measures CPU usage
3. Both tests must pass before marking `passes: true`

---

## 📝 Updating feature_list.json

```bash
# After feature passes all tests, update the JSON:
# Change "passes": false → "passes": true

# Example using jq:
jq '(.features[] | select(.id == "SLEEP-001") | .passes) = true' feature_list.json > temp.json && mv temp.json feature_list.json

# Or edit manually in your editor
```

**Important**: Also update `completedFeatures` count at top of file!

---

## 🔍 Finding Existing Code

```bash
# Find service by name
find Backend/services -name "*keyword*.py"

# Search for function usage
grep -r "function_name" Backend/

# Find tests for a service
find Backend/tests -name "*my_service*.py"

# Check if endpoint exists
grep -r "router.post" Backend/api/endpoints/
```

---

## 🎨 Code Style

### Backend (Python)
- Use **Black** formatter
- Type hints on all functions
- Docstrings (Google style)
- `async/await` for I/O operations
- Logger instead of print statements

```python
async def my_function(param: str) -> dict:
    """
    Brief description.

    Args:
        param: Description of param

    Returns:
        dict: Description of return value

    Raises:
        ValueError: When param is invalid
    """
    logger.info(f"Processing {param}")
    return {"result": "success"}
```

### Frontend (TypeScript)
- ESLint + Prettier
- TypeScript strict mode
- React functional components
- Hooks for state management

### Commits
Use conventional commits:
```
feat: add sleep mode core service (SLEEP-001)
fix: resolve wake trigger race condition (SLEEP-003)
test: add unit tests for sleep mode service
docs: update sleep mode documentation
refactor: simplify wake trigger registry
```

---

## 🚨 Common Pitfalls

1. **Don't duplicate services**
   - Check `Backend/services/` first (191 files!)
   - Many services already exist

2. **Safari automation requires sessions**
   - Use `safari_session_manager.py`
   - Don't create raw Safari instances

3. **Update Supabase RLS policies**
   - New tables need row-level security
   - Add migration files to `supabase/migrations/`

4. **All endpoints need contract tests**
   - Create test in `Backend/tests/contract/`
   - Verify request/response schemas

5. **Don't hardcode URLs or secrets**
   - Use environment variables
   - Load from `.env` via `os.getenv()`

---

## 🔗 Useful Commands Cheat Sheet

```bash
# Backend
cd Backend
source venv/bin/activate              # Activate virtualenv
pip install -r requirements.txt       # Install dependencies
uvicorn main:app --reload             # Start backend server
pytest tests/ -v                      # Run tests
pytest --cov=Backend --cov-report=html # Coverage report

# Frontend
cd dashboard
npm install                           # Install dependencies
npm run dev                           # Start dev server
npm run test                          # Run unit tests
npm run test:e2e                      # Run E2E tests

# Database
cd supabase
supabase start                        # Start local Supabase
supabase db push                      # Push migrations

# Git
git status                            # Check status
git add .                             # Stage all changes
git commit -m "feat: message"         # Commit with message
git push                              # Push to remote

# Redis
redis-server                          # Start Redis (separate terminal)
redis-cli ping                        # Test Redis connection

# Find things
find Backend -name "*.py" | grep keyword
grep -r "search_term" Backend/
ls -la Backend/services/ | grep keyword
```

---

## 📊 Progress Tracking

### Harness Files
- **`harness-status.json`**: Current session state, stats, PID
- **`harness-metrics.json`**: Performance metrics
- **`harness-output.log`**: Execution logs
- **`claude-progress.txt`**: Session notes (you update this)
- **`feature_list.json`**: Feature tracking (mark passes=true)

### After Each Feature
1. Run all related tests
2. Update `feature_list.json` (passes=true)
3. Add notes to `claude-progress.txt`
4. Commit with conventional commit message

---

## 🎯 Your Mission

**Goal**: Implement all 310 features across 10 phases.

**Current Status**: 0/310 complete (0.0%)

**Recommended Path**:
1. Start with **Phase 1** (Sleep/Wake Mode) - 20 features
2. Move to **Phase 2** (Content Ops Controller) - 40 features
3. Continue through phases sequentially
4. Prioritize P0 → P1 → P2 features

**Estimate**: ~500-600 hours total (310 features × ~2h avg)

---

## 📞 Help & Resources

### Documentation
- `README.md` - Project overview
- `INITIALIZATION_COMPLETE.md` - Detailed setup guide
- `ENVIRONMENT_VALIDATION.md` - Environment check results
- `COMPREHENSIVE_TEST_PLAN_2026.md` - Test specifications
- `docs/` - 123+ additional docs

### Architecture
- `ARCHITECTURE_PLAN.md` - System design
- `DEVELOPMENT_PHASES.md` - Phased rollout
- `docs/EVENT_DRIVEN_ARCHITECTURE_PRD.md` - Event system

### PRDs (Product Requirements)
- `docs/PRD_AUTOMATED_CONTENT_PIPELINE.md`
- `docs/PRD_SORA_VIDEO_ORCHESTRATOR.md`
- `docs/AI_NARRATIVE_SCHEDULING_PRD.md`
- `docs/AUTOMATION_CENTER_PRD.md`
- ...and many more in `docs/`

---

## ✅ Pre-Flight Checklist

Before starting your session:
- [ ] Read `INITIALIZATION_COMPLETE.md`
- [ ] Read `claude-progress.txt`
- [ ] Check `harness-status.json`
- [ ] Choose a feature from `feature_list.json`
- [ ] Review feature's `acceptance` criteria
- [ ] Check if feature's `files` exist
- [ ] Read related PRD if available
- [ ] Understand testing requirements

During implementation:
- [ ] Write clean, documented code
- [ ] Add comprehensive tests
- [ ] Run tests locally
- [ ] Verify acceptance criteria
- [ ] Update `feature_list.json`
- [ ] Update `claude-progress.txt`
- [ ] Commit with conventional commit

---

**Ready to code! Start with SLEEP-001 or pick any P0 feature from Phase 1.**

**Good luck! 🚀**
