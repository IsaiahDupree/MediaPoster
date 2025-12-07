"""
Screenshot Recorder with Visual Change Detection
Captures periodic screenshots and saves only when significant changes are detected.
"""
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from loguru import logger

try:
    from PIL import Image
    import imagehash
    IMAGING_AVAILABLE = True
except ImportError:
    IMAGING_AVAILABLE = False
    logger.warning("PIL/imagehash not installed. Screenshot change detection limited.")


class ScreenshotRecorder:
    """
    Records screenshots at intervals, saving only when visual changes are detected.
    Uses perceptual hashing to efficiently compare screenshots.
    """
    
    def __init__(self,
                 output_dir: Path,
                 interval: float = 2.0,
                 change_threshold: int = 10,
                 max_screenshots: int = 100):
        """
        Initialize the screenshot recorder.
        
        Args:
            output_dir: Directory to save screenshots
            interval: Seconds between screenshot captures
            change_threshold: Hash difference threshold for "significant" change (0-64)
                             Lower = more sensitive, Higher = less sensitive
            max_screenshots: Maximum number of screenshots to keep
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.interval = interval
        self.change_threshold = change_threshold
        self.max_screenshots = max_screenshots
        
        self.is_recording = False
        self.screenshots: List[Dict] = []
        self._counter = 0
        self._last_hash: Optional['imagehash.ImageHash'] = None
        self._task: Optional[asyncio.Task] = None
        self.start_time: Optional[datetime] = None
    
    def _capture_safari_window(self) -> Optional[Path]:
        """
        Capture a screenshot of the Safari window.
        
        Returns:
            Path to the screenshot file, or None if capture failed.
        """
        self._counter += 1
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Include milliseconds
        filename = f"screen_{self._counter:04d}_{timestamp}.png"
        filepath = self.output_dir / filename
        
        try:
            # First, try to get Safari window ID
            script = '''
            tell application "Safari"
                if (count of windows) > 0 then
                    tell front window
                        return id
                    end tell
                end if
            end tell
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            window_id = result.stdout.strip()
            
            if window_id:
                # Capture specific Safari window
                capture_result = subprocess.run(
                    ["screencapture", "-l", window_id, str(filepath)],
                    capture_output=True,
                    timeout=5
                )
                if capture_result.returncode == 0 and filepath.exists():
                    return filepath
            
            # Fallback: capture full screen
            subprocess.run(
                ["screencapture", "-x", str(filepath)],  # -x for silent
                capture_output=True,
                timeout=5
            )
            
            if filepath.exists():
                return filepath
            return None
            
        except subprocess.TimeoutExpired:
            logger.debug("Screenshot capture timed out")
            return None
        except Exception as e:
            logger.debug(f"Screenshot capture error: {e}")
            return None
    
    def _compute_hash(self, image_path: Path) -> Optional['imagehash.ImageHash']:
        """
        Compute perceptual hash of an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            ImageHash object, or None if computation failed.
        """
        if not IMAGING_AVAILABLE:
            return None
        
        try:
            img = Image.open(image_path)
            return imagehash.phash(img)
        except Exception as e:
            logger.debug(f"Hash computation error: {e}")
            return None
    
    def _is_significant_change(self, current_hash: 'imagehash.ImageHash') -> bool:
        """
        Check if the current screenshot is significantly different from the last.
        
        Args:
            current_hash: Hash of the current screenshot
            
        Returns:
            True if significant change detected, False otherwise.
        """
        if self._last_hash is None:
            return True  # First screenshot is always significant
        
        # Compute hamming distance between hashes
        distance = current_hash - self._last_hash
        return distance >= self.change_threshold
    
    async def _capture_loop(self):
        """Main capture loop running at specified interval."""
        while self.is_recording:
            try:
                # Capture screenshot
                screenshot_path = self._capture_safari_window()
                
                if screenshot_path:
                    # Compute hash and check for changes
                    current_hash = self._compute_hash(screenshot_path)
                    
                    if current_hash is None:
                        # No hash available, keep screenshot anyway
                        self._record_screenshot(screenshot_path, "no_hash")
                    elif self._is_significant_change(current_hash):
                        # Significant change detected
                        self._record_screenshot(screenshot_path, "change_detected")
                        self._last_hash = current_hash
                    else:
                        # No significant change, delete the screenshot
                        try:
                            screenshot_path.unlink()
                        except:
                            pass
                
                # Enforce max screenshots limit
                self._enforce_limit()
                
            except Exception as e:
                logger.debug(f"Screenshot loop error: {e}")
            
            await asyncio.sleep(self.interval)
    
    def _record_screenshot(self, path: Path, reason: str):
        """Record a captured screenshot."""
        timestamp = datetime.now()
        relative_time = None
        if self.start_time:
            relative_time = (timestamp - self.start_time).total_seconds()
        
        record = {
            "path": str(path),
            "filename": path.name,
            "timestamp": timestamp.isoformat(),
            "relative_time": relative_time,
            "reason": reason
        }
        
        self.screenshots.append(record)
        logger.debug(f"📸 Screenshot saved: {path.name} ({reason})")
    
    def _enforce_limit(self):
        """Delete oldest screenshots if limit exceeded."""
        while len(self.screenshots) > self.max_screenshots:
            oldest = self.screenshots.pop(0)
            try:
                Path(oldest["path"]).unlink()
            except:
                pass
    
    async def start(self) -> bool:
        """
        Start the screenshot recorder.
        
        Returns:
            True if started successfully.
        """
        if self.is_recording:
            logger.warning("Screenshot recorder already running")
            return True
        
        self.is_recording = True
        self.start_time = datetime.now()
        self.screenshots = []
        self._counter = 0
        self._last_hash = None
        
        # Start capture loop
        self._task = asyncio.create_task(self._capture_loop())
        
        logger.success(f"✅ Screenshot recorder started (interval: {self.interval}s, threshold: {self.change_threshold})")
        return True
    
    async def stop(self) -> List[Dict]:
        """
        Stop the screenshot recorder.
        
        Returns:
            List of captured screenshot records.
        """
        if not self.is_recording:
            return self.screenshots
        
        self.is_recording = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        logger.info(f"Screenshot recorder stopped. Captured {len(self.screenshots)} screenshots.")
        return self.screenshots
    
    def capture_now(self, name: str = "manual") -> Optional[Dict]:
        """
        Capture a screenshot immediately (bypasses change detection).
        
        Args:
            name: Tag for this screenshot
            
        Returns:
            Screenshot record, or None if capture failed.
        """
        screenshot_path = self._capture_safari_window()
        
        if screenshot_path:
            # Update hash
            current_hash = self._compute_hash(screenshot_path)
            if current_hash:
                self._last_hash = current_hash
            
            self._record_screenshot(screenshot_path, name)
            return self.screenshots[-1]
        
        return None
    
    def get_screenshots(self) -> List[Dict]:
        """Get all captured screenshot records."""
        return list(self.screenshots)
    
    def get_new_screenshots(self, since_index: int = 0) -> List[Dict]:
        """Get screenshots captured since the given index."""
        return self.screenshots[since_index:]
    
    def get_summary(self) -> Dict:
        """Get summary of captured screenshots."""
        return {
            "total_captured": len(self.screenshots),
            "output_dir": str(self.output_dir),
            "interval_seconds": self.interval,
            "change_threshold": self.change_threshold,
            "duration_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else None
        }


# Test function
async def test_screenshot_recorder():
    """Test the screenshot recorder."""
    output_dir = Path(__file__).parent / "test_screenshots"
    output_dir.mkdir(exist_ok=True)
    
    print(f"Testing screenshot recorder (saving to {output_dir})...")
    print("Open Safari and interact for 10 seconds...")
    print()
    
    recorder = ScreenshotRecorder(
        output_dir=output_dir,
        interval=2.0,
        change_threshold=5
    )
    
    await recorder.start()
    await asyncio.sleep(10)
    screenshots = await recorder.stop()
    
    print(f"\nCaptured {len(screenshots)} screenshots:")
    for ss in screenshots:
        print(f"  {ss['filename']} ({ss['reason']})")
    
    print(f"\nSummary: {recorder.get_summary()}")


if __name__ == "__main__":
    asyncio.run(test_screenshot_recorder())
