# MediaPoster Test Suite

## Running Tests

### Run all tests
```bash
cd backend
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_video_validator.py -v
```

### Run with coverage
```bash
pytest tests/ -v --cov=modules --cov-report=html
```

### Run only fast tests (skip slow integration tests)
```bash
pytest tests/ -v -m "not slow"
```

## Test Structure

- `conftest.py` - Pytest fixtures and configuration
- `test_video_validator.py` - Tests for video validation and metadata extraction
- `test_file_watcher.py` - Tests for file system watching
- `test_ingestion_service.py` - Tests for main ingestion service

## Test Requirements

### System Requirements
- **FFmpeg**: Required for creating test videos
- **macOS**: Some tests require macOS-specific features (iCloud, Image Capture)

### Install Test Dependencies
```bash
pip install pytest pytest-asyncio pytest-cov watchdog
```

## Test Categories

### Unit Tests
Test individual components in isolation:
- Video validator
- File format detection
- Metadata extraction

### Integration Tests
Test components working together:
- File watcher detecting new videos
- Complete ingestion pipeline
- Multi-source video handling

### System Tests (Marked as `slow`)
Test full system functionality:
- iCloud Photos integration
- USB device detection
- AirDrop monitoring

## Creating Test Videos

The test suite uses FFmpeg to generate test videos. If FFmpeg is not available, some tests will be skipped automatically.

### Manual Test Video Creation
```bash
# Create 10-second test video
ffmpeg -f lavfi -i testsrc=duration=10:size=1920x1080:rate=30 \
       -f lavfi -i sine=frequency=1000:duration=10 \
       -c:v libx264 -c:a aac test_video.mp4

# Create short video (for validation tests)
ffmpeg -f lavfi -i testsrc=duration=2:size=1280x720:rate=30 \
       -f lavfi -i sine=frequency=1000:duration=2 \
       -c:v libx264 -c:a aac short_video.mp4
```

## Mocking macOS Features

Some tests mock macOS-specific features:
- **iCloud Photos Library**: Creates temporary directory structure
- **Image Capture**: Mocks USB device detection
- **AppleScript**: Simulates responses for system integration

## Running Tests on CI/CD

For CI/CD environments without macOS:
```bash
# Skip macOS-specific tests
pytest tests/ -v -m "not macos"
```

## Test Coverage Goals

- **Unit Tests**: >90% coverage
- **Integration Tests**: >75% coverage
- **End-to-End Tests**: All critical paths covered

## Troubleshooting

### FFmpeg Not Found
```bash
# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

### Tests Timeout
Increase timeouts in `pytest.ini` or mark tests as slow:
```python
@pytest.mark.slow
def test_long_running():
    pass
```

### File Permission Issues
Some tests require read/write permissions:
```bash
chmod -R 755 /path/to/test/directory
```

## Contributing Tests

When adding new features:
1. Write tests first (TDD)
2. Include unit tests for each function
3. Add integration tests for workflows
4. Update this README with new test categories
5. Ensure all tests pass before committing
