# TikTok Comment Automation - Technical Documentation

## Overview

This module provides automated commenting for TikTok videos using Safari automation via AppleScript.

## Key Features

| Feature | Method | Status |
|---------|--------|--------|
| Post a comment | `post_comment(text)` | ✅ Working |
| Extract all comments | `get_comments(limit)` | ✅ Working |
| Save comments to JSON | `save_comments(filepath)` | ✅ Working |
| Verify comment posted | Built into `post_comment()` | ✅ Working |

---

## Comment Posting Flow

The `post_comment()` method follows this 5-step process:

### Step 1: Open Comments Panel
```python
await self.open_comments()
```
- Clicks the comment button (data-e2e="comment-icon")
- Opens the comments overlay panel

### Step 2: Click Comment Input Field
```python
await self._click_element(self.SELECTORS["comment_input"])
```
- Selector: `[data-e2e="comment-input"]` or `[data-e2e="comment-text"]`
- Focuses the text input field

### Step 3: Type Comment Text
```python
await self._type_text(text)
```
- Simulates typing the comment text character by character

### Step 4: Click Post Button
```python
await self._click_element(self.SELECTORS["comment_post"])
```
- Selector: `[data-e2e="comment-post"]`
- Submits the comment

### Step 5: Verify Comment Posted
```python
verified = await self._verify_comment_posted(text)
```
- Searches for the comment text in `[data-e2e="comment-level-1"]` elements
- Confirms the comment appears in the comments list

---

## Comment Extraction

The `get_comments()` method extracts existing comments:

### Selectors Used
| Element | Selector |
|---------|----------|
| Comment text | `[data-e2e="comment-level-1"]` |
| Username | `[data-e2e="comment-username-1"]` |

### Return Format
```python
[
    {"username": "user123", "text": "Great video!", "likes": "0", "index": 0},
    {"username": "user456", "text": "Love this!", "likes": "0", "index": 1}
]
```

---

## Usage Examples

### Post a Comment
```python
from automation.tiktok_engagement import TikTokEngagement

engagement = TikTokEngagement()
await engagement.start()
await engagement.navigate_to_fyp()

result = await engagement.post_comment("Great video! 🔥")
# Returns: {"success": True, "text": "Great video! 🔥", "verified": True}

if result["verified"]:
    print("Comment confirmed in comments list!")
```

### Extract Comments
```python
comments = await engagement.get_comments(limit=20)
for c in comments:
    print(f"@{c['username']}: {c['text']}")
```

### Save Comments to File
```python
result = await engagement.save_comments(filepath="/path/to/comments.json")
# Returns: {"success": True, "filepath": "...", "count": 15}
```

---

## TikTok DOM Selectors Reference

| Element | data-e2e Attribute | Usage |
|---------|-------------------|-------|
| Comment Button | `comment-icon` | Open comments panel |
| Comment Input | `comment-input`, `comment-text` | Text input field |
| Post Button | `comment-post` | Submit comment |
| Comment Text | `comment-level-1` | Extract comment content |
| Username | `comment-username-1` | Extract commenter username |
| Comment Count | `comment-count` | Number of comments |

---

## Rate Limiting

Comments are rate-limited to prevent detection:
- Default: 1 comment per 30 seconds minimum
- Configurable in `TikTokSessionManager`

---

## Requirements

1. **Safari Permissions**:
   - Safari → Develop → Allow JavaScript from Apple Events ✅
   - System Settings → Full Disk Access → Terminal ✅

2. **Logged In**: User must be logged into TikTok in Safari
