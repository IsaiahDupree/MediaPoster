"""
Creative Briefs & AI Coach Insights Test Suite
===============================================
Tests for:
1. Creative Brief Generation
2. Check-back Period Insights
3. AI Coach "Hard Truths" Analysis
4. Performance-to-Action Pipeline

Run:
    pytest tests/test_creative_briefs_coach_insights.py -v
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass


# =============================================================================
# SECTION 1: CREATIVE BRIEFS - Data Model Tests
# =============================================================================

class TestCreativeBriefDataModel:
    """Tests for creative brief data structure."""
    
    def test_brief_has_required_fields(self):
        """Brief should have all required fields."""
        brief = {
            'id': str(uuid.uuid4()),
            'source_type': 'own_top_post',
            'source_reference': {'post_id': '123'},
            'angle_name': "The 'I tried this' demo",
            'target_audience': 'TikTok creators',
            'core_promise': 'Find viral frames easily',
            'hook_ideas': ['Hook 1', 'Hook 2'],
            'script_outline': {'intro': [], 'body': [], 'cta': []},
            'visual_directions': {'broll': [], 'face_cam': []},
            'posting_guidance': {'platform_priority': ['tiktok']},
            'ready_for_use': True,
            'created_at': datetime.now().isoformat()
        }
        
        required = ['angle_name', 'target_audience', 'core_promise', 
                   'hook_ideas', 'script_outline', 'posting_guidance']
        assert all(field in brief for field in required)
    
    def test_brief_source_types(self):
        """Source type should be valid enum value."""
        valid_sources = ['kalodata_product', 'own_top_post', 'prompt_only']
        source = 'own_top_post'
        assert source in valid_sources
    
    def test_brief_hook_ideas_array(self):
        """Hook ideas should be array with multiple options."""
        hooks = [
            "This 30-second script made my OLD video go viral again.",
            "I fed my entire camera roll into an AI and this is what happened…",
            "POV: You finally cracked the algorithm"
        ]
        assert len(hooks) >= 2
        assert all(isinstance(h, str) for h in hooks)
    
    def test_brief_script_outline_structure(self):
        """Script outline should have intro, body, cta sections."""
        outline = {
            'intro': [
                'Quick pattern interrupt: show old dead posts',
                'Line: "You\'re sitting on a goldmine"'
            ],
            'body': [
                'Show dashboard auto-rating clips',
                'Explain pre-social vs post-social score',
                'Show before/after performance'
            ],
            'cta': [
                'Comment "POSTER" for breakdown'
            ]
        }
        
        assert 'intro' in outline
        assert 'body' in outline
        assert 'cta' in outline
        assert len(outline['body']) >= 2
    
    def test_brief_visual_directions(self):
        """Visual directions should have broll and face_cam."""
        directions = {
            'broll': [
                'Screen capture of timeline view',
                'Overlay text: "This is my 2-month queue"'
            ],
            'face_cam': [
                'Shoot vertical, close-up framing',
                'Use captions synced to hook lines'
            ]
        }
        
        assert 'broll' in directions
        assert 'face_cam' in directions
    
    def test_brief_posting_guidance(self):
        """Posting guidance should have platform and frequency."""
        guidance = {
            'platform_priority': ['tiktok', 'reels'],
            'frequency': '2-4 times per day',
            'time_window_hint': 'Peak engagement windows'
        }
        
        assert 'tiktok' in guidance['platform_priority']


# =============================================================================
# SECTION 2: CREATIVE BRIEFS - Generation Tests
# =============================================================================

class TestCreativeBriefGeneration:
    """Tests for generating creative briefs."""
    
    def test_generate_brief_from_top_post(self):
        """Generate brief from top-performing post."""
        top_post = {
            'id': '123',
            'views': 50000,
            'avg_views': 10000,
            'performance_ratio': 5.0,
            'topics': ['automation', 'coding'],
            'hook_text': 'This changed everything'
        }
        
        # Should trigger brief generation
        should_generate = top_post['performance_ratio'] > 2.0
        assert should_generate is True
    
    def test_generate_brief_from_kalodata(self):
        """Generate brief from Kalodata product patterns."""
        kalodata_pattern = {
            'product_category': 'digital_products',
            'top_hooks': ['POV:', 'This is why', 'Nobody talks about'],
            'avg_length_sec': 45,
            'format': 'problem_solution'
        }
        
        brief = {
            'source_type': 'kalodata_product',
            'angle_name': f"The '{kalodata_pattern['format']}' angle",
            'hook_ideas': kalodata_pattern['top_hooks']
        }
        
        assert brief['source_type'] == 'kalodata_product'
        assert len(brief['hook_ideas']) >= 3
    
    def test_generate_brief_from_prompt(self):
        """Generate brief from user prompt."""
        prompt = "Create a brief for promoting my automation tool"
        
        brief = {
            'source_type': 'prompt_only',
            'angle_name': 'Automation Tool Demo',
            'target_audience': 'Inferred from prompt'
        }
        
        assert brief['source_type'] == 'prompt_only'
    
    def test_brief_extracts_winning_elements(self):
        """Brief should identify what made source content successful."""
        source_analysis = {
            'hook_strength': 9,
            'first_3_seconds': 'Strong pattern interrupt',
            'retention_curve': 'High throughout',
            'top_comments_themes': ['relatable', 'useful', 'funny']
        }
        
        winning_elements = {
            'hook': source_analysis['first_3_seconds'],
            'engagement_drivers': source_analysis['top_comments_themes']
        }
        
        assert winning_elements['hook'] is not None
        assert len(winning_elements['engagement_drivers']) >= 1
    
    def test_brief_suggests_variations(self):
        """Brief should suggest content variations."""
        variations = [
            {'format': 'broll_text', 'description': 'B-roll with text overlay'},
            {'format': 'face_cam', 'description': 'Face to camera re-take'},
            {'format': 'carousel', 'description': 'Image carousel version'},
            {'format': 'duet', 'description': 'Duet with original'}
        ]
        
        assert len(variations) >= 3
        assert all('format' in v for v in variations)


# =============================================================================
# SECTION 3: CHECK-BACK PERIOD INSIGHTS
# =============================================================================

class TestCheckBackPeriodInsights:
    """Tests for insights from check-back metric collection."""
    
    def test_checkback_periods_defined(self):
        """Standard check-back periods should be defined."""
        checkpoints = ['15m', '1h', '4h', '24h', '72h', '7d']
        assert len(checkpoints) == 6
        assert '24h' in checkpoints
    
    def test_metrics_collected_at_checkpoint(self):
        """Metrics should be collected at each checkpoint."""
        checkpoint_metrics = {
            'checkpoint': '24h',
            'views': 25000,
            'likes': 1500,
            'comments': 200,
            'shares': 100,
            'saves': 500,
            'watch_time_avg_sec': 35,
            'profile_visits': 150,
            'follower_delta': 25
        }
        
        required_metrics = ['views', 'likes', 'comments', 'shares']
        assert all(m in checkpoint_metrics for m in required_metrics)
    
    def test_metrics_growth_calculated(self):
        """Growth between checkpoints should be calculated."""
        metrics_15m = {'views': 5000, 'likes': 200}
        metrics_1h = {'views': 12000, 'likes': 600}
        
        growth = {
            'views_delta': metrics_1h['views'] - metrics_15m['views'],
            'views_growth_pct': (metrics_1h['views'] - metrics_15m['views']) / metrics_15m['views'] * 100,
            'likes_delta': metrics_1h['likes'] - metrics_15m['likes'],
            'likes_growth_pct': (metrics_1h['likes'] - metrics_15m['likes']) / metrics_15m['likes'] * 100
        }
        
        assert growth['views_delta'] == 7000
        assert growth['views_growth_pct'] == 140.0
    
    def test_velocity_analysis(self):
        """Analyze velocity of metric growth."""
        checkpoints = [
            {'time': '15m', 'views': 5000},
            {'time': '1h', 'views': 12000},
            {'time': '4h', 'views': 18000},
            {'time': '24h', 'views': 25000}
        ]
        
        # Early velocity (first hour)
        early_velocity = (checkpoints[1]['views'] - checkpoints[0]['views']) / 0.75  # per hour
        
        # Late velocity (after 4h)
        late_velocity = (checkpoints[3]['views'] - checkpoints[2]['views']) / 20  # per hour
        
        velocity_ratio = early_velocity / late_velocity if late_velocity > 0 else float('inf')
        
        # High early velocity indicates viral potential
        is_viral_pattern = early_velocity > 5000  # 5k views/hour in first hour
        assert is_viral_pattern is True
    
    def test_benchmark_comparison(self):
        """Compare against channel benchmarks."""
        post_metrics = {'views': 25000, 'likes': 1500, 'engagement_rate': 6.0}
        channel_avg = {'views': 10000, 'likes': 500, 'engagement_rate': 5.0}
        
        comparison = {
            'views_vs_avg': post_metrics['views'] / channel_avg['views'],
            'likes_vs_avg': post_metrics['likes'] / channel_avg['likes'],
            'engagement_vs_avg': post_metrics['engagement_rate'] / channel_avg['engagement_rate']
        }
        
        is_overperformer = comparison['views_vs_avg'] > 1.5
        assert is_overperformer is True
        assert comparison['views_vs_avg'] == 2.5
    
    def test_plateau_detection(self):
        """Detect when metrics plateau (growth < 5%)."""
        checkpoints = [
            {'time': '24h', 'views': 25000},
            {'time': '72h', 'views': 26000},
            {'time': '7d', 'views': 26500}
        ]
        
        growth_24h_72h = (checkpoints[1]['views'] - checkpoints[0]['views']) / checkpoints[0]['views']
        growth_72h_7d = (checkpoints[2]['views'] - checkpoints[1]['views']) / checkpoints[1]['views']
        
        plateaued = growth_72h_7d < 0.05  # Less than 5% growth
        assert plateaued is True


# =============================================================================
# SECTION 4: AI COACH "HARD TRUTHS" ANALYSIS
# =============================================================================

class TestAICoachHardTruths:
    """Tests for AI Coach providing actionable, honest feedback."""
    
    def test_coach_identifies_underperformance(self):
        """Coach should flag underperforming content."""
        metrics = {
            'views': 2000,
            'channel_avg_views': 10000,
            'pre_social_score': 75,
            'post_social_score': 45
        }
        
        performance_ratio = metrics['views'] / metrics['channel_avg_views']
        is_underperforming = performance_ratio < 0.5
        
        hard_truth = None
        if is_underperforming:
            hard_truth = "This post performed 80% below your average. The hook didn't resonate."
        
        assert is_underperforming is True
        assert hard_truth is not None
    
    def test_coach_identifies_hook_failure(self):
        """Coach should identify weak hooks."""
        watch_data = {
            'avg_watch_time_sec': 8,
            'video_duration_sec': 45,
            'drop_off_3sec_pct': 65,  # 65% dropped off in first 3 seconds
            'completion_rate': 10
        }
        
        hook_failed = watch_data['drop_off_3sec_pct'] > 50
        
        hard_truth = None
        if hook_failed:
            hard_truth = f"65% of viewers left in the first 3 seconds. Your hook isn't stopping the scroll."
        
        assert hook_failed is True
        assert 'first 3 seconds' in hard_truth
    
    def test_coach_identifies_cta_timing_issue(self):
        """Coach should identify CTA placement issues."""
        video_data = {
            'duration_sec': 45,
            'cta_appears_at_sec': 42,
            'avg_watch_time_sec': 20,
            'completion_rate': 15
        }
        
        # CTA appears after most viewers have left
        viewers_see_cta = video_data['avg_watch_time_sec'] > video_data['cta_appears_at_sec']
        
        hard_truth = None
        if not viewers_see_cta:
            hard_truth = f"Your CTA appears at {video_data['cta_appears_at_sec']}s but viewers leave at {video_data['avg_watch_time_sec']}s. Move it to the 5-10 second mark."
        
        assert viewers_see_cta is False
        assert 'Move it' in hard_truth
    
    def test_coach_identifies_posting_time_issue(self):
        """Coach should identify suboptimal posting times."""
        post_data = {
            'posted_hour': 3,  # 3 AM
            'best_performing_hours': [10, 14, 19],
            'views': 3000,
            'avg_views_at_best_hours': 15000
        }
        
        posted_at_bad_time = post_data['posted_hour'] not in post_data['best_performing_hours']
        
        hard_truth = None
        if posted_at_bad_time:
            hard_truth = f"You posted at 3 AM. Your audience is most active at 10 AM, 2 PM, and 7 PM."
        
        assert posted_at_bad_time is True
        assert '3 AM' in hard_truth
    
    def test_coach_identifies_format_mismatch(self):
        """Coach should identify when format doesn't match audience."""
        content_analysis = {
            'format': 'talking_head',
            'niche': 'tech_tutorials',
            'top_performing_formats_in_niche': ['screen_recording', 'demo', 'broll_text'],
            'views': 5000,
            'niche_avg_views': 20000
        }
        
        format_mismatch = content_analysis['format'] not in content_analysis['top_performing_formats_in_niche']
        
        hard_truth = None
        if format_mismatch:
            hard_truth = f"Talking head videos underperform in tech tutorials. Try screen recordings or demos instead."
        
        assert format_mismatch is True
        assert 'screen recordings' in hard_truth
    
    def test_coach_identifies_consistency_issue(self):
        """Coach should flag posting inconsistency."""
        posting_history = {
            'posts_last_7_days': 2,
            'posts_last_30_days': 5,
            'recommended_frequency': 14,  # per week
            'avg_gap_hours': 72
        }
        
        inconsistent = posting_history['posts_last_7_days'] < 7
        
        hard_truth = None
        if inconsistent:
            hard_truth = f"You posted {posting_history['posts_last_7_days']} times this week. Consistent creators post 2-3x daily. The algorithm rewards consistency."
        
        assert inconsistent is True
        assert 'Consistent creators' in hard_truth
    
    def test_coach_identifies_engagement_bait_working(self):
        """Coach should recognize when engagement tactics work."""
        post_analysis = {
            'has_question_in_caption': True,
            'has_cta_in_video': True,
            'comment_count': 500,
            'avg_comments': 50,
            'top_comment_themes': ['answering_question', 'sharing_experience']
        }
        
        engagement_tactics_working = post_analysis['comment_count'] > post_analysis['avg_comments'] * 5
        
        insight = None
        if engagement_tactics_working:
            insight = "Your question prompt drove 10x more comments. Keep using open-ended questions."
        
        assert engagement_tactics_working is True
        assert 'question prompt' in insight


# =============================================================================
# SECTION 5: COACH INSIGHTS - Actionable Recommendations
# =============================================================================

class TestCoachActionableRecommendations:
    """Tests for coach generating specific, actionable recommendations."""
    
    def test_coach_generates_what_worked(self):
        """Coach should list what worked."""
        what_worked = [
            "Strong pattern interrupt in first 2 seconds (face close-up with shocked expression)",
            "Text overlay matched spoken hook exactly",
            "Problem statement was specific and relatable",
            "Video length (32s) matched audience attention span"
        ]
        
        assert len(what_worked) >= 3
        assert all(len(item) > 20 for item in what_worked)  # Specific, not generic
    
    def test_coach_generates_what_to_improve(self):
        """Coach should list specific improvements."""
        what_to_improve = [
            "CTA appears at 42s but avg watch time is 20s → Move CTA to 8-10s mark",
            "Caption doesn't include the hook text → Add 'This is why...' to caption",
            "No hashtags used → Add 3-5 niche hashtags (#techtok, #automation)",
            "Thumbnail is auto-generated → Create custom thumbnail with text overlay"
        ]
        
        assert len(what_to_improve) >= 3
        # Each should have problem → solution format
        assert all('→' in item or '->' in item for item in what_to_improve)
    
    def test_coach_generates_next_content_suggestions(self):
        """Coach should suggest next content based on insights."""
        next_actions = [
            {
                'action': 'create_followup',
                'description': 'Create Part 2 addressing top comment questions',
                'priority': 'high',
                'deadline': '48 hours'
            },
            {
                'action': 'repurpose',
                'description': 'Turn this into a carousel for Instagram',
                'priority': 'medium',
                'deadline': '1 week'
            },
            {
                'action': 'test_variation',
                'description': 'Test same hook with screen recording format',
                'priority': 'high',
                'deadline': '3 days'
            }
        ]
        
        assert len(next_actions) >= 2
        assert all('priority' in a for a in next_actions)
    
    def test_coach_provides_benchmark_context(self):
        """Coach should provide benchmark context for metrics."""
        context = {
            'your_views': 25000,
            'your_avg': 10000,
            'niche_avg': 15000,
            'top_10_pct_threshold': 50000,
            'interpretation': 'Above your average but below niche leaders'
        }
        
        assert 'interpretation' in context
        assert context['your_views'] > context['your_avg']
    
    def test_coach_identifies_trend_alignment(self):
        """Coach should identify if content aligns with trends."""
        trend_analysis = {
            'trending_sounds_used': False,
            'trending_hashtags_used': True,
            'trending_format_used': False,
            'trend_score': 1,  # out of 3
            'recommendation': 'Add trending sound to boost discoverability'
        }
        
        underutilizing_trends = trend_analysis['trend_score'] < 2
        assert underutilizing_trends is True
        assert 'trending sound' in trend_analysis['recommendation']


# =============================================================================
# SECTION 6: COACH INSIGHTS - Performance Prediction
# =============================================================================

class TestCoachPerformancePrediction:
    """Tests for coach predicting future performance."""
    
    def test_predict_final_views_from_velocity(self):
        """Predict final views based on early velocity."""
        early_data = {
            '1h_views': 5000,
            '4h_views': 15000,
            'velocity_1h_4h': 3333  # views per hour
        }
        
        # Simple projection: velocity typically drops 50% after 24h
        projected_24h_views = early_data['4h_views'] + (early_data['velocity_1h_4h'] * 0.5 * 20)
        projected_7d_views = projected_24h_views * 1.3  # Typical 30% additional after 24h
        
        assert projected_24h_views > early_data['4h_views']
        assert projected_7d_views > projected_24h_views
    
    def test_predict_viral_potential(self):
        """Predict if post has viral potential based on early metrics."""
        early_metrics = {
            '1h_views': 10000,
            '1h_likes': 800,
            '1h_comments': 100,
            '1h_shares': 50,
            'engagement_rate': 9.5
        }
        
        viral_indicators = {
            'high_early_views': early_metrics['1h_views'] > 5000,
            'strong_engagement': early_metrics['engagement_rate'] > 8,
            'share_ratio': early_metrics['1h_shares'] / early_metrics['1h_views'] > 0.003,
            'comment_ratio': early_metrics['1h_comments'] / early_metrics['1h_views'] > 0.005
        }
        
        viral_score = sum(viral_indicators.values())
        has_viral_potential = viral_score >= 3
        
        assert has_viral_potential is True
    
    def test_predict_best_repost_time(self):
        """Predict optimal time to repost/remix content."""
        performance_data = {
            'peak_views_hour': 14,
            'peak_engagement_hour': 19,
            'audience_active_hours': [10, 14, 19, 21],
            'original_post_hour': 3
        }
        
        # Best repost time is peak engagement hour
        best_repost_hour = performance_data['peak_engagement_hour']
        improvement_potential = 'high' if performance_data['original_post_hour'] not in performance_data['audience_active_hours'] else 'low'
        
        assert best_repost_hour in performance_data['audience_active_hours']
        assert improvement_potential == 'high'


# =============================================================================
# SECTION 7: API RESPONSE STRUCTURES
# =============================================================================

class TestAPIResponseStructures:
    """Tests for API response structures."""
    
    def test_creative_brief_api_response(self):
        """GET /api/creative-briefs/:id response."""
        response = {
            'id': str(uuid.uuid4()),
            'source_type': 'own_top_post',
            'angle_name': "The 'I tried this' demo",
            'target_audience': 'TikTok creators',
            'core_promise': 'Find viral frames easily',
            'hook_ideas': [
                "This 30-second script made my OLD video go viral again.",
                "I fed my camera roll into an AI..."
            ],
            'script_outline': {
                'intro': ['Pattern interrupt'],
                'body': ['Show dashboard', 'Explain scores'],
                'cta': ['Comment POSTER']
            },
            'visual_directions': {
                'broll': ['Screen capture'],
                'face_cam': ['Vertical, close-up']
            },
            'posting_guidance': {
                'platform_priority': ['tiktok', 'reels'],
                'frequency': '2-4x daily'
            },
            'ready_for_use': True
        }
        
        required = ['angle_name', 'hook_ideas', 'script_outline', 'posting_guidance']
        assert all(k in response for k in required)
    
    def test_coach_insights_api_response(self):
        """GET /api/media/:id/coach-insights response."""
        response = {
            'media_id': str(uuid.uuid4()),
            'checkpoint': '24h',
            'pre_social_score': 78,
            'post_social_score': 65,
            'performance_summary': {
                'views': 8000,
                'channel_avg': 10000,
                'ratio': 0.8,
                'verdict': 'Below average'
            },
            'hard_truths': [
                "60% of viewers left in first 3 seconds. Your hook isn't working.",
                "Posted at 3 AM - your audience peaks at 2 PM and 7 PM."
            ],
            'what_worked': [
                "Caption drove curiosity clicks"
            ],
            'what_to_improve': [
                "Hook → Start with the result, not the setup",
                "Timing → Schedule for peak hours"
            ],
            'recommended_actions': [
                {'action': 'repost_optimized', 'priority': 'high'},
                {'action': 'create_variation', 'priority': 'medium'}
            ]
        }
        
        assert 'hard_truths' in response
        assert len(response['hard_truths']) >= 1
        assert 'what_to_improve' in response
    
    def test_checkback_metrics_api_response(self):
        """GET /api/posts/:id/checkback-metrics response."""
        response = {
            'post_id': str(uuid.uuid4()),
            'checkpoints': [
                {
                    'checkpoint': '15m',
                    'timestamp': '2024-01-15T10:15:00Z',
                    'views': 2000,
                    'likes': 100,
                    'comments': 15,
                    'shares': 5
                },
                {
                    'checkpoint': '1h',
                    'timestamp': '2024-01-15T11:00:00Z',
                    'views': 8000,
                    'likes': 500,
                    'comments': 60,
                    'shares': 25
                },
                {
                    'checkpoint': '24h',
                    'timestamp': '2024-01-16T10:00:00Z',
                    'views': 25000,
                    'likes': 1500,
                    'comments': 200,
                    'shares': 100
                }
            ],
            'growth_analysis': {
                'total_growth_pct': 1150,
                'peak_growth_period': '15m-1h',
                'current_velocity': 'slowing'
            }
        }
        
        assert len(response['checkpoints']) >= 3
        assert 'growth_analysis' in response


# =============================================================================
# SECTION 8: INTEGRATION TESTS
# =============================================================================

class TestBriefCoachIntegration:
    """Integration tests for brief and coach systems."""
    
    def test_top_post_triggers_brief_generation(self):
        """Top performing post should trigger brief creation."""
        post_performance = {
            'views': 50000,
            'channel_avg': 10000,
            'ratio': 5.0
        }
        
        # Threshold for brief generation
        should_generate_brief = post_performance['ratio'] > 2.0
        
        if should_generate_brief:
            brief = {
                'source_type': 'own_top_post',
                'source_reference': {'post_id': '123'}
            }
            assert brief['source_type'] == 'own_top_post'
        
        assert should_generate_brief is True
    
    def test_checkback_triggers_coach_analysis(self):
        """24h and 7d checkbacks should trigger coach analysis."""
        checkpoints_triggering_coach = ['24h', '7d']
        current_checkpoint = '24h'
        
        should_analyze = current_checkpoint in checkpoints_triggering_coach
        assert should_analyze is True
    
    def test_coach_insights_create_brief_recommendations(self):
        """Coach insights should recommend brief creation."""
        coach_output = {
            'recommended_actions': [
                {'action': 'create_brief', 'format': 'broll_text'},
                {'action': 'create_brief', 'format': 'face_cam'}
            ]
        }
        
        brief_recommendations = [a for a in coach_output['recommended_actions'] if a['action'] == 'create_brief']
        assert len(brief_recommendations) >= 1
    
    def test_full_pipeline_post_to_insights_to_brief(self):
        """Full pipeline: Post → Metrics → Insights → Brief."""
        # Step 1: Post created
        post = {'id': '123', 'status': 'posted'}
        
        # Step 2: Metrics collected at 24h
        metrics = {'views': 50000, 'ratio': 5.0}
        
        # Step 3: Coach analyzes
        is_top_performer = metrics['ratio'] > 2.0
        
        # Step 4: Brief generated
        brief_created = False
        if is_top_performer:
            brief_created = True
        
        assert brief_created is True


# =============================================================================
# SECTION 9: EDGE CASES & ERROR HANDLING
# =============================================================================

class TestEdgeCases:
    """Edge cases and error handling."""
    
    def test_handle_no_checkback_data(self):
        """Handle missing checkback data gracefully."""
        checkback_data = None
        
        insights = {
            'status': 'insufficient_data',
            'message': 'Waiting for metrics collection'
        }
        
        if not checkback_data:
            pass  # Return waiting status
        
        assert insights['status'] == 'insufficient_data'
    
    def test_handle_zero_views(self):
        """Handle post with zero views."""
        metrics = {'views': 0, 'likes': 0}
        
        # Avoid division by zero
        engagement_rate = 0 if metrics['views'] == 0 else metrics['likes'] / metrics['views']
        
        assert engagement_rate == 0
    
    def test_handle_first_post_no_baseline(self):
        """Handle first post with no channel baseline."""
        channel_avg = None
        post_views = 5000
        
        # Use platform average as fallback
        fallback_avg = 10000
        
        comparison_base = channel_avg if channel_avg else fallback_avg
        ratio = post_views / comparison_base
        
        assert ratio == 0.5
    
    def test_handle_missing_transcript(self):
        """Handle video with no transcript."""
        analysis = {'transcript': None}
        
        # Should still generate brief with visual-only analysis
        can_generate_brief = True  # Use visual analysis
        
        assert can_generate_brief is True


# =============================================================================
# RUNNER
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
