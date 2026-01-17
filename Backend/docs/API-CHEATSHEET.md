# MediaPoster API Cheatsheet

**Last Updated:** 2026-01-16

Quick reference for all public methods, interfaces, and common patterns.

---

## Safari Automation Classes

### SafariSessionManager

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `require_login(platform)` | `Platform` enum | `bool` | Check/ensure login |
| `check_login_status(platform)` | `Platform` enum | `LoginState` | Detailed status |
| `can_perform_action(action)` | `str` | `bool` | Rate limit check |
| `get_wait_time_for_action(action)` | `str` | `float` | Seconds to wait |

### SafariTwitterPoster

| Method | Parameters | Returns |
|--------|------------|---------|
| `post_tweet(text, media_paths)` | `str`, `List[str]` | `Dict` |
| `post_thread(tweets)` | `List[str]` | `Dict` |
| `reply_to_tweet(url, text, media)` | `str`, `str`, `List[str]` | `Dict` |
| `create_poll(text, options, days)` | `str`, `List[str]`, `int` | `Dict` |
| `schedule_tweet(text, time, media)` | `str`, `datetime`, `List[str]` | `Dict` |

### TwitterNotifications

| Method | Parameters | Returns |
|--------|------------|---------|
| `get_notifications(limit, mentions_only)` | `int`, `bool` | `Dict` |
| `get_unread_count()` | - | `int` |

### TwitterDM

| Method | Parameters | Returns |
|--------|------------|---------|
| `get_conversations(limit)` | `int` | `Dict` |
| `open_conversation(username)` | `str` | `bool` |
| `read_messages(limit)` | `int` | `Dict` |
| `send_message(text)` | `str` | `Dict` |

### SafariThreadsPoster

| Method | Parameters | Returns |
|--------|------------|---------|
| `post_thread(text, media_paths)` | `str`, `List[str]` | `Dict` |
| `reply_to_thread(url, text, media)` | `str`, `str`, `List[str]` | `Dict` |

### ThreadsNotifications

| Method | Parameters | Returns |
|--------|------------|---------|
| `get_notifications(limit)` | `int` | `Dict` |

### ThreadsDM

| Method | Parameters | Returns |
|--------|------------|---------|
| `get_conversations(limit)` | `int` | `Dict` |
| `send_message(text, username)` | `str`, `str` | `Dict` |

### TikTokEngagement

| Method | Parameters | Returns |
|--------|------------|---------|
| `start(url)` | `str` | `bool` |
| `navigate_to_fyp()` | - | `bool` |
| `navigate_to_profile(username)` | `str` | `bool` |
| `like_current_video()` | - | `bool` |
| `post_comment(text)` | `str` | `Dict` |
| `follow_user()` | - | `bool` |
| `cleanup()` | - | - |

### TikTokNotifications

| Method | Parameters | Returns |
|--------|------------|---------|
| `get_notifications(limit)` | `int` | `Dict` |
| `get_all_activity(limit)` | `int` | `Dict` |

### TikTokMessenger

| Method | Parameters | Returns |
|--------|------------|---------|
| `open_inbox()` | - | `bool` |
| `get_conversations()` | - | `List[Conversation]` |
| `open_conversation(username)` | `str` | `bool` |
| `send_message(text)` | `str` | `bool` |
| `get_messages(limit)` | `int` | `List[Message]` |
| `send_to_user(username, text)` | `str`, `str` | `bool` |

### SoraBrowserAutomation

| Method | Parameters | Returns |
|--------|------------|---------|
| `open_sora()` | - | `bool` |
| `check_login()` | - | `bool` |
| `generate_video(prompt, duration, ratio)` | `str`, `int`, `str` | `Dict` |
| `download_video(job_id)` | `str` | `str` |

---

## API Publishers

### PublishRequest

```python
from services.platform_publishers import PublishRequest, MediaType, Platform

request = PublishRequest(
    media_path="/path/to/file.mp4",
    media_type=MediaType.VIDEO,      # VIDEO, IMAGE, REEL, SHORT, STORY, CAROUSEL
    title="Optional title",
    description="Post description",
    hashtags=["#tag1", "#tag2"],
    account_id="account_123",
    platform=Platform.TIKTOK,        # TIKTOK, INSTAGRAM, YOUTUBE
    scheduled_time=None,             # ISO datetime string for scheduling
    thumbnail_path=None,
    privacy="public",                # public, private, unlisted
    metadata={}                      # Platform-specific options
)
```

### PublishResult

```python
result = await publisher.publish(request)

result.success          # bool
result.status           # PublishStatus enum
result.platform         # Platform enum
result.post_id          # str - Platform's post ID
result.post_url         # str - URL to the post
result.error_message    # str - Error if failed
result.published_at     # str - ISO datetime
result.metadata         # Dict - Additional data
```

### Publisher Classes

```python
# TikTok
from services.platform_publishers import TikTokPublisher
publisher = TikTokPublisher({"access_token": "..."})

# Instagram
from services.platform_publishers import InstagramPublisher
publisher = InstagramPublisher({
    "access_token": "...",
    "instagram_user_id": "..."
})

# YouTube
from services.platform_publishers import YouTubePublisher
publisher = YouTubePublisher({"access_token": "..."})
```

---

## Enums

### Platform
```python
from automation.safari_session_manager import Platform

Platform.TWITTER    # x.com
Platform.TIKTOK     # tiktok.com
Platform.INSTAGRAM  # instagram.com
Platform.THREADS    # threads.net
Platform.SORA       # sora.com
Platform.YOUTUBE    # youtube.com
```

### MediaType
```python
from services.platform_publishers import MediaType

MediaType.VIDEO
MediaType.IMAGE
MediaType.REEL
MediaType.SHORT
MediaType.STORY
MediaType.CAROUSEL
```

### PublishStatus
```python
from services.platform_publishers import PublishStatus

PublishStatus.PENDING
PublishStatus.UPLOADING
PublishStatus.PROCESSING
PublishStatus.PUBLISHED
PublishStatus.FAILED
PublishStatus.SCHEDULED
```

---

## Environment Variables

| Variable | Description | Used By |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Content generation |
| `BLOTATO_API_KEY` | Blotato publishing API | Quick posting |
| `TIKTOK_ACCESS_TOKEN` | TikTok API token | TikTokPublisher |
| `INSTAGRAM_ACCESS_TOKEN` | IG Graph API token | InstagramPublisher |
| `INSTAGRAM_USER_ID` | Instagram user ID | InstagramPublisher |
| `YOUTUBE_ACCESS_TOKEN` | YouTube API token | YouTubePublisher |
| `DATABASE_URL` | PostgreSQL connection | Scheduling DB |

---

## CLI Quick Reference

### Twitter
```bash
# Post
python safari_twitter_poster.py post "Text" [-m MEDIA]

# Thread
python safari_twitter_poster.py thread -t "Tweet1" "Tweet2"

# Reply
python safari_twitter_poster.py reply URL "Text"

# Notifications
python safari_twitter_poster.py notifications [--mentions] [--unread]

# DMs
python safari_twitter_poster.py dm list
python safari_twitter_poster.py dm read USERNAME
python safari_twitter_poster.py dm send USERNAME "Message"
```

### Threads
```bash
python safari_threads_poster.py post "Text" [-m MEDIA]
python safari_threads_poster.py reply URL "Text"
python safari_threads_poster.py notifications
python safari_threads_poster.py dm list
python safari_threads_poster.py dm send USERNAME "Message"
```

### TikTok
```bash
python safari_tiktok_cli.py --check-login
python safari_tiktok_cli.py like URL
python safari_tiktok_cli.py comment URL "Text"
python safari_tiktok_cli.py follow @USERNAME
python safari_tiktok_cli.py notifications
python safari_tiktok_cli.py dm list|read|send
```

### Sora
```bash
python sora_browser_automation.py --check-login
python sora_browser_automation.py generate "Prompt" [-d DURATION] [-r RATIO]
python sora_browser_automation.py list
```

---

## Common Selectors

### Twitter/X
```python
SELECTORS = {
    "post_button": '[data-testid="tweetButton"]',
    "compose": '[data-testid="tweetTextarea_0"]',
    "like": '[data-testid="like"]',
    "reply": '[data-testid="reply"]',
    "notification": '[data-testid="notification"]',
    "dm_inbox": '[data-testid="DM_Inbox"]',
}
```

### TikTok
```python
SELECTORS = {
    "like_button": '[data-e2e="like-icon"]',
    "comment_button": '[data-e2e="comment-icon"]',
    "comment_input": '[data-e2e="comment-input"]',
    "comment_post": '[data-e2e="comment-post"]',
    "follow_button": '[data-e2e="follow-button"]',
    "profile_icon": '[data-e2e="profile-icon"]',
}
```

### Threads
```python
SELECTORS = {
    "compose": '[role="textbox"]',
    "post_button": 'div[role="button"]',
    "activity_item": '[role="listitem"]',
    "user_link": 'a[href*="/@"]',
}
```

---

## Quick Patterns

### Delay Between Actions
```python
import time
time.sleep(0.5)  # After click
time.sleep(2)    # After navigation
time.sleep(3)    # After form submit
```

### Retry on Failure
```python
for attempt in range(3):
    result = await poster.post_tweet(text)
    if result.get('success'):
        break
    time.sleep(2)
```

### Check Login First
```python
from automation.safari_session_manager import SafariSessionManager, Platform

manager = SafariSessionManager()
if not manager.require_login(Platform.TWITTER):
    print("Please log in manually")
    exit(1)
```

### Async Publish
```python
import asyncio
from services.platform_publishers import TikTokPublisher

async def publish():
    publisher = TikTokPublisher(credentials)
    result = await publisher.publish(request)
    await publisher.close()
    return result

result = asyncio.run(publish())
```

---

## Return Value Patterns

### Success Response
```python
{
    "success": True,
    "post_url": "https://x.com/user/status/123",
    "post_id": "123456789",
    "platform": "twitter"
}
```

### Error Response
```python
{
    "success": False,
    "error": "Element not found",
    "requires_login": False
}
```

### Notifications Response
```python
{
    "success": True,
    "count": 15,
    "notifications": [
        {"text": "...", "user": "username", "time": "2026-01-16T..."}
    ]
}
```

### DM List Response
```python
{
    "success": True,
    "count": 10,
    "conversations": [
        {"name": "User", "preview": "Last message...", "unread": True}
    ]
}
```
