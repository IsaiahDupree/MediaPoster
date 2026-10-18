"""Durable, approval-bound publication attempts for the marketing control plane."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional, Protocol
from urllib.parse import urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field


router = APIRouter(prefix="/v1/control-plane", tags=["control-plane-publications"])
RUNTIME_ID = uuid.uuid4().hex
SHA256_PATTERN = "^[a-f0-9]{64}$"
MAX_MEDIA_BYTES = 1024 * 1024 * 1024
SENSITIVE_KEY_RE = re.compile(
    r"(?:authorization|cookie|password|secret|credential|api[_-]?key|"
    r"access[_-]?token|refresh[_-]?token)$",
    re.IGNORECASE,
)

PLATFORM_MAP = {
    "facebook_reels": "facebook",
    "instagram_reels": "instagram",
    "youtube_shorts": "youtube",
    "x": "twitter",
    "twitter": "twitter",
    "tiktok": "tiktok",
    "threads": "threads",
    "pinterest": "pinterest",
}


class AssetReference(BaseModel):
    asset_id: str = Field(min_length=1, max_length=240)
    sha256: str = Field(pattern=SHA256_PATTERN)
    bytes: int = Field(gt=0, le=MAX_MEDIA_BYTES)
    download_path: str = Field(pattern=r"^/v1/control-plane/assets/[^/]+/bytes$")


class ApprovalReference(BaseModel):
    generation_approval_id: str = Field(min_length=1, max_length=240)
    publication_policy: Literal["auto_publish_after_qc"]
    approve_scheduled_publication: Literal[True]
    approved_at: datetime


class QCReference(BaseModel):
    decision: Literal["passed"]
    receipt_sha256: str = Field(pattern=SHA256_PATTERN)
    asset_sha256: str = Field(pattern=SHA256_PATTERN)


class PublicationAttemptRequest(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    contract_type: Literal["publication_attempt_request_v1"]
    content_work_item_id: str = Field(min_length=1, max_length=240)
    production_plan_id: str = Field(min_length=1, max_length=240)
    production_plan_sha256: str = Field(pattern=SHA256_PATTERN)
    destination_id: str = Field(min_length=1, max_length=240)
    attempt_number: int = Field(ge=1, le=20)
    platform: Literal[
        "facebook_reels", "instagram_reels", "youtube_shorts", "x", "twitter",
        "tiktok", "threads", "pinterest",
    ]
    airtime_account_id: str = Field(min_length=1, max_length=240)
    provider_account_id: str = Field(min_length=1, max_length=240)
    account_username: Optional[str] = Field(default=None, max_length=240)
    title: str = Field(min_length=1, max_length=200)
    caption: str = Field(min_length=1, max_length=5000)
    scheduled_at: datetime
    freshness_deadline_at: Optional[datetime] = None
    asset: AssetReference
    approval: ApprovalReference
    qc: QCReference
    held: Literal[False]
    confirm_provider_write: Literal[True]


class PublicationProvider(Protocol):
    async def publish(self, file_path: Path, request: PublicationAttemptRequest) -> dict[str, Any]: ...
    async def status(self, provider_submission_id: str) -> dict[str, Any]: ...


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str)


def _sha256(value: str | bytes) -> str:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(raw).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _safe_text(value: Any, limit: int = 1000) -> str:
    text = str(value or "").strip()
    text = re.sub(r"(?i)bearer\s+[A-Za-z0-9._~+/-]+", "Bearer [REDACTED]", text)
    text = re.sub(r"\bsk[_-][A-Za-z0-9_-]{12,}\b", "[REDACTED]", text)
    return text[:limit]


def _safe_public_url(value: Any) -> Optional[str]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = urlsplit(text)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    if parsed.username or parsed.password:
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _sanitize_provider_value(value: Any, depth: int = 0) -> Any:
    if depth > 6:
        return "[TRUNCATED]"
    if isinstance(value, dict):
        return {
            str(key)[:160]: ("[REDACTED]" if SENSITIVE_KEY_RE.search(str(key))
                             else _sanitize_provider_value(child, depth + 1))
            for key, child in list(value.items())[:200]
        }
    if isinstance(value, list):
        return [_sanitize_provider_value(child, depth + 1) for child in value[:200]]
    if isinstance(value, str):
        if value.startswith(("http://", "https://")):
            return _safe_public_url(value)
        return _safe_text(value, 4000)
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _safe_text(value, 1000)


def _db_path() -> Path:
    configured = os.environ.get("MEDIAPOSTER_CONTROL_PLANE_DB")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[2] / "data" / "control-plane-publications.sqlite3"


def _connect() -> sqlite3.Connection:
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS control_plane_publication_attempts (
          attempt_id TEXT PRIMARY KEY,
          idempotency_key TEXT NOT NULL UNIQUE,
          request_sha256 TEXT NOT NULL,
          content_work_item_id TEXT NOT NULL,
          production_plan_id TEXT NOT NULL,
          production_plan_sha256 TEXT NOT NULL,
          destination_id TEXT NOT NULL,
          attempt_number INTEGER NOT NULL,
          platform TEXT NOT NULL,
          airtime_account_id TEXT NOT NULL,
          provider_account_id TEXT NOT NULL,
          asset_id TEXT NOT NULL,
          asset_sha256 TEXT NOT NULL,
          qc_receipt_sha256 TEXT NOT NULL,
          generation_approval_id TEXT NOT NULL,
          state TEXT NOT NULL,
          runtime_id TEXT NOT NULL,
          provider_submission_id TEXT,
          provider_post_id TEXT,
          public_url TEXT,
          error_code TEXT,
          error_message TEXT,
          request_json TEXT NOT NULL,
          result_json TEXT,
          receipt_sha256 TEXT,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          submitted_at TEXT,
          completed_at TEXT,
          UNIQUE(content_work_item_id, production_plan_id, destination_id, attempt_number)
        );
        CREATE INDEX IF NOT EXISTS control_plane_publication_state_idx
          ON control_plane_publication_attempts(state, updated_at);
        """
    )
    db.execute(
        """UPDATE control_plane_publication_attempts
           SET state='prepared', error_code='PROCESS_RESTARTED_BEFORE_PROVIDER',
               error_message='MediaPoster restarted before provider submission began.',
               runtime_id=?, updated_at=?
           WHERE state='downloading' AND runtime_id<>?""",
        (RUNTIME_ID, _now_iso(), RUNTIME_ID),
    )
    db.execute(
        """UPDATE control_plane_publication_attempts
           SET state='unknown', error_code='PROCESS_RESTARTED_DURING_PROVIDER',
               error_message='MediaPoster restarted after provider submission began; reconcile before retrying.',
               runtime_id=?, updated_at=?, completed_at=COALESCE(completed_at, ?)
           WHERE state='submitting' AND runtime_id<>?""",
        (RUNTIME_ID, _now_iso(), _now_iso(), RUNTIME_ID),
    )
    db.commit()
    return db


def _authorize(authorization: Optional[str]) -> None:
    expected = os.environ.get("MEDIAPOSTER_CONTROL_TOKEN", "")
    supplied = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
    if not expected or not supplied or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail={
            "code": "MEDIAPOSTER_CONTROL_AUTH_REQUIRED",
            "message": "A valid MediaPoster control-plane token is required.",
        })


def _request_doc(request: PublicationAttemptRequest) -> dict[str, Any]:
    if hasattr(request, "model_dump"):
        return request.model_dump(mode="json")
    return json.loads(request.json())


def _preflight(request: PublicationAttemptRequest) -> dict[str, Any]:
    if request.qc.asset_sha256 != request.asset.sha256:
        raise HTTPException(status_code=409, detail={
            "code": "PUBLICATION_QC_ASSET_MISMATCH",
            "message": "The QC receipt is bound to different asset bytes.",
        })
    datetimes = {
        "scheduled_at": request.scheduled_at,
        "freshness_deadline_at": request.freshness_deadline_at,
        "approval.approved_at": request.approval.approved_at,
    }
    invalid_timezones = [name for name, value in datetimes.items()
                         if value is not None
                         and (value.tzinfo is None or value.utcoffset() is None)]
    if invalid_timezones:
        raise HTTPException(status_code=422, detail={
            "code": "PUBLICATION_TIMEZONE_REQUIRED",
            "message": "Publication, freshness, and approval timestamps must include a timezone.",
            "fields": invalid_timezones,
        })
    now = _now()
    if request.approval.approved_at > now:
        raise HTTPException(status_code=409, detail={
            "code": "PUBLICATION_APPROVAL_IN_FUTURE",
            "message": "The generation and publication approval timestamp is in the future.",
        })
    if request.freshness_deadline_at and request.freshness_deadline_at <= now:
        raise HTTPException(status_code=409, detail={
            "code": "PUBLICATION_FRESHNESS_EXPIRED",
            "message": "The approved content freshness deadline has passed.",
        })
    if os.environ.get("MEDIAPOSTER_CONTROL_PUBLISH_ENABLED", "").lower() != "true":
        raise HTTPException(status_code=423, detail={
            "code": "PUBLICATION_KILL_SWITCH_ACTIVE",
            "message": (
                "Control-plane publishing is disabled. Set "
                "MEDIAPOSTER_CONTROL_PUBLISH_ENABLED=true only when the workspace gate is on."
            ),
        })
    early_seconds = max(0, int(os.environ.get("MEDIAPOSTER_EARLY_PUBLISH_GRACE_SECONDS", "120")))
    if request.scheduled_at.timestamp() > now.timestamp() + early_seconds:
        raise HTTPException(status_code=409, detail={
            "code": "PUBLICATION_NOT_DUE",
            "message": "The destination is approved but its publication time has not arrived.",
            "scheduled_at": request.scheduled_at.isoformat(),
        })
    vault_url = os.environ.get("MEDIA_VAULT_CONTROL_URL", "").rstrip("/")
    vault_token = os.environ.get("MEDIA_VAULT_CONTROL_TOKEN", "")
    if not vault_url or not vault_token:
        raise HTTPException(status_code=503, detail={
            "code": "MEDIA_VAULT_CONTROL_UNAVAILABLE",
            "message": "Media Vault URL and service token must be configured before publication.",
        })
    if not os.environ.get("BLOTATO_API_KEY"):
        raise HTTPException(status_code=503, detail={
            "code": "PUBLISH_PROVIDER_CREDENTIAL_UNAVAILABLE",
            "message": "The MediaPoster publishing provider credential is unavailable.",
        })
    return {
        "ok": True,
        "executable": True,
        "provider": "mediaposter-blotato",
        "platform": PLATFORM_MAP[request.platform],
        "asset_sha256": request.asset.sha256,
        "approval_verified": True,
        "qc_verified": True,
        "provider_write_performed": False,
    }


def _target_config(request: PublicationAttemptRequest) -> dict[str, Any]:
    platform = PLATFORM_MAP[request.platform]
    if platform == "tiktok":
        return {
            "privacyLevel": "PUBLIC_TO_EVERYONE", "title": request.title[:80],
            "disabledComments": False, "disabledDuet": False, "disabledStitch": False,
            "isBrandedContent": False, "isYourBrand": True, "isAiGenerated": True,
        }
    if platform == "youtube":
        return {
            "title": request.title[:100], "privacyStatus": "public",
            "shouldNotifySubscribers": True, "isMadeForKids": False,
            "containsSyntheticMedia": True,
        }
    if platform == "instagram":
        return {"mediaType": "reel"}
    if platform == "facebook":
        return {"mediaType": "reel"}
    if platform == "pinterest":
        return {"title": request.title[:80]}
    return {}


class MediaPosterProvider:
    async def publish(self, file_path: Path, request: PublicationAttemptRequest) -> dict[str, Any]:
        from services.publish_service import get_publish_service

        service = get_publish_service()
        result = await service.full_publish_flow(
            file_path=file_path,
            account_id=request.provider_account_id,
            platform=PLATFORM_MAP[request.platform],
            text=request.caption,
            target_config=_target_config(request),
            scheduled_time=None,
            cleanup_storage=True,
            use_supabase=False,
        )
        return result

    async def status(self, provider_submission_id: str) -> dict[str, Any]:
        from services.publish_service import get_publish_service

        return await get_publish_service().get_post_status(provider_submission_id)


class MediaVaultDownloader:
    async def fetch(self, request: PublicationAttemptRequest, destination: Path) -> None:
        url = os.environ["MEDIA_VAULT_CONTROL_URL"].rstrip("/") + request.asset.download_path
        token = os.environ["MEDIA_VAULT_CONTROL_TOKEN"]
        digest = hashlib.sha256()
        size = 0
        async with httpx.AsyncClient(timeout=300) as client:
            async with client.stream("GET", url, headers={"Authorization": f"Bearer {token}"}) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"Media Vault returned HTTP {response.status_code}")
                declared_sha = response.headers.get("x-asset-sha256")
                if declared_sha and declared_sha != request.asset.sha256:
                    raise RuntimeError("Media Vault response SHA-256 does not match the approved asset")
                with destination.open("wb") as handle:
                    async for chunk in response.aiter_bytes(1024 * 1024):
                        size += len(chunk)
                        if size > request.asset.bytes or size > MAX_MEDIA_BYTES:
                            raise RuntimeError("Media Vault response exceeded the approved asset size")
                        digest.update(chunk)
                        handle.write(chunk)
        if size != request.asset.bytes or digest.hexdigest() != request.asset.sha256:
            raise RuntimeError("Media Vault bytes do not match the approved asset receipt")


class PublicationCoordinator:
    def __init__(self, provider: Optional[PublicationProvider] = None,
                 downloader: Optional[MediaVaultDownloader] = None):
        self.provider = provider or MediaPosterProvider()
        self.downloader = downloader or MediaVaultDownloader()

    def preflight(self, request: PublicationAttemptRequest) -> dict[str, Any]:
        return _preflight(request)

    def _present(self, row: sqlite3.Row, *, replay: bool = False) -> dict[str, Any]:
        request = json.loads(row["request_json"])
        result = json.loads(row["result_json"] or "{}")
        receipt = {
            "schema_version": "1.0",
            "contract_type": "publication_attempt_receipt_v1",
            "attempt_id": row["attempt_id"],
            "content_work_item_id": row["content_work_item_id"],
            "production_plan_id": row["production_plan_id"],
            "production_plan_sha256": row["production_plan_sha256"],
            "destination_id": row["destination_id"],
            "attempt_number": row["attempt_number"],
            "platform": row["platform"],
            "airtime_account_id": row["airtime_account_id"],
            "provider_account_id": row["provider_account_id"],
            "asset_id": row["asset_id"],
            "asset_sha256": row["asset_sha256"],
            "qc_receipt_sha256": row["qc_receipt_sha256"],
            "generation_approval_id": row["generation_approval_id"],
            "state": row["state"],
            "provider_submission_id": row["provider_submission_id"],
            "provider_post_id": row["provider_post_id"],
            "public_url": row["public_url"],
            "error": ({"code": row["error_code"], "message": row["error_message"]}
                      if row["error_code"] or row["error_message"] else None),
            "scheduled_at": request["scheduled_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "submitted_at": row["submitted_at"],
            "completed_at": row["completed_at"],
            "provider_result": result,
            "idempotent_replay": replay,
        }
        receipt_core = {key: value for key, value in receipt.items()
                        if key not in {"receipt_sha256", "idempotent_replay"}}
        receipt["receipt_sha256"] = _sha256(_canonical_json(receipt_core))
        return receipt

    def get(self, attempt_id: str) -> Optional[dict[str, Any]]:
        db = _connect()
        try:
            row = db.execute(
                "SELECT * FROM control_plane_publication_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            return self._present(row) if row else None
        finally:
            db.close()

    async def submit(self, request: PublicationAttemptRequest, idempotency_key: str) -> dict[str, Any]:
        request_doc = _request_doc(request)
        request_sha = _sha256(_canonical_json(request_doc))
        attempt_id = "pubatt_" + _sha256(
            f"{request.content_work_item_id}:{request.production_plan_id}:"
            f"{request.destination_id}:{request.attempt_number}"
        )[:24]
        db = _connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT * FROM control_plane_publication_attempts WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if existing:
                if existing["request_sha256"] != request_sha:
                    db.rollback()
                    raise HTTPException(status_code=409, detail={
                        "code": "IDEMPOTENCY_KEY_REUSED",
                        "message": "That Idempotency-Key is bound to another publication request.",
                    })
                if existing["state"] not in {"prepared"}:
                    db.commit()
                    return self._present(existing, replay=True)
                attempt_id = existing["attempt_id"]
                self.preflight(request)
            else:
                self.preflight(request)
                at = _now_iso()
                try:
                    db.execute(
                        """INSERT INTO control_plane_publication_attempts
                           (attempt_id,idempotency_key,request_sha256,content_work_item_id,
                            production_plan_id,production_plan_sha256,destination_id,
                            attempt_number,platform,airtime_account_id,provider_account_id,
                            asset_id,asset_sha256,qc_receipt_sha256,generation_approval_id,
                            state,runtime_id,request_json,created_at,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (attempt_id, idempotency_key, request_sha,
                         request.content_work_item_id, request.production_plan_id,
                         request.production_plan_sha256, request.destination_id,
                         request.attempt_number, request.platform, request.airtime_account_id,
                         request.provider_account_id, request.asset.asset_id,
                         request.asset.sha256, request.qc.receipt_sha256,
                         request.approval.generation_approval_id, "prepared", RUNTIME_ID,
                         _canonical_json(request_doc), at, at),
                    )
                except sqlite3.IntegrityError as exc:
                    db.rollback()
                    raise HTTPException(status_code=409, detail={
                        "code": "PUBLICATION_ATTEMPT_CONFLICT",
                        "message": "That destination attempt number already has a durable receipt.",
                    }) from exc
            db.execute(
                """UPDATE control_plane_publication_attempts
                   SET state='downloading', runtime_id=?, error_code=NULL,
                       error_message=NULL, updated_at=? WHERE attempt_id=?""",
                (RUNTIME_ID, _now_iso(), attempt_id),
            )
            db.commit()
        finally:
            db.close()

        temporary_path: Optional[Path] = None
        provider_started = False
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as handle:
                temporary_path = Path(handle.name)
            await self.downloader.fetch(request, temporary_path)
            db = _connect()
            try:
                db.execute(
                    """UPDATE control_plane_publication_attempts
                       SET state='submitting',runtime_id=?,submitted_at=?,updated_at=?
                       WHERE attempt_id=?""",
                    (RUNTIME_ID, _now_iso(), _now_iso(), attempt_id),
                )
                db.commit()
            finally:
                db.close()
            provider_started = True
            raw_result = await self.provider.publish(temporary_path, request)
            if not isinstance(raw_result, dict):
                raise RuntimeError("Provider returned a non-object publication receipt")
            result = _sanitize_provider_value(raw_result)
            success = result.get("success") is True
            submission_id = result.get("post_submission_id") or result.get("postSubmissionId")
            public_url = _safe_public_url(result.get("public_url") or result.get("publicUrl"))
            if success and not submission_id:
                raise RuntimeError("Provider accepted no submission ID")
            state = "published" if success and public_url else "submitted" if success else "failed"
            error_code = None if success else "PROVIDER_REJECTED"
            error_message = None if success else _safe_text(
                result.get("error") or "Provider rejected publication"
            )
            completed = _now_iso() if state in {"published", "failed"} else None
            db = _connect()
            try:
                db.execute(
                    """UPDATE control_plane_publication_attempts
                       SET state=?,provider_submission_id=?,public_url=?,error_code=?,
                           error_message=?,result_json=?,updated_at=?,completed_at=?
                       WHERE attempt_id=?""",
                    (state, _safe_text(submission_id, 240) if submission_id else None,
                     public_url, error_code, error_message,
                     _canonical_json(result), _now_iso(), completed, attempt_id),
                )
                db.commit()
                row = db.execute(
                    "SELECT * FROM control_plane_publication_attempts WHERE attempt_id=?",
                    (attempt_id,),
                ).fetchone()
                return self._present(row)
            finally:
                db.close()
        except HTTPException:
            raise
        except Exception as exc:
            db = _connect()
            try:
                state = "unknown" if provider_started else "failed"
                code = "PROVIDER_OUTCOME_UNKNOWN" if provider_started else "ASSET_DOWNLOAD_FAILED"
                db.execute(
                    """UPDATE control_plane_publication_attempts
                       SET state=?,error_code=?,error_message=?,updated_at=?,completed_at=?
                       WHERE attempt_id=?""",
                    (state, code, _safe_text(exc), _now_iso(), _now_iso(), attempt_id),
                )
                db.commit()
                row = db.execute(
                    "SELECT * FROM control_plane_publication_attempts WHERE attempt_id=?",
                    (attempt_id,),
                ).fetchone()
                return self._present(row)
            finally:
                db.close()
        finally:
            if temporary_path:
                temporary_path.unlink(missing_ok=True)

    async def reconcile(self, attempt_id: str) -> dict[str, Any]:
        db = _connect()
        try:
            row = db.execute(
                "SELECT * FROM control_plane_publication_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail={"code": "PUBLICATION_ATTEMPT_NOT_FOUND"})
            if row["state"] in {"published", "failed"}:
                return self._present(row, replay=True)
            submission_id = row["provider_submission_id"]
            if not submission_id:
                return self._present(row, replay=True)
        finally:
            db.close()
        raw_result = await self.provider.status(submission_id)
        if not isinstance(raw_result, dict):
            raise HTTPException(status_code=502, detail={
                "code": "PROVIDER_STATUS_RECEIPT_INVALID",
                "message": "Provider returned a non-object status receipt.",
            })
        result = _sanitize_provider_value(raw_result)
        status = str(result.get("status") or result.get("state") or "processing").lower()
        public_url = _safe_public_url(
            result.get("publicUrl") or result.get("public_url") or result.get("url")
        )
        error = result.get("errorMessage") or result.get("error_message") or result.get("error")
        if error or status in {"failed", "rejected", "cancelled", "canceled", "error"}:
            state, code, completed = "failed", "PROVIDER_PUBLICATION_FAILED", _now_iso()
        elif public_url and status in {"published", "completed", "success", "succeeded"}:
            state, code, completed = "published", None, _now_iso()
        else:
            state, code, completed = "processing", None, None
        provider_post_id = result.get("platformPostId") or result.get("platform_post_id")
        db = _connect()
        try:
            db.execute(
                """UPDATE control_plane_publication_attempts
                   SET state=?,provider_post_id=?,public_url=COALESCE(?,public_url),
                       error_code=?,error_message=?,result_json=?,updated_at=?,completed_at=?
                   WHERE attempt_id=?""",
                (state, str(provider_post_id) if provider_post_id else None,
                 public_url, code, _safe_text(error) if error else None,
                 _canonical_json(result),
                 _now_iso(), completed, attempt_id),
            )
            db.commit()
            row = db.execute(
                "SELECT * FROM control_plane_publication_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            return self._present(row)
        finally:
            db.close()


_coordinator = PublicationCoordinator()


def get_coordinator() -> PublicationCoordinator:
    return _coordinator


@router.post("/publication-preflights")
def publication_preflight(
    request: PublicationAttemptRequest,
    authorization: Optional[str] = Header(default=None),
    coordinator: PublicationCoordinator = Depends(get_coordinator),
):
    _authorize(authorization)
    return coordinator.preflight(request)


@router.post("/publication-attempts")
async def create_publication_attempt(
    request: PublicationAttemptRequest,
    authorization: Optional[str] = Header(default=None),
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    coordinator: PublicationCoordinator = Depends(get_coordinator),
):
    _authorize(authorization)
    key = (idempotency_key or "").strip()
    if not key or len(key) > 240:
        raise HTTPException(status_code=400, detail={
            "code": "IDEMPOTENCY_KEY_REQUIRED",
            "message": "A bounded Idempotency-Key is required.",
        })
    return await coordinator.submit(request, key)


@router.get("/publication-attempts/{attempt_id}")
def get_publication_attempt(
    attempt_id: str,
    authorization: Optional[str] = Header(default=None),
    coordinator: PublicationCoordinator = Depends(get_coordinator),
):
    _authorize(authorization)
    receipt = coordinator.get(attempt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail={"code": "PUBLICATION_ATTEMPT_NOT_FOUND"})
    return receipt


@router.post("/publication-attempts/{attempt_id}/reconcile")
async def reconcile_publication_attempt(
    attempt_id: str,
    authorization: Optional[str] = Header(default=None),
    coordinator: PublicationCoordinator = Depends(get_coordinator),
):
    _authorize(authorization)
    return await coordinator.reconcile(attempt_id)
