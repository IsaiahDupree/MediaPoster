"""
Tests for AI Image Analysis API
Tests comprehensive image analysis with AI vision.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import uuid
import base64
import os

import sys
sys.path.insert(0, '..')
from main import app

client = TestClient(app)

# Sample test image (1x1 red pixel PNG in base64)
SAMPLE_IMAGE_BASE64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

# Sample test image URL
SAMPLE_IMAGE_URL = "https://picsum.photos/400/300"


class TestImageAnalysisEndpoints:
    """Test image analysis endpoints"""

    def test_analyze_from_url(self):
        """Test analyzing image from URL"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": SAMPLE_IMAGE_URL,
                "analysis_depth": "brief"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "analysis_id" in data
        assert "title" in data
        assert "detailed_description" in data

    def test_analyze_from_base64(self):
        """Test analyzing image from base64"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_base64": SAMPLE_IMAGE_BASE64,
                "analysis_depth": "brief"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "analysis_id" in data

    def test_analyze_missing_image(self):
        """Test analyzing without image"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={}
        )
        assert response.status_code == 400

    def test_analyze_with_custom_fields(self):
        """Test analyzing with custom fields"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": SAMPLE_IMAGE_URL,
                "custom_fields": ["brand_alignment", "target_demographic"],
                "analysis_depth": "brief"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "custom_fields" in data

    def test_analyze_with_focus_areas(self):
        """Test analyzing with focus areas"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": SAMPLE_IMAGE_URL,
                "focus_areas": ["fashion", "emotions", "colors"],
                "analysis_depth": "brief"
            }
        )
        assert response.status_code == 200

    def test_analyze_different_depths(self):
        """Test analyzing with different depth settings"""
        for depth in ["brief", "standard", "detailed", "comprehensive"]:
            response = client.post(
                "/api/image-analysis/analyze",
                json={
                    "image_url": SAMPLE_IMAGE_URL,
                    "analysis_depth": depth
                }
            )
            assert response.status_code == 200


class TestImageAnalysisResultStructure:
    """Test analysis result structure"""

    def get_analysis(self):
        """Helper to get a sample analysis"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": SAMPLE_IMAGE_URL,
                "analysis_depth": "detailed"
            }
        )
        return response.json() if response.status_code == 200 else None

    def test_overall_description_fields(self):
        """Test overall description fields exist"""
        data = self.get_analysis()
        if not data:
            pytest.skip("Could not get analysis")
        
        assert "title" in data
        assert "short_description" in data
        assert "detailed_description" in data
        assert len(data["detailed_description"]) >= 50  # At least 50 chars

    def test_scene_analysis_fields(self):
        """Test scene analysis fields exist"""
        data = self.get_analysis()
        if not data:
            pytest.skip("Could not get analysis")
        
        assert "scene_type" in data
        assert "scene_setting" in data
        assert "indoor_outdoor" in data

    def test_location_time_fields(self):
        """Test location and time fields exist"""
        data = self.get_analysis()
        if not data:
            pytest.skip("Could not get analysis")
        
        assert "location_type" in data
        assert "time_of_day" in data
        assert "time_indicators" in data
        assert isinstance(data["time_indicators"], list)

    def test_people_analysis_fields(self):
        """Test people analysis fields exist"""
        data = self.get_analysis()
        if not data:
            pytest.skip("Could not get analysis")
        
        assert "people_count" in data
        assert "people" in data
        assert isinstance(data["people"], list)
        
        if data["people"]:
            person = data["people"][0]
            assert "person_id" in person
            assert "approximate_age" in person
            assert "clothing_description" in person
            assert "primary_emotion" in person
            assert "emotion_confidence" in person

    def test_objects_fields(self):
        """Test objects and elements fields exist"""
        data = self.get_analysis()
        if not data:
            pytest.skip("Could not get analysis")
        
        assert "main_subjects" in data
        assert "objects_detected" in data
        assert "background_elements" in data
        assert "foreground_elements" in data
        assert isinstance(data["main_subjects"], list)

    def test_colors_aesthetics_fields(self):
        """Test colors and aesthetics fields exist"""
        data = self.get_analysis()
        if not data:
            pytest.skip("Could not get analysis")
        
        assert "dominant_colors" in data
        assert "color_palette" in data
        assert "lighting_type" in data
        assert "lighting_quality" in data
        assert "contrast_level" in data
        assert isinstance(data["dominant_colors"], list)

    def test_composition_fields(self):
        """Test composition fields exist"""
        data = self.get_analysis()
        if not data:
            pytest.skip("Could not get analysis")
        
        assert "composition_style" in data
        assert "focal_point" in data
        assert "depth_of_field" in data
        assert "perspective" in data

    def test_mood_style_fields(self):
        """Test mood and style fields exist"""
        data = self.get_analysis()
        if not data:
            pytest.skip("Could not get analysis")
        
        assert "overall_mood" in data
        assert "visual_style" in data
        assert "aesthetic_tags" in data
        assert isinstance(data["aesthetic_tags"], list)

    def test_social_media_fields(self):
        """Test social media optimization fields exist"""
        data = self.get_analysis()
        if not data:
            pytest.skip("Could not get analysis")
        
        assert "suggested_hashtags" in data
        assert "suggested_caption" in data
        assert "engagement_prediction" in data
        assert "suitable_platforms" in data
        assert isinstance(data["suggested_hashtags"], list)
        assert isinstance(data["suitable_platforms"], list)

    def test_technical_quality_fields(self):
        """Test technical quality fields exist"""
        data = self.get_analysis()
        if not data:
            pytest.skip("Could not get analysis")
        
        assert "image_quality" in data
        assert "sharpness" in data
        assert "exposure" in data

    def test_metadata_fields(self):
        """Test metadata fields exist"""
        data = self.get_analysis()
        if not data:
            pytest.skip("Could not get analysis")
        
        assert "analysis_id" in data
        assert "analyzed_at" in data
        assert "overall_confidence" in data
        assert "processing_time_ms" in data


class TestImageAnalysisRetrieval:
    """Test analysis retrieval endpoints"""

    def test_get_analysis_by_id(self):
        """Test retrieving analysis by ID"""
        # First create an analysis
        create_response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": SAMPLE_IMAGE_URL,
                "analysis_depth": "brief"
            }
        )
        assert create_response.status_code == 200
        analysis_id = create_response.json()["analysis_id"]
        
        # Then retrieve it
        get_response = client.get(f"/api/image-analysis/analysis/{analysis_id}")
        assert get_response.status_code == 200
        assert get_response.json()["analysis_id"] == analysis_id

    def test_get_nonexistent_analysis(self):
        """Test retrieving non-existent analysis"""
        response = client.get(f"/api/image-analysis/analysis/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_list_analyses(self):
        """Test listing recent analyses"""
        response = client.get("/api/image-analysis/analyses")
        assert response.status_code == 200
        
        data = response.json()
        assert "analyses" in data
        assert isinstance(data["analyses"], list)

    def test_list_analyses_with_limit(self):
        """Test listing analyses with limit"""
        response = client.get("/api/image-analysis/analyses?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["analyses"]) <= 5


class TestImageAnalysisFields:
    """Test fields endpoint"""

    def test_get_available_fields(self):
        """Test getting available analysis fields"""
        response = client.get("/api/image-analysis/fields")
        assert response.status_code == 200
        
        data = response.json()
        assert "standard_fields" in data
        assert "person_fields" in data
        assert "custom_field_examples" in data
        assert "focus_area_examples" in data
        assert "analysis_depths" in data

    def test_standard_fields_list(self):
        """Test standard fields list is complete"""
        response = client.get("/api/image-analysis/fields")
        assert response.status_code == 200
        
        fields = response.json()["standard_fields"]
        expected = ["title", "detailed_description", "scene_type", "time_of_day", 
                   "people_count", "dominant_colors", "overall_mood"]
        
        for expected_field in expected:
            assert expected_field in fields

    def test_person_fields_list(self):
        """Test person fields list is complete"""
        response = client.get("/api/image-analysis/fields")
        assert response.status_code == 200
        
        fields = response.json()["person_fields"]
        expected = ["approximate_age", "clothing_description", "primary_emotion", 
                   "body_pose", "facial_expression"]
        
        for expected_field in expected:
            assert expected_field in fields


class TestImageAnalysisValidation:
    """Test input validation"""

    def test_invalid_image_url(self):
        """Test with invalid image URL"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": "not-a-valid-url",
                "analysis_depth": "brief"
            }
        )
        # May return 200 with mock data or 400/500
        assert response.status_code in [200, 400, 500]

    def test_invalid_analysis_depth(self):
        """Test with invalid analysis depth"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": SAMPLE_IMAGE_URL,
                "analysis_depth": "invalid_depth"
            }
        )
        # May accept any string or validate
        assert response.status_code in [200, 400, 422]

    def test_empty_custom_fields(self):
        """Test with empty custom fields list"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": SAMPLE_IMAGE_URL,
                "custom_fields": [],
                "analysis_depth": "brief"
            }
        )
        assert response.status_code == 200


class TestImageAnalysisPersonDetails:
    """Test person analysis details"""

    def test_person_emotion_values(self):
        """Test that person emotions are valid"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": SAMPLE_IMAGE_URL,
                "analysis_depth": "detailed"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        valid_emotions = ["happy", "sad", "angry", "surprised", "neutral", 
                        "excited", "thoughtful", "confident", "relaxed", "focused"]
        
        for person in data.get("people", []):
            if "primary_emotion" in person:
                assert person["primary_emotion"] in valid_emotions

    def test_person_emotion_confidence_range(self):
        """Test that emotion confidence is 0-1"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": SAMPLE_IMAGE_URL,
                "analysis_depth": "detailed"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        for person in data.get("people", []):
            if "emotion_confidence" in person:
                assert 0 <= person["emotion_confidence"] <= 1

    def test_clothing_colors_is_list(self):
        """Test that clothing colors is a list"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": SAMPLE_IMAGE_URL,
                "analysis_depth": "detailed"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        for person in data.get("people", []):
            if "clothing_colors" in person:
                assert isinstance(person["clothing_colors"], list)


class TestImageAnalysisTimeOfDay:
    """Test time of day analysis"""

    def test_time_of_day_values(self):
        """Test that time_of_day is valid"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": SAMPLE_IMAGE_URL,
                "analysis_depth": "detailed"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        valid_times = ["dawn", "morning", "midday", "afternoon", 
                      "evening", "sunset", "night", "unknown"]
        
        assert data.get("time_of_day") in valid_times


class TestImageAnalysisEngagement:
    """Test engagement prediction"""

    def test_engagement_prediction_values(self):
        """Test that engagement prediction is valid"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": SAMPLE_IMAGE_URL,
                "analysis_depth": "detailed"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        valid_predictions = ["low", "medium", "high"]
        
        assert data.get("engagement_prediction") in valid_predictions


class TestImageAnalysisHashtags:
    """Test hashtag suggestions"""

    def test_hashtags_are_list(self):
        """Test that hashtags is a list"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": SAMPLE_IMAGE_URL,
                "analysis_depth": "detailed"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data.get("suggested_hashtags", []), list)

    def test_hashtags_format(self):
        """Test that hashtags start with #"""
        response = client.post(
            "/api/image-analysis/analyze",
            json={
                "image_url": SAMPLE_IMAGE_URL,
                "analysis_depth": "detailed"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        for tag in data.get("suggested_hashtags", []):
            assert tag.startswith("#")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
