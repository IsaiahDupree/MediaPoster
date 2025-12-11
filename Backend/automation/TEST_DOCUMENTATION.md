# TikTok Automation Test Documentation

## Overview

This document covers all unit and integration tests for the TikTok automation system, organized by category with implementation details.

---

## Test Categories

| Category | File | Tests | Purpose |
|----------|------|-------|---------|
| **Unit** | `test_unit.py` | 15+ | Core component logic |
| **Functional** | `test_functional.py` | 30+ | Selector validation, rate limits |
| **Integration** | `test_integration.py` | 5+ | Component interaction |
| **E2E** | `test_e2e.py` | 20+ | Full browser flows |
| **API** | `test_tiktok_api.py` | 5+ | RapidAPI data extraction |
| **Engagement** | `test_tiktok_full_engagement.py` | 3+ | Like, comment, scroll |
| **Data Extraction** | `test_data_extraction.py` | 3+ | Browser-based scraping |

---

## 1. Unit Tests (`test_unit.py`)

### Session Manager State

```bash
pytest automation/tests/test_unit.py -v
```

| Test | Description |
|------|-------------|
| `test_init_default_values` | SessionManager initializes with defaults |
| `test_init_custom_session_dir` | Custom session directory works |
| `test_init_max_action_history` | Action history limit enforced |
| `test_update_state_single_field` | State updates correctly |

### Implementation

```python
from automation.session_manager import SessionManager

# Create session manager
sm = SessionManager(session_dir="./sessions")

# Update state
sm.update_state(current_url="https://tiktok.com/foryou")

# Check state
assert sm.state.current_url == "https://tiktok.com/foryou"
```

---

## 2. Functional Tests (`test_functional.py`)

### Navigation

```bash
pytest automation/tests/test_functional.py::TestNavigationFunctional -v
```

| Test | Description |
|------|-------------|
| `test_url_to_page_type_mapping` | URL detection (FYP, profile, etc.) |
| `test_navigation_records_action` | Actions logged to history |
| `test_navigation_updates_current_url` | URL state tracking |
| `test_navigation_respects_rate_limit` | Rate limiting enforced |

### Selectors

| Test | Description |
|------|-------------|
| `test_like_selector_defined` | Like button selector exists |
| `test_comment_selector_defined` | Comment button selector exists |
| `test_share_selector_defined` | Share button selector exists |
| `test_follow_selector_defined` | Follow button selector exists |
| `test_message_input_selector_defined` | DM input selector exists |

### Rate Limits

```python
# Default rate limits per action type
RATE_LIMITS = {
    "like": 100,      # per day
    "comment": 20,    # per day
    "follow": 50,     # per day
    "message": 10,    # per day
}
```

---

## 3. Integration Tests (`test_integration.py`)

```bash
pytest automation/tests/test_integration.py -v
```

| Test | Description |
|------|-------------|
| `test_state_persists_across_managers` | Session state saved/loaded |
| `test_rate_limits_persist` | Rate limits survive restart |

### Implementation

```python
# Session persistence
sm1 = SessionManager(session_dir=tmp_path)
sm1.update_state(current_url="https://tiktok.com")
sm1.save_session()

sm2 = SessionManager(session_dir=tmp_path)
sm2.load_session()
assert sm2.state.current_url == "https://tiktok.com"
```

---

## 4. E2E Tests (`test_e2e.py`)

### Prerequisites
- Safari open with TikTok logged in
- PyAutoGUI permissions granted

```bash
pytest automation/tests/test_e2e.py -v -s
```

### Navigation Tests

| Test | Description |
|------|-------------|
| `test_navigate_to_fyp` | Go to For You Page |
| `test_navigate_to_following` | Go to Following feed |
| `test_navigate_to_messages` | Go to DM inbox |
| `test_navigate_to_profile` | Go to user profile |
| `test_navigate_to_search` | Go to search page |

### Engagement Tests

| Test | Description |
|------|-------------|
| `test_like_video` | Like current video |
| `test_unlike_video` | Unlike if already liked |
| `test_post_comment` | Post a comment |
| `test_scroll_next_video` | Scroll to next video |
| `test_follow_user` | Follow a user |

### Messaging Tests

| Test | Description |
|------|-------------|
| `test_send_dm` | Send a direct message |
| `test_message_flow` | Full DM conversation flow |

### Data Extraction Tests

| Test | Description |
|------|-------------|
| `test_extract_video_info` | Get video metadata |
| `test_extract_comments` | Get comments via browser |
| `test_extract_conversations` | Get DM conversations |

---

## 5. API Tests (`test_tiktok_api.py`)

### Prerequisites
- `RAPIDAPI_KEY` in `.env`
- Subscription to tiktok-scraper7

```bash
# Discover endpoints
python automation/tests/test_tiktok_api.py discover

# Full test
python automation/tests/test_tiktok_api.py
```

### Endpoints Tested

| Endpoint | Test | Description |
|----------|------|-------------|
| `GET /` | `test_video_info` | Video metadata |
| `GET /comment/list` | `test_comments` | Paginated comments |
| `GET /user/info` | `test_user_info` | User profile |
| `GET /user/posts` | `test_user_posts` | User's videos |
| `GET /feed/list` | `test_trending` | Trending feed |

### Implementation

```python
from automation.tests.test_tiktok_api import TikTokRapidAPI

api = TikTokRapidAPI()

# Get video info
video = api.get_video_info("https://tiktok.com/@user/video/123")
print(f"Likes: {video['data']['digg_count']}")

# Get all comments
comments = get_all_comments_paginated(api_key, video_url, max_comments=500)
```

---

## 6. Engagement Tests (`test_tiktok_full_engagement.py`)

### Prerequisites
- Safari open with TikTok FYP loaded
- Logged in as target account

```bash
pytest automation/tests/test_tiktok_full_engagement.py -v -s
```

| Test | Description |
|------|-------------|
| `test_engagement_on_three_videos` | Like + comment + scroll x3 |
| `test_like_via_js` | JS-based like (reliable) |
| `test_comment_via_pyautogui` | Keyboard-based comment |

### Implementation

```python
# Like via JS
safari.run_js("""
    var likeBtn = document.querySelector('[data-e2e="like-icon"]');
    if (likeBtn) likeBtn.click();
""")

# Comment via PyAutoGUI
safari.run_js("document.querySelector('[role=\"textbox\"]').focus();")
pyautogui.typewrite("Nice video!", interval=0.02)
safari.run_js("document.querySelector('[class*=\"DivPostButton\"]').click();")
```

---

## 7. Data Extraction Tests (`test_data_extraction.py`)

```bash
pytest automation/tests/test_data_extraction.py -v -s
```

| Test | Description |
|------|-------------|
| `test_extract_video_metadata` | Get author, description, hashtags |
| `test_extract_all_comments` | Scroll and extract comments |
| `test_detect_panel_state` | Check if comment panel open |

---

## System-Level Implementation

### 1. Install Dependencies

```bash
cd Backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# .env file
RAPIDAPI_KEY=your_rapidapi_key
TIKTOK_USERNAME=your_username
```

### 3. Run Test Suites

```bash
# All unit tests (no browser needed)
pytest automation/tests/test_unit.py automation/tests/test_functional.py -v

# Integration tests
pytest automation/tests/test_integration.py -v

# E2E tests (browser required)
pytest automation/tests/test_e2e.py -v -s

# Engagement tests (browser + TikTok login required)
pytest automation/tests/test_tiktok_full_engagement.py -v -s

# API tests
python automation/tests/test_tiktok_api.py
```

### 4. Test Execution Order

```
1. Unit Tests (no dependencies)
   └── test_unit.py
   └── test_functional.py

2. Integration Tests (file system)
   └── test_integration.py

3. Smoke Tests (imports/sanity)
   └── test_regression_smoke_api.py

4. API Tests (network, no browser)
   └── test_tiktok_api.py

5. E2E Tests (Safari required)
   └── test_e2e.py
   └── test_tiktok_full_engagement.py
   └── test_data_extraction.py
```

---

## Key Selectors Reference

### Video Actions

```javascript
'[data-e2e="like-icon"]'           // Like button
'span[data-e2e="comment-icon"]'     // Comment icon
'[data-e2e="share-icon"]'           // Share button
'[data-e2e="browse-username"]'      // Author username
'[data-e2e="like-count"]'           // Like count
'[data-e2e="comment-count"]'        // Comment count
```

### Comment Input

```javascript
'[role="textbox"]'                  // DraftJS editor
'.public-DraftEditor-content'       // Alt comment field
'[class*="DivPostButton"]'          // Post button
'[class*="DivCommentItemWrapper"]'  // Comment item
```

### Navigation

```javascript
'a[href="/messages"]'               // Messages link
'a[href*="/foryou"]'                // FYP link
'input[type="search"]'              // Search input
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `No element found` | Check selector, page may not be loaded |
| `Rate limit exceeded` | Wait for cooldown period |
| `Comment not posting` | Focus input, use PyAutoGUI not JS |
| `API 403` | Subscribe to API on RapidAPI |
| `Screenshot fails` | Grant screen recording permission |

### Debug Mode

```bash
# Run with verbose output
pytest automation/tests/test_e2e.py -v -s --tb=long

# Take screenshots on failure
pytest automation/tests/test_e2e.py --screenshot=on
```
