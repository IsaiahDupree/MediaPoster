# Safari Cookie Access - macOS Permissions

## Why Permissions Are Needed

Safari on macOS stores cookies in a sandboxed container for security. To extract cookies for automation, you need to grant your terminal app access.

## How to Grant Permissions

### Method 1: Full Disk Access (Recommended)

1. **Open System Settings** (or System Preferences on older macOS)
2. Go to **Privacy & Security**
3. Click **Full Disk Access**
4. Click the **+** button to add an app
5. Navigate to and select:
   - **Terminal** (if using Terminal.app)
   - **iTerm2** (if using iTerm2)
   - **Cursor** (if running from Cursor's terminal)
6. Make sure the checkbox is **enabled** (checked)
7. **Restart your terminal** for changes to take effect

### Method 2: Using Terminal Command

You can also try granting permissions via command line:

```bash
# For Terminal
sudo sqlite3 /Library/Application\ Support/com.apple.TCC/TCC.db "INSERT INTO access VALUES('kTCCServiceSystemPolicyAllFiles','com.apple.Terminal',0,2,2,1,NULL,NULL,0,'UNUSED',NULL,0,1541440109);"

# Note: This requires admin password and may not work on newer macOS versions
```

### Method 3: Manual Login (No Permissions Needed)

If you don't want to grant permissions, you can:
1. Run the recorder without cookie import
2. Manually log in (cookies will be saved after login)
3. Use the saved session for future runs

## Verify Permissions

After granting permissions, test cookie extraction:

```bash
cd Backend
source venv/bin/activate
python3 -c "import browser_cookie3; cookies = list(browser_cookie3.safari(domain_name='tiktok.com')); print(f'Found {len(cookies)} TikTok cookies')"
```

If it works, you should see a number of cookies found.

## Troubleshooting

### "Operation not permitted" Error

- Make sure you added the **correct terminal app** (Terminal, iTerm2, etc.)
- **Restart the terminal** after granting permissions
- Try closing and reopening the terminal app completely
- On newer macOS, you may need to grant permissions to the Python process itself

### Still Not Working?

1. Check System Settings > Privacy & Security > Full Disk Access
2. Make sure your terminal app is listed and **enabled**
3. Try restarting your computer
4. Use Chrome instead (doesn't require these permissions)

### Alternative: Use Chrome

Chrome doesn't require special permissions:

```bash
python3 automation/test_manual_login_recording.py chrome
```

## Security Note

Granting Full Disk Access gives your terminal app access to all files on your system. This is necessary for Safari cookie extraction but should be done carefully. Only grant this to trusted terminal applications.

## What Gets Imported

When permissions are granted, the system imports:
- ✅ TikTok cookies (session, authentication)
- ✅ Google cookies (if using Google login)
- ✅ Other relevant domain cookies

This allows the automation to use your existing logged-in sessions.

