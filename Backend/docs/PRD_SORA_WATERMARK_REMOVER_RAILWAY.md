# PRD: Sora Watermark Remover Service

**Version:** 1.0  
**Date:** January 3, 2026  
**Author:** MediaPoster Team  
**Platform:** Railway  

---

## 1. Executive Summary

A cloud-hosted service that removes watermarks from Sora-generated videos using FFmpeg crop processing. Deployed on Railway for reliable, scalable video processing with a simple REST API.

### Key Value Proposition
- **One-click watermark removal** for Sora AI-generated videos
- **API-first design** for integration with existing workflows
- **Cost-effective** processing at ~$0.01-0.03 per video
- **Fast turnaround** - 5-15 seconds per video

---

## 2. Problem Statement

### Current Pain Points
1. Sora videos include a persistent watermark ("Sora @username") at the bottom
2. Manual FFmpeg processing requires technical knowledge
3. No existing SaaS solution specifically for Sora watermarks
4. Local processing doesn't scale for batch operations

### Target Users
- **Content creators** using Sora for social media content
- **Marketing teams** producing AI-generated video ads
- **Developers** building on top of Sora's API
- **MediaPoster users** automating video posting workflows

---

## 3. Solution Overview

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         RAILWAY                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │   Next.js   │    │   FastAPI   │    │   Redis Queue       │  │
│  │  Frontend   │───▶│   Backend   │───▶│   (Bull/BullMQ)     │  │
│  │  (Web UI)   │    │   (API)     │    │                     │  │
│  └─────────────┘    └─────────────┘    └──────────┬──────────┘  │
│                                                    │             │
│                           ┌────────────────────────▼──────────┐  │
│                           │        Worker Service             │  │
│                           │   (FFmpeg Processing Container)   │  │
│                           └────────────────────────┬──────────┘  │
└────────────────────────────────────────────────────┼─────────────┘
                                                     │
                              ┌──────────────────────▼──────────┐
                              │     Cloudflare R2 / S3          │
                              │     (Video Storage)             │
                              └─────────────────────────────────┘
```

### Technology Stack

| Component | Technology | Justification |
|-----------|------------|---------------|
| **Runtime** | Python 3.11 | Railway default, optimal compatibility |
| **API** | FastAPI | High performance async web framework |
| **Queue** | Redis + BullMQ | Job queue for async processing |
| **Worker** | Python + FFmpeg Docker | Video processing container |
| **Storage** | Cloudflare R2 | Cost-effective S3-compatible storage |
| **Database** | PostgreSQL | Job tracking and metadata |

---

## 4. Feature Requirements

### 4.1 Core Features (MVP)

#### F1: Video Upload
- **Priority:** P0
- **Description:** Users can upload Sora videos via web UI or API
- **Acceptance Criteria:**
  - Support MP4, MOV, WebM formats
  - Max file size: 500MB
  - Drag-and-drop upload interface
  - Progress indicator during upload

#### F2: Watermark Removal Processing
- **Priority:** P0
- **Description:** Automatically detect and remove Sora watermark
- **Acceptance Criteria:**
  - Crop bottom 100px (configurable)
  - Preserve audio track
  - Maintain original quality (no re-encoding video stream)
  - Processing time < 30 seconds for typical video

#### F3: Download Clean Video
- **Priority:** P0
- **Description:** Users can download the processed video
- **Acceptance Criteria:**
  - Direct download link
  - Signed URLs with 24-hour expiry
  - Original filename preserved with "_clean" suffix

#### F4: REST API
- **Priority:** P0
- **Description:** Programmatic access to all features
- **Endpoints:**
  ```
  POST /api/v1/jobs           - Create new removal job
  GET  /api/v1/jobs/{id}      - Get job status
  GET  /api/v1/jobs/{id}/download - Get download URL
  DELETE /api/v1/jobs/{id}    - Cancel/delete job
  ```

### 4.2 Enhanced Features (v1.1)

#### F5: Batch Processing
- **Priority:** P1
- **Description:** Process multiple videos in one request
- **Acceptance Criteria:**
  - Upload up to 20 videos per batch
  - Parallel processing (up to 5 concurrent)
  - ZIP download option for batch results

#### F6: Webhook Notifications
- **Priority:** P1
- **Description:** Notify external systems when processing completes
- **Acceptance Criteria:**
  - Configurable webhook URL per job
  - Retry logic (3 attempts with exponential backoff)
  - HMAC signature verification

#### F7: Custom Crop Settings
- **Priority:** P2
- **Description:** Allow users to customize crop parameters
- **Acceptance Criteria:**
  - Crop from any edge (top, bottom, left, right)
  - Pixel or percentage-based cropping
  - Preview before processing

### 4.3 Integration Features (v1.2)

#### F8: MediaPoster Integration
- **Priority:** P1
- **Description:** Direct integration with MediaPoster pipeline
- **Acceptance Criteria:**
  - Auto-ingest cleaned videos to MediaPoster
  - Trigger analysis pipeline after cleaning
  - Source tracking (source_type = 'sora')

#### F9: Sora API Integration
- **Priority:** P2
- **Description:** Direct connection to Sora generation API
- **Acceptance Criteria:**
  - Generate + clean in one workflow
  - Store generation prompts with videos
  - Re-generate options

---

## 5. API Specification

### Authentication
```
Authorization: Bearer <API_KEY>
```

### Endpoints

#### POST /api/v1/jobs
Create a new watermark removal job.

**Request:**
```json
{
  "video_url": "https://example.com/sora_video.mp4",
  "crop_pixels": 100,
  "crop_position": "bottom",
  "webhook_url": "https://myapp.com/webhook",
  "metadata": {
    "original_prompt": "A cat playing piano",
    "source": "sora_api"
  }
}
```

**Response:**
```json
{
  "job_id": "job_abc123xyz",
  "status": "queued",
  "created_at": "2026-01-03T09:30:00Z",
  "estimated_completion": "2026-01-03T09:30:15Z"
}
```

#### GET /api/v1/jobs/{job_id}
Get job status and results.

**Response:**
```json
{
  "job_id": "job_abc123xyz",
  "status": "completed",
  "progress": 100,
  "input": {
    "filename": "sora_video.mp4",
    "size_bytes": 15086580,
    "duration_sec": 12.5
  },
  "output": {
    "filename": "sora_video_clean.mp4",
    "size_bytes": 14892340,
    "download_url": "https://r2.example.com/signed/...",
    "expires_at": "2026-01-04T09:30:00Z"
  },
  "processing_time_ms": 8450,
  "created_at": "2026-01-03T09:30:00Z",
  "completed_at": "2026-01-03T09:30:08Z"
}
```

#### POST /api/v1/jobs/batch
Create multiple jobs at once.

**Request:**
```json
{
  "videos": [
    {"video_url": "https://example.com/video1.mp4"},
    {"video_url": "https://example.com/video2.mp4"},
    {"video_url": "https://example.com/video3.mp4"}
  ],
  "crop_pixels": 100,
  "webhook_url": "https://myapp.com/batch-webhook"
}
```

**Response:**
```json
{
  "batch_id": "batch_xyz789",
  "jobs": [
    {"job_id": "job_001", "status": "queued"},
    {"job_id": "job_002", "status": "queued"},
    {"job_id": "job_003", "status": "queued"}
  ],
  "total": 3
}
```

---

## 6. Database Schema

```sql
-- Jobs table
CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    status VARCHAR(20) DEFAULT 'queued',  -- queued, processing, completed, failed
    
    -- Input
    input_url TEXT NOT NULL,
    input_filename VARCHAR(255),
    input_size_bytes BIGINT,
    input_duration_sec NUMERIC(10,2),
    
    -- Processing config
    crop_pixels INTEGER DEFAULT 100,
    crop_position VARCHAR(10) DEFAULT 'bottom',
    
    -- Output
    output_url TEXT,
    output_filename VARCHAR(255),
    output_size_bytes BIGINT,
    
    -- Webhook
    webhook_url TEXT,
    webhook_sent_at TIMESTAMPTZ,
    
    -- Metadata
    metadata JSONB,
    error_message TEXT,
    processing_time_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days'
);

-- Users table (for API keys)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    api_key VARCHAR(64) UNIQUE NOT NULL,
    plan VARCHAR(20) DEFAULT 'free',  -- free, pro, enterprise
    credits_remaining INTEGER DEFAULT 10,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Usage tracking
CREATE TABLE usage_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    job_id UUID REFERENCES jobs(id),
    action VARCHAR(50),
    credits_used INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_jobs_user_id ON jobs(user_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_created_at ON jobs(created_at DESC);
CREATE INDEX idx_users_api_key ON users(api_key);
```

---

## 7. Railway Deployment Configuration

### railway.toml
```toml
[build]
builder = "dockerfile"

[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "on_failure"
restartPolicyMaxRetries = 3
```

### Dockerfile (Worker)
```dockerfile
FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "worker.py"]
```

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://...

# Redis
REDIS_URL=redis://...

# Storage (Cloudflare R2)
R2_ACCOUNT_ID=xxx
R2_ACCESS_KEY_ID=xxx
R2_SECRET_ACCESS_KEY=xxx
R2_BUCKET_NAME=sora-watermark-remover

# API
API_SECRET_KEY=xxx
CORS_ORIGINS=https://watermark.example.com

# Limits
MAX_FILE_SIZE_MB=500
MAX_CONCURRENT_JOBS=5
JOB_TIMEOUT_SECONDS=300
```

### Railway Services

| Service | Type | Instances | Resources |
|---------|------|-----------|-----------|
| **api** | Web | 1 | 512MB RAM, 0.5 vCPU |
| **worker** | Worker | 2 | 2GB RAM, 1 vCPU |
| **redis** | Plugin | 1 | 256MB |
| **postgres** | Plugin | 1 | 1GB |

---

## 8. Cost Analysis

### Railway Costs (Estimated Monthly)

| Resource | Usage | Cost |
|----------|-------|------|
| API Service | 720 hrs | $5 |
| Worker (2x) | 1440 hrs | $20 |
| Redis | 256MB | $3 |
| Postgres | 1GB | $7 |
| Bandwidth | 100GB | $10 |
| **Total** | | **~$45/month** |

### Per-Video Cost
- Average video: 15MB input, 10s processing
- Storage: $0.015/GB/month (R2)
- Processing: ~$0.005 per video
- **Total: ~$0.02 per video**

### Pricing Tiers (Suggested)

| Plan | Price | Credits/Month | Features |
|------|-------|---------------|----------|
| **Free** | $0 | 10 videos | Basic crop, 100MB max |
| **Pro** | $9/mo | 200 videos | Batch, webhook, 500MB max |
| **Enterprise** | Custom | Unlimited | Priority, SLA, custom integration |

---

## 9. Security Considerations

### Data Protection
- All videos encrypted at rest (R2 default encryption)
- Signed URLs with 24-hour expiry
- Automatic deletion after 7 days
- No video content logging

### API Security
- Rate limiting: 60 requests/minute
- API key rotation support
- Request signing for webhooks
- CORS restricted to allowed origins

### Compliance
- GDPR: User data deletion on request
- No PII stored in video metadata
- Audit logging for enterprise tier

---

## 10. Success Metrics

### KPIs

| Metric | Target | Measurement |
|--------|--------|-------------|
| Processing success rate | > 99% | jobs_completed / jobs_total |
| Average processing time | < 15s | avg(processing_time_ms) |
| API uptime | 99.9% | Railway monitoring |
| User retention (monthly) | > 40% | returning users / total users |
| Cost per video | < $0.03 | total_costs / videos_processed |

### Launch Goals (30 days)
- [ ] 100 registered users
- [ ] 1,000 videos processed
- [ ] 5 paying customers
- [ ] < 1% error rate

---

## 11. Timeline

### Phase 1: MVP (Week 1-2)
- [ ] FastAPI backend with core endpoints
- [ ] FFmpeg worker with Redis queue
- [ ] Cloudflare R2 integration
- [ ] Basic web UI for upload/download
- [ ] Railway deployment

### Phase 2: Polish (Week 3)
- [ ] User authentication & API keys
- [ ] Usage tracking & rate limiting
- [ ] Webhook notifications
- [ ] Error handling & retries

### Phase 3: Scale (Week 4)
- [ ] Batch processing
- [ ] MediaPoster integration
- [ ] Monitoring & alerting
- [ ] Documentation & API reference

---

## 12. Open Questions

1. **Storage retention:** How long to keep processed videos? (Current: 7 days)
2. **Free tier limits:** 10 videos/month enough to drive conversions?
3. **Sora detection:** Should we auto-detect Sora watermark position vs fixed crop?
4. **Additional platforms:** Support for other AI video generators (Runway, Pika)?

---

## 13. Appendix

### A. FFmpeg Crop Command
```bash
ffmpeg -y -i input.mp4 \
  -vf "crop=in_w:in_h-100:0:0" \
  -c:a copy \
  output.mp4
```

### B. Sample Worker Code
```python
import os
import subprocess
import tempfile
from redis import Redis
from rq import Worker, Queue

redis_conn = Redis.from_url(os.environ["REDIS_URL"])
queue = Queue(connection=redis_conn)

def process_video(job_id: str, input_url: str, crop_pixels: int = 100):
    """Download, crop, upload video."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = f"{tmpdir}/input.mp4"
        output_path = f"{tmpdir}/output.mp4"
        
        # Download
        subprocess.run(["curl", "-o", input_path, input_url], check=True)
        
        # Get dimensions
        probe = subprocess.run([
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0", input_path
        ], capture_output=True, text=True)
        width, height = map(int, probe.stdout.strip().split(','))
        
        # Crop
        crop_height = height - crop_pixels
        subprocess.run([
            "ffmpeg", "-y", "-i", input_path,
            "-vf", f"crop={width}:{crop_height}:0:0",
            "-c:a", "copy", output_path
        ], check=True)
        
        # Upload to R2
        output_url = upload_to_r2(output_path, f"{job_id}_clean.mp4")
        
        return {"output_url": output_url}

if __name__ == "__main__":
    worker = Worker([queue], connection=redis_conn)
    worker.work()
```

### C. Related Documentation
- [Railway Docs](https://docs.railway.app/)
- [Cloudflare R2 API](https://developers.cloudflare.com/r2/)
- [FFmpeg Filtering Guide](https://ffmpeg.org/ffmpeg-filters.html)
