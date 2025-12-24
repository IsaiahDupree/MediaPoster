# 🎯 START HERE - MediaPoster First Time Setup

**Welcome! This is your quick-start guide to get MediaPoster running.**

---

## ✅ Prerequisites Checklist

Before starting, ensure you have:

- [ ] **Python 3.10+** installed (`python3 --version`)
- [ ] **Node.js 18+** installed (`node --version`)
- [ ] **FFmpeg** installed (`ffmpeg -version`)
- [ ] **Supabase CLI** installed (`supabase --version`)
- [ ] **Git** installed (`git --version`)

**Install missing tools:**
```bash
# macOS
brew install python@3.10 node ffmpeg supabase/tap/supabase

# Or use existing installations
```

---

## 🚀 3-Step Startup

### Step 1: Start Database (Terminal 1)
```bash
cd supabase
supabase start
```
**✅ Success when you see:** "API URL: http://127.0.0.1:54321"

**⏱️ First time:** May take 2-3 minutes to download Docker images

---

### Step 2: Start Backend (Terminal 2)
```bash
cd Backend

# Activate virtual environment
source venv/bin/activate  # You should see (venv) in prompt

# If venv doesn't exist, create it:
# python3 -m venv venv
# source venv/bin/activate
# pip install -r requirements.txt

# Start server
uvicorn main:app --port 5555 --reload
```
**✅ Success when you see:** "Uvicorn running on http://0.0.0.0:5555"

**🔍 Verify:** Open http://localhost:5555/docs (should show Swagger UI)

---

### Step 3: Start Frontend (Terminal 3)
```bash
cd dashboard

# Install dependencies (first time only)
npm install

# Start dev server
npm run dev
```
**✅ Success when you see:** "Ready on http://localhost:5557"

**🔍 Verify:** Open http://localhost:5557 (should show dashboard)

---

## 🎉 You're Running!

**Access Points:**
- **Dashboard:** http://localhost:5557
- **API Docs:** http://localhost:5555/docs
- **Database UI:** http://localhost:54323
- **API Health:** http://localhost:5555/api/health

---

## ⚠️ Troubleshooting

### "Database connection refused"
→ Make sure Supabase is running: `cd supabase && supabase status`

### "Module not found" (Python)
→ Activate venv: `source venv/bin/activate`

### "Cannot find module" (Node)
→ Install dependencies: `cd dashboard && npm install`

### "Port already in use"
→ Check what's using the port: `lsof -i :5555`

---

## 📚 Next Steps

1. **Read:** `ONBOARDING_GUIDE.md` for detailed navigation
2. **Explore:** `PROJECT_STRUCTURE.md` for directory map
3. **Check:** `docs/DATABASE_ARCHITECTURE.md` for database schema

---

## 🆘 Need Help?

- Check logs: `Backend/logs/app.log`
- Check database: http://localhost:54323
- Check API: http://localhost:5555/docs
- Read: `ONBOARDING_GUIDE.md`

---

**Happy coding! 🚀**

