"""
YouTube Analytics Collector using YouTube Data API v3
"""
from typing import Optional, Dict, List, Any
from loguru import logger
import os

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    logger.warning("google-api-python-client not installed. Run: pip install google-api-python-client")


class YouTubeAnalytics:
    """Collect analytics from YouTube videos"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize YouTube API client
        
        Args:
            api_key: YouTube Data API v3 key
        """
        self.api_key = api_key or os.getenv('YOUTUBE_API_KEY')
        
        if not self.api_key:
            logger.warning("YouTube API key not configured")
            self.youtube = None
        else:
            try:
                self.youtube = build('youtube', 'v3', developerKey=self.api_key)
                logger.info("YouTube Analytics initialized")
            except Exception as e:
                logger.error(f"Failed to initialize YouTube client: {e}")
                self.youtube = None
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from YouTube URL
        
        Args:
            url: YouTube URL
            
        Returns:
            Video ID or None
        """
        # Handle different YouTube URL formats
        import re
        
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/v/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    
    def get_video_stats(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get video statistics
        
        Args:
            url: YouTube video URL
            
        Returns:
            {
                'views': int,
                'likes': int,
                'comments_count': int,
                'title': str,
                'published_at': str,
                'duration': str
            }
        """
        if not self.youtube:
            logger.error("YouTube client not initialized")
            return None
        
        video_id = self.extract_video_id(url)
        if not video_id:
            logger.error(f"Could not extract video ID from {url}")
            return None
        
        try:
            response = self.youtube.videos().list(
                part='statistics,snippet,contentDetails',
                id=video_id
            ).execute()
            
            if not response.get('items'):
                logger.error(f"Video not found: {video_id}")
                return None
            
            video = response['items'][0]
            stats = video['statistics']
            snippet = video['snippet']
            
            return {
                'views': int(stats.get('viewCount', 0)),
                'likes': int(stats.get('likeCount', 0)),
                'comments_count': int(stats.get('commentCount', 0)),
                'title': snippet.get('title', ''),
                'published_at': snippet.get('publishedAt', ''),
                'duration': video['contentDetails'].get('duration', ''),
                'raw_stats': stats
            }
            
        except HttpError as e:
            logger.error(f"YouTube API error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting video stats: {e}")
            return None
    
    def get_comments(self, url: str, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        Get video comments
        
        Args:
            url: YouTube video URL
            max_results: Maximum comments to fetch
            
        Returns:
            List of comments with author, text, likes, posted_at
        """
        if not self.youtube:
            logger.error("YouTube client not initialized")
            return []
        
        video_id = self.extract_video_id(url)
        if not video_id:
            return []
        
        comments = []
        
        try:
            request = self.youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=min(max_results, 100),
                order='relevance'
            )
            
            while request and len(comments) < max_results:
                response = request.execute()
                
                for item in response['items']:
                    comment = item['snippet']['topLevelComment']['snippet']
                    comments.append({
                        'comment_id': item['id'],
                        'author': comment.get('authorDisplayName', ''),
                        'text': comment.get('textDisplay', ''),
                        'likes_count': comment.get('likeCount', 0),
                        'posted_at': comment.get('publishedAt', ''),
                        'author_channel_id': comment.get('authorChannelId', {}).get('value', '')
                    })
                
                # Get next page if available
                if 'nextPageToken' in response and len(comments) < max_results:
                    request = self.youtube.commentThreads().list(
                        part='snippet',
                        videoId=video_id,
                        maxResults=min(max_results - len(comments), 100),
                        pageToken=response['nextPageToken'],
                        order='relevance'
                    )
                else:
                    request = None
            
            logger.info(f"Fetched {len(comments)} comments from {video_id}")
            return comments[:max_results]
            
        except HttpError as e:
            if 'commentsDisabled' in str(e):
                logger.warning(f"Comments disabled for video {video_id}")
            else:
                logger.error(f"YouTube API error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting comments: {e}")
            return []


# Example usage
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    youtube = YouTubeAnalytics()
    
    # Test with the video we posted
    test_url = "https://www.youtube.com/watch?v=Q1Mhzw7nXDY"
    
    logger.info(f"Testing with: {test_url}")
    
    # Get stats
    stats = youtube.get_video_stats(test_url)
    if stats:
        logger.info("Video Stats:")
        logger.info(f"  Views: {stats['views']}")
        logger.info(f"  Likes: {stats['likes']}")
        logger.info(f"  Comments: {stats['comments_count']}")
        logger.info(f"  Title: {stats['title']}")
    
    # Get comments
    comments = youtube.get_comments(test_url, max_results=10)
    logger.info(f"\nFetched {len(comments)} comments")
    
    for i, comment in enumerate(comments[:3], 1):
        logger.info(f"\nComment {i}:")
        logger.info(f"  Author: {comment['author']}")
        logger.info(f"  Text: {comment['text'][:100]}...")
