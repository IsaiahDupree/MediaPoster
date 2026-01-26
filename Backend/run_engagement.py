#!/usr/bin/env python3
"""
Continuous Engagement Runner
=============================
Runs the engagement automation continuously with console logging.

Usage:
    python run_engagement.py
"""
import os
import sys
import asyncio

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Configure logging BEFORE imports
from loguru import logger
import logging

# Remove default handler and add console handler with colors
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="DEBUG",
    colorize=True
)

# Also capture standard logging
logging.basicConfig(level=logging.INFO)


async def main():
    """Run engagement automation."""
    print("\n" + "="*60)
    print("🚀 ENGAGEMENT AUTOMATION STARTING")
    print("="*60 + "\n")
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not set!")
        return
    print(f"✅ OpenAI API key loaded ({api_key[:10]}...)")
    
    # Import controller
    from services.engagement.engagement_controller import EngagementController
    
    # Get singleton instance
    controller = EngagementController.get_instance()
    
    print(f"📊 Current state: {controller.state.value}")
    print(f"🔧 Platforms: {list(controller.platform_stats.keys())}")
    print(f"⏱️  Rate limit: {controller.COMMENTS_PER_HOUR_PER_PLATFORM} comments/hour/platform")
    print(f"🔄 Auto-resume: {controller.auto_resume_enabled} (after {controller.auto_resume_after_hours}h idle)")
    print()
    
    # Start automation
    result = await controller.start()
    print(f"📢 Start result: {result}")
    
    # Keep running
    print("\n" + "="*60)
    print("🔄 RUNNING CONTINUOUSLY - Press Ctrl+C to stop")
    print("="*60 + "\n")
    
    try:
        while True:
            # Print status every 30 seconds
            await asyncio.sleep(30)
            status = controller.get_status()
            print(f"📊 Status: {status.state.value} | Comments today: {status.total_comments_today} | Idle: {status.idle_minutes:.1f}m")
    except KeyboardInterrupt:
        print("\n⏹️  Stopping...")
        await controller.stop()
        print("✅ Stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
