"""
Content Analysis Service
Analyzes transcripts using GPT-4 to identify viral patterns, hooks, tone, and key moments
"""
import os
import json
from typing import Dict, List, Optional
from openai import OpenAI
from loguru import logger


class ContentAnalyzer:
    """Analyze video content using GPT-4"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize analyzer
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        self.client = OpenAI(api_key=self.api_key)
    
    def analyze_transcript(self, transcript: str, video_metadata: dict = None) -> dict:
        """
        Analyze transcript for viral patterns using GPT-4
        
        Args:
            transcript: Full transcript text
            video_metadata: Optional metadata (duration, title, etc.)
            
        Returns:
            Analysis results with hooks, tone, topics, key moments, and viral score
        """
        logger.info(f"Analyzing transcript ({len(transcript)} chars) with GPT-4")
        
        # Build analysis prompt
        prompt = self._build_analysis_prompt(transcript, video_metadata)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert content analyst specializing in viral video patterns and social media engagement. Analyze content for hooks, emotional triggers, pacing, and viral potential."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3  # Lower for more consistent analysis
            )
            
            # Parse JSON response
            analysis = json.loads(response.choices[0].message.content)
            
            logger.success(f"Content analysis complete. Viral score: {analysis.get('viral_score', 'N/A')}")
            
            return self._normalize_analysis(analysis)
            
        except Exception as e:
            logger.error(f"GPT-4 analysis error: {e}")
            raise RuntimeError(f"Content analysis failed: {e}")
    
    def _build_analysis_prompt(self, transcript: str, metadata: dict = None) -> str:
        """Build GPT-4 analysis prompt with comprehensive extraction"""
        
        # Calculate estimated duration for scene structure
        word_count = len(transcript.split())
        estimated_duration = (word_count / 150) * 60  # ~150 words per minute
        
        prompt = """Analyze this video transcript for viral potential, content patterns, and creative brief generation.

TRANSCRIPT:
""" + transcript + """

Provide COMPREHENSIVE analysis in JSON format with the following structure:
{
  "topics": [list of 3-5 main topics/themes],
  "hooks": [list of 2-4 attention-grabbing phrases or hooks],
  "detected_hook": "the single best/strongest hook phrase from the content",
  "tone": "overall tone (energetic/calm/educational/entertaining/inspirational/motivational/humorous)",
  "pacing": "delivery speed (fast/medium/slow)",
  "key_moments": {
    "0-3": "hook/opening description",
    "middle": "main content description",
    "end": "closing/CTA description"
  },
  
  "pain_points": [
    "specific problem or frustration the content addresses",
    "another pain point mentioned or implied"
  ],
  
  "emotional_drivers": [
    "primary emotional motivation (e.g., fear of missing out, desire for transformation)",
    "secondary emotional element"
  ],
  
  "emotional_journey": {
    "opening_emotion": "emotion evoked at start (curiosity/shock/relatability)",
    "peak_emotion": "strongest emotional moment (excitement/revelation/empathy)",
    "closing_emotion": "ending emotional state (inspiration/urgency/satisfaction)"
  },
  
  "call_to_action": {
    "type": "follow/subscribe/purchase/dm/link/comment/share/none",
    "text": "exact CTA text if present, or suggested CTA if none",
    "strength": "strong/medium/weak/none",
    "timestamp_hint": "beginning/middle/end"
  },
  
  "scene_structure": [
    {
      "start_sec": 0,
      "end_sec": 3,
      "role": "hook",
      "summary": "attention-grabbing opening",
      "emotion": "curiosity"
    },
    {
      "start_sec": 3,
      "end_sec": 15,
      "role": "problem",
      "summary": "establishes the pain point",
      "emotion": "relatability"
    },
    {
      "start_sec": 15,
      "end_sec": 25,
      "role": "solution",
      "summary": "presents the answer/method",
      "emotion": "hope"
    },
    {
      "start_sec": 25,
      "end_sec": 30,
      "role": "cta",
      "summary": "call to action",
      "emotion": "urgency"
    }
  ],
  
  "viral_score": <0-100 score for viral potential>,
  "viral_analysis": "explanation of viral potential",
  "improvement_suggestions": [2-3 actionable suggestions to increase engagement],
  
  "content_type": "tutorial/storytime/review/transformation/lifestyle/comedy/educational/promotional",
  
  "target_audience": {
    "demographic": "who this appeals to",
    "interests": ["relevant interests"],
    "awareness_level": "problem-aware/solution-aware/product-aware"
  },
  
  "music_suggestion": {
    "mood": "mood of the music (e.g., upbeat, suspenseful, chill, inspiring)",
    "genre": "genre (e.g., lo-fi, cinematic, hip-hop, electronic, acoustic)",
    "tempo": "fast/medium/slow",
    "energy": "high/medium/low",
    "reasoning": "why this music fits the content"
  }
}

IMPORTANT EXTRACTION GUIDELINES:
1. PAIN POINTS: Identify specific problems, frustrations, or challenges mentioned or implied
2. EMOTIONAL DRIVERS: What motivates the viewer - fear, desire, curiosity, belonging, transformation
3. CTA: Even if no explicit CTA, suggest what would work best for this content
4. SCENE STRUCTURE: Break down the content flow - estimate timestamps based on ~150 words/minute
5. Focus on actionable insights for recreating similar content

Focus on identifying:
- Strong opening hooks (first 3 seconds)
- Emotional resonance and relatability
- Pattern interrupts and attention retention
- Social proof elements
- Scarcity/urgency triggers
- Curiosity gaps
- Transformation promises
- Suitable background music to enhance the mood
"""
        
        if metadata:
            prompt += f"\n\nVIDEO METADATA: {json.dumps(metadata)}"
            if metadata.get("duration"):
                prompt += f"\nNote: Actual video duration is {metadata['duration']} seconds. Adjust scene_structure timestamps accordingly."
        
        return prompt
    
    def _normalize_analysis(self, raw_analysis: dict) -> dict:
        """Normalize GPT-4 response to match database schema"""
        
        # Get score and ensure it's on 0-100 scale
        raw_score = float(raw_analysis.get("viral_score", raw_analysis.get("pre_social_score", 50)))
        if raw_score <= 10:
            raw_score = raw_score * 10  # Convert 0-10 scale to 0-100
        
        # Extract detected_hook - use first hook if not explicitly provided
        detected_hook = raw_analysis.get("detected_hook")
        if not detected_hook and raw_analysis.get("hooks"):
            detected_hook = raw_analysis["hooks"][0]
        
        # Normalize CTA - handle both old format (list) and new format (object)
        cta_data = raw_analysis.get("call_to_action", {})
        if isinstance(cta_data, list):
            # Old format - convert to new
            cta_data = {
                "type": "none" if not cta_data else "follow",
                "text": cta_data[0] if cta_data else "",
                "strength": "medium" if cta_data else "none"
            }
        
        return {
            # Core fields
            "topics": raw_analysis.get("topics", []),
            "hooks": raw_analysis.get("hooks", []),
            "detected_hook": detected_hook,
            "tone": raw_analysis.get("tone", "unknown"),
            "pacing": raw_analysis.get("pacing", "medium"),
            "key_moments": raw_analysis.get("key_moments", {}),
            "pre_social_score": raw_score,
            
            # NEW: Pain points and emotional drivers for creative briefs
            "pain_points": raw_analysis.get("pain_points", []),
            "emotional_drivers": raw_analysis.get("emotional_drivers", []),
            "emotional_journey": raw_analysis.get("emotional_journey", {}),
            
            # NEW: Structured CTA extraction
            "call_to_action": cta_data,
            
            # NEW: Scene structure for video generation
            "scene_structure": raw_analysis.get("scene_structure", []),
            
            # NEW: Content classification
            "content_type": raw_analysis.get("content_type", "general"),
            "target_audience": raw_analysis.get("target_audience", {}),
            
            # Existing fields (backward compatible)
            "emotional_triggers": raw_analysis.get("emotional_triggers", raw_analysis.get("emotional_drivers", [])),
            "calls_to_action": [cta_data.get("text")] if cta_data.get("text") else [],
            "viral_analysis": raw_analysis.get("viral_analysis", ""),
            "suggestions": raw_analysis.get("improvement_suggestions", []),
            "music_suggestion": raw_analysis.get("music_suggestion", {})
        }
    
    def analyze_from_visuals(self, visual_summary: str, video_metadata: dict = None) -> dict:
        """
        Analyze video content based on visual analysis when no transcript is available.
        
        Args:
            visual_summary: Description of visual content from frame analysis
            video_metadata: Optional metadata (duration, title, etc.)
            
        Returns:
            Analysis results with topics, tone, and engagement predictions
        """
        logger.info(f"[ContentAnalyzer] Analyzing from visuals only ({len(visual_summary)} chars)")
        
        prompt = f"""Analyze this video based on its visual content (no audio/transcript available).

VISUAL DESCRIPTION:
{visual_summary}

Based on the visual content, provide analysis in JSON format:
{{
  "topics": [list of 3-5 topics/themes visible in the video],
  "hooks": [potential attention-grabbing visual elements],
  "tone": "visual tone (dynamic/calm/educational/entertaining/aesthetic)",
  "pacing": "visual pacing estimate (fast/medium/slow)",
  "key_moments": {{}},
  "emotional_triggers": [visual emotional elements],
  "calls_to_action": [],
  "viral_score": <0-100 score based on visual appeal>,
  "viral_analysis": "explanation of visual viral potential",
  "improvement_suggestions": [2-3 suggestions],
  "music_suggestion": {{
      "mood": "suggested music mood based on visuals",
      "genre": "suggested genre",
      "tempo": "fast/medium/slow",
      "reasoning": "why this fits the visuals"
  }},
  "analysis_note": "Analysis based on visual content only - no audio transcript available"
}}

Focus on:
- Visual appeal and composition
- Colors and lighting
- Subject matter engagement potential
- Platform suitability (TikTok, Instagram, YouTube)
"""
        
        if video_metadata:
            prompt += f"\nVIDEO METADATA: {json.dumps(video_metadata)}"
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert visual content analyst. Analyze video content based on visual elements when audio is unavailable."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            analysis = json.loads(response.choices[0].message.content)
            logger.success(f"[ContentAnalyzer] Visual analysis complete. Score: {analysis.get('viral_score', 'N/A')}")
            
            # Normalize and ensure pre_social_score is on 0-100 scale
            result = self._normalize_analysis(analysis)
            if result.get("pre_social_score", 0) <= 10:
                result["pre_social_score"] = result["pre_social_score"] * 10
            result["analysis_note"] = "Analysis based on visual content only - no audio transcript"
            
            return result
            
        except Exception as e:
            logger.error(f"[ContentAnalyzer] Visual analysis error: {e}")
            # Return minimal fallback
            return {
                "topics": ["visual content"],
                "hooks": [],
                "tone": "visual",
                "pacing": "unknown",
                "pre_social_score": 50,
                "analysis_note": f"Visual analysis failed: {str(e)}"
            }
