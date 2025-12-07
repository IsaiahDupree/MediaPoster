# SMS Verification Code Reader

## Overview

The SMS code reader automatically detects verification codes sent to your iPhone via SMS and enters them into Safari during login.

## How It Works

1. **Monitors Messages.app** - Watches for new SMS messages
2. **Extracts Codes** - Finds verification codes (4-8 digits)
3. **Auto-Fills** - Enters the code into the verification field in Safari
4. **Records Action** - Logs the code entry in the recording

## Features

- ✅ Automatic code detection from SMS
- ✅ Works with TikTok, Google, and other services
- ✅ Filters by keywords (TikTok, verification, code, etc.)
- ✅ Handles multiple code formats (4-8 digits)
- ✅ Prevents duplicate code entry

## Requirements

### macOS Permissions

The SMS reader needs access to Messages.app:

1. **System Settings** → **Privacy & Security** → **Automation**
2. Enable **Terminal** (or iTerm2) to control **Messages**
3. **System Settings** → **Privacy & Security** → **Full Disk Access**
4. Enable **Terminal** (or iTerm2) for full access

### iPhone Setup

- iPhone must be signed into the same Apple ID
- Messages must be synced to Mac (iMessage/SMS forwarding enabled)
- Settings → Messages → Text Message Forwarding → Enable for your Mac

## Usage

The SMS reader is automatically active when using Safari:

```bash
python3 automation/test_manual_login_recording.py safari
```

When a verification code is needed:
1. System detects the code input field
2. Monitors Messages.app for new SMS
3. Extracts the code automatically
4. Enters it into Safari
5. Continues login process

## Code Detection

The reader looks for:
- **6-digit codes** (most common)
- **4-8 digit codes**
- Messages containing keywords: "TikTok", "verification", "code", "verify"

## Example Flow

1. You click "Send Code" in Safari
2. System detects code input field appears
3. SMS arrives on your iPhone
4. Code syncs to Messages.app on Mac
5. Reader extracts code: "123456"
6. Code is automatically entered in Safari
7. Login continues

## Troubleshooting

### Codes Not Detected

- Check Messages.app is syncing SMS from iPhone
- Verify automation permissions are granted
- Check that keywords match (TikTok, verification, etc.)
- Try manually checking Messages.app for the code

### Permission Errors

If you see "not allowed automation" errors:
1. System Settings → Privacy & Security → Automation
2. Enable Terminal/iTerm to control Messages
3. Restart Terminal

### Code Not Entered

- Verify code field is detected (check logs)
- Check that code format matches (4-8 digits)
- Try manual entry if auto-fill fails

## Manual Override

If auto-fill doesn't work, you can:
1. Check Messages.app for the code
2. Enter it manually in Safari
3. The action will still be recorded

## Security

- Codes are logged in recordings (for debugging)
- Codes are not stored permanently
- Only recent messages (last 5-10 minutes) are checked
- Duplicate codes are filtered out

