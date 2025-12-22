# LinkedIn Scraper API

## Overview
- **Host**: `linkedin-data-scraper.p.rapidapi.com`
- **Base URL**: `https://linkedin-data-scraper.p.rapidapi.com`
- **Status**: ⚠️ Rate limited (requires PRO plan for reliable access)
- **Rating**: 9.9/10
- **Provider**: RockApis
- **RapidAPI Link**: https://rapidapi.com/RockApis/api/real-time-linkedin-scraper-api

## Features
- Real-time profile data enrichment
- Company information
- Job listings
- Search functionality

## Authentication

```
X-RapidAPI-Key: YOUR_API_KEY
X-RapidAPI-Host: linkedin-data-scraper.p.rapidapi.com
```

## Endpoints

### GET /profile
Get LinkedIn profile data.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `url` | string | Yes | Full LinkedIn profile URL |

**Example Request:**
```bash
curl -X GET "https://linkedin-data-scraper.p.rapidapi.com/profile?url=https://www.linkedin.com/in/username/" \
  -H "X-RapidAPI-Key: YOUR_KEY" \
  -H "X-RapidAPI-Host: linkedin-data-scraper.p.rapidapi.com"
```

**Expected Response:**
```json
{
  "success": true,
  "data": {
    "name": "John Doe",
    "headline": "Software Engineer at Company",
    "location": "San Francisco, CA",
    "connections": 500,
    "about": "Bio description...",
    "experience": [...],
    "education": [...],
    "skills": [...],
    "profilePicture": "https://..."
  }
}
```

---

### GET /company
Get company information.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `url` | string | Yes | LinkedIn company URL |

---

### GET /search
Search LinkedIn profiles.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `query` | string | Yes | Search query |
| `type` | string | No | people, companies, jobs |

---

### GET /jobs
Get job listings.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `keywords` | string | Yes | Job keywords |
| `location` | string | No | Location filter |

---

## Alternative: Fresh LinkedIn Scraper API

- **Host**: Various
- **Rating**: 9.9/10
- **Provider**: SaleLeads

---

## Python Usage

```python
import httpx

RAPIDAPI_KEY = "your_key"
HOST = "linkedin-data-scraper.p.rapidapi.com"

headers = {
    "X-RapidAPI-Key": RAPIDAPI_KEY,
    "X-RapidAPI-Host": HOST,
}

# Get profile data
response = httpx.get(
    f"https://{HOST}/profile",
    headers=headers,
    params={"url": "https://www.linkedin.com/in/username/"}
)

data = response.json()
if data.get("success"):
    profile = data.get("data", {})
    print(f"Name: {profile.get('name')}")
    print(f"Headline: {profile.get('headline')}")
```

---

## Rate Limits

| Plan | Requests/Month |
|------|----------------|
| BASIC | 25 |
| PRO | 1,000 |
| ULTRA | 10,000 |

⚠️ **Note**: Free tier is very limited. Expect 429/403 errors without PRO subscription.

---

*Last Updated: December 2024*
