"""
Test configuration and fixtures for TikTok automation tests.
Includes screenshot capture and detailed logging.
"""
import pytest
import asyncio
import subprocess
import json
from pathlib import Path
from datetime import datetime
import sys
import os

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Test output directories
TEST_OUTPUT_DIR = Path(__file__).parent / "test_output"
SCREENSHOTS_DIR = TEST_OUTPUT_DIR / "screenshots"
LOGS_DIR = TEST_OUTPUT_DIR / "logs"


# ============================================================================
# SETUP
# ============================================================================

def pytest_configure(config):
    """Register custom markers and setup directories."""
    config.addinivalue_line("markers", "e2e: mark test as end-to-end (requires browser)")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "auth: mark test as requiring authentication")
    
    # Create output directories
    TEST_OUTPUT_DIR.mkdir(exist_ok=True)
    SCREENSHOTS_DIR.mkdir(exist_ok=True)
    LOGS_DIR.mkdir(exist_ok=True)


# ============================================================================
# SCREENSHOT CAPTURE
# ============================================================================

class ScreenshotCapture:
    """Utility class for capturing screenshots during tests."""
    
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.screenshot_count = 0
        self.screenshots = []
        self.log_entries = []
        self.start_time = datetime.now()
    
    def capture(self, step_name: str = "") -> str:
        """Capture a screenshot of Safari window."""
        self.screenshot_count += 1
        timestamp = datetime.now().strftime("%H%M%S")
        safe_test_name = self.test_name.replace("/", "_").replace("::", "_").replace("[", "_").replace("]", "").replace(".", "_")
        filename = f"{safe_test_name}_{self.screenshot_count:02d}_{step_name}_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename
        
        try:
            # Use screencapture to capture the front window (Safari)
            result = subprocess.run(
                ["screencapture", "-l$(osascript -e 'tell app \"Safari\" to id of window 1')", str(filepath)],
                capture_output=True,
                text=True,
                shell=True,
                timeout=10
            )
            
            # Fallback: capture the entire screen if window capture fails
            if not filepath.exists():
                subprocess.run(
                    ["screencapture", "-x", str(filepath)],
                    capture_output=True,
                    timeout=10
                )
            
            if filepath.exists():
                self.screenshots.append(str(filepath))
                self.log(f"📸 Screenshot captured: {filename}")
                return str(filepath)
            else:
                self.log(f"⚠️ Screenshot failed for step: {step_name}")
                return ""
                
        except Exception as e:
            self.log(f"❌ Screenshot error: {e}")
            return ""
    
    def capture_safari_window(self, step_name: str = "") -> str:
        """Capture the entire screen including Safari window."""
        self.screenshot_count += 1
        timestamp = datetime.now().strftime("%H%M%S")
        safe_test_name = self.test_name.replace("/", "_").replace("::", "_").replace("[", "_").replace("]", "").replace(".", "_")
        filename = f"{safe_test_name}_{self.screenshot_count:02d}_{step_name}_{timestamp}.png"
        filepath = SCREENSHOTS_DIR / filename
        
        try:
            # Capture the entire screen (not just Safari window)
            subprocess.run(
                ["screencapture", "-x", str(filepath)],
                capture_output=True,
                timeout=10
            )
            
            if filepath.exists():
                self.screenshots.append(str(filepath))
                self.log(f"📸 Screenshot: {filename}")
                return str(filepath)
            else:
                self.log(f"⚠️ Screenshot failed for step: {step_name}")
                return ""
                
        except Exception as e:
            self.log(f"❌ Screenshot error: {e}")
            return ""
    
    def log(self, message: str):
        """Add a log entry."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = f"[{timestamp}] {message}"
        self.log_entries.append(entry)
        print(entry)
    
    def get_safari_url(self) -> str:
        """Get current Safari URL."""
        try:
            script = 'tell application "Safari" to return URL of current tab of front window'
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"
    
    def get_safari_title(self) -> str:
        """Get current Safari page title."""
        try:
            script = 'tell application "Safari" to return name of current tab of front window'
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            return result.stdout.strip() if result.returncode == 0 else "unknown"
        except:
            return "unknown"
    
    def save_report(self, passed: bool, error_msg: str = ""):
        """Save test report with screenshots and logs."""
        duration = (datetime.now() - self.start_time).total_seconds()
        # Replace all path separators and special chars with underscores
        safe_test_name = self.test_name.replace("/", "_").replace("::", "_").replace("[", "_").replace("]", "").replace(".", "_")
        report_file = LOGS_DIR / f"{safe_test_name}_report.json"
        
        report = {
            "test_name": self.test_name,
            "passed": passed,
            "duration_seconds": round(duration, 2),
            "start_time": self.start_time.isoformat(),
            "end_time": datetime.now().isoformat(),
            "screenshot_count": len(self.screenshots),
            "screenshots": self.screenshots,
            "logs": self.log_entries,
            "error": error_msg,
            "final_url": self.get_safari_url(),
            "final_title": self.get_safari_title()
        }
        
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
        
        self.log(f"📄 Report saved: {report_file.name}")
        return str(report_file)


@pytest.fixture
def screenshot(request):
    """Fixture providing screenshot capture for tests."""
    capture = ScreenshotCapture(request.node.nodeid)
    capture.log(f"🧪 Starting test: {request.node.name}")
    yield capture
    
    # Determine pass/fail from test outcome
    passed = True
    error_msg = ""
    if hasattr(request.node, "rep_call"):
        passed = request.node.rep_call.passed
        if not passed and hasattr(request.node.rep_call, "longrepr"):
            error_msg = str(request.node.rep_call.longrepr)
    
    capture.save_report(passed, error_msg)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook to capture test outcome for screenshot fixture."""
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def tmp_session_dir(tmp_path):
    """Create a temporary session directory."""
    session_dir = tmp_path / "sessions"
    session_dir.mkdir()
    return session_dir


@pytest.fixture
def session_manager(tmp_session_dir):
    """Create a session manager with temp directory."""
    from automation.tiktok_session_manager import TikTokSessionManager
    return TikTokSessionManager(session_dir=tmp_session_dir)


@pytest.fixture
def engagement():
    """Create an engagement instance."""
    from automation.tiktok_engagement import TikTokEngagement
    return TikTokEngagement(browser_type="safari", auto_restore_session=False)


@pytest.fixture
async def engagement_with_screenshots(screenshot):
    """Create engagement instance with screenshot capture."""
    from automation.tiktok_engagement import TikTokEngagement
    e = TikTokEngagement(browser_type="safari", auto_restore_session=False)
    e._screenshot = screenshot  # Attach screenshot utility
    screenshot.log("📱 Created TikTokEngagement instance")
    yield e
    await e.cleanup()
    screenshot.capture("cleanup_complete")


# ============================================================================
# ASYNC SUPPORT
# ============================================================================

@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
