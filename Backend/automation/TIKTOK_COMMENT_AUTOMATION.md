# TikTok Comment Automation - Achievement & Investigation

## ✅ Verified Working (2024-12-06)

### Successful Comment Post
```
Comment: "5t3g3"
Username: isaiah.c.smith  
Position: #1 at top of comments list
Total comments: 6
```

### What Works
| Step | Method | Status |
|------|--------|--------|
| Open comments panel | JS click `[data-e2e=comment-icon]` | ✅ |
| Focus input field | JS click `[data-e2e=comment-input]` | ✅ |
| Detect text in field | JS `el.textContent` | ✅ |
| Detect Post button active | JS `getComputedStyle(btn).color` = `rgb(255, 87, 111)` (RED) | ✅ |
| Click Post button | JS click `[class*=DivPostButton]` | ✅ |
| Verify comment posted | JS query `[data-e2e=comment-level-1]` | ✅ |

---

## 🔬 Current Investigation: Automated Typing

### The Challenge
TikTok uses **Draft.js** editor which requires React state updates triggered by real keyboard events.

### Methods Tested (2024-12-06)

| # | Method | Text Appears? | Button Active? | Notes |
|---|--------|--------------|----------------|-------|
| 1 | `el.innerText = "text"` | ✅ Yes | ❌ Grey | React state not updated |
| 2 | `el.innerHTML = "text"` | ✅ Yes | ❌ Grey | Same |
| 3 | `el.textContent = "text"` | ✅ Yes | ❌ Grey | Same |
| 4 | `dispatchEvent(new InputEvent())` | ❌ No | ❌ Grey | Not recognized |
| 5 | `document.execCommand("insertText")` | ❌ No | ❌ Grey | Deprecated |
| 6 | AppleScript `keystroke` | ❌ No | ❌ Grey | Goes to wrong element |
| 7 | cliclick physical click + type | ❌ No | ❌ Grey | Coordinates issue |
| 8 | KeyboardEvent simulation (keydown/keypress/keyup) | ❌ No | ❌ Grey | Draft.js ignores |
| 9 | ClipboardEvent paste with DataTransfer | ❌ No | ❌ Grey | Not recognized |
| 10 | Direct React props.onKeyDown() call | ❌ No | ❌ Grey | No effect |
| 11 | InputEvent with beforeinput | ❌ No | ❌ Grey | Event fires but no insert |

### Key Discovery
**Manual typing works!** When user typed `5t3g3`:
- Text appeared in field ✅
- Post button turned RED (`rgb(255, 87, 111)`) ✅
- JS click on Post button worked ✅
- Comment posted successfully ✅

### ✅ WORKING METHOD: pyautogui (Method #12)

```python
import pyautogui
import subprocess
import time

# Focus the comment input
subprocess.run(['osascript', '-e', '''
tell application "Safari"
    activate
    do JavaScript "var el=document.querySelector('[data-e2e=comment-input]');el.click();el.focus();" in current tab of front window
end tell
'''])
time.sleep(1)

# Type text with pyautogui
pyautogui.typewrite('Your comment here', interval=0.05)

# Click Post button
subprocess.run(['osascript', '-e', '''
tell application "Safari"
    do JavaScript "document.querySelector('[class*=DivPostButton]').click();" in current tab of front window
end tell
'''])
```

### Verified Results (2024-12-06 21:11)
```
Comment: "YAUTO2111p"
Position: #1 at top of comments
Username: isaiah visible
Post button: rgb(255, 87, 111) (RED - active)
```

---

## Summary

| Approach | Works? | Button Activates? |
|----------|--------|-------------------|
| JavaScript DOM manipulation | ❌ | ❌ Grey |
| JavaScript events | ❌ | ❌ Grey |
| AppleScript keystroke | ❌ | ❌ Grey |
| cliclick physical mouse | ❌ | ❌ Grey |
| React fiber manipulation | ❌ | ❌ Grey |
| **pyautogui typing** | ✅ | ✅ RED |

---

## Working Selectors

```javascript
// Comment button
document.querySelector("[data-e2e=comment-icon]")

// Comment input
document.querySelector("[data-e2e=comment-input]")
document.querySelector("[contenteditable=true]")

// Post button
document.querySelector("[class*=DivPostButton]")
document.querySelector("[data-e2e=comment-post]")

// Comments list
document.querySelectorAll("[data-e2e=comment-level-1]")

// Usernames
document.querySelectorAll("[data-e2e=comment-username-1]")
```

---

## Next Steps
1. Research Draft.js editor state manipulation
2. Try React devtools approach to set component state
3. Test low-level keyboard event simulation
4. Consider Playwright/Puppeteer with headless Chrome (different from Safari)
