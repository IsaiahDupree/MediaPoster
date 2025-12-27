#!/usr/bin/env python3
"""
Test pymobiledevice3 for Direct iPhone File Access
==================================================
Tests using pymobiledevice3 to access iPhone files directly on macOS.
"""

import sys
from pathlib import Path

try:
    from pymobiledevice3.lockdown import LockdownClient
    from pymobiledevice3.services.afc import AfcService
    PYMOBILEDEVICE3_AVAILABLE = True
except ImportError:
    PYMOBILEDEVICE3_AVAILABLE = False
    print("❌ pymobiledevice3 not installed")
    print("   Install with: pip install pymobiledevice3")
    sys.exit(1)


def test_lockdown():
    """Test connecting to device via Lockdown."""
    print("=" * 60)
    print("pymobiledevice3 Direct File Access Test")
    print("=" * 60)
    print()
    
    try:
        print("🔗 Connecting to device...")
        lockdown = LockdownClient()
        
        print(f"✅ Connected to: {lockdown.device_info.get('DeviceName', 'Unknown Device')}")
        print(f"   Model: {lockdown.device_info.get('ProductType', 'Unknown')}")
        print(f"   iOS: {lockdown.device_info.get('ProductVersion', 'Unknown')}")
        print(f"   UDID: {lockdown.udid[:20]}...")
        
        return lockdown
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("   Make sure iPhone is unlocked and 'Trust This Computer' is accepted")
        return None


def test_afc_access(lockdown):
    """Test AFC (Apple File Conduit) service for file access."""
    print("\n📂 Testing AFC file access...")
    
    try:
        afc = AfcService(lockdown)
        
        # List root directory
        print("   Root directory contents:")
        root_items = afc.listdir('/')
        for item in root_items[:10]:
            print(f"   - {item}")
        
        # Try to access DCIM
        if 'DCIM' in root_items:
            print("\n   DCIM folder found!")
            dcim_items = afc.listdir('/DCIM')
            print(f"   DCIM contains {len(dcim_items)} items")
            
            # Show first few items
            for item in dcim_items[:5]:
                print(f"   - {item}")
            
            return True
        else:
            print("   ⚠️  DCIM folder not found in root")
            return False
            
    except Exception as e:
        print(f"❌ AFC access failed: {e}")
        return False


def test_file_download(lockdown, test_file: str = None):
    """Test downloading a file from iPhone."""
    print("\n📥 Testing file download...")
    
    try:
        afc = AfcService(lockdown)
        
        # Find a test file in DCIM
        if test_file is None:
            dcim_items = afc.listdir('/DCIM')
            for item in dcim_items:
                # Check if it's a directory
                try:
                    sub_items = afc.listdir(f'/DCIM/{item}')
                    # Look for media files in subdirectory
                    for sub_item in sub_items:
                        if any(sub_item.lower().endswith(ext) for ext in ['.mov', '.mp4', '.jpg', '.heic']):
                            test_file = f'/DCIM/{item}/{sub_item}'
                            break
                    if test_file:
                        break
                except:
                    # Not a directory, might be a file
                    if any(item.lower().endswith(ext) for ext in ['.mov', '.mp4', '.jpg', '.heic']):
                        test_file = f'/DCIM/{item}'
                        break
        
        if not test_file:
            print("   ⚠️  No test file found")
            return False
        
        print(f"   Downloading: {test_file}")
        
        # Download to temp directory
        output_dir = Path.home() / "iPhoneTestDownloads"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / Path(test_file).name
        
        # Get file from device
        with open(output_file, 'wb') as f:
            afc.get_file_contents(test_file, f)
        
        if output_file.exists():
            size_mb = output_file.stat().st_size / (1024 * 1024)
            print(f"   ✅ Downloaded: {output_file.name} ({size_mb:.1f} MB)")
            print(f"   Saved to: {output_file}")
            return True
        else:
            print("   ❌ Download failed")
            return False
            
    except Exception as e:
        print(f"   ❌ Download error: {e}")
        return False


def main():
    """Main test function."""
    if not PYMOBILEDEVICE3_AVAILABLE:
        print("Install pymobiledevice3 first:")
        print("  pip install pymobiledevice3")
        sys.exit(1)
    
    # Connect to device
    lockdown = test_lockdown()
    if not lockdown:
        sys.exit(1)
    
    # Test AFC access
    if test_afc_access(lockdown):
        print("\n" + "=" * 60)
        print("✅ Direct File Access Working!")
        print("=" * 60)
        print("\nYou can now access iPhone files directly via pymobiledevice3")
        
        # Test download if requested
        if len(sys.argv) > 1 and sys.argv[1] == "--test-download":
            test_file_download(lockdown)
    else:
        print("\n⚠️  Could not access files via AFC")
        print("   This might require additional permissions or pairing")


if __name__ == "__main__":
    main()

