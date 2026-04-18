# PRD 09 — Trend Intelligence Agent

**Backend root:** `/Users/isaiahdupree/Documents/Software/MediaPoster/Backend`

## Owned Files
- `services/trend_detection.py` — Core trend detection engine
- `services/trend_intelligence/` — Trend intelligence subsystem (23 files)
- `services/trend_velocity_service.py` — Trend velocity scoring (rising/falling)
- `services/trend_brief_service.py` — Trend brief generation
- `services/trend_brief_generator.py` — AI-powered brief generator
- `services/trend_flash/` — Real-time trend flash alerts
- `services/trending_keywords_service.py` — Keyword trend tracking
- `services/keyword_extraction_service.py` — Keyword extraction from content
- `services/trend_scoring_service.py` — Trend relevance scoring
- `services/trend_ingestion_service.py` — External trend data ingestion
- `services/trending_content.py` — Trending content discovery
- `services/niche_search_service.py` — Niche-specific search
- `services/trends_agent.py` — Agentic trend monitor
- `api/endpoints/trends_agent.py` — Trends API endpoints

## Features to Build

### F1 — Real-Time Trend Flash Pipeline
Complete the `trend_flash/` pipeline:
1. Monitor TikTok/Twitter/Instagram for keyword velocity spikes every 15min
2. When a keyword grows >200% in 6h, classify as "trend flash"
3. Generate a content brief via `trend_brief_generator.py` within 5min of detection
4. Emit `agent_event` type `trend_flash_detected` with brief + suggested hook
5. Auto-queue a pipeline run via `MasterOrchestrator` with the trend as theme

Add `GET /api/trends/flash` returning active flashes with brief + urgency score.

### F2 — Niche Trend Scoring vs Your Content
Compare detected trends against your existing content library.
Score each trend: `coverage_gap` (0–1) — how underrepresented this trend is in your past content.
High gap + high velocity = highest priority to create.
Add `GET /api/trends/opportunities?min_velocity=2.0&min_gap=0.6` returning ranked opportunities.

### F3 — Keyword → Hook Suggestion
For each trending keyword, use GPT-4o to generate 5 hooks targeting each Schwartz awareness level.
Store in DB as `trend_hooks` table. Refresh weekly.
Add `GET /api/trends/{keyword}/hooks?awareness=2` returning level-specific hook options.

### F4 — Cross-Platform Trend Correlation
Detect when the same trend appears on multiple platforms simultaneously (TikTok + Twitter + Instagram).
Cross-platform trends get a `multiplier` boost to their opportunity score.
Add `platform_spread: int` field to trend records.
Trends with spread >= 3 platforms auto-trigger a content brief.

### F5 — Competitor Trend Adoption Tracker
When a competitor posts content that matches a detected trend within 24h of trend detection,
record it as `competitor_adopted_trend`. Track how quickly each competitor moves on trends.
Add `GET /api/trends/competitor-speed` returning avg time-to-adopt per competitor account.

## Success Criteria
- Trend flash detected and brief generated within 5min of keyword spike
- Opportunity scorer ranks trends by gap × velocity correctly
- Hook suggestions use real GPT-4o calls, 5 per keyword per awareness level
- Cross-platform correlation detects multi-platform trends
- Competitor adoption tracking stores data for all watched accounts
