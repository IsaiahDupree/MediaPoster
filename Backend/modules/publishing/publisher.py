"""
Content Publisher
Orchestrates cloud upload and multi-platform publishing
"""
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
from datetime import datetime, timedelta

from .blotato_client import BlotatoClient
from modules.cloud_staging import StorageManager, GoogleDriveUploader


class ContentPublisher:
    """Orchestrate content publishing workflow"""
    
    def __init__(
        self,
        use_cloud_staging: bool = True,
        use_blotato: bool = True
    ):
        """
        Initialize content publisher
        
        Args:
            use_cloud_staging: Upload to cloud storage
            use_blotato: Post via Blotato
        """
        self.use_cloud_staging = use_cloud_staging
        self.use_blotato = use_blotato
        
        # Initialize services
        self.storage = None
        if use_cloud_staging:
            self.storage = StorageManager()
            drive = GoogleDriveUploader()
            self.storage.add_provider('google_drive', drive, set_default=True)
        
        self.blotato = None
        if use_blotato:
            self.blotato = BlotatoClient()
        
        logger.info(f"Content publisher initialized (cloud={use_cloud_staging}, blotato={use_blotato})")
    
    def publish_clip(
        self,
        clip_path: Path,
        platforms: List[str],
        metadata: Dict,
        schedule_delay_minutes: Optional[int] = None
    ) -> Dict:
        """
        Complete publishing workflow
        
        Args:
            clip_path: Path to clip
            platforms: Target platforms
            metadata: Clip metadata (caption, hashtags, etc.)
            schedule_delay_minutes: Delay before posting (None = immediate)
            
        Returns:
            Publishing result
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"PUBLISHING CLIP: {clip_path.name}")
        logger.info(f"Platforms: {', '.join(platforms)}")
        logger.info(f"{'='*60}")
        
        result = {
            'clip_path': str(clip_path),
            'platforms': platforms,
            'success': False,
            'storage': None,
            'posts': {}
        }
        
        # Step 1: Upload to cloud storage
        if self.use_cloud_staging and self.storage:
            logger.info("\n📤 Step 1/2: Uploading to cloud storage...")
            try:
                storage_result = self.storage.upload_clip(clip_path, metadata)
                if storage_result:
                    result['storage'] = storage_result
                    logger.success("✓ Cloud upload complete")
                else:
                    logger.warning("Cloud upload failed, continuing...")
            except Exception as e:
                logger.error(f"Cloud upload error: {e}")
        else:
            logger.info("\n📤 Step 1/2: Skipping cloud storage")
        
        # Step 2: Post to platforms via Blotato
        if self.use_blotato and self.blotato:
            logger.info("\n🚀 Step 2/2: Publishing to platforms...")
            try:
                # Calculate schedule time if delay specified
                schedule_time = None
                if schedule_delay_minutes:
                    future_time = datetime.utcnow() + timedelta(minutes=schedule_delay_minutes)
                    schedule_time = future_time.isoformat() + 'Z'
                    logger.info(f"   Scheduling for: {future_time.strftime('%Y-%m-%d %H:%M UTC')}")
                
                # Prepare caption and hashtags
                caption = metadata.get('caption', metadata.get('hook_text', ''))
                hashtags = metadata.get('hashtags', [])
                title = metadata.get('title', clip_path.stem)
                
                # Post to platforms
                post_result = self.blotato.post_clip(
                    clip_path,
                    platforms,
                    caption,
                    hashtags,
                    title,
                    schedule_time
                )
                
                if post_result:
                    result['posts'] = post_result
                    result['success'] = True
                    logger.success("✓ Publishing complete!")
                    
                    # Log platform URLs
                    if post_result.get('urls'):
                        logger.info("\n📱 Platform URLs:")
                        for platform, url in post_result['urls'].items():
                            logger.info(f"   {platform}: {url}")
                else:
                    logger.error("Publishing failed")
            except Exception as e:
                logger.error(f"Publishing error: {e}")
        else:
            logger.info("\n🚀 Step 2/2: Skipping Blotato posting")
            result['success'] = True  # Success if cloud upload worked
        
        return result
    
    def publish_batch(
        self,
        clips: List[Dict],
        stagger_minutes: int = 30
    ) -> List[Dict]:
        """
        Publish multiple clips with staggered scheduling
        
        Args:
            clips: List of dicts with 'path', 'platforms', 'metadata'
            stagger_minutes: Minutes between posts
            
        Returns:
            List of publish results
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH PUBLISHING: {len(clips)} clips")
        logger.info(f"Stagger: {stagger_minutes} minutes")
        logger.info(f"{'='*60}")
        
        results = []
        
        for i, clip_data in enumerate(clips):
            clip_path = Path(clip_data['path'])
            platforms = clip_data.get('platforms', ['tiktok'])
            metadata = clip_data.get('metadata', {})
            
            # Calculate delay for this clip
            delay = i * stagger_minutes if i > 0 else None
            
            logger.info(f"\n\n{'#'*60}")
            logger.info(f"CLIP {i+1}/{len(clips)}")
            if delay:
                logger.info(f"Scheduled: +{delay} minutes")
            logger.info(f"{'#'*60}")
            
            result = self.publish_clip(
                clip_path,
                platforms,
                metadata,
                schedule_delay_minutes=delay
            )
            
            results.append(result)
        
        successful = sum(1 for r in results if r['success'])
        
        logger.info(f"\n\n{'='*60}")
        logger.success(f"✓ BATCH COMPLETE: {successful}/{len(clips)} published")
        logger.info(f"{'='*60}")
        
        return results
    
    def get_publishing_status(
        self,
        post_id: str
    ) -> Optional[Dict]:
        """Get status of published post"""
        if not self.blotato:
            return None
        
        return self.blotato.get_post_status(post_id)
    
    def validate_clip_for_platforms(
        self,
        clip_path: Path,
        platforms: List[str]
    ) -> Dict:
        """
        Validate clip meets all platform requirements
        
        Args:
            clip_path: Path to clip
            platforms: Target platforms
            
        Returns:
            Validation results
        """
        if not self.blotato:
            return {'valid': False, 'error': 'Blotato not initialized'}
        
        results = {}
        all_valid = True
        
        for platform in platforms:
            validation = self.blotato.validate_clip_for_platform(clip_path, platform)
            results[platform] = validation
            
            if not validation['valid']:
                all_valid = False
                logger.warning(f"{platform}: {', '.join(validation['issues'])}")
        
        return {
            'all_valid': all_valid,
            'platforms': results
        }
    
    def get_connected_accounts(self) -> Optional[Dict]:
        """Get Blotato connected accounts"""
        if not self.blotato:
            return None
        
        return self.blotato.get_account_info()


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("CONTENT PUBLISHER")
    print("="*60)
    print("\nOrchestrates complete publishing workflow:")
    print("  1. Upload to Google Drive (backup)")
    print("  2. Post to TikTok/Instagram/YouTube via Blotato")
    print("\nFor testing, use test_phase4.py")
