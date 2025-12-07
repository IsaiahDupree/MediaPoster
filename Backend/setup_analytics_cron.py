"""
Setup Daily Analytics Cron Job
Configures daily fetching of social media analytics
"""
import os
import subprocess
from pathlib import Path

# Get absolute paths
BACKEND_DIR = Path(__file__).parent.absolute()
VENV_PYTHON = BACKEND_DIR / "venv" / "bin" / "python"
FETCH_SCRIPT = BACKEND_DIR / "services" / "fetch_social_analytics.py"
LOG_DIR = BACKEND_DIR / "logs"

# Create logs directory
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "analytics_fetch.log"


def create_cron_job():
    """Create cron job for daily analytics fetch"""
    
    # Cron command - runs every day at 3 AM
    cron_command = f"0 3 * * * cd {BACKEND_DIR} && {VENV_PYTHON} {FETCH_SCRIPT} >> {LOG_FILE} 2>&1"
    
    print("🕐 Setting up daily analytics cron job...")
    print(f"\nCommand: {cron_command}")
    print(f"\nThis will run every day at 3:00 AM")
    print(f"Logs will be saved to: {LOG_FILE}")
    
    # Get current crontab
    try:
        current_cron = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            check=False
        )
        
        existing_jobs = current_cron.stdout if current_cron.returncode == 0 else ""
        
        # Check if job already exists
        if "fetch_social_analytics.py" in existing_jobs:
            print("\n⚠️  Analytics cron job already exists!")
            response = input("Do you want to replace it? (y/n): ")
            if response.lower() != 'y':
                print("Cancelled.")
                return
            
            # Remove old job
            new_cron = "\n".join([
                line for line in existing_jobs.split("\n")
                if "fetch_social_analytics.py" not in line
            ])
        else:
            new_cron = existing_jobs
        
        # Add new job
        if new_cron and not new_cron.endswith("\n"):
            new_cron += "\n"
        new_cron += cron_command + "\n"
        
        # Install new crontab
        process = subprocess.run(
            ["crontab", "-"],
            input=new_cron,
            text=True,
            capture_output=True
        )
        
        if process.returncode == 0:
            print("\n✅ Cron job installed successfully!")
            print("\nTo view your cron jobs, run: crontab -l")
            print("To remove this job, run: crontab -e")
        else:
            print(f"\n❌ Error installing cron job: {process.stderr}")
            
    except Exception as e:
        print(f"\n❌ Error setting up cron job: {e}")
        print("\nYou can manually add this to your crontab:")
        print(f"\n{cron_command}\n")


def create_launchd_plist():
    """Create macOS LaunchAgent (alternative to cron)"""
    
    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.mediaposter.analytics</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>{VENV_PYTHON}</string>
        <string>{FETCH_SCRIPT}</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>{BACKEND_DIR}</string>
    
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>3</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    
    <key>StandardOutPath</key>
    <string>{LOG_FILE}</string>
    
    <key>StandardErrorPath</key>
    <string>{LOG_FILE}</string>
    
    <key>RunAtLoad</key>
    <false/>
</dict>
</plist>'''
    
    # Save to LaunchAgents directory
    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(exist_ok=True)
    
    plist_file = launch_agents_dir / "com.mediaposter.analytics.plist"
    
    print("\n📋 Creating macOS LaunchAgent (recommended for macOS)...")
    print(f"\nPlist file: {plist_file}")
    
    with open(plist_file, 'w') as f:
        f.write(plist_content)
    
    print("✅ LaunchAgent plist created!")
    
    # Load the agent
    print("\n⚙️  Loading LaunchAgent...")
    try:
        subprocess.run(["launchctl", "unload", str(plist_file)], check=False, capture_output=True)
        result = subprocess.run(["launchctl", "load", str(plist_file)], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ LaunchAgent loaded successfully!")
            print(f"\nThe analytics fetch will run daily at 3:00 AM")
            print(f"Logs: {LOG_FILE}")
        else:
            print(f"⚠️  Warning: {result.stderr}")
            print("LaunchAgent created but may need manual loading")
            
    except Exception as e:
        print(f"⚠️  Could not load LaunchAgent: {e}")
        print(f"\nYou can manually load it with:")
        print(f"launchctl load {plist_file}")


def test_manual_run():
    """Test the fetch script manually"""
    print("\n🧪 Testing manual run...")
    print(f"Running: {VENV_PYTHON} {FETCH_SCRIPT}")
    
    try:
        result = subprocess.run(
            [str(VENV_PYTHON), str(FETCH_SCRIPT)],
            cwd=BACKEND_DIR,
            capture_output=True,
            text=True
        )
        
        print("\n--- Output ---")
        print(result.stdout)
        
        if result.stderr:
            print("\n--- Errors ---")
            print(result.stderr)
        
        if result.returncode == 0:
            print("\n✅ Test run completed successfully!")
        else:
            print(f"\n⚠️  Test run failed with exit code {result.returncode}")
            
    except Exception as e:
        print(f"\n❌ Error running test: {e}")


def main():
    """Main setup function"""
    print("\n" + "="*80)
    print("📊 Social Media Analytics - Cron Job Setup")
    print("="*80 + "\n")
    
    print("This will set up daily analytics fetching for your social media accounts.")
    print("\nOptions:")
    print("  1. Create cron job (works on all Unix systems)")
    print("  2. Create macOS LaunchAgent (recommended for macOS)")
    print("  3. Test manual run")
    print("  4. Exit")
    
    while True:
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == "1":
            create_cron_job()
            break
        elif choice == "2":
            create_launchd_plist()
            break
        elif choice == "3":
            test_manual_run()
            break
        elif choice == "4":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please select 1-4.")


if __name__ == "__main__":
    main()
