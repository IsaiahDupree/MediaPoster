#!/bin/bash
# Install Weekly Database Backup Scheduler
# =========================================
# This script sets up automatic weekly database backups via launchd.
# Backups run every Sunday at 2:00 AM.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_SOURCE="$SCRIPT_DIR/com.mediaposter.db-backup.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.mediaposter.db-backup.plist"
LOG_DIR="$SCRIPT_DIR/../logs"

echo "🗄️  MediaPoster Database Backup Scheduler Installer"
echo "=================================================="
echo ""

# Create logs directory
mkdir -p "$LOG_DIR"
echo "✅ Created logs directory: $LOG_DIR"

# Check if plist exists
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "❌ Plist file not found: $PLIST_SOURCE"
    exit 1
fi

# Create LaunchAgents directory if needed
mkdir -p "$HOME/Library/LaunchAgents"

# Unload existing if present
if launchctl list | grep -q "com.mediaposter.db-backup"; then
    echo "🔄 Unloading existing scheduler..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Copy plist to LaunchAgents
cp "$PLIST_SOURCE" "$PLIST_DEST"
echo "✅ Copied plist to: $PLIST_DEST"

# Load the scheduler
launchctl load "$PLIST_DEST"
echo "✅ Loaded backup scheduler"

# Verify it's running
if launchctl list | grep -q "com.mediaposter.db-backup"; then
    echo ""
    echo "✅ Backup scheduler installed successfully!"
    echo ""
    echo "📅 Schedule: Every Sunday at 2:00 AM"
    echo "📁 Backup location: /Volumes/My Passport/MediaPoster/backups/database/"
    echo "📋 Logs: $LOG_DIR/db_backup.log"
    echo ""
    echo "Commands:"
    echo "  - Run backup now:    python $SCRIPT_DIR/db_backup.py"
    echo "  - List backups:      python $SCRIPT_DIR/db_backup.py --list"
    echo "  - Uninstall:         launchctl unload $PLIST_DEST"
    echo ""
else
    echo "❌ Failed to load scheduler"
    exit 1
fi
