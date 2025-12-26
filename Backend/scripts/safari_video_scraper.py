#!/usr/bin/env python3
"""
Safari Browser Automation for Instagram Video Scraping
Automates Safari to scroll through a profile, collect all post URLs,
then visit each one to extract and download video content.

Requirements:
- Safari with "Allow Remote Automation" enabled (Develop menu)
- selenium package: pip install selenium
- safaridriver enabled: safaridriver --enable

Usage:
    python safari_video_scraper.py personalbrandlaunch
    python safari_video_scraper.py personalbrandlaunch --max-posts 100
"""
import os
import sys
import json
import time
import argparse
import requests
import re
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

STORAGE_BASE = "/Users/isaiahdupree/Documents/CompetitorResearch/accounts"


class InstagramVideoScraper:
    def __init__(self, username: str, max_posts: int = 500):
        self.username = username
        self.max_posts = max_posts
        self.storage_path = Path(STORAGE_BASE) / username / "posts"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.manifest_path = Path(STORAGE_BASE) / username / "scrape_manifest.json"
        self.driver = None
        self.post_urls = []
        self.downloaded = []
        self.failed = []
        
    def load_manifest(self):
        """Load existing manifest if available"""
        if self.manifest_path.exists():
            with open(self.manifest_path) as f:
                data = json.load(f)
                self.post_urls = data.get('post_urls', [])
                self.downloaded = data.get('downloaded', [])
                self.failed = data.get('failed', [])
                print(f"Loaded manifest: {len(self.post_urls)} URLs, {len(self.downloaded)} downloaded")
    
    def save_manifest(self):
        """Save current state to manifest"""
        with open(self.manifest_path, 'w') as f:
            json.dump({
                'username': self.username,
                'post_urls': self.post_urls,
                'downloaded': self.downloaded,
                'failed': self.failed,
                'last_updated': datetime.now().isoformat()
            }, f, indent=2)
    
    def start_browser(self):
        """Start Safari browser"""
        print("Starting Safari browser...")
        options = webdriver.SafariOptions()
        self.driver = webdriver.Safari(options=options)
        self.driver.set_window_size(1200, 900)
        print("Safari started successfully")
    
    def stop_browser(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def login(self, username: str, password: str):
        """Log into Instagram"""
        print("\nLogging into Instagram...")
        self.driver.get("https://www.instagram.com/accounts/login/")
        time.sleep(5)
        
        try:
            # Wait for and dismiss any cookie popups
            try:
                cookie_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Allow') or contains(text(), 'Accept')]")
                for btn in cookie_buttons:
                    try:
                        btn.click()
                        time.sleep(1)
                    except:
                        pass
            except:
                pass
            
            # Find and fill username using JavaScript for reliability
            username_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='username']"))
            )
            self.driver.execute_script("arguments[0].value = arguments[1]", username_input, username)
            username_input.send_keys(" ")  # Trigger input event
            username_input.send_keys(Keys.BACKSPACE)
            time.sleep(1)
            
            # Find and fill password
            password_input = self.driver.find_element(By.CSS_SELECTOR, "input[name='password']")
            self.driver.execute_script("arguments[0].value = arguments[1]", password_input, password)
            password_input.send_keys(" ")
            password_input.send_keys(Keys.BACKSPACE)
            time.sleep(1)
            
            # Click login button
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            login_button.click()
            
            # Wait for login to complete
            print("Waiting for login to complete...")
            time.sleep(8)
            
            # Handle "Save Login Info" popup if present
            try:
                not_now_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Not Now') or contains(text(), 'Not now')]")
                for btn in not_now_buttons:
                    try:
                        btn.click()
                        time.sleep(1)
                    except:
                        pass
            except:
                pass
            
            # Check for login success
            if "login" not in self.driver.current_url.lower():
                print("✓ Login successful!")
                return True
            else:
                print("⚠️ Login may have failed, continuing anyway...")
                return False
                
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def scroll_and_collect_posts(self):
        """Scroll through profile and collect all post URLs"""
        # Go to Reels tab directly for more video content
        reels_url = f"https://www.instagram.com/{self.username}/reels/"
        print(f"\nNavigating to {reels_url}")
        self.driver.get(reels_url)
        
        # Wait for page to load
        time.sleep(3)
        
        # Check if we need to log in
        if "login" in self.driver.current_url.lower():
            print("\n⚠️  Redirected to login - session may have expired")
            return
        
        # Wait for posts grid to load
        print("Waiting for posts to load...")
        try:
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article a[href*='/p/'], article a[href*='/reel/']"))
            )
        except TimeoutException:
            print("Could not find posts. Make sure you're on the profile page.")
            return
        
        # Scroll and collect posts
        print("Scrolling and collecting post URLs...")
        last_height = 0
        scroll_attempts = 0
        max_scroll_attempts = 100
        
        while len(self.post_urls) < self.max_posts and scroll_attempts < max_scroll_attempts:
            # Find all post links
            post_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/'], a[href*='/reel/']")
            
            for link in post_links:
                href = link.get_attribute('href')
                if href and href not in self.post_urls:
                    # Check if it's a video (has video indicator)
                    try:
                        # Look for video icon in the post thumbnail
                        parent = link.find_element(By.XPATH, "./..")
                        video_icon = parent.find_elements(By.CSS_SELECTOR, "svg[aria-label*='Video'], svg[aria-label*='Reel']")
                        if video_icon or '/reel/' in href:
                            self.post_urls.append(href)
                            print(f"  Found video: {href.split('/')[-2]}")
                    except:
                        # If we can't determine, add it anyway for /reel/ URLs
                        if '/reel/' in href:
                            self.post_urls.append(href)
            
            # Scroll down
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Check if we've reached the bottom
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                scroll_attempts += 1
                if scroll_attempts >= 3:
                    print("Reached end of feed")
                    break
            else:
                scroll_attempts = 0
                last_height = new_height
            
            print(f"  Collected {len(self.post_urls)} video URLs so far...")
            self.save_manifest()
        
        print(f"\nTotal video URLs collected: {len(self.post_urls)}")
    
    def extract_video_url(self, post_url: str) -> str:
        """Visit a post page and extract the video URL"""
        try:
            self.driver.get(post_url)
            time.sleep(2)
            
            # Try to find video element
            video_elements = self.driver.find_elements(By.TAG_NAME, "video")
            for video in video_elements:
                src = video.get_attribute('src')
                if src and 'blob:' not in src:
                    return src
            
            # Try to find source element inside video
            source_elements = self.driver.find_elements(By.CSS_SELECTOR, "video source")
            for source in source_elements:
                src = source.get_attribute('src')
                if src and 'blob:' not in src:
                    return src
            
            # Try to extract from page source using regex
            page_source = self.driver.page_source
            video_patterns = [
                r'"video_url":"([^"]+)"',
                r'"playback_url":"([^"]+)"',
                r'src="(https://[^"]+\.mp4[^"]*)"',
            ]
            for pattern in video_patterns:
                match = re.search(pattern, page_source)
                if match:
                    url = match.group(1).replace('\\u0026', '&').replace('\\/', '/')
                    return url
            
        except Exception as e:
            print(f"    Error extracting video: {e}")
        
        return None
    
    def download_video(self, video_url: str, shortcode: str) -> bool:
        """Download video from URL"""
        filepath = self.storage_path / f"{shortcode}.mp4"
        
        if filepath.exists():
            return True
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15'
            }
            resp = requests.get(video_url, headers=headers, timeout=120, stream=True)
            if resp.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                return True
        except Exception as e:
            print(f"    Download error: {e}")
        
        return False
    
    def process_all_posts(self):
        """Visit each post and download the video"""
        print(f"\nProcessing {len(self.post_urls)} video posts...")
        
        for i, post_url in enumerate(self.post_urls):
            # Extract shortcode from URL
            match = re.search(r'/(?:p|reel|reels)/([A-Za-z0-9_-]+)', post_url)
            if not match:
                continue
            shortcode = match.group(1)
            
            # Skip if already downloaded
            if shortcode in self.downloaded:
                continue
            
            filepath = self.storage_path / f"{shortcode}.mp4"
            if filepath.exists():
                self.downloaded.append(shortcode)
                continue
            
            print(f"[{i+1}/{len(self.post_urls)}] Processing {shortcode}...", end=" ")
            
            video_url = self.extract_video_url(post_url)
            if not video_url:
                print("❌ No video URL found")
                self.failed.append(shortcode)
                continue
            
            if self.download_video(video_url, shortcode):
                size_mb = filepath.stat().st_size / (1024 * 1024) if filepath.exists() else 0
                print(f"✓ ({size_mb:.1f}MB)")
                self.downloaded.append(shortcode)
            else:
                print("❌ Download failed")
                self.failed.append(shortcode)
            
            self.save_manifest()
            time.sleep(1)  # Rate limiting
    
    def run(self, collect_only: bool = False, ig_username: str = None, ig_password: str = None, manual_login: bool = False):
        """Main run method"""
        self.load_manifest()
        
        try:
            self.start_browser()
            
            # Try auto login first if credentials provided, then fall back to manual
            login_success = False
            
            if ig_username and ig_password and not manual_login:
                print("\n🔐 Attempting automatic login...")
                login_success = self.login(ig_username, ig_password)
                time.sleep(2)
                
                # Check if we're still on login page (login failed)
                if "login" in self.driver.current_url.lower() or not login_success:
                    print("\n⚠️  Auto-login may have failed. Switching to manual login...")
                    manual_login = True
            
            # Manual login - user logs in themselves
            if manual_login:
                print("\n" + "="*60)
                print("MANUAL LOGIN REQUIRED")
                print("="*60)
                if "login" not in self.driver.current_url.lower():
                    self.driver.get("https://www.instagram.com/accounts/login/")
                print("\n👤 Please log into Instagram in the Safari window.")
                print("   Take your time - handle any 2FA or security prompts.")
                print("\n   Press ENTER here when you're logged in and see the feed...")
                input()
                print("✓ Continuing with scraping...")
                time.sleep(2)
            
            # Collect post URLs if we don't have enough
            if len(self.post_urls) < self.max_posts:
                self.scroll_and_collect_posts()
                self.save_manifest()
            
            if collect_only:
                print("\nCollection complete. Run without --collect-only to download videos.")
                return
            
            # Process and download all posts
            self.process_all_posts()
            
        finally:
            self.stop_browser()
            self.save_manifest()
        
        # Summary
        total_videos = len(list(self.storage_path.glob("*.mp4")))
        total_size = sum(f.stat().st_size for f in self.storage_path.glob("*.mp4"))
        
        print(f"\n{'='*60}")
        print(f"SCRAPING COMPLETE")
        print(f"{'='*60}")
        print(f"  URLs collected: {len(self.post_urls)}")
        print(f"  Downloaded: {len(self.downloaded)}")
        print(f"  Failed: {len(self.failed)}")
        print(f"  Total videos: {total_videos}")
        print(f"  Total size: {total_size/(1024*1024):.1f} MB")
        print(f"\n  Storage: {self.storage_path}")


def main():
    parser = argparse.ArgumentParser(description="Safari-based Instagram video scraper")
    parser.add_argument("username", help="Instagram username to scrape")
    parser.add_argument("--max-posts", type=int, default=500, help="Maximum posts to collect")
    parser.add_argument("--collect-only", action="store_true", help="Only collect URLs, don't download")
    parser.add_argument("--resume", action="store_true", help="Resume from existing manifest")
    parser.add_argument("--manual-login", action="store_true", help="Pause for manual login")
    parser.add_argument("--ig-user", help="Instagram login username")
    parser.add_argument("--ig-pass", help="Instagram login password")
    args = parser.parse_args()
    
    scraper = InstagramVideoScraper(args.username, args.max_posts)
    scraper.run(
        collect_only=args.collect_only, 
        ig_username=args.ig_user, 
        ig_password=args.ig_pass,
        manual_login=args.manual_login
    )


if __name__ == "__main__":
    main()
