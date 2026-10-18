"""
Quick test of TikTok trending sounds and Instagram music via RapidAPI.
Run: python3 scripts/test_music_rapidapi.py
"""
import os
import sys
import json
import requests
from pathlib import Path

# Load .env manually
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
if not RAPIDAPI_KEY:
    print("ERROR: RAPIDAPI_KEY not found in .env")
    sys.exit(1)

print(f"Using RAPIDAPI_KEY: {RAPIDAPI_KEY[:12]}...")
print("=" * 60)


def test(label, url, host, params=None):
    """Make a RapidAPI request and print result."""
    print(f"\n>>> {label}")
    print(f"    URL: {url}")
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": host,
    }
    try:
        r = requests.get(url, headers=headers, params=params or {}, timeout=15)
        print(f"    Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            # Print first item or keys to show structure
            if isinstance(data, list):
                print(f"    Items: {len(data)}")
                if data:
                    print(f"    First item keys: {list(data[0].keys()) if isinstance(data[0], dict) else data[0]}")
            elif isinstance(data, dict):
                print(f"    Top-level keys: {list(data.keys())}")
                # Try to find music/audio items
                for key in ["data", "result", "audio", "sounds", "music", "tracks", "results", "items"]:
                    if key in data:
                        val = data[key]
                        if isinstance(val, list):
                            print(f"    data['{key}']: {len(val)} items")
                            if val and isinstance(val[0], dict):
                                print(f"    First item keys: {list(val[0].keys())[:10]}")
                                print(f"    First item sample: {json.dumps(val[0], indent=2)[:400]}")
                            break
        else:
            print(f"    Response: {r.text[:300]}")
    except Exception as e:
        print(f"    ERROR: {e}")


# ── 1. Deezer deep-dive ───────────────────────────────────────────────────────
HOST_DZ = "deezerdevs-deezer.p.rapidapi.com"

print("\n>>> DEEZER – full track structure (lofi search)")
r = requests.get(
    f"https://{HOST_DZ}/search",
    headers={"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": HOST_DZ},
    params={"q": "lofi chill", "limit": "3"},
    timeout=15,
)
print(f"    Status: {r.status_code}")
data = r.json()
for track in data.get("data", [])[:3]:
    print(f"\n    Title:    {track.get('title')}")
    print(f"    Artist:   {track.get('artist', {}).get('name')}")
    print(f"    Duration: {track.get('duration')}s")
    print(f"    Preview:  {track.get('preview')}")
    print(f"    Link:     {track.get('link')}")
    print(f"    Album:    {track.get('album', {}).get('title')}")
    print(f"    Explicit: {track.get('explicit_lyrics')}")

print("\n>>> DEEZER – genre/mood searches")
for mood_q in ["upbeat motivational", "dramatic cinematic", "calm ambient", "energetic workout"]:
    r2 = requests.get(
        f"https://{HOST_DZ}/search",
        headers={"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": HOST_DZ},
        params={"q": mood_q, "limit": "2"},
        timeout=15,
    )
    tracks = r2.json().get("data", [])
    print(f"    [{mood_q}] → {len(tracks)} results, e.g.: {tracks[0].get('title') if tracks else 'none'}")

# ── 2. TikTok scraper7 music/posts – full response ───────────────────────────
HOST7 = "tiktok-scraper7.p.rapidapi.com"
print("\n>>> TIKTOK-SCRAPER7 – music/posts full response")
r3 = requests.get(
    f"https://{HOST7}/music/posts",
    headers={"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": HOST7},
    params={"music_id": "6829574271011089158", "count": "3"},
    timeout=15,
)
print(f"    Status: {r3.status_code}")
print(f"    Full response: {json.dumps(r3.json(), indent=2)[:600]}")

# ── 3. TikTok user/posts – check music field on each post ────────────────────
print("\n>>> TIKTOK-SCRAPER7 – user/posts, extracting music from each post")
r4 = requests.get(
    f"https://{HOST7}/user/posts",
    headers={"X-RapidAPI-Key": RAPIDAPI_KEY, "X-RapidAPI-Host": HOST7},
    params={"unique_id": "the_isaiah_dupree", "count": "3"},
    timeout=15,
)
r4_data = r4.json()
print(f"    Full keys: {list(r4_data.keys())}")
posts = r4_data.get("data", {}).get("videos", []) or r4_data.get("msg", {}).get("videos", []) or []
if isinstance(r4_data.get("data"), list):
    posts = r4_data["data"]
print(f"    Full response snippet: {json.dumps(r4_data, indent=2)[:600]}")

print("\n" + "=" * 60)
print("Summary:")
print("  ✅ Deezer: works, has preview URLs, full metadata, no extra subscription needed")
print("  ❓ TikTok music/posts: 200 but check 'msg' field above for actual structure")
