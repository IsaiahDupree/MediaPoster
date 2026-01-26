"""
Tracking Helper Functions
==========================
Convenience functions for tracking events across the application.
"""

from typing import Optional, Dict, Any
from loguru import logger

from services.user_tracking_service import UserTrackingService, EventName


async def track_login_success(user_id: str, login_method: str = "email", session_id: Optional[str] = None):
    """Track successful login (TRACK-003: Activation)"""
    tracking = UserTrackingService.get_instance()
    await tracking.track_activation(
        event_name=EventName.LOGIN_SUCCESS.value,
        user_id=user_id,
        session_id=session_id,
        properties={"login_method": login_method}
    )
    logger.info(f"✓ Tracked login_success for user {user_id}")


async def track_login_failed(error: str, session_id: Optional[str] = None):
    """Track failed login attempt (TRACK-002: Acquisition)"""
    tracking = UserTrackingService.get_instance()
    await tracking.track_acquisition(
        event_name=EventName.LOGIN_FAILED.value,
        session_id=session_id,
        properties={"error": error}
    )
    logger.info(f"✓ Tracked login_failed: {error}")


async def track_platform_connected(user_id: str, platform: str, session_id: Optional[str] = None):
    """Track platform connection (TRACK-003: Activation)"""
    tracking = UserTrackingService.get_instance()
    await tracking.track_activation(
        event_name=EventName.PLATFORM_CONNECTED.value,
        user_id=user_id,
        session_id=session_id,
        properties={"platform": platform}
    )
    logger.info(f"✓ Tracked platform_connected: {platform} for user {user_id}")


async def track_activation_complete(user_id: str, session_id: Optional[str] = None):
    """Track activation milestone (first platform connected) (TRACK-003)"""
    tracking = UserTrackingService.get_instance()
    await tracking.track_activation(
        event_name=EventName.ACTIVATION_COMPLETE.value,
        user_id=user_id,
        session_id=session_id,
        properties={}
    )
    logger.info(f"✓ Tracked activation_complete for user {user_id}")


async def track_post_created(
    user_id: str,
    post_id: str,
    platform: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None
):
    """Track post creation (TRACK-004: Core Value)"""
    tracking = UserTrackingService.get_instance()
    props = properties or {}
    props.update({
        "post_id": post_id,
        "platform": platform
    })

    await tracking.track_core_value(
        event_name=EventName.POST_CREATED.value,
        user_id=user_id,
        properties=props
    )
    logger.info(f"✓ Tracked post_created: {post_id} for user {user_id}")


async def track_post_scheduled(
    user_id: str,
    post_id: str,
    platform: str,
    scheduled_time: str,
    properties: Optional[Dict[str, Any]] = None
):
    """Track post scheduling (TRACK-004: Core Value)"""
    tracking = UserTrackingService.get_instance()
    props = properties or {}
    props.update({
        "post_id": post_id,
        "platform": platform,
        "scheduled_time": scheduled_time
    })

    await tracking.track_core_value(
        event_name=EventName.POST_SCHEDULED.value,
        user_id=user_id,
        properties=props
    )
    logger.info(f"✓ Tracked post_scheduled: {post_id} for {scheduled_time}")


async def track_post_published(
    user_id: str,
    post_id: str,
    platform: str,
    properties: Optional[Dict[str, Any]] = None
):
    """Track post publication (TRACK-004: Core Value)"""
    tracking = UserTrackingService.get_instance()
    props = properties or {}
    props.update({
        "post_id": post_id,
        "platform": platform
    })

    await tracking.track_core_value(
        event_name=EventName.POST_PUBLISHED.value,
        user_id=user_id,
        properties=props
    )
    logger.info(f"✓ Tracked post_published: {post_id} on {platform}")


async def track_media_uploaded(
    user_id: str,
    media_id: str,
    media_type: str,
    file_size: Optional[int] = None,
    properties: Optional[Dict[str, Any]] = None
):
    """Track media upload (TRACK-004: Core Value)"""
    tracking = UserTrackingService.get_instance()
    props = properties or {}
    props.update({
        "media_id": media_id,
        "media_type": media_type,
        "file_size": file_size
    })

    await tracking.track_core_value(
        event_name=EventName.MEDIA_UPLOADED.value,
        user_id=user_id,
        properties=props
    )
    logger.info(f"✓ Tracked media_uploaded: {media_id} ({media_type})")


async def track_template_used(
    user_id: str,
    template_id: str,
    template_name: str,
    properties: Optional[Dict[str, Any]] = None
):
    """Track template usage (TRACK-004: Core Value)"""
    tracking = UserTrackingService.get_instance()
    props = properties or {}
    props.update({
        "template_id": template_id,
        "template_name": template_name
    })

    await tracking.track_core_value(
        event_name=EventName.TEMPLATE_USED.value,
        user_id=user_id,
        properties=props
    )
    logger.info(f"✓ Tracked template_used: {template_name}")


async def track_checkout_started(
    user_id: str,
    plan: str,
    price: float,
    properties: Optional[Dict[str, Any]] = None
):
    """Track checkout initiation (TRACK-005: Monetization)"""
    tracking = UserTrackingService.get_instance()
    props = properties or {}
    props.update({
        "plan": plan,
        "price": price
    })

    await tracking.track_monetization(
        event_name=EventName.CHECKOUT_STARTED.value,
        user_id=user_id,
        properties=props
    )
    logger.info(f"✓ Tracked checkout_started: {plan} (${price})")


async def track_purchase_completed(
    user_id: str,
    plan: str,
    price: float,
    transaction_id: str,
    properties: Optional[Dict[str, Any]] = None
):
    """Track purchase completion (TRACK-005: Monetization)"""
    tracking = UserTrackingService.get_instance()
    props = properties or {}
    props.update({
        "plan": plan,
        "price": price,
        "transaction_id": transaction_id
    })

    await tracking.track_monetization(
        event_name=EventName.PURCHASE_COMPLETED.value,
        user_id=user_id,
        properties=props
    )
    logger.info(f"✓ Tracked purchase_completed: {plan} (${price})")


async def track_subscription_upgraded(
    user_id: str,
    from_plan: str,
    to_plan: str,
    price_delta: float,
    properties: Optional[Dict[str, Any]] = None
):
    """Track subscription upgrade (TRACK-005: Monetization)"""
    tracking = UserTrackingService.get_instance()
    props = properties or {}
    props.update({
        "from_plan": from_plan,
        "to_plan": to_plan,
        "price_delta": price_delta
    })

    await tracking.track_monetization(
        event_name=EventName.SUBSCRIPTION_UPGRADED.value,
        user_id=user_id,
        properties=props
    )
    logger.info(f"✓ Tracked subscription_upgraded: {from_plan} → {to_plan}")


# TRACK-006: Retention Event Tracking
async def track_user_returned(
    user_id: str,
    days_since_last_visit: int,
    session_id: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None
):
    """Track user return event (TRACK-006: Retention)"""
    tracking = UserTrackingService.get_instance()
    props = properties or {}
    props.update({
        "days_since_last_visit": days_since_last_visit
    })

    await tracking.track_retention(
        event_name=EventName.USER_RETURNED.value,
        user_id=user_id,
        session_id=session_id,
        properties=props
    )
    logger.info(f"✓ Tracked user_returned: user {user_id} after {days_since_last_visit} days")


async def track_feature_adopted(
    user_id: str,
    feature_name: str,
    usage_count: int = 3,
    session_id: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None
):
    """Track feature adoption (3rd usage) (TRACK-006: Retention)"""
    tracking = UserTrackingService.get_instance()
    props = properties or {}
    props.update({
        "feature_name": feature_name,
        "usage_count": usage_count
    })

    await tracking.track_retention(
        event_name=EventName.FEATURE_ADOPTED.value,
        user_id=user_id,
        session_id=session_id,
        properties=props
    )
    logger.info(f"✓ Tracked feature_adopted: {feature_name} ({usage_count} uses)")


# TRACK-007: Error & Performance Tracking
async def track_error(
    error_message: str,
    error_code: Optional[str] = None,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None
):
    """Track error event (TRACK-007)"""
    tracking = UserTrackingService.get_instance()

    await tracking.track_error(
        error_message=error_message,
        error_code=error_code,
        user_id=user_id,
        session_id=session_id,
        properties=properties
    )
    logger.info(f"✓ Tracked error: {error_code} - {error_message}")


async def track_api_latency(
    endpoint: str,
    latency_ms: float,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None
):
    """Track API endpoint latency (TRACK-007)"""
    tracking = UserTrackingService.get_instance()
    props = properties or {}
    props.update({
        "endpoint": endpoint
    })

    await tracking.track_performance(
        metric_name="api_latency",
        metric_value=latency_ms,
        user_id=user_id,
        session_id=session_id,
        properties=props
    )
    logger.debug(f"✓ Tracked api_latency: {endpoint} ({latency_ms}ms)")


async def track_page_load(
    page_url: str,
    load_time_ms: float,
    session_id: Optional[str] = None,
    properties: Optional[Dict[str, Any]] = None
):
    """Track page load time (TRACK-007)"""
    tracking = UserTrackingService.get_instance()
    props = properties or {}
    props.update({
        "page_url": page_url
    })

    await tracking.track_performance(
        metric_name="page_load_time",
        metric_value=load_time_ms,
        session_id=session_id,
        properties=props
    )
    logger.debug(f"✓ Tracked page_load_time: {page_url} ({load_time_ms}ms)")


async def track_core_web_vitals(
    page_url: str,
    lcp: Optional[float] = None,
    fid: Optional[float] = None,
    cls: Optional[float] = None,
    session_id: Optional[str] = None
):
    """Track Core Web Vitals (TRACK-007)"""
    tracking = UserTrackingService.get_instance()

    # Track LCP (Largest Contentful Paint)
    if lcp is not None:
        await tracking.track_performance(
            metric_name="lcp",
            metric_value=lcp,
            session_id=session_id,
            properties={"page_url": page_url}
        )

    # Track FID (First Input Delay)
    if fid is not None:
        await tracking.track_performance(
            metric_name="fid",
            metric_value=fid,
            session_id=session_id,
            properties={"page_url": page_url}
        )

    # Track CLS (Cumulative Layout Shift)
    if cls is not None:
        await tracking.track_performance(
            metric_name="cls",
            metric_value=cls,
            session_id=session_id,
            properties={"page_url": page_url}
        )

    logger.debug(f"✓ Tracked Core Web Vitals for {page_url}")


# TRACK-008: User Identification
async def identify_user(
    user_id: str,
    email: Optional[str] = None,
    plan: Optional[str] = None,
    name: Optional[str] = None,
    traits: Optional[Dict[str, Any]] = None
):
    """
    Identify user with traits (TRACK-008)

    Call on login or when user data is updated.

    Args:
        user_id: User ID
        email: User email
        plan: User plan (free, pro, enterprise)
        name: User name
        traits: Additional user traits
    """
    tracking = UserTrackingService.get_instance()

    # Build traits dict
    user_traits = traits or {}
    if email:
        user_traits["email"] = email
    if plan:
        user_traits["plan"] = plan
    if name:
        user_traits["name"] = name

    await tracking.identify_user(
        user_id=user_id,
        traits=user_traits
    )
    logger.info(f"✓ Identified user {user_id} with {len(user_traits)} traits")
