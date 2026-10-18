# Recent Scripts & Integration Opportunities Report

**Generated:** December 26, 2025  
**Period:** Last 7 days

---

## Summary

This report catalogs recently created scripts and APIs, assessing their integration potential into the MediaPoster platform.

---

## 1. iOS Import API (`api/endpoints/ios_import_api.py`)

**Created:** Dec 26, 2025  
**Purpose:** Import media from iOS devices with smart duplicate detection

### Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/import/ios/device` | GET | Check iOS device connection |
| `/api/import/ios/stats` | GET | Get import statistics |
| `/api/import/ios/scan` | POST | Scan directory for files |
| `/api/import/ios/start` | POST | Start import job |
| `/api/import/ios/job/{id}/pause` | POST | Pause job |
| `/api/import/ios/job/{id}/resume` | POST | Resume job |
| `/api/import/ios/job/{id}/cancel` | POST | Cancel job |
| `/api/import/ios/history` | GET/DELETE | View/clear import history |

### Integration Recommendation: ✅ **HIGH PRIORITY**
- Already integrated into dashboard at `/import/ios`
- **Next Steps:** Connect to media library service to auto-add imported files
- **Benefit:** Streamlines iPhone → MediaPoster content pipeline

---

## 2. RapidAPI Endpoint Scraper (`scripts/scrape_rapidapi_endpoints.py`)

**Created:** Dec 26, 2025  
**Purpose:** Automate discovery of RapidAPI endpoint URLs using Safari

### Features
- Safari automation via AppleScript
- Extracts endpoint paths, parameters, and curl commands
- Generates JSON and Markdown documentation

### Integration Recommendation: ⚙️ **UTILITY TOOL**
- Standalone script for API discovery
- **Use Case:** When adding new RapidAPI integrations, run this to document endpoints
- **Not for production integration** - developer tool only

---

## 3. Competitor Video Downloader (`scripts/download_competitor_videos.py`)

**Created:** Dec 26, 2025  
**Purpose:** Download competitor Instagram videos for research

### Features
- Downloads from manifest file
- Skips existing videos (no duplicates)
- Organizes by username

### Integration Recommendation: ✅ **MEDIUM PRIORITY**
- **Integrate with:** `competitor_sync_scheduler.py`
- **Benefit:** Automated competitor content collection
- **Next Steps:** Add to scheduler as daily/weekly job

---

## 4. Safari Instagram Scraper (`automation/safari_instagram_scraper.py`)

**Created:** Dec 26, 2025  
**Purpose:** Scrape Instagram reels URLs via Safari automation

### Features
- Opens Safari and navigates to Instagram
- Scrolls and collects reel URLs without clicking
- Exports to manifest for batch download

### Integration Recommendation: ✅ **HIGH PRIORITY**
- **Integrate with:** Competitor research service
- **Benefit:** Collect competitor content without API limits
- **Next Steps:** 
  1. Add endpoint to trigger scraper
  2. Connect output to download_competitor_videos.py
  3. Add to automation scheduler

---

## 5. Voice Training Scripts

### 5.1 `scripts/identify_best_voice_training_videos.py`
**Purpose:** Find best videos for AI voice cloning training

### 5.2 `scripts/find_and_combine_voice_training_data.py`
**Purpose:** Combine audio segments for voice training

### 5.3 `scripts/extract_combined_audio.py`
**Purpose:** Extract audio from videos for voice training

### 5.4 `scripts/run_voice_quality_assessment.py`
**Purpose:** Assess audio quality for voice cloning

### Integration Recommendation: ⚙️ **SPECIALIZED FEATURE**
- These support the Voice Cloning Quality service
- **Integrate with:** `services/voice_cloning_quality_assessor.py`
- **Endpoint exists:** `/api/voice-cloning-quality/*`
- **Next Steps:** Add dashboard UI for voice training workflow

---

## 6. API Usage Tracker Updates (`services/api_usage_tracker.py`)

**Updated:** Dec 26, 2025  
**Changes:** Added Instagram Scraper Stable API

### New Provider
```python
APIProvider.RAPIDAPI_INSTAGRAM_STABLE
```

### Integration Status: ✅ **INTEGRATED**
- Dashboard shows at `/api-usage`
- Tracks calls, budgets, rate limits
- **Next Steps:** Connect to audio service for actual usage tracking

---

## 7. Instagram Scraper Stable Adapter (`services/instagram/adapters/instagram_stable_adapter.py`)

**Updated:** Dec 26, 2025  
**Changes:** Updated to use correct endpoint format

### Key Endpoints Documented
- `POST /get_ig_user_reels.php` - User reels (metadata only)
- `POST /get_ig_user_posts.php` - User posts
- `POST /get_ig_account_data.php` - Profile data
- `GET /get_media_data_v2.php` - Detailed media

### Integration Status: ⚠️ **PARTIAL**
- Adapter works for metadata
- **Limitation:** API doesn't return video/audio download URLs
- **Next Steps:** Find alternative API for actual media downloads

---

## 8. Trending Keywords Service (`services/trending_keywords_service.py`)

**Created:** Dec 26, 2025  
**Purpose:** Extract trending keywords, hooks, and CTAs from competitor content

### Integration Recommendation: ✅ **HIGH PRIORITY**
- **Integrate with:** Trends API, Narrative Builder
- **Benefit:** AI-powered trend discovery from real competitor content
- **Next Steps:**
  1. Add endpoint at `/api/trends/keywords`
  2. Connect to competitor video transcripts
  3. Surface in dashboard IG Trends page

---

## Integration Priority Matrix

| Script/Service | Priority | Effort | Impact | Status |
|---------------|----------|--------|--------|--------|
| iOS Import API | HIGH | Done | High | ✅ Integrated |
| Safari IG Scraper | HIGH | Medium | High | 🔄 Needs endpoint |
| Trending Keywords | HIGH | Low | High | 🔄 Needs endpoint |
| Competitor Downloader | MEDIUM | Low | Medium | 🔄 Needs scheduler |
| Voice Training Suite | LOW | High | Medium | ⚙️ Specialized |
| RapidAPI Scraper | UTILITY | Done | Low | ⚙️ Dev tool |

---

## Recommended Next Steps

1. **Add `/api/trends/keywords` endpoint** - Connect trending_keywords_service to API
2. **Schedule competitor sync** - Add Safari scraper + downloader to automation
3. **Voice Training UI** - Build dashboard page for voice cloning workflow
4. **Fix Git History** - Remove venv311 from history to enable push:
   ```bash
   git filter-branch --force --index-filter \
     'git rm -r --cached --ignore-unmatch Backend/venv311/' \
     --prune-empty -- --all
   ```

---

## Files Created This Session

| File | Type | Lines |
|------|------|-------|
| `api/endpoints/ios_import_api.py` | API | 350 |
| `scripts/scrape_rapidapi_endpoints.py` | Script | 180 |
| `docs/rapidapi/instagram-scraper-stable-api-endpoints.md` | Docs | 150 |
| `docs/rapidapi/instagram-scraper-stable-api-endpoints.json` | Data | 200 |
| `dashboard/app/(dashboard)/import/page.tsx` | UI | 110 |

**Total new code:** ~990 lines
