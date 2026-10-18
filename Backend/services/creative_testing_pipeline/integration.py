"""
ACTP Integration Module
========================
Handles external integrations: webhooks, OAuth, funnel tracking,
dynamic landing pages, offer expiry, and analytics webhooks.
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─── Webhook Receiver ─────────────────────────────────────

class WebhookReceiver:
    """Receive and validate incoming webhooks from external platforms."""

    def __init__(self, db_client=None):
        self.db = db_client

    def verify_signature(
        self, payload: bytes, signature: str, secret: str, algorithm: str = "sha256"
    ) -> bool:
        """Verify HMAC signature on an incoming webhook."""
        expected = hmac.new(
            secret.encode(), payload, getattr(hashlib, algorithm)
        ).hexdigest()
        sig_value = signature.split("=")[-1] if "=" in signature else signature
        return hmac.compare_digest(expected, sig_value)

    async def receive(
        self, source: str, event_type: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process an incoming webhook event."""
        event = {
            "source": source,
            "event_type": event_type,
            "payload": payload,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "status": "received",
        }

        if self.db:
            await self.db.table("actp_webhooks").insert(event).execute()

        logger.info(f"[ACTP:Webhook] Received {event_type} from {source}")

        # Route to handler
        handler = self._get_handler(source, event_type)
        if handler:
            result = await handler(payload)
            event["handled"] = True
            event["result"] = result
        else:
            event["handled"] = False

        return event

    def _get_handler(self, source: str, event_type: str):
        handlers = {
            ("meta_ads", "ad_status_update"): self._handle_meta_ad_status,
            ("tiktok_ads", "ad_status_update"): self._handle_tiktok_ad_status,
            ("stripe", "payment.succeeded"): self._handle_payment,
            ("waitlistlab", "offer.converted"): self._handle_offer_conversion,
        }
        return handlers.get((source, event_type))

    async def _handle_meta_ad_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        ad_id = payload.get("ad_id")
        status = payload.get("effective_status")
        if self.db and ad_id:
            await self.db.table("actp_ad_deployments").update({
                "status": status,
            }).eq("external_ad_id", ad_id).execute()
        return {"updated": bool(ad_id), "ad_id": ad_id, "status": status}

    async def _handle_tiktok_ad_status(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        ad_id = payload.get("ad_id")
        status = payload.get("status")
        if self.db and ad_id:
            await self.db.table("actp_ad_deployments").update({
                "status": status,
            }).eq("external_ad_id", ad_id).execute()
        return {"updated": bool(ad_id), "ad_id": ad_id}

    async def _handle_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        amount = payload.get("amount", 0)
        creative_id = (payload.get("metadata") or {}).get("creative_id")
        logger.info(f"[ACTP:Webhook] Payment ${amount/100:.2f} for creative {creative_id}")
        return {"recorded": True, "amount_cents": amount, "creative_id": creative_id}

    async def _handle_offer_conversion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        creative_id = payload.get("creative_id")
        offer_id = payload.get("offer_id")
        logger.info(f"[ACTP:Webhook] Offer {offer_id} converted via creative {creative_id}")
        return {"recorded": True, "creative_id": creative_id, "offer_id": offer_id}


# ─── Webhook Configuration CRUD ───────────────────────────

class WebhookManager:
    """Manage outbound webhook configurations."""

    def __init__(self, db_client=None):
        self.db = db_client

    async def create(
        self, url: str, events: List[str], secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """Register a new outbound webhook endpoint."""
        if not self.db:
            return {"created": False}

        config = {
            "url": url,
            "events": events,
            "secret": secret or os.urandom(32).hex(),
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        result = await self.db.table("actp_webhooks_config").insert(config).execute()
        return {"created": True, "webhook": (result.data or [{}])[0]}

    async def list_all(self) -> List[Dict[str, Any]]:
        if not self.db:
            return []
        result = await self.db.table("actp_webhooks_config").select("*").eq("active", True).execute()
        return result.data or []

    async def update(self, webhook_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        if not self.db:
            return {"updated": False}
        await self.db.table("actp_webhooks_config").update(updates).eq("id", webhook_id).execute()
        return {"updated": True, "webhook_id": webhook_id}

    async def delete(self, webhook_id: str) -> bool:
        if not self.db:
            return False
        await self.db.table("actp_webhooks_config").update({"active": False}).eq("id", webhook_id).execute()
        return True

    async def dispatch(self, event_type: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Dispatch an event to all matching registered webhooks."""
        import httpx
        webhooks = await self.list_all()
        results = []

        for wh in webhooks:
            if event_type not in (wh.get("events") or []):
                continue
            try:
                body = json.dumps({"event": event_type, "data": payload, "timestamp": datetime.now(timezone.utc).isoformat()})
                secret = wh.get("secret", "")
                sig = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        wh["url"],
                        content=body,
                        headers={"Content-Type": "application/json", "X-ACTP-Signature": f"sha256={sig}"},
                    )
                results.append({"webhook_id": wh.get("id"), "status": resp.status_code, "success": resp.is_success})
            except Exception as e:
                logger.error(f"[ACTP:Webhook] Dispatch failed to {wh.get('url')}: {e}")
                results.append({"webhook_id": wh.get("id"), "error": str(e), "success": False})

        return results


# ─── Social Account OAuth Management ──────────────────────

class OAuthManager:
    """Manage OAuth tokens for social platform accounts."""

    PLATFORMS = ["youtube", "tiktok", "instagram", "meta_ads", "twitter"]

    def __init__(self, db_client=None):
        self.db = db_client

    async def store_token(
        self, platform: str, account_id: str, access_token: str,
        refresh_token: Optional[str] = None, expires_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Store an OAuth token for a platform account."""
        if not self.db:
            return {"stored": False}

        record = {
            "platform": platform,
            "account_id": account_id,
            "access_token": access_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.db.table("actp_oauth_tokens").upsert(record).execute()
        return {"stored": True, "platform": platform, "account_id": account_id}

    async def get_token(self, platform: str, account_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a stored OAuth token."""
        if not self.db:
            return None
        result = await self.db.table("actp_oauth_tokens").select("*").eq(
            "platform", platform
        ).eq("account_id", account_id).single().execute()
        return result.data

    async def is_token_valid(self, platform: str, account_id: str) -> bool:
        """Check if a stored token is still valid (not expired)."""
        token = await self.get_token(platform, account_id)
        if not token:
            return False
        expires_at = token.get("expires_at")
        if not expires_at:
            return True  # No expiry set, assume valid
        try:
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            return expiry > datetime.now(timezone.utc)
        except Exception:
            return False

    async def list_connected_accounts(self) -> Dict[str, List[str]]:
        """List all connected social accounts by platform."""
        if not self.db:
            return {}
        result = await self.db.table("actp_oauth_tokens").select("platform, account_id").execute()
        by_platform: Dict[str, List[str]] = {}
        for row in (result.data or []):
            p = row["platform"]
            if p not in by_platform:
                by_platform[p] = []
            by_platform[p].append(row["account_id"])
        return by_platform


# ─── Funnel Tracking ──────────────────────────────────────

class FunnelTracker:
    """Track click → land → convert funnel per creative."""

    def __init__(self, db_client=None):
        self.db = db_client

    async def record_click(self, creative_id: str, source: str, metadata: Optional[Dict] = None) -> str:
        """Record a click event from a creative's CTA."""
        event = {
            "creative_id": creative_id,
            "event_type": "click",
            "source": source,
            "metadata": metadata or {},
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.db:
            result = await self.db.table("actp_funnel_events").insert(event).execute()
            return (result.data or [{}])[0].get("id", "")
        return ""

    async def record_landing(self, creative_id: str, session_id: str, metadata: Optional[Dict] = None):
        """Record a landing page view."""
        event = {
            "creative_id": creative_id,
            "event_type": "landing",
            "session_id": session_id,
            "metadata": metadata or {},
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.db:
            await self.db.table("actp_funnel_events").insert(event).execute()

    async def record_conversion(
        self, creative_id: str, session_id: str, revenue_cents: int = 0, metadata: Optional[Dict] = None
    ):
        """Record a conversion event."""
        event = {
            "creative_id": creative_id,
            "event_type": "conversion",
            "session_id": session_id,
            "revenue_cents": revenue_cents,
            "metadata": metadata or {},
            "occurred_at": datetime.now(timezone.utc).isoformat(),
        }
        if self.db:
            await self.db.table("actp_funnel_events").insert(event).execute()

    async def get_funnel_stats(self, creative_id: str) -> Dict[str, Any]:
        """Get full funnel stats for a creative."""
        if not self.db:
            return {"creative_id": creative_id, "clicks": 0, "landings": 0, "conversions": 0}

        result = await self.db.table("actp_funnel_events").select(
            "event_type, revenue_cents"
        ).eq("creative_id", creative_id).execute()

        events = result.data or []
        clicks = sum(1 for e in events if e["event_type"] == "click")
        landings = sum(1 for e in events if e["event_type"] == "landing")
        conversions = sum(1 for e in events if e["event_type"] == "conversion")
        revenue = sum(e.get("revenue_cents", 0) for e in events if e["event_type"] == "conversion")

        click_to_land = round(landings / max(clicks, 1) * 100, 1)
        land_to_convert = round(conversions / max(landings, 1) * 100, 1)
        overall_cvr = round(conversions / max(clicks, 1) * 100, 1)

        return {
            "creative_id": creative_id,
            "clicks": clicks,
            "landings": landings,
            "conversions": conversions,
            "revenue_cents": revenue,
            "revenue_usd": round(revenue / 100, 2),
            "click_to_land_pct": click_to_land,
            "land_to_convert_pct": land_to_convert,
            "overall_cvr_pct": overall_cvr,
        }


# ─── Dynamic Landing Page ─────────────────────────────────

class LandingPageManager:
    """Manage dynamic landing pages per creative."""

    def __init__(self, db_client=None):
        self.db = db_client
        self._base_url = os.getenv("ACTP_LANDING_BASE_URL", "https://app.waitlistlab.com/lp")

    def generate_tracking_url(self, creative_id: str, offer_url: str, utm_params: Optional[Dict] = None) -> str:
        """Generate a tracked landing page URL for a creative."""
        params = utm_params or {}
        params.setdefault("utm_source", "actp")
        params.setdefault("utm_medium", "video")
        params.setdefault("utm_content", creative_id[:8])

        query = "&".join(f"{k}={v}" for k, v in params.items())
        separator = "&" if "?" in offer_url else "?"
        return f"{offer_url}{separator}{query}&actp_cid={creative_id}"

    async def create_landing_page(
        self, creative_id: str, offer_id: str, headline: str, cta: str
    ) -> Dict[str, Any]:
        """Create a dynamic landing page record for a creative."""
        if not self.db:
            return {"created": False}

        slug = f"actp-{creative_id[:8]}"
        page = {
            "creative_id": creative_id,
            "offer_id": offer_id,
            "slug": slug,
            "headline": headline,
            "cta": cta,
            "url": f"{self._base_url}/{slug}",
            "active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.db.table("actp_landing_pages").insert(page).execute()
        return {"created": True, "url": page["url"], "slug": slug}


# ─── Offer Expiry Handling ─────────────────────────────────

class OfferExpiryHandler:
    """Handle offer expiry — pause ads and notify when offers expire."""

    def __init__(self, db_client=None):
        self.db = db_client

    async def check_offer_expiry(self, offer_id: str) -> Dict[str, Any]:
        """Check if an offer has expired."""
        if not self.db:
            return {"expired": False}

        result = await self.db.table("actp_campaigns").select(
            "id, name, offer_id, status"
        ).eq("offer_id", offer_id).execute()

        campaigns = result.data or []
        return {
            "offer_id": offer_id,
            "affected_campaigns": len(campaigns),
            "campaign_ids": [c["id"] for c in campaigns],
        }

    async def handle_expiry(self, offer_id: str) -> Dict[str, Any]:
        """Pause all active campaigns for an expired offer."""
        if not self.db:
            return {"handled": False}

        check = await self.check_offer_expiry(offer_id)
        paused = []

        for campaign_id in check["campaign_ids"]:
            await self.db.table("actp_campaigns").update({
                "status": "paused",
                "pause_reason": f"Offer {offer_id} expired",
            }).eq("id", campaign_id).eq("status", "active").execute()

            await self.db.table("actp_ad_deployments").update({
                "status": "paused",
            }).eq("campaign_id", campaign_id).eq("status", "active").execute()

            paused.append(campaign_id)
            logger.info(f"[ACTP:Integration] Paused campaign {campaign_id} — offer {offer_id} expired")

        return {
            "handled": True,
            "offer_id": offer_id,
            "paused_campaigns": paused,
        }


# ─── External Analytics Webhook ───────────────────────────

class AnalyticsWebhookHandler:
    """Push metric events to external analytics platforms."""

    def __init__(self, db_client=None):
        self.db = db_client
        self._webhook_manager = WebhookManager(db_client)

    async def push_winner_selected(self, campaign_id: str, creative_id: str, score: float):
        """Push winner selection event to external webhooks."""
        await self._webhook_manager.dispatch("winner.selected", {
            "campaign_id": campaign_id,
            "creative_id": creative_id,
            "score": score,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def push_round_completed(self, campaign_id: str, round_id: str, round_number: int):
        """Push round completion event to external webhooks."""
        await self._webhook_manager.dispatch("round.completed", {
            "campaign_id": campaign_id,
            "round_id": round_id,
            "round_number": round_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def push_metric_anomaly(self, creative_id: str, metric: str, value: float, expected: float):
        """Push metric anomaly alert to external webhooks."""
        await self._webhook_manager.dispatch("metric.anomaly", {
            "creative_id": creative_id,
            "metric": metric,
            "value": value,
            "expected": expected,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })


# ─── Multi-Offer Parallel Testing ─────────────────────────

class MultiOfferOrchestrator:
    """Run parallel creative tests across multiple offers simultaneously."""

    def __init__(self, db_client=None):
        self.db = db_client

    async def create_parallel_campaigns(
        self, offer_ids: List[str], base_config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create one campaign per offer, all running in parallel."""
        if not self.db:
            return []

        campaigns = []
        for offer_id in offer_ids:
            config = {**base_config, "offer_id": offer_id, "name": f"{base_config.get('name', 'Campaign')} - {offer_id[:8]}"}
            result = await self.db.table("actp_campaigns").insert(config).execute()
            if result.data:
                campaigns.append(result.data[0])
                logger.info(f"[ACTP:Integration] Created parallel campaign for offer {offer_id}")

        return campaigns

    async def get_parallel_summary(self, offer_ids: List[str]) -> Dict[str, Any]:
        """Get performance summary across all parallel offer campaigns."""
        if not self.db:
            return {"offers": []}

        summaries = []
        for offer_id in offer_ids:
            result = await self.db.table("actp_campaigns").select(
                "id, name, status"
            ).eq("offer_id", offer_id).execute()

            campaigns = result.data or []
            winner_count = 0
            for c in campaigns:
                w = await self.db.table("actp_creatives").select("id").eq(
                    "campaign_id", c["id"]
                ).eq("is_winner", True).execute()
                winner_count += len(w.data or [])

            summaries.append({
                "offer_id": offer_id,
                "campaign_count": len(campaigns),
                "winner_count": winner_count,
            })

        return {"offers": summaries, "total_offers": len(offer_ids)}


# ─── MediaPoster Lite Bridge ───────────────────────────────

class MPLiteBridge:
    """
    Integration bridge between ACTP and MediaPoster Lite.

    Handles the feedback loop when a local machine completes publishing
    via MPLite: converts the completed MPLite queue item into an ACTP
    OrganicPost and records it in the database so metrics collection begins.

    Typical flow:
      1. ACTP enqueues creative → MPLite (via MPLitePublisher)
      2. Local machine polls MPLite /api/queue/next, claims, publishes
      3. Local machine calls MPLite /api/queue/{id}/complete with post URL
      4. MPLite webhook fires → ACTP /api/actp/webhooks/receive
      5. MPLiteBridge.handle_publish_complete() records the OrganicPost
      6. ACTP begins collecting metrics for the post
    """

    def __init__(self, db_client=None):
        self.db = db_client

    async def handle_publish_complete(
        self,
        mplite_item_id: str,
        creative_id: str,
        platform: str,
        post_url: str,
        platform_post_id: Optional[str] = None,
        published_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Record a successfully published MPLite item as an ACTP OrganicPost.

        Called when the local machine reports a successful publish back to ACTP,
        either via webhook or direct API call.
        """
        from .models import Platform as ACTPPlatform

        # Map MPLite platform string back to ACTP Platform enum
        platform_map = {
            "tiktok": "tiktok",
            "youtube": "youtube_shorts",
            "instagram": "instagram_reels",
            "twitter": "twitter",
            "threads": "threads",
        }
        actp_platform = platform_map.get(platform, platform)

        post_record = {
            "creative_id": creative_id,
            "platform": actp_platform,
            "post_id": platform_post_id or mplite_item_id,
            "post_url": post_url,
            "status": "published",
            "posted_at": published_at or datetime.now(timezone.utc).isoformat(),
            "metrics": {},
            "metadata": {
                "mplite_item_id": mplite_item_id,
                "published_via": "mplite",
            },
        }

        if self.db:
            result = await self.db.table("actp_organic_posts").insert(post_record).execute()
            saved = (result.data or [{}])[0]
            logger.info(
                f"[ACTP:MPLiteBridge] OrganicPost recorded for creative {creative_id} "
                f"on {actp_platform} (post_id={post_record['post_id']})"
            )
            return {"recorded": True, "post": saved}

        logger.info(
            f"[ACTP:MPLiteBridge] OrganicPost (no DB) creative={creative_id} "
            f"platform={actp_platform} url={post_url}"
        )
        return {"recorded": False, "post": post_record}

    async def handle_publish_failed(
        self,
        mplite_item_id: str,
        creative_id: str,
        platform: str,
        error_message: str,
    ) -> Dict[str, Any]:
        """
        Record a failed MPLite publish attempt as a failed OrganicPost.

        The MPLite queue will auto-retry up to max_retries. This records
        the failure in ACTP for visibility.
        """
        platform_map = {
            "tiktok": "tiktok",
            "youtube": "youtube_shorts",
            "instagram": "instagram_reels",
            "twitter": "twitter",
            "threads": "threads",
        }
        actp_platform = platform_map.get(platform, platform)

        post_record = {
            "creative_id": creative_id,
            "platform": actp_platform,
            "post_id": mplite_item_id,
            "post_url": "",
            "status": "failed",
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "metrics": {},
            "error": error_message,
            "metadata": {
                "mplite_item_id": mplite_item_id,
                "published_via": "mplite",
            },
        }

        if self.db:
            await self.db.table("actp_organic_posts").insert(post_record).execute()

        logger.warning(
            f"[ACTP:MPLiteBridge] Publish failed for creative {creative_id} "
            f"on {actp_platform}: {error_message}"
        )
        return {"recorded": True, "creative_id": creative_id, "error": error_message}

    async def sync_completed_items(self, campaign_id: str) -> Dict[str, Any]:
        """
        Poll MPLite for completed items belonging to this campaign and
        record any that haven't been recorded in ACTP yet.

        Use this as a fallback if webhooks are not configured.
        """
        from .mplite_publisher import MPLitePublisher

        publisher = MPLitePublisher(db_client=self.db)
        if not publisher.is_configured():
            return {"synced": 0, "reason": "MPLITE_KEY not configured"}

        items = await publisher.poll_pending_for_campaign(campaign_id)
        synced = 0

        for item in items:
            if item.get("status") != "published":
                continue

            metadata = item.get("metadata") or {}
            creative_id = metadata.get("actp_creative_id")
            if not creative_id:
                continue

            # Check if already recorded
            if self.db:
                existing = await self.db.table("actp_organic_posts").select("id").eq(
                    "post_id", item["id"]
                ).execute()
                if existing.data:
                    continue

            await self.handle_publish_complete(
                mplite_item_id=item["id"],
                creative_id=creative_id,
                platform=item.get("platform", ""),
                post_url=item.get("platform_url") or "",
                platform_post_id=item.get("platform_post_id"),
                published_at=item.get("published_at"),
            )
            synced += 1

        logger.info(f"[ACTP:MPLiteBridge] Synced {synced} completed items for campaign {campaign_id}")
        return {"synced": synced, "campaign_id": campaign_id}

    def get_mplite_dashboard_url(self) -> str:
        """Return the live MPLite dashboard URL."""
        base = os.getenv("MPLITE_URL", "https://mediaposter-lite-isaiahduprees-projects.vercel.app")
        return base

    def get_mplite_api_base(self) -> str:
        """Return the MPLite API base URL."""
        return f"{self.get_mplite_dashboard_url()}/api"
