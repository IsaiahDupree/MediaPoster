# 📱 iPhone Video Import Guide

## Quick Start

Import videos from your iPhone directly to MediaPoster for processing.

---

## 🔌 Method 1: Direct USB Import (Recommended)

### Prerequisites
- iPhone connected via USB cable
- iPhone unlocked
- "Trust This Computer" accepted on iPhone

### Steps

```bash
cd backend
./venv/bin/python3 import_from_iphone.py
```

**Choose Import Method:**
1. **Image Capture** - Direct control, choose destination
2. **Photos App** - Organizes in library
3. **Watch Folder** - Manual import with auto-detection

### Import Destination
```
~/Downloads/iPhone_Videos/
```

Videos imported here will be automatically detected by MediaPoster.

---

## 🚀 Method 2: AirDrop (Fastest - 30 seconds)

### Steps
1. Open a video on your iPhone
2. Tap **Share** button
3. Select **AirDrop**
4. Choose your Mac name
5. Video lands in `~/Downloads`
6. MediaPoster detects it automatically!

### No Setup Required
- Works instantly
- No cables needed
- iPhone and Mac must be nearby
- WiFi and Bluetooth must be enabled

---

## 📷 Method 3: iCloud Photos (Automatic Sync)

### Prerequisites
- iCloud Photos enabled on iPhone (Settings → Photos → iCloud Photos)
- iCloud Photos enabled on Mac (System Settings → Apple ID → iCloud → Photos)

### How It Works
- Videos sync automatically to Mac
- Location: `~/Pictures/Photos Library.photoslibrary`
- Takes a few minutes to sync
- Requires internet connection

### Note
Videos in Photos library may need to be exported to be detected by MediaPoster.

---

## 🖥️ Method 4: Image Capture App (Manual)

### Steps
1. Connect iPhone via USB
2. Open **Image Capture** app on Mac
3. Select your iPhone in left sidebar
4. Select videos to import
5. Choose **Import To**: `~/Downloads/iPhone_Videos/`
6. Click **Import** or **Import All**

### Advantages
- Full control over which videos
- See thumbnails before importing
- Can delete from iPhone after import

---

## 📁 MediaPoster Watch Folders

MediaPoster automatically scans these folders for videos:

```
✅ ~/Desktop
✅ ~/Downloads
✅ ~/Downloads/iPhone_Videos
✅ ~/Movies
✅ ~/Pictures
```

### Scan for New Videos

```bash
# Via API
curl http://localhost:8000/api/videos/scan

# View in browser
open http://localhost:8000/docs
```

---

## 🔧 Troubleshooting

### iPhone Not Detected

**Problem**: USB import shows "No iPhone detected"

**Solutions**:
1. ✅ Check USB cable is properly connected
2. ✅ Unlock your iPhone
3. ✅ Tap "Trust This Computer" on iPhone
4. ✅ Try a different USB port
5. ✅ Restart both iPhone and Mac
6. ✅ Check USB cable isn't damaged

**Alternative**: Use AirDrop instead (always works!)

### AirDrop Not Working

**Problem**: Mac doesn't appear in AirDrop

**Solutions**:
1. ✅ Enable WiFi and Bluetooth on both devices
2. ✅ Turn AirDrop "on" in Control Center (iPhone)
3. ✅ Set AirDrop to "Everyone" temporarily
4. ✅ Move iPhone closer to Mac
5. ✅ Restart WiFi on both devices

### Videos Not Showing in MediaPoster

**Problem**: Imported video not appearing

**Solutions**:
1. ✅ Check video is in a watched folder
2. ✅ Refresh scan: `curl http://localhost:8000/api/videos/scan`
3. ✅ Verify file extension (`.mp4`, `.mov`, `.m4v`)
4. ✅ Check file isn't corrupted
5. ✅ Restart MediaPoster server

---

## 🎬 Supported Video Formats

MediaPoster supports:
- ✅ `.mp4` (Most common)
- ✅ `.mov` (iPhone default)
- ✅ `.m4v` (iTunes/Apple)
- ✅ `.avi`
- ✅ `.mkv`

### iPhone Video Info
- **Format**: MOV or MP4
- **Codec**: H.264 or HEVC (H.265)
- **Size**: Varies (typically 50-500 MB per minute)

---

## 📊 After Import

Once videos are imported:

1. **Server Detects** - Videos appear in `/api/videos`
2. **Process** - Extract highlights, generate clips
3. **Publish** - Post to social media platforms

### Next Steps

```bash
# View imported videos
curl http://localhost:8000/api/videos

# Start processing
curl -X POST http://localhost:8000/api/videos/{video_id}/analyze

# Generate clips
curl -X POST http://localhost:8000/api/videos/{video_id}/clips
```

---

## 💡 Pro Tips

### Batch Import
- Import multiple videos at once
- Image Capture can select multiple files
- AirDrop supports multiple selections

### Storage Management
- Videos are large - monitor disk space
- Delete originals after processing if needed
- Use external drive for archives

### Quality Settings
- iPhone 4K videos are huge (400MB/min)
- 1080p is usually sufficient (150MB/min)
- Settings → Camera → Record Video

### Fastest Workflow
1. Record video on iPhone
2. AirDrop to Mac immediately
3. MediaPoster processes automatically
4. Delete from iPhone to save space

---

## 🚀 Quick Reference

| Method | Speed | Setup | Best For |
|--------|-------|-------|----------|
| **AirDrop** | ⚡ 30s | None | Quick single videos |
| **USB + Image Capture** | 🔥 1-2min | USB cable | Multiple videos |
| **iCloud Photos** | ⏱️ Auto | iCloud account | Automatic backup |
| **Photos App** | 🔥 2min | USB cable | Organization |

---

## 🆘 Need Help?

### Check Connection Status
```bash
cd backend
./venv/bin/python3 check_devices.py
```

### View Server Logs
```bash
cd backend
tail -f logs/app.log
```

### Restart Server
```bash
# Stop server (Ctrl+C)
# Start server
./venv/bin/python3 quickstart.py
```

---

## 📝 Summary

**Easiest**: Use **AirDrop** for 1-2 videos  
**Best for bulk**: **USB + Image Capture**  
**Most automatic**: **iCloud Photos**

All methods work great - choose what fits your workflow!

---

**🎉 Happy Importing!**

Videos imported → MediaPoster processes → Clips published → Viral content! 🚀
