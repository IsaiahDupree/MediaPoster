"""
Strategic Analysis Service (Cross-Platform Intelligence)
=========================================================
Pub/sub service that collects analytics from all connected platforms,
runs AI-driven strategic analysis, and publishes actionable recommendations.

Topics Published:
    - strategy.analysis.requested        → Trigger a full analysis run
    - strategy.data_collection.started   → Pulling stats from APIs
    - strategy.platform.data_ready       → One platform's data fetched
    - strategy.data_collection.completed → All platform data collected
    - strategy.ai_analysis.started       → AI processing raw data
    - strategy.ai_analysis.completed     → AI strategy generated
    - strategy.recommendations.ready     → Actionable recommendations available
    - strategy.cadence.updated           → Posting cadence changed
    - strategy.report.ready              → Full report available
    - strategy.analysis.failed           → Analysis pipeline error

Topics Subscribed:
    - strategy.analysis.requested        → Kicks off a full analysis run
    - publish.completed                  → Tracks new publishes for cadence tracking
    - metrics.fetch.completed            → Incorporates fresh metrics data

Usage:
    from services.strategic_analysis_service import get_strategic_analysis_service

    service = get_strategic_analysis_service()
    await service.start()

    # Trigger via event bus
    await bus.publish(Topics.STRATEGY_ANALYSIS_REQUESTED, {"platforms": ["youtube", "tiktok", "instagram"]})

    # Or call directly
    report = await service.run_full_analysis()
"""

import asyncio
import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

import httpx
from openai import AsyncOpenAI

from services.event_bus import EventBus, Event, Topics

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class PlatformSnapshot:
    """Raw analytics snapshot for a single platform account"""
    platform: str
    account_username: str
    account_id: Optional[str] = None
    followers: int = 0
    following: int = 0
    total_posts: int = 0
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    total_saves: int = 0
    avg_views_per_post: float = 0.0
    engagement_rate: float = 0.0
    top_posts: List[Dict[str, Any]] = field(default_factory=list)
    posting_timeline: Dict[str, Any] = field(default_factory=dict)
    content_mix: Dict[str, int] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    fetched_at: str = ""
    error: Optional[str] = None


@dataclass
class StrategicReport:
    """Full cross-platform strategic analysis report"""
    correlation_id: str
    platform_snapshots: Dict[str, PlatformSnapshot] = field(default_factory=dict)
    ai_analysis: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    cadence: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    status: str = "pending"

    def to_dict(self) -> Dict[str, Any]:
        snapshots = {}
        for k, v in self.platform_snapshots.items():
            snapshots[k] = {
                "platform": v.platform,
                "account_username": v.account_username,
                "followers": v.followers,
                "total_posts": v.total_posts,
                "total_views": v.total_views,
                "total_likes": v.total_likes,
                "total_comments": v.total_comments,
                "total_shares": v.total_shares,
                "avg_views_per_post": v.avg_views_per_post,
                "engagement_rate": v.engagement_rate,
                "top_posts": v.top_posts,
                "content_mix": v.content_mix,
                "posting_timeline": v.posting_timeline,
                "error": v.error,
            }
        return {
            "correlation_id": self.correlation_id,
            "platform_snapshots": snapshots,
            "ai_analysis": self.ai_analysis,
            "recommendations": self.recommendations,
            "cadence": self.cadence,
            "created_at": self.created_at,
            "status": self.status,
        }


# =============================================================================
# PLATFORM DATA COLLECTORS
# =============================================================================

class YouTubeCollector:
    """Collects YouTube channel and video analytics via YouTube Data API v3"""

    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.channel_id = os.getenv("YOUTUBE_CHANNEL_ID")
        self.API_BASE = "https://www.googleapis.com/youtube/v3"

    async def collect(self) -> PlatformSnapshot:
        snapshot = PlatformSnapshot(platform="youtube", account_username="@isaiah_dupree")
        snapshot.fetched_at = datetime.now(timezone.utc).isoformat()

        if not self.api_key or not self.channel_id:
            snapshot.error = "YOUTUBE_API_KEY or YOUTUBE_CHANNEL_ID not configured"
            return snapshot

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Channel metrics
                ch_resp = await client.get(f"{self.API_BASE}/channels", params={
                    "part": "snippet,statistics", "id": self.channel_id, "key": self.api_key
                })
                if ch_resp.status_code == 200:
                    items = ch_resp.json().get("items", [])
                    if items:
                        stats = items[0].get("statistics", {})
                        snippet = items[0].get("snippet", {})
                        snapshot.followers = int(stats.get("subscriberCount", 0))
                        snapshot.total_posts = int(stats.get("videoCount", 0))
                        snapshot.total_views = int(stats.get("viewCount", 0))
                        snapshot.account_username = snippet.get("customUrl", snapshot.account_username)

                # Recent videos via search
                search_resp = await client.get(f"{self.API_BASE}/search", params={
                    "part": "id", "channelId": self.channel_id, "type": "video",
                    "order": "date", "maxResults": 50, "key": self.api_key
                })
                if search_resp.status_code != 200:
                    return snapshot

                video_ids = [i["id"]["videoId"] for i in search_resp.json().get("items", [])]
                if not video_ids:
                    return snapshot

                # Video details
                vid_resp = await client.get(f"{self.API_BASE}/videos", params={
                    "part": "snippet,statistics,contentDetails",
                    "id": ",".join(video_ids), "key": self.api_key
                })
                if vid_resp.status_code != 200:
                    return snapshot

                videos = vid_resp.json().get("items", [])
                shorts_count = 0
                longform_count = 0
                recent_views = 0
                recent_likes = 0
                recent_comments = 0
                top_posts = []
                timeline = {}

                for v in videos:
                    s = v.get("statistics", {})
                    c = v.get("contentDetails", {})
                    sn = v.get("snippet", {})
                    dur = self._parse_duration(c.get("duration", "PT0S"))
                    views = int(s.get("viewCount", 0))
                    likes = int(s.get("likeCount", 0))
                    comments = int(s.get("commentCount", 0))
                    is_short = dur <= 60
                    date = sn.get("publishedAt", "")[:10]

                    if is_short:
                        shorts_count += 1
                    else:
                        longform_count += 1

                    recent_views += views
                    recent_likes += likes
                    recent_comments += comments

                    timeline.setdefault(date, {"count": 0, "views": 0})
                    timeline[date]["count"] += 1
                    timeline[date]["views"] += views

                    top_posts.append({
                        "title": sn.get("title", ""),
                        "views": views, "likes": likes, "comments": comments,
                        "is_short": is_short, "duration_seconds": dur,
                        "date": date,
                    })

                top_posts.sort(key=lambda x: x["views"], reverse=True)
                snapshot.top_posts = top_posts[:10]
                snapshot.total_likes = recent_likes
                snapshot.total_comments = recent_comments
                snapshot.content_mix = {"shorts": shorts_count, "longform": longform_count}
                snapshot.posting_timeline = timeline
                snapshot.avg_views_per_post = recent_views / len(videos) if videos else 0
                snapshot.engagement_rate = (recent_likes + recent_comments) / recent_views if recent_views else 0
                snapshot.raw_data = {"recent_video_count": len(videos), "recent_total_views": recent_views}

        except Exception as e:
            snapshot.error = str(e)
            logger.error(f"YouTube collection error: {e}")

        return snapshot

    @staticmethod
    def _parse_duration(iso: str) -> int:
        import re
        m = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', iso)
        if not m:
            return 0
        return int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)


class TikTokCollector:
    """Collects TikTok analytics via RapidAPI tiktok-scraper7"""

    def __init__(self):
        self.api_key = os.getenv("RAPIDAPI_KEY")
        self.host = "tiktok-scraper7.p.rapidapi.com"

    async def collect(self, username: str = "isaiah_dupree") -> PlatformSnapshot:
        snapshot = PlatformSnapshot(platform="tiktok", account_username=f"@{username}")
        snapshot.fetched_at = datetime.now(timezone.utc).isoformat()

        if not self.api_key:
            snapshot.error = "RAPIDAPI_KEY not configured"
            return snapshot

        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": self.host}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Profile
                profile_resp = await client.get(
                    f"https://{self.host}/user/info",
                    headers=headers, params={"unique_id": username}
                )
                if profile_resp.status_code == 200:
                    data = profile_resp.json().get("data", {})
                    stats = data.get("stats", {})
                    snapshot.followers = stats.get("followerCount", 0)
                    snapshot.following = stats.get("followingCount", 0)
                    snapshot.total_likes = stats.get("heartCount", 0)
                    snapshot.total_posts = stats.get("videoCount", 0)

                # Recent posts
                await asyncio.sleep(0.5)
                posts_resp = await client.get(
                    f"https://{self.host}/user/posts",
                    headers=headers, params={"unique_id": username, "count": 30}
                )
                if posts_resp.status_code != 200:
                    return snapshot

                videos = posts_resp.json().get("data", {}).get("videos", [])
                total_views = 0
                total_likes = 0
                total_comments = 0
                total_shares = 0
                total_saves = 0
                top_posts = []
                timeline = {}

                for v in videos:
                    views = v.get("play_count", 0)
                    likes = v.get("digg_count", 0)
                    comments = v.get("comment_count", 0)
                    shares = v.get("share_count", 0)
                    saves = v.get("collect_count", 0)
                    dur = v.get("duration", 0)
                    ct = v.get("create_time", 0)
                    date = datetime.fromtimestamp(int(ct)).strftime("%Y-%m-%d") if ct else "unknown"
                    desc_raw = v.get("content_desc", v.get("title", ""))
                    desc = " ".join(desc_raw) if isinstance(desc_raw, list) else str(desc_raw)

                    total_views += views
                    total_likes += likes
                    total_comments += comments
                    total_shares += shares
                    total_saves += saves

                    month = date[:7]
                    timeline.setdefault(month, {"count": 0, "views": 0})
                    timeline[month]["count"] += 1
                    timeline[month]["views"] += views

                    top_posts.append({
                        "title": desc[:80], "views": views, "likes": likes,
                        "comments": comments, "shares": shares, "saves": saves,
                        "duration_seconds": dur, "date": date,
                    })

                top_posts.sort(key=lambda x: x["views"], reverse=True)
                snapshot.top_posts = top_posts[:10]
                snapshot.total_comments = total_comments
                snapshot.total_shares = total_shares
                snapshot.total_saves = total_saves
                snapshot.posting_timeline = timeline
                snapshot.avg_views_per_post = total_views / len(videos) if videos else 0
                snapshot.engagement_rate = (
                    (total_likes + total_comments + total_shares) / total_views
                    if total_views else 0
                )
                snapshot.content_mix = {"short_form": len(videos)}
                snapshot.raw_data = {
                    "recent_video_count": len(videos),
                    "recent_total_views": total_views,
                    "recent_total_likes": total_likes,
                }

        except Exception as e:
            snapshot.error = str(e)
            logger.error(f"TikTok collection error: {e}")

        return snapshot


class InstagramCollector:
    """Collects Instagram analytics via RapidAPI instagram-looter2 (public data)"""

    def __init__(self):
        self.api_key = os.getenv("RAPIDAPI_KEY")
        self.host = "instagram-looter2.p.rapidapi.com"

    async def collect(self, username: str = "the_isaiah_dupree") -> PlatformSnapshot:
        snapshot = PlatformSnapshot(platform="instagram", account_username=f"@{username}")
        snapshot.fetched_at = datetime.now(timezone.utc).isoformat()

        if not self.api_key:
            snapshot.error = "RAPIDAPI_KEY not configured"
            return snapshot

        headers = {"X-RapidAPI-Key": self.api_key, "X-RapidAPI-Host": self.host}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"https://{self.host}/profile",
                    headers=headers, params={"username": username}
                )
                if resp.status_code != 200:
                    snapshot.error = f"Instagram API error: {resp.status_code}"
                    return snapshot

                data = resp.json()
                user = data.get("data", data)

                snapshot.followers = user.get("edge_followed_by", {}).get("count", 0)
                snapshot.following = user.get("edge_follow", {}).get("count", 0)
                snapshot.total_posts = user.get("edge_owner_to_timeline_media", {}).get("count", 0)
                snapshot.raw_data = {
                    "is_verified": user.get("is_verified", False),
                    "is_business": user.get("is_business_account", False),
                    "biography": (user.get("biography") or "")[:200],
                }

        except Exception as e:
            snapshot.error = str(e)
            logger.error(f"Instagram collection error: {e}")

        return snapshot


class InstagramGraphCollector:
    """Collects Instagram insights via the Instagram Graph API (graph.instagram.com).

    Uses an IGAA-prefixed Instagram token for direct access to:
        - Account profile (followers, media count, bio)
        - Account-level insights (reach, profile_views per day)
        - Per-media insights (likes, comments, shares, saves, total_interactions)

    Falls back to META_ACCESS_TOKEN via Facebook Page discovery if IGAA token
    is not available.

    Env vars (checked in order):
        1. INSTAGRAM_GRAPH_TOKEN  (IGAA token — uses graph.instagram.com)
        2. META_ACCESS_TOKEN      (EAA token — uses graph.facebook.com/me/accounts)
    """

    IG_BASE = "https://graph.instagram.com/v21.0"
    FB_BASE = "https://graph.facebook.com/v21.0"

    def __init__(self):
        self.ig_token = os.getenv("INSTAGRAM_GRAPH_TOKEN")
        self.fb_token = os.getenv("META_ACCESS_TOKEN")
        self.ig_account_id = os.getenv("INSTAGRAM_GRAPH_ACCOUNT_ID") or os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")

    async def collect(self) -> PlatformSnapshot:
        snapshot = PlatformSnapshot(
            platform="instagram_graph",
            account_username="@the_isaiah_dupree (Graph API)",
            account_id=self.ig_account_id,
        )
        snapshot.fetched_at = datetime.now(timezone.utc).isoformat()

        if self.ig_token:
            return await self._collect_via_ig_api(snapshot)
        elif self.fb_token:
            return await self._collect_via_fb_page(snapshot)
        else:
            snapshot.error = "No INSTAGRAM_GRAPH_TOKEN or META_ACCESS_TOKEN configured"
            return snapshot

    async def _collect_via_ig_api(self, snapshot: PlatformSnapshot) -> PlatformSnapshot:
        """Primary path: IGAA token → graph.instagram.com"""
        params = {"access_token": self.ig_token}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # --- Profile ---
                profile_resp = await client.get(
                    f"{self.IG_BASE}/me",
                    params={**params, "fields": "id,username,name,account_type,media_count,followers_count,follows_count,biography"},
                )
                if profile_resp.status_code != 200:
                    err = profile_resp.json().get("error", {}).get("message", profile_resp.text[:200])
                    snapshot.error = f"IG Graph API error: {err}"
                    return snapshot

                profile = profile_resp.json()
                snapshot.account_username = f"@{profile.get('username', 'unknown')}"
                snapshot.account_id = profile.get("id", self.ig_account_id)
                snapshot.followers = profile.get("followers_count", 0)
                snapshot.following = profile.get("follows_count", 0)
                snapshot.total_posts = profile.get("media_count", 0)
                snapshot.raw_data["biography"] = (profile.get("biography") or "")[:200]
                snapshot.raw_data["name"] = profile.get("name", "")
                snapshot.raw_data["account_type"] = profile.get("account_type", "")
                snapshot.raw_data["token_type"] = "IGAA"

                ig_id = profile.get("id", self.ig_account_id)

                # --- Account-level insights (28-day) ---
                for metric in ("reach", "profile_views", "accounts_engaged", "total_interactions"):
                    ins_resp = await client.get(
                        f"{self.IG_BASE}/{ig_id}/insights",
                        params={**params, "metric": metric, "period": "day"},
                    )
                    if ins_resp.status_code == 200:
                        data = ins_resp.json().get("data", [])
                        if data:
                            vals = data[0].get("values", [])
                            total = sum(v.get("value", 0) for v in vals[-28:])
                            snapshot.raw_data[f"28d_{metric}"] = total

                # --- Recent media with per-post insights ---
                media_resp = await client.get(
                    f"{self.IG_BASE}/me/media",
                    params={
                        **params,
                        "fields": "id,caption,media_type,media_product_type,timestamp,like_count,comments_count,permalink",
                        "limit": 25,
                    },
                )
                if media_resp.status_code != 200:
                    return snapshot

                media_items = media_resp.json().get("data", [])
                total_likes = 0
                total_comments = 0
                total_shares = 0
                total_saves = 0
                total_interactions = 0
                top_posts = []
                timeline = {}

                for item in media_items:
                    likes = item.get("like_count", 0)
                    comments = item.get("comments_count", 0)
                    ts = item.get("timestamp", "")[:10]
                    media_type = item.get("media_type", "UNKNOWN")
                    product_type = item.get("media_product_type", "")
                    caption = (item.get("caption") or "")[:80]

                    total_likes += likes
                    total_comments += comments

                    # Per-media insights
                    shares = 0
                    saves = 0
                    interactions = 0
                    media_id = item.get("id")
                    if media_id:
                        ins_resp = await client.get(
                            f"{self.IG_BASE}/{media_id}/insights",
                            params={**params, "metric": "likes,comments,shares,saved,total_interactions"},
                        )
                        if ins_resp.status_code == 200:
                            for m in ins_resp.json().get("data", []):
                                val = m.get("values", [{}])[0].get("value", 0)
                                if m["name"] == "shares":
                                    shares = val
                                elif m["name"] == "saved":
                                    saves = val
                                elif m["name"] == "total_interactions":
                                    interactions = val
                            total_shares += shares
                            total_saves += saves
                            total_interactions += interactions

                    month = ts[:7]
                    timeline.setdefault(month, {"count": 0, "likes": 0, "shares": 0, "saves": 0})
                    timeline[month]["count"] += 1
                    timeline[month]["likes"] += likes
                    timeline[month]["shares"] += shares
                    timeline[month]["saves"] += saves

                    top_posts.append({
                        "title": caption, "likes": likes, "comments": comments,
                        "shares": shares, "saves": saves,
                        "total_interactions": interactions,
                        "media_type": media_type, "product_type": product_type,
                        "date": ts, "permalink": item.get("permalink", ""),
                    })

                top_posts.sort(key=lambda x: x.get("total_interactions", 0), reverse=True)
                snapshot.top_posts = top_posts[:10]
                snapshot.total_likes = total_likes
                snapshot.total_comments = total_comments
                snapshot.total_shares = total_shares
                snapshot.total_saves = total_saves
                snapshot.posting_timeline = timeline
                snapshot.content_mix = {
                    t: sum(1 for p in top_posts if p["media_type"] == t)
                    for t in {p["media_type"] for p in top_posts}
                }
                snapshot.engagement_rate = (
                    total_interactions / (snapshot.followers * len(media_items))
                    if snapshot.followers and media_items else 0
                )
                snapshot.raw_data["total_interactions_25_posts"] = total_interactions
                snapshot.raw_data["total_shares_25_posts"] = total_shares
                snapshot.raw_data["total_saves_25_posts"] = total_saves

        except Exception as e:
            snapshot.error = str(e)
            logger.error(f"Instagram Graph API (IGAA) collection error: {e}")

        return snapshot

    async def _collect_via_fb_page(self, snapshot: PlatformSnapshot) -> PlatformSnapshot:
        """Fallback path: EAA token → graph.facebook.com/me/accounts → IG business account"""
        params = {"access_token": self.fb_token}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                pages_resp = await client.get(
                    f"{self.FB_BASE}/me/accounts",
                    params={
                        **params,
                        "fields": "id,name,instagram_business_account{id,username,followers_count,follows_count,media_count,biography,name}",
                    },
                )
                if pages_resp.status_code == 200:
                    for page in pages_resp.json().get("data", []):
                        ig_biz = page.get("instagram_business_account")
                        if ig_biz:
                            snapshot.account_username = f"@{ig_biz.get('username', 'unknown')}"
                            snapshot.account_id = ig_biz.get("id")
                            snapshot.followers = ig_biz.get("followers_count", 0)
                            snapshot.following = ig_biz.get("follows_count", 0)
                            snapshot.total_posts = ig_biz.get("media_count", 0)
                            snapshot.raw_data["biography"] = (ig_biz.get("biography") or "")[:200]
                            snapshot.raw_data["name"] = ig_biz.get("name", "")
                            snapshot.raw_data["token_type"] = "EAA (fallback)"
                            snapshot.raw_data["media_access"] = "limited — INSTAGRAM_GRAPH_TOKEN not set"
                            break
                else:
                    snapshot.error = f"FB Page discovery failed: {pages_resp.status_code}"

        except Exception as e:
            snapshot.error = str(e)
            logger.error(f"Instagram Graph API (FB fallback) error: {e}")

        return snapshot


class FacebookAdsCollector:
    """Collects Facebook Ads account data via the Marketing API.

    Requires:
        - META_ACCESS_TOKEN
        - FACEBOOK_AD_ACCOUNT_ID (format: act_XXXXX)

    Returns:
        Campaign-level spend, impressions, clicks, conversions for last 30 days.
    """

    GRAPH_BASE = "https://graph.facebook.com/v21.0"

    def __init__(self):
        self.access_token = os.getenv("META_ACCESS_TOKEN")
        self.ad_account_id = os.getenv("FACEBOOK_AD_ACCOUNT_ID")

    async def collect(self) -> PlatformSnapshot:
        snapshot = PlatformSnapshot(
            platform="facebook_ads",
            account_username=self.ad_account_id or "unknown",
            account_id=self.ad_account_id,
        )
        snapshot.fetched_at = datetime.now(timezone.utc).isoformat()

        if not self.access_token or not self.ad_account_id:
            snapshot.error = "META_ACCESS_TOKEN or FACEBOOK_AD_ACCOUNT_ID not configured"
            return snapshot

        params = {"access_token": self.access_token}

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # --- Ad Account summary ---
                acct_resp = await client.get(
                    f"{self.GRAPH_BASE}/{self.ad_account_id}",
                    params={**params, "fields": "name,account_status,currency,amount_spent,balance"},
                )
                if acct_resp.status_code != 200:
                    err = acct_resp.json().get("error", {}).get("message", acct_resp.text[:200])
                    snapshot.error = f"FB Ads account error: {err}"
                    return snapshot

                acct = acct_resp.json()
                snapshot.raw_data["account_name"] = acct.get("name", "")
                snapshot.raw_data["currency"] = acct.get("currency", "USD")
                snapshot.raw_data["total_amount_spent"] = acct.get("amount_spent", "0")
                snapshot.raw_data["balance"] = acct.get("balance", "0")
                snapshot.raw_data["account_status"] = acct.get("account_status")

                # --- Campaign insights (last 30 days) ---
                insights_resp = await client.get(
                    f"{self.GRAPH_BASE}/{self.ad_account_id}/insights",
                    params={
                        **params,
                        "fields": "campaign_name,impressions,reach,clicks,spend,actions,ctr,cpc,cpm,frequency",
                        "date_preset": "last_30d",
                        "level": "campaign",
                        "limit": 50,
                    },
                )

                campaigns = []
                total_spend = 0.0
                total_impressions = 0
                total_clicks = 0
                total_reach = 0

                if insights_resp.status_code == 200:
                    for row in insights_resp.json().get("data", []):
                        spend = float(row.get("spend", 0))
                        impressions = int(row.get("impressions", 0))
                        clicks = int(row.get("clicks", 0))
                        reach = int(row.get("reach", 0))

                        total_spend += spend
                        total_impressions += impressions
                        total_clicks += clicks
                        total_reach += reach

                        # Extract conversions from actions array
                        actions = row.get("actions", [])
                        conversions = 0
                        for a in actions:
                            if a.get("action_type") in ("lead", "offsite_conversion", "omni_purchase"):
                                conversions += int(a.get("value", 0))

                        campaigns.append({
                            "name": row.get("campaign_name", "Unknown"),
                            "spend": spend,
                            "impressions": impressions,
                            "reach": reach,
                            "clicks": clicks,
                            "ctr": row.get("ctr", "0"),
                            "cpc": row.get("cpc", "0"),
                            "cpm": row.get("cpm", "0"),
                            "conversions": conversions,
                        })
                else:
                    err = insights_resp.json().get("error", {}).get("message", "")
                    snapshot.raw_data["insights_error"] = err

                campaigns.sort(key=lambda c: c["spend"], reverse=True)
                snapshot.top_posts = campaigns[:10]  # Reuse top_posts for top campaigns
                snapshot.total_views = total_impressions
                snapshot.total_likes = total_clicks  # Map clicks → likes field for unified view
                snapshot.raw_data["total_spend_30d"] = round(total_spend, 2)
                snapshot.raw_data["total_impressions_30d"] = total_impressions
                snapshot.raw_data["total_clicks_30d"] = total_clicks
                snapshot.raw_data["total_reach_30d"] = total_reach
                snapshot.raw_data["campaign_count"] = len(campaigns)
                snapshot.raw_data["ctr_30d"] = f"{(total_clicks / total_impressions * 100):.2f}%" if total_impressions else "0%"
                snapshot.avg_views_per_post = total_impressions / len(campaigns) if campaigns else 0
                snapshot.engagement_rate = total_clicks / total_impressions if total_impressions else 0

        except Exception as e:
            snapshot.error = str(e)
            logger.error(f"Facebook Ads collection error: {e}")

        return snapshot


# =============================================================================
# AI STRATEGY ANALYZER
# =============================================================================

class AIStrategyAnalyzer:
    """Uses OpenAI to generate strategic analysis from platform data"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    async def analyze(self, snapshots: Dict[str, PlatformSnapshot]) -> Dict[str, Any]:
        platform_data = {}
        for key, snap in snapshots.items():
            platform_data[key] = {
                "platform": snap.platform,
                "account": snap.account_username,
                "followers": snap.followers,
                "total_posts": snap.total_posts,
                "total_views": snap.total_views,
                "total_likes": snap.total_likes,
                "avg_views_per_post": round(snap.avg_views_per_post, 1),
                "engagement_rate": f"{snap.engagement_rate * 100:.2f}%",
                "top_posts": snap.top_posts[:5],
                "content_mix": snap.content_mix,
                "posting_timeline": snap.posting_timeline,
                "error": snap.error,
            }

        response = await self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a data-driven social media strategist. Analyze cross-platform "
                        "analytics and return a JSON object with these exact keys:\n"
                        "- diagnosis: string (what the data reveals, #1 problem)\n"
                        "- account_consolidation: array of {platform, account, action, reason}\n"
                        "- content_strategy: {double_down: array, stop: array, repurpose_plan: string}\n"
                        "- weekly_cadence: array of {day, platform, format, time_est, notes}\n"
                        "- immediate_actions: array of strings (top 5 this week)\n"
                        "- thirty_day_plan: array of {week, targets: array of strings}\n"
                        "- kpis: array of {metric, current, target_30d}\n"
                        "Return ONLY valid JSON. No markdown. Reference actual numbers."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Analyze this cross-platform data and generate strategy:\n{json.dumps(platform_data, indent=2, default=str)}",
                },
            ],
            temperature=0.7,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.error(f"AI returned invalid JSON: {raw[:200]}")
            return {"error": "AI returned invalid JSON", "raw": raw[:500]}


# =============================================================================
# STRATEGIC ANALYSIS SERVICE (Pub/Sub)
# =============================================================================

class StrategicAnalysisService:
    """
    Pub/sub service for cross-platform strategic analysis.

    Subscribes to:
        - strategy.analysis.requested → Run full analysis pipeline
        - publish.completed           → Track publishing activity
        - metrics.fetch.completed     → Incorporate fresh metrics

    Publishes:
        - strategy.data_collection.started/completed
        - strategy.platform.data_ready
        - strategy.ai_analysis.started/completed
        - strategy.recommendations.ready
        - strategy.cadence.updated
        - strategy.report.ready
        - strategy.analysis.failed
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self._bus = event_bus or EventBus.get_instance()
        self._youtube = YouTubeCollector()
        self._tiktok = TikTokCollector()
        self._instagram = InstagramCollector()
        self._instagram_graph = InstagramGraphCollector()
        self._facebook_ads = FacebookAdsCollector()
        self._analyzer = AIStrategyAnalyzer()
        self._latest_report: Optional[StrategicReport] = None
        self._is_running = False
        self._source = "strategic-analysis-service"

    async def start(self):
        """Subscribe to event bus topics and mark service as running."""
        self._bus.subscribe(
            Topics.STRATEGY_ANALYSIS_REQUESTED, self._handle_analysis_requested
        )
        self._bus.subscribe(
            Topics.PUBLISH_COMPLETED, self._handle_publish_completed
        )
        self._bus.subscribe(
            Topics.METRICS_FETCH_COMPLETED, self._handle_metrics_completed
        )
        self._is_running = True
        logger.info("📊 StrategicAnalysisService started — subscribed to strategy.* topics")

    async def stop(self):
        """Mark service as stopped."""
        self._is_running = False
        logger.info("📊 StrategicAnalysisService stopped")

    # -------------------------------------------------------------------------
    # EVENT HANDLERS
    # -------------------------------------------------------------------------

    async def _handle_analysis_requested(self, event: Event):
        """Handle strategy.analysis.requested — kick off full pipeline."""
        platforms = event.payload.get("platforms", ["youtube", "tiktok", "instagram"])
        correlation_id = event.correlation_id
        logger.info(f"📊 Analysis requested for {platforms} (cid={correlation_id[:8]})")

        try:
            report = await self.run_full_analysis(
                platforms=platforms, correlation_id=correlation_id
            )
            await self._bus.publish(
                Topics.STRATEGY_REPORT_READY,
                report.to_dict(),
                correlation_id=correlation_id,
                source=self._source,
            )
        except Exception as e:
            logger.error(f"Analysis pipeline failed: {e}")
            await self._bus.publish(
                Topics.STRATEGY_ANALYSIS_FAILED,
                {"error": str(e), "platforms": platforms},
                correlation_id=correlation_id,
                source=self._source,
            )

    async def _handle_publish_completed(self, event: Event):
        """Track publishes for cadence monitoring."""
        platform = event.payload.get("platform", "unknown")
        logger.debug(f"📊 Tracked publish to {platform} for cadence analysis")

    async def _handle_metrics_completed(self, event: Event):
        """Incorporate fresh metrics into latest report if available."""
        logger.debug("📊 Fresh metrics available — can trigger re-analysis")

    # -------------------------------------------------------------------------
    # CORE ANALYSIS PIPELINE
    # -------------------------------------------------------------------------

    async def run_full_analysis(
        self,
        platforms: Optional[List[str]] = None,
        correlation_id: Optional[str] = None,
    ) -> StrategicReport:
        """
        Run the full cross-platform strategic analysis pipeline.

        Steps:
            1. Collect data from all platform APIs in parallel
            2. Publish per-platform data events
            3. Run AI analysis on collected data
            4. Generate recommendations and cadence
            5. Publish final report

        Returns:
            StrategicReport with all analysis results
        """
        from uuid import uuid4

        platforms = platforms or ["youtube", "tiktok", "instagram", "instagram_graph", "facebook_ads"]
        cid = correlation_id or str(uuid4())
        report = StrategicReport(
            correlation_id=cid,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        # --- Step 1: Data Collection ---
        await self._bus.publish(
            Topics.STRATEGY_DATA_COLLECTION_STARTED,
            {"platforms": platforms},
            correlation_id=cid,
            source=self._source,
        )

        snapshots = await self._collect_all_platforms(platforms, cid)
        report.platform_snapshots = snapshots

        await self._bus.publish(
            Topics.STRATEGY_DATA_COLLECTION_COMPLETED,
            {
                "platforms_collected": list(snapshots.keys()),
                "errors": {k: v.error for k, v in snapshots.items() if v.error},
            },
            correlation_id=cid,
            source=self._source,
        )

        # --- Step 2: AI Analysis ---
        await self._bus.publish(
            Topics.STRATEGY_AI_ANALYSIS_STARTED,
            {"platform_count": len(snapshots)},
            correlation_id=cid,
            source=self._source,
        )

        ai_result = await self._analyzer.analyze(snapshots)
        report.ai_analysis = ai_result

        await self._bus.publish(
            Topics.STRATEGY_AI_ANALYSIS_COMPLETED,
            {"has_diagnosis": "diagnosis" in ai_result, "has_cadence": "weekly_cadence" in ai_result},
            correlation_id=cid,
            source=self._source,
        )

        # --- Step 3: Extract structured outputs ---
        report.recommendations = ai_result.get("immediate_actions", [])
        report.cadence = {
            "weekly_schedule": ai_result.get("weekly_cadence", []),
            "content_strategy": ai_result.get("content_strategy", {}),
            "kpis": ai_result.get("kpis", []),
        }
        report.status = "completed"

        # Publish recommendations
        await self._bus.publish(
            Topics.STRATEGY_RECOMMENDATIONS_READY,
            {
                "immediate_actions": report.recommendations,
                "account_consolidation": ai_result.get("account_consolidation", []),
            },
            correlation_id=cid,
            source=self._source,
        )

        # Publish cadence
        await self._bus.publish(
            Topics.STRATEGY_CADENCE_UPDATED,
            report.cadence,
            correlation_id=cid,
            source=self._source,
        )

        self._latest_report = report
        logger.info(f"📊 Strategic analysis complete (cid={cid[:8]})")
        return report

    async def _collect_all_platforms(
        self, platforms: List[str], correlation_id: str
    ) -> Dict[str, PlatformSnapshot]:
        """Collect data from all requested platforms in parallel."""
        tasks = {}
        if "youtube" in platforms:
            tasks["youtube"] = self._youtube.collect()
        if "tiktok" in platforms:
            tasks["tiktok"] = self._tiktok.collect()
        if "instagram" in platforms:
            tasks["instagram"] = self._instagram.collect()
        if "instagram_graph" in platforms:
            tasks["instagram_graph"] = self._instagram_graph.collect()
        if "facebook_ads" in platforms:
            tasks["facebook_ads"] = self._facebook_ads.collect()

        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        snapshots = {}

        for platform_key, result in zip(tasks.keys(), results):
            if isinstance(result, Exception):
                snap = PlatformSnapshot(platform=platform_key, account_username="unknown")
                snap.error = str(result)
                snapshots[platform_key] = snap
            else:
                snapshots[platform_key] = result

            # Publish per-platform event
            snap = snapshots[platform_key]
            await self._bus.publish(
                Topics.STRATEGY_PLATFORM_DATA_READY,
                {
                    "platform": platform_key,
                    "account": snap.account_username,
                    "followers": snap.followers,
                    "total_posts": snap.total_posts,
                    "error": snap.error,
                },
                correlation_id=correlation_id,
                source=self._source,
            )

        return snapshots

    # -------------------------------------------------------------------------
    # PUBLIC ACCESSORS
    # -------------------------------------------------------------------------

    def get_latest_report(self) -> Optional[Dict[str, Any]]:
        """Return the latest strategic report as a dict."""
        if self._latest_report:
            return self._latest_report.to_dict()
        return None

    def get_status(self) -> Dict[str, Any]:
        """Return service status."""
        return {
            "is_running": self._is_running,
            "has_report": self._latest_report is not None,
            "latest_report_time": self._latest_report.created_at if self._latest_report else None,
            "latest_report_status": self._latest_report.status if self._latest_report else None,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_instance: Optional[StrategicAnalysisService] = None


def get_strategic_analysis_service(event_bus: Optional[EventBus] = None) -> StrategicAnalysisService:
    """Get or create singleton StrategicAnalysisService."""
    global _instance
    if _instance is None:
        _instance = StrategicAnalysisService(event_bus=event_bus)
    return _instance
