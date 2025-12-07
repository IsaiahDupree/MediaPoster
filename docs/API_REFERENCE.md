# MediaPoster API Reference

> Base URL: `http://localhost:5555`
> 
> Interactive Docs: http://localhost:5555/docs

## Authentication

Currently using mock authentication. All endpoints are accessible without auth in development.

---

## Analytics Endpoints

### Overview

```http
GET /api/social-analytics/overview
```

Returns dashboard overview with aggregated metrics.

**Response:**
```json
{
  "total_followers": 0,
  "total_posts": 0,
  "total_engagement": 0,
  "accounts": []
}
```

---

### Accounts

```http
GET /api/social-analytics/accounts
```

Returns list of connected social media accounts.

**Response:**
```json
[
  {
    "platform": "instagram",
    "username": "example",
    "followers_count": 1000,
    "total_views": 5000,
    "engagement_rate": 3.5
  }
]
```

---

### Trends

```http
GET /api/social-analytics/trends?days=7
```

Returns analytics trends over time.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `days` | integer | 7 | Number of days to include |

**Response:**
```json
{
  "period_days": 7,
  "data_points": 7,
  "trends": [
    {
      "date": "2025-12-01",
      "followers": 1000,
      "views": 500,
      "likes": 100,
      "engagement_rate": 3.5
    }
  ]
}
```

---

### Content Performance

```http
GET /api/social-analytics/content?limit=20
```

Returns content performance metrics.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `limit` | integer | 20 | Maximum results |
| `min_platforms` | integer | 1 | Minimum platform count |

---

## Video Library

### List Videos

```http
GET /api/videos/?limit=50&offset=0
```

Returns paginated list of videos.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `limit` | integer | 50 | Maximum results |
| `offset` | integer | 0 | Pagination offset |

**Response:**
```json
[
  {
    "id": "uuid",
    "file_name": "video.mp4",
    "duration_sec": 120,
    "source_type": "upload",
    "thumbnail_path": "/thumbnails/video.jpg",
    "created_at": "2025-12-07T00:00:00Z"
  }
]
```

---

### List Clips

```http
GET /api/clips/
```

Returns list of generated clips.

**Response:**
```json
{
  "clips": [
    {
      "clip_id": "uuid",
      "video_id": "uuid",
      "start_time": 10.5,
      "end_time": 30.0,
      "duration": 19.5,
      "status": "ready"
    }
  ],
  "total": 1
}
```

---

## Publishing

### Scheduled Posts

```http
GET /api/publishing/scheduled?limit=50
```

Returns list of scheduled posts.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `limit` | integer | 50 | Maximum results |
| `status` | string | null | Filter by status |

**Response:**
```json
[
  {
    "id": "uuid",
    "clip_id": "uuid",
    "platform": "tiktok",
    "scheduled_time": "2025-12-08T10:00:00Z",
    "status": "pending"
  }
]
```

---

### Schedule Post

```http
POST /api/publishing/schedule
```

Schedule a clip for publishing.

**Request Body:**
```json
{
  "clip_id": "uuid",
  "platforms": ["tiktok", "instagram"],
  "scheduled_time": "2025-12-08T10:00:00Z",
  "caption": "Check out this clip!",
  "hashtags": ["viral", "content"]
}
```

---

### Calendar View

```http
GET /api/publishing/calendar?start_date=2025-12-01&end_date=2025-12-31
```

Returns posts for calendar display.

---

## Platform Management

### Available Platforms

```http
GET /api/platform/platforms
```

Returns list of supported platforms.

**Response:**
```json
{
  "platforms": ["tiktok", "instagram", "youtube", "twitter", "facebook", "linkedin", "pinterest", "threads", "bluesky"],
  "total": 9
}
```

---

### Published Posts

```http
GET /api/platform/posts?limit=50&platform=tiktok
```

Returns list of published posts.

**Parameters:**
| Name | Type | Default | Description |
|------|------|---------|-------------|
| `limit` | integer | 50 | Maximum results |
| `platform` | string | null | Filter by platform |
| `status` | string | null | Filter by status |

---

## Goals

### List Goals

```http
GET /api/goals/
```

Returns user's posting goals.

**Response:**
```json
[
  {
    "id": "uuid",
    "goal_type": "weekly_posts",
    "target_value": 7,
    "current_value": 3,
    "progress_percent": 42.8,
    "period_start": "2025-12-01",
    "period_end": "2025-12-07"
  }
]
```

---

### Create Goal

```http
POST /api/goals/
```

Create a new goal.

**Request Body:**
```json
{
  "goal_type": "weekly_posts",
  "target_value": 7,
  "platform": "all"
}
```

---

## Recommendations

### Get Recommendations

```http
GET /api/recommendations
```

Returns AI-generated content recommendations.

**Response:**
```json
{
  "optimal_posting_times": [
    {"day": "Monday", "time": "18:00", "engagement_score": 8.5}
  ],
  "content_suggestions": [
    "Create behind-the-scenes content",
    "Try trending audio"
  ],
  "hashtag_recommendations": ["viral", "fyp", "trending"]
}
```

---

## Coaching

### Get Coaching Recommendations

```http
GET /api/coaching/recommendations?goal_id=uuid
```

Returns personalized coaching advice.

---

### Chat with Coach

```http
POST /api/coaching/chat
```

Interactive chat with AI coach.

**Request Body:**
```json
{
  "message": "How can I improve my engagement?",
  "context": {
    "platform": "instagram"
  }
}
```

**Response:**
```json
{
  "message": "Here are some tips...",
  "recommendations": {},
  "suggestions": ["Post consistently", "Use trending hashtags"]
}
```

---

## Error Responses

All endpoints return consistent error formats:

### 400 Bad Request
```json
{
  "detail": "Invalid parameter value"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "message": "Error details..."
}
```

---

## Rate Limiting

Development: No rate limiting

Production: TBD

---

## Pagination

Endpoints returning lists support pagination:

```http
GET /api/endpoint?limit=20&offset=0
```

| Parameter | Type | Default | Max |
|-----------|------|---------|-----|
| `limit` | integer | varies | 100-200 |
| `offset` | integer | 0 | - |
