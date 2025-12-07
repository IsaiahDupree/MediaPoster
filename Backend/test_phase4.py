#!/usr/bin/env python3
"""
Phase 4 Testing - Cloud Staging & Publishing
Test Google Drive upload and Blotato publishing
"""
import sys
from pathlib import Path
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))

from modules.cloud_staging import GoogleDriveUploader, StorageManager
from modules.publishing import BlotatoClient, ContentPublisher


def test_google_drive():
    """Test Google Drive upload"""
    logger.info("\n" + "="*60)
    logger.info("TEST 1: Google Drive Upload")
    logger.info("="*60)
    
    logger.info("\nRequires: google_credentials.json in backend/")
    logger.info("Get it from: Google Cloud Console > APIs > Credentials")
    
    cont = input("\nDo you have credentials? (y/n) [n]: ").strip().lower() == 'y'
    if not cont:
        logger.warning("Skipped - get credentials first")
        return
    
    try:
        drive = GoogleDriveUploader()
        
        logger.info("\n1. Authenticating...")
        if not drive.authenticate():
            logger.error("Authentication failed")
            return
        
        logger.info("\n2. Getting storage quota...")
        quota = drive.get_storage_quota()
        if quota:
            logger.success(f"✓ Drive Storage:")
            logger.info(f"   Total: {quota['total_gb']:.2f} GB")
            logger.info(f"   Used: {quota['used_gb']:.2f} GB")
            logger.info(f"   Free: {quota['remaining_gb']:.2f} GB")
        
        # Test file upload
        test_file = input("\nEnter test file path (or skip): ").strip()
        if test_file:
            test_path = Path(test_file).expanduser()
            if test_path.exists():
                logger.info("\n3. Uploading test file...")
                result = drive.upload_clip(test_path, {'test': True})
                if result:
                    logger.success(f"✓ Upload successful!")
                    logger.info(f"   Link: {result['link']}")
            else:
                logger.error("File not found")
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()


def test_blotato():
    """Test Blotato API"""
    logger.info("\n" + "="*60)
    logger.info("TEST 2: Blotato API")
    logger.info("="*60)
    
    logger.info("\nRequires: BLOTATO_API_KEY in .env")
    
    try:
        client = BlotatoClient()
        
        logger.info("\n1. Getting account info...")
        accounts = client.get_account_info()
        if accounts:
            logger.success("✓ Connected to Blotato")
        else:
            logger.warning("Could not get accounts - check API key")
        
        # Test upload (don't actually post)
        test_file = input("\nTest clip upload? Enter path (or skip): ").strip()
        if test_file:
            test_path = Path(test_file).expanduser()
            if test_path.exists():
                logger.info("\n2. Uploading to Blotato...")
                logger.warning("This will use your Blotato credits!")
                
                confirm = input("Continue? (yes/no) [no]: ").strip().lower() == 'yes'
                if confirm:
                    media_id = client.upload_media(test_path, "Test Upload")
                    if media_id:
                        logger.success(f"✓ Upload successful: {media_id}")
                        logger.info("   (Media uploaded but not posted)")
                else:
                    logger.info("Skipped")
            else:
                logger.error("File not found")
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()


def test_complete_publishing():
    """Test complete publishing workflow"""
    logger.info("\n" + "="*60)
    logger.info("TEST 3: Complete Publishing Workflow")
    logger.info("="*60)
    
    clip_path_str = input("\nEnter clip path: ").strip()
    if not clip_path_str:
        logger.warning("Skipped")
        return
    
    clip_path = Path(clip_path_str).expanduser()
    if not clip_path.exists():
        logger.error(f"Not found: {clip_path}")
        return
    
    logger.info("\nSelect services to use:")
    use_drive = input("Upload to Google Drive? (y/n) [y]: ").strip().lower() != 'n'
    use_blotato = input("Post via Blotato? (y/n) [n]: ").strip().lower() == 'y'
    
    if use_blotato:
        logger.warning("\n⚠️  This will POST to real platforms!")
        logger.warning("Make sure you want to publish this clip.")
        confirm = input("\nType 'PUBLISH' to confirm: ").strip()
        if confirm != 'PUBLISH':
            logger.info("Cancelled")
            return
    
    try:
        publisher = ContentPublisher(
            use_cloud_staging=use_drive,
            use_blotato=use_blotato
        )
        
        # Get platforms
        platforms = []
        if use_blotato:
            logger.info("\nSelect platforms:")
            if input("  TikTok? (y/n) [y]: ").strip().lower() != 'n':
                platforms.append('tiktok')
            if input("  Instagram? (y/n) [y]: ").strip().lower() != 'n':
                platforms.append('instagram')
            if input("  YouTube Shorts? (y/n) [n]: ").strip().lower() == 'y':
                platforms.append('youtube')
        
        # Get caption
        caption = input("\nCaption (or press Enter for default): ").strip()
        if not caption:
            caption = "Check this out! 🔥"
        
        # Get hashtags
        hashtags_str = input("Hashtags (space-separated, or skip): ").strip()
        hashtags = []
        if hashtags_str:
            hashtags = ['#' + tag.lstrip('#') for tag in hashtags_str.split()]
        else:
            hashtags = ['#fyp', '#viral', '#trending']
        
        # Metadata
        metadata = {
            'caption': caption,
            'hashtags': hashtags,
            'title': clip_path.stem
        }
        
        # Schedule?
        schedule_str = input("\nDelay posting by X minutes (or 0 for immediate) [0]: ").strip()
        delay = int(schedule_str) if schedule_str else 0
        
        logger.info("\n" + "="*60)
        logger.info("PUBLISHING...")
        logger.info("="*60)
        
        result = publisher.publish_clip(
            clip_path,
            platforms if platforms else ['tiktok'],
            metadata,
            schedule_delay_minutes=delay if delay > 0 else None
        )
        
        logger.info("\n" + "="*60)
        if result['success']:
            logger.success("✅ PUBLISHING COMPLETE!")
        else:
            logger.error("❌ PUBLISHING FAILED")
        logger.info("="*60)
        
        if result.get('storage'):
            logger.info(f"\n📤 Cloud: {result['storage']['link']}")
        
        if result.get('posts'):
            logger.info(f"\n🚀 Post ID: {result['posts']['post_id']}")
            if result['posts'].get('urls'):
                logger.info("📱 URLs:")
                for platform, url in result['posts']['urls'].items():
                    logger.info(f"   {platform}: {url}")
        
    except Exception as e:
        logger.error(f"Failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main menu"""
    print("\n" + "="*60)
    print("   MediaPoster - Phase 4 Testing")
    print("   (Cloud Staging & Publishing)")
    print("="*60)
    print("\nChoose a test:")
    print("  1. Google Drive Upload")
    print("  2. Blotato API")
    print("  3. Complete Publishing Workflow (recommended)")
    print("  0. Exit")
    print()
    
    choice = input("Enter choice (0-3): ").strip()
    print()
    
    if choice == '0':
        logger.info("Goodbye!")
        return
    
    elif choice == '1':
        test_google_drive()
    
    elif choice == '2':
        test_blotato()
    
    elif choice == '3':
        test_complete_publishing()
    
    else:
        logger.error("Invalid choice")


if __name__ == "__main__":
    main()
