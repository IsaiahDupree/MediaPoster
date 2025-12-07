"""
Database models for post monitoring and analytics tracking
"""
from sqlalchemy import Column, String, DateTime, Integer, Float, JSON, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database.base import Base


class PostSubmission(Base):
    """Tracks Blotato post submissions"""
    __tablename__ = "post_submissions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(String, unique=True, nullable=False, index=True)  # Blotato submission ID
    clip_id = Column(UUID(as_uuid=True), ForeignKey('clips.id'), nullable=True)
    
    # Platform info
    platform = Column(String, nullable=False, index=True)  # youtube, tiktok, instagram, etc.
    account_id = Column(String, nullable=False)  # Blotato account ID
    account_name = Column(String, nullable=True)  # Human-readable account name
    
    # Post content
    caption = Column(Text, nullable=True)
    media_url = Column(String, nullable=True)  # Blotato media URL
    platform_url = Column(String, nullable=True)  # Published post URL
    
    # Status tracking
    status = Column(String, nullable=False, index=True)  # queued, processing, published, failed
    scheduled_time = Column(DateTime, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    published_at = Column(DateTime, nullable=True)
    failed_at = Column(DateTime, nullable=True)
    last_checked = Column(DateTime, default=datetime.utcnow)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_code = Column(String, nullable=True)
    
    # Metadata
    target_config = Column(JSON, nullable=True)  # Platform-specific config
    blotato_response = Column(JSON, nullable=True)  # Full Blotato response
    
    # Relationships
    analytics = relationship("PostAnalytics", back_populates="submission", cascade="all, delete-orphan")
    comments = relationship("PostComment", back_populates="submission", cascade="all, delete-orphan")
    

class PostAnalytics(Base):
    """Analytics snapshots for posts at different time intervals"""
    __tablename__ = "post_analytics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey('post_submissions.id'), nullable=False, index=True)
    
    # Timing
    checked_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    hours_since_publish = Column(Float, nullable=True)  # Hours since publication
    
    # Engagement metrics
    views = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    shares = Column(Integer, default=0)
    saves = Column(Integer, default=0)
    
    # Calculated metrics
    engagement_rate = Column(Float, nullable=True)  # (likes + comments + shares) / views
    like_rate = Column(Float, nullable=True)  # likes / views
    
    # Sentiment analysis
    sentiment_score = Column(Float, nullable=True)  # -1 to 1
    sentiment_positive = Column(Float, nullable=True)  # % positive
    sentiment_negative = Column(Float, nullable=True)  # % negative  
    sentiment_neutral = Column(Float, nullable=True)  # % neutral
    
    # Raw data
    raw_data = Column(JSON, nullable=True)  # Platform-specific raw analytics
    
    # Relationships
    submission = relationship("PostSubmission", back_populates="analytics")


class PostComment(Base):
    """Individual comments on posts for sentiment analysis"""
    __tablename__ = "post_comments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_id = Column(UUID(as_uuid=True), ForeignKey('post_submissions.id'), nullable=False, index=True)
    
    # Comment info
    comment_id = Column(String, unique=True, nullable=False, index=True)  # Platform comment ID
    author = Column(String, nullable=True)
    author_id = Column(String, nullable=True)
    text = Column(Text, nullable=False)
    
    # Sentiment
    sentiment = Column(String, nullable=True, index=True)  # positive, negative, neutral
    sentiment_score = Column(Float, nullable=True)  # Confidence score
    
    # Timing
    posted_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Metadata
    is_reply = Column(Boolean, default=False)
    likes_count = Column(Integer, default=0)
    raw_data = Column(JSON, nullable=True)
    
    # Relationships
    submission = relationship("PostSubmission", back_populates="comments")


# Migration helper
def create_tables(engine):
    """Create all monitoring tables"""
    Base.metadata.create_all(bind=engine, tables=[
        PostSubmission.__table__,
        PostAnalytics.__table__,
        PostComment.__table__
    ])
    

def drop_tables(engine):
    """Drop all monitoring tables (for testing)"""
    Base.metadata.drop_all(bind=engine, tables=[
        PostComment.__table__,
        PostAnalytics.__table__,
        PostSubmission.__table__
    ])
