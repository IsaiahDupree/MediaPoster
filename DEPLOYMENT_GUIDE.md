# Deployment Guide - MediaPoster

## Architecture Overview

**Frontend (Next.js)** → Vercel ✅ Perfect match!
**Backend (Python FastAPI)** → Separate hosting (multiple options)

## Option 1: Vercel + Railway (Recommended)

### Frontend on Vercel
```bash
cd dashboard

# Deploy to Vercel
npm install -g vercel
vercel login
vercel deploy --prod
```

### Backend on Railway
Railway is perfect for Python backends with background jobs:

1. **Create Railway Account**: https://railway.app
2. **Connect GitHub repo**
3. **Add services**:
   - Python backend (FastAPI)
   - PostgreSQL (or use Supabase)
   - Redis (for Celery)

**`railway.json`** (create in backend/):
```json
{
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "pip install -r requirements.txt"
  },
  "deploy": {
    "startCommand": "uvicorn main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**Cost**: ~$20/month for backend with Redis

---

## Option 2: Vercel + DigitalOcean

### Frontend on Vercel (same as above)

### Backend on DigitalOcean App Platform

1. **Create DigitalOcean account**
2. **Create App from GitHub**
3. **Configure**:
   - Runtime: Python
   - Run command: `uvicorn main:app --host 0.0.0.0 --port 8080`
   - Add PostgreSQL + Redis databases

**Cost**: ~$25/month

---

## Option 3: Vercel + AWS (Production Scale)

### Frontend on Vercel

### Backend on AWS
- **EC2** for FastAPI server
- **RDS** for PostgreSQL  
- **ElastiCache** for Redis
- **S3** for video storage
- **Lambda** for AI processing (optional offload)

**Cost**: ~$50-100/month (scales up)

---

## Option 4: All-in-One Vercel (Serverless Functions)

⚠️ **Limitations**: Vercel serverless functions have:
- 10s execution limit (Hobby)
- 60s execution limit (Pro)
- Not ideal for video processing
- No background jobs (Celery)

**Use this ONLY if**:
- Backend is just an API gateway
- Heavy processing happens on external services
- No long-running tasks

### Setup
1. Convert FastAPI routes to API routes in Next.js
2. Move logic to `/dashboard/app/api/`
3. Use external services for:
   - Video processing → Cloud Run / Lambda
   - AI analysis → OpenAI API directly
   - Job queue → Inngest or QStash

---

## Recommended: Hybrid Architecture (Best of Both)

### What Goes Where

**Vercel (Next.js Frontend)**
- Dashboard UI
- Real-time updates (WebSocket via Supabase)
- Client-side video upload to Supabase Storage
- API calls to backend

**Railway/DigitalOcean (Python Backend)**
- Video ingestion monitoring
- FFmpeg processing
- AI analysis orchestration
- Celery job queue
- Blotato API integration

**Supabase (Shared)**
- PostgreSQL database
- File storage (videos, thumbnails)
- Real-time subscriptions
- Authentication

### Benefits
✅ Frontend instantly deployed on Vercel's edge network
✅ Backend has full Python/FFmpeg capabilities
✅ Shared database for real-time sync
✅ Cost-effective (~$20-30/month total)

---

## Deployment Steps: Vercel + Railway

### 1. Deploy Supabase Database

```bash
# Already have schema.sql ready
# 1. Go to supabase.com
# 2. Create project
# 3. Run backend/database/schema.sql in SQL Editor
# 4. Copy project URL and anon key
```

### 2. Deploy Backend to Railway

```bash
cd backend

# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize
railway init

# Add services
railway add # Select PostgreSQL (or skip if using Supabase)
railway add # Select Redis

# Set environment variables
railway variables set BLOTATO_API_KEY=blt_nRMU7mx13OAGEFEs8NVZ/cv6ThhEeZ/VcozFFq4f6to=
railway variables set OPENAI_API_KEY=your_key
railway variables set SUPABASE_URL=your_url
railway variables set SUPABASE_KEY=your_key

# Deploy
railway up
```

### 3. Deploy Frontend to Vercel

```bash
cd dashboard

# Set environment variables
# Create .env.local:
echo "NEXT_PUBLIC_API_URL=https://your-railway-url.up.railway.app" > .env.local
echo "NEXT_PUBLIC_SUPABASE_URL=your_url" >> .env.local
echo "NEXT_PUBLIC_SUPABASE_ANON_KEY=your_key" >> .env.local

# Deploy
vercel deploy --prod
```

### 4. Configure Domain (Optional)

**Vercel**:
- Dashboard: `mediaposter.com`
- Auto SSL certificate

**Railway**:
- API: `api.mediaposter.com`
- Point CNAME to Railway URL

---

## Environment Variables

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=https://api.mediaposter.com
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
```

### Backend (Railway/DigitalOcean)
```bash
# API Keys (from .env)
BLOTATO_API_KEY=blt_nRMU7mx13OAGEFEs8NVZ/cv6ThhEeZ/VcozFFq4f6to=
OPENAI_API_KEY=your_key
SUPABASE_URL=your_url
SUPABASE_KEY=your_key

# Database
DATABASE_URL=postgresql://...  # Auto-provided by Railway/DO
REDIS_URL=redis://...          # Auto-provided

# Application
APP_ENV=production
DEBUG=false
FRONTEND_URL=https://mediaposter.com
```

---

## Cost Comparison

| Solution | Frontend | Backend | Database | Redis | Total/mo |
|----------|----------|---------|----------|-------|----------|
| **Vercel + Railway** | Free/$20 | $5 | Free (Supabase) | $5 | **$10-30** |
| **Vercel + DigitalOcean** | Free/$20 | $12 | $15 | $15 | **$42-62** |
| **Vercel + AWS** | Free/$20 | $20+ | $15+ | $15+ | **$50-100+** |
| **All Vercel Serverless** | $20 | N/A | Free (Supabase) | N/A | **$20** ⚠️ Limited |

**Recommendation**: Start with **Vercel + Railway** (~$10-30/month)

---

## Development vs Production

### Development (Local)
```bash
# Terminal 1: Frontend
cd dashboard
npm run dev  # localhost:3000

# Terminal 2: Backend
cd backend
source venv/bin/activate
uvicorn main:app --reload  # localhost:8000

# Terminal 3: Redis
redis-server

# Terminal 4: Celery
celery -A main worker
```

### Production
- Frontend: Vercel edge network (global CDN)
- Backend: Railway/DO (single region, close to you)
- Database: Supabase (multi-region)

---

## Video Processing Consideration

**Important**: Video processing is CPU-intensive and may need:

1. **Dedicated server** for FFmpeg operations
2. **Cloud Functions** for parallel processing:
   - AWS Lambda with EFS for FFmpeg
   - Google Cloud Run (up to 60min timeout)
   - Modal Labs (GPU support for AI)

3. **Hybrid approach**:
   - Light API on Railway/Vercel
   - Heavy processing on separate workers

---

## CI/CD Pipeline

### GitHub Actions for Auto-Deploy

**`.github/workflows/deploy.yml`**:
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: amondnet/vercel-action@v20
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./dashboard

  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: berviantoleo/railway-deploy@v1
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: backend
```

---

## Monitoring & Observability

### Frontend (Vercel)
- Built-in analytics
- Real-time logs
- Performance metrics

### Backend
- **Sentry** for error tracking
- **Loguru** for structured logging  
- **Railway dashboard** for metrics

### Database (Supabase)
- Query performance dashboard
- Real-time connections
- Storage usage

---

## Scaling Strategy

### Phase 1: MVP (Current)
- Vercel frontend (free tier)
- Railway backend ($5-10)
- Supabase free tier
**Total: ~$10/month**

### Phase 2: Growing (~100 users)
- Vercel Pro ($20)
- Railway hobby ($20)
- Supabase Pro ($25)
**Total: ~$65/month**

### Phase 3: Scale (~1000 users)
- Vercel Pro
- DigitalOcean dedicated server ($50)
- Supabase Pro with larger DB
- Separate video processing workers
**Total: ~$150-200/month**

---

## Quick Start: Deploy Now

### 1-Click Vercel Deploy (Frontend)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/yourusername/MediaPoster/tree/main/dashboard)

### Railway Deploy (Backend)

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template)

---

## Summary

**✅ YES, use Next.js (we already are!)**

**Best Deployment**: 
1. **Frontend**: Vercel (instant, free/cheap, global CDN)
2. **Backend**: Railway or DigitalOcean ($10-25/mo)
3. **Database**: Supabase (free tier generous)

**Avoid**: Trying to run Python backend on Vercel serverless (too limited)

**Start**: Deploy frontend to Vercel today (takes 2 minutes), backend when ready.

---

## Next Steps

1. ✅ Frontend is Next.js (perfect for Vercel)
2. Create Railway account
3. Add `railway.json` to backend
4. Set environment variables
5. Deploy with `railway up`
6. Connect frontend to backend URL
7. Done!

Questions? The Next.js frontend is already optimized for Vercel. Just run `vercel deploy`!
