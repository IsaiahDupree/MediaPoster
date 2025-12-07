"""
Comprehensive End-to-End Testing Suite for MediaPoster
Tests the full workflow: Video → Google Drive → Blotato → Social Media
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Load environment
load_dotenv()

# Configure logger
logger.remove()
logger.add(sys.stdout, format="<level>{message}</level>", level="INFO")


class MediaPosterE2ETests:
    """End-to-end test suite for MediaPoster publishing workflow"""
    
    def __init__(self):
        self.test_video_path = None
        self.google_drive_url = None
        self.blotato_media_url = None
        self.post_submission_id = None
        
    def test_1_environment_setup(self):
        """Test 1: Verify all required environment variables"""
        logger.info("\n" + "="*80)
        logger.info("TEST 1: Environment Setup")
        logger.info("="*80)
        
        required_vars = {
            'BLOTATO_API_KEY': os.getenv('BLOTATO_API_KEY'),
            'GOOGLE_DRIVE_CREDENTIALS_PATH': os.getenv('GOOGLE_DRIVE_CREDENTIALS_PATH'),
            'GOOGLE_DRIVE_FOLDER_ID': os.getenv('GOOGLE_DRIVE_FOLDER_ID'),
            'INSTAGRAM_ACCOUNT_ID': os.getenv('INSTAGRAM_ACCOUNT_ID'),
        }
        
        all_present = True
        for var, value in required_vars.items():
            if value:
                logger.success(f"  ✓ {var}: {'*' * 20}... (configured)")
            else:
                logger.error(f"  ✗ {var}: Not configured")
                all_present = False
        
        if all_present:
            logger.success("✓ Environment setup complete")
            return True
        else:
            logger.error("✗ Missing required environment variables")
            return False
    
    def test_2_blotato_connection(self):
        """Test 2: Verify Blotato API connectivity"""
        logger.info("\n" + "="*80)
        logger.info("TEST 2: Blotato API Connection")
        logger.info("="*80)
        
        from modules.publishing.blotato_client import BlotatoClient
        
        try:
            client = BlotatoClient()
            result = client.get_account_info()
            
            if result:
                logger.success("✓ Successfully connected to Blotato API")
                accounts = result.get('accounts', [])
                logger.info(f"  Found {len(accounts)} connected accounts")
                for acc in accounts[:5]:
                    logger.info(f"    - {acc.get('platform')}: @{acc.get('username')}")
                return True
            else:
                logger.error("✗ Failed to connect to Blotato API")
                return False
                
        except Exception as e:
            logger.error(f"✗ Blotato connection error: {e}")
            return False
    
    def test_3_google_drive_setup(self):
        """Test 3: Verify Google Drive credentials and access"""
        logger.info("\n" + "="*80)
        logger.info("TEST 3: Google Drive Setup")
        logger.info("="*80)
        
        creds_path = os.getenv('GOOGLE_DRIVE_CREDENTIALS_PATH')
        
        if not creds_path:
            logger.error("✗ GOOGLE_DRIVE_CREDENTIALS_PATH not set")
            return False
        
        creds_file = Path(creds_path)
        
        if not creds_file.exists():
            logger.error(f"✗ Credentials file not found: {creds_path}")
            logger.info(f"  Please save your Google Cloud service account JSON to:")
            logger.info(f"  {creds_file.absolute()}")
            return False
        
        logger.success(f"✓ Credentials file found: {creds_path}")
        
        # Try to initialize Google Drive client
        try:
            from modules.cloud_staging.google_drive_uploader import GoogleDriveUploader
            
            uploader = GoogleDriveUploader()
            logger.success("✓ Google Drive client initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"✗ Google Drive initialization failed: {e}")
            logger.info("  Check if credentials JSON is valid")
            return False
    
    def test_4_upload_to_google_drive(self, test_video_path: str = None):
        """Test 4: Upload test video to Google Drive"""
        logger.info("\n" + "="*80)
        logger.info("TEST 4: Upload to Google Drive")
        logger.info("="*80)
        
        if not test_video_path:
            logger.warning("  No test video provided - skipping upload test")
            logger.info("  To test upload: python3 test_e2e.py --video path/to/video.mp4")
            return None
        
        test_video = Path(test_video_path)
        
        if not test_video.exists():
            logger.error(f"✗ Test video not found: {test_video_path}")
            return False
        
        logger.info(f"  Uploading: {test_video.name}")
        
        try:
            from modules.cloud_staging.google_drive_uploader import GoogleDriveUploader
            
            uploader = GoogleDriveUploader()
            public_url = uploader.upload_video(test_video)
            
            if public_url:
                logger.success(f"✓ Uploaded to Google Drive")
                logger.info(f"  Public URL: {public_url}")
                self.google_drive_url = public_url
                return True
            else:
                logger.error("✗ Upload failed - no URL returned")
                return False
                
        except Exception as e:
            logger.error(f"✗ Upload error: {e}")
            return False
    
    def test_5_upload_to_blotato(self):
        """Test 5: Upload media to Blotato from Google Drive URL"""
        logger.info("\n" + "="*80)
        logger.info("TEST 5: Upload to Blotato")
        logger.info("="*80)
        
        if not self.google_drive_url:
            logger.warning("  No Google Drive URL - skipping Blotato upload")
            return None
        
        try:
            from modules.publishing.blotato_client import BlotatoClient
            
            client = BlotatoClient()
            blotato_url = client.upload_media(None, public_url=self.google_drive_url)
            
            if blotato_url:
                logger.success(f"✓ Media uploaded to Blotato")
                logger.info(f"  Blotato URL: {blotato_url}")
                self.blotato_media_url = blotato_url
                return True
            else:
                logger.error("✗ Blotato upload failed")
                return False
                
        except Exception as e:
            logger.error(f"✗ Blotato upload error: {e}")
            return False
    
    def test_6_create_draft_post(self):
        """Test 6: Create a DRAFT post (won't publish)"""
        logger.info("\n" + "="*80)
        logger.info("TEST 6: Create Draft Post (Instagram)")
        logger.info("="*80)
        
        if not self.blotato_media_url:
            logger.warning("  No Blotato media URL - skipping post creation")
            return None
        
        account_id = os.getenv('INSTAGRAM_ACCOUNT_ID')
        
        if not account_id:
            logger.error("✗ INSTAGRAM_ACCOUNT_ID not configured")
            return False
        
        try:
            from modules.publishing.blotato_client import BlotatoClient
            
            client = BlotatoClient()
            
            # Create draft post (won't actually publish)
            result = client.create_post(
                account_id=account_id,
                platform='instagram',
                text='🧪 Test post from MediaPoster (DRAFT - Not published)',
                media_urls=[self.blotato_media_url],
                target_config={'isDraft': True}  # Draft mode
            )
            
            if result:
                logger.success(f"✓ Draft post created")
                logger.info(f"  Submission ID: {result.get('post_submission_id')}")
                logger.info(f"  Status: {result.get('status')}")
                self.post_submission_id = result.get('post_submission_id')
                return True
            else:
                logger.error("✗ Draft post creation failed")
                return False
                
        except Exception as e:
            logger.error(f"✗ Post creation error: {e}")
            return False
    
    def run_all_tests(self, test_video_path: str = None):
        """Run all tests in sequence"""
        logger.info("\n" + "╔" + "="*78 + "╗")
        logger.info("║" + " "*22 + "MEDIAPOSTER E2E TEST SUITE" + " "*30 + "║")
        logger.info("╚" + "="*78 + "╝")
        
        results = {}
        
        # Test 1: Environment
        results['environment'] = self.test_1_environment_setup()
        if not results['environment']:
            logger.error("\n⚠️  Stopping tests - environment setup failed")
            return results
        
        # Test 2: Blotato
        results['blotato_connection'] = self.test_2_blotato_connection()
        
        # Test 3: Google Drive
        results['google_drive_setup'] = self.test_3_google_drive_setup()
        
        # Test 4: Upload to Google Drive (optional)
        if test_video_path:
            results['google_drive_upload'] = self.test_4_upload_to_google_drive(test_video_path)
            
            # Test 5: Upload to Blotato
            if results.get('google_drive_upload'):
                results['blotato_upload'] = self.test_5_upload_to_blotato()
                
                # Test 6: Create draft post
                if results.get('blotato_upload'):
                    results['draft_post'] = self.test_6_create_draft_post()
        
        # Summary
        logger.info("\n" + "="*80)
        logger.info("TEST SUMMARY")
        logger.info("="*80)
        
        total = len(results)
        passed = sum(1 for r in results.values() if r is True)
        skipped = sum(1 for r in results.values() if r is None)
        failed = total - passed - skipped
        
        for test_name, result in results.items():
            status = "✓ PASS" if result is True else ("⊘ SKIP" if result is None else "✗ FAIL")
            logger.info(f"  {status}  {test_name}")
        
        logger.info("="*80)
        logger.info(f"Total: {total} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
        logger.info("="*80)
        
        return results


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='MediaPoster End-to-End Tests')
    parser.add_argument('--video', type=str, help='Path to test video file')
    parser.add_argument('--quick', action='store_true', help='Run quick tests only (skip upload)')
    
    args = parser.parse_args()
    
    tester = MediaPosterE2ETests()
    
    if args.quick:
        logger.info("Running quick tests (connection checks only)\n")
        results = tester.run_all_tests(test_video_path=None)
    else:
        results = tester.run_all_tests(test_video_path=args.video)
    
    # Exit code based on results
    if all(r in [True, None] for r in results.values()):
        sys.exit(0)
    else:
        sys.exit(1)
