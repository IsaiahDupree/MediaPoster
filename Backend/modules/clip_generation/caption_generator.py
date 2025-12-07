"""
Caption Generator
Creates and styles captions for video clips
"""
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from loguru import logger
import re


class CaptionGenerator:
    """Generate and burn captions into video clips"""
    
    # Caption style presets
    STYLES = {
        'viral': {
            'font': 'Arial',
            'font_size': 52,
            'bold': True,
            'color': 'white',
            'border_color': 'black',
            'border_width': 3,
            'bg_color': None,
            'position': 'center',
            'max_chars': 20,
            'uppercase': True
        },
        'minimal': {
            'font': 'Helvetica',
            'font_size': 42,
            'bold': False,
            'color': 'white',
            'border_color': 'black',
            'border_width': 2,
            'bg_color': None,
            'position': 'bottom',
            'max_chars': 30,
            'uppercase': False
        },
        'modern': {
            'font': 'Montserrat-Bold',
            'font_size': 48,
            'bold': True,
            'color': 'yellow',
            'border_color': 'black',
            'border_width': 4,
            'bg_color': 'black@0.5',
            'position': 'center',
            'max_chars': 25,
            'uppercase': True
        }
    }
    
    def __init__(self, style: str = 'viral'):
        """
        Initialize caption generator
        
        Args:
            style: Caption style preset ('viral', 'minimal', 'modern')
        """
        self.style = self.STYLES.get(style, self.STYLES['viral'])
        logger.info(f"Caption generator initialized with '{style}' style")
    
    def create_srt_from_transcript(
        self,
        transcript: Dict,
        start_time: float,
        end_time: float,
        output_path: Optional[Path] = None
    ) -> Path:
        """
        Create SRT file from transcript segment
        
        Args:
            transcript: Full transcript with word timings
            start_time: Clip start time
            end_time: Clip end time
            output_path: Output SRT path
            
        Returns:
            Path to SRT file
        """
        if output_path is None:
            output_path = Path(f"./captions_{start_time:.1f}.srt")
        
        logger.info(f"Creating SRT for {start_time:.1f}s - {end_time:.1f}s")
        
        # Extract relevant segments
        segments = []
        if 'segments' in transcript:
            for seg in transcript['segments']:
                seg_start = seg.get('start', 0)
                seg_end = seg.get('end', seg_start)
                
                # Check if segment overlaps with clip time
                if seg_end >= start_time and seg_start <= end_time:
                    segments.append({
                        'start': max(0, seg_start - start_time),
                        'end': min(end_time - start_time, seg_end - start_time),
                        'text': seg.get('text', '').strip()
                    })
        
        # If no segments, try words
        if not segments and 'words' in transcript:
            segments = self._create_segments_from_words(
                transcript['words'],
                start_time,
                end_time
            )
        
        if not segments:
            logger.warning("No captions found in time range")
            # Create empty SRT
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("")
            return output_path
        
        # Write SRT file
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(segments, 1):
                # Format timestamps
                start_ts = self._format_srt_timestamp(seg['start'])
                end_ts = self._format_srt_timestamp(seg['end'])
                
                # Format text
                text = self._format_caption_text(seg['text'])
                
                # Write SRT entry
                f.write(f"{i}\n")
                f.write(f"{start_ts} --> {end_ts}\n")
                f.write(f"{text}\n\n")
        
        logger.success(f"✓ SRT file created with {len(segments)} captions")
        return output_path
    
    def _create_segments_from_words(
        self,
        words: List[Dict],
        start_time: float,
        end_time: float,
        words_per_segment: int = 3
    ) -> List[Dict]:
        """Create caption segments from word timings"""
        # Filter words in time range
        relevant_words = [
            w for w in words
            if start_time <= w.get('start', 0) <= end_time
        ]
        
        if not relevant_words:
            return []
        
        # Group words into segments
        segments = []
        for i in range(0, len(relevant_words), words_per_segment):
            word_group = relevant_words[i:i+words_per_segment]
            
            seg_start = word_group[0].get('start', 0) - start_time
            seg_end = word_group[-1].get('end', seg_start + 1) - start_time
            seg_text = ' '.join([w.get('word', '') for w in word_group])
            
            segments.append({
                'start': max(0, seg_start),
                'end': seg_end,
                'text': seg_text
            })
        
        return segments
    
    def _format_srt_timestamp(self, seconds: float) -> str:
        """Format seconds as SRT timestamp (00:00:00,000)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
    
    def _format_caption_text(self, text: str) -> str:
        """Format caption text according to style"""
        text = text.strip()
        
        if self.style['uppercase']:
            text = text.upper()
        
        # Split long lines
        max_chars = self.style['max_chars']
        if len(text) > max_chars:
            words = text.split()
            lines = []
            current_line = []
            current_length = 0
            
            for word in words:
                word_length = len(word) + 1  # +1 for space
                if current_length + word_length > max_chars and current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = word_length
                else:
                    current_line.append(word)
                    current_length += word_length
            
            if current_line:
                lines.append(' '.join(current_line))
            
            text = '\n'.join(lines)
        
        return text
    
    def burn_captions(
        self,
        video_path: Path,
        srt_path: Path,
        output_path: Optional[Path] = None,
        style_override: Optional[Dict] = None
    ) -> Path:
        """
        Burn captions into video
        
        Args:
            video_path: Source video
            srt_path: SRT subtitle file
            output_path: Output video path
            style_override: Override style settings
            
        Returns:
            Path to video with burned captions
        """
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_captioned.mp4"
        
        logger.info("Burning captions into video")
        
        # Merge styles
        style = {**self.style, **(style_override or {})}
        
        # Build subtitles filter
        subtitle_filter = self._build_subtitle_filter(srt_path, style)
        
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', subtitle_filter,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'copy',
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg error: {result.stderr}")
                raise Exception(f"Caption burning failed: {result.stderr}")
            
            logger.success(f"✓ Captions burned: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Caption burning failed: {e}")
            raise
    
    def _build_subtitle_filter(self, srt_path: Path, style: Dict) -> str:
        """Build FFmpeg subtitle filter with styling"""
        # Escape path for FFmpeg
        srt_escaped = str(srt_path).replace('\\', '/').replace(':', '\\\\:')
        
        # Build style string
        style_parts = []
        
        style_parts.append(f"FontName={style['font']}")
        style_parts.append(f"FontSize={style['font_size']}")
        style_parts.append(f"PrimaryColour=&H{self._color_to_ass(style['color'])}")
        style_parts.append(f"OutlineColour=&H{self._color_to_ass(style['border_color'])}")
        style_parts.append(f"Outline={style['border_width']}")
        style_parts.append(f"Bold={1 if style['bold'] else 0}")
        
        if style['bg_color']:
            style_parts.append(f"BackColour=&H{self._color_to_ass(style['bg_color'].split('@')[0])}")
        
        # Alignment (2=bottom, 5=center, 8=top)
        alignment = {'bottom': 2, 'center': 5, 'top': 8}.get(style['position'], 5)
        style_parts.append(f"Alignment={alignment}")
        
        style_string = ','.join(style_parts)
        
        # Build filter
        return f"subtitles={srt_escaped}:force_style='{style_string}'"
    
    def _color_to_ass(self, color: str) -> str:
        """Convert color name to ASS format (BGR)"""
        colors = {
            'white': 'FFFFFF',
            'black': '000000',
            'red': '0000FF',
            'green': '00FF00',
            'blue': 'FF0000',
            'yellow': '00FFFF',
            'cyan': 'FFFF00',
            'magenta': 'FF00FF'
        }
        
        bgr = colors.get(color.lower(), 'FFFFFF')
        
        # Convert RGB to BGR
        if len(bgr) == 6:
            r, g, b = bgr[0:2], bgr[2:4], bgr[4:6]
            return f"{b}{g}{r}"
        
        return bgr
    
    def create_animated_captions(
        self,
        video_path: Path,
        srt_path: Path,
        output_path: Optional[Path] = None,
        animation: str = 'pop'
    ) -> Path:
        """
        Create captions with animation effects
        
        Args:
            video_path: Source video
            srt_path: SRT file
            output_path: Output path
            animation: Animation type ('pop', 'slide', 'fade')
            
        Returns:
            Video with animated captions
        """
        if output_path is None:
            output_path = video_path.parent / f"{video_path.stem}_animated_captions.mp4"
        
        logger.info(f"Creating animated captions: {animation}")
        
        # For animated captions, we'd need to use ASS format with advanced styling
        # This is a simplified version
        
        # Convert SRT to ASS with animations
        ass_path = srt_path.with_suffix('.ass')
        self._convert_srt_to_ass(srt_path, ass_path, animation)
        
        # Burn ASS subtitles
        cmd = [
            'ffmpeg', '-y',
            '-i', str(video_path),
            '-vf', f"ass={ass_path}",
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'copy',
            str(output_path)
        ]
        
        try:
            subprocess.run(cmd, capture_output=True, timeout=600, check=True)
            logger.success(f"✓ Animated captions created: {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Animated captions failed: {e}")
            # Fallback to regular captions
            return self.burn_captions(video_path, srt_path, output_path)
    
    def _convert_srt_to_ass(
        self,
        srt_path: Path,
        ass_path: Path,
        animation: str = 'pop'
    ):
        """Convert SRT to ASS format with animation"""
        # Read SRT
        with open(srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()
        
        # Parse SRT
        entries = self._parse_srt(srt_content)
        
        # Write ASS
        with open(ass_path, 'w', encoding='utf-8') as f:
            # ASS header
            f.write("[Script Info]\n")
            f.write("ScriptType: v4.00+\n")
            f.write("PlayResX: 1080\n")
            f.write("PlayResY: 1920\n\n")
            
            f.write("[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write(f"Style: Default,{self.style['font']},{self.style['font_size']},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,3,0,5,10,10,10,1\n\n")
            
            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
            
            for entry in entries:
                start = self._srt_to_ass_time(entry['start'])
                end = self._srt_to_ass_time(entry['end'])
                text = entry['text'].replace('\n', '\\N')
                
                # Add animation effects
                if animation == 'pop':
                    text = f"{{\\fscx0\\fscy0\\t(0,200,\\fscx100\\fscy100)}}{text}"
                elif animation == 'fade':
                    text = f"{{\\fade(0,200)}}{text}"
                
                f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")
    
    def _parse_srt(self, content: str) -> List[Dict]:
        """Parse SRT content"""
        entries = []
        blocks = content.strip().split('\n\n')
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                time_line = lines[1]
                text = '\n'.join(lines[2:])
                
                # Parse time
                times = time_line.split(' --> ')
                if len(times) == 2:
                    entries.append({
                        'start': times[0],
                        'end': times[1],
                        'text': text
                    })
        
        return entries
    
    def _srt_to_ass_time(self, srt_time: str) -> str:
        """Convert SRT timestamp to ASS format"""
        # SRT: 00:00:10,500
        # ASS: 0:00:10.50
        return srt_time.replace(',', '.')[:-1]  # Remove last digit


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("CAPTION GENERATOR")
    print("="*60)
    print("\nThis module creates and burns captions into videos.")
    print("Requires: video file + transcript JSON")
    print("\nFor end-to-end testing, use test_phase3.py")
