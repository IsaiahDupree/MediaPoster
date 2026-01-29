# PRD: Daily Automation System

**Version:** 1.0  
**Date:** January 27, 2026  
**Status:** Implementation Ready  
**Priority:** P0 (Critical)

---

## Executive Summary

Unified daily automation that maximizes content output:
1. **Sora**: Check credits on startup, use all 30 daily generations
2. **Twitter**: Post offers every 2 hours (12 posts/day)
3. **Startup**: Both automations initialize on backend startup

---

## Requirements

### AUTO-001: Backend Startup Integration
- Auto-start both schedulers on `main.py` startup
- Health check for Safari/browser availability
- Status endpoint: `/api/daily-automation/status`

### AUTO-002: Sora Credit Check
- Check credits via Safari automation on startup
- Parse "X video gens left" from usage page
- Plan generation based on available credits

### AUTO-003: Daily Sora Generation
- Use all 30 daily credits
- Max 3 concurrent generations
- Content: 4 three-part movies + 10 singles + 8 buffer
- Watermark removal via BlankLogo
- Publish to YouTube (Account ID: 228)

### AUTO-004: Twitter Offer Posting
- Post every 2 hours (12 posts/day)
- Rotate through offers and awareness stages
- AI-generated copy via TwitterCampaignService
- Safari automation for posting

---

## API Endpoints

```
GET  /api/daily-automation/status     - Current automation status
POST /api/daily-automation/start      - Manual start
POST /api/daily-automation/stop       - Pause automations
GET  /api/daily-automation/sora       - Sora generation status
GET  /api/daily-automation/twitter    - Twitter posting status
```

---

## File Structure

```
Backend/services/daily_automation/
├── __init__.py
├── manager.py              # DailyAutomationManager
├── sora_scheduler.py       # Sora credit check + generation
├── twitter_scheduler.py    # 2-hour offer posting
└── events.py               # Event definitions

Backend/api/endpoints/
└── daily_automation.py     # REST API
```

---

## Event Topics

| Event | Description |
|-------|-------------|
| `daily.automation.started` | Manager initialized |
| `daily.sora.credit_check` | Credits checked |
| `daily.sora.generation_queued` | Video queued |
| `daily.sora.generation_completed` | Video done |
| `daily.twitter.post_scheduled` | Tweet scheduled |
| `daily.twitter.post_completed` | Tweet posted |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Daily Sora Usage | 30/30 (100%) |
| Twitter Posts/Day | 12 (every 2 hours) |
| Startup Success | 95%+ |
| Post Success Rate | 95%+ |
