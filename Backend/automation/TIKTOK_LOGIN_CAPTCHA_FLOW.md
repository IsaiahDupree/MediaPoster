# TikTok Login with Captcha Solving - Complete Flow

## Overview

This flow integrates Chrome profile management with TikTok login automation and automatic captcha solving. The system:

1. **Discovers Chrome profiles** on your computer
2. **Saves the profile configuration** for future use
3. **Starts Chrome** with your saved profile
4. **Automates TikTok login** 
5. **Detects and solves captchas** automatically using the RapidAPI captcha solver

## Components

### 1. Chrome Profile Manager (`chrome_profile_manager.py`)

Finds and manages Chrome profiles on your system:

```bash
# List all available profiles
python3 automation/chrome_profile_manager.py list

# Select and save a profile
python3 automation/chrome_profile_manager.py select Default
python3 automation/chrome_profile_manager.py select "Profile 1"

# Show saved profile
python3 automation/chrome_profile_manager.py show
```

**Features:**
- Auto-discovers all Chrome profiles (Default, Profile 1, Profile 2, etc.)
- Extracts profile metadata from Chrome's Local State
- Saves profile configuration to `chrome_profile_config.json`
- Works on macOS, Windows, and Linux

### 2. TikTok Login Automation (`tiktok_login_automation.py`)

Enhanced with:
- **Chrome Profile Integration**: Uses saved profile from Profile Manager
- **Captcha Detection**: Automatically detects captchas during login
- **Captcha Solving**: Integrates with TikTok Captcha Solver API
- **Session Saving**: Saves authenticated sessions for reuse

### 3. Test Script (`test_tiktok_login_with_captcha.py`)

Runs the complete flow:

```bash
python3 automation/test_tiktok_login_with_captcha.py
```

## Setup

### Prerequisites

1. **Environment Variables** (in `.env`):
   ```bash
   RAPIDAPI_KEY=your_rapidapi_key_here
   TIKTOK_USERNAME=your_tiktok_username
   TIKTOK_PASSWORD=your_tiktok_password
   ```

2. **Chrome Profile**: Make sure Chrome is installed and you have at least one profile

3. **Dependencies**: All required packages should be in `requirements.txt`

### Initial Setup

1. **Discover and save your Chrome profile**:
   ```bash
   cd Backend
   source venv/bin/activate
   python3 automation/chrome_profile_manager.py list
   python3 automation/chrome_profile_manager.py select Default
   ```

2. **Verify profile is saved**:
   ```bash
   python3 automation/chrome_profile_manager.py show
   ```

## Running the Full Flow

### Option 1: Test Script (Recommended)

```bash
cd Backend
source venv/bin/activate
python3 automation/test_tiktok_login_with_captcha.py
```

This will:
- Discover Chrome profiles
- Save the profile configuration
- Start Chrome with your profile
- Navigate to TikTok
- Attempt login
- Detect and solve any captchas
- Save session if successful

### Option 2: Direct Automation

```python
from automation.tiktok_login_automation import TikTokLoginAutomation

automation = TikTokLoginAutomation(
    headless=False,
    save_session=True,
    profile_name="Default"  # or None to use saved profile
)

success = await automation.login()
```

## How It Works

### 1. Chrome Profile Discovery

The system searches for Chrome profiles in the standard location:
- **macOS**: `~/Library/Application Support/Google/Chrome`
- **Windows**: `~/AppData/Local/Google/Chrome/User Data`
- **Linux**: `~/.config/google-chrome`

It finds:
- Default profile
- Numbered profiles (Profile 1, Profile 2, etc.)
- Profile metadata from Local State

### 2. Profile Snapshot

When starting Chrome, the system:
- Creates a temporary copy of your Chrome profile
- Copies essential files (Cookies, Preferences, Login Data, etc.)
- Excludes caches to save time and space
- Launches Chrome with the snapshot (allows Chrome to be open)

### 3. Login Flow

1. Navigate to TikTok
2. Click login button
3. Handle Google OAuth popup
4. Wait for login completion

### 4. Captcha Detection & Solving

During login, the system:
- Continuously monitors for captcha elements
- Detects captcha type (3D, Slide, Whirl, Icon)
- Extracts captcha images
- Calls TikTok Captcha Solver API
- Applies the solution automatically
- Verifies captcha is solved

### 5. Session Saving

If login succeeds:
- Cookies are saved to `automation/sessions/tiktok_session.json`
- Can be reused in future runs
- Reduces need for repeated logins

## API Usage & Limits

⚠️ **Important**: The captcha solver makes API calls that consume credits.

- Each captcha solve = 1 API call
- Failed attempts still consume credits
- Check your RapidAPI subscription limits

**To minimize API usage:**
- The system only solves captchas when detected
- Uses saved sessions when available
- Implements retry logic with exponential backoff

## Troubleshooting

### Chrome Profile Not Found

```bash
# List profiles to see what's available
python3 automation/chrome_profile_manager.py list

# Select a different profile
python3 automation/chrome_profile_manager.py select "Profile 1"
```

### Captcha Solving Fails

1. Check `RAPIDAPI_KEY` is set correctly
2. Verify API subscription is active
3. Check API response format (may need payload adjustments)
4. Review screenshots in `automation/screenshots/`

### Login Fails

1. Check `TIKTOK_USERNAME` and `TIKTOK_PASSWORD` in `.env`
2. Verify Chrome profile has valid cookies
3. Check screenshots for visual debugging
4. Review logs for specific errors

### Profile Locked

If Chrome is open, the profile may be locked. Options:
- Close Chrome before running
- Use a different profile
- The snapshot system should handle this, but may fail on some files

## File Structure

```
Backend/automation/
├── chrome_profile_manager.py      # Profile discovery & management
├── chrome_profile_config.json      # Saved profile configuration
├── tiktok_login_automation.py      # Main automation class
├── test_tiktok_login_with_captcha.py  # Test script
├── sessions/
│   └── tiktok_session.json         # Saved login session
└── screenshots/                    # Debug screenshots
    ├── 01_homepage_*.png
    ├── 02_login_modal_*.png
    └── captcha_*.png
```

## Next Steps

1. **Run the test script** to verify everything works
2. **Monitor API usage** to stay within limits
3. **Review screenshots** if issues occur
4. **Adjust captcha solving logic** if API response format changes

## Notes

- Chrome must be installed and accessible
- The automation runs in non-headless mode (visible browser) for captcha solving
- Profile snapshots are cleaned up after automation completes
- Saved sessions expire when cookies expire (typically 30 days)

