"""
Whisper Transcription Service
Uses OpenAI Whisper API for accurate speech-to-text
"""
import openai
from pathlib import Path
from typing import Optional, Dict, List
from loguru import logger
import subprocess
import json

from config import settings


class WhisperService:
    """Transcribe video audio using OpenAI Whisper"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "whisper-1"):
        """
        Initialize Whisper service
        
        Args:
            api_key: OpenAI API key (defaults to settings)
            model: Whisper model to use
        """
        self.api_key = api_key or settings.openai_api_key
        openai.api_key = self.api_key
        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key)
        
        logger.info(f"Whisper service initialized with model: {model}")
    
    def extract_audio(self, video_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Extract audio from video file
        
        Args:
            video_path: Path to video file
            output_path: Where to save audio (optional)
            
        Returns:
            Path to extracted audio file
        """
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_audio.mp3"
        
        logger.info(f"Extracting audio from {video_path.name}")
        
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',  # No video
            '-acodec', 'libmp3lame',
            '-ar', '16000',  # 16kHz sample rate (good for speech)
            '-ac', '1',  # Mono
            '-b:a', '64k',  # 64 kbps bitrate
            '-y',  # Overwrite
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"FFmpeg failed: {result.stderr}")
            
            logger.success(f"✓ Audio extracted: {output_path.name}")
            return output_path
            
        except subprocess.TimeoutExpired:
            logger.error("Audio extraction timed out")
            raise
        except Exception as e:
            logger.error(f"Failed to extract audio: {e}")
            raise
    
    def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
        format: str = "verbose_json"
    ) -> Dict:
        """
        Transcribe audio file using Whisper API
        
        Args:
            audio_path: Path to audio file
            language: Language code (e.g., 'en', 'es') or None for auto-detect
            format: Response format (json, text, srt, verbose_json, vtt)
            
        Returns:
            Transcription result with timestamps
        """
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"Transcribing audio: {audio_path.name}")
        
        try:
            with open(audio_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model=self.model,
                    file=audio_file,
                    language=language,
                    response_format=format,
                    timestamp_granularities=["word", "segment"]
                )
            
            # Parse response
            if format == "verbose_json":
                result = {
                    'text': transcript.text,
                    'language': transcript.language,
                    'duration': transcript.duration,
                    'words': transcript.words if hasattr(transcript, 'words') else [],
                    'segments': transcript.segments if hasattr(transcript, 'segments') else []
                }
            else:
                result = {'text': transcript}
            
            logger.success(f"✓ Transcription complete ({len(result['text'])} chars)")
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def transcribe_video(
        self,
        video_path: Path,
        language: Optional[str] = None,
        cleanup: bool = True
    ) -> Dict:
        """
        Complete transcription workflow: extract audio + transcribe
        
        Args:
            video_path: Path to video file
            language: Language code or None for auto-detect
            cleanup: Delete temporary audio file after transcription
            
        Returns:
            Transcription result with timestamps
        """
        logger.info(f"Starting transcription for: {video_path.name}")
        
        # Extract audio
        audio_path = self.extract_audio(video_path)
        
        try:
            # Transcribe
            result = self.transcribe(audio_path, language=language)
            
            # Add metadata
            result['video_path'] = str(video_path)
            result['video_name'] = video_path.name
            
            return result
            
        finally:
            # Cleanup temporary audio file
            if cleanup and audio_path.exists():
                audio_path.unlink()
                logger.debug(f"Cleaned up temporary audio: {audio_path.name}")
    
    def generate_srt(self, transcript: Dict, output_path: Path) -> Path:
        """
        Generate SRT subtitle file from transcript
        
        Args:
            transcript: Transcription result with segments
            output_path: Where to save SRT file
            
        Returns:
            Path to SRT file
        """
        logger.info(f"Generating SRT file: {output_path.name}")
        
        if 'segments' not in transcript or not transcript['segments']:
            raise ValueError("Transcript does not contain segments")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(transcript['segments'], 1):
                # Format timestamps
                start = self._format_timestamp(segment['start'])
                end = self._format_timestamp(segment['end'])
                text = segment['text'].strip()
                
                # Write SRT entry
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
        
        logger.success(f"✓ SRT file created: {output_path.name}")
        return output_path
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as SRT timestamp (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def get_word_timestamps(self, transcript: Dict) -> List[Dict]:
        """
        Extract word-level timestamps from transcript
        
        Args:
            transcript: Transcription result
            
        Returns:
            List of {word, start, end} dictionaries
        """
        if 'words' in transcript and transcript['words']:
            return [
                {
                    'word': w.word if hasattr(w, 'word') else w['word'],
                    'start': w.start if hasattr(w, 'start') else w['start'],
                    'end': w.end if hasattr(w, 'end') else w['end']
                }
                for w in transcript['words']
            ]
        return []
    
    def search_transcript(self, transcript: Dict, query: str) -> List[Dict]:
        """
        Search for specific words/phrases in transcript
        
        Args:
            transcript: Transcription result
            query: Search query
            
        Returns:
            List of matching segments with timestamps
        """
        query_lower = query.lower()
        matches = []
        
        if 'segments' in transcript:
            for segment in transcript['segments']:
                if query_lower in segment['text'].lower():
                    matches.append({
                        'text': segment['text'],
                        'start': segment['start'],
                        'end': segment['end']
                    })
        
        return matches


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python whisper_service.py <video_file>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    
    if not video_path.exists():
        print(f"Video file not found: {video_path}")
        sys.exit(1)
    
    # Test transcription
    service = WhisperService()
    result = service.transcribe_video(video_path)
    
    print("\n" + "="*60)
    print("TRANSCRIPTION RESULT")
    print("="*60)
    print(f"\nLanguage: {result.get('language', 'unknown')}")
    print(f"Duration: {result.get('duration', 0):.1f}s")
    print(f"\nTranscript:\n{result['text']}")
    print(f"\nSegments: {len(result.get('segments', []))}")
    print(f"Words: {len(result.get('words', []))}")
    
    # Generate SRT
    srt_path = video_path.parent / f"{video_path.stem}_subtitles.srt"
    service.generate_srt(result, srt_path)
    print(f"\n✓ SRT file saved: {srt_path}")
