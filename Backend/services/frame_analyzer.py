"""
Frame Analyzer Service
Uses OpenAI Vision to analyze video frames for visual context, objects, and text.
"""
import base64
import os
import logging
from typing import List, Dict, Any
from openai import OpenAI

logger = logging.getLogger(__name__)

class FrameAnalyzer:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        self.client = OpenAI(api_key=self.api_key)

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 string"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def analyze_frames(self, frame_paths: List[str]) -> Dict[str, Any]:
        """
        Analyze a list of video frames using OpenAI Vision.
        Returns a summary of visual content, objects, and text.
        """
        if not frame_paths:
            return {"error": "No frames provided"}

        logger.info(f"Analyzing {len(frame_paths)} frames with OpenAI Vision")

        # Prepare messages with images
        content = [
            {
                "type": "text",
                "text": "Analyze these video frames. Describe the visual setting, key objects, any text on screen, and the overall visual style/mood. Summarize the visual progression."
            }
        ]

        for path in frame_paths:
            if os.path.exists(path):
                base64_image = self._encode_image(path)
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "low" # Low detail is cheaper and usually sufficient for summary
                    }
                })

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o", # Or gpt-4-turbo
                messages=[
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                max_tokens=500
            )
            
            analysis_text = response.choices[0].message.content
            
            # Structured extraction (optional, could be a second pass or structured output)
            # For now, returning the narrative summary
            return {
                "visual_summary": analysis_text,
                "frame_count": len(frame_paths)
            }

        except Exception as e:
            logger.error(f"Frame analysis failed: {e}")
            return {"error": str(e)}
