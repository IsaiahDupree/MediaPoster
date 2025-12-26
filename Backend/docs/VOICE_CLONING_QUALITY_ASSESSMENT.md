# Voice Cloning Quality Assessment

## Overview

The Voice Cloning Quality Assessment service evaluates audio recordings to determine their suitability for use as training data for voice cloning models. It provides comprehensive metrics and recommendations to help ensure high-quality voice training datasets.

## Features

### Quality Metrics Assessed

1. **Signal Quality**
   - Signal-to-Noise Ratio (SNR) in dB
   - Background noise levels
   - Speech clarity score

2. **Audio Characteristics**
   - Mean volume levels
   - Volume consistency across recording
   - Dynamic range

3. **Frequency Analysis**
   - Fundamental frequency detection
   - Voice range coverage (85-255 Hz fundamental, harmonics up to 8kHz)
   - Frequency response score

4. **Speech Quality**
   - Silence percentage
   - Speech percentage
   - Pause count and average duration

5. **Distortion Detection**
   - Clipping detection
   - Distortion artifacts
   - Overall distortion score

6. **Transcript Alignment** (if transcript provided)
   - Word count and words per minute
   - Alignment score (how well transcript matches audio duration)

## API Endpoints

### POST `/api/voice-cloning-quality/assess`

Assess a single audio or video file for voice cloning quality.

**Request:**
- `file`: Audio or video file (multipart/form-data)
- `transcript`: Optional transcript text (form field)

**Response:**
```json
{
  "overall_score": 0.85,
  "suitability_for_cloning": "good",
  "snr_db": 28.5,
  "background_noise_level_db": -35.2,
  "speech_clarity_score": 0.82,
  "mean_volume_db": -12.3,
  "volume_consistency": 0.78,
  "silence_percentage": 15.2,
  "speech_percentage": 84.8,
  "duration_seconds": 245.5,
  "transcript_length_words": 612,
  "words_per_minute": 149.5,
  "has_distortion": false,
  "has_clipping": false,
  "recommendations": [
    "Audio quality is suitable for voice cloning training"
  ],
  "issues": [],
  "sample_rate_hz": 44100,
  "bitrate_kbps": 128,
  "channels": 1
}
```

### POST `/api/voice-cloning-quality/assess-batch`

Assess multiple audio files at once.

**Request:**
- `files`: Array of audio/video files
- `transcript`: Optional shared transcript

**Response:**
```json
{
  "summary": {
    "total_files": 5,
    "valid_files": 5,
    "average_score": 0.78,
    "total_duration_seconds": 1250.3,
    "total_duration_minutes": 20.8
  },
  "assessments": [
    {
      "filename": "recording1.wav",
      "overall_score": 0.82,
      "suitability": "good",
      "duration_seconds": 245.5,
      "snr_db": 28.5,
      "issues": [],
      "recommendations": []
    }
  ]
}
```

### GET `/api/voice-cloning-quality/requirements`

Get quality requirements and thresholds.

**Response:**
```json
{
  "minimum_requirements": {
    "duration_seconds": 30.0,
    "recommended_duration_seconds": 300.0,
    "ideal_duration_seconds": 1800.0,
    "min_snr_db": 20.0,
    "excellent_snr_db": 35.0,
    "max_silence_percentage": 20.0,
    "max_background_noise_db": -30.0,
    "min_words_per_minute": 100,
    "max_words_per_minute": 200
  },
  "audio_specs": {
    "recommended_sample_rate_hz": 22050,
    "minimum_sample_rate_hz": 16000,
    "preferred_channels": 1,
    "voice_fundamental_range_hz": {
      "min": 85,
      "max": 255
    },
    "voice_harmonics_max_hz": 8000
  },
  "quality_thresholds": {
    "excellent": 0.8,
    "good": 0.65,
    "fair": 0.5,
    "poor": 0.0
  }
}
```

## Quality Thresholds

### Suitability Ratings

- **Excellent** (≥0.8): High-quality audio suitable for professional voice cloning
- **Good** (≥0.65): Good quality, suitable for voice cloning with minor issues
- **Fair** (≥0.5): Acceptable quality but may need improvement
- **Poor** (<0.5): Not recommended for voice cloning without significant improvement

### Minimum Requirements

- **Duration**: At least 30 seconds (5 minutes recommended, 30 minutes ideal)
- **SNR**: Minimum 20 dB (35+ dB for excellent)
- **Silence**: Maximum 20% silence
- **Background Noise**: Maximum -30 dB
- **Sample Rate**: Minimum 16 kHz (22.05 kHz recommended)
- **Channels**: Mono preferred

## Usage Examples

### Python (httpx)

```python
import httpx

async def assess_audio_quality(audio_file_path: str, transcript: str = None):
    async with httpx.AsyncClient(timeout=300.0) as client:
        with open(audio_file_path, 'rb') as f:
            files = {'file': f}
            data = {}
            if transcript:
                data['transcript'] = transcript
            
            response = await client.post(
                'http://localhost:5555/api/voice-cloning-quality/assess',
                files=files,
                data=data
            )
            
            return response.json()

# Usage
result = await assess_audio_quality('recording.wav', 'Full transcript text here')
print(f"Score: {result['overall_score']}")
print(f"Suitability: {result['suitability_for_cloning']}")
```

### cURL

```bash
curl -X POST "http://localhost:5555/api/voice-cloning-quality/assess" \
  -F "file=@recording.wav" \
  -F "transcript=Full transcript text here"
```

### JavaScript (fetch)

```javascript
async function assessAudioQuality(audioFile, transcript = null) {
  const formData = new FormData();
  formData.append('file', audioFile);
  if (transcript) {
    formData.append('transcript', transcript);
  }
  
  const response = await fetch(
    'http://localhost:5555/api/voice-cloning-quality/assess',
    {
      method: 'POST',
      body: formData
    }
  );
  
  return await response.json();
}
```

## Command Line Usage

The service can also be used directly from the command line:

```bash
cd Backend
python services/voice_cloning_quality_assessor.py audio_file.wav transcript.txt
```

## Integration with Long Transcripts

The service is designed to work with long transcripts. When a transcript is provided:

1. **Word Count Analysis**: Calculates total words and words per minute
2. **Alignment Score**: Compares transcript length to audio duration
3. **Speech Rate Validation**: Ensures speech rate is within acceptable range (100-200 WPM)

### Best Practices for Long Transcripts

1. **Segment Alignment**: For very long transcripts, consider providing segment timestamps:
   ```python
   transcript_segments = [
       {"start": 0.0, "end": 30.5, "text": "First segment..."},
       {"start": 30.5, "end": 60.2, "text": "Second segment..."}
   ]
   ```

2. **Quality Consistency**: Long recordings should maintain consistent quality throughout
3. **Pause Management**: Long transcripts may have natural pauses - ensure they're not excessive

## Recommendations

The service provides actionable recommendations based on assessment results:

- **Signal Quality**: Suggestions for improving SNR
- **Recording Environment**: Tips for reducing background noise
- **Audio Processing**: Recommendations for normalization, filtering, etc.
- **Duration**: Guidance on minimum/recommended recording lengths
- **Technical Specs**: Sample rate, bitrate, channel configuration

## Common Issues and Solutions

### Low SNR (< 20 dB)
- **Issue**: Too much background noise
- **Solution**: Record in quieter environment, use noise reduction, improve microphone positioning

### High Silence Percentage (> 20%)
- **Issue**: Too many pauses or gaps
- **Solution**: Edit out long pauses, ensure continuous speech

### Clipping Detected
- **Issue**: Audio levels too high, causing distortion
- **Solution**: Reduce input gain, use limiter, normalize audio

### Insufficient Duration (< 30 seconds)
- **Issue**: Not enough training data
- **Solution**: Record longer sessions (minimum 5 minutes recommended)

### Poor Volume Consistency
- **Issue**: Volume varies significantly throughout recording
- **Solution**: Use audio normalization, maintain consistent microphone distance

## Technical Details

### Audio Processing

The service uses FFmpeg for audio analysis:
- Audio extraction from video files
- Signal analysis (RMS, peak levels)
- Frequency analysis (bandpass filtering)
- Silence detection
- Distortion detection

### Metrics Calculation

**Overall Score** (weighted):
- Signal Quality (SNR): 30%
- Speech Clarity: 20%
- Volume Consistency: 10%
- Frequency Response: 15%
- Distortion: 15%
- Silence Percentage: 10%
- Duration Bonus: 5%

## Dependencies

- FFmpeg (for audio processing)
- NumPy (for numerical analysis)
- FastAPI (for API endpoints)

## Future Enhancements

- Real-time quality monitoring during recording
- Speaker diarization (detect multiple speakers)
- Emotion and tone analysis
- Automatic audio enhancement suggestions
- Integration with voice cloning training pipelines

