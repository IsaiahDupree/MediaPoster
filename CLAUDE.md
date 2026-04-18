# MediaPoster + MPLite — Claude Code Context

## What This System Does
Two complementary services for social media publishing:

| Service | Purpose | Location |
|---------|---------|----------|
| **MediaPoster** | Full AI-powered media factory: video analysis, AI generation, content pipeline, scheduling, analytics | `/Users/isaiahdupree/Documents/Software/MediaPoster/` |
| **MPLite** | Lightweight publish queue + Thompson Sampling optimal timing — deployed to Vercel | `/Users/isaiahdupree/Documents/Software/mediaposter-lite/` |
| **Blotato** | The actual publisher — API that pushes content to Instagram/TikTok/YouTube/Twitter etc. | `https://backend.blotato.com/v2` |

**The canonical publishing flow for any image or video:**
```
Local file
  → Supabase Storage (sora-videos bucket) → public URL
  → POST /v2/media → Blotato-hosted media URL
  → POST /v2/posts { accountId, platform, content, mediaUrls } → live post
```

---

## MediaPoster Full System

### Start / Stop
```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster

# Backend (FastAPI, port 5555)
cd Backend && source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload

# Frontend (Next.js, port 5557)
cd frontend && npm run dev -- -p 5557

# Kill if stuck
lsof -ti:5555 | xargs kill -9   # backend
lsof -ti:5557 | xargs kill -9   # frontend
```

### Health check
```bash
curl http://localhost:5555/health
curl http://localhost:5555/docs   # Swagger UI — all endpoints
```

### Key paths
- **Backend root:** `/Users/isaiahdupree/Documents/Software/MediaPoster/Backend/`
- **Blotato service:** `Backend/services/blotato_api.py` — full Blotato API wrapper, all platforms, AI video generation
- **Blotato client:** `Backend/modules/publishing/blotato_client.py` — upload_media + publish pipeline
- **Blotato accounts config:** `Backend/config/blotato_accounts.py` — account ID map
- **Publish service:** `Backend/services/publish_service.py` — multi-platform publish orchestrator
- **Supabase storage:** `Backend/services/supabase_storage.py` — upload files → public URL

---

## MPLite (Vercel — always on)

### URLs
- **Live dashboard:** `https://mediaposter-lite-isaiahduprees-projects.vercel.app`
- **API base:** `https://mediaposter-lite-isaiahduprees-projects.vercel.app/api`
- **Auth header:** `x-api-key: {MPLITE_KEY}`

### Key endpoints
```bash
MPLITE="https://mediaposter-lite-isaiahduprees-projects.vercel.app/api"
KEY="your_mplite_key"

# Health
curl $MPLITE/health

# Add to publish queue
curl -X POST $MPLITE/queue \
  -H "x-api-key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "instagram",
    "content_type": "image",
    "media_url": "https://...",
    "caption": "your caption",
    "scheduled_for": "2026-03-04T10:00:00Z"
  }'

# Get queue status
curl "$MPLITE/queue?status=pending" -H "x-api-key: $KEY"

# Daily summary
curl $MPLITE/daily-summary -H "x-api-key: $KEY"

# Can publish check (rate limits)
curl $MPLITE/can-publish/instagram -H "x-api-key: $KEY"
```

### Supabase table
MPLite uses `publish_queue` in the shared Supabase project (`ivhfuhxorppptyuofbgq`).
Items move through: `queued` → `scheduled` → `publishing` → `published` / `failed`

---

## Blotato Direct API

**The fastest path to posting anything.** No local server needed.

```bash
BLOTATO_KEY="$BLOTATO_API_KEY"
BLOTATO="https://backend.blotato.com/v2"

# Step 1: Upload media (needs public URL — use Supabase Storage or any CDN)
curl -X POST $BLOTATO/media \
  -H "blotato-api-key: $BLOTATO_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-public-url/image.jpg"}'
# Returns: { "url": "https://database.blotato.io/..." }

# Step 2: Publish
curl -X POST $BLOTATO/posts \
  -H "blotato-api-key: $BLOTATO_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "accountId": 807,
    "post": {
      "platform": "instagram",
      "text": "your caption",
      "mediaUrls": ["https://database.blotato.io/..."],
      "mediaType": "reel"
    }
  }'

# Check post status
curl $BLOTATO/posts/{id} -H "blotato-api-key: $BLOTATO_KEY"
```

### Upload local image to Supabase first
```python
import os
from supabase import create_client

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))

with open("/path/to/image.jpg", "rb") as f:
    sb.storage.from_("sora-videos").upload("images/my-image.jpg", f, {"content-type": "image/jpeg"})

public_url = sb.storage.from_("sora-videos").get_public_url("images/my-image.jpg")
print(public_url)  # Use this as mediaUrl in Blotato
```

Or using the CLI (one-liner):
```bash
cd /Users/isaiahdupree/Documents/Software/actp-worker && python3 -c "
from supabase import create_client
import config, sys
sb = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_ROLE_KEY)
path = sys.argv[1]; fname = path.split('/')[-1]
sb.storage.from_('sora-videos').upload(f'images/{fname}', open(path,'rb'), {'content-type':'image/jpeg'})
print(sb.storage.from_('sora-videos').get_public_url(f'images/{fname}'))
" /path/to/your/image.jpg
```

---

## Blotato Account IDs

| Platform | Account ID | Handle |
|----------|-----------|--------|
| Instagram | **807** | @the_isaiah_dupree ← primary |
| Instagram | 670 | @the_isaiah_dupree_ |
| Instagram | 1369 | @dupree_isaiah_ |
| TikTok | **710** | @isaiah_dupree ← primary |
| TikTok | 4508 | @dupree_isaiah |
| TikTok | 4150 | @isaiahdupree75 |
| TikTok | 4151 | @soursides_is_sour |
| YouTube | **228** | Isaiah Dupree ← primary |
| YouTube | 3370 | lofi creator |
| Twitter | **571** | @IsaiahDupree7 |
| Threads | 243 | @the_isaiah_dupree |
| Facebook | 786 | Isaiah Dupree (pageId: 346276551897190) |
| Pinterest | 173 | @isaiahdupree33 |
| LinkedIn | 571 | @IsaiahDupree7 |

### Platform-specific required fields
- **Instagram:** `"mediaType": "reel"` (or `"story"`)
- **YouTube:** `"title"` required, `"privacyStatus"`, `"containsSyntheticMedia"`
- **TikTok:** `"privacyLevel": "PUBLIC_TO_EVERYONE"`, `"disabledComments"`, `"isAiGenerated"`
- **Facebook:** `"pageId": "346276551897190"` required
- **scheduledTime:** top-level field (ISO 8601), NOT inside `post` object

---

## MCP Server (MediaPoster)

**File:** `/Users/isaiahdupree/Documents/Software/MediaPoster/mcp/server.js`
**Start:** `node /Users/isaiahdupree/Documents/Software/MediaPoster/mcp/server.js`

### Tools exposed
| Tool | What it does |
|------|-------------|
| `mp_health` | Check MediaPoster backend (5555) + MPLite (Vercel) status |
| `mp_upload_media` | Upload local file → Supabase Storage → return public URL |
| `mp_publish` | Publish image/video to any platform via Blotato immediately |
| `mp_schedule` | Add post to MPLite queue with optional scheduled_for time |
| `mp_queue_status` | Get MPLite queue counts by status and platform |
| `mp_accounts` | List all Blotato accounts with IDs |

### Add to Claude Code MCP config (~/.claude/config.json or project .mcp.json)
```json
{
  "mcpServers": {
    "mediaposter": {
      "command": "node",
      "args": ["/Users/isaiahdupree/Documents/Software/MediaPoster/mcp/server.js"],
      "env": {
        "BLOTATO_API_KEY": "$BLOTATO_API_KEY",
        "SUPABASE_URL": "https://ivhfuhxorppptyuofbgq.supabase.co",
        "SUPABASE_SERVICE_ROLE_KEY": "",
        "MPLITE_URL": "https://mediaposter-lite-isaiahduprees-projects.vercel.app",
        "MPLITE_KEY": ""
      }
    }
  }
}
```

---

## If MediaPoster Backend is Down

```bash
# 1. Check if process exists
lsof -i:5555

# 2. Start it
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 5555 --reload &

# 3. Verify
curl http://localhost:5555/health

# If venv missing:
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

**Note:** MPLite (Vercel) is always on — use it for queueing even when MediaPoster is down.
Blotato API is also always on — direct API calls work regardless of local server state.
