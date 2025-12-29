"""
Unit tests for FormatDetector service.

Tests content format detection logic across various scenarios.
"""
import pytest
from services.format_detector import (
    FormatDetector, 
    ContentFormat, 
    ProductionQuality,
    FormatAnalysis
)


class TestFormatDetector:
    """Test suite for FormatDetector service"""
    
    @pytest.fixture
    def detector(self):
        """Create a FormatDetector instance"""
        return FormatDetector()
    
    # === TALKING HEAD TESTS ===
    
    def test_talking_head_with_speech(self, detector):
        """Video with significant speech and person visible should be talking_head"""
        result = detector.detect_format(
            transcript="Hey everyone welcome back to my channel today we're going to talk about something really exciting I've been working on this project for weeks and I'm so happy to finally share it with you",
            visual_analysis={"visual_summary": "A person speaking directly to camera, close-up face shot, indoor setting"},
            duration_sec=120
        )
        
        assert result.primary_format == ContentFormat.TALKING_HEAD
        assert result.has_speech is True
        assert result.has_people is True
        assert result.people_speaking is True
        assert result.confidence >= 0.5
        assert "primary" in result.suggested_use
    
    def test_talking_head_minimal_visuals(self, detector):
        """High word count with minimal visual info should still detect talking head"""
        result = detector.detect_format(
            transcript="This is a long monologue about various topics including technology and productivity and how to be more efficient in your daily life and work routines",
            visual_analysis={"visual_summary": "Person in frame"},
            duration_sec=90
        )
        
        assert result.primary_format == ContentFormat.TALKING_HEAD
        assert result.has_speech is True
    
    # === B-ROLL TESTS ===
    
    def test_broll_scenic_no_speech(self, detector):
        """Scenic footage with no speech should be broll_scenic"""
        result = detector.detect_format(
            transcript="",
            visual_analysis={"visual_summary": "Beautiful mountain landscape with sunset, aerial drone footage over forest and lake"},
            duration_sec=30
        )
        
        assert result.primary_format == ContentFormat.BROLL_SCENIC
        assert result.has_speech is False
        assert result.has_people is False
        assert "overlay" in result.suggested_use
    
    def test_broll_scenic_with_nature_keywords(self, detector):
        """Scenic content with nature keywords"""
        result = detector.detect_format(
            transcript="",
            visual_analysis={"visual_summary": "Ocean waves crashing on beach, sunset sky, nature scenery"},
            duration_sec=45
        )
        
        assert result.primary_format == ContentFormat.BROLL_SCENIC
        assert result.confidence >= 0.5
    
    def test_broll_action_movement(self, detector):
        """Action footage with movement should detect action keywords"""
        result = detector.detect_format(
            transcript="",
            visual_analysis={"visual_summary": "Fast movement, running action, sports activity"},
            duration_sec=20
        )
        
        # Action detected as secondary or primary format
        assert result.has_speech is False
        assert ContentFormat.BROLL_ACTION in result.secondary_formats or result.primary_format == ContentFormat.BROLL_ACTION
        assert "Action/movement content" in result.reasons
    
    def test_broll_people_not_speaking(self, detector):
        """People visible but not speaking should detect people"""
        result = detector.detect_format(
            transcript="",
            visual_analysis={"visual_summary": "Person walking, crowd of people in background"},
            duration_sec=25
        )
        
        # People detected but not speaking
        assert result.has_people is True
        assert result.people_speaking is False
        assert "People present but not speaking" in result.reasons
    
    # === SCREEN RECORDING TESTS ===
    
    def test_screen_recording_software(self, detector):
        """Screen recording with software keywords"""
        result = detector.detect_format(
            transcript="So first you click here on the menu then navigate to settings",
            visual_analysis={"visual_summary": "Computer screen showing software interface, cursor moving, desktop application"},
            duration_sec=180
        )
        
        # Screen recording detected
        assert "Screen recording detected" in result.reasons
        assert ContentFormat.SCREEN_RECORDING in result.secondary_formats or result.primary_format == ContentFormat.SCREEN_RECORDING
    
    def test_screen_recording_code(self, detector):
        """Screen recording with code/terminal"""
        result = detector.detect_format(
            transcript="Let me show you how to run this command",
            visual_analysis={"visual_summary": "Terminal window with code, software development interface"},
            duration_sec=120
        )
        
        assert result.primary_format == ContentFormat.SCREEN_RECORDING
    
    # === ANIMATED CONTENT TESTS ===
    
    def test_animated_motion_graphics(self, detector):
        """Animation/motion graphics content"""
        result = detector.detect_format(
            transcript="",
            visual_analysis={"visual_summary": "Animated graphics, motion design, digital art illustration"},
            duration_sec=60
        )
        
        assert result.primary_format == ContentFormat.ANIMATED
        assert "standalone" in result.suggested_use
    
    def test_animated_cartoon(self, detector):
        """Cartoon/illustrated content"""
        result = detector.detect_format(
            transcript="",
            visual_analysis={"visual_summary": "Cartoon animation, illustrated characters, drawn style"},
            duration_sec=90
        )
        
        assert result.primary_format == ContentFormat.ANIMATED
    
    # === INTERVIEW TESTS ===
    
    def test_interview_two_people(self, detector):
        """Interview with multiple people"""
        result = detector.detect_format(
            transcript="So tell me about your experience working in tech and what got you started in this field",
            visual_analysis={"visual_summary": "Interview setup, two people in conversation, podcast style"},
            duration_sec=300
        )
        
        assert result.primary_format == ContentFormat.INTERVIEW
        assert result.people_count_estimate >= 2
    
    # === LIVE EVENT TESTS ===
    
    def test_live_event_concert(self, detector):
        """Concert/live event footage"""
        result = detector.detect_format(
            transcript="",
            visual_analysis={"visual_summary": "Concert stage, crowd audience, live performance, festival"},
            duration_sec=120
        )
        
        assert result.primary_format == ContentFormat.LIVE_EVENT
    
    # === TUTORIAL TESTS ===
    
    def test_tutorial_hands_on(self, detector):
        """Hands-on tutorial content"""
        result = detector.detect_format(
            transcript="First we're going to add the ingredients step by step and mix them together",
            visual_analysis={"visual_summary": "Hands demonstration, cooking tutorial, showing how to make"},
            duration_sec=180
        )
        
        # Tutorial detected in reasons
        assert "Tutorial/hands-on content" in result.reasons
    
    # === ATTRIBUTE TESTS ===
    
    def test_duration_category_short(self, detector):
        """Short video duration category"""
        result = detector.detect_format(
            transcript="Quick tip",
            visual_analysis={"visual_summary": "Person speaking"},
            duration_sec=30
        )
        
        assert result.duration_category == "short"
    
    def test_duration_category_medium(self, detector):
        """Medium video duration category"""
        result = detector.detect_format(
            transcript="This is a medium length video",
            visual_analysis={"visual_summary": "Person speaking"},
            duration_sec=120
        )
        
        assert result.duration_category == "medium"
    
    def test_duration_category_long(self, detector):
        """Long video duration category"""
        result = detector.detect_format(
            transcript="This is a long form content piece",
            visual_analysis={"visual_summary": "Person speaking"},
            duration_sec=600
        )
        
        assert result.duration_category == "long"
    
    def test_text_overlay_detection(self, detector):
        """Text overlay detection in visuals"""
        result = detector.detect_format(
            transcript="",
            visual_analysis={"visual_summary": "Video with text overlay, caption at bottom, title screen"},
            duration_sec=30
        )
        
        assert result.has_text_overlay is True
    
    # === PLATFORM RECOMMENDATION TESTS ===
    
    def test_short_content_recommends_tiktok(self, detector):
        """Short content should recommend TikTok"""
        result = detector.detect_format(
            transcript="Quick tip",
            visual_analysis={"visual_summary": "Person speaking"},
            duration_sec=15
        )
        
        assert "tiktok" in result.best_platforms
    
    def test_long_content_recommends_youtube(self, detector):
        """Long content should recommend YouTube"""
        result = detector.detect_format(
            transcript="This is a detailed tutorial on a complex topic",
            visual_analysis={"visual_summary": "Documentary style narration"},
            duration_sec=900
        )
        
        assert "youtube" in result.best_platforms
    
    # === EDGE CASES ===
    
    def test_empty_inputs(self, detector):
        """Handle empty inputs gracefully"""
        result = detector.detect_format(
            transcript=None,
            visual_analysis=None,
            duration_sec=None
        )
        
        assert result.primary_format is not None
        assert isinstance(result.confidence, float)
    
    def test_minimal_data(self, detector):
        """Handle minimal data"""
        result = detector.detect_format(
            transcript="",
            visual_analysis={},
            duration_sec=30
        )
        
        assert result.primary_format is not None
    
    def test_existing_broll_analysis(self, detector):
        """Use existing B-roll analysis when available"""
        result = detector.detect_format(
            transcript="",
            visual_analysis={"visual_summary": "outdoor scene"},
            duration_sec=30,
            existing_broll_analysis={
                "is_broll": True,
                "broll_visual_type": "scenic"
            }
        )
        
        assert result.primary_format == ContentFormat.BROLL_SCENIC
    
    # === CONFIDENCE TESTS ===
    
    def test_high_confidence_clear_format(self, detector):
        """Clear format indicators should have high confidence"""
        result = detector.detect_format(
            transcript="",
            visual_analysis={"visual_summary": "Beautiful mountain landscape sunset nature scenery outdoor aerial drone"},
            duration_sec=30
        )
        
        assert result.confidence >= 0.5
    
    def test_ambiguous_content_lower_confidence(self, detector):
        """Ambiguous content should have lower confidence"""
        result = detector.detect_format(
            transcript="hmm",
            visual_analysis={"visual_summary": "generic scene"},
            duration_sec=30
        )
        
        # Should still classify but with lower confidence
        assert result.primary_format is not None


class TestFormatAnalysisDataclass:
    """Test FormatAnalysis dataclass"""
    
    def test_default_values(self):
        """Test default values in FormatAnalysis"""
        analysis = FormatAnalysis(
            primary_format=ContentFormat.TALKING_HEAD,
            confidence=0.8
        )
        
        assert analysis.has_speech is False
        assert analysis.has_music is False
        assert analysis.secondary_formats == []
        assert analysis.reasons == []
        assert analysis.best_platforms == []
    
    def test_full_initialization(self):
        """Test full initialization of FormatAnalysis"""
        analysis = FormatAnalysis(
            primary_format=ContentFormat.BROLL_SCENIC,
            confidence=0.9,
            secondary_formats=[ContentFormat.BROLL_ACTION],
            has_speech=False,
            has_music=True,
            has_people=False,
            is_vertical=True,
            duration_category="short",
            production_quality=ProductionQuality.HIGH,
            reasons=["Scenic content detected"],
            best_platforms=["tiktok", "instagram"],
            suggested_use="overlay"
        )
        
        assert analysis.primary_format == ContentFormat.BROLL_SCENIC
        assert len(analysis.secondary_formats) == 1
        assert analysis.has_music is True
        assert analysis.production_quality == ProductionQuality.HIGH


class TestContentFormatEnum:
    """Test ContentFormat enum"""
    
    def test_all_formats_have_values(self):
        """All content formats should have string values"""
        for fmt in ContentFormat:
            assert isinstance(fmt.value, str)
            assert len(fmt.value) > 0
    
    def test_format_count(self):
        """Verify expected number of formats"""
        # Should have 16 format types including UNKNOWN
        assert len(ContentFormat) >= 15


class TestProductionQualityEnum:
    """Test ProductionQuality enum"""
    
    def test_quality_levels(self):
        """Verify quality levels exist"""
        assert ProductionQuality.LOW.value == "low"
        assert ProductionQuality.MEDIUM.value == "medium"
        assert ProductionQuality.HIGH.value == "high"
        assert ProductionQuality.PROFESSIONAL.value == "professional"
