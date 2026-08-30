# MediaPoster Agent Service and Contract Guide

> Repository-owned documentation. It does not require an external control plane.

Media production, provider integration, scheduling, analytics, and social publishing services.

## Agent operating rules

1. Read this guide before changing an API, queue, schema, provider adapter, database object, or cross-system payload.
2. Treat JSON Schema and OpenAPI files as authoritative. Typed application models are implementation contracts unless explicitly exported.
3. Do not guess route parameters, environment values, account IDs, provider IDs, or receipt fields.
4. Read operations do not authorize writes. Provider writes, publishing, messages, paid compute, destructive controls, and migrations require their owning approval policy.
5. Persist idempotency and provider/job receipts before retrying an accepted or ambiguous external write.
6. Never place credential values in source, docs, fixtures, logs, generated artifacts, or receipts.

## Inventory summary

- Static API routes: **2237** (1034 potentially mutating)
- Formal JSON Schema/OpenAPI contracts: **2**
- Typed application models: **1132**
- Database objects declared in migrations: **593**
- Environment-variable names: **197**
- Package manifests with scripts: **3**
- Source fingerprint: `4065f53e3033906ad229a7832a508392a223bc74415e6c9a12d56ce67708a60b`

This is a static source inventory, not a live health report. Dynamic routes and runtime registrations must be verified through the repository's own health/discovery interface.

## Service entrypoints

| Package | Manifest | Script names |
|---|---|---|
| `actp-dashboard` | [`Backend/services/creative_testing_pipeline/ui/package.json`](Backend/services/creative_testing_pipeline/ui/package.json) | build, dev, preview |
| `mediaposter-motion` | [`MotionCanvas/package.json`](MotionCanvas/package.json) | build, render, start |
| `mediaposter-control-plane-publishing-20260830` | [`package.json`](package.json) | - |

## HTTP and API surface

| Method | Route | Source | Write review |
|---|---|---|---|
| `GET` | `/` | [`Backend/api/endpoints/accounts.py:58`](Backend/api/endpoints/accounts.py#L58) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/ai_recommendations.py:44`](Backend/api/endpoints/ai_recommendations.py#L44) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/app_config.py:17`](Backend/api/endpoints/app_config.py#L17) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/automations.py:77`](Backend/api/endpoints/automations.py#L77) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/brands.py:143`](Backend/api/endpoints/brands.py#L143) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/briefs.py:22`](Backend/api/endpoints/briefs.py#L22) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/clips.py:35`](Backend/api/endpoints/clips.py#L35) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/content.py:48`](Backend/api/endpoints/content.py#L48) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/content_metrics.py:22`](Backend/api/endpoints/content_metrics.py#L22) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/goals.py:75`](Backend/api/endpoints/goals.py#L75) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/icps.py:137`](Backend/api/endpoints/icps.py#L137) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/jobs.py:34`](Backend/api/endpoints/jobs.py#L34) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/offers.py:153`](Backend/api/endpoints/offers.py#L153) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/people.py:59`](Backend/api/endpoints/people.py#L59) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/prompt_settings.py:57`](Backend/api/endpoints/prompt_settings.py#L57) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/segments.py:74`](Backend/api/endpoints/segments.py#L74) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/templates.py:119`](Backend/api/endpoints/templates.py#L119) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/videos.py:58`](Backend/api/endpoints/videos.py#L58) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/voice_selection.py:51`](Backend/api/endpoints/voice_selection.py#L51) | `read` |
| `GET` | `/` | [`Backend/api/endpoints/workspaces.py:54`](Backend/api/endpoints/workspaces.py#L54) | `read` |
| `GET` | `/` | [`Backend/control_plane/main.py:165`](Backend/control_plane/main.py#L165) | `read` |
| `GET` | `/` | [`Backend/main.py:882`](Backend/main.py#L882) | `read` |
| `GET` | `/` | [`Backend/quickstart.py:30`](Backend/quickstart.py#L30) | `read` |
| `POST` | `/` | [`Backend/api/endpoints/automations.py:143`](Backend/api/endpoints/automations.py#L143) | `required` |
| `POST` | `/` | [`Backend/api/endpoints/brands.py:93`](Backend/api/endpoints/brands.py#L93) | `required` |
| `POST` | `/` | [`Backend/api/endpoints/goals.py:47`](Backend/api/endpoints/goals.py#L47) | `required` |
| `POST` | `/` | [`Backend/api/endpoints/icps.py:85`](Backend/api/endpoints/icps.py#L85) | `required` |
| `POST` | `/` | [`Backend/api/endpoints/offers.py:88`](Backend/api/endpoints/offers.py#L88) | `required` |
| `POST` | `/` | [`Backend/api/endpoints/segments.py:22`](Backend/api/endpoints/segments.py#L22) | `required` |
| `POST` | `/` | [`Backend/api/endpoints/templates.py:247`](Backend/api/endpoints/templates.py#L247) | `required` |
| `POST` | `/` | [`Backend/api/endpoints/workspaces.py:95`](Backend/api/endpoints/workspaces.py#L95) | `required` |
| `PUT` | `/` | [`Backend/api/endpoints/prompt_settings.py:81`](Backend/api/endpoints/prompt_settings.py#L81) | `required` |
| `GET` | `/1hour-schedule` | [`Backend/api/endpoints/safari_automation.py:451`](Backend/api/endpoints/safari_automation.py#L451) | `read` |
| `POST` | `/ab-test` | [`Backend/api/endpoints/adaptive_scheduler.py:564`](Backend/api/endpoints/adaptive_scheduler.py#L564) | `required` |
| `POST` | `/account` | [`Backend/api/endpoints/content_download.py:133`](Backend/api/endpoints/content_download.py#L133) | `required` |
| `GET` | `/account-history/{account_id}` | [`Backend/api/endpoints/content_guard.py:171`](Backend/api/endpoints/content_guard.py#L171) | `read` |
| `GET` | `/account/{account_id}/summary` | [`Backend/api/endpoints/post_social_score.py:226`](Backend/api/endpoints/post_social_score.py#L226) | `read` |
| `GET` | `/account/{account_id}/trends` | [`Backend/api/endpoints/social_analytics.py:409`](Backend/api/endpoints/social_analytics.py#L409) | `read` |
| `GET` | `/accounts` | [`Backend/api/analytics_compare.py:332`](Backend/api/analytics_compare.py#L332) | `read` |
| `GET` | `/accounts` | [`Backend/api/blotato_router.py:206`](Backend/api/blotato_router.py#L206) | `read` |
| `GET` | `/accounts` | [`Backend/api/endpoints/blotato_test.py:105`](Backend/api/endpoints/blotato_test.py#L105) | `read` |
| `GET` | `/accounts` | [`Backend/api/endpoints/competitor_api.py:47`](Backend/api/endpoints/competitor_api.py#L47) | `read` |
| `GET` | `/accounts` | [`Backend/api/endpoints/competitor_audit.py:325`](Backend/api/endpoints/competitor_audit.py#L325) | `read` |
| `GET` | `/accounts` | [`Backend/api/endpoints/external_scheduling.py:512`](Backend/api/endpoints/external_scheduling.py#L512) | `read` |
| `GET` | `/accounts` | [`Backend/api/endpoints/safari_sessions.py:100`](Backend/api/endpoints/safari_sessions.py#L100) | `read` |
| `GET` | `/accounts` | [`Backend/api/endpoints/social_accounts.py:198`](Backend/api/endpoints/social_accounts.py#L198) | `read` |
| `GET` | `/accounts` | [`Backend/api/endpoints/social_analytics.py:164`](Backend/api/endpoints/social_analytics.py#L164) | `read` |
| `GET` | `/accounts` | [`Backend/api/endpoints/tiktok_repurpose.py:322`](Backend/api/endpoints/tiktok_repurpose.py#L322) | `read` |
| `GET` | `/accounts` | [`Backend/api/social_accounts.py:16`](Backend/api/social_accounts.py#L16) | `read` |
| `POST` | `/accounts` | [`Backend/api/endpoints/competitor_api.py:72`](Backend/api/endpoints/competitor_api.py#L72) | `required` |
| `POST` | `/accounts` | [`Backend/api/endpoints/social_accounts.py:255`](Backend/api/endpoints/social_accounts.py#L255) | `required` |
| `GET` | `/accounts/detailed` | [`Backend/api/endpoints/competitor_api.py:58`](Backend/api/endpoints/competitor_api.py#L58) | `read` |
| `POST` | `/accounts/fetch-all` | [`Backend/api/endpoints/social_accounts.py:483`](Backend/api/endpoints/social_accounts.py#L483) | `required` |
| `GET` | `/accounts/list` | [`Backend/api/endpoints/schedule.py:953`](Backend/api/endpoints/schedule.py#L953) | `read` |
| `GET` | `/accounts/platform/{platform}` | [`Backend/api/endpoints/safari_sessions.py:157`](Backend/api/endpoints/safari_sessions.py#L157) | `read` |
| `POST` | `/accounts/platform/{platform}/set-active` | [`Backend/api/endpoints/safari_sessions.py:219`](Backend/api/endpoints/safari_sessions.py#L219) | `required` |
| `POST` | `/accounts/register` | [`Backend/api/endpoints/safari_sessions.py:58`](Backend/api/endpoints/safari_sessions.py#L58) | `required` |
| `POST` | `/accounts/sync-from-env` | [`Backend/api/endpoints/social_accounts.py:155`](Backend/api/endpoints/social_accounts.py#L155) | `required` |
| `DELETE` | `/accounts/{account_id}` | [`Backend/api/endpoints/social_accounts.py:356`](Backend/api/endpoints/social_accounts.py#L356) | `required` |
| `GET` | `/accounts/{account_id}` | [`Backend/api/endpoints/safari_sessions.py:127`](Backend/api/endpoints/safari_sessions.py#L127) | `read` |
| `GET` | `/accounts/{account_id}/fetch-live` | [`Backend/api/endpoints/social_accounts.py:383`](Backend/api/endpoints/social_accounts.py#L383) | `read` |
| `GET` | `/accounts/{account_id}/posting-times` | [`Backend/api/endpoints/competitor_audit.py:642`](Backend/api/endpoints/competitor_audit.py#L642) | `read` |
| `GET` | `/accounts/{account_id}/posts` | [`Backend/api/endpoints/competitor_audit.py:364`](Backend/api/endpoints/competitor_audit.py#L364) | `read` |
| `PATCH` | `/accounts/{account_id}/role` | [`Backend/api/endpoints/experiments.py:1031`](Backend/api/endpoints/experiments.py#L1031) | `required` |
| `POST` | `/accounts/{account_id}/status` | [`Backend/api/endpoints/safari_sessions.py:187`](Backend/api/endpoints/safari_sessions.py#L187) | `required` |
| `POST` | `/accounts/{account_id}/sync` | [`Backend/api/endpoints/social_accounts.py:320`](Backend/api/endpoints/social_accounts.py#L320) | `required` |
| `GET` | `/accounts/{platform}/{account_id}/offers` | [`Backend/api/endpoints/dm_outreach.py:451`](Backend/api/endpoints/dm_outreach.py#L451) | `read` |
| `DELETE` | `/accounts/{username}` | [`Backend/api/endpoints/competitor_api.py:941`](Backend/api/endpoints/competitor_api.py#L941) | `required` |
| `GET` | `/accounts/{username}/analysis` | [`Backend/api/endpoints/competitor_api.py:246`](Backend/api/endpoints/competitor_api.py#L246) | `read` |
| `POST` | `/accounts/{username}/analyze` | [`Backend/api/endpoints/competitor_api.py:211`](Backend/api/endpoints/competitor_api.py#L211) | `required` |
| `GET` | `/accounts/{username}/content` | [`Backend/api/endpoints/competitor_api.py:964`](Backend/api/endpoints/competitor_api.py#L964) | `read` |
| `POST` | `/accounts/{username}/download` | [`Backend/api/endpoints/competitor_api.py:337`](Backend/api/endpoints/competitor_api.py#L337) | `required` |
| `POST` | `/accounts/{username}/fetch-posts` | [`Backend/api/endpoints/competitor_api.py:859`](Backend/api/endpoints/competitor_api.py#L859) | `required` |
| `GET` | `/accounts/{username}/posts` | [`Backend/api/endpoints/competitor_api.py:193`](Backend/api/endpoints/competitor_api.py#L193) | `read` |
| `GET` | `/accounts/{username}/profile` | [`Backend/api/endpoints/competitor_api.py:155`](Backend/api/endpoints/competitor_api.py#L155) | `read` |
| `GET` | `/accounts/{username}/reels` | [`Backend/api/endpoints/competitor_api.py:175`](Backend/api/endpoints/competitor_api.py#L175) | `read` |
| `POST` | `/accounts/{username}/scrape` | [`Backend/api/endpoints/competitor_api.py:266`](Backend/api/endpoints/competitor_api.py#L266) | `required` |
| `GET` | `/accounts/{username}/scrape/status` | [`Backend/api/endpoints/competitor_api.py:301`](Backend/api/endpoints/competitor_api.py#L301) | `read` |
| `POST` | `/accounts/{username}/sync` | [`Backend/api/endpoints/competitor_api.py:112`](Backend/api/endpoints/competitor_api.py#L112) | `required` |
| `GET` | `/actions` | [`Backend/api/engagement_autopilot.py:43`](Backend/api/engagement_autopilot.py#L43) | `read` |
| `POST` | `/actions/{action_id}/approve` | [`Backend/api/engagement_autopilot.py:81`](Backend/api/engagement_autopilot.py#L81) | `required` |
| `POST` | `/actions/{action_id}/reject` | [`Backend/api/engagement_autopilot.py:89`](Backend/api/engagement_autopilot.py#L89) | `required` |
| `GET` | `/active` | [`Backend/api/endpoints/workflows.py:36`](Backend/api/endpoints/workflows.py#L36) | `read` |
| `GET` | `/activity` | [`Backend/api/approval_queue.py:590`](Backend/api/approval_queue.py#L590) | `read` |
| `POST` | `/adapt` | [`Backend/api/endpoints/adaptive_scheduler.py:427`](Backend/api/endpoints/adaptive_scheduler.py#L427) | `required` |
| `POST` | `/adapt/full` | [`Backend/api/endpoints/adaptive_scheduler.py:383`](Backend/api/endpoints/adaptive_scheduler.py#L383) | `required` |
| `POST` | `/add` | [`Backend/api/endpoints/publishing_queue.py:71`](Backend/api/endpoints/publishing_queue.py#L71) | `required` |
| `GET` | `/agents` | [`Backend/api/endpoints/agent_events.py:260`](Backend/api/endpoints/agent_events.py#L260) | `read` |
| `GET` | `/ai-models` | [`Backend/api/blotato_router.py:1225`](Backend/api/blotato_router.py#L1225) | `read` |
| `POST` | `/ai/generate` | [`Backend/api/endpoints/adaptive_scheduler.py:572`](Backend/api/endpoints/adaptive_scheduler.py#L572) | `required` |
| `GET` | `/alerts` | [`Backend/api/endpoints/content_runway.py:219`](Backend/api/endpoints/content_runway.py#L219) | `read` |
| `GET` | `/alerts` | [`Backend/api/endpoints/trends.py:470`](Backend/api/endpoints/trends.py#L470) | `read` |
| `GET` | `/alerts` | [`Backend/api/trend_detection.py:55`](Backend/api/trend_detection.py#L55) | `read` |
| `POST` | `/alerts/{alert_id}/dismiss` | [`Backend/api/endpoints/trends.py:507`](Backend/api/endpoints/trends.py#L507) | `required` |
| `POST` | `/alerts/{alert_id}/read` | [`Backend/api/endpoints/trends.py:495`](Backend/api/endpoints/trends.py#L495) | `required` |
| `GET` | `/all` | [`Backend/api/endpoints/app_validation.py:15`](Backend/api/endpoints/app_validation.py#L15) | `read` |
| `GET` | `/all` | [`Backend/api/posted_media.py:264`](Backend/api/posted_media.py#L264) | `read` |
| `GET` | `/allocation/{template_id}` | [`Backend/api/endpoints/bandit.py:131`](Backend/api/endpoints/bandit.py#L131) | `read` |
| `GET` | `/allocations` | [`Backend/api/endpoints/bandit.py:92`](Backend/api/endpoints/bandit.py#L92) | `read` |
| `GET` | `/already-posted` | [`Backend/api/endpoints/posted_content_matcher.py:147`](Backend/api/endpoints/posted_content_matcher.py#L147) | `read` |
| `GET` | `/analyses` | [`Backend/api/image_analysis.py:943`](Backend/api/image_analysis.py#L943) | `read` |
| `GET` | `/analysis-status` | [`Backend/api/media_processing_db.py:896`](Backend/api/media_processing_db.py#L896) | `read` |
| `GET` | `/analysis/aggregate` | [`Backend/api/endpoints/competitor_api.py:513`](Backend/api/endpoints/competitor_api.py#L513) | `read` |
| `POST` | `/analysis/generate-playbook` | [`Backend/api/endpoints/competitor_api.py:652`](Backend/api/endpoints/competitor_api.py#L652) | `required` |
| `POST` | `/analysis/start` | [`Backend/api/endpoints/content_ingestion.py:178`](Backend/api/endpoints/content_ingestion.py#L178) | `required` |
| `POST` | `/analysis/stop` | [`Backend/api/endpoints/content_ingestion.py:213`](Backend/api/endpoints/content_ingestion.py#L213) | `required` |
| `GET` | `/analysis/{analysis_id}` | [`Backend/api/image_analysis.py:935`](Backend/api/image_analysis.py#L935) | `read` |
| `GET` | `/analysis/{media_id}` | [`Backend/api/media_processing.py:324`](Backend/api/media_processing.py#L324) | `read` |
| `GET` | `/analysis/{media_id}` | [`Backend/api/media_processing_db.py:3150`](Backend/api/media_processing_db.py#L3150) | `read` |
| `PUT` | `/analysis/{media_id}` | [`Backend/api/media_processing_db.py:3245`](Backend/api/media_processing_db.py#L3245) | `required` |
| `PUT` | `/analysis/{media_id}/post-score` | [`Backend/api/media_processing_db.py:3335`](Backend/api/media_processing_db.py#L3335) | `required` |
| `GET` | `/analysis/{media_id}/scores` | [`Backend/api/media_processing_db.py:3427`](Backend/api/media_processing_db.py#L3427) | `read` |
| `GET` | `/analytics` | [`Backend/api/content_pipeline.py:596`](Backend/api/content_pipeline.py#L596) | `read` |
| `GET` | `/analytics` | [`Backend/api/endpoints/publishing_queue.py:58`](Backend/api/endpoints/publishing_queue.py#L58) | `read` |
| `GET` | `/analytics/benchmarks/{platform}` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:843`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L843) | `read` |
| `GET` | `/analytics/by-origin` | [`Backend/api/endpoints/experiments.py:1874`](Backend/api/endpoints/experiments.py#L1874) | `read` |
| `GET` | `/analytics/by-url` | [`Backend/api/endpoints/posted_content.py:335`](Backend/api/endpoints/posted_content.py#L335) | `read` |
| `GET` | `/analytics/campaign/{campaign_id}` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:617`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L617) | `read` |
| `POST` | `/analytics/compare` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:586`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L586) | `required` |
| `GET` | `/analytics/content` | [`Backend/api/endpoints/adaptive_scheduler.py:866`](Backend/api/endpoints/adaptive_scheduler.py#L866) | `read` |
| `GET` | `/analytics/dashboard` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:334`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L334) | `read` |
| `GET` | `/analytics/export` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:595`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L595) | `read` |
| `GET` | `/analytics/historical` | [`Backend/api/endpoints/orchestrator.py:457`](Backend/api/endpoints/orchestrator.py#L457) | `read` |
| `GET` | `/analytics/insights` | [`Backend/api/endpoints/publishing_analytics.py:423`](Backend/api/endpoints/publishing_analytics.py#L423) | `read` |
| `GET` | `/analytics/overview` | [`Backend/api/endpoints/publishing_analytics.py:292`](Backend/api/endpoints/publishing_analytics.py#L292) | `read` |
| `GET` | `/analytics/posted` | [`Backend/routers/visual_campaign.py:211`](Backend/routers/visual_campaign.py#L211) | `read` |
| `GET` | `/analytics/posts/{post_id}/performance` | [`Backend/api/endpoints/publishing_analytics.py:357`](Backend/api/endpoints/publishing_analytics.py#L357) | `read` |
| `GET` | `/analytics/posts/{post_id}/retention` | [`Backend/api/endpoints/publishing_analytics.py:390`](Backend/api/endpoints/publishing_analytics.py#L390) | `read` |
| `POST` | `/analytics/refresh-all` | [`Backend/api/endpoints/posted_content.py:394`](Backend/api/endpoints/posted_content.py#L394) | `required` |
| `GET` | `/analytics/round/{round_id}` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:610`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L610) | `read` |
| `GET` | `/analytics/scheduled` | [`Backend/routers/twitter_campaign.py:283`](Backend/routers/twitter_campaign.py#L283) | `read` |
| `GET` | `/analytics/scheduled` | [`Backend/routers/visual_campaign.py:166`](Backend/routers/visual_campaign.py#L166) | `read` |
| `GET` | `/analytics/summary` | [`Backend/routers/twitter_campaign.py:275`](Backend/routers/twitter_campaign.py#L275) | `read` |
| `GET` | `/analytics/top-themes` | [`Backend/api/endpoints/orchestrator.py:428`](Backend/api/endpoints/orchestrator.py#L428) | `read` |
| `GET` | `/analytics/tweets` | [`Backend/routers/twitter_campaign.py:256`](Backend/routers/twitter_campaign.py#L256) | `read` |
| `GET` | `/analytics/{creative_id}/peak-engagement` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:834`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L834) | `read` |
| `GET` | `/analytics/{creative_id}/retention` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:827`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L827) | `read` |
| `GET` | `/analytics/{creative_id}/stream` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:782`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L782) | `read` |
| `GET` | `/analytics/{post_id}` | [`Backend/api/endpoints/posted_content.py:355`](Backend/api/endpoints/posted_content.py#L355) | `read` |
| `POST` | `/analyze` | [`Backend/api/content_pipeline.py:636`](Backend/api/content_pipeline.py#L636) | `required` |
| `POST` | `/analyze` | [`Backend/api/endpoints/channel_analyzer.py:200`](Backend/api/endpoints/channel_analyzer.py#L200) | `required` |
| `POST` | `/analyze` | [`Backend/api/endpoints/content_analyzer_api.py:60`](Backend/api/endpoints/content_analyzer_api.py#L60) | `required` |
| `POST` | `/analyze` | [`Backend/api/endpoints/influencer_analysis.py:48`](Backend/api/endpoints/influencer_analysis.py#L48) | `required` |
| `POST` | `/analyze` | [`Backend/api/endpoints/reeltrends.py:551`](Backend/api/endpoints/reeltrends.py#L551) | `required` |
| `POST` | `/analyze` | [`Backend/api/endpoints/review.py:71`](Backend/api/endpoints/review.py#L71) | `required` |
| `POST` | `/analyze` | [`Backend/api/endpoints/strategic_analysis.py:50`](Backend/api/endpoints/strategic_analysis.py#L50) | `required` |
| `POST` | `/analyze` | [`Backend/api/endpoints/video_routing_api.py:61`](Backend/api/endpoints/video_routing_api.py#L61) | `required` |
| `POST` | `/analyze` | [`Backend/api/image_analysis.py:733`](Backend/api/image_analysis.py#L733) | `required` |
| `POST` | `/analyze-and-route` | [`Backend/api/endpoints/video_routing_api.py:140`](Backend/api/endpoints/video_routing_api.py#L140) | `required` |
| `POST` | `/analyze-file` | [`Backend/api/endpoints/analysis.py:67`](Backend/api/endpoints/analysis.py#L67) | `required` |
| `POST` | `/analyze-message` | [`Backend/api/endpoints/relationship_crm.py:462`](Backend/api/endpoints/relationship_crm.py#L462) | `required` |
| `POST` | `/analyze-sentiment` | [`Backend/api/endpoints/batch_analysis.py:56`](Backend/api/endpoints/batch_analysis.py#L56) | `required` |
| `POST` | `/analyze-sentiment` | [`Backend/api/endpoints/inbox.py:291`](Backend/api/endpoints/inbox.py#L291) | `required` |
| `POST` | `/analyze-sentiment/batch` | [`Backend/api/ai_curation.py:196`](Backend/api/ai_curation.py#L196) | `required` |
| `GET` | `/analyze-sentiment/status/{job_id}` | [`Backend/api/ai_curation.py:270`](Backend/api/ai_curation.py#L270) | `read` |
| `POST` | `/analyze-single/{media_id}` | [`Backend/api/endpoints/batch_analysis.py:168`](Backend/api/endpoints/batch_analysis.py#L168) | `required` |
| `POST` | `/analyze-upload` | [`Backend/api/image_analysis.py:875`](Backend/api/image_analysis.py#L875) | `required` |
| `POST` | `/analyze-videos` | [`Backend/api/endpoints/batch_analysis.py:29`](Backend/api/endpoints/batch_analysis.py#L29) | `required` |
| `POST` | `/analyze/batch` | [`Backend/api/endpoints/content_analyzer_api.py:271`](Backend/api/endpoints/content_analyzer_api.py#L271) | `required` |
| `POST` | `/analyze/from-media/{media_id}` | [`Backend/api/endpoints/content_analyzer_api.py:204`](Backend/api/endpoints/content_analyzer_api.py#L204) | `required` |
| `POST` | `/analyze/quick` | [`Backend/api/endpoints/content_analyzer_api.py:166`](Backend/api/endpoints/content_analyzer_api.py#L166) | `required` |
| `POST` | `/analyze/sync` | [`Backend/api/endpoints/strategic_analysis.py:102`](Backend/api/endpoints/strategic_analysis.py#L102) | `required` |
| `GET` | `/analyze/{channel_id}` | [`Backend/api/endpoints/channel_analyzer.py:235`](Backend/api/endpoints/channel_analyzer.py#L235) | `read` |
| `GET` | `/analyze/{hashtag}` | [`Backend/api/endpoints/hashtag_generator_api.py:109`](Backend/api/endpoints/hashtag_generator_api.py#L109) | `read` |
| `GET` | `/analyze/{job_id}` | [`Backend/api/endpoints/content_analyzer_api.py:110`](Backend/api/endpoints/content_analyzer_api.py#L110) | `read` |
| `GET` | `/analyze/{job_id}/recommendations` | [`Backend/api/endpoints/content_analyzer_api.py:133`](Backend/api/endpoints/content_analyzer_api.py#L133) | `read` |
| `POST` | `/analyze/{media_id}` | [`Backend/api/endpoints/audio_analysis.py:102`](Backend/api/endpoints/audio_analysis.py#L102) | `required` |
| `POST` | `/analyze/{media_id}` | [`Backend/api/media_processing_db.py:1220`](Backend/api/media_processing_db.py#L1220) | `required` |
| `POST` | `/anti-spam` | [`Backend/api/endpoints/sfx_library.py:280`](Backend/api/endpoints/sfx_library.py#L280) | `required` |
| `GET` | `/api-usage/can-call` | [`Backend/api/endpoints/posted_content.py:479`](Backend/api/endpoints/posted_content.py#L479) | `read` |
| `GET` | `/api-usage/endpoints` | [`Backend/api/endpoints/posted_content.py:529`](Backend/api/endpoints/posted_content.py#L529) | `read` |
| `GET` | `/api-usage/providers` | [`Backend/api/endpoints/posted_content.py:693`](Backend/api/endpoints/posted_content.py#L693) | `read` |
| `POST` | `/api-usage/set-tier` | [`Backend/api/endpoints/posted_content.py:501`](Backend/api/endpoints/posted_content.py#L501) | `required` |
| `GET` | `/api-usage/summary` | [`Backend/api/endpoints/posted_content.py:454`](Backend/api/endpoints/posted_content.py#L454) | `read` |
| `GET` | `/api/agents/feed` | [`Backend/api/endpoints/orchestrator_goals.py:263`](Backend/api/endpoints/orchestrator_goals.py#L263) | `read` |
| `GET` | `/api/health` | [`Backend/main.py:847`](Backend/main.py#L847) | `read` |
| `GET` | `/api/media-db` | [`Backend/main.py:1699`](Backend/main.py#L1699) | `read` |
| `GET` | `/api/media/video/{video_id}` | [`Backend/main.py:783`](Backend/main.py#L783) | `read` |
| `POST` | `/api/orchestrator/budget/record-spend` | [`Backend/api/endpoints/orchestrator_goals.py:250`](Backend/api/endpoints/orchestrator_goals.py#L250) | `required` |
| `GET` | `/api/orchestrator/budget/status` | [`Backend/api/endpoints/orchestrator_goals.py:228`](Backend/api/endpoints/orchestrator_goals.py#L228) | `read` |
| `POST` | `/api/orchestrator/goals/decompose` | [`Backend/api/endpoints/orchestrator_goals.py:78`](Backend/api/endpoints/orchestrator_goals.py#L78) | `required` |
| `POST` | `/api/orchestrator/goals/{goal_id}/actuals` | [`Backend/api/endpoints/orchestrator_goals.py:112`](Backend/api/endpoints/orchestrator_goals.py#L112) | `required` |
| `GET` | `/api/orchestrator/goals/{goal_id}/status` | [`Backend/api/endpoints/orchestrator_goals.py:95`](Backend/api/endpoints/orchestrator_goals.py#L95) | `read` |
| `GET` | `/api/orchestrator/learnings` | [`Backend/api/endpoints/orchestrator_goals.py:128`](Backend/api/endpoints/orchestrator_goals.py#L128) | `read` |
| `POST` | `/api/orchestrator/pipeline/record` | [`Backend/api/endpoints/orchestrator_goals.py:143`](Backend/api/endpoints/orchestrator_goals.py#L143) | `required` |
| `POST` | `/api/orchestrator/pipeline/variants` | [`Backend/api/endpoints/orchestrator_goals.py:165`](Backend/api/endpoints/orchestrator_goals.py#L165) | `required` |
| `GET` | `/api/videos` | [`Backend/quickstart.py:77`](Backend/quickstart.py#L77) | `read` |
| `GET` | `/api/videos/scan` | [`Backend/quickstart.py:44`](Backend/quickstart.py#L44) | `read` |
| `GET` | `/api/videos/{video_id}` | [`Backend/quickstart.py:82`](Backend/quickstart.py#L82) | `read` |
| `GET` | `/api/videos/{video_id}/info` | [`Backend/quickstart.py:100`](Backend/quickstart.py#L100) | `read` |
| `GET` | `/applicable-rules` | [`Backend/api/endpoints/narrative_builder.py:1349`](Backend/api/endpoints/narrative_builder.py#L1349) | `read` |
| `POST` | `/approval/submit` | [`Backend/api/endpoints/adaptive_scheduler.py:657`](Backend/api/endpoints/adaptive_scheduler.py#L657) | `required` |
| `POST` | `/approve` | [`Backend/api/content_pipeline.py:321`](Backend/api/content_pipeline.py#L321) | `required` |
| `POST` | `/approve-bulk` | [`Backend/api/comment_automation.py:632`](Backend/api/comment_automation.py#L632) | `required` |
| `POST` | `/approve/{comment_id}` | [`Backend/api/comment_automation.py:608`](Backend/api/comment_automation.py#L608) | `required` |
| `GET` | `/appstore/categories` | [`Backend/api/endpoints/trends.py:386`](Backend/api/endpoints/trends.py#L386) | `read` |
| `GET` | `/appstore/rankings` | [`Backend/api/endpoints/trends.py:337`](Backend/api/endpoints/trends.py#L337) | `read` |
| `POST` | `/appstore/rankings` | [`Backend/api/endpoints/trends.py:365`](Backend/api/endpoints/trends.py#L365) | `required` |
| `POST` | `/assess` | [`Backend/api/endpoints/voice_cloning_quality.py:46`](Backend/api/endpoints/voice_cloning_quality.py#L46) | `required` |
| `POST` | `/assess-batch` | [`Backend/api/endpoints/voice_cloning_quality.py:131`](Backend/api/endpoints/voice_cloning_quality.py#L131) | `required` |
| `GET` | `/asset/{asset_id}` | [`Backend/api/endpoints/media_assets.py:336`](Backend/api/endpoints/media_assets.py#L336) | `read` |
| `GET` | `/assets` | [`Backend/api/endpoints/vault_api.py:203`](Backend/api/endpoints/vault_api.py#L203) | `read` |
| `POST` | `/assets` | [`Backend/api/endpoints/vault_api.py:221`](Backend/api/endpoints/vault_api.py#L221) | `required` |
| `GET` | `/assets/broll` | [`Backend/api/explainer_video.py:370`](Backend/api/explainer_video.py#L370) | `read` |
| `POST` | `/assets/generate-image` | [`Backend/api/explainer_video.py:449`](Backend/api/explainer_video.py#L449) | `required` |
| `GET` | `/assets/memes` | [`Backend/api/explainer_video.py:426`](Backend/api/explainer_video.py#L426) | `read` |
| `GET` | `/assets/music` | [`Backend/api/explainer_video.py:342`](Backend/api/explainer_video.py#L342) | `read` |
| `POST` | `/assets/scan` | [`Backend/api/endpoints/vault_api.py:322`](Backend/api/endpoints/vault_api.py#L322) | `required` |
| `GET` | `/assets/sfx` | [`Backend/api/explainer_video.py:398`](Backend/api/explainer_video.py#L398) | `read` |
| `DELETE` | `/assets/{asset_id}` | [`Backend/api/endpoints/vault_api.py:313`](Backend/api/endpoints/vault_api.py#L313) | `required` |
| `GET` | `/assets/{asset_id}` | [`Backend/api/endpoints/vault_api.py:303`](Backend/api/endpoints/vault_api.py#L303) | `read` |
| `DELETE` | `/assets/{asset_id}/stage` | [`Backend/api/endpoints/vault_api.py:541`](Backend/api/endpoints/vault_api.py#L541) | `required` |
| `POST` | `/assets/{asset_id}/stage` | [`Backend/api/endpoints/vault_api.py:437`](Backend/api/endpoints/vault_api.py#L437) | `required` |
| `GET` | `/assets/{asset_id}/stage/status` | [`Backend/api/endpoints/vault_api.py:530`](Backend/api/endpoints/vault_api.py#L530) | `read` |
| `GET` | `/attributes/{post_id}` | [`Backend/api/content_intelligence.py:76`](Backend/api/content_intelligence.py#L76) | `read` |
| `GET` | `/audience` | [`Backend/api/endpoints/comment_engagement.py:822`](Backend/api/endpoints/comment_engagement.py#L822) | `read` |
| `GET` | `/audience-comparison` | [`Backend/api/analytics_compare.py:447`](Backend/api/analytics_compare.py#L447) | `read` |
| `GET` | `/audience/stats` | [`Backend/api/endpoints/comment_engagement.py:962`](Backend/api/endpoints/comment_engagement.py#L962) | `read` |
| `GET` | `/audience/top-fans` | [`Backend/api/endpoints/comment_engagement.py:908`](Backend/api/endpoints/comment_engagement.py#L908) | `read` |
| `POST` | `/audience/{member_id}/update-tier` | [`Backend/api/endpoints/comment_engagement.py:1011`](Backend/api/endpoints/comment_engagement.py#L1011) | `required` |
| `GET` | `/audio` | [`Backend/api/endpoints/trends_api.py:78`](Backend/api/endpoints/trends_api.py#L78) | `read` |
| `POST` | `/audio/mix` | [`Backend/api/endpoints/video_pipeline.py:346`](Backend/api/endpoints/video_pipeline.py#L346) | `required` |
| `GET` | `/audio/rising` | [`Backend/api/endpoints/trend_queries_api.py:445`](Backend/api/endpoints/trend_queries_api.py#L445) | `read` |
| `GET` | `/audit-report` | [`Backend/api/endpoints/competitor_api.py:1323`](Backend/api/endpoints/competitor_api.py#L1323) | `read` |
| `GET` | `/auto-curate/preview` | [`Backend/api/ai_curation.py:561`](Backend/api/ai_curation.py#L561) | `read` |
| `POST` | `/auto-curate/run` | [`Backend/api/ai_curation.py:605`](Backend/api/ai_curation.py#L605) | `required` |
| `GET` | `/auto-curate/settings` | [`Backend/api/ai_curation.py:549`](Backend/api/ai_curation.py#L549) | `read` |
| `PUT` | `/auto-curate/settings` | [`Backend/api/ai_curation.py:554`](Backend/api/ai_curation.py#L554) | `required` |
| `POST` | `/auto-detect-and-recommend` | [`Backend/api/endpoints/duplicate_detection.py:346`](Backend/api/endpoints/duplicate_detection.py#L346) | `required` |
| `POST` | `/auto-fork-now` | [`Backend/api/endpoints/template_auto_forker.py:165`](Backend/api/endpoints/template_auto_forker.py#L165) | `required` |
| `POST` | `/auto-populate` | [`Backend/api/endpoints/hook_library_api.py:393`](Backend/api/endpoints/hook_library_api.py#L393) | `required` |
| `POST` | `/auto-recycle` | [`Backend/api/content_recycling.py:91`](Backend/api/content_recycling.py#L91) | `required` |
| `POST` | `/auto-schedule` | [`Backend/api/comment_automation.py:699`](Backend/api/comment_automation.py#L699) | `required` |
| `POST` | `/auto-schedule` | [`Backend/api/content_pipeline.py:507`](Backend/api/content_pipeline.py#L507) | `required` |
| `POST` | `/auto-schedule` | [`Backend/api/endpoints/adaptive_scheduler.py:367`](Backend/api/endpoints/adaptive_scheduler.py#L367) | `required` |
| `POST` | `/auto-schedule` | [`Backend/api/endpoints/inventory_scheduler.py:121`](Backend/api/endpoints/inventory_scheduler.py#L121) | `required` |
| `POST` | `/auto-schedule` | [`Backend/api/endpoints/smart_schedule.py:43`](Backend/api/endpoints/smart_schedule.py#L43) | `required` |
| `POST` | `/auto-sleep/disable` | [`Backend/api/endpoints/cpu_monitor.py:136`](Backend/api/endpoints/cpu_monitor.py#L136) | `required` |
| `POST` | `/auto-sleep/enable` | [`Backend/api/endpoints/cpu_monitor.py:87`](Backend/api/endpoints/cpu_monitor.py#L87) | `required` |
| `POST` | `/auto-sync` | [`Backend/api/endpoints/ingestion.py:275`](Backend/api/endpoints/ingestion.py#L275) | `required` |
| `POST` | `/automate/{job_id}` | [`Backend/api/routes/sora_automation.py:124`](Backend/api/routes/sora_automation.py#L124) | `required` |
| `GET` | `/automation/rules` | [`Backend/api/endpoints/comment_engagement.py:721`](Backend/api/endpoints/comment_engagement.py#L721) | `read` |
| `POST` | `/automation/rules` | [`Backend/api/endpoints/comment_engagement.py:687`](Backend/api/endpoints/comment_engagement.py#L687) | `required` |
| `DELETE` | `/automation/rules/{rule_id}` | [`Backend/api/endpoints/comment_engagement.py:802`](Backend/api/endpoints/comment_engagement.py#L802) | `required` |
| `PATCH` | `/automation/rules/{rule_id}` | [`Backend/api/endpoints/comment_engagement.py:763`](Backend/api/endpoints/comment_engagement.py#L763) | `required` |
| `GET` | `/autonomous/backlog` | [`Backend/api/endpoints/experiments.py:2464`](Backend/api/endpoints/experiments.py#L2464) | `read` |
| `POST` | `/autonomous/enable` | [`Backend/api/endpoints/experiments.py:2426`](Backend/api/endpoints/experiments.py#L2426) | `required` |
| `POST` | `/autonomous/run-cycle` | [`Backend/api/endpoints/experiments.py:2412`](Backend/api/endpoints/experiments.py#L2412) | `required` |
| `POST` | `/autonomous/settings` | [`Backend/api/endpoints/experiments.py:2441`](Backend/api/endpoints/experiments.py#L2441) | `required` |
| `POST` | `/autonomous/start-top` | [`Backend/api/endpoints/experiments.py:2494`](Backend/api/endpoints/experiments.py#L2494) | `required` |
| `GET` | `/autonomous/status` | [`Backend/api/endpoints/experiments.py:2398`](Backend/api/endpoints/experiments.py#L2398) | `read` |
| `GET` | `/available-slots` | [`Backend/api/endpoints/smart_schedule.py:74`](Backend/api/endpoints/smart_schedule.py#L74) | `read` |
| `GET` | `/awareness` | [`Backend/api/endpoints/adaptive_scheduler.py:503`](Backend/api/endpoints/adaptive_scheduler.py#L503) | `read` |
| `POST` | `/awareness/classify` | [`Backend/api/endpoints/adaptive_scheduler.py:649`](Backend/api/endpoints/adaptive_scheduler.py#L649) | `required` |
| `POST` | `/backfill` | [`Backend/api/content_growth.py:463`](Backend/api/content_growth.py#L463) | `required` |
| `POST` | `/backfill-metadata` | [`Backend/api/media_processing_db.py:3467`](Backend/api/media_processing_db.py#L3467) | `required` |
| `GET` | `/backfill/jobs` | [`Backend/api/rapidapi_metrics.py:446`](Backend/api/rapidapi_metrics.py#L446) | `read` |
| `POST` | `/backfill/start` | [`Backend/api/rapidapi_metrics.py:396`](Backend/api/rapidapi_metrics.py#L396) | `required` |
| `GET` | `/backfill/status/{job_id}` | [`Backend/api/rapidapi_metrics.py:438`](Backend/api/rapidapi_metrics.py#L438) | `read` |
| `GET` | `/backfill/{job_id}` | [`Backend/api/content_growth.py:560`](Backend/api/content_growth.py#L560) | `read` |
| `GET` | `/background/active` | [`Backend/api/endpoints/jobs.py:141`](Backend/api/endpoints/jobs.py#L141) | `read` |
| `GET` | `/background/list` | [`Backend/api/endpoints/jobs.py:98`](Backend/api/endpoints/jobs.py#L98) | `read` |
| `GET` | `/background/{job_id}` | [`Backend/api/endpoints/jobs.py:111`](Backend/api/endpoints/jobs.py#L111) | `read` |
| `POST` | `/background/{job_id}/cancel` | [`Backend/api/endpoints/jobs.py:126`](Backend/api/endpoints/jobs.py#L126) | `required` |
| `POST` | `/backlog/add` | [`Backend/api/endpoints/experiments.py:711`](Backend/api/endpoints/experiments.py#L711) | `required` |
| `POST` | `/backlog/generate-ideas` | [`Backend/api/endpoints/experiments.py:1412`](Backend/api/endpoints/experiments.py#L1412) | `required` |
| `GET` | `/backlog/list` | [`Backend/api/endpoints/experiments.py:678`](Backend/api/endpoints/experiments.py#L678) | `read` |
| `POST` | `/backlog/{idea_id}/promote` | [`Backend/api/endpoints/experiments.py:750`](Backend/api/endpoints/experiments.py#L750) | `required` |
| `POST` | `/bandit/allocate` | [`Backend/api/endpoints/adaptive_scheduler.py:543`](Backend/api/endpoints/adaptive_scheduler.py#L543) | `required` |
| `GET` | `/batch` | [`Backend/api/content_pipeline.py:915`](Backend/api/content_pipeline.py#L915) | `read` |
| `POST` | `/batch` | [`Backend/api/endpoints/ai_titles.py:181`](Backend/api/endpoints/ai_titles.py#L181) | `required` |
| `POST` | `/batch` | [`Backend/api/endpoints/audio_analysis.py:53`](Backend/api/endpoints/audio_analysis.py#L53) | `required` |
| `POST` | `/batch` | [`Backend/api/endpoints/channel_analyzer.py:254`](Backend/api/endpoints/channel_analyzer.py#L254) | `required` |
| `POST` | `/batch` | [`Backend/api/endpoints/content_download.py:91`](Backend/api/endpoints/content_download.py#L91) | `required` |
| `POST` | `/batch` | [`Backend/api/endpoints/platform_matching.py:162`](Backend/api/endpoints/platform_matching.py#L162) | `required` |
| `POST` | `/batch` | [`Backend/api/endpoints/sora.py:119`](Backend/api/endpoints/sora.py#L119) | `required` |
| `GET` | `/batch-actions` | [`Backend/api/endpoints/relationship_crm.py:435`](Backend/api/endpoints/relationship_crm.py#L435) | `read` |
| `POST` | `/batch-analyze` | [`Backend/api/endpoints/competitor_api.py:808`](Backend/api/endpoints/competitor_api.py#L808) | `required` |
| `POST` | `/batch-analyze` | [`Backend/api/endpoints/hashtag_generator_api.py:150`](Backend/api/endpoints/hashtag_generator_api.py#L150) | `required` |
| `POST` | `/batch-check` | [`Backend/api/endpoints/content_guard.py:130`](Backend/api/endpoints/content_guard.py#L130) | `required` |
| `POST` | `/batch-fetch-posts` | [`Backend/api/endpoints/competitor_api.py:743`](Backend/api/endpoints/competitor_api.py#L743) | `required` |
| `POST` | `/batch-generate-rules` | [`Backend/api/endpoints/experiments.py:1266`](Backend/api/endpoints/experiments.py#L1266) | `required` |
| `POST` | `/batch/analyze` | [`Backend/api/media_processing_db.py:2354`](Backend/api/media_processing_db.py#L2354) | `required` |
| `GET` | `/batch/analyze/status/{job_id}` | [`Backend/api/media_processing_db.py:2567`](Backend/api/media_processing_db.py#L2567) | `read` |
| `GET` | `/batch/analyze/test-completion` | [`Backend/api/media_processing_db.py:2588`](Backend/api/media_processing_db.py#L2588) | `read` |
| `POST` | `/batch/cancel` | [`Backend/api/media_processing_db.py:2494`](Backend/api/media_processing_db.py#L2494) | `required` |
| `POST` | `/batch/cancel/{job_id}` | [`Backend/api/media_processing_db.py:2528`](Backend/api/media_processing_db.py#L2528) | `required` |
| `POST` | `/batch/create` | [`Backend/api/content_pipeline.py:853`](Backend/api/content_pipeline.py#L853) | `required` |
| `POST` | `/batch/ingest` | [`Backend/api/media_processing.py:391`](Backend/api/media_processing.py#L391) | `required` |
| `POST` | `/batch/ingest` | [`Backend/api/media_processing_db.py:1072`](Backend/api/media_processing_db.py#L1072) | `required` |
| `POST` | `/batch/resume/{job_id}` | [`Backend/api/media_processing.py:526`](Backend/api/media_processing.py#L526) | `required` |
| `GET` | `/batch/status/{job_id}` | [`Backend/api/media_processing.py:502`](Backend/api/media_processing.py#L502) | `read` |
| `GET` | `/batch/{batch_id}` | [`Backend/api/content_pipeline.py:903`](Backend/api/content_pipeline.py#L903) | `read` |
| `POST` | `/batch/{batch_id}/cancel` | [`Backend/api/content_pipeline.py:927`](Backend/api/content_pipeline.py#L927) | `required` |
| `POST` | `/beat-queries` | [`Backend/api/endpoints/broll_candidates.py:149`](Backend/api/endpoints/broll_candidates.py#L149) | `required` |
| `POST` | `/beats/extract` | [`Backend/api/endpoints/video_pipeline.py:259`](Backend/api/endpoints/video_pipeline.py#L259) | `required` |
| `GET` | `/benchmarks` | [`Backend/api/endpoints/adaptive_scheduler.py:519`](Backend/api/endpoints/adaptive_scheduler.py#L519) | `read` |
| `GET` | `/benchmarks` | [`Backend/api/endpoints/trends.py:523`](Backend/api/endpoints/trends.py#L523) | `read` |
| `POST` | `/best-match` | [`Backend/api/endpoints/sfx_library.py:403`](Backend/api/endpoints/sfx_library.py#L403) | `required` |
| `GET` | `/best-time` | [`Backend/api/endpoints/reeltrends.py:529`](Backend/api/endpoints/reeltrends.py#L529) | `read` |
| `POST` | `/best-time` | [`Backend/api/endpoints/reeltrends.py:504`](Backend/api/endpoints/reeltrends.py#L504) | `required` |
| `GET` | `/best-times` | [`Backend/api/endpoints/posting_optimizer_api.py:54`](Backend/api/endpoints/posting_optimizer_api.py#L54) | `read` |
| `POST` | `/brand-voice/{brand_id}` | [`Backend/api/endpoints/reply_suggestions.py:169`](Backend/api/endpoints/reply_suggestions.py#L169) | `required` |
| `GET` | `/breakdown` | [`Backend/api/endpoints/content_runway.py:179`](Backend/api/endpoints/content_runway.py#L179) | `read` |
| `POST` | `/brief` | [`Backend/api/endpoints/trends_agent.py:190`](Backend/api/endpoints/trends_agent.py#L190) | `required` |
| `POST` | `/brief/from-prompt` | [`Backend/api/explainer_video.py:116`](Backend/api/explainer_video.py#L116) | `required` |
| `POST` | `/brief/from-topics` | [`Backend/api/explainer_video.py:149`](Backend/api/explainer_video.py#L149) | `required` |
| `POST` | `/brief/generate` | [`Backend/api/endpoints/trend_queries_api.py:279`](Backend/api/endpoints/trend_queries_api.py#L279) | `required` |
| `POST` | `/brief/{trend_type}/{trend_id}` | [`Backend/api/endpoints/trends_api.py:686`](Backend/api/endpoints/trends_api.py#L686) | `required` |
| `GET` | `/briefs` | [`Backend/api/content_intelligence.py:31`](Backend/api/content_intelligence.py#L31) | `read` |
| `GET` | `/briefs` | [`Backend/api/endpoints/content_ideas_api.py:559`](Backend/api/endpoints/content_ideas_api.py#L559) | `read` |
| `GET` | `/briefs` | [`Backend/api/endpoints/trend_intelligence.py:241`](Backend/api/endpoints/trend_intelligence.py#L241) | `read` |
| `GET` | `/briefs` | [`Backend/api/endpoints/trends_api.py:737`](Backend/api/endpoints/trends_api.py#L737) | `read` |
| `POST` | `/briefs` | [`Backend/api/endpoints/trend_intelligence.py:207`](Backend/api/endpoints/trend_intelligence.py#L207) | `required` |
| `POST` | `/briefs` | [`Backend/api/endpoints/video_orchestrator.py:280`](Backend/api/endpoints/video_orchestrator.py#L280) | `required` |
| `POST` | `/briefs/generate` | [`Backend/api/content_intelligence.py:43`](Backend/api/content_intelligence.py#L43) | `required` |
| `GET` | `/briefs/{brief_id}` | [`Backend/api/endpoints/trend_intelligence.py:229`](Backend/api/endpoints/trend_intelligence.py#L229) | `read` |
| `GET` | `/briefs/{brief_id}` | [`Backend/api/endpoints/video_orchestrator.py:308`](Backend/api/endpoints/video_orchestrator.py#L308) | `read` |
| `PUT` | `/briefs/{brief_id}` | [`Backend/api/content_intelligence.py:52`](Backend/api/content_intelligence.py#L52) | `required` |
| `GET` | `/broll-candidates` | [`Backend/api/endpoints/format_discovery.py:39`](Backend/api/endpoints/format_discovery.py#L39) | `read` |
| `GET` | `/budgets` | [`Backend/api/endpoints/agent_panel.py:422`](Backend/api/endpoints/agent_panel.py#L422) | `read` |
| `POST` | `/budgets/{agent_type}/track` | [`Backend/api/endpoints/agent_panel.py:483`](Backend/api/endpoints/agent_panel.py#L483) | `required` |
| `POST` | `/bulk` | [`Backend/api/endpoints/publishing_queue.py:155`](Backend/api/endpoints/publishing_queue.py#L155) | `required` |
| `POST` | `/bulk-action` | [`Backend/api/approval_queue.py:377`](Backend/api/approval_queue.py#L377) | `required` |
| `POST` | `/bulk-approve` | [`Backend/api/ai_curation.py:663`](Backend/api/ai_curation.py#L663) | `required` |
| `POST` | `/bulk-approve` | [`Backend/api/content_pipeline.py:375`](Backend/api/content_pipeline.py#L375) | `required` |
| `POST` | `/bulk-deny` | [`Backend/api/ai_curation.py:714`](Backend/api/ai_curation.py#L714) | `required` |
| `POST` | `/bulk-generate` | [`Backend/api/endpoints/content_variations.py:339`](Backend/api/endpoints/content_variations.py#L339) | `required` |
| `POST` | `/bulk-schedule` | [`Backend/api/endpoints/calendar.py:204`](Backend/api/endpoints/calendar.py#L204) | `required` |
| `POST` | `/bulk-schedule` | [`Backend/api/endpoints/external_scheduling.py:415`](Backend/api/endpoints/external_scheduling.py#L415) | `required` |
| `GET` | `/by-filename/{filename}` | [`Backend/api/endpoints/media_provider.py:176`](Backend/api/endpoints/media_provider.py#L176) | `read` |
| `GET` | `/by-media/{media_id}` | [`Backend/api/endpoints/posted_content.py:207`](Backend/api/endpoints/posted_content.py#L207) | `read` |
| `GET` | `/by-media/{media_id}/fetch-metrics` | [`Backend/api/endpoints/posted_content.py:560`](Backend/api/endpoints/posted_content.py#L560) | `read` |
| `GET` | `/by-submission/{submission_id}` | [`Backend/api/endpoints/posted_content.py:175`](Backend/api/endpoints/posted_content.py#L175) | `read` |
| `PATCH` | `/by-submission/{submission_id}/url` | [`Backend/api/endpoints/posted_content.py:275`](Backend/api/endpoints/posted_content.py#L275) | `required` |
| `GET` | `/by-type` | [`Backend/api/endpoints/hook_library_api.py:76`](Backend/api/endpoints/hook_library_api.py#L76) | `read` |
| `POST` | `/cache/clear` | [`Backend/api/endpoints/media_provider.py:168`](Backend/api/endpoints/media_provider.py#L168) | `required` |
| `GET` | `/cadence` | [`Backend/api/endpoints/strategic_analysis.py:176`](Backend/api/endpoints/strategic_analysis.py#L176) | `read` |
| `POST` | `/cadence/complete` | [`Backend/api/endpoints/relationship_crm.py:648`](Backend/api/endpoints/relationship_crm.py#L648) | `required` |
| `GET` | `/cadence/daily` | [`Backend/api/endpoints/relationship_crm.py:592`](Backend/api/endpoints/relationship_crm.py#L592) | `read` |
| `GET` | `/cadence/today` | [`Backend/api/endpoints/relationship_crm.py:576`](Backend/api/endpoints/relationship_crm.py#L576) | `read` |
| `GET` | `/cadence/weekly` | [`Backend/api/endpoints/relationship_crm.py:618`](Backend/api/endpoints/relationship_crm.py#L618) | `read` |
| `GET` | `/calendar` | [`Backend/api/endpoints/adaptive_scheduler.py:834`](Backend/api/endpoints/adaptive_scheduler.py#L834) | `read` |
| `GET` | `/calendar` | [`Backend/api/endpoints/publishing.py:635`](Backend/api/endpoints/publishing.py#L635) | `read` |
| `GET` | `/calendar/month` | [`Backend/api/endpoints/schedule.py:903`](Backend/api/endpoints/schedule.py#L903) | `read` |
| `GET` | `/calendar/week` | [`Backend/api/endpoints/schedule.py:855`](Backend/api/endpoints/schedule.py#L855) | `read` |
| `GET` | `/camera-motions` | [`Backend/api/endpoints/ai_video_generation.py:741`](Backend/api/endpoints/ai_video_generation.py#L741) | `read` |
| `GET` | `/campaign/{campaign}` | [`Backend/api/endpoints/offer_tracking.py:194`](Backend/api/endpoints/offer_tracking.py#L194) | `read` |
| `GET` | `/campaign/{campaign}/platform/{platform}` | [`Backend/api/endpoints/offer_tracking.py:219`](Backend/api/endpoints/offer_tracking.py#L219) | `read` |
| `GET` | `/campaigns` | [`Backend/api/endpoints/offer_tracking.py:241`](Backend/api/endpoints/offer_tracking.py#L241) | `read` |
| `GET` | `/campaigns` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:87`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L87) | `read` |
| `POST` | `/campaigns` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:73`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L73) | `required` |
| `POST` | `/campaigns/bulk/archive` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:483`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L483) | `required` |
| `POST` | `/campaigns/bulk/pause` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:467`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L467) | `required` |
| `POST` | `/campaigns/bulk/resume` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:475`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L475) | `required` |
| `GET` | `/campaigns/{campaign_id}` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:95`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L95) | `read` |
| `GET` | `/campaigns/{campaign_id}/angle-exhaustion` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:992`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L992) | `read` |
| `POST` | `/campaigns/{campaign_id}/archive` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:413`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L413) | `required` |
| `POST` | `/campaigns/{campaign_id}/clone` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:405`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L405) | `required` |
| `GET` | `/campaigns/{campaign_id}/cross-campaign-insights` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1001`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1001) | `read` |
| `GET` | `/campaigns/{campaign_id}/diminishing-returns` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:983`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L983) | `read` |
| `POST` | `/campaigns/{campaign_id}/dry-run` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:449`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L449) | `required` |
| `GET` | `/campaigns/{campaign_id}/history` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:457`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L457) | `read` |
| `POST` | `/campaigns/{campaign_id}/pause` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:116`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L116) | `required` |
| `GET` | `/campaigns/{campaign_id}/progress` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:442`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L442) | `read` |
| `GET` | `/campaigns/{campaign_id}/report` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1012`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1012) | `read` |
| `POST` | `/campaigns/{campaign_id}/restore` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:421`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L421) | `required` |
| `POST` | `/campaigns/{campaign_id}/resume` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:127`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L127) | `required` |
| `POST` | `/campaigns/{campaign_id}/save-template` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:501`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L501) | `required` |
| `GET` | `/campaigns/{campaign_id}/score-calibration` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:972`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L972) | `read` |
| `POST` | `/campaigns/{campaign_id}/start` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:105`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L105) | `required` |
| `POST` | `/campaigns/{campaign_id}/tags` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:429`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L429) | `required` |
| `GET` | `/campaigns/{campaign_id}/winning-patterns` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:963`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L963) | `read` |
| `GET` | `/can-publish/{platform}` | [`Backend/api/endpoints/publishing_controls.py:411`](Backend/api/endpoints/publishing_controls.py#L411) | `read` |
| `DELETE` | `/cancel/{post_id}` | [`Backend/api/endpoints/post_scheduler_api.py:136`](Backend/api/endpoints/post_scheduler_api.py#L136) | `required` |
| `GET` | `/candidates` | [`Backend/api/content_recycling.py:31`](Backend/api/content_recycling.py#L31) | `read` |
| `GET` | `/candidates` | [`Backend/api/endpoints/broll.py:316`](Backend/api/endpoints/broll.py#L316) | `read` |
| `GET` | `/candidates` | [`Backend/api/endpoints/broll_candidates.py:53`](Backend/api/endpoints/broll_candidates.py#L53) | `read` |
| `GET` | `/candidates` | [`Backend/api/endpoints/broll_producer.py:312`](Backend/api/endpoints/broll_producer.py#L312) | `read` |
| `GET` | `/candidates` | [`Backend/api/endpoints/narrative_builder.py:237`](Backend/api/endpoints/narrative_builder.py#L237) | `read` |
| `GET` | `/candidates` | [`Backend/api/endpoints/template_retiree.py:62`](Backend/api/endpoints/template_retiree.py#L62) | `read` |
| `GET` | `/candidates/{video_id}/preview` | [`Backend/api/endpoints/broll_producer.py:365`](Backend/api/endpoints/broll_producer.py#L365) | `read` |
| `GET` | `/capacity` | [`Backend/api/endpoints/external_scheduling.py:814`](Backend/api/endpoints/external_scheduling.py#L814) | `read` |
| `GET` | `/captions` | [`Backend/api/endpoints/reeltrends.py:380`](Backend/api/endpoints/reeltrends.py#L380) | `read` |
| `POST` | `/captions` | [`Backend/api/endpoints/reeltrends.py:204`](Backend/api/endpoints/reeltrends.py#L204) | `required` |
| `POST` | `/capture` | [`Backend/api/endpoints/post_tracking.py:68`](Backend/api/endpoints/post_tracking.py#L68) | `required` |
| `GET` | `/cards` | [`Backend/api/endpoints/trends_api.py:376`](Backend/api/endpoints/trends_api.py#L376) | `read` |
| `POST` | `/cards/match` | [`Backend/api/endpoints/trends_api.py:422`](Backend/api/endpoints/trends_api.py#L422) | `required` |
| `POST` | `/cards/seed` | [`Backend/api/endpoints/trends_api.py:445`](Backend/api/endpoints/trends_api.py#L445) | `required` |
| `GET` | `/cards/{format_type}` | [`Backend/api/endpoints/trends_api.py:399`](Backend/api/endpoints/trends_api.py#L399) | `read` |
| `GET` | `/carousel` | [`Backend/api/endpoints/reeltrends.py:395`](Backend/api/endpoints/reeltrends.py#L395) | `read` |
| `POST` | `/carousel` | [`Backend/api/endpoints/reeltrends.py:253`](Backend/api/endpoints/reeltrends.py#L253) | `required` |
| `GET` | `/categories` | [`Backend/api/endpoints/review.py:117`](Backend/api/endpoints/review.py#L117) | `read` |
| `GET` | `/categories` | [`Backend/api/endpoints/sfx_library.py:455`](Backend/api/endpoints/sfx_library.py#L455) | `read` |
| `GET` | `/categories` | [`Backend/api/endpoints/voice_selection.py:130`](Backend/api/endpoints/voice_selection.py#L130) | `read` |
| `GET` | `/channel` | [`Backend/api/endpoints/youtube_analytics.py:21`](Backend/api/endpoints/youtube_analytics.py#L21) | `read` |
| `GET` | `/characters` | [`Backend/api/endpoints/ai_video_generation.py:779`](Backend/api/endpoints/ai_video_generation.py#L779) | `read` |
| `POST` | `/characters` | [`Backend/api/endpoints/ai_video_generation.py:819`](Backend/api/endpoints/ai_video_generation.py#L819) | `required` |
| `DELETE` | `/characters/{character_id}` | [`Backend/api/endpoints/ai_video_generation.py:867`](Backend/api/endpoints/ai_video_generation.py#L867) | `required` |
| `GET` | `/chart-data/{post_id}` | [`Backend/api/content_growth.py:615`](Backend/api/content_growth.py#L615) | `read` |
| `POST` | `/chat` | [`Backend/api/ai_chat.py:270`](Backend/api/ai_chat.py#L270) | `required` |
| `POST` | `/chat` | [`Backend/api/endpoints/coaching.py:75`](Backend/api/endpoints/coaching.py#L75) | `required` |
| `POST` | `/check` | [`Backend/api/endpoints/qa_gate.py:35`](Backend/api/endpoints/qa_gate.py#L35) | `required` |
| `GET` | `/check-before-post/{video_id}` | [`Backend/api/endpoints/posted_content_matcher.py:168`](Backend/api/endpoints/posted_content_matcher.py#L168) | `read` |
| `POST` | `/check-duplicate` | [`Backend/api/endpoints/content_guard.py:55`](Backend/api/endpoints/content_guard.py#L55) | `required` |
| `POST` | `/check-gates` | [`Backend/api/cascade_publisher.py:147`](Backend/api/cascade_publisher.py#L147) | `required` |
| `POST` | `/check-now` | [`Backend/api/endpoints/template_retiree.py:172`](Backend/api/endpoints/template_retiree.py#L172) | `required` |
| `GET` | `/check/{venv_type}` | [`Backend/api/endpoints/venv_status.py:35`](Backend/api/endpoints/venv_status.py#L35) | `read` |
| `POST` | `/checkbacks/schedule` | [`Backend/api/endpoints/adaptive_scheduler.py:770`](Backend/api/endpoints/adaptive_scheduler.py#L770) | `required` |
| `GET` | `/classify/{media_id}` | [`Backend/api/endpoints/format_discovery.py:114`](Backend/api/endpoints/format_discovery.py#L114) | `read` |
| `POST` | `/cleanup` | [`Backend/api/endpoints/backup.py:176`](Backend/api/endpoints/backup.py#L176) | `required` |
| `POST` | `/cleanup` | [`Backend/api/endpoints/storage.py:229`](Backend/api/endpoints/storage.py#L229) | `required` |
| `POST` | `/clear-and-retry/{video_id}` | [`Backend/api/endpoints/analysis_health.py:311`](Backend/api/endpoints/analysis_health.py#L311) | `required` |
| `POST` | `/clear-cache` | [`Backend/api/endpoints/instagram_trends.py:276`](Backend/api/endpoints/instagram_trends.py#L276) | `required` |
| `POST` | `/clear-cache/{api_name}` | [`Backend/api/endpoints/api_usage.py:243`](Backend/api/endpoints/api_usage.py#L243) | `required` |
| `POST` | `/click` | [`Backend/api/endpoints/offer_tracking.py:140`](Backend/api/endpoints/offer_tracking.py#L140) | `required` |
| `POST` | `/clip-plans` | [`Backend/api/endpoints/video_orchestrator.py:383`](Backend/api/endpoints/video_orchestrator.py#L383) | `required` |
| `GET` | `/clip-plans/{plan_id}` | [`Backend/api/endpoints/video_orchestrator.py:503`](Backend/api/endpoints/video_orchestrator.py#L503) | `read` |
| `POST` | `/clip-plans/{plan_id}/start` | [`Backend/api/endpoints/video_orchestrator.py:527`](Backend/api/endpoints/video_orchestrator.py#L527) | `required` |
| `GET` | `/clip-plans/{plan_id}/status` | [`Backend/api/endpoints/video_orchestrator.py:559`](Backend/api/endpoints/video_orchestrator.py#L559) | `read` |
| `GET` | `/clips` | [`Backend/api/endpoints/repurpose.py:330`](Backend/api/endpoints/repurpose.py#L330) | `read` |
| `GET` | `/clips` | [`Backend/api/endpoints/storage.py:132`](Backend/api/endpoints/storage.py#L132) | `read` |
| `POST` | `/clips/select` | [`Backend/api/endpoints/adaptive_scheduler.py:746`](Backend/api/endpoints/adaptive_scheduler.py#L746) | `required` |
| `DELETE` | `/clips/{clip_id}` | [`Backend/api/endpoints/storage.py:317`](Backend/api/endpoints/storage.py#L317) | `required` |
| `POST` | `/clips/{clip_id}/approve` | [`Backend/api/endpoints/repurpose.py:170`](Backend/api/endpoints/repurpose.py#L170) | `required` |
| `POST` | `/clips/{clip_id}/render` | [`Backend/api/endpoints/repurpose.py:200`](Backend/api/endpoints/repurpose.py#L200) | `required` |
| `GET` | `/clips/{media_id}` | [`Backend/api/endpoints/clip_extraction.py:197`](Backend/api/endpoints/clip_extraction.py#L197) | `read` |
| `GET` | `/clusters` | [`Backend/api/endpoints/trend_flash.py:54`](Backend/api/endpoints/trend_flash.py#L54) | `read` |
| `GET` | `/clusters/{cluster_id}` | [`Backend/api/endpoints/trend_flash.py:77`](Backend/api/endpoints/trend_flash.py#L77) | `read` |
| `GET` | `/collections` | [`Backend/api/endpoints/media_assets.py:283`](Backend/api/endpoints/media_assets.py#L283) | `read` |
| `POST` | `/collections` | [`Backend/api/endpoints/media_assets.py:275`](Backend/api/endpoints/media_assets.py#L275) | `required` |
| `GET` | `/collections/{collection_id}` | [`Backend/api/endpoints/media_assets.py:291`](Backend/api/endpoints/media_assets.py#L291) | `read` |
| `GET` | `/collections/{collection_id}/assets` | [`Backend/api/endpoints/media_assets.py:301`](Backend/api/endpoints/media_assets.py#L301) | `read` |
| `POST` | `/collections/{collection_id}/assets` | [`Backend/api/endpoints/media_assets.py:312`](Backend/api/endpoints/media_assets.py#L312) | `required` |
| `DELETE` | `/collections/{collection_id}/assets/{asset_id}` | [`Backend/api/endpoints/media_assets.py:322`](Backend/api/endpoints/media_assets.py#L322) | `required` |
| `POST` | `/commands` | [`Backend/control_plane/routers/commands.py:52`](Backend/control_plane/routers/commands.py#L52) | `required` |
| `POST` | `/comment` | [`Backend/api/endpoints/instagram_automation.py:85`](Backend/api/endpoints/instagram_automation.py#L85) | `required` |
| `POST` | `/comment` | [`Backend/api/endpoints/safari_automation.py:154`](Backend/api/endpoints/safari_automation.py#L154) | `required` |
| `POST` | `/comment/generate` | [`Backend/api/engagement_autopilot.py:109`](Backend/api/engagement_autopilot.py#L109) | `required` |
| `GET` | `/comments` | [`Backend/api/endpoints/comment_engagement.py:608`](Backend/api/endpoints/comment_engagement.py#L608) | `read` |
| `GET` | `/comments` | [`Backend/api/endpoints/comments.py:53`](Backend/api/endpoints/comments.py#L53) | `read` |
| `GET` | `/comments` | [`Backend/api/endpoints/tiktok_analytics.py:37`](Backend/api/endpoints/tiktok_analytics.py#L37) | `read` |
| `GET` | `/comments` | [`Backend/api/endpoints/youtube_analytics.py:221`](Backend/api/endpoints/youtube_analytics.py#L221) | `read` |
| `POST` | `/comments/collect` | [`Backend/api/endpoints/platform_publishing.py:226`](Backend/api/endpoints/platform_publishing.py#L226) | `required` |
| `POST` | `/comments/ingest` | [`Backend/api/endpoints/comment_engagement.py:377`](Backend/api/endpoints/comment_engagement.py#L377) | `required` |
| `GET` | `/comments/stats` | [`Backend/api/endpoints/comments.py:187`](Backend/api/endpoints/comments.py#L187) | `read` |
| `GET` | `/comments/{video_id}` | [`Backend/api/endpoints/youtube_analytics.py:193`](Backend/api/endpoints/youtube_analytics.py#L193) | `read` |
| `GET` | `/compare` | [`Backend/api/content_growth.py:660`](Backend/api/content_growth.py#L660) | `read` |
| `GET` | `/compare` | [`Backend/api/cross_platform_dashboard.py:71`](Backend/api/cross_platform_dashboard.py#L71) | `read` |
| `GET` | `/compare` | [`Backend/api/endpoints/competitor_api.py:993`](Backend/api/endpoints/competitor_api.py#L993) | `read` |
| `GET` | `/compare` | [`Backend/api/endpoints/multi_platform_analytics.py:207`](Backend/api/endpoints/multi_platform_analytics.py#L207) | `read` |
| `POST` | `/compare` | [`Backend/api/analytics_compare.py:346`](Backend/api/analytics_compare.py#L346) | `required` |
| `GET` | `/compare-posts` | [`Backend/api/metrics_scheduler_api.py:346`](Backend/api/metrics_scheduler_api.py#L346) | `read` |
| `GET` | `/compare-time/{account_id}` | [`Backend/api/analytics_compare.py:397`](Backend/api/analytics_compare.py#L397) | `read` |
| `GET` | `/competitor` | [`Backend/api/endpoints/adaptive_scheduler.py:511`](Backend/api/endpoints/adaptive_scheduler.py#L511) | `read` |
| `GET` | `/competitors` | [`Backend/api/endpoints/trends.py:408`](Backend/api/endpoints/trends.py#L408) | `read` |
| `POST` | `/competitors` | [`Backend/api/endpoints/trends.py:421`](Backend/api/endpoints/trends.py#L421) | `required` |
| `DELETE` | `/competitors/{competitor_id}` | [`Backend/api/endpoints/trends.py:437`](Backend/api/endpoints/trends.py#L437) | `required` |
| `GET` | `/competitors/{competitor_id}/history` | [`Backend/api/endpoints/trends.py:449`](Backend/api/endpoints/trends.py#L449) | `read` |
| `POST` | `/complete-workflow` | [`Backend/api/endpoints/thumbnails.py:336`](Backend/api/endpoints/thumbnails.py#L336) | `required` |
| `GET` | `/component/{component_name}` | [`Backend/api/endpoints/app_validation.py:78`](Backend/api/endpoints/app_validation.py#L78) | `read` |
| `POST` | `/compose/{project_id}` | [`Backend/api/endpoints/sora_pipeline.py:184`](Backend/api/endpoints/sora_pipeline.py#L184) | `required` |
| `POST` | `/compute` | [`Backend/api/endpoints/bandit.py:44`](Backend/api/endpoints/bandit.py#L44) | `required` |
| `GET` | `/config` | [`Backend/api/comment_automation.py:276`](Backend/api/comment_automation.py#L276) | `read` |
| `GET` | `/config` | [`Backend/api/endpoints/analysis_scheduler.py:122`](Backend/api/endpoints/analysis_scheduler.py#L122) | `read` |
| `GET` | `/config` | [`Backend/api/endpoints/blotato_test.py:38`](Backend/api/endpoints/blotato_test.py#L38) | `read` |
| `GET` | `/config` | [`Backend/api/endpoints/publishing_controls.py:85`](Backend/api/endpoints/publishing_controls.py#L85) | `read` |
| `GET` | `/config` | [`Backend/api/endpoints/smart_schedule.py:168`](Backend/api/endpoints/smart_schedule.py#L168) | `read` |
| `GET` | `/config` | [`Backend/api/endpoints/vault_api.py:120`](Backend/api/endpoints/vault_api.py#L120) | `read` |
| `PATCH` | `/config` | [`Backend/api/endpoints/publishing_controls.py:96`](Backend/api/endpoints/publishing_controls.py#L96) | `required` |
| `POST` | `/config` | [`Backend/api/endpoints/engagement_control.py:105`](Backend/api/endpoints/engagement_control.py#L105) | `required` |
| `PUT` | `/config` | [`Backend/api/comment_automation.py:282`](Backend/api/comment_automation.py#L282) | `required` |
| `PUT` | `/config` | [`Backend/api/endpoints/analysis_scheduler.py:129`](Backend/api/endpoints/analysis_scheduler.py#L129) | `required` |
| `PUT` | `/config` | [`Backend/api/endpoints/vault_api.py:126`](Backend/api/endpoints/vault_api.py#L126) | `required` |
| `DELETE` | `/config/niche/{niche}` | [`Backend/api/comment_automation.py:311`](Backend/api/comment_automation.py#L311) | `required` |
| `GET` | `/config/niche/{niche}` | [`Backend/api/comment_automation.py:296`](Backend/api/comment_automation.py#L296) | `read` |
| `PUT` | `/config/niche/{niche}` | [`Backend/api/comment_automation.py:304`](Backend/api/comment_automation.py#L304) | `required` |
| `GET` | `/config/niches` | [`Backend/api/comment_automation.py:290`](Backend/api/comment_automation.py#L290) | `read` |
| `POST` | `/config/pause` | [`Backend/api/endpoints/publishing_controls.py:117`](Backend/api/endpoints/publishing_controls.py#L117) | `required` |
| `PUT` | `/config/platform/{platform}` | [`Backend/api/comment_automation.py:325`](Backend/api/comment_automation.py#L325) | `required` |
| `GET` | `/config/platforms` | [`Backend/api/comment_automation.py:319`](Backend/api/comment_automation.py#L319) | `read` |
| `POST` | `/config/resume` | [`Backend/api/endpoints/publishing_controls.py:133`](Backend/api/endpoints/publishing_controls.py#L133) | `required` |
| `POST` | `/connect` | [`Backend/api/endpoints/accounts.py:175`](Backend/api/endpoints/accounts.py#L175) | `required` |
| `GET` | `/constraints` | [`Backend/api/endpoints/content_pipeline.py:81`](Backend/api/endpoints/content_pipeline.py#L81) | `read` |
| `POST` | `/constraints` | [`Backend/api/endpoints/narrative_goals.py:250`](Backend/api/endpoints/narrative_goals.py#L250) | `required` |
| `GET` | `/constraints/{platform}/{surface}` | [`Backend/api/endpoints/content_pipeline.py:134`](Backend/api/endpoints/content_pipeline.py#L134) | `read` |
| `POST` | `/contacts` | [`Backend/api/endpoints/relationship_crm.py:63`](Backend/api/endpoints/relationship_crm.py#L63) | `required` |
| `GET` | `/contacts/by-username/{platform}/{username}` | [`Backend/api/endpoints/relationship_crm.py:112`](Backend/api/endpoints/relationship_crm.py#L112) | `read` |
| `GET` | `/contacts/{contact_id}` | [`Backend/api/endpoints/relationship_crm.py:91`](Backend/api/endpoints/relationship_crm.py#L91) | `read` |
| `GET` | `/contacts/{contact_id}/3-1-rule` | [`Backend/api/endpoints/relationship_crm.py:736`](Backend/api/endpoints/relationship_crm.py#L736) | `read` |
| `POST` | `/contacts/{contact_id}/advance` | [`Backend/api/endpoints/relationship_crm.py:209`](Backend/api/endpoints/relationship_crm.py#L209) | `required` |
| `PATCH` | `/contacts/{contact_id}/context` | [`Backend/api/endpoints/relationship_crm.py:133`](Backend/api/endpoints/relationship_crm.py#L133) | `required` |
| `POST` | `/contacts/{contact_id}/detect-fit` | [`Backend/api/endpoints/relationship_crm.py:482`](Backend/api/endpoints/relationship_crm.py#L482) | `required` |
| `POST` | `/contacts/{contact_id}/interaction` | [`Backend/api/endpoints/relationship_crm.py:255`](Backend/api/endpoints/relationship_crm.py#L255) | `required` |
| `GET` | `/contacts/{contact_id}/next-action` | [`Backend/api/endpoints/relationship_crm.py:364`](Backend/api/endpoints/relationship_crm.py#L364) | `read` |
| `GET` | `/contacts/{contact_id}/offer-timing` | [`Backend/api/endpoints/relationship_crm.py:531`](Backend/api/endpoints/relationship_crm.py#L531) | `read` |
| `POST` | `/contacts/{contact_id}/suggest-reply` | [`Backend/api/endpoints/relationship_crm.py:402`](Backend/api/endpoints/relationship_crm.py#L402) | `required` |
| `POST` | `/contacts/{contact_id}/trust-signal` | [`Backend/api/endpoints/relationship_crm.py:230`](Backend/api/endpoints/relationship_crm.py#L230) | `required` |
| `POST` | `/contacts/{contact_id}/value` | [`Backend/api/endpoints/relationship_crm.py:160`](Backend/api/endpoints/relationship_crm.py#L160) | `required` |
| `GET` | `/contacts/{contact_id}/value-log` | [`Backend/api/endpoints/relationship_crm.py:189`](Backend/api/endpoints/relationship_crm.py#L189) | `read` |
| `GET` | `/content` | [`Backend/api/cross_platform_dashboard.py:62`](Backend/api/cross_platform_dashboard.py#L62) | `read` |
| `GET` | `/content` | [`Backend/api/endpoints/social_analytics.py:631`](Backend/api/endpoints/social_analytics.py#L631) | `read` |
| `GET` | `/content` | [`Backend/api/endpoints/trend_flash.py:158`](Backend/api/endpoints/trend_flash.py#L158) | `read` |
| `GET` | `/content-gaps` | [`Backend/api/endpoints/adaptive_scheduler.py:706`](Backend/api/endpoints/adaptive_scheduler.py#L706) | `read` |
| `GET` | `/content-ideas` | [`Backend/api/endpoints/inbox.py:409`](Backend/api/endpoints/inbox.py#L409) | `read` |
| `GET` | `/content-items` | [`Backend/api/endpoints/content_loop.py:65`](Backend/api/endpoints/content_loop.py#L65) | `read` |
| `POST` | `/content-items` | [`Backend/api/endpoints/content_loop.py:90`](Backend/api/endpoints/content_loop.py#L90) | `required` |
| `GET` | `/content-mapping` | [`Backend/api/endpoints/social_analytics.py:325`](Backend/api/endpoints/social_analytics.py#L325) | `read` |
| `POST` | `/content-pack` | [`Backend/api/endpoints/reeltrends.py:332`](Backend/api/endpoints/reeltrends.py#L332) | `required` |
| `GET` | `/content-stats` | [`Backend/api/endpoints/narrative_builder.py:1503`](Backend/api/endpoints/narrative_builder.py#L1503) | `read` |
| `GET` | `/content-types` | [`Backend/api/endpoints/content_mix_api.py:79`](Backend/api/endpoints/content_mix_api.py#L79) | `read` |
| `GET` | `/content-types` | [`Backend/api/endpoints/media_creation.py:39`](Backend/api/endpoints/media_creation.py#L39) | `read` |
| `GET` | `/content-types` | [`Backend/api/endpoints/platform_matching.py:230`](Backend/api/endpoints/platform_matching.py#L230) | `read` |
| `GET` | `/content-types` | [`Backend/api/endpoints/video_render.py:250`](Backend/api/endpoints/video_render.py#L250) | `read` |
| `POST` | `/content/generate` | [`Backend/api/endpoints/adaptive_scheduler.py:694`](Backend/api/endpoints/adaptive_scheduler.py#L694) | `required` |
| `GET` | `/content/leaderboard` | [`Backend/api/endpoints/social_analytics.py:700`](Backend/api/endpoints/social_analytics.py#L700) | `read` |
| `GET` | `/content/scored` | [`Backend/api/endpoints/adaptive_scheduler.py:157`](Backend/api/endpoints/adaptive_scheduler.py#L157) | `read` |
| `GET` | `/content/{content_id}` | [`Backend/api/endpoints/social_analytics.py:754`](Backend/api/endpoints/social_analytics.py#L754) | `read` |
| `GET` | `/content/{content_id}` | [`Backend/api/endpoints/trend_flash.py:177`](Backend/api/endpoints/trend_flash.py#L177) | `read` |
| `POST` | `/content/{content_id}/render` | [`Backend/api/endpoints/trend_flash.py:283`](Backend/api/endpoints/trend_flash.py#L283) | `required` |
| `GET` | `/content/{media_id}` | [`Backend/api/cross_platform_dashboard.py:53`](Backend/api/cross_platform_dashboard.py#L53) | `read` |
| `GET` | `/content/{post_id}` | [`Backend/api/content_growth.py:288`](Backend/api/content_growth.py#L288) | `read` |
| `POST` | `/context-pack` | [`Backend/api/endpoints/sfx_library.py:296`](Backend/api/endpoints/sfx_library.py#L296) | `required` |
| `GET` | `/contexts` | [`Backend/api/ai_chat.py:228`](Backend/api/ai_chat.py#L228) | `read` |
| `GET` | `/conversations` | [`Backend/api/endpoints/community_inbox.py:326`](Backend/api/endpoints/community_inbox.py#L326) | `read` |
| `POST` | `/conversion` | [`Backend/api/endpoints/offer_tracking.py:166`](Backend/api/endpoints/offer_tracking.py#L166) | `required` |
| `POST` | `/copy-plan/generate` | [`Backend/api/endpoints/content_pipeline.py:177`](Backend/api/endpoints/content_pipeline.py#L177) | `required` |
| `GET` | `/copy-plan/{copy_plan_id}` | [`Backend/api/endpoints/content_pipeline.py:233`](Backend/api/endpoints/content_pipeline.py#L233) | `read` |
| `GET` | `/copy-plans/by-asset/{asset_id}` | [`Backend/api/endpoints/content_pipeline.py:274`](Backend/api/endpoints/content_pipeline.py#L274) | `read` |
| `GET` | `/count` | [`Backend/api/endpoints/videos.py:176`](Backend/api/endpoints/videos.py#L176) | `read` |
| `GET` | `/coverage-stats` | [`Backend/api/ai_curation.py:133`](Backend/api/ai_curation.py#L133) | `read` |
| `POST` | `/crawl` | [`Backend/api/endpoints/trend_intelligence.py:903`](Backend/api/endpoints/trend_intelligence.py#L903) | `required` |
| `GET` | `/crawl/seed-accounts` | [`Backend/api/endpoints/trend_intelligence.py:945`](Backend/api/endpoints/trend_intelligence.py#L945) | `read` |
| `POST` | `/crawl/seed-accounts` | [`Backend/api/endpoints/trend_intelligence.py:929`](Backend/api/endpoints/trend_intelligence.py#L929) | `required` |
| `POST` | `/crawl/start` | [`Backend/api/endpoints/trends_api.py:470`](Backend/api/endpoints/trends_api.py#L470) | `required` |
| `POST` | `/crawl/youtube` | [`Backend/api/endpoints/trend_intelligence.py:980`](Backend/api/endpoints/trend_intelligence.py#L980) | `required` |
| `GET` | `/crawl/youtube/channels` | [`Backend/api/endpoints/trend_intelligence.py:1037`](Backend/api/endpoints/trend_intelligence.py#L1037) | `read` |
| `POST` | `/crawl/youtube/channels` | [`Backend/api/endpoints/trend_intelligence.py:1021`](Backend/api/endpoints/trend_intelligence.py#L1021) | `required` |
| `POST` | `/crawler/populate-hashtags` | [`Backend/api/endpoints/trends_api.py:833`](Backend/api/endpoints/trends_api.py#L833) | `required` |
| `POST` | `/create` | [`Backend/api/endpoints/backup.py:41`](Backend/api/endpoints/backup.py#L41) | `required` |
| `POST` | `/create` | [`Backend/api/endpoints/clip_management.py:85`](Backend/api/endpoints/clip_management.py#L85) | `required` |
| `POST` | `/create` | [`Backend/api/endpoints/content_variations.py:62`](Backend/api/endpoints/content_variations.py#L62) | `required` |
| `POST` | `/create` | [`Backend/api/endpoints/experiments.py:444`](Backend/api/endpoints/experiments.py#L444) | `required` |
| `POST` | `/create` | [`Backend/api/endpoints/formats.py:191`](Backend/api/endpoints/formats.py#L191) | `required` |
| `POST` | `/create` | [`Backend/api/endpoints/schedule.py:316`](Backend/api/endpoints/schedule.py#L316) | `required` |
| `POST` | `/create` | [`Backend/api/endpoints/video_generation.py:78`](Backend/api/endpoints/video_generation.py#L78) | `required` |
| `POST` | `/create` | [`Backend/api/endpoints/video_render.py:88`](Backend/api/endpoints/video_render.py#L88) | `required` |
| `POST` | `/create-link` | [`Backend/api/endpoints/offer_tracking.py:112`](Backend/api/endpoints/offer_tracking.py#L112) | `required` |
| `POST` | `/creatives/cleanup` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:954`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L954) | `required` |
| `GET` | `/creatives/library` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:916`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L916) | `read` |
| `GET` | `/creatives/search` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:533`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L533) | `read` |
| `GET` | `/creatives/{creative_id}` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:294`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L294) | `read` |
| `POST` | `/creatives/{creative_id}/approve` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:929`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L929) | `required` |
| `GET` | `/creatives/{creative_id}/decay-curve` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:553`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L553) | `read` |
| `POST` | `/creatives/{creative_id}/estimate-cost` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:575`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L575) | `required` |
| `GET` | `/creatives/{creative_id}/lineage` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:324`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L324) | `read` |
| `POST` | `/creatives/{creative_id}/reject` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:937`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L937) | `required` |
| `GET` | `/creatives/{creative_id}/snapshots` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:567`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L567) | `read` |
| `POST` | `/creatives/{creative_id}/submit-approval` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:947`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L947) | `required` |
| `GET` | `/creatives/{creative_id}/velocity` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:560`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L560) | `read` |
| `GET` | `/creators` | [`Backend/api/endpoints/trends.py:284`](Backend/api/endpoints/trends.py#L284) | `read` |
| `GET` | `/cross-competitor/posting-times` | [`Backend/api/endpoints/competitor_audit.py:707`](Backend/api/endpoints/competitor_audit.py#L707) | `read` |
| `GET` | `/cross-reference-summary` | [`Backend/api/endpoints/posted_content_matcher.py:213`](Backend/api/endpoints/posted_content_matcher.py#L213) | `read` |
| `POST` | `/crosspost` | [`Backend/api/endpoints/tiktok_repurpose.py:223`](Backend/api/endpoints/tiktok_repurpose.py#L223) | `required` |
| `GET` | `/crosspost/queue` | [`Backend/api/endpoints/adaptive_scheduler.py:171`](Backend/api/endpoints/adaptive_scheduler.py#L171) | `read` |
| `POST` | `/curate` | [`Backend/api/endpoints/auto_curator.py:46`](Backend/api/endpoints/auto_curator.py#L46) | `required` |
| `PUT` | `/curate/{media_id}` | [`Backend/api/media_processing_db.py:3385`](Backend/api/media_processing_db.py#L3385) | `required` |
| `POST` | `/cycle` | [`Backend/api/cascade_publisher.py:139`](Backend/api/cascade_publisher.py#L139) | `required` |
| `GET` | `/daily-digest` | [`Backend/api/endpoints/trends_agent.py:265`](Backend/api/endpoints/trends_agent.py#L265) | `read` |
| `GET` | `/daily-summary` | [`Backend/api/endpoints/publishing_controls.py:351`](Backend/api/endpoints/publishing_controls.py#L351) | `read` |
| `POST` | `/daily/sync` | [`Backend/api/endpoints/adaptive_scheduler.py:762`](Backend/api/endpoints/adaptive_scheduler.py#L762) | `required` |
| `GET` | `/dashboard` | [`Backend/api/endpoints/analytics_insights.py:99`](Backend/api/endpoints/analytics_insights.py#L99) | `read` |
| `GET` | `/dashboard` | [`Backend/api/endpoints/content_loop.py:442`](Backend/api/endpoints/content_loop.py#L442) | `read` |
| `GET` | `/dashboard` | [`Backend/api/engagement_autopilot.py:35`](Backend/api/engagement_autopilot.py#L35) | `read` |
| `GET` | `/dashboard` | [`Backend/api/trend_detection.py:35`](Backend/api/trend_detection.py#L35) | `read` |
| `GET` | `/dashboard/hypothesis-results` | [`Backend/api/endpoints/experiments.py:2088`](Backend/api/endpoints/experiments.py#L2088) | `read` |
| `GET` | `/dashboard/overview` | [`Backend/api/endpoints/experiments.py:1991`](Backend/api/endpoints/experiments.py#L1991) | `read` |
| `GET` | `/dashboard/recent-experiments` | [`Backend/api/endpoints/experiments.py:2056`](Backend/api/endpoints/experiments.py#L2056) | `read` |
| `GET` | `/dashboard/top-patterns` | [`Backend/api/endpoints/experiments.py:2121`](Backend/api/endpoints/experiments.py#L2121) | `read` |
| `GET` | `/dashboard/winner-leaderboard` | [`Backend/api/endpoints/experiments.py:2138`](Backend/api/endpoints/experiments.py#L2138) | `read` |
| `POST` | `/dco/optimize` | [`Backend/api/endpoints/adaptive_scheduler.py:609`](Backend/api/endpoints/adaptive_scheduler.py#L609) | `required` |
| `GET` | `/dead-letter` | [`Backend/api/endpoints/events.py:60`](Backend/api/endpoints/events.py#L60) | `read` |
| `POST` | `/dead-letter/clear` | [`Backend/api/endpoints/events.py:77`](Backend/api/endpoints/events.py#L77) | `required` |
| `POST` | `/dedup/check` | [`Backend/api/endpoints/adaptive_scheduler.py:730`](Backend/api/endpoints/adaptive_scheduler.py#L730) | `required` |
| `GET` | `/default-style` | [`Backend/api/subtitles.py:125`](Backend/api/subtitles.py#L125) | `read` |
| `POST` | `/demo` | [`Backend/api/endpoints/sora_pipeline.py:222`](Backend/api/endpoints/sora_pipeline.py#L222) | `required` |
| `GET` | `/detail/{media_id}` | [`Backend/api/media_processing_db.py:586`](Backend/api/media_processing_db.py#L586) | `read` |
| `GET` | `/detailed` | [`Backend/api/endpoints/backend_health.py:14`](Backend/api/endpoints/backend_health.py#L14) | `read` |
| `GET` | `/detailed` | [`Backend/api/endpoints/health.py:259`](Backend/api/endpoints/health.py#L259) | `read` |
| `POST` | `/detect` | [`Backend/api/endpoints/trend_flash.py:32`](Backend/api/endpoints/trend_flash.py#L32) | `required` |
| `POST` | `/detect` | [`Backend/api/endpoints/trends_agent.py:139`](Backend/api/endpoints/trends_agent.py#L139) | `required` |
| `POST` | `/detect-all` | [`Backend/api/endpoints/broll.py:114`](Backend/api/endpoints/broll.py#L114) | `required` |
| `POST` | `/detect-all` | [`Backend/api/endpoints/content_format.py:136`](Backend/api/endpoints/content_format.py#L136) | `required` |
| `GET` | `/detect/{video_id}` | [`Backend/api/endpoints/broll.py:36`](Backend/api/endpoints/broll.py#L36) | `read` |
| `GET` | `/detect/{video_id}` | [`Backend/api/endpoints/content_format.py:36`](Backend/api/endpoints/content_format.py#L36) | `read` |
| `POST` | `/detect/{video_id}` | [`Backend/api/endpoints/highlights.py:44`](Backend/api/endpoints/highlights.py#L44) | `required` |
| `GET` | `/device` | [`Backend/api/endpoints/android_import_api.py:141`](Backend/api/endpoints/android_import_api.py#L141) | `read` |
| `GET` | `/device` | [`Backend/api/endpoints/ios_import_api.py:117`](Backend/api/endpoints/ios_import_api.py#L117) | `read` |
| `GET` | `/dimensions` | [`Backend/api/endpoints/thumbnails.py:56`](Backend/api/endpoints/thumbnails.py#L56) | `read` |
| `POST` | `/disable` | [`Backend/api/endpoints/user_tracking.py:244`](Backend/api/endpoints/user_tracking.py#L244) | `required` |
| `POST` | `/discover` | [`Backend/api/comment_automation.py:336`](Backend/api/comment_automation.py#L336) | `required` |
| `POST` | `/discover` | [`Backend/api/endpoints/channel_analyzer.py:276`](Backend/api/endpoints/channel_analyzer.py#L276) | `required` |
| `POST` | `/discover` | [`Backend/api/endpoints/competitor_api.py:1079`](Backend/api/endpoints/competitor_api.py#L1079) | `required` |
| `POST` | `/discover` | [`Backend/api/endpoints/dm_outreach.py:153`](Backend/api/endpoints/dm_outreach.py#L153) | `required` |
| `POST` | `/discover` | [`Backend/api/endpoints/trend_intelligence.py:838`](Backend/api/endpoints/trend_intelligence.py#L838) | `required` |
| `POST` | `/discover/configure` | [`Backend/api/endpoints/trend_intelligence.py:879`](Backend/api/endpoints/trend_intelligence.py#L879) | `required` |
| `POST` | `/discover/sync` | [`Backend/api/endpoints/trend_intelligence.py:856`](Backend/api/endpoints/trend_intelligence.py#L856) | `required` |
| `GET` | `/discover/{query}` | [`Backend/api/endpoints/channel_analyzer.py:316`](Backend/api/endpoints/channel_analyzer.py#L316) | `read` |
| `DELETE` | `/discovered` | [`Backend/api/endpoints/content_sourcing.py:266`](Backend/api/endpoints/content_sourcing.py#L266) | `required` |
| `GET` | `/discovered` | [`Backend/api/endpoints/content_sourcing.py:323`](Backend/api/endpoints/content_sourcing.py#L323) | `read` |
| `POST` | `/dm` | [`Backend/api/endpoints/tiktok_automation.py:81`](Backend/api/endpoints/tiktok_automation.py#L81) | `required` |
| `POST` | `/dm` | [`Backend/api/endpoints/twitter_automation.py:67`](Backend/api/endpoints/twitter_automation.py#L67) | `required` |
| `GET` | `/dm/conversations` | [`Backend/api/endpoints/twitter_posting.py:270`](Backend/api/endpoints/twitter_posting.py#L270) | `read` |
| `POST` | `/dm/coordinate` | [`Backend/api/endpoints/adaptive_scheduler.py:354`](Backend/api/endpoints/adaptive_scheduler.py#L354) | `required` |
| `GET` | `/dm/outreach` | [`Backend/api/endpoints/adaptive_scheduler.py:343`](Backend/api/endpoints/adaptive_scheduler.py#L343) | `read` |
| `POST` | `/dm/send` | [`Backend/api/endpoints/twitter_posting.py:316`](Backend/api/endpoints/twitter_posting.py#L316) | `required` |
| `GET` | `/dm/{username}` | [`Backend/api/endpoints/twitter_posting.py:290`](Backend/api/endpoints/twitter_posting.py#L290) | `read` |
| `GET` | `/docker` | [`Backend/api/endpoints/db_health.py:168`](Backend/api/endpoints/db_health.py#L168) | `read` |
| `POST` | `/download` | [`Backend/api/endpoints/tiktok_repurpose.py:140`](Backend/api/endpoints/tiktok_repurpose.py#L140) | `required` |
| `GET` | `/download/{audio_id}` | [`Backend/api/endpoints/audio_api.py:110`](Backend/api/endpoints/audio_api.py#L110) | `read` |
| `GET` | `/download/{filename}` | [`Backend/api/endpoints/backup.py:122`](Backend/api/endpoints/backup.py#L122) | `read` |
| `GET` | `/downloads` | [`Backend/api/endpoints/media_assets.py:353`](Backend/api/endpoints/media_assets.py#L353) | `read` |
| `GET` | `/downloads` | [`Backend/api/endpoints/sora.py:255`](Backend/api/endpoints/sora.py#L255) | `read` |
| `GET` | `/due-actions` | [`Backend/api/endpoints/relationship_crm.py:325`](Backend/api/endpoints/relationship_crm.py#L325) | `read` |
| `GET` | `/duplicates` | [`Backend/api/ai_curation.py:323`](Backend/api/ai_curation.py#L323) | `read` |
| `POST` | `/duplicates/delete` | [`Backend/api/ai_curation.py:470`](Backend/api/ai_curation.py#L470) | `required` |
| `GET` | `/durations` | [`Backend/api/endpoints/content_mix_api.py:62`](Backend/api/endpoints/content_mix_api.py#L62) | `read` |
| `POST` | `/edit/{comment_id}` | [`Backend/api/comment_automation.py:663`](Backend/api/comment_automation.py#L663) | `required` |
| `GET` | `/effectiveness` | [`Backend/api/endpoints/hook_library_api.py:327`](Backend/api/endpoints/hook_library_api.py#L327) | `read` |
| `POST` | `/email/trigger` | [`Backend/api/endpoints/adaptive_scheduler.py:814`](Backend/api/endpoints/adaptive_scheduler.py#L814) | `required` |
| `POST` | `/embed/batch` | [`Backend/api/endpoints/semantic_search.py:301`](Backend/api/endpoints/semantic_search.py#L301) | `required` |
| `POST` | `/embed/competitor` | [`Backend/api/endpoints/semantic_search.py:375`](Backend/api/endpoints/semantic_search.py#L375) | `required` |
| `POST` | `/embed/text` | [`Backend/api/endpoints/semantic_search.py:263`](Backend/api/endpoints/semantic_search.py#L263) | `required` |
| `POST` | `/embed/video` | [`Backend/api/endpoints/semantic_search.py:334`](Backend/api/endpoints/semantic_search.py#L334) | `required` |
| `POST` | `/embeddings/generate` | [`Backend/api/endpoints/adaptive_scheduler.py:786`](Backend/api/endpoints/adaptive_scheduler.py#L786) | `required` |
| `GET` | `/emerging` | [`Backend/api/endpoints/trends_agent.py:336`](Backend/api/endpoints/trends_agent.py#L336) | `read` |
| `POST` | `/enable` | [`Backend/api/endpoints/user_tracking.py:227`](Backend/api/endpoints/user_tracking.py#L227) | `required` |
| `GET` | `/engagement-timing` | [`Backend/api/endpoints/competitor_api.py:1261`](Backend/api/endpoints/competitor_api.py#L1261) | `read` |
| `POST` | `/engagement/trigger` | [`Backend/api/endpoints/adaptive_scheduler.py:617`](Backend/api/endpoints/adaptive_scheduler.py#L617) | `required` |
| `POST` | `/enhance-prompt` | [`Backend/api/endpoints/analytics_feedback.py:151`](Backend/api/endpoints/analytics_feedback.py#L151) | `required` |
| `POST` | `/enhance-with-ai` | [`Backend/api/endpoints/thumbnails.py:286`](Backend/api/endpoints/thumbnails.py#L286) | `required` |
| `GET` | `/enriched` | [`Backend/api/endpoints/accounts.py:714`](Backend/api/endpoints/accounts.py#L714) | `read` |
| `POST` | `/enter` | [`Backend/api/endpoints/sleep.py:67`](Backend/api/endpoints/sleep.py#L67) | `required` |
| `POST` | `/error` | [`Backend/api/endpoints/user_tracking.py:322`](Backend/api/endpoints/user_tracking.py#L322) | `required` |
| `GET` | `/errors` | [`Backend/api/endpoints/backend_health.py:24`](Backend/api/endpoints/backend_health.py#L24) | `read` |
| `GET` | `/errors/summary` | [`Backend/api/endpoints/backend_health.py:35`](Backend/api/endpoints/backend_health.py#L35) | `read` |
| `POST` | `/event` | [`Backend/api/endpoints/email.py:147`](Backend/api/endpoints/email.py#L147) | `required` |
| `POST` | `/event` | [`Backend/api/endpoints/user_tracking.py:34`](Backend/api/endpoints/user_tracking.py#L34) | `required` |
| `GET` | `/event-names` | [`Backend/api/endpoints/user_tracking.py:176`](Backend/api/endpoints/user_tracking.py#L176) | `read` |
| `GET` | `/events` | [`Backend/api/endpoints/event_history.py:42`](Backend/api/endpoints/event_history.py#L42) | `read` |
| `GET` | `/events` | [`Backend/api/endpoints/user_tracking.py:76`](Backend/api/endpoints/user_tracking.py#L76) | `read` |
| `GET` | `/events/name/{event_name}` | [`Backend/api/endpoints/user_tracking.py:142`](Backend/api/endpoints/user_tracking.py#L142) | `read` |
| `GET` | `/events/stream` | [`Backend/control_plane/routers/events.py:21`](Backend/control_plane/routers/events.py#L21) | `read` |
| `GET` | `/events/user/{user_id}` | [`Backend/api/endpoints/user_tracking.py:108`](Backend/api/endpoints/user_tracking.py#L108) | `read` |
| `GET` | `/events/{event_id}` | [`Backend/api/endpoints/event_history.py:151`](Backend/api/endpoints/event_history.py#L151) | `read` |
| `POST` | `/events/{event_id}/replay` | [`Backend/api/endpoints/event_history.py:255`](Backend/api/endpoints/event_history.py#L255) | `required` |
| `GET` | `/exact` | [`Backend/api/endpoints/duplicate_detection.py:206`](Backend/api/endpoints/duplicate_detection.py#L206) | `read` |
| `POST` | `/execute` | [`Backend/api/endpoints/pipeline.py:47`](Backend/api/endpoints/pipeline.py#L47) | `required` |
| `POST` | `/execute` | [`Backend/api/endpoints/video_pipeline.py:204`](Backend/api/endpoints/video_pipeline.py#L204) | `required` |
| `DELETE` | `/execute-deletion` | [`Backend/api/endpoints/duplicate_detection.py:461`](Backend/api/endpoints/duplicate_detection.py#L461) | `required` |
| `GET` | `/executions` | [`Backend/api/endpoints/autonomous_executor.py:110`](Backend/api/endpoints/autonomous_executor.py#L110) | `read` |
| `GET` | `/experiment-accounts` | [`Backend/api/endpoints/experiments.py:292`](Backend/api/endpoints/experiments.py#L292) | `read` |
| `GET` | `/experiment-runner/timeline` | [`Backend/api/endpoints/agent_panel.py:157`](Backend/api/endpoints/agent_panel.py#L157) | `read` |
| `GET` | `/export` | [`Backend/api/endpoints/strategy_report_api.py:214`](Backend/api/endpoints/strategy_report_api.py#L214) | `read` |
| `POST` | `/export` | [`Backend/api/endpoints/content_ingestion.py:245`](Backend/api/endpoints/content_ingestion.py#L245) | `required` |
| `POST` | `/export/verify` | [`Backend/api/endpoints/content_ingestion.py:287`](Backend/api/endpoints/content_ingestion.py#L287) | `required` |
| `POST` | `/extract` | [`Backend/api/endpoints/clip_extraction.py:85`](Backend/api/endpoints/clip_extraction.py#L85) | `required` |
| `POST` | `/extract` | [`Backend/api/endpoints/video_toolkit.py:105`](Backend/api/endpoints/video_toolkit.py#L105) | `required` |
| `POST` | `/extract-and-push` | [`Backend/api/endpoints/video_toolkit.py:166`](Backend/api/endpoints/video_toolkit.py#L166) | `required` |
| `POST` | `/extract/{username}` | [`Backend/api/endpoints/hook_library_api.py:165`](Backend/api/endpoints/hook_library_api.py#L165) | `required` |
| `GET` | `/facebook` | [`Backend/api/endpoints/rapidapi_comments.py:152`](Backend/api/endpoints/rapidapi_comments.py#L152) | `read` |
| `GET` | `/facebook/all` | [`Backend/api/endpoints/rapidapi_comments.py:171`](Backend/api/endpoints/rapidapi_comments.py#L171) | `read` |
| `GET` | `/failed` | [`Backend/api/endpoints/agent_events.py:172`](Backend/api/endpoints/agent_events.py#L172) | `read` |
| `GET` | `/failures` | [`Backend/api/endpoints/autonomous_executor.py:133`](Backend/api/endpoints/autonomous_executor.py#L133) | `read` |
| `POST` | `/fate/score` | [`Backend/api/endpoints/adaptive_scheduler.py:266`](Backend/api/endpoints/adaptive_scheduler.py#L266) | `required` |
| `GET` | `/fate/scores` | [`Backend/api/endpoints/adaptive_scheduler.py:254`](Backend/api/endpoints/adaptive_scheduler.py#L254) | `read` |
| `GET` | `/favorites` | [`Backend/api/endpoints/media_assets.py:260`](Backend/api/endpoints/media_assets.py#L260) | `read` |
| `POST` | `/favorites` | [`Backend/api/endpoints/media_assets.py:240`](Backend/api/endpoints/media_assets.py#L240) | `required` |
| `DELETE` | `/favorites/{asset_id}` | [`Backend/api/endpoints/media_assets.py:250`](Backend/api/endpoints/media_assets.py#L250) | `required` |
| `GET` | `/favorites/{asset_id}/status` | [`Backend/api/endpoints/media_assets.py:268`](Backend/api/endpoints/media_assets.py#L268) | `read` |
| `GET` | `/feed` | [`Backend/api/endpoints/instagram_trends.py:88`](Backend/api/endpoints/instagram_trends.py#L88) | `read` |
| `POST` | `/fetch` | [`Backend/api/endpoints/audio_api.py:49`](Backend/api/endpoints/audio_api.py#L49) | `required` |
| `POST` | `/fetch` | [`Backend/api/endpoints/community_inbox.py:306`](Backend/api/endpoints/community_inbox.py#L306) | `required` |
| `POST` | `/fetch` | [`Backend/api/endpoints/tiktok_repurpose.py:98`](Backend/api/endpoints/tiktok_repurpose.py#L98) | `required` |
| `POST` | `/fetch-all` | [`Backend/api/endpoints/social_data_fetcher.py:35`](Backend/api/endpoints/social_data_fetcher.py#L35) | `required` |
| `POST` | `/fetch-platform/{platform}` | [`Backend/api/endpoints/social_data_fetcher.py:294`](Backend/api/endpoints/social_data_fetcher.py#L294) | `required` |
| `GET` | `/fetch-status` | [`Backend/api/endpoints/social_data_fetcher.py:239`](Backend/api/endpoints/social_data_fetcher.py#L239) | `read` |
| `POST` | `/fetch/batch` | [`Backend/api/endpoints/instagram_api.py:300`](Backend/api/endpoints/instagram_api.py#L300) | `required` |
| `GET` | `/fetch/comments/{platform}/{post_id}` | [`Backend/api/endpoints/data_orchestrator.py:111`](Backend/api/endpoints/data_orchestrator.py#L111) | `read` |
| `GET` | `/fetch/posts/{platform}/{username}` | [`Backend/api/endpoints/data_orchestrator.py:90`](Backend/api/endpoints/data_orchestrator.py#L90) | `read` |
| `GET` | `/fetch/profile/{platform}/{username}` | [`Backend/api/endpoints/data_orchestrator.py:69`](Backend/api/endpoints/data_orchestrator.py#L69) | `read` |
| `POST` | `/fetch/{platform}` | [`Backend/api/endpoints/trends.py:639`](Backend/api/endpoints/trends.py#L639) | `required` |
| `GET` | `/fields` | [`Backend/api/image_analysis.py:951`](Backend/api/image_analysis.py#L951) | `read` |
| `GET` | `/file/{media_id}` | [`Backend/api/endpoints/media_provider.py:100`](Backend/api/endpoints/media_provider.py#L100) | `read` |
| `GET` | `/files/clips/{clip_id}` | [`Backend/api/endpoints/storage.py:209`](Backend/api/endpoints/storage.py#L209) | `read` |
| `GET` | `/files/thumbnails/{video_id}` | [`Backend/api/endpoints/storage.py:189`](Backend/api/endpoints/storage.py#L189) | `read` |
| `GET` | `/files/videos/{video_id}` | [`Backend/api/endpoints/storage.py:168`](Backend/api/endpoints/storage.py#L168) | `read` |
| `GET` | `/filter` | [`Backend/api/endpoints/media_assets.py:212`](Backend/api/endpoints/media_assets.py#L212) | `read` |
| `GET` | `/filter-preview` | [`Backend/api/ai_curation.py:763`](Backend/api/ai_curation.py#L763) | `read` |
| `GET` | `/find` | [`Backend/api/endpoints/duplicate_detection.py:167`](Backend/api/endpoints/duplicate_detection.py#L167) | `read` |
| `GET` | `/find-image-duplicates` | [`Backend/api/endpoints/duplicate_detection.py:22`](Backend/api/endpoints/duplicate_detection.py#L22) | `read` |
| `GET` | `/followers` | [`Backend/api/endpoints/social_analytics.py:910`](Backend/api/endpoints/social_analytics.py#L910) | `read` |
| `GET` | `/followers/leaderboard` | [`Backend/api/endpoints/social_analytics.py:845`](Backend/api/endpoints/social_analytics.py#L845) | `read` |
| `GET` | `/followers/{follower_id}` | [`Backend/api/endpoints/social_analytics.py:998`](Backend/api/endpoints/social_analytics.py#L998) | `read` |
| `GET` | `/for-niche` | [`Backend/api/trend_detection.py:63`](Backend/api/trend_detection.py#L63) | `read` |
| `GET` | `/forecast` | [`Backend/api/endpoints/reeltrends.py:633`](Backend/api/endpoints/reeltrends.py#L633) | `read` |
| `POST` | `/forecast` | [`Backend/api/endpoints/reeltrends.py:601`](Backend/api/endpoints/reeltrends.py#L601) | `required` |
| `POST` | `/fork` | [`Backend/api/endpoints/template_auto_forker.py:63`](Backend/api/endpoints/template_auto_forker.py#L63) | `required` |
| `GET` | `/formats` | [`Backend/api/endpoints/captions.py:186`](Backend/api/endpoints/captions.py#L186) | `read` |
| `GET` | `/formats` | [`Backend/api/endpoints/content_format.py:332`](Backend/api/endpoints/content_format.py#L332) | `read` |
| `GET` | `/formats` | [`Backend/api/endpoints/creative_briefs.py:409`](Backend/api/endpoints/creative_briefs.py#L409) | `read` |
| `GET` | `/formats` | [`Backend/api/endpoints/instagram_trends.py:212`](Backend/api/endpoints/instagram_trends.py#L212) | `read` |
| `GET` | `/formats` | [`Backend/api/endpoints/trend_intelligence.py:382`](Backend/api/endpoints/trend_intelligence.py#L382) | `read` |
| `GET` | `/formats` | [`Backend/api/endpoints/trends.py:312`](Backend/api/endpoints/trends.py#L312) | `read` |
| `GET` | `/formats` | [`Backend/api/endpoints/trends_api.py:143`](Backend/api/endpoints/trends_api.py#L143) | `read` |
| `GET` | `/formats` | [`Backend/api/endpoints/video_format_api.py:19`](Backend/api/endpoints/video_format_api.py#L19) | `read` |
| `GET` | `/formats` | [`Backend/api/endpoints/video_pipeline.py:144`](Backend/api/endpoints/video_pipeline.py#L144) | `read` |
| `GET` | `/formats` | [`Backend/api/explainer_video.py:201`](Backend/api/explainer_video.py#L201) | `read` |
| `POST` | `/formats/classify` | [`Backend/api/endpoints/adaptive_scheduler.py:738`](Backend/api/endpoints/adaptive_scheduler.py#L738) | `required` |
| `GET` | `/formats/{format_id}` | [`Backend/api/endpoints/trend_intelligence.py:403`](Backend/api/endpoints/trend_intelligence.py#L403) | `read` |
| `GET` | `/formats/{format_id}` | [`Backend/api/endpoints/video_format_api.py:36`](Backend/api/endpoints/video_format_api.py#L36) | `read` |
| `GET` | `/formats/{format_id}` | [`Backend/api/explainer_video.py:227`](Backend/api/explainer_video.py#L227) | `read` |
| `GET` | `/formats/{format_id}/candidates` | [`Backend/api/endpoints/broll_candidates.py:194`](Backend/api/endpoints/broll_candidates.py#L194) | `read` |
| `POST` | `/frameworks/create` | [`Backend/api/endpoints/experiments.py:1962`](Backend/api/endpoints/experiments.py#L1962) | `required` |
| `POST` | `/from-transcription` | [`Backend/api/endpoints/captions.py:124`](Backend/api/endpoints/captions.py#L124) | `required` |
| `POST` | `/full-analysis/{video_id}` | [`Backend/api/endpoints/analysis.py:306`](Backend/api/endpoints/analysis.py#L306) | `required` |
| `POST` | `/full-pipeline` | [`Backend/api/endpoints/strategy_report_api.py:124`](Backend/api/endpoints/strategy_report_api.py#L124) | `required` |
| `POST` | `/full-pipeline` | [`Backend/api/endpoints/tiktok_repurpose.py:268`](Backend/api/endpoints/tiktok_repurpose.py#L268) | `required` |
| `GET` | `/funnel` | [`Backend/api/endpoints/dm_outreach.py:491`](Backend/api/endpoints/dm_outreach.py#L491) | `read` |
| `POST` | `/funnel/click` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:739`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L739) | `required` |
| `POST` | `/funnel/conversion` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:753`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L753) | `required` |
| `GET` | `/funnel/{creative_id}/stats` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:771`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L771) | `read` |
| `GET` | `/gaps` | [`Backend/api/endpoints/calendar.py:234`](Backend/api/endpoints/calendar.py#L234) | `read` |
| `POST` | `/generate` | [`Backend/api/caption_variants.py:34`](Backend/api/caption_variants.py#L34) | `required` |
| `POST` | `/generate` | [`Backend/api/comment_automation.py:490`](Backend/api/comment_automation.py#L490) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/ai_recommendations.py:26`](Backend/api/endpoints/ai_recommendations.py#L26) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/ai_titles.py:80`](Backend/api/endpoints/ai_titles.py#L80) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/ai_video.py:120`](Backend/api/endpoints/ai_video.py#L120) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/ai_video_generation.py:353`](Backend/api/endpoints/ai_video_generation.py#L353) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/briefs.py:51`](Backend/api/endpoints/briefs.py#L51) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/broll_candidates.py:84`](Backend/api/endpoints/broll_candidates.py#L84) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/captions.py:45`](Backend/api/endpoints/captions.py#L45) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/content_generation.py:26`](Backend/api/endpoints/content_generation.py#L26) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/content_ideas_api.py:198`](Backend/api/endpoints/content_ideas_api.py#L198) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/content_variations.py:243`](Backend/api/endpoints/content_variations.py#L243) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/hashtag_generator_api.py:57`](Backend/api/endpoints/hashtag_generator_api.py#L57) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/messages.py:26`](Backend/api/endpoints/messages.py#L26) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/reply_suggestions.py:88`](Backend/api/endpoints/reply_suggestions.py#L88) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/script_generation.py:35`](Backend/api/endpoints/script_generation.py#L35) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/sora.py:52`](Backend/api/endpoints/sora.py#L52) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/sora_automation.py:113`](Backend/api/endpoints/sora_automation.py#L113) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/strategy_report_api.py:34`](Backend/api/endpoints/strategy_report_api.py#L34) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/thumbnails.py:127`](Backend/api/endpoints/thumbnails.py#L127) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/tts.py:48`](Backend/api/endpoints/tts.py#L48) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/ugc_content.py:75`](Backend/api/endpoints/ugc_content.py#L75) | `required` |
| `POST` | `/generate` | [`Backend/api/endpoints/voice_cloning.py:279`](Backend/api/endpoints/voice_cloning.py#L279) | `required` |
| `POST` | `/generate` | [`Backend/api/routes/sora_automation.py:96`](Backend/api/routes/sora_automation.py#L96) | `required` |
| `POST` | `/generate` | [`Backend/routers/twitter_campaign.py:87`](Backend/routers/twitter_campaign.py#L87) | `required` |
| `POST` | `/generate` | [`Backend/routers/visual_campaign.py:38`](Backend/routers/visual_campaign.py#L38) | `required` |
| `POST` | `/generate-batch` | [`Backend/api/comment_automation.py:539`](Backend/api/comment_automation.py#L539) | `required` |
| `POST` | `/generate-brief` | [`Backend/api/endpoints/creative_briefs.py:295`](Backend/api/endpoints/creative_briefs.py#L295) | `required` |
| `POST` | `/generate-captions/{media_id}` | [`Backend/api/endpoints/analysis.py:499`](Backend/api/endpoints/analysis.py#L499) | `required` |
| `POST` | `/generate-comment` | [`Backend/api/endpoints/instagram_automation.py:120`](Backend/api/endpoints/instagram_automation.py#L120) | `required` |
| `POST` | `/generate-from-video` | [`Backend/api/endpoints/thumbnails.py:199`](Backend/api/endpoints/thumbnails.py#L199) | `required` |
| `POST` | `/generate-insights` | [`Backend/api/endpoints/analytics_feedback.py:29`](Backend/api/endpoints/analytics_feedback.py#L29) | `required` |
| `POST` | `/generate-message` | [`Backend/api/endpoints/tiktok_automation.py:116`](Backend/api/endpoints/tiktok_automation.py#L116) | `required` |
| `POST` | `/generate-message` | [`Backend/api/endpoints/twitter_automation.py:98`](Backend/api/endpoints/twitter_automation.py#L98) | `required` |
| `POST` | `/generate-preview` | [`Backend/api/endpoints/prompt_settings.py:169`](Backend/api/endpoints/prompt_settings.py#L169) | `required` |
| `POST` | `/generate-prompt` | [`Backend/api/endpoints/creative_briefs.py:368`](Backend/api/endpoints/creative_briefs.py#L368) | `required` |
| `POST` | `/generate-recommendations` | [`Backend/api/endpoints/narrative_builder.py:356`](Backend/api/endpoints/narrative_builder.py#L356) | `required` |
| `POST` | `/generate-single` | [`Backend/api/caption_variants.py:54`](Backend/api/caption_variants.py#L54) | `required` |
| `POST` | `/generate-text` | [`Backend/api/endpoints/broll_producer.py:261`](Backend/api/endpoints/broll_producer.py#L261) | `required` |
| `POST` | `/generate-thumbnails` | [`Backend/api/media_processing_db.py:3574`](Backend/api/media_processing_db.py#L3574) | `required` |
| `POST` | `/generate-thumbnails-batch` | [`Backend/api/endpoints/videos.py:835`](Backend/api/endpoints/videos.py#L835) | `required` |
| `POST` | `/generate-variations` | [`Backend/api/content_pipeline.py:573`](Backend/api/content_pipeline.py#L573) | `required` |
| `POST` | `/generate-variations` | [`Backend/api/endpoints/hook_library_api.py:141`](Backend/api/endpoints/hook_library_api.py#L141) | `required` |
| `POST` | `/generate/all-offers` | [`Backend/api/endpoints/ugc_content.py:108`](Backend/api/endpoints/ugc_content.py#L108) | `required` |
| `POST` | `/generate/batch` | [`Backend/api/endpoints/sora_automation.py:150`](Backend/api/endpoints/sora_automation.py#L150) | `required` |
| `POST` | `/generate/batch` | [`Backend/api/endpoints/voice_cloning.py:314`](Backend/api/endpoints/voice_cloning.py#L314) | `required` |
| `POST` | `/generate/quick` | [`Backend/api/endpoints/hashtag_generator_api.py:83`](Backend/api/endpoints/hashtag_generator_api.py#L83) | `required` |
| `POST` | `/generate/{cluster_id}` | [`Backend/api/endpoints/trend_flash.py:122`](Backend/api/endpoints/trend_flash.py#L122) | `required` |
| `GET` | `/generate/{generation_id}` | [`Backend/api/endpoints/voice_cloning.py:341`](Backend/api/endpoints/voice_cloning.py#L341) | `read` |
| `POST` | `/generate/{project_id}` | [`Backend/api/endpoints/sora_pipeline.py:158`](Backend/api/endpoints/sora_pipeline.py#L158) | `required` |
| `POST` | `/generate/{video_id}` | [`Backend/api/endpoints/clips.py:61`](Backend/api/endpoints/clips.py#L61) | `required` |
| `GET` | `/generations` | [`Backend/api/endpoints/ai_video.py:165`](Backend/api/endpoints/ai_video.py#L165) | `read` |
| `GET` | `/generations` | [`Backend/api/endpoints/ai_video_generation.py:430`](Backend/api/endpoints/ai_video_generation.py#L430) | `read` |
| `DELETE` | `/generations/{generation_id}` | [`Backend/api/endpoints/ai_video.py:208`](Backend/api/endpoints/ai_video.py#L208) | `required` |
| `GET` | `/generations/{generation_id}` | [`Backend/api/endpoints/ai_video.py:191`](Backend/api/endpoints/ai_video.py#L191) | `read` |
| `GET` | `/giphy/categories` | [`Backend/api/endpoints/media_assets.py:103`](Backend/api/endpoints/media_assets.py#L103) | `read` |
| `GET` | `/giphy/search` | [`Backend/api/endpoints/media_assets.py:81`](Backend/api/endpoints/media_assets.py#L81) | `read` |
| `GET` | `/giphy/trending` | [`Backend/api/endpoints/media_assets.py:95`](Backend/api/endpoints/media_assets.py#L95) | `read` |
| `GET` | `/goals` | [`Backend/api/endpoints/briefs.py:99`](Backend/api/endpoints/briefs.py#L99) | `read` |
| `GET` | `/goals` | [`Backend/api/endpoints/narrative_builder.py:608`](Backend/api/endpoints/narrative_builder.py#L608) | `read` |
| `POST` | `/goals` | [`Backend/api/endpoints/narrative_builder.py:647`](Backend/api/endpoints/narrative_builder.py#L647) | `required` |
| `POST` | `/goals` | [`Backend/api/endpoints/narrative_goals.py:59`](Backend/api/endpoints/narrative_goals.py#L59) | `required` |
| `GET` | `/goals/{goal_id}` | [`Backend/api/endpoints/narrative_goals.py:107`](Backend/api/endpoints/narrative_goals.py#L107) | `read` |
| `PATCH` | `/goals/{goal_id}` | [`Backend/api/endpoints/narrative_builder.py:700`](Backend/api/endpoints/narrative_builder.py#L700) | `required` |
| `GET` | `/goals/{goal_id}/constraints` | [`Backend/api/endpoints/narrative_goals.py:310`](Backend/api/endpoints/narrative_goals.py#L310) | `read` |
| `POST` | `/goals/{goal_id}/default-pillars` | [`Backend/api/endpoints/narrative_goals.py:208`](Backend/api/endpoints/narrative_goals.py#L208) | `required` |
| `GET` | `/goals/{goal_id}/pillars` | [`Backend/api/endpoints/narrative_goals.py:185`](Backend/api/endpoints/narrative_goals.py#L185) | `read` |
| `GET` | `/growth` | [`Backend/api/cross_platform_dashboard.py:39`](Backend/api/cross_platform_dashboard.py#L39) | `read` |
| `GET` | `/hashtag-analytics` | [`Backend/api/endpoints/competitor_api.py:1174`](Backend/api/endpoints/competitor_api.py#L1174) | `read` |
| `GET` | `/hashtag-sets` | [`Backend/api/endpoints/competitor_api.py:1704`](Backend/api/endpoints/competitor_api.py#L1704) | `read` |
| `POST` | `/hashtag-sets` | [`Backend/api/endpoints/competitor_api.py:1711`](Backend/api/endpoints/competitor_api.py#L1711) | `required` |
| `POST` | `/hashtag-sets/generate` | [`Backend/api/endpoints/competitor_api.py:1735`](Backend/api/endpoints/competitor_api.py#L1735) | `required` |
| `DELETE` | `/hashtag-sets/{set_id}` | [`Backend/api/endpoints/competitor_api.py:1823`](Backend/api/endpoints/competitor_api.py#L1823) | `required` |
| `GET` | `/hashtag/{tag}` | [`Backend/api/endpoints/instagram_api.py:201`](Backend/api/endpoints/instagram_api.py#L201) | `read` |
| `GET` | `/hashtags` | [`Backend/api/endpoints/instagram_trends.py:150`](Backend/api/endpoints/instagram_trends.py#L150) | `read` |
| `GET` | `/hashtags` | [`Backend/api/endpoints/reeltrends.py:412`](Backend/api/endpoints/reeltrends.py#L412) | `read` |
| `GET` | `/hashtags` | [`Backend/api/endpoints/trends.py:81`](Backend/api/endpoints/trends.py#L81) | `read` |
| `GET` | `/hashtags` | [`Backend/api/endpoints/trends_api.py:116`](Backend/api/endpoints/trends_api.py#L116) | `read` |
| `POST` | `/hashtags` | [`Backend/api/endpoints/reeltrends.py:299`](Backend/api/endpoints/reeltrends.py#L299) | `required` |
| `POST` | `/hashtags` | [`Backend/api/endpoints/trends.py:105`](Backend/api/endpoints/trends.py#L105) | `required` |
| `GET` | `/hashtags/top` | [`Backend/api/endpoints/social_analytics.py:596`](Backend/api/endpoints/social_analytics.py#L596) | `read` |
| `POST` | `/hashtags/top` | [`Backend/api/endpoints/trend_queries_api.py:194`](Backend/api/endpoints/trend_queries_api.py#L194) | `required` |
| `GET` | `/hashtags/{platform}/top` | [`Backend/api/endpoints/trends.py:139`](Backend/api/endpoints/trends.py#L139) | `read` |
| `GET` | `/health` | [`Backend/api/blotato_router.py:188`](Backend/api/blotato_router.py#L188) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/ai_titles.py:270`](Backend/api/endpoints/ai_titles.py#L270) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/app_config.py:26`](Backend/api/endpoints/app_config.py#L26) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/approval_queue.py:392`](Backend/api/endpoints/approval_queue.py#L392) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/audio_analysis.py:36`](Backend/api/endpoints/audio_analysis.py#L36) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/audio_api.py:36`](Backend/api/endpoints/audio_api.py#L36) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/auto_curator.py:300`](Backend/api/endpoints/auto_curator.py#L300) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/automation.py:21`](Backend/api/endpoints/automation.py#L21) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/benchmark_api.py:25`](Backend/api/endpoints/benchmark_api.py#L25) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/competitor_api.py:34`](Backend/api/endpoints/competitor_api.py#L34) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/content_gap_api.py:22`](Backend/api/endpoints/content_gap_api.py#L22) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/content_generation.py:139`](Backend/api/endpoints/content_generation.py#L139) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/content_ideas_api.py:192`](Backend/api/endpoints/content_ideas_api.py#L192) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/content_ingestion.py:321`](Backend/api/endpoints/content_ingestion.py#L321) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/cpu_monitor.py:157`](Backend/api/endpoints/cpu_monitor.py#L157) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/external_scheduling.py:550`](Backend/api/endpoints/external_scheduling.py#L550) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/hook_library_api.py:34`](Backend/api/endpoints/hook_library_api.py#L34) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/instagram_api.py:275`](Backend/api/endpoints/instagram_api.py#L275) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/instagram_trends.py:297`](Backend/api/endpoints/instagram_trends.py#L297) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/media_provider.py:16`](Backend/api/endpoints/media_provider.py#L16) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/multi_platform_analytics.py:268`](Backend/api/endpoints/multi_platform_analytics.py#L268) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/music_matching.py:62`](Backend/api/endpoints/music_matching.py#L62) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/orchestrator.py:361`](Backend/api/endpoints/orchestrator.py#L361) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/platform_matching.py:303`](Backend/api/endpoints/platform_matching.py#L303) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/post_tracking.py:240`](Backend/api/endpoints/post_tracking.py#L240) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/pubsub_inspector.py:153`](Backend/api/endpoints/pubsub_inspector.py#L153) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/qa_gate.py:103`](Backend/api/endpoints/qa_gate.py#L103) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/reply_suggestions.py:242`](Backend/api/endpoints/reply_suggestions.py#L242) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/safari_sessions.py:345`](Backend/api/endpoints/safari_sessions.py#L345) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/scheduler.py:237`](Backend/api/endpoints/scheduler.py#L237) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/semantic_search.py:88`](Backend/api/endpoints/semantic_search.py#L88) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/sleep.py:218`](Backend/api/endpoints/sleep.py#L218) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/strategy_report_api.py:22`](Backend/api/endpoints/strategy_report_api.py#L22) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/system.py:25`](Backend/api/endpoints/system.py#L25) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/trend_queries_api.py:626`](Backend/api/endpoints/trend_queries_api.py#L626) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/video_orchestrator.py:770`](Backend/api/endpoints/video_orchestrator.py#L770) | `read` |
| `GET` | `/health` | [`Backend/api/endpoints/video_routing_api.py:247`](Backend/api/endpoints/video_routing_api.py#L247) | `read` |
| `GET` | `/health` | [`Backend/api/media_processing.py:895`](Backend/api/media_processing.py#L895) | `read` |
| `GET` | `/health` | [`Backend/api/media_processing_db.py:3091`](Backend/api/media_processing_db.py#L3091) | `read` |
| `GET` | `/health` | [`Backend/main.py:811`](Backend/main.py#L811) | `read` |
| `GET` | `/health` | [`Backend/quickstart.py:111`](Backend/quickstart.py#L111) | `read` |
| `GET` | `/health` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:395`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L395) | `read` |
| `GET` | `/health-check` | [`Backend/api/endpoints/app_validation.py:103`](Backend/api/endpoints/app_validation.py#L103) | `read` |
| `GET` | `/health/detailed` | [`Backend/api/endpoints/system.py:36`](Backend/api/endpoints/system.py#L36) | `read` |
| `GET` | `/health/{api_name}` | [`Backend/api/endpoints/api_usage.py:158`](Backend/api/endpoints/api_usage.py#L158) | `read` |
| `GET` | `/healthy` | [`Backend/api/endpoints/relationship_crm.py:306`](Backend/api/endpoints/relationship_crm.py#L306) | `read` |
| `GET` | `/heatmap/{platform}` | [`Backend/api/cross_platform_dashboard.py:84`](Backend/api/cross_platform_dashboard.py#L84) | `read` |
| `GET` | `/heatmap/{platform}` | [`Backend/api/smart_posting_times.py:111`](Backend/api/smart_posting_times.py#L111) | `read` |
| `DELETE` | `/history` | [`Backend/api/endpoints/android_import_api.py:532`](Backend/api/endpoints/android_import_api.py#L532) | `required` |
| `DELETE` | `/history` | [`Backend/api/endpoints/ios_import_api.py:821`](Backend/api/endpoints/ios_import_api.py#L821) | `required` |
| `GET` | `/history` | [`Backend/api/endpoints/analysis_scheduler.py:110`](Backend/api/endpoints/analysis_scheduler.py#L110) | `read` |
| `GET` | `/history` | [`Backend/api/endpoints/android_import_api.py:522`](Backend/api/endpoints/android_import_api.py#L522) | `read` |
| `GET` | `/history` | [`Backend/api/endpoints/benchmark_api.py:122`](Backend/api/endpoints/benchmark_api.py#L122) | `read` |
| `GET` | `/history` | [`Backend/api/endpoints/instagram_automation.py:189`](Backend/api/endpoints/instagram_automation.py#L189) | `read` |
| `GET` | `/history` | [`Backend/api/endpoints/ios_import_api.py:811`](Backend/api/endpoints/ios_import_api.py#L811) | `read` |
| `GET` | `/history` | [`Backend/api/endpoints/post_scheduler_api.py:166`](Backend/api/endpoints/post_scheduler_api.py#L166) | `read` |
| `GET` | `/history` | [`Backend/api/endpoints/publishing_controls.py:362`](Backend/api/endpoints/publishing_controls.py#L362) | `read` |
| `GET` | `/history` | [`Backend/api/endpoints/sora_daily.py:548`](Backend/api/endpoints/sora_daily.py#L548) | `read` |
| `GET` | `/history` | [`Backend/api/endpoints/tiktok_automation.py:172`](Backend/api/endpoints/tiktok_automation.py#L172) | `read` |
| `GET` | `/history` | [`Backend/api/endpoints/twitter_automation.py:150`](Backend/api/endpoints/twitter_automation.py#L150) | `read` |
| `GET` | `/history` | [`Backend/api/endpoints/voice_cloning.py:366`](Backend/api/endpoints/voice_cloning.py#L366) | `read` |
| `GET` | `/history` | [`Backend/api/metrics_scheduler_api.py:155`](Backend/api/metrics_scheduler_api.py#L155) | `read` |
| `POST` | `/hooks/generate` | [`Backend/api/endpoints/competitor_audit.py:667`](Backend/api/endpoints/competitor_audit.py#L667) | `required` |
| `POST` | `/hooks/inject` | [`Backend/api/endpoints/adaptive_scheduler.py:722`](Backend/api/endpoints/adaptive_scheduler.py#L722) | `required` |
| `GET` | `/hooks/leaderboard` | [`Backend/api/endpoints/trend_queries_api.py:386`](Backend/api/endpoints/trend_queries_api.py#L386) | `read` |
| `POST` | `/hydrate` | [`Backend/api/endpoints/adaptive_scheduler.py:850`](Backend/api/endpoints/adaptive_scheduler.py#L850) | `required` |
| `GET` | `/hydrated` | [`Backend/api/endpoints/accounts.py:896`](Backend/api/endpoints/accounts.py#L896) | `read` |
| `POST` | `/identify` | [`Backend/api/endpoints/user_tracking.py:424`](Backend/api/endpoints/user_tracking.py#L424) | `required` |
| `GET` | `/image/{media_id}` | [`Backend/api/endpoints/media_provider.py:93`](Backend/api/endpoints/media_provider.py#L93) | `read` |
| `GET` | `/image/{media_id}` | [`Backend/api/media_processing_db.py:3006`](Backend/api/media_processing_db.py#L3006) | `read` |
| `GET` | `/impact` | [`Backend/api/comment_automation.py:873`](Backend/api/comment_automation.py#L873) | `read` |
| `GET` | `/impact/breakdown` | [`Backend/api/comment_automation.py:945`](Backend/api/comment_automation.py#L945) | `read` |
| `POST` | `/import` | [`Backend/api/endpoints/music_library.py:133`](Backend/api/endpoints/music_library.py#L133) | `required` |
| `POST` | `/import-iphone` | [`Backend/api/endpoints/ingestion.py:432`](Backend/api/endpoints/ingestion.py#L432) | `required` |
| `GET` | `/inbox` | [`Backend/api/endpoints/comment_engagement.py:1074`](Backend/api/endpoints/comment_engagement.py#L1074) | `read` |
| `GET` | `/industry-averages` | [`Backend/api/endpoints/benchmark_api.py:88`](Backend/api/endpoints/benchmark_api.py#L88) | `read` |
| `GET` | `/info` | [`Backend/api/endpoints/content_download.py:167`](Backend/api/endpoints/content_download.py#L167) | `read` |
| `GET` | `/info` | [`Backend/api/endpoints/content_guard.py:195`](Backend/api/endpoints/content_guard.py#L195) | `read` |
| `GET` | `/info` | [`Backend/api/endpoints/reeltrends.py:426`](Backend/api/endpoints/reeltrends.py#L426) | `read` |
| `GET` | `/info/{audio_id}` | [`Backend/api/endpoints/audio_api.py:148`](Backend/api/endpoints/audio_api.py#L148) | `read` |
| `GET` | `/info/{media_id}` | [`Backend/api/endpoints/media_provider.py:28`](Backend/api/endpoints/media_provider.py#L28) | `read` |
| `POST` | `/ingest` | [`Backend/api/endpoints/content_ingestion.py:94`](Backend/api/endpoints/content_ingestion.py#L94) | `required` |
| `POST` | `/ingest` | [`Backend/api/endpoints/content_sourcing.py:104`](Backend/api/endpoints/content_sourcing.py#L104) | `required` |
| `POST` | `/ingest` | [`Backend/api/endpoints/trend_intelligence.py:117`](Backend/api/endpoints/trend_intelligence.py#L117) | `required` |
| `POST` | `/ingest/cluster` | [`Backend/api/endpoints/trend_intelligence.py:166`](Backend/api/endpoints/trend_intelligence.py#L166) | `required` |
| `POST` | `/ingest/comment` | [`Backend/api/endpoints/people.py:213`](Backend/api/endpoints/people.py#L213) | `required` |
| `POST` | `/ingest/file` | [`Backend/api/media_processing_db.py:947`](Backend/api/media_processing_db.py#L947) | `required` |
| `POST` | `/ingest/lingo/{cluster_id}` | [`Backend/api/endpoints/trend_intelligence.py:188`](Backend/api/endpoints/trend_intelligence.py#L188) | `required` |
| `GET` | `/insights` | [`Backend/api/content_intelligence.py:23`](Backend/api/content_intelligence.py#L23) | `read` |
| `GET` | `/insights` | [`Backend/api/endpoints/adaptive_scheduler.py:478`](Backend/api/endpoints/adaptive_scheduler.py#L478) | `read` |
| `GET` | `/insights` | [`Backend/api/endpoints/coaching.py:165`](Backend/api/endpoints/coaching.py#L165) | `read` |
| `GET` | `/insights` | [`Backend/api/endpoints/content_loop.py:397`](Backend/api/endpoints/content_loop.py#L397) | `read` |
| `GET` | `/insights` | [`Backend/api/endpoints/review.py:137`](Backend/api/endpoints/review.py#L137) | `read` |
| `POST` | `/insights` | [`Backend/api/endpoints/content_loop.py:413`](Backend/api/endpoints/content_loop.py#L413) | `required` |
| `POST` | `/insights/apply` | [`Backend/api/endpoints/adaptive_scheduler.py:535`](Backend/api/endpoints/adaptive_scheduler.py#L535) | `required` |
| `GET` | `/insights/hooks` | [`Backend/api/endpoints/analytics_insights.py:166`](Backend/api/endpoints/analytics_insights.py#L166) | `read` |
| `GET` | `/insights/posting-times/{platform}` | [`Backend/api/endpoints/analytics_insights.py:199`](Backend/api/endpoints/analytics_insights.py#L199) | `read` |
| `GET` | `/insights/topics` | [`Backend/api/endpoints/analytics_insights.py:225`](Backend/api/endpoints/analytics_insights.py#L225) | `read` |
| `GET` | `/insights/types` | [`Backend/api/endpoints/channel_analyzer.py:337`](Backend/api/endpoints/channel_analyzer.py#L337) | `read` |
| `GET` | `/instagram` | [`Backend/api/endpoints/rapidapi_comments.py:69`](Backend/api/endpoints/rapidapi_comments.py#L69) | `read` |
| `GET` | `/instagram/all` | [`Backend/api/endpoints/rapidapi_comments.py:93`](Backend/api/endpoints/rapidapi_comments.py#L93) | `read` |
| `GET` | `/instagram/check-duplicate/{media_id}` | [`Backend/api/posted_media.py:607`](Backend/api/posted_media.py#L607) | `read` |
| `POST` | `/instagram/crawl` | [`Backend/api/endpoints/music_crawler.py:51`](Backend/api/endpoints/music_crawler.py#L51) | `required` |
| `GET` | `/instagram/post/{media_id}` | [`Backend/api/rapidapi_metrics.py:319`](Backend/api/rapidapi_metrics.py#L319) | `read` |
| `GET` | `/instagram/posted-media` | [`Backend/api/posted_media.py:657`](Backend/api/posted_media.py#L657) | `read` |
| `GET` | `/instagram/posts/{username}` | [`Backend/api/rapidapi_metrics.py:287`](Backend/api/rapidapi_metrics.py#L287) | `read` |
| `GET` | `/instagram/profile/{username}` | [`Backend/api/rapidapi_metrics.py:259`](Backend/api/rapidapi_metrics.py#L259) | `read` |
| `POST` | `/instagram/sync` | [`Backend/api/posted_media.py:475`](Backend/api/posted_media.py#L475) | `required` |
| `GET` | `/instagram/tracks` | [`Backend/api/endpoints/music_crawler.py:93`](Backend/api/endpoints/music_crawler.py#L93) | `read` |
| `GET` | `/integration/landing/{creative_id}/url` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:905`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L905) | `read` |
| `GET` | `/integration/oauth/accounts` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:887`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L887) | `read` |
| `POST` | `/integration/offer/{offer_id}/expire` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:896`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L896) | `required` |
| `GET` | `/intervals` | [`Backend/api/metrics_scheduler_api.py:167`](Backend/api/metrics_scheduler_api.py#L167) | `read` |
| `GET` | `/inventory` | [`Backend/api/endpoints/adaptive_scheduler.py:714`](Backend/api/endpoints/adaptive_scheduler.py#L714) | `read` |
| `GET` | `/inventory` | [`Backend/api/endpoints/inventory_scheduler.py:48`](Backend/api/endpoints/inventory_scheduler.py#L48) | `read` |
| `GET` | `/iphone-import-stats` | [`Backend/api/endpoints/ingestion.py:391`](Backend/api/endpoints/ingestion.py#L391) | `read` |
| `GET` | `/ir/formats` | [`Backend/api/endpoints/video_generation.py:293`](Backend/api/endpoints/video_generation.py#L293) | `read` |
| `GET` | `/ir/pipeline-status` | [`Backend/api/endpoints/video_generation.py:472`](Backend/api/endpoints/video_generation.py#L472) | `read` |
| `POST` | `/ir/render-plan` | [`Backend/api/endpoints/video_generation.py:426`](Backend/api/endpoints/video_generation.py#L426) | `required` |
| `POST` | `/ir/select-format` | [`Backend/api/endpoints/video_generation.py:316`](Backend/api/endpoints/video_generation.py#L316) | `required` |
| `POST` | `/ir/shot-plan` | [`Backend/api/endpoints/video_generation.py:381`](Backend/api/endpoints/video_generation.py#L381) | `required` |
| `POST` | `/ir/story-ir` | [`Backend/api/endpoints/video_generation.py:347`](Backend/api/endpoints/video_generation.py#L347) | `required` |
| `DELETE` | `/item/{item_id}` | [`Backend/api/approval_queue.py:415`](Backend/api/approval_queue.py#L415) | `required` |
| `GET` | `/item/{item_id}` | [`Backend/api/approval_queue.py:302`](Backend/api/approval_queue.py#L302) | `read` |
| `POST` | `/item/{item_id}/action` | [`Backend/api/approval_queue.py:311`](Backend/api/approval_queue.py#L311) | `required` |
| `POST` | `/item/{item_id}/resubmit` | [`Backend/api/approval_queue.py:425`](Backend/api/approval_queue.py#L425) | `required` |
| `GET` | `/item/{sfx_id}` | [`Backend/api/endpoints/sfx_library.py:436`](Backend/api/endpoints/sfx_library.py#L436) | `read` |
| `GET` | `/items` | [`Backend/api/approval_queue.py:213`](Backend/api/approval_queue.py#L213) | `read` |
| `GET` | `/items` | [`Backend/api/endpoints/content.py:78`](Backend/api/endpoints/content.py#L78) | `read` |
| `GET` | `/items` | [`Backend/api/endpoints/publishing_queue.py:172`](Backend/api/endpoints/publishing_queue.py#L172) | `read` |
| `POST` | `/items` | [`Backend/api/endpoints/approval_queue.py:75`](Backend/api/endpoints/approval_queue.py#L75) | `required` |
| `POST` | `/items` | [`Backend/api/endpoints/content.py:66`](Backend/api/endpoints/content.py#L66) | `required` |
| `GET` | `/items/pending` | [`Backend/api/endpoints/approval_queue.py:136`](Backend/api/endpoints/approval_queue.py#L136) | `read` |
| `DELETE` | `/items/{item_id}` | [`Backend/api/endpoints/approval_queue.py:329`](Backend/api/endpoints/approval_queue.py#L329) | `required` |
| `GET` | `/items/{item_id}` | [`Backend/api/endpoints/approval_queue.py:187`](Backend/api/endpoints/approval_queue.py#L187) | `read` |
| `GET` | `/items/{item_id}` | [`Backend/api/endpoints/content.py:84`](Backend/api/endpoints/content.py#L84) | `read` |
| `POST` | `/items/{item_id}/approve` | [`Backend/api/endpoints/approval_queue.py:209`](Backend/api/endpoints/approval_queue.py#L209) | `required` |
| `POST` | `/items/{item_id}/assign` | [`Backend/api/endpoints/approval_queue.py:292`](Backend/api/endpoints/approval_queue.py#L292) | `required` |
| `POST` | `/items/{item_id}/generate-variants` | [`Backend/api/endpoints/content.py:115`](Backend/api/endpoints/content.py#L115) | `required` |
| `POST` | `/items/{item_id}/reject` | [`Backend/api/endpoints/approval_queue.py:249`](Backend/api/endpoints/approval_queue.py#L249) | `required` |
| `GET` | `/items/{item_id}/variants` | [`Backend/api/endpoints/content.py:106`](Backend/api/endpoints/content.py#L106) | `read` |
| `GET` | `/job/current` | [`Backend/api/endpoints/android_import_api.py:204`](Backend/api/endpoints/android_import_api.py#L204) | `read` |
| `GET` | `/job/current` | [`Backend/api/endpoints/ios_import_api.py:272`](Backend/api/endpoints/ios_import_api.py#L272) | `read` |
| `DELETE` | `/job/{job_id}` | [`Backend/api/endpoints/ai_video_generation.py:573`](Backend/api/endpoints/ai_video_generation.py#L573) | `required` |
| `GET` | `/job/{job_id}` | [`Backend/api/endpoints/ai_video_generation.py:529`](Backend/api/endpoints/ai_video_generation.py#L529) | `read` |
| `GET` | `/job/{job_id}` | [`Backend/api/endpoints/android_import_api.py:510`](Backend/api/endpoints/android_import_api.py#L510) | `read` |
| `POST` | `/job/{job_id}/cancel` | [`Backend/api/endpoints/android_import_api.py:494`](Backend/api/endpoints/android_import_api.py#L494) | `required` |
| `POST` | `/job/{job_id}/cancel` | [`Backend/api/endpoints/ios_import_api.py:540`](Backend/api/endpoints/ios_import_api.py#L540) | `required` |
| `POST` | `/job/{job_id}/pause` | [`Backend/api/endpoints/ios_import_api.py:518`](Backend/api/endpoints/ios_import_api.py#L518) | `required` |
| `GET` | `/job/{job_id}/resilience` | [`Backend/api/endpoints/analysis_health.py:151`](Backend/api/endpoints/analysis_health.py#L151) | `read` |
| `POST` | `/job/{job_id}/resume` | [`Backend/api/endpoints/ios_import_api.py:529`](Backend/api/endpoints/ios_import_api.py#L529) | `required` |
| `GET` | `/jobs` | [`Backend/api/endpoints/clip_extraction.py:166`](Backend/api/endpoints/clip_extraction.py#L166) | `read` |
| `GET` | `/jobs` | [`Backend/api/endpoints/remotion.py:188`](Backend/api/endpoints/remotion.py#L188) | `read` |
| `GET` | `/jobs` | [`Backend/api/endpoints/sora.py:197`](Backend/api/endpoints/sora.py#L197) | `read` |
| `GET` | `/jobs` | [`Backend/api/endpoints/sora_daily.py:161`](Backend/api/endpoints/sora_daily.py#L161) | `read` |
| `GET` | `/jobs` | [`Backend/api/endpoints/trend_intelligence.py:557`](Backend/api/endpoints/trend_intelligence.py#L557) | `read` |
| `GET` | `/jobs` | [`Backend/api/endpoints/video_generation.py:169`](Backend/api/endpoints/video_generation.py#L169) | `read` |
| `GET` | `/jobs` | [`Backend/api/endpoints/video_render.py:231`](Backend/api/endpoints/video_render.py#L231) | `read` |
| `GET` | `/jobs` | [`Backend/api/endpoints/youtube_automation.py:72`](Backend/api/endpoints/youtube_automation.py#L72) | `read` |
| `GET` | `/jobs` | [`Backend/api/routes/sora_automation.py:66`](Backend/api/routes/sora_automation.py#L66) | `read` |
| `GET` | `/jobs` | [`Backend/control_plane/routers/jobs.py:41`](Backend/control_plane/routers/jobs.py#L41) | `read` |
| `POST` | `/jobs` | [`Backend/api/endpoints/trend_intelligence.py:534`](Backend/api/endpoints/trend_intelligence.py#L534) | `required` |
| `POST` | `/jobs/aggregate-rollups` | [`Backend/api/endpoints/content.py:173`](Backend/api/endpoints/content.py#L173) | `required` |
| `GET` | `/jobs/pending` | [`Backend/api/endpoints/sora_daily.py:181`](Backend/api/endpoints/sora_daily.py#L181) | `read` |
| `POST` | `/jobs/poll-metrics` | [`Backend/api/endpoints/content.py:167`](Backend/api/endpoints/content.py#L167) | `required` |
| `POST` | `/jobs/process/{queue_name}` | [`Backend/api/endpoints/trend_intelligence.py:596`](Backend/api/endpoints/trend_intelligence.py#L596) | `required` |
| `GET` | `/jobs/stats` | [`Backend/api/endpoints/trend_intelligence.py:581`](Backend/api/endpoints/trend_intelligence.py#L581) | `read` |
| `GET` | `/jobs/status` | [`Backend/api/endpoints/ai_video_generation.py:491`](Backend/api/endpoints/ai_video_generation.py#L491) | `read` |
| `DELETE` | `/jobs/{job_id}` | [`Backend/api/endpoints/clip_extraction.py:242`](Backend/api/endpoints/clip_extraction.py#L242) | `required` |
| `DELETE` | `/jobs/{job_id}` | [`Backend/api/endpoints/sora.py:214`](Backend/api/endpoints/sora.py#L214) | `required` |
| `GET` | `/jobs/{job_id}` | [`Backend/api/endpoints/clip_extraction.py:186`](Backend/api/endpoints/clip_extraction.py#L186) | `read` |
| `GET` | `/jobs/{job_id}` | [`Backend/api/endpoints/youtube_automation.py:81`](Backend/api/endpoints/youtube_automation.py#L81) | `read` |
| `GET` | `/jobs/{job_id}` | [`Backend/api/routes/sora_automation.py:84`](Backend/api/routes/sora_automation.py#L84) | `read` |
| `GET` | `/jobs/{job_id}` | [`Backend/control_plane/routers/jobs.py:26`](Backend/control_plane/routers/jobs.py#L26) | `read` |
| `POST` | `/jobs/{job_id}/cancel` | [`Backend/control_plane/routers/jobs.py:102`](Backend/control_plane/routers/jobs.py#L102) | `required` |
| `GET` | `/jobs/{job_id}/events` | [`Backend/control_plane/routers/jobs.py:73`](Backend/control_plane/routers/jobs.py#L73) | `read` |
| `POST` | `/jobs/{job_id}/retry` | [`Backend/api/endpoints/sora_daily.py:200`](Backend/api/endpoints/sora_daily.py#L200) | `required` |
| `POST` | `/jobs/{job_id}/retry` | [`Backend/control_plane/routers/jobs.py:146`](Backend/control_plane/routers/jobs.py#L146) | `required` |
| `GET` | `/kb/constraints` | [`Backend/api/endpoints/knowledge_base.py:525`](Backend/api/endpoints/knowledge_base.py#L525) | `read` |
| `POST` | `/kb/constraints` | [`Backend/api/endpoints/knowledge_base.py:584`](Backend/api/endpoints/knowledge_base.py#L584) | `required` |
| `GET` | `/kb/playbooks` | [`Backend/api/endpoints/knowledge_base.py:635`](Backend/api/endpoints/knowledge_base.py#L635) | `read` |
| `POST` | `/kb/playbooks` | [`Backend/api/endpoints/knowledge_base.py:688`](Backend/api/endpoints/knowledge_base.py#L688) | `required` |
| `GET` | `/kb/rules` | [`Backend/api/endpoints/knowledge_base.py:226`](Backend/api/endpoints/knowledge_base.py#L226) | `read` |
| `POST` | `/kb/rules` | [`Backend/api/endpoints/knowledge_base.py:288`](Backend/api/endpoints/knowledge_base.py#L288) | `required` |
| `GET` | `/kb/rules/{rule_id}` | [`Backend/api/endpoints/knowledge_base.py:350`](Backend/api/endpoints/knowledge_base.py#L350) | `read` |
| `PATCH` | `/kb/rules/{rule_id}/deprecate` | [`Backend/api/endpoints/knowledge_base.py:395`](Backend/api/endpoints/knowledge_base.py#L395) | `required` |
| `POST` | `/kb/seed-demo-data` | [`Backend/api/endpoints/knowledge_base.py:736`](Backend/api/endpoints/knowledge_base.py#L736) | `required` |
| `GET` | `/kb/templates` | [`Backend/api/endpoints/knowledge_base.py:422`](Backend/api/endpoints/knowledge_base.py#L422) | `read` |
| `POST` | `/kb/templates` | [`Backend/api/endpoints/knowledge_base.py:476`](Backend/api/endpoints/knowledge_base.py#L476) | `required` |
| `GET` | `/keywords` | [`Backend/api/endpoints/trends_api.py:170`](Backend/api/endpoints/trends_api.py#L170) | `read` |
| `GET` | `/lag` | [`Backend/api/endpoints/pubsub_inspector.py:115`](Backend/api/endpoints/pubsub_inspector.py#L115) | `read` |
| `GET` | `/latest` | [`Backend/api/endpoints/benchmark_api.py:73`](Backend/api/endpoints/benchmark_api.py#L73) | `read` |
| `GET` | `/latest` | [`Backend/api/endpoints/content_gap_api.py:65`](Backend/api/endpoints/content_gap_api.py#L65) | `read` |
| `GET` | `/latest` | [`Backend/api/endpoints/strategy_report_api.py:62`](Backend/api/endpoints/strategy_report_api.py#L62) | `read` |
| `GET` | `/latest/markdown` | [`Backend/api/endpoints/strategy_report_api.py:77`](Backend/api/endpoints/strategy_report_api.py#L77) | `read` |
| `GET` | `/leaderboard` | [`Backend/api/endpoints/template_leaderboard.py:33`](Backend/api/endpoints/template_leaderboard.py#L33) | `read` |
| `POST` | `/leaderboard/recompute` | [`Backend/api/endpoints/template_leaderboard.py:82`](Backend/api/endpoints/template_leaderboard.py#L82) | `required` |
| `POST` | `/leads/discover` | [`Backend/api/endpoints/adaptive_scheduler.py:778`](Backend/api/endpoints/adaptive_scheduler.py#L778) | `required` |
| `POST` | `/learn/update` | [`Backend/api/endpoints/adaptive_scheduler.py:665`](Backend/api/endpoints/adaptive_scheduler.py#L665) | `required` |
| `GET` | `/learnings` | [`Backend/api/ab_testing.py:59`](Backend/api/ab_testing.py#L59) | `read` |
| `GET` | `/learnings` | [`Backend/api/endpoints/experiments.py:336`](Backend/api/endpoints/experiments.py#L336) | `read` |
| `GET` | `/library` | [`Backend/api/endpoints/music_matching.py:74`](Backend/api/endpoints/music_matching.py#L74) | `read` |
| `GET` | `/line-graph-aggregate` | [`Backend/api/metrics_scheduler_api.py:273`](Backend/api/metrics_scheduler_api.py#L273) | `read` |
| `GET` | `/line-graph/{post_id}` | [`Backend/api/metrics_scheduler_api.py:197`](Backend/api/metrics_scheduler_api.py#L197) | `read` |
| `GET` | `/linkedin/posts/{profile_id}` | [`Backend/api/rapidapi_metrics.py:366`](Backend/api/rapidapi_metrics.py#L366) | `read` |
| `GET` | `/linkedin/profile/{profile_id}` | [`Backend/api/rapidapi_metrics.py:347`](Backend/api/rapidapi_metrics.py#L347) | `read` |
| `GET` | `/list` | [`Backend/api/endpoints/analyzed_content.py:17`](Backend/api/endpoints/analyzed_content.py#L17) | `read` |
| `GET` | `/list` | [`Backend/api/endpoints/audio_analysis.py:197`](Backend/api/endpoints/audio_analysis.py#L197) | `read` |
| `GET` | `/list` | [`Backend/api/endpoints/audio_api.py:133`](Backend/api/endpoints/audio_api.py#L133) | `read` |
| `GET` | `/list` | [`Backend/api/endpoints/backup.py:102`](Backend/api/endpoints/backup.py#L102) | `read` |
| `GET` | `/list` | [`Backend/api/endpoints/broll.py:206`](Backend/api/endpoints/broll.py#L206) | `read` |
| `GET` | `/list` | [`Backend/api/endpoints/content_format.py:227`](Backend/api/endpoints/content_format.py#L227) | `read` |
| `GET` | `/list` | [`Backend/api/endpoints/dm_outreach.py:179`](Backend/api/endpoints/dm_outreach.py#L179) | `read` |
| `GET` | `/list` | [`Backend/api/endpoints/experiments.py:225`](Backend/api/endpoints/experiments.py#L225) | `read` |
| `GET` | `/list` | [`Backend/api/endpoints/formats.py:91`](Backend/api/endpoints/formats.py#L91) | `read` |
| `GET` | `/list` | [`Backend/api/endpoints/formats_api.py:71`](Backend/api/endpoints/formats_api.py#L71) | `read` |
| `GET` | `/list` | [`Backend/api/endpoints/media_provider.py:126`](Backend/api/endpoints/media_provider.py#L126) | `read` |
| `GET` | `/list` | [`Backend/api/endpoints/schedule.py:162`](Backend/api/endpoints/schedule.py#L162) | `read` |
| `GET` | `/list` | [`Backend/api/endpoints/strategy_report_api.py:113`](Backend/api/endpoints/strategy_report_api.py#L113) | `read` |
| `GET` | `/list` | [`Backend/api/media_processing.py:353`](Backend/api/media_processing.py#L353) | `read` |
| `GET` | `/list` | [`Backend/api/media_processing_db.py:252`](Backend/api/media_processing_db.py#L252) | `read` |
| `GET` | `/list` | [`Backend/api/posted_media.py:69`](Backend/api/posted_media.py#L69) | `read` |
| `POST` | `/list/add` | [`Backend/api/endpoints/dm_outreach.py:227`](Backend/api/endpoints/dm_outreach.py#L227) | `required` |
| `GET` | `/list/ready` | [`Backend/api/endpoints/dm_outreach.py:208`](Backend/api/endpoints/dm_outreach.py#L208) | `read` |
| `POST` | `/list/{entry_id}/message` | [`Backend/api/endpoints/dm_outreach.py:288`](Backend/api/endpoints/dm_outreach.py#L288) | `required` |
| `POST` | `/list/{entry_id}/note` | [`Backend/api/endpoints/dm_outreach.py:304`](Backend/api/endpoints/dm_outreach.py#L304) | `required` |
| `PUT` | `/list/{entry_id}/phase` | [`Backend/api/endpoints/dm_outreach.py:267`](Backend/api/endpoints/dm_outreach.py#L267) | `required` |
| `POST` | `/list/{entry_id}/send` | [`Backend/api/endpoints/dm_outreach.py:530`](Backend/api/endpoints/dm_outreach.py#L530) | `required` |
| `GET` | `/list/{entry_id}/should-advance` | [`Backend/api/endpoints/dm_outreach.py:371`](Backend/api/endpoints/dm_outreach.py#L371) | `read` |
| `PUT` | `/list/{entry_id}/status` | [`Backend/api/endpoints/dm_outreach.py:246`](Backend/api/endpoints/dm_outreach.py#L246) | `required` |
| `GET` | `/list/{entry_id}/suggest` | [`Backend/api/endpoints/dm_outreach.py:324`](Backend/api/endpoints/dm_outreach.py#L324) | `read` |
| `GET` | `/list/{video_id}` | [`Backend/api/endpoints/clips.py:137`](Backend/api/endpoints/clips.py#L137) | `read` |
| `GET` | `/live` | [`Backend/api/endpoints/health.py:347`](Backend/api/endpoints/health.py#L347) | `read` |
| `POST` | `/lock-selection` | [`Backend/api/endpoints/broll_candidates.py:255`](Backend/api/endpoints/broll_candidates.py#L255) | `required` |
| `POST` | `/login/verify` | [`Backend/api/endpoints/twitter_posting.py:90`](Backend/api/endpoints/twitter_posting.py#L90) | `required` |
| `DELETE` | `/logs` | [`Backend/api/endpoints/api_usage.py:269`](Backend/api/endpoints/api_usage.py#L269) | `required` |
| `GET` | `/logs` | [`Backend/api/endpoints/safari_sessions.py:259`](Backend/api/endpoints/safari_sessions.py#L259) | `read` |
| `GET` | `/logs/account/{account_id}` | [`Backend/api/endpoints/safari_sessions.py:311`](Backend/api/endpoints/safari_sessions.py#L311) | `read` |
| `GET` | `/low-performers` | [`Backend/api/endpoints/analytics_feedback.py:123`](Backend/api/endpoints/analytics_feedback.py#L123) | `read` |
| `GET` | `/manifest` | [`Backend/api/endpoints/sfx_library.py:152`](Backend/api/endpoints/sfx_library.py#L152) | `read` |
| `GET` | `/manifest/stats` | [`Backend/api/endpoints/sfx_library.py:168`](Backend/api/endpoints/sfx_library.py#L168) | `read` |
| `POST` | `/mark-as-posted` | [`Backend/api/endpoints/posted_content_matcher.py:115`](Backend/api/endpoints/posted_content_matcher.py#L115) | `required` |
| `POST` | `/mark-for-deletion` | [`Backend/api/endpoints/duplicate_detection.py:267`](Backend/api/endpoints/duplicate_detection.py#L267) | `required` |
| `POST` | `/mark-for-reanalysis` | [`Backend/api/endpoints/analysis_health.py:248`](Backend/api/endpoints/analysis_health.py#L248) | `required` |
| `POST` | `/mark-incomplete-for-reanalysis` | [`Backend/api/endpoints/analysis_health.py:262`](Backend/api/endpoints/analysis_health.py#L262) | `required` |
| `POST` | `/mark-used` | [`Backend/api/endpoints/content_variations.py:215`](Backend/api/endpoints/content_variations.py#L215) | `required` |
| `GET` | `/marked-for-deletion` | [`Backend/api/endpoints/duplicate_detection.py:303`](Backend/api/endpoints/duplicate_detection.py#L303) | `read` |
| `POST` | `/match` | [`Backend/api/endpoints/music_library.py:489`](Backend/api/endpoints/music_library.py#L489) | `required` |
| `POST` | `/match` | [`Backend/api/endpoints/platform_matching.py:64`](Backend/api/endpoints/platform_matching.py#L64) | `required` |
| `POST` | `/match-pillars` | [`Backend/api/endpoints/narrative_builder.py:894`](Backend/api/endpoints/narrative_builder.py#L894) | `required` |
| `POST` | `/match-transcript` | [`Backend/api/endpoints/posted_content_matcher.py:70`](Backend/api/endpoints/posted_content_matcher.py#L70) | `required` |
| `POST` | `/materialize` | [`Backend/api/endpoints/adaptive_scheduler.py:238`](Backend/api/endpoints/adaptive_scheduler.py#L238) | `required` |
| `POST` | `/media/upload` | [`Backend/api/blotato_router.py:816`](Backend/api/blotato_router.py#L816) | `required` |
| `GET` | `/media/{identifier}` | [`Backend/api/endpoints/instagram_api.py:103`](Backend/api/endpoints/instagram_api.py#L103) | `read` |
| `GET` | `/memories` | [`Backend/api/endpoints/agent_panel.py:514`](Backend/api/endpoints/agent_panel.py#L514) | `read` |
| `POST` | `/memories` | [`Backend/api/endpoints/agent_panel.py:558`](Backend/api/endpoints/agent_panel.py#L558) | `required` |
| `GET` | `/messages` | [`Backend/api/endpoints/community_inbox.py:118`](Backend/api/endpoints/community_inbox.py#L118) | `read` |
| `GET` | `/messages` | [`Backend/api/endpoints/inbox.py:68`](Backend/api/endpoints/inbox.py#L68) | `read` |
| `GET` | `/messages/unread/count` | [`Backend/api/endpoints/inbox.py:103`](Backend/api/endpoints/inbox.py#L103) | `read` |
| `GET` | `/messages/{message_id}` | [`Backend/api/endpoints/community_inbox.py:190`](Backend/api/endpoints/community_inbox.py#L190) | `read` |
| `GET` | `/messages/{message_id}` | [`Backend/api/endpoints/email.py:203`](Backend/api/endpoints/email.py#L203) | `read` |
| `GET` | `/messages/{message_id}` | [`Backend/api/endpoints/inbox.py:119`](Backend/api/endpoints/inbox.py#L119) | `read` |
| `PUT` | `/messages/{message_id}` | [`Backend/api/endpoints/community_inbox.py:212`](Backend/api/endpoints/community_inbox.py#L212) | `required` |
| `POST` | `/messages/{message_id}/ai-generate` | [`Backend/api/endpoints/inbox.py:253`](Backend/api/endpoints/inbox.py#L253) | `required` |
| `GET` | `/messages/{message_id}/ai-suggestions` | [`Backend/api/endpoints/inbox.py:207`](Backend/api/endpoints/inbox.py#L207) | `read` |
| `PUT` | `/messages/{message_id}/assign` | [`Backend/api/endpoints/inbox.py:161`](Backend/api/endpoints/inbox.py#L161) | `required` |
| `POST` | `/messages/{message_id}/respond` | [`Backend/api/endpoints/community_inbox.py:254`](Backend/api/endpoints/community_inbox.py#L254) | `required` |
| `PUT` | `/messages/{message_id}/status` | [`Backend/api/endpoints/inbox.py:140`](Backend/api/endpoints/inbox.py#L140) | `required` |
| `POST` | `/messages/{message_id}/tags` | [`Backend/api/endpoints/inbox.py:182`](Backend/api/endpoints/inbox.py#L182) | `required` |
| `POST` | `/messages/{message_id}/to-idea` | [`Backend/api/endpoints/inbox.py:379`](Backend/api/endpoints/inbox.py#L379) | `required` |
| `POST` | `/meta-ads/coordinate` | [`Backend/api/endpoints/adaptive_scheduler.py:794`](Backend/api/endpoints/adaptive_scheduler.py#L794) | `required` |
| `GET` | `/meta/expressions` | [`Backend/api/endpoints/characters.py:435`](Backend/api/endpoints/characters.py#L435) | `read` |
| `GET` | `/meta/styles` | [`Backend/api/endpoints/characters.py:429`](Backend/api/endpoints/characters.py#L429) | `read` |
| `GET` | `/metrics` | [`Backend/api/endpoints/content.py:55`](Backend/api/endpoints/content.py#L55) | `read` |
| `GET` | `/metrics` | [`Backend/api/endpoints/cpu_monitor.py:56`](Backend/api/endpoints/cpu_monitor.py#L56) | `read` |
| `GET` | `/metrics` | [`Backend/api/endpoints/orchestrator.py:346`](Backend/api/endpoints/orchestrator.py#L346) | `read` |
| `POST` | `/metrics` | [`Backend/api/endpoints/twitter_api.py:339`](Backend/api/endpoints/twitter_api.py#L339) | `required` |
| `POST` | `/metrics/calculate-weekly` | [`Backend/api/endpoints/analytics_insights.py:68`](Backend/api/endpoints/analytics_insights.py#L68) | `required` |
| `POST` | `/metrics/collect` | [`Backend/api/endpoints/platform_publishing.py:190`](Backend/api/endpoints/platform_publishing.py#L190) | `required` |
| `GET` | `/metrics/dashboard` | [`Backend/api/endpoints/relationship_crm.py:668`](Backend/api/endpoints/relationship_crm.py#L668) | `read` |
| `GET` | `/metrics/health-distribution` | [`Backend/api/endpoints/relationship_crm.py:712`](Backend/api/endpoints/relationship_crm.py#L712) | `read` |
| `GET` | `/metrics/north-star` | [`Backend/api/endpoints/analytics_insights.py:290`](Backend/api/endpoints/analytics_insights.py#L290) | `read` |
| `GET` | `/metrics/overview` | [`Backend/api/endpoints/system.py:115`](Backend/api/endpoints/system.py#L115) | `read` |
| `GET` | `/metrics/pipeline` | [`Backend/api/endpoints/relationship_crm.py:684`](Backend/api/endpoints/relationship_crm.py#L684) | `read` |
| `POST` | `/metrics/snapshot` | [`Backend/api/endpoints/content_loop.py:186`](Backend/api/endpoints/content_loop.py#L186) | `required` |
| `GET` | `/metrics/two-brain` | [`Backend/api/endpoints/system.py:246`](Backend/api/endpoints/system.py#L246) | `read` |
| `GET` | `/metrics/{platform_post_id}` | [`Backend/api/endpoints/twitter_api.py:456`](Backend/api/endpoints/twitter_api.py#L456) | `read` |
| `POST` | `/mix/align` | [`Backend/api/endpoints/adaptive_scheduler.py:551`](Backend/api/endpoints/adaptive_scheduler.py#L551) | `required` |
| `GET` | `/models` | [`Backend/api/endpoints/matting.py:132`](Backend/api/endpoints/matting.py#L132) | `read` |
| `GET` | `/models` | [`Backend/api/endpoints/tts.py:132`](Backend/api/endpoints/tts.py#L132) | `read` |
| `POST` | `/monitor/start` | [`Backend/api/endpoints/content_sourcing.py:188`](Backend/api/endpoints/content_sourcing.py#L188) | `required` |
| `POST` | `/monitor/stop` | [`Backend/api/endpoints/content_sourcing.py:236`](Backend/api/endpoints/content_sourcing.py#L236) | `required` |
| `GET` | `/monitoring/costs/{campaign_id}` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:640`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L640) | `read` |
| `GET` | `/monitoring/dlq` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:656`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L656) | `read` |
| `GET` | `/monitoring/errors` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:633`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L633) | `read` |
| `GET` | `/monitoring/latency` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:626`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L626) | `read` |
| `GET` | `/monitoring/stale` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:648`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L648) | `read` |
| `POST` | `/mplite/campaigns/{campaign_id}/cancel-queue` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1370`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1370) | `required` |
| `GET` | `/mplite/campaigns/{campaign_id}/queue` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1357`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1357) | `read` |
| `GET` | `/mplite/can-publish/{platform}` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1072`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1072) | `read` |
| `GET` | `/mplite/daily-summary` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1060`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1060) | `read` |
| `POST` | `/mplite/enqueue` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1139`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1139) | `required` |
| `POST` | `/mplite/enqueue/creative/{creative_id}` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1166`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1166) | `required` |
| `GET` | `/mplite/health` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1031`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1031) | `read` |
| `GET` | `/mplite/history` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1329`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1329) | `read` |
| `POST` | `/mplite/pause` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1305`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1305) | `required` |
| `GET` | `/mplite/platforms` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1345`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1345) | `read` |
| `GET` | `/mplite/queue` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1084`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1084) | `read` |
| `GET` | `/mplite/queue/next` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1112`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1112) | `read` |
| `GET` | `/mplite/queue/stats` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1100`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1100) | `read` |
| `GET` | `/mplite/queue/{item_id}` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1127`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1127) | `read` |
| `POST` | `/mplite/queue/{item_id}/cancel` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1266`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1266) | `required` |
| `POST` | `/mplite/queue/{item_id}/claim` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1220`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1220) | `required` |
| `POST` | `/mplite/queue/{item_id}/complete` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1232`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1232) | `required` |
| `POST` | `/mplite/queue/{item_id}/fail` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1254`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1254) | `required` |
| `POST` | `/mplite/queue/{item_id}/reschedule` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1290`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1290) | `required` |
| `POST` | `/mplite/queue/{item_id}/retry` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1278`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1278) | `required` |
| `POST` | `/mplite/resume` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1317`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1317) | `required` |
| `GET` | `/mplite/status` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:1048`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L1048) | `read` |
| `GET` | `/narrative-planner/timeline` | [`Backend/api/endpoints/agent_panel.py:139`](Backend/api/endpoints/agent_panel.py#L139) | `read` |
| `GET` | `/needs-care` | [`Backend/api/endpoints/relationship_crm.py:287`](Backend/api/endpoints/relationship_crm.py#L287) | `read` |
| `GET` | `/next-content` | [`Backend/api/endpoints/content_recommendation.py:22`](Backend/api/endpoints/content_recommendation.py#L22) | `read` |
| `GET` | `/next-slots` | [`Backend/api/endpoints/smart_schedule.py:133`](Backend/api/endpoints/smart_schedule.py#L133) | `read` |
| `PUT` | `/niche-config` | [`Backend/api/trend_detection.py:142`](Backend/api/trend_detection.py#L142) | `required` |
| `GET` | `/niches` | [`Backend/api/endpoints/channel_analyzer.py:391`](Backend/api/endpoints/channel_analyzer.py#L391) | `read` |
| `GET` | `/niches` | [`Backend/api/endpoints/creative_briefs.py:424`](Backend/api/endpoints/creative_briefs.py#L424) | `read` |
| `GET` | `/niches` | [`Backend/api/endpoints/trend_queries_api.py:598`](Backend/api/endpoints/trend_queries_api.py#L598) | `read` |
| `GET` | `/niches` | [`Backend/api/endpoints/trends_api.py:295`](Backend/api/endpoints/trends_api.py#L295) | `read` |
| `POST` | `/niches` | [`Backend/api/endpoints/trend_queries_api.py:564`](Backend/api/endpoints/trend_queries_api.py#L564) | `required` |
| `POST` | `/niches/discover` | [`Backend/api/endpoints/trends_api.py:262`](Backend/api/endpoints/trends_api.py#L262) | `required` |
| `GET` | `/niches/search` | [`Backend/api/endpoints/trends_api.py:234`](Backend/api/endpoints/trends_api.py#L234) | `read` |
| `POST` | `/nightly/analyze` | [`Backend/api/endpoints/adaptive_scheduler.py:842`](Backend/api/endpoints/adaptive_scheduler.py#L842) | `required` |
| `GET` | `/north-star` | [`Backend/api/endpoints/dashboard.py:118`](Backend/api/endpoints/dashboard.py#L118) | `read` |
| `GET` | `/notifications` | [`Backend/api/endpoints/twitter_posting.py:230`](Backend/api/endpoints/twitter_posting.py#L230) | `read` |
| `GET` | `/notifications/unread` | [`Backend/api/endpoints/twitter_posting.py:249`](Backend/api/endpoints/twitter_posting.py#L249) | `read` |
| `GET` | `/offers` | [`Backend/api/endpoints/adaptive_scheduler.py:183`](Backend/api/endpoints/adaptive_scheduler.py#L183) | `read` |
| `GET` | `/offers` | [`Backend/api/endpoints/dm_outreach.py:406`](Backend/api/endpoints/dm_outreach.py#L406) | `read` |
| `GET` | `/offers` | [`Backend/api/endpoints/ugc_content.py:289`](Backend/api/endpoints/ugc_content.py#L289) | `read` |
| `GET` | `/offers` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:365`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L365) | `read` |
| `POST` | `/offers` | [`Backend/api/endpoints/dm_outreach.py:425`](Backend/api/endpoints/dm_outreach.py#L425) | `required` |
| `GET` | `/offers/active` | [`Backend/api/endpoints/adaptive_scheduler.py:194`](Backend/api/endpoints/adaptive_scheduler.py#L194) | `read` |
| `POST` | `/offers/track` | [`Backend/api/endpoints/adaptive_scheduler.py:754`](Backend/api/endpoints/adaptive_scheduler.py#L754) | `required` |
| `POST` | `/offers/{offer_id}/create-campaign` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:373`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L373) | `required` |
| `POST` | `/oneclick/render_from_trend` | [`Backend/api/endpoints/trend_intelligence.py:419`](Backend/api/endpoints/trend_intelligence.py#L419) | `required` |
| `POST` | `/open-image-capture` | [`Backend/api/endpoints/ios_import_api.py:551`](Backend/api/endpoints/ios_import_api.py#L551) | `required` |
| `POST` | `/open/compose` | [`Backend/api/endpoints/twitter_posting.py:438`](Backend/api/endpoints/twitter_posting.py#L438) | `required` |
| `POST` | `/open/home` | [`Backend/api/endpoints/twitter_posting.py:450`](Backend/api/endpoints/twitter_posting.py#L450) | `required` |
| `GET` | `/optimal` | [`Backend/api/smart_posting_times.py:54`](Backend/api/smart_posting_times.py#L54) | `read` |
| `GET` | `/optimal/{platform}` | [`Backend/api/smart_posting_times.py:18`](Backend/api/smart_posting_times.py#L18) | `read` |
| `GET` | `/optimization-hints` | [`Backend/api/endpoints/analytics_feedback.py:75`](Backend/api/endpoints/analytics_feedback.py#L75) | `read` |
| `GET` | `/output/{job_id}` | [`Backend/api/endpoints/broll_producer.py:198`](Backend/api/endpoints/broll_producer.py#L198) | `read` |
| `GET` | `/output/{job_id}/stream` | [`Backend/api/endpoints/broll_producer.py:216`](Backend/api/endpoints/broll_producer.py#L216) | `read` |
| `GET` | `/output/{project_id}` | [`Backend/api/endpoints/sora_pipeline.py:299`](Backend/api/endpoints/sora_pipeline.py#L299) | `read` |
| `GET` | `/output/{project_id}/stream` | [`Backend/api/endpoints/sora_pipeline.py:315`](Backend/api/endpoints/sora_pipeline.py#L315) | `read` |
| `GET` | `/overview` | [`Backend/api/cross_platform_dashboard.py:14`](Backend/api/cross_platform_dashboard.py#L14) | `read` |
| `GET` | `/overview` | [`Backend/api/endpoints/social_analytics.py:95`](Backend/api/endpoints/social_analytics.py#L95) | `read` |
| `GET` | `/overview` | [`Backend/api/endpoints/trends.py:549`](Backend/api/endpoints/trends.py#L549) | `read` |
| `GET` | `/page/analytics` | [`Backend/api/endpoints/data_hydration.py:89`](Backend/api/endpoints/data_hydration.py#L89) | `read` |
| `GET` | `/page/content-performance` | [`Backend/api/endpoints/data_hydration.py:96`](Backend/api/endpoints/data_hydration.py#L96) | `read` |
| `GET` | `/page/followers` | [`Backend/api/endpoints/data_hydration.py:103`](Backend/api/endpoints/data_hydration.py#L103) | `read` |
| `GET` | `/page/narrative-builder` | [`Backend/api/endpoints/data_hydration.py:140`](Backend/api/endpoints/data_hydration.py#L140) | `read` |
| `GET` | `/page/people` | [`Backend/api/endpoints/data_hydration.py:114`](Backend/api/endpoints/data_hydration.py#L114) | `read` |
| `GET` | `/page/schedule` | [`Backend/api/endpoints/data_hydration.py:121`](Backend/api/endpoints/data_hydration.py#L121) | `read` |
| `GET` | `/panel/combined` | [`Backend/api/endpoints/agent_panel.py:369`](Backend/api/endpoints/agent_panel.py#L369) | `read` |
| `GET` | `/panel/experiments` | [`Backend/api/endpoints/agent_panel.py:324`](Backend/api/endpoints/agent_panel.py#L324) | `read` |
| `GET` | `/panel/narrative` | [`Backend/api/endpoints/agent_panel.py:288`](Backend/api/endpoints/agent_panel.py#L288) | `read` |
| `GET` | `/patterns` | [`Backend/api/endpoints/experiments.py:1892`](Backend/api/endpoints/experiments.py#L1892) | `read` |
| `POST` | `/patterns/extract/{experiment_id}` | [`Backend/api/endpoints/experiments.py:1918`](Backend/api/endpoints/experiments.py#L1918) | `required` |
| `POST` | `/patterns/recommend` | [`Backend/api/endpoints/experiments.py:1936`](Backend/api/endpoints/experiments.py#L1936) | `required` |
| `GET` | `/patterns/top-performing` | [`Backend/api/endpoints/enhanced_analysis.py:252`](Backend/api/endpoints/enhanced_analysis.py#L252) | `read` |
| `POST` | `/pause` | [`Backend/api/endpoints/engagement_control.py:61`](Backend/api/endpoints/engagement_control.py#L61) | `required` |
| `POST` | `/pause` | [`Backend/api/endpoints/safari_automation.py:94`](Backend/api/endpoints/safari_automation.py#L94) | `required` |
| `POST` | `/pause` | [`Backend/api/endpoints/sora_daily.py:119`](Backend/api/endpoints/sora_daily.py#L119) | `required` |
| `GET` | `/performance` | [`Backend/api/endpoints/adaptive_scheduler.py:221`](Backend/api/endpoints/adaptive_scheduler.py#L221) | `read` |
| `GET` | `/performance` | [`Backend/api/endpoints/analytics.py:65`](Backend/api/endpoints/analytics.py#L65) | `read` |
| `GET` | `/performance` | [`Backend/api/endpoints/review.py:53`](Backend/api/endpoints/review.py#L53) | `read` |
| `POST` | `/performance` | [`Backend/api/endpoints/user_tracking.py:367`](Backend/api/endpoints/user_tracking.py#L367) | `required` |
| `GET` | `/performance/daily` | [`Backend/api/endpoints/posting_optimizer_api.py:106`](Backend/api/endpoints/posting_optimizer_api.py#L106) | `read` |
| `GET` | `/performance/hourly` | [`Backend/api/endpoints/posting_optimizer_api.py:82`](Backend/api/endpoints/posting_optimizer_api.py#L82) | `read` |
| `POST` | `/periodic-checks/start` | [`Backend/api/endpoints/sora_automation.py:184`](Backend/api/endpoints/sora_automation.py#L184) | `required` |
| `POST` | `/periodic-checks/stop` | [`Backend/api/endpoints/sora_automation.py:203`](Backend/api/endpoints/sora_automation.py#L203) | `required` |
| `GET` | `/person/{person_id}/messages` | [`Backend/api/endpoints/email.py:229`](Backend/api/endpoints/email.py#L229) | `read` |
| `GET` | `/pexels/attribution/{asset_id}` | [`Backend/api/endpoints/media_assets.py:137`](Backend/api/endpoints/media_assets.py#L137) | `read` |
| `GET` | `/pexels/photos` | [`Backend/api/endpoints/media_assets.py:114`](Backend/api/endpoints/media_assets.py#L114) | `read` |
| `GET` | `/pexels/videos` | [`Backend/api/endpoints/media_assets.py:126`](Backend/api/endpoints/media_assets.py#L126) | `read` |
| `POST` | `/pillars` | [`Backend/api/endpoints/narrative_builder.py:783`](Backend/api/endpoints/narrative_builder.py#L783) | `required` |
| `POST` | `/pillars` | [`Backend/api/endpoints/narrative_goals.py:133`](Backend/api/endpoints/narrative_goals.py#L133) | `required` |
| `GET` | `/pillars/{goal_id}` | [`Backend/api/endpoints/narrative_builder.py:752`](Backend/api/endpoints/narrative_builder.py#L752) | `read` |
| `POST` | `/pipeline` | [`Backend/api/endpoints/sora.py:158`](Backend/api/endpoints/sora.py#L158) | `required` |
| `GET` | `/pipeline-summary` | [`Backend/api/endpoints/relationship_crm.py:344`](Backend/api/endpoints/relationship_crm.py#L344) | `read` |
| `POST` | `/pipeline/full` | [`Backend/api/endpoints/sora_automation.py:397`](Backend/api/endpoints/sora_automation.py#L397) | `required` |
| `POST` | `/pipeline/full` | [`Backend/api/endpoints/trend_intelligence.py:469`](Backend/api/endpoints/trend_intelligence.py#L469) | `required` |
| `GET` | `/pipeline/job/{job_id}` | [`Backend/api/endpoints/sora_automation.py:481`](Backend/api/endpoints/sora_automation.py#L481) | `read` |
| `GET` | `/pipeline/jobs` | [`Backend/api/endpoints/sora_automation.py:461`](Backend/api/endpoints/sora_automation.py#L461) | `read` |
| `POST` | `/pipeline/multi-part` | [`Backend/api/endpoints/sora_automation.py:336`](Backend/api/endpoints/sora_automation.py#L336) | `required` |
| `POST` | `/pipeline/promote-winners` | [`Backend/api/endpoints/experiments.py:2173`](Backend/api/endpoints/experiments.py#L2173) | `required` |
| `POST` | `/pipeline/queue` | [`Backend/api/endpoints/trend_intelligence.py:633`](Backend/api/endpoints/trend_intelligence.py#L633) | `required` |
| `POST` | `/pipeline/run` | [`Backend/api/endpoints/orchestrator.py:149`](Backend/api/endpoints/orchestrator.py#L149) | `required` |
| `POST` | `/pipeline/run` | [`Backend/api/endpoints/trends_api.py:557`](Backend/api/endpoints/trends_api.py#L557) | `required` |
| `POST` | `/pipeline/run-all` | [`Backend/api/endpoints/trend_intelligence.py:663`](Backend/api/endpoints/trend_intelligence.py#L663) | `required` |
| `POST` | `/pipeline/run-experiment` | [`Backend/api/endpoints/experiments.py:2220`](Backend/api/endpoints/experiments.py#L2220) | `required` |
| `POST` | `/pipeline/start` | [`Backend/api/endpoints/orchestrator.py:92`](Backend/api/endpoints/orchestrator.py#L92) | `required` |
| `POST` | `/pipeline/start` | [`Backend/scripts/verify_arch_complete.py:239`](Backend/scripts/verify_arch_complete.py#L239) | `required` |
| `POST` | `/pipeline/sync-learnings` | [`Backend/api/endpoints/experiments.py:2514`](Backend/api/endpoints/experiments.py#L2514) | `required` |
| `DELETE` | `/pipeline/{pipeline_id}` | [`Backend/api/endpoints/orchestrator.py:229`](Backend/api/endpoints/orchestrator.py#L229) | `required` |
| `GET` | `/pipeline/{pipeline_id}` | [`Backend/api/endpoints/orchestrator.py:163`](Backend/api/endpoints/orchestrator.py#L163) | `read` |
| `GET` | `/pipeline/{pipeline_id}` | [`Backend/scripts/verify_arch_complete.py:240`](Backend/scripts/verify_arch_complete.py#L240) | `read` |
| `GET` | `/pipeline/{pipeline_id}/analytics` | [`Backend/api/endpoints/orchestrator.py:387`](Backend/api/endpoints/orchestrator.py#L387) | `read` |
| `GET` | `/pipeline/{pipeline_id}/analytics` | [`Backend/scripts/verify_arch_complete.py:242`](Backend/scripts/verify_arch_complete.py#L242) | `read` |
| `GET` | `/pipeline/{pipeline_id}/events` | [`Backend/api/endpoints/orchestrator.py:263`](Backend/api/endpoints/orchestrator.py#L263) | `read` |
| `GET` | `/pipeline/{pipeline_id}/traffic` | [`Backend/api/endpoints/orchestrator.py:498`](Backend/api/endpoints/orchestrator.py#L498) | `read` |
| `GET` | `/pipeline/{pipeline_id}/traffic` | [`Backend/scripts/verify_arch_complete.py:243`](Backend/scripts/verify_arch_complete.py#L243) | `read` |
| `GET` | `/pipelines` | [`Backend/api/endpoints/orchestrator.py:189`](Backend/api/endpoints/orchestrator.py#L189) | `read` |
| `GET` | `/pipelines` | [`Backend/scripts/verify_arch_complete.py:241`](Backend/scripts/verify_arch_complete.py#L241) | `read` |
| `GET` | `/plan` | [`Backend/api/endpoints/inventory_scheduler.py:82`](Backend/api/endpoints/inventory_scheduler.py#L82) | `read` |
| `GET` | `/plan` | [`Backend/api/endpoints/sora_daily.py:48`](Backend/api/endpoints/sora_daily.py#L48) | `read` |
| `GET` | `/plan/7-day` | [`Backend/api/endpoints/narrative_builder.py:1123`](Backend/api/endpoints/narrative_builder.py#L1123) | `read` |
| `GET` | `/plans` | [`Backend/api/endpoints/content_mix_api.py:180`](Backend/api/endpoints/content_mix_api.py#L180) | `read` |
| `POST` | `/plans/generate` | [`Backend/api/endpoints/content_mix_api.py:118`](Backend/api/endpoints/content_mix_api.py#L118) | `required` |
| `GET` | `/plans/{plan_id}` | [`Backend/api/endpoints/content_mix_api.py:192`](Backend/api/endpoints/content_mix_api.py#L192) | `read` |
| `POST` | `/plans/{plan_id}/approve` | [`Backend/api/endpoints/content_mix_api.py:245`](Backend/api/endpoints/content_mix_api.py#L245) | `required` |
| `GET` | `/plans/{plan_id}/summary` | [`Backend/api/endpoints/content_mix_api.py:259`](Backend/api/endpoints/content_mix_api.py#L259) | `read` |
| `GET` | `/platform-comparison` | [`Backend/api/endpoints/analytics_insights.py:322`](Backend/api/endpoints/analytics_insights.py#L322) | `read` |
| `GET` | `/platform-limits` | [`Backend/api/endpoints/prompt_settings.py:112`](Backend/api/endpoints/prompt_settings.py#L112) | `read` |
| `GET` | `/platform-limits/{platform}` | [`Backend/api/endpoints/prompt_settings.py:143`](Backend/api/endpoints/prompt_settings.py#L143) | `read` |
| `GET` | `/platform/{platform}` | [`Backend/api/endpoints/multi_platform_analytics.py:149`](Backend/api/endpoints/multi_platform_analytics.py#L149) | `read` |
| `GET` | `/platform/{platform}` | [`Backend/api/endpoints/optimal_posting_times.py:27`](Backend/api/endpoints/optimal_posting_times.py#L27) | `read` |
| `GET` | `/platform/{platform}` | [`Backend/api/endpoints/social_analytics.py:228`](Backend/api/endpoints/social_analytics.py#L228) | `read` |
| `PUT` | `/platform/{platform}` | [`Backend/api/metrics_scheduler_api.py:99`](Backend/api/metrics_scheduler_api.py#L99) | `required` |
| `POST` | `/platform/{platform}/disable` | [`Backend/api/endpoints/engagement_control.py:94`](Backend/api/endpoints/engagement_control.py#L94) | `required` |
| `POST` | `/platform/{platform}/enable` | [`Backend/api/endpoints/engagement_control.py:83`](Backend/api/endpoints/engagement_control.py#L83) | `required` |
| `GET` | `/platforms` | [`Backend/api/approval_queue.py:518`](Backend/api/approval_queue.py#L518) | `read` |
| `GET` | `/platforms` | [`Backend/api/blotato_router.py:1095`](Backend/api/blotato_router.py#L1095) | `read` |
| `GET` | `/platforms` | [`Backend/api/caption_variants.py:74`](Backend/api/caption_variants.py#L74) | `read` |
| `GET` | `/platforms` | [`Backend/api/endpoints/ai_titles.py:260`](Backend/api/endpoints/ai_titles.py#L260) | `read` |
| `GET` | `/platforms` | [`Backend/api/endpoints/platform_matching.py:220`](Backend/api/endpoints/platform_matching.py#L220) | `read` |
| `GET` | `/platforms` | [`Backend/api/endpoints/platform_publishing.py:174`](Backend/api/endpoints/platform_publishing.py#L174) | `read` |
| `GET` | `/platforms` | [`Backend/api/endpoints/safari_sessions.py:408`](Backend/api/endpoints/safari_sessions.py#L408) | `read` |
| `GET` | `/platforms` | [`Backend/api/endpoints/trends.py:582`](Backend/api/endpoints/trends.py#L582) | `read` |
| `GET` | `/platforms` | [`Backend/api/posted_media.py:328`](Backend/api/posted_media.py#L328) | `read` |
| `GET` | `/platforms-summary` | [`Backend/api/analytics_compare.py:499`](Backend/api/analytics_compare.py#L499) | `read` |
| `GET` | `/platforms/summary` | [`Backend/api/endpoints/social_accounts.py:567`](Backend/api/endpoints/social_accounts.py#L567) | `read` |
| `PUT` | `/platforms/{platform}` | [`Backend/api/approval_queue.py:575`](Backend/api/approval_queue.py#L575) | `required` |
| `GET` | `/platforms/{platform}/accounts` | [`Backend/api/endpoints/social_accounts.py:607`](Backend/api/endpoints/social_accounts.py#L607) | `read` |
| `GET` | `/playbook` | [`Backend/api/endpoints/content_loop.py:297`](Backend/api/endpoints/content_loop.py#L297) | `read` |
| `POST` | `/playbook` | [`Backend/api/endpoints/content_loop.py:312`](Backend/api/endpoints/content_loop.py#L312) | `required` |
| `GET` | `/playlists` | [`Backend/api/endpoints/youtube_automation.py:38`](Backend/api/endpoints/youtube_automation.py#L38) | `read` |
| `POST` | `/playlists` | [`Backend/api/endpoints/youtube_automation.py:25`](Backend/api/endpoints/youtube_automation.py#L25) | `required` |
| `DELETE` | `/playlists/{playlist_id}` | [`Backend/api/endpoints/youtube_automation.py:46`](Backend/api/endpoints/youtube_automation.py#L46) | `required` |
| `POST` | `/poll` | [`Backend/api/endpoints/twitter_posting.py:176`](Backend/api/endpoints/twitter_posting.py#L176) | `required` |
| `POST` | `/poll-recent` | [`Backend/api/endpoints/content_metrics.py:142`](Backend/api/endpoints/content_metrics.py#L142) | `required` |
| `POST` | `/poll/download-now` | [`Backend/api/endpoints/sora_automation.py:288`](Backend/api/endpoints/sora_automation.py#L288) | `required` |
| `POST` | `/poll/start` | [`Backend/api/endpoints/sora_automation.py:223`](Backend/api/endpoints/sora_automation.py#L223) | `required` |
| `GET` | `/poll/status` | [`Backend/api/endpoints/sora_automation.py:268`](Backend/api/endpoints/sora_automation.py#L268) | `read` |
| `POST` | `/poll/stop` | [`Backend/api/endpoints/sora_automation.py:252`](Backend/api/endpoints/sora_automation.py#L252) | `required` |
| `POST` | `/poll/{content_id}` | [`Backend/api/endpoints/content_metrics.py:79`](Backend/api/endpoints/content_metrics.py#L79) | `required` |
| `POST` | `/pool/curate` | [`Backend/api/endpoints/adaptive_scheduler.py:633`](Backend/api/endpoints/adaptive_scheduler.py#L633) | `required` |
| `POST` | `/pool/health` | [`Backend/api/endpoints/adaptive_scheduler.py:625`](Backend/api/endpoints/adaptive_scheduler.py#L625) | `required` |
| `POST` | `/populate-engagement` | [`Backend/api/endpoints/data_orchestrator.py:53`](Backend/api/endpoints/data_orchestrator.py#L53) | `required` |
| `POST` | `/post` | [`Backend/api/endpoints/sora_automation.py:570`](Backend/api/endpoints/sora_automation.py#L570) | `required` |
| `POST` | `/post` | [`Backend/api/endpoints/twitter_posting.py:115`](Backend/api/endpoints/twitter_posting.py#L115) | `required` |
| `POST` | `/post-due` | [`Backend/routers/visual_campaign.py:106`](Backend/routers/visual_campaign.py#L106) | `required` |
| `POST` | `/post/{comment_id}` | [`Backend/api/comment_automation.py:774`](Backend/api/comment_automation.py#L774) | `required` |
| `POST` | `/post/{content_id}` | [`Backend/routers/visual_campaign.py:114`](Backend/routers/visual_campaign.py#L114) | `required` |
| `GET` | `/post/{post_id}` | [`Backend/api/endpoints/post_social_score.py:30`](Backend/api/endpoints/post_social_score.py#L30) | `read` |
| `POST` | `/post/{post_id}/calculate` | [`Backend/api/endpoints/post_social_score.py:117`](Backend/api/endpoints/post_social_score.py#L117) | `required` |
| `GET` | `/post/{post_id}/performance` | [`Backend/api/endpoints/analytics_insights.py:136`](Backend/api/endpoints/analytics_insights.py#L136) | `read` |
| `GET` | `/postings` | [`Backend/api/endpoints/content_loop.py:113`](Backend/api/endpoints/content_loop.py#L113) | `read` |
| `POST` | `/postings` | [`Backend/api/endpoints/content_loop.py:136`](Backend/api/endpoints/content_loop.py#L136) | `required` |
| `GET` | `/postings/{posting_id}/metrics` | [`Backend/api/endpoints/content_loop.py:209`](Backend/api/endpoints/content_loop.py#L209) | `read` |
| `PATCH` | `/postings/{posting_id}/status` | [`Backend/api/endpoints/content_loop.py:158`](Backend/api/endpoints/content_loop.py#L158) | `required` |
| `GET` | `/posts` | [`Backend/api/cascade_publisher.py:66`](Backend/api/cascade_publisher.py#L66) | `read` |
| `GET` | `/posts` | [`Backend/api/endpoints/calendar.py:72`](Backend/api/endpoints/calendar.py#L72) | `read` |
| `GET` | `/posts` | [`Backend/api/endpoints/platform_publishing.py:262`](Backend/api/endpoints/platform_publishing.py#L262) | `read` |
| `GET` | `/posts` | [`Backend/api/endpoints/social_analytics.py:456`](Backend/api/endpoints/social_analytics.py#L456) | `read` |
| `POST` | `/posts` | [`Backend/api/blotato_router.py:230`](Backend/api/blotato_router.py#L230) | `required` |
| `POST` | `/posts/bulk` | [`Backend/api/blotato_router.py:397`](Backend/api/blotato_router.py#L397) | `required` |
| `GET` | `/posts/by-origin` | [`Backend/api/endpoints/calendar.py:297`](Backend/api/endpoints/calendar.py#L297) | `read` |
| `POST` | `/posts/full-publish` | [`Backend/api/blotato_router.py:542`](Backend/api/blotato_router.py#L542) | `required` |
| `POST` | `/posts/full-publish-tracked` | [`Backend/api/blotato_router.py:700`](Backend/api/blotato_router.py#L700) | `required` |
| `POST` | `/posts/multi-platform` | [`Backend/api/blotato_router.py:338`](Backend/api/blotato_router.py#L338) | `required` |
| `GET` | `/posts/status/{submission_id}` | [`Backend/api/blotato_router.py:797`](Backend/api/blotato_router.py#L797) | `read` |
| `POST` | `/posts/{cascade_id}/approve` | [`Backend/api/cascade_publisher.py:101`](Backend/api/cascade_publisher.py#L101) | `required` |
| `POST` | `/posts/{cascade_id}/skip` | [`Backend/api/cascade_publisher.py:114`](Backend/api/cascade_publisher.py#L114) | `required` |
| `DELETE` | `/posts/{post_id}` | [`Backend/api/endpoints/calendar.py:177`](Backend/api/endpoints/calendar.py#L177) | `required` |
| `GET` | `/posts/{post_id}` | [`Backend/api/endpoints/platform_publishing.py:338`](Backend/api/endpoints/platform_publishing.py#L338) | `read` |
| `PATCH` | `/posts/{post_id}` | [`Backend/api/endpoints/calendar.py:145`](Backend/api/endpoints/calendar.py#L145) | `required` |
| `POST` | `/posts/{post_id}/publish` | [`Backend/api/endpoints/calendar.py:269`](Backend/api/endpoints/calendar.py#L269) | `required` |
| `GET` | `/pre-check` | [`Backend/api/endpoints/analysis_validation.py:171`](Backend/api/endpoints/analysis_validation.py#L171) | `read` |
| `GET` | `/pre-check/{video_id}` | [`Backend/api/endpoints/analysis_validation.py:238`](Backend/api/endpoints/analysis_validation.py#L238) | `read` |
| `POST` | `/predict` | [`Backend/api/endpoints/enhanced_analysis.py:263`](Backend/api/endpoints/enhanced_analysis.py#L263) | `required` |
| `GET` | `/preview` | [`Backend/api/endpoints/smart_schedule.py:110`](Backend/api/endpoints/smart_schedule.py#L110) | `read` |
| `POST` | `/preview` | [`Backend/api/endpoints/video_pipeline.py:161`](Backend/api/endpoints/video_pipeline.py#L161) | `required` |
| `POST` | `/preview` | [`Backend/api/endpoints/voice_selection.py:184`](Backend/api/endpoints/voice_selection.py#L184) | `required` |
| `POST` | `/preview-scene-graph` | [`Backend/api/endpoints/video_format_api.py:135`](Backend/api/endpoints/video_format_api.py#L135) | `required` |
| `GET` | `/preview/{music_id}` | [`Backend/api/endpoints/music_matching.py:387`](Backend/api/endpoints/music_matching.py#L387) | `read` |
| `POST` | `/process` | [`Backend/api/endpoints/matting.py:48`](Backend/api/endpoints/matting.py#L48) | `required` |
| `POST` | `/process` | [`Backend/api/endpoints/publishing_controls.py:382`](Backend/api/endpoints/publishing_controls.py#L382) | `required` |
| `POST` | `/process` | [`Backend/api/endpoints/publishing_queue.py:277`](Backend/api/endpoints/publishing_queue.py#L277) | `required` |
| `POST` | `/process` | [`Backend/api/endpoints/repurpose.py:104`](Backend/api/endpoints/repurpose.py#L104) | `required` |
| `POST` | `/process` | [`Backend/api/endpoints/youtube_automation.py:57`](Backend/api/endpoints/youtube_automation.py#L57) | `required` |
| `POST` | `/process-due` | [`Backend/routers/twitter_campaign.py:151`](Backend/routers/twitter_campaign.py#L151) | `required` |
| `POST` | `/process-now` | [`Backend/api/endpoints/post_scheduler_api.py:80`](Backend/api/endpoints/post_scheduler_api.py#L80) | `required` |
| `POST` | `/process/batch` | [`Backend/api/endpoints/publishing_controls.py:395`](Backend/api/endpoints/publishing_controls.py#L395) | `required` |
| `POST` | `/produce` | [`Backend/api/endpoints/broll_producer.py:92`](Backend/api/endpoints/broll_producer.py#L92) | `required` |
| `POST` | `/produce/async` | [`Backend/api/endpoints/broll_producer.py:155`](Backend/api/endpoints/broll_producer.py#L155) | `required` |
| `GET` | `/products` | [`Backend/api/endpoints/adaptive_scheduler.py:229`](Backend/api/endpoints/adaptive_scheduler.py#L229) | `read` |
| `GET` | `/products` | [`Backend/routers/twitter_campaign.py:163`](Backend/routers/twitter_campaign.py#L163) | `read` |
| `GET` | `/products/{slug}` | [`Backend/routers/twitter_campaign.py:186`](Backend/routers/twitter_campaign.py#L186) | `read` |
| `GET` | `/products/{slug}/cycle` | [`Backend/routers/twitter_campaign.py:207`](Backend/routers/twitter_campaign.py#L207) | `read` |
| `GET` | `/profile/videos` | [`Backend/api/endpoints/tiktok_analytics.py:126`](Backend/api/endpoints/tiktok_analytics.py#L126) | `read` |
| `GET` | `/profile/{identifier}` | [`Backend/api/endpoints/instagram_api.py:71`](Backend/api/endpoints/instagram_api.py#L71) | `read` |
| `GET` | `/profiles` | [`Backend/api/endpoints/voice_cloning.py:146`](Backend/api/endpoints/voice_cloning.py#L146) | `read` |
| `POST` | `/profiles` | [`Backend/api/endpoints/voice_cloning.py:112`](Backend/api/endpoints/voice_cloning.py#L112) | `required` |
| `DELETE` | `/profiles/{profile_id}` | [`Backend/api/endpoints/voice_cloning.py:224`](Backend/api/endpoints/voice_cloning.py#L224) | `required` |
| `GET` | `/profiles/{profile_id}` | [`Backend/api/endpoints/voice_cloning.py:172`](Backend/api/endpoints/voice_cloning.py#L172) | `read` |
| `PUT` | `/profiles/{profile_id}` | [`Backend/api/endpoints/voice_cloning.py:197`](Backend/api/endpoints/voice_cloning.py#L197) | `required` |
| `POST` | `/profiles/{profile_id}/reference` | [`Backend/api/endpoints/voice_cloning.py:247`](Backend/api/endpoints/voice_cloning.py#L247) | `required` |
| `GET` | `/projects` | [`Backend/api/endpoints/media_creation.py:156`](Backend/api/endpoints/media_creation.py#L156) | `read` |
| `GET` | `/projects` | [`Backend/api/endpoints/sora_pipeline.py:131`](Backend/api/endpoints/sora_pipeline.py#L131) | `read` |
| `GET` | `/projects` | [`Backend/api/endpoints/video_orchestrator.py:262`](Backend/api/endpoints/video_orchestrator.py#L262) | `read` |
| `POST` | `/projects` | [`Backend/api/endpoints/media_creation.py:125`](Backend/api/endpoints/media_creation.py#L125) | `required` |
| `POST` | `/projects` | [`Backend/api/endpoints/sora_pipeline.py:81`](Backend/api/endpoints/sora_pipeline.py#L81) | `required` |
| `POST` | `/projects` | [`Backend/api/endpoints/video_orchestrator.py:239`](Backend/api/endpoints/video_orchestrator.py#L239) | `required` |
| `GET` | `/projects/{project_id}` | [`Backend/api/endpoints/media_creation.py:192`](Backend/api/endpoints/media_creation.py#L192) | `read` |
| `GET` | `/projects/{project_id}` | [`Backend/api/endpoints/sora_pipeline.py:119`](Backend/api/endpoints/sora_pipeline.py#L119) | `read` |
| `GET` | `/projects/{project_id}` | [`Backend/api/endpoints/video_orchestrator.py:268`](Backend/api/endpoints/video_orchestrator.py#L268) | `read` |
| `POST` | `/projects/{project_id}/create-content` | [`Backend/api/endpoints/media_creation.py:222`](Backend/api/endpoints/media_creation.py#L222) | `required` |
| `POST` | `/projects/{project_id}/edit` | [`Backend/api/endpoints/media_creation.py:264`](Backend/api/endpoints/media_creation.py#L264) | `required` |
| `GET` | `/projects/{project_id}/preview` | [`Backend/api/endpoints/media_creation.py:294`](Backend/api/endpoints/media_creation.py#L294) | `read` |
| `GET` | `/prompt-runs` | [`Backend/api/endpoints/content_generation.py:116`](Backend/api/endpoints/content_generation.py#L116) | `read` |
| `GET` | `/prompt-runs/{run_id}` | [`Backend/api/endpoints/content_generation.py:101`](Backend/api/endpoints/content_generation.py#L101) | `read` |
| `GET` | `/prospects` | [`Backend/api/endpoints/dm_outreach.py:77`](Backend/api/endpoints/dm_outreach.py#L77) | `read` |
| `POST` | `/prospects` | [`Backend/api/endpoints/dm_outreach.py:129`](Backend/api/endpoints/dm_outreach.py#L129) | `required` |
| `GET` | `/prospects/{prospect_id}` | [`Backend/api/endpoints/dm_outreach.py:108`](Backend/api/endpoints/dm_outreach.py#L108) | `read` |
| `GET` | `/providers` | [`Backend/api/endpoints/ai_video.py:104`](Backend/api/endpoints/ai_video.py#L104) | `read` |
| `GET` | `/providers` | [`Backend/api/endpoints/ai_video_generation.py:601`](Backend/api/endpoints/ai_video_generation.py#L601) | `read` |
| `GET` | `/providers` | [`Backend/api/endpoints/video_generation.py:219`](Backend/api/endpoints/video_generation.py#L219) | `read` |
| `GET` | `/providers/{provider_name}` | [`Backend/api/endpoints/video_generation.py:225`](Backend/api/endpoints/video_generation.py#L225) | `read` |
| `POST` | `/providers/{provider}/schedule` | [`Backend/api/endpoints/blotato_test.py:84`](Backend/api/endpoints/blotato_test.py#L84) | `required` |
| `POST` | `/providers/{provider}/scrape` | [`Backend/api/endpoints/blotato_test.py:94`](Backend/api/endpoints/blotato_test.py#L94) | `required` |
| `POST` | `/providers/{provider}/test` | [`Backend/api/endpoints/blotato_test.py:65`](Backend/api/endpoints/blotato_test.py#L65) | `required` |
| `POST` | `/publication-attempts` | [`Backend/api/control_plane_publications.py:654`](Backend/api/control_plane_publications.py#L654) | `required` |
| `GET` | `/publication-attempts/{attempt_id}` | [`Backend/api/control_plane_publications.py:671`](Backend/api/control_plane_publications.py#L671) | `read` |
| `POST` | `/publication-attempts/{attempt_id}/reconcile` | [`Backend/api/control_plane_publications.py:684`](Backend/api/control_plane_publications.py#L684) | `required` |
| `POST` | `/publication-preflights` | [`Backend/api/control_plane_publications.py:644`](Backend/api/control_plane_publications.py#L644) | `required` |
| `POST` | `/publish` | [`Backend/api/endpoints/events.py:98`](Backend/api/endpoints/events.py#L98) | `required` |
| `POST` | `/publish` | [`Backend/api/endpoints/platform_publishing.py:123`](Backend/api/endpoints/platform_publishing.py#L123) | `required` |
| `POST` | `/publish` | [`Backend/api/endpoints/twitter_api.py:78`](Backend/api/endpoints/twitter_api.py#L78) | `required` |
| `POST` | `/publish-now` | [`Backend/api/endpoints/schedule.py:1009`](Backend/api/endpoints/schedule.py#L1009) | `required` |
| `POST` | `/publish-thread` | [`Backend/api/endpoints/twitter_api.py:204`](Backend/api/endpoints/twitter_api.py#L204) | `required` |
| `POST` | `/publish/due` | [`Backend/api/endpoints/adaptive_scheduler.py:826`](Backend/api/endpoints/adaptive_scheduler.py#L826) | `required` |
| `GET` | `/publisher/credentials` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:677`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L677) | `read` |
| `POST` | `/publishing/auto-schedule` | [`Backend/api/endpoints/publishing_analytics.py:230`](Backend/api/endpoints/publishing_analytics.py#L230) | `required` |
| `GET` | `/publishing/calendar/{year}/{month}` | [`Backend/api/endpoints/publishing_analytics.py:191`](Backend/api/endpoints/publishing_analytics.py#L191) | `read` |
| `POST` | `/publishing/posts/{post_id}/regenerate` | [`Backend/api/endpoints/publishing_analytics.py:110`](Backend/api/endpoints/publishing_analytics.py#L110) | `required` |
| `PUT` | `/publishing/posts/{post_id}/reschedule` | [`Backend/api/endpoints/publishing_analytics.py:85`](Backend/api/endpoints/publishing_analytics.py#L85) | `required` |
| `POST` | `/publishing/schedule` | [`Backend/api/endpoints/publishing_analytics.py:54`](Backend/api/endpoints/publishing_analytics.py#L54) | `required` |
| `POST` | `/pull-from-device` | [`Backend/api/endpoints/android_import_api.py:280`](Backend/api/endpoints/android_import_api.py#L280) | `required` |
| `POST` | `/push` | [`Backend/api/endpoints/video_toolkit.py:138`](Backend/api/endpoints/video_toolkit.py#L138) | `required` |
| `POST` | `/qa-gate` | [`Backend/api/endpoints/sfx_library.py:251`](Backend/api/endpoints/sfx_library.py#L251) | `required` |
| `POST` | `/qa/check` | [`Backend/api/endpoints/adaptive_scheduler.py:641`](Backend/api/endpoints/adaptive_scheduler.py#L641) | `required` |
| `GET` | `/quality-profiles/list` | [`Backend/api/endpoints/formats.py:562`](Backend/api/endpoints/formats.py#L562) | `read` |
| `GET` | `/queue` | [`Backend/api/comment_automation.py:565`](Backend/api/comment_automation.py#L565) | `read` |
| `GET` | `/queue` | [`Backend/api/content_pipeline.py:265`](Backend/api/content_pipeline.py#L265) | `read` |
| `GET` | `/queue` | [`Backend/api/endpoints/post_scheduler_api.py:91`](Backend/api/endpoints/post_scheduler_api.py#L91) | `read` |
| `GET` | `/queue` | [`Backend/api/endpoints/publishing_controls.py:151`](Backend/api/endpoints/publishing_controls.py#L151) | `read` |
| `GET` | `/queue` | [`Backend/api/endpoints/publishing_queue.py:49`](Backend/api/endpoints/publishing_queue.py#L49) | `read` |
| `GET` | `/queue` | [`Backend/api/endpoints/safari_automation.py:121`](Backend/api/endpoints/safari_automation.py#L121) | `read` |
| `POST` | `/queue` | [`Backend/api/endpoints/publishing_controls.py:185`](Backend/api/endpoints/publishing_controls.py#L185) | `required` |
| `GET` | `/queue-analysis` | [`Backend/api/endpoints/external_scheduling.py:784`](Backend/api/endpoints/external_scheduling.py#L784) | `read` |
| `POST` | `/queue/bulk` | [`Backend/api/endpoints/publishing_controls.py:211`](Backend/api/endpoints/publishing_controls.py#L211) | `required` |
| `GET` | `/queue/external` | [`Backend/api/endpoints/adaptive_scheduler.py:890`](Backend/api/endpoints/adaptive_scheduler.py#L890) | `read` |
| `GET` | `/queue/next` | [`Backend/api/content_pipeline.py:308`](Backend/api/content_pipeline.py#L308) | `read` |
| `GET` | `/queue/pending` | [`Backend/api/endpoints/publishing.py:29`](Backend/api/endpoints/publishing.py#L29) | `read` |
| `GET` | `/queue/stats` | [`Backend/api/endpoints/publishing_controls.py:176`](Backend/api/endpoints/publishing_controls.py#L176) | `read` |
| `DELETE` | `/queue/{content_id}` | [`Backend/api/content_pipeline.py:673`](Backend/api/content_pipeline.py#L673) | `required` |
| `DELETE` | `/queue/{item_id}` | [`Backend/api/endpoints/publishing_controls.py:325`](Backend/api/endpoints/publishing_controls.py#L325) | `required` |
| `GET` | `/queue/{item_id}` | [`Backend/api/endpoints/publishing_controls.py:237`](Backend/api/endpoints/publishing_controls.py#L237) | `read` |
| `PATCH` | `/queue/{item_id}` | [`Backend/api/endpoints/publishing_controls.py:247`](Backend/api/endpoints/publishing_controls.py#L247) | `required` |
| `POST` | `/queue/{item_id}/cancel` | [`Backend/api/endpoints/publishing_controls.py:305`](Backend/api/endpoints/publishing_controls.py#L305) | `required` |
| `POST` | `/queue/{item_id}/pause` | [`Backend/api/endpoints/publishing_controls.py:285`](Backend/api/endpoints/publishing_controls.py#L285) | `required` |
| `PATCH` | `/queue/{item_id}/priority` | [`Backend/api/endpoints/publishing_controls.py:265`](Backend/api/endpoints/publishing_controls.py#L265) | `required` |
| `POST` | `/queue/{item_id}/reschedule` | [`Backend/api/endpoints/publishing_controls.py:275`](Backend/api/endpoints/publishing_controls.py#L275) | `required` |
| `POST` | `/queue/{item_id}/resume` | [`Backend/api/endpoints/publishing_controls.py:295`](Backend/api/endpoints/publishing_controls.py#L295) | `required` |
| `POST` | `/queue/{item_id}/retry` | [`Backend/api/endpoints/publishing_controls.py:315`](Backend/api/endpoints/publishing_controls.py#L315) | `required` |
| `GET` | `/queues` | [`Backend/api/endpoints/trend_intelligence.py:708`](Backend/api/endpoints/trend_intelligence.py#L708) | `read` |
| `GET` | `/quick` | [`Backend/api/endpoints/backend_health.py:42`](Backend/api/endpoints/backend_health.py#L42) | `read` |
| `POST` | `/quick` | [`Backend/api/endpoints/video_render.py:167`](Backend/api/endpoints/video_render.py#L167) | `required` |
| `GET` | `/quick-prompts` | [`Backend/api/ai_chat.py:389`](Backend/api/ai_chat.py#L389) | `read` |
| `POST` | `/quick-start` | [`Backend/api/explainer_video.py:485`](Backend/api/explainer_video.py#L485) | `required` |
| `POST` | `/quick-video` | [`Backend/api/endpoints/sora_pipeline.py:254`](Backend/api/endpoints/sora_pipeline.py#L254) | `required` |
| `GET` | `/quota` | [`Backend/api/endpoints/dm_outreach.py:546`](Backend/api/endpoints/dm_outreach.py#L546) | `read` |
| `GET` | `/rate-check` | [`Backend/api/engagement_autopilot.py:161`](Backend/api/engagement_autopilot.py#L161) | `read` |
| `GET` | `/rate-limit-status` | [`Backend/api/endpoints/music_crawler.py:153`](Backend/api/endpoints/music_crawler.py#L153) | `read` |
| `GET` | `/ready` | [`Backend/api/endpoints/health.py:329`](Backend/api/endpoints/health.py#L329) | `read` |
| `GET` | `/reasoning/live/{goal_id}` | [`Backend/api/endpoints/narrative_scheduler.py:66`](Backend/api/endpoints/narrative_scheduler.py#L66) | `read` |
| `GET` | `/reasoning/{goal_id}` | [`Backend/api/endpoints/narrative_scheduler.py:14`](Backend/api/endpoints/narrative_scheduler.py#L14) | `read` |
| `POST` | `/rebuild-all-lenses` | [`Backend/api/endpoints/people.py:241`](Backend/api/endpoints/people.py#L241) | `required` |
| `POST` | `/recalculate` | [`Backend/api/endpoints/content_runway.py:325`](Backend/api/endpoints/content_runway.py#L325) | `required` |
| `GET` | `/recent` | [`Backend/api/endpoints/events.py:24`](Backend/api/endpoints/events.py#L24) | `read` |
| `POST` | `/recommend` | [`Backend/api/endpoints/optimal_posting_times.py:55`](Backend/api/endpoints/optimal_posting_times.py#L55) | `required` |
| `GET` | `/recommendations` | [`Backend/api/endpoints/adaptive_scheduler.py:527`](Backend/api/endpoints/adaptive_scheduler.py#L527) | `read` |
| `GET` | `/recommendations` | [`Backend/api/endpoints/analytics_insights.py:255`](Backend/api/endpoints/analytics_insights.py#L255) | `read` |
| `GET` | `/recommendations` | [`Backend/api/endpoints/api_usage.py:306`](Backend/api/endpoints/api_usage.py#L306) | `read` |
| `GET` | `/recommendations` | [`Backend/api/endpoints/coaching.py:39`](Backend/api/endpoints/coaching.py#L39) | `read` |
| `GET` | `/recommendations` | [`Backend/api/endpoints/strategic_analysis.py:153`](Backend/api/endpoints/strategic_analysis.py#L153) | `read` |
| `POST` | `/record` | [`Backend/api/endpoints/posted_content.py:125`](Backend/api/endpoints/posted_content.py#L125) | `required` |
| `POST` | `/record-posted` | [`Backend/api/endpoints/schedule.py:759`](Backend/api/endpoints/schedule.py#L759) | `required` |
| `POST` | `/recycle` | [`Backend/api/content_recycling.py:68`](Backend/api/content_recycling.py#L68) | `required` |
| `GET` | `/reels/{identifier}` | [`Backend/api/endpoints/instagram_api.py:152`](Backend/api/endpoints/instagram_api.py#L152) | `read` |
| `POST` | `/refresh` | [`Backend/api/endpoints/data_hydration.py:29`](Backend/api/endpoints/data_hydration.py#L29) | `required` |
| `POST` | `/refresh-all` | [`Backend/api/endpoints/data_orchestrator.py:42`](Backend/api/endpoints/data_orchestrator.py#L42) | `required` |
| `POST` | `/refresh-all-metrics` | [`Backend/api/endpoints/posted_content.py:740`](Backend/api/endpoints/posted_content.py#L740) | `required` |
| `POST` | `/refresh-background` | [`Backend/api/endpoints/data_hydration.py:62`](Backend/api/endpoints/data_hydration.py#L62) | `required` |
| `POST` | `/refresh-posted-content` | [`Backend/api/endpoints/youtube_analytics.py:138`](Backend/api/endpoints/youtube_analytics.py#L138) | `required` |
| `POST` | `/register-content` | [`Backend/api/endpoints/content_guard.py:97`](Backend/api/endpoints/content_guard.py#L97) | `required` |
| `POST` | `/reject/{comment_id}` | [`Backend/api/comment_automation.py:649`](Backend/api/comment_automation.py#L649) | `required` |
| `GET` | `/remotion-spec/compositions` | [`Backend/api/endpoints/content_pipeline.py:369`](Backend/api/endpoints/content_pipeline.py#L369) | `read` |
| `POST` | `/remotion-spec/generate` | [`Backend/api/endpoints/content_pipeline.py:317`](Backend/api/endpoints/content_pipeline.py#L317) | `required` |
| `GET` | `/remotion-spec/{render_spec_id}` | [`Backend/api/endpoints/content_pipeline.py:382`](Backend/api/endpoints/content_pipeline.py#L382) | `read` |
| `POST` | `/render` | [`Backend/api/endpoints/remotion.py:103`](Backend/api/endpoints/remotion.py#L103) | `required` |
| `POST` | `/render` | [`Backend/api/endpoints/templates.py:515`](Backend/api/endpoints/templates.py#L515) | `required` |
| `POST` | `/render` | [`Backend/api/endpoints/video_format_api.py:59`](Backend/api/endpoints/video_format_api.py#L59) | `required` |
| `POST` | `/render-pending` | [`Backend/routers/visual_campaign.py:98`](Backend/routers/visual_campaign.py#L98) | `required` |
| `GET` | `/render/jobs` | [`Backend/api/endpoints/trend_flash.py:310`](Backend/api/endpoints/trend_flash.py#L310) | `read` |
| `GET` | `/render/jobs/{job_id}` | [`Backend/api/endpoints/trend_flash.py:328`](Backend/api/endpoints/trend_flash.py#L328) | `read` |
| `GET` | `/renders` | [`Backend/api/endpoints/trend_intelligence.py:299`](Backend/api/endpoints/trend_intelligence.py#L299) | `read` |
| `POST` | `/renders` | [`Backend/api/endpoints/trend_intelligence.py:260`](Backend/api/endpoints/trend_intelligence.py#L260) | `required` |
| `POST` | `/renders/callback` | [`Backend/api/endpoints/trend_intelligence.py:314`](Backend/api/endpoints/trend_intelligence.py#L314) | `required` |
| `GET` | `/renders/output/{job_id}` | [`Backend/api/endpoints/trend_intelligence.py:338`](Backend/api/endpoints/trend_intelligence.py#L338) | `read` |
| `GET` | `/renders/{job_id}` | [`Backend/api/endpoints/trend_intelligence.py:287`](Backend/api/endpoints/trend_intelligence.py#L287) | `read` |
| `POST` | `/replay/{event_id}` | [`Backend/api/endpoints/events.py:86`](Backend/api/endpoints/events.py#L86) | `required` |
| `POST` | `/replies/generate` | [`Backend/api/engagement_autopilot.py:97`](Backend/api/engagement_autopilot.py#L97) | `required` |
| `POST` | `/reply` | [`Backend/api/endpoints/twitter_posting.py:153`](Backend/api/endpoints/twitter_posting.py#L153) | `required` |
| `GET` | `/report` | [`Backend/api/content_intelligence.py:60`](Backend/api/content_intelligence.py#L60) | `read` |
| `GET` | `/report` | [`Backend/api/endpoints/strategic_analysis.py:125`](Backend/api/endpoints/strategic_analysis.py#L125) | `read` |
| `GET` | `/report/{report_id}` | [`Backend/api/endpoints/competitor_audit.py:164`](Backend/api/endpoints/competitor_audit.py#L164) | `read` |
| `GET` | `/reports` | [`Backend/api/endpoints/influencer_analysis.py:93`](Backend/api/endpoints/influencer_analysis.py#L93) | `read` |
| `GET` | `/reports/by-username/{platform}/{username}` | [`Backend/api/endpoints/influencer_analysis.py:171`](Backend/api/endpoints/influencer_analysis.py#L171) | `read` |
| `GET` | `/reports/{report_id}` | [`Backend/api/endpoints/influencer_analysis.py:142`](Backend/api/endpoints/influencer_analysis.py#L142) | `read` |
| `POST` | `/repurpose/clips` | [`Backend/api/endpoints/adaptive_scheduler.py:332`](Backend/api/endpoints/adaptive_scheduler.py#L332) | `required` |
| `POST` | `/request` | [`Backend/api/endpoints/music.py:52`](Backend/api/endpoints/music.py#L52) | `required` |
| `POST` | `/request` | [`Backend/api/endpoints/visuals.py:51`](Backend/api/endpoints/visuals.py#L51) | `required` |
| `GET` | `/requirements` | [`Backend/api/endpoints/voice_cloning_quality.py:222`](Backend/api/endpoints/voice_cloning_quality.py#L222) | `read` |
| `GET` | `/requirements/{platform}` | [`Backend/api/endpoints/platform_matching.py:240`](Backend/api/endpoints/platform_matching.py#L240) | `read` |
| `GET` | `/research-export` | [`Backend/api/endpoints/competitor_api.py:1465`](Backend/api/endpoints/competitor_api.py#L1465) | `read` |
| `POST` | `/reset` | [`Backend/api/comment_automation.py:1015`](Backend/api/comment_automation.py#L1015) | `required` |
| `POST` | `/reset` | [`Backend/api/endpoints/app_settings.py:131`](Backend/api/endpoints/app_settings.py#L131) | `required` |
| `POST` | `/reset-mock-data` | [`Backend/api/content_pipeline.py:682`](Backend/api/content_pipeline.py#L682) | `required` |
| `GET` | `/resources` | [`Backend/api/endpoints/video_toolkit.py:39`](Backend/api/endpoints/video_toolkit.py#L39) | `read` |
| `GET` | `/resources/summary` | [`Backend/api/endpoints/video_toolkit.py:77`](Backend/api/endpoints/video_toolkit.py#L77) | `read` |
| `GET` | `/results` | [`Backend/api/endpoints/analysis.py:416`](Backend/api/endpoints/analysis.py#L416) | `read` |
| `GET` | `/results` | [`Backend/api/endpoints/highlights.py:122`](Backend/api/endpoints/highlights.py#L122) | `read` |
| `GET` | `/results/{video_id}` | [`Backend/api/endpoints/analysis.py:448`](Backend/api/endpoints/analysis.py#L448) | `read` |
| `GET` | `/results/{video_id}` | [`Backend/api/endpoints/highlights.py:157`](Backend/api/endpoints/highlights.py#L157) | `read` |
| `POST` | `/resume` | [`Backend/api/endpoints/engagement_control.py:72`](Backend/api/endpoints/engagement_control.py#L72) | `required` |
| `POST` | `/resume` | [`Backend/api/endpoints/safari_automation.py:102`](Backend/api/endpoints/safari_automation.py#L102) | `required` |
| `POST` | `/resume` | [`Backend/api/endpoints/sora_daily.py:138`](Backend/api/endpoints/sora_daily.py#L138) | `required` |
| `POST` | `/retention` | [`Backend/api/endpoints/user_tracking.py:270`](Backend/api/endpoints/user_tracking.py#L270) | `required` |
| `POST` | `/retire` | [`Backend/api/endpoints/template_retiree.py:108`](Backend/api/endpoints/template_retiree.py#L108) | `required` |
| `POST` | `/retry-failed/{job_id}` | [`Backend/api/endpoints/analysis_health.py:75`](Backend/api/endpoints/analysis_health.py#L75) | `required` |
| `POST` | `/retry/{media_id}` | [`Backend/api/media_processing.py:558`](Backend/api/media_processing.py#L558) | `required` |
| `POST` | `/retry/{post_id}` | [`Backend/api/endpoints/post_scheduler_api.py:98`](Backend/api/endpoints/post_scheduler_api.py#L98) | `required` |
| `GET` | `/review-windows` | [`Backend/api/endpoints/content_loop.py:225`](Backend/api/endpoints/content_loop.py#L225) | `read` |
| `GET` | `/reviews` | [`Backend/api/endpoints/content_loop.py:253`](Backend/api/endpoints/content_loop.py#L253) | `read` |
| `POST` | `/reviews` | [`Backend/api/endpoints/content_loop.py:273`](Backend/api/endpoints/content_loop.py#L273) | `required` |
| `POST` | `/rewards/compute` | [`Backend/api/endpoints/adaptive_scheduler.py:305`](Backend/api/endpoints/adaptive_scheduler.py#L305) | `required` |
| `POST` | `/rounds/{round_id}/collect-metrics` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:192`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L192) | `required` |
| `POST` | `/rounds/{round_id}/deploy-ads` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:238`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L238) | `required` |
| `POST` | `/rounds/{round_id}/generate` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:140`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L140) | `required` |
| `POST` | `/rounds/{round_id}/iterate` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:264`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L264) | `required` |
| `POST` | `/rounds/{round_id}/publish` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:168`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L168) | `required` |
| `POST` | `/rounds/{round_id}/retry` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:523`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L523) | `required` |
| `POST` | `/rounds/{round_id}/select-winners` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:209`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L209) | `required` |
| `POST` | `/route` | [`Backend/api/endpoints/adaptive_scheduler.py:806`](Backend/api/endpoints/adaptive_scheduler.py#L806) | `required` |
| `POST` | `/route` | [`Backend/api/endpoints/video_routing_api.py:96`](Backend/api/endpoints/video_routing_api.py#L96) | `required` |
| `GET` | `/routing-rules` | [`Backend/api/endpoints/video_routing_api.py:192`](Backend/api/endpoints/video_routing_api.py#L192) | `read` |
| `GET` | `/rules` | [`Backend/api/cascade_publisher.py:32`](Backend/api/cascade_publisher.py#L32) | `read` |
| `GET` | `/rules` | [`Backend/api/endpoints/auto_curator.py:85`](Backend/api/endpoints/auto_curator.py#L85) | `read` |
| `GET` | `/rules` | [`Backend/api/endpoints/community_inbox.py:540`](Backend/api/endpoints/community_inbox.py#L540) | `read` |
| `POST` | `/rules` | [`Backend/api/cascade_publisher.py:41`](Backend/api/cascade_publisher.py#L41) | `required` |
| `POST` | `/rules` | [`Backend/api/endpoints/auto_curator.py:123`](Backend/api/endpoints/auto_curator.py#L123) | `required` |
| `POST` | `/rules` | [`Backend/api/endpoints/community_inbox.py:578`](Backend/api/endpoints/community_inbox.py#L578) | `required` |
| `POST` | `/rules/seed-defaults` | [`Backend/api/cascade_publisher.py:58`](Backend/api/cascade_publisher.py#L58) | `required` |
| `DELETE` | `/rules/{rule_id}` | [`Backend/api/endpoints/auto_curator.py:239`](Backend/api/endpoints/auto_curator.py#L239) | `required` |
| `PUT` | `/rules/{rule_id}` | [`Backend/api/endpoints/auto_curator.py:178`](Backend/api/endpoints/auto_curator.py#L178) | `required` |
| `POST` | `/run` | [`Backend/api/endpoints/benchmark_api.py:34`](Backend/api/endpoints/benchmark_api.py#L34) | `required` |
| `POST` | `/run` | [`Backend/api/endpoints/content_gap_api.py:31`](Backend/api/endpoints/content_gap_api.py#L31) | `required` |
| `POST` | `/run` | [`Backend/api/endpoints/trend_flash.py:202`](Backend/api/endpoints/trend_flash.py#L202) | `required` |
| `POST` | `/run-batch` | [`Backend/api/endpoints/analysis_scheduler.py:93`](Backend/api/endpoints/analysis_scheduler.py#L93) | `required` |
| `POST` | `/run-daily` | [`Backend/routers/twitter_campaign.py:133`](Backend/routers/twitter_campaign.py#L133) | `required` |
| `POST` | `/run-daily` | [`Backend/routers/visual_campaign.py:90`](Backend/routers/visual_campaign.py#L90) | `required` |
| `POST` | `/run-format/{format_id}` | [`Backend/api/endpoints/format_discovery.py:135`](Backend/api/endpoints/format_discovery.py#L135) | `required` |
| `GET` | `/run/{run_id}` | [`Backend/api/endpoints/agent_events.py:117`](Backend/api/endpoints/agent_events.py#L117) | `read` |
| `GET` | `/runs` | [`Backend/api/endpoints/automation.py:202`](Backend/api/endpoints/automation.py#L202) | `read` |
| `GET` | `/runs/active` | [`Backend/api/endpoints/automations.py:286`](Backend/api/endpoints/automations.py#L286) | `read` |
| `GET` | `/runs/{run_id}` | [`Backend/api/endpoints/automation.py:220`](Backend/api/endpoints/automation.py#L220) | `read` |
| `GET` | `/runs/{run_id}` | [`Backend/api/endpoints/formats.py:401`](Backend/api/endpoints/formats.py#L401) | `read` |
| `GET` | `/runs/{run_id}/artifacts` | [`Backend/api/endpoints/automation.py:256`](Backend/api/endpoints/automation.py#L256) | `read` |
| `GET` | `/runs/{run_id}/artifacts` | [`Backend/api/endpoints/formats.py:471`](Backend/api/endpoints/formats.py#L471) | `read` |
| `POST` | `/runs/{run_id}/cancel` | [`Backend/api/endpoints/automation.py:289`](Backend/api/endpoints/automation.py#L289) | `required` |
| `POST` | `/runs/{run_id}/pause` | [`Backend/api/endpoints/automation.py:267`](Backend/api/endpoints/automation.py#L267) | `required` |
| `POST` | `/runs/{run_id}/retry` | [`Backend/api/endpoints/automation.py:311`](Backend/api/endpoints/automation.py#L311) | `required` |
| `GET` | `/runs/{run_id}/steps` | [`Backend/api/endpoints/automation.py:234`](Backend/api/endpoints/automation.py#L234) | `read` |
| `GET` | `/runs/{run_id}/timeline` | [`Backend/api/endpoints/automation.py:245`](Backend/api/endpoints/automation.py#L245) | `read` |
| `GET` | `/runway` | [`Backend/api/content_pipeline.py:405`](Backend/api/content_pipeline.py#L405) | `read` |
| `GET` | `/safari-automation` | [`Backend/api/endpoints/health.py:430`](Backend/api/endpoints/health.py#L430) | `read` |
| `GET` | `/safari-automation/commands` | [`Backend/api/endpoints/health.py:455`](Backend/api/endpoints/health.py#L455) | `read` |
| `POST` | `/same-day-adjuster/check-now` | [`Backend/api/endpoints/autonomy.py:55`](Backend/api/endpoints/autonomy.py#L55) | `required` |
| `GET` | `/same-day-adjuster/status` | [`Backend/api/endpoints/autonomy.py:37`](Backend/api/endpoints/autonomy.py#L37) | `read` |
| `PUT` | `/same-day-adjuster/thresholds` | [`Backend/api/endpoints/autonomy.py:75`](Backend/api/endpoints/autonomy.py#L75) | `required` |
| `POST` | `/sample` | [`Backend/api/endpoints/template_leaderboard.py:149`](Backend/api/endpoints/template_leaderboard.py#L149) | `required` |
| `POST` | `/save` | [`Backend/api/endpoints/content_ideas_api.py:321`](Backend/api/endpoints/content_ideas_api.py#L321) | `required` |
| `POST` | `/save-posted-content` | [`Backend/api/endpoints/tiktok_repurpose.py:181`](Backend/api/endpoints/tiktok_repurpose.py#L181) | `required` |
| `GET` | `/saved-recommendations` | [`Backend/api/endpoints/narrative_builder.py:528`](Backend/api/endpoints/narrative_builder.py#L528) | `read` |
| `GET` | `/saved-replies` | [`Backend/api/endpoints/inbox.py:311`](Backend/api/endpoints/inbox.py#L311) | `read` |
| `POST` | `/saved-replies` | [`Backend/api/endpoints/inbox.py:330`](Backend/api/endpoints/inbox.py#L330) | `required` |
| `POST` | `/saved-replies/{reply_id}/use` | [`Backend/api/endpoints/inbox.py:354`](Backend/api/endpoints/inbox.py#L354) | `required` |
| `POST` | `/scan` | [`Backend/api/endpoints/android_import_api.py:219`](Backend/api/endpoints/android_import_api.py#L219) | `required` |
| `POST` | `/scan` | [`Backend/api/endpoints/content_ingestion.py:55`](Backend/api/endpoints/content_ingestion.py#L55) | `required` |
| `POST` | `/scan` | [`Backend/api/endpoints/content_sourcing.py:55`](Backend/api/endpoints/content_sourcing.py#L55) | `required` |
| `POST` | `/scan` | [`Backend/api/endpoints/ingestion.py:258`](Backend/api/endpoints/ingestion.py#L258) | `required` |
| `POST` | `/scan` | [`Backend/api/endpoints/ios_import_api.py:278`](Backend/api/endpoints/ios_import_api.py#L278) | `required` |
| `POST` | `/scan` | [`Backend/api/endpoints/videos.py:523`](Backend/api/endpoints/videos.py#L523) | `required` |
| `POST` | `/scan` | [`Backend/api/trend_detection.py:134`](Backend/api/trend_detection.py#L134) | `required` |
| `GET` | `/scan-incomplete` | [`Backend/api/endpoints/analysis_health.py:234`](Backend/api/endpoints/analysis_health.py#L234) | `read` |
| `POST` | `/scan/cancel/{scan_id}` | [`Backend/api/endpoints/videos.py:769`](Backend/api/endpoints/videos.py#L769) | `required` |
| `GET` | `/scan/status` | [`Backend/api/endpoints/videos.py:781`](Backend/api/endpoints/videos.py#L781) | `read` |
| `GET` | `/scene-roles` | [`Backend/api/endpoints/creative_briefs.py:436`](Backend/api/endpoints/creative_briefs.py#L436) | `read` |
| `GET` | `/schedule` | [`Backend/api/comment_automation.py:744`](Backend/api/comment_automation.py#L744) | `read` |
| `GET` | `/schedule` | [`Backend/api/content_pipeline.py:481`](Backend/api/content_pipeline.py#L481) | `read` |
| `GET` | `/schedule` | [`Backend/api/endpoints/adaptive_scheduler.py:134`](Backend/api/endpoints/adaptive_scheduler.py#L134) | `read` |
| `GET` | `/schedule` | [`Backend/api/routes/sora_automation.py:229`](Backend/api/routes/sora_automation.py#L229) | `read` |
| `POST` | `/schedule` | [`Backend/api/content_pipeline.py:450`](Backend/api/content_pipeline.py#L450) | `required` |
| `POST` | `/schedule` | [`Backend/api/endpoints/calendar.py:108`](Backend/api/endpoints/calendar.py#L108) | `required` |
| `POST` | `/schedule` | [`Backend/api/endpoints/publishing.py:87`](Backend/api/endpoints/publishing.py#L87) | `required` |
| `POST` | `/schedule` | [`Backend/api/endpoints/twitter_posting.py:204`](Backend/api/endpoints/twitter_posting.py#L204) | `required` |
| `POST` | `/schedule` | [`Backend/api/routes/sora_automation.py:236`](Backend/api/routes/sora_automation.py#L236) | `required` |
| `POST` | `/schedule` | [`Backend/routers/twitter_campaign.py:112`](Backend/routers/twitter_campaign.py#L112) | `required` |
| `POST` | `/schedule` | [`Backend/routers/visual_campaign.py:67`](Backend/routers/visual_campaign.py#L67) | `required` |
| `POST` | `/schedule-7-day-plan` | [`Backend/api/endpoints/narrative_builder.py:970`](Backend/api/endpoints/narrative_builder.py#L970) | `required` |
| `POST` | `/schedule-checkbacks/{post_id}` | [`Backend/api/endpoints/platform_publishing.py:420`](Backend/api/endpoints/platform_publishing.py#L420) | `required` |
| `POST` | `/schedule-from-plan` | [`Backend/api/endpoints/narrative_builder.py:1435`](Backend/api/endpoints/narrative_builder.py#L1435) | `required` |
| `POST` | `/schedule-variant` | [`Backend/api/endpoints/experiments.py:1306`](Backend/api/endpoints/experiments.py#L1306) | `required` |
| `POST` | `/schedule-wake` | [`Backend/api/endpoints/sleep.py:131`](Backend/api/endpoints/sleep.py#L131) | `required` |
| `GET` | `/schedule/7days` | [`Backend/api/endpoints/adaptive_scheduler.py:146`](Backend/api/endpoints/adaptive_scheduler.py#L146) | `read` |
| `GET` | `/schedule/suggest` | [`Backend/api/endpoints/posting_optimizer_api.py:130`](Backend/api/endpoints/posting_optimizer_api.py#L130) | `read` |
| `POST` | `/schedule/{comment_id}` | [`Backend/api/comment_automation.py:681`](Backend/api/comment_automation.py#L681) | `required` |
| `DELETE` | `/schedule/{job_id}` | [`Backend/api/routes/sora_automation.py:261`](Backend/api/routes/sora_automation.py#L261) | `required` |
| `GET` | `/scheduled` | [`Backend/api/endpoints/content_ideas_api.py:378`](Backend/api/endpoints/content_ideas_api.py#L378) | `read` |
| `GET` | `/scheduled` | [`Backend/api/endpoints/publishing.py:597`](Backend/api/endpoints/publishing.py#L597) | `read` |
| `GET` | `/scheduler/agent/actions` | [`Backend/api/endpoints/experiments.py:1775`](Backend/api/endpoints/experiments.py#L1775) | `read` |
| `POST` | `/scheduler/create` | [`Backend/api/endpoints/experiments.py:1720`](Backend/api/endpoints/experiments.py#L1720) | `required` |
| `POST` | `/scheduler/plan` | [`Backend/api/endpoints/experiments.py:1742`](Backend/api/endpoints/experiments.py#L1742) | `required` |
| `POST` | `/scheduler/process-now` | [`Backend/api/endpoints/schedule.py:1196`](Backend/api/endpoints/schedule.py#L1196) | `required` |
| `GET` | `/scheduler/queue` | [`Backend/api/endpoints/schedule.py:1187`](Backend/api/endpoints/schedule.py#L1187) | `read` |
| `POST` | `/scheduler/run-now` | [`Backend/api/endpoints/trend_intelligence.py:802`](Backend/api/endpoints/trend_intelligence.py#L802) | `required` |
| `POST` | `/scheduler/start` | [`Backend/api/endpoints/agent_panel.py:179`](Backend/api/endpoints/agent_panel.py#L179) | `required` |
| `POST` | `/scheduler/start` | [`Backend/api/endpoints/trend_intelligence.py:775`](Backend/api/endpoints/trend_intelligence.py#L775) | `required` |
| `POST` | `/scheduler/start` | [`Backend/api/routes/sora_automation.py:271`](Backend/api/routes/sora_automation.py#L271) | `required` |
| `POST` | `/scheduler/start` | [`Backend/routers/twitter_campaign.py:46`](Backend/routers/twitter_campaign.py#L46) | `required` |
| `GET` | `/scheduler/status` | [`Backend/api/endpoints/competitor_api.py:468`](Backend/api/endpoints/competitor_api.py#L468) | `read` |
| `GET` | `/scheduler/status` | [`Backend/api/endpoints/schedule.py:1178`](Backend/api/endpoints/schedule.py#L1178) | `read` |
| `GET` | `/scheduler/status` | [`Backend/api/endpoints/trend_intelligence.py:814`](Backend/api/endpoints/trend_intelligence.py#L814) | `read` |
| `GET` | `/scheduler/status` | [`Backend/routers/twitter_campaign.py:72`](Backend/routers/twitter_campaign.py#L72) | `read` |
| `POST` | `/scheduler/stop` | [`Backend/api/endpoints/agent_panel.py:192`](Backend/api/endpoints/agent_panel.py#L192) | `required` |
| `POST` | `/scheduler/stop` | [`Backend/api/endpoints/trend_intelligence.py:793`](Backend/api/endpoints/trend_intelligence.py#L793) | `required` |
| `POST` | `/scheduler/stop` | [`Backend/api/routes/sora_automation.py:278`](Backend/api/routes/sora_automation.py#L278) | `required` |
| `POST` | `/scheduler/stop` | [`Backend/routers/twitter_campaign.py:59`](Backend/routers/twitter_campaign.py#L59) | `required` |
| `POST` | `/scheduler/sync-all` | [`Backend/api/endpoints/competitor_api.py:475`](Backend/api/endpoints/competitor_api.py#L475) | `required` |
| `POST` | `/scheduler/sync/{username}` | [`Backend/api/endpoints/competitor_api.py:493`](Backend/api/endpoints/competitor_api.py#L493) | `required` |
| `POST` | `/scheduler/task/{task_id}/interval` | [`Backend/api/endpoints/agent_panel.py:266`](Backend/api/endpoints/agent_panel.py#L266) | `required` |
| `POST` | `/scheduler/task/{task_id}/pause` | [`Backend/api/endpoints/agent_panel.py:217`](Backend/api/endpoints/agent_panel.py#L217) | `required` |
| `POST` | `/scheduler/task/{task_id}/resume` | [`Backend/api/endpoints/agent_panel.py:232`](Backend/api/endpoints/agent_panel.py#L232) | `required` |
| `POST` | `/scheduler/task/{task_id}/run` | [`Backend/api/endpoints/agent_panel.py:247`](Backend/api/endpoints/agent_panel.py#L247) | `required` |
| `GET` | `/scheduler/tasks` | [`Backend/api/endpoints/agent_panel.py:205`](Backend/api/endpoints/agent_panel.py#L205) | `read` |
| `GET` | `/scheduler/{experiment_id}/analyze` | [`Backend/api/endpoints/experiments.py:1798`](Backend/api/endpoints/experiments.py#L1798) | `read` |
| `POST` | `/scheduler/{experiment_id}/start` | [`Backend/api/endpoints/experiments.py:1784`](Backend/api/endpoints/experiments.py#L1784) | `required` |
| `GET` | `/schedules` | [`Backend/api/endpoints/automation.py:68`](Backend/api/endpoints/automation.py#L68) | `read` |
| `POST` | `/schedules/{schedule_id}/run` | [`Backend/api/endpoints/automation.py:149`](Backend/api/endpoints/automation.py#L149) | `required` |
| `POST` | `/schedules/{schedule_id}/toggle` | [`Backend/api/endpoints/automation.py:112`](Backend/api/endpoints/automation.py#L112) | `required` |
| `GET` | `/scored` | [`Backend/api/endpoints/hook_library_api.py:185`](Backend/api/endpoints/hook_library_api.py#L185) | `read` |
| `POST` | `/scores/calculate` | [`Backend/api/endpoints/trends_api.py:535`](Backend/api/endpoints/trends_api.py#L535) | `required` |
| `POST` | `/scrape-and-match` | [`Backend/api/endpoints/posted_content_matcher.py:37`](Backend/api/endpoints/posted_content_matcher.py#L37) | `required` |
| `POST` | `/scrape-background` | [`Backend/api/endpoints/posted_content_matcher.py:264`](Backend/api/endpoints/posted_content_matcher.py#L264) | `required` |
| `GET` | `/scrape-status/{job_id}` | [`Backend/api/endpoints/posted_content_matcher.py:293`](Backend/api/endpoints/posted_content_matcher.py#L293) | `read` |
| `POST` | `/scrape/safari/{username}` | [`Backend/api/endpoints/competitor_api.py:600`](Backend/api/endpoints/competitor_api.py#L600) | `required` |
| `GET` | `/script` | [`Backend/api/endpoints/reeltrends.py:359`](Backend/api/endpoints/reeltrends.py#L359) | `read` |
| `POST` | `/script` | [`Backend/api/endpoints/reeltrends.py:150`](Backend/api/endpoints/reeltrends.py#L150) | `required` |
| `GET` | `/scripts` | [`Backend/api/endpoints/safari_automation.py:382`](Backend/api/endpoints/safari_automation.py#L382) | `read` |
| `GET` | `/scripts` | [`Backend/api/endpoints/sora_daily.py:703`](Backend/api/endpoints/sora_daily.py#L703) | `read` |
| `GET` | `/scripts` | [`Backend/api/endpoints/ugc_content.py:136`](Backend/api/endpoints/ugc_content.py#L136) | `read` |
| `POST` | `/scripts` | [`Backend/api/endpoints/video_orchestrator.py:320`](Backend/api/endpoints/video_orchestrator.py#L320) | `required` |
| `POST` | `/scripts/bulk-queue` | [`Backend/api/endpoints/ugc_content.py:238`](Backend/api/endpoints/ugc_content.py#L238) | `required` |
| `POST` | `/scripts/estimate` | [`Backend/api/endpoints/video_orchestrator.py:362`](Backend/api/endpoints/video_orchestrator.py#L362) | `required` |
| `POST` | `/scripts/generate` | [`Backend/api/endpoints/safari_automation.py:310`](Backend/api/endpoints/safari_automation.py#L310) | `required` |
| `POST` | `/scripts/generate` | [`Backend/api/endpoints/sora_daily.py:602`](Backend/api/endpoints/sora_daily.py#L602) | `required` |
| `POST` | `/scripts/generate-now` | [`Backend/api/endpoints/safari_automation.py:349`](Backend/api/endpoints/safari_automation.py#L349) | `required` |
| `POST` | `/scripts/generate-sync` | [`Backend/api/endpoints/sora_daily.py:664`](Backend/api/endpoints/sora_daily.py#L664) | `required` |
| `DELETE` | `/scripts/{script_id}` | [`Backend/api/endpoints/sora_daily.py:787`](Backend/api/endpoints/sora_daily.py#L787) | `required` |
| `DELETE` | `/scripts/{script_id}` | [`Backend/api/endpoints/ugc_content.py:199`](Backend/api/endpoints/ugc_content.py#L199) | `required` |
| `GET` | `/scripts/{script_id}` | [`Backend/api/endpoints/sora_daily.py:736`](Backend/api/endpoints/sora_daily.py#L736) | `read` |
| `GET` | `/scripts/{script_id}` | [`Backend/api/endpoints/ugc_content.py:158`](Backend/api/endpoints/ugc_content.py#L158) | `read` |
| `GET` | `/scripts/{script_id}` | [`Backend/api/endpoints/video_orchestrator.py:354`](Backend/api/endpoints/video_orchestrator.py#L354) | `read` |
| `PATCH` | `/scripts/{script_id}` | [`Backend/api/endpoints/ugc_content.py:168`](Backend/api/endpoints/ugc_content.py#L168) | `required` |
| `POST` | `/scripts/{script_id}/queue` | [`Backend/api/endpoints/safari_automation.py:398`](Backend/api/endpoints/safari_automation.py#L398) | `required` |
| `POST` | `/scripts/{script_id}/queue` | [`Backend/api/endpoints/ugc_content.py:213`](Backend/api/endpoints/ugc_content.py#L213) | `required` |
| `PATCH` | `/scripts/{script_id}/status` | [`Backend/api/endpoints/sora_daily.py:762`](Backend/api/endpoints/sora_daily.py#L762) | `required` |
| `PATCH` | `/scripts/{script_id}/status` | [`Backend/api/endpoints/ugc_content.py:182`](Backend/api/endpoints/ugc_content.py#L182) | `required` |
| `GET` | `/search` | [`Backend/api/endpoints/instagram_api.py:227`](Backend/api/endpoints/instagram_api.py#L227) | `read` |
| `GET` | `/search` | [`Backend/api/endpoints/instagram_trends.py:243`](Backend/api/endpoints/instagram_trends.py#L243) | `read` |
| `GET` | `/search` | [`Backend/api/endpoints/media_assets.py:184`](Backend/api/endpoints/media_assets.py#L184) | `read` |
| `GET` | `/search` | [`Backend/api/endpoints/music_library.py:217`](Backend/api/endpoints/music_library.py#L217) | `read` |
| `POST` | `/search` | [`Backend/api/endpoints/music_crawler.py:177`](Backend/api/endpoints/music_crawler.py#L177) | `required` |
| `POST` | `/search` | [`Backend/api/endpoints/sfx_library.py:201`](Backend/api/endpoints/sfx_library.py#L201) | `required` |
| `POST` | `/search/competitors` | [`Backend/api/endpoints/semantic_search.py:215`](Backend/api/endpoints/semantic_search.py#L215) | `required` |
| `POST` | `/search/hooks` | [`Backend/api/endpoints/semantic_search.py:168`](Backend/api/endpoints/semantic_search.py#L168) | `required` |
| `POST` | `/search/videos` | [`Backend/api/endpoints/semantic_search.py:121`](Backend/api/endpoints/semantic_search.py#L121) | `required` |
| `GET` | `/security/providers` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:666`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L666) | `read` |
| `POST` | `/seed-demo-data` | [`Backend/api/endpoints/experiments.py:879`](Backend/api/endpoints/experiments.py#L879) | `required` |
| `POST` | `/seed-samples` | [`Backend/api/endpoints/formats.py:512`](Backend/api/endpoints/formats.py#L512) | `required` |
| `POST` | `/seed-samples` | [`Backend/api/endpoints/formats_api.py:123`](Backend/api/endpoints/formats_api.py#L123) | `required` |
| `GET` | `/segments` | [`Backend/api/endpoints/adaptive_scheduler.py:487`](Backend/api/endpoints/adaptive_scheduler.py#L487) | `read` |
| `POST` | `/segments` | [`Backend/api/endpoints/enhanced_analysis.py:136`](Backend/api/endpoints/enhanced_analysis.py#L136) | `required` |
| `POST` | `/segments/merge` | [`Backend/api/endpoints/enhanced_analysis.py:220`](Backend/api/endpoints/enhanced_analysis.py#L220) | `required` |
| `DELETE` | `/segments/{segment_id}` | [`Backend/api/endpoints/enhanced_analysis.py:179`](Backend/api/endpoints/enhanced_analysis.py#L179) | `required` |
| `PUT` | `/segments/{segment_id}` | [`Backend/api/endpoints/enhanced_analysis.py:159`](Backend/api/endpoints/enhanced_analysis.py#L159) | `required` |
| `GET` | `/segments/{segment_id}/performance` | [`Backend/api/endpoints/enhanced_analysis.py:241`](Backend/api/endpoints/enhanced_analysis.py#L241) | `read` |
| `POST` | `/segments/{segment_id}/split` | [`Backend/api/endpoints/enhanced_analysis.py:197`](Backend/api/endpoints/enhanced_analysis.py#L197) | `required` |
| `POST` | `/select-best-frame` | [`Backend/api/endpoints/thumbnails.py:85`](Backend/api/endpoints/thumbnails.py#L85) | `required` |
| `POST` | `/selection-prompt` | [`Backend/api/endpoints/sfx_library.py:332`](Backend/api/endpoints/sfx_library.py#L332) | `required` |
| `GET` | `/selectors` | [`Backend/api/endpoints/twitter_posting.py:338`](Backend/api/endpoints/twitter_posting.py#L338) | `read` |
| `POST` | `/selectors/test` | [`Backend/api/endpoints/twitter_posting.py:374`](Backend/api/endpoints/twitter_posting.py#L374) | `required` |
| `GET` | `/selectors/{category}` | [`Backend/api/endpoints/twitter_posting.py:352`](Backend/api/endpoints/twitter_posting.py#L352) | `read` |
| `POST` | `/send` | [`Backend/api/endpoints/email.py:66`](Backend/api/endpoints/email.py#L66) | `required` |
| `POST` | `/send` | [`Backend/api/endpoints/messages.py:42`](Backend/api/endpoints/messages.py#L42) | `required` |
| `POST` | `/send-segment` | [`Backend/api/endpoints/email.py:120`](Backend/api/endpoints/email.py#L120) | `required` |
| `GET` | `/sentiment-stats` | [`Backend/api/endpoints/batch_analysis.py:108`](Backend/api/endpoints/batch_analysis.py#L108) | `read` |
| `GET` | `/services` | [`Backend/api/endpoints/automation.py:391`](Backend/api/endpoints/automation.py#L391) | `read` |
| `GET` | `/services` | [`Backend/api/endpoints/safari_automation.py:237`](Backend/api/endpoints/safari_automation.py#L237) | `read` |
| `POST` | `/session/start` | [`Backend/api/endpoints/instagram_automation.py:154`](Backend/api/endpoints/instagram_automation.py#L154) | `required` |
| `POST` | `/session/start` | [`Backend/api/endpoints/tiktok_automation.py:140`](Backend/api/endpoints/tiktok_automation.py#L140) | `required` |
| `POST` | `/session/start` | [`Backend/api/endpoints/twitter_automation.py:120`](Backend/api/endpoints/twitter_automation.py#L120) | `required` |
| `POST` | `/session/start` | [`Backend/api/engagement_autopilot.py:120`](Backend/api/engagement_autopilot.py#L120) | `required` |
| `POST` | `/session/{session_id}/stop` | [`Backend/api/engagement_autopilot.py:128`](Backend/api/engagement_autopilot.py#L128) | `required` |
| `GET` | `/settings` | [`Backend/api/approval_queue.py:445`](Backend/api/approval_queue.py#L445) | `read` |
| `GET` | `/settings` | [`Backend/api/engagement_autopilot.py:136`](Backend/api/engagement_autopilot.py#L136) | `read` |
| `PUT` | `/settings` | [`Backend/api/approval_queue.py:451`](Backend/api/approval_queue.py#L451) | `required` |
| `PUT` | `/settings` | [`Backend/api/endpoints/post_scheduler_api.py:215`](Backend/api/endpoints/post_scheduler_api.py#L215) | `required` |
| `PUT` | `/settings` | [`Backend/api/engagement_autopilot.py:144`](Backend/api/engagement_autopilot.py#L144) | `required` |
| `GET` | `/settings/presets` | [`Backend/api/approval_queue.py:459`](Backend/api/approval_queue.py#L459) | `read` |
| `POST` | `/ship/{cluster_id}` | [`Backend/api/endpoints/trend_flash.py:349`](Backend/api/endpoints/trend_flash.py#L349) | `required` |
| `POST` | `/shot-plan` | [`Backend/api/endpoints/video_pipeline.py:293`](Backend/api/endpoints/video_pipeline.py#L293) | `required` |
| `POST` | `/shuffle/{media_id}` | [`Backend/api/endpoints/music_matching.py:283`](Backend/api/endpoints/music_matching.py#L283) | `required` |
| `GET` | `/signals` | [`Backend/api/endpoints/narrative_builder.py:72`](Backend/api/endpoints/narrative_builder.py#L72) | `read` |
| `POST` | `/single` | [`Backend/api/endpoints/content_download.py:52`](Backend/api/endpoints/content_download.py#L52) | `required` |
| `POST` | `/skip-images` | [`Backend/api/endpoints/analysis_health.py:298`](Backend/api/endpoints/analysis_health.py#L298) | `required` |
| `POST` | `/sleep/sync` | [`Backend/api/endpoints/adaptive_scheduler.py:601`](Backend/api/endpoints/adaptive_scheduler.py#L601) | `required` |
| `DELETE` | `/slot` | [`Backend/api/endpoints/adaptive_scheduler.py:927`](Backend/api/endpoints/adaptive_scheduler.py#L927) | `required` |
| `POST` | `/slot` | [`Backend/api/endpoints/adaptive_scheduler.py:902`](Backend/api/endpoints/adaptive_scheduler.py#L902) | `required` |
| `PUT` | `/slot` | [`Backend/api/endpoints/adaptive_scheduler.py:913`](Backend/api/endpoints/adaptive_scheduler.py#L913) | `required` |
| `GET` | `/slots` | [`Backend/api/endpoints/content_loop.py:334`](Backend/api/endpoints/content_loop.py#L334) | `read` |
| `POST` | `/slots` | [`Backend/api/endpoints/content_loop.py:357`](Backend/api/endpoints/content_loop.py#L357) | `required` |
| `PATCH` | `/slots/{slot_id}` | [`Backend/api/endpoints/content_mix_api.py:211`](Backend/api/endpoints/content_mix_api.py#L211) | `required` |
| `POST` | `/slots/{slot_id}/assign` | [`Backend/api/endpoints/content_loop.py:378`](Backend/api/endpoints/content_loop.py#L378) | `required` |
| `POST` | `/smart-bulk` | [`Backend/api/endpoints/external_scheduling.py:694`](Backend/api/endpoints/external_scheduling.py#L694) | `required` |
| `POST` | `/smart-schedule` | [`Backend/api/endpoints/external_scheduling.py:587`](Backend/api/endpoints/external_scheduling.py#L587) | `required` |
| `GET` | `/sora` | [`Backend/api/endpoints/daily_automation.py:35`](Backend/api/endpoints/daily_automation.py#L35) | `read` |
| `POST` | `/sora-daily` | [`Backend/api/endpoints/adaptive_scheduler.py:681`](Backend/api/endpoints/adaptive_scheduler.py#L681) | `required` |
| `POST` | `/sora-ready` | [`Backend/services/video_ready_pipeline.py:961`](Backend/services/video_ready_pipeline.py#L961) | `required` |
| `POST` | `/sora/check-credits` | [`Backend/api/endpoints/daily_automation.py:42`](Backend/api/endpoints/daily_automation.py#L42) | `required` |
| `POST` | `/sora/generate` | [`Backend/api/endpoints/adaptive_scheduler.py:593`](Backend/api/endpoints/adaptive_scheduler.py#L593) | `required` |
| `POST` | `/sora/generate` | [`Backend/api/endpoints/safari_automation.py:191`](Backend/api/endpoints/safari_automation.py#L191) | `required` |
| `POST` | `/sora/generate` | [`Backend/api/endpoints/video_orchestrator.py:583`](Backend/api/endpoints/video_orchestrator.py#L583) | `required` |
| `GET` | `/sora/history` | [`Backend/api/endpoints/video_orchestrator.py:749`](Backend/api/endpoints/video_orchestrator.py#L749) | `read` |
| `POST` | `/sora/optimize-prompt` | [`Backend/api/endpoints/video_orchestrator.py:724`](Backend/api/endpoints/video_orchestrator.py#L724) | `required` |
| `POST` | `/sora/remix` | [`Backend/api/endpoints/video_orchestrator.py:645`](Backend/api/endpoints/video_orchestrator.py#L645) | `required` |
| `GET` | `/sora/videos/{video_id}` | [`Backend/api/endpoints/video_orchestrator.py:692`](Backend/api/endpoints/video_orchestrator.py#L692) | `read` |
| `GET` | `/sounds` | [`Backend/api/endpoints/instagram_trends.py:181`](Backend/api/endpoints/instagram_trends.py#L181) | `read` |
| `GET` | `/sounds` | [`Backend/api/endpoints/trends.py:161`](Backend/api/endpoints/trends.py#L161) | `read` |
| `POST` | `/sounds` | [`Backend/api/endpoints/trends.py:184`](Backend/api/endpoints/trends.py#L184) | `required` |
| `POST` | `/sounds/analyze` | [`Backend/api/endpoints/reeltrends.py:766`](Backend/api/endpoints/reeltrends.py#L766) | `required` |
| `GET` | `/sounds/for-niche` | [`Backend/api/endpoints/reeltrends.py:827`](Backend/api/endpoints/reeltrends.py#L827) | `read` |
| `POST` | `/sounds/for-niche` | [`Backend/api/endpoints/reeltrends.py:794`](Backend/api/endpoints/reeltrends.py#L794) | `required` |
| `GET` | `/sounds/of-the-day` | [`Backend/api/endpoints/reeltrends.py:756`](Backend/api/endpoints/reeltrends.py#L756) | `read` |
| `POST` | `/sounds/of-the-day` | [`Backend/api/endpoints/reeltrends.py:717`](Backend/api/endpoints/reeltrends.py#L717) | `required` |
| `GET` | `/sounds/trending` | [`Backend/api/endpoints/reeltrends.py:670`](Backend/api/endpoints/reeltrends.py#L670) | `read` |
| `GET` | `/source-types` | [`Backend/api/endpoints/remotion.py:200`](Backend/api/endpoints/remotion.py#L200) | `read` |
| `GET` | `/sources` | [`Backend/api/endpoints/music.py:110`](Backend/api/endpoints/music.py#L110) | `read` |
| `GET` | `/sources` | [`Backend/api/endpoints/repurpose.py:274`](Backend/api/endpoints/repurpose.py#L274) | `read` |
| `GET` | `/sources` | [`Backend/api/endpoints/trend_intelligence.py:754`](Backend/api/endpoints/trend_intelligence.py#L754) | `read` |
| `GET` | `/sources` | [`Backend/api/endpoints/visuals.py:122`](Backend/api/endpoints/visuals.py#L122) | `read` |
| `POST` | `/sources` | [`Backend/api/endpoints/trend_intelligence.py:736`](Backend/api/endpoints/trend_intelligence.py#L736) | `required` |
| `GET` | `/sources/status` | [`Backend/api/endpoints/trends.py:818`](Backend/api/endpoints/trends.py#L818) | `read` |
| `DELETE` | `/sources/{source_id}` | [`Backend/api/endpoints/repurpose.py:386`](Backend/api/endpoints/repurpose.py#L386) | `required` |
| `DELETE` | `/sources/{source_id}` | [`Backend/api/endpoints/trend_intelligence.py:766`](Backend/api/endpoints/trend_intelligence.py#L766) | `required` |
| `GET` | `/sources/{source_id}` | [`Backend/api/endpoints/repurpose.py:144`](Backend/api/endpoints/repurpose.py#L144) | `read` |
| `POST` | `/sourcing/folders/add` | [`Backend/api/content_pipeline.py:959`](Backend/api/content_pipeline.py#L959) | `required` |
| `DELETE` | `/sourcing/folders/remove` | [`Backend/api/content_pipeline.py:980`](Backend/api/content_pipeline.py#L980) | `required` |
| `POST` | `/sourcing/import-file` | [`Backend/api/content_pipeline.py:1027`](Backend/api/content_pipeline.py#L1027) | `required` |
| `POST` | `/sourcing/scan` | [`Backend/api/content_pipeline.py:1001`](Backend/api/content_pipeline.py#L1001) | `required` |
| `GET` | `/sourcing/status` | [`Backend/api/content_pipeline.py:940`](Backend/api/content_pipeline.py#L940) | `read` |
| `POST` | `/staging/cleanup` | [`Backend/api/endpoints/vault_api.py:560`](Backend/api/endpoints/vault_api.py#L560) | `required` |
| `GET` | `/staging/usage` | [`Backend/api/endpoints/vault_api.py:595`](Backend/api/endpoints/vault_api.py#L595) | `read` |
| `POST` | `/start` | [`Backend/api/endpoints/analysis_scheduler.py:36`](Backend/api/endpoints/analysis_scheduler.py#L36) | `required` |
| `POST` | `/start` | [`Backend/api/endpoints/android_import_api.py:303`](Backend/api/endpoints/android_import_api.py#L303) | `required` |
| `POST` | `/start` | [`Backend/api/endpoints/autonomous_executor.py:46`](Backend/api/endpoints/autonomous_executor.py#L46) | `required` |
| `POST` | `/start` | [`Backend/api/endpoints/competitor_audit.py:55`](Backend/api/endpoints/competitor_audit.py#L55) | `required` |
| `POST` | `/start` | [`Backend/api/endpoints/daily_automation.py:19`](Backend/api/endpoints/daily_automation.py#L19) | `required` |
| `POST` | `/start` | [`Backend/api/endpoints/engagement_control.py:39`](Backend/api/endpoints/engagement_control.py#L39) | `required` |
| `POST` | `/start` | [`Backend/api/endpoints/ingestion.py:36`](Backend/api/endpoints/ingestion.py#L36) | `required` |
| `POST` | `/start` | [`Backend/api/endpoints/ios_import_api.py:344`](Backend/api/endpoints/ios_import_api.py#L344) | `required` |
| `POST` | `/start` | [`Backend/api/endpoints/post_scheduler_api.py:53`](Backend/api/endpoints/post_scheduler_api.py#L53) | `required` |
| `POST` | `/start` | [`Backend/api/endpoints/safari_automation.py:56`](Backend/api/endpoints/safari_automation.py#L56) | `required` |
| `POST` | `/start` | [`Backend/api/endpoints/sora_daily.py:68`](Backend/api/endpoints/sora_daily.py#L68) | `required` |
| `GET` | `/startup` | [`Backend/api/endpoints/health.py:361`](Backend/api/endpoints/health.py#L361) | `read` |
| `POST` | `/startup/verify` | [`Backend/api/endpoints/health.py:392`](Backend/api/endpoints/health.py#L392) | `required` |
| `GET` | `/states` | [`Backend/api/endpoints/agent_panel.py:404`](Backend/api/endpoints/agent_panel.py#L404) | `read` |
| `GET` | `/stats` | [`Backend/api/approval_queue.py:247`](Backend/api/approval_queue.py#L247) | `read` |
| `GET` | `/stats` | [`Backend/api/cascade_publisher.py:155`](Backend/api/cascade_publisher.py#L155) | `read` |
| `GET` | `/stats` | [`Backend/api/comment_automation.py:992`](Backend/api/comment_automation.py#L992) | `read` |
| `GET` | `/stats` | [`Backend/api/content_recycling.py:104`](Backend/api/content_recycling.py#L104) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/android_import_api.py:179`](Backend/api/endpoints/android_import_api.py#L179) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/approval_queue.py:357`](Backend/api/endpoints/approval_queue.py#L357) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/auto_curator.py:276`](Backend/api/endpoints/auto_curator.py#L276) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/automations.py:311`](Backend/api/endpoints/automations.py#L311) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/backup.py:197`](Backend/api/endpoints/backup.py#L197) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/broll.py:272`](Backend/api/endpoints/broll.py#L272) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/community_inbox.py:377`](Backend/api/endpoints/community_inbox.py#L377) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/content_analyzer_api.py:337`](Backend/api/endpoints/content_analyzer_api.py#L337) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/content_format.py:286`](Backend/api/endpoints/content_format.py#L286) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/dm_outreach.py:475`](Backend/api/endpoints/dm_outreach.py#L475) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/event_history.py:324`](Backend/api/endpoints/event_history.py#L324) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/events.py:44`](Backend/api/endpoints/events.py#L44) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/experiments.py:183`](Backend/api/endpoints/experiments.py#L183) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/inbox.py:432`](Backend/api/endpoints/inbox.py#L432) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/ios_import_api.py:246`](Backend/api/endpoints/ios_import_api.py#L246) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/media_assets.py:346`](Backend/api/endpoints/media_assets.py#L346) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/media_provider.py:161`](Backend/api/endpoints/media_provider.py#L161) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/orchestrator.py:302`](Backend/api/endpoints/orchestrator.py#L302) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/pubsub_inspector.py:136`](Backend/api/endpoints/pubsub_inspector.py#L136) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/semantic_search.py:417`](Backend/api/endpoints/semantic_search.py#L417) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/storage.py:22`](Backend/api/endpoints/storage.py#L22) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/template_leaderboard.py:203`](Backend/api/endpoints/template_leaderboard.py#L203) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/trend_flash.py:242`](Backend/api/endpoints/trend_flash.py#L242) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/trends_agent.py:398`](Backend/api/endpoints/trends_agent.py#L398) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/trends_api.py:608`](Backend/api/endpoints/trends_api.py#L608) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/ugc_content.py:278`](Backend/api/endpoints/ugc_content.py#L278) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/workflows.py:48`](Backend/api/endpoints/workflows.py#L48) | `read` |
| `GET` | `/stats` | [`Backend/api/endpoints/youtube_automation.py:99`](Backend/api/endpoints/youtube_automation.py#L99) | `read` |
| `GET` | `/stats` | [`Backend/api/engagement_autopilot.py:152`](Backend/api/engagement_autopilot.py#L152) | `read` |
| `GET` | `/stats` | [`Backend/api/media_processing_db.py:772`](Backend/api/media_processing_db.py#L772) | `read` |
| `GET` | `/stats` | [`Backend/routers/visual_campaign.py:124`](Backend/routers/visual_campaign.py#L124) | `read` |
| `GET` | `/stats/by-origin` | [`Backend/api/endpoints/calendar.py:399`](Backend/api/endpoints/calendar.py#L399) | `read` |
| `GET` | `/stats/overview` | [`Backend/api/endpoints/schedule.py:801`](Backend/api/endpoints/schedule.py#L801) | `read` |
| `GET` | `/stats/overview` | [`Backend/api/endpoints/templates.py:580`](Backend/api/endpoints/templates.py#L580) | `read` |
| `GET` | `/stats/summary` | [`Backend/api/endpoints/music_library.py:391`](Backend/api/endpoints/music_library.py#L391) | `read` |
| `GET` | `/stats/today` | [`Backend/api/endpoints/safari_automation.py:132`](Backend/api/endpoints/safari_automation.py#L132) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/accounts.py:384`](Backend/api/endpoints/accounts.py#L384) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/adaptive_scheduler.py:126`](Backend/api/endpoints/adaptive_scheduler.py#L126) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/agent_panel.py:21`](Backend/api/endpoints/agent_panel.py#L21) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/analysis_health.py:16`](Backend/api/endpoints/analysis_health.py#L16) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/analysis_scheduler.py:29`](Backend/api/endpoints/analysis_scheduler.py#L29) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/autonomous_executor.py:19`](Backend/api/endpoints/autonomous_executor.py#L19) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/autonomy.py:314`](Backend/api/endpoints/autonomy.py#L314) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/bandit.py:162`](Backend/api/endpoints/bandit.py#L162) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/content_ingestion.py:137`](Backend/api/endpoints/content_ingestion.py#L137) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/content_runway.py:65`](Backend/api/endpoints/content_runway.py#L65) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/content_sourcing.py:148`](Backend/api/endpoints/content_sourcing.py#L148) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/cpu_monitor.py:30`](Backend/api/endpoints/cpu_monitor.py#L30) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/daily_automation.py:12`](Backend/api/endpoints/daily_automation.py#L12) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/data_hydration.py:22`](Backend/api/endpoints/data_hydration.py#L22) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/data_orchestrator.py:32`](Backend/api/endpoints/data_orchestrator.py#L32) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/db_health.py:31`](Backend/api/endpoints/db_health.py#L31) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/email.py:23`](Backend/api/endpoints/email.py#L23) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/engagement_control.py:28`](Backend/api/endpoints/engagement_control.py#L28) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/ingestion.py:240`](Backend/api/endpoints/ingestion.py#L240) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/instagram_automation.py:247`](Backend/api/endpoints/instagram_automation.py#L247) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/inventory_scheduler.py:177`](Backend/api/endpoints/inventory_scheduler.py#L177) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/post_scheduler_api.py:46`](Backend/api/endpoints/post_scheduler_api.py#L46) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/publishing_controls.py:339`](Backend/api/endpoints/publishing_controls.py#L339) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/publishing_queue.py:206`](Backend/api/endpoints/publishing_queue.py#L206) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/rapidapi_comments.py:16`](Backend/api/endpoints/rapidapi_comments.py#L16) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/reply_suggestions.py:219`](Backend/api/endpoints/reply_suggestions.py#L219) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/safari_automation.py:114`](Backend/api/endpoints/safari_automation.py#L114) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/safari_sessions.py:369`](Backend/api/endpoints/safari_sessions.py#L369) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/sleep.py:42`](Backend/api/endpoints/sleep.py#L42) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/sora_daily.py:32`](Backend/api/endpoints/sora_daily.py#L32) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/strategic_analysis.py:145`](Backend/api/endpoints/strategic_analysis.py#L145) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/template_auto_forker.py:115`](Backend/api/endpoints/template_auto_forker.py#L115) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/template_retiree.py:148`](Backend/api/endpoints/template_retiree.py#L148) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/tiktok_analytics.py:20`](Backend/api/endpoints/tiktok_analytics.py#L20) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/tiktok_automation.py:226`](Backend/api/endpoints/tiktok_automation.py#L226) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/tiktok_repurpose.py:414`](Backend/api/endpoints/tiktok_repurpose.py#L414) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/twitter_automation.py:198`](Backend/api/endpoints/twitter_automation.py#L198) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/twitter_posting.py:66`](Backend/api/endpoints/twitter_posting.py#L66) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/vault_api.py:159`](Backend/api/endpoints/vault_api.py#L159) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/venv_status.py:21`](Backend/api/endpoints/venv_status.py#L21) | `read` |
| `GET` | `/status` | [`Backend/api/endpoints/youtube_analytics.py:162`](Backend/api/endpoints/youtube_analytics.py#L162) | `read` |
| `GET` | `/status` | [`Backend/api/metrics_scheduler_api.py:74`](Backend/api/metrics_scheduler_api.py#L74) | `read` |
| `GET` | `/status-summary` | [`Backend/api/endpoints/schedule.py:393`](Backend/api/endpoints/schedule.py#L393) | `read` |
| `GET` | `/status/{job_id}` | [`Backend/api/endpoints/matting.py:116`](Backend/api/endpoints/matting.py#L116) | `read` |
| `GET` | `/status/{job_id}` | [`Backend/api/endpoints/remotion.py:179`](Backend/api/endpoints/remotion.py#L179) | `read` |
| `GET` | `/status/{job_id}` | [`Backend/api/endpoints/sora.py:93`](Backend/api/endpoints/sora.py#L93) | `read` |
| `GET` | `/status/{job_id}` | [`Backend/api/endpoints/tts.py:115`](Backend/api/endpoints/tts.py#L115) | `read` |
| `GET` | `/status/{job_id}` | [`Backend/api/endpoints/video_render.py:211`](Backend/api/endpoints/video_render.py#L211) | `read` |
| `GET` | `/status/{media_id}` | [`Backend/api/media_processing.py:302`](Backend/api/media_processing.py#L302) | `read` |
| `GET` | `/status/{pipeline_id}` | [`Backend/api/endpoints/pipeline.py:96`](Backend/api/endpoints/pipeline.py#L96) | `read` |
| `GET` | `/status/{run_id}` | [`Backend/api/endpoints/competitor_audit.py:125`](Backend/api/endpoints/competitor_audit.py#L125) | `read` |
| `GET` | `/status/{source_id}` | [`Backend/api/endpoints/external_scheduling.py:479`](Backend/api/endpoints/external_scheduling.py#L479) | `read` |
| `POST` | `/stop` | [`Backend/api/endpoints/analysis_scheduler.py:77`](Backend/api/endpoints/analysis_scheduler.py#L77) | `required` |
| `POST` | `/stop` | [`Backend/api/endpoints/autonomous_executor.py:78`](Backend/api/endpoints/autonomous_executor.py#L78) | `required` |
| `POST` | `/stop` | [`Backend/api/endpoints/daily_automation.py:27`](Backend/api/endpoints/daily_automation.py#L27) | `required` |
| `POST` | `/stop` | [`Backend/api/endpoints/engagement_control.py:50`](Backend/api/endpoints/engagement_control.py#L50) | `required` |
| `POST` | `/stop` | [`Backend/api/endpoints/ingestion.py:227`](Backend/api/endpoints/ingestion.py#L227) | `required` |
| `POST` | `/stop` | [`Backend/api/endpoints/post_scheduler_api.py:67`](Backend/api/endpoints/post_scheduler_api.py#L67) | `required` |
| `POST` | `/stop` | [`Backend/api/endpoints/safari_automation.py:77`](Backend/api/endpoints/safari_automation.py#L77) | `required` |
| `POST` | `/story/generate-movie` | [`Backend/api/endpoints/sora_daily.py:334`](Backend/api/endpoints/sora_daily.py#L334) | `required` |
| `POST` | `/story/generate-single` | [`Backend/api/endpoints/sora_daily.py:307`](Backend/api/endpoints/sora_daily.py#L307) | `required` |
| `GET` | `/stream/{audio_id}` | [`Backend/api/endpoints/audio_api.py:87`](Backend/api/endpoints/audio_api.py#L87) | `read` |
| `GET` | `/stream/{media_id}` | [`Backend/api/endpoints/media_provider.py:72`](Backend/api/endpoints/media_provider.py#L72) | `read` |
| `GET` | `/style` | [`Backend/routers/twitter_campaign.py:226`](Backend/routers/twitter_campaign.py#L226) | `read` |
| `PUT` | `/style` | [`Backend/routers/twitter_campaign.py:234`](Backend/routers/twitter_campaign.py#L234) | `required` |
| `GET` | `/styles` | [`Backend/api/endpoints/ai_titles.py:243`](Backend/api/endpoints/ai_titles.py#L243) | `read` |
| `GET` | `/styles` | [`Backend/api/endpoints/ai_video_generation.py:701`](Backend/api/endpoints/ai_video_generation.py#L701) | `read` |
| `GET` | `/styles` | [`Backend/api/subtitles.py:44`](Backend/api/subtitles.py#L44) | `read` |
| `POST` | `/submit` | [`Backend/api/endpoints/external_scheduling.py:330`](Backend/api/endpoints/external_scheduling.py#L330) | `required` |
| `GET` | `/subscribers` | [`Backend/api/endpoints/events.py:51`](Backend/api/endpoints/events.py#L51) | `read` |
| `GET` | `/subscribers` | [`Backend/api/endpoints/pubsub_inspector.py:98`](Backend/api/endpoints/pubsub_inspector.py#L98) | `read` |
| `POST` | `/subtitles/generate` | [`Backend/api/endpoints/clip_extraction.py:435`](Backend/api/endpoints/clip_extraction.py#L435) | `required` |
| `POST` | `/subtitles/preview` | [`Backend/api/endpoints/clip_extraction.py:484`](Backend/api/endpoints/clip_extraction.py#L484) | `required` |
| `GET` | `/suggest` | [`Backend/api/endpoints/clip_management.py:58`](Backend/api/endpoints/clip_management.py#L58) | `read` |
| `GET` | `/suggest` | [`Backend/api/smart_posting_times.py:120`](Backend/api/smart_posting_times.py#L120) | `read` |
| `POST` | `/suggest` | [`Backend/api/endpoints/sfx_library.py:370`](Backend/api/endpoints/sfx_library.py#L370) | `required` |
| `POST` | `/suggest-goal` | [`Backend/api/endpoints/narrative_scheduler.py:124`](Backend/api/endpoints/narrative_scheduler.py#L124) | `required` |
| `POST` | `/suggest/{media_id}` | [`Backend/api/endpoints/music_matching.py:86`](Backend/api/endpoints/music_matching.py#L86) | `required` |
| `GET` | `/suggest/{track_id}` | [`Backend/api/endpoints/music_library.py:541`](Backend/api/endpoints/music_library.py#L541) | `read` |
| `DELETE` | `/suggestion/{media_id}` | [`Backend/api/endpoints/music_matching.py:443`](Backend/api/endpoints/music_matching.py#L443) | `required` |
| `GET` | `/suggestions/{category}` | [`Backend/api/endpoints/hashtag_generator_api.py:126`](Backend/api/endpoints/hashtag_generator_api.py#L126) | `read` |
| `GET` | `/summary` | [`Backend/api/content_growth.py:384`](Backend/api/content_growth.py#L384) | `read` |
| `GET` | `/summary` | [`Backend/api/endpoints/analytics.py:24`](Backend/api/endpoints/analytics.py#L24) | `read` |
| `GET` | `/summary` | [`Backend/api/endpoints/analytics_feedback.py:59`](Backend/api/endpoints/analytics_feedback.py#L59) | `read` |
| `GET` | `/summary` | [`Backend/api/endpoints/duplicate_detection.py:230`](Backend/api/endpoints/duplicate_detection.py#L230) | `read` |
| `GET` | `/summary` | [`Backend/api/endpoints/youtube_analytics.py:113`](Backend/api/endpoints/youtube_analytics.py#L113) | `read` |
| `GET` | `/swipe-file` | [`Backend/api/endpoints/competitor_api.py:1539`](Backend/api/endpoints/competitor_api.py#L1539) | `read` |
| `POST` | `/swipe-file` | [`Backend/api/endpoints/competitor_api.py:1550`](Backend/api/endpoints/competitor_api.py#L1550) | `required` |
| `DELETE` | `/swipe-file/{item_id}` | [`Backend/api/endpoints/competitor_api.py:1608`](Backend/api/endpoints/competitor_api.py#L1608) | `required` |
| `PATCH` | `/swipe-file/{item_id}` | [`Backend/api/endpoints/competitor_api.py:1586`](Backend/api/endpoints/competitor_api.py#L1586) | `required` |
| `POST` | `/sync` | [`Backend/api/endpoints/accounts.py:313`](Backend/api/endpoints/accounts.py#L313) | `required` |
| `POST` | `/sync-metrics` | [`Backend/api/endpoints/experiments.py:797`](Backend/api/endpoints/experiments.py#L797) | `required` |
| `POST` | `/sync-now` | [`Backend/api/metrics_scheduler_api.py:126`](Backend/api/metrics_scheduler_api.py#L126) | `required` |
| `POST` | `/sync-trending` | [`Backend/api/endpoints/content_ideas_api.py:133`](Backend/api/endpoints/content_ideas_api.py#L133) | `required` |
| `POST` | `/sync/all` | [`Backend/api/endpoints/inbox.py:482`](Backend/api/endpoints/inbox.py#L482) | `required` |
| `POST` | `/sync/{platform}` | [`Backend/api/endpoints/inbox.py:452`](Backend/api/endpoints/inbox.py#L452) | `required` |
| `POST` | `/sync/{post_id}` | [`Backend/api/content_growth.py:569`](Backend/api/content_growth.py#L569) | `required` |
| `GET` | `/system/status` | [`Backend/api/endpoints/experiments.py:2309`](Backend/api/endpoints/experiments.py#L2309) | `read` |
| `GET` | `/tables` | [`Backend/api/endpoints/db_health.py:139`](Backend/api/endpoints/db_health.py#L139) | `read` |
| `POST` | `/tag-posts` | [`Backend/api/content_intelligence.py:68`](Backend/api/content_intelligence.py#L68) | `required` |
| `GET` | `/tags` | [`Backend/api/endpoints/sfx_library.py:471`](Backend/api/endpoints/sfx_library.py#L471) | `read` |
| `GET` | `/tags` | [`Backend/api/endpoints/voice_selection.py:235`](Backend/api/endpoints/voice_selection.py#L235) | `read` |
| `GET` | `/targets` | [`Backend/api/comment_automation.py:363`](Backend/api/comment_automation.py#L363) | `read` |
| `PUT` | `/targets` | [`Backend/api/comment_automation.py:356`](Backend/api/comment_automation.py#L356) | `required` |
| `GET` | `/targets/{content_id}/top-comments` | [`Backend/api/comment_automation.py:389`](Backend/api/comment_automation.py#L389) | `read` |
| `GET` | `/template/{template_id}/forks` | [`Backend/api/endpoints/template_auto_forker.py:141`](Backend/api/endpoints/template_auto_forker.py#L141) | `read` |
| `GET` | `/templates` | [`Backend/api/endpoints/ai_video_generation.py:650`](Backend/api/endpoints/ai_video_generation.py#L650) | `read` |
| `GET` | `/templates` | [`Backend/api/endpoints/community_inbox.py:480`](Backend/api/endpoints/community_inbox.py#L480) | `read` |
| `GET` | `/templates` | [`Backend/api/endpoints/competitor_audit.py:219`](Backend/api/endpoints/competitor_audit.py#L219) | `read` |
| `GET` | `/templates` | [`Backend/api/endpoints/enhanced_analysis.py:425`](Backend/api/endpoints/enhanced_analysis.py#L425) | `read` |
| `GET` | `/templates` | [`Backend/api/endpoints/media_creation.py:97`](Backend/api/endpoints/media_creation.py#L97) | `read` |
| `GET` | `/templates` | [`Backend/routers/visual_campaign.py:135`](Backend/routers/visual_campaign.py#L135) | `read` |
| `GET` | `/templates` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:493`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L493) | `read` |
| `POST` | `/templates` | [`Backend/api/endpoints/community_inbox.py:514`](Backend/api/endpoints/community_inbox.py#L514) | `required` |
| `POST` | `/templates/auto-populate` | [`Backend/api/endpoints/enhanced_analysis.py:514`](Backend/api/endpoints/enhanced_analysis.py#L514) | `required` |
| `POST` | `/templates/create-from-video` | [`Backend/api/endpoints/enhanced_analysis.py:545`](Backend/api/endpoints/enhanced_analysis.py#L545) | `required` |
| `POST` | `/templates/match` | [`Backend/api/endpoints/enhanced_analysis.py:474`](Backend/api/endpoints/enhanced_analysis.py#L474) | `required` |
| `GET` | `/templates/winners` | [`Backend/api/endpoints/adaptive_scheduler.py:495`](Backend/api/endpoints/adaptive_scheduler.py#L495) | `read` |
| `GET` | `/templates/{template_id}` | [`Backend/api/endpoints/competitor_audit.py:274`](Backend/api/endpoints/competitor_audit.py#L274) | `read` |
| `GET` | `/templates/{template_id}` | [`Backend/api/endpoints/enhanced_analysis.py:451`](Backend/api/endpoints/enhanced_analysis.py#L451) | `read` |
| `POST` | `/templates/{template_id}/create-campaign` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:511`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L511) | `required` |
| `POST` | `/test` | [`Backend/api/endpoints/sora.py:224`](Backend/api/endpoints/sora.py#L224) | `required` |
| `POST` | `/test` | [`Backend/api/endpoints/video_render.py:265`](Backend/api/endpoints/video_render.py#L265) | `required` |
| `POST` | `/test-ai-env` | [`Backend/api/endpoints/venv_status.py:97`](Backend/api/endpoints/venv_status.py#L97) | `required` |
| `POST` | `/test-brief` | [`Backend/api/endpoints/briefs.py:128`](Backend/api/endpoints/briefs.py#L128) | `required` |
| `POST` | `/test-connection` | [`Backend/api/endpoints/blotato_test.py:50`](Backend/api/endpoints/blotato_test.py#L50) | `required` |
| `POST` | `/test-connection` | [`Backend/api/endpoints/db_health.py:199`](Backend/api/endpoints/db_health.py#L199) | `required` |
| `POST` | `/test-error` | [`Backend/api/endpoints/backend_health.py:55`](Backend/api/endpoints/backend_health.py#L55) | `required` |
| `POST` | `/text-suggestions` | [`Backend/api/endpoints/broll_candidates.py:292`](Backend/api/endpoints/broll_candidates.py#L292) | `required` |
| `GET` | `/theme-analytics` | [`Backend/api/endpoints/competitor_api.py:1219`](Backend/api/endpoints/competitor_api.py#L1219) | `read` |
| `GET` | `/themes` | [`Backend/api/endpoints/sora_daily.py:357`](Backend/api/endpoints/sora_daily.py#L357) | `read` |
| `POST` | `/thread` | [`Backend/api/endpoints/twitter_posting.py:134`](Backend/api/endpoints/twitter_posting.py#L134) | `required` |
| `GET` | `/threads` | [`Backend/api/endpoints/rapidapi_comments.py:113`](Backend/api/endpoints/rapidapi_comments.py#L113) | `read` |
| `GET` | `/threads/all` | [`Backend/api/endpoints/rapidapi_comments.py:132`](Backend/api/endpoints/rapidapi_comments.py#L132) | `read` |
| `GET` | `/thumbnail-file` | [`Backend/api/media_processing.py:648`](Backend/api/media_processing.py#L648) | `read` |
| `GET` | `/thumbnail/{media_id}` | [`Backend/api/endpoints/media_provider.py:51`](Backend/api/endpoints/media_provider.py#L51) | `read` |
| `GET` | `/thumbnail/{media_id}` | [`Backend/api/media_processing.py:605`](Backend/api/media_processing.py#L605) | `read` |
| `GET` | `/thumbnails` | [`Backend/api/endpoints/storage.py:96`](Backend/api/endpoints/storage.py#L96) | `read` |
| `POST` | `/thumbnails` | [`Backend/api/endpoints/tiktok_repurpose.py:357`](Backend/api/endpoints/tiktok_repurpose.py#L357) | `required` |
| `POST` | `/thumbnails/associate` | [`Backend/api/endpoints/tiktok_repurpose.py:393`](Backend/api/endpoints/tiktok_repurpose.py#L393) | `required` |
| `POST` | `/thumbnails/generate` | [`Backend/api/media_processing.py:760`](Backend/api/media_processing.py#L760) | `required` |
| `POST` | `/thumbnails/select` | [`Backend/api/endpoints/adaptive_scheduler.py:580`](Backend/api/endpoints/adaptive_scheduler.py#L580) | `required` |
| `GET` | `/thumbnails/stats` | [`Backend/api/media_processing.py:883`](Backend/api/media_processing.py#L883) | `read` |
| `GET` | `/thumbnails/status/{job_id}` | [`Backend/api/media_processing.py:864`](Backend/api/media_processing.py#L864) | `read` |
| `DELETE` | `/thumbnails/{video_id}` | [`Backend/api/endpoints/storage.py:301`](Backend/api/endpoints/storage.py#L301) | `required` |
| `POST` | `/tick` | [`Backend/api/endpoints/scheduler.py:26`](Backend/api/endpoints/scheduler.py#L26) | `required` |
| `GET` | `/tiktok` | [`Backend/api/endpoints/rapidapi_comments.py:25`](Backend/api/endpoints/rapidapi_comments.py#L25) | `read` |
| `GET` | `/tiktok/all` | [`Backend/api/endpoints/rapidapi_comments.py:49`](Backend/api/endpoints/rapidapi_comments.py#L49) | `read` |
| `POST` | `/tiktok/repurpose` | [`Backend/api/endpoints/adaptive_scheduler.py:318`](Backend/api/endpoints/adaptive_scheduler.py#L318) | `required` |
| `GET` | `/timeline` | [`Backend/api/endpoints/agent_panel.py:37`](Backend/api/endpoints/agent_panel.py#L37) | `read` |
| `GET` | `/timeouts` | [`Backend/api/endpoints/sora_automation.py:87`](Backend/api/endpoints/sora_automation.py#L87) | `read` |
| `POST` | `/to-format-brief` | [`Backend/api/endpoints/trends_agent.py:427`](Backend/api/endpoints/trends_agent.py#L427) | `required` |
| `GET` | `/top` | [`Backend/api/endpoints/analyzed_content.py:140`](Backend/api/endpoints/analyzed_content.py#L140) | `read` |
| `GET` | `/top` | [`Backend/api/endpoints/template_leaderboard.py:109`](Backend/api/endpoints/template_leaderboard.py#L109) | `read` |
| `GET` | `/top` | [`Backend/api/endpoints/trend_flash.py:99`](Backend/api/endpoints/trend_flash.py#L99) | `read` |
| `GET` | `/top-performers` | [`Backend/api/endpoints/analytics_feedback.py:91`](Backend/api/endpoints/analytics_feedback.py#L91) | `read` |
| `GET` | `/top-posts` | [`Backend/api/cross_platform_dashboard.py:24`](Backend/api/cross_platform_dashboard.py#L24) | `read` |
| `GET` | `/topics` | [`Backend/api/endpoints/agent_events.py:213`](Backend/api/endpoints/agent_events.py#L213) | `read` |
| `GET` | `/topics` | [`Backend/api/endpoints/automation.py:337`](Backend/api/endpoints/automation.py#L337) | `read` |
| `GET` | `/topics` | [`Backend/api/endpoints/events.py:15`](Backend/api/endpoints/events.py#L15) | `read` |
| `GET` | `/topics` | [`Backend/api/endpoints/pubsub_inspector.py:20`](Backend/api/endpoints/pubsub_inspector.py#L20) | `read` |
| `GET` | `/topics` | [`Backend/api/endpoints/trends.py:222`](Backend/api/endpoints/trends.py#L222) | `read` |
| `GET` | `/topics` | [`Backend/api/endpoints/video_toolkit.py:223`](Backend/api/endpoints/video_toolkit.py#L223) | `read` |
| `POST` | `/topics` | [`Backend/api/endpoints/trends.py:246`](Backend/api/endpoints/trends.py#L246) | `required` |
| `GET` | `/topics/{topic:path}/events` | [`Backend/api/endpoints/pubsub_inspector.py:49`](Backend/api/endpoints/pubsub_inspector.py#L49) | `read` |
| `GET` | `/topics/{topic:path}/stats` | [`Backend/api/endpoints/pubsub_inspector.py:70`](Backend/api/endpoints/pubsub_inspector.py#L70) | `read` |
| `GET` | `/topics/{topic}/events` | [`Backend/api/endpoints/automation.py:353`](Backend/api/endpoints/automation.py#L353) | `read` |
| `POST` | `/touchpoints/check` | [`Backend/api/endpoints/adaptive_scheduler.py:874`](Backend/api/endpoints/adaptive_scheduler.py#L874) | `required` |
| `GET` | `/track/{music_id}` | [`Backend/api/endpoints/music_matching.py:427`](Backend/api/endpoints/music_matching.py#L427) | `read` |
| `GET` | `/tracking` | [`Backend/api/comment_automation.py:813`](Backend/api/comment_automation.py#L813) | `read` |
| `GET` | `/tracking/open/{message_id}` | [`Backend/api/endpoints/email.py:176`](Backend/api/endpoints/email.py#L176) | `read` |
| `POST` | `/tracking/{comment_id}/update` | [`Backend/api/comment_automation.py:843`](Backend/api/comment_automation.py#L843) | `required` |
| `GET` | `/traffic/platform-performance` | [`Backend/api/endpoints/orchestrator.py:526`](Backend/api/endpoints/orchestrator.py#L526) | `read` |
| `GET` | `/traffic/top-campaigns` | [`Backend/api/endpoints/orchestrator.py:565`](Backend/api/endpoints/orchestrator.py#L565) | `read` |
| `POST` | `/transcribe` | [`Backend/api/endpoints/venv_status.py:65`](Backend/api/endpoints/venv_status.py#L65) | `required` |
| `POST` | `/transcribe` | [`Backend/api/subtitles.py:56`](Backend/api/subtitles.py#L56) | `required` |
| `POST` | `/transcribe-only` | [`Backend/api/subtitles.py:94`](Backend/api/subtitles.py#L94) | `required` |
| `POST` | `/transcribe/{video_id}` | [`Backend/api/endpoints/analysis.py:379`](Backend/api/endpoints/analysis.py#L379) | `required` |
| `GET` | `/transcript/{video_id}` | [`Backend/api/endpoints/analysis.py:474`](Backend/api/endpoints/analysis.py#L474) | `read` |
| `POST` | `/transfer-files` | [`Backend/api/endpoints/ios_import_api.py:633`](Backend/api/endpoints/ios_import_api.py#L633) | `required` |
| `POST` | `/transfer-files-direct` | [`Backend/api/endpoints/ios_import_api.py:562`](Backend/api/endpoints/ios_import_api.py#L562) | `required` |
| `GET` | `/trend-breakdown` | [`Backend/api/endpoints/creator_intelligence.py:23`](Backend/api/endpoints/creator_intelligence.py#L23) | `read` |
| `POST` | `/trend-intel/ingest` | [`Backend/api/endpoints/adaptive_scheduler.py:673`](Backend/api/endpoints/adaptive_scheduler.py#L673) | `required` |
| `GET` | `/trend-opportunities` | [`Backend/api/endpoints/narrative_builder.py:1394`](Backend/api/endpoints/narrative_builder.py#L1394) | `read` |
| `GET` | `/trend-prompts` | [`Backend/api/endpoints/sora_daily.py:369`](Backend/api/endpoints/sora_daily.py#L369) | `read` |
| `POST` | `/trend-prompts/generate-custom` | [`Backend/api/endpoints/sora_daily.py:518`](Backend/api/endpoints/sora_daily.py#L518) | `required` |
| `POST` | `/trend-prompts/random` | [`Backend/api/endpoints/sora_daily.py:477`](Backend/api/endpoints/sora_daily.py#L477) | `required` |
| `GET` | `/trend-prompts/series` | [`Backend/api/endpoints/sora_daily.py:427`](Backend/api/endpoints/sora_daily.py#L427) | `read` |
| `GET` | `/trend-prompts/trends` | [`Backend/api/endpoints/sora_daily.py:407`](Backend/api/endpoints/sora_daily.py#L407) | `read` |
| `GET` | `/trend-prompts/{prompt_id}` | [`Backend/api/endpoints/sora_daily.py:456`](Backend/api/endpoints/sora_daily.py#L456) | `read` |
| `GET` | `/trending` | [`Backend/api/endpoints/media_assets.py:204`](Backend/api/endpoints/media_assets.py#L204) | `read` |
| `GET` | `/trending-audio` | [`Backend/api/endpoints/competitor_api.py:1621`](Backend/api/endpoints/competitor_api.py#L1621) | `read` |
| `GET` | `/trending-keywords` | [`Backend/api/endpoints/trends_api.py:762`](Backend/api/endpoints/trends_api.py#L762) | `read` |
| `GET` | `/trending-keywords/ctas` | [`Backend/api/endpoints/trends_api.py:801`](Backend/api/endpoints/trends_api.py#L801) | `read` |
| `POST` | `/trending-keywords/extract` | [`Backend/api/endpoints/trends_api.py:817`](Backend/api/endpoints/trends_api.py#L817) | `required` |
| `GET` | `/trending-keywords/hooks` | [`Backend/api/endpoints/trends_api.py:785`](Backend/api/endpoints/trends_api.py#L785) | `read` |
| `GET` | `/trending-phrases` | [`Backend/api/endpoints/broll_producer.py:237`](Backend/api/endpoints/broll_producer.py#L237) | `read` |
| `GET` | `/trending/competitor/{username}` | [`Backend/api/endpoints/trending.py:96`](Backend/api/endpoints/trending.py#L96) | `read` |
| `GET` | `/trending/hashtag/{hashtag}` | [`Backend/api/endpoints/trending.py:134`](Backend/api/endpoints/trending.py#L134) | `read` |
| `GET` | `/trending/ideas` | [`Backend/api/endpoints/trending.py:172`](Backend/api/endpoints/trending.py#L172) | `read` |
| `GET` | `/trending/list` | [`Backend/api/endpoints/music_library.py:333`](Backend/api/endpoints/music_library.py#L333) | `read` |
| `GET` | `/trending/topics` | [`Backend/api/endpoints/trending.py:59`](Backend/api/endpoints/trending.py#L59) | `read` |
| `GET` | `/trending/video/{video_id}` | [`Backend/api/endpoints/trending.py:202`](Backend/api/endpoints/trending.py#L202) | `read` |
| `GET` | `/trends` | [`Backend/api/endpoints/adaptive_scheduler.py:275`](Backend/api/endpoints/adaptive_scheduler.py#L275) | `read` |
| `GET` | `/trends` | [`Backend/api/endpoints/analytics.py:86`](Backend/api/endpoints/analytics.py#L86) | `read` |
| `GET` | `/trends` | [`Backend/api/endpoints/content_runway.py:281`](Backend/api/endpoints/content_runway.py#L281) | `read` |
| `GET` | `/trends` | [`Backend/api/endpoints/social_analytics.py:550`](Backend/api/endpoints/social_analytics.py#L550) | `read` |
| `GET` | `/trends` | [`Backend/api/endpoints/sora_daily.py:220`](Backend/api/endpoints/sora_daily.py#L220) | `read` |
| `GET` | `/trends` | [`Backend/api/endpoints/trend_intelligence.py:62`](Backend/api/endpoints/trend_intelligence.py#L62) | `read` |
| `GET` | `/trends` | [`Backend/api/endpoints/trends_agent.py:68`](Backend/api/endpoints/trends_agent.py#L68) | `read` |
| `GET` | `/trends-context` | [`Backend/api/endpoints/broll_candidates.py:441`](Backend/api/endpoints/broll_candidates.py#L441) | `read` |
| `GET` | `/trends/briefs` | [`Backend/api/endpoints/trend_opportunities.py:537`](Backend/api/endpoints/trend_opportunities.py#L537) | `read` |
| `POST` | `/trends/briefs` | [`Backend/api/endpoints/trend_opportunities.py:581`](Backend/api/endpoints/trend_opportunities.py#L581) | `required` |
| `POST` | `/trends/collect` | [`Backend/api/endpoints/sora_daily.py:244`](Backend/api/endpoints/sora_daily.py#L244) | `required` |
| `POST` | `/trends/fetch` | [`Backend/api/endpoints/adaptive_scheduler.py:290`](Backend/api/endpoints/adaptive_scheduler.py#L290) | `required` |
| `GET` | `/trends/items` | [`Backend/api/endpoints/trend_opportunities.py:215`](Backend/api/endpoints/trend_opportunities.py#L215) | `read` |
| `POST` | `/trends/items` | [`Backend/api/endpoints/trend_opportunities.py:288`](Backend/api/endpoints/trend_opportunities.py#L288) | `required` |
| `GET` | `/trends/opportunities` | [`Backend/api/endpoints/trend_opportunities.py:345`](Backend/api/endpoints/trend_opportunities.py#L345) | `read` |
| `POST` | `/trends/opportunities` | [`Backend/api/endpoints/trend_opportunities.py:419`](Backend/api/endpoints/trend_opportunities.py#L419) | `required` |
| `PATCH` | `/trends/opportunities/{opp_id}/action` | [`Backend/api/endpoints/trend_opportunities.py:486`](Backend/api/endpoints/trend_opportunities.py#L486) | `required` |
| `PATCH` | `/trends/opportunities/{opp_id}/dismiss` | [`Backend/api/endpoints/trend_opportunities.py:510`](Backend/api/endpoints/trend_opportunities.py#L510) | `required` |
| `POST` | `/trends/score` | [`Backend/api/endpoints/trend_opportunities.py:630`](Backend/api/endpoints/trend_opportunities.py#L630) | `required` |
| `POST` | `/trends/seed-demo-data` | [`Backend/api/endpoints/trend_opportunities.py:671`](Backend/api/endpoints/trend_opportunities.py#L671) | `required` |
| `GET` | `/trends/velocity` | [`Backend/api/endpoints/adaptive_scheduler.py:858`](Backend/api/endpoints/adaptive_scheduler.py#L858) | `read` |
| `GET` | `/trends/{cluster_id}` | [`Backend/api/endpoints/trend_intelligence.py:84`](Backend/api/endpoints/trend_intelligence.py#L84) | `read` |
| `GET` | `/trends/{cluster_id}/posts` | [`Backend/api/endpoints/trend_intelligence.py:97`](Backend/api/endpoints/trend_intelligence.py#L97) | `read` |
| `GET` | `/trends/{trend_id}` | [`Backend/api/endpoints/trends_agent.py:123`](Backend/api/endpoints/trends_agent.py#L123) | `read` |
| `POST` | `/trigger` | [`Backend/api/cascade_publisher.py:127`](Backend/api/cascade_publisher.py#L127) | `required` |
| `POST` | `/trigger/{schedule_id}` | [`Backend/api/endpoints/scheduler.py:185`](Backend/api/endpoints/scheduler.py#L185) | `required` |
| `POST` | `/tweet` | [`Backend/api/endpoints/safari_automation.py:175`](Backend/api/endpoints/safari_automation.py#L175) | `required` |
| `GET` | `/twitter` | [`Backend/api/endpoints/daily_automation.py:55`](Backend/api/endpoints/daily_automation.py#L55) | `read` |
| `POST` | `/twitter/campaigns` | [`Backend/api/endpoints/adaptive_scheduler.py:882`](Backend/api/endpoints/adaptive_scheduler.py#L882) | `required` |
| `GET` | `/types` | [`Backend/api/endpoints/visuals.py:107`](Backend/api/endpoints/visuals.py#L107) | `read` |
| `GET` | `/unanalyzed-videos` | [`Backend/api/endpoints/batch_analysis.py:133`](Backend/api/endpoints/batch_analysis.py#L133) | `read` |
| `GET` | `/unified` | [`Backend/api/endpoints/multi_platform_analytics.py:82`](Backend/api/endpoints/multi_platform_analytics.py#L82) | `read` |
| `POST` | `/unified/generate-week` | [`Backend/api/content_pipeline.py:733`](Backend/api/content_pipeline.py#L733) | `required` |
| `POST` | `/unified/quick-schedule` | [`Backend/api/content_pipeline.py:699`](Backend/api/content_pipeline.py#L699) | `required` |
| `GET` | `/unified/stats` | [`Backend/api/content_pipeline.py:787`](Backend/api/content_pipeline.py#L787) | `read` |
| `GET` | `/unsplash/collections` | [`Backend/api/endpoints/media_assets.py:163`](Backend/api/endpoints/media_assets.py#L163) | `read` |
| `GET` | `/unsplash/search` | [`Backend/api/endpoints/media_assets.py:151`](Backend/api/endpoints/media_assets.py#L151) | `read` |
| `POST` | `/unsplash/track-download/{asset_id}` | [`Backend/api/endpoints/media_assets.py:170`](Backend/api/endpoints/media_assets.py#L170) | `required` |
| `POST` | `/update-on-new-content` | [`Backend/api/endpoints/inventory_scheduler.py:159`](Backend/api/endpoints/inventory_scheduler.py#L159) | `required` |
| `POST` | `/upload` | [`Backend/api/endpoints/scheduling.py:100`](Backend/api/endpoints/scheduling.py#L100) | `required` |
| `POST` | `/upload` | [`Backend/api/endpoints/videos.py:372`](Backend/api/endpoints/videos.py#L372) | `required` |
| `POST` | `/upload` | [`Backend/api/media_processing.py:226`](Backend/api/media_processing.py#L226) | `required` |
| `POST` | `/upload/init` | [`Backend/api/media_processing.py:189`](Backend/api/media_processing.py#L189) | `required` |
| `GET` | `/url` | [`Backend/api/endpoints/twitter_posting.py:462`](Backend/api/endpoints/twitter_posting.py#L462) | `read` |
| `GET` | `/usage` | [`Backend/api/endpoints/api_usage.py:18`](Backend/api/endpoints/api_usage.py#L18) | `read` |
| `GET` | `/usage` | [`Backend/api/endpoints/sora_automation.py:43`](Backend/api/endpoints/sora_automation.py#L43) | `read` |
| `GET` | `/usage` | [`Backend/api/endpoints/voice_cloning.py:402`](Backend/api/endpoints/voice_cloning.py#L402) | `read` |
| `GET` | `/usage` | [`Backend/api/rapidapi_metrics.py:495`](Backend/api/rapidapi_metrics.py#L495) | `read` |
| `GET` | `/usage/cached` | [`Backend/api/endpoints/sora_automation.py:73`](Backend/api/endpoints/sora_automation.py#L73) | `read` |
| `POST` | `/usage/check` | [`Backend/api/endpoints/sora_automation.py:94`](Backend/api/endpoints/sora_automation.py#L94) | `required` |
| `POST` | `/usage/reset` | [`Backend/api/rapidapi_metrics.py:529`](Backend/api/rapidapi_metrics.py#L529) | `required` |
| `GET` | `/usage/{api_name}` | [`Backend/api/endpoints/api_usage.py:87`](Backend/api/endpoints/api_usage.py#L87) | `read` |
| `GET` | `/v1/health` | [`Backend/control_plane/main.py:91`](Backend/control_plane/main.py#L91) | `read` |
| `GET` | `/v1/ready` | [`Backend/control_plane/main.py:102`](Backend/control_plane/main.py#L102) | `read` |
| `POST` | `/validate` | [`Backend/api/endpoints/sfx_library.py:225`](Backend/api/endpoints/sfx_library.py#L225) | `required` |
| `POST` | `/variants` | [`Backend/api/endpoints/content.py:96`](Backend/api/endpoints/content.py#L96) | `required` |
| `POST` | `/variants/{variant_id}/publish` | [`Backend/api/endpoints/content.py:142`](Backend/api/endpoints/content.py#L142) | `required` |
| `GET` | `/velocity` | [`Backend/api/endpoints/trends_api.py:654`](Backend/api/endpoints/trends_api.py#L654) | `read` |
| `POST` | `/velocity/calculate` | [`Backend/api/endpoints/trends_api.py:516`](Backend/api/endpoints/trends_api.py#L516) | `required` |
| `POST` | `/verify-publish` | [`Backend/api/endpoints/schedule.py:1050`](Backend/api/endpoints/schedule.py#L1050) | `required` |
| `GET` | `/video-file` | [`Backend/api/media_processing.py:692`](Backend/api/media_processing.py#L692) | `read` |
| `POST` | `/video-ready` | [`Backend/services/video_ready_pipeline.py:931`](Backend/services/video_ready_pipeline.py#L931) | `required` |
| `GET` | `/video-stats` | [`Backend/api/endpoints/batch_analysis.py:83`](Backend/api/endpoints/batch_analysis.py#L83) | `read` |
| `GET` | `/video-stream/{media_id}` | [`Backend/api/media_processing_db.py:2857`](Backend/api/media_processing_db.py#L2857) | `read` |
| `GET` | `/video-styles` | [`Backend/api/blotato_router.py:1183`](Backend/api/blotato_router.py#L1183) | `read` |
| `GET` | `/video-templates` | [`Backend/api/blotato_router.py:1194`](Backend/api/blotato_router.py#L1194) | `read` |
| `GET` | `/video/comments` | [`Backend/api/endpoints/tiktok_analytics.py:83`](Backend/api/endpoints/tiktok_analytics.py#L83) | `read` |
| `POST` | `/video/create` | [`Backend/api/explainer_video.py:243`](Backend/api/explainer_video.py#L243) | `required` |
| `GET` | `/video/jobs` | [`Backend/api/explainer_video.py:295`](Backend/api/explainer_video.py#L295) | `read` |
| `GET` | `/video/jobs/{job_id}` | [`Backend/api/explainer_video.py:316`](Backend/api/explainer_video.py#L316) | `read` |
| `POST` | `/video/process` | [`Backend/api/endpoints/safari_automation.py:215`](Backend/api/endpoints/safari_automation.py#L215) | `required` |
| `GET` | `/video/{media_id}` | [`Backend/api/endpoints/media_provider.py:83`](Backend/api/endpoints/media_provider.py#L83) | `read` |
| `GET` | `/video/{media_id}` | [`Backend/api/media_processing_db.py:2751`](Backend/api/media_processing_db.py#L2751) | `read` |
| `GET` | `/video/{video_id}` | [`Backend/api/endpoints/clip_management.py:131`](Backend/api/endpoints/clip_management.py#L131) | `read` |
| `GET` | `/video/{video_id}` | [`Backend/api/endpoints/review.py:225`](Backend/api/endpoints/review.py#L225) | `read` |
| `GET` | `/video/{video_id}` | [`Backend/api/endpoints/youtube_analytics.py:47`](Backend/api/endpoints/youtube_analytics.py#L47) | `read` |
| `GET` | `/videos` | [`Backend/api/endpoints/enhanced_analysis.py:22`](Backend/api/endpoints/enhanced_analysis.py#L22) | `read` |
| `GET` | `/videos` | [`Backend/api/endpoints/storage.py:60`](Backend/api/endpoints/storage.py#L60) | `read` |
| `GET` | `/videos` | [`Backend/api/endpoints/viral_analysis.py:23`](Backend/api/endpoints/viral_analysis.py#L23) | `read` |
| `GET` | `/videos` | [`Backend/api/endpoints/youtube_analytics.py:73`](Backend/api/endpoints/youtube_analytics.py#L73) | `read` |
| `GET` | `/videos-needing-reanalysis` | [`Backend/api/endpoints/analysis_health.py:333`](Backend/api/endpoints/analysis_health.py#L333) | `read` |
| `POST` | `/videos/create` | [`Backend/api/blotato_router.py:845`](Backend/api/blotato_router.py#L845) | `required` |
| `POST` | `/videos/narrated` | [`Backend/api/blotato_router.py:973`](Backend/api/blotato_router.py#L973) | `required` |
| `GET` | `/videos/pool` | [`Backend/api/endpoints/adaptive_scheduler.py:210`](Backend/api/endpoints/adaptive_scheduler.py#L210) | `read` |
| `POST` | `/videos/pov` | [`Backend/api/blotato_router.py:929`](Backend/api/blotato_router.py#L929) | `required` |
| `POST` | `/videos/slideshow` | [`Backend/api/blotato_router.py:949`](Backend/api/blotato_router.py#L949) | `required` |
| `DELETE` | `/videos/{video_id}` | [`Backend/api/blotato_router.py:1013`](Backend/api/blotato_router.py#L1013) | `required` |
| `DELETE` | `/videos/{video_id}` | [`Backend/api/endpoints/storage.py:284`](Backend/api/endpoints/storage.py#L284) | `required` |
| `GET` | `/videos/{video_id}` | [`Backend/api/blotato_router.py:991`](Backend/api/blotato_router.py#L991) | `read` |
| `POST` | `/videos/{video_id}/analyze` | [`Backend/api/endpoints/enhanced_analysis.py:94`](Backend/api/endpoints/enhanced_analysis.py#L94) | `required` |
| `POST` | `/videos/{video_id}/analyze` | [`Backend/api/endpoints/viral_analysis.py:117`](Backend/api/endpoints/viral_analysis.py#L117) | `required` |
| `POST` | `/videos/{video_id}/analyze-sync` | [`Backend/api/endpoints/viral_analysis.py:175`](Backend/api/endpoints/viral_analysis.py#L175) | `required` |
| `GET` | `/videos/{video_id}/export` | [`Backend/api/endpoints/enhanced_analysis.py:121`](Backend/api/endpoints/enhanced_analysis.py#L121) | `read` |
| `GET` | `/videos/{video_id}/frames` | [`Backend/api/endpoints/viral_analysis.py:290`](Backend/api/endpoints/viral_analysis.py#L290) | `read` |
| `GET` | `/videos/{video_id}/metrics` | [`Backend/api/endpoints/viral_analysis.py:445`](Backend/api/endpoints/viral_analysis.py#L445) | `read` |
| `GET` | `/videos/{video_id}/timeline` | [`Backend/api/endpoints/viral_analysis.py:368`](Backend/api/endpoints/viral_analysis.py#L368) | `read` |
| `GET` | `/videos/{video_id}/validate` | [`Backend/api/endpoints/enhanced_analysis.py:110`](Backend/api/endpoints/enhanced_analysis.py#L110) | `read` |
| `GET` | `/videos/{video_id}/wait` | [`Backend/api/blotato_router.py:1025`](Backend/api/blotato_router.py#L1025) | `read` |
| `GET` | `/videos/{video_id}/words` | [`Backend/api/endpoints/viral_analysis.py:216`](Backend/api/endpoints/viral_analysis.py#L216) | `read` |
| `GET` | `/view-modes` | [`Backend/api/endpoints/calendar.py:491`](Backend/api/endpoints/calendar.py#L491) | `read` |
| `POST` | `/vision/analyze-structured` | [`Backend/api/endpoints/enhanced_analysis.py:292`](Backend/api/endpoints/enhanced_analysis.py#L292) | `required` |
| `POST` | `/vision/detect-motion` | [`Backend/api/endpoints/enhanced_analysis.py:382`](Backend/api/endpoints/enhanced_analysis.py#L382) | `required` |
| `POST` | `/vision/detect-scenes` | [`Backend/api/endpoints/enhanced_analysis.py:339`](Backend/api/endpoints/enhanced_analysis.py#L339) | `required` |
| `GET` | `/voices` | [`Backend/api/blotato_router.py:1059`](Backend/api/blotato_router.py#L1059) | `read` |
| `POST` | `/wake` | [`Backend/api/endpoints/sleep.py:98`](Backend/api/endpoints/sleep.py#L98) | `required` |
| `GET` | `/wake-events` | [`Backend/api/endpoints/sleep.py:245`](Backend/api/endpoints/sleep.py#L245) | `read` |
| `DELETE` | `/wake/{trigger_id}` | [`Backend/api/endpoints/sleep.py:185`](Backend/api/endpoints/sleep.py#L185) | `required` |
| `POST` | `/watermark/remove` | [`Backend/api/endpoints/sora_daily.py:268`](Backend/api/endpoints/sora_daily.py#L268) | `required` |
| `GET` | `/watermark/status` | [`Backend/api/endpoints/sora_daily.py:284`](Backend/api/endpoints/sora_daily.py#L284) | `read` |
| `GET` | `/webhooks` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:700`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L700) | `read` |
| `POST` | `/webhooks` | [`Backend/api/endpoints/trends_agent.py:375`](Backend/api/endpoints/trends_agent.py#L375) | `required` |
| `POST` | `/webhooks` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:686`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L686) | `required` |
| `POST` | `/webhooks/receive` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:728`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L728) | `required` |
| `DELETE` | `/webhooks/{webhook_id}` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:718`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L718) | `required` |
| `PATCH` | `/webhooks/{webhook_id}` | [`Backend/services/creative_testing_pipeline/routers/actp_router.py:709`](Backend/services/creative_testing_pipeline/routers/actp_router.py#L709) | `required` |
| `GET` | `/week/{week_start}` | [`Backend/api/endpoints/strategy_report_api.py:93`](Backend/api/endpoints/strategy_report_api.py#L93) | `read` |
| `POST` | `/weekly-planner/generate` | [`Backend/api/endpoints/autonomy.py:125`](Backend/api/endpoints/autonomy.py#L125) | `required` |
| `GET` | `/weekly-planner/plans` | [`Backend/api/endpoints/autonomy.py:177`](Backend/api/endpoints/autonomy.py#L177) | `read` |
| `GET` | `/weekly-planner/plans/{plan_id}` | [`Backend/api/endpoints/autonomy.py:230`](Backend/api/endpoints/autonomy.py#L230) | `read` |
| `GET` | `/weekly-planner/status` | [`Backend/api/endpoints/autonomy.py:107`](Backend/api/endpoints/autonomy.py#L107) | `read` |
| `GET` | `/weekly-report` | [`Backend/api/endpoints/analytics_feedback.py:13`](Backend/api/endpoints/analytics_feedback.py#L13) | `read` |
| `GET` | `/weekly-schedule` | [`Backend/api/smart_posting_times.py:79`](Backend/api/smart_posting_times.py#L79) | `read` |
| `GET` | `/weekly-schedules` | [`Backend/api/endpoints/narrative_scheduler.py:81`](Backend/api/endpoints/narrative_scheduler.py#L81) | `read` |
| `GET` | `/widgets` | [`Backend/api/endpoints/dashboard.py:11`](Backend/api/endpoints/dashboard.py#L11) | `read` |
| `GET` | `/winners` | [`Backend/api/endpoints/experiments.py:1824`](Backend/api/endpoints/experiments.py#L1824) | `read` |
| `GET` | `/winners/promotion-candidates` | [`Backend/api/endpoints/experiments.py:1842`](Backend/api/endpoints/experiments.py#L1842) | `read` |
| `POST` | `/winners/{winner_id}/promote` | [`Backend/api/endpoints/experiments.py:1860`](Backend/api/endpoints/experiments.py#L1860) | `required` |
| `POST` | `/worker/process` | [`Backend/api/endpoints/scheduler.py:102`](Backend/api/endpoints/scheduler.py#L102) | `required` |
| `GET` | `/workflow/{correlation_id}` | [`Backend/api/endpoints/event_history.py:199`](Backend/api/endpoints/event_history.py#L199) | `read` |
| `GET` | `/ws/stats` | [`Backend/api/endpoints/websocket.py:294`](Backend/api/endpoints/websocket.py#L294) | `read` |
| `GET` | `/ws/topics` | [`Backend/api/endpoints/websocket.py:300`](Backend/api/endpoints/websocket.py#L300) | `read` |
| `DELETE` | `/{audio_id}` | [`Backend/api/endpoints/audio_api.py:188`](Backend/api/endpoints/audio_api.py#L188) | `required` |
| `DELETE` | `/{automation_id}` | [`Backend/api/endpoints/automations.py:222`](Backend/api/endpoints/automations.py#L222) | `required` |
| `GET` | `/{automation_id}` | [`Backend/api/endpoints/automations.py:116`](Backend/api/endpoints/automations.py#L116) | `read` |
| `PUT` | `/{automation_id}` | [`Backend/api/endpoints/automations.py:181`](Backend/api/endpoints/automations.py#L181) | `required` |
| `POST` | `/{automation_id}/pause` | [`Backend/api/endpoints/automations.py:376`](Backend/api/endpoints/automations.py#L376) | `required` |
| `POST` | `/{automation_id}/resume` | [`Backend/api/endpoints/automations.py:411`](Backend/api/endpoints/automations.py#L411) | `required` |
| `GET` | `/{automation_id}/runs` | [`Backend/api/endpoints/automations.py:252`](Backend/api/endpoints/automations.py#L252) | `read` |
| `POST` | `/{automation_id}/start` | [`Backend/api/endpoints/automations.py:337`](Backend/api/endpoints/automations.py#L337) | `required` |
| `DELETE` | `/{brand_id}` | [`Backend/api/endpoints/brands.py:251`](Backend/api/endpoints/brands.py#L251) | `required` |
| `GET` | `/{brand_id}` | [`Backend/api/endpoints/brands.py:171`](Backend/api/endpoints/brands.py#L171) | `read` |
| `PATCH` | `/{brand_id}` | [`Backend/api/endpoints/brands.py:199`](Backend/api/endpoints/brands.py#L199) | `required` |
| `GET` | `/{character_id}` | [`Backend/api/endpoints/characters.py:293`](Backend/api/endpoints/characters.py#L293) | `read` |
| `POST` | `/{character_id}/batch-remove-background` | [`Backend/api/endpoints/characters.py:584`](Backend/api/endpoints/characters.py#L584) | `required` |
| `GET` | `/{character_id}/index` | [`Backend/api/endpoints/characters.py:363`](Backend/api/endpoints/characters.py#L363) | `read` |
| `POST` | `/{character_id}/remove-background` | [`Backend/api/endpoints/characters.py:469`](Backend/api/endpoints/characters.py#L469) | `required` |
| `GET` | `/{character_id}/variants` | [`Backend/api/endpoints/characters.py:332`](Backend/api/endpoints/characters.py#L332) | `read` |
| `POST` | `/{character_id}/variants` | [`Backend/api/endpoints/characters.py:185`](Backend/api/endpoints/characters.py#L185) | `required` |
| `POST` | `/{character_id}/variants/{variant_id}/remove-background` | [`Backend/api/endpoints/characters.py:536`](Backend/api/endpoints/characters.py#L536) | `required` |
| `DELETE` | `/{clip_id}` | [`Backend/api/endpoints/clip_management.py:120`](Backend/api/endpoints/clip_management.py#L120) | `required` |
| `GET` | `/{clip_id}` | [`Backend/api/endpoints/clip_management.py:97`](Backend/api/endpoints/clip_management.py#L97) | `read` |
| `PUT` | `/{clip_id}` | [`Backend/api/endpoints/clip_management.py:108`](Backend/api/endpoints/clip_management.py#L108) | `required` |
| `GET` | `/{clip_id}/performance` | [`Backend/api/endpoints/clip_management.py:189`](Backend/api/endpoints/clip_management.py#L189) | `read` |
| `GET` | `/{clip_id}/posts` | [`Backend/api/endpoints/clip_management.py:181`](Backend/api/endpoints/clip_management.py#L181) | `read` |
| `POST` | `/{clip_id}/publish` | [`Backend/api/endpoints/clip_management.py:160`](Backend/api/endpoints/clip_management.py#L160) | `required` |
| `GET` | `/{clip_id}/stream` | [`Backend/api/endpoints/clips.py:161`](Backend/api/endpoints/clips.py#L161) | `read` |
| `POST` | `/{clip_id}/variants` | [`Backend/api/endpoints/clip_management.py:146`](Backend/api/endpoints/clip_management.py#L146) | `required` |
| `GET` | `/{content_id}` | [`Backend/api/endpoints/content_variations.py:111`](Backend/api/endpoints/content_variations.py#L111) | `read` |
| `GET` | `/{content_id}/metrics` | [`Backend/api/endpoints/content_metrics.py:123`](Backend/api/endpoints/content_metrics.py#L123) | `read` |
| `GET` | `/{content_id}/next` | [`Backend/api/endpoints/content_variations.py:161`](Backend/api/endpoints/content_variations.py#L161) | `read` |
| `POST` | `/{content_id}/recompute-rollup` | [`Backend/api/endpoints/content_metrics.py:157`](Backend/api/endpoints/content_metrics.py#L157) | `required` |
| `GET` | `/{content_id}/rollup` | [`Backend/api/endpoints/content_metrics.py:106`](Backend/api/endpoints/content_metrics.py#L106) | `read` |
| `GET` | `/{content_id}/stats` | [`Backend/api/endpoints/content_variations.py:277`](Backend/api/endpoints/content_variations.py#L277) | `read` |
| `GET` | `/{content_id}/suggest-repost` | [`Backend/api/endpoints/content_variations.py:302`](Backend/api/endpoints/content_variations.py#L302) | `read` |
| `GET` | `/{correlation_id}` | [`Backend/api/endpoints/workflows.py:55`](Backend/api/endpoints/workflows.py#L55) | `read` |
| `GET` | `/{correlation_id}/events` | [`Backend/api/endpoints/workflows.py:70`](Backend/api/endpoints/workflows.py#L70) | `read` |
| `GET` | `/{experiment_id}` | [`Backend/api/endpoints/experiments.py:376`](Backend/api/endpoints/experiments.py#L376) | `read` |
| `POST` | `/{experiment_id}/calculate-confidence` | [`Backend/api/endpoints/experiments.py:1106`](Backend/api/endpoints/experiments.py#L1106) | `required` |
| `POST` | `/{experiment_id}/complete` | [`Backend/api/endpoints/experiments.py:556`](Backend/api/endpoints/experiments.py#L556) | `required` |
| `POST` | `/{experiment_id}/generate-rule` | [`Backend/api/endpoints/experiments.py:1176`](Backend/api/endpoints/experiments.py#L1176) | `required` |
| `GET` | `/{experiment_id}/scheduled-variants` | [`Backend/api/endpoints/experiments.py:1380`](Backend/api/endpoints/experiments.py#L1380) | `read` |
| `POST` | `/{experiment_id}/start` | [`Backend/api/endpoints/experiments.py:512`](Backend/api/endpoints/experiments.py#L512) | `required` |
| `POST` | `/{experiment_id}/stop` | [`Backend/api/endpoints/experiments.py:540`](Backend/api/endpoints/experiments.py#L540) | `required` |
| `PUT` | `/{experiment_id}/variant/{variant_id}/metrics` | [`Backend/api/endpoints/experiments.py:628`](Backend/api/endpoints/experiments.py#L628) | `required` |
| `DELETE` | `/{filename}` | [`Backend/api/endpoints/backup.py:150`](Backend/api/endpoints/backup.py#L150) | `required` |
| `DELETE` | `/{format_id}` | [`Backend/api/endpoints/formats.py:284`](Backend/api/endpoints/formats.py#L284) | `required` |
| `DELETE` | `/{format_id}` | [`Backend/api/endpoints/formats_api.py:270`](Backend/api/endpoints/formats_api.py#L270) | `required` |
| `DELETE` | `/{format_id}` | [`Backend/api/routes/video_formats.py:214`](Backend/api/routes/video_formats.py#L214) | `required` |
| `GET` | `/{format_id}` | [`Backend/api/endpoints/formats.py:156`](Backend/api/endpoints/formats.py#L156) | `read` |
| `GET` | `/{format_id}` | [`Backend/api/endpoints/formats_api.py:175`](Backend/api/endpoints/formats_api.py#L175) | `read` |
| `GET` | `/{format_id}` | [`Backend/api/routes/video_formats.py:129`](Backend/api/routes/video_formats.py#L129) | `read` |
| `PUT` | `/{format_id}` | [`Backend/api/endpoints/formats.py:229`](Backend/api/endpoints/formats.py#L229) | `required` |
| `POST` | `/{format_id}/generate` | [`Backend/api/routes/video_formats.py:163`](Backend/api/routes/video_formats.py#L163) | `required` |
| `POST` | `/{format_id}/run` | [`Backend/api/endpoints/formats.py:306`](Backend/api/endpoints/formats.py#L306) | `required` |
| `POST` | `/{format_id}/run` | [`Backend/api/endpoints/formats_api.py:213`](Backend/api/endpoints/formats_api.py#L213) | `required` |
| `GET` | `/{format_id}/runs` | [`Backend/api/endpoints/formats.py:351`](Backend/api/endpoints/formats.py#L351) | `read` |
| `GET` | `/{format_id}/runs` | [`Backend/api/endpoints/formats_api.py:248`](Backend/api/endpoints/formats_api.py#L248) | `read` |
| `DELETE` | `/{goal_id}` | [`Backend/api/endpoints/goals.py:113`](Backend/api/endpoints/goals.py#L113) | `required` |
| `PATCH` | `/{goal_id}` | [`Backend/api/endpoints/goals.py:87`](Backend/api/endpoints/goals.py#L87) | `required` |
| `GET` | `/{goal_id}/recommendations` | [`Backend/api/endpoints/goal_recommendations.py:21`](Backend/api/endpoints/goal_recommendations.py#L21) | `read` |
| `POST` | `/{goal_id}/refresh-progress` | [`Backend/api/endpoints/goals.py:122`](Backend/api/endpoints/goals.py#L122) | `required` |
| `GET` | `/{highlight_id}/reasoning` | [`Backend/api/endpoints/highlights.py:183`](Backend/api/endpoints/highlights.py#L183) | `read` |
| `DELETE` | `/{hook_id}` | [`Backend/api/endpoints/hook_library_api.py:131`](Backend/api/endpoints/hook_library_api.py#L131) | `required` |
| `POST` | `/{hook_id}/ab-test` | [`Backend/api/endpoints/hook_library_api.py:210`](Backend/api/endpoints/hook_library_api.py#L210) | `required` |
| `POST` | `/{hook_id}/favorite` | [`Backend/api/endpoints/hook_library_api.py:111`](Backend/api/endpoints/hook_library_api.py#L111) | `required` |
| `PATCH` | `/{hook_id}/track-results` | [`Backend/api/endpoints/hook_library_api.py:270`](Backend/api/endpoints/hook_library_api.py#L270) | `required` |
| `POST` | `/{hook_id}/track-usage` | [`Backend/api/endpoints/hook_library_api.py:223`](Backend/api/endpoints/hook_library_api.py#L223) | `required` |
| `POST` | `/{hook_id}/used` | [`Backend/api/endpoints/hook_library_api.py:121`](Backend/api/endpoints/hook_library_api.py#L121) | `required` |
| `DELETE` | `/{icp_id}` | [`Backend/api/endpoints/icps.py:248`](Backend/api/endpoints/icps.py#L248) | `required` |
| `GET` | `/{icp_id}` | [`Backend/api/endpoints/icps.py:168`](Backend/api/endpoints/icps.py#L168) | `read` |
| `PATCH` | `/{icp_id}` | [`Backend/api/endpoints/icps.py:196`](Backend/api/endpoints/icps.py#L196) | `required` |
| `DELETE` | `/{idea_id}` | [`Backend/api/endpoints/content_ideas_api.py:390`](Backend/api/endpoints/content_ideas_api.py#L390) | `required` |
| `POST` | `/{idea_id}/generate-brief` | [`Backend/api/endpoints/content_ideas_api.py:451`](Backend/api/endpoints/content_ideas_api.py#L451) | `required` |
| `PATCH` | `/{idea_id}/schedule` | [`Backend/api/endpoints/content_ideas_api.py:359`](Backend/api/endpoints/content_ideas_api.py#L359) | `required` |
| `PATCH` | `/{idea_id}/status` | [`Backend/api/endpoints/content_ideas_api.py:338`](Backend/api/endpoints/content_ideas_api.py#L338) | `required` |
| `POST` | `/{id}/action` | [`Backend/api/endpoints/ai_recommendations.py:55`](Backend/api/endpoints/ai_recommendations.py#L55) | `required` |
| `DELETE` | `/{item_id}/cancel` | [`Backend/api/endpoints/publishing_queue.py:261`](Backend/api/endpoints/publishing_queue.py#L261) | `required` |
| `PUT` | `/{item_id}/reschedule` | [`Backend/api/endpoints/publishing_queue.py:237`](Backend/api/endpoints/publishing_queue.py#L237) | `required` |
| `PUT` | `/{item_id}/retry` | [`Backend/api/endpoints/publishing_queue.py:218`](Backend/api/endpoints/publishing_queue.py#L218) | `required` |
| `DELETE` | `/{job_id}` | [`Backend/api/endpoints/video_generation.py:198`](Backend/api/endpoints/video_generation.py#L198) | `required` |
| `GET` | `/{job_id}` | [`Backend/api/endpoints/jobs.py:54`](Backend/api/endpoints/jobs.py#L54) | `read` |
| `GET` | `/{job_id}` | [`Backend/api/endpoints/video_generation.py:143`](Backend/api/endpoints/video_generation.py#L143) | `read` |
| `GET` | `/{key}` | [`Backend/api/endpoints/app_settings.py:52`](Backend/api/endpoints/app_settings.py#L52) | `read` |
| `PUT` | `/{key}` | [`Backend/api/endpoints/app_settings.py:76`](Backend/api/endpoints/app_settings.py#L76) | `required` |
| `DELETE` | `/{media_id}` | [`Backend/api/media_processing.py:589`](Backend/api/media_processing.py#L589) | `required` |
| `DELETE` | `/{media_id}` | [`Backend/api/media_processing_db.py:3063`](Backend/api/media_processing_db.py#L3063) | `required` |
| `GET` | `/{media_id}` | [`Backend/api/endpoints/audio_analysis.py:264`](Backend/api/endpoints/audio_analysis.py#L264) | `read` |
| `DELETE` | `/{offer_id}` | [`Backend/api/endpoints/offers.py:272`](Backend/api/endpoints/offers.py#L272) | `required` |
| `GET` | `/{offer_id}` | [`Backend/api/endpoints/offers.py:187`](Backend/api/endpoints/offers.py#L187) | `read` |
| `PATCH` | `/{offer_id}` | [`Backend/api/endpoints/offers.py:215`](Backend/api/endpoints/offers.py#L215) | `required` |
| `GET` | `/{person_id}` | [`Backend/api/endpoints/people.py:147`](Backend/api/endpoints/people.py#L147) | `read` |
| `GET` | `/{person_id}/insights` | [`Backend/api/endpoints/people.py:165`](Backend/api/endpoints/people.py#L165) | `read` |
| `POST` | `/{person_id}/recompute-lens` | [`Backend/api/endpoints/people.py:190`](Backend/api/endpoints/people.py#L190) | `required` |
| `DELETE` | `/{post_id}` | [`Backend/api/endpoints/schedule.py:643`](Backend/api/endpoints/schedule.py#L643) | `required` |
| `GET` | `/{post_id}` | [`Backend/api/endpoints/schedule.py:439`](Backend/api/endpoints/schedule.py#L439) | `read` |
| `GET` | `/{post_id}` | [`Backend/api/posted_media.py:370`](Backend/api/posted_media.py#L370) | `read` |
| `PATCH` | `/{post_id}` | [`Backend/api/endpoints/posted_content.py:233`](Backend/api/endpoints/posted_content.py#L233) | `required` |
| `PUT` | `/{post_id}` | [`Backend/api/endpoints/schedule.py:474`](Backend/api/endpoints/schedule.py#L474) | `required` |
| `POST` | `/{post_id}/checkback` | [`Backend/api/endpoints/post_tracking.py:192`](Backend/api/endpoints/post_tracking.py#L192) | `required` |
| `GET` | `/{post_id}/comments` | [`Backend/api/endpoints/posted_content.py:627`](Backend/api/endpoints/posted_content.py#L627) | `read` |
| `POST` | `/{post_id}/publish` | [`Backend/api/endpoints/schedule.py:1090`](Backend/api/endpoints/schedule.py#L1090) | `required` |
| `POST` | `/{post_id}/reschedule` | [`Backend/api/endpoints/schedule.py:672`](Backend/api/endpoints/schedule.py#L672) | `required` |
| `GET` | `/{post_id}/score` | [`Backend/api/endpoints/post_tracking.py:149`](Backend/api/endpoints/post_tracking.py#L149) | `read` |
| `GET` | `/{post_id}/status` | [`Backend/api/endpoints/post_tracking.py:115`](Backend/api/endpoints/post_tracking.py#L115) | `read` |
| `GET` | `/{segment_id}` | [`Backend/api/endpoints/segments.py:116`](Backend/api/endpoints/segments.py#L116) | `read` |
| `GET` | `/{segment_id}/insights` | [`Backend/api/endpoints/segments.py:158`](Backend/api/endpoints/segments.py#L158) | `read` |
| `DELETE` | `/{template_id}` | [`Backend/api/endpoints/templates.py:409`](Backend/api/endpoints/templates.py#L409) | `required` |
| `GET` | `/{template_id}` | [`Backend/api/endpoints/templates.py:197`](Backend/api/endpoints/templates.py#L197) | `read` |
| `PUT` | `/{template_id}` | [`Backend/api/endpoints/templates.py:333`](Backend/api/endpoints/templates.py#L333) | `required` |
| `POST` | `/{template_id}/fork` | [`Backend/api/endpoints/templates.py:451`](Backend/api/endpoints/templates.py#L451) | `required` |
| `GET` | `/{test_id}` | [`Backend/api/ab_testing.py:72`](Backend/api/ab_testing.py#L72) | `read` |
| `POST` | `/{test_id}/analyze` | [`Backend/api/ab_testing.py:93`](Backend/api/ab_testing.py#L93) | `required` |
| `POST` | `/{test_id}/collect` | [`Backend/api/ab_testing.py:84`](Backend/api/ab_testing.py#L84) | `required` |
| `POST` | `/{test_id}/declare` | [`Backend/api/ab_testing.py:102`](Backend/api/ab_testing.py#L102) | `required` |
| `GET` | `/{track_id}` | [`Backend/api/endpoints/music_library.py:311`](Backend/api/endpoints/music_library.py#L311) | `read` |
| `POST` | `/{track_id}/use` | [`Backend/api/endpoints/music_library.py:370`](Backend/api/endpoints/music_library.py#L370) | `required` |
| `GET` | `/{trend_id}` | [`Backend/api/trend_detection.py:81`](Backend/api/trend_detection.py#L81) | `read` |
| `POST` | `/{trend_id}/generate-brief` | [`Backend/api/trend_detection.py:126`](Backend/api/trend_detection.py#L126) | `required` |
| `DELETE` | `/{video_id}` | [`Backend/api/endpoints/videos.py:346`](Backend/api/endpoints/videos.py#L346) | `required` |
| `GET` | `/{video_id}` | [`Backend/api/endpoints/videos.py:253`](Backend/api/endpoints/videos.py#L253) | `read` |
| `POST` | `/{video_id}/analyze` | [`Backend/api/endpoints/videos.py:990`](Backend/api/endpoints/videos.py#L990) | `required` |
| `GET` | `/{video_id}/clips` | [`Backend/api/endpoints/videos.py:328`](Backend/api/endpoints/videos.py#L328) | `read` |
| `POST` | `/{video_id}/generate-thumbnail` | [`Backend/api/endpoints/videos.py:794`](Backend/api/endpoints/videos.py#L794) | `required` |
| `GET` | `/{video_id}/summary` | [`Backend/api/endpoints/videos.py:273`](Backend/api/endpoints/videos.py#L273) | `read` |
| `GET` | `/{voice_id}` | [`Backend/api/endpoints/voice_selection.py:153`](Backend/api/endpoints/voice_selection.py#L153) | `read` |
| `DELETE` | `/{workspace_id}` | [`Backend/api/endpoints/workspaces.py:266`](Backend/api/endpoints/workspaces.py#L266) | `required` |
| `GET` | `/{workspace_id}` | [`Backend/api/endpoints/workspaces.py:150`](Backend/api/endpoints/workspaces.py#L150) | `read` |
| `PATCH` | `/{workspace_id}` | [`Backend/api/endpoints/workspaces.py:193`](Backend/api/endpoints/workspaces.py#L193) | `required` |
| `GET` | `/{workspace_id}/members` | [`Backend/api/endpoints/workspaces.py:300`](Backend/api/endpoints/workspaces.py#L300) | `read` |

## Formal file contracts

| Contract | Kind | Required fields | Join fields | Hash |
|---|---|---|---|---|
| [`Social Intelligence Unified API`](Backend/docs/rapidapi/openapi-unified.yaml)<br>`Backend/docs/rapidapi/openapi-unified.yaml` | `openapi` | - | - | `6e1ab70f9cb5` |
| [`MediaPoster control-plane publication contracts`](schema/control-plane-publication.schema.json)<br>`schema/control-plane-publication.schema.json` | `json_schema` | - | airtime_account_id, asset_id, attempt_id, content_work_item_id, destination_id, generation_approval_id, production_plan_id, provider_account_id | `0edc6d8dc83f` |

## Typed application models

| Model | Kind | Source |
|---|---|---|
| `ABTestRequest` | `python-pydantic` | [`Backend/api/endpoints/adaptive_scheduler.py`](Backend/api/endpoints/adaptive_scheduler.py) |
| `AICoachInsight` | `python-pydantic` | [`Backend/models/supabase_models.py`](Backend/models/supabase_models.py) |
| `AICommentRequest` | `python-pydantic` | [`Backend/api/endpoints/instagram_automation.py`](Backend/api/endpoints/instagram_automation.py) |
| `AICommentResponse` | `python-pydantic` | [`Backend/api/endpoints/instagram_automation.py`](Backend/api/endpoints/instagram_automation.py) |
| `AIMessageRequest` | `python-pydantic` | [`Backend/api/endpoints/tiktok_automation.py`](Backend/api/endpoints/tiktok_automation.py) |
| `AIMessageRequest` | `python-pydantic` | [`Backend/api/endpoints/twitter_automation.py`](Backend/api/endpoints/twitter_automation.py) |
| `AIMessageResponse` | `python-pydantic` | [`Backend/api/endpoints/tiktok_automation.py`](Backend/api/endpoints/tiktok_automation.py) |
| `AIMessageResponse` | `python-pydantic` | [`Backend/api/endpoints/twitter_automation.py`](Backend/api/endpoints/twitter_automation.py) |
| `APIUsageStats` | `python-pydantic` | [`Backend/api/rapidapi_metrics.py`](Backend/api/rapidapi_metrics.py) |
| `AcceptanceCheckSchema` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `AcceptanceCriteriaSchema` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `AccountConfig` | `python-pydantic` | [`Backend/api/endpoints/blotato_test.py`](Backend/api/endpoints/blotato_test.py) |
| `AccountDownloadRequest` | `python-pydantic` | [`Backend/api/endpoints/content_download.py`](Backend/api/endpoints/content_download.py) |
| `AccountLearnings` | `python-pydantic` | [`Backend/services/competitor_analysis_service.py`](Backend/services/competitor_analysis_service.py) |
| `AccountMetrics` | `python-pydantic` | [`Backend/api/analytics_compare.py`](Backend/api/analytics_compare.py) |
| `AccountPublishItem` | `python-pydantic` | [`Backend/api/blotato_router.py`](Backend/api/blotato_router.py) |
| `AccountSummary` | `python-pydantic` | [`Backend/api/endpoints/social_analytics.py`](Backend/api/endpoints/social_analytics.py) |
| `AdDeployment` | `python-pydantic` | [`Backend/services/creative_testing_pipeline/models.py`](Backend/services/creative_testing_pipeline/models.py) |
| `AdaptRequest` | `python-pydantic` | [`Backend/api/endpoints/adaptive_scheduler.py`](Backend/api/endpoints/adaptive_scheduler.py) |
| `AddAccountRequest` | `python-pydantic` | [`Backend/api/endpoints/competitor_api.py`](Backend/api/endpoints/competitor_api.py) |
| `AddAccountRequest` | `python-pydantic` | [`Backend/api/endpoints/social_accounts.py`](Backend/api/endpoints/social_accounts.py) |
| `AddHookRequest` | `python-pydantic` | [`Backend/api/endpoints/hook_library_api.py`](Backend/api/endpoints/hook_library_api.py) |
| `AddItemRequest` | `python-pydantic` | [`Backend/api/endpoints/approval_queue.py`](Backend/api/endpoints/approval_queue.py) |
| `AddNoteRequest` | `python-pydantic` | [`Backend/api/endpoints/dm_outreach.py`](Backend/api/endpoints/dm_outreach.py) |
| `AddPlaylistRequest` | `python-pydantic` | [`Backend/api/endpoints/youtube_automation.py`](Backend/api/endpoints/youtube_automation.py) |
| `AddProspectRequest` | `python-pydantic` | [`Backend/api/endpoints/dm_outreach.py`](Backend/api/endpoints/dm_outreach.py) |
| `AddReferenceAudioRequest` | `python-pydantic` | [`Backend/api/endpoints/voice_cloning.py`](Backend/api/endpoints/voice_cloning.py) |
| `AddTagsRequest` | `python-pydantic` | [`Backend/api/endpoints/inbox.py`](Backend/api/endpoints/inbox.py) |
| `AddToListRequest` | `python-pydantic` | [`Backend/api/endpoints/dm_outreach.py`](Backend/api/endpoints/dm_outreach.py) |
| `AdjustmentThresholdsRequest` | `python-pydantic` | [`Backend/api/endpoints/autonomy.py`](Backend/api/endpoints/autonomy.py) |
| `AllocationsResponse` | `python-pydantic` | [`Backend/api/endpoints/bandit.py`](Backend/api/endpoints/bandit.py) |
| `AnalysisJobResponse` | `python-pydantic` | [`Backend/api/endpoints/content_analyzer_api.py`](Backend/api/endpoints/content_analyzer_api.py) |
| `AnalysisRequest` | `python-pydantic` | [`Backend/api/endpoints/analysis.py`](Backend/api/endpoints/analysis.py) |
| `AnalysisRequest` | `python-pydantic` | [`Backend/api/endpoints/strategic_analysis.py`](Backend/api/endpoints/strategic_analysis.py) |
| `AnalysisRequest` | `python-pydantic` | [`Backend/api/image_analysis.py`](Backend/api/image_analysis.py) |
| `AnalysisResponse` | `python-pydantic` | [`Backend/api/endpoints/analysis.py`](Backend/api/endpoints/analysis.py) |
| `AnalysisResponse` | `python-pydantic` | [`Backend/api/endpoints/strategic_analysis.py`](Backend/api/endpoints/strategic_analysis.py) |
| `AnalysisResponse` | `python-pydantic` | [`Backend/api/endpoints/viral_analysis.py`](Backend/api/endpoints/viral_analysis.py) |
| `AnalysisResult` | `python-pydantic` | [`Backend/api/media_processing.py`](Backend/api/media_processing.py) |
| `AnalysisResultResponse` | `python-pydantic` | [`Backend/api/endpoints/content_analyzer_api.py`](Backend/api/endpoints/content_analyzer_api.py) |
| `AnalysisSaveRequest` | `python-pydantic` | [`Backend/api/media_processing_db.py`](Backend/api/media_processing_db.py) |
| `AnalyticsResponse` | `python-pydantic` | [`Backend/api/endpoints/analytics.py`](Backend/api/endpoints/analytics.py) |
| `AnalyzeFileRequest` | `python-pydantic` | [`Backend/api/endpoints/analysis.py`](Backend/api/endpoints/analysis.py) |
| `AnalyzeFileResponse` | `python-pydantic` | [`Backend/api/endpoints/analysis.py`](Backend/api/endpoints/analysis.py) |
| `AnalyzeInfluencerRequest` | `python-pydantic` | [`Backend/api/endpoints/influencer_analysis.py`](Backend/api/endpoints/influencer_analysis.py) |
| `AnalyzeRequest` | `python-pydantic` | [`Backend/api/content_pipeline.py`](Backend/api/content_pipeline.py) |
| `AnalyzeRequest` | `python-pydantic` | [`Backend/api/endpoints/content_analyzer_api.py`](Backend/api/endpoints/content_analyzer_api.py) |
| `AnalyzeVideoRequest` | `python-pydantic` | [`Backend/api/endpoints/video_routing_api.py`](Backend/api/endpoints/video_routing_api.py) |
| `AppRanking` | `python-pydantic` | [`Backend/api/endpoints/trends.py`](Backend/api/endpoints/trends.py) |
| `ApprovalAction` | `python-pydantic` | [`Backend/api/approval_queue.py`](Backend/api/approval_queue.py) |
| `ApprovalItemResponse` | `python-pydantic` | [`Backend/api/endpoints/approval_queue.py`](Backend/api/endpoints/approval_queue.py) |
| `ApprovalReference` | `python-pydantic` | [`Backend/api/control_plane_publications.py`](Backend/api/control_plane_publications.py) |
| `ApproveClipRequest` | `python-pydantic` | [`Backend/api/endpoints/repurpose.py`](Backend/api/endpoints/repurpose.py) |
| `ApproveRequest` | `python-pydantic` | [`Backend/api/content_pipeline.py`](Backend/api/content_pipeline.py) |
| `AssessmentResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `AssetClipV2` | `python-pydantic` | [`Backend/services/video_generation/shot_types.py`](Backend/services/video_generation/shot_types.py) |
| `AssetManifestV1` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `AssetReference` | `python-pydantic` | [`Backend/api/control_plane_publications.py`](Backend/api/control_plane_publications.py) |
| `AssetResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `AssignMessageRequest` | `python-pydantic` | [`Backend/api/endpoints/inbox.py`](Backend/api/endpoints/inbox.py) |
| `AssignRequest` | `python-pydantic` | [`Backend/api/endpoints/approval_queue.py`](Backend/api/endpoints/approval_queue.py) |
| `AudienceDemographics` | `python-pydantic` | [`Backend/api/analytics_compare.py`](Backend/api/analytics_compare.py) |
| `AudioAnalysisResponse` | `python-pydantic` | [`Backend/api/endpoints/audio_analysis.py`](Backend/api/endpoints/audio_analysis.py) |
| `AudioBusConfig` | `python-pydantic` | [`Backend/services/video_generation/audio_bus_mixer.py`](Backend/services/video_generation/audio_bus_mixer.py) |
| `AudioBusResult` | `python-pydantic` | [`Backend/services/video_generation/audio_bus_mixer.py`](Backend/services/video_generation/audio_bus_mixer.py) |
| `AudioConfig` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `AudioEvents` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `AudioIntent` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `AudioMetadata` | `python-pydantic` | [`Backend/services/audio_service.py`](Backend/services/audio_service.py) |
| `AudioMixRequest` | `python-pydantic` | [`Backend/api/endpoints/video_pipeline.py`](Backend/api/endpoints/video_pipeline.py) |
| `AudioResponse` | `python-pydantic` | [`Backend/api/endpoints/audio_api.py`](Backend/api/endpoints/audio_api.py) |
| `AudioTrack` | `python-pydantic` | [`Backend/services/video_generation/audio_bus_mixer.py`](Backend/services/video_generation/audio_bus_mixer.py) |
| `AudioTrackRequest` | `python-pydantic` | [`Backend/api/endpoints/remotion.py`](Backend/api/endpoints/remotion.py) |
| `AudioTrackSchema` | `python-pydantic` | [`Backend/services/media_factory/contracts/timeline.py`](Backend/services/media_factory/contracts/timeline.py) |
| `AuditStatusResponse` | `python-pydantic` | [`Backend/api/endpoints/competitor_audit.py`](Backend/api/endpoints/competitor_audit.py) |
| `AutoCurationSettings` | `python-pydantic` | [`Backend/api/ai_curation.py`](Backend/api/ai_curation.py) |
| `AutoReply` | `python-pydantic` | [`Backend/api/endpoints/comment_engagement.py`](Backend/api/endpoints/comment_engagement.py) |
| `AutoScheduleRequest` | `python-pydantic` | [`Backend/api/endpoints/adaptive_scheduler.py`](Backend/api/endpoints/adaptive_scheduler.py) |
| `AutoScheduleRequest` | `python-pydantic` | [`Backend/api/endpoints/inventory_scheduler.py`](Backend/api/endpoints/inventory_scheduler.py) |
| `AutoScheduleRequest` | `python-pydantic` | [`Backend/api/endpoints/publishing_analytics.py`](Backend/api/endpoints/publishing_analytics.py) |
| `AutomationRule` | `python-pydantic` | [`Backend/api/endpoints/comment_engagement.py`](Backend/api/endpoints/comment_engagement.py) |
| `AvailableExpressionsResponse` | `python-pydantic` | [`Backend/api/endpoints/characters.py`](Backend/api/endpoints/characters.py) |
| `AvailableStylesResponse` | `python-pydantic` | [`Backend/api/endpoints/characters.py`](Backend/api/endpoints/characters.py) |
| `BackfillJob` | `python-pydantic` | [`Backend/api/rapidapi_metrics.py`](Backend/api/rapidapi_metrics.py) |
| `BackfillStatus` | `python-pydantic` | [`Backend/api/content_growth.py`](Backend/api/content_growth.py) |
| `BackgroundJobResponse` | `python-pydantic` | [`Backend/api/endpoints/jobs.py`](Backend/api/endpoints/jobs.py) |
| `BacklogIdea` | `python-pydantic` | [`Backend/api/endpoints/experiments.py`](Backend/api/endpoints/experiments.py) |
| `BackupRequest` | `python-pydantic` | [`Backend/api/endpoints/backup.py`](Backend/api/endpoints/backup.py) |
| `BackupResponse` | `python-pydantic` | [`Backend/api/endpoints/backup.py`](Backend/api/endpoints/backup.py) |
| `BatchAnalysisRequest` | `python-pydantic` | [`Backend/api/endpoints/audio_analysis.py`](Backend/api/endpoints/audio_analysis.py) |
| `BatchAnalysisRequest` | `python-pydantic` | [`Backend/api/endpoints/batch_analysis.py`](Backend/api/endpoints/batch_analysis.py) |
| `BatchCheckRequest` | `python-pydantic` | [`Backend/api/endpoints/content_guard.py`](Backend/api/endpoints/content_guard.py) |
| `BatchConfig` | `python-pydantic` | [`Backend/api/content_pipeline.py`](Backend/api/content_pipeline.py) |
| `BatchDownloadRequest` | `python-pydantic` | [`Backend/api/endpoints/content_download.py`](Backend/api/endpoints/content_download.py) |
| `BatchEmbedRequest` | `python-pydantic` | [`Backend/api/endpoints/semantic_search.py`](Backend/api/endpoints/semantic_search.py) |
| `BatchGenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/ai_titles.py`](Backend/api/endpoints/ai_titles.py) |
| `BatchGenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/sora.py`](Backend/api/endpoints/sora.py) |
| `BatchGenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/sora_automation.py`](Backend/api/endpoints/sora_automation.py) |
| `BatchGenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/voice_cloning.py`](Backend/api/endpoints/voice_cloning.py) |
| `BatchIngestRequest` | `python-pydantic` | [`Backend/api/media_processing.py`](Backend/api/media_processing.py) |
| `BatchIngestRequest` | `python-pydantic` | [`Backend/api/media_processing_db.py`](Backend/api/media_processing_db.py) |
| `BatchIngestResponse` | `python-pydantic` | [`Backend/api/media_processing.py`](Backend/api/media_processing.py) |
| `BatchIngestResponse` | `python-pydantic` | [`Backend/api/media_processing_db.py`](Backend/api/media_processing_db.py) |
| `BatchMatchRequest` | `python-pydantic` | [`Backend/api/endpoints/platform_matching.py`](Backend/api/endpoints/platform_matching.py) |
| `BatchRecycleRequest` | `python-pydantic` | [`Backend/api/content_recycling.py`](Backend/api/content_recycling.py) |
| `BatchRemoveBackgroundResponse` | `python-pydantic` | [`Backend/api/endpoints/characters.py`](Backend/api/endpoints/characters.py) |
| `BatchThumbnailRequest` | `python-pydantic` | [`Backend/api/endpoints/videos.py`](Backend/api/endpoints/videos.py) |
| `Beat` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `Beat` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `BeatDefaults` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `BeatExtractRequest` | `python-pydantic` | [`Backend/api/endpoints/video_pipeline.py`](Backend/api/endpoints/video_pipeline.py) |
| `BeatExtractResponse` | `python-pydantic` | [`Backend/api/endpoints/video_pipeline.py`](Backend/api/endpoints/video_pipeline.py) |
| `BeatExtractionResult` | `python-pydantic` | [`Backend/services/sfx_library/beat_extractor.py`](Backend/services/sfx_library/beat_extractor.py) |
| `BeatNarrationInput` | `python-pydantic` | [`Backend/services/video_generation/vo_stitcher.py`](Backend/services/video_generation/vo_stitcher.py) |
| `BeatQueryRequest` | `python-pydantic` | [`Backend/api/endpoints/broll_candidates.py`](Backend/api/endpoints/broll_candidates.py) |
| `BeatSec` | `python-pydantic` | [`Backend/services/sfx_library/macro_policy.py`](Backend/services/sfx_library/macro_policy.py) |
| `BeatShotPolicy` | `python-pydantic` | [`Backend/services/video_generation/auto_shot_planner.py`](Backend/services/video_generation/auto_shot_planner.py) |
| `BeatSpeechBudget` | `python-pydantic` | [`Backend/services/video_generation/voice_engine.py`](Backend/services/video_generation/voice_engine.py) |
| `BeatVoiceFlags` | `python-pydantic` | [`Backend/services/video_generation/voice_strategy.py`](Backend/services/video_generation/voice_strategy.py) |
| `BenchmarkResult` | `python-pydantic` | [`Backend/services/benchmark_service.py`](Backend/services/benchmark_service.py) |
| `BestFrameResponse` | `python-pydantic` | [`Backend/api/endpoints/thumbnails.py`](Backend/api/endpoints/thumbnails.py) |
| `BestMatchRequest` | `python-pydantic` | [`Backend/api/endpoints/sfx_library.py`](Backend/api/endpoints/sfx_library.py) |
| `BestTimeRequest` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `BestTimeResponse` | `python-pydantic` | [`Backend/api/endpoints/posting_optimizer_api.py`](Backend/api/endpoints/posting_optimizer_api.py) |
| `BgPlate` | `python-pydantic` | [`Backend/services/video_generation/shot_budgeter.py`](Backend/services/video_generation/shot_budgeter.py) |
| `BgShotSpec` | `python-pydantic` | [`Backend/services/video_generation/shot_budgeter.py`](Backend/services/video_generation/shot_budgeter.py) |
| `BibleResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `Binding` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `BrandContext` | `python-pydantic` | [`Backend/services/message_engine.py`](Backend/services/message_engine.py) |
| `BrandCreate` | `python-pydantic` | [`Backend/api/endpoints/brands.py`](Backend/api/endpoints/brands.py) |
| `BrandResponse` | `python-pydantic` | [`Backend/api/endpoints/brands.py`](Backend/api/endpoints/brands.py) |
| `BrandUpdate` | `python-pydantic` | [`Backend/api/endpoints/brands.py`](Backend/api/endpoints/brands.py) |
| `BrandVoice` | `python-pydantic` | [`Backend/api/endpoints/brands.py`](Backend/api/endpoints/brands.py) |
| `BriefAngleSchema` | `python-pydantic` | [`Backend/services/media_factory/contracts/content_brief.py`](Backend/services/media_factory/contracts/content_brief.py) |
| `BriefGenerateRequest` | `python-pydantic` | [`Backend/api/content_intelligence.py`](Backend/api/content_intelligence.py) |
| `BriefInput` | `python-pydantic` | [`Backend/api/endpoints/video_pipeline.py`](Backend/api/endpoints/video_pipeline.py) |
| `BriefRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_intelligence.py`](Backend/api/endpoints/trend_intelligence.py) |
| `BriefRequest` | `python-pydantic` | [`Backend/api/endpoints/trends_agent.py`](Backend/api/endpoints/trends_agent.py) |
| `BriefResponse` | `python-pydantic` | [`Backend/api/endpoints/creative_briefs.py`](Backend/api/endpoints/creative_briefs.py) |
| `BriefResponse` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `BriefResponse` | `python-pydantic` | [`Backend/api/explainer_video.py`](Backend/api/explainer_video.py) |
| `BriefResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `BriefScoreSchema` | `python-pydantic` | [`Backend/services/media_factory/contracts/content_brief.py`](Backend/services/media_factory/contracts/content_brief.py) |
| `BriefStatusUpdate` | `python-pydantic` | [`Backend/api/content_intelligence.py`](Backend/api/content_intelligence.py) |
| `BrollCandidate` | `python-pydantic` | [`Backend/api/endpoints/format_discovery.py`](Backend/api/endpoints/format_discovery.py) |
| `BrollCandidateResponse` | `python-pydantic` | [`Backend/api/endpoints/broll_producer.py`](Backend/api/endpoints/broll_producer.py) |
| `BrollIntent` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `BrollItem` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `BrollSlotQueryRequest` | `python-pydantic` | [`Backend/api/endpoints/broll_candidates.py`](Backend/api/endpoints/broll_candidates.py) |
| `BudgetPlan` | `python-pydantic` | [`Backend/services/video_generation/shot_budgeter.py`](Backend/services/video_generation/shot_budgeter.py) |
| `BulkAction` | `python-pydantic` | [`Backend/api/approval_queue.py`](Backend/api/approval_queue.py) |
| `BulkApproveRequest` | `python-pydantic` | [`Backend/api/comment_automation.py`](Backend/api/comment_automation.py) |
| `BulkEnqueueRequest` | `python-pydantic` | [`Backend/api/endpoints/publishing_controls.py`](Backend/api/endpoints/publishing_controls.py) |
| `BulkFilter` | `python-pydantic` | [`Backend/api/ai_curation.py`](Backend/api/ai_curation.py) |
| `BulkPublishRequest` | `python-pydantic` | [`Backend/api/blotato_router.py`](Backend/api/blotato_router.py) |
| `BulkQueueRequest` | `python-pydantic` | [`Backend/api/endpoints/ugc_content.py`](Backend/api/endpoints/ugc_content.py) |
| `BulkScheduleItem` | `python-pydantic` | [`Backend/api/endpoints/calendar.py`](Backend/api/endpoints/calendar.py) |
| `BulkScheduleRequest` | `python-pydantic` | [`Backend/api/endpoints/calendar.py`](Backend/api/endpoints/calendar.py) |
| `BulkScheduleRequest` | `python-pydantic` | [`Backend/api/endpoints/external_scheduling.py`](Backend/api/endpoints/external_scheduling.py) |
| `BulkScheduleRequest` | `python-pydantic` | [`Backend/api/endpoints/publishing_queue.py`](Backend/api/endpoints/publishing_queue.py) |
| `BulkSettingsUpdate` | `python-pydantic` | [`Backend/api/endpoints/app_settings.py`](Backend/api/endpoints/app_settings.py) |
| `CTA` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `CampaignDetail` | `python-pydantic` | [`Backend/services/creative_testing_pipeline/models.py`](Backend/services/creative_testing_pipeline/models.py) |
| `CampaignReportResponse` | `python-pydantic` | [`Backend/api/endpoints/offer_tracking.py`](Backend/api/endpoints/offer_tracking.py) |
| `CampaignSummary` | `python-pydantic` | [`Backend/api/endpoints/offer_tracking.py`](Backend/api/endpoints/offer_tracking.py) |
| `CampaignSummary` | `python-pydantic` | [`Backend/services/creative_testing_pipeline/models.py`](Backend/services/creative_testing_pipeline/models.py) |
| `CancelResponse` | `python-pydantic` | [`Backend/control_plane/schemas.py`](Backend/control_plane/schemas.py) |
| `CaptionConfigRequest` | `python-pydantic` | [`Backend/api/endpoints/remotion.py`](Backend/api/endpoints/remotion.py) |
| `CaptionConfigSchema` | `python-pydantic` | [`Backend/services/media_factory/contracts/timeline.py`](Backend/services/media_factory/contracts/timeline.py) |
| `CaptionGenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/captions.py`](Backend/api/endpoints/captions.py) |
| `CaptionResponse` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `CaptionsRequest` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `CaptionsResponse` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `CapturePostURLRequest` | `python-pydantic` | [`Backend/api/endpoints/post_tracking.py`](Backend/api/endpoints/post_tracking.py) |
| `CarouselRequest` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `CarouselResponse` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `CarouselSlideResponse` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `CascadeRuleRequest` | `python-pydantic` | [`Backend/api/cascade_publisher.py`](Backend/api/cascade_publisher.py) |
| `CategoryStats` | `python-pydantic` | [`Backend/api/endpoints/review.py`](Backend/api/endpoints/review.py) |
| `ChannelAnalyzeRequest` | `python-pydantic` | [`Backend/api/endpoints/channel_analyzer.py`](Backend/api/endpoints/channel_analyzer.py) |
| `ChannelBatchRequest` | `python-pydantic` | [`Backend/api/endpoints/channel_analyzer.py`](Backend/api/endpoints/channel_analyzer.py) |
| `ChannelResponse` | `python-pydantic` | [`Backend/api/endpoints/channel_analyzer.py`](Backend/api/endpoints/channel_analyzer.py) |
| `CharPlacement` | `python-pydantic` | [`Backend/services/video_generation/char_variety.py`](Backend/services/video_generation/char_variety.py) |
| `CharVarietyConfig` | `python-pydantic` | [`Backend/services/video_generation/char_variety.py`](Backend/services/video_generation/char_variety.py) |
| `CharacterCreate` | `python-pydantic` | [`Backend/api/endpoints/ai_video_generation.py`](Backend/api/endpoints/ai_video_generation.py) |
| `CharacterIndexResponse` | `python-pydantic` | [`Backend/api/endpoints/characters.py`](Backend/api/endpoints/characters.py) |
| `CharacterResponse` | `python-pydantic` | [`Backend/api/endpoints/characters.py`](Backend/api/endpoints/characters.py) |
| `CharacterVariantResponse` | `python-pydantic` | [`Backend/api/endpoints/characters.py`](Backend/api/endpoints/characters.py) |
| `ChatMessage` | `python-pydantic` | [`Backend/api/ai_chat.py`](Backend/api/ai_chat.py) |
| `ChatMessage` | `python-pydantic` | [`Backend/api/endpoints/coaching.py`](Backend/api/endpoints/coaching.py) |
| `ChatRequest` | `python-pydantic` | [`Backend/api/ai_chat.py`](Backend/api/ai_chat.py) |
| `ChatRequest` | `python-pydantic` | [`Backend/api/endpoints/coaching.py`](Backend/api/endpoints/coaching.py) |
| `ChatResponse` | `python-pydantic` | [`Backend/api/ai_chat.py`](Backend/api/ai_chat.py) |
| `ChatResponse` | `python-pydantic` | [`Backend/api/endpoints/coaching.py`](Backend/api/endpoints/coaching.py) |
| `CheckBreakdownResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `ClassificationRule` | `python-pydantic` | [`Backend/services/video_generation/script_classifier.py`](Backend/services/video_generation/script_classifier.py) |
| `ClearDiscoveredRequest` | `python-pydantic` | [`Backend/api/endpoints/content_sourcing.py`](Backend/api/endpoints/content_sourcing.py) |
| `ClickEventRequest` | `python-pydantic` | [`Backend/api/endpoints/offer_tracking.py`](Backend/api/endpoints/offer_tracking.py) |
| `Clip` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `ClipCreateRequest` | `python-pydantic` | [`Backend/api/endpoints/clip_management.py`](Backend/api/endpoints/clip_management.py) |
| `ClipInfo` | `python-pydantic` | [`Backend/api/endpoints/clip_extraction.py`](Backend/api/endpoints/clip_extraction.py) |
| `ClipPlanResponse` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `ClipPlanResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `ClipPublishRequest` | `python-pydantic` | [`Backend/api/endpoints/clip_management.py`](Backend/api/endpoints/clip_management.py) |
| `ClipRequest` | `python-pydantic` | [`Backend/api/endpoints/adaptive_scheduler.py`](Backend/api/endpoints/adaptive_scheduler.py) |
| `ClipRequest` | `python-pydantic` | [`Backend/api/endpoints/clips.py`](Backend/api/endpoints/clips.py) |
| `ClipResponse` | `python-pydantic` | [`Backend/api/endpoints/clips.py`](Backend/api/endpoints/clips.py) |
| `ClipResponse` | `python-pydantic` | [`Backend/api/endpoints/repurpose.py`](Backend/api/endpoints/repurpose.py) |
| `ClipResponse` | `python-pydantic` | [`Backend/api/endpoints/sora_pipeline.py`](Backend/api/endpoints/sora_pipeline.py) |
| `ClipResponse` | `python-pydantic` | [`Backend/api/endpoints/videos.py`](Backend/api/endpoints/videos.py) |
| `ClipResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `ClipRunResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `ClipSummary` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `ClipUpdateRequest` | `python-pydantic` | [`Backend/api/endpoints/clip_management.py`](Backend/api/endpoints/clip_management.py) |
| `ClusterSchema` | `python-pydantic` | [`Backend/services/media_factory/contracts/cluster.py`](Backend/services/media_factory/contracts/cluster.py) |
| `CoerceTransform` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `CollectCommentsRequest` | `python-pydantic` | [`Backend/api/endpoints/platform_publishing.py`](Backend/api/endpoints/platform_publishing.py) |
| `CollectMetricsRequest` | `python-pydantic` | [`Backend/api/endpoints/platform_publishing.py`](Backend/api/endpoints/platform_publishing.py) |
| `CollectionAssetRequest` | `python-pydantic` | [`Backend/api/endpoints/media_assets.py`](Backend/api/endpoints/media_assets.py) |
| `CollectionRequest` | `python-pydantic` | [`Backend/api/endpoints/media_assets.py`](Backend/api/endpoints/media_assets.py) |
| `CommandAck` | `python-pydantic` | [`Backend/control_plane/schemas.py`](Backend/control_plane/schemas.py) |
| `CommandEnvelope` | `python-pydantic` | [`Backend/control_plane/schemas.py`](Backend/control_plane/schemas.py) |
| `CommandTarget` | `python-pydantic` | [`Backend/control_plane/schemas.py`](Backend/control_plane/schemas.py) |
| `Comment` | `python-pydantic` | [`Backend/models/supabase_models.py`](Backend/models/supabase_models.py) |
| `CommentBatch` | `python-pydantic` | [`Backend/api/engagement_autopilot.py`](Backend/api/engagement_autopilot.py) |
| `CommentConfig` | `python-pydantic` | [`Backend/api/comment_automation.py`](Backend/api/comment_automation.py) |
| `CommentCreate` | `python-pydantic` | [`Backend/api/endpoints/comment_engagement.py`](Backend/api/endpoints/comment_engagement.py) |
| `CommentEngagement` | `python-pydantic` | [`Backend/api/comment_automation.py`](Backend/api/comment_automation.py) |
| `CommentRequest` | `python-pydantic` | [`Backend/api/endpoints/instagram_automation.py`](Backend/api/endpoints/instagram_automation.py) |
| `CommentRequest` | `python-pydantic` | [`Backend/api/endpoints/safari_automation.py`](Backend/api/endpoints/safari_automation.py) |
| `CommentResponse` | `python-pydantic` | [`Backend/api/endpoints/comments.py`](Backend/api/endpoints/comments.py) |
| `CommentResponse` | `python-pydantic` | [`Backend/api/endpoints/instagram_automation.py`](Backend/api/endpoints/instagram_automation.py) |
| `CommentsListResponse` | `python-pydantic` | [`Backend/api/endpoints/comments.py`](Backend/api/endpoints/comments.py) |
| `CommentsResponse` | `python-pydantic` | [`Backend/api/endpoints/platform_publishing.py`](Backend/api/endpoints/platform_publishing.py) |
| `ComparisonInsight` | `python-pydantic` | [`Backend/api/analytics_compare.py`](Backend/api/analytics_compare.py) |
| `ComparisonRecommendation` | `python-pydantic` | [`Backend/api/analytics_compare.py`](Backend/api/analytics_compare.py) |
| `ComparisonResult` | `python-pydantic` | [`Backend/api/analytics_compare.py`](Backend/api/analytics_compare.py) |
| `CompetitorAccount` | `python-pydantic` | [`Backend/services/competitor_service.py`](Backend/services/competitor_service.py) |
| `CompetitorAnalysisResponse` | `python-pydantic` | [`Backend/api/endpoints/trending.py`](Backend/api/endpoints/trending.py) |
| `CompetitorContent` | `python-pydantic` | [`Backend/services/competitor_service.py`](Backend/services/competitor_service.py) |
| `CompetitorEmbedRequest` | `python-pydantic` | [`Backend/api/endpoints/semantic_search.py`](Backend/api/endpoints/semantic_search.py) |
| `CompileResult` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `CompositionConfig` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `CompressionPlan` | `python-pydantic` | [`Backend/services/video_generation/runtime_budget.py`](Backend/services/video_generation/runtime_budget.py) |
| `ComputeAllocationsRequest` | `python-pydantic` | [`Backend/api/endpoints/bandit.py`](Backend/api/endpoints/bandit.py) |
| `ConfigUpdate` | `python-pydantic` | [`Backend/api/endpoints/engagement_control.py`](Backend/api/endpoints/engagement_control.py) |
| `ConnectAccountRequest` | `python-pydantic` | [`Backend/api/endpoints/accounts.py`](Backend/api/endpoints/accounts.py) |
| `ConnectedAccount` | `python-pydantic` | [`Backend/api/endpoints/accounts.py`](Backend/api/endpoints/accounts.py) |
| `ConnectedAccountResponse` | `python-pydantic` | [`Backend/api/endpoints/social_accounts.py`](Backend/api/endpoints/social_accounts.py) |
| `ConstraintCreate` | `python-pydantic` | [`Backend/api/endpoints/knowledge_base.py`](Backend/api/endpoints/knowledge_base.py) |
| `ConstraintsConfig` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `ConstraintsConfig` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `ContentAnalysis` | `python-pydantic` | [`Backend/services/ai_content_service.py`](Backend/services/ai_content_service.py) |
| `ContentAnalysis` | `python-pydantic` | [`Backend/services/competitor_analysis_service.py`](Backend/services/competitor_analysis_service.py) |
| `ContentBrief` | `python-pydantic` | [`Backend/services/brief_generator.py`](Backend/services/brief_generator.py) |
| `ContentBrief` | `python-pydantic` | [`Backend/services/intelligence/content_brief.py`](Backend/services/intelligence/content_brief.py) |
| `ContentBriefRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_queries_api.py`](Backend/api/endpoints/trend_queries_api.py) |
| `ContentBriefResponse` | `python-pydantic` | [`Backend/api/endpoints/trend_queries_api.py`](Backend/api/endpoints/trend_queries_api.py) |
| `ContentBriefSchema` | `python-pydantic` | [`Backend/services/media_factory/contracts/content_brief.py`](Backend/services/media_factory/contracts/content_brief.py) |
| `ContentBriefV1` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `ContentConstraints` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `ContentGenRequest` | `python-pydantic` | [`Backend/api/endpoints/adaptive_scheduler.py`](Backend/api/endpoints/adaptive_scheduler.py) |
| `ContentIdeaRequest` | `python-pydantic` | [`Backend/api/endpoints/inbox.py`](Backend/api/endpoints/inbox.py) |
| `ContentIdeaResponse` | `python-pydantic` | [`Backend/api/endpoints/trending.py`](Backend/api/endpoints/trending.py) |
| `ContentItem` | `python-pydantic` | [`Backend/api/content_pipeline.py`](Backend/api/content_pipeline.py) |
| `ContentItemCreate` | `python-pydantic` | [`Backend/api/endpoints/content.py`](Backend/api/endpoints/content.py) |
| `ContentItemCreate` | `python-pydantic` | [`Backend/api/endpoints/content_loop.py`](Backend/api/endpoints/content_loop.py) |
| `ContentMapping` | `python-pydantic` | [`Backend/api/endpoints/social_analytics.py`](Backend/api/endpoints/social_analytics.py) |
| `ContentMetricResponse` | `python-pydantic` | [`Backend/api/endpoints/content_metrics.py`](Backend/api/endpoints/content_metrics.py) |
| `ContentMetricsHistory` | `python-pydantic` | [`Backend/api/content_growth.py`](Backend/api/content_growth.py) |
| `ContentMixRequest` | `python-pydantic` | [`Backend/api/endpoints/content_mix_api.py`](Backend/api/endpoints/content_mix_api.py) |
| `ContentPackRequest` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `ContentPackResponse` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `ContentRollup` | `python-pydantic` | [`Backend/services/analytics_aggregator.py`](Backend/services/analytics_aggregator.py) |
| `ContentRollupResponse` | `python-pydantic` | [`Backend/api/endpoints/content_metrics.py`](Backend/api/endpoints/content_metrics.py) |
| `ContentSlotCreate` | `python-pydantic` | [`Backend/api/endpoints/content_loop.py`](Backend/api/endpoints/content_loop.py) |
| `ContentSuggestionsResponse` | `python-pydantic` | [`Backend/api/endpoints/ai_titles.py`](Backend/api/endpoints/ai_titles.py) |
| `ContentVariant` | `python-pydantic` | [`Backend/connectors/base.py`](Backend/connectors/base.py) |
| `ContentVariantCreate` | `python-pydantic` | [`Backend/api/endpoints/content.py`](Backend/api/endpoints/content.py) |
| `ContentVariation` | `python-pydantic` | [`Backend/api/content_pipeline.py`](Backend/api/content_pipeline.py) |
| `ContextPackRequest` | `python-pydantic` | [`Backend/api/endpoints/sfx_library.py`](Backend/api/endpoints/sfx_library.py) |
| `ContextPackResponse` | `python-pydantic` | [`Backend/api/endpoints/sfx_library.py`](Backend/api/endpoints/sfx_library.py) |
| `ControlSettings` | `python-pydantic` | [`Backend/api/approval_queue.py`](Backend/api/approval_queue.py) |
| `ConversionEventRequest` | `python-pydantic` | [`Backend/api/endpoints/offer_tracking.py`](Backend/api/endpoints/offer_tracking.py) |
| `CopyPlanInputModel` | `python-pydantic` | [`Backend/api/endpoints/content_pipeline.py`](Backend/api/endpoints/content_pipeline.py) |
| `CoverageStats` | `python-pydantic` | [`Backend/api/ai_curation.py`](Backend/api/ai_curation.py) |
| `CrawlConfigRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_intelligence.py`](Backend/api/endpoints/trend_intelligence.py) |
| `CrawlJobResponse` | `python-pydantic` | [`Backend/api/endpoints/trends_api.py`](Backend/api/endpoints/trends_api.py) |
| `CrawlMusicRequest` | `python-pydantic` | [`Backend/api/endpoints/music_crawler.py`](Backend/api/endpoints/music_crawler.py) |
| `CrawlRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_intelligence.py`](Backend/api/endpoints/trend_intelligence.py) |
| `CreateAutoReplyRuleRequest` | `python-pydantic` | [`Backend/api/endpoints/community_inbox.py`](Backend/api/endpoints/community_inbox.py) |
| `CreateBibleRequest` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `CreateBriefFromPromptRequest` | `python-pydantic` | [`Backend/api/explainer_video.py`](Backend/api/explainer_video.py) |
| `CreateBriefFromTopicsRequest` | `python-pydantic` | [`Backend/api/explainer_video.py`](Backend/api/explainer_video.py) |
| `CreateBriefRequest` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `CreateBriefRequest` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `CreateCampaignRequest` | `python-pydantic` | [`Backend/services/creative_testing_pipeline/models.py`](Backend/services/creative_testing_pipeline/models.py) |
| `CreateClipPlanRequest` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `CreateClipPlanRequest` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `CreateClipRequest` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `CreateConstraintsRequest` | `python-pydantic` | [`Backend/api/endpoints/narrative_goals.py`](Backend/api/endpoints/narrative_goals.py) |
| `CreateContactRequest` | `python-pydantic` | [`Backend/api/endpoints/relationship_crm.py`](Backend/api/endpoints/relationship_crm.py) |
| `CreateContentRequest` | `python-pydantic` | [`Backend/api/endpoints/media_creation.py`](Backend/api/endpoints/media_creation.py) |
| `CreateExperiment` | `python-pydantic` | [`Backend/api/endpoints/experiments.py`](Backend/api/endpoints/experiments.py) |
| `CreateGoalRequest` | `python-pydantic` | [`Backend/api/endpoints/narrative_goals.py`](Backend/api/endpoints/narrative_goals.py) |
| `CreateOfferRequest` | `python-pydantic` | [`Backend/api/endpoints/dm_outreach.py`](Backend/api/endpoints/dm_outreach.py) |
| `CreatePillarRequest` | `python-pydantic` | [`Backend/api/endpoints/narrative_goals.py`](Backend/api/endpoints/narrative_goals.py) |
| `CreateProjectRequest` | `python-pydantic` | [`Backend/api/endpoints/media_creation.py`](Backend/api/endpoints/media_creation.py) |
| `CreateProjectRequest` | `python-pydantic` | [`Backend/api/endpoints/sora_pipeline.py`](Backend/api/endpoints/sora_pipeline.py) |
| `CreateProjectRequest` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `CreateProjectRequest` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `CreateResponseTemplateRequest` | `python-pydantic` | [`Backend/api/endpoints/community_inbox.py`](Backend/api/endpoints/community_inbox.py) |
| `CreateScriptRequest` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `CreateScriptRequest` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `CreateTemplateRequest` | `python-pydantic` | [`Backend/api/endpoints/templates.py`](Backend/api/endpoints/templates.py) |
| `CreateTestRequest` | `python-pydantic` | [`Backend/api/ab_testing.py`](Backend/api/ab_testing.py) |
| `CreateTrackedLinkRequest` | `python-pydantic` | [`Backend/api/endpoints/offer_tracking.py`](Backend/api/endpoints/offer_tracking.py) |
| `CreateVariationRequest` | `python-pydantic` | [`Backend/api/endpoints/content_variations.py`](Backend/api/endpoints/content_variations.py) |
| `CreateVideoRequest` | `python-pydantic` | [`Backend/api/blotato_router.py`](Backend/api/blotato_router.py) |
| `CreateVideoRequest` | `python-pydantic` | [`Backend/api/endpoints/video_generation.py`](Backend/api/endpoints/video_generation.py) |
| `CreateVideoRequest` | `python-pydantic` | [`Backend/api/explainer_video.py`](Backend/api/explainer_video.py) |
| `CreateVoiceProfileRequest` | `python-pydantic` | [`Backend/api/endpoints/voice_cloning.py`](Backend/api/endpoints/voice_cloning.py) |
| `Creative` | `python-pydantic` | [`Backend/services/creative_testing_pipeline/models.py`](Backend/services/creative_testing_pipeline/models.py) |
| `CreativeBriefV2` | `python-pydantic` | [`Backend/models/supabase_models.py`](Backend/models/supabase_models.py) |
| `CreativeLineage` | `python-pydantic` | [`Backend/services/creative_testing_pipeline/models.py`](Backend/services/creative_testing_pipeline/models.py) |
| `CrosspostRequest` | `python-pydantic` | [`Backend/api/endpoints/tiktok_repurpose.py`](Backend/api/endpoints/tiktok_repurpose.py) |
| `CueSheet` | `python-pydantic` | [`Backend/services/sfx_library/cue_sheet.py`](Backend/services/sfx_library/cue_sheet.py) |
| `CurateRequest` | `python-pydantic` | [`Backend/api/endpoints/auto_curator.py`](Backend/api/endpoints/auto_curator.py) |
| `CurationRequest` | `python-pydantic` | [`Backend/api/media_processing_db.py`](Backend/api/media_processing_db.py) |
| `CurationRuleRequest` | `python-pydantic` | [`Backend/api/endpoints/auto_curator.py`](Backend/api/endpoints/auto_curator.py) |
| `CustomTrendRequest` | `python-pydantic` | [`Backend/api/endpoints/sora_daily.py`](Backend/api/endpoints/sora_daily.py) |
| `DMRequest` | `python-pydantic` | [`Backend/api/endpoints/tiktok_automation.py`](Backend/api/endpoints/tiktok_automation.py) |
| `DMRequest` | `python-pydantic` | [`Backend/api/endpoints/twitter_automation.py`](Backend/api/endpoints/twitter_automation.py) |
| `DMRequest` | `python-pydantic` | [`Backend/api/endpoints/twitter_posting.py`](Backend/api/endpoints/twitter_posting.py) |
| `DMResponse` | `python-pydantic` | [`Backend/api/endpoints/tiktok_automation.py`](Backend/api/endpoints/tiktok_automation.py) |
| `DMResponse` | `python-pydantic` | [`Backend/api/endpoints/twitter_automation.py`](Backend/api/endpoints/twitter_automation.py) |
| `DMSessionRequest` | `python-pydantic` | [`Backend/api/endpoints/tiktok_automation.py`](Backend/api/endpoints/tiktok_automation.py) |
| `DMSessionRequest` | `python-pydantic` | [`Backend/api/endpoints/twitter_automation.py`](Backend/api/endpoints/twitter_automation.py) |
| `DMSessionResponse` | `python-pydantic` | [`Backend/api/endpoints/tiktok_automation.py`](Backend/api/endpoints/tiktok_automation.py) |
| `DMSessionResponse` | `python-pydantic` | [`Backend/api/endpoints/twitter_automation.py`](Backend/api/endpoints/twitter_automation.py) |
| `DailyPerformanceResponse` | `python-pydantic` | [`Backend/api/endpoints/posting_optimizer_api.py`](Backend/api/endpoints/posting_optimizer_api.py) |
| `DashboardOverview` | `python-pydantic` | [`Backend/api/endpoints/social_analytics.py`](Backend/api/endpoints/social_analytics.py) |
| `DashboardResponse` | `python-pydantic` | [`Backend/api/endpoints/analytics_insights.py`](Backend/api/endpoints/analytics_insights.py) |
| `DataContext` | `python-pydantic` | [`Backend/api/ai_chat.py`](Backend/api/ai_chat.py) |
| `DataSource` | `python-pydantic` | [`Backend/api/ai_chat.py`](Backend/api/ai_chat.py) |
| `DecomposeGoalRequest` | `python-pydantic` | [`Backend/api/endpoints/orchestrator_goals.py`](Backend/api/endpoints/orchestrator_goals.py) |
| `DefaultTransform` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `DeleteRequest` | `python-pydantic` | [`Backend/api/endpoints/duplicate_detection.py`](Backend/api/endpoints/duplicate_detection.py) |
| `DemoVideoRequest` | `python-pydantic` | [`Backend/api/endpoints/sora_pipeline.py`](Backend/api/endpoints/sora_pipeline.py) |
| `DerivativeMediaPlan` | `python-pydantic` | [`Backend/models/supabase_models.py`](Backend/models/supabase_models.py) |
| `DetectRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_flash.py`](Backend/api/endpoints/trend_flash.py) |
| `DiscernmentInputs` | `python-pydantic` | [`Backend/services/video_generation/voice_strategy.py`](Backend/services/video_generation/voice_strategy.py) |
| `DiscoverRequest` | `python-pydantic` | [`Backend/api/endpoints/channel_analyzer.py`](Backend/api/endpoints/channel_analyzer.py) |
| `DiscoverResponse` | `python-pydantic` | [`Backend/api/endpoints/channel_analyzer.py`](Backend/api/endpoints/channel_analyzer.py) |
| `DiscoveryRequest` | `python-pydantic` | [`Backend/api/endpoints/dm_outreach.py`](Backend/api/endpoints/dm_outreach.py) |
| `DiscoveryResponse` | `python-pydantic` | [`Backend/api/endpoints/format_discovery.py`](Backend/api/endpoints/format_discovery.py) |
| `Domain` | `python-pydantic` | [`Backend/services/video_generation/domain_dict.py`](Backend/services/video_generation/domain_dict.py) |
| `DomainDict` | `python-pydantic` | [`Backend/services/video_generation/domain_dict.py`](Backend/services/video_generation/domain_dict.py) |
| `DomainSignals` | `python-pydantic` | [`Backend/services/video_generation/domain_dict.py`](Backend/services/video_generation/domain_dict.py) |
| `DownloadRequest` | `python-pydantic` | [`Backend/api/endpoints/tiktok_repurpose.py`](Backend/api/endpoints/tiktok_repurpose.py) |
| `DownloadResponse` | `python-pydantic` | [`Backend/api/endpoints/content_download.py`](Backend/api/endpoints/content_download.py) |
| `DuckingConfig` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `DuckingPolicy` | `python-pydantic` | [`Backend/services/video_generation/audio_ducking.py`](Backend/services/video_generation/audio_ducking.py) |
| `DuplicateCheckRequest` | `python-pydantic` | [`Backend/api/endpoints/content_guard.py`](Backend/api/endpoints/content_guard.py) |
| `DuplicateCheckResponse` | `python-pydantic` | [`Backend/api/endpoints/content_guard.py`](Backend/api/endpoints/content_guard.py) |
| `DuplicateGroup` | `python-pydantic` | [`Backend/api/ai_curation.py`](Backend/api/ai_curation.py) |
| `DuplicateListResponse` | `python-pydantic` | [`Backend/api/endpoints/duplicate_detection.py`](Backend/api/endpoints/duplicate_detection.py) |
| `DuplicatePairResponse` | `python-pydantic` | [`Backend/api/endpoints/duplicate_detection.py`](Backend/api/endpoints/duplicate_detection.py) |
| `EmailEventRequest` | `python-pydantic` | [`Backend/api/endpoints/email.py`](Backend/api/endpoints/email.py) |
| `EmbedRequest` | `python-pydantic` | [`Backend/api/endpoints/semantic_search.py`](Backend/api/endpoints/semantic_search.py) |
| `EmbeddingResponse` | `python-pydantic` | [`Backend/api/endpoints/semantic_search.py`](Backend/api/endpoints/semantic_search.py) |
| `EmotionConfigRequest` | `python-pydantic` | [`Backend/api/endpoints/tts.py`](Backend/api/endpoints/tts.py) |
| `EnableAutoSleepRequest` | `python-pydantic` | [`Backend/api/endpoints/cpu_monitor.py`](Backend/api/endpoints/cpu_monitor.py) |
| `EngagementCommentRequest` | `python-pydantic` | [`Backend/api/engagement_autopilot.py`](Backend/api/engagement_autopilot.py) |
| `EngagementSessionRequest` | `python-pydantic` | [`Backend/api/endpoints/instagram_automation.py`](Backend/api/endpoints/instagram_automation.py) |
| `EngagementSessionResponse` | `python-pydantic` | [`Backend/api/endpoints/instagram_automation.py`](Backend/api/endpoints/instagram_automation.py) |
| `EnqueueVideoRequest` | `python-pydantic` | [`Backend/api/endpoints/publishing_controls.py`](Backend/api/endpoints/publishing_controls.py) |
| `ErrorResponse` | `python-pydantic` | [`Backend/control_plane/schemas.py`](Backend/control_plane/schemas.py) |
| `EventEnvelope` | `python-pydantic` | [`Backend/control_plane/schemas.py`](Backend/control_plane/schemas.py) |
| `EventHistoryListResponse` | `python-pydantic` | [`Backend/api/endpoints/event_history.py`](Backend/api/endpoints/event_history.py) |
| `EventHistoryResponse` | `python-pydantic` | [`Backend/api/endpoints/event_history.py`](Backend/api/endpoints/event_history.py) |
| `Evidence` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `ExpandedCue` | `python-pydantic` | [`Backend/services/sfx_library/macros.py`](Backend/services/sfx_library/macros.py) |
| `ExperimentVariant` | `python-pydantic` | [`Backend/api/endpoints/experiments.py`](Backend/api/endpoints/experiments.py) |
| `ExportRequest` | `python-pydantic` | [`Backend/api/endpoints/content_ingestion.py`](Backend/api/endpoints/content_ingestion.py) |
| `ExternalVideoSubmission` | `python-pydantic` | [`Backend/api/endpoints/external_scheduling.py`](Backend/api/endpoints/external_scheduling.py) |
| `ExtractRequestModel` | `python-pydantic` | [`Backend/api/endpoints/video_toolkit.py`](Backend/api/endpoints/video_toolkit.py) |
| `ExtractedBeat` | `python-pydantic` | [`Backend/services/sfx_library/beat_extractor.py`](Backend/services/sfx_library/beat_extractor.py) |
| `ExtractionJob` | `python-pydantic` | [`Backend/api/endpoints/clip_extraction.py`](Backend/api/endpoints/clip_extraction.py) |
| `ExtractionOptions` | `python-pydantic` | [`Backend/api/endpoints/clip_extraction.py`](Backend/api/endpoints/clip_extraction.py) |
| `ExtractionRequest` | `python-pydantic` | [`Backend/api/endpoints/clip_extraction.py`](Backend/api/endpoints/clip_extraction.py) |
| `FATEWeights` | `python-pydantic` | [`Backend/api/endpoints/templates.py`](Backend/api/endpoints/templates.py) |
| `FavoriteRequest` | `python-pydantic` | [`Backend/api/endpoints/media_assets.py`](Backend/api/endpoints/media_assets.py) |
| `FetchAudioRequest` | `python-pydantic` | [`Backend/api/endpoints/audio_api.py`](Backend/api/endpoints/audio_api.py) |
| `FetchJobResponse` | `python-pydantic` | [`Backend/api/endpoints/instagram_api.py`](Backend/api/endpoints/instagram_api.py) |
| `FetchMetricsRequest` | `python-pydantic` | [`Backend/api/endpoints/twitter_api.py`](Backend/api/endpoints/twitter_api.py) |
| `FetchRequest` | `python-pydantic` | [`Backend/api/endpoints/social_data_fetcher.py`](Backend/api/endpoints/social_data_fetcher.py) |
| `FetchRequest` | `python-pydantic` | [`Backend/api/endpoints/tiktok_repurpose.py`](Backend/api/endpoints/tiktok_repurpose.py) |
| `FetchStatus` | `python-pydantic` | [`Backend/api/endpoints/social_data_fetcher.py`](Backend/api/endpoints/social_data_fetcher.py) |
| `FixReport` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `FixedEvent` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `ForkStatusResponse` | `python-pydantic` | [`Backend/api/endpoints/template_auto_forker.py`](Backend/api/endpoints/template_auto_forker.py) |
| `ForkTemplateRequest` | `python-pydantic` | [`Backend/api/endpoints/template_auto_forker.py`](Backend/api/endpoints/template_auto_forker.py) |
| `ForkTemplateRequest` | `python-pydantic` | [`Backend/api/endpoints/templates.py`](Backend/api/endpoints/templates.py) |
| `ForkTemplateResponse` | `python-pydantic` | [`Backend/api/endpoints/template_auto_forker.py`](Backend/api/endpoints/template_auto_forker.py) |
| `FormatBlock` | `python-pydantic` | [`Backend/services/video_generation/hybrid_format.py`](Backend/services/video_generation/hybrid_format.py) |
| `FormatCreate` | `python-pydantic` | [`Backend/api/endpoints/formats.py`](Backend/api/endpoints/formats.py) |
| `FormatDefaults` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `FormatDefinition` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `FormatListResponse` | `python-pydantic` | [`Backend/api/endpoints/formats_api.py`](Backend/api/endpoints/formats_api.py) |
| `FormatPackV1` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `FormatResponse` | `python-pydantic` | [`Backend/api/endpoints/formats.py`](Backend/api/endpoints/formats.py) |
| `FormatResponse` | `python-pydantic` | [`Backend/api/endpoints/formats_api.py`](Backend/api/endpoints/formats_api.py) |
| `FormatResponse` | `python-pydantic` | [`Backend/api/endpoints/instagram_trends.py`](Backend/api/endpoints/instagram_trends.py) |
| `FormatResponse` | `python-pydantic` | [`Backend/api/explainer_video.py`](Backend/api/explainer_video.py) |
| `FormatRules` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `FormatRun` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `FormatRunCreate` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `FormatStyle` | `python-pydantic` | [`Backend/services/video_generation/hybrid_format.py`](Backend/services/video_generation/hybrid_format.py) |
| `FormatTraits` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `FormatUpdate` | `python-pydantic` | [`Backend/api/endpoints/formats.py`](Backend/api/endpoints/formats.py) |
| `FrameData` | `python-pydantic` | [`Backend/api/endpoints/viral_analysis.py`](Backend/api/endpoints/viral_analysis.py) |
| `FullCycleRequest` | `python-pydantic` | [`Backend/api/endpoints/adaptive_scheduler.py`](Backend/api/endpoints/adaptive_scheduler.py) |
| `FullPipelineRequest` | `python-pydantic` | [`Backend/api/endpoints/sora_automation.py`](Backend/api/endpoints/sora_automation.py) |
| `FullPipelineRequest` | `python-pydantic` | [`Backend/api/endpoints/tiktok_repurpose.py`](Backend/api/endpoints/tiktok_repurpose.py) |
| `FullPublishRequest` | `python-pydantic` | [`Backend/api/blotato_router.py`](Backend/api/blotato_router.py) |
| `FullPublishResponse` | `python-pydantic` | [`Backend/api/blotato_router.py`](Backend/api/blotato_router.py) |
| `FullPublishWithTrackingRequest` | `python-pydantic` | [`Backend/api/blotato_router.py`](Backend/api/blotato_router.py) |
| `GapAnalysisResult` | `python-pydantic` | [`Backend/services/content_gap_service.py`](Backend/services/content_gap_service.py) |
| `GapTheme` | `python-pydantic` | [`Backend/services/content_gap_service.py`](Backend/services/content_gap_service.py) |
| `GateResult` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `GateRule` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `GenerateAudioRequest` | `python-pydantic` | [`Backend/api/endpoints/voice_cloning.py`](Backend/api/endpoints/voice_cloning.py) |
| `GenerateBriefRequest` | `python-pydantic` | [`Backend/api/endpoints/briefs.py`](Backend/api/endpoints/briefs.py) |
| `GenerateBriefRequest` | `python-pydantic` | [`Backend/api/endpoints/creative_briefs.py`](Backend/api/endpoints/creative_briefs.py) |
| `GenerateCandidatesRequest` | `python-pydantic` | [`Backend/api/endpoints/broll_candidates.py`](Backend/api/endpoints/broll_candidates.py) |
| `GenerateCaptionsRequest` | `python-pydantic` | [`Backend/api/endpoints/analysis.py`](Backend/api/endpoints/analysis.py) |
| `GenerateCharacterRequest` | `python-pydantic` | [`Backend/api/endpoints/characters.py`](Backend/api/endpoints/characters.py) |
| `GenerateContentRequest` | `python-pydantic` | [`Backend/routers/visual_campaign.py`](Backend/routers/visual_campaign.py) |
| `GenerateCopyPlanRequest` | `python-pydantic` | [`Backend/api/endpoints/content_pipeline.py`](Backend/api/endpoints/content_pipeline.py) |
| `GenerateForAllOffersRequest` | `python-pydantic` | [`Backend/api/endpoints/ugc_content.py`](Backend/api/endpoints/ugc_content.py) |
| `GenerateForOfferRequest` | `python-pydantic` | [`Backend/api/endpoints/ugc_content.py`](Backend/api/endpoints/ugc_content.py) |
| `GenerateHashtagsRequest` | `python-pydantic` | [`Backend/api/endpoints/hashtag_generator_api.py`](Backend/api/endpoints/hashtag_generator_api.py) |
| `GenerateHashtagsResponse` | `python-pydantic` | [`Backend/api/endpoints/hashtag_generator_api.py`](Backend/api/endpoints/hashtag_generator_api.py) |
| `GenerateIdeasRequest` | `python-pydantic` | [`Backend/api/endpoints/content_ideas_api.py`](Backend/api/endpoints/content_ideas_api.py) |
| `GeneratePlanRequest` | `python-pydantic` | [`Backend/api/endpoints/content_mix_api.py`](Backend/api/endpoints/content_mix_api.py) |
| `GeneratePromptRequest` | `python-pydantic` | [`Backend/api/endpoints/creative_briefs.py`](Backend/api/endpoints/creative_briefs.py) |
| `GenerateRemotionSpecRequest` | `python-pydantic` | [`Backend/api/endpoints/content_pipeline.py`](Backend/api/endpoints/content_pipeline.py) |
| `GenerateRenderPlanRequest` | `python-pydantic` | [`Backend/api/endpoints/video_generation.py`](Backend/api/endpoints/video_generation.py) |
| `GenerateReportRequest` | `python-pydantic` | [`Backend/api/endpoints/strategy_report_api.py`](Backend/api/endpoints/strategy_report_api.py) |
| `GenerateRequest` | `python-pydantic` | [`Backend/api/comment_automation.py`](Backend/api/comment_automation.py) |
| `GenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/ai_recommendations.py`](Backend/api/endpoints/ai_recommendations.py) |
| `GenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/messages.py`](Backend/api/endpoints/messages.py) |
| `GenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/sora.py`](Backend/api/endpoints/sora.py) |
| `GenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/sora_pipeline.py`](Backend/api/endpoints/sora_pipeline.py) |
| `GenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_flash.py`](Backend/api/endpoints/trend_flash.py) |
| `GenerateRequest` | `python-pydantic` | [`Backend/api/routes/video_formats.py`](Backend/api/routes/video_formats.py) |
| `GenerateScriptsRequest` | `python-pydantic` | [`Backend/api/endpoints/sora_daily.py`](Backend/api/endpoints/sora_daily.py) |
| `GenerateShotPlanRequest` | `python-pydantic` | [`Backend/api/endpoints/video_generation.py`](Backend/api/endpoints/video_generation.py) |
| `GenerateSingleRequest` | `python-pydantic` | [`Backend/api/caption_variants.py`](Backend/api/caption_variants.py) |
| `GenerateStoryIRRequest` | `python-pydantic` | [`Backend/api/endpoints/video_generation.py`](Backend/api/endpoints/video_generation.py) |
| `GenerateSuggestionsRequest` | `python-pydantic` | [`Backend/api/endpoints/ai_titles.py`](Backend/api/endpoints/ai_titles.py) |
| `GenerateSuggestionsRequest` | `python-pydantic` | [`Backend/api/endpoints/reply_suggestions.py`](Backend/api/endpoints/reply_suggestions.py) |
| `GenerateSuggestionsResponse` | `python-pydantic` | [`Backend/api/endpoints/reply_suggestions.py`](Backend/api/endpoints/reply_suggestions.py) |
| `GenerateTweetsRequest` | `python-pydantic` | [`Backend/routers/twitter_campaign.py`](Backend/routers/twitter_campaign.py) |
| `GenerateVariantsRequest` | `python-pydantic` | [`Backend/api/caption_variants.py`](Backend/api/caption_variants.py) |
| `GenerateVariantsRequest` | `python-pydantic` | [`Backend/api/endpoints/characters.py`](Backend/api/endpoints/characters.py) |
| `GenerateVariationsRequest` | `python-pydantic` | [`Backend/api/endpoints/content_variations.py`](Backend/api/endpoints/content_variations.py) |
| `GenerateVariationsRequest` | `python-pydantic` | [`Backend/api/endpoints/hook_library_api.py`](Backend/api/endpoints/hook_library_api.py) |
| `GenerateWeeklyPlanRequest` | `python-pydantic` | [`Backend/api/endpoints/autonomy.py`](Backend/api/endpoints/autonomy.py) |
| `GeneratedComment` | `python-pydantic` | [`Backend/api/comment_automation.py`](Backend/api/comment_automation.py) |
| `GeneratedContent` | `python-pydantic` | [`Backend/services/ai_content_service.py`](Backend/services/ai_content_service.py) |
| `GeneratedMessage` | `python-pydantic` | [`Backend/services/message_engine.py`](Backend/services/message_engine.py) |
| `GenerationProgressResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `GenerationRequest` | `python-pydantic` | [`Backend/services/content_generation_pipeline.py`](Backend/services/content_generation_pipeline.py) |
| `GenerationResult` | `python-pydantic` | [`Backend/services/content_generation_pipeline.py`](Backend/services/content_generation_pipeline.py) |
| `GenerationStatusResponse` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `GitPushRequestModel` | `python-pydantic` | [`Backend/api/endpoints/video_toolkit.py`](Backend/api/endpoints/video_toolkit.py) |
| `GoalCreate` | `python-pydantic` | [`Backend/api/endpoints/goals.py`](Backend/api/endpoints/goals.py) |
| `GoalResponse` | `python-pydantic` | [`Backend/api/endpoints/goals.py`](Backend/api/endpoints/goals.py) |
| `GoalUpdate` | `python-pydantic` | [`Backend/api/endpoints/goals.py`](Backend/api/endpoints/goals.py) |
| `GrowthMetrics` | `python-pydantic` | [`Backend/services/realtime_metrics.py`](Backend/services/realtime_metrics.py) |
| `GrowthSummary` | `python-pydantic` | [`Backend/api/content_growth.py`](Backend/api/content_growth.py) |
| `HFTTSConfig` | `python-pydantic` | [`Backend/services/video_generation/hf_tts_provider.py`](Backend/services/video_generation/hf_tts_provider.py) |
| `HashtagAnalysisResponse` | `python-pydantic` | [`Backend/api/endpoints/hashtag_generator_api.py`](Backend/api/endpoints/hashtag_generator_api.py) |
| `HashtagInsightsResponse` | `python-pydantic` | [`Backend/api/endpoints/trending.py`](Backend/api/endpoints/trending.py) |
| `HashtagRequest` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `HashtagResponse` | `python-pydantic` | [`Backend/api/endpoints/hashtag_generator_api.py`](Backend/api/endpoints/hashtag_generator_api.py) |
| `HashtagResponse` | `python-pydantic` | [`Backend/api/endpoints/instagram_api.py`](Backend/api/endpoints/instagram_api.py) |
| `HashtagResponse` | `python-pydantic` | [`Backend/api/endpoints/instagram_trends.py`](Backend/api/endpoints/instagram_trends.py) |
| `HashtagResponse` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `HashtagResult` | `python-pydantic` | [`Backend/api/endpoints/trend_queries_api.py`](Backend/api/endpoints/trend_queries_api.py) |
| `HealthCheckResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `HealthResponse` | `python-pydantic` | [`Backend/control_plane/schemas.py`](Backend/control_plane/schemas.py) |
| `HighlightRequest` | `python-pydantic` | [`Backend/api/endpoints/highlights.py`](Backend/api/endpoints/highlights.py) |
| `HighlightResponse` | `python-pydantic` | [`Backend/api/endpoints/highlights.py`](Backend/api/endpoints/highlights.py) |
| `HookLeaderboardResponse` | `python-pydantic` | [`Backend/api/endpoints/trend_queries_api.py`](Backend/api/endpoints/trend_queries_api.py) |
| `HookResult` | `python-pydantic` | [`Backend/api/endpoints/trend_queries_api.py`](Backend/api/endpoints/trend_queries_api.py) |
| `HourlyPerformanceResponse` | `python-pydantic` | [`Backend/api/endpoints/posting_optimizer_api.py`](Backend/api/endpoints/posting_optimizer_api.py) |
| `HttpApiSource` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `HybridFormat` | `python-pydantic` | [`Backend/services/video_generation/hybrid_format.py`](Backend/services/video_generation/hybrid_format.py) |
| `ICPCreate` | `python-pydantic` | [`Backend/api/endpoints/icps.py`](Backend/api/endpoints/icps.py) |
| `ICPResponse` | `python-pydantic` | [`Backend/api/endpoints/icps.py`](Backend/api/endpoints/icps.py) |
| `ICPUpdate` | `python-pydantic` | [`Backend/api/endpoints/icps.py`](Backend/api/endpoints/icps.py) |
| `IdentifyUserRequest` | `python-pydantic` | [`Backend/api/endpoints/user_tracking.py`](Backend/api/endpoints/user_tracking.py) |
| `ImageAnalysisResult` | `python-pydantic` | [`Backend/api/image_analysis.py`](Backend/api/image_analysis.py) |
| `ImpactAnalysis` | `python-pydantic` | [`Backend/api/comment_automation.py`](Backend/api/comment_automation.py) |
| `ImportFilter` | `python-pydantic` | [`Backend/api/endpoints/android_import_api.py`](Backend/api/endpoints/android_import_api.py) |
| `ImportFilter` | `python-pydantic` | [`Backend/api/endpoints/ios_import_api.py`](Backend/api/endpoints/ios_import_api.py) |
| `ImportTrackRequest` | `python-pydantic` | [`Backend/api/endpoints/music_library.py`](Backend/api/endpoints/music_library.py) |
| `InboxMessageResponse` | `python-pydantic` | [`Backend/api/endpoints/community_inbox.py`](Backend/api/endpoints/community_inbox.py) |
| `InfluencerReportResponse` | `python-pydantic` | [`Backend/api/endpoints/influencer_analysis.py`](Backend/api/endpoints/influencer_analysis.py) |
| `IngestCommentRequest` | `python-pydantic` | [`Backend/api/endpoints/people.py`](Backend/api/endpoints/people.py) |
| `IngestPendingRequest` | `python-pydantic` | [`Backend/api/endpoints/content_sourcing.py`](Backend/api/endpoints/content_sourcing.py) |
| `IngestRequest` | `python-pydantic` | [`Backend/api/endpoints/content_ingestion.py`](Backend/api/endpoints/content_ingestion.py) |
| `IngestRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_intelligence.py`](Backend/api/endpoints/trend_intelligence.py) |
| `IngestStatsResponse` | `python-pydantic` | [`Backend/api/media_processing_db.py`](Backend/api/media_processing_db.py) |
| `IngestionConfig` | `python-pydantic` | [`Backend/api/endpoints/ingestion.py`](Backend/api/endpoints/ingestion.py) |
| `IngestionStatus` | `python-pydantic` | [`Backend/api/endpoints/ingestion.py`](Backend/api/endpoints/ingestion.py) |
| `InsightCreate` | `python-pydantic` | [`Backend/api/endpoints/content_loop.py`](Backend/api/endpoints/content_loop.py) |
| `InsightResponse` | `python-pydantic` | [`Backend/api/endpoints/analytics_insights.py`](Backend/api/endpoints/analytics_insights.py) |
| `InsightResponse` | `python-pydantic` | [`Backend/api/endpoints/channel_analyzer.py`](Backend/api/endpoints/channel_analyzer.py) |
| `InstagramPostInfo` | `python-pydantic` | [`Backend/api/posted_media.py`](Backend/api/posted_media.py) |
| `InstagramSyncRequest` | `python-pydantic` | [`Backend/api/posted_media.py`](Backend/api/posted_media.py) |
| `InstagramSyncResponse` | `python-pydantic` | [`Backend/api/posted_media.py`](Backend/api/posted_media.py) |
| `JobEventsResponse` | `python-pydantic` | [`Backend/control_plane/schemas.py`](Backend/control_plane/schemas.py) |
| `JobListResponse` | `python-pydantic` | [`Backend/control_plane/schemas.py`](Backend/control_plane/schemas.py) |
| `JobRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_intelligence.py`](Backend/api/endpoints/trend_intelligence.py) |
| `JobResponse` | `python-pydantic` | [`Backend/api/endpoints/jobs.py`](Backend/api/endpoints/jobs.py) |
| `JobResponse` | `python-pydantic` | [`Backend/api/explainer_video.py`](Backend/api/explainer_video.py) |
| `JobState` | `python-pydantic` | [`Backend/control_plane/schemas.py`](Backend/control_plane/schemas.py) |
| `JobStatusResponse` | `python-pydantic` | [`Backend/api/media_processing.py`](Backend/api/media_processing.py) |
| `LLMSfxResult` | `python-pydantic` | [`Backend/services/sfx_library/llm_integration.py`](Backend/services/sfx_library/llm_integration.py) |
| `LayerRequest` | `python-pydantic` | [`Backend/api/endpoints/remotion.py`](Backend/api/endpoints/remotion.py) |
| `LayerSchema` | `python-pydantic` | [`Backend/services/media_factory/contracts/timeline.py`](Backend/services/media_factory/contracts/timeline.py) |
| `LayerV2` | `python-pydantic` | [`Backend/services/video_generation/render_plan_v2.py`](Backend/services/video_generation/render_plan_v2.py) |
| `LineGraphData` | `python-pydantic` | [`Backend/api/metrics_scheduler_api.py`](Backend/api/metrics_scheduler_api.py) |
| `LineGraphDataPoint` | `python-pydantic` | [`Backend/api/metrics_scheduler_api.py`](Backend/api/metrics_scheduler_api.py) |
| `LiveAnalyticsResponse` | `python-pydantic` | [`Backend/api/endpoints/social_accounts.py`](Backend/api/endpoints/social_accounts.py) |
| `LocalLibrarySource` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `LogValueRequest` | `python-pydantic` | [`Backend/api/endpoints/relationship_crm.py`](Backend/api/endpoints/relationship_crm.py) |
| `MacroCandidate` | `python-pydantic` | [`Backend/services/sfx_library/macros.py`](Backend/services/sfx_library/macros.py) |
| `MacroCue` | `python-pydantic` | [`Backend/services/sfx_library/macros.py`](Backend/services/sfx_library/macros.py) |
| `MacroCueSheet` | `python-pydantic` | [`Backend/services/sfx_library/macros.py`](Backend/services/sfx_library/macros.py) |
| `MapTransform` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `MarkPostedRequest` | `python-pydantic` | [`Backend/api/endpoints/posted_content_matcher.py`](Backend/api/endpoints/posted_content_matcher.py) |
| `MarkUsedRequest` | `python-pydantic` | [`Backend/api/endpoints/content_variations.py`](Backend/api/endpoints/content_variations.py) |
| `MatchMusicRequest` | `python-pydantic` | [`Backend/api/endpoints/music_library.py`](Backend/api/endpoints/music_library.py) |
| `MatchRequest` | `python-pydantic` | [`Backend/api/endpoints/posted_content_matcher.py`](Backend/api/endpoints/posted_content_matcher.py) |
| `MatchVideoRequest` | `python-pydantic` | [`Backend/api/endpoints/platform_matching.py`](Backend/api/endpoints/platform_matching.py) |
| `MattingConfigRequest` | `python-pydantic` | [`Backend/api/endpoints/matting.py`](Backend/api/endpoints/matting.py) |
| `MattingProvider` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `MattingRequest` | `python-pydantic` | [`Backend/api/endpoints/matting.py`](Backend/api/endpoints/matting.py) |
| `MattingResponse` | `python-pydantic` | [`Backend/api/endpoints/matting.py`](Backend/api/endpoints/matting.py) |
| `MediaAnalysis` | `python-pydantic` | [`Backend/models/supabase_models.py`](Backend/models/supabase_models.py) |
| `MediaAsset` | `python-pydantic` | [`Backend/models/supabase_models.py`](Backend/models/supabase_models.py) |
| `MediaDetailResponse` | `python-pydantic` | [`Backend/api/media_processing_db.py`](Backend/api/media_processing_db.py) |
| `MediaInfo` | `python-pydantic` | [`Backend/services/video_generation/media_probe.py`](Backend/services/video_generation/media_probe.py) |
| `MediaItemResponse` | `python-pydantic` | [`Backend/api/endpoints/instagram_api.py`](Backend/api/endpoints/instagram_api.py) |
| `MediaPageResponse` | `python-pydantic` | [`Backend/api/endpoints/instagram_api.py`](Backend/api/endpoints/instagram_api.py) |
| `MediaStatusResponse` | `python-pydantic` | [`Backend/api/media_processing.py`](Backend/api/media_processing.py) |
| `MediaStatusResponse` | `python-pydantic` | [`Backend/api/media_processing_db.py`](Backend/api/media_processing_db.py) |
| `MediaTiming` | `python-pydantic` | [`Backend/services/video_generation/media_probe.py`](Backend/services/video_generation/media_probe.py) |
| `MediaUploadResponse` | `python-pydantic` | [`Backend/api/blotato_router.py`](Backend/api/blotato_router.py) |
| `MediaUploadResponse` | `python-pydantic` | [`Backend/api/media_processing.py`](Backend/api/media_processing.py) |
| `MemeItem` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `MessageFilters` | `python-pydantic` | [`Backend/api/endpoints/inbox.py`](Backend/api/endpoints/inbox.py) |
| `MessageGoal` | `python-pydantic` | [`Backend/services/message_engine.py`](Backend/services/message_engine.py) |
| `MetricComparison` | `python-pydantic` | [`Backend/services/benchmark_service.py`](Backend/services/benchmark_service.py) |
| `MetricSnapshot` | `python-pydantic` | [`Backend/api/content_growth.py`](Backend/api/content_growth.py) |
| `MetricSnapshotCreate` | `python-pydantic` | [`Backend/api/endpoints/content_loop.py`](Backend/api/endpoints/content_loop.py) |
| `MetricsResponse` | `python-pydantic` | [`Backend/api/endpoints/platform_publishing.py`](Backend/api/endpoints/platform_publishing.py) |
| `MetricsResult` | `python-pydantic` | [`Backend/api/rapidapi_metrics.py`](Backend/api/rapidapi_metrics.py) |
| `MonitorStartRequest` | `python-pydantic` | [`Backend/api/endpoints/content_sourcing.py`](Backend/api/endpoints/content_sourcing.py) |
| `MultiMetricLineGraph` | `python-pydantic` | [`Backend/api/metrics_scheduler_api.py`](Backend/api/metrics_scheduler_api.py) |
| `MultiPartRequest` | `python-pydantic` | [`Backend/api/endpoints/sora_automation.py`](Backend/api/endpoints/sora_automation.py) |
| `MultiPlatformPostRequest` | `python-pydantic` | [`Backend/api/blotato_router.py`](Backend/api/blotato_router.py) |
| `MusicAudioEvent` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `MusicProvider` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `MusicRequest` | `python-pydantic` | [`Backend/api/endpoints/music.py`](Backend/api/endpoints/music.py) |
| `MusicResponse` | `python-pydantic` | [`Backend/api/endpoints/music.py`](Backend/api/endpoints/music.py) |
| `MusicSearchCriteriaRequest` | `python-pydantic` | [`Backend/api/endpoints/music.py`](Backend/api/endpoints/music.py) |
| `MusicSuggestionRequest` | `python-pydantic` | [`Backend/api/endpoints/music_matching.py`](Backend/api/endpoints/music_matching.py) |
| `MusicSuggestionResponse` | `python-pydantic` | [`Backend/api/endpoints/music_matching.py`](Backend/api/endpoints/music_matching.py) |
| `NarrationAsset` | `python-pydantic` | [`Backend/services/video_generation/vo_stitcher.py`](Backend/services/video_generation/vo_stitcher.py) |
| `NarrationConfigSchema` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `NarrationCue` | `python-pydantic` | [`Backend/services/video_generation/audio_ducking.py`](Backend/services/video_generation/audio_ducking.py) |
| `NarrationCue` | `python-pydantic` | [`Backend/services/video_generation/vo_stitcher.py`](Backend/services/video_generation/vo_stitcher.py) |
| `NarrativeGoal` | `python-pydantic` | [`Backend/api/endpoints/narrative_builder.py`](Backend/api/endpoints/narrative_builder.py) |
| `NarrativeGoalCreate` | `python-pydantic` | [`Backend/api/endpoints/narrative_builder.py`](Backend/api/endpoints/narrative_builder.py) |
| `NarratorConfig` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `NarratorConfig` | `python-pydantic` | [`Backend/services/video_generation/voice_engine.py`](Backend/services/video_generation/voice_engine.py) |
| `NarratorConfig` | `python-pydantic` | [`Backend/services/video_generation/voice_strategy.py`](Backend/services/video_generation/voice_strategy.py) |
| `NicheConfig` | `python-pydantic` | [`Backend/api/comment_automation.py`](Backend/api/comment_automation.py) |
| `NicheConfigUpdate` | `python-pydantic` | [`Backend/api/trend_detection.py`](Backend/api/trend_detection.py) |
| `NicheCreate` | `python-pydantic` | [`Backend/api/endpoints/trend_queries_api.py`](Backend/api/endpoints/trend_queries_api.py) |
| `NicheData` | `python-pydantic` | [`Backend/services/niche_search_service.py`](Backend/services/niche_search_service.py) |
| `NicheResponse` | `python-pydantic` | [`Backend/api/endpoints/trend_queries_api.py`](Backend/api/endpoints/trend_queries_api.py) |
| `NicheSoundsRequest` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `NormalizeConfig` | `python-pydantic` | [`Backend/services/video_generation/duration_normalizer.py`](Backend/services/video_generation/duration_normalizer.py) |
| `ObjectDetection` | `python-pydantic` | [`Backend/api/image_analysis.py`](Backend/api/image_analysis.py) |
| `OfferCreate` | `python-pydantic` | [`Backend/api/endpoints/offers.py`](Backend/api/endpoints/offers.py) |
| `OfferResponse` | `python-pydantic` | [`Backend/api/endpoints/offers.py`](Backend/api/endpoints/offers.py) |
| `OfferUpdate` | `python-pydantic` | [`Backend/api/endpoints/offers.py`](Backend/api/endpoints/offers.py) |
| `OnScreenText` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `OneClickRenderRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_intelligence.py`](Backend/api/endpoints/trend_intelligence.py) |
| `OpportunityCreate` | `python-pydantic` | [`Backend/api/endpoints/trend_opportunities.py`](Backend/api/endpoints/trend_opportunities.py) |
| `OpportunityScore` | `python-pydantic` | [`Backend/api/endpoints/trend_opportunities.py`](Backend/api/endpoints/trend_opportunities.py) |
| `OptimizePromptRequest` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `OptimizePromptRequest` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `OptimizePromptResponse` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `OptimizePromptResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `OrganicPost` | `python-pydantic` | [`Backend/services/creative_testing_pipeline/models.py`](Backend/services/creative_testing_pipeline/models.py) |
| `OutlineLine` | `python-pydantic` | [`Backend/services/video_generation/duration_normalizer.py`](Backend/services/video_generation/duration_normalizer.py) |
| `OverlapTheme` | `python-pydantic` | [`Backend/services/content_gap_service.py`](Backend/services/content_gap_service.py) |
| `OverlayPreset` | `python-pydantic` | [`Backend/services/video_generation/render_plan_v2.py`](Backend/services/video_generation/render_plan_v2.py) |
| `OverlayRules` | `python-pydantic` | [`Backend/services/video_generation/render_plan_v2.py`](Backend/services/video_generation/render_plan_v2.py) |
| `PacingConfig` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `PacingConfig` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `PerformanceLog` | `python-pydantic` | [`Backend/services/creative_testing_pipeline/models.py`](Backend/services/creative_testing_pipeline/models.py) |
| `PerformanceReviewResponse` | `python-pydantic` | [`Backend/api/endpoints/review.py`](Backend/api/endpoints/review.py) |
| `PerformanceScoreResponse` | `python-pydantic` | [`Backend/api/endpoints/post_tracking.py`](Backend/api/endpoints/post_tracking.py) |
| `PersonAnalysis` | `python-pydantic` | [`Backend/api/image_analysis.py`](Backend/api/image_analysis.py) |
| `PersonContext` | `python-pydantic` | [`Backend/services/message_engine.py`](Backend/services/message_engine.py) |
| `PersonInsightResponse` | `python-pydantic` | [`Backend/api/endpoints/people.py`](Backend/api/endpoints/people.py) |
| `PersonResponse` | `python-pydantic` | [`Backend/api/endpoints/people.py`](Backend/api/endpoints/people.py) |
| `PerspectiveResult` | `python-pydantic` | [`Backend/services/video_generation/perspective_enforcer.py`](Backend/services/video_generation/perspective_enforcer.py) |
| `PickTransform` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `PillarCreate` | `python-pydantic` | [`Backend/api/endpoints/narrative_builder.py`](Backend/api/endpoints/narrative_builder.py) |
| `PipelineConfig` | `python-pydantic` | [`Backend/services/video_generation/pipeline_orchestrator.py`](Backend/services/video_generation/pipeline_orchestrator.py) |
| `PipelineDashboard` | `python-pydantic` | [`Backend/services/creative_testing_pipeline/models.py`](Backend/services/creative_testing_pipeline/models.py) |
| `PipelineExecuteRequest` | `python-pydantic` | [`Backend/api/endpoints/pipeline.py`](Backend/api/endpoints/pipeline.py) |
| `PipelineExecuteRequest` | `python-pydantic` | [`Backend/api/endpoints/video_pipeline.py`](Backend/api/endpoints/video_pipeline.py) |
| `PipelineExecuteResponse` | `python-pydantic` | [`Backend/api/endpoints/pipeline.py`](Backend/api/endpoints/pipeline.py) |
| `PipelineExecuteResponse` | `python-pydantic` | [`Backend/api/endpoints/video_pipeline.py`](Backend/api/endpoints/video_pipeline.py) |
| `PipelineListItem` | `python-pydantic` | [`Backend/api/endpoints/orchestrator.py`](Backend/api/endpoints/orchestrator.py) |
| `PipelinePreviewRequest` | `python-pydantic` | [`Backend/api/endpoints/video_pipeline.py`](Backend/api/endpoints/video_pipeline.py) |
| `PipelinePreviewResponse` | `python-pydantic` | [`Backend/api/endpoints/video_pipeline.py`](Backend/api/endpoints/video_pipeline.py) |
| `PipelineRequest` | `python-pydantic` | [`Backend/api/endpoints/sora.py`](Backend/api/endpoints/sora.py) |
| `PipelineRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_intelligence.py`](Backend/api/endpoints/trend_intelligence.py) |
| `PipelineResponse` | `python-pydantic` | [`Backend/api/endpoints/tiktok_repurpose.py`](Backend/api/endpoints/tiktok_repurpose.py) |
| `PipelineResult` | `python-pydantic` | [`Backend/services/video_generation/pipeline_orchestrator.py`](Backend/services/video_generation/pipeline_orchestrator.py) |
| `PipelineStatusResponse` | `python-pydantic` | [`Backend/api/endpoints/orchestrator.py`](Backend/api/endpoints/orchestrator.py) |
| `PipelineStep` | `python-pydantic` | [`Backend/services/video_generation/pipeline_orchestrator.py`](Backend/services/video_generation/pipeline_orchestrator.py) |
| `PipelineVariantsRequest` | `python-pydantic` | [`Backend/api/endpoints/orchestrator_goals.py`](Backend/api/endpoints/orchestrator_goals.py) |
| `PlannedShot` | `python-pydantic` | [`Backend/services/video_generation/auto_shot_planner.py`](Backend/services/video_generation/auto_shot_planner.py) |
| `PlateUsage` | `python-pydantic` | [`Backend/services/video_generation/plate_manager.py`](Backend/services/video_generation/plate_manager.py) |
| `PlateVariantPlan` | `python-pydantic` | [`Backend/services/video_generation/plate_manager.py`](Backend/services/video_generation/plate_manager.py) |
| `PlatformAssignment` | `python-pydantic` | [`Backend/api/content_pipeline.py`](Backend/api/content_pipeline.py) |
| `PlatformComment` | `python-pydantic` | [`Backend/services/rapidapi_comments_service.py`](Backend/services/rapidapi_comments_service.py) |
| `PlatformConfig` | `python-pydantic` | [`Backend/api/comment_automation.py`](Backend/api/comment_automation.py) |
| `PlatformConfigSchema` | `python-pydantic` | [`Backend/services/media_factory/contracts/publish_job.py`](Backend/services/media_factory/contracts/publish_job.py) |
| `PlatformConfigUpdate` | `python-pydantic` | [`Backend/api/metrics_scheduler_api.py`](Backend/api/metrics_scheduler_api.py) |
| `PlatformConstraints` | `python-pydantic` | [`Backend/services/qa_gate_service.py`](Backend/services/qa_gate_service.py) |
| `PlatformDimensionsResponse` | `python-pydantic` | [`Backend/api/endpoints/thumbnails.py`](Backend/api/endpoints/thumbnails.py) |
| `PlatformLimitResponse` | `python-pydantic` | [`Backend/api/endpoints/prompt_settings.py`](Backend/api/endpoints/prompt_settings.py) |
| `PlatformMatchResponse` | `python-pydantic` | [`Backend/api/endpoints/platform_matching.py`](Backend/api/endpoints/platform_matching.py) |
| `PlatformMetricSnapshot` | `python-pydantic` | [`Backend/connectors/base.py`](Backend/connectors/base.py) |
| `PlatformMetrics` | `python-pydantic` | [`Backend/api/endpoints/social_analytics.py`](Backend/api/endpoints/social_analytics.py) |
| `PlatformMetrics` | `python-pydantic` | [`Backend/services/analytics_aggregator.py`](Backend/services/analytics_aggregator.py) |
| `PlatformMetricsResponse` | `python-pydantic` | [`Backend/api/endpoints/multi_platform_analytics.py`](Backend/api/endpoints/multi_platform_analytics.py) |
| `PlatformReportResponse` | `python-pydantic` | [`Backend/api/endpoints/offer_tracking.py`](Backend/api/endpoints/offer_tracking.py) |
| `PlatformSummary` | `python-pydantic` | [`Backend/api/endpoints/social_accounts.py`](Backend/api/endpoints/social_accounts.py) |
| `PlaybookCreate` | `python-pydantic` | [`Backend/api/endpoints/knowledge_base.py`](Backend/api/endpoints/knowledge_base.py) |
| `PlaybookRuleCreate` | `python-pydantic` | [`Backend/api/endpoints/content_loop.py`](Backend/api/endpoints/content_loop.py) |
| `PolicyConfig` | `python-pydantic` | [`Backend/services/sfx_library/macro_policy.py`](Backend/services/sfx_library/macro_policy.py) |
| `PollRequest` | `python-pydantic` | [`Backend/api/endpoints/twitter_posting.py`](Backend/api/endpoints/twitter_posting.py) |
| `PopulateRequest` | `python-pydantic` | [`Backend/api/endpoints/data_orchestrator.py`](Backend/api/endpoints/data_orchestrator.py) |
| `PostAnalyzeRequest` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `PostDetailResponse` | `python-pydantic` | [`Backend/api/endpoints/platform_publishing.py`](Backend/api/endpoints/platform_publishing.py) |
| `PostMetrics` | `python-pydantic` | [`Backend/services/realtime_metrics.py`](Backend/services/realtime_metrics.py) |
| `PostPerformanceResponse` | `python-pydantic` | [`Backend/api/endpoints/analytics_insights.py`](Backend/api/endpoints/analytics_insights.py) |
| `PostRecordRequest` | `python-pydantic` | [`Backend/api/endpoints/posted_content.py`](Backend/api/endpoints/posted_content.py) |
| `PostResponse` | `python-pydantic` | [`Backend/api/blotato_router.py`](Backend/api/blotato_router.py) |
| `PostResponse` | `python-pydantic` | [`Backend/api/endpoints/publishing.py`](Backend/api/endpoints/publishing.py) |
| `PostScoreUpdateRequest` | `python-pydantic` | [`Backend/api/media_processing_db.py`](Backend/api/media_processing_db.py) |
| `PostSocialScoreResponse` | `python-pydantic` | [`Backend/api/endpoints/post_social_score.py`](Backend/api/endpoints/post_social_score.py) |
| `PostTrackingStatusResponse` | `python-pydantic` | [`Backend/api/endpoints/post_tracking.py`](Backend/api/endpoints/post_tracking.py) |
| `PostWithContent` | `python-pydantic` | [`Backend/api/endpoints/social_analytics.py`](Backend/api/endpoints/social_analytics.py) |
| `PostedContentItem` | `python-pydantic` | [`Backend/api/endpoints/posted_content.py`](Backend/api/endpoints/posted_content.py) |
| `PostedContentResponse` | `python-pydantic` | [`Backend/api/endpoints/posted_content.py`](Backend/api/endpoints/posted_content.py) |
| `PostedMediaItem` | `python-pydantic` | [`Backend/api/posted_media.py`](Backend/api/posted_media.py) |
| `PostedMediaResponse` | `python-pydantic` | [`Backend/api/posted_media.py`](Backend/api/posted_media.py) |
| `PostedMediaStats` | `python-pydantic` | [`Backend/api/posted_media.py`](Backend/api/posted_media.py) |
| `PostingCreate` | `python-pydantic` | [`Backend/api/endpoints/content_loop.py`](Backend/api/endpoints/content_loop.py) |
| `PostingMetrics` | `python-pydantic` | [`Backend/models/supabase_models.py`](Backend/models/supabase_models.py) |
| `PostingSchedule` | `python-pydantic` | [`Backend/models/supabase_models.py`](Backend/models/supabase_models.py) |
| `PostprocessHints` | `python-pydantic` | [`Backend/services/video_generation/shot_types.py`](Backend/services/video_generation/shot_types.py) |
| `PriorityRequest` | `python-pydantic` | [`Backend/api/endpoints/publishing_controls.py`](Backend/api/endpoints/publishing_controls.py) |
| `ProcessResult` | `python-pydantic` | [`Backend/api/endpoints/post_scheduler_api.py`](Backend/api/endpoints/post_scheduler_api.py) |
| `ProcessResultResponse` | `python-pydantic` | [`Backend/api/endpoints/repurpose.py`](Backend/api/endpoints/repurpose.py) |
| `ProcessVideoRequest` | `python-pydantic` | [`Backend/api/endpoints/repurpose.py`](Backend/api/endpoints/repurpose.py) |
| `ProcessVideoRequest` | `python-pydantic` | [`Backend/api/endpoints/youtube_automation.py`](Backend/api/endpoints/youtube_automation.py) |
| `ProduceVideoRequest` | `python-pydantic` | [`Backend/api/endpoints/broll_producer.py`](Backend/api/endpoints/broll_producer.py) |
| `ProduceVideoResponse` | `python-pydantic` | [`Backend/api/endpoints/broll_producer.py`](Backend/api/endpoints/broll_producer.py) |
| `ProductDataRequest` | `python-pydantic` | [`Backend/api/endpoints/creative_briefs.py`](Backend/api/endpoints/creative_briefs.py) |
| `ProfileMetrics` | `python-pydantic` | [`Backend/services/realtime_metrics.py`](Backend/services/realtime_metrics.py) |
| `ProfileResponse` | `python-pydantic` | [`Backend/api/endpoints/instagram_api.py`](Backend/api/endpoints/instagram_api.py) |
| `ProjectResponse` | `python-pydantic` | [`Backend/api/endpoints/sora_pipeline.py`](Backend/api/endpoints/sora_pipeline.py) |
| `ProjectResponse` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `ProjectResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `PromptResponse` | `python-pydantic` | [`Backend/api/endpoints/creative_briefs.py`](Backend/api/endpoints/creative_briefs.py) |
| `PromptRun` | `python-pydantic` | [`Backend/services/content_generation_pipeline.py`](Backend/services/content_generation_pipeline.py) |
| `PromptSettingsUpdate` | `python-pydantic` | [`Backend/api/endpoints/prompt_settings.py`](Backend/api/endpoints/prompt_settings.py) |
| `ProviderConfig` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `ProviderHintsSchema` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `ProviderInfo` | `python-pydantic` | [`Backend/api/endpoints/video_generation.py`](Backend/api/endpoints/video_generation.py) |
| `ProviderReferenceSchema` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `PublicationAttemptRequest` | `python-pydantic` | [`Backend/api/control_plane_publications.py`](Backend/api/control_plane_publications.py) |
| `PublishJobSchema` | `python-pydantic` | [`Backend/services/media_factory/contracts/publish_job.py`](Backend/services/media_factory/contracts/publish_job.py) |
| `PublishNowRequest` | `python-pydantic` | [`Backend/api/endpoints/schedule.py`](Backend/api/endpoints/schedule.py) |
| `PublishPostRequest` | `python-pydantic` | [`Backend/api/blotato_router.py`](Backend/api/blotato_router.py) |
| `PublishRequest` | `python-pydantic` | [`Backend/services/platform_publishers.py`](Backend/services/platform_publishers.py) |
| `PublishResponse` | `python-pydantic` | [`Backend/api/endpoints/platform_publishing.py`](Backend/api/endpoints/platform_publishing.py) |
| `PublishResponse` | `python-pydantic` | [`Backend/api/endpoints/twitter_api.py`](Backend/api/endpoints/twitter_api.py) |
| `PublishResult` | `python-pydantic` | [`Backend/services/platform_publishers.py`](Backend/services/platform_publishers.py) |
| `PublishThreadRequest` | `python-pydantic` | [`Backend/api/endpoints/twitter_api.py`](Backend/api/endpoints/twitter_api.py) |
| `PublishTweetRequest` | `python-pydantic` | [`Backend/api/endpoints/twitter_api.py`](Backend/api/endpoints/twitter_api.py) |
| `PublishVideoRequest` | `python-pydantic` | [`Backend/api/endpoints/platform_publishing.py`](Backend/api/endpoints/platform_publishing.py) |
| `QACheckRequest` | `python-pydantic` | [`Backend/api/endpoints/qa_gate.py`](Backend/api/endpoints/qa_gate.py) |
| `QAGateRequest` | `python-pydantic` | [`Backend/api/endpoints/sfx_library.py`](Backend/api/endpoints/sfx_library.py) |
| `QAIssue` | `python-pydantic` | [`Backend/services/qa_gate_service.py`](Backend/services/qa_gate_service.py) |
| `QAResult` | `python-pydantic` | [`Backend/services/qa_gate_service.py`](Backend/services/qa_gate_service.py) |
| `QATimelineIssue` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `QATimelineReport` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `QCReference` | `python-pydantic` | [`Backend/api/control_plane_publications.py`](Backend/api/control_plane_publications.py) |
| `QualityAssessmentResponse` | `python-pydantic` | [`Backend/api/endpoints/voice_cloning_quality.py`](Backend/api/endpoints/voice_cloning_quality.py) |
| `QualityGateResult` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `QualityProfile` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `QueueItem` | `python-pydantic` | [`Backend/api/approval_queue.py`](Backend/api/approval_queue.py) |
| `QueueItem` | `python-pydantic` | [`Backend/api/endpoints/post_scheduler_api.py`](Backend/api/endpoints/post_scheduler_api.py) |
| `QueueItemCreate` | `python-pydantic` | [`Backend/api/endpoints/publishing_queue.py`](Backend/api/endpoints/publishing_queue.py) |
| `QueueItemUpdate` | `python-pydantic` | [`Backend/api/endpoints/publishing_queue.py`](Backend/api/endpoints/publishing_queue.py) |
| `QueueScriptRequest` | `python-pydantic` | [`Backend/api/endpoints/ugc_content.py`](Backend/api/endpoints/ugc_content.py) |
| `QueueStats` | `python-pydantic` | [`Backend/api/approval_queue.py`](Backend/api/approval_queue.py) |
| `QuickRenderRequest` | `python-pydantic` | [`Backend/api/endpoints/video_render.py`](Backend/api/endpoints/video_render.py) |
| `ReadyResponse` | `python-pydantic` | [`Backend/control_plane/schemas.py`](Backend/control_plane/schemas.py) |
| `RecommendationResponse` | `python-pydantic` | [`Backend/api/endpoints/ai_recommendations.py`](Backend/api/endpoints/ai_recommendations.py) |
| `RecommendationResponse` | `python-pydantic` | [`Backend/api/endpoints/content_analyzer_api.py`](Backend/api/endpoints/content_analyzer_api.py) |
| `RecommendationsResponse` | `python-pydantic` | [`Backend/api/endpoints/analytics_insights.py`](Backend/api/endpoints/analytics_insights.py) |
| `RecommendedTimeResponse` | `python-pydantic` | [`Backend/api/endpoints/optimal_posting_times.py`](Backend/api/endpoints/optimal_posting_times.py) |
| `ReconcileChange` | `python-pydantic` | [`Backend/services/video_generation/speech_timing.py`](Backend/services/video_generation/speech_timing.py) |
| `ReconcileResult` | `python-pydantic` | [`Backend/services/video_generation/speech_timing.py`](Backend/services/video_generation/speech_timing.py) |
| `RecordActualRequest` | `python-pydantic` | [`Backend/api/endpoints/orchestrator_goals.py`](Backend/api/endpoints/orchestrator_goals.py) |
| `RecordInteractionRequest` | `python-pydantic` | [`Backend/api/endpoints/relationship_crm.py`](Backend/api/endpoints/relationship_crm.py) |
| `RecordPipelineResultRequest` | `python-pydantic` | [`Backend/api/endpoints/orchestrator_goals.py`](Backend/api/endpoints/orchestrator_goals.py) |
| `RecordPostedRequest` | `python-pydantic` | [`Backend/api/endpoints/schedule.py`](Backend/api/endpoints/schedule.py) |
| `RecycleRequest` | `python-pydantic` | [`Backend/api/content_recycling.py`](Backend/api/content_recycling.py) |
| `RefreshAllResponse` | `python-pydantic` | [`Backend/api/endpoints/data_orchestrator.py`](Backend/api/endpoints/data_orchestrator.py) |
| `RefreshRequest` | `python-pydantic` | [`Backend/api/endpoints/data_hydration.py`](Backend/api/endpoints/data_hydration.py) |
| `RegenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/publishing_analytics.py`](Backend/api/endpoints/publishing_analytics.py) |
| `RegisterAccountRequest` | `python-pydantic` | [`Backend/api/endpoints/safari_sessions.py`](Backend/api/endpoints/safari_sessions.py) |
| `RegisterAutomationRequest` | `python-pydantic` | [`Backend/api/endpoints/automations.py`](Backend/api/endpoints/automations.py) |
| `RegisterContentRequest` | `python-pydantic` | [`Backend/api/endpoints/content_guard.py`](Backend/api/endpoints/content_guard.py) |
| `RejectedEvent` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `RemotionBeatMarker` | `python-pydantic` | [`Backend/services/video_generation/remotion_time_events.py`](Backend/services/video_generation/remotion_time_events.py) |
| `RemotionBgLayer` | `python-pydantic` | [`Backend/services/video_generation/remotion_budgeter.py`](Backend/services/video_generation/remotion_budgeter.py) |
| `RemotionBudgetedPlan` | `python-pydantic` | [`Backend/services/video_generation/remotion_budgeter.py`](Backend/services/video_generation/remotion_budgeter.py) |
| `RemotionCharLayer` | `python-pydantic` | [`Backend/services/video_generation/remotion_budgeter.py`](Backend/services/video_generation/remotion_budgeter.py) |
| `RemotionRenderRequest` | `python-pydantic` | [`Backend/api/endpoints/remotion.py`](Backend/api/endpoints/remotion.py) |
| `RemotionRenderResponse` | `python-pydantic` | [`Backend/api/endpoints/remotion.py`](Backend/api/endpoints/remotion.py) |
| `RemotionSfxCue` | `python-pydantic` | [`Backend/services/video_generation/remotion_sfx.py`](Backend/services/video_generation/remotion_sfx.py) |
| `RemotionSfxLayer` | `python-pydantic` | [`Backend/services/video_generation/remotion_sfx.py`](Backend/services/video_generation/remotion_sfx.py) |
| `RemotionSfxMacro` | `python-pydantic` | [`Backend/services/video_generation/remotion_sfx.py`](Backend/services/video_generation/remotion_sfx.py) |
| `RemotionSfxMacros` | `python-pydantic` | [`Backend/services/video_generation/remotion_sfx.py`](Backend/services/video_generation/remotion_sfx.py) |
| `RemotionTimeEvent` | `python-pydantic` | [`Backend/services/video_generation/remotion_time_events.py`](Backend/services/video_generation/remotion_time_events.py) |
| `RemotionTimeEventsFile` | `python-pydantic` | [`Backend/services/video_generation/remotion_time_events.py`](Backend/services/video_generation/remotion_time_events.py) |
| `RemotionVisualReveal` | `python-pydantic` | [`Backend/services/video_generation/remotion_time_events.py`](Backend/services/video_generation/remotion_time_events.py) |
| `RemoveBackgroundRequest` | `python-pydantic` | [`Backend/api/endpoints/characters.py`](Backend/api/endpoints/characters.py) |
| `RemoveBackgroundResponse` | `python-pydantic` | [`Backend/api/endpoints/characters.py`](Backend/api/endpoints/characters.py) |
| `RenderClipRequest` | `python-pydantic` | [`Backend/api/endpoints/repurpose.py`](Backend/api/endpoints/repurpose.py) |
| `RenderConfig` | `python-pydantic` | [`Backend/services/video_generation/render_trigger.py`](Backend/services/video_generation/render_trigger.py) |
| `RenderJobSchema` | `python-pydantic` | [`Backend/services/media_factory/contracts/render_job.py`](Backend/services/media_factory/contracts/render_job.py) |
| `RenderMeta` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `RenderPlanMeta` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `RenderPlanRemotionV1` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `RenderPlanRemotionV2` | `python-pydantic` | [`Backend/services/video_generation/render_plan_v2.py`](Backend/services/video_generation/render_plan_v2.py) |
| `RenderPlanV2Meta` | `python-pydantic` | [`Backend/services/video_generation/render_plan_v2.py`](Backend/services/video_generation/render_plan_v2.py) |
| `RenderProps` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `RenderRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_intelligence.py`](Backend/api/endpoints/trend_intelligence.py) |
| `RenderRequest` | `python-pydantic` | [`Backend/api/endpoints/video_render.py`](Backend/api/endpoints/video_render.py) |
| `RenderResponse` | `python-pydantic` | [`Backend/api/endpoints/video_render.py`](Backend/api/endpoints/video_render.py) |
| `RenderResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `RenderResult` | `python-pydantic` | [`Backend/services/video_generation/render_trigger.py`](Backend/services/video_generation/render_trigger.py) |
| `RenderStatusResponse` | `python-pydantic` | [`Backend/api/endpoints/video_render.py`](Backend/api/endpoints/video_render.py) |
| `RenderStrategy` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `RenderTemplateRequest` | `python-pydantic` | [`Backend/api/endpoints/templates.py`](Backend/api/endpoints/templates.py) |
| `ReplyRequest` | `python-pydantic` | [`Backend/api/endpoints/inbox.py`](Backend/api/endpoints/inbox.py) |
| `ReplyRequest` | `python-pydantic` | [`Backend/api/endpoints/twitter_posting.py`](Backend/api/endpoints/twitter_posting.py) |
| `RepurposeRequest` | `python-pydantic` | [`Backend/api/endpoints/adaptive_scheduler.py`](Backend/api/endpoints/adaptive_scheduler.py) |
| `RescheduleRequest` | `python-pydantic` | [`Backend/api/endpoints/publishing_controls.py`](Backend/api/endpoints/publishing_controls.py) |
| `RespondToMessageRequest` | `python-pydantic` | [`Backend/api/endpoints/community_inbox.py`](Backend/api/endpoints/community_inbox.py) |
| `RetireStatusResponse` | `python-pydantic` | [`Backend/api/endpoints/template_retiree.py`](Backend/api/endpoints/template_retiree.py) |
| `RetireTemplateRequest` | `python-pydantic` | [`Backend/api/endpoints/template_retiree.py`](Backend/api/endpoints/template_retiree.py) |
| `RetireTemplateResponse` | `python-pydantic` | [`Backend/api/endpoints/template_retiree.py`](Backend/api/endpoints/template_retiree.py) |
| `RetirementCandidateResponse` | `python-pydantic` | [`Backend/api/endpoints/template_retiree.py`](Backend/api/endpoints/template_retiree.py) |
| `RetryClipRequest` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `RetryJobRequest` | `python-pydantic` | [`Backend/api/endpoints/sora_daily.py`](Backend/api/endpoints/sora_daily.py) |
| `RetryPolicyConfig` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `RetryResponse` | `python-pydantic` | [`Backend/control_plane/schemas.py`](Backend/control_plane/schemas.py) |
| `ReviewCreate` | `python-pydantic` | [`Backend/api/endpoints/content_loop.py`](Backend/api/endpoints/content_loop.py) |
| `ReviewRequest` | `python-pydantic` | [`Backend/api/endpoints/approval_queue.py`](Backend/api/endpoints/approval_queue.py) |
| `RisingAudioResponse` | `python-pydantic` | [`Backend/api/endpoints/trend_queries_api.py`](Backend/api/endpoints/trend_queries_api.py) |
| `RisingAudioResult` | `python-pydantic` | [`Backend/api/endpoints/trend_queries_api.py`](Backend/api/endpoints/trend_queries_api.py) |
| `RiskConfig` | `python-pydantic` | [`Backend/services/video_generation/plate_manager.py`](Backend/services/video_generation/plate_manager.py) |
| `RiskFlags` | `python-pydantic` | [`Backend/services/video_generation/plate_manager.py`](Backend/services/video_generation/plate_manager.py) |
| `RiskReport` | `python-pydantic` | [`Backend/services/video_generation/plate_manager.py`](Backend/services/video_generation/plate_manager.py) |
| `RoundDetail` | `python-pydantic` | [`Backend/services/creative_testing_pipeline/models.py`](Backend/services/creative_testing_pipeline/models.py) |
| `RouteRequest` | `python-pydantic` | [`Backend/api/endpoints/adaptive_scheduler.py`](Backend/api/endpoints/adaptive_scheduler.py) |
| `RouteVideoRequest` | `python-pydantic` | [`Backend/api/endpoints/video_routing_api.py`](Backend/api/endpoints/video_routing_api.py) |
| `RoutingDecisionResponse` | `python-pydantic` | [`Backend/api/endpoints/video_routing_api.py`](Backend/api/endpoints/video_routing_api.py) |
| `RssSource` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `RuleConditions` | `python-pydantic` | [`Backend/api/endpoints/knowledge_base.py`](Backend/api/endpoints/knowledge_base.py) |
| `RuleCreate` | `python-pydantic` | [`Backend/api/endpoints/knowledge_base.py`](Backend/api/endpoints/knowledge_base.py) |
| `RuleResponse` | `python-pydantic` | [`Backend/api/endpoints/knowledge_base.py`](Backend/api/endpoints/knowledge_base.py) |
| `RunArtifact` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `RunBenchmarkRequest` | `python-pydantic` | [`Backend/api/endpoints/benchmark_api.py`](Backend/api/endpoints/benchmark_api.py) |
| `RunCreate` | `python-pydantic` | [`Backend/api/endpoints/formats.py`](Backend/api/endpoints/formats.py) |
| `RunGapAnalysisRequest` | `python-pydantic` | [`Backend/api/endpoints/content_gap_api.py`](Backend/api/endpoints/content_gap_api.py) |
| `RunRequest` | `python-pydantic` | [`Backend/api/endpoints/formats_api.py`](Backend/api/endpoints/formats_api.py) |
| `RunResponse` | `python-pydantic` | [`Backend/api/endpoints/formats.py`](Backend/api/endpoints/formats.py) |
| `RunResponse` | `python-pydantic` | [`Backend/api/endpoints/formats_api.py`](Backend/api/endpoints/formats_api.py) |
| `RuntimeBudget` | `python-pydantic` | [`Backend/services/video_generation/runtime_budget.py`](Backend/services/video_generation/runtime_budget.py) |
| `RunwayAlert` | `python-pydantic` | [`Backend/api/endpoints/content_runway.py`](Backend/api/endpoints/content_runway.py) |
| `RunwayBreakdown` | `python-pydantic` | [`Backend/api/endpoints/content_runway.py`](Backend/api/endpoints/content_runway.py) |
| `RunwayStats` | `python-pydantic` | [`Backend/api/content_pipeline.py`](Backend/api/content_pipeline.py) |
| `RunwayStatus` | `python-pydantic` | [`Backend/api/endpoints/content_runway.py`](Backend/api/endpoints/content_runway.py) |
| `SafetyConfig` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `SampleTemplateRequest` | `python-pydantic` | [`Backend/api/endpoints/template_leaderboard.py`](Backend/api/endpoints/template_leaderboard.py) |
| `SaveIdeaRequest` | `python-pydantic` | [`Backend/api/endpoints/content_ideas_api.py`](Backend/api/endpoints/content_ideas_api.py) |
| `SavedHook` | `python-pydantic` | [`Backend/services/hook_library_service.py`](Backend/services/hook_library_service.py) |
| `SavedReplyRequest` | `python-pydantic` | [`Backend/api/endpoints/inbox.py`](Backend/api/endpoints/inbox.py) |
| `ScanDirectoryRequest` | `python-pydantic` | [`Backend/api/endpoints/content_ingestion.py`](Backend/api/endpoints/content_ingestion.py) |
| `ScanDirectoryRequest` | `python-pydantic` | [`Backend/api/endpoints/content_sourcing.py`](Backend/api/endpoints/content_sourcing.py) |
| `ScanRequest` | `python-pydantic` | [`Backend/api/endpoints/android_import_api.py`](Backend/api/endpoints/android_import_api.py) |
| `ScanRequest` | `python-pydantic` | [`Backend/api/endpoints/ios_import_api.py`](Backend/api/endpoints/ios_import_api.py) |
| `ScanRequest` | `python-pydantic` | [`Backend/api/endpoints/videos.py`](Backend/api/endpoints/videos.py) |
| `SceneDataRequest` | `python-pydantic` | [`Backend/api/endpoints/creative_briefs.py`](Backend/api/endpoints/creative_briefs.py) |
| `SceneResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `SceneSummary` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `ScheduleConfig` | `python-pydantic` | [`Backend/api/routes/sora_automation.py`](Backend/api/routes/sora_automation.py) |
| `ScheduleContentRequest` | `python-pydantic` | [`Backend/routers/visual_campaign.py`](Backend/routers/visual_campaign.py) |
| `SchedulePlanRequest` | `python-pydantic` | [`Backend/api/endpoints/narrative_builder.py`](Backend/api/endpoints/narrative_builder.py) |
| `SchedulePostRequest` | `python-pydantic` | [`Backend/api/endpoints/calendar.py`](Backend/api/endpoints/calendar.py) |
| `SchedulePostRequest` | `python-pydantic` | [`Backend/api/endpoints/publishing_analytics.py`](Backend/api/endpoints/publishing_analytics.py) |
| `SchedulePostUpdate` | `python-pydantic` | [`Backend/api/endpoints/calendar.py`](Backend/api/endpoints/calendar.py) |
| `SchedulePreviewResponse` | `python-pydantic` | [`Backend/api/endpoints/smart_schedule.py`](Backend/api/endpoints/smart_schedule.py) |
| `ScheduleRequest` | `python-pydantic` | [`Backend/api/content_pipeline.py`](Backend/api/content_pipeline.py) |
| `ScheduleRequest` | `python-pydantic` | [`Backend/api/endpoints/publishing.py`](Backend/api/endpoints/publishing.py) |
| `ScheduleRequest` | `python-pydantic` | [`Backend/api/endpoints/smart_schedule.py`](Backend/api/endpoints/smart_schedule.py) |
| `ScheduleRequest` | `python-pydantic` | [`Backend/api/endpoints/twitter_posting.py`](Backend/api/endpoints/twitter_posting.py) |
| `ScheduleResponse` | `python-pydantic` | [`Backend/api/endpoints/external_scheduling.py`](Backend/api/endpoints/external_scheduling.py) |
| `ScheduleResponse` | `python-pydantic` | [`Backend/api/endpoints/scheduling.py`](Backend/api/endpoints/scheduling.py) |
| `ScheduleSlotResponse` | `python-pydantic` | [`Backend/api/endpoints/posting_optimizer_api.py`](Backend/api/endpoints/posting_optimizer_api.py) |
| `ScheduleTarget` | `python-pydantic` | [`Backend/api/endpoints/external_scheduling.py`](Backend/api/endpoints/external_scheduling.py) |
| `ScheduleTweetsRequest` | `python-pydantic` | [`Backend/routers/twitter_campaign.py`](Backend/routers/twitter_campaign.py) |
| `ScheduleWakeRequest` | `python-pydantic` | [`Backend/api/endpoints/sleep.py`](Backend/api/endpoints/sleep.py) |
| `ScheduledPost` | `python-pydantic` | [`Backend/api/endpoints/schedule.py`](Backend/api/endpoints/schedule.py) |
| `ScheduledPostCreate` | `python-pydantic` | [`Backend/api/endpoints/schedule.py`](Backend/api/endpoints/schedule.py) |
| `ScheduledPostResponse` | `python-pydantic` | [`Backend/api/endpoints/calendar.py`](Backend/api/endpoints/calendar.py) |
| `ScheduledPostUpdate` | `python-pydantic` | [`Backend/api/endpoints/schedule.py`](Backend/api/endpoints/schedule.py) |
| `SchedulerConfigRequest` | `python-pydantic` | [`Backend/api/endpoints/analysis_scheduler.py`](Backend/api/endpoints/analysis_scheduler.py) |
| `SchedulerConfigRequest` | `python-pydantic` | [`Backend/api/endpoints/inventory_scheduler.py`](Backend/api/endpoints/inventory_scheduler.py) |
| `SchedulerStatus` | `python-pydantic` | [`Backend/api/metrics_scheduler_api.py`](Backend/api/metrics_scheduler_api.py) |
| `SchedulerStatusResponse` | `python-pydantic` | [`Backend/api/endpoints/post_scheduler_api.py`](Backend/api/endpoints/post_scheduler_api.py) |
| `ScrapeRequest` | `python-pydantic` | [`Backend/api/endpoints/posted_content_matcher.py`](Backend/api/endpoints/posted_content_matcher.py) |
| `Script` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `ScriptBeatResponse` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `ScriptBeatSchema` | `python-pydantic` | [`Backend/services/media_factory/contracts/script.py`](Backend/services/media_factory/contracts/script.py) |
| `ScriptGenerationRequest` | `python-pydantic` | [`Backend/api/endpoints/safari_automation.py`](Backend/api/endpoints/safari_automation.py) |
| `ScriptOutline` | `python-pydantic` | [`Backend/api/endpoints/trend_queries_api.py`](Backend/api/endpoints/trend_queries_api.py) |
| `ScriptRequest` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `ScriptRequest` | `python-pydantic` | [`Backend/api/endpoints/script_generation.py`](Backend/api/endpoints/script_generation.py) |
| `ScriptResponse` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `ScriptResponse` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `ScriptResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `ScriptSchema` | `python-pydantic` | [`Backend/services/media_factory/contracts/script.py`](Backend/services/media_factory/contracts/script.py) |
| `ScriptSegment` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `SearchMusicRequest` | `python-pydantic` | [`Backend/api/endpoints/music_crawler.py`](Backend/api/endpoints/music_crawler.py) |
| `SearchRequest` | `python-pydantic` | [`Backend/api/endpoints/semantic_search.py`](Backend/api/endpoints/semantic_search.py) |
| `SearchResponse` | `python-pydantic` | [`Backend/api/endpoints/semantic_search.py`](Backend/api/endpoints/semantic_search.py) |
| `SearchResult` | `python-pydantic` | [`Backend/services/niche_search_service.py`](Backend/services/niche_search_service.py) |
| `SearchSfxRequest` | `python-pydantic` | [`Backend/api/endpoints/sfx_library.py`](Backend/api/endpoints/sfx_library.py) |
| `SearchTracksRequest` | `python-pydantic` | [`Backend/api/endpoints/music_library.py`](Backend/api/endpoints/music_library.py) |
| `SeedAccountRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_intelligence.py`](Backend/api/endpoints/trend_intelligence.py) |
| `SegmentCreate` | `python-pydantic` | [`Backend/services/segment_engine.py`](Backend/services/segment_engine.py) |
| `SegmentCreateRequest` | `python-pydantic` | [`Backend/api/endpoints/enhanced_analysis.py`](Backend/api/endpoints/enhanced_analysis.py) |
| `SegmentDefinition` | `python-pydantic` | [`Backend/services/segment_engine.py`](Backend/services/segment_engine.py) |
| `SegmentInsightResponse` | `python-pydantic` | [`Backend/services/segment_engine.py`](Backend/services/segment_engine.py) |
| `SegmentMergeRequest` | `python-pydantic` | [`Backend/api/endpoints/enhanced_analysis.py`](Backend/api/endpoints/enhanced_analysis.py) |
| `SegmentSplitRequest` | `python-pydantic` | [`Backend/api/endpoints/enhanced_analysis.py`](Backend/api/endpoints/enhanced_analysis.py) |
| `SegmentUpdateRequest` | `python-pydantic` | [`Backend/api/endpoints/enhanced_analysis.py`](Backend/api/endpoints/enhanced_analysis.py) |
| `SelectFormatRequest` | `python-pydantic` | [`Backend/api/endpoints/video_generation.py`](Backend/api/endpoints/video_generation.py) |
| `SelectorUpdateRequest` | `python-pydantic` | [`Backend/api/endpoints/twitter_posting.py`](Backend/api/endpoints/twitter_posting.py) |
| `SendDMRequest` | `python-pydantic` | [`Backend/api/endpoints/dm_outreach.py`](Backend/api/endpoints/dm_outreach.py) |
| `SendEmailRequest` | `python-pydantic` | [`Backend/api/endpoints/email.py`](Backend/api/endpoints/email.py) |
| `SendMessageRequest` | `python-pydantic` | [`Backend/api/endpoints/dm_outreach.py`](Backend/api/endpoints/dm_outreach.py) |
| `SendSegmentEmailRequest` | `python-pydantic` | [`Backend/api/endpoints/email.py`](Backend/api/endpoints/email.py) |
| `SentimentBatchRequest` | `python-pydantic` | [`Backend/api/endpoints/batch_analysis.py`](Backend/api/endpoints/batch_analysis.py) |
| `SentimentResult` | `python-pydantic` | [`Backend/api/ai_curation.py`](Backend/api/ai_curation.py) |
| `ServiceStatusResponse` | `python-pydantic` | [`Backend/api/endpoints/strategic_analysis.py`](Backend/api/endpoints/strategic_analysis.py) |
| `SessionRequest` | `python-pydantic` | [`Backend/api/engagement_autopilot.py`](Backend/api/engagement_autopilot.py) |
| `SetActiveAccountRequest` | `python-pydantic` | [`Backend/api/endpoints/safari_sessions.py`](Backend/api/endpoints/safari_sessions.py) |
| `SettingUpdate` | `python-pydantic` | [`Backend/api/endpoints/app_settings.py`](Backend/api/endpoints/app_settings.py) |
| `SettingsUpdate` | `python-pydantic` | [`Backend/api/engagement_autopilot.py`](Backend/api/engagement_autopilot.py) |
| `SfxAudioEvent` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `SfxContextItem` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `SfxContextPack` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `SfxCue` | `python-pydantic` | [`Backend/services/sfx_library/cue_sheet.py`](Backend/services/sfx_library/cue_sheet.py) |
| `SfxItem` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `SfxLicense` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `SfxMacro` | `python-pydantic` | [`Backend/services/sfx_library/macros.py`](Backend/services/sfx_library/macros.py) |
| `SfxMacros` | `python-pydantic` | [`Backend/services/sfx_library/macros.py`](Backend/services/sfx_library/macros.py) |
| `SfxManifest` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `SfxSelectionPromptRequest` | `python-pydantic` | [`Backend/api/endpoints/sfx_library.py`](Backend/api/endpoints/sfx_library.py) |
| `SfxSelectionPromptResponse` | `python-pydantic` | [`Backend/api/endpoints/sfx_library.py`](Backend/api/endpoints/sfx_library.py) |
| `Shot` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `ShotBudget` | `python-pydantic` | [`Backend/services/video_generation/shot_budgeter.py`](Backend/services/video_generation/shot_budgeter.py) |
| `ShotPlanEntry` | `python-pydantic` | [`Backend/services/video_generation/auto_shot_planner.py`](Backend/services/video_generation/auto_shot_planner.py) |
| `ShotPlanMeta` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `ShotPlanV1` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `ShotReferences` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `ShotV2` | `python-pydantic` | [`Backend/services/video_generation/shot_types.py`](Backend/services/video_generation/shot_types.py) |
| `ShuffleResponse` | `python-pydantic` | [`Backend/api/endpoints/music_matching.py`](Backend/api/endpoints/music_matching.py) |
| `SignalMetrics` | `python-pydantic` | [`Backend/api/endpoints/narrative_builder.py`](Backend/api/endpoints/narrative_builder.py) |
| `SimilarContentResponse` | `python-pydantic` | [`Backend/api/endpoints/semantic_search.py`](Backend/api/endpoints/semantic_search.py) |
| `SingleDownloadRequest` | `python-pydantic` | [`Backend/api/endpoints/content_download.py`](Backend/api/endpoints/content_download.py) |
| `SlotOverride` | `python-pydantic` | [`Backend/api/endpoints/adaptive_scheduler.py`](Backend/api/endpoints/adaptive_scheduler.py) |
| `SlotRequest` | `python-pydantic` | [`Backend/api/endpoints/adaptive_scheduler.py`](Backend/api/endpoints/adaptive_scheduler.py) |
| `SmartBulkRequest` | `python-pydantic` | [`Backend/api/endpoints/external_scheduling.py`](Backend/api/endpoints/external_scheduling.py) |
| `SmartScheduleRequest` | `python-pydantic` | [`Backend/api/endpoints/external_scheduling.py`](Backend/api/endpoints/external_scheduling.py) |
| `SoraDialogueConfig` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `SoraDialogueConfig` | `python-pydantic` | [`Backend/services/video_generation/voice_strategy.py`](Backend/services/video_generation/voice_strategy.py) |
| `SoraGenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/adaptive_scheduler.py`](Backend/api/endpoints/adaptive_scheduler.py) |
| `SoraGenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `SoraGenerateRequest` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `SoraGenerationRequest` | `python-pydantic` | [`Backend/api/endpoints/safari_automation.py`](Backend/api/endpoints/safari_automation.py) |
| `SoraPrompt` | `python-pydantic` | [`Backend/api/routes/sora_automation.py`](Backend/api/routes/sora_automation.py) |
| `SoraRemixRequest` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `SoraRemixRequest` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `SoraVideoResponse` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `SoraVideoResponse` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `SoundAnalyzeRequest` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `SoundOfTheDayRequest` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `SoundResponse` | `python-pydantic` | [`Backend/api/endpoints/instagram_trends.py`](Backend/api/endpoints/instagram_trends.py) |
| `SourceRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_intelligence.py`](Backend/api/endpoints/trend_intelligence.py) |
| `SourceResponse` | `python-pydantic` | [`Backend/api/endpoints/repurpose.py`](Backend/api/endpoints/repurpose.py) |
| `SpeechBudgetResult` | `python-pydantic` | [`Backend/services/video_generation/voice_engine.py`](Backend/services/video_generation/voice_engine.py) |
| `SpeechTimingConfig` | `python-pydantic` | [`Backend/services/video_generation/speech_timing.py`](Backend/services/video_generation/speech_timing.py) |
| `SpendRequest` | `python-pydantic` | [`Backend/api/endpoints/orchestrator_goals.py`](Backend/api/endpoints/orchestrator_goals.py) |
| `StartAuditRequest` | `python-pydantic` | [`Backend/api/endpoints/competitor_audit.py`](Backend/api/endpoints/competitor_audit.py) |
| `StartDailyRunRequest` | `python-pydantic` | [`Backend/api/endpoints/sora_daily.py`](Backend/api/endpoints/sora_daily.py) |
| `StartGenerationRequest` | `python-pydantic` | [`Backend/api/endpoints/video_orchestrator.py`](Backend/api/endpoints/video_orchestrator.py) |
| `StartGenerationRequest` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `StartImportRequest` | `python-pydantic` | [`Backend/api/endpoints/android_import_api.py`](Backend/api/endpoints/android_import_api.py) |
| `StartImportRequest` | `python-pydantic` | [`Backend/api/endpoints/ios_import_api.py`](Backend/api/endpoints/ios_import_api.py) |
| `StartPipelineRequest` | `python-pydantic` | [`Backend/api/endpoints/orchestrator.py`](Backend/api/endpoints/orchestrator.py) |
| `StartRenderRequest` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `StartRunRequest` | `python-pydantic` | [`Backend/api/endpoints/automations.py`](Backend/api/endpoints/automations.py) |
| `StatusResponse` | `python-pydantic` | [`Backend/api/endpoints/safari_automation.py`](Backend/api/endpoints/safari_automation.py) |
| `StitchedNarration` | `python-pydantic` | [`Backend/services/video_generation/vo_stitcher.py`](Backend/services/video_generation/vo_stitcher.py) |
| `StoryIRMeta` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `StoryIRV1` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `StoryIRVariables` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `StrategyReport` | `python-pydantic` | [`Backend/services/strategy_report_service.py`](Backend/services/strategy_report_service.py) |
| `StructuredAnalysisRequest` | `python-pydantic` | [`Backend/api/endpoints/enhanced_analysis.py`](Backend/api/endpoints/enhanced_analysis.py) |
| `StyleBible` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `StyleConfig` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `StyleInfo` | `python-pydantic` | [`Backend/api/subtitles.py`](Backend/api/subtitles.py) |
| `SubtitleRequest` | `python-pydantic` | [`Backend/api/endpoints/clip_extraction.py`](Backend/api/endpoints/clip_extraction.py) |
| `SuggestReplyRequest` | `python-pydantic` | [`Backend/api/endpoints/relationship_crm.py`](Backend/api/endpoints/relationship_crm.py) |
| `SuggestSfxRequest` | `python-pydantic` | [`Backend/api/endpoints/sfx_library.py`](Backend/api/endpoints/sfx_library.py) |
| `SuggestionResponse` | `python-pydantic` | [`Backend/api/endpoints/reply_suggestions.py`](Backend/api/endpoints/reply_suggestions.py) |
| `SupabaseQuerySource` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `SyncAccountRequest` | `python-pydantic` | [`Backend/api/endpoints/accounts.py`](Backend/api/endpoints/accounts.py) |
| `SyncResponse` | `python-pydantic` | [`Backend/api/endpoints/competitor_api.py`](Backend/api/endpoints/competitor_api.py) |
| `TTSGenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/tts.py`](Backend/api/endpoints/tts.py) |
| `TTSGenerateResponse` | `python-pydantic` | [`Backend/api/endpoints/tts.py`](Backend/api/endpoints/tts.py) |
| `TTSProvider` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `TTSRequest` | `python-pydantic` | [`Backend/services/video_generation/hf_tts_provider.py`](Backend/services/video_generation/hf_tts_provider.py) |
| `TargetContent` | `python-pydantic` | [`Backend/api/comment_automation.py`](Backend/api/comment_automation.py) |
| `TemplateAllocationResponse` | `python-pydantic` | [`Backend/api/endpoints/bandit.py`](Backend/api/endpoints/bandit.py) |
| `TemplateCreate` | `python-pydantic` | [`Backend/api/endpoints/knowledge_base.py`](Backend/api/endpoints/knowledge_base.py) |
| `TemplateMatchRequest` | `python-pydantic` | [`Backend/api/endpoints/enhanced_analysis.py`](Backend/api/endpoints/enhanced_analysis.py) |
| `TemplateResponse` | `python-pydantic` | [`Backend/api/endpoints/knowledge_base.py`](Backend/api/endpoints/knowledge_base.py) |
| `TemplateResponse` | `python-pydantic` | [`Backend/api/endpoints/templates.py`](Backend/api/endpoints/templates.py) |
| `TemplateTransform` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `TestCampaign` | `python-pydantic` | [`Backend/services/creative_testing_pipeline/models.py`](Backend/services/creative_testing_pipeline/models.py) |
| `TestResult` | `python-pydantic` | [`Backend/api/endpoints/blotato_test.py`](Backend/api/endpoints/blotato_test.py) |
| `TestRound` | `python-pydantic` | [`Backend/services/creative_testing_pipeline/models.py`](Backend/services/creative_testing_pipeline/models.py) |
| `TextConstraintModel` | `python-pydantic` | [`Backend/api/endpoints/content_pipeline.py`](Backend/api/endpoints/content_pipeline.py) |
| `TextSuggestionRequest` | `python-pydantic` | [`Backend/api/endpoints/broll_candidates.py`](Backend/api/endpoints/broll_candidates.py) |
| `ThreadRequest` | `python-pydantic` | [`Backend/api/endpoints/twitter_posting.py`](Backend/api/endpoints/twitter_posting.py) |
| `ThumbnailJobResponse` | `python-pydantic` | [`Backend/api/media_processing.py`](Backend/api/media_processing.py) |
| `ThumbnailResponse` | `python-pydantic` | [`Backend/api/endpoints/thumbnails.py`](Backend/api/endpoints/thumbnails.py) |
| `TikTokComment` | `python-pydantic` | [`Backend/services/tiktok_analytics_service.py`](Backend/services/tiktok_analytics_service.py) |
| `TikTokVideoInfo` | `python-pydantic` | [`Backend/services/tiktok_analytics_service.py`](Backend/services/tiktok_analytics_service.py) |
| `TimePeriodComparison` | `python-pydantic` | [`Backend/api/analytics_compare.py`](Backend/api/analytics_compare.py) |
| `TimeSlotResponse` | `python-pydantic` | [`Backend/api/endpoints/smart_schedule.py`](Backend/api/endpoints/smart_schedule.py) |
| `TimelineItem` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `TimelineSchema` | `python-pydantic` | [`Backend/services/media_factory/contracts/timeline.py`](Backend/services/media_factory/contracts/timeline.py) |
| `TitleVariationResponse` | `python-pydantic` | [`Backend/api/endpoints/ai_titles.py`](Backend/api/endpoints/ai_titles.py) |
| `TopHashtagsRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_queries_api.py`](Backend/api/endpoints/trend_queries_api.py) |
| `TopHashtagsResponse` | `python-pydantic` | [`Backend/api/endpoints/trend_queries_api.py`](Backend/api/endpoints/trend_queries_api.py) |
| `TopicInput` | `python-pydantic` | [`Backend/api/explainer_video.py`](Backend/api/explainer_video.py) |
| `TrackErrorRequest` | `python-pydantic` | [`Backend/api/endpoints/user_tracking.py`](Backend/api/endpoints/user_tracking.py) |
| `TrackEventRequest` | `python-pydantic` | [`Backend/api/endpoints/user_tracking.py`](Backend/api/endpoints/user_tracking.py) |
| `TrackPerformanceRequest` | `python-pydantic` | [`Backend/api/endpoints/user_tracking.py`](Backend/api/endpoints/user_tracking.py) |
| `TrackRetentionRequest` | `python-pydantic` | [`Backend/api/endpoints/user_tracking.py`](Backend/api/endpoints/user_tracking.py) |
| `TrackedCompetitor` | `python-pydantic` | [`Backend/api/endpoints/trends.py`](Backend/api/endpoints/trends.py) |
| `TrackedLinkResponse` | `python-pydantic` | [`Backend/api/endpoints/offer_tracking.py`](Backend/api/endpoints/offer_tracking.py) |
| `TranscribeRequest` | `python-pydantic` | [`Backend/api/endpoints/venv_status.py`](Backend/api/endpoints/venv_status.py) |
| `TranscribeRequest` | `python-pydantic` | [`Backend/api/subtitles.py`](Backend/api/subtitles.py) |
| `TranscribeResponse` | `python-pydantic` | [`Backend/api/subtitles.py`](Backend/api/subtitles.py) |
| `TranscriptionInput` | `python-pydantic` | [`Backend/api/endpoints/captions.py`](Backend/api/endpoints/captions.py) |
| `Transform2D` | `python-pydantic` | [`Backend/services/video_generation/render_plan_v2.py`](Backend/services/video_generation/render_plan_v2.py) |
| `TrendBrief` | `python-pydantic` | [`Backend/services/trend_brief_service.py`](Backend/services/trend_brief_service.py) |
| `TrendBriefCreate` | `python-pydantic` | [`Backend/api/endpoints/trend_opportunities.py`](Backend/api/endpoints/trend_opportunities.py) |
| `TrendCardResponse` | `python-pydantic` | [`Backend/api/endpoints/trends_api.py`](Backend/api/endpoints/trends_api.py) |
| `TrendCardSchema` | `python-pydantic` | [`Backend/services/media_factory/contracts/trend_card.py`](Backend/services/media_factory/contracts/trend_card.py) |
| `TrendHashtag` | `python-pydantic` | [`Backend/api/endpoints/trends.py`](Backend/api/endpoints/trends.py) |
| `TrendInput` | `python-pydantic` | [`Backend/api/endpoints/video_pipeline.py`](Backend/api/endpoints/video_pipeline.py) |
| `TrendItemCreate` | `python-pydantic` | [`Backend/api/endpoints/trend_opportunities.py`](Backend/api/endpoints/trend_opportunities.py) |
| `TrendItemV1` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `TrendQuery` | `python-pydantic` | [`Backend/api/endpoints/trends_agent.py`](Backend/api/endpoints/trends_agent.py) |
| `TrendRequest` | `python-pydantic` | [`Backend/api/endpoints/adaptive_scheduler.py`](Backend/api/endpoints/adaptive_scheduler.py) |
| `TrendSound` | `python-pydantic` | [`Backend/api/endpoints/trends.py`](Backend/api/endpoints/trends.py) |
| `TrendTopic` | `python-pydantic` | [`Backend/api/endpoints/trends.py`](Backend/api/endpoints/trends.py) |
| `TrendVelocity` | `python-pydantic` | [`Backend/services/trend_velocity_service.py`](Backend/services/trend_velocity_service.py) |
| `TrendingAudioResponse` | `python-pydantic` | [`Backend/api/endpoints/trends_api.py`](Backend/api/endpoints/trends_api.py) |
| `TrendingFormatResponse` | `python-pydantic` | [`Backend/api/endpoints/trends_api.py`](Backend/api/endpoints/trends_api.py) |
| `TrendingHashtagResponse` | `python-pydantic` | [`Backend/api/endpoints/trends_api.py`](Backend/api/endpoints/trends_api.py) |
| `TrendingPhrase` | `python-pydantic` | [`Backend/api/endpoints/broll_producer.py`](Backend/api/endpoints/broll_producer.py) |
| `TrendingPhrasesResponse` | `python-pydantic` | [`Backend/api/endpoints/broll_producer.py`](Backend/api/endpoints/broll_producer.py) |
| `TrendingTopicResponse` | `python-pydantic` | [`Backend/api/endpoints/trending.py`](Backend/api/endpoints/trending.py) |
| `TrendsFeedResponse` | `python-pydantic` | [`Backend/api/endpoints/instagram_trends.py`](Backend/api/endpoints/instagram_trends.py) |
| `TriggerCascadeRequest` | `python-pydantic` | [`Backend/api/cascade_publisher.py`](Backend/api/cascade_publisher.py) |
| `TweetMetrics` | `python-pydantic` | [`Backend/api/endpoints/twitter_api.py`](Backend/api/endpoints/twitter_api.py) |
| `TweetRequest` | `python-pydantic` | [`Backend/api/endpoints/safari_automation.py`](Backend/api/endpoints/safari_automation.py) |
| `TweetRequest` | `python-pydantic` | [`Backend/api/endpoints/twitter_posting.py`](Backend/api/endpoints/twitter_posting.py) |
| `UGCConfig` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `UnifiedMetricsResponse` | `python-pydantic` | [`Backend/api/endpoints/multi_platform_analytics.py`](Backend/api/endpoints/multi_platform_analytics.py) |
| `UnifiedSearchRequest` | `python-pydantic` | [`Backend/api/endpoints/media_assets.py`](Backend/api/endpoints/media_assets.py) |
| `UpdateAutomationRequest` | `python-pydantic` | [`Backend/api/endpoints/automations.py`](Backend/api/endpoints/automations.py) |
| `UpdateBrandVoiceRequest` | `python-pydantic` | [`Backend/api/endpoints/reply_suggestions.py`](Backend/api/endpoints/reply_suggestions.py) |
| `UpdateConfigRequest` | `python-pydantic` | [`Backend/api/endpoints/publishing_controls.py`](Backend/api/endpoints/publishing_controls.py) |
| `UpdateContextRequest` | `python-pydantic` | [`Backend/api/endpoints/relationship_crm.py`](Backend/api/endpoints/relationship_crm.py) |
| `UpdateExperiment` | `python-pydantic` | [`Backend/api/endpoints/experiments.py`](Backend/api/endpoints/experiments.py) |
| `UpdateMessageRequest` | `python-pydantic` | [`Backend/api/endpoints/community_inbox.py`](Backend/api/endpoints/community_inbox.py) |
| `UpdatePhaseRequest` | `python-pydantic` | [`Backend/api/endpoints/dm_outreach.py`](Backend/api/endpoints/dm_outreach.py) |
| `UpdateProjectRequest` | `python-pydantic` | [`Backend/api/endpoints/media_creation.py`](Backend/api/endpoints/media_creation.py) |
| `UpdateQueueItemRequest` | `python-pydantic` | [`Backend/api/endpoints/publishing_controls.py`](Backend/api/endpoints/publishing_controls.py) |
| `UpdateScriptRequest` | `python-pydantic` | [`Backend/api/endpoints/ugc_content.py`](Backend/api/endpoints/ugc_content.py) |
| `UpdateScriptStatusRequest` | `python-pydantic` | [`Backend/api/endpoints/sora_daily.py`](Backend/api/endpoints/sora_daily.py) |
| `UpdateSlotRequest` | `python-pydantic` | [`Backend/api/endpoints/content_mix_api.py`](Backend/api/endpoints/content_mix_api.py) |
| `UpdateStatusRequest` | `python-pydantic` | [`Backend/api/endpoints/dm_outreach.py`](Backend/api/endpoints/dm_outreach.py) |
| `UpdateStatusRequest` | `python-pydantic` | [`Backend/api/endpoints/inbox.py`](Backend/api/endpoints/inbox.py) |
| `UpdateStatusRequest` | `python-pydantic` | [`Backend/api/endpoints/safari_sessions.py`](Backend/api/endpoints/safari_sessions.py) |
| `UpdateStyleRequest` | `python-pydantic` | [`Backend/routers/twitter_campaign.py`](Backend/routers/twitter_campaign.py) |
| `UpdateTemplateRequest` | `python-pydantic` | [`Backend/api/endpoints/templates.py`](Backend/api/endpoints/templates.py) |
| `UpdateVoiceProfileRequest` | `python-pydantic` | [`Backend/api/endpoints/voice_cloning.py`](Backend/api/endpoints/voice_cloning.py) |
| `UploadInitRequest` | `python-pydantic` | [`Backend/api/media_processing.py`](Backend/api/media_processing.py) |
| `UploadInitResponse` | `python-pydantic` | [`Backend/api/media_processing.py`](Backend/api/media_processing.py) |
| `UploadMediaRequest` | `python-pydantic` | [`Backend/api/blotato_router.py`](Backend/api/blotato_router.py) |
| `UsageStatsResponse` | `python-pydantic` | [`Backend/api/endpoints/api_usage.py`](Backend/api/endpoints/api_usage.py) |
| `ValidateEventsRequest` | `python-pydantic` | [`Backend/api/endpoints/sfx_library.py`](Backend/api/endpoints/sfx_library.py) |
| `ValidateEventsResponse` | `python-pydantic` | [`Backend/api/endpoints/sfx_library.py`](Backend/api/endpoints/sfx_library.py) |
| `ValidatedRequest` | `python-pydantic` | [`Backend/utils/input_validation.py`](Backend/utils/input_validation.py) |
| `ValidationError` | `python-pydantic` | [`Backend/services/video_generation/validator.py`](Backend/services/video_generation/validator.py) |
| `ValidationResult` | `python-pydantic` | [`Backend/services/video_generation/validator.py`](Backend/services/video_generation/validator.py) |
| `VariantScheduleRequest` | `python-pydantic` | [`Backend/api/endpoints/experiments.py`](Backend/api/endpoints/experiments.py) |
| `VariantSet` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `VariationResponse` | `python-pydantic` | [`Backend/api/endpoints/content_variations.py`](Backend/api/endpoints/content_variations.py) |
| `VelocityCalculationResponse` | `python-pydantic` | [`Backend/api/endpoints/trends_api.py`](Backend/api/endpoints/trends_api.py) |
| `VerifyExportRequest` | `python-pydantic` | [`Backend/api/endpoints/content_ingestion.py`](Backend/api/endpoints/content_ingestion.py) |
| `VerifyPublishRequest` | `python-pydantic` | [`Backend/api/endpoints/schedule.py`](Backend/api/endpoints/schedule.py) |
| `VideoConfig` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `VideoCreationResponse` | `python-pydantic` | [`Backend/api/blotato_router.py`](Backend/api/blotato_router.py) |
| `VideoDataRequest` | `python-pydantic` | [`Backend/api/endpoints/creative_briefs.py`](Backend/api/endpoints/creative_briefs.py) |
| `VideoEmbedRequest` | `python-pydantic` | [`Backend/api/endpoints/semantic_search.py`](Backend/api/endpoints/semantic_search.py) |
| `VideoFormat` | `python-pydantic` | [`Backend/api/routes/video_formats.py`](Backend/api/routes/video_formats.py) |
| `VideoGenerateRequest` | `python-pydantic` | [`Backend/api/endpoints/sora_automation.py`](Backend/api/endpoints/sora_automation.py) |
| `VideoGeneration` | `python-pydantic` | [`Backend/api/endpoints/ai_video.py`](Backend/api/endpoints/ai_video.py) |
| `VideoGenerationRequest` | `python-pydantic` | [`Backend/api/endpoints/ai_video.py`](Backend/api/endpoints/ai_video.py) |
| `VideoGenerationRequest` | `python-pydantic` | [`Backend/api/endpoints/ai_video_generation.py`](Backend/api/endpoints/ai_video_generation.py) |
| `VideoGenerationResponse` | `python-pydantic` | [`Backend/api/endpoints/ai_video_generation.py`](Backend/api/endpoints/ai_video_generation.py) |
| `VideoInfo` | `python-pydantic` | [`Backend/api/endpoints/platform_matching.py`](Backend/api/endpoints/platform_matching.py) |
| `VideoJob` | `python-pydantic` | [`Backend/api/endpoints/ai_video_generation.py`](Backend/api/endpoints/ai_video_generation.py) |
| `VideoJobResponse` | `python-pydantic` | [`Backend/api/endpoints/video_generation.py`](Backend/api/endpoints/video_generation.py) |
| `VideoMetadataResponse` | `python-pydantic` | [`Backend/api/endpoints/video_routing_api.py`](Backend/api/endpoints/video_routing_api.py) |
| `VideoProcessRequest` | `python-pydantic` | [`Backend/api/endpoints/safari_automation.py`](Backend/api/endpoints/safari_automation.py) |
| `VideoResponse` | `python-pydantic` | [`Backend/api/endpoints/channel_analyzer.py`](Backend/api/endpoints/channel_analyzer.py) |
| `VideoResponse` | `python-pydantic` | [`Backend/api/endpoints/tiktok_repurpose.py`](Backend/api/endpoints/tiktok_repurpose.py) |
| `VideoResponse` | `python-pydantic` | [`Backend/api/endpoints/videos.py`](Backend/api/endpoints/videos.py) |
| `VideoReview` | `python-pydantic` | [`Backend/api/endpoints/review.py`](Backend/api/endpoints/review.py) |
| `VideoStatusResponse` | `python-pydantic` | [`Backend/api/blotato_router.py`](Backend/api/blotato_router.py) |
| `ViralForecastRequest` | `python-pydantic` | [`Backend/api/endpoints/reeltrends.py`](Backend/api/endpoints/reeltrends.py) |
| `VisualIntentSchema` | `python-pydantic` | [`Backend/services/video_orchestrator/schemas.py`](Backend/services/video_orchestrator/schemas.py) |
| `VisualReveal` | `python-pydantic` | [`Backend/services/sfx_library/visual_reveals.py`](Backend/services/sfx_library/visual_reveals.py) |
| `VisualRevealsFile` | `python-pydantic` | [`Backend/services/sfx_library/visual_reveals.py`](Backend/services/sfx_library/visual_reveals.py) |
| `VisualsConfig` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `VisualsProvider` | `python-pydantic` | [`Backend/services/formats/schema.py`](Backend/services/formats/schema.py) |
| `VisualsRequest` | `python-pydantic` | [`Backend/api/endpoints/visuals.py`](Backend/api/endpoints/visuals.py) |
| `VisualsResponse` | `python-pydantic` | [`Backend/api/endpoints/visuals.py`](Backend/api/endpoints/visuals.py) |
| `VisualsSearchCriteriaRequest` | `python-pydantic` | [`Backend/api/endpoints/visuals.py`](Backend/api/endpoints/visuals.py) |
| `VoiceBuildResult` | `python-pydantic` | [`Backend/services/video_generation/voice_engine.py`](Backend/services/video_generation/voice_engine.py) |
| `VoiceConstraints` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `VoiceConstraints` | `python-pydantic` | [`Backend/services/video_generation/voice_strategy.py`](Backend/services/video_generation/voice_strategy.py) |
| `VoiceGenerationResponse` | `python-pydantic` | [`Backend/api/endpoints/voice_cloning.py`](Backend/api/endpoints/voice_cloning.py) |
| `VoiceInfo` | `python-pydantic` | [`Backend/api/blotato_router.py`](Backend/api/blotato_router.py) |
| `VoiceInfo` | `python-pydantic` | [`Backend/api/endpoints/voice_selection.py`](Backend/api/endpoints/voice_selection.py) |
| `VoicePreviewRequest` | `python-pydantic` | [`Backend/api/endpoints/voice_selection.py`](Backend/api/endpoints/voice_selection.py) |
| `VoiceProfileResponse` | `python-pydantic` | [`Backend/api/endpoints/voice_cloning.py`](Backend/api/endpoints/voice_cloning.py) |
| `VoiceStrategy` | `python-pydantic` | [`Backend/services/video_generation/types.py`](Backend/services/video_generation/types.py) |
| `VoiceStrategy` | `python-pydantic` | [`Backend/services/video_generation/voice_engine.py`](Backend/services/video_generation/voice_engine.py) |
| `VoiceStrategy` | `python-pydantic` | [`Backend/services/video_generation/voice_strategy.py`](Backend/services/video_generation/voice_strategy.py) |
| `VoiceVars` | `python-pydantic` | [`Backend/services/video_generation/perspective_enforcer.py`](Backend/services/video_generation/perspective_enforcer.py) |
| `VoiceoverAudioEvent` | `python-pydantic` | [`Backend/services/sfx_library/types.py`](Backend/services/sfx_library/types.py) |
| `WakeRequest` | `python-pydantic` | [`Backend/api/endpoints/sleep.py`](Backend/api/endpoints/sleep.py) |
| `WebhookConfig` | `python-pydantic` | [`Backend/api/endpoints/trends_agent.py`](Backend/api/endpoints/trends_agent.py) |
| `WeeklyMetricsResponse` | `python-pydantic` | [`Backend/api/endpoints/analytics_insights.py`](Backend/api/endpoints/analytics_insights.py) |
| `WinnerSelection` | `python-pydantic` | [`Backend/services/creative_testing_pipeline/models.py`](Backend/services/creative_testing_pipeline/models.py) |
| `WordData` | `python-pydantic` | [`Backend/api/endpoints/viral_analysis.py`](Backend/api/endpoints/viral_analysis.py) |
| `WorkspaceCreate` | `python-pydantic` | [`Backend/api/endpoints/workspaces.py`](Backend/api/endpoints/workspaces.py) |
| `WorkspaceMemberResponse` | `python-pydantic` | [`Backend/api/endpoints/workspaces.py`](Backend/api/endpoints/workspaces.py) |
| `WorkspaceResponse` | `python-pydantic` | [`Backend/api/endpoints/workspaces.py`](Backend/api/endpoints/workspaces.py) |
| `WorkspaceUpdate` | `python-pydantic` | [`Backend/api/endpoints/workspaces.py`](Backend/api/endpoints/workspaces.py) |
| `YouTubeChannelMetrics` | `python-pydantic` | [`Backend/services/youtube_analytics_service.py`](Backend/services/youtube_analytics_service.py) |
| `YouTubeChannelRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_intelligence.py`](Backend/api/endpoints/trend_intelligence.py) |
| `YouTubeComment` | `python-pydantic` | [`Backend/services/youtube_analytics_service.py`](Backend/services/youtube_analytics_service.py) |
| `YouTubeCrawlRequest` | `python-pydantic` | [`Backend/api/endpoints/trend_intelligence.py`](Backend/api/endpoints/trend_intelligence.py) |
| `YouTubeVideoMetrics` | `python-pydantic` | [`Backend/services/youtube_analytics_service.py`](Backend/services/youtube_analytics_service.py) |

## Database contracts

| Object | Kind | Migration/source |
|---|---|---|
| `actp_campaign_summary` | `MATERIALIZED VIEW` | [`Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql`](Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql) |
| `actp_creative_leaderboard` | `MATERIALIZED VIEW` | [`Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql`](Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql) |
| `actp_ad_deployments` | `TABLE` | [`Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql`](Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql) |
| `actp_audit_log` | `TABLE` | [`Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql`](Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql) |
| `actp_campaign_templates` | `TABLE` | [`Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql`](Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql) |
| `actp_campaigns` | `TABLE` | [`Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql`](Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql) |
| `actp_creatives` | `TABLE` | [`Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql`](Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql) |
| `actp_dead_letter_queue` | `TABLE` | [`Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql`](Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql) |
| `actp_metric_snapshots` | `TABLE` | [`Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql`](Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql) |
| `actp_organic_posts` | `TABLE` | [`Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql`](Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql) |
| `actp_performance_logs` | `TABLE` | [`Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql`](Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql) |
| `actp_rounds` | `TABLE` | [`Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql`](Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql) |
| `actp_scheduled_tasks` | `TABLE` | [`Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql`](Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql) |
| `actp_webhooks` | `TABLE` | [`Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql`](Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql) |
| `actp_winner_selections` | `TABLE` | [`Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql`](Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql) |
| `actp_winning_patterns` | `TABLE` | [`Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql`](Backend/services/creative_testing_pipeline/migrations/002_indexes_audit_fts.sql) |
| `ad_instances` | `TABLE` | [`Backend/migrations/narrative_builder_schema.sql`](Backend/migrations/narrative_builder_schema.sql) |
| `agent_artifacts` | `TABLE` | [`supabase/migrations_disabled/20251223000002_automation_center_schema.sql`](supabase/migrations_disabled/20251223000002_automation_center_schema.sql) |
| `agent_budgets` | `TABLE` | [`Backend/migrations/agent_budget_memory_schema.sql`](Backend/migrations/agent_budget_memory_schema.sql) |
| `agent_events` | `TABLE` | [`Backend/migrations/001_create_agent_events_table.sql`](Backend/migrations/001_create_agent_events_table.sql) |
| `agent_events` | `TABLE` | [`supabase/migrations_disabled/20251223000005_agent_events.sql`](supabase/migrations_disabled/20251223000005_agent_events.sql) |
| `agent_memories` | `TABLE` | [`Backend/migrations/agent_budget_memory_schema.sql`](Backend/migrations/agent_budget_memory_schema.sql) |
| `agent_queue` | `TABLE` | [`supabase/migrations_disabled/20251223000003_agent_queue.sql`](supabase/migrations_disabled/20251223000003_agent_queue.sql) |
| `agent_runs` | `TABLE` | [`Backend/database/migrations/014_brand_ops_engagement.sql`](Backend/database/migrations/014_brand_ops_engagement.sql) |
| `agent_runs` | `TABLE` | [`Backend/migrations/agent_schedules_runs_steps.sql`](Backend/migrations/agent_schedules_runs_steps.sql) |
| `agent_runs` | `TABLE` | [`supabase/migrations_disabled/20251223000002_automation_center_schema.sql`](supabase/migrations_disabled/20251223000002_automation_center_schema.sql) |
| `agent_schedules` | `TABLE` | [`Backend/migrations/agent_schedules_runs_steps.sql`](Backend/migrations/agent_schedules_runs_steps.sql) |
| `agent_schedules` | `TABLE` | [`supabase/migrations_disabled/20251223000002_automation_center_schema.sql`](supabase/migrations_disabled/20251223000002_automation_center_schema.sql) |
| `agent_steps` | `TABLE` | [`Backend/migrations/agent_schedules_runs_steps.sql`](Backend/migrations/agent_schedules_runs_steps.sql) |
| `agent_steps` | `TABLE` | [`supabase/migrations_disabled/20251223000002_automation_center_schema.sql`](supabase/migrations_disabled/20251223000002_automation_center_schema.sql) |
| `ai_camera_motions` | `TABLE` | [`supabase/migrations/20251222000002_ai_media_generations_enhanced.sql`](supabase/migrations/20251222000002_ai_media_generations_enhanced.sql) |
| `ai_characters` | `TABLE` | [`supabase/migrations/20251222000002_ai_media_generations_enhanced.sql`](supabase/migrations/20251222000002_ai_media_generations_enhanced.sql) |
| `ai_generation_jobs` | `TABLE` | [`supabase/migrations/20251222000002_ai_media_generations_enhanced.sql`](supabase/migrations/20251222000002_ai_media_generations_enhanced.sql) |
| `ai_service_logs` | `TABLE` | [`Backend/database/schema.sql`](Backend/database/schema.sql) |
| `ai_style_presets` | `TABLE` | [`supabase/migrations/20251222000002_ai_media_generations_enhanced.sql`](supabase/migrations/20251222000002_ai_media_generations_enhanced.sql) |
| `ai_video_generations` | `TABLE` | [`supabase/migrations/20251222000001_ai_video_generations.sql`](supabase/migrations/20251222000001_ai_video_generations.sql) |
| `analytics_checkbacks` | `TABLE` | [`supabase/migrations/20260113000000_twitter_campaign_system.sql`](supabase/migrations/20260113000000_twitter_campaign_system.sql) |
| `analytics_feedback` | `TABLE` | [`Backend/database/migrations/001_orchestrator_tables.sql`](Backend/database/migrations/001_orchestrator_tables.sql) |
| `analytics_feedback` | `TABLE` | [`Backend/database/migrations/001_orchestrator_tables_no_triggers.sql`](Backend/database/migrations/001_orchestrator_tables_no_triggers.sql) |
| `analytics_fetch_jobs` | `TABLE` | [`Backend/migrations/comprehensive_social_schema.sql`](Backend/migrations/comprehensive_social_schema.sql) |
| `analytics_fetch_jobs` | `TABLE` | [`Backend/migrations/social_media_analytics.sql`](Backend/migrations/social_media_analytics.sql) |
| `analyzed_videos` | `TABLE` | [`Backend/database/migrations/004_content_intelligence_video_analysis.sql`](Backend/database/migrations/004_content_intelligence_video_analysis.sql) |
| `analyzed_videos` | `TABLE` | [`Backend/supabase/migrations/20260131_add_missing_tables.sql`](Backend/supabase/migrations/20260131_add_missing_tables.sql) |
| `analyzed_videos` | `TABLE` | [`supabase/migrations/20250121000005_content_intelligence_video_analysis.sql`](supabase/migrations/20250121000005_content_intelligence_video_analysis.sql) |
| `api_usage_tracking` | `TABLE` | [`Backend/migrations/comprehensive_social_schema.sql`](Backend/migrations/comprehensive_social_schema.sql) |
| `api_usage_tracking` | `TABLE` | [`Backend/migrations/social_media_analytics.sql`](Backend/migrations/social_media_analytics.sql) |
| `appstore_metrics` | `TABLE` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `appstore_rankings` | `TABLE` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `appstore_reviews` | `TABLE` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `attribution_touchpoints` | `TABLE` | [`Backend/database/migrations/015_growth_data_plane.sql`](Backend/database/migrations/015_growth_data_plane.sql) |
| `auto_comments` | `TABLE` | [`Backend/database/migrations/013_auto_comment_tracking.sql`](Backend/database/migrations/013_auto_comment_tracking.sql) |
| `automation_actions` | `TABLE` | [`Backend/migrations/add_automation_features.sql`](Backend/migrations/add_automation_features.sql) |
| `automation_actions` | `TABLE` | [`supabase/migrations_disabled/20251207000000_automation_features.sql`](supabase/migrations_disabled/20251207000000_automation_features.sql) |
| `automation_runs` | `TABLE` | [`Backend/migrations/003_create_automation_registry.sql`](Backend/migrations/003_create_automation_registry.sql) |
| `automations` | `TABLE` | [`Backend/migrations/003_create_automation_registry.sql`](Backend/migrations/003_create_automation_registry.sql) |
| `background_jobs` | `TABLE` | [`Backend/supabase/migrations/20260120_background_jobs.sql`](Backend/supabase/migrations/20260120_background_jobs.sql) |
| `background_jobs` | `TABLE` | [`supabase/migrations/20251227_create_background_jobs.sql`](supabase/migrations/20251227_create_background_jobs.sql) |
| `beat_sheet` | `TABLE` | [`supabase/migrations/20250122000010_content_pipeline_schema.sql`](supabase/migrations/20250122000010_content_pipeline_schema.sql) |
| `brands` | `TABLE` | [`Backend/supabase/migrations/20260119_content_ops_entities.sql`](Backend/supabase/migrations/20260119_content_ops_entities.sql) |
| `brands` | `TABLE` | [`supabase/migrations/20260118000000_content_ops_entities.sql`](supabase/migrations/20260118000000_content_ops_entities.sql) |
| `briefs` | `TABLE` | [`Backend/migrations/trend_intelligence_v1.sql`](Backend/migrations/trend_intelligence_v1.sql) |
| `c2_job_events` | `TABLE` | [`supabase/migrations/20260131000001_c2_control_plane_tables.sql`](supabase/migrations/20260131000001_c2_control_plane_tables.sql) |
| `c2_jobs` | `TABLE` | [`supabase/migrations/20260131000001_c2_control_plane_tables.sql`](supabase/migrations/20260131000001_c2_control_plane_tables.sql) |
| `campaign_analytics` | `TABLE` | [`Backend/database/migrations/015_offer_tracking.sql`](Backend/database/migrations/015_offer_tracking.sql) |
| `campaign_analytics` | `TABLE` | [`supabase/migrations/20250127000000_offer_tracking.sql`](supabase/migrations/20250127000000_offer_tracking.sql) |
| `campaign_cycles` | `TABLE` | [`supabase/migrations/20260113000000_twitter_campaign_system.sql`](supabase/migrations/20260113000000_twitter_campaign_system.sql) |
| `campaign_products` | `TABLE` | [`supabase/migrations/20260113000000_twitter_campaign_system.sql`](supabase/migrations/20260113000000_twitter_campaign_system.sql) |
| `character_assets` | `TABLE` | [`Backend/supabase/migrations/20260120_character_assets.sql`](Backend/supabase/migrations/20260120_character_assets.sql) |
| `character_variants` | `TABLE` | [`Backend/supabase/migrations/20260120_character_assets.sql`](Backend/supabase/migrations/20260120_character_assets.sql) |
| `clip_posts` | `TABLE` | [`Backend/database/migrations/005_video_clips.sql`](Backend/database/migrations/005_video_clips.sql) |
| `clip_posts` | `TABLE` | [`supabase/migrations/20250121000011_video_clips.sql`](supabase/migrations/20250121000011_video_clips.sql) |
| `clip_styles` | `TABLE` | [`Backend/migrations/phase_1_essentials.sql`](Backend/migrations/phase_1_essentials.sql) |
| `clip_tags` | `TABLE` | [`Backend/database/schema.sql`](Backend/database/schema.sql) |
| `clips` | `TABLE` | [`Backend/database/migrations/003_base_video_tables.sql`](Backend/database/migrations/003_base_video_tables.sql) |
| `clips` | `TABLE` | [`Backend/database/schema.sql`](Backend/database/schema.sql) |
| `clips` | `TABLE` | [`Backend/migrations/phase_1_essentials.sql`](Backend/migrations/phase_1_essentials.sql) |
| `clips` | `TABLE` | [`supabase/migrations/20250121000004_base_video_tables.sql`](supabase/migrations/20250121000004_base_video_tables.sql) |
| `cluster_lingo` | `TABLE` | [`Backend/migrations/trend_intelligence_v1.sql`](Backend/migrations/trend_intelligence_v1.sql) |
| `cluster_members` | `TABLE` | [`Backend/migrations/trend_intelligence_v1.sql`](Backend/migrations/trend_intelligence_v1.sql) |
| `comment_event` | `TABLE` | [`supabase/migrations/20250122000010_content_pipeline_schema.sql`](supabase/migrations/20250122000010_content_pipeline_schema.sql) |
| `comment_insights_snapshot` | `TABLE` | [`supabase/migrations/20250122000010_content_pipeline_schema.sql`](supabase/migrations/20250122000010_content_pipeline_schema.sql) |
| `comment_templates` | `TABLE` | [`Backend/migrations/engagement_interactions_schema.sql`](Backend/migrations/engagement_interactions_schema.sql) |
| `community_inbox_messages` | `TABLE` | [`Backend/database/migrations/011_community_inbox.sql`](Backend/database/migrations/011_community_inbox.sql) |
| `competitor_account` | `TABLE` | [`supabase/migrations/20250122000009_competitor_audit_schema.sql`](supabase/migrations/20250122000009_competitor_audit_schema.sql) |
| `competitor_accounts` | `TABLE` | [`Backend/supabase/migrations/20251226_competitor_research.sql`](Backend/supabase/migrations/20251226_competitor_research.sql) |
| `competitor_audit_report` | `TABLE` | [`supabase/migrations/20250122000009_competitor_audit_schema.sql`](supabase/migrations/20250122000009_competitor_audit_schema.sql) |
| `competitor_audit_run` | `TABLE` | [`supabase/migrations/20250122000009_competitor_audit_schema.sql`](supabase/migrations/20250122000009_competitor_audit_schema.sql) |
| `competitor_content` | `TABLE` | [`Backend/supabase/migrations/20251226_competitor_research.sql`](Backend/supabase/migrations/20251226_competitor_research.sql) |
| `competitor_deep_audit` | `TABLE` | [`supabase/migrations/20250122000009_competitor_audit_schema.sql`](supabase/migrations/20250122000009_competitor_audit_schema.sql) |
| `competitor_funnel_map` | `TABLE` | [`supabase/migrations/20250122000009_competitor_audit_schema.sql`](supabase/migrations/20250122000009_competitor_audit_schema.sql) |
| `competitor_learnings` | `TABLE` | [`Backend/supabase/migrations/20251226_competitor_research.sql`](Backend/supabase/migrations/20251226_competitor_research.sql) |
| `competitor_post` | `TABLE` | [`supabase/migrations/20250122000009_competitor_audit_schema.sql`](supabase/migrations/20250122000009_competitor_audit_schema.sql) |
| `competitor_post_ranking` | `TABLE` | [`supabase/migrations/20250122000009_competitor_audit_schema.sql`](supabase/migrations/20250122000009_competitor_audit_schema.sql) |
| `competitor_post_snapshot` | `TABLE` | [`supabase/migrations/20250122000009_competitor_audit_schema.sql`](supabase/migrations/20250122000009_competitor_audit_schema.sql) |
| `competitor_snapshots` | `TABLE` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `competitor_template_pack` | `TABLE` | [`supabase/migrations/20250122000009_competitor_audit_schema.sql`](supabase/migrations/20250122000009_competitor_audit_schema.sql) |
| `connector_configs` | `TABLE` | [`Backend/database/migrations/003_connectors.sql`](Backend/database/migrations/003_connectors.sql) |
| `connector_configs` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `connector_configs` | `TABLE` | [`supabase/migrations/20250121000003_connectors.sql`](supabase/migrations/20250121000003_connectors.sql) |
| `content_ab_tests` | `TABLE` | [`Backend/database/migrations/005_content_intelligence_platform_tracking.sql`](Backend/database/migrations/005_content_intelligence_platform_tracking.sql) |
| `content_ab_tests` | `TABLE` | [`supabase/migrations/20250121000006_content_intelligence_platform_tracking.sql`](supabase/migrations/20250121000006_content_intelligence_platform_tracking.sql) |
| `content_analysis` | `TABLE` | [`Backend/database/migrations/012_content_analysis.sql`](Backend/database/migrations/012_content_analysis.sql) |
| `content_asset` | `TABLE` | [`supabase/migrations/20250122000010_content_pipeline_schema.sql`](supabase/migrations/20250122000010_content_pipeline_schema.sql) |
| `content_experiments` | `TABLE` | [`Backend/database/migrations/002_content_graph_extensions.sql`](Backend/database/migrations/002_content_graph_extensions.sql) |
| `content_experiments` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `content_experiments` | `TABLE` | [`supabase/migrations/20250121000002_content_graph_extensions.sql`](supabase/migrations/20250121000002_content_graph_extensions.sql) |
| `content_experiments` | `TABLE` | [`supabase/migrations/20251123143004_content_metrics.sql`](supabase/migrations/20251123143004_content_metrics.sql) |
| `content_frameworks` | `TABLE` | [`supabase/migrations_disabled/20251223000004_experiments_scheduler.sql`](supabase/migrations_disabled/20251223000004_experiments_scheduler.sql) |
| `content_gap_analysis` | `TABLE` | [`supabase/migrations/20260205000000_instagram_research_enhancements.sql`](supabase/migrations/20260205000000_instagram_research_enhancements.sql) |
| `content_insights` | `TABLE` | [`Backend/database/migrations/006_content_intelligence_insights_metrics.sql`](Backend/database/migrations/006_content_intelligence_insights_metrics.sql) |
| `content_insights` | `TABLE` | [`supabase/migrations/20250121000007_content_intelligence_insights_metrics.sql`](supabase/migrations/20250121000007_content_intelligence_insights_metrics.sql) |
| `content_items` | `TABLE` | [`Backend/database/migrations/000_content_base_tables.sql`](Backend/database/migrations/000_content_base_tables.sql) |
| `content_items` | `TABLE` | [`Backend/migrations/add_content_and_engagement_tracking.sql`](Backend/migrations/add_content_and_engagement_tracking.sql) |
| `content_items` | `TABLE` | [`Backend/migrations/add_content_cross_platform.sql`](Backend/migrations/add_content_cross_platform.sql) |
| `content_items` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `content_items` | `TABLE` | [`Backend/migrations/phase_1_essentials.sql`](Backend/migrations/phase_1_essentials.sql) |
| `content_items` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `content_items` | `TABLE` | [`supabase/migrations/20250121000000_content_base_tables.sql`](supabase/migrations/20250121000000_content_base_tables.sql) |
| `content_items` | `TABLE` | [`supabase/migrations/20251123143003_content_core.sql`](supabase/migrations/20251123143003_content_core.sql) |
| `content_metrics` | `TABLE` | [`Backend/database/migrations/000_content_base_tables.sql`](Backend/database/migrations/000_content_base_tables.sql) |
| `content_metrics` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `content_metrics` | `TABLE` | [`supabase/migrations/20250121000000_content_base_tables.sql`](supabase/migrations/20250121000000_content_base_tables.sql) |
| `content_metrics` | `TABLE` | [`supabase/migrations/20251123143004_content_metrics.sql`](supabase/migrations/20251123143004_content_metrics.sql) |
| `content_mix_plans` | `TABLE` | [`Backend/migrations/content_mix_planner_schema.sql`](Backend/migrations/content_mix_planner_schema.sql) |
| `content_mix_slots` | `TABLE` | [`Backend/migrations/content_mix_planner_schema.sql`](Backend/migrations/content_mix_planner_schema.sql) |
| `content_music_library` | `TABLE` | [`supabase/migrations/20260113010000_visual_content_campaigns.sql`](supabase/migrations/20260113010000_visual_content_campaigns.sql) |
| `content_patterns` | `TABLE` | [`supabase/migrations_disabled/20251223000004_experiments_scheduler.sql`](supabase/migrations_disabled/20251223000004_experiments_scheduler.sql) |
| `content_patterns` | `TABLE` | [`supabase/migrations_disabled/20251223000008_experiments_scheduler_schema.sql`](supabase/migrations_disabled/20251223000008_experiments_scheduler_schema.sql) |
| `content_performance_insights` | `TABLE` | [`supabase/migrations/20260113000000_twitter_campaign_system.sql`](supabase/migrations/20260113000000_twitter_campaign_system.sql) |
| `content_plans` | `TABLE` | [`supabase/migrations/20260118000000_content_ops_entities.sql`](supabase/migrations/20260118000000_content_ops_entities.sql) |
| `content_posts` | `TABLE` | [`Backend/migrations/add_content_and_engagement_tracking.sql`](Backend/migrations/add_content_and_engagement_tracking.sql) |
| `content_posts` | `TABLE` | [`Backend/migrations/add_content_cross_platform.sql`](Backend/migrations/add_content_cross_platform.sql) |
| `content_predictions` | `TABLE` | [`Backend/database/migrations/006_content_intelligence_insights_metrics.sql`](Backend/database/migrations/006_content_intelligence_insights_metrics.sql) |
| `content_predictions` | `TABLE` | [`supabase/migrations/20250121000007_content_intelligence_insights_metrics.sql`](supabase/migrations/20250121000007_content_intelligence_insights_metrics.sql) |
| `content_quality_scores` | `TABLE` | [`Backend/database/migrations/006_content_intelligence_insights_metrics.sql`](Backend/database/migrations/006_content_intelligence_insights_metrics.sql) |
| `content_quality_scores` | `TABLE` | [`supabase/migrations/20250121000007_content_intelligence_insights_metrics.sql`](supabase/migrations/20250121000007_content_intelligence_insights_metrics.sql) |
| `content_recommendations` | `TABLE` | [`Backend/database/migrations/006_content_intelligence_insights_metrics.sql`](Backend/database/migrations/006_content_intelligence_insights_metrics.sql) |
| `content_recommendations` | `TABLE` | [`supabase/migrations/20250121000007_content_intelligence_insights_metrics.sql`](supabase/migrations/20250121000007_content_intelligence_insights_metrics.sql) |
| `content_rollups` | `TABLE` | [`Backend/database/migrations/002_content_graph_extensions.sql`](Backend/database/migrations/002_content_graph_extensions.sql) |
| `content_rollups` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `content_rollups` | `TABLE` | [`supabase/migrations/20250121000002_content_graph_extensions.sql`](supabase/migrations/20250121000002_content_graph_extensions.sql) |
| `content_rollups` | `TABLE` | [`supabase/migrations/20251123143004_content_metrics.sql`](supabase/migrations/20251123143004_content_metrics.sql) |
| `content_scores` | `TABLE` | [`Backend/database/migrations/014_brand_ops_engagement.sql`](Backend/database/migrations/014_brand_ops_engagement.sql) |
| `content_sentiment` | `TABLE` | [`Backend/migrations/narrative_builder_schema.sql`](Backend/migrations/narrative_builder_schema.sql) |
| `content_slots` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `content_slots` | `TABLE` | [`supabase/migrations/20260118000000_content_ops_entities.sql`](supabase/migrations/20260118000000_content_ops_entities.sql) |
| `content_tags` | `TABLE` | [`Backend/database/schema.sql`](Backend/database/schema.sql) |
| `content_tags` | `TABLE` | [`Backend/migrations/add_content_and_engagement_tracking.sql`](Backend/migrations/add_content_and_engagement_tracking.sql) |
| `content_tags` | `TABLE` | [`Backend/migrations/add_content_cross_platform.sql`](Backend/migrations/add_content_cross_platform.sql) |
| `content_templates` | `TABLE` | [`Backend/supabase/migrations/20260119_content_ops_entities.sql`](Backend/supabase/migrations/20260119_content_ops_entities.sql) |
| `content_templates` | `TABLE` | [`supabase/migrations/20260118000000_content_ops_entities.sql`](supabase/migrations/20260118000000_content_ops_entities.sql) |
| `content_variants` | `TABLE` | [`Backend/database/migrations/000_content_base_tables.sql`](Backend/database/migrations/000_content_base_tables.sql) |
| `content_variants` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `content_variants` | `TABLE` | [`supabase/migrations/20250121000000_content_base_tables.sql`](supabase/migrations/20250121000000_content_base_tables.sql) |
| `content_variants` | `TABLE` | [`supabase/migrations/20251123143003_content_core.sql`](supabase/migrations/20251123143003_content_core.sql) |
| `copy_plan` | `TABLE` | [`supabase/migrations/20250122000010_content_pipeline_schema.sql`](supabase/migrations/20250122000010_content_pipeline_schema.sql) |
| `creative_asset_metrics` | `TABLE` | [`Backend/migrations/narrative_builder_schema.sql`](Backend/migrations/narrative_builder_schema.sql) |
| `creative_assets` | `TABLE` | [`Backend/database/migrations/add_content_performance_fields.sql`](Backend/database/migrations/add_content_performance_fields.sql) |
| `creative_features` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `creator_profiles` | `TABLE` | [`supabase/migrations/20260118000000_content_ops_entities.sql`](supabase/migrations/20260118000000_content_ops_entities.sql) |
| `deals` | `TABLE` | [`Backend/database/migrations/015_growth_data_plane.sql`](Backend/database/migrations/015_growth_data_plane.sql) |
| `deep_audit` | `TABLE` | [`supabase/migrations/20250122000010_content_pipeline_schema.sql`](supabase/migrations/20250122000010_content_pipeline_schema.sql) |
| `deletion_audit` | `TABLE` | [`supabase/migrations/20250122000002_add_curation_sentiment_columns.sql`](supabase/migrations/20250122000002_add_curation_sentiment_columns.sql) |
| `derived_metrics` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `email_events` | `TABLE` | [`Backend/database/migrations/015_growth_data_plane.sql`](Backend/database/migrations/015_growth_data_plane.sql) |
| `email_messages` | `TABLE` | [`Backend/database/migrations/015_growth_data_plane.sql`](Backend/database/migrations/015_growth_data_plane.sql) |
| `engagement_actions` | `TABLE` | [`Backend/database/migrations/014_brand_ops_engagement.sql`](Backend/database/migrations/014_brand_ops_engagement.sql) |
| `engagement_comments` | `TABLE` | [`supabase/migrations/20260125_engagement_tracking.sql`](supabase/migrations/20260125_engagement_tracking.sql) |
| `engagement_daily_stats` | `TABLE` | [`Backend/database/migrations/014_brand_ops_engagement.sql`](Backend/database/migrations/014_brand_ops_engagement.sql) |
| `engagement_interactions` | `TABLE` | [`Backend/migrations/engagement_interactions_schema.sql`](Backend/migrations/engagement_interactions_schema.sql) |
| `engagement_limits` | `TABLE` | [`supabase/migrations/20260125_engagement_tracking.sql`](supabase/migrations/20260125_engagement_tracking.sql) |
| `engagement_sessions` | `TABLE` | [`Backend/migrations/engagement_interactions_schema.sql`](Backend/migrations/engagement_interactions_schema.sql) |
| `engagement_state` | `TABLE` | [`Backend/migrations/engagement_state_persistence.sql`](Backend/migrations/engagement_state_persistence.sql) |
| `event_history` | `TABLE` | [`supabase/migrations/20251225000000_event_history.sql`](supabase/migrations/20251225000000_event_history.sql) |
| `experiment_agent_actions` | `TABLE` | [`supabase/migrations_disabled/20251223000004_experiments_scheduler.sql`](supabase/migrations_disabled/20251223000004_experiments_scheduler.sql) |
| `experiment_variants` | `TABLE` | [`supabase/migrations_disabled/20251223000008_experiments_scheduler_schema.sql`](supabase/migrations_disabled/20251223000008_experiments_scheduler_schema.sql) |
| `experiment_winners` | `TABLE` | [`supabase/migrations_disabled/20251223000004_experiments_scheduler.sql`](supabase/migrations_disabled/20251223000004_experiments_scheduler.sql) |
| `experiment_winners` | `TABLE` | [`supabase/migrations_disabled/20251223000008_experiments_scheduler_schema.sql`](supabase/migrations_disabled/20251223000008_experiments_scheduler_schema.sql) |
| `experiments` | `TABLE` | [`supabase/migrations_disabled/20251223000004_experiments_scheduler.sql`](supabase/migrations_disabled/20251223000004_experiments_scheduler.sql) |
| `experiments` | `TABLE` | [`supabase/migrations_disabled/20251223000008_experiments_scheduler_schema.sql`](supabase/migrations_disabled/20251223000008_experiments_scheduler_schema.sql) |
| `external_identities` | `TABLE` | [`Backend/database/migrations/015_growth_data_plane.sql`](Backend/database/migrations/015_growth_data_plane.sql) |
| `follower_engagement_scores` | `TABLE` | [`Backend/migrations/add_content_and_engagement_tracking.sql`](Backend/migrations/add_content_and_engagement_tracking.sql) |
| `follower_interactions` | `TABLE` | [`Backend/migrations/add_content_and_engagement_tracking.sql`](Backend/migrations/add_content_and_engagement_tracking.sql) |
| `followers` | `TABLE` | [`Backend/migrations/add_content_and_engagement_tracking.sql`](Backend/migrations/add_content_and_engagement_tracking.sql) |
| `format_runs` | `TABLE` | [`supabase/migrations/20250122000014_formats_system.sql`](supabase/migrations/20250122000014_formats_system.sql) |
| `format_templates` | `TABLE` | [`Backend/migrations/trend_intelligence_v1.sql`](Backend/migrations/trend_intelligence_v1.sql) |
| `format_triggers` | `TABLE` | [`supabase/migrations/20250122000014_formats_system.sql`](supabase/migrations/20250122000014_formats_system.sql) |
| `formats` | `TABLE` | [`supabase/migrations/20250122000014_formats_system.sql`](supabase/migrations/20250122000014_formats_system.sql) |
| `highlights` | `TABLE` | [`Backend/database/schema.sql`](Backend/database/schema.sql) |
| `hook_patterns` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `hydration_snapshots` | `TABLE` | [`supabase/migrations/20251222100000_account_roles_knowledge_base.sql`](supabase/migrations/20251222100000_account_roles_knowledge_base.sql) |
| `hypotheses` | `TABLE` | [`supabase/migrations_disabled/20251223000004_experiments_scheduler.sql`](supabase/migrations_disabled/20251223000004_experiments_scheduler.sql) |
| `hypotheses` | `TABLE` | [`supabase/migrations_disabled/20251223000008_experiments_scheduler_schema.sql`](supabase/migrations_disabled/20251223000008_experiments_scheduler_schema.sql) |
| `icps` | `TABLE` | [`Backend/supabase/migrations/20260119_content_ops_entities.sql`](Backend/supabase/migrations/20260119_content_ops_entities.sql) |
| `icps` | `TABLE` | [`supabase/migrations/20260118000000_content_ops_entities.sql`](supabase/migrations/20260118000000_content_ops_entities.sql) |
| `identities` | `TABLE` | [`Backend/database/migrations/001_people_graph.sql`](Backend/database/migrations/001_people_graph.sql) |
| `identities` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `identities` | `TABLE` | [`supabase/migrations/20250121000001_people_graph.sql`](supabase/migrations/20250121000001_people_graph.sql) |
| `identities` | `TABLE` | [`supabase/migrations/20251123143001_core_people.sql`](supabase/migrations/20251123143001_core_people.sql) |
| `ig_analysis_jobs` | `TABLE` | [`supabase/migrations/20250101000000_create_instagram_tables.sql`](supabase/migrations/20250101000000_create_instagram_tables.sql) |
| `ig_audio` | `TABLE` | [`supabase/migrations/20250101000000_create_instagram_tables.sql`](supabase/migrations/20250101000000_create_instagram_tables.sql) |
| `ig_connections` | `TABLE` | [`Backend/database/migrations/003_connectors.sql`](Backend/database/migrations/003_connectors.sql) |
| `ig_connections` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `ig_connections` | `TABLE` | [`supabase/migrations/20250121000003_connectors.sql`](supabase/migrations/20250121000003_connectors.sql) |
| `ig_hashtags` | `TABLE` | [`supabase/migrations/20250101000000_create_instagram_tables.sql`](supabase/migrations/20250101000000_create_instagram_tables.sql) |
| `ig_media` | `TABLE` | [`supabase/migrations/20250101000000_create_instagram_tables.sql`](supabase/migrations/20250101000000_create_instagram_tables.sql) |
| `ig_profiles` | `TABLE` | [`supabase/migrations/20250101000000_create_instagram_tables.sql`](supabase/migrations/20250101000000_create_instagram_tables.sql) |
| `inbox_analytics` | `TABLE` | [`Backend/database/migrations/011_community_inbox.sql`](Backend/database/migrations/011_community_inbox.sql) |
| `inbox_auto_reply_rules` | `TABLE` | [`Backend/database/migrations/011_community_inbox.sql`](Backend/database/migrations/011_community_inbox.sql) |
| `inbox_conversations` | `TABLE` | [`Backend/database/migrations/011_community_inbox.sql`](Backend/database/migrations/011_community_inbox.sql) |
| `inbox_response_templates` | `TABLE` | [`Backend/database/migrations/011_community_inbox.sql`](Backend/database/migrations/011_community_inbox.sql) |
| `industry_benchmarks` | `TABLE` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `influencer_analysis_reports` | `TABLE` | [`supabase/migrations/20250122000015_influencer_analysis.sql`](supabase/migrations/20250122000015_influencer_analysis.sql) |
| `insights` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `instagram_trending_music` | `TABLE` | [`supabase/migrations/20250122000016_instagram_trending_music.sql`](supabase/migrations/20250122000016_instagram_trending_music.sql) |
| `kb_constraints` | `TABLE` | [`supabase/migrations/20251222100000_account_roles_knowledge_base.sql`](supabase/migrations/20251222100000_account_roles_knowledge_base.sql) |
| `kb_playbooks` | `TABLE` | [`supabase/migrations/20251222100000_account_roles_knowledge_base.sql`](supabase/migrations/20251222100000_account_roles_knowledge_base.sql) |
| `kb_rules` | `TABLE` | [`supabase/migrations/20251222100000_account_roles_knowledge_base.sql`](supabase/migrations/20251222100000_account_roles_knowledge_base.sql) |
| `kb_templates` | `TABLE` | [`supabase/migrations/20251222100000_account_roles_knowledge_base.sql`](supabase/migrations/20251222100000_account_roles_knowledge_base.sql) |
| `learnings` | `TABLE` | [`supabase/migrations_disabled/20251223000007_narrative_scheduler.sql`](supabase/migrations_disabled/20251223000007_narrative_scheduler.sql) |
| `media_creation_assets` | `TABLE` | [`Backend/database/migrations/008_media_creation_types.sql`](Backend/database/migrations/008_media_creation_types.sql) |
| `media_creation_projects` | `TABLE` | [`Backend/database/migrations/008_media_creation_types.sql`](Backend/database/migrations/008_media_creation_types.sql) |
| `media_creation_templates` | `TABLE` | [`Backend/database/migrations/008_media_creation_types.sql`](Backend/database/migrations/008_media_creation_types.sql) |
| `message_templates` | `TABLE` | [`Backend/migrations/add_automation_features.sql`](Backend/migrations/add_automation_features.sql) |
| `message_templates` | `TABLE` | [`supabase/migrations_disabled/20251207000000_automation_features.sql`](supabase/migrations_disabled/20251207000000_automation_features.sql) |
| `metric_snapshots` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `music_tracks` | `TABLE` | [`Backend/supabase/migrations/20260120_music_tracks.sql`](Backend/supabase/migrations/20260120_music_tracks.sql) |
| `narrative_goals` | `TABLE` | [`Backend/migrations/narrative_builder_schema.sql`](Backend/migrations/narrative_builder_schema.sql) |
| `narrative_goals` | `TABLE` | [`supabase/migrations/20251222100000_account_roles_knowledge_base.sql`](supabase/migrations/20251222100000_account_roles_knowledge_base.sql) |
| `narrative_goals` | `TABLE` | [`supabase/migrations_disabled/20251223000007_narrative_scheduler.sql`](supabase/migrations_disabled/20251223000007_narrative_scheduler.sql) |
| `narrative_pillars` | `TABLE` | [`supabase/migrations_disabled/20251223000007_narrative_scheduler.sql`](supabase/migrations_disabled/20251223000007_narrative_scheduler.sql) |
| `offer_campaigns` | `TABLE` | [`Backend/database/migrations/015_offer_tracking.sql`](Backend/database/migrations/015_offer_tracking.sql) |
| `offer_campaigns` | `TABLE` | [`supabase/migrations/20250127000000_offer_tracking.sql`](supabase/migrations/20250127000000_offer_tracking.sql) |
| `offer_conversions` | `TABLE` | [`Backend/database/migrations/015_offer_tracking.sql`](Backend/database/migrations/015_offer_tracking.sql) |
| `offer_conversions` | `TABLE` | [`supabase/migrations/20250127000000_offer_tracking.sql`](supabase/migrations/20250127000000_offer_tracking.sql) |
| `offer_conversions` | `TABLE` | [`supabase/migrations/20250127000000_orchestrator_pipelines.sql`](supabase/migrations/20250127000000_orchestrator_pipelines.sql) |
| `offer_traffic` | `TABLE` | [`Backend/database/migrations/015_offer_tracking.sql`](Backend/database/migrations/015_offer_tracking.sql) |
| `offer_traffic` | `TABLE` | [`supabase/migrations/20250127000000_offer_tracking.sql`](supabase/migrations/20250127000000_offer_tracking.sql) |
| `offer_traffic` | `TABLE` | [`supabase/migrations/20250127000000_orchestrator_pipelines.sql`](supabase/migrations/20250127000000_orchestrator_pipelines.sql) |
| `offer_traffic_tracking` | `TABLE` | [`Backend/database/migrations/001_orchestrator_tables.sql`](Backend/database/migrations/001_orchestrator_tables.sql) |
| `offer_traffic_tracking` | `TABLE` | [`Backend/database/migrations/001_orchestrator_tables_no_triggers.sql`](Backend/database/migrations/001_orchestrator_tables_no_triggers.sql) |
| `offers` | `TABLE` | [`Backend/supabase/migrations/20260119_content_ops_entities.sql`](Backend/supabase/migrations/20260119_content_ops_entities.sql) |
| `offers` | `TABLE` | [`supabase/migrations/20260118000000_content_ops_entities.sql`](supabase/migrations/20260118000000_content_ops_entities.sql) |
| `orchestrator_pipeline_steps` | `TABLE` | [`Backend/database/migrations/001_orchestrator_tables.sql`](Backend/database/migrations/001_orchestrator_tables.sql) |
| `orchestrator_pipeline_steps` | `TABLE` | [`Backend/database/migrations/001_orchestrator_tables_no_triggers.sql`](Backend/database/migrations/001_orchestrator_tables_no_triggers.sql) |
| `orchestrator_pipeline_steps` | `TABLE` | [`supabase/migrations/20250127000000_orchestrator_pipelines.sql`](supabase/migrations/20250127000000_orchestrator_pipelines.sql) |
| `orchestrator_pipeline_steps` | `TABLE` | [`supabase/migrations/20250127000001_orchestrator_pipelines.sql`](supabase/migrations/20250127000001_orchestrator_pipelines.sql) |
| `orchestrator_pipelines` | `TABLE` | [`Backend/database/migrations/001_orchestrator_tables.sql`](Backend/database/migrations/001_orchestrator_tables.sql) |
| `orchestrator_pipelines` | `TABLE` | [`Backend/database/migrations/001_orchestrator_tables_no_triggers.sql`](Backend/database/migrations/001_orchestrator_tables_no_triggers.sql) |
| `orchestrator_pipelines` | `TABLE` | [`supabase/migrations/20250127000000_orchestrator_pipelines.sql`](supabase/migrations/20250127000000_orchestrator_pipelines.sql) |
| `orchestrator_pipelines` | `TABLE` | [`supabase/migrations/20250127000001_orchestrator_pipelines.sql`](supabase/migrations/20250127000001_orchestrator_pipelines.sql) |
| `original_videos` | `TABLE` | [`Backend/database/migrations/003_base_video_tables.sql`](Backend/database/migrations/003_base_video_tables.sql) |
| `original_videos` | `TABLE` | [`Backend/database/schema.sql`](Backend/database/schema.sql) |
| `original_videos` | `TABLE` | [`Backend/supabase/migrations/20260131_add_missing_tables.sql`](Backend/supabase/migrations/20260131_add_missing_tables.sql) |
| `original_videos` | `TABLE` | [`supabase/migrations/20250121000004_base_video_tables.sql`](supabase/migrations/20250121000004_base_video_tables.sql) |
| `outbound_messages` | `TABLE` | [`Backend/database/migrations/001_people_graph.sql`](Backend/database/migrations/001_people_graph.sql) |
| `outbound_messages` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `outbound_messages` | `TABLE` | [`supabase/migrations/20250121000001_people_graph.sql`](supabase/migrations/20250121000001_people_graph.sql) |
| `outbound_messages` | `TABLE` | [`supabase/migrations/20251123143002_insights_segments.sql`](supabase/migrations/20251123143002_insights_segments.sql) |
| `people` | `TABLE` | [`Backend/database/migrations/001_people_graph.sql`](Backend/database/migrations/001_people_graph.sql) |
| `people` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `people` | `TABLE` | [`supabase/migrations/20250121000001_people_graph.sql`](supabase/migrations/20250121000001_people_graph.sql) |
| `people` | `TABLE` | [`supabase/migrations/20251123143001_core_people.sql`](supabase/migrations/20251123143001_core_people.sql) |
| `performance_benchmarks` | `TABLE` | [`supabase/migrations/20260205000000_instagram_research_enhancements.sql`](supabase/migrations/20260205000000_instagram_research_enhancements.sql) |
| `performance_metrics` | `TABLE` | [`Backend/database/schema.sql`](Backend/database/schema.sql) |
| `person_events` | `TABLE` | [`Backend/database/migrations/001_people_graph.sql`](Backend/database/migrations/001_people_graph.sql) |
| `person_events` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `person_events` | `TABLE` | [`supabase/migrations/20250121000001_people_graph.sql`](supabase/migrations/20250121000001_people_graph.sql) |
| `person_events` | `TABLE` | [`supabase/migrations/20251123143001_core_people.sql`](supabase/migrations/20251123143001_core_people.sql) |
| `person_features` | `TABLE` | [`Backend/database/migrations/015_growth_data_plane.sql`](Backend/database/migrations/015_growth_data_plane.sql) |
| `person_insights` | `TABLE` | [`Backend/database/migrations/001_people_graph.sql`](Backend/database/migrations/001_people_graph.sql) |
| `person_insights` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `person_insights` | `TABLE` | [`supabase/migrations/20250121000001_people_graph.sql`](supabase/migrations/20250121000001_people_graph.sql) |
| `person_insights` | `TABLE` | [`supabase/migrations/20251123143002_insights_segments.sql`](supabase/migrations/20251123143002_insights_segments.sql) |
| `pipeline_runs` | `TABLE` | [`Backend/migrations/trend_intelligence_v1.sql`](Backend/migrations/trend_intelligence_v1.sql) |
| `platform_accounts` | `TABLE` | [`Backend/supabase/migrations/20260131_add_missing_tables.sql`](Backend/supabase/migrations/20260131_add_missing_tables.sql) |
| `platform_checkbacks` | `TABLE` | [`Backend/database/migrations/005_content_intelligence_platform_tracking.sql`](Backend/database/migrations/005_content_intelligence_platform_tracking.sql) |
| `platform_checkbacks` | `TABLE` | [`supabase/migrations/20250121000006_content_intelligence_platform_tracking.sql`](supabase/migrations/20250121000006_content_intelligence_platform_tracking.sql) |
| `platform_post` | `TABLE` | [`supabase/migrations/20250122000010_content_pipeline_schema.sql`](supabase/migrations/20250122000010_content_pipeline_schema.sql) |
| `platform_posts` | `TABLE` | [`Backend/database/migrations/005_content_intelligence_platform_tracking.sql`](Backend/database/migrations/005_content_intelligence_platform_tracking.sql) |
| `platform_posts` | `TABLE` | [`Backend/database/schema.sql`](Backend/database/schema.sql) |
| `platform_posts` | `TABLE` | [`supabase/migrations/20250121000006_content_intelligence_platform_tracking.sql`](supabase/migrations/20250121000006_content_intelligence_platform_tracking.sql) |
| `platform_text_constraints` | `TABLE` | [`supabase/migrations/20250122000010_content_pipeline_schema.sql`](supabase/migrations/20250122000010_content_pipeline_schema.sql) |
| `playbook_rules` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `post_comments` | `TABLE` | [`Backend/database/migrations/005_content_intelligence_platform_tracking.sql`](Backend/database/migrations/005_content_intelligence_platform_tracking.sql) |
| `post_comments` | `TABLE` | [`supabase/migrations/20250121000006_content_intelligence_platform_tracking.sql`](supabase/migrations/20250121000006_content_intelligence_platform_tracking.sql) |
| `post_enrichment` | `TABLE` | [`Backend/migrations/trend_intelligence_v1.sql`](Backend/migrations/trend_intelligence_v1.sql) |
| `post_platform_publish` | `TABLE` | [`Backend/migrations/phase_1_essentials.sql`](Backend/migrations/phase_1_essentials.sql) |
| `post_snapshot` | `TABLE` | [`supabase/migrations/20250122000010_content_pipeline_schema.sql`](supabase/migrations/20250122000010_content_pipeline_schema.sql) |
| `posted_content` | `TABLE` | [`Backend/database/migrations/add_posted_content_table.sql`](Backend/database/migrations/add_posted_content_table.sql) |
| `posted_content` | `TABLE` | [`supabase/migrations_disabled/20251223000006_posted_content_table.sql`](supabase/migrations_disabled/20251223000006_posted_content_table.sql) |
| `posted_tweets` | `TABLE` | [`supabase/migrations/20260113000000_twitter_campaign_system.sql`](supabase/migrations/20260113000000_twitter_campaign_system.sql) |
| `posted_visual_content` | `TABLE` | [`supabase/migrations/20260113010000_visual_content_campaigns.sql`](supabase/migrations/20260113010000_visual_content_campaigns.sql) |
| `posting_goals` | `TABLE` | [`supabase/migrations/20250122000000_fix_schema_mismatches.sql`](supabase/migrations/20250122000000_fix_schema_mismatches.sql) |
| `postings` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `posts` | `TABLE` | [`Backend/migrations/phase_1_essentials.sql`](Backend/migrations/phase_1_essentials.sql) |
| `posts_raw` | `TABLE` | [`Backend/migrations/trend_intelligence_v1.sql`](Backend/migrations/trend_intelligence_v1.sql) |
| `processing_jobs` | `TABLE` | [`Backend/database/schema.sql`](Backend/database/schema.sql) |
| `processing_jobs` | `TABLE` | [`supabase/migrations/20250122000000_fix_schema_mismatches.sql`](supabase/migrations/20250122000000_fix_schema_mismatches.sql) |
| `prompt_runs` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `prompt_runs` | `TABLE` | [`supabase/migrations/20260118000000_content_ops_entities.sql`](supabase/migrations/20260118000000_content_ops_entities.sql) |
| `prompt_templates` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `prompt_versions` | `TABLE` | [`Backend/database/migrations/014_brand_ops_engagement.sql`](Backend/database/migrations/014_brand_ops_engagement.sql) |
| `publishing_queue` | `TABLE` | [`Backend/database/migrations/007_publishing_queue.sql`](Backend/database/migrations/007_publishing_queue.sql) |
| `publishing_queue` | `TABLE` | [`supabase/migrations/20250121000013_publishing_queue.sql`](supabase/migrations/20250121000013_publishing_queue.sql) |
| `quality_profiles` | `TABLE` | [`supabase/migrations/20250122000014_formats_system.sql`](supabase/migrations/20250122000014_formats_system.sql) |
| `remotion_render_spec` | `TABLE` | [`supabase/migrations/20250122000010_content_pipeline_schema.sql`](supabase/migrations/20250122000010_content_pipeline_schema.sql) |
| `render_jobs` | `TABLE` | [`Backend/migrations/trend_intelligence_v1.sql`](Backend/migrations/trend_intelligence_v1.sql) |
| `repurpose_clips` | `TABLE` | [`Backend/migrations/002_create_repurpose_tables.sql`](Backend/migrations/002_create_repurpose_tables.sql) |
| `repurpose_renders` | `TABLE` | [`Backend/migrations/002_create_repurpose_tables.sql`](Backend/migrations/002_create_repurpose_tables.sql) |
| `repurpose_sources` | `TABLE` | [`Backend/migrations/002_create_repurpose_tables.sql`](Backend/migrations/002_create_repurpose_tables.sql) |
| `repurpose_transcripts` | `TABLE` | [`Backend/migrations/002_create_repurpose_tables.sql`](Backend/migrations/002_create_repurpose_tables.sql) |
| `retention_events` | `TABLE` | [`Backend/database/migrations/005_content_intelligence_platform_tracking.sql`](Backend/database/migrations/005_content_intelligence_platform_tracking.sql) |
| `retention_events` | `TABLE` | [`supabase/migrations/20250121000006_content_intelligence_platform_tracking.sql`](supabase/migrations/20250121000006_content_intelligence_platform_tracking.sql) |
| `retention_series` | `TABLE` | [`supabase/migrations/20250122000010_content_pipeline_schema.sql`](supabase/migrations/20250122000010_content_pipeline_schema.sql) |
| `review_windows` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `reviews` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `run_artifacts` | `TABLE` | [`supabase/migrations/20250122000014_formats_system.sql`](supabase/migrations/20250122000014_formats_system.sql) |
| `safari_accounts` | `TABLE` | [`Backend/supabase/migrations/20260120_safari_session_manager.sql`](Backend/supabase/migrations/20260120_safari_session_manager.sql) |
| `safari_commands` | `TABLE` | [`supabase/migrations/20260131000000_safari_automation_tables.sql`](supabase/migrations/20260131000000_safari_automation_tables.sql) |
| `safari_events` | `TABLE` | [`supabase/migrations/20260131000000_safari_automation_tables.sql`](supabase/migrations/20260131000000_safari_automation_tables.sql) |
| `safari_session_logs` | `TABLE` | [`Backend/supabase/migrations/20260120_safari_session_manager.sql`](Backend/supabase/migrations/20260120_safari_session_manager.sql) |
| `safari_sessions` | `TABLE` | [`supabase/migrations/20260131000000_safari_automation_tables.sql`](supabase/migrations/20260131000000_safari_automation_tables.sql) |
| `safari_videos` | `TABLE` | [`supabase/migrations/20260131000000_safari_automation_tables.sql`](supabase/migrations/20260131000000_safari_automation_tables.sql) |
| `saved_hooks` | `TABLE` | [`supabase/migrations/20260205000000_instagram_research_enhancements.sql`](supabase/migrations/20260205000000_instagram_research_enhancements.sql) |
| `saved_trends` | `TABLE` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `schedule_performance` | `TABLE` | [`supabase/migrations_disabled/20251223000007_narrative_scheduler.sql`](supabase/migrations_disabled/20251223000007_narrative_scheduler.sql) |
| `schedule_slots` | `TABLE` | [`supabase/migrations_disabled/20251223000007_narrative_scheduler.sql`](supabase/migrations_disabled/20251223000007_narrative_scheduler.sql) |
| `scheduled_posts` | `TABLE` | [`Backend/supabase/migrations/20260131_add_missing_tables.sql`](Backend/supabase/migrations/20260131_add_missing_tables.sql) |
| `scheduled_posts` | `TABLE` | [`supabase/migrations/20250122000000_fix_schema_mismatches.sql`](supabase/migrations/20250122000000_fix_schema_mismatches.sql) |
| `scheduled_tweets` | `TABLE` | [`supabase/migrations/20260113000000_twitter_campaign_system.sql`](supabase/migrations/20260113000000_twitter_campaign_system.sql) |
| `scheduled_visual_content` | `TABLE` | [`supabase/migrations/20260113010000_visual_content_campaigns.sql`](supabase/migrations/20260113010000_visual_content_campaigns.sql) |
| `scheduling_constraints` | `TABLE` | [`supabase/migrations_disabled/20251223000007_narrative_scheduler.sql`](supabase/migrations_disabled/20251223000007_narrative_scheduler.sql) |
| `segment_edit_history` | `TABLE` | [`Backend/database/migrations/006_segment_editing.sql`](Backend/database/migrations/006_segment_editing.sql) |
| `segment_edit_history` | `TABLE` | [`supabase/migrations/20250121000012_segment_editing.sql`](supabase/migrations/20250121000012_segment_editing.sql) |
| `segment_insights` | `TABLE` | [`Backend/database/migrations/001_people_graph.sql`](Backend/database/migrations/001_people_graph.sql) |
| `segment_insights` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `segment_insights` | `TABLE` | [`supabase/migrations/20250121000001_people_graph.sql`](supabase/migrations/20250121000001_people_graph.sql) |
| `segment_insights` | `TABLE` | [`supabase/migrations/20251123143002_insights_segments.sql`](supabase/migrations/20251123143002_insights_segments.sql) |
| `segment_members` | `TABLE` | [`Backend/database/migrations/001_people_graph.sql`](Backend/database/migrations/001_people_graph.sql) |
| `segment_members` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `segment_members` | `TABLE` | [`supabase/migrations/20250121000001_people_graph.sql`](supabase/migrations/20250121000001_people_graph.sql) |
| `segment_members` | `TABLE` | [`supabase/migrations/20251123143002_insights_segments.sql`](supabase/migrations/20251123143002_insights_segments.sql) |
| `segment_performance` | `TABLE` | [`Backend/database/migrations/006_segment_editing.sql`](Backend/database/migrations/006_segment_editing.sql) |
| `segment_performance` | `TABLE` | [`supabase/migrations/20250121000012_segment_editing.sql`](supabase/migrations/20250121000012_segment_editing.sql) |
| `segments` | `TABLE` | [`Backend/database/migrations/001_people_graph.sql`](Backend/database/migrations/001_people_graph.sql) |
| `segments` | `TABLE` | [`supabase/migrations/20241121000000_everreach_blend_schema.sql`](supabase/migrations/20241121000000_everreach_blend_schema.sql) |
| `segments` | `TABLE` | [`supabase/migrations/20250121000001_people_graph.sql`](supabase/migrations/20250121000001_people_graph.sql) |
| `segments` | `TABLE` | [`supabase/migrations/20251123143002_insights_segments.sql`](supabase/migrations/20251123143002_insights_segments.sql) |
| `shortlinks` | `TABLE` | [`supabase/migrations/20260118000000_content_ops_entities.sql`](supabase/migrations/20260118000000_content_ops_entities.sql) |
| `social_accounts` | `TABLE` | [`Backend/migrations/phase_1_essentials.sql`](Backend/migrations/phase_1_essentials.sql) |
| `social_accounts` | `TABLE` | [`supabase/migrations/20251125100000_social_accounts.sql`](supabase/migrations/20251125100000_social_accounts.sql) |
| `social_analytics_config` | `TABLE` | [`Backend/migrations/social_analytics_extension.sql`](Backend/migrations/social_analytics_extension.sql) |
| `social_analytics_config` | `TABLE` | [`supabase/migrations/20251126000000_social_analytics_extension.sql`](supabase/migrations/20251126000000_social_analytics_extension.sql) |
| `social_analytics_snapshots` | `TABLE` | [`Backend/migrations/social_analytics_extension.sql`](Backend/migrations/social_analytics_extension.sql) |
| `social_analytics_snapshots` | `TABLE` | [`supabase/migrations/20251126000000_social_analytics_extension.sql`](supabase/migrations/20251126000000_social_analytics_extension.sql) |
| `social_api_usage` | `TABLE` | [`Backend/migrations/social_analytics_extension.sql`](Backend/migrations/social_analytics_extension.sql) |
| `social_api_usage` | `TABLE` | [`supabase/migrations/20251126000000_social_analytics_extension.sql`](supabase/migrations/20251126000000_social_analytics_extension.sql) |
| `social_audience_demographics` | `TABLE` | [`Backend/migrations/social_analytics_extension.sql`](Backend/migrations/social_analytics_extension.sql) |
| `social_audience_demographics` | `TABLE` | [`supabase/migrations/20251126000000_social_analytics_extension.sql`](supabase/migrations/20251126000000_social_analytics_extension.sql) |
| `social_comments` | `TABLE` | [`Backend/migrations/social_analytics_extension.sql`](Backend/migrations/social_analytics_extension.sql) |
| `social_comments` | `TABLE` | [`supabase/migrations/20251126000000_social_analytics_extension.sql`](supabase/migrations/20251126000000_social_analytics_extension.sql) |
| `social_fetch_jobs` | `TABLE` | [`Backend/migrations/social_analytics_extension.sql`](Backend/migrations/social_analytics_extension.sql) |
| `social_fetch_jobs` | `TABLE` | [`supabase/migrations/20251126000000_social_analytics_extension.sql`](supabase/migrations/20251126000000_social_analytics_extension.sql) |
| `social_hashtags` | `TABLE` | [`Backend/migrations/social_analytics_extension.sql`](Backend/migrations/social_analytics_extension.sql) |
| `social_hashtags` | `TABLE` | [`supabase/migrations/20251126000000_social_analytics_extension.sql`](supabase/migrations/20251126000000_social_analytics_extension.sql) |
| `social_media_accounts` | `TABLE` | [`Backend/migrations/comprehensive_social_schema.sql`](Backend/migrations/comprehensive_social_schema.sql) |
| `social_media_accounts` | `TABLE` | [`Backend/migrations/social_media_analytics.sql`](Backend/migrations/social_media_analytics.sql) |
| `social_media_analytics_snapshots` | `TABLE` | [`Backend/migrations/comprehensive_social_schema.sql`](Backend/migrations/comprehensive_social_schema.sql) |
| `social_media_analytics_snapshots` | `TABLE` | [`Backend/migrations/social_media_analytics.sql`](Backend/migrations/social_media_analytics.sql) |
| `social_media_audience_demographics` | `TABLE` | [`Backend/migrations/comprehensive_social_schema.sql`](Backend/migrations/comprehensive_social_schema.sql) |
| `social_media_comments` | `TABLE` | [`Backend/migrations/comprehensive_social_schema.sql`](Backend/migrations/comprehensive_social_schema.sql) |
| `social_media_content_mapping` | `TABLE` | [`Backend/migrations/comprehensive_social_schema.sql`](Backend/migrations/comprehensive_social_schema.sql) |
| `social_media_content_mapping` | `TABLE` | [`Backend/migrations/social_media_analytics.sql`](Backend/migrations/social_media_analytics.sql) |
| `social_media_conversations` | `TABLE` | [`Backend/migrations/add_automation_features.sql`](Backend/migrations/add_automation_features.sql) |
| `social_media_conversations` | `TABLE` | [`supabase/migrations_disabled/20251207000000_automation_features.sql`](supabase/migrations_disabled/20251207000000_automation_features.sql) |
| `social_media_hashtags` | `TABLE` | [`Backend/migrations/comprehensive_social_schema.sql`](Backend/migrations/comprehensive_social_schema.sql) |
| `social_media_hashtags` | `TABLE` | [`Backend/migrations/social_media_analytics.sql`](Backend/migrations/social_media_analytics.sql) |
| `social_media_mentions` | `TABLE` | [`Backend/migrations/comprehensive_social_schema.sql`](Backend/migrations/comprehensive_social_schema.sql) |
| `social_media_messages` | `TABLE` | [`Backend/migrations/add_automation_features.sql`](Backend/migrations/add_automation_features.sql) |
| `social_media_messages` | `TABLE` | [`supabase/migrations_disabled/20251207000000_automation_features.sql`](supabase/migrations_disabled/20251207000000_automation_features.sql) |
| `social_media_post_analytics` | `TABLE` | [`Backend/migrations/comprehensive_social_schema.sql`](Backend/migrations/comprehensive_social_schema.sql) |
| `social_media_post_analytics` | `TABLE` | [`Backend/migrations/social_media_analytics.sql`](Backend/migrations/social_media_analytics.sql) |
| `social_media_post_hashtags` | `TABLE` | [`Backend/migrations/comprehensive_social_schema.sql`](Backend/migrations/comprehensive_social_schema.sql) |
| `social_media_post_hashtags` | `TABLE` | [`Backend/migrations/social_media_analytics.sql`](Backend/migrations/social_media_analytics.sql) |
| `social_media_posts` | `TABLE` | [`Backend/migrations/comprehensive_social_schema.sql`](Backend/migrations/comprehensive_social_schema.sql) |
| `social_media_posts` | `TABLE` | [`Backend/migrations/social_media_analytics.sql`](Backend/migrations/social_media_analytics.sql) |
| `social_post_hashtags` | `TABLE` | [`Backend/migrations/social_analytics_extension.sql`](Backend/migrations/social_analytics_extension.sql) |
| `social_post_hashtags` | `TABLE` | [`supabase/migrations/20251126000000_social_analytics_extension.sql`](supabase/migrations/20251126000000_social_analytics_extension.sql) |
| `social_post_metrics` | `TABLE` | [`Backend/migrations/social_analytics_extension.sql`](Backend/migrations/social_analytics_extension.sql) |
| `social_post_metrics` | `TABLE` | [`supabase/migrations/20251126000000_social_analytics_extension.sql`](supabase/migrations/20251126000000_social_analytics_extension.sql) |
| `social_posts_analytics` | `TABLE` | [`Backend/migrations/social_analytics_extension.sql`](Backend/migrations/social_analytics_extension.sql) |
| `social_posts_analytics` | `TABLE` | [`supabase/migrations/20251126000000_social_analytics_extension.sql`](supabase/migrations/20251126000000_social_analytics_extension.sql) |
| `strategy_reports` | `TABLE` | [`supabase/migrations/20260205000000_instagram_research_enhancements.sql`](supabase/migrations/20260205000000_instagram_research_enhancements.sql) |
| `subscriptions` | `TABLE` | [`Backend/database/migrations/015_growth_data_plane.sql`](Backend/database/migrations/015_growth_data_plane.sql) |
| `system_settings` | `TABLE` | [`Backend/database/schema.sql`](Backend/database/schema.sql) |
| `template_usage_log` | `TABLE` | [`supabase/migrations/20250122000013_enhanced_visual_analysis.sql`](supabase/migrations/20250122000013_enhanced_visual_analysis.sql) |
| `text_embeddings` | `TABLE` | [`Backend/migrations/trend_intelligence_v1.sql`](Backend/migrations/trend_intelligence_v1.sql) |
| `top_engaged_followers` | `TABLE` | [`Backend/database/migrations/create_top_engaged_followers.sql`](Backend/database/migrations/create_top_engaged_followers.sql) |
| `touchpoints` | `TABLE` | [`Backend/supabase/migrations/20260119_content_ops_entities.sql`](Backend/supabase/migrations/20260119_content_ops_entities.sql) |
| `touchpoints` | `TABLE` | [`supabase/migrations/20260118000000_content_ops_entities.sql`](supabase/migrations/20260118000000_content_ops_entities.sql) |
| `tracked_competitors` | `TABLE` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `trend_alerts` | `TABLE` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `trend_asset_matches` | `TABLE` | [`supabase/migrations/20251222110000_trend_opportunities.sql`](supabase/migrations/20251222110000_trend_opportunities.sql) |
| `trend_briefs` | `TABLE` | [`Backend/supabase/migrations/20251226_trend_velocity.sql`](Backend/supabase/migrations/20251226_trend_velocity.sql) |
| `trend_briefs` | `TABLE` | [`supabase/migrations/20251222110000_trend_opportunities.sql`](supabase/migrations/20251222110000_trend_opportunities.sql) |
| `trend_cards` | `TABLE` | [`supabase/migrations/20250101000000_create_instagram_tables.sql`](supabase/migrations/20250101000000_create_instagram_tables.sql) |
| `trend_clusters` | `TABLE` | [`Backend/migrations/trend_intelligence_v1.sql`](Backend/migrations/trend_intelligence_v1.sql) |
| `trend_clusters` | `TABLE` | [`supabase/migrations/20251222110000_trend_opportunities.sql`](supabase/migrations/20251222110000_trend_opportunities.sql) |
| `trend_creators` | `TABLE` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `trend_formats` | `TABLE` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `trend_hashtag_snapshots` | `TABLE` | [`Backend/supabase/migrations/20251226_trend_velocity.sql`](Backend/supabase/migrations/20251226_trend_velocity.sql) |
| `trend_hashtags` | `TABLE` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `trend_items` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `trend_items` | `TABLE` | [`supabase/migrations/20251222110000_trend_opportunities.sql`](supabase/migrations/20251222110000_trend_opportunities.sql) |
| `trend_keyword_snapshots` | `TABLE` | [`Backend/supabase/migrations/20251226_trend_velocity.sql`](Backend/supabase/migrations/20251226_trend_velocity.sql) |
| `trend_observations` | `TABLE` | [`supabase/migrations/20250101000000_create_instagram_tables.sql`](supabase/migrations/20250101000000_create_instagram_tables.sql) |
| `trend_opportunities` | `TABLE` | [`supabase/migrations/20251222110000_trend_opportunities.sql`](supabase/migrations/20251222110000_trend_opportunities.sql) |
| `trend_raw` | `TABLE` | [`supabase/migrations/20251222110000_trend_opportunities.sql`](supabase/migrations/20251222110000_trend_opportunities.sql) |
| `trend_recommendations` | `TABLE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `trend_scores` | `TABLE` | [`Backend/migrations/trend_intelligence_v1.sql`](Backend/migrations/trend_intelligence_v1.sql) |
| `trend_settings` | `TABLE` | [`supabase/migrations/20251222110000_trend_opportunities.sql`](supabase/migrations/20251222110000_trend_opportunities.sql) |
| `trend_sound_snapshots` | `TABLE` | [`Backend/supabase/migrations/20251226_trend_velocity.sql`](Backend/supabase/migrations/20251226_trend_velocity.sql) |
| `trend_sounds` | `TABLE` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `trend_topics` | `TABLE` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `trend_velocity_scores` | `TABLE` | [`Backend/supabase/migrations/20251226_trend_velocity.sql`](Backend/supabase/migrations/20251226_trend_velocity.sql) |
| `tweet_templates` | `TABLE` | [`supabase/migrations/20260113000000_twitter_campaign_system.sql`](supabase/migrations/20260113000000_twitter_campaign_system.sql) |
| `user_writing_styles` | `TABLE` | [`supabase/migrations/20260113000000_twitter_campaign_system.sql`](supabase/migrations/20260113000000_twitter_campaign_system.sql) |
| `users` | `TABLE` | [`Backend/migrations/phase_1_essentials.sql`](Backend/migrations/phase_1_essentials.sql) |
| `variant_metrics` | `TABLE` | [`Backend/migrations/narrative_builder_schema.sql`](Backend/migrations/narrative_builder_schema.sql) |
| `video_analysis` | `TABLE` | [`Backend/database/migrations/008_video_library.sql`](Backend/database/migrations/008_video_library.sql) |
| `video_analysis` | `TABLE` | [`Backend/migrations/add_video_analysis_tables.sql`](Backend/migrations/add_video_analysis_tables.sql) |
| `video_analysis` | `TABLE` | [`supabase/migrations/20250121000008_video_library.sql`](supabase/migrations/20250121000008_video_library.sql) |
| `video_assessments` | `TABLE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `video_assets` | `TABLE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `video_audio_analysis` | `TABLE` | [`Backend/migrations/add_comprehensive_viral_schema.sql`](Backend/migrations/add_comprehensive_viral_schema.sql) |
| `video_bibles` | `TABLE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `video_captions` | `TABLE` | [`Backend/database/migrations/004_content_intelligence_video_analysis.sql`](Backend/database/migrations/004_content_intelligence_video_analysis.sql) |
| `video_captions` | `TABLE` | [`supabase/migrations/20250121000005_content_intelligence_video_analysis.sql`](supabase/migrations/20250121000005_content_intelligence_video_analysis.sql) |
| `video_clip_plan_clips` | `TABLE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `video_clip_plans` | `TABLE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `video_clip_run_assets` | `TABLE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `video_clip_runs` | `TABLE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `video_clips` | `TABLE` | [`Backend/database/migrations/005_video_clips.sql`](Backend/database/migrations/005_video_clips.sql) |
| `video_clips` | `TABLE` | [`supabase/migrations/20250121000011_video_clips.sql`](supabase/migrations/20250121000011_video_clips.sql) |
| `video_content_briefs` | `TABLE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `video_copy_elements` | `TABLE` | [`Backend/migrations/add_comprehensive_viral_schema.sql`](Backend/migrations/add_comprehensive_viral_schema.sql) |
| `video_frames` | `TABLE` | [`Backend/database/migrations/004_content_intelligence_video_analysis.sql`](Backend/database/migrations/004_content_intelligence_video_analysis.sql) |
| `video_frames` | `TABLE` | [`Backend/migrations/add_comprehensive_viral_schema.sql`](Backend/migrations/add_comprehensive_viral_schema.sql) |
| `video_frames` | `TABLE` | [`supabase/migrations/20250121000005_content_intelligence_video_analysis.sql`](supabase/migrations/20250121000005_content_intelligence_video_analysis.sql) |
| `video_headlines` | `TABLE` | [`Backend/database/migrations/004_content_intelligence_video_analysis.sql`](Backend/database/migrations/004_content_intelligence_video_analysis.sql) |
| `video_headlines` | `TABLE` | [`supabase/migrations/20250121000005_content_intelligence_video_analysis.sql`](supabase/migrations/20250121000005_content_intelligence_video_analysis.sql) |
| `video_offer_analysis` | `TABLE` | [`Backend/migrations/add_comprehensive_viral_schema.sql`](Backend/migrations/add_comprehensive_viral_schema.sql) |
| `video_pattern_matches` | `TABLE` | [`Backend/migrations/add_comprehensive_viral_schema.sql`](Backend/migrations/add_comprehensive_viral_schema.sql) |
| `video_platform_intent` | `TABLE` | [`Backend/migrations/add_comprehensive_viral_schema.sql`](Backend/migrations/add_comprehensive_viral_schema.sql) |
| `video_projects` | `TABLE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `video_renders` | `TABLE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `video_repair_attempts` | `TABLE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `video_retention_events` | `TABLE` | [`Backend/migrations/add_comprehensive_viral_schema.sql`](Backend/migrations/add_comprehensive_viral_schema.sql) |
| `video_routing_log` | `TABLE` | [`supabase/migrations/20250122000008_add_video_orientation_fields.sql`](supabase/migrations/20250122000008_add_video_orientation_fields.sql) |
| `video_scene_detection` | `TABLE` | [`supabase/migrations/20250122000013_enhanced_visual_analysis.sql`](supabase/migrations/20250122000013_enhanced_visual_analysis.sql) |
| `video_scenes` | `TABLE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `video_scripts` | `TABLE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `video_segments` | `TABLE` | [`Backend/database/migrations/004_content_intelligence_video_analysis.sql`](Backend/database/migrations/004_content_intelligence_video_analysis.sql) |
| `video_segments` | `TABLE` | [`Backend/migrations/add_video_analysis_tables.sql`](Backend/migrations/add_video_analysis_tables.sql) |
| `video_segments` | `TABLE` | [`supabase/migrations/20250121000005_content_intelligence_video_analysis.sql`](supabase/migrations/20250121000005_content_intelligence_video_analysis.sql) |
| `video_template_library` | `TABLE` | [`supabase/migrations/20250122000013_enhanced_visual_analysis.sql`](supabase/migrations/20250122000013_enhanced_visual_analysis.sql) |
| `video_words` | `TABLE` | [`Backend/database/migrations/004_content_intelligence_video_analysis.sql`](Backend/database/migrations/004_content_intelligence_video_analysis.sql) |
| `video_words` | `TABLE` | [`Backend/migrations/add_comprehensive_viral_schema.sql`](Backend/migrations/add_comprehensive_viral_schema.sql) |
| `video_words` | `TABLE` | [`supabase/migrations/20250121000005_content_intelligence_video_analysis.sql`](supabase/migrations/20250121000005_content_intelligence_video_analysis.sql) |
| `videos` | `TABLE` | [`Backend/database/migrations/008_video_library.sql`](Backend/database/migrations/008_video_library.sql) |
| `videos` | `TABLE` | [`supabase/migrations/20250121000008_video_library.sql`](supabase/migrations/20250121000008_video_library.sql) |
| `viral_patterns` | `TABLE` | [`Backend/migrations/add_comprehensive_viral_schema.sql`](Backend/migrations/add_comprehensive_viral_schema.sql) |
| `visual_campaign_cycles` | `TABLE` | [`supabase/migrations/20260113010000_visual_content_campaigns.sql`](supabase/migrations/20260113010000_visual_content_campaigns.sql) |
| `visual_templates` | `TABLE` | [`supabase/migrations/20260113010000_visual_content_campaigns.sql`](supabase/migrations/20260113010000_visual_content_campaigns.sql) |
| `voice_generations` | `TABLE` | [`Backend/supabase/migrations/20260120_voice_cloning.sql`](Backend/supabase/migrations/20260120_voice_cloning.sql) |
| `voice_profiles` | `TABLE` | [`Backend/supabase/migrations/20260120_voice_cloning.sql`](Backend/supabase/migrations/20260120_voice_cloning.sql) |
| `watermark_removals` | `TABLE` | [`supabase/migrations/20260131000000_safari_automation_tables.sql`](supabase/migrations/20260131000000_safari_automation_tables.sql) |
| `webhook_subscriptions` | `TABLE` | [`Backend/migrations/trend_intelligence_v1.sql`](Backend/migrations/trend_intelligence_v1.sql) |
| `weekly_metrics` | `TABLE` | [`Backend/database/migrations/006_content_intelligence_insights_metrics.sql`](Backend/database/migrations/006_content_intelligence_insights_metrics.sql) |
| `weekly_metrics` | `TABLE` | [`supabase/migrations/20250121000007_content_intelligence_insights_metrics.sql`](supabase/migrations/20250121000007_content_intelligence_insights_metrics.sql) |
| `weekly_plan_slots` | `TABLE` | [`Backend/supabase/migrations/20260131_add_missing_tables.sql`](Backend/supabase/migrations/20260131_add_missing_tables.sql) |
| `weekly_schedules` | `TABLE` | [`supabase/migrations_disabled/20251223000007_narrative_scheduler.sql`](supabase/migrations_disabled/20251223000007_narrative_scheduler.sql) |
| `workspace_members` | `TABLE` | [`Backend/migrations/phase_1_essentials.sql`](Backend/migrations/phase_1_essentials.sql) |
| `workspace_members` | `TABLE` | [`supabase/migrations/20251125000000_workspace_architecture.sql`](supabase/migrations/20251125000000_workspace_architecture.sql) |
| `workspace_sources` | `TABLE` | [`Backend/migrations/trend_intelligence_v1.sql`](Backend/migrations/trend_intelligence_v1.sql) |
| `workspaces` | `TABLE` | [`Backend/migrations/phase_1_essentials.sql`](Backend/migrations/phase_1_essentials.sql) |
| `workspaces` | `TABLE` | [`Backend/migrations/trend_intelligence_v1.sql`](Backend/migrations/trend_intelligence_v1.sql) |
| `workspaces` | `TABLE` | [`supabase/migrations/20251125000000_workspace_architecture.sql`](supabase/migrations/20251125000000_workspace_architecture.sql) |
| `youtube_channels` | `TABLE` | [`supabase/migrations/20250122000008_add_video_orientation_fields.sql`](supabase/migrations/20250122000008_add_video_orientation_fields.sql) |
| `actp_ad_status` | `TYPE` | [`Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql`](Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql) |
| `actp_campaign_status` | `TYPE` | [`Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql`](Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql) |
| `actp_generation_source` | `TYPE` | [`Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql`](Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql) |
| `actp_platform` | `TYPE` | [`Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql`](Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql) |
| `actp_round_status` | `TYPE` | [`Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql`](Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql) |
| `actp_round_type` | `TYPE` | [`Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql`](Backend/services/creative_testing_pipeline/migrations/001_create_actp_tables.sql) |
| `agent_event_status` | `TYPE` | [`Backend/migrations/001_create_agent_events_table.sql`](Backend/migrations/001_create_agent_events_table.sql) |
| `agent_event_type` | `TYPE` | [`Backend/migrations/001_create_agent_events_table.sql`](Backend/migrations/001_create_agent_events_table.sql) |
| `assessment_verdict` | `TYPE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `awareness_stage` | `TYPE` | [`supabase/migrations/20260113000000_twitter_campaign_system.sql`](supabase/migrations/20260113000000_twitter_campaign_system.sql) |
| `bible_kind` | `TYPE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `clip_run_status` | `TYPE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `clip_state` | `TYPE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `content_format` | `TYPE` | [`supabase/migrations/20260113010000_visual_content_campaigns.sql`](supabase/migrations/20260113010000_visual_content_campaigns.sql) |
| `content_format_type` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `content_source_type` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `content_type_enum` | `TYPE` | [`Backend/database/migrations/008_media_creation_types.sql`](Backend/database/migrations/008_media_creation_types.sql) |
| `cta_type` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `editing_style` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `emotion_type` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `failure_reason` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `insight_type` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `orchestrator_role` | `TYPE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `plan_status` | `TYPE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `platform_type` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `posting_status` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `pov_type` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `prompt_purpose` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `proof_type` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `render_status` | `TYPE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `review_label` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `review_next_action` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `rule_type` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `slot_objective` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `trend_type` | `TYPE` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `video_provider_name` | `TYPE` | [`supabase/migrations/20241222_video_orchestrator.sql`](supabase/migrations/20241222_video_orchestrator.sql) |
| `active_agent_schedules` | `VIEW` | [`Backend/migrations/agent_schedules_runs_steps.sql`](Backend/migrations/agent_schedules_runs_steps.sql) |
| `active_conversations_summary` | `VIEW` | [`Backend/migrations/add_automation_features.sql`](Backend/migrations/add_automation_features.sql) |
| `active_conversations_summary` | `VIEW` | [`supabase/migrations_disabled/20251207000000_automation_features.sql`](supabase/migrations_disabled/20251207000000_automation_features.sql) |
| `active_subscribers_with_engagement` | `VIEW` | [`Backend/database/migrations/015_growth_data_plane.sql`](Backend/database/migrations/015_growth_data_plane.sql) |
| `agent_health_dashboard` | `VIEW` | [`Backend/database/migrations/014_brand_ops_engagement.sql`](Backend/database/migrations/014_brand_ops_engagement.sql) |
| `appstore_leaders` | `VIEW` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `auto_comment_daily_stats` | `VIEW` | [`Backend/database/migrations/013_auto_comment_tracking.sql`](Backend/database/migrations/013_auto_comment_tracking.sql) |
| `auto_comment_hourly_rate` | `VIEW` | [`Backend/database/migrations/013_auto_comment_tracking.sql`](Backend/database/migrations/013_auto_comment_tracking.sql) |
| `best_clips_by_hook_type` | `VIEW` | [`Backend/database/schema.sql`](Backend/database/schema.sql) |
| `c2_active_jobs` | `VIEW` | [`supabase/migrations/20260131000001_c2_control_plane_tables.sql`](supabase/migrations/20260131000001_c2_control_plane_tables.sql) |
| `c2_job_performance` | `VIEW` | [`supabase/migrations/20260131000001_c2_control_plane_tables.sql`](supabase/migrations/20260131000001_c2_control_plane_tables.sql) |
| `c2_recent_errors` | `VIEW` | [`supabase/migrations/20260131000001_c2_control_plane_tables.sql`](supabase/migrations/20260131000001_c2_control_plane_tables.sql) |
| `clip_performance_summary` | `VIEW` | [`Backend/database/schema.sql`](Backend/database/schema.sql) |
| `clips_full` | `VIEW` | [`Backend/migrations/phase_1_essentials.sql`](Backend/migrations/phase_1_essentials.sql) |
| `content_cross_platform_summary` | `VIEW` | [`Backend/migrations/add_content_and_engagement_tracking.sql`](Backend/migrations/add_content_and_engagement_tracking.sql) |
| `content_cross_platform_summary` | `VIEW` | [`Backend/migrations/add_content_cross_platform.sql`](Backend/migrations/add_content_cross_platform.sql) |
| `content_cross_platform_summary` | `VIEW` | [`supabase/migrations/20251123160000_update_content_summary_view.sql`](supabase/migrations/20251123160000_update_content_summary_view.sql) |
| `content_leaderboard` | `VIEW` | [`Backend/migrations/add_content_cross_platform.sql`](Backend/migrations/add_content_cross_platform.sql) |
| `content_platform_rollup` | `VIEW` | [`Backend/migrations/add_content_and_engagement_tracking.sql`](Backend/migrations/add_content_and_engagement_tracking.sql) |
| `content_platform_rollup` | `VIEW` | [`Backend/migrations/add_content_cross_platform.sql`](Backend/migrations/add_content_cross_platform.sql) |
| `daily_action_counts` | `VIEW` | [`Backend/migrations/add_automation_features.sql`](Backend/migrations/add_automation_features.sql) |
| `daily_action_counts` | `VIEW` | [`supabase/migrations_disabled/20251207000000_automation_features.sql`](supabase/migrations_disabled/20251207000000_automation_features.sql) |
| `engagement_content_lab` | `VIEW` | [`Backend/database/migrations/014_brand_ops_engagement.sql`](Backend/database/migrations/014_brand_ops_engagement.sql) |
| `engagement_executive_scorecard` | `VIEW` | [`Backend/database/migrations/014_brand_ops_engagement.sql`](Backend/database/migrations/014_brand_ops_engagement.sql) |
| `follower_activity_timeline` | `VIEW` | [`Backend/migrations/add_content_and_engagement_tracking.sql`](Backend/migrations/add_content_and_engagement_tracking.sql) |
| `follower_cohorts` | `VIEW` | [`Backend/migrations/add_content_and_engagement_tracking.sql`](Backend/migrations/add_content_and_engagement_tracking.sql) |
| `for` | `VIEW` | [`Backend/migrations/social_media_analytics.sql`](Backend/migrations/social_media_analytics.sql) |
| `high_value_leads` | `VIEW` | [`Backend/database/migrations/015_growth_data_plane.sql`](Backend/database/migrations/015_growth_data_plane.sql) |
| `hourly_action_distribution` | `VIEW` | [`Backend/migrations/add_automation_features.sql`](Backend/migrations/add_automation_features.sql) |
| `hourly_action_distribution` | `VIEW` | [`supabase/migrations_disabled/20251207000000_automation_features.sql`](supabase/migrations_disabled/20251207000000_automation_features.sql) |
| `latest_account_analytics` | `VIEW` | [`Backend/migrations/comprehensive_social_schema.sql`](Backend/migrations/comprehensive_social_schema.sql) |
| `latest_account_analytics` | `VIEW` | [`Backend/migrations/social_media_analytics.sql`](Backend/migrations/social_media_analytics.sql) |
| `latest_hashtag_trends` | `VIEW` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `latest_sound_trends` | `VIEW` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `narrative_candidates` | `VIEW` | [`Backend/migrations/narrative_builder_schema.sql`](Backend/migrations/narrative_builder_schema.sql) |
| `pipeline_summary` | `VIEW` | [`supabase/migrations/20250127000000_orchestrator_pipelines.sql`](supabase/migrations/20250127000000_orchestrator_pipelines.sql) |
| `post_performance_trends` | `VIEW` | [`Backend/migrations/comprehensive_social_schema.sql`](Backend/migrations/comprehensive_social_schema.sql) |
| `post_performance_trends` | `VIEW` | [`Backend/migrations/social_media_analytics.sql`](Backend/migrations/social_media_analytics.sql) |
| `posts_full` | `VIEW` | [`Backend/migrations/phase_1_essentials.sql`](Backend/migrations/phase_1_essentials.sql) |
| `posts_pending_checkback` | `VIEW` | [`Backend/migrations/add_automation_features.sql`](Backend/migrations/add_automation_features.sql) |
| `posts_pending_checkback` | `VIEW` | [`supabase/migrations_disabled/20251207000000_automation_features.sql`](supabase/migrations_disabled/20251207000000_automation_features.sql) |
| `processing_pipeline_status` | `VIEW` | [`Backend/database/schema.sql`](Backend/database/schema.sql) |
| `recent_agent_runs` | `VIEW` | [`Backend/migrations/agent_schedules_runs_steps.sql`](Backend/migrations/agent_schedules_runs_steps.sql) |
| `recent_ai_videos` | `VIEW` | [`supabase/migrations/20251222000001_ai_video_generations.sql`](supabase/migrations/20251222000001_ai_video_generations.sql) |
| `safari_command_performance` | `VIEW` | [`supabase/migrations/20260131000000_safari_automation_tables.sql`](supabase/migrations/20260131000000_safari_automation_tables.sql) |
| `social_analytics_latest` | `VIEW` | [`Backend/migrations/social_analytics_extension.sql`](Backend/migrations/social_analytics_extension.sql) |
| `social_analytics_latest` | `VIEW` | [`supabase/migrations/20251126000000_social_analytics_extension.sql`](supabase/migrations/20251126000000_social_analytics_extension.sql) |
| `social_post_performance` | `VIEW` | [`Backend/migrations/social_analytics_extension.sql`](Backend/migrations/social_analytics_extension.sql) |
| `social_post_performance` | `VIEW` | [`supabase/migrations/20251126000000_social_analytics_extension.sql`](supabase/migrations/20251126000000_social_analytics_extension.sql) |
| `stuck_agent_runs` | `VIEW` | [`Backend/migrations/agent_schedules_runs_steps.sql`](Backend/migrations/agent_schedules_runs_steps.sql) |
| `top_engaged_followers` | `VIEW` | [`Backend/migrations/add_content_and_engagement_tracking.sql`](Backend/migrations/add_content_and_engagement_tracking.sql) |
| `top_trending_now` | `VIEW` | [`supabase/migrations/20251222000000_trends_analytics_system.sql`](supabase/migrations/20251222000000_trends_analytics_system.sql) |
| `top_viral_patterns` | `VIEW` | [`Backend/migrations/add_comprehensive_viral_schema.sql`](Backend/migrations/add_comprehensive_viral_schema.sql) |
| `unified_media_library` | `VIEW` | [`supabase/migrations/20251222000002_ai_media_generations_enhanced.sql`](supabase/migrations/20251222000002_ai_media_generations_enhanced.sql) |
| `v_category_performance` | `VIEW` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `v_event_statistics` | `VIEW` | [`supabase/migrations/20251225000000_event_history.sql`](supabase/migrations/20251225000000_event_history.sql) |
| `v_experiment_results` | `VIEW` | [`supabase/migrations_disabled/20251223000008_experiments_scheduler_schema.sql`](supabase/migrations_disabled/20251223000008_experiments_scheduler_schema.sql) |
| `v_pattern_leaderboard` | `VIEW` | [`supabase/migrations_disabled/20251223000008_experiments_scheduler_schema.sql`](supabase/migrations_disabled/20251223000008_experiments_scheduler_schema.sql) |
| `v_posting_latest_metrics` | `VIEW` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `v_posting_performance` | `VIEW` | [`Backend/migrations/closed_loop_content_system.sql`](Backend/migrations/closed_loop_content_system.sql) |
| `v_recent_events_by_topic` | `VIEW` | [`supabase/migrations/20251225000000_event_history.sql`](supabase/migrations/20251225000000_event_history.sql) |
| `v_recent_runs` | `VIEW` | [`supabase/migrations_disabled/20251223000002_automation_center_schema.sql`](supabase/migrations_disabled/20251223000002_automation_center_schema.sql) |
| `v_run_timeline` | `VIEW` | [`supabase/migrations_disabled/20251223000002_automation_center_schema.sql`](supabase/migrations_disabled/20251223000002_automation_center_schema.sql) |
| `videos_complete_analysis` | `VIEW` | [`Backend/migrations/add_comprehensive_viral_schema.sql`](Backend/migrations/add_comprehensive_viral_schema.sql) |
| `videos_with_analysis` | `VIEW` | [`Backend/migrations/add_video_analysis_tables.sql`](Backend/migrations/add_video_analysis_tables.sql) |
| `voice_usage_analytics` | `VIEW` | [`Backend/supabase/migrations/20260120_voice_cloning.sql`](Backend/supabase/migrations/20260120_voice_cloning.sql) |
| `watermark_free_videos` | `VIEW` | [`supabase/migrations/20260131000000_safari_automation_tables.sql`](supabase/migrations/20260131000000_safari_automation_tables.sql) |

## Runtime configuration contract

Only variable names are documented. Values belong in the repository's approved secret/configuration store.

`ACTP_API_KEY`, `ACTP_CORS_ORIGINS`, `ACTP_LANDING_BASE_URL`, `ACTP_MAX_BODY_SIZE`, `ACTP_VERSION`, `AGENT_DAILY_BUDGET_USD`, `AIRTIME_ACCOUNTS_JSON`, `AI_MAX_TOKENS`, `AI_MODEL`, `AI_PROVIDER`, `AI_TEMPERATURE`, `AI_TIMEOUT`, `ANALYSIS_PROVIDER`, `ANTHROPIC_API_KEY`, `API_URL`, `APP_MODE`, `APP_VERSION`, `ASSEMBLYAI_API_KEY`, `BACKEND_HOST`, `BACKEND_PORT`, `BLOTATO_API_KEY`, `BLOTATO_API_URL`, `BLOTATO_URL`, `BLUESKY_USERNAMES`, `C2_API_KEY`, `C2_AUTH_DISABLED`, `C2_BIND_HOST`, `C2_PORT`, `C2_RELOAD`, `CAPTION_VARIANT_MODEL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`, `CI`, `CLIP_OUTPUT_DIR`, `CLOUD_SUPABASE_ANON_KEY`, `CLOUD_SUPABASE_STORAGE_BUCKET`, `CLOUD_SUPABASE_URL`, `CONTENT_INTEL_URL`, `DATABASE_URL`, `DEFAULT_CAPTION_STYLE`, `DOWNLOAD_PATH`, `ELEVENLABS_API_KEY`, `ENABLE_AI_CAPTION_VARIANTS`, `ENABLE_LOCAL_SCRAPERS`, `ENABLE_RAPIDAPI_ENRICHMENT`, `EVENT_BUS_BACKEND`, `FACEBOOK_AD_ACCOUNT_ID`, `FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_NAMES`, `FREESOUND_API_KEY`, `FROM_EMAIL`, `FROM_NAME`, `FRONTEND_PORT`, `GIPHY_API_KEY`, `GOOGLE_ADS_CUSTOMER_ID`, `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_API_KEY`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CONVERSION_ID`, `GOOGLE_CONVERSION_LABEL`, `GOOGLE_CREDENTIALS_PATH`, `GOOGLE_DRIVE_API_KEY`, `GOOGLE_DRIVE_FOLDER_ID`, `GOOGLE_SHEET_ID`, `GOOGLE_VEO3_API_KEY`, `HAILUO_API_KEY`, `HF_API_TOKEN`, `HF_TOKEN`, `HUGGINGFACE_API_TOKEN`, `HUGGINGFACE_HUB_TOKEN`, `HUGGINGFACE_TOKEN`, `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_BUSINESS_ACCOUNT_ID`, `INSTAGRAM_GRAPH_ACCOUNT_ID`, `INSTAGRAM_GRAPH_TOKEN`, `INSTAGRAM_USERNAME`, `INSTAGRAM_USERNAMES`, `INSTAGRAM_USER_ID`, `KLING_API_KEY`, `LINKEDIN_ACCESS_TOKEN`, `LINKEDIN_API_KEY`, `LINKEDIN_MODE`, `LOCAL_CLIPS_PATH`, `LOCAL_STORAGE_ENABLED`, `LOCAL_STORAGE_PATH`, `LOCAL_TEMP_PATH`, `LOCAL_THUMBNAILS_PATH`, `LOCAL_VIDEOS_PATH`, `LUMA_API_KEY`, `MEDIAPOSTER_BASE_PATH`, `MEDIAPOSTER_CONTROL_PLANE_DB`, `MEDIAPOSTER_CONTROL_PUBLISH_ENABLED`, `MEDIAPOSTER_CONTROL_TOKEN`, `MEDIAPOSTER_EARLY_PUBLISH_GRACE_SECONDS`, `MEDIA_PIPELINE_URL`, `MEDIA_VAULT_CONTROL_TOKEN`, `MEDIA_VAULT_CONTROL_URL`, `MEDIUM_API_TOKEN`, `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`, `META_APP_ID`, `META_APP_SECRET`, `META_PAGE_ACCESS_TOKEN`, `META_PIXEL_ID`, `MINIMAX_API_KEY`, `MODAL_VOICE_API_KEY`, `MODAL_VOICE_ENDPOINT`, `MPLITE_DEFAULT_ACCOUNT_ID`, `MPLITE_KEY`, `MPLITE_URL`, `MUSIC_INDEX_PATH`, `MUSIC_LIBRARY_PATH`, `NANO_BANANA_API_KEY`, `OPENAI_API_KEY`, `OPENAI_MODEL`, `PEXELS_API_KEY`, `PIKA_API_KEY`, `PINTEREST_USERNAMES`, `PIXABAY_API_KEY`, `PORT`, `POSTING_TIMEZONE_OFFSET`, `RAPIDAPI_HOST`, `RAPIDAPI_KEY`, `RAPIDAPI_TIKTOK_TIER`, `REDIS_URL`, `REMOTION_BASE_PATH`, `REMOTION_PROJECT_PATH`, `REMOTION_SERVER_URL`, `REMOTION_URL`, `RESEND_API_KEY`, `RESEND_WEBHOOK_SECRET`, `RUNWAY_API_KEY`, `SAFARI_AUTH_TOKEN`, `SAFARI_CONTROL_URL`, `SAFARI_TELEMETRY_URL`, `SAFARI_URL`, `SAME_DAY_CHECK_INTERVAL`, `SFX_MANIFEST_PATH`, `SMTP_HOST`, `SMTP_PASSWORD`, `SMTP_PORT`, `SMTP_USER`, `SNAPCHAT_ACCESS_TOKEN`, `SORA_API_KEY`, `SORA_DEFAULT_SECONDS`, `SORA_DEFAULT_SIZE`, `SORA_MODEL`, `SORA_TIMEOUT`, `STABILITY_API_KEY`, `SUPABASE_ANON_KEY`, `SUPABASE_JWT_SECRET`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_STORAGE_BUCKET`, `SUPABASE_URL`, `TEMP_DIR`, `THREADS_USERNAME`, `THREADS_USERNAMES`, `THREADS_USER_ID`, `TIKTOK_ACCESS_TOKEN`, `TIKTOK_ADS_ACCESS_TOKEN`, `TIKTOK_ADVERTISER_ID`, `TIKTOK_API_KEY`, `TIKTOK_APP_KEY`, `TIKTOK_APP_SECRET`, `TIKTOK_CAPTCHA_API_URL`, `TIKTOK_PIXEL_ID`, `TIKTOK_USERNAME`, `TIKTOK_USERNAMES`, `TRANSCRIPTION_PROVIDER`, `TREND_FLASH_OUTPUT`, `TWITTER_ACCESS_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET`, `TWITTER_ACCOUNT_ID`, `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_BEARER_TOKEN`, `TWITTER_USERNAMES`, `UNSPLASH_ACCESS_KEY`, `USE_SUPABASE_STORAGE`, `VIDEO_PROVIDER`, `VIDEO_RENDERER_ENGINE`, `VIRTUAL_ENV`, `WAITLISTLAB_API_KEY`, `WAITLISTLAB_API_URL`, `WEEKLY_EXECUTOR_CHECK_INTERVAL`, `WEEKLY_PLANNER_INTERVAL`, `YOUTUBE_ACCESS_TOKEN`, `YOUTUBE_API_KEY`, `YOUTUBE_CHANNEL_ID`, `YOUTUBE_CHANNEL_IDS`, `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN`, `YOUTUBE_USERNAMES`

## Validation and drift

```bash
python3 scripts/generate_agent_service_contracts.py --check
```

Regenerate this document after changing routes, schemas, typed models, migrations, package scripts, or runtime configuration names:

```bash
python3 scripts/generate_agent_service_contracts.py
```

The generator reads repository source only. It does not call providers, start services, execute routes, read credential values, publish content, or spend money.
