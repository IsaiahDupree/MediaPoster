"""
Media Vault + Staging Cache API
Manages remote media storage references, local staging cache,
and rsync-based file transfers for reliable Safari uploads.
"""
import os
import json
import shutil
import hashlib
import subprocess
import asyncio
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

router = APIRouter(prefix="/api/vault", tags=["Media Vault"])

# --- Config ---

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "vault_config.json"
DEFAULT_STAGING_DIR = Path.home() / "staging"

DEFAULT_CONFIG = {
    "vault_mount_path": "/Volumes/MediaVault",
    "vault_type": "smb",
    "vault_host": "",
    "vault_share": "MediaVault",
    "staging_dir": str(DEFAULT_STAGING_DIR),
    "max_staging_size_gb": 50,
    "auto_cleanup_hours": 24,
    "transfer_method": "rsync",
    "rsync_options": "--partial --append-verify --progress",
    "scan_directories": ["exports", "renders", "originals"],
    "supported_extensions": [".mp4", ".mov", ".avi", ".mkv", ".webm", ".jpg", ".png", ".heic"],
}

ASSETS_PATH = Path(__file__).parent.parent.parent / "data" / "vault_assets.json"
JOBS_PATH = Path(__file__).parent.parent.parent / "data" / "vault_staging_jobs.json"


def _load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def _save_config(config: Dict[str, Any]):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def _load_assets() -> List[Dict[str, Any]]:
    if ASSETS_PATH.exists():
        try:
            with open(ASSETS_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_assets(assets: List[Dict[str, Any]]):
    ASSETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ASSETS_PATH, "w") as f:
        json.dump(assets, f, indent=2)


def _load_jobs() -> List[Dict[str, Any]]:
    if JOBS_PATH.exists():
        try:
            with open(JOBS_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save_jobs(jobs: List[Dict[str, Any]]):
    JOBS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(JOBS_PATH, "w") as f:
        json.dump(jobs, f, indent=2)


def _get_staging_dir() -> Path:
    config = _load_config()
    staging = Path(config.get("staging_dir", str(DEFAULT_STAGING_DIR)))
    staging.mkdir(parents=True, exist_ok=True)
    return staging


def _dir_size_bytes(path: Path) -> int:
    total = 0
    if path.exists():
        for f in path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
    return total


def _file_checksum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# =============================================================================
# VAULT CONFIGURATION
# =============================================================================

@router.get("/config")
async def get_config():
    """Get vault mount config + staging settings."""
    return _load_config()


@router.put("/config")
async def update_config(
    vault_mount_path: str = "",
    vault_host: str = "",
    vault_share: str = "",
    vault_type: str = "",
    staging_dir: str = "",
    max_staging_size_gb: int = 0,
    auto_cleanup_hours: int = 0,
    transfer_method: str = "",
):
    """Update vault configuration."""
    config = _load_config()
    if vault_mount_path:
        config["vault_mount_path"] = vault_mount_path
    if vault_host:
        config["vault_host"] = vault_host
    if vault_share:
        config["vault_share"] = vault_share
    if vault_type:
        config["vault_type"] = vault_type
    if staging_dir:
        config["staging_dir"] = staging_dir
    if max_staging_size_gb > 0:
        config["max_staging_size_gb"] = max_staging_size_gb
    if auto_cleanup_hours > 0:
        config["auto_cleanup_hours"] = auto_cleanup_hours
    if transfer_method:
        config["transfer_method"] = transfer_method
    _save_config(config)
    return {"status": "updated", "config": config}


@router.get("/status")
async def get_status():
    """Check vault mount connectivity + staging disk usage."""
    config = _load_config()
    vault_path = Path(config["vault_mount_path"])
    staging_path = Path(config.get("staging_dir", str(DEFAULT_STAGING_DIR)))

    vault_mounted = vault_path.exists() and vault_path.is_dir()
    vault_files = 0
    vault_dirs = []
    if vault_mounted:
        try:
            vault_dirs = [d.name for d in vault_path.iterdir() if d.is_dir()][:20]
            vault_files = sum(1 for _ in vault_path.rglob("*") if _.is_file())
        except PermissionError:
            vault_files = -1

    staging_size = _dir_size_bytes(staging_path)
    staging_files = sum(1 for f in staging_path.glob("*") if f.is_file()) if staging_path.exists() else 0
    max_size = config.get("max_staging_size_gb", 50) * 1024 * 1024 * 1024

    assets = _load_assets()
    staged_count = sum(1 for a in assets if a.get("staging_status") == "staged")

    return {
        "vault_mounted": vault_mounted,
        "vault_path": str(vault_path),
        "vault_directories": vault_dirs,
        "vault_file_count": vault_files,
        "staging_path": str(staging_path),
        "staging_size_bytes": staging_size,
        "staging_size_human": f"{staging_size / (1024**3):.2f} GB",
        "staging_file_count": staging_files,
        "staging_usage_pct": round(staging_size / max(max_size, 1) * 100, 1),
        "max_staging_size_gb": config.get("max_staging_size_gb", 50),
        "total_assets": len(assets),
        "staged_assets": staged_count,
    }


# =============================================================================
# ASSET REGISTRY
# =============================================================================

@router.get("/assets")
async def list_assets(
    tag: str = "",
    staged_only: bool = False,
    content_type: str = "",
    limit: int = 100,
):
    """List all registered vault assets with optional filters."""
    assets = _load_assets()
    if tag:
        assets = [a for a in assets if tag.lower() in [t.lower() for t in a.get("tags", [])]]
    if staged_only:
        assets = [a for a in assets if a.get("staging_status") == "staged"]
    if content_type:
        assets = [a for a in assets if a.get("content_type", "").startswith(content_type)]
    return {"count": len(assets[:limit]), "total": len(assets), "assets": assets[:limit]}


@router.post("/assets")
async def register_asset(
    filename: str = "",
    source_path: str = "",
    tags: str = "",
    project_id: str = "",
):
    """Register a new asset from the vault (or a local path). Auto-reads file metadata."""
    config = _load_config()
    vault_path = Path(config["vault_mount_path"])

    # Resolve full path
    if source_path:
        full_path = Path(source_path)
    elif filename:
        # Search scan directories
        full_path = None
        for scan_dir in config.get("scan_directories", []):
            candidate = vault_path / scan_dir / filename
            if candidate.exists():
                full_path = candidate
                break
        if not full_path:
            full_path = vault_path / filename
    else:
        raise HTTPException(status_code=400, detail="Provide filename or source_path")

    if not full_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {full_path}")

    stat = full_path.stat()
    ext = full_path.suffix.lower()

    # Determine content type
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    image_exts = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
    ct = "video/mp4" if ext in video_exts else "image/jpeg" if ext in image_exts else "application/octet-stream"

    # Get duration for videos via ffprobe
    duration = 0
    resolution = ""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(full_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            probe = json.loads(result.stdout)
            duration = float(probe.get("format", {}).get("duration", 0))
            for stream in probe.get("streams", []):
                if stream.get("codec_type") == "video":
                    resolution = f"{stream.get('width', 0)}x{stream.get('height', 0)}"
                    break
    except Exception:
        pass

    assets = _load_assets()
    asset_id = f"asset_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(assets)}"

    entry = {
        "asset_id": asset_id,
        "filename": full_path.name,
        "source_uri": str(full_path),
        "source_type": "local" if str(full_path).startswith(str(Path.home())) else "vault",
        "file_size_bytes": stat.st_size,
        "file_size_human": f"{stat.st_size / (1024**2):.1f} MB",
        "duration_seconds": round(duration, 1),
        "resolution": resolution,
        "content_type": ct,
        "tags": [t.strip() for t in tags.split(",") if t.strip()] if tags else [],
        "project_id": project_id or None,
        "created_at": datetime.now().isoformat(),
        "staging_status": "not_staged",
        "local_cached_path": None,
        "staged_at": None,
        "last_used_at": None,
    }
    assets.append(entry)
    _save_assets(assets)
    return {"status": "registered", "asset": entry}


@router.get("/assets/{asset_id}")
async def get_asset(asset_id: str):
    """Get asset details + staging status."""
    assets = _load_assets()
    asset = next((a for a in assets if a["asset_id"] == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.delete("/assets/{asset_id}")
async def unregister_asset(asset_id: str):
    """Remove asset from registry (doesn't delete source file)."""
    assets = _load_assets()
    assets = [a for a in assets if a["asset_id"] != asset_id]
    _save_assets(assets)
    return {"status": "unregistered"}


@router.post("/assets/scan")
async def scan_vault():
    """Scan vault directories and auto-register new files."""
    config = _load_config()
    vault_path = Path(config["vault_mount_path"])
    if not vault_path.exists():
        raise HTTPException(status_code=400, detail=f"Vault not mounted: {vault_path}")

    supported = set(config.get("supported_extensions", [".mp4", ".mov"]))
    existing = _load_assets()
    existing_uris = {a["source_uri"] for a in existing}

    new_count = 0
    for scan_dir in config.get("scan_directories", []):
        dir_path = vault_path / scan_dir
        if not dir_path.exists():
            continue
        for file in dir_path.rglob("*"):
            if not file.is_file() or file.suffix.lower() not in supported:
                continue
            uri = str(file)
            if uri in existing_uris:
                continue

            stat = file.stat()
            ext = file.suffix.lower()
            video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
            image_exts = {".jpg", ".jpeg", ".png", ".heic", ".webp"}
            ct = "video/mp4" if ext in video_exts else "image/jpeg" if ext in image_exts else "application/octet-stream"

            entry = {
                "asset_id": f"asset_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(existing) + new_count}",
                "filename": file.name,
                "source_uri": uri,
                "source_type": "vault",
                "file_size_bytes": stat.st_size,
                "file_size_human": f"{stat.st_size / (1024**2):.1f} MB",
                "duration_seconds": 0,
                "resolution": "",
                "content_type": ct,
                "tags": [scan_dir],
                "project_id": None,
                "created_at": datetime.now().isoformat(),
                "staging_status": "not_staged",
                "local_cached_path": None,
                "staged_at": None,
                "last_used_at": None,
            }
            existing.append(entry)
            new_count += 1

    _save_assets(existing)
    return {"status": "scanned", "new_assets": new_count, "total_assets": len(existing)}


# =============================================================================
# STAGING OPERATIONS
# =============================================================================

async def _run_rsync(source: str, dest: str, job_id: str):
    """Run rsync transfer in background and update job progress."""
    jobs = _load_jobs()
    job = next((j for j in jobs if j["job_id"] == job_id), None)
    if not job:
        return

    job["status"] = "transferring"
    job["started_at"] = datetime.now().isoformat()
    _save_jobs(jobs)

    config = _load_config()
    rsync_opts = config.get("rsync_options", "--partial --append-verify --progress")

    try:
        cmd = f"rsync {rsync_opts} \"{source}\" \"{dest}\""
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        jobs = _load_jobs()
        job = next((j for j in jobs if j["job_id"] == job_id), None)
        if not job:
            return

        if proc.returncode == 0 and Path(dest).exists():
            job["status"] = "staged"
            job["completed_at"] = datetime.now().isoformat()
            job["bytes_transferred"] = Path(dest).stat().st_size
            job["progress_pct"] = 100

            # Update asset staging status
            assets = _load_assets()
            asset = next((a for a in assets if a["asset_id"] == job["asset_id"]), None)
            if asset:
                asset["staging_status"] = "staged"
                asset["local_cached_path"] = dest
                asset["staged_at"] = datetime.now().isoformat()
                _save_assets(assets)
        else:
            job["status"] = "failed"
            job["error"] = stderr.decode()[:500] if stderr else "Unknown error"
        _save_jobs(jobs)

    except Exception as e:
        jobs = _load_jobs()
        job = next((j for j in jobs if j["job_id"] == job_id), None)
        if job:
            job["status"] = "failed"
            job["error"] = str(e)[:500]
            _save_jobs(jobs)


@router.post("/assets/{asset_id}/stage")
async def stage_asset(asset_id: str, background_tasks: BackgroundTasks):
    """Start staging an asset (rsync from vault to local staging dir)."""
    assets = _load_assets()
    asset = next((a for a in assets if a["asset_id"] == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if asset.get("staging_status") == "staged" and asset.get("local_cached_path"):
        cached = Path(asset["local_cached_path"])
        if cached.exists():
            return {"status": "already_staged", "local_path": str(cached)}

    source = asset["source_uri"]
    if not Path(source).exists():
        raise HTTPException(status_code=400, detail=f"Source file not accessible: {source}")

    staging_dir = _get_staging_dir()
    ext = Path(source).suffix
    dest = str(staging_dir / f"{asset_id}{ext}")

    # Check staging capacity
    config = _load_config()
    max_bytes = config.get("max_staging_size_gb", 50) * 1024 * 1024 * 1024
    current_size = _dir_size_bytes(staging_dir)
    if current_size + asset.get("file_size_bytes", 0) > max_bytes:
        raise HTTPException(status_code=507, detail="Staging directory full. Run cleanup first.")

    jobs = _load_jobs()
    job_id = f"stage_{datetime.now().strftime('%Y%m%d%H%M%S')}_{asset_id}"
    job = {
        "job_id": job_id,
        "asset_id": asset_id,
        "source_uri": source,
        "local_path": dest,
        "status": "pending",
        "transfer_method": config.get("transfer_method", "rsync"),
        "bytes_transferred": 0,
        "progress_pct": 0,
        "started_at": None,
        "completed_at": None,
        "error": None,
    }
    jobs.append(job)
    _save_jobs(jobs)

    # Use rsync or cp
    if config.get("transfer_method", "rsync") == "rsync":
        background_tasks.add_task(_run_rsync, source, dest, job_id)
    else:
        # Simple copy fallback
        background_tasks.add_task(_run_copy, source, dest, job_id)

    return {"status": "staging_started", "job_id": job_id, "dest": dest}


async def _run_copy(source: str, dest: str, job_id: str):
    """Simple copy fallback."""
    jobs = _load_jobs()
    job = next((j for j in jobs if j["job_id"] == job_id), None)
    if not job:
        return
    job["status"] = "transferring"
    job["started_at"] = datetime.now().isoformat()
    _save_jobs(jobs)

    try:
        shutil.copy2(source, dest)
        jobs = _load_jobs()
        job = next((j for j in jobs if j["job_id"] == job_id), None)
        if job:
            job["status"] = "staged"
            job["completed_at"] = datetime.now().isoformat()
            job["bytes_transferred"] = Path(dest).stat().st_size
            job["progress_pct"] = 100
            _save_jobs(jobs)

            assets = _load_assets()
            asset = next((a for a in assets if a["asset_id"] == job["asset_id"]), None)
            if asset:
                asset["staging_status"] = "staged"
                asset["local_cached_path"] = dest
                asset["staged_at"] = datetime.now().isoformat()
                _save_assets(assets)
    except Exception as e:
        jobs = _load_jobs()
        job = next((j for j in jobs if j["job_id"] == job_id), None)
        if job:
            job["status"] = "failed"
            job["error"] = str(e)[:500]
            _save_jobs(jobs)


@router.get("/assets/{asset_id}/stage/status")
async def get_staging_status(asset_id: str):
    """Get transfer progress for an asset's staging job."""
    jobs = _load_jobs()
    asset_jobs = [j for j in jobs if j["asset_id"] == asset_id]
    if not asset_jobs:
        return {"status": "no_job", "asset_id": asset_id}
    latest = asset_jobs[-1]
    return latest


@router.delete("/assets/{asset_id}/stage")
async def clean_staged_file(asset_id: str):
    """Clean up a locally staged file."""
    assets = _load_assets()
    asset = next((a for a in assets if a["asset_id"] == asset_id), None)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    cached = asset.get("local_cached_path")
    if cached and Path(cached).exists():
        Path(cached).unlink()

    asset["staging_status"] = "not_staged"
    asset["local_cached_path"] = None
    asset["staged_at"] = None
    _save_assets(assets)
    return {"status": "cleaned", "asset_id": asset_id}


@router.post("/staging/cleanup")
async def cleanup_staging(max_age_hours: int = 24):
    """Clean all staged files older than max_age_hours."""
    staging_dir = _get_staging_dir()
    now = datetime.now()
    cleaned = 0
    freed_bytes = 0

    assets = _load_assets()
    for asset in assets:
        if asset.get("staging_status") != "staged":
            continue
        staged_at = asset.get("staged_at")
        if not staged_at:
            continue
        age_hours = (now - datetime.fromisoformat(staged_at)).total_seconds() / 3600
        if age_hours > max_age_hours:
            cached = asset.get("local_cached_path")
            if cached and Path(cached).exists():
                freed_bytes += Path(cached).stat().st_size
                Path(cached).unlink()
                cleaned += 1
            asset["staging_status"] = "not_staged"
            asset["local_cached_path"] = None
            asset["staged_at"] = None

    _save_assets(assets)
    return {
        "status": "cleanup_complete",
        "files_cleaned": cleaned,
        "freed_bytes": freed_bytes,
        "freed_human": f"{freed_bytes / (1024**2):.1f} MB",
    }


@router.get("/staging/usage")
async def get_staging_usage():
    """Get staging folder disk usage."""
    staging_dir = _get_staging_dir()
    size = _dir_size_bytes(staging_dir)
    config = _load_config()
    max_bytes = config.get("max_staging_size_gb", 50) * 1024 * 1024 * 1024
    files = list(staging_dir.glob("*")) if staging_dir.exists() else []
    file_list = []
    for f in files:
        if f.is_file():
            file_list.append({
                "name": f.name,
                "size_bytes": f.stat().st_size,
                "size_human": f"{f.stat().st_size / (1024**2):.1f} MB",
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    file_list.sort(key=lambda x: x["modified"], reverse=True)

    return {
        "staging_dir": str(staging_dir),
        "total_size_bytes": size,
        "total_size_human": f"{size / (1024**3):.2f} GB",
        "max_size_gb": config.get("max_staging_size_gb", 50),
        "usage_pct": round(size / max(max_bytes, 1) * 100, 1),
        "file_count": len(file_list),
        "files": file_list,
    }
