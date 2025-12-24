# ⚡ Quick Reference Card

**Essential commands and URLs for daily development**

---

## 🚀 Start Services

```bash
# Terminal 1: Database
cd supabase && supabase start

# Terminal 2: Backend
cd Backend && source venv/bin/activate && uvicorn main:app --port 5555 --reload

# Terminal 3: Frontend
cd dashboard && npm run dev
```

---

## 🔗 URLs

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:5557 |
| API Docs | http://localhost:5555/docs |
| API Health | http://localhost:5555/api/health |
| Database UI | http://localhost:54323 |
| Media Provider | http://localhost:5555/api/media-provider/health |

---

## 🗄️ Database

```bash
# Connection string
postgresql://postgres:postgres@127.0.0.1:54322/postgres

# Direct access
psql postgresql://postgres:postgres@127.0.0.1:54322/postgres

# Status
cd supabase && supabase status
```

---

## 🧪 Testing

```bash
# Run all tests
cd Backend && pytest tests/ -v

# Run specific test type
cd Backend && python tests/run_all_test_types.py

# Frontend tests
cd dashboard && npm test
```

---

## 📁 Key Paths

| What | Where |
|------|-------|
| Backend entry | `Backend/main.py` |
| Frontend pages | `dashboard/app/(dashboard)/` |
| API endpoints | `Backend/api/endpoints/` |
| Database models | `Backend/database/models.py` |
| Migrations | `supabase/migrations/` |
| Logs | `Backend/logs/app.log` |

---

## 🔧 Common Commands

```bash
# Check ports
lsof -i :5555 -i :5557 -i :54322

# View logs
tail -f Backend/logs/app.log

# Database reset (⚠️ deletes data)
cd supabase && supabase db reset

# Apply migrations
cd supabase && supabase db push
```

---

## 📚 Documentation

- **First time?** → `START_HERE.md`
- **Navigation?** → `ONBOARDING_GUIDE.md`
- **Structure?** → `PROJECT_STRUCTURE.md`
- **Database?** → `docs/DATABASE_ARCHITECTURE.md`

---

**Print this and keep it handy! 📌**

