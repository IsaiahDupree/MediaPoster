#!/usr/bin/env python3
"""
Analyze competitor TikTok videos and generate Sora/Veo3 reproducible prompts.
Downloads top videos, analyzes with GPT-4 Vision, generates prompts, then deletes videos.
"""

import asyncio
import httpx
import json
import os
import sys
import base64
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
import logging
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OUTPUT_DIR = Path("/Users/isaiahdupree/Documents/CompetitorResearch/accounts")


@dataclass
class VideoAnalysis:
    video_id: str
    url: str
    caption: str
    play_count: int
    duration: int
    transcript: str
    visual_analysis: str
    sora_prompt: str
    veo3_prompt: str
    format_breakdown: Dict[str, Any]


class CompetitorPromptGenerator:
    def __init__(self, username: str):
        self.username = username.lstrip('@')
        self.output_dir = OUTPUT_DIR / self.username
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.analyses: List[VideoAnalysis] = []
        
    async def fetch_top_videos(self, count: int = 5) -> List[Dict]:
        """Fetch top performing videos"""
        logger.info(f"Fetching top {count} videos for @{self.username}...")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                "https://tiktok-scraper7.p.rapidapi.com/user/posts",
                headers={
                    "X-RapidAPI-Key": RAPIDAPI_KEY,
                    "X-RapidAPI-Host": "tiktok-scraper7.p.rapidapi.com"
                },
                params={"unique_id": self.username, "count": 50}
            )
            
            if response.status_code != 200:
                logger.error(f"Failed: {response.status_code}")
                return []
            
            data = response.json()
            videos = data.get("data", {}).get("videos", [])
            
            # Sort by play_count and take top N
            videos.sort(key=lambda x: x.get("play_count", 0), reverse=True)
            top_videos = videos[:count]
            
            logger.info(f"✅ Found {len(top_videos)} top videos")
            for v in top_videos:
                logger.info(f"   - {v.get('play_count', 0):,} views: {v.get('title', '')[:50]}...")
            
            return top_videos
    
    async def download_video(self, video: Dict, temp_dir: Path) -> Optional[Path]:
        """Download video to temp directory"""
        video_id = video.get("video_id", "")
        play_url = video.get("play", "") or video.get("wmplay", "")
        
        if not play_url:
            return None
        
        filepath = temp_dir / f"{video_id}.mp4"
        
        try:
            async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
                response = await client.get(play_url)
                if response.status_code == 200:
                    filepath.write_bytes(response.content)
                    logger.info(f"✅ Downloaded: {video_id}")
                    return filepath
        except Exception as e:
            logger.error(f"Download error: {e}")
        return None
    
    async def transcribe_video(self, video_path: Path) -> str:
        """Transcribe video using Whisper API"""
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(video_path, "rb") as f:
                    response = await client.post(
                        "https://api.openai.com/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                        files={"file": (video_path.name, f, "video/mp4")},
                        data={"model": "whisper-1"}
                    )
                    if response.status_code == 200:
                        return response.json().get("text", "")
        except Exception as e:
            logger.error(f"Transcription error: {e}")
        return ""
    
    def extract_frames(self, video_path: Path, num_frames: int = 4) -> List[str]:
        """Extract frames and return as base64"""
        frames = []
        try:
            # Get video duration
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
                capture_output=True, text=True
            )
            duration = float(result.stdout.strip() or "10")
            
            # Extract frames at intervals
            interval = duration / (num_frames + 1)
            
            for i in range(num_frames):
                timestamp = interval * (i + 1)
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                    subprocess.run([
                        "ffmpeg", "-ss", str(timestamp), "-i", str(video_path),
                        "-vframes", "1", "-y", "-q:v", "2", tmp.name
                    ], capture_output=True)
                    
                    if Path(tmp.name).exists() and Path(tmp.name).stat().st_size > 0:
                        with open(tmp.name, "rb") as f:
                            frames.append(base64.b64encode(f.read()).decode())
                    Path(tmp.name).unlink(missing_ok=True)
                    
        except Exception as e:
            logger.error(f"Frame extraction error: {e}")
        
        return frames
    
    async def analyze_with_vision(self, video_path: Path, caption: str, transcript: str) -> Dict:
        """Analyze video with GPT-4 Vision to understand format"""
        frames = self.extract_frames(video_path, num_frames=4)
        
        if not frames:
            return {"error": "No frames extracted"}
        
        # Build vision messages
        content = [
            {
                "type": "text",
                "text": f"""Analyze this TikTok video to understand its format for recreation with AI video generators.

CAPTION: {caption}
TRANSCRIPT: {transcript}

Analyze these 4 frames from the video and provide:
1. VISUAL STYLE: Camera angles, lighting, setting, color grading
2. SUBJECT: What's being shown, person characteristics, actions
3. TEXT/OVERLAYS: Any on-screen text, its style and placement
4. PACING: How the video flows, cuts, transitions
5. HOOK: What makes the first 3 seconds engaging
6. FORMAT PATTERN: The repeatable formula (e.g., "person talks to camera about X with Y background")

Then generate:
- A detailed SORA PROMPT to recreate this exact style
- A detailed VEO3 PROMPT to recreate this exact style

Be specific about visual details that AI video generators need."""
            }
        ]
        
        # Add frames
        for i, frame in enumerate(frames):
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{frame}", "detail": "high"}
            })
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o",
                        "messages": [{"role": "user", "content": content}],
                        "max_tokens": 2000
                    }
                )
                
                if response.status_code == 200:
                    return {"analysis": response.json()["choices"][0]["message"]["content"]}
                else:
                    return {"error": f"API error: {response.status_code}"}
                    
        except Exception as e:
            return {"error": str(e)}
    
    async def generate_master_analysis(self, analyses: List[str]) -> str:
        """Generate master analysis across all videos to find common patterns"""
        
        prompt = f"""You analyzed {len(analyses)} TikTok videos from @{self.username}. 
Here are the individual analyses:

{"="*50}
""" + "\n\n".join([f"VIDEO {i+1}:\n{a}" for i, a in enumerate(analyses)]) + f"""

{"="*50}

Now synthesize these into:

## 1. CORE FORMAT TEMPLATE
What is the repeatable formula across all these videos? Define the exact structure.

## 2. MASTER SORA PROMPT
A single, detailed Sora prompt that captures the essence of this creator's style.
Include: visual style, pacing, camera work, subject presentation, mood.

## 3. MASTER VEO3 PROMPT  
A single, detailed Veo3 prompt optimized for Google's video model.

## 4. CONTENT THEMES
What topics/themes work best? List 10 topic ideas in this format.

## 5. RECREATION CHECKLIST
Step-by-step checklist to recreate this format with YOUR face:
- Pre-production requirements
- Recording setup
- AI generation settings
- Post-production steps

## 6. AUTOMATION PIPELINE SPEC
How to automate this at scale:
- Content ideation → Script generation → Video creation → Stitching → Posting
"""
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENAI_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 4000
                    }
                )
                
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
                    
        except Exception as e:
            logger.error(f"Master analysis error: {e}")
        
        return ""
    
    async def run(self, num_videos: int = 5):
        """Main execution"""
        # Fetch top videos
        videos = await self.fetch_top_videos(num_videos)
        if not videos:
            print("❌ No videos found")
            return
        
        individual_analyses = []
        
        # Process in temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            for i, video in enumerate(videos):
                video_id = video.get("video_id", "")
                caption = video.get("title", "")
                views = video.get("play_count", 0)
                
                logger.info(f"\n[{i+1}/{len(videos)}] Processing {video_id} ({views:,} views)")
                
                # Download
                video_path = await self.download_video(video, temp_path)
                if not video_path:
                    continue
                
                # Transcribe
                logger.info("  Transcribing...")
                transcript = await self.transcribe_video(video_path)
                logger.info(f"  Transcript: {transcript[:100]}...")
                
                # Analyze with vision
                logger.info("  Analyzing with GPT-4 Vision...")
                analysis = await self.analyze_with_vision(video_path, caption, transcript)
                
                if "analysis" in analysis:
                    individual_analyses.append(analysis["analysis"])
                    logger.info("  ✅ Analysis complete")
                
                # Video file auto-deleted when temp dir is cleaned
        
        if not individual_analyses:
            print("❌ No analyses generated")
            return
        
        # Generate master analysis
        logger.info("\n" + "="*50)
        logger.info("Generating master analysis across all videos...")
        master = await self.generate_master_analysis(individual_analyses)
        
        # Save results
        output_file = self.output_dir / "prompt_analysis.md"
        
        full_report = f"""# Video Format Analysis: @{self.username}
Generated: {datetime.now().isoformat()}
Videos Analyzed: {len(individual_analyses)}

---

{master}

---

## Individual Video Analyses

"""
        for i, analysis in enumerate(individual_analyses):
            full_report += f"\n### Video {i+1}\n\n{analysis}\n\n---\n"
        
        output_file.write_text(full_report)
        logger.info(f"\n✅ Analysis saved to: {output_file}")
        
        # Print summary
        print("\n" + "="*60)
        print(f"✅ ANALYSIS COMPLETE: @{self.username}")
        print(f"   Videos analyzed: {len(individual_analyses)}")
        print(f"   Output: {output_file}")
        print("="*60)
        print("\n" + master)


async def main():
    username = sys.argv[1] if len(sys.argv) > 1 else "pensacola_bigfoot"
    num_videos = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    
    generator = CompetitorPromptGenerator(username)
    await generator.run(num_videos)


if __name__ == "__main__":
    asyncio.run(main())
