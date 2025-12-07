"""
Chrome Profile Manager
Finds Chrome profiles on the system and manages profile selection for automation.
"""
import os
import json
import platform
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger


class ChromeProfileManager:
    """Manages Chrome profile discovery and configuration."""
    
    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize the Chrome Profile Manager.
        
        Args:
            config_file: Path to save/load profile configuration
        """
        if config_file is None:
            # Default to automation directory
            config_file = Path(__file__).parent / "chrome_profile_config.json"
        
        self.config_file = Path(config_file)
        self.system = platform.system()
        
    def get_chrome_user_data_dir(self) -> Path:
        """
        Get the Chrome User Data Directory based on the operating system.
        
        Returns:
            Path to Chrome User Data Directory
        """
        if self.system == "Darwin":  # macOS
            return Path(os.path.expanduser("~/Library/Application Support/Google/Chrome"))
        elif self.system == "Windows":
            return Path(os.path.expanduser("~/AppData/Local/Google/Chrome/User Data"))
        elif self.system == "Linux":
            return Path(os.path.expanduser("~/.config/google-chrome"))
        else:
            raise OSError(f"Unsupported operating system: {self.system}")
    
    def find_all_profiles(self) -> List[Dict[str, str]]:
        """
        Find all Chrome profiles on the system.
        
        Returns:
            List of profile dictionaries with name, path, and info
        """
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
                "is_default": True
            })
        
        # Check for numbered profiles (Profile 1, Profile 2, etc.)
        for item in user_data_dir.iterdir():
            if item.is_dir() and item.name.startswith("Profile "):
                profiles.append({
                    "name": item.name,
                    "path": str(item),
                    "full_path": str(user_data_dir),
                    "is_default": False
                })
        
        # Also check Local State for profile info
        local_state_file = user_data_dir / "Local State"
        if local_state_file.exists():
            try:
                with open(local_state_file, 'r', encoding='utf-8') as f:
                    local_state = json.load(f)
                    
                # Extract profile info from Local State
                profile_info = local_state.get("profile", {})
                info_cache = local_state.get("profile", {}).get("info_cache", {})
                
                for profile_name, profile_data in info_cache.items():
                    # Check if we already have this profile
                    if not any(p["name"] == profile_name for p in profiles):
                        profile_path = user_data_dir / profile_name
                        if profile_path.exists():
                            profiles.append({
                                "name": profile_name,
                                "path": str(profile_path),
                                "full_path": str(user_data_dir),
                                "is_default": profile_name == "Default",
                                "display_name": profile_data.get("name", profile_name),
                                "user_name": profile_data.get("user_name", ""),
                                "avatar_icon": profile_data.get("avatar_icon", "")
                            })
            except Exception as e:
                logger.warning(f"Could not parse Local State: {e}")
        
        logger.info(f"Found {len(profiles)} Chrome profile(s)")
        return profiles
    
    def select_profile(self, profile_name: Optional[str] = None) -> Optional[Dict[str, str]]:
        """
        Select a Chrome profile by name, or prompt for selection.
        
        Args:
            profile_name: Name of profile to select (e.g., "Default", "Profile 1")
            
        Returns:
            Selected profile dictionary or None
        """
        profiles = self.find_all_profiles()
        
        if not profiles:
            logger.error("No Chrome profiles found")
            return None
        
        if profile_name:
            # Find by name
            for profile in profiles:
                if profile["name"] == profile_name:
                    logger.info(f"Selected profile: {profile_name}")
                    return profile
            logger.warning(f"Profile '{profile_name}' not found")
        
        # If no name provided or not found, return Default or first profile
        default_profile = next((p for p in profiles if p.get("is_default")), None)
        if default_profile:
            logger.info(f"Using default profile: {default_profile['name']}")
            return default_profile
        
        # Fallback to first profile
        logger.info(f"Using first available profile: {profiles[0]['name']}")
        return profiles[0]
    
    def save_profile_config(self, profile: Dict[str, str]) -> bool:
        """
        Save the selected profile configuration to file.
        
        Args:
            profile: Profile dictionary to save
            
        Returns:
            True if saved successfully
        """
        try:
            # Convert Path objects to strings for JSON serialization
            profile_copy = {k: str(v) if isinstance(v, Path) else v for k, v in profile.items()}
            
            config = {
                "selected_profile": profile_copy,
                "chrome_user_data_dir": str(self.get_chrome_user_data_dir()),
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
        """
        Load saved profile configuration from file.
        
        Returns:
            Configuration dictionary or None
        """
        if not self.config_file.exists():
            logger.warning(f"Profile config file not found: {self.config_file}")
            return None
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            logger.info(f"Profile configuration loaded from: {self.config_file}")
            return config
        except Exception as e:
            logger.error(f"Failed to load profile config: {e}")
            return None
    
    def get_saved_profile(self) -> Optional[Dict[str, str]]:
        """
        Get the saved profile from configuration.
        
        Returns:
            Saved profile dictionary or None
        """
        config = self.load_profile_config()
        if config and "selected_profile" in config:
            return config["selected_profile"]
        return None
    
    def list_profiles(self) -> None:
        """List all available Chrome profiles."""
        profiles = self.find_all_profiles()
        
        if not profiles:
            logger.warning("No Chrome profiles found")
            return
        
        logger.info(f"\n{'='*60}")
        logger.info("Available Chrome Profiles:")
        logger.info(f"{'='*60}")
        
        for i, profile in enumerate(profiles, 1):
            logger.info(f"\n{i}. {profile['name']}")
            logger.info(f"   Path: {profile['path']}")
            if 'display_name' in profile:
                logger.info(f"   Display Name: {profile['display_name']}")
            if 'user_name' in profile:
                logger.info(f"   User: {profile['user_name']}")
            logger.info(f"   Default: {'Yes' if profile.get('is_default') else 'No'}")


def main():
    """CLI for Chrome Profile Manager."""
    import sys
    
    manager = ChromeProfileManager()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "list":
            manager.list_profiles()
        elif command == "select":
            profile_name = sys.argv[2] if len(sys.argv) > 2 else None
            profile = manager.select_profile(profile_name)
            if profile:
                manager.save_profile_config(profile)
                logger.success(f"Profile '{profile['name']}' saved to config")
        elif command == "show":
            config = manager.load_profile_config()
            if config:
                logger.info(f"Current profile: {config.get('selected_profile', {}).get('name', 'None')}")
            else:
                logger.warning("No saved profile configuration")
        else:
            logger.error(f"Unknown command: {command}")
            logger.info("Usage: python chrome_profile_manager.py [list|select [profile_name]|show]")
    else:
        # Interactive mode
        manager.list_profiles()
        logger.info("\nTo save a profile, run: python chrome_profile_manager.py select [profile_name]")


if __name__ == "__main__":
    main()

