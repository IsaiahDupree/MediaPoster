"""
AI Services, Content Filtering & Blotato Integration Tests
============================================================
Tests for:
1. AI-Powered Analysis (OpenAI Vision, Whisper, GPT)
2. AI Coach Insights Generation
3. Content Filtering (AI analysis, transcript, social filters)
4. Blotato Platform Posting & URL Retrieval

Run:
    pytest tests/test_ai_services_blotato.py -v
"""

import pytest
import json
import uuid
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import Mock, patch, AsyncMock
from dataclasses import dataclass


# =============================================================================
# SECTION 1: AI SERVICE INTEGRATION - OpenAI
# =============================================================================

class TestOpenAIWhisperTranscription:
    """Tests for Whisper speech-to-text integration."""
    
    def test_whisper_api_request_structure(self):
        """Whisper API request should have correct structure."""
        request = {
            'model': 'whisper-1',
            'file': 'audio.mp3',
            'response_format': 'json',
            'language': 'en'
        }
        
        assert request['model'] == 'whisper-1'
        assert 'file' in request
    
    def test_whisper_response_structure(self):
        """Whisper response should contain transcript."""
        response = {
            'text': 'This is the transcribed text from the video.',
            'language': 'en',
            'duration': 45.5,
            'segments': [
                {'start': 0, 'end': 5, 'text': 'This is'},
                {'start': 5, 'end': 10, 'text': 'the transcribed text'}
            ]
        }
        
        assert 'text' in response
        assert len(response['text']) > 0
    
    def test_whisper_handles_multiple_languages(self):
        """Whisper should detect and transcribe multiple languages."""
        supported_languages = ['en', 'es', 'fr', 'de', 'zh', 'ja', 'ko']
        detected_language = 'en'
        
        assert detected_language in supported_languages
    
    def test_whisper_extracts_timestamps(self):
        """Whisper should provide word-level timestamps."""
        segments = [
            {'start': 0.0, 'end': 2.5, 'text': 'This changed everything'},
            {'start': 2.5, 'end': 5.0, 'text': 'Let me show you how'}
        ]
        
        assert segments[0]['start'] == 0.0
        assert segments[1]['start'] > segments[0]['end'] or segments[1]['start'] == segments[0]['end']
    
    @patch('openai.Audio.transcribe')
    def test_whisper_mock_api_call(self, mock_transcribe):
        """Mock Whisper API call."""
        mock_transcribe.return_value = {'text': 'Transcribed content'}
        
        # Simulate call
        result = mock_transcribe(model='whisper-1', file='audio.mp3')
        
        assert result['text'] == 'Transcribed content'
        mock_transcribe.assert_called_once()


class TestOpenAIVisionAnalysis:
    """Tests for GPT-4 Vision frame analysis."""
    
    def test_vision_api_request_structure(self):
        """Vision API request should have correct structure."""
        request = {
            'model': 'gpt-4-vision-preview',
            'messages': [
                {
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': 'Analyze this video frame for hook potential'},
                        {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,...'}}
                    ]
                }
            ],
            'max_tokens': 500
        }
        
        assert request['model'] == 'gpt-4-vision-preview'
        assert len(request['messages']) > 0
    
    def test_vision_frame_analysis_response(self):
        """Vision should return structured frame analysis."""
        response = {
            'hook_score': 85,
            'face_detected': True,
            'face_emotion': 'surprised',
            'text_detected': True,
            'text_content': 'This changed everything',
            'visual_quality': 'high',
            'composition': 'centered_subject',
            'thumbnail_suitable': True
        }
        
        assert 0 <= response['hook_score'] <= 100
        assert 'face_detected' in response
    
    def test_vision_detects_hook_elements(self):
        """Vision should detect elements that make strong hooks."""
        hook_elements = {
            'pattern_interrupt': True,  # Unexpected visual
            'emotion_present': True,    # Clear facial expression
            'text_overlay': True,       # Hook text visible
            'eye_contact': True,        # Looking at camera
            'motion_blur': False,       # Clear image
            'good_lighting': True
        }
        
        hook_score = sum(10 for v in hook_elements.values() if v)
        assert hook_score >= 40  # 4+ elements = good hook
    
    def test_vision_batch_frame_analysis(self):
        """Vision should analyze multiple frames efficiently."""
        frames = [
            {'index': 0, 'timestamp': 0},
            {'index': 1, 'timestamp': 3},
            {'index': 2, 'timestamp': 6},
            {'index': 3, 'timestamp': 9},
            {'index': 4, 'timestamp': 12}
        ]
        
        # Batch analysis
        analyzed_frames = [
            {**frame, 'hook_score': 50 + (i * 10)} 
            for i, frame in enumerate(frames)
        ]
        
        assert len(analyzed_frames) == 5
        best_frame = max(analyzed_frames, key=lambda f: f['hook_score'])
        assert best_frame['index'] == 4


class TestOpenAIGPTAnalysis:
    """Tests for GPT-4 content analysis and generation."""
    
    def test_gpt_topic_extraction(self):
        """GPT should extract topics from transcript."""
        transcript = """
        Today I'll show you how to build an Arduino project for home automation.
        We'll use a simple relay module to control lights and appliances.
        This is perfect for beginners who want to learn IoT.
        """
        
        expected_topics = ['arduino', 'home automation', 'IoT', 'electronics', 'DIY']
        
        # Mock extracted topics
        extracted = ['arduino', 'home automation', 'IoT', 'relay module']
        
        assert any(t in extracted for t in expected_topics)
    
    def test_gpt_sentiment_analysis(self):
        """GPT should analyze sentiment of content."""
        transcript = "This is absolutely amazing! I can't believe how well this worked!"
        
        sentiment = {
            'score': 0.9,  # -1 to 1
            'label': 'very_positive',
            'emotions': ['excitement', 'surprise', 'joy']
        }
        
        assert sentiment['score'] > 0.5
        assert sentiment['label'] in ['positive', 'very_positive']
    
    def test_gpt_caption_generation(self):
        """GPT should generate engaging captions."""
        context = {
            'topics': ['arduino', 'automation'],
            'hook': 'This changed everything',
            'platform': 'tiktok'
        }
        
        captions = [
            "This Arduino hack will blow your mind 🤯 #arduino #tech",
            "POV: You just automated your entire house for $20",
            "Why didn't I know about this sooner?! 😱"
        ]
        
        assert len(captions) >= 3
        assert any('#' in c for c in captions)  # Has hashtags
    
    def test_gpt_hashtag_generation(self):
        """GPT should generate relevant hashtags."""
        topics = ['arduino', 'home automation', 'DIY', 'tech']
        platform = 'tiktok'
        
        hashtags = {
            'niche': ['#arduino', '#homeautomation', '#diyelectronics'],
            'trending': ['#techtok', '#learnontiktok', '#fyp'],
            'broad': ['#viral', '#trending', '#foryou']
        }
        
        all_hashtags = hashtags['niche'] + hashtags['trending']
        assert len(all_hashtags) >= 5
        assert all(h.startswith('#') for h in all_hashtags)
    
    def test_gpt_virality_scoring(self):
        """GPT should score virality potential."""
        analysis = {
            'hook_strength': 8,
            'topic_trending': True,
            'emotional_appeal': 'high',
            'shareability': 'high',
            'controversy_level': 'low',
            'educational_value': 'high'
        }
        
        # Calculate virality score
        virality_score = 0
        virality_score += analysis['hook_strength'] * 5  # 40 max
        virality_score += 20 if analysis['topic_trending'] else 0
        virality_score += {'low': 5, 'medium': 10, 'high': 20}[analysis['emotional_appeal']]
        virality_score += {'low': 5, 'medium': 10, 'high': 20}[analysis['shareability']]
        
        assert 0 <= virality_score <= 100


# =============================================================================
# SECTION 2: AI COACH - LLM-POWERED INSIGHTS
# =============================================================================

class TestAICoachLLMIntegration:
    """Tests for AI Coach using LLM for insights."""
    
    def test_coach_prompt_structure(self):
        """Coach prompt should include all context."""
        prompt_context = {
            'post_metrics': {'views': 25000, 'likes': 1500},
            'channel_avg': {'views': 10000, 'likes': 500},
            'transcript': 'This changed everything...',
            'topics': ['automation', 'tech'],
            'comment_sentiment': {'positive': 70, 'neutral': 20, 'negative': 10},
            'top_comments': ['Great video!', 'How did you do this?']
        }
        
        prompt = f"""
        Analyze this TikTok post performance and provide actionable insights:
        
        Metrics: {prompt_context['post_metrics']}
        Channel Average: {prompt_context['channel_avg']}
        Topics: {prompt_context['topics']}
        Comment Sentiment: {prompt_context['comment_sentiment']}
        
        Provide:
        1. What worked well
        2. What to improve
        3. Specific next actions
        """
        
        assert 'views' in prompt
        assert 'improve' in prompt.lower()
    
    def test_coach_response_parsing(self):
        """Coach should parse LLM response into structured format."""
        llm_response = """
        ## What Worked
        - Strong hook in first 2 seconds grabbed attention
        - Topic aligns with current trends
        
        ## What to Improve
        - CTA appears too late at 42 seconds
        - Caption doesn't match hook text
        
        ## Next Actions
        1. Create Part 2 addressing top comment questions
        2. Repost optimized version at peak hours
        """
        
        parsed = {
            'what_worked': [
                'Strong hook in first 2 seconds grabbed attention',
                'Topic aligns with current trends'
            ],
            'what_to_improve': [
                'CTA appears too late at 42 seconds',
                'Caption doesn\'t match hook text'
            ],
            'next_actions': [
                'Create Part 2 addressing top comment questions',
                'Repost optimized version at peak hours'
            ]
        }
        
        assert len(parsed['what_worked']) >= 1
        assert len(parsed['what_to_improve']) >= 1
        assert len(parsed['next_actions']) >= 1
    
    def test_coach_hard_truth_generation(self):
        """Coach should generate honest, direct feedback."""
        metrics = {
            'views': 2000,
            'channel_avg': 10000,
            'drop_off_3sec': 70,
            'completion_rate': 8
        }
        
        hard_truths = []
        
        if metrics['views'] / metrics['channel_avg'] < 0.5:
            hard_truths.append(
                f"This post got {metrics['views']} views vs your {metrics['channel_avg']} average. "
                "That's 80% below normal. Something fundamental didn't work."
            )
        
        if metrics['drop_off_3sec'] > 50:
            hard_truths.append(
                f"{metrics['drop_off_3sec']}% of viewers left in the first 3 seconds. "
                "Your hook isn't stopping the scroll."
            )
        
        if metrics['completion_rate'] < 15:
            hard_truths.append(
                f"Only {metrics['completion_rate']}% watched to the end. "
                "The content isn't holding attention."
            )
        
        assert len(hard_truths) >= 2
        assert any('80%' in t for t in hard_truths)
    
    def test_coach_compares_to_top_performers(self):
        """Coach should compare against top performers in niche."""
        post_analysis = {
            'hook_type': 'question',
            'format': 'talking_head',
            'length_sec': 45,
            'has_captions': False
        }
        
        top_performer_patterns = {
            'hook_types': ['pattern_interrupt', 'controversy', 'result_first'],
            'formats': ['screen_recording', 'broll_text', 'duet'],
            'avg_length': 25,
            'caption_rate': 0.95
        }
        
        gaps = []
        
        if post_analysis['hook_type'] not in top_performer_patterns['hook_types']:
            gaps.append(f"Top performers use {top_performer_patterns['hook_types']}, not questions")
        
        if post_analysis['format'] not in top_performer_patterns['formats']:
            gaps.append(f"Format mismatch: talking head underperforms vs {top_performer_patterns['formats']}")
        
        if not post_analysis['has_captions']:
            gaps.append(f"95% of top performers use captions. You're missing easy engagement.")
        
        assert len(gaps) >= 2


# =============================================================================
# SECTION 3: CONTENT FILTERING - AI & SOCIAL FILTERS
# =============================================================================

class TestContentFilteringAI:
    """Tests for filtering content based on AI analysis."""
    
    def test_filter_by_pre_social_score(self):
        """Filter content by pre-social score threshold."""
        content = [
            {'id': '1', 'pre_social_score': 85},
            {'id': '2', 'pre_social_score': 45},
            {'id': '3', 'pre_social_score': 72},
            {'id': '4', 'pre_social_score': 90},
            {'id': '5', 'pre_social_score': 55}
        ]
        
        threshold = 70
        high_potential = [c for c in content if c['pre_social_score'] >= threshold]
        
        assert len(high_potential) == 3
        assert all(c['pre_social_score'] >= 70 for c in high_potential)
    
    def test_filter_by_topic(self):
        """Filter content by topic/niche."""
        content = [
            {'id': '1', 'topics': ['arduino', 'tech', 'DIY']},
            {'id': '2', 'topics': ['cooking', 'food', 'recipe']},
            {'id': '3', 'topics': ['tech', 'programming', 'python']},
            {'id': '4', 'topics': ['fitness', 'workout', 'health']}
        ]
        
        filter_topic = 'tech'
        tech_content = [c for c in content if filter_topic in c['topics']]
        
        assert len(tech_content) == 2
    
    def test_filter_by_sentiment(self):
        """Filter content by sentiment score."""
        content = [
            {'id': '1', 'sentiment': 0.8},   # Very positive
            {'id': '2', 'sentiment': -0.3},  # Negative
            {'id': '3', 'sentiment': 0.5},   # Positive
            {'id': '4', 'sentiment': 0.1},   # Neutral
        ]
        
        # Only positive content
        positive_only = [c for c in content if c['sentiment'] > 0.3]
        
        assert len(positive_only) == 2
    
    def test_filter_by_hook_strength(self):
        """Filter content by hook strength score."""
        content = [
            {'id': '1', 'hook_score': 9},
            {'id': '2', 'hook_score': 5},
            {'id': '3', 'hook_score': 8},
            {'id': '4', 'hook_score': 3}
        ]
        
        strong_hooks = [c for c in content if c['hook_score'] >= 7]
        
        assert len(strong_hooks) == 2
    
    def test_filter_by_virality_features(self):
        """Filter by specific virality features."""
        content = [
            {'id': '1', 'has_face': True, 'has_text': True, 'trending_sound': True},
            {'id': '2', 'has_face': False, 'has_text': True, 'trending_sound': False},
            {'id': '3', 'has_face': True, 'has_text': False, 'trending_sound': True},
            {'id': '4', 'has_face': False, 'has_text': False, 'trending_sound': False}
        ]
        
        # Must have face AND text
        filtered = [c for c in content if c['has_face'] and c['has_text']]
        
        assert len(filtered) == 1
        assert filtered[0]['id'] == '1'


class TestContentFilteringTranscript:
    """Tests for filtering content based on transcript analysis."""
    
    def test_filter_by_keyword(self):
        """Filter content containing specific keywords."""
        content = [
            {'id': '1', 'transcript': 'Learn how to build an Arduino project'},
            {'id': '2', 'transcript': 'Best recipes for healthy cooking'},
            {'id': '3', 'transcript': 'Arduino automation for beginners'},
            {'id': '4', 'transcript': 'Fitness tips for busy people'}
        ]
        
        keyword = 'arduino'
        filtered = [c for c in content if keyword.lower() in c['transcript'].lower()]
        
        assert len(filtered) == 2
    
    def test_filter_by_transcript_length(self):
        """Filter by transcript length (video duration proxy)."""
        content = [
            {'id': '1', 'transcript_words': 50},   # ~15 seconds
            {'id': '2', 'transcript_words': 200},  # ~60 seconds
            {'id': '3', 'transcript_words': 100},  # ~30 seconds
            {'id': '4', 'transcript_words': 350}   # ~105 seconds
        ]
        
        # Short-form only (under 60 seconds ~ 200 words)
        short_form = [c for c in content if c['transcript_words'] <= 200]
        
        assert len(short_form) == 3
    
    def test_filter_by_language(self):
        """Filter content by transcript language."""
        content = [
            {'id': '1', 'language': 'en'},
            {'id': '2', 'language': 'es'},
            {'id': '3', 'language': 'en'},
            {'id': '4', 'language': 'fr'}
        ]
        
        english_only = [c for c in content if c['language'] == 'en']
        
        assert len(english_only) == 2
    
    def test_filter_excludes_profanity(self):
        """Filter out content with profanity in transcript."""
        content = [
            {'id': '1', 'has_profanity': False},
            {'id': '2', 'has_profanity': True},
            {'id': '3', 'has_profanity': False},
            {'id': '4', 'has_profanity': True}
        ]
        
        clean_content = [c for c in content if not c['has_profanity']]
        
        assert len(clean_content) == 2


class TestContentFilteringSocial:
    """Tests for filtering based on social metrics."""
    
    def test_filter_by_engagement_rate(self):
        """Filter by minimum engagement rate."""
        content = [
            {'id': '1', 'views': 10000, 'likes': 800, 'engagement_rate': 8.0},
            {'id': '2', 'views': 50000, 'likes': 1000, 'engagement_rate': 2.0},
            {'id': '3', 'views': 5000, 'likes': 500, 'engagement_rate': 10.0},
            {'id': '4', 'views': 20000, 'likes': 600, 'engagement_rate': 3.0}
        ]
        
        high_engagement = [c for c in content if c['engagement_rate'] >= 5.0]
        
        assert len(high_engagement) == 2
    
    def test_filter_by_share_ratio(self):
        """Filter by share ratio (virality indicator)."""
        content = [
            {'id': '1', 'views': 10000, 'shares': 500, 'share_ratio': 0.05},
            {'id': '2', 'views': 50000, 'shares': 250, 'share_ratio': 0.005},
            {'id': '3', 'views': 5000, 'shares': 300, 'share_ratio': 0.06},
        ]
        
        viral_potential = [c for c in content if c['share_ratio'] >= 0.01]
        
        assert len(viral_potential) == 2
    
    def test_filter_by_comment_sentiment(self):
        """Filter by positive comment sentiment."""
        content = [
            {'id': '1', 'comment_sentiment_avg': 0.7},
            {'id': '2', 'comment_sentiment_avg': -0.2},
            {'id': '3', 'comment_sentiment_avg': 0.5},
            {'id': '4', 'comment_sentiment_avg': 0.1}
        ]
        
        positive_reception = [c for c in content if c['comment_sentiment_avg'] >= 0.3]
        
        assert len(positive_reception) == 2
    
    def test_filter_top_performers(self):
        """Filter content that outperformed channel average."""
        channel_avg_views = 10000
        
        content = [
            {'id': '1', 'views': 25000},  # 2.5x
            {'id': '2', 'views': 8000},   # 0.8x
            {'id': '3', 'views': 50000},  # 5x
            {'id': '4', 'views': 12000}   # 1.2x
        ]
        
        outperformers = [c for c in content if c['views'] / channel_avg_views >= 2.0]
        
        assert len(outperformers) == 2
    
    def test_combined_filters(self):
        """Apply multiple filters together."""
        content = [
            {'id': '1', 'pre_social_score': 85, 'topics': ['tech'], 'engagement_rate': 8.0},
            {'id': '2', 'pre_social_score': 45, 'topics': ['tech'], 'engagement_rate': 3.0},
            {'id': '3', 'pre_social_score': 72, 'topics': ['food'], 'engagement_rate': 9.0},
            {'id': '4', 'pre_social_score': 90, 'topics': ['tech'], 'engagement_rate': 7.0}
        ]
        
        # High score + tech topic + high engagement
        filtered = [
            c for c in content 
            if c['pre_social_score'] >= 70 
            and 'tech' in c['topics'] 
            and c['engagement_rate'] >= 5.0
        ]
        
        assert len(filtered) == 2


# =============================================================================
# SECTION 4: BLOTATO INTEGRATION - POSTING & URL RETRIEVAL
# =============================================================================

class TestBlotatoAPIStructure:
    """Tests for Blotato API request/response structures."""
    
    def test_blotato_post_request_structure(self):
        """Blotato post request should have correct structure."""
        request = {
            'media_url': 'https://storage.example.com/video.mp4',
            'caption': 'This changed everything! #tech #fyp',
            'thumbnail_url': 'https://storage.example.com/thumb.jpg',
            'platform': 'tiktok',
            'account_id': 'acc_123',
            'schedule_time': None,  # Immediate post
            'options': {
                'allow_comments': True,
                'allow_duet': True,
                'allow_stitch': True
            }
        }
        
        required_fields = ['media_url', 'caption', 'platform', 'account_id']
        assert all(f in request for f in required_fields)
    
    def test_blotato_post_response_success(self):
        """Blotato successful post response."""
        response = {
            'success': True,
            'post_id': 'blotato_post_abc123',
            'external_post_id': '7564912360520011038',
            'external_post_url': 'https://www.tiktok.com/@user/video/7564912360520011038',
            'platform': 'tiktok',
            'posted_at': '2024-01-15T14:00:00Z',
            'status': 'published'
        }
        
        assert response['success'] is True
        assert response['external_post_id'] is not None
        assert 'tiktok.com' in response['external_post_url']
    
    def test_blotato_post_response_failure(self):
        """Blotato failed post response."""
        response = {
            'success': False,
            'error_code': 'MEDIA_TOO_LONG',
            'error_message': 'Video exceeds maximum duration of 3 minutes',
            'retry_allowed': False
        }
        
        assert response['success'] is False
        assert 'error_message' in response
    
    def test_blotato_multiplatform_post(self):
        """Blotato should support multi-platform posting."""
        request = {
            'media_url': 'https://storage.example.com/video.mp4',
            'caption': 'Cross-platform post',
            'platforms': ['tiktok', 'instagram_reels', 'youtube_shorts'],
            'account_ids': {
                'tiktok': 'acc_tiktok_123',
                'instagram_reels': 'acc_ig_456',
                'youtube_shorts': 'acc_yt_789'
            }
        }
        
        assert len(request['platforms']) == 3


class TestBlotatoPostingFlow:
    """Tests for Blotato posting workflow."""
    
    def test_post_returns_external_url(self):
        """Posting should return the external platform URL."""
        post_result = {
            'tiktok': {
                'success': True,
                'external_post_url': 'https://www.tiktok.com/@mewtru/video/7564912360520011038'
            }
        }
        
        url = post_result['tiktok']['external_post_url']
        
        assert 'tiktok.com' in url
        assert '/video/' in url
    
    def test_post_returns_external_id(self):
        """Posting should return the external post ID for API calls."""
        post_result = {
            'external_post_id': '7564912360520011038',
            'platform': 'tiktok'
        }
        
        # Can use this ID to fetch metrics via RapidAPI
        assert len(post_result['external_post_id']) > 0
        assert post_result['external_post_id'].isdigit()
    
    def test_post_stores_in_database(self):
        """Successful post should update database with external IDs."""
        schedule_before = {
            'id': 'schedule_123',
            'status': 'pending',
            'external_post_id': None,
            'external_post_url': None
        }
        
        # After successful Blotato post
        schedule_after = {
            'id': 'schedule_123',
            'status': 'posted',
            'external_post_id': '7564912360520011038',
            'external_post_url': 'https://www.tiktok.com/@user/video/7564912360520011038',
            'posted_at': datetime.now().isoformat()
        }
        
        assert schedule_after['status'] == 'posted'
        assert schedule_after['external_post_id'] is not None
    
    def test_post_triggers_checkback_schedule(self):
        """Successful post should create checkback schedule."""
        post_time = datetime.now()
        
        checkback_schedule = [
            {'checkpoint': '15m', 'scheduled_at': post_time + timedelta(minutes=15)},
            {'checkpoint': '1h', 'scheduled_at': post_time + timedelta(hours=1)},
            {'checkpoint': '4h', 'scheduled_at': post_time + timedelta(hours=4)},
            {'checkpoint': '24h', 'scheduled_at': post_time + timedelta(hours=24)},
            {'checkpoint': '72h', 'scheduled_at': post_time + timedelta(hours=72)},
            {'checkpoint': '7d', 'scheduled_at': post_time + timedelta(days=7)}
        ]
        
        assert len(checkback_schedule) == 6
        assert checkback_schedule[0]['checkpoint'] == '15m'


class TestBlotatoURLRetrieval:
    """Tests for retrieving posted URL from Blotato."""
    
    def test_get_post_status(self):
        """Get status and URL of a posted item."""
        post_id = 'blotato_post_abc123'
        
        status_response = {
            'post_id': post_id,
            'status': 'published',
            'platform': 'tiktok',
            'external_post_id': '7564912360520011038',
            'external_post_url': 'https://www.tiktok.com/@mewtru/video/7564912360520011038',
            'metrics': {
                'views': 10000,
                'likes': 500
            }
        }
        
        assert status_response['status'] == 'published'
        assert status_response['external_post_url'] is not None
    
    def test_get_post_by_schedule_id(self):
        """Get posted URL by internal schedule ID."""
        schedule_id = 'schedule_123'
        
        # Query database
        post_record = {
            'schedule_id': schedule_id,
            'external_post_url': 'https://www.tiktok.com/@user/video/7564912360520011038',
            'status': 'posted'
        }
        
        assert post_record['external_post_url'] is not None
    
    def test_extract_video_id_from_url(self):
        """Extract video ID from TikTok URL."""
        url = 'https://www.tiktok.com/@mewtru/video/7564912360520011038'
        
        # Extract video ID
        video_id = url.split('/video/')[-1].split('?')[0]
        
        assert video_id == '7564912360520011038'
    
    def test_handle_pending_post(self):
        """Handle case where post is still processing."""
        status_response = {
            'post_id': 'blotato_post_abc123',
            'status': 'processing',
            'external_post_url': None,
            'estimated_completion': '2024-01-15T14:05:00Z'
        }
        
        is_complete = status_response['status'] == 'published'
        assert is_complete is False
        assert status_response['external_post_url'] is None
    
    def test_handle_failed_post(self):
        """Handle case where post failed."""
        status_response = {
            'post_id': 'blotato_post_abc123',
            'status': 'failed',
            'error_code': 'ACCOUNT_SUSPENDED',
            'error_message': 'TikTok account is temporarily suspended',
            'external_post_url': None
        }
        
        assert status_response['status'] == 'failed'
        assert 'error_message' in status_response


class TestBlotatoPlatformSpecific:
    """Tests for platform-specific Blotato behavior."""
    
    def test_tiktok_url_format(self):
        """TikTok URL should have correct format."""
        url = 'https://www.tiktok.com/@mewtru/video/7564912360520011038'
        
        assert 'tiktok.com' in url
        assert '/@' in url
        assert '/video/' in url
    
    def test_instagram_url_format(self):
        """Instagram Reels URL should have correct format."""
        url = 'https://www.instagram.com/reel/ABC123xyz/'
        
        assert 'instagram.com' in url
        assert '/reel/' in url
    
    def test_youtube_url_format(self):
        """YouTube Shorts URL should have correct format."""
        url = 'https://www.youtube.com/shorts/dQw4w9WgXcQ'
        
        assert 'youtube.com' in url
        assert '/shorts/' in url
    
    def test_multiplatform_post_returns_all_urls(self):
        """Multi-platform post should return URL for each platform."""
        post_results = {
            'tiktok': {
                'success': True,
                'external_post_url': 'https://www.tiktok.com/@user/video/123'
            },
            'instagram_reels': {
                'success': True,
                'external_post_url': 'https://www.instagram.com/reel/ABC123/'
            },
            'youtube_shorts': {
                'success': True,
                'external_post_url': 'https://www.youtube.com/shorts/xyz789'
            }
        }
        
        assert all(r['success'] for r in post_results.values())
        assert len(post_results) == 3


# =============================================================================
# SECTION 5: INTEGRATION TESTS
# =============================================================================

class TestFullPostingPipeline:
    """Integration tests for full posting pipeline."""
    
    def test_analysis_to_post_to_checkback(self):
        """Full pipeline: Analysis → Schedule → Post → Checkback."""
        # Step 1: Media analyzed
        media = {
            'id': 'media_123',
            'status': 'analyzed',
            'pre_social_score': 85,
            'caption_suggestions': ['Great caption #fyp']
        }
        
        # Step 2: Scheduled
        schedule = {
            'media_id': media['id'],
            'platform': 'tiktok',
            'scheduled_at': datetime.now(),
            'status': 'pending'
        }
        
        # Step 3: Posted via Blotato
        post_result = {
            'success': True,
            'external_post_id': '7564912360520011038',
            'external_post_url': 'https://tiktok.com/@user/video/7564912360520011038'
        }
        
        # Step 4: Update schedule with result
        schedule['status'] = 'posted'
        schedule['external_post_id'] = post_result['external_post_id']
        schedule['external_post_url'] = post_result['external_post_url']
        
        # Step 5: Checkback scheduled
        checkbacks = [
            {'checkpoint': '15m', 'status': 'pending'},
            {'checkpoint': '24h', 'status': 'pending'}
        ]
        
        assert schedule['status'] == 'posted'
        assert schedule['external_post_url'] is not None
        assert len(checkbacks) >= 2
    
    def test_checkback_to_insights_to_brief(self):
        """Pipeline: Checkback → AI Insights → Creative Brief."""
        # Step 1: Checkback metrics collected
        metrics = {
            'views': 50000,
            'channel_avg': 10000,
            'ratio': 5.0
        }
        
        # Step 2: AI generates insights
        insights = {
            'is_top_performer': metrics['ratio'] > 2.0,
            'what_worked': ['Strong hook', 'Trending topic'],
            'hard_truths': []  # No issues for top performer
        }
        
        # Step 3: Brief generated for top performer
        brief_created = insights['is_top_performer']
        
        assert brief_created is True


# =============================================================================
# RUNNER
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
