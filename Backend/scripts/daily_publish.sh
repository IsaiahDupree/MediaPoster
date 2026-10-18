#!/bin/bash
# Daily Publisher Shell Wrapper
# 
# Usage:
#   ./scripts/daily_publish.sh              # Full cycle: start, publish, shutdown
#   ./scripts/daily_publish.sh --check      # Just check what's scheduled
#   ./scripts/daily_publish.sh --keep-alive # Don't shutdown after
#
# To schedule with cron (every 2 hours):
#   crontab -e
#   0 */2 * * * /Users/isaiahdupree/Documents/Software/MediaPoster/Backend/scripts/daily_publish.sh >> /tmp/daily_publisher.log 2>&1
#
# To schedule with launchd (recommended for macOS):
#   cp scripts/com.mediaposter.daily-publisher.plist ~/Library/LaunchAgents/
#   launchctl load ~/Library/LaunchAgents/com.mediaposter.daily-publisher.plist

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$BACKEND_DIR")"

cd "$BACKEND_DIR"

# Activate virtual environment
source venv/bin/activate

# Parse arguments
ARGS=""
if [[ "$1" == "--check" ]]; then
    ARGS="--check-only --keep-alive"
elif [[ "$1" == "--keep-alive" ]]; then
    ARGS="--keep-alive"
fi

# Run the publisher
python scripts/daily_publisher.py $ARGS

exit $?
