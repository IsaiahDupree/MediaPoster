"""
Full Sora Video Pipeline Execution
Ingests all cleaned Sora videos, analyzes them, and prepares for posting.
"""
import asyncio
import httpx
from pathlib import Path
from datetime import datetime
from typing import List, Dict
import json

API_BASE = "http://localhost:5555"
SORA_CLEAN_DIR = Path("/Users/isaiahdupree/Documents/SoraVideos/clean")

class SoraPipeline:
    def __init__(self):
        self.results = {
            "ingested": [],
            "analyzed": [],
            "failed": [],
            "skipped": []
        }
        
    async def run(self):
        """Execute full pipeline"""
        print("=" * 80)
        print("SORA VIDEO PIPELINE - FULL EXECUTION")
        print("=" * 80)
        print(f"Source: {SORA_CLEAN_DIR}")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Step 1: Batch ingest
        print("[STEP 1/2] Batch Ingesting Videos...")
        print("-" * 80)
        ingest_result = await self.batch_ingest()
        print(f"✓ Ingest complete: {ingest_result}")
        print()
        
        # Step 2: Batch analyze
        print("[STEP 2/2] Batch Analyzing Videos...")
        print("-" * 80)
        analysis_result = await self.batch_analyze()
        print(f"✓ Analysis started: {analysis_result}")
        print()
        
        # Monitor analysis progress
        await self.monitor_analysis(analysis_result.get("job_id"))
        
        # Final summary
        self.print_summary()
        
    async def batch_ingest(self) -> Dict:
        """Batch ingest all videos from clean directory"""
        async with httpx.AsyncClient(timeout=300) as client:
            try:
                response = await client.post(
                    f"{API_BASE}/api/media-db/batch/ingest",
                    json={
                        "directory_path": str(SORA_CLEAN_DIR),
                        "recursive": False,
                        "resume": True
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                print(f"  Job ID: {result.get('job_id')}")
                print(f"  Total files: {result.get('total_files')}")
                print(f"  Status: {result.get('status')}")
                
                return result
                
            except Exception as e:
                print(f"  ❌ Ingest failed: {e}")
                return {"error": str(e)}
    
    async def batch_analyze(self) -> Dict:
        """Batch analyze all ingested videos"""
        async with httpx.AsyncClient(timeout=300) as client:
            try:
                response = await client.post(
                    f"{API_BASE}/api/media-db/batch/analyze",
                    json={
                        "limit": 100,
                        "skip_analyzed": True
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                print(f"  Job ID: {result.get('job_id')}")
                print(f"  Total videos: {result.get('total_videos')}")
                print(f"  Status: {result.get('status')}")
                
                return result
                
            except Exception as e:
                print(f"  ❌ Analysis failed: {e}")
                return {"error": str(e)}
    
    async def monitor_analysis(self, job_id: str):
        """Monitor analysis progress"""
        if not job_id:
            print("  ⚠️ No job ID to monitor")
            return
        
        print()
        print("[MONITORING] Analysis Progress...")
        print("-" * 80)
        
        async with httpx.AsyncClient(timeout=60) as client:
            last_completed = 0
            last_status = None
            
            while True:
                try:
                    response = await client.get(
                        f"{API_BASE}/api/media-db/batch/analyze/status/{job_id}"
                    )
                    
                    if response.status_code == 200:
                        status = response.json()
                        
                        completed = status.get("completed", 0)
                        total = status.get("total", 0)
                        current_status = status.get("status")
                        current_video = status.get("current_filename", "")
                        current_step = status.get("current_step", "")
                        
                        # Only print if something changed
                        if completed != last_completed or current_status != last_status:
                            progress_pct = (completed / total * 100) if total > 0 else 0
                            print(f"  [{completed}/{total}] {progress_pct:.1f}% | {current_status}")
                            if current_video:
                                print(f"    → {current_video} ({current_step})")
                            
                            last_completed = completed
                            last_status = current_status
                        
                        # Check if done
                        if current_status in ["completed", "failed"]:
                            print()
                            print(f"  ✓ Analysis {current_status}")
                            print(f"    Completed: {completed}/{total}")
                            print(f"    Failed: {status.get('failed', 0)}")
                            break
                    
                    await asyncio.sleep(5)  # Check every 5 seconds
                    
                except Exception as e:
                    print(f"  ⚠️ Monitoring error: {e}")
                    await asyncio.sleep(10)
    
    async def get_analyzed_videos(self) -> List[Dict]:
        """Get list of analyzed videos"""
        async with httpx.AsyncClient(timeout=60) as client:
            try:
                response = await client.get(
                    f"{API_BASE}/api/media-db/list",
                    params={
                        "limit": 100,
                        "analyzed_only": True
                    }
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"  ❌ Failed to get analyzed videos: {e}")
                return []
    
    def print_summary(self):
        """Print final summary"""
        print()
        print("=" * 80)
        print("PIPELINE EXECUTION COMPLETE")
        print("=" * 80)
        print()
        print("Next Steps:")
        print("  1. Review analyzed videos in dashboard: http://localhost:5557")
        print("  2. Check generated titles and scores")
        print("  3. Schedule posts to YouTube via API or dashboard")
        print()
        print("API Endpoints:")
        print(f"  - List analyzed: GET {API_BASE}/api/media-db/list?analyzed_only=true")
        print(f"  - Get details: GET {API_BASE}/api/media-db/detail/{{media_id}}")
        print(f"  - Schedule post: POST {API_BASE}/api/schedule/create")
        print()

async def main():
    pipeline = SoraPipeline()
    await pipeline.run()

if __name__ == "__main__":
    asyncio.run(main())
