#!/usr/bin/env python3
"""
Demo script for Video Ingestion System
Shows how to use all Mac/iOS video ingestion features
"""
import sys
import time
from pathlib import Path
from loguru import logger

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from modules.video_ingestion import VideoIngestionService, VideoValidator


def on_new_video(video_path: Path, metadata: dict):
    """
    Callback function called when a new video is detected
    
    Args:
        video_path: Path to the detected video
        metadata: Video metadata including duration, resolution, source, etc.
    """
    logger.info("=" * 60)
    logger.success(f"🎥 NEW VIDEO DETECTED!")
    logger.info(f"📁 Path: {video_path}")
    logger.info(f"📊 Source: {metadata['source']}")
    logger.info(f"⏱️  Duration: {metadata['duration']:.1f}s")
    logger.info(f"📐 Resolution: {metadata['width']}x{metadata['height']}")
    logger.info(f"💾 Size: {metadata['file_size_bytes'] / (1024*1024):.2f}MB")
    logger.info(f"🎬 Codec: {metadata['video_codec']}")
    logger.info(f"🔊 Audio: {'Yes' if metadata['has_audio'] else 'No'}")
    logger.info("=" * 60)
    
    # Here you would trigger the next stage in your pipeline
    # For example:
    # - Upload to database
    # - Start AI analysis
    # - Queue for processing
    print("\n✓ Video ready for processing pipeline\n")


def demo_validator_only():
    """Demo: Test video validation on a single file"""
    logger.info("Demo 1: Video Validator")
    logger.info("-" * 60)
    
    validator = VideoValidator(min_duration=5, max_duration=3600)
    
    # Prompt for video file
    video_path = input("Enter path to video file to validate: ").strip()
    video_file = Path(video_path).expanduser()
    
    if not video_file.exists():
        logger.error(f"File not found: {video_file}")
        return
    
    logger.info(f"Validating: {video_file.name}")
    
    is_valid, error, metadata = validator.validate(video_file)
    
    if is_valid:
        logger.success("✓ Video is valid!")
        logger.info(f"Duration: {metadata['duration']:.1f}s")
        logger.info(f"Resolution: {metadata['width']}x{metadata['height']}")
        logger.info(f"FPS: {metadata['fps']:.2f}")
        
        # Extract thumbnail
        thumbnail_path = video_file.parent / f"{video_file.stem}_thumbnail.jpg"
        if validator.get_video_thumbnail(video_file, thumbnail_path):
            logger.success(f"✓ Thumbnail saved: {thumbnail_path}")
    else:
        logger.error(f"✗ Invalid video: {error}")


def demo_file_watcher():
    """Demo: Watch a directory for new videos"""
    logger.info("Demo 2: File Watcher")
    logger.info("-" * 60)
    
    watch_dir = input("Enter directory to watch (or press Enter for Downloads): ").strip()
    if not watch_dir:
        watch_dir = str(Path.home() / "Downloads")
    
    logger.info(f"Watching: {watch_dir}")
    logger.info("Drop video files into this directory to detect them")
    logger.info("Press Ctrl+C to stop...\n")
    
    service = VideoIngestionService(
        enable_icloud=False,
        enable_usb=False,
        enable_airdrop=False,
        enable_file_watcher=True,
        watch_directories=[watch_dir],
        callback=on_new_video
    )
    
    try:
        service.start_all()
        
        # Keep running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nStopping file watcher...")
        service.stop_all()
        logger.success("✓ File watcher stopped")


def demo_airdrop_monitor():
    """Demo: Monitor AirDrop for videos"""
    logger.info("Demo 3: AirDrop Monitor")
    logger.info("-" * 60)
    logger.info("Monitoring Downloads folder for AirDrop videos")
    logger.info("Send a video via AirDrop to test")
    logger.info("Press Ctrl+C to stop...\n")
    
    service = VideoIngestionService(
        enable_icloud=False,
        enable_usb=False,
        enable_airdrop=True,
        enable_file_watcher=False,
        callback=on_new_video
    )
    
    try:
        service.start_all()
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nStopping AirDrop monitor...")
        service.stop_all()
        logger.success("✓ AirDrop monitor stopped")


def demo_icloud_photos():
    """Demo: Monitor iCloud Photos for new videos"""
    logger.info("Demo 4: iCloud Photos Monitor")
    logger.info("-" * 60)
    logger.info("Monitoring iCloud Photos library for new videos")
    logger.info("Take a video on your iPhone to test")
    logger.info("Press Ctrl+C to stop...\n")
    
    service = VideoIngestionService(
        enable_icloud=True,
        enable_usb=False,
        enable_airdrop=False,
        enable_file_watcher=False,
        callback=on_new_video
    )
    
    # Check if Photos library is accessible
    status = service.get_status()
    if not status['icloud']['available']:
        logger.error("✗ iCloud Photos library not accessible")
        logger.info("Make sure Photos.app is configured and accessible")
        return
    
    logger.success("✓ iCloud Photos library found")
    
    try:
        service.start_all()
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nStopping iCloud monitor...")
        service.stop_all()
        logger.success("✓ iCloud monitor stopped")


def demo_all_sources():
    """Demo: Monitor all sources simultaneously"""
    logger.info("Demo 5: All Sources (Comprehensive)")
    logger.info("-" * 60)
    logger.info("Monitoring ALL video sources:")
    logger.info("  - iCloud Photos")
    logger.info("  - USB iPhone connections")
    logger.info("  - AirDrop")
    logger.info("  - File system (Desktop, Downloads, Movies)")
    logger.info("\nPress Ctrl+C to stop...\n")
    
    watch_dirs = [
        str(Path.home() / "Desktop"),
        str(Path.home() / "Downloads"),
        str(Path.home() / "Movies"),
    ]
    
    service = VideoIngestionService(
        enable_icloud=True,
        enable_usb=True,
        enable_airdrop=True,
        enable_file_watcher=True,
        watch_directories=watch_dirs,
        callback=on_new_video
    )
    
    # Show status
    status = service.get_status()
    logger.info("\nService Status:")
    logger.info(f"  iCloud: {'✓ Available' if status['icloud']['available'] else '✗ Not available'}")
    logger.info(f"  USB: {status['usb']['devices_connected']} device(s) connected")
    logger.info(f"  AirDrop: {'✓ Enabled' if status['airdrop']['enabled'] else '✗ Disabled'}")
    logger.info(f"  File Watcher: {'✓ Enabled' if status['file_watcher']['enabled'] else '✗ Disabled'}")
    logger.info("")
    
    try:
        service.start_all()
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nStopping all services...")
        service.stop_all()
        logger.success("✓ All services stopped")


def demo_scan_existing():
    """Demo: Scan for existing videos"""
    logger.info("Demo 6: Scan Existing Videos")
    logger.info("-" * 60)
    
    hours = input("Scan videos from last N hours (default: 24): ").strip()
    if not hours:
        hours = 24
    else:
        hours = int(hours)
    
    logger.info(f"Scanning for videos from last {hours} hours...")
    
    watch_dirs = [
        str(Path.home() / "Desktop"),
        str(Path.home() / "Downloads"),
        str(Path.home() / "Movies"),
    ]
    
    service = VideoIngestionService(
        enable_icloud=False,  # Scanning iCloud is slow
        enable_usb=False,
        enable_airdrop=False,
        enable_file_watcher=True,
        watch_directories=watch_dirs,
        callback=on_new_video
    )
    
    count = service.scan_existing_videos(hours=hours)
    
    logger.success(f"\n✓ Scan complete: found {count} videos")


def main():
    """Main menu"""
    logger.remove()  # Remove default handler
    logger.add(sys.stdout, colorize=True, format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")
    
    print("\n" + "=" * 60)
    print("   MediaPoster - Video Ingestion System Demo")
    print("=" * 60)
    print("\nChoose a demo:")
    print("  1. Test video validator (single file)")
    print("  2. Watch directory for new videos")
    print("  3. Monitor AirDrop")
    print("  4. Monitor iCloud Photos")
    print("  5. Monitor ALL sources simultaneously")
    print("  6. Scan for existing videos")
    print("  0. Exit")
    print()
    
    choice = input("Enter choice (0-6): ").strip()
    print()
    
    demos = {
        '1': demo_validator_only,
        '2': demo_file_watcher,
        '3': demo_airdrop_monitor,
        '4': demo_icloud_photos,
        '5': demo_all_sources,
        '6': demo_scan_existing,
    }
    
    if choice == '0':
        logger.info("Goodbye!")
        return
    
    if choice in demos:
        try:
            demos[choice]()
        except Exception as e:
            logger.error(f"Error: {e}")
            import traceback
            traceback.print_exc()
    else:
        logger.error("Invalid choice")


if __name__ == "__main__":
    main()
