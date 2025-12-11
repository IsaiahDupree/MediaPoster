"""
Webhook Service
Phase 4: Status webhooks for publishing events
"""
import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4
import httpx


class WebhookEvent(str, Enum):
    # Publishing events
    POST_SCHEDULED = "post.scheduled"
    POST_PUBLISHING = "post.publishing"
    POST_PUBLISHED = "post.published"
    POST_FAILED = "post.failed"
    POST_DELETED = "post.deleted"
    
    # Content events
    CONTENT_ANALYZED = "content.analyzed"
    CONTENT_APPROVED = "content.approved"
    CONTENT_REJECTED = "content.rejected"
    
    # Metrics events
    METRICS_UPDATED = "metrics.updated"
    MILESTONE_REACHED = "metrics.milestone"
    
    # Comment automation events
    COMMENT_GENERATED = "comment.generated"
    COMMENT_APPROVED = "comment.approved"
    COMMENT_POSTED = "comment.posted"
    
    # System events
    RATE_LIMIT_WARNING = "system.rate_limit_warning"
    API_ERROR = "system.api_error"
    OAUTH_EXPIRING = "system.oauth_expiring"


@dataclass
class WebhookEndpoint:
    """Webhook endpoint configuration"""
    id: str
    url: str
    secret: str
    events: List[WebhookEvent]
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    failure_count: int = 0
    metadata: Dict = field(default_factory=dict)


@dataclass
class WebhookDelivery:
    """Record of a webhook delivery attempt"""
    id: str
    endpoint_id: str
    event: WebhookEvent
    payload: Dict
    status_code: Optional[int] = None
    response_body: Optional[str] = None
    success: bool = False
    attempt: int = 1
    created_at: datetime = field(default_factory=datetime.utcnow)
    delivered_at: Optional[datetime] = None
    error: Optional[str] = None


class WebhookService:
    """
    Manages webhook subscriptions and deliveries.
    Supports retry logic, signature verification, and event filtering.
    """
    
    MAX_RETRIES = 3
    RETRY_DELAYS = [60, 300, 900]  # 1 min, 5 min, 15 min
    TIMEOUT_SECONDS = 30
    MAX_FAILURES_BEFORE_DISABLE = 10
    
    def __init__(self):
        self.endpoints: Dict[str, WebhookEndpoint] = {}
        self.deliveries: List[WebhookDelivery] = []
        self.event_handlers: Dict[WebhookEvent, List[Callable]] = {}
        self._http_client: Optional[httpx.AsyncClient] = None
        self._retry_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
    
    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self.TIMEOUT_SECONDS)
        return self._http_client
    
    def register_endpoint(
        self,
        url: str,
        events: List[WebhookEvent],
        secret: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> WebhookEndpoint:
        """Register a new webhook endpoint"""
        endpoint = WebhookEndpoint(
            id=str(uuid4()),
            url=url,
            secret=secret or self._generate_secret(),
            events=events,
            metadata=metadata or {}
        )
        self.endpoints[endpoint.id] = endpoint
        return endpoint
    
    def _generate_secret(self) -> str:
        """Generate a secure webhook secret"""
        import secrets
        return secrets.token_hex(32)
    
    def _generate_signature(self, payload: str, secret: str) -> str:
        """Generate HMAC signature for payload"""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def update_endpoint(
        self,
        endpoint_id: str,
        url: Optional[str] = None,
        events: Optional[List[WebhookEvent]] = None,
        active: Optional[bool] = None
    ) -> Optional[WebhookEndpoint]:
        """Update an existing endpoint"""
        if endpoint_id not in self.endpoints:
            return None
        
        endpoint = self.endpoints[endpoint_id]
        
        if url is not None:
            endpoint.url = url
        if events is not None:
            endpoint.events = events
        if active is not None:
            endpoint.active = active
            if active:
                endpoint.failure_count = 0  # Reset on re-enable
        
        return endpoint
    
    def delete_endpoint(self, endpoint_id: str) -> bool:
        """Delete a webhook endpoint"""
        if endpoint_id in self.endpoints:
            del self.endpoints[endpoint_id]
            return True
        return False
    
    def get_endpoints_for_event(self, event: WebhookEvent) -> List[WebhookEndpoint]:
        """Get all active endpoints subscribed to an event"""
        return [
            ep for ep in self.endpoints.values()
            if ep.active and event in ep.events
        ]
    
    async def trigger_event(
        self,
        event: WebhookEvent,
        data: Dict,
        metadata: Optional[Dict] = None
    ) -> List[WebhookDelivery]:
        """
        Trigger a webhook event.
        Sends to all subscribed endpoints.
        """
        endpoints = self.get_endpoints_for_event(event)
        deliveries = []
        
        payload = {
            'event': event.value,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data,
            'metadata': metadata or {}
        }
        
        # Also trigger internal handlers
        if event in self.event_handlers:
            for handler in self.event_handlers[event]:
                try:
                    await handler(payload) if asyncio.iscoroutinefunction(handler) else handler(payload)
                except Exception:
                    pass  # Don't let handler failures affect webhook delivery
        
        # Send to external endpoints
        for endpoint in endpoints:
            delivery = await self._deliver(endpoint, payload)
            deliveries.append(delivery)
            
            # Queue for retry if failed
            if not delivery.success and delivery.attempt < self.MAX_RETRIES:
                await self._retry_queue.put((endpoint, payload, delivery.attempt + 1))
        
        return deliveries
    
    async def _deliver(
        self,
        endpoint: WebhookEndpoint,
        payload: Dict,
        attempt: int = 1
    ) -> WebhookDelivery:
        """Deliver webhook to a single endpoint"""
        delivery = WebhookDelivery(
            id=str(uuid4()),
            endpoint_id=endpoint.id,
            event=WebhookEvent(payload['event']),
            payload=payload,
            attempt=attempt
        )
        
        try:
            client = await self._get_client()
            
            payload_json = json.dumps(payload)
            signature = self._generate_signature(payload_json, endpoint.secret)
            
            headers = {
                'Content-Type': 'application/json',
                'X-Webhook-Signature': f'sha256={signature}',
                'X-Webhook-Event': payload['event'],
                'X-Webhook-Delivery': delivery.id,
                'X-Webhook-Timestamp': payload['timestamp'],
            }
            
            response = await client.post(
                endpoint.url,
                content=payload_json,
                headers=headers
            )
            
            delivery.status_code = response.status_code
            delivery.response_body = response.text[:1000]  # Truncate
            delivery.success = 200 <= response.status_code < 300
            delivery.delivered_at = datetime.utcnow()
            
            if delivery.success:
                endpoint.last_triggered = datetime.utcnow()
                endpoint.failure_count = 0
            else:
                endpoint.failure_count += 1
                
        except Exception as e:
            delivery.error = str(e)
            delivery.success = False
            endpoint.failure_count += 1
        
        # Disable endpoint if too many failures
        if endpoint.failure_count >= self.MAX_FAILURES_BEFORE_DISABLE:
            endpoint.active = False
        
        self.deliveries.append(delivery)
        return delivery
    
    async def start_retry_worker(self):
        """Start background worker for retrying failed deliveries"""
        self._running = True
        
        while self._running:
            try:
                endpoint, payload, attempt = await asyncio.wait_for(
                    self._retry_queue.get(),
                    timeout=1.0
                )
                
                # Wait before retry
                delay = self.RETRY_DELAYS[min(attempt - 1, len(self.RETRY_DELAYS) - 1)]
                await asyncio.sleep(delay)
                
                # Retry delivery
                if endpoint.active:
                    delivery = await self._deliver(endpoint, payload, attempt)
                    
                    # Queue for another retry if still failing
                    if not delivery.success and attempt < self.MAX_RETRIES:
                        await self._retry_queue.put((endpoint, payload, attempt + 1))
                        
            except asyncio.TimeoutError:
                continue
            except Exception:
                continue
    
    def stop_retry_worker(self):
        """Stop the retry worker"""
        self._running = False
    
    def register_handler(
        self,
        event: WebhookEvent,
        handler: Callable[[Dict], Any]
    ):
        """Register an internal handler for an event"""
        if event not in self.event_handlers:
            self.event_handlers[event] = []
        self.event_handlers[event].append(handler)
    
    def get_recent_deliveries(
        self,
        endpoint_id: Optional[str] = None,
        event: Optional[WebhookEvent] = None,
        limit: int = 100
    ) -> List[WebhookDelivery]:
        """Get recent webhook deliveries"""
        deliveries = self.deliveries
        
        if endpoint_id:
            deliveries = [d for d in deliveries if d.endpoint_id == endpoint_id]
        if event:
            deliveries = [d for d in deliveries if d.event == event]
        
        return sorted(deliveries, key=lambda d: d.created_at, reverse=True)[:limit]
    
    def get_delivery_stats(self, endpoint_id: Optional[str] = None) -> Dict:
        """Get delivery statistics"""
        deliveries = self.deliveries
        if endpoint_id:
            deliveries = [d for d in deliveries if d.endpoint_id == endpoint_id]
        
        total = len(deliveries)
        successful = len([d for d in deliveries if d.success])
        failed = total - successful
        
        # Calculate average response time
        response_times = [
            (d.delivered_at - d.created_at).total_seconds()
            for d in deliveries
            if d.delivered_at
        ]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'total_deliveries': total,
            'successful': successful,
            'failed': failed,
            'success_rate': successful / total if total > 0 else 0,
            'avg_response_time_seconds': avg_response_time,
        }


# Singleton instance
webhook_service = WebhookService()


# Convenience functions for triggering common events
async def notify_post_published(
    post_id: str,
    platform: str,
    post_url: str,
    title: str
):
    """Notify subscribers that a post was published"""
    await webhook_service.trigger_event(
        WebhookEvent.POST_PUBLISHED,
        {
            'post_id': post_id,
            'platform': platform,
            'post_url': post_url,
            'title': title,
        }
    )


async def notify_post_failed(
    post_id: str,
    platform: str,
    error: str,
    retry_scheduled: bool = False
):
    """Notify subscribers that a post failed"""
    await webhook_service.trigger_event(
        WebhookEvent.POST_FAILED,
        {
            'post_id': post_id,
            'platform': platform,
            'error': error,
            'retry_scheduled': retry_scheduled,
        }
    )


async def notify_metrics_updated(
    post_id: str,
    platform: str,
    metrics: Dict
):
    """Notify subscribers of metrics update"""
    await webhook_service.trigger_event(
        WebhookEvent.METRICS_UPDATED,
        {
            'post_id': post_id,
            'platform': platform,
            'metrics': metrics,
        }
    )


async def notify_milestone(
    post_id: str,
    platform: str,
    milestone_type: str,
    value: int
):
    """Notify subscribers of a milestone reached"""
    await webhook_service.trigger_event(
        WebhookEvent.MILESTONE_REACHED,
        {
            'post_id': post_id,
            'platform': platform,
            'milestone_type': milestone_type,  # e.g., 'views', 'likes'
            'value': value,  # e.g., 10000
        }
    )
