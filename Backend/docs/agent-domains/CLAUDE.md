# MediaPoster — Claude Code Agent System Prompt

You are a Claude Code agent working on the MediaPoster backend.
Read this file fully before touching any code.

## Project Structure
- **Backend root:** `/Users/isaiahdupree/Documents/Software/MediaPoster/Backend`
- **Backend API:** `http://localhost:5555`
- **Frontend Dashboard:** `http://localhost:5557`
- **Database (local):** `postgresql://postgres:postgres@127.0.0.1:54322/postgres`

---

## CRITICAL RULES — Never Violate These

### 1. Never Skip Pipeline Steps
If a step cannot be completed, it MUST FAIL with a descriptive error. Never add silent skip logic.
```python
# WRONG
if not can_transcribe:
    logger.info("Skipping transcription")
    return None

# RIGHT
if not can_transcribe:
    raise ValueError(f"Cannot transcribe {file_path}: audio stream not found")
```

### 2. Never Run `supabase db reset`
This wipes $10+ of irreplaceable AI analysis data (7,450 files with transcriptions, scores, thumbnails).
- Use `supabase db push` to apply migrations
- Always backup first: `pg_dump postgresql://postgres:postgres@127.0.0.1:54322/postgres > backup.sql`

### 3. Never Revert Files to Simpler Versions
Never use `git checkout` to revert files. Fix specific errors with targeted edits only.

### 4. Always Use Real AI API Calls
All AI features must use real OpenAI/Groq API calls. No hardcoded templates, no mock responses.
The owner explicitly does not care about API credit cost.

### 5. Never Hardcode Account IDs or Paths
- Use `config/blotato_accounts.py` for all Blotato account references
- Use `config/paths.py` for all file paths (especially iPhone import / external drive)
- iPhone import: `/Volumes/My Passport/MediaPoster/workspace1/iphone_import` (fallback: `~/Documents/IphoneImport`)

---

## AI Model Configuration
Configured in `config/model_registry.py`. Use `TaskType` enum, never hardcode model names.

| Task | Provider | Model |
|------|----------|-------|
| Transcription | Groq | whisper-large-v3 |
| Content Analysis | Groq | llama-3.3-70b-versatile |
| Frame Analysis | OpenAI | gpt-4o-mini |
| Vision Analysis | OpenAI | gpt-4o |
| Hook/ICP/Strategy | OpenAI | gpt-4o |

---

## Platform Accounts (22 Blotato accounts)
Full mapping in `config/blotato_accounts.py`.

| Platform | Account IDs |
|----------|-------------|
| TikTok | 710 (@isaiah_dupree), 243 (@the_isaiah_dupree), 4508 (@dupree_isaiah), 571 (@soursides_is_sour) |
| Instagram | 807, 670, 1369, 4508 |
| YouTube | 228 (Isaiah Dupree), 3370 (lofi_creator) |
| Twitter | 4151 (@IsaiahDupree7) |
| Threads | 173, 201, 1369, 4150 |
| Pinterest | 173, 243 |
| LinkedIn | 571 |
| Facebook | 786 |
| Bluesky | 201 |

---

## RapidAPI — Working Endpoints Only

### Instagram (instagram-looter2.p.rapidapi.com)
- `/v1/info` ✅ `/v1/posts` ✅ `/profile` ✅ `/post` ✅
- `/v1/reels` ❌ 404 — does NOT exist, use `/v1/posts` and filter video content

### TikTok (tiktok-scraper7.p.rapidapi.com)
- `/user/posts` ✅

### Instagram Stats (instagram-statistics-api.p.rapidapi.com)
- `/community` ✅ `/posts` ✅

---

## Safari Automation
- Requires: Safari > Develop > Allow Remote Automation enabled
- Session refresh intervals: Twitter 25min, TikTok 20min, Instagram 25min, Sora 30min, YouTube 45min
- Twitter encryption code if prompted: `7911`
- All automation dispatches through `services/safari_queue_manager.py` — never direct execution
- Screenshot every action to `automation/screenshots/{platform}/{action}/{timestamp}.png`

## Rate Limits (Safari automation)
- TikTok: 50 comments/day, 20 DMs/day
- Instagram: 30 comments/day, 10 DMs/day
- Twitter: 500 tweets/day

---

## Content Intelligence Framework

### FATE Persuasion Scoring (Chase Hughes SRS #253)
- **F** — Focus: pattern interrupts, curiosity gaps, stakes
- **A** — Authority: numbers, proof, mechanism
- **T** — Tribe: identity markers, us-vs-them
- **E** — Emotion: story beats, contrast, loss aversion, hope
- Score range: 0.0 – 1.0 per dimension
- Scorer: `services/fate_scorer.py`

### Eugene Schwartz 5 Levels of Awareness
- 1: Unaware → pure story, no mention of problem
- 2: Problem-aware → name/amplify the pain
- 3: Solution-aware → show a method exists
- 4: Product-aware → why this solution specifically
- 5: Most-aware → just make the offer
- Classifier: `services/awareness_classifier.py`

### Awareness → Platform Routing
- Levels 1-2 (cold): TikTok + Instagram Reels
- Level 3 (educate): YouTube + Twitter threads
- Levels 4-5 (convert): LinkedIn + DM

---

## Key Data Paths
- Competitor research: `/Users/isaiahdupree/Documents/CompetitorResearch/accounts/{username}/`
- iPhone import (primary): `/Volumes/My Passport/MediaPoster/workspace1/iphone_import`
- RapidAPI media: `/Volumes/My Passport/MediaPoster/rapidapi_media`

---

## Sora Video Generation
- URL: `https://sora.chatgpt.com/explore`
- Usage check: click Settings → Usage tab → `[id*="-trigger-usage"]`
- Automation: `automation/sora_full_automation.py`
- ALWAYS check quota before generating. If 0 remaining, emit `agent_event` type `sora_quota_exhausted` and raise — never skip.

---

## Database Rules
- Migrations: write SQL file to `migrations/` directory, apply with `supabase db push`
- Never use `supabase db reset` — ever
- All schema changes through migration files, never ad-hoc ALTER TABLE in scripts
- After any DDL change, check `GET /api/advisors/security` and `GET /api/advisors/performance`

---

## Testing
- Run tests before and after changes: `pytest tests/ -v`
- Test files in `tests/unit/` and `tests/integration/`
- Never delete or weaken tests
- Add regression tests for every bug fixed
