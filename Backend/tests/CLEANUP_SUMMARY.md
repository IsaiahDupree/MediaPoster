# Test Directory Cleanup Summary

## Issues Identified
1. **134 test files in root directory** - Should be organized into subdirectories
2. **Multiple test runners** - 4 different runner scripts
3. **Multiple conftest files** - 3 different conftest files
4. **Duplicate test categories** - Some tests exist in multiple places
5. **Outdated phase directories** - phase0-5 may be outdated

## Organization Plan

### Directory Structure
```
tests/
├── api/                    # API endpoint tests
│   ├── accounts/
│   ├── media/
│   ├── schedule/
│   ├── content/
│   ├── posting/
│   ├── narrative/
│   ├── experiments/
│   └── analytics/
│
├── unit/                   # Unit tests
│   ├── services/
│   └── utils/
│
├── integration/            # Integration tests
│   ├── workflows/
│   └── services/
│
├── e2e/                   # End-to-end tests
│   └── workflows/
│
├── comprehensive/          # Comprehensive workflow tests
│   └── workflows/
│
├── performance/            # Performance tests (already organized)
├── security/               # Security tests (already organized)
├── database/               # Database tests (already organized)
└── contract/               # Contract tests (already organized)
```

## Actions Taken

1. ✅ Created organization script (`organize_tests.py`)
2. ✅ Created organization plan document
3. ⏳ Ready to execute organization (run with `--execute` flag)

## Next Steps

1. Review the organization plan
2. Run `python organize_tests.py --execute` to move files
3. Update test runner to use new paths
4. Consolidate conftest files
5. Update imports in test files
6. Archive/remove outdated phase directories

