# Using Safari for TikTok Login Recording

## Safari Support

The manual login recorder now supports **Safari** in addition to Chrome! Safari is great for:
- ✅ Native macOS integration
- ✅ Better privacy controls
- ✅ Less bot detection (looks more natural)
- ✅ Uses your existing Safari profile

## Quick Start

### 1. List Available Browsers

```bash
cd Backend
source venv/bin/activate
python3 automation/browser_profile_manager.py list
```

You'll see both Chrome and Safari profiles.

### 2. Select Safari Profile

```bash
python3 automation/browser_profile_manager.py select safari Default
```

### 3. Run Recorder with Safari

```bash
python3 automation/test_manual_login_recording.py safari
```

Or for Chrome:
```bash
python3 automation/test_manual_login_recording.py chrome
```

## How Safari Works

### Differences from Chrome

1. **Profile Handling**: 
   - Safari uses a single profile (not multiple like Chrome)
   - Profile data is in `~/Library/Safari`
   - Cookies are in binary format (harder to extract)

2. **Browser Launch**:
   - Uses Playwright's WebKit engine (Safari-compatible)
   - Launches as a regular context (not persistent like Chrome)
   - Still records all your actions

3. **Cookies**:
   - Safari cookies are managed by the browser
   - Session saving works, but cookie format differs
   - Still functional for login purposes

### What Gets Recorded

Same as Chrome:
- ✅ All clicks
- ✅ All inputs (field types)
- ✅ Page navigations
- ✅ Captcha detections
- ✅ Login completion

## Benefits of Safari

1. **More Natural**: Safari on macOS looks more like a real user
2. **Better Privacy**: Safari's privacy features may help avoid detection
3. **Native Integration**: Uses macOS Safari engine
4. **Familiar**: If you normally use Safari, it's your natural browser

## Usage Tips

1. **First Time**: Safari may ask for permissions - allow them
2. **Cookies**: Safari manages cookies automatically
3. **Extensions**: Safari extensions won't be available in the automated browser
4. **Performance**: Safari/WebKit is fast and efficient

## Troubleshooting

### Safari Not Found

- Make sure you're on macOS (Safari is macOS-only)
- Check that Safari is installed: `/Applications/Safari.app`

### Profile Not Detected

- Safari profile is in `~/Library/Safari`
- Make sure Safari has been used at least once
- Check that key files exist (Cookies.binarycookies, History.db)

### Browser Doesn't Launch

- Playwright needs WebKit support
- Install Playwright browsers: `playwright install webkit`
- Check Playwright installation

## Switching Between Browsers

You can easily switch:

```bash
# Use Safari
python3 automation/test_manual_login_recording.py safari

# Use Chrome  
python3 automation/test_manual_login_recording.py chrome
```

The system remembers your last choice in the config file.

## Notes

- Safari uses WebKit engine (same as Safari browser)
- Profile is auto-detected and saved
- All recording features work the same
- Session saving works for both browsers

