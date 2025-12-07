#!/usr/bin/env python3
"""
Device Checker - Display All Connected Peripherals
Shows USB devices, mounted drives, network devices, and more
"""
import subprocess
import json
from pathlib import Path
from datetime import datetime

class DeviceChecker:
    """Check and display all connected devices"""
    
    def __init__(self):
        self.devices = {
            'usb': [],
            'storage': [],
            'network': [],
            'bluetooth': [],
            'display': []
        }
    
    def check_usb_devices(self):
        """Check USB connected devices"""
        print("\n" + "="*60)
        print("📱 USB DEVICES")
        print("="*60)
        
        try:
            result = subprocess.run(
                ['system_profiler', 'SPUSBDataType'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            lines = result.stdout.split('\n')
            current_device = None
            device_count = 0
            
            for line in lines:
                line_stripped = line.strip()
                
                # Device name (indented 4 spaces)
                if line.startswith('    ') and ':' in line and not line.startswith('        '):
                    device_name = line_stripped.replace(':', '')
                    if device_name and not any(skip in device_name.lower() for skip in ['bus', 'controller']):
                        current_device = {
                            'name': device_name,
                            'details': {}
                        }
                        device_count += 1
                        print(f"\n{device_count}. {device_name}")
                
                # Device details (indented 8+ spaces)
                elif current_device and line.startswith('        ') and ':' in line:
                    key, value = line_stripped.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    if key in ['Product ID', 'Vendor ID', 'Serial Number', 'Speed', 'Manufacturer']:
                        current_device['details'][key] = value
                        print(f"   {key}: {value}")
                        
                        if current_device not in self.devices['usb']:
                            self.devices['usb'].append(current_device)
            
            if device_count == 0:
                print("\n✗ No USB devices detected")
                print("\nTip: Connect iPhone, external drive, or USB device")
            else:
                print(f"\n✓ Found {device_count} USB device(s)")
                
                # Specifically check for iPhone
                if any('iPhone' in str(d) for d in self.devices['usb']):
                    print("\n🎉 iPhone detected! Ready for import.")
                else:
                    print("\n💡 No iPhone detected. To connect:")
                    print("   1. Plug in iPhone via USB")
                    print("   2. Unlock iPhone")
                    print("   3. Tap 'Trust This Computer'")
        
        except Exception as e:
            print(f"\n✗ Error checking USB devices: {e}")
    
    def check_storage_devices(self):
        """Check mounted storage devices"""
        print("\n" + "="*60)
        print("💾 STORAGE DEVICES")
        print("="*60)
        
        try:
            result = subprocess.run(
                ['df', '-h'],
                capture_output=True,
                text=True
            )
            
            lines = result.stdout.split('\n')[1:]  # Skip header
            device_count = 0
            
            for line in lines:
                if not line.strip():
                    continue
                
                parts = line.split()
                if len(parts) >= 6:
                    device = parts[0]
                    size = parts[1]
                    used = parts[2]
                    avail = parts[3]
                    capacity = parts[4]
                    mount = ' '.join(parts[5:])
                    
                    # Filter relevant mounts
                    if any(x in mount for x in ['/Volumes', '/System/Volumes/Data', '/private']):
                        if mount != '/System/Volumes/Data' or device_count == 0:
                            device_count += 1
                            print(f"\n{device_count}. {mount}")
                            print(f"   Device: {device}")
                            print(f"   Size: {size} | Used: {used} | Available: {avail}")
                            print(f"   Capacity: {capacity}")
                            
                            self.devices['storage'].append({
                                'mount': mount,
                                'device': device,
                                'size': size,
                                'used': used,
                                'available': avail
                            })
            
            if device_count == 0:
                print("\n✗ No external storage detected")
            else:
                print(f"\n✓ Found {device_count} storage device(s)")
        
        except Exception as e:
            print(f"\n✗ Error checking storage: {e}")
    
    def check_network_interfaces(self):
        """Check network interfaces"""
        print("\n" + "="*60)
        print("🌐 NETWORK INTERFACES")
        print("="*60)
        
        try:
            result = subprocess.run(
                ['ifconfig'],
                capture_output=True,
                text=True
            )
            
            interfaces = []
            current_interface = None
            
            for line in result.stdout.split('\n'):
                if line and not line.startswith('\t'):
                    # New interface
                    interface_name = line.split(':')[0]
                    if interface_name:
                        current_interface = {
                            'name': interface_name,
                            'status': 'unknown',
                            'ip': None
                        }
                        interfaces.append(current_interface)
                elif current_interface:
                    if 'status: active' in line:
                        current_interface['status'] = 'active'
                    elif 'inet ' in line and 'inet6' not in line:
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            current_interface['ip'] = parts[1]
            
            # Display active interfaces
            active_count = 0
            for interface in interfaces:
                if interface['status'] == 'active' and interface['ip']:
                    active_count += 1
                    print(f"\n{active_count}. {interface['name']}")
                    print(f"   Status: ✓ Active")
                    print(f"   IP Address: {interface['ip']}")
                    
                    self.devices['network'].append(interface)
            
            if active_count == 0:
                print("\n✗ No active network interfaces")
            else:
                print(f"\n✓ Found {active_count} active interface(s)")
        
        except Exception as e:
            print(f"\n✗ Error checking network: {e}")
    
    def check_bluetooth_devices(self):
        """Check Bluetooth devices"""
        print("\n" + "="*60)
        print("🔵 BLUETOOTH DEVICES")
        print("="*60)
        
        try:
            result = subprocess.run(
                ['system_profiler', 'SPBluetoothDataType'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            lines = result.stdout.split('\n')
            device_count = 0
            in_devices_section = False
            
            for line in lines:
                if 'Devices (Paired, Configured, etc.):' in line:
                    in_devices_section = True
                    continue
                
                if in_devices_section:
                    # Device names are indented
                    if line.strip() and not line.startswith(' ' * 12) and ':' in line:
                        device_name = line.strip().replace(':', '')
                        if device_name:
                            device_count += 1
                            print(f"\n{device_count}. {device_name}")
            
            if device_count == 0:
                print("\n✗ No Bluetooth devices detected")
            else:
                print(f"\n✓ Found {device_count} Bluetooth device(s)")
        
        except Exception as e:
            print(f"\n✗ Error checking Bluetooth: {e}")
    
    def check_displays(self):
        """Check connected displays"""
        print("\n" + "="*60)
        print("🖥️  DISPLAYS")
        print("="*60)
        
        try:
            result = subprocess.run(
                ['system_profiler', 'SPDisplaysDataType'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            lines = result.stdout.split('\n')
            display_count = 0
            
            for line in lines:
                if 'Display Type:' in line or 'Resolution:' in line:
                    print(f"   {line.strip()}")
                elif 'Chipset Model:' in line or 'VRAM' in line:
                    display_count += 1
                    print(f"\n{display_count}. Display")
                    print(f"   {line.strip()}")
            
            if display_count == 0:
                display_count = 1  # At least built-in display
                print("\n1. Built-in Display")
            
            print(f"\n✓ Found {display_count} display(s)")
        
        except Exception as e:
            print(f"\n✗ Error checking displays: {e}")
    
    def check_camera_devices(self):
        """Check camera/video devices"""
        print("\n" + "="*60)
        print("📷 CAMERAS")
        print("="*60)
        
        try:
            result = subprocess.run(
                ['system_profiler', 'SPCameraDataType'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if 'No cameras' in result.stdout or not result.stdout.strip():
                print("\n✗ No external cameras detected")
                print("\n💡 Built-in FaceTime camera available")
            else:
                print("\n✓ Camera devices found:")
                for line in result.stdout.split('\n'):
                    if line.strip() and ':' in line:
                        print(f"   {line.strip()}")
        
        except Exception as e:
            print(f"\n✗ Error checking cameras: {e}")
    
    def get_system_info(self):
        """Get basic system information"""
        print("\n" + "="*60)
        print("💻 SYSTEM INFORMATION")
        print("="*60)
        
        try:
            # Computer name
            result = subprocess.run(['scutil', '--get', 'ComputerName'], 
                                  capture_output=True, text=True)
            print(f"\nComputer Name: {result.stdout.strip()}")
            
            # macOS version
            result = subprocess.run(['sw_vers'], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if line.strip():
                    print(f"{line.strip()}")
            
            # Uptime
            result = subprocess.run(['uptime'], capture_output=True, text=True)
            uptime_info = result.stdout.strip()
            if 'up' in uptime_info:
                print(f"\nUptime: {uptime_info.split('up')[1].split(',')[0].strip()}")
        
        except Exception as e:
            print(f"\n✗ Error getting system info: {e}")
    
    def generate_summary(self):
        """Generate summary"""
        print("\n" + "="*60)
        print("📊 SUMMARY")
        print("="*60)
        
        print(f"\nTotal Devices Found:")
        print(f"  USB Devices: {len(self.devices['usb'])}")
        print(f"  Storage Devices: {len(self.devices['storage'])}")
        print(f"  Network Interfaces: {len(self.devices['network'])}")
        print(f"  Bluetooth Devices: {len(self.devices.get('bluetooth', []))}")
        
        # Check for iPhone specifically
        has_iphone = any('iPhone' in str(d) for d in self.devices['usb'])
        print(f"\n📱 iPhone Connected: {'✓ YES' if has_iphone else '✗ NO'}")
        
        if not has_iphone:
            print("\n💡 To connect iPhone:")
            print("   1. Connect via USB cable")
            print("   2. Unlock iPhone")
            print("   3. Tap 'Trust This Computer'")
            print("   4. Run this script again")


def main():
    """Main function"""
    print("\n" + "="*60)
    print("  🔍 DEVICE CHECKER - Connected Peripherals")
    print("="*60)
    print(f"\nChecking devices... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    checker = DeviceChecker()
    
    # Run all checks
    checker.get_system_info()
    checker.check_usb_devices()
    checker.check_storage_devices()
    checker.check_network_interfaces()
    checker.check_bluetooth_devices()
    checker.check_displays()
    checker.check_camera_devices()
    checker.generate_summary()
    
    print("\n" + "="*60)
    print("✓ Device check complete!")
    print("="*60)
    print("\n💡 Tips:")
    print("  • For iPhone import: ./venv/bin/python3 import_from_iphone.py")
    print("  • For MediaPoster server: ./venv/bin/python3 quickstart.py")
    print("  • Refresh this check anytime to see new devices")
    print()


if __name__ == "__main__":
    main()
