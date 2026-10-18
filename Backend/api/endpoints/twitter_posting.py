"""
Twitter Posting API
===================
API endpoints for Twitter/X posting with full selector control.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/twitter", tags=["Twitter Posting"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class TweetRequest(BaseModel):
    text: str
    media_paths: Optional[List[str]] = None
    
class ThreadRequest(BaseModel):
    tweets: List[str]
    
class ReplyRequest(BaseModel):
    tweet_url: str
    text: str
    media_paths: Optional[List[str]] = None

class PollRequest(BaseModel):
    text: str
    options: List[str]
    duration_days: int = 1

class ScheduleRequest(BaseModel):
    text: str
    schedule_time: str  # ISO format
    media_paths: Optional[List[str]] = None

class DMRequest(BaseModel):
    username: str
    message: str

class SelectorUpdateRequest(BaseModel):
    category: str  # compose, feed, reply, etc.
    selector_name: str
    selectors: List[str]


# =============================================================================
# HELPER
# =============================================================================

def get_poster():
    from automation.safari_twitter_poster import SafariTwitterPoster
    return SafariTwitterPoster()


# =============================================================================
# STATUS / LOGIN
# =============================================================================

@router.get("/status")
async def get_twitter_status():
    """Check Twitter login status and readiness."""
    try:
        poster = get_poster()
        
        # Navigate to Twitter first
        poster.open_twitter()
        
        # Check login
        login_status = poster.check_login_status()
        
        return {
            "success": True,
            "logged_in": login_status.get("logged_in", False),
            "username": login_status.get("username", ""),
            "indicator": login_status.get("indicator", ""),
            "reason": login_status.get("reason", ""),
        }
    except Exception as e:
        logger.error(f"Failed to check Twitter status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/login/verify")
async def verify_twitter_login():
    """Navigate to Twitter and verify login status."""
    try:
        poster = get_poster()
        
        if not poster.open_twitter():
            return {"success": False, "error": "Failed to open Twitter"}
        
        login_status = poster.check_login_status()
        
        return {
            "success": True,
            "logged_in": login_status.get("logged_in", False),
            "details": login_status
        }
    except Exception as e:
        logger.error(f"Failed to verify login: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# POSTING ENDPOINTS
# =============================================================================

@router.post("/post")
async def post_tweet(request: TweetRequest):
    """Post a single tweet."""
    try:
        poster = get_poster()
        result = poster.post_tweet(request.text, request.media_paths)
        
        return {
            "success": result.get("success", False),
            "tweet_url": result.get("url"),
            "tweet_id": result.get("tweet_id"),
            "error": result.get("error"),
            "method": result.get("method", "safari_automation")
        }
    except Exception as e:
        logger.error(f"Failed to post tweet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/thread")
async def post_thread(request: ThreadRequest):
    """Post a Twitter thread."""
    try:
        poster = get_poster()
        result = poster.post_thread(request.tweets)
        
        return {
            "success": result.get("success", False),
            "thread_id": result.get("thread_id"),
            "tweet_urls": result.get("tweet_urls", []),
            "tweets_posted": result.get("tweets_posted", 0),
            "error": result.get("error")
        }
    except Exception as e:
        logger.error(f"Failed to post thread: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reply")
async def reply_to_tweet(request: ReplyRequest):
    """Reply to a specific tweet."""
    try:
        poster = get_poster()
        result = poster.reply_to_tweet(
            request.tweet_url, 
            request.text, 
            request.media_paths
        )
        
        return {
            "success": result.get("success", False),
            "reply_url": result.get("url"),
            "reply_id": result.get("tweet_id"),
            "original_url": request.tweet_url,
            "error": result.get("error")
        }
    except Exception as e:
        logger.error(f"Failed to reply: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/poll")
async def create_poll(request: PollRequest):
    """Create a tweet with a poll."""
    try:
        if len(request.options) < 2 or len(request.options) > 4:
            raise HTTPException(status_code=400, detail="Poll must have 2-4 options")
        
        poster = get_poster()
        result = poster.create_poll(
            request.text,
            request.options,
            request.duration_days
        )
        
        return {
            "success": result.get("success", False),
            "tweet_url": result.get("tweet_url"),
            "tweet_id": result.get("tweet_id"),
            "poll_options": request.options,
            "error": result.get("error")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create poll: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/schedule")
async def schedule_tweet(request: ScheduleRequest):
    """Schedule a tweet for later."""
    try:
        poster = get_poster()
        result = poster.schedule_tweet(
            request.text,
            request.schedule_time,
            request.media_paths
        )
        
        return {
            "success": result.get("success", False),
            "scheduled": result.get("scheduled", False),
            "scheduled_time": request.schedule_time,
            "error": result.get("error")
        }
    except Exception as e:
        logger.error(f"Failed to schedule tweet: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# NOTIFICATIONS
# =============================================================================

@router.get("/notifications")
async def get_notifications(limit: int = 20, mentions_only: bool = False):
    """Get Twitter notifications."""
    try:
        from automation.safari_twitter_poster import TwitterNotifications
        notifications = TwitterNotifications()
        result = notifications.get_notifications(limit=limit, mentions_only=mentions_only)
        
        return {
            "success": result.get("success", False),
            "count": result.get("count", 0),
            "notifications": result.get("notifications", []),
            "error": result.get("error")
        }
    except Exception as e:
        logger.error(f"Failed to get notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications/unread")
async def get_unread_count():
    """Get unread notification count."""
    try:
        from automation.safari_twitter_poster import TwitterNotifications
        notifications = TwitterNotifications()
        result = notifications.get_unread_count()
        
        return {
            "success": True,
            "unread_count": result.get("unread_count", 0)
        }
    except Exception as e:
        logger.error(f"Failed to get unread count: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DIRECT MESSAGES
# =============================================================================

@router.get("/dm/conversations")
async def get_dm_conversations(limit: int = 20):
    """Get DM conversations."""
    try:
        from automation.safari_twitter_poster import TwitterDM
        dm = TwitterDM()
        result = dm.get_conversations(limit=limit)
        
        return {
            "success": result.get("success", False),
            "count": result.get("count", 0),
            "unread_count": result.get("unread_count", 0),
            "conversations": result.get("conversations", []),
            "error": result.get("error")
        }
    except Exception as e:
        logger.error(f"Failed to get conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dm/{username}")
async def read_dm_conversation(username: str, limit: int = 50):
    """Read messages from a specific user."""
    try:
        from automation.safari_twitter_poster import TwitterDM
        dm = TwitterDM()
        
        if not dm.open_conversation(username):
            raise HTTPException(status_code=404, detail=f"Could not open conversation with @{username}")
        
        result = dm.read_messages(limit=limit)
        
        return {
            "success": result.get("success", False),
            "username": username,
            "count": result.get("count", 0),
            "messages": result.get("messages", []),
            "error": result.get("error")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read DMs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dm/send")
async def send_dm(request: DMRequest):
    """Send a direct message."""
    try:
        from automation.safari_twitter_poster import TwitterDM
        dm = TwitterDM()
        result = dm.send_message(request.message, request.username)
        
        return {
            "success": result.get("success", False),
            "username": request.username,
            "error": result.get("error")
        }
    except Exception as e:
        logger.error(f"Failed to send DM: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# SELECTOR MANAGEMENT
# =============================================================================

@router.get("/selectors")
async def get_all_selectors():
    """Get all Twitter selectors configuration."""
    try:
        from config.twitter_selectors import get_all_selectors
        return {
            "success": True,
            "selectors": get_all_selectors()
        }
    except Exception as e:
        logger.error(f"Failed to get selectors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/selectors/{category}")
async def get_category_selectors(category: str):
    """Get selectors for a specific category."""
    try:
        from config.twitter_selectors import get_all_selectors
        all_selectors = get_all_selectors()
        
        if category not in all_selectors:
            raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
        
        return {
            "success": True,
            "category": category,
            "selectors": all_selectors[category]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get category selectors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/selectors/test")
async def test_selector(selector: str):
    """Test a selector against the current Twitter page."""
    try:
        poster = get_poster()
        
        # Execute JS to test selector
        escaped = selector.replace('"', '\\"').replace("'", "\\'")
        script = f'''
        tell application "Safari"
            tell window 1
                tell current tab
                    do JavaScript "
                        (function() {{
                            var el = document.querySelector(\\"{escaped}\\");
                            if (el) {{
                                return JSON.stringify({{
                                    found: true,
                                    tagName: el.tagName,
                                    text: (el.innerText || '').substring(0, 100),
                                    classes: el.className,
                                    id: el.id
                                }});
                            }}
                            return JSON.stringify({{found: false}});
                        }})();
                    "
                end tell
            end tell
        end tell
        '''
        
        import subprocess
        result = subprocess.run(
            ['osascript', '-e', script],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            import json
            data = json.loads(result.stdout.strip())
            return {
                "success": True,
                "selector": selector,
                "result": data
            }
        else:
            return {
                "success": False,
                "selector": selector,
                "error": result.stderr
            }
            
    except Exception as e:
        logger.error(f"Failed to test selector: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@router.post("/open/compose")
async def open_compose():
    """Open the Twitter compose modal."""
    try:
        poster = get_poster()
        success = poster.open_compose()
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to open compose: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/open/home")
async def open_home():
    """Open Twitter home page."""
    try:
        poster = get_poster()
        success = poster.open_twitter()
        return {"success": success}
    except Exception as e:
        logger.error(f"Failed to open home: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/url")
async def get_current_url():
    """Get current Safari URL."""
    try:
        poster = get_poster()
        url = poster.get_current_url()
        return {"success": True, "url": url}
    except Exception as e:
        logger.error(f"Failed to get URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))
