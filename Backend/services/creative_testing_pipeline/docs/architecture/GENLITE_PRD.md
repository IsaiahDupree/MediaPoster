# GenLite — Video Generation Job Queue

## Product Requirements Document

### Problem
ACTP's `CreativeEngine` generates videos by calling cloud AI APIs (Sora, Veo3, Nano Banana) and then polling for completion — each job takes 2-10 minutes. This blocks the local Python process, limits throughput to serial generation, and fails entirely if the Mac goes to sleep mid-generation. Remotion renders also tie up local resources (Chrome + ffmpeg) with no queue management.

### Solution
A Vercel-deployed job queue that manages the full lifecycle of video generation:
1. ACTP submits a generation brief (prompt, model, duration, aspect ratio)
2. GenLite submits to the appropriate AI API and begins polling
3. On completion, GenLite stores the output URL in Supabase
4. For Remotion renders (require local Node.js + Chrome), GenLite marks the job as `local_only` — the `actp-worker` daemon picks it up

### Architecture
```
ACTP / ACTPDash
      │
      ▼ POST /api/jobs (brief + model)
  GenLite (Vercel)
      │
      ├── model=sora    → OpenAI Sora API → poll → store URL
      ├── model=veo3    → Google Veo3 API → poll → store URL
      ├── model=nano    → Nano Banana API → poll → store URL
      ├── model=remotion → Mark as local_only
      │
      ▼
  actp_gen_jobs (Supabase)
      │
      ├── Cloud jobs: GenLite cron polls providers for completion
      └── Local jobs:  actp-worker polls → Remotion render → report back
```

### Tech Stack
- **Framework:** Next.js 16 (App Router)
- **Database:** Supabase (shared ACTP project)
- **Hosting:** Vercel (serverless functions + cron)
- **AI APIs:** OpenAI Sora, Google Veo3, Nano Banana
- **Local:** Remotion (via actp-worker)

### Supabase Tables

#### `actp_gen_jobs`
```sql
CREATE TABLE actp_gen_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id TEXT,
  round_id TEXT,
  creative_id TEXT,               -- links back to actp_creatives once created

  -- Brief
  model TEXT NOT NULL,            -- 'sora', 'veo3', 'nano_banana', 'remotion'
  prompt TEXT NOT NULL,
  brief JSONB NOT NULL,           -- full creative brief (hook, cta, angle, script, visual_direction)
  duration_seconds INT DEFAULT 15,
  aspect_ratio TEXT DEFAULT '9:16',
  style TEXT,                     -- 'cinematic', 'ugc', 'animated', etc.

  -- Provider tracking
  provider_job_id TEXT,           -- provider's generation ID for polling
  provider_status TEXT,           -- raw provider status string
  executor TEXT DEFAULT 'cloud',  -- 'cloud' or 'local' (Remotion)

  -- Output
  output_url TEXT,                -- final video URL (CDN or Supabase Storage)
  output_metadata JSONB,          -- provider-specific output data
  file_size_bytes BIGINT,
  thumbnail_url TEXT,

  -- Status
  status TEXT NOT NULL DEFAULT 'pending',  -- pending, submitted, generating, completed, failed, cancelled
  priority INT DEFAULT 5,         -- 1=highest, 10=lowest
  attempts INT DEFAULT 0,
  max_attempts INT DEFAULT 3,
  error TEXT,
  error_history JSONB DEFAULT '[]',

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  submitted_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  claimed_by TEXT,                 -- worker ID for local jobs
  claimed_at TIMESTAMPTZ
);

CREATE INDEX idx_gen_jobs_status ON actp_gen_jobs(status, priority, created_at);
CREATE INDEX idx_gen_jobs_campaign ON actp_gen_jobs(campaign_id);
CREATE INDEX idx_gen_jobs_provider ON actp_gen_jobs(model, provider_job_id);
```

### API Routes

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/jobs` | Submit a new generation job |
| GET | `/api/jobs` | List jobs (filterable by status, model, campaign) |
| GET | `/api/jobs/:id` | Get job details |
| POST | `/api/jobs/:id/cancel` | Cancel a pending/generating job |
| POST | `/api/jobs/:id/retry` | Retry a failed job |
| GET | `/api/jobs/next` | Get next `local_only` job for actp-worker |
| POST | `/api/jobs/:id/claim` | Worker claims a local job |
| POST | `/api/jobs/:id/complete` | Worker reports local job completion |
| POST | `/api/jobs/:id/fail` | Worker reports local job failure |
| POST | `/api/cron/poll-providers` | Cron: poll AI APIs for job completion |
| POST | `/api/cron/retry-failed` | Cron: retry failed jobs under max_attempts |
| GET | `/api/health` | Health check |
| GET | `/api/stats` | Job statistics by model/status |
| GET | `/api/providers` | Available providers and their API key status |

### Vercel Cron Configuration
```json
{
  "crons": [
    {
      "path": "/api/cron/poll-providers",
      "schedule": "*/2 * * * *"
    },
    {
      "path": "/api/cron/retry-failed",
      "schedule": "*/15 * * * *"
    }
  ]
}
```

### Generation Flow

#### Cloud Jobs (Sora, Veo3, Nano Banana)
1. `POST /api/jobs` with `{ model: "sora", brief: {...}, campaign_id: "..." }`
2. GenLite validates brief, writes to `actp_gen_jobs` with `status: "pending"`
3. GenLite immediately submits to provider API, updates `status: "submitted"`, stores `provider_job_id`
4. Cron `/api/cron/poll-providers` runs every 2 minutes:
   - Query `actp_gen_jobs WHERE status IN ('submitted', 'generating')`
   - Poll each provider for status
   - On success: download video → upload to Supabase Storage → update `output_url`, `status: "completed"`
   - On failure: increment `attempts`, set `status: "failed"` if `attempts >= max_attempts`
5. Once completed, GenLite updates `actp_creatives.video_url` if `creative_id` is set

#### Local Jobs (Remotion)
1. `POST /api/jobs` with `{ model: "remotion", brief: {...}, template: "hook-cta-vertical" }`
2. GenLite writes to `actp_gen_jobs` with `executor: "local"`, `status: "pending"`
3. `actp-worker` polls `GET /api/jobs/next` → gets the Remotion job
4. Worker claims → renders locally with Remotion → uploads to Supabase Storage
5. Worker calls `POST /api/jobs/:id/complete` with `output_url`

### Provider Implementations

#### Sora (OpenAI)
- Submit: `POST https://api.openai.com/v1/videos/generations`
- Poll: `GET https://api.openai.com/v1/videos/generations/{id}`
- Timeout: 10 minutes
- Output: download URL (expires)

#### Veo3 (Google)
- Submit: `POST https://generativelanguage.googleapis.com/v1beta/models/veo-3.0-generate-preview:predictLongRunning`
- Poll: `GET https://generativelanguage.googleapis.com/v1beta/{operation_name}`
- Timeout: 15 minutes
- Output: GCS URI

#### Nano Banana
- Submit: `POST https://api.nanobanana.com/v1/videos/generate`
- Poll: response includes `video_url` when done (or webhook)
- Timeout: 5 minutes
- Output: direct URL

### Dashboard Pages

| Page | Path | Purpose |
|------|------|---------|
| Jobs | `/` | Live job queue with status badges, grouped by campaign |
| Job Detail | `/jobs/[id]` | Full brief, provider logs, output preview, retry button |
| Providers | `/providers` | Provider health, API key status, usage stats |
| Stats | `/stats` | Generation counts, success rates, avg duration by model |

### Environment Variables
```
NEXT_PUBLIC_SUPABASE_URL=...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...

GENLITE_MASTER_KEY=gl_...
CRON_SECRET=...

OPENAI_API_KEY=...
GOOGLE_API_KEY=...
NANO_BANANA_API_KEY=...
```

### CLI Commands
```bash
genlite health                       # Health check
genlite jobs                         # List recent jobs
genlite jobs <id>                    # Job details
genlite submit --model sora --prompt "..." --campaign <id>
genlite cancel <id>                  # Cancel a job
genlite retry <id>                   # Retry a failed job
genlite stats                        # Generation statistics
genlite providers                    # Provider status
```

### Success Criteria
1. Sora/Veo3/Nano Banana jobs complete end-to-end without local machine
2. Remotion jobs picked up by actp-worker within 30 seconds of submission
3. Failed jobs auto-retry up to 3 times with exponential backoff
4. Video output URLs accessible from any service (Supabase Storage)
5. Dashboard shows real-time job status
6. Average Sora turnaround < 5 min, Veo3 < 12 min
