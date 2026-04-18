# PRD 05 — Video Generation Agent

**Backend root:** `/Users/isaiahdupree/Documents/Software/MediaPoster/Backend`

## Owned Files
- `services/sora_video_pipeline.py` — Sora video generation pipeline
- `services/video_generation/` — Video generation services (orchestrator, pipeline)
- `services/video_orchestrator/` — Video orchestration + narrative bridge
- `services/tts/` — Text-to-speech (ElevenLabs + fallbacks)
- `services/music/` — Music matching, selector, library
- `services/matting/` — Background removal/matting
- `services/remotion/` — Remotion renderer integration
- `services/video_renderer/` — Video renderer formats + pipeline
- `services/thumbnail_generator.py` / `services/thumbnail_service.py`
- `services/subtitle_service.py` — Auto subtitle generation
- `services/clip_editor.py` / `services/clip_selector.py`
- `automation/sora/` — Sora browser automation
- `automation/sora_generator.py` — Sora generator
- `automation/sora_full_automation.py` — Full Sora automation
- `api/endpoints/video_orchestrator.py` — Video orchestration API
- `scripts/personalbrand_video_generator.py` — End-to-end competitor-inspired video gen

## Current State
- Sora pipeline: browser automation via Safari → sora.chatgpt.com
- TTS: ElevenLabs primary, fallback chain
- Music matching: content-aware selection from library
- Remotion: renders React-based video compositions (stickfigure template)
- MasterOrchestrator workflow: Sora → Stitch → Analyze → Publish

## Features to Build

### F1 — Voice Clone Pipeline
Wire `voice_cloning_quality_assessor.py` into TTS pipeline.
When `creator_voice_id` is set in brand config, use ElevenLabs cloned voice.
Fall back to preset voice if clone quality score < 0.7.
Add `POST /api/tts/generate` accepting text + voice_id, returning audio file path.
Store generated audio in `/tmp/mediaposter_tts/{job_id}.mp3`.

### F2 — Auto-Thumbnail Selection
After video generation, use `ai_thumbnail_selector.py` to extract 5 candidate frames,
score each on visual impact + text legibility, select the top scorer as the thumbnail.
Store thumbnail path in DB alongside video record.
Add `GET /api/videos/{video_id}/thumbnails` returning all candidates with scores.

### F3 — Subtitle Auto-Embed
After transcription, use `subtitle_service.py` to generate SRT file.
Use FFmpeg to burn subtitles into output video with brand-consistent styling
(white text, black outline, bottom-center, 36px).
Add `burned_subtitles: bool` flag to video generation request.

### F4 — Music Mood Matching
Extend `music_matcher.py` to accept FATE emotion score as input.
High E score → uplifting/inspiring music. Low E → neutral/ambient.
High F score → high-energy, punchy. Map FATE → mood enum → music selection.
Add unit test covering all 4 FATE dimension combinations.

### F5 — Sora Usage Guard
Before triggering Sora generation, call `sora_full_automation.get_usage()`.
If 0 video gens remaining, emit `agent_event` with type `sora_quota_exhausted`
and abort with clear error (no silent skip).
Add `GET /api/sora/quota` endpoint returning remaining gens + reset date.

## Success Criteria
- Voice clone pipeline uses real ElevenLabs API, quality gate functional
- Thumbnail selection runs automatically post-generation
- Subtitles burned correctly using FFmpeg (verify with ffprobe)
- Sora quota check prevents wasted automation runs
- No steps skip silently — all failures raise with descriptive errors
