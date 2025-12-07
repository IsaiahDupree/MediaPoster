"""
Safely stop the recorder and save the recording.
"""
import subprocess
import sys
from pathlib import Path

def stop_recorder():
    """Stop recorder processes gracefully."""
    print("🛑 Stopping recorder processes...")
    
    # Find all recorder processes
    try:
        result = subprocess.run(
            ["pgrep", "-f", "test_manual_login_recording"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"Found {len(pids)} recorder process(es)")
            
            for pid in pids:
                if pid:
                    print(f"  Sending SIGINT to process {pid}...")
                    try:
                        subprocess.run(["kill", "-INT", pid], check=True)
                    except subprocess.CalledProcessError:
                        print(f"  ⚠️  Could not stop process {pid}")
            
            print("\n⏳ Waiting for processes to save recordings...")
            import time
            time.sleep(3)
            
            # Check if any are still running
            result = subprocess.run(
                ["pgrep", "-f", "test_manual_login_recording"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                print("⚠️  Some processes still running - forcing stop...")
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    if pid:
                        subprocess.run(["kill", "-9", pid], check=False)
        else:
            print("✅ No recorder processes found")
    
    except Exception as e:
        print(f"Error: {e}")
    
    # Check for recordings
    recordings_dir = Path(__file__).parent / "recordings"
    recordings = list(recordings_dir.glob("login_recording_*.json"))
    
    if recordings:
        print(f"\n✅ Found {len(recordings)} recording(s)")
        print(f"   Latest: {recordings[-1].name}")
        print("\nTo view recordings:")
        print("  python3 automation/review_recordings.py")
    else:
        print("\n⚠️  No recordings found")
        print("   (Recording may not have been saved if process was killed)")
        print("   Run the recorder again and use Ctrl+C to stop it properly")


if __name__ == "__main__":
    stop_recorder()


