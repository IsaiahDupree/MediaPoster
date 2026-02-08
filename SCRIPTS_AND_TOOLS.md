# Scripts & Tools — Quick Reference

> **Everything you need to publish, schedule, automate, and monitor content.**

---

## 🚀 Publishing & Scheduling (Priority)

These scripts handle the core content pipeline — scheduling videos, publishing to platforms, and monitoring results. All work **standalone** (no backend server required) and connect directly to the PostgreSQL database.

| Script | What It Does | Quick Start |
|--------|-------------|-------------|
| [`schedule_videos.py`](Backend/scripts/schedule_videos.py) | Schedule videos from a folder into the DB | `python scripts/schedule_videos.py ~/videos --platform youtube` |
| [`plan_content.py`](Backend/scripts/plan_content.py) | Analyze schedule, find gaps, plan strategy | `python scripts/plan_content.py overview` |
| [`schedule_from_guide.py`](Backend/scripts/schedule_from_guide.py) | Parse a markdown publishing guide → schedule | `python scripts/schedule_from_guide.py ~/guide.md --platform youtube` |
| [`watch_folder.py`](Backend/scripts/watch_folder.py) | Auto-ingest daemon: drop video → auto-scheduled | `python scripts/watch_folder.py ~/incoming --platform youtube` |
| [`publish_monitor.py`](Backend/scripts/publish_monitor.py) | Live publish monitoring + notifications | `python scripts/publish_monitor.py --status` |
| [`bulk_scheduler.py`](Backend/scripts/bulk_scheduler.py) | Direct Blotato API scheduling (bypass DB) | `python scripts/bulk_scheduler.py --source ~/v.mp4 --platform tiktok` |

📖 **Full docs:** [`Backend/scripts/SCHEDULING_TOOLS.md`](Backend/scripts/SCHEDULING_TOOLS.md)

---

## 📹 Video Ingestion & Processing

| Script | What It Does |
|--------|-------------|
| [`ingest_iphone_media.py`](Backend/scripts/ingest_iphone_media.py) | Import videos from iPhone/external drive into media DB |
| [`ingest_sora_videos.py`](Backend/scripts/ingest_sora_videos.py) | Import Sora AI-generated videos into media DB |
| [`full_workflow_ingest_analyze_publish.py`](Backend/scripts/full_workflow_ingest_analyze_publish.py) | End-to-end: ingest → analyze → schedule → publish |
| [`import_analyze_schedule_25_videos.py`](Backend/scripts/import_analyze_schedule_25_videos.py) | Batch import + analyze + schedule 25 videos at once |
| [`generate_thumbnails.py`](Backend/scripts/generate_thumbnails.py) | Generate thumbnails for videos using ffmpeg |
| [`reprocess_sora_watermarks.py`](Backend/scripts/reprocess_sora_watermarks.py) | Clean watermarks from Sora videos |

---

## 🤖 Browser Automation (Safari)

All Safari automation scripts require macOS with "Allow Remote Automation" enabled.

| Script | What It Does |
|--------|-------------|
| [`safari_app_controller.py`](Backend/automation/safari_app_controller.py) | Core Safari automation controller (singleton) |
| [`safari_instagram_scraper.py`](Backend/automation/safari_instagram_scraper.py) | Scrape Instagram reels/posts via Safari scroll+collect |
| [`safari_instagram_poster.py`](Backend/automation/safari_instagram_poster.py) | Post to Instagram via Safari |
| [`safari_twitter_poster.py`](Backend/automation/safari_twitter_poster.py) | Post to Twitter/X via Safari |
| [`safari_twitter_dm.py`](Backend/automation/safari_twitter_dm.py) | Send Twitter/X DMs via Safari |
| [`safari_threads_poster.py`](Backend/automation/safari_threads_poster.py) | Post to Threads via Safari |
| [`safari_reddit_poster.py`](Backend/automation/safari_reddit_poster.py) | Post to Reddit via Safari |
| [`safari_tiktok_cli.py`](Backend/automation/safari_tiktok_cli.py) | TikTok CLI for Safari-based automation |
| [`sora_full_automation.py`](Backend/automation/sora_full_automation.py) | Sora video generation via browser (usage check, generate, batch) |

📖 **Automation docs:** [`Backend/automation/README.md`](Backend/automation/README.md)

---

## 💬 Engagement & DMs

| Script | What It Does |
|--------|-------------|
| [`tiktok_engagement.py`](Backend/automation/tiktok_engagement.py) | TikTok FYP engagement (like, comment, follow) |
| [`tiktok_dm_controller.py`](Backend/automation/tiktok_dm_controller.py) | TikTok DM automation controller |
| [`instagram_comment_automation.py`](Backend/automation/instagram_comment_automation.py) | Auto-comment on Instagram posts |
| [`instagram_dm_controller.py`](Backend/automation/instagram_dm_controller.py) | Instagram DM automation |
| [`threads_auto_commenter.py`](Backend/automation/threads_auto_commenter.py) | Auto-comment on Threads posts |
| [`tiktok_comment_agentic.py`](Backend/automation/tiktok_comment_agentic.py) | AI-powered TikTok commenting |
| [`auto_comment_runner.py`](Backend/scripts/auto_comment_runner.py) | Multi-platform auto-comment orchestrator |

📖 **Engagement docs:** [`Backend/scripts/auto_engagement/README.md`](Backend/scripts/auto_engagement/README.md)  
📖 **FYP engagement:** [`Backend/automation/FYP_ENGAGEMENT_README.md`](Backend/automation/FYP_ENGAGEMENT_README.md)

---

## 📊 Analytics & Competitor Research

| Script | What It Does |
|--------|-------------|
| [`youtube_performance_review.py`](Backend/scripts/youtube_performance_review.py) | Review YouTube Shorts performance metrics |
| [`analyze_competitor_video.py`](Backend/scripts/analyze_competitor_video.py) | AI analysis of competitor videos |
| [`analyze_competitor_for_prompts.py`](Backend/scripts/analyze_competitor_for_prompts.py) | Extract prompts/strategies from competitor content |
| [`scrape_competitor_tiktok.py`](Backend/scripts/scrape_competitor_tiktok.py) | Scrape competitor TikTok profiles |
| [`download_competitor_videos.py`](Backend/scripts/download_competitor_videos.py) | Download competitor videos for analysis |
| [`download_from_manifest.py`](Backend/scripts/download_from_manifest.py) | Download videos from a manifest of URLs (RapidAPI) |
| [`extract_engagement_stats.py`](Backend/scripts/extract_engagement_stats.py) | Extract engagement statistics |
| [`populate_social_analytics.py`](Backend/scripts/populate_social_analytics.py) | Populate social media analytics data |

---

## 🎬 Sora Video Pipeline

| Script | What It Does |
|--------|-------------|
| [`sora_full_pipeline.py`](Backend/scripts/sora_full_pipeline.py) | Full Sora pipeline: generate → clean → schedule |
| [`sora_full_automation.py`](Backend/automation/sora_full_automation.py) | Browser automation for Sora (usage, generate, batch) |
| [`sora_generate_with_character.py`](Backend/scripts/sora_generate_with_character.py) | Generate Sora video with @character |
| [`publish_sora_videos.py`](Backend/scripts/publish_sora_videos.py) | Publish Sora videos to platforms |
| [`sora_youtube_schedule.py`](Backend/scripts/sora_youtube_schedule.py) | Schedule Sora videos specifically to YouTube |
| [`run_full_sora_pipeline.py`](Backend/scripts/run_full_sora_pipeline.py) | Run the complete Sora pipeline end-to-end |

---

## 🛠️ Database & Infrastructure

| Script | What It Does |
|--------|-------------|
| [`backup_database.py`](Backend/scripts/backup_database.py) | Backup PostgreSQL database |
| [`db_audit.py`](Backend/scripts/db_audit.py) | Audit database tables and data integrity |
| [`health_check.py`](Backend/scripts/health_check.py) | Check backend API health status |
| [`startup_checks.py`](Backend/scripts/startup_checks.py) | Run startup verification checks |
| [`env_check.py`](Backend/scripts/env_check.py) | Verify environment variables are configured |
| [`check_api_status.py`](Backend/scripts/check_api_status.py) | Check API endpoint status |

---

## 🗂️ Key Documentation

| Document | Description |
|----------|-------------|
| [`Backend/scripts/SCHEDULING_TOOLS.md`](Backend/scripts/SCHEDULING_TOOLS.md) | Full scheduling scripts docs with examples |
| [`Backend/QUICKSTART.md`](Backend/QUICKSTART.md) | Backend quick start guide |
| [`Backend/SETUP.md`](Backend/SETUP.md) | Full backend setup instructions |
| [`Backend/automation/README.md`](Backend/automation/README.md) | Safari automation setup and usage |
| [`Backend/automation/FYP_ENGAGEMENT_README.md`](Backend/automation/FYP_ENGAGEMENT_README.md) | FYP engagement automation guide |
| [`Backend/automation/SAFARI_PERMISSIONS.md`](Backend/automation/SAFARI_PERMISSIONS.md) | Safari permissions setup |
| [`Backend/SLEEP_MODE_QUICKSTART.md`](Backend/SLEEP_MODE_QUICKSTART.md) | Sleep/wake mode for scheduled publishing |

---

## ⚡ Default Accounts (Blotato)

| Platform | ID | Username |
|----------|-----|----------|
| YouTube | 228 | Isaiah Dupree |
| TikTok | 710 | @isaiah_dupree |
| Instagram | 807 | @the_isaiah_dupree |
| Threads | 173 | @the_isaiah_dupree_ |
| Twitter/X | 4151 | @soursides_is_sour |
| Pinterest | 173 | @isaiahdupree33 |
| LinkedIn | 571 | @IsaiahDupree7 |
| Facebook | 786 | Isaiah Dupree |
| Bluesky | 201 | isaiahdupree.bsky.social |

Full mapping: `Backend/config/blotato_accounts.py` or `GET /api/blotato/accounts`

---

## 🏃 Running Services

```bash
# Backend API (port 5555)
cd Backend && python main.py

# Dashboard (port 5557)
cd dashboard && npm run dev

# Local Supabase DB (port 54322)
supabase start

# Folder watcher daemon
python Backend/scripts/watch_folder.py ~/incoming --platform youtube --daemon

# Publish monitor (live)
python Backend/scripts/publish_monitor.py --notify
```

---

## 📅 Current Schedule Status

Check anytime with:
```bash
python Backend/scripts/plan_content.py overview      # Full overview
python Backend/scripts/plan_content.py upcoming       # Next posts
python Backend/scripts/publish_monitor.py --status    # Live status
```
