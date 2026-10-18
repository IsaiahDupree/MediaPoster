#!/usr/bin/env python3
"""
Full RapidAPI sweep — discovers working endpoints across all subscribed APIs.
Run: python3 scripts/test_all_rapidapi.py
"""
import os, json, asyncio, time
from pathlib import Path
import httpx

# ── env ───────────────────────────────────────────────────────────────────────
for line in Path(__file__).parent.parent.joinpath(".env").read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip())

KEY = os.getenv("RAPIDAPI_KEY")
assert KEY, "RAPIDAPI_KEY not set"

TIMEOUT = 12
RESULTS = []


async def probe(client, label, host, path, params=None, method="GET"):
    url = f"https://{host}{path}"
    hdrs = {"X-RapidAPI-Key": KEY, "X-RapidAPI-Host": host}
    try:
        if method == "POST":
            r = await client.post(url, headers=hdrs, json=params or {}, timeout=TIMEOUT)
        else:
            r = await client.get(url, headers=hdrs, params=params or {}, timeout=TIMEOUT)
        snippet = ""
        try:
            d = r.json()
            if isinstance(d, dict):
                snippet = str(list(d.keys())[:6])
            elif isinstance(d, list):
                snippet = f"list[{len(d)}]"
        except Exception:
            snippet = r.text[:80]
        status_sym = "✅" if r.status_code == 200 else ("⛔" if r.status_code == 403 else "❌")
        row = (status_sym, r.status_code, label, path, snippet)
        RESULTS.append(row)
        print(f"  {status_sym} {r.status_code:3}  {path:<40}  {snippet[:70]}")
        return r.status_code, d if r.status_code == 200 else None
    except Exception as e:
        row = ("💥", "err", label, path, str(e)[:60])
        RESULTS.append(row)
        print(f"  💥 ERR  {path:<40}  {str(e)[:60]}")
        return "err", None


# ══════════════════════════════════════════════════════════════════════════════
# 1. INSTAGRAM LOOTER2 — exhaustive endpoint discovery
# ══════════════════════════════════════════════════════════════════════════════
async def test_instagram_looter2(client):
    HOST = "instagram-looter2.p.rapidapi.com"
    IG_USER = "the_isaiah_dupree"
    IG_REEL_SC = "C3gABC1234xyz"  # placeholder shortcode — real ones found after /profile

    print(f"\n{'='*70}")
    print("INSTAGRAM LOOTER2 — instagram-looter2.p.rapidapi.com")
    print(f"{'='*70}")

    # --- profile first (to get a real shortcode) ---
    status, profile_data = await probe(client, "IG", HOST, "/profile", {"username": IG_USER})
    real_sc = None
    if profile_data:
        edges = profile_data.get("edge_owner_to_timeline_media", {}).get("edges", [])
        for e in edges:
            node = e.get("node", {})
            if node.get("shortcode"):
                real_sc = node["shortcode"]
                break

    # All path patterns to try
    endpoints = [
        # Info / account
        ("GET",  "/v1/info",          {"username_or_id_or_url": IG_USER}),
        ("GET",  "/info",             {"username": IG_USER}),
        ("GET",  "/user",             {"username": IG_USER}),
        # Posts
        ("GET",  "/v1/posts",         {"username_or_id_or_url": IG_USER, "count": 3}),
        ("GET",  "/posts",            {"username": IG_USER, "count": 3}),
        # Reels
        ("GET",  "/v1/reels",         {"username_or_id_or_url": IG_USER, "count": 3}),
        ("GET",  "/reels",            {"username": IG_USER, "count": 3}),
        # Stories
        ("GET",  "/v1/stories",       {"username_or_id_or_url": IG_USER}),
        ("GET",  "/stories",          {"username": IG_USER}),
        # Highlights
        ("GET",  "/v1/highlights",    {"username_or_id_or_url": IG_USER}),
        ("GET",  "/highlights",       {"username": IG_USER}),
        # Feed
        ("GET",  "/feed",             {"username": IG_USER, "count": 3}),
        ("GET",  "/v1/feed",          {"username_or_id_or_url": IG_USER, "count": 3}),
        # Followers / following
        ("GET",  "/followers",        {"username": IG_USER, "count": 5}),
        ("GET",  "/v1/followers",     {"username_or_id_or_url": IG_USER, "count": 5}),
        ("GET",  "/following",        {"username": IG_USER, "count": 5}),
        ("GET",  "/v1/following",     {"username_or_id_or_url": IG_USER, "count": 5}),
        # Search
        ("GET",  "/search",           {"query": "lofi"}),
        ("GET",  "/v1/search",        {"query": "lofi"}),
        # Hashtag
        ("GET",  "/hashtag",          {"hashtag": "lofi"}),
        ("GET",  "/v1/hashtag",       {"hashtag": "lofi"}),
        # Location
        ("GET",  "/location",         {"location_id": "213385402"}),
        # Music / audio (the holy grail)
        ("GET",  "/music",            {"id": "123"}),
        ("GET",  "/audio",            {"id": "123"}),
        ("GET",  "/v1/audio",         {"id": "123"}),
        ("GET",  "/v1/music",         {"music_id": "123"}),
        ("GET",  "/trending",         {}),
        ("GET",  "/v1/trending",      {}),
        ("GET",  "/explore",          {}),
        ("GET",  "/v1/explore",       {}),
    ]

    # Post / reel detail with real shortcode if we got one
    sc = real_sc or "CxYZaBC1234"
    endpoints += [
        ("GET",  "/post",             {"shortcode": sc}),
        ("GET",  "/v1/post",          {"shortcode": sc}),
        ("GET",  "/reel",             {"shortcode": sc}),
        ("GET",  "/v1/reel",          {"shortcode": sc}),
        ("GET",  "/comments",         {"shortcode": sc, "count": 3}),
        ("GET",  "/v1/comments",      {"shortcode": sc, "count": 3}),
        ("GET",  "/likers",           {"shortcode": sc}),
        ("GET",  "/v1/likers",        {"shortcode": sc}),
    ]

    real_sc_found = None
    for method, path, params in endpoints:
        status, data = await probe(client, "IG", HOST, path, params, method)
        if status == 200 and data and path in ("/post", "/v1/post"):
            # try to extract music
            clips = data.get("clips_metadata", {}) or {}
            music = clips.get("music_info", {})
            if music:
                asset = music.get("music_asset_info", {})
                print(f"    🎵 MUSIC FOUND: {asset.get('title')} — {asset.get('display_artist')}")
                dl = asset.get("progressive_download_url", "")
                if dl:
                    print(f"    🎵 DOWNLOAD URL: {dl[:100]}")
        await asyncio.sleep(0.2)


# ══════════════════════════════════════════════════════════════════════════════
# 2. SOUNDCLOUD APIs
# ══════════════════════════════════════════════════════════════════════════════
async def test_soundcloud(client):
    print(f"\n{'='*70}")
    print("SOUNDCLOUD APIs")
    print(f"{'='*70}")

    hosts = [
        "soundcloud-api.p.rapidapi.com",
        "soundcloud-api2.p.rapidapi.com",
        "soundcloud-api3.p.rapidapi.com",
        "soundcloud-scraper.p.rapidapi.com",
        "soundcloud-mp3-downloader-api.p.rapidapi.com",
    ]
    paths = [
        ("/search",           {"q": "lofi chill"}),
        ("/tracks",           {"q": "lofi chill"}),
        ("/v2/search/tracks", {"q": "lofi", "limit": "3"}),
        ("/resolve",          {"url": "https://soundcloud.com/lofi-hip-hop/sets/chillhop"}),
        ("/stream",           {"url": "https://soundcloud.com/lofi-hip-hop/sets/chillhop"}),
        ("/",                 {"url": "https://soundcloud.com/lofi-hip-hop/lofi-relax"}),
    ]

    for host in hosts:
        print(f"\n  HOST: {host}")
        for path, params in paths:
            await probe(client, "SC", host, path, params)
            await asyncio.sleep(0.15)


# ══════════════════════════════════════════════════════════════════════════════
# 3. YOUTUBE MP3 APIs
# ══════════════════════════════════════════════════════════════════════════════
async def test_youtube_mp3(client):
    print(f"\n{'='*70}")
    print("YOUTUBE MP3 APIs")
    print(f"{'='*70}")

    YT_ID = "jfKfPfyJRdk"  # lofi girl stream

    apis = [
        ("youtube-mp3.p.rapidapi.com",            "/dl",     {"id": YT_ID}),
        ("youtube-mp32.p.rapidapi.com",            "/dl",     {"id": YT_ID}),
        ("youtube-mp33.p.rapidapi.com",            "/dl",     {"id": YT_ID}),
        ("youtube-to-mp3.p.rapidapi.com",          "/dl",     {"id": YT_ID}),
        ("youtube-mp3-download.p.rapidapi.com",    "/dl",     {"id": YT_ID}),
        ("youtube-media-downloader.p.rapidapi.com","/v2/video/mp3", {"id": YT_ID}),
        ("youtube-video-to-mp3.p.rapidapi.com",    "/download",{"url": f"https://youtube.com/watch?v={YT_ID}"}),
        ("youtube-video-fast-downloader.p.rapidapi.com", "/dl", {"id": YT_ID}),
        ("youtube-mp36.p.rapidapi.com",            "/dl",     {"id": YT_ID}),
    ]

    for host, path, params in apis:
        await probe(client, "YT-MP3", host, path, params)
        await asyncio.sleep(0.2)


# ══════════════════════════════════════════════════════════════════════════════
# 4. YT-API (for music search → then convert)
# ══════════════════════════════════════════════════════════════════════════════
async def test_yt_api(client):
    print(f"\n{'='*70}")
    print("YT-API (yt-api.p.rapidapi.com)")
    print(f"{'='*70}")

    HOST = "yt-api.p.rapidapi.com"
    endpoints = [
        ("/search",   {"q": "lofi chill no copyright", "hl": "en", "gl": "US"}),
        ("/trending", {"hl": "en", "gl": "US", "type": "music"}),
        ("/home",     {"hl": "en"}),
    ]
    for path, params in endpoints:
        await probe(client, "YT", HOST, path, params)
        await asyncio.sleep(0.2)


# ══════════════════════════════════════════════════════════════════════════════
# 5. TWITTER
# ══════════════════════════════════════════════════════════════════════════════
async def test_twitter(client):
    print(f"\n{'='*70}")
    print("TWITTER — twitter-api45.p.rapidapi.com")
    print(f"{'='*70}")

    HOST = "twitter-api45.p.rapidapi.com"
    endpoints = [
        ("/user",           {"screenname": "IsaiahDupree7"}),
        ("/timeline",       {"user_id": "1234"}),
        ("/search",         {"query": "lofi", "count": "3"}),
        ("/tweet",          {"tweet_id": "1234567890"}),
        ("/followers",      {"user_id": "1234"}),
        ("/following",      {"user_id": "1234"}),
    ]
    for path, params in endpoints:
        await probe(client, "TW", HOST, path, params)
        await asyncio.sleep(0.2)


# ══════════════════════════════════════════════════════════════════════════════
# 6. TIKTOK ADDITIONAL APIs
# ══════════════════════════════════════════════════════════════════════════════
async def test_tiktok_extras(client):
    print(f"\n{'='*70}")
    print("TIKTOK EXTRAS")
    print(f"{'='*70}")

    apis = [
        ("tiktok-video-no-watermark.p.rapidapi.com", "/", {"url": "https://www.tiktok.com/@tiktok/video/123"}),
        ("tiktok-scraper.p.rapidapi.com", "/user/posts", {"unique_id": "tiktok", "count": "3"}),
        ("tiktok-api.p.rapidapi.com",     "/user/info",  {"username": "tiktok"}),
        ("tiktok-api2.p.rapidapi.com",    "/user/info",  {"username": "tiktok"}),
        ("tiktok-video-feature-summary.p.rapidapi.com", "/user/posts", {"unique_id": "tiktok", "count": "3"}),
    ]
    for host, path, params in apis:
        await probe(client, "TT", host, path, params)
        await asyncio.sleep(0.2)


# ══════════════════════════════════════════════════════════════════════════════
# 7. INSTAGRAM STATISTICS
# ══════════════════════════════════════════════════════════════════════════════
async def test_ig_stats(client):
    print(f"\n{'='*70}")
    print("INSTAGRAM STATISTICS — instagram-statistics-api.p.rapidapi.com")
    print(f"{'='*70}")

    HOST = "instagram-statistics-api.p.rapidapi.com"
    endpoints = [
        ("/community", {"url": "https://www.instagram.com/the_isaiah_dupree/"}),
        ("/posts",     {"url": "https://www.instagram.com/the_isaiah_dupree/"}),
        ("/reel",      {"url": "https://www.instagram.com/the_isaiah_dupree/"}),
    ]
    for path, params in endpoints:
        await probe(client, "IGS", HOST, path, params)
        await asyncio.sleep(0.2)


# ══════════════════════════════════════════════════════════════════════════════
# 8. DEEZER (already confirmed working — spot-check)
# ══════════════════════════════════════════════════════════════════════════════
async def test_deezer(client):
    print(f"\n{'='*70}")
    print("DEEZER — deezerdevs-deezer.p.rapidapi.com")
    print(f"{'='*70}")

    HOST = "deezerdevs-deezer.p.rapidapi.com"
    endpoints = [
        ("/search",         {"q": "lofi chill"}),
        ("/chart",          {}),
        ("/chart/0/tracks", {}),
        ("/radio",          {}),
        ("/genre",          {}),
    ]
    for path, params in endpoints:
        await probe(client, "DZ", HOST, path, params)
        await asyncio.sleep(0.2)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
async def main():
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        await test_instagram_looter2(client)
        await test_soundcloud(client)
        await test_youtube_mp3(client)
        await test_yt_api(client)
        await test_twitter(client)
        await test_tiktok_extras(client)
        await test_ig_stats(client)
        await test_deezer(client)

    # ── summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    working   = [r for r in RESULTS if r[0] == "✅"]
    forbidden = [r for r in RESULTS if r[0] == "⛔"]
    failed    = [r for r in RESULTS if r[0] == "❌"]

    print(f"\n✅ WORKING ({len(working)}):")
    for _, code, label, path, snippet in working:
        print(f"   [{label}] {path:<40}  {snippet[:60]}")

    print(f"\n⛔ NOT SUBSCRIBED ({len(forbidden)}):")
    for _, code, label, path, snippet in forbidden:
        print(f"   [{label}] {path}")

    print(f"\n❌ FAILED/404 ({len(failed)}):")
    for _, code, label, path, snippet in failed:
        print(f"   [{label}] {code} {path}")

    # Save full results
    out = Path("data/rapidapi_sweep_results.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps([
        {"sym": r[0], "status": r[1], "api": r[2], "path": r[3], "response": r[4]}
        for r in RESULTS
    ], indent=2))
    print(f"\nFull results → {out}")


if __name__ == "__main__":
    asyncio.run(main())
