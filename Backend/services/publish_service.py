"""
Publish Service
Handles the full publish flow:
1. Upload media to Google Drive (get public URL)
2. Upload to Blotato via /v2/media (get Blotato-hosted URL)
3. Publish to platform via /v2/posts
4. Delete from Google Drive after successful publish
"""

import os
import asyncio
from pathlib import Path
from typing import Optional, Dict, List, Any
from loguru import logger
import httpx
from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path, override=True)


class PublishService:
    """Service to handle full publish flow with Google Drive staging"""
    
    BLOTATO_BASE_URL = "https://backend.blotato.com/v2"
    
    def __init__(self):
        self.blotato_api_key = os.getenv("BLOTATO_API_KEY")
        self.gdrive_uploader = None
        
    def _get_blotato_headers(self) -> dict:
        """Get headers for Blotato API requests"""
        return {
            "Content-Type": "application/json",
            "blotato-api-key": self.blotato_api_key or "",
        }
    
    def _init_gdrive(self):
        """Initialize Google Drive uploader"""
        if self.gdrive_uploader is None:
            from modules.cloud_staging.google_drive import GoogleDriveUploader
            self.gdrive_uploader = GoogleDriveUploader()
            if not self.gdrive_uploader.authenticate():
                raise Exception("Failed to authenticate with Google Drive")
        return self.gdrive_uploader
    
    async def upload_to_supabase(self, file_path: Path) -> Optional[Dict]:
        """
        Upload file to Supabase Storage and get public URL
        
        Returns:
            Dict with file_id and public_url, or None if failed
        """
        try:
            from services.supabase_storage import SupabaseStorageService
            import uuid
            
            storage = SupabaseStorageService()
            
            # Generate unique ID for staging file
            staging_id = f"staging_{uuid.uuid4().hex[:12]}"
            extension = file_path.suffix.lstrip('.').lower() or 'mp4'
            
            # Upload to staging folder
            storage_path = f"staging/{staging_id}.{extension}"
            
            with open(file_path, 'rb') as f:
                result = storage.client.storage.from_(storage.bucket_name).upload(
                    path=storage_path,
                    file=f,
                    file_options={"content-type": f"video/{extension}"}
                )
            
            # Get public URL
            public_url = storage.client.storage.from_(storage.bucket_name).get_public_url(storage_path)
            
            logger.success(f"✓ Uploaded to Supabase Storage: {file_path.name}")
            logger.info(f"  Public URL: {public_url}")
            
            return {
                'file_id': staging_id,
                'storage_path': storage_path,
                'public_url': public_url,
                'name': file_path.name
            }
            
        except Exception as e:
            logger.error(f"Supabase Storage upload failed: {e}")
            return None
    
    async def delete_from_supabase(self, storage_path: str) -> bool:
        """Delete file from Supabase Storage after successful publish"""
        try:
            from services.supabase_storage import SupabaseStorageService
            storage = SupabaseStorageService()
            storage.client.storage.from_(storage.bucket_name).remove([storage_path])
            logger.success(f"✓ Deleted from Supabase Storage: {storage_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete from Supabase Storage: {e}")
            return False
    
    async def upload_to_gdrive(self, file_path: Path) -> Optional[Dict]:
        """
        Upload file to Google Drive and make it publicly accessible
        
        Returns:
            Dict with file_id and public_url, or None if failed
        """
        try:
            gdrive = self._init_gdrive()
            
            # Get or create staging folder
            folder_id = gdrive.get_or_create_folder("MediaPoster_Staging")
            
            # Upload file
            result = gdrive.upload_file(file_path, folder_id)
            if not result:
                logger.error("Failed to upload to Google Drive")
                return None
            
            file_id = result['id']
            
            # Make file publicly accessible
            gdrive.service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()
            
            # Use Google Drive API URL format which bypasses virus scan for large files
            # Format: https://www.googleapis.com/drive/v3/files/{FILE_ID}?alt=media&key={API_KEY}
            # This requires an API key from Google Cloud Console
            google_api_key = os.getenv("GOOGLE_DRIVE_API_KEY")
            
            if google_api_key:
                # Use API URL format (bypasses virus scan for large files)
                public_url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&key={google_api_key}"
                logger.info("Using Google Drive API URL format (bypasses virus scan)")
            else:
                # Fallback to standard download URL (may fail for files >100MB)
                file_metadata = gdrive.service.files().get(
                    fileId=file_id,
                    fields='webContentLink'
                ).execute()
                public_url = file_metadata.get('webContentLink') or f"https://drive.google.com/uc?export=download&id={file_id}"
                logger.warning("No GOOGLE_DRIVE_API_KEY set - using standard URL (may fail for large files)")
            
            logger.success(f"✓ Uploaded to Google Drive: {file_path.name}")
            logger.info(f"  Public URL: {public_url}")
            
            return {
                'file_id': file_id,
                'public_url': public_url,
                'name': result['name']
            }
            
        except Exception as e:
            logger.error(f"Google Drive upload failed: {e}")
            return None
    
    async def upload_to_blotato(self, public_url: str) -> Optional[str]:
        """
        Upload media to Blotato via /v2/media endpoint
        
        Args:
            public_url: Publicly accessible URL to the media
            
        Returns:
            Blotato-hosted media URL or None if failed
        """
        try:
            async with httpx.AsyncClient(timeout=300) as client:
                response = await client.post(
                    f"{self.BLOTATO_BASE_URL}/media",
                    headers=self._get_blotato_headers(),
                    json={"url": public_url}
                )
                response.raise_for_status()
                result = response.json()
                
                blotato_url = result.get('url')
                logger.success(f"✓ Uploaded to Blotato: {blotato_url}")
                return blotato_url
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Blotato media upload failed: {e.response.status_code} - {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Blotato media upload error: {e}")
            return None
    
    async def publish_to_platform(
        self,
        account_id: str,
        platform: str,
        text: str,
        media_urls: List[str],
        target_config: Optional[Dict] = None,
        scheduled_time: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish to a social media platform via Blotato /v2/posts
        
        Returns:
            Dict with success status, post_submission_id, and any errors
        """
        try:
            # Build target configuration with platform-specific defaults
            target = target_config.copy() if target_config else {}
            target['targetType'] = platform
            
            # Add platform-specific defaults to ensure public visibility
            if platform == 'tiktok':
                target.setdefault('privacyLevel', 'PUBLIC_TO_EVERYONE')
                target.setdefault('disabledComments', False)
                target.setdefault('disabledDuet', False)
                target.setdefault('disabledStitch', False)
                target.setdefault('isBrandedContent', False)
                target.setdefault('isYourBrand', False)
                target.setdefault('isAiGenerated', True)
            elif platform == 'youtube':
                target.setdefault('privacyStatus', 'public')
                target.setdefault('shouldNotifySubscribers', True)
                target.setdefault('isMadeForKids', False)
            elif platform == 'instagram':
                target.setdefault('mediaType', 'reel')  # Default to reel for video
            elif platform == 'facebook':
                # Facebook posts to pages are public by default
                pass
            elif platform == 'linkedin':
                # LinkedIn posts are public by default
                pass
            elif platform == 'twitter':
                # Twitter posts are public by default
                pass
            elif platform == 'threads':
                # Threads posts are public by default
                pass
            elif platform == 'bluesky':
                # Bluesky posts are public by default
                pass
            elif platform == 'pinterest':
                # Pinterest pins are public by default
                pass
            
            # Build payload per Blotato v2 spec
            payload = {
                "post": {
                    "accountId": account_id,
                    "content": {
                        "text": text,
                        "mediaUrls": media_urls,
                        "platform": platform
                    },
                    "target": target
                }
            }
            
            # Add scheduling if specified
            if scheduled_time:
                payload['scheduledTime'] = scheduled_time
            
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.BLOTATO_BASE_URL}/posts",
                    headers=self._get_blotato_headers(),
                    json=payload
                )
                response.raise_for_status()
                result = response.json()
                
                post_submission_id = result.get('postSubmissionId')
                logger.success(f"✓ Published to {platform}: {post_submission_id}")
                
                return {
                    'success': True,
                    'post_submission_id': post_submission_id,
                    'platform': platform
                }
                
        except httpx.HTTPStatusError as e:
            error_msg = f"{e.response.status_code}: {e.response.text}"
            logger.error(f"Publish failed: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'platform': platform
            }
        except Exception as e:
            logger.error(f"Publish error: {e}")
            return {
                'success': False,
                'error': str(e),
                'platform': platform
            }
    
    async def delete_from_gdrive(self, file_id: str) -> bool:
        """Delete file from Google Drive after successful publish"""
        try:
            gdrive = self._init_gdrive()
            return gdrive.delete_file(file_id)
        except Exception as e:
            logger.error(f"Failed to delete from Google Drive: {e}")
            return False
    
    async def full_publish_flow(
        self,
        file_path: Path,
        account_id: str,
        platform: str,
        text: str,
        target_config: Optional[Dict] = None,
        scheduled_time: Optional[str] = None,
        cleanup_storage: bool = True,
        use_supabase: bool = True
    ) -> Dict[str, Any]:
        """
        Execute the full publish flow:
        1. Upload to cloud storage (Supabase or Google Drive)
        2. Upload to Blotato
        3. Publish to platform
        4. Cleanup storage (optional)
        
        Returns:
            Dict with status and details of each step
        """
        result = {
            'success': False,
            'steps': {},
            'error': None
        }
        
        storage_info = None
        
        try:
            # Step 1: Upload to cloud storage
            if use_supabase:
                logger.info(f"Step 1: Uploading to Supabase Storage...")
                storage_result = await self.upload_to_supabase(file_path)
                if not storage_result:
                    result['error'] = "Failed to upload to Supabase Storage"
                    result['steps']['storage_upload'] = {'success': False}
                    return result
                storage_info = {'type': 'supabase', 'path': storage_result['storage_path']}
            else:
                logger.info(f"Step 1: Uploading to Google Drive...")
                storage_result = await self.upload_to_gdrive(file_path)
                if not storage_result:
                    result['error'] = "Failed to upload to Google Drive"
                    result['steps']['storage_upload'] = {'success': False}
                    return result
                storage_info = {'type': 'gdrive', 'file_id': storage_result['file_id']}
            
            result['steps']['storage_upload'] = {
                'success': True,
                'storage_type': storage_info['type'],
                'public_url': storage_result['public_url']
            }
            
            # Step 2: Upload to Blotato
            logger.info(f"Step 2: Uploading to Blotato...")
            blotato_url = await self.upload_to_blotato(storage_result['public_url'])
            if not blotato_url:
                result['error'] = "Failed to upload to Blotato"
                result['steps']['blotato_upload'] = {'success': False}
                return result
            
            result['steps']['blotato_upload'] = {
                'success': True,
                'blotato_url': blotato_url
            }
            
            # Step 3: Publish to platform
            logger.info(f"Step 3: Publishing to {platform}...")
            publish_result = await self.publish_to_platform(
                account_id=account_id,
                platform=platform,
                text=text,
                media_urls=[blotato_url],
                target_config=target_config,
                scheduled_time=scheduled_time
            )
            
            result['steps']['publish'] = publish_result
            
            if not publish_result['success']:
                result['error'] = publish_result.get('error', 'Publish failed')
                return result
            
            result['success'] = True
            result['post_submission_id'] = publish_result.get('post_submission_id')
            
            # Step 4: Cleanup storage (optional)
            if cleanup_storage and storage_info:
                logger.info(f"Step 4: Cleaning up storage...")
                if storage_info['type'] == 'supabase':
                    cleanup_success = await self.delete_from_supabase(storage_info['path'])
                else:
                    cleanup_success = await self.delete_from_gdrive(storage_info['file_id'])
                result['steps']['cleanup'] = {'success': cleanup_success}
            
            return result
            
        except Exception as e:
            logger.error(f"Full publish flow failed: {e}")
            result['error'] = str(e)
            return result
        
        finally:
            # Cleanup on failure if we uploaded to storage
            if not result['success'] and storage_info and cleanup_storage:
                logger.info("Cleaning up storage after failure...")
                if storage_info['type'] == 'supabase':
                    await self.delete_from_supabase(storage_info['path'])
                else:
                    await self.delete_from_gdrive(storage_info['file_id'])


    async def get_post_status(self, post_submission_id: str) -> Dict[str, Any]:
        """
        Get post status from Blotato API
        Rate limit: 60 requests/minute
        
        Returns:
            Dict with status, publicUrl, errorMessage
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"{self.BLOTATO_BASE_URL}/posts/{post_submission_id}",
                    headers=self._get_blotato_headers()
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Get post status failed: {e.response.status_code} - {e.response.text}")
            return {'error': str(e)}
        except Exception as e:
            logger.error(f"Get post status error: {e}")
            return {'error': str(e)}
    
    async def poll_for_post_url(
        self,
        post_submission_id: str,
        max_attempts: int = 30,
        poll_interval_seconds: float = 2.0,
        rate_limit_margin: float = 1.0
    ) -> Dict[str, Any]:
        """
        Poll Blotato API for post status until published or failed
        
        Args:
            post_submission_id: The submission ID from publish response
            max_attempts: Maximum polling attempts (default 30 = ~1 minute)
            poll_interval_seconds: Seconds between polls (default 2.0)
            rate_limit_margin: Extra seconds to add for rate limit safety (default 1.0)
        
        Returns:
            Dict with status, publicUrl, platform info
        """
        actual_interval = poll_interval_seconds + rate_limit_margin
        
        for attempt in range(max_attempts):
            logger.info(f"Polling post status (attempt {attempt + 1}/{max_attempts})...")
            
            status_result = await self.get_post_status(post_submission_id)
            
            if 'error' in status_result:
                logger.warning(f"Poll error: {status_result['error']}")
                await asyncio.sleep(actual_interval)
                continue
            
            status = status_result.get('status', '').lower()
            public_url = status_result.get('publicUrl')
            error_message = status_result.get('errorMessage')
            
            if status == 'published' and public_url:
                logger.success(f"✓ Post published! URL: {public_url}")
                return {
                    'success': True,
                    'status': 'published',
                    'public_url': public_url,
                    'post_submission_id': post_submission_id
                }
            elif status == 'failed' or error_message:
                logger.error(f"Post failed: {error_message}")
                return {
                    'success': False,
                    'status': 'failed',
                    'error': error_message,
                    'post_submission_id': post_submission_id
                }
            elif status in ['pending', 'processing', 'queued']:
                logger.info(f"Post status: {status}, waiting...")
                await asyncio.sleep(actual_interval)
            else:
                logger.warning(f"Unknown status: {status}")
                await asyncio.sleep(actual_interval)
        
        logger.warning(f"Max polling attempts reached for {post_submission_id}")
        return {
            'success': False,
            'status': 'timeout',
            'error': 'Max polling attempts reached',
            'post_submission_id': post_submission_id
        }
    
    async def full_publish_with_url_tracking(
        self,
        file_path: Path,
        account_id: str,
        platform: str,
        text: str,
        media_id: str = None,
        target_config: Optional[Dict] = None,
        scheduled_time: Optional[str] = None,
        cleanup_storage: bool = True,
        use_supabase: bool = False,
        poll_for_url: bool = True
    ) -> Dict[str, Any]:
        """
        Full publish flow with URL tracking:
        1. Upload to cloud storage
        2. Upload to Blotato
        3. Publish to platform
        4. Poll for public URL
        5. Store URL for analytics
        6. Cleanup storage
        
        Returns:
            Dict with full result including public_url if available
        """
        # First do the standard publish flow
        result = await self.full_publish_flow(
            file_path=file_path,
            account_id=account_id,
            platform=platform,
            text=text,
            target_config=target_config,
            scheduled_time=scheduled_time,
            cleanup_storage=cleanup_storage,
            use_supabase=use_supabase
        )
        
        if not result['success']:
            return result
        
        post_submission_id = result.get('post_submission_id')
        
        # Poll for URL if requested and we have a submission ID
        if poll_for_url and post_submission_id:
            logger.info("Step 5: Polling for public URL...")
            url_result = await self.poll_for_post_url(post_submission_id)
            
            result['steps']['url_tracking'] = url_result
            
            if url_result.get('success'):
                result['public_url'] = url_result.get('public_url')
                
                # Store in database for analytics tracking
                if media_id:
                    await self._store_post_record(
                        media_id=media_id,
                        platform=platform,
                        post_submission_id=post_submission_id,
                        public_url=url_result.get('public_url'),
                        account_id=account_id,
                        caption=text
                    )
        
        return result
    
    async def _store_post_record(
        self,
        media_id: str,
        platform: str,
        post_submission_id: str,
        public_url: str,
        account_id: str,
        caption: str = None
    ) -> bool:
        """
        Store post record in database for analytics tracking
        Uses the existing PlatformPost model
        """
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "http://localhost:5555/api/posted-content/record",
                    json={
                        "media_id": media_id,
                        "platform": platform,
                        "blotato_submission_id": post_submission_id,
                        "platform_url": public_url,
                        "blotato_account_id": account_id,
                        "caption": caption,
                        "status": "published"
                    }
                )
                if response.status_code == 200:
                    logger.success(f"✓ Post record stored for analytics tracking")
                    return True
                else:
                    logger.warning(f"Failed to store post record: {response.text}")
                    return False
        except Exception as e:
            logger.error(f"Error storing post record: {e}")
            return False


# Singleton instance
_publish_service = None

def get_publish_service() -> PublishService:
    """Get singleton instance of PublishService"""
    global _publish_service
    if _publish_service is None:
        _publish_service = PublishService()
    return _publish_service
