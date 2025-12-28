# Recent Developments - MediaPoster

**Last Updated:** December 27, 2025

This document covers all recent feature developments, API endpoints, and system improvements.

---

## Table of Contents

1. [Analysis Health System](#1-analysis-health-system)
2. [Duplicate Detection System](#2-duplicate-detection-system)
3. [Posted Content Matcher](#3-posted-content-matcher)
4. [B-Roll + Text Format System](#4-b-roll--text-format-system)
5. [Formats API](#5-formats-api)
6. [Video Renderer Comparison](#6-video-renderer-comparison)
7. [Integration Tests](#7-integration-tests)

---

## 1. Analysis Health System

### Purpose
Detects videos with incomplete or failed analysis and enables re-analysis to ensure all videos have complete metadata.

### Files
- **Service:** `Backend/services/analysis_health.py`
- **API:** `Backend/api/endpoints/analysis_health.py`

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/analysis-health/status` | Get overall health status |
| GET | `/api/analysis-health/scan-incomplete` | Scan all videos for incomplete analysis |
| POST | `/api/analysis-health/mark-for-reanalysis` | Mark specific videos for re-analysis |
| POST | `/api/analysis-health/mark-incomplete-for-reanalysis` | Auto-mark all incomplete videos |
| POST | `/api/analysis-health/skip-images` | Mark image files as skipped |
| POST | `/api/analysis-health/clear-and-retry/{video_id}` | Clear and retry single video |
| GET | `/api/analysis-health/videos-needing-reanalysis` | List videos needing re-analysis |

### Key Features

1. **File Type Detection**
   - Automatically identifies video vs image files
   - Skips images (PNG, JPG, HEIC) from video analysis queue

2. **Incomplete Analysis Detection**
   - Checks for missing: transcript, visual_analysis, audio_analysis, ai_score
   - Categorizes: complete, incomplete, not_started, images_skipped

3. **Re-analysis Workflow**
   ```bash
   # Scan for incomplete
   curl "http://localhost:5555/api/analysis-health/scan-incomplete"
   
   # Mark incomplete for reanalysis
   curl -X POST "http://localhost:5555/api/analysis-health/mark-incomplete-for-reanalysis"
   
   # Run batch analysis
   curl -X POST "http://localhost:5555/api/media-db/batch/analyze" -d '{"limit": 100}'
   ```

### Data Model

```python
@dataclass
class AnalysisHealthStatus:
    video_id: str
    filename: str
    file_extension: str
    is_video: bool
    is_image: bool
    has_transcript: bool
    has_visual_analysis: bool
    has_audio_analysis: bool
    has_ai_score: bool
    analysis_status: str  # 'complete', 'incomplete', 'failed', 'not_started'
    missing_components: List[str]
    recommendation: str
```

---

## 2. Duplicate Detection System

### Purpose
Finds videos with similar transcripts to identify duplicates for cleanup/deletion, preventing storage waste and duplicate posting.

### Files
- **Service:** `Backend/services/duplicate_detector.py`
- **API:** `Backend/api/endpoints/duplicate_detection.py`

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/duplicates/find` | Find duplicates with configurable threshold |
| GET | `/api/duplicates/exact` | Find exact matches (99%+ similarity) |
| GET | `/api/duplicates/summary` | Get duplicate summary stats |
| POST | `/api/duplicates/mark-for-deletion` | Mark videos for deletion |
| GET | `/api/duplicates/marked-for-deletion` | List marked videos |
| DELETE | `/api/duplicates/execute-deletion` | Execute deletion |

### Key Features

1. **Transcript Similarity**
   - Uses SequenceMatcher for similarity calculation
   - Configurable threshold (default 85%)
   - Normalizes text for accurate comparison

2. **Caption Status Protection**
   - By default, only compares videos with same caption status
   - Prevents false positives between captioned and non-captioned versions

3. **Smart Recommendations**
   ```
   - If one has captions → keep the one WITH captions
   - If same caption status → keep the longer video
   - Otherwise → manual review
   ```

### Usage

```bash
# Find duplicates (80%+ similarity)
curl "http://localhost:5555/api/duplicates/find?similarity_threshold=0.80"

# Get summary
curl "http://localhost:5555/api/duplicates/summary"

# Mark for deletion
curl -X POST "http://localhost:5555/api/duplicates/mark-for-deletion" \
  -H "Content-Type: application/json" \
  -d '{"video_ids": ["uuid1", "uuid2"]}'
```

### Data Model

```python
@dataclass
class DuplicatePair:
    video1_id: str
    video1_filename: str
    video1_has_captions: bool
    video2_id: str
    video2_filename: str
    video2_has_captions: bool
    similarity_score: float
    transcript_preview: str
    recommendation: str  # "keep_with_captions", "keep_longer", "review_manually"
```

---

## 3. Posted Content Matcher

### Purpose
Scrapes posted content from social platforms and cross-references with local library to prevent posting duplicate content.

### Files
- **Service:** `Backend/services/posted_content_matcher.py`
- **API:** `Backend/api/endpoints/posted_content_matcher.py`

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/posted-matcher/scrape-and-match` | Scrape platform + match with library |
| POST | `/api/posted-matcher/match-transcript` | Match single transcript to library |
| POST | `/api/posted-matcher/mark-as-posted` | Mark video as already posted |
| GET | `/api/posted-matcher/already-posted` | List videos marked as posted |
| GET | `/api/posted-matcher/check-before-post/{video_id}` | Safety check before posting |
| GET | `/api/posted-matcher/cross-reference-summary` | Summary stats |

### Key Features

1. **Safari Automation**
   - Uses AppleScript to control Safari
   - Scrapes video URLs from TikTok and Instagram profiles
   - Handles login prompts manually

2. **Transcript Matching**
   - Cross-references posted video transcripts with local library
   - Returns similarity scores and match confidence

3. **Already Posted Tracking**
   - Marks local videos as "already_posted"
   - Stores platform and URL in visual_analysis JSON
   - Prevents re-posting same content

### Usage

```bash
# Scrape TikTok profile
curl -X POST "http://localhost:5555/api/posted-matcher/scrape-and-match" \
  -H "Content-Type: application/json" \
  -d '{"platform": "tiktok", "username": "isaiah_dupree", "max_videos": 50}'

# Check before posting
curl "http://localhost:5555/api/posted-matcher/check-before-post/{video_id}"

# Get summary
curl "http://localhost:5555/api/posted-matcher/cross-reference-summary"
```

### Supported Platforms
- **TikTok:** @isaiah_dupree, @the_isaiah_dupree, @dupree_isaiah, @soursides_is_sour
- **Instagram:** @the_isaiah_dupree, @the_isaiah_dupree_, @dupree_isaiah_, @dupree_isaiah

---

## 4. B-Roll + Text Format System

### Purpose
Detects videos suitable for text overlay (b-roll footage) and provides tools to add text and background music.

### Files
- **Classifier:** `Backend/services/format_classifier.py`
- **Discovery API:** `Backend/api/endpoints/format_discovery.py`
- **Sample Formats:** `Backend/services/formats/sample_formats.py`

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/format-discovery/broll-candidates` | Find b-roll candidates |
| GET | `/api/format-discovery/classify/{media_id}` | Classify single video |
| POST | `/api/format-discovery/run-format/{format_id}` | Run format on candidates |

### Video Format Types

| Format | Description | Use Case |
|--------|-------------|----------|
| `broll_text` | Person visible, NOT talking | Add motivational quotes |
| `pure_broll` | No person, no speech | Cinematic text overlays |
| `talking_head` | Person visible AND talking | Standard video content |
| `voiceover` | Speech but no visible person | Documentary style |
| `music_only` | Music background only | Mood/atmosphere clips |

### Classification Logic

```python
# B-Roll + Text Candidate
if significant_face and not has_speech:
    format = BROLL_TEXT_CANDIDATE
    reasons = ["Person visible", "No speech detected - ideal for text overlay"]

# Pure B-Roll
if not has_face and not has_speech:
    format = PURE_BROLL
    reasons = ["No person detected", "Ideal for adding text overlays"]
```

### Usage

```bash
# Find B-Roll candidates
curl "http://localhost:5555/api/format-discovery/broll-candidates?limit=20"

# Response:
{
  "total_found": 30,
  "broll_text_candidates": [...],
  "pure_broll_candidates": [
    {
      "media_id": "uuid",
      "filename": "TABL2182.MOV",
      "format_type": "pure_broll",
      "confidence": 0.68,
      "reasons": ["No person detected", "Ideal for adding text overlays"]
    }
  ]
}
```

---

## 5. Formats API

### Purpose
Manage video format templates for automated content generation.

### Files
- **API:** `Backend/api/endpoints/formats_api.py`
- **Sample Formats:** `Backend/services/formats/sample_formats.py`

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/formats/list` | List all formats |
| POST | `/api/formats/seed-samples` | Seed sample formats |
| GET | `/api/formats/{format_id}` | Get single format |
| POST | `/api/formats/{format_id}/run` | Trigger format run |
| GET | `/api/formats/{format_id}/runs` | List format runs |
| DELETE | `/api/formats/{format_id}` | Delete format |

### Available Formats

| Format ID | Name | Status |
|-----------|------|--------|
| `dev_vlog_meme_v1` | Dev Vlog + Memes | active |
| `ai_explainer_v1` | AI Explainer | active |
| `trend_breakdown_v1` | Trend Breakdown | active |
| `product_promo_v1` | Product Promo | draft |
| `ugc_corner_v1` | UGC Corner Overlay | active |
| `broll_text_v1` | B-Roll + Text Overlay | active |
| `pure_broll_v1` | Pure B-Roll + Text | active |

### Usage

```bash
# Seed sample formats
curl -X POST "http://localhost:5555/api/formats/seed-samples"

# List formats
curl "http://localhost:5555/api/formats/list"

# Run a format
curl -X POST "http://localhost:5555/api/formats/broll_text_v1/run" \
  -H "Content-Type: application/json" \
  -d '{"params": {"text": "Your Quote"}, "trigger_type": "manual"}'
```

---

## 6. Video Renderer Comparison

### Recommendation: **Motion Canvas**

| Feature | Motion Canvas | Remotion |
|---------|:-------------:|:--------:|
| **License** | ✅ Free (MIT) | ❌ Paid ($100-500/mo) |
| **Text Overlays** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Background Music** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Learning Curve** | Easy | Harder (React) |
| **Automation** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

### Files
- **Motion Canvas:** `Backend/services/video_renderer/motion_canvas_adapter.py`
- **Remotion:** `Backend/services/video_renderer/remotion_adapter.py`
- **Comparison Doc:** `Backend/docs/BROLL_TEXT_MUSIC_COMPARISON.md`

### Text Overlay Example (Motion Canvas)

```typescript
const text = new Txt({
  text: 'Your Quote Here',
  fontSize: 64,
  fill: '#ffffff',
});
view.add(text);
yield* text.opacity(1, 0.5);
```

### Background Music Example (Motion Canvas)

```typescript
audio('/path/to/music.mp3', 0, {volume: 0.7});
```

---

## 7. Integration Tests

### Test Files

| File | Tests | Coverage |
|------|-------|----------|
| `test_analysis_health_integration.py` | 13 | Analysis Health endpoints |
| `test_duplicate_detection_integration.py` | 17 | Duplicate Detection endpoints |
| `test_formats_api_integration.py` | 16 | Formats API endpoints |

### Run Tests

```bash
cd Backend

# Run all integration tests
./venv/bin/python -m pytest tests/integration/test_analysis_health_integration.py \
  tests/integration/test_duplicate_detection_integration.py \
  tests/integration/test_formats_api_integration.py -v

# Run specific test file
./venv/bin/python -m pytest tests/integration/test_duplicate_detection_integration.py -v
```

### Test Categories

**Analysis Health Tests:**
- Health status endpoint
- Scan incomplete analysis
- Skip image files
- Mark for reanalysis
- Concurrent scans

**Duplicate Detection Tests:**
- Find duplicates with threshold
- Exact matches
- Caption status protection
- Marking workflow
- Edge cases

**Formats API Tests:**
- List/seed/get formats
- B-Roll format discovery
- Run format triggers
- Complete workflows

---

## Quick Reference

### Check System Health
```bash
# Analysis status
curl "http://localhost:5555/api/analysis-health/scan-incomplete"

# Duplicate summary
curl "http://localhost:5555/api/duplicates/summary"

# Posted content summary
curl "http://localhost:5555/api/posted-matcher/cross-reference-summary"

# B-Roll candidates
curl "http://localhost:5555/api/format-discovery/broll-candidates"
```

### Common Workflows

**1. Find and Clean Duplicates:**
```bash
curl "http://localhost:5555/api/duplicates/find?similarity_threshold=0.85"
curl -X POST "http://localhost:5555/api/duplicates/mark-for-deletion" -d '{"video_ids": [...]}'
```

**2. Ensure All Videos Analyzed:**
```bash
curl "http://localhost:5555/api/analysis-health/scan-incomplete"
curl -X POST "http://localhost:5555/api/analysis-health/mark-incomplete-for-reanalysis"
curl -X POST "http://localhost:5555/api/media-db/batch/analyze" -d '{"limit": 100}'
```

**3. Prevent Duplicate Posting:**
```bash
curl "http://localhost:5555/api/posted-matcher/check-before-post/{video_id}"
curl -X POST "http://localhost:5555/api/posted-matcher/mark-as-posted" -d '{"local_video_id": "...", "platform": "tiktok", "posted_url": "..."}'
```

**4. Create B-Roll + Text Video:**
```bash
curl "http://localhost:5555/api/format-discovery/broll-candidates?limit=10"
curl -X POST "http://localhost:5555/api/formats/broll_text_v1/run" -d '{"params": {"text": "Your Quote"}}'
```

---

## Commits

| Commit | Description |
|--------|-------------|
| `65f8fdbd` | feat: Add duplicate video detection |
| `fc337f2e` | feat: Add analysis health system |
| `1557390c` | feat: Add integration tests |
| `c1c731b5` | feat: Add posted content matcher |
| `8e35b2cf` | fix: B-Roll detector + comparison doc |

---

*This document is auto-updated with new developments.*
