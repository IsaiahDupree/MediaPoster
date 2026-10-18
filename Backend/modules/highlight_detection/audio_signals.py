"""
Audio Signal Processing
Identifies audio patterns that indicate highlight moments
"""
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from loguru import logger
import statistics


class AudioSignalProcessor:
    """Process audio signals to identify highlight-worthy moments"""
    
    def __init__(self):
        """Initialize audio signal processor"""
        logger.info("Audio signal processor initialized")
    
    def detect_volume_spikes(
        self,
        video_path: Path,
        threshold_percentile: float = 85.0,
        window_size: float = 2.0
    ) -> List[Dict]:
        """
        Detect sudden volume increases (excitement, emphasis)
        
        Args:
            video_path: Path to video file
            threshold_percentile: Percentile for spike detection
            window_size: Analysis window in seconds
            
        Returns:
            List of volume spike events with timestamps
        """
        logger.info(f"Detecting volume spikes in {video_path.name}")
        
        # Analyze volume in segments
        duration = self._get_duration(video_path)
        num_segments = int(duration / window_size)
        
        volumes = []
        spikes = []
        
        for i in range(num_segments):
            start_time = i * window_size
            volume = self._measure_segment_volume(video_path, start_time, window_size)
            
            if volume is not None:
                volumes.append({
                    'timestamp': start_time + window_size / 2,
                    'volume': volume,
                    'segment': i
                })
        
        if not volumes:
            return []
        
        # Calculate threshold from percentile
        volume_values = [v['volume'] for v in volumes]
        threshold = self._percentile(volume_values, threshold_percentile)
        
        # Identify spikes
        for i, vol_data in enumerate(volumes):
            if vol_data['volume'] >= threshold:
                # Check if this is a local maximum
                is_peak = True
                for j in range(max(0, i-1), min(len(volumes), i+2)):
                    if j != i and volumes[j]['volume'] > vol_data['volume']:
                        is_peak = False
                        break
                
                if is_peak:
                    spikes.append({
                        'timestamp': vol_data['timestamp'],
                        'volume': vol_data['volume'],
                        'relative_intensity': vol_data['volume'] / statistics.mean(volume_values),
                        'type': 'volume_spike'
                    })
        
        logger.success(f"✓ Detected {len(spikes)} volume spikes")
        return spikes
    
    def detect_speech_emphasis(
        self,
        transcript: Dict,
        audio_peaks: List[Dict]
    ) -> List[Dict]:
        """
        Detect emphasized speech (correlate peaks with words)
        
        Args:
            transcript: Whisper transcript with word timestamps
            audio_peaks: Audio peak events
            
        Returns:
            Emphasized speech segments
        """
        logger.info("Detecting speech emphasis patterns")
        
        if 'words' not in transcript or not audio_peaks:
            return []
        
        emphasized = []
        words = transcript['words']
        
        for peak in audio_peaks:
            # Find words near this peak
            nearby_words = [
                w for w in words
                if abs(w.get('start', 0) - peak['timestamp']) < 1.0
            ]
            
            if nearby_words:
                # Get the text around emphasis
                text = ' '.join([w.get('word', '') for w in nearby_words])
                
                emphasized.append({
                    'timestamp': peak['timestamp'],
                    'text': text.strip(),
                    'intensity': peak.get('volume', 0) if 'volume' in peak else 1.0,
                    'type': 'emphasized_speech'
                })
        
        logger.success(f"✓ Detected {len(emphasized)} emphasis points")
        return emphasized
    
    def detect_laughter_applause(
        self,
        video_path: Path,
        min_duration: float = 0.5
    ) -> List[Dict]:
        """
        Detect laughter, applause, or audience reactions
        Uses spectral analysis to identify characteristic patterns
        
        Args:
            video_path: Path to video file
            min_duration: Minimum duration for reaction
            
        Returns:
            Detected reaction events
        """
        logger.info(f"Detecting audience reactions in {video_path.name}")
        
        # Use FFmpeg's silencedetect in reverse - find non-speech high-frequency events
        # This is a simplified approach; could be enhanced with ML models
        
        reactions = []
        
        # Detect high-frequency bursts (characteristic of laughter/applause)
        cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-af', 'highpass=f=1000,volumedetect',
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
            
            # Parse for high-energy high-frequency events
            # This is a heuristic approach
            for line in result.stderr.split('\n'):
                if 'mean_volume:' in line:
                    try:
                        volume = float(line.split('mean_volume:')[1].split('dB')[0].strip())
                        if volume > -20.0:  # High volume in high frequencies
                            reactions.append({
                                'timestamp': 0.0,  # Would need more sophisticated parsing
                                'type': 'possible_reaction',
                                'confidence': 0.6
                            })
                    except:
                        pass
            
            logger.info(f"Detected {len(reactions)} possible reactions (heuristic)")
            return reactions
            
        except Exception as e:
            logger.warning(f"Reaction detection limited: {e}")
            return []
    
    def calculate_energy_curve(
        self,
        video_path: Path,
        window_size: float = 1.0
    ) -> List[Dict]:
        """
        Calculate audio energy over time
        
        Args:
            video_path: Path to video file
            window_size: Window size for energy calculation
            
        Returns:
            Energy values over time
        """
        logger.info(f"Calculating energy curve for {video_path.name}")
        
        duration = self._get_duration(video_path)
        num_windows = int(duration / window_size)
        
        energy_curve = []
        
        for i in range(num_windows):
            start_time = i * window_size
            volume = self._measure_segment_volume(video_path, start_time, window_size)
            
            if volume is not None:
                # Convert dB to relative energy (0-1 scale)
                # Typical range: -60dB (quiet) to 0dB (loud)
                energy = max(0, (volume + 60) / 60.0)
                
                energy_curve.append({
                    'timestamp': start_time + window_size / 2,
                    'energy': energy,
                    'volume_db': volume
                })
        
        logger.success(f"✓ Generated energy curve with {len(energy_curve)} points")
        return energy_curve
    
    def find_energy_peaks(
        self,
        energy_curve: List[Dict],
        prominence_threshold: float = 0.3
    ) -> List[Dict]:
        """
        Find peaks in energy curve (exciting moments)
        
        Args:
            energy_curve: Energy values over time
            prominence_threshold: Minimum prominence for peaks
            
        Returns:
            Peak events
        """
        if len(energy_curve) < 3:
            return []
        
        peaks = []
        
        for i in range(1, len(energy_curve) - 1):
            current = energy_curve[i]['energy']
            prev = energy_curve[i - 1]['energy']
            next_val = energy_curve[i + 1]['energy']
            
            # Check if this is a local maximum
            if current > prev and current > next_val:
                # Calculate prominence (how much it stands out)
                local_min = min(prev, next_val)
                prominence = current - local_min
                
                if prominence >= prominence_threshold:
                    peaks.append({
                        'timestamp': energy_curve[i]['timestamp'],
                        'energy': current,
                        'prominence': prominence,
                        'type': 'energy_peak'
                    })
        
        logger.info(f"Found {len(peaks)} energy peaks")
        return peaks
    
    def detect_tempo_changes(
        self,
        energy_curve: List[Dict],
        window: int = 5
    ) -> List[Dict]:
        """
        Detect changes in audio tempo/pacing
        
        Args:
            energy_curve: Energy values over time
            window: Window size for tempo calculation
            
        Returns:
            Tempo change events
        """
        if len(energy_curve) < window * 2:
            return []
        
        changes = []
        
        for i in range(window, len(energy_curve) - window):
            # Calculate variance in previous and next windows
            prev_window = [energy_curve[j]['energy'] for j in range(i - window, i)]
            next_window = [energy_curve[j]['energy'] for j in range(i, i + window)]
            
            prev_var = statistics.variance(prev_window) if len(prev_window) > 1 else 0
            next_var = statistics.variance(next_window) if len(next_window) > 1 else 0
            
            # Significant change in variance = tempo change
            if prev_var > 0 and abs(next_var - prev_var) / prev_var > 0.5:
                changes.append({
                    'timestamp': energy_curve[i]['timestamp'],
                    'from_tempo': 'high' if prev_var > next_var else 'low',
                    'to_tempo': 'high' if next_var > prev_var else 'low',
                    'type': 'tempo_change'
                })
        
        logger.info(f"Detected {len(changes)} tempo changes")
        return changes
    
    def score_audio_highlights(
        self,
        timestamps: List[float],
        audio_events: List[Dict]
    ) -> List[float]:
        """
        Score timestamps based on audio events
        
        Args:
            timestamps: Candidate highlight timestamps
            audio_events: All detected audio events
            
        Returns:
            Scores for each timestamp (0-1)
        """
        scores = []
        
        for ts in timestamps:
            score = 0.0
            
            # Check proximity to audio events
            for event in audio_events:
                event_ts = event['timestamp']
                distance = abs(ts - event_ts)
                
                # Events within 2 seconds contribute to score
                if distance < 2.0:
                    proximity_score = 1.0 - (distance / 2.0)
                    
                    # Weight by event type
                    if event['type'] == 'volume_spike':
                        score += proximity_score * 0.4
                    elif event['type'] == 'energy_peak':
                        score += proximity_score * 0.3
                    elif event['type'] == 'emphasized_speech':
                        score += proximity_score * 0.2
                    elif event['type'] == 'tempo_change':
                        score += proximity_score * 0.1
            
            scores.append(min(score, 1.0))
        
        return scores
    
    def _measure_segment_volume(
        self,
        video_path: Path,
        start_time: float,
        duration: float
    ) -> Optional[float]:
        """Measure average volume of a video segment"""
        cmd = [
            'ffmpeg',
            '-ss', str(start_time),
            '-i', str(video_path),
            '-t', str(duration),
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
                    volume_str = line.split('mean_volume:')[1].split('dB')[0].strip()
                    return float(volume_str)
        except:
            pass
        
        return None
    
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
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = int(len(sorted_values) * (percentile / 100.0))
        index = min(index, len(sorted_values) - 1)
        
        return sorted_values[index]


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python audio_signals.py <video_file>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    
    if not video_path.exists():
        print(f"Video file not found: {video_path}")
        sys.exit(1)
    
    # Test audio signal processing
    processor = AudioSignalProcessor()
    
    print("\n" + "="*60)
    print("AUDIO SIGNAL PROCESSING TEST")
    print("="*60)
    
    # Detect volume spikes
    print("\n1. Detecting volume spikes...")
    spikes = processor.detect_volume_spikes(video_path)
    print(f"✓ Found {len(spikes)} volume spikes")
    for i, spike in enumerate(spikes[:5]):
        print(f"  Spike {i+1}: {spike['timestamp']:.1f}s (intensity: {spike['relative_intensity']:.2f}x)")
    
    # Calculate energy curve
    print("\n2. Calculating energy curve...")
    energy_curve = processor.calculate_energy_curve(video_path, window_size=0.5)
    print(f"✓ Generated {len(energy_curve)} energy points")
    
    # Find energy peaks
    print("\n3. Finding energy peaks...")
    peaks = processor.find_energy_peaks(energy_curve)
    print(f"✓ Found {len(peaks)} energy peaks")
    for i, peak in enumerate(peaks[:5]):
        print(f"  Peak {i+1}: {peak['timestamp']:.1f}s (energy: {peak['energy']:.2f})")
    
    # Detect tempo changes
    print("\n4. Detecting tempo changes...")
    tempo_changes = processor.detect_tempo_changes(energy_curve)
    print(f"✓ Found {len(tempo_changes)} tempo changes")
