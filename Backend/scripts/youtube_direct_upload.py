#!/usr/bin/env python3
"""Legacy YouTube direct-upload entrypoint, disabled in favor of Airtime.

Only ``--dry-run`` previews existing scheduled rows. Provider writes and status
updates are owned by Airtime delivery receipts.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"

class YouTubeDirectUploader:
    """Disabled legacy uploader retained for migration compatibility."""

    def authenticate(self):
        raise RuntimeError("airtime_required: direct YouTube uploads are disabled; use Airtime.")

    def upload_video(self, video_path: str, title: str, description: str,
                     tags: list = None, category_id: str = "22",
                     privacy_status: str = "public") -> dict:
        raise RuntimeError("airtime_required: direct YouTube uploads are disabled; use Airtime.")


def get_pending_videos():
    """Get videos that need to be uploaded."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT 
            sp.id as schedule_id,
            sp.title,
            sp.caption as description,
            sp.clip_id,
            v.source_uri as video_path,
            sp.status
        FROM scheduled_posts sp
        JOIN videos v ON sp.clip_id = v.id
        WHERE sp.platform = 'youtube'
          AND sp.created_at > NOW() - INTERVAL '6 hours'
          AND sp.status IN ('scheduled', 'publishing')
        ORDER BY sp.scheduled_time
    """)
    
    videos = cur.fetchall()
    cur.close()
    conn.close()
    return videos


def mark_as_posted(schedule_id: str, video_id: str, video_url: str):
    """Direct status writes are owned by Airtime delivery receipts."""
    raise RuntimeError("airtime_required: legacy publisher status writes are disabled; use Airtime receipts.")


def mark_as_failed(schedule_id: str, error: str):
    """Direct status writes are owned by Airtime delivery receipts."""
    raise RuntimeError("airtime_required: legacy publisher status writes are disabled; use Airtime receipts.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Legacy YouTube uploader (preview only)")
    parser.add_argument("--dry-run", action="store_true", help="List pending records without publishing")
    parser.add_argument("--limit", type=int, default=30, help="Maximum records to preview")
    parser.add_argument("--delay", type=int, default=30, help="Deprecated; retained for CLI compatibility")
    args = parser.parse_args()

    if not args.dry_run:
        print("airtime_required: direct YouTube uploads are disabled; use Airtime.")
        return 2

    videos = get_pending_videos()[:args.limit]
    print(f"Preview only: {len(videos)} pending YouTube schedule records")
    for index, video in enumerate(videos, 1):
        print(f"{index:3}. [{video['status']}] {video['title'][:40]} — {video['video_path']}")
    print("Airtime owns YouTube provider writes; no upload was attempted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
