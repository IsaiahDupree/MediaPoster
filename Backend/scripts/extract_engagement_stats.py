"""
Extract Engagement Stats from Instagram URLs
=============================================
Visits each URL from Safari manifest and extracts:
- View count
- Like count  
- Comment count
- Caption
- Posted date
"""

import json
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
from loguru import logger
from concurrent.futures import ThreadPoolExecutor


MANIFEST_PATH = Path("/Users/isaiahdupree/Documents/CompetitorResearch/accounts/personalbrandlaunch/safari_manifest.json")
STATS_PATH = Path("/Users/isaiahdupree/Documents/CompetitorResearch/accounts/personalbrandlaunch/engagement_stats.json")


def extract_stats_from_url(url: str) -> Optional[Dict[str, Any]]:
    """Extract engagement stats from a single Instagram URL using yt-dlp"""
    
    try:
        # Use yt-dlp to get video metadata without downloading
        result = subprocess.run([
            "yt-dlp",
            "--skip-download",
            "--dump-json",
            url
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode != 0:
            logger.debug(f"yt-dlp failed for {url}: {result.stderr[:100]}")
            return None
        
        data = json.loads(result.stdout)
        
        # Extract shortcode from URL
        shortcode = url.split("/")[-2] if url.endswith("/") else url.split("/")[-1]
        
        return {
            "shortcode": shortcode,
            "url": url,
            "view_count": data.get("view_count", 0),
            "like_count": data.get("like_count", 0),
            "comment_count": data.get("comment_count", 0),
            "caption": data.get("description", "")[:500],
            "duration": data.get("duration", 0),
            "upload_date": data.get("upload_date", ""),
            "uploader": data.get("uploader", ""),
            "title": data.get("title", ""),
            "extracted_at": datetime.now().isoformat()
        }
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout extracting stats from {url}")
        return None
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON from yt-dlp for {url}")
        return None
    except Exception as e:
        logger.error(f"Error extracting stats from {url}: {e}")
        return None


async def extract_all_stats(
    urls: List[str],
    max_concurrent: int = 5,
    max_urls: int = 100
) -> List[Dict[str, Any]]:
    """Extract stats from multiple URLs with rate limiting"""
    
    stats = []
    urls_to_process = urls[:max_urls]
    
    logger.info(f"Extracting stats from {len(urls_to_process)} URLs (max {max_concurrent} concurrent)...")
    
    # Use thread pool for concurrent extraction
    with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
        loop = asyncio.get_event_loop()
        
        for i, url in enumerate(urls_to_process):
            logger.info(f"[{i+1}/{len(urls_to_process)}] Processing: {url.split('/')[-2]}")
            
            # Run in thread pool
            result = await loop.run_in_executor(executor, extract_stats_from_url, url)
            
            if result:
                stats.append(result)
                logger.success(f"  Views: {result['view_count']:,} | Likes: {result['like_count']:,} | Comments: {result['comment_count']:,}")
            else:
                logger.warning(f"  Failed to extract stats")
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.5)
    
    return stats


def analyze_engagement(stats: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze engagement patterns from extracted stats"""
    
    if not stats:
        return {}
    
    total_views = sum(s.get("view_count", 0) for s in stats)
    total_likes = sum(s.get("like_count", 0) for s in stats)
    total_comments = sum(s.get("comment_count", 0) for s in stats)
    
    # Sort by engagement
    sorted_by_views = sorted(stats, key=lambda x: x.get("view_count", 0), reverse=True)
    sorted_by_likes = sorted(stats, key=lambda x: x.get("like_count", 0), reverse=True)
    
    # Calculate averages
    avg_views = total_views / len(stats) if stats else 0
    avg_likes = total_likes / len(stats) if stats else 0
    avg_comments = total_comments / len(stats) if stats else 0
    
    # Engagement rate (likes + comments) / views
    engagement_rate = ((total_likes + total_comments) / total_views * 100) if total_views > 0 else 0
    
    return {
        "total_videos_analyzed": len(stats),
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "avg_views": round(avg_views),
        "avg_likes": round(avg_likes),
        "avg_comments": round(avg_comments),
        "engagement_rate": round(engagement_rate, 2),
        "top_5_by_views": [
            {"shortcode": s["shortcode"], "views": s["view_count"], "caption": s["caption"][:100]}
            for s in sorted_by_views[:5]
        ],
        "top_5_by_likes": [
            {"shortcode": s["shortcode"], "likes": s["like_count"], "caption": s["caption"][:100]}
            for s in sorted_by_likes[:5]
        ]
    }


async def main():
    """Extract engagement stats from all Safari-scraped URLs"""
    
    print("\n" + "="*60)
    print("Extracting Engagement Stats from Instagram URLs")
    print("="*60 + "\n")
    
    # Load manifest
    if not MANIFEST_PATH.exists():
        logger.error(f"Manifest not found: {MANIFEST_PATH}")
        return
    
    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)
    
    urls = manifest.get("post_urls", [])
    logger.info(f"Found {len(urls)} URLs in manifest")
    
    # Check for existing stats to resume
    existing_stats = []
    processed_shortcodes = set()
    
    if STATS_PATH.exists():
        with open(STATS_PATH) as f:
            data = json.load(f)
            existing_stats = data.get("videos", [])
            processed_shortcodes = {s["shortcode"] for s in existing_stats}
            logger.info(f"Found {len(existing_stats)} existing stats, resuming...")
    
    # Filter out already processed URLs
    new_urls = [u for u in urls if u.split("/")[-2] not in processed_shortcodes]
    logger.info(f"New URLs to process: {len(new_urls)}")
    
    # Extract stats (limit to 50 for this run)
    new_stats = await extract_all_stats(new_urls, max_concurrent=3, max_urls=50)
    
    # Combine with existing
    all_stats = existing_stats + new_stats
    
    # Analyze
    analysis = analyze_engagement(all_stats)
    
    # Save
    output = {
        "username": "personalbrandlaunch",
        "extracted_at": datetime.now().isoformat(),
        "analysis": analysis,
        "videos": all_stats
    }
    
    with open(STATS_PATH, "w") as f:
        json.dump(output, f, indent=2)
    
    logger.success(f"Saved stats to {STATS_PATH}")
    
    # Print summary
    print("\n" + "="*60)
    print("ENGAGEMENT ANALYSIS")
    print("="*60)
    print(f"\n📊 Videos Analyzed: {analysis.get('total_videos_analyzed', 0)}")
    print(f"👁️  Total Views: {analysis.get('total_views', 0):,}")
    print(f"❤️  Total Likes: {analysis.get('total_likes', 0):,}")
    print(f"💬 Total Comments: {analysis.get('total_comments', 0):,}")
    print(f"\n📈 Avg Views/Video: {analysis.get('avg_views', 0):,}")
    print(f"📈 Avg Likes/Video: {analysis.get('avg_likes', 0):,}")
    print(f"📈 Engagement Rate: {analysis.get('engagement_rate', 0)}%")
    
    print("\n🏆 Top 5 by Views:")
    for i, video in enumerate(analysis.get("top_5_by_views", [])[:5], 1):
        print(f"   {i}. {video['shortcode']} - {video['views']:,} views")
    
    print("\n💖 Top 5 by Likes:")
    for i, video in enumerate(analysis.get("top_5_by_likes", [])[:5], 1):
        print(f"   {i}. {video['shortcode']} - {video['likes']:,} likes")


if __name__ == "__main__":
    asyncio.run(main())
