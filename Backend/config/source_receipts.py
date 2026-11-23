"""Resolve archived iPhone imports using an operator-selected source receipt."""

import json
import os
import re
import stat
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=2)
def _read_receipt(path: Path, version: tuple[int, ...]) -> dict[str, dict]:
    with path.open(encoding="utf-8") as stream:
        return {record["application_copy"]: record for record in json.load(stream)["verified"]}


def _identity(info: os.stat_result) -> list[int]:
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def import_replacements(import_dir: Path, filename: str = "") -> dict[Path, Path]:
    """Return receipt entries whose retained file still has its verified identity."""
    receipt = os.environ.get("MEDIAPOSTER_IPHONE_SOURCE_RECEIPT")
    if not receipt:
        return {}
    archive_root = import_dir.parents[2]
    try:
        path = Path(receipt)
        info = path.stat()
        records = _read_receipt(path, (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns))
    except (OSError, ValueError, KeyError, TypeError):
        return {}
    selected = records.values()
    if filename:
        key = str((import_dir / filename).relative_to(archive_root))
        selected = (records[key],) if key in records else ()

    replacements = {}
    for record in selected:
        old = archive_root / record["application_copy"]
        source = archive_root / record["retained_path"]
        if old.parent != import_dir or not re.fullmatch(r"[0-9a-f]{64}", record["sha256"]):
            continue
        if not source.is_relative_to(archive_root) or source.is_relative_to(archive_root / "MediaPoster"):
            continue
        try:
            if source.resolve(strict=True) != source:
                continue
            current = source.lstat()
        except OSError:
            continue
        if not stat.S_ISREG(current.st_mode) or _identity(current) != record["verified_identity"]:
            continue
        try:
            original = old.lstat()
        except FileNotFoundError:
            pass  # The verified source remains usable after cleanup.
        except OSError:
            continue
        else:
            if not stat.S_ISREG(original.st_mode) or _identity(original) != record["application_identity"]:
                continue
        replacements[old] = source
    return replacements


def archived_import_sources(archive: Path) -> set[Path]:
    """Discover completed direct imports by their durable source receipts."""
    sources = set()
    receipts = archive / "receipts"
    if receipts.is_symlink():
        return sources
    for path in receipts.glob("*.source.json"):
        try:
            if path.is_symlink():
                continue
            record = json.loads(path.read_text(encoding="utf-8"))
            if record["status"] not in {"published", "existing_verified"}:
                continue
            sha256 = record["sha256"]
            if not re.fullmatch(r"[0-9a-f]{64}", sha256):
                continue
            source = Path(record["retained_path"])
            if source.parent != archive / "objects" / "sha256" / sha256 or source.stem != "source":
                continue
            if source.resolve(strict=True) != source:
                continue
            info = source.lstat()
            if stat.S_ISREG(info.st_mode) and _identity(info) == record["verified_identity"]:
                sources.add(source)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return sources
