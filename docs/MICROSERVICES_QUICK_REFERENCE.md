# MediaPoster Microservices Quick Reference

**Last Updated:** 2026-02-01

---

## TL;DR - Where Does Each Service Go?

| MediaPoster Service | → Target Repo | Port |
|---------------------|---------------|------|
| **Scheduling/Publishing** | Keep in MediaPoster | :5555 |
| **Safari Automation** | `~/Safari Automation/` | :6001 |
| **Video Rendering** | `~/Remotion/` | :6002 |
| **Voice/TTS/Audio** | `~/TTS/` | :6003 |
| **Media Processing** | `~/WaterMarkRemover - BlankLogo/` | :6004 |
| **CRM/Engagement** | `~/Local EverReach CRM/` | :6005 |

---

## Existing Repos Found

```
~/Documents/Software/
├── Safari Automation/      ← Browser automation (TS)
├── Local EverReach CRM/    ← Engagement/CRM (TS)
├── Remotion/               ← Video rendering (TS/Remotion)
├── TTS/                    ← Voice cloning (Python)
└── WaterMarkRemover.../    ← Media processing (TS/Docker)
```

---

## Service File Counts

| Service Category | Files in MediaPoster | Move To |
|------------------|---------------------|---------|
| Safari/Browser Automation | ~15 files | Safari Automation |
| Video Generation | ~50 files | Remotion |
| Voice/Audio/TTS | ~20 files | TTS |
| Media Processing | ~25 files | BlankLogo |
| CRM/Engagement | ~30 files | EverReach CRM |
| AI Services | ~15 files | TBD |
| **Core (Keep)** | ~20 files | MediaPoster |

---

## Migration Priority

```
🔴 HIGH (Do First)
├── Safari Automation (Mac-bound)
├── Media Processing (GPU-heavy)
└── Video Rendering (Memory-heavy)

🟡 MEDIUM (Do Second)
├── Voice/TTS (Specialized)
└── CRM/Engagement (Separate product)

🟢 LOW (Do Last)
└── AI Services (API-bound only)
```

---

## Communication Patterns

```
MediaPoster Core ──WebSocket──► Safari Automation
                ──Redis Queue──► Remotion, TTS, BlankLogo
                ──Event Bus──► EverReach CRM

All Services ──PostgreSQL──► Supabase @ :54322
```

---

## Quick Links

| Document | Purpose |
|----------|---------|
| `ARCHITECTURE_MICROSERVICES_SPLIT.md` | Full architecture proposal |
| `MICROSERVICES_REPO_MAPPING.md` | Detailed file-to-repo mapping |
| `SUPABASE_PORT_REGISTRY.md` | Port assignments |

---

## Core Services (Keep in MediaPoster)

```python
# These files stay - they ARE MediaPoster
services/
├── post_scheduler.py
├── blotato_service.py
├── blotato_api.py
├── publish_service.py
├── smart_scheduler.py
├── sleep_mode_service.py
├── weekly_planner.py
├── approval_queue.py
└── event_bus/
```

---

## Start a Service

```bash
# MediaPoster Core
cd ~/Documents/Software/MediaPoster/Backend && python main.py

# Safari Automation
cd ~/Documents/Software/Safari\ Automation && npm run dev

# Remotion
cd ~/Documents/Software/Remotion && npm run dev

# TTS
cd ~/Documents/Software/TTS && python -m flask run --port 6003

# BlankLogo
cd ~/Documents/Software/WaterMarkRemover\ -\ BlankLogo && npm run dev

# EverReach CRM
cd ~/Documents/Software/Local\ EverReach\ CRM && npm run dev
```

---

## Health Checks

```bash
# All services
curl http://localhost:5555/api/external/health  # MediaPoster
curl http://localhost:6001/health               # Safari Automation
curl http://localhost:6002/health               # Remotion
curl http://localhost:6003/health               # TTS
curl http://localhost:6004/health               # BlankLogo
curl http://localhost:6005/health               # EverReach CRM
```
