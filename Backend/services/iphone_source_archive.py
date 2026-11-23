"""Publish staged iPhone originals with full hashes and durable source receipts.

This module never deletes source or duplicate files. Interrupted staging files
and incomplete publications remain available for recovery.
"""
import fcntl
import hashlib
import json
import os
import stat
import uuid
from datetime import datetime, timezone
from pathlib import Path


def identity(info):
    return [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]


def full_hash(path):
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Source is not a regular file")
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
        if identity(os.fstat(stream.fileno())) != identity(before) or identity(path.lstat()) != identity(before):
            raise ValueError("File changed during hashing")
    return digest.hexdigest(), before


def durable_json(path, record):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2, default=str)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def publish_staged_source(archive_dir, staged_path, source, expected_size):
    """Publish a complete staged file; return the per-source completion receipt.

    Callers must stage into archive/.incoming and provide device UDID, AFC path,
    original filename, and before/after device metadata in ``source``.
    Existing objects are freshly fully hashed before reuse. Duplicate staging
    files are retained and reported, never silently removed.
    """
    archive = Path(archive_dir).absolute()
    staged = Path(staged_path).absolute()
    if archive.resolve() != archive or staged.resolve() != staged:
        raise ValueError("Archive and staged paths must not traverse symlinks")
    if staged.parent != archive / ".incoming":
        raise ValueError("Staged file must be directly inside archive/.incoming")
    if not source.get("device_udid") or not source.get("afc_path") or not source.get("original_name"):
        raise ValueError("Missing source device/path/name")
    if source.get("before") != source.get("after"):
        raise ValueError("Device file changed during transfer")
    if not isinstance(expected_size, int) or expected_size < 0:
        raise ValueError("Invalid expected size")
    with (archive / ".publication.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        digest, info = full_hash(staged)
        if info.st_size != expected_size:
            raise ValueError("Transferred file size differs from source")
        with staged.open("rb") as stream:
            os.fsync(stream.fileno())
        receipts = archive / "receipts"
        objects = archive / "objects" / "sha256"
        receipts.mkdir(parents=True, exist_ok=True)
        objects.mkdir(parents=True, exist_ok=True)
        if receipts.resolve() != receipts or objects.resolve() != objects:
            raise ValueError("Archive subdirectories must not traverse symlinks")
        token = uuid.uuid4().hex
        directory = objects / digest
        record = {"version": 1, "recorded_utc": datetime.now(timezone.utc).isoformat(),
                  "source": source, "sha256": digest, "size_bytes": info.st_size,
                  "staged_path": str(staged), "staged_identity": identity(info)}
        durable_json(receipts / (token + ".intent.json"), record)
        if directory.exists():
            if directory.resolve() != directory:
                raise ValueError("Archive object directory must not traverse symlinks")
            candidates = list(directory.glob("source.*"))
            if len(candidates) != 1:
                raise ValueError("Existing object is incomplete or ambiguous; recovery required")
            target = candidates[0]
            found_hash, found_info = full_hash(target)
            if found_hash != digest or found_info.st_size != info.st_size:
                raise ValueError("Existing archive object failed full verification")
            status = "existing_verified"
        else:
            suffix = Path(source["original_name"]).suffix.lower()
            if not suffix or not suffix[1:].isalnum():
                raise ValueError("Original filename must have a media extension")
            directory.mkdir()  # Exclusive reservation: never replace an object.
            target = directory / ("source" + suffix)
            if identity(staged.lstat()) != identity(info):
                raise ValueError("Staged file changed before publication")
            os.rename(staged, target)
            found_hash, found_info = full_hash(target)
            if found_hash != digest:
                raise ValueError("Published archive object failed full verification")
            status = "published"
        record.update(status=status, retained_path=str(target),
                      verified_identity=identity(found_info),
                      retained_staging_path=str(staged) if status == "existing_verified" else None)
        receipt = receipts / (token + ".source.json")
        durable_json(receipt, record)
        return {**record, "receipt_path": str(receipt)}
