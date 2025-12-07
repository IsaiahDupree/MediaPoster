# 📸 Instagram Analytics Integration - Swappable Design

**Date**: November 23, 2025, 1:30 PM

---

## 🎯 Overview

Swappable Instagram analytics service that matches our content tracking schema. Easily switch between different Instagram API providers without changing your application code.

---

## ✨ Key Features

### Swappable Architecture
- **Interface-based design**: Easy to swap Instagram API providers
- **Consistent schema**: All data normalized to match our database
- **Drop-in replacement**: Change providers by swapping one file
- **Future-proof**: Add new providers without breaking changes

### What It Tracks
- ✅ Profile information (followers, posts, bio)
- ✅ Post statistics (likes, comments, plays)
- ✅ Media thumbnails and URLs
- ✅ Captions and hashtags
- ✅ Post timestamps
- ✅ Media types (photo, video, carousel)

---

## 🏗️ Architecture

### Swappable Service Pattern

```python
# services/instagram_analytics.py
class InstagramAnalytics:
    """
    Swappable Instagram API client
    """
    async def _make_request(self, endpoint, params):
        # Generic request method - swap this out!
        pass
    
    async def get_user_profile(self, username):
        # Standardized output regardless of provider
        return {
            "user_id": ...,
            "username": ...,
            "follower_count": ...,
            ...
        }
```

### Multiple Providers Supported

#### Current: Instagram Looter2 (RapidAPI)
- **Cost**: $9.90/month for 15K requests
- **Rate Limit**: 10 req/sec
- **Auth**: RapidAPI Key
- **Pros**: Reliable, good docs, affordable
- **Cons**: Rate limits on free tier

#### Easy to Add:
- Instagram Graph API (official, requires business account)
- Instaloader (unofficial, no API key needed)
- Instagram-scraper (open source)
- Custom scraper with Playwright

---

## 🔌 API Provider Details

### Instagram Looter2 API

**Endpoints Used**:
```
GET /id                 # Convert username → user_id
GET /profile            # Get profile info
GET /user-feeds2        # Get user's posts (improved)
GET /post               # Get individual post details
```

**Headers Required**:
```python
{
    "X-RapidAPI-Key": "your-key-here",
    "X-RapidAPI-Host": "instagram-looter2.p.rapidapi.com"
}
```

**Rate Limits**:
- Basic (Free): 150 requests/month
- Pro: 15K requests/month ($9.90)
- Ultra: 75K requests/month ($27.90)
- Mega: 250K requests/month ($75.90)

---

## 📋 Setup Instructions

### Step 1: Get RapidAPI Key

1. **Sign up**: https://rapidapi.com/
2. **Subscribe to Instagram Looter2**: https://rapidapi.com/irrors-apis/api/instagram-looter2
3. **Copy your API key** from the dashboard
4. **Choose a plan** (Basic free plan has 150 requests/month)

### Step 2: Add to Environment

Edit `/Backend/.env`:
```bash
# Instagram Analytics (RapidAPI)
RAPIDAPI_KEY=your-rapidapi-key-here
INSTAGRAM_USERNAME=your_instagram_username
```

### Step 3: Test the Service

```bash
cd Backend
./venv/bin/python -c "
import asyncio
from services.instagram_analytics import fetch_instagram_analytics

data = asyncio.run(fetch_instagram_analytics('instagram', max_posts=5))
print(f'Found {len(data[\"posts\"])} posts')
"
```

### Step 4: Run Backfill

```bash
./venv/bin/python backfill_instagram_engagement.py
```

---

## 🔄 Swapping API Providers

### Option 1: Instagram Graph API (Official)

```python
# services/instagram_analytics_graph.py
class InstagramGraphAPI(InstagramAnalytics):
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://graph.instagram.com"
    
    async def _make_request(self, endpoint, params):
        params['access_token'] = self.access_token
        # ... rest of implementation
```

**Pros**:
- Official API
- Best rate limits
- Most reliable

**Cons**:
- Requires Business/Creator account
- Complex OAuth flow
- Limited to own account only

### Option 2: Instaloader (Unofficial)

```python
# services/instagram_analytics_instaloader.py
import instaloader

class InstagramInstaloader(InstagramAnalytics):
    def __init__(self):
        self.L = instaloader.Instaloader()
    
    async def get_user_profile(self, username):
        profile = instaloader.Profile.from_username(
            self.L.context, username
        )
        return {
            "user_id": profile.userid,
            "username": profile.username,
            "follower_count": profile.followers,
            ...
        }
```

**Pros**:
- No API key needed
- Works with any public account
- Free and open source

**Cons**:
- Can be blocked by Instagram
- Slower than API
- Requires Instagram login for private accounts

### Option 3: Custom Playwright Scraper

```python
# services/instagram_analytics_scraper.py
from playwright.async_api import async_playwright

class InstagramScraper(InstagramAnalytics):
    async def get_user_profile(self, username):
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto(f"https://instagram.com/{username}")
            # ... scrape the page
```

**Pros**:
- No API limits
- Most flexible
- Can get any public data

**Cons**:
- Slowest option
- Can break with Instagram changes
- Against Instagram TOS

---

## 📊 Data Schema Mapping

### Profile Data

```python
# API Response → Our Schema
{
    "user_id": str,          # → followers.platform_user_id
    "username": str,         # → followers.username
    "full_name": str,        # → followers.display_name
    "biography": str,        # → (metadata)
    "profile_pic_url": str,  # → followers.avatar_url
    "follower_count": int,   # → (metadata)
    "following_count": int,  # → (metadata)
    "media_count": int       # → (metadata)
}
```

### Post Data

```python
# API Response → Our Schema
{
    "media_id": str,         # → content_posts.external_post_id
    "shortcode": str,        # → Used in URLs
    "caption": str,          # → content_items.title & description
    "like_count": int,       # → follower_interactions (aggregate)
    "comment_count": int,    # → (counted in interactions)
    "taken_at": int,         # → content_posts.posted_at
    "thumbnail_url": str,    # → content_items.thumbnail_url
    "url": str               # → content_posts.permalink_url
}
```

---

## 💾 Database Integration

### Tables Populated

**content_items**:
```sql
- title: Extracted from caption
- description: Full caption with hashtags
- slug: Generated from title + shortcode
- thumbnail_url: Post thumbnail image
```

**content_posts**:
```sql
- platform: 'instagram'
- external_post_id: Instagram shortcode
- permalink_url: Instagram post URL
- posted_at: Post timestamp
```

**content_tags**:
```sql
- tag: Hashtags from caption
- platform: 'instagram'
```

**follower_interactions**:
```sql
- interaction_type: 'like'
- metadata: {count: likes, is_aggregate: true}
```

---

## 🎨 Features by Platform

| Feature | Instagram | YouTube | TikTok |
|---------|-----------|---------|--------|
| **Profile Info** | ✅ | ✅ | ✅ |
| **Post Stats** | ✅ | ✅ | ✅ |
| **Thumbnails** | ✅ | ✅ | ✅ |
| **Captions** | ✅ | ✅ | ✅ |
| **Hashtags** | ✅ | ✅ | ✅ |
| **Real Commenters** | ❌ | ✅ | ❌ |
| **Comment Text** | ❌ | ✅ | ❌ |
| **Sentiment Analysis** | ❌ | ✅ | ❌ |
| **Video URLs** | ✅ | ✅ | ❌ |

---

## 📈 Usage Examples

### Fetch Analytics

```python
from services.instagram_analytics import fetch_instagram_analytics

data = await fetch_instagram_analytics('your_username', max_posts=20)

print(f"Followers: {data['profile']['follower_count']:,}")
print(f"Posts: {len(data['posts'])}")
print(f"Total likes: {sum(p['like_count'] for p in data['posts']):,}")
```

### Import to Database

```bash
# Import your Instagram data
./venv/bin/python backfill_instagram_engagement.py

# View in dashboard
open http://localhost:5557/analytics/content
```

### Switch API Provider

```python
# Option 1: Use Instagram Graph API
from services.instagram_analytics_graph import InstagramGraphAPI
ig = InstagramGraphAPI(access_token="YOUR_TOKEN")

# Option 2: Use Instaloader
from services.instagram_analytics_instaloader import InstagramInstaloader
ig = InstagramInstaloader()

# Both have the same interface!
data = await ig.get_account_analytics('username', max_posts=20)
```

---

## 🔐 API Costs & Limits

### Instagram Looter2 (Current)

**Free Tier**:
- 150 requests/month
- ~7 profiles or ~30 posts
- Good for testing

**Pro Tier** ($9.90/month):
- 15,000 requests/month
- ~750 profiles or ~3,000 posts
- Perfect for small businesses

**Usage Calculation**:
```
Backfill 1 account with 20 posts:
- 1 request: Get profile info
- 1 request: Get posts list
- Total: 2 requests per backfill

Monthly: $9.90 = 7,500 backfills = 150K posts
```

### Instagram Graph API (Alternative)

**Official API**:
- FREE (no cost)
- 200 requests/hour per user
- 4,800 requests/day
- Must have Business/Creator account

**Usage**: Perfect for managing your own account

---

## 🚀 Example Output

```
📸 Fetching Instagram analytics for: @your_username

👤 Profile: @your_username
📊 2,500 followers, 85 posts

🔍 Fetching latest 20 posts...
✅ Found 20 posts

📷 Processing post 1/20: CXaBcDefGhi
   Stats: 150 likes, 12 comments
  ✅ Got thumbnail
  ✅ Content item: uuid
  ✅ Linked to Instagram
  📊 150 likes, 12 comments, 0 plays
  ✅ Post processed

...

✅ INSTAGRAM BACKFILL COMPLETE!
================================

📊 Database Summary:
   • Content items: 60
   • Instagram posts: 20
   • Followers tracked: 1
   • Interactions recorded: 20

👤 Profile Stats:
   • @your_username
   • 2,500 followers
   • 85 total posts
   • ✅ Verified

🏆 Top Instagram Posts:
   • Summer vibes at the beach: 450 likes
   • New product launch: 380 likes
   • Behind the scenes: 320 likes
```

---

## 🔧 Troubleshooting

### "API key not found"
```bash
# Make sure RAPIDAPI_KEY is in your .env file
echo "RAPIDAPI_KEY=your-key-here" >> Backend/.env
```

### "Rate limit exceeded"
```python
# Add delays between requests
await asyncio.sleep(2)  # Wait 2 seconds

# Or reduce batch size
data = await fetch_instagram_analytics('user', max_posts=10)
```

### "User not found"
- Check username spelling
- Make sure account is public
- Try with a well-known public account first

### "Thumbnail not loading"
- Instagram URLs expire after ~1 hour
- Re-run backfill to get fresh URLs
- Or download and host thumbnails locally

---

## 📝 Next Steps

### Phase 1: Basic Integration ✅
- ✅ Create swappable service
- ✅ Build backfill script
- ✅ Import to database
- ✅ Display in dashboard

### Phase 2: Enhanced Features
- [ ] Add Instagram Graph API provider
- [ ] Download and host thumbnails locally
- [ ] Track Stories and Reels separately
- [ ] Add engagement rate calculations
- [ ] Track hashtag performance

### Phase 3: Advanced Analytics
- [ ] Compare cross-platform performance
- [ ] Identify best posting times
- [ ] Track follower growth over time
- [ ] A/B test caption styles
- [ ] Generate content recommendations

---

## 🎉 Summary

### What We Built
- ✅ **Swappable Instagram service** - Easy to change providers
- ✅ **Backfill script** - Import historical data
- ✅ **Schema mapping** - Normalized to our database
- ✅ **Thumbnail support** - Visual previews
- ✅ **Hashtag extraction** - Track tags automatically

### Platform Coverage
- ✅ **YouTube**: 20 videos with REAL commenters
- ✅ **TikTok**: 20 videos with thumbnails
- ✅ **Instagram**: 20 posts with thumbnails
- ✅ **Total**: 60 pieces of content tracked

### Benefits
- 📊 **Cross-platform analytics** in one place
- 🔄 **Swappable providers** for flexibility
- 💰 **Cost-effective** with free/cheap tiers
- 🎨 **Beautiful dashboards** with thumbnails
- 📈 **Data-driven decisions** for content strategy

---

**Instagram analytics now fully integrated with swappable design!** 🚀

Change providers anytime without breaking your application!
