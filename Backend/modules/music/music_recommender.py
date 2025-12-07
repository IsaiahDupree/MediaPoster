"""
Music Recommendation System
AI-powered background music selection for videos
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from loguru import logger
import os
import requests


@dataclass
class MusicTrack:
    """Music track metadata"""
    track_id: str
    title: str
    artist: str
    duration: int  # seconds
    genre: str
    mood: str
    tempo: str  # slow, medium, fast
    download_url: str
    preview_url: Optional[str] = None
    source: str = "pixabay"  # pixabay, pexels, youtube
    license: str = "royalty-free"


class MusicRecommender:
    """
    Recommend background music for videos
    Supports multiple free music APIs
    """
    
    def __init__(self):
        """Initialize with API keys"""
        self.pixabay_key = os.getenv('PIXABAY_API_KEY')
        self.pexels_key = os.getenv('PEXELS_API_KEY')
        
        logger.info("Music Recommender initialized")
    
    def analyze_video_mood(self, prompt: str) -> Dict[str, str]:
        """
        Analyze video mood from prompt/description
        
        Args:
            prompt: Video description or generation prompt
            
        Returns:
            {
                'mood': 'upbeat' | 'calm' | 'dramatic' | 'energetic' | 'emotional',
                'genre': 'electronic' | 'acoustic' | 'rock' | 'ambient' | 'cinematic',
                'tempo': 'slow' | 'medium' | 'fast'
            }
        """
        prompt_lower = prompt.lower()
        
        # Simple keyword-based mood detection
        mood = 'neutral'
        genre = 'ambient'
        tempo = 'medium'
        
        # Mood detection
        if any(word in prompt_lower for word in ['happy', 'fun', 'joyful', 'upbeat', 'exciting']):
            mood = 'upbeat'
            tempo = 'fast'
        elif any(word in prompt_lower for word in ['calm', 'peaceful', 'serene', 'relaxing', 'meditation']):
            mood = 'calm'
            tempo = 'slow'
        elif any(word in prompt_lower for word in ['dramatic', 'intense', 'epic', 'powerful']):
            mood = 'dramatic'
            genre = 'cinematic'
        elif any(word in prompt_lower for word in ['energetic', 'fast', 'action', 'sport']):
            mood = 'energetic'
            tempo = 'fast'
        elif any(word in prompt_lower for word in ['sad', 'emotional', 'melancholic', 'nostalgic']):
            mood = 'emotional'
            tempo = 'slow'
        
        # Genre hints
        if any(word in prompt_lower for word in ['tech', 'digital', 'cyber', 'futuristic']):
            genre = 'electronic'
        elif any(word in prompt_lower for word in ['nature', 'organic', 'acoustic', 'guitar']):
            genre = 'acoustic'
        elif any(word in prompt_lower for word in ['rock', 'band', 'loud']):
            genre = 'rock'
        
        logger.info(f"Analyzed mood: {mood}, genre: {genre}, tempo: {tempo}")
        
        return {
            'mood': mood,
            'genre': genre,
            'tempo': tempo
        }
    
    def recommend_tracks(
        self, 
        mood: str, 
        duration: int, 
        limit: int = 5
    ) -> List[MusicTrack]:
        """
        Recommend music tracks
        
        Args:
            mood: Desired mood
            duration: Video duration in seconds
            limit: Max number of tracks to return
            
        Returns:
            List of recommended tracks
        """
        tracks = []
        
        # Try Pixabay first
        if self.pixabay_key:
            pixabay_tracks = self._search_pixabay(mood, duration, limit)
            tracks.extend(pixabay_tracks)
        
        # Try Pexels if needed
        if len(tracks) < limit and self.pexels_key:
            pexels_tracks = self._search_pexels(mood, duration, limit - len(tracks))
            tracks.extend(pexels_tracks)
        
        # Use curated fallback if no API keys
        if not tracks:
            tracks = self._get_fallback_tracks(mood, duration, limit)
        
        logger.info(f"Recommended {len(tracks)} tracks for mood: {mood}")
        return tracks[:limit]
    
    def _search_pixabay(self, mood: str, duration: int, limit: int) -> List[MusicTrack]:
        """Search Pixabay music library"""
        try:
            # Pixabay Music API
            url = "https://pixabay.com/api/music/"
            params = {
                'key': self.pixabay_key,
                'q': mood,
                'per_page': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Pixabay API error: {response.status_code}")
                return []
            
            data = response.json()
            tracks = []
            
            for item in data.get('hits', []):
                track = MusicTrack(
                    track_id=f"pixabay_{item['id']}",
                    title=item.get('name', 'Unknown'),
                    artist=item.get('artist', 'Unknown'),
                    duration=item.get('duration', duration),
                    genre=item.get('genre', 'ambient'),
                    mood=mood,
                    tempo='medium',
                    download_url=item.get('url', ''),
                    preview_url=item.get('previewURL'),
                    source='pixabay',
                    license='Pixabay License'
                )
                tracks.append(track)
            
            logger.success(f"Found {len(tracks)} tracks from Pixabay")
            return tracks
            
        except Exception as e:
            logger.error(f"Pixabay search failed: {e}")
            return []
    
    def _search_pexels(self, mood: str, duration: int, limit: int) -> List[MusicTrack]:
        """Search Pexels music library"""
        try:
            # Pexels doesn't have a music API yet, but keeping for future
            logger.warning("Pexels music API not yet available")
            return []
        except Exception as e:
            logger.error(f"Pexels search failed: {e}")
            return []
    
    def _get_fallback_tracks(self, mood: str, duration: int, limit: int) -> List[MusicTrack]:
        """Fallback curated track list"""
        # Curated free music tracks (YouTube Audio Library examples)
        curated = {
            'upbeat': [
                MusicTrack(
                    track_id='fallback_1',
                    title='Happy Upbeat Track',
                    artist='AudioLibrary',
                    duration=180,
                    genre='electronic',
                    mood='upbeat',
                    tempo='fast',
                    download_url='https://example.com/track1.mp3',
                    source='curated',
                    license='CC0'
                )
            ],
            'calm': [
                MusicTrack(
                    track_id='fallback_2',
                    title='Peaceful Ambient',
                    artist='AudioLibrary',
                    duration=240,
                    genre='ambient',
                    mood='calm',
                    tempo='slow',
                    download_url='https://example.com/track2.mp3',
                    source='curated',
                    license='CC0'
                )
            ]
        }
        
        tracks = curated.get(mood, curated['calm'])
        logger.info(f"Using {len(tracks)} fallback tracks")
        return tracks[:limit]
    
    def download_track(self, track: MusicTrack, output_path: str) -> bool:
        """
        Download a music track
        
        Args:
            track: MusicTrack object
            output_path: Local file path to save
            
        Returns:
            True if successful
        """
        if not track.download_url:
            logger.error("No download URL available")
            return False
        
        try:
            logger.info(f"Downloading {track.title} to {output_path}")
            
            response = requests.get(track.download_url, stream=True, timeout=60)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.success(f"Downloaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Download failed: {e}")
            return False
    
    def add_background_music(
        self, 
        video_path: str, 
        music_path: str, 
        output_path: str,
        volume: float = 0.3,
        fade_duration: float = 2.0
    ) -> bool:
        """
        Mix background music with video
        
        Args:
            video_path: Input video file
            music_path: Background music file
            output_path: Output video file
            volume: Music volume (0.0-1.0)
            fade_duration: Fade in/out duration in seconds
            
        Returns:
            True if successful
        """
        try:
            from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
            
            logger.info(f"Mixing {music_path} with {video_path}")
            
            # Load video and music
            video = VideoFileClip(video_path)
            music = AudioFileClip(music_path)
            
            # Trim or loop music to match video duration
            if music.duration > video.duration:
                music = music.subclip(0, video.duration)
            elif music.duration < video.duration:
                # Loop music
                loops_needed = int(video.duration / music.duration) + 1
                music = music.loop(n=loops_needed).subclip(0, video.duration)
            
            # Apply volume and fade
            music = music.volumex(volume)
            music = music.audio_fadein(fade_duration).audio_fadeout(fade_duration)
            
            # Mix with original audio if exists
            if video.audio:
                composite_audio = CompositeAudioClip([video.audio, music])
            else:
                composite_audio = music
            
            # Set audio to video
            final_video = video.set_audio(composite_audio)
            
            # Write output
            final_video.write_videofile(
                output_path,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True
            )
            
            # Clean up
            video.close()
            music.close()
            final_video.close()
            
            logger.success(f"Video with music saved to {output_path}")
            return True
            
        except ImportError:
            logger.error("moviepy not installed. Run: pip install moviepy")
            return False
        except Exception as e:
            logger.error(f"Audio mixing failed: {e}")
            return False


# Example usage
if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    
    recommender = MusicRecommender()
    
    # Test mood analysis
    test_prompts = [
        "A serene lake at sunset with mountains",
        "Fast-paced action scene with cars racing",
        "Emotional scene of person remembering childhood",
        "Futuristic cyberpunk city at night"
    ]
    
    logger.info("\n" + "="*80)
    logger.info("MOOD ANALYSIS TEST")
    logger.info("="*80)
    
    for prompt in test_prompts:
        logger.info(f"\nPrompt: {prompt}")
        mood_data = recommender.analyze_video_mood(prompt)
        logger.info(f"Result: {mood_data}")
    
    # Test track recommendation
    logger.info("\n" + "="*80)
    logger.info("TRACK RECOMMENDATION TEST")
    logger.info("="*80)
    
    tracks = recommender.recommend_tracks(mood='upbeat', duration=30, limit=3)
    
    if tracks:
        logger.info(f"\nFound {len(tracks)} tracks:")
        for i, track in enumerate(tracks, 1):
            logger.info(f"\n{i}. {track.title} by {track.artist}")
            logger.info(f"   Duration: {track.duration}s")
            logger.info(f"   Source: {track.source}")
            logger.info(f"   License: {track.license}")
    else:
        logger.warning("No tracks found")
    
    logger.info("\n" + "="*80)
