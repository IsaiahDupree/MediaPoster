"""
Audio Analysis Service
Analyzes audio characteristics for highlight detection
"""
import subprocess
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from loguru import logger


class AudioAnalyzer:
    """Analyze audio characteristics of videos"""
    
    def __init__(self):
        """Initialize audio analyzer"""
        logger.info("Audio analyzer initialized")
    
    def extract_audio_data(self, video_path: Path) -> Path:
        """
        Extract audio to WAV format for analysis
        
        Args:
            video_path: Path to video file
            
        Returns:
            Path to extracted WAV file
        """
        output_path = video_path.parent / f"{video_path.stem}_audio.wav"
        
        logger.info(f"Extracting audio data from {video_path.name}")
        
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', '44100',
            '-ac', '2',
            '-y',
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300
            )
            
            if result.returncode != 0:
                raise RuntimeError("Audio extraction failed")
            
            logger.success(f"✓ Audio extracted: {output_path.name}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to extract audio: {e}")
            raise
    
    def analyze_volume_levels(
        self,
        video_path: Path,
        interval: float = 0.5
    ) -> List[Dict]:
        """
        Analyze volume levels over time
        
        Args:
            video_path: Path to video file
            interval: Sampling interval in seconds
            
        Returns:
            List of volume measurements with timestamps
        """
        logger.info(f"Analyzing volume levels in {video_path.name}")
        
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-af', f'volumedetect',
            '-f', 'null',
            '-'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse volume statistics
            stats = {}
            for line in result.stderr.split('\n'):
                if 'mean_volume:' in line:
                    stats['mean_volume'] = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                elif 'max_volume:' in line:
                    stats['max_volume'] = float(line.split('max_volume:')[1].split('dB')[0].strip())
            
            logger.success(f"✓ Volume analysis complete")
            return [stats]
            
        except Exception as e:
            logger.error(f"Volume analysis failed: {e}")
            return []
    
    def detect_silence(
        self,
        video_path: Path,
        noise_threshold_db: float = -40.0,
        min_silence_duration: float = 0.5
    ) -> List[Dict]:
        """
        Detect silent periods in audio
        
        Args:
            video_path: Path to video file
            noise_threshold_db: Volume threshold for silence (dB)
            min_silence_duration: Minimum silence duration (seconds)
            
        Returns:
            List of silence periods with start/end times
        """
        logger.info(f"Detecting silence in {video_path.name}")
        
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-af', f'silencedetect=noise={noise_threshold_db}dB:d={min_silence_duration}',
            '-f', 'null',
            '-'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse silence detection output
            silences = []
            current_silence = {}
            
            for line in result.stderr.split('\n'):
                if 'silence_start:' in line:
                    try:
                        time = float(line.split('silence_start:')[1].strip())
                        current_silence = {'start': time}
                    except (IndexError, ValueError):
                        pass
                        
                elif 'silence_end:' in line and current_silence:
                    try:
                        parts = line.split('silence_end:')[1].strip().split('|')
                        time = float(parts[0].strip())
                        duration = float(parts[1].split('silence_duration:')[1].strip())
                        
                        current_silence['end'] = time
                        current_silence['duration'] = duration
                        silences.append(current_silence)
                        current_silence = {}
                    except (IndexError, ValueError):
                        pass
            
            logger.success(f"✓ Detected {len(silences)} silence periods")
            return silences
            
        except Exception as e:
            logger.error(f"Silence detection failed: {e}")
            return []
    
    def detect_audio_peaks(
        self,
        video_path: Path,
        threshold_percentile: float = 90.0
    ) -> List[Dict]:
        """
        Detect audio peaks/loud moments
        
        Args:
            video_path: Path to video file
            threshold_percentile: Percentile threshold for peaks
            
        Returns:
            List of peak timestamps
        """
        logger.info(f"Detecting audio peaks in {video_path.name}")
        
        # Use astats filter to get detailed audio statistics
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-af', 'astats=metadata=1:reset=1,ametadata=print:file=-',
            '-f', 'null',
            '-'
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Parse for high RMS values
            peaks = []
            current_time = 0.0
            
            for line in result.stderr.split('\n'):
                if 'lavfi.astats.Overall.RMS_level' in line:
                    try:
                        rms = float(line.split('=')[1].strip())
                        if rms > -10.0:  # High volume threshold
                            peaks.append({
                                'timestamp': current_time,
                                'rms_level': rms
                            })
                    except (IndexError, ValueError):
                        pass
                        
                if 'pts_time:' in line:
                    try:
                        current_time = float(line.split('pts_time:')[1].split()[0])
                    except (IndexError, ValueError):
                        pass
            
            logger.success(f"✓ Detected {len(peaks)} audio peaks")
            return peaks
            
        except Exception as e:
            logger.warning(f"Peak detection failed, using alternative method: {e}")
            return self._detect_peaks_alternative(video_path)
    
    def _detect_peaks_alternative(self, video_path: Path) -> List[Dict]:
        """Alternative peak detection method"""
        # Simpler approach: segment the audio and measure volume
        duration = self._get_duration(video_path)
        segment_size = 2.0  # 2-second segments
        peaks = []
        
        num_segments = int(duration / segment_size)
        
        for i in range(num_segments):
            start_time = i * segment_size
            cmd = [
                'ffmpeg',
                '-ss', str(start_time),
                '-i', str(video_path),
                '-t', str(segment_size),
                '-af', 'volumedetect',
                '-f', 'null',
                '-'
            ]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                for line in result.stderr.split('\n'):
                    if 'mean_volume:' in line:
                        vol = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                        if vol > -20.0:  # High volume
                            peaks.append({
                                'timestamp': start_time + segment_size / 2,
                                'mean_volume': vol
                            })
            except:
                continue
        
        return peaks
    
    def _get_duration(self, video_path: Path) -> float:
        """Get video duration"""
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'json',
            str(video_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return float(data['format']['duration'])
        except:
            pass
        
        return 0.0
    
    def analyze_audio_comprehensive(
        self,
        video_path: Path
    ) -> Dict:
        """
        Comprehensive audio analysis
        
        Args:
            video_path: Path to video file
            
        Returns:
            Complete audio analysis report
        """
        logger.info(f"Performing comprehensive audio analysis for {video_path.name}")
        
        analysis = {
            'video_path': str(video_path),
            'video_name': video_path.name
        }
        
        # Volume levels
        try:
            analysis['volume_levels'] = self.analyze_volume_levels(video_path)
        except Exception as e:
            logger.error(f"Volume analysis failed: {e}")
            analysis['volume_levels'] = []
        
        # Silence detection
        try:
            analysis['silence_periods'] = self.detect_silence(video_path)
        except Exception as e:
            logger.error(f"Silence detection failed: {e}")
            analysis['silence_periods'] = []
        
        # Peak detection
        try:
            analysis['audio_peaks'] = self.detect_audio_peaks(video_path)
        except Exception as e:
            logger.error(f"Peak detection failed: {e}")
            analysis['audio_peaks'] = []
        
        # Summary stats
        analysis['num_silence_periods'] = len(analysis['silence_periods'])
        analysis['num_peaks'] = len(analysis['audio_peaks'])
        analysis['total_silence_duration'] = sum(
            s.get('duration', 0) for s in analysis['silence_periods']
        )
        
        logger.success("✓ Comprehensive audio analysis complete")
        return analysis


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python audio_analyzer.py <video_file>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    
    if not video_path.exists():
        print(f"Video file not found: {video_path}")
        sys.exit(1)
    
    # Test audio analysis
    analyzer = AudioAnalyzer()
    
    print("\n" + "="*60)
    print("AUDIO ANALYSIS TEST")
    print("="*60)
    
    # Comprehensive analysis
    analysis = analyzer.analyze_audio_comprehensive(video_path)
    
    print(f"\nVideo: {analysis['video_name']}")
    print(f"\nVolume Levels:")
    for vol in analysis['volume_levels']:
        print(f"  Mean: {vol.get('mean_volume', 'N/A')} dB")
        print(f"  Max: {vol.get('max_volume', 'N/A')} dB")
    
    print(f"\nSilence Periods: {analysis['num_silence_periods']}")
    for i, silence in enumerate(analysis['silence_periods'][:5]):
        print(f"  {i+1}. {silence['start']:.2f}s - {silence['end']:.2f}s ({silence['duration']:.2f}s)")
    
    print(f"\nAudio Peaks: {analysis['num_peaks']}")
    for i, peak in enumerate(analysis['audio_peaks'][:5]):
        print(f"  {i+1}. {peak['timestamp']:.2f}s")
    
    print(f"\nTotal silence duration: {analysis['total_silence_duration']:.2f}s")
