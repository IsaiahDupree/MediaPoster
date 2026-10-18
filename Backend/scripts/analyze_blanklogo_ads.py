"""
Analyze BlankLogo watermark remover ad videos and generate Meta ad copy.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path
from openai import OpenAI
import base64
import subprocess
from datetime import datetime

# Video paths
VIDEO_DIR = Path("/Users/isaiahdupree/Documents/Software/Remotion/out/blanklogo-ads/video")
VIDEOS = {
    "video5": VIDEO_DIR / "video5/9x16/PA-01-PostToday.mp4",
    "video6": VIDEO_DIR / "video6/9x16/PA-01-PostToday.mp4",
    "video7": VIDEO_DIR / "video7/9x16/PA-01-PostToday.mp4",
    "video8": VIDEO_DIR / "video8/9x16/PA-01-PostToday.mp4",
}

# Load API key from .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_frames(video_path: Path, num_frames: int = 5) -> list:
    """Extract frames from video at regular intervals."""
    output_dir = Path("/tmp/blanklogo_frames") / video_path.parent.name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Get video duration
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(video_path)],
        capture_output=True, text=True
    )
    duration = float(result.stdout.strip())
    
    frames = []
    for i in range(num_frames):
        timestamp = (duration / (num_frames + 1)) * (i + 1)
        output_path = output_dir / f"frame_{i:02d}.jpg"
        
        subprocess.run([
            "ffmpeg", "-y", "-ss", str(timestamp), "-i", str(video_path),
            "-vframes", "1", "-q:v", "2", str(output_path)
        ], capture_output=True)
        
        if output_path.exists():
            frames.append(output_path)
    
    return frames


def encode_image(image_path: Path) -> str:
    """Encode image to base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_video_frames(video_name: str, frames: list) -> dict:
    """Analyze video frames with GPT-4 Vision."""
    print(f"\n🎬 Analyzing {video_name}...")
    
    content = [
        {
            "type": "text",
            "text": """Analyze these frames from a BlankLogo watermark remover advertisement video.

This is a "before/after" style ad showing:
- BEFORE: A video with a visible watermark (Sora, TikTok, etc.)
- AFTER: The same video with the watermark removed by BlankLogo

Please provide a detailed analysis:
1. **Visual Content**: What's shown in the before/after comparison?
2. **Watermark Type**: What watermark is being removed?
3. **Video Style**: What type of content is in the video? (AI-generated, creator content, etc.)
4. **Emotional Appeal**: What emotions does this ad evoke?
5. **Target Audience**: Who would this ad appeal to?
6. **Key Selling Points**: What makes this compelling?
7. **Text/Copy Visible**: Any text overlays or captions shown?
8. **Quality Assessment**: How professional/polished does it look?

Be specific and detailed."""
        }
    ]
    
    for frame_path in frames:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{encode_image(frame_path)}",
                "detail": "high"
            }
        })
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": content}],
        max_tokens=1500
    )
    
    analysis = response.choices[0].message.content
    print(f"✓ Analysis complete for {video_name}")
    
    return {
        "video_name": video_name,
        "analysis": analysis,
        "tokens_used": response.usage.total_tokens
    }


def generate_meta_ad_copy(analyses: list) -> dict:
    """Generate Meta ad copy based on video analyses."""
    print("\n📝 Generating Meta Ad Copy...")
    
    combined_analysis = "\n\n".join([
        f"=== {a['video_name']} ===\n{a['analysis']}"
        for a in analyses
    ])
    
    prompt = f"""Based on these video analyses for BlankLogo watermark remover ads, create compelling Meta (Facebook/Instagram) ad copy.

VIDEO ANALYSES:
{combined_analysis}

---

PRODUCT INFO:
- Product: BlankLogo - AI Watermark Remover
- Key Feature: Removes watermarks from Sora, Runway, Pika, TikTok, and other AI-generated videos
- Target Audience: Content creators, social media managers, video editors, AI video enthusiasts
- Value Proposition: Post your AI-generated videos without ugly watermarks. Look professional.
- Copy Theme Used: PA-01 "Post Today" (READY TO POST • Remove the Watermark.)

---

Generate the following Meta Ad components (provide multiple options for each):

## PRIMARY TEXT (3 options)
The main body copy shown above the video. Should be:
- Attention-grabbing opening
- Clear value proposition
- Create urgency/desire
- 125 characters recommended, max 500

## HEADLINE (3 options)
Short, punchy headline shown below the video. Should be:
- 25-40 characters
- Clear benefit statement
- Action-oriented

## DESCRIPTION (3 options)
Additional details shown under headline. Should be:
- Support the headline
- Add credibility or features
- 25-30 characters

## CALL TO ACTION
Recommend the best CTA button from these options:
- Learn More
- Sign Up
- Get Started
- Try Now
- Download
- Get Offer

Also provide:

## CREATIVE RECOMMENDATIONS
- Best performing video from the 4 analyzed
- Recommended aspect ratios for placement
- A/B testing suggestions

## AUDIENCE TARGETING SUGGESTIONS
- Interest-based targeting
- Lookalike suggestions
- Demographics

Format your response clearly with markdown headers."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an expert Meta Ads copywriter specializing in SaaS and creator tools. You write high-converting ad copy that is clear, compelling, and drives action."
            },
            {"role": "user", "content": prompt}
        ],
        max_tokens=3000
    )
    
    return {
        "ad_copy": response.choices[0].message.content,
        "tokens_used": response.usage.total_tokens
    }


def main():
    print("=" * 60)
    print("BlankLogo Ad Video Analysis & Meta Ad Copy Generator")
    print("=" * 60)
    
    analyses = []
    total_tokens = 0
    
    for video_name, video_path in VIDEOS.items():
        if not video_path.exists():
            print(f"⚠️  Video not found: {video_path}")
            continue
        
        print(f"\n📹 Processing {video_name}: {video_path}")
        print(f"   Size: {video_path.stat().st_size / 1024 / 1024:.1f} MB")
        
        frames = extract_frames(video_path, num_frames=5)
        print(f"   Extracted {len(frames)} frames")
        
        analysis = analyze_video_frames(video_name, frames)
        analyses.append(analysis)
        total_tokens += analysis["tokens_used"]
    
    print(f"\n✓ Analyzed {len(analyses)} videos (Total tokens: {total_tokens})")
    
    ad_copy_result = generate_meta_ad_copy(analyses)
    total_tokens += ad_copy_result["tokens_used"]
    
    print("\n" + "=" * 60)
    print("COMPLETE ANALYSIS RESULTS")
    print("=" * 60)
    
    for analysis in analyses:
        print(f"\n### {analysis['video_name'].upper()} ###")
        print(analysis["analysis"])
        print("-" * 40)
    
    print("\n" + "=" * 60)
    print("META AD COPY RECOMMENDATIONS")
    print("=" * 60)
    print(ad_copy_result["ad_copy"])
    
    print(f"\n📊 Total API tokens used: {total_tokens}")
    
    output_file = Path("/tmp/blanklogo_ad_analysis.json")
    results = {
        "timestamp": datetime.now().isoformat(),
        "video_analyses": analyses,
        "ad_copy": ad_copy_result["ad_copy"],
        "total_tokens": total_tokens
    }
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    main()
