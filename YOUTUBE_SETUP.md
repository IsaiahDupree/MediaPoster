# 🎥 YouTube Analytics Setup Guide

Get real follower engagement data from YouTube with the official API!

---

## Why YouTube is Better Than TikTok

### ✅ YouTube Data API Provides
- **Real commenter data**: Username, profile URL, avatar
- **Comment text**: Full comment content
- **Comment metadata**: Likes on comments, reply threads
- **Video statistics**: Views, likes, comments count
- **Channel information**: Subscribers, total videos
- **Hashtags/Tags**: Video tags for categorization

### ❌ TikTok Limitations
- No individual liker/commenter data
- Only aggregate counts
- Limited API access

---

## Step 1: Get YouTube API Key

### Create a Google Cloud Project

1. **Go to Google Cloud Console**:
   - Visit: https://console.cloud.google.com/

2. **Create a New Project**:
   - Click "Select a project" → "New Project"
   - Name: "MediaPoster YouTube Analytics"
   - Click "Create"

3. **Enable YouTube Data API v3**:
   - Go to: https://console.cloud.google.com/apis/library
   - Search for "YouTube Data API v3"
   - Click on it → Click "Enable"

4. **Create API Credentials**:
   - Go to: https://console.cloud.google.com/apis/credentials
   - Click "Create Credentials" → "API Key"
   - Copy your API key (looks like: `AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`)

5. **Restrict Your API Key** (Recommended):
   - Click on the API key you just created
   - Under "API restrictions":
     - Select "Restrict key"
     - Check "YouTube Data API v3"
   - Click "Save"

---

## Step 2: Find Your YouTube Channel ID

### Method 1: From YouTube Studio
1. Go to: https://studio.youtube.com/
2. Click on your profile icon → Settings
3. Look at the URL: `https://studio.youtube.com/channel/XXXXXXXXXXXXXXXXX`
4. The `XXXXXXXXXXXXXXXXX` part is your channel ID

### Method 2: From Your Channel Page
1. Go to your YouTube channel
2. Look at the URL
   - If it shows: `youtube.com/channel/UCxxxxx` → That's your channel ID
   - If it shows: `youtube.com/@username` → Use Method 1 or 3

### Method 3: Using the API
```python
# If you know your channel username
import requests

username = "yourchannelname"
api_key = "YOUR_API_KEY"

url = f"https://www.googleapis.com/youtube/v3/channels"
params = {
    "part": "id",
    "forUsername": username,
    "key": api_key
}

response = requests.get(url, params=params)
data = response.json()
channel_id = data["items"][0]["id"]
print(f"Channel ID: {channel_id}")
```

---

## Step 3: Add to Environment Variables

Edit your `.env` file:

```bash
# YouTube Analytics
YOUTUBE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
YOUTUBE_CHANNEL_ID=UCxxxxxxxxxxxxxxxxxxxxxxxxx
```

---

## Step 4: Install Dependencies

```bash
cd Backend
./venv/bin/pip install aiohttp
```

(You've already added this to requirements.txt!)

---

## Step 5: Run YouTube Backfill

```bash
cd Backend
./venv/bin/python backfill_youtube_engagement.py
```

### What It Does:
1. ✅ Fetches your latest 20 YouTube videos
2. ✅ Imports video details (title, description, stats)
3. ✅ Creates content items in database
4. ✅ **Fetches ALL comments with commenter data**
5. ✅ **Tracks real followers who commented**
6. ✅ Analyzes comment sentiment
7. ✅ Calculates engagement scores
8. ✅ Links videos to content tracking system

---

## What You Get

### Real Follower Data! 🎉

Unlike TikTok, YouTube gives you:

```json
{
  "comment_id": "UgwXXXXXXXXXXXXX",
  "text": "Great video! Really helpful.",
  "author_name": "John Doe",
  "author_channel_id": "UCxxxxxxxxxxxxxxxxx",
  "author_profile_image": "https://...",
  "author_channel_url": "https://youtube.com/channel/UCxxxxx",
  "like_count": 5,
  "published_at": "2025-11-20T10:30:00Z",
  "sentiment": "positive"
}
```

### Database Entries:

**Followers Table**:
```sql
- username: "John Doe"
- platform: "youtube"
- platform_user_id: "UCxxxxxxxxxxxxxxxxx"
- profile_url: "https://youtube.com/channel/UCxxxxx"
- avatar_url: "https://..."
```

**Follower Interactions**:
```sql
- interaction_type: "comment"
- interaction_value: "Great video! Really helpful."
- sentiment_score: 0.8
- sentiment_label: "positive"
- occurred_at: "2025-11-20T10:30:00Z"
```

---

## API Quotas

### Free Tier:
- **10,000 units per day**
- Costs:
  - Video details: 1 unit
  - Comments: 1 unit per page (100 comments)
  - Channel info: 1 unit

### Daily Limits:
- ~200 videos with comments (50 comments each)
- Plenty for personal/small business use

### If You Need More:
- Request quota increase in Google Cloud Console
- Or use billing to get more quota

---

## Example Output

```
🎥 Fetching YouTube analytics for channel: UCxxxxxxxxxx

📺 Channel: Your Channel Name
📊 123,456 subscribers
🎬 50 videos

🔍 Fetching latest 20 videos...
✅ Found 20 videos

📹 Processing video 1/20: How to Build a Social Media Dashboard
   Title: How to Build a Social Media Dashboard with React...
   Stats: 1,234 views, 45 likes, 12 comments
   💬 Fetching comments...
   ✅ Got 12 comments

...

✅ YOUTUBE BACKFILL COMPLETE!
================================

📊 Database Summary:
   • Content items: 20
   • YouTube videos: 20
   • Followers tracked: 47 (REAL USERS!)
   • Interactions recorded: 156
   • Comments from users: 145

🏆 Top YouTube Commenters:
   • @JohnDoe: 5 comments 😊
   • @JaneSmith: 4 comments 😊
   • @TechFan2024: 3 comments 😐
```

---

## View in Dashboard

After backfill, go to:
- **`/analytics/content`** - See YouTube videos alongside TikTok
- **`/analytics/followers`** - See REAL YouTube commenters
- **`/analytics/followers/:id`** - View commenter profiles with all their comments

---

## Comparison: TikTok vs YouTube Data

| Feature | TikTok | YouTube |
|---------|--------|---------|
| Individual likers | ❌ No | ❌ No |
| Commenter names | ❌ No | ✅ **Yes!** |
| Commenter profiles | ❌ No | ✅ **Yes!** |
| Comment text | ❌ Limited | ✅ **Yes!** |
| Comment sentiment | ❌ No | ✅ **Yes!** |
| Profile avatars | ❌ No | ✅ **Yes!** |
| Engagement tracking | Aggregate only | **Real followers!** |

---

## Next Steps

1. **Run the backfill** to import your YouTube data
2. **View real follower profiles** in the dashboard
3. **Identify your super fans** who comment most
4. **Analyze sentiment** to see how people feel
5. **Cross-platform insights**: Compare YouTube vs TikTok performance

---

## Troubleshooting

### "API key not found"
- Make sure `YOUTUBE_API_KEY` is set in `.env`
- Restart your terminal/IDE after editing `.env`

### "Channel not found"
- Double-check your channel ID
- Make sure it starts with "UC"
- Try the API method to find it

### "Quota exceeded"
- You've hit the 10,000 units/day limit
- Wait until tomorrow
- Or reduce `max_videos` in the script

### "Comments disabled"
- Some videos have comments disabled
- The script will skip those automatically
- You'll still get video stats

---

## Cost

**100% FREE** for most use cases!
- YouTube Data API is free up to 10,000 units/day
- No credit card required
- Unlimited for personal use within quota

---

🎉 **You now have access to REAL follower data from YouTube!** 

Unlike TikTok, you can track actual users, their comments, sentiment, and build meaningful relationships with your most engaged followers.
