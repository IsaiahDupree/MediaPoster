# Blotato Error Reference

## API Errors

| Error | Explanation |
|-------|-------------|
| Authorization failed - please check your credentials | Double check your Blotato API key |
| Wrong Blotato API Key | Check API key copied correctly without whitespaces |
| URL is empty | URL being passed is empty. Check previous step finished |
| Wrong Account ID | Check account ID copied correctly |
| Wrong Page ID | Facebook requires both Account ID and Page ID |
| Invalid File Format | Check file format is valid per platform requirements |
| Invalid Video Dimensions | Video dimensions not supported. Test with sample video |
| reached_active_user_cap | Account not properly warmed up |
| You Ran Out Of AI Credits | Check Settings > Billing |
| Wrong Template Parameters | Check API docs for correct template parameters |
| Missing AI Voice | POV template doesn't include AI voice |
| Missing Music | Add autoAddMusic: true for TikTok |
| Wrong Heygen API Key and IDs | Check HEYGEN AVATAR ID, not Avatar GROUP ID |
| You're On Heygen Free Plan | Requires $99/mo API plan |
| Your Avatar Has a Background | Set matting to false |
| Invalid JSON Error | Validate JSON at jsonlint.com |
| The service is receiving too many requests | Rate limit: Upload 10/min, Publish 30/min |
| The aspect ratio is not supported | Check platform aspect ratio requirements |
| body/template/id must be equal to constant | Pass template object with id |
| mediaURL is null or empty | Video not done. Increase wait time or check credits |
| Please review our URL ownership verification rules | TikTok rejects URL. Upload media first, use Blotato URL |
| Tiktok's servers may be experiencing issues | TikTok server issue or posting too frequently |
| Threads API Feature Not Available | Link Instagram to Threads. Warm up account first |
| Failed to read media metadata | File not accessible or invalid. Check Google Drive URL format |
| Base64 data is too large, maximum size is 20MB | Switch to URL-based upload for files > 15MB |
| Error posting to Instagram: No error | Reduce hashtags, caption length, increase time between posts |

## Connection Errors

| Error | Explanation |
|-------|-------------|
| 400 Session Error Connecting Instagram | Use incognito, log out others, log into target only |
| Unable to connect LinkedIn company page | Verify you're Admin. Use incognito browser |
| YouTube Unauthorized error | Incognito browser, log into YouTube, then Blotato |
| Unable to connect social account (general) | Incognito Chrome, log into social first, then Blotato |

## Platform-Specific Errors

| Error | Explanation |
|-------|-------------|
| Post failed to publish. Could not upload video | Check video meets platform requirements |
| The user has exceeded the number of videos they may upload (YouTube) | Wait 24 hours or check API quota |
| TikTok views consistently < 50 | Account likely shadowbanned |
| TikTok views consistently ~200 | Use niche keywords in title/description |
| Single TikTok video stuck at low views | Change to PRIVATE, close app, reopen, switch to EVERYONE |
| TikTok account banned | Not warmed up properly. Don't post > 3x/day via API |
| Escape Multi-Line Paragraphs error | Use toJsonString() for long text with linebreaks |
| Brand New Account error | Warm up account with manual posts first |
| Sorry! This site doesn't allow you to save Pins | Website disabled Pinterest saving |

## Account Limits

| Platform | Limit | Explanation |
|----------|-------|-------------|
| TikTok (Starter) | 3 accounts/24h, 10 posts/account | Starter plan only |
| Instagram | 50 posts/day/account | Hard 24-hour limit |
| Pinterest | 10 pins/day/account | Requires validation: help@blotato.com |
| YouTube | Variable by age | New channels have low quota |

## Troubleshooting Steps

### General Connection
1. Incognito Chrome browser
2. Log out of all other accounts
3. Log into target social account only
4. Log into Blotato
5. Connect account

### API Issues
1. Check https://my.blotato.com/failed
2. Verify API keys (no spaces)
3. Check AI credits
4. Validate JSON at jsonlint.com
5. Compare with API docs

### Account Health
1. Warm up new accounts manually for several days
2. Post organically before connecting to Blotato
3. Stay active (reply, engage)
4. Don't exceed platform limits
5. Use platform-appropriate formats
