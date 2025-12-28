"""
Analyze Video Style Templates
=============================
Downloads YouTube videos, analyzes their style/structure, and creates reusable
templates that can be used to recreate videos in the same style with new content.
"""

import os
import re
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass, asdict, field
from datetime import datetime

from openai import OpenAI
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logger
logger.remove()
logger.add(sys.stderr, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

# Initialize OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable not set")

client = OpenAI(api_key=OPENAI_API_KEY)


@dataclass
class VideoStyleTemplate:
    """Reusable template extracted from video analysis"""
    template_id: str
    source_video_url: str
    source_video_title: str
    
    # Structure
    structure_pattern: Dict[str, Any]  # hook, body, cta timing
    beat_sheet_template: List[Dict[str, Any]]
    
    # Style Elements
    hook_archetype: str
    hook_examples: List[str]
    pacing: str  # fast, medium, slow
    cut_density: str  # high, medium, low
    
    # Visual Style
    primary_shot_type: str
    text_overlay_style: Dict[str, Any]
    
    # Content Style
    content_style: str  # tutorial, story, rant, explainer, etc.
    tone: str  # casual, professional, energetic, etc.
    complexity: str  # simple, medium, technical
    
    # CTA Pattern
    cta_type: str
    cta_placement: str
    
    # Emotional Triggers
    primary_emotion: str
    
    # Replication Instructions
    replication_guide: str
    
    # Optional fields with defaults
    color_scheme: Optional[str] = None
    cta_examples: List[str] = field(default_factory=list)
    emotional_triggers: List[str] = field(default_factory=list)
    key_patterns: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL"""
    try:
        parsed = urlparse(url)
        if parsed.hostname in ['youtube.com', 'www.youtube.com']:
            return parse_qs(parsed.query).get('v', [None])[0]
        elif parsed.hostname == 'youtu.be':
            return parsed.path.lstrip('/')
    except Exception as e:
        logger.error(f"Error parsing URL {url}: {e}")
    return None


def download_video_transcript(video_id: str, output_dir: Path) -> Optional[str]:
    """Download video transcript using youtube-transcript-api or yt-dlp"""
    try:
        logger.info(f"📥 Downloading transcript for video {video_id}...")
        
        # Try youtube-transcript-api first (simpler, more reliable)
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
            
            api = YouTubeTranscriptApi()
            transcript = api.fetch(video_id)
            transcript_text = ' '.join([snippet.text for snippet in transcript.snippets])
            
            if transcript_text:
                logger.success(f"✅ Transcript downloaded via API: {len(transcript_text)} chars")
                return transcript_text
        except (TranscriptsDisabled, NoTranscriptFound):
            logger.warning(f"⚠️  No transcript available via API for {video_id}")
        except ImportError:
            logger.warning(f"⚠️  youtube-transcript-api not installed, trying yt-dlp...")
        except Exception as e:
            logger.warning(f"⚠️  API error: {e}, trying yt-dlp...")
        
        # Fallback to yt-dlp
        vtt_path = output_dir / f"{video_id}.vtt"
        cmd = [
            "yt-dlp",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "en",
            "--sub-format", "vtt",
            "--skip-download",
            "--no-warnings",
            f"https://www.youtube.com/watch?v={video_id}",
            "-o", str(output_dir / "%(id)s.%(ext)s")
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and vtt_path.exists():
            # Parse VTT to text
            transcript = parse_vtt(vtt_path)
            logger.success(f"✅ Transcript downloaded via yt-dlp: {len(transcript)} chars")
            return transcript
        else:
            logger.warning(f"⚠️  Could not download transcript via yt-dlp")
            return None
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ Timeout downloading transcript for {video_id}")
        return None
    except Exception as e:
        logger.error(f"❌ Error downloading transcript: {e}")
        return None


def parse_vtt(vtt_path: Path) -> str:
    """Parse VTT subtitle file and extract full transcript"""
    text_lines = []
    
    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip WEBVTT header and metadata
            if line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
                i += 1
                continue
            
            # Check if this is a timestamp line
            if '-->' in line:
                # Next line(s) should be the text
                i += 1
                text_parts = []
                while i < len(lines) and lines[i].strip() and '-->' not in lines[i]:
                    text_line = lines[i].strip()
                    # Remove HTML tags
                    text_line = re.sub(r'<[^>]+>', '', text_line)
                    if text_line:
                        text_parts.append(text_line)
                    i += 1
                if text_parts:
                    text = ' '.join(text_parts)
                    # Remove duplicate consecutive words
                    words = text.split()
                    deduped = []
                    for word in words:
                        if not deduped or word != deduped[-1]:
                            deduped.append(word)
                    text_lines.append(' '.join(deduped))
                continue
            
            i += 1
        
        return '\n'.join(text_lines)
    except Exception as e:
        logger.error(f"Error parsing VTT file {vtt_path}: {e}")
        return ""


def get_video_info(video_id: str) -> Dict[str, Any]:
    """Get video metadata using yt-dlp"""
    try:
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            f"https://www.youtube.com/watch?v={video_id}"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            logger.warning(f"Could not get video info: {result.stderr}")
            return {}
    except Exception as e:
        logger.error(f"Error getting video info: {e}")
        return {}


STYLE_ANALYSIS_PROMPT = """
Analyze this video and extract a complete style template that can be used to recreate videos in the same style with different content.

VIDEO INFO:
- Title: {title}
- Duration: {duration} seconds
- URL: {url}

TRANSCRIPT:
{transcript}

ANALYZE AND EXTRACT:

1. STRUCTURE PATTERN:
   - Hook timing (first X seconds)
   - Body structure (how content is organized)
   - CTA placement and timing
   - Beat sheet: Break down the video into beats with timestamps and roles
   
2. HOOK ANALYSIS:
   - Hook archetype (e.g., "Stop doing X", "3 mistakes", "Nobody tells you", "POV:", etc.)
   - Extract 2-3 example hook phrases from the video
   - Hook strength and why it works
   
3. PACING & RHYTHM:
   - Overall pacing: fast, medium, or slow
   - Cut density: high (many cuts), medium, or low
   - Speech rate: fast, medium, or slow
   
4. VISUAL STYLE:
   - Primary shot type: talking_head, screen_record, b_roll, mixed, animation
   - Text overlay style: Describe how text appears (animated, static, captions, etc.)
   - Color scheme (if identifiable)
   - Visual elements: memes, graphics, transitions
   
5. CONTENT STYLE:
   - Content type: tutorial, story, rant, vlog, review, explainer, demo, interview, listicle
   - Tone: casual, professional, energetic, calm, authoritative, friendly
   - Complexity: simple, medium, technical
   
6. CTA PATTERN:
   - CTA type: engagement, conversion, open_loop, conversation, none
   - CTA placement: opening, middle, closing
   - Extract actual CTA text examples
   
7. EMOTIONAL TRIGGERS:
   - Primary emotion evoked: relief, excitement, curiosity, fomo, frustration, hope, surprise
   - List 3-5 emotional triggers used
   
8. REPLICATION GUIDE:
   - Write a step-by-step guide on how to recreate this style
   - Identify 5-7 key patterns that make this style work
   - Explain what makes this style effective

Return ONLY valid JSON (no markdown, no code blocks):
{{
  "structure": {{
    "hook_duration_sec": 3,
    "body_structure": "problem-solution-proof",
    "cta_placement": "closing",
    "beat_sheet": [
      {{"role": "hook", "start_sec": 0, "end_sec": 3, "summary": "Opens with pain point"}},
      {{"role": "problem", "start_sec": 3, "end_sec": 15, "summary": "Describes the problem"}},
      {{"role": "solution", "start_sec": 15, "end_sec": 45, "summary": "Presents solution"}},
      {{"role": "proof", "start_sec": 45, "end_sec": 55, "summary": "Shows proof/results"}},
      {{"role": "cta", "start_sec": 55, "end_sec": 60, "summary": "Call to action"}}
    ]
  }},
  "hook": {{
    "archetype": "Stop doing X",
    "examples": ["Stop doing email manually", "Stop wasting time on X"],
    "strength": 0.85,
    "why_it_works": "Immediate pain point that resonates"
  }},
  "pacing": {{
    "overall": "fast",
    "cut_density": "high",
    "speech_rate": "fast"
  }},
  "visual": {{
    "primary_shot": "screen_record",
    "text_overlay_style": {{
      "type": "animated_captions",
      "position": "center",
      "animation": "fade_in_out"
    }},
    "color_scheme": "bright_high_contrast"
  }},
  "content": {{
    "style": "tutorial",
    "tone": "energetic",
    "complexity": "medium"
  }},
  "cta": {{
    "type": "engagement",
    "placement": "closing",
    "examples": ["Comment 'AUTOMATION' to get the template", "Save this for later"]
  }},
  "emotion": {{
    "primary": "relief",
    "triggers": ["relatable pain", "quick solution", "proof of results"]
  }},
  "replication": {{
    "guide": "Step-by-step guide on how to recreate...",
    "key_patterns": [
      "Open with relatable pain point",
      "Use screen recordings with animated captions",
      "Fast pacing with high cut density",
      "End with clear engagement CTA"
    ]
  }}
}}
"""


def analyze_video_style(video_url: str, video_id: str, title: str, duration: int, transcript: str) -> Dict[str, Any]:
    """Analyze video and extract style template using AI"""
    logger.info(f"🔍 Analyzing style for: {title}")
    
    try:
        prompt = STYLE_ANALYSIS_PROMPT.format(
            title=title,
            duration=duration,
            url=video_url,
            transcript=transcript[:4000]  # Limit transcript length
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert video content strategist specializing in analyzing and extracting reusable style templates from successful videos. Always respond with valid JSON only."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=2500
        )
        
        analysis = json.loads(response.choices[0].message.content)
        logger.success(f"✅ Style analysis complete")
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Error analyzing video style: {e}")
        return {}


def create_style_template(video_url: str, video_id: str, video_info: Dict, analysis: Dict) -> VideoStyleTemplate:
    """Create a VideoStyleTemplate from analysis results"""
    
    structure = analysis.get("structure", {})
    hook = analysis.get("hook", {})
    pacing = analysis.get("pacing", {})
    visual = analysis.get("visual", {})
    content = analysis.get("content", {})
    cta = analysis.get("cta", {})
    emotion = analysis.get("emotion", {})
    replication = analysis.get("replication", {})
    
    return VideoStyleTemplate(
        template_id=f"template_{video_id}",
        source_video_url=video_url,
        source_video_title=video_info.get("title", "Unknown"),
        structure_pattern={
            "hook_duration_sec": structure.get("hook_duration_sec", 3),
            "body_structure": structure.get("body_structure", "unknown"),
            "cta_placement": structure.get("cta_placement", "closing")
        },
        beat_sheet_template=structure.get("beat_sheet", []),
        hook_archetype=hook.get("archetype", "unknown"),
        hook_examples=hook.get("examples", []),
        pacing=pacing.get("overall", "medium"),
        cut_density=pacing.get("cut_density", "medium"),
        primary_shot_type=visual.get("primary_shot", "unknown"),
        text_overlay_style=visual.get("text_overlay_style", {}),
        color_scheme=visual.get("color_scheme"),
        content_style=content.get("style", "unknown"),
        tone=content.get("tone", "casual"),
        complexity=content.get("complexity", "medium"),
        cta_type=cta.get("type", "none"),
        cta_placement=cta.get("placement", "closing"),
        cta_examples=cta.get("examples", []),
        primary_emotion=emotion.get("primary", "curiosity"),
        emotional_triggers=emotion.get("triggers", []),
        replication_guide=replication.get("guide", ""),
        key_patterns=replication.get("key_patterns", [])
    )


def aggregate_templates(templates: List[VideoStyleTemplate]) -> Dict[str, Any]:
    """Aggregate patterns across multiple templates"""
    logger.info("📊 Aggregating patterns across templates...")
    
    # Count patterns
    hook_archetypes = {}
    pacing_distribution = {}
    content_styles = {}
    cta_types = {}
    shot_types = {}
    
    for template in templates:
        # Hook archetypes
        hook_archetypes[template.hook_archetype] = hook_archetypes.get(template.hook_archetype, 0) + 1
        
        # Pacing
        pacing_distribution[template.pacing] = pacing_distribution.get(template.pacing, 0) + 1
        
        # Content styles
        content_styles[template.content_style] = content_styles.get(template.content_style, 0) + 1
        
        # CTA types
        cta_types[template.cta_type] = cta_types.get(template.cta_type, 0) + 1
        
        # Shot types
        shot_types[template.primary_shot_type] = shot_types.get(template.primary_shot_type, 0) + 1
    
    # Find most common patterns
    most_common_hook = max(hook_archetypes.items(), key=lambda x: x[1])[0] if hook_archetypes else None
    most_common_pacing = max(pacing_distribution.items(), key=lambda x: x[1])[0] if pacing_distribution else None
    most_common_style = max(content_styles.items(), key=lambda x: x[1])[0] if content_styles else None
    
    return {
        "total_templates": len(templates),
        "hook_archetypes": hook_archetypes,
        "most_common_hook": most_common_hook,
        "pacing_distribution": pacing_distribution,
        "most_common_pacing": most_common_pacing,
        "content_styles": content_styles,
        "most_common_style": most_common_style,
        "cta_types": cta_types,
        "shot_types": shot_types,
        "all_templates": [asdict(t) for t in templates]
    }


def main():
    """Main analysis function"""
    # Video URLs to analyze
    video_urls = [
        "https://www.youtube.com/watch?v=Om0d0u1ASJY&t=156s",
        "https://www.youtube.com/watch?v=DScr9hwfcas&t=258s",
        "https://www.youtube.com/watch?v=HSmHYWBy0ss",
        "https://www.youtube.com/watch?v=oBYM1bEpGB0&t=62s",
        "https://www.youtube.com/watch?v=XOtMZchugyQ&t=302s",
        "https://www.youtube.com/watch?v=Dgzb6ojbjWg",
        "https://www.youtube.com/watch?v=v4LDsaWNjaM"
    ]
    
    # Remove duplicates
    video_urls = list(dict.fromkeys(video_urls))
    
    print("=" * 80)
    print("🎬 Video Style Template Analyzer")
    print("=" * 80)
    print(f"📹 Analyzing {len(video_urls)} videos...")
    print()
    
    # Setup output directory
    output_dir = Path("Backend/data/video_style_templates")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    templates = []
    
    for i, url in enumerate(video_urls, 1):
        print(f"\n{'='*80}")
        print(f"Video {i}/{len(video_urls)}: {url}")
        print(f"{'='*80}\n")
        
        # Extract video ID
        video_id = extract_video_id(url)
        if not video_id:
            logger.error(f"❌ Could not extract video ID from: {url}")
            continue
        
        # Get video info
        logger.info(f"📋 Getting video info...")
        video_info = get_video_info(video_id)
        title = video_info.get("title", f"Video {video_id}")
        duration = int(video_info.get("duration", 0))
        
        logger.info(f"📺 {title} ({duration}s)")
        
        # Download transcript
        transcript = download_video_transcript(video_id, output_dir)
        if not transcript:
            logger.warning(f"⚠️  No transcript available, skipping detailed analysis")
            continue
        
        # Analyze style
        analysis = analyze_video_style(url, video_id, title, duration, transcript)
        if not analysis:
            logger.warning(f"⚠️  Style analysis failed, skipping")
            continue
        
        # Create template
        template = create_style_template(url, video_id, video_info, analysis)
        templates.append(template)
        
        # Save individual template
        template_file = output_dir / f"template_{video_id}.json"
        template_file.write_text(json.dumps(asdict(template), indent=2))
        logger.success(f"💾 Saved template: {template_file.name}")
    
    # Aggregate patterns
    if templates:
        print(f"\n{'='*80}")
        print("📊 Aggregating Patterns")
        print(f"{'='*80}\n")
        
        aggregated = aggregate_templates(templates)
        
        # Save aggregated results
        aggregated_file = output_dir / "aggregated_templates.json"
        aggregated_file.write_text(json.dumps(aggregated, indent=2))
        logger.success(f"💾 Saved aggregated templates: {aggregated_file}")
        
        # Print summary
        print("\n📈 Pattern Summary:")
        print(f"  Total templates: {aggregated['total_templates']}")
        print(f"  Most common hook: {aggregated['most_common_hook']}")
        print(f"  Most common pacing: {aggregated['most_common_pacing']}")
        print(f"  Most common style: {aggregated['most_common_style']}")
        print(f"\n  Hook archetypes: {aggregated['hook_archetypes']}")
        print(f"  Content styles: {aggregated['content_styles']}")
        print(f"  CTA types: {aggregated['cta_types']}")
        
        print(f"\n✅ Analysis complete! Templates saved to: {output_dir}")
    else:
        print("\n❌ No templates created. Check errors above.")


if __name__ == "__main__":
    main()

