"""
Test Sora video generation
"""
import os
import sys
from dotenv import load_dotenv
from loguru import logger

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.ai.video_model_factory import create_video_model
from modules.ai.video_model_interface import VideoGenerationRequest, VideoStatus

load_dotenv()

def test_sora_generation():
    """Test Sora video generation end-to-end"""
    logger.info("\n╔" + "="*78 + "╗")
    logger.info("║" + " "*25 + "SORA VIDEO GENERATION TEST" + " "*26 + "║")
    logger.info("╚" + "="*78 + "╝\n")
    
    # Check API key
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("❌ OPENAI_API_KEY not found in environment")
        logger.info("Add to .env: OPENAI_API_KEY=sk-...")
        return False
    
    # Create Sora model
    logger.info("STEP 1: Initialize Sora Model")
    logger.info("─"*80)
    sora = create_video_model("sora", model_variant="sora-2")
    logger.success("✅ Sora model initialized\n")
    
    # Create video request
    logger.info("STEP 2: Create Video Request")
    logger.info("─"*80)
    
    request = VideoGenerationRequest(
        prompt="A cool cat wearing sunglasses riding a motorcycle through neon-lit city streets at night, cinematic tracking shot",
        model="sora-2",
        width=1280,
        height=720,
        duration_seconds=8
    )
    
    logger.info(f"Prompt: {request.prompt}")
    logger.info(f"Resolution: {request.width}x{request.height}")
    logger.info(f"Duration: {request.duration_seconds}s\n")
    
    # Generate video
    logger.info("STEP 3: Generate Video")
    logger.info("─"*80)
    logger.info("This may take several minutes...\n")
    
    job = sora.create_and_wait(
        request,
        poll_interval=15,
        max_wait=600  # 10 minutes
    )
    
    # Check result
    logger.info("\n" + "="*80)
    logger.info("RESULTS")
    logger.info("="*80 + "\n")
    
    if job.status == VideoStatus.COMPLETED:
        logger.success("🎉 Video generation completed!")
        logger.info(f"Job ID: {job.job_id}")
        
        # Download video
        logger.info("\nSTEP 4: Download Video")
        logger.info("─"*80)
        
        output_path = "test_sora_output.mp4"
        try:
            sora.download_video(job.job_id, output_path)
            logger.success(f"✅ Video saved to: {output_path}")
            logger.info(f"\nYou can now:")
            logger.info(f"  • Upload to Blotato for posting")
            logger.info(f"  • Use in clip generation workflow")
            logger.info(f"  • Edit with other tools")
            return True
        except Exception as e:
            logger.error(f"❌ Download failed: {e}")
            return False
    else:
        logger.error(f"❌ Video generation failed")
        logger.error(f"Status: {job.status}")
        logger.error(f"Error: {job.error_message}")
        return False

if __name__ == '__main__':
    success = test_sora_generation()
    
    print("\n" + "="*80)
    if success:
        logger.success("All tests passed! Sora integration working.")
    else:
        logger.warning("Tests failed. Check logs above.")
    print("="*80 + "\n")
    
    sys.exit(0 if success else 1)
