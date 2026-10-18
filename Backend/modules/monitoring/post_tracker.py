"""
Post Status Tracker
Monitors Blotato post submissions until published and retrieves platform URLs
"""
from typing import Optional, Dict, Any
import requests
import time
from loguru import logger
from datetime import datetime


class PostTracker:
    """Track post submissions and retrieve published URLs"""
    
    def __init__(self, api_key: str, base_url: str = "https://backend.blotato.com/v2"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            'blotato-api-key': api_key,
            'Content-Type': 'application/json'
        }
    
    def get_post_status(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a post submission
        
        Args:
            submission_id: Blotato submission ID
            
        Returns:
            Dict with status info or None if error
        """
        try:
            # Note: This endpoint might be /v2/posts/{id} or /v2/submissions/{id}
            # Testing both formats
            endpoints = [
                f"{self.base_url}/posts/{submission_id}",
                f"{self.base_url}/submissions/{submission_id}",
            ]
            
            for endpoint in endpoints:
                response = requests.get(
                    endpoint,
                    headers=self.headers,
                    timeout=15
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    continue  # Try next endpoint
                else:
                    logger.warning(f"Status check returned {response.status_code}: {response.text[:100]}")
            
            logger.error(f"Could not find submission {submission_id} at any endpoint")
            return None
            
        except Exception as e:
            logger.error(f"Error checking status for {submission_id}: {e}")
            return None
    
    def poll_until_complete(
        self, 
        submission_id: str, 
        max_wait_seconds: int = 600,
        poll_interval: int = 30
    ) -> Optional[Dict[str, Any]]:
        """
        Poll submission status until complete or timeout
        
        Args:
            submission_id: Blotato submission ID  
            max_wait_seconds: Maximum time to wait (default 10 min)
            poll_interval: Seconds between polls (default 30s)
            
        Returns:
            Final status dict with URL or None if timeout/error
        """
        logger.info(f"Monitoring submission: {submission_id}")
        logger.info(f"Max wait: {max_wait_seconds}s, Poll interval: {poll_interval}s")
        
        start_time = time.time()
        attempts = 0
        
        while (time.time() - start_time) < max_wait_seconds:
            attempts += 1
            elapsed = int(time.time() - start_time)
            
            logger.info(f"  Poll #{attempts} (elapsed: {elapsed}s)...")
            
            status_data = self.get_post_status(submission_id)
            
            if not status_data:
                logger.warning(f"  Could not retrieve status")
                time.sleep(poll_interval)
                continue
            
            status = status_data.get('status', '').lower()
            platform_url = (
                status_data.get('publicUrl') or 
                status_data.get('url') or 
                status_data.get('platformUrl')
            )
            
            logger.info(f"  Status: {status}")
            
            if status == 'complete' or status ==  'published':
                if platform_url:
                    logger.success(f"  ✅ Post complete! URL: {platform_url}")
                    return {
                        'submission_id': submission_id,
                        'status': status,
                        'url': platform_url,
                        'completed_at': datetime.now().isoformat(),
                        'wait_time': elapsed,
                        'full_data': status_data
                    }
                else:
                    logger.warning(f"  Post complete but no URL found")
                    logger.debug(f"  Response: {status_data}")
            
            elif status == 'failed' or status == 'error':
                error_msg = status_data.get('error') or status_data.get('message', 'Unknown error')
                logger.error(f"  ❌ Post failed: {error_msg}")
                return {
                    'submission_id': submission_id,
                    'status': 'failed',
                    'error': error_msg,
                    'failed_at': datetime.now().isoformat(),
                    'full_data': status_data
                }
            
            elif status in ['queued', 'processing', 'pending', 'in-progress']:
                logger.info(f"  ⏳ Still {status}...")
            
            else:
                logger.warning(f"  Unknown status: {status}")
            
            time.sleep(poll_interval)
        
        # Timeout
        elapsed = int(time.time() - start_time)
        logger.warning(f"  ⏱️  Timeout after {elapsed}s")
        return {
            'submission_id': submission_id,
            'status': 'timeout',
            'waited': elapsed,
            'message': f'Post did not complete within {max_wait_seconds}s'
        }
    
    def get_published_url(self, submission_id: str) -> Optional[str]:
        """
        Get the published platform URL for a submission
        
        Args:
            submission_id: Blotato submission ID
            
        Returns:
            Platform URL string or None
        """
        status_data = self.get_post_status(submission_id)
        
        if not status_data:
            return None
        
        # Try multiple field names (publicUrl is the primary one)
        url = (
            status_data.get('publicUrl') or
            status_data.get('url') or 
            status_data.get('platformUrl') or
            status_data.get('platform_url') or
            status_data.get('postUrl')
        )
        
        return url
    
    def batch_check_status(self, submission_ids: list) -> Dict[str, Dict]:
        """
        Check status for multiple submissions
        
        Args:
            submission_ids: List of submission IDs
            
        Returns:
            Dict mapping submission_id to status data
        """
        results = {}
        
        for sub_id in submission_ids:
            status = self.get_post_status(sub_id)
            if status:
                results[sub_id] = status
            else:
                results[sub_id] = {'error': 'Could not retrieve status'}
            
            # Small delay to respect rate limits
            time.sleep(0.5)
        
        return results


# Example usage
if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    api_key = os.getenv('BLOTATO_API_KEY')
    
    if not api_key:
        logger.error("BLOTATO_API_KEY not found")
        exit(1)
    
    tracker = PostTracker(api_key)
    
    # Example: Monitor a submission
    test_submission_id = "08a5d9e9-e72c-4398-b0cf-a4d5471f3cf6"  # From test results
    
    logger.info(f"\n{'='*80}")
    logger.info("POST TRACKER TEST")
    logger.info(f"{'='*80}\n")
    
    result = tracker.poll_until_complete(test_submission_id, max_wait_seconds=120)
    
    if result:
        logger.info(f"\nFinal result:")
        logger.info(f"  Status: {result.get('status')}")
        logger.info(f"  URL: {result.get('url', 'N/A')}")
        logger.info(f"  Wait time: {result.get('wait_time', result.get('waited', 0))}s")
    else:
        logger.error("\nFailed to get result")
