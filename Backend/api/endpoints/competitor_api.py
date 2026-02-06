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


@router.post("/batch-fetch-posts")
async def batch_fetch_posts(count: int = 50):
    """
    Fetch posts for ALL tracked competitor accounts via instagram-looter2.
    Runs sequentially to avoid API rate limits.
    """
    import httpx
    import re
    import json as json_mod

    service = get_competitor_service()

    if not service.api_key:
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY not configured")

    accounts = service.get_stored_accounts()
    if not accounts:
        raise HTTPException(status_code=404, detail="No tracked accounts found")

    results = []
    errors = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for username in accounts:
            try:
                response = await client.get(
                    "https://instagram-looter2.p.rapidapi.com/v1/posts",
                    headers={
                        "X-RapidAPI-Key": service.api_key,
                        "X-RapidAPI-Host": "instagram-looter2.p.rapidapi.com",
                    },
                    params={"username": username, "count": str(count)},
                )

                if response.status_code != 200:
                    errors.append({"username": username, "error": f"API {response.status_code}"})
                    continue

                data = response.json()
                posts = data.get("data", data.get("items", data if isinstance(data, list) else []))
                if not isinstance(posts, list):
                    posts = [posts] if posts else []

                # Save
                account_dir = service._get_account_dir(username)
                posts_file = account_dir / "posts" / "posts.json"
                with open(posts_file, "w") as f:
                    json_mod.dump(posts, f, indent=2, default=str)

                results.append({"username": username, "posts_fetched": len(posts)})
                logger.info(f"Batch fetched {len(posts)} posts for @{username}")

            except Exception as e:
                logger.error(f"Batch fetch posts error for @{username}: {e}")
                errors.append({"username": username, "error": str(e)})

    return {
        "status": "completed",
        "fetched": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }


@router.post("/batch-analyze")
async def batch_analyze_all():
    """
    Run AI analysis on ALL tracked competitor accounts.
    Processes each account sequentially and returns aggregate results.
    """
    service = get_competitor_service()
    analysis_service = get_analysis_service()
    accounts = service.get_stored_accounts()

    if not accounts:
        raise HTTPException(status_code=404, detail="No tracked accounts found")

    results = []
    errors = []

    for username in accounts:
        try:
            logger.info(f"Batch analyzing @{username}...")
            content = service.load_stored_content(username)

            if not content:
                errors.append({"username": username, "error": "No stored content"})
                continue

            learnings = await analysis_service.analyze_account(username)

            if learnings:
                results.append({
                    "username": username,
                    "content_analyzed": learnings.total_content_analyzed,
                    "themes": learnings.content_themes[:5],
                    "top_hooks": [h.get("type") for h in learnings.top_hooks[:3]],
                    "ideas_generated": len(learnings.content_ideas),
                })
            else:
                errors.append({"username": username, "error": "Analysis returned no results"})

        except Exception as e:
            logger.error(f"Error batch-analyzing @{username}: {e}")
            errors.append({"username": username, "error": str(e)})

    return {
        "status": "completed",
        "analyzed": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
    }


@router.post("/accounts/{username}/fetch-posts")
async def fetch_posts_looter2(username: str, count: int = 50):
    """
    Fetch posts for a competitor via instagram-looter2 API.
    Uses the confirmed working /v1/posts endpoint.
    Stores results locally in the account's posts directory.
    """
    import httpx
    import re

    service = get_competitor_service()

    if not service.api_key:
        raise HTTPException(status_code=500, detail="RAPIDAPI_KEY not configured")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://instagram-looter2.p.rapidapi.com/v1/posts",
                headers={
                    "X-RapidAPI-Key": service.api_key,
                    "X-RapidAPI-Host": "instagram-looter2.p.rapidapi.com",
                },
                params={"username": username, "count": str(count)},
            )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"API returned {response.status_code}: {response.text[:200]}",
            )

        data = response.json()
        posts = data.get("data", data.get("items", data if isinstance(data, list) else []))

        if not isinstance(posts, list):
            posts = [posts] if posts else []

        # Save raw posts
        account_dir = service._get_account_dir(username)
        posts_file = account_dir / "posts" / "posts.json"
        
        import json as json_mod
        with open(posts_file, "w") as f:
            json_mod.dump(posts, f, indent=2, default=str)

        # Parse into structured content
        parsed = []
        for p in posts:
            caption = p.get("caption", "") or ""
            hashtags = re.findall(r'#(\w+)', caption)
            mentions = re.findall(r'@(\w+)', caption)

            parsed.append({
                "id": p.get("id", p.get("pk", "")),
                "shortcode": p.get("code", p.get("shortcode", "")),
                "type": "video" if p.get("is_video") or p.get("video_url") else "image",
                "caption": caption[:200],
                "like_count": p.get("like_count", 0),
                "comment_count": p.get("comment_count", 0),
                "play_count": p.get("play_count", p.get("video_view_count", 0)),
                "hashtags": [f"#{t}" for t in hashtags],
                "mentions": [f"@{m}" for m in mentions],
            })

        logger.info(f"Fetched {len(parsed)} posts for @{username} via looter2")

        return {
            "status": "fetched",
            "username": username,
            "posts_count": len(parsed),
            "saved_to": str(posts_file),
            "posts": parsed[:10],  # Return first 10 as preview
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching posts for @{username}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/accounts/{username}")
async def delete_account(username: str):
    """
    Remove a tracked competitor account and its local data.
    """
    import shutil

    service = get_competitor_service()
    accounts = service.get_stored_accounts()

    if username not in accounts:
        raise HTTPException(status_code=404, detail=f"Account @{username} not found")

    account_dir = service.storage_dir / "accounts" / username
    try:
        shutil.rmtree(account_dir)
        logger.info(f"Deleted competitor account @{username}")
        return {"status": "deleted", "username": username}
    except Exception as e:
        logger.error(f"Error deleting @{username}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{username}/content")
async def get_account_content(username: str, limit: int = 50):
    """
    Get stored content (reels + posts) for a competitor account.
    Returns parsed content with engagement metrics.
    """
    service = get_competitor_service()
    content = service.load_stored_content(username)

    if not content:
        raise HTTPException(
            status_code=404,
            detail=f"No content found for @{username}. Run fetch-posts or sync first.",
        )

    # Sort by play_count desc
    sorted_content = sorted(
        [c.model_dump() for c in content],
        key=lambda x: x.get("play_count", 0),
        reverse=True,
    )

    return {
        "username": username,
        "total": len(sorted_content),
        "content": sorted_content[:limit],
    }


@router.get("/compare")
async def compare_competitors(usernames: str = ""):
    """
    Side-by-side comparison of multiple competitor accounts.
    Pass comma-separated usernames, or leave empty for all tracked accounts.

    Returns metrics, themes, hooks, and content mix for each account.
    """
    service = get_competitor_service()
    all_accounts = service.get_stored_accounts()

    if usernames:
        selected = [u.strip() for u in usernames.split(",") if u.strip()]
    else:
        selected = all_accounts

    if len(selected) < 1:
        raise HTTPException(status_code=400, detail="Need at least 1 account to compare")

    comparisons = []

    for username in selected:
        if username not in all_accounts:
            continue

        account_dir = service.storage_dir / "accounts" / username
        entry: Dict[str, Any] = {
            "username": username,
            "followers": 0,
            "total_content": 0,
            "avg_engagement": 0,
            "content_mix": {"reels": 0, "posts": 0},
            "themes": [],
            "top_hooks": [],
            "top_formats": [],
            "hashtags": [],
        }

        # Load profile
        profile_path = account_dir / "profile.json"
        if profile_path.exists():
            try:
                with open(profile_path) as f:
                    profile = json.load(f)
                entry["followers"] = profile.get("followers_count", 0)
                entry["full_name"] = profile.get("full_name", "")
                entry["bio"] = profile.get("bio", "")[:120]
            except Exception:
                pass

        # Load analysis
        analysis_path = account_dir / "analysis" / "learnings.json"
        if analysis_path.exists():
            try:
                with open(analysis_path) as f:
                    data = json.load(f)
                entry["total_content"] = data.get("total_content_analyzed", 0)
                entry["avg_engagement"] = round(data.get("avg_engagement_rate", 0), 1)
                entry["themes"] = data.get("content_themes", [])[:6]
                entry["top_hooks"] = data.get("top_hooks", [])[:4]
                entry["top_formats"] = data.get("top_formats", [])[:4]

                patterns = data.get("posting_patterns", {})
                entry["content_mix"] = {
                    "reels": patterns.get("total_reels", 0),
                    "posts": patterns.get("total_posts", 0),
                }
                entry["hashtags"] = [
                    h.get("tag", "") for h in patterns.get("hashtag_frequency", [])[:8]
                ]
                entry["content_ideas"] = data.get("content_ideas", [])[:3]
                entry["key_learnings"] = data.get("key_learnings", [])[:3]
            except Exception:
                pass

        comparisons.append(entry)

    # Sort by followers desc
    comparisons.sort(key=lambda c: c.get("followers", 0), reverse=True)

    return {
        "count": len(comparisons),
        "comparisons": comparisons,
    }


@router.post("/discover")
async def discover_similar_accounts(niche: str = "personal branding", count: int = 10):
    """
    AI-powered competitor discovery.
    Suggests new accounts to track based on existing competitor data and niche.
    """
    import openai as _openai

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    service = get_competitor_service()
    all_accounts = service.get_stored_accounts()

    # Gather context from existing tracked accounts
    themes: List[str] = []
    hashtags: List[str] = []
    for username in all_accounts:
        analysis_path = service.storage_dir / "accounts" / username / "analysis" / "learnings.json"
        if analysis_path.exists():
            try:
                with open(analysis_path) as f:
                    data = json.load(f)
                themes.extend(data.get("content_themes", []))
                for h in data.get("posting_patterns", {}).get("hashtag_frequency", []):
                    hashtags.append(h.get("tag", ""))
            except Exception:
                pass

    unique_themes = list(set(themes))[:10]
    unique_tags = list(set(hashtags))[:15]

    try:
        client = _openai.OpenAI(api_key=api_key)

        prompt = f"""Suggest {count} Instagram accounts to track as competitors/inspirations for the "{niche}" niche.

CURRENTLY TRACKED ACCOUNTS (exclude these):
{json.dumps(all_accounts)}

THEMES FROM CURRENT COMPETITORS:
{json.dumps(unique_themes)}

POPULAR HASHTAGS IN NICHE:
{json.dumps(unique_tags)}

Return a JSON array of account suggestions:
[
    {{
        "username": "instagram_handle (no @)",
        "reason": "Why this account is worth tracking",
        "estimated_followers": "approximate range like 50K-100K",
        "content_style": "brief description of their content approach",
        "overlap_themes": ["themes they share with current competitors"]
    }}
]

Rules:
- Suggest REAL, active Instagram accounts in this niche
- Mix of account sizes (micro to large)
- Focus on accounts with strong engagement, not just followers
- Don't repeat any currently tracked accounts

Return ONLY valid JSON array."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an Instagram growth expert who discovers high-value competitor accounts to study. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1500,
        )

        result_text = response.choices[0].message.content.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]

        suggestions = json.loads(result_text)

        return {
            "niche": niche,
            "currently_tracked": len(all_accounts),
            "suggestions": suggestions,
        }

    except Exception as e:
        logger.error(f"Error discovering accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hashtag-analytics")
async def get_hashtag_analytics(limit: int = 50):
    """
    Aggregate hashtag analytics across all tracked competitors.
    Returns frequency, accounts using each tag, and estimated reach.
    """
    service = get_competitor_service()
    all_accounts = service.get_stored_accounts()

    tag_data: Dict[str, Dict[str, Any]] = {}

    for username in all_accounts:
        analysis_path = service.storage_dir / "accounts" / username / "analysis" / "learnings.json"
        if not analysis_path.exists():
            continue
        try:
            with open(analysis_path) as f:
                data = json.load(f)

            hashtag_freq = data.get("posting_patterns", {}).get("hashtag_frequency", [])
            for entry in hashtag_freq:
                tag = entry.get("tag", "")
                count = entry.get("count", 0)
                if not tag:
                    continue
                if tag not in tag_data:
                    tag_data[tag] = {"tag": tag, "total_uses": 0, "accounts": [], "top_account": ""}
                tag_data[tag]["total_uses"] += count
                tag_data[tag]["accounts"].append({"username": username, "count": count})
        except Exception:
            pass

    # Sort by total uses and enrich
    sorted_tags = sorted(tag_data.values(), key=lambda t: t["total_uses"], reverse=True)[:limit]
    for t in sorted_tags:
        t["account_count"] = len(t["accounts"])
        t["top_account"] = max(t["accounts"], key=lambda a: a["count"])["username"] if t["accounts"] else ""

    return {
        "total_unique_hashtags": len(tag_data),
        "competitors_analyzed": len(all_accounts),
        "top_hashtags": sorted_tags,
    }


@router.get("/theme-analytics")
async def get_theme_analytics():
    """
    Aggregate content themes across all tracked competitors.
    Shows which themes are most common, who uses them, and overlap.
    """
    service = get_competitor_service()
    all_accounts = service.get_stored_accounts()

    theme_data: Dict[str, Dict[str, Any]] = {}

    for username in all_accounts:
        analysis_path = service.storage_dir / "accounts" / username / "analysis" / "learnings.json"
        if not analysis_path.exists():
            continue
        try:
            with open(analysis_path) as f:
                data = json.load(f)
            for theme in data.get("content_themes", []):
                if not theme:
                    continue
                key = theme.lower().strip()
                if key not in theme_data:
                    theme_data[key] = {"theme": theme, "accounts": [], "count": 0}
                if username not in theme_data[key]["accounts"]:
                    theme_data[key]["accounts"].append(username)
                theme_data[key]["count"] += 1
        except Exception:
            pass

    sorted_themes = sorted(theme_data.values(), key=lambda t: t["count"], reverse=True)
    for t in sorted_themes:
        t["account_count"] = len(t["accounts"])
        t["coverage_pct"] = round(len(t["accounts"]) / max(len(all_accounts), 1) * 100, 1)

    return {
        "total_themes": len(theme_data),
        "competitors_analyzed": len(all_accounts),
        "themes": sorted_themes[:50],
    }


@router.get("/engagement-timing")
async def get_engagement_timing():
    """
    Analyze posting patterns and top-performing content timing across competitors.
    Returns aggregated data on content mix, engagement rates, and best performing content.
    """
    service = get_competitor_service()
    all_accounts = service.get_stored_accounts()

    total_reels = 0
    total_posts = 0
    reel_plays: List[int] = []
    reel_likes: List[int] = []
    post_likes: List[int] = []
    top_content: List[Dict[str, Any]] = []

    for username in all_accounts:
        analysis_path = service.storage_dir / "accounts" / username / "analysis" / "learnings.json"
        if not analysis_path.exists():
            continue
        try:
            with open(analysis_path) as f:
                data = json.load(f)
            pp = data.get("posting_patterns", {})
            total_reels += pp.get("total_reels", 0)
            total_posts += pp.get("total_posts", 0)

            reel_eng = pp.get("engagement_by_type", {}).get("reels", {})
            post_eng = pp.get("engagement_by_type", {}).get("posts", {})
            if reel_eng.get("avg_plays"):
                reel_plays.append(reel_eng["avg_plays"])
            if reel_eng.get("avg_likes"):
                reel_likes.append(reel_eng["avg_likes"])
            if post_eng.get("avg_likes"):
                post_likes.append(post_eng["avg_likes"])

            for tc in pp.get("top_performing", [])[:3]:
                top_content.append({**tc, "source": username})
        except Exception:
            pass

    top_content.sort(key=lambda c: c.get("plays", 0) + c.get("likes", 0) * 10, reverse=True)

    def _avg(lst: list) -> float:
        return round(sum(lst) / len(lst), 1) if lst else 0

    return {
        "competitors_analyzed": len(all_accounts),
        "content_mix": {
            "total_reels": total_reels,
            "total_posts": total_posts,
            "reels_pct": round(total_reels / max(total_reels + total_posts, 1) * 100, 1),
        },
        "avg_engagement": {
            "reel_avg_plays": _avg(reel_plays),
            "reel_avg_likes": _avg(reel_likes),
            "post_avg_likes": _avg(post_likes),
        },
        "top_performing_content": top_content[:10],
    }


@router.get("/audit-report")
async def get_audit_report():
    """
    Generate a comprehensive audit report synthesizing all competitor data:
    - Account summaries with follower counts and content volume
    - Cross-competitor theme analysis
    - Hashtag strategy overview
    - Engagement benchmarks
    - Content format breakdown
    - Key opportunities identified
    """
    service = get_competitor_service()
    all_accounts = service.get_stored_accounts()

    account_summaries = []
    all_themes: Dict[str, int] = {}
    all_hashtags: Dict[str, int] = {}
    total_reels = 0
    total_posts = 0
    engagement_scores: List[float] = []
    all_hooks: List[str] = []
    all_strategies: List[str] = []
    opportunities: List[Dict[str, Any]] = []

    for username in all_accounts:
        analysis_path = service.storage_dir / "accounts" / username / "analysis" / "learnings.json"
        if not analysis_path.exists():
            account_summaries.append({
                "username": username,
                "has_analysis": False,
                "status": "needs_analysis",
            })
            continue

        try:
            with open(analysis_path) as f:
                data = json.load(f)

            # Account summary
            pp = data.get("posting_patterns", {})
            acct_reels = pp.get("total_reels", 0)
            acct_posts = pp.get("total_posts", 0)
            total_reels += acct_reels
            total_posts += acct_posts

            reel_eng = pp.get("engagement_by_type", {}).get("reels", {})
            post_eng = pp.get("engagement_by_type", {}).get("posts", {})
            avg_eng = (reel_eng.get("avg_likes", 0) + post_eng.get("avg_likes", 0)) / 2

            account_summaries.append({
                "username": username,
                "has_analysis": True,
                "total_content": acct_reels + acct_posts,
                "reels": acct_reels,
                "posts": acct_posts,
                "avg_reel_plays": reel_eng.get("avg_plays", 0),
                "avg_reel_likes": reel_eng.get("avg_likes", 0),
                "avg_post_likes": post_eng.get("avg_likes", 0),
                "engagement_score": round(avg_eng, 1),
                "themes": data.get("content_themes", [])[:5],
                "top_hooks": [h.get("hook", "") for h in pp.get("top_performing", [])[:2] if h.get("hook")],
            })

            engagement_scores.append(avg_eng)

            # Aggregate themes
            for theme in data.get("content_themes", []):
                if theme:
                    key = theme.lower().strip()
                    all_themes[key] = all_themes.get(key, 0) + 1

            # Aggregate hashtags
            for ht in data.get("hashtag_strategy", []):
                if ht:
                    key = ht.lower().strip()
                    all_hashtags[key] = all_hashtags.get(key, 0) + 1

            # Collect hooks
            for hook in data.get("hook_patterns", []):
                if isinstance(hook, str) and hook:
                    all_hooks.append(hook)
                elif isinstance(hook, dict) and hook.get("pattern"):
                    all_hooks.append(hook["pattern"])

            # Collect strategies
            for strat in data.get("growth_strategies", []):
                if isinstance(strat, str) and strat:
                    all_strategies.append(strat)

        except Exception:
            account_summaries.append({
                "username": username,
                "has_analysis": False,
                "status": "error",
            })

    # Sort themes and hashtags by frequency
    sorted_themes = sorted(all_themes.items(), key=lambda x: x[1], reverse=True)[:20]
    sorted_hashtags = sorted(all_hashtags.items(), key=lambda x: x[1], reverse=True)[:30]

    # Identify opportunities from gaps
    analyzed_count = sum(1 for a in account_summaries if a.get("has_analysis"))
    if analyzed_count > 0:
        # Low-competition themes (used by few competitors)
        for theme, count in sorted_themes:
            if count <= max(1, analyzed_count // 3):
                opportunities.append({
                    "type": "underserved_theme",
                    "label": f"Low-competition theme: {theme}",
                    "detail": f"Only {count}/{analyzed_count} competitors cover this",
                    "priority": "high" if count == 1 else "medium",
                })
        # High-engagement formats
        if total_reels > total_posts * 2:
            opportunities.append({
                "type": "format_trend",
                "label": "Reels dominate competitor content",
                "detail": f"{round(total_reels / max(total_reels + total_posts, 1) * 100)}% reels vs posts",
                "priority": "high",
            })

    avg_eng_score = round(sum(engagement_scores) / len(engagement_scores), 1) if engagement_scores else 0

    return {
        "generated_at": datetime.now().isoformat(),
        "summary": {
            "total_competitors": len(all_accounts),
            "analyzed": analyzed_count,
            "total_content_pieces": total_reels + total_posts,
            "total_reels": total_reels,
            "total_posts": total_posts,
            "avg_engagement_score": avg_eng_score,
        },
        "accounts": sorted(account_summaries, key=lambda a: a.get("engagement_score", 0), reverse=True),
        "top_themes": [{"theme": t, "count": c, "coverage_pct": round(c / max(analyzed_count, 1) * 100, 1)} for t, c in sorted_themes],
        "top_hashtags": [{"hashtag": h, "count": c} for h, c in sorted_hashtags],
        "hook_patterns": list(set(all_hooks))[:20],
        "growth_strategies": list(set(all_strategies))[:15],
        "opportunities": opportunities[:10],
    }


@router.get("/research-export")
async def export_research_data():
    """
    Export all research data in a unified format for download/sharing.
    Combines competitor analysis, hashtags, themes, hooks, and strategies.
    """
    service = get_competitor_service()
    all_accounts = service.get_stored_accounts()

    export_data: Dict[str, Any] = {
        "exported_at": datetime.now().isoformat(),
        "accounts": {},
    }

    for username in all_accounts:
        analysis_path = service.storage_dir / "accounts" / username / "analysis" / "learnings.json"
        acct_data: Dict[str, Any] = {"username": username, "has_analysis": False}

        if analysis_path.exists():
            try:
                with open(analysis_path) as f:
                    acct_data = json.load(f)
                acct_data["has_analysis"] = True
                acct_data["username"] = username
            except Exception:
                pass

        export_data["accounts"][username] = acct_data

    # Include saved hooks
    hooks_path = service.storage_dir / "saved_hooks.json"
    if hooks_path.exists():
        try:
            with open(hooks_path) as f:
                export_data["saved_hooks"] = json.load(f)
        except Exception:
            export_data["saved_hooks"] = []

    # Include saved ideas
    ideas_path = service.storage_dir / "saved_ideas.json"
    if ideas_path.exists():
        try:
            with open(ideas_path) as f:
                export_data["saved_ideas"] = json.load(f)
        except Exception:
            export_data["saved_ideas"] = []

    return export_data


# =============================================================================
# SWIPE FILE - Save inspiring competitor content with notes/tags
# =============================================================================

def _load_swipe_file() -> List[Dict[str, Any]]:
    service = get_competitor_service()
    path = service.storage_dir / "swipe_file.json"
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_swipe_file(items: List[Dict[str, Any]]):
    service = get_competitor_service()
    path = service.storage_dir / "swipe_file.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(items, f, indent=2)


@router.get("/swipe-file")
async def get_swipe_file(tag: str = "", source: str = ""):
    """Get all saved swipe file entries, optionally filtered by tag or source account."""
    items = _load_swipe_file()
    if tag:
        items = [i for i in items if tag.lower() in [t.lower() for t in i.get("tags", [])]]
    if source:
        items = [i for i in items if i.get("source_account", "").lower() == source.lower()]
    return {"count": len(items), "items": items}


@router.post("/swipe-file")
async def add_to_swipe_file(
    source_account: str = "",
    content_url: str = "",
    content_type: str = "reel",
    caption: str = "",
    thumbnail_url: str = "",
    plays: int = 0,
    likes: int = 0,
    comments: int = 0,
    notes: str = "",
    tags: str = "",
    why_saved: str = "",
):
    """Save a piece of competitor content to your swipe file for inspiration."""
    items = _load_swipe_file()
    entry = {
        "id": f"swipe_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(items)}",
        "source_account": source_account,
        "content_url": content_url,
        "content_type": content_type,
        "caption": caption[:500] if caption else "",
        "thumbnail_url": thumbnail_url,
        "plays": plays,
        "likes": likes,
        "comments": comments,
        "notes": notes,
        "tags": [t.strip() for t in tags.split(",") if t.strip()] if tags else [],
        "why_saved": why_saved,
        "saved_at": datetime.now().isoformat(),
    }
    items.append(entry)
    _save_swipe_file(items)
    return {"status": "saved", "item": entry}


@router.patch("/swipe-file/{item_id}")
async def update_swipe_item(
    item_id: str,
    notes: str = "",
    tags: str = "",
    why_saved: str = "",
):
    """Update notes/tags on a swipe file entry."""
    items = _load_swipe_file()
    target = next((i for i in items if i.get("id") == item_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Swipe item not found")
    if notes:
        target["notes"] = notes
    if tags:
        target["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
    if why_saved:
        target["why_saved"] = why_saved
    _save_swipe_file(items)
    return {"status": "updated", "item": target}


@router.delete("/swipe-file/{item_id}")
async def delete_swipe_item(item_id: str):
    """Remove an entry from the swipe file."""
    items = _load_swipe_file()
    items = [i for i in items if i.get("id") != item_id]
    _save_swipe_file(items)
    return {"status": "deleted"}


# =============================================================================
# TRENDING AUDIO TRACKER - aggregate audio from competitor reels
# =============================================================================

@router.get("/trending-audio")
async def get_trending_audio(limit: int = 30):
    """
    Aggregate audio/sound data from all tracked competitor reels.
    Shows which sounds are most used and their associated engagement.
    """
    service = get_competitor_service()
    all_accounts = service.get_stored_accounts()
    audio_map: Dict[str, Dict[str, Any]] = {}

    for username in all_accounts:
        reels_dir = service.storage_dir / "accounts" / username / "reels"
        if not reels_dir.exists():
            continue
        for reel_file in reels_dir.glob("*.json"):
            try:
                with open(reel_file) as f:
                    reel = json.load(f)
                audio_title = reel.get("audio_title") or reel.get("music_title") or ""
                audio_artist = reel.get("audio_artist") or reel.get("music_artist") or ""
                audio_id = reel.get("audio_id") or reel.get("music_id") or ""
                is_original = reel.get("is_original_audio", False)
                if not audio_title:
                    continue
                key = f"{audio_title}|{audio_artist}".lower()
                if key not in audio_map:
                    audio_map[key] = {
                        "audio_title": audio_title,
                        "audio_artist": audio_artist,
                        "audio_id": audio_id,
                        "is_original_audio": is_original,
                        "used_by": set(),
                        "total_plays": 0,
                        "total_likes": 0,
                        "count": 0,
                    }
                audio_map[key]["used_by"].add(username)
                audio_map[key]["total_plays"] += reel.get("play_count", 0)
                audio_map[key]["total_likes"] += reel.get("like_count", 0)
                audio_map[key]["count"] += 1
            except Exception:
                continue

    # Sort by usage count, convert sets to lists
    sorted_audio = sorted(audio_map.values(), key=lambda a: a["count"], reverse=True)[:limit]
    for a in sorted_audio:
        a["used_by"] = list(a["used_by"])
        a["avg_plays"] = round(a["total_plays"] / max(a["count"], 1))
        a["avg_likes"] = round(a["total_likes"] / max(a["count"], 1))

    original_count = sum(1 for a in sorted_audio if a.get("is_original_audio"))
    return {
        "total_unique_audio": len(audio_map),
        "showing": len(sorted_audio),
        "original_audio_pct": round(original_count / max(len(sorted_audio), 1) * 100, 1),
        "audio": sorted_audio,
    }


# =============================================================================
# HASHTAG STRATEGY BUILDER - build and save optimized hashtag sets
# =============================================================================

def _load_hashtag_sets() -> List[Dict[str, Any]]:
    service = get_competitor_service()
    path = service.storage_dir / "hashtag_sets.json"
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_hashtag_sets(sets: List[Dict[str, Any]]):
    service = get_competitor_service()
    path = service.storage_dir / "hashtag_sets.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(sets, f, indent=2)


@router.get("/hashtag-sets")
async def get_hashtag_sets():
    """Get all saved hashtag strategy sets."""
    sets = _load_hashtag_sets()
    return {"count": len(sets), "sets": sets}


@router.post("/hashtag-sets")
async def create_hashtag_set(
    name: str = "Default Set",
    description: str = "",
    hashtags: str = "",
    category: str = "general",
):
    """Create a new hashtag strategy set."""
    sets = _load_hashtag_sets()
    tag_list = [t.strip().lstrip("#") for t in hashtags.split(",") if t.strip()]
    entry = {
        "id": f"hset_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(sets)}",
        "name": name,
        "description": description,
        "hashtags": tag_list,
        "category": category,
        "times_used": 0,
        "created_at": datetime.now().isoformat(),
    }
    sets.append(entry)
    _save_hashtag_sets(sets)
    return {"status": "created", "set": entry}


@router.post("/hashtag-sets/generate")
async def generate_hashtag_set(
    niche: str = "personal branding",
    content_type: str = "reel",
    theme: str = "",
    count: int = 30,
):
    """
    AI-powered hashtag set generation based on competitor data and niche.
    Builds an optimized mix of high-reach, mid-tier, and niche hashtags.
    """
    import openai

    service = get_competitor_service()
    all_accounts = service.get_stored_accounts()

    # Gather competitor hashtags for context
    comp_hashtags: Dict[str, int] = {}
    for username in all_accounts:
        analysis_path = service.storage_dir / "accounts" / username / "analysis" / "learnings.json"
        if not analysis_path.exists():
            continue
        try:
            with open(analysis_path) as f:
                data = json.load(f)
            for ht in data.get("hashtag_strategy", []):
                if ht:
                    comp_hashtags[ht.lower()] = comp_hashtags.get(ht.lower(), 0) + 1
            for h in data.get("posting_patterns", {}).get("hashtag_frequency", []):
                tag = h.get("tag", "")
                if tag:
                    comp_hashtags[tag.lower()] = comp_hashtags.get(tag.lower(), 0) + h.get("count", 0)
        except Exception:
            continue

    top_comp_tags = sorted(comp_hashtags.items(), key=lambda x: x[1], reverse=True)[:20]
    comp_context = ", ".join([f"#{t} ({c}x)" for t, c in top_comp_tags]) if top_comp_tags else "none found"

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not set")

    client = openai.OpenAI(api_key=api_key)
    prompt = f"""Generate an optimized hashtag set for Instagram {content_type} content.

Niche: {niche}
{f'Theme/topic: {theme}' if theme else ''}
Competitor hashtags: {comp_context}

Create {count} hashtags in 3 tiers:
1. HIGH REACH (10): Popular hashtags with millions of posts (broad discovery)
2. MID TIER (10): Medium-competition hashtags (thousands of posts, targeted)
3. NICHE (10): Low-competition, highly specific hashtags (your unique positioning)

Return as JSON: {{"name": "set name", "hashtags": [{{"tag": "hashtag", "tier": "high|mid|niche", "reasoning": "why"}}]}}
Only return valid JSON, no markdown."""

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        result = json.loads(resp.choices[0].message.content.strip())

        # Save as a new set
        sets = _load_hashtag_sets()
        entry = {
            "id": f"hset_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(sets)}",
            "name": result.get("name", f"{niche} - {content_type}"),
            "description": f"AI-generated for {niche} {content_type}" + (f" ({theme})" if theme else ""),
            "hashtags": [h.get("tag", "") for h in result.get("hashtags", [])],
            "hashtag_details": result.get("hashtags", []),
            "category": "ai_generated",
            "niche": niche,
            "content_type": content_type,
            "times_used": 0,
            "created_at": datetime.now().isoformat(),
        }
        sets.append(entry)
        _save_hashtag_sets(sets)

        return {"status": "generated", "set": entry}
    except Exception as e:
        logger.error(f"Error generating hashtag set: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/hashtag-sets/{set_id}")
async def delete_hashtag_set(set_id: str):
    """Delete a hashtag set."""
    sets = _load_hashtag_sets()
    sets = [s for s in sets if s.get("id") != set_id]
    _save_hashtag_sets(sets)
    return {"status": "deleted"}
