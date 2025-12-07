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
  "viral_score": <0-10 score for viral potential>,
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
        
        return {
            "topics": raw_analysis.get("topics", []),
            "hooks": raw_analysis.get("hooks", []),
            "tone": raw_analysis.get("tone", "unknown"),
            "pacing": raw_analysis.get("pacing", "medium"),
            "key_moments": raw_analysis.get("key_moments", {}),
            "pre_social_score": float(raw_analysis.get("viral_score", 5.0)),
            "emotional_triggers": raw_analysis.get("emotional_triggers", []),
            "calls_to_action": raw_analysis.get("calls_to_action", []),
            "viral_analysis": raw_analysis.get("viral_analysis", ""),
            "suggestions": raw_analysis.get("improvement_suggestions", []),
            "music_suggestion": raw_analysis.get("music_suggestion", {})
        }
