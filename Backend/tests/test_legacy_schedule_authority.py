import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

import scripts.schedule_videos as schedule_videos
import scripts.watch_folder as watch_folder
import scripts.youtube_direct_upload as youtube_direct_upload


def test_schedule_videos_only_allows_preview_insert():
    assert schedule_videos.insert_scheduled_posts(None, [{"id": "preview"}], dry_run=True) == 1
    with pytest.raises(RuntimeError, match="airtime_required"):
        schedule_videos.insert_scheduled_posts(None, [{"id": "blocked"}], dry_run=False)


def test_watch_folder_helpers_fail_before_file_or_database_access():
    with pytest.raises(RuntimeError, match="airtime_required"):
        watch_folder.schedule_video(None, Path("/definitely/missing.mp4"), [])
    watcher = object.__new__(watch_folder.FolderWatcher)
    with pytest.raises(RuntimeError, match="airtime_required"):
        watcher._process_file(Path("/definitely/missing.mp4"))
    with pytest.raises(RuntimeError, match="airtime_required"):
        watcher.start()


@pytest.mark.parametrize(
    "call",
    [
        lambda: youtube_direct_upload.YouTubeDirectUploader().authenticate(),
        lambda: youtube_direct_upload.YouTubeDirectUploader().upload_video("/missing", "x", "x"),
        lambda: youtube_direct_upload.mark_as_posted("id", "id", "url"),
        lambda: youtube_direct_upload.mark_as_failed("id", "error"),
    ],
)
def test_youtube_direct_upload_helpers_are_disabled(call):
    with pytest.raises(RuntimeError, match="airtime_required"):
        call()


@pytest.mark.parametrize(
    ("script", "args", "expected"),
    [
        ("youtube_direct_upload.py", [], "airtime_required"),
        ("schedule_from_guide.py", ["/missing/guide.md"], "airtime_required"),
        ("schedule_videos.py", ["/missing/videos"], "airtime_required"),
        ("watch_folder.py", ["/missing/folder"], "airtime_required"),
        ("schedule_videos.py", ["/missing/videos", "--dry-run", "--thumbnails"], "orion_required"),
    ],
)
def test_legacy_cli_write_paths_fail_closed(script, args, expected):
    result = subprocess.run(
        [sys.executable, str(BACKEND / "scripts" / script), *args],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert expected in result.stdout
