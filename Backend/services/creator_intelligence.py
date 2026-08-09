"""
Creator Intelligence
=====================
Deep-dives into a specific TikTok creator's real recent posts (or the
top-scoring creator for a niche, sourced from trend_detection.py's already
niche-filtered results) to produce an honest style breakdown: hook/caption
patterns, hashtag strategy, posting cadence, and relative engagement --
everything genuinely inferable from real caption text + engagement metrics
+ post format.

Explicitly NOT claimed: visual/editing/pacing/on-screen-text analysis. The
RapidAPI TikTok endpoints used here (/user/info, /user/posts) return caption
text and engagement numbers -- not video frames, on-screen text (OCR), or a
spoken transcript -- so an "editing style"/"pacing" claim would be
fabricated. Every response carries a `data_basis` field naming exactly what
was and wasn't analyzed, plus real video URLs so a human can inspect the
visual/audio style directly.

Instagram is deliberately NOT used for per-creator post fetches here: live
verification (2026-07-31) confirmed its RapidAPI tier allows roughly 20
requests per ~26 days -- a single "find top creators + analyze each" query
could exhaust a month's budget in one call. TikTok's /user/posts has ample
headroom (~300 requests / 7.8 days) by comparison, so this module is
TikTok-only for now.
"""
import json
import os
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from services.trend_detection import RAPIDAPI_KEY, TrendDetectionService

TIKTOK_API_HOST = "tiktok-scraper7.p.rapidapi.com"

DATA_BASIS_NOTE = (
    "Analysis derived from real caption text, hashtags, posting cadence, and "
    "engagement metrics across this creator's recent posts. Does NOT include "
    "visual, editing, pacing, on-screen-text, or spoken-audio analysis -- "
    "those signals aren't available from this data source. Use the linked "
    "video_url on each post to inspect that yourself."
)


class CreatorIntelligenceUnavailable(RuntimeError):
    """Raised when the creator can't be found/fetched, or AI synthesis fails."""


async def get_creator_profile(handle: str) -> Optional[Dict[str, Any]]:
    """Real TikTok /user/info call. None if the handle doesn't resolve."""
    if not RAPIDAPI_KEY:
        logger.warning(f"[CreatorIntel] No RAPIDAPI_KEY set, skipping profile lookup for {handle!r}")
        return None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://{TIKTOK_API_HOST}/user/info",
                params={"unique_id": handle},
                headers={"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": TIKTOK_API_HOST},
            )
            if resp.status_code != 200:
                return None
            data = (resp.json().get("data") or {})
            user = data.get("user") or {}
            stats = data.get("stats") or {}
            if not user:
                return None
            return {
                "handle": user.get("uniqueId", handle),
                "nickname": user.get("nickname"),
                "bio": user.get("signature"),
                "avatar_url": user.get("avatarLarger"),
                "follower_count": stats.get("followerCount"),
                "heart_count": stats.get("heartCount"),
                "video_count": stats.get("videoCount"),
            }
    except Exception as e:
        logger.warning(f"[CreatorIntel] profile lookup failed for {handle!r}: {e}")
        return None


async def get_creator_posts(handle: str, count: int = 10) -> List[Dict[str, Any]]:
    """Real TikTok /user/posts call. Empty list on any failure, never fabricated."""
    if not RAPIDAPI_KEY:
        logger.warning(f"[CreatorIntel] No RAPIDAPI_KEY set, skipping posts lookup for {handle!r}")
        return []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"https://{TIKTOK_API_HOST}/user/posts",
                params={"unique_id": handle, "count": count},
                headers={"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": TIKTOK_API_HOST},
            )
            if resp.status_code != 200:
                return []
            videos = ((resp.json().get("data") or {}).get("videos")) or []
            posts = []
            for v in videos:
                title = (v.get("title") or "").strip()
                if not title:
                    continue
                posts.append({
                    "caption": title,
                    "views": v.get("play_count", 0),
                    "likes": v.get("digg_count", 0),
                    "comments": v.get("comment_count", 0),
                    "shares": v.get("share_count", 0),
                    "posted_at_epoch": v.get("create_time"),
                    "video_url": v.get("play"),
                    "thumbnail_url": v.get("cover"),
                })
            return posts
    except Exception as e:
        logger.warning(f"[CreatorIntel] posts lookup failed for {handle!r}: {e}")
        return []


async def find_top_creator_for_niche(niche: str) -> Optional[Dict[str, str]]:
    """
    The top-scoring real, niche-relevant TikTok video's creator, sourced from
    trend_detection.py's already niche-filtered results (not a raw/unfiltered
    search hit -- this creator's video genuinely passed niche relevance
    scoring). None if nothing relevant has a resolvable author.
    """
    trends = TrendDetectionService()
    result = await trends.get_trending_for_niche(niche, limit=15)
    for item in result["trending"]:
        if item.get("author_handle"):
            return {"handle": item["author_handle"], "nickname": item.get("author_nickname") or ""}
    return None


def _engagement_rate(post: Dict[str, Any]) -> float:
    views = post.get("views") or 0
    if views <= 0:
        return 0.0
    return (post.get("likes", 0) + post.get("comments", 0) + post.get("shares", 0)) / views


async def analyze_creator_style(handle: str, niche: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch this creator's real profile + recent posts and produce an honest
    style breakdown (hook/caption/hashtag/format/cadence patterns) via GPT,
    explicitly constrained to what the real metadata supports. Raises
    CreatorIntelligenceUnavailable if the creator can't be found or AI
    synthesis fails -- never returns a fabricated breakdown.
    """
    profile = await get_creator_profile(handle)
    if profile is None:
        raise CreatorIntelligenceUnavailable(f"could not find TikTok creator {handle!r}")

    posts = await get_creator_posts(handle, count=10)
    if not posts:
        raise CreatorIntelligenceUnavailable(f"no fetchable recent posts for {handle!r}")

    ranked = sorted(posts, key=_engagement_rate, reverse=True)
    best_post = ranked[0]

    try:
        breakdown = await _gpt_style_breakdown(profile, posts, niche)
    except Exception as e:
        logger.error(f"[CreatorIntel] style synthesis failed for {handle!r}: {e}")
        raise CreatorIntelligenceUnavailable(str(e)) from e

    return {
        "creator": profile,
        "example_post": best_post,
        "style_breakdown": breakdown,
        "posts_analyzed": len(posts),
        "data_basis": DATA_BASIS_NOTE,
    }


async def _gpt_style_breakdown(
    profile: Dict[str, Any],
    posts: List[Dict[str, Any]],
    niche: Optional[str],
) -> Dict[str, Any]:
    from openai import OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    posts_desc = "\n".join(
        f"- \"{p['caption']}\" ({p['views']} views, {p['likes']} likes, {p['comments']} comments, {p['shares']} shares)"
        for p in posts
    )

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": f"""You are a social media analyst. You are given a real creator's profile and
their {len(posts)} most recent post captions + engagement numbers.
Identify ONLY patterns genuinely supported by this text/engagement data:
hook style (how their captions open), hashtag strategy, caption tone/voice,
recurring content format, and which posts perform best and why (based on
the engagement numbers given, not invented reasons).

Do NOT claim anything about visual style, editing, pacing, on-screen text,
or spoken content -- you were not given video, audio, or frames, only
caption text and engagement counts. If you cannot support a claim from the
given text/numbers, omit it or say so plainly.

{f'The creator is being evaluated for the niche: {niche}.' if niche else ''}

Return JSON: {{"hook_pattern": str, "hashtag_strategy": str,
"caption_tone": str, "content_format": str, "why_top_post_works": str,
"adaptation_suggestion": str}}
"adaptation_suggestion" should say concretely how someone in a similar or
adjacent niche could adapt this creator's approach -- grounded in the
patterns you just identified, not generic advice.""",
            },
            {
                "role": "user",
                "content": f"Creator: {profile.get('nickname')} (@{profile.get('handle')})\n"
                f"Bio: {profile.get('bio')}\n"
                f"Followers: {profile.get('follower_count')}\n\n"
                f"Recent posts:\n{posts_desc}",
            },
        ],
        temperature=0.5,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)
