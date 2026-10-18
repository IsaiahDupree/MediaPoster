# Full-Scale Media Pipeline End-to-End Test

## Overview

This test validates the complete media pipeline workflow from video ingestion through AI analysis, multi-platform publishing, URL retrieval, and checkback scheduling.

## Test Workflow

### Step 1: Get Video from Resources
- Retrieves a real video from the database
- Verifies video file exists and is accessible
- Validates video metadata (duration, file path, etc.)

### Step 2: Full AI Analysis Pipeline
Runs complete AI analysis including:
- **Transcription**: Speech-to-text with word-level timestamps
- **Context Generation**: AI-generated context/description
- **Titles Generation**: Multiple title variations
- **Words Analysis**: Word-level analysis (emphasis, sentiment, functions)
- **Frame Analysis**: Visual content analysis (if enabled)
- **Audio Analysis**: Audio characteristics (if enabled)
- **Viral Analysis**: FATE model scoring (if enabled)

### Step 3: Post to All Linked Platforms
- Posts video to all connected/linked platforms
- Uses AI-generated titles and descriptions
- Includes hashtags and metadata
- Tracks post creation status

### Step 4: Obtain Platform URLs
- Retrieves published URLs from each platform
- Verifies URLs are accessible
- Stores URLs in database

### Step 5: Schedule Checkback Periods
- Schedules checkback metrics collection after 5 minutes
- Creates checkback jobs for each platform post
- Verifies checkback scheduling

### Step 6: Verify Complete Workflow
- Validates all steps completed successfully
- Checks database records
- Verifies data integrity

## Running the Test

### Prerequisites

1. **Database**: Must have videos in the database with valid file paths
2. **Linked Accounts**: Must have connected accounts for platforms you want to test
3. **API Keys**: OpenAI API key for AI analysis (if not mocked)
4. **Blotato API**: Blotato API key for publishing (if not mocked)

### Quick Run

```bash
cd Backend
python run_full_pipeline_test.py
```

### Manual Run with Pytest

```bash
cd Backend
pytest tests/test_full_media_pipeline_e2e.py::TestFullMediaPipelineE2E::test_full_pipeline_with_real_data -v -s
```

### Run with Specific Options

```bash
# Run with verbose output
pytest tests/test_full_media_pipeline_e2e.py -v -s

# Run with specific video
pytest tests/test_full_media_pipeline_e2e.py -v -s --video-id=<video_id>

# Run with specific platforms
pytest tests/test_full_media_pipeline_e2e.py -v -s --platforms=tiktok,instagram
```

## Test Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@host:port/test_db

# API Keys
OPENAI_API_KEY=sk-...
BLOTATO_API_KEY=...

# Test Settings
TEST_CHECKBACK_MINUTES=5  # Default: 5 minutes
TEST_PLATFORMS=tiktok,instagram,youtube,threads
```

### Test Data Requirements

1. **Video in Database**:
   - Must have `source_type = 'local'`
   - Must have valid `source_uri` (file path)
   - Must have `duration_sec > 0`
   - File must exist at the specified path

2. **Linked Accounts**:
   - Accounts must be connected in the `accounts` table
   - Accounts must be active/enabled
   - Platform must be supported

## Expected Output

```
================================================================================
FULL-SCALE MEDIA PIPELINE TEST
================================================================================
Video ID: 123e4567-e89b-12d3-a456-426614174000
Video Path: /path/to/video.mp4
Duration: 120.5s
Platforms: tiktok, instagram, youtube, threads
================================================================================

STEP 1: Getting video from resources...
✅ Video retrieved: my_video.mp4

STEP 2: Running full AI analysis pipeline...
   Analysis job started: job_123
✅ AI Analysis complete:
   - Words analyzed: 450
   - Context: This video discusses...
   - Titles: 5 generated

STEP 3: Posting to 4 linked platforms...
   Posting to tiktok...
   ✅ tiktok: Posted
   Posting to instagram...
   ✅ instagram: Posted
   Posting to youtube...
   ✅ youtube: Posted
   Posting to threads...
   ✅ threads: Posted
✅ Posted to 4/4 platforms

STEP 4: Obtaining URLs from platforms...
✅ Obtained 4 platform URLs:
   - tiktok: https://tiktok.com/@user/video/123
   - instagram: https://instagram.com/p/ABC123
   - youtube: https://youtube.com/watch?v=xyz789
   - threads: https://threads.net/@user/post/456

STEP 5: Scheduling checkback period (5 minutes)...
✅ Scheduled 4 checkback periods
   - tiktok: Checkback at 2025-01-22T10:05:00
   - instagram: Checkback at 2025-01-22T10:05:00
   - youtube: Checkback at 2025-01-22T10:05:00
   - threads: Checkback at 2025-01-22T10:05:00

STEP 6: Verifying complete workflow...
✅ Video analyzed
✅ Posts created: 4
✅ URLs obtained: 4
✅ Checkbacks scheduled: 4

================================================================================
✅ FULL PIPELINE TEST COMPLETE
================================================================================
Video: my_video.mp4
Analysis: ✅ Complete
Posts: ✅ 4 created
URLs: ✅ 4 obtained
Checkbacks: ✅ 4 scheduled
================================================================================
```

## Troubleshooting

### No Video Found
```
pytest.skip("No real video found in database")
```
**Solution**: Add a video to the database with a valid file path

### Analysis Job Failed
```
Analysis job failed: <error>
```
**Solution**: 
- Check OpenAI API key
- Verify video file is accessible
- Check API rate limits

### Posting Failed
```
❌ platform: Failed (status_code)
```
**Solution**:
- Verify platform accounts are connected
- Check Blotato API key
- Verify account permissions

### URLs Not Obtained
```
⚠️  Could not get URL for platform: <error>
```
**Solution**:
- Check post status (may still be processing)
- Verify platform URL format
- Check database records

## Test Coverage

This test covers:
- ✅ Video retrieval from database
- ✅ Full AI analysis pipeline
- ✅ Multi-platform publishing
- ✅ URL retrieval
- ✅ Checkback scheduling
- ✅ Data persistence
- ✅ Error handling

## Integration with CI/CD

Add to your CI/CD pipeline:

```yaml
# .github/workflows/test.yml
- name: Run Full Pipeline Test
  run: |
    cd Backend
    pytest tests/test_full_media_pipeline_e2e.py -v
  env:
    DATABASE_URL: ${{ secrets.TEST_DATABASE_URL }}
    OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
    BLOTATO_API_KEY: ${{ secrets.BLOTATO_API_KEY }}
```

## Notes

- This test uses **real data** from your database
- It makes **real API calls** (unless mocked)
- It may take **5-10 minutes** to complete
- It requires **active internet connection**
- It may incur **API costs** (OpenAI, Blotato)

For faster testing without real API calls, use the mocked version:
```bash
pytest tests/test_full_media_pipeline_e2e.py::test_full_pipeline_with_mock_data -v
```

