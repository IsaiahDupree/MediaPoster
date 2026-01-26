"""
Twitter/X Selectors Configuration
=================================
Centralized selectors for Twitter/X Safari automation.
Update these when Twitter changes their DOM structure.

Last updated: 2026-01-25
"""

from typing import Dict, List

# =============================================================================
# LOGIN DETECTION SELECTORS
# =============================================================================

LOGIN_INDICATORS = {
    "logged_in": [
        '[data-testid="AppTabBar_Profile_Link"]',
        '[data-testid="SideNav_NewTweet_Button"]',
        'a[href="/compose/post"]',
        'a[href="/compose/tweet"]',
        '[aria-label="Profile"]',
        '[data-testid="primaryColumn"]',
        '[data-testid="tweetTextarea_0"]',
    ],
    "logged_out": [
        'a[href="/login"]',
        'a[href="/i/flow/login"]',
        '[data-testid="loginButton"]',
        'a[href="/i/flow/signup"]',
    ],
    "login_page_urls": [
        "/login",
        "/i/flow/login",
        "/i/flow/signup",
    ]
}

# =============================================================================
# COMPOSE / POST CREATION SELECTORS
# =============================================================================

COMPOSE_SELECTORS = {
    # Tweet text input
    "textarea": [
        '[data-testid="tweetTextarea_0"]',
        '[role="textbox"][data-testid*="tweetTextarea"]',
        '.public-DraftEditor-content',
        '[contenteditable="true"]',
        '[data-testid="tweetTextarea_0RichTextInputContainer"]',
    ],
    
    # Post/Tweet button
    "post_button": [
        '[data-testid="tweetButton"]',
        '[data-testid="tweetButtonInline"]',
        'button[data-testid="tweetButton"]',
    ],
    "post_button_text": ["Post", "Tweet"],
    
    # Media attachment
    "media_button": [
        '[aria-label="Add photos or video"]',
        '[data-testid="fileInput"]',
        'input[type="file"][accept*="image"]',
        '[aria-label="Media"]',
    ],
    
    # GIF button
    "gif_button": [
        '[aria-label="Add a GIF"]',
        '[data-testid="gifSearchButton"]',
    ],
    
    # Poll button
    "poll_button": [
        '[data-testid="createPollButton"]',
        '[aria-label="Add poll"]',
    ],
    
    # Schedule button
    "schedule_button": [
        '[data-testid="scheduleOption"]',
        '[aria-label="Schedule post"]',
        '[aria-label="Schedule"]',
    ],
    
    # Emoji button
    "emoji_button": [
        '[aria-label="Add emoji"]',
        '[data-testid="emojiButton"]',
    ],
    
    # Location button
    "location_button": [
        '[aria-label="Add location"]',
        '[data-testid="geoButton"]',
    ],
}

# =============================================================================
# FEED / TIMELINE SELECTORS
# =============================================================================

FEED_SELECTORS = {
    # Individual tweets in feed
    "tweet_article": [
        'article[data-testid="tweet"]',
        'article[role="article"]',
        '[data-testid="cellInnerDiv"] article',
    ],
    
    # Tweet text content
    "tweet_text": [
        '[data-testid="tweetText"]',
        '[lang]',
    ],
    
    # Tweet link (to status page)
    "tweet_link": [
        'a[href*="/status/"]',
        'time[datetime]',
    ],
    
    # User info
    "user_link": [
        'a[href^="/"][role="link"]',
    ],
    
    # Engagement buttons
    "like_button": [
        '[data-testid="like"]',
        '[aria-label*="Like"]',
    ],
    "retweet_button": [
        '[data-testid="retweet"]',
        '[aria-label*="Repost"]',
        '[aria-label*="Retweet"]',
    ],
    "reply_button": [
        '[data-testid="reply"]',
        '[aria-label*="Reply"]',
    ],
    "share_button": [
        '[data-testid="share"]',
        '[aria-label*="Share"]',
    ],
    "bookmark_button": [
        '[data-testid="bookmark"]',
        '[aria-label*="Bookmark"]',
    ],
}

# =============================================================================
# REPLY SELECTORS
# =============================================================================

REPLY_SELECTORS = {
    # Reply textarea (on tweet detail page)
    "reply_textarea": [
        '[data-testid="tweetTextarea_0"]',
        '[aria-label="Post your reply"]',
        '[placeholder*="Post your reply"]',
    ],
    
    # Reply button
    "reply_submit": [
        '[data-testid="tweetButton"]',
        '[data-testid="tweetButtonInline"]',
    ],
}

# =============================================================================
# NOTIFICATION SELECTORS
# =============================================================================

NOTIFICATION_SELECTORS = {
    # Notification items
    "notification_item": [
        '[data-testid="notification"]',
        'article[data-testid="notification"]',
        '[data-testid="cellInnerDiv"]',
    ],
    
    # Unread badge
    "unread_badge": [
        '[data-testid="notificationIndicator"]',
        '[aria-label*="unread"]',
    ],
    
    # Notification tabs
    "all_tab": '[role="tab"][href="/notifications"]',
    "mentions_tab": '[role="tab"][href="/notifications/mentions"]',
}

# =============================================================================
# DM SELECTORS
# =============================================================================

DM_SELECTORS = {
    # Conversation list
    "conversation_item": [
        '[data-testid="conversation"]',
        '[data-testid="DMConversationEntry"]',
    ],
    
    # Message input
    "message_input": [
        '[data-testid="dmComposerTextInput"]',
        '[aria-label="Start a new message"]',
        '[placeholder*="Start a new message"]',
    ],
    
    # Send button
    "send_button": [
        '[data-testid="dmComposerSendButton"]',
        '[aria-label="Send"]',
    ],
    
    # Message bubbles
    "message_bubble": [
        '[data-testid="messageEntry"]',
        '[data-testid="DM_message"]',
    ],
}

# =============================================================================
# PROFILE SELECTORS
# =============================================================================

PROFILE_SELECTORS = {
    # Profile link in nav
    "profile_nav_link": [
        '[data-testid="AppTabBar_Profile_Link"]',
    ],
    
    # Profile header
    "profile_header": [
        '[data-testid="UserName"]',
        '[data-testid="UserProfileHeader_Items"]',
    ],
    
    # Follow button
    "follow_button": [
        '[data-testid="followButton"]',
        '[aria-label*="Follow"]',
    ],
    
    # Following button (already following)
    "following_button": [
        '[data-testid="unfollowButton"]',
        '[aria-label*="Following"]',
    ],
}

# =============================================================================
# TOAST / ALERT SELECTORS
# =============================================================================

FEEDBACK_SELECTORS = {
    "toast": [
        '[data-testid="toast"]',
        '[role="alert"]',
    ],
    "error_banner": [
        '[role="alert"]',
        '[data-testid="error"]',
    ],
}

# =============================================================================
# URL PATTERNS
# =============================================================================

URL_PATTERNS = {
    "compose": "https://x.com/compose/post",
    "compose_legacy": "https://twitter.com/compose/tweet",
    "home": "https://x.com/home",
    "home_legacy": "https://twitter.com/home",
    "notifications": "https://x.com/notifications",
    "messages": "https://x.com/messages",
    "profile": "https://x.com/{username}",
    "status": "https://x.com/{username}/status/{tweet_id}",
    "intent_post": "https://x.com/intent/post",
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_selector_chain(selector_list: List[str]) -> str:
    """
    Convert a list of selectors into a JavaScript selector chain.
    Returns the first matching element.
    """
    checks = []
    for sel in selector_list:
        checks.append(f'document.querySelector("{sel}")')
    return " || ".join(checks)


def generate_find_element_js(selector_list: List[str], var_name: str = "el") -> str:
    """
    Generate JavaScript to find an element using multiple selectors.
    """
    lines = [f"var {var_name} = null;"]
    for sel in selector_list:
        escaped = sel.replace('"', '\\"')
        lines.append(f'if (!{var_name}) {var_name} = document.querySelector("{escaped}");')
    return "\n".join(lines)


def get_all_selectors() -> Dict:
    """Return all selector configurations."""
    return {
        "login": LOGIN_INDICATORS,
        "compose": COMPOSE_SELECTORS,
        "feed": FEED_SELECTORS,
        "reply": REPLY_SELECTORS,
        "notifications": NOTIFICATION_SELECTORS,
        "dm": DM_SELECTORS,
        "profile": PROFILE_SELECTORS,
        "feedback": FEEDBACK_SELECTORS,
        "urls": URL_PATTERNS,
    }


# =============================================================================
# SELECTOR UPDATE LOG
# =============================================================================

SELECTOR_CHANGELOG = """
2026-01-25: Initial extraction from safari_twitter_poster.py
- Extracted all selectors into centralized config
- Added fallback selectors for reliability
- Added helper functions for JS generation

To update selectors:
1. Inspect Twitter/X DOM in Safari Developer Tools
2. Update the relevant selector list
3. Test with: python -c "from config.twitter_selectors import *; print(get_all_selectors())"
"""
