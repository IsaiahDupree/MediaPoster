# 📱 # iPhone USB Connection Troubleshooting

## 🚨 Important: macOS vs Linux
**`ifuse` is for Linux only.** It does NOT work on macOS.
On macOS, you cannot mount the iPhone filesystem directly as a drive using open-source tools due to Apple's security restrictions.

## ✅ The Solution for macOS
To programmatically import videos on macOS, use **Image Capture Automation**.
We have built a tool that automates this for you:

```bash
cd Backend
./venv/bin/python3 import_via_imagecapture.py
```

This script:
1. Detects your iPhone
2. Opens the native Image Capture app
3. Watches for new files in `~/Downloads/iPhone_Videos`
4. Auto-imports them into MediaPoster

## 🔍 Diagnostic Steps
If the script above doesn't detect your iPhone:

### 1. Check USB Connection
Run our diagnostic tool:
```bash
cd Backend
./venv/bin/python3 test_iphone_connection.py
```

### 2. Trust the Computer
1. Connect iPhone via USB
2. Unlock iPhone
3. Tap **"Trust"** on the "Trust This Computer?" popup
4. Enter your iPhone passcode

### 3. Reset Privacy Settings (Last Resort)
If "Trust" never appears:
1. Go to iPhone Settings → General → Transfer or Reset iPhone
2. Tap Reset → **Reset Location & Privacy**
3. Reconnect USB and Trust again

## 📱 Alternative Methods
If USB automation is problematic, use these native features:

### Option A: AirDrop (Fastest)
1. Select video on iPhone
2. Share → AirDrop → Your Mac
3. MediaPoster automatically detects it in `~/Downloads`

### Option B: iCloud Photos
1. Enable iCloud Photos on both devices
2. MediaPoster automatically watches `~/Pictures/Photos Library.photoslibrary`

## 🛠 Technical Details
| Tool | macOS Status | Function |
|------|--------------|----------|
| `idevice_id` | ✅ Works | Detects UDID |
| `ideviceinfo` | ✅ Works | Gets Device Name/iOS Version |
| `ifuse` | ❌ **Fails** | Linux only (Mounts filesystem) |
| `Image Capture` | ✅ **Best** | Native macOS import tool |
stablish a programmatic connection to your iPhone via USB for automated video import.

---

## 🔧 Required Tools

### 1. libimobiledevice (Essential)

Open-source library for communicating with iOS devices.

**Install via Homebrew:**
```bash
brew install libimobiledevice
brew install ifuse  # Optional: mount iPhone filesystem
brew install ideviceinstaller  # Optional: manage apps
```

**What it provides:**
- `idevice_id` - List connected devices
- `ideviceinfo` - Get device information
- `idevicepair` - Manage device pairing
- `idevicebackup2` - Access backups
- `ifuse` - Mount device filesystem

### 2. usbmuxd (Usually auto-installed)

Daemon that multiplexes connections to iOS devices over USB.

**Check if running:**
```bash
ps aux | grep usbmuxd
```

**Install if needed:**
```bash
brew install usbmuxd
```

---

## 🔍 Step-by-Step Troubleshooting

### Step 1: Physical Connection

**Check:**
- ✅ USB cable is Apple-certified or MFi certified
- ✅ Cable is not damaged
- ✅ Try different USB ports on Mac
- ✅ iPhone shows "Charging" on lock screen

**Test:**
```bash
# Check if iPhone appears in USB tree
system_profiler SPUSBDataType | grep -A 10 iPhone
```

**Expected:** Should see iPhone with Product ID

**If not visible:**
- Try a different cable
- Try a different USB port
- Restart iPhone
- Restart Mac

---

### Step 2: Trust Relationship

**On iPhone:**
1. Unlock iPhone
2. Look for "Trust This Computer?" popup
3. Tap **"Trust"**
4. Enter iPhone passcode if prompted

**Verify trust status:**
```bash
idevicepair validate
```

**Expected output:**
```
SUCCESS: Validated pairing with device [UDID]
```

**If "No device found":**
```bash
# Re-pair the device
idevicepair pair
```

**If "Trust required":**
- iPhone needs to be unlocked
- Tap "Trust" on iPhone popup
- Run `idevicepair pair` again

---

### Step 3: Check Device Detection

**List connected devices:**
```bash
idevice_id -l
```

**Expected:** Shows device UDID (40-character hex string)

**Get device info:**
```bash
ideviceinfo
```

**Expected:** Shows device name, iOS version, model, etc.

**If no device found:**
```bash
# Check usbmuxd status
sudo launchctl list | grep usbmuxd

# Restart usbmuxd
sudo launchctl stop com.apple.usbmuxd
sudo launchctl start com.apple.usbmuxd

# Try again
idevice_id -l
```

---

### Step 4: Access Photos/Videos

**Method A: Mount Filesystem (ifuse)**

```bash
# Create mount point
mkdir -p ~/iPhone_Mount

# Mount iPhone
ifuse ~/iPhone_Mount

# List DCIM folder (where photos/videos are)
ls -la ~/iPhone_Mount/DCIM/

# Access videos
find ~/iPhone_Mount/DCIM -name "*.MOV" -o -name "*.MP4"

# Unmount when done
umount ~/iPhone_Mount
```

**Method B: Use Python libimobiledevice bindings**

```python
import subprocess
import json

def get_device_info():
    result = subprocess.run(
        ['ideviceinfo', '-u', get_device_udid()],
        capture_output=True,
        text=True
    )
    return result.stdout

def get_device_udid():
    result = subprocess.run(
        ['idevice_id', '-l'],
        capture_output=True,
        text=True
    )
    return result.stdout.strip()
```

**Method C: Image Capture Scripting**

```bash
# Use ImageCaptureCore framework via osascript
osascript -e 'tell application "Image Capture"
    activate
end tell'
```

---

### Step 5: Permissions on macOS

**Grant permissions:**

1. **System Settings** → **Privacy & Security**
2. **Files and Folders** → Allow terminal apps
3. **Full Disk Access** → Add Terminal/iTerm

**Check Python permissions:**
```bash
# Your Python script needs access to:
# - Files and Folders
# - Removable Volumes
```

---

## 🐛 Common Issues & Solutions

### Issue 1: "No device found" even when plugged in

**Symptoms:**
- iPhone appears in Finder
- `idevice_id -l` returns nothing

**Solutions:**

**A. Restart usbmuxd:**
```bash
sudo launchctl stop com.apple.usbmuxd
sudo launchctl start com.apple.usbmuxd
```

**B. Reset iPhone location services:**
1. iPhone Settings → Privacy → Location Services
2. Scroll to bottom → System Services
3. Find "Important Locations"
4. Toggle off and on

**C. Reset network settings on iPhone:**
1. Settings → General → Transfer or Reset iPhone
2. Reset → Reset Network Settings
3. Reconnect via USB

**D. Check for lockdown file:**
```bash
# Remove old lockdown files
rm -rf ~/Library/Lockdown/*

# Re-pair
idevicepair pair
```

---

### Issue 2: "Trust required" but no popup on iPhone

**Solutions:**

**A. Reset Location & Privacy:**
1. iPhone Settings → General → Transfer or Reset iPhone
2. Reset → Reset Location & Privacy
3. Reconnect and trust

**B. Force prompt:**
```bash
# Unpair first
idevicepair unpair

# Wait 5 seconds
sleep 5

# Pair again (this should trigger popup)
idevicepair pair
```

**C. Check iPhone is unlocked:**
- Face ID must be activated
- Or passcode entered
- Screen must be on

---

### Issue 3: Can detect device but can't access files

**Solutions:**

**A. Mount with ifuse:**
```bash
# Install if not already
brew install ifuse

# Mount
ifuse ~/iPhone_Mount

# Check if mounted
mount | grep iPhone
```

**B. Permissions:**
```bash
# Check directory permissions
ls -la ~/iPhone_Mount/DCIM/

# If permission denied, unmount and remount
umount ~/iPhone_Mount
ifuse ~/iPhone_Mount -o allow_other
```

**C. Use AFC (Apple File Conduit):**
```bash
# Check if AFC service is running
ideviceinfo | grep AFCService
```

---

### Issue 4: ifuse mounts but DCIM folder is empty

**Causes:**
- iPhone is locked
- Photos app permission needed
- Device not in correct mode

**Solutions:**

**A. Unlock iPhone completely:**
- Face ID or passcode entered
- Screen must stay on
- Don't let it auto-lock

**B. Force refresh:**
```bash
# Unmount
umount ~/iPhone_Mount

# Unlock iPhone completely
# Then mount again
ifuse ~/iPhone_Mount

# Navigate to DCIM
cd ~/iPhone_Mount/DCIM
ls -la
```

**C. Check iOS version:**
```bash
ideviceinfo | grep ProductVersion
```

iOS 13+ has stricter photo access. May need to use Photos.app integration instead.

---

### Issue 5: Connection works but is unstable

**Solutions:**

**A. Check cable quality:**
- Use official Apple Lightning cable
- Or certified MFi cable
- Cheap cables cause connection drops

**B. Disable USB power saving:**
```bash
# Check USB power management
pmset -g

# Prevent USB sleep
sudo pmset -a usb 0
```

**C. Keep iPhone unlocked:**
- Turn off auto-lock temporarily
- Settings → Display & Brightness → Auto-Lock → Never

---

## 🔬 Diagnostic Commands

### Complete Device Check:

```bash
# 1. Check USB connection
system_profiler SPUSBDataType | grep -A 10 iPhone

# 2. List devices via libimobiledevice
idevice_id -l

# 3. Check pairing
idevicepair validate

# 4. Get device info
ideviceinfo | head -20

# 5. Try to mount
ifuse ~/iPhone_Mount && echo "Mount successful" || echo "Mount failed"

# 6. Check DCIM
ls -la ~/iPhone_Mount/DCIM/ 2>&1

# 7. Count media files
find ~/iPhone_Mount/DCIM -type f \( -name "*.MOV" -o -name "*.MP4" -o -name "*.JPG" \) 2>/dev/null | wc -l

# 8. Unmount
umount ~/iPhone_Mount
```

---

## 🛠️ Programmatic Access Methods

### Method 1: Direct File Access (ifuse)

**Pros:**
- Direct filesystem access
- Fast
- Works offline

**Cons:**
- Requires trust relationship
- iPhone must be unlocked
- May fail on newer iOS versions

**Use when:**
- Full control needed
- Bulk operations
- Offline access

### Method 2: Image Capture Framework (macOS)

**Pros:**
- Official Apple API
- Reliable
- Handles permissions properly

**Cons:**
- macOS only
- More complex
- Requires Objective-C/Swift

**Use when:**
- Production app
- Need reliability
- macOS target only

### Method 3: Photos.app Integration

**Pros:**
- Most reliable
- Handles iOS restrictions
- Better user experience

**Cons:**
- Not truly programmatic
- User must interact
- Photos organized in library

**Use when:**
- User-friendly approach preferred
- Don't need raw file access
- Can accept some manual steps

### Method 4: Network Transfer (WiFi Sync)

**Pros:**
- No cable needed
- Can be fully automated
- Works with iPhone locked

**Cons:**
- Slower than USB
- Requires same network
- Setup complexity

**Use when:**
- USB unreliable
- Multiple devices
- Remote access needed

---

## 📱 iOS Version Considerations

### iOS 12 and older:
- ✅ ifuse works well
- ✅ Direct DCIM access
- ✅ Fewer restrictions

### iOS 13-14:
- ⚠️ Photo library restrictions
- ⚠️ May need Photos.app
- ✅ ifuse still works with trust

### iOS 15+:
- ⚠️ Stricter privacy
- ⚠️ Limited DCIM access
- ⚠️ May need user approval per file

### iOS 17+ (Latest):
- ⚠️ Very strict privacy
- ⚠️ Individual file permissions
- ✅ Better continuity camera
- 💡 Recommendation: Use AirDrop or iCloud

---

## 🚀 Recommended Approach

### For Production (Most Reliable):

**Hybrid Approach:**

1. **Primary: AirDrop/iCloud**
   - Fastest and most reliable
   - No trust issues
   - Works with latest iOS

2. **Secondary: USB with ifuse**
   - For bulk operations
   - When WiFi unavailable
   - For automated workflows

3. **Fallback: Manual Import**
   - Image Capture.app
   - Photos.app
   - Drag and drop

### Implementation Priority:

1. ✅ **AirDrop watcher** (easiest, most reliable)
2. ✅ **USB detection + Image Capture automation**
3. ✅ **ifuse mounting** (power users)
4. ✅ **iCloud Photos sync** (automatic)

---

## 🔧 Quick Setup Script

Save this as `setup_iphone_usb.sh`:

```bash
#!/bin/bash
echo "Setting up iPhone USB access..."

# Install dependencies
echo "1. Installing libimobiledevice..."
brew install libimobiledevice ifuse

# Check device
echo "2. Checking for iPhone..."
if idevice_id -l &> /dev/null; then
    echo "✓ iPhone detected!"
    ideviceinfo | grep -E "DeviceName|ProductVersion"
else
    echo "✗ No iPhone detected"
    echo "Please connect iPhone and trust this computer"
    exit 1
fi

# Verify pairing
echo "3. Verifying trust..."
if idevicepair validate &> /dev/null; then
    echo "✓ Device is trusted"
else
    echo "⚠️ Device not trusted. Pairing..."
    idevicepair pair
fi

# Test mount
echo "4. Testing filesystem mount..."
mkdir -p ~/iPhone_Mount
if ifuse ~/iPhone_Mount 2>/dev/null; then
    echo "✓ Mount successful"
    ls -la ~/iPhone_Mount/DCIM/ | head -5
    umount ~/iPhone_Mount
else
    echo "✗ Mount failed"
    echo "iPhone may need to be unlocked"
fi

echo ""
echo "✓ Setup complete!"
echo "Use: ifuse ~/iPhone_Mount to access files"
```

---

## 📞 Get Help

If still having issues:

1. **Check iOS version:** Newer iOS = more restrictions
2. **Try different cable:** Cable quality matters
3. **Restart everything:** iPhone, Mac, usbmuxd
4. **Check Console.app:** See system logs for errors
5. **Use Activity Monitor:** Check if usbmuxd is running

**Alternative solutions:**
- Use AirDrop (fastest, no setup)
- Use iCloud Photos (automatic sync)
- Use Continuity Camera (for recording)

---

## ✅ Success Checklist

- [ ] libimobiledevice installed
- [ ] iPhone appears in USB tree
- [ ] Trust relationship established
- [ ] `idevice_id -l` shows UDID
- [ ] `ideviceinfo` returns data
- [ ] ifuse mounts successfully
- [ ] DCIM folder accessible
- [ ] Can copy files programmatically

**Once all checked:** You have full programmatic access! 🎉

---

**Last Updated:** 2025-11-19  
**Tested On:** macOS Sequoia 15.0+, iOS 17+
