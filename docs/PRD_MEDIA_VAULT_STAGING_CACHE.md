# PRD: Media Vault + Staging Cache Architecture

**Status:** In Progress  
**Created:** 2026-02-06  
**Priority:** High  

---

## 1. Problem Statement

MediaPoster runs on a Mac (Safari automation + posting ops), but large media files (raw captures, Sora renders, transcoded outputs) live on a separate machine with more storage. Currently there's no structured way to:

- Reference assets stored on a remote machine
- Stage files locally before Safari uploads (network mounts are flaky for browser uploads)
- Track which files are cached locally vs. remote-only
- Clean up staging after successful posts

## 2. Architecture: Option A — Media Vault + Local Staging Cache

```
┌─────────────────────┐         LAN (SMB/NFS)        ┌──────────────────────┐
│   Machine B          │◄────────────────────────────►│   Mac (This Machine) │
│   "Media Vault"      │                              │   "Ops Runner"       │
│                      │                              │                      │
│   /MediaVault/       │    rsync --partial            │   ~/staging/         │
│     originals/       │────────────────────────────►  │     {asset_id}.mp4   │
│     renders/         │    (on-demand per job)        │                      │
│     exports/         │                              │   Safari uploads     │
│                      │                              │   from staging/      │
└─────────────────────┘                              └──────────────────────┘
                                                              │
                                                              ▼
                                                     ┌──────────────────┐
                                                     │  Supabase / DB   │
                                                     │  asset_registry  │
                                                     │  staging_jobs    │
                                                     └──────────────────┘
```

### Core Principles

1. **Machine B = canonical storage** — originals, renders, exports
2. **Mac = ops runner** — Safari automation, posting, scheduling
3. **Staging = local SSD cache** — only pull what's needed per job
4. **DB = metadata + pointers** — never stores media, only references
5. **Cleanup after success** — staging folder stays lean

## 3. Data Model

### 3.1 Asset Registry (local JSON + optional Supabase)

```json
{
  "asset_id": "asset_20260206_001",
  "filename": "morning_routine_final.mp4",
  "source_uri": "smb://machineb/MediaVault/exports/morning_routine_final.mp4",
  "source_type": "smb",
  "file_size_bytes": 524288000,
  "checksum_sha256": "abc123...",
  "duration_seconds": 62,
  "resolution": "1080x1920",
  "codec": "h264",
  "content_type": "video/mp4",
  "tags": ["morning", "routine", "reel"],
  "project_id": null,
  "created_at": "2026-02-06T00:00:00Z",
  "staging_status": "not_staged",
  "local_cached_path": null,
  "staged_at": null,
  "last_used_at": null
}
```

### 3.2 Staging Job

```json
{
  "job_id": "stage_20260206_001",
  "asset_id": "asset_20260206_001",
  "source_uri": "smb://machineb/MediaVault/exports/morning_routine_final.mp4",
  "local_path": "/Users/isaiahdupree/staging/asset_20260206_001.mp4",
  "status": "pending|transferring|staged|failed|cleaned",
  "transfer_method": "rsync",
  "bytes_transferred": 0,
  "progress_pct": 0,
  "started_at": null,
  "completed_at": null,
  "error": null
}
```

## 4. API Endpoints

### 4.1 Vault Configuration

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/vault/config` | Get vault mount config + staging settings |
| PUT | `/api/vault/config` | Update vault mount path, staging dir, max cache size |
| GET | `/api/vault/status` | Check mount connectivity + staging disk usage |

### 4.2 Asset Registry

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/vault/assets` | List all registered assets (with filters) |
| POST | `/api/vault/assets` | Register a new asset (scan file metadata) |
| GET | `/api/vault/assets/{id}` | Get asset details + staging status |
| DELETE | `/api/vault/assets/{id}` | Unregister asset (doesn't delete source file) |
| POST | `/api/vault/assets/scan` | Scan vault directory and auto-register new files |

### 4.3 Staging Operations

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/vault/assets/{id}/stage` | Start staging (rsync to local) |
| GET | `/api/vault/assets/{id}/stage/status` | Get transfer progress |
| DELETE | `/api/vault/assets/{id}/stage` | Clean up local staged file |
| POST | `/api/vault/staging/cleanup` | Clean all staged files older than N hours |
| GET | `/api/vault/staging/usage` | Get staging folder disk usage |

## 5. Vault Configuration File

Stored at `Backend/config/vault_config.json`:

```json
{
  "vault_mount_path": "/Volumes/MediaVault",
  "vault_type": "smb",
  "vault_host": "192.168.1.100",
  "vault_share": "MediaVault",
  "staging_dir": "/Users/isaiahdupree/staging",
  "max_staging_size_gb": 50,
  "auto_cleanup_hours": 24,
  "transfer_method": "rsync",
  "rsync_options": "--partial --append-verify --progress",
  "scan_directories": ["exports", "renders", "originals"],
  "supported_extensions": [".mp4", ".mov", ".avi", ".mkv", ".webm", ".jpg", ".png"]
}
```

## 6. Frontend Pages

### 6.1 Media Vault Settings (`/vault-settings`)

- Mount path configuration
- Staging directory + max size
- Test connection button
- Auto-cleanup settings
- Current staging disk usage bar

### 6.2 Asset Browser (`/vault-assets`)

- Grid/list view of all registered assets
- Filter by tags, type, staging status
- Quick-stage button per asset
- Staging progress indicator
- Bulk scan + register from vault

### 6.3 Integration Points

- **Publish flow**: When scheduling a post, if asset is remote → auto-stage before upload
- **Content Calendar**: Show staging status badge on posts with remote assets
- **Orchestrator**: Stage step added before Safari upload step

## 7. Transfer Implementation

### rsync command (primary)

```bash
rsync --partial --append-verify --progress \
  "/Volumes/MediaVault/exports/file.mp4" \
  "/Users/isaiahdupree/staging/asset_id.mp4"
```

### Fallback: cp (if mount is local)

```bash
cp -n "/Volumes/MediaVault/exports/file.mp4" \
  "/Users/isaiahdupree/staging/asset_id.mp4"
```

### Progress tracking

- Parse rsync `--progress` output for bytes transferred
- Update staging job record in real-time
- WebSocket or polling from frontend

## 8. Cleanup Strategy

1. **Auto-cleanup**: Cron/background task deletes staged files older than `auto_cleanup_hours`
2. **Post-success cleanup**: After successful upload, mark for cleanup
3. **Max size enforcement**: Before staging, check if staging dir exceeds `max_staging_size_gb`; if so, evict oldest files first
4. **Manual cleanup**: API endpoint + UI button

## 9. Implementation Phases

### Phase 1 (This PR): Core Infrastructure
- [x] PRD document
- [ ] Vault config file + management endpoints
- [ ] Asset registry (JSON-based, local storage)
- [ ] Staging operations (rsync transfer + progress)
- [ ] Cleanup service
- [ ] Frontend: Vault Settings page
- [ ] Frontend: Asset Browser page
- [ ] Sidebar navigation

### Phase 2 (Future): Deep Integration
- [ ] Auto-stage in publish pipeline
- [ ] Supabase asset_registry table (optional)
- [ ] R2/S3 support (Option C from design)
- [ ] Machine B render trigger (Option B)
- [ ] WebSocket progress streaming

## 10. Success Metrics

- Safari uploads from staging succeed > 99% of the time
- Staging transfer completes within 2x raw file copy time
- Staging folder stays under configured max size
- Zero "file not found" errors during scheduled posts
