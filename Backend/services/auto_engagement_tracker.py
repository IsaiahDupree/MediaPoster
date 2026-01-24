"""
Auto Engagement Tracker Service

Integrates Safari auto-commenting with Brand Ops closed-loop system:
- Logs all engagement actions (comments, likes) to engagement_actions table
- Tracks agent runs for observability
- Manages daily engagement targets
- Calculates performance scores
"""

import os
import json
import uuid
from datetime import datetime, date
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict

# Try to import Supabase, fall back to direct postgres if not available
try:
    from supabase import create_client, Client
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
    supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None
except ImportError:
    supabase = None


@dataclass
class DailyTarget:
    """Daily engagement targets per platform."""
    platform: str
    comments_target: int = 10
    likes_target: int = 20
    follows_target: int = 5
    dms_target: int = 0
    
    # Current progress
    comments_done: int = 0
    likes_done: int = 0
    follows_done: int = 0
    dms_done: int = 0


@dataclass
class EngagementLog:
    """Log entry for an engagement action."""
    id: str
    agent_run_id: Optional[str]
    action_type: str  # 'comment', 'like', 'follow', 'dm'
    platform: str
    our_account_id: Optional[str]
    our_username: Optional[str]
    target_post_url: str
    target_post_id: Optional[str]
    target_username: str
    post_caption: Optional[str]
    post_image_description: Optional[str]
    action_content: Optional[str]  # Comment text, DM text
    ai_prompt_used: Optional[str]
    ai_model: Optional[str]
    ai_tokens_input: int = 0
    ai_tokens_output: int = 0
    ai_cost_usd: float = 0.0
    status: str = 'pending'  # pending, posted, verified, failed
    verified_at: Optional[datetime] = None
    created_at: datetime = None
    posted_at: Optional[datetime] = None


class AutoEngagementTracker:
    """
    Tracks all auto-engagement activity and integrates with Brand Ops.
    
    Usage:
        tracker = AutoEngagementTracker()
        
        # Start an engagement session
        run_id = tracker.start_agent_run('auto_commenter', 'instagram')
        
        # Log actions
        tracker.log_comment(run_id, post_url, username, comment_text, context)
        tracker.log_like(run_id, post_url, username)
        
        # Complete session
        tracker.complete_agent_run(run_id, status='success')
        
        # Check daily progress
        progress = tracker.get_daily_progress('instagram')
    """
    
    def __init__(self):
        self.supabase = supabase
        self._daily_targets: Dict[str, DailyTarget] = {}
        self._load_default_targets()
    
    def _load_default_targets(self):
        """Load default daily targets per platform."""
        self._daily_targets = {
            'instagram': DailyTarget(
                platform='instagram',
                comments_target=15,
                likes_target=30,
                follows_target=5
            ),
            'threads': DailyTarget(
                platform='threads',
                comments_target=10,
                likes_target=20,
                follows_target=3
            ),
            'tiktok': DailyTarget(
                platform='tiktok',
                comments_target=10,
                likes_target=20,
                follows_target=5
            ),
            'twitter': DailyTarget(
                platform='twitter',
                comments_target=10,
                likes_target=15,
                follows_target=5
            )
        }
    
    def set_daily_target(self, platform: str, comments: int = None, likes: int = None, 
                         follows: int = None, dms: int = None):
        """Update daily targets for a platform."""
        if platform not in self._daily_targets:
            self._daily_targets[platform] = DailyTarget(platform=platform)
        
        target = self._daily_targets[platform]
        if comments is not None:
            target.comments_target = comments
        if likes is not None:
            target.likes_target = likes
        if follows is not None:
            target.follows_target = follows
        if dms is not None:
            target.dms_target = dms
    
    def start_agent_run(self, agent_type: str, platform: str, 
                        account_id: str = None, prompt_version: str = None) -> str:
        """Start a new agent run and return the run_id."""
        run_id = str(uuid.uuid4())
        
        run_data = {
            'id': run_id,
            'agent_type': agent_type,
            'agent_version': '1.0.0',
            'run_id': run_id,
            'platform': platform,
            'account_id': account_id,
            'prompt_version': prompt_version or 'default',
            'status': 'running',
            'started_at': datetime.utcnow().isoformat()
        }
        
        if self.supabase:
            try:
                self.supabase.table('agent_runs').insert(run_data).execute()
            except Exception as e:
                print(f'[tracker] Failed to log agent run: {e}')
        
        return run_id
    
    def complete_agent_run(self, run_id: str, status: str = 'success', 
                           error_message: str = None, 
                           total_tokens: int = 0, total_cost: float = 0.0):
        """Complete an agent run."""
        update_data = {
            'status': status,
            'completed_at': datetime.utcnow().isoformat(),
            'ai_tokens_used': total_tokens,
            'ai_cost_usd': total_cost
        }
        
        if error_message:
            update_data['error_message'] = error_message
        
        if self.supabase:
            try:
                self.supabase.table('agent_runs').update(update_data).eq('id', run_id).execute()
            except Exception as e:
                print(f'[tracker] Failed to update agent run: {e}')
    
    def log_engagement(self, agent_run_id: str, action_type: str, platform: str,
                       target_post_url: str, target_username: str,
                       action_content: str = None, post_caption: str = None,
                       post_image_description: str = None, ai_prompt: str = None,
                       ai_model: str = None, ai_tokens: int = 0, ai_cost: float = 0.0,
                       status: str = 'posted', verified: bool = False,
                       our_username: str = None) -> str:
        """Log an engagement action (comment, like, follow, dm)."""
        action_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        action_data = {
            'id': action_id,
            'agent_run_id': agent_run_id,
            'action_type': action_type,
            'platform': platform,
            'our_username': our_username,
            'target_post_url': target_post_url,
            'target_username': target_username,
            'post_caption': post_caption[:500] if post_caption else None,
            'post_image_description': post_image_description[:500] if post_image_description else None,
            'action_content': action_content,
            'ai_prompt_used': ai_prompt,
            'ai_model': ai_model,
            'ai_tokens_input': ai_tokens,
            'ai_cost_usd': ai_cost,
            'status': status,
            'created_at': now.isoformat(),
            'posted_at': now.isoformat() if status == 'posted' else None
        }
        
        if verified:
            action_data['verified_at'] = now.isoformat()
            action_data['verification_method'] = 'page_check'
        
        if self.supabase:
            try:
                self.supabase.table('engagement_actions').insert(action_data).execute()
            except Exception as e:
                print(f'[tracker] Failed to log engagement: {e}')
        
        # Update daily progress
        self._update_daily_progress(platform, action_type)
        
        return action_id
    
    def log_comment(self, agent_run_id: str, platform: str, target_post_url: str,
                    target_username: str, comment_text: str, 
                    post_context: Dict = None, ai_prompt: str = None,
                    ai_model: str = 'gpt-4o', verified: bool = False) -> str:
        """Log a comment action."""
        return self.log_engagement(
            agent_run_id=agent_run_id,
            action_type='comment',
            platform=platform,
            target_post_url=target_post_url,
            target_username=target_username,
            action_content=comment_text,
            post_caption=post_context.get('caption') if post_context else None,
            post_image_description=post_context.get('image_alt') if post_context else None,
            ai_prompt=ai_prompt,
            ai_model=ai_model,
            status='posted' if verified else 'pending',
            verified=verified
        )
    
    def log_like(self, agent_run_id: str, platform: str, target_post_url: str,
                 target_username: str, verified: bool = False) -> str:
        """Log a like action."""
        return self.log_engagement(
            agent_run_id=agent_run_id,
            action_type='like',
            platform=platform,
            target_post_url=target_post_url,
            target_username=target_username,
            status='posted' if verified else 'pending',
            verified=verified
        )
    
    def _update_daily_progress(self, platform: str, action_type: str):
        """Update daily progress counter."""
        if platform not in self._daily_targets:
            return
        
        target = self._daily_targets[platform]
        
        if action_type == 'comment':
            target.comments_done += 1
        elif action_type == 'like':
            target.likes_done += 1
        elif action_type == 'follow':
            target.follows_done += 1
        elif action_type == 'dm':
            target.dms_done += 1
    
    def get_daily_progress(self, platform: str = None) -> Dict:
        """Get daily progress for one or all platforms."""
        if platform:
            if platform not in self._daily_targets:
                return {}
            target = self._daily_targets[platform]
            return {
                'platform': platform,
                'comments': {'done': target.comments_done, 'target': target.comments_target},
                'likes': {'done': target.likes_done, 'target': target.likes_target},
                'follows': {'done': target.follows_done, 'target': target.follows_target},
                'dms': {'done': target.dms_done, 'target': target.dms_target},
                'comments_remaining': max(0, target.comments_target - target.comments_done),
                'likes_remaining': max(0, target.likes_target - target.likes_done),
                'overall_progress': self._calculate_progress(target)
            }
        
        # Return all platforms
        return {p: self.get_daily_progress(p) for p in self._daily_targets}
    
    def _calculate_progress(self, target: DailyTarget) -> float:
        """Calculate overall progress percentage."""
        total_target = target.comments_target + target.likes_target + target.follows_target + target.dms_target
        total_done = target.comments_done + target.likes_done + target.follows_done + target.dms_done
        
        if total_target == 0:
            return 100.0
        
        return min(100.0, (total_done / total_target) * 100)
    
    def get_remaining_to_target(self, platform: str) -> Dict:
        """Get remaining actions needed to hit daily target."""
        progress = self.get_daily_progress(platform)
        if not progress:
            return {}
        
        return {
            'comments_remaining': progress.get('comments_remaining', 0),
            'likes_remaining': progress.get('likes_remaining', 0),
            'total_remaining': progress.get('comments_remaining', 0) + progress.get('likes_remaining', 0)
        }
    
    def reset_daily_counters(self):
        """Reset daily counters (call at start of each day)."""
        for target in self._daily_targets.values():
            target.comments_done = 0
            target.likes_done = 0
            target.follows_done = 0
            target.dms_done = 0
    
    def get_today_stats_from_db(self, platform: str = None) -> Dict:
        """Get today's stats from database."""
        if not self.supabase:
            return self.get_daily_progress(platform)
        
        today = date.today().isoformat()
        
        try:
            query = self.supabase.table('engagement_actions').select('action_type, status').gte('created_at', today)
            
            if platform:
                query = query.eq('platform', platform)
            
            result = query.execute()
            
            stats = {'comments': 0, 'likes': 0, 'follows': 0, 'dms': 0}
            for row in result.data:
                action = row['action_type']
                if action in stats:
                    stats[action] += 1
            
            return stats
        except Exception as e:
            print(f'[tracker] Failed to get stats: {e}')
            return {}
    
    def should_continue_engagement(self, platform: str) -> bool:
        """Check if we should continue engagement (haven't hit targets yet)."""
        remaining = self.get_remaining_to_target(platform)
        return remaining.get('total_remaining', 0) > 0


# Singleton instance
_tracker_instance = None

def get_tracker() -> AutoEngagementTracker:
    """Get singleton tracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = AutoEngagementTracker()
    return _tracker_instance


# Integration with Safari Auto Comment
def track_safari_engagement(results: List[Any], platform: str = 'instagram'):
    """
    Track engagement results from Safari auto-comment.
    
    Args:
        results: List of EngageResult from safari_auto_comment
        platform: Platform name
    """
    tracker = get_tracker()
    
    # Start agent run
    run_id = tracker.start_agent_run('safari_auto_commenter', platform)
    
    total_tokens = 0
    total_cost = 0.0
    success_count = 0
    
    for result in results:
        # Log like if present
        if result.like_result and result.like_result.success:
            tracker.log_like(
                agent_run_id=run_id,
                platform=platform,
                target_post_url=result.context.post_url if result.context else '',
                target_username=result.context.username if result.context else '',
                verified=result.like_result.verified
            )
        
        # Log comment if present
        if result.comment_result and result.comment_result.success:
            context = {
                'caption': result.context.caption if result.context else '',
                'image_alt': result.context.image_alt if result.context else ''
            }
            tracker.log_comment(
                agent_run_id=run_id,
                platform=platform,
                target_post_url=result.context.post_url if result.context else '',
                target_username=result.context.username if result.context else '',
                comment_text=result.generated_comment,
                post_context=context,
                verified=True  # We verify via page check
            )
            success_count += 1
    
    # Complete agent run
    status = 'success' if success_count > 0 else 'failed'
    tracker.complete_agent_run(run_id, status=status)
    
    # Print progress
    progress = tracker.get_daily_progress(platform)
    print(f"\n📊 Daily Progress ({platform}):")
    print(f"   Comments: {progress['comments']['done']}/{progress['comments']['target']}")
    print(f"   Likes: {progress['likes']['done']}/{progress['likes']['target']}")
    print(f"   Overall: {progress['overall_progress']:.1f}%")
    
    remaining = tracker.get_remaining_to_target(platform)
    if remaining['total_remaining'] > 0:
        print(f"   🎯 {remaining['comments_remaining']} comments and {remaining['likes_remaining']} likes remaining to hit target")
    else:
        print(f"   ✅ Daily target reached!")
    
    return run_id


if __name__ == '__main__':
    # Test the tracker
    tracker = get_tracker()
    
    # Set targets
    tracker.set_daily_target('instagram', comments=15, likes=30)
    
    # Simulate some engagement
    run_id = tracker.start_agent_run('auto_commenter', 'instagram')
    
    for i in range(3):
        tracker.log_like(run_id, 'instagram', f'https://instagram.com/p/test{i}', f'user{i}', verified=True)
        tracker.log_comment(run_id, 'instagram', f'https://instagram.com/p/test{i}', f'user{i}', 
                           f'Great post! 🔥', verified=True)
    
    tracker.complete_agent_run(run_id)
    
    # Check progress
    progress = tracker.get_daily_progress('instagram')
    print(json.dumps(progress, indent=2))
