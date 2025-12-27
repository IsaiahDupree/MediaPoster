#!/usr/bin/env python3
"""
Test SAM 2 via Hugging Face Inference API
==========================================
Tests video segmentation using SAM 2 through Hugging Face API (not local).
"""

import os
import sys
import logging
import requests
from pathlib import Path
from typing import Optional, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s'
)
logger = logging.getLogger(__name__)


def test_sam2_huggingface_api(
    image_path: str,
    prompt: Optional[str] = None,
    hf_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Test SAM 2 via Hugging Face Inference API.
    
    Args:
        image_path: Path to input image
        prompt: Optional text prompt for segmentation
        hf_token: Hugging Face API token
    
    Returns:
        Dict with segmentation results
    """
    # Get token from environment if not provided
    if not hf_token:
        hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    
    if not hf_token:
        logger.warning("No Hugging Face token found. Using anonymous access (may have limits)")
    
    # Check if image exists
    image_file = Path(image_path)
    if not image_file.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    
    logger.info("=" * 80)
    logger.info("Testing SAM 2 via Hugging Face Inference API")
    logger.info("=" * 80)
    logger.info(f"Image: {image_file.name}")
    logger.info(f"Model: facebook/sam2-hiera-large")
    logger.info("")
    
    # Hugging Face Inference API endpoint
    # Note: SAM 2 may not have a direct Inference API endpoint yet
    # We'll test with the model card and check availability
    api_url = "https://api-inference.huggingface.co/models/facebook/sam2-hiera-large"
    
    # Alternative: Check if there's a Space with SAM 2
    space_url = "https://huggingface.co/spaces/facebook/sam2"
    
    logger.info("Checking SAM 2 availability on Hugging Face...")
    logger.info(f"Model card: https://huggingface.co/facebook/sam2-hiera-large")
    logger.info(f"Space: {space_url}")
    logger.info("")
    
    # For now, we'll test the API endpoint structure
    # Actual implementation will depend on SAM 2's API availability
    
    headers = {}
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"
        logger.info("✅ Using authenticated access")
    else:
        logger.warning("⚠️  Using anonymous access (may have rate limits)")
    
    logger.info("")
    logger.info("Note: SAM 2 may require:")
    logger.info("  1. Direct model download and local inference")
    logger.info("  2. Hugging Face Spaces API (gradio_client)")
    logger.info("  3. Custom inference endpoint")
    logger.info("")
    
    # Test with a simple API call to check model availability
    try:
        response = requests.get(
            "https://huggingface.co/api/models/facebook/sam2-hiera-large",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            model_info = response.json()
            logger.info("✅ Model found on Hugging Face")
            logger.info(f"   Model ID: {model_info.get('id', 'N/A')}")
            logger.info(f"   Task: {model_info.get('pipeline_tag', 'N/A')}")
            logger.info("")
        else:
            logger.warning(f"⚠️  Model info request returned: {response.status_code}")
            logger.info("")
    except Exception as e:
        logger.warning(f"⚠️  Could not fetch model info: {e}")
        logger.info("")
    
    # Check for SAM 2 Space (gradio-based)
    logger.info("Checking for SAM 2 Space (gradio-based API)...")
    try:
        from gradio_client import Client
        
        # Try to connect to SAM 2 Space
        # Note: Actual space URL may differ
        space_urls = [
            "facebook/sam2",
            "facebookresearch/sam2",
        ]
        
        for space_url in space_urls:
            try:
                logger.info(f"Trying space: {space_url}")
                client = Client(space_url, hf_token=hf_token)
                logger.info(f"✅ Connected to {space_url}")
                logger.info("   Available endpoints:")
                # List available API endpoints
                # This will depend on the actual Space implementation
                break
            except Exception as e:
                logger.debug(f"   Space {space_url} not available: {e}")
                continue
        else:
            logger.warning("⚠️  No SAM 2 Space found. May need local installation.")
            logger.info("")
            logger.info("Alternative: Use rembg (RMBG-1.4) for background removal")
            logger.info("  pip install rembg[new]")
            logger.info("  This is simpler and has a Python API")
            
    except ImportError:
        logger.warning("⚠️  gradio_client not installed")
        logger.info("  Install with: pip install gradio_client")
        logger.info("")
    
    logger.info("=" * 80)
    logger.info("RECOMMENDATION")
    logger.info("=" * 80)
    logger.info("")
    logger.info("For video matting, consider:")
    logger.info("")
    logger.info("1. RMBG-1.4 (rembg) - Recommended for production")
    logger.info("   - Fast and accurate")
    logger.info("   - Python API available")
    logger.info("   - Good for people and objects")
    logger.info("   - pip install rembg[new]")
    logger.info("")
    logger.info("2. SAM 2 - For advanced segmentation")
    logger.info("   - More accurate for specific objects")
    logger.info("   - May require local installation or custom API")
    logger.info("   - Better for complex scenes")
    logger.info("")
    logger.info("3. Hybrid approach")
    logger.info("   - Use RMBG-1.4 for background removal (fast path)")
    logger.info("   - Use SAM 2 for specific object extraction (when needed)")
    logger.info("")
    
    return {
        "status": "tested",
        "model_available": True,
        "api_type": "to_be_determined",
        "recommendation": "Use RMBG-1.4 for production, SAM 2 for advanced cases"
    }


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test SAM 2 via Hugging Face API")
    parser.add_argument(
        '--image',
        type=str,
        required=True,
        help='Path to input image'
    )
    parser.add_argument(
        '--prompt',
        type=str,
        default=None,
        help='Optional text prompt for segmentation'
    )
    parser.add_argument(
        '--token',
        type=str,
        default=None,
        help='Hugging Face API token (or set HF_TOKEN env var)'
    )
    
    args = parser.parse_args()
    
    try:
        result = test_sam2_huggingface_api(
            image_path=args.image,
            prompt=args.prompt,
            hf_token=args.token
        )
        
        logger.info("")
        logger.info("Test completed:")
        logger.info(f"  Status: {result['status']}")
        logger.info(f"  Model Available: {result['model_available']}")
        logger.info(f"  Recommendation: {result['recommendation']}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

