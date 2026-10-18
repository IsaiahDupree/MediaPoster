# Voice Quality Assessment - Quick Start

## Running the Assessment

### Single Video File

```bash
cd Backend
source venv/bin/activate  # or venv311/bin/activate

# Basic assessment
python scripts/run_voice_quality_assessment.py /path/to/video.mp4

# With automatic transcript extraction (requires OPENAI_API_KEY)
python scripts/run_voice_quality_assessment.py /path/to/video.mp4 --transcript

# Save report to file
python scripts/run_voice_quality_assessment.py /path/to/video.mp4 --output report.txt

# With custom transcript file
python scripts/run_voice_quality_assessment.py /path/to/video.mp4 --transcript-file transcript.txt
```

### Multiple Video Files

```bash
# Assess multiple files
python scripts/run_voice_quality_assessment.py video1.mp4 video2.mp4 video3.mp4

# Assess all videos in a directory
python scripts/run_voice_quality_assessment.py --directory /Users/isaiahdupree/Documents/IphoneImport

# Summary only (faster)
python scripts/run_voice_quality_assessment.py --directory /path/to/videos --summary
```

### JSON Output

```bash
# Get JSON results for programmatic use
python scripts/run_voice_quality_assessment.py video.mp4 --json > results.json
```

## Example: Assess iPhone Import Videos

```bash
cd Backend
source venv/bin/activate

# Assess first 5 MOV files from iPhone import
python scripts/run_voice_quality_assessment.py \
  --directory /Users/isaiahdupree/Documents/IphoneImport \
  --summary \
  --output iphone_videos_assessment.txt
```

## Report Format

The report includes:

- **Overall Score** (0.0 to 1.0) and suitability rating
- **Signal Quality**: SNR, background noise, clarity
- **Audio Characteristics**: Duration, volume, consistency
- **Technical Specs**: Sample rate, bitrate, channels
- **Frequency Analysis**: Voice range coverage
- **Speech Analysis**: Speech/silence percentages
- **Distortion Detection**: Clipping and artifacts
- **Issues**: Critical problems identified
- **Recommendations**: Actionable improvements

## Quality Thresholds

- **Excellent** (≥0.8): Ready for professional voice cloning
- **Good** (≥0.65): Suitable with minor improvements
- **Fair** (≥0.5): Needs significant improvements
- **Poor** (<0.5): Not recommended without major fixes

## Minimum Requirements

- Duration: 30 seconds minimum (5 minutes recommended)
- SNR: 20 dB minimum (35+ dB excellent)
- Silence: <20% of total duration
- Sample Rate: 16 kHz minimum (22.05 kHz recommended)
- Channels: Mono preferred

## API Usage

You can also use the API endpoint:

```bash
curl -X POST "http://localhost:5555/api/voice-cloning-quality/assess" \
  -F "file=@video.mp4" \
  -F "transcript=Your transcript text here"
```

## Troubleshooting

### FFmpeg Not Found
```bash
# Install FFmpeg
brew install ffmpeg  # macOS
# or
apt-get install ffmpeg  # Linux
```

### Missing Dependencies
```bash
pip install loguru numpy
```

### No Audio in Video
The assessment will still run but will show low scores for signal quality metrics.

