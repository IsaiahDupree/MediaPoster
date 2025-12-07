# TikTok Scraper Integration Configuration

## Overview
The TikTok Scraper integration enables trending content discovery, competitive analysis, and hashtag research to inform your content strategy.

## RapidAPI Setup

### 1. Get API Key
1. Visit [https://rapidapi.com/tikwm-tikwm-default/api/tiktok-scraper7](https://rapidapi.com/tikwm-tikwm-default/api/tiktok-scraper7)
2. Subscribe to a plan (Basic plan available for testing)
3. Copy your RapidAPI key from the dashboard

### 2. Configure Environment Variable
Add to your `.env` file:
```
RAPIDAPI_KEY=your_rapidapi_key_here
```

## Available Features

### 1. Trending Topics Discovery
```bash
GET /api/trending/topics?region=US&limit=50
```
- Analyzes currently trending TikTok content
- Returns hashtags ranked by engagement rate
- Stores top insights in database for recommendations

### 2. Competitor Analysis
```bash
GET /api/trending/competitor/username?count=20
```
- Analyzes any TikTok creator's content strategy
- Returns average views, engagement rate
- Shows top hashtags and best performing videos
- Identifies content patterns

### 3. Hashtag Research
```bash
GET /api/trending/hashtag/viral?count=30
```
- Deep analysis of any hashtag's performance
- Returns engagement metrics and reach data
- Recommends optimal posting times
- Provides strategic recommendations

### 4. Content Idea Generation
```bash
GET /api/trending/ideas?region=US
```
- Generates content ideas based on trending videos
- Shows what's working and why
- Suggests hashtags to use
- Provides actionable next steps

### 5. Video Details
```bash
GET /api/trending/video/{video_id}
```
- Fetches detailed metadata for any TikTok video
- Returns stats, author info, music data
- Useful for analyzing specific viral content

## API Capabilities

The TikTok Scraper API provides:
- ✅ Trending feed by region
- ✅ Hashtag search with pagination
- ✅ User post history
- ✅ Video metadata and stats
- ✅ Comment extraction
- ✅ No video downloads (respects TikTok ToS)

## Integration Points

### 1. Content Intelligence System
Trending insights are stored as `ContentInsight` records with:
- Type: `trending_topic`
- 3-day expiration (trends move fast)
- Confidence score based on sample size
- Pattern data for analysis

### 2. Recommendations Engine
The Insights Engine can now:
- Suggest trending hashtags to use
- Recommend optimal content formats
- Identify successful competitor strategies
- Generate data-driven content ideas

### 3. Analytics Dashboard
Frontend can display:
- Current trending topics
- Competitor performance benchmarks
- Hashtag effectiveness scores
- Content idea board

## Rate Limits

- Basic plan: Varies by endpoint (check RapidAPI dashboard)
- Use pagination cursors for large data sets
- Implement caching for frequently accessed data

## Example Workflows

### Find Trending Content in Your Niche
1. Call `/api/trending/topics` to see what's hot
2. Filter by relevant hashtags
3. Analyze top videos with `/api/trending/video/{id}`
4. Adapt concepts for your brand

### Analyze Competitor Strategy
1. Call `/api/trending/competitor/{username}`
2. Review their top hashtags and posting patterns
3. Examine best performing videos
4. Identify gaps and opportunities

### Research Hashtags Before Posting
1. Call `/api/trending/hashtag/{tag}` for each hashtag you're considering
2. Compare engagement rates
3. Note optimal posting times
4. Choose the best combination

## Error Handling

If `RAPIDAPI_KEY` is not configured:
- API returns empty arrays
- Services log warnings
- System continues functioning without trending data

## Data Freshness

- Trending data updates in real-time
- Stored insights expire after 3 days
- Re-query for latest data
- Implement caching layer for rate limit optimization

## Future Enhancements

- [ ] Automated trending alerts
- [ ] Scheduled trend reports
- [ ] Multi-platform trend comparison (TikTok + Instagram Reels)
- [ ] AI-powered content remixing suggestions
- [ ] Trend prediction using historical data

## Support

For API issues: [RapidAPI Support](https://support.rapidapi.com)  
For integration issues: Check service logs in `Backend/services/tiktok_scraper.py`
