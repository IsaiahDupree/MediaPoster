# TikTok Automation Strategy

## Overview

This document outlines our strategic approach to TikTok automation using a **hybrid system**:

1. **API (tiktok-scraper7)** - Fast data extraction for analytics and monitoring
2. **Browser Automation (Safari/PyAutoGUI)** - User engagement actions (like, comment, message)

---

## Part 1: API Data Extraction (tiktok-scraper7)

### Confirmed Working Endpoints

| Endpoint | Parameters | Description | Use Case |
|----------|------------|-------------|----------|
| `GET /` | `url` | Video info by URL | Get video metrics, author info |
| `GET /comment/list` | `url`, `count`, `cursor` | Paginated comments | Extract all comments |
| `GET /user/info` | `unique_id` | User profile info | Check user stats |
| `GET /user/posts` | `unique_id`, `count`, `cursor` | User's videos | Get user's content |
| `GET /user/followers` | `unique_id`, `count` | User followers | Audience analysis |
| `GET /user/following` | `unique_id`, `count` | User following | Network analysis |
| `GET /feed/list` | `count` | Trending feed | Discover trending content |
| `GET /challenge/posts` | `challenge_name`, `count` | Hashtag videos | Hashtag research |
| `GET /challenge/info` | `challenge_name` | Hashtag info | Hashtag stats |
| `GET /music/info` | `music_id` | Music info | Sound tracking |
| `GET /music/posts` | `music_id`, `count` | Music videos | Sound-based discovery |

### API Configuration

```python
# .env configuration
RAPIDAPI_KEY=your_key_here

# API Host
HOST = "tiktok-scraper7.p.rapidapi.com"

# Headers
headers = {
    "x-rapidapi-key": os.getenv("RAPIDAPI_KEY"),
    "x-rapidapi-host": "tiktok-scraper7.p.rapidapi.com"
}
```

### Check-Back Period Monitoring

Use API to track post performance over time:

```python
# Schedule: Every 6 hours for first 48 hours, then daily for 7 days

CHECK_BACK_SCHEDULE = {
    "0-48h": "every 6 hours",   # 8 checks
    "48h-7d": "daily",          # 5 checks
    "7d-30d": "weekly"          # 4 checks
}

# Data to track per check:
# - digg_count (likes)
# - comment_count
# - share_count
# - play_count (views)
```

### Pagination for Full Data

```python
def get_all_comments(video_url: str, max_comments: int = 500):
    """Paginate through all comments."""
    all_comments = []
    cursor = 0
    
    while len(all_comments) < max_comments:
        response = requests.get(
            f"https://{HOST}/comment/list",
            headers=headers,
            params={"url": video_url, "count": "50", "cursor": str(cursor)}
        )
        data = response.json()
        comments = data["data"]["comments"]
        all_comments.extend(comments)
        
        cursor = data["data"].get("cursor", 0)
        if not data["data"].get("hasMore"):
            break
    
    return all_comments
```

---

## Part 2: Browser Automation (Engagement)

### Why Browser Automation for Engagement?

- **Likes, Comments, Messages** require authenticated sessions
- **API cannot perform write actions** (only read)
- **Browser mimics real user behavior** - less detection risk

### Supported Actions

| Action | Method | Status |
|--------|--------|--------|
| **Like Video** | JS click on like icon | ✅ Working |
| **Post Comment** | PyAutoGUI keyboard input | ✅ Working |
| **Scroll to Next** | Down arrow key | ✅ Working |
| **Open Comment Panel** | JS click on comment icon | ✅ Working |
| **Search** | Browser navigation | 🔨 To implement |
| **Send Message** | DM automation | 🔨 To implement |

### Current Working Code

```python
# Like a video
safari.run_js("""
    var likeBtn = document.querySelector('[data-e2e="like-icon"]');
    if (likeBtn) likeBtn.click();
""")

# Post a comment (DraftJS input)
safari.run_js("document.querySelector('[role=\"textbox\"]').focus();")
time.sleep(0.1)
pyautogui.typewrite(comment_text, interval=0.02)
safari.run_js("document.querySelector('[class*=\"DivPostButton\"]').click();")

# Scroll to next video
pyautogui.press('down')
```

### Key Selectors

```javascript
// Engagement buttons
'[data-e2e="like-icon"]'           // Like button
'span[data-e2e="comment-icon"]'     // Comment icon
'[data-e2e="share-icon"]'           // Share button

// Comment input
'[role="textbox"]'                  // DraftJS editor
'.public-DraftEditor-content'       // Comment field
'[class*="DivPostButton"]'          // Post button

// Video info
'[data-e2e="browse-username"]'      // Author username
'[data-e2e="like-count"]'           // Like count
'[data-e2e="comment-count"]'        // Comment count
```

---

## Part 3: Messaging Automation (To Implement)

### TikTok DM Structure

TikTok DMs are accessed via:
- **Web**: Messages icon in header → `/messages`
- **Direct URL**: `https://www.tiktok.com/messages`

### Proposed Implementation

```python
class TikTokMessenger:
    """Browser automation for TikTok direct messages."""
    
    def open_messages(self):
        """Navigate to messages inbox."""
        self.safari.navigate("https://www.tiktok.com/messages")
        time.sleep(3)
    
    def open_conversation(self, username: str):
        """Open or start conversation with user."""
        # Search for user in message list
        # Or click "New Message" and search for user
        pass
    
    def send_message(self, text: str):
        """Send a message in current conversation."""
        # Find message input
        # Type message using PyAutoGUI
        # Click send button
        pass
    
    def read_messages(self):
        """Extract messages from current conversation."""
        # Extract all visible messages
        # Return list of {sender, text, timestamp}
        pass
```

### Message Selectors (To Discover)

```javascript
// Need to discover via browser inspection:
// - Message input field
// - Send button
// - Conversation list
// - Individual message elements
```

---

## Part 4: Workflow Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    TIKTOK AUTOMATION                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐         ┌─────────────────┐            │
│  │   API LAYER     │         │  BROWSER LAYER  │            │
│  │  (Read Only)    │         │  (Read + Write) │            │
│  ├─────────────────┤         ├─────────────────┤            │
│  │ • Video info    │         │ • Like videos   │            │
│  │ • Comments      │         │ • Post comments │            │
│  │ • User profiles │         │ • Send messages │            │
│  │ • Followers     │         │ • Search/browse │            │
│  │ • Hashtag data  │         │ • Follow users  │            │
│  │ • Trending feed │         │                 │            │
│  └────────┬────────┘         └────────┬────────┘            │
│           │                           │                      │
│           └───────────┬───────────────┘                      │
│                       │                                      │
│              ┌────────▼────────┐                            │
│              │   DATABASE      │                            │
│              │  (PostgreSQL)   │                            │
│              ├─────────────────┤                            │
│              │ • Post metrics  │                            │
│              │ • Comments      │                            │
│              │ • Engagement    │                            │
│              │ • DM history    │                            │
│              └─────────────────┘                            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Check-Back Period Schedule

```python
CHECK_BACK_PERIODS = [
    {"after": "1h",   "action": "api_fetch_metrics"},
    {"after": "6h",   "action": "api_fetch_metrics"},
    {"after": "12h",  "action": "api_fetch_metrics"},
    {"after": "24h",  "action": "api_fetch_metrics + comments"},
    {"after": "48h",  "action": "api_fetch_metrics + comments"},
    {"after": "72h",  "action": "api_fetch_all"},
    {"after": "7d",   "action": "api_fetch_all"},
    {"after": "14d",  "action": "api_fetch_all"},
    {"after": "30d",  "action": "api_fetch_final"},
]
```

---

## Part 5: Implementation Files

### Current Files

| File | Purpose |
|------|---------|
| `test_tiktok_api.py` | API data extraction |
| `test_tiktok_full_engagement.py` | Like, comment, scroll automation |
| `test_data_extraction.py` | Browser-based data extraction |
| `test_pyautogui_automation.py` | Core automation tests |

### To Create

| File | Purpose |
|------|---------|
| `tiktok_messenger.py` | DM automation class |
| `tiktok_scheduler.py` | Check-back period scheduler |
| `tiktok_analytics.py` | Post performance analytics |

---

## Part 6: Rate Limits & Safety

### API Rate Limits (tiktok-scraper7)

- **Free Tier**: Limited requests/month
- **Basic**: Higher limits
- **Recommended**: Use pagination efficiently, cache results

### Browser Automation Safety

```python
# Recommended delays to avoid detection
ACTION_DELAYS = {
    "between_likes": (2, 5),      # 2-5 seconds
    "between_comments": (30, 60), # 30-60 seconds
    "between_messages": (60, 120),# 1-2 minutes
    "between_videos": (3, 8),     # 3-8 seconds
}

# Daily limits (conservative)
DAILY_LIMITS = {
    "likes": 100,
    "comments": 20,
    "messages": 10,
    "follows": 50,
}
```

---

## Quick Start Commands

```bash
# Test API endpoints
python automation/tests/test_tiktok_api.py discover

# Test API data extraction
python automation/tests/test_tiktok_api.py

# Test browser engagement
pytest automation/tests/test_tiktok_full_engagement.py -v -s

# Test browser data extraction
pytest automation/tests/test_data_extraction.py -v -s
```

---

## Part 7: New Modules (Implemented)

### 1. Messaging (`tiktok_messenger.py`)

```python
from automation.tiktok_messenger import TikTokMessenger

messenger = TikTokMessenger(safari_controller)
messenger.open_inbox()
messenger.send_to_user("username", "Hello!")
```

### 2. Search (`tiktok_search.py`)

```python
from automation.tiktok_search import TikTokSearch

search = TikTokSearch(safari_controller)
users = search.search_users("arduino", limit=20)
videos = search.search_videos("#coding", limit=20)
search.navigate_to_user("mewtru")
```

### 3. Scheduler (`tiktok_scheduler.py`)

```python
from automation.tiktok_scheduler import TikTokScheduler

scheduler = TikTokScheduler()
post = scheduler.track_post("https://tiktok.com/@user/video/123")
scheduler.run_pending_checks()
analytics = scheduler.get_post_analytics(video_id)
```

### CLI Commands

```bash
# Scheduler
python automation/tiktok_scheduler.py track <url>
python automation/tiktok_scheduler.py check
python automation/tiktok_scheduler.py list
python automation/tiktok_scheduler.py daemon

# Test new features
pytest automation/tests/test_tiktok_features.py -v -s
```

---

## Next Steps

1. ✅ API endpoint discovery complete
2. ✅ Paginated comment extraction working
3. ✅ Messaging automation - `tiktok_messenger.py`
4. ✅ Search automation - `tiktok_search.py`
5. ✅ Check-back scheduler - `tiktok_scheduler.py` (JSON) + `tiktok_scheduler_db.py` (DB)
6. ✅ Database schema migration - `add_automation_features.sql`
7. 🔨 Discover actual DM selectors (browser inspection)
8. 🔨 Build analytics dashboard
9. 🔨 Run migration on database

---

## Database Migration

### Run Migration

```bash
# Via Supabase CLI
supabase db push

# Via Docker (local Supabase)
cat supabase/migrations/20251207000000_automation_features.sql | \
  docker exec -i supabase_db_MediaPoster psql -U postgres -d postgres

# Via psql directly
psql $DATABASE_URL -f Backend/migrations/add_automation_features.sql
```

### What's Included

| Type | Count | Description |
|------|-------|-------------|
| **New Tables** | 4 | conversations, messages, actions, templates |
| **New Columns** | 5 | check_schedule, next_check_at, etc. |
| **Views** | 4 | posts_pending_checkback, daily_action_counts |
| **Functions** | 3 | check_rate_limit, get_next_check_time |
| **Settings** | 2 | rate_limits, checkback_schedule_default |
