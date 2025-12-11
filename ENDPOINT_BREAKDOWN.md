# API Endpoint Breakdown

**Total Endpoints:** 325

## api > blotato_router (16)
| Method | Path |
|--------|------|
| GET | `/health` |
| POST | `/posts` |
| POST | `/posts/multi-platform` |
| POST | `/media/upload` |
| POST | `/videos/create` |
| POST | `/videos/pov` |
| POST | `/videos/slideshow` |
| POST | `/videos/narrated` |
| GET | `/videos/{video_id}` |
| DELETE | `/videos/{video_id}` |
| GET | `/videos/{video_id}/wait` |
| GET | `/voices` |
| GET | `/platforms` |
| GET | `/video-styles` |
| GET | `/video-templates` |
| GET | `/ai-models` |


## api > media_processing (15)
| Method | Path |
|--------|------|
| POST | `/upload/init` |
| POST | `/upload` |
| GET | `/status/{media_id}` |
| GET | `/analysis/{media_id}` |
| GET | `/list` |
| POST | `/batch/ingest` |
| GET | `/batch/status/{job_id}` |
| POST | `/batch/resume/{job_id}` |
| POST | `/retry/{media_id}` |
| DELETE | `/{media_id}` |
| GET | `/thumbnail/{media_id}` |
| POST | `/thumbnails/generate` |
| GET | `/thumbnails/status/{job_id}` |
| GET | `/thumbnails/stats` |
| GET | `/health` |


## api > endpoints > social_analytics (13)
| Method | Path |
|--------|------|
| GET | `/overview` |
| GET | `/accounts` |
| GET | `/platform/{platform}` |
| GET | `/content-mapping` |
| GET | `/posts` |
| GET | `/trends` |
| GET | `/hashtags/top` |
| GET | `/content` |
| GET | `/content/leaderboard` |
| GET | `/content/{content_id}` |
| GET | `/followers/leaderboard` |
| GET | `/followers` |
| GET | `/followers/{follower_id}` |


## api > endpoints > videos (13)
| Method | Path |
|--------|------|
| GET | `/` |
| GET | `/count` |
| GET | `/{video_id}` |
| GET | `/{video_id}/summary` |
| GET | `/{video_id}/clips` |
| DELETE | `/{video_id}` |
| POST | `/upload` |
| POST | `/scan` |
| POST | `/scan/cancel/{scan_id}` |
| GET | `/scan/status` |
| POST | `/{video_id}/generate-thumbnail` |
| POST | `/generate-thumbnails-batch` |
| POST | `/{video_id}/analyze` |


## api > endpoints > enhanced_analysis (12)
| Method | Path |
|--------|------|
| GET | `/videos` |
| POST | `/videos/{video_id}/analyze` |
| GET | `/videos/{video_id}/validate` |
| GET | `/videos/{video_id}/export` |
| POST | `/segments` |
| PUT | `/segments/{segment_id}` |
| DELETE | `/segments/{segment_id}` |
| POST | `/segments/{segment_id}/split` |
| POST | `/segments/merge` |
| GET | `/segments/{segment_id}/performance` |
| GET | `/patterns/top-performing` |
| POST | `/predict` |


## api > media_processing_db (11)
| Method | Path |
|--------|------|
| GET | `/list` |
| GET | `/detail/{media_id}` |
| GET | `/stats` |
| POST | `/ingest/file` |
| POST | `/batch/ingest` |
| POST | `/analyze/{media_id}` |
| POST | `/batch/analyze` |
| GET | `/thumbnail/{media_id}` |
| GET | `/video/{media_id}` |
| DELETE | `/{media_id}` |
| GET | `/health` |


## api > endpoints > content (11)
| Method | Path |
|--------|------|
| GET | `/` |
| GET | `/metrics` |
| POST | `/items` |
| GET | `/items` |
| GET | `/items/{item_id}` |
| POST | `/variants` |
| GET | `/items/{item_id}/variants` |
| POST | `/items/{item_id}/generate-variants` |
| POST | `/variants/{variant_id}/publish` |
| POST | `/jobs/poll-metrics` |
| POST | `/jobs/aggregate-rollups` |


## api > endpoints > storage (11)
| Method | Path |
|--------|------|
| GET | `/stats` |
| GET | `/videos` |
| GET | `/thumbnails` |
| GET | `/clips` |
| GET | `/files/videos/{video_id}` |
| GET | `/files/thumbnails/{video_id}` |
| GET | `/files/clips/{clip_id}` |
| POST | `/cleanup` |
| DELETE | `/videos/{video_id}` |
| DELETE | `/thumbnails/{video_id}` |
| DELETE | `/clips/{clip_id}` |


## api > endpoints > clip_management (10)
| Method | Path |
|--------|------|
| GET | `/suggest` |
| POST | `/create` |
| GET | `/{clip_id}` |
| PUT | `/{clip_id}` |
| DELETE | `/{clip_id}` |
| GET | `/video/{video_id}` |
| POST | `/{clip_id}/variants` |
| POST | `/{clip_id}/publish` |
| GET | `/{clip_id}/posts` |
| GET | `/{clip_id}/performance` |


## api > endpoints > publishing_queue (10)
| Method | Path |
|--------|------|
| GET | `/queue` |
| GET | `/analytics` |
| POST | `/add` |
| POST | `/bulk` |
| GET | `/items` |
| GET | `/status` |
| PUT | `/{item_id}/retry` |
| PUT | `/{item_id}/reschedule` |
| DELETE | `/{item_id}/cancel` |
| POST | `/process` |


## api > endpoints > analytics_insights (9)
| Method | Path |
|--------|------|
| POST | `/metrics/calculate-weekly` |
| GET | `/dashboard` |
| GET | `/post/{post_id}/performance` |
| GET | `/insights/hooks` |
| GET | `/insights/posting-times/{platform}` |
| GET | `/insights/topics` |
| GET | `/recommendations` |
| GET | `/metrics/north-star` |
| GET | `/platform-comparison` |


## api > endpoints > publishing_analytics (9)
| Method | Path |
|--------|------|
| POST | `/publishing/schedule` |
| PUT | `/publishing/posts/{post_id}/reschedule` |
| POST | `/publishing/posts/{post_id}/regenerate` |
| GET | `/publishing/calendar/{year}/{month}` |
| POST | `/publishing/auto-schedule` |
| GET | `/analytics/overview` |
| GET | `/analytics/posts/{post_id}/performance` |
| GET | `/analytics/posts/{post_id}/retention` |
| GET | `/analytics/insights` |


## api > endpoints > media_creation (8)
| Method | Path |
|--------|------|
| GET | `/content-types` |
| GET | `/templates` |
| POST | `/projects` |
| GET | `/projects` |
| GET | `/projects/{project_id}` |
| POST | `/projects/{project_id}/create-content` |
| POST | `/projects/{project_id}/edit` |
| GET | `/projects/{project_id}/preview` |


## api > endpoints > social_accounts (8)
| Method | Path |
|--------|------|
| POST | `/accounts/sync-from-env` |
| GET | `/accounts` |
| POST | `/accounts` |
| DELETE | `/accounts/{account_id}` |
| GET | `/accounts/{account_id}/fetch-live` |
| POST | `/accounts/fetch-all` |
| GET | `/platforms/summary` |
| GET | `/platforms/{platform}/accounts` |


## api > endpoints > viral_analysis (7)
| Method | Path |
|--------|------|
| GET | `/videos` |
| POST | `/videos/{video_id}/analyze` |
| POST | `/videos/{video_id}/analyze-sync` |
| GET | `/videos/{video_id}/words` |
| GET | `/videos/{video_id}/frames` |
| GET | `/videos/{video_id}/timeline` |
| GET | `/videos/{video_id}/metrics` |


## api > endpoints > platform_publishing (7)
| Method | Path |
|--------|------|
| POST | `/publish` |
| GET | `/platforms` |
| POST | `/metrics/collect` |
| POST | `/comments/collect` |
| GET | `/posts` |
| GET | `/posts/{post_id}` |
| POST | `/schedule-checkbacks/{post_id}` |


## api > endpoints > calendar (7)
| Method | Path |
|--------|------|
| GET | `/posts` |
| POST | `/schedule` |
| PATCH | `/posts/{post_id}` |
| DELETE | `/posts/{post_id}` |
| POST | `/bulk-schedule` |
| GET | `/gaps` |
| POST | `/posts/{post_id}/publish` |


## api > endpoints > email (7)
| Method | Path |
|--------|------|
| GET | `/status` |
| POST | `/send` |
| POST | `/send-segment` |
| POST | `/event` |
| GET | `/tracking/open/{message_id}` |
| GET | `/messages/{message_id}` |
| GET | `/person/{person_id}/messages` |


## quickstart (6)
| Method | Path |
|--------|------|
| GET | `/` |
| GET | `/api/videos/scan` |
| GET | `/api/videos` |
| GET | `/api/videos/{video_id}` |
| GET | `/api/videos/{video_id}/info` |
| GET | `/health` |


## api > endpoints > people (6)
| Method | Path |
|--------|------|
| GET | `/` |
| GET | `/{person_id}` |
| GET | `/{person_id}/insights` |
| POST | `/{person_id}/recompute-lens` |
| POST | `/ingest/comment` |
| POST | `/rebuild-all-lenses` |


## api > endpoints > api_usage (6)
| Method | Path |
|--------|------|
| GET | `/usage` |
| GET | `/usage/{api_name}` |
| GET | `/health/{api_name}` |
| POST | `/clear-cache/{api_name}` |
| DELETE | `/logs` |
| GET | `/recommendations` |


## api > endpoints > content_metrics (6)
| Method | Path |
|--------|------|
| GET | `/` |
| POST | `/poll/{content_id}` |
| GET | `/{content_id}/rollup` |
| GET | `/{content_id}/metrics` |
| POST | `/poll-recent` |
| POST | `/{content_id}/recompute-rollup` |


## api > endpoints > video_generation (6)
| Method | Path |
|--------|------|
| POST | `/create` |
| GET | `/{job_id}` |
| GET | `/jobs` |
| DELETE | `/{job_id}` |
| GET | `/providers` |
| GET | `/providers/{provider_name}` |


## api > endpoints > thumbnails (6)
| Method | Path |
|--------|------|
| GET | `/dimensions` |
| POST | `/select-best-frame` |
| POST | `/generate` |
| POST | `/generate-from-video` |
| POST | `/enhance-with-ai` |
| POST | `/complete-workflow` |


## api > endpoints > workspaces (6)
| Method | Path |
|--------|------|
| GET | `/` |
| POST | `/` |
| GET | `/{workspace_id}` |
| PATCH | `/{workspace_id}` |
| DELETE | `/{workspace_id}` |
| GET | `/{workspace_id}/members` |


## api > analytics_compare (5)
| Method | Path |
|--------|------|
| GET | `/accounts` |
| POST | `/compare` |
| GET | `/compare-time/{account_id}` |
| GET | `/audience-comparison` |
| GET | `/platforms-summary` |


## api > endpoints > creative_briefs (5)
| Method | Path |
|--------|------|
| POST | `/generate-brief` |
| POST | `/generate-prompt` |
| GET | `/formats` |
| GET | `/niches` |
| GET | `/scene-roles` |


## api > endpoints > ingestion (5)
| Method | Path |
|--------|------|
| POST | `/start` |
| POST | `/stop` |
| GET | `/status` |
| POST | `/scan` |
| POST | `/import-iphone` |


## api > endpoints > analysis (5)
| Method | Path |
|--------|------|
| POST | `/full-analysis/{video_id}` |
| POST | `/transcribe/{video_id}` |
| GET | `/results` |
| GET | `/results/{video_id}` |
| GET | `/transcript/{video_id}` |


## api > endpoints > trending (5)
| Method | Path |
|--------|------|
| GET | `/trending/topics` |
| GET | `/trending/competitor/{username}` |
| GET | `/trending/hashtag/{hashtag}` |
| GET | `/trending/ideas` |
| GET | `/trending/video/{video_id}` |


## api > endpoints > goals (5)
| Method | Path |
|--------|------|
| POST | `/` |
| GET | `/` |
| PATCH | `/{goal_id}` |
| DELETE | `/{goal_id}` |
| POST | `/{goal_id}/refresh-progress` |


## api > endpoints > blotato_test (5)
| Method | Path |
|--------|------|
| GET | `/config` |
| POST | `/test-connection` |
| POST | `/providers/{provider}/test` |
| POST | `/providers/{provider}/schedule` |
| POST | `/providers/{provider}/scrape` |


## api > endpoints > inventory_scheduler (5)
| Method | Path |
|--------|------|
| GET | `/inventory` |
| GET | `/plan` |
| POST | `/auto-schedule` |
| POST | `/update-on-new-content` |
| GET | `/status` |


## api > endpoints > briefs (4)
| Method | Path |
|--------|------|
| GET | `/` |
| POST | `/generate` |
| GET | `/goals` |
| POST | `/test-brief` |


## api > endpoints > clips (4)
| Method | Path |
|--------|------|
| GET | `/` |
| POST | `/generate/{video_id}` |
| GET | `/list/{video_id}` |
| GET | `/{clip_id}/stream` |


## api > endpoints > highlights (4)
| Method | Path |
|--------|------|
| POST | `/detect/{video_id}` |
| GET | `/results` |
| GET | `/results/{video_id}` |
| GET | `/{highlight_id}/reasoning` |


## api > endpoints > accounts (4)
| Method | Path |
|--------|------|
| GET | `/` |
| POST | `/connect` |
| POST | `/sync` |
| GET | `/status` |


## api > endpoints > segments (4)
| Method | Path |
|--------|------|
| POST | `/` |
| GET | `/` |
| GET | `/{segment_id}` |
| GET | `/{segment_id}/insights` |


## main (3)
| Method | Path |
|--------|------|
| GET | `/health` |
| GET | `/api/health` |
| GET | `/` |


## api > posted_media (3)
| Method | Path |
|--------|------|
| GET | `/list` |
| GET | `/platforms` |
| GET | `/{post_id}` |


## api > ai_chat (3)
| Method | Path |
|--------|------|
| GET | `/contexts` |
| POST | `/chat` |
| GET | `/quick-prompts` |


## api > endpoints > publishing (3)
| Method | Path |
|--------|------|
| POST | `/schedule` |
| GET | `/scheduled` |
| GET | `/calendar` |


## api > endpoints > ai_recommendations (3)
| Method | Path |
|--------|------|
| POST | `/generate` |
| GET | `/` |
| POST | `/{id}/action` |


## api > endpoints > post_social_score (3)
| Method | Path |
|--------|------|
| GET | `/post/{post_id}` |
| POST | `/post/{post_id}/calculate` |
| GET | `/account/{account_id}/summary` |


## api > endpoints > analytics (3)
| Method | Path |
|--------|------|
| GET | `/summary` |
| GET | `/performance` |
| GET | `/trends` |


## list_endpoints_detailed (2)
| Method | Path |
|--------|------|
| GET | `/some/path` |
| POST | `/some/path` |


## api > endpoints > dashboard (2)
| Method | Path |
|--------|------|
| GET | `/widgets` |
| GET | `/north-star` |


## api > endpoints > jobs (2)
| Method | Path |
|--------|------|
| GET | `/` |
| GET | `/{job_id}` |


## api > endpoints > coaching (2)
| Method | Path |
|--------|------|
| GET | `/recommendations` |
| POST | `/chat` |


## api > endpoints > messages (2)
| Method | Path |
|--------|------|
| POST | `/generate` |
| POST | `/send` |


## api > endpoints > optimal_posting_times (2)
| Method | Path |
|--------|------|
| GET | `/platform/{platform}` |
| POST | `/recommend` |


## api > endpoints > comments (2)
| Method | Path |
|--------|------|
| GET | `/comments` |
| GET | `/comments/stats` |


## api > endpoints > app_config (2)
| Method | Path |
|--------|------|
| GET | `/` |
| GET | `/health` |


## api > endpoints > goal_recommendations (1)
| Method | Path |
|--------|------|
| GET | `/{goal_id}/recommendations` |


## api > endpoints > scheduling (1)
| Method | Path |
|--------|------|
| POST | `/upload` |


