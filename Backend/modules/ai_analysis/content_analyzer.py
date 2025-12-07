"""
Content Analyzer
Combines all AI analysis modules for comprehensive video understanding
"""
from pathlib import Path
from typing import Dict, Optional
from loguru import logger
import json

from .whisper_service import WhisperService
from .frame_extractor import FrameExtractor
from .vision_analyzer import VisionAnalyzer
from .audio_analyzer import AudioAnalyzer


class ContentAnalyzer:
    """
    Main content analysis orchestrator
    Combines transcription, visual analysis, and audio analysis
    """
    
    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        output_dir: Optional[Path] = None
    ):
        """
        Initialize content analyzer with all sub-analyzers
        
        Args:
            openai_api_key: OpenAI API key
            output_dir: Directory for temporary files
        """
        self.whisper = WhisperService(api_key=openai_api_key)
        self.frame_extractor = FrameExtractor(output_dir=output_dir)
        self.vision = VisionAnalyzer(api_key=openai_api_key)
        self.audio = AudioAnalyzer()
        
        logger.info("Content analyzer initialized with all modules")
    
    def analyze_video_complete(
        self,
        video_path: Path,
        extract_frames: bool = True,
        analyze_vision: bool = True,
        transcribe_audio: bool = True,
        analyze_audio: bool = True,
        max_frames: int = 15
    ) -> Dict:
        """
        Perform complete video analysis
        
        Args:
            video_path: Path to video file
            extract_frames: Extract and analyze frames
            analyze_vision: Analyze frames with GPT-4 Vision
            transcribe_audio: Transcribe speech
            analyze_audio: Analyze audio characteristics
            max_frames: Maximum number of frames to analyze
            
        Returns:
            Complete analysis report
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        logger.info(f"🎬 Starting complete analysis for: {video_path.name}")
        logger.info("="*60)
        
        analysis = {
            'video_path': str(video_path),
            'video_name': video_path.name,
            'modules_run': []
        }
        
        # 1. Audio Transcription
        if transcribe_audio:
            try:
                logger.info("📝 Step 1/4: Transcribing audio with Whisper...")
                transcript = self.whisper.transcribe_video(video_path)
                analysis['transcript'] = transcript
                analysis['modules_run'].append('whisper_transcription')
                
                logger.success(f"✓ Transcription complete: {len(transcript['text'])} chars")
                
                # Generate SRT file
                srt_path = video_path.parent / f"{video_path.stem}_subtitles.srt"
                self.whisper.generate_srt(transcript, srt_path)
                analysis['srt_file'] = str(srt_path)
                
            except Exception as e:
                logger.error(f"Transcription failed: {e}")
                analysis['transcript'] = {'error': str(e)}
        
        # 2. Frame Extraction
        if extract_frames:
            try:
                logger.info("🎞️  Step 2/4: Extracting key frames...")
                key_frames = self.frame_extractor.extract_key_frames(
                    video_path,
                    threshold=0.3,
                    max_frames=max_frames
                )
                analysis['frames'] = [
                    {
                        'path': str(f['path']),
                        'timestamp': f['timestamp'],
                        'score': f.get('score', 0.0)
                    }
                    for f in key_frames
                ]
                analysis['modules_run'].append('frame_extraction')
                
                logger.success(f"✓ Extracted {len(key_frames)} key frames")
                
            except Exception as e:
                logger.error(f"Frame extraction failed: {e}")
                analysis['frames'] = []
        
        # 3. Visual Analysis
        if analyze_vision and extract_frames and analysis.get('frames'):
            try:
                logger.info("👁️  Step 3/4: Analyzing frames with GPT-4 Vision...")
                
                # Prepare frames for analysis
                frames_to_analyze = [
                    {'path': Path(f['path']), 'timestamp': f['timestamp']}
                    for f in analysis['frames']
                ]
                
                # Analyze frames
                vision_results = self.vision.analyze_frames_batch(
                    frames_to_analyze,
                    prompt="Describe what's happening in this video frame. Focus on key actions, emotions, and visual elements."
                )
                
                analysis['visual_analysis'] = vision_results
                analysis['modules_run'].append('vision_analysis')
                
                logger.success(f"✓ Analyzed {len(vision_results)} frames with GPT-4 Vision")
                
                # Generate video summary
                logger.info("📋 Generating video summary...")
                summary = self.vision.generate_frame_summary(vision_results)
                analysis['video_summary'] = summary
                
            except Exception as e:
                logger.error(f"Visual analysis failed: {e}")
                analysis['visual_analysis'] = []
        
        # 4. Audio Analysis
        if analyze_audio:
            try:
                logger.info("🔊 Step 4/4: Analyzing audio characteristics...")
                audio_analysis = self.audio.analyze_audio_comprehensive(video_path)
                analysis['audio_analysis'] = audio_analysis
                analysis['modules_run'].append('audio_analysis')
                
                logger.success("✓ Audio analysis complete")
                
            except Exception as e:
                logger.error(f"Audio analysis failed: {e}")
                analysis['audio_analysis'] = {}
        
        # 5. Multimodal Synthesis
        logger.info("🧠 Synthesizing multimodal insights...")
        analysis['insights'] = self._generate_insights(analysis)
        
        logger.info("="*60)
        logger.success(f"🎉 Complete analysis finished for {video_path.name}")
        logger.info(f"Modules run: {', '.join(analysis['modules_run'])}")
        
        return analysis
    
    def _generate_insights(self, analysis: Dict) -> Dict:
        """
        Generate high-level insights from all analysis data
        
        Args:
            analysis: Complete analysis data
            
        Returns:
            Synthesized insights
        """
        insights = {}
        
        # Content topics from transcript
        if 'transcript' in analysis and 'text' in analysis['transcript']:
            text = analysis['transcript']['text']
            insights['transcript_length'] = len(text)
            insights['word_count'] = len(text.split())
            
            # Simple keyword extraction (could be enhanced with NLP)
            words = text.lower().split()
            word_freq = {}
            for word in words:
                if len(word) > 4:  # Only longer words
                    word_freq[word] = word_freq.get(word, 0) + 1
            
            top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:10]
            insights['key_topics'] = [word for word, count in top_words]
        
        # Visual themes
        if 'visual_analysis' in analysis:
            insights['frames_analyzed'] = len(analysis['visual_analysis'])
        
        # Audio characteristics
        if 'audio_analysis' in analysis:
            audio = analysis['audio_analysis']
            insights['silence_periods'] = audio.get('num_silence_periods', 0)
            insights['audio_peaks'] = audio.get('num_peaks', 0)
            insights['energy_level'] = 'high' if insights['audio_peaks'] > 5 else 'low'
        
        # Content type estimation
        insights['content_type'] = self._estimate_content_type(analysis)
        
        # Viral potential indicators
        insights['viral_indicators'] = self._identify_viral_indicators(analysis)
        
        return insights
    
    def _estimate_content_type(self, analysis: Dict) -> str:
        """Estimate the type of content"""
        # Simple heuristic based on available data
        if 'transcript' in analysis:
            text = analysis['transcript'].get('text', '').lower()
            
            if any(word in text for word in ['tutorial', 'how to', 'learn', 'guide']):
                return 'educational'
            elif any(word in text for word in ['funny', 'hilarious', 'laugh']):
                return 'comedy'
            elif any(word in text for word in ['review', 'unboxing', 'test']):
                return 'review'
            elif any(word in text for word in ['story', 'happened', 'time']):
                return 'storytelling'
        
        return 'general'
    
    def _identify_viral_indicators(self, analysis: Dict) -> List[str]:
        """Identify potential viral elements"""
        indicators = []
        
        # High energy audio
        if analysis.get('insights', {}).get('audio_peaks', 0) > 5:
            indicators.append('high_energy_audio')
        
        # Multiple scenes (dynamic content)
        if len(analysis.get('frames', [])) > 10:
            indicators.append('dynamic_visuals')
        
        # Good pacing (not too many silences)
        silence_ratio = analysis.get('audio_analysis', {}).get('total_silence_duration', 0)
        duration = analysis.get('transcript', {}).get('duration', 1)
        if silence_ratio / duration < 0.2:  # Less than 20% silence
            indicators.append('good_pacing')
        
        return indicators
    
    def save_analysis(self, analysis: Dict, output_path: Path):
        """
        Save analysis results to JSON file
        
        Args:
            analysis: Analysis results
            output_path: Where to save JSON
        """
        logger.info(f"Saving analysis to {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        logger.success(f"✓ Analysis saved to {output_path}")


# Example usage and testing
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python content_analyzer.py <video_file>")
        sys.exit(1)
    
    video_path = Path(sys.argv[1])
    
    if not video_path.exists():
        print(f"Video file not found: {video_path}")
        sys.exit(1)
    
    # Run complete analysis
    analyzer = ContentAnalyzer()
    
    print("\n" + "="*60)
    print("COMPLETE VIDEO ANALYSIS")
    print("="*60)
    
    analysis = analyzer.analyze_video_complete(
        video_path,
        extract_frames=True,
        analyze_vision=True,
        transcribe_audio=True,
        analyze_audio=True,
        max_frames=10
    )
    
    # Print summary
    print("\n" + "="*60)
    print("ANALYSIS SUMMARY")
    print("="*60)
    
    print(f"\nVideo: {analysis['video_name']}")
    print(f"Modules run: {', '.join(analysis['modules_run'])}")
    
    if 'transcript' in analysis:
        print(f"\n📝 Transcript: {analysis['insights'].get('word_count', 0)} words")
    
    if 'frames' in analysis:
        print(f"🎞️  Frames: {len(analysis['frames'])} extracted")
    
    if 'visual_analysis' in analysis:
        print(f"👁️  Vision: {len(analysis['visual_analysis'])} frames analyzed")
    
    if 'audio_analysis' in analysis:
        print(f"🔊 Audio: {analysis['insights'].get('audio_peaks', 0)} peaks detected")
    
    if 'video_summary' in analysis:
        print(f"\n📋 Summary:\n{analysis['video_summary']}")
    
    print(f"\n🎯 Content Type: {analysis['insights'].get('content_type', 'unknown')}")
    print(f"✨ Viral Indicators: {', '.join(analysis['insights'].get('viral_indicators', []))}")
    
    # Save to JSON
    output_path = video_path.parent / f"{video_path.stem}_analysis.json"
    analyzer.save_analysis(analysis, output_path)
    
    print(f"\n✓ Complete analysis saved to: {output_path}")
