#!/usr/bin/env python3
"""
Test iPhone Mount Access
========================
Tests mounting iPhone as filesystem using libimobiledevice + ifuse.
This allows direct file access without Image Capture.
"""

import subprocess
import sys
from pathlib import Path
import time
import shutil


def check_dependencies():
    """Check if required tools are installed."""
    tools = {
        'idevice_id': 'libimobiledevice',
        'ifuse': 'ifuse',
        'idevicepair': 'libimobiledevice'
    }
    
    missing = []
    for tool, package in tools.items():
        result = subprocess.run(['which', tool], capture_output=True)
        if result.returncode != 0:
            missing.append(f"{tool} (from {package})")
    
    if missing:
        print("❌ Missing dependencies:")
        for tool in missing:
            print(f"   - {tool}")
        print("\nInstall with:")
        print("   brew install --cask macfuse")
        print("   brew install libimobiledevice ifuse")
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
                print(f"   UDID: {udid[:20]}...")
            return udids[0] if udids else None
        else:
            print("❌ No device connected")
            return None
    except subprocess.TimeoutExpired:
        print("❌ Device check timed out")
        return None
    except Exception as e:
        print(f"❌ Error checking device: {e}")
        return None


def pair_device():
    """Pair with iPhone (if not already paired)."""
    print("\n📱 Pairing with device...")
    try:
        result = subprocess.run(
            ['idevicepair', 'pair'],
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
            print(f"❌ Pairing failed: {result.stderr.strip()}")
            print("   Make sure iPhone is unlocked and 'Trust This Computer' is accepted")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Pairing timed out")
        return False
    except Exception as e:
        print(f"❌ Pairing error: {e}")
        return False


def mount_device(mount_point: Path):
    """Mount iPhone filesystem."""
    print(f"\n📂 Mounting device to {mount_point}...")
    
    # Create mount point
    mount_point.mkdir(parents=True, exist_ok=True)
    
    # Check if already mounted
    if (mount_point / "DCIM").exists():
        print("✅ Device already mounted")
        return True
    
    try:
        result = subprocess.run(
            ['ifuse', str(mount_point)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Check if mount succeeded
            if (mount_point / "DCIM").exists():
                print("✅ Device mounted successfully")
                return True
            else:
                print("⚠️  Mount command succeeded but DCIM not found")
                return False
        else:
            error = result.stderr.strip() or result.stdout.strip()
            print(f"❌ Mount failed: {error}")
            if "Permission denied" in error:
                print("   Try: sudo chmod 666 /dev/fuse")
            elif "macFUSE" in error:
                print("   Make sure macFUSE is installed: brew install --cask macfuse")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Mount timed out")
        return False
    except Exception as e:
        print(f"❌ Mount error: {e}")
        return False


def list_files(mount_point: Path):
    """List files in mounted iPhone."""
    print(f"\n📋 Listing files in {mount_point}...")
    
    dcim = mount_point / "DCIM"
    if not dcim.exists():
        print("❌ DCIM folder not found")
        return []
    
    print(f"✅ DCIM folder found")
    
    # List top-level directories
    dirs = [d for d in dcim.iterdir() if d.is_dir()]
    print(f"   Found {len(dirs)} directories")
    
    # Count files
    media_files = []
    for ext in ['.jpg', '.jpeg', '.png', '.heic', '.mov', '.mp4', '.m4v']:
        files = list(dcim.rglob(f"*{ext}"))
        media_files.extend(files)
    
    print(f"   Found {len(media_files)} media files")
    
    # Show sample files
    if media_files:
        print("\n   Sample files:")
        for f in media_files[:5]:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"   - {f.name} ({size_mb:.1f} MB)")
    
    return media_files


def test_file_access(mount_point: Path, test_file: Path = None):
    """Test reading a file from mounted iPhone."""
    print(f"\n🔍 Testing file access...")
    
    dcim = mount_point / "DCIM"
    if not dcim.exists():
        print("❌ DCIM folder not accessible")
        return False
    
    # Find a test file
    if test_file is None:
        media_files = []
        for ext in ['.mov', '.mp4', '.jpg', '.heic']:
            files = list(dcim.rglob(f"*{ext}"))
            if files:
                test_file = files[0]
                break
    
    if test_file and test_file.exists():
        try:
            # Try to read file metadata
            stat = test_file.stat()
            size_mb = stat.st_size / (1024 * 1024)
            print(f"✅ Can access file: {test_file.name}")
            print(f"   Size: {size_mb:.1f} MB")
            print(f"   Path: {test_file}")
            return True
        except Exception as e:
            print(f"❌ Cannot access file: {e}")
            return False
    else:
        print("⚠️  No test file found")
        return False


def unmount_device(mount_point: Path):
    """Unmount iPhone filesystem."""
    print(f"\n📤 Unmounting device...")
    try:
        result = subprocess.run(
            ['umount', str(mount_point)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("✅ Device unmounted")
            return True
        else:
            # Try alternative unmount
            result = subprocess.run(
                ['diskutil', 'unmount', str(mount_point)],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                print("✅ Device unmounted (via diskutil)")
                return True
            else:
                print(f"⚠️  Unmount warning: {result.stderr.strip()}")
                return False
    except Exception as e:
        print(f"⚠️  Unmount error: {e}")
        return False


def main():
    """Main test function."""
    print("=" * 60)
    print("iPhone Mount Access Test")
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
    
    # Pair device
    if not pair_device():
        print("\n⚠️  Pairing failed, but continuing...")
    
    # Mount point
    mount_point = Path.home() / "iPhoneMount"
    
    # Mount device
    if not mount_device(mount_point):
        print("\n❌ Failed to mount device")
        sys.exit(1)
    
    try:
        # List files
        files = list_files(mount_point)
        
        # Test file access
        test_file_access(mount_point)
        
        print("\n" + "=" * 60)
        print("✅ Test Complete!")
        print("=" * 60)
        print(f"\nDevice mounted at: {mount_point}")
        print(f"DCIM folder: {mount_point / 'DCIM'}")
        print(f"\nYou can now access files directly from: {mount_point}")
        print("\nTo unmount:")
        print(f"  umount {mount_point}")
        print(f"  # or: diskutil unmount {mount_point}")
        
    finally:
        # Ask if user wants to unmount
        print("\n" + "=" * 60)
        response = input("Unmount device now? (y/n): ").strip().lower()
        if response == 'y':
            unmount_device(mount_point)


if __name__ == "__main__":
    main()

