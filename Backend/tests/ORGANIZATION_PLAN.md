# Test Directory Organization Plan

## Current Issues
- 134 test files in root directory
- Multiple test runner scripts (4 different runners)
- Multiple conftest files
- Duplicate test categories
- Unclear organization

## Proposed Structure

```
tests/
├── __init__.py
├── conftest.py                    # Main pytest configuration
├── README.md                      # Updated documentation
├── run_all_tests.py              # Single unified test runner
│
├── unit/                         # Unit tests (isolated components)
│   ├── services/
│   ├── models/
│   └── utils/
│
├── api/                          # API endpoint tests
│   ├── accounts/
│   ├── media/
│   ├── schedule/
│   ├── narrative/
│   ├── experiments/
│   └── blotato/
│
├── integration/                  # Integration tests
│   ├── workflows/
│   └── services/
│
├── e2e/                          # End-to-end tests
│   └── workflows/
│
├── performance/                  # Performance tests
│   ├── latency/
│   ├── load/
│   └── database/
│
├── security/                     # Security tests
│   ├── authentication/
│   ├── input_validation/
│   └── data_protection/
│
├── database/                     # Database tests
│   ├── constraints/
│   ├── performance/
│   └── migrations/
│
├── contract/                     # API contract tests
│
└── comprehensive/                # Comprehensive workflow tests
    ├── narrative_builder/
    ├── experiments/
    └── scheduling/
```

## Migration Steps
1. Consolidate test runners into single `run_all_tests.py`
2. Move API tests to `api/` subdirectories
3. Move unit tests to `unit/` subdirectories
4. Consolidate conftest files
5. Archive/remove outdated phase directories
6. Update all imports and references

