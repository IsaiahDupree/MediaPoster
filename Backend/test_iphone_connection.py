#!/usr/bin/env python3
"""
iPhone USB Connection Diagnostic Tool
Tests programmatic connection and provides fixes
"""
import subprocess
import sys
from pathlib import Path

def run_cmd(cmd):
    """Run command and return output"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def test_homebrew():
    print("\n" + "="*60)
    print("1. Checking Homebrew")
    print("="*60)
    success, out, err = run_cmd(['brew', '--version'])
    if success:
        print(f"✓ Homebrew installed: {out.split()[1]}")
    else:
        print("✗ Homebrew not found")
        print("Install: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
    return success

def test_libimobiledevice():
    print("\n" + "="*60)
    print("2. Checking libimobiledevice Tools")
    print("="*60)
    
    tools = ['idevice_id', 'ideviceinfo', 'idevicepair', 'ifuse']
    all_ok = True
    
    for tool in tools:
        success, out, _ = run_cmd(['which', tool])
        if success:
            print(f"✓ {tool}: {out.strip()}")
        else:
            print(f"✗ {tool}: Not found")
            all_ok = False
    
    if not all_ok:
        print("\nInstall: brew install libimobiledevice ifuse")
    return all_ok

def test_usb_connection():
    print("\n" + "="*60)
    print("3. Checking USB Connection")
    print("="*60)
    
    success, out, _ = run_cmd(['system_profiler', 'SPUSBDataType'])
    if 'iPhone' in out:
        print("✓ iPhone detected in USB")
        return True
    else:
        print("✗ iPhone not detected")
        print("  1. Connect iPhone via USB")
        print("  2. Use Apple/MFi certified cable")
        print("  3. Try different USB port")
        return False

def test_device_detection():
    print("\n" + "="*60)
    print("4. Checking Device Detection")
    print("="*60)
    
    success, out, _ = run_cmd(['idevice_id', '-l'])
    if success and out.strip():
        print(f"✓ Device detected: {out.strip()}")
        return True, out.strip()
    else:
        print("✗ Device not detected")
        print("  1. Unlock iPhone")
        print("  2. Trust this computer")
        print("  3. Run: idevicepair pair")
        return False, None

def test_trust():
    print("\n" + "="*60)
    print("5. Checking Trust Relationship")
    print("="*60)
    
    success, out, _ = run_cmd(['idevicepair', 'validate'])
    if 'SUCCESS' in out:
        print("✓ Device is trusted")
        return True
    else:
        print("✗ Device not trusted")
        print("  Run: idevicepair pair")
        print("  Then tap 'Trust' on iPhone")
        return False

def test_mount():
    print("\n" + "="*60)
    print("6. Testing Filesystem Mount")
    print("="*60)
    
    mount_point = Path.home() / "iPhone_Mount"
    mount_point.mkdir(exist_ok=True)
    
    # Unmount if already mounted
    run_cmd(['umount', str(mount_point)])
    
    success, out, err = run_cmd(['ifuse', str(mount_point)])
    
    import time
    time.sleep(2)
    
    if mount_point.exists() and list(mount_point.iterdir()):
        print(f"✓ Mounted at: {mount_point}")
        
        # Check DCIM
        dcim = mount_point / "DCIM"
        if dcim.exists():
            videos = list(dcim.rglob("*.MOV")) + list(dcim.rglob("*.MP4"))
            print(f"✓ Found {len(videos)} videos in DCIM")
        
        # Cleanup
        run_cmd(['umount', str(mount_point)])
        return True
    else:
        print("✗ Mount failed")
        print("  1. iPhone must be unlocked")
        print("  2. Keep screen on")
        print("  3. Verify trust: idevicepair validate")
        return False

def main():
    print("\n" + "="*60)
    print("  iPhone USB Connection Diagnostic")
    print("="*60)
    
    results = []
    results.append(("Homebrew", test_homebrew()))
    results.append(("libimobiledevice", test_libimobiledevice()))
    results.append(("USB Connection", test_usb_connection()))
    
    has_device, udid = test_device_detection()
    results.append(("Device Detection", has_device))
    
    if has_device:
        results.append(("Trust", test_trust()))
        results.append(("Filesystem Mount", test_mount()))
    
    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"{status} {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All checks passed! iPhone is ready for programmatic access.")
        print("\nUsage:")
        print("  ifuse ~/iPhone_Mount")
        print("  find ~/iPhone_Mount/DCIM -name '*.MOV'")
        print("  umount ~/iPhone_Mount")
    else:
        print("\n⚠️ Some checks failed. Follow the troubleshooting steps above.")
        print("\nAlternatives:")
        print("  • Use AirDrop (fastest, no setup)")
        print("  • Use iCloud Photos (automatic sync)")
    
    print("\nSee: IPHONE_USB_TROUBLESHOOTING.md for detailed guide\n")

if __name__ == "__main__":
    main()
