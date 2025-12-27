# Video Matting Solutions Comparison

**Date:** December 26, 2024  
**Purpose:** Evaluate matting solutions for Media Factory pipeline

---

## Solution Comparison Matrix

| Solution | Quality | Speed | API Available | Local Required | Best For |
|----------|---------|-------|---------------|----------------|----------|
| **RVM** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ | ✅ GPU | Production quality, real-time |
| **BackgroundMattingV2** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | ✅ GPU | Clean background plate available |
| **MediaPipe** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ | ✅ CPU/GPU | Fast, lightweight, UGC content |
| **rembg** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ | ✅ CPU/GPU | Simple, batch processing |
| **SAM 2** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ❓ | ✅ GPU | Advanced segmentation, specific objects |

---

## Detailed Analysis

### 1. Robust Video Matting (RVM) ⭐ RECOMMENDED FOR PRODUCTION

**GitHub**: https://github.com/PeterL1n/RobustVideoMatting

**Pros:**
- ✅ Highest quality matting (alpha matte with clean edges)
- ✅ Temporal memory (no flickering frame-to-frame)
- ✅ Real-time performance (4K @ 76 FPS, HD @ 104 FPS on GTX 1080 Ti)
- ✅ No additional inputs required (no green screen, no background plate)
- ✅ Well-maintained, active project
- ✅ Python API available

**Cons:**
- ❌ Requires GPU (CUDA)
- ❌ Local installation required (no API)
- ❌ Model download required (~200MB)

**Installation:**
```bash
pip install torch torchvision
pip install git+https://github.com/PeterL1n/RobustVideoMatting.git
```

**Use Case**: Production-quality matting for "cut me out and put me somewhere else" workflow

**Code Example:**
```python
from inference import convert_video

convert_video(
    source='input.mp4',
    output='output.mp4',
    model='rvm_mobilenetv3.pth',  # or rvm_resnet50.pth
    downsample_ratio=0.25,
    device='cuda'
)
```

---

### 2. BackgroundMattingV2 ⭐ BEST WITH CLEAN PLATE

**GitHub**: https://github.com/PeterL1n/BackgroundMattingV2

**Pros:**
- ✅ Highest quality when clean background plate available
- ✅ Very stable mattes
- ✅ Handles complex scenes well
- ✅ Python API available

**Cons:**
- ❌ Requires clean background plate (same scene without person)
- ❌ Requires GPU
- ❌ Local installation required

**Use Case**: When you can record a clean background plate (same scene, no person)

**Code Example:**
```python
from inference import convert_video

convert_video(
    source='input.mp4',
    background='background.mp4',  # Clean plate
    output='output.mp4',
    model='pytorch_resnet50.pth',
    device='cuda'
)
```

---

### 3. MediaPipe Selfie Segmentation ⭐ FASTEST, LIGHTWEIGHT

**GitHub**: https://github.com/google/mediapipe

**Pros:**
- ✅ Very fast (real-time on CPU)
- ✅ Lightweight
- ✅ Works on web/mobile
- ✅ Python API available
- ✅ No GPU required (but faster with GPU)

**Cons:**
- ⚠️ Quality is "good enough" but not perfect (softer edges)
- ⚠️ Best for selfie/talking head content
- ⚠️ May struggle with complex backgrounds

**Installation:**
```bash
pip install mediapipe
```

**Use Case**: Quick UGC content, real-time processing, lightweight requirements

**Code Example:**
```python
import cv2
import mediapipe as mp

mp_selfie_segmentation = mp.solutions.selfie_segmentation
selfie_segmentation = mp_selfie_segmentation.SelfieSegmentation(model_selection=1)

# Process video frame by frame
cap = cv2.VideoCapture('input.mp4')
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    results = selfie_segmentation.process(frame)
    mask = results.segmentation_mask
    
    # Apply mask to extract person
    # ... composite with background
```

---

### 4. rembg (RMBG-1.4) ⭐ SIMPLE, BATCH PROCESSING

**GitHub**: https://github.com/danielgatis/rembg

**Pros:**
- ✅ Simple to use
- ✅ Works on images and video (via frame extraction)
- ✅ CPU and GPU support
- ✅ Python API available
- ✅ Good quality for general use

**Cons:**
- ⚠️ Primarily designed for images (video requires frame-by-frame)
- ⚠️ May have temporal inconsistencies
- ⚠️ Requires frame extraction → process → re-encode

**Installation:**
```bash
pip install rembg[new]
```

**Use Case**: Simple batch processing, image matting, quick prototypes

**Code Example:**
```python
from rembg import remove
from PIL import Image

# For images
input_image = Image.open('input.jpg')
output_image = remove(input_image)
output_image.save('output.png')

# For video: extract frames → process → re-encode
```

---

### 5. SAM 2 (Segment Anything Model 2) ⭐ ADVANCED SEGMENTATION

**GitHub**: https://github.com/facebookresearch/sam2

**Pros:**
- ✅ Most advanced segmentation
- ✅ Can segment specific objects (not just people)
- ✅ Point/box prompting
- ✅ Consistent tracking across frames

**Cons:**
- ❌ Requires GPU
- ❌ Local installation required (no API confirmed)
- ❌ More complex setup
- ❌ Slower than RVM/MediaPipe

**Use Case**: Advanced segmentation, specific object extraction, research

**Status**: API availability unclear - may need local installation

---

## Recommendation for Media Factory

### Primary: RVM (Robust Video Matting)

**Why:**
- Best quality-to-speed ratio
- No additional inputs required
- Temporal memory prevents flickering
- Real-time capable
- Well-maintained project

**Implementation:**
- Use as default matting solution
- Requires GPU (CUDA) - can fallback to CPU (slower)
- Local installation (but can be containerized)

### Fallback: MediaPipe

**Why:**
- Fast and lightweight
- Works on CPU
- Good enough for UGC content
- Easy to integrate

**Implementation:**
- Use when GPU not available
- Use for quick previews
- Use for lightweight requirements

### Future: BackgroundMattingV2

**Why:**
- Best quality when clean plate available
- Useful for specific use cases

**Implementation:**
- Add as optional adapter
- Use when clean background plate is provided

---

## Adapter Pattern Implementation

All matting solutions will implement a common interface:

```python
class MattingAdapter(ABC):
    @abstractmethod
    async def extract_foreground(
        self,
        source_video: str,
        output_path: str,
        config: MattingConfig
    ) -> MattingResult:
        pass
    
    @abstractmethod
    def get_model_info(self) -> dict:
        pass
```

**Adapters:**
- `RVMAdapter` - Primary (production quality)
- `MediaPipeAdapter` - Fallback (fast, lightweight)
- `BackgroundMattingV2Adapter` - Optional (clean plate)
- `RembgAdapter` - Optional (simple batch)
- `SAM2Adapter` - Future (advanced segmentation)

---

## Testing Strategy

1. **Quality Test**: Compare matting quality across solutions
2. **Speed Test**: Benchmark processing speed
3. **Compatibility Test**: Test on Mac/Windows/Linux
4. **Integration Test**: Test with Remotion pipeline

---

## Next Steps

1. ✅ Research complete
2. 🚧 Implement adapter pattern
3. 🚧 Implement RVM adapter (primary)
4. 🚧 Implement MediaPipe adapter (fallback)
5. 🚧 Create matting service
6. 🚧 Integration tests

