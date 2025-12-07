"""
Browser Profile Manager
Finds and manages browser profiles for Chrome and Safari.
"""
import os
import json
import platform
from pathlib import Path
from typing import Dict, List, Optional, Literal
from loguru import logger


BrowserType = Literal["chrome", "safari"]


class BrowserProfileManager:
    """Manages browser profile discovery and configuration for Chrome and Safari."""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize the Browser Profile Manager.
        
        Args:
            config_file: Path to save/load profile configuration
        """
        if config_file is None:
            config_file = Path(__file__).parent / "browser_profile_config.json"
        
        self.config_file = Path(config_file)
        self.system = platform.system()
    
    def get_safari_user_data_dir(self) -> Path:
        """
        Get the Safari User Data Directory on macOS.
        
        Returns:
            Path to Safari directory
        """
        if self.system != "Darwin":
            raise OSError("Safari is only available on macOS")
        
        return Path(os.path.expanduser("~/Library/Safari"))
    
    def get_chrome_user_data_dir(self) -> Path:
        """Get the Chrome User Data Directory based on the operating system."""
        if self.system == "Darwin":  # macOS
            return Path(os.path.expanduser("~/Library/Application Support/Google/Chrome"))
        elif self.system == "Windows":
            return Path(os.path.expanduser("~/AppData/Local/Google/Chrome/User Data"))
        elif self.system == "Linux":
            return Path(os.path.expanduser("~/.config/google-chrome"))
        else:
            raise OSError(f"Unsupported operating system: {self.system}")
    
    def find_safari_profiles(self) -> List[Dict[str, str]]:
        """
        Find Safari profile information.
        
        Note: Safari doesn't have multiple profiles like Chrome,
        but we can detect if Safari is configured.
        
        Returns:
            List with Safari profile info
        """
        safari_dir = self.get_safari_user_data_dir()
        profiles = []
        
        if not safari_dir.exists():
            logger.warning(f"Safari directory not found: {safari_dir}")
            return profiles
        
        # Safari uses a single profile structure
        # Check for key files to confirm it's set up
        key_files = ["Cookies.binarycookies", "History.db", "Bookmarks.plist"]
        has_data = any((safari_dir / f).exists() for f in key_files)
        
        if has_data:
            profiles.append({
                "name": "Default",
                "path": str(safari_dir),
                "full_path": str(safari_dir),
                "is_default": True,
                "browser": "safari"
            })
        
        logger.info(f"Found {len(profiles)} Safari profile(s)")
        return profiles
    
    def find_chrome_profiles(self) -> List[Dict[str, str]]:
        """Find all Chrome profiles on the system."""
        user_data_dir = self.get_chrome_user_data_dir()
        profiles = []
        
        if not user_data_dir.exists():
            logger.warning(f"Chrome User Data directory not found: {user_data_dir}")
            return profiles
        
        logger.info(f"Searching for Chrome profiles in: {user_data_dir}")
        
        # Check for Default profile
        default_profile = user_data_dir / "Default"
        if default_profile.exists():
            profiles.append({
                "name": "Default",
                "path": str(default_profile),
                "full_path": str(user_data_dir),
                "is_default": True,
                "browser": "chrome"
            })
        
        # Check for numbered profiles
        for item in user_data_dir.iterdir():
            if item.is_dir() and item.name.startswith("Profile "):
                profiles.append({
                    "name": item.name,
                    "path": str(item),
                    "full_path": str(user_data_dir),
                    "is_default": False,
                    "browser": "chrome"
                })
        
        # Check Local State for profile info
        local_state_file = user_data_dir / "Local State"
        if local_state_file.exists():
            try:
                with open(local_state_file, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                
                info_cache = local_state.get("profile", {}).get("info_cache", {})
                
                for profile_name, profile_data in info_cache.items():
                    if not any(p["name"] == profile_name for p in profiles):
                        profile_path = user_data_dir / profile_name
                        if profile_path.exists():
                            profiles.append({
                                "name": profile_name,
                                "path": str(profile_path),
                                "full_path": str(user_data_dir),
                                "is_default": profile_name == "Default",
                                "browser": "chrome",
                                "display_name": profile_data.get("name", profile_name),
                                "user_name": profile_data.get("user_name", ""),
                            })
            except Exception as e:
                logger.warning(f"Could not parse Local State: {e}")
        
        logger.info(f"Found {len(profiles)} Chrome profile(s)")
        return profiles
    
    def find_all_profiles(self, browser_type: Optional[BrowserType] = None) -> List[Dict[str, str]]:
        """
        Find all profiles for specified browser(s).
        
        Args:
            browser_type: "chrome", "safari", or None for both
            
        Returns:
            List of all profiles
        """
        all_profiles = []
        
        if browser_type is None or browser_type == "chrome":
            all_profiles.extend(self.find_chrome_profiles())
        
        if browser_type is None or browser_type == "safari":
            if self.system == "Darwin":  # Only macOS has Safari
                all_profiles.extend(self.find_safari_profiles())
        
        return all_profiles
    
    def select_profile(self, browser_type: BrowserType, profile_name: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Select a profile by browser type and name.
        
        Args:
            browser_type: "chrome" or "safari"
            profile_name: Name of profile (e.g., "Default")
            
        Returns:
            Selected profile dictionary or None
        """
        profiles = self.find_all_profiles(browser_type)
        
        if not profiles:
            logger.error(f"No {browser_type} profiles found")
            return None
        
        if profile_name:
            for profile in profiles:
                if profile["name"] == profile_name and profile.get("browser") == browser_type:
                    logger.info(f"Selected {browser_type} profile: {profile_name}")
                    return profile
            logger.warning(f"Profile '{profile_name}' not found for {browser_type}")
        
        # Return default or first profile
        default_profile = next((p for p in profiles if p.get("is_default") and p.get("browser") == browser_type), None)
        if default_profile:
            logger.info(f"Using default {browser_type} profile: {default_profile['name']}")
            return default_profile
        
        # Fallback to first profile of this type
        first_profile = next((p for p in profiles if p.get("browser") == browser_type), None)
        if first_profile:
            logger.info(f"Using first available {browser_type} profile: {first_profile['name']}")
            return first_profile
        
        return None
    
    def save_profile_config(self, profile: Dict[str, str]) -> bool:
        """Save the selected profile configuration to file."""
        try:
            profile_copy = {k: str(v) if isinstance(v, Path) else v for k, v in profile.items()}
            
            config = {
                "selected_profile": profile_copy,
                "system": self.system,
                "all_profiles": [
                    {k: str(v) if isinstance(v, Path) else v for k, v in p.items()}
                    for p in self.find_all_profiles()
                ]
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.success(f"Profile configuration saved to: {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save profile config: {e}")
            return False
    
    def load_profile_config(self) -> Optional[Dict]:
        """Load saved profile configuration from file."""
        if not self.config_file.exists():
            return None
        
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load profile config: {e}")
            return None
    
    def get_saved_profile(self) -> Optional[Dict[str, str]]:
        """Get the saved profile from configuration."""
        config = self.load_profile_config()
        if config and "selected_profile" in config:
            return config["selected_profile"]
        return None
    
    def list_profiles(self, browser_type: Optional[BrowserType] = None):
        """List all available profiles."""
        profiles = self.find_all_profiles(browser_type)
        
        if not profiles:
            logger.warning("No profiles found")
            return
        
        logger.info(f"\n{'='*60}")
        logger.info("Available Browser Profiles:")
        logger.info(f"{'='*60}")
        
        # Group by browser
        chrome_profiles = [p for p in profiles if p.get("browser") == "chrome"]
        safari_profiles = [p for p in profiles if p.get("browser") == "safari"]
        
        if chrome_profiles:
            logger.info("\n🌐 Chrome Profiles:")
            for i, profile in enumerate(chrome_profiles, 1):
                logger.info(f"  {i}. {profile['name']}")
                logger.info(f"     Path: {profile['path']}")
                logger.info(f"     Default: {'Yes' if profile.get('is_default') else 'No'}")
        
        if safari_profiles:
            logger.info("\n🍎 Safari Profiles:")
            for i, profile in enumerate(safari_profiles, 1):
                logger.info(f"  {i}. {profile['name']}")
                logger.info(f"     Path: {profile['path']}")
                logger.info(f"     Default: {'Yes' if profile.get('is_default') else 'No'}")


def main():
    """CLI for Browser Profile Manager."""
    import sys
    
    manager = BrowserProfileManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            browser_type = sys.argv[2] if len(sys.argv) > 2 else None
            manager.list_profiles(browser_type)
        elif command == "select":
            if len(sys.argv) < 3:
                logger.error("Usage: select <browser_type> [profile_name]")
                logger.info("Example: select safari Default")
                return
            
            browser_type = sys.argv[2]
            profile_name = sys.argv[3] if len(sys.argv) > 3 else None
            
            if browser_type not in ["chrome", "safari"]:
                logger.error(f"Invalid browser type: {browser_type}. Must be 'chrome' or 'safari'")
                return
            
            profile = manager.select_profile(browser_type, profile_name)
            if profile:
                manager.save_profile_config(profile)
                logger.success(f"Profile '{profile['name']}' ({browser_type}) saved to config")
        elif command == "show":
            config = manager.load_profile_config()
            if config:
                profile = config.get('selected_profile', {})
                logger.info(f"Current profile: {profile.get('name', 'None')} ({profile.get('browser', 'unknown')})")
            else:
                logger.warning("No saved profile configuration")
        else:
            logger.error(f"Unknown command: {command}")
            logger.info("Usage: python browser_profile_manager.py [list|select <browser> [profile]|show]")
    else:
        manager.list_profiles()


if __name__ == "__main__":
    main()

