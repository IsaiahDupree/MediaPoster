# PRD 01 — Content Intelligence Agent

**Backend root:** `/Users/isaiahdupree/Documents/Software/MediaPoster/Backend`

## Owned Files
- `services/fate_scorer.py` — FATE persuasion scorer (F/A/T/E, regex-based, 0.0-1.0)
- `services/awareness_classifier.py` — Eugene Schwartz 5-level classifier
- `services/content_analyzer.py` — Groq Llama 3.3 70B content analysis
- `services/video_analyzer.py` — Full pipeline orchestrator
- `services/vision_analyzer.py` — OpenAI Vision frame analysis
- `services/whisper_transcriber.py` — Groq Whisper transcription
- `services/frame_analyzer.py` / `services/frame_sampler.py`
- `services/psychology_tagger.py` — Psychological trigger tagging
- `api/endpoints/analysis.py` — Analysis API including `/api/analysis/analyze-file`
- `config/model_registry.py` — Central AI model config

## Features to Build

### F1 — Cialdini Extension to FATEScorer
Add `score_scarcity()` and `score_social_proof()` to `FATEScorer`. Update `score_all()` to return `S` and `P` dimensions. Update `QAGateService` thresholds accordingly.

### F2 — FATE Score Persistence + Trends Endpoint
Store FATE scores per analysis run in DB. Add `GET /api/analysis/fate-trends?days=30` returning weekly F/A/T/E averages as chart-ready JSON.

### F3 — Awareness Classifier Confidence Score
Add `confidence: float` to classifier output. If top-2 levels are close, flag as `ambiguous: true` for human review.

### F4 — Batch Analyze Endpoint
Add `POST /api/analysis/batch` accepting a list of file paths/video IDs. Run pipeline concurrently (asyncio.gather), return results array. Cap at 20 items per request.

### F5 — Psychology Tags in QA Gate
Wire `psychology_tagger.py` output into `QAGateService`. Warn if content has zero psychological triggers detected for awareness levels 4-5.

## Success Criteria
- All existing tests in `tests/unit/` still pass
- New endpoints return valid JSON matching documented shapes
- No skipping allowed — every pipeline step must succeed or raise with clear error
- Use real OpenAI + Groq API calls
