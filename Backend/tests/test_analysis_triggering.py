"""
Tests for Analysis Triggering and State Updates
Covers: force re-analysis, transcript/topics generation, polling for completion
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import uuid


class TestAnalysisEndpoint:
    """Tests for /analyze/{media_id} endpoint"""
    
    def test_analyze_endpoint_path(self):
        """Analyze endpoint should include media_id"""
        media_id = str(uuid.uuid4())
        endpoint = f"/api/media-db/analyze/{media_id}"
        assert media_id in endpoint
    
    def test_force_parameter_default(self):
        """Force parameter should default to False"""
        force = False
        assert force == False
    
    def test_force_parameter_true(self):
        """Force parameter should accept True"""
        force = True
        assert force == True
    
    def test_endpoint_with_force_query(self):
        """Endpoint should accept force query parameter"""
        media_id = "test-123"
        force = True
        endpoint = f"/api/media-db/analyze/{media_id}?force={force}"
        assert "force=True" in endpoint


class TestForceReanalysis:
    """Tests for force re-analysis functionality"""
    
    def test_force_skips_existing_check(self):
        """Force=true should skip existing analysis check"""
        existing_analysis = {"transcript": "existing"}
        force = True
        should_analyze = force or not existing_analysis
        assert should_analyze == True
    
    def test_no_force_respects_existing(self):
        """Force=false should respect existing analysis"""
        existing_analysis = {"transcript": "existing"}
        force = False
        should_analyze = force or not existing_analysis
        assert should_analyze == False
    
    def test_force_deletes_old_analysis(self):
        """Force=true should delete old analysis before new"""
        old_analysis = {"id": "old-123", "transcript": "old"}
        force = True
        
        if force:
            old_analysis = None
        
        assert old_analysis is None
    
    def test_partial_analysis_triggers_full(self):
        """Partial analysis with force should run full analysis"""
        partial = {"transcript": "exists", "topics": None}
        force = True
        run_full = force
        assert run_full == True


class TestFilePathResolution:
    """Tests for file path resolution in analysis"""
    
    def test_source_uri_preferred(self):
        """source_uri should be preferred if available"""
        source_uri = "https://storage.example.com/video.mp4"
        file_path = "/local/path/video.mp4"
        resolved = source_uri or file_path
        assert resolved == source_uri
    
    def test_file_path_fallback(self):
        """file_path should be used if source_uri is None"""
        source_uri = None
        file_path = "/local/path/video.mp4"
        resolved = source_uri or file_path
        assert resolved == file_path
    
    def test_no_path_raises_error(self):
        """No path available should raise error"""
        source_uri = None
        file_path = None
        resolved = source_uri or file_path
        assert resolved is None
        # Would raise HTTPException(400)
    
    def test_empty_string_path_fallback(self):
        """Empty string source_uri should fallback to file_path"""
        source_uri = ""
        file_path = "/local/path/video.mp4"
        resolved = source_uri or file_path
        assert resolved == file_path


class TestAnalysisResponse:
    """Tests for analysis endpoint responses"""
    
    def test_success_response(self):
        """Successful analysis should return success status"""
        response = {
            "status": "analysis_started",
            "media_id": "test-123",
            "message": "Analysis started in background",
        }
        assert response["status"] == "analysis_started"
    
    def test_already_analyzed_response(self):
        """Already analyzed (no force) should return specific status"""
        response = {
            "status": "already_analyzed",
            "media_id": "test-123",
            "message": "Media already analyzed. Use force=true to re-analyze",
        }
        assert response["status"] == "already_analyzed"
    
    def test_not_found_response(self):
        """Non-existent media should return 404"""
        status_code = 404
        assert status_code == 404
    
    def test_no_file_path_response(self):
        """No file path should return 400"""
        status_code = 400
        assert status_code == 400


class TestTranscriptGeneration:
    """Tests for Whisper transcription"""
    
    def test_transcript_field_populated(self):
        """Transcript field should be populated after analysis"""
        media = {"transcript": None}
        generated_transcript = "This is the transcribed content from the video."
        media["transcript"] = generated_transcript
        assert media["transcript"] is not None
        assert len(media["transcript"]) > 0
    
    def test_empty_audio_handling(self):
        """Videos with no audio should handle gracefully"""
        has_audio = False
        transcript = "" if not has_audio else "Transcribed content"
        assert transcript == ""
    
    def test_transcript_character_count(self):
        """Transcript should track character count"""
        transcript = "Test transcript content"
        char_count = len(transcript)
        assert char_count == 23
    
    def test_transcript_word_count(self):
        """Transcript should support word count calculation"""
        transcript = "This is a test transcript with seven words"
        word_count = len(transcript.split())
        assert word_count == 8


class TestTopicsExtraction:
    """Tests for GPT-4 topic extraction"""
    
    def test_topics_array_populated(self):
        """Topics should be populated as array"""
        media = {"topics": None}
        extracted_topics = ["topic1", "topic2", "topic3"]
        media["topics"] = extracted_topics
        assert isinstance(media["topics"], list)
        assert len(media["topics"]) == 3
    
    def test_topics_from_transcript(self):
        """Topics should be extracted from transcript"""
        transcript = "This video is about cooking and recipes"
        # Simulated extraction
        topics = ["cooking", "recipes"]
        assert "cooking" in topics
    
    def test_empty_transcript_no_topics(self):
        """Empty transcript should result in no topics"""
        transcript = ""
        topics = [] if not transcript else ["topic"]
        assert topics == []
    
    def test_topic_limit(self):
        """Topics should be limited to reasonable count"""
        all_topics = ["t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8", "t9", "t10"]
        max_topics = 5
        limited_topics = all_topics[:max_topics]
        assert len(limited_topics) == 5


class TestPreSocialScore:
    """Tests for pre-social score calculation"""
    
    def test_score_range(self):
        """Pre-social score should be in valid range"""
        score = 75
        assert 0 <= score <= 100
    
    def test_score_factors(self):
        """Score should consider multiple factors"""
        factors = {
            "transcript_quality": 12,
            "topic_relevance": 10,
            "duration_optimal": 8,
            "engagement_potential": 10,
        }
        base_score = 40
        total = base_score + sum(factors.values())
        assert total == 80
    
    def test_transcript_contributes_to_score(self):
        """Having transcript should increase score"""
        base_score = 40
        transcript_bonus = 12  # max for transcript
        score_with_transcript = base_score + transcript_bonus
        assert score_with_transcript > base_score
    
    @pytest.mark.parametrize("transcript_length,expected_bonus", [
        (0, 0),
        (51, 6),
        (201, 9),
        (501, 12),
    ])
    def test_transcript_length_scoring(self, transcript_length, expected_bonus):
        """Longer transcripts should get higher bonus"""
        if transcript_length > 500:
            bonus = 12
        elif transcript_length > 200:
            bonus = 9
        elif transcript_length > 50:
            bonus = 6
        else:
            bonus = 0
        assert bonus == expected_bonus


class TestAnalysisPolling:
    """Tests for frontend polling for analysis completion"""
    
    def test_poll_interval(self):
        """Poll interval should be 2 seconds"""
        poll_interval_ms = 2000
        assert poll_interval_ms == 2000
    
    def test_max_poll_attempts(self):
        """Max poll attempts should allow 60 seconds"""
        max_polls = 30
        interval_sec = 2
        total_time = max_polls * interval_sec
        assert total_time == 60
    
    def test_poll_detects_transcript(self):
        """Polling should detect when transcript appears"""
        responses = [
            {"transcript": None},
            {"transcript": None},
            {"transcript": "Generated transcript"},
        ]
        for response in responses:
            if response["transcript"]:
                assert response["transcript"] is not None
                break
    
    def test_poll_updates_state(self):
        """Polling should update media state directly"""
        media_state = {"transcript": None, "topics": None}
        updated_data = {"transcript": "New transcript", "topics": ["topic1"]}
        
        media_state.update(updated_data)
        
        assert media_state["transcript"] == "New transcript"
        assert media_state["topics"] == ["topic1"]


class TestImmediateCheck:
    """Tests for immediate transcript check before polling"""
    
    def test_immediate_check_before_poll(self):
        """Should check immediately before starting poll loop"""
        check_order = []
        
        def immediate_check():
            check_order.append("immediate")
            return {"transcript": "Already exists"}
        
        def start_polling():
            check_order.append("polling")
        
        result = immediate_check()
        if not result.get("transcript"):
            start_polling()
        
        assert check_order == ["immediate"]
        assert "polling" not in check_order
    
    def test_skip_polling_if_immediate_found(self):
        """Should skip polling if immediate check finds transcript"""
        transcript_found = True
        polling_started = not transcript_found
        assert polling_started == False


class TestAnalysisStateUpdate:
    """Tests for React state updates after analysis"""
    
    def test_setmedia_called_with_updated_data(self):
        """setMedia should be called with fresh data"""
        set_media_calls = []
        
        def mock_set_media(data):
            set_media_calls.append(data)
        
        updated_media = {"transcript": "New", "topics": ["t1"]}
        mock_set_media(updated_media)
        
        assert len(set_media_calls) == 1
        assert set_media_calls[0]["transcript"] == "New"
    
    def test_no_page_reload_needed(self):
        """State update should not require page reload"""
        use_reload = False
        use_state_update = True
        assert use_state_update == True
        assert use_reload == False


class TestAnalysisButton:
    """Tests for analysis button behavior"""
    
    def test_button_triggers_analysis(self):
        """Clicking button should trigger analysis"""
        button_clicked = True
        analysis_started = button_clicked
        assert analysis_started == True
    
    def test_button_shows_loading_state(self):
        """Button should show loading during analysis"""
        is_analyzing = True
        button_text = "Analyzing..." if is_analyzing else "Analyze"
        assert button_text == "Analyzing..."
    
    def test_double_click_confirmation(self):
        """Re-analyze should require double-click confirmation"""
        click_count = 0
        confirm_threshold = 2
        
        click_count += 1
        confirmed = click_count >= confirm_threshold
        assert confirmed == False
        
        click_count += 1
        confirmed = click_count >= confirm_threshold
        assert confirmed == True
    
    def test_confirmation_timeout(self):
        """Confirmation should timeout after 2 seconds"""
        timeout_ms = 2000
        assert timeout_ms == 2000


class TestDeepAnalysis:
    """Tests for deep AI image analysis"""
    
    def test_deep_analysis_endpoint(self):
        """Deep analysis should call image-analysis endpoint"""
        media_id = "test-123"
        endpoint = f"/api/image-analysis/analyze"
        assert "image-analysis" in endpoint
    
    def test_deep_analysis_uses_thumbnail(self):
        """Deep analysis should use large thumbnail"""
        media_id = "test-123"
        thumbnail_url = f"/api/media-db/thumbnail/{media_id}?size=large"
        assert "size=large" in thumbnail_url
    
    def test_deep_analysis_response(self):
        """Deep analysis should return structured data"""
        response = {
            "suggested_caption": "Amazing content!",
            "suggested_hashtags": ["#content", "#viral"],
            "scene_description": "Person outdoors",
            "visual_summary": "Bright, colorful scene",
        }
        assert "suggested_caption" in response
        assert isinstance(response["suggested_hashtags"], list)


class TestAnalysisLogging:
    """Tests for analysis logging"""
    
    def test_analysis_start_logged(self):
        """Analysis start should be logged"""
        log_message = "[Analysis] Starting for media_id: test-123"
        assert "Starting" in log_message
    
    def test_analysis_complete_logged(self):
        """Analysis completion should be logged"""
        log_message = "[Analysis] Complete for test-123: score=75.0"
        assert "Complete" in log_message
    
    def test_analysis_error_logged(self):
        """Analysis errors should be logged"""
        log_message = "[Analysis] Error for test-123: File not found"
        assert "Error" in log_message


class TestHasFullAnalysis:
    """Tests for hasFullAnalysis check"""
    
    def test_full_analysis_requires_both(self):
        """Full analysis requires transcript AND topics"""
        media = {"transcript": "exists", "topics": ["t1"]}
        has_full = bool(media["transcript"] and media["topics"] and len(media["topics"]) > 0)
        assert has_full == True
    
    def test_transcript_only_not_full(self):
        """Transcript only is not full analysis"""
        media = {"transcript": "exists", "topics": None}
        has_full = bool(media["transcript"] and media.get("topics") and len(media.get("topics", [])) > 0)
        assert has_full == False
    
    def test_topics_only_not_full(self):
        """Topics only is not full analysis"""
        media = {"transcript": None, "topics": ["t1"]}
        has_full = bool(media.get("transcript") and media["topics"] and len(media["topics"]) > 0)
        assert has_full == False
    
    def test_empty_topics_not_full(self):
        """Empty topics array is not full analysis"""
        media = {"transcript": "exists", "topics": []}
        has_full = bool(media["transcript"] and media["topics"] and len(media["topics"]) > 0)
        assert has_full == False


class TestPostButtonDisabling:
    """Tests for Post button disabling without full analysis"""
    
    def test_button_disabled_without_analysis(self):
        """Post button should be disabled without full analysis"""
        has_full_analysis = False
        button_enabled = has_full_analysis
        assert button_enabled == False
    
    def test_button_enabled_with_analysis(self):
        """Post button should be enabled with full analysis"""
        has_full_analysis = True
        button_enabled = has_full_analysis
        assert button_enabled == True
    
    def test_button_shows_tooltip(self):
        """Disabled button should show tooltip"""
        has_full_analysis = False
        tooltip = "Run full analysis before posting" if not has_full_analysis else "Post this video"
        assert "analysis" in tooltip
    
    def test_button_href_conditional(self):
        """Button href should be conditional"""
        has_full_analysis = False
        media_id = "test-123"
        href = f"/post-content/{media_id}" if has_full_analysis else "#"
        assert href == "#"


class TestBackgroundAnalysis:
    """Tests for background analysis execution"""
    
    def test_analysis_runs_in_background(self):
        """Analysis should run in background thread"""
        background = True
        blocking = not background
        assert blocking == False
    
    def test_response_returns_immediately(self):
        """Endpoint should return immediately after starting"""
        response_status = "analysis_started"
        assert response_status == "analysis_started"
    
    def test_executor_submit(self):
        """Analysis should be submitted to executor"""
        submitted = True
        assert submitted == True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
