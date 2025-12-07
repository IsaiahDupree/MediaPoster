"""
Vision Analysis Service
Analyzes video frames using GPT-4 Vision
"""
import openai
import base64
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger

from config import settings


class VisionAnalyzer:
    """Analyze video frames using GPT-4 Vision"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4-vision-preview"
    ):
        """
        Initialize vision analyzer
        
        Args:
            api_key: OpenAI API key (defaults to settings)
            model: GPT model to use (must support vision)
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model
        self.client = openai.OpenAI(api_key=self.api_key)
        
        logger.info(f"Vision analyzer initialized with model: {model}")
    
    def encode_image(self, image_path: Path) -> str:
        """
        Encode image to base64
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded string
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def analyze_frame(
        self,
        image_path: Path,
        prompt: Optional[str] = None,
        detail: str = "auto"
    ) -> Dict:
        """
        Analyze a single frame
        
        Args:
            image_path: Path to image file
            prompt: Custom prompt (or use default)
            detail: Image detail level (low, high, auto)
            
        Returns:
            Analysis result with description
        """
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")
        
        logger.info(f"Analyzing frame: {image_path.name}")
        
        # Default prompt for video frame analysis
        if prompt is None:
            prompt = """Analyze this video frame and provide:
1. A detailed description of what's happening
2. Key objects and people visible
3. Any text or graphics shown
4. The mood/emotion conveyed
5. Notable visual elements

Be concise but thorough."""
        
        # Encode image
        base64_image = self.encode_image(image_path)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}",
                                    "detail": detail
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            result = {
                'image_path': str(image_path),
                'description': response.choices[0].message.content,
                'model': self.model,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
            logger.success(f"✓ Frame analyzed ({result['usage']['total_tokens']} tokens)")
            return result
            
        except Exception as e:
            logger.error(f"Frame analysis failed: {e}")
            raise
    
    def analyze_frames_batch(
        self,
        frames: List[Dict],
        prompt: Optional[str] = None,
        max_concurrent: int = 5
    ) -> List[Dict]:
        """
        Analyze multiple frames (with timestamps)
        
        Args:
            frames: List of dicts with 'path' and 'timestamp'
            prompt: Custom prompt for all frames
            max_concurrent: Maximum concurrent API calls
            
        Returns:
            List of analysis results
        """
        logger.info(f"Analyzing {len(frames)} frames")
        
        results = []
        total_tokens = 0
        
        for i, frame_info in enumerate(frames):
            try:
                analysis = self.analyze_frame(
                    frame_info['path'],
                    prompt=prompt
                )
                
                # Add timestamp info
                analysis['timestamp'] = frame_info.get('timestamp', 0.0)
                analysis['frame_index'] = i
                
                results.append(analysis)
                total_tokens += analysis['usage']['total_tokens']
                
                logger.info(f"Progress: {i+1}/{len(frames)} frames analyzed")
                
            except Exception as e:
                logger.error(f"Failed to analyze frame {i}: {e}")
                results.append({
                    'image_path': str(frame_info['path']),
                    'timestamp': frame_info.get('timestamp', 0.0),
                    'frame_index': i,
                    'error': str(e),
                    'description': None
                })
        
        logger.success(f"✓ Batch analysis complete (total {total_tokens} tokens)")
        return results
    
    def detect_text_in_frame(self, image_path: Path) -> Dict:
        """
        Detect and extract text from a frame
        
        Args:
            image_path: Path to image file
            
        Returns:
            Detected text and locations
        """
        prompt = """Identify and extract ALL text visible in this image.
For each text element, provide:
1. The exact text content
2. Its approximate position (top, center, bottom, etc.)
3. The text style/size (small, medium, large)
4. Whether it's part of UI, captions, or content

List all text found."""
        
        return self.analyze_frame(image_path, prompt=prompt, detail="high")
    
    def identify_viral_elements(self, image_path: Path) -> Dict:
        """
        Identify elements that make content viral
        
        Args:
            image_path: Path to image file
            
        Returns:
            Analysis of viral potential
        """
        prompt = """Analyze this frame for viral content potential:
1. Is there a clear focal point or surprising element?
2. Are there expressive faces or emotions?
3. Is there text overlay or captions?
4. Are there bold colors or high contrast?
5. Is there movement or action implied?
6. Are there any meme-worthy elements?

Rate the viral potential (low/medium/high) and explain why."""
        
        return self.analyze_frame(image_path, prompt=prompt)
    
    def compare_frames(
        self,
        frame1_path: Path,
        frame2_path: Path
    ) -> Dict:
        """
        Compare two frames to detect changes
        
        Args:
            frame1_path: Path to first frame
            frame2_path: Path to second frame
            
        Returns:
            Comparison analysis
        """
        logger.info("Comparing two frames")
        
        base64_image1 = self.encode_image(frame1_path)
        base64_image2 = self.encode_image(frame2_path)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Compare these two video frames. What changed between them? Describe the differences in detail."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image1}",
                                    "detail": "auto"
                                }
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image2}",
                                    "detail": "auto"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            return {
                'frame1': str(frame1_path),
                'frame2': str(frame2_path),
                'comparison': response.choices[0].message.content
            }
            
        except Exception as e:
            logger.error(f"Frame comparison failed: {e}")
            raise
    
    def generate_frame_summary(self, analyses: List[Dict]) -> str:
        """
        Generate overall video summary from frame analyses
        
        Args:
            analyses: List of frame analysis results
            
        Returns:
            Combined summary
        """
        if not analyses:
            return "No frames analyzed"
        
        # Combine all descriptions
        descriptions = [
            f"[{a['timestamp']:.1f}s] {a['description']}"
            for a in analyses
            if a.get('description')
        ]
        
        combined_text = "\n\n".join(descriptions)
        
        # Use GPT to create a cohesive summary
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",  # Use regular GPT-4 for text
                messages=[
                    {
                        "role": "system",
                        "content": "You are a video content analyst. Create a concise summary of a video based on frame-by-frame descriptions."
                    },
                    {
                        "role": "user",
                        "content": f"Create a brief but comprehensive summary of this video based on these timestamped frame descriptions:\n\n{combined_text}\n\nProvide: 1) Overall topic/theme, 2) Key moments, 3) Visual style"
                    }
                ],
                max_tokens=300
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Summary generation failed: {e}")
            return combined_text


# Example usage and testing
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    if len(sys.argv) < 2:
        print("Usage: python vision_analyzer.py <image_file>")
        sys.exit(1)
    
    image_path = Path(sys.argv[1])
    
    if not image_path.exists():
        print(f"Image file not found: {image_path}")
        sys.exit(1)
    
    # Test vision analysis
    analyzer = VisionAnalyzer()
    
    print("\n" + "="*60)
    print("VISION ANALYSIS TEST")
    print("="*60)
    
    # Test 1: Basic frame analysis
    print("\n1. Analyzing frame...")
    result = analyzer.analyze_frame(image_path)
    print(f"\n✓ Analysis complete!")
    print(f"\nDescription:\n{result['description']}")
    print(f"\nTokens used: {result['usage']['total_tokens']}")
    
    # Test 2: Text detection
    print("\n2. Detecting text...")
    text_result = analyzer.detect_text_in_frame(image_path)
    print(f"\nText detection:\n{text_result['description']}")
    
    # Test 3: Viral potential
    print("\n3. Analyzing viral potential...")
    viral_result = analyzer.identify_viral_elements(image_path)
    print(f"\nViral analysis:\n{viral_result['description']}")
