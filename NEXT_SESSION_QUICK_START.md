# MediaPoster - Next Session Quick Start Guide

**Current Status:** 295/495 features (59.6%) ✅ ARCH Features Complete
**Last Updated:** January 30, 2026
**Recommended Duration:** 4-6 hours per feature group

---

## 🎯 Three Priority Paths (Pick One)

### Path A: Design System Components (IMMEDIATE - Unblocks Frontend)
**Duration:** 4-6 hours
**Impact:** Enables 30+ dashboard and UI features
**Components to Build:**
- Button (DS-001) - 2h
- Card (DS-002) - 2h
- StatusBadge (DS-003) - 1h
- LoadingState (DS-004) - 2h
- EmptyState (DS-005) - 1h
- ErrorState (DS-006) - 1h

**Start File:** `dashboard/app/components/ui/`
**Tech Stack:** React + Tailwind + TypeScript
**Reference:** Phase 20 in feature_list.json

---

### Path B: Daily Sora Automation (AUTONOMOUS OPERATION)
**Duration:** 6-8 hours (can split across 2 sessions)
**Impact:** Fully autonomous 30+ video generation per day
**Features to Build:**
- Daily Sora Usage Optimization (SORA-AUTO-001)
- Watermark Removal Automation (SORA-AUTO-002)
- Trend-Based Story Generation (SORA-AUTO-003)
- Character Stories Pipeline (SORA-AUTO-004)
- YouTube Daily Publishing (SORA-AUTO-005)
- Pub/Sub Integration (SORA-AUTO-006)

**Start File:** `Backend/services/sora_daily/daily_scheduler.py` (partially exists)
**Core Logic:** Cron jobs → Event triggering → MasterOrchestrator coordination
**Reference:** SORA-AUTO category in feature_list.json

---

### Path C: Growth Data Plane (ANALYTICS FOUNDATION)
**Duration:** 5-7 hours
**Impact:** Enables all tracking, analytics, and optimization
**Database Tables to Create:**
- `people` - User/person identity registry
- `engagement_metrics` - Per-post analytics (views, likes, shares, follows)
- `conversion_funnels` - E-commerce tracking (clicks, conversions, revenue)
- `ab_tests` - A/B test results and comparison
- `platform_interactions` - Cross-platform engagement data

**Files to Modify:**
- `Backend/database/models.py` - Add SQLAlchemy models
- `Backend/api/endpoints/analytics.py` - Analytics endpoints (partially exists)
- Supabase migrations in `Backend/migrations/`

**Tech Stack:** SQLAlchemy + PostgreSQL + Supabase
**Reference:** GDP category in feature_list.json

---

## 📋 Step-by-Step for Path A (Design System)

### 1. Create Component Scaffold (15 min)
```bash
mkdir -p dashboard/app/components/ui/{Button,Card,Badge,States}
touch dashboard/app/components/ui/Button.tsx
touch dashboard/app/components/ui/Card.tsx
# ... etc
```

### 2. Build Button Component (30 min)
**File:** `dashboard/app/components/ui/Button.tsx`
**Features:**
- Variants: primary, secondary, danger, ghost
- Sizes: sm, md, lg
- Loading state
- Disabled state
- Icon support

**Template:**
```typescript
import React from 'react'
import { cn } from '@/lib/utils'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', isLoading, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          'inline-flex items-center justify-center font-medium transition-colors',
          // variant styles...
          // size styles...
        )}
        disabled={isLoading || props.disabled}
        {...props}
      >
        {isLoading && <Spinner className="mr-2" />}
        {props.children}
      </button>
    )
  }
)

Button.displayName = 'Button'
```

### 3. Build Card Component (30 min)
**File:** `dashboard/app/components/ui/Card.tsx`
**Features:**
- Header, body, footer sections
- Hover effects
- Loading skeleton variant

### 4. Build Status/State Components (2 hours)
- StatusBadge (success, error, warning, info)
- LoadingState (spinner + skeleton)
- EmptyState (icon + message)
- ErrorState (icon + message + retry button)

### 5. Export from Index (15 min)
**File:** `dashboard/app/components/ui/index.ts`
```typescript
export { Button } from './Button'
export { Card } from './Card'
export { StatusBadge } from './StatusBadge'
// ... etc
```

### 6. Add to feature_list.json
Mark each as `"passes": true` when tests pass:
```json
{ "id": "DS-001", "passes": true, "completed": "2026-01-30" }
```

**Testing:** `npm run test` in dashboard directory

---

## 📋 Step-by-Step for Path B (Daily Sora Automation)

### 1. Create Daily Scheduler Service (1.5 hours)
**File:** `Backend/services/sora_daily/daily_scheduler.py`
**Key Classes:**
```python
class DailySoraScheduler:
    async def schedule_daily_generations(self) -> None:
        """Run every 6 hours to queue 5 videos per run (30/day)"""

    async def _get_daily_trend(self) -> str:
        """Fetch trending topic from trend_intelligence service"""

    async def _generate_video(self, theme: str) -> str:
        """Trigger MasterOrchestrator.start_pipeline()"""
```

### 2. Add to EventBus Topic System
**File:** `Backend/services/event_bus/topics.py`
```python
SORA_DAILY_REQUESTED = "sora.daily.requested"
SORA_DAILY_COMPLETED = "sora.daily.completed"
```

### 3. Wire to MasterOrchestrator
**File:** `Backend/services/master_orchestrator.py`
```python
def __init__(self, ...):
    # Subscribe to daily scheduler events
    self.event_bus.subscribe(
        Topics.SORA_DAILY_REQUESTED,
        self._handle_sora_daily_requested
    )
```

### 4. Add to Automation Registry
**File:** `Backend/services/automation_registry.py`
```python
self.register_automation('daily_sora', DailySoraScheduler(), interval_hours=6)
```

### 5. Create Tests
**File:** `Backend/tests/test_daily_sora_scheduler.py`
- Test scheduling runs every 6 hours
- Test 5 videos generated per run
- Test theme selection from trends
- Test event emission

---

## 📋 Step-by-Step for Path C (Growth Data Plane)

### 1. Create Database Models (2 hours)
**File:** `Backend/database/models.py` (add to existing)
```python
class Person(Base):
    __tablename__ = "people"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True)
    twitter_handle = Column(String, unique=True)
    instagram_handle = Column(String)
    # ... platform handles
    created_at = Column(DateTime, default=datetime.utcnow)

class EngagementMetric(Base):
    __tablename__ = "engagement_metrics"
    id = Column(String, primary_key=True)
    post_id = Column(String, ForeignKey("posts.id"))
    platform = Column(String)  # twitter, instagram, tiktok, youtube
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    follows = Column(Integer, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow)

class ConversionFunnel(Base):
    __tablename__ = "conversion_funnels"
    id = Column(String, primary_key=True)
    post_id = Column(String, ForeignKey("posts.id"))
    link_clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    revenue = Column(Float, default=0.0)
    conversion_rate = Column(Float, default=0.0)
    aov = Column(Float, default=0.0)  # Average Order Value
    timestamp = Column(DateTime, default=datetime.utcnow)

class ABTest(Base):
    __tablename__ = "ab_tests"
    id = Column(String, primary_key=True)
    name = Column(String)
    control_post_id = Column(String, ForeignKey("posts.id"))
    variant_post_id = Column(String, ForeignKey("posts.id"))
    status = Column(String)  # running, paused, completed
    winner = Column(String)  # control, variant, tie, inconclusive
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
```

### 2. Create API Endpoints (1.5 hours)
**File:** `Backend/api/endpoints/analytics.py` (expand existing)
```python
@router.get("/people/{person_id}")
async def get_person(person_id: str):
    """Get person profile"""

@router.post("/engagement/record")
async def record_engagement(event: EngagementEvent):
    """Record engagement metric"""

@router.get("/posts/{post_id}/metrics")
async def get_post_metrics(post_id: str):
    """Get aggregated metrics for a post"""

@router.post("/ab-tests/create")
async def create_ab_test(config: ABTestConfig):
    """Create new A/B test"""
```

### 3. Create Supabase Migrations
**File:** `Backend/migrations/002_growth_data_plane.sql`
```sql
-- People table
CREATE TABLE IF NOT EXISTS people (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR UNIQUE,
    twitter_handle VARCHAR UNIQUE,
    instagram_handle VARCHAR,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Engagement metrics table
CREATE TABLE IF NOT EXISTS engagement_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id UUID REFERENCES posts(id),
    platform VARCHAR NOT NULL,
    views INTEGER DEFAULT 0,
    likes INTEGER DEFAULT 0,
    shares INTEGER DEFAULT 0,
    comments INTEGER DEFAULT 0,
    follows INTEGER DEFAULT 0,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- ... etc for other tables
```

### 4. Create Tests
**File:** `Backend/tests/test_growth_data_plane.py`
- Test person creation
- Test engagement metric recording
- Test funnel tracking
- Test A/B test creation and winner determination

### 5. Update feature_list.json
Mark as complete when schema is created and tests pass:
```json
{ "id": "GDP-001", "passes": true, "completed": "2026-01-30" }
```

---

## 🚀 How to Get Started

### Quick Start (Next 15 minutes)
1. Read this file completely ✓
2. Choose a Path (A, B, or C based on your expertise)
3. Read the step-by-step for your path
4. Run the first step commands
5. Use `npm run test` or `pytest` to verify

### For Path A (Design System):
```bash
cd dashboard
npm install  # If needed
npm run dev  # Start dev server
# Create components as shown above
npm run test  # Verify
```

### For Path B (Daily Sora):
```bash
cd Backend
source venv/bin/activate
python -m pytest tests/test_daily_sora_scheduler.py -v
# Implement as shown above
```

### For Path C (Growth Data Plane):
```bash
cd Backend
source venv/bin/activate
# Run migrations
alembic upgrade head
# Create models and endpoints
pytest tests/test_growth_data_plane.py -v
```

---

## 📊 Success Criteria

### Path A Complete When:
- [ ] All 6 UI components created
- [ ] Components exported from index file
- [ ] Visual tests pass (storybook or manual)
- [ ] DS-001 to DS-006 marked as `passes: true`
- [ ] PR ready for review

### Path B Complete When:
- [ ] Daily scheduler created and wired to EventBus
- [ ] MasterOrchestrator subscribes to daily events
- [ ] Automation registry includes DailySoraScheduler
- [ ] All 6 SORA-AUTO features marked as `passes: true`
- [ ] Tests verify 5 videos queued per run
- [ ] PR ready for review

### Path C Complete When:
- [ ] All 5 database models created in SQLAlchemy
- [ ] Supabase migrations run successfully
- [ ] API endpoints functional with sample data
- [ ] All 5 GDP features marked as `passes: true`
- [ ] Tests verify data persistence
- [ ] PR ready for review

---

## 🔗 Key Files Reference

### Design System (Path A)
- `dashboard/app/components/ui/` - Component folder
- `dashboard/app/styles/tailwind.config.js` - Tailwind config
- `dashboard/app/lib/utils.ts` - Utility functions (cn classifier)

### Daily Sora (Path B)
- `Backend/services/sora_daily/` - Main implementation folder
- `Backend/services/master_orchestrator.py` - Orchestrator to wire to
- `Backend/services/event_bus/topics.py` - Topic definitions
- `Backend/tests/test_daily_sora_scheduler.py` - Test file

### Growth Data Plane (Path C)
- `Backend/database/models.py` - SQLAlchemy models
- `Backend/api/endpoints/analytics.py` - API endpoints
- `Backend/migrations/` - Database migration scripts
- `Backend/tests/test_growth_data_plane.py` - Test file

---

## ✅ Checklist Before Starting

- [ ] Read PROJECT_STATUS_2026_01_30.md
- [ ] Read this file completely
- [ ] Choose your Path (A, B, or C)
- [ ] Verify you have environment set up:
  - For A: Node 18+, npm, Next.js 16
  - For B: Python 3.11+, venv activated, pytest
  - For C: Python 3.11+, venv, psql CLI
- [ ] Latest code pulled from main branch
- [ ] All tests currently passing (`npm run test` or `pytest`)

---

**Created:** January 30, 2026
**Current Feature Status:** 295/495 (59.6%)
**Target for Session:** +8 features (+1.6% → 61.2%)
