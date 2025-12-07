"""
Visual Enhancer
Adds visual effects, progress bars, emojis, and overlays to clips
"""
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger
import json


class VisualEnhancer:
    """Add visual enhancements to video clips"""
    
    def __init__(self):
        """Initialize visual enhancer"""
        logger.info("Visual enhancer initialized")
    
    def add_progress_bar(
        self,
        video_path: Path,
        output_path: Optional[Path] = None,
        position: str = 'top',
        height: int = 8,
        color: str = 'yellow'
    ) -> Path:
        """
        Add progress bar to video
        
        Args:
            video_path: Source video
            output_path: Output path
            position: 'top' or 'bottom'
            height: Bar height in pixels
            color: Bar color
            
        Returns:
            Video with progress bar
        """
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_progress.mp4"
        
        logger.info(f"Adding {position} progress bar")
        
        # Get video duration
        duration = self._get_duration(video_path)
        
        # Build progress bar filter
        y_pos = '0' if position == 'top' else 'h-height'
        
        # Color mapping
        color_map = {
            'yellow': 'yellow',
            'white': 'white',
            'red': 'red',
            'green': 'green',
            'blue': 'blue'
        }
        bar_color = color_map.get(color, 'yellow')
        
        # Progress bar filter using drawbox
        filter_str = (
            f"drawbox=x=0:y={y_pos}:"
            f"w='w*t/{duration}':h={height}:"
            f"color={bar_color}:t=fill"
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', filter_str,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'copy',
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=600, check=True)
            logger.success(f"✓ Progress bar added: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Progress bar failed: {e}")
            raise
    
    def add_text_overlay(
        self,
        video_path: Path,
        text: str,
        output_path: Optional[Path] = None,
        position: str = 'top',
        font_size: int = 60,
        font_color: str = 'white',
        duration: Optional[float] = None,
        start_time: float = 0.0
    ) -> Path:
        """
        Add text overlay to video
        
        Args:
            video_path: Source video
            text: Text to overlay
            output_path: Output path
            position: 'top', 'center', 'bottom'
            font_size: Font size
            font_color: Text color
            duration: How long to show text (None = entire video)
            start_time: When to start showing text
            
        Returns:
            Video with text overlay
        """
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_text.mp4"
        
        logger.info(f"Adding text overlay: {text[:30]}...")
        
        # Position mapping
        positions = {
            'top': '(w-text_w)/2:50',
            'center': '(w-text_w)/2:(h-text_h)/2',
            'bottom': '(w-text_w)/2:h-150'
        }
        
        xy = positions.get(position, positions['center'])
        
        # Escape text for FFmpeg
        text_escaped = text.replace(':', '\\:').replace("'", "\\'")
        
        # Build drawtext filter
        filter_parts = [
            f"text='{text_escaped}'",
            f"fontsize={font_size}",
            f"fontcolor={font_color}",
            f"x={xy.split(':')[0]}",
            f"y={xy.split(':')[1]}",
            "borderw=3",
            "bordercolor=black",
            "fontfile=/System/Library/Fonts/Supplemental/Arial Bold.ttf"
        ]
        
        # Add timing if specified
        if duration:
            end_time = start_time + duration
            filter_parts.append(f"enable='between(t,{start_time},{end_time})'")
        elif start_time > 0:
            filter_parts.append(f"enable='gte(t,{start_time})'")
        
        filter_str = "drawtext=" + ":".join(filter_parts)
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', filter_str,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'copy',
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=600, check=True)
            logger.success(f"✓ Text overlay added: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Text overlay failed: {e}")
            raise
    
    def add_emoji_overlay(
        self,
        video_path: Path,
        emoji: str,
        output_path: Optional[Path] = None,
        position: Tuple[int, int] = (50, 50),
        size: int = 100,
        duration: Optional[float] = None,
        start_time: float = 0.0
    ) -> Path:
        """
        Add emoji overlay (simplified - uses text)
        
        Args:
            video_path: Source video
            emoji: Emoji character
            output_path: Output path
            position: (x, y) position
            size: Emoji size
            duration: Duration to show
            start_time: Start time
            
        Returns:
            Video with emoji
        """
        logger.info(f"Adding emoji: {emoji}")
        
        # Use text overlay with emoji
        return self.add_text_overlay(
            video_path,
            emoji,
            output_path,
            position='top',
            font_size=size,
            duration=duration,
            start_time=start_time
        )
    
    def add_zoom_effect(
        self,
        video_path: Path,
        output_path: Optional[Path] = None,
        zoom_factor: float = 1.2,
        duration_pct: float = 100.0
    ) -> Path:
        """
        Add zoom effect
        
        Args:
            video_path: Source video
            output_path: Output path
            zoom_factor: How much to zoom (1.0 = no zoom, 2.0 = 2x)
            duration_pct: Percentage of video to apply zoom
            
        Returns:
            Video with zoom effect
        """
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_zoom.mp4"
        
        logger.info(f"Adding zoom effect: {zoom_factor}x")
        
        duration = self._get_duration(video_path)
        zoom_duration = duration * (duration_pct / 100.0)
        
        # Zoom filter (zoompan)
        filter_str = (
            f"zoompan=z='min(zoom+0.0015,{zoom_factor})':"
            f"d={int(zoom_duration * 25)}:"  # frames
            "x='iw/2-(iw/zoom/2)':"
            "y='ih/2-(ih/zoom/2)':"
            "s=1080x1920"
        )
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', filter_str,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'copy',
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=600, check=True)
            logger.success(f"✓ Zoom effect added: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Zoom effect failed: {e}")
            raise
    
    def add_vignette(
        self,
        video_path: Path,
        output_path: Optional[Path] = None,
        intensity: float = 0.3
    ) -> Path:
        """
        Add vignette effect (darkened edges)
        
        Args:
            video_path: Source video
            output_path: Output path
            intensity: Vignette intensity (0.0-1.0)
            
        Returns:
            Video with vignette
        """
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_vignette.mp4"
        
        logger.info(f"Adding vignette: {intensity}")
        
        filter_str = f"vignette=PI/{intensity}"
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', filter_str,
            '-c:v', 'libx264',
            '-c:a', 'copy',
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=600, check=True)
            logger.success(f"✓ Vignette added: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Vignette failed: {e}")
            raise
    
    def add_filter(
        self,
        video_path: Path,
        filter_name: str,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Add color filter/LUT
        
        Args:
            video_path: Source video
            filter_name: 'warm', 'cool', 'vibrant', 'vintage'
            output_path: Output path
            
        Returns:
            Filtered video
        """
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_{filter_name}.mp4"
        
        logger.info(f"Adding {filter_name} filter")
        
        # Filter mappings
        filters = {
            'warm': 'eq=saturation=1.3:gamma=1.1,colorbalance=rs=0.1:gs=0.05',
            'cool': 'eq=saturation=1.2:gamma=0.9,colorbalance=bs=0.1',
            'vibrant': 'eq=saturation=1.5:contrast=1.1',
            'vintage': 'curves=vintage,vignette=PI/0.4'
        }
        
        filter_str = filters.get(filter_name, filters['vibrant'])
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', filter_str,
            '-c:v', 'libx264',
            '-c:a', 'copy',
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=600, check=True)
            logger.success(f"✓ Filter applied: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Filter failed: {e}")
            raise
    
    def combine_effects(
        self,
        video_path: Path,
        effects: List[Dict],
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Combine multiple effects in one pass
        
        Args:
            video_path: Source video
            effects: List of effect configs
            output_path: Output path
            
        Returns:
            Video with all effects
        """
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_enhanced.mp4"
        
        logger.info(f"Combining {len(effects)} effects")
        
        # Build complex filter
        filters = []
        
        for effect in effects:
            effect_type = effect.get('type')
            
            if effect_type == 'progress_bar':
                height = effect.get('height', 8)
                position = effect.get('position', 'top')
                color = effect.get('color', 'yellow')
                y_pos = '0' if position == 'top' else 'h-height'
                duration = self._get_duration(video_path)
                filters.append(
                    f"drawbox=x=0:y={y_pos}:w='w*t/{duration}':h={height}:color={color}:t=fill"
                )
            
            elif effect_type == 'text':
                text = effect.get('text', '')
                position = effect.get('position', 'top')
                font_size = effect.get('font_size', 60)
                text_escaped = text.replace(':', '\\:').replace("'", "\\'")
                
                positions = {
                    'top': '(w-text_w)/2:50',
                    'center': '(w-text_w)/2:(h-text_h)/2',
                    'bottom': '(w-text_w)/2:h-150'
                }
                xy = positions.get(position, positions['top'])
                
                filters.append(
                    f"drawtext=text='{text_escaped}':fontsize={font_size}:"
                    f"fontcolor=white:x={xy.split(':')[0]}:y={xy.split(':')[1]}:"
                    "borderw=3:bordercolor=black"
                )
            
            elif effect_type == 'vignette':
                intensity = effect.get('intensity', 0.3)
                filters.append(f"vignette=PI/{intensity}")
            
            elif effect_type == 'filter':
                filter_name = effect.get('name', 'vibrant')
                filter_map = {
                    'warm': 'eq=saturation=1.3:gamma=1.1',
                    'cool': 'eq=saturation=1.2:gamma=0.9',
                    'vibrant': 'eq=saturation=1.5:contrast=1.1',
                    'vintage': 'curves=vintage'
                }
                if filter_name in filter_map:
                    filters.append(filter_map[filter_name])
        
        if not filters:
            logger.warning("No valid effects to apply")
            return video_path
        
        # Combine all filters
        filter_complex = ','.join(filters)
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', filter_complex,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'copy',
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=600, check=True)
            logger.success(f"✓ Effects combined: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Effect combination failed: {e}")
            raise
    
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
                timeout=30,
                check=True
            )
            
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
        except:
            return 0.0


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("VISUAL ENHANCER")
    print("="*60)
    print("\nThis module adds visual effects to videos.")
    print("For end-to-end testing, use test_phase3.py")
