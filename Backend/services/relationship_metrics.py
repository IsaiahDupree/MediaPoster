"""
RF-008: Success Metrics
Track relationship quality, not just conversion.
"""

import os
from datetime import datetime, date, timedelta, timezone
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger
from sqlalchemy import create_engine, text


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


@dataclass
class RelationshipMetrics:
    """Core relationship success metrics."""
    meaningful_replies_week: int = 0
    context_cards_filled_pct: float = 0.0
    micro_wins_month: int = 0
    avg_time_to_followup_hours: float = 0.0
    permissioned_offer_acceptance_rate: float = 0.0
    referrals_month: int = 0
    avg_relationship_health: float = 0.0
    total_contacts: int = 0
    active_contacts: int = 0


@dataclass
class PipelineFunnel:
    """Pipeline stage distribution."""
    first_touch: int = 0
    context_captured: int = 0
    micro_win: int = 0
    cadence: int = 0
    trust_signals: int = 0
    fit_identified: int = 0
    offer: int = 0
    post_win: int = 0


@dataclass
class HealthDistribution:
    """Relationship health score distribution."""
    excellent: int = 0    # 80-100
    good: int = 0         # 60-79
    needs_attention: int = 0  # 40-59
    cold: int = 0         # <40


@dataclass
class ValueDeliveryStats:
    """Statistics on value delivered."""
    total_value_delivered: int = 0
    resources_sent: int = 0
    intros_made: int = 0
    templates_shared: int = 0
    feedback_given: int = 0
    avg_value_per_contact: float = 0.0


class RelationshipMetricsService:
    """
    Tracks relationship quality metrics.
    
    Philosophy: Measure what matters - trust and value, not just conversions.
    """
    
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        logger.info("✅ RelationshipMetricsService initialized")
    
    def get_metrics(self, user_id: str) -> RelationshipMetrics:
        """Get all relationship success metrics."""
        metrics = RelationshipMetrics()
        
        try:
            with self.engine.connect() as conn:
                # Total and active contacts
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE last_touch > NOW() - INTERVAL '30 days') as active
                    FROM dm_contacts
                    WHERE user_id = :user_id
                """), {"user_id": user_id})
                row = result.mappings().fetchone()
                if row:
                    metrics.total_contacts = row["total"]
                    metrics.active_contacts = row["active"]
                
                # Meaningful replies this week
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM dm_conversations
                    WHERE contact_id IN (SELECT id FROM dm_contacts WHERE user_id = :user_id)
                    AND message_type = 'inbound'
                    AND created_at > NOW() - INTERVAL '7 days'
                """), {"user_id": user_id})
                row = result.mappings().fetchone()
                if row:
                    metrics.meaningful_replies_week = row["count"]
                
                # Context cards filled percentage
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE building IS NOT NULL AND building != '') as with_building,
                        COUNT(*) FILTER (WHERE struggles IS NOT NULL AND struggles != '') as with_struggles
                    FROM dm_contacts
                    WHERE user_id = :user_id
                """), {"user_id": user_id})
                row = result.mappings().fetchone()
                if row and row["total"] > 0:
                    filled = (row["with_building"] + row["with_struggles"]) / 2
                    metrics.context_cards_filled_pct = (filled / row["total"]) * 100
                
                # Micro-wins delivered this month
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM dm_value_delivered
                    WHERE contact_id IN (SELECT id FROM dm_contacts WHERE user_id = :user_id)
                    AND delivered_at > NOW() - INTERVAL '30 days'
                """), {"user_id": user_id})
                row = result.mappings().fetchone()
                if row:
                    metrics.micro_wins_month = row["count"]
                
                # Average relationship health
                result = conn.execute(text("""
                    SELECT AVG(relationship_health) as avg_health
                    FROM dm_contacts
                    WHERE user_id = :user_id
                """), {"user_id": user_id})
                row = result.mappings().fetchone()
                if row and row["avg_health"]:
                    metrics.avg_relationship_health = float(row["avg_health"])
                
                # Permissioned offer acceptance rate
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE accepted = true) as accepted
                    FROM dm_offers
                    WHERE contact_id IN (SELECT id FROM dm_contacts WHERE user_id = :user_id)
                    AND permissioned = true
                """), {"user_id": user_id})
                row = result.mappings().fetchone()
                if row and row["total"] > 0:
                    metrics.permissioned_offer_acceptance_rate = (row["accepted"] / row["total"]) * 100
                
                # Referrals this month (trust signals containing 'referred')
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM dm_contacts
                    WHERE user_id = :user_id
                    AND 'referred_friend' = ANY(trust_signals)
                """), {"user_id": user_id})
                row = result.mappings().fetchone()
                if row:
                    metrics.referrals_month = row["count"]
                    
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
        
        return metrics
    
    def get_pipeline_funnel(self, user_id: str) -> PipelineFunnel:
        """Get pipeline stage distribution."""
        funnel = PipelineFunnel()
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT pipeline_stage, COUNT(*) as count
                    FROM dm_contacts
                    WHERE user_id = :user_id
                    GROUP BY pipeline_stage
                """), {"user_id": user_id})
                
                for row in result.mappings():
                    stage = row["pipeline_stage"]
                    count = row["count"]
                    
                    if stage == "first_touch":
                        funnel.first_touch = count
                    elif stage == "context_captured":
                        funnel.context_captured = count
                    elif stage == "micro_win":
                        funnel.micro_win = count
                    elif stage == "cadence":
                        funnel.cadence = count
                    elif stage == "trust_signals":
                        funnel.trust_signals = count
                    elif stage == "fit_identified":
                        funnel.fit_identified = count
                    elif stage == "offer":
                        funnel.offer = count
                    elif stage == "post_win":
                        funnel.post_win = count
                        
        except Exception as e:
            logger.error(f"Failed to get pipeline funnel: {e}")
        
        return funnel
    
    def get_health_distribution(self, user_id: str) -> HealthDistribution:
        """Get relationship health score distribution."""
        dist = HealthDistribution()
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) FILTER (WHERE relationship_health >= 80) as excellent,
                        COUNT(*) FILTER (WHERE relationship_health >= 60 AND relationship_health < 80) as good,
                        COUNT(*) FILTER (WHERE relationship_health >= 40 AND relationship_health < 60) as needs_attention,
                        COUNT(*) FILTER (WHERE relationship_health < 40) as cold
                    FROM dm_contacts
                    WHERE user_id = :user_id
                """), {"user_id": user_id})
                
                row = result.mappings().fetchone()
                if row:
                    dist.excellent = row["excellent"]
                    dist.good = row["good"]
                    dist.needs_attention = row["needs_attention"]
                    dist.cold = row["cold"]
                    
        except Exception as e:
            logger.error(f"Failed to get health distribution: {e}")
        
        return dist
    
    def get_value_delivery_stats(self, user_id: str) -> ValueDeliveryStats:
        """Get statistics on value delivered."""
        stats = ValueDeliveryStats()
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE value_type = 'resource') as resources,
                        COUNT(*) FILTER (WHERE value_type = 'intro') as intros,
                        COUNT(*) FILTER (WHERE value_type = 'template') as templates,
                        COUNT(*) FILTER (WHERE value_type = 'feedback') as feedback
                    FROM dm_value_delivered
                    WHERE contact_id IN (SELECT id FROM dm_contacts WHERE user_id = :user_id)
                """), {"user_id": user_id})
                
                row = result.mappings().fetchone()
                if row:
                    stats.total_value_delivered = row["total"]
                    stats.resources_sent = row["resources"]
                    stats.intros_made = row["intros"]
                    stats.templates_shared = row["templates"]
                    stats.feedback_given = row["feedback"]
                
                # Average value per contact
                result = conn.execute(text("""
                    SELECT COUNT(DISTINCT contact_id) as contacts_with_value
                    FROM dm_value_delivered
                    WHERE contact_id IN (SELECT id FROM dm_contacts WHERE user_id = :user_id)
                """), {"user_id": user_id})
                row = result.mappings().fetchone()
                if row and row["contacts_with_value"] > 0:
                    stats.avg_value_per_contact = stats.total_value_delivered / row["contacts_with_value"]
                    
        except Exception as e:
            logger.error(f"Failed to get value delivery stats: {e}")
        
        return stats
    
    def get_full_dashboard(self, user_id: str) -> Dict:
        """Get complete metrics dashboard."""
        metrics = self.get_metrics(user_id)
        funnel = self.get_pipeline_funnel(user_id)
        health = self.get_health_distribution(user_id)
        value = self.get_value_delivery_stats(user_id)
        
        return {
            "metrics": {
                "meaningful_replies_week": metrics.meaningful_replies_week,
                "context_cards_filled_pct": round(metrics.context_cards_filled_pct, 1),
                "micro_wins_month": metrics.micro_wins_month,
                "avg_time_to_followup_hours": round(metrics.avg_time_to_followup_hours, 1),
                "permissioned_offer_acceptance_rate": round(metrics.permissioned_offer_acceptance_rate, 1),
                "referrals_month": metrics.referrals_month,
                "avg_relationship_health": round(metrics.avg_relationship_health, 1),
                "total_contacts": metrics.total_contacts,
                "active_contacts": metrics.active_contacts
            },
            "pipeline_funnel": {
                "first_touch": funnel.first_touch,
                "context_captured": funnel.context_captured,
                "micro_win": funnel.micro_win,
                "cadence": funnel.cadence,
                "trust_signals": funnel.trust_signals,
                "fit_identified": funnel.fit_identified,
                "offer": funnel.offer,
                "post_win": funnel.post_win
            },
            "health_distribution": {
                "excellent": health.excellent,
                "good": health.good,
                "needs_attention": health.needs_attention,
                "cold": health.cold
            },
            "value_delivery": {
                "total": value.total_value_delivered,
                "resources": value.resources_sent,
                "intros": value.intros_made,
                "templates": value.templates_shared,
                "feedback": value.feedback_given,
                "avg_per_contact": round(value.avg_value_per_contact, 1)
            },
            "targets": {
                "meaningful_replies_week": {"target": 50, "current": metrics.meaningful_replies_week},
                "context_cards_filled_pct": {"target": 80, "current": round(metrics.context_cards_filled_pct, 1)},
                "micro_wins_month": {"target": 20, "current": metrics.micro_wins_month},
                "avg_time_to_followup_hours": {"target": 24, "current": round(metrics.avg_time_to_followup_hours, 1)},
                "permissioned_offer_acceptance_rate": {"target": 30, "current": round(metrics.permissioned_offer_acceptance_rate, 1)},
                "referrals_month": {"target": 5, "current": metrics.referrals_month},
                "avg_relationship_health": {"target": 70, "current": round(metrics.avg_relationship_health, 1)}
            }
        }
    
    def check_3_1_rule_compliance(self, user_id: str, contact_id: str) -> Dict:
        """
        Check if 3:1 rule is being followed for a contact.
        
        3:1 Rule: For every 1 offer touch, do 3 relationship/value touches.
        """
        try:
            with self.engine.connect() as conn:
                # Count offer messages (Lane C)
                result = conn.execute(text("""
                    SELECT COUNT(*) as offers
                    FROM dm_conversations
                    WHERE contact_id = :contact_id
                    AND intent_lane = 'C'
                    AND created_at > NOW() - INTERVAL '30 days'
                """), {"contact_id": contact_id})
                offers = result.mappings().fetchone()["offers"]
                
                # Count value messages (Lane A + B)
                result = conn.execute(text("""
                    SELECT COUNT(*) as value_touches
                    FROM dm_conversations
                    WHERE contact_id = :contact_id
                    AND intent_lane IN ('A', 'B')
                    AND created_at > NOW() - INTERVAL '30 days'
                """), {"contact_id": contact_id})
                value_touches = result.mappings().fetchone()["value_touches"]
                
                # Count value delivered
                result = conn.execute(text("""
                    SELECT COUNT(*) as value_delivered
                    FROM dm_value_delivered
                    WHERE contact_id = :contact_id
                    AND delivered_at > NOW() - INTERVAL '30 days'
                """), {"contact_id": contact_id})
                value_delivered = result.mappings().fetchone()["value_delivered"]
                
                total_value = value_touches + value_delivered
                ratio = total_value / offers if offers > 0 else float('inf')
                compliant = ratio >= 3.0 or offers == 0
                
                return {
                    "compliant": compliant,
                    "ratio": round(ratio, 1) if ratio != float('inf') else "∞",
                    "value_touches": total_value,
                    "offer_touches": offers,
                    "recommendation": "Good balance!" if compliant else f"Deliver {3 * offers - total_value} more value touches before next offer"
                }
                
        except Exception as e:
            logger.error(f"Failed to check 3:1 rule: {e}")
            return {"compliant": True, "ratio": "N/A", "error": str(e)}
