"""
Analyze Competitor Analysis Video
==================================
Downloads YouTube video, transcribes it, and analyzes what competitor analysis
features are discussed to identify gaps in our current tools.
"""

import re
import sys
from pathlib import Path
from typing import List, Dict, Any
import json

def parse_vtt(vtt_path: Path) -> str:
    """Parse VTT subtitle file and extract full transcript."""
    text_lines = []
    
    with open(vtt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # VTT format: timestamp lines followed by text
    # Pattern: 00:00:00.000 --> 00:00:03.000
    # Then text on next lines until blank line
    
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
            while i < len(lines) and lines[i].strip() and not '-->' in lines[i]:
                text_line = lines[i].strip()
                # Remove HTML tags like <c>, <00:00:00.960>
                text_line = re.sub(r'<[^>]+>', '', text_line)
                if text_line:
                    text_parts.append(text_line)
                i += 1
            if text_parts:
                # Join text parts and deduplicate
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


def extract_features_from_transcript(transcript: str) -> Dict[str, Any]:
    """
    Extract competitor analysis features mentioned in transcript.
    Uses keyword matching and context analysis.
    """
    features = {
        "mentioned_features": [],
        "capabilities": [],
        "gaps_identified": [],
        "keywords": []
    }
    
    transcript_lower = transcript.lower()
    
    # Keywords to look for
    feature_keywords = {
        "content research": ["content research", "research", "analyze content"],
        "trending topics": ["trending", "trends", "viral topics", "hot topics"],
        "competitor analysis": ["competitor", "competitors", "analyze competitors"],
        "engagement analysis": ["engagement", "engagement rate", "likes", "comments", "shares"],
        "audience analysis": ["audience", "demographics", "follower", "viewer"],
        "content performance": ["performance", "views", "metrics", "analytics"],
        "hook analysis": ["hook", "hooks", "opening", "attention grabber"],
        "cta analysis": ["cta", "call to action", "call-to-action"],
        "posting schedule": ["schedule", "posting time", "best time"],
        "hashtag analysis": ["hashtag", "hashtags", "#"],
        "content ideas": ["content ideas", "ideas", "suggestions"],
        "automation": ["automate", "automation", "automatic", "auto"],
        "ai analysis": ["ai", "artificial intelligence", "machine learning"],
        "predictive": ["predict", "prediction", "forecast", "predictive"],
        "insights": ["insight", "insights", "data", "analytics"],
        "viral potential": ["viral", "virality", "viral potential"],
        "content calendar": ["calendar", "content calendar", "schedule"],
        "performance tracking": ["track", "tracking", "monitor", "performance"],
    }
    
    # Find mentioned features
    for feature_name, keywords in feature_keywords.items():
        for keyword in keywords:
            if keyword in transcript_lower:
                if feature_name not in features["mentioned_features"]:
                    features["mentioned_features"].append(feature_name)
                features["keywords"].append(keyword)
    
    # Extract specific capabilities mentioned
    capability_patterns = [
        r"can ([\w\s]+)",
        r"does ([\w\s]+)",
        r"analyzes? ([\w\s]+)",
        r"tracks? ([\w\s]+)",
        r"predicts? ([\w\s]+)",
        r"identifies? ([\w\s]+)",
        r"finds? ([\w\s]+)",
    ]
    
    for pattern in capability_patterns:
        matches = re.findall(pattern, transcript_lower, re.IGNORECASE)
        for match in matches:
            capability = match.strip()[:100]  # Limit length
            if len(capability) > 5 and capability not in features["capabilities"]:
                features["capabilities"].append(capability)
    
    return features


def compare_with_current_tools(video_features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compare video features with our current competitor analysis tools.
    """
    current_tools = {
        "competitor_collector": [
            "profile data",
            "post collection",
            "metrics collection",
        ],
        "deep_audit": [
            "hook analysis",
            "cta analysis",
            "style fingerprint",
            "beat sheet",
            "angle type",
            "content pillar",
            "positioning",
        ],
        "funnel_mapper": [
            "entry points",
            "lead magnets",
            "offer stack",
            "conversion paths",
        ],
        "post_ranker": [
            "velocity scoring",
            "engagement scoring",
            "viral potential",
            "template worthiness",
        ],
        "report_generator": [
            "strategy reports",
            "insights",
        ],
        "template_exporter": [
            "remotion templates",
            "format extraction",
        ],
    }
    
    gaps = []
    covered = []
    
    # Check each mentioned feature
    for feature in video_features["mentioned_features"]:
        found = False
        for tool, capabilities in current_tools.items():
            if any(feature.lower() in cap.lower() or cap.lower() in feature.lower() 
                   for cap in capabilities):
                covered.append({
                    "feature": feature,
                    "tool": tool,
                    "capability": [c for c in capabilities if feature.lower() in c.lower() or c.lower() in feature.lower()][0] if any(feature.lower() in c.lower() or c.lower() in feature.lower() for c in capabilities) else capabilities[0]
                })
                found = True
                break
        
        if not found:
            gaps.append(feature)
    
    return {
        "covered": covered,
        "gaps": gaps,
        "current_tools": current_tools,
    }


def main():
    """Main analysis function."""
    print("=" * 80)
    print("Competitor Analysis Video Analysis")
    print("=" * 80)
    print()
    
    # Find VTT file
    vtt_dir = Path("data/competitor_analysis")
    vtt_files = list(vtt_dir.glob("*.vtt"))
    
    if not vtt_files:
        print("❌ No VTT file found. Please download subtitles first.")
        return
    
    vtt_file = vtt_files[0]
    print(f"📄 Reading transcript: {vtt_file.name}")
    print()
    
    # Parse transcript
    transcript = parse_vtt(vtt_file)
    
    # Save full transcript
    transcript_file = vtt_dir / "transcript.txt"
    transcript_file.write_text(transcript)
    print(f"✅ Saved full transcript: {transcript_file}")
    print()
    
    # Extract features
    print("🔍 Extracting features from transcript...")
    video_features = extract_features_from_transcript(transcript)
    
    print(f"\n📊 Features Mentioned ({len(video_features['mentioned_features'])}):")
    for feature in video_features["mentioned_features"]:
        print(f"  - {feature}")
    
    print(f"\n💡 Capabilities Mentioned ({len(video_features['capabilities'])}):")
    for i, capability in enumerate(video_features["capabilities"][:20], 1):  # Top 20
        print(f"  {i}. {capability}")
    
    # Compare with current tools
    print("\n" + "=" * 80)
    print("Comparison with Current Tools")
    print("=" * 80)
    print()
    
    comparison = compare_with_current_tools(video_features)
    
    print("✅ Covered Features:")
    for item in comparison["covered"]:
        print(f"  - {item['feature']} → {item['tool']} ({item['capability']})")
    
    print(f"\n❌ Potential Gaps ({len(comparison['gaps'])}):")
    for gap in comparison["gaps"]:
        print(f"  - {gap}")
    
    # Save analysis
    analysis_file = vtt_dir / "analysis.json"
    analysis_data = {
        "video_url": "https://youtu.be/mBFXaUO7jhI",
        "transcript_length": len(transcript),
        "features": video_features,
        "comparison": comparison,
    }
    analysis_file.write_text(json.dumps(analysis_data, indent=2))
    print(f"\n💾 Saved analysis: {analysis_file}")
    
    # Summary
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Total features mentioned: {len(video_features['mentioned_features'])}")
    print(f"Covered by current tools: {len(comparison['covered'])}")
    print(f"Potential gaps: {len(comparison['gaps'])}")
    print()
    
    if comparison["gaps"]:
        print("⚠️  Gaps to investigate:")
        for gap in comparison["gaps"]:
            print(f"   - {gap}")
    else:
        print("✅ All mentioned features appear to be covered!")


if __name__ == "__main__":
    main()

