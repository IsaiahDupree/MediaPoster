# Login Recording System

## Overview

The login recorder captures all actions during TikTok login for analysis and automation replay.

## Current Status

**Recorder is running** - Actions are being recorded in memory and will be saved when:
- You press Ctrl+C in the recorder terminal
- Login is automatically detected as complete
- The recorder stops for any reason

## What Gets Recorded

### 1. Navigations
- Initial page load
- All URL changes
- Browser type (Safari.app vs Playwright)

### 2. Captcha Events
- Detection: When captchas appear
- Type: 3D, Slide, Whirl, Icon
- Solving: Automatic solving attempts
- Results: Success/failure status

### 3. Verification Codes
- SMS detection from Messages.app
- Code extraction (4-8 digits)
- Auto-fill into Safari
- Entry confirmation

### 4. Login Flow
- URL progression through login
- Form interactions
- Login success detection

### 5. Session Data
- Cookies extracted from Safari
- Final URL
- Browser state

## Recording File Format

```json
{
  "recorded_at": "2025-12-06T15:30:00",
  "total_actions": 15,
  "duration_seconds": 45.2,
  "browser_type": "safari",
  "using_actual_safari": true,
  "final_url": "https://www.tiktok.com/@username",
  "summary": {
    "navigations": 2,
    "url_changes": 5,
    "captchas_detected": 1,
    "captchas_solved": 1,
    "verification_codes": 1,
    "login_success": true
  },
  "actions": [
    {
      "type": "navigation",
      "timestamp": "2025-12-06T15:30:01",
      "relative_time": 0.0,
      "details": {
        "url": "https://www.tiktok.com/en/",
        "description": "Navigated to https://www.tiktok.com/en/"
      }
    }
  ]
}
```

## Viewing Recordings

### List All Recordings
```bash
python3 automation/review_recordings.py
```

### View Specific Recording
```bash
python3 automation/review_recordings.py 1  # View first recording
python3 automation/review_recordings.py 2  # View second recording
```

### Preview Recording Format
```bash
python3 automation/show_recording_format.py
```

## Recording Location

Recordings are saved to:
```
Backend/automation/recordings/login_recording_YYYYMMDD_HHMMSS.json
```

## Action Types

- `navigation` - Page navigation
- `url_change` - URL changed
- `captcha_detected` - Captcha appeared
- `captcha_solved` - Captcha solved
- `verification_code_entered` - SMS code entered
- `login_success` - Login completed
- `click` - User clicked (Playwright only)
- `input` - User typed (Playwright only)
- `keypress` - Special key pressed (Playwright only)

## Example Review Output

```
📹 LOGIN RECORDING REVIEW
================================================================================

📁 File: login_recording_20251206_153000.json
🕐 Recorded: 2025-12-06 15:30:00
⏱️  Duration: 45s
🌐 Browser: SAFARI
🍎 Using Actual Safari: Yes
🔗 Final URL: https://www.tiktok.com/@username

--------------------------------------------------------------------------------
📊 SUMMARY
--------------------------------------------------------------------------------
  Total Actions: 15
  Navigations: 2
  URL Changes: 5
  Captchas Detected: 1
  Captchas Solved: 1
  Verification Codes: 1
  Login Success: ✅ Yes

--------------------------------------------------------------------------------
📝 ACTION TIMELINE
--------------------------------------------------------------------------------

  1. 🌐 NAVIGATION [+0.0s]
     Navigated to https://www.tiktok.com/en/

  2. 🔗 URL_CHANGE [+5.2s]
     URL changed to https://www.tiktok.com/login
     From: https://www.tiktok.com/en/
     To:   https://www.tiktok.com/login

  3. ⚠️ CAPTCHA_DETECTED [+12.5s]
     Captcha detected in Safari: 3d
     Selector: .secsdk-captcha-wrapper
     Type: 3d

  4. ✅ CAPTCHA_SOLVED [+18.3s]
     Captcha solved automatically
     Type: 3d

  5. 📱 VERIFICATION_CODE_ENTERED [+25.7s]
     Verification code entered from SMS
     Code: 12**** (masked for security)

  6. 🎉 LOGIN_SUCCESS [+32.5s]
     Login completed in Safari.app
```

## Tips

1. **Recordings are saved on exit** - Press Ctrl+C to save current progress
2. **Check recordings directory** - Files appear after recorder stops
3. **Review format** - Use `review_recordings.py` for readable output
4. **Multiple recordings** - Each run creates a new file with timestamp

## Next Steps

After reviewing recordings, you can:
- Analyze the login flow
- Identify patterns
- Replay actions (future feature)
- Debug issues
- Optimize automation


