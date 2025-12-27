"""
iPhone Direct Import Service
============================
Direct file access and import from iPhone using pymobiledevice3.
Uses fingerprinting to avoid duplicates.
"""

import json
import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Try to import pymobiledevice3
try:
    from pymobiledevice3.lockdown import LockdownClient
    from pymobiledevice3.services.afc import AfcService
    PYMOBILEDEVICE3_AVAILABLE = True
except ImportError:
    PYMOBILEDEVICE3_AVAILABLE = False
    logger.warning("pymobiledevice3 not available. Install with: pip install pymobiledevice3")


class iPhoneDirectImporter:
    """
    Direct iPhone file importer with duplicate detection via fingerprinting.
    
    Uses pymobiledevice3 to access iPhone files directly, then uses
    fast fingerprinting (first+last bytes + size) to detect duplicates.
    """
    
    def __init__(self, destination_dir: Path, manifest_file: Optional[Path] = None):
        """
        Initialize importer.
        
        Args:
            destination_dir: Directory to import files to
            manifest_file: Path to manifest file (default: destination/.import_manifest.jsonl)
        """
        self.destination_dir = Path(destination_dir)
        self.destination_dir.mkdir(parents=True, exist_ok=True)
        
        self.manifest_file = manifest_file or (self.destination_dir / ".import_manifest.jsonl")
        self.index_file = self.destination_dir / ".import_index.json"
        
        self.video_exts = {".mov", ".mp4", ".m4v", ".m4a"}
        self.image_exts = {".jpg", ".jpeg", ".png", ".heic", ".heif"}
        
        self.lockdown: Optional[LockdownClient] = None
        self.afc: Optional[AfcService] = None
    
    def connect(self) -> bool:
        """
        Connect to iPhone via pymobiledevice3.
        
        Returns:
            True if connected successfully
        """
        if not PYMOBILEDEVICE3_AVAILABLE:
            logger.error("pymobiledevice3 not available")
            return False
        
        try:
            self.lockdown = LockdownClient()
            self.afc = AfcService(self.lockdown)
            
            device_name = self.lockdown.device_info.get('DeviceName', 'Unknown')
            logger.info(f"✅ Connected to: {device_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to device: {e}")
            logger.info("Make sure iPhone is unlocked and 'Trust This Computer' is accepted")
            return False
    
    def fingerprint(self, file_path: Path, sample_bytes: int = 4 * 1024 * 1024) -> str:
        """
        Generate fast fingerprint for duplicate detection.
        
        Uses: sha256(first N bytes + last N bytes + file_size)
        Much faster than hashing entire video.
        
        Args:
            file_path: Path to file
            sample_bytes: Number of bytes to sample from start/end (default: 4MB)
        
        Returns:
            SHA256 hex digest
        """
        try:
            stat = file_path.stat()
            size = stat.st_size
        except Exception:
            # If we can't stat, try to get size from AFC
            try:
                if self.afc:
                    # Get file info from AFC
                    info = self.afc.get_file_info(str(file_path))
                    size = info.get('st_size', 0)
                else:
                    return ""
            except:
                return ""
        
        h = hashlib.sha256()
        h.update(str(size).encode())
        
        try:
            with open(file_path, "rb") as f:
                # Read head
                head = f.read(min(sample_bytes, size))
                h.update(head)
                
                # Read tail if file is large enough
                if size > sample_bytes:
                    f.seek(max(0, size - sample_bytes), os.SEEK_SET)
                    tail = f.read(sample_bytes)
                    h.update(tail)
        except Exception as e:
            logger.warning(f"Error reading file for fingerprint: {e}")
            # Fallback: use size + mtime
            try:
                mtime = file_path.stat().st_mtime
                h.update(str(mtime).encode())
            except:
                pass
        
        return h.hexdigest()
    
    def fingerprint_from_afc(self, afc_path: str, size: int, sample_bytes: int = 4 * 1024 * 1024) -> str:
        """
        Generate fingerprint from AFC file handle.
        
        Args:
            afc_path: Path on device (e.g., "/DCIM/100APPLE/IMG_1234.MOV")
            size: File size in bytes
            sample_bytes: Bytes to sample
        
        Returns:
            SHA256 hex digest
        """
        h = hashlib.sha256()
        h.update(str(size).encode())
        
        try:
            if not self.afc:
                return ""
            
            # Read head
            head_data = self.afc.get_file_contents(afc_path, max_size=sample_bytes)
            if head_data:
                h.update(head_data[:min(sample_bytes, len(head_data))])
            
            # Read tail if file is large
            if size > sample_bytes:
                # Seek to tail position
                tail_start = max(0, size - sample_bytes)
                tail_data = self.afc.get_file_contents(afc_path, offset=tail_start, max_size=sample_bytes)
                if tail_data:
                    h.update(tail_data)
        except Exception as e:
            logger.warning(f"Error generating fingerprint from AFC: {e}")
            # Fallback: use size only
            pass
        
        return h.hexdigest()
    
    def load_index(self) -> Dict[str, str]:
        """Load fingerprint index from disk."""
        if self.index_file.exists():
            try:
                return json.loads(self.index_file.read_text())
            except Exception as e:
                logger.warning(f"Error loading index: {e}")
        return {}
    
    def save_index(self, index: Dict[str, str]):
        """Save fingerprint index to disk."""
        try:
            self.index_file.write_text(json.dumps(index, indent=2))
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    def build_index_from_destination(self) -> Dict[str, str]:
        """Build fingerprint index from existing files in destination."""
        logger.info("Building index from destination directory...")
        index = {}
        
        if not self.destination_dir.exists():
            return index
        
        count = 0
        for p in self.destination_dir.rglob("*"):
            if p.is_file() and p.suffix.lower() in (self.video_exts | self.image_exts):
                try:
                    fp = self.fingerprint(p)
                    if fp:
                        index[fp] = str(p)
                        count += 1
                except Exception as e:
                    logger.debug(f"Error fingerprinting {p}: {e}")
        
        logger.info(f"Indexed {count} existing files")
        return index
    
    def list_iphone_files(self, media_types: List[str] = None) -> List[Dict[str, Any]]:
        """
        List files on iPhone via AFC.
        
        Args:
            media_types: List of media types to find (default: ["video", "image"])
        
        Returns:
            List of file info dictionaries
        """
        if not self.afc:
            return []
        
        if media_types is None:
            media_types = ["video", "image"]
        
        files = []
        exts = set()
        if "video" in media_types:
            exts.update(self.video_exts)
        if "image" in media_types:
            exts.update(self.image_exts)
        
        try:
            # List DCIM directory
            dcim_items = self.afc.listdir('/DCIM')
            
            for item in dcim_items:
                item_path = f'/DCIM/{item}'
                try:
                    # Check if it's a directory
                    sub_items = self.afc.listdir(item_path)
                    
                    # It's a directory, check sub-items
                    for sub_item in sub_items:
                        sub_path = f'{item_path}/{sub_item}'
                        ext = Path(sub_item).suffix.lower()
                        
                        if ext in exts:
                            try:
                                # Get file info
                                info = self.afc.get_file_info(sub_path)
                                files.append({
                                    'path': sub_path,
                                    'name': sub_item,
                                    'size': info.get('st_size', 0),
                                    'type': 'video' if ext in self.video_exts else 'image'
                                })
                            except:
                                pass
                except:
                    # Not a directory, might be a file
                    ext = Path(item).suffix.lower()
                    if ext in exts:
                        try:
                            info = self.afc.get_file_info(item_path)
                            files.append({
                                'path': item_path,
                                'name': item,
                                'size': info.get('st_size', 0),
                                'type': 'video' if ext in self.video_exts else 'image'
                            })
                        except:
                            pass
        except Exception as e:
            logger.error(f"Error listing iPhone files: {e}")
        
        return files
    
    def import_files(
        self,
        media_types: List[str] = None,
        max_files: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Import files from iPhone with duplicate detection.
        
        Args:
            media_types: Media types to import (default: ["video", "image"])
            max_files: Maximum files to import (None = all)
            date_from: Only import files newer than this date
            date_to: Only import files older than this date
        
        Returns:
            Import result dictionary
        """
        if not self.afc:
            return {
                "success": False,
                "error": "Not connected to device",
                "imported": 0,
                "skipped": 0
            }
        
        if media_types is None:
            media_types = ["video", "image"]
        
        # Load or build index
        index = self.load_index()
        if not index:
            index = self.build_index_from_destination()
        
        # List files on iPhone
        iphone_files = self.list_iphone_files(media_types)
        
        logger.info(f"Found {len(iphone_files)} files on iPhone")
        
        imported = 0
        skipped = 0
        errors = 0
        
        # Ensure manifest file parent exists
        self.manifest_file.parent.mkdir(parents=True, exist_ok=True)
        
        for file_info in iphone_files:
            if max_files and imported >= max_files:
                break
            
            afc_path = file_info['path']
            file_name = file_info['name']
            file_size = file_info['size']
            
            try:
                # Generate fingerprint
                fp = self.fingerprint_from_afc(afc_path, file_size)
                
                if not fp:
                    logger.warning(f"Could not generate fingerprint for {file_name}")
                    errors += 1
                    continue
                
                # Check if duplicate
                if fp in index:
                    logger.debug(f"Skipping duplicate: {file_name}")
                    skipped += 1
                    continue
                
                # Download file
                dst = self.destination_dir / file_name
                if dst.exists():
                    # Add timestamp suffix if collision
                    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    stem = Path(file_name).stem
                    suffix = Path(file_name).suffix
                    dst = self.destination_dir / f"{stem}_{stamp}{suffix}"
                
                # Download from AFC
                logger.info(f"Importing: {file_name} ({file_size / (1024*1024):.1f} MB)")
                with open(dst, 'wb') as f:
                    self.afc.get_file_contents(afc_path, f)
                
                # Update index
                index[fp] = str(dst)
                
                # Log to manifest
                manifest_entry = {
                    "src": afc_path,
                    "dst": str(dst),
                    "fp": fp,
                    "size": file_size,
                    "imported_at": datetime.now().isoformat()
                }
                with open(self.manifest_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(manifest_entry) + '\n')
                
                imported += 1
                
            except Exception as e:
                logger.error(f"Error importing {file_name}: {e}", exc_info=True)
                errors += 1
        
        # Save updated index
        self.save_index(index)
        
        result = {
            "success": True,
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
            "total_found": len(iphone_files)
        }
        
        logger.info(f"Import complete: {imported} imported, {skipped} skipped, {errors} errors")
        return result
    
    def disconnect(self):
        """Disconnect from device."""
        self.afc = None
        self.lockdown = None


def test_direct_import():
    """Test direct import functionality."""
    print("=" * 60)
    print("iPhone Direct Import Test")
    print("=" * 60)
    print()
    
    if not PYMOBILEDEVICE3_AVAILABLE:
        print("❌ pymobiledevice3 not available")
        print("   Install with: pip install pymobiledevice3")
        return
    
    # Set destination (use default import path)
    import sys
    from pathlib import Path
    
    # Try to import from config, fallback to default
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from config.paths import get_iphone_import_dir
        dest_dir = get_iphone_import_dir()
    except ImportError:
        # Fallback to default path
        dest_dir = Path("/Volumes/My Passport/MediaPoster/workspace1/iphone_import")
        if not dest_dir.exists():
            dest_dir = Path.home() / "Documents" / "IphoneImport"
    
    print(f"Destination: {dest_dir}")
    print()
    
    # Create importer
    importer = iPhoneDirectImporter(dest_dir)
    
    # Connect
    if not importer.connect():
        print("❌ Failed to connect to device")
        return
    
    try:
        # List files
        print("📋 Listing files on iPhone...")
        files = importer.list_iphone_files(["video", "image"])
        print(f"   Found {len(files)} files")
        
        if files:
            print("\n   Sample files:")
            for f in files[:5]:
                size_mb = f['size'] / (1024 * 1024)
                print(f"   - {f['name']} ({size_mb:.1f} MB)")
        
        # Test import (dry run - just show what would be imported)
        print("\n" + "=" * 60)
        response = input("Import files? (y/n): ").strip().lower()
        if response == 'y':
            result = importer.import_files(media_types=["video", "image"], max_files=5)
            print(f"\n✅ Import complete:")
            print(f"   Imported: {result['imported']}")
            print(f"   Skipped: {result['skipped']}")
            print(f"   Errors: {result['errors']}")
        else:
            print("Skipping import")
    
    finally:
        importer.disconnect()


if __name__ == "__main__":
    test_direct_import()

