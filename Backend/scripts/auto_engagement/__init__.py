"""
Auto-Engagement Package for Social Media Platforms

This package provides modular, reusable components for automating
engagement on social media platforms using Safari browser automation.

Modules:
    - safari_controller: Core Safari automation utilities
    - ai_comment_generator: OpenAI-powered comment generation
    - threads_engagement: Threads auto-commenting
    - instagram_engagement: Instagram auto-commenting
    - tiktok_engagement: TikTok auto-commenting

Quick Start:
    from auto_engagement import MultiPlatformEngagement
    
    engagement = MultiPlatformEngagement()
    results = engagement.engage_all_platforms()

Individual Platform Usage:
    from auto_engagement import ThreadsEngagement, InstagramEngagement, TikTokEngagement
    
    threads = ThreadsEngagement()
    result = threads.engage_with_post()
"""

from .safari_controller import SafariController, NavigationResult
from .ai_comment_generator import AICommentGenerator, PostContext, GeneratedComment
from .threads_engagement import ThreadsEngagement, ThreadsEngagementResult
from .instagram_engagement import InstagramEngagement, InstagramEngagementResult
from .tiktok_engagement import TikTokEngagement, TikTokEngagementResult

__all__ = [
    # Core
    'SafariController',
    'NavigationResult',
    'AICommentGenerator',
    'PostContext',
    'GeneratedComment',
    
    # Platforms
    'ThreadsEngagement',
    'ThreadsEngagementResult',
    'InstagramEngagement',
    'InstagramEngagementResult',
    'TikTokEngagement',
    'TikTokEngagementResult',
    
    # Convenience
    'MultiPlatformEngagement',
]


class MultiPlatformEngagement:
    """
    Unified multi-platform engagement runner.
    
    Runs engagement across all supported platforms in sequence:
    Threads → Instagram → TikTok
    
    Usage:
        engagement = MultiPlatformEngagement()
        results = engagement.engage_all_platforms()
        
        for result in results:
            print(f"{result['platform']}: {result['success']}")
    """
    
    def __init__(self, openai_api_key: str = None):
        """
        Initialize multi-platform engagement.
        
        Args:
            openai_api_key: OpenAI API key (optional, uses OPENAI_API_KEY env var)
        """
        self.threads = ThreadsEngagement(openai_api_key=openai_api_key)
        self.instagram = InstagramEngagement(openai_api_key=openai_api_key)
        self.tiktok = TikTokEngagement(openai_api_key=openai_api_key)
    
    def engage_all_platforms(self, platforms: list = None) -> list:
        """
        Engage with all platforms in sequence.
        
        Args:
            platforms: List of platforms to engage with. 
                       Defaults to ['threads', 'instagram', 'tiktok']
        
        Returns:
            List of result dictionaries with platform name and result object
        """
        if platforms is None:
            platforms = ['threads', 'instagram', 'tiktok']
        
        results = []
        
        print("="*70)
        print("🌐 MULTI-PLATFORM AUTO-ENGAGEMENT")
        print(f"   Platforms: {' → '.join(platforms)}")
        print("="*70)
        
        for platform in platforms:
            if platform == 'threads':
                result = self.threads.engage_with_post()
                results.append({
                    'platform': 'threads',
                    'success': result.success,
                    'result': result
                })
            elif platform == 'instagram':
                result = self.instagram.engage_with_post()
                results.append({
                    'platform': 'instagram',
                    'success': result.success,
                    'result': result
                })
            elif platform == 'tiktok':
                result = self.tiktok.engage_with_video()
                results.append({
                    'platform': 'tiktok',
                    'success': result.success,
                    'result': result
                })
        
        # Print summary
        self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: list):
        """Print engagement summary."""
        print("\n" + "="*70)
        print("📊 ENGAGEMENT SUMMARY")
        print("="*70)
        
        success_count = sum(1 for r in results if r['success'])
        
        for r in results:
            status = "✅" if r['success'] else "❌"
            result = r['result']
            platform = r['platform'].upper()
            
            print(f"\n{status} {platform}")
            print(f"   👤 @{getattr(result, 'username', 'N/A')}")
            print(f"   💬 \"{getattr(result, 'generated_comment', 'N/A')[:50]}...\"")
            print(f"   📤 Posted: {getattr(result, 'comment_posted', False)}")
            print(f"   📸 {getattr(result, 'proof_screenshot', 'N/A')}")
            
            if hasattr(result, 'error') and result.error:
                print(f"   ⚠️ Error: {result.error}")
        
        print(f"\n{'='*70}")
        print(f"🏆 RESULT: {success_count}/{len(results)} platforms successful")
        print(f"{'='*70}")
