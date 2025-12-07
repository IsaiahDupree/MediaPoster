"""
Psychology Tagging Service
Analyzes transcripts and applies FATE/AIDA framework tags
Uses GPT-4 to classify segments and tag psychology patterns
"""
import logging
from typing import Dict, List, Optional, Any
import json
from openai import OpenAI
from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PsychologyTagger:
    """Tags content with psychology frameworks (FATE, AIDA)"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize psychology tagger
        
        Args:
            api_key: OpenAI API key (defaults to settings.OPENAI_API_KEY)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        
        if not self.client:
            logger.warning("OpenAI API key not configured - psychology tagging disabled")
    
    def is_enabled(self) -> bool:
        """Check if psychology tagging is enabled"""
        return self.client is not None
    
    def classify_segments(
        self,
        transcript_text: str,
        duration_s: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Classify video transcript into segments (hook, context, body, CTA, payoff)
        
        Args:
            transcript_text: Full transcript text
            duration_s: Video duration in seconds (optional)
            
        Returns:
            Segment classification with timestamps
        """
        if not self.is_enabled():
            return {"error": "Psychology tagging not enabled"}
        
        try:
            prompt = f"""Analyze this video transcript and identify the key segments.
Return a JSON array of segments with:
- segment_type: "hook" | "context" | "body" | "cta" | "payoff"
- start_pct: estimated start position as 0-1 percentage of video
- end_pct: estimated end position as 0-1 percentage
- summary: brief description of this segment
- key_phrases: important phrases from this segment

Transcript:
{transcript_text}

Return only valid JSON, no other text."""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing viral video structure. You understand hooks, value delivery, CTAs, and payoff moments."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON
            if content.startswith('['):
                segments = json.loads(content)
                
                # Convert percentages to seconds if duration provided
                if duration_s:
                    for seg in segments:
                        seg["start_s"] = seg["start_pct"] * duration_s
                        seg["end_s"] = seg["end_pct"] * duration_s
                
                return {
                    "segments": segments,
                    "total_segments": len(segments)
                }
            else:
                return {"raw_response": content}
        
        except Exception as e:
            logger.error(f"Error classifying segments: {e}")
            return {"error": str(e)}
    
    def tag_fate_framework(
        self,
        segment_text: str,
        segment_type: str
    ) -> Dict[str, Any]:
        """
        Tag segment with FATE framework (Focus, Authority, Tribe, Emotion)
        
        Args:
            segment_text: Text of the segment
            segment_type: Type of segment (hook, context, body, cta, payoff)
            
        Returns:
            FATE tags
        """
        if not self.is_enabled():
            return {}
        
        try:
            prompt = f"""Analyze this {segment_type} segment using the FATE framework.
Return JSON with:
{{
  "focus": "specific problem or audience targeted (or empty string)",
  "authority_signal": "credentials, proof, experience shown (or empty string)",
  "tribe_marker": "identity call, shared language, in-group signal (or empty string)",
  "emotion": "primary emotion" ("relief" | "excitement" | "curiosity" | "FOMO" | "frustration" | "hope")
}}

Segment text:
{segment_text}

Return only valid JSON."""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing psychology and persuasion in content marketing."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            
            if content.startswith('{'):
                return json.loads(content)
            else:
                return {"raw_response": content}
        
        except Exception as e:
            logger.error(f"Error tagging FATE: {e}")
            return {"error": str(e)}
    
    def classify_hook_type(
        self,
        hook_text: str
    ) -> Dict[str, Any]:
        """
        Classify hook type
        
        Args:
            hook_text: Text of the hook segment
            
        Returns:
            Hook classification
        """
        if not self.is_enabled():
            return {}
        
        try:
            prompt = f"""Classify this video hook.
Return JSON:
{{
  "hook_type": "pain" | "curiosity" | "aspirational" | "contrarian" | "gap" | "absurd",
  "hook_score": 0.0 to 1.0 (how effective is this hook?),
  "reasoning": "short explanation",
  "improvements": ["suggestion 1", "suggestion 2"]
}}

Hook text:
{hook_text}

Return only valid JSON."""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing viral video hooks for social media."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            
            if content.startswith('{'):
                return json.loads(content)
            else:
                return {"raw_response": content}
        
        except Exception as e:
            logger.error(f"Error classifying hook: {e}")
            return {"error": str(e)}
    
    def extract_cta_keywords(
        self,
        transcript_text: str
    ) -> Dict[str, Any]:
        """
        Extract CTA keywords and analyze CTA effectiveness
        
        Args:
            transcript_text: Full or CTA segment transcript
            
        Returns:
            CTA analysis
        """
        if not self.is_enabled():
            return {}
        
        try:
            prompt = f"""Analyze the Call-To-Action (CTA) in this content.
Return JSON:
{{
  "has_cta": true/false,
  "cta_type": "conversion" | "engagement" | "open_loop" | "conversation" | null,
  "cta_keywords": ["keyword1", "keyword2"],
  "cta_text": "the actual CTA phrase",
  "cta_clarity_score": 0.0 to 1.0,
  "suggestions": ["improvement 1", "improvement 2"]
}}

Content:
{transcript_text}

Return only valid JSON."""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing CTAs and conversion optimization."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=300
            )
            
            content = response.choices[0].message.content.strip()
            
            if content.startswith('{'):
                return json.loads(content)
            else:
                return {"raw_response": content}
        
        except Exception as e:
            logger.error(f"Error extracting CTA: {e}")
            return {"error": str(e)}
    
    def analyze_sentiment_emotion(
        self,
        text: str,
        granularity: str = "sentence"
    ) -> Dict[str, Any]:
        """
        Analyze sentiment and emotion in text
        
        Args:
            text: Text to analyze
            granularity: "overall" | "sentence" | "word"
            
        Returns:
            Sentiment and emotion analysis
        """
        if not self.is_enabled():
            return {}
        
        try:
            prompt = f"""Analyze the sentiment and emotion in this text.
Return JSON:
{{
  "sentiment_score": -1.0 to 1.0 (-1=very negative, 0=neutral, 1=very positive),
  "primary_emotion": "curiosity" | "frustration" | "hope" | "flex" | "warning" | "excitement" | "relief",
  "emotion_intensity": 0.0 to 1.0,
  "tone": "calm_teacher" | "hype_coach" | "rant" | "confessional" | "storyteller"
}}

Text:
{text}

Return only valid JSON."""

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at analyzing text sentiment and emotional tone."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            
            if content.startswith('{'):
                return json.loads(content)
            else:
                return {"raw_response": content}
        
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {"error": str(e)}
    
    def comprehensive_analysis(
        self,
        transcript_text: str,
        duration_s: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Run full psychology analysis on transcript
        
        Args:
            transcript_text: Full transcript
            duration_s: Video duration
            
        Returns:
            Comprehensive analysis results
        """
        if not self.is_enabled():
            return {"error": "Psychology tagging not enabled"}
        
        logger.info("Running comprehensive psychology analysis")
        
        results = {
            "segments": {},
            "overall_sentiment": {},
            "cta_analysis": {},
            "hook_analysis": {}
        }
        
        # Step 1: Classify segments
        logger.info("Classifying segments...")
        segments_result = self.classify_segments(transcript_text, duration_s)
        results["segments"] = segments_result
        
        if "segments" in segments_result:
            segments = segments_result["segments"]
            
            # Step 2: Analyze hook
            hook_segments = [s for s in segments if s["segment_type"] == "hook"]
            if hook_segments:
                hook_text = hook_segments[0].get("summary", "")
                logger.info("Analyzing hook...")
                results["hook_analysis"] = self.classify_hook_type(hook_text)
            
            # Step 3: Tag FATE for each segment
            logger.info("Tagging FATE framework...")
            for segment in segments:
                segment_text = segment.get("summary", "")
                fate_tags = self.tag_fate_framework(segment_text, segment["segment_type"])
                segment["fate_tags"] = fate_tags
        
        # Step 4: Extract CTA
        logger.info("Extracting CTA...")
        results["cta_analysis"] = self.extract_cta_keywords(transcript_text)
        
        # Step 5: Overall sentiment
        logger.info("Analyzing sentiment...")
        results["overall_sentiment"] = self.analyze_sentiment_emotion(transcript_text)
        
        logger.info("Comprehensive analysis complete")
        return results
