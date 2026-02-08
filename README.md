# MediaPoster - Modular macOS Social Video Automation System

> Automate the journey from raw iPhone footage to viral social media content with AI-powered analysis, intelligent highlight detection, and multi-platform distribution.

## 🎯 **NEW TO THIS PROJECT?** 
👉 **Start here:** [`START_HERE.md`](./START_HERE.md) - Quick 3-step setup guide  
👉 **Understanding structure:** [`ONBOARDING_GUIDE.md`](./ONBOARDING_GUIDE.md) - Complete navigation guide  
👉 **Project structure:** [`PROJECT_STRUCTURE.md`](./PROJECT_STRUCTURE.md) - Directory map

## 📋 **SCRIPTS & TOOLS INDEX**
👉 **[`SCRIPTS_AND_TOOLS.md`](./SCRIPTS_AND_TOOLS.md)** — Master reference for all publishing, scheduling, automation, and monitoring scripts  
👉 **[`Backend/scripts/SCHEDULING_TOOLS.md`](./Backend/scripts/SCHEDULING_TOOLS.md)** — Detailed scheduling & planning CLI docs with examples

## 🎯 Overview

MediaPoster is a comprehensive automation system that transforms long-form videos from your iPhone into optimized, viral-style short clips and automatically distributes them across multiple social media platforms. Built with modularity and scalability in mind, each component can operate independently or as part of an integrated pipeline.

### Key Features

- 📱 **Automated iPhone Sync**: Seamless video ingestion via iCloud Photos or USB
- 🤖 **AI-Powered Analysis**: GPT-4 Vision, Whisper transcription, and intelligent scene detection
- ✨ **Smart Highlight Detection**: Multi-signal analysis to find the most engaging moments
- 🎬 **Viral Clip Generation**: Automatic captions, hooks, progress bars, and visual enhancements
- 🌐 **Multi-Platform Distribution**: Post to Instagram, TikTok, YouTube, Twitter, and Threads via Blotato
- 📊 **Performance Analytics**: Track engagement, identify winners, auto-delete low-performers
- 🎨 **Watermark Removal**: AI-powered detection and removal with metadata cleaning
- 📈 **Learning Loop**: Tag-based performance optimization and content strategy insights

## 🏗️ Architecture

```
video ingestion → AI analysis → highlight detection → clip generation 
    → cloud staging → multi-platform upload → performance monitoring → data storage
```

Each module is standalone and can be deployed locally on Mac or in the cloud. See `ARCHITECTURE_PLAN.md` for complete technical details.

## 🚀 Quick Start

### Prerequisites

- macOS 12.0+ (Apple Silicon recommended for local AI processing)
- Python 3.10+
- Node.js 18+
- FFmpeg
- PostgreSQL (or Supabase account)
- Redis (for job queue)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd MediaPoster
```

2. **Backend Setup**
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your API keys and settings
```

3. **Database Setup**
```bash
# If using Supabase, run the schema in their SQL editor
# If using local PostgreSQL:
psql -U postgres -d mediaposter -f database/schema.sql
```

4. **Frontend Setup**
```bash
cd dashboard
npm install
npm run dev
```

5. **Start Services**
```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery worker
cd backend
celery -A main worker --loglevel=info

# Terminal 3: Start FastAPI server
uvicorn main:app --reload --port 8000

# Terminal 4: Start Next.js dashboard
cd dashboard
npm run dev
```

Visit http://localhost:3000 for the dashboard and http://localhost:8000/docs for API documentation.

## 📁 Project Structure

```
MediaPoster/
├── README.md                   # This file
├── ARCHITECTURE_PLAN.md        # Detailed system design
├── PROGRESS.md                 # Implementation status
├── VideoPackaging4/            # Existing Python video processor (integrated)
├── dashboard/                  # Next.js frontend
│   ├── src/
│   │   ├── app/               # Next.js 15 App Router
│   │   ├── components/        # React components
│   │   └── lib/               # Utilities and API clients
│   └── package.json
└── backend/
    ├── requirements.txt
    ├── .env.example
    ├── config.py              # Application settings
    ├── main.py                # FastAPI application
    ├── modules/               # Core processing modules
    │   ├── video_ingestion/   # iPhone sync and video detection
    │   ├── ai_analysis/       # Whisper, GPT-4 Vision, frame extraction
    │   ├── highlight_detection/ # Multi-signal moment ranking
    │   ├── clip_generation/   # FFmpeg editing and viral enhancements
    │   ├── cloud_staging/     # Google Drive integration
    │   ├── blotato_uploader/  # Multi-platform posting
    │   ├── content_monitor/   # Performance tracking
    │   └── watermark_remover/ # AI-powered watermark removal
    ├── api/                   # FastAPI endpoints
    ├── database/
    │   ├── schema.sql         # Supabase/PostgreSQL schema
    │   ├── models.py          # SQLAlchemy ORM models
    │   └── connection.py      # Database utilities
    ├── utils/                 # Helper functions
    └── services/              # External API integrations
```

## 🔧 Configuration

All configuration is managed through environment variables. Copy `.env.example` to `.env` and fill in your credentials:

### Required API Keys

- **OpenAI API Key**: For Whisper transcription and GPT-4 Vision analysis
- **Blotato API Key**: For multi-platform social media posting
- **Google Drive Credentials**: For cloud staging
- **Supabase URL & Key**: For database and storage

### Optional Services

- **Anthropic API Key**: Alternative LLM provider
- **YouTube Data API**: For direct performance metrics
- **Instagram Graph API**: For business account insights
- **Sentry DSN**: For error tracking

See `.env.example` for all available options.

## 📚 Module Documentation

### 1. Video Ingestion
Monitors iCloud Photos or USB connections to automatically import new videos from iPhone.

### 2. AI Analysis
- **Frame Extraction**: FFmpeg-based scene detection
- **Transcription**: OpenAI Whisper for accurate speech-to-text
- **Visual Analysis**: GPT-4 Vision for frame content descriptions
- **Multimodal Synthesis**: Combines visual and audio data

### 3. Highlight Detection
Uses multiple signals to identify engaging moments:
- Scene changes and camera cuts
- Audio peaks and speaker emphasis
- Key phrases in transcript
- Visual salience (unusual visuals, text overlays)

### 4. Clip Generation
Creates viral-optimized short clips with:
- Auto captions (Whisper-synced subtitles)
- Catchy text hooks (GPT-4 generated)
- Progress bars and emoji overlays
- Aspect ratio conversion (9:16 for mobile)
- Branding and CTAs

### 5. Cloud Staging
Uploads clips to Google Drive and generates direct download URLs for Blotato integration.

### 6. Blotato Integration
Unified API for posting to:
- Instagram (Feed, Reels, Stories)
- TikTok
- YouTube (Shorts)
- Twitter
- Threads

### 7. Content Monitor
- Checks post status after configurable delay
- Collects performance metrics (views, likes, engagement)
- Auto-deletes low-performers based on thresholds
- Schedules follow-up checkbacks (1hr, 24hr, 7day)

### 8. Watermark Removal
- AI-powered watermark detection
- Inpainting-based removal
- Metadata cleaning
- Quality validation

### 9. Data Storage
Supabase PostgreSQL database with:
- Video and clip metadata
- Performance metrics time-series
- Content tags for optimization
- Processing job queue
- AI service usage logs

## 🎨 Dashboard Features

The Next.js dashboard provides:

- **Video Library**: Browse uploaded videos and their generated clips
- **Processing Pipeline**: Real-time status of each module
- **Analytics Dashboard**: Performance insights by hook type, platform, and keyword
- **Content Management**: Approve/reject highlights, edit captions
- **Settings**: Configure processing parameters and thresholds
- **Job Monitor**: Track background tasks and errors

## 🧪 Testing

```bash
# Run backend tests
cd backend
pytest tests/ -v --cov

# Run frontend tests
cd dashboard
npm test
```

## 🚢 Deployment

### Local Deployment (Recommended for Development)
All processing happens on your Mac. Requires Apple Silicon for efficient local AI processing.

### Cloud-Assisted Deployment
- Mac handles video ingestion and orchestration
- Cloud services (OpenAI API, Azure) handle AI analysis
- Reduces local compute requirements

### Hybrid Deployment
- Critical path on Mac for low latency
- Heavy processing offloaded to cloud
- Best for scaling to multiple channels

See `ARCHITECTURE_PLAN.md` for detailed deployment strategies.

## 📊 Performance Optimization

The system tracks content performance and learns over time:

- **Tag-based Analysis**: Hook types, keywords, visual elements
- **A/B Testing**: Compare variations automatically
- **Platform-specific Insights**: What works best where
- **Viral Pattern Detection**: Identify common traits of high performers

Query examples:
```sql
-- Best performing hook types by platform
SELECT * FROM best_clips_by_hook_type;

-- Clips with >1000 views in first hour
SELECT * FROM clip_performance_summary 
WHERE minutes_after_post < 60 AND views > 1000;
```

## 🔐 Security

- API keys stored in environment variables or macOS Keychain
- Supabase Row Level Security (RLS) enabled
- Google Drive folder access restricted
- No credentials in code or version control

## 🛠️ Development

### Adding a New Module

1. Create module directory: `backend/modules/my_module/`
2. Implement core logic in `processor.py`
3. Add API endpoint in `backend/api/endpoints/`
4. Register Celery task in `main.py`
5. Add tests in `tests/modules/test_my_module.py`
6. Update documentation

### Code Style

- Backend: Black formatter, flake8 linter, mypy type checking
- Frontend: ESLint, Prettier
- Commit messages: Conventional Commits format

## 📖 Additional Documentation

- **Architecture Plan**: See `ARCHITECTURE_PLAN.md` for complete system design
- **Progress Tracking**: See `PROGRESS.md` for implementation status
- **API Documentation**: Visit `/docs` when running the FastAPI server
- **VideoPackaging4 Docs**: See `VideoPackaging4/README.md` for legacy system details

## 🤝 Contributing

This is a personal project, but suggestions and improvements are welcome! Please open an issue to discuss major changes.

## 📝 License

[Your License Here]

## 🙏 Acknowledgments

- OpenAI for Whisper and GPT-4 Vision
- Blotato for multi-platform posting API
- FFmpeg for video processing
- Supabase for backend infrastructure
- The open-source community for countless tools and libraries

## 📞 Support

For questions or issues:
- Open a GitHub issue
- Check documentation in `ARCHITECTURE_PLAN.md`
- Review existing VideoPackaging4 code for examples

---

**Built with ❤️ for content creators who want to automate the boring parts and focus on creating amazing content.**
