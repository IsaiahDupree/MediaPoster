"""
Clip Assembler
Orchestrates the complete clip generation pipeline
"""
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger

from .video_editor import VideoEditor
from .caption_generator import CaptionGenerator
from .hook_generator import HookGenerator
from .visual_enhancer import VisualEnhancer
from .music_selector import MusicSelector
from .audio_mixer import AudioMixer


class ClipAssembler:
    """Assemble complete viral-ready clips from highlights"""
    
    TEMPLATES = {
        'viral_basic': {
            'captions': True,
            'hook': True,
            'progress_bar': True,
            'effects': ['vibrant'],
            'vertical': True
        },
        'clean': {
            'captions': True,
            'hook': False,
            'progress_bar': False,
            'effects': [],
            'vertical': True
        },
        'maximum': {
            'captions': True,
            'hook': True,
            'progress_bar': True,
            'effects': ['vibrant', 'vignette'],
            'vertical': True,
            'zoom': 1.1
        },
        'minimal': {
            'captions': False,
            'hook': False,
            'progress_bar': False,
            'effects': [],
            'vertical': True
        }
    }
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize clip assembler
        
        Args:
            output_dir: Directory for output clips
        """
        self.output_dir = output_dir or Path("./generated_clips")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize sub-components
        self.editor = VideoEditor(self.output_dir / "temp")
        self.caption_gen = CaptionGenerator(style='viral')
        self.hook_gen = HookGenerator()
        self.enhancer = VisualEnhancer()
        self.music_selector = MusicSelector()
        self.audio_mixer = AudioMixer()
        
        logger.info(f"Clip assembler initialized with music support, output: {self.output_dir}")
    
    def create_clip(
        self,
        video_path: Path,
        highlight: Dict,
        transcript: Optional[Dict] = None,
        video_context: Optional[Dict] = None,
        template: str = 'viral_basic',
        platform: str = 'tiktok',
        add_music: bool = False,
        music_track_id: Optional[str] = None,
        music_volume: float = 0.3
    ) -> Dict:
        """
        Create a complete clip from a highlight
        
        Args:
            video_path: Source video path
            highlight: Highlight data with start/end times
            transcript: Full transcript (for captions)
            video_context: Video metadata (for hooks)
            template: Template name or 'custom'
            platform: Target platform
            
        Returns:
            Dictionary with clip paths and metadata
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"CREATING CLIP: {highlight['start']:.1f}s - {highlight['end']:.1f}s")
        logger.info(f"{'='*60}")
        
        # Get template config
        config = self.TEMPLATES.get(template, self.TEMPLATES['viral_basic'])
        
        # Step 1: Extract base clip
        logger.info("\n📹 Step 1/6: Extracting clip...")
        clip_path = self.editor.extract_clip(
            video_path,
            start_time=highlight['start'],
            duration=highlight['duration']
        )
        current_path = clip_path
        
        # Step 2: Convert to vertical
        if config.get('vertical'):
            logger.info("\n📐 Step 2/6: Converting to vertical (9:16)...")
            vertical_path = self.editor.convert_to_vertical(
                current_path,
                crop_mode='blur'
            )
            current_path = vertical_path
        else:
            logger.info("\n📐 Step 2/6: Skipping vertical conversion")
        
        # Step 3: Add captions
        srt_path = None
        if config.get('captions') and transcript:
            logger.info("\n💬 Step 3/6: Adding captions...")
            try:
                srt_path = self.caption_gen.create_srt_from_transcript(
                    transcript,
                    start_time=highlight['start'],
                    end_time=highlight['end'],
                    output_path=self.output_dir / "temp" / "captions.srt"
                )
                
                captioned_path = self.caption_gen.burn_captions(
                    current_path,
                    srt_path,
                    output_path=self.output_dir / "temp" / f"{current_path.stem}_captioned.mp4"
                )
                current_path = captioned_path
            except Exception as e:
                logger.warning(f"Captions failed: {e}")
        else:
            logger.info("\n💬 Step 3/6: Skipping captions")
        
        # Step 4: Generate and add hook
        hook_data = None
        if config.get('hook') and video_context:
            logger.info("\n🎯 Step 4/6: Generating hook...")
            try:
                hooks = self.hook_gen.generate_hooks(
                    highlight,
                    video_context,
                    count=3
                )
                
                if hooks:
                    hook_data = hooks[0]  # Use best hook
                    logger.info(f"   Hook: {hook_data['text']}")
                    
                    # Add hook as text overlay
                    hooked_path = self.enhancer.add_text_overlay(
                        current_path,
                        hook_data['text'],
                        output_path=self.output_dir / "temp" / f"{current_path.stem}_hooked.mp4",
                        position='top',
                        font_size=56,
                        duration=3.0  # Show for first 3 seconds
                    )
                    current_path = hooked_path
            except Exception as e:
                logger.warning(f"Hook generation failed: {e}")
        else:
            logger.info("\n🎯 Step 4/6: Skipping hook")
        
        # Step 5: Add visual effects
        if config.get('effects') or config.get('progress_bar'):
            logger.info("\n✨ Step 5/6: Adding visual effects...")
            try:
                effects_list = []
                
                # Add progress bar
                if config.get('progress_bar'):
                    effects_list.append({
                        'type': 'progress_bar',
                        'position': 'top',
                        'height': 8,
                        'color': 'yellow'
                    })
                
                # Add filters
                for effect_name in config.get('effects', []):
                    if effect_name == 'vibrant':
                        effects_list.append({
                            'type': 'filter',
                            'name': 'vibrant'
                        })
                    elif effect_name == 'vignette':
                        effects_list.append({
                            'type': 'vignette',
                            'intensity': 0.3
                        })
                
                if effects_list:
                    enhanced_path = self.enhancer.combine_effects(
                        current_path,
                        effects_list,
                        output_path=self.output_dir / "temp" / f"{current_path.stem}_enhanced.mp4"
                    )
                    current_path = enhanced_path
            except Exception as e:
                logger.warning(f"Visual effects failed: {e}")
        else:
            logger.info("\n✨ Step 5/6: Skipping effects")
        
        # Step 5.5: Add background music (if requested)
        if add_music:
            logger.info("\n🎵 Step 5.5/7: Adding background music...")
            try:
                # Select music track
                if music_track_id:
                    # Use specified track
                    track = self.music_selector.get_track_by_id(music_track_id)
                    logger.info(f"   Using specified track: {track['title']}")
                else:
                    # AI-powered selection
                    logger.info("   AI selecting best music...")
                    recommended_tracks = self.music_selector.select_music_with_ai(
                        video_context or {},
                        top_n=1
                    )
                    track = recommended_tracks[0] if recommended_tracks else None
                
                if track:
                    logger.info(f"   Selected: {track['title']} ({track['genre']})")
                    logger.info(f"   Confidence: {track.get('confidence', 0.5):.0%}")
                    
                    # Get music file path
                    music_file = Path(track['file'])
                    if not music_file.is_absolute():
                        music_file = Path(__file__).parent.parent.parent / music_file
                    
                    if music_file.exists():
                        # Mix background music
                        music_path = self.output_dir / "temp" / f"{current_path.stem}_with_music.mp4"
                        success = self.audio_mixer.add_background_music(
                            current_path,
                            music_file,
                            music_path,
                            music_volume=music_volume,
                            video_volume=1.0,
                            fade_in_duration=1.0,
                            fade_out_duration=1.0
                        )
                        
                        if success:
                            current_path = music_path
                            logger.success(f"✓ Music added")
                        else:
                            logger.warning("Music mixing failed, continuing without")
                    else:
                        logger.warning(f"Music file not found: {music_file}")
                else:
                    logger.warning("No suitable music track found")
                    
            except Exception as e:
                logger.warning(f"Music addition failed: {e}, continuing without")
        else:
            logger.info("\n🎵 Step 5.5/7: Skipping background music")
        
        # Step 6: Optimize for platform
        logger.info(f"\n🚀 Step 6/7: Optimizing for {platform}...")
        final_name = self._generate_clip_name(highlight, platform)
        final_path = self.output_dir / final_name
        
        try:
            optimized_path = self.editor.optimize_for_social(
                current_path,
                platform=platform,
                output_path=final_path
            )
        except Exception as e:
            logger.warning(f"Optimization failed, using current: {e}")
            # Just copy current to final
            import shutil
            shutil.copy(current_path, final_path)
            optimized_path = final_path
        
        # Generate metadata
        logger.info("\n✅ Clip generation complete!")
        
        metadata = {
            'clip_path': str(optimized_path),
            'duration': highlight['duration'],
            'start_time': highlight['start'],
            'end_time': highlight['end'],
            'platform': platform,
            'template': template,
            'has_captions': config.get('captions', False) and transcript is not None,
            'has_hook': hook_data is not None,
            'hook_text': hook_data['text'] if hook_data else None,
            'file_size_mb': optimized_path.stat().st_size / (1024*1024),
            'config': config
        }
        
        # Generate additional metadata
        if video_context:
            try:
                # Generate hashtags
                hashtags = self.hook_gen.suggest_hashtags(
                    video_context,
                    platform=platform,
                    count=10
                )
                metadata['hashtags'] = hashtags
                
                # Generate CTA
                cta = self.hook_gen.generate_cta(video_context, platform)
                metadata['cta'] = cta['recommended']
            except Exception as e:
                logger.warning(f"Metadata generation failed: {e}")
        
        logger.success(f"\n🎉 CLIP SAVED: {optimized_path}")
        logger.info(f"   Size: {metadata['file_size_mb']:.2f} MB")
        if metadata.get('hook_text'):
            logger.info(f"   Hook: {metadata['hook_text']}")
        
        return metadata
    
    def create_clips_batch(
        self,
        video_path: Path,
        highlights: List[Dict],
        transcript: Optional[Dict] = None,
        video_context: Optional[Dict] = None,
        template: str = 'viral_basic',
        platforms: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Create multiple clips from highlights
        
        Args:
            video_path: Source video
            highlights: List of highlights
            transcript: Full transcript
            video_context: Video metadata
            template: Template to use
            platforms: Target platforms
            
        Returns:
            List of clip metadata
        """
        platforms = platforms or ['tiktok']
        
        logger.info(f"\n{'='*60}")
        logger.info(f"BATCH CLIP GENERATION")
        logger.info(f"Highlights: {len(highlights)}")
        logger.info(f"Platforms: {', '.join(platforms)}")
        logger.info(f"{'='*60}")
        
        all_clips = []
        
        for i, highlight in enumerate(highlights, 1):
            logger.info(f"\n\n{'#'*60}")
            logger.info(f"HIGHLIGHT {i}/{len(highlights)}")
            logger.info(f"{'#'*60}")
            
            for platform in platforms:
                try:
                    clip_meta = self.create_clip(
                        video_path,
                        highlight,
                        transcript,
                        video_context,
                        template,
                        platform
                    )
                    
                    clip_meta['highlight_index'] = i - 1
                    all_clips.append(clip_meta)
                    
                except Exception as e:
                    logger.error(f"Failed to create clip {i} for {platform}: {e}")
                    continue
        
        logger.info(f"\n\n{'='*60}")
        logger.success(f"✅ BATCH COMPLETE: {len(all_clips)} clips created")
        logger.info(f"{'='*60}")
        
        # Save batch metadata
        batch_meta_path = self.output_dir / "batch_metadata.json"
        with open(batch_meta_path, 'w') as f:
            json.dump(all_clips, f, indent=2, default=str)
        
        logger.info(f"📄 Batch metadata saved: {batch_meta_path}")
        
        return all_clips
    
    def _generate_clip_name(
        self,
        highlight: Dict,
        platform: str
    ) -> str:
        """Generate clip filename"""
        start = highlight['start']
        duration = highlight['duration']
        score = highlight.get('composite_score', 0)
        
        return f"clip_{start:.0f}s_{duration:.0f}s_{score:.2f}_{platform}.mp4"
    
    def cleanup_temp_files(self):
        """Clean up temporary files"""
        temp_dir = self.output_dir / "temp"
        if temp_dir.exists():
            import shutil
            shutil.rmtree(temp_dir)
            temp_dir.mkdir(parents=True, exist_ok=True)
            logger.info("✓ Temp files cleaned")


# Example usage
if __name__ == "__main__":
    print("\n" + "="*60)
    print("CLIP ASSEMBLER")
    print("="*60)
    print("\nThis module orchestrates complete clip generation.")
    print("It combines: extraction + vertical + captions + hooks + effects")
    print("\nFor end-to-end testing, use test_phase3.py")
