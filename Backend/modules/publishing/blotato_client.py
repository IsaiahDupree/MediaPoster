"""
Blotato API Client
Multi-platform social media posting via Blotato
"""
import requests
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
from config import settings


class BlotatoClient:
    """Client for Blotato API v2"""
    
    BASE_URL = "https://backend.blotato.com"
    
    PLATFORM_CONFIGS = {
        'tiktok': {
            'max_video_size_mb': 287,
            'max_duration_seconds': 600,
            'aspect_ratios': ['9:16', '1:1'],
            'max_caption_length': 2200
        },
        'instagram': {
            'max_video_size_mb': 100,
            'max_duration_seconds': 90,
            'aspect_ratios': ['9:16', '4:5', '1:1'],
            'max_caption_length': 2200
        },
        'youtube': {
            'max_video_size_mb': 256,
            'max_duration_seconds': 60,
            'aspect_ratios': ['9:16'],
            'max_caption_length': 5000
        }
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Blotato client
        
        Args:
            api_key: Blotato API key
        """
        self.api_key = api_key or settings.blotato_api_key
        self.session = requests.Session()
        self.session.headers.update({
            'blotato-api-key': self.api_key,
            'Content-Type': 'application/json'
        })
        
        logger.info("Blotato client initialized (API v2)")
    
    def upload_media(
        self,
        file_path: Path,
        public_url: Optional[str] = None
    ) -> Optional[str]:
        """
        Upload media file to Blotato
        
        Args:
            file_path: Path to video file (for local testing)
            public_url: Public URL to media (preferred for production)
            
        Returns:
            Blotato media URL or None if failed
        """
        logger.info(f"Uploading media to Blotato...")
        
        try:
            # If public URL provided, use that (Blotato will download)
            if public_url:
                payload = {"url": public_url}
                logger.info(f"  Using public URL: {public_url}")
            else:
                # For local files, we'd need to host them first
                # This is a limitation - Blotato v2 API expects URLs
                logger.warning("Local file upload requires public URL")
                logger.warning("Consider uploading to S3/GCP/Drive first")
                return None
            
            response = self.session.post(
                f"{self.BASE_URL}/v2/media",
                json=payload,
                timeout=300
            )
            
            response.raise_for_status()
            result = response.json()
            
            # Response contains the new Blotato-hosted URL
            media_url = result.get('url')
            
            if media_url:
                logger.success(f"✓ Media uploaded: {media_url}")
            return media_url
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Upload failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def create_post(
        self,
        account_id: str,
        platform: str,
        text: str,
        media_urls: List[str],
        target_config: Optional[Dict] = None,
        scheduled_time: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Create a post on a specific platform (Blotato API v2)
        
        Args:
            account_id: Blotato account ID for the social account
            platform: Platform name ('twitter', 'instagram', 'tiktok', etc.)
            text: Post caption/text
            media_urls: List of Blotato media URLs
            target_config: Platform-specific target configuration
            scheduled_time: ISO 8601 timestamp for scheduling
            
        Returns:
            Post result with submission ID
        """
        logger.info(f"Creating {platform} post")
        
        # Build target configuration
        target = target_config or {}
        target['targetType'] = platform
        
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
        
        try:
            response = self.session.post(
                f"{self.BASE_URL}/v2/posts",
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            
            post_submission_id = result.get('postSubmissionId')
            
            logger.success(f"✓ Post submitted: {post_submission_id}")
            logger.info(f"  Platform: {platform}")
            
            return {
                'post_submission_id': post_submission_id,
                'platform': platform,
                'status': 'queued'
            }
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Post creation failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None
    
    def post_clip(
        self,
        account_id: str,
        platform: str,
        clip_url: str,
        caption: str,
        hashtags: Optional[List[str]] = None,
        target_config: Optional[Dict] = None,
        scheduled_time: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Post clip (assumes media already uploaded to public URL)
        
        Args:
            account_id: Blotato account ID
            platform: Platform name
            clip_url: Public URL to clip (or Blotato URL)
            caption: Post caption
            hashtags: Hashtags to append
            target_config: Platform-specific config
            scheduled_time: ISO 8601 schedule time
            
        Returns:
            Post result
        """
        # Build full text with hashtags
        text = caption
        if hashtags:
            text = f"{caption}\n\n{' '.join(hashtags)}"
        
        # Upload media to Blotato first (if not already Blotato URL)
        if not clip_url.startswith('https://database.blotato.com'):
            logger.info("Uploading media to Blotato...")
            blotato_url = self.upload_media(None, public_url=clip_url)
            if not blotato_url:
                return None
            media_urls = [blotato_url]
        else:
            media_urls = [clip_url]
        
        # Create post
        return self.create_post(
            account_id,
            platform,
            text,
            media_urls,
            target_config,
            scheduled_time
        )
    
    def get_post_status(self, post_id: str) -> Optional[Dict]:
        """Get post status and URLs"""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/posts/{post_id}",
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to get post status: {e}")
            return None
    
    def get_account_info(self) -> Optional[Dict]:
        """Get connected accounts info"""
        try:
            response = self.session.get(
                f"{self.BASE_URL}/accounts",
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            accounts = result.get('accounts', [])
            
            logger.info(f"Connected accounts: {len(accounts)}")
            for account in accounts:
                platform = account.get('platform')
                username = account.get('username')
                status = account.get('status', 'unknown')
                logger.info(f"  - {platform}: @{username} ({status})")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return None
    
    def validate_clip_for_platform(
        self,
        clip_path: Path,
        platform: str
    ) -> Dict:
        """
        Validate if clip meets platform requirements
        
        Args:
            clip_path: Path to clip
            platform: Platform name
            
        Returns:
            Validation result with issues
        """
        if platform not in self.PLATFORM_CONFIGS:
            return {
                'valid': False,
                'issues': [f'Unknown platform: {platform}']
            }
        
        config = self.PLATFORM_CONFIGS[platform]
        issues = []
        
        # Check file size
        size_mb = clip_path.stat().st_size / (1024 * 1024)
        if size_mb > config['max_video_size_mb']:
            issues.append(f"File too large: {size_mb:.1f}MB > {config['max_video_size_mb']}MB")
        
        # Check duration (would need ffprobe)
        # For now, just file size
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'size_mb': size_mb,
            'platform': platform
        }


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("BLOTATO CLIENT")
    print("="*60)
    print("\nMulti-platform posting via Blotato API.")
    print("\nSupports:")
    print("  - TikTok")
    print("  - Instagram Reels")
    print("  - YouTube Shorts")
    print("\nRequires: Blotato API key in .env")
    print("\nFor testing, use test_phase4.py")
