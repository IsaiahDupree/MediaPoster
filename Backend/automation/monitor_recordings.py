"""
Monitor recordings in real-time and show what's being recorded.
"""
import json
import time
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger


def monitor_live_recording():
    """Monitor the recorder process and show actions as they happen."""
    recordings_dir = Path(__file__).parent / "recordings"
    recordings_dir.mkdir(exist_ok=True)
    
    print("🔍 Monitoring for new recordings...")
    print("   (The recorder saves when you press Ctrl+C or login completes)\n")
    
    # Check for existing recordings
    existing = list(recordings_dir.glob("login_recording_*.json"))
    last_count = len(existing)
    
    print(f"📁 Current recordings: {last_count}")
    
    if existing:
        print("\n📖 Most recent recording preview:\n")
        try:
            with open(existing[-1], 'r') as f:
                data = json.load(f)
            
            actions = data.get('actions', [])
            print(f"   Total actions: {len(actions)}")
            print(f"   Duration: {data.get('duration_seconds', 0):.1f}s")
            
            if actions:
                print("\n   Recent actions:")
                for action in actions[-5:]:  # Last 5 actions
                    action_type = action.get('type', 'unknown')
                    details = action.get('details', {})
                    desc = details.get('description', '')[:50]
                    print(f"     • {action_type}: {desc}")
        except Exception as e:
            print(f"   Error reading: {e}")
    
    print("\n💡 Tips:")
    print("   - Recordings are saved when the recorder stops")
    print("   - Press Ctrl+C in the recorder to save current progress")
    print("   - Run: python3 automation/review_recordings.py to view full recordings")
    print("\n⏳ Waiting for new recordings... (Press Ctrl+C to exit)")


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")
    
    try:
        monitor_live_recording()
        # Keep monitoring
        while True:
            time.sleep(5)
            recordings_dir = Path(__file__).parent / "recordings"
            current = list(recordings_dir.glob("login_recording_*.json"))
            if len(current) > 0:
                print(f"\n✅ New recording detected! Run review_recordings.py to view it.")
                break
    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped")


