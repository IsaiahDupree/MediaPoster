# MediaPoster Full System Quick Start

**Status:** ✅ 100% Complete - Ready to Run
**Last Updated:** February 2, 2026
**Duration to Full System Up:** ~10 minutes

---

## System Overview

MediaPoster is a complete autonomous content operations platform with:

- **Backend**: FastAPI REST API + Event Bus + Multi-service architecture
- **Frontend**: Next.js dashboard with 100+ pages and design system
- **Database**: PostgreSQL (Supabase) with 50+ tables
- **Queue**: Redis for task processing
- **Automation**: Safari automation for content creation
- **Integration**: 22+ social platforms (TikTok, Instagram, YouTube, Twitter, etc.)

---

## Prerequisites

```bash
# Python 3.11+
python3 --version

# Node.js 18+
node --version
npm --version

# PostgreSQL 14+
psql --version

# Redis 7+
redis-cli --version

# Docker (optional but recommended)
docker --version
```

---

## Step 1: Start Services

### Option A: Docker Compose (Recommended)

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster

# Start all services
docker-compose up -d

# Verify services
docker-compose ps
```

**Services Started:**
- PostgreSQL: localhost:5432
- Redis: localhost:6379
- Supabase Studio: localhost:54323

### Option B: Manual Start

#### Start PostgreSQL

```bash
# If installed via Homebrew
brew services start postgresql

# Verify
psql -U postgres -c "SELECT 1;"
```

#### Start Redis

```bash
# If installed via Homebrew
brew services start redis

# Verify
redis-cli ping  # Should return PONG
```

---

## Step 2: Configure Backend

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python scripts/db_migrate.py

# Verify database
psql -U postgres -d mediaposter -c "SELECT * FROM pg_tables LIMIT 5;"
```

---

## Step 3: Start Backend API

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend

# Activate virtual environment
source venv/bin/activate

# Start FastAPI server
uvicorn main:app --host 0.0.0.0 --port 5555 --reload

# In another terminal, verify API
curl http://localhost:5555/api/health
# Expected response: {"status": "healthy"}
```

**Backend Running At:**
- API: `http://localhost:5555`
- Docs: `http://localhost:5555/docs` (Swagger UI)
- ReDoc: `http://localhost:5555/redoc`

---

## Step 4: Configure Frontend

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/dashboard

# Install dependencies
npm install

# Create environment file
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_URL=http://localhost:5555
NEXT_PUBLIC_APP_NAME=MediaPoster
NEXT_PUBLIC_APP_VERSION=5.0
EOF
```

---

## Step 5: Start Frontend

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/dashboard

# Start development server
npm run dev

# Expected output:
# ▲ Next.js 16.x.x
# - Local:        http://localhost:3000
# - Environments: .env.local
```

**Frontend Running At:**
- Dashboard: `http://localhost:3000`

---

## Step 6: Verify Full Stack

### Check Backend Health

```bash
curl -s http://localhost:5555/api/health | jq .
# {
#   "status": "healthy",
#   "timestamp": "2026-02-02T...",
#   "version": "5.0"
# }
```

### Check EventBus Status

```bash
curl -s http://localhost:5555/api/orchestrator/health | jq .
# Returns EventBus and service status
```

### Access Frontend Dashboard

```bash
open http://localhost:3000
# Or: firefox http://localhost:3000
# Or: chrome http://localhost:3000
```

### Test API Endpoint

```bash
# Create a new orchestrator pipeline
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "AI automation",
    "num_parts": 1,
    "character": "@creator",
    "publish_platforms": ["tiktok"],
    "schedule_tweets": true,
    "tweets_per_day": 12
  }' | jq .
```

---

## System Architecture at a Glance

```
┌─────────────────────────────────────────────────────────┐
│                  Frontend Dashboard                     │
│         http://localhost:3000                           │
│                  (Next.js + React)                      │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ HTTP/REST
                       │
┌──────────────────────▼──────────────────────────────────┐
│                    Backend API                          │
│         http://localhost:5555                           │
│               (FastAPI + Services)                      │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
    ┌────────┐    ┌────────┐    ┌─────────┐
    │EventBus│    │Services│    │Database │
    │(Pub/Sub)   │(Logic) │    │(Postgres)
    └────────┘    └────────┘    └─────────┘
        │              │              │
        └──────────────┼──────────────┘
                       │
                    ┌──┴──┐
                    │Redis│
                    │Queue│
                    └─────┘
```

---

## Key Endpoints

### Health & Status

- `GET /api/health` - Application health
- `GET /api/orchestrator/health` - System health
- `GET /api/metrics` - Metrics dashboard

### Orchestrator

- `POST /api/orchestrator/pipeline/start` - Start pipeline
- `GET /api/orchestrator/pipeline/:id` - Get pipeline status
- `GET /api/orchestrator/pipelines` - List pipelines
- `DELETE /api/orchestrator/pipeline/:id` - Cancel pipeline

### Content

- `GET /api/content` - Get content
- `POST /api/content/create` - Create content
- `POST /api/content/analyze` - Analyze content

### Publishing

- `POST /api/publish` - Publish to platforms
- `GET /api/publish/status/:id` - Check publish status

### Analytics

- `GET /api/analytics/metrics` - Get metrics
- `GET /api/analytics/engagement` - Get engagement data

---

## Example Workflows

### Workflow 1: Create and Publish Content

```bash
# 1. Start orchestrator pipeline
PIPELINE_ID=$(curl -s -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "AI trends",
    "num_parts": 3,
    "character": "@isaiahdupree",
    "publish_platforms": ["tiktok", "instagram"],
    "schedule_tweets": true
  }' | jq -r '.pipeline_id')

echo "Pipeline ID: $PIPELINE_ID"

# 2. Monitor pipeline progress
watch -n 2 "curl -s http://localhost:5555/api/orchestrator/pipeline/$PIPELINE_ID | jq '.status'"

# 3. Check published content
curl -s http://localhost:5555/api/orchestrator/pipeline/$PIPELINE_ID | jq '.published_count'
```

### Workflow 2: Schedule Content

```bash
# 1. Create scheduled post
curl -X POST http://localhost:5555/api/content/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "content_id": "content-123",
    "platforms": ["tiktok", "instagram"],
    "scheduled_time": "2026-02-03T14:00:00Z"
  }' | jq .

# 2. View scheduled posts
curl http://localhost:5555/api/schedule/upcoming | jq .
```

### Workflow 3: Track Analytics

```bash
# Get engagement metrics
curl http://localhost:5555/api/analytics/metrics \
  -H "Authorization: Bearer YOUR_TOKEN" | jq .

# Get performance by platform
curl http://localhost:5555/api/analytics/by-platform | jq .

# Get trending content
curl http://localhost:5555/api/analytics/trending | jq .
```

---

## Testing the System

### Run Backend Tests

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend

source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/integration/test_arch_complete_integration.py -v

# Run with coverage
pytest tests/ --cov=services --cov-report=html
```

### Run Frontend Tests

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/dashboard

# Run unit tests
npm test

# Run E2E tests
npm run e2e

# Run with coverage
npm test -- --coverage
```

### Integration Testing

```bash
# Test full orchestrator flow
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "Test workflow",
    "num_parts": 1,
    "character": "@test",
    "publish_platforms": ["tiktok"],
    "schedule_tweets": false
  }'

# Then monitor progress in dashboard: http://localhost:3000/orchestrator
```

---

## Monitoring & Debugging

### View Logs

```bash
# Backend logs
tail -f /Users/isaiahdupree/Documents/Software/MediaPoster/Backend/logs/app.log

# Frontend logs (in browser console)
# Press F12 → Console tab

# PostgreSQL logs
tail -f /usr/local/var/log/postgres.log

# Redis logs
redis-cli MONITOR
```

### Check Service Health

```bash
# Check all services
curl http://localhost:5555/api/health && \
curl http://localhost:3000/api/health && \
psql -c "SELECT 1;" && \
redis-cli ping

# Check database connections
psql -d mediaposter -c "SELECT count(*) FROM pg_stat_activity;"

# Check Redis usage
redis-cli INFO memory

# Check event bus status
curl http://localhost:5555/api/orchestrator/health | jq '.event_bus'
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Restart backend
cd Backend && source venv/bin/activate && uvicorn main:app --reload

# Enable verbose API responses
curl -s -H "X-Debug: true" http://localhost:5555/api/health | jq .
```

---

## Troubleshooting

### Backend won't start

```bash
# Check if port 5555 is in use
lsof -i :5555

# Kill process if needed
kill -9 <PID>

# Verify database is running
psql -c "SELECT 1;"

# Verify Redis is running
redis-cli ping
```

### Frontend won't connect to backend

```bash
# Check backend is running
curl http://localhost:5555/api/health

# Check environment variable
grep NEXT_PUBLIC_API_URL dashboard/.env.local

# Restart frontend
cd dashboard && npm run dev
```

### Database errors

```bash
# Reset database (caution: deletes data)
cd Backend && python scripts/db_reset.py

# Or restore from backup
psql -U postgres -d mediaposter < backup.sql

# Check database status
psql -d mediaposter -c "\dt"
```

### Event bus not working

```bash
# Check event bus health
curl http://localhost:5555/api/orchestrator/health | jq '.event_bus'

# Restart backend service
kill <PID> && uvicorn main:app --reload

# Check for errors in logs
tail -f logs/app.log | grep -i event
```

---

## Performance Tuning

### Database

```bash
# Enable query logging
psql -d mediaposter -c "SET log_statement = 'all';"

# Analyze table
psql -d mediaposter -c "ANALYZE orchestrator_pipelines;"

# Check index usage
psql -d mediaposter -c "SELECT * FROM pg_stat_user_indexes;"
```

### Redis

```bash
# Clear cache
redis-cli FLUSHDB

# Monitor operations
redis-cli MONITOR | head -20

# Check memory usage
redis-cli INFO memory
```

### Backend

```bash
# Monitor metrics
curl http://localhost:5555/api/metrics | jq .

# Check event bus load
curl http://localhost:5555/api/orchestrator/health | jq '.event_bus.queued_events'
```

---

## Useful Commands

```bash
# Start everything
docker-compose up -d
cd Backend && source venv/bin/activate && uvicorn main:app --reload &
cd ../dashboard && npm run dev &

# Stop everything
docker-compose down
pkill -f uvicorn
pkill -f "next"

# View database
psql -d mediaposter -c "SELECT * FROM orchestrator_pipelines;"

# Test API
curl http://localhost:5555/api/health

# Monitor all services
watch -n 1 "curl -s http://localhost:5555/api/health && echo 'Frontend:' && curl -s http://localhost:3000/api/health"
```

---

## Next Steps

1. ✅ **System is running** - All services active
2. 📊 **Access Dashboard** - http://localhost:3000
3. 🧪 **Try a Pipeline** - Create test content via API
4. 📈 **Monitor Metrics** - Watch dashboard during operations
5. 🚀 **Deploy to Production** - See PRODUCTION_READINESS_CHECKLIST.md

---

## Support & Resources

### Key Files

- API Docs: http://localhost:5555/docs
- Backend Code: `Backend/services/`
- Frontend Code: `dashboard/app/`
- Tests: `Backend/tests/` and `dashboard/__tests__/`

### Documentation

- Architecture: `MASTER_ARCHITECTURE.md`
- Design System: `dashboard/components/ui/`
- PRDs: `Backend/docs/PRD_*.md`
- API Reference: `Backend/api/endpoints/`

### Quick References

- System Architecture: `SESSION_STATUS_2026_02_02.md`
- Feature List: `feature_list.json`
- Deployment Guide: `PRODUCTION_READINESS_CHECKLIST.md`

---

**Status:** ✅ READY TO RUN
**Setup Time:** ~10 minutes
**Uptime Target:** 99.9%

**Generated:** February 2, 2026
**MediaPoster v5.0** - 100% Complete
