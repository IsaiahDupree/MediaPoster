"""
Follower tracking service for engagement analytics
Provides functions to track followers and their interactions across platforms
"""
from sqlalchemy import create_engine, text
from datetime import datetime
from typing import Optional, Dict, Any
import os
import json
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


def get_or_create_follower(
    platform: str,
    platform_user_id: str,
    username: str,
    display_name: Optional[str] = None,
    profile_url: Optional[str] = None,
    avatar_url: Optional[str] = None,
    follower_count: Optional[int] = None,
    verified: bool = False,
    bio: Optional[str] = None,
    workspace_id: Optional[str] = None
) -> str:
    """
    Get existing follower or create new one
    Returns follower_id (UUID)
    """
    conn = engine.connect()
    
    try:
        # Check if follower exists
        result = conn.execute(text("""
            SELECT id FROM followers 
            WHERE platform = :platform AND platform_user_id = :platform_user_id
        """), {
            "platform": platform,
            "platform_user_id": platform_user_id
        })
        
        existing = result.fetchone()
        
        if existing:
            follower_id = existing[0]
            
            # Update last_seen_at and any new profile data
            conn.execute(text("""
                UPDATE followers 
                SET 
                    last_seen_at = NOW(),
                    username = COALESCE(:username, username),
                    display_name = COALESCE(:display_name, display_name),
                    profile_url = COALESCE(:profile_url, profile_url),
                    avatar_url = COALESCE(:avatar_url, avatar_url),
                    follower_count = COALESCE(:follower_count, follower_count),
                    verified = :verified,
                    bio = COALESCE(:bio, bio)
                WHERE id = :follower_id
            """), {
                "follower_id": follower_id,
                "username": username,
                "display_name": display_name,
                "profile_url": profile_url,
                "avatar_url": avatar_url,
                "follower_count": follower_count,
                "verified": verified,
                "bio": bio
            })
            conn.commit()
            
            return str(follower_id)
        
        # Create new follower
        result = conn.execute(text("""
            INSERT INTO followers (
                workspace_id,
                platform,
                platform_user_id,
                username,
                display_name,
                profile_url,
                avatar_url,
                follower_count,
                verified,
                bio,
                first_seen_at,
                last_seen_at
            ) VALUES (
                :workspace_id,
                :platform,
                :platform_user_id,
                :username,
                :display_name,
                :profile_url,
                :avatar_url,
                :follower_count,
                :verified,
                :bio,
                NOW(),
                NOW()
            )
            RETURNING id
        """), {
            "workspace_id": workspace_id,
            "platform": platform,
            "platform_user_id": platform_user_id,
            "username": username,
            "display_name": display_name,
            "profile_url": profile_url,
            "avatar_url": avatar_url,
            "follower_count": follower_count,
            "verified": verified,
            "bio": bio
        })
        
        follower_id = result.fetchone()[0]
        conn.commit()
        
        return str(follower_id)
        
    finally:
        conn.close()


def record_interaction(
    follower_id: str,
    interaction_type: str,  # 'comment', 'like', 'share', 'save', 'profile_visit', 'link_click'
    platform: str,
    occurred_at: datetime,
    post_id: Optional[str] = None,
    content_id: Optional[str] = None,
    interaction_value: Optional[str] = None,
    sentiment_score: Optional[float] = None,
    sentiment_label: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    Record a follower interaction
    Returns interaction_id
    """
    conn = engine.connect()
    
    try:
        # Convert metadata dict to JSON string
        metadata_json = json.dumps(metadata) if metadata else None
        
        result = conn.execute(text("""
            INSERT INTO follower_interactions (
                follower_id,
                post_id,
                content_id,
                interaction_type,
                interaction_value,
                sentiment_score,
                sentiment_label,
                occurred_at,
                platform,
                metadata
            ) VALUES (
                :follower_id,
                :post_id,
                :content_id,
                :interaction_type,
                :interaction_value,
                :sentiment_score,
                :sentiment_label,
                :occurred_at,
                :platform,
                CAST(:metadata AS jsonb)
            )
            RETURNING id
        """), {
            "follower_id": follower_id,
            "post_id": post_id,
            "content_id": content_id,
            "interaction_type": interaction_type,
            "interaction_value": interaction_value,
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "occurred_at": occurred_at,
            "platform": platform,
            "metadata": metadata_json
        })
        
        interaction_id = result.fetchone()[0]
        conn.commit()
        
        return interaction_id
        
    finally:
        conn.close()


def analyze_sentiment(text: str) -> tuple[float, str]:
    """
    Simple sentiment analysis (can be enhanced with OpenAI later)
    Returns (score, label) where score is -1 to 1
    """
    if not text:
        return 0.0, 'neutral'
    
    text_lower = text.lower()
    
    # Positive words
    positive_words = ['love', 'great', 'awesome', 'amazing', 'perfect', 'excellent', 
                      'thanks', 'thank you', '🔥', '❤️', '😍', '🙌', '👏', '💯']
    
    # Negative words
    negative_words = ['bad', 'hate', 'terrible', 'awful', 'worst', 'disappointed',
                      'useless', 'spam', '👎', '😡', '😠']
    
    positive_count = sum(1 for word in positive_words if word in text_lower)
    negative_count = sum(1 for word in negative_words if word in text_lower)
    
    total = positive_count + negative_count
    if total == 0:
        return 0.0, 'neutral'
    
    score = (positive_count - negative_count) / total
    
    if score > 0.3:
        label = 'positive'
    elif score < -0.3:
        label = 'negative'
    else:
        label = 'neutral'
    
    return score, label


def update_engagement_scores(follower_id: Optional[str] = None):
    """
    Calculate/update engagement scores for followers
    If follower_id is provided, updates just that follower
    Otherwise updates all followers
    """
    conn = engine.connect()
    
    try:
        if follower_id:
            # Update single follower
            conn.execute(text("""
                INSERT INTO follower_engagement_scores (
                    follower_id,
                    total_interactions,
                    comment_count,
                    like_count,
                    share_count,
                    save_count,
                    profile_visit_count,
                    link_click_count,
                    engagement_score,
                    engagement_tier,
                    avg_sentiment,
                    first_interaction,
                    last_interaction,
                    last_calculated_at
                )
                SELECT
                    :follower_id,
                    COUNT(*) as total_interactions,
                    COUNT(*) FILTER (WHERE interaction_type = 'comment') as comment_count,
                    COUNT(*) FILTER (WHERE interaction_type = 'like') as like_count,
                    COUNT(*) FILTER (WHERE interaction_type = 'share') as share_count,
                    COUNT(*) FILTER (WHERE interaction_type = 'save') as save_count,
                    COUNT(*) FILTER (WHERE interaction_type = 'profile_visit') as profile_visit_count,
                    COUNT(*) FILTER (WHERE interaction_type = 'link_click') as link_click_count,
                    calculate_engagement_score(
                        COUNT(*) FILTER (WHERE interaction_type = 'comment')::INT,
                        COUNT(*) FILTER (WHERE interaction_type = 'like')::INT,
                        COUNT(*) FILTER (WHERE interaction_type = 'share')::INT,
                        COUNT(*) FILTER (WHERE interaction_type = 'save')::INT,
                        COUNT(*) FILTER (WHERE interaction_type = 'profile_visit')::INT,
                        COUNT(*) FILTER (WHERE interaction_type = 'link_click')::INT
                    ) as engagement_score,
                    determine_engagement_tier(
                        calculate_engagement_score(
                            COUNT(*) FILTER (WHERE interaction_type = 'comment')::INT,
                            COUNT(*) FILTER (WHERE interaction_type = 'like')::INT,
                            COUNT(*) FILTER (WHERE interaction_type = 'share')::INT,
                            COUNT(*) FILTER (WHERE interaction_type = 'save')::INT,
                            COUNT(*) FILTER (WHERE interaction_type = 'profile_visit')::INT,
                            COUNT(*) FILTER (WHERE interaction_type = 'link_click')::INT
                        )
                    ) as engagement_tier,
                    AVG(sentiment_score) as avg_sentiment,
                    MIN(occurred_at) as first_interaction,
                    MAX(occurred_at) as last_interaction,
                    NOW() as last_calculated_at
                FROM follower_interactions
                WHERE follower_id = :follower_id
                ON CONFLICT (follower_id) DO UPDATE SET
                    total_interactions = EXCLUDED.total_interactions,
                    comment_count = EXCLUDED.comment_count,
                    like_count = EXCLUDED.like_count,
                    share_count = EXCLUDED.share_count,
                    save_count = EXCLUDED.save_count,
                    profile_visit_count = EXCLUDED.profile_visit_count,
                    link_click_count = EXCLUDED.link_click_count,
                    engagement_score = EXCLUDED.engagement_score,
                    engagement_tier = EXCLUDED.engagement_tier,
                    avg_sentiment = EXCLUDED.avg_sentiment,
                    first_interaction = EXCLUDED.first_interaction,
                    last_interaction = EXCLUDED.last_interaction,
                    last_calculated_at = EXCLUDED.last_calculated_at
            """), {"follower_id": follower_id})
        else:
            # Update all followers with interactions
            conn.execute(text("""
                INSERT INTO follower_engagement_scores (
                    follower_id,
                    total_interactions,
                    comment_count,
                    like_count,
                    share_count,
                    save_count,
                    profile_visit_count,
                    link_click_count,
                    engagement_score,
                    engagement_tier,
                    avg_sentiment,
                    first_interaction,
                    last_interaction,
                    last_calculated_at
                )
                SELECT
                    follower_id,
                    COUNT(*) as total_interactions,
                    COUNT(*) FILTER (WHERE interaction_type = 'comment') as comment_count,
                    COUNT(*) FILTER (WHERE interaction_type = 'like') as like_count,
                    COUNT(*) FILTER (WHERE interaction_type = 'share') as share_count,
                    COUNT(*) FILTER (WHERE interaction_type = 'save') as save_count,
                    COUNT(*) FILTER (WHERE interaction_type = 'profile_visit') as profile_visit_count,
                    COUNT(*) FILTER (WHERE interaction_type = 'link_click') as link_click_count,
                    calculate_engagement_score(
                        COUNT(*) FILTER (WHERE interaction_type = 'comment')::INT,
                        COUNT(*) FILTER (WHERE interaction_type = 'like')::INT,
                        COUNT(*) FILTER (WHERE interaction_type = 'share')::INT,
                        COUNT(*) FILTER (WHERE interaction_type = 'save')::INT,
                        COUNT(*) FILTER (WHERE interaction_type = 'profile_visit')::INT,
                        COUNT(*) FILTER (WHERE interaction_type = 'link_click')::INT
                    ) as engagement_score,
                    determine_engagement_tier(
                        calculate_engagement_score(
                            COUNT(*) FILTER (WHERE interaction_type = 'comment')::INT,
                            COUNT(*) FILTER (WHERE interaction_type = 'like')::INT,
                            COUNT(*) FILTER (WHERE interaction_type = 'share')::INT,
                            COUNT(*) FILTER (WHERE interaction_type = 'save')::INT,
                            COUNT(*) FILTER (WHERE interaction_type = 'profile_visit')::INT,
                            COUNT(*) FILTER (WHERE interaction_type = 'link_click')::INT
                        )
                    ) as engagement_tier,
                    AVG(sentiment_score) as avg_sentiment,
                    MIN(occurred_at) as first_interaction,
                    MAX(occurred_at) as last_interaction,
                    NOW() as last_calculated_at
                FROM follower_interactions
                GROUP BY follower_id
                ON CONFLICT (follower_id) DO UPDATE SET
                    total_interactions = EXCLUDED.total_interactions,
                    comment_count = EXCLUDED.comment_count,
                    like_count = EXCLUDED.like_count,
                    share_count = EXCLUDED.share_count,
                    save_count = EXCLUDED.save_count,
                    profile_visit_count = EXCLUDED.profile_visit_count,
                    link_click_count = EXCLUDED.link_click_count,
                    engagement_score = EXCLUDED.engagement_score,
                    engagement_tier = EXCLUDED.engagement_tier,
                    avg_sentiment = EXCLUDED.avg_sentiment,
                    first_interaction = EXCLUDED.first_interaction,
                    last_interaction = EXCLUDED.last_interaction,
                    last_calculated_at = EXCLUDED.last_calculated_at
            """))
        
        conn.commit()
        
    finally:
        conn.close()


# Convenience function for processing comments
def process_comment(
    platform: str,
    platform_user_id: str,
    username: str,
    comment_text: str,
    occurred_at: datetime,
    post_id: Optional[str] = None,
    content_id: Optional[str] = None,
    **follower_kwargs
) -> tuple[str, int]:
    """
    Process a comment: create/update follower, analyze sentiment, record interaction
    Returns (follower_id, interaction_id)
    """
    # Get or create follower
    follower_id = get_or_create_follower(
        platform=platform,
        platform_user_id=platform_user_id,
        username=username,
        **follower_kwargs
    )
    
    # Analyze sentiment
    sentiment_score, sentiment_label = analyze_sentiment(comment_text)
    
    # Record interaction
    interaction_id = record_interaction(
        follower_id=follower_id,
        interaction_type='comment',
        platform=platform,
        occurred_at=occurred_at,
        post_id=post_id,
        content_id=content_id,
        interaction_value=comment_text,
        sentiment_score=sentiment_score,
        sentiment_label=sentiment_label
    )
    
    # Update engagement scores for this follower
    update_engagement_scores(follower_id=follower_id)
    
    return follower_id, interaction_id
