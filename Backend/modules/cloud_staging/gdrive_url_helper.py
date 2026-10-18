"""
Google Drive URL Helper for Blotato Integration
Converts Google Drive sharing URLs to download URLs
"""
import re
from typing import Optional
from loguru import logger


def extract_file_id(drive_url: str) -> Optional[str]:
    """
    Extract file ID from various Google Drive URL formats
    
    Args:
        drive_url: Google Drive URL (any format)
        
    Returns:
        File ID or None if not found
    """
    # Pattern 1: /file/d/FILE_ID/view
    pattern1 = r'/file/d/([a-zA-Z0-9_-]+)/view'
    match = re.search(pattern1, drive_url)
    if match:
        return match.group(1)
    
    # Pattern 2: id=FILE_ID
    pattern2 = r'[?&]id=([a-zA-Z0-9_-]+)'
    match = re.search(pattern2, drive_url)
    if match:
        return match.group(1)
    
    # Pattern 3: /open?id=FILE_ID
    pattern3 = r'/open\?id=([a-zA-Z0-9_-]+)'
    match = re.search(pattern3, drive_url)
    if match:
        return match.group(1)
    
    return None


def convert_to_download_url(drive_url: str) -> Optional[str]:
    """
    Convert Google Drive sharing URL to direct download URL for Blotato
    
    Args:
        drive_url: Google Drive sharing URL
        
    Returns:
        Direct download URL or None if conversion failed
        
    Examples:
        Input:  https://drive.google.com/file/d/FILE_ID/view?usp=sharing
        Output: https://drive.google.com/uc?export=download&id=FILE_ID
    """
    file_id = extract_file_id(drive_url)
    
    if not file_id:
        logger.error(f"Could not extract file ID from URL: {drive_url}")
        return None
    
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    logger.info(f"Converted Drive URL:")
    logger.info(f"  From: {drive_url[:80]}...")
    logger.info(f"  To:   {download_url}")
    
    return download_url


def validate_drive_url(drive_url: str) -> bool:
    """
    Check if URL is a valid Google Drive URL
    
    Args:
        drive_url: URL to validate
        
    Returns:
        True if valid Google Drive URL
    """
    return 'drive.google.com' in drive_url


# Example usage
if __name__ == '__main__':
    test_urls = [
        "https://drive.google.com/file/d/18-UgDEaKG7YR7AewIDd_Qi4QCLCX5Kop/view?usp=drivesdk",
        "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/view?usp=sharing",
        "https://drive.google.com/open?id=1XyZ123AbC456DeF789GhI",
    ]
    
    print("\n" + "="*80)
    print("Google Drive URL Conversion Tests")
    print("="*80)
    
    for url in test_urls:
        print(f"\nOriginal: {url}")
        converted = convert_to_download_url(url)
        if converted:
            print(f"Download: {converted}")
        else:
            print("Failed to convert")
    
    print("\n" + "="*80)
