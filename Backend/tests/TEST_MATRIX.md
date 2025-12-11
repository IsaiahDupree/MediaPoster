# MediaPoster Test Matrix

Mapping of test types to project tests for AI Analysis & Scheduling.

## Test Coverage Summary

| Test Type | File | Tests | Status |
|-----------|------|-------|--------|
| **Unit** | `test_ai_analysis_scheduling.py` | 22 | ✅ |
| **Integration** | `test_ai_analysis_scheduling.py` | 8 | ✅ |
| **Functional** | `test_ai_analysis_scheduling.py` | 9 | ✅ |
| **API** | `test_ai_analysis_scheduling.py` | 3 | ✅ |
| **Database** | `test_ai_analysis_scheduling.py` | 4 | ✅ |
| **Regression** | `test_ai_analysis_scheduling.py` | 3 | ✅ |
| **Performance** | `test_ai_analysis_scheduling.py` | 2 | ✅ |
| **Smoke** | `test_ai_analysis_scheduling.py` | 3 | ✅ |
| **PRD Requirements** | `test_prd_requirements.py` | 154 | ✅ |
| **PRD Integration** | `test_prd_integration.py` | 51 | ✅ |
| **TikTok API** | `test_tiktok_features.py` | 6 | ✅ |

---

## By Test Level

### Unit Tests ✅
Individual functions/classes in isolation.

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestAIAnalysisUnit` | 12 | Pre-social score, frames, transcript |
| `TestSchedulingUnit` | 9 | Gap constraints, edge cases |

```bash
pytest tests/test_ai_analysis_scheduling.py::TestAIAnalysisUnit -v
pytest tests/test_ai_analysis_scheduling.py::TestSchedulingUnit -v
```

### Integration Tests ✅
How components work together.

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestAnalysisPipelineIntegration` | 5 | Ingest → Analyze → Schedule |
| `TestSchedulingPipelineIntegration` | 3 | Schedule conflicts, platforms |

```bash
pytest tests/test_ai_analysis_scheduling.py::TestAnalysisPipelineIntegration -v
pytest tests/test_ai_analysis_scheduling.py::TestSchedulingPipelineIntegration -v
```

### System/E2E Tests ✅
Full application flows.

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestE2EIngestToPost` | 7 | Full pipeline flow |
| `TestE2EMetricsCollection` | 8 | Checkpoint collection |
| `TestE2ECoachInsights` | 4 | AI Coach flow |

```bash
pytest tests/test_prd_integration.py::TestE2EIngestToPost -v
```

---

## By Purpose

### Functional Tests ✅

| Test Class | Tests | Purpose |
|------------|-------|---------|
| `TestPRDRequirementsFunctional` | 9 | PRD spec compliance |
| `TestMediaAnalysisTable` | 6 | Schema requirements |
| `TestSchedulingAlgorithm` | 14 | Algorithm correctness |

### API Tests ✅

| Test Class | Tests | Endpoints |
|------------|-------|-----------|
| `TestAPIEndpoints` | 3 | /analysis, /schedule, /coach-summary |
| `TestAPIIntegration` | 6 | All PRD endpoints |

### Smoke Tests ✅

| Test Class | Tests | Purpose |
|------------|-------|---------|
| `TestSmoke` | 3 | Quick "does it run?" checks |

### Regression Tests ✅

| Test Class | Tests | Purpose |
|------------|-------|---------|
| `TestRegression` | 3 | Prevent breaking changes |

### Database Tests ✅

| Test Class | Tests | Coverage |
|------------|-------|----------|
| `TestDatabaseOperations` | 4 | FK, JSONB, timestamps |
| `TestDatabaseIntegration` | 9 | Constraints, indexes |

### Performance Tests ✅

| Test Class | Tests | Benchmarks |
|------------|-------|------------|
| `TestPerformance` | 2 | <100ms schedule, <1s score calc |

---

## By Approach

### Black-box Testing ✅
Test inputs/outputs without knowing internals.

- `TestPRDRequirementsFunctional`
- `TestAPIEndpoints`
- `TestSmoke`

### White-box Testing ✅
Test with knowledge of internal code.

- `TestAIAnalysisUnit`
- `TestSchedulingUnit`
- `TestRegression`

---

## Run Commands

```bash
# All AI Analysis & Scheduling Tests
pytest tests/test_ai_analysis_scheduling.py -v

# Specific test types
pytest tests/test_ai_analysis_scheduling.py::TestAIAnalysisUnit -v      # Unit
pytest tests/test_ai_analysis_scheduling.py::TestSchedulingUnit -v      # Unit
pytest tests/test_ai_analysis_scheduling.py::TestAnalysisPipelineIntegration -v  # Integration
pytest tests/test_ai_analysis_scheduling.py::TestAPIEndpoints -v        # API
pytest tests/test_ai_analysis_scheduling.py::TestDatabaseOperations -v  # Database
pytest tests/test_ai_analysis_scheduling.py::TestRegression -v          # Regression
pytest tests/test_ai_analysis_scheduling.py::TestPerformance -v         # Performance
pytest tests/test_ai_analysis_scheduling.py::TestSmoke -v               # Smoke

# All Non-Browser Tests
pytest tests/test_ai_analysis_scheduling.py \
       tests/test_prd_requirements.py \
       tests/test_prd_integration.py \
       automation/tests/test_tiktok_features.py -v
```

---

## Test Types NOT YET IMPLEMENTED

| Type | Priority | Notes |
|------|----------|-------|
| Load Testing | Medium | Need locust/k6 setup |
| Security Testing | High | SAST/DAST tools |
| Chaos Testing | Low | Production-like env needed |
| Visual Regression | Low | Frontend screenshots |
| A/B Testing | Low | Feature flags needed |
| Accessibility | Medium | Frontend focus |

---

## Minimum Sensible Test Stack for MediaPoster

### Must Have ✅
1. **Unit Tests** - Core algorithm validation
2. **Integration Tests** - Pipeline flows
3. **API Tests** - Endpoint contracts
4. **Regression Tests** - Change safety
5. **Smoke Tests** - Quick validation

### Should Have ⚠️
1. **Performance Tests** - Baseline benchmarks
2. **Database Tests** - Data integrity
3. **Security Tests** - Vulnerability scans

### Nice to Have 📋
1. **Load Tests** - Scale validation
2. **E2E Browser Tests** - Full user flows
3. **Visual Regression** - UI changes
