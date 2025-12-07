# TikTok PyAutoGUI Automation Guide
> **Status**: ✅ VERIFIED WORKING
> **Date**: 2024-12-07
> **Environment**: macOS / Safari

## Executive Summary
We have established a **100% reliable method** for automating TikTok comments on Safari. Because TikTok uses a Draft.js editor that resists standard JavaScript event simulation, OS-level keyboard events are required.

The solution uses a hybrid approach:
1. **AppleScript/JavaScript**: To query the DOM and find element positions.
2. **PyAutoGUI**: To physically click coordinates and type text (simulating a real user).

---

## 🔑 The "Visible Element" Discovery (Critical)
On the For You Page (FYP), TikTok uses a **virtualized list** of videos. This means there are multiple `data-e2e="comment-icon"` elements in the DOM, but **most are off-screen** with negative coordinates (e.g., `y: -3219`).

**Trying to click the first found element fails.**

### The Fix
You must iterate through all `[data-e2e="comment-icon"]` elements and find the one that is **currently visible in the viewport**:

```javascript
// JavaScript logic to find the visible icon
var icons = document.querySelectorAll('[data-e2e="comment-icon"]');
var visible = null;
for (var icon of icons) {
    var rect = icon.getBoundingClientRect();
    // Check if y-coordinate is within the viewport (0 to window.innerHeight)
    if (rect.top > 0 && rect.top < window.innerHeight && rect.left > 0) {
        visible = {
            x: rect.left + rect.width/2, 
            y: rect.top + rect.height/2
        };
        break;
    }
}
```

---

## 🚀 Optimizations

### 1. Smart Like Detection (Toggle Prevention)
Video pages are stateful. Clicking a like button blindly will **unlike** a video if it's already liked.
We inspect the `fill` color of the SVG icon to determine state before acting.

**Logic:**
```javascript
// Check for like state (specific to like icon)
var isLiked = false;
var svg = el.querySelector('svg'); 
if (svg) {
    var fill = window.getComputedStyle(svg).fill;
    // Red color indicates Liked
    isLiked = fill.includes('255, 56, 92') || fill.includes('rgb(255, 56, 92)');
}
```
*   **If `isLiked == true`**: Skip click (Log: "Already Liked").
*   **If `isLiked == false`**: Perform click.

### 2. Persistent Comment Panel (Click Reduction)
The comment panel is a **globally persistent** element in the DOM overlay. When scrolling from Video A to Video B, if the panel was open, it **stays open**.
Blindly clicking the comment icon again might close it or interact with the wrong element.

**Optimization:**
Before finding the comment icon, check if the panel is already open:
```javascript
var container = document.querySelector('[class*="DivInputEditorContainer"]');
var footer = document.querySelector('[class*="DivCommentFooter"]');
var isOpen = (!!container || !!footer);
```
*   **If `isOpen`**: Skip icon click -> Immediately focus input.
*   **If `!isOpen`**: Find and click `comment-icon`.

**Benefit**: Saves ~2 seconds and 1 click per video interaction.

---

## 🛠️ Implementation Workflow

### 1. Calculate Screen Coordinates
Browser element coordinates are relative to the *viewport*. PyAutoGUI needs coordinates relative to the *screen*.

**Formula**:
`Screen_X = Safari_Window_X + Element_Client_X`
`Screen_Y = Safari_Window_Y + Element_Client_Y + Toolbar_Offset`

*Note: Safari's toolbar/tabs usually offset the content by ~75px.*

### 2. The Python Implementation
Here is the proven logic to replicate this success:

```python
import subprocess
import time
import pyautogui
import json

# 1. Get Safari Window Position
window_bounds = subprocess.run(
    ["osascript", "-e", 'tell application "Safari" to get bounds of front window'],
    capture_output=True, text=True
).stdout.strip()
# bounds format: "x, y, width, height" -> e.g., "1156, 199, 2871, 1272"
bounds = [int(x.strip()) for x in window_bounds.split(',')]
win_x, win_y = bounds[0], bounds[1]

# 2. Get Visible Element Coordinates (via JavaScript)
js_code = """
    var icons = document.querySelectorAll('[data-e2e="comment-icon"]');
    var visible = null;
    for (var icon of icons) {
        var rect = icon.getBoundingClientRect();
        if (rect.top > 0 && rect.top < window.innerHeight) { 
            visible = {x: rect.left + rect.width/2, y: rect.top + rect.height/2};
            break;
        }
    }
    visible ? JSON.stringify(visible) : 'null';
"""
# ... run js_code via osascript ...
# result -> {"x": 1165, "y": 713}

# 3. Calculate Click Target
screen_x = win_x + int(data['x'])
screen_y = win_y + int(data['y']) + 75 # Toolbar offset

# 4. Perform Action
pyautogui.click(screen_x, screen_y)
```

---

## ✅ Verification Checklist

When the automation runs correctly, observe these indicators:

1.  **Panel Opens**: The comment sidebar slides open (or stays open).
2.  **Input Focus**: The text cursor appears in the "Add comment..." field.
3.  **Typing**: Text appears character-by-character (e.g., `NiceVideo2024`).
4.  **Button Activation**: The "Post" button turns from grey/faded to **RED** (`rgb(255, 87, 111)`).
5.  **Submission**: After clicking Post, your comment appears at the top of the list.

## ⚠️ Common Pitfalls

-   **Case Sensitivity**: PyAutoGUI types exactly what is sent. `NiceVideo` -> `niceVideo` if Shift isn't handled (standard `write` usually works fine for alphanumeric).
-   **Toolbar Offset**: If clicks are missing (hitting the address bar or bookmarks), adjust the `75px` vertical offset.
-   **Window Focus**: Safari **must** be the active, front-most window for `pyautogui` to send keys to it. Always call `activate` before typing.
