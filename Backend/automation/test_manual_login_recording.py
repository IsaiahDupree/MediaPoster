"""
Quick test script to run the manual login recorder
"""
import asyncio
import sys
import signal
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.append(str(Path(__file__).parent.parent))

from automation.tiktok_login_recorder import TikTokLoginRecorder
from loguru import logger

# Global recorder instance for signal handling
recorder_instance = None


async def save_and_exit():
    """Save recording and exit gracefully."""
    global recorder_instance
    if recorder_instance:
        logger.info("\n💾 Saving recording before exit...")
        try:
            await recorder_instance.save_recording()
            await recorder_instance.save_session()
            logger.success("✅ Recording saved successfully!")
        except Exception as e:
            logger.error(f"Error saving recording: {e}")
        finally:
            await recorder_instance.cleanup()
    sys.exit(0)


def signal_handler(signum, frame):
    """Handle signals to save recording before exit."""
    logger.info(f"\n📥 Received signal {signum} - saving recording...")
    asyncio.create_task(save_and_exit())


async def main():
    """Run the manual login recorder."""
    global recorder_instance
    
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Allow browser selection via command line
    browser_type = "safari"  # Default to Safari
    if len(sys.argv) > 1:
        browser_type = sys.argv[1].lower()
        if browser_type not in ["chrome", "safari"]:
            logger.error(f"Invalid browser: {browser_type}. Use 'chrome' or 'safari'")
            return
    
    logger.info("=" * 60)
    logger.info("TikTok Manual Login Recorder")
    logger.info("=" * 60)
    logger.info("")
    logger.info(f"Browser: {browser_type.capitalize()}")
    logger.info("")
    logger.info("This will:")
    logger.info(f"  ✓ Open {browser_type.capitalize()} with your profile")
    logger.info("  ✓ Navigate to TikTok")
    logger.info("  ✓ Watch and record all your manual actions")
    logger.info("  ✓ Detect captchas if they appear")
    logger.info("  ✓ Save the recording when you're done")
    logger.info("")
    logger.info("Press Ctrl+C when login is complete!")
    logger.info("   (Recording will be saved automatically)")
    logger.info("")
    
    recorder = TikTokLoginRecorder(browser_type=browser_type)
    recorder_instance = recorder  # Store for signal handler
    
    try:
        await recorder.start_browser()
        await recorder.monitor_login()
        await recorder.save_recording()
        await recorder.save_session()
        
        logger.success("\n✅ Recording complete!")
        
    except KeyboardInterrupt:
        logger.info("\n⏹️  Stopping recorder...")
        await recorder.save_recording()
        await recorder.save_session()
    except Exception as e:
        logger.error(f"Error: {e}")
        # Try to save anyway
        try:
            await recorder.save_recording()
        except:
            pass
    finally:
        await recorder.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

