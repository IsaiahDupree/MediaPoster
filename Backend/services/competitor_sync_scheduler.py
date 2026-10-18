"""
Competitor Sync Scheduler
Background job to periodically sync competitor accounts and download new content.
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from loguru import logger
import httpx

COMPETITOR_RESEARCH_DIR = Path("/Users/isaiahdupree/Documents/CompetitorResearch")
SCHEDULER_STATE_FILE = COMPETITOR_RESEARCH_DIR / "scheduler_state.json"


class CompetitorSyncScheduler:
    """Scheduler for periodic competitor account syncing."""
    
    def __init__(self, api_base_url: str = "http://localhost:5555"):
        self.api_base_url = api_base_url
        self.sync_interval_hours = 24  # Sync every 24 hours
        self.download_batch_size = 50  # Download 50 videos per sync
        self.running = False
        self.state = self._load_state()
    
    def _load_state(self) -> Dict:
        """Load scheduler state from disk."""
        if SCHEDULER_STATE_FILE.exists():
            with open(SCHEDULER_STATE_FILE) as f:
                return json.load(f)
        return {
            "last_full_sync": None,
            "accounts": {},
            "total_syncs": 0,
            "total_videos_downloaded": 0
        }
    
    def _save_state(self):
        """Save scheduler state to disk."""
        SCHEDULER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SCHEDULER_STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2, default=str)
    
    def get_tracked_accounts(self) -> List[str]:
        """Get list of tracked competitor accounts."""
        accounts_dir = COMPETITOR_RESEARCH_DIR / "accounts"
        if not accounts_dir.exists():
            return []
        
        accounts = []
        for folder in accounts_dir.iterdir():
            if folder.is_dir() and not folder.name.startswith('.'):
                accounts.append(folder.name)
        return accounts
    
    def needs_sync(self, username: str) -> bool:
        """Check if an account needs syncing based on last sync time."""
        account_state = self.state.get("accounts", {}).get(username, {})
        last_sync = account_state.get("last_sync")
        
        if not last_sync:
            return True
        
        last_sync_dt = datetime.fromisoformat(last_sync)
        hours_since_sync = (datetime.now() - last_sync_dt).total_seconds() / 3600
        
        return hours_since_sync >= self.sync_interval_hours
    
    async def sync_account(self, username: str) -> Dict:
        """Sync a single competitor account."""
        logger.info(f"Syncing competitor account: @{username}")
        
        result = {
            "username": username,
            "status": "pending",
            "urls_collected": 0,
            "videos_downloaded": 0,
            "errors": []
        }
        
        async with httpx.AsyncClient(timeout=300) as client:
            try:
                # Step 1: Sync profile and content metadata via API
                sync_resp = await client.post(
                    f"{self.api_base_url}/api/competitors/accounts/{username}/sync"
                )
                if sync_resp.status_code == 200:
                    sync_data = sync_resp.json()
                    logger.info(f"  Profile synced: {sync_data.get('reels_fetched', 0)} reels, {sync_data.get('posts_fetched', 0)} posts")
                else:
                    result["errors"].append(f"Sync failed: {sync_resp.status_code}")
                
                # Step 2: Check scrape status (URLs collected via Safari)
                status_resp = await client.get(
                    f"{self.api_base_url}/api/competitors/accounts/{username}/scrape/status"
                )
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    result["urls_collected"] = status_data.get("urls_collected", 0)
                    result["videos_downloaded"] = status_data.get("videos_downloaded", 0)
                    
                    # Step 3: Download new videos if URLs are available
                    urls_available = status_data.get("urls_collected", 0)
                    videos_have = status_data.get("videos_downloaded", 0)
                    
                    if urls_available > videos_have:
                        logger.info(f"  Downloading new videos ({urls_available - videos_have} pending)...")
                        download_resp = await client.post(
                            f"{self.api_base_url}/api/competitors/accounts/{username}/download",
                            params={"limit": self.download_batch_size}
                        )
                        if download_resp.status_code == 200:
                            dl_data = download_resp.json()
                            result["videos_downloaded"] = dl_data.get("total_videos", 0)
                            logger.info(f"  Downloaded {dl_data.get('new_downloads', 0)} new videos")
                
                # Step 4: Run analysis
                logger.info(f"  Running AI analysis...")
                analysis_resp = await client.post(
                    f"{self.api_base_url}/api/competitors/accounts/{username}/analyze"
                )
                if analysis_resp.status_code == 200:
                    logger.info(f"  Analysis complete")
                
                result["status"] = "completed"
                
            except Exception as e:
                logger.error(f"  Sync error: {e}")
                result["status"] = "error"
                result["errors"].append(str(e))
        
        # Update state
        if "accounts" not in self.state:
            self.state["accounts"] = {}
        
        self.state["accounts"][username] = {
            "last_sync": datetime.now().isoformat(),
            "last_result": result
        }
        self.state["total_syncs"] = self.state.get("total_syncs", 0) + 1
        self._save_state()
        
        return result
    
    async def sync_all_accounts(self) -> Dict:
        """Sync all tracked competitor accounts."""
        accounts = self.get_tracked_accounts()
        logger.info(f"Starting sync for {len(accounts)} competitor accounts")
        
        results = {
            "started_at": datetime.now().isoformat(),
            "accounts_synced": 0,
            "accounts_skipped": 0,
            "total_videos": 0,
            "errors": [],
            "account_results": []
        }
        
        for username in accounts:
            if self.needs_sync(username):
                result = await self.sync_account(username)
                results["account_results"].append(result)
                results["accounts_synced"] += 1
                results["total_videos"] += result.get("videos_downloaded", 0)
                if result.get("errors"):
                    results["errors"].extend(result["errors"])
            else:
                results["accounts_skipped"] += 1
                logger.info(f"Skipping @{username} (recently synced)")
        
        results["finished_at"] = datetime.now().isoformat()
        
        # Update global state
        self.state["last_full_sync"] = datetime.now().isoformat()
        self.state["total_videos_downloaded"] = results["total_videos"]
        self._save_state()
        
        logger.info(f"Sync complete: {results['accounts_synced']} synced, {results['accounts_skipped']} skipped")
        return results
    
    async def run_scheduler(self):
        """Run the background scheduler loop."""
        self.running = True
        logger.info("Competitor sync scheduler started")
        
        while self.running:
            try:
                # Check if any accounts need syncing
                accounts = self.get_tracked_accounts()
                needs_sync = [a for a in accounts if self.needs_sync(a)]
                
                if needs_sync:
                    logger.info(f"{len(needs_sync)} accounts need syncing")
                    await self.sync_all_accounts()
                
                # Wait before next check (1 hour)
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(300)  # Wait 5 minutes on error
        
        logger.info("Competitor sync scheduler stopped")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
    
    def get_status(self) -> Dict:
        """Get current scheduler status."""
        accounts = self.get_tracked_accounts()
        accounts_needing_sync = [a for a in accounts if self.needs_sync(a)]
        
        return {
            "running": self.running,
            "tracked_accounts": len(accounts),
            "accounts_needing_sync": len(accounts_needing_sync),
            "sync_interval_hours": self.sync_interval_hours,
            "last_full_sync": self.state.get("last_full_sync"),
            "total_syncs": self.state.get("total_syncs", 0),
            "total_videos_downloaded": self.state.get("total_videos_downloaded", 0)
        }


# Singleton instance
_scheduler_instance: Optional[CompetitorSyncScheduler] = None


def get_competitor_scheduler() -> CompetitorSyncScheduler:
    """Get the competitor sync scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = CompetitorSyncScheduler()
    return _scheduler_instance


async def start_competitor_scheduler():
    """Start the background competitor scheduler."""
    scheduler = get_competitor_scheduler()
    await scheduler.run_scheduler()
