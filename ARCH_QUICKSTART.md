# System Architecture - Quick Start Guide

**Date:** January 29, 2026
**Status:** ✅ All ARCH features complete and operational

---

## 🚀 Quick Start: Run Your First Pipeline

### 1. Start the Backend
```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload
```

### 2. Start a Pipeline via API
```bash
curl -X POST http://localhost:5555/api/orchestrator/pipeline/start \
  -H "Content-Type: application/json" \
  -d '{
    "theme": "AI tools that save 10 hours per week",
    "num_parts": 3,
    "character": "@isaiahdupree",
    "publish_platforms": ["tiktok", "instagram", "youtube"],
    "schedule_tweets": true,
    "tweets_per_day": 12,
    "offer_url": "https://blotato.com/ai-tools"
  }'
```

**Response:**
```json
{
  "success": true,
  "pipeline_id": "pipeline-abc123",
  "status": "initializing"
}
```

### 3. Check Pipeline Status
```bash
curl http://localhost:5555/api/orchestrator/pipeline/pipeline-abc123
```

### 4. View in Dashboard
```bash
# In separate terminal
cd /Users/isaiahdupree/Documents/Software/MediaPoster/dashboard
npm run dev

# Open: http://localhost:5557
# Navigate to Pipeline Dashboard widget
```

---

## 📊 What Happens in a Pipeline

1. **Generate 3 Sora Videos** (0-5 min)
2. **Stitch Videos Together** (5-15 min)
3. **AI Content Analysis** (15-16 min)
4. **Publish to Platforms** (16-20 min)
5. **Schedule Twitter Campaign** (20-21 min)
6. **Track Traffic & Conversions** (Ongoing)
7. **AI Analytics Feedback** (24h later)

---

## 🎯 Core Features (ARCH-001 to ARCH-008)

| Feature | What It Does | Status |
|---------|--------------|--------|
| **ARCH-001** | Master Orchestrator - coordinates everything | ✅ Complete |
| **ARCH-002** | 3-Part Sora Batch - generates & stitches videos | ✅ Complete |
| **ARCH-003** | Analyzer → Publisher - auto-fills titles/descriptions | ✅ Complete |
| **ARCH-004** | Tweet Scheduler - posts every 2 hours | ✅ Complete |
| **ARCH-005** | Traffic Tracker - monitors clicks & conversions | ✅ Complete |
| **ARCH-006** | Analytics Feedback - AI optimization suggestions | ✅ Complete |
| **ARCH-007** | Unified API - single endpoint for everything | ✅ Complete |
| **ARCH-008** | Dashboard Widget - real-time monitoring | ✅ Complete |

---

## 🔗 Key API Endpoints

```bash
# Start pipeline
POST /api/orchestrator/pipeline/start

# Get status
GET /api/orchestrator/pipeline/{id}

# List pipelines
GET /api/orchestrator/pipelines?status=completed&limit=10

# Get AI analytics
GET /api/orchestrator/pipeline/{id}/analytics

# Get traffic report
GET /api/orchestrator/pipeline/{id}/traffic

# Health check
GET /api/orchestrator/health
```

---

## 🧪 Testing

```bash
cd Backend
source venv/bin/activate

# Run orchestrator tests
pytest tests/test_orchestrator_integration.py -v

# Run all integration tests
pytest tests/integration/ -v
```

---

## 📚 Full Documentation

- **Comprehensive Guide:** `ARCH_COMPLETE_SESSION_2026_01_29.md`
- **Quick Reference:** This file
- **API Docs:** In endpoint docstrings
- **Tests:** `Backend/tests/test_orchestrator_integration.py`

---

**Status:** All ARCH features (001-008) complete and operational ✅
**Last Updated:** January 29, 2026
