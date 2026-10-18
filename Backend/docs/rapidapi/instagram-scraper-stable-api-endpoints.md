# Instagram Scraper Stable API - Complete Endpoint Reference

**Host:** `instagram-scraper-stable-api.p.rapidapi.com`  
**Provider:** RockSolid APIs (thetechguy32744)  
**RapidAPI:** [https://rapidapi.com/thetechguy32744/api/instagram-scraper-stable-api](https://rapidapi.com/thetechguy32744/api/instagram-scraper-stable-api)  
**Content-Type:** `application/x-www-form-urlencoded`  
**Last Updated:** 2025-12-26

## Important Notes

- All POST endpoints use `application/x-www-form-urlencoded` content type
- Parameter `username_or_url` accepts: username, user ID, or full Instagram URL
- This API returns **metadata only** - video/audio download URLs are NOT included
- For actual media downloads, use a different API or Instagram's CDN URLs

## Endpoints (27 total)

### POST Search (Users + Hashtags)

**Path:** `/search_ig.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `query` | ✓ |  |

---

### POST User Bio Links

**Path:** `/get_ig_user_bio_links.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |

---

### POST User Stories

**Path:** `/get_ig_user_stories.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |

---

### GET Basic User + Posts

**Path:** `/get_ig_basic_user.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |

---

### POST Account Data

**Path:** `/get_ig_account_data.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |

---

### POST Account Data V2

**Path:** `/get_ig_account_data_v2.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |

---

### GET User About

**Path:** `/get_ig_user_about.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |

---

### GET User Similar Accounts

**Path:** `/get_ig_similar_accounts.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |

---

### POST Followers List v2

**Path:** `/get_ig_followers_v2.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |
| `amount` |  |  |

---

### POST Followers List

**Path:** `/get_ig_followers.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |

---

### POST Following List v2

**Path:** `/get_ig_following_v2.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |

---

### POST Following List

**Path:** `/get_ig_following.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |

---

### POST User Posts

**Path:** `/get_ig_user_posts.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |
| `amount` |  |  |

---

### POST User Reels

**Path:** `/get_ig_user_reels.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |
| `amount` |  |  |

---

### POST User Highlights

**Path:** `/get_ig_user_highlights.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |

---

### POST User Highlight Stories

**Path:** `/get_ig_highlight_stories.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `highlight_id` | ✓ |  |

---

### POST User Tagged Posts

**Path:** `/get_ig_user_tagged.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `username_or_url` | ✓ |  |

---

### GET Detailed Media Data v2

**Path:** `/get_media_data_v2.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `media_code` | ✓ |  |

---

### GET Get Post Likers V2

**Path:** `/get_ig_post_likers_v2.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `media_code` | ✓ |  |

---

### GET GET Post Title/Description

**Path:** `/get_ig_post_caption.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `media_code` | ✓ |  |

---

### GET Detailed Post Data

**Path:** `/get_media_data.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `reel_post_code_or_url` | ✓ |  |
| `type` | ✓ |  |

---

### GET Get Reel Title/Description

**Path:** `/get_ig_reel_caption.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `media_code` | ✓ |  |

---

### GET Detailed Reel Data

**Path:** `/get_media_data.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `reel_post_code_or_url` | ✓ |  |
| `type` | ✓ |  (default: `reel`) |

---

### GET Get Post Comments

**Path:** `/get_ig_post_comments.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `media_code` | ✓ |  |

---

### GET Get Comment Replies

**Path:** `/get_ig_comment_replies.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `comment_id` | ✓ |  |

---

### GET Get Media Code or ID

**Path:** `/get_ig_media_id.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `url` | ✓ |  |

---

### GET Posts & Reels V2 (Hashtag)

**Path:** `/get_ig_hashtag_posts_v2.php`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `hashtag` | ✓ |  |

---

