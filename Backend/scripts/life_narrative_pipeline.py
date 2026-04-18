#!/usr/bin/env python3
"""
Life Narrative Pipeline
=======================
Analyzes Isaiah's published YouTube videos + an inspirational playlist
to define the narrative arc and guiding storyline of his life.

Steps:
  1. Pull unique video IDs from youtube_video_stats (own videos)
  2. Fetch transcripts via youtube_transcript_api (no video download)
  3. Claude AI analysis: themes, emotional journey, FATE, values, narrative
  4. Store in yt_own_video_analysis
  5. Pull all videos from the inspirational playlist via YouTube Data API
  6. Fetch transcripts + metadata for each
  7. Claude AI analysis
  8. Store in yt_inspiration_analysis
  9. Final synthesis comparing both datasets → life_narrative_synthesis

Usage:
  cd /Users/isaiahdupree/Documents/Software/MediaPoster/Backend
  source venv/bin/activate
  python scripts/life_narrative_pipeline.py
"""

import os
import sys
import json
import time
import requests
import traceback
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

# Load env from Backend/.env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled, CouldNotRetrieveTranscript
import anthropic
from supabase import create_client

# ─── Config ────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ["SUPABASE_KEY"]
YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
PLAYLIST_ID = "PLL7TyPlRkPShX1uKR70PovVPBt-IpbKRs"
CLAUDE_MODEL = "claude-sonnet-4-6"

db = create_client(SUPABASE_URL, SUPABASE_KEY)
ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=60.0)

# Sora AI-generated video slugs — no dialogue, skip transcript
SORA_TITLES = {"badass", "sora", "wingsuit", "dinosaur", "urban surf"}


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


# ─── Transcript ────────────────────────────────────────────────────────────

_yt_api = YouTubeTranscriptApi()

def get_transcript(video_id: str) -> tuple[str, list[dict], bool]:
    """Returns (full_text, segments_as_dicts, has_transcript). Uses v1.x API."""
    try:
        fetched = _yt_api.fetch(video_id, languages=["en", "en-US", "en-GB"])
        segments = [{"text": s.text, "start": s.start, "duration": s.duration} for s in fetched]
        full_text = " ".join(s["text"] for s in segments)
        return full_text, segments, True
    except (NoTranscriptFound, TranscriptsDisabled, CouldNotRetrieveTranscript):
        return "", [], False
    except Exception as e:
        # Try without language filter as fallback
        try:
            fetched = _yt_api.fetch(video_id)
            segments = [{"text": s.text, "start": s.start, "duration": s.duration} for s in fetched]
            full_text = " ".join(s["text"] for s in segments)
            return full_text, segments, True
        except Exception:
            return "", [], False


# ─── Claude Analysis ────────────────────────────────────────────────────────

def analyze_own_video(video_id: str, title: str, transcript: str) -> dict:
    """Analyze Isaiah's own video. Returns structured dict."""
    prompt = f"""You are analyzing a YouTube video by Isaiah Dupree — a software founder and AI automation entrepreneur building toward $5K/month.

VIDEO: "{title}"
VIDEO ID: {video_id}

TRANSCRIPT:
{transcript[:8000]}

Analyze this video deeply and return a JSON object with exactly these keys:

{{
  "themes": ["list", "of", "main", "topics"],
  "emotional_journey": {{
    "opening": "how it starts emotionally",
    "middle": "how it develops",
    "close": "how it ends / what feeling is left",
    "arc_type": "hero_journey|problem_solution|revelation|motivation|story"
  }},
  "fate_scores": {{
    "fear": 0.0,
    "authority": 0.0,
    "trust": 0.0,
    "excitement": 0.0
  }},
  "values_expressed": ["values", "the", "creator", "demonstrates"],
  "narrative_patterns": ["recurring", "storytelling", "structures"],
  "key_insights": ["main", "takeaways", "from", "this", "video"],
  "hook": "the opening hook line or concept",
  "storytelling_style": "conversational|educational|inspirational|documentary|raw",
  "personal_brand_signals": {{
    "identity": "how he positions himself",
    "audience": "who he's speaking to",
    "promise": "what transformation he offers",
    "differentiator": "what makes him unique"
  }},
  "content_category": "business|tech|mindset|automation|marketing|personal|tutorial",
  "narrative_summary": "2-3 sentences capturing what this video is really about at a deeper level beyond the surface topic"
}}

Return ONLY valid JSON. No markdown, no explanation."""

    try:
        text = claude_call(prompt, max_tokens=1500)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        log(f"  Claude analysis failed for {video_id}: {e}")
        return {}


def claude_call(prompt: str, max_tokens: int = 600, retries: int = 3) -> str:
    """Call Claude with retry on timeout."""
    for attempt in range(retries):
        try:
            resp = ai.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return resp.content[0].text.strip()
        except Exception as e:
            if attempt < retries - 1:
                wait = 10 * (attempt + 1)
                log(f"    Claude error (attempt {attempt+1}): {e} — retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise
    return ""


def analyze_inspiration_video_metadata(video_id: str, title: str, channel: str, description: str) -> dict:
    """Analyze an inspirational video from title + description alone (no transcript)."""
    prompt = f"""You are analyzing a YouTube video from Isaiah Dupree's inspirational playlist based on its title and description.
Isaiah is a software founder building AI automation systems, working toward $5K/month revenue.

VIDEO TITLE: "{title}"
CHANNEL: {channel}
DESCRIPTION: {description[:1000] if description else '(no description)'}

Based ONLY on the title, channel name, and description, infer the likely themes and what Isaiah might find inspiring about this video.

Return a JSON object with exactly these keys:

{{
  "themes": ["inferred", "main", "topics"],
  "values_expressed": ["likely", "values", "in", "this", "content"],
  "key_lessons": ["what", "Isaiah", "might", "absorb"],
  "why_inspiring": "why this type of content would appeal to someone building AI automation businesses",
  "content_category": "business|tech|mindset|automation|marketing|personal|tutorial|philosophy",
  "narrative_summary": "1-2 sentences on what this video is likely about and why Isaiah saved it"
}}

Return ONLY valid JSON. No markdown, no explanation."""

    try:
        text = claude_call(prompt, max_tokens=600)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        return {}


def analyze_inspiration_video(video_id: str, title: str, channel: str, transcript: str, description: str) -> dict:
    """Analyze an inspirational playlist video."""
    prompt = f"""You are analyzing a YouTube video from Isaiah Dupree's inspirational playlist — videos he finds meaningful and aspirational.

VIDEO: "{title}"
CHANNEL: {channel}
VIDEO ID: {video_id}
DESCRIPTION EXCERPT: {description[:500]}

TRANSCRIPT:
{transcript[:8000]}

Analyze this video and return a JSON object with exactly these keys:

{{
  "themes": ["list", "of", "main", "topics"],
  "emotional_journey": {{
    "opening": "how it starts emotionally",
    "middle": "how it develops",
    "close": "how it ends / what feeling is left",
    "arc_type": "hero_journey|problem_solution|revelation|motivation|story"
  }},
  "fate_scores": {{
    "fear": 0.0,
    "authority": 0.0,
    "trust": 0.0,
    "excitement": 0.0
  }},
  "values_expressed": ["values", "demonstrated", "in", "this", "video"],
  "key_lessons": ["what", "Isaiah", "can", "absorb", "from", "this"],
  "why_inspiring": "what specifically makes this video likely to inspire someone building an online business and AI systems",
  "narrative_style": "conversational|educational|inspirational|documentary|raw|motivational",
  "speaker_identity": "how the speaker positions themselves and their authority",
  "content_category": "business|tech|mindset|automation|marketing|personal|tutorial|philosophy",
  "narrative_summary": "2-3 sentences on what this video is really about at a deeper level"
}}

Return ONLY valid JSON. No markdown, no explanation."""

    try:
        text = claude_call(prompt, max_tokens=1500)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        log(f"  Claude analysis failed for {video_id}: {e}")
        return {}


def synthesize_narrative(own_videos: list[dict], inspiration_videos: list[dict]) -> dict:
    """Final Claude synthesis — define the life narrative."""
    own_summaries = []
    for v in own_videos:
        a = v.get("ai_analysis", {})
        if a:
            own_summaries.append(f"- \"{v['title']}\": themes={a.get('themes', [])}, values={a.get('values_expressed', [])}, summary={a.get('narrative_summary', '')}")

    insp_summaries = []
    for v in inspiration_videos:
        a = v.get("ai_analysis", {})
        if a:
            src = "transcript" if v.get("has_transcript") else "metadata"
            insp_summaries.append(f"- \"{v['title']}\" by {v.get('channel_name', '')} [{src}]: themes={a.get('themes', [])}, lessons={a.get('key_lessons', [])}, why_inspiring={a.get('why_inspiring', '')}")

    prompt = f"""You are a narrative architect helping Isaiah Dupree understand the guiding storyline of his life.

Isaiah is a software founder building AI automation systems, working toward $5K/month revenue, creating content about business, AI, and online entrepreneurship.

HIS PUBLISHED YOUTUBE VIDEOS ({len(own_summaries)} analyzed):
{chr(10).join(own_summaries[:20])}

HIS INSPIRATIONAL PLAYLIST ({len(insp_summaries)} analyzed):
{chr(10).join(insp_summaries[:20])}

Based on what he creates AND what he's drawn to, synthesize the deep narrative of his life.

Return a JSON object with exactly these keys:

{{
  "guiding_storyline": "A vivid 2-3 paragraph narrative that captures the arc of Isaiah's life story — who he is, the journey he's on, and where it's all pointing. Write it as a compelling story, not a list.",
  "narrative_arc": "The mythic/story structure his life follows (e.g. 'The Builder's Journey', 'The Reluctant Visionary', 'The Sovereign Creator')",
  "life_chapter": "What chapter/phase he's currently in — name it evocatively",
  "recurring_themes": ["themes", "that", "appear", "across", "both", "his", "content", "and", "his", "inspirations"],
  "core_values": ["distilled", "values", "driving", "everything"],
  "dominant_emotions": ["emotional", "signature", "of", "his", "work"],
  "identity_patterns": {{
    "who_he_is": "based on what he creates",
    "how_he_sees_himself": "the identity he projects",
    "his_gift": "what he uniquely brings to the world"
  }},
  "aspiration_patterns": {{
    "who_he_wants_to_become": "based on what inspires him",
    "the_version_he_is_becoming": "the upgraded identity emerging",
    "what_he_hungers_for": "the deeper need driving the inspiration"
  }},
  "alignment_score": 0.0,
  "alignment_summary": "How aligned are his current creations with his deepest inspirations? What's the gap?",
  "gaps": ["things", "his", "inspiration", "shows", "that", "his", "content", "doesn't", "yet", "express"],
  "emerging_themes": ["themes", "in", "inspiration", "not", "yet", "in", "his", "own", "content"],
  "narrative_voice": "The voice/tone that is distinctly Isaiah's",
  "content_superpower": "The one thing he does that no one else does quite the same way",
  "north_star": "A single sentence: the destination all of this is pointing toward",
  "recommendations": ["3-5", "specific", "things", "to", "lean", "into", "based", "on", "this", "analysis"]
}}

Return ONLY valid JSON. No markdown, no explanation."""

    try:
        text = claude_call(prompt, max_tokens=3000)
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except Exception as e:
        log(f"  Synthesis failed: {e}")
        traceback.print_exc()
        return {}


# ─── YouTube Data API ───────────────────────────────────────────────────────

def get_playlist_videos(playlist_id: str) -> list[dict]:
    """Fetch all videos from a YouTube playlist."""
    videos = []
    page_token = None
    base_url = "https://www.googleapis.com/youtube/v3/playlistItems"

    while True:
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": 50,
            "key": YOUTUBE_API_KEY
        }
        if page_token:
            params["pageToken"] = page_token

        r = requests.get(base_url, params=params, timeout=10)
        data = r.json()

        if "error" in data:
            log(f"YouTube API error: {data['error']}")
            break

        for item in data.get("items", []):
            snippet = item["snippet"]
            vid_id = snippet.get("resourceId", {}).get("videoId", "")
            if vid_id and vid_id != "deleted":
                videos.append({
                    "video_id": vid_id,
                    "title": snippet.get("title", ""),
                    "channel_name": snippet.get("videoOwnerChannelTitle", ""),
                    "channel_id": snippet.get("videoOwnerChannelId", ""),
                    "description": snippet.get("description", ""),
                    "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "playlist_position": snippet.get("position", 0)
                })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    # Enrich with video statistics and duration
    if videos:
        video_ids = [v["video_id"] for v in videos]
        for i in range(0, len(video_ids), 50):
            batch = video_ids[i:i+50]
            r = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "contentDetails,statistics", "id": ",".join(batch), "key": YOUTUBE_API_KEY},
                timeout=10
            )
            for item in r.json().get("items", []):
                vid_id = item["id"]
                for v in videos:
                    if v["video_id"] == vid_id:
                        stats = item.get("statistics", {})
                        v["view_count"] = int(stats.get("viewCount", 0))
                        v["like_count"] = int(stats.get("likeCount", 0))
                        # Parse ISO duration (e.g. PT4M13S)
                        dur = item.get("contentDetails", {}).get("duration", "PT0S")
                        v["duration_seconds"] = parse_duration(dur)

    log(f"  Found {len(videos)} videos in playlist")
    return videos


def parse_duration(iso: str) -> int:
    """Parse ISO 8601 duration to seconds."""
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso)
    if not m:
        return 0
    h, mins, s = m.groups(default="0")
    return int(h) * 3600 + int(mins) * 60 + int(s)


# ─── Main Pipeline ──────────────────────────────────────────────────────────

def process_own_videos():
    log("=" * 60)
    log("PHASE 1: Analyzing Isaiah's published YouTube videos")
    log("=" * 60)

    # Get unique video IDs not yet analyzed
    existing = {r["video_id"] for r in db.table("yt_own_video_analysis").select("video_id").execute().data}
    rows = db.table("youtube_video_stats").select("video_id,title,views,likes,published_at").execute().data

    # Deduplicate
    seen = set()
    videos = []
    for r in rows:
        vid = r["video_id"]
        if vid not in seen:
            seen.add(vid)
            videos.append(r)

    log(f"  {len(videos)} unique videos in youtube_video_stats, {len(existing)} already analyzed")
    analyzed = []

    for v in videos:
        vid_id = v["video_id"]
        title = v.get("title", "")

        if vid_id in existing:
            log(f"  SKIP (already done): {title[:50]}")
            continue

        # Skip pure Sora aesthetic videos (no dialogue)
        title_lower = title.lower()
        is_sora = any(kw in title_lower for kw in ["badass", "wingsuit", "dino", "urban surf", "primadonna glow"])
        # But keep shorts with real dialogue
        if is_sora and "shorts" not in title_lower:
            log(f"  SKIP (Sora AI, no transcript): {title[:50]}")
            # Still record it with no transcript
            db.table("yt_own_video_analysis").upsert({
                "video_id": vid_id,
                "title": title,
                "views": v.get("views"),
                "published_at": v.get("published_at"),
                "has_transcript": False,
                "content_category": "aesthetic_video",
                "analyzed_at": datetime.now(timezone.utc).isoformat()
            }).execute()
            continue

        log(f"  Processing: {title[:60]}")

        transcript, segments, has_transcript = get_transcript(vid_id)

        record = {
            "video_id": vid_id,
            "title": title,
            "views": v.get("views"),
            "likes": v.get("likes"),
            "published_at": v.get("published_at"),
            "has_transcript": has_transcript,
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }

        if has_transcript and len(transcript) > 100:
            record["transcript"] = transcript
            record["transcript_segments"] = segments
            record["word_count"] = len(transcript.split())
            record["duration_minutes"] = round(len(transcript.split()) / 130, 1)  # ~130 wpm

            log(f"    Transcript: {record['word_count']} words — running Claude analysis...")
            analysis = analyze_own_video(vid_id, title, transcript)

            if analysis:
                record["themes"] = analysis.get("themes", [])
                record["emotional_journey"] = analysis.get("emotional_journey", {})
                record["fate_scores"] = analysis.get("fate_scores", {})
                record["values_expressed"] = analysis.get("values_expressed", [])
                record["narrative_patterns"] = analysis.get("narrative_patterns", [])
                record["key_insights"] = analysis.get("key_insights", [])
                record["hook"] = analysis.get("hook", "")
                record["storytelling_style"] = analysis.get("storytelling_style", "")
                record["personal_brand_signals"] = analysis.get("personal_brand_signals", {})
                record["content_category"] = analysis.get("content_category", "")
                record["ai_analysis"] = analysis
                log(f"    Done: themes={analysis.get('themes', [])[:3]}")
        else:
            log(f"    No transcript available")

        db.table("yt_own_video_analysis").upsert(record).execute()
        analyzed.append(record)
        time.sleep(0.5)  # Respect rate limits

    log(f"\n  Phase 1 complete: {len(analyzed)} videos newly analyzed")
    return analyzed


def process_inspiration_playlist(max_videos: int = 200):
    log("=" * 60)
    log("PHASE 2: Analyzing inspirational playlist")
    log(f"  Playlist: {PLAYLIST_ID}")
    log("=" * 60)

    existing = {r["video_id"] for r in db.table("yt_inspiration_analysis").select("video_id").execute().data}
    log(f"  {len(existing)} already analyzed")

    log("  Fetching playlist videos from YouTube API...")
    all_playlist_videos = get_playlist_videos(PLAYLIST_ID)
    # Take only the top N (most recently added = position 0..N-1)
    playlist_videos = all_playlist_videos[:max_videos]
    log(f"  Limiting to {len(playlist_videos)} of {len(all_playlist_videos)} total videos")
    analyzed = []

    for v in playlist_videos:
        vid_id = v["video_id"]
        title = v.get("title", "")

        if vid_id in existing:
            log(f"  SKIP (already done): {title[:50]}")
            continue

        log(f"  Processing: {title[:60]} ({v.get('channel_name', '')})")

        transcript, segments, has_transcript = get_transcript(vid_id)

        record = {
            "video_id": vid_id,
            "playlist_id": PLAYLIST_ID,
            "title": title,
            "channel_name": v.get("channel_name", ""),
            "channel_id": v.get("channel_id", ""),
            "description": v.get("description", "")[:2000],
            "thumbnail_url": v.get("thumbnail_url", ""),
            "published_at": v.get("published_at") or None,
            "duration_seconds": v.get("duration_seconds"),
            "view_count": v.get("view_count"),
            "like_count": v.get("like_count"),
            "has_transcript": has_transcript,
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }

        if has_transcript and len(transcript) > 100:
            record["transcript"] = transcript
            record["transcript_segments"] = segments
            record["word_count"] = len(transcript.split())

            log(f"    Transcript: {record['word_count']} words — running full Claude analysis...")
            analysis = analyze_inspiration_video(
                vid_id, title,
                v.get("channel_name", ""),
                transcript,
                v.get("description", "")
            )
        else:
            # Use metadata-only analysis (title + description) — no transcript needed
            log(f"    No transcript — metadata analysis...")
            analysis = analyze_inspiration_video_metadata(
                vid_id, title,
                v.get("channel_name", ""),
                v.get("description", "")
            )

        if analysis:
            record["themes"] = analysis.get("themes", [])
            record["values_expressed"] = analysis.get("values_expressed", [])
            record["key_lessons"] = analysis.get("key_lessons", [])
            record["why_inspiring"] = analysis.get("why_inspiring", "")
            record["content_category"] = analysis.get("content_category", "")
            record["ai_analysis"] = analysis
            if has_transcript:
                record["emotional_journey"] = analysis.get("emotional_journey", {})
                record["fate_scores"] = analysis.get("fate_scores", {})
                record["narrative_style"] = analysis.get("narrative_style", "")
                record["speaker_identity"] = analysis.get("speaker_identity", "")
            log(f"    Done: themes={analysis.get('themes', [])[:3]}")

        # Always upsert — metadata analysis is still valuable
        db.table("yt_inspiration_analysis").upsert(record).execute()
        analyzed.append(record)
        time.sleep(0.3)

    log(f"\n  Phase 2 complete: {len(analyzed)} inspiration videos newly analyzed")
    return analyzed


def run_synthesis():
    log("=" * 60)
    log("PHASE 3: Synthesizing life narrative")
    log("=" * 60)

    own = db.table("yt_own_video_analysis").select("*").execute().data
    insp = db.table("yt_inspiration_analysis").select("*").execute().data

    own_with_analysis = [v for v in own if v.get("ai_analysis")]
    insp_with_analysis = [v for v in insp if v.get("ai_analysis")]

    log(f"  {len(own_with_analysis)} own videos with analysis")
    log(f"  {len(insp_with_analysis)} inspiration videos with analysis")

    if len(own_with_analysis) + len(insp_with_analysis) < 3:
        log("  Not enough analyzed videos yet for synthesis. Run again after more transcripts are available.")
        return

    log("  Running Claude synthesis...")
    synthesis = synthesize_narrative(own_with_analysis, insp_with_analysis)

    if synthesis:
        # Build theme frequency map
        theme_freq = {}
        for v in own_with_analysis + insp_with_analysis:
            a = v.get("ai_analysis", {})
            for t in a.get("themes", []):
                theme_freq[t] = theme_freq.get(t, 0) + 1

        record = {
            "own_videos_analyzed": len(own_with_analysis),
            "inspiration_videos_analyzed": len(insp_with_analysis),
            "playlist_id": PLAYLIST_ID,
            "guiding_storyline": synthesis.get("guiding_storyline", ""),
            "narrative_arc": synthesis.get("narrative_arc", ""),
            "life_chapter": synthesis.get("life_chapter", ""),
            "recurring_themes": synthesis.get("recurring_themes", []),
            "core_values": synthesis.get("core_values", []),
            "dominant_emotions": synthesis.get("dominant_emotions", []),
            "identity_patterns": synthesis.get("identity_patterns", {}),
            "aspiration_patterns": synthesis.get("aspiration_patterns", {}),
            "alignment_score": synthesis.get("alignment_score", 0),
            "alignment_summary": synthesis.get("alignment_summary", ""),
            "gaps": synthesis.get("gaps", []),
            "emerging_themes": synthesis.get("emerging_themes", []),
            "narrative_voice": synthesis.get("narrative_voice", ""),
            "content_superpower": synthesis.get("content_superpower", ""),
            "north_star": synthesis.get("north_star", ""),
            "recommendations": synthesis.get("recommendations", []),
            "theme_frequency": theme_freq,
            "full_synthesis": synthesis,
            "generated_at": datetime.now(timezone.utc).isoformat()
        }

        db.table("life_narrative_synthesis").insert(record).execute()
        log("\n" + "=" * 60)
        log("LIFE NARRATIVE SYNTHESIS COMPLETE")
        log("=" * 60)
        log(f"\nNARRATIVE ARC: {synthesis.get('narrative_arc', '')}")
        log(f"LIFE CHAPTER:  {synthesis.get('life_chapter', '')}")
        log(f"\nNORTH STAR: {synthesis.get('north_star', '')}")
        log(f"\nCORE VALUES: {', '.join(synthesis.get('core_values', []))}")
        log(f"\nCONTENT SUPERPOWER: {synthesis.get('content_superpower', '')}")
        log(f"\nALIGNMENT SCORE: {synthesis.get('alignment_score', 0):.0%}")
        log(f"\n--- GUIDING STORYLINE ---")
        print(synthesis.get("guiding_storyline", ""))
        log(f"\n--- RECOMMENDATIONS ---")
        for r in synthesis.get("recommendations", []):
            log(f"  • {r}")
    else:
        log("  Synthesis failed — check logs above")


# ─── Entry Point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=["1", "2", "3", "all"], default="all",
                        help="Which phase to run: 1=own videos, 2=playlist, 3=synthesis, all=everything")
    parser.add_argument("--max-inspiration", type=int, default=200,
                        help="Max inspiration videos to analyze (default 200 = most recently added)")
    args = parser.parse_args()

    log("Life Narrative Pipeline starting...")
    log(f"Supabase: {SUPABASE_URL[:40]}...")
    log(f"Playlist: {PLAYLIST_ID}")
    log(f"Phase: {args.phase}")
    log(f"Max inspiration videos: {args.max_inspiration}")
    log("")

    try:
        if args.phase in ("1", "all"):
            process_own_videos()
        if args.phase in ("2", "all"):
            process_inspiration_playlist(max_videos=args.max_inspiration)
        if args.phase in ("3", "all"):
            run_synthesis()
    except KeyboardInterrupt:
        log("\nInterrupted by user.")
    except Exception as e:
        log(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)

    log("\nDone.")
