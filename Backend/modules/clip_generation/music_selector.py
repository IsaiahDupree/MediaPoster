"""
Music Selector
AI-powered background music selection based on video content
"""
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger
import json
import random

from config import settings
from openai import OpenAI


class MusicSelector:
    """Select background music using AI based on content analysis"""
    
    MUSIC_GENRES = {
        'upbeat': ['energetic', 'happy', 'exciting', 'fun', 'motivational'],
        'calm': ['peaceful', 'relaxing', 'ambient', 'soft', 'meditation'],
        'dramatic': ['epic', 'intense', 'cinematic', 'powerful', 'suspenseful'],
        'corporate': ['professional', 'business', 'clean', 'modern', 'technology'],
        'emotional': ['inspiring', 'heartfelt', 'touching', 'sentimental', 'beautiful'],
        'hip_hop': ['urban', 'cool', 'street', 'rap', 'beats'],
        'electronic': ['techno', 'edm', 'dance', 'synth', 'futuristic'],
        'acoustic': ['guitar', 'folk', 'organic', 'natural', 'indie']
    }
    
    def __init__(self, music_library_path: Optional[Path] = None):
        """
        Initialize music selector
        
        Args:
            music_library_path: Path to music library JSON
        """
        self.music_library_path = music_library_path or Path("./data/music/library.json")
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        self.music_tracks = self._load_music_library()
        
        logger.info(f"Music selector initialized with {len(self.music_tracks)} tracks")
    
    def _load_music_library(self) -> List[Dict]:
        """Load music library from JSON"""
        if not self.music_library_path.exists():
            logger.warning(f"Music library not found: {self.music_library_path}")
            return self._create_default_library()
        
        try:
            with open(self.music_library_path, 'r') as f:
                library = json.load(f)
            
            logger.info(f"✓ Loaded {len(library)} tracks from library")
            return library
            
        except Exception as e:
            logger.error(f"Failed to load music library: {e}")
            return self._create_default_library()
    
    def _create_default_library(self) -> List[Dict]:
        """Create a default music library structure"""
        default_tracks = [
            {
                "id": "upbeat_001",
                "title": "Energetic Pop",
                "file": "music/upbeat_pop.mp3",
                "genre": "upbeat",
                "mood": ["energetic", "happy", "fun"],
                "tempo": "fast",
                "duration": 180,
                "tags": ["viral", "tiktok", "instagram", "youth"]
            },
            {
                "id": "calm_001",
                "title": "Peaceful Ambient",
                "file": "music/calm_ambient.mp3",
                "genre": "calm",
                "mood": ["peaceful", "relaxing", "meditation"],
                "tempo": "slow",
                "duration": 240,
                "tags": ["wellness", "mindfulness", "nature"]
            },
            {
                "id": "dramatic_001",
                "title": "Epic Cinematic",
                "file": "music/epic_cinematic.mp3",
                "genre": "dramatic",
                "mood": ["epic", "intense", "powerful"],
                "tempo": "medium",
                "duration": 200,
                "tags": ["storytelling", "impact", "reveals"]
            },
            {
                "id": "hiphop_001",
                "title": "Urban Beats",
                "file": "music/urban_beats.mp3",
                "genre": "hip_hop",
                "mood": ["cool", "urban", "street"],
                "tempo": "medium",
                "duration": 165,
                "tags": ["rap", "lifestyle", "fashion", "culture"]
            },
            {
                "id": "electronic_001",
                "title": "EDM Energy",
                "file": "music/edm_energy.mp3",
                "genre": "electronic",
                "mood": ["dance", "energetic", "futuristic"],
                "tempo": "fast",
                "duration": 190,
                "tags": ["party", "night", "club", "technology"]
            },
            {
                "id": "emotional_001",
                "title": "Inspiring Piano",
                "file": "music/inspiring_piano.mp3",
                "genre": "emotional",
                "mood": ["inspiring", "heartfelt", "beautiful"],
                "tempo": "slow",
                "duration": 210,
                "tags": ["motivation", "success", "journey", "transformation"]
            },
            {
                "id": "corporate_001",
                "title": "Professional Tech",
                "file": "music/corporate_tech.mp3",
                "genre": "corporate",
                "mood": ["professional", "modern", "clean"],
                "tempo": "medium",
                "duration": 195,
                "tags": ["business", "technology", "innovation", "startup"]
            },
            {
                "id": "acoustic_001",
                "title": "Indie Folk Guitar",
                "file": "music/indie_folk.mp3",
                "genre": "acoustic",
                "mood": ["organic", "natural", "warm"],
                "tempo": "medium",
                "duration": 175,
                "tags": ["lifestyle", "travel", "authentic", "story"]
            }
        ]
        
        # Save default library
        self.music_library_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.music_library_path, 'w') as f:
                json.dump(default_tracks, f, indent=2)
            logger.info(f"✓ Created default music library: {self.music_library_path}")
        except Exception as e:
            logger.error(f"Failed to save default library: {e}")
        
        return default_tracks
    
    def select_music_with_ai(
        self,
        video_metadata: Dict,
        top_n: int = 3
    ) -> List[Dict]:
        """
        Use GPT-4 to select best music tracks for video
        
        Args:
            video_metadata: Video content metadata (transcript, topics, insights)
            top_n: Number of track recommendations to return
            
        Returns:
            List of recommended tracks with reasoning
        """
        logger.info("Selecting music with AI...")
        
        # Build context for GPT
        context = self._build_content_context(video_metadata)
        
        # Create track descriptions for GPT
        track_descriptions = []
        for track in self.music_tracks:
            desc = (
                f"ID: {track['id']}\n"
                f"Title: {track['title']}\n"
                f"Genre: {track['genre']}\n"
                f"Mood: {', '.join(track['mood'])}\n"
                f"Tempo: {track['tempo']}\n"
                f"Tags: {', '.join(track['tags'])}\n"
            )
            track_descriptions.append(desc)
        
        tracks_text = "\n---\n".join(track_descriptions)
        
        # Build prompt
        prompt = f"""You are an expert music supervisor for social media content. 
Select the best background music track for this video clip.

VIDEO CONTENT:
{context}

AVAILABLE TRACKS:
{tracks_text}

Task: Recommend the top {top_n} tracks that would work best for this video.
Consider:
1. Content topic and mood
2. Target audience and platform
3. Pacing and energy level
4. Emotional resonance

Respond in JSON format:
{{
    "recommendations": [
        {{
            "track_id": "track_id_here",
            "confidence": 0.95,
            "reasoning": "Why this track fits the content"
        }}
    ]
}}

Provide exactly {top_n} recommendations, ordered by best fit."""

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert music supervisor."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            recommendations = result.get('recommendations', [])
            
            # Enrich with full track data
            enriched = []
            for rec in recommendations[:top_n]:
                track_id = rec['track_id']
                track = next((t for t in self.music_tracks if t['id'] == track_id), None)
                if track:
                    enriched.append({
                        **track,
                        'confidence': rec.get('confidence', 0.5),
                        'ai_reasoning': rec.get('reasoning', '')
                    })
            
            logger.success(f"✓ AI selected {len(enriched)} tracks")
            for i, track in enumerate(enriched, 1):
                logger.info(f"  {i}. {track['title']} ({track['confidence']:.0%} match)")
                logger.info(f"     {track['ai_reasoning']}")
            
            return enriched
            
        except Exception as e:
            logger.error(f"AI selection failed: {e}")
            # Fallback to rule-based
            return self._fallback_selection(video_metadata, top_n)
    
    def _build_content_context(self, metadata: Dict) -> str:
        """Build context string from video metadata"""
        parts = []
        
        if metadata.get('transcript'):
            transcript = metadata['transcript']
            if isinstance(transcript, str):
                parts.append(f"Transcript: {transcript[:500]}...")
            elif isinstance(transcript, list):
                text = ' '.join([w.get('word', '') for w in transcript[:100]])
                parts.append(f"Transcript: {text}...")
        
        if metadata.get('topics'):
            parts.append(f"Topics: {', '.join(metadata['topics'])}")
        
        if metadata.get('mood'):
            parts.append(f"Mood: {metadata['mood']}")
        
        if metadata.get('insights'):
            insights = metadata['insights']
            if isinstance(insights, dict):
                if insights.get('summary'):
                    parts.append(f"Summary: {insights['summary']}")
                if insights.get('viral_indicators'):
                    parts.append(f"Viral Indicators: {', '.join(insights['viral_indicators'])}")
        
        if metadata.get('platform'):
            parts.append(f"Platform: {metadata['platform']}")
        
        if metadata.get('duration'):
            parts.append(f"Duration: {metadata['duration']}s")
        
        return "\n".join(parts)
    
    def _fallback_selection(
        self,
        metadata: Dict,
        top_n: int = 3
    ) -> List[Dict]:
        """Fallback rule-based selection if AI fails"""
        logger.info("Using fallback rule-based selection")
        
        # Simple scoring based on keywords
        scores = []
        
        content_text = json.dumps(metadata).lower()
        
        for track in self.music_tracks:
            score = 0
            
            # Match genre keywords
            for mood in track['mood']:
                if mood.lower() in content_text:
                    score += 3
            
            # Match tags
            for tag in track['tags']:
                if tag.lower() in content_text:
                    score += 2
            
            # Platform preference
            platform = metadata.get('platform', 'tiktok')
            if platform in track['tags']:
                score += 5
            
            scores.append((track, score))
        
        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Get top N
        selected = []
        for track, score in scores[:top_n]:
            selected.append({
                **track,
                'confidence': min(score / 10, 1.0),
                'ai_reasoning': 'Rule-based selection based on content keywords'
            })
        
        if not selected and self.music_tracks:
            # Random fallback
            selected = random.sample(
                self.music_tracks, 
                min(top_n, len(self.music_tracks))
            )
            for track in selected:
                track['confidence'] = 0.5
                track['ai_reasoning'] = 'Random selection (fallback)'
        
        return selected
    
    def get_track_by_id(self, track_id: str) -> Optional[Dict]:
        """Get track by ID"""
        return next((t for t in self.music_tracks if t['id'] == track_id), None)
    
    def get_tracks_by_genre(self, genre: str) -> List[Dict]:
        """Get all tracks of a specific genre"""
        return [t for t in self.music_tracks if t['genre'] == genre]
    
    def get_tracks_by_mood(self, mood: str) -> List[Dict]:
        """Get tracks matching a mood"""
        return [t for t in self.music_tracks if mood in t['mood']]
    
    def add_track(self, track: Dict) -> bool:
        """Add a new track to the library"""
        try:
            # Validate required fields
            required = ['id', 'title', 'file', 'genre', 'mood']
            if not all(k in track for k in required):
                logger.error("Missing required track fields")
                return False
            
            # Check for duplicates
            if any(t['id'] == track['id'] for t in self.music_tracks):
                logger.error(f"Track ID already exists: {track['id']}")
                return False
            
            # Add track
            self.music_tracks.append(track)
            
            # Save library
            with open(self.music_library_path, 'w') as f:
                json.dump(self.music_tracks, f, indent=2)
            
            logger.success(f"✓ Added track: {track['title']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add track: {e}")
            return False


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("MUSIC SELECTOR")
    print("="*60)
    print("\nAI-powered background music selection.")
    print("For testing, use test_phase3.py")
