"""
Unit tests for Story IR generation.

Tests:
- Trend + Brief → Story IR conversion
- Beat generation
- Duration estimation
- Script classification
"""

import pytest
from services.video_generation.types import (
    TrendItemV1,
    ContentBriefV1,
    StoryIRV1,
    ContentConstraints,
)
from services.video_generation.story_ir import make_story_ir
from services.video_generation.script_classifier import (
    classify_sentence,
    split_sentences,
    classify_script,
    script_to_outline,
    script_to_story_ir,
)
from services.video_generation.domain_dict import (
    classify_sentence_smart,
    get_domain_score,
    extract_domain_keywords,
    DEFAULT_DOMAIN_DICT,
)


class TestStoryIRGeneration:
    """Tests for Story IR generation from trend + brief."""
    
    @pytest.fixture
    def sample_trend(self) -> TrendItemV1:
        return TrendItemV1(
            id="trend_001",
            platform="tiktok",
            topic="Motion Canvas automation",
            angle_candidates=["practical walkthrough", "before/after comparison"],
        )
    
    @pytest.fixture
    def sample_brief(self) -> ContentBriefV1:
        return ContentBriefV1(
            goal="educate",
            audience="developers",
            promise="automate your SFX in Motion Canvas",
            key_points=[
                "Set up the SFX manifest",
                "Create macro policies",
                "Generate audio bus",
                "Integrate with render pipeline",
            ],
            constraints=ContentConstraints(
                max_seconds=58,
            ),
        )
    
    def test_make_story_ir_creates_valid_structure(self, sample_trend, sample_brief):
        """Story IR should have valid structure."""
        ir = make_story_ir(sample_trend, sample_brief, fps=30, aspect="9:16")
        
        assert ir is not None
        assert hasattr(ir, 'meta')
        assert hasattr(ir, 'beats')
        assert len(ir.beats) > 0
    
    def test_make_story_ir_has_hook_beat(self, sample_trend, sample_brief):
        """Story IR should have a HOOK beat."""
        ir = make_story_ir(sample_trend, sample_brief)
        
        beat_types = [b.type.value for b in ir.beats]
        assert "HOOK" in beat_types
    
    def test_make_story_ir_has_step_beats(self, sample_trend, sample_brief):
        """Story IR should have STEP beats for each key point."""
        ir = make_story_ir(sample_trend, sample_brief)
        
        step_beats = [b for b in ir.beats if b.type.value == "STEP"]
        assert len(step_beats) >= len(sample_brief.key_points)
    
    def test_make_story_ir_respects_fps(self, sample_trend, sample_brief):
        """Story IR should use specified FPS."""
        ir = make_story_ir(sample_trend, sample_brief, fps=60)
        
        assert ir.meta.fps == 60
    
    def test_make_story_ir_respects_aspect(self, sample_trend, sample_brief):
        """Story IR should use specified aspect ratio."""
        ir = make_story_ir(sample_trend, sample_brief, aspect="16:9")
        
        assert ir.meta.aspect == "16:9"
    
    def test_beats_have_narration(self, sample_trend, sample_brief):
        """All beats should have narration text."""
        ir = make_story_ir(sample_trend, sample_brief)
        
        for beat in ir.beats:
            assert beat.narration is not None
            assert len(beat.narration) > 0
    
    def test_beats_have_positive_duration(self, sample_trend, sample_brief):
        """All beats should have positive duration."""
        ir = make_story_ir(sample_trend, sample_brief)
        
        for beat in ir.beats:
            assert beat.duration_s > 0


class TestScriptClassification:
    """Tests for script → outline conversion."""
    
    def test_split_sentences_basic(self):
        """Should split text into sentences."""
        text = "This is the first sentence with enough words. This is the second sentence with content! This is the third sentence here?"
        sentences = split_sentences(text)
        
        assert len(sentences) == 3
    
    def test_split_sentences_preserves_content(self):
        """Should preserve sentence content."""
        text = "Hello world this is a longer sentence. Goodbye world this is another sentence."
        sentences = split_sentences(text)
        
        assert "Hello world" in sentences[0]
        assert "Goodbye world" in sentences[1]
    
    def test_classify_sentence_hook(self):
        """Should classify hook sentences."""
        hook = "I tried to automate SFX in Motion Canvas"
        result = classify_sentence(hook)
        
        assert result == "HOOK"
    
    def test_classify_sentence_problem(self):
        """Should classify problem sentences."""
        problem = "The problem is timing gets messy"
        result = classify_sentence(problem)
        
        assert result == "PROBLEM"
    
    def test_classify_sentence_reveal(self):
        """Should classify reveal sentences."""
        reveal = "Here's the fix: use a single audio bus"
        result = classify_sentence(reveal)
        
        assert result == "REVEAL"
    
    def test_classify_sentence_cta(self):
        """Should classify CTA sentences."""
        cta = "Comment TECH for the template"
        result = classify_sentence(cta)
        
        assert result == "CTA"
    
    def test_classify_sentence_code(self):
        """Should classify code sentences."""
        code = "pnpm run build"
        result = classify_sentence(code)
        
        assert result == "CODE"
    
    def test_classify_sentence_error(self):
        """Should classify error sentences."""
        error = "It crashed with a timeout error"
        result = classify_sentence(error)
        
        assert result == "ERROR"
    
    def test_classify_sentence_success(self):
        """Should classify success sentences."""
        success = "Now it works perfectly"
        result = classify_sentence(success)
        
        assert result == "SUCCESS"
    
    def test_classify_script_returns_buckets(self):
        """Should return classified buckets."""
        script = """
        I tried to automate SFX.
        The problem was timing.
        Here's the fix.
        Comment for template.
        """
        
        buckets = classify_script(script)
        
        assert "HOOK" in buckets
        assert "PROBLEM" in buckets
        assert "REVEAL" in buckets
        assert "CTA" in buckets
    
    def test_script_to_outline_creates_lines(self):
        """Should create outline lines."""
        script = """
        I tried to automate SFX in Motion Canvas.
        The problem is timing gets messy.
        Here's the fix: one audio bus.
        Comment TECH for template.
        """
        
        outline = script_to_outline(script)
        
        # script_to_outline returns a string, not a list
        assert len(outline) > 0
        assert "HOOK" in outline
    
    def test_script_to_story_ir_creates_ir(self):
        """Should create Story IR from script."""
        script = """
        I tried to automate SFX in Motion Canvas.
        The problem is timing gets messy.
        Here's the fix: one audio bus.
        Now renders are locked.
        Comment TECH for template.
        """
        
        ir = script_to_story_ir(script, title="Test Video")
        
        assert ir is not None
        assert "meta" in ir
        assert "beats" in ir
        assert len(ir["beats"]) > 0


class TestDomainDictClassification:
    """Tests for smart classification with domain dictionary."""
    
    def test_classify_sentence_smart_code(self):
        """Should classify code with domain dict."""
        code = "pnpm run mc:hybrid:final"
        result = classify_sentence_smart(code)
        
        assert result == "CODE"
    
    def test_classify_sentence_smart_reveal(self):
        """Should classify reveal with domain dict."""
        reveal = "Here's the fix for the timing issue"
        result = classify_sentence_smart(reveal)
        
        assert result == "REVEAL"
    
    def test_get_domain_score_tech_content(self):
        """Should score tech content higher."""
        tech_text = "Motion Canvas render timeline with ffmpeg audio bus"
        generic_text = "The weather is nice today"
        
        tech_score = get_domain_score(tech_text)
        generic_score = get_domain_score(generic_text)
        
        assert tech_score > generic_score
    
    def test_extract_domain_keywords(self):
        """Should extract domain keywords."""
        text = "Motion Canvas automation with ffmpeg and supabase"
        keywords = extract_domain_keywords(text)
        
        assert len(keywords) > 0
        # Should include some of these
        keyword_set = set(k.lower() for k in keywords)
        assert any(k in keyword_set for k in ["motion canvas", "ffmpeg", "supabase"])
    
    def test_domain_dict_has_domains(self):
        """Default domain dict should have domains."""
        assert len(DEFAULT_DOMAIN_DICT.domains) > 0
    
    def test_domain_dict_has_signals(self):
        """Default domain dict should have signals."""
        assert len(DEFAULT_DOMAIN_DICT.signals.reveal_phrases) > 0
        assert len(DEFAULT_DOMAIN_DICT.signals.cta_phrases) > 0
