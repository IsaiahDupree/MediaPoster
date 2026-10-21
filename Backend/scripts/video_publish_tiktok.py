#!/usr/bin/env python3
"""
Video Publishing Script for TikTok
Legacy direct-publish command; blocked until migrated to Airtime

Usage:
    python3 scripts/video_publish_tiktok.py  # exits with airtime_required

The old implementation's backend, Google Drive, and Blotato calls are disabled.
"""

import sys
from datetime import datetime

API_URL = "http://localhost:5555"  # Retained for callers; this module performs no HTTP requests.

# Colors for terminal output
class C:
    R = '\033[91m'
    G = '\033[92m'
    Y = '\033[93m'
    B = '\033[94m'
    M = '\033[95m'
    C = '\033[96m'
    W = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


def log(msg, color=C.W):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{C.C}[{ts}]{C.END} {color}{msg}{C.END}")


def generate_caption(media_id, platform="tiktok"):
    """Block unreceipted legacy generation; copy must come from ScriptHub."""
    log(f"script_hub_required: legacy caption generation blocked for {media_id}/{platform}", C.R)
    return None


# =============================================================================
# Legacy direct-publish API
# =============================================================================

def publish_via_full_flow(media_id, account_id, username, title, caption, platform="tiktok"):
    """Block this legacy direct publisher until it uses Airtime."""
    return {
        "success": False,
        "status": "blocked",
        "error": "airtime_required: direct Blotato publishing is disabled; use Airtime",
    }


# =============================================================================
# MAIN SCRIPT
# =============================================================================

def main():
    log("airtime_required: this legacy direct-publish command is disabled; submit approved content through Airtime", C.R)
    return 2

if __name__ == "__main__":
    sys.exit(main())
