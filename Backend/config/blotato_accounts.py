"""
Blotato Account Mapping Configuration

Maps MediaPoster usernames to Blotato account IDs for posting.
These IDs come from the Blotato dashboard at https://app.blotato.com/settings/accounts

To update: Copy the Account ID from Blotato's "Copy Account ID" button for each account.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger


@dataclass
class BlotatoAccount:
    """Represents a connected Blotato account"""
    blotato_id: int
    platform: str
    username: str
    display_name: Optional[str] = None
    is_active: bool = True


# Master list of Blotato accounts with their IDs
# Format: BlotatoAccount(blotato_id, platform, username, display_name)
# Source: Blotato dashboard at https://app.blotato.com/settings/accounts
BLOTATO_ACCOUNTS: List[BlotatoAccount] = [
    # TikTok accounts (3)
    BlotatoAccount(710, "tiktok", "isaiah_dupree", "Isaiah Dupree"),
    BlotatoAccount(243, "tiktok", "the_isaiah_dupree", "The Isaiah Dupree"),
    BlotatoAccount(4508, "tiktok", "dupree_isaiah", "Dupree Isaiah"),
    
    # Instagram accounts (4)
    BlotatoAccount(807, "instagram", "the_isaiah_dupree", "The Isaiah Dupree"),
    BlotatoAccount(670, "instagram", "the_isaiah_dupree_", "The Isaiah Dupree"),
    BlotatoAccount(1369, "instagram", "dupree_isaiah_", "Dupree Isaiah"),  # Note: This might be Threads per memory
    BlotatoAccount(4508, "instagram", "dupree_isaiah", "Dupree Isaiah"),  # Same ID as TikTok - verify
    
    # YouTube accounts (2)
    BlotatoAccount(228, "youtube", "UCnDBsELI2OlaEl5yxA77HNA", "Isaiah Dupree"),
    BlotatoAccount(3370, "youtube", "lofi_creator", "lofi creator"),
    
    # Twitter/X accounts (1)
    BlotatoAccount(4151, "twitter", "soursides_is_sour", "Soursides"),
    
    # Threads accounts (2)
    BlotatoAccount(1369, "threads", "dupree_isaiah_", "Dupree Isaiah"),
    BlotatoAccount(4150, "threads", "isaiahdupree75", "Isaiah Dupree"),
    
    # Pinterest accounts (2)
    BlotatoAccount(173, "pinterest", "isaiahdupree33", "Isaiah Dupree"),
    BlotatoAccount(243, "pinterest", "isaiahdupree75", "Isaiah Dupree"),  # Note: Same ID as TikTok - verify
    
    # LinkedIn accounts (1)
    BlotatoAccount(571, "linkedin", "IsaiahDupree7", "Isaiah Dupree"),
    
    # Facebook accounts (1)
    BlotatoAccount(786, "facebook", "Isaiah Dupree", "Isaiah Dupree"),
    
    # Bluesky accounts (1)
    BlotatoAccount(201, "bluesky", "the_isaiah_dupree_", "The Isaiah Dupree"),
]


# Quick lookup by username (case-insensitive, strips @ symbol)
def normalize_username(username: str) -> str:
    """Normalize username for matching"""
    return username.lower().strip().lstrip('@').replace(' ', '_')


def get_blotato_id(platform: str, username: str) -> Optional[int]:
    """Get Blotato account ID for a given platform and username"""
    normalized = normalize_username(username)
    platform_lower = platform.lower()
    
    for account in BLOTATO_ACCOUNTS:
        if account.platform.lower() == platform_lower:
            if normalize_username(account.username) == normalized:
                return account.blotato_id
    
    logger.warning(f"No Blotato ID found for {platform}/@{username}")
    return None


def get_blotato_account(platform: str, username: str) -> Optional[BlotatoAccount]:
    """Get full Blotato account info for a given platform and username"""
    normalized = normalize_username(username)
    platform_lower = platform.lower()
    
    for account in BLOTATO_ACCOUNTS:
        if account.platform.lower() == platform_lower:
            if normalize_username(account.username) == normalized:
                return account
    
    return None


def get_all_accounts_for_platform(platform: str) -> List[BlotatoAccount]:
    """Get all Blotato accounts for a given platform"""
    platform_lower = platform.lower()
    return [a for a in BLOTATO_ACCOUNTS if a.platform.lower() == platform_lower and a.is_active]


def get_account_by_blotato_id(blotato_id: int) -> Optional[BlotatoAccount]:
    """Get account by Blotato ID"""
    for account in BLOTATO_ACCOUNTS:
        if account.blotato_id == blotato_id:
            return account
    return None


# Username to Blotato ID mapping (for quick lookups)
# This is auto-generated from BLOTATO_ACCOUNTS
USERNAME_TO_BLOTATO_ID: Dict[str, int] = {}
for account in BLOTATO_ACCOUNTS:
    if account.blotato_id:
        key = f"{account.platform.lower()}:{normalize_username(account.username)}"
        USERNAME_TO_BLOTATO_ID[key] = account.blotato_id


def lookup_blotato_id(platform: str, username: str) -> Optional[int]:
    """Fast lookup of Blotato ID using the mapping dict"""
    key = f"{platform.lower()}:{normalize_username(username)}"
    return USERNAME_TO_BLOTATO_ID.get(key)


# Print mapping for debugging
if __name__ == "__main__":
    print("=== Blotato Account Mapping ===")
    print(f"Total accounts: {len(BLOTATO_ACCOUNTS)}")
    print()
    
    for platform in ["tiktok", "instagram", "youtube", "twitter", "threads", "pinterest"]:
        accounts = get_all_accounts_for_platform(platform)
        print(f"{platform.upper()} ({len(accounts)} accounts):")
        for a in accounts:
            print(f"  {a.blotato_id}: @{a.username}")
        print()
