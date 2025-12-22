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
        """Build GPT-4 analysis prompt"""
        
        prompt = """Analyze this video transcript for viral potential and content patterns.

TRANSCRIPT:
""" + transcript + """

Provide analysis in JSON format with the following structure:
{
  "topics": [list of 3-5 main topics/themes],
  "hooks": [list of 2-4 attention-grabbing phrases or hooks],
  "tone": "overall tone (energetic/calm/educational/entertaining/inspirational)",
  "pacing": "delivery speed (fast/medium/slow)",
  "key_moments": {
    "timestamp": "description of important moment"
  },
  "emotional_triggers": [list of emotional elements used],
  "calls_to_action": [any CTAs mentioned],
  "viral_score": <0-100 score for viral potential>,
  "viral_analysis": "explanation of viral potential",
  "improvement_suggestions": [2-3 suggestions to increase engagement],
  "music_suggestion": {
      "mood": "mood of the music (e.g., upbeat, suspenseful, chill)",
      "genre": "genre (e.g., lo-fi, cinematic, hip-hop)",
      "tempo": "fast/medium/slow",
      "reasoning": "why this music fits"
  }
}

Focus on identifying:
- Strong opening hooks
- Emotional resonance
- Pattern interrupts
- Social proof elements
- Scarcity/urgency
- Curiosity gaps
- Relatability
- Suitable background music to enhance the mood
"""
        
        if metadata:
            prompt += "\nVIDEO METADATA: " + json.dumps(metadata)
        
        return prompt
    
    def _normalize_analysis(self, raw_analysis: dict) -> dict:
        """Normalize GPT-4 response to match database schema"""
        
        # Get score and ensure it's on 0-100 scale
        raw_score = float(raw_analysis.get("viral_score", raw_analysis.get("pre_social_score", 50)))
        if raw_score <= 10:
            raw_score = raw_score * 10  # Convert 0-10 scale to 0-100
        
        return {
            "topics": raw_analysis.get("topics", []),
            "hooks": raw_analysis.get("hooks", []),
            "tone": raw_analysis.get("tone", "unknown"),
            "pacing": raw_analysis.get("pacing", "medium"),
            "key_moments": raw_analysis.get("key_moments", {}),
            "pre_social_score": raw_score,
            "emotional_triggers": raw_analysis.get("emotional_triggers", []),
            "calls_to_action": raw_analysis.get("calls_to_action", []),
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
