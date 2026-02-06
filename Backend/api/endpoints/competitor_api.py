"""
Competitor Research API Endpoints
Manage tracked competitor accounts and fetch their content.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from loguru import logger

from services.event_bus import EventBus, Topics
from services.competitor_service import get_competitor_service
from services.competitor_analysis_service import get_analysis_service
from services.competitor_sync_scheduler import get_competitor_scheduler

router = APIRouter(prefix="/api/competitors", tags=["Competitor Research"])


class AddAccountRequest(BaseModel):
    """Request to add a competitor account"""
    username: str
    priority: int = 1  # 1=high, 2=medium, 3=low


class SyncResponse(BaseModel):
    """Response from sync operation"""
    username: str
    reels_fetched: int
    posts_fetched: int
    videos_downloaded: int
    errors: List[str]


@router.get("/health")
async def health_check():
    """Health check for competitor service"""
    service = get_competitor_service()
    accounts = service.get_stored_accounts()
    return {
        "status": "healthy",
        "service": "competitor-research",
        "tracked_accounts": len(accounts),
        "storage_dir": str(service.storage_dir)
    }


@router.get("/accounts")
async def list_accounts():
    """List all tracked competitor accounts"""
    service = get_competitor_service()
    accounts = service.get_stored_accounts()
    return {
        "count": len(accounts),
        "accounts": accounts
    }


@router.get("/accounts/detailed")
async def list_accounts_detailed():
    """
    List all tracked competitor accounts with full details.
    Includes profile data, analysis status, and local video counts.
    """
    service = get_competitor_service()
    details = service.get_stored_account_details()
    return {
        "count": len(details),
        "accounts": details
    }


@router.post("/accounts")
async def add_account(request: AddAccountRequest):
    """
    Add a new competitor account to track.
    Fetches initial profile info.
    """
    service = get_competitor_service()
    
    try:
        profile = await service.fetch_account_info(request.username)
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"Could not find Instagram account: @{request.username}"
            )
        
        # Emit competitor added event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.COMPETITOR_ADDED, {
                "username": request.username,
                "priority": request.priority,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as evt_err:
            logger.warning(f"Failed to emit COMPETITOR_ADDED event: {evt_err}")
        
        return {
            "status": "added",
            "account": profile.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/{username}/sync")
async def sync_account(username: str, background_tasks: BackgroundTasks):
    """
    Sync all content from a competitor account.
    Runs in background for large accounts.
    """
    service = get_competitor_service()
    
    try:
        # Emit sync started event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.COMPETITOR_SYNC_STARTED, {
                "username": username,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as evt_err:
            logger.warning(f"Failed to emit COMPETITOR_SYNC_STARTED event: {evt_err}")
        
        # Run sync
        results = await service.sync_account(username)
        
        # Emit sync completed event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.COMPETITOR_SYNC_COMPLETED, {
                "username": username,
                "results": results,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as evt_err:
            logger.warning(f"Failed to emit COMPETITOR_SYNC_COMPLETED event: {evt_err}")
        
        return {
            "status": "synced",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error syncing account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{username}/profile")
async def get_account_profile(username: str):
    """Get profile info for a competitor account"""
    service = get_competitor_service()
    
    try:
        profile = await service.fetch_account_info(username)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return profile.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{username}/reels")
async def get_account_reels(username: str, count: int = 50):
    """Get reels from a competitor account"""
    service = get_competitor_service()
    
    try:
        reels = await service.fetch_user_reels(username, count)
        
        return {
            "count": len(reels),
            "reels": [r.model_dump() for r in reels]
        }
        
    except Exception as e:
        logger.error(f"Error fetching reels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{username}/posts")
async def get_account_posts(username: str, count: int = 50):
    """Get posts from a competitor account"""
    service = get_competitor_service()
    
    try:
        posts = await service.fetch_user_posts(username, count)
        
        return {
            "count": len(posts),
            "posts": [p.model_dump() for p in posts]
        }
        
    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/{username}/analyze")
async def analyze_account(username: str, max_content: int = 20):
    """
    Analyze competitor content using AI.
    
    Extracts:
    - Top performing hooks
    - Content formats
    - Themes and patterns
    - Replication tips
    - Content ideas
    
    Results saved to CompetitorResearch/accounts/{username}/analysis/
    """
    analysis_service = get_analysis_service()
    
    try:
        learnings = await analysis_service.analyze_account(username, max_content)
        
        if not learnings:
            raise HTTPException(status_code=404, detail="No content to analyze")
        
        return {
            "status": "analyzed",
            "username": username,
            "learnings": learnings.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{username}/analysis")
async def get_account_analysis(username: str):
    """Get stored analysis results for a competitor account"""
    from pathlib import Path
    import json
    
    analysis_path = Path(f"/Users/isaiahdupree/Documents/CompetitorResearch/accounts/{username}/analysis/learnings.json")
    
    if not analysis_path.exists():
        raise HTTPException(status_code=404, detail="No analysis found. Run POST /analyze first.")
    
    try:
        with open(analysis_path) as f:
            learnings = json.load(f)
        return learnings
    except Exception as e:
        logger.error(f"Error reading analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/{username}/scrape")
async def scrape_account_videos(
    username: str,
    background_tasks: BackgroundTasks,
    max_posts: int = 500
):
    """
    Scrape video URLs from a competitor's Instagram profile.
    Uses Safari AppleScript automation to scroll and collect URLs.
    
    This is a background task - check /accounts/{username}/scrape/status for progress.
    """
    from pathlib import Path
    import json
    
    storage_path = Path(f"/Users/isaiahdupree/Documents/CompetitorResearch/accounts/{username}")
    manifest_path = storage_path / "safari_manifest.json"
    
    # Check existing manifest
    existing_urls = 0
    if manifest_path.exists():
        with open(manifest_path) as f:
            data = json.load(f)
            existing_urls = len(data.get('post_urls', []))
    
    return {
        "status": "info",
        "username": username,
        "existing_urls": existing_urls,
        "message": "Run Safari scraper manually for now",
        "command": f"python automation/safari_instagram_scraper.py {username} --max-posts {max_posts}",
        "note": "Safari automation requires manual login - run from terminal"
    }


@router.get("/accounts/{username}/scrape/status")
async def get_scrape_status(username: str):
    """Get the status of URL collection for an account"""
    from pathlib import Path
    import json
    
    storage_path = Path(f"/Users/isaiahdupree/Documents/CompetitorResearch/accounts/{username}")
    manifest_path = storage_path / "safari_manifest.json"
    posts_path = storage_path / "posts"
    
    if not manifest_path.exists():
        return {
            "status": "not_started",
            "username": username,
            "urls_collected": 0,
            "videos_downloaded": 0
        }
    
    with open(manifest_path) as f:
        data = json.load(f)
    
    videos_downloaded = len(list(posts_path.glob("*.mp4"))) if posts_path.exists() else 0
    total_size = sum(f.stat().st_size for f in posts_path.glob("*.mp4")) if posts_path.exists() else 0
    
    return {
        "status": "collected",
        "username": username,
        "urls_collected": len(data.get('post_urls', [])),
        "videos_downloaded": videos_downloaded,
        "downloaded_ids": data.get('downloaded', []),
        "failed_ids": data.get('failed', []),
        "total_size_mb": round(total_size / (1024*1024), 1),
        "last_updated": data.get('last_updated')
    }


@router.post("/accounts/{username}/download")
async def download_account_videos(
    username: str,
    background_tasks: BackgroundTasks,
    limit: int = 0
):
    """
    Download videos from collected URLs using RapidAPI.
    Skips already downloaded videos.
    
    Run this after /scrape to download the collected video URLs.
    """
    from pathlib import Path
    import json
    import re
    import requests
    import os
    import time
    
    storage_path = Path(f"/Users/isaiahdupree/Documents/CompetitorResearch/accounts/{username}")
    manifest_path = storage_path / "safari_manifest.json"
    posts_path = storage_path / "posts"
    posts_path.mkdir(parents=True, exist_ok=True)
    
    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="No URLs collected. Run /scrape first.")
    
    with open(manifest_path) as f:
        manifest = json.load(f)
    
    post_urls = manifest.get('post_urls', [])
    downloaded = set(manifest.get('downloaded', []))
    
    # Get API key
    env_path = Path(__file__).parent.parent.parent / ".env"
    api_key = None
    with open(env_path) as f:
        for line in f:
            if line.startswith('RAPIDAPI_KEY='):
                api_key = line.strip().split('=', 1)[1]
                break
    
    if not api_key:
        raise HTTPException(status_code=500, detail="RapidAPI key not configured")
    
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": "instagram-looter2.p.rapidapi.com"
    }
    
    # Download videos
    new_downloads = 0
    skipped = 0
    failed = []
    download_limit = limit if limit > 0 else len(post_urls)
    
    for post_url in post_urls:
        if new_downloads >= download_limit:
            break
        
        match = re.search(r'/(?:reel|p)/([A-Za-z0-9_-]+)', post_url)
        if not match:
            continue
        shortcode = match.group(1)
        
        filepath = posts_path / f"{shortcode}.mp4"
        if filepath.exists() or shortcode in downloaded:
            skipped += 1
            continue
        
        # Fetch video URL
        video_url = None
        for url_type in ['reel', 'p']:
            try:
                resp = requests.get(
                    f"https://instagram-looter2.p.rapidapi.com/post?url=https://www.instagram.com/{url_type}/{shortcode}/",
                    headers=headers,
                    timeout=30
                )
                if resp.status_code == 200:
                    data = resp.json()
                    video_url = data.get('video_url')
                    if video_url:
                        break
            except:
                pass
            time.sleep(0.3)
        
        if not video_url:
            failed.append(shortcode)
            continue
        
        # Download video
        try:
            video_resp = requests.get(video_url, timeout=120, stream=True)
            if video_resp.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in video_resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                downloaded.add(shortcode)
                new_downloads += 1
        except Exception as e:
            failed.append(shortcode)
            logger.error(f"Download error for {shortcode}: {e}")
        
        time.sleep(0.5)
    
    # Update manifest
    manifest['downloaded'] = list(downloaded)
    manifest['failed'] = list(set(manifest.get('failed', []) + failed))
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    total_videos = len(list(posts_path.glob("*.mp4")))
    total_size = sum(f.stat().st_size for f in posts_path.glob("*.mp4"))
    
    return {
        "status": "completed",
        "username": username,
        "new_downloads": new_downloads,
        "skipped": skipped,
        "failed": len(failed),
        "total_videos": total_videos,
        "total_size_mb": round(total_size / (1024*1024), 1)
    }


# =============================================================================
# SCHEDULER ENDPOINTS
# =============================================================================

@router.get("/scheduler/status")
async def get_scheduler_status():
    """Get the status of the background sync scheduler."""
    scheduler = get_competitor_scheduler()
    return scheduler.get_status()


@router.post("/scheduler/sync-all")
async def trigger_sync_all(background_tasks: BackgroundTasks):
    """Trigger a sync of all tracked competitor accounts."""
    scheduler = get_competitor_scheduler()
    
    # Run sync in background
    async def run_sync():
        return await scheduler.sync_all_accounts()
    
    background_tasks.add_task(run_sync)
    
    return {
        "status": "started",
        "message": "Background sync started for all accounts",
        "tracked_accounts": len(scheduler.get_tracked_accounts())
    }


@router.post("/scheduler/sync/{username}")
async def trigger_sync_account(username: str, background_tasks: BackgroundTasks):
    """Trigger a sync for a specific competitor account."""
    scheduler = get_competitor_scheduler()
    
    async def run_sync():
        return await scheduler.sync_account(username)
    
    background_tasks.add_task(run_sync)
    
    return {
        "status": "started",
        "message": f"Background sync started for @{username}"
    }


# =============================================================================
# CROSS-ACCOUNT ANALYSIS
# =============================================================================

@router.get("/analysis/aggregate")
async def get_aggregate_analysis():
    """
    Get aggregated learnings across all tracked competitor accounts.
    Identifies common patterns, top hooks, and best practices.
    """
    from pathlib import Path
    import json
    
    accounts_dir = Path("/Users/isaiahdupree/Documents/CompetitorResearch/accounts")
    if not accounts_dir.exists():
        return {"status": "no_data", "accounts": 0}
    
    all_hooks = {}
    all_formats = {}
    all_themes = []
    all_learnings = []
    total_content = 0
    total_videos = 0
    accounts_analyzed = []
    
    for account_dir in accounts_dir.iterdir():
        if not account_dir.is_dir() or account_dir.name.startswith('.'):
            continue
        
        username = account_dir.name
        analysis_file = account_dir / "analysis" / "learnings.json"
        posts_dir = account_dir / "posts"
        
        # Count videos
        if posts_dir.exists():
            video_count = len(list(posts_dir.glob("*.mp4")))
            total_videos += video_count
        
        # Load analysis if exists
        if analysis_file.exists():
            try:
                with open(analysis_file) as f:
                    data = json.load(f)
                
                accounts_analyzed.append(username)
                total_content += data.get("total_content_analyzed", 0)
                
                # Aggregate hooks
                for hook in data.get("top_hooks", []):
                    hook_type = hook.get("type", "unknown")
                    count = hook.get("count", 0)
                    all_hooks[hook_type] = all_hooks.get(hook_type, 0) + count
                
                # Aggregate formats
                for fmt in data.get("top_formats", []):
                    fmt_type = fmt.get("type", "unknown")
                    count = fmt.get("count", 0)
                    all_formats[fmt_type] = all_formats.get(fmt_type, 0) + count
                
                # Collect themes
                all_themes.extend(data.get("content_themes", []))
                
                # Collect learnings
                all_learnings.extend(data.get("key_learnings", []))
                
            except Exception as e:
                logger.error(f"Error loading analysis for {username}: {e}")
    
    # Deduplicate and rank
    unique_themes = list(set(all_themes))[:15]
    unique_learnings = list(set(all_learnings))[:20]
    
    # Sort hooks and formats by count
    sorted_hooks = sorted(all_hooks.items(), key=lambda x: x[1], reverse=True)
    sorted_formats = sorted(all_formats.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "status": "success",
        "accounts_analyzed": len(accounts_analyzed),
        "account_names": accounts_analyzed,
        "total_content_items": total_content,
        "total_videos_downloaded": total_videos,
        "aggregate_insights": {
            "top_hooks": [{"type": h[0], "count": h[1]} for h in sorted_hooks[:10]],
            "top_formats": [{"type": f[0], "count": f[1]} for f in sorted_formats[:10]],
            "common_themes": unique_themes,
            "key_learnings": unique_learnings
        }
    }


@router.post("/scrape/safari/{username}")
async def trigger_safari_scrape(
    username: str,
    background_tasks: BackgroundTasks,
    max_posts: int = 500
):
    """
    Trigger Safari AppleScript scraper to collect video URLs.
    This runs the Safari automation in background to scroll and collect URLs.
    
    Note: Requires Safari to be available and may need manual login on first run.
    """
    import subprocess
    import asyncio
    from pathlib import Path
    
    script_path = Path(__file__).parent.parent.parent / "automation" / "safari_instagram_scraper.py"
    venv_path = Path(__file__).parent.parent.parent / "venv" / "bin" / "python"
    
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Safari scraper script not found")
    
    async def run_scraper():
        try:
            # Run the Safari scraper
            process = await asyncio.create_subprocess_exec(
                str(venv_path),
                str(script_path),
                username,
                "--max-posts", str(max_posts),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(script_path.parent.parent)
            )
            stdout, stderr = await process.communicate()
            logger.info(f"Safari scraper completed for {username}")
            if stderr:
                logger.warning(f"Safari scraper stderr: {stderr.decode()[:500]}")
        except Exception as e:
            logger.error(f"Safari scraper error: {e}")
    
    background_tasks.add_task(run_scraper)
    
    return {
        "status": "started",
        "username": username,
        "max_posts": max_posts,
        "message": "Safari scraper started in background. Check /scrape/status for progress.",
        "note": "If this is the first run, Safari may need manual login. Check Safari window."
    }


@router.post("/analysis/generate-playbook")
async def generate_content_playbook():
    """
    Generate an AI-powered content playbook from all competitor learnings.
    Creates actionable recommendations based on cross-account patterns.
    """
    import os
    from openai import OpenAI
    from pathlib import Path
    import json
    
    # Get aggregate data first
    accounts_dir = Path("/Users/isaiahdupree/Documents/CompetitorResearch/accounts")
    
    all_learnings = []
    all_hooks = []
    all_themes = []
    account_summaries = []
    
    for account_dir in accounts_dir.iterdir():
        if not account_dir.is_dir() or account_dir.name.startswith('.'):
            continue
        
        analysis_file = account_dir / "analysis" / "learnings.json"
        if analysis_file.exists():
            with open(analysis_file) as f:
                data = json.load(f)
            
            account_summaries.append({
                "account": account_dir.name,
                "content_count": data.get("total_content_analyzed", 0),
                "top_hooks": [h.get("type") for h in data.get("top_hooks", [])[:3]],
                "themes": data.get("content_themes", [])[:5]
            })
            all_learnings.extend(data.get("key_learnings", []))
            all_hooks.extend([h.get("type") for h in data.get("top_hooks", [])])
            all_themes.extend(data.get("content_themes", []))
    
    if not account_summaries:
        raise HTTPException(status_code=404, detail="No competitor analysis data found")
    
    # Generate playbook with OpenAI
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""Based on analysis of {len(account_summaries)} successful Instagram accounts, create a content playbook.

ACCOUNT SUMMARIES:
{json.dumps(account_summaries, indent=2)}

TOP HOOKS USED: {list(set(all_hooks))[:10]}
COMMON THEMES: {list(set(all_themes))[:15]}
KEY LEARNINGS: {list(set(all_learnings))[:15]}

Create a structured content playbook with:
1. HOOK FORMULAS - 5 proven hook templates with examples
2. CONTENT FORMATS - Top 3 formats that work best
3. POSTING STRATEGY - Timing and frequency recommendations
4. ENGAGEMENT TACTICS - How to maximize interaction
5. CONTENT IDEAS - 10 specific content ideas based on what's working

Format as JSON with these keys: hook_formulas, content_formats, posting_strategy, engagement_tactics, content_ideas"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )
    
    try:
        playbook = json.loads(response.choices[0].message.content)
    except:
        playbook = {"raw_response": response.choices[0].message.content}
    
    # Save playbook
    playbook_path = accounts_dir.parent / "learnings" / "content_playbook.json"
    playbook_path.parent.mkdir(parents=True, exist_ok=True)
    with open(playbook_path, 'w') as f:
        json.dump({
            "generated_at": datetime.now().isoformat(),
            "accounts_analyzed": len(account_summaries),
            "playbook": playbook
        }, f, indent=2, default=str)
    
    return {
        "status": "generated",
        "accounts_analyzed": len(account_summaries),
        "playbook": playbook,
        "saved_to": str(playbook_path)
    }
