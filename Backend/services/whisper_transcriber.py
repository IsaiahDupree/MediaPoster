"""
Whisper Transcription Service
Extracts audio from video and transcribes using OpenAI's Whisper API
"""
import os
import subprocess
import tempfile
from pathlib import Path
from openai import OpenAI
from loguru import logger


class WhisperTranscriber:
    """Handle video transcription using Whisper API"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize transcriber
        
        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        
        self.client = OpenAI(api_key=self.api_key)
    
    def extract_audio(self, video_path: str) -> str:
        """
        Extract audio from video file
        
        Args:
            video_path: Path to video file
            
        Returns:
            Path to extracted audio file (mp3)
        """
        video_path = os.path.expanduser(video_path)
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Create temp file for audio
        temp_dir = tempfile.gettempdir()
        audio_path = os.path.join(temp_dir, f"{Path(video_path).stem}_audio.mp3")
        
        # Extract audio using FFmpeg
        cmd = [
            "ffmpeg",
            "-i", video_path,
            "-vn",  # No video
            "-acodec", "libmp3lame",  # MP3 codec
            "-ar", "16000",  # 16kHz sample rate (Whisper optimal)
            "-ac", "1",  # Mono channel
            "-b:a", "64k",  # Bitrate
            "-y",  # Overwrite
            audio_path
        ]
        
        try:
            logger.info(f"Extracting audio from {Path(video_path).name}")
            subprocess.run(cmd, capture_output=True, check=True)
            logger.success(f"Audio extracted: {audio_path}")
            return audio_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr.decode()}")
            raise RuntimeError(f"Failed to extract audio: {e}")
    
    def transcribe(self, audio_path: str) -> dict:
        """
        Transcribe audio using Whisper API
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            dict with transcript text and metadata
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"Transcribing audio with Whisper API")
        
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",  # Get timestamps
                    language="en"  # Can be made configurable
                )
            
            logger.success(f"Transcription complete: {len(transcript.text)} characters")
            
            return {
                "text": transcript.text,
                "language": transcript.language,
                "duration": transcript.duration,
                "segments": transcript.segments if hasattr(transcript, 'segments') else []
            }
            
        except Exception as e:
            logger.error(f"Whisper API error: {e}")
            raise RuntimeError(f"Transcription failed: {e}")
    
    def transcribe_video(self, video_path: str, cleanup: bool = True) -> dict:
        """
        Complete transcription pipeline: extract audio + transcribe
        
        Args:
            video_path: Path to video file
            cleanup: Whether to delete temp audio file
            
        Returns:
            dict with transcript and metadata
        """
        logger.info(f"Starting transcription for {Path(video_path).name}")
        
        # Extract audio
        audio_path = self.extract_audio(video_path)
        
        try:
            # Transcribe
            result = self.transcribe(audio_path)
            
            logger.success(f"Video transcription complete")
            return result
            
        finally:
            # Cleanup temp audio file
            if cleanup and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                    logger.info(f"Cleaned up temp audio file")
                except Exception as e:
                    logger.warning(f"Failed to clean up {audio_path}: {e}")
