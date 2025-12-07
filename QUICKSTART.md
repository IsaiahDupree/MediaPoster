# MediaPoster Quickstart Guide

This guide provides commands to start, stop, and manage the MediaPoster application (Backend + Frontend).

## 🚀 Start Servers

You will need two terminal windows.

### Terminal 1: Backend (FastAPI)
```bash
cd Backend
# Option A: Using the start script (Interactive)
./start.sh

# Option B: Direct command (Development Mode)
# Make sure venv is active: source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload
```
*Backend runs on: http://localhost:5555*
*API Docs: http://localhost:5555/docs*

### Terminal 2: Frontend (Next.js)
```bash
cd frontend
npm run dev -- -p 5557
```
*Frontend runs on: http://localhost:5557*

---

## 🛑 Stop Servers

To stop a server, simply press `Ctrl + C` in the respective terminal window.

If a process is stuck or running in the background, you can kill it by port:

**Kill Backend (Port 5555):**
```bash
lsof -ti:5555 | xargs kill -9
```

**Kill Frontend (Port 5557):**
```bash
lsof -ti:5557 | xargs kill -9
```

---

## 🔄 Restart Servers

To restart, simply stop the server (`Ctrl + C`) and run the start command again.

If you made changes to the **Backend code**, it should auto-reload if you used the `--reload` flag.
If you made changes to the **Frontend code**, Next.js usually auto-reloads, but sometimes a hard refresh is needed.

---

## 🧪 Verification

Once both servers are running:

1.  **Open Frontend:** Go to [http://localhost:5557](http://localhost:5557)
2.  **Check Backend Health:** Go to [http://localhost:5555/docs](http://localhost:5555/docs)
3.  **Run E2E Test:**
    ```bash
    # From the root directory
    python3 Backend/test_everreach_e2e.py
    ```

---

## 📍 New Features

The following new pages are now available:
- `/content` - Content Graph Dashboard (manage items and variants)
- `/segments` - Audience Segments (view insights)
- `/briefs` - Content Briefs Generator (AI-powered content ideas)
