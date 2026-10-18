# MediaPoster Port Topology

**Last Updated:** January 31, 2026  
**Status:** Authoritative Reference

---

## Official Port Assignments

| Port | Service | Protocol | Description |
|------|---------|----------|-------------|
| **5555** | Backend API | HTTP | FastAPI main application |
| **5557** | Frontend/Dashboard | HTTP | Next.js web interface |
| **7070** | Safari Automation Control | HTTP | Safari browser automation commands |
| **7071** | Safari Automation Telemetry | WebSocket | Real-time Safari automation events |
| **9100** | Control Plane API | HTTP/SSE | External command & control interface |
| **54321** | Supabase API Gateway | HTTP | Local Supabase REST/Auth API |
| **54322** | PostgreSQL | TCP | Local Supabase database |
| **54323** | Supabase Studio | HTTP | Database management UI |
| **6379** | Redis | TCP | Caching and job queue |

---

## Service URLs

### Development (localhost)

```bash
# Core Services
BACKEND_URL=http://localhost:5555
FRONTEND_URL=http://localhost:5557
DASHBOARD_URL=http://localhost:5557

# Safari Automation
SAFARI_CONTROL_URL=http://localhost:7070
SAFARI_TELEMETRY_URL=ws://localhost:7071

# Command & Control
C2_API_URL=http://localhost:9100

# Database
SUPABASE_URL=http://127.0.0.1:54321
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres

# Redis
REDIS_URL=redis://localhost:6379/0
```

---

## Quick Start Commands

```bash
# Start Backend (port 5555)
cd Backend && source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload

# Start Frontend/Dashboard (port 5557)
cd Frontend && npm run dev
# or
cd dashboard && npm run dev

# Start Safari Automation (ports 7070/7071)
cd "Safari Automation/packages/protocol" && npm start

# Start Control Plane API (port 9100)
cd Backend && uvicorn control_plane.main:app --port 9100

# Start Supabase (ports 54321/54322/54323)
cd Backend && supabase start
```

---

## Architecture Diagram

```
                    ┌─────────────────────────────────────┐
                    │           MediaPoster               │
                    │                                     │
┌───────────┐       │  ┌─────────────────────────────┐   │
│  Browser  │◀──────┼──│  Frontend (:5557)           │   │
│           │       │  │  Next.js Dashboard          │   │
└───────────┘       │  └──────────────┬──────────────┘   │
                    │                 │                   │
                    │                 ▼                   │
                    │  ┌─────────────────────────────┐   │
                    │  │  Backend API (:5555)        │   │
                    │  │  FastAPI + Celery           │   │
                    │  └──────────────┬──────────────┘   │
                    │                 │                   │
                    │     ┌───────────┴───────────┐       │
                    │     ▼                       ▼       │
                    │  ┌──────────┐         ┌──────────┐ │
                    │  │ Supabase │         │  Redis   │ │
                    │  │ (:54322) │         │ (:6379)  │ │
                    │  └──────────┘         └──────────┘ │
                    │                                     │
                    └─────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                External Services                         │
│                                                          │
│  ┌─────────────────────────┐  ┌─────────────────────┐   │
│  │ Safari Automation       │  │ Control Plane API   │   │
│  │ Control: :7070          │  │ :9100               │   │
│  │ Telemetry: :7071        │  │ Commands + Events   │   │
│  └─────────────────────────┘  └─────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Environment Variables

Add to `.env`:

```bash
# Server Ports
BACKEND_PORT=5555
BACKEND_HOST=0.0.0.0
FRONTEND_PORT=5557
FRONTEND_URL=http://localhost:5557

# Safari Automation
SAFARI_CONTROL_URL=http://localhost:7070
SAFARI_TELEMETRY_URL=ws://localhost:7071

# Control Plane
C2_PORT=9100
C2_BIND_HOST=127.0.0.1
C2_API_KEY=your-api-key

# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:54322/postgres
SUPABASE_URL=http://127.0.0.1:54321
REDIS_URL=redis://localhost:6379/0
```

---

## Port Conflicts

If you encounter port conflicts:

```bash
# Check what's using a port
lsof -i :5555
lsof -i :5557

# Kill process on port
kill -9 $(lsof -t -i:5555)
```

---

## Legacy Port References

**DO NOT USE** - These are deprecated:

| Old Port | Was Used For | New Port |
|----------|--------------|----------|
| 8000 | Backend API | 5555 |
| 3000 | Frontend | 5557 |

If you find references to ports 8000 or 3000 in documentation, they should be updated to 5555 and 5557 respectively.
