"""
Generate Video Script from Style Template
=========================================
Uses a video style template to generate a script following that template's
structure, hook pattern, and style for a new topic.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from openai import OpenAI
from loguru import logger

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


def load_template(template_id: str) -> Optional[Dict[str, Any]]:
    """Load a video style template"""
    template_path = Path("Backend/data/video_style_templates") / f"template_{template_id}.json"
    
    if not template_path.exists():
        logger.error(f"Template not found: {template_path}")
        return None
    
    with open(template_path, 'r') as f:
        return json.load(f)


def generate_script_from_template(
    template: Dict[str, Any],
    topic: str,
    duration_seconds: int = 60
) -> Dict[str, Any]:
    """Generate a script following a template's style"""
    
    logger.info(f"📝 Generating script for: {topic}")
    logger.info(f"📋 Using template: {template['source_video_title']}")
    
    # Extract template elements
    hook_archetype = template.get("hook_archetype", "")
    hook_examples = template.get("hook_examples", [])
    beat_sheet = template.get("beat_sheet_template", [])
    content_style = template.get("content_style", "explainer")
    tone = template.get("tone", "casual")
    pacing = template.get("pacing", "medium")
    replication_guide = template.get("replication_guide", "")
    key_patterns = template.get("key_patterns", [])
    
    # Build prompt
    prompt = f"""Generate a video script following this exact style template:

TEMPLATE STYLE:
- Source Video: {template['source_video_title']}
- Hook Archetype: {hook_archetype}
- Hook Examples: {', '.join(hook_examples[:3])}
- Content Style: {content_style}
- Tone: {tone}
- Pacing: {pacing}

BEAT SHEET STRUCTURE:
{json.dumps(beat_sheet, indent=2)}

KEY PATTERNS TO FOLLOW:
{chr(10).join(f'- {pattern}' for pattern in key_patterns)}

REPLICATION GUIDE:
{replication_guide}

TOPIC: {topic}
TARGET DURATION: {duration_seconds} seconds (~{int(duration_seconds * 2.5)} words)

REQUIREMENTS:
1. Use the EXACT hook archetype pattern from the template, adapted for the topic
2. Follow the beat sheet structure with appropriate timing
3. Match the tone and pacing of the template
4. Include all key patterns from the template
5. Write in a conversational, engaging style
6. End with an engagement CTA matching the template's style

OUTPUT FORMAT:
Return a JSON object with:
{{
  "hook": "The opening hook following the template's archetype",
  "script": "The full script text",
  "beats": [
    {{"role": "hook", "start_sec": 0, "end_sec": 5, "text": "..."}},
    {{"role": "...", "start_sec": ..., "end_sec": ..., "text": "..."}}
  ],
  "cta": "The closing call-to-action",
  "estimated_duration": {duration_seconds},
  "word_count": 0
}}

Write ONLY valid JSON, no markdown, no code blocks."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert video script writer who creates engaging scripts that follow specific style templates. Always respond with valid JSON only."
                },
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.7,
            max_tokens=2000
        )
        
        result = json.loads(response.choices[0].message.content)
        
        # Calculate word count if not provided
        if "word_count" not in result or result["word_count"] == 0:
            result["word_count"] = len(result.get("script", "").split())
        
        logger.success(f"✅ Script generated: {result['word_count']} words")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error generating script: {e}")
        return {}


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate video script from style template")
    parser.add_argument("--topic", required=True, help="Topic for the script")
    parser.add_argument("--template", default="DScr9hwfcas", help="Template ID (default: DScr9hwfcas)")
    parser.add_argument("--duration", type=int, default=60, help="Target duration in seconds (default: 60)")
    parser.add_argument("--output", help="Output file path (default: print to stdout)")
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("🎬 Video Script Generator from Template")
    print("=" * 80)
    print()
    
    # Load template
    logger.info(f"📂 Loading template: {args.template}")
    template = load_template(args.template)
    
    if not template:
        print("❌ Failed to load template")
        return
    
    logger.info(f"✅ Template loaded: {template['source_video_title']}")
    print()
    
    # Generate script
    result = generate_script_from_template(template, args.topic, args.duration)
    
    if not result:
        print("❌ Failed to generate script")
        return
    
    # Output result
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2))
        logger.success(f"💾 Script saved to: {output_path}")
    else:
        print("\n" + "=" * 80)
        print("📝 GENERATED SCRIPT")
        print("=" * 80)
        print()
        print(f"HOOK: {result.get('hook', 'N/A')}")
        print()
        print("SCRIPT:")
        print(result.get('script', 'N/A'))
        print()
        print(f"CTA: {result.get('cta', 'N/A')}")
        print()
        print("=" * 80)
        print("BEAT BREAKDOWN:")
        print("=" * 80)
        for beat in result.get('beats', []):
            print(f"[{beat.get('start_sec', 0)}s - {beat.get('end_sec', 0)}s] {beat.get('role', 'unknown')}:")
            print(f"  {beat.get('text', '')[:100]}...")
            print()
        print(f"Estimated Duration: {result.get('estimated_duration', 0)}s")
        print(f"Word Count: {result.get('word_count', 0)}")


if __name__ == "__main__":
    main()

