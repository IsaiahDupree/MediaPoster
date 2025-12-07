# Instagram Looter2 API - Endpoint Reference

**Base URL**: `https://instagram-looter2.p.rapidapi.com`

**Headers Required**:
- `X-RapidAPI-Key`: Your RapidAPI key
- `X-RapidAPI-Host`: `instagram-looter2.p.rapidapi.com`

---

## 👤 User Insights

### `/profile` - User info by username
**Method**: GET
**Params**:
- `username` (required): Instagram username

**Returns**: Full user profile data including follower count, bio, profile pic, etc.

### `/user-feeds` - Media list by user ID  
**Method**: GET
**Params**:
- `id` (required): User ID
- `count` (optional): Number of posts (default: 12, max: 50)
- `end_cursor` (optional): Pagination cursor

**Returns**: List of user's posts with engagement stats

### `/id` - Convert username to user ID
**Method**: GET
**Params**:
- `username` (required): Instagram username

**Returns**: User ID

---

## 📸 Media Details

### `/post` - Media info by URL
**Method**: GET
**Params**:
- `url` (required): Instagram post URL

**Returns**: Full media details, stats, caption, etc.

### `/post` - Media info by ID
**Method**: GET  
**Params**:
- `id` (required): Media ID

**Returns**: Full media details

---

## 🔖 Hashtag Lookup

### `/tag-feeds` - Media by hashtag
**Method**: GET
**Params**:
- `tag` (required): Hashtag (without #)
- `count` (optional): Number of posts

**Returns**: Posts using that hashtag

---

## Key Response Fields

### User Profile Response:
```json
{
  "id": "user_id",
  "username": "username",
  "full_name": "Full Name",
  "biography": "Bio text",
  "profile_pic_url": "https://...",
  "is_verified": false,
  "is_private": false,
  "edge_followed_by": { "count": 123 },
  "edge_follow": { "count": 456 },
  "edge_owner_to_timeline_media": { "count": 789 }
}
```

### Media List Response:
```json
{
  "items": [
    {
      "id": "media_id",
      "code": "shortcode",
      "media_type": 1,  // 1=photo, 2=video, 8=carousel
      "caption": { "text": "..." },
      "like_count": 123,
      "comment_count": 45,
      "taken_at": 1234567890,
      "image_versions2": {
        "candidates": [
          { "url": "https://..." }
        ]
      }
    }
  ],
  "more_available": true,
  "next_max_id": "cursor_string"
}
```

---

## Rate Limits

**Free Tier**: 150 requests/month
**Pro Tier** ($9.90/mo): 15,000 requests/month, 10 req/sec
**Ultra Tier** ($27.90/mo): 75,000 requests/month, 30 req/sec
**Mega Tier** ($75.90/mo): 250,000 requests/month, 60 req/sec

---

## Important Notes

1. **User ID is required** for most endpoints - must first convert username to ID
2. **Pagination**: Use `end_cursor`/`next_max_id` from previous response
3. **Media Types**: 1=Photo, 2=Video, 8=Carousel (multiple images/videos)
4. **Thumbnails**: Located in `image_versions2.candidates[0].url` or `thumbnail_url`
5. **Captions**: Usually in `caption.text` or just `caption` (varies by endpoint)
