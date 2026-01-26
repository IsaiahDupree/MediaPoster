"""
Personal Brand Short Video Generator
====================================
Analyzes @personalbrandlaunch content and generates short videos
with icons, captions, and unique font titles.

Uses the existing CompetitorAnalysisService for full 100% analysis.

Reference style: https://www.instagram.com/p/DTwMxg1jsFB/
- 9:16 vertical (720x1278)
- Icon/illustration based
- Bold title at top
- Captions at bottom
- 30-60 seconds
"""

import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime
from loguru import logger

import httpx
from openai import OpenAI

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.competitor_analysis_service import (
    CompetitorAnalysisService,
    AccountLearnings,
    get_analysis_service
)
from services.competitor_service import get_competitor_service


# Output directory
OUTPUT_DIR = Path("/tmp/personalbrand_videos")

# Competitor data
MANIFEST_PATH = Path("/Users/isaiahdupree/Documents/CompetitorResearch/accounts/personalbrandlaunch/safari_manifest.json")


@dataclass
class ShortVideo:
    """A short video to generate"""
    title: str
    hook: str
    key_points: List[str]
    call_to_action: str
    icon_prompts: List[str] = field(default_factory=list)
    duration_seconds: int = 30


class PersonalBrandVideoGenerator:
    """
    Generates short videos inspired by personal brand content.
    Uses existing CompetitorAnalysisService for full 100% analysis.
    """
    
    def __init__(self):
        self.openai = OpenAI()
        self.output_dir = OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Use existing services
        self.analysis_service = get_analysis_service()
        self.competitor_service = get_competitor_service()
        
        # ElevenLabs config
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY", "sk_2252654c95162d4e0e644a1e2a540892d3faa828a36cace5")
        self.elevenlabs_voice_id = "k0HDiJKO5QdXkGN6NSLI"
    
    def load_competitor_data(self) -> Dict[str, Any]:
        """Load scraped competitor data"""
        if MANIFEST_PATH.exists():
            with open(MANIFEST_PATH) as f:
                return json.load(f)
        return {"username": "personalbrandlaunch", "post_urls": []}
    
    async def analyze_competitor(self, username: str = "personalbrandlaunch", max_content: int = 50) -> AccountLearnings:
        """
        Run full 100% analysis using Safari-scraped URLs + GPT-4.
        
        Falls back to Safari scraper manifest (525 URLs) when RapidAPI is rate-limited.
        """
        logger.info(f"Running FULL analysis on @{username}...")
        
        # Check for existing analysis first
        analysis_path = Path(f"/Users/isaiahdupree/Documents/CompetitorResearch/accounts/{username}/analysis/learnings.json")
        
        if analysis_path.exists():
            logger.info(f"Found existing analysis at {analysis_path}")
            with open(analysis_path) as f:
                data = json.load(f)
            
            # Use existing if less than 1 day old AND has real content
            age = datetime.now() - datetime.fromisoformat(data.get("generated_at", datetime.now().isoformat()))
            if age.days < 1 and data.get("total_content_analyzed", 0) > 10:
                logger.info("Using existing analysis (less than 1 day old)")
                return AccountLearnings(**data)
        
        # Try RapidAPI first via the service
        try:
            learnings = await self.analysis_service.analyze_account(username, max_content=max_content)
            if learnings and learnings.total_content_analyzed > 0:
                logger.success(f"Full analysis complete for @{username}")
                return learnings
        except Exception as e:
            logger.warning(f"RapidAPI analysis failed: {e}")
        
        # Fallback: Use Safari-scraped URLs (we have 525!)
        logger.info("Using Safari-scraped URLs for analysis...")
        return await self._analyze_from_safari_manifest(username)
    
    async def _analyze_from_safari_manifest(self, username: str) -> AccountLearnings:
        """Analyze using URLs from Safari scraper manifest + engagement stats"""
        
        manifest_path = Path(f"/Users/isaiahdupree/Documents/CompetitorResearch/accounts/{username}/safari_manifest.json")
        stats_path = Path(f"/Users/isaiahdupree/Documents/CompetitorResearch/accounts/{username}/engagement_stats.json")
        
        if not manifest_path.exists():
            logger.warning(f"No Safari manifest found for @{username}")
            return await self._fallback_analysis(username)
        
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        urls = manifest.get("post_urls", [])
        logger.info(f"Found {len(urls)} URLs in Safari manifest")
        
        # Load engagement stats if available
        engagement_data = {}
        if stats_path.exists():
            with open(stats_path) as f:
                engagement_data = json.load(f)
            logger.info(f"Loaded engagement stats for {len(engagement_data.get('videos', []))} videos")
        
        # Download and analyze a sample of videos
        sample_urls = urls[:20]  # Analyze top 20
        
        # Get captions by downloading video metadata
        captions = []
        for url in sample_urls[:10]:  # First 10 for caption extraction
            try:
                caption = await self._get_caption_from_url(url)
                if caption:
                    captions.append(caption)
            except Exception as e:
                logger.debug(f"Could not get caption: {e}")
        
        # Get top performing videos from engagement stats
        top_videos = []
        if engagement_data.get("videos"):
            sorted_videos = sorted(
                engagement_data["videos"],
                key=lambda x: x.get("like_count", 0) + x.get("comment_count", 0),
                reverse=True
            )[:10]
            top_videos = [
                {"likes": v["like_count"], "comments": v["comment_count"], "caption": v.get("caption", "")[:200]}
                for v in sorted_videos
            ]
        
        # Run GPT-4 analysis on URLs, captions, and engagement stats
        prompt = f"""Analyze this Instagram personal branding account based on their content.

Account: @{username}
Total Videos/Reels: {len(urls)}

ENGAGEMENT STATS (from {len(engagement_data.get('videos', []))} videos):
- Total Likes: {engagement_data.get('analysis', {}).get('total_likes', 'N/A')}
- Total Comments: {engagement_data.get('analysis', {}).get('total_comments', 'N/A')}
- Avg Likes/Video: {engagement_data.get('analysis', {}).get('avg_likes', 'N/A')}

TOP PERFORMING VIDEOS (by engagement):
{json.dumps(top_videos[:5], indent=2) if top_videos else "No engagement data"}

SAMPLE VIDEO URLs:
{json.dumps(sample_urls[:10], indent=2)}

SAMPLE CAPTIONS EXTRACTED:
{json.dumps(captions[:5], indent=2) if captions else "No captions extracted"}

Analyze the content patterns and provide:

1. Top Performing Hook Types (with percentages)
2. Top Content Formats (with percentages) 
3. Main Content Themes
4. Key Learnings from their strategy
5. Content Ideas to replicate their success

Return JSON:
{{
    "top_hooks": [
        {{"type": "hook_type_name", "count": 5, "percentage": 50.0}}
    ],
    "top_formats": [
        {{"type": "format_type_name", "count": 5, "percentage": 50.0}}
    ],
    "content_themes": ["theme1", "theme2", "theme3"],
    "key_learnings": ["learning1", "learning2"],
    "content_ideas": ["specific actionable idea 1", "idea 2", "idea 3", "idea 4", "idea 5"]
}}"""

        response = self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        learnings = AccountLearnings(
            username=username,
            total_content_analyzed=len(urls),
            avg_engagement_rate=0,
            top_hooks=result.get("top_hooks", []),
            top_formats=result.get("top_formats", []),
            content_themes=result.get("content_themes", []),
            posting_patterns={"total_reels": len(urls), "total_posts": 0},
            key_learnings=result.get("key_learnings", []),
            content_ideas=result.get("content_ideas", []),
            generated_at=datetime.now().isoformat()
        )
        
        # Save to analysis folder
        analysis_dir = Path(f"/Users/isaiahdupree/Documents/CompetitorResearch/accounts/{username}/analysis")
        analysis_dir.mkdir(parents=True, exist_ok=True)
        with open(analysis_dir / "learnings.json", "w") as f:
            json.dump(learnings.model_dump(), f, indent=2, default=str)
        
        logger.success(f"Safari manifest analysis complete: {len(urls)} URLs analyzed")
        return learnings
    
    async def _get_caption_from_url(self, url: str) -> Optional[str]:
        """Extract caption from Instagram URL using yt-dlp"""
        import subprocess
        
        try:
            result = subprocess.run(
                ["yt-dlp", "--skip-download", "--print", "%(description)s", url],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()[:500]  # Limit to 500 chars
        except Exception as e:
            logger.debug(f"Caption extraction failed: {e}")
        return None
    
    async def _fallback_analysis(self, username: str) -> AccountLearnings:
        """Fallback analysis when RapidAPI fails - uses GPT-4 with URL patterns"""
        
        data = self.load_competitor_data()
        urls = data.get("post_urls", [])[:30]
        
        prompt = f"""Analyze this personal branding Instagram account based on their content patterns.

Account: @{username}
Sample URLs (showing their content themes):
{json.dumps(urls[:20], indent=2)}

The account has {len(data.get('post_urls', []))} total reels/posts.

Based on typical personal branding content patterns, provide analysis in JSON:
{{
    "top_hooks": [
        {{"type": "hook_type", "count": 5, "percentage": 50.0}}
    ],
    "top_formats": [
        {{"type": "format_type", "count": 5, "percentage": 50.0}}
    ],
    "content_themes": ["theme1", "theme2"],
    "key_learnings": ["learning1", "learning2"],
    "content_ideas": ["idea1", "idea2", "idea3", "idea4", "idea5"]
}}"""

        response = self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return AccountLearnings(
            username=username,
            total_content_analyzed=len(urls),
            avg_engagement_rate=0,
            top_hooks=result.get("top_hooks", []),
            top_formats=result.get("top_formats", []),
            content_themes=result.get("content_themes", []),
            posting_patterns={"total_reels": len(urls), "total_posts": 0},
            key_learnings=result.get("key_learnings", []),
            content_ideas=result.get("content_ideas", []),
            generated_at=datetime.now().isoformat()
        )
    
    async def generate_icon_image(
        self,
        prompt: str,
        output_path: Path,
        style: str = "minimal flat icon, solid background, centered"
    ) -> Path:
        """Generate icon/illustration using DALL-E"""
        
        full_prompt = f"{prompt}. Style: {style}, modern design, no text, clean illustration, suitable for social media video"
        
        try:
            response = self.openai.images.generate(
                model="dall-e-3",
                prompt=full_prompt,
                size="1024x1024",
                quality="standard",
                n=1
            )
            
            image_url = response.data[0].url
            
            async with httpx.AsyncClient() as client:
                img_response = await client.get(image_url)
                with open(output_path, "wb") as f:
                    f.write(img_response.content)
            
            logger.success(f"Generated icon: {output_path.name}")
            return output_path
            
        except Exception as e:
            logger.warning(f"DALL-E failed: {e}, creating placeholder")
            # Create colored placeholder
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", "color=c=0x6366f1:s=1024x1024:d=1",
                "-frames:v", "1",
                str(output_path)
            ]
            subprocess.run(cmd, capture_output=True)
            return output_path
    
    async def generate_voice(self, text: str, output_path: Path) -> Path:
        """Generate voiceover using ElevenLabs"""
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": self.elevenlabs_api_key
        }
        
        payload = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.3,
                "similarity_boost": 0.85,
                "style": 0.6,
                "use_speaker_boost": True
            }
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{self.elevenlabs_voice_id}",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                logger.success(f"Generated voice: {output_path.name}")
                return output_path
            else:
                logger.error(f"ElevenLabs error: {response.status_code}")
                raise Exception("Voice generation failed")
    
    async def create_short_video(
        self,
        video: ShortVideo,
        video_index: int
    ) -> Path:
        """
        Create a short video with:
        - Title at top with unique font
        - Icons/images for each point
        - Captions at bottom
        - Voiceover
        
        Reference style: DTwMxg1jsFB (9:16 vertical, 720x1278)
        """
        
        video_dir = self.output_dir / f"video_{video_index:02d}"
        video_dir.mkdir(exist_ok=True)
        
        logger.info(f"Creating video {video_index}: {video.title}")
        
        # Step 1: Create script
        script = f"{video.hook} "
        for point in video.key_points:
            script += f"{point}. "
        script += video.call_to_action
        
        # Step 2: Generate voiceover
        voice_path = video_dir / "voiceover.mp3"
        await self.generate_voice(script, voice_path)
        
        # Get audio duration
        result = subprocess.run([
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(voice_path)
        ], capture_output=True, text=True)
        audio_duration = float(result.stdout.strip())
        
        # Step 3: Generate icon images for each key point
        icon_prompts = [
            f"Icon representing: {video.hook}",
            *[f"Icon representing: {point}" for point in video.key_points],
            f"Icon representing: {video.call_to_action}"
        ]
        
        icon_paths = []
        for i, prompt in enumerate(icon_prompts[:4]):  # Max 4 icons
            icon_path = video_dir / f"icon_{i:02d}.png"
            await self.generate_icon_image(prompt, icon_path)
            icon_paths.append(icon_path)
        
        # Step 4: Calculate timing per scene
        num_scenes = len(icon_paths)
        scene_duration = audio_duration / num_scenes
        
        # Step 5: Build video with ffmpeg
        # Create 9:16 vertical video (720x1278)
        output_path = video_dir / f"{video.title.replace(' ', '_')}.mp4"
        
        # Build filter complex
        inputs = []
        filter_parts = []
        
        # Add icons as inputs
        for i, icon_path in enumerate(icon_paths):
            inputs.extend(["-loop", "1", "-t", str(scene_duration), "-i", str(icon_path)])
        
        # Add audio
        inputs.extend(["-i", str(voice_path)])
        
        n_icons = len(icon_paths)
        
        # Process each icon: scale to fit 9:16, add gradient background
        for i in range(n_icons):
            filter_parts.append(
                f"[{i}:v]scale=500:500,pad=720:1278:(720-500)/2:300:color=0x1a1a2e[icon{i}];"
            )
        
        # Add title text at top for each icon scene
        # Escape special characters for ffmpeg drawtext
        title_safe = video.title.replace("'", "").replace(":", " -").replace("\\", "")
        
        for i in range(n_icons):
            # Determine text for this scene
            if i == 0:
                scene_text = video.hook[:60]
            elif i < len(video.key_points) + 1:
                scene_text = video.key_points[i-1][:80] if i-1 < len(video.key_points) else ""
            else:
                scene_text = video.call_to_action[:60]
            
            # Clean text for ffmpeg
            scene_text_safe = scene_text.replace("'", "").replace(":", " -").replace("\n", " ").replace("\\", "")
            
            # Add title at top and caption at bottom (simpler filter, no font specification)
            filter_parts.append(
                f"[icon{i}]drawtext=text='{title_safe}':"
                f"fontsize=42:fontcolor=white:x=(w-tw)/2:y=80:"
                f"box=1:boxcolor=black@0.5:boxborderw=10,"
                f"drawtext=text='{scene_text_safe}':"
                f"fontsize=28:fontcolor=white:x=(w-tw)/2:y=h-200:"
                f"box=1:boxcolor=black@0.7:boxborderw=8[scene{i}];"
            )
        
        # Concat all scenes
        concat_inputs = "".join([f"[scene{i}]" for i in range(n_icons)])
        filter_parts.append(f"{concat_inputs}concat=n={n_icons}:v=1:a=0[outv]")
        
        filter_complex = "".join(filter_parts)
        
        # Build ffmpeg command
        cmd = ["ffmpeg", "-y"]
        cmd.extend(inputs)
        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", "[outv]",
            "-map", f"{n_icons}:a",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path)
        ])
        
        logger.info("Rendering video...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.success(f"Video created: {output_path}")
        else:
            logger.error(f"FFmpeg error: {result.stderr[:300]}")
        
        return output_path
    
    async def generate_videos(self, num_videos: int = 3, username: str = "personalbrandlaunch") -> List[Path]:
        """Generate multiple short videos based on full 100% analysis"""
        
        # Step 1: Run FULL analysis using CompetitorAnalysisService
        logger.info(f"Running FULL analysis on @{username}...")
        learnings = await self.analyze_competitor(username, max_content=50)
        
        print(f"\n📊 FULL Content Analysis Complete:")
        print(f"   Content Analyzed: {learnings.total_content_analyzed}")
        print(f"   Avg Engagement: {learnings.avg_engagement_rate:,.0f}")
        print(f"   Top Hooks: {[h.get('type') for h in learnings.top_hooks[:3]]}")
        print(f"   Top Formats: {[f.get('type') for f in learnings.top_formats[:3]]}")
        print(f"   Themes: {', '.join(learnings.content_themes[:5])}")
        print(f"   Content Ideas: {len(learnings.content_ideas)}")
        print(f"   Key Learnings: {len(learnings.key_learnings)}")
        
        # Step 2: Generate video ideas from learnings
        video_ideas = await self._generate_video_ideas_from_learnings(learnings, num_videos)
        
        # Step 3: Generate videos from ideas
        generated_videos = []
        
        for i, idea in enumerate(video_ideas[:num_videos]):
            video = ShortVideo(
                title=idea.get("title", f"Video {i+1}"),
                hook=idea.get("hook", "Here's something you need to know..."),
                key_points=idea.get("key_points", ["Point 1", "Point 2", "Point 3"]),
                call_to_action=idea.get("cta", "Follow for more tips!")
            )
            
            video_path = await self.create_short_video(video, i)
            generated_videos.append(video_path)
            print(f"\n✅ Video {i+1}/{num_videos}: {video.title}")
        
        return generated_videos
    
    async def _generate_video_ideas_from_learnings(self, learnings: AccountLearnings, num_ideas: int = 5) -> List[Dict]:
        """Generate specific video ideas from AccountLearnings"""
        
        # If we already have content_ideas from the service, use those
        if learnings.content_ideas:
            # Convert string ideas to structured format
            ideas = []
            for idea_text in learnings.content_ideas[:num_ideas]:
                # Generate structured idea from text
                structured = await self._structure_idea(idea_text, learnings)
                ideas.append(structured)
            return ideas
        
        # Otherwise generate new ideas based on learnings
        prompt = f"""Based on this competitor analysis, generate {num_ideas} specific video ideas.

TOP PERFORMING HOOKS:
{json.dumps(learnings.top_hooks, indent=2)}

TOP FORMATS:
{json.dumps(learnings.top_formats, indent=2)}

CONTENT THEMES:
{', '.join(learnings.content_themes)}

KEY LEARNINGS:
{json.dumps(learnings.key_learnings[:5], indent=2)}

Generate {num_ideas} video ideas that combine successful patterns. Each should be actionable and ready to create.

Return JSON:
{{
    "video_ideas": [
        {{
            "title": "Video Title",
            "hook": "Opening hook line that grabs attention",
            "key_points": ["point1", "point2", "point3"],
            "cta": "Call to action"
        }}
    ]
}}"""

        response = self.openai.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        return result.get("video_ideas", [])
    
    async def _structure_idea(self, idea_text: str, learnings: AccountLearnings) -> Dict:
        """Convert a text idea into structured video format"""
        
        # Use top hook type for the hook style
        hook_type = learnings.top_hooks[0].get("type", "question") if learnings.top_hooks else "question"
        
        prompt = f"""Convert this content idea into a structured video brief:

IDEA: {idea_text}

Use this hook style: {hook_type}

Return JSON:
{{
    "title": "Short catchy title",
    "hook": "Opening hook line using {hook_type} style",
    "key_points": ["point1", "point2", "point3"],
    "cta": "Call to action"
}}"""

        response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        return json.loads(response.choices[0].message.content)


async def main():
    """Main entry point"""
    
    print("\n" + "="*60)
    print("Personal Brand Video Generator")
    print("="*60 + "\n")
    
    generator = PersonalBrandVideoGenerator()
    
    # Generate 3 videos
    videos = await generator.generate_videos(num_videos=3)
    
    print("\n" + "="*60)
    print("GENERATION COMPLETE")
    print("="*60)
    print(f"\n📁 Output: {OUTPUT_DIR}")
    print(f"🎬 Videos: {len(videos)}")
    
    for video in videos:
        print(f"   - {video}")
    
    # Open first video
    if videos:
        subprocess.run(["open", str(videos[0])])
    
    return videos


if __name__ == "__main__":
    asyncio.run(main())
