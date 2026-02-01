#!/usr/bin/env python3
"""
End-to-End Demo: MediaPoster Microservices Pipeline

Demonstrates the full content analysis pipeline using:
- media-pipeline (port 6004): Video analysis, format detection
- content-intelligence (port 6006): FATE scoring, awareness classification, sentiment

This script shows how MediaPoster can use microservices for content processing.
"""
import asyncio
import httpx
import json
from typing import Dict, Any

# Service URLs
MEDIA_PIPELINE = "http://localhost:6004"
CONTENT_INTEL = "http://localhost:6006"


async def demo_content_analysis_pipeline():
    """
    Demo: Analyze content through the full pipeline.
    
    Flow:
    1. Analyze video format (media-pipeline)
    2. Score content with FATE framework (content-intelligence)
    3. Classify awareness level (content-intelligence)
    4. Analyze sentiment (content-intelligence)
    5. Generate viral titles (content-intelligence)
    """
    print("\n" + "="*70)
    print("🚀 MediaPoster Microservices Pipeline Demo")
    print("="*70)
    
    # Sample content for analysis
    sample_content = {
        "transcript": """
        Most founders fail because they don't understand this one pattern.
        I've helped 127 entrepreneurs discover the mechanism behind viral growth.
        If you're like me, you've felt the frustration of posting every day
        with zero results. But then everything changed when I finally cracked
        the code. Here's the truth nobody tells you about content marketing...
        """,
        "title": "The Growth Pattern Nobody Talks About",
        "platform": "tiktok"
    }
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # Step 1: Format Detection
        print("\n📹 Step 1: Format Detection (media-pipeline)")
        print("-" * 50)
        try:
            response = await client.post(
                f"{MEDIA_PIPELINE}/api/format/detect",
                json={
                    "file_path": "/tmp/demo_video.mp4",
                    "transcript": sample_content["transcript"]
                }
            )
            if response.status_code == 200:
                data = response.json()
                fmt = data.get("format", {})
                print(f"   Primary Format: {fmt.get('primary_format', 'unknown')}")
                print(f"   Has Speech: {fmt.get('has_speech', False)}")
                print(f"   Implementation: {data.get('implementation', 'unknown')}")
            else:
                print(f"   ❌ Error: HTTP {response.status_code}")
        except httpx.ConnectError:
            print("   ⚠️ media-pipeline not running (port 6004)")
        
        # Step 2: FATE Scoring
        print("\n🎯 Step 2: FATE Scoring (content-intelligence)")
        print("-" * 50)
        try:
            response = await client.post(
                f"{CONTENT_INTEL}/api/score/fate",
                json={"content": sample_content["transcript"]}
            )
            if response.status_code == 200:
                data = response.json()
                scores = data.get("fate_score", {})
                print(f"   Focus:     {scores.get('focus', 0):.2f}")
                print(f"   Authority: {scores.get('authority', 0):.2f}")
                print(f"   Tribe:     {scores.get('tribe', 0):.2f}")
                print(f"   Emotion:   {scores.get('emotion', 0):.2f}")
                print(f"   Overall:   {scores.get('overall', 0):.2f}")
                print(f"   Implementation: {data.get('implementation', 'unknown')}")
            else:
                print(f"   ❌ Error: HTTP {response.status_code}")
        except httpx.ConnectError:
            print("   ⚠️ content-intelligence not running (port 6006)")
        
        # Step 3: Awareness Classification
        print("\n🧠 Step 3: Awareness Classification (content-intelligence)")
        print("-" * 50)
        try:
            response = await client.post(
                f"{CONTENT_INTEL}/api/classify/awareness",
                json={"content": sample_content["transcript"]}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"   Level: {data.get('awareness_level', 'unknown')}")
                print(f"   Confidence: {data.get('confidence', 0):.2f}")
                print(f"   Implementation: {data.get('implementation', 'unknown')}")
            else:
                print(f"   ❌ Error: HTTP {response.status_code}")
        except httpx.ConnectError:
            print("   ⚠️ content-intelligence not running (port 6006)")
        
        # Step 4: Sentiment Analysis
        print("\n💭 Step 4: Sentiment Analysis (content-intelligence)")
        print("-" * 50)
        try:
            response = await client.post(
                f"{CONTENT_INTEL}/api/analyze/sentiment",
                json={"text": sample_content["transcript"]}
            )
            if response.status_code == 200:
                data = response.json()
                print(f"   Sentiment: {data.get('sentiment', 'unknown')}")
                print(f"   Score: {data.get('score', 0):.2f}")
                print(f"   Confidence: {data.get('confidence', 0):.2f}")
                emotions = data.get("emotions", {})
                if emotions:
                    print(f"   Emotions: {', '.join(f'{k}={v:.2f}' for k, v in emotions.items())}")
                print(f"   Implementation: {data.get('implementation', 'unknown')}")
            else:
                print(f"   ❌ Error: HTTP {response.status_code}")
        except httpx.ConnectError:
            print("   ⚠️ content-intelligence not running (port 6006)")
        
        # Step 5: Title Generation
        print("\n✨ Step 5: Title Generation (content-intelligence)")
        print("-" * 50)
        try:
            response = await client.post(
                f"{CONTENT_INTEL}/api/generate/title",
                json={
                    "content": sample_content["transcript"],
                    "platform": sample_content["platform"],
                    "style": "viral",
                    "count": 3
                }
            )
            if response.status_code == 200:
                data = response.json()
                titles = data.get("titles", [])
                for i, title in enumerate(titles, 1):
                    print(f"   {i}. {title}")
                print(f"   AI Provider: {data.get('ai_provider', 'unknown')}")
            else:
                print(f"   ❌ Error: HTTP {response.status_code}")
        except httpx.ConnectError:
            print("   ⚠️ content-intelligence not running (port 6006)")
    
    # Summary
    print("\n" + "="*70)
    print("✅ Pipeline Demo Complete!")
    print("="*70)
    print("""
To run this demo with real services:

1. Start media-pipeline:
   cd ~/Documents/Software/media-pipeline
   source venv/bin/activate
   python app.py

2. Start content-intelligence:
   cd ~/Documents/Software/content-intelligence
   source venv/bin/activate
   python app.py

3. Run this demo:
   python scripts/demo_microservices_pipeline.py
""")


if __name__ == "__main__":
    asyncio.run(demo_content_analysis_pipeline())
