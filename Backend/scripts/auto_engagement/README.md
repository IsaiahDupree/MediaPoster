# Auto-Engagement Package

Modular, reusable components for automating social media engagement using Safari browser automation and AI-powered comment generation.

## Features

- **Safari Browser Controller** - Core automation utilities with AppleScript and JavaScript injection
- **AI Comment Generator** - OpenAI GPT-4o powered contextual comment generation
- **Platform-Specific Modules** - Threads, Instagram, TikTok engagement
- **Full Context Extraction** - Post content, comments, engagement stats
- **Proof Screenshots** - Verifiable engagement documentation

## Installation

The package is located at `Backend/scripts/auto_engagement/`. Ensure you have:

1. macOS with Safari browser
2. Safari > Develop > Allow Remote Automation enabled
3. `OPENAI_API_KEY` environment variable set
4. Logged into social media platforms in Safari

## Quick Start

### Multi-Platform Engagement

```python
from auto_engagement import MultiPlatformEngagement

# Engage with all platforms
engagement = MultiPlatformEngagement()
results = engagement.engage_all_platforms()

# Or specific platforms
results = engagement.engage_all_platforms(platforms=['threads', 'instagram'])
```

### Individual Platform Engagement

```python
from auto_engagement import ThreadsEngagement, InstagramEngagement, TikTokEngagement

# Threads
threads = ThreadsEngagement()
result = threads.engage_with_post()
print(f"Posted: {result.comment_posted}")
print(f"Comment: {result.generated_comment}")

# Instagram
instagram = InstagramEngagement()
result = instagram.engage_with_post()

# TikTok
tiktok = TikTokEngagement()
result = tiktok.engage_with_video()
```

### Using Individual Components

```python
from auto_engagement import SafariController, AICommentGenerator

# Safari automation
safari = SafariController()
safari.navigate_to('https://www.instagram.com/')
result = safari.execute_js('return document.title')
safari.take_screenshot('/tmp/screenshot.png')

# AI comment generation
ai = AICommentGenerator()
comment = ai.generate_comment(
    platform='instagram',
    post_content='Amazing sunset photo!',
    existing_comments=['So beautiful!', 'Where is this?'],
    username='photographer123'
)
print(comment.text)
```

## Module Reference

### SafariController

Core Safari automation utilities.

| Method | Description |
|--------|-------------|
| `navigate_to(url, wait_time)` | Navigate to URL |
| `navigate_with_verification(url, domain, max_attempts)` | Navigate with domain verification |
| `execute_js(code)` | Execute JavaScript in Safari |
| `take_screenshot(filepath)` | Capture Safari window screenshot |
| `type_via_clipboard(text)` | Type text using clipboard (supports emojis) |
| `scroll_down(pixels)` | Scroll page down |
| `refresh_page()` | Refresh current page |

### AICommentGenerator

OpenAI-powered comment generation.

| Method | Description |
|--------|-------------|
| `generate_comment(platform, post_content, existing_comments, username, engagement)` | Generate contextual comment |
| `analyze_image(image_path, prompt)` | Analyze image with Vision API |
| `generate_from_context(context)` | Generate from PostContext object |

### Platform Engagement Classes

Each platform class follows the same pattern:

| Method | Description |
|--------|-------------|
| `engage_with_post()` / `engage_with_video()` | Full engagement flow |
| `check_login_state()` | Check if logged in |

## Engagement Flow

### Threads
1. Navigate to Threads feed
2. Find post with engagement
3. **Click into post page** to see all replies
4. Extract main post + ALL replies
5. Generate contextual AI comment
6. Post reply
7. Capture proof screenshot

### Instagram
1. Navigate to Instagram feed
2. Find post in feed
3. **Like post** in feed
4. Navigate to post page
5. **Expand comments** (click "View all X comments")
6. Extract caption + ALL comments
7. Generate contextual AI comment
8. Post comment
9. Capture proof screenshot

### TikTok
1. Navigate to For You page **with URL verification**
2. Pause video
3. Extract video data (creator, description, engagement)
4. **Like video**
5. Open comments panel
6. Extract top comments
7. Generate contextual AI comment
8. Post comment
9. Capture proof screenshot

## Result Objects

### ThreadsEngagementResult

```python
@dataclass
class ThreadsEngagementResult:
    success: bool
    username: str
    post_url: str
    post_content: str
    replies_found: int
    replies: List[str]
    generated_comment: str
    comment_posted: bool
    proof_screenshot: str
    error: str
```

### InstagramEngagementResult

```python
@dataclass
class InstagramEngagementResult:
    success: bool
    username: str
    post_url: str
    caption: str
    comments_found: int
    comments: List[str]
    liked: bool
    generated_comment: str
    comment_posted: bool
    proof_screenshot: str
    error: str
```

### TikTokEngagementResult

```python
@dataclass
class TikTokEngagementResult:
    success: bool
    username: str
    description: str
    likes: str
    comments_count: str
    shares: str
    comments_found: int
    comments: List[str]
    liked: bool
    generated_comment: str
    comment_posted: bool
    proof_screenshot: str
    error: str
```

## Running Tests

### Command Line

```bash
# Test individual platforms
cd Backend/scripts
python -m auto_engagement.threads_engagement
python -m auto_engagement.instagram_engagement
python -m auto_engagement.tiktok_engagement

# Test all platforms
python -c "from auto_engagement import MultiPlatformEngagement; MultiPlatformEngagement().engage_all_platforms()"
```

### With Environment Variable

```bash
OPENAI_API_KEY=your_key python -m auto_engagement.threads_engagement
```

## Integration with Other Services

### Example: Brand Ops Integration

```python
from auto_engagement import MultiPlatformEngagement
from services.auto_engagement_tracker import AutoEngagementTracker

tracker = AutoEngagementTracker()
engagement = MultiPlatformEngagement()

results = engagement.engage_all_platforms()

for r in results:
    if r['success']:
        run_id = tracker.start_agent_run('auto_engagement', platform=r['platform'])
        result = r['result']
        
        if result.comment_posted:
            tracker.log_comment(
                run_id=run_id,
                platform=r['platform'],
                post_url=getattr(result, 'post_url', ''),
                username=result.username,
                comment_text=result.generated_comment,
                verified=True
            )
        
        tracker.complete_agent_run(run_id)
```

### Example: Scheduled Engagement

```python
import schedule
from auto_engagement import MultiPlatformEngagement

def daily_engagement():
    engagement = MultiPlatformEngagement()
    results = engagement.engage_all_platforms()
    
    # Log results
    for r in results:
        print(f"{r['platform']}: {'✅' if r['success'] else '❌'}")

# Run twice daily
schedule.every().day.at("09:00").do(daily_engagement)
schedule.every().day.at("18:00").do(daily_engagement)
```

## Troubleshooting

### Safari Not Responding
- Ensure Safari > Develop > Allow Remote Automation is enabled
- Restart Safari if it's unresponsive

### Login Required
- Manually log into each platform in Safari first
- The scripts assume you're already logged in

### Selectors Not Working
- Social media platforms frequently update their DOM structure
- Check proof screenshots to see what's happening
- Update JavaScript selectors in the platform modules as needed

### Comment Not Posting
- Check if the platform has rate limiting
- Verify the comment doesn't violate platform guidelines
- Some platforms require additional verification for new accounts

## File Structure

```
auto_engagement/
├── __init__.py              # Package exports + MultiPlatformEngagement
├── README.md                # This documentation
├── safari_controller.py     # Core Safari automation
├── ai_comment_generator.py  # OpenAI comment generation
├── threads_engagement.py    # Threads automation
├── instagram_engagement.py  # Instagram automation
└── tiktok_engagement.py     # TikTok automation
```
