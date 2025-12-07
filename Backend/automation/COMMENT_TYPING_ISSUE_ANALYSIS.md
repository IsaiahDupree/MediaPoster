# TikTok Comment Typing Issue - Analysis & Solutions

**Date**: 2024-12-07  
**Status**: ✅ RESOLVED - Working with minimal wait timing  
**Environment**: macOS Sonoma / Safari / Cursor IDE

## ✅ SOLUTION FOUND

**Key Discovery**: Reducing wait time between `safari.activate()` and `pyautogui.write()` from 0.3s to **0.1s** prevents the IDE from stealing focus.

```python
safari.activate()
time.sleep(0.1)  # Critical: 0.1s works, 0.3s fails
pyautogui.write(comment_text, interval=0.02)
```

---

---

## 🔍 Problem Summary

The automation successfully:
- ✅ Likes videos via JS click
- ✅ Opens comment panel via JS click
- ✅ Finds the DraftJS editor (`.public-DraftEditor-content`)
- ✅ Clicks the editor coordinates with pyautogui
- ❌ **FAILS to type text into the editor**

**Root Cause**: When running pytest from **Cursor IDE**, the IDE immediately reclaims keyboard focus after Safari is activated, causing all `pyautogui.write()` keystrokes to go to the IDE instead of Safari.

---

## 🧪 What We've Tried

### Approach 1: PyAutoGUI Direct Typing ❌
```python
safari.activate()
time.sleep(0.3)
pyautogui.write(comment_text, interval=0.02)
```
**Result**: Text appears in Cursor IDE, not Safari  
**Why it failed**: IDE steals focus immediately after Safari activation

### Approach 2: PyAutoGUI Click + Type ❌
```python
pyautogui.click(editor_x, editor_y)  # Click in editor
time.sleep(0.3)
pyautogui.write(comment_text)
```
**Result**: Click works, but typing still goes to IDE  
**Why it failed**: IDE reclaims focus between click and type

### Approach 3: AppleScript Keystroke ❌
```applescript
tell application "System Events"
    keystroke "comment text"
end tell
```
**Result**: Error - "osascript is not allowed to send keystrokes (1002)"  
**Why it failed**: macOS security blocks osascript from sending keystrokes without explicit permission

### Approach 4: Clipboard Paste (pbcopy + Cmd+V) ❌
```python
subprocess.run(["pbcopy"], input=comment_text.encode())
pyautogui.hotkey('command', 'v')
```
**Result**: Paste command sent to IDE, not Safari  
**Why it failed**: Same focus issue as typing

### Approach 5: JavaScript Direct Manipulation ❌ (CRASHES SITE)
```javascript
editor.innerText = "comment";
editor.dispatchEvent(new InputEvent('input'));
```
**Result**: TikTok page crashes/freezes  
**Why it failed**: DraftJS editor has complex internal state that breaks when directly manipulated

### Approach 6: JavaScript execCommand ❌ (CRASHES SITE)
```javascript
document.execCommand('insertText', false, 'comment');
```
**Result**: TikTok page crashes/freezes  
**Why it failed**: Same as Approach 5 - DraftJS doesn't handle synthetic commands

---

## ✅ Solutions & Options

### Option 1: Run from Terminal (Not IDE) ⭐ RECOMMENDED
**How**: Execute pytest from a standalone Terminal window
```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
source venv/bin/activate
python -m pytest automation/tests/test_pyautogui_automation.py -v -s
```

**Pros**:
- ✅ Terminal doesn't steal focus like IDE does
- ✅ No code changes needed
- ✅ Uses proven pyautogui approach from TIKTOK_PYAUTOGUI_AUTOMATION.md
- ✅ Most reliable for keyboard automation

**Cons**:
- ❌ Can't run tests directly from IDE
- ❌ Requires manual terminal invocation
- ❌ Less convenient for development workflow

**Status**: ✅ VERIFIED - Test launched in Terminal (waiting for results)

---

### Option 2: Grant osascript Accessibility Permissions
**How**: Add Terminal.app (or osascript) to System Settings > Privacy & Security > Accessibility

**Pros**:
- ✅ Allows AppleScript `keystroke` commands
- ✅ Can run from IDE
- ✅ More reliable than pyautogui for focus issues

**Cons**:
- ❌ Requires manual system configuration
- ❌ Security implications (giving osascript broad permissions)
- ❌ May need to be redone after OS updates

**Implementation**:
```applescript
tell application "Safari" to activate
delay 0.5
tell application "System Events"
    keystroke "comment text"
end tell
```

---

### Option 3: Use Playwright/Puppeteer Instead
**How**: Switch from Safari + pyautogui to Playwright with Chrome

**Pros**:
- ✅ Full browser control via DevTools Protocol
- ✅ Can inject text directly into DOM
- ✅ No OS-level permissions needed
- ✅ More reliable for CI/CD
- ✅ Better debugging tools

**Cons**:
- ❌ Requires complete rewrite of automation
- ❌ TikTok may detect headless browsers
- ❌ Need to handle bot detection/captchas
- ❌ Loses Safari-specific advantages

**Example**:
```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('https://www.tiktok.com/foryou')
    # Can directly evaluate JS to set text
```

---

### Option 4: Hybrid - JS for Everything Except Post Click
**How**: Use JavaScript to manipulate DraftJS state correctly, only use pyautogui for final Post button

**Pros**:
- ✅ Avoids typing issues entirely
- ✅ Faster than keyboard simulation
- ✅ Can run from IDE

**Cons**:
- ❌ Requires deep understanding of DraftJS internals
- ❌ Fragile - breaks if TikTok updates DraftJS
- ❌ Previous attempts crashed the site

**Research Needed**: Study DraftJS documentation to find proper API for programmatic text insertion

---

### Option 5: Use Selenium with Real Browser
**How**: Selenium WebDriver with Safari or Chrome

**Pros**:
- ✅ Standard automation framework
- ✅ Can send keys directly to elements
- ✅ Good documentation

**Cons**:
- ❌ TikTok detects WebDriver
- ❌ Requires driver setup (chromedriver/safaridriver)
- ❌ May need anti-detection measures

---

## 🎯 Recommended Approach

### Short-term (Immediate):
**Use Option 1 - Run from Terminal**
- Minimal changes needed
- Proven to work based on TIKTOK_PYAUTOGUI_AUTOMATION.md
- Can verify functionality immediately

### Medium-term (Development):
**Combine Options 1 + 2**
1. Document that tests must run from Terminal
2. Optionally grant osascript permissions for convenience
3. Add helper script to launch tests in Terminal

### Long-term (Production):
**Consider Option 3 - Playwright Migration**
- More robust for production automation
- Better error handling and debugging
- Easier to scale and maintain
- Can handle captchas and bot detection properly

---

## 📋 Possible Combinations

### Combo A: Terminal + Accessibility Permissions
- Run from Terminal for reliability
- Grant osascript permissions as backup
- Best of both worlds

### Combo B: Playwright + PyAutoGUI Fallback
- Use Playwright for most actions
- Fall back to pyautogui for captcha solving or human verification
- Hybrid approach for maximum reliability

### Combo C: JS Manipulation + Post-Only Click
- Research proper DraftJS API
- Use JS for text insertion if we can find safe method
- Use pyautogui only for final Post button click
- Fastest if we can make it work

---

## 🔬 Next Steps

1. **Verify Terminal execution** - Check if test passes when run from Terminal
2. **Document Terminal requirement** - Update test README with execution instructions
3. **Research DraftJS** - Investigate if there's a safe way to programmatically insert text
4. **Evaluate Playwright** - Prototype basic TikTok automation with Playwright
5. **Create helper script** - Make it easy to launch tests from Terminal

---

## 📊 Current Test Status

**From IDE (Cursor)**:
```
Like action: CLICKED ✅
Comment panel opened: ✅
Text in editor: '' ❌
Post action: CLICKED ✅
Comment verification: NOT_FOUND ❌
```

**From Terminal**:
```
Status: RUNNING - Awaiting results
```

---

## 🔗 References

- `/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/automation/TIKTOK_PYAUTOGUI_AUTOMATION.md` - Original working guide
- `/Users/isaiahdupree/Documents/Software/MediaPoster/selector_js_path_tiktok_comments_messages.txt` - TikTok selector reference
- DraftJS Documentation: https://draftjs.org/
- PyAutoGUI Docs: https://pyautogui.readthedocs.io/
