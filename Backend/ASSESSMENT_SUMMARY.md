# Voice Cloning Quality Assessment - Summary Report

**Generated:** $(date)
**Assessment Tool:** Voice Cloning Quality Assessor
**Location:** Backend/scripts/run_voice_quality_assessment.py

## Assessment Results

### Files Assessed

1. **IMG_2872.MOV** - 24.7 seconds
   - Score: 0.36/1.00 (POOR)
   - Status: Insufficient duration

2. **IMG_3588.MOV** - 22.5 seconds  
   - Score: 0.36/1.00 (POOR)
   - Status: Insufficient duration

3. **IMG_3577.MOV** - 243.3 seconds (4.1 minutes)
   - Score: 0.31/1.00 (POOR)
   - Status: Fair duration, but quality issues

### Overall Statistics

- **Average Score:** 0.34/1.00
- **Total Duration Assessed:** 290.5 seconds (4.8 minutes)
- **Average Duration:** 96.8 seconds per video

### Key Findings

#### ✅ Positive Aspects
- **Sample Rate:** All videos have excellent 44.1 kHz sample rate
- **Channels:** All videos are mono (preferred for voice cloning)
- **No Distortion:** No clipping or distortion detected
- **Silence Levels:** Good silence percentages (0-11%)

#### ⚠️ Issues Identified
- **Duration:** Most videos are too short (< 30 seconds minimum)
- **Signal Quality:** SNR and background noise metrics not available (may indicate no clear speech detected)
- **Volume Consistency:** Low consistency scores
- **Frequency Response:** Limited voice range coverage

### Recommendations

1. **Duration Requirements:**
   - Minimum: 30 seconds (most videos meet this)
   - Recommended: 5+ minutes per video
   - Ideal: 30+ minutes total training data

2. **Quality Improvements:**
   - Record in quieter environments
   - Use better microphones
   - Ensure clear speech is present
   - Normalize audio levels

3. **For Voice Cloning:**
   - Need videos with clear, consistent speech
   - Combine multiple short videos to reach 5+ minutes total
   - Focus on videos with actual spoken content

## Generated Reports

- `voice_quality_assessment_report.txt` - Single file detailed report
- `voice_quality_batch_report.txt` - Batch summary
- `voice_quality_detailed_report.txt` - Detailed report for longer video

## Next Steps

1. Identify videos with clear speech content
2. Combine multiple videos to reach recommended duration
3. Re-run assessment with transcript extraction (requires OPENAI_API_KEY)
4. Focus on videos with actual voice recordings rather than music/ambient sound

