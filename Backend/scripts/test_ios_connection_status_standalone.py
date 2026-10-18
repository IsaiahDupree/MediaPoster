#!/usr/bin/env python3
"""
Test iOS Device Connection Status (Standalone)
==============================================
Tests that device connection status updates correctly when device is disconnected.

This script tests the connection detection logic directly without requiring FastAPI.
"""

import sys
import json
import subprocess
import time
from pathlib import Path


def check_device_finder():
    """Check for iOS device via Finder."""
    try:
        result = subprocess.run(
            ["osascript", "-e", '''
            tell application "Finder"
                set deviceList to {}
                repeat with d in (get every disk)
                    set diskName to name of d as string
                    if diskName contains "iPhone" or diskName contains "iPad" or diskName contains "iOS" then
                        set end of deviceList to diskName
                    end if
                end repeat
                return deviceList
            end tell
            '''],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            device_name = result.stdout.strip()
            if device_name:
                return {
                    "connected": True,
                    "name": "Isaiah's iPhone" if "iOS" in device_name else device_name,
                    "serial": device_name,
                    "connection_type": "finder"
                }
    except subprocess.TimeoutExpired:
        print("  ⚠️  Finder check timed out")
    except Exception as e:
        print(f"  ⚠️  Finder check failed: {e}")
    
    return None


def check_device_usb():
    """Check for iOS device via USB."""
    try:
        result = subprocess.run(
            ["system_profiler", "SPUSBDataType", "-json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                usb_data = data.get("SPUSBDataType", [])
                
                for controller in usb_data:
                    items = controller.get("_items", [])
                    for item in items:
                        name = item.get("_name", "").lower()
                        if "iphone" in name or "ipad" in name or "apple mobile" in name:
                            return {
                                "connected": True,
                                "name": item.get("_name", "iOS Device"),
                                "serial": item.get("serial_num", ""),
                                "product_id": item.get("product_id", ""),
                                "connection_type": "usb"
                            }
                        # Check nested items
                        nested = item.get("_items", [])
                        for nested_item in nested:
                            nested_name = nested_item.get("_name", "").lower()
                            if "iphone" in nested_name or "ipad" in nested_name or "apple mobile" in nested_name:
                                return {
                                    "connected": True,
                                    "name": nested_item.get("_name", "iOS Device"),
                                    "serial": nested_item.get("serial_num", ""),
                                    "product_id": nested_item.get("product_id", ""),
                                    "connection_type": "usb"
                                }
            except json.JSONDecodeError as e:
                print(f"  ⚠️  Failed to parse USB data as JSON: {e}")
    except subprocess.TimeoutExpired:
        print("  ⚠️  USB check timed out")
    except Exception as e:
        print(f"  ⚠️  USB check failed: {e}")
    
    return None


def check_device():
    """Check if an iOS device is connected (USB or WiFi sync)."""
    # Try USB FIRST (more reliable for physical disconnection)
    result = check_device_usb()
    if result:
        return result
    
    # Try Finder second (only if USB found nothing)
    # Note: Finder may show stale mounts, so we validate accessibility
    result = check_device_finder()
    if result:
        # Additional validation: Check if mount point is actually accessible
        import os
        device_name = result.get("serial", "")
        if device_name:
            mount_path = f"/Volumes/{device_name}"
            if os.path.exists(mount_path):
                # Try to access the mount point
                try:
                    test_result = subprocess.run(
                        ["test", "-d", mount_path],
                        capture_output=True,
                        timeout=2
                    )
                    if test_result.returncode == 0:
                        return result
                    else:
                        print(f"  ⚠️  Finder mount exists but is not accessible: {device_name}")
                except Exception:
                    pass
    
    # No device found
    return {"connected": False}


def test_single_check():
    """Test a single connection check."""
    print("=" * 60)
    print("iOS Device Connection Status Test")
    print("=" * 60)
    print()
    
    print("Checking device connection...")
    print()
    
    result = check_device()
    
    print(f"Result: {json.dumps(result, indent=2)}")
    print()
    
    if result.get("connected"):
        print("✅ Device is CONNECTED")
        print(f"   Name: {result.get('name', 'Unknown')}")
        print(f"   Type: {result.get('connection_type', 'Unknown')}")
        if result.get('serial'):
            print(f"   Serial: {result.get('serial')}")
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
    print("Press Ctrl+C to stop early")
    print()
    
    results = []
    
    for i in range(5):
        print(f"Check {i + 1}/5...")
        result = check_device()
        results.append(result)
        
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
    print("Summary:")
    print("=" * 60)
    connected_count = sum(1 for r in results if r.get("connected"))
    print(f"Connected: {connected_count}/5 checks")
    print(f"Not Connected: {5 - connected_count}/5 checks")
    
    # Check if status changed
    if len(set(r.get("connected") for r in results)) > 1:
        print()
        print("✅ Status changed during test - disconnection was detected!")
    else:
        print()
        if connected_count == 5:
            print("ℹ️  Device remained connected throughout test")
        else:
            print("ℹ️  Device remained disconnected throughout test")
    
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
    
    try:
        if args.multiple:
            test_multiple_checks()
        else:
            test_single_check()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)

