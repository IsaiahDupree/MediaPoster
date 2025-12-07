# Manual Login Recording Guide

## What It Does

The manual login recorder watches and records all your actions while you sign into TikTok manually. This allows you to:

1. **Perform login yourself** - No automation, just you doing it naturally
2. **Record all actions** - Every click, input, navigation is recorded
3. **Detect captchas** - System watches for captchas and can alert you
4. **Save session** - After successful login, cookies are saved
5. **Learn the flow** - Recording shows exactly what actions were taken

## How to Use

### Start Recording

```bash
cd Backend
source venv/bin/activate
python3 automation/test_manual_login_recording.py
```

### What Happens

1. **Chrome opens** with your saved profile
2. **Navigates to TikTok** automatically
3. **Recording starts** - all your actions are being watched
4. **You perform login** manually:
   - Click login button
   - Enter credentials
   - Handle any captchas
   - Complete OAuth if needed
5. **System detects** when login is complete (profile icon appears)
6. **Press Ctrl+C** when done, or wait for auto-detection

### What Gets Recorded

- ✅ All clicks (element, text, selector)
- ✅ All inputs (field type, but not values for privacy)
- ✅ Page navigations
- ✅ Special key presses (Enter, Tab, etc.)
- ✅ Captcha detections
- ✅ URL changes
- ✅ Login completion

### Output Files

After recording, you'll get:

1. **Recording File**: `automation/recordings/login_recording_YYYYMMDD_HHMMSS.json`
   - Contains all recorded actions with timestamps
   - Can be analyzed or replayed later

2. **Session File**: `automation/sessions/tiktok_session.json`
   - Contains cookies from successful login
   - Can be reused for future automation

3. **Screenshots**: `automation/screenshots/captcha_*.png`
   - Captured when captchas are detected

## Example Recording Output

```json
{
  "recorded_at": "2025-12-06T15:30:00",
  "total_actions": 15,
  "duration_seconds": 45.2,
  "actions": [
    {
      "type": "navigation",
      "timestamp": "2025-12-06T15:30:01",
      "relative_time": 1.0,
      "details": {
        "url": "https://www.tiktok.com/en/",
        "description": "Navigated to https://www.tiktok.com/en/"
      }
    },
    {
      "type": "click",
      "timestamp": "2025-12-06T15:30:05",
      "relative_time": 5.2,
      "details": {
        "tag": "DIV",
        "text": "Log in",
        "selector": "#header-login-button",
        "description": "Clicked DIV: Log in"
      }
    }
  ]
}
```

## Benefits

1. **No Bot Detection** - You're doing it manually, so no automation flags
2. **Learn the Flow** - See exactly what actions are needed
3. **Handle Complex Auth** - OAuth, 2FA, etc. handled naturally
4. **Captcha Awareness** - System alerts you if captchas appear
5. **Session Reuse** - Saved cookies can be used later

## Tips

- **Take your time** - No rush, the recorder is patient
- **Watch for captcha alerts** - System will notify you if one appears
- **Let it detect completion** - System auto-detects when login succeeds
- **Review the recording** - Check the JSON file to see what happened

## Next Steps

After recording, you can:

1. **Review the recording** - See what actions were taken
2. **Use saved session** - Future automation can use the cookies
3. **Replay actions** - (Future feature) Automate based on recording
4. **Analyze flow** - Understand the exact login sequence

## Troubleshooting

### Browser doesn't open
- Check Chrome is installed
- Verify profile is saved: `python3 automation/chrome_profile_manager.py show`

### Recording stops early
- Make sure not to close the browser manually
- Use Ctrl+C in terminal to stop gracefully

### Login not detected
- System looks for profile icon or upload button
- If login succeeds but not detected, press Ctrl+C manually
- Session will still be saved

### Captcha appears
- System will alert you
- Solve it manually (you're in control)
- Recording continues normally

