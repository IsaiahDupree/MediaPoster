# MediaPoster Microservices Implementation Guide

**Created:** 2026-02-01  
**Status:** Active Implementation

---

## Service Registry

| Service | Repo | Port | Health Endpoint |
|---------|------|------|-----------------|
| **MediaPoster Core** | `MediaPoster/` | `:5555` | `/api/external/health` |
| **Safari Automation** | `Safari Automation/` | `:6001` | `/health` |
| **Remotion (Video+Audio)** | `Remotion/` | `:6002` | `/health` |
| **Media Pipeline** | `media-pipeline/` | `:6004` | `/health` |
| **Content Intelligence** | `content-intelligence/` | `:6006` | `/health` |

---

## 1. Connectivity Patterns

### Service-to-Service Communication

```
┌─────────────────┐     HTTP/JSON      ┌─────────────────┐
│  MediaPoster    │◄──────────────────►│ Safari Auto     │
│     :5555       │     WebSocket      │     :6001       │
└────────┬────────┘                    └─────────────────┘
         │
         │ Redis Queue (async jobs)
         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Remotion      │     │ Media Pipeline  │     │Content Intel    │
│     :6002       │     │     :6004       │     │     :6006       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Communication Methods

| From → To | Method | Use Case |
|-----------|--------|----------|
| Core → Safari | WebSocket | Real-time browser control |
| Core → Remotion | Redis Queue | Async video renders |
| Core → Media Pipeline | HTTP POST | Sync analysis requests |
| Core → Content Intel | HTTP POST | AI inference requests |
| Any → Any | Event Bus | Pub/sub notifications |

---

## 2. Shared Configuration

### Environment Variables (all services)

```bash
# Shared Database
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=<key>
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:54322/postgres

# Redis (job queues)
REDIS_URL=redis://localhost:6379

# Service Discovery
MEDIAPOSTER_URL=http://localhost:5555
SAFARI_URL=http://localhost:6001
REMOTION_URL=http://localhost:6002
MEDIA_PIPELINE_URL=http://localhost:6004
CONTENT_INTEL_URL=http://localhost:6006
```

---

## 3. Service Capabilities

### MediaPoster Core (:5555)
- **Scheduling** - Post scheduling, smart scheduling
- **Publishing** - Multi-platform publishing via Blotato
- **Queue Management** - Approval queues, inventory
- **Event Bus** - Cross-service event coordination

### Safari Automation (:6001)
- **Browser Control** - Safari WebDriver automation
- **Platform Actions** - Post, comment, DM on social platforms
- **Session Management** - Login state, cookie persistence
- **Scraping** - Content collection from platforms

### Remotion Video+Audio (:6002)
- **Video Rendering** - Remotion compositions
- **TTS Generation** - Voice synthesis
- **Music Selection** - Background music matching
- **Audio Processing** - Transcription, voice cloning

### Media Pipeline (:6004)
- **Thumbnail Generation** - Frame extraction, AI selection
- **Format Detection** - Video format classification
- **Clip Extraction** - Segment extraction
- **Deduplication** - Content fingerprinting

### Content Intelligence (:6006)
- **Content Analysis** - FATE scoring, awareness classification
- **AI Generation** - Titles, captions, recommendations
- **Vision Analysis** - Frame analysis, scene detection
- **Sentiment Analysis** - Comment/content sentiment

---

## 4. API Contracts

### Health Check (all services)

```http
GET /health
Response: { "status": "healthy", "service": "<name>", "version": "1.0.0" }
```

### Safari Automation API

```http
POST /api/browser/navigate
{ "url": "https://twitter.com", "wait_for": "networkidle" }

POST /api/browser/execute
{ "script": "document.querySelector('.tweet-button').click()" }

POST /api/post/twitter
{ "content": "Hello world", "media_path": "/path/to/video.mp4" }

GET /api/session/status
Response: { "logged_in": true, "platform": "twitter" }
```

### Remotion API

```http
POST /api/render
{
  "composition": "AdTemplate",
  "props": { "headline": "Sale!", "background": "#ff0000" },
  "output_format": "mp4"
}

POST /api/tts/generate
{ "text": "Hello world", "voice": "isaiah", "emotion": "excited" }

POST /api/audio/transcribe
{ "audio_path": "/path/to/audio.mp3" }
```

### Media Pipeline API

```http
POST /api/analyze
{ "video_path": "/path/to/video.mp4" }

POST /api/thumbnail/generate
{ "video_path": "/path/to/video.mp4", "count": 5 }

POST /api/format/detect
{ "file_path": "/path/to/media.mp4" }
```

### Content Intelligence API

```http
POST /api/analyze/content
{ "title": "...", "description": "...", "transcript": "..." }

POST /api/generate/title
{ "content": "...", "platform": "tiktok", "style": "viral" }

POST /api/score/fate
{ "content_id": "uuid", "metrics": {...} }
```

---

## 5. Implementation Files

### Shared Service Client (for each repo)

```python
# shared/service_client.py
import os
import httpx

class ServiceClient:
    def __init__(self):
        self.services = {
            "core": os.getenv("MEDIAPOSTER_URL", "http://localhost:5555"),
            "safari": os.getenv("SAFARI_URL", "http://localhost:6001"),
            "remotion": os.getenv("REMOTION_URL", "http://localhost:6002"),
            "media": os.getenv("MEDIA_PIPELINE_URL", "http://localhost:6004"),
            "ai": os.getenv("CONTENT_INTEL_URL", "http://localhost:6006"),
        }
    
    async def call(self, service: str, endpoint: str, data: dict = None):
        url = f"{self.services[service]}{endpoint}"
        async with httpx.AsyncClient(timeout=30) as client:
            if data:
                response = await client.post(url, json=data)
            else:
                response = await client.get(url)
            return response.json()
    
    async def health_check(self, service: str) -> bool:
        try:
            result = await self.call(service, "/health")
            return result.get("status") == "healthy"
        except:
            return False
```

---

## 6. Test Commands

### Health Check All Services

```bash
# Check all services
curl http://localhost:5555/api/external/health  # Core
curl http://localhost:6001/health               # Safari
curl http://localhost:6002/health               # Remotion
curl http://localhost:6004/health               # Media Pipeline
curl http://localhost:6006/health               # Content Intel
```

### Connectivity Test Script

```bash
#!/bin/bash
# test_connectivity.sh

services=("5555" "6001" "6002" "6004" "6006")
names=("MediaPoster" "Safari" "Remotion" "MediaPipeline" "ContentIntel")

for i in "${!services[@]}"; do
    port=${services[$i]}
    name=${names[$i]}
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1; then
        echo "✅ $name (:$port) - UP"
    else
        echo "❌ $name (:$port) - DOWN"
    fi
done
```

---

## 7. Startup Order

1. **Redis** - Start first (job queues)
2. **Supabase** - Database
3. **MediaPoster Core** - Main orchestrator
4. **Safari Automation** - Browser service
5. **Remotion** - Video rendering
6. **Media Pipeline** - Analysis
7. **Content Intelligence** - AI

```bash
# Start all services
docker-compose up -d redis
cd ~/Documents/Software/MediaPoster && supabase start
cd ~/Documents/Software/MediaPoster/Backend && python main.py &
cd ~/Documents/Software/Safari\ Automation && npm run dev &
cd ~/Documents/Software/Remotion && npm run dev &
cd ~/Documents/Software/media-pipeline && python -m flask run --port 6004 &
cd ~/Documents/Software/content-intelligence && python -m flask run --port 6006 &
```

---

## 8. Next Implementation Steps

- [ ] Add `/health` endpoint to each new service
- [ ] Create shared `service_client.py` in each repo
- [ ] Add Redis connection for job queues
- [ ] Implement API endpoints per contract above
- [ ] Write integration tests
- [ ] Create docker-compose for full stack
