"""
Storage Manager
Coordinate multiple storage providers
"""
from pathlib import Path
from typing import Dict, Optional, List
from loguru import logger
from .google_drive import GoogleDriveUploader


class StorageManager:
    """Manage multiple cloud storage providers"""
    
    def __init__(self):
        """Initialize storage manager"""
        self.providers = {}
        self.default_provider = None
        
        logger.info("Storage manager initialized")
    
    def add_provider(
        self,
        name: str,
        provider,
        set_default: bool = False
    ):
        """
        Add storage provider
        
        Args:
            name: Provider name
            provider: Provider instance
            set_default: Set as default provider
        """
        self.providers[name] = provider
        
        if set_default or not self.default_provider:
            self.default_provider = name
        
        logger.info(f"Added provider: {name}")
    
    def upload_clip(
        self,
        clip_path: Path,
        metadata: Optional[Dict] = None,
        provider: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Upload clip to storage
        
        Args:
            clip_path: Path to clip
            metadata: Clip metadata
            provider: Provider name (uses default if None)
            
        Returns:
            Upload result with links
        """
        provider_name = provider or self.default_provider
        
        if not provider_name:
            logger.error("No storage provider configured")
            return None
        
        if provider_name not in self.providers:
            logger.error(f"Provider not found: {provider_name}")
            return None
        
        logger.info(f"Uploading to {provider_name}...")
        
        provider_instance = self.providers[provider_name]
        result = provider_instance.upload_clip(clip_path, metadata)
        
        if result:
            result['provider'] = provider_name
        
        return result
    
    def upload_batch(
        self,
        clip_paths: List[Path],
        metadata_list: Optional[List[Dict]] = None,
        provider: Optional[str] = None
    ) -> List[Dict]:
        """Upload multiple clips"""
        results = []
        
        for i, clip_path in enumerate(clip_paths):
            metadata = metadata_list[i] if metadata_list else None
            
            result = self.upload_clip(clip_path, metadata, provider)
            if result:
                results.append(result)
        
        logger.success(f"✓ Uploaded {len(results)}/{len(clip_paths)} clips")
        return results
    
    def get_storage_info(self) -> Dict:
        """Get storage info from all providers"""
        info = {}
        
        for name, provider in self.providers.items():
            if hasattr(provider, 'get_storage_quota'):
                try:
                    info[name] = provider.get_storage_quota()
                except Exception as e:
                    logger.error(f"Failed to get {name} info: {e}")
                    info[name] = {'error': str(e)}
        
        return info


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("STORAGE MANAGER")
    print("="*60)
    print("\nCoordinates multiple storage providers.")
    print("Currently supports: Google Drive")
    print("\nFor testing, use test_phase4.py")
