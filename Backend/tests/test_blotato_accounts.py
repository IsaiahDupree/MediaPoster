"""
Blotato Account Identification Tests
=====================================
Comprehensive tests to verify and identify Blotato account mappings.

Run with: python -m pytest tests/test_blotato_accounts.py -v
Or standalone: python tests/test_blotato_accounts.py
"""

import asyncio
import httpx
import os
import sys
from typing import Dict, List, Optional
from datetime import datetime

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Blotato API configuration
BLOTATO_API_KEY = os.getenv("BLOTATO_API_KEY", "")
BLOTATO_BASE_URL = "https://api.blotato.com/v2"
LOCAL_API_URL = "http://localhost:5555"


# Known account mappings from Blotato dashboard
KNOWN_ACCOUNTS = {
    # TikTok
    710: {"platform": "tiktok", "username": "isaiah_dupree"},
    243: {"platform": "tiktok", "username": "the_isaiah_dupree"},
    4508: {"platform": "tiktok", "username": "dupree_isaiah"},
    571: {"platform": "tiktok", "username": "soursides_is_sour"},
    
    # Instagram
    807: {"platform": "instagram", "username": "the_isaiah_dupree"},
    670: {"platform": "instagram", "username": "the_isaiah_dupree_"},
    1369: {"platform": "instagram", "username": "dupree_isaiah_"},
    
    # YouTube
    228: {"platform": "youtube", "username": "UCnDBsELI2OlaEl5yxA77HNA"},
    3370: {"platform": "youtube", "username": "lofi_creator"},
    
    # Twitter
    4151: {"platform": "twitter", "username": "IsaiahDupree7"},
    
    # Threads
    173: {"platform": "threads", "username": "the_isaiah_dupree_"},
    201: {"platform": "threads", "username": "the_isaiah_dupree"},
    4150: {"platform": "threads", "username": "isaiahdupree75"},
    
    # Pinterest
    # 173: also pinterest/isaiahdupree33
    # 243: also pinterest/isaiahdupree75
    
    # LinkedIn
    # 571: also linkedin/IsaiahDupree7
    
    # Facebook
    786: {"platform": "facebook", "username": "Isaiah Dupree"},
    
    # Bluesky
    # 201: also bluesky/the_isaiah_dupree_
}


class BlotatoAccountTester:
    """Test Blotato account identification and connectivity"""
    
    def __init__(self):
        self.api_key = BLOTATO_API_KEY
        self.results: List[Dict] = []
    
    async def test_local_accounts_endpoint(self) -> Dict:
        """Test local /api/blotato/accounts endpoint"""
        print("\n" + "="*60)
        print("TEST: Local Accounts Endpoint")
        print("="*60)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{LOCAL_API_URL}/api/blotato/accounts", timeout=10)
                
                if response.status_code == 200:
                    accounts = response.json()
                    print(f"✅ Found {len(accounts)} accounts from local API")
                    
                    # Group by platform
                    by_platform: Dict[str, List] = {}
                    for acc in accounts:
                        platform = acc.get("platform", "unknown")
                        if platform not in by_platform:
                            by_platform[platform] = []
                        by_platform[platform].append(acc)
                    
                    print("\nAccounts by platform:")
                    for platform, accs in sorted(by_platform.items()):
                        print(f"\n  {platform.upper()} ({len(accs)}):")
                        for acc in accs:
                            print(f"    ID {acc['id']:>4}: @{acc['username']}")
                    
                    return {"success": True, "accounts": accounts, "count": len(accounts)}
                else:
                    print(f"❌ Failed: HTTP {response.status_code}")
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            print(f"❌ Error: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_blotato_api_accounts(self) -> Dict:
        """Test Blotato API directly to get account list"""
        print("\n" + "="*60)
        print("TEST: Blotato API Direct - Get Accounts")
        print("="*60)
        
        if not self.api_key:
            print("⚠️  BLOTATO_API_KEY not set - skipping direct API test")
            return {"success": False, "error": "No API key"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{BLOTATO_BASE_URL}/accounts",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    accounts = data if isinstance(data, list) else data.get("accounts", [])
                    
                    print(f"✅ Blotato API returned {len(accounts)} accounts")
                    
                    for acc in accounts:
                        acc_id = acc.get("id") or acc.get("account_id")
                        platform = acc.get("platform") or acc.get("provider")
                        username = acc.get("username") or acc.get("handle") or acc.get("name")
                        print(f"  ID {acc_id}: {platform} / @{username}")
                    
                    return {"success": True, "accounts": accounts}
                else:
                    print(f"❌ Blotato API error: HTTP {response.status_code}")
                    print(f"   Response: {response.text[:200]}")
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            print(f"❌ Error calling Blotato API: {e}")
            return {"success": False, "error": str(e)}
    
    async def test_account_mapping_consistency(self) -> Dict:
        """Test that local mappings match what Blotato returns"""
        print("\n" + "="*60)
        print("TEST: Account Mapping Consistency")
        print("="*60)
        
        local_result = await self.test_local_accounts_endpoint()
        if not local_result.get("success"):
            return {"success": False, "error": "Could not fetch local accounts"}
        
        local_accounts = local_result.get("accounts", [])
        
        # Verify against known mappings
        mismatches = []
        for acc in local_accounts:
            acc_id = acc.get("id")
            if acc_id in KNOWN_ACCOUNTS:
                known = KNOWN_ACCOUNTS[acc_id]
                if acc.get("platform") != known["platform"]:
                    mismatches.append({
                        "id": acc_id,
                        "expected_platform": known["platform"],
                        "actual_platform": acc.get("platform")
                    })
        
        if mismatches:
            print(f"⚠️  Found {len(mismatches)} platform mismatches:")
            for m in mismatches:
                print(f"   ID {m['id']}: expected {m['expected_platform']}, got {m['actual_platform']}")
        else:
            print("✅ All account mappings are consistent")
        
        return {"success": len(mismatches) == 0, "mismatches": mismatches}
    
    async def test_platform_counts(self) -> Dict:
        """Test that we have expected number of accounts per platform"""
        print("\n" + "="*60)
        print("TEST: Platform Account Counts")
        print("="*60)
        
        expected = {
            "tiktok": 4,
            "instagram": 4,
            "youtube": 2,
            "twitter": 1,
            "threads": 4,
            "pinterest": 2,
            "linkedin": 1,
            "facebook": 1,
            "bluesky": 1,
        }
        
        local_result = await self.test_local_accounts_endpoint()
        if not local_result.get("success"):
            return {"success": False, "error": "Could not fetch accounts"}
        
        accounts = local_result.get("accounts", [])
        
        # Count by platform
        counts: Dict[str, int] = {}
        for acc in accounts:
            platform = acc.get("platform", "unknown").lower()
            counts[platform] = counts.get(platform, 0) + 1
        
        print("\nPlatform counts (actual vs expected):")
        all_match = True
        for platform, expected_count in expected.items():
            actual = counts.get(platform, 0)
            status = "✅" if actual >= expected_count else "❌"
            print(f"  {status} {platform}: {actual}/{expected_count}")
            if actual < expected_count:
                all_match = False
        
        return {"success": all_match, "counts": counts, "expected": expected}
    
    async def test_username_matching(self) -> Dict:
        """Test that username matching works correctly"""
        print("\n" + "="*60)
        print("TEST: Username Matching Logic")
        print("="*60)
        
        test_cases = [
            ("tiktok", "@isaiah_dupree", 710),
            ("tiktok", "isaiah_dupree", 710),
            ("tiktok", "ISAIAH_DUPREE", 710),
            ("instagram", "@the_isaiah_dupree", 807),
            ("instagram", "the_isaiah_dupree_", 670),
            ("youtube", "lofi_creator", 3370),
            ("twitter", "IsaiahDupree7", 4151),
        ]
        
        def normalize(username: str) -> str:
            return (username or "").lower().strip().lstrip("@").rstrip("_")
        
        local_result = await self.test_local_accounts_endpoint()
        if not local_result.get("success"):
            return {"success": False, "error": "Could not fetch accounts"}
        
        accounts = local_result.get("accounts", [])
        
        results = []
        for platform, username, expected_id in test_cases:
            normalized = normalize(username)
            
            # Find matching account
            found = None
            for acc in accounts:
                if acc.get("platform", "").lower() != platform.lower():
                    continue
                acc_username = normalize(acc.get("username", ""))
                if acc_username == normalized or normalized in acc_username or acc_username in normalized:
                    found = acc
                    break
            
            if found and found.get("id") == expected_id:
                status = "✅"
                success = True
            elif found:
                status = f"⚠️ (found ID {found.get('id')}, expected {expected_id})"
                success = False
            else:
                status = "❌ (not found)"
                success = False
            
            print(f"  {status} {platform}/@{username} -> ID {expected_id}")
            results.append({"platform": platform, "username": username, "expected": expected_id, "success": success})
        
        all_passed = all(r["success"] for r in results)
        return {"success": all_passed, "results": results}
    
    async def run_all_tests(self) -> Dict:
        """Run all tests and generate report"""
        print("\n" + "="*60)
        print("BLOTATO ACCOUNT IDENTIFICATION TESTS")
        print("="*60)
        print(f"Started: {datetime.now().isoformat()}")
        
        results = {
            "local_endpoint": await self.test_local_accounts_endpoint(),
            "blotato_api": await self.test_blotato_api_accounts(),
            "mapping_consistency": await self.test_account_mapping_consistency(),
            "platform_counts": await self.test_platform_counts(),
            "username_matching": await self.test_username_matching(),
        }
        
        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in results.values() if r.get("success"))
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result.get("success") else "❌ FAIL"
            print(f"  {status}: {test_name}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        return {
            "passed": passed,
            "total": total,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }


def print_account_reference():
    """Print a reference table of all known accounts"""
    print("\n" + "="*60)
    print("BLOTATO ACCOUNT REFERENCE")
    print("="*60)
    print("\nCopy these IDs when needed:\n")
    
    accounts_by_platform = {}
    for acc_id, info in sorted(KNOWN_ACCOUNTS.items()):
        platform = info["platform"]
        if platform not in accounts_by_platform:
            accounts_by_platform[platform] = []
        accounts_by_platform[platform].append((acc_id, info["username"]))
    
    for platform in ["tiktok", "instagram", "youtube", "twitter", "threads", "pinterest", "linkedin", "facebook", "bluesky"]:
        if platform in accounts_by_platform:
            print(f"{platform.upper()}:")
            for acc_id, username in accounts_by_platform[platform]:
                print(f"  {acc_id:>5} = @{username}")
            print()


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Blotato Account Tests")
    parser.add_argument("--reference", action="store_true", help="Print account reference only")
    parser.add_argument("--test", type=str, help="Run specific test (local, api, consistency, counts, matching)")
    args = parser.parse_args()
    
    if args.reference:
        print_account_reference()
        return
    
    tester = BlotatoAccountTester()
    
    if args.test:
        test_map = {
            "local": tester.test_local_accounts_endpoint,
            "api": tester.test_blotato_api_accounts,
            "consistency": tester.test_account_mapping_consistency,
            "counts": tester.test_platform_counts,
            "matching": tester.test_username_matching,
        }
        if args.test in test_map:
            await test_map[args.test]()
        else:
            print(f"Unknown test: {args.test}")
            print(f"Available: {', '.join(test_map.keys())}")
    else:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
