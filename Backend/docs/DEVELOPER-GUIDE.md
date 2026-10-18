# MediaPoster Developer Guide

**Last Updated:** 2026-01-16

## Overview

MediaPoster is a comprehensive social media automation platform that combines:
1. **Safari Browser Automation** - AppleScript-based automation for macOS
2. **API-Based Publishing** - Direct API integration with platforms
3. **Scheduling System** - Queue and calendar management
4. **AI Content Generation** - Template-based content with OpenAI

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        MediaPoster                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │   Frontend       │    │   Backend        │                   │
│  │   (Next.js)      │◄──►│   (FastAPI)      │                   │
│  └──────────────────┘    └────────┬─────────┘                   │
│                                   │                              │
│          ┌────────────────────────┼────────────────────────┐    │
│          │                        │                        │    │
│          ▼                        ▼                        ▼    │
│  ┌───────────────┐    ┌───────────────────┐    ┌────────────┐  │
│  │ Safari        │    │ API Publishers    │    │ Scheduler  │  │
│  │ Automation    │    │ (TikTok/IG/YT)    │    │ Service    │  │
│  └───────┬───────┘    └─────────┬─────────┘    └────────────┘  │
│          │                      │                               │
│          ▼                      ▼                               │
│  ┌───────────────┐    ┌───────────────────┐                    │
│  │ AppleScript   │    │ Platform APIs     │                    │
│  │ + JavaScript  │    │ (OAuth2)          │                    │
│  └───────────────┘    └───────────────────┘                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Safari Browser Automation

### How It Works

Safari automation uses macOS AppleScript to control the browser and inject JavaScript into web pages:

```
┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│   Python     │────►│  osascript  │────►│   Safari     │
│   Script     │     │  (shell)    │     │   Browser    │
└──────────────┘     └─────────────┘     └──────┬───────┘
                                                 │
                                                 ▼
                                         ┌──────────────┐
                                         │  JavaScript  │
                                         │  Injection   │
                                         └──────────────┘
```

### Core Components

#### 1. SafariSessionManager

**File:** `automation/safari_session_manager.py`

Centralized login verification for all platforms.

```python
from automation.safari_session_manager import SafariSessionManager, Platform

manager = SafariSessionManager()

# Check if logged in to Twitter
if manager.require_login(Platform.TWITTER):
    print("Logged in!")
else:
    print("Please log in manually")
```

**Supported Platforms:**
- `Platform.TWITTER` - x.com
- `Platform.TIKTOK` - tiktok.com
- `Platform.INSTAGRAM` - instagram.com
- `Platform.THREADS` - threads.net
- `Platform.SORA` - sora.com
- `Platform.YOUTUBE` - youtube.com

#### 2. SafariAppController

**File:** `automation/safari_app_controller.py`

Low-level Safari control via AppleScript.

```python
from automation.safari_app_controller import SafariAppController

controller = SafariAppController()

# Navigate to URL
controller.navigate("https://x.com")

# Execute JavaScript
result = controller.run_js("document.title")

# Click element
controller.click_element('[data-testid="tweetButton"]')
```

#### 3. Platform-Specific Posters

| Platform | File | Main Class |
|----------|------|------------|
| Twitter/X | `safari_twitter_poster.py` | `SafariTwitterPoster` |
| Threads | `safari_threads_poster.py` | `SafariThreadsPoster` |
| TikTok | `tiktok_engagement.py` | `TikTokEngagement` |
| Sora | `sora_browser_automation.py` | `SoraBrowserAutomation` |

---

## AppleScript Execution Pattern

All Safari automation follows this pattern:

```python
import subprocess

def _run_applescript(self, script: str) -> tuple:
    """Execute AppleScript and return (success, output)."""
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip()
    except Exception as e:
        return False, str(e)
```

### Common AppleScript Commands

#### Navigate to URL
```applescript
tell application "Safari"
    activate
    if (count of windows) = 0 then
        make new document
    end if
    set URL of front document to "https://x.com"
end tell
```

#### Execute JavaScript
```applescript
tell application "Safari"
    tell front document
        do JavaScript "document.querySelector('.tweet-button').click()"
    end tell
end tell
```

#### Get Page Content
```applescript
tell application "Safari"
    tell front document
        do JavaScript "document.body.innerText"
    end tell
end tell
```

---

## JavaScript Injection Patterns

### Click Element
```javascript
(function() {
    var el = document.querySelector('[data-testid="tweetButton"]');
    if (el) {
        el.click();
        return 'clicked';
    }
    return 'not_found';
})();
```

### Fill Input Field
```javascript
(function() {
    var input = document.querySelector('[data-testid="tweetTextarea"]');
    if (input) {
        input.focus();
        input.innerText = 'Hello World!';
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return 'filled';
    }
    return 'not_found';
})();
```

### Wait for Element
```javascript
(function() {
    return new Promise((resolve) => {
        var attempts = 0;
        var check = setInterval(function() {
            var el = document.querySelector('.success-message');
            if (el || attempts > 30) {
                clearInterval(check);
                resolve(el ? 'found' : 'timeout');
            }
            attempts++;
        }, 500);
    });
})();
```

### Extract Data
```javascript
(function() {
    var items = [];
    document.querySelectorAll('[data-testid="notification"]').forEach(function(el) {
        items.push({
            text: el.innerText.substring(0, 200),
            time: el.querySelector('time')?.getAttribute('datetime')
        });
    });
    return JSON.stringify(items);
})();
```

---

## API-Based Publishing

### Platform Publishers

**File:** `services/platform_publishers.py`

#### TikTokPublisher

Uses TikTok Content Posting API:

```python
from services.platform_publishers import TikTokPublisher, PublishRequest, MediaType, Platform

publisher = TikTokPublisher(credentials={
    "access_token": "your_access_token"
})

request = PublishRequest(
    media_path="/path/to/video.mp4",
    media_type=MediaType.VIDEO,
    description="Check this out!",
    hashtags=["#viral", "#fyp"],
    account_id="123",
    platform=Platform.TIKTOK
)

result = await publisher.publish(request)
print(result.success, result.post_url)
```

#### InstagramPublisher

Uses Instagram Graph API:

```python
from services.platform_publishers import InstagramPublisher

publisher = InstagramPublisher(credentials={
    "access_token": "your_access_token",
    "instagram_user_id": "your_ig_user_id"
})

# Publish reel
result = await publisher.publish(PublishRequest(
    media_path="/path/to/reel.mp4",
    media_type=MediaType.REEL,
    description="Amazing content!",
    hashtags=["#reels"],
    account_id="456",
    platform=Platform.INSTAGRAM,
    metadata={"video_url": "https://publicly-accessible-url.com/video.mp4"}
))
```

#### YouTubePublisher

Uses YouTube Data API v3 with resumable uploads:

```python
from services.platform_publishers import YouTubePublisher

publisher = YouTubePublisher(credentials={
    "access_token": "your_access_token"
})

result = await publisher.publish(PublishRequest(
    media_path="/path/to/video.mp4",
    media_type=MediaType.VIDEO,
    title="My Video Title",
    description="Video description",
    hashtags=["#youtube"],
    account_id="789",
    platform=Platform.YOUTUBE,
    privacy="public"  # or "private", "unlisted"
))
```

---

## CLI Reference

### Twitter CLI
```bash
# Post
python safari_twitter_poster.py post "Hello Twitter!"
python safari_twitter_poster.py post "With media" -m /path/to/image.jpg

# Thread
python safari_twitter_poster.py thread -t "Tweet 1" "Tweet 2" "Tweet 3"

# Reply
python safari_twitter_poster.py reply https://x.com/user/status/123 "Reply text"

# Notifications
python safari_twitter_poster.py notifications
python safari_twitter_poster.py notifications --mentions --unread

# DMs
python safari_twitter_poster.py dm list
python safari_twitter_poster.py dm read username
python safari_twitter_poster.py dm send username "Message"
```

### Threads CLI
```bash
python safari_threads_poster.py post "Hello Threads!"
python safari_threads_poster.py reply URL "Reply"
python safari_threads_poster.py notifications
python safari_threads_poster.py dm list
python safari_threads_poster.py dm send username "Message"
```

### TikTok CLI
```bash
python safari_tiktok_cli.py --check-login
python safari_tiktok_cli.py like URL
python safari_tiktok_cli.py comment URL "Great video!"
python safari_tiktok_cli.py follow @username
python safari_tiktok_cli.py notifications
python safari_tiktok_cli.py dm list
python safari_tiktok_cli.py dm send username "Hello!"
```

### Sora CLI
```bash
python sora_browser_automation.py --check-login
python sora_browser_automation.py generate "A cat playing piano" -d 10 -r 16:9
python sora_browser_automation.py list
```

---

## Best Practices

### 1. Error Handling

Always wrap automation in try/except:

```python
try:
    result = await poster.post_tweet("Hello!")
    if not result.get('success'):
        logger.error(f"Post failed: {result.get('error')}")
except Exception as e:
    logger.error(f"Automation error: {e}")
```

### 2. Rate Limiting

Use session manager's rate limiting:

```python
if not session_manager.can_perform_action("post"):
    delay = session_manager.get_wait_time_for_action("post")
    await asyncio.sleep(delay)
```

### 3. Selector Strategy

Prefer stable selectors in this order:
1. `data-testid` or `data-e2e` attributes
2. `aria-label` attributes
3. Class names with semantic meaning
4. Tag + attribute combinations

```javascript
// Best
'[data-testid="tweetButton"]'
'[data-e2e="comment-post"]'

// Good
'[aria-label="Post"]'
'button[type="submit"]'

// Avoid (unstable)
'.css-1dbjc4n.r-1awozwy'
```

### 4. Wait Patterns

Always wait after navigation or actions:

```python
# After navigation
time.sleep(2)

# After clicking
time.sleep(0.5)

# After form submission
time.sleep(3)
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Not logged in" | Session expired | Log in manually in Safari |
| "Element not found" | Selector changed | Update selector in SELECTORS dict |
| AppleScript timeout | Page slow to load | Increase timeout value |
| "Permission denied" | macOS security | Enable Safari automation in System Preferences |

### Debug Mode

Enable verbose logging:

```python
from loguru import logger
logger.add("debug.log", level="DEBUG")
```

### Safari Permissions

Ensure Safari allows JavaScript from AppleScript:
1. Safari → Preferences → Advanced
2. Check "Show Develop menu in menu bar"
3. Develop → Allow JavaScript from Apple Events

---

## File Structure

```
Backend/
├── automation/
│   ├── safari_session_manager.py     # Login verification
│   ├── safari_app_controller.py      # Low-level Safari control
│   ├── safari_twitter_poster.py      # Twitter automation
│   ├── safari_threads_poster.py      # Threads automation
│   ├── safari_tiktok_cli.py          # TikTok CLI
│   ├── tiktok_engagement.py          # TikTok engagement
│   ├── tiktok_messenger.py           # TikTok DMs
│   ├── sora_browser_automation.py    # Sora video generation
│   └── safari_instagram_scraper.py   # Instagram scraping
├── services/
│   ├── platform_publishers.py        # API publishers
│   ├── background_publisher.py       # Async publishing
│   └── feedback_loop/                # AI content generation
├── api/
│   └── endpoints/
│       └── schedule.py               # Scheduling API
└── docs/
    ├── DEVELOPER-GUIDE.md            # This file
    ├── APPLESCRIPT-SAFARI-REFERENCE.md
    ├── API-CHEATSHEET.md
    └── SAFARI_AUTOMATION_CAPABILITIES.md
```
