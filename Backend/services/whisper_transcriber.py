"""
Whisper Transcription Service
Extracts audio from video and transcribes using Groq's Whisper API (or OpenAI fallback)
"""
import os
import subprocess
import tempfile
from pathlib import Path
from loguru import logger


class WhisperTranscriber:
    """Handle video transcription using Whisper API (Groq primary, OpenAI fallback)"""
    
    # Image extensions that should never be processed for audio
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.heif', '.tiff', '.svg'}
    
    def __init__(self, api_key: str = None, provider: str = None):
        """
        Initialize transcriber
        
        Args:
            api_key: API key (defaults to GROQ_API_KEY, falls back to OPENAI_API_KEY)
            provider: Provider to use ('groq' or 'openai', defaults to GROQ if available)
        """
        # Determine provider and API key
        self.provider = provider or os.getenv("TRANSCRIPTION_PROVIDER", "groq")
        
        if self.provider == "groq":
            self.api_key = api_key or os.getenv("GROQ_API_KEY")
            if self.api_key:
                from groq import Groq
                self.client = Groq(api_key=self.api_key)
                logger.info("Using Groq for transcription (FREE, 32x faster)")
            else:
                # Fallback to OpenAI
                logger.warning("GROQ_API_KEY not found, falling back to OpenAI")
                self.provider = "openai"
                self.api_key = os.getenv("OPENAI_API_KEY")
                if not self.api_key:
                    raise ValueError("Neither GROQ_API_KEY nor OPENAI_API_KEY found")
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
        else:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY not found in environment")
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
    
    def has_audio_stream(self, file_path: str) -> bool:
        """
        Check if a file has an audio stream using FFprobe
        
        Args:
            file_path: Path to media file
            
        Returns:
            True if file has audio stream, False otherwise
        """
        # Quick check: images never have audio
        ext = Path(file_path).suffix.lower()
        if ext in self.IMAGE_EXTENSIONS:
            logger.info(f"Skipping audio check for image file: {ext}")
            return False
        
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=codec_type",
                "-of", "csv=p=0",
                file_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            has_audio = "audio" in result.stdout.lower()
            logger.info(f"Audio stream check for {Path(file_path).name}: {has_audio}")
            return has_audio
        except Exception as e:
            logger.warning(f"FFprobe check failed: {e}, assuming no audio")
            return False
    
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
        
        # Check if file has audio before attempting extraction
        if not self.has_audio_stream(video_path):
            logger.warning(f"No audio stream found in {Path(video_path).name}, returning empty transcript")
            return {
                "text": "",
                "language": None,
                "duration": None,
                "segments": [],
                "no_audio": True
            }
        
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
