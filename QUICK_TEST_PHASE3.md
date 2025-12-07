# Quick Test - Phase 3 Clip Generation

## Fastest Way to Test (2 minutes)

```bash
cd backend
python3 test_phase3.py
# Choose option 4
# Enter video path
# Enter start time (e.g., 10) and duration (e.g., 20)
# Skip transcript (press Enter)
```

**Result**: A finished vertical clip in under 1 minute!

## What You'll Get

```
generated_clips/clip_10s_20s_0.80_tiktok.mp4

✅ 9:16 vertical format
✅ Blur background
✅ Optimized for TikTok (5000k bitrate)
✅ Ready to upload!
```

## Test with Full Features

If you have transcript from Phase 1:

```bash
python3 test_phase3.py
# Option 4
# Provide video + transcript
```

**Extra features**:
- ✅ Styled captions
- ✅ GPT-4 viral hook
- ✅ Progress bar
- ✅ Hashtag suggestions
- ✅ CTA text

## What Gets Created

**Basic clip** (no transcript):
- 9:16 vertical video
- Platform-optimized
- ~15-20 MB for 20s clip

**Full clip** (with transcript + GPT):
- Everything above PLUS:
- Burned-in captions
- Hook text overlay (first 3s)
- Progress bar (top)
- Color enhancement
- ~18-25 MB for 20s clip

## Templates

Try different styles:

```bash
# Viral (recommended)
template='viral_basic'  # Captions + hook + progress + effects

# Clean
template='clean'  # Captions only

# Maximum
template='maximum'  # Everything + zoom + vignette

# Minimal
template='minimal'  # Just vertical conversion
```

## Common Issues

**"FFmpeg not found"**
```bash
brew install ffmpeg
```

**"Takes too long"**
- Use `minimal` template
- Skip captions
- Disable GPT hooks

**"File too large"**
- Shorter duration
- Use Instagram platform (lower bitrate)

## Platform Specs

| Platform | Max Size | Best Duration |
|----------|----------|---------------|
| TikTok | 287 MB | 15-60s |
| Instagram | 100 MB | 15-30s |
| YouTube Shorts | 256 MB | 15-60s |

## Example Output

```bash
$ python3 test_phase3.py

🎬 CREATING CLIP: 10.0s - 30.0s
📹 Step 1/6: Extracting clip...
✓ Clip extracted
📐 Step 2/6: Converting to vertical (9:16)...
✓ Converted to vertical
💬 Step 3/6: Adding captions...
✓ Captions burned
🎯 Step 4/6: Generating hook...
   Hook: Watch what happens next 🔥
✓ Hook added
✨ Step 5/6: Adding visual effects...
✓ Effects combined
🚀 Step 6/6: Optimizing for tiktok...
✓ Optimized

✅ CLIP GENERATED!
✓ File: clip_10s_20s_0.80_tiktok.mp4
✓ Size: 15.2 MB
✓ Duration: 20.0s
✓ Hook: Watch what happens next 🔥
✓ Hashtags: #fyp #viral #trending #amazing #wow
```

## Next Steps

After testing:
1. **Upload to TikTok** - Test engagement
2. **Adjust template** - Find what works
3. **Batch generate** - Create multiple clips
4. **Move to Phase 4** - Automate posting!

---

## That's It! 🎉

Phase 3 is ready. Generate your first viral clip:

```bash
cd backend
python3 test_phase3.py
```

Takes under 2 minutes! 🚀
