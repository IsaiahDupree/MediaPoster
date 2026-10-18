# YouTube Trend Enrichment Strategy

## Current State
✅ Basic trend discovery working:
- Title templates
- Entities
- Format trends (duration)
- Channel-normalized uplift scoring

## Enhancement Plan

### 1. **Richer Video Metadata Collection**

#### Already Available in YouTube Data API v3
```python
# Current API call gets: snippet, statistics, contentDetails
# We need to also request: topicDetails

response = await client.get(
    "https://www.googleapis.com/youtube/v3/videos",
    params={
        "part": "snippet,statistics,contentDetails,topicDetails",
        "id": "video_ids",
        "key": API_KEY
    }
)
```

**New Fields to Extract:**
- `snippet.description` - Full video description (currently not extracted)
- `snippet.thumbnails.high.url` - High-res thumbnail URL
- `snippet.tags` - Video tags
- `topicDetails.topicCategories` - Wikipedia topic URLs
- `statistics.commentCount` - Comment activity
- `statistics.favoriteCount` - Favorites

#### Comment Activity Analysis
```python
# Separate API call for top comments
GET https://www.googleapis.com/youtube/v3/commentThreads
params: videoId, part=snippet, maxResults=100, order=relevance
```

**Extract:**
- Top comment themes
- Comment velocity (comments/day)
- Sentiment signals
- Question patterns (what viewers ask)

---

### 2. **Topic Clustering (Semantic Analysis)**

Instead of just title templates, cluster by **meaning**:

```python
from openai import OpenAI

# For each video title + description
embeddings = openai.embeddings.create(
    model="text-embedding-3-small",
    input=[f"{title}\n\n{description}" for video in videos]
)

# Cluster embeddings using HDBSCAN or K-means
from sklearn.cluster import HDBSCAN
clusters = HDBSCAN(min_cluster_size=3).fit(embeddings)

# Label each cluster
for cluster_id in unique_clusters:
    cluster_videos = [v for v in videos if v.cluster == cluster_id]
    cluster_titles = [v.title for v in cluster_videos]
    
    # Use GPT to generate cluster label
    label = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": f"What topic do these video titles share?\n{cluster_titles}"
        }]
    )
```

**Result:** Topic trends like:
- "AI productivity tools"
- "Morning routine optimization"
- "Passive income strategies"

---

### 3. **Description Analysis**

Extract structured data from descriptions:

```python
def extract_from_description(description: str) -> Dict:
    """Extract links, timestamps, products, CTAs"""
    
    return {
        "links": re.findall(r'https?://\S+', description),
        "timestamps": re.findall(r'(\d{1,2}:\d{2})\s*-?\s*(.+)', description),
        "products_mentioned": extract_products(description),
        "affiliate_links": [l for l in links if 'amzn.to' in l or 'geni.us' in l],
        "cta_phrases": ["Get my course", "Download free", "Join the community"],
    }
```

**Trend Signals:**
- Products frequently linked (affiliate trends)
- Chapter structure patterns (timestamp usage)
- CTA patterns (what successful creators ask viewers to do)

---

### 4. **Thumbnail Analysis**

Download and analyze thumbnails:

```python
import cv2
from PIL import Image

async def analyze_thumbnail(thumbnail_url: str) -> Dict:
    """Extract visual patterns from thumbnails"""
    
    # Download image
    img = await download_image(thumbnail_url)
    
    # Analyze
    return {
        "dominant_colors": extract_colors(img),
        "text_present": detect_text_overlay(img),  # OCR
        "face_count": detect_faces(img),
        "emotion": detect_emotion(img),  # surprised face, pointing, etc.
        "composition": analyze_layout(img),  # rule of thirds, etc.
    }
```

**Trend Signals:**
- Thumbnail styles that perform well
- Text overlay patterns ("You WON'T BELIEVE...")
- Color schemes trending in niche
- Face vs no-face performance

---

### 5. **Google Ads Keyword Density Integration**

Use Google Ads API to check keyword competition:

```python
from google.ads.googleads.client import GoogleAdsClient

async def get_keyword_metrics(keywords: List[str]) -> Dict:
    """Get search volume and competition for keywords"""
    
    client = GoogleAdsClient.load_from_storage()
    keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")
    
    request = client.get_type("GenerateKeywordIdeasRequest")
    request.customer_id = CUSTOMER_ID
    request.keyword_seed.keywords.extend(keywords)
    
    response = keyword_plan_idea_service.generate_keyword_ideas(request=request)
    
    return {
        keyword: {
            "avg_monthly_searches": idea.keyword_idea_metrics.avg_monthly_searches,
            "competition": idea.keyword_idea_metrics.competition,  # LOW/MEDIUM/HIGH
            "competition_index": idea.keyword_idea_metrics.competition_index,  # 0-100
            "low_top_of_page_bid_micros": idea.keyword_idea_metrics.low_top_of_page_bid_micros,
            "high_top_of_page_bid_micros": idea.keyword_idea_metrics.high_top_of_page_bid_micros,
        }
        for idea in response
    }
```

**Trend Signals:**
- Topics with high search volume + low competition (opportunity)
- Rising keyword trends (month-over-month growth)
- CPC trends (what advertisers are willing to pay)
- Seasonal patterns

---

### 6. **Engagement Rate Normalization**

Current: We calculate uplift (views vs channel median)

**Add:**
```python
def calculate_engagement_metrics(video: Dict, channel_baseline: Dict) -> Dict:
    """Calculate normalized engagement"""
    
    views = int(video["statistics"]["viewCount"])
    likes = int(video["statistics"]["likeCount"])
    comments = int(video["statistics"]["commentCount"])
    
    # Engagement rate
    like_rate = likes / views if views > 0 else 0
    comment_rate = comments / views if views > 0 else 0
    
    # Normalized against channel baseline
    like_rate_uplift = like_rate / channel_baseline["median_like_rate"]
    comment_rate_uplift = comment_rate / channel_baseline["median_comment_rate"]
    
    # Velocity (if we have publish date)
    hours_since_publish = (datetime.now() - video["publishedAt"]).total_seconds() / 3600
    views_per_hour = views / hours_since_publish if hours_since_publish > 0 else 0
    
    return {
        "like_rate": like_rate,
        "comment_rate": comment_rate,
        "like_rate_uplift": like_rate_uplift,
        "comment_rate_uplift": comment_rate_uplift,
        "views_per_hour": views_per_hour,
        "engagement_score": (like_rate_uplift + comment_rate_uplift) / 2,
    }
```

---

### 7. **Enhanced Trend Card Output**

Instead of just:
```json
{
  "trend_type": "title_template",
  "title": "How to X",
  "score": 0.40
}
```

Output:
```json
{
  "trend_type": "topic_cluster",
  "title": "AI Productivity Tools",
  "score": 0.85,
  "metadata": {
    "videos": 15,
    "channels": 5,
    "total_views": 2500000,
    "avg_engagement_rate": 0.045,
    "median_uplift": 2.3,
    "velocity": "+45% last 7 days",
    
    "top_titles": [
      "I tried ChatGPT for my entire workflow",
      "10 AI tools that replaced my team",
      "How I use AI to work 4 hours a day"
    ],
    
    "top_thumbnails": [
      "https://i.ytimg.com/vi/abc123/maxresdefault.jpg"
    ],
    
    "common_description_elements": {
      "products": ["Notion", "ChatGPT Plus", "Zapier"],
      "affiliate_links": 8,
      "avg_timestamps": 6,
      "cta_pattern": "Get my free AI toolkit"
    },
    
    "comment_themes": [
      "Which AI tool is best for beginners?",
      "Does this work for freelancers?",
      "Can you make a tutorial?"
    ],
    
    "google_ads_data": {
      "primary_keyword": "ai productivity tools",
      "search_volume": 12000,
      "competition": "MEDIUM",
      "cpc_range": "$1.20 - $3.50",
      "trend": "+25% MoM"
    },
    
    "recommended_angles": [
      "Beginner-friendly AI tool comparison",
      "AI productivity for freelancers",
      "Free vs paid AI tools breakdown"
    ]
  }
}
```

---

## Implementation Priority

### Phase 1: Immediate (No new APIs needed)
1. ✅ Extract descriptions from existing API calls
2. ✅ Add topicDetails to API requests
3. ✅ Calculate engagement rates (like/comment ratios)
4. ✅ Extract links and products from descriptions

### Phase 2: AI Enhancement (OpenAI API)
5. 🔄 Topic clustering with embeddings
6. 🔄 GPT-based cluster labeling
7. 🔄 Description analysis (extract products, CTAs)

### Phase 3: Comment Analysis (YouTube API)
8. ⏳ Fetch top comments per video
9. ⏳ Extract comment themes
10. ⏳ Calculate comment velocity

### Phase 4: Visual Analysis (Computer Vision)
11. ⏳ Download thumbnails
12. ⏳ OCR text extraction
13. ⏳ Face detection
14. ⏳ Color analysis

### Phase 5: Google Ads Integration (Ads API)
15. ⏳ Set up Google Ads API credentials
16. ⏳ Extract keywords from titles/descriptions
17. ⏳ Fetch keyword metrics (volume, competition, CPC)
18. ⏳ Calculate opportunity scores

---

## API Quotas to Consider

**YouTube Data API v3:**
- Default quota: 10,000 units/day
- videos.list: 1 unit per request (up to 50 videos)
- commentThreads.list: 1 unit per request
- Strategy: Batch video requests, cache results

**OpenAI API:**
- Embeddings: ~$0.00002 per 1K tokens
- GPT-4o-mini: ~$0.15 per 1M input tokens
- For 1000 videos: ~$0.50 total

**Google Ads API:**
- Free to use (requires Ads account)
- Rate limits: 15,000 operations/day

---

## Database Schema Updates Needed

```sql
-- Add to trend_clusters table
ALTER TABLE trend_clusters ADD COLUMN metadata JSONB;

-- Store enriched video data
CREATE TABLE youtube_videos_enriched (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    video_id TEXT UNIQUE NOT NULL,
    channel_id TEXT NOT NULL,
    title TEXT,
    description TEXT,
    thumbnail_url TEXT,
    tags TEXT[],
    topic_categories TEXT[],
    
    -- Stats
    view_count BIGINT,
    like_count INTEGER,
    comment_count INTEGER,
    
    -- Calculated metrics
    like_rate FLOAT,
    comment_rate FLOAT,
    engagement_score FLOAT,
    views_per_hour FLOAT,
    
    -- Enrichment
    description_links TEXT[],
    products_mentioned TEXT[],
    affiliate_links TEXT[],
    thumbnail_analysis JSONB,
    top_comments JSONB,
    
    -- Clustering
    embedding_vector VECTOR(1536),  -- for pgvector
    topic_cluster_id INTEGER,
    
    published_at TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ DEFAULT NOW()
);

-- Google Ads keyword data
CREATE TABLE keyword_metrics (
    keyword TEXT PRIMARY KEY,
    avg_monthly_searches BIGINT,
    competition TEXT,  -- LOW/MEDIUM/HIGH
    competition_index INTEGER,
    cpc_low_micros BIGINT,
    cpc_high_micros BIGINT,
    trend_direction TEXT,  -- UP/DOWN/STABLE
    last_updated TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Next Steps

Want me to implement:
1. **Phase 1** (descriptions, engagement rates) - immediate, no new APIs
2. **Phase 2** (topic clustering with OpenAI) - best ROI for trend quality
3. **Phase 3** (comment analysis) - good for understanding audience
4. **Phase 4** (thumbnail analysis) - visual trends
5. **Phase 5** (Google Ads integration) - keyword opportunity scoring

Which phase should we start with?
