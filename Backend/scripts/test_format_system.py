#!/usr/bin/env python3
"""
Test Format-Agnostic Video Rendering System
============================================
Demonstrates the format-agnostic rendering architecture.
"""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.video_renderer import VideoRenderService, FORMAT_REGISTRY
from loguru import logger


def create_sample_content() -> dict:
    """Create sample content in universal schema."""
    return {
        "meta": {
            "project_id": "thermodynamics_explainer",
            "language": "en",
            "tone": "professional",
            "target_audience": "Science enthusiasts",
        },
        "items": [
            {
                "id": "intro",
                "type": "intro",
                "title": "Why Ice Floats on Water",
                "description": "Exploring a fascinating phenomenon in thermodynamics",
                "order": 0,
            },
            {
                "id": "topic_1",
                "type": "topic",
                "title": "Water's Unique Properties",
                "description": "As water cools, it becomes denser until it reaches 4 degrees Celsius. At this temperature, it is at its densest.",
                "audio": {
                    "narration": "As water cools, it becomes denser until it reaches 4 degrees Celsius.",
                    "duration": 40
                },
                "order": 1,
            },
            {
                "id": "topic_2",
                "type": "topic",
                "title": "The Crystalline Lattice",
                "description": "As it continues to cool and freezes into ice, the structure of water molecules changes, creating a crystalline lattice that is less dense than liquid water.",
                "audio": {
                    "narration": "As it continues to cool and freezes into ice, the structure of water molecules changes.",
                    "duration": 45
                },
                "order": 2,
            },
            {
                "id": "topic_3",
                "type": "topic",
                "title": "Life on Earth",
                "description": "This unique property is crucial for life on Earth, allowing ice to float on lakes and oceans.",
                "audio": {
                    "narration": "This unique property is crucial for life on Earth.",
                    "duration": 10
                },
                "order": 3,
            },
            {
                "id": "outro",
                "type": "outro",
                "title": "Thanks for watching!",
                "description": "Don't forget to like, share, and subscribe for more scientific insights!",
                "order": 4,
            },
        ]
    }


def test_format_system():
    """Test the format-agnostic rendering system."""
    logger.info("=" * 80)
    logger.info("🧪 Testing Format-Agnostic Video Rendering System")
    logger.info("=" * 80)
    logger.info("")
    
    # Initialize service
    service = VideoRenderService()
    logger.info("")
    
    # List available formats
    logger.info("📋 Available Formats:")
    formats = service.list_formats()
    for format_id, format_info in formats.items():
        logger.info(f"   {format_id}: {format_info['name']}")
        logger.info(f"      Layout: {format_info['layout']}")
        logger.info(f"      Description: {format_info['description']}")
    logger.info("")
    
    # Create sample content
    content = create_sample_content()
    logger.info("📝 Sample Content Created:")
    logger.info(f"   Project: {content['meta']['project_id']}")
    logger.info(f"   Items: {len(content['items'])}")
    logger.info("")
    
    # Test each format
    for format_id in FORMAT_REGISTRY.keys():
        logger.info("=" * 80)
        logger.info(f"🎬 Testing Format: {format_id}")
        logger.info("=" * 80)
        
        try:
            # Build scene graph
            scene_graph = service.build_scene_graph(content, format_id)
            
            logger.info(f"✅ Scene graph built successfully")
            logger.info(f"   Total scenes: {len(scene_graph)}")
            
            # Show scene breakdown
            for i, scene in enumerate(scene_graph):
                scene_type = scene.get("scene_type", "Unknown")
                duration = scene.get("duration", 0)
                logger.info(f"   Scene {i+1}: {scene_type} ({duration}s)")
            
            logger.info("")
            
        except Exception as e:
            logger.error(f"❌ Error testing format {format_id}: {e}")
            logger.info("")
    
    logger.info("=" * 80)
    logger.info("✅ Format System Test Complete")
    logger.info("=" * 80)


if __name__ == "__main__":
    test_format_system()

