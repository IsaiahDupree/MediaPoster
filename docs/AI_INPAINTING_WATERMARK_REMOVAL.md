# AI Inpainting Watermark Removal

## Overview

AI inpainting removes watermarks by detecting them with a trained model, then using generative AI to seamlessly fill in the area with context from surrounding pixels. This preserves the full video frame unlike cropping methods.

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│  1. DETECTION (YOLOv11s)                                    │
│     - Scans each frame for watermark                        │
│     - Returns bounding box coordinates                      │
│     - Handles missed frames via interval averaging          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2. MASK GENERATION                                         │
│     - Creates binary mask from bounding box                 │
│     - White = watermark area to remove                      │
│     - Black = preserve original pixels                      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3. INPAINTING (LAMA or E2FGVI_HQ)                          │
│     - AI generates replacement pixels                       │
│     - Uses surrounding context for seamless fill            │
│     - Preserves temporal consistency across frames          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  4. OUTPUT                                                  │
│     - Encodes cleaned frames to H.264                       │
│     - Merges original audio track                           │
│     - Full frame preserved (no cropping)                    │
└─────────────────────────────────────────────────────────────┘
```

## Models

### LAMA (Recommended)
- **Type:** Image-based inpainting
- **Speed:** ~45 seconds per video
- **Quality:** Good
- **GPU:** Works on MPS (Apple Silicon), CPU
- **Best for:** Quick processing, most use cases

### E2FGVI_HQ
- **Type:** Video-based inpainting (time-consistent)
- **Speed:** Very slow (minutes per video)
- **Quality:** Best (no flickering)
- **GPU:** CUDA only (NVIDIA)
- **Best for:** Professional output, visible watermark areas

## Installation

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend/SoraWatermarkCleaner

# Install dependencies with uv
uv sync

# Models download automatically on first run:
# - YOLOv11s detector: resources/best.pt
# - LAMA model: ~/.cache/torch/hub/
```

## Usage

### Basic Command
```bash
source .venv/bin/activate

python cli.py \
  -i /path/to/input/folder \
  -o /path/to/output/folder \
  --pattern "*.mp4" \
  -m lama
```

### Options
| Flag | Description | Default |
|------|-------------|---------|
| `-i` | Input folder with videos | Required |
| `-o` | Output folder for cleaned videos | Required |
| `-p, --pattern` | File pattern to match | `*.mp4` |
| `-m, --model` | Model: `lama` or `e2fgvi_hq` | `lama` |
| `--quiet` | Suppress progress output | False |

### Example: Clean Sora Videos
```bash
python cli.py \
  -i /Users/isaiahdupree/Documents/SoraVideos \
  -o /Users/isaiahdupree/Documents/SoraVideos/clean \
  --pattern "*_watermarked.mp4" \
  -m lama
```

## Python API

```python
from pathlib import Path
from sorawm.core import SoraWM
from sorawm.schemas import CleanerType

# Initialize with LAMA model
cleaner = SoraWM(cleaner_type=CleanerType.LAMA)

# Process single video
cleaner.run(
    input_video_path=Path("input.mp4"),
    output_video_path=Path("output.mp4")
)

# Process batch
cleaner.run_batch(
    input_video_dir_path=Path("./videos"),
    output_video_dir_path=Path("./cleaned")
)
```

## Technical Details

### Detection Pipeline
The YOLOv11s model was trained specifically on Sora watermarks. For frames where detection fails, the system:
1. Finds change points in watermark position
2. Calculates interval-average bounding boxes
3. Falls back to neighbor frames if needed

### LAMA Inpainting
- Processes each frame independently
- Uses large mask inpainting architecture
- Fast but may have slight flickering on moving watermarks

### E2FGVI_HQ Inpainting
- Processes frames in overlapping chunks
- Considers temporal consistency
- Blends chunk boundaries for smooth transitions
- Adapts chunk size based on available VRAM

## Performance

| Hardware | LAMA Speed | E2FGVI_HQ Speed |
|----------|------------|-----------------|
| Apple M1/M2/M3 | ~45s/video | CPU fallback (slow) |
| NVIDIA GPU | ~30s/video | ~3-5 min/video |
| CPU only | ~2 min/video | Not recommended |

## Troubleshooting

### "E2FGVI_HQ doesn't support MPS"
Expected on Apple Silicon. Use LAMA instead - it works well on MPS.

### Models not downloading
Check internet connection. Manual download URLs:
- YOLO: https://github.com/linkedlist771/SoraWatermarkCleaner/releases
- LAMA: https://github.com/Sanster/models/releases

### Out of memory
Reduce video resolution before processing, or use LAMA which has lower memory requirements.

## File Locations

```
Backend/SoraWatermarkCleaner/
├── cli.py                    # Command-line interface
├── sorawm/
│   ├── core.py               # Main SoraWM class
│   ├── watermark_detector.py # YOLOv11s detection
│   ├── watermark_cleaner.py  # Cleaner factory
│   └── cleaner/
│       ├── lama_cleaner.py   # LAMA implementation
│       └── e2fgvi_hq_cleaner.py # E2FGVI_HQ implementation
└── resources/
    └── best.pt               # YOLO weights (auto-downloaded)
```

## References

- [SoraWatermarkCleaner GitHub](https://github.com/linkedlist771/SoraWatermarkCleaner)
- [LAMA Inpainting Paper](https://arxiv.org/abs/2109.07161)
- [E2FGVI Video Inpainting](https://github.com/MCG-NKU/E2FGVI)
