"""
iPhone Direct File Access Service
==================================
Uses libimobiledevice tools to access iPhone files directly via AFC.
Alternative to Image Capture for automated file transfer.
"""

import subprocess
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
import tempfile
import shutil

logger = logging.getLogger(__name__)


class iPhoneDirectAccess:
    """
    Direct access to iPhone files using libimobiledevice.
    
    This provides programmatic access to iPhone files without
    requiring Image Capture or manual intervention.
    """
    
    def __init__(self):
        """Initialize iPhone direct access service."""
        self.mount_point: Optional[Path] = None
    
    def check_device_connected(self) -> Optional[str]:
        """
        Check if iPhone is connected and return UDID.
        
        Returns:
            Device UDID if connected, None otherwise
        """
        try:
            result = subprocess.run(
                ['idevice_id', '-l'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                udids = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
                if udids:
                    logger.info(f"Device connected: {udids[0][:20]}...")
                    return udids[0]
            
            return None
        except Exception as e:
            logger.warning(f"Error checking device: {e}")
            return None
    
    def get_device_info(self, udid: Optional[str] = None) -> Dict[str, Any]:
        """
        Get device information.
        
        Args:
            udid: Device UDID (optional, will auto-detect if not provided)
        
        Returns:
            Dictionary with device info
        """
        if not udid:
            udid = self.check_device_connected()
            if not udid:
                return {}
        
        try:
            result = subprocess.run(
                ['ideviceinfo', '-u', udid] if udid else ['ideviceinfo'],
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
                return info
        except Exception as e:
            logger.warning(f"Error getting device info: {e}")
        
        return {}
    
    def pair_device(self, udid: Optional[str] = None) -> bool:
        """
        Pair with iPhone (required for file access).
        
        Args:
            udid: Device UDID (optional)
        
        Returns:
            True if paired successfully
        """
        if not udid:
            udid = self.check_device_connected()
            if not udid:
                return False
        
        try:
            cmd = ['idevicepair', '-u', udid, 'pair'] if udid else ['idevicepair', 'pair']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                output = result.stdout + result.stderr
                if "SUCCESS" in output or "Paired" in output or "already paired" in output.lower():
                    logger.info("Device paired successfully")
                    return True
            
            logger.warning(f"Pairing failed: {result.stderr.strip()}")
            return False
        except Exception as e:
            logger.warning(f"Pairing error: {e}")
            return False
    
    def list_media_files(self, udid: Optional[str] = None, media_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        List media files on iPhone using ideviceinstaller or backup method.
        
        Note: Direct file listing via AFC requires ifuse (Linux) or pymobiledevice3.
        On macOS, we fall back to using Image Capture automation or backup extraction.
        
        Args:
            udid: Device UDID (optional)
            media_types: List of media types to find (default: ["video", "image"])
        
        Returns:
            List of file information dictionaries
        """
        if media_types is None:
            media_types = ["video", "image"]
        
        if not udid:
            udid = self.check_device_connected()
            if not udid:
                return []
        
        # On macOS without ifuse, we can't directly list files via AFC
        # This would require pymobiledevice3 or ifuse (Linux only)
        logger.warning("Direct file listing not available on macOS without ifuse")
        logger.info("Falling back to Image Capture method for file access")
        
        return []
    
    def transfer_files_direct(
        self,
        destination: Path,
        udid: Optional[str] = None,
        media_types: List[str] = None,
        max_files: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Transfer files directly from iPhone to destination.
        
        On macOS, this uses Image Capture automation as fallback
        since direct AFC access requires ifuse (Linux only).
        
        Args:
            destination: Destination directory
            udid: Device UDID (optional)
            media_types: Media types to transfer (default: ["video", "image"])
            max_files: Maximum number of files to transfer (None = all)
        
        Returns:
            Transfer result dictionary
        """
        if media_types is None:
            media_types = ["video", "image"]
        
        if not udid:
            udid = self.check_device_connected()
            if not udid:
                return {
                    "success": False,
                    "error": "No device connected",
                    "transferred": 0
                }
        
        # Pair device first
        if not self.pair_device(udid):
            logger.warning("Device pairing failed, but continuing...")
        
        # On macOS, we need to use Image Capture automation
        # Direct AFC file access requires ifuse which is Linux-only
        logger.info("Using Image Capture automation for file transfer (macOS)")
        
        # This will be handled by the existing Image Capture automation
        # in the API endpoint
        return {
            "success": False,
            "error": "Direct file transfer requires ifuse (Linux) or Image Capture automation (macOS)",
            "transferred": 0,
            "recommendation": "Use Image Capture automation endpoint instead"
        }


def test_direct_access():
    """Test direct iPhone access capabilities."""
    print("=" * 60)
    print("iPhone Direct Access Test")
    print("=" * 60)
    print()
    
    service = iPhoneDirectAccess()
    
    # Check device
    udid = service.check_device_connected()
    if not udid:
        print("❌ No device connected")
        return
    
    print(f"✅ Device connected: {udid[:20]}...")
    
    # Get device info
    info = service.get_device_info(udid)
    if info:
        print(f"✅ Device: {info.get('DeviceName', 'Unknown')}")
        print(f"   Model: {info.get('ProductType', 'Unknown')}")
        print(f"   iOS: {info.get('ProductVersion', 'Unknown')}")
    
    # Pair device
    if service.pair_device(udid):
        print("✅ Device paired")
    else:
        print("⚠️  Pairing failed or already paired")
    
    print("\n" + "=" * 60)
    print("Note: Direct file access on macOS requires:")
    print("  - ifuse (Linux only) OR")
    print("  - pymobiledevice3 (Python library) OR")
    print("  - Image Capture automation (current method)")
    print("=" * 60)


if __name__ == "__main__":
    test_direct_access()

