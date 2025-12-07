"""
Review and display login recordings in a readable format.
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from loguru import logger


def format_timestamp(iso_string: str) -> str:
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(iso_string.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_string


def format_duration(seconds: float) -> str:
    """Format duration in seconds to readable format."""
    if seconds is None:
        return "N/A"
    
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    
    if minutes > 0:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


def display_recording(recording_file: Path):
    """Display a recording file in a readable format."""
    try:
        with open(recording_file, 'r') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading recording file: {e}")
        return
    
    print("\n" + "=" * 80)
    print(f"📹 LOGIN RECORDING REVIEW")
    print("=" * 80)
    print(f"\n📁 File: {recording_file.name}")
    print(f"🕐 Recorded: {format_timestamp(data.get('recorded_at', ''))}")
    print(f"⏱️  Duration: {format_duration(data.get('duration_seconds'))}")
    print(f"🌐 Browser: {data.get('browser_type', 'unknown').upper()}")
    print(f"🍎 Using Actual Safari: {'Yes' if data.get('using_actual_safari') else 'No'}")
    print(f"🔗 Final URL: {data.get('final_url', 'N/A')}")
    
    # Summary
    summary = data.get('summary', {})
    if summary:
        print("\n" + "-" * 80)
        print("📊 SUMMARY")
        print("-" * 80)
        print(f"  Total Actions: {data.get('total_actions', 0)}")
        print(f"  Navigations: {summary.get('navigations', 0)}")
        print(f"  URL Changes: {summary.get('url_changes', 0)}")
        print(f"  Captchas Detected: {summary.get('captchas_detected', 0)}")
        print(f"  Captchas Solved: {summary.get('captchas_solved', 0)}")
        print(f"  Verification Codes: {summary.get('verification_codes', 0)}")
        print(f"  Login Success: {'✅ Yes' if summary.get('login_success') else '❌ No'}")
    
    # Actions timeline
    actions = data.get('actions', [])
    if actions:
        print("\n" + "-" * 80)
        print("📝 ACTION TIMELINE")
        print("-" * 80)
        
        for i, action in enumerate(actions, 1):
            action_type = action.get('type', 'unknown')
            timestamp = action.get('timestamp', '')
            relative_time = action.get('relative_time')
            details = action.get('details', {})
            description = details.get('description', '')
            
            # Format time
            time_str = ""
            if relative_time is not None:
                time_str = f"[+{relative_time:.1f}s]"
            elif timestamp:
                time_str = f"[{format_timestamp(timestamp)}]"
            
            # Icon based on action type
            icons = {
                'navigation': '🌐',
                'url_change': '🔗',
                'captcha_detected': '⚠️',
                'captcha_solved': '✅',
                'verification_code_entered': '📱',
                'login_success': '🎉',
                'click': '🖱️',
                'input': '⌨️',
                'keypress': '🔑',
            }
            icon = icons.get(action_type, '📌')
            
            print(f"\n{i:3d}. {icon} {action_type.upper()} {time_str}")
            if description:
                print(f"     {description}")
            
            # Show additional details for specific actions
            if action_type == 'url_change':
                print(f"     From: {details.get('from', 'N/A')[:60]}")
                print(f"     To:   {details.get('to', 'N/A')[:60]}")
            elif action_type == 'captcha_detected':
                print(f"     Selector: {details.get('selector', 'N/A')}")
                print(f"     Type: {details.get('type', 'unknown')}")
            elif action_type == 'captcha_solved':
                print(f"     Type: {details.get('type', 'unknown')}")
            elif action_type == 'verification_code_entered':
                code = details.get('code', 'N/A')
                masked_code = f"{code[:2]}****" if len(code) > 2 else "****"
                print(f"     Code: {masked_code} (masked for security)")
            elif action_type == 'click':
                print(f"     Element: {details.get('tag', 'N/A')}")
                print(f"     Text: {details.get('text', 'N/A')[:50]}")
                print(f"     Selector: {details.get('selector', 'N/A')}")
            elif action_type == 'input':
                print(f"     Field Type: {details.get('input_type', 'N/A')}")
                print(f"     Selector: {details.get('selector', 'N/A')}")
    
    print("\n" + "=" * 80)
    print("End of Recording")
    print("=" * 80 + "\n")


def list_recordings(recordings_dir: Path) -> List[Path]:
    """List all recording files."""
    if not recordings_dir.exists():
        return []
    
    recordings = sorted(
        recordings_dir.glob("login_recording_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    return recordings


def main():
    """Main function to review recordings."""
    logger.remove()
    logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")
    
    recordings_dir = Path(__file__).parent / "recordings"
    
    # List all recordings
    recordings = list_recordings(recordings_dir)
    
    if not recordings:
        print("❌ No recordings found in automation/recordings/")
        print("\nTo create a recording, run:")
        print("  python3 automation/test_manual_login_recording.py safari")
        return
    
    print(f"\n📁 Found {len(recordings)} recording(s):\n")
    
    # Show list
    for i, rec in enumerate(recordings, 1):
        try:
            with open(rec, 'r') as f:
                data = json.load(f)
            recorded_at = format_timestamp(data.get('recorded_at', ''))
            total_actions = data.get('total_actions', 0)
            duration = format_duration(data.get('duration_seconds'))
            success = data.get('summary', {}).get('login_success', False)
            status = "✅ Success" if success else "⏳ Incomplete"
            
            print(f"  {i}. {rec.name}")
            print(f"     {recorded_at} | {total_actions} actions | {duration} | {status}")
        except:
            print(f"  {i}. {rec.name} (error reading)")
    
    # If argument provided, show specific recording
    if len(sys.argv) > 1:
        try:
            index = int(sys.argv[1]) - 1
            if 0 <= index < len(recordings):
                display_recording(recordings[index])
            else:
                print(f"\n❌ Invalid index. Choose 1-{len(recordings)}")
        except ValueError:
            print(f"\n❌ Invalid index: {sys.argv[1]}")
    else:
        # Show most recent recording
        print(f"\n📖 Showing most recent recording:\n")
        display_recording(recordings[0])
        
        if len(recordings) > 1:
            print(f"\n💡 To view other recordings, run:")
            print(f"   python3 automation/review_recordings.py <number>")
            print(f"   Example: python3 automation/review_recordings.py 2")


if __name__ == "__main__":
    main()


