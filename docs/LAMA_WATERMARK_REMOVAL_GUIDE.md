# LAMA Watermark Removal - Replication Guide

## Overview

This guide documents exactly how to replicate the LAMA-based watermark removal process used on Sora videos.

**Test Results (Jan 10, 2026):**
- Processing time: 42 seconds
- Frames processed: 291
- Success rate: 100%

## Software Files Used

### Core Files

```
Backend/SoraWatermarkCleaner/
├── cli.py                          # Command-line entry point
├── sorawm/
│   ├── core.py                     # Main SoraWM orchestrator class
│   ├── configs.py                  # Configuration constants
│   ├── schemas.py                  # CleanerType enum (LAMA, E2FGVI_HQ)
│   ├── watermark_detector.py       # YOLOv11s detection logic
│   ├── watermark_cleaner.py        # Cleaner factory
│   ├── cleaner/
│   │   ├── lama_cleaner.py         # LAMA inpainting implementation
│   │   └── e2fgvi_hq_cleaner.py    # E2FGVI_HQ implementation
│   ├── utils/
│   │   ├── video_utils.py          # VideoLoader, frame merging
│   │   ├── devices_utils.py        # GPU/MPS/CPU detection
│   │   ├── download_utils.py       # Model weight downloads
│   │   └── imputation_utils.py     # Missed frame bbox interpolation
│   └── iopaint/                    # LAMA model from IOPaint project
│       ├── model_manager.py        # Model loading/inference
│       ├── download.py             # Model download logic
│       └── schema.py               # InpaintRequest dataclass
└── resources/
    └── best.pt                     # YOLOv11s detector weights (auto-downloaded)
```

### External Dependencies

| Dependency | Purpose |
|------------|---------|
| `ultralytics` | YOLO model inference |
| `torch` | Neural network backend |
| `ffmpeg-python` | Video encoding/decoding |
| `numpy` | Frame array manipulation |
| `opencv-python` | Image processing |
| `loguru` | Logging |
| `tqdm` | Progress bars |
| `rich` | CLI formatting |

## Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  cli.py                                                                     │
│  - Parses arguments (-i input, -o output, -m model, --pattern)              │
│  - Validates paths                                                          │
│  - Initializes SoraWM with CleanerType.LAMA                                 │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  sorawm/core.py :: SoraWM                                                   │
│  - __init__(): Creates SoraWaterMarkDetector + WaterMarkCleaner             │
│  - run_batch(): Iterates over matching videos                               │
│  - run(): Processes single video                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  sorawm/watermark_detector.py :: SoraWaterMarkDetector                      │
│  - Loads YOLOv11s model from resources/best.pt                              │
│  - detect(frame) → {"detected": bool, "bbox": (x1,y1,x2,y2), "confidence"}  │
│  - Runs on every frame to locate watermark                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  sorawm/utils/imputation_utils.py                                           │
│  - Handles frames where detection missed                                    │
│  - find_2d_data_bkps(): Find position change points                         │
│  - get_interval_average_bbox(): Average bbox per interval                   │
│  - Fills missed frames with interpolated bboxes                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  sorawm/cleaner/lama_cleaner.py :: LamaCleaner                              │
│  - Downloads LAMA model if not cached (~/.cache/torch/hub/)                 │
│  - clean(frame, mask) → inpainted_frame                                     │
│  - Uses IOPaint's ModelManager for inference                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────────────┐
│  sorawm/core.py :: merge_audio_track()                                      │
│  - FFmpeg combines cleaned video with original audio                        │
│  - Output: cleaned_<original_filename>.mp4                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Replication Steps

### 1. Setup Environment

```bash
cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend/SoraWatermarkCleaner

# Install uv if needed
brew install uv

# Sync dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### 2. Prepare Input

Place watermarked videos in a folder:
```bash
mkdir -p /path/to/input
cp your_watermarked_video.mp4 /path/to/input/
```

### 3. Run LAMA Removal

```bash
python cli.py \
  -i /path/to/input \
  -o /path/to/output \
  --pattern "*.mp4" \
  -m lama
```

### 4. Verify Output

```bash
# Check output files
ls -la /path/to/output/

# Open cleaned video
open /path/to/output/cleaned_*.mp4
```

## Python API Usage

```python
from pathlib import Path
from sorawm.core import SoraWM
from sorawm.schemas import CleanerType

# Initialize
cleaner = SoraWM(cleaner_type=CleanerType.LAMA)

# Process single video
cleaner.run(
    input_video_path=Path("/path/to/watermarked.mp4"),
    output_video_path=Path("/path/to/cleaned.mp4"),
    progress_callback=lambda p: print(f"Progress: {p}%"),
    quiet=False
)

# Process batch
cleaner.run_batch(
    input_video_dir_path=Path("/path/to/input"),
    output_video_dir_path=Path("/path/to/output"),
    quiet=False
)
```

## Model Weights

### YOLOv11s Detector
- **File:** `resources/best.pt`
- **Source:** https://github.com/linkedlist771/SoraWatermarkCleaner/releases
- **Auto-download:** Yes (on first run)

### LAMA Inpainting
- **Location:** `~/.cache/torch/hub/`
- **Source:** https://github.com/Sanster/models/releases
- **Auto-download:** Yes (on first run via IOPaint)

## Configuration

Key settings in `sorawm/configs.py`:

```python
DEFAULT_WATERMARK_REMOVE_MODEL = "lama"
WATER_MARK_DETECT_YOLO_WEIGHTS = "resources/best.pt"
ENABLE_E2FGVI_HQ_TORCH_COMPILE = False
```

## Performance Benchmarks

| Hardware | Speed | Notes |
|----------|-------|-------|
| Apple M1/M2/M3 (MPS) | ~45s/video | Recommended |
| NVIDIA GPU (CUDA) | ~30s/video | Fastest |
| CPU only | ~2-3 min/video | Slow but works |

## Troubleshooting

### Models not downloading
```bash
# Manual YOLO weights download
curl -L -o resources/best.pt \
  https://github.com/linkedlist771/SoraWatermarkCleaner/releases/download/v0.0.1/best.pt
```

### FFmpeg errors
```bash
# Ensure ffmpeg is installed
brew install ffmpeg
```

### Memory issues
- LAMA uses ~2-4GB RAM
- Close other applications if needed
- Process videos one at a time

## Test Results Archive

**Test: Jan 10, 2026**
```
Input:  s_691962781e148191afa5c59ad5bb3cc5_watermarked.mp4 (3.7 MB)
Output: cleaned_s_691962781e148191afa5c59ad5bb3cc5_watermarked.mp4 (4.1 MB)
Time:   42 seconds
Frames: 291
Result: Watermark fully removed, seamless inpainting
```

## References

- [SoraWatermarkCleaner GitHub](https://github.com/linkedlist771/SoraWatermarkCleaner)
- [LAMA: Resolution-robust Large Mask Inpainting](https://arxiv.org/abs/2109.07161)
- [IOPaint (LAMA implementation)](https://github.com/Sanster/IOPaint)
- [Ultralytics YOLO](https://github.com/ultralytics/ultralytics)
