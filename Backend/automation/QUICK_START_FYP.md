# Quick Start: FYP Engagement Script

## 🚀 Run the Script

```bash
cd Backend/automation
python3 run_fyp_engagement.py
```

This will automatically:
1. ✅ Open Safari and navigate to TikTok FYP
2. ✅ Like and comment on 3 videos in a row
3. ✅ Show detailed results

## 📋 Prerequisites

1. **Install dependencies** (if not already installed):
   ```bash
   cd Backend
   pip3 install loguru
   ```

2. **Make sure you're logged into TikTok** in Safari

3. **Optional**: Install Safari extension for better comment typing
   - See `safari_extension/SAFARI_EXTENSION_SETUP.md`

## 🎯 Usage Examples

### Basic (3 videos)
```bash
python3 run_fyp_engagement.py
```

### Custom number of videos
```bash
python3 run_fyp_engagement.py -n 5
```

### Custom comment
```bash
python3 run_fyp_engagement.py -c "Amazing content! 🎉"
```

### Without Safari extension
```bash
python3 run_fyp_engagement.py --no-extension
```

## 📊 What You'll See

```
🚀 Starting FYP engagement automation
   Videos: 3
   Comment template: Great content! 🔥

📍 Step 1: Navigating to For You Page...
   Current URL: https://www.tiktok.com/foryou

============================================================
📹 VIDEO 1/3
============================================================
   Video: @username
   Caption: Check out this amazing video...

   ❤️  Liking video...
   ✅ Video liked successfully

   💬 Posting comment...
   ✅ Comment posted: Great content! 🔥 123456
   ✅ Comment verified in comments list

   ⏭️  Moving to next video...

...

📊 ENGAGEMENT SUMMARY
============================================================
✅ Successfully engaged: 3/3
❤️  Videos liked: 3/3
💬 Comments posted: 3/3
```

## ⚠️ Troubleshooting

### "ModuleNotFoundError: No module named 'loguru'"
```bash
pip3 install loguru
```

### "Not logged in" warning
- Open Safari manually
- Log into TikTok
- Run the script again

### Comments not posting
- Make sure Safari extension is installed (optional)
- Or use `--no-extension` flag to use pyautogui

## 📝 Next Steps

- See `FYP_ENGAGEMENT_README.md` for full documentation
- See `TIKTOK_PYAUTOGUI_AUTOMATION.md` for technical details
- See `safari_extension/SAFARI_EXTENSION_SETUP.md` for extension setup

