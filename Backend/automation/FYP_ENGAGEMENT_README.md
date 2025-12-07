# FYP Engagement Script

Automated script to like and comment on multiple videos from TikTok's For You Page (FYP).

## Quick Start

### Basic Usage

```bash
cd Backend/automation
python3 run_fyp_engagement.py
```

This will:
- Navigate to TikTok FYP
- Like and comment on 3 videos in a row
- Use Safari extension if available (falls back to pyautogui)

### Custom Options

```bash
# Engage with 5 videos
python3 run_fyp_engagement.py -n 5

# Custom comment template
python3 run_fyp_engagement.py -c "Amazing! 🎉"

# Don't use Safari extension (use pyautogui instead)
python3 run_fyp_engagement.py --no-extension

# Combine options
python3 run_fyp_engagement.py -n 3 -c "Love this! ❤️"
```

### Using the Test Script

```bash
./test_fyp_engagement.sh
```

## How It Works

1. **Initialization**: Opens Safari and navigates to TikTok FYP
2. **For each video**:
   - Gets video information (username, caption)
   - Likes the video
   - Opens comments panel
   - Types and posts a comment (using Safari extension or pyautogui)
   - Verifies comment was posted
   - Moves to next video
3. **Summary**: Displays results for all videos

## Requirements

- macOS with Safari
- Logged into TikTok in Safari
- Safari extension installed (optional but recommended for reliable typing)

## Features

✅ **Automatic Navigation**: Navigates to FYP automatically  
✅ **Video Detection**: Finds and engages with visible videos  
✅ **Like & Comment**: Performs both actions on each video  
✅ **Extension Support**: Uses Safari extension for Draft.js typing  
✅ **Fallback**: Falls back to pyautogui if extension not available  
✅ **Verification**: Verifies comments were posted  
✅ **Rate Limiting**: Built-in rate limiting to avoid detection  
✅ **Error Handling**: Graceful error handling and reporting  

## Output

The script provides detailed logging:

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
   📍 Now on: https://www.tiktok.com/@user2/video/7890123456

...

📊 ENGAGEMENT SUMMARY
============================================================
✅ Successfully engaged: 3/3
❤️  Videos liked: 3/3
💬 Comments posted: 3/3

📋 Detailed Results:
   Video 1: ✅
      Liked: True
      Commented: True
      Comment: Great content! 🔥 123456
   ...
```

## Troubleshooting

### "Not logged in" warning

Make sure you're logged into TikTok in Safari before running the script.

### Comments not posting

1. **Check Safari extension**: Make sure extension is installed and enabled
2. **Try without extension**: Use `--no-extension` flag to use pyautogui
3. **Check focus**: Make sure Safari window is active and visible

### Can't find videos

1. Make sure you're on the FYP (For You Page)
2. Wait a few seconds for videos to load
3. Check that TikTok is accessible

### Rate limiting

The script has built-in rate limiting. If you see rate limit warnings:
- Wait a few minutes before running again
- Reduce the number of videos (`-n 2` instead of `-n 3`)

## Integration

You can also use this as a Python module:

```python
from automation.run_fyp_engagement import engage_with_fyp_videos
import asyncio

results = asyncio.run(engage_with_fyp_videos(
    num_videos=3,
    comment_template="Nice! 🔥",
    use_extension=True
))

for result in results:
    print(f"Video {result['video_number']}: {result['success']}")
```

## Next Steps

- Add more engagement actions (follow, share, save)
- Customize comment templates per video type
- Add video filtering (skip certain types)
- Integrate with analytics tracking

