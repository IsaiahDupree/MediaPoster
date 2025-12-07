"""
GPT-Powered Highlight Recommender
Uses GPT-4 to provide intelligent highlight recommendations and reasoning
"""
import openai
from typing import List, Dict, Optional
from loguru import logger
import json

from config import settings


class GPTRecommender:
    """Use GPT-4 to recommend and explain highlights"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize GPT recommender
        
        Args:
            api_key: OpenAI API key
        """
        self.api_key = api_key or settings.openai_api_key
        self.client = openai.OpenAI(api_key=self.api_key)
        
        logger.info("GPT recommender initialized")
    
    def recommend_highlights(
        self,
        video_context: Dict,
        candidate_highlights: List[Dict],
        target_count: int = 3
    ) -> List[Dict]:
        """
        Use GPT-4 to recommend best highlights
        
        Args:
            video_context: Video metadata and analysis summary
            candidate_highlights: Ranked highlights from HighlightRanker
            target_count: Number of highlights to recommend
            
        Returns:
            Top recommended highlights with GPT reasoning
        """
        logger.info(f"Getting GPT-4 recommendations for top {target_count} highlights")
        
        # Prepare prompt
        prompt = self._build_recommendation_prompt(
            video_context,
            candidate_highlights[:10],  # Send top 10 to GPT
            target_count
        )
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert video editor specializing in creating viral short-form content. You analyze videos and recommend the best moments for highlights."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=1000
            )
            
            # Parse GPT response
            gpt_analysis = response.choices[0].message.content
            
            # Extract recommendations
            recommendations = self._parse_recommendations(
                gpt_analysis,
                candidate_highlights
            )
            
            logger.success(f"✓ GPT-4 provided {len(recommendations)} recommendations")
            return recommendations
            
        except Exception as e:
            logger.error(f"GPT recommendation failed: {e}")
            # Fallback to top scored highlights
            return candidate_highlights[:target_count]
    
    def _build_recommendation_prompt(
        self,
        video_context: Dict,
        candidates: List[Dict],
        target_count: int
    ) -> str:
        """Build prompt for GPT"""
        
        prompt = f"""I have a video with the following characteristics:

VIDEO CONTEXT:
- Duration: {video_context.get('duration', 'unknown')}s
- Content Type: {video_context.get('content_type', 'unknown')}
- Key Topics: {', '.join(video_context.get('key_topics', []))}
- Transcript Preview: {video_context.get('transcript_preview', 'N/A')[:200]}...

I've identified {len(candidates)} potential highlight moments. Here are the top candidates:

"""
        
        for i, candidate in enumerate(candidates, 1):
            prompt += f"\nCANDIDATE #{i}:\n"
            prompt += f"- Time: {candidate['start']:.1f}s - {candidate['end']:.1f}s ({candidate['duration']:.1f}s)\n"
            prompt += f"- Score: {candidate['composite_score']:.2f}\n"
            prompt += f"- Strengths: {', '.join(self._get_strengths(candidate))}\n"
            
            # Add signal breakdown
            signals = candidate.get('signal_scores', {})
            prompt += f"- Signals: Audio={signals.get('audio', 0):.2f}, Transcript={signals.get('transcript', 0):.2f}, Visual={signals.get('visual', 0):.2f}\n"
        
        prompt += f"""

TASK:
Please recommend the TOP {target_count} highlights that would make the best short-form clips for social media (TikTok, Instagram Reels, YouTube Shorts).

Consider:
1. Viral potential (hooks, punchlines, surprising moments)
2. Self-contained story (makes sense without full context)
3. Length (ideal 15-45 seconds)
4. Visual and audio interest
5. Emotional impact

For each recommendation, provide:
1. Candidate number (#1, #2, etc.)
2. Why this moment stands out
3. Suggested clip angle/theme
4. Estimated viral potential (low/medium/high)

Format your response as:
RECOMMENDATION 1: #X
Reason: ...
Clip Angle: ...
Viral Potential: ...

RECOMMENDATION 2: #Y
...
"""
        
        return prompt
    
    def _get_strengths(self, candidate: Dict) -> List[str]:
        """Get candidate strengths"""
        metadata = candidate.get('metadata', {})
        strengths = []
        
        if metadata.get('has_audio_peaks'):
            strengths.append("High energy")
        if metadata.get('has_transcript_hooks'):
            strengths.append("Strong hooks")
        if metadata.get('has_visual_interest'):
            strengths.append("Dynamic visuals")
        
        scores = candidate.get('signal_scores', {})
        if scores.get('audio', 0) > 0.7:
            strengths.append("Exciting audio")
        if scores.get('transcript', 0) > 0.7:
            strengths.append("Engaging content")
        
        return strengths if strengths else ["Balanced"]
    
    def _parse_recommendations(
        self,
        gpt_response: str,
        candidates: List[Dict]
    ) -> List[Dict]:
        """Parse GPT response into structured recommendations"""
        
        recommendations = []
        
        # Split by recommendation sections
        sections = gpt_response.split('RECOMMENDATION')
        
        for section in sections[1:]:  # Skip first empty split
            try:
                # Extract candidate number
                lines = section.strip().split('\n')
                first_line = lines[0]
                
                # Try to find candidate number
                import re
                match = re.search(r'#(\d+)', first_line)
                if match:
                    candidate_num = int(match.group(1)) - 1  # Convert to 0-indexed
                    
                    if 0 <= candidate_num < len(candidates):
                        candidate = candidates[candidate_num].copy()
                        
                        # Extract reason, angle, viral potential
                        reason = ""
                        angle = ""
                        viral = ""
                        
                        for line in lines[1:]:
                            if line.startswith('Reason:'):
                                reason = line.replace('Reason:', '').strip()
                            elif line.startswith('Clip Angle:'):
                                angle = line.replace('Clip Angle:', '').strip()
                            elif line.startswith('Viral Potential:'):
                                viral = line.replace('Viral Potential:', '').strip()
                        
                        candidate['gpt_reasoning'] = {
                            'reason': reason,
                            'clip_angle': angle,
                            'viral_potential': viral,
                            'full_analysis': section.strip()
                        }
                        
                        recommendations.append(candidate)
            except Exception as e:
                logger.warning(f"Failed to parse recommendation section: {e}")
                continue
        
        return recommendations
    
    def explain_highlight(
        self,
        highlight: Dict,
        video_context: Dict
    ) -> str:
        """
        Generate detailed explanation for why a highlight was chosen
        
        Args:
            highlight: Highlight data
            video_context: Video metadata
            
        Returns:
            Explanation text
        """
        logger.info(f"Generating explanation for highlight at {highlight['start']:.1f}s")
        
        prompt = f"""Explain why this is a good highlight for a short-form viral clip:

VIDEO: {video_context.get('video_name', 'Unknown')}
Content Type: {video_context.get('content_type', 'Unknown')}

HIGHLIGHT:
- Time: {highlight['start']:.1f}s - {highlight['end']:.1f}s
- Duration: {highlight['duration']:.1f}s
- Overall Score: {highlight['composite_score']:.2f}
- Audio Score: {highlight['signal_scores'].get('audio', 0):.2f}
- Transcript Score: {highlight['signal_scores'].get('transcript', 0):.2f}
- Visual Score: {highlight['signal_scores'].get('visual', 0):.2f}

Provide a 2-3 sentence explanation of why this moment would make a great clip."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a viral video content expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            explanation = response.choices[0].message.content
            logger.success("✓ Explanation generated")
            return explanation
            
        except Exception as e:
            logger.error(f"Explanation generation failed: {e}")
            return "This moment was selected based on high scores across audio, visual, and content analysis."
    
    def generate_clip_titles(
        self,
        highlight: Dict,
        video_context: Dict,
        count: int = 5
    ) -> List[str]:
        """
        Generate catchy titles for a highlight clip
        
        Args:
            highlight: Highlight data
            video_context: Video metadata
            count: Number of titles to generate
            
        Returns:
            List of suggested titles
        """
        logger.info(f"Generating {count} clip titles")
        
        prompt = f"""Generate {count} catchy, viral-worthy titles for this video clip:

VIDEO: {video_context.get('video_name', 'Video')}
Content Type: {video_context.get('content_type', 'Unknown')}
Clip Duration: {highlight['duration']:.1f}s
Key Topics: {', '.join(video_context.get('key_topics', [])[:5])}

The titles should be:
- Short (under 60 characters)
- Attention-grabbing
- Include emojis where appropriate
- Follow viral TikTok/Instagram style

Provide {count} title options, one per line, without numbering."""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a social media viral content expert specializing in catchy titles."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,  # Higher temperature for creativity
                max_tokens=300
            )
            
            titles_text = response.choices[0].message.content
            titles = [t.strip() for t in titles_text.split('\n') if t.strip()]
            
            logger.success(f"✓ Generated {len(titles)} titles")
            return titles[:count]
            
        except Exception as e:
            logger.error(f"Title generation failed: {e}")
            return [f"Viral Moment #{i+1}" for i in range(count)]


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("GPT RECOMMENDER")
    print("="*60)
    print("\nThis module uses GPT-4 to provide intelligent recommendations.")
    print("Requires highlights from the HighlightRanker.")
    print("\nFor end-to-end testing, use test_phase2.py")
