"""
Audio Mixer
Mix background music with video audio using FFmpeg
"""
from pathlib import Path
from typing import Optional
from loguru import logger
import ffmpeg


class AudioMixer:
    """Mix background music with video audio"""
    
    def __init__(self):
        """Initialize audio mixer"""
        logger.info("Audio mixer initialized")
    
    def add_background_music(
        self,
        video_path: Path,
        music_path: Path,
        output_path: Path,
        music_volume: float = 0.3,
        video_volume: float = 1.0,
        fade_in_duration: float = 1.0,
        fade_out_duration: float = 1.0,
        loop_music: bool = True
    ) -> bool:
        """
        Add background music to video
        
        Args:
            video_path: Path to input video
            music_path: Path to music file
            output_path: Path for output video
            music_volume: Music volume (0.0-1.0)
            video_volume: Original audio volume (0.0-1.0)
            fade_in_duration: Music fade in duration (seconds)
            fade_out_duration: Music fade out duration (seconds)
            loop_music: Loop music if shorter than video
            
        Returns:
            True if successful
        """
        logger.info(f"Adding background music: {music_path.name}")
        logger.info(f"  Music volume: {music_volume:.0%}")
        logger.info(f"  Video volume: {video_volume:.0%}")
        
        try:
            # Get video duration
            probe = ffmpeg.probe(str(video_path))
            video_duration = float(probe['format']['duration'])
            
            # Get music duration
            music_probe = ffmpeg.probe(str(music_path))
            music_duration = float(music_probe['format']['duration'])
            
            logger.info(f"  Video duration: {video_duration:.1f}s")
            logger.info(f"  Music duration: {music_duration:.1f}s")
            
            # Input streams
            video_input = ffmpeg.input(str(video_path))
            music_input = ffmpeg.input(str(music_path))
            
            # Extract video and audio from video
            video_stream = video_input.video
            video_audio = video_input.audio
            
            # Process music
            music_stream = music_input.audio
            
            # Loop music if needed
            if loop_music and music_duration < video_duration:
                # Calculate how many loops needed
                loops = int(video_duration / music_duration) + 1
                logger.info(f"  Looping music {loops} times")
                
                # Create concat for looping
                music_inputs = [ffmpeg.input(str(music_path)).audio for _ in range(loops)]
                music_stream = ffmpeg.concat(*music_inputs, v=0, a=1)
            
            # Trim music to video duration
            music_stream = music_stream.filter('atrim', duration=video_duration)
            
            # Apply fade in/out to music
            if fade_in_duration > 0:
                music_stream = music_stream.filter('afade', t='in', d=fade_in_duration)
            
            if fade_out_duration > 0:
                music_stream = music_stream.filter(
                    'afade',
                    t='out',
                    st=max(0, video_duration - fade_out_duration),
                    d=fade_out_duration
                )
            
            # Adjust volumes
            music_stream = music_stream.filter('volume', music_volume)
            
            if video_volume != 1.0:
                video_audio = video_audio.filter('volume', video_volume)
            
            # Mix audio streams
            mixed_audio = ffmpeg.filter([video_audio, music_stream], 'amix', inputs=2, duration='first')
            
            # Combine video with mixed audio
            output = ffmpeg.output(
                video_stream,
                mixed_audio,
                str(output_path),
                vcodec='copy',  # Copy video codec (no re-encode)
                acodec='aac',   # Encode audio to AAC
                audio_bitrate='192k',
                strict='experimental'
            )
            
            # Run FFmpeg
            output.overwrite_output().run(capture_stdout=True, capture_stderr=True)
            
            logger.success(f"✓ Background music added: {output_path}")
            return True
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error: {e.stderr.decode()}")
            return False
        except Exception as e:
            logger.error(f"Failed to add background music: {e}")
            return False
    
    def replace_audio(
        self,
        video_path: Path,
        music_path: Path,
        output_path: Path,
        fade_in_duration: float = 0.5,
        fade_out_duration: float = 0.5
    ) -> bool:
        """
        Replace video audio entirely with music
        
        Args:
            video_path: Path to input video
            music_path: Path to music file
            output_path: Path for output video
            fade_in_duration: Music fade in duration
            fade_out_duration: Music fade out duration
            
        Returns:
            True if successful
        """
        logger.info(f"Replacing audio with: {music_path.name}")
        
        try:
            # Get video duration
            probe = ffmpeg.probe(str(video_path))
            video_duration = float(probe['format']['duration'])
            
            # Input streams
            video_input = ffmpeg.input(str(video_path))
            music_input = ffmpeg.input(str(music_path))
            
            # Video stream (no audio)
            video_stream = video_input.video
            
            # Music stream
            music_stream = music_input.audio
            
            # Trim music to video duration
            music_stream = music_stream.filter('atrim', duration=video_duration)
            
            # Apply fades
            if fade_in_duration > 0:
                music_stream = music_stream.filter('afade', t='in', d=fade_in_duration)
            
            if fade_out_duration > 0:
                music_stream = music_stream.filter(
                    'afade',
                    t='out',
                    st=max(0, video_duration - fade_out_duration),
                    d=fade_out_duration
                )
            
            # Combine
            output = ffmpeg.output(
                video_stream,
                music_stream,
                str(output_path),
                vcodec='copy',
                acodec='aac',
                audio_bitrate='192k'
            )
            
            output.overwrite_output().run(capture_stdout=True, capture_stderr=True)
            
            logger.success(f"✓ Audio replaced: {output_path}")
            return True
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error: {e.stderr.decode()}")
            return False
        except Exception as e:
            logger.error(f"Failed to replace audio: {e}")
            return False
    
    def adjust_music_volume(
        self,
        video_path: Path,
        output_path: Path,
        volume: float = 0.5
    ) -> bool:
        """
        Adjust volume of existing audio
        
        Args:
            video_path: Input video
            output_path: Output video
            volume: Volume multiplier (0.0-2.0)
            
        Returns:
            True if successful
        """
        logger.info(f"Adjusting audio volume to {volume:.0%}")
        
        try:
            stream = ffmpeg.input(str(video_path))
            audio = stream.audio.filter('volume', volume)
            video = stream.video
            
            output = ffmpeg.output(
                video,
                audio,
                str(output_path),
                vcodec='copy',
                acodec='aac'
            )
            
            output.overwrite_output().run(capture_stdout=True, capture_stderr=True)
            
            logger.success(f"✓ Volume adjusted")
            return True
            
        except Exception as e:
            logger.error(f"Failed to adjust volume: {e}")
            return False


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("AUDIO MIXER")
    print("="*60)
    print("\nMixes background music with video audio.")
    print("For testing, use test_phase3.py")
