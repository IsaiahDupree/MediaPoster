#!/usr/bin/env python3
"""
Test iPhone AFC (Apple File Conduit) Access
===========================================
Uses libimobiledevice to access iPhone files directly via AFC service.
Works on macOS without ifuse mounting.
"""

import subprocess
import sys
from pathlib import Path
import tempfile
import shutil


def check_dependencies():
    """Check if required tools are installed."""
    tools = ['idevice_id', 'idevicepair', 'ideviceinfo', 'ideviceafc']
    
    missing = []
    for tool in tools:
        result = subprocess.run(['which', tool], capture_output=True)
        if result.returncode != 0:
            missing.append(tool)
    
    if missing:
        print("❌ Missing dependencies:")
        for tool in missing:
            print(f"   - {tool}")
        print("\nInstall with:")
        print("   brew install libimobiledevice")
        return False
    
    print("✅ All dependencies installed")
    return True


def check_device_connected():
    """Check if iPhone is connected."""
    try:
        result = subprocess.run(
            ['idevice_id', '-l'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            udids = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
            print(f"✅ Device connected: {len(udids)} device(s)")
            for udid in udids:
                print(f"   UDID: {udid}")
            return udids[0] if udids else None
        else:
            print("❌ No device connected")
            return None
    except Exception as e:
        print(f"❌ Error checking device: {e}")
        return None


def get_device_info(udid):
    """Get device information."""
    print(f"\n📱 Getting device info...")
    try:
        result = subprocess.run(
            ['ideviceinfo', '-u', udid],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            info = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    info[key.strip()] = value.strip()
            
            if 'DeviceName' in info:
                print(f"✅ Device: {info['DeviceName']}")
            if 'ProductType' in info:
                print(f"   Model: {info['ProductType']}")
            if 'ProductVersion' in info:
                print(f"   iOS: {info['ProductVersion']}")
            
            return info
        else:
            print(f"⚠️  Could not get device info: {result.stderr.strip()}")
            return {}
    except Exception as e:
        print(f"⚠️  Error getting device info: {e}")
        return {}


def pair_device(udid):
    """Pair with iPhone."""
    print(f"\n🔗 Pairing with device...")
    try:
        result = subprocess.run(
            ['idevicepair', '-u', udid, 'pair'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            if "SUCCESS" in result.stdout or "Paired" in result.stdout:
                print("✅ Device paired successfully")
                return True
            elif "already paired" in result.stdout.lower():
                print("✅ Device already paired")
                return True
            else:
                print(f"⚠️  Pairing result: {result.stdout.strip()}")
                return False
        else:
            print(f"⚠️  Pairing status: {result.stderr.strip()}")
            if "already paired" in result.stderr.lower():
                print("✅ Device already paired")
                return True
            return False
    except Exception as e:
        print(f"⚠️  Pairing error: {e}")
        return False


def list_dcim_files(udid):
    """List files in DCIM folder using ideviceafc."""
    print(f"\n📂 Listing DCIM files...")
    
    try:
        # Use ideviceafc to list DCIM directory
        result = subprocess.run(
            ['ideviceafc', '-u', udid, 'ls', 'DCIM'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
            print(f"✅ Found {len(lines)} items in DCIM")
            
            # Show first few items
            for item in lines[:10]:
                print(f"   - {item}")
            
            return lines
        else:
            print(f"⚠️  Could not list DCIM: {result.stderr.strip()}")
            return []
    except Exception as e:
        print(f"⚠️  Error listing DCIM: {e}")
        return []


def test_file_download(udid, test_file_path: str, output_dir: Path):
    """Test downloading a file from iPhone."""
    print(f"\n📥 Testing file download...")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Get filename from path
        filename = Path(test_file_path).name
        output_file = output_dir / filename
        
        # Use ideviceafc to get file
        result = subprocess.run(
            ['ideviceafc', '-u', udid, 'get', test_file_path, str(output_file)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and output_file.exists():
            size_mb = output_file.stat().st_size / (1024 * 1024)
            print(f"✅ Downloaded: {filename} ({size_mb:.1f} MB)")
            print(f"   Saved to: {output_file}")
            return True
        else:
            print(f"❌ Download failed: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ Download error: {e}")
        return False


def main():
    """Main test function."""
    print("=" * 60)
    print("iPhone AFC (Apple File Conduit) Access Test")
    print("=" * 60)
    print()
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Check device
    udid = check_device_connected()
    if not udid:
        print("\n❌ No iPhone connected. Please connect your iPhone via USB.")
        sys.exit(1)
    
    # Get device info
    device_info = get_device_info(udid)
    
    # Pair device
    pair_device(udid)
    
    # List DCIM files
    dcim_items = list_dcim_files(udid)
    
    if dcim_items:
        print("\n" + "=" * 60)
        print("✅ AFC Access Working!")
        print("=" * 60)
        print(f"\nDevice UDID: {udid}")
        print(f"DCIM items: {len(dcim_items)}")
        print("\nYou can use ideviceafc to access files:")
        print(f"  ideviceafc -u {udid} ls DCIM")
        print(f"  ideviceafc -u {udid} get <path> <local_file>")
        
        # Test download if user wants
        if len(sys.argv) > 1 and sys.argv[1] == "--test-download":
            test_dir = Path.home() / "iPhoneTestDownloads"
            if dcim_items:
                # Try to find a file (not a directory)
                for item in dcim_items:
                    if '.' in item and not item.startswith('.'):
                        test_file_download(udid, f"DCIM/{item}", test_dir)
                        break
    else:
        print("\n⚠️  Could not access DCIM folder")
        print("   Make sure iPhone is unlocked and 'Trust This Computer' is accepted")


if __name__ == "__main__":
    main()

