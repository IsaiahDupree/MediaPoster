# MediaPoster Documentation

Welcome to the MediaPoster documentation. This folder contains comprehensive guides for development, testing, and deployment.

## Documentation Index

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](./QUICKSTART.md) | Get up and running in 5 minutes |
| [API_REFERENCE.md](./API_REFERENCE.md) | Complete API endpoint documentation |
| [TESTING_AND_INFRASTRUCTURE.md](./TESTING_AND_INFRASTRUCTURE.md) | Testing strategy and troubleshooting |
| [CHANGELOG.md](./CHANGELOG.md) | Version history and recent changes |

## Quick Links

### Getting Started
- [Quick Start Guide](./QUICKSTART.md) - Start here!
- [API Documentation](http://localhost:5555/docs) - Interactive Swagger docs (requires running server)

### Development
- [Testing Guide](./TESTING_AND_INFRASTRUCTURE.md#running-tests)
- [Troubleshooting](./TESTING_AND_INFRASTRUCTURE.md#troubleshooting)
- [Database Setup](./TESTING_AND_INFRASTRUCTURE.md#database-setup)

### Reference
- [API Reference](./API_REFERENCE.md)
- [Test Plan](../COMPREHENSIVE_TEST_PLAN.md)

## Project Structure

```
MediaPoster/
├── docs/                    # 📚 Documentation (you are here)
├── Backend/                 # 🐍 FastAPI backend
│   ├── api/endpoints/       # API route handlers
│   ├── database/            # Models & connection
│   ├── services/            # Business logic
│   └── tests/               # Test suites
├── Frontend/                # ⚛️  Next.js frontend
│   ├── src/app/             # App router pages
│   ├── src/components/      # React components
│   └── e2e/                 # Playwright tests
├── supabase/                # 🗄️  Database
│   └── migrations/          # SQL migrations
└── scripts/                 # 🔧 Utility scripts
```

## Essential Commands

```bash
# Start everything
supabase start
cd Backend && uvicorn main:app --port 5555 --reload
cd Frontend && npm run dev

# Run tests
./run_all_tests.sh --smoke

# Health check
./scripts/health_check.sh

# Diagnostics
python3 scripts/diagnose_tests.py
```

## Need Help?

1. Check [Troubleshooting](./TESTING_AND_INFRASTRUCTURE.md#troubleshooting)
2. Run diagnostics: `python3 scripts/diagnose_tests.py`
3. Review logs: `tail -f Backend/logs/app.log`
