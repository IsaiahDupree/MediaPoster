# TikTok Automation Suite

**Status**: ✅ WORKING  
**Last Updated**: 2024-12-07  
**Platform**: macOS / Safari

## Overview

Automated TikTok engagement using PyAutoGUI and Safari JavaScript execution. Successfully performs:
- **Like** videos (with state detection to avoid unliking)
- **Comment** on videos (with posting verification)
- **Scroll** to next video (with video change detection)

## Prerequisites

### System Requirements
- macOS
- Safari browser
- Python 3.10+

### Safari Configuration
1. Open Safari > Settings > Advanced
2. Enable **"Show Develop menu in menu bar"**
3. Enable **"Allow JavaScript from Apple Events"**

### Python Dependencies
```bash
pip install pyautogui pytest
```

## Test Files

| File | Description | Status |
|------|-------------|--------|
| `test_pyautogui_automation.py` | Original working comment-only test | ✅ Working |
| `test_tiktok_full_engagement.py` | Full Like + Comment + Scroll | ✅ Working |
| `test_scroll_only.py` | Scroll method testing | ✅ Working |

## Running Tests

### From Terminal (Recommended)
```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
source venv/bin/activate
python -m pytest automation/tests/test_tiktok_full_engagement.py -v -s
```

### Important: Run from Terminal, NOT IDE
When running from an IDE like Cursor, keyboard focus issues prevent typing from working correctly. Always run from a standalone Terminal window.

## How It Works

### 1. Like Detection
```javascript
// Check if already liked (red SVG fill)
var svg = likeBtn.querySelector('svg');
var fill = window.getComputedStyle(svg).fill;
var isLiked = fill.includes('255, 56, 92');
```

### 2. Comment Typing
```python
# Focus editor via JS, then type with pyautogui
safari.run_js("document.querySelector('.public-DraftEditor-content').focus()")
safari.activate()
time.sleep(0.1)  # Critical timing!
pyautogui.write(comment_text, interval=0.02)
```

### 3. Scroll to Next Video
```python
# Must click video area first to deselect comment field
pyautogui.click(video_x, video_y)  # Click on video
time.sleep(0.2)
pyautogui.press('down')  # Scroll to next
```

## Key Discoveries

### Focus Timing is Critical
- `time.sleep(0.1)` between `safari.activate()` and `pyautogui.write()` prevents IDE from stealing focus
- Longer waits (0.3s+) allow IDE to reclaim focus

### DraftJS Editor
- TikTok uses DraftJS for comment input
- Cannot manipulate directly via JavaScript (crashes site)
- Must use OS-level keyboard input via PyAutoGUI

### Scroll Requirements
- Must click **outside** the comment text field before pressing down arrow
- Clicking on video area deselects the comment field
- Then down arrow scrolls to next video

## Selectors Reference

| Element | Selector |
|---------|----------|
| Like button | `[data-e2e="like-icon"]` |
| Comment icon | `span[data-e2e="comment-icon"]` |
| Comment editor | `.public-DraftEditor-content` |
| Post button | `[class*="DivPostButton"]` |
| Like count | `[data-e2e="like-count"]` |
| Comment count | `[data-e2e="comment-count"]` |
| Video author | `[data-e2e="video-author-uniqueid"]` |

## Troubleshooting

### Text not appearing in comment field
- Run from Terminal, not IDE
- Check that Safari is the active window
- Verify timing between activate and write

### Scroll not working
- Click on video area first to deselect comment field
- Ensure Safari has focus before pressing down

### Like verification shows NOT_LIKED after click
- Some videos may have restrictions
- The click may still have worked; check visually

## Future Work

- [ ] Data extraction (comments, metrics)
- [ ] Multi-video engagement loop
- [ ] Error recovery and retry logic
- [ ] Rate limiting to avoid detection
