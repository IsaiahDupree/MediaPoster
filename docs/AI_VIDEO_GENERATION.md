# AI Video Generation with Sora

## Overview

The MediaPoster system now supports AI video generation with a swappable model architecture. Currently implements OpenAI Sora, with easy extension points for RunwayML, Pika, and other providers.

## Quick Start

### Basic Usage

```python
from modules.ai.video_model_factory import create_video_model
from modules.ai.video_model_interface import VideoGenerationRequest

# Create Sora model
model = create_video_model("sora", model_variant="sora-2")

# Generate video
request = VideoGenerationRequest(
    prompt="A serene lake at sunset with mountains in the background",
    width=1280,
    height=720,
    duration_seconds=8
)

job = model.create_and_wait(request)

if job.status == VideoStatus.COMPLETED:
    model.download_video(job.job_id, "output.mp4")
```

### Model Variants

```python
# Fast iteration (sora-2)
fast_model = create_video_model("sora", model_variant="sora-2")

# Production quality (sora-2-pro)
pro_model = create_video_model("sora", model_variant="sora-2-pro")
```

## Architecture

### Swappable Models

The system uses an interface-based architecture for easy model switching:

```
VideoModelInterface (abstract)
    ├── SoraVideoModel (OpenAI Sora)
    ├── RunwayMLModel (coming soon)
    └── PikaModel (coming soon)
```

### Adding New Models

To add a new model provider:

1. Create `YourModel` class in `modules/ai/`
2. Implement `VideoModelInterface`
3. Add to factory in `video_model_factory.py`

```python
class MyCustomModel(VideoModelInterface):
    def create_video(self, request):
        # Your implementation
        pass
    
    def get_status(self, job_id):
        # Your implementation
        pass
    
    # ... other methods
```

## Integration with Clip Generation

Generate AI videos and use in content workflow:

```python
# 1. Generate video with Sora
sora = create_video_model("sora")
job = sora.create_and_wait(VideoGenerationRequest(
    prompt="Product demo in futuristic setting",
    duration_seconds=10
))

# 2. Download locally
video_path = sora.download_video(job.job_id, "ai_video.mp4")

# 3. Upload to Blotato
from modules.publishing.blotato_client import BlotatoClient
blotato = BlotatoClient()
blotato_url = blotato.upload_media(video_path)

# 4. Post to platforms
blotato.create_post(
    account_id="807",
    platform="instagram",
    text="AI-generated product demo!",
    media_urls=[blotato_url]
)
```

## Configuration

Add to `.env`:
```bash
# OpenAI for Sora
OPENAI_API_KEY=sk-...

# Future providers
RUNWAY_API_KEY=...
PIKA_API_KEY=...
```

## API Reference

### VideoGenerationRequest
- `prompt`: str - Text description
- `model`: str - Model variant
- `width`: int - Video width (720p: 1280, 1080p: 1920)
- `height`: int - Video height (720p: 720, 1080p: 1080)
- `duration_seconds`: int - 2-20 seconds
- `input_image`: Optional[str] - Reference image path

### VideoGenerationJob
- `job_id`: str - Unique identifier
- `status`: VideoStatus - QUEUED, IN_PROGRESS, COMPLETED, FAILED
- `progress`: Optional[int] - 0-100%
- `video_url`: Optional[str] - Download URL when complete
- `error_message`: Optional[str] - Error details if failed

### SoraVideoModel Methods

**Core Methods:**
- `create_video(request)` - Start generation
- `get_status(job_id)` - Check progress
- `download_video(job_id, path)` - Get MP4
- `create_and_wait(request)` - Convenience method

**Advanced:**
- `remix_video(job_id, prompt)` - Modify existing video
- `list_jobs(limit)` - Get recent jobs
- `delete_video(job_id)` - Remove from storage

## Examples

### Social Media Content
```python
request = VideoGenerationRequest(
    prompt="Product showcase in modern minimalist setting, slow rotation, soft lighting",
    model="sora-2-pro",
    duration_seconds=15
)
```

### Quick Iteration
```python
# Generate fast draft
draft = sora.create_video(VideoGenerationRequest(
    prompt="Concept A",
    model="sora-2"
))

# Remix with changes
final = sora.remix_video(draft.job_id, 
    "Change color palette to warm tones"
)
```

### Batch Generation
```python
prompts = [
    "Morning coffee scene",
    "Sunset beach walk",
    "City street night"
]

jobs = []
for prompt in prompts:
    job = model.create_video(VideoGenerationRequest(
        prompt=prompt,
        duration_seconds=8
    ))
    jobs.append(job)

# Wait for all to complete
for job in jobs:
    while job.status != VideoStatus.COMPLETED:
        job = model.get_status(job.job_id)
        time.sleep(10)
```

## Testing

Run the test suite:
```bash
cd Backend
source venv/bin/activate
python3 test_sora.py
```

This will:
1. Initialize Sora model
2. Generate a test video
3. Monitor progress
4. Download result

## Files Created

- `modules/ai/video_model_interface.py` - Base interface
- `modules/ai/sora_model.py` - Sora implementation  
- `modules/ai/video_model_factory.py` - Model factory
- `test_sora.py` - Test script
- `docs/SORA_API.md` - API documentation

## Next Steps

1. Test Sora generation with your OpenAI API key
2. Integrate into clip generation UI
3. Add RunwayML support
4. Build video library management
