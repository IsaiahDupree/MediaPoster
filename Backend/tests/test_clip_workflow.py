"""
Integration Tests for Complete Clip Workflow
Tests end-to-end: Video → Analysis → Clip Suggestion → Create → Publish → Analytics
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
import uuid

from services.clip_selector import ClipSelector
from services.clip_editor import ClipEditor
from services.clip_publisher import ClipPublisher
from database.models import AnalyzedVideo, VideoSegment, VideoFrame, VideoClip, PlatformPost, ClipPost


@pytest.fixture
def complete_video(db_session):
    """Create a complete video with segments and frames"""
    # Create video
    video = AnalyzedVideo(
        id=uuid.uuid4(),
        duration_seconds=90.0
    )
    db_session.add(video)
    db_session.commit()
    
    # Create segments (hook, body, CTA)
    segments = [
        VideoSegment(
            video_id=video.id,
            segment_type="hook",
            start_s=0.0,
            end_s=12.0,
            emotion="curiosity",
            hook_type="fear_aspiration"
        ),
        VideoSegment(
            video_id=video.id,
            segment_type="body",
            start_s=12.0,
            end_s=70.0,
            emotion="interest"
        ),
        VideoSegment(
            video_id=video.id,
            segment_type="cta",
            start_s=70.0,
            end_s=90.0,
            emotion="motivation"
        )
    ]
    
    for seg in segments:
        db_session.add(seg)
    
    # Create frames
    for i in range(9):
        frame = VideoFrame(
            video_id=video.id,
            frame_time_s=i * 10.0,
            frame_url=f"/frames/{i}.jpg",
            is_pattern_interrupt=(i % 2 == 0),
            objects=["person"]
        )
        db_session.add(frame)
    
    db_session.commit()
    return video


@pytest.mark.asyncio
class TestCompleteWorkflow:
    """Test complete clip generation workflow"""
    
    async def test_full_workflow_video_to_post(self, db_session, complete_video):
        """
        Test complete workflow:
        1. Video with analysis exists
        2. Get AI clip suggestions
        3. Create clip from suggestion
        4. Generate platform variants
        5. Publish to platforms
        6. Verify post creation
        """
        user_id = str(uuid.uuid4())
        
        # Step 1: Video with analysis exists (from fixture)
        assert complete_video.id is not None
        
        # Step 2: Get AI clip suggestions
        selector = ClipSelector(db_session)
        
        with patch('openai.chat.completions.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "REASONING: Strong hook\nTITLE: Viral Content"
            mock_openai.return_value = mock_response
            
            suggestions = await selector.suggest_clips(
                video_id=str(complete_video.id),
                platform="tiktok",
                max_clips=3
            )
            
            assert len(suggestions) > 0
            best_suggestion = suggestions[0]
            
            # Step 3: Create clip from suggestion
            editor = ClipEditor(db_session)
            clip = editor.create_clip(
                video_id=str(complete_video.id),
                user_id=user_id,
                start_time=best_suggestion.start_time,
                end_time=best_suggestion.end_time,
                title=best_suggestion.suggested_title,
                clip_type="ai_generated",
                ai_suggested=True,
                ai_score=best_suggestion.ai_score,
                ai_reasoning=best_suggestion.reasoning
            )
            
            assert clip.id is not None
            assert clip.ai_score == best_suggestion.ai_score
            
            # Step 4: Generate platform variants
            variants = editor.generate_platform_variants(
                str(clip.id),
                platforms=["tiktok", "instagram_reel", "youtube_short"]
            )
            
            assert len(variants) == 3
            assert "tiktok" in variants
            
            # Step 5: Publish to platforms
            publisher = ClipPublisher(db_session)
            
            posts = await publisher.publish_clip(
                clip_id=str(clip.id),
                platforms=["tiktok", "instagram_reel"],
                schedule_time=datetime.now() + timedelta(hours=2)
            )
            
            # Step 6: Verify post creation
            assert len(posts) == 2
            
            # Verify ClipPost relationships were created
            clip_posts = db_session.query(ClipPost).filter(
                ClipPost.clip_id == clip.id
            ).all()
            
            assert len(clip_posts) == 2
            assert any(cp.platform == "tiktok" for cp in clip_posts)
            assert any(cp.platform == "instagram_reel" for cp in clip_posts)
    
    async def test_ai_suggestion_to_publish(self, db_session, complete_video):
        """Test quick workflow from AI suggestion directly to publish"""
        user_id = str(uuid.uuid4())
        
        # Get suggestion
        selector = ClipSelector(db_session)
        
        with patch('openai.chat.completions.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "REASONING: Great\nTITLE: Amazing"
            mock_openai.return_value = mock_response
            
            suggestions = await selector.suggest_clips(
                video_id=str(complete_video.id),
                max_clips=1
            )
            
            # Create and publish in one flow
            editor = ClipEditor(db_session)
            clip = editor.create_clip(
                video_id=str(complete_video.id),
                user_id=user_id,
                start_time=suggestions[0].start_time,
                end_time=suggestions[0].end_time,
                title=suggestions[0].suggested_title,
                ai_suggested=True,
                ai_score=suggestions[0].ai_score
            )
            
            # Generate variants
            editor.generate_platform_variants(str(clip.id))
            
            # Publish immediately
            publisher = ClipPublisher(db_session)
            posts = await publisher.publish_clip(
                clip_id=str(clip.id),
                platforms=["tiktok"],
                schedule_time=None  # Immediate
            )
            
            assert len(posts) == 1
            assert posts[0].status == "draft"  # Draft since no schedule time
    
    async def test_multi_clip_generation_from_video(self, db_session, complete_video):
        """Test generating multiple clips from one video"""
        user_id = str(uuid.uuid4())
        
        selector = ClipSelector(db_session)
        editor = ClipEditor(db_session)
        
        with patch('openai.chat.completions.create') as mock_openai:
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = "REASONING: Test\nTITLE: Test"
            mock_openai.return_value = mock_response
            
            # Get multiple suggestions
            suggestions = await selector.suggest_clips(
                video_id=str(complete_video.id),
                max_clips=3
            )
            
            # Create clips from each suggestion
            created_clips = []
            for i, suggestion in enumerate(suggestions):
                clip = editor.create_clip(
                    video_id=str(complete_video.id),
                    user_id=user_id,
                    start_time=suggestion.start_time,
                    end_time=suggestion.end_time,
                    title=f"Clip {i+1}: {suggestion.suggested_title}",
                    ai_suggested=True,
                    ai_score=suggestion.ai_score
                )
                created_clips.append(clip)
            
            # Verify all clips were created
            all_clips = editor.get_video_clips(str(complete_video.id))
            assert len(all_clips) >= len(suggestions)


class TestClipPerformanceTracking:
    """Test clip performance tracking across platforms"""
    
    @pytest.mark.asyncio
    async def test_clip_performance_aggregation(self, db_session, complete_video):
        """Test that clip performance aggregates across platforms"""
        user_id = str(uuid.uuid4())
        
        # Create clip
        editor = ClipEditor(db_session)
        clip = editor.create_clip(
            video_id=str(complete_video.id),
            user_id=user_id,
            start_time=0.0,
            end_time=30.0,
            title="Performance Test Clip"
        )
        
        # Publish to multiple platforms
        publisher = ClipPublisher(db_session)
        await publisher.publish_clip(
            clip_id=str(clip.id),
            platforms=["tiktok", "instagram_reel", "youtube_short"]
        )
        
        # Get performance
        performance = publisher.get_clip_performance(str(clip.id))
        
        assert performance["clip_id"] == str(clip.id)
        assert performance["total_posts"] == 3
        assert len(performance["platforms"]) == 3
        assert "platform_breakdown" in performance


class TestClipEditing:
    """Test clip editing and iteration"""
    
    @pytest.mark.asyncio
    async def test_edit_clip_after_creation(self, db_session, complete_video):
        """Test editing clip configuration after creation"""
        user_id = str(uuid.uuid4())
        
        # Create initial clip
        editor = ClipEditor(db_session)
        clip = editor.create_clip(
            video_id=str(complete_video.id),
            user_id=user_id,
            start_time=10.0,
            end_time=40.0,
            title="Initial Title"
        )
        
        # Edit configuration
        updated_clip = editor.update_clip_config(
            clip_id=str(clip.id),
            title="Updated Title",
            overlay_config={"text": "AMAZING", "position": "bottom"},
            status="ready"
        )
        
        assert updated_clip.title == "Updated Title"
        assert updated_clip.overlay_config["text"] == "AMAZING"
        assert updated_clip.status == "ready"
        
        # Regenerate variants with new config
        variants = editor.generate_platform_variants(str(clip.id))
        assert len(variants) > 0


class TestErrorHandling:
    """Test error handling in workflow"""
    
    @pytest.mark.asyncio
    async def test_publish_clip_without_variants(self, db_session, complete_video):
        """Test that publishing works even without pre-generated variants"""
        user_id = str(uuid.uuid4())
        
        editor = ClipEditor(db_session)
        clip = editor.create_clip(
            video_id=str(complete_video.id),
            user_id=user_id,
            start_time=5.0,
            end_time=35.0
        )
        
        # Publish without generating variants first
        publisher = ClipPublisher(db_session)
        posts = await publisher.publish_clip(
            clip_id=str(clip.id),
            platforms=["tiktok"]
        )
        
        # Should still succeed
        assert len(posts) == 1
    
    @pytest.mark.asyncio
    async def test_publish_invalid_clip_raises_error(self, db_session):
        """Test that publishing invalid clip raises error"""
        publisher = ClipPublisher(db_session)
        
        with pytest.raises(ValueError, match="not found"):
            await publisher.publish_clip(
                clip_id=str(uuid.uuid4()),
                platforms=["tiktok"]
            )
    
    @pytest.mark.asyncio
    async def test_publish_no_platforms_raises_error(self, db_session, complete_video):
        """Test that publishing with no platforms raises error"""
        user_id = str(uuid.uuid4())
        
        editor = ClipEditor(db_session)
        clip = editor.create_clip(
            video_id=str(complete_video.id),
            user_id=user_id,
            start_time=0.0,
            end_time=30.0
        )
        
        publisher = ClipPublisher(db_session)
        
        with pytest.raises(ValueError, match="At least one platform"):
            await publisher.publish_clip(
                clip_id=str(clip.id),
                platforms=[]
            )
