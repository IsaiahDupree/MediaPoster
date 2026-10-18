#!/usr/bin/env python3
"""
Check API Status for All Social Media Platforms
Shows which APIs are working and which need subscriptions.

Run: python scripts/check_api_status.py
"""
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import httpx
from loguru import logger


async def check_api_status():
    """Check status of all social media APIs."""
    start_time = time.time()
    
    logger.info("="*80)
    logger.info("🔍 Social Media API Status Check")
    logger.info("="*80)
    logger.info(f"📅 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    rapidapi_key = os.getenv("RAPIDAPI_KEY", "")
    youtube_key = os.getenv("YOUTUBE_API_KEY", "")
    
    # Check API keys
    logger.info("="*80)
    logger.info("📋 API Keys Configuration")
    logger.info("="*80)
    logger.info(f"   RapidAPI Key: {'✅ Set' if rapidapi_key else '❌ Missing'} ({len(rapidapi_key)} chars)")
    logger.info(f"   YouTube API Key: {'✅ Set' if youtube_key else '❌ Missing'} ({len(youtube_key)} chars)")
    logger.info("")
    
    # Test each platform
    logger.info("="*80)
    logger.info("🧪 Testing API Endpoints")
    logger.info("="*80)
    results = []
    
    # Instagram
    logger.info("  📸 Testing Instagram API...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://instagram-scraper-api2.p.rapidapi.com/v1/info",
                headers={
                    "X-RapidAPI-Key": rapidapi_key,
                    "X-RapidAPI-Host": "instagram-scraper-api2.p.rapidapi.com"
                },
                params={"username_or_id_or_url": "instagram"}
            )
            status = response.status_code
            if status == 200:
                results.append(("Instagram", "✅ Working", status, "No action needed"))
            elif status == 401:
                results.append(("Instagram", "⚠️ Unauthorized", status, "Need RapidAPI subscription"))
            elif status == 403:
                results.append(("Instagram", "⚠️ Forbidden", status, "Need RapidAPI subscription"))
            elif status == 429:
                results.append(("Instagram", "⚠️ Rate Limited", status, "Too many requests"))
            else:
                results.append(("Instagram", f"❌ Error {status}", status, "Check API status"))
    except Exception as e:
        results.append(("Instagram", "❌ Failed", 0, str(e)[:40]))
    
    # TikTok
    logger.info("  🎵 Testing TikTok API...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://tiktok-scraper7.p.rapidapi.com/user/info",
                headers={
                    "X-RapidAPI-Key": rapidapi_key,
                    "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com"
                },
                params={"unique_id": "tiktok"}
            )
            status = response.status_code
            if status == 200:
                results.append(("TikTok", "✅ Working", status, "No action needed"))
            elif status == 401:
                results.append(("TikTok", "⚠️ Unauthorized", status, "Need RapidAPI subscription"))
            elif status == 403:
                results.append(("TikTok", "⚠️ Forbidden", status, "Need RapidAPI subscription"))
            elif status == 429:
                results.append(("TikTok", "⚠️ Rate Limited", status, "Too many requests"))
            else:
                results.append(("TikTok", f"❌ Error {status}", status, "Check API status"))
    except Exception as e:
        results.append(("TikTok", "❌ Failed", 0, str(e)[:40]))
    
    # Twitter
    logger.info("  𝕏 Testing Twitter API...")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://twitter241.p.rapidapi.com/user",
                headers={
                    "X-RapidAPI-Key": rapidapi_key,
                    "X-RapidAPI-Host": "twitter241.p.rapidapi.com"
                },
                params={"username": "twitter"}
            )
            status = response.status_code
            if status == 200:
                results.append(("Twitter", "✅ Working", status, "No action needed"))
            elif status == 401:
                results.append(("Twitter", "⚠️ Unauthorized", status, "Need RapidAPI subscription"))
            elif status == 403:
                results.append(("Twitter", "⚠️ Forbidden", status, "Need RapidAPI subscription"))
            elif status == 429:
                results.append(("Twitter", "⚠️ Rate Limited", status, "Too many requests"))
            else:
                results.append(("Twitter", f"❌ Error {status}", status, "Check API status"))
    except Exception as e:
        results.append(("Twitter", "❌ Failed", 0, str(e)[:40]))
    
    # YouTube
    logger.info("  📺 Testing YouTube API...")
    if youtube_key:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://www.googleapis.com/youtube/v3/channels",
                    params={
                        "part": "snippet,statistics",
                        "id": "UCnDBsELI2OIaEI5yxA77HNA",
                        "key": youtube_key
                    }
                )
                status = response.status_code
                if status == 200:
                    results.append(("YouTube", "✅ Working", status, "Using YouTube Data API v3"))
                elif status == 403:
                    results.append(("YouTube", "⚠️ Quota Exceeded", status, "Daily quota limit reached"))
                else:
                    results.append(("YouTube", f"❌ Error {status}", status, "Check API key"))
        except Exception as e:
            results.append(("YouTube", "❌ Failed", 0, str(e)[:40]))
    else:
        results.append(("YouTube", "⚠️ No API Key", 0, "Set YOUTUBE_API_KEY in .env"))
    
    total_elapsed = time.time() - start_time
    logger.info("")
    logger.info("="*80)
    logger.info("📊 Results Summary")
    logger.info("="*80)
    logger.info("")
    
    # Print table
    logger.info(f"{'Platform':<12} {'Status':<20} {'Code':<6} {'Action'}")
    logger.info("-" * 80)
    for platform, status, code, action in results:
        logger.info(f"{platform:<12} {status:<20} {code:<6} {action}")
    
    logger.info("")
    logger.info("="*80)
    logger.info("💡 Recommendations")
    logger.info("="*80)
    logger.info("")
    
    working = [r for r in results if "Working" in r[1]]
    needs_sub = [r for r in results if "Unauthorized" in r[1] or "Forbidden" in r[1]]
    errors = [r for r in results if "Failed" in r[1] or "Error" in r[1]]
    
    logger.info(f"✅ Working APIs: {len(working)}/{len(results)}")
    for r in working:
        logger.info(f"   • {r[0]}")
    
    if needs_sub:
        logger.info("")
        logger.info(f"⚠️  Need Subscription: {len(needs_sub)}")
        for r in needs_sub:
            logger.info(f"   • {r[0]} - {r[3]}")
        logger.info("")
        logger.info("   💰 Estimated Cost: $25-100/month for all subscriptions")
        logger.info("   📝 See API_ERROR_CODES.md for details")
    
    if errors:
        logger.info("")
        logger.info(f"❌ Errors: {len(errors)}")
        for r in errors:
            logger.info(f"   • {r[0]} - {r[3]}")
    
    logger.info("")
    logger.info(f"⏱️  Total check time: {total_elapsed:.1f}s")
    logger.info("")


if __name__ == "__main__":
    asyncio.run(check_api_status())
