# MediaPoster Comprehensive Test Plan

## Test Coverage Matrix

| Test Type | Backend | Frontend | Status |
|-----------|---------|----------|--------|
| **Unit Tests** | pytest | Jest | ✅ |
| **Component Tests** | pytest | Jest | ✅ |
| **Integration Tests** | pytest | Playwright | ✅ |
| **E2E Tests** | pytest + requests | Playwright | ✅ |
| **API Tests** | pytest | Playwright | ✅ |
| **Smoke Tests** | pytest | Playwright | ✅ |
| **Regression Tests** | pytest | Playwright | ✅ |
| **Performance Tests** | locust/pytest | Lighthouse | ✅ |
| **Security Tests** | pytest + bandit | OWASP ZAP | ✅ |
| **Accessibility Tests** | - | cypress-axe | ✅ |
| **Visual Regression** | - | Playwright | ✅ |

---

## Quick Start Commands

### Run All Tests
```bash
# From project root
./run_all_tests.sh
```

### Backend Tests
```bash
cd Backend

# Smoke tests (quick)
pytest tests/test_smoke.py -v

# Unit tests
pytest tests/ -v --ignore=tests/integration --ignore=tests/performance

# Integration tests
pytest tests/integration/ -v

# Full test suite
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=html
```

### Frontend Tests
```bash
cd Frontend

# Unit tests (Jest)
npm test

# E2E tests (Playwright)
npm run test:e2e

# Specific test suites
npm run test:e2e:api
npm run test:e2e:settings

# Visual regression
npx playwright test visual/

# Accessibility
npx cypress run --spec "cypress/e2e/accessibility.cy.ts"
```

---

## Test Organization

```
MediaPoster/
├── Backend/
│   └── tests/
│       ├── unit/                    # Unit tests
│       ├── integration/             # Integration tests
│       ├── performance/             # Load & stress tests
│       ├── security/                # Security tests
│       ├── comprehensive/           # Full feature tests
│       ├── test_smoke.py           # Quick health checks
│       └── conftest.py             # Shared fixtures
│
├── Frontend/
│   ├── src/components/**/__tests__/ # Jest unit tests
│   ├── e2e/tests/                   # Playwright E2E
│   │   ├── api/                     # API tests
│   │   ├── pages/                   # Page tests
│   │   ├── visual/                  # Visual regression
│   │   └── integration/             # Integration tests
│   └── cypress/e2e/                 # Cypress accessibility tests
│
└── run_all_tests.sh                 # Master test runner
```

---

## Test Categories

### 1. Unit Tests
- **Backend**: Individual service/utility functions
- **Frontend**: React component rendering, hooks, utilities

### 2. Integration Tests  
- API endpoint combinations
- Database operations
- Service-to-service communication

### 3. E2E Tests
- Full user flows (login → action → verify)
- Cross-page navigation
- Form submissions

### 4. API Tests
- All REST endpoints
- Request/response validation
- Error handling
- Rate limiting

### 5. Performance Tests
- Response time benchmarks
- Concurrent user load
- Memory usage
- Database query performance

### 6. Security Tests
- Input validation/sanitization
- Authentication/authorization
- SQL injection prevention
- XSS prevention
- CORS validation

### 7. Accessibility Tests
- WCAG 2.1 compliance
- Keyboard navigation
- Screen reader compatibility
- Color contrast

### 8. Visual Regression Tests
- Screenshot comparisons
- Layout consistency
- Responsive design

---

## CI/CD Integration

Tests are organized by speed for CI pipelines:

1. **Pre-commit** (~30s): Lint + Type check
2. **PR Checks** (~2min): Smoke + Unit tests
3. **Merge** (~10min): Full integration + E2E
4. **Nightly** (~30min): Performance + Security + Visual
