"""
Sora Browser Automation - Safari automation for sora.com video generation
Uses AppleScript to control Safari browser for:
1. Navigate to sora.com
2. Login (if needed)
3. Input prompts
4. Generate videos
5. Download completed videos
"""

import asyncio
import subprocess
import time
import os
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Import centralized Safari session manager
try:
    from automation.safari_session_manager import SafariSessionManager, Platform
    HAS_SESSION_MANAGER = True
except ImportError:
    try:
        from safari_session_manager import SafariSessionManager, Platform
        HAS_SESSION_MANAGER = True
    except ImportError:
        HAS_SESSION_MANAGER = False

SORA_URL = "https://sora.com"
DOWNLOAD_DIR = Path("/Users/isaiahdupree/Documents/CompetitorResearch/sora_downloads")


@dataclass
class SoraGenerationJob:
    id: str
    prompt: str
    duration: int  # seconds
    aspect_ratio: str  # "9:16", "16:9", "1:1"
    status: str  # pending, generating, completed, failed
    video_path: Optional[str] = None
    error: Optional[str] = None
    created_at: str = None
    completed_at: str = None


class SoraBrowserAutomation:
    """Safari-based automation for Sora video generation"""
    
    def __init__(self):
        self.download_dir = DOWNLOAD_DIR
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.jobs_file = self.download_dir / "jobs.json"
        self.jobs: List[SoraGenerationJob] = []
        self._load_jobs()
        
        # Session manager for login verification
        self.session_manager = SafariSessionManager() if HAS_SESSION_MANAGER else None
    
    def require_login(self) -> bool:
        """Check if logged into Sora before automation."""
        if self.session_manager:
            return self.session_manager.require_login(Platform.SORA)
        logger.warning("Session manager not available, assuming logged in")
        return True
    
    def _load_jobs(self):
        """Load jobs from file"""
        if self.jobs_file.exists():
            with open(self.jobs_file) as f:
                data = json.load(f)
                self.jobs = [SoraGenerationJob(**j) for j in data]
    
    def _save_jobs(self):
        """Save jobs to file"""
        with open(self.jobs_file, "w") as f:
            json.dump([vars(j) for j in self.jobs], f, indent=2)
    
    def _run_applescript(self, script: str) -> tuple[bool, str]:
        """Execute AppleScript and return success status and output"""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Script timed out"
        except Exception as e:
            return False, str(e)
    
    def open_sora(self) -> bool:
        """Open Safari and navigate to Sora"""
        script = f'''
        tell application "Safari"
            activate
            if (count of windows) = 0 then
                make new document
            end if
            set URL of front document to "{SORA_URL}"
        end tell
        
        delay 3
        return "opened"
        '''
        success, output = self._run_applescript(script)
        logger.info(f"Open Sora: {success} - {output}")
        return success
    
    def check_login_status(self) -> bool:
        """Check if logged into Sora"""
        script = '''
        tell application "Safari"
            set pageURL to URL of front document
            set pageContent to do JavaScript "document.body.innerText" in front document
        end tell
        
        if pageContent contains "Sign in" or pageContent contains "Log in" then
            return "not_logged_in"
        else
            return "logged_in"
        end if
        '''
        success, output = self._run_applescript(script)
        return success and output == "logged_in"
    
    def wait_for_login(self, timeout: int = 120) -> bool:
        """Wait for user to complete login"""
        logger.info("Waiting for user to log in to Sora...")
        start = time.time()
        while time.time() - start < timeout:
            if self.check_login_status():
                logger.info("✅ Login detected")
                return True
            time.sleep(3)
        logger.error("❌ Login timeout")
        return False
    
    def navigate_to_create(self) -> bool:
        """Navigate to the create/generate page"""
        script = '''
        tell application "Safari"
            -- Click on Create button or navigate to create page
            do JavaScript "
                // Look for create button
                const createBtn = document.querySelector('a[href*=\"create\"], button:contains(\"Create\")');
                if (createBtn) {
                    createBtn.click();
                } else {
                    // Try direct navigation
                    window.location.href = window.location.origin + '/create';
                }
            " in front document
        end tell
        
        delay 2
        return "navigated"
        '''
        success, output = self._run_applescript(script)
        return success
    
    def input_prompt(self, prompt: str, duration: int = 5, aspect_ratio: str = "9:16") -> bool:
        """Input prompt into Sora's text field"""
        # Escape special characters for AppleScript/JavaScript
        escaped_prompt = prompt.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'").replace("\n", " ")
        
        script = f'''
        tell application "Safari"
            -- Find and fill the prompt textarea
            do JavaScript "
                // Find prompt input
                const promptInput = document.querySelector('textarea[placeholder*=\"prompt\"], textarea[name*=\"prompt\"], textarea.prompt-input, [contenteditable=\"true\"]');
                if (promptInput) {{
                    promptInput.value = '{escaped_prompt}';
                    promptInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    'prompt_entered';
                }} else {{
                    'prompt_input_not_found';
                }}
            " in front document
        end tell
        '''
        success, output = self._run_applescript(script)
        logger.info(f"Input prompt: {success} - {output}")
        return success and "entered" in output.lower()
    
    def set_video_settings(self, duration: int = 5, aspect_ratio: str = "9:16") -> bool:
        """Set video duration and aspect ratio"""
        script = f'''
        tell application "Safari"
            do JavaScript "
                // Set duration if dropdown exists
                const durationSelect = document.querySelector('select[name*=\"duration\"], [data-duration]');
                if (durationSelect) {{
                    durationSelect.value = '{duration}';
                    durationSelect.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                
                // Set aspect ratio
                const aspectBtns = document.querySelectorAll('[data-aspect-ratio], button[aria-label*=\"{aspect_ratio}\"]');
                aspectBtns.forEach(btn => {{
                    if (btn.textContent.includes('{aspect_ratio}') || btn.getAttribute('data-aspect-ratio') === '{aspect_ratio}') {{
                        btn.click();
                    }}
                }});
                
                'settings_applied';
            " in front document
        end tell
        '''
        success, output = self._run_applescript(script)
        return success
    
    def click_generate(self) -> bool:
        """Click the generate button"""
        script = '''
        tell application "Safari"
            do JavaScript "
                // Find generate button
                const genBtn = document.querySelector('button[type=\"submit\"], button:contains(\"Generate\"), button.generate-btn, [data-action=\"generate\"]');
                if (genBtn && !genBtn.disabled) {
                    genBtn.click();
                    'generate_clicked';
                } else {
                    'generate_button_not_found';
                }
            " in front document
        end tell
        '''
        success, output = self._run_applescript(script)
        logger.info(f"Click generate: {success} - {output}")
        return success and "clicked" in output.lower()
    
    def wait_for_generation(self, timeout: int = 300) -> tuple[bool, Optional[str]]:
        """Wait for video generation to complete and return video URL"""
        logger.info("Waiting for video generation...")
        start = time.time()
        
        while time.time() - start < timeout:
            script = '''
            tell application "Safari"
                do JavaScript "
                    // Check for completed video
                    const videoEl = document.querySelector('video[src], source[src*=\".mp4\"]');
                    const downloadBtn = document.querySelector('a[download], button[aria-label*=\"download\"], [data-action=\"download\"]');
                    
                    if (videoEl && videoEl.src) {
                        'completed:' + videoEl.src;
                    } else if (downloadBtn) {
                        const href = downloadBtn.href || downloadBtn.getAttribute('data-url');
                        if (href) 'completed:' + href;
                        else 'generating';
                    } else {
                        // Check for error
                        const errorEl = document.querySelector('.error, [role=\"alert\"]');
                        if (errorEl && errorEl.textContent.toLowerCase().includes('error')) {
                            'error:' + errorEl.textContent;
                        } else {
                            'generating';
                        }
                    }
                " in front document
            end tell
            '''
            success, output = self._run_applescript(script)
            
            if "completed:" in output:
                video_url = output.split("completed:")[1].strip()
                logger.info(f"✅ Generation complete: {video_url[:50]}...")
                return True, video_url
            elif "error:" in output:
                error_msg = output.split("error:")[1].strip()
                logger.error(f"❌ Generation error: {error_msg}")
                return False, error_msg
            
            time.sleep(5)
        
        logger.error("❌ Generation timeout")
        return False, "Timeout waiting for generation"
    
    def download_video(self, video_url: str, filename: str) -> Optional[str]:
        """Download the generated video"""
        output_path = self.download_dir / filename
        
        # Try using Safari's download functionality
        script = f'''
        tell application "Safari"
            do JavaScript "
                const link = document.createElement('a');
                link.href = '{video_url}';
                link.download = '{filename}';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                'download_triggered';
            " in front document
        end tell
        '''
        success, output = self._run_applescript(script)
        
        if success:
            # Wait for download
            time.sleep(5)
            
            # Check Downloads folder
            downloads = Path.home() / "Downloads"
            for f in downloads.glob(f"*{filename}*"):
                # Move to our folder
                dest = output_path
                f.rename(dest)
                logger.info(f"✅ Downloaded: {dest}")
                return str(dest)
        
        # Fallback: use curl
        try:
            subprocess.run(
                ["curl", "-L", "-o", str(output_path), video_url],
                capture_output=True,
                timeout=120
            )
            if output_path.exists():
                logger.info(f"✅ Downloaded via curl: {output_path}")
                return str(output_path)
        except Exception as e:
            logger.error(f"Download error: {e}")
        
        return None
    
    async def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "9:16",
        job_id: Optional[str] = None
    ) -> SoraGenerationJob:
        """Full generation flow: open → prompt → generate → download"""
        
        job = SoraGenerationJob(
            id=job_id or f"sora_{int(time.time())}",
            prompt=prompt[:200],  # Truncate for storage
            duration=duration,
            aspect_ratio=aspect_ratio,
            status="pending",
            created_at=datetime.now().isoformat()
        )
        self.jobs.append(job)
        self._save_jobs()
        
        try:
            # Step 1: Open Sora
            logger.info("Step 1: Opening Sora...")
            if not self.open_sora():
                raise Exception("Failed to open Sora")
            await asyncio.sleep(3)
            
            # Step 2: Check login
            logger.info("Step 2: Checking login...")
            if not self.check_login_status():
                logger.info("⚠️ Not logged in - waiting for manual login...")
                if not self.wait_for_login(timeout=120):
                    raise Exception("Login timeout")
            
            # Step 3: Navigate to create
            logger.info("Step 3: Navigating to create...")
            self.navigate_to_create()
            await asyncio.sleep(2)
            
            # Step 4: Input prompt
            logger.info("Step 4: Entering prompt...")
            job.status = "generating"
            self._save_jobs()
            
            if not self.input_prompt(prompt, duration, aspect_ratio):
                raise Exception("Failed to input prompt")
            await asyncio.sleep(1)
            
            # Step 5: Set settings
            logger.info("Step 5: Setting video options...")
            self.set_video_settings(duration, aspect_ratio)
            await asyncio.sleep(1)
            
            # Step 6: Generate
            logger.info("Step 6: Starting generation...")
            if not self.click_generate():
                raise Exception("Failed to click generate")
            
            # Step 7: Wait for completion
            logger.info("Step 7: Waiting for generation...")
            success, result = self.wait_for_generation(timeout=300)
            
            if not success:
                raise Exception(result)
            
            # Step 8: Download
            logger.info("Step 8: Downloading video...")
            filename = f"{job.id}.mp4"
            video_path = self.download_video(result, filename)
            
            if not video_path:
                raise Exception("Failed to download video")
            
            job.status = "completed"
            job.video_path = video_path
            job.completed_at = datetime.now().isoformat()
            self._save_jobs()
            
            logger.info(f"✅ Generation complete: {video_path}")
            return job
            
        except Exception as e:
            logger.error(f"❌ Generation failed: {e}")
            job.status = "failed"
            job.error = str(e)
            self._save_jobs()
            return job
    
    def get_pending_jobs(self) -> List[SoraGenerationJob]:
        """Get jobs that are pending generation"""
        return [j for j in self.jobs if j.status == "pending"]
    
    def get_job(self, job_id: str) -> Optional[SoraGenerationJob]:
        """Get a specific job by ID"""
        for job in self.jobs:
            if job.id == job_id:
                return job
        return None


class SoraScheduler:
    """Scheduler for automated Sora video generation"""
    
    def __init__(self):
        self.automation = SoraBrowserAutomation()
        self.schedule_file = DOWNLOAD_DIR / "schedule.json"
        self.running = False
    
    def add_scheduled_job(
        self,
        prompt: str,
        scheduled_time: datetime,
        duration: int = 5,
        aspect_ratio: str = "9:16"
    ) -> str:
        """Add a job to the schedule"""
        job_id = f"scheduled_{int(time.time())}"
        
        schedule = self._load_schedule()
        schedule.append({
            "job_id": job_id,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "scheduled_time": scheduled_time.isoformat(),
            "status": "scheduled"
        })
        self._save_schedule(schedule)
        
        return job_id
    
    def _load_schedule(self) -> List[Dict]:
        """Load schedule from file"""
        if self.schedule_file.exists():
            with open(self.schedule_file) as f:
                return json.load(f)
        return []
    
    def _save_schedule(self, schedule: List[Dict]):
        """Save schedule to file"""
        with open(self.schedule_file, "w") as f:
            json.dump(schedule, f, indent=2)
    
    async def run_scheduler(self):
        """Run the scheduler loop"""
        self.running = True
        logger.info("🕐 Sora scheduler started")
        
        while self.running:
            schedule = self._load_schedule()
            now = datetime.now()
            
            for job in schedule:
                if job["status"] != "scheduled":
                    continue
                
                scheduled_time = datetime.fromisoformat(job["scheduled_time"])
                if scheduled_time <= now:
                    logger.info(f"⏰ Running scheduled job: {job['job_id']}")
                    
                    # Update status
                    job["status"] = "running"
                    self._save_schedule(schedule)
                    
                    # Run generation
                    result = await self.automation.generate_video(
                        prompt=job["prompt"],
                        duration=job["duration"],
                        aspect_ratio=job["aspect_ratio"],
                        job_id=job["job_id"]
                    )
                    
                    # Update status
                    job["status"] = result.status
                    job["video_path"] = result.video_path
                    job["error"] = result.error
                    self._save_schedule(schedule)
            
            await asyncio.sleep(60)  # Check every minute
    
    def stop(self):
        """Stop the scheduler"""
        self.running = False


async def main():
    """Test the automation"""
    automation = SoraBrowserAutomation()
    
    # Test prompt
    prompt = """A charismatic Black man in his late 20s with a warm smile walks through 
downtown Pensacola, selfie-style camera angle, natural daylight, vibrant colors, 
casual hoodie and gold chain. He has an expressive, humorous demeanor as he 
gestures at the historic buildings around him. 9:16 vertical format, 5 seconds."""
    
    result = await automation.generate_video(
        prompt=prompt,
        duration=5,
        aspect_ratio="9:16"
    )
    
    print(f"\nResult: {result.status}")
    if result.video_path:
        print(f"Video: {result.video_path}")
    if result.error:
        print(f"Error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
