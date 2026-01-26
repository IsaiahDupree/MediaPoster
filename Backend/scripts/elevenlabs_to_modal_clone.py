"""
ElevenLabs to Modal Voice Clone Pipeline
========================================
Generates voice samples from ElevenLabs and uses them to create
a Modal voice clone for local/offline usage.

Usage:
    python scripts/elevenlabs_to_modal_clone.py
"""

import os
import asyncio
import httpx
from pathlib import Path
from datetime import datetime
from loguru import logger

# ElevenLabs Configuration
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "sk_2252654c95162d4e0e644a1e2a540892d3faa828a36cace5")
ELEVENLABS_VOICE_ID = "k0HDiJKO5QdXkGN6NSLI"
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

# Output directory
OUTPUT_DIR = Path("/tmp/elevenlabs_voice_clone")


async def get_voice_info(voice_id: str) -> dict:
    """Get information about an ElevenLabs voice"""
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ELEVENLABS_BASE_URL}/voices/{voice_id}",
            headers={"xi-api-key": ELEVENLABS_API_KEY}
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get voice info: {response.status_code} - {response.text}")
            return {}


async def generate_elevenlabs_sample(
    text: str,
    voice_id: str,
    output_path: Path,
    model_id: str = "eleven_monolingual_v1"
) -> Path:
    """Generate a voice sample from ElevenLabs"""
    
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True
        }
    }
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    logger.info(f"Generating ElevenLabs sample: {len(text)} chars")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(response.content)
            logger.success(f"Generated: {output_path} ({len(response.content)} bytes)")
            return output_path
        else:
            logger.error(f"ElevenLabs API error: {response.status_code} - {response.text}")
            raise Exception(f"Failed to generate audio: {response.status_code}")


async def create_voice_reference_set(voice_id: str, output_dir: Path) -> list[Path]:
    """Generate multiple voice samples for better cloning quality"""
    
    # Sample texts for voice reference (variety of sounds and patterns)
    sample_texts = [
        # Long-form narration
        """The art of voice cloning has evolved dramatically in recent years. 
        What once required extensive studio recordings can now be achieved with 
        just a few minutes of reference audio. This technology opens up incredible 
        possibilities for content creators, allowing them to scale their production 
        while maintaining a consistent personal voice across all content.""",
        
        # Technical explanation
        """To configure the voice cloning system, first ensure your Modal deployment 
        is active. Then navigate to the voice profiles section in the dashboard. 
        Upload your reference audio files, and the system will analyze the voice 
        characteristics including pitch, tempo, and tonal qualities.""",
        
        # Conversational style
        """Hey everyone, welcome back to another video! Today we're going to dive 
        deep into something really exciting. I've been working on this for weeks, 
        and I can't wait to show you what we've built. Let's get started!""",
        
        # Numbers and technical terms
        """Version three point five was released on January twenty-first, twenty 
        twenty-six. The new API supports up to one hundred concurrent requests, 
        with latency improvements of approximately forty-two percent compared to 
        the previous version. The endpoint URL is api dot mediaposter dot io.""",
        
        # Emotional range
        """This is absolutely incredible! I'm so excited to share this with you. 
        But wait, there's a catch - we need to be careful here. The process can 
        be tricky, and I've made plenty of mistakes along the way. Trust me, 
        you'll want to pay close attention to these next steps.""",
    ]
    
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []
    
    for i, text in enumerate(sample_texts):
        output_path = output_dir / f"reference_{i:02d}.mp3"
        try:
            await generate_elevenlabs_sample(text, voice_id, output_path)
            generated_files.append(output_path)
            # Small delay between requests
            await asyncio.sleep(1)
        except Exception as e:
            logger.warning(f"Failed to generate sample {i}: {e}")
    
    return generated_files


async def combine_audio_files(audio_files: list[Path], output_path: Path) -> Path:
    """Combine multiple audio files into one reference file"""
    import subprocess
    
    # Create file list for ffmpeg
    list_path = output_path.parent / "files.txt"
    with open(list_path, "w") as f:
        for audio_file in audio_files:
            f.write(f"file '{audio_file}'\n")
    
    # Combine with ffmpeg
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(list_path),
        "-c", "copy",
        str(output_path)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.success(f"Combined audio: {output_path}")
        # Cleanup
        list_path.unlink()
        return output_path
    else:
        logger.error(f"FFmpeg error: {result.stderr}")
        raise Exception("Failed to combine audio files")


async def main():
    """Main pipeline: ElevenLabs → Reference Audio → Modal Clone"""
    
    print("\n" + "="*60)
    print("ElevenLabs to Modal Voice Clone Pipeline")
    print("="*60 + "\n")
    
    # Step 1: Get voice info
    logger.info(f"Getting voice info for: {ELEVENLABS_VOICE_ID}")
    voice_info = await get_voice_info(ELEVENLABS_VOICE_ID)
    
    if voice_info:
        print(f"Voice Name: {voice_info.get('name', 'Unknown')}")
        print(f"Category: {voice_info.get('category', 'Unknown')}")
        print(f"Labels: {voice_info.get('labels', {})}")
        print()
    
    # Step 2: Generate reference samples
    logger.info("Generating voice reference samples...")
    reference_files = await create_voice_reference_set(
        ELEVENLABS_VOICE_ID,
        OUTPUT_DIR / "samples"
    )
    
    print(f"\n✅ Generated {len(reference_files)} reference samples")
    for f in reference_files:
        print(f"   - {f.name}")
    
    # Step 3: Combine into single reference file
    if len(reference_files) > 1:
        combined_path = OUTPUT_DIR / "combined_reference.mp3"
        await combine_audio_files(reference_files, combined_path)
        print(f"\n✅ Combined reference: {combined_path}")
    else:
        combined_path = reference_files[0] if reference_files else None
    
    # Step 4: Display Modal clone instructions
    print("\n" + "="*60)
    print("Next Steps: Create Modal Voice Clone")
    print("="*60)
    print(f"""
To use this reference audio with Modal voice cloning:

1. Upload reference to cloud storage (S3, GCS, or serve locally)
   Reference file: {combined_path}

2. Create voice profile in MediaPoster:
   
   from services.voice.modal_voice_service import ModalVoiceService
   
   service = ModalVoiceService()
   
   # Create embedding from reference
   result = await service.create_voice_embedding(
       voice_reference_urls=["https://your-storage/combined_reference.mp3"],
       name="ElevenLabs Clone - {ELEVENLABS_VOICE_ID}"
   )
   
   embedding_id = result["embedding_id"]

3. Generate speech with cloned voice:
   
   audio = await service.generate_with_embedding(
       text="Your text here",
       embedding_id=embedding_id
   )

Output Directory: {OUTPUT_DIR}
""")
    
    # Step 5: Test generation with the voice
    print("\n" + "="*60)
    print("Test: Generating sample with ElevenLabs voice")
    print("="*60)
    
    test_text = """This is a test of the voice cloning pipeline. 
    We're using ElevenLabs to generate this reference audio, 
    which will then be used to create a Modal voice clone 
    for scalable, offline voice synthesis."""
    
    test_output = OUTPUT_DIR / "test_output.mp3"
    await generate_elevenlabs_sample(test_text, ELEVENLABS_VOICE_ID, test_output)
    
    print(f"\n✅ Test audio generated: {test_output}")
    print(f"\n🎉 Pipeline complete! Files saved to: {OUTPUT_DIR}")
    
    return {
        "reference_files": [str(f) for f in reference_files],
        "combined_reference": str(combined_path) if combined_path else None,
        "test_output": str(test_output),
        "voice_id": ELEVENLABS_VOICE_ID,
        "voice_info": voice_info
    }


if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nResult: {result}")
