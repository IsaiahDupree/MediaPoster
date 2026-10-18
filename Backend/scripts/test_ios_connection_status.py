#!/usr/bin/env python3
"""
Test iOS Device Connection Status
=================================
Tests that device connection status updates correctly when device is disconnected.

Run this script:
1. With iPhone connected - should show "connected: True"
2. Disconnect iPhone - should show "connected: False"
3. Reconnect iPhone - should show "connected: True" again

Usage:
    python3 scripts/test_ios_connection_status.py
"""

import sys
import os
import json
import subprocess
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.endpoints.ios_import_api import check_device
import asyncio


def test_connection_check():
    """Test the connection check function directly."""
    print("=" * 60)
    print("iOS Device Connection Status Test")
    print("=" * 60)
    print()
    
    print("Testing connection check function...")
    print("(This will check the current device status)")
    print()
    
    # Run the async function
    result = asyncio.run(check_device())
    
    print(f"Result: {json.dumps(result, indent=2)}")
    print()
    
    if result.get("connected"):
        print("✅ Device is CONNECTED")
        print(f"   Name: {result.get('name', 'Unknown')}")
        print(f"   Type: {result.get('connection_type', 'Unknown')}")
    else:
        print("❌ Device is NOT CONNECTED")
    
    print()
    print("=" * 60)
    print("Test Instructions:")
    print("=" * 60)
    print("1. Run this script with iPhone connected")
    print("2. Disconnect iPhone")
    print("3. Run this script again - should show 'connected: False'")
    print("4. Reconnect iPhone")
    print("5. Run this script again - should show 'connected: True'")
    print()
    
    return result


def test_multiple_checks():
    """Test multiple connection checks to verify status updates."""
    print("=" * 60)
    print("Multiple Connection Checks Test")
    print("=" * 60)
    print()
    print("This will check connection status 5 times with 2 second intervals.")
    print("Disconnect your iPhone during the test to see status change.")
    print()
    
    for i in range(5):
        print(f"Check {i + 1}/5...")
        result = asyncio.run(check_device())
        
        status = "✅ CONNECTED" if result.get("connected") else "❌ NOT CONNECTED"
        print(f"  Status: {status}")
        
        if result.get("connected"):
            print(f"  Device: {result.get('name', 'Unknown')}")
            print(f"  Type: {result.get('connection_type', 'Unknown')}")
        
        if i < 4:  # Don't sleep after last check
            print("  Waiting 2 seconds...")
            time.sleep(2)
        print()
    
    print("=" * 60)
    print("Test complete!")
    print("=" * 60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test iOS device connection status")
    parser.add_argument(
        "--multiple",
        action="store_true",
        help="Run multiple checks with intervals (useful for testing disconnection)"
    )
    
    args = parser.parse_args()
    
    if args.multiple:
        test_multiple_checks()
    else:
        test_connection_check()

