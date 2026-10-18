# actp-worker — Local Worker Daemon

## Product Requirements Document

### Problem
Several ACTP operations require macOS-native resources that cannot run on Vercel:
- **Safari browser automation** for TikTok, Instagram, and YouTube uploads
- **Blotato** macOS app for platform uploads via its local HTTP API
- **Remotion** video rendering requires Node.js, Chrome/Chromium, and ffmpeg
- **File system** access for downloading AI-generated videos and staging for upload

These tasks are queued in cloud services (MPLite, GenLite) but need a local executor.

### Solution
A single Python daemon that runs on the local Mac, polls all cloud queues, and executes tasks that require native resources. It's the bridge between the Vercel-hosted Lite services and the macOS-only tools.

### Architecture
```
┌─────────────────────────────────────────────────┐
│            actp-worker (local Mac)               │
│                                                   │
│  ┌─────────────────────────────────────────┐     │
│  │          Polling Loop (async)            │     │
│  │                                          │     │
│  │  ┌──────────┐  ┌──────────┐             │     │
│  │  │ MPLite   │  │ GenLite  │             │     │
│  │  │ Poller   │  │ Poller   │             │     │
│  │  └────┬─────┘  └────┬─────┘             │     │
│  │       │              │                   │     │
│  │       ▼              ▼                   │     │
│  │  ┌──────────────────────────────────┐   │     │
│  │  │         Task Router               │   │     │
│  │  │  publish job → Safari/Blotato     │   │     │
│  │  │  render job  → Remotion           │   │     │
│  │  └──────────────────────────────────┘   │     │
│  └─────────────────────────────────────────┘     │
│                                                   │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐        │
│  │  Safari   │ │ Blotato  │ │ Remotion  │        │
│  │  runner   │ │ client   │ │ renderer  │        │
│  └──────────┘ └──────────┘ └───────────┘        │
│                                                   │
│  ┌──────────────────────────────────────────┐    │
│  │  Heartbeat → Supabase (every 60s)        │    │
│  │  Reports: online, current job, system     │    │
│  └──────────────────────────────────────────┘    │
└─────────────────────────────────────────────────┘
```

### Tech Stack
- **Language:** Python 3.11+
- **Async:** asyncio + httpx (for polling REST APIs)
- **Local tools:** Safari via AppleScript/subprocess, Blotato via HTTP, Remotion via Node subprocess
- **Config:** .env file + CLI flags
- **Process management:** launchd (macOS) for auto-start on login

### Supabase Tables

#### `actp_worker_heartbeats` (new)
```sql
CREATE TABLE actp_worker_heartbeats (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  worker_id TEXT NOT NULL UNIQUE,
  hostname TEXT,
  os_version TEXT,
  python_version TEXT,
  status TEXT NOT NULL DEFAULT 'online',  -- online, busy, offline
  current_job JSONB,                       -- {service, job_id, type, started_at}
  capabilities JSONB DEFAULT '[]',         -- ['safari', 'blotato', 'remotion', 'ffmpeg']
  jobs_completed INT DEFAULT 0,
  jobs_failed INT DEFAULT 0,
  last_heartbeat TIMESTAMPTZ DEFAULT NOW(),
  started_at TIMESTAMPTZ DEFAULT NOW(),
  system_info JSONB                        -- cpu, memory, disk usage
);

CREATE INDEX idx_heartbeats_worker ON actp_worker_heartbeats(worker_id);
```

#### `actp_worker_logs` (new)
```sql
CREATE TABLE actp_worker_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  worker_id TEXT NOT NULL,
  level TEXT NOT NULL,           -- 'info', 'warn', 'error', 'debug'
  service TEXT,                  -- 'mplite', 'genlite', 'system'
  job_id TEXT,
  message TEXT NOT NULL,
  details JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_worker_logs_worker ON actp_worker_logs(worker_id, created_at DESC);
```

### Core Modules

#### `worker.py` — Main Daemon
```python
# Pseudocode structure
class ACTPWorker:
    def __init__(self, config):
        self.worker_id = f"worker-{hostname}-{pid}"
        self.pollers = [
            MPLitePoller(config.mplite_url, config.mplite_key),
            GenLitePoller(config.genlite_url, config.genlite_key),
        ]
        self.executors = {
            "safari": SafariExecutor(),
            "blotato": BlotatoExecutor(config.blotato_url),
            "remotion": RemotionExecutor(config.remotion_path),
        }
        self.heartbeat = HeartbeatReporter(config.supabase, self.worker_id)

    async def run(self):
        # Start heartbeat
        asyncio.create_task(self.heartbeat.start(interval=60))
        # Main polling loop
        while True:
            for poller in self.pollers:
                job = await poller.poll()
                if job:
                    await self.execute(job)
            await asyncio.sleep(config.poll_interval)  # default 10s

    async def execute(self, job):
        executor = self.route(job)
        self.heartbeat.set_busy(job)
        try:
            result = await executor.run(job)
            await job.poller.report_complete(job.id, result)
            self.heartbeat.increment_completed()
        except Exception as e:
            await job.poller.report_fail(job.id, str(e))
            self.heartbeat.increment_failed()
        finally:
            self.heartbeat.set_online()
```

#### `pollers/mplite_poller.py` — MPLite Queue Poller
- Calls `GET /api/queue/next` on MPLite
- Claims the job via `POST /api/queue/{id}/claim`
- Routes to Safari or Blotato executor based on `executor` field
- Reports completion via `POST /api/queue/{id}/complete`

#### `pollers/genlite_poller.py` — GenLite Job Poller
- Calls `GET /api/jobs/next` on GenLite (only `local_only` jobs)
- Claims via `POST /api/jobs/{id}/claim`
- Routes to Remotion executor
- Uploads rendered video to Supabase Storage
- Reports completion via `POST /api/jobs/{id}/complete`

#### `executors/safari_executor.py` — Safari Automation
- Wraps existing `safari_tiktok_cli` and `safari_instagram_poster`
- Downloads video to temp dir if needed
- Launches Safari automation via AppleScript/subprocess
- Waits for completion, captures post URL
- Returns `{ post_url, platform_post_id }`

#### `executors/blotato_executor.py` — Blotato Local API
- Discovers Blotato's local HTTP port
- `POST http://localhost:{port}/api/upload` with video file + metadata
- Polls for upload completion
- Returns `{ post_url, platform_post_id }`

#### `executors/remotion_executor.py` — Remotion Renderer
- Receives render brief (template, props, duration, output format)
- Runs `npx remotion render` via subprocess
- Monitors progress via Remotion's stdout
- Uploads output to Supabase Storage
- Returns `{ output_url, file_size, duration }`

#### `heartbeat.py` — Heartbeat Reporter
- Every 60 seconds: upsert `actp_worker_heartbeats` with current status
- Includes: hostname, capabilities, current job, system info (CPU/memory/disk)
- On shutdown: sets status to `offline`
- ACTPDash reads this to show worker status

### CLI Interface
```bash
# Start the worker daemon
actp-worker start
actp-worker start --poll-interval 5     # Poll every 5 seconds
actp-worker start --services mplite     # Only poll MPLite
actp-worker start --daemon              # Run as background daemon

# Status and control
actp-worker status                       # Current worker status
actp-worker stop                         # Graceful shutdown
actp-worker logs                         # Tail worker logs
actp-worker logs --level error           # Filter by level
actp-worker capabilities                 # List detected capabilities

# Manual job execution (for testing)
actp-worker run-safari --video /path/to/video.mp4 --platform tiktok --caption "..."
actp-worker run-blotato --video /path/to/video.mp4 --platform instagram --caption "..."
actp-worker run-remotion --template hook-cta --props '{"hook": "...", "cta": "..."}'

# Diagnostics
actp-worker check-safari                 # Verify Safari automation works
actp-worker check-blotato                # Verify Blotato is running and reachable
actp-worker check-remotion               # Verify Remotion + ffmpeg installed
actp-worker check-all                    # Check all capabilities
```

### Configuration (.env)
```
# Cloud service URLs
MPLITE_URL=https://mediaposter-lite-...vercel.app
MPLITE_KEY=mpl_...
GENLITE_URL=https://genlite-...vercel.app
GENLITE_KEY=gl_...

# Supabase (for heartbeat + logs)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Local tools
BLOTATO_LOCAL_URL=http://localhost:PORT
REMOTION_PROJECT_PATH=/path/to/remotion/project

# Worker config
WORKER_POLL_INTERVAL=10        # seconds between polls
WORKER_MAX_CONCURRENT=2        # max concurrent jobs
WORKER_DOWNLOAD_DIR=/tmp/actp-worker
WORKER_LOG_LEVEL=info
```

### macOS Auto-Start (launchd)

```xml
<!-- ~/Library/LaunchAgents/com.actp.worker.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.actp.worker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/path/to/actp-worker/worker.py</string>
        <string>start</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/actp-worker.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/actp-worker.error.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>DOTENV_PATH</key>
        <string>/path/to/actp-worker/.env</string>
    </dict>
</dict>
</plist>
```

Install with:
```bash
actp-worker install-service    # Copies plist + enables
actp-worker uninstall-service  # Removes plist
```

### File Structure
```
actp-worker/
├── worker.py                  # Main daemon entry point
├── config.py                  # Configuration loader
├── pollers/
│   ├── __init__.py
│   ├── base_poller.py
│   ├── mplite_poller.py
│   └── genlite_poller.py
├── executors/
│   ├── __init__.py
│   ├── base_executor.py
│   ├── safari_executor.py
│   ├── blotato_executor.py
│   └── remotion_executor.py
├── heartbeat.py
├── cli.py                     # CLI interface
├── diagnostics.py             # Capability checks
├── requirements.txt
├── .env.example
├── com.actp.worker.plist      # launchd template
└── README.md
```

### Capability Detection
On startup, actp-worker probes for available tools:
1. **Safari:** Check `osascript` available + Safari installed
2. **Blotato:** HTTP GET to `BLOTATO_LOCAL_URL/api/status`
3. **Remotion:** Check `npx remotion --version` + `ffmpeg -version`
4. **ffmpeg:** Check `ffmpeg -version`

Capabilities are reported in heartbeat. Jobs requiring unavailable capabilities are skipped (not claimed).

### Error Handling
- **Network failure:** Exponential backoff on poll failures (10s → 20s → 40s → max 5min)
- **Safari crash:** Kill Safari process, retry once, then fail the job
- **Blotato unreachable:** Skip Blotato jobs, log warning, retry on next poll
- **Remotion timeout:** Kill render process after 10 minutes, fail the job
- **Disk full:** Check available space before downloads, skip if < 1GB free

### Success Criteria
1. Worker starts on login and runs continuously via launchd
2. MPLite publish jobs executed within 30 seconds of availability
3. Remotion render jobs picked up and completed without manual intervention
4. Blotato uploads work when Blotato is running
5. Heartbeat visible in ACTPDash within 60 seconds of worker start
6. Graceful degradation: missing capabilities don't crash the worker
7. Zero manual intervention for normal operation — fully autonomous
